#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CURUTME 12 — FLIP PROVASI: OZET_TEMSIL_SURUM 2 -> 3 yapilinca CI'daki ozet tuketicileri
ne yapiyor?

NEDEN ([[kapi-yan-etkisi-gizli-onkosul]]): `yeni` anahtari v3'te `yeniRef` olur ve kapak
URL'si kisalir. ozet.json'u HAM okuyan (cozucuden gecirmeyen) her kapi/olcum bu gun
sessizce vakuma duser ya da kirmizi yanar. Bayrak flip'i "yalniz bir sabit" degildir.

Yordam: build.py'de sabit 3 yapilir, CI'daki ozet tuketicileri KOSULUR, rc'ler TABAN ile
karsilastirilir, sonra dosya GERI YUKLENIR.
"""
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLS = os.path.join(KOK, "tools")
BUILD = os.path.join(TOOLS, "build.py")
GEC = tempfile.mkdtemp(prefix="curut-flip-")

KAPILAR = [
    ("build --sadece-ozet", ["python3", BUILD, "--sadece-ozet", "--katalog",
                             os.path.join(KOK, "urunler.json"), "--cikti",
                             os.path.join(GEC, "ozet.json")]),
    ("ozet-temsil-test.js", ["node", os.path.join(TOOLS, "ozet-temsil-test.js")]),
    ("edge-kart-kapisi.py", ["python3", os.path.join(TOOLS, "edge-kart-kapisi.py")]),
    ("vitrin-siralama-test.js", ["node", os.path.join(TOOLS, "vitrin-siralama-test.js")]),
    ("eski-fiyat-test.py", ["python3", os.path.join(TOOLS, "eski-fiyat-test.py")]),
    ("marka-sayac-kapisi.py", ["python3", os.path.join(TOOLS, "marka-sayac-kapisi.py")]),
    ("is-akisi-kapisi.py", ["python3", os.path.join(TOOLS, "is-akisi-kapisi.py")]),
    ("deploy-aclik-kapisi.py", ["python3", os.path.join(TOOLS, "deploy-aclik-kapisi.py")]),
    ("faz3-yuk.js", ["node", os.path.join(TOOLS, "faz3-yuk.js")]),
    ("ozet-bayt-atifi.py (FAZ 1 olcumu)", ["python3", os.path.join(TOOLS, "ozet-bayt-atifi.py")]),
]


def kos(argv):
    try:
        r = subprocess.run(argv, capture_output=True, text=True, cwd=KOK, timeout=900)
    except subprocess.TimeoutExpired:
        return None, "ZAMAN ASIMI"
    s = [x for x in (r.stdout or "").strip().split("\n") if x.strip()]
    son = s[-1][:110] if s else (r.stderr or "").strip().split("\n")[-1][:110]
    return r.returncode, son


def tur(etiket):
    print("--- %s" % etiket)
    out = {}
    for ad, argv in KAPILAR:
        rc, son = kos(argv)
        out[ad] = rc
        print("   %-34s rc=%s | %s" % (ad, rc, son))
    return out


print("=== CURUTME 12 — bayrak FLIP provasi (2 -> 3)\n")
taban = tur("TABAN: OZET_TEMSIL_SURUM = 2")
print("")
yedek = os.path.join(GEC, "build.py.yedek")
shutil.copy2(BUILD, yedek)
try:
    with open(BUILD, encoding="utf-8") as f:
        src = f.read()
    capa = "OZET_TEMSIL_SURUM = 2"
    if src.count(capa) != 1:
        print("OLCULEMEDI: bayrak capasi %d adet" % src.count(capa))
        sys.exit(2)
    with open(BUILD, "w", encoding="utf-8") as f:
        f.write(src.replace(capa, "OZET_TEMSIL_SURUM = 3", 1))
    flip = tur("FLIP: OZET_TEMSIL_SURUM = 3")
finally:
    shutil.copy2(yedek, BUILD)

print("")
print("=== KARSILASTIRMA (taban rc -> flip rc)")
bozulan = []
for ad, _ in KAPILAR:
    t, f = taban[ad], flip[ad]
    isaret = "  " if t == f else "  <<< DEGISTI"
    if t == 0 and f != 0:
        bozulan.append(ad)
        isaret = "  <<< FLIP BUNU KIRIYOR"
    print("   %-34s %s -> %s%s" % (ad, t, f, isaret))
print("")
print("FLIP'IN KIRDIGI KAPI SAYISI: %d" % len(bozulan))
for a in bozulan:
    print("   ✘ %s" % a)
shutil.rmtree(GEC, ignore_errors=True)
