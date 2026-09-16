#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K351-31AGU KABUL KAPISI — rotasyonun BASLANGIC bacagi onarim esiginden turer.

🔴 OLCULEN ARIZA (29 Agu + 31 Agu, uc bagimsiz kosum; 16 Eyl'de kodda birebir
dogrulandi): `defter-rotasyon.py` icindeki BASLANGIC kapisi
`if not _tavan_asildi_mi(...): return 0` CEZA esigini soruyordu; onarim esigi
(`_su_seviyesi_ustunde_mi`, K353) YALNIZ durma kolunda kullaniliyordu. Yani
esik ayrimi DURMA bacagina uygulanmis, BASLAMA bacagi ceza esiginde kalmisti
([[onarim-kolu-zarar-esiginin-arkasinda]]). Sonuc olculdu: defter 12.284 B /
tavan 12.288 B iken yordamin EMRETTIGI `--tavan-kaynaktan`
`TASINAN=0 ... TAVAN=DOLU_NO_OP` dondu ve dosya BIREBIR ayni kaldi. Koruma,
korudugu isi ancak zarar olustuktan SONRA yapabiliyordu — ama o an kota kapisi
evin TUM commit'ini zaten kilitlemis olur.

BU BATARYA NE OLCER
  V1  TABAN: tavan ALTINDA + su seviyesi USTUNDE bir defterde `--tavan-kaynaktan`
      HICBIR SEY tasimaz (arizanin birebir sekli — bu davranis DOGRUDUR,
      ceza esigi ekseni budur; kirmizi olan sey BUNUN TEK YOL OLMASIYDI)
  V2  🔴 ONARIM: ayni defterde `--onlem` GERCEKTEN tasir (TASINAN>0) ve dosya
      KUCULUR
  V3  🔴 IKI BACAK TEK ESIKTEN TURER: `--onlem` su seviyesinin ALTINA inince
      DURUR (asiri tasima yok, ikinci-derece esik uretmez)
  V4  🔴 FAIL-CLOSED: tek kaynakta `su_seviyesi()` YOKSA `--onlem` TAVANA
      SESSIZCE GERI DUSMEZ; `OLCULEMEDI` + rc=4
  V5  MENZIL SINIRI: `--onlem` kota kapisinin HUKMUNU degistirmez (kilit hala
      YALNIZ tavandan turer — onlemi hukme baglamak arizayi onarmak degil ONE
      ALMAK olurdu)
  V6  KONTROL: su seviyesinin de ALTINDAKI defterde `--onlem` NO-OP kalir ve
      dosya BAYT BAYT ayni durur

MUTANTLAR (hedef-kol ATIFLI)
  M1  BASLANGIC kapisi ceza esigine GERI konur   -> V2 OLMELI
  M2  `--onlem` bayragi YOK SAYILIR              -> V2 OLMELI
  M3  fail-closed kolu kaldirilir (esik yoksa tavana duser) -> V4 OLMELI
  M4  KONTROL: ilgisiz metin degisikligi         -> HEPSI YESIL KALMALI

Kosum: python3 tools/defter-onlem-bacagi-test.py   (borusuz; rc 0/1)
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROTASYON = os.path.join(TOOLS, "defter-rotasyon.py")
TABAN = os.path.join(TOOLS, "defter-kota-taban.py")
KOTA_KAPISI = os.path.join(TOOLS, "defter-kota-kapisi.py")

_GECEN = []
_KALAN = []


def iddia(ad, kosul, kanit=""):
    if kosul:
        _GECEN.append(ad)
        print("  ✅ %s" % ad)
    else:
        _KALAN.append(ad)
        print("  ❌ %s\n     kanit: %s" % (ad, str(kanit)[:600]))


def kos(arac_kok, argv, **kw):
    """Rotasyon araci kosar; (rc, stdout+stderr) doner. BORU YOK."""
    p = subprocess.run(
        [sys.executable, os.path.join(arac_kok, "defter-rotasyon.py")] + argv,
        capture_output=True, text=True, **kw)
    return p.returncode, p.stdout + p.stderr


# ---------------------------------------------------------------------------
# FIKSTUR — tavan ALTINDA ama SU SEVIYESI USTUNDE bir defter + kapali icerik
# ---------------------------------------------------------------------------
# 🔴 BLOK SEKLI OLCULEREK SECILDI (16 Eyl): `defter-rotasyon.py:408` bloklari
# `## ` basligindan, `:140` maddeleri `- ` onekinden tanir. `### ` basligi ve
# `- [x]` maddesi BLOK=0 uretir — fikstur o sekilde yazilirsa batarya, aracin
# degil KENDI fiksturunun sessizligini olcerdi.
KAPALI_BLOK = """## {tarih} — K{no} kapandi
- ✅ K{no} bitti, kanit sha {sha}
- ✅ K{no} ikinci madde tamam
"""

ACIK_BLOK = """## 2026-09-16 — K{no} suruyor
- 🔴 ACIK: K{no} bu blok tasinmaz
"""


def fikstur_defter(kapali_adet, acik_adet):
    parca = ["# DEVAM — calisma defteri", ""]
    for i in range(kapali_adet):
        parca.append(KAPALI_BLOK.format(tarih="2026-09-%02d" % (1 + i % 28),
                                        no=500 + i, sha="%06x" % (i * 7919)))
    for i in range(acik_adet):
        parca.append(ACIK_BLOK.format(no=900 + i))
    return "\n".join(parca) + "\n"


def arac_kopyasi(kok, *, yama=None):
    """Rotasyon aracinin + tek kaynagin IZOLE kopyasi (mutant burada yasar).

    🔴 GERCEK ARAC ASLA DEGISTIRILMEZ: mutant yalniz bu gecici kopyada.
    """
    hedef = os.path.join(kok, "arac")
    os.makedirs(hedef, exist_ok=True)
    for ad in ("defter-rotasyon.py", "defter-kota-taban.py"):
        shutil.copy2(os.path.join(TOOLS, ad), os.path.join(hedef, ad))
    if yama:
        yama(hedef)
    return hedef


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def _yaz(yol, metin):
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)


def m1_baslangic_geri(hedef):
    """M1: BASLANGIC kapisi CEZA esigine geri konur (onarim oncesi hâl)."""
    yol = os.path.join(hedef, "defter-rotasyon.py")
    s = _oku(yol)
    capa = "        _baslangic_asildi_mi = _tavan_asildi_mi\n        _m1 = 1\n"
    yeni = s.replace("    _baslangic_asildi_mi = _tavan_asildi_mi\n"
                     "    if a.onlem:",
                     "    _baslangic_asildi_mi = _tavan_asildi_mi\n"
                     "    if False:")
    if yeni == s:
        raise SystemExit("M1 MUTANT ULASMADI — capa kirildi (kaynak degisti)")
    _yaz(yol, yeni)
    return capa


def m2_bayrak_yok_sayilir(hedef):
    """M2: `--onlem` parse edilir ama HICBIR SEY yapmaz."""
    yol = os.path.join(hedef, "defter-rotasyon.py")
    s = _oku(yol)
    yeni = s.replace("    if a.tavan_kaynaktan or a.onlem:",
                     "    a.onlem = False\n    if a.tavan_kaynaktan or a.onlem:")
    if yeni == s:
        raise SystemExit("M2 MUTANT ULASMADI — capa kirildi")
    _yaz(yol, yeni)


def m3_fail_closed_kalkar(hedef):
    """M3: esik yoksa OLCULEMEDI yerine TAVANA SESSIZCE geri dusulur."""
    yol = os.path.join(hedef, "defter-rotasyon.py")
    s = _oku(yol)
    yeni = s.replace('        if getattr(_tab_mod, "su_seviyesi", None) is None:',
                     '        if False:')
    if yeni == s:
        raise SystemExit("M3 MUTANT ULASMADI — capa kirildi")
    # Ayrica tek kaynaktan su_seviyesi'ni SIL ki kol gercekten tetiklensin.
    _yaz(yol, yeni)


def m3_taban_bozar(hedef):
    """M3'un ikinci yarisi: tek kaynakta `su_seviyesi` YOK edilir."""
    yol = os.path.join(hedef, "defter-kota-taban.py")
    s = _oku(yol)
    yeni = re.sub(r"^def su_seviyesi\(", "def _gizli_su_seviyesi(", s,
                  flags=re.M)
    if yeni == s:
        raise SystemExit("M3b MUTANT ULASMADI — `def su_seviyesi(` yok")
    # Modul govdesi kendi icinde cagiriyor olabilir -> takma ad birak.
    yeni = yeni.replace("SU_SEVIYESI_SATIR = su_seviyesi(",
                        "SU_SEVIYESI_SATIR = _gizli_su_seviyesi(")
    yeni = yeni.replace("SU_SEVIYESI_BAYT = su_seviyesi(",
                        "SU_SEVIYESI_BAYT = _gizli_su_seviyesi(")
    _yaz(yol, yeni)


def m4_ilgisiz(hedef):
    """M4 KONTROL: anlam degistirmeyen metin dokunusu."""
    yol = os.path.join(hedef, "defter-rotasyon.py")
    s = _oku(yol)
    _yaz(yol, s.replace("# === K351-31AGU — BASLANGIC BACAGININ ESIGI",
                        "# === K351-31AGU  —  BASLANGIC BACAGININ ESIGI"))


# ---------------------------------------------------------------------------
def _esikler(arac_kok):
    """Kopyadaki TEK KAYNAKTAN tavan + su seviyesi oku (ikinci kopya ACMA)."""
    import importlib.util as ilu
    yol = os.path.join(arac_kok, "defter-kota-taban.py")
    spec = ilu.spec_from_file_location("_t_%d" % abs(hash(arac_kok)), yol)
    m = ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.TAVAN_SATIR, m.su_seviyesi(m.TAVAN_SATIR)


def _defter_kur(kok, arac_kok, *, hedef_satir):
    """Satir sayisi `hedef_satir` CIVARINDA bir defter uret (kapali icerikli)."""
    defter = os.path.join(kok, "DEVAM.md")
    arsiv = os.path.join(kok, "DEVAM-ARSIV.md")
    kapali = 4
    while True:
        metin = fikstur_defter(kapali, 1)
        if len(metin.splitlines()) >= hedef_satir:
            break
        kapali += 1
        if kapali > 400:
            break
    _yaz(defter, metin)
    _yaz(arsiv, "# DEVAM ARSIV\n")
    return defter, arsiv


def batarya(arac_kok, etiket):
    kok = tempfile.mkdtemp(prefix="k351-onlem-")
    try:
        tavan, su = _esikler(arac_kok)
        # Tavanin ALTINDA, su seviyesinin USTUNDE bir defter: (su, tavan] araligi.
        hedef = (su + tavan) // 2
        defter, arsiv = _defter_kur(kok, arac_kok, hedef_satir=hedef)
        satir0 = len(_oku(defter).splitlines())
        bayt0 = os.path.getsize(defter)
        print("  · esikler: tavan=%d su_seviyesi=%d | defter=%d satir / %d bayt"
              % (tavan, su, satir0, bayt0))
        iddia("%s V0 fikstur GERCEKTEN (su, tavan] araliginda" % etiket,
              su < satir0 <= tavan, (su, satir0, tavan))

        print("\n[V1] TABAN — `--tavan-kaynaktan` tavan altinda HICBIR SEY tasimaz")
        rc, c1 = kos(arac_kok, [defter, arsiv, "--tavan-kaynaktan"])
        iddia("%s V1a rc=0" % etiket, rc == 0, (rc, c1[-400:]))
        iddia("%s V1b TASINAN=0 + DOLU_NO_OP" % etiket,
              "TASINAN=0" in c1 and "TAVAN=DOLU_NO_OP" in c1, c1[-500:])
        iddia("%s V1c dosya BIREBIR ayni" % etiket,
              os.path.getsize(defter) == bayt0, os.path.getsize(defter))

        print("\n[V2] 🔴 ONARIM — `--onlem` tavan ALTINDA GERCEKTEN tasir")
        rc, c2 = kos(arac_kok, [defter, arsiv, "--onlem"])
        iddia("%s V2a rc=0" % etiket, rc == 0, (rc, c2[-600:]))
        iddia("%s V2b ONLEM_HEDEFI basildi (esik GORUNUR)" % etiket,
              "ONLEM_HEDEFI satir=%d" % su in c2, c2[:400])
        m = re.search(r"TASINAN=(\d+)", c2)
        tasinan = int(m.group(1)) if m else -1
        iddia("%s V2c 🔴 TASINAN>0 (BASLANGIC bacagi ACILDI)" % etiket,
              tasinan > 0, (tasinan, c2[-600:]))
        satir1 = len(_oku(defter).splitlines())
        iddia("%s V2d defter KUCULDU (%d -> %d)" % (etiket, satir0, satir1),
              satir1 < satir0, (satir0, satir1))
        iddia("%s V2e DOLU_NO_OP BASILMADI" % etiket,
              "TAVAN=DOLU_NO_OP" not in c2, c2[-400:])

        print("\n[V3] 🔴 IKI BACAK TEK ESIKTEN — su seviyesine inince DURUR")
        iddia("%s V3a defter su seviyesinin ALTINA indi" % etiket,
              satir1 <= su, (satir1, su))
        rc, c3 = kos(arac_kok, [defter, arsiv, "--onlem"])
        iddia("%s V3b ikinci kosum NO-OP (rc=0, TASINAN=0)" % etiket,
              rc == 0 and "TASINAN=0" in c3, (rc, c3[-400:]))

        print("\n[V6] KONTROL — su seviyesi altindaki defterde `--onlem` NO-OP")
        bayt2 = os.path.getsize(defter)
        rc, c6 = kos(arac_kok, [defter, arsiv, "--onlem"])
        iddia("%s V6a dosya BAYT BAYT ayni" % etiket,
              os.path.getsize(defter) == bayt2, os.path.getsize(defter))
        iddia("%s V6b rc=0" % etiket, rc == 0, (rc, c6[-300:]))
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def fail_closed_vakasi(arac_kok, etiket, *, beklenen_rc):
    """V4 — tek kaynakta `su_seviyesi()` yoksa `--onlem` ne yapar?"""
    kok = tempfile.mkdtemp(prefix="k351-failclosed-")
    try:
        defter = os.path.join(kok, "DEVAM.md")
        arsiv = os.path.join(kok, "DEVAM-ARSIV.md")
        _yaz(defter, fikstur_defter(110, 1))
        _yaz(arsiv, "# DEVAM ARSIV\n")
        bayt0 = os.path.getsize(defter)
        rc, c = kos(arac_kok, [defter, arsiv, "--onlem"])
        iddia("%s V4a rc=%d (beklenen %d)" % (etiket, rc, beklenen_rc),
              rc == beklenen_rc, (rc, c[-500:]))
        if beklenen_rc == 4:
            iddia("%s V4b OLCULEMEDI + `su_seviyesi()` ADIYLA anildi" % etiket,
                  "OLCULEMEDI" in c and "su_seviyesi()" in c, c[-500:])
            iddia("%s V4c dosyaya DOKUNULMADI" % etiket,
                  os.path.getsize(defter) == bayt0, os.path.getsize(defter))
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def menzil_siniri():
    """V5 — `--onlem` kota KAPISININ hukmunu DEGISTIRMEZ."""
    print("\n[V5] MENZIL SINIRI — kilit hala YALNIZ tavandan turer")
    if not os.path.isfile(KOTA_KAPISI):
        iddia("V5 OLCULEMEDI: defter-kota-kapisi.py YOK", False, KOTA_KAPISI)
        return
    s = _oku(KOTA_KAPISI)
    iddia("V5a kota kapisi `onlem` SOZCUGUNU HIC anmiyor",
          "onlem" not in s.lower(), [l for l in s.splitlines()
                                     if "onlem" in l.lower()][:3])
    r = _oku(ROTASYON)
    iddia("V5b `--onlem` kolu yalniz BASLANGIC yuklemini degistirir"
          " (tavan_asi_mi'ye dokunmaz)",
          "_baslangic_asildi_mi = _su_seviyesi_ustunde_mi" in r
          and "tavan_asi_mi" not in r.split("if a.onlem:")[1][:900],
          r.split("if a.onlem:")[1][:400] if "if a.onlem:" in r else "YOK")


def main():
    print("=" * 74)
    print("K351-31AGU — ROTASYON BASLANGIC BACAGI ONARIM ESIGINDEN TURER")
    print("=" * 74)

    kok = tempfile.mkdtemp(prefix="k351-gercek-")
    try:
        gercek = arac_kopyasi(kok)
        print("\n--- GERCEK ARAC (mutantsiz) ---")
        batarya(gercek, "G")
        menzil_siniri()
        print("\n[V4] 🔴 FAIL-CLOSED — tek kaynakta esik YOKSA tavana DUSMEZ")
        fc = arac_kopyasi(kok + "-fc", yama=m3_taban_bozar)
        fail_closed_vakasi(fc, "G", beklenen_rc=4)
    finally:
        shutil.rmtree(kok, ignore_errors=True)
        shutil.rmtree(kok + "-fc", ignore_errors=True)

    taban_dusen = len(_KALAN)
    print("\nTABAN: VAKA=%d DUSEN=%d" % (len(_GECEN) + len(_KALAN), taban_dusen))
    if taban_dusen:
        print("HUKUM=KIRMIZI rc=1 (taban kirmizi — mutantlar KOSULMADI)")
        return 1

    print("\n" + "=" * 74)
    print("MUTANTLAR — her biri HEDEF vakasini ADIYLA oldurmeli")
    print("=" * 74)
    mutantlar = [
        ("M1 BASLANGIC kapisi CEZA esigine geri konur", m1_baslangic_geri,
         "V2c", True),
        ("M2 `--onlem` bayragi yok sayilir", m2_bayrak_yok_sayilir,
         "V2c", True),
        ("M4 KONTROL: ilgisiz metin dokunusu", m4_ilgisiz, "-", False),
    ]
    mutant_sonuc = []
    for ad, yama, hedef, olmeli in mutantlar:
        print("\n--- MUTANT %s (hedef vaka: %s) ---" % (ad, hedef))
        onceki = len(_KALAN)
        kok = tempfile.mkdtemp(prefix="k351-mut-")
        try:
            arac = arac_kopyasi(kok, yama=yama)
            batarya(arac, "M")
        finally:
            shutil.rmtree(kok, ignore_errors=True)
        dusen = len(_KALAN) - onceki
        oldu = dusen > 0
        uygun = (oldu == olmeli)
        mutant_sonuc.append((ad, oldu, olmeli, uygun, dusen))
        print("  -> DUSEN=%d (beklenen: %s)"
              % (dusen, "KIRMIZI" if olmeli else "YESIL"))
        # Mutant dususlerini taban hukmune KARISTIRMA.
        del _KALAN[onceki:]

    # M3: fail-closed kolu kaldirilir -> V4 rc=4 yerine 0/başka olur.
    print("\n--- MUTANT M3 fail-closed kolu kaldirilir (hedef vaka: V4a) ---")
    onceki = len(_KALAN)
    kok = tempfile.mkdtemp(prefix="k351-mut3-")
    try:
        def _m3(h):
            m3_taban_bozar(h)
            m3_fail_closed_kalkar(h)
        arac = arac_kopyasi(kok, yama=_m3)
        fail_closed_vakasi(arac, "M", beklenen_rc=4)
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    dusen3 = len(_KALAN) - onceki
    mutant_sonuc.append(("M3 fail-closed kolu kaldirilir", dusen3 > 0, True,
                         dusen3 > 0, dusen3))
    print("  -> DUSEN=%d (beklenen: KIRMIZI)" % dusen3)
    del _KALAN[onceki:]

    print("\n" + "=" * 74)
    uyumsuz = [m for m in mutant_sonuc if not m[3]]
    for ad, oldu, olmeli, uygun, dusen in mutant_sonuc:
        print("  %s %s -> %s (beklenen %s)"
              % ("✅" if uygun else "❌", ad,
                 "KIRMIZI" if oldu else "YESIL",
                 "KIRMIZI" if olmeli else "YESIL"))
    print("VAKA=%d DUSEN=0 MUTANT=%d/%d KONTROL=%s"
          % (len(_GECEN), len(mutant_sonuc) - len(uyumsuz), len(mutant_sonuc),
             "YESIL" if not uyumsuz else "KIRMIZI"))
    if uyumsuz:
        print("HUKUM=KIRMIZI rc=1 (mutant beklentisi TUTMADI)")
        return 1
    print("HUKUM=YESIL rc=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
