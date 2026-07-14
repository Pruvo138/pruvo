#!/usr/bin/env python3
"""duzelt.py — MEVCUT bir urunun alanini BILEREK degistirmenin TEK yetkili yolu.

urunler-guard.py, HEAD'de var olan urunlerin herhangi bir alani degistiginde onu
otomatik HEAD'e geri dondurur. Mesru bir duzeltme (or. bir urunun fiyatini/
kategorisini bilerek degistirmek) yapmak icin bu araci kullan: degisikligi
.urunler.lock altinda urunler.json'a yazar VE guard'in izin vermesi icin
deger-bagli bir "duzeltme izni" manifesti (.urunler-duzelt-izin.json) uretir.

Guard yalnizca working-tree'deki yeni deger manifeste yazilan deger ile BIREBIR
esitse o alanin degismesine izin verir; beyan disi hicbir alani gecirmez.

Kullanim:
  python3 tools/duzelt.py <id> --alan fiyat --deger "500 TL"
  python3 tools/duzelt.py <id> --alan fiyat --deger "500 TL" --alan kategori --deger Elektronik
  python3 tools/duzelt.py <id> --alan marka --deger '["BMW","Mini"]'   # liste/sozluk icin JSON

Deger cozumleme: '[' veya '{' ile baslayan degerler JSON olarak (liste/sozluk)
ayristirilir; digerleri duz metin kabul edilir (fiyat "500 TL" gibi).
'id' alani degistirilemez.
"""
import argparse
import datetime
import fcntl
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(ROOT, "urunler.json")
LOCK = os.path.join(ROOT, ".urunler.lock")
MANIFEST = os.path.join(ROOT, ".urunler-duzelt-izin.json")
LOG = os.path.join(ROOT, ".urunler-guard.log")

DEGISTIRILEBILIR = {"kategori", "marka", "baslik", "aciklama", "fiyat", "gorseller", "lisans"}


def _log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG, "a") as f:
            f.write("[%s] %s\n" % (ts, msg))
    except OSError:
        pass


def _parse_deger(raw):
    s = raw.strip()
    if s[:1] in ("[", "{"):
        return json.loads(s)  # liste/sozluk
    return raw  # duz metin (fiyat, baslik, kategori, ...)


def _atomic_write(path, obj):
    tmp = path + ".tmp-" + str(os.getpid())
    with open(tmp, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("id", help="degistirilecek MEVCUT urun id'si")
    ap.add_argument("--alan", action="append", required=True,
                    help="degistirilecek alan adi (tekrarlanabilir)")
    ap.add_argument("--deger", action="append", required=True,
                    help="yeni deger (her --alan icin bir tane; JSON icin [ veya { ile basla)")
    args = ap.parse_args()

    if len(args.alan) != len(args.deger):
        print("HATA: --alan ve --deger sayisi esit olmali.", file=sys.stderr)
        return 2

    degisiklikler = {}
    for alan, deger in zip(args.alan, args.deger):
        if alan == "id":
            print("HATA: 'id' alani degistirilemez.", file=sys.stderr)
            return 2
        if alan not in DEGISTIRILEBILIR:
            print("HATA: bilinmeyen/izinsiz alan: %s (izinli: %s)"
                  % (alan, ", ".join(sorted(DEGISTIRILEBILIR))), file=sys.stderr)
            return 2
        try:
            degisiklikler[alan] = _parse_deger(deger)
        except ValueError as e:
            print("HATA: '%s' alaninin degeri JSON olarak cozumlenemedi: %s" % (alan, e),
                  file=sys.stderr)
            return 2

    lockf = open(LOCK, "w")
    fcntl.flock(lockf, fcntl.LOCK_EX)
    try:
        with open(URUNLER, encoding="utf-8") as f:
            urunler = json.load(f)
        idx = next((i for i, p in enumerate(urunler)
                    if isinstance(p, dict) and p.get("id") == args.id), None)
        if idx is None:
            print("HATA: '%s' id'li urun urunler.json'da yok." % args.id, file=sys.stderr)
            return 1

        # SADECE beyan edilen alanlari degistir; beyan disina dokunma.
        for alan, deger in degisiklikler.items():
            urunler[idx][alan] = deger
        _atomic_write(URUNLER, urunler)

        # Guard icin deger-bagli izin manifesti (birikimli).
        manifest = {}
        if os.path.exists(MANIFEST):
            try:
                with open(MANIFEST, encoding="utf-8") as f:
                    m = json.load(f)
                if isinstance(m, dict):
                    manifest = m
            except ValueError:
                manifest = {}
        manifest.setdefault(args.id, {})
        for alan, deger in degisiklikler.items():
            manifest[args.id][alan] = deger
        _atomic_write(MANIFEST, manifest)
    finally:
        fcntl.flock(lockf, fcntl.LOCK_UN)
        lockf.close()

    ozet = ", ".join("%s=%s" % (a, json.dumps(v, ensure_ascii=False))
                     for a, v in degisiklikler.items())
    _log("duzelt: %s -> %s (izin manifestine yazildi)" % (args.id, ozet))
    print("Duzeltildi: %s  (%s)" % (args.id, ozet))
    print("Guard bu degisikligi manifest sayesinde gecirir; commit sonrasi post-commit "
          "hook manifesti temizler.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
