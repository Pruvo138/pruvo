#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CURUTME 11 — EKSEN 1 CEKIRDEGI: build ICI kayipsizlik kontrolu TAUTOLOJIK mi?

build.py `render_ozet` her build'de temsili GERI ACIP `kart_ozeti` ciktisiyla karsilastirir
ve yorum bunu "fail-closed kayipsizlik olcumu" diye beyan eder. AMA geri acan kod
(`ozet_karti_ac`) build.py'nin KENDI ikinci cozucusudur — istemcinin (index.html `ozetAc`)
IKIZI. Iki ikiz AYNI hatayi yaparsa kontrol yesil kalir.

PROBA: sikistirici ile Python cozucusu AYNI simetrik hatayi yapar (kart dizisinde 2. ve 3.
konum — `kategori` ile `marka` — takas edilir). Beklenen:
  build ICI kontrol  -> YESIL  (tautoloji KANITI)
  CANLI istemci testi -> KIRMIZI (gercek koruma BURADA)
Bu, "gelistirici temsili degistirip build.py'nin iki tarafini gunceller ama index.html'i
UNUTUR" senaryosunun tam sekli.
"""
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLS = os.path.join(KOK, "tools")
BUILD = os.path.join(TOOLS, "build.py")
TEST = os.path.join(TOOLS, "ozet-temsil-test.js")
GEC = tempfile.mkdtemp(prefix="curut-sim-")

SIK_ESKI = "    dizi = [kart.get(alan) for alan in OZET_KART_ALANLARI[:son + 1]]\n"
SIK_YENI = (SIK_ESKI
            + "    if len(dizi) > 3:\n"
              "        dizi[2], dizi[3] = dizi[3], dizi[2]\n")
AC_ESKI = "    kart = {}\n    for i, deger in enumerate(dizi):\n"
AC_YENI = ("    kart = {}\n"
           "    dizi = list(dizi)\n"
           "    if len(dizi) > 3:\n"
           "        dizi[2], dizi[3] = dizi[3], dizi[2]\n"
           "    for i, deger in enumerate(dizi):\n")


def kos(argv):
    r = subprocess.run(argv, capture_output=True, text=True, cwd=KOK)
    s = [x for x in (r.stdout or "").strip().split("\n") if x.strip()]
    return r.returncode, (s[-1][:120] if s else (r.stderr or "").strip()[-120:])


yedek = os.path.join(GEC, "build.py.yedek")
shutil.copy2(BUILD, yedek)
try:
    with open(BUILD, encoding="utf-8") as f:
        src = f.read()
    for e in (SIK_ESKI, AC_ESKI):
        if src.count(e) != 1:
            print("OLCULEMEDI: capa %d adet -> %r" % (src.count(e), e[:50]))
            sys.exit(2)
    src = src.replace(SIK_ESKI, SIK_YENI, 1).replace(AC_ESKI, AC_YENI, 1)
    with open(BUILD, "w", encoding="utf-8") as f:
        f.write(src)
    print("=== CURUTME 11 — SIMETRIK temsil hatasi (sikistirici + Python cozucu AYNI)\n")
    b = kos(["python3", BUILD, "--sadece-ozet", "--katalog", os.path.join(KOK, "urunler.json"),
             "--cikti", os.path.join(GEC, "o.json"), "--ozet-surum", "3"])
    print("  build ICI KAYIPSIZLIK KONTROLU : rc=%d | %s" % b)
    t = kos(["node", TEST])
    print("  CANLI istemci kabul testi      : rc=%d | %s" % t)
    e = kos(["python3", os.path.join(TOOLS, "edge-kart-kapisi.py")])
    print("  sepet fiyat/beyan nobetcisi    : rc=%d | %s" % e)
    print("")
    if b[0] == 0 and t[0] != 0:
        print("HUKUM: build ICI kontrol TAUTOLOJIK ✘ — simetrik hatayi GORMEDI; "
              "tek gercek koruma CANLI istemci testidir.")
    elif b[0] != 0:
        print("HUKUM: build ICI kontrol simetrik hatayi da yakaladi (tautoloji YOK).")
    else:
        print("HUKUM: HER IKI KAPI da kor -> AGIR.")
finally:
    shutil.copy2(yedek, BUILD)
    shutil.rmtree(GEC, ignore_errors=True)
