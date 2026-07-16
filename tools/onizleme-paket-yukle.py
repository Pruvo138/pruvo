#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Onizleme derleme paketini toplar ve GIZLI R2 bucket'ina yukler.

PAKET = eslem-ozel.json + eslemin isaret ettigi .scad kaynaklari. Ikisi de SIRDIR
(uyelik ureteci kodu/degisken adlari) — public repoya ASLA girmez (gitignore).
Kanonik kopya R2 `pruvo-ozel` bucket'i: CI imaj derlerken oradan ceker
(.github/workflows/onizleme-imaj.yml), boylece sir GitHub'a ugramaz.

Kaynaklar (SALT OKUNUR — ana repoya hicbir sey yazilmaz):
  - eslem: <repo>/onizleme/derleyici/eslem-ozel.json (gitignore'lu yerel dosya)
  - .scad: PRUVO_UYELIK_DIR (varsayilan /Users/okan/dev/pruvo/.uyelik-kodlar)

Kullanim:
  python3 tools/onizleme-paket-yukle.py --yerel <dizin>   # sadece topla (test/kabul icin)
  python3 tools/onizleme-paket-yukle.py                   # topla + R2'ye yukle
Yukleme yerel wrangler oturumuyla yapilir (token gerekmez):
  npx wrangler r2 object put pruvo-ozel/onizleme/paket-v<N>.tar.gz --file ...
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESLEM_YOL = os.path.join(REPO, "onizleme", "derleyici", "eslem-ozel.json")
BUCKET = "pruvo-ozel"


def topla(hedef, uyelik_dir):
    if not os.path.exists(ESLEM_YOL):
        sys.exit("eslem-ozel.json yok: %s (gitignore'lu — R2'deki paketten geri alin: "
                 "npx wrangler r2 object get %s/onizleme/paket-v<N>.tar.gz)" %
                 (ESLEM_YOL, BUCKET))
    with open(ESLEM_YOL, encoding="utf-8") as f:
        eslem = json.load(f)
    os.makedirs(hedef, exist_ok=True)
    shutil.copy2(ESLEM_YOL, os.path.join(hedef, "eslem-ozel.json"))
    eksik = []
    for aile, tanim in eslem["aileler"].items():
        kaynak = os.path.join(uyelik_dir, tanim["scad"])
        if not os.path.exists(kaynak):
            eksik.append("%s (%s)" % (tanim["scad"], aile))
            continue
        shutil.copy2(kaynak, os.path.join(hedef, tanim["scad"]))
    if eksik:
        sys.exit("eksik .scad kaynagi: %s (PRUVO_UYELIK_DIR dogru mu?)" % ", ".join(eksik))
    return eslem.get("surum", 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yerel", metavar="DIZIN",
                    help="paketi bu dizine topla, YUKLEME (kabul testleri kullanir)")
    ap.add_argument("--uyelik-dir",
                    default=os.environ.get("PRUVO_UYELIK_DIR",
                                           "/Users/okan/dev/pruvo/.uyelik-kodlar"))
    args = ap.parse_args()

    if args.yerel:
        surum = topla(args.yerel, args.uyelik_dir)
        print("paket toplandi (v%d): %s" % (surum, args.yerel))
        return

    with tempfile.TemporaryDirectory() as tmp:
        paket_dizin = os.path.join(tmp, "paket")
        surum = topla(paket_dizin, args.uyelik_dir)
        arsiv = os.path.join(tmp, "paket.tar.gz")
        with tarfile.open(arsiv, "w:gz") as tar:
            for ad in sorted(os.listdir(paket_dizin)):
                tar.add(os.path.join(paket_dizin, ad), arcname=ad)
        anahtar = "onizleme/paket-v%d.tar.gz" % surum
        # Yerel wrangler oturumu (token'siz). shell degiskeni yok — komut listesi.
        komut = ["npx", "wrangler", "r2", "object", "put",
                 BUCKET + "/" + anahtar, "--file", arsiv, "--remote"]
        proc = subprocess.run(komut, cwd=REPO, capture_output=True)
        if proc.returncode != 0:
            sys.stderr.write(proc.stdout.decode("utf-8", "replace"))
            sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
            sys.exit("R2 yuklemesi basarisiz (wrangler oturumu acik mi?)")
        print("yuklendi: r2://%s/%s (%d bayt)" %
              (BUCKET, anahtar, os.path.getsize(arsiv)))
        # 'guncel' takma adi: CI hep bunu ceker, surumlu kopya gecmis icin durur.
        komut2 = ["npx", "wrangler", "r2", "object", "put",
                  BUCKET + "/onizleme/paket-guncel.tar.gz", "--file", arsiv, "--remote"]
        proc2 = subprocess.run(komut2, cwd=REPO, capture_output=True)
        if proc2.returncode != 0:
            sys.exit("paket-guncel.tar.gz yuklemesi basarisiz")
        print("yuklendi: r2://%s/onizleme/paket-guncel.tar.gz" % BUCKET)
        # NOT (2026-07-16): ONIZLEME_PAKET_B64 yedegi KALDIRILDI (Okan karari). CI artik
        # paketi dogrudan R2'den ceker: R2_ERISIM_ID/R2_GIZLI_ANAHTAR secret'lari
        # pruvo-ozel'e SALT-OKUMA yetkili 'pruvo-ozel-okuma-ci' token'idir.


if __name__ == "__main__":
    main()
