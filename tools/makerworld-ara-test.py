#!/usr/bin/env python3
"""KABUL TESTI — makerworld-ara.py `marka_geciyor()` \\bMARKA\\b kelime-siniri filtresi.

Amac: marka adi alt-dize olarak baska kelimenin icinde geciyorsa (Oxford, afford) ELENMELI;
tam kelime olarak geciyorsa (Ford Mustang) GECMELI. Turkce-duyarli (İ/I dogru kucultulur).

Kosum:  python3 tools/makerworld-ara-test.py   -> tum satirlar ok, son 'TUM TESTLER GECTI'.
ONCE-KIRMIZI: duz alt-dize eslemesi (`marka in metin`) kullanan bir filtre 'Oxford'/'afford'
satirlarinda KIRMIZI yanardi (yanlislikla ALAKALI sayardi)."""
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("makerworld_ara", os.path.join(_HERE, "makerworld-ara.py"))
ara = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ara)

# (marka, metin, beklenen_gecer?, aciklama)
CASES = [
    # --- ELENMELI (alt-dize gurultusu) ---
    ("ford", "Oxford pencil holder",              False, "Ox+ford alt-dize -> alakasiz"),
    ("ford", "Things you can afford to print",     False, "af+ford alt-dize"),
    ("ford", "Bradford city keychain",             False, "Brad+ford alt-dize"),
    ("opel", "Please open the box lid",            False, "opel != open (harf farki degil ama kelime siniri)"),
    ("mini", "aluminium bracket",                  False, "alu+mini+um alt-dize"),
    ("audi", "audiophile speaker stand",           False, "audi+ophile alt-dize"),

    # --- GECMELI (tam kelime) ---
    ("ford", "Ford Mustang wheel cap",             True,  "Ford tam kelime"),
    ("ford", "grille for FORD Focus MK2",          True,  "buyuk harf FORD"),
    ("ford", "Focus (ford) cup holder",            True,  "parantez icinde tam kelime"),
    ("renault", "Renault Clio armrest",            True,  "tam kelime"),
    ("bmw", "BMW E46 vent clip",                   True,  "tam kelime"),
    ("mini", "Mini Cooper badge holder",           True,  "Mini tam kelime"),
    ("opel", "Opel Astra hub cap",                 True,  "Opel tam kelime"),
    # slug/etiket uzerinde de calismali (bosluga cevrilmis slug + etiketler cagirandan gelir)
    ("audi", "custom part", False, "metinde audi yok -> elenir"),
]

# marka birden cok metinde aranabildigini de dogrula (baslik yok, etiket var)
MULTI = [
    ("audi", ("generic bracket", "audi a4 b8", "some-slug"), True, "etikette tam kelime -> gecer"),
    ("audi", ("audiophile", "hifi speaker", "audiophile-stand"), False, "hicbir alanda tam kelime yok"),
]


def main():
    fails = []
    for marka, metin, bek, aciklama in CASES:
        got = ara.marka_geciyor(marka, metin)
        durum = "ok" if got == bek else "HATA"
        if got != bek:
            fails.append((marka, metin, got, bek, aciklama))
        print("  %-4s marka=%-8s %-38r -> %-5s (bek %s)  # %s"
              % (durum, marka, metin[:36], got, bek, aciklama))
    for marka, metinler, bek, aciklama in MULTI:
        got = ara.marka_geciyor(marka, *metinler)
        durum = "ok" if got == bek else "HATA"
        if got != bek:
            fails.append((marka, metinler, got, bek, aciklama))
        print("  %-4s marka=%-8s %-38r -> %-5s (bek %s)  # %s"
              % (durum, marka, str(metinler)[:36], got, bek, aciklama))

    print()
    if fails:
        print("BASARISIZ — %d senaryo yanlis:" % len(fails))
        for f in fails:
            print("  x", f)
        sys.exit(1)
    print("TUM TESTLER GECTI (%d senaryo)." % (len(CASES) + len(MULTI)))


if __name__ == "__main__":
    main()
