#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gercek wrangler `d1 execute --json` cevabi — D1 okuyucularinin TEK ORTAK FIKSTURU.

NEDEN VAR (17 Eki 2026, BaBa 17:4x kurali): `tools/inis-sayac-oku.py` kabul testini
yalniz sqlite fiksturuyle gecti ve canli D1'de 25 inis varken `TOPLAM=0` basti — test
gercek wrangler zarfiyla HIC konusmamisti. Her okuyucuya elle yazilmis zarf, ayni korlugu
okuyucu sayisi kadar cogaltir. Sekil TEK dosyada durur (`fikstur/wrangler-d1-zarf.json`,
canli cevaptan yakalandi); okuyucu testleri satirlarini bu zarfin `results`ina koyar.
Kapsam kapisi: `tools/d1-zarf-fikstur-kapisi.py` (D1 sonucu ayristiran her arac, bu
modulu kullanan bir kabul testine bagli olmak ZORUNDA).

Kullanim (testte):
    import d1_zarf_fikstur as Z
    raw = Z.zarf([{"kaynak": "google", "kampanya": "x", "n": 3}])   # list[dict]
    metin = Z.zarf_metni([...])                                       # wrangler stdout'u
"""
import copy
import json
import os

YOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fikstur", "wrangler-d1-zarf.json")


def sablon():
    """Canli cevaptan yakalanan zarf (results bos). Sekil bozuksa ValueError."""
    with open(YOL, encoding="utf-8") as f:
        veri = json.load(f)
    if (not isinstance(veri, list) or len(veri) != 1 or not isinstance(veri[0], dict)
            or not isinstance(veri[0].get("results"), list) or "meta" not in veri[0]):
        raise ValueError("wrangler zarf fiksturu beklenen sekilde degil: %s" % YOL)
    return veri


def zarf(satirlar):
    """Satirlari gercek zarfin `results`ina koyar -> wrangler --json cevabinin ayni sekli."""
    z = copy.deepcopy(sablon())
    z[0]["results"] = [dict(s) for s in satirlar]
    z[0]["meta"]["rows_read"] = len(z[0]["results"])
    return z


def zarf_metni(satirlar):
    """`zarf()`'in wrangler stdout'u gibi JSON metni."""
    return json.dumps(zarf(satirlar), ensure_ascii=False, indent=2)
