#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CURUTME 06 — EKSEN 3: 7 mutantlik batarya GERCEK mi?

Olculen sorular:
  S1  Mutant DISKE mi yaziliyor, bellege mi? Hangi dizine?
  S2  Kosum yarida kalirsa depoda ARTIK kaliyor mu? (gitignore var mi?)
  S3  Ayni saniyede ayni uzunlukta yazilan mutasyon UYGULANIYOR mu?
      ([[mutasyon-bytecode-onbellegi]] tuzagi)
  S4  Mutant ELLE uygulanirsa batarya disinda da yakalaniyor mu?
"""
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLS = os.path.join(KOK, "tools")
TEST = os.path.join(TOOLS, "ozet-temsil-test.js")
BUILD = os.path.join(TOOLS, "build.py")
INDEX = os.path.join(KOK, "index.html")
MUTANT_YOL = os.path.join(TOOLS, "_mutant-ozet-build.py")
GEC = tempfile.mkdtemp(prefix="curut-mut-")

print("=== CURUTME 06 — mutasyon bataryasi gercekligi\n")

# --------------------------------------------------------------- S1/S2 disk gozlemi
print("S1/S2 — batarya kosarken depo agacinda mutant dosya olusuyor mu?")
gorulen = {"var": False, "en_cok": 0}


def gozle(dur):
    while not dur.is_set():
        if os.path.exists(MUTANT_YOL):
            gorulen["var"] = True
            try:
                gorulen["en_cok"] = max(gorulen["en_cok"], os.path.getsize(MUTANT_YOL))
            except OSError:
                pass
        time.sleep(0.02)


dur = threading.Event()
t = threading.Thread(target=gozle, args=(dur,))
t.start()
r = subprocess.run(["node", TEST, "--mutasyon"], capture_output=True, text=True, cwd=KOK)
dur.set()
t.join()
son = [s for s in (r.stdout or "").strip().split("\n") if s.strip()][-1:]
print("   batarya rc=%d | son satir: %s" % (r.returncode, son[0] if son else ""))
print("   tools/_mutant-ozet-build.py kosum SIRASINDA gorulду mu: %s (en buyuk %d B)"
      % ("EVET (DEPO AGACINA YAZILIYOR)" if gorulen["var"] else "hayir", gorulen["en_cok"]))
print("   kosum SONRASI hala var mi: %s" % ("EVET (ARTIK)" if os.path.exists(MUTANT_YOL) else "hayir"))
ig = subprocess.run(["git", "-C", KOK, "check-ignore", "-v", MUTANT_YOL],
                    capture_output=True, text=True)
print("   gitignore kapsaminda mi: %s" % (ig.stdout.strip() or "HAYIR — izlenmeyen dosya "
                                          "olarak gorunur, commit'e sizabilir"))
pyc = os.path.join(TOOLS, "__pycache__")
kalinti = [f for f in (os.listdir(pyc) if os.path.isdir(pyc) else [])
           if "_mutant-ozet-build" in f]
print("   __pycache__ kalintisi: %s" % (kalinti or "yok (script __main__ olarak kosuyor)"))

# --------------------------------------------------------------- S3 ayni-saniye/uzunluk
print("\nS3 — ayni saniyede AYNI UZUNLUKTA yazilan mutasyon uygulaniyor mu?")
katalog = os.path.join(GEC, "kat.json")
with open(katalog, "w", encoding="utf-8") as f:
    f.write('[{"id":"a1","kategori":"Marin","marka":[],"baslik":"A","aciklama":"a",'
            '"fiyat":"1 TL","gorseller":["https://media.pruvo3d.com/urunler/a-1.jpg"]}]')
with open(BUILD, encoding="utf-8") as f:
    taban = f.read()
capa = "OZET_TEMSIL_SURUM = 2"
sonuclar = []
bas = time.time()
for yeni in ("OZET_TEMSIL_SURUM = 3", "OZET_TEMSIL_SURUM = 2"):
    with open(MUTANT_YOL, "w", encoding="utf-8") as f:
        f.write(taban.replace(capa, yeni, 1))
    cik = os.path.join(GEC, "o-%s.json" % yeni[-1])
    rr = subprocess.run(["python3", MUTANT_YOL, "--sadece-ozet", "--katalog", katalog,
                         "--cikti", cik], capture_output=True, text=True)
    sonuclar.append((yeni, rr.returncode, (rr.stdout or "").strip()[-60:]))
gecen = time.time() - bas
os.remove(MUTANT_YOL)
print("   iki yazma arasi gecen sure: %.2f s (ayni saniye: %s)"
      % (gecen, "EVET" if gecen < 1.0 else "hayir"))
for y, rc, c in sonuclar:
    print("   %s -> rc=%d | %s" % (y, rc, c))
farkli = sonuclar[0][2] != sonuclar[1][2]
print("   iki mutasyon FARKLI sonuc verdi mi: %s" % ("EVET (onbellek tuzagi YOK)" if farkli
                                                    else "HAYIR — MUTASYON UYGULANMIYOR"))

# --------------------------------------------------------------- S4 elle mutant
print("\nS4 — mutant ELLE uygulandiginda batarya disinda da yakalaniyor mu?")
elle = [
    ("M-A (istemci: onek geri EKLENMEZ)", INDEX,
     "        out.gorsel = onek + out.gorsel;", "        out.gorsel = out.gorsel;"),
    ("M-C (istemci: TAM kart dusurulur)", INDEX,
     '        var kart = (typeof oge === "string") ? havuz[oge] : kartAc(oge);',
     '        var kart = (typeof oge === "string") ? havuz[oge] : null;'),
]
for ad, yol, eski, yeni in elle:
    with open(yol, encoding="utf-8") as f:
        src = f.read()
    if src.count(eski) != 1:
        print("   %s -> OLCULEMEDI: capa %d adet" % (ad, src.count(eski)))
        continue
    mut = os.path.join(GEC, "elle-index.html")
    with open(mut, "w", encoding="utf-8") as f:
        f.write(src.replace(eski, yeni, 1))
    rr = subprocess.run(["node", TEST, "--index", mut], capture_output=True, text=True, cwd=KOK)
    dusen = [s for s in (rr.stdout or "").split("\n") if "✘" in s]
    print("   %s -> rc=%d | dusen iddia %d | %s"
          % (ad, rr.returncode, len(dusen), (dusen[0].strip()[:90] if dusen else "")))

shutil.rmtree(GEC, ignore_errors=True)
sys.exit(0)
