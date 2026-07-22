#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON-LD "offers" kabul testi (GSC Merchant listings — «"price" alanı eksik»).

Üretilen TÜM ürün sayfalarını (urun/*/index.html) tarar; her
<script type="application/ld+json"> bloğu için:

  1. JSON geçerli olmalı.
  2. Hiçbir objede YİNELENEN ANAHTAR olmamalı (json.loads sessizce son değeri
     alır; bu test object_pairs_hook ile yakalar).
  3. Her Product objesinde "offers" VARSA: offers geçerli biçimde olmalı
     (Offer objesi ya da Offer dizisi) ve içindeki HER Offer/AggregateOffer
     "price" YA DA "lowPrice" taşımalı, değer SAYISAL olmalı (pozitif int/float
     ya da "1250" / "150.50" biçimli string) ve "priceCurrency" bulunmalı.
     Fiyatsız Offer basmak GSC Merchant listings'te «"price" alanı eksik»
     KRİTİK hatası üretir (canlıda doğrulandı, 22 Tem — parametrik/sarı seri
     sayfaların TÜMÜ fiyatsız Offer basıyordu). Fail-closed kural (build.py):
     sayısal fiyat bulunamayan üründe offers HİÇ basılmaz — fiyatsız Offer
     basmak yasak; offers'ı tamamen çıkarmak yalnız uyarı düzeyinde kalır.
  4. SINIF-GENELİ GERİLEME: offers'lı Product sayısı 0 ise KIRMIZI — build
     offers'ı TÜM sayfalardan düşürmüşse tek tek ihlal üretmez, bu kural
     yakalar. Ayrıca offers'sız sayfa oranı > %10 ise BLOKLAMAYAN uyarı
     satırı basılır (çıkış kodunu ETKİLEMEZ — parametrik fail-closed
     çıkarımına meşru alan).

Kullanım (önce build.py ile urun/ üretilmiş olmalı):
  python3 tools/test-jsonld-offers.py
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
# Schema.org "price": nokta ondalıklı sayı; binlik ayracı/para simgesi/virgül GEÇERSİZ.
PRICE_RE = re.compile(r"^\d+(?:\.\d+)?$")


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


def _sayisal_fiyat(v):
    """price/lowPrice değeri GSC için geçerli sayısal mı? (bool DEĞİL; pozitif
    int/float; ya da '1250' / '150.50' biçimli string)."""
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return v > 0
    if isinstance(v, str):
        s = v.strip()
        return bool(PRICE_RE.match(s)) and float(s) > 0
    return False


def _offer_ihlalleri(offers):
    """Bir Product.offers değerinin ihlal mesajlarını döndürür (boş liste = temiz)."""
    if isinstance(offers, dict):
        offer_listesi = [offers]
    elif isinstance(offers, list):
        if not offers or not all(isinstance(o, dict) for o in offers):
            return ["offers dizisi boş ya da obje-dışı eleman içeriyor"]
        offer_listesi = offers
    else:
        return ["offers ne Offer objesi ne Offer dizisi (%s)" % type(offers).__name__]

    mesajlar = []
    for o in offer_listesi:
        fiyat = o.get("price", o.get("lowPrice"))
        if "price" not in o and "lowPrice" not in o:
            mesajlar.append("Offer'da price/lowPrice YOK (GSC: «price alanı eksik» KRİTİK)")
        elif not _sayisal_fiyat(fiyat):
            mesajlar.append("price/lowPrice sayısal değil: %r" % (fiyat,))
        if "priceCurrency" not in o:
            mesajlar.append("Offer'da priceCurrency yok")
        elif not (isinstance(o.get("priceCurrency"), str) and o["priceCurrency"].strip()):
            mesajlar.append("priceCurrency boş/string değil: %r" % (o.get("priceCurrency"),))
    return mesajlar


def main():
    sayfalar = sorted(glob.glob(URUN_GLOB))
    if not sayfalar:
        print("KIRMIZI: hiç ürün sayfası yok (%s) — önce tools/build.py çalıştır." % URUN_GLOB)
        return 1

    n_blok = 0
    n_product = 0
    n_offerli = 0
    hatalar = []          # (sayfa, mesaj)
    ihlalli_sayfalar = set()
    offerssiz_sayfalar = 0   # offers hiç yok (fail-closed çıkarılmış) — sadece SAYILIR

    for yol in sayfalar:
        with open(yol, encoding="utf-8") as f:
            html_icerik = f.read()
        goreli = os.path.relpath(yol, ROOT)
        bloklar = LD_RE.findall(html_icerik)
        if not bloklar:
            hatalar.append((goreli, "JSON-LD bloğu yok"))
            ihlalli_sayfalar.add(goreli)
            continue
        sayfa_offerli = False
        for blok in bloklar:
            n_blok += 1
            dup = []
            try:
                veri = json.loads(blok, object_pairs_hook=_pairs_hook_yakala(dup))
            except ValueError as e:
                hatalar.append((goreli, "geçersiz JSON: %s" % e))
                ihlalli_sayfalar.add(goreli)
                continue
            if dup:
                hatalar.append((goreli, "yinelenen anahtar(lar): %s" % sorted(set(dup))))
                ihlalli_sayfalar.add(goreli)
            for prod in _product_objeleri(veri):
                n_product += 1
                if "offers" not in prod:
                    continue  # fail-closed çıkarım — ihlal değil, aşağıda sayılır
                sayfa_offerli = True
                n_offerli += 1
                for msg in _offer_ihlalleri(prod["offers"]):
                    hatalar.append((goreli, msg))
                    ihlalli_sayfalar.add(goreli)
        if not sayfa_offerli:
            offerssiz_sayfalar += 1

    print("Taranan ürün sayfası    : %d" % len(sayfalar))
    print("JSON-LD blok            : %d" % n_blok)
    print("Product objesi          : %d" % n_product)
    print("offers'lı Product       : %d" % n_offerli)
    print("offers'sız sayfa        : %d  (fail-closed çıkarım — ihlal değil)" % offerssiz_sayfalar)
    print("İhlalli sayfa           : %d" % len(ihlalli_sayfalar))
    print("Toplam ihlal            : %d" % len(hatalar))

    # BLOKLAMAYAN uyarı: offers'sız sayfa oranı %10'u aşarsa haber ver
    # (çıkış kodunu etkilemez — parametrik/fail-closed çıkarım meşru).
    oran = offerssiz_sayfalar / len(sayfalar)
    if oran > 0.10:
        print("UYARI (bloklamayan): offers'sız sayfa oranı %%%.1f > %%10 — "
              "fail-closed çıkarım beklenenden yaygın, build.py fiyat akışını gözden geçir."
              % (oran * 100))

    # SINIF-GENELİ GERİLEME: hiçbir Product offers taşımıyorsa build offers'ı
    # komple düşürmüş demektir — tek tek ihlal üretmez, burada KIRMIZI.
    if n_offerli == 0:
        print("\nKIRMIZI: offers'lı Product sayısı 0 — TAM SINIF GERİLEMESİ "
              "(build hiçbir sayfaya offers basmıyor; fail-closed çıkarım tekil üründe "
              "meşrudur, tüm katalogda değil).")
        return 1

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
