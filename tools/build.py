#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRUVO statik sayfa üreticisi.

urunler.json'u okur ve her ürün için Google'da çıkabilen, tam SEO'lu
kendi adresine sahip statik bir sayfa üretir:  /urun/<id>/index.html

Ayrıca sitemap.xml, robots.txt, .nojekyll ve Google Merchant Center ürün
feed'ini (merchant-feed.xml — sadece sabit fiyatlı ürünler) üretir.

Ürün ekleme akışı (LOKALDE ÇALIŞTIRMA — CI üretir):
  1) urunler.json'un başına yeni ürünü ekle
  2) git add urunler.json && commit && push
  3) GitHub Actions (deploy.yml) bu betiği sunucuda çalıştırıp Pages'e yayınlar.
     Üretilenler (urun/, sitemap.xml, robots.txt, merchant-feed.xml, .nojekyll)
     gitignore'dadır; git'e GİRMEZ.

Harici bağımlılık YOK (saf Python 3 standart kütüphane).
"""

import os
import re
import json
import math
import shutil
import subprocess
import html
import hashlib
import datetime
import sys
from urllib.parse import quote as _urlq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sayfalar import (SELLER, PAY_BAND_HTML, FOOT_NAV_HTML,
                      CONTENT_CSS, CONTENT_PAGES, SITEMAP_SLUGS,
                      STATIK_SAYFALAR, PV_SCRIPT_HTML)
import filament_ortak
import marka_model_build
import sitemap_damga
# CIP INDEKSI — ana sayfa MARKA/GRUP/MODEL cip satirlarinin CAPRAZ DARALMA tablosu.
# YALNIZ yayin kopyasina gomulur (bkz. yayin_index): indeks urunler.json'dan turer, kaynak
# index.html'e yazilsaydi her urun partisi blogu bayatlatir ve baska bir mimarin akisini
# kilitlerdi. Modul adinda tire oldugu icin importlib ile yuklenir.
def _cip_indeks_yukle():
    import importlib.util
    _yol = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cip-indeks.py")
    _spec = importlib.util.spec_from_file_location("cip_indeks", _yol)
    if _spec is None:
        raise SystemExit("HATA: tools/cip-indeks.py bulunamadi — cip indeksi uretilemez "
                         "(fail-closed: capraz daralma canlida sessizce kaybolurdu).")
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    return _mod
cip_indeks = _cip_indeks_yukle()
import landing_hub_build
import yorum_soy
# `altkategori` (kategori ICINDEKI daraltma etiketi) TEK KAYNAKTAN okunur: arama.py
# altkategori_kanonik(). Burada ikinci bir "gecerli mi" mantigi YAZILMAZ — yazilsaydi
# sayfada gorunen etiket ile D1'e/Ege'ye giden deger sessizce ayrisabilirdi
# ([[ikiz-tanim-sessiz-ayrisma]]). Fonksiyon FAIL-CLOSED: izinli kumede olmayan /
# imza tasiyan / tipi yanlis / eksik her deger "" doner -> sayfada HIC basilmaz.
import arama

# ------------------------------------------------------------------ ayarlar
SITE = "https://pruvo3d.com"
WHATSAPP = "905451386526"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT, "urunler.json")
URUN_DIR = os.path.join(ROOT, "urun")
# Parametrik ("Ölçüye Özel" sarı seri) konfigüratör şemaları — jenerator/urunler/<id>.json.
# Şeması olan parametrik ürünün sayfasına konfigüratör UI basılır; olmayana dokunulmaz.
JEN_URUN_DIR = os.path.join(ROOT, "jenerator", "urunler")
CATEGORIES = ["Marin", "Otomobil", "Motosiklet", "Bisiklet", "Tamirat", "Ev", "Ofis", "Elektronik", "Kamera", "Bahçe", "Dekorasyon", "Oyun/Hobi"]
# GİZLİ kategoriler (Okan, 17 Tem): ana sayfa menüsünde GÖRÜNMEZ ama ürün sayfaları,
# arama ve ?kategori=<ad> linki çalışır. "Jeneratör" = TÜM parametrik (sarı seri) ürünler.
# "Skan Art" (Okan, 23 Tem) = İskandinav tasarım dilli dekor/heykel alt-serisi; aynı sınıf.
# index.html'deki GIZLI_KATEGORILER ile BİRLİKTE güncelle (CATEGORIES kuralının aynısı).
NAV_GIZLI = ["Jeneratör", "Skan Art"]


def fiyat_normalize(p):
    """Katalog yukleme sinirinda `fiyat` alanini kanonik metne cevirir."""
    fiyat = p.get("fiyat")
    if isinstance(fiyat, str):
        return p
    if fiyat is None:
        p["fiyat"] = ""
        return p
    if isinstance(fiyat, bool) or not isinstance(fiyat, (int, float)):
        raise SystemExit("HATA: urun %s fiyat tipi desteklenmiyor: %s"
                         % (p.get("id", "<id-yok>"), type(fiyat).__name__))
    if isinstance(fiyat, float) and not math.isfinite(fiyat):
        raise SystemExit("HATA: urun %s fiyat tipi desteklenmiyor: %s"
                         % (p.get("id", "<id-yok>"), type(fiyat).__name__))
    metin = str(int(fiyat)) if float(fiyat).is_integer() else str(fiyat)
    p["fiyat"] = metin + " TL"
    return p


def load_products(path=JSON_PATH):
    """Katalogu yukler; fiyat tipini tum tuketicilerden once tek noktada duzeltir."""
    with open(path, encoding="utf-8") as f:
        products = json.load(f)
    for p in products:
        fiyat_normalize(p)
    return products

# ---------------------------------------------------------------------------
# 🔴 GIZLI SERI ADI -> MUSTERIYE GORUNEN ETIKET (11 Agu, canli kural ihlali onarimi)
#
# CLAUDE.md: parametrik/"jeneratör" semasi ve arkasindaki uretec IC bilgidir; ic seri adi
# musteriye gorunen yuzeyde GECMEZ. Bugune kadar parametrik urun sayfasi kategori ROZETINDE,
# BREADCRUMB'da, JSON-LD `category`/`BreadcrumbList`inde ve "Diğer ... ürünleri" basliginda
# "Jeneratör" yaziyordu -> AKTIF IHLAL.
#
# KARAR DEFTERI DEGIL, KANONIK ESLEME: NAV_GIZLI'daki HER gizli seri icin burada acik bir
# karar olmak ZORUNDADIR (asagidaki fail-closed kontrol). Karar ya bir GORUNUR ETIKET'tir
# (ad ic bilgidir, degistirilir) ya da None'dir (ad publikte zaten kullaniliyor). Yeni bir
# gizli seri NAV_GIZLI'ya eklenip burada karara baglanmazsa build DUSER -> "elle tutulan
# defter bayatlar" sinifi yapisal olarak kapali ([[envanter-drift-parti-basina]]).
#
# ⚠️ DONUSUM YALNIZ `parametrik: true` URUNDE UYGULANIR — YANLIS-POZITIF EKSENI:
# "Jeneratör" ayni zamanda 17 GERCEK jenerator yedek parcasinin (Honda EU20i, Yamaha EF3000
# ...) kategorisidir; orada kelime musterinin ARADIGI kelimedir ve KALIR. Ic sizinti,
# kelimenin kendisi degil, kelimenin PARAMETRIK SERININ etiketi olarak gorunmesidir.
GIZLI_SERI_KARARI = {
    # ic ad -> musteriye gorunen etiket (None = ad publikte guvenli, oldugu gibi kalir)
    "Jeneratör": "Ölçüye Özel Üretim",   # sari/parametrik seri; banner dili "Ölçüne özel"
    "Skan Art": None,                    # seri adi ana sayfa banner'inda ZATEN yaziyor
}
_karar_eksik = [k for k in NAV_GIZLI if k not in GIZLI_SERI_KARARI]
if _karar_eksik:
    raise SystemExit("GIZLI_SERI_KARARI eksik: %s — gizli seri adinin musteriye gorunup "
                     "gorunmeyecegi KARARA baglanmadan sayfa uretilemez." % ", ".join(_karar_eksik))
# Ic (musteriye gosterilmeyecek) seri adlari + gorunur karsiliklari. Kapi bu sozlukten turer.
IC_SERI_ETIKET = {k: v for k, v in GIZLI_SERI_KARARI.items() if v}


def gorunur_kategori(p):
    """Urunun MUSTERIYE GORUNEN kategori etiketi.

    VERI DEGISMEZ: `p["kategori"]`, `urunler.json`, D1 ve sayfadaki `URUN` JSON blogu ic
    adi tasimaya devam eder (arama/filtre/fiyat kollari ona bakar). Degisen tek sey
    GORUNEN metindir."""
    kat = p.get("kategori") or ""
    if p.get("parametrik") and kat in IC_SERI_ETIKET:
        return IC_SERI_ETIKET[kat]
    return kat
# Malzeme/renk seçicisi + kompakt ikon düzeni (Adet + sepet/WhatsApp ikonu üstte) bu
# kategorilerde gösterilir. Okan 23 Tem: Dekorasyon + Oyun/Hobi de standart ürün kartını
# (Marin/Otomobil ile birebir) alır — eski geniş sayfa-altı buton düzeni kalktı.
# secenekler.js'deki FONKSIYONEL_KATEGORILER ile BİRLİKTE güncelle (tek karar iki yerde).
FONKSIYONEL_KATEGORILER = ["Otomobil", "Motosiklet", "Tamirat", "Elektronik", "Ev", "Marin", "Bisiklet", "Bahçe", "Ofis", "Kamera", "Dekorasyon", "Oyun/Hobi", "Skan Art"]

# "Ilgili urunler" YEDEK HAVUZU (23 Tem, olculdu). Ilgili-urun bolumu AYNI kategoriden
# beslenir; ince bir alt-seride (Skan Art'ta bugun TEK urun) aday havuzu BOSALIR ve
# <section class="related"> HIC basilmaz -> sayfa 8 ic linkini SESSIZCE kaybeder
# (olculdu: kurt sayfasi 8 -> 0 rel-card, base'e gore tek fark buydu). Alt-seri hangi ana
# kategoriden ayrildiysa yedek havuz orasidir; boyle bir esleme YOKSA davranis eskisi gibi.
AKRABA_KATEGORI = {"Skan Art": "Dekorasyon"}
# Yedek havuz bu esigin ALTINDA devreye girer (ust sinir zaten 8).
REL_EN_AZ = 4

# Malzeme katsayilari / renk listesi / adet araligi TEK KAYNAK: /secenekler.js.
# Buraya kopyalanmaz — secici HTML'inin "(+%30)" etiketleri o dosyadan OKUNUR ki katsayi
# degisince etiket sessizce eski kalmasin (Worker, sepet ve bu sablon ayni tabloyu gorur).
SECENEKLER_JS = os.path.join(ROOT, "secenekler.js")


# ------------------------------------------------------------------ GA4 + KVKK onay (Consent Mode v2)
# gtag.js client tag'i KVKK-uyumlu: Consent Mode v2 ile analytics_storage (ve tum ad_* alanlari)
# VARSAYILAN 'denied' baslar -> GA cerez YAZMAZ / olcum GONDERMEZ. Ziyaretci banner'dan "Kabul Et"
# derse analytics_storage 'granted' olur (ad_* denied kalir; client reklam pikseli yok), secim
# localStorage'a yazilir ve banner bir daha cikmaz. Olcum Kimligi G-5V53CQMSCE GIZLI DEGIL.
# TEK KAYNAK (drift'e karsi): AYNI iki blok index.html + statik sayfalarda (hakkimizda/iletisim/
# sss/gizlilik) birebir tekrar eder. Harici lib YOK; sadece gtag.js Google'dan yuklenir (zorunlu
# istisna — analytics'in kendisi). GA_HEAD_SNIPPET <head>'e, GA_BANNER_SNIPPET </body> oncesine.
GA_MEASUREMENT_ID = "G-5V53CQMSCE"

ATTRIBUTION_JS_PATH = os.path.join(ROOT, "attribution-ref.js")
ATTRIBUTION_START = "<!-- PRUVO attribution module: start -->"
ATTRIBUTION_END = "<!-- PRUVO attribution module: end -->"


def attribution_kaynak():
    """attribution-ref.js gövdesi — TEK KAYNAK. İki basım yolu (inline + /varlik/) da
    BU dizeden türer; elle tutulan ikinci bir kopya YOK ([[ikiz-tanim-sessiz-ayrisma]])."""
    with open(ATTRIBUTION_JS_PATH, encoding="utf-8") as f:
        return f.read().strip()


def attribution_head_snippet():
    """Tek kaynak modülü inline basar; yayın beyaz listesine yeni varlık gerekmez.

    KİMİN İÇİN: elle yazılmış 4 statik yasal sayfa (attribution_ekle), ana sayfanın
    yayın kopyası (yayin_index) ve marka/model + landing + içerik şablonları. Bunlar
    SAYICA az (~1.300 sayfa) — gömülü kalmaları yayın ölçeğinde ölçülebilir bir yük
    değil, buna karşılık byte-birebirlik kapıları (tools/enjeksiyon-kapisi.py) ve
    marka/model attribution zemin+tavan ekseni (tools/marka-model-test.py) tam da
    GÖMÜLÜ gövdeyi ölçer. Ölçek kaldıracı ürün sayfalarındadır (aşağıya bak)."""
    return ATTRIBUTION_START + "\n<script>\n" + attribution_kaynak() + "\n</script>\n" + ATTRIBUTION_END


def attribution_varlik_head():
    """AYNI tek kaynak, sayfaya GÖMÜLMEDEN: içerik-adresli /varlik/atif-<hash>.js referansı.

    NEDEN (ölçüldü, 6 Ağu 2026): atıf modülü ürün sayfasına inline basılıyordu ve yayına
    inen (yorumu soyulmuş) hâli sayfa başına 10.768 bayt tutuyordu. 21.185 ürün sayfasında
    bu, açılmış yayın artefaktının 216,5 MiB'ı demekti — 1 GB'lık GitHub Pages sınırının
    beşte birinden fazlası, hem de HER SAYFADA BİREBİR AYNI bayt. Blok PAGE_CSS ve ürün
    JS'iyle aynı mekanizmaya (varlik_adres) alındı: same-origin /varlik/ altında TEK dosya,
    adı içeriğinin sha256'sından türüyor.

    ⚠️ HARİCİ HOST/CDN/KÜTÜPHANE YOK — dosya kendi origin'imizde; dışarıdan hiçbir şey
    çekilmez. ÖNBELLEK: ad içerikten türediği için aynı adın ÜSTÜNE yazılmaz; bir bayt
    değişirse ad değişir, bayat modül servis edilemez ([[r2-sessiz-uzerine-yazma]]).

    🔴 `defer`/`async` EKLENMEZ: modül `window.pruvoRef` / `window.pruvoRefRiza`'yı tanımlar
    ve sayfanın SONRAKİ satır-içi script'leri (rıza bannerı, WhatsApp huni prefill'i) bunları
    çağırır. Düz harici <script> tıpkı gömülü blok gibi SIRAYLA ve parse'ı bloklayarak koşar;
    defer eklemek çalışma sırasını sessizce tersine çevirir ve atıf ekranda hata vermeden
    kaybolurdu."""
    return (ATTRIBUTION_START + '\n<script src="'
            + varlik_adres("atif", "js", attribution_kaynak())
            + '"></script>\n' + ATTRIBUTION_END)


def attribution_ekle(html_metni):
    """Attribution bloğunu ekler veya mevcut bloğu tek kaynaktan yeniler.

    ⚠️ re.sub'un REPLACEMENT dizesi backslash kaçışı yorumlar: JS kaynağındaki `\\n` GERÇEK
    satır sonuna döner (string literali kırılır -> sayfa parse edilmez) ve `\\s` gibi geçersiz
    kaçış `re.error` ile TÜM build'i düşürür. Enjekte edilen gövde VERİ'dir, kalıp değil ->
    lambda ile birebir konur (kaçış yorumlanmaz). Aynı tuzak meta_ekle'de de bu şekilde
    kapatılmıştır. Kaynak dosyada `\\n`/`\\s` kullanımını kısıtlamak ÇÖZÜM DEĞİL — enjeksiyon
    yolu kaçışa duyarsız olmalı. Kapı: tools/enjeksiyon-kapisi.py (bayt-birebir + node --check).
    """
    snippet = attribution_head_snippet()
    pattern = re.compile(re.escape(ATTRIBUTION_START) + r".*?" +
                         re.escape(ATTRIBUTION_END), re.S)
    if pattern.search(html_metni):
        return pattern.sub(lambda m: snippet, html_metni, count=1)
    needle = "</script>\n<title>"
    if needle not in html_metni:
        raise RuntimeError("attribution ekleme noktasi bulunamadi")
    return html_metni.replace(needle, "</script>\n" + snippet + "\n<title>", 1)

GA_HEAD_SNIPPET = """<!-- Google Analytics 4 (gtag.js) + Consent Mode v2 — KVKK uyumlu. Ölçüm Kimliği G-5V53CQMSCE herkese açıktır. -->
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  /* Açık rıza (onay) gelene kadar TÜM depolama REDDEDİLMİŞ (denied) başlar:
     GA çerez yazmaz, ölçüm göndermez. */
  gtag('consent', 'default', {
    'ad_storage': 'denied',
    'ad_user_data': 'denied',
    'ad_personalization': 'denied',
    'analytics_storage': 'denied',
    'wait_for_update': 500
  });
  /* ad_storage 'denied' iken Google'in SART KOSTUGU iki ayar (Consent Mode v2).
     Rizaya BAGLI DEGIL — riza olmadan da calisan tek reklam-olcumu kazanimi:
       url_passthrough    -> reklam tiklama kimligi (gclid/gbraid/wbraid) CEREZ
                             YAZILMADAN sayfadan sayfaya URL uzerinde tasinir.
       ads_data_redaction -> riza yokken reklam isteklerinden tanimlayicilar SILINIR.
     Bu iki cagri hicbir alani 'granted' YAPMAZ; varsayilan denied AYNEN kalir. */
  gtag('set', 'url_passthrough', true);
  gtag('set', 'ads_data_redaction', true);
  /* Riza verilince acilacak alan kumesi — TEK KANONIK KAYNAK; varsayilan denied KALIR. */
  window.PRUVO_RIZA_ALANLARI = ['analytics_storage','ad_storage','ad_user_data','ad_personalization'];
  window.PRUVO_RIZA_KAPSAMI = 'analitik+reklam';
  window.pruvoRizaUygula = function(d){ var g={},a=window.PRUVO_RIZA_ALANLARI,i; for(i=0;i<a.length;i++){ g[a[i]]=d; } gtag('consent','update',g); };
  /* GA4 e-ticaret olay gondericisi — reklam olcumunun HUNI ayagi (sayfa goruntuleme tek
     basina kampanya karari verdirmez). Meta yuzeyiyle AYNI riza anahtarina baglidir
     (pruvo_onay_analitik === "kabul"): riza yoksa olay GONDERILMEZ.
     Yalniz beyaz listedeki olay adlari gecer; bilinmeyen ad sessizce DUSER. Satin alma
     olayi SUNUCUDAN gider — buradan da gonderilse ayni islem IKI KEZ sayilirdi.
     Olay parametresine YALNIZ katalog alanlari girer (item_id/item_name/item_category/
     price/quantity/currency/value); kisisel veri (ad/telefon/e-posta/adres) GIRMEZ. */
  window.PRUVO_GA4_OLAYLARI = ['view_item','add_to_cart','begin_checkout'];
  window.pruvoGA4Track = function(olay, veri){
    try { if(localStorage.getItem('pruvo_onay_analitik') !== 'kabul'){ return; } } catch(e){ return; }
    var a = window.PRUVO_GA4_OLAYLARI, i;
    for(i=0;i<a.length;i++){ if(a[i] === olay){ gtag('event', olay, veri); return; } } };
  /* Onayı geri yükle. ESKİ (DAR) kayıt reklam alanlarını KAPSAMAZ: yalnız analitik açılır. */
  try { if (localStorage.getItem('pruvo_onay_analitik') === 'kabul') {
    if (localStorage.getItem('pruvo_onay_kapsam') === window.PRUVO_RIZA_KAPSAMI) { window.pruvoRizaUygula('granted'); }
    else { gtag('consent', 'update', { 'analytics_storage': 'granted' }); } } } catch(e){}
</script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-5V53CQMSCE"></script>
<script>
  gtag('js', new Date());
  gtag('config', 'AW-18330673570');
  gtag('config', 'G-5V53CQMSCE', { 'anonymize_ip': true });
</script>"""

# ------------------------------------------------------------------ Meta Pixel (tarayıcı) — rıza kapılı
# GA ile AYNI onay anahtarını kullanır: pruvo_onay_analitik === "kabul" olmadan piksel YÜKLENMEZ,
# fbevents.js indirilmez, hiçbir Meta ağ çağrısı olmaz. Rıza verilince (banner "Kabul Et" ya da zaten
# kayıtlı) fbq init olur + PageView atılır. Piksel Kimliği herkese açıktır (public var, sır değil).
# Sunucu-tarafı CAPI Purchase'ı (shop/src/olcum.js) event_id = siparis_no ile dedup eder; tarayıcı
# Purchase yüzeyi de AYNI siparis_no'yu eventID olarak kullanır (çift sayım olmaz).
# window.pruvoMetaTrack(): sayfa içi ViewContent/AddToCart/InitiateCheckout/Purchase yüzeyleri bunu
# çağırır — piksel hazır (rıza var) değilse sessizce yutar. TEK KAYNAK: aynı blok index.html'de
# birebir tekrar eder (GA snippet'lerindeki gibi) — değiştirirsen İKİSİNİ de değiştir.
META_PIXEL_ID = "2150216885710153"

META_HEAD_SNIPPET = """<!-- Meta Pixel — KVKK/rıza kapılı. Piksel Kimliği 2150216885710153 herkese açıktır.
     GA ile AYNI onay anahtarı (pruvo_onay_analitik==="kabul"): rıza YOKSA fbevents.js YÜKLENMEZ,
     hiçbir Meta ağ çağrısı olmaz. TEK KAYNAK: aynı blok index.html'de birebir tekrar eder. -->
<script>
(function(){
  window.pruvoMetaHazir = false;
  /* Pikseli yalnız açık rıza gelince YÜKLE. Rıza yoksa erken döner -> fbevents.js inmez, çağrı yok. */
  window.pruvoMetaBaslat = function(){
    if(window.pruvoMetaHazir){ return; }
    try { if(localStorage.getItem("pruvo_onay_analitik") !== "kabul"){ return; } } catch(e){ return; }
    window.pruvoMetaHazir = true;
    !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
      n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
      n.push=n;n.loaded=!0;n.version="2.0";n.queue=[];t=b.createElement(e);t.async=!0;
      t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}
      (window,document,"script","https://connect.facebook.net/en_US/fbevents.js");
    window.fbq("init", "2150216885710153");
    window.fbq("track", "PageView");
  };
  /* Rıza-kapılı olay gönderici: piksel hazır DEĞİLSE sessizce yut (rıza yoksa Meta çağrısı yok).
     Ürün/sepet/ödeme yüzeyleri ViewContent/AddToCart/InitiateCheckout/Purchase için bunu çağırır. */
  window.pruvoMetaTrack = function(olay, veri, opsiyon){
    if(!window.pruvoMetaHazir || typeof window.fbq !== "function"){ return; }
    if(opsiyon){ window.fbq("track", olay, veri, opsiyon); }
    else { window.fbq("track", olay, veri); }
  };
  /* Ziyaretçi daha önce onay verdiyse pikseli hemen başlat (banner çıkmaz, PageView atılır). */
  try { if(localStorage.getItem("pruvo_onay_analitik") === "kabul"){ window.pruvoMetaBaslat(); } } catch(e){}
})();
</script>"""

# Elle yazılmış statik yasal sayfalara (hakkimizda/iletisim/sss/gizlilik) Meta pikselini idempotent
# enjekte etmek için işaretçiler (attribution bloğuyla AYNI desen). build.py'nin ÜRETTİĞİ ürün/içerik
# sayfaları META_HEAD_SNIPPET'i şablonla zaten basar; statik sayfalar üretilmediği için burada eklenir.
META_START = "<!-- PRUVO meta pixel: start -->"
META_END = "<!-- PRUVO meta pixel: end -->"


def meta_ekle(html_metni):
    """Meta Pixel bloğunu statik sayfaya ekler veya mevcut bloğu TEK KAYNAKTAN (META_HEAD_SNIPPET)
    yeniler. Rıza kapısı GA ile AYNI (pruvo_onay_analitik==="kabul"); yalnız base + PageView —
    ViewContent ATILMAZ (statik sayfalar ürün değil, snippet zaten ViewContent göndermez).
    İşaretçili blok idempotenttir: tekrar koşunca çift enjekte etmez. GA'nın hemen yanına
    (attribution bloğundan önce) girer; her iki durumda da <head> içindedir."""
    snippet = META_START + "\n" + META_HEAD_SNIPPET + "\n" + META_END
    pattern = re.compile(re.escape(META_START) + r".*?" + re.escape(META_END), re.S)
    if pattern.search(html_metni):
        # re.sub replacement stringi backslash yorumlar -> lambda ile birebir koy (snippet'te
        # kaçış dizisi olsa bile bozulmasın).
        return pattern.sub(lambda m: snippet, html_metni, count=1)
    # GA head bloğu ile <title> arasına yerleştir: attribution START'ından hemen önce (attribution
    # bloğu her statik sayfada var, GA'dan sonra gelir). Bulunamazsa <title>'dan önceye düş.
    if ATTRIBUTION_START in html_metni:
        return html_metni.replace(ATTRIBUTION_START, snippet + "\n" + ATTRIBUTION_START, 1)
    if "<title>" in html_metni:
        return html_metni.replace("<title>", snippet + "\n<title>", 1)
    raise RuntimeError("meta pixel ekleme noktasi bulunamadi")


# ------------------------------------------------------------------ yukarı-çık oku (TEK KAYNAK)
# NEDEN VAR (Okan, 3 Ağu — gözlem): ↑ oku ana sayfada/katalogda çalışıyor ama marka/model,
# yasal (gizlilik/hakkimizda/iletisim/sss) ve landing/SEO sayfalarında YOKTU — bu üç ailenin
# kendi şablonu var (render_content_page burada; marka_model_build._shell; landing_hub_build._shell)
# ve hiçbiri butonu KOPYALAMADI. Davranış index.html + render_product'takiyle BİREBİR AYNI
# (eşik scrollY>600, tıklayınca yumuşak kaydırma, aria-label); CSS zaten stil_bloklari()
# üzerinden TÜM şablonlarda ortak (.top-btn tanımı yukarıda) — burada yalnız DOM + kablolama
# TEK KAYNAKTAN üretilir, kopyala-yapıştırla ÜÇ şablona ayrı ayrı GÖMÜLMEZ.
TOP_BTN_HTML = u"""<button id="topBtn" class="top-btn" aria-label="Yukarı çık">
  <svg viewBox="0 0 24 24"><path d="M12 4.6 4.6 12l1.8 1.8 4.3-4.3V20h2.6V9.5l4.3 4.3 1.8-1.8z"/></svg>
</button>"""

TOP_BTN_SCRIPT_HTML = u"""<script>
(function(){
  var topBtn=document.getElementById("topBtn");
  if(!topBtn){ return; }
  window.addEventListener("scroll",function(){
    topBtn.classList.toggle("show", window.scrollY > 600);
  },{passive:true});
  topBtn.onclick=function(){ window.scrollTo({top:0, behavior:"smooth"}); };
})();
</script>"""

TOP_BTN_BLOCK_HTML = TOP_BTN_HTML + "\n" + TOP_BTN_SCRIPT_HTML

# Elle yazılmış statik yasal sayfalara (hakkimizda/iletisim/sss/gizlilik) butonu idempotent
# enjekte etmek için işaretçiler (attribution/meta pixel bloğuyla AYNI desen).
TOP_BTN_START = "<!-- PRUVO yukari-cik oku: start -->"
TOP_BTN_END = "<!-- PRUVO yukari-cik oku: end -->"


def top_btn_ekle(html_metni):
    """Yukarı-çık okunu elle yazılmış statik sayfaya ekler veya mevcut bloğu TEK KAYNAKTAN
    (TOP_BTN_BLOCK_HTML) yeniler. attribution_ekle/meta_ekle ile AYNI idempotent işaretçi
    deseni: tekrar koşunca çift enjekte ETMEZ (çift buton regresyonu yok)."""
    snippet = TOP_BTN_START + "\n" + TOP_BTN_BLOCK_HTML + "\n" + TOP_BTN_END
    pattern = re.compile(re.escape(TOP_BTN_START) + r".*?" + re.escape(TOP_BTN_END), re.S)
    if pattern.search(html_metni):
        return pattern.sub(lambda m: snippet, html_metni, count=1)
    if "</body>" not in html_metni:
        raise RuntimeError("yukari-cik oku ekleme noktasi bulunamadi")
    return html_metni.replace("</body>", snippet + "\n</body>", 1)


GA_BANNER_SNIPPET = """<!-- KVKK çerez onay banner'ı (vanilla JS/CSS — harici kütüphane YOK). analytics_storage için açık rıza. -->
<style>
  #pruvo-cerez-onay{position:fixed;left:0;right:0;bottom:0;z-index:2147483000;
    background:#12294d;color:#fff;padding:15px 18px;box-shadow:0 -2px 14px rgba(0,0,0,.28);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    font-size:14px;line-height:1.5}
  #pruvo-cerez-onay[hidden]{display:none}
  #pruvo-cerez-onay .pco-inner{max-width:1100px;margin:0 auto;display:flex;align-items:center;
    gap:14px;flex-wrap:wrap;justify-content:space-between}
  #pruvo-cerez-onay p{margin:0;flex:1 1 320px;color:#dbe4f2}
  #pruvo-cerez-onay a{color:#fff;text-decoration:underline}
  #pruvo-cerez-onay .pco-btns{display:flex;gap:10px;flex:0 0 auto}
  #pruvo-cerez-onay button{cursor:pointer;border:none;border-radius:8px;padding:10px 18px;
    font-size:14px;font-weight:700;font-family:inherit}
  #pruvo-cerez-onay .pco-kabul{background:#d1332e;color:#fff}
  #pruvo-cerez-onay .pco-ret{background:rgba(255,255,255,.14);color:#fff;
    border:1px solid rgba(255,255,255,.4)}
  #pruvo-cerez-onay button:focus-visible{outline:3px solid #ffd166;outline-offset:2px}
</style>
<div id="pruvo-cerez-onay" role="dialog" aria-label="Çerez onayı" hidden>
  <div class="pco-inner">
    <p>Trafiği anlamak için analiz çerezleri (Google Analytics), reklamlarımızın ölçümü ve
       kişiselleştirilmesi için reklam çerezleri (Google Ads) kullanmak istiyoruz. İkisi de
       isteğe bağlıdır; onayınız olmadan çalışmazlar. Onayınızı istediğiniz zaman
       <a href="/gizlilik/">Gizlilik Politikası</a> sayfasından geri alabilirsiniz.</p>
    <div class="pco-btns">
      <button type="button" class="pco-ret" id="pco-ret">Reddet</button>
      <button type="button" class="pco-kabul" id="pco-kabul">Kabul Et</button>
    </div>
  </div>
</div>
<script>
(function(){
  var ANAHTAR = "pruvo_onay_analitik";
  var KAPSAM_ANAHTARI = "pruvo_onay_kapsam";
  function kapsamAdi(){ return window.PRUVO_RIZA_KAPSAMI || ""; }   /* kaynak koşmadıysa "" -> fail-closed */
  var el = document.getElementById("pruvo-cerez-onay");
  if(!el){ return; }
  var secim = null, kapsam = null;
  try { secim = localStorage.getItem(ANAHTAR); kapsam = localStorage.getItem(KAPSAM_ANAHTARI); } catch(e){}
  if(secim === "ret"){ return; }   /* reddedene TEKRAR SORULMAZ */
  if(secim === "kabul" && kapsam && kapsam === kapsamAdi()){ return; }   /* güncel kapsamda onaylı */
  el.hidden = false;
  function kaydet(deger){ var k = deger === "kabul" ? kapsamAdi() : ""; try { localStorage.setItem(ANAHTAR, deger); if(k){ localStorage.setItem(KAPSAM_ANAHTARI, k); } else { localStorage.removeItem(KAPSAM_ANAHTARI); } } catch(e){} if(deger !== "kabul" && typeof window.pruvoRizaUygula === "function"){ window.pruvoRizaUygula('denied'); } el.hidden = true; }
  var kabul = document.getElementById("pco-kabul");
  var ret = document.getElementById("pco-ret");
  kabul.addEventListener("click", function(){
    if(typeof window.pruvoRizaUygula === "function"){ window.pruvoRizaUygula('granted'); }
    kaydet("kabul");
    /* Meta pikseli de rıza anında başlasın (init + PageView) — kaydet() localStorage'ı 'kabul'
       yazdıktan SONRA çağrılır ki pruvoMetaBaslat rıza kontrolünden geçsin. */
    if(typeof window.pruvoMetaBaslat === "function"){ window.pruvoMetaBaslat(); }
    /* Tıklama kimliği (gclid/gbraid/wbraid) rıza kapısının ARKASINDA saklanır: rıza şimdi
       geldi → URL'de hâlâ duruyorsa bu andan itibaren yakalanabilir (sayfa yenilemesi yok). */
    if(typeof window.pruvoRefRiza === "function"){ window.pruvoRefRiza(); }
  });
  /* denied kalır + saklanmış tıklama kimliği varsa SİLİNİR (rıza geri çekme yolu). */
  ret.addEventListener("click", function(){
    kaydet("ret");
    if(typeof window.pruvoRefRiza === "function"){ window.pruvoRefRiza(); }
  });
  try { kabul.focus(); } catch(e){}
})();
</script>"""


# ------------------------------------------------------------------ script onbellek surumleme
# Yayinlanan HTML'lerde site-ici JS script src'lerine dosya iceriginin kisa hash'ini
# "?v=<hash>" olarak ekler. NEDEN: bu .js dosyalari (secenekler.js, taban-fiyatlar.js,
# jenerator/*.js) canlida cache-control: max-age=14400 (4 SAAT tarayici onbellegi) ile
# geliyor; Actions'in Cloudflare purge'u musteri TARAYICISINI temizlemez -> bayrak/fiyat
# kurali degisikligi musteriye 4 saate kadar gec ulasiyordu. Icerik degisince URL degisir
# (?v=yeni-hash) -> hem tarayici hem edge cache miss -> taze surum aninda gider. Icerik
# degismezse hash sabit kalir, onbellek bosa gitmez. KAYNAK dosyalara (index.html) elle
# surum YAZILMAZ (curur); surumleme burada build zamani otomatik yapilir.
_SURUM_CACHE = {}


def dosya_surum(dosya_yolu):
    """Dosya iceriginin kisa (10 hex) sha1 hash'i — icerik degismezse ayni kalir."""
    onbellek = _SURUM_CACHE.get(dosya_yolu)
    if onbellek is not None:
        return onbellek
    with open(dosya_yolu, "rb") as f:
        h = hashlib.sha1(f.read()).hexdigest()[:10]
    _SURUM_CACHE[dosya_yolu] = h
    return h


# YAYIN JS DIZINI — commit'li JS kaynaklarinin YORUMU SOYULMUS yayin kopyalari.
# deploy.yml _site'a BURADAN kopyalar; kaynak dosyalar (secenekler.js ...) tam
# muhendislik dokumantasyonuyla depoda KALIR. git'e GIRMEZ (.gitignore).
YAYIN_DIR = "_yayin"
# deploy.yml beyaz listesindeki commit'li JS varliklari (uretilen ikisi ayrica
# uretildikleri yerde soyulur: filament-veri.js + taban-fiyatlar.js).
SOYULACAK_JS = ("secenekler.js", "konfigur.js",
                "jenerator/hacim.js", "jenerator/konfigurator.js", "jenerator/viewer.js")


def _yayin_js_sozdizimi(hedef):
    """Yayin kopyasini GERCEK bir JS ayristiricisindan (node --check) gecirir.

    NEDEN (bagimsiz ikinci goz): yorum_soy.py kendi JS lexer'ini kullanir ve regex/bolme
    ayrimi bir SEZGIye dayanir. O sezgi bir gun yanilirsa soyma bir dizgenin/regex'in
    ICINI silebilir — hata SESSIZDIR: dosya yayinlanir, odeme JS'i tarayicida coker.
    node --check bagimsiz bir ayristirici oldugu icin o sinifi YAYINDAN ONCE yakalar.
    FAIL-CLOSED: bozuksa build DURUR; CI'da node yoksa da DURUR (setup-node bloklayici
    on-kosuldur, yani orada node HEP vardir). Yerelde node yoksa yuksek sesle uyarir."""
    try:
        p = subprocess.run(["node", "--check", hedef], capture_output=True, text=True)
    except OSError:
        if os.environ.get("GITHUB_ACTIONS"):
            print("HATA: node yok -> yayin JS sozdizimi DOGRULANAMADI (fail-closed): %s" % hedef)
            sys.exit(1)
        print("UYARI: node bulunamadi -> yayin JS sozdizimi DOGRULANAMADI (yerel kosum)")
        return
    if p.returncode != 0:
        print("HATA: yayin kopyasinin SOZDIZIMI BOZUK -> %s\n%s"
              % (hedef, (p.stderr or "")[:800]))
        sys.exit(1)


def yayin_js_yaz(rel):
    """<rel> JS kaynagini yorumu soyulmus olarak _yayin/<rel>'e yazar; yolu doner.
    Kaynak DEGISMEZ. Dosya yoksa (lokalde uretilmemis) None doner."""
    kaynak = os.path.join(ROOT, rel)
    if not os.path.isfile(kaynak):
        return None
    with open(kaynak, encoding="utf-8") as f:
        metin = f.read()
    hedef = os.path.join(ROOT, YAYIN_DIR, rel)
    d = os.path.dirname(hedef)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(yorum_soy.js_soy(metin))
    _yayin_js_sozdizimi(hedef)             # bozuk soyma YAYINLANMAZ (fail-closed)
    _SURUM_CACHE.pop(hedef, None)          # ayni kosumda yeniden uretilirse bayat hash kalmasin
    return hedef


def _yayin_yolu(rel):
    """Bir varligin YAYINLANAN kopyasinin yolu: _yayin/<rel> varsa o, yoksa kaynak.
    ?v=<hash> boylece TARAYICIYA GIDEN baytlardan turer (soyma sonrasi da dogru)."""
    y = os.path.join(ROOT, YAYIN_DIR, rel)
    return y if os.path.isfile(y) else os.path.join(ROOT, rel)


_SCRIPT_SRC_RE = re.compile(r'(<script\b[^>]*\ssrc=")(/[^"?]+\.js)(")')


def _surumle_scriptler(html_metni):
    """HTML icindeki site-ici <script src="/...js"> referanslarina ?v=<icerik-hash>
    ekler. Zaten surumlu (?v= olan — regex .js'ten hemen sonra " bekler, eslesmez) ya da
    dosyasi bulunmayan (lokalde build'siz) referansa DOKUNMAZ.
    Hash YAYINLANAN kopyadan (varsa _yayin/<rel>) hesaplanir.
    /varlik/ ALTINA DOKUNULMAZ: o dosyalarin ADI zaten icerik hash'idir (varlik_adres);
    ustune ?v= yazmak ayni bayta IKINCI bir surum ekseni verirdi ([[ikiz-tanim-sessiz-ayrisma]])."""
    def _degistir(m):
        yol = m.group(2)                      # or. "/secenekler.js"
        if yol.startswith(VARLIK_URL_ONEK):
            return m.group(0)                 # icerik-adresli varlik — surumlenmez
        dosya = _yayin_yolu(yol.lstrip("/"))
        if not os.path.isfile(dosya):
            return m.group(0)
        return m.group(1) + yol + "?v=" + dosya_surum(dosya) + m.group(3)
    return _SCRIPT_SRC_RE.sub(_degistir, html_metni)


def yayin_html(html_metni):
    """YAYIN kopyasi donusumu — TEK YER. Iki is yapar:
      (1) YORUMLARI SOYAR (HTML yorumu + <style> CSS yorumu + JS tur'lu <script>
          yorumlari; JSON-LD/ham-metin bloklari DOKUNULMAZ) — tools/yorum_soy.py.
      (2) site-ici <script src>'lerine ?v=<icerik-hash> ekler (onbellek kirici).
    Neden BURADA: uretilen HER yayin sayfasi (urun/, icerik/yasal, /marka, landing
    hub, ana sayfa) bu fonksiyondan gecer -> soyma tek noktadan uygulanir, yeni bir
    sayfa turu eklendiginde unutulamaz. KAYNAK dosyalar (index.html, sablonlar)
    DEGISMEZ; yorumlar depoda kalir, TARAYICIYA inmez.
    ⚠️ KAPSAM DISI (bilerek): elle yazilmis 4 statik yasal sayfa
    (hakkimizda/iletisim/sss/gizlilik) bu fonksiyondan GECMEZ — onlar commit'li
    kaynaktir ve tools/yasal-sayfa-drift-kapisi.py bayt-esitlik ister. Onlarin
    nobetcisi tools/yayin-ic-dil-kapisi.py'dir (ic-dil ekseni)."""
    return _surumle_scriptler(yorum_soy.html_soy(html_metni))


# Kardes moduller (marka_model_build / landing_hub_build) ctx'ten bu adla alir;
# anahtar adi degismesin diye ESKI AD ayni govdeye baglanir (ikinci kopya YOK).
surumle_scriptler = yayin_html


# ------------------------------------------------------------------ VARLIK (icerik-adresli same-origin dosya)
# NEDEN VAR (olculdu, 2 Agu): urun sayfasinin ~%86'si her sayfada BIREBIR ayni bayttı ve
# bunun en buyugu gomulu CSS + gomulu urun JS'iydi. 16.874 urunde brut tekrar ~0,87 GB;
# toplam yayin ~1,03 GB ve GitHub Pages siniri ~1 GB — sinira dayanmistik. Cozum: tekrar
# eden bloklari sayfaya GOMMEK yerine KENDI ALANIMIZDA bir dosyaya yazip referansla cagirmak.
# ⚠️ HARICI HOST / CDN / KUTUPHANE YOK — dosyalar /varlik/ altinda, ayni origin'de; disaridan
# hicbir sey cekilmez (CLAUDE.md'nin CDN yasagi kendi statik varligimiza uygulanmaz).
#
# 🔴 AD ICERIKTEN TURER (sha256 ilk 10) — bu depoda olculmus hata sinifi: ayni anahtarin
# UZERINE YAZMAK bayat dosyanin CDN'den servis edilmesine yol acti ([[r2-sessiz-uzerine-yazma]],
# [[gorsel-anahtar-cakismasi]]). Icerik degismezse ad AYNI kalir (gereksiz cache-miss yok);
# bir bayt degisirse ad DEGISIR (bayat CSS/JS servis edilmesi imkansiz).
VARLIK_DIR_ADI = "varlik"
VARLIK_DIR = os.path.join(ROOT, VARLIK_DIR_ADI)
VARLIK_URL_ONEK = "/" + VARLIK_DIR_ADI + "/"
VARLIK_HASH_UZUNLUK = 10
# icerik -> url onbellegi: ayni blok 16.874 kez uretilse de dosya BIR kez yazilir.
_VARLIK_ONBELLEK = {}


def varlik_hash(icerik):
    """Yayina inen BAYTLARDAN turetilen kisa ad. TEK KAYNAK: ad da, dosya da bu
    dizeden turer -> sayfadaki referans ile dosya adinin ayrisma yolu YOKTUR."""
    return hashlib.sha256(icerik.encode("utf-8")).hexdigest()[:VARLIK_HASH_UZUNLUK]


# 🔴 SOYMA ANIMSAMASI (12 Agu 2026, OLCULDU). `varlik_adres` her cagrida yorum soyuyordu;
# oysa girdi SAYFADAN BAGIMSIZ modul sabitleridir (PAGE_CSS kalani, ek CSS, JS bloklari) ve
# her urun sayfasinda AYNI metin yeniden soyuluyordu. cProfile (800 sayfa): toplam 9,98 s'nin
# 8,09 s'si (%81) `varlik_adres` -> `yorum_soy` lexer'inda; 21,8 milyon regex `match`.
# 26.000 sayfalik katalogda bu, her build'e ve bu yuzeyi olcen her kapiya ~2 dakikadir.
# Animsama, SAF bir fonksiyonun (metin -> soyulmus metin) sonucunu ICERIGE gore tutar:
# cikti bayt-bayt AYNIDIR (soyma girdiden baska hicbir seye bakmaz), yalniz ikinci kez
# hesaplanmaz. Ad ve dosya yine soyulmus GOVDEDEN turer -> tek kaynak bozulmaz.
_SOYMA_ONBELLEK = {}


def _varlik_govdesi(uzanti, icerik):
    """Yorumu soyulmus govde — ayni (uzanti, icerik) icin lexer BIR KEZ kosar."""
    anahtar = (uzanti, icerik)
    govde = _SOYMA_ONBELLEK.get(anahtar)
    if govde is not None:
        return govde
    if uzanti == "css":
        govde = yorum_soy.css_soy(icerik)
    elif uzanti == "js":
        govde = yorum_soy.js_soy(icerik)
    else:
        raise RuntimeError("varlik_adres: bilinmeyen uzanti %r" % uzanti)
    _SOYMA_ONBELLEK[anahtar] = govde
    return govde


def varlik_adres(onek, uzanti, icerik):
    """<icerik>'i /varlik/<onek>-<hash>.<uzanti> dosyasina yazar ve URL'ini doner.

    Yorumlar BURADA soyulur (yayin_html gomulu bloklarda ne yapiyorsa aynisi, AYNI
    lexer'dan) -> dosyanin bayti = tarayiciya inen bayt = kapinin olctugu bayt.
    FAIL-CLOSED: bos icerik, yazilamayan dizin ya da geri-okumada bayt farki => build DURUR.
    Sessizce ciplak (stil/JS'siz) sayfa URETILMEZ."""
    govde = _varlik_govdesi(uzanti, icerik)
    if not govde.strip():
        raise RuntimeError("varlik_adres: BOS varlik govdesi (%s.%s) — sayfa ciplak kalirdi"
                           % (onek, uzanti))
    ad = "%s-%s.%s" % (onek, varlik_hash(govde), uzanti)
    url = VARLIK_URL_ONEK + ad
    if _VARLIK_ONBELLEK.get(ad) == url and os.path.isfile(os.path.join(VARLIK_DIR, ad)):
        return url
    try:
        if not os.path.isdir(VARLIK_DIR):
            os.makedirs(VARLIK_DIR)
        hedef = os.path.join(VARLIK_DIR, ad)
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(govde)
        with open(hedef, encoding="utf-8") as f:
            geri = f.read()
    except OSError as e:
        raise RuntimeError("varlik_adres: %s yazilamadi (%s) — build DURDU" % (ad, e))
    if geri != govde:
        raise RuntimeError("varlik_adres: %s geri-okumada AYRISTI — build DURDU" % ad)
    _VARLIK_ONBELLEK[ad] = url
    return url


# Kritik cekirdek CSS ile harici dosya TEK KAYNAKTAN (PAGE_CSS) calisma aninda BOLUNUR.
# 🔴 IKINCI METIN BLOGU TUTULMAZ: elle yazilan bir "cekirdek" kopyasi ikiz tanimdir ve
# sessizce ayrisir ([[ikiz-tanim-sessiz-ayrisma]]) — kaynagi bozan bir mutant IKI ciktiyi
# da degistirmek ZORUNDA. Sinir isareti kaynaktan kaybolursa build DURUR (fail-closed).
# ISARET KENDI SATIRINDA ve girintisiz durur; iki parcadan da DISLANIR -> cekirdek+kalan,
# isaretin eklenmesinden ONCEKI CSS ile BAYT-ESITTIR (kabul testi eksen 2 bunu olcer).
KRITIK_CSS_SINIRI = "/* === KRITIK CEKIRDEK SONU === */\n"


def css_bol(css):
    """(satir_ici_cekirdek, harici_kalan) — ikisi de KAYNAGIN DILIMI, kopyasi DEGIL."""
    i = css.find(KRITIK_CSS_SINIRI)
    if i < 0:
        raise RuntimeError("PAGE_CSS'te kritik cekirdek siniri YOK -> bolme yapilamaz "
                           "(fail-closed; ikiz cekirdek yazmak YASAK)")
    return css[:i], css[i + len(KRITIK_CSS_SINIRI):]


def stil_bloklari(ek_css=""):
    """Sayfanin <head>'ine giren stil yuzeyi: kritik cekirdek SATIR-ICI + gerisi HARICI.

    Cekirdek ilk boyamayi (renk degiskenleri, reset, body, header) tasir; geri kalan
    PAGE_CSS icerik-adresli /varlik/sayfa-<hash>.css dosyasindan gelir. `ek_css` (marka /
    landing hub gibi sayfa turune ozel kurallar) AYRI bir varliga yazilir ki taban dosya
    TUM sayfa turlerinde AYNI kalsin — ikinci kopya uretilmez (spec 2. bolum)."""
    cekirdek, kalan = css_bol(PAGE_CSS)
    parcalar = ["<style>" + cekirdek + "</style>",
                '<link rel="stylesheet" href="%s">' % varlik_adres("sayfa", "css", kalan)]
    if ek_css:
        parcalar.append('<link rel="stylesheet" href="%s">' % varlik_adres("ek", "css", ek_css))
    return "\n".join(parcalar)


def _marka_cip_enjekte(html_metni, chip_links, slug_map):
    """Anasayfa marka çiplerini SSR yapar: JS-siz curl'de görünsün diye çip <a> linklerini
    #brandChips'e basar + renderBrands'in okuduğu window.PRUVO_MARKA_SLUG haritasını <head>'e
    inline gömer (marka_model_build çip↔sayfa slug'ı ile TEK KAYNAK). KAYNAK index.html
    DEGISMEZ; yalnız YAYIN kopyası (index.built.html) zenginleşir. chip_links boşsa no-op."""
    if not chip_links:
        return html_metni
    harita = json.dumps(slug_map, ensure_ascii=False, separators=(",", ":"))
    script = ('<script>window.PRUVO_MARKA_SLUG=' + harita + ';</script>\n</head>')
    if "</head>" in html_metni:
        html_metni = html_metni.replace("</head>", script, 1)
    bos = '<div class="brand-chips" id="brandChips"></div>'
    dolu = '<div class="brand-chips" id="brandChips">' + chip_links + '</div>'
    if bos in html_metni:
        html_metni = html_metni.replace(bos, dolu, 1)
    return html_metni


def yayin_index(marka_sonuc=None, products=None):
    """Yayinlanan ana sayfa: KAYNAK index.html'in script src'leri surumlenmis kopyasi.
    Kaynak dosya DEGISTIRILMEZ (curumesin diye); cikti index.built.html'e yazilir, deploy
    onu _site/index.html olarak kopyalar. taban-fiyatlar.js bu asamada uretilmis olmali.
    marka_sonuc verilirse anasayfa marka çipleri SSR link'e çevrilir (discovery kök-fix).
    products verilirse CIP INDEKSI (marka/grup/model capraz daralma tablosu) <head>'e
    gomulur — tools/cip-indeks.py; KAYNAK index.html'e YAZILMAZ cunku indeks urunler.json'dan
    turer ve her urun partisi kaynak dosyayi bayatlatirdi. FAIL-CLOSED: uretim/gomme
    patlarsa build DURUR (sessizce indekssiz yayinlanip capraz daralma kaybolmaz)."""
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        metin = f.read()
    if marka_sonuc:
        metin = _marka_cip_enjekte(metin, marka_sonuc.get("chip_links", ""),
                                   marka_sonuc.get("slug_map", {}))
    if products is not None:
        metin = cip_indeks.enjekte(metin, cip_indeks.indeks_uret(products, metin))
    return surumle_scriptler(attribution_ekle(metin))


def _js_sabiti(kaynak, ad):
    m = re.search(r"var\s+" + re.escape(ad) + r"\s*=\s*(\{.*?\}|\[.*?\]);", kaynak, re.S)
    if not m:
        raise SystemExit("secenekler.js'te %s bulunamadi — secici HTML'i uretilemez "
                         "(tek kaynak bozulmus)." % ad)
    return json.loads(m.group(1))


def _js_sayisi(kaynak, ad):
    m = re.search(r"var\s+" + re.escape(ad) + r"\s*=\s*(\d+);", kaynak)
    if not m:
        raise SystemExit("secenekler.js'te %s bulunamadi." % ad)
    return int(m.group(1))


with open(SECENEKLER_JS, encoding="utf-8") as _f:
    _SEC_JS = _f.read()
FILAMENT_FARK = _js_sabiti(_SEC_JS, "FILAMENT_FARK")
# 🔴 TÜREYEN KATSAYI (14 Ağu): ABS = ASA. Sayı BURAYA ELLE YAZILMAZ — istemciyle AYNI
# haritadan (secenekler.js FILAMENT_TUREME) AYNI türetme uygulanır. Elle yazsaydık ASA
# değiştiği gün Python tarafı sessizce eski sayıda kalır, sayfada ilan edilen tutar ile
# Worker'ın tahsil ettiği tutar ayrışırdı ([[ikiz-tanim-sessiz-ayrisma]]).
FILAMENT_TUREME = _js_sabiti(_SEC_JS, "FILAMENT_TUREME")
for _t_ad, _t_kaynak in FILAMENT_TUREME.items():
    if _t_kaynak not in FILAMENT_FARK:
        raise SystemExit("FILAMENT_TUREME %r -> %r: kaynak malzeme FILAMENT_FARK'ta YOK "
                         "(tek kaynak bozulmus)." % (_t_ad, _t_kaynak))
    FILAMENT_FARK[_t_ad] = FILAMENT_FARK[_t_kaynak]
FILAMENT_SIRA = _js_sabiti(_SEC_JS, "FILAMENT_SIRA")
# 🔴 MALZEME x KATEGORI KAPISI — kanonik tablo secenekler.js'te; burada İKİNCİ KOPYA
# TUTULMAZ, aynı satır okunur. Seçim listesi (çip + dropdown) bu tabloyu uygular; Worker
# aynı tabloyu ZORLAR (fail-closed) — ikisi ayrışırsa müşteri göremediği bir malzemeyi
# sipariş edebilir ya da görüp sipariş edemez.
FILAMENT_KATEGORI_HARIC = _js_sabiti(_SEC_JS, "FILAMENT_KATEGORI_HARIC")
_PARAMETRIK_KATEGORI_M = re.search(r'var\s+PARAMETRIK_KATEGORI\s*=\s*"([^"]+)";', _SEC_JS)
if not _PARAMETRIK_KATEGORI_M:
    raise SystemExit("secenekler.js'te PARAMETRIK_KATEGORI bulunamadi — kisitli malzeme "
                     "kategori evreni turetilemez (tek kaynak bozulmus).")
PARAMETRIK_KATEGORI = _PARAMETRIK_KATEGORI_M.group(1)
# FAIL-CLOSED DRIFT NÖBETİ: secenekler.js'teki seri adı bu üretecin gizli kategori
# defteriyle örtüşmeli. Ayrışırsa (ad değişir/silinir) ölçüye özel seride ABS sessizce
# "tanınmayan kategori" sayılıp listeden düşerdi -> build DÜŞER, insan bakar.
if PARAMETRIK_KATEGORI not in NAV_GIZLI:
    raise SystemExit("secenekler.js PARAMETRIK_KATEGORI (%r) NAV_GIZLI listesinde YOK "
                     "(%s) — kisitli malzeme kategori evreni ayrismis."
                     % (PARAMETRIK_KATEGORI, ", ".join(NAV_GIZLI)))
_HARIC_EVREN = set(CATEGORIES) | set(NAV_GIZLI)
for _h_malzeme, _h_liste in FILAMENT_KATEGORI_HARIC.items():
    _bilinmeyen = [k for k in _h_liste if k not in _HARIC_EVREN]
    if _bilinmeyen:
        raise SystemExit("FILAMENT_KATEGORI_HARIC[%r] taninmayan kategori iceriyor: %s "
                         "(kategori defteri ayrismis — harıc satiri OLU olurdu)."
                         % (_h_malzeme, ", ".join(_bilinmeyen)))


def malzeme_kategori_uygun_mu(malzeme, kategori):
    """Bu malzeme BU kategoride sunulabilir mi? (istemci ikizi: malzemeKategoriUygunMu)

    Kısıtsız malzemede DAİMA True (bugünkü davranış birebir). Kısıtlı malzemede kategori
    TANINMALIDIR — boş/None/bilinmeyen ad FAIL-CLOSED False'tur: "bilinmiyorsa göster"
    yönü, kategorisi çözülemeyen bir üründe sessizce satış açardı."""
    haric = FILAMENT_KATEGORI_HARIC.get(malzeme)
    if haric is None:
        return True
    if not isinstance(kategori, str):
        return False
    if kategori not in FONKSIYONEL_KATEGORILER and kategori != PARAMETRIK_KATEGORI:
        return False
    return kategori not in haric


def _kategori_katsayi_adlari(kategori):
    """O kategoride ON-SECIME aday olabilecek malzeme adlari (katsayi tablosu x sizgec)."""
    return {m for m in FILAMENT_FARK if malzeme_kategori_uygun_mu(m, kategori)}
RENK_SECENEKLERI = _js_sabiti(_SEC_JS, "RENK_SECENEKLERI")
RENK_DIGER_YUZDE = _js_sayisi(_SEC_JS, "RENK_DIGER_YUZDE")
ADET_EN_AZ = _js_sayisi(_SEC_JS, "ADET_EN_AZ")
ADET_EN_COK = _js_sayisi(_SEC_JS, "ADET_EN_COK")
# SINIF BEYANI cümleleri TEK KAYNAK secenekler.js BEYAN (aynı sözlüğü sipariş e-postası
# ve ödeme ekranı da okur). İKİNCİ KOPYA YAZILMAZ: ikiz tanım sessizce ayrışır, burada
# ayrışma FAIL-CLOSED patlar (_js_sabiti bulamazsa/JSON bozuksa build DÜŞER).
BEYAN = _js_sabiti(_SEC_JS, "BEYAN")


def _js_bos_satir_varsayilani(kaynak, alan):
    """secenekler.js `bosSatir()` icindeki VARSAYILAN secim degeri (malzeme/renk).

    🔴 NEDEN BURADAN OKUNUR (ikinci liste YAZILMAZ): sayfada ONDEN SECILI gelen malzeme/renk,
    sunucunun (shop worker -> SECENEK.satirOzeti) ve sepetin varsayilan satiriyla AYNI deger
    OLMAK ZORUNDADIR. Elle yazilan bir "PLA" sabiti ikiz tanimdir: bosSatir degisince sayfa
    sessizce baska bir malzemeyi onden secer ve tahsil edilen tutar musterinin gordugunden
    AYRISIR ([[ikiz-tanim-sessiz-ayrisma]]). Buradan turetilince on-secim bir ARAYUZ
    varsayilanidir, fiyat mantigina DOKUNMAZ: satira yazilan deger zaten bosSatir'in yazdigi
    degerin ta kendisidir -> kurus farki YAPISAL OLARAK 0.
    FAIL-CLOSED: fonksiyon ya da alan bulunamazsa build DUSER (sessizce secimsiz sayfa
    uretmek, bugunku sessiz sepet arizasini geri getirirdi)."""
    m = re.search(r"function\s+bosSatir\s*\([^)]*\)\s*\{\s*return\s*\{(.*?)\}\s*;", kaynak, re.S)
    if not m:
        raise SystemExit("secenekler.js'te bosSatir() bulunamadi — on-secim varsayilani "
                         "turetilemez (tek kaynak bozulmus).")
    g = re.search(re.escape(alan) + r'\s*:\s*"([^"]*)"', m.group(1))
    if not g or not g.group(1):
        raise SystemExit("secenekler.js bosSatir() icinde %r alani bulunamadi/bos." % alan)
    return g.group(1)


# Sayfada ONDEN SECILI gelen malzeme/renk — TEK KAYNAK secenekler.js bosSatir().
VARSAYILAN_MALZEME = _js_bos_satir_varsayilani(_SEC_JS, "malzeme")
VARSAYILAN_RENK = _js_bos_satir_varsayilani(_SEC_JS, "renk")
if VARSAYILAN_MALZEME not in FILAMENT_SIRA:
    raise SystemExit("bosSatir varsayilan malzemesi (%r) sitede satilan FILAMENT_SIRA "
                     "listesinde YOK — onden secili cip basilamaz." % VARSAYILAN_MALZEME)
if VARSAYILAN_RENK not in RENK_SECENEKLERI or VARSAYILAN_RENK == "Diğer":
    raise SystemExit("bosSatir varsayilan rengi (%r) standart renk listesinde YOK ya da "
                     "serbest-metin gerektiren 'Diğer' — onden secilemez." % VARSAYILAN_RENK)
# On-secimin FIYATA DOKUNMADIGININ yapisal kaniti: varsayilan malzemenin farki %0 ve
# varsayilan renk "Diğer" degil -> hesaplaFiyatKurus carpanlari 1,00. Bozulursa build DUSER.
if FILAMENT_FARK.get(VARSAYILAN_MALZEME, 0) != 0:
    raise SystemExit("bosSatir varsayilan malzemesi (%r) fiyat farki tasiyor (+%%%s) — onden "
                     "secilseydi sayfada ilan edilen liste fiyatinin USTUNDE bir tutar sepete "
                     "yazilirdi." % (VARSAYILAN_MALZEME, FILAMENT_FARK.get(VARSAYILAN_MALZEME)))


def _js_bayragi(kaynak, ad):
    m = re.search(r"var\s+" + re.escape(ad) + r"\s*=\s*(true|false);", kaynak)
    if not m:
        raise SystemExit("secenekler.js'te %s bulunamadi." % ad)
    return m.group(1) == "true"


# ---------------------------------------------------------------------------
# ON-SECILI MALZEME + ILAN EDILEN TUTAR — TEK TURETME NOKTASI
#
# 🔴 SESSIZ ZAM SINIFI: PETG +%30, ASA +%60. Onden secili malzeme ile sayfada ILAN
# EDILEN tutar ayri ayri hesaplanirsa, hic secim yapmayan musteri gordugu tutarin
# %30-60 ustunu sepete yazar ve fark HICBIR YERDE gorunmez (yapilandirilmis veri,
# kart yuzeyi ve alisveris akisi ayni sayiyi beyan etmeye devam eder). Bu yuzden
# ilan_kurus(), on_secim_malzeme()'yi CAGIRIR: cip hangi malzemeyi isaretliyorsa
# tutar da ondan turer, ikisi ayrisamaz.
#
# Bayrak KAPALIYKEN on-secim guvenli varsayilana (bosSatir malzemesi, farki %0)
# duser -> uretilen sayfa bugunkuyle BAYT-ESIT kalir.
#
# 🔴 IKI YUZEY IKI ANAHTAR (isletme karari 11 Agu): URUN SAYFASI kolu ONERI_ONSECIM_ACIK,
# LISTE/KART kolu ONERI_VITRIN_ACIK. Kart yuzeyi istemcide cizilir (index.html
# ilanFiyatMetni -> vitrinBirimKurus); burada okunmasinin sebebi, kart tutari ile D1'e
# yazilan liste tutarinin AYRISMADIGINI olcen kapinin (tools/d1-fiyat-parite-kapisi.py)
# bayragi TEK KAYNAKTAN almasidir. Ikinci kopya tutulmaz.
ONERI_ONSECIM_ACIK = _js_bayragi(_SEC_JS, "ONERI_ONSECIM_ACIK")
ONERI_VITRIN_ACIK = _js_bayragi(_SEC_JS, "ONERI_VITRIN_ACIK")

# Hazir ticari mal isareti — TEK KAYNAK secenekler.js (istemci/sunucu ayni dizeyi kullanir;
# karsilastirma TAM dize esitligidir, kirpma/kucultme YOK).
_TUR_FIZIKSEL_M = re.search(r'var\s+TUR_FIZIKSEL\s*=\s*"([^"]+)";', _SEC_JS)
if not _TUR_FIZIKSEL_M:
    raise SystemExit("secenekler.js'te TUR_FIZIKSEL bulunamadi — hazir ticari mal ayrimi "
                     "turetilemez (tek kaynak bozulmus).")
TUR_FIZIKSEL = _TUR_FIZIKSEL_M.group(1)


def fiziksel_mi(p):
    return bool(p) and p.get("tur") == TUR_FIZIKSEL


def on_secim_tani(p, acik=None):
    """(tani, malzeme) — ON-SECIMIN sonucu ve hangi koldan geldigi.

    KAPSAM — BEYAN EDILEN SINIR (sessiz yesil yasak): kural YALNIZ sabit fiyatli katalog
    kolunda uygulanir. Olcuye-ozel (parametrik) ve yapilandiricili urunlerde gorunen tutar
    tabandan CANLI hesaplanir ve kart yuzeyi "X TL'den baslayan" tabani ayri bir haritadan
    okur; oralarda on-secimi degistirmek ilan edilen tabani BU degisiklikle olculmeyen bir
    yoldan kaydirirdi -> guvenli varsayilan korunur. Hazir ticari malda uretim malzemesi
    karsiliksizdir (carpan zaten 1,00) -> guvenli varsayilan.

    🔴 TANINMAYAN KOLU (fail-loud): `tavsiyeFilament` DOLU ama adlarinin hicbiri sitede
    satilan malzeme degilse sonuc yine guvenli varsayilandir — ama jeton TANINMAYAN'dir,
    yani "onerisi olmayan urun"den AYIRT EDILEBILIR. Sessizce PLA'ya dusen veri kusuru
    boylece SAYILABILIR (tools/d1-fiyat-parite-kapisi.py eksen E6)."""
    if acik is None:
        acik = ONERI_ONSECIM_ACIK
    # SIRA ISTEMCIYLE BIREBIR (secenekler.js _onSecimCekirdek): once ANAHTAR, sonra KAPSAM.
    # Ters sirada, kural kapaliyken ayni urun icin iki dil FARKLI jeton uretirdi.
    if not acik:
        return (filament_ortak.TANI_KAPALI, VARSAYILAN_MALZEME)
    if fiziksel_mi(p) or p.get("parametrik") or p.get("konfigur"):
        return (filament_ortak.TANI_KAPSAM_DISI, VARSAYILAN_MALZEME)
    # 🔴 KATEGORI SUZGECI (14 Agu): on-secime aday olan adlar, o kategoride FIILEN
    # SUNULAN adlardir. Harıc bir malzeme on-secilseydi cipi hic basilmadigi halde
    # sepete yazilir ve musteri gormedigi bir katsayiyla fiyatlanirdi. Istemci ikizi:
    # secenekler.js _onSecimCekirdek icindeki malzemeKategoriUygunMu kosulu.
    return filament_ortak.on_secim_tani(p.get("kategori"), p.get("tavsiyeFilament"),
                                        _kategori_katsayi_adlari(p.get("kategori")),
                                        VARSAYILAN_MALZEME, acik=acik)


def on_secim_malzeme(p):
    """Urun sayfasinda ONDEN SECILI gelecek malzeme (istemci karsiligi: onSecimMalzeme)."""
    return on_secim_tani(p)[1]


def vitrin_malzeme(p):
    """LISTE/KART yuzeyinin malzemesi (istemci karsiligi: vitrinMalzeme). KENDI anahtarina
    baglidir: urun sayfasi kolu acilinca kart KAYMAZ."""
    return on_secim_tani(p, acik=ONERI_VITRIN_ACIK)[1]


def _birim_kurus(p, malzeme):
    """🔴 TEK TURETME NOKTASI (uretec tarafi): bir malzeme secildiginde olusan BIRIM tutar.

    Kural istemcideki hesaplaFiyatKurus ile BIREBIR: taban x (100+yuzde) x renkCarpan
    / 10000. Onden secili renk "Diğer" DEGIL (yukaridaki fail-closed kontrol) ve boy
    farki 0 -> renkCarpan 100. Fiyat sayisi cikarilamiyorsa None (fiyatsiz urun).

    Urun sayfasi tutari, kart tutari ve cipte GORUNEN tutar UCU DE buradan cikar; ikinci
    bir formul yazilmaz (yazilsaydi bir yuzey digerlerinden sessizce ayrisirdi)."""
    temel = feed_price(p.get("fiyat") if "fiyat" in p else "")
    if not temel:
        return None
    yuzde = 0 if fiziksel_mi(p) else FILAMENT_FARK.get(malzeme, 0)
    return int(temel) * (100 + yuzde)


def vitrin_kurus(p):
    """LISTE/KART yuzeyinin BIRIM tutari (tamsayi kurus) — istemci vitrinBirimKurus ikizi."""
    return _birim_kurus(p, vitrin_malzeme(p))


def ilan_kurus(p):
    """ILAN EDILEN birim tutar (tamsayi kurus) — on-secimli malzemeye gore."""
    return _birim_kurus(p, on_secim_malzeme(p))


def cip_kurus(p, malzeme):
    """CIPTE GORUNEN tutar (tamsayi kurus) ya da None.

    🔴 NEDEN VAR (azaltici, 11 Agu — Okan'in karari): besleme ve yapilandirilmis veri
    BASLANGIC tabanini beyan ederken urun sayfasi ONERILEN malzemenin tutarini vurgular.
    Iki sayi arasindaki bagi kullanicinin ve dis yuzeyin GOREBILMESI icin, her malzeme
    cipi KENDI tutarini tasir: taban secenegin (PLA) tutari sayfada hem GORUNUR hem
    makineyle okunabilir (data-kurus) kalir.

    None: olcuye ozel / yapilandiricili urun (tutar tabandan CANLI hesaplanir, sabit sayi
    basmak YANILTICI olurdu) ya da sayisal fiyati olmayan urun."""
    if p.get("parametrik") or p.get("konfigur"):
        return None
    return _birim_kurus(p, malzeme)


def ilan_tl_metni(kurus):
    """Kurusu yapilandirilmis veri/besleme icin sayisal TL dizesine cevirir."""
    if kurus is None:
        return None
    return ("%.2f" % (kurus / 100.0)).rstrip("0").rstrip(".")


# ---------------------------------------------------------------------------
# ILAN TUTARI ARALIGI — KART METNI + YAPILANDIRILMIS VERI (isletme karari 12 Agu, Okan)
#
# 🔴 KARAR: kart BASLANGIC tabanini yazar, urun sayfasi ONERILEN malzemenin tutarini.
# Iki sayi BILEREK farkli. Musteri kartta gordugu tutarin bir TABAN oldugunu KARTTAN
# anlamali -> kart metni duz "X TL" degil "X TL'den baslayan"dir; yapilandirilmis veri
# de tek fiyat yerine AggregateOffer low/high ARALIGI beyan eder.
#
# 🔴 EK IKINCI KEZ YAZILMAZ: dize TEK KAYNAK secenekler.js BASLAYAN_SONEK'ten okunur
# (istemci kart yuzeyi ve marka/model karti da ayni ekten turer). Ayrisma sessizdir
# ([[ikiz-tanim-sessiz-ayrisma]]); anahtar bulunamazsa build FAIL-CLOSED duser.
_BASLAYAN_M = re.search(r'var\s+BASLAYAN_SONEK\s*=\s*"([^"]+)";', _SEC_JS)
if not _BASLAYAN_M:
    raise SystemExit("secenekler.js'te BASLAYAN_SONEK bulunamadi — kart metninin eki "
                     "turetilemez (tek kaynak bozulmus).")
BASLAYAN_SONEK = _BASLAYAN_M.group(1)
# HTML gomulusu: `esc()` kesme isaretini `&#x27;` yazar, sayfadaki tarihsel gosterim ise
# `&#39;`dur. Ikisi ayni karakteri kodlar ama BAYT farki uretirdi (varlik kapisi bayt
# olcer) -> ek, sayfanin bugunku kodlamasiyla yazilir. Ikinci DIZE degil, ayni tek
# kaynagin kodlanmis hali.
BASLAYAN_SONEK_HTML = html.escape(BASLAYAN_SONEK, quote=False).replace("'", "&#39;")


def en_pahali_malzeme_farki():
    """Sitede satilan malzemelerin EN YUKSEK farki (yuzde). Istemci ikizi:
    secenekler.js enPahaliMalzemeFarki."""
    return max([FILAMENT_FARK.get(m, 0) for m in FILAMENT_SIRA] or [0])


def malzeme_aralikli_mi(p):
    """Urunun ILAN TUTARI malzeme secimiyle YUKSELEBILIR mi?

    KAPSAM = MALZEME SECICISI BASILAN KOL (render_product'taki `fonksiyonel and not
    parametrik` dali): olcuye ozel (parametrik) ve yapilandiricili urunde tutar tabandan
    CANLI hesaplanir, hazir ticari malda uretim malzemesi karsiliksizdir (carpan 1,00).
    Oralarda "baslayan" demek ve aralik beyan etmek YANILTICI olurdu.

    🔴 IKIZ TANIM: istemci tarafi secenekler.js malzemeAralikliMi. Iki dilin TUM KATALOG
    uzerinde ayni cevabi verdigini tools/ilan-tutari-kapisi.py eksen 1 fail-closed olcer."""
    if fiziksel_mi(p) or p.get("parametrik") or p.get("konfigur"):
        return False
    if p.get("kategori") not in FONKSIYONEL_KATEGORILER:
        return False
    if feed_price(p.get("fiyat") if "fiyat" in p else "") is None:
        return False
    return en_pahali_malzeme_farki() > 0


def en_yuksek_kurus(p):
    """Urunun EN PAHALI malzemeyle olusan BIRIM tutari (kurus) ya da None.

    Kart tutari (vitrin_kurus), urun sayfasi tutari (ilan_kurus) ve bu TAVAN ayni
    turetme noktasindan (_birim_kurus) cikar; ikinci formul yazilmaz."""
    if not malzeme_aralikli_mi(p):
        return vitrin_kurus(p)
    adaylar = [k for k in (_birim_kurus(p, m) for m in FILAMENT_SIRA) if k is not None]
    return max(adaylar) if adaylar else None


def kart_tutar_metni(p, tutar_metni):
    """🔴 KARTIN YAZDIGI TUTAR METNI — TEK KANONIK NOKTA (istemci ikizi
    secenekler.js kartTutarMetni). `tutar_metni` kartin kendi tutar turetmesinden gelir;
    burada YALNIZ "baslangic mi" karari ve ek tutulur."""
    if not tutar_metni:
        return tutar_metni
    return (tutar_metni + BASLAYAN_SONEK) if malzeme_aralikli_mi(p) else tutar_metni


# ---------------------------------------------------------------------------
# SATIS KAPISI OKUYUCUSU — "bu aile satisa ACIK mi?" sorusunun TEK KAYNAGI
# secenekler.js'teki HACIM_DOGRULANMIS_AILELER'dir (ayni sozlugu istemci fiyat
# hesabi ve Worker kolu da okur). BURAYA IKINCI LISTE YAZILMAZ: ikiz tanim
# sessizce ayrisir -> [[ikiz-tanim-sessiz-ayrisma]].
#
# NEDEN _js_sabiti YETMEZ: o fonksiyon json.loads kullanir; HACIM_DOGRULANMIS_AILELER
# blogu YORUMLU ve TIRNAKSIZ anahtarli JS'tir (JSON DEGIL) -> json.loads patlar.
# Bu yuzden ayri, KATI bir anahtar okuyucu var.
#
# 🔴 FAIL-CLOSED — IKI YONLU: blok bulunamaz/ayristirilamazsa SystemExit ile build
# DUSER. "Sessizce hepsini ACIK say" (yanlis fiyat/InStock beyani) DA, "sessizce
# hepsini KAPALI say" (18 acik ailenin fiyati kaybolur) DA ayri ayri yanlistir;
# ikisi de olmaz, build durur ve insan bakar.
def _js_yorum_sil(metin):
    """JS kaynagindan // ve /* */ yorumlarini siler; dize icindekilere DOKUNMAZ.
    Kapanmamis blok yorumunda taramayi orada KESER (o noktadan sonrasi zaten
    ilgilenilen bloktan sonradir; blok icindeyse kume ayrastirmasi patlar)."""
    cikti = []
    i, n = 0, len(metin)
    tirnak = None
    while i < n:
        c = metin[i]
        if tirnak is not None:
            cikti.append(c)
            if c == "\\" and i + 1 < n:
                cikti.append(metin[i + 1])
                i += 2
                continue
            if c == tirnak:
                tirnak = None
            i += 1
            continue
        if c == '"' or c == "'":
            tirnak = c
            cikti.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and metin[i + 1] == "/":
            while i < n and metin[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and metin[i + 1] == "*":
            son = metin.find("*/", i + 2)
            if son < 0:
                break
            cikti.append(" ")
            i = son + 2
            continue
        cikti.append(c)
        i += 1
    return "".join(cikti)


# Kabul edilen tek girdi bicimi: `ident: sayi` (olculen hacim sapmasi yuzdesi).
_AILE_GIRDI_RE = re.compile(r"^([A-Za-z_$][A-Za-z0-9_$]*)\s*:\s*-?\d+(?:\.\d+)?$")


def _js_anahtar_kumesi(kaynak_temiz, ad):
    """Yorumu SILINMIS JS kaynagindan `var <ad> = { k: sayi, ... };` blogunun
    ANAHTAR kumesini dondurur. Tanimadigi her sey SystemExit."""
    m = re.search(r"var\s+" + re.escape(ad) + r"\s*=\s*\{", kaynak_temiz)
    if not m:
        raise SystemExit("secenekler.js'te %s blogu bulunamadi — satis kapisi "
                         "okunamadi (fail-closed, build durdu)." % ad)
    bas = m.end() - 1
    derinlik = 0
    son = -1
    for j in range(bas, len(kaynak_temiz)):
        ch = kaynak_temiz[j]
        if ch == "{":
            derinlik += 1
        elif ch == "}":
            derinlik -= 1
            if derinlik == 0:
                son = j
                break
    if son < 0:
        raise SystemExit("secenekler.js'te %s blogu kapanmiyor — satis kapisi "
                         "okunamadi (fail-closed, build durdu)." % ad)
    govde = kaynak_temiz[bas + 1:son]
    anahtarlar = []
    for parca in govde.split(","):
        p = parca.strip()
        if not p:
            continue
        g = _AILE_GIRDI_RE.match(p)
        if not g:
            raise SystemExit("secenekler.js %s icinde cozumlenemeyen girdi: %r "
                             "(fail-closed, build durdu)." % (ad, p))
        anahtarlar.append(g.group(1))
    if not anahtarlar:
        raise SystemExit("secenekler.js %s BOS okundu — 'hepsi kapali' sessizce "
                         "varsayilmaz (fail-closed, build durdu)." % ad)
    if len(set(anahtarlar)) != len(anahtarlar):
        raise SystemExit("secenekler.js %s icinde yinelenen anahtar var "
                         "(fail-closed, build durdu)." % ad)
    return set(anahtarlar)


# Fiyat URETILEMEDIGINDE gosterilen cumle — TEK KAYNAK secenekler.js'teki
# `kurus == null` dalidir (istemci JS'i de AYNI cumleyi basar). Buraya elle
# ikinci kopya yazilmaz; ayrisirsa JS oncesi ve JS sonrasi metin celisir.
_FIYATSIZ_METIN_RE = re.compile(r"\(\s*kurus\s*==\s*null\s*\)\s*\?\s*\"([^\"]+)\"")


def _js_fiyatsiz_metni(kaynak_temiz):
    m = _FIYATSIZ_METIN_RE.search(kaynak_temiz)
    if not m or not m.group(1).strip():
        raise SystemExit("secenekler.js'te fiyatsiz (kurus == null) metni bulunamadi "
                         "— JS oncesi metin tek kaynaktan turetilemiyor "
                         "(fail-closed, build durdu).")
    return m.group(1).strip()


_SEC_JS_TEMIZ = _js_yorum_sil(_SEC_JS)
# Satisa ACIK (hacmi dogrulanmis) aile anahtarlari; sema.hacimFormulu ile eslesir.
HACIM_DOGRULANMIS_AILELER = _js_anahtar_kumesi(_SEC_JS_TEMIZ, "HACIM_DOGRULANMIS_AILELER")
FIYATSIZ_METIN = _js_fiyatsiz_metni(_SEC_JS_TEMIZ)


def aile_satis_kapali_mi(sema):
    """"Bu urun BUGUN satilabilir mi?" sorusunun TEK karar noktasi.

    True  = aile hacim dogrulamasindan GECMEMIS -> secenekler.js parametrikFiyatKurus
            null dondurur, Worker sepeti 400 `hacim-dogrulanmamis` ile reddeder;
            yani hicbir YUZEYDE (urun sayfasi, JSON-LD, ana sayfa karti, SSR kart)
            sayisal tutar BEYAN EDILMEZ.
    False = bugunku davranis AYNEN surer.

    Semasiz/parametrik olmayan urun (sema None) bu daldan GECMEZ -> kapali DEGIL,
    15.9xx baskı urununde regresyon 0.
    FAIL-CLOSED: sema VAR ama hacimFormulu yok/dizge degilse aile KAPALI sayilir
    (taninmayan aile icin fiyat beyan etmek, beyan etmemekten kotudur).

    🔴 IKINCI KOPYA YAZILMAZ: sayfa yuzeyi (render_product), kart haritasi
    (uret_taban_fiyatlar) ve SSR kart (marka_model_build) AYNI bu fonksiyonu
    cagirir -> ikiz tanim sessizce ayrisamaz ([[ikiz-tanim-sessiz-ayrisma]]).
    """
    if not sema:
        return False
    aile = sema.get("hacimFormulu")
    return not (isinstance(aile, str) and aile in HACIM_DOGRULANMIS_AILELER)


# Sari seri 3D onizleme (tools/paket-onizleme-3d.md) — bayrak + aile listesi TEK KAYNAK
# secenekler.js (onizleme Worker'i da AYNI listeyi okur). Bayrak kapaliyken sayfalara
# hicbir onizleme ogesi basilmaz = canlida sifir gorunur fark.
ONIZLEME_3D_ACIK = _js_bayragi(_SEC_JS, "ONIZLEME_3D_ACIK")
ONIZLEME_AILELER = set(_js_sabiti(_SEC_JS, "ONIZLEME_AILELER"))

# "Onizle (3D)" akisi: parametreleri konfiguratorden alir, /api/onizleme/olustur'a
# gonderir, donen gzip'li binary STL'i acip /jenerator/viewer.js ile cizer.
# .format() SONRASI yerlestirilir (placeholder degeri yeniden islenmez) -> tek suslu
# parantezler guvenlidir. Fiyat/sepet koduna dokunmaz; salt gorsel katman.
#
# 2-RENK (COK GOVDELI) YOL — 29 Tem 2026: musteri "Yazı rengi (2. renk)" secince
# onizleme IKI govde ceker (parca="govde" + parca="yazi", ayni parametrelerle) ve
# ikisini AYRI renklerde cizer. Uretim de AYNI ucu ayni parca adlariyla kullanir
# (/ic-derle) -> ekranda gorulen ayrim, basilacak filaman ayriminin ta kendisi.
# Tek renkte (ya da renk temsil edilemiyorsa) BUGUNKU tek-govde yolu aynen kosar.
ONIZLEME_JS = """
(function(){
  var btn=document.getElementById("onizleBtn"); if(!btn){ return; }
  var kutu=document.getElementById("onizlemeKutu");
  var durum=document.getElementById("onizlemeDurum");
  var tuval=document.getElementById("onizlemeTuval");
  var mesgul=false;
  var gosterge=null;   /* PRUVO_VIEWER.goster kolu — renk secimi degisince yeniden boyar */
  var ekrandaIkiGovde=false;   /* su an ekranda ayri yazi govdesi var mi */
  var sonYaziRenk=null;        /* son cizimde kullanilan yazi rengi ADI */
  function de(t){ if(durum){ durum.textContent=t||""; } }
  /* SECILI RENK ADI — sayfa iki duzende de calisir: kart-secim urununde renk
     BUTONLARI (#renkButonlar .renk-btn.secili), klasik duzende #renkSec.
     Hicbiri secili degilse "" -> aile varsayilan rengi kullanilir. */
  function seciliRenkAdi(){
    var b=document.querySelector("#renkButonlar .renk-btn.secili");
    if(b){ return b.getAttribute("data-renk")||""; }
    var s=document.getElementById("renkSec");
    return s?s.value:"";
  }
  function onizlemeRenk(){
    return (window.PRUVO_SECENEK&&PRUVO_SECENEK.onizlemeRengi)
      ? PRUVO_SECENEK.onizlemeRengi(URUN.id, seciliRenkAdi()) : null;
  }
  /* 2-renk karari TEK KAYNAK /secenekler.js onizlemeIkiRenk(): aile cok govdeli mi,
     yazi rengi govdeden farkli mi, iki renk de temsil edilebiliyor mu. */
  function ikiRenkDurumu(yaziRenkAdi){
    return (window.PRUVO_SECENEK&&PRUVO_SECENEK.onizlemeIkiRenk)
      ? PRUVO_SECENEK.onizlemeIkiRenk(URUN.id, seciliRenkAdi(), yaziRenkAdi) : null;
  }
  /* Renk secimi degisince modeli YENIDEN INDIRMEDEN boya (derleyici kotasi
     yenmez); onizleme henuz acilmadiysa hicbir sey yapma.
     EKRANDA IKI GOVDE varsa iki rengi birden tazeler; iki renk esitlenirse
     (ya da temsil edilemez hale gelirse) iki govde de govde rengine boyanir —
     bu, tek govdeli gorunumle GORSEL OLARAK AYNIDIR, yeniden indirme gerekmez.
     TERSI yon (tek govde ekranda iken 2-renk secilmesi) boyamayla ifade
     EDILEMEZ (ayri yazi govdesi indirilmemistir) -> onizleme yeniden kosar. */
  /* Yazi renginin GUNCEL degeri DAIMA seciciden okunur; son cizimdeki deger yalnizca
     secici henuz yoksa yedektir. (Ilk turda burada `sonYaziRenk` kullaniliyordu:
     musteri 2. rengi degistirince ekran DEGISMIYORDU — bildirilen sikayetin ta kendisi;
     kapi S5b bunu yakaladi.) */
  function guncelYaziRenk(){
    var el=yaziRenkEl();
    return el ? el.value : sonYaziRenk;
  }
  function renkTazele(){
    if(!gosterge){ return; }
    var ik=ikiRenkDurumu(guncelYaziRenk());
    if(ekrandaIkiGovde){
      if(gosterge.renklerAyarla){
        var g=ik?ik.govdeRenk:onizlemeRenk();
        gosterge.renklerAyarla([g, ik?ik.yaziRenk:g]);
      }
      return;
    }
    if(ik){ onizlemeCalistir(); return; }
    var r=onizlemeRenk();
    if(r&&gosterge.renkAyarla){ gosterge.renkAyarla(r); }
  }
  var rbtn=document.querySelectorAll("#renkButonlar .renk-btn");
  for(var ri=0;ri<rbtn.length;ri++){ rbtn[ri].addEventListener("click", renkTazele); }
  var rsec=document.getElementById("renkSec");
  if(rsec){ rsec.addEventListener("change", renkTazele); }
  /* Yazi rengi (2. renk) secicisi konfigurator tarafindan DINAMIK olusturulur;
     bu script ondan once kosabilir -> baglanti tembel yapilir (her denemede
     tekrar aranir, bir kez baglanir). Baglanmazsa 2. renk secimi onizlemeye
     ULASMAZDI (bildirilen sikayetin tam ikizi). */
  function yaziRenkEl(){ return document.getElementById("konf_yazi_renk"); }
  function yaziRenkBagla(){
    var el=yaziRenkEl();
    if(el&&!el.onzBagli){ el.onzBagli=true; el.addEventListener("change", renkTazele); }
  }
  yaziRenkBagla();
  function cevapCoz(c){
    if(!c.ok){ return c.json().then(function(h){ throw new Error(h.hata||("hata-"+c.status)); }); }
    if(c.headers.get("X-Sikistirma")==="gzip"){
      if(!window.DecompressionStream){ throw new Error("tarayici-eski"); }
      return new Response(c.body.pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();
    }
    return c.arrayBuffer();
  }
  function govdeGetir(parametreler, parca){
    var g={ aile: URUN.id, parametreler: parametreler };
    if(parca){ g.parca=parca; }
    return fetch("/api/onizleme/olustur", { method:"POST",
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify(g) }).then(cevapCoz);
  }
  function onizlemeCalistir(){
    if(mesgul){ return; }
    yaziRenkBagla();
    if(!(window.PRUVO_KONF && PRUVO_KONF.hazir() && PRUVO_KONF.gecerliMi())){
      kutu.hidden=false; de("Önce ölçüleri geçerli aralıkta doldurun."); return;
    }
    /* satiraYaz: konfiguratorun dogrulanmis parametre setini verir (fiyat alanlari
       burada KULLANILMAZ; onizleme fiyattan bagimsiz). Govde rengi olarak SAYFADA
       SECILI rengi veririz: konfigurator 2-renk kararini (yazi_renk alani) govde
       rengiyle karsilastirarak verir — sabit "Siyah" verilseydi musteri siyah
       cerceve + siyah yazi secince onizleme 2 renk sanirdi. */
    var s = PRUVO_KONF.satiraYaz({ malzeme:"PLA", renk: seciliRenkAdi()||"Siyah" });
    if(!s.parametreler){ kutu.hidden=false; de("Önce ölçüleri geçerli aralıkta doldurun."); return; }
    /* Onizleme secenek kisitlari (tek kaynak /secenekler.js): uretim motorunda
       KARSILIGI OLMAYAN secimlerde istek atmadan uyar.
       🔴 METIN 2026-08-03'TE DUZELTILDI — ESKI METIN YALAN SOYLUYORDU: "siparis
       verebilirsiniz, uretim etkilenmez" deniyordu, oysa bu liste tam olarak
       URETILEMEZ bolgenin beyanidir (olculdu: petek %50,0 / cetvel %66,7 /
       kase %83,3 — sema kapisi 'gecerli' derken uretim ucu ayni seti reddediyor).
       O ailelerin satis kapisi da ayni gun kapatildi (secenekler.js
       HACIM_DOGRULANMIS_AILELER) -> metin ile kod artik AYNI seyi soyluyor.
       🔴 KARAR MANTIGI BURADA DEGIL: kosullu (`eger`) beyanlar dahil tum kisit
       yargisi secenekler.js onizlemeKisitIhlali() icindedir — Worker sema kapisi
       (onizleme/src/index.js) AYNI fonksiyonu cagirir, ikinci kopya YOK. Fonksiyon
       yoksa (bayat onbellekli secenekler.js) beyan VARKEN bloklanir: fail-closed,
       cunku "kisiti okuyamadim" hali musteriye yanlis vaat basmamali.
       3. ARGUMAN URUN_SEMA: `eger` kosul degerleri SEMAYA gore dogrulanir; hicbir
       musteri girdisiyle eslesemeyen bir kosul degeri (yazim hatasi) girdiyi
       sessizce etkisizlestiremez -> ihlal. Sema verilmeseydi yalniz tip ailesi
       olculebilirdi; bu sayfa semayi TASIR (URUN_SEMA satir-ici). */
    var kis=(window.PRUVO_SECENEK&&PRUVO_SECENEK.ONIZLEME_KISITLAR||{})[URUN.id];
    var kisitFn=window.PRUVO_SECENEK&&PRUVO_SECENEK.onizlemeKisitIhlali;
    if(kis&&(!kisitFn||kisitFn(kis,s.parametreler,URUN_SEMA))){
      kutu.hidden=false;
      de("Bu seçenek üretim hattımızda henüz karşılanmıyor: önizleme sunulamıyor ve bu seçenekle sipariş alınmıyor. Ölçüleri değiştirin ya da WhatsApp'tan teklif isteyin.");
      return;
    }
    var ik=ikiRenkDurumu(s.yazi_renk);
    mesgul=true; btn.disabled=true; kutu.hidden=false; de("Model hazırlanıyor…");
    /* YAYIN SIRASI YEDEGI: parca aileleri derleyici imajina girmeden site kodu
       yayina cikarsa (imaj/paket sirasi) parcali istek "aile-yok" alir. O halde
       onizleme BOS KALMAZ: TEK GOVDE yoluna duser (bugunku davranis). Yalniz
       "parca yolu henuz yok" anlamina gelen hatalarda; gecersiz-geometri gibi
       GERCEK musteri hatalari aynen yukari cikar (maskeleme yok). */
    var YEDEGE_DUS = ["aile-yok", "gecersiz-parca", "bulunamadi"];
    var istek = ik
      ? Promise.all([govdeGetir(s.parametreler,"govde"), govdeGetir(s.parametreler,"yazi")])
          .catch(function(e){
            if(YEDEGE_DUS.indexOf(e.message)<0){ throw e; }
            ik=null;
            return govdeGetir(s.parametreler,null).then(function(b){ return [b]; });
          })
      : govdeGetir(s.parametreler,null).then(function(b){ return [b]; });
    istek.then(function(buflar){
      if(ik && buflar.length===2){
        /* IKI GOVDE, IKI RENK: govde + yazi ayni koordinat sisteminde gelir
           (derleyici ayni uretim modelini yalniz Output farkiyla surer) -> viewer hicbirini
           kaydirmaz, ust uste tam oturur. */
        gosterge=PRUVO_VIEWER.goster(tuval,
          [{ buf:buflar[0], renk:ik.govdeRenk }, { buf:buflar[1], renk:ik.yaziRenk }]);
        ekrandaIkiGovde=true; sonYaziRenk=s.yazi_renk;
        de("Yazı 2. renkte üretilir · Sürükleyerek döndürün · tekerlek/iki parmakla yakınlaştırın");
      } else {
        /* Onizleme rengi TEK KAYNAK /secenekler.js onizlemeRengi(): renk secimi
           acik ailede MUSTERININ sectigi renk, aksi halde aile rengi, o da yoksa
           viewer'in sari-seri varsayilani. */
        var onzRenk=onizlemeRenk();
        gosterge=PRUVO_VIEWER.goster(tuval, buflar[0], onzRenk?{ renk:onzRenk }:undefined);
        ekrandaIkiGovde=false; sonYaziRenk=s.yazi_renk||null;
        de("Sürükleyerek döndürün · tekerlek/iki parmakla yakınlaştırın");
      }
    })
    .catch(function(e){
      var m={
        "gecersiz-geometri":"Bu ölçü kombinasyonu üretilemiyor; ölçüleri değiştirip tekrar deneyin.",
        "onizleme-secenek-kisiti":"Bu seçenek üretim hattımızda henüz karşılanmıyor: önizleme sunulamıyor ve bu seçenekle sipariş alınmıyor. Ölçüleri değiştirin ya da WhatsApp'tan teklif isteyin.",
        "gecersiz-parca":"Önizleme bu üründe 2 renk gösteremiyor; sipariş verebilirsiniz, üretim etkilenmez.",
        "hiz-siniri":"Kısa sürede çok fazla önizleme istendi; bir dakika sonra tekrar deneyin.",
        "derleyici-yok":"Önizleme servisi şu an hazır değil; lütfen daha sonra deneyin.",
        "tarayici-eski":"Tarayıcınız 3D önizlemeyi desteklemiyor."
      };
      de(m[e.message] || "Önizleme oluşturulamadı; lütfen tekrar deneyin.");
    })
    .then(function(){ mesgul=false; btn.disabled=false; });
  }
  btn.addEventListener("click", onizlemeCalistir);
})();
"""

TODAY = datetime.date.today().isoformat()
PRICE_VALID = (datetime.date.today().replace(month=12, day=31)
               + datetime.timedelta(days=365)).isoformat()

# ------------------------------------------------------------------ Google Merchant feed
# /merchant-feed.xml — Google Merchant Center'a gonderilecek urun feed'i (ucretsiz listelemeler).
# SADECE parametrik OLMAYAN, SABIT sayisal fiyatli, gorseli olan urunler girer.
# Parametrik "sari seri" (net fiyati yok -> "Olcuye ozel") feed'e GIRMEZ (Merchant reddeder).
MERCHANT_FEED = "merchant-feed.xml"
FEED_BRAND = "PRUVO"
# --- Gorsel onbellek kirici (cache-bust) ---------------------------------
# Meta/Google katalogu bir gorsel URL'ini BIR KEZ ceker ve onbellege alir; ayni R2 anahtarinin
# uzerine yazilan yeni gorseli ASLA yeniden cekmez (sessiz: feed yesil, reklamda eski gorsel).
# Cozum: feed'deki gorsel URL'lerine SABIT bir surum damgasi (?v=N) eklenir.
# 🔴 Damga ZAMAN/RASTGELE DEGIL, SABIT olmali: her build'de degisen damga tum feed'i degistirir
# -> katalog her seferinde binlerce gorseli yeniden ceker (gereksiz yuk + oran sinirlama).
# Yeni bir toplu re-crawl istenirse bu sayiyi bir artir (1 -> 2) VE
# tools/test-merchant-feed.py icindeki BEKLENEN_DAMGA sabitini ayni degere getir
# (o test damgayi bilerek BAGIMSIZ pinliyor -> tautoloji olmasin diye). Baska yere dokunma.
FEED_IMG_SURUM = "1"
# Urunler talep uzerine ozel uretilir ama sabit fiyatli kalem her zaman uretilebilir -> in_stock.
# (Uretim-sonrasi teslim vurgulanmak istenirse "backorder" yapilabilir.)
FEED_AVAILABILITY = "in_stock"
# Kendi kategorimiz -> Google urun taksonomisi (kaba, gecerli ust dugumler; eslesmeyen atlanir).
GOOGLE_PRODUCT_CATEGORY = {
    "Otomobil": "Vehicles & Parts > Vehicle Parts & Accessories",
    "Motosiklet": "Vehicles & Parts > Vehicle Parts & Accessories",
    "Marin": "Vehicles & Parts > Vehicle Parts & Accessories",
    "Bisiklet": "Sporting Goods > Cycling",
    "Tamirat": "Hardware > Tools",
    "Ev": "Home & Garden",
    "Ofis": "Office Supplies",
    "Elektronik": "Electronics",
    "Kamera": "Cameras & Optics",
    "Bahçe": "Home & Garden > Lawn & Garden",
    "Dekorasyon": "Home & Garden > Decor",
    "Oyun/Hobi": "Toys & Games",
    # Skan Art = dekor/heykel alt-serisi -> Dekorasyon ile ayni taksonomi dugumu.
    # Eslesme yoksa g:google_product_category satiri feed'e HIC yazilmaz (asagida ~2210)
    # ve Merchant siniflandirmasi sessizce duser.
    "Skan Art": "Home & Garden > Decor",
}
# Marka kurali: "3D baski"/"3D printed" -> "ozel tasarim uretim". SADECE uretim iddiasi olan
# ifadeler; kasa kodu (Passat 3B), "3D perspektif", "3D yazici" gibi masum kullanimlara DOKUNMAZ.
_MARKA_SUB = [
    (re.compile(r"3\s*[d]\s*[-\s]?bask[ıi](?:l[ıi])?", re.I), "özel tasarım üretim"),
    (re.compile(r"3\s*boyutlu\s+bask[ıi](?:l[ıi])?", re.I), "özel tasarım üretim"),
    (re.compile(r"3\s*[d]\s*print(?:ed|ing)?", re.I), "özel tasarım üretim"),
]

# Kaynak model CC lisanslıysa (MakerWorld / Thingiverse / Printables) atıf ZORUNLU.
# urunler.json'da ürüne "lisans": {"tasarimci": "Ad", "tur": "CC BY 4.0"} eklenir;
# "url" verilmezse tür kodundan aşağıdaki tablodan otomatik CC linki türetilir.
# (CGTrader royalty-free lisanslı ürünlerde CC atıfı yoktur; "lisans" alanı eklenmez.)
CC_URLS = {
    "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC BY-SA 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "CC BY-ND 4.0": "https://creativecommons.org/licenses/by-nd/4.0/",
    "CC BY-NC 4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
    "CC BY-NC-SA 4.0": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    "CC BY-NC-ND 4.0": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
    "CC0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
}

FAVICON = ("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' "
           "viewBox='0 0 100 100'><rect width='100' height='100' rx='20' "
           "fill='%2312294d'/><text x='50' y='55' font-family='Arial,"
           "Helvetica,sans-serif' font-size='72' font-weight='800' "
           "fill='%23ffffff' text-anchor='middle' dominant-baseline='central'"
           ">P</text></svg>")

WA_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12.04 2C6.58 '
           '2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2 22l5.25-1.38a9.9 '
           '9.9 0 0 0 4.79 1.22h.01c5.46 0 9.9-4.45 9.9-9.91 0-2.65-1.03-5.14-'
           '2.9-7.01A9.82 9.82 0 0 0 12.04 2zm5.8 14.13c-.24.68-1.42 1.31-1.96 '
           '1.35-.5.05-.98.24-3.3-.69-2.77-1.09-4.56-3.9-4.7-4.08-.14-.19-1.12-'
           '1.49-1.12-2.84 0-1.35.71-2.02.96-2.29.24-.27.53-.34.71-.34.18 0 .35 '
           '0 .51.01.16.01.38-.06.6.46.24.56.79 1.94.86 2.08.07.14.12.31.02.5-'
           '.09.19-.14.31-.28.48-.14.17-.29.37-.42.5-.14.14-.28.29-.12.57.16.28'
           '.72 1.18 1.54 1.91 1.06.94 1.95 1.24 2.23 1.38.28.14.44.12.6-.07.16-'
           '.19.69-.8.87-1.08.18-.28.36-.23.6-.14.24.09 1.55.73 1.81.86.27.14.45'
           '.21.51.32.06.11.06.64-.18 1.32z"/></svg>')

# Karbon Katkılı SİTEDE SATILMAZ — mühendislik malzemesi, WhatsApp özel talebi
# (secenekler.js FILAMENT_SIRA'da yok). ABS 14 Ağu'da satışa AÇILDI (kategori süzgeciyle);
# bu not artık YALNIZ karbon fiber/takviyeli aileyi anlatır. Not metni TEK KAYNAK: hem malzeme
# seçicisinin altında (fonksiyonel/parametrik ürün) hem de seçici olmayan ürünlerdeki filament
# bilgi bloğunda (filament_html) aynen kullanılır.
def muhendislik_wa_not(p=None, url=None):
    """Mühendislik-malzeme (karbon fiber/ABS) özel üretim WhatsApp notu.

    NİYET KORUNUR: bu link "malzeme/özel üretim sorusu"dur — help-cta'nın "aradığımı
    bulamadım" niyetiyle KARIŞTIRILMAZ. Eklenen tek şey SAYFA BAĞLAMI (ürün adı +
    canonical URL) ki Ege hangi üründe hangi malzemenin sorulduğunu bilsin; bağlam
    yoksa (p/url verilmemişse) metin eskisi gibi bağlamsız kalır.

    Kodlama: quote() ile TEK KEZ percent-kodlama (wa_href sözleşmesi), döndürülen
    HTML'de href zaten kodlu -> %-biçimlendirme KULLANILMAZ (URL'i bozar), parçalar
    birleştirilir. Numara = WHATSAPP sabiti."""
    from urllib.parse import quote
    msg = u"Merhaba, mühendislik malzemesiyle özel üretim hakkında bilgi almak istiyorum."
    if p is not None and url:
        msg = (u"Merhaba, şu sayfadaydım: " + (p.get("baslik") or "") + "\n" + url + "\n"
               + u"Mühendislik malzemesiyle (karbon fiber vb.) özel üretim hakkında "
                 u"bilgi almak istiyorum.")
    return ('<p class="malzeme-not">Karbon fiber veya diğer mühendislik malzemeleriyle '
            'üretim için <a href="https://wa.me/' + WHATSAPP + '?text=' + quote(msg) + '" '
            'target="_blank" rel="noopener">WhatsApp\'tan bize yazın</a>.</p>')

# Malzeme/renk satırları — klasik opsiyon bloğu ve parametrik konfigüratör AYNI bileşeni
# kullanır. Seçenekler ve "(+%30)" etiketleri secenekler.js'ten ÜRETİLİR (elle yazılmaz):
# katsayı orada değişince etiket sessizce eskimesin.
def _renk_html():
    """Renk seçici satırı (malzemeden bağımsız — hem konfigüratör hem kart-seçim ürünü kullanır)."""
    renk_opts = "".join(
        '\n          <option value="%s">%s</option>' % (
            esc(r), esc(r + (" (+%%%d)" % RENK_DIGER_YUZDE if r == "Diğer" else "")))
        for r in RENK_SECENEKLERI)
    return ("""
      <div class="opsiyon-row">
        <label for="renkSec">Renk</label>
        <select id="renkSec">""" + renk_opts + """
        </select>
        <input type="text" id="renkOzel" placeholder="istediğiniz rengi yazın" style="display:none">
      </div>""")


def _konfigur_varsayilan_renk(konfigur):
    """KONFIGUR (dekor) sayfasinda ONDEN SECILI renk. Secim, sayfanin ANA GORSELI ile
    celismeyecek renktir: renkGorselIndeks'i 0 olan (yani mainImg'de zaten gorunen) renk;
    yoksa listenin ilki. Boylece on-secim goruntuyu DEGISTIRMEZ, yalnizca durumu doldurur
    -> "secili gorunuyor ama sepete eklenmiyor" yalani dogmaz."""
    renkler = konfigur.get("renkler") or []
    if not renkler:
        return None
    ix = konfigur.get("renkGorselIndeks") or {}
    for r in renkler:
        if ix.get(r) == 0:
            return r
    return renkler[0]


def _renk_butonlari_html(renkler=None, renk_gorselleri=None, secili=None):
    """Renk BUTONLARI (Okan, 16 Tem) — fonksiyonel/kart-seçim ürününde dropdown yerine 4 buton:
    Siyah/Beyaz/Gri düz renk yuvarlağı, Diğer = gökkuşağı gradyan. Önden seçili YOK; 'Diğer'
    seçilince altında serbest metin kutusu (renkOzel) belirir. Parametrik ürün DROPDOWN kalır.

    KONFIGUR dalı (dekor konfigüratörü): renkler verilirse YALNIZ o alt küme basılır
    ('Diğer' yok -> renkOzel kutusu da basılmaz) ve her butona data-gorsel eklenir
    (renk_gorselleri[renk] = o rengin ürün görseli; /konfigur.js tıklamada ana görseli
    değiştirir). renkler=None çağrısı bugünkü çıktıyla BAYT-BAYT aynıdır (geri uyumluluk)."""
    ornek = {
        "Siyah": '<span class="renk-yuvar" style="background:#151515"></span>',
        "Beyaz": '<span class="renk-yuvar" style="background:#fff;border:1px solid var(--gray-line)"></span>',
        "Gri": '<span class="renk-yuvar" style="background:#8a929e"></span>',
        "Diğer": '<span class="renk-yuvar renk-yuvar-gokkusagi"></span>',
    }
    # Onden secili renk (11 Agu): secili=None cagrisi eski ciktiyla BAYT-ESIT kalir.
    def _cls(r):
        return "renk-btn secili" if (secili is not None and r == secili) else "renk-btn"

    def _ek(r):
        return ' aria-pressed="true"' if (secili is not None and r == secili) else ""

    if renkler is not None:
        btns = "".join(
            '<button type="button" class="%s" data-renk="%s" data-gorsel="%s"%s>%s'
            '<span class="renk-ad">%s</span></button>' % (
                _cls(r), esc(r), esc((renk_gorselleri or {}).get(r, "")), _ek(r),
                ornek.get(r, ""), esc(r))
            for r in renkler)
        return ("""
      <div class="opsiyon-row opsiyon-renk">
        <label>Renk</label>
        <div class="renk-butonlar" id="renkButonlar">""" + btns + """</div>
      </div>""")
    btns = "".join(
        '<button type="button" class="%s" data-renk="%s"%s>%s'
        '<span class="renk-ad">%s</span></button>' % (
            _cls(r), esc(r), _ek(r), ornek.get(r, ""),
            esc(r + (" (+%%%d)" % RENK_DIGER_YUZDE if r == "Diğer" else "")))
        for r in RENK_SECENEKLERI)
    return ("""
      <div class="opsiyon-row opsiyon-renk">
        <label>Renk</label>
        <div class="renk-butonlar" id="renkButonlar">""" + btns + """</div>
      </div>
      <input type="text" id="renkOzel" class="renk-ozel" maxlength="30"
             placeholder="istediğiniz rengi yazın (ör. turuncu)" style="display:none">""")


def _malzeme_renk_html(p=None, url=None):
    """Malzeme dropdown + mühendislik-malzeme WA notu + renk. YALNIZ parametrik (konfigüratör)
    ürün sayfası kullanır — fonksiyonel ürünlerde malzeme artık kartlardan seçilir (dropdown yok).
    p/url verilirse WA notu sayfa bağlamını (ad + canonical URL) taşır.

    🔴 MALZEME x KATEGORI KAPISI (14 Ağu): liste ürünün kategorisine göre SÜZÜLÜR
    (secenekler.js FILAMENT_KATEGORI_HARIC — tek kaynak). p verilmezse kategori
    çözülemez ve kısıtlı malzeme FAIL-CLOSED düşer."""
    kategori = p.get("kategori") if p else None
    malzeme_opts = "".join(
        '\n          <option value="%s">%s</option>' % (
            esc(m), esc(m + (" (standart)" if not FILAMENT_FARK.get(m)
                             else " (+%%%d)" % FILAMENT_FARK[m])))
        for m in FILAMENT_SIRA if malzeme_kategori_uygun_mu(m, kategori))
    # NOT: metinde yuzde-kacisli WhatsApp URL'i var (%2C, %C3%BC...) -> %-bicimlendirme
    # KULLANILMAZ (URL'i bozar / ValueError verir); parcalar birlestirilir.
    return ("""
      <div class="opsiyon-row">
        <label for="malzemeSec">Malzeme</label>
        <select id="malzemeSec">""" + malzeme_opts + """
        </select>
      </div>
      """ + muhendislik_wa_not(p, url) + _renk_html())


# Adet seçici — klasik blok ve konfigüratör ortak (Okan, 16 Tem: varsayılan 1, aralık 1-99).
ADET_HTML = """
      <div class="opsiyon-row">
        <label for="adetSec">Adet</label>
        <div class="adet-kutu">
          <button type="button" class="adet-btn" id="adetEksi" aria-label="Adet azalt">−</button>
          <input type="number" id="adetSec" value="1" min="%d" max="%d"
                 inputmode="numeric" aria-label="Adet">
          <button type="button" class="adet-btn" id="adetArti" aria-label="Adet artır">+</button>
        </div>
      </div>"""

# Adet + eylem İKONLARI (Okan madde 7, 16 Tem) — YALNIZ kart-seçim (normal fonksiyonel) sayfa:
# sayfa altındaki iki büyük buton kalkar, Adet satırının SAĞINA yazısız iki küçük ikon gelir
# (sepet = lacivert, WhatsApp = yeşil; 44×44 dokunma alanı, aria-label + title zorunlu).
# id'ler (cartBtn/orderAlt) AYNEN korunur — sayfa scripti (seçim şartı + titreme + WA mesajı)
# değişmeden çalışır. Parametrik/şemasız/panelsiz sayfalarda büyük butonlar YERİNDE kalır.
# %s sırası: min, max, ikon bloğu (pid + wa href ile üretilir).
ADET_IKON_HTML = """
      <div class="opsiyon-row opsiyon-adet-eylem">
        <label for="adetSec">Adet</label>
        <div class="adet-kutu">
          <button type="button" class="adet-btn" id="adetEksi" aria-label="Adet azalt">−</button>
          <input type="number" id="adetSec" value="1" min="%d" max="%d"
                 inputmode="numeric" aria-label="Adet">
          <button type="button" class="adet-btn" id="adetArti" aria-label="Adet artır">+</button>
        </div>
        %s
      </div>"""


def konf_sema(pid):
    """Parametrik ürünün konfigüratör şeması (jenerator/urunler/<id>.json); yoksa None."""
    yol = os.path.join(JEN_URUN_DIR, "%s.json" % pid)
    if not os.path.exists(yol):
        return None
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def taban_fiyat_metni(tl):
    """TL sayısını secenekler.js kurusMetni ile AYNI biçimde yazar: 150 -> "150,00 TL".
    Sarı sayfanın JS öncesi başlangıç fiyatı bundan üretilir; JS aynı değeri kuruşla
    tazelediği için biçim ayrışırsa metin 'zıplar' — o yüzden ikinci biçim yok."""
    tam, kusur = ("%.2f" % tl).split(".")
    tam = "{:,}".format(int(tam)).replace(",", ".")
    return tam + "," + kusur + " TL"


# ------------------------------------------------------------------ konfigur (dekor konfigüratörü)
# Ürün objesindeki OPSİYONEL "konfigur" alanı: müşteri sayfada RENK (görsel de değişir) +
# BOY (kaydırma çubuğu) seçer, fiyat canlı hesaplanır. Sarı seri kural setinden BAĞIMSIZ
# (parametrik:true KULLANILMAZ; kategori normal kalır). Alan YOKSA sayfa bugünkü gibi
# davranır — kabul: tools/konfigur-test.py (bayt-eşitlik + şema + fiyat monotonluğu).
# Beklenen yapı:
#   "konfigur": {
#     "renkler": ["Siyah", "Beyaz", "Gri"],            # secenekler.js RENK_SECENEKLERI alt kümesi, "Diğer" YASAK
#     "renkGorselIndeks": {"Siyah": 0, ...},           # renk -> gorseller[i] (görsel değişimi)
#     "boyutMm": {"min": 60, "max": 300, "adim": 10, "varsayilan": 150, "etiket": "Yükseklik"},
#     "hacim": {"refYukseklikMm": 1899.739, "refHacimCm3": 239222.8},  # referans model ölçümü
#     "fiyatCapalari": [[60, 150], [300, 1300]]        # [boyMm, TL] × 2 — eğri bu iki çapadan çözülür
#   }
# FİYAT MODELİ (mimar kararı, Okan onaylı band — TUR-3): iki çapadan çözülen AFİN model
# fiyat_TL = sabit + birim × hacim_cm3(boy); pilot çapalarla birim ≈ 1,2306 TL/cm³,
# sabit ≈ 140,72 TL. sabit/birim koda YAZILMAZ, çapadan ÇÖZÜLÜR (Okan tek çapa sayısını
# değiştirince eğri türesin). Fiyat en küçük boydan itibaren KESİN ARTAN; görünen fiyat
# TAM TL'ye yuvarlanır. Ürünün "fiyat" alanı = çapa-1 (EN KÜÇÜK boy) fiyatı — JSON-LD
# Offer.price ve Merchant feed'e mevcut kod yolundan otomatik bu (minimum) sayı gider.


def konfigur_dogrula(p):
    """Ürünün "konfigur" alanını doğrular; hata mesajı listesi döner (boş = geçerli).
    FAIL-CLOSED: render_product geçersiz konfigur'da build'i DÜŞÜRÜR — yanlış fiyat/görsel
    eşlemesi sessizce yayına çıkamaz (kategori uyarısının aksine bu ticari beyandır)."""
    hatalar = []
    k = p.get("konfigur")
    if not isinstance(k, dict):
        return ["konfigur bir obje değil"]
    if p.get("parametrik"):
        hatalar.append("konfigur ile parametrik:true birlikte olamaz (sarı seri kural seti tetiklenmesin)")

    renkler = k.get("renkler")
    if not isinstance(renkler, list) or not renkler:
        hatalar.append("renkler boş ya da liste değil")
        renkler = []
    else:
        if len(set(renkler)) != len(renkler):
            hatalar.append("renkler içinde mükerrer değer var")
        for r in renkler:
            if not isinstance(r, str) or not r.strip():
                hatalar.append("renkler içinde boş/dize-olmayan değer var")
            elif r == "Diğer":
                hatalar.append("renkler 'Diğer' içeremez (özel renk yüzdesi bu akışta hesaplanmıyor)")
            elif r not in RENK_SECENEKLERI:
                hatalar.append("bilinmeyen renk: %r (secenekler.js RENK_SECENEKLERI dışı)" % r)

    bm = k.get("boyutMm")
    if not isinstance(bm, dict):
        hatalar.append("boyutMm eksik ya da obje değil")
    else:
        sayilar = {}
        for alan in ("min", "max", "adim", "varsayilan"):
            v = bm.get(alan)
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not v > 0:
                hatalar.append("boyutMm.%s pozitif sayı olmalı" % alan)
            else:
                sayilar[alan] = float(v)
        if len(sayilar) == 4:
            if not (sayilar["min"] < sayilar["varsayilan"] < sayilar["max"]):
                hatalar.append("boyutMm sırası bozuk: min < varsayilan < max olmalı")
            for alan in ("varsayilan", "max"):
                kalan = (sayilar[alan] - sayilar["min"]) / sayilar["adim"]
                if abs(kalan - round(kalan)) > 1e-6:
                    hatalar.append("boyutMm.%s adıma oturmuyor (min + n×adim olmalı)" % alan)
        etiket = bm.get("etiket")
        if not isinstance(etiket, str) or not etiket.strip():
            hatalar.append("boyutMm.etiket boş olamaz (sepet/WhatsApp satır detayında görünür)")

    h = k.get("hacim")
    if not isinstance(h, dict):
        hatalar.append("hacim eksik ya da obje değil")
    else:
        for alan in ("refYukseklikMm", "refHacimCm3"):
            v = h.get(alan)
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not v > 0:
                hatalar.append("hacim.%s pozitif sayı olmalı" % alan)

    gorseller = images_of(p)
    rgi = k.get("renkGorselIndeks")
    if not isinstance(rgi, dict):
        hatalar.append("renkGorselIndeks eksik ya da obje değil")
    elif renkler:
        if set(rgi.keys()) != set(renkler):
            hatalar.append("renkGorselIndeks anahtarları renkler listesiyle birebir örtüşmeli")
        for r, idx in rgi.items():
            if not isinstance(idx, int) or isinstance(idx, bool) or not (0 <= idx < len(gorseller)):
                hatalar.append("renkGorselIndeks[%r] geçersiz görsel indeksi: %r (gorseller %d adet)"
                               % (r, idx, len(gorseller)))

    # Fiyat çapaları: [boyMm, TL] × 2 — afin eğri bu iki noktadan çözülür.
    capalar = k.get("fiyatCapalari")
    capa_gecerli = True
    if (not isinstance(capalar, list) or len(capalar) != 2 or
            any(not isinstance(c, list) or len(c) != 2 for c in capalar)):
        hatalar.append("fiyatCapalari [[boyMm, TL], [boyMm, TL]] biçiminde tam 2 çapa olmalı")
        capa_gecerli = False
    else:
        for c in capalar:
            for v in c:
                if not isinstance(v, (int, float)) or isinstance(v, bool) or not v > 0:
                    hatalar.append("fiyatCapalari değerleri pozitif sayı olmalı: %r" % (c,))
                    capa_gecerli = False
                    break
    if capa_gecerli:
        if not capalar[0][0] < capalar[1][0]:
            hatalar.append("fiyatCapalari boyları artan sırada olmalı (capa1.boy < capa2.boy)")
        if not capalar[0][1] < capalar[1][1]:
            hatalar.append("fiyatCapalari fiyatları artan olmalı (birim > 0 -> fiyat kesin artan)")
        if isinstance(bm, dict) and isinstance(bm.get("min"), (int, float)) and \
                isinstance(bm.get("max"), (int, float)):
            if abs(capalar[0][0] - bm["min"]) > 1e-9:
                hatalar.append("capa1 EN KÜÇÜK boyda olmalı (capa1.boy == boyutMm.min) — "
                               "JSON-LD/feed minimum fiyat beyanı bu çapadan gelir")
            if capalar[1][0] > bm["max"] + 1e-9:
                hatalar.append("capa2.boy boyutMm.max'ı aşamaz")

    # "fiyat" alanı = çapa-1 (EN KÜÇÜK boyun) fiyatı (feed/JSON-LD ile TEK kaynak). Boş ya
    # da çapadan farklıysa minimum fiyat beyanı yalan olur -> reddedilir.
    fiyat_sayi = feed_price(p.get("fiyat") if "fiyat" in p else "")
    if not fiyat_sayi:
        hatalar.append('konfigur\'lu üründe "fiyat" sayısal minimum fiyat taşımalı '
                       '(ör. "150 TL" — çapa-1/en küçük boyun fiyatı; JSON-LD/feed bunu basar)')
    elif capa_gecerli and abs(int(fiyat_sayi) - capalar[0][1]) > 0.005:
        hatalar.append('"fiyat" alanı (%s TL) çapa-1 fiyatıyla (%s TL) aynı olmalı '
                       "(JSON-LD Offer.price = minimum fiyat beyanı)" % (fiyat_sayi, capalar[0][1]))

    # Malzeme ekseni (OPSİYONEL): "malzemeler" [{ad, katsayi}] + "varsayilanMalzeme".
    # Alan YOKSA sayfa bugünkü gibi (renk+boy) davranır — GERİ UYUMLULUK. Alan varsa
    # fail-closed: katsayı secenekler.js FILAMENT_FARK TEK KAYNAĞIYLA örtüşmeli (drift
    # nöbeti — yanlış katsayı = sessiz ticari beyan hatası), ABS+Karbon SATIŞA KAPALI
    # (FILAMENT_SIRA dışı ad reddedilir), en düşük malzeme × çapa-1 = "fiyat" (min offer).
    malz = k.get("malzemeler")
    if malz is not None or "varsayilanMalzeme" in k:
        if not isinstance(malz, list) or not malz:
            hatalar.append("malzemeler boş ya da liste değil (malzeme ekseni açıksa dolu olmalı)")
            malz = []
        adlar, katsayilar = [], []
        for m in malz:
            if not isinstance(m, dict):
                hatalar.append("malzemeler öğesi obje değil: %r" % (m,))
                continue
            ad, kat = m.get("ad"), m.get("katsayi")
            if not isinstance(ad, str) or not ad.strip():
                hatalar.append("malzeme.ad boş/dize değil: %r" % (ad,))
                continue
            if ad not in FILAMENT_SIRA:
                hatalar.append("satışa kapalı/bilinmeyen malzeme: %r (izinli: %s; "
                               "ABS+Karbon SATIŞA KAPALI)" % (ad, ", ".join(FILAMENT_SIRA)))
                continue
            adlar.append(ad)
            beklenen = 1.0 + FILAMENT_FARK.get(ad, 0) / 100.0
            if not isinstance(kat, (int, float)) or isinstance(kat, bool) or not kat > 0:
                hatalar.append("malzeme.katsayi pozitif sayı olmalı: %r (%s)" % (kat, ad))
            elif abs(float(kat) - beklenen) > 1e-9:
                hatalar.append("malzeme %s katsayısı %.2f olmalı (secenekler.js FILAMENT_FARK "
                               "tek kaynağı), gelen: %r" % (ad, beklenen, kat))
            else:
                katsayilar.append(float(kat))
        if len(set(adlar)) != len(adlar):
            hatalar.append("malzemeler içinde mükerrer 'ad' var")
        vm = k.get("varsayilanMalzeme")
        if not isinstance(vm, str) or vm not in adlar:
            hatalar.append("varsayilanMalzeme malzemeler listesindeki bir 'ad' olmalı: %r" % (vm,))
        # JSON-LD/feed Offer.price = MİNİMUM: en düşük katsayı × çapa-1 (round-TL) == "fiyat".
        if katsayilar and capa_gecerli and fiyat_sayi:
            min_tl = int(math.floor(capalar[0][1] * min(katsayilar) + 0.5))
            if abs(min_tl - int(fiyat_sayi)) > 0.005:
                hatalar.append('malzeme ekseni açıkken "fiyat" (%s TL) EN DÜŞÜK malzeme × '
                               "çapa-1 (%s TL) olmalı (JSON-LD Offer.price = minimum offer)"
                               % (fiyat_sayi, min_tl))
    return hatalar


def konfigur_hacim_mm3(konfigur, boy_mm):
    """Referans modelden küple ölçeklenmiş hacim (mm³). /konfigur.js hacimMm3 ile AYNI
    işlem sırası (çift hassasiyet eşleniği) — JS öncesi basılan başlangıç fiyatı, sayfa
    JS'inin ilk hesabıyla bayt-bayt aynı metni versin diye."""
    h = konfigur["hacim"]
    oran = boy_mm / float(h["refYukseklikMm"])
    return float(h["refHacimCm3"]) * 1000 * oran * oran * oran


def _konfigur_fiyat_modeli(konfigur):
    """/konfigur.js fiyatModeli'nin Python aynası (AYNI işlem sırası): iki çapadan
    afin model çöz -> (birim TL/cm³, sabit TL)."""
    c = konfigur["fiyatCapalari"]
    v1 = konfigur_hacim_mm3(konfigur, c[0][0]) / 1000.0
    v2 = konfigur_hacim_mm3(konfigur, c[1][0]) / 1000.0
    birim = (c[1][1] - c[0][1]) / (v2 - v1)
    return birim, c[0][1] - birim * v1


def konfigur_fiyat_kurus(konfigur, boy_mm, katsayi=1.0):
    """/konfigur.js fiyatKurus'un Python aynası: fiyat_TL = (sabit + birim × hacim_cm3) ×
    malzeme katsayısı, TAM TL'ye yuvarlanır (Math.round eşleniği floor(x+0.5)), kuruş = TL × 100.
    katsayi=1.0 (PLA / malzemesiz) => malzeme-öncesi kodla BİREBİR aynı (geri uyumluluk).
    Drift nöbeti: tools/konfigur-test.py bu fonksiyonu node'daki GERÇEK JS ile karşılaştırır."""
    birim, sabit = _konfigur_fiyat_modeli(konfigur)
    k = katsayi if (isinstance(katsayi, (int, float)) and not isinstance(katsayi, bool)
                    and katsayi > 0) else 1.0
    tl = (sabit + birim * (konfigur_hacim_mm3(konfigur, boy_mm) / 1000.0)) * k
    tavan = 3 * konfigur["fiyatCapalari"][0][1]   # 3× TAVAN (Okan)
    if tl > tavan:
        tl = tavan
    return int(math.floor(tl + 0.5)) * 100


def _sayi_metni(v):
    """HTML sayı niteliği için kısa metin: 6.0 -> "6", 0.5 -> "0.5" (nokta ondalık)."""
    return "%g" % v


def _konfigur_boy_html(konfigur):
    """Boy satırı: sayı kutusu (cm) + kaydırma çubuğu (cm) — sarı konfigüratörün alan
    dili (konf-row/konf-sayi/konf-kaydirici sınıfları AYNEN). Kaydırıcı görsel birincil
    kontrol; erişilebilir kontrol sayı kutusudur (kaydırıcı aria-hidden, sarıyla aynı)."""
    bm = konfigur["boyutMm"]
    c_min, c_max = _sayi_metni(bm["min"] / 10.0), _sayi_metni(bm["max"] / 10.0)
    c_adim, c_var = _sayi_metni(bm["adim"] / 10.0), _sayi_metni(bm["varsayilan"] / 10.0)
    etiket = bm.get("etiket") or "Boy"
    return ("""
      <div class="opsiyon-row konf-row">
        <label for="konfigurBoy">%s</label>
        <input type="number" id="konfigurBoy" class="konf-sayi" inputmode="decimal"
               min="%s" max="%s" step="%s" value="%s">
        <span class="konf-birim">cm</span>
      </div>
      <div class="konf-kaydirici-satir">
        <input type="range" id="konfigurKaydirici" class="konf-kaydirici"
               min="%s" max="%s" step="%s" value="%s" aria-hidden="true" tabindex="-1">
      </div>""" % (esc(etiket), c_min, c_max, c_adim, c_var,
                   c_min, c_max, c_adim, c_var))


def _konfigur_malzeme_html(malzemeler, varsayilan, p):
    """Malzeme seçici — sitenin STANDART filament KARTLARIYLA (filament_html) AYNI görsel
    bileşen: ısı dayanımı + kısa etiket + bilgi balonu (tooltip) + "Tavsiyemiz" rozeti,
    tek kaynak filamentler.json'dan türetilir. Fark: her kart /konfigur.js'in bağladığı
    .malzeme-btn kancasını + data-katsayi fiyat çarpanını taşır ve #malzemeButonlar içinde
    olur. Böylece konfigur ürününde TEK, tutarlı malzeme arayüzü olur (eski basit-buton
    seçici + ayrı fancy bilgi kartı "çift-UI"si kalkar; kart-seçim/parametrik ürünlerdeki
    filament kartıyla birebir dil). Varsayılan malzeme önden 'secili' (lacivert dolgu).
    filamentler.json'da tanımsız / satışa kapalı (ABS/Karbon) malzeme konfigur_dogrula ile
    ZATEN reddedilir -> burada bulunamayan malzeme savunmacı atlanır."""
    ref = filament_ortak.referans()
    fil_map = {f["ad"]: f for f in ref["filamentler"]}
    tavs = {t["ad"]: t["rozet"]
            for t in filament_ortak.tavsiyeler(p.get("kategori"), p.get("tavsiyeFilament"))}
    kartlar = []
    for m in malzemeler:
        ad = m["ad"]
        f = fil_map.get(ad)
        if not f:
            continue
        kat = float(m["katsayi"])
        rozet = tavs.get(ad, "")
        rozet_html = ""
        if rozet:
            rcls = "fil-rozet" if rozet == "Tavsiyemiz" else "fil-rozet fil-rozet-not"
            rozet_html = '<span class="%s">%s</span>' % (rcls, esc(rozet))
        # Sınıf sırası: fil-cip [tavsiyeli] malzeme-btn [secili] — "fil-cip tavsiyeli" bitişik
        # (test-skan-art bunu arar); .malzeme-btn = /konfigur.js kancası; .secili = varsayılan.
        cls = "fil-cip"
        if rozet:
            cls += " tavsiyeli"
        cls += " malzeme-btn"
        if ad == varsayilan:
            cls += " secili"
        kartlar.append(
            '<button type="button" class="%s" data-malzeme="%s" data-katsayi="%s" '
            'aria-expanded="false">'
            '<span class="fil-isi">%s</span>'
            '<span class="fil-ad">%s</span>'
            '<span class="fil-etiket">%s</span>'
            '%s'
            '<span class="fil-balon" role="tooltip"><strong>%s — %s</strong><br>%s</span>'
            '</button>'
            % (cls, esc(ad), _sayi_metni(kat), esc(f["isiDayanimi"]), esc(ad),
               esc(f["kisaEtiket"]), rozet_html,
               esc(f.get("uzunAd") or ad), esc(f["kisaEtiket"]), esc(f["uzun"])))
    # Kaplayıcı .fil-cipler (position:relative) -> .fil-balon tooltip doğru konumlanır;
    # id="malzemeButonlar" /konfigur.js'in bağlama kancası (DEĞİŞMEDEN çalışır).
    return ("""
      <div class="opsiyon-row opsiyon-renk">
        <label>Malzeme</label>
        <div class="fil-cipler" id="malzemeButonlar">""" + "".join(kartlar) + """</div>
      </div>""")


# 🔴 GORUNUR SECIM HATASI (11 Agu) — sessiz basarisizligin panzehiri.
# Butonun HEMEN ALTINDA durur; role="alert" + aria-live ile ekran okuyucuya da gider.
# Kural: "Sepete Ekle"ye basildiginda ya ekleme OLUR ya BU KUTU DOLAR — sessiz titreme
# tek basina YETMEZ (kullanici tikladigini sanip sepeti bos birakiyordu).
# Bicim SATIR ICI yazilir, paylasilan PAGE_CSS'e kural EKLENMEZ: oraya tek satir eklemek
# secici tasimayan (fiziksel/panelsiz) sayfalarin da BAYTINI degistirirdi.
SECIM_HATA_HTML = ('<div class="secim-hata" id="secimHata" role="alert" aria-live="assertive" '
                   'hidden style="margin:2px 0 12px;padding:9px 12px;border-radius:8px;'
                   'background:#fdecea;border:1px solid #f0b3ae;color:#8f1d19;font-size:13.5px;'
                   'font-weight:600;line-height:1.45"></div>')

CART_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 '
             '7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96 0 1.1.9 2 2 2h12v-2H7.42c-.14 '
             '0-.25-.11-.25-.25l.03-.12L8.1 15h7.45c.75 0 1.41-.41 1.75-1.03l3.58-6.49A1 1 0 0 0 20 6H5.21l-.94-2H1zm16 '
             '16c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2z"/></svg>')

# Eylem butonlari (kart-secim sayfasi, Adet satirinin sagi) — %s sirasi: pid, wa href.
# 🔴 CTA DENGESI (Okan, 11 Agu): birincil eylem SEPETE EKLE'dir. Once ikisi de yazisiz
# 44x44 ikondu; yanlarindaki sticky WhatsApp bandi butonu ise 231x44 idi -> WhatsApp
# dokunma alaninda 5,22 KAT buyuk gorunuyordu. Artik sepet butonu ETIKETLI ve genis
# (tools/cta-denge-kapisi.py olcer), WhatsApp KALIR ama ikincil ikon boyunda durur.
# `.cart-label` sinifi ZORUNLU: sayfa scripti sepetteki/sepette-degil durumunu O spanin
# metninden bildirir (buyuk buton kalibiyla AYNI kanca — ikinci kopya yok).
IKON_BUTONLAR_HTML = (
    '<div class="eylem-ikonlar">'
    '<button class="ikon-btn ikon-sepet" id="cartBtn" data-id="%s" '
    'aria-label="Sepete Ekle" title="Sepete Ekle">' + CART_ICON +
    '<span class="cart-label">Sepete Ekle</span></button>'
    '<a class="ikon-btn ikon-wa" id="orderAlt" href="%s" target="_blank" rel="noopener" '
    'aria-label="WhatsApp\'tan Sor" title="WhatsApp\'tan Sor">' + WA_ICON + '</a>'
    '</div>')

# BÜYÜK butonlar (eski düzen) — parametrik + şemasız-fonksiyonel + panelsiz (Dekorasyon/
# Oyun-Hobi) sayfalarda AYNEN kalır (Okan talimatı NORMAL ürün sayfası için).
# %s sırası: pid, wa href.
BUYUK_BUTONLAR_HTML = (
    '<button class="cart-btn" id="cartBtn" data-id="%s">' + CART_ICON +
    '<span class="cart-label">Sepete Ekle</span></button>\n'
    '      <a class="order-wa" id="orderAlt" href="%s" target="_blank" rel="noopener">' +
    WA_ICON + 'WhatsApp\'tan Sor</a>')

# ------------------------------------------------------------------ ortak CSS
PAGE_CSS = """
  :root{
    --navy:#12294d;--navy-2:#1c3a6b;--navy-dark:#0d1e3a;
    --gray-bg:#eef1f5;--gray-card:#fff;--gray-line:#d7dde6;
    --gray-text:#5b6675;--red:#d1332e;--red-dark:#b12723;
    --radius:10px;--shadow:0 2px 10px rgba(18,41,77,.08);
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    background:var(--gray-bg);color:var(--navy);line-height:1.5}
  a{color:inherit}
  header{background:var(--navy);color:#fff;padding:20px;box-shadow:var(--shadow)}
  .header-inner{max-width:1100px;margin:0 auto;display:flex;align-items:center;
    justify-content:space-between;gap:16px;flex-wrap:wrap}
  .brand-link{text-decoration:none;color:#fff;display:block}
  .brand{font-size:34px;font-weight:800;letter-spacing:3px;line-height:1}
  .brand-sub{font-size:12px;letter-spacing:2px;text-transform:uppercase;
    color:#b9c6dc;margin-top:5px}
  .top-back{color:#cdd8ea;text-decoration:none;font-weight:600;font-size:14px;
    white-space:nowrap}
  .top-back:hover{color:#fff}

/* === KRITIK CEKIRDEK SONU === */
  .help-cta{background:var(--gray-card);border-bottom:1px solid var(--gray-line);box-shadow:var(--shadow);
    position:sticky;top:0;z-index:100}
  .help-cta-inner{max-width:1100px;margin:0 auto;padding:16px 20px;display:flex;align-items:center;
    justify-content:center;flex-wrap:wrap;gap:12px 18px;text-align:center}
  .help-cta-text{font-size:15.5px;color:var(--navy)}
  .help-cta-text strong{font-weight:800}
  .info-strip{background:#fff;border-bottom:1px solid var(--gray-line)}
  .info-strip-inner{max-width:1100px;margin:0 auto;padding:12px 20px;text-align:center}
  .info-strip p{font-size:14px;color:var(--gray-text);line-height:1.5;margin:0}
  .info-strip strong{color:var(--navy);font-weight:700}
  .help-cta-btn{background:#25D366;color:#fff;border:none;border-radius:24px;padding:11px 22px;font-size:14.5px;
    font-weight:700;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;gap:8px;
    white-space:nowrap;box-shadow:0 3px 10px rgba(37,211,102,.35);transition:.15s}
  .help-cta-btn:hover{background:#1ebe5a}
  .help-cta-btn svg{width:19px;height:19px;fill:#fff}
  /* 🔴 DENGE TABANI KALKTI (Okan karari, 11 Agu): hap etiketi ARTIK HER genislikte
     kisadir ("Iletisime Gecin"); uzun on-ek GLOBAL gizlenir, mobil-only DEGIL. Masaustu
     CTA dengesini bu kisa etiket tutuyor — `.ikon-sepet` min-width tabani DEGIL (o
     kaldirildi). Olcen: cta-denge-kapisi.py CTA-A1-ORAN · mutant: cta-denge-mutasyon.py M12. */
  .wa-uzun{display:none}

  main{max-width:1100px;margin:0 auto;padding:28px 20px 50px}
  .crumbs{font-size:13px;color:var(--gray-text);margin-bottom:18px}
  .crumbs a{color:var(--navy-2);text-decoration:none}
  .crumbs a:hover{text-decoration:underline}
  .crumbs span{color:var(--gray-line);margin:0 6px}

  .detail{display:grid;grid-template-columns:1fr 1fr;gap:34px;align-items:start}
  .gallery{position:sticky;top:78px}
  .main-img{width:100%;aspect-ratio:1/1;object-fit:contain;background:var(--gray-card);
    border:1px solid var(--gray-line);border-radius:var(--radius);display:block}
  .thumbs{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
  .thumb{width:74px;height:74px;object-fit:cover;border-radius:8px;
    border:2px solid transparent;cursor:pointer;background:var(--gray-card)}
  .thumb:hover{border-color:var(--gray-line)}
  .thumb.active{border-color:var(--navy)}

  .cat{display:inline-block;background:var(--navy);color:#fff;font-size:11px;
    font-weight:600;letter-spacing:.5px;text-transform:uppercase;padding:4px 11px;
    border-radius:20px}
  .ozel-badge{display:inline-block;background:#f7b500;color:#12294d;font-size:11px;
    font-weight:800;letter-spacing:.3px;padding:4px 11px;border-radius:20px;margin-left:8px}
  h1{font-size:27px;font-weight:800;margin:14px 0 10px;color:var(--navy);line-height:1.25}
  .brands{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:14px}
  .brand-chip{background:var(--gray-card);border:1px solid var(--gray-line);
    border-radius:20px;padding:5px 12px;font-size:12.5px;font-weight:600;
    color:var(--navy);text-decoration:none}
  .brand-chip:hover{border-color:var(--navy-2)}
  .price{font-size:26px;font-weight:800;color:var(--navy);margin:4px 0 20px}
  .price.empty{font-size:15px;font-weight:600;color:var(--gray-text)}
  /* Ustu cizili ESKI FIYAT (opsiyonel `eski_fiyat` alani) — yalniz gosterim.
     [hidden]: secim birim fiyati eski fiyatin ustune cikarsa JS gizler (yaniltici
     indirim yasak); bazi CSS sifirlayicilari UA'nin [hidden] kuralini ezdigi icin
     kural BURADA da yazilir. */
  .fiyat-satiri{display:flex;align-items:baseline;flex-wrap:wrap;gap:9px}
  .eski-fiyat{font-size:17px;font-weight:700;color:var(--gray-text);
    text-decoration:line-through;text-decoration-thickness:2px}
  .eski-fiyat[hidden]{display:none}
  .opsiyonlar{margin:4px 0 20px;padding:14px 16px;background:var(--gray-card);
    border:1px solid var(--gray-line);border-radius:var(--radius)}
  .opsiyon-row{display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap}
  .opsiyon-row:last-of-type{margin-bottom:0}
  .opsiyon-row label{font-size:13px;font-weight:700;color:var(--navy);min-width:64px}
  .opsiyon-row select,.opsiyon-row input[type=text]{padding:8px 10px;border:1px solid var(--gray-line);
    border-radius:7px;font-size:14px;background:#fff;color:var(--navy)}
  .adet-kutu{display:inline-flex;align-items:center;border:1px solid var(--gray-line);
    border-radius:7px;background:#fff;overflow:hidden}
  .adet-btn{width:34px;height:36px;border:none;background:#fff;color:var(--navy);
    font-size:18px;font-weight:700;cursor:pointer;line-height:1}
  .adet-btn:hover{background:var(--gray-bg)}
  .adet-kutu input{width:52px;height:36px;border:none;border-left:1px solid var(--gray-line);
    border-right:1px solid var(--gray-line);text-align:center;font-size:14px;font-weight:700;
    color:var(--navy);background:#fff;-moz-appearance:textfield}
  .adet-kutu input::-webkit-outer-spin-button,
  .adet-kutu input::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}
  .opsiyon-fiyat{font-size:19px;font-weight:800;color:var(--navy);margin-top:10px}
  /* Eylem butonları (madde 7 + CTA dengesi 11 Ağu): ETİKETLİ "Sepete Ekle" (birincil)
     + yazısız WhatsApp ikonu (ikincil; kanal KALIR). Buton HER genişlikte METNE göre
     büzüşür: denge tabanı KALKTI, dengeyi kısa hap etiketi tutar (cta-denge-kapisi.py). */
  .eylem-ikonlar{display:inline-flex;gap:8px;margin-left:auto;flex-wrap:wrap;
    justify-content:flex-end}
  .ikon-btn{width:44px;height:44px;border:none;border-radius:9px;display:inline-flex;
    align-items:center;justify-content:center;cursor:pointer;transition:.15s;flex:none;
    text-decoration:none;padding:0}
  .ikon-btn svg{width:22px;height:22px;fill:#fff}
  .ikon-sepet{background:var(--navy);width:fit-content;height:56px;
    padding:0 14px;gap:9px;color:#fff;font-size:16px;font-weight:700;font-family:inherit}
  .ikon-sepet:hover{background:var(--navy-2)}
  .ikon-sepet.added{background:#178a44}
  .cart-label{white-space:nowrap}
  .ikon-wa{background:#25D366}
  .ikon-wa:hover{background:#1ebe5a}
  .konf-baslik{font-size:14px;font-weight:800;color:var(--navy);margin-bottom:12px}
  .konf-row label{min-width:130px}
  .konf-sayi{width:110px;padding:8px 10px;border:1px solid var(--gray-line);
    border-radius:7px;font-size:14px;background:#fff;color:var(--navy)}
  .konf-birim{font-size:12.5px;color:var(--gray-text);font-weight:600}
  .konf-kaydirici-satir{margin:-4px 0 10px;padding-left:140px}
  .konf-kaydirici{width:100%;max-width:260px;accent-color:var(--navy-2)}
  .konf-row select,.konf-row input[type=text]{max-width:220px}
  .konf-hata{flex-basis:100%;font-size:12px;font-weight:600;color:var(--red);min-height:0}
  .konf-row .hatali{border-color:var(--red);background:#fff5f5;outline:1px solid var(--red)}
  .konf-hacim{font-size:12.5px;color:var(--gray-text);margin-top:4px}
  .cart-btn.kilitli{opacity:.45;cursor:not-allowed}
  .desc{font-size:15px;color:#39434f;line-height:1.7;margin-bottom:26px}
  .desc-satir{display:block}
  .desc-bosluk{height:.85em}
  .order-btn{background:var(--red);color:#fff;border:none;border-radius:9px;
    padding:15px 22px;font-size:16px;font-weight:700;cursor:pointer;
    text-decoration:none;display:inline-flex;align-items:center;justify-content:center;
    gap:9px;transition:.15s;max-width:320px;width:100%}
  .order-btn:hover{background:var(--red-dark)}
  .order-btn svg{width:19px;height:19px;fill:#fff}
  .cart-btn{background:var(--navy);color:#fff;border:none;border-radius:9px;
    padding:15px 22px;font-size:16px;font-weight:700;cursor:pointer;
    display:inline-flex;align-items:center;justify-content:center;gap:9px;
    transition:.15s;max-width:320px;width:100%}
  .cart-btn:hover{background:var(--navy-2)}
  .cart-btn svg{width:19px;height:19px;fill:#fff}
  .cart-btn.added{background:#e8f6ee;color:#178a44}
  .cart-btn.added svg{fill:#178a44}
  .order-wa{background:#25D366;color:#fff;border:none;border-radius:9px;
    padding:13px 22px;font-size:15px;font-weight:700;cursor:pointer;
    text-decoration:none;display:inline-flex;align-items:center;justify-content:center;
    gap:9px;transition:.15s;max-width:320px;width:100%;margin-top:11px}
  .order-wa:hover{background:#1ebe5a}
  .order-wa svg{width:19px;height:19px;fill:#fff}
  /* Onerilenden farkli malzeme seciliyken cikan BILGI notu (engel degil). */
  .oneri-not{margin:8px 0 0;padding:8px 11px;border-radius:8px;background:#fff7e6;
    border:1px solid #f0d9a8;color:#6b4e11;font-size:12.5px;line-height:1.5}
  .oneri-not[hidden]{display:none}
  .malzeme-not{font-size:12.5px;color:var(--gray-text);line-height:1.5;margin:2px 0 2px}
  .malzeme-not a{color:#178a44;font-weight:600;text-decoration:underline}
  .cart-fab{position:fixed;right:18px;bottom:18px;z-index:60;background:#25a35a;color:#fff;
    border-radius:30px;padding:12px 20px;font-size:15px;font-weight:700;text-decoration:none;
    box-shadow:0 6px 18px rgba(0,0,0,.22);align-items:center;gap:8px;display:none}
  .cart-fab:hover{background:#1ebe5a}
  .cart-fab svg{width:19px;height:19px;fill:#fff}
  /* Yukarı çık oku — ana sayfadakiyle aynı dil; sepet FAB'ı (z:60) doluyken üstüne kayar */
  .top-btn{position:fixed;right:18px;bottom:18px;z-index:59;width:44px;height:44px;border:none;
    border-radius:50%;background:var(--navy);cursor:pointer;display:flex;align-items:center;
    justify-content:center;box-shadow:0 6px 18px rgba(0,0,0,.22);opacity:0;visibility:hidden;
    transform:translateY(8px);transition:opacity .2s,transform .2s,visibility .2s,bottom .2s}
  .top-btn.show{opacity:1;visibility:visible;transform:none}
  .top-btn:hover{background:var(--navy-2)}
  .top-btn svg{width:21px;height:21px;fill:#fff}
  body.fab-var .top-btn{bottom:78px}
  .note{font-size:12.5px;color:var(--gray-text);margin-top:12px}

  /* Malzeme bolumu: sitede satilan malzeme cipleri + tavsiye rozeti + aciklama balonu.
     Balon, cip satirinin ALTINDA konteyner genisliginde acilir (kenar ciplerinde
     ekran disina tasmaz — mobil guvenli). Masaustunde hover, mobilde dokunma
     (.acik sinifi, sayfa scriptindeki toggle) ile acilir; title= mobilde calismadigi
     icin bilerek CSS balon kullanildi. */
  .malzeme-blok{margin:4px 0 22px}
  .malzeme-baslik{font-size:13px;font-weight:700;letter-spacing:.4px;
    text-transform:uppercase;color:var(--gray-text);margin-bottom:8px}
  .fil-cipler{display:flex;flex-wrap:wrap;gap:8px;position:relative}
  .fil-cip{display:flex;flex-direction:column;align-items:flex-start;gap:1px;
    background:var(--gray-card);border:1px solid var(--gray-line);border-radius:9px;
    padding:7px 11px;cursor:pointer;font-family:inherit;text-align:left;transition:.15s}
  .fil-cip:hover{border-color:var(--navy-2)}
  .fil-cip.tavsiyeli{border-color:var(--navy);box-shadow:0 0 0 1px var(--navy)}
  .fil-isi{font-size:10.5px;color:var(--gray-text);font-weight:600;letter-spacing:.2px}
  .fil-ad{font-size:13.5px;font-weight:800;color:var(--navy)}
  .fil-etiket{font-size:10.5px;color:var(--gray-text)}
  /* Cipin KENDI tutari: taban secenegin (PLA) tutari sayfada GORUNUR kalsin. */
  .fil-tutar{font-size:11.5px;font-weight:700;color:var(--navy);margin-top:1px}
  .fil-rozet{background:var(--navy);color:#fff;font-size:9.5px;font-weight:800;
    letter-spacing:.4px;text-transform:uppercase;border-radius:8px;padding:2px 7px;margin-top:4px}
  .fil-rozet-not{background:#f7b500;color:#12294d;text-transform:none;letter-spacing:.1px}
  .fil-balon{display:none;position:absolute;left:0;right:0;top:calc(100% + 9px);z-index:45;
    background:var(--navy);color:#e7edf8;font-size:13px;line-height:1.6;font-weight:400;
    border-radius:9px;padding:12px 14px;box-shadow:0 8px 24px rgba(13,30,58,.35);
    text-align:left;cursor:default}
  .fil-balon strong{color:#fff}
  .fil-cip:hover .fil-balon,.fil-cip:focus-visible .fil-balon,
  .fil-cip.acik .fil-balon{display:block}
  .fil-not{font-size:12.5px;color:var(--gray-text);margin-top:9px}
  .malzeme-link{display:inline-block;margin-top:9px;font-size:12.5px;color:var(--navy-2)}
  /* Secili malzeme karti: DOLGU (lacivert zemin) — tavsiyeli kartin ince cercevesinden
     acikca ayrilir; "Tavsiyemiz" rozeti sadece bilgidir, secim yapmaz. */
  .fil-cip.secili{background:var(--navy);border-color:var(--navy);
    box-shadow:0 2px 10px rgba(18,41,77,.28)}
  .fil-cip.secili .fil-ad{color:#fff}
  .fil-cip.secili .fil-isi,.fil-cip.secili .fil-etiket{color:#cdd8ea}
  .fil-cip.secili .fil-tutar{color:#fff}
  .fil-cip.secili .fil-rozet{background:#fff;color:var(--navy)}

  /* Renk BUTONLARI (dropdown yerine) — kucuk renk yuvarlagi + ad; Diger = gokkusagi gradyan. */
  .opsiyon-renk{align-items:flex-start}
  .renk-butonlar{display:flex;flex-wrap:wrap;gap:8px}
  .renk-btn{display:inline-flex;align-items:center;gap:7px;background:var(--gray-card);
    border:1px solid var(--gray-line);border-radius:9px;padding:7px 12px;cursor:pointer;
    font-family:inherit;font-size:13.5px;font-weight:700;color:var(--navy);transition:.15s}
  .renk-btn:hover{border-color:var(--navy-2)}
  .renk-btn.secili{background:var(--navy);border-color:var(--navy);color:#fff;
    box-shadow:0 2px 10px rgba(18,41,77,.28)}
  .renk-yuvar{width:16px;height:16px;border-radius:50%;display:inline-block;flex:none}
  .renk-yuvar-gokkusagi{background:conic-gradient(from 0deg,#ff004c,#ff8a00,#ffe600,
    #00d158,#00b3ff,#7a5cff,#ff004c)}
  .renk-ozel{padding:8px 10px;border:1px solid var(--gray-line);border-radius:7px;
    font-size:14px;background:#fff;color:var(--navy);margin:6px 0 0 74px;max-width:260px}

  /* Secimsiz "Sepete Ekle" denemesi: eksik secim grubu titrer + cerceveleri kirmizi olur
     (gecici, ~0.4sn). Saf CSS/JS — malzeme kartlari, renk butonlari, renk metin kutusu ortak. */
  @keyframes pruvoTitre{0%,100%{transform:translateX(0)}
    15%,45%,75%{transform:translateX(-6px)}30%,60%,90%{transform:translateX(6px)}}
  .titre{animation:pruvoTitre .4s ease-in-out}
  .hata-vurgu .fil-cip,.hata-vurgu .renk-btn{border-color:var(--red);box-shadow:0 0 0 1px var(--red)}
  .renk-ozel.hata{border-color:var(--red);box-shadow:0 0 0 1px var(--red)}

  .related{max-width:1100px;margin:0 auto;padding:0 20px 60px}
  .related h2{font-size:19px;font-weight:700;margin-bottom:16px}
  .rel-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:16px}
  .rel-card{background:var(--gray-card);border:1px solid var(--gray-line);
    border-radius:var(--radius);overflow:hidden;text-decoration:none;color:var(--navy);
    display:flex;flex-direction:column;box-shadow:var(--shadow);transition:transform .15s,box-shadow .15s}
  .rel-card:hover{transform:translateY(-3px);box-shadow:0 8px 22px rgba(18,41,77,.14)}
  .rel-img{width:100%;aspect-ratio:4/3;object-fit:cover;background:#dbe2ec;display:block}
  .rel-body{padding:12px 13px 14px}
  .rel-title{font-size:14px;font-weight:700;line-height:1.35;margin-bottom:6px}
  .rel-price{font-size:14px;font-weight:800;color:var(--navy)}

  footer{background:var(--navy-dark);color:#aeb9cd;text-align:center;padding:22px 20px;
    font-size:13.5px;letter-spacing:.5px}
  .foot-nav{margin-top:8px}
  .foot-nav a{color:#c7d2e4;text-decoration:none;margin:0 8px}
  .foot-nav a:hover{color:#fff;text-decoration:underline}
  .attribution{margin-top:12px;font-size:11px;letter-spacing:.3px;color:#7d8aa3}
  .attribution a{color:#93a1bd;text-decoration:underline}

  @media (max-width:760px){
    .detail{grid-template-columns:1fr;gap:22px}
    .gallery{position:static}
    h1{font-size:22px}.price{font-size:22px}
    .order-btn,.cart-btn{max-width:none}
    /* 🔴 STICKY BANT PAYI (11 Ağu): 135px=%16,6 -> 61px=%7,5; kanal KALIR, dokunma 44px. */
    .help-cta-inner{padding:8px 14px;gap:10px;flex-wrap:nowrap;
      justify-content:space-between;text-align:left}
    .help-cta-text{font-size:11px;line-height:1.3;display:-webkit-box;
      -webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
    .help-cta-btn{padding:11px 14px;font-size:13px;gap:6px;min-height:44px;flex:none}
    .eylem-ikonlar{flex-wrap:nowrap;width:100%}
    /* `flex:1 1 auto` butonu 249 px'e şişiriyordu; `flex:none` (=0 0 auto) onu durdurur.
       Mobil min-width sıfırlaması KALKTI: sıfırlayacağı masaüstü denge tabanı artık YOK
       ve flex:none zaten küçültmediği için ölçüye etkisi kalmamıştı — duran bir
       sıfırlama "hâlâ bir taban var" izlenimi verip ikiz tanım riski doğuruyordu. */
    .ikon-sepet{flex:none}
  }
"""
PAGE_CSS += CONTENT_CSS


# ------------------------------------------------------------------ yardımcılar
def esc(s):
    return html.escape(s or "", quote=True)


# ---------------------------------------------------------------------------
# OZEL URETIM TESLIM BEYANI (10 Agu) — 23.968 `tur`suz urunun sayfasina basilan
# tek satirlik beyan.
#
# 🔴 NEDEN VAR: ziyaretci "ne zaman elime gecer" bilmeden odeme karari veriyordu.
# Sure sitede 69 yerde yazili (SSS · teslimat-iade · mesafeli-satis m.4) ama URUN
# SAYFASINDA hic yoktu; hazir/stok dali (fiziksel) ise 1 Agu'dan beri kendi sinif
# beyanini basiyor. Yani ozel uretim kolu BEYANSIZDI.
#
# 🔴 CUMLE IKINCI KEZ YAZILMAZ: metin secenekler.js BEYAN["SAYFA_OZEL"]'den gelir
# (ayni sozlugu siparis e-postasi ve odeme ekrani da okur). Ikiz tanim sessizce
# ayrisir; _js_sabiti anahtari bulamazsa build FAIL-CLOSED duser.
# Nobet DAVRANISSALDIR (kaynak taramasi degil): cayma-beyani-kapisi.py E5 BEYAN
# degerini calisma zamaninda degistirip CIKTININ da degistigini olcer — kacis
# dizileriyle ("Ö...") yazilmis bir ikiz de bu olcumu GECEMEZ.
#
# 🔴 TETIKLEYICI: cumle "siparisiniz onaylandiktan sonra" der, "olcu onayindan
# sonra" DEMEZ. Ozel uretim sinifinin %99,84'u (23.929/23.968) sabit tasarim
# katalog parcasidir; alicidan olcu girdisi ALINMAZ ve odeme akisinda "olcu
# onayi" asamasi YOKTUR -> var olmayan bir olaya baglanan taahhudun saati hic
# baslamaz. Ayrica "olcuye ozel" damgasi m.15 cayma istisnasinin anahtar
# ifadesidir; sabit tasarim urune urun bazinda basilmaz. Tetikleyici, siparis
# onay e-postasinin dili (SATIR_OZEL / EPOSTA_ODENDI_OZEL) ile AYNI SINIFTA
# olmak zorundadir — kapi B7 celiskiyi KIRMIZI yakar.
#
# ⚠️ BICIM SATIR ICI: PAYLASILAN PAGE_CSS'e kural EKLENMEZ — ortak stil HER urun
# sayfasina basildigi icin oraya tek satir eklemek 24.911 sayfanin BAYTINI
# degistirirdi (regresyon butcesi sha256 ile olculuyor). Kalip, fiziksel daldaki
# `.sinif-beyan` blogunun BIREBIR esidir.
#
# 🔴 NEREYE BASILIR — TEK NOKTA, `{malzeme}` YUVASININ HEMEN ARDI (sablonda
# `{malzeme}{ozel_beyan}`). Uc gerekce, ucu de olculdu:
#   1. SINIF KAPISI AYNI: `malzeme` yuvasi da "fiziksel ise BOS" kuralinda
#      (bkz. render_product `malzeme=("" if fiziksel else filament_html(...))`).
#      Beyan ayni kosula baglaninca "ozel uretim sayfasi = beyan VAR" invaryanti
#      TEK satirda yasar; opsiyon zincirinin BES dalina dagitilsaydi yarin acilan
#      altinci dal SESSIZCE beyansiz dogardi.
#   2. HAZIR/STOK SAYFASI BAYT-BIREBIR: fiziksel dalda yuva BOS dizeye cozulur,
#      sablonda cevresinde bosluk YOKTUR -> 943 sayfanin bayti degismez.
#   3. NOBET KABLOLANABILIR: tools/varlik-test.py gorunur-metin ekseni GRANUL
#      (ESKI -> YENI) beyan ister; malzeme blogunun kuyrugu ("Malzeme Rehberi")
#      BUTUN ozel uretim sayfalarinda AYNI ve fiziksel sayfada YOK — yani tek bir
#      sinif-hizali capa yetiyor. Opsiyon panelinin icine basilsaydi capa sayfa
#      sinifina gore degisir, beyan tablosu urun katalogu degistikce BAYATLARDI.
OZEL_TESLIM_BEYAN_HTML = (
    '<div class="sinif-beyan" id="sinifBeyan" style="margin-top:10px;font-size:13px;'
    'line-height:1.5;color:var(--gray-text)">%s</div>') % esc(BEYAN["SAYFA_OZEL"])


# Sorgu dizesinde HAM birakilamayacak karakterler (bosluk basta olmak uzere: ayirici ya da
# yapilandirilmis veride GECERSIZ). BILEREK DAR: Turkce harfler (Bahçe, Jeneratör) ve
# "Oyun/Hobi"deki egik cizgi HAM birakilir -> aylardir yayinda olan 13 kategorinin URL'leri
# BAYT-OZDES kalir (konfigur-test.py'nin merge-base bayt-esitlik nobetcisi bunu olcuyor).
_KATEGORI_KACIS = {"%": "%25", " ": "%20", "#": "%23", "&": "%26", "?": "%3F",
                   "+": "%2B", '"': "%22", "<": "%3C", ">": "%3E"}


def kategori_url(kategori):
    """Ana sayfa kategori derin linki: /?kategori=<ad>, gecersiz karakterler kodlu.

    23 Tem'e kadar butun kategori adlari tek kelimeydi, bu yuzden kategori URL'e HAM
    gomuluyordu. Iki kelimeli "Skan Art" ile bu, JSON-LD BreadcrumbList item'inde ve
    <a href>'te "?kategori=Skan Art" gibi HAM BOSLUKLU (yapilandirilmis veride GECERSIZ)
    URL uretir hale geldi. Kacis artik TEK yerden gecer.
    index.html applyUrlParams URLSearchParams ile okur -> %20 sorunsuz cozulur.
    Donen deger KOKE GORECE yoldur ("/?kategori=..."); mutlak gerekince SITE ile birlestir."""
    ad = kategori or ""
    return "/?kategori=" + "".join(_KATEGORI_KACIS.get(ch, ch) for ch in ad)


def meta_desc(p):
    """Ürün açıklamasından ~160 karakterlik temiz meta açıklama üret."""
    txt = re.sub(r"\s+", " ", (p.get("aciklama") or "")).strip()
    if len(txt) > 158:
        txt = txt[:158].rsplit(" ", 1)[0] + "…"
    return txt


def price_number(fiyat):
    """'1250 TL' -> '1250' (rakam yoksa None)."""
    if not fiyat:
        return None
    digits = re.sub(r"[^0-9]", "", fiyat)
    return digits or None


def marka_temiz(txt):
    """Feed metni marka kurali: '3D baski/printed' -> 'ozel tasarim uretim' (hedefli)."""
    s = txt or ""
    for pat, rep in _MARKA_SUB:
        s = pat.sub(rep, s)
    return s


def feed_price(fiyat):
    """Feed icin net sayisal TL fiyati: '650 TL'->'650', '1.250 TL'->'1250',
    '350 TL (12 cm)'->'350'. Sayisal fiyat yoksa (parametrik/'olcuye ozel') None.

    Tip sozlesmesi arama.KATALOG_ALAN_TIPLERI'dir. Sayi gibi bozuk bir katalog degeri
    burada ikinci, daha genis bir kabul sinifi acmaz; sayfa uretimini cokertmeden None
    doner. Katalog kapisi ayni kanonik sebeple yayini zaten fail-closed durdurur.
    """
    if arama.katalog_alan_tip_sebebi("fiyat", fiyat) is not None:
        return None
    if not fiyat:
        return None
    m = re.search(r"(\d[\d.]*)\s*(?:tl|try|₺)", fiyat, re.I) or re.search(r"(\d[\d.]*)", fiyat)
    if not m:
        return None
    raw = m.group(1).replace(".", "")          # Turkce binlik ayraci ('1.250' -> '1250')
    return raw if raw.isdigit() and int(raw) > 0 else None


# ----------------------------------------------------- ESKI FIYAT (ustu cizili gosterim)
# OPSIYONEL alan `eski_fiyat` ("1.200 TL") — YALNIZ GOSTERIMDIR.
#
# 🔴 PARA YOLUNA SIFIR ETKI: sepet/konfigur/iyzico/D1/feed/JSON-LD fiyat hesabi bu alani
#    OKUMAZ. Tahsil edilen tutar `fiyat`tan (secenekler.js fiyatSayisi / konfigur capalari)
#    turer; burada uretilen tek sey ekranda gorunen bir <s> etiketidir.
#
# FAIL-CLOSED (yanlis gosterim = musteriye YANILTICI indirim = sessiz ticari/hukuki hata):
#   asagidaki KOSULLARIN HEPSI saglanmazsa HIC gosterilmez — "0 TL" YOK, ham dize YOK,
#   NaN YOK. Sessiz yesil yerine sessiz YOKLUK secilir.
#     1. urun parametrik DEGIL     (sari seri `fiyat` BOS — kiyaslanacak guncel fiyat yok)
#     2. urun konfigur'lu DEGIL    (fiyat boya/malzemeye gore CANLI degisir; sabit bir eski
#                                   fiyat orada yaniltici olur — /konfigur.js'e DOKUNULMAZ)
#     3. `fiyat` ayristirilabilir  (TL/TRY/₺ tasiyan sayi)
#     4. `eski_fiyat` TAM olarak "<sayi> <para birimi>" kalibina uyar (bastan sona; ek
#        metin/isaret KABUL EDILMEZ -> gosterilen dize yapisal olarak zararsizdir)
#     5. para birimi AYNI: her iki taraf da TL/TRY/₺. Baska bir birim (USD/EUR/$) bu
#        kalibi hic eslemez -> ayristirilamaz sayilir -> gosterilmez.
#     6. eski_fiyat > fiyat        (esit/kucuk = indirim DEGIL -> gosterilmez)
#
# SAYI KALIBI: Turkce binlik nokta + virgullu kurus. "1.250" = 1250 · "1.250,50" = 1250,50.
# BELIRSIZ bicim ("1.25", "1.2.3") KABUL EDILMEZ (nokta ondalik mi binlik mi belli degil).
# Arama kalibindaki `(?:^|[^\d.,])` oneki, "1.2.3 TL" gibi bozuk dizede sondaki "3"un
# 3 TL diye okunmasini engeller (lookbehind YOK: index.html'deki ayni kalip eski
# Safari'lerde de kosmali, oradan KOPYALANMAZ — ikisi tools/eski-fiyat-test.py'de AYNI
# vaka tablosuyla kilitlenir).
_PARA_BIRIMI_RE = r"(?:TL|TRY|₺)"
_PARA_SAYI_RE = r"(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{1,2})?"
_ESKI_FIYAT_TAM_RE = re.compile(r"^\s*(" + _PARA_SAYI_RE + r")\s*" + _PARA_BIRIMI_RE + r"\s*$",
                                re.I)
_FIYAT_ARA_RE = re.compile(r"(?:^|[^\d.,])(" + _PARA_SAYI_RE + r")\s*" + _PARA_BIRIMI_RE, re.I)


def para_kurus(sayi):
    """'1.250' -> 125000 · '1.250,50' -> 125050 (kalibi ONCEDEN dogrulanmis sayi dizesi)."""
    tam, _, kusurat = sayi.partition(",")
    kusurat = (kusurat + "00")[:2] if kusurat else "00"
    return int(tam.replace(".", "")) * 100 + int(kusurat)


def fiyat_kurus_gevsek(metin):
    """`fiyat` alanindan kurus. Alan ek metin tasiyabilir ('350 TL (12 cm)') -> ARAMA.
    Sayi/para birimi bulunamazsa None (fail-closed)."""
    m = _FIYAT_ARA_RE.search(metin or "")
    return para_kurus(m.group(1)) if m else None


def eski_fiyat_gosterim(p):
    """Urun icin ustu cizili eski fiyat: (metin, kurus) ya da (None, None).

    Donen metin, TAM kalibi (sayi + TL/TRY/₺) geceni oldugu icin yapisal olarak
    zararsizdir; yine de basildigi yerde esc()/textContent ile kacisi UYGULANIR."""
    if not isinstance(p, dict):
        return (None, None)
    if p.get("parametrik") or p.get("konfigur"):
        return (None, None)
    ham = p.get("eski_fiyat")
    if not isinstance(ham, str):
        return (None, None)
    ham = ham.strip()
    m = _ESKI_FIYAT_TAM_RE.match(ham)
    if not m:
        return (None, None)
    guncel = p.get("fiyat")
    if not isinstance(guncel, str) or not guncel.strip():
        return (None, None)
    guncel_kurus = fiyat_kurus_gevsek(guncel)
    if guncel_kurus is None:
        return (None, None)
    eski_kurus = para_kurus(m.group(1))
    if eski_kurus <= guncel_kurus:
        return (None, None)
    return (ham, eski_kurus)


def eski_fiyat_html(p):
    """Ustu cizili <s> etiketi (yoksa BOS dize -> sayfa bugunku gibi basilir)."""
    metin, kurus = eski_fiyat_gosterim(p)
    if not metin:
        return ""
    # 🔴 ON-SECIM ILAN TUTARINI YUKARI TASIYORSA CIZILI FIYAT BASILMAZ: 1.200 TL cizili
    # dururken 1.275 TL ilan etmek YANILTICI INDIRIMDIR. Istemci ayni kiyasi render'da
    # yapip kutuyu gizler; burada JS ONCESI de gorunmemesi icin sunucuda elenir (ayni
    # kiyas, ayni sayi: ilan_kurus). Bayrak kapaliyken ilan tutari liste tutaridir ->
    # kosul bugunku davranisla ayni (bayt-esit).
    if ONERI_ONSECIM_ACIK:
        _ilan = ilan_kurus(p)
        if _ilan is not None and kurus <= _ilan:
            return ""
    return ('<s class="eski-fiyat" id="eskiFiyat" data-kurus="%d">%s</s>'
            % (kurus, esc(metin)))


def fiyat_satiri(eski_html, ic_html):
    """Eski fiyat VARSA guncel fiyatla yan yana tek satir; YOKSA fiyat blogu bugunku gibi
    TEK BASINA basilir (eski_fiyat tasimayan sayfalar bayt-esit kalir)."""
    if not eski_html:
        return ic_html
    return '<div class="fiyat-satiri">%s%s</div>' % (eski_html, ic_html)


def feed_id(pid):
    """Google Merchant 'id'/'mpn' 50 karakter siniri: uzun urun-id'sini kisalt.
    <=50 ise AYNEN dondur (kisa id'ler DEGISMEZ, churn yok). Uzunsa ilk 41 karakter
    + '-' + sha1'in ilk 8 hex hanesi = TAM 50 karakter; benzersiz, deterministik,
    KALICI. NOT: bu yalniz feed kimligidir; product_url/link TAM pid ile kalir."""
    if len(pid) <= 50:
        return pid
    return pid[:41] + "-" + hashlib.sha1(pid.encode("utf-8")).hexdigest()[:8]


def feed_img(url):
    """Feed gorsel URL'ine kararli cache-bust damgasi ekle: '...jpg' -> '...jpg?v=1'.
    URL'de zaten sorgu varsa '&' ile eklenir ('??' olusmaz). Ayni damga zaten varsa
    tekrar eklenmez (idempotent). Damga SABIT -> ayni girdi ayni cikti (build'ler
    byte-esit; katalog gereksiz yere yeniden cekmez)."""
    u = (url or "").strip()
    if not u:
        return u
    damga = "v=" + FEED_IMG_SURUM
    if damga in (u.split("?", 1)[1] if "?" in u else "").split("&"):
        return u
    return u + ("&" if "?" in u else "?") + damga


def images_of(p):
    imgs = p.get("gorseller") or []
    return [i for i in imgs if i]


# --- GORSELSIZ URUN: YER TUTUCU -------------------------------------------------------
# NEDEN VAR (olculdu, 1 Agu — canli 404): gorseli HIC olmayan urunun sayfasi
# `SITE + "/favicon.png"` kapagiyla uretiliyordu. O dosya depoda YOK ve canlida
# `https://pruvo3d.com/favicon.png` -> HTTP 404 (olculdu: curl, 404/text-html). Yani
# musteri urun sayfasinda 800x800'luk bir KIRIK GORSEL ikonu goruyordu; ayni 404 URL
# og:image / twitter:image / JSON-LD `image` alanlarina da basiliyordu (paylasim onizlemesi
# bos, Google icin "image_link gecersiz"). Hicbir kapi kirmizi yakmiyordu — hatanin
# TAMAMI sessizdi, yalniz musteri ve crawler goruyordu.
#
# COZUM: KIRIK GORSEL yerine KASITLI YER TUTUCU. Ag istegi YOK (data: URI) -> 404
# imkansiz. Sekil ana sayfadaki kart yer tutucusuyla AYNI: index.html `placeholder(kat)`
# zaten gorselsiz/bozuk kartta bu SVG'yi basiyor, yani ziyaretciye yeni bir gorsel dil
# uydurmuyoruz — katalogda gordugu ayni kutu urun sayfasinda da cikiyor.
#
# 🔴 IKIZ TANIM: bu SVG index.html'deki `placeholder()` ile BIREBIR ayni dizeyi uretmek
# ZORUNDA. Ayrisirsa iki yuzey sessizce farkli gorunur ([[ikiz-tanim-sessiz-ayrisma]]).
# Drift nobetcisi: tools/gorselsiz-render-kapisi.py — index.html'in GERCEK fonksiyonunu
# node'da kosturup bu fonksiyonun ciktisiyla BAYT karsilastirir.
#
# ⚠️ data: URI YALNIZ <img src> icindir. og:image / JSON-LD `image` MUTLAK URL bekler;
# oralara yer tutucu BASILMAZ, alan HIC yazilmaz (bkz. render_product). "Yanlis gorsel"
# yerine "gorsel yok" beyani -> fail-closed.
PLACEHOLDER_W = "400"
PLACEHOLDER_H = "300"


def placeholder_svg(kat):
    """index.html `placeholder(txt)` ile BAYT-AYNI SVG dizesi."""
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%s" height="%s">'
            '<rect width="%s" height="%s" fill="#1c3a6b"/>'
            '<text x="50%%" y="50%%" fill="#9db1d4" font-family="Arial" font-size="26" '
            'font-weight="bold" text-anchor="middle" dominant-baseline="middle">PRUVO · %s'
            '</text></svg>'
            % (PLACEHOLDER_W, PLACEHOLDER_H, PLACEHOLDER_W, PLACEHOLDER_H, kat or "Ürün"))


def placeholder_data_uri(kat):
    """index.html `phData(kat)` ile BAYT-AYNI data: URI.

    Kacis kumesi encodeURIComponent ile ayni: A-Za-z0-9 ve -_.!~*'() kacilmaz. Python'un
    varsayilan quote()'u (safe='/') '/' karakterini birakirdi -> "Oyun/Hobi" kategorisinde
    iki taraf ayrisirdi; safe ACIKCA verilir."""
    from urllib.parse import quote
    return "data:image/svg+xml;utf8," + quote(placeholder_svg(kat), safe="-_.!~*'()")


def wa_href(p, url):
    msg = u"Merhaba, şu ürünle ilgileniyorum: " + (p.get("baslik") or "") + "\n" + url
    from urllib.parse import quote
    return "https://wa.me/" + WHATSAPP + "?text=" + quote(msg)


def help_cta_href(p, url):
    """ORGANİK "Bizimle İletişime Geçin" (help-cta-btn) butonunun wa.me href'i.

    ⚠️ BU BUTONUN NİYETİ: kendi metni "Aradığınız parçayı bulamadınız mı? Bizimle
    iletişime geçin, üretelim!" -> basan müşteri SAYFADAKİ ürünü İSTEMİYOR, BULAMADIĞI
    BAŞKA bir parçayı arıyor. Prefill bu yüzden "bu ürünü istiyorum" DEMEZ; yoksa Ege
    yanlış niyetle o ürün için fiyat/malzeme akışı başlatır (bağlamsızdan beter).
    Eskiden prefill BAĞLAM-KÖRdü (sabit metin — hangi sayfadan gelindiği belirsiz).
    Çözüm: sayfa bağlamını (ad + canonical URL) VER, niyeti ("aradığımı bulamadım,
    üretebilir misiniz?") KORU.

    Kodlama sözleşmesi wa_href ile BİREBİR AYNI: metin quote() ile TEK KEZ
    percent-kodlanır (boşluk=%20, Türkçe ç/ğ/ı/ö/ş/ü UTF-8 %XX), döndürülen URL
    format() içinde esc() ile HTML-escape edilir (quote çıktısında &/<>/" olmadığı
    için esc no-op) — double-encode YOK. Numara = WHATSAPP sabiti (arama 4005 ASLA).
    REF/atıf butonu (orderAlt) AYRIDIR; buraya dokunmak onu etkilemez."""
    from urllib.parse import quote
    msg = (u"Merhaba, şu sayfadaydım: " + (p.get("baslik") or "")
           + "\n" + url + "\n"
           + u"Aradığım parçayı bulamadım, üretebilir misiniz?")
    return "https://wa.me/" + WHATSAPP + "?text=" + quote(msg)


def product_url(pid):
    return SITE + "/urun/" + pid + "/"


def attribution_html(p):
    """CC lisanslı kaynaklar için tasarımcı + lisans atıfı (küçük, sayfa altı).
    Format: 'Design by <Ad>, licensed under <CC BY 4.0>.'  (isim linksiz,
    lisans türü creativecommons linkine bağlı)."""
    lis = p.get("lisans")
    if not lis:
        return ""
    tasarimci = (lis.get("tasarimci") or "").strip()
    tur = (lis.get("tur") or "").strip()
    url = (lis.get("url") or CC_URLS.get(tur) or "").strip()
    if not tur:
        return ""
    if url:
        lic = ('<a href="%s" target="_blank" rel="license noopener nofollow">%s</a>'
               % (esc(url), esc(tur)))
    else:
        lic = esc(tur)
    if not tasarimci:
        # Tasarimci hesabi silinmis/anonim olabilir; CC atifi lisans linkiyle yine verilir.
        return '<div class="attribution">Licensed under %s.</div>' % lic
    return ('<div class="attribution">Design by %s, licensed under %s.</div>'
            % (esc(tasarimci), lic))


# ------------------------------------------------------------------ malzeme (filament) bölümü
def _fil_cipleri(p, secili=None):
    """Sitede satilan filament CIPLERI (buton listesi). TEK GOVDE: hem sayfa govdesindeki
    "Malzeme" bolumu (filament_html) hem panel icindeki SECICI (panel_malzeme_html) bu
    fonksiyondan uretilir -> iki yerde iki farkli cip kalibi DOGMAZ.

    secili=None cagrisi 11 Agu oncesi ciktiyla BAYT-BAYT aynidir (geri uyumluluk)."""
    ref = filament_ortak.referans()
    tavs = {
        t["ad"]: t["rozet"]
        for t in filament_ortak.tavsiyeler(p.get("kategori"), p.get("tavsiyeFilament"))}
    cips = []
    for f in ref["filamentler"]:
        if not f.get("site"):
            continue
        # 🔴 MALZEME x KATEGORI KAPISI (14 Agu): haric kategoride cip HIC BASILMAZ.
        # Tablo secenekler.js'te (tek kaynak); Worker AYNI tabloyu zorlar.
        if not malzeme_kategori_uygun_mu(f["ad"], p.get("kategori")):
            continue
        rozet = tavs.get(f["ad"], "")
        rozet_html = ""
        if rozet:
            rcls = "fil-rozet" if rozet == "Tavsiyemiz" else "fil-rozet fil-rozet-not"
            rozet_html = '<span class="%s">%s</span>' % (rcls, esc(rozet))
        cls = " tavsiyeli" if rozet else ""
        # Onden secili cip: gorsel DOLGU (.secili) + ekran okuyucu icin aria-pressed.
        ek = ""
        if secili is not None and f["ad"] == secili:
            cls += " secili"
            ek = ' aria-pressed="true"'
        # 🔴 CIP TUTARI (azaltici — Okan karari, 11 Agu): besleme/markup BASLANGIC tabanini,
        # sayfa ise ONERILEN malzemenin tutarini beyan ediyor. Bag kopmasin diye her cip
        # KENDI tutarini `data-kurus` ile tasir (makine okur); GORUNUR etiketi sayfa JS'i
        # bu attribute'tan yazar -> taban secenegin tutari sayfadan hem cikarilabilir hem
        # okunabilir kalir. Sayi TEK turetme noktasindan gelir (cip_kurus -> _birim_kurus);
        # ikinci formul YOK.
        # Olcuye ozel/yapilandiricili urunde None -> alan ve metin HIC basilmaz (sabit sayi
        # basmak orada yaniltici olurdu) ve cikti bugunkuyle bayt-esit kalir.
        birim = cip_kurus(p, f["ad"])
        tutar_attr = "" if birim is None else ' data-kurus="%d"' % birim
        cips.append(
            '<button type="button" class="fil-cip%s" data-malzeme="%s"%s aria-expanded="false"%s>'
            '<span class="fil-isi">%s</span>'
            '<span class="fil-ad">%s</span>'
            '<span class="fil-etiket">%s</span>'
            '%s'
            '<span class="fil-balon" role="tooltip"><strong>%s — %s</strong><br>%s</span>'
            '</button>'
            % (cls, esc(f["ad"]), tutar_attr, ek, esc(f["isiDayanimi"]), esc(f["ad"]),
               esc(f["kisaEtiket"]), rozet_html,
               esc(f.get("uzunAd") or f["ad"]), esc(f["kisaEtiket"]), esc(f["uzun"])))
    return cips


def panel_malzeme_html(p):
    """🔴 SEPETE EKLE'NIN USTUNDEKI malzeme secicisi (11 Agu, sessiz sepet arizasi).

    ONCE: zorunlu malzeme secimi butonun ~168 px ALTINDAYDI ve onden secili DEGILDI ->
    kullanici "Sepete Ekle"ye basiyor, secim eksik oldugu icin ekleme SESSIZCE dusuyordu
    (yalniz 500 ms titreme; sepet bos kaliyordu). Secici artik butondan ONCE, opsiyon
    panelinin ICINDE basilir ve VARSAYILAN_MALZEME onden secilidir.

    Fiyat mantigina DOKUNULMAZ: varsayilan secenekler.js bosSatir()'dan turer ve farki
    %0'dir (yukaridaki fail-closed kontrole bak) -> satira yazilan tutar, hicbir secim
    yapilmadan eklenen bugunku bosSatir tutarinin ta kendisidir.

    Govdenin ALTINDAKI "Malzeme" bolumu bu sayfalarda kartlar_gizli=True ile basilir:
    muhendislik-malzeme WhatsApp notu + Malzeme Rehberi linki kalir, KART ikinci kez
    basilmaz (cift-UI olurdu)."""
    # ETIKET "Malzeme seçimi" (asagidaki bilgi bolumunun basligi "Malzeme"ydi): bu satir
    # bir SECICIDIR, asagisi bilgi bolumuydu — iki ayri sey, iki ayri etiket. Fark ayrica
    # tools/varlik-test.py'nin gorunur-metin beyanini GRANUL tutar (kartlarin ESKI yerden
    # kalkip YENI yere gitmesi iki DAR giriste ifade edilebilir; ayni etiket kullanilsaydi
    # beyan iki konumu birbirinden ayirt edemezdi). Etiketi "Malzeme"ye geri cevirmeden
    # once o beyanlara bak.
    # 🔴 ONERI NOTU (spec kabul ekseni 4): onerilenden BASKA malzeme seciliyken GORUNUR,
    # onerilen seciliyken GORUNMEZ. ENGEL DEGIL, BILGILENDIRME — musteri bilerek taban
    # malzemeye ihtiyac duyabilir (Okan). Kutu YALNIZ onerisi TURETILEBILEN uründe
    # basilir; turetilemeyende (bkz. taninmayan kolu) HIC basilmaz -> o sayfalar
    # bugunkuyle bayt-esit kalir ve "oneri var" diye YALAN soylenmez.
    #
    # 🔴 GOVDE NEDEN BOS: kutunun metni de, ciplerin tutar etiketi de URUNE GORE DEGISEN
    # metinlerdir. Uretilen HTML'e urun basina degisen GORUNUR METIN koymak, sayfa
    # icerigini bayt duzeyinde nobetleyen kapinin (tools/varlik-test.py eksen 1) beyan
    # yuzeyiyle ifade EDILEMEZ: o yuzey SABIT dizeler alir, sayfa basina degisen sayilari
    # ancak "her sayfa icin ayri beyan" ile karsilardi ve o da nobetcinin susturma kolunu
    # gevsetirdi. Cozum: SUNUCU veriyi ATTRIBUTE olarak basar (makine okur: data-kurus /
    # data-oneri), METNI sayfa JS'i yazar (satirlar SABIT -> beyan edilebilir).
    secili = on_secim_malzeme(p)
    tani, _ = on_secim_tani(p)
    not_html = ""
    if tani == filament_ortak.TANI_ONERI:
        not_html = ('\n        <div class="oneri-not" id="oneriNot" data-oneri="%s" '
                    'hidden></div>' % esc(secili))
    return ("""
      <div class="opsiyon-row opsiyon-renk">
        <label>Malzeme seçimi</label>
        <div class="fil-cipler" id="filCipler">""" + "".join(_fil_cipleri(p, secili))
            + """</div>""" + not_html + """
      </div>""")


def filament_html(p, wa_not=False, kartlar_gizli=False):
    """Fiyat bloğunun altındaki "Malzeme" bölümü: sitede satılan filament çipleri + tavsiye
    rozeti + balon. Karbon Katkılı SİTEDE SATILMAZ — mühendislik malzemesi, WhatsApp özel
    talebiyle satılır; burada çip olarak SUNULMAZ (yalnız /malzeme-rehberi/ sayfasında ayrı
    bölümde anlatılır). ABS satılır ama KATEGORİYE BAĞLIDIR: hariç kategorilerde
    (secenekler.js FILAMENT_KATEGORI_HARIC) çipi HİÇ basılmaz. wa_not=True ise (malzeme
    seçicisi/dropdown'u olmayan ürün — MALZEME_RENK_HTML basılmıyor) mühendislik malzemesi
    notu burada gösterilir; dropdown'lu üründe not zaten opsiyonlar bloğunda var, mükerrer
    basılmaz.

    kartlar_gizli=True (KONFIGUR-malzemeli sayfa, Okan 24 Tem): malzeme SEÇİMİ yukarıda
    #malzemeButonlar fancy kartlarından yapılır -> buradaki AYNI kartların ikinci kopyası
    "çift-UI" olur; KART bölümü (başlık + fil-cipler) BASILMAZ, yalnız mühendislik-malzeme
    (Karbon/ABS) WhatsApp notu + "Malzeme Rehberi" linki kalır (faydalı bilgi).

    MİMARİ İLKE: filament bilgisi ürün verisine YAZILMAZ — tavsiye, kategori haritasından
    (tools/filamentler.json) render anında türetilir; ürün "tavsiyeFilament" override'ı
    taşıyorsa harita yerine o geçer. Balon metni referanstaki "uzun" alanının birebir
    kendisidir (tek kaynak). F kalemi (Okan, 16 Tem gece): parametrik (sarı) sayfa da
    normal sayfayla BİREBİR — tavsiye rozeti dahil; eski "rozet basılmaz + konuşarak
    belirlenir notu" istisnası kaldırıldı.
    """
    cips = _fil_cipleri(p)
    wa_html = muhendislik_wa_not(p, product_url(p.get("id") or "")) if wa_not else ""
    if kartlar_gizli:
        # Konfigur-malzemeli sayfa: malzeme seçimi #malzemeButonlar fancy kartlarında -> burada
        # KART bölümü (başlık + #filCipler) mükerrer olur, basılmaz; WA notu + rehber linki kalır.
        return ('<div class="malzeme-blok">%s'
                '<a class="malzeme-link" href="/malzeme-rehberi/">Hangi malzeme nerede kullanılır? '
                'Malzeme Rehberi &rarr;</a>'
                '</div>' % wa_html)
    return ('<div class="malzeme-blok">'
            '<div class="malzeme-baslik">Malzeme</div>'
            '<div class="fil-cipler" id="filCipler">%s</div>'
            '%s'
            '<a class="malzeme-link" href="/malzeme-rehberi/">Hangi malzeme nerede kullanılır? '
            'Malzeme Rehberi &rarr;</a>'
            '</div>' % ("".join(cips), wa_html))


# ------------------------------------------------------------------ ürün sayfası
# ------------------------------------------------------------------ urun sayfasi PAYLASILAN JS
# Bu govde HER urun sayfasinda BIREBIR aynidir -> sayfaya gomulmez, icerik-adresli
# /varlik/urun-<hash>.js dosyasina yazilir ve referansla cagirilir (varlik_adres).
# URUNE OZEL VERI sayfada satir-ici kalir: URUN / URUN_SEMA / URUN_KART_SECIM /
# URUN_KONFIGUR. Bu dosya klasik (async/defer'siz) script'tir; sayfadaki veri blogu
# ONUNDE durur -> tarayici sirayi korur, degisken tanimli olur.
# Kanca alanlari ({konf_*} / {onizleme_js}) yalniz ilgili sayfa turunde DOLU olur; dolu
# ve bos govde AYRI icerik = AYRI hash = AYRI dosya (davranis bire bir korunur).
URUN_JS_SABLONU = u"""(function(){{
  var topBtn=document.getElementById("topBtn");
  window.addEventListener("scroll",function(){{
    topBtn.classList.toggle("show", window.scrollY > 600);
  }},{{passive:true}});
  topBtn.onclick=function(){{ window.scrollTo({{top:0, behavior:"smooth"}}); }};
}})();
function pv(el,src){{
  document.getElementById('mainImg').src=src;
  var t=document.querySelectorAll('.thumb');
  for(var i=0;i<t.length;i++){{t[i].className='thumb';}}
  el.className='thumb active';
}}
/* Sepet: bu ürünü index.html ile ortak localStorage sepetine (secenekler.js: PRUVO_SECENEK) ekle/çıkar.
   Malzeme/renk/boy seçiliyse (opsiyonlar bloğu varsa) seçilen TAM konfigürasyon bileşik anahtarla
   toggle edilir; farklı bir konfigürasyonla eklenmiş başka bir satıra dokunulmaz. */
(function(){{
  var btn=document.getElementById("cartBtn"); if(!btn){{ return; }}
  var id=URUN.id;
  var label=btn.querySelector(".cart-label");
  var fab=document.getElementById("cartFab");
  var count=document.getElementById("cartCount");
  var orderAlt=document.getElementById("orderAlt");
  var malzemeSec=document.getElementById("malzemeSec");
  var renkSec=document.getElementById("renkSec");
  var renkOzel=document.getElementById("renkOzel");
  var boySec=document.getElementById("boySec");
  var adetSec=document.getElementById("adetSec");
  var adetEksi=document.getElementById("adetEksi");
  var adetArti=document.getElementById("adetArti");
  var fiyatEl=document.getElementById("opsiyonFiyat");
  /* Ustu cizili eski fiyat (opsiyonel `eski_fiyat`). Sayfada YOKSA null -> hicbir sey olmaz. */
  var eskiEl=document.getElementById("eskiFiyat");
  /* Kart-secim modu (işletme kararı, 16 Tem): fonksiyonel ürünlerde malzeme dropdown YOK,
     malzeme KARTLARINDAN seçilir. */
  var KART_SECIM = URUN_KART_SECIM;
  var cipler = document.getElementById("filCipler");
  var renkBtnlar = document.getElementById("renkButonlar");
  /* 🔴 ONDEN SECILI (11 Agu) — baslangic durumu SAYFADAN okunur, JS'e IKINCI bir varsayilan
     listesi YAZILMAZ. Uretec hangi cipe/butona `secili` bastiysa durum odur; uretecin
     varsayilani da secenekler.js bosSatir()'dan turer -> gorunen secim, hicbir secim
     yapilmadan olusan sepet satiriyla AYNI degerdir (kurus farki yapisal olarak 0). */
  function _ilkSecim(kok, secici, alan){{ var ilk = (kok && kok.querySelector) ? kok.querySelector(secici) : null; return ilk ? (ilk.getAttribute(alan) || "") : ""; }}
  var seciliMalzeme = _ilkSecim(cipler, ".fil-cip.secili", "data-malzeme");
  var seciliRenk = _ilkSecim(renkBtnlar, ".renk-btn.secili", "data-renk");
  /* 🔴 GORUNUR SECIM HATASI — "sessiz basarisizlik" sinifinin kapatildigi yer.
     ONCE: eksik secimde yalniz 500 ms titreme vardi; kullanici tikladigini saniyor,
     sepet bos kaliyordu (canlida olculdu). ARTIK: ya ekleme OLUR ya BU KUTU DOLAR.
     Kutu sayfada yoksa (kirpilmis/eski sablon) BURADA URETILIR — "kutu yok" hali
     sessizlige DUSMEK degildir (fail-loud). */
  var hataEl = document.getElementById("secimHata");
  /* Onerilenden BASKA malzeme secildiginde gorunen bilgi notu (varsa). Metni BURADA
     yazilir: sunucu yalniz hangi malzemenin onerildigini `data-oneri` ile bildirir. */
  var oneriNot = document.getElementById("oneriNot");
  if(oneriNot){{ oneriNot.textContent = "Seçtiğiniz malzeme, bu ürün için önerdiğimiz malzeme (" + (oneriNot.getAttribute("data-oneri") || "") + ") değil. Dilerseniz devam edebilirsiniz."; }}
  /* Her malzeme cipi KENDI tutarini `data-kurus` ile tasir; GORUNUR etiketi burada
     yazilir. Boylece taban secenegin tutari sayfada hem okunur hem gorunur kalir. */
  if(cipler){{ var _ct = cipler.querySelectorAll(".fil-cip[data-kurus]"); for(var t=0;t<_ct.length;t++){{ var _bl=_ct[t].querySelector(".fil-balon"); var _sp=document.createElement("span"); _sp.className="fil-tutar"; _sp.textContent=PRUVO_SECENEK.kurusMetni(parseInt(_ct[t].getAttribute("data-kurus"),10)); if(_bl){{ _ct[t].insertBefore(_sp,_bl); }} else {{ _ct[t].appendChild(_sp); }} }} }}
  function hataKutusu(){{
    if(hataEl || !document.createElement){{ return hataEl; }}
    var kutu = document.createElement("div");
    kutu.id = "secimHata"; kutu.className = "secim-hata";
    kutu.setAttribute("role", "alert"); kutu.setAttribute("aria-live", "assertive");
    kutu.style.cssText = "margin:2px 0 12px;padding:9px 12px;border-radius:8px;background:#fdecea;border:1px solid #f0b3ae;color:#8f1d19;font-size:13.5px;font-weight:600;line-height:1.45";
    var kap = (btn.parentNode && btn.parentNode.parentNode) || btn.parentNode;
    if(kap && kap.appendChild){{ kap.appendChild(kutu); hataEl = kutu; }}
    /* ⚠️ KAPANIS SUSLU PARANTEZI SON SATIRA BITISIK: tools/varlik-test.py eksen 2 sayfa
       JS'ini SATIR COKKUMESI olarak olcer ve yalniz `}}` iceren bir satir AYIRT EDICI
       DEGILDIR — beyan edilemez (beyan edilseydi gercek bir icerik kaybini maskelerdi).
       Bicimi "duzeltip" `}}`yi kendi satirina almadan once o kapiya bak. */
    return hataEl; }}
  function hataGoster(metin){{
    var kutu = hataKutusu();
    /* SON CARE: DOM'a kutu koyulamadiysa bile kullanici UYARILIR — sessiz donus YOK. */
    if(!kutu){{ if(typeof alert === "function"){{ alert(metin); }} return; }}
    kutu.textContent = metin; kutu.hidden = false; kutu.removeAttribute("hidden"); }}
  function hataGizle(){{ if(hataEl){{ hataEl.hidden = true; hataEl.setAttribute("hidden", "hidden"); hataEl.textContent = ""; }} }}

  function currentSatir(){{
    var s = PRUVO_SECENEK.bosSatir(id);
    if(malzemeSec){{ s.malzeme = malzemeSec.value; }}
    else if(KART_SECIM){{ s.malzeme = seciliMalzeme; }}
    if(renkSec){{
      s.renk = renkSec.value;
      s.renk_ozel = (renkSec.value === "Diğer" && renkOzel) ? renkOzel.value : "";
    }} else if(KART_SECIM){{
      s.renk = seciliRenk;
      s.renk_ozel = (seciliRenk === "Diğer" && renkOzel)
        ? renkOzel.value.trim().slice(0, 30) : "";
    }}
    if(boySec){{ s.boy_etiket = boySec.value || null; }}
    if(adetSec){{ s.adet = PRUVO_SECENEK.adetDuzelt(adetSec.value); }}
    /* Parametrik urun: konfigurator parametreleri + hacim + (taban fiyat varsa) kurusu satira
       yazar. Adet YUKARIDA set edildi -> parametrik satirda da gecerli. */
    if(URUN_SEMA && window.PRUVO_KONF && PRUVO_KONF.hazir()){{ PRUVO_KONF.satiraYaz(s); }}{konf_satir_hook}
    return s;
  }}
  /* Adet kutusu: aralik disi deger (elle yazilan 0/500) secenekler.js kuralina cekilir —
     Worker da AYNI araligi dogrular, aralik disi istegi reddeder. */
  function adetYaz(v){{
    if(!adetSec){{ return; }}
    adetSec.value = PRUVO_SECENEK.adetDuzelt(v);
    render();
  }}
  /* Eksik seçim grubunu titret + kırmızıya çevir (geçici). Konteyner (malzeme kartları /
     renk butonları) -> cocuk cerceveleri kirmizi; metin kutusu -> kendisi. Saf CSS/JS. */
  function titret(el){{
    if(!el){{ return; }}
    var kutu = el.classList.contains("renk-ozel");
    el.classList.remove("titre", "hata-vurgu", "hata");
    void el.offsetWidth;                           // animasyonu yeniden başlat (reflow)
    el.classList.add("titre", kutu ? "hata" : "hata-vurgu");
    setTimeout(function(){{ el.classList.remove("titre", "hata-vurgu", "hata"); }}, 500);
  }}
  function render(){{
    /* Eksik secim tamamlanir tamamlanmaz kirmizi uyari kendiliginden kalkar. */
    if(!KART_SECIM || (seciliMalzeme && seciliRenk && !(seciliRenk === "Diğer" && renkOzel && !renkOzel.value.trim()))){{ hataGizle(); }}
    /* 🔴 BILGILENDIRME (ENGEL DEGIL): onerdigimizden BASKA malzeme secildiginde musteri
       bunu ANLAMALI. Secim serbesttir — musterinin bilerek taban malzemeye ihtiyaci
       olabilir. Not YALNIZ ayrik durumda gorunur; onerilen seciliyken GORUNMEZ (gurultu
       yapmaz). Onerisi TURETILEMEYEN urunde kutu HIC basilmaz -> `data-oneri` bos kalir
       ve kosul dogal olarak hicbir zaman saglanmaz (fail-closed). */
    if(oneriNot){{ var _o = oneriNot.getAttribute("data-oneri") || ""; oneriNot.hidden = !(_o && seciliMalzeme && seciliMalzeme !== _o); }}
    var c = PRUVO_SECENEK.sepetYukle();
    var satir = currentSatir();
    var anahtar = PRUVO_SECENEK.satirAnahtari(satir);
    var has = c.some(function(s){{ return PRUVO_SECENEK.satirAnahtari(s) === anahtar; }});
    btn.classList.toggle("added", has);
    /* 🔴 ETIKETLI KALIPTA DA ARIA SENKRON (11 Agu): sepet butonu artik yazili; gorunur
       metin "Sepette ✓" olurken aria-label "Sepete Ekle"de kalsaydi ekran okuyucu
       kullanicisi butonun ne yaptigini YANLIS duyardi. Tek satir, ayirt edici. */
    if(label){{ var eD = has ? "Sepette ✓ — çıkarmak için tıklayın" : "Sepete Ekle"; btn.setAttribute("aria-label", eD); btn.setAttribute("title", eD); }}
    if(label){{ label.textContent = has ? "Sepette ✓" : "Sepete Ekle"; }}
    else {{
      /* İkon buton (yazısız, madde 7): durum bildirimi title + aria-label ile. */
      var bm = has ? "Sepette ✓ — çıkarmak için tıklayın" : "Sepete Ekle";
      btn.setAttribute("aria-label", bm); btn.setAttribute("title", bm);
    }}
    if(count){{ count.textContent = c.length; }}
    if(fab){{ fab.style.display = c.length ? "inline-flex" : "none"; }}
    /* yukarı-çık oku FAB'la çakışmasın (CSS: body.fab-var .top-btn) */
    document.body.classList.toggle("fab-var", c.length > 0);
    var ozet = PRUVO_SECENEK.satirOzeti(URUN, satir);
    /* ESKI FIYAT NOBETI (yalniz GOSTERIM — sepet/odeme kurusuna DOKUNMAZ): ustu cizili
       fiyat, secilen malzeme/renk BIRIM fiyatini eski fiyatin ustune cikardigi anda
       GIZLENIR. Aksi halde 1.200 TL cizili dururken 1.275 TL tahsil edilir gorunurdu —
       yaniltici indirim (sessiz ticari/hukuki hata). Kiyas BIRIM kurusla yapilir (adet
       carpani iki tarafta da yok). ozet.birimKurus null ise (fiyatsiz urun) gizlenir. */
    if(eskiEl){{
      var _eskiKurus = parseInt(eskiEl.getAttribute("data-kurus") || "0", 10);
      eskiEl.hidden = !(_eskiKurus > 0 && ozet.birimKurus != null
                        && _eskiKurus > ozet.birimKurus);
    }}
    /* Konfigüratörlü sayfada fiyat alanını konfigüratör yönetir (kuruşlu canlı hesap,
       taban fiyat yoksa "—"); geçersiz ölçüde sepete ekleme kilitlenir. */
    if(fiyatEl && !URUN_SEMA{konf_fiyat_kosul}){{
      /* Kart-secim: malzeme+renk seçilene kadar fiyat taban (PLA) "…'den başlayan";
         ikisi de seçilince kesin katsayılı/renkli fiyat gösterilir. */
      if(KART_SECIM && (!seciliMalzeme || !seciliRenk) && ozet.birimKurus != null){{
        fiyatEl.textContent = ozet.fiyatMetni + "'den başlayan";
      }} else {{
        fiyatEl.textContent = ozet.fiyatMetni;
      }}
    }}
    if(URUN_SEMA && window.PRUVO_KONF && PRUVO_KONF.hazir()){{
      PRUVO_KONF.tazele();
      var gecerli = PRUVO_KONF.gecerliMi();
      btn.disabled = !gecerli;
      btn.classList.toggle("kilitli", !gecerli);
    }}{konf_render_hook}
    if(orderAlt){{
      var mesaj = "Merhaba, şu ürünle ilgileniyorum: " + URUN.baslik +
                  (ozet.detay ? ("\\n" + ozet.detay) : "") + "\\n" + location.href;
      var ref = (typeof window.pruvoRef === "function") ? window.pruvoRef() : "";
      if(ref){{ mesaj += "\\n" + ref; }}
      orderAlt.href = "https://wa.me/{whatsapp}?text=" + encodeURIComponent(mesaj);
    }}
  }}
  btn.addEventListener("click", function(){{{konf_klik_guard}
    /* Malzeme + renk seçilmeden sepete eklenemez (istemci 1. savunma; Worker 2. savunma).
       "Diğer" renkte serbest metin kutusu da dolu olmalı. Eksik olan grup(lar) titrer. */
    if(KART_SECIM){{
      var eksikM = !seciliMalzeme;
      var eksikR = !seciliRenk;
      var eksikO = seciliRenk === "Diğer" && renkOzel && !renkOzel.value.trim();
      if(eksikM || eksikR || eksikO){{
        if(eksikM){{ titret(cipler); }}
        if(eksikR){{ titret(renkBtnlar); }}
        if(eksikO){{ titret(renkOzel); }}
        /* 🔴 METINLI UYARI ZORUNLU — titreme tek basina "sessiz basarisizlik"tir. */
        var eksikAd = [];
        if(eksikM){{ eksikAd.push("malzeme"); }}
        if(eksikR){{ eksikAd.push("renk"); }}
        hataGoster(eksikAd.length ? ("Sepete eklemek için " + eksikAd.join(" ve ") + " seçin.") : "Sepete eklemek için istediğiniz rengi yazın.");
        var hedef = eksikM ? cipler : (eksikR ? renkBtnlar : renkOzel);
        if(hedef){{
          try {{ hedef.scrollIntoView({{ behavior:"smooth", block:"center" }}); }} catch(e) {{}}
          var od = eksikO ? renkOzel
            : (hedef.querySelector ? hedef.querySelector(".fil-cip,.renk-btn") : null);
          if(od){{ od.focus(); }}
        }}
        return;
      }}
    }}
    var c = PRUVO_SECENEK.sepetYukle();
    var satir = currentSatir();
    var anahtar = PRUVO_SECENEK.satirAnahtari(satir);
    var i=-1;
    for(var j=0;j<c.length;j++){{ if(PRUVO_SECENEK.satirAnahtari(c[j])===anahtar){{ i=j; break; }} }}
    if(i===-1){{
      c.push(satir);
      /* AddToCart (rıza-kapılı): yalnız gerçek EKLEMEDE (toggle-çıkarmada değil). value = seçilen
         konfigürasyonun kuruşlu tutarı TRY'ye; content_ids DAİMA katalog kimliği URUN.fid
         (=feed_id(pid), feed g:id ile tek kaynak), content_type "product". */
      try {{
        var mAtc = PRUVO_SECENEK.satirOzeti(URUN, satir);
        var mAtcVeri = {{ content_ids:[URUN.fid], content_type:"product", currency:"TRY" }};
        if(mAtc && mAtc.kurus != null){{ mAtcVeri.value = mAtc.kurus/100; }}
        if(typeof window.pruvoMetaTrack === "function"){{ window.pruvoMetaTrack("AddToCart", mAtcVeri); }}
        /* GA4 ikizi (add_to_cart): AYNI noktadan, AYNI degerlerden (URUN.fid + mAtc) turer;
           ikinci bir huni/tetikleme noktasi YOK. value satir toplamidir, price birim fiyat
           (value/adet) — adet 0 olamaz (adetDuzelt en az 1 doner) ama yine de korunur. */
        var gAtcAdet = PRUVO_SECENEK.adetDuzelt(satir.adet);
        var gAtcKalem = {{ item_id: URUN.fid, item_name: URUN.baslik,
                           item_category: URUN.kategori, quantity: gAtcAdet }};
        var gAtcVeri = {{ currency: "TRY", items: [gAtcKalem] }};
        if(mAtcVeri.value != null){{ gAtcVeri.value = mAtcVeri.value;
          if(gAtcAdet > 0){{ gAtcKalem.price = mAtcVeri.value / gAtcAdet; }} }}
        if(typeof window.pruvoGA4Track === "function"){{ window.pruvoGA4Track("add_to_cart", gAtcVeri); }}
      }} catch(e) {{}}
    }} else {{ c.splice(i,1); }}
    /* Uyari ayrica sokulmez: asagidaki render() secim tamamlandiginda kutuyu kapatir. */
    PRUVO_SECENEK.sepetKaydet(c); render();
  }});
  /* Malzeme kartlarını malzeme seçicisine çevir (yalnız kart-secim modu). Tıklanan kart
     seçili (lacivert dolgu) olur, ötekiler bırakılır; fiyat + sepet durumu tazelenir.
     Bilgi balonunu ayrı IIFE (aşağıda) yönetir — burada yalnız SEÇİM. */
  if(KART_SECIM && cipler){{
    var kartlar = cipler.querySelectorAll(".fil-cip");
    for(var k=0;k<kartlar.length;k++){{
      kartlar[k].addEventListener("click", function(){{
        seciliMalzeme = this.getAttribute("data-malzeme") || "";
        for(var n=0;n<kartlar.length;n++){{ kartlar[n].classList.toggle("secili", kartlar[n]===this); }}
        render();
      }});
    }}
  }}
  /* Renk butonları: tıklanan seçili (lacivert dolgu), ötekiler bırakılır. "Diğer" seçilince
     serbest metin kutusu belirir (müşteri istediği rengi yazar). */
  if(KART_SECIM && renkBtnlar){{
    var rbtnlar = renkBtnlar.querySelectorAll(".renk-btn");
    for(var rr=0;rr<rbtnlar.length;rr++){{
      rbtnlar[rr].addEventListener("click", function(){{
        seciliRenk = this.getAttribute("data-renk") || "";
        for(var n=0;n<rbtnlar.length;n++){{ rbtnlar[n].classList.toggle("secili", rbtnlar[n]===this); }}
        if(renkOzel){{ renkOzel.style.display = (seciliRenk === "Diğer") ? "block" : "none"; }}
        render();
      }});
    }}
  }}
  [malzemeSec, renkSec, boySec].forEach(function(el){{
    if(!el){{ return; }}
    el.addEventListener("change", function(){{
      if(renkSec && renkOzel){{ renkOzel.style.display = renkSec.value === "Diğer" ? "inline-block" : "none"; }}
      render();
    }});
  }});
  if(renkOzel){{ renkOzel.addEventListener("input", render); }}
  if(URUN_SEMA && window.PRUVO_KONF && window.PRUVO_HACIM){{
    /* F kalemi: sari sayfa da kart-secim — konfiguratorun fiyat gostergesi
       secili kart/cipten beslenir (dropdown yok; tek kaynak secenekler.js kurali). */
    if(KART_SECIM && PRUVO_KONF.secimKaynagi){{
      PRUVO_KONF.secimKaynagi(function(){{ return {{ malzeme: seciliMalzeme, renk: seciliRenk }}; }});
    }}
    PRUVO_KONF.kur(URUN_SEMA, document.getElementById("konfAlanlar"), render);
  }}{konf_kur_hook}
  if(adetEksi){{ adetEksi.addEventListener("click", function(){{ adetYaz((adetSec.value|0)-1); }}); }}
  if(adetArti){{ adetArti.addEventListener("click", function(){{ adetYaz((adetSec.value|0)+1); }}); }}
  if(adetSec){{
    /* Bu urun/konfigurasyon SEPETTEYSE adet degisikligi sepete de islenir: kullanici
       "Sepette ✓" gorurken adeti 3 yapip sepette 1 kalmasi sasirtici olurdu. */
    adetSec.addEventListener("change", function(){{
      var yeni = PRUVO_SECENEK.adetDuzelt(adetSec.value);
      adetSec.value = yeni;
      var c = PRUVO_SECENEK.sepetYukle();
      var anahtar = PRUVO_SECENEK.satirAnahtari(currentSatir());
      var degisti = false;
      for(var j=0;j<c.length;j++){{
        if(PRUVO_SECENEK.satirAnahtari(c[j])===anahtar){{ c[j].adet = yeni; degisti = true; }}
      }}
      if(degisti){{ PRUVO_SECENEK.sepetKaydet(c); }}
      render();
    }});
    adetSec.addEventListener("input", render);
  }}
  render();
}})();
/* Malzeme çipleri: masaüstünde hover (CSS), mobilde DOKUNMA ile açılır/kapanır.
   title= mobilde çalışmadığı için balon .acik sınıfıyla toggle edilir; başka çipe
   dokununca öncekiler kapanır, sayfada boş yere dokununca hepsi kapanır. */
(function(){{
  var cips=document.querySelectorAll(".fil-cip");
  function kapat(haric){{
    for(var i=0;i<cips.length;i++){{
      if(cips[i]!==haric){{ cips[i].classList.remove("acik"); cips[i].setAttribute("aria-expanded","false"); }}
    }}
  }}
  for(var i=0;i<cips.length;i++){{
    cips[i].addEventListener("click",function(e){{
      e.stopPropagation();
      var acildi=this.classList.toggle("acik");
      this.setAttribute("aria-expanded",acildi?"true":"false");
      kapat(this);
    }});
  }}
  document.addEventListener("click",function(){{ kapat(null); }});
}})();
{onizleme_js}
"""



def render_product(p, all_products, chip_map=None):
    pid = p["id"]
    url = product_url(pid)
    baslik = p.get("baslik") or ""
    # `kategori` = VERI (arama/filtre/ilgili-urun/fonksiyonel kollari BUNA bakar).
    # `gorunur_kat` = MUSTERIYE GORUNEN etiket (rozet, breadcrumb, JSON-LD, "Diğer ...
    # ürünleri" basligi, kategori linkleri). Ikisi parametrik seride BILEREK farklidir —
    # bkz. GIZLI_SERI_KARARI. Asagida "gorunen" her yerde gorunur_kat kullanilir.
    kategori = p.get("kategori") or ""
    gorunur_kat = gorunur_kategori(p)
    fiyat = (p.get("fiyat") or "").strip()
    # ALT KATEGORI — kategori icindeki daraltma etiketi (935/16.874 kayitta dolu, hepsi
    # Marin). Bugune kadar YALNIZ veriydi: musteri hicbir yuzeyde gormuyordu.
    #
    # 🔴 FAIL-CLOSED, TEK KAYNAK: deger arama.altkategori_kanonik'ten gelir. Bos / eksik /
    # None / izinsiz / yanlis-kategorili / metin-olmayan her girdide "" doner -> asagida
    # ne gorunur etiket ne yapilandirilmis veri anahtari basilir. "Gorsel yoksa kirik adres
    # yerine durust eksiklik" kuralinin aynisi: bos etiket/bos kirilim/bos JSON-LD YOK.
    # 15.939 altkategorisiz sayfa bu daldan GECMEZ -> cikti BAYT-ESIT (regresyon 0).
    altkategori = arama.altkategori_kanonik(p)
    markalar = p.get("marka") or []
    imgs = images_of(p)
    # cover = GOVDEDE basilan kapak (gorsel yoksa data: URI yer tutucu -> ag istegi yok).
    # paylasim_gorseli = og:image / twitter:image / JSON-LD `image` icin MUTLAK URL; gorsel
    # yoksa BOS kalir ve o alanlar HIC basilmaz (bkz. placeholder_data_uri yorumu).
    # Gorselli urunde ikisi de imgs[0] -> cikti BAYT-ESIT.
    paylasim_gorseli = imgs[0] if imgs else ""
    # Gorselsiz urunun yer tutucusuna kategori ADI CIZILIR -> gorunur etiket kullanilir.
    cover = paylasim_gorseli or placeholder_data_uri(gorunur_kat)
    desc160 = meta_desc(p)
    pnum = price_number(fiyat)
    parametrik = bool(p.get("parametrik"))
    # --- FIZIKSEL URUN (Okan, 31 Tem — canli kusur): `tur` == "fiziksel" olan kayit HAZIR
    # TICARI MALDIR (tekne boyasi, vernik, tiner...). 3D BASKIYLA URETILMEZ; dolayisiyla
    # o urunde malzeme SECIMI ve renk SECIMI YOKTUR, fiyati da SABITTIR.
    #
    # 🔴 NEDEN PARA YOLU (sayfa kozmetigi DEGIL): renk butonlarindaki "Diğer (+%15)"
    # secenegi secenekler.js hesaplaFiyatKurus'a `renk == "Diğer"` olarak gider ve liste
    # fiyatini x1,15 yapar; malzeme cipleri ayrica x1,60'a kadar (ASA) cikarir. Olculdu:
    # 1.000 TL'lik boya, ASA+"Diğer" secimiyle 1.840,00 TL tahsil ediliyordu — KARSILIGI
    # OLMAYAN bir secim icin. Secicileri basmamak bu yolu ISTEMCIDE kapatir: sepet satiri
    # PRUVO_SECENEK.bosSatir varsayilanlariyla (PLA/Siyah = x1,00) uretilir.
    #
    # 🔴 FAIL-CLOSED: SADECE tam "fiziksel" dizesi bu dali acar. Alan YOKSA ya da taninmayan
    # bir deger tasiyorsa sayfa BUGUNKU gibi uretilir ("3D ISE goster" DEGIL, "fiziksel ISE
    # kaldir") -> `tur`suz 15.930 baski urununde regresyon 0.
    fiziksel = (p.get("tur") == "fiziksel")
    # Parametrik (sarı seri) şeması TEK KEZ burada yüklenir: hem JSON-LD taban
    # fiyatı hem aşağıdaki konfigüratör bloğu aynı sema objesini kullanır.
    sema = konf_sema(pid) if parametrik else None
    # SATIŞ KAPISI: bu ailenin hacmi doğrulandı mı? Soru TEK KAYNAKTAN (yukarıdaki
    # aile_satis_kapali_mi) sorulur — ana sayfa kartı ve SSR kart da AYNI fonksiyonu
    # çağırır; ikinci liste/ikinci ifade YOK.
    aile_satis_kapali = aile_satis_kapali_mi(sema)
    # Konfigur (dekor konfigüratörü): OPSİYONEL alan; yoksa sayfa bugünkü gibi davranır
    # (kabul: tools/konfigur-test.py bayt-eşitlik). Geçersiz konfigur build'i DÜŞÜRÜR
    # (fail-closed — yanlış fiyat/görsel eşlemesi sessizce yayınlanamaz).
    konfigur = p.get("konfigur")
    if konfigur is not None:
        _konf_hatalar = konfigur_dogrula(p)
        if _konf_hatalar:
            raise SystemExit("HATA: %s urununde gecersiz konfigur alani:\n  - %s"
                             % (pid, "\n  - ".join(_konf_hatalar)))

    # Safari Reader Mode kaçınması: açıklama TEK büyük <p>/<br> yerine, WebKit
    # isProbablyReaderable skorlayıcısının SAYMADIĞI düğümlerde emit edilir —
    # her kaynak satırı bir <div class="desc-satir">, boş satır bir
    # <div class="desc-bosluk">. Metin bayt-bayt korunur (yalnız sarma etiketi
    # <br> yerine satır-başı <div> olur). → [[safari-reader-desc]]
    _desc_satir = (p.get("aciklama") or "").split("\n")
    aciklama_html = "".join(
        ('<div class="desc-satir">%s</div>' % esc(ln)) if ln.strip()
        else '<div class="desc-bosluk" aria-hidden="true"></div>'
        for ln in _desc_satir)

    # --- JSON-LD Product
    # Fiyat temsili (GSC Merchant listings): FİYATSIZ Offer basmak «"price" alanı
    # eksik» KRİTİK hatası üretir (canlıda doğrulandı, 22 Tem — 21 parametrik sayfa
    # etkilenmişti). Parametrik/sarı üründe "fiyat" BOŞ → taban fiyat şemadan
    # (jenerator/urunler/<id>.json tabanFiyatTL — taban-fiyatlar.js ile AYNI tek
    # kaynak). Taban fiyat ZEMİNdir ("X TL'den başlayan") → Offer.price başlangıç
    # fiyatı olarak doğru beyan. FAIL-CLOSED: sayısal fiyat hiçbir kaynaktan
    # bulunamazsa offers HİÇ basılmaz. Test: tools/test-jsonld-offers.py
    #
    # 🔴 SATIS KAPISI KAPALI AILE (2026-08-04, canli kusur): hacmi DOGRULANMAMIS
    # ailede secenekler.js parametrikFiyatKurus **null** dondurur ve Worker sepeti
    # 400 `hacim-dogrulanmamis` ile reddeder — yani o urun BUGUN SATILAMAZ. Buna
    # ragmen sayfa JSON-LD'de `price` + `availability: InStock` beyan ediyordu:
    # arama motoruna (ve fiyat karsilastirma yuzeylerine) OLMAYAN bir tutar ve
    # ALINABILIR bir stok bildiriliyordu. Ayni fail-closed dala sokulur: sayisal
    # fiyat YOK -> offers HIC basilmaz (InStock da offers'in icinde oldugu icin
    # birlikte duser). Yeni paralel dal ACILMAZ.
    # 🔴 YAPILANDIRILMIS VERI TABANI = LISTE/KART YUZEYI (isletme karari, 11 Agu — Okan'in
    # kendi secimi, riski kendisine YAZILI bildirildikten sonra): beyan edilen TABAN
    # BASLANGIC tutaridir. Yani bu satir urun sayfasi koluna DEGIL, KART koluna baglidir
    # (ONERI_VITRIN_ACIK) — urun sayfasinda onden secili malzeme yukselse bile TABAN KAYMAZ.
    # 🔴 TEK TURETME NOKTASI (12 Agu): taban artik BAYRAKLA KOSULLU DEGIL, kart yuzeyinin
    # KENDI turetmesinden (vitrin_kurus — anahtari ICINDE) KOSULSUZ cikar. Onceki hal
    # bayrak kapaliyken `price_number`a dusuyordu ve o AYRI bir ayristirma kuralidir:
    # olculdu (12 Agu), "300 TL (30 cm)" biçimli 1 kayitta kart 300 TL derken markup
    # 30.030 TL beyan ediyordu — 100 kat sapma, SIFIR alarm. Iki yuzey artik ayni sayidan
    # turer. `pnum` yalnizca tutar CIKARILAMAYAN kolda (parametrik) geri dusustur.
    ld_fiyat = ilan_tl_metni(vitrin_kurus(p)) or pnum
    if aile_satis_kapali:
        ld_fiyat = None
    elif ld_fiyat is None and sema is not None:
        taban = sema.get("tabanFiyatTL")
        if isinstance(taban, (int, float)) and not isinstance(taban, bool) and taban > 0:
            ld_fiyat = ("%.2f" % taban).rstrip("0").rstrip(".")
    # 🔴 ARALIK (12 Agu, Okan'in karari — 11 Agu'daki "tek fiyat" tercihinin YERINE GECER):
    # kart BASLANGIC tabanini, urun sayfasi ONERILEN malzemenin tutarini yazdigi surece TEK
    # fiyat basmak dis yuzeye eksik bilgi verir. Markup artik AggregateOffer'dir:
    #   lowPrice  = kartin yazdigi tutar (BASLANGIC tabani; kart yuzeyiyle BIREBIR)
    #   highPrice = EN PAHALI malzemenin tutari (musterinin sayfada secebilecegi tavan)
    # Ikisi de TEK turetme noktasindan (_birim_kurus) cikar; ikinci formul yazilmaz.
    # `price` KALIR ve lowPrice ile AYNIDIR: GSC "«price» alani eksik" hatasi bu depoda
    # ZATEN OLCULDU (22 Tem, 21 sayfa) — alani dusurmek o kusuru geri getirme riski tasir.
    # Aralik YALNIZ malzeme secicisi basilan kolda acilir; olcuye ozel / yapilandiricili /
    # hazir ticari malda tutar malzemeyle yukselmez -> tekil Offer AYNEN kalir (bayt-esit).
    ld_yuksek = ilan_tl_metni(en_yuksek_kurus(p)) if (ld_fiyat and
                                                      malzeme_aralikli_mi(p)) else None
    if ld_yuksek is not None and ld_yuksek == ld_fiyat:
        ld_yuksek = None            # aralik acilmadi -> tekil teklif (yaniltici tavan yok)
    offer = {
        "@type": "AggregateOffer" if ld_yuksek else "Offer",
        "url": url,
        "availability": "https://schema.org/InStock",
        "itemCondition": "https://schema.org/NewCondition",
        "priceCurrency": "TRY",
        "seller": {"@type": "Organization", "name": "PRUVO"},
    }
    if ld_fiyat:
        offer["price"] = ld_fiyat
        if ld_yuksek:
            offer["lowPrice"] = ld_fiyat
            offer["highPrice"] = ld_yuksek
            # SAYI = MUSTERININ O SAYFADA SECEBILECEGI malzeme adedi: kategori sizgeci
            # (FILAMENT_KATEGORI_HARIC) uygulanir. Ham FILAMENT_SIRA basilsaydi haric
            # kategoride secilemeyen bir secenek DISA BEYAN EDILIRDI.
            offer["offerCount"] = len([m for m in FILAMENT_SIRA
                                       if malzeme_kategori_uygun_mu(m, p.get("kategori"))])
        offer["priceValidUntil"] = PRICE_VALID

    # `image` KOSULLU basilir; bu yuzden sozluk IKI parcada kurulur. Anahtar SIRASI
    # korunur (json.dumps ekleme sirasini yazar): gorselli urunde @context, @type, name,
    # image, description, sku, mpn, category -> bugunkuyle BAYT-ESIT.
    #
    # NEDEN gorselsizde alan HIC yazilmaz: eskiden `imgs or [cover]` ile 404 veren
    # favicon.png basiliyordu; Google icin bu "gorsel beyan edildi ama alinamiyor" = HATA.
    # `image` Product'ta ONERILEN alandir, ZORUNLU degil — eksik birakmak durust ve
    # zararsiz, KIRIK URL degil. Yer tutucu data: URI de basilmaz: schema.org `image`
    # ImageObject/URL bekler, data: URI crawler icin anlamsiz ve ~1 KB gurultudur. Ayni
    # urun Merchant feed'e zaten girmiyor (render_merchant_feed gorselsizi eler) -> feed
    # ile JSON-LD celismez.
    product_ld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": baslik,
    }
    if imgs:
        product_ld["image"] = imgs
    product_ld.update({
        "description": re.sub(r"\s+", " ", (p.get("aciklama") or "")).strip(),
        # GSC Merchant listings "sku" 50 karakter siniri: feed g:id/g:mpn ile TEK
        # KAYNAK kanonik kimlik (feed_id: <=50 AYNEN, uzunsa pid[:41]+'-'+sha1[:8]
        # = tam 50). Uzun urun-id'lerinde HAM pid «gecersiz uzunluk» KRITIK hatasi
        # uretiyordu (GSC WNC-10030322, 24 Tem). product_url/link TAM pid ile kalir
        # (sadece feed/JSON-LD kimligi kisalir). Test: tools/test-jsonld-sku.py
        "sku": feed_id(pid),
        # mpn: brand+mpn = GEÇERLİ tanımlayıcı çifti (gtin/barkod YOK -> UYDURULMAZ).
        # GSC Merchant listings "genel tanımlayıcı (gtin, marka) verilmemiş" uyarısını
        # kapatır. Değer feed g:mpn ile TEK KAYNAK (feed_id -> sku == mpn, <=50 karakter);
        # test-jsonld-sku.py sku özdeşliğini + feed g:mpn çapraz-kontrolünü zaten kilitliyor.
        "mpn": feed_id(pid),
        # category: altkategori VARSA "Ust > Alt" taksonomi yolu (schema.org Product.category
        # Text kabul eder; '>' ayracli yol Google urun taksonomisi/product_type ile AYNI
        # yazim — render_merchant_feed'deki `kategori + " > " + marka` ile tutarli). Alan
        # ZATEN vardi ve DOLUYDU; sadece dolu kayitta bir dugum derinlesir -> yapilandirilmis
        # veri GECERLI kalir, YENI ANAHTAR eklenmez, bos deger asla basilmaz.
        # BreadcrumbList'e KONMAZ: ara dugumun `item` URL'i olmak zorunda, altkategori
        # filtresinin URL'i ise HENUZ YOK (ana sayfa ucu kardes depoda) -> kirik/uydurma
        # adres basmak yerine dugum HIC acilmaz.
        # 🔴 GORUNUR ETIKET (11 Agu): yapilandirilmis veri arama sonucunda MUSTERIYE gosterilir
        # -> ic seri adi buraya da GIRMEZ (bkz. GIZLI_SERI_KARARI).
        "category": (gorunur_kat + " > " + altkategori) if altkategori else gorunur_kat,
    })
    if ld_fiyat:
        product_ld["offers"] = offer
    # brand TEK değer (GSC Merchant listings "brand"i tek bekler; DİZİ/iki-kez basmak
    # «brand yineleniyor» KRİTİK hatası — 22 Tem, ÇÖZÜLDÜ, geri getirme). Araç markası VARSA
    # marka[0] (asıl üretici; sonrakiler model kodu); YOKSA (bespoke "ölçüye özel", Skan Art,
    # dağınık) kendi markamız PRUVO -> "genel tanımlayıcı verilmemiş" uyarısı dürüst kapanır.
    # Test: tools/test-jsonld-brand.py (tek brand + dizi-değil).
    product_ld["brand"] = {"@type": "Brand", "name": markalar[0] if markalar else FEED_BRAND}

    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Ana Sayfa", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": gorunur_kat,
             "item": SITE + kategori_url(gorunur_kat)},
            {"@type": "ListItem", "position": 3, "name": baslik, "item": url},
        ],
    }

    def ld(obj):
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

    # --- galeri
    main_img = ('<img class="main-img" id="mainImg" src="%s" alt="%s" '
                'width="800" height="800">') % (esc(cover), esc(baslik))
    thumbs_html = ""
    if len(imgs) > 1:
        parts = []
        for i, src in enumerate(imgs):
            cls = "thumb active" if i == 0 else "thumb"
            parts.append(
                '<img class="%s" src="%s" alt="%s görsel %d" '
                'onclick="pv(this,\'%s\')" loading="lazy">'
                % (cls, esc(src), esc(baslik), i + 1, esc(src)))
        thumbs_html = '<div class="thumbs">' + "".join(parts) + "</div>"

    # --- marka çipleri. markalar[0] (asıl marka) çipi, ürünün crawlable /marka sayfasına
    # (varsa >=ESIK model sayfası, yoksa marka sayfası) GERİ-LİNK verir — Google discovery
    # kök-fix'i ([[seo-olcum-geri-besleme]]): /urun sayfaları yukarı /marka'ya bağlanmıyordu.
    # Hedef marka_model_build.uret'in ürettiği product_chip_map[pid]'dendir (aynı slug/eşik/
    # collision mantığı — reinvent YOK). Sayfası olmayan markada (harita dışı) ya da chip_map
    # verilmediğinde (kabul testleri) bugünkü /?marka= JS-filtre görünümü AYNEN korunur.
    # DEĞİŞEN TEK ŞEY çip HREF'i; çip metni/JSON-LD/fiyat/görsel/feed dokunulmaz. Sonraki
    # çipler (model kodları) da değişmez.
    # 🔴 KAPSAMSIZ `/?marka=<ham>` LINKI YANLIS LISTE VERIYORDU (olculdu 3 Agu, CANLI).
    # Ana sayfa applyUrlParams degeri KATLAR (markaKatla): "Volvo Penta" -> "Volvo";
    # uc ise KATLAMAZ, ham etiketle TAM eslesir. Kategorisiz istek sonucu:
    #   /?marka=Volvo Penta  ->  uc marka=Volvo  ->  620 OTOMOBIL parcasi;
    #   musterinin tikladigi 51 MARIN parcasinin HICBIRI listede YOK (bos liste DEGIL,
    #   YANLIS liste — daha kotusu).
    # ONARIM: link URUNUN KATEGORISINI tasir; istemci o kategorinin cip indeksinden uc
    # etiketini cozer (index.html :: ucMarkaEtiketi) ve uca `marka=Volvo Penta` gider.
    # Kategori bossa parametre BASILMAZ -> o sayfalarda cikti BAYT-AYNI kalir.
    # Marka cipi HREF'i de musteriye gorunen bir adrestir -> gorunur etiket basilir
    # (index.html applyUrlParams gorunur etiketi ic ada CEVIRIR: KATEGORI_ALIAS).
    kapsam = ("kategori=" + _urlq(gorunur_kat, safe="") + "&") if gorunur_kat else ""
    brand_html = ""
    if markalar:
        mm_hedef = (chip_map or {}).get(pid)
        parcalar = []
        for i, b in enumerate(markalar):
            href = esc(mm_hedef) if (i == 0 and mm_hedef) else ("/?" + kapsam + "marka=" + esc(b))
            parcalar.append('<a class="brand-chip" href="%s">%s</a>' % (href, esc(b)))
        brand_html = '<div class="brands">' + "".join(parcalar) + "</div>"

    # --- parametrik ("ölçüye özel") rozeti (bayrak yukarıda, JSON-LD'den önce hesaplandı)
    badge_html = '<span class="ozel-badge">Ölçüye Özel</span>' if parametrik else ''

    # --- GORUNUR ALT KATEGORI ETIKETI (kategori cipinin hemen sagi)
    # ⚠️ Bicim SATIR ICI yazilir, PAYLASILAN PAGE_CSS'e kural EKLENMEZ: ortak stil HER urun
    # sayfasina basildigi icin oraya tek satir eklemek 15.939 altkategorisiz sayfanin da
    # BAYTINI degistirirdi (regresyon butcesi sha256 ile olculuyor — `.sinif-beyan` ayni
    # gerekceyle satir ici yazilmisti). Mevcut `.cat` sinifi yeniden kullanilir; ayirt
    # edici tek fark daha acik lacivert zemin (--navy-2) + soldan bosluk.
    # Deger BOSSA dize BOS kalir -> sablona hicbir sey basilmaz (bos <span> bile yok).
    altkat_html = ('<span class="cat" style="margin-left:8px;background:var(--navy-2)">%s</span>'
                   % esc(altkategori)) if altkategori else ''

    # --- üstü çizili ESKİ FİYAT (opsiyonel `eski_fiyat`; kural + gerekçe eski_fiyat_gosterim'de)
    # Geçersiz/eski<=güncel/parametrik/konfigür durumlarında BOŞ dize döner -> sayfa bugünkü
    # gibi basılır. Parametrik (sarı) ve konfigür sayfalarında BİLEREK basılmaz: oralarda
    # görünen fiyat ölçüye/malzemeye göre CANLI değişir, sabit bir eski fiyat yanıltır.
    eski_html = eski_fiyat_html(p)

    # --- fiyat metni (JS'siz/tarayıcı öncesi durum + fonksiyonel OLMAYAN ürünlerin tek gösterimi)
    if fiyat:
        price_text = fiyat
    elif parametrik:
        # Cumle secenekler.js'ten okunur (FIYATSIZ_METIN) — elle ikinci kopya
        # tutulmaz; ayrisirsa JS oncesi ve JS sonrasi metin celisirdi.
        price_text = FIYATSIZ_METIN
    else:
        price_text = "Fiyat için sipariş verin"

    # --- malzeme/renk/boy seçicisi (fonksiyonel kategoriler) / konfigüratör (parametrik+şemalı)
    fonksiyonel = kategori in FONKSIYONEL_KATEGORILER
    boy_secenekleri = p.get("boy_secenekleri") or []
    # sema yukarıda (JSON-LD taban fiyatı için) TEK KEZ yüklendi.
    if fiziksel:
        # FIZIKSEL URUN paneli — 3D baski secimi YOK: renk butonlari, malzeme cipleri ve
        # "…'den başlayan" fiyat BASILMAZ (malzeme bloğu da aşağıda boş geçilir). KALAN:
        # adet seçici + sepet ikonu + WhatsApp ikonu (aynı ADET_IKON_HTML/IKON_BUTONLAR_HTML
        # bileşenleri — ikinci kopya yok). Fiyat SABIT: liste fiyatı aynen, "başlayan" YOK.
        # 🔴 SINIF BEYANI (tüketici hukuku, 1 Ağu): hazır ticari malda cayma hakkı
        # İŞLER (Mesafeli Sözleşmeler Yönetmeliği m.15 istisnası ölçüye/kişiye özel
        # üretime bakar). Müşteri hangi sınıfta alışveriş yaptığını ÜRÜN SAYFASINDA
        # görmeli; `tur` bugüne kadar yalnız para yolunu sürüyor, hiçbir beyanı
        # sürmüyordu. Cümle secenekler.js BEYAN tek kaynağından gelir; `tur`suz
        # 15.930 ürün bu daldan GEÇMEZ (regresyon 0).
        # ⚠️ Biçim SATIR İÇİ yazılır, PAYLAŞILAN CSS bloğuna kural EKLENMEZ: ortak stil
        # her ürün sayfasına basıldığı için oraya tek satır eklemek 15.930 özel üretim
        # sayfasının BAYTINI değiştirirdi (regresyon bütçesi sha256 ile ölçülüyor).
        opsiyonlar_html = ("""
    <div class="opsiyonlar" id="opsiyonlar">
      {adet}
      {fiyat_blok}
      <div class="sinif-beyan" id="sinifBeyan" style="margin-top:10px;font-size:13px;line-height:1.5;color:var(--gray-text)">{beyan}</div>
    </div>
    """).format(adet=ADET_IKON_HTML % (
                    ADET_EN_AZ, ADET_EN_COK,
                    IKON_BUTONLAR_HTML % (esc(pid), esc(wa_href(p, url)))),
                fiyat_blok=fiyat_satiri(
                    eski_html,
                    '<div class="opsiyon-fiyat" id="opsiyonFiyat">%s</div>' % esc(price_text)),
                beyan=esc(BEYAN["SAYFA_HAZIR"]))
        price_html = ""
    elif sema:
        # Konfigüratör: müşteri ölçü/parametre girer, hacim + fiyat canlı hesaplanır
        # (jenerator/hacim.js + jenerator/konfigurator.js). Kategoriden bağımsız —
        # sarı seride malzeme/renk seçimi de müşteride. tabanFiyatTL=null iken
        # fiyat "—" kalır (Okan taban fiyatları verene kadar altyapı hazır bekler).
        # 3D onizleme blogu — yalniz bayrak acik + pilot ailedeyse basilir.
        onizleme_html = ""
        if ONIZLEME_3D_ACIK and pid in ONIZLEME_AILELER:
            onizleme_html = """
      <div class="onizleme3d">
        <button type="button" id="onizleBtn" style="background:#12294d;color:#fff;border:0;border-radius:8px;padding:10px 18px;font-size:15px;cursor:pointer">Önizle (3D)</button>
        <div id="onizlemeKutu" hidden style="margin-top:10px">
          <canvas id="onizlemeTuval" style="width:100%;height:320px;display:block;border-radius:8px;background:#f4f6f8;border:1px solid #dde3ea"></canvas>
          <div id="onizlemeDurum" style="font-size:13px;color:#5a6572;margin-top:6px;min-height:18px"></div>
        </div>
      </div>"""
        # F kalemi (Okan, 16 Tem gece): sari sayfa secici duzeni NORMAL (kart-secim)
        # sayfayla birebir — malzeme asagidaki filament KARTLARINDAN (filament_html,
        # ayni bilesen), renk CIP butonlari, adet -/+ satirinda IKON butonlar (Sepete
        # Ekle + WhatsApp USTTE). Dropdown ve sayfa-alti buyuk butonlar KALKTI.
        # Ikinci kopya YOK: _renk_butonlari_html / ADET_IKON_HTML / IKON_BUTONLAR_HTML
        # kart-secim daliyla AYNI fonksiyon/sabitlerdir.
        # Sari fiyat paketi: taban fiyati DOLU ailede JS oncesi metin de kart-secim
        # kalibi ("X TL'den baslayan" — varsayilan olculerde fiyat = taban, JS kurusla
        # ayni degeri tazeler); taban null (vida) ise "Olcuye ozel fiyat" surer.
        # 🔴 SATIS KAPISI KAPALI AILE: taban fiyat DOLU olsa bile "X TL'den başlayan"
        # BASILMAZ — o tutar bu ailede hicbir zaman hesaplanmiyor (parametrikFiyatKurus
        # null), sepet sunucuda reddediliyor. JS'siz/JS oncesi/crawler goruntusunde
        # musteriye OLMAYAN bir fiyat gosterilmesi bu sayfanin canli kusuruydu.
        # Metin secenekler.js'in `kurus == null` dalindan gelir (tek kaynak) -> JS
        # kostugunda ayni cumle yerinde kalir, metin "ziplamaz".
        taban_tl = sema.get("tabanFiyatTL")
        if aile_satis_kapali:
            konf_fiyat_metni = esc(FIYATSIZ_METIN)
        else:
            konf_fiyat_metni = ((taban_fiyat_metni(taban_tl) + BASLAYAN_SONEK_HTML)
                                if taban_tl is not None else "Ölçüye özel fiyat")
        opsiyonlar_html = ("""
    <div class="opsiyonlar konf" id="opsiyonlar">
      <div class="konf-baslik">Ölçülerinizi girin</div>
      <div id="konfAlanlar"></div>
      {onizleme}
      {malzeme}
      {renk}
      {adet}
      {hata}
      <div class="opsiyon-fiyat" id="opsiyonFiyat">{fiyat_metni}</div>
      <div class="konf-hacim" id="konfHacim"></div>
    </div>
    """).format(fiyat_metni=konf_fiyat_metni,
                onizleme=onizleme_html,
                malzeme=panel_malzeme_html(p),
                renk=_renk_butonlari_html(secili=VARSAYILAN_RENK),
                hata=SECIM_HATA_HTML,
                adet=ADET_IKON_HTML % (
                    ADET_EN_AZ, ADET_EN_COK,
                    IKON_BUTONLAR_HTML % (esc(pid), esc(wa_href(p, url)))))
        price_html = ""
    elif konfigur:
        # KONFIGUR (dekor konfigüratörü): (opsiyonel malzeme seçici) + renk butonları
        # (görsel değişimli) + boy kaydırıcısı + adet/ikon satırı. Kategoriden bağımsız
        # (pilot Dekorasyon). "malzemeler" alanı YOKSA malzeme PLA sabittir (seçici basılmaz,
        # geri uyumluluk); VARSA varsayılan malzeme önden seçili ve fiyatı çarpanla ölçekler.
        # JS öncesi fiyat = VARSAYILAN boy × VARSAYILAN malzeme TAM-TL fiyatı (/konfigur.js
        # aynı değeri tazeler, metin zıplamaz); renk seçimi fiyatı değiştirmez (standart renkler).
        _bm = konfigur["boyutMm"]
        _malzemeler = konfigur.get("malzemeler")
        _vm = konfigur.get("varsayilanMalzeme")
        _vm_katsayi = 1.0
        if _malzemeler:
            for _m in _malzemeler:
                if _m.get("ad") == _vm:
                    _vm_katsayi = float(_m.get("katsayi") or 1.0)
                    break
        _varsayilan_kurus = konfigur_fiyat_kurus(konfigur, _bm["varsayilan"], _vm_katsayi)
        _renk_gorselleri = {r: imgs[konfigur["renkGorselIndeks"][r]]
                            for r in konfigur["renkler"]}
        _boy_araligi = "%s–%s cm" % (_sayi_metni(_bm["min"] / 10.0),
                                     _sayi_metni(_bm["max"] / 10.0))
        _malzeme_html = _konfigur_malzeme_html(_malzemeler, _vm, p) if _malzemeler else ""
        _konf_baslik = ("Malzeme, renk ve boyutunu seçin" if _malzemeler
                        else "Rengini ve boyutunu seçin")
        _boy_not = ("%s %s arasında ayarlanabilir; fiyat seçtiğiniz boyut ve malzemeye göre "
                    "hesaplanır." % (_bm.get("etiket") or "Boy", _boy_araligi)) if _malzemeler \
            else ("%s %s arasında ayarlanabilir; fiyat seçtiğiniz boyuta göre hesaplanır."
                  % (_bm.get("etiket") or "Boy", _boy_araligi))
        opsiyonlar_html = ("""
    <div class="opsiyonlar konf" id="opsiyonlar">
      <div class="konf-baslik">{konf_baslik}</div>
      {malzeme}
      {renk}
      {boy}
      {adet}
      {hata}
      <div class="opsiyon-fiyat" id="opsiyonFiyat">{fiyat_metni}</div>
      <div class="konf-hacim">{boy_not}</div>
    </div>
    """).format(konf_baslik=esc(_konf_baslik),
                malzeme=_malzeme_html,
                hata=SECIM_HATA_HTML,
                renk=_renk_butonlari_html(konfigur["renkler"], _renk_gorselleri,
                                          secili=_konfigur_varsayilan_renk(konfigur)),
                boy=_konfigur_boy_html(konfigur),
                adet=ADET_IKON_HTML % (
                    ADET_EN_AZ, ADET_EN_COK,
                    IKON_BUTONLAR_HTML % (esc(pid), esc(wa_href(p, url)))),
                fiyat_metni=taban_fiyat_metni(_varsayilan_kurus / 100.0),
                boy_not=esc(_boy_not))
        price_html = ""
    elif fonksiyonel and not parametrik:
        # Kart-secim (Okan, 16 Tem): malzeme dropdown YOK — malzeme aşağıdaki filament
        # KARTLARINDAN seçilir. Burada yalnız Renk + Adet + fiyat kalır. Önden seçili
        # malzeme yok; fiyat, seçim yapılana kadar "…'den başlayan" (taban PLA) gösterir.
        boy_html = ""
        if boy_secenekleri:
            boy_opts = "".join(
                '<option value="%s">%s%s</option>' % (
                    esc(b.get("etiket") or ""), esc(b.get("etiket") or ""),
                    (" (+%d TL)" % b["fark_tl"]) if b.get("fark_tl") else "")
                for b in boy_secenekleri)
            boy_html = ('<div class="opsiyon-row"><label for="boySec">Boy</label>'
                        '<select id="boySec">%s</select></div>' % boy_opts)
        # JS öncesi/JS'siz görünüm: fiyatlı üründe taban "…'den başlayan" (JS kuruşlu tazeler).
        # 🔴 ÖN-SEÇİM AÇIKKEN "başlayan" YOK: malzeme+renk zaten seçilidir, JS ilk render'da
        # KESİN tutarı yazar. Statik metin liste fiyatında bırakılsaydı sayfa açılışta düşük
        # tutar gösterip saniyesinde yükseltirdi (JS'siz istemcide ise hiç düzelmezdi) —
        # ilan edilen tutar ile sepete yazılan tutar ayrışırdı. İki metin de TEK sayıdan
        # (ilan_kurus -> on_secim_malzeme) türer.
        _ilan_k = ilan_kurus(p)
        if ONERI_ONSECIM_ACIK and _ilan_k is not None:
            baslangic_fiyat = esc(taban_fiyat_metni(_ilan_k / 100.0))
        else:
            baslangic_fiyat = (esc(fiyat) + BASLAYAN_SONEK_HTML) if fiyat else esc(price_text)
        opsiyonlar_html = ("""
    <div class="opsiyonlar" id="opsiyonlar">
      {malzeme}
      {renk}
      {boy}
      {adet}
      {hata}
      {fiyat_blok}
    </div>
    """).format(malzeme=panel_malzeme_html(p),
                renk=_renk_butonlari_html(secili=VARSAYILAN_RENK), boy=boy_html,
                hata=SECIM_HATA_HTML,
                adet=ADET_IKON_HTML % (
                    ADET_EN_AZ, ADET_EN_COK,
                    IKON_BUTONLAR_HTML % (esc(pid), esc(wa_href(p, url)))),
                fiyat_blok=fiyat_satiri(
                    eski_html,
                    '<div class="opsiyon-fiyat" id="opsiyonFiyat">%s</div>' % baslangic_fiyat))
        price_html = ""
    elif fonksiyonel:
        # Parametrik ama şemasız (bugün böyle ürün YOK — 18/18 şemalı) fonksiyonel ürün için
        # güvenli geri dönüş: eski malzeme dropdown'lu düzen aynen korunur.
        boy_html = ""
        if boy_secenekleri:
            boy_opts = "".join(
                '<option value="%s">%s%s</option>' % (
                    esc(b.get("etiket") or ""), esc(b.get("etiket") or ""),
                    (" (+%d TL)" % b["fark_tl"]) if b.get("fark_tl") else "")
                for b in boy_secenekleri)
            boy_html = ('<div class="opsiyon-row"><label for="boySec">Boy</label>'
                        '<select id="boySec">%s</select></div>' % boy_opts)
        opsiyonlar_html = ("""
    <div class="opsiyonlar" id="opsiyonlar">
      {malzeme_renk}
      {boy}
      {adet}
      <div class="opsiyon-fiyat" id="opsiyonFiyat">{fiyat_metni}</div>
    </div>
    """).format(malzeme_renk=_malzeme_renk_html(p, url), boy=boy_html,
                adet=ADET_HTML % (ADET_EN_AZ, ADET_EN_COK),
                fiyat_metni=esc(price_text))
        price_html = ""
    else:
        opsiyonlar_html = ""
        price_html = fiyat_satiri(
            eski_html,
            '<div class="price%s">%s</div>' % ("" if fiyat else " empty", esc(price_text)))

    # --- eylem butonları (madde 7): kart-seçim sayfasında İKONLAR Adet satırında (yukarıda
    # opsiyonlar_html'e basıldı) -> sayfa altına buton BASILMAZ; diğer sayfalarda (parametrik
    # konfigüratör, şemasız fonksiyonel, panelsiz Dekorasyon/Oyun-Hobi) büyük butonlar yerinde.
    # F kalemi: SEMALI parametrik (sari) sayfa da kart-secim modunda — malzeme
    # filament kartlarindan, butonlar Adet satirinda (sayfa altina buton basilmaz).
    # Buyuk butonlar yalniz semasiz-fonksiyonel (bugun urun yok) + panelsiz sayfalarda.
    # KONFIGUR sayfası KART_SECIM JS bayrağını AÇMAZ (malzeme kartı seçimi yok — o akışın
    # "malzeme seçilmeden ekleme" kilidi konfigur'da yanlış tetiklenirdi); ikon düzeni
    # (Adet satırında sepet+WA ikonu, sayfa altında büyük buton YOK) yine kullanılır.
    # 🔴 FIZIKSEL URUNDE KART_SECIM KAPALI OLMALI: acik kalsaydi sayfa scripti "malzeme+renk
    # secilmeden sepete eklenemez" kilidini uygular, ama secilecek cip/buton BASILMADIGI icin
    # seciliMalzeme/seciliRenk sonsuza kadar bos kalir -> SEPETE EKLE BUTONU SESSIZCE HICBIR
    # SEY YAPMAZ (titret(null) da no-op). Kapaliyken currentSatir bosSatir varsayilanlarini
    # (PLA/Siyah) kullanir -> tutar liste fiyatinin TA KENDISI, +%15 carpani yok.
    kart_secim = (not fiziksel) and (
        bool(sema) or (fonksiyonel and not parametrik and not konfigur))
    if kart_secim or konfigur or fiziksel:
        eylem_butonlar_html = ""
    else:
        eylem_butonlar_html = BUYUK_BUTONLAR_HTML % (esc(pid), esc(wa_href(p, url)))

    # --- ilgili ürünler (aynı kategori, kendisi hariç, en fazla 8)
    rel = [x for x in all_products
           if x.get("kategori") == kategori and x["id"] != pid][:8]
    # Bolum basligi ("Diğer <X> ürünleri") MUSTERIYE GORUNUR -> gorunur etiket.
    rel_baslik = gorunur_kat
    # YEDEK HAVUZ: ince alt-seride (Skan Art) aynı kategoriden REL_EN_AZ adet aday
    # çıkmıyorsa akraba ana kategoriden doldur — yoksa bölüm hiç basılmaz ve sayfa
    # TÜM iç linklerini kaybeder (ölçüldü: 8 -> 0). Eşlemesi olmayan kategori etkilenmez.
    akraba = AKRABA_KATEGORI.get(kategori)
    if akraba and len(rel) < REL_EN_AZ:
        varolan = {x["id"] for x in rel}
        rel = (rel + [x for x in all_products
                      if x.get("kategori") == akraba and x["id"] != pid
                      and x["id"] not in varolan])[:8]
        rel_baslik = akraba
    rel_html = ""
    if rel:
        cards = []
        for r in rel:
            rimgs = images_of(r)
            # 🔴 ESKIDEN: `rimgs[0] if rimgs else cover` — gorseli olmayan komsu urunun
            # karti BU SAYFANIN kapagiyla basiliyordu. Yani "B urunu" yazan, B'nin
            # sayfasina giden bir kartta A urununun FOTOGRAFI goruluyordu. Kirik gorselden
            # BETER: musteri yanlis parcayi siparis edebilir ve hata tamamen sessizdir.
            # Simdi: komsunun KENDI kategorisinin yer tutucusu (ana sayfa kartiyla ayni).
            rcov = rimgs[0] if rimgs else placeholder_data_uri(r.get("kategori") or "")
            rfiyat = (r.get("fiyat") or "").strip()
            rprice = ('<div class="rel-price">%s</div>' % esc(rfiyat)) if rfiyat else ""
            cards.append(
                '<a class="rel-card" href="%s">'
                '<img class="rel-img" src="%s" alt="%s" loading="lazy" '
                'width="400" height="300">'
                '<div class="rel-body"><div class="rel-title">%s</div>%s</div></a>'
                % (product_url(r["id"]), esc(rcov), esc(r.get("baslik") or ""),
                   esc(r.get("baslik") or ""), rprice))
        rel_html = (
            '<section class="related"><h2>Diğer %s ürünleri</h2>'
            '<div class="rel-grid">%s</div></section>'
            % (esc(rel_baslik), "".join(cards)))

    title_tag = esc(baslik) + " — PRUVO Özel Tasarım Yedek Parça"

    # --- JS'e (opsiyonlar bloğu + fiyat hesabı) aktarılacak ürün verisi
    # fid = KATALOG kimligi (feed g:id ile TEK KAYNAK: feed_id). Piksel content_ids DAIMA bunu
    # gonderir -> Meta/Google katalogdaki id ile birebir eslesir. id (TAM pid) API/D1 anahtari
    # olarak KALIR (Worker fiyati pid'den okur); fid yalniz olcum/katalog eslemesi icindir.
    # `tur`: YALNIZ fiziksel üründe basılır (hazır ticari mal). secenekler.js satirOzeti bunu
    # okuyup malzeme/renk çarpanını 1,00'e sabitler — sayfa scripti ile Worker AYNI kuralı AYNI
    # fonksiyondan alır, ikinci tanım yok. Alan `tur`süz 15.930 üründe HİÇ basılmaz -> o
    # sayfalar bayt-bayt bugünküyle aynı kalır (regresyon 0).
    _urun_veri = {"id": pid, "fid": feed_id(pid), "baslik": baslik, "kategori": kategori,
                  "fiyat": fiyat, "parametrik": parametrik, "boy_secenekleri": boy_secenekleri}
    if fiziksel:
        _urun_veri["tur"] = "fiziksel"
    urun_json = json.dumps(
        _urun_veri,
        ensure_ascii=False, separators=(",", ":")).replace("</script>", "<\\/script>")

    # --- Meta Pixel ViewContent (rıza-kapılı, YALNIZ ürün sayfası). content_ids = feed_id(pid)
    # (feed g:id ile TEK KAYNAK -> katalog eşleşmesi %100; uzun pid'de TAM pid feed'de kısaltıldığı
    # için katalog eşleşmez -> DAİMA feed_id gönder); content_type "product"; currency "TRY"; value
    # SAYI (sabit fiyat varsa), parametrik/fiyatsız üründe value yok. pruvoMetaTrack rıza yoksa yutar.
    mvc = {"content_ids": [feed_id(pid)], "content_type": "product", "currency": "TRY"}
    _vc_fiyat = price_number(fiyat)
    if _vc_fiyat:
        mvc["value"] = int(_vc_fiyat)
    mvc_json = json.dumps(mvc, ensure_ascii=False, separators=(",", ":")
                          ).replace("</script>", "<\\/script>")
    # --- GA4 view_item (rıza-kapılı) — Meta ViewContent ile AYNI noktadan, AYNI kaynak
    # degerlerden (feed_id(pid) / baslik / kategori / price_number(fiyat)) turer. Ikinci bir
    # huni tanimlanmaz ([[ikiz-tanim-sessiz-ayrisma]]): item_id DAIMA feed_id, yani Meta
    # content_ids ile birebir ayni kimlik. Kisisel veri YOK (yalniz katalog alanlari).
    gvi_kalem = {"item_id": feed_id(pid), "item_name": baslik,
                 "item_category": kategori, "quantity": 1}
    gvi = {"currency": "TRY", "items": [gvi_kalem]}
    if _vc_fiyat:
        gvi["value"] = int(_vc_fiyat)
        gvi_kalem["price"] = int(_vc_fiyat)
    gvi_json = json.dumps(gvi, ensure_ascii=False, separators=(",", ":")
                          ).replace("</script>", "<\\/script>")
    meta_view_content = (
        '<script>\n'
        'if(typeof window.pruvoMetaTrack==="function"){ window.pruvoMetaTrack("ViewContent", '
        + mvc_json + '); }\n'
        'if(typeof window.pruvoGA4Track==="function"){ window.pruvoGA4Track("view_item", '
        + gvi_json + '); }\n</script>')

    # Konfigüratör şeması sayfaya inline gömülür (tek kaynak jenerator/urunler/<id>.json,
    # build her push'ta yeniden gömer); hacim fonksiyonları ise /jenerator/hacim.js'ten
    # AYNI DOSYA olarak yüklenir (kopya yasak — kabul testi #4).
    sema_json = "null"
    konf_scripts = ""
    onizleme_js = ""
    if sema:
        sema_json = json.dumps(sema, ensure_ascii=False, separators=(",", ":")
                               ).replace("</script>", "<\\/script>")
        konf_scripts = ('<script src="/jenerator/hacim.js"></script>\n'
                        '<script src="/jenerator/konfigurator.js"></script>')
        if ONIZLEME_3D_ACIK and pid in ONIZLEME_AILELER:
            konf_scripts += '\n<script src="/jenerator/viewer.js"></script>'
            onizleme_js = ONIZLEME_JS

    # --- konfigur kancaları: konfigur OLMAYAN sayfada HEPSİ boş dize -> şablon çıktısı
    # bayt-bayt bugünkü gibi kalır (kabul: tools/konfigur-test.py). Konfigur sayfasında
    # inline URUN_KONFIGUR verisi + /konfigur.js modül kancaları basılır. Kanca değerleri
    # .format SONRASI yerleştirilir (yeniden işlenmez) -> tek süslü parantez güvenli.
    konfigur_tanim = ""
    konf_satir_hook = ""
    konf_fiyat_kosul = ""
    konf_render_hook = ""
    konf_klik_guard = ""
    konf_kur_hook = ""
    if konfigur:
        konf_scripts = '<script src="/konfigur.js"></script>'
        _konfigur_client = {
            "boyutMm": konfigur["boyutMm"],
            "hacim": konfigur["hacim"],
            "fiyatCapalari": konfigur["fiyatCapalari"],
        }
        konfigur_tanim = ("\nvar URUN_KONFIGUR = "
                          + json.dumps(_konfigur_client, ensure_ascii=False,
                                       separators=(",", ":")).replace("</script>", "<\\/script>")
                          + ";")
        konf_satir_hook = ("\n    if(URUN_KONFIGUR && window.PRUVO_KONFIGUR && "
                           "PRUVO_KONFIGUR.hazir()){ PRUVO_KONFIGUR.satiraYaz(s); }")
        konf_fiyat_kosul = " && !URUN_KONFIGUR"
        konf_render_hook = ("\n    if(URUN_KONFIGUR && window.PRUVO_KONFIGUR && "
                            "PRUVO_KONFIGUR.hazir()){ PRUVO_KONFIGUR.tazele(); }")
        # 🔴 Konfigur kolu da SESSIZ degildir (11 Agu): titreme + odak YETMEZ, gorunur
        # metin de basilir. Ayni sinif, ayni panzehir (kart-secim koluyla TEK kutu).
        konf_klik_guard = ("\n    /* Konfigur: renk seçilmeden sepete eklenemez "
                           "(titret + odakla + GÖRÜNÜR uyarı). */"
                           "\n    if(URUN_KONFIGUR && window.PRUVO_KONFIGUR && "
                           "!PRUVO_KONFIGUR.gecerliMi()){ PRUVO_KONFIGUR.eksikVurgula(); "
                           "hataGoster(\"Sepete eklemek için renk seçin.\"); return; }")
        konf_kur_hook = ("\n  if(URUN_KONFIGUR && window.PRUVO_KONFIGUR){ "
                         "PRUVO_KONFIGUR.kur(URUN_KONFIGUR, URUN, render); }")

    # PAYLASILAN JS: sayfaya gomulmez, icerik-adresli /varlik/urun-<hash>.js olur.
    # Kancalar burada (build zamani) doldurulur -> uretilen govde bugunkuyle BIREBIR ayni
    # baytlardir; yalniz sayfanin ICINDEN cikip kendi dosyasina tasinmistir.
    urun_js_url = varlik_adres("urun", "js", URUN_JS_SABLONU.format(
        konf_satir_hook=konf_satir_hook,
        konf_fiyat_kosul=konf_fiyat_kosul,
        konf_render_hook=konf_render_hook,
        konf_klik_guard=konf_klik_guard,
        konf_kur_hook=konf_kur_hook,
        onizleme_js=onizleme_js,
        whatsapp=WHATSAPP,
    ))

    doc = u"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{ga_head}
{meta_head}
{attribution_head}
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="icon" href="{favicon}">
<meta property="og:type" content="product">
<meta property="og:site_name" content="PRUVO">
<meta property="og:locale" content="tr_TR">
<meta property="og:title" content="{ogtitle}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
{og_image_meta}<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{ogtitle}">
<meta name="twitter:description" content="{desc}">
{tw_image_meta}<script type="application/ld+json">{product_ld}</script>
<script type="application/ld+json">{breadcrumb_ld}</script>
{stil}
</head>
<body>
<header>
  <div class="header-inner">
    <a class="brand-link" href="/">
      <div class="brand">PRUVO</div>
      <div class="brand-sub">Endüstriyel Parça Üretimi</div>
    </a>
    <a class="top-back" href="/">&larr; Tüm Ürünler</a>
  </div>
</header>

<section class="help-cta">
  <div class="help-cta-inner">
    <span class="help-cta-text">Aradığınız parçayı bulamadınız mı? <strong>Bizimle iletişime geçin, üretelim!</strong></span>
    <a class="help-cta-btn" href="{help_wa}" target="_blank" rel="noopener">{icon} <span class="wa-uzun">Bizimle </span>İletişime Geçin</a>
  </div>
</section>

<section class="info-strip">
  <div class="info-strip-inner">
    <p><strong>Model numarasını</strong> biliyorsanız gönderin, <strong>araştıralım</strong>; ya da <strong>parçanın bir eşini</strong> (kırık olsa da) gönderin, <strong>endüstriyel tarayıcıyla modelleyelim</strong>.</p>
  </div>
</section>

<main>
  <nav class="crumbs" aria-label="breadcrumb">
    <a href="/">Ana Sayfa</a><span>&rsaquo;</span>
    <a href="{katq}">{kategori}</a><span>&rsaquo;</span>
    {baslik}
  </nav>

  <div class="detail">
    <div class="gallery">
      {main_img}
      {thumbs}
    </div>
    <div class="info">
      <span class="cat">{kategori}</span>{altkat}{badge}
      <h1>{h1}</h1>
      {brands}
      {price}
      {opsiyonlar}
      {malzeme}{ozel_beyan}
      <div class="desc">{aciklama}</div>
      {eylem_butonlar}
    </div>
  </div>
</main>

{related}

<footer>
  PRUVO &mdash; Endüstriyel Parça Üretimi
  {foot_nav}
  {pay_band}
  {attribution}
</footer>

<a id="cartFab" class="cart-fab" href="/?sepet=1">{cart_icon}Sepetim (<span id="cartCount">0</span>)</a>

<button id="topBtn" class="top-btn" aria-label="Yukarı çık">
  <svg viewBox="0 0 24 24"><path d="M12 4.6 4.6 12l1.8 1.8 4.3-4.3V20h2.6V9.5l4.3 4.3 1.8-1.8z"/></svg>
</button>

<script src="/secenekler.js"></script>
{konf_scripts}
<script>
var URUN = {urun_json};
var URUN_SEMA = {sema_json};
var URUN_KART_SECIM = {kart_secim};{konfigur_tanim}
</script>
<script src="{urun_js}"></script>
{meta_view_content}
{ga_banner}
</body>
</html>
""".format(
        title=title_tag,
        desc=esc(desc160),
        url=esc(url),
        favicon=FAVICON,
        ogtitle=esc(baslik),
        # og:image / twitter:image — MUTLAK URL alanlari. Gorsel varsa satirlar (kendi
        # satir sonlariyla) bugunku HALIYLE basilir -> gorselli sayfa bayt-esit. Gorsel
        # yoksa satirlar HIC basilmaz: eskiden buraya 404 veren favicon.png yaziliyordu ve
        # WhatsApp/X onizlemesi kirik gorsel gosteriyordu. Alan yoksa paylasim karti
        # gorselsiz (metin) cizilir — dogru davranis. data: URI BURAYA KONMAZ (OG/Twitter
        # kaziyicilari data: semasini cekemez).
        og_image_meta=(('<meta property="og:image" content="%s">\n' % esc(paylasim_gorseli))
                       if paylasim_gorseli else ""),
        tw_image_meta=(('<meta name="twitter:image" content="%s">\n' % esc(paylasim_gorseli))
                       if paylasim_gorseli else ""),
        product_ld=ld(product_ld),
        breadcrumb_ld=ld(breadcrumb_ld),
        stil=stil_bloklari(),
        # GORUNEN yuzey (breadcrumb metni+linki, `.cat` rozeti) IC seri adini tasimaz.
        katq=esc(kategori_url(gorunur_kat)),
        kategori=esc(gorunur_kat),
        altkat=altkat_html,
        baslik=esc(baslik),
        main_img=main_img,
        thumbs=thumbs_html,
        h1=esc(baslik),
        brands=brand_html,
        price=price_html,
        opsiyonlar=opsiyonlar_html,
        badge=badge_html,
        aciklama=aciklama_html,
        wa=esc(wa_href(p, url)),
        help_wa=esc(help_cta_href(p, url)),
        icon=WA_ICON,
        pid=esc(p.get("id") or ""),
        cart_icon=CART_ICON,
        # Muhendislik-malzeme WA notu kartlarin altinda — malzeme dropdown'u kalan TEK
        # dal (semasiz-parametrik-fonksiyonel, bugun urun yok) haric her sayfada; o dalda
        # not zaten _malzeme_renk_html icinde, mukerrer basilmaz.
        # FIZIKSEL urun (hazir ticari mal): malzeme bolumu HIC basilmaz — filament cipleri,
        # "TAVSIYEMIZ" rozeti, muhendislik-malzeme (Karbon/ABS) WhatsApp notu ve govdedeki
        # "Malzeme Rehberi" linki bir boya kutusunu 3D baskiyla uretiyormus gibi gosteriyordu.
        # 🔴 KART_SECIM sayfasinda kartlar YUKARI TASINDI (panel_malzeme_html, 11 Agu):
        # asagida IKINCI kopya basilsaydi iki ayri #filCipler dogar, sayfa scripti
        # getElementById ile BIRINCISINE baglanirdi ve kullanicinin gordugu/tikladigi
        # kart secimi hicbir seye yazmazdi (sessiz arizanin ta kendisi). Burada yalniz
        # muhendislik-malzeme WA notu + "Malzeme Rehberi" linki kalir.
        malzeme=("" if fiziksel else
                 filament_html(p, wa_not=not (parametrik and fonksiyonel and not sema),
                               kartlar_gizli=bool(kart_secim
                                                  or (konfigur and konfigur.get("malzemeler"))))),
        # 🔴 SINIF BEYANI — OZEL URETIM KOLU (23.968 urun). Kosul `malzeme` ile AYNI:
        # "fiziksel ISE bos" (fail-closed yon — `tur` yoksa/taninmiyorsa urun OZEL
        # URETIMDIR). Hazir/stok kolunda BOS dizeye cozulur ve sablonda cevresinde
        # bosluk olmadigi icin `{ozel_beyan}` kaynakli bayt farki 943 hazir sayfada
        # SIFIRDIR. Hazir kolun beyani BEYAN["SAYFA_HAZIR"]'dir ve 11 Agu'da Okan'in
        # karariyla TEK CUMLEYE indirildi: panelde artik teslim suresi de 14 gunluk
        # cayma da YAZMAZ. Iki bilgi SILINMEDI — baglayici yasal govdede yerinde duruyor
        # (tools/sayfalar.py STOK_TESLIM_CUMLESI + mesafeli-satis m.5/teslimat-iade).
        # Kanonik "3-5 is gunu" artik YALNIZ OZEL kolun panel beyanindadir (kapi C6).
        # Nobet: tools/cayma-beyani-kapisi.py B ekseni (urun sayfasi) + C ekseni
        # (baglayici yasal govde) + E ekseni (tek kaynak). Tek tek iddia numarasi
        # YAZILMAZ: numaralar buyuyor ve burada bayatlayan bir liste, yanindaki
        # baglayici metne yalan soyleyen bir ikize donusuyor.
        ozel_beyan=("" if fiziksel else OZEL_TESLIM_BEYAN_HTML),
        related=rel_html,
        foot_nav=FOOT_NAV_HTML,
        pay_band=PAY_BAND_HTML,
        attribution=attribution_html(p),
        urun_json=urun_json,
        sema_json=sema_json,
        konfigur_tanim=konfigur_tanim,
        # konf_* kancalari + onizleme_js + whatsapp ARTIK SAYFADA DEGIL: paylasilan
        # JS govdesindeler (URUN_JS_SABLONU, yukarida doldurulur). Burada tekrar
        # verilmezler ki "hangi metin nerede uretiliyor" tek yerde kalsin.
        kart_secim=("true" if kart_secim else "false"),
        urun_js=urun_js_url,
        eylem_butonlar=eylem_butonlar_html,
        konf_scripts=konf_scripts,
        ga_head=GA_HEAD_SNIPPET,
        meta_head=META_HEAD_SNIPPET,
        meta_view_content=meta_view_content,
        # ATIF MODULU: gomulu DEGIL, paylasilan /varlik/atif-<hash>.js referansi.
        # Olcek kaldiracinin tamami burada: 21.185 sayfa x 10.718 bayt.
        attribution_head=attribution_varlik_head(),
        ga_banner=GA_BANNER_SNIPPET,
    )
    # script src'lerine ?v=<icerik-hash> (onbellek kirici) — tek yer, yayin=render.
    return surumle_scriptler(doc)


# ------------------------------------------------------------------ içerik/yasal sayfa
def render_content_page(slug, title, meta, body_html):
    title_tag = esc(title) + " — PRUVO"
    url = SITE + "/" + slug + "/"
    wa_mesaj = ("Merhaba, %s konusunda özel tasarım üretim için bilgi almak istiyorum."
                % title)
    wa_href = "https://wa.me/905451386526?text=" + _urlq(wa_mesaj, safe="")
    wa_cta = (
        '<aside class="landing-wa-cta" aria-label="WhatsApp ile iletişim">'
        '<p>Parçanızın fotoğrafını ve ölçülerini gönderin; birlikte değerlendirelim.</p>'
        '<a class="landing-wa-link" href="%s" target="_blank" rel="noopener">'
        'WhatsApp üzerinden bilgi alın</a></aside>' % esc(wa_href)
    )
    # surumle_scriptler: bugun icerik sayfalarinda site-ici <script src="/*.js"> YOK
    # (no-op), ama ileride eklenirse otomatik surumlensin diye tek yerden gecirilir.
    return surumle_scriptler(u"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{ga_head}
{meta_head}
{attribution_head}
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow">
<link rel="icon" href="{favicon}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="PRUVO">
<meta property="og:title" content="{ogtitle}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
{stil}
</head>
<body>
<header>
  <div class="header-inner">
    <a class="brand-link" href="/">
      <div class="brand">PRUVO</div>
      <div class="brand-sub">Endüstriyel Parça Üretimi</div>
    </a>
    <a class="top-back" href="/">&larr; Tüm Ürünler</a>
  </div>
</header>

<main class="content">
{body}
</main>

<footer>
  PRUVO &mdash; Endüstriyel Parça Üretimi
  {foot_nav}
  {pay_band}
</footer>
{pv_js}
{ga_banner}
{top_btn}
</body>
</html>
""".format(
        title=title_tag,
        desc=esc(meta),
        ogtitle=esc(title),
        url=esc(url),
        favicon=FAVICON,
        stil=stil_bloklari(),
        body=body_html + wa_cta,
        foot_nav=FOOT_NAV_HTML,
        pay_band=PAY_BAND_HTML,
        pv_js=PV_SCRIPT_HTML,
        ga_head=GA_HEAD_SNIPPET,
        meta_head=META_HEAD_SNIPPET,
        attribution_head=attribution_head_snippet(),
        ga_banner=GA_BANNER_SNIPPET,
        top_btn=TOP_BTN_BLOCK_HTML,
    ))


# ------------------------------------------------------------------ sitemap
def sitemap_tarihleri(products):
    """{url: 'YYYY-MM-DD'} — GERÇEK içerik-değişim tarihleri (tools/sitemap_damga.py).

    🔴 11 Ağu 2026'ya kadar burada `TODAY` basılıyordu: canlı sitemap'teki 26.696
    URL'in HEPSİ aynı `<lastmod>`'u taşıyordu, yani Google'a her gün "her şey
    bugün değişti" deniyordu (ölçüldü: benzersiz lastmod = 1; tarama isteklerinin
    %93'ü Refresh). Tarih artık git geçmişinden TÜRETİLİR; türetilemeyen URL'de
    `<lastmod>` etiketi HİÇ BASILMAZ (eksik lastmod, yanlış lastmod'dan iyidir).
    """
    url_tarih, tani = sitemap_damga.sitemap_tarihleri(
        products, product_url, sitemap_damga.defter_yolu(ROOT), ROOT,
        ana_sayfa_url=SITE + "/")
    print("sitemap lastmod: önbellekten %d · git'ten %d · çözülemedi %d "
          "(yürünen commit %d · %.1f sn · tavan aşıldı: %s · süre aşıldı: %s)"
          % (tani["defterden"], tani["gitten"], tani["cozulemedi"],
             tani["yurunen_commit"], tani["sure_sn"], tani["tavan_asildi"],
             tani["sure_asildi"]))
    return url_tarih


def render_sitemap(products, extra_urls=None, tarihler=None):
    urls = []
    urls.append((SITE + "/", "1.0", "daily"))
    for slug in SITEMAP_SLUGS:
        urls.append((SITE + "/" + slug + "/", "0.4", "monthly"))
    for p in products:
        urls.append((product_url(p["id"]), "0.8", "weekly"))
    # marka->model pilot URL'leri (build.py main -> marka_model_build.uret döndürür): her
    # marka + >=3-ürünlü model URL'i girer (spec §5, keşif kök-çözümü). Bu sayfalar ürün
    # KAYDINDAN türemediği için tarihleri de türetilemez -> lastmod'suz girerler.
    if extra_urls:
        urls.extend(extra_urls)
    if tarihler is None:
        tarihler = sitemap_tarihleri(products)
    items = []
    for loc, prio, freq in urls:
        tarih = tarihler.get(loc)
        # 🔴 Tarih BİLİNMİYORSA etiket hiç basılmaz — uydurma tarih YASAK.
        lastmod = ("    <lastmod>%s</lastmod>\n" % esc(tarih)) if tarih else ""
        items.append(
            "  <url>\n"
            "    <loc>%s</loc>\n"
            "%s"
            "    <changefreq>%s</changefreq>\n"
            "    <priority>%s</priority>\n"
            "  </url>" % (esc(loc), lastmod, freq, prio))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(items) + "\n</urlset>\n")


# ------------------------------------------------------------------ robots.txt
# Tarama bütçesi: parametreli URL'ler (`?kategori=`, `?marka=`, `?ara=`, `?sepet=`)
# ana sayfanın İSTEMCİ TARAFI filtreleridir; hepsi aynı HTML'i döndürür ve canonical
# ana sayfayı gösterir (ölçüldü 11 Ağu 2026: dördünde de `<link rel=canonical
# href="https://pruvo3d.com/">`). Google onları tarayıp kanonik yüzünden atıyor.
#
# ⚠️ EN BÜYÜK RİSK FAZLADAN KAPATMAK. Desenler bu yüzden SORGU'ya çıpalıdır: her biri
# `?` ya da `&` LİTERALİ ile başlar, dolayısıyla sorgusuz hiçbir yolu (kanonik ürün
# adresi `/urun/<id>/`, `/marka/...`, ana sayfa, `/sitemap.xml`) eşleyemez.
# `&` biçimi ÖLÇÜMLE eklendi: canlı iç linklerde parametre ikinci sırada da geçiyor
# (`/?kategori=Otomobil&marka=MX-5`) — yalnız `/*?marka=` yazılsaydı o URL AÇIK kalırdı.
ROBOTS_PARAMETRELERI = ("kategori", "marka", "ara", "sepet")


def render_robots():
    satirlar = ["User-agent: *", "Allow: /"]
    for ad in ROBOTS_PARAMETRELERI:
        satirlar.append("Disallow: /*?" + ad + "=")
        satirlar.append("Disallow: /*&" + ad + "=")
    satirlar += ["", "Sitemap: " + SITE + "/sitemap.xml", ""]
    return "\n".join(satirlar)


# ------------------------------------------------------------------ Google Merchant feed
def render_merchant_feed(products):
    """Google Merchant Center urun feed'i (RSS 2.0 + g: namespace).
    SADECE parametrik OLMAYAN, sabit sayisal fiyatli, gorseli olan urunler girer;
    parametrik "sari seri" (net fiyati yok) HARIC tutulur. Dondurulen (xml, adet)."""
    items = []
    for p in products:
        if p.get("parametrik"):
            continue                                   # sari seri -> feed disi
        price = feed_price(p.get("fiyat") if "fiyat" in p else "")
        if not price:
            continue                                   # net sayisal fiyati yok -> feed disi
        # 🔴 BESLEME = LISTE/KART YUZEYI (isletme karari, 11 Agu): besleme BASLANGIC
        # tabanini beyan eder ve KART kolunun anahtarina baglidir (ONERI_VITRIN_ACIK).
        # Urun sayfasinda onden secili malzeme yukselse bile besleme KAYMAZ.
        # ⚠️ BEYAN EDILEN RISK: besleme tutari ile acilan sayfanin vurgulanan tutari
        # ayrisabilir; karar Okan'in (yazili bildirilen risk). Azaltici: urun sayfasinda
        # taban tutar GORUNUR ve her malzeme cipi kendi tutarini data-kurus ile tasir.
        if ONERI_VITRIN_ACIK:
            price = ilan_tl_metni(vitrin_kurus(p)) or price
        imgs = images_of(p)
        if not imgs:
            continue                                   # gorselsiz urun feed'e girmez

        pid = p["id"]
        fid = feed_id(pid)                                 # feed kimligi <=50 karakter; URL/link TAM pid ile kalir
        url = product_url(pid)
        title = marka_temiz((p.get("baslik") or "").strip())[:150]
        desc = marka_temiz(re.sub(r"\s+", " ", (p.get("aciklama") or "")).strip())[:5000] or title
        kategori = p.get("kategori") or ""
        markalar = p.get("marka") or []

        row = [
            "    <g:id>%s</g:id>" % esc(fid),
            "    <title>%s</title>" % esc(title),
            "    <description>%s</description>" % esc(desc),
            "    <link>%s</link>" % esc(url),
            "    <g:image_link>%s</g:image_link>" % esc(feed_img(imgs[0])),
        ]
        for extra in imgs[1:11]:                        # Google en fazla 10 ek gorsel
            row.append("    <g:additional_image_link>%s</g:additional_image_link>" % esc(feed_img(extra)))
        row += [
            "    <g:availability>%s</g:availability>" % FEED_AVAILABILITY,
            "    <g:condition>new</g:condition>",
            "    <g:price>%s TRY</g:price>" % price,
            # Urunu BIZ uretiyoruz -> marka PRUVO (OEM uyum bilgisi baslik/product_type'ta).
            "    <g:brand>%s</g:brand>" % FEED_BRAND,
            "    <g:mpn>%s</g:mpn>" % esc(fid),          # GTIN yok; brand+mpn gecerli kimlik cifti
        ]
        gpc = GOOGLE_PRODUCT_CATEGORY.get(kategori)
        if gpc:
            row.append("    <g:google_product_category>%s</g:google_product_category>" % esc(gpc))
        ptype = kategori + (" > " + markalar[0] if markalar else "")
        if ptype:
            row.append("    <g:product_type>%s</g:product_type>" % esc(ptype))
        items.append("  <item>\n" + "\n".join(row) + "\n  </item>")

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">\n'
           '<channel>\n'
           '  <title>PRUVO — Özel Tasarım Üretim Yedek Parça</title>\n'
           '  <link>' + SITE + '</link>\n'
           '  <description>PRUVO özel tasarım üretim yedek parça ürün listesi.</description>\n'
           + "\n".join(items) + "\n</channel>\n</rss>\n")
    return xml, len(items)


# ------------------------------------------------------------------ ozet.json (FAZ 3)
# Ana sayfanın İLK BOYAMASI için gereken minimum veri. Bayrak (index.html EDGE_KATALOG)
# açıkken site 5-15 MB'lık urunler.json'u İNDİRMEZ; bunu indirir (~50 KB) ve gerisini
# Worker'dan sayfalı çeker. urunler.json üretilmeye/yayınlanmaya DEVAM eder (yedeklilik
# + dış tüketiciler); bu dosya onun YERİNE değil, YANINA gelir.
#
# İÇİNDEKİLER ve NEDEN: kategori sayıları (menü) · marka çipleri kategori kırılımıyla
# (index.html brandCounts() bunu activeCat'e göre hesaplıyordu — katalog inmeyince
# önceden hesaplanmış olmalı) · parametrik havuz (sarı vitrin: tamamı) · en yeni N kart
# (ilk ekran + Worker'a ulaşılamazsa yedek arama havuzu).
OZET_JSON = "ozet.json"
OZET_YENI = 48            # ilk ekran 24 (PAGE_SIZE) + "daha fazla" için 1 sayfa pay
OZET_ACIKLAMA_KES = 160   # Worker KART_ALANLARI substr(aciklama,1,160) ile AYNI olmalı
# 🔴 OZET_BUTCE — TEK KAYNAK (tools/faz3-yuk.js bu satırı REGEX ile OKUR, kendi kopyasını
# TUTMAZ; ikiz sabit sessizce ayrışırdı → [[ikiz-tanim-sessiz-ayrisma]]). BÜTÇE
# YÜKSELTİLEREK "çözülmez" (mimar kararı, 9 Ağu 2026): bu bir edge ilk-boyama iş paketi
# tavanıdır, katalog büyüdükçe elle yükseltmek aynı kırmızıyı bir sonraki partide geri
# getirir ([[envanter-drift-parti-basina]]). Aşım, kart değerlerini koruyan kayıpsız
# temsil sıkıştırmasıyla giderilir; kapı yine fail-closed HATA verir.
OZET_BUTCE = 150 * 1024   # iş paketi hedefi (bkz. asagida: bayrak kapaliyken UYARI, acikken HATA)
# İş paketi (paket-faz3-site-arama.md kabul 3): bayrak AÇIK ilk yük (index.html + ozet.json,
# görseller hariç) < 500 KB. tools/faz3-yuk.js bunu da build.py'den REGEX ile okur.
ILK_YUK_BUTCE = 500 * 1024
# ozet.json kartları sabit sıralı diziler olarak taşır; uzun alan adlarını her kartta
# tekrarlamaz. Alan adları artefaktın kendisinde TEK sözlük olarak bulunur ve istemci
# dizileri bu sözlüğe göre açar. Değerlerin tamamı korunur; yalnız temsil sıkıştırılır.
OZET_KART_ALANLARI = ("id", "baslik", "kategori", "marka", "fiyat", "gorsel",
                      "parametrik", "aciklama", "eski_fiyat", "tur",
                      "tavsiyeFilament", "konfigur")
# 🔴 ARTEFAKT SÜRÜMÜ — istemci sözleşmesi. v1 = sözlük kartları · v2 = sabit sıralı dizi ·
# v3 = dizi + görsel ortak öneki başlıkta (`gorselOnek`) + `yeni` kesiti havuz kartlarını
# ID ile REFERANSLAR (`yeniRef`). index.html ozetAc ÜÇÜNÜ DE açar (bayat tarayıcı
# önbelleği gerçektir). `_ozet_surum_dogrula` fail-closed kontrol eder: sürüm ile basılan
# alanlar ayrışırsa build KIRMIZI.
#
# 🔴 TEK KAYNAK TEMSİL BAYRAĞI — OKUYUCU ÖNCE, YAZICI SONRA (mimar kararı, 12 Ağu 2026).
# ÖLÇÜLDÜ: bayat tarayıcı önbelleğindeki ESKİ index.html yeni (v3) artefaktı alırsa boş
# kart çizmez ve fiyat/beyan bozulmaz, ama 223 kartın kapak URL'si kısa kalır ve yer
# tutucuya düşer. Bu pencere İKİ AŞAMALI YAYINLA tamamen kapanır — ikinci artefakta ve
# bayt kazancından vazgeçmeye GEREK YOK:
#   Yayın N   : v3'ü AÇABİLEN index.html çıkar, bu bayrak KAPALI kalır -> artefakt v2.
#               (Yeni istemci eski artefaktı zaten sorunsuz açıyor; kimse etkilenmez.)
#   Yayın N+1 : index.html tarayıcı önbelleği döndükten SONRA (≥4 saat,
#               [[tarayici-onbellek-4saat]]) bu sabit 3 yapılır -> artefakt v3, kazanç
#               (21.766 B) devreye girer, bayat istemci KALMADIĞI için kapak kaybı 0.
# Yordam + doğrulama komutu: tools/paket-ozet-butce.md "FAZ 2b".
# ⚠️ VARSAYILAN AÇIK (3) — bu AYRI ve BİLİNÇLİ bir yayındır. `--sadece-ozet` için
# `--ozet-surum <2|3>` YALNIZCA ölçüm/kabul testi kolu; yayın yolunu ETKİLEMEZ.
OZET_TEMSIL_SURUM = 3
# Kart kapak URL'lerinin ortak öneki. Kartta yalnız kalan parça taşınır; istemci öneki
# geri ekler. ÖNEKİ TAŞIMAYAN değer (başka konak) OLDUĞU GİBİ kalır — istemcinin ayrımı
# "://" içeriyor mu (mutlak = dokunma). Ölçüldü (11 Ağu, 271 kart): 34 B × 271 = 9.164 B.
OZET_GORSEL_ONEK = "https://media.pruvo3d.com/urunler/"
_OZET_I_GORSEL = OZET_KART_ALANLARI.index("gorsel")

# 🔴 `yeniRef` REFERANS YÜKLEMİ — index.html ile ORTAK JETON (12 Ağu 2026, çürütücü bulgusu).
# ÖLÇÜLDÜ: derleme "id None değil mi" (Python), istemci "k.id truthy mi" (JS) diye soruyordu.
# İki yüklem 8 senaryonun 5'inde ayrıştı ve ayrışma SESSİZDİ — build YEŞİL kalırken canlı
# `ozetAc` ya kartı düşürüyor (boş dize id) ya da Object.prototype'tan miras bir değeri karta
# koyuyordu (constructor/__proto__/toString/hasOwnProperty). Bugün katalogda böyle id 0/25.712
# ama id'ler DIŞ KAYNAKLI başlıklardan türüyor; "bugün 0" kalıcı garanti DEĞİLDİR.
#
# YÜKLEM: referans anahtarı = BOŞ OLMAYAN DİZE. Başka her şey referans DEĞİLDİR — o kart
# tele TAM olarak yazılır (kayıp yok), referans kısaltması UYGULANMAZ.
# TEK KAYNAK BAĞI: jeton index.html'de `var OZET_REF_YUKLEM = "...";` satırında YAŞAR;
# aşağıdaki `_index_ref_yuklemi_dogrula` her render_ozet çağrısında iki tarafın AYNI jetonu
# beyan ettiğini fail-closed ölçer. İstemci yüklemi değişip burası güncellenmezse build
# KIRMIZI yanar ([[ikiz-tanim-sessiz-ayrisma]]).
OZET_REF_YUKLEM = "bos-olmayan-dize"


def _ref_gecerli(v):
    """index.html `refGecerli` ile BİREBİR aynı yüklem (jeton: bos-olmayan-dize)."""
    return isinstance(v, str) and v != ""


def _index_ref_yuklemi_dogrula():
    """İstemcinin BEYAN ettiği referans yüklemi jetonu ile buradaki eşleşmeli."""
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        kaynak = f.read()
    m = re.search(r"var\s+OZET_REF_YUKLEM\s*=\s*\"([^\"]*)\"\s*;", kaynak)
    if not m:
        raise SystemExit("index.html'de OZET_REF_YUKLEM jetonu YOK — `yeniRef` referans "
                         "yuklemi tek kaynagi bozulmus (istemci ile derleme sessizce "
                         "ayrisabilir).")
    if m.group(1) != OZET_REF_YUKLEM:
        raise SystemExit("`yeniRef` REFERANS YUKLEMI AYRISTI: index.html %r diyor, build.py "
                         "%r uyguluyor. Iki taraf ayni soruya ayni cevabi VERMEK ZORUNDA."
                         % (m.group(1), OZET_REF_YUKLEM))


def kart_ozeti(p):
    """Worker /katalog + /ara yanıtındaki kartla AYNI şekil — site TEK kart çizici
    (index.html kartCiz) kullanır. Şekil ayrışırsa ozet.json'dan gelen kart ile
    Worker'dan gelen kart farklı görünürdü.

    ⚠️ SÖZLEŞME: buraya alan EKLENİRSE Worker'ın KART_ALANLARI'na da eklenmeli.
    Sepet fiyatını etkileyen alanlar (ör. `boy_secenekleri`, secenekler.js boyFarki)
    BURAYA DA girmeli: yoksa edge modunda sepet paneli boy farkını 0 sayar (sessiz fiyat
    sapması). Boy alanı aşağıda koşullu taşınır; kapısı tools/boy-secenekleri-kabul.py.

    🔴 `tur` (31 Tem / 1 Ağu) TAM DA O ALAN OLDU ve sözleşme İHLAL EDİLMİŞTİ: satirOzeti
    fiziksel üründe malzeme/renk çarpanını 1,00'e sabitler; kartta `tur` yoksa edge modunda
    panel bayat bir sepet satırını ×1,84 gösterip Worker liste fiyatını tahsil ediyordu
    (ölçüldü: international-micron-99-antifouling-boya-20lt → panel 15.842.400 krs, sunucu
    8.610.000 krs, fark 7.232.400 krs; 103 fiziksel üründe toplam 53.270.280 krs) ve panel
    "Malzeme: ASA (+%60) · Renk: turuncu (özel, +%15)" yazıp aynı şişik tutarı WhatsApp
    mesajına koyuyordu. Kapı: tools/edge-kart-kapisi.py (satirOzeti'nin OKUDUĞU alanları
    kaynaktan çıkarır, katalogda değer taşıyanları kartta ARAR).

    `tur` KOŞULLU basılır (eski_fiyat emsali): DEĞER TAŞIMAYAN üründe alan HİÇ yazılmaz.
    NEDEN koşullu: (a) ozet.json ~16k kartlık bir bütçe dosyasıdır (OZET_BUTCE) ve 15.930
    ürüne `"tur":""` yazmak ~130 KB'lık taşıyıcısız yük demektir; (b) SÖZLEŞME zaten
    fail-closed yönde yazılıdır — `tur` ALANI YOK == ÖZEL ÜRETİM (3D), tıpkı D1'deki `''`
    varsayılanı ve secenekler.js fizikselMi() gibi: yalnız TAM "fiziksel" dizesi hazır
    ticari mal demektir. Yani eksik alan hiçbir zaman "bilinmiyor" değil, "3D"dir ve
    okuyan taraf bugünkü davranışı uygular."""
    kart = {
        "id": p.get("id"),
        "baslik": p.get("baslik") or "",
        "kategori": p.get("kategori") or "",
        "marka": p.get("marka") or [],
        "fiyat": p.get("fiyat") or "",
        "gorsel": (p.get("gorseller") or [None])[0],
        "parametrik": bool(p.get("parametrik")),
        # Worker substr() ile kırpıyor (boşluk sadeleştirmiyor) — birebir aynısı.
        "aciklama": (p.get("aciklama") or "")[:OZET_ACIKLAMA_KES],
    }
    # ESKİ FİYAT (üstü çizili) — SADECE gösterim kuralını GEÇEN üründe ve SADECE o zaman
    # eklenir. NEDEN koşullu: (a) alan bugün hiçbir kayıtta yok -> ozet.json BAYT-EŞİT
    # kalır; (b) doğrulamayı derleme anında yapıp karta yalnız GEÇERLİ değeri koyduğumuz
    # için edge kartında olmayan `konfigur`/ham alanlara istemcinin ihtiyacı olmaz.
    # ⚠️ Worker (/katalog, /ara) KART_ALANLARI'nda bu alan YOK -> edge modunda Worker'dan
    # gelen kartta üstü çizili fiyat GÖRÜNMEZ (fail-closed: eksik alan = gösterme).
    # Worker tarafı HocA'nın düzlemi; KraL'a raporlandı.
    eski_metin, _ = eski_fiyat_gosterim(p)
    if eski_metin:
        kart["eski_fiyat"] = eski_metin
    # TİCARİ HAL — sepet FİYATINI ve BEYANINI etkiler (secenekler.js satirOzeti `urun.tur`u
    # okur). Yalnız TAM "fiziksel" değeri basılır; başka/boş değer HİÇ yazılmaz (yukarıdaki
    # sözleşme: alan yok = özel üretim). Bu satır düşerse tools/edge-kart-kapisi.py KIRMIZI.
    if p.get("tur") == "fiziksel":
        kart["tur"] = "fiziksel"
    # ÖN-SEÇİLİ MALZEME + ÖLÇÜYE ÖZEL KOL (11 Ağu) — ikisi de sepet FİYATINI/BEYANINI sürer:
    # secenekler.js `onSecimMalzeme` ürünün kendi malzeme önerisini (`urun.tavsiyeFilament`)
    # ön-seçer ve `urun.konfigur` taşıyan üründe ön-seçimi HİÇ uygulamaz (tutar tabandan canlı
    # hesaplanır); index.html `konfigurSatirMi` ise `urun.konfigur`u bayraksız ESKİ sepet
    # satırının yedek ekseni olarak okur. Kartta yoklarsa edge modunda panel başka malzeme
    # ön-seçip sunucudan FARKLI tutar gösterir ve konfigür satırı ödeme kapısını atlar.
    # Değer BİREBİR kopyalanır (normalize/kırpma/sıralama YOK) ve değer taşımayan üründe alan
    # HİÇ yazılmaz (`tur`/`eski_fiyat` emsali: ozet.json bir bütçe dosyasıdır). Bu iki satır
    # düşerse ya da değeri dönüştürürse tools/edge-kart-kapisi.py KIRMIZI yanar.
    if p.get("tavsiyeFilament"):
        kart["tavsiyeFilament"] = p.get("tavsiyeFilament")
    if p.get("konfigur"):
        kart["konfigur"] = p.get("konfigur")
    # Boy varyanti sepet fiyatini surer; edge kartinda yoksa boyFarki sessizce 0 olur.
    if p.get("boy_secenekleri"):
        kart["boy_secenekleri"] = p.get("boy_secenekleri")
    return kart


def ozet_karti_sikistir(kart, gorsel_onek=None):
    """Tam kart sözlüğünü kayıpsız, sabit sıralı dizi temsiline çevirir.

    Sondaki koşullu alanlar yoksa taşınmaz; aradaki boş konumlar ``None`` kalır. Böylece
    ``tur`` taşıyan kartta ``eski_fiyat`` konumu korunur ve istemci alanları kaydıramaz.

    ``gorsel_onek`` verilirse (v3) kapak URL'sinin ortak öneki DÜŞÜLÜR. Düşme YALNIZ
    değer önekle başlıyorsa ve KALAN BOŞ DEĞİLSE olur; kalan "://" taşırsa temsil
    çift-anlamlı olurdu → fail-closed (build KIRMIZI). Öneki taşımayan mutlak URL
    olduğu gibi kalır ve istemci ona dokunmaz.
    """
    son = max((i for i, alan in enumerate(OZET_KART_ALANLARI) if alan in kart), default=-1)
    dizi = [kart.get(alan) for alan in OZET_KART_ALANLARI[:son + 1]]
    if gorsel_onek and len(dizi) > _OZET_I_GORSEL:
        deger = dizi[_OZET_I_GORSEL]
        if isinstance(deger, str) and deger.startswith(gorsel_onek):
            kalan = deger[len(gorsel_onek):]
            if kalan and "://" not in kalan:
                dizi[_OZET_I_GORSEL] = kalan
            elif kalan and "://" in kalan:
                raise SystemExit("ozet.json gorsel oneki cift-anlamli deger uretti "
                                 "(kalan parca '://' tasiyor): %r" % (deger,))
    return dizi


def ozet_karti_ac(dizi, alanlar=None, gorsel_onek=""):
    """``ozet_karti_sikistir``ın TERSİ — dizi temsilini tam kart sözlüğüne çevirir.

    index.html ``ozetAc`` ile AYNI yüklem: 8'inci konumdan sonraki ``None`` değerler
    "alan yok" demektir (koşullu alanlar), önündekiler korunur; öneki geri ekleme
    yalnız BOŞ OLMAYAN ve "://" taşımayan dizede yapılır.
    """
    alanlar = list(alanlar or OZET_KART_ALANLARI)
    if not isinstance(dizi, list):
        return dizi
    kart = {}
    for i, deger in enumerate(dizi):
        if i < len(alanlar) and (i < 8 or deger is not None):
            kart[alanlar[i]] = deger
    g = kart.get("gorsel")
    if gorsel_onek and isinstance(g, str) and g and "://" not in g:
        kart["gorsel"] = gorsel_onek + g
    return kart


def ozet_temsil_ac(ozet):
    """Artefaktın TAMAMINI (v1/v2/v3) kart sözlüklerine geri açar — kayıpsızlık kanıtı
    ve Python tarafındaki tüketiciler (kabul testleri) için TEK kaynak.

    Dönen sözlük: {"parametrik": [...], "bloklar": {kat: [...]}, "yeni": [...]}.
    Çözülemeyen bir ``yeniRef`` referansı SESSİZCE atlanmaz — hata olarak döner
    (istemci tarafı onu BOŞ KART çizmemek için düşürür, build ise KIRMIZI yanar).
    """
    alanlar = ozet.get("kartAlanlari") or []
    onek = ozet.get("gorselOnek") or ""
    if not alanlar:                      # v1: kartlar zaten sözlük
        return {"parametrik": list(ozet.get("parametrik") or []),
                "bloklar": {k: list(v) for k, v in (ozet.get("bloklar") or {}).items()},
                "yeni": list(ozet.get("yeni") or []), "cozulemeyen": []}
    ac = lambda k: ozet_karti_ac(k, alanlar, onek)
    parametrik = [ac(k) for k in (ozet.get("parametrik") or [])]
    bloklar = {kat: [ac(k) for k in kartlar]
               for kat, kartlar in (ozet.get("bloklar") or {}).items()}
    havuz = {}
    for kart in parametrik + [k for liste in bloklar.values() for k in liste]:
        if isinstance(kart, dict) and _ref_gecerli(kart.get("id")):
            havuz.setdefault(kart["id"], kart)
    cozulemeyen = []
    if "yeniRef" in ozet:
        yeni = []
        for oge in (ozet.get("yeniRef") or []):
            # İSTEMCİ İLE AYNI ÜÇ KOL: dize = referans · dizi = tam kart · başka her şey
            # ne referans ne karttır. İstemci onu güvenle DÜŞÜRÜR (ve sayar); derleme
            # tarafında sessizce atlamak yerine ÇÖZÜLEMEYEN sayılır -> build KIRMIZI.
            if isinstance(oge, str):
                if _ref_gecerli(oge) and oge in havuz:
                    yeni.append(havuz[oge])
                else:
                    cozulemeyen.append(oge)
            elif isinstance(oge, list):
                yeni.append(ac(oge))
            else:
                cozulemeyen.append(oge)
    else:
        yeni = [ac(k) for k in (ozet.get("yeni") or [])]
    return {"parametrik": parametrik, "bloklar": bloklar, "yeni": yeni,
            "cozulemeyen": cozulemeyen}


def _temsil_konum_capasi(tel_dizileri, kartlar, alanlar, onek, etiket):
    """🔴 BAĞIMSIZ ÇAPA — telin her KONUMUNU kaynak kartın alan sözlüğüyle DOĞRUDAN kıyaslar.

    NEDEN AYRI BİR ÇAPA ([[anahat-referans-tautolojisi]], 12 Ağu 2026 çürütücü bulgusu):
    ``ozet_temsil_ac`` sıkıştırıcının İKİZİDİR. Sıkıştırıcı ile Python çözücüsü AYNI hatayı
    yaparsa (ölçüldü: kart dizisinde 2. ve 3. konumun — `kategori` ile `marka` — iki tarafta
    birden takas edilmesi) o karşılaştırma YEŞİL kalıyor, hatayı yalnız CANLI istemci kabul
    testi görüyordu. Bu çapa çözücüyü HİÇ ÇAĞIRMAZ: `dizi[i]` ile `kart[alanlar[i]]`i
    karşılaştırır, yani simetrik takas burada KIRMIZI yanar.

    Uyguladığı üç kural (istemcinin YAZILI sözleşmesi, çözücüden türetilmeden):
      * konum i alan sözlüğündeki i'nci alanın değerini taşır;
      * telin SONUNDAN kırpılan konumların alanı kartta BULUNMAMALIDIR (kayıp yok);
      * `gorsel` konumunda önek düşülmüşse ("://" taşımayan boş olmayan dize) geri
        eklendiğinde kaynak değeri vermelidir.
    """
    if len(tel_dizileri) != len(kartlar):
        raise SystemExit("ozet.json TEMSIL CAPASI (%s): tel %d kayit, kaynak %d kart — "
                         "kesit uzunlugu ayrisiyor." % (etiket, len(tel_dizileri), len(kartlar)))
    for sira, (dizi, kart) in enumerate(zip(tel_dizileri, kartlar)):
        if not isinstance(dizi, list):
            raise SystemExit("ozet.json TEMSIL CAPASI (%s #%d): tel kaydi dizi degil: %r"
                             % (etiket, sira, dizi))
        if len(dizi) > len(alanlar):
            raise SystemExit("ozet.json TEMSIL CAPASI (%s #%d): tel %d konum tasiyor, alan "
                             "sozlugu %d — fazla konumun karsiligi YOK."
                             % (etiket, sira, len(dizi), len(alanlar)))
        for i, alan in enumerate(alanlar):
            if i >= len(dizi):
                if alan in kart:
                    raise SystemExit("ozet.json TEMSIL CAPASI (%s #%d): `%s` alani kartta VAR "
                                     "ama tel %d konumda bitmis — DEGER TELDE KAYBOLDU."
                                     % (etiket, sira, alan, len(dizi)))
                continue
            tel = dizi[i]
            if (alan == "gorsel" and onek and isinstance(tel, str) and tel
                    and "://" not in tel):
                tel = onek + tel
            if tel != kart.get(alan):
                raise SystemExit("ozet.json TEMSIL CAPASI (%s #%d): konum %d `%s` — telde %r, "
                                 "kaynak kartta %r (KONUM/DEGER AYRISMASI)."
                                 % (etiket, sira, i, alan, dizi[i], kart.get(alan)))


def _ozet_surum_dogrula(ozet):
    """FAIL-CLOSED sürüm nöbetçisi — ``surum`` ile BASILAN ALANLAR birbirini tutmalı.

    İKİ YÖN de ölçülür:
      * v3 alanı var + ``surum`` < 3  -> bump DÜŞMÜŞ; bayat istemci yeni temsili sessizce
        yanlış çizerdi (mutasyon M-D bu satırı ölçer).
      * ``surum`` >= 3 ama v3 alanı yok -> etiket ile içerik ayrışmış; temsil bayrağı
        yarım uygulanmış demektir (yeni istemci alan varlığına bakar, sürüm etiketine
        DEĞİL; sessiz ayrışma burada durur)."""
    v3_alan = [a for a in ("gorselOnek", "yeniRef") if a in ozet]
    surum = ozet.get("surum", 0)
    if v3_alan and surum < 3:
        raise SystemExit("ozet.json v3 alani basildi (%s) ama surum=%r — SURUM BUMP "
                         "DUSMUS. Bayat istemci yeni temsili yanlis cizer."
                         % (", ".join(v3_alan), surum))
    if surum >= 3 and len(v3_alan) < 2:
        raise SystemExit("ozet.json surum=%r ama v3 alanlari EKSIK (%s) — temsil bayragi "
                         "yarim uygulanmis." % (surum, ", ".join(v3_alan) or "hicbiri"))


# ------------------------------------ ANA SAYFA VİTRİN HİYERARŞİSİ (Okan kuralı, 31 Tem)
# KURAL: filtresiz ana vitrin SLOT DÜZENİYLE çizilir — 4 Jeneratör · 80 Marin · 80 Otomobil ·
# gerisi karışık; her blok KENDİ İÇİNDE rastgele sıralanır.
#
# 🔴 SIRALAMA BURADA YAPILMAZ — build yalnız HAVUZ üretir. Neden: rastgelelik "her sayfa
# yenilemesinde farklı" olacak. Derleme anında sıralanırsa sıra DEPLOY BAŞINA sabitlenir
# (aynı ziyaretçi gün boyu aynı vitrini görür). Sıra istemcide, sayfa yüklemesi başına
# üretilen tek seed ile kurulur (index.html vitrinSirala). Bu dosyanın işi: her blok için
# `havuz` kadar aday kartı ozet.json'a koymak, ki tarayıcı 24 kartlık ilk boyamadan sonra
# 164 slotluk ön bloğu AĞA ÇIKMADAN dizebilsin.
#
# ESKİ KURAL (Ev/Dekorasyon/Ofis ilk 20 slotta görünmez) KALDIRILDI: yeni düzende ilk 164
# slot zaten Jeneratör/Marin/Otomobil olduğu için o üç kategori oraya giremez — kural
# YUTULDU. (vitrin-siralama-test.js bunu ayrı iddiayla ölçer, sessizce kaybolmasın.)
def _index_vitrin_kurali():
    """Blok kuralını index.html'deki TEK KAYNAKTAN oku (VITRIN_BLOKLAR).
    İkinci bir kopya, kuralın iki tarafta SESSİZCE ayrışması demekti: derleme bir havuz
    üretir, tarayıcı başka bir blok düzeni uygular, ekranda hata görünmezdi. Çapa
    bulunamaz ya da şema bozuksa FAIL-CLOSED (build kırmızı) — sessizce "kural yok"
    sayılmaz."""
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        kaynak = f.read()
    m = re.search(r"var\s+VITRIN_BLOKLAR\s*=\s*(\[[\s\S]*?\])\s*;", kaynak)
    if not m:
        raise SystemExit("index.html'de VITRIN_BLOKLAR bulunamadi "
                         "(vitrin kurali tek kaynagi bozulmus).")
    try:
        bloklar = json.loads(m.group(1))
    except ValueError as e:
        raise SystemExit("index.html VITRIN_BLOKLAR JSON olarak okunamadi: %s" % e)
    if not isinstance(bloklar, list) or not bloklar:
        raise SystemExit("index.html VITRIN_BLOKLAR bos/gecersiz.")
    for b in bloklar:
        for alan in ("kategori", "adet", "havuz", "kaynak"):
            if alan not in b:
                raise SystemExit("VITRIN_BLOKLAR kaydinda '%s' alani yok: %r" % (alan, b))
        if b["kaynak"] not in ("parametrik", "bloklar"):
            raise SystemExit("VITRIN_BLOKLAR kaynak degeri gecersiz: %r" % (b,))
    return bloklar


def render_ozet(products, temsil_surum=None):
    """ozet.json'u kayıpsız kart temsiliyle üretir; arama/vitrin havuzlarını kırpmaz.

    ``temsil_surum`` verilmezse TEK KAYNAK bayrağı (``OZET_TEMSIL_SURUM``) kullanılır.
    Parametre YALNIZCA ölçüm/kabul testi koludur (iki hâli de aynı koşumda ölçmek için);
    yayın yolu daima sabiti okur."""
    surum = OZET_TEMSIL_SURUM if temsil_surum is None else int(temsil_surum)
    if surum not in (2, 3):
        raise SystemExit("ozet temsil surumu gecersiz: %r (2 ya da 3 olmali)" % (surum,))
    # İki taraf "bu referans geçerli mi" sorusuna AYNI cevabı veriyor mu — bayrak KAPALI
    # iken de ölçülür: ayrışma, bayrak açıldığı gün değil BUGÜN kırmızı yanmalı.
    _index_ref_yuklemi_dogrula()
    kategoriler = {}
    markalar = {}          # {kategori: {marka: adet}} — global sayım = kategorilerin toplamı
    for p in products:
        k = p.get("kategori") or ""
        kategoriler[k] = kategoriler.get(k, 0) + 1
        kat_markalari = markalar.setdefault(k, {})
        for m in (p.get("marka") or []):
            kat_markalari[m] = kat_markalari.get(m, 0) + 1

    # BLOK HAVUZLARI (sıralama YOK — yukarıdaki gerekçe). Her blok için katalogun o
    # kategorideki ilk `havuz` ürünü (en yeni önce) ozet'e konur; tarayıcı seed'iyle
    # karıştırıp ilk `adet` kadarını çizer. havuz > adet olduğu için her yenilemede
    # farklı ürünler öne gelir.
    #
    # Kartlar (kart_ozeti) burada TEK SEFER hesaplanır; içerik ve sıra korunur.
    vitrin_bloklar = _index_vitrin_kurali()
    parametrik_kartlar = [kart_ozeti(p) for p in products if p.get("parametrik")]
    tam_havuzlar = {}    # kategori -> tam kart listesi (havuz_n0 kadar, ya da stok kadar)
    stoklar = {}
    havuz_n0 = {}        # VITRIN_BLOKLAR'da TANIMLI başlangıç havuz adedi
    for kural in vitrin_bloklar:
        if kural["kaynak"] == "parametrik":
            continue
        kat = kural["kategori"]
        havuz_n = int(kural["havuz"] or 0)
        aday = [p for p in products if (p.get("kategori") or "") == kat]
        stoklar[kat] = len(aday)
        tam_havuzlar[kat] = [kart_ozeti(p) for p in (aday[:havuz_n] if havuz_n else aday)]
        havuz_n0[kat] = len(tam_havuzlar[kat])

    yeni_kartlar = [kart_ozeti(p) for p in products[:OZET_YENI]]

    def _uret(havuz_boyut):
        """Verilen havuz adetleriyle ozet sözlüğünü (ve JSON metnini) kurar."""
        bloklar = {}
        blok_sapma = []
        yetersiz = False
        for kural in vitrin_bloklar:
            kat = kural["kategori"]
            adet = int(kural["adet"])
            if kural["kaynak"] == "parametrik":
                havuz_kartlar = parametrik_kartlar
                stok = len(parametrik_kartlar)
            else:
                n = havuz_boyut.get(kat, havuz_n0.get(kat, 0))
                havuz_kartlar = tam_havuzlar.get(kat, [])[:n]
                bloklar[kat] = havuz_kartlar
                stok = stoklar.get(kat, 0)
            if len(havuz_kartlar) < adet:
                yetersiz = True
            blok_sapma.append({"kategori": kat, "adet": adet,
                               "havuz": len(havuz_kartlar), "stok": stok})
        # --- TEMSİL (kayıpsız, bayrağa göre):
        #   v2 = sabit sıralı dizi, tam kapak URL'si, `yeni` kesiti TAM kartlar.
        #   v3 = + kapak öneki başlıkta (`gorselOnek`) + `yeni` kesiti havuz kartlarını
        #        ID ile referanslar (`yeniRef`). Referans YALNIZ kart BASILAN havuzlarda
        #        BİREBİR aynı temsille varsa verilir; yoksa TAM kart taşınır. Örtüşme bugün
        #        %100 ama yarın 0 olabilir (yeni ürün havuzsuz kategoriye düşerse) — iki hâl
        #        de aynı akışta çizilir.
        onek = OZET_GORSEL_ONEK if surum >= 3 else None
        sik = lambda k: ozet_karti_sikistir(k, onek)
        s_parametrik = [sik(k) for k in parametrik_kartlar]
        s_bloklar = {kat: [sik(k) for k in kartlar] for kat, kartlar in bloklar.items()}
        s_yeni = [sik(k) for k in yeni_kartlar]
        if surum >= 3:
            # REFERANS YALNIZ GEÇERLİ ANAHTARDA (`_ref_gecerli`: boş olmayan dize; istemci
            # ile ORTAK yüklem). Geçersiz/patolojik id taşıyan kart KISALTILMAZ, tele TAM
            # yazılır: kayıp yok ve istemci onu dizi olarak açar.
            havuz_dizin = {}
            for dizi in s_parametrik + [d for liste in s_bloklar.values() for d in liste]:
                if dizi and _ref_gecerli(dizi[0]):
                    havuz_dizin.setdefault(dizi[0], dizi)
            s_yeni = [(dizi[0] if (dizi and _ref_gecerli(dizi[0])
                                   and havuz_dizin.get(dizi[0]) == dizi) else dizi)
                      for dizi in s_yeni]
        # ANAHTAR SIRASI KORUNUR (bayrak KAPALI iken artefakt, bayraktan önceki v2 ile
        # BAYT BAYT aynı olmalı — "yayın N kimseyi etkilemez" iddiası buna dayanır).
        ozet = {"surum": surum, "kartAlanlari": list(OZET_KART_ALANLARI)}
        if surum >= 3:
            ozet["gorselOnek"] = OZET_GORSEL_ONEK
        ozet["uretim"] = TODAY
        ozet["toplam"] = len(products)
        ozet["kategoriler"] = kategoriler
        ozet["markalar"] = markalar
        # Sarı vitrin havuzu = Jeneratör bloğunun havuzu: parametrik ürünlerin TAMAMI.
        ozet["parametrik"] = s_parametrik
        # Blok havuzları (Marin, Otomobil, ...). Sıra istemcide kurulur.
        ozet["bloklar"] = s_bloklar
        # KARIŞIK kuyruk + Worker'a ulaşılamazsa yedek arama havuzu: katalogun ham başı
        # (en yeni ürünler). Vitrin sırası BURADA UYGULANMAZ (istemcinin işi).
        # v3'te ANAHTAR ADI DEĞİŞİR (`yeni` -> `yeniRef`): bayat istemci tanımadığı anahtarı
        # BOŞ görür ve kuyruğu çizmez; referans dizelerini karta çevirip BOŞ KART üretmez.
        ozet["yeniRef" if surum >= 3 else "yeni"] = s_yeni
        # Sapma ÖLÇÜLEBİLİR kalır (canlı doğrulama + kabul testi bunu okur).
        ozet["vitrin"] = {"yetersiz": yetersiz, "bloklar": blok_sapma,
                          "liste": len(products)}
        _ozet_surum_dogrula(ozet)
        # 🔴 KAYIPSIZLIK HER BUILD'DE İKİ AYRI ÇAPAYLA ÖLÇÜLÜR (fail-closed):
        #
        #  (1) KONUM ÇAPASI (`_temsil_konum_capasi`) — ÇÖZÜCÜYÜ ÇAĞIRMAZ; telin i'nci
        #      konumunu kaynak kartın i'nci ALANIYLA doğrudan kıyaslar. Sıkıştırıcı ile
        #      Python çözücüsünün AYNI hatayı paylaşması (simetrik takas) burada yakalanır.
        #  (2) GERİ AÇMA (`ozet_temsil_ac`) — çözücünün kendisini kartlarla kıyaslar;
        #      çözücüye ÖZGÜ hataları (yalnız açma tarafında olan kayma) yakalar.
        #
        # ⚠️ DÜRÜST SINIR: (2) sıkıştırıcının İKİZİDİR, tek başına simetrik hataya KÖRDÜR
        # (ölçüldü, 12 Ağu). "Her build'de fail-closed kayıpsızlık ölçülür" iddiası (1)
        # sayesinde ayakta durur. İstemci tarafının (index.html `ozetAc`) kendi doğruluğu
        # BURADA ölçülemez — onun bağımsız çapası tools/ozet-temsil-test.js'tir (CANLI
        # çözücüyü koşturur); ozet.json'un kart ALAN SÖZLEŞMESİ ise
        # tools/edge-kart-kapisi.py'dir (kartı bu telden geçirip canlı çözücüyle geri açar).
        _temsil_konum_capasi(s_parametrik, parametrik_kartlar,
                             OZET_KART_ALANLARI, onek, "parametrik")
        for _kat, _tel in s_bloklar.items():
            _temsil_konum_capasi(_tel, bloklar.get(_kat, []),
                                 OZET_KART_ALANLARI, onek, "bloklar/%s" % _kat)
        # `yeni` kesiti referans TAŞIYABİLİR: konum çapası için referansı telin KENDİ
        # havuzundan (artefaktın basılmış kartlarından) çözeriz — çözücü yine devrede DEĞİL.
        _tel_havuz = {}
        for _dizi in s_parametrik + [d for liste in s_bloklar.values() for d in liste]:
            if _dizi and _ref_gecerli(_dizi[0]):
                _tel_havuz.setdefault(_dizi[0], _dizi)
        _yeni_tel = []
        for _oge in s_yeni:
            if isinstance(_oge, list):
                _yeni_tel.append(_oge)
            elif _ref_gecerli(_oge) and _oge in _tel_havuz:
                _yeni_tel.append(_tel_havuz[_oge])
            else:
                raise SystemExit("ozet.json 'yeniRef' kaydi ne TAM KART ne de COZULEBILIR "
                                 "REFERANS: %r" % (_oge,))
        _temsil_konum_capasi(_yeni_tel, yeni_kartlar, OZET_KART_ALANLARI, onek, "yeni")
        geri = ozet_temsil_ac(ozet)
        beklenen = {"parametrik": parametrik_kartlar,
                    "bloklar": bloklar, "yeni": yeni_kartlar}
        if geri["cozulemeyen"]:
            raise SystemExit("ozet.json 'yeniRef' referansi havuzda COZULEMEDI: %s"
                             % ", ".join(map(str, geri["cozulemeyen"][:3])))
        if (geri["parametrik"] != beklenen["parametrik"]
                or geri["bloklar"] != beklenen["bloklar"]
                or geri["yeni"] != beklenen["yeni"]):
            raise SystemExit("ozet.json temsili KAYIPLI — geri acilan kartlar kart_ozeti "
                             "ciktisiyla ayrisiyor (v3 sikistirma bozuk).")
        return json.dumps(ozet, ensure_ascii=False, separators=(",", ":")), yetersiz, blok_sapma

    havuz_boyut = dict(havuz_n0)
    metin, yetersiz, blok_sapma = _uret(havuz_boyut)
    bayt = len(metin.encode("utf-8"))

    if yetersiz:
        print("UYARI: vitrin-sapma — blok havuzu YETERSIZ (%s); ilgili blok kisalir, "
              "bosluk birakilmaz."
              % ", ".join("%s %d/%d" % (b["kategori"], b["havuz"], b["adet"])
                          for b in blok_sapma))
    return metin


def _index_bayragi(ad):
    """index.html'deki TEK KAYNAK bayrağını oku (FAZ 3: EDGE_KATALOG)."""
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        kaynak = f.read()
    m = re.search(r"var\s+" + re.escape(ad) + r"\s*=\s*(true|false);", kaynak)
    if not m:
        raise SystemExit("index.html'de %s bayragi bulunamadi (FAZ 3 tek kaynagi bozulmus)." % ad)
    return m.group(1) == "true"


# ------------------------------------------------------------------ taban fiyat haritası
def uret_taban_fiyatlar():
    """taban-fiyatlar.js — ana sayfa sarı kartlarının "X TL'den başlayan" fiyatı buradan
    okur; kaynak jenerator/urunler/<id>.json tabanFiyatTL (TEK KAYNAK, elle kopya YOK —
    filament-veri.js deseni). tabanFiyatTL null/eksik olan şema haritaya GİRMEZ (kartta
    "Ölçüye özel fiyat" fallback'i). CI üretir, git'e girmez.

    🔴 SATIŞ KAPISI KAPALI AİLE (2026-08-04, ölçülen canlı kusur — ürün SAYFASI yüzeyi
    476fac2a ile kapanmıştı, KART yüzeyi açık kalmıştı): hacmi doğrulanmamış ailede
    parametrikFiyatKurus **null** döner ve Worker sepeti 400 `hacim-dogrulanmamis` ile
    reddeder; yani o ürün BUGÜN SATILAMAZ. Buna rağmen ana sayfa sarı kartı taban
    fiyattan türetilmiş "X TL'den başlayan" gösteriyordu = müşteriye satılmayacak bir
    tutar beyanı. Kapalı ailenin id'si haritaya HİÇ GİRMEZ (kart sayısal tutar
    üretemez — sayı taşıyıcısı burasıdır) ve ayrıca `PRUVO_SATIS_KAPALI` ile
    işaretlenir; kart o id'de ürün sayfasıyla AYNI cümleyi (`PRUVO_FIYATSIZ_METIN`,
    tek kaynak secenekler.js `kurus == null` dalı) basar.
    Karar aile_satis_kapali_mi()'den gelir — ikinci kural kopyası YOK."""
    harita = {}
    kapali = {}
    if os.path.isdir(JEN_URUN_DIR):
        for ad in sorted(os.listdir(JEN_URUN_DIR)):
            if not ad.endswith(".json"):
                continue
            with open(os.path.join(JEN_URUN_DIR, ad), encoding="utf-8") as f:
                sema = json.load(f)
            pid = sema.get("id") or ad[:-5]
            if aile_satis_kapali_mi(sema):
                kapali[pid] = 1
                continue
            taban = sema.get("tabanFiyatTL")
            if taban is not None:
                harita[pid] = taban
    with open(os.path.join(ROOT, "taban-fiyatlar.js"), "w", encoding="utf-8") as f:
        f.write("/* Sayfa ureteci uretir — ELLE DUZENLEME. "
                "Tek kaynak: jenerator/urunler/<id>.json tabanFiyatTL */\n"
                "window.PRUVO_TABAN_FIYATLAR = "
                + json.dumps(harita, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
                + ";\n"
                "/* Satisa KAPALI (hacmi dogrulanmamis) aileler — kart sayisal tutar "
                "BASMAZ, asagidaki cumleyi basar. */\n"
                "window.PRUVO_SATIS_KAPALI = "
                + json.dumps(kapali, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
                + ";\n"
                "window.PRUVO_FIYATSIZ_METIN = "
                + json.dumps(FIYATSIZ_METIN, ensure_ascii=False)
                + ";\n")
    return harita


# ------------------------------------------------------------------ marka->model pilot ctx
def marka_model_ctx():
    """marka_model_build.uret'e verilen yardımcı/sabit sözlüğü (döngüsel import olmadan;
    modül build.py'yi import ETMEZ, gereken her şeyi buradan alır)."""
    return {
        "ROOT": ROOT, "SITE": SITE, "TODAY": TODAY,
        "esc": esc, "surumle_scriptler": surumle_scriptler,
        "product_url": product_url, "FAVICON": FAVICON,
        # PAGE_CSS ham metni HALA verilir (kardes modul kendi kurallarini onun uzerine
        # yaziyor olabilir); stil YUZEYI ise TEK KAYNAK stil_bloklari'ndan gelir.
        "PAGE_CSS": PAGE_CSS, "stil_bloklari": stil_bloklari,
        "varlik_adres": varlik_adres, "FOOT_NAV_HTML": FOOT_NAV_HTML,
        "PAY_BAND_HTML": PAY_BAND_HTML, "PV_SCRIPT_HTML": PV_SCRIPT_HTML,
        "GA_HEAD_SNIPPET": GA_HEAD_SNIPPET, "META_HEAD_SNIPPET": META_HEAD_SNIPPET,
        "attribution_head_snippet": attribution_head_snippet,
        "GA_BANNER_SNIPPET": GA_BANNER_SNIPPET,
        # Standart katalog kartı (kartCiz) için: görsel + parametrik taban fiyatı
        "images_of": images_of, "konf_sema": konf_sema,
        "taban_fiyat_metni": taban_fiyat_metni,
        # "X TL'den başlayan" kararı + eki TEK KANONİK NOKTA (secenekler.js kaynaklı).
        # Kardeş modül ikinci bir dize/koşul TUTMAZ; ayrışma sessiz olurdu.
        "kart_tutar_metni": kart_tutar_metni, "BASLAYAN_SONEK": BASLAYAN_SONEK,
        # SATIŞ KAPISI — SSR kart da ana sayfa kartıyla AYNI kararı kullanır
        # (ikiz tanım sessizce ayrışmasın): kapalı ailede sayısal tutar basılmaz,
        # yerine ürün sayfasıyla aynı cümle (FIYATSIZ_METIN) gösterilir.
        "aile_satis_kapali_mi": aile_satis_kapali_mi, "FIYATSIZ_METIN": FIYATSIZ_METIN,
        # Yukarı-çık oku TEK KAYNAK (build.py) — marka/model + hub şablonu kopyalamaz, buradan alır.
        "TOP_BTN_BLOCK_HTML": TOP_BTN_BLOCK_HTML,
    }


# ------------------------------------------------------------------ ana akış
def main():
    # --sadece-taban: yalnız taban-fiyatlar.js'i üret (kabul testi hızlı koşsun;
    # tam build 6900+ sayfa yazar). Deploy yine main()'in tamamını koşar.
    if "--sadece-taban" in sys.argv[1:]:
        harita = uret_taban_fiyatlar()
        print("OK: taban-fiyatlar.js uretildi (%d urun)." % len(harita))
        return

    # --sadece-ozet: yalnız ozet.json'u üret. NEDEN VAR: index.html EDGE_KATALOG=true
    # iken ana sayfanın ilk boyaması bu artefakta BAĞIMLI; jenerator/test/vitrin-kabul.js
    # onu üretip sahte fetch'e servis ediyor. Özetin ŞEKLİ tek kaynakta (render_ozet)
    # kalsın diye test kendi kopyasını hesaplamıyor, bu bayrağı çağırıyor. Bütçe kapısı
    # burada KOŞMAZ (tam build'in işi) — bu bayrak sadece artefaktı yazar.
    # --katalog/--cikti: girdi katalogu ve çıktı yolu değiştirilebilir. NEDEN: vitrin
    # sıralama kabul testi ozet'i SENTETİK fikstür üzerinde GERÇEK build koduyla üretir
    # (kendi kopyasını hesaplamaz) ve bunu yaparken depodaki ozet.json'u EZMEZ.
    if "--sadece-ozet" in sys.argv[1:]:
        def _arg(ad, varsayilan):
            i = sys.argv.index(ad) if ad in sys.argv else -1
            return sys.argv[i + 1] if 0 <= i < len(sys.argv) - 1 else varsayilan
        _katalog = _arg("--katalog", JSON_PATH)
        _cikti = _arg("--cikti", os.path.join(ROOT, OZET_JSON))
        # --ozet-surum: TEMSİL bayrağının ÖLÇÜM kolu (2 = v2, 3 = v3). Yayın yolu (aşağıdaki
        # tam build) bu bayrağı OKUMAZ, daima OZET_TEMSIL_SURUM sabitini kullanır — yani
        # bu lever bir "gizli açma düğmesi" DEĞİL, kabul testinin iki hâli de aynı koşumda
        # ölçebilmesi içindir.
        _surum = _arg("--ozet-surum", None)
        _urunler = load_products(_katalog)
        _ozet = render_ozet(_urunler, temsil_surum=_surum)
        with open(_cikti, "w", encoding="utf-8") as f:
            f.write(_ozet)
        print("OK: ozet.json uretildi (%d urun, %d bayt, temsil surum %s)."
              % (len(_urunler), len(_ozet.encode("utf-8")),
                 _surum if _surum is not None else OZET_TEMSIL_SURUM))
        return

    products = load_products()

    # Kategori UYARISI (bilerek ölümcül DEĞİL): CATEGORIES + NAV_GIZLI dışında bir kategori,
    # ürünü katalogda bırakır ama kategori çipinden GÖRÜNMEZ yapar (index.html birebir eşler)
    # ve FONKSIYONEL_KATEGORILER dışında kaldığı için malzeme/renk seçicisini düşürür.
    # Tek kötü kategori TÜM yayını kırmasın diye burada sadece uyarılır; kapı ayrı ve
    # çalıştırılabilir: `python3 tools/kategori-kapisi.py` (exit 1 verir).
    _gecerli_kat = set(CATEGORIES) | set(NAV_GIZLI)
    _kotu_kat = sorted({p.get("kategori") for p in products if p.get("kategori") not in _gecerli_kat})
    if _kotu_kat:
        print("UYARI: gecersiz kategori(ler) var -> %s | detay: python3 tools/kategori-kapisi.py"
              % ", ".join(repr(k) for k in _kotu_kat))

    # Elle korunan dört içerik sayfasında işaretli attribution + Meta piksel + yukarı-çık oku
    # bloklarını yenile. (GA bu sayfalara elle gömülü; diğer üçü burada TEK KAYNAKtan enjekte
    # edilir — rıza kapısı GA ile aynı, ViewContent yok.) CI aynı dosyaları yayın klasörüne
    # kopyaladığı için ayrı varlık/deploy değişikliği gerekmez.
    for slug in STATIK_SAYFALAR:
        statik_yol = os.path.join(ROOT, slug, "index.html")
        with open(statik_yol, encoding="utf-8") as f:
            statik_html = f.read()
        yenilenmis = top_btn_ekle(meta_ekle(attribution_ekle(statik_html)))
        if yenilenmis != statik_html:
            with open(statik_yol, "w", encoding="utf-8") as f:
                f.write(yenilenmis)

    # eski urun/ klasörünü temizle (silinen ürünler kalmasın)
    if os.path.isdir(URUN_DIR):
        shutil.rmtree(URUN_DIR)
    os.makedirs(URUN_DIR, exist_ok=True)

    # YAYIN JS KOPYALARI (yorumu soyulmuş) — ÜRÜN DÖNGÜSÜNDEN ÖNCE üretilir ki
    # sayfalara basılan ?v=<hash> ile deploy'un _site'a kopyaladığı BAYTLAR aynı
    # dosyadan türesin (aksi halde ürün sayfaları kaynağın, ana sayfa soyulmuşun
    # hash'ini basar -> aynı varlık için İKİ ayrı ?v=, gereksiz önbellek kaybı).
    # Eski çıktı önce silinir: kaynaktan kaldırılan bir varlık _yayin'de kalırsa
    # deploy BAYAT dosya yayınlar (sessiz hata).
    if os.path.isdir(os.path.join(ROOT, YAYIN_DIR)):
        shutil.rmtree(os.path.join(ROOT, YAYIN_DIR))
    # VARLIK DIZINI ayni gerekce: kaynaktan kalkan bir blok varlik/ icinde kalirsa deploy
    # BAYAT dosya yayinlar. Icerik-adresli oldugu icin bayat dosyaya artik referans veren
    # yoktur ama yayina girip yer kaplar; her kosumda sifirdan uretilir.
    if os.path.isdir(VARLIK_DIR):
        shutil.rmtree(VARLIK_DIR)
    _VARLIK_ONBELLEK.clear()
    os.makedirs(VARLIK_DIR, exist_ok=True)
    for _rel in SOYULACAK_JS:
        if yayin_js_yaz(_rel) is None:
            print("HATA: yayin JS varligi bulunamadi -> %s "
                  "(deploy.yml beyaz listesi ile _yayin/ arasinda drift)" % _rel)
            sys.exit(1)

    # marka -> model hiyerarşik gezinme (anasayfa çip-marka evreni) — additive ek modül.
    # urunler.json'a DOKUNMAZ; /marka/... sayfalarını yazar; sitemap kayıtları + kopyalanacak
    # üst dizin(ler) + anasayfa SSR çip linkleri + çip slug haritası + ürün-çip geri-link
    # haritasını döner. ÜRÜN DÖNGÜSÜNDEN ÖNCE çağrılır: render_product marka çipini crawlable
    # /marka sayfasına bağlamak için product_chip_map'e muhtaç (Google discovery kök-fix'i;
    # /urun sayfaları bugüne dek yukarı /marka'ya link vermiyordu). /marka yazımı ürün/ çıktısına
    # bağımlı değildir; sıranın öne alınması yalnız haritayı erken hazır eder.
    marka_sonuc = marka_model_build.uret(products, marka_model_ctx())
    urun_cip_haritasi = marka_sonuc["product_chip_map"]

    for p in products:
        pdir = os.path.join(URUN_DIR, p["id"])
        os.makedirs(pdir, exist_ok=True)
        with open(os.path.join(pdir, "index.html"), "w", encoding="utf-8") as f:
            f.write(render_product(p, products, urun_cip_haritasi))

    # içerik/yasal sayfalar (/<slug>/index.html)
    for slug, title, meta, fn in CONTENT_PAGES:
        cdir = os.path.join(ROOT, slug)
        os.makedirs(cdir, exist_ok=True)
        with open(os.path.join(cdir, "index.html"), "w", encoding="utf-8") as f:
            f.write(render_content_page(slug, title, meta, fn()))

    # LANDING HUB — additive ek modül (tools/landing_hub_build.py). 166+ uzun-kuyruk landing'i
    # (CONTENT_PAGES) TEK crawlable dizin sayfasında listeler; landing'ler bugüne dek yalnız
    # birbirlerinden inbound alıyordu (güçlü-sayfa geri-linki yok). Hub sitemap kaydı + kopyalanacak
    # üst dizin(ini) döner; sayfalar.py CONTENT_PAGES'e DOKUNMAZ (kaynağı oradan OKUR).
    hub_sonuc = landing_hub_build.uret(marka_model_ctx())

    # deploy.yml beyaz-listesi için TEK KAYNAK manifesti: içerik/yasal sayfa dizinleri
    # (statik hakkimizda/iletisim/sss/gizlilik + üretilen CONTENT_PAGES) = SITEMAP_SLUGS +
    # marka->model üst dizini ("marka") + landing hub dizini. CI bu dosyayı okuyup her slug'ı
    # _site'a kopyalar; böylece yeni CONTENT_PAGES/marka/hub eklenince deploy.yml elle
    # güncellenmese de SESSİZCE 404 olmaz.
    with open(os.path.join(ROOT, "_yayin-icerik-dizinleri.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(SITEMAP_SLUGS + marka_sonuc["dizinler"] + hub_sonuc["dizinler"]) + "\n")

    # sitemap.xml (marka->model + landing hub URL'leri lastmod'lu eklenir)
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(render_sitemap(products, extra_urls=marka_sonuc["sitemap"] + hub_sonuc["sitemap"]))

    # merchant-feed.xml  (Google Merchant Center — sadece sabit fiyatli urunler)
    feed_xml, feed_n = render_merchant_feed(products)
    with open(os.path.join(ROOT, MERCHANT_FEED), "w", encoding="utf-8") as f:
        f.write(feed_xml)

    # filament-veri.js — ana sayfa kart çipleri (index.html) filament kuralını buradan
    # okur; kaynak tools/filamentler.json (tek kaynak, elle kopya YOK). CI üretir, git'e girmez.
    # "_" ile başlayan iç notlar ve "kaynaklar" siteye TAŞINMAZ (sadece gereken veri).
    fil_ref = {k: v for k, v in filament_ortak.referans().items()
               if not k.startswith("_") and k != "kaynaklar"}
    with open(os.path.join(ROOT, "filament-veri.js"), "w", encoding="utf-8") as f:
        f.write("/* Sayfa ureteci uretir — ELLE DUZENLEME. Tek kaynak: malzeme tablosu */\n"
                "window.PRUVO_FILAMENT = "
                + json.dumps(fil_ref, ensure_ascii=False, separators=(",", ":"))
                + ";\n")

    # taban-fiyatlar.js — sarı kart "X TL'den başlayan" haritası (tek kaynak: şemalar)
    uret_taban_fiyatlar()

    # ÜRETİLEN iki JS varlığının yayın kopyası (yorumu soyulmuş). Bunlar yukarıda
    # üretildiği için burada soyulur; deploy _site'a _yayin/'dan kopyalar.
    for _rel in ("filament-veri.js", "taban-fiyatlar.js"):
        if yayin_js_yaz(_rel) is None:
            print("HATA: uretilen yayin JS varligi bulunamadi -> %s" % _rel)
            sys.exit(1)

    # index.built.html — ana sayfanin YAYIN kopyasi: script src'leri ?v=<hash> ile
    # surumlenir (KAYNAK index.html degismez). deploy.yml bunu _site/index.html yapar.
    # taban-fiyatlar.js YUKARIDA uretildi -> hash'i artik hesaplanabilir.
    with open(os.path.join(ROOT, "index.built.html"), "w", encoding="utf-8") as f:
        f.write(yayin_index(marka_sonuc, products))

    # robots.txt
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(render_robots())

    # ozet.json  (FAZ 3 — ana sayfanin ilk boyamasi; bayrak kapaliyken URETILIR ama
    # site onu CEKMEZ. Uretmeye devam etmemizin sebebi: bayrak acildigi an dosya
    # yayindaymis gibi hazir olsun + faz3-yuk/faz3-bayrak testleri her zaman kosabilsin.)
    ozet_json = render_ozet(products)
    with open(os.path.join(ROOT, OZET_JSON), "w", encoding="utf-8") as f:
        f.write(ozet_json)
    ozet_bayt = len(ozet_json.encode("utf-8"))

    # .nojekyll  (GitHub Pages tüm dosyaları olduğu gibi sunsun)
    open(os.path.join(ROOT, ".nojekyll"), "w").close()

    # VARLIK FAIL-CLOSED: bir sayfa uretildiyse en az bir CSS + bir JS varligi yazilmis
    # OLMALI. Bos varlik dizini = sayfalar ciplak (stilsiz/JS'siz) yayinlanmis demektir;
    # bu SESSIZ hata olmasin diye build burada DURUR.
    _varliklar = sorted(os.listdir(VARLIK_DIR)) if os.path.isdir(VARLIK_DIR) else []
    _v_css = [a for a in _varliklar if a.endswith(".css")]
    _v_js = [a for a in _varliklar if a.endswith(".js")]
    if products and not (_v_css and _v_js):
        print("HATA: varlik/ eksik (css=%d js=%d) -> sayfalar CIPLAK kalirdi; yayin DURDU."
              % (len(_v_css), len(_v_js)))
        sys.exit(1)
    _v_bayt = sum(os.path.getsize(os.path.join(VARLIK_DIR, a)) for a in _varliklar)
    print("varlik/: %d dosya (%d css + %d js), %d bayt"
          % (len(_varliklar), len(_v_css), len(_v_js), _v_bayt))

    print("OK: %d urun sayfasi + sitemap.xml + robots.txt + merchant-feed.xml (%d urun) uretildi."
          % (len(products), feed_n))
    print("ozet.json: %d bayt (%.1f KB) | butce %d KB"
          % (ozet_bayt, ozet_bayt / 1024.0, OZET_BUTCE // 1024))

    # BUTCE KAPISI KOSULLU (mimar emri, 20 Tem):
    #   bayrak KAPALI -> site ozet.json'a bagimli DEGIL; asim sadece UYARI. Katalog
    #     buyudu diye TUM deploy'un kirilmasi (urun sayfalari, sitemap, feed) kabul edilemez.
    #   bayrak ACIK   -> ozet.json ilk boyamanin kritik yolunda; sessizce sismesi
    #     mobil ilk acilisi bozar => build KIRMIZI.
    if ozet_bayt > OZET_BUTCE:
        if _index_bayragi("EDGE_KATALOG"):
            print("HATA: ozet.json butceyi asti (%d > %d bayt) ve EDGE_KATALOG ACIK. "
                  "Kart temsilini ya da VITRIN_BLOKLAR havuzlarini yeniden olc."
                  % (ozet_bayt, OZET_BUTCE))
            sys.exit(1)
        print("UYARI: ozet.json butceyi asti (%d > %d bayt). EDGE_KATALOG kapali oldugu "
              "icin yayin KIRILMADI; bayragi acmadan once kart temsilini yeniden olc."
              % (ozet_bayt, OZET_BUTCE))


if __name__ == "__main__":
    main()
