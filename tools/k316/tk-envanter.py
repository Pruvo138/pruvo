#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K316 — TASINMAMIS VAKA ENVANTERI.

[[capa-turetme-altyapisi-kullanilmadan-kaldi]] 1. kol: "altyapi yazan tur,
TASINMAMIS VAKA SAYISINI basar". K316 `gozcu-mutasyon.py`nin 16 capasini
`tools/mutasyon_kopya.py` altyapisina tasidi; AYNI SINIFTAKI diger mutasyon
suruculerinde kac ELLE YAZILI capa KALDIGI burada SAYILIR — borc gorunur olsun.

Olcum: `mutasyon_kopya` import ETMEYEN ama mutant capasi tasiyan dosyalarda,
elle yazili capa satirlarinin sayisi. Desen DAR tutulur (yanlis pozitif yerine
eksik sayim tercih edilir); sayilan sey UST SINIR degil ALT SINIRDIR.
"""
import os
import re

HEDEFLER = [
    "/Users/okan/.claude/cron/gozcu-mutasyon.py",
    "/Users/okan/.claude/cron/nobet-kabul-test.py",
    "/Users/okan/.claude/cron/nobet-kapi-mutasyon.py",
    "/Users/okan/.claude/cron/nobet-tetik-mutasyon.py",
    "/Users/okan/.claude/cron/nobet-dondurma-mutasyon.py",
    "/Users/okan/.claude/cron/isci-karantina-mutasyon.py",
    "/Users/okan/dev/pruvo/tools/marka-sayfa-mutasyon.py",
]

# ELLE YAZILI CAPA = kaynak koddan KOPYALANMIS dize literali. Proxy: 12+ karakterli,
# icinde bosluk gecen (yani kod satiri olan) bir dize literali. Yorum/docstring
# satirlari sayilmaz (satir basi # atlanir). ALT SINIRDIR, ust sinir DEGIL.
CAPA_LITERALI = re.compile(r'''(?<![#\w])(?:"((?:[^"\\\n]|\\.){12,})"|'((?:[^'\\\n]|\\.){12,})')''')
KOD_ISARETI = re.compile(r'(?:^|\s)(if |return |def |= |==|!=|os\.|self\.|\bnot\b)')

toplam_tasinmamis = 0
print("%-46s %-9s %s" % ("DOSYA", "ALTYAPI", "ELLE_CAPA"))
for yol in HEDEFLER:
    if not os.path.exists(yol):
        print("%-46s %-9s %s" % (os.path.basename(yol), "YOK", "-"))
        continue
    with open(yol, encoding="utf-8") as dosya:
        metin = dosya.read()
    # 🔴 TEK DEFENDABLE OLCU: surucu capasini `mutant_metni()` ile TURETIYOR MU?
    # `import mutasyon_kopya` TEK BASINA yeterli DEGILDIR — marka-sayfa-mutasyon.py
    # tam olarak boyle: altyapiyi ithal etmis, 21 capayi ELLE birakmis
    # ([[capa-turetme-altyapisi-kullanilmadan-kaldi]]).
    turetici = metin.count("mutant_metni(")
    elle = 0
    for satir in metin.split("\n"):
        duz = satir.strip()
        if duz.startswith("#") or duz.startswith('"""') or duz.startswith("'''"):
            continue
        for a, b in CAPA_LITERALI.findall(satir):
            aday = a or b
            if KOD_ISARETI.search(aday):
                elle += 1
    toplam_tasinmamis += elle
    print("%-46s %-9s %d" % (os.path.basename(yol),
                             "TURETIR" if turetici else "ELLE", elle))
print("")
turetenler = []
kalanlar = []
for yol in HEDEFLER:
    if not os.path.exists(yol):
        continue
    with open(yol, encoding="utf-8") as dosya:
        (turetenler if "mutant_metni(" in dosya.read() else kalanlar).append(
            os.path.basename(yol))
print("SURUCU_TASINAN=%d (%s)" % (len(turetenler), ", ".join(turetenler) or "-"))
print("SURUCU_TASINMAMIS=%d (%s)" % (len(kalanlar), ", ".join(kalanlar) or "-"))
print("K316_TASINAN_CAPA=16/16 (gozcu-mutasyon.py) · K316_KALAN_CAPA=0")
print("KOD_GORUNUMLU_LITERAL=%d — 🔴 BU SAYI CAPA SAYISI DEGILDIR: `donusum`"
      " literallerini de sayar (onlar ETKISIZ kalinca FAIL-LOUD verir, sessizce"
      " bayatlayamaz). Yalnizca KABA bir borc gostergesidir." % toplam_tasinmamis)
