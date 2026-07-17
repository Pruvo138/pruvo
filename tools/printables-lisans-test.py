#!/usr/bin/env python3
"""KABUL TESTI — printables-api.py `satilabilir()` FAIL-CLOSED beyaz-liste davranisi.

Neden: eski `satilabilir()` FAIL-OPEN idi — "Standard Digital File" ve tanimadigi HER lisansi
SATILABILIR sayiyordu (satir yorumu bunu itiraf ediyordu). Sonuc: satilamaz urunler otomatik
stage'e giriyordu (Ford+Yamaha partilerinde maraba 5 tanesini elle yakaladi = hukuki risk).

Girdi tablosu, Printables API'nin GERCEKTEN dondurdugu `abbreviation` degerlerinden turetildi
(canli olcum, 2026-07-18) + spec'in istedigi ek kenar durumlar (bos, uydurma).

Kosum:  python3 tools/printables-lisans-test.py
Cikti:  tum satirlar 'ok', son satir 'TUM TESTLER GECTI' (basarisizsa exit 1 + neyin patladigi).

ONCE-KIRMIZI kaniti: eski (fail-open) satilabilir() ile "Standard Digital File", "OCL v1" ve
"uydurma-lisans" True donerdi -> bu test KIRMIZI yanardi. Yeni fail-closed hali ile YESIL,
satilabilir CC/GPL lisanslari True kalir (regresyon korumasi)."""
import importlib.util
import os
import sys

# printables-api.py dosya adinda '-' var -> normal import edilemez, spec ile yukle.
_HERE = os.path.dirname(os.path.abspath(__file__))
_API = os.path.join(_HERE, "printables-api.py")
_spec = importlib.util.spec_from_file_location("printables_api", _API)
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)

# (abbreviation girdisi, beklenen satilabilir?, aciklama)
# True  = ticari satisa uygun (whitelist)
# False = NC / satis-lisansi / tanimsiz (fail-closed)
CASES = [
    # --- SATILAMAZ (fail-closed'in tuttuklari) ---
    ("Standard Digital File",        False, "Printables satis-lisansi; eski kod True sayiyordu (ASIL BUG)"),
    ("Standard Digital File License", False, "ayni lisansin 'name' bicimi de satilamaz"),
    ("CC-BY-NC",                     False, "NonCommercial"),
    ("CC-BY-NC-SA",                  False, "NonCommercial + ShareAlike"),
    ("CC-BY-NC-ND",                  False, "NonCommercial + NoDerivatives"),
    ("OCL v1",                       False, "Prusa Open Community License; satis ayri anlasma ister"),
    ("",                             False, "bos lisans -> bilinmiyor -> atla"),
    (None,                           False, "None lisans -> atla"),
    ("uydurma-lisans",               False, "taninmayan lisans -> FAIL-CLOSED, satma"),
    ("All Rights Reserved",          False, "taninmayan -> atla"),

    # --- SATILABILIR (whitelist) ---
    ("CC-BY",                        True,  "Attribution"),
    ("CC-BY-SA",                     True,  "Attribution-ShareAlike"),
    ("CC-BY-ND",                     True,  "Attribution-NoDerivatives"),
    ("CC0",                          True,  "Public Domain"),
    ("Public Domain",                True,  "CC0'in 'name' bicimi"),
    ("GPL 3.0",                      True,  "GPL bosluklu surum (Printables gercek bicimi)"),
    ("GPL 2.0",                      True,  "GPL 2 bosluklu surum"),
    ("MIT",                          True,  "MIT yazilim lisansi"),
    ("BSD",                          True,  "BSD yazilim lisansi"),
]


def main():
    fails = []
    for abbr, beklenen, aciklama in CASES:
        try:
            sonuc = pr.satilabilir(abbr)
        except Exception as e:                       # noqa: BLE001
            fails.append((abbr, beklenen, "PATLADI: %r" % e, aciklama))
            print("  PATLADI  %-26r -> exception %r" % (abbr, e))
            continue
        durum = "ok" if sonuc == beklenen else "HATA"
        if sonuc != beklenen:
            fails.append((abbr, beklenen, sonuc, aciklama))
        print("  %-4s %-26r bekle=%-5s gercek=%-5s  # %s"
              % (durum, abbr, beklenen, sonuc, aciklama))

    print()
    if fails:
        print("BASARISIZ — %d/%d senaryo yanlis:" % (len(fails), len(CASES)))
        for abbr, beklenen, sonuc, aciklama in fails:
            print("  x abbr=%r  bekle=%s  gercek=%s  (%s)" % (abbr, beklenen, sonuc, aciklama))
        sys.exit(1)
    print("TUM TESTLER GECTI (%d senaryo)." % len(CASES))


if __name__ == "__main__":
    main()
