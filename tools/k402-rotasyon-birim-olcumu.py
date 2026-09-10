#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K402 — `defter-rotasyon.py` TASIMA BIRIMI ONCULUNUN OLCUMU (curutme kanidi).

NEDEN VAR: 10 Eyl 2026'da ucuncu kez su HIPOTEZ kuruldu —
  "rotasyon araci `TASINAN_MADDE=0` basiyor, cunku TASIMA BIRIMI YANLIS
   SEVIYEDE: veto BLOK duzeyinde veriliyor, oysa kapanmis maddeler blok
   icinde AYRI AYRI ayrilabilir."
Hipotez UCUNCU tekrarinda sinif kapisi yazilmasi istendi. Bu betik hipotezi
KOSARAK olcer ve CURUTUR: madde granulu ZATEN VAR (K243 + K324 ile kuruldu)
ve KAPSAYICI blogun ICINDEN de madde cikarabiliyor.

Prose bir curutme bayatlar ve dorduncu kez yeniden kurulur
([[aracin-teshis-cumlesi-olcum-degil]]); bu yuzden curutme CALISTIRILABILIR.

BAYRAK YOKTUR (argparse yok): bu bir OLCUM betigidir, kapi DEGILDIR — CI
kapsam sozlesmesine iddia EKLEMEZ.

Kosum:  python3 tools/k402-rotasyon-birim-olcumu.py
Cikti son satiri: ONCUL=CURUDU|AYAKTA
rc: 0 = olcum kosuldu (hukum son satirda), 2 = olcum KOSULAMADI.

🔴 GERCEK `DEVAM.md`/`DEVAM-ARSIV.md` UZERINDE HICBIR SEY YAZILMAZ. Fikstur
koku `tempfile.mkdtemp()` altina CIVILENIR ve `assert` ile dogrulanir; temizlik
yalniz o kok altinda yapilir (DISK KURALI: makinede iz birakma).
"""
import collections
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

_BURASI = os.path.dirname(os.path.abspath(__file__))
ARAC = os.path.join(_BURASI, "defter-rotasyon.py")


def _arac_modulu():
    """Aracin KENDISINI modul olarak yukler — kova adlari IKINCI KEZ YAZILMAZ
    ([[ikiz-tanim-sessiz-ayrisma]]); hepsi `defter-rotasyon.py`'dan TURER."""
    spec = importlib.util.spec_from_file_location("dr_k402", ARAC)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul

# --- FIKSTUR: kabul metninin birebir tarif ettigi defter -------------------
# "bir blokta 3 KAPALI + 1 ACIK madde varken arac 3'u tasir, ACIK olani
#  BIRAKIR, blok basligi + acik madde defterde kalir".
# Ek olarak IKI kontrol bolgesi:
#   * KAPSAYICI blok (`## ACIK KALEMLER`) icinde 1 KAPALI + 1 ACIK madde
#     -> kapsayici BUTUN olarak tasinmaz ama ICINDEKI kapali madde CIKAR.
#   * Defterin IKINCI notasyonu: kapanis HALI OLMAYAN olgu/rapor satirlari
#     -> `SINIFLANAMAZ` (fail-closed) ve DEFTERDE KALIR.
FIKSTUR_DEFTER = """# DEVAM — sentetik fikstur (K402)

Baslik bolgesi. Asla tasinmaz.

## 🔧 SENTETIK TUR — 3 KAPALI + 1 ACIK
- **K900 KAPANDI** kabul 5/5, mutant 3/3, merge `aaa111`.
- **K901 KAPANDI** kapi rc=0, iddia 12/12.
- ✅ **K902 KAPANDI** batarya 8/8 yesil.
- 🔧 **K903** acik kalem, olculmedi.

## ACIK KALEMLER
- **K910 KAPANDI** kapsayici ICINDE duran kapali madde.
- 🔴 **K911** kapsayici icinde duran acik madde.

## 🔧 NOTASYON-2 — kapanis HALI olmayan olgu satirlari
- **YAYIN:** run `34417809688` — `deploy` success · `yayin` success · SKIPPED=0.
- **KAYIP ADAYI 6 → 1.** Menzil daraltma (1.657.912 → 26.760 aday).
- 🔧 **K904** acik kalem, olculmedi.
"""

FIKSTUR_ARSIV = ("# DEVAM-ARSIV — sentetik (K402)\n\n"
                 "## eski govde\n- eski satir 1\n- eski satir 2\n")

# Fiksturde TASINMASI beklenen maddelerin ilk satirlari (BIREBIR).
BEKLENEN_TASINAN = (
    "- **K900 KAPANDI** kabul 5/5, mutant 3/3, merge `aaa111`.",
    "- **K901 KAPANDI** kapi rc=0, iddia 12/12.",
    "- ✅ **K902 KAPANDI** batarya 8/8 yesil.",
    "- **K910 KAPANDI** kapsayici ICINDE duran kapali madde.",
)
# Fiksturde DEFTERDE KALMASI beklenen maddeler (BIREBIR).
BEKLENEN_KALAN = (
    "- 🔧 **K903** acik kalem, olculmedi.",
    "- 🔴 **K911** kapsayici icinde duran acik madde.",
    "- **YAYIN:** run `34417809688` — `deploy` success · `yayin` success · SKIPPED=0.",
    "- **KAYIP ADAYI 6 → 1.** Menzil daraltma (1.657.912 → 26.760 aday).",
    "- 🔧 **K904** acik kalem, olculmedi.",
)


def _fikstur_kur():
    """Fikstur kokunu tempfile ALTINA civiler ve dogrular (yikici yuk YOK)."""
    kok = tempfile.mkdtemp(prefix="k402-oncul-")
    gercek = os.path.realpath(kok)
    tmp = os.path.realpath(tempfile.gettempdir())
    # 🔴 Temizlik menzili: kok GERCEKTEN tempfile altinda mi? Degilse
    # hicbir sey silinmez — testin yuku YIKICI OLAMAZ.
    assert gercek.startswith(tmp + os.sep), (
        "fikstur koku tempfile altinda DEGIL: %s" % gercek)
    defter = os.path.join(kok, "DEVAM.md")
    arsiv = os.path.join(kok, "DEVAM-ARSIV.md")
    with open(defter, "w", encoding="utf-8") as f:
        f.write(FIKSTUR_DEFTER)
    with open(arsiv, "w", encoding="utf-8") as f:
        f.write(FIKSTUR_ARSIV)
    return kok, defter, arsiv


def _temizle(kok):
    gercek = os.path.realpath(kok)
    tmp = os.path.realpath(tempfile.gettempdir())
    assert gercek.startswith(tmp + os.sep), gercek
    shutil.rmtree(gercek, ignore_errors=True)


def _eksen_a_fikstur():
    """EKSEN A — kabul fiksturu: 3 KAPALI tasinir, ACIK olan KALIR.

    Donus: (gecti_mi, [satir, ...])
    """
    rapor = []
    kok, defter, arsiv = _fikstur_kur()
    try:
        p = subprocess.run([sys.executable, ARAC, defter, arsiv,
                            "--tarih", "2026-09-10"],
                           capture_output=True, text=True)
        cikti = p.stdout
        with open(defter, encoding="utf-8") as f:
            defter_son = f.read()
        with open(arsiv, encoding="utf-8") as f:
            arsiv_son = f.read()
    finally:
        _temizle(kok)

    ozet = [s for s in cikti.splitlines() if s.startswith("TASINAN=")]
    ozet_satir = ozet[-1] if ozet else "(TASINAN satiri BASILMADI)"
    rapor.append("  rc=%d" % p.returncode)
    rapor.append("  %s" % ozet_satir)
    for s in cikti.splitlines():
        if s.startswith("MADDE_KOVALARI"):
            rapor.append("  %s" % s)

    tasinan_madde = None
    for parca in ozet_satir.split():
        if parca.startswith("TASINAN_MADDE="):
            tasinan_madde = int(parca.split("=", 1)[1])
    rapor.append("  TASINAN_MADDE olculen=%s (oncul '0 basiyor' diyordu)"
                 % tasinan_madde)

    # Arsivde BIREBIR var mi, defterden BIREBIR dustu mu?
    eksik_arsivde = [s for s in BEKLENEN_TASINAN if s not in arsiv_son]
    hala_defterde = [s for s in BEKLENEN_TASINAN if s in defter_son]
    dusen_kalan = [s for s in BEKLENEN_KALAN if s not in defter_son]
    rapor.append("  arsivde BULUNAMAYAN tasinan=%d · defterde HALA duran"
                 " tasinan=%d · defterden HAKSIZ dusen=%d"
                 % (len(eksik_arsivde), len(hala_defterde), len(dusen_kalan)))
    for s in eksik_arsivde + hala_defterde + dusen_kalan:
        rapor.append("    ! %s" % s[:90])

    gecti = (p.returncode == 0 and tasinan_madde == len(BEKLENEN_TASINAN)
             and not eksik_arsivde and not hala_defterde and not dusen_kalan)
    return gecti, rapor


def _eksen_b_canli_defter():
    """EKSEN B — CANLI defterin kova dokumu (SALT OKUMA, hicbir sey yazilmaz).

    `TASINAN_MADDE=0`in sebebi arac mi, yoksa defterde kapali icerik OLMAMASI
    mi? Kovalar SAYIYLA cevaplar.
    """
    rapor = []
    dr = _arac_modulu()

    canli = os.path.join(os.path.dirname(_BURASI), "DEVAM.md")
    if not os.path.exists(canli):
        rapor.append("  CANLI DEFTER YOK (%s) — eksen ATLANDI" % canli)
        return None, rapor

    with open(canli, "rb") as f:
        metin = f.read().decode("utf-8")
    _bas, bloklar = dr._bloklari_ayir(metin)
    kova = collections.Counter()
    ornekler = []
    kapsayici = 0
    for blok in bloklar:
        if dr._blok_kapsayici_mi(blok):
            kapsayici += 1
        if not dr._tasinir_mi(blok):
            dr._maddeleri_isle(blok["govde"], kova, ornekler)
    rapor.append("  %s" % dr._kova_satiri(kova, kapsayici, len(bloklar)))
    rapor.append("  SINIFLANAMAZ maddelerin SEBEP yuzeyi:")
    sebepli = 0
    for sinif, ilk, sebep in ornekler:
        if sebep:
            sebepli += 1
        rapor.append("    [%s] sebep=%s | %s"
                     % (sinif, "VAR" if sebep else "YOK", ilk[:70]))
    rapor.append("  sebep BASILAN=%d · sebep BASILMAYAN=%d"
                 % (sebepli, len(ornekler) - sebepli))
    return kova, rapor


def main():
    if not os.path.exists(ARAC):
        print("OLCUM KOSULAMADI: %s yok" % ARAC, file=sys.stderr)
        return 2

    print("=" * 70)
    print("K402 — TASIMA BIRIMI ONCULU: OLCUM")
    print("=" * 70)
    print("ONCUL: 'veto BLOK duzeyinde veriliyor; kapanmis maddeler blok")
    print("        icinde AYRI AYRI ayrilamiyor' -> bu yuzden TASINAN_MADDE=0")
    print("")
    print("EKSEN A — kabul fiksturu (3 KAPALI + 1 ACIK, tempfile kokunde):")
    a_gecti, a_rapor = _eksen_a_fikstur()
    for s in a_rapor:
        print(s)
    print("  EKSEN A: %s" % ("madde granulu CALISIYOR" if a_gecti
                             else "madde granulu CALISMIYOR"))
    print("")
    print("EKSEN B — canli defterin kova dokumu (salt okuma):")
    kova, b_rapor = _eksen_b_canli_defter()
    for s in b_rapor:
        print(s)
    if kova is not None:
        kapali = kova.get(_arac_modulu().MADDE_KAPALI, 0)
        print("  EKSEN B: KAPALI=%d -> `TASINAN_MADDE=0` %s"
              % (kapali,
                 "DOGRU CEVAP (tasinacak kapali icerik YOK)" if kapali == 0
                 else "ARIZA (kapali icerik VAR ama tasinmiyor)"))
    print("")
    # Oncul ancak madde granulu CALISMIYORSA ayakta kalir.
    hukum = "CURUDU" if a_gecti else "AYAKTA"
    print("ONCUL=%s" % hukum)
    return 0


if __name__ == "__main__":
    sys.exit(main())
