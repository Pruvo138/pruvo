#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Marka x platform -> indirilebilir CSV (Excel/Sheets). Tum markalar, urun sayisina gore.
Hucre: sayi = eklenen | 0 = arandi, urun yok | bos = HIC aranmamis (arastirma eksik)."""
import csv
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import marka_katla as mk  # noqa: E402

DEFTER = "/Users/okan/dev/pruvo/.marka-kapsama.json"
OUT = "/Users/okan/Desktop/pruvo-marka-platform.csv"
PLATS = ["Printables", "Thingiverse", "MakerWorld"]


def oku():
    for _ in range(6):
        try:
            return json.load(open(DEFTER, encoding="utf-8"))
        except Exception:
            time.sleep(0.2)
    return {}


# Satır evreni = KANONIK TANINMIS_MARKALAR; ham defter markaKatla ile katlanır, çöp görünmez.
d = mk.kanonik_kapsama(oku())


def hucre(m, p):
    return mk.hucre_deger(d.get(m, {}).get(p))


def toplam(m):
    return sum(v for p in PLATS for v in [hucre(m, p)] if v)


def durum(m):
    vals = {p: hucre(m, p) for p in PLATS}
    kirmizi, sari = mk.durum_hucreler(vals, PLATS)
    notlar = []
    if kirmizi:
        notlar.append("hic aranmadi: " + ", ".join(kirmizi))
    if sari:
        notlar.append("az kalmis: " + ", ".join(sari))
    return " | ".join(notlar) if notlar else "dengeli"


markalar = sorted(d.keys(), key=lambda m: -toplam(m))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Marka", "Printables", "Thingiverse", "MakerWorld", "Toplam", "Eksik / dengesiz"])
    for m in markalar:
        cells = []
        for p in PLATS:
            v = hucre(m, p)
            cells.append("" if v is None else v)  # bos = hic aranmamis
        w.writerow([m] + cells + [toplam(m), durum(m)])

print("YAZILDI: %s  (%d marka)" % (OUT, len(markalar)))
