#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Marka x platform -> indirilebilir CSV (Excel/Sheets). Tum markalar, urun sayisina gore.
Hucre: sayi = eklenen | 0 = arandi, urun yok | bos = HIC aranmamis (arastirma eksik)."""
import csv
import json
import os
import time

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


d = oku()


def hucre(m, p):
    k = d.get(m, {}).get(p)
    if not k:
        return None
    if k.get("eklenen", 0) > 0:
        return k["eklenen"]
    if k.get("taranan", 0) > 0:
        return 0
    return None


def toplam(m):
    return sum(v for p in PLATS for v in [hucre(m, p)] if v)


def durum(m):
    vals = {p: hucre(m, p) for p in PLATS}
    tot = sum(v for v in vals.values() if v)
    hic = [p for p in PLATS if vals[p] is None]
    ekli = {p: v for p, v in vals.items() if v}
    notlar = []
    if hic and tot >= 3:
        notlar.append("hic aranmadi: " + ", ".join(hic))
    if len(ekli) >= 2:
        en = max(ekli.values())
        if en >= 10:
            az = [p for p, v in ekli.items() if v < en * 0.5]
            if az:
                notlar.append("az kalmis: " + ", ".join(az))
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
