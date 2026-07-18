#!/usr/bin/env python3
"""KABUL TESTI — cults3d-api.py `satilabilir()` FAIL-CLOSED beyaz-liste davranisi.

Cults3D bir PAZAR: VARSAYILAN lisans "Cults - Private use" (kod: cults_cu) TICARI DEGIL, ayrica
ucretli "Cults - Standard use" (cults_su) satis lisansi var. Yanlis satarsak telif ihlali. Bu
yuzden fail-closed beyaz liste SART: sadece CC-BY / BY-SA / BY-ND / CC0 satilabilir; Cults tescilli
+ NC + tanimadigimiz HER lisans -> satilamaz.

Girdi tablosu Cults3D'nin GERCEK lisanslarindan (hem kanonik `code`, hem insan-okur `name(locale:EN)`
formu) — canli API 401 (kimlik gerektiriyor) oldugu icin degerler resmi dok + cults3d.com/licenses'tan.

Kosum:  python3 tools/cults3d-lisans-test.py
Cikti:  tum satirlar 'ok', son satir 'TUM TESTLER GECTI' (basarisizsa exit 1 + neyin patladigi).

ONCE-KIRMIZI kaniti: FAIL-OPEN bir satilabilir() (bilinmeyen/Cults/tescilli -> True) bu testte
KIRMIZI yanardi (cults_cu / cults_su / uydurma satirlari). Ayrica "cc_by_nd"yi bloklayan (ND'yi
yanlislikla eleyen) ya da varsayilan "Cults - Private use"i geciren bir kapi da KIRMIZI olurdu."""
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_API = os.path.join(_HERE, "cults3d-api.py")
_spec = importlib.util.spec_from_file_location("cults3d_api", _API)
c3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(c3)

# (license girdisi, beklenen satilabilir?, beklenen cc_turu, aciklama)
CASES = [
    # --- SATILAMAZ: Cults tescilli (fail-closed'un tuttuklari) ---
    ("cults_cu",                                          False, None, "Cults - Private use kodu (VARSAYILAN, en yaygin)"),
    ("Cults - Private use",                               False, None, "Cults - Private use adi (kisisel, ticari degil)"),
    ("cults_cu_nd",                                       False, None, "Cults private use turevi (no-deriv)"),
    ("cults_su",                                          False, None, "Cults - Standard use kodu (UCRETLI ticari satis lisansi)"),
    ("Cults - Standard use",                             False, None, "Cults standard use adi (dosyayi biz satin almadik)"),
    # --- SATILAMAZ: NonCommercial ---
    ("cc_by_nc",                                          False, None, "CC BY-NC kodu"),
    ("cc_by_nc_sa",                                       False, None, "CC BY-NC-SA kodu"),
    ("cc_by_nc_nd",                                       False, None, "CC BY-NC-ND kodu"),
    ("Creative Commons - Attribution - Noncommercial",   False, None, "NC adi (Attribution + Noncommercial)"),
    ("Creative Commons - Attribution - Noncommercial - Share Alike", False, None, "NC-SA adi"),
    # --- SATILAMAZ: bos / bilinmeyen ---
    ("",                                                 False, None, "bos -> bilinmiyor -> atla"),
    (None,                                               False, None, "None -> atla"),
    ("All Rights Reserved",                              False, None, "taninmayan -> FAIL-CLOSED"),
    ("uydurma-lisans",                                   False, None, "taninmayan -> FAIL-CLOSED"),

    # --- SATILABILIR: CC beyaz liste (kod formu) ---
    ("cc0",                                              True,  None,           "CC0 kodu (Public Domain, atif yok)"),
    ("cc_by",                                            True,  "CC BY 4.0",    "CC-BY kodu"),
    ("cc_by_sa",                                         True,  "CC BY-SA 4.0", "CC-BY-SA kodu"),
    ("cc_by_nd",                                         True,  "CC BY-ND 4.0", "CC-BY-ND kodu (ND SATILABILIR)"),

    # --- SATILABILIR: CC beyaz liste (insan-okur name formu) ---
    ("Creative Commons - Public Domain",                 True,  None,           "CC0 adi -> atif yok"),
    ("Creative Commons - Attribution",                   True,  "CC BY 4.0",    "CC-BY adi"),
    ("Creative Commons - Attribution - Share Alike",     True,  "CC BY-SA 4.0", "CC-BY-SA adi"),
    ("Creative Commons - Attribution - No Derivatives",  True,  "CC BY-ND 4.0", "CC-BY-ND adi"),
]


def main():
    fails = []
    for lic, bek_sat, bek_cc, aciklama in CASES:
        try:
            sat = c3.satilabilir(lic)
            cc = c3.cc_turu(lic)
        except Exception as e:                                   # noqa: BLE001
            fails.append((lic, "PATLADI %r" % e, aciklama))
            print("  PATLADI  %-46r -> %r" % (lic, e))
            continue
        ok_sat = (sat == bek_sat)
        ok_cc = (cc == bek_cc)
        durum = "ok" if (ok_sat and ok_cc) else "HATA"
        if not (ok_sat and ok_cc):
            fails.append((lic, "sat=%s(bek %s) cc=%r(bek %r)" % (sat, bek_sat, cc, bek_cc), aciklama))
        print("  %-4s %-48r sat=%-5s cc=%-12r  # %s"
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
