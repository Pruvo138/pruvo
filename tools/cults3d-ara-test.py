#!/usr/bin/env python3
# ⛔ ÇAĞIRMA — EMEKLİ (Okan 18 Tem: Cults3D rate-limit/429 yüzünden çıkarıldı)
"""KABUL TESTI — cults3d-ara.py `marka_alakali()` \\bMARKA\\b kelime-siniri filtresi.

cults3d-ara.py markanin ORTAK filtresini printables-api.marka_kelime_gecer() ile uygular (INLINE
DEGIL — import). marka_alakali() baslik+etiket+slug'i birlestirip o ortak filtreye verir. Amac:
marka adi alt-dize olarak baska kelimenin icinde geciyorsa (Oxford, afford) ELENMELI; tam kelime
olarak geciyorsa (Ford Mustang) GECMELI. Turkce-duyarli.

Kosum:  python3 tools/cults3d-ara-test.py   -> tum satirlar ok, son 'TUM TESTLER GECTI'.
ONCE-KIRMIZI: duz alt-dize eslemesi (`marka in metin`) kullanan bir filtre 'Oxford'/'afford'
satirlarinda KIRMIZI yanardi (yanlislikla ALAKALI sayardi).

NOT: cults3d-ara.py import edilirken cults3d-api.py + printables-api.py yuklenir (ikisi de import
aninda AG CAGRISI/kimlik YAPMAZ) — test agsiz calisir."""
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("cults3d_ara", os.path.join(_HERE, "cults3d-ara.py"))
ara = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ara)

# (marka, baslik, beklenen_gecer?, aciklama)  — tek metin (baslik) uzerinde
CASES = [
    # --- ELENMELI (alt-dize gurultusu) ---
    ("ford", "Oxford pencil holder",              False, "Ox+ford alt-dize -> alakasiz"),
    ("ford", "Things you can afford to print",     False, "af+ford alt-dize"),
    ("ford", "Bradford city sign",                 False, "Brad+ford alt-dize"),
    ("mini", "aluminium bracket",                  False, "alu+mini+um alt-dize"),
    ("audi", "audiophile speaker stand",           False, "audi+ophile alt-dize"),

    # --- GECMELI (tam kelime) ---
    ("ford", "Ford Mustang wheel cap",             True,  "Ford tam kelime"),
    ("ford", "grille for FORD Focus MK2",          True,  "buyuk harf FORD"),
    ("ford", "Focus (ford) cup holder",            True,  "parantez icinde tam kelime"),
    ("renault", "Renault Clio armrest",            True,  "tam kelime"),
    ("bmw", "BMW E46 vent clip",                   True,  "tam kelime"),
    ("mini", "Mini Cooper badge holder",           True,  "Mini tam kelime"),
    ("audi", "custom bracket",                     False, "metinde audi yok -> elenir"),
]

# baslik+etiket+slug birlesimi: tam kelime alanlarin HERHANGI birinde gecmeli
MULTI = [
    ("audi", "generic bracket", ["audi a4 b8"], "some-slug",       True,  "etikette tam kelime -> gecer"),
    ("audi", "audiophile mount", ["hifi speaker"], "audiophile-stand", False, "hicbir alanda tam kelime yok"),
    ("ford", "vent clip", [], "ford-focus-mk3-vent",               True,  "slug'da tam kelime (tire -> bosluk)"),
]


def main():
    fails = []
    for marka, baslik, bek, aciklama in CASES:
        got = ara.marka_alakali(marka, baslik)
        durum = "ok" if got == bek else "HATA"
        if got != bek:
            fails.append((marka, baslik, got, bek, aciklama))
        print("  %-4s marka=%-8s %-38r -> %-5s (bek %s)  # %s"
              % (durum, marka, baslik[:36], got, bek, aciklama))
    for marka, baslik, tags, slug, bek, aciklama in MULTI:
        got = ara.marka_alakali(marka, baslik, tags, slug)
        durum = "ok" if got == bek else "HATA"
        if got != bek:
            fails.append((marka, (baslik, tags, slug), got, bek, aciklama))
        print("  %-4s marka=%-8s %-38r -> %-5s (bek %s)  # %s"
              % (durum, marka, ("%s|%s|%s" % (baslik, tags, slug))[:36], got, bek, aciklama))

    print()
    if fails:
        print("BASARISIZ — %d senaryo yanlis:" % len(fails))
        for f in fails:
            print("  x", f)
        sys.exit(1)
    print("TUM TESTLER GECTI (%d senaryo)." % (len(CASES) + len(MULTI)))


if __name__ == "__main__":
    main()
