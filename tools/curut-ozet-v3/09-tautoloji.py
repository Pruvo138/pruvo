#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CURUTME 09 — EKSEN 1: kayipsizlik iddiasi cozucuyu KENDISIYLE mi karsilastiriyor?

Iki AYRI kayipsizlik iddiasi var:
  (I)  BUILD ICI (render_ozet): `ozet_temsil_ac(ozet)` cikitisi `kart_ozeti` ciktisiyla
       karsilastirilir. AMA `ozet_temsil_ac`/`ozet_karti_ac` build.py'nin KENDI ikinci
       cozucusudur — istemcinin (index.html ozetAc) IKIZIDIR. Simetrik bir hata iki tarafta
       da ayni sekilde yapilirsa bu kontrol YESIL kalir (TAUTOLOJI).
  (II) KABUL TESTI (ozet-temsil-test.js): CANLI index.html cozucusu + JS'te ELLE yazilmis
       `beklenenKart` capasi. Bu gercekten bagimsizdir.

Problar:
  P1  kart_ozeti aciklama kesimi 160 -> 150   : capa BAGIMSIZ mi, FIKSTUR bunu tetikliyor mu?
  P2  kart_ozeti basligi BUYUK HARFE cevirir  : bagimsiz capa yakalamali
  P3  YALNIZ Python cozucusu kaydirilir       : (I) yakalamali (asimetrik)
  P4  SIMETRIK: sikistir + Python cozucu AYNI  : (I) YESIL kalmali, (II) KIRMIZI yakmali
      sekilde ters cevrilir                     -> (I)'in tautolojik oldugunun KANITI
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
GEC = tempfile.mkdtemp(prefix="curut-taut-")

SIK_ESKI = ("    dizi = [kart.get(alan) for alan in OZET_KART_ALANLARI[:son + 1]]")
AC_ESKI = ("    for i, deger in enumerate(dizi):")

PROBLAR = [
    ("P1 kart_ozeti: aciklama kesimi 160 -> 150",
     [('        "aciklama": (p.get("aciklama") or "")[:OZET_ACIKLAMA_KES],',
       '        "aciklama": (p.get("aciklama") or "")[:150],')],
     "build ICI kontrol kendi ciktisina bakar -> YESIL bekleniyor; kabul testi ancak "
     "FIKSTURDE 150+ karakterlik aciklama varsa yakalar"),
    ("P2 kart_ozeti: baslik BUYUK HARF",
     [('        "baslik": p.get("baslik") or "",',
       '        "baslik": (p.get("baslik") or "").upper(),')],
     "bagimsiz JS capasi (beklenenKart) yakalamali"),
    ("P3 ASIMETRIK: yalniz Python cozucusu kaydirildi",
     [("    for i, deger in enumerate(dizi):\n"
       "        if i < len(alanlar) and (i < 8 or deger is not None):",
       "    for i, deger in enumerate(dizi):\n"
       "        if i < len(alanlar) and (i < 9 or deger is not None):")],
     "build ICI kontrol ASIMETRIK hatayi yakalamali (KIRMIZI bekleniyor)"),
    ("P4 SIMETRIK: sikistir + Python cozucu AYNI sekilde ters cevrildi",
     [(SIK_ESKI, SIK_ESKI + "[::-1]"),
      (AC_ESKI, "    dizi = list(dizi)[::-1]\n" + AC_ESKI)],
     "build ICI kontrol TAUTOLOJIK ise YESIL kalir; telde alanlar KARISIR ve yalniz "
     "CANLI istemci testi (II) kirmizi yakar"),
]


def kos(argv):
    r = subprocess.run(argv, capture_output=True, text=True, cwd=KOK)
    satirlar = [s for s in (r.stdout or "").strip().split("\n") if s.strip()]
    return r.returncode, (satirlar[-1][:110] if satirlar else
                          (r.stderr or "").strip().split("\n")[-1][:110])


def olc(etiket):
    b = kos(["python3", BUILD, "--sadece-ozet", "--katalog", os.path.join(KOK, "urunler.json"),
             "--cikti", os.path.join(GEC, "o.json"), "--ozet-surum", "3"])
    t = kos(["node", TEST])
    print("  %s" % etiket)
    print("      build(v3, IC KAYIPSIZLIK KONTROLU) rc=%d  | %s" % (b[0], b[1]))
    print("      ozet-temsil-test (CANLI istemci)   rc=%d  | %s" % (t[0], t[1]))
    return b[0], t[0]


print("=== CURUTME 09 — kayipsizlik iddiasinda tautoloji var mi?\n")
olc("TABAN (mutasyonsuz)")
print("")
yedek = os.path.join(GEC, "build.py.yedek")
for ad, degisimler, beklenti in PROBLAR:
    shutil.copy2(BUILD, yedek)
    try:
        with open(BUILD, encoding="utf-8") as f:
            src = f.read()
        atla = False
        for eski, yeni in degisimler:
            if src.count(eski) != 1:
                print("  %s -> OLCULEMEDI: capa %d adet" % (ad, src.count(eski)))
                atla = True
                break
            src = src.replace(eski, yeni, 1)
        if atla:
            continue
        with open(BUILD, "w", encoding="utf-8") as f:
            f.write(src)
        print("  beklenti: %s" % beklenti)
        olc(ad)
    finally:
        shutil.copy2(yedek, BUILD)
    print("")

shutil.rmtree(GEC, ignore_errors=True)
sys.exit(0)
