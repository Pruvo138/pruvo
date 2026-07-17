#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yerel stl/ klasorundeki uretim dosyalarini OZEL R2 kovasina (pruvo-ozel) yukler.

Yonetim sayfasindaki "Uretim dosyasi indir" dugmesi bu kovadan (stl/<urun-id>.stl|.3mf)
okur. Kova OZELDIR (public pruvo-media DEGIL) — ticari uretim dosyasi sizmaz.

  python3 tools/stl-r2-yukle.py            # yerel stl/ -> r2 pruvo-ozel/stl/ (idempotent)
  python3 tools/stl-r2-yukle.py --kuru     # yalniz ne yapacagini soyle (yukleme yok)
  python3 tools/stl-r2-yukle.py --dizin X  # farkli kaynak klasor

ADLANDIRMA: dosya adi <urun-id>.stl ya da <urun-id>.3mf OLMALI (urunler.json id'siyle
birebir). Baska adlananlar RAPORLANIR, TAHMIN EDILMEZ (yanlis urune yanlis dosya = pahali
hata). Idempotent: R2'de ayni anahtar + AYNI boyut varsa atlanir.

Yukleme yerel wrangler oturumuyla (npx wrangler r2 object put ... --remote) — token gerekmez.
KAPSAM GERCEGI: her urunun dosyasi diskte YOK (bazi urunler siparis aninda kaynaktan
indirilir); arac sonunda "yuklendi / atlandi / hatali-ad" sayimi basar, eksikler yonetim
sayfasindaki notta gorunur (dosya R2'de yoksa "yok" uyarisi).
"""

import argparse
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUCKET = "pruvo-ozel"
PREFIX = "stl"
UZANTILAR = (".stl", ".3mf")


def urun_idleri():
    """urunler.json'daki gecerli id kumesi (yanlis-ad tespiti icin)."""
    try:
        with open(os.path.join(REPO, "urunler.json"), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return {u.get("id") for u in d if isinstance(u, dict) and u.get("id")}


def siniflandir(dosyalar, idler):
    """Dosya adlarini (yuklenecekler, hatali_ad) olarak ayirir. SAF fonksiyon (test edilir).
    <urun-id>.stl|.3mf disi uzantilar atlanir; id eslesmeyenler TAHMIN EDILMEZ, raporlanir."""
    hedefler, hatali_ad = [], []
    for ad in dosyalar:
        kok, uz = os.path.splitext(ad)
        if uz.lower() not in UZANTILAR:
            continue
        if idler is not None and kok not in idler:
            hatali_ad.append(ad)
            continue
        hedefler.append((ad, PREFIX + "/" + kok + uz.lower()))
    return hedefler, hatali_ad


def atlanir(anahtar, boyut, r2_liste):
    """Idempotens karari: R2'de ayni anahtar + AYNI boyut varsa True (yeniden yuklenmez)."""
    var = r2_liste.get(anahtar)
    return var is not None and int(var) == boyut


def r2_liste_yukle():
    """stl/ prefix'indeki tum nesneleri {anahtar: boyut} olarak dondurur (idempotens icin)."""
    komut = ["npx", "wrangler", "r2", "object", "list", BUCKET,
             "--prefix", PREFIX + "/", "--remote"]
    p = subprocess.run(komut, cwd=REPO, capture_output=True, text=True)
    harita = {}
    ham = (p.stdout or "")
    # Cikti JSON dizisi ya da satir satir olabilir; JSON dene, olmazsa bos (ilk kez bos kova).
    i = ham.find("[")
    if p.returncode == 0 and i != -1:
        try:
            for n in json.loads(ham[i:]):
                if isinstance(n, dict) and n.get("key"):
                    harita[n["key"]] = n.get("size")
        except json.JSONDecodeError:
            pass
    return harita


def yukle(yerel, anahtar):
    komut = ["npx", "wrangler", "r2", "object", "put", BUCKET + "/" + anahtar,
             "--file", yerel, "--remote"]
    p = subprocess.run(komut, cwd=REPO, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write((p.stdout or "") + (p.stderr or ""))
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dizin", default=os.path.join(REPO, "stl"))
    ap.add_argument("--kuru", action="store_true", help="yazmadan ne yapacagini soyle")
    a = ap.parse_args()

    if not os.path.isdir(a.dizin):
        sys.exit("kaynak klasor yok: " + a.dizin)

    idler = urun_idleri()  # None = urunler.json okunamadi (yanlis-ad kontrolu atlanir)
    dosyalar = sorted(os.listdir(a.dizin))
    hedefler, hatali_ad = siniflandir(dosyalar, idler)

    r2_liste = {} if a.kuru else r2_liste_yukle()

    yuklendi, atlandi = 0, 0
    for ad, anahtar in hedefler:
        yerel = os.path.join(a.dizin, ad)
        boyut = os.path.getsize(yerel)
        if atlanir(anahtar, boyut, r2_liste):
            atlandi += 1
            continue
        if a.kuru:
            print("YUKLENECEK: %s -> r2://%s/%s (%d B)" % (yerel, BUCKET, anahtar, boyut))
            yuklendi += 1
            continue
        if yukle(yerel, anahtar):
            print("yuklendi: r2://%s/%s (%d B)" % (BUCKET, anahtar, boyut))
            yuklendi += 1
        else:
            sys.exit("R2 yuklemesi basarisiz (wrangler oturumu acik mi?): " + anahtar)

    print("\nOZET: yuklendi=%d atlandi=%d hatali-ad=%d (kaynak: %s)"
          % (yuklendi, atlandi, len(hatali_ad), a.dizin))
    if hatali_ad:
        print("HATALI AD (urunler.json id'siyle eslesmiyor — TAHMIN EDILMEDI, elle bak):")
        for ad in hatali_ad:
            print("  - " + ad)


if __name__ == "__main__":
    main()
