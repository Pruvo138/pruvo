#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meta Pixel (tarayıcı) kabul testi — build.py'nin ürettiği sayfalarda pikselin doğru,
RIZA-KAPILI ve funnel event'leriyle basıldığını doğrular. Deterministik + hızlı:
tam build KOŞMAZ, yalnız render_product + render_content_page'i örnek girdiyle çağırır.

Çalıştır:  python3 tools/meta-piksel-test.py   -> PASS/FAIL döker, hepsi geçerse exit 0.

Doğrulananlar (görev kabul kriterleri):
  1) Meta base var + RIZA-KAPILI (fbevents.js yalnız pruvo_onay_analitik==="kabul" iken yüklenir)
  2) PageView var
  3) Ürün sayfasında ViewContent + örnek slug content_ids + content_type "product"
  4) İçerik sayfasında ViewContent YOK
  5) fbq("init","2150216885710153") var
  (+ ek: ürün AddToCart var; içerik sayfası da Meta base + PageView taşır)
  (+ S1-S7: elle yazılmış statik yasal sayfaya meta_ekle() base + PageView enjekte eder,
     ViewContent YOK, GA korunur, idempotent)
"""

import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import build as B  # noqa: E402

# --- YAYIN YUZEYI SARGISI (2 Agu 2026) --------------------------------------------
# Sayfanin ORTAK CSS/JS'i artik sayfaya gomulu degil: icerik-adresli /varlik/<ad>-<hash>
# dosyalarindan REFERANSLA geliyor. Bu kapi sayfanin <script>/<style> govdesinde kural
# ariyor; ham HTML'i okursa aradigi kod TARAYICIYA INMEYE DEVAM ETTIGI HALDE metinde
# bulunmaz ve kapi SESSIZCE yesile doner (olculen yuzey kucuulur). Bu yuzden render
# ciktisi TEK KAYNAK tools/yayin_yuzey.py'den gecirilir: /varlik/ referanslari
# icerikleriyle yerine konur, olculen metin tasima ONCESIYLE ayni kurallari tasir.
import yayin_yuzey                                                       # noqa: E402
_HAM_RENDER_PRODUCT = B.render_product


def _yayin_yuzeyli_render_product(*a, **k):
    return yayin_yuzey.govde(_HAM_RENDER_PRODUCT(*a, **k))


B.render_product = _yayin_yuzeyli_render_product
# ----------------------------------------------------------------------------------


PIXEL = "2150216885710153"
ORNEK_SLUG = "meta-test-oto-parca"

sonuclar = []


def kontrol(ad, kosul):
    sonuclar.append((ad, bool(kosul)))


def _once(metin, a, b):
    """a alt-dizesi b'den ÖNCE geçiyor mu (ikisi de var olmalı)."""
    ia, ib = metin.find(a), metin.find(b)
    return ia != -1 and ib != -1 and ia < ib


# ----- örnek girdilerle render -----
ornek_urun = {
    "id": ORNEK_SLUG,
    "kategori": "Otomobil",
    "marka": ["Test"],
    "baslik": "Örnek Oto Parça",
    "aciklama": "Meta piksel testi için örnek ürün açıklaması.",
    "fiyat": "850 TL",
    "gorseller": ["https://media.pruvo3d.com/urunler/meta-test-1.jpg"],
}
urun_html = B.render_product(ornek_urun, [ornek_urun])

# İçerik/yasal sayfa örneği (CONTENT_PAGES ilk kaydı) — ürün DEĞİL.
c_slug, c_baslik, c_meta, c_fn = B.CONTENT_PAGES[0]
icerik_html = B.render_content_page(c_slug, c_baslik, c_meta, c_fn())

FB_SRC = "connect.facebook.net/en_US/fbevents.js"
KABUL_GUARD = 'localStorage.getItem("pruvo_onay_analitik") !== "kabul"'

# ----- 1) Meta base + rıza-kapılı -----
kontrol("1a Ürün: Meta base (fbevents.js) var", FB_SRC in urun_html)
kontrol("1b Ürün: rıza anahtarı (pruvo_onay_analitik) var", "pruvo_onay_analitik" in urun_html)
kontrol("1c Ürün: fbevents.js RIZA GUARD'ın İÇİNDE (guard, load'dan ÖNCE)",
        _once(urun_html, KABUL_GUARD, FB_SRC))
kontrol("1d Ürün: pruvoMetaBaslat + pruvoMetaTrack yardımcıları var",
        "pruvoMetaBaslat" in urun_html and "pruvoMetaTrack" in urun_html)

# ----- 2) PageView -----
kontrol('2 Ürün: PageView var', 'window.fbq("track", "PageView")' in urun_html)

# ----- 3) Ürün ViewContent + content_ids(slug) + content_type product -----
kontrol('3a Ürün: ViewContent var', 'pruvoMetaTrack("ViewContent"' in urun_html)
kontrol('3b Ürün: ViewContent content_ids = örnek slug',
        '"content_ids":["%s"]' % ORNEK_SLUG in urun_html)
kontrol('3c Ürün: content_type "product"', '"content_type":"product"' in urun_html)
kontrol('3d Ürün: currency "TRY"', '"currency":"TRY"' in urun_html)

# ----- 4) İçerik sayfasında ViewContent ATILMAZ -----
# DİKKAT: "ViewContent" kelimesi head snippet YORUMUNDA (event listesi) geçer; asıl kural
# olayın FIRLATILMAMASI -> firing çağrısını ara, düz kelimeyi değil.
kontrol("4 İçerik: ViewContent olayı ATILMAZ (firing çağrısı yok)",
        'pruvoMetaTrack("ViewContent"' not in icerik_html)

# ----- 5) fbq init pixel id -----
kontrol('5a Ürün: fbq("init","%s") var' % PIXEL,
        'window.fbq("init", "%s")' % PIXEL in urun_html)
kontrol('5b İçerik: fbq("init","%s") var' % PIXEL,
        'window.fbq("init", "%s")' % PIXEL in icerik_html)

# ----- ek funnel + içerik sayfası kapsamı -----
kontrol('E1 Ürün: AddToCart var', 'pruvoMetaTrack("AddToCart"' in urun_html)
kontrol("E2 İçerik: Meta base + PageView var (ürün-dışı sayfa da izlenir)",
        FB_SRC in icerik_html and 'window.fbq("track", "PageView")' in icerik_html)
kontrol("E3 İçerik: rıza guard load'dan önce", _once(icerik_html, KABUL_GUARD, FB_SRC))

# ----- statik yasal sayfa (hakkimizda/iletisim/sss/gizlilik): Meta piksel ENJEKTE edilir -----
# Bu 4 sayfa build.py'de render_content_page ile ÜRETİLMEZ; elle yazılmış statik dosyadır ve
# GA gömülü ama Meta piksel meta_ekle() ile enjekte edilir. Deterministik test: gerçek dosyaya
# bağlanmadan temsili bir statik <head> (GA + attribution bloğu + <title>) üzerinde meta_ekle çalıştır.
sahte_statik = (
    '<!DOCTYPE html>\n<html lang="tr">\n<head>\n<meta charset="UTF-8">\n'
    + B.GA_HEAD_SNIPPET + "\n"
    + B.ATTRIBUTION_START + "\n<script>/*attribution*/</script>\n" + B.ATTRIBUTION_END + "\n"
    + "<title>Örnek Statik Sayfa — PRUVO</title>\n"
    + '<meta name="description" content="x">\n</head>\n<body>Statik gövde</body>\n</html>'
)
statik_html = B.meta_ekle(sahte_statik)

kontrol("S1 Statik: Meta base (fbevents.js) enjekte edildi", FB_SRC in statik_html)
kontrol("S2 Statik: rıza guard var + fbevents.js'ten ÖNCE", _once(statik_html, KABUL_GUARD, FB_SRC))
kontrol('S3 Statik: PageView var', 'window.fbq("track", "PageView")' in statik_html)
kontrol('S4 Statik: fbq("init","%s") var' % PIXEL,
        'window.fbq("init", "%s")' % PIXEL in statik_html)
kontrol("S5 Statik: ViewContent olayı ATILMAZ (ürün değil, base+PageView)",
        'pruvoMetaTrack("ViewContent"' not in statik_html)
kontrol("S6 Statik: GA KORUNDU (Meta enjekte GA'yı ezmedi)",
        "G-5V53CQMSCE" in statik_html and "gtag(" in statik_html)
kontrol("S7 Statik: idempotent (2. koşu çift enjekte etmez, tek META bloğu)",
        B.meta_ekle(statik_html) == statik_html and statik_html.count(B.META_START) == 1)

# ----- YUKARI-ÇIK OKU (Okan, 3 Ağu — gözlem): ana sayfada/katalogda çalışıyordu ama marka/model,
# yasal ve landing/SEO sayfalarında YOKTU. build.py'nin TEK KAYNAKTAN (TOP_BTN_BLOCK_HTML +
# top_btn_ekle) ürettiği/enjekte ettiği buton, ürün sayfasıyla BİREBİR AYNI id/aria-label/JS
# davranışını taşıyor mu + statik yasal sayfaya idempotent enjekte ediliyor mu — burada ölçülür
# (ayrı dosya AÇILMAZ: CI kapsam kapısı yalnız deploy.yml'de FİİLEN koşulan dosyaları tanır;
# bu dosya zaten koşuyor ve render_product/render_content_page/statik enjeksiyon örneklerini
# ÇOKTAN üretiyor — ikinci bir jeneratör çağrısı AÇILMAZ, aynı örnekler yeniden kullanılır).
BTN_ID = 'id="topBtn"'
BTN_ARIA = 'aria-label="Yukarı çık"'
BTN_JS_ANKOR = 'topBtn.classList.toggle("show", window.scrollY > 600)'

kontrol("B1 Ürün: yukarı-çık butonu TEKİL (regresyon yok)", urun_html.count(BTN_ID) == 1)
kontrol("B2 Ürün: aria-label var", BTN_ARIA in urun_html)

kontrol("B3 İçerik/landing: yukarı-çık butonu TEKİL", icerik_html.count(BTN_ID) == 1)
kontrol("B4 İçerik/landing: aria-label var", BTN_ARIA in icerik_html)
kontrol("B5 İçerik/landing: scroll/tıklama kablolaması var",
        BTN_JS_ANKOR in icerik_html and "topBtn.onclick=function(){ window.scrollTo({top:0" in icerik_html)

statik_btn_html = B.top_btn_ekle(statik_html)
kontrol("B6 Statik yasal sayfa: yukarı-çık butonu enjekte edildi (tekil)",
        statik_btn_html.count(BTN_ID) == 1)
kontrol("B7 Statik yasal sayfa: aria-label var", BTN_ARIA in statik_btn_html)
kontrol("B8 Statik yasal sayfa: idempotent (2. koşu çift buton üretmez)",
        B.top_btn_ekle(statik_btn_html) == statik_btn_html
        and statik_btn_html.count(B.TOP_BTN_START) == 1)
kontrol("B9 Statik yasal sayfa: Meta/GA/attribution blokları BOZULMADI (enjeksiyonlar birbirini ezmez)",
        FB_SRC in statik_btn_html and "G-5V53CQMSCE" in statik_btn_html
        and B.ATTRIBUTION_START in statik_btn_html)

# ----- rapor -----
gecen = sum(1 for _, ok in sonuclar if ok)
kalan = len(sonuclar) - gecen
for ad, ok in sonuclar:
    print(("PASS  " if ok else "FAIL  ") + ad)
print("-" * 48)
print("Toplam: %d  |  PASS: %d  |  FAIL: %d" % (len(sonuclar), gecen, kalan))
sys.exit(0 if kalan == 0 else 1)
