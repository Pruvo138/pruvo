#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/n2b-dagitim-probu.py — DAGITILAN parti kapisini CALISTIRARAK olcer.

NEDEN VAR (20 Agu 2026, canli bloker):
`mimar-kapi-kur.py --parti-kapisi --uygula` her eve `<ev>/.claude/parti-kapisi.py`
kopyaladi ve "KURULDU" yazdi. Kopyanin YANINDA bagimliligi (T4 =
`parti-borc-kapisi.py`) YOKTU; kapi T4'u KARDES dosya olarak ariyordu,
bulamiyordu ve hatayi SESSIZCE yutuyordu -> her ev icin `N2B-OLCULEMEDI`
(fail-closed) -> bes evin ucuz kati (isci.sh) OLDU, sebebi hicbir satirda
gorunmedi. Dagitim raporu yine de yesil okunuyordu.

DERS: "dosya yerinde" ile "kapi kosuyor" AYNI SEY DEGILDIR
([[aracin-teshis-cumlesi-olcum-degil]]) ve bir kapinin menzili CAGRI YERIDIR
([[kapinin-menzili-cagri-yeridir]]) — repo kopyasinin yesil olmasi, EVLERE
DAGITILAN kopya hakkinda HICBIR SEY soylemez.

NE OLCER (her ev icin, SALT OKUMA — hicbir dosya yazilmaz):
  YUZEY-ISCI  : kopyayi `--isci-kapi <motor> <kok> <spec> <ETIKET>` ile kosar —
                `isci.sh`in GERCEKTEN cagirdigi kol. 🔴 SINIFLAMA BU YUZEYDEN
                OKUNUR: hukum satiri (`N2B HUKUM=... KOL=...`) GECER halinde de
                BASILIR, kanca yuzeyinde ise GECER = CIKTISIZ izindir. Yalniz
                kancaya bakan bir prob, "kalemi yok" ile "defteri yok"u ayirt
                EDEMEZ ve ucuncu kovayi GECER'e yutar.
  YUZEY-KANCA : kopyaya gercek bir PreToolUse JSON'u verir (mahsur kalan
                cagrinin birebir taklidi: `isci.sh ... <MUAF OLMAYAN ETIKET>`).
                Iki yuzey AYNI karar fonksiyonundan turer -> ANLASMAK ZORUNDA;
                anlasmazlik = olcum guvenilmez = SINIFLANAMAYAN.
  YUZEY-T4    : kopyayi `--t4-durum` ile kosar (bagimlilik teshisi; onarim
                oncesi surumde bu bayrak YOKTUR ve rc=2 doner — o da olcumdur).

Ev tablosu TEK KAYNAK: `tools/mimar-kapi-kur.py:CODEX_EVLER` (ikinci tablo YOK).

KABUL (calistirilabilir):
  python3 tools/n2b-dagitim-probu.py --kendini-test
    son satir + rc=0:  VAKA=7/7 MUTANT=3/3 HEDEF_KOL_ATFI=3/3 BAGLAMA=3/3
    🔴 Bu batarya SART: canli duzlemde `DEFTER_YOK_EV=0` yazildiginda o sifir
    tek basina CURUTULEMEZ (kova calisirken de, kova OLU iken de 0 yazar).

  python3 tools/n2b-dagitim-probu.py
    rc=0  <=> OLU_EV=0 VE SINIFLANAMAYAN_EV=0
    rc=1  <=> ikisinden biri >0 (hepsi SATIRLA yazilir — sessiz kirpma yok)
  🔴 KOVA DORTTUR (K229):
    OLU            T4/ev cozulemedi ya da defter VAR ama okunamadi -> hat OLU
    DEFTER_YOK     evin defter DOSYASI hic yok -> hat ACIK, ama olcum EKSIK;
                   AYRI sayilir, `CANLI`ya YAZILMAZ ve rc'yi kirmizi YAPMAZ
    CANLI          gercek olcum yapildi (RED / SUREN / MUAF)
    SINIFLANAMAYAN prob hukum okuyamadi ya da iki yuzey ANLASMADI
  Ucuncu/dorduncu kova baska bir kovaya yazilirsa olcememe basari gibi okunur
  [[iki-kovali-siniflama-ucuncu-sinifi-yutar]]. Sinif jetondan okunur, rc'den
  DEGIL [[rc-hukmu-kapi-imzasini-ezer]] — ama rc ile jeton celisirse
  SINIFLANAMAYAN'a dusulur.
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

KURUCU_YOLU = "/Users/okan/dev/pruvo/tools/mimar-kapi-kur.py"
ISCI_SARMALAYICI = "/Users/okan/.claude/cron/isci.sh"
# 🔴 MUAF OLMAYAN etiket sart: muaf etiket (tamir/onarim/kabul/nobet/posta/
# devir) T4'e HIC ugramaz ve prob KORLESIR — yesil gorunur, hicbir sey olcmez.
VARSAYILAN_ETIKET = "d2-2"

# Hukum satirindaki KOL jetonu -> prob kovasi. TEK esleme tablosu.
KOL_KOVA = {
    "N2B-OLCULEMEDI": "OLU",
    "N2B-DEFTER-YOK": "DEFTER_YOK",
    "N2B-RED":        "CANLI",
    "N2B-SUREN":      "CANLI",
    "N2B-MUAF":       "CANLI",
}
# `--isci-kapi` cikis kodlari (kapinin sozlesmesi): 0 GECER · 1 RED · 2 OLCULEMEDI
KOL_BEKLENEN_RC = {
    "N2B-OLCULEMEDI": 2,
    "N2B-DEFTER-YOK": 0,
    "N2B-RED":        1,
    "N2B-SUREN":      0,
    "N2B-MUAF":       0,
}


def kurucu_yukle(yol):
    spec = importlib.util.spec_from_file_location("pruvo_kurucu", yol)
    if spec is None or spec.loader is None:
        raise ImportError("kurucu spec/loader COZULEMEDI: %s" % yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _hukum_kolu(metin):
    """Bir cikti govdesindeki SON `N2B HUKUM=` satirindan KOL jetonunu ceker.

    🔴 Serbest metinden DEGIL, hukum satirindan okunur: defterdeki bir kelime
    (`OLCULEMEDI`) kapinin hukmunu taklit edebilir
    [[aracin-teshis-cumlesi-olcum-degil]].
    """
    hukumler = [s.strip() for s in (metin or "").splitlines()
                if s.strip().startswith("N2B HUKUM=")]
    if not hukumler:
        return None, None
    son = hukumler[-1]
    for jeton in KOL_KOVA:
        if ("KOL=%s" % jeton) in son:
            return jeton, son
    return None, son


def siniflandir_isci_ciktisi(govde, rc, *, mutant=None):
    """SAF SINIFLAYICI — (kova, jeton, satir). Prob hukmunun TEK yeri.

    🔴 Ayri fonksiyon, cunku canli duzlemde `DEFTER_YOK_EV=0` basildiginda bu
    sayi TEK BASINA CURUTULEMEZ: kova calisiyorken de, kova OLU iken de 0 yazar
    [[batarya-kapsam-tabani-sayiyla-civilenir]]. Burasi `--kendini-test` ile
    mutasyona tabidir; `isci_probu` bu fonksiyona DELEGE eder (ikinci hukum YOK).
    """
    jeton, satir = _hukum_kolu(govde)
    if jeton is None:
        # 🔴 Hukum okunamadi -> "canli" SAYILMAZ (ucuncu sinifi yutma).
        ozet = " ⏎ ".join(s.strip() for s in (govde or "").strip().splitlines()
                          if s.strip())
        return "SINIFLANAMAYAN", "HUKUMSUZ", (ozet[:300] or "(cikti yok)")
    if mutant != "M3" and rc != KOL_BEKLENEN_RC[jeton]:
        # Sinif jetondan okunur, ama jeton ile rc CELISIYORSA olcum guvenilmez
        # [[rc-hukmu-kapi-imzasini-ezer]].
        return ("SINIFLANAMAYAN", "RC-CELISKI",
                "%s || jeton %s rc=%d bekliyordu, rc=%d geldi"
                % (satir[:200], jeton, KOL_BEKLENEN_RC[jeton], rc))
    kova = KOL_KOVA[jeton]
    if mutant == "M1" and kova == "DEFTER_YOK":
        kova = "OLU"        # ucuncu kova IKINCIYE yutulur -> ev bosuna kirmizi
    if mutant == "M2" and kova == "DEFTER_YOK":
        kova = "CANLI"      # ucuncu kova "olcum yapildi" gibi okunur
    return kova, jeton, satir[:240]


def isci_probu(kapi, kok, etiket):
    """`isci.sh`in cagirdigi kolu CALISTIRIR. -> (kova, jeton, rc, satir).

    SALT OKUMA: `--isci-kapi` yalnizca hukme baglar ve basar, hicbir sey yazmaz.
    """
    try:
        p = subprocess.run([sys.executable, kapi, "--isci-kapi", "kimi", kok,
                            "/tmp/spec-prob.md", etiket],
                           capture_output=True, text=True, timeout=120)
    except Exception as e:
        return "SINIFLANAMAYAN", "PROB-COKTU", -1, "%s: %s" % (type(e).__name__, e)
    govde = (p.stdout or "") + (p.stderr or "")
    kova, jeton, satir = siniflandir_isci_ciktisi(govde, p.returncode)
    return kova, jeton, p.returncode, satir


def kanca_probu(kapi, kok, etiket):
    """Kopyayi gercek PreToolUse girdisiyle kosar. -> (sinif, rc, satir)."""
    girdi = {
        "tool_name": "Bash",
        "tool_input": {"command": "%s kimi %s /tmp/spec-prob.md %s"
                                  % (ISCI_SARMALAYICI, kok, etiket)},
        "cwd": kok,
    }
    try:
        p = subprocess.run([sys.executable, kapi, "--kanca"],
                           input=json.dumps(girdi), capture_output=True,
                           text=True, timeout=120)
    except Exception as e:
        return "PROB-COKTU", -1, "%s: %s" % (type(e).__name__, e)
    ham = (p.stdout or "").strip()
    if not ham:
        return "GECER", p.returncode, "(cikti yok = izin)"
    try:
        veri = json.loads(ham)
    except Exception:
        return "COZULEMEDI", p.returncode, ham[:240]
    ozel = veri.get("hookSpecificOutput") or {}
    if ozel.get("permissionDecision") != "deny":
        return "GECER", p.returncode, ham[:240]
    sebep = (ozel.get("permissionDecisionReason") or "").strip()
    ilk = sebep.splitlines()[0] if sebep else "(sebep YOK — sessiz yutma)"
    # 🔴 SINIFLAMA HUKUM JETONUNDAN OKUNUR, SERBEST METINDEN DEGIL.
    # Ilk surum `"OLCULEMEDI" in sebep` diyordu ve KraL'i OLU sandi: RED metni
    # acik kalemleri BASAR, K53'un govdesinde `OLCULEMEDI (rc=3)` geciyordu ->
    # defterdeki bir kelime kapinin HUKMUNU taklit etti (yanlis KIRMIZI).
    # [[aracin-teshis-cumlesi-olcum-degil]] · [[rc-hukmu-kapi-imzasini-ezer]]
    hukumler = [s for s in sebep.splitlines() if s.startswith("N2B HUKUM=")]
    if not hukumler:
        # 🔴 UCUNCU KOVA: siniflanamayan cagri "canli" SAYILMAZ — iki kovali
        # siniflama ucuncu sinifi yutar [[iki-kovali-siniflama-ucuncu-sinifi-yutar]].
        return "HUKUMSUZ", p.returncode, ilk[:300]
    sinif = "OLCULEMEDI" if "KOL=N2B-OLCULEMEDI" in hukumler[-1] else "RED"
    return sinif, p.returncode, "%s || %s" % (hukumler[-1][:200], ilk[:160])


def t4_probu(kapi):
    try:
        p = subprocess.run([sys.executable, kapi, "--t4-durum"],
                           capture_output=True, text=True, timeout=120)
    except Exception as e:
        return -1, "%s: %s" % (type(e).__name__, e)
    ham = ((p.stdout or "") + (p.stderr or "")).strip().replace("\n", " ⏎ ")
    return p.returncode, (ham[:400] or "(cikti yok)")


def _hukum_govdesi(kol, hukum, ev="X"):
    return ("N2B PARTI KAPISI — sentetik\n"
            "N2B HUKUM=%s KOL=%s EV=%s ACIK=0 KALEM=-\n" % (hukum, kol, ev))


# (ad, govde, rc, beklenen_kova, beklenen_jeton)
_KT_VAKALAR = (
    ("defter-yok",  _hukum_govdesi("N2B-DEFTER-YOK", "GECER"), 0,
     "DEFTER_YOK", "N2B-DEFTER-YOK"),
    ("olculemedi",  _hukum_govdesi("N2B-OLCULEMEDI", "RED"),   2, "OLU",
     "N2B-OLCULEMEDI"),
    ("red",         _hukum_govdesi("N2B-RED", "RED"),          1, "CANLI",
     "N2B-RED"),
    ("suren",       _hukum_govdesi("N2B-SUREN", "GECER"),      0, "CANLI",
     "N2B-SUREN"),
    ("muaf",        _hukum_govdesi("N2B-MUAF", "GECER"),       0, "CANLI",
     "N2B-MUAF"),
    ("hukumsuz",    "bir sey yazdi ama hukum satiri YOK\n",    0,
     "SINIFLANAMAYAN", "HUKUMSUZ"),
    ("rc-celiski",  _hukum_govdesi("N2B-DEFTER-YOK", "GECER"), 2,
     "SINIFLANAMAYAN", "RC-CELISKI"),
)

# mutant -> (aciklama, hedef vaka adlari)
_KT_MUTANTLAR = {
    "M1": ("DEFTER_YOK kovasi OLU'ya YUTULUR (ucuncu kova kaybolur)",
           ("defter-yok",)),
    "M2": ("DEFTER_YOK kovasi CANLI'ya YUTULUR (olcememe 'olcum' okunur)",
           ("defter-yok",)),
    "M3": ("jeton<->rc celiski kolu OLDURULUR", ("rc-celiski",)),
}


def kendini_test():
    """🔴 `DEFTER_YOK_EV=<n>` sayisini CURUTULEBILIR kilar.

    Canli duzlemde bugun dort evin de defteri VAR (20 Agu 03:21'de acildilar),
    yani `DEFTER_YOK_EV=0`. O sifir, kova CALISIRKEN de kova OLU iken de ayni
    yazilir — bu batarya olmadan ucuncu kova KAPSAM DISI kalirdi.
    """
    print("N2B DAGITIM PROBU — KENDINI-TEST (siniflayici + kova ayrimi)")
    print("")
    taban_ok, taban = True, {}
    for ad, govde, rc, b_kova, b_jeton in _KT_VAKALAR:
        kova, jeton, _s = siniflandir_isci_ciktisi(govde, rc)
        taban[ad] = (kova, jeton)
        ok = (kova == b_kova and jeton == b_jeton)
        taban_ok = taban_ok and ok
        print("  TABAN %-12s -> kova=%-14s jeton=%-16s (beklenen %s/%s) %s"
              % (ad, kova, jeton, b_kova, b_jeton, "✓" if ok else "✗"))
    print("")

    # KAPSAM: her jeton bir vakada GORUNMELI, her kova bir vaka URETMELI.
    vaka_jetonlari = set(v[4] for v in _KT_VAKALAR)
    eksik_jeton = sorted(set(KOL_KOVA) - vaka_jetonlari)
    uretilen_kova = set(v[3] for v in _KT_VAKALAR)
    eksik_kova = sorted({"OLU", "DEFTER_YOK", "CANLI", "SINIFLANAMAYAN"}
                        - uretilen_kova)
    kapsam_ok = not eksik_jeton and not eksik_kova
    print("KAPSAM jeton=%d/%d kova=%d/4 eksik_jeton=%s eksik_kova=%s %s"
          % (len(vaka_jetonlari & set(KOL_KOVA)), len(KOL_KOVA),
             len(uretilen_kova), eksik_jeton or "-", eksik_kova or "-",
             "✓" if kapsam_ok else "✗"))
    print("")
    if not taban_ok or not kapsam_ok:
        print("TABAN/KAPSAM KIRMIZI — mutant olcumu ANLAMSIZ.")
        print("VAKA=0/%d MUTANT=0/%d HEDEF_KOL_ATFI=0/%d"
              % (len(_KT_VAKALAR), len(_KT_MUTANTLAR), len(_KT_MUTANTLAR)))
        return 1

    mutant_sayaci, atif_sayaci = 0, 0
    for ad in sorted(_KT_MUTANTLAR):
        aciklama, hedefler = _KT_MUTANTLAR[ad]
        print("MUTANT %s — %s" % (ad, aciklama))
        hedef_kirmizi, yan_bozulan = False, []
        for vad, govde, rc, _bk, _bj in _KT_VAKALAR:
            kova, jeton, _s = siniflandir_isci_ciktisi(govde, rc, mutant=ad)
            degisti = ((kova, jeton) != taban[vad])
            if vad in hedefler:
                if degisti:
                    hedef_kirmizi = True
                print("  hedef %-12s taban=%-14s mutant=%-14s"
                      % (vad, taban[vad][0], kova))
            elif degisti:
                yan_bozulan.append(vad)
        print("  yan eksen bozulan: %s" % (",".join(yan_bozulan) or "-"))
        if hedef_kirmizi:
            mutant_sayaci += 1
            print("  SONUÇ: BEKLENDI YAKALANDI (mutant yasamaz)")
        else:
            print("  SONUÇ: BEKLENDI YAKALANMADI (MUTANT YASARDI)")
        if hedef_kirmizi and not yan_bozulan:
            atif_sayaci += 1
            print("  ATIF : hedef kol kirmizi + yan eksen YESIL")
        else:
            print("  ATIF : KUSUR")
        print("")

    # 🔴 BAGLAMA KONTROLU: `isci_probu` GERCEKTEN bu siniflayiciya delege
    # ediyor mu? Yoksa siniflayiciyi test etmek TAUTOLOJI olurdu — kapinin
    # menzili CAGRI YERIDIR [[kapinin-menzili-cagri-yeridir]]. Gercek bir alt
    # surec (sentetik kapi betigi) kosulur.
    gecici = tempfile.mkdtemp(prefix="n2b-prob-kt-")
    bagli = 0
    baglama = (("N2B-DEFTER-YOK", "GECER", 0, "DEFTER_YOK"),
               ("N2B-OLCULEMEDI", "RED",   2, "OLU"),
               ("N2B-RED",        "RED",   1, "CANLI"))
    try:
        for kol, hukum, rc, b_kova in baglama:
            sahte = os.path.join(gecici, "kapi-%s.py" % kol.lower())
            with open(sahte, "w", encoding="utf-8") as f:
                f.write("import sys\n")
                f.write("sys.stdout.write(%r)\n" % _hukum_govdesi(kol, hukum))
                f.write("sys.exit(%d)\n" % rc)
            kova, jeton, rc_g, _s = isci_probu(sahte, "/tmp/sentetik-ev", "d2-2")
            ok = (kova == b_kova and jeton == kol and rc_g == rc)
            bagli += 1 if ok else 0
            print("BAGLAMA isci_probu(%s) -> kova=%-14s rc=%d (beklenen %s/%d) %s"
                  % (kol, kova, rc_g, b_kova, rc, "✓" if ok else "✗"))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)   # ureten temizler
    print("")
    print("VAKA=%d/%d MUTANT=%d/%d HEDEF_KOL_ATFI=%d/%d BAGLAMA=%d/%d"
          % (len(_KT_VAKALAR), len(_KT_VAKALAR), mutant_sayaci,
             len(_KT_MUTANTLAR), atif_sayaci, len(_KT_MUTANTLAR),
             bagli, len(baglama)))
    return 0 if (mutant_sayaci == len(_KT_MUTANTLAR)
                 and atif_sayaci == len(_KT_MUTANTLAR)
                 and bagli == len(baglama)) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--etiket", default=VARSAYILAN_ETIKET,
                    help="prob etiketi (MUAF OLMAYAN olmali)")
    ap.add_argument("--kurucu", default=KURUCU_YOLU)
    ap.add_argument("--kendini-test", action="store_true",
                    help="siniflayici + kova ayrimi mutasyon bataryasi")
    args = ap.parse_args(argv)

    if args.kendini_test:
        return kendini_test()

    kurucu = kurucu_yukle(args.kurucu)
    print("N2B DAGITIM PROBU — dagitilan kopyalar CALISTIRILARAK olculur")
    print("ev tablosu (tek kaynak): %s" % args.kurucu)
    print("prob etiketi: %s" % args.etiket)
    print("")

    olu, canli, kapisiz, siniflanamayan, defter_yok = [], [], [], [], []
    for ad, kok, _goreli, mod in kurucu.CODEX_EVLER:
        goreli = ("tools/parti-kapisi.py" if mod == "kaynak"
                  else ".claude/parti-kapisi.py")
        kapi = os.path.join(kok, goreli)
        if not os.path.isdir(kok):
            print("%-7s %-34s EV-YOK" % (ad, kok))
            kapisiz.append(ad)
            continue
        if not os.path.isfile(kapi):
            print("%-7s %-34s KAPI-YOK (%s)" % (ad, kok, goreli))
            kapisiz.append(ad)
            continue
        kova, jeton, rc_i, satir_i = isci_probu(kapi, kok, args.etiket)
        sinif, rc_k, satir = kanca_probu(kapi, kok, args.etiket)
        rc_t, t4_satir = t4_probu(kapi)

        # 🔴 IKI YUZEY ANLASMAK ZORUNDA (ayni karar fonksiyonundan turerler).
        # Kanca yuzeyi yalnizca RED/OLCULEMEDI'de `deny` basar; GECER ciktisizdir.
        kanca_deny = (sinif in ("RED", "OLCULEMEDI"))
        beklenen_deny = (kova in ("CANLI", "OLU")
                         and jeton in ("N2B-RED", "N2B-OLCULEMEDI"))
        uyum = (kanca_deny == beklenen_deny) if kova != "SINIFLANAMAYAN" else True
        if not uyum:
            kova = "SINIFLANAMAYAN"
            jeton = "YUZEY-CELISKISI"

        if kova == "OLU":
            olu.append(ad)
        elif kova == "DEFTER_YOK":
            defter_yok.append(ad)
        elif kova == "CANLI":
            canli.append(ad)
        else:
            siniflanamayan.append("%s(%s)" % (ad, jeton))
        print("%-7s %-34s %s (%d B)"
              % (ad, kok, goreli, os.path.getsize(kapi)))
        print("        YUZEY-ISCI  kova=%-14s jeton=%-16s rc=%d | %s"
              % (kova, jeton, rc_i, satir_i))
        print("        YUZEY-KANCA sinif=%-11s rc=%d deny=%-5s (beklenen %-5s) | %s"
              % (sinif, rc_k, kanca_deny, beklenen_deny, satir))
        print("        YUZEY-T4    rc=%-3d | %s" % (rc_t, t4_satir))
        print("")

    print("-" * 92)
    print("OLU_EV=%d %s" % (len(olu), ",".join(olu) or "-"))
    # 🔴 K229 — AYRI SATIR, AYRI SAYI. `CANLI_EV`e toplanirsa "olcum yapildi"
    # gibi okunur; `OLU_EV`e toplanirsa dort ev bosuna kirmizi yanar.
    print("DEFTER_YOK_EV=%d %s (hat ACIK, kalem olcumu YOK — ev defter "
          "gelenegini benimsemedi)"
          % (len(defter_yok), ",".join(defter_yok) or "-"))
    print("CANLI_EV=%d %s" % (len(canli), ",".join(canli) or "-"))
    print("KAPISIZ_EV=%d %s" % (len(kapisiz), ",".join(kapisiz) or "-"))
    print("SINIFLANAMAYAN_EV=%d %s"
          % (len(siniflanamayan), ",".join(siniflanamayan) or "-"))
    return 0 if not (olu or siniflanamayan) else 1


if __name__ == "__main__":
    sys.exit(main())
