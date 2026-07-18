#!/usr/bin/env python3
"""KABUL TESTI — makerworld-api.py `satilabilir()` FAIL-CLOSED beyaz-liste davranisi.

MakerWorld'un lisanslari Printables'tan FARKLI string doner: CC'yi CIPLAK verir ("BY",
"BY-SA"... — "CC-" oneki YOK) + kendi tescilli lisanslari ("Standard Digital File License",
"MakerWorld Exclusive License"). Bu yuzden Printables lisans kapisi MakerWorld'e OLDUGU GIBI
uymaz (Printables kodu ciplak "BY"yi satilamaz sayardi -> gecerli CC-BY urunleri kaybederdik;
tersinden Printables'in "CC-BY" whitelist'i MakerWorld'un tescilli lisansini yakalamazdi).

Girdi tablosu MakerWorld API'nin GERCEKTEN dondurdugu `license` degerlerinden turetildi
(canli olcum, 2026-07-18, 16 marka/terim, ~480 model) + spec'in istedigi kenar durumlar.

Kosum:  python3 tools/makerworld-lisans-test.py
Cikti:  tum satirlar 'ok', son satir 'TUM TESTLER GECTI' (basarisizsa exit 1 + neyin patladigi).

ONCE-KIRMIZI kaniti: FAIL-OPEN bir satilabilir() (bilinmeyen/Standard/Exclusive -> True) bu testte
KIRMIZI yanardi (Standard/Exclusive/Community/uydurma satirlari). Ayrica Printables'in kapisini
(CC- oneki bekleyen) buraya baglasan ciplak "BY"/"BY-SA"/"BY-ND" satirlari KIRMIZI olurdu."""
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_API = os.path.join(_HERE, "makerworld-api.py")
_spec = importlib.util.spec_from_file_location("makerworld_api", _API)
mw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mw)

# (license girdisi, beklenen satilabilir?, beklenen cc_turu, aciklama)
CASES = [
    # --- SATILAMAZ (fail-closed'in tuttuklari) ---
    ("Standard Digital File License",                 False, None, "MakerWorld tescilli satis lisansi (en yaygin)"),
    ("Standard Digital File License - Community Use",  False, None, "Community Use varyanti da kisitli"),
    ("MakerWorld Exclusive License",                   False, None, "MakerWorld ozel/kapali lisans"),
    ("BY-NC",                                          False, None, "NonCommercial"),
    ("BY-NC-SA",                                       False, None, "NonCommercial + ShareAlike"),
    ("BY-NC-ND",                                       False, None, "NonCommercial + NoDerivatives"),
    ("",                                               False, None, "bos lisans -> bilinmiyor -> atla"),
    (None,                                             False, None, "None lisans -> atla"),
    ("uydurma-lisans",                                 False, None, "taninmayan -> FAIL-CLOSED"),
    ("All Rights Reserved",                            False, None, "taninmayan -> atla"),

    # --- SATILABILIR (whitelist) — MakerWorld CIPLAK CC formu ---
    ("BY",                                             True,  "CC BY 4.0",    "CC-BY (MakerWorld ciplak formu)"),
    ("BY-SA",                                          True,  "CC BY-SA 4.0", "CC-BY-SA ciplak"),
    ("BY-ND",                                          True,  "CC BY-ND 4.0", "CC-BY-ND ciplak"),
    ("CC0",                                            True,  None,           "Public Domain (atif yok)"),

    # --- ileri-uyum: CC- onekli gelirse de dogru ---
    ("CC-BY",                                          True,  "CC BY 4.0",    "onekli form da satilabilir"),
    ("CC-BY-NC",                                       False, None,           "onekli NC yine satilamaz"),
]


def main():
    fails = []
    for lic, bek_sat, bek_cc, aciklama in CASES:
        try:
            sat = mw.satilabilir(lic)
            cc = mw.cc_turu(lic)
        except Exception as e:                                   # noqa: BLE001
            fails.append((lic, "PATLADI %r" % e, aciklama))
            print("  PATLADI  %-40r -> %r" % (lic, e))
            continue
        ok_sat = (sat == bek_sat)
        ok_cc = (cc == bek_cc)
        durum = "ok" if (ok_sat and ok_cc) else "HATA"
        if not (ok_sat and ok_cc):
            fails.append((lic, "sat=%s(bek %s) cc=%r(bek %r)" % (sat, bek_sat, cc, bek_cc), aciklama))
        print("  %-4s %-42r sat=%-5s cc=%-12r  # %s"
              % (durum, lic, sat, cc, aciklama))

    print()
    if fails:
        print("BASARISIZ — %d/%d senaryo yanlis:" % (len(fails), len(CASES)))
        for lic, ne, aciklama in fails:
            print("  x %r -> %s  (%s)" % (lic, ne, aciklama))
        sys.exit(1)
    print("TUM TESTLER GECTI (%d senaryo)." % len(CASES))


if __name__ == "__main__":
    main()
