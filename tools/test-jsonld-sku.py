#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON-LD "sku" kabul testi (GSC Merchant listings — «sku alani gecersiz uzunluk»).

KOK NEDEN (GSC WNC-10030322, 24 Tem): Google Merchant "sku" alani 50 karakter
sinirlidir. Merchant feed g:id/g:mpn bu siniri feed_id(pid) ile uyguluyordu
(<=50 AYNEN; uzunsa pid[:41]+'-'+sha1[:8] = tam 50) AMA JSON-LD Product.sku HAM
pid basiyordu -> 50 karakteri asan urun-id'lerinde sku «gecersiz uzunluk» KRITIK
hatasi. Onarim (build.py render_product): "sku" = feed_id(pid) -> feed g:id/g:mpn
ile TEK KAYNAK kanonik kimlik. product_url/link/canonical TAM pid ile KALIR.

Bu test UC katman dogrular:

  A) SINIF-GENELI (uretilen TUM urun/*/index.html): her JSON-LD blogu gecerli +
     hicbir objede yinelenen anahtar yok; her Product objesinde:
       1. "sku" VAR ve bos-olmayan string.
       2. len(sku) <= 50 (feed_id ile ayni birim: Python str/kod-noktasi).
       3. sku == feed_id(pid)  (pid = urun/<pid>/ dizin adi; feed g:id/g:mpn ile
          AYNI kanonik kimlik -> katalog/feed tutarli).
       4. KISA id (len(pid) <= 50): sku == HAM pid  (churn yok — kisa id'ler
          onarimdan ETKILENMEZ).
       5. UZUN id (len(pid) > 50): sku != HAM pid  (kisaltilmis olmali).
     SINIF-GENELI GERILEME: sku'lu Product sayisi 0 ise KIRMIZI (build tum
     sayfalardan sku'yu dusurmusse tekil ihlal uretmez, bu kural yakalar).

  B) FEED CAPRAZ-KONTROL (merchant-feed.xml varsa): feed'deki HER <item> icin
     <link>'ten pid, <g:mpn>'den kimlik geri okunur; ilgili urun sayfasinin
     JSON-LD sku'su g:mpn ile BIREBIR ayni olmali. Feed'de bir UZUN-id urun
     varsa "sayfa sku == feed g:mpn" ozdesligi orada dogrudan kanitlanir.

  C) MUTASYON-KANITI SENTETIK NOBET (katalogdan BAGIMSIZ): sentetik bir UZUN-id
     (60 karakter) urun render_product'tan gecirilir; ciktidaki JSON-LD sku
     <= 50 VE == feed_id VE != pid olmali. Boylece katalogda o an uzun-id urun
     olmasa bile "sku": pid gerilemesi yakalanir (kod yolu dogrudan kilitli).
     Ayrica sentetik KISA-id urunde sku == pid (churn nobeti).

MUTASYON: build.py'de "sku": feed_id(pid) -> "sku": pid'e cevrilince C katmani
(ve katalogda uzun-id varsa A/B) KIRMIZI yanar; feed_id(pid)'e geri alininca YESIL.

Kullanim (once build.py ile urun/ + merchant-feed.xml uretilmis olmali):
  python3 tools/test-jsonld-sku.py
Cikis kodu: 0 = YESIL, 1 = KIRMIZI (ihlal sayilari yazilir).
"""
import glob
import html
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import build as B  # noqa: E402  feed_id / render_product / SITE — TEK KAYNAK

URUN_GLOB = os.path.join(ROOT, "urun", "*", "index.html")
MERCHANT_FEED = os.path.join(ROOT, "merchant-feed.xml")
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
ITEM_RE = re.compile(r"<item>(.*?)</item>", re.S)
LINK_RE = re.compile(r"<link>(.*?)</link>", re.S)
MPN_RE = re.compile(r"<g:mpn>(.*?)</g:mpn>", re.S)

SKU_MAX = 50


def _pairs_hook_yakala(dup_listesi):
    """Yinelenen anahtari kaydeden object_pairs_hook uretir (fail-closed)."""
    def hook(pairs):
        gorulen = set()
        for k, _ in pairs:
            if k in gorulen:
                dup_listesi.append(k)
            gorulen.add(k)
        return dict(pairs)
    return hook


def _product_objeleri(obj):
    """JSON agacindaki tum @type=Product objelerini dondurur (ic ice dahil)."""
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


def _sayfa_sku_kontrol(pid, prod, goreli, hatalar, sayaclar):
    """Bir Product objesinin sku kurallarini dogrular (ihlalleri hatalar'a ekler)."""
    if "sku" not in prod:
        hatalar.append((goreli, "Product'ta sku YOK"))
        return
    sku = prod["sku"]
    sayaclar["sku"] += 1
    if not (isinstance(sku, str) and sku.strip()):
        hatalar.append((goreli, "sku bos/string degil: %r" % (sku,)))
        return
    # kural 2: uzunluk siniri (asil GSC hatasi)
    if len(sku) > SKU_MAX:
        sayaclar["uzun_sku"] += 1
        hatalar.append((goreli, "sku %d karakter > %d (GSC «gecersiz uzunluk»): %r"
                        % (len(sku), SKU_MAX, sku)))
    # kural 3: feed g:id/g:mpn ile ayni kanonik kimlik
    beklenen = B.feed_id(pid)
    if sku != beklenen:
        hatalar.append((goreli, "sku != feed_id(pid): sku=%r feed_id=%r pid=%r"
                        % (sku, beklenen, pid)))
    # kural 4/5: churn nobeti (kisa id degismez, uzun id kisalir)
    if len(pid) <= SKU_MAX:
        if sku != pid:
            hatalar.append((goreli, "KISA id (%d<=%d) sku HAM pid DEGIL (churn): sku=%r pid=%r"
                            % (len(pid), SKU_MAX, sku, pid)))
    else:
        sayaclar["uzun_id_sayfa"] += 1
        if sku == pid:
            hatalar.append((goreli, "UZUN id (%d>%d) sku HAM pid ile ayni (kisaltilmadi): %r"
                            % (len(pid), SKU_MAX, pid)))


def sinif_geneli(hatalar, sayaclar):
    """A katmani: uretilen tum urun sayfalarini tarar."""
    sayfalar = sorted(glob.glob(URUN_GLOB))
    if not sayfalar:
        print("KIRMIZI: hic urun sayfasi yok (%s) — once tools/build.py calistir." % URUN_GLOB)
        return None
    sayaclar["sayfa"] = len(sayfalar)
    # pid -> sayfa sku (B katmani feed capraz-kontrolu icin)
    sayfa_sku = {}
    for yol in sayfalar:
        with open(yol, encoding="utf-8") as f:
            html_icerik = f.read()
        goreli = os.path.relpath(yol, ROOT)
        pid = os.path.basename(os.path.dirname(yol))
        bloklar = LD_RE.findall(html_icerik)
        if not bloklar:
            hatalar.append((goreli, "JSON-LD blogu yok"))
            continue
        for blok in bloklar:
            sayaclar["blok"] += 1
            dup = []
            try:
                veri = json.loads(blok, object_pairs_hook=_pairs_hook_yakala(dup))
            except ValueError as e:
                hatalar.append((goreli, "gecersiz JSON: %s" % e))
                continue
            if dup:
                hatalar.append((goreli, "yinelenen anahtar(lar): %s" % sorted(set(dup))))
            for prod in _product_objeleri(veri):
                sayaclar["product"] += 1
                _sayfa_sku_kontrol(pid, prod, goreli, hatalar, sayaclar)
                if isinstance(prod.get("sku"), str):
                    sayfa_sku[pid] = prod["sku"]
    return sayfa_sku


def feed_capraz(sayfa_sku, hatalar, sayaclar):
    """B katmani: merchant-feed.xml g:mpn ile sayfa sku ozdesligi (varsa)."""
    if not os.path.exists(MERCHANT_FEED):
        print("UYARI (bloklamayan): merchant-feed.xml yok — feed capraz-kontrol atlandi "
              "(build.py'den ONCE mi kosuldu?).")
        return
    with open(MERCHANT_FEED, encoding="utf-8") as f:
        feed = f.read()
    onek = B.SITE + "/urun/"
    for item in ITEM_RE.findall(feed):
        lm = LINK_RE.search(item)
        mm = MPN_RE.search(item)
        if not lm or not mm:
            continue
        link = html.unescape(lm.group(1).strip())
        mpn = html.unescape(mm.group(1).strip())
        if not (link.startswith(onek) and link.endswith("/")):
            continue
        pid = link[len(onek):-1]
        sayaclar["feed_item"] += 1
        if len(pid) > SKU_MAX:
            sayaclar["feed_uzun_id"] += 1
        sku = sayfa_sku.get(pid)
        if sku is None:
            hatalar.append(("merchant-feed.xml", "feed item pid=%r icin urun sayfasi/sku yok" % pid))
        elif sku != mpn:
            hatalar.append(("merchant-feed.xml",
                            "sayfa sku != feed g:mpn: pid=%r sku=%r g:mpn=%r" % (pid, sku, mpn)))


def _render_sku(pid):
    """Sentetik urunu render_product'tan gecirip JSON-LD Product.sku'sunu dondurur."""
    p = {"id": pid, "kategori": "Tamirat", "baslik": "Sentetik Test Urunu",
         "aciklama": "Sentetik test aciklamasi.", "fiyat": "850 TL",
         "gorseller": ["https://media.pruvo3d.com/urunler/sentetik-1.jpg"], "marka": []}
    html_icerik = B.render_product(p, [p])
    for blok in LD_RE.findall(html_icerik):
        try:
            veri = json.loads(blok)
        except ValueError:
            continue
        for prod in _product_objeleri(veri):
            if "sku" in prod:
                return prod["sku"]
    return None


def sentetik_nobet(hatalar):
    """C katmani: katalogdan BAGIMSIZ mutasyon-kaniti (uzun + kisa id kod yolu)."""
    uzun_pid = "sentetik-cok-uzun-urun-kimligi-" + ("x" * 30)   # 60 karakter (>50)
    assert len(uzun_pid) > SKU_MAX, "sentetik uzun id 50'yi asmali"
    sku = _render_sku(uzun_pid)
    if sku is None:
        hatalar.append(("sentetik", "uzun-id render_product ciktisinda JSON-LD sku bulunamadi"))
    else:
        beklenen = B.feed_id(uzun_pid)
        if len(sku) > SKU_MAX:
            hatalar.append(("sentetik", "UZUN-id sku %d > %d — build.py sku'yu kisaltmiyor "
                            "(«sku»: pid gerilemesi?): %r" % (len(sku), SKU_MAX, sku)))
        if sku == uzun_pid:
            hatalar.append(("sentetik", "UZUN-id sku HAM pid ile ayni (kisaltilmadi): %r" % (sku,)))
        if sku != beklenen:
            hatalar.append(("sentetik", "UZUN-id sku != feed_id: sku=%r feed_id=%r" % (sku, beklenen)))

    kisa_pid = "sentetik-kisa-id"                                # <=50
    assert len(kisa_pid) <= SKU_MAX
    sku2 = _render_sku(kisa_pid)
    if sku2 is None:
        hatalar.append(("sentetik", "kisa-id render_product ciktisinda JSON-LD sku bulunamadi"))
    elif sku2 != kisa_pid:
        hatalar.append(("sentetik", "KISA-id sku HAM pid DEGIL (churn): sku=%r pid=%r"
                        % (sku2, kisa_pid)))


def main():
    hatalar = []
    sayaclar = {"sayfa": 0, "blok": 0, "product": 0, "sku": 0, "uzun_sku": 0,
                "uzun_id_sayfa": 0, "feed_item": 0, "feed_uzun_id": 0}

    sayfa_sku = sinif_geneli(hatalar, sayaclar)
    if sayfa_sku is None:
        return 1
    feed_capraz(sayfa_sku, hatalar, sayaclar)
    sentetik_nobet(hatalar)

    print("Taranan urun sayfasi   : %d" % sayaclar["sayfa"])
    print("JSON-LD blok           : %d" % sayaclar["blok"])
    print("Product objesi         : %d" % sayaclar["product"])
    print("sku'lu Product         : %d" % sayaclar["sku"])
    print("sku > %d karakter       : %d" % (SKU_MAX, sayaclar["uzun_sku"]))
    print("Uzun-id (pid>%d) sayfa  : %d" % (SKU_MAX, sayaclar["uzun_id_sayfa"]))
    print("Feed item / uzun-id    : %d / %d" % (sayaclar["feed_item"], sayaclar["feed_uzun_id"]))
    print("Toplam ihlal           : %d" % len(hatalar))

    # SINIF-GENELI GERILEME: hicbir Product sku tasimiyorsa build sku'yu komple
    # dusurmus demektir — tekil ihlal uretmez, burada KIRMIZI.
    if sayaclar["sku"] == 0:
        print("\nKIRMIZI: sku'lu Product sayisi 0 — TAM SINIF GERILEMESI "
              "(build hicbir sayfaya sku basmiyor).")
        return 1

    if hatalar:
        print("\nIlk 10 ihlal:")
        for sayfa, msg in hatalar[:10]:
            print("  %s — %s" % (sayfa, msg))
        print("\nKIRMIZI")
        return 1
    print("\nYESIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
