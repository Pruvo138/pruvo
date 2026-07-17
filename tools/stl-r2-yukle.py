#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yerel stl/ klasorundeki uretim dosyalarini OZEL R2 kovasina (pruvo-ozel) yukler.

COK-PARCA TASARIMI (mimar duzeltme turu, 17 Tem aksam): bir urunun BIRDEN COK parca
dosyasi olabilir — istisna degil NORM (stl/'de ~6.100 dosya `<id>--<parca>.stl` adli).
  <urun-id>--<parca>.stl  ->  r2: stl/<urun-id>/<parca>.stl
  <urun-id>.stl           ->  r2: stl/<urun-id>/<urun-id>.stl  (tekli ad da klasore normalize)
Uzanti kucuk harfe cevrilir (.STL -> .stl); parca adinin harf buyuklugu korunur.
Onek urunler.json id listesiyle DOGRULANIR: listede yoksa HATALI-AD raporuna (tahmin YOK —
kaynak-id onekli dosyalar [Thingiverse sayisal / prNNN] once urun-id'ye adlandirilmali).

IDEMPOTENS — YEREL MANIFEST (mimar duzeltme turu). KOK NEDEN DERSI: wrangler'da
`r2 object list` / `head` alt komutu YOK; ilk surum listeyi sessizce bos alip HER kosumda
her seyi yeniden yukluyordu (canli kosumda yakalandi: 2. kosum atlandi=0). Cozum:
gitignore'lu `.stl-r2-manifest.json` (repo koku) anahtar -> {sha1, boyut} tutar; ikisi de
ayni ise atlanir (SHA kiyasi: ayni boyutlu farkli icerik de yakalanir). Manifest her
basarili yuklemeden SONRA atomik yazilir (kesilen kosum kaldigi yerden devam eder).
Manifest silinirse dosyalar yeniden yuklenir (zararsiz: ayni anahtarin ustune yazar).

  python3 tools/stl-r2-yukle.py            # yerel stl/ -> r2 pruvo-ozel/stl/<id>/<parca>
  python3 tools/stl-r2-yukle.py --kuru     # yalniz ne yapacagini soyle (yukleme/manifest yok)
  python3 tools/stl-r2-yukle.py --dizin X  # farkli kaynak klasor

Yukleme yerel wrangler oturumuyla (npx wrangler r2 object put ... --remote) — token gerekmez.
Sonda "yuklendi / atlandi / hatali-ad" sayimi basilir. ZIP YOK (280 MB'lik dosyalar var;
worker'da sikistirma yapilmaz — yonetim sayfasi parcalari tek tek indirir).
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUCKET = "pruvo-ozel"
PREFIX = "stl"
UZANTILAR = (".stl", ".3mf")
MANIFEST = os.path.join(REPO, ".stl-r2-manifest.json")


def urun_idleri():
    """urunler.json'daki gecerli id kumesi (onek dogrulamasi icin)."""
    try:
        with open(os.path.join(REPO, "urunler.json"), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return {u.get("id") for u in d if isinstance(u, dict) and u.get("id")}


def siniflandir(dosyalar, idler):
    """Dosya adlarini ([(ad, r2_anahtari)], hatali_ad) olarak ayirir. SAF fonksiyon.
    - `<id>--<parca>.stl` -> stl/<id>/<parca>.stl ; `<id>.stl` -> stl/<id>/<id>.stl
    - onek id listesinde yoksa ya da parca adi bossa HATALI-AD (tahmin edilmez)
    - .stl/.3mf disi uzantilar sessizce atlanir"""
    hedefler, hatali_ad = [], []
    for ad in dosyalar:
        kok, uz = os.path.splitext(ad)
        if uz.lower() not in UZANTILAR:
            continue
        if "--" in kok:
            onek, parca = kok.split("--", 1)
        else:
            onek, parca = kok, kok
        if not parca or (idler is not None and onek not in idler):
            hatali_ad.append(ad)
            continue
        hedefler.append((ad, PREFIX + "/" + onek + "/" + parca + uz.lower()))
    return hedefler, hatali_ad


def sha1_dosya(yol):
    h = hashlib.sha1()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def manifest_oku(yol):
    try:
        with open(yol, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def manifest_yaz(yol, manifest):
    # Atomik yazim: yarim yazilmis manifest sonraki kosumun idempotensini bozmasin.
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, sort_keys=True)
    os.replace(gecici, yol)


def yukle(yerel, anahtar):
    komut = ["npx", "wrangler", "r2", "object", "put", BUCKET + "/" + anahtar,
             "--file", yerel, "--remote"]
    p = subprocess.run(komut, cwd=REPO, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write((p.stdout or "") + (p.stderr or ""))
        return False
    return True


def kos(dizin, idler, manifest_yol, kuru=False, yukle_fn=None):
    """Ana is akisi (test edilebilir): (yuklendi, atlandi, hatali_ad) dondurur.
    kuru=True: yukleme YOK, manifest'e yazma YOK — yuklenecekler sayilir/basilir."""
    gonderici = yukle_fn or yukle
    dosyalar = sorted(os.listdir(dizin))
    hedefler, hatali_ad = siniflandir(dosyalar, idler)
    manifest = manifest_oku(manifest_yol)
    yuklendi = atlandi = 0
    for ad, anahtar in hedefler:
        yerel = os.path.join(dizin, ad)
        boyut = os.path.getsize(yerel)
        ozet = sha1_dosya(yerel)
        kayit = manifest.get(anahtar)
        if kayit and kayit.get("sha1") == ozet and kayit.get("boyut") == boyut:
            atlandi += 1
            continue
        if kuru:
            print("YUKLENECEK: %s -> r2://%s/%s (%d B)" % (ad, BUCKET, anahtar, boyut))
            yuklendi += 1
            continue
        if not gonderici(yerel, anahtar):
            sys.exit("R2 yuklemesi basarisiz (wrangler oturumu acik mi?): " + anahtar)
        manifest[anahtar] = {"sha1": ozet, "boyut": boyut}
        manifest_yaz(manifest_yol, manifest)  # her yuklemeden sonra — kesinti guvenli
        print("yuklendi: r2://%s/%s (%d B)" % (BUCKET, anahtar, boyut))
        yuklendi += 1
    return yuklendi, atlandi, hatali_ad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dizin", default=os.path.join(REPO, "stl"))
    ap.add_argument("--kuru", action="store_true", help="yazmadan ne yapacagini soyle")
    a = ap.parse_args()

    if not os.path.isdir(a.dizin):
        sys.exit("kaynak klasor yok: " + a.dizin)

    idler = urun_idleri()  # None = urunler.json okunamadi (onek kontrolu atlanir)
    yuklendi, atlandi, hatali_ad = kos(a.dizin, idler, MANIFEST, kuru=a.kuru)

    print("\nOZET: yuklendi=%d atlandi=%d hatali-ad=%d (kaynak: %s%s)"
          % (yuklendi, atlandi, len(hatali_ad), a.dizin, ", --kuru" if a.kuru else ""))
    if hatali_ad:
        print("HATALI AD (%d dosya; onek urunler.json id'si DEGIL ya da parca adi bos —"
              " TAHMIN EDILMEDI, once urun-id'ye adlandirilmali):" % len(hatali_ad))
        for ad in hatali_ad[:40]:
            print("  - " + ad)
        if len(hatali_ad) > 40:
            print("  ... (+%d dosya daha)" % (len(hatali_ad) - 40))


if __name__ == "__main__":
    main()
