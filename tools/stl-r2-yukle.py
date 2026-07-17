#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yerel stl/ klasorundeki uretim dosyalarini OZEL R2 kovasina (pruvo-ozel) yukler.

COK-PARCA TASARIMI (mimar duzeltme turu, 17 Tem aksam): bir urunun BIRDEN COK parca
dosyasi olabilir — istisna degil NORM (stl/'de ~6.100 dosya `<id>--<parca>.stl` adli).
  <urun-id>--<parca>.stl  ->  r2: stl/<urun-id>/<parca>.stl
  <urun-id>.stl           ->  r2: stl/<urun-id>/<urun-id>.stl  (tekli ad da klasore normalize)
Uzanti kucuk harfe cevrilir (.STL -> .stl); parca adinin harf buyuklugu korunur.
Onek urunler.json id listesiyle DOGRULANIR: listede yoksa HATALI-AD raporuna (tahmin YOK).

KAYNAK-ID ESLEMESI (mimar duzeltme turu, 17 Tem gece). KOK NEDEN: 9.075 dosyanin oneki
urun-id DEGIL kaynak-id (Thingiverse sayisal / Printables `prNNN`) — eski toplu STL
indirmesi urun-id'ye gore degil kaynak sisteme gore adlandirmisti. Onek idler'de yoksa,
gizli `.urun-kaynaklari.json` (ANA repo koku, gitignore'lu, SALT-OKUNUR) kaydindaki
`link` alanindan cikarilan kaynak-id -> urun-id sozlugune bakilir:
  thingiverse.com/thing:<sayi>      -> kaynak-id = "<sayi>"
  printables.com/model/<sayi>-...   -> kaynak-id = "pr<sayi>"
Bir kaynak-id BIRDEN FAZLA urune bagliysa TAHMIN EDILMEZ — o dosyalar "cakisan" raporuna
duser, yuklenmez (hatali-ad'dan AYRI sayilir). Eslenirse R2 anahtari
stl/<urun-id>/<orijinal-dosya-adi> olur (orijinal ad KORUNUR, sadece uzanti kucultulur) —
boylece kaynak-id iz olarak dosya adinda kalir. Gizli dosya bulunamazsa (worktree, baska
makine) esleme BOS doner — davranis eskisiyle AYNI (kaynak-id'li dosyalar hatali-ad'da kalir).

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
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUCKET = "pruvo-ozel"
PREFIX = "stl"
UZANTILAR = (".stl", ".3mf")
MANIFEST = os.path.join(REPO, ".stl-r2-manifest.json")
KAYNAKLAR = os.path.join(REPO, ".urun-kaynaklari.json")

_THING_DESENI = re.compile(r"thingiverse\.com/thing:(\d+)")
_PRINTABLES_DESENI = re.compile(r"printables\.com/model/(\d+)")


def urun_idleri():
    """urunler.json'daki gecerli id kumesi (onek dogrulamasi icin)."""
    try:
        with open(os.path.join(REPO, "urunler.json"), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return {u.get("id") for u in d if isinstance(u, dict) and u.get("id")}


def _kaynak_id_cikar(link):
    """link URL'sinden dosya-onek bicimindeki kaynak-id'yi cikarir: Thingiverse sayisal
    ("1002858"), Printables "pr<sayi>". Baska kaynaklar (********, kendi ureticimiz,
    MakerWorld, GitHub...) icin None doner — yerel STL adlandirmasi bu ikisi disinda
    kaynak-id onegi kullanmadi (bkz. modul basligindaki KAYNAK-ID ESLEMESI notu)."""
    if not isinstance(link, str):
        return None
    m = _THING_DESENI.search(link)
    if m:
        return m.group(1)
    m = _PRINTABLES_DESENI.search(link)
    if m:
        return "pr" + m.group(1)
    return None


def kaynak_esleme(gizli_kayit):
    """SAF fonksiyon. gizli .urun-kaynaklari.json icerigini (urun-id -> {"link":..., ...})
    alir, (esle, cakisan) dondurur:
    - esle: kaynak-id -> urun-id, YALNIZCA o kaynak-id TEK bir urune bagliysa.
    - cakisan: birden fazla urune bagli kaynak-id kumesi — TAHMIN EDILMEZ, esle'ye GIRMEZ,
      cagiran taraf bu dosyalari ayri ("cakisan") raporlar, yuklemez."""
    adaylar = {}
    if isinstance(gizli_kayit, dict):
        for urun_id, kayit in gizli_kayit.items():
            if not isinstance(kayit, dict):
                continue
            kid = _kaynak_id_cikar(kayit.get("link"))
            if kid:
                adaylar.setdefault(kid, set()).add(urun_id)
    esle, cakisan = {}, set()
    for kid, urunler in adaylar.items():
        if len(urunler) == 1:
            esle[kid] = next(iter(urunler))
        else:
            cakisan.add(kid)
    return esle, cakisan


def kaynak_esleme_yukle(yol):
    """Diskten gizli kaydi okuyup kaynak_esleme() uygular. Dosya yoksa/bozuksa (worktree'de
    YOK, CI, baska makine) BOS esleme+cakisan doner — davranis eskisiyle AYNI kalir
    (kaynak-id onekli dosyalar hatali-ad'da kalir, sessizce atlanmaz)."""
    try:
        with open(yol, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}, set()
    return kaynak_esleme(d)


def siniflandir(dosyalar, idler, kaynak_esle=None, kaynak_cakisan=None):
    """Dosya adlarini ([(ad, r2_anahtari)], hatali_ad, cakisan_ad) olarak ayirir. SAF fonksiyon.
    - `<id>--<parca>.stl` -> stl/<id>/<parca>.stl ; `<id>.stl` -> stl/<id>/<id>.stl
    - onek id listesinde yoksa: kaynak_esle'de TEKIL karsiligi varsa oraya yonlendirilir
      (r2 anahtari stl/<eslenen-id>/<orijinal-dosya-adi>, orijinal ad KORUNUR); onek
      kaynak_cakisan'daysa (birden fazla urune bagli) cakisan_ad'a duser (TAHMIN YOK,
      yuklenmez); hicbiri degilse HATALI-AD (eskisi gibi).
    - parca adi bossa HATALI-AD (tahmin edilmez)
    - .stl/.3mf disi uzantilar sessizce atlanir"""
    kaynak_esle = kaynak_esle or {}
    kaynak_cakisan = kaynak_cakisan or set()
    hedefler, hatali_ad, cakisan_ad = [], [], []
    for ad in dosyalar:
        kok, uz = os.path.splitext(ad)
        if uz.lower() not in UZANTILAR:
            continue
        if "--" in kok:
            onek, parca = kok.split("--", 1)
        else:
            onek, parca = kok, kok
        if not parca:
            hatali_ad.append(ad)
            continue
        if idler is not None and onek not in idler:
            if onek in kaynak_cakisan:
                cakisan_ad.append(ad)
                continue
            eslenen_id = kaynak_esle.get(onek)
            if eslenen_id is None:
                hatali_ad.append(ad)
                continue
            hedefler.append((ad, PREFIX + "/" + eslenen_id + "/" + kok + uz.lower()))
            continue
        hedefler.append((ad, PREFIX + "/" + onek + "/" + parca + uz.lower()))
    return hedefler, hatali_ad, cakisan_ad


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


def kos(dizin, idler, manifest_yol, kuru=False, yukle_fn=None, kaynak_esle=None, kaynak_cakisan=None):
    """Ana is akisi (test edilebilir): (yuklendi, atlandi, hatali_ad, cakisan_ad) dondurur.
    kuru=True: yukleme YOK, manifest'e yazma YOK — yuklenecekler sayilir/basilir.
    kaynak_esle/kaynak_cakisan: kaynak_esleme()'den gelen sozlukce/kume (bkz. siniflandir)."""
    gonderici = yukle_fn or yukle
    dosyalar = sorted(os.listdir(dizin))
    hedefler, hatali_ad, cakisan_ad = siniflandir(dosyalar, idler, kaynak_esle, kaynak_cakisan)
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
    return yuklendi, atlandi, hatali_ad, cakisan_ad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dizin", default=os.path.join(REPO, "stl"))
    ap.add_argument("--kuru", action="store_true", help="yazmadan ne yapacagini soyle")
    ap.add_argument("--kaynaklar", default=KAYNAKLAR,
                    help="gizli kaynak-id->urun-id kaydi (varsayilan: ana repo koku; "
                         "worktree/baska makinede yoksa esleme BOS kalir)")
    a = ap.parse_args()

    if not os.path.isdir(a.dizin):
        sys.exit("kaynak klasor yok: " + a.dizin)

    idler = urun_idleri()  # None = urunler.json okunamadi (onek kontrolu atlanir)
    kaynak_esle, kaynak_cakisan = kaynak_esleme_yukle(a.kaynaklar)
    yuklendi, atlandi, hatali_ad, cakisan_ad = kos(
        a.dizin, idler, MANIFEST, kuru=a.kuru,
        kaynak_esle=kaynak_esle, kaynak_cakisan=kaynak_cakisan)

    print("\nOZET: yuklendi=%d atlandi=%d hatali-ad=%d cakisan=%d (kaynak: %s%s)"
          % (yuklendi, atlandi, len(hatali_ad), len(cakisan_ad), a.dizin,
             ", --kuru" if a.kuru else ""))
    if cakisan_ad:
        print("CAKISAN KAYNAK-ID (%d dosya; onek gizli kayitta BIRDEN FAZLA urune bagli —"
              " TAHMIN EDILMEDI, yuklenmedi, elle karar verilmeli):" % len(cakisan_ad))
        for ad in cakisan_ad[:40]:
            print("  - " + ad)
        if len(cakisan_ad) > 40:
            print("  ... (+%d dosya daha)" % (len(cakisan_ad) - 40))
    if hatali_ad:
        print("HATALI AD (%d dosya; onek urunler.json id'si DEGIL, gizli kaynak eslemesinde de"
              " YOK ya da parca adi bos — TAHMIN EDILMEDI, once urun-id'ye adlandirilmali):"
              % len(hatali_ad))
        for ad in hatali_ad[:40]:
            print("  - " + ad)
        if len(hatali_ad) > 40:
            print("  ... (+%d dosya daha)" % (len(hatali_ad) - 40))


if __name__ == "__main__":
    main()
