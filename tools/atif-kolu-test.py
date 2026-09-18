#!/usr/bin/env python3
r"""KABUL TESTI — denetim-kapisi.py ATIF KOLU (K418: gizli atif-zorunlu => public `lisans` dolu).

NE OLCER (tamami SENTETIK veri; gercek urunler.json / .urun-kaynaklari.json OKUNMAZ, YAZILMAZ):
  (a) atif-zorunlu gizli tur + public `lisans` DOLU        -> temiz (ihlal 0)
  (b) atif-zorunlu gizli tur + public `lisans` null/bos    -> SAYILIR; her varyant AILESINDEN
      en az bir dizge (ciplak "BY", Cults "cc_by_sa", uzun GPL, kisa GPL, LGPL, MIT, BSD,
      "CC BY - Attribution", "Creative Commons — Attribution", {tasarimci,tur} nesnesi)
  (c) CC0 / Public Domain                                   -> MUAF (SERBEST)
  (d) "... SATIN ALINMADI", "UYELIK", Standard/Royalty, tur=satin-alma, parametrik -> MUAF
  (e) NON-GROWTH: ihlal == taban YESIL · taban+1 KIRMIZI · taban-1 YESIL + "taban dusurulebilir"
  (f) taninmayan gizli dizge                                -> SINIFLANAMADI (muaf DEGIL) +
      kendi tabanini asinca KIRMIZI
  (g) gizli kayit YOK (None)                                -> OLCULEMEDI, KIRMIZI DEGIL
  (h) UCTAN UCA main(): sentetik katalog + --kaynaklar ile rc ve `ATIF_KOLU=` satiri;
      gizli dosya yokken OLCULEMEDI + rc 0 (CI davranisi).
MUTANTLAR (kaynak BELLEKTE derlenir; canli dosya sha256 ONCE == SONRA):
  M1 siniflayici her seyi MUAF doner      -> (b)/(e) KIRMIZI olmali
  M2 uzun GPL bicimini tanimayan eski desen -> (b) KIRMIZI olmali
  M3 NON-GROWTH karsilastirmasi gevsetildi (taban+1 serbest) -> (e) KIRMIZI olmali
  M4 SINIFLANAMADI 'muaf' sayildi (fail-open) -> (f) KIRMIZI olmali
  K0 ilgisiz (yorum) degisiklik            -> HICBIR iddia dusmemeli (yalanci-hassasiyet nobeti)

Calistir:  python3 tools/atif-kolu-test.py   (cikis 0 = gecti, 1 = kaldi)
"""
import contextlib
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
CANLI = [DK_YOL, os.path.join(ROOT, "urunler.json"), os.path.join(ROOT, ".urun-kaynaklari.json")]


def _sha(yol):
    try:
        with open(yol, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return "YOK"


SHA_ONCE = {y: _sha(y) for y in CANLI}


def _yukle_canli():
    spec = importlib.util.spec_from_file_location("dk_atif_canli", DK_YOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _yukle_mutant(capa, yeni):
    """Capa TEK kez gecmiyorsa None (OLCULEMEDI — sessiz yesil YOK)."""
    with open(DK_YOL, encoding="utf-8") as f:
        src = f.read()
    if src.count(capa) != 1:
        return None
    m = types.ModuleType("dk_atif_mutant")
    m.__file__ = DK_YOL
    exec(compile(src.replace(capa, yeni, 1), DK_YOL + "#mutant", "exec"), m.__dict__)
    return m


# --- sentetik veri (gercek tasarimci/tedarikci ADI YOK) -------------------------------------
def _u(uid, lisans=None, **kw):
    u = {"id": uid, "kategori": "Otomobil", "marka": ["Audi"],
         "baslik": "Sentetik Braket %s" % uid,
         "aciklama": "Sentetik parca. Yaklasik dis olculer: 40 × 30 × 12 mm.",
         "fiyat": "850 TL",
         "gorseller": ["https://media.pruvo3d.com/urunler/%s-1.jpg" % uid],
         "lisans": lisans}
    u.update(kw)
    return u


PUB = {"tasarimci": "Sentetik Tasarimci", "tur": "CC BY 4.0"}

# (b) atif-zorunlu varyant aileleri — her biri public null ile SAYILMALI
ATIF_VARYANT = [
    "BY", "BY-SA", "CC-BY", "cc_by_sa", "CC BY - Attribution",
    "Creative Commons — Attribution  — Share Alike", "GNU General Public License v3.0",
    "GNU Lesser General Public License", "GPL 2.0", "GNU - GPL", "MIT", "BSD License",
    {"tasarimci": "Sentetik Tasarimci", "tur": "CC BY 4.0"},
]
SERBEST_VARYANT = ["CC0", "Creative Commons — Public Domain", "CC0 1.0", "PUBLIC-DOMAIN"]
UCRETLI_VARYANT = ["cults_cu (Commercial Use) - SATIN ALINMADI", "UYELIK", "uyelik",
                   "Standard Digital File License", "Royalty Free License",
                   "CGTrader custom (Custom License) - SATIN ALINMADI"]
TANINMAYAN = "Sentetik Lisans Turu XYZ-42"


def _kayit(lisans, **kw):
    k = {"kaynak": "Sentetik", "link": "https://ornek.invalid/x", "lisans": lisans}
    k.update(kw)
    return k


def batarya(dk):
    """[(iddia adi, ok)] — ayni batarya canli modul ve mutantlara uygulanir."""
    s = []

    def iddia(ad, ok):
        s.append((ad, bool(ok)))

    # (a) dolu public -> temiz
    ur = [_u("a%d" % i, PUB) for i in range(len(ATIF_VARYANT))]
    kay = {"a%d" % i: _kayit(v) for i, v in enumerate(ATIF_VARYANT)}
    r = dk.atif_kolu(ur, kay, taban=0, siniflanamadi_tabani=0)
    iddia("(a) atif-zorunlu + public DOLU -> ihlal 0, YESIL",
          r["ihlal"] == 0 and r["durum"] == "YESIL")

    # (b) her varyant null public ile TEK TEK sayilir
    for i, v in enumerate(ATIF_VARYANT):
        r = dk.atif_kolu([_u("b%d" % i)], {"b%d" % i: _kayit(v)}, taban=0,
                         siniflanamadi_tabani=0)
        iddia("(b) atif-zorunlu %r + public null -> SAYILIR (ihlal 1)" % (v,),
              r["ihlal"] == 1 and r["durum"] == "KIRMIZI")
    # public bos dizge / tur'u bos nesne da BOS sayilir
    r = dk.atif_kolu([_u("b-bos", {"tasarimci": "Sentetik", "tur": ""})],
                     {"b-bos": _kayit("GPL 3.0")}, taban=0, siniflanamadi_tabani=0)
    iddia("(b) public lisans nesnesi tur'u BOS -> SAYILIR", r["ihlal"] == 1)

    # (c) serbest -> muaf
    for i, v in enumerate(SERBEST_VARYANT):
        r = dk.atif_kolu([_u("c%d" % i)], {"c%d" % i: _kayit(v)}, taban=0,
                         siniflanamadi_tabani=0)
        iddia("(c) %r -> MUAF (SERBEST, ihlal 0, SINIFLANAMADI 0)" % v,
              r["ihlal"] == 0 and r["sinif"]["SERBEST"] == 1 and r["durum"] == "YESIL")

    # (d) ucretli model -> muaf
    for i, v in enumerate(UCRETLI_VARYANT):
        r = dk.atif_kolu([_u("d%d" % i)], {"d%d" % i: _kayit(v)}, taban=0,
                         siniflanamadi_tabani=0)
        iddia("(d) %r -> MUAF (UCRETLI)" % v,
              r["ihlal"] == 0 and r["sinif"]["UCRETLI"] == 1 and r["durum"] == "YESIL")
    r = dk.atif_kolu([_u("d-sa")], {"d-sa": _kayit(None, tur="satin-alma")}, 0, 0)
    iddia("(d) lisanssiz tur=satin-alma -> MUAF (UCRETLI)",
          r["sinif"]["UCRETLI"] == 1 and r["durum"] == "YESIL")
    r = dk.atif_kolu([_u("d-p", parametrik=True)], {"d-p": _kayit("CC-BY")}, 0, 0)
    iddia("(d) parametrik (sari seri, kendi IP) -> MUAF", r["ihlal"] == 0)

    # (e) NON-GROWTH
    ur = [_u("e%d" % i) for i in range(3)]
    kay = {"e%d" % i: _kayit("BY") for i in range(3)}
    r = dk.atif_kolu(ur, kay, taban=3, siniflanamadi_tabani=0)
    iddia("(e) ihlal == taban (3) -> YESIL", r["ihlal"] == 3 and r["durum"] == "YESIL")
    r = dk.atif_kolu(ur, kay, taban=2, siniflanamadi_tabani=0)
    iddia("(e) ihlal == taban+1 -> KIRMIZI", r["ihlal"] == 3 and r["durum"] == "KIRMIZI")
    r = dk.atif_kolu(ur, kay, taban=4, siniflanamadi_tabani=0)
    iddia("(e) ihlal < taban -> YESIL + 'taban dusurulebilir'",
          r["durum"] == "YESIL" and any("taban dusurulebilir" in n for n in r["notlar"]))
    iddia("(e) canli taban sabiti tanimli ve >= 0",
          isinstance(dk.ATIF_IHLAL_TABANI, int) and dk.ATIF_IHLAL_TABANI >= 0)

    # (f) taninmayan dizge -> SINIFLANAMADI (muaf DEGIL)
    r = dk.atif_kolu([_u("f1")], {"f1": _kayit(TANINMAYAN)}, taban=0, siniflanamadi_tabani=1)
    iddia("(f) taninmayan dizge -> SINIFLANAMADI sayaci 1 (taban icinde YESIL)",
          r["sinif"]["SINIFLANAMADI"] == 1 and r["siniflanamadi_bos"] == 1
          and r["durum"] == "YESIL")
    r = dk.atif_kolu([_u("f1")], {"f1": _kayit(TANINMAYAN)}, taban=0, siniflanamadi_tabani=0)
    iddia("(f) SINIFLANAMADI tabani asildi -> KIRMIZI (fail-closed)", r["durum"] == "KIRMIZI")
    r = dk.atif_kolu([_u("f2")], {"f2": {"link": "https://ornek.invalid/y"}}, 0, 0)
    iddia("(f) lisans+tur YOK (yalniz link) -> SINIFLANAMADI",
          r["sinif"]["SINIFLANAMADI"] == 1)
    r = dk.atif_kolu([_u("f3")], {"f3": _kayit("bilinmiyor")}, 0, 0)
    iddia("(f) 'bilinmiyor' -> BELIRSIZ ayri sayac, KIRMIZI DEGIL",
          r["sinif"]["BELIRSIZ"] == 1 and r["durum"] == "YESIL")
    r = dk.atif_kolu([_u("f4")], {"f4": _kayit("CC BY-NC 4.0")}, 0, 0)
    iddia("(f) -NC -> NC ayri sayac (ATIF ihlali DEGIL)",
          r["sinif"]["NC"] == 1 and r["nc_bos"] == 1 and r["ihlal"] == 0)

    # (g) gizli kayit YOK -> OLCULEMEDI
    r = dk.atif_kolu([_u("g1")], None, taban=0, siniflanamadi_tabani=0)
    iddia("(g) gizli kayit YOK -> OLCULEMEDI (KIRMIZI DEGIL)", r["durum"] == "OLCULEMEDI")
    return s


def uctan_uca(dk, tmp):
    """(h) main() sentetik katalog ile; dk.URUNLER ve _head_ids BELLEKTE yamanir."""
    s = []
    ur = [_u("h1"), _u("h2"), _u("h3", PUB)]
    kay = {"h1": _kayit("GNU General Public License v2.0"), "h2": _kayit("BY"),
           "h3": _kayit("CC-BY")}
    uy = os.path.join(tmp, "urunler.json")
    ky = os.path.join(tmp, "kaynak.json")
    with open(uy, "w", encoding="utf-8") as f:
        json.dump(ur, f)
    with open(ky, "w", encoding="utf-8") as f:
        json.dump(kay, f)
    dk.URUNLER = uy
    dk._head_ids = lambda: set()

    def kos(argv):
        eski = sys.argv
        sys.argv = ["denetim-kapisi.py"] + argv + ["--rapor", os.path.join(tmp, "r.json")]
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                rc = dk.main()
        finally:
            sys.argv = eski
        return rc, out.getvalue()

    dk.ATIF_IHLAL_TABANI, dk.SINIFLANAMADI_BOS_TABANI = 2, 0
    rc, out = kos(["--tum-katalog", "--kaynaklar", ky])
    s.append(("(h) main: ihlal 2 == taban 2 -> rc 0 + ATIF_KOLU=YESIL IHLAL=2",
              rc == 0 and "ATIF_KOLU=YESIL IHLAL=2" in out))
    dk.ATIF_IHLAL_TABANI = 1
    rc, out = kos(["--tum-katalog", "--kaynaklar", ky])
    s.append(("(h) main: taban+1 -> rc 1 + ATIF_KOLU=KIRMIZI", rc == 1 and "ATIF_KOLU=KIRMIZI" in out))
    rc, out = kos(["--tum-katalog", "--envanter", "--kaynaklar", ky])
    s.append(("(h) main --envanter: KIRMIZI RAPORLANIR, rc 0",
              rc == 0 and "ATIF_KOLU=KIRMIZI" in out))
    rc, out = kos(["--tum-katalog", "--kaynaklar", os.path.join(tmp, "yok.json")])
    s.append(("(h) main: gizli dosya YOK -> ATIF_KOLU=OLCULEMEDI + rc 0 (CI davranisi)",
              rc == 0 and "ATIF_KOLU=OLCULEMEDI" in out))
    return s


MUTANTLAR = [
    # (ad, capa, yeni, olmesi gereken iddia oneki listesi)
    ("M1 siniflayici her seyi MUAF doner",
     "    alinirsa Ticari) - SATIN ALINMADI' ucretli modeldir, atif kolu DEGIL.\"\"\"\n",
     "    alinirsa Ticari) - SATIN ALINMADI' ucretli modeldir, atif kolu DEGIL.\"\"\"\n"
     "    return \"SERBEST\"\n",
     ["(b)", "(e) ihlal == taban+1"]),
    ("M2 uzun GPL bicimini tanimayan eski desen",
     r'    r"|\bl?gpl\b|\bgnu\b|\bgeneral public license\b|\bmit\b|\bbsd\b")',
     r'    r"|\bgpl\b|\bmit\b|\bbsd\b")',
     ["(b) atif-zorunlu 'GNU General Public License v3.0'"]),
    ("M3 NON-GROWTH gevsetildi (taban+1 serbest)",
     '    if r["ihlal"] > taban:', '    if r["ihlal"] > taban + 1:',
     ["(e) ihlal == taban+1"]),
    ("M4 SINIFLANAMADI 'muaf' sayildi (fail-open)",
     '            return "BELIRSIZ"\n        return "SINIFLANAMADI"\n',
     '            return "BELIRSIZ"\n        return "SERBEST"\n',
     ["(f) lisans+tur YOK"]),
]
KONTROL = ("K0 ilgisiz yorum degisikligi",
           "# KOL K418: ATIF EKSENI", "# KOL K418: ATIF EKSENI (kontrol mutanti)")


def main():
    fails = []
    tmp = tempfile.mkdtemp(prefix="atif-kolu-test-")
    try:
        dk = _yukle_canli()
        sonuc = batarya(dk) + uctan_uca(dk, tmp)
        for ad, ok in sonuc:
            print("  %-4s %s" % ("OK" if ok else "KALDI", ad))
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
            dusen = [a for a, ok in batarya(m) if not ok]
            hepsi = all(any(d.startswith(b) for d in dusen) for b in beklenen)
            print("  %-4s %s -> %d iddia KIRMIZI (beklenen %s)"
                  % ("OK" if hepsi else "KALDI", ad, len(dusen), ", ".join(beklenen)))
            if not hepsi:
                fails.append(ad + " OLDURULEMEDI")
        ad, capa, yeni = KONTROL
        m = _yukle_mutant(capa, yeni)
        dusen = None if m is None else [a for a, ok in batarya(m) if not ok]
        ok = dusen == []
        print("  %-4s %s -> %s" % ("OK" if ok else "KALDI", ad,
                                   "capa yok" if dusen is None else "%d KIRMIZI" % len(dusen)))
        if not ok:
            fails.append(ad)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n--- sha256 ONCE == SONRA (canli dosyalara yazilmadi) ---")
    for y in CANLI:
        once, sonra = SHA_ONCE[y], _sha(y)
        esit = once == sonra
        print("  %-4s %s once=%s sonra=%s" % ("OK" if esit else "KALDI",
                                              os.path.relpath(y, ROOT), once[:16], sonra[:16]))
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
