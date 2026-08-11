#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CURUTME 10 — kosullu kart alanlarinin GERCEK katalogdaki dagilimi.

Kabul testi fiksturunde HANGI alan BIRLIKTELIKLERI hic denenmiyor? Temsil hatalari
konum-bagimlidir; bir konum ciftini hic doldurmayan fikstur o cifti kor birakir.
"""
import json
import os

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
with open(os.path.join(KOK, "urunler.json"), encoding="utf-8") as f:
    urunler = json.load(f)

tf = [p for p in urunler if p.get("tavsiyeFilament")]
kf = [p for p in urunler if p.get("konfigur")]
tur = [p for p in urunler if p.get("tur") == "fiziksel"]
ikisi = [p for p in urunler if p.get("tavsiyeFilament") and p.get("konfigur")]
ucu = [p for p in urunler
       if p.get("tavsiyeFilament") and p.get("konfigur") and p.get("tur") == "fiziksel"]

print("katalog: %d urun" % len(urunler))
print("tavsiyeFilament (konum 10) tasiyan   : %d" % len(tf))
print("konfigur        (konum 11) tasiyan   : %d" % len(kf))
print("tur=fiziksel    (konum 9)  tasiyan   : %d" % len(tur))
print("tavsiyeFilament + konfigur BIRLIKTE  : %d  ornek: %s"
      % (len(ikisi), [p.get("id") for p in ikisi[:3]]))
print("ucu BIRDEN                           : %d" % len(ucu))
print("")
print("KABUL TESTI FIKSTURU (tools/ozet-temsil-test.js KENAR dizisi):")
print("  {tur, tavsiyeFilament} VAR · {konfigur, tur} VAR · "
      "{tavsiyeFilament + konfigur BIRLIKTE} -> YOK")
print("  eski_fiyat (konum 8) tasiyan fikstur/urun -> YOK (katalogda da 0)")
