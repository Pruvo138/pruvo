#!/usr/bin/env python3
r"""KABUL TESTI — denetim-kapisi.py UCRETLI-ATIF KOLU (para odenen kaynak => public `lisans`/atif YOK).

NE OLCER (fikstur SENTETIK; gercek kaynak adi YOK, sahte kaynak `ornek-uyelik.invalid`):
  (a) GERCEK katalog (bu agacin urunler.json'u, salt okuma): PUBLIC kol 0 isabet. Gizli kayit
      varsa GIZLI kol da 0; yoksa OLCULEMEDI BASILIR (sahte YESIL yok, CI'da beklenen).
  (b) fikstur: uyelik kaynakli id + public `lisans` -> KIRMIZI · ayni id `lisans`siz -> YESIL ·
      CC BY + atif -> YESIL ve atif SILINMEDI (fikstur ONCE == SONRA) · satin-alma / parametrik
      + `lisans` -> KIRMIZI · public `lisans` icinde ucretli jeton, gizli dosya YOK -> KIRMIZI ·
      gizli dosya YOK + temiz -> OLCULEMEDI (YESIL DEGIL).
  (c) "PUBLIC" alt-dizge vaka ciftleri (atif_sinifi): GNU (Lesser) General Public License -> ATIF
      (dogru eslesme: CC0/PD SAYILMAZ) · Public Domain / CC0 -> SERBEST · CC BY -> ATIF.
  (d) UCTAN UCA main(): sentetik katalog + --kaynaklar -> rc 1 + `UCRETLI_ATIF_KOLU=KIRMIZI`;
      temiz -> rc 0; gizli dosya yok -> rc 0 + `UCRETLI_ATIF_KOLU=OLCULEMEDI`.
MUTANTLAR (kaynak BELLEKTE derlenir; canli dosya sha256 ONCE == SONRA):
  M1 kapi rc'ye baglanmadi            -> (d) KIRMIZI vaka gecer -> yakalanmali
  M2 GIZLI kol kalkti                 -> (b) uyelik + lisans -> yakalanmali
  M3 OLCULEMEDI sahte YESIL'e dondu   -> (b)/(d) OLCULEMEDI -> yakalanmali
  M4 PUBLIC kol kalkti                -> (b) public jeton -> yakalanmali
  M5 "public" alt-dizge kusuru (PD deseni -> \bpublic\b) -> (c) GPL -> yakalanmali
  K0 ilgisiz yorum degisikligi        -> HICBIR iddia dusmemeli

Calistir:  python3 tools/ucretli-atif-kolu-test.py   (cikis 0 = gecti, 1 = kaldi)
"""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import types

DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DIR)
DK_YOL = os.path.join(DIR, "denetim-kapisi.py")
KATALOG = os.path.join(ROOT, "urunler.json")
GIZLI = os.path.join(ROOT, ".urun-kaynaklari.json")
CANLI = [DK_YOL, KATALOG, GIZLI]
SAHTE = "https://ornek-uyelik.invalid/model/1"


def _sha(yol):
    try:
        with open(yol, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return "YOK"


SHA_ONCE = {y: _sha(y) for y in CANLI}


def _sessiz_yukle(ad, src):
    m = types.ModuleType(ad)
    m.__file__ = DK_YOL
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        exec(compile(src, DK_YOL + "#" + ad, "exec"), m.__dict__)
    return m


def _kaynak():
    with open(DK_YOL, encoding="utf-8") as f:
        return f.read()


def _yukle_mutant(capa, yeni):
    """Capa TEK kez gecmiyorsa None (OLCULEMEDI — sessiz yesil YOK)."""
    src = _kaynak()
    if src.count(capa) != 1:
        return None
    return _sessiz_yukle("dk_ucretli_mutant", src.replace(capa, yeni, 1))


def _u(uid, lisans=None, **kw):
    u = {"id": uid, "baslik": "Urun " + uid, "kategori": "Tamirat"}
    if lisans is not None:
        u["lisans"] = lisans
    u.update(kw)
    return u


ATIF = {"tur": "CC BY 4.0", "tasarimci": "ornek-tasarimci"}
UYELIK_LIS = {"tur": "uyelik", "tasarimci": "uyelik"}


def batarya(dk):
    s = []
    gizli = {
        "u1": {"kaynak": "ornek-uyelik", "link": SAHTE, "tur": "uyelik", "lisans": "uyelik"},
        "u2": {"kaynak": "ornek-uyelik", "link": SAHTE, "uyelik": "ornek-uyelik"},
        "c1": {"kaynak": "Ornek", "link": "https://ornek.invalid/1", "lisans": "CC BY 4.0",
               "tur": "ucretsiz-cc", "tasarimci": "ornek-tasarimci"},
        "s1": {"kaynak": "Ornek", "tur": "satin-alma"},
        "p1": {"kaynak": "Ornek", "tur": "kendi-tasarim"},
    }
    # (b) uyelik id + atif -> KIRMIZI (lisans nesnesi de, ucretli jetonsuz CC dizgesi de)
    r = dk.ucretli_atif_kolu([_u("u1", dict(UYELIK_LIS)), _u("u2", dict(ATIF))], gizli)
    s.append(("(b) uyelik id + public lisans -> KIRMIZI (gizli 2)",
              r["durum"] == "KIRMIZI" and sorted(r["gizli_ids"]) == ["u1", "u2"]))
    r = dk.ucretli_atif_kolu([_u("u1"), _u("u2")], gizli)
    s.append(("(b) uyelik id lisanssiz -> YESIL", r["durum"] == "YESIL" and not r["gizli_ids"]))
    kat = [_u("c1", dict(ATIF))]
    once = copy.deepcopy(kat)
    r = dk.ucretli_atif_kolu(kat, gizli)
    s.append(("(b) CC BY + atif -> YESIL ve atif SILINMEDI",
              r["durum"] == "YESIL" and kat == once and kat[0].get("lisans") == ATIF))
    r = dk.ucretli_atif_kolu([_u("s1", dict(ATIF))], gizli)
    s.append(("(b) satin-alma + lisans -> KIRMIZI", r["durum"] == "KIRMIZI"))
    r = dk.ucretli_atif_kolu([_u("p1", dict(ATIF), parametrik=True)], gizli)
    s.append(("(b) parametrik + lisans -> KIRMIZI", r["durum"] == "KIRMIZI"))
    r = dk.ucretli_atif_kolu([_u("x1", dict(UYELIK_LIS))], None)
    s.append(("(b) public jeton, gizli dosya YOK -> KIRMIZI (PUBLIC kol)",
              r["durum"] == "KIRMIZI" and r["public_ids"] == ["x1"]))
    r = dk.ucretli_atif_kolu([_u("c1", dict(ATIF))], None)
    s.append(("(b) gizli dosya YOK + temiz -> OLCULEMEDI (YESIL DEGIL)",
              r["durum"] == "OLCULEMEDI" and r["gizli_kol"] == "OLCULEMEDI"))

    # (c) "PUBLIC" alt-dizge vaka ciftleri — dogru/yanlis eslesme
    for dizge, beklenen in (("GNU General Public License v3.0", "ATIF"),
                            ("GNU Lesser General Public License", "ATIF"),
                            ("GNU GPL - GNU General Public License 3.0", "ATIF"),
                            ("Public Domain", "SERBEST"),
                            ("Public Domain Dedication", "SERBEST"),
                            ("CC0", "SERBEST"),
                            ("CC BY 4.0", "ATIF")):
        got = dk.atif_sinifi({"lisans": dizge})
        s.append(("(c) %r -> %s (bulunan %s)" % (dizge, beklenen, got), got == beklenen))
    return s


def gercek(dk):
    """(a) gercek katalog salt okuma."""
    s = []
    try:
        with open(KATALOG, encoding="utf-8") as f:
            kat = json.load(f)
    except (OSError, ValueError) as e:
        return [("(a) gercek katalog okunamadi: %s" % e, False)]
    gizli = None
    try:
        with open(GIZLI, encoding="utf-8") as f:
            gizli = json.load(f)
    except (OSError, ValueError):
        pass
    r = dk.ucretli_atif_kolu(kat, gizli if isinstance(gizli, dict) else None)
    print("  (a) gercek katalog: UCRETLI_ATIF_KOLU=%s GIZLI_KOL=%s GIZLI=%d PUBLIC=%d"
          % (r["durum"], r["gizli_kol"], len(r["gizli_ids"]), len(r["public_ids"])))
    s.append(("(a) gercek katalog PUBLIC kol 0", not r["public_ids"]))
    s.append(("(a) gercek katalog GIZLI kol 0 ya da OLCULEMEDI",
              not r["gizli_ids"] and r["gizli_kol"] in ("YESIL", "OLCULEMEDI")))
    return s


def uctan_uca(dk, tmp):
    s = []
    gizli = {"u1": {"kaynak": "ornek-uyelik", "link": SAHTE, "tur": "uyelik"},
             "c1": {"kaynak": "Ornek", "lisans": "CC BY 4.0", "tur": "ucretsiz-cc"}}
    ky = os.path.join(tmp, "kaynak.json")
    with open(ky, "w", encoding="utf-8") as f:
        json.dump(gizli, f)
    dk.ATIF_IHLAL_TABANI, dk.SINIFLANAMADI_BOS_TABANI = 99, 99

    def kos(urunler, kaynak):
        uy = os.path.join(tmp, "urunler.json")
        with open(uy, "w", encoding="utf-8") as f:
            json.dump(urunler, f)
        dk.URUNLER = uy
        eski = sys.argv
        # varsayilan parti kipi + HEAD = fikstur: yeni parti BOS, diger kapilarin fikstur
        # ihlali rc'yi kirletmez; atif kollari parti farkindan bagimsiz TUM katalogu olcer.
        dk._head_ids = lambda: {u["id"] for u in urunler}
        sys.argv = ["denetim-kapisi.py", "--kaynaklar", kaynak,
                    "--rapor", os.path.join(tmp, "r.json")]
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                rc = dk.main()
        finally:
            sys.argv = eski
        return rc, out.getvalue()

    rc, out = kos([_u("u1", dict(ATIF)), _u("c1", dict(ATIF))], ky)
    s.append(("(d) main: uyelik + atif -> rc 1 + UCRETLI_ATIF_KOLU=KIRMIZI",
              rc == 1 and "UCRETLI_ATIF_KOLU=KIRMIZI GIZLI=1" in out))
    rc, out = kos([_u("u1"), _u("c1", dict(ATIF))], ky)
    s.append(("(d) main: temiz -> rc 0 + UCRETLI_ATIF_KOLU=YESIL",
              rc == 0 and "UCRETLI_ATIF_KOLU=YESIL" in out))
    rc, out = kos([_u("u1"), _u("c1", dict(ATIF))], os.path.join(tmp, "yok.json"))
    s.append(("(d) main: gizli dosya YOK -> rc 0 + UCRETLI_ATIF_KOLU=OLCULEMEDI",
              rc == 0 and "UCRETLI_ATIF_KOLU=OLCULEMEDI" in out))
    return s


MUTANTLAR = [
    ("M1 kapi rc'ye baglanmadi",
     '    atif_kirmizi = atif["durum"] == "KIRMIZI" or ucretli["durum"] == "KIRMIZI"\n',
     '    atif_kirmizi = atif["durum"] == "KIRMIZI"\n',
     ["(d) main: uyelik + atif"]),
    ("M2 GIZLI kol kalkti",
     '                atif_sinifi(kaynaklar.get(str(u.get("id"))), u) == "UCRETLI":',
     '                atif_sinifi(kaynaklar.get(str(u.get("id"))), u) == "UCRETLI_YOK":',
     ["(b) uyelik id + public lisans", "(b) satin-alma", "(b) parametrik"]),
    ("M3 OLCULEMEDI sahte YESIL",
     '    elif not gizli_var:\n        r["durum"] = "OLCULEMEDI"\n',
     '    elif not gizli_var:\n        r["durum"] = "YESIL"\n',
     ["(b) gizli dosya YOK + temiz", "(d) main: gizli dosya YOK"]),
    ("M4 PUBLIC kol kalkti",
     '            r["public_ids"].append(u["id"])\n',
     '            pass\n',
     ["(b) public jeton"]),
    ("M5 'public' alt-dizge kusuru",
     r'_ATIF_SERBEST_RE = re.compile(r"\bcc0\b|\bpublic domain\b|\bkamu mali\b")',
     r'_ATIF_SERBEST_RE = re.compile(r"\bcc0\b|\bpublic\b|\bkamu mali\b")',
     ["(c) 'GNU General Public License v3.0'", "(c) 'GNU Lesser General Public License'"]),
]
KONTROL = ("K0 ilgisiz yorum degisikligi",
           "# KOL UCRETLI-ATIF: atif kolunun TERS yonu.",
           "# KOL UCRETLI-ATIF: atif kolunun TERS yonu. (kontrol mutanti)")


def _hepsi(dk, tmp):
    return batarya(dk) + uctan_uca(dk, tmp)


def main():
    fails = []
    tmp = tempfile.mkdtemp(prefix="ucretli-atif-test-")
    try:
        dk = _sessiz_yukle("dk_ucretli_canli", _kaynak())
        sonuc = gercek(dk) + _hepsi(dk, tmp)
        for ad, ok in sonuc:
            print("  %-5s %s" % ("OK" if ok else "KALDI", ad))
            if not ok:
                fails.append(ad)
        print("canli: %d/%d iddia" % (sum(ok for _, ok in sonuc), len(sonuc)))

        print("\n--- MUTANTLAR (bellekte) ---")
        for ad, capa, yeni, beklenen in MUTANTLAR:
            m = _yukle_mutant(capa, yeni)
            if m is None:
                print("  KALDI %s: capa TEK kez tutmadi (OLCULEMEDI)" % ad)
                fails.append(ad + " OLCULEMEDI")
                continue
            dusen = [a for a, ok in _hepsi(m, tmp) if not ok]
            hepsi = all(any(d.startswith(b) for d in dusen) for b in beklenen)
            print("  %-5s %s -> %d iddia KIRMIZI (beklenen %s)"
                  % ("OK" if hepsi else "KALDI", ad, len(dusen), " · ".join(beklenen)))
            if not hepsi:
                fails.append(ad + " OLDURULEMEDI")
        ad, capa, yeni = KONTROL
        m = _yukle_mutant(capa, yeni)
        dusen = None if m is None else [a for a, ok in _hepsi(m, tmp) if not ok]
        ok = dusen == []
        print("  %-5s %s -> %s" % ("OK" if ok else "KALDI", ad,
                                   "capa yok" if dusen is None else "%d KIRMIZI" % len(dusen)))
        if not ok:
            fails.append(ad)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n--- sha256 ONCE == SONRA (canli dosyalara yazilmadi) ---")
    for y in CANLI:
        esit = SHA_ONCE[y] == _sha(y)
        print("  %-5s %s" % ("OK" if esit else "KALDI", os.path.relpath(y, ROOT)))
        if not esit:
            fails.append("sha " + y)
    if fails:
        print("\nSONUC: KIRMIZI ❌ — %d kalem: %s" % (len(fails), "; ".join(fails[:8])))
        return 1
    print("\nSONUC: YESIL ✅ — canli batarya + %d mutant + 1 kontrol + sha nobeti"
          % len(MUTANTLAR))
    return 0


if __name__ == "__main__":
    sys.exit(main())
