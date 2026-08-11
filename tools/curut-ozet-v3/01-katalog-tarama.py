#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CURUTME 01 — v3 temsilinin GERCEK katalogdaki saldiri yuzeyini sayar.

Olculen eksenler:
  (a) kapak URL'si "://" TASIMAYAN urun  -> v3'te istemci onegi YANLIS ekler / build kirmizi
  (b) kapak URL'si onekle baslayip kalani BOS olan urun (onegin TAM kendisi)
  (c) kapak URL'si onege BENZEYEN ama farkli konak
  (d) JS'te FALSY id (bos dize, 0, false) -> istemci havuz cozumu SESSIZ duser
  (e) Object.prototype anahtari olan id (constructor/__proto__/toString/...) -> istemci
      havuzda YANLIS nesne bulur ve karta onu koyar
  (f) MUKERRER id
Cikti: sayilar. Kod DEGISTIRMEZ.
"""
import json
import os

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ONEK = "https://media.pruvo3d.com/urunler/"
PROTO = {"constructor", "__proto__", "toString", "valueOf", "hasOwnProperty",
         "isPrototypeOf", "propertyIsEnumerable", "toLocaleString", "__defineGetter__",
         "__defineSetter__", "__lookupGetter__", "__lookupSetter__"}

with open(os.path.join(KOK, "urunler.json"), encoding="utf-8") as f:
    urunler = json.load(f)

a = []      # "://" yok ama BOS da degil
bos = 0     # kapak hic yok
b = []
c = []
d = []
e = []
gorulen = {}
mukerrer = []
for p in urunler:
    g = (p.get("gorseller") or [None])[0]
    if g is None or g == "":
        bos += 1
    elif not isinstance(g, str):
        a.append((p.get("id"), repr(g)))
    elif "://" not in g:
        a.append((p.get("id"), g))
    elif g == ONEK:
        b.append(p.get("id"))
    elif g.startswith("https://media.pruvo3d.com/") and not g.startswith(ONEK):
        c.append((p.get("id"), g))
    i = p.get("id")
    if i == "" or i == 0 or i is False:
        d.append(repr(i))
    if isinstance(i, str) and i in PROTO:
        e.append(i)
    if i in gorulen:
        mukerrer.append(i)
    else:
        gorulen[i] = 1

print("katalog urun sayisi: %d" % len(urunler))
print("(a) kapak '://' TASIMAYAN (bos olmayan): %d  ornek: %s" % (len(a), a[:3]))
print("    kapak HIC yok (None/bos): %d" % bos)
print("(b) kapak onegin TAM kendisi: %d  ornek: %s" % (len(b), b[:3]))
print("(c) ayni konak farkli yol (onek TASIMAZ): %d  ornek: %s" % (len(c), c[:3]))
print("(d) JS'te FALSY id: %d  ornek: %s" % (len(d), d[:3]))
print("(e) Object.prototype anahtari olan id: %d  ornek: %s" % (len(e), e[:3]))
print("(f) MUKERRER id: %d  ornek: %s" % (len(mukerrer), mukerrer[:3]))
