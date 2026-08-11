#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CURUTME 04 — EKSEN 6: v3'te sepet FIYAT/BEYAN nobetcisi (edge-kart-kapisi.py) ne goruyor?

SORU: `tur` gibi bir fiyat/beyan alani KART_OZETI'de dururken TEL uzerinde (ozet.json
temsili) ya da ISTEMCI COZUCUSUNDE kaybolursa, sepet nobetcisi KIRMIZI yanar mi?

Uc mutant, her biri diske UYGULANIR ve uc kapi birden olculur:
  W1  ISTEMCI (index.html ozetAc) `tur` alanini geri ACMAZ  -> panel +%84 sisik fiyat
  W2  DERLEME (ozet_karti_sikistir) telde 8'inci konumdan sonrasini KESER
  W3  KONTROL: kart_ozeti'den `tur` silinir (nobetcinin KENDI M-A mutanti)

Her mutant icin rc: edge-kart-kapisi.py · ozet-temsil-test.js · build.py --sadece-ozet
(0 = yesil/gecti, !=0 = kirmizi). Dosyalar finally'de GERI YUKLENIR.
"""
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLS = os.path.join(KOK, "tools")
INDEX = os.path.join(KOK, "index.html")
BUILD = os.path.join(TOOLS, "build.py")
GEC = tempfile.mkdtemp(prefix="curut-korluk-")

MUTANTLAR = [
    ("W1 ISTEMCI: ozetAc `tur` alanini geri ACMAZ", INDEX,
     '        if(i < alanlar.length && (i < 8 || deger !== null)){ out[alanlar[i]] = deger; }',
     '        if(i < alanlar.length && (i < 8 || deger !== null) && alanlar[i] !== "tur"){ out[alanlar[i]] = deger; }'),
    ("W2 DERLEME: telde 8'inci konumdan sonrasi KESILIR", BUILD,
     '    son = max((i for i, alan in enumerate(OZET_KART_ALANLARI) if alan in kart), default=-1)',
     '    son = min(7, max((i for i, alan in enumerate(OZET_KART_ALANLARI) if alan in kart), default=-1))'),
    ("W3 KONTROL: kart_ozeti'den `tur` silindi (nobetcinin M-A mutanti)", BUILD,
     '    if p.get("tur") == "fiziksel":\n        kart["tur"] = "fiziksel"\n', ""),
]


def kos(ad, argv):
    r = subprocess.run(argv, capture_output=True, text=True, cwd=KOK)
    ozet = (r.stdout or "").strip().split("\n")
    son = ozet[-1][:110] if ozet else ""
    return r.returncode, son


def olc(etiket):
    a = kos("edge", ["python3", os.path.join(TOOLS, "edge-kart-kapisi.py")])
    b = kos("temsil", ["node", os.path.join(TOOLS, "ozet-temsil-test.js")])
    c = kos("build", ["python3", BUILD, "--sadece-ozet", "--katalog",
                      os.path.join(KOK, "urunler.json"), "--cikti",
                      os.path.join(GEC, "o.json"), "--ozet-surum", "3"])
    print("  %-58s edge-kart-kapisi rc=%d | ozet-temsil-test rc=%d | build(v3) rc=%d"
          % (etiket, a[0], b[0], c[0]))
    print("       edge  : %s" % a[1])
    print("       temsil: %s" % b[1])
    if c[0] != 0:
        print("       build : %s" % c[1])
    return {"edge": a[0], "temsil": b[0], "build": c[0]}


def main():
    print("=== CURUTME 04 — sepet fiyat/beyan nobetcisi v3 telini goruyor mu?\n")
    print("YAPISAL OLCUM: edge-kart-kapisi.py kaynaginda 'index.html' gecisi: %d, "
          "'ozet.json' ARTEFAKTINI okuma: %d"
          % (open(os.path.join(TOOLS, "edge-kart-kapisi.py"), encoding="utf-8").read()
             .count("index.html"),
             open(os.path.join(TOOLS, "edge-kart-kapisi.py"), encoding="utf-8").read()
             .count("render_ozet")))
    print("")
    taban = olc("TABAN (mutasyonsuz)")
    sonuc = []
    for ad, yol, eski, yeni in MUTANTLAR:
        yedek = os.path.join(GEC, os.path.basename(yol) + ".yedek")
        shutil.copy2(yol, yedek)
        try:
            with open(yol, encoding="utf-8") as f:
                src = f.read()
            if src.count(eski) != 1:
                print("  %-58s OLCULEMEDI: capa %d adet" % (ad, src.count(eski)))
                continue
            with open(yol, "w", encoding="utf-8") as f:
                f.write(src.replace(eski, yeni, 1))
            sonuc.append((ad, olc(ad)))
        finally:
            shutil.copy2(yedek, yol)
    print("")
    print("TABAN: edge=%d temsil=%d build=%d" % (taban["edge"], taban["temsil"], taban["build"]))
    kor = [ad for ad, s in sonuc if s["edge"] == 0]
    print("Sepet nobetcisinin KOR kaldigi mutant sayisi: %d/%d" % (len(kor), len(sonuc)))
    for ad in kor:
        print("   ✘ KOR: %s" % ad)
    yakalayan = [ad for ad, s in sonuc if s["temsil"] != 0 or s["build"] != 0]
    print("Baska kapinin (temsil testi / build fail-closed) yakaladigi: %d/%d"
          % (len(yakalayan), len(sonuc)))
    shutil.rmtree(GEC, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
