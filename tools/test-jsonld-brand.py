#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON-LD "brand" kabul testi (GSC Merchant listings — "brand alanı yineleniyor").

Üretilen TÜM ürün sayfalarını (urun/*/index.html) tarar; her
<script type="application/ld+json"> bloğu için:

  1. JSON geçerli olmalı.
  2. Hiçbir objede YİNELENEN ANAHTAR olmamalı (json.loads sessizce son değeri
     alır; bu test object_pairs_hook ile yakalar).
  3. Her Product objesinde en fazla 1 "brand" anahtarı olmalı.
  4. Product.brand ÇOK-DEĞERLİ DİZİ olmamalı: Google Merchant listings "brand"i
     TEK değer bekler; birden çok Brand objesi taşıyan dizi GSC'de
     «"brand" alanı yineleniyor» KRİTİK hatası üretir (canlıda doğrulandı, 22 Tem).
     Geçerli biçimler: {"@type":"Brand","name":...} veya düz string.

Kullanım (önce build.py ile urun/ üretilmiş olmalı):
  python3 tools/test-jsonld-brand.py
Çıkış kodu: 0 = YEŞİL, 1 = KIRMIZI (ihlal sayıları yazılır).
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUN_GLOB = os.path.join(ROOT, "urun", "*", "index.html")
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def _pairs_hook_yakala(dup_listesi):
    """Yinelenen anahtarı kaydeden object_pairs_hook üretir (fail-closed)."""
    def hook(pairs):
        gorulen = set()
        for k, _ in pairs:
            if k in gorulen:
                dup_listesi.append(k)
            gorulen.add(k)
        return dict(pairs)
    return hook


def _product_objeleri(obj):
    """JSON ağacındaki tüm @type=Product objelerini döndürür (iç içe dahil)."""
    bulunan = []
    if isinstance(obj, dict):
        if obj.get("@type") == "Product":
            bulunan.append(obj)
        for v in obj.values():
            bulunan.extend(_product_objeleri(v))
    elif isinstance(obj, list):
        for v in obj:
            bulunan.extend(_product_objeleri(v))
    return bulunan


def main():
    sayfalar = sorted(glob.glob(URUN_GLOB))
    if not sayfalar:
        print("KIRMIZI: hiç ürün sayfası yok (%s) — önce tools/build.py çalıştır." % URUN_GLOB)
        return 1

    n_blok = 0
    n_product = 0
    hatalar = []          # (sayfa, mesaj)
    coklu_brand_sayfa = 0

    for yol in sayfalar:
        with open(yol, encoding="utf-8") as f:
            html_icerik = f.read()
        goreli = os.path.relpath(yol, ROOT)
        bloklar = LD_RE.findall(html_icerik)
        if not bloklar:
            hatalar.append((goreli, "JSON-LD bloğu yok"))
            continue
        sayfa_coklu = False
        for blok in bloklar:
            n_blok += 1
            dup = []
            try:
                veri = json.loads(blok, object_pairs_hook=_pairs_hook_yakala(dup))
            except ValueError as e:
                hatalar.append((goreli, "geçersiz JSON: %s" % e))
                continue
            if dup:
                hatalar.append((goreli, "yinelenen anahtar(lar): %s" % sorted(set(dup))))
            for prod in _product_objeleri(veri):
                n_product += 1
                # kural 3: object_pairs_hook zaten çift "brand" anahtarını dup'a düşürür;
                # burada kural 4: brand tek-değerli olmalı.
                brand = prod.get("brand")
                if isinstance(brand, list) and len(brand) > 1:
                    hatalar.append((goreli, "Product.brand çok-değerli dizi (%d değer) — "
                                            "Merchant listings tek değer bekler" % len(brand)))
                    sayfa_coklu = True
        if sayfa_coklu:
            coklu_brand_sayfa += 1

    print("Taranan ürün sayfası : %d" % len(sayfalar))
    print("JSON-LD blok         : %d" % n_blok)
    print("Product objesi       : %d" % n_product)
    print("Çok-değerli brand'li sayfa : %d" % coklu_brand_sayfa)
    print("Toplam ihlal         : %d" % len(hatalar))
    if hatalar:
        print("\nİlk 10 ihlal:")
        for sayfa, msg in hatalar[:10]:
            print("  %s — %s" % (sayfa, msg))
        print("\nKIRMIZI")
        return 1
    print("\nYEŞİL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
