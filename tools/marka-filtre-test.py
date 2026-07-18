#!/usr/bin/env python3
r"""KABUL TESTI — marka TAM-KELIME (\bMARKA\b) arama filtresi.

Sorun (Ford derin pull, 2026-07-18): marka aramasi basligi ALT-DIZE eslesen
alakasiz urunleri getiriyor ("Oxford", "afford", "Food" -> 896/1214 gurultu);
maraba kendi filtresini kurmak zorunda kaldi. Cozum: printables-api.py'de
marka_kelime_gecer(baslik, marka) -> baslikta marka Unicode kelime siniriyla
(\bMARKA\b, Turkce-duyarli, buyuk/kucuk duyarsiz) geciyorsa True.

Bu test:
  1. marka_kelime_gecer'i karisik basliklarla sinar (Ford GECER, Oxford/afford/Food ELENIR).
  2. printables-ara.py VE thing-ara.py'nin ayni fonksiyonu KULLANDIGINI dogrular
     (kaynak-grep: filtre gercekten baglanmis mi — birinde unutulursa yakalanir).

Calistir:  python3 tools/marka-filtre-test.py   (cikis 0 = gecti, 1 = kaldi)
"""
import importlib.util
import os
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
FAILS = []


def _load(fname, modname):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(DIR, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(ad, kosul):
    if not kosul:
        FAILS.append(ad)
        print("TEST KALDI:", ad, file=sys.stderr)


pr = _load("printables-api.py", "pr_api")
gec = pr.marka_kelime_gecer

# --- 1. Fonksiyon davranisi: karisik baslik listesi ---------------------------
# "Ford" markasi: tam kelime GECER, alt-dize ELENIR.
GECMELI_FORD = [
    "Ford Focus orta konsol duzenleyici",
    "ford fiesta debriyaj pedali",          # kucuk harf
    "FORD Transit kapi tutamaci",           # buyuk harf
    "Kapak (Ford Focus icin)",              # parantez/kelime-ortasi degil
    "Ford-Focus vites korukleme",           # tire ile sinir
    "yeni ford",                            # baslik sonu
]
ELENMELI_FORD = [
    "Oxford pen holder",                    # alt-dize: ...ford...
    "I can afford this bracket",            # alt-dize: af-ford
    "Food container lid",                   # hic ilgisiz
    "Stanford lab mount",                   # alt-dize
    "Bradford bike clip",                   # alt-dize
    "fordable box",                         # kelime-ici (ford + able)
]
for t in GECMELI_FORD:
    check("Ford GECMELI: %r" % t, gec(t, "Ford") is True)
for t in ELENMELI_FORD:
    check("Ford ELENMELI: %r" % t, gec(t, "Ford") is False)

# Turkce-duyarli buyuk/kucuk: "BMW" vs govde; ve Turkce I/İ katmani
check("BMW tam kelime gecer", gec("BMW e46 far braketi", "BMW") is True)
check("BMW alt-dize elenir", gec("ABMWX rastgele", "BMW") is False)

# Cok kelimeli marka: "Alfa Romeo" tam ifade
check("Alfa Romeo gecer", gec("Alfa Romeo Giulia kalorifer", "Alfa Romeo") is True)
check("Alfa (tek) Romeosuz gecmez-degil", gec("Alfa Romeo Giulia", "Alfa") is True)  # "Alfa" tek kelime de var
check("Romeo baska baglamda elenir", gec("Romeo and Juliet statue", "Alfa Romeo") is False)

# Kisa/bos marka -> filtre uygulanmaz (asiri eleme onlenir): True
check("bos marka filtre yok", gec("herhangi baslik", "") is True)
check("tek harf marka filtre yok", gec("X-wing", "X") is True)

# Turkce karakterli marka kelime siniri (ı ç ş): "Şahin" govde icinde degilse elenir
check("Turkce marka tam kelime", gec("Şahin torpido kapagi", "Şahin") is True)
check("Turkce marka alt-dize elenir", gec("Kırşahinler kutu", "Şahin") is False)

# --- 2. Iki arama araci da fonksiyonu KULLANIYOR mu (kaynak-grep) --------------
for f in ("printables-ara.py", "thing-ara.py"):
    src = open(os.path.join(DIR, f), encoding="utf-8").read()
    check("%s marka_kelime_gecer cagiriyor" % f, "marka_kelime_gecer" in src)
    check("%s --tam-kelime bayragi var" % f, "--tam-kelime" in src)

if FAILS:
    print("\n%d KONTROL KALDI" % len(FAILS), file=sys.stderr)
    sys.exit(1)
print("TEST GECTI")
sys.exit(0)
