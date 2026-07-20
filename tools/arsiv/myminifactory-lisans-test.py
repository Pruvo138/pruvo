#!/usr/bin/env python3
# EMEKLI - Okan 19 Tem: bu platformda arama YAPILMAZ (parity-backfill'den cikarildi).
"""KABUL TESTI — myminifactory-api.py `satilabilir()` FAIL-CLOSED beyaz-liste davranisi.

MMF lisanslari IKI gercek bicimde gelir (canli olcum 2026-07-18, object-licensing sayfasi +
gercek urun sayfalari + "introducing the CC licenses" blogu):
  CIPLAK CC   : "BY-NC-SA" (obje 98393), "BY", "BY-SA", "BY-ND", "BY-NC", "BY-NC-ND", "CC0"
  BETIMLEYICI : "MyMiniFactory - Credit - Remix - Noncommercial" (obje 58065), "... - Commercial"
  TESCILLI    : "Standard Digital File Store License", "MyMiniFactory Exclusivity License",
                "Official Content License", "All Rights Reserved"
Varsayilan lisans CC BY-NC-SA 4.0 (NC -> SATILAMAZ). DIKKAT: "MyMiniFactory" alt-dizesi TEK BASINA
reddettirmez — betimleyici CC bicimi de "MyMiniFactory -" ile baslar; ayrim COMMERCIAL/NONCOMMERCIAL
tokeninde.

Kosum:  python3 tools/myminifactory-lisans-test.py
Cikti:  tum satirlar 'ok', son satir 'TUM TESTLER GECTI' (basarisizsa exit 1 + neyin patladigi).

ONCE-KIRMIZI kaniti: FAIL-OPEN bir satilabilir() (bilinmeyen/Standard/Exclusive/betimleyici-NC ->
True) bu testte KIRMIZI yanardi. Ayrica "MyMiniFactory" alt-dizesine bakip HEPSINI reddeden naif bir
kapi, gecerli "MyMiniFactory - Credit - Remix - Commercial" satirinda KIRMIZI yanardi (yanlis eleme)."""
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_API = os.path.join(_HERE, "myminifactory-api.py")
_spec = importlib.util.spec_from_file_location("myminifactory_api", _API)
mmf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mmf)

# (license girdisi, beklenen satilabilir?, beklenen cc_turu, aciklama)
CASES = [
    # --- SATILAMAZ (fail-closed'in tuttuklari) ---
    ("Standard Digital File Store License",            False, None, "MMF ucretli store lisansi (no commercial)"),
    ("MyMiniFactory Exclusivity License",              False, None, "MMF ozel/kapali host lisansi"),
    ("Official Content License",                       False, None, "marka/resmi icerik — All Rights Reserved"),
    ("All Rights Reserved",                            False, None, "taninmayan/kapali -> atla"),
    ("MyMiniFactory - Credit - Remix - Noncommercial", False, None, "BETIMLEYICI NC (gercek: obje 58065)"),
    ("MyMiniFactory - Credit - Noncommercial",         False, None, "betimleyici NC, remix yok"),
    ("BY-NC-SA",                                       False, None, "ciplak NC (gercek: obje 98393; MMF varsayilani)"),
    ("BY-NC",                                          False, None, "NonCommercial"),
    ("BY-NC-ND",                                       False, None, "NonCommercial + NoDerivatives"),
    ("Attribution-NonCommercial-ShareAlike 4.0 International", False, None, "tam ad NC -> collapsed yakalar"),
    ("Non-Commercial",                                 False, None, "tireli yazim da NC"),
    ("",                                               False, None, "bos lisans -> bilinmiyor -> atla"),
    (None,                                             False, None, "None lisans -> atla"),
    ("uydurma-lisans",                                 False, None, "taninmayan -> FAIL-CLOSED"),

    # --- SATILABILIR (whitelist) — MMF CIPLAK CC formu ---
    ("BY",                                             True,  "CC BY 4.0",    "CC-BY (ciplak)"),
    ("BY-SA",                                          True,  "CC BY-SA 4.0", "CC-BY-SA ciplak"),
    ("BY-ND",                                          True,  "CC BY-ND 4.0", "CC-BY-ND ciplak"),
    ("CC0",                                            True,  None,           "Public Domain (atif yok)"),
    ("Public Domain",                                  True,  None,           "Public Domain metni"),

    # --- SATILABILIR — MMF BETIMLEYICI ticari formu ---
    ("MyMiniFactory - Credit - Remix - Commercial",    True,  "CC BY 4.0",    "betimleyici ticari: Credit+Remix+Commercial"),
    ("MyMiniFactory - Credit - Commercial",            True,  "CC BY-ND 4.0", "betimleyici ticari, remix yok -> ND"),

    # --- ileri-uyum: onekli / tam-ad gelirse de dogru ---
    ("CC-BY",                                          True,  "CC BY 4.0",    "onekli form da satilabilir"),
    ("CC-BY-NC",                                       False, None,           "onekli NC yine satilamaz"),
    ("Attribution 4.0 International",                   True,  "CC BY 4.0",    "tam ad CC-BY (Attribution=BY)"),
    ("GPL 3.0",                                        True,  None,           "ticari-serbest yazilim lisansi"),
]

# licenses[] flag capraz-reddi (ticari_flags) — SADECE reddeder, asla kurtarmaz.
FLAG_CASES = [
    ([{"type": "commercial-use", "value": True}, {"type": "store", "value": False}],  True,  "commercial acik, store kapali"),
    ([{"type": "commercial-use", "value": False}],                                    False, "commercial kapali -> reddet"),
    ([{"type": "commercial-use", "value": True}, {"type": "store", "value": True}],   False, "store acik (ucretli) -> reddet"),
    ([{"type": "commercial-use", "value": True}, {"type": "exclusivity", "value": True}], False, "exclusive -> reddet"),
    ([{"type": "remix", "value": True}],                                              None,  "commercial-use anahtari yok -> karar yok"),
    ([],                                                                              None,  "bos -> bilgi yok"),
    (None,                                                                            None,  "yok -> bilgi yok"),
]


def main():
    fails = []
    for lic, bek_sat, bek_cc, aciklama in CASES:
        try:
            sat = mmf.satilabilir(lic)
            cc = mmf.cc_turu(lic)
        except Exception as e:                                   # noqa: BLE001
            fails.append((lic, "PATLADI %r" % e, aciklama))
            print("  PATLADI  %-42r -> %r" % (lic, e))
            continue
        ok = (sat == bek_sat) and (cc == bek_cc)
        if not ok:
            fails.append((lic, "sat=%s(bek %s) cc=%r(bek %r)" % (sat, bek_sat, cc, bek_cc), aciklama))
        print("  %-4s %-46r sat=%-5s cc=%-12r  # %s"
              % ("ok" if ok else "HATA", lic, sat, cc, aciklama))

    print("  --- ticari_flags (licenses[] capraz-reddi) ---")
    for flags, bek, aciklama in FLAG_CASES:
        got = mmf.ticari_flags(flags)
        ok = (got == bek)
        if not ok:
            fails.append((flags, "flag=%r (bek %r)" % (got, bek), aciklama))
        print("  %-4s ticari_flags(%-46r) -> %-5s (bek %s)  # %s"
              % ("ok" if ok else "HATA", str(flags)[:44], got, bek, aciklama))

    print()
    if fails:
        print("BASARISIZ — %d senaryo yanlis:" % len(fails))
        for lic, ne, aciklama in fails:
            print("  x %r -> %s  (%s)" % (lic, ne, aciklama))
        sys.exit(1)
    print("TUM TESTLER GECTI (%d senaryo)." % (len(CASES) + len(FLAG_CASES)))


if __name__ == "__main__":
    main()
