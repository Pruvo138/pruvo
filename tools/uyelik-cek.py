#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Üyelik (***** vb.) ürünlerini toplu listeleme / kaldırma güvenlik betiği.

***** gibi tasarımcıların modelleri YALNIZCA aylık üyelik aktifken satılabilir.
Üyelik biterse bu ürünler siteden çekilmelidir (lisans ihlali olmasın). Bu betik,
`urunler.json`'da `"uyelik"` etiketli ürünleri bulur; istenirse kaldırır ve R2'deki
görsellerini siler.

Kullanım:
    python3 tools/uyelik-cek.py                 # sadece LİSTELE (dry-run, güvenli)
    python3 tools/uyelik-cek.py --uygula        # urunler.json'dan KALDIR
    python3 tools/uyelik-cek.py --uygula --r2   # ayrıca R2 görsellerini de sil
    python3 tools/uyelik-cek.py --etiket *****  # sadece belirli üyeliği hedefle

Kaldırdıktan sonra: git add urunler.json && commit && push (CI sayfaları yeniden üretir).
NOT: Ücretsiz gear generator üyelik biterse CC BY'a döner — istersen onu kaldırmak yerine
`lisans` alanını geri koyup (atıflı) tutabilirsin.
"""
import os, sys, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT, "urunler.json")


def main():
    args = sys.argv[1:]
    uygula = "--uygula" in args
    r2 = "--r2" in args
    etiket = None
    if "--etiket" in args:
        etiket = args[args.index("--etiket") + 1]

    data = json.load(open(JSON_PATH, encoding="utf-8"))
    hedef = [o for o in data if o.get("uyelik") and (etiket is None or o.get("uyelik") == etiket)]

    if not hedef:
        print("Üyelik etiketli ürün yok.")
        return

    print("Üyelik etiketli %d ürün:" % len(hedef))
    for o in hedef:
        print("  - %s  [uyelik=%s]  %s" % (o["id"], o.get("uyelik"), o.get("baslik", "")))

    if not uygula:
        print("\n(dry-run) Kaldırmak için: python3 tools/uyelik-cek.py --uygula [--r2]")
        return

    if r2:
        import boto3
        cfg = json.load(open(os.path.join(ROOT, ".r2-credentials.json")))
        s3 = boto3.client("s3", endpoint_url=cfg["endpoint"],
                          aws_access_key_id=cfg["access_key"],
                          aws_secret_access_key=cfg["secret"], region_name="auto")
        base = cfg["public_base"] + "/"
        for o in hedef:
            for url in o.get("gorseller", []):
                if url.startswith(base):
                    key = url[len(base):]
                    s3.delete_object(Bucket=cfg["bucket"], Key=key)
                    print("  R2 silindi:", key)

    kalan = [o for o in data if o not in hedef]
    json.dump(kalan, open(JSON_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n%d ürün urunler.json'dan kaldırıldı. Kalan: %d" % (len(hedef), len(kalan)))
    print("Şimdi: git add urunler.json && commit && push")


if __name__ == "__main__":
    main()
