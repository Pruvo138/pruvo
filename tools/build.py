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
import shutil
import html
import hashlib
import datetime
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sayfalar import (SELLER, PAY_BAND_HTML, FOOT_NAV_HTML,
                      CONTENT_CSS, CONTENT_PAGES, SITEMAP_SLUGS,
                      STATIK_SAYFALAR, PV_SCRIPT_HTML)
import filament_ortak

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
# index.html'deki GIZLI_KATEGORILER ile BİRLİKTE güncelle (CATEGORIES kuralının aynısı).
NAV_GIZLI = ["Jeneratör"]
# Malzeme/renk/boy seçicisi bu kategorilerde gösterilir (Dekorasyon, Oyun/Hobi HARİÇ).
# secenekler.js'deki FONKSIYONEL_KATEGORILER ile BİRLİKTE güncelle (tek karar iki yerde).
FONKSIYONEL_KATEGORILER = ["Otomobil", "Motosiklet", "Tamirat", "Elektronik", "Ev", "Marin", "Bisiklet", "Bahçe", "Ofis", "Kamera"]

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


def attribution_head_snippet():
    """Tek kaynak modülü inline basar; yayın beyaz listesine yeni varlık gerekmez."""
    with open(ATTRIBUTION_JS_PATH, encoding="utf-8") as f:
        source = f.read().strip()
    return ATTRIBUTION_START + "\n<script>\n" + source + "\n</script>\n" + ATTRIBUTION_END


def attribution_ekle(html_metni):
    """Attribution bloğunu ekler veya mevcut bloğu tek kaynaktan yeniler."""
    snippet = attribution_head_snippet()
    pattern = re.compile(re.escape(ATTRIBUTION_START) + r".*?" +
                         re.escape(ATTRIBUTION_END), re.S)
    if pattern.search(html_metni):
        return pattern.sub(snippet, html_metni, count=1)
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
  /* Ziyaretçi daha önce onay verdiyse geri yükle (banner tekrar çıkmaz). */
  try { if (localStorage.getItem('pruvo_onay_analitik') === 'kabul') {
    gtag('consent', 'update', { 'analytics_storage': 'granted' }); } } catch(e){}
</script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-5V53CQMSCE"></script>
<script>
  gtag('js', new Date());
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
META_PIXEL_ID = "1562627655518274"

META_HEAD_SNIPPET = """<!-- Meta Pixel — KVKK/rıza kapılı. Piksel Kimliği 1562627655518274 herkese açıktır.
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
    window.fbq("init", "1562627655518274");
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
    <p>Trafiği anlamak için isteğe bağlı analiz çerezleri (Google Analytics) kullanmak istiyoruz.
       Onayınız olmadan çalışmazlar. <a href="/gizlilik/">Gizlilik Politikası</a></p>
    <div class="pco-btns">
      <button type="button" class="pco-ret" id="pco-ret">Reddet</button>
      <button type="button" class="pco-kabul" id="pco-kabul">Kabul Et</button>
    </div>
  </div>
</div>
<script>
(function(){
  var ANAHTAR = "pruvo_onay_analitik";
  var el = document.getElementById("pruvo-cerez-onay");
  if(!el){ return; }
  var secim = null;
  try { secim = localStorage.getItem(ANAHTAR); } catch(e){}
  if(secim === "kabul" || secim === "ret"){ return; }   /* seçim yapılmış: banner çıkmaz */
  el.hidden = false;
  function kaydet(deger){ try { localStorage.setItem(ANAHTAR, deger); } catch(e){} el.hidden = true; }
  var kabul = document.getElementById("pco-kabul");
  var ret = document.getElementById("pco-ret");
  kabul.addEventListener("click", function(){
    if(typeof gtag === "function"){ gtag('consent','update',{'analytics_storage':'granted'}); }
    kaydet("kabul");
    /* Meta pikseli de rıza anında başlasın (init + PageView) — kaydet() localStorage'ı 'kabul'
       yazdıktan SONRA çağrılır ki pruvoMetaBaslat rıza kontrolünden geçsin. */
    if(typeof window.pruvoMetaBaslat === "function"){ window.pruvoMetaBaslat(); }
  });
  ret.addEventListener("click", function(){ kaydet("ret"); });  /* denied kalır */
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


_SCRIPT_SRC_RE = re.compile(r'(<script\b[^>]*\ssrc=")(/[^"?]+\.js)(")')


def surumle_scriptler(html_metni):
    """HTML icindeki site-ici <script src="/...js"> referanslarina ?v=<icerik-hash>
    ekler. Zaten surumlu (?v= olan — regex .js'ten hemen sonra " bekler, eslesmez) ya da
    dosyasi bulunmayan (lokalde build'siz) referansa DOKUNMAZ."""
    def _degistir(m):
        yol = m.group(2)                      # or. "/secenekler.js"
        dosya = os.path.join(ROOT, yol.lstrip("/"))
        if not os.path.isfile(dosya):
            return m.group(0)
        return m.group(1) + yol + "?v=" + dosya_surum(dosya) + m.group(3)
    return _SCRIPT_SRC_RE.sub(_degistir, html_metni)


def yayin_index():
    """Yayinlanan ana sayfa: KAYNAK index.html'in script src'leri surumlenmis kopyasi.
    Kaynak dosya DEGISTIRILMEZ (curumesin diye); cikti index.built.html'e yazilir, deploy
    onu _site/index.html olarak kopyalar. taban-fiyatlar.js bu asamada uretilmis olmali."""
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        return surumle_scriptler(attribution_ekle(f.read()))


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
FILAMENT_SIRA = _js_sabiti(_SEC_JS, "FILAMENT_SIRA")
RENK_SECENEKLERI = _js_sabiti(_SEC_JS, "RENK_SECENEKLERI")
RENK_DIGER_YUZDE = _js_sayisi(_SEC_JS, "RENK_DIGER_YUZDE")
ADET_EN_AZ = _js_sayisi(_SEC_JS, "ADET_EN_AZ")
ADET_EN_COK = _js_sayisi(_SEC_JS, "ADET_EN_COK")


def _js_bayragi(kaynak, ad):
    m = re.search(r"var\s+" + re.escape(ad) + r"\s*=\s*(true|false);", kaynak)
    if not m:
        raise SystemExit("secenekler.js'te %s bulunamadi." % ad)
    return m.group(1) == "true"


# Sari seri 3D onizleme (tools/paket-onizleme-3d.md) — bayrak + aile listesi TEK KAYNAK
# secenekler.js (onizleme Worker'i da AYNI listeyi okur). Bayrak kapaliyken sayfalara
# hicbir onizleme ogesi basilmaz = canlida sifir gorunur fark.
ONIZLEME_3D_ACIK = _js_bayragi(_SEC_JS, "ONIZLEME_3D_ACIK")
ONIZLEME_AILELER = set(_js_sabiti(_SEC_JS, "ONIZLEME_AILELER"))

# "Onizle (3D)" akisi: parametreleri konfiguratorden alir, /api/onizleme/olustur'a
# gonderir, donen gzip'li binary STL'i acip /jenerator/viewer.js ile cizer.
# .format() SONRASI yerlestirilir (placeholder degeri yeniden islenmez) -> tek suslu
# parantezler guvenlidir. Fiyat/sepet koduna dokunmaz; salt gorsel katman.
ONIZLEME_JS = """
(function(){
  var btn=document.getElementById("onizleBtn"); if(!btn){ return; }
  var kutu=document.getElementById("onizlemeKutu");
  var durum=document.getElementById("onizlemeDurum");
  var tuval=document.getElementById("onizlemeTuval");
  var mesgul=false;
  function de(t){ if(durum){ durum.textContent=t||""; } }
  btn.addEventListener("click", function(){
    if(mesgul){ return; }
    if(!(window.PRUVO_KONF && PRUVO_KONF.hazir() && PRUVO_KONF.gecerliMi())){
      kutu.hidden=false; de("Önce ölçüleri geçerli aralıkta doldurun."); return;
    }
    /* satiraYaz: konfiguratorun dogrulanmis parametre setini verir (fiyat alanlari
       burada KULLANILMAZ; onizleme fiyattan bagimsiz). */
    var s = PRUVO_KONF.satiraYaz({ malzeme:"PLA", renk:"Siyah" });
    if(!s.parametreler){ kutu.hidden=false; de("Önce ölçüleri geçerli aralıkta doldurun."); return; }
    /* Onizleme secenek kisitlari (tek kaynak /secenekler.js): motorda 3D
       karsiligi olmayan secimlerde istek atmadan dostca uyar. */
    var kis=(window.PRUVO_SECENEK&&PRUVO_SECENEK.ONIZLEME_KISITLAR||{})[URUN.id];
    if(kis){ for(var ad in kis){ if(Object.prototype.hasOwnProperty.call(kis,ad)){
      var v=s.parametreler[ad];
      if(v!==undefined && kis[ad].indexOf(v)<0){
        kutu.hidden=false;
        de("Bu seçenekle 3D önizleme şimdilik sunulamıyor; sipariş verebilirsiniz, üretim etkilenmez.");
        return;
      }
    }}}
    mesgul=true; btn.disabled=true; kutu.hidden=false; de("Model hazırlanıyor…");
    fetch("/api/onizleme/olustur", { method:"POST",
      headers:{ "Content-Type":"application/json" },
      body: JSON.stringify({ aile: URUN.id, parametreler: s.parametreler }) })
    .then(function(c){
      if(!c.ok){ return c.json().then(function(h){ throw new Error(h.hata||("hata-"+c.status)); }); }
      if(c.headers.get("X-Sikistirma")==="gzip"){
        if(!window.DecompressionStream){ throw new Error("tarayici-eski"); }
        return new Response(c.body.pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();
      }
      return c.arrayBuffer();
    })
    .then(function(buf){
      PRUVO_VIEWER.goster(tuval, buf);
      de("Sürükleyerek döndürün · tekerlek/iki parmakla yakınlaştırın");
    })
    .catch(function(e){
      var m={
        "gecersiz-geometri":"Bu ölçü kombinasyonu üretilemiyor; ölçüleri değiştirip tekrar deneyin.",
        "onizleme-secenek-kisiti":"Bu seçenekle 3D önizleme şimdilik sunulamıyor; sipariş verebilirsiniz, üretim etkilenmez.",
        "hiz-siniri":"Kısa sürede çok fazla önizleme istendi; bir dakika sonra tekrar deneyin.",
        "derleyici-yok":"Önizleme servisi şu an hazır değil; lütfen daha sonra deneyin.",
        "tarayici-eski":"Tarayıcınız 3D önizlemeyi desteklemiyor."
      };
      de(m[e.message] || "Önizleme oluşturulamadı; lütfen tekrar deneyin.");
    })
    .then(function(){ mesgul=false; btn.disabled=false; });
  });
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
# (******** royalty-free lisanslı ürünlerde CC atıfı yoktur; "lisans" alanı eklenmez.)
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

# ABS ve Karbon Katkılı SİTEDE SATILMAZ (Okan, 16 Tem) — mühendislik malzemesi, WhatsApp
# özel talebi (secenekler.js FILAMENT_SIRA'da zaten yok). Not metni TEK KAYNAK: hem malzeme
# seçicisinin altında (fonksiyonel/parametrik ürün) hem de seçici olmayan ürünlerdeki filament
# bilgi bloğunda (filament_html) aynen kullanılır.
MUHENDISLIK_WA_NOT = ('<p class="malzeme-not">Karbon fiber veya diğer mühendislik malzemeleriyle '
    'üretim için <a href="https://wa.me/905451386526?text=Merhaba%2C%20m%C3%BChendislik%20'
    'malzemesiyle%20%C3%B6zel%20%C3%BCretim%20hakk%C4%B1nda%20bilgi%20almak%20istiyorum." '
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


def _renk_butonlari_html():
    """Renk BUTONLARI (Okan, 16 Tem) — fonksiyonel/kart-seçim ürününde dropdown yerine 4 buton:
    Siyah/Beyaz/Gri düz renk yuvarlağı, Diğer = gökkuşağı gradyan. Önden seçili YOK; 'Diğer'
    seçilince altında serbest metin kutusu (renkOzel) belirir. Parametrik ürün DROPDOWN kalır."""
    ornek = {
        "Siyah": '<span class="renk-yuvar" style="background:#151515"></span>',
        "Beyaz": '<span class="renk-yuvar" style="background:#fff;border:1px solid var(--gray-line)"></span>',
        "Gri": '<span class="renk-yuvar" style="background:#8a929e"></span>',
        "Diğer": '<span class="renk-yuvar renk-yuvar-gokkusagi"></span>',
    }
    btns = "".join(
        '<button type="button" class="renk-btn" data-renk="%s">%s'
        '<span class="renk-ad">%s</span></button>' % (
            esc(r), ornek.get(r, ""),
            esc(r + (" (+%%%d)" % RENK_DIGER_YUZDE if r == "Diğer" else "")))
        for r in RENK_SECENEKLERI)
    return ("""
      <div class="opsiyon-row opsiyon-renk">
        <label>Renk</label>
        <div class="renk-butonlar" id="renkButonlar">""" + btns + """</div>
      </div>
      <input type="text" id="renkOzel" class="renk-ozel" maxlength="30"
             placeholder="istediğiniz rengi yazın (ör. turuncu)" style="display:none">""")


def _malzeme_renk_html():
    """Malzeme dropdown + mühendislik-malzeme WA notu + renk. YALNIZ parametrik (konfigüratör)
    ürün sayfası kullanır — fonksiyonel ürünlerde malzeme artık kartlardan seçilir (dropdown yok)."""
    malzeme_opts = "".join(
        '\n          <option value="%s">%s</option>' % (
            esc(m), esc(m + (" (standart)" if not FILAMENT_FARK.get(m)
                             else " (+%%%d)" % FILAMENT_FARK[m])))
        for m in FILAMENT_SIRA)
    # NOT: metinde yuzde-kacisli WhatsApp URL'i var (%2C, %C3%BC...) -> %-bicimlendirme
    # KULLANILMAZ (URL'i bozar / ValueError verir); parcalar birlestirilir.
    return ("""
      <div class="opsiyon-row">
        <label for="malzemeSec">Malzeme</label>
        <select id="malzemeSec">""" + malzeme_opts + """
        </select>
      </div>
      """ + MUHENDISLIK_WA_NOT + _renk_html())


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


CART_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 18c-1.1 0-1.99.9-1.99 2S5.9 22 '
             '7 22s2-.9 2-2-.9-2-2-2zM1 2v2h2l3.6 7.59-1.35 2.45c-.16.28-.25.61-.25.96 0 1.1.9 2 2 2h12v-2H7.42c-.14 '
             '0-.25-.11-.25-.25l.03-.12L8.1 15h7.45c.75 0 1.41-.41 1.75-1.03l3.58-6.49A1 1 0 0 0 20 6H5.21l-.94-2H1zm16 '
             '16c-1.1 0-1.99.9-1.99 2s.89 2 1.99 2 2-.9 2-2-.9-2-2-2z"/></svg>')

# Eylem İKON çifti (kart-seçim sayfası, Adet satırının sağı) — %s sırası: pid, wa href.
# Yazı yok -> aria-label + title ZORUNLU (erişilebilirlik); id'ler script'le birebir.
IKON_BUTONLAR_HTML = (
    '<div class="eylem-ikonlar">'
    '<button class="ikon-btn ikon-sepet" id="cartBtn" data-id="%s" '
    'aria-label="Sepete Ekle" title="Sepete Ekle">' + CART_ICON + '</button>'
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
  /* Eylem ikonları (madde 7): Adet satırının sağında yazısız sepet + WhatsApp ikonu.
     44×44 = mobil dokunma alanı; margin-left:auto sağa yaslar, dar ekranda .opsiyon-row
     flex-wrap ile ikonlar panel İÇİNDE alt satıra kırılır. */
  .eylem-ikonlar{display:inline-flex;gap:8px;margin-left:auto}
  .ikon-btn{width:44px;height:44px;border:none;border-radius:9px;display:inline-flex;
    align-items:center;justify-content:center;cursor:pointer;transition:.15s;flex:none;
    text-decoration:none;padding:0}
  .ikon-btn svg{width:22px;height:22px;fill:#fff}
  .ikon-sepet{background:var(--navy)}
  .ikon-sepet:hover{background:var(--navy-2)}
  .ikon-sepet.added{background:#178a44}
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

  /* Malzeme bolumu: sitede satilan filament cipleri (ABS/Karbon haric) + tavsiye rozeti + aciklama balonu.
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
  }
"""
PAGE_CSS += CONTENT_CSS


# ------------------------------------------------------------------ yardımcılar
def esc(s):
    return html.escape(s or "", quote=True)


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
    '350 TL (12 cm)'->'350'. Sayisal fiyat yoksa (parametrik/'olcuye ozel') None."""
    if not fiyat:
        return None
    m = re.search(r"(\d[\d.]*)\s*(?:tl|try|₺)", fiyat, re.I) or re.search(r"(\d[\d.]*)", fiyat)
    if not m:
        return None
    raw = m.group(1).replace(".", "")          # Turkce binlik ayraci ('1.250' -> '1250')
    return raw if raw.isdigit() and int(raw) > 0 else None


def feed_id(pid):
    """Google Merchant 'id'/'mpn' 50 karakter siniri: uzun urun-id'sini kisalt.
    <=50 ise AYNEN dondur (kisa id'ler DEGISMEZ, churn yok). Uzunsa ilk 41 karakter
    + '-' + sha1'in ilk 8 hex hanesi = TAM 50 karakter; benzersiz, deterministik,
    KALICI. NOT: bu yalniz feed kimligidir; product_url/link TAM pid ile kalir."""
    if len(pid) <= 50:
        return pid
    return pid[:41] + "-" + hashlib.sha1(pid.encode("utf-8")).hexdigest()[:8]


def images_of(p):
    imgs = p.get("gorseller") or []
    return [i for i in imgs if i]


def wa_href(p, url):
    msg = u"Merhaba, şu ürünle ilgileniyorum: " + (p.get("baslik") or "") + "\n" + url
    from urllib.parse import quote
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
def filament_html(p, wa_not=False):
    """Fiyat bloğunun altındaki "Malzeme" bölümü: sitede satılan filament çipleri + tavsiye
    rozeti + balon. ABS ve Karbon Katkılı SİTEDE SATILMAZ (Okan, 16 Tem) — mühendislik
    malzemesi, WhatsApp özel talebiyle satılır; burada çip olarak SUNULMAZ (yalnız
    /malzeme-rehberi/ sayfasında ayrı bölümde anlatılır). wa_not=True ise (malzeme
    seçicisi/dropdown'u olmayan ürün — MALZEME_RENK_HTML basılmıyor) mühendislik malzemesi
    notu burada gösterilir; dropdown'lu üründe not zaten opsiyonlar bloğunda var, mükerrer
    basılmaz.

    MİMARİ İLKE: filament bilgisi ürün verisine YAZILMAZ — tavsiye, kategori haritasından
    (tools/filamentler.json) render anında türetilir; ürün "tavsiyeFilament" override'ı
    taşıyorsa harita yerine o geçer. Balon metni referanstaki "uzun" alanının birebir
    kendisidir (tek kaynak). F kalemi (Okan, 16 Tem gece): parametrik (sarı) sayfa da
    normal sayfayla BİREBİR — tavsiye rozeti dahil; eski "rozet basılmaz + konuşarak
    belirlenir notu" istisnası kaldırıldı.
    """
    ref = filament_ortak.referans()
    tavs = {
        t["ad"]: t["rozet"]
        for t in filament_ortak.tavsiyeler(p.get("kategori"), p.get("tavsiyeFilament"))}
    cips = []
    for f in ref["filamentler"]:
        if not f.get("site"):
            continue
        rozet = tavs.get(f["ad"], "")
        rozet_html = ""
        if rozet:
            rcls = "fil-rozet" if rozet == "Tavsiyemiz" else "fil-rozet fil-rozet-not"
            rozet_html = '<span class="%s">%s</span>' % (rcls, esc(rozet))
        cips.append(
            '<button type="button" class="fil-cip%s" data-malzeme="%s" aria-expanded="false">'
            '<span class="fil-isi">%s</span>'
            '<span class="fil-ad">%s</span>'
            '<span class="fil-etiket">%s</span>'
            '%s'
            '<span class="fil-balon" role="tooltip"><strong>%s — %s</strong><br>%s</span>'
            '</button>'
            % (" tavsiyeli" if rozet else "", esc(f["ad"]), esc(f["isiDayanimi"]), esc(f["ad"]),
               esc(f["kisaEtiket"]), rozet_html,
               esc(f.get("uzunAd") or f["ad"]), esc(f["kisaEtiket"]), esc(f["uzun"])))
    wa_html = MUHENDISLIK_WA_NOT if wa_not else ""
    return ('<div class="malzeme-blok">'
            '<div class="malzeme-baslik">Malzeme</div>'
            '<div class="fil-cipler" id="filCipler">%s</div>'
            '%s'
            '<a class="malzeme-link" href="/malzeme-rehberi/">Hangi malzeme nerede kullanılır? '
            'Malzeme Rehberi &rarr;</a>'
            '</div>' % ("".join(cips), wa_html))


# ------------------------------------------------------------------ ürün sayfası
def render_product(p, all_products):
    pid = p["id"]
    url = product_url(pid)
    baslik = p.get("baslik") or ""
    kategori = p.get("kategori") or ""
    fiyat = (p.get("fiyat") or "").strip()
    markalar = p.get("marka") or []
    imgs = images_of(p)
    cover = imgs[0] if imgs else (SITE + "/favicon.png")
    desc160 = meta_desc(p)
    pnum = price_number(fiyat)

    aciklama_html = esc(p.get("aciklama") or "").replace("\n", "<br>")

    # --- JSON-LD Product
    offer = {
        "@type": "Offer",
        "url": url,
        "availability": "https://schema.org/InStock",
        "itemCondition": "https://schema.org/NewCondition",
        "priceCurrency": "TRY",
        "seller": {"@type": "Organization", "name": "PRUVO"},
    }
    if pnum:
        offer["price"] = pnum
        offer["priceValidUntil"] = PRICE_VALID

    product_ld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": baslik,
        "image": imgs or [cover],
        "description": re.sub(r"\s+", " ", (p.get("aciklama") or "")).strip(),
        "sku": pid,
        "category": kategori,
        "offers": offer,
    }
    if markalar:
        product_ld["brand"] = [{"@type": "Brand", "name": b} for b in markalar]

    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Ana Sayfa", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": kategori,
             "item": SITE + "/?kategori=" + kategori},
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

    # --- marka çipleri (ana sayfada o markayı filtreler)
    brand_html = ""
    if markalar:
        chips = "".join(
            '<a class="brand-chip" href="/?marka=%s">%s</a>' % (esc(b), esc(b))
            for b in markalar)
        brand_html = '<div class="brands">' + chips + "</div>"

    # --- parametrik ("ölçüye özel") rozeti
    parametrik = bool(p.get("parametrik"))
    badge_html = '<span class="ozel-badge">Ölçüye Özel</span>' if parametrik else ''

    # --- fiyat metni (JS'siz/tarayıcı öncesi durum + fonksiyonel OLMAYAN ürünlerin tek gösterimi)
    if fiyat:
        price_text = fiyat
    elif parametrik:
        price_text = "Ölçüye özel fiyat — teklif için sipariş verin"
    else:
        price_text = "Fiyat için sipariş verin"

    # --- malzeme/renk/boy seçicisi (fonksiyonel kategoriler) / konfigüratör (parametrik+şemalı)
    fonksiyonel = kategori in FONKSIYONEL_KATEGORILER
    boy_secenekleri = p.get("boy_secenekleri") or []
    sema = konf_sema(pid) if parametrik else None
    if sema:
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
        taban_tl = sema.get("tabanFiyatTL")
        konf_fiyat_metni = ((taban_fiyat_metni(taban_tl) + "&#39;den başlayan")
                            if taban_tl is not None else "Ölçüye özel fiyat")
        opsiyonlar_html = ("""
    <div class="opsiyonlar konf" id="opsiyonlar">
      <div class="konf-baslik">Ölçülerinizi girin</div>
      <div id="konfAlanlar"></div>
      {onizleme}
      {renk}
      {adet}
      <div class="opsiyon-fiyat" id="opsiyonFiyat">{fiyat_metni}</div>
      <div class="konf-hacim" id="konfHacim"></div>
    </div>
    """).format(fiyat_metni=konf_fiyat_metni,
                onizleme=onizleme_html,
                renk=_renk_butonlari_html(),
                adet=ADET_IKON_HTML % (
                    ADET_EN_AZ, ADET_EN_COK,
                    IKON_BUTONLAR_HTML % (esc(pid), esc(wa_href(p, url)))))
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
        baslangic_fiyat = (esc(fiyat) + "&#39;den başlayan") if fiyat else esc(price_text)
        opsiyonlar_html = ("""
    <div class="opsiyonlar" id="opsiyonlar">
      {renk}
      {boy}
      {adet}
      <div class="opsiyon-fiyat" id="opsiyonFiyat">{fiyat_metni}</div>
    </div>
    """).format(renk=_renk_butonlari_html(), boy=boy_html,
                adet=ADET_IKON_HTML % (
                    ADET_EN_AZ, ADET_EN_COK,
                    IKON_BUTONLAR_HTML % (esc(pid), esc(wa_href(p, url)))),
                fiyat_metni=baslangic_fiyat)
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
    """).format(malzeme_renk=_malzeme_renk_html(), boy=boy_html,
                adet=ADET_HTML % (ADET_EN_AZ, ADET_EN_COK),
                fiyat_metni=esc(price_text))
        price_html = ""
    else:
        opsiyonlar_html = ""
        price_html = '<div class="price%s">%s</div>' % (
            "" if fiyat else " empty", esc(price_text))

    # --- eylem butonları (madde 7): kart-seçim sayfasında İKONLAR Adet satırında (yukarıda
    # opsiyonlar_html'e basıldı) -> sayfa altına buton BASILMAZ; diğer sayfalarda (parametrik
    # konfigüratör, şemasız fonksiyonel, panelsiz Dekorasyon/Oyun-Hobi) büyük butonlar yerinde.
    # F kalemi: SEMALI parametrik (sari) sayfa da kart-secim modunda — malzeme
    # filament kartlarindan, butonlar Adet satirinda (sayfa altina buton basilmaz).
    # Buyuk butonlar yalniz semasiz-fonksiyonel (bugun urun yok) + panelsiz sayfalarda.
    kart_secim = bool(sema) or (fonksiyonel and not parametrik)
    if kart_secim:
        eylem_butonlar_html = ""
    else:
        eylem_butonlar_html = BUYUK_BUTONLAR_HTML % (esc(pid), esc(wa_href(p, url)))

    # --- ilgili ürünler (aynı kategori, kendisi hariç, en fazla 8)
    rel = [x for x in all_products
           if x.get("kategori") == kategori and x["id"] != pid][:8]
    rel_html = ""
    if rel:
        cards = []
        for r in rel:
            rimgs = images_of(r)
            rcov = rimgs[0] if rimgs else cover
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
            % (esc(kategori), "".join(cards)))

    title_tag = esc(baslik) + " — PRUVO Özel Tasarım Yedek Parça"

    # --- JS'e (opsiyonlar bloğu + fiyat hesabı) aktarılacak ürün verisi
    urun_json = json.dumps(
        {"id": pid, "baslik": baslik, "kategori": kategori, "fiyat": fiyat,
         "parametrik": parametrik, "boy_secenekleri": boy_secenekleri},
        ensure_ascii=False, separators=(",", ":")).replace("</script>", "<\\/script>")

    # --- Meta Pixel ViewContent (rıza-kapılı, YALNIZ ürün sayfası). content_ids = TAM ürün slug'ı
    # (feed g:id ile birebir -> katalog eşleşmesi); content_type "product"; currency "TRY"; value
    # SAYI (sabit fiyat varsa), parametrik/fiyatsız üründe value yok. pruvoMetaTrack rıza yoksa yutar.
    mvc = {"content_ids": [pid], "content_type": "product", "currency": "TRY"}
    _vc_fiyat = price_number(fiyat)
    if _vc_fiyat:
        mvc["value"] = int(_vc_fiyat)
    mvc_json = json.dumps(mvc, ensure_ascii=False, separators=(",", ":")
                          ).replace("</script>", "<\\/script>")
    meta_view_content = (
        '<script>\n'
        'if(typeof window.pruvoMetaTrack==="function"){ window.pruvoMetaTrack("ViewContent", '
        + mvc_json + '); }\n</script>')

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
<meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{ogtitle}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{img}">
<script type="application/ld+json">{product_ld}</script>
<script type="application/ld+json">{breadcrumb_ld}</script>
<style>{css}</style>
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
    <a class="help-cta-btn" href="https://wa.me/905451386526?text=Merhaba%2C%20arad%C4%B1%C4%9F%C4%B1m%20bir%20yedek%20par%C3%A7a%20var.%20%C3%9Cretebilir%20misiniz%3F" target="_blank" rel="noopener">{icon} Bizimle İletişime Geçin</a>
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
    <a href="/?kategori={katq}">{kategori}</a><span>&rsaquo;</span>
    {baslik}
  </nav>

  <div class="detail">
    <div class="gallery">
      {main_img}
      {thumbs}
    </div>
    <div class="info">
      <span class="cat">{kategori}</span>{badge}
      <h1>{h1}</h1>
      {brands}
      {price}
      {opsiyonlar}
      {malzeme}
      <p class="desc">{aciklama}</p>
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
<script>
(function(){{
  var topBtn=document.getElementById("topBtn");
  window.addEventListener("scroll",function(){{
    topBtn.classList.toggle("show", window.scrollY > 600);
  }},{{passive:true}});
  topBtn.onclick=function(){{ window.scrollTo({{top:0, behavior:"smooth"}}); }};
}})();
</script>

<script src="/secenekler.js"></script>
{konf_scripts}
<script>
function pv(el,src){{
  document.getElementById('mainImg').src=src;
  var t=document.querySelectorAll('.thumb');
  for(var i=0;i<t.length;i++){{t[i].className='thumb';}}
  el.className='thumb active';
}}
var URUN = {urun_json};
var URUN_SEMA = {sema_json};
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
  /* Kart-secim modu (Okan, 16 Tem): fonksiyonel ürünlerde malzeme dropdown YOK, malzeme
     filament KARTLARINDAN seçilir. Önden seçili malzeme YOK -> seciliMalzeme boş başlar. */
  var KART_SECIM = {kart_secim};
  var cipler = document.getElementById("filCipler");
  var renkBtnlar = document.getElementById("renkButonlar");
  var seciliMalzeme = "";
  var seciliRenk = "";

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
    if(URUN_SEMA && window.PRUVO_KONF && PRUVO_KONF.hazir()){{ PRUVO_KONF.satiraYaz(s); }}
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
    var c = PRUVO_SECENEK.sepetYukle();
    var satir = currentSatir();
    var anahtar = PRUVO_SECENEK.satirAnahtari(satir);
    var has = c.some(function(s){{ return PRUVO_SECENEK.satirAnahtari(s) === anahtar; }});
    btn.classList.toggle("added", has);
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
    /* Konfigüratörlü sayfada fiyat alanını konfigüratör yönetir (kuruşlu canlı hesap,
       taban fiyat yoksa "—"); geçersiz ölçüde sepete ekleme kilitlenir. */
    if(fiyatEl && !URUN_SEMA){{
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
    }}
    if(orderAlt){{
      var mesaj = "Merhaba, şu ürünle ilgileniyorum: " + URUN.baslik +
                  (ozet.detay ? ("\\n" + ozet.detay) : "") + "\\n" + location.href;
      var ref = (typeof window.pruvoRef === "function") ? window.pruvoRef() : "";
      if(ref){{ mesaj += "\\n" + ref; }}
      orderAlt.href = "https://wa.me/{whatsapp}?text=" + encodeURIComponent(mesaj);
    }}
  }}
  btn.addEventListener("click", function(){{
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
         konfigürasyonun kuruşlu tutarı TRY'ye; content_ids DAİMA ürün slug'ı, content_type "product". */
      try {{
        var mAtc = PRUVO_SECENEK.satirOzeti(URUN, satir);
        var mAtcVeri = {{ content_ids:[id], content_type:"product", currency:"TRY" }};
        if(mAtc && mAtc.kurus != null){{ mAtcVeri.value = mAtc.kurus/100; }}
        if(typeof window.pruvoMetaTrack === "function"){{ window.pruvoMetaTrack("AddToCart", mAtcVeri); }}
      }} catch(e) {{}}
    }} else {{ c.splice(i,1); }}
    PRUVO_SECENEK.sepetKaydet(c); render();
  }});
  /* Filament kartlarını malzeme seçicisine çevir (yalnız kart-secim modu). Tıklanan kart
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
  }}
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
</script>
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
        img=esc(cover),
        product_ld=ld(product_ld),
        breadcrumb_ld=ld(breadcrumb_ld),
        css=PAGE_CSS,
        katq=esc(kategori),
        kategori=esc(kategori),
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
        icon=WA_ICON,
        pid=esc(p.get("id") or ""),
        cart_icon=CART_ICON,
        # Muhendislik-malzeme WA notu kartlarin altinda — malzeme dropdown'u kalan TEK
        # dal (semasiz-parametrik-fonksiyonel, bugun urun yok) haric her sayfada; o dalda
        # not zaten _malzeme_renk_html icinde, mukerrer basilmaz.
        malzeme=filament_html(p, wa_not=not (parametrik and fonksiyonel and not sema)),
        related=rel_html,
        foot_nav=FOOT_NAV_HTML,
        pay_band=PAY_BAND_HTML,
        attribution=attribution_html(p),
        urun_json=urun_json,
        sema_json=sema_json,
        kart_secim=("true" if kart_secim else "false"),
        eylem_butonlar=eylem_butonlar_html,
        konf_scripts=konf_scripts,
        onizleme_js=onizleme_js,
        whatsapp=WHATSAPP,
        ga_head=GA_HEAD_SNIPPET,
        meta_head=META_HEAD_SNIPPET,
        meta_view_content=meta_view_content,
        attribution_head=attribution_head_snippet(),
        ga_banner=GA_BANNER_SNIPPET,
    )
    # script src'lerine ?v=<icerik-hash> (onbellek kirici) — tek yer, yayin=render.
    return surumle_scriptler(doc)


# ------------------------------------------------------------------ içerik/yasal sayfa
def render_content_page(slug, title, meta, body_html):
    title_tag = esc(title) + " — PRUVO"
    url = SITE + "/" + slug + "/"
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
<style>{css}</style>
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
</body>
</html>
""".format(
        title=title_tag,
        desc=esc(meta),
        ogtitle=esc(title),
        url=esc(url),
        favicon=FAVICON,
        css=PAGE_CSS,
        body=body_html,
        foot_nav=FOOT_NAV_HTML,
        pay_band=PAY_BAND_HTML,
        pv_js=PV_SCRIPT_HTML,
        ga_head=GA_HEAD_SNIPPET,
        meta_head=META_HEAD_SNIPPET,
        attribution_head=attribution_head_snippet(),
        ga_banner=GA_BANNER_SNIPPET,
    ))


# ------------------------------------------------------------------ sitemap
def render_sitemap(products):
    urls = []
    urls.append((SITE + "/", "1.0", "daily"))
    for slug in SITEMAP_SLUGS:
        urls.append((SITE + "/" + slug + "/", "0.4", "monthly"))
    for p in products:
        urls.append((product_url(p["id"]), "0.8", "weekly"))
    items = []
    for loc, prio, freq in urls:
        items.append(
            "  <url>\n"
            "    <loc>%s</loc>\n"
            "    <lastmod>%s</lastmod>\n"
            "    <changefreq>%s</changefreq>\n"
            "    <priority>%s</priority>\n"
            "  </url>" % (esc(loc), TODAY, freq, prio))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(items) + "\n</urlset>\n")


# ------------------------------------------------------------------ Google Merchant feed
def render_merchant_feed(products):
    """Google Merchant Center urun feed'i (RSS 2.0 + g: namespace).
    SADECE parametrik OLMAYAN, sabit sayisal fiyatli, gorseli olan urunler girer;
    parametrik "sari seri" (net fiyati yok) HARIC tutulur. Dondurulen (xml, adet)."""
    items = []
    for p in products:
        if p.get("parametrik"):
            continue                                   # sari seri -> feed disi
        price = feed_price((p.get("fiyat") or "").strip())
        if not price:
            continue                                   # net sayisal fiyati yok -> feed disi
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
            "    <g:image_link>%s</g:image_link>" % esc(imgs[0]),
        ]
        for extra in imgs[1:11]:                        # Google en fazla 10 ek gorsel
            row.append("    <g:additional_image_link>%s</g:additional_image_link>" % esc(extra))
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


# ------------------------------------------------------------------ taban fiyat haritası
def uret_taban_fiyatlar():
    """taban-fiyatlar.js — ana sayfa sarı kartlarının "X TL'den başlayan" fiyatı buradan
    okur; kaynak jenerator/urunler/<id>.json tabanFiyatTL (TEK KAYNAK, elle kopya YOK —
    filament-veri.js deseni). tabanFiyatTL null/eksik olan şema haritaya GİRMEZ (kartta
    "Ölçüye özel fiyat" fallback'i). CI üretir, git'e girmez."""
    harita = {}
    if os.path.isdir(JEN_URUN_DIR):
        for ad in sorted(os.listdir(JEN_URUN_DIR)):
            if not ad.endswith(".json"):
                continue
            with open(os.path.join(JEN_URUN_DIR, ad), encoding="utf-8") as f:
                sema = json.load(f)
            taban = sema.get("tabanFiyatTL")
            if taban is not None:
                harita[sema.get("id") or ad[:-5]] = taban
    with open(os.path.join(ROOT, "taban-fiyatlar.js"), "w", encoding="utf-8") as f:
        f.write("/* tools/build.py uretir — ELLE DUZENLEME. "
                "Tek kaynak: jenerator/urunler/<id>.json tabanFiyatTL */\n"
                "window.PRUVO_TABAN_FIYATLAR = "
                + json.dumps(harita, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
                + ";\n")
    return harita


# ------------------------------------------------------------------ ana akış
def main():
    # --sadece-taban: yalnız taban-fiyatlar.js'i üret (kabul testi hızlı koşsun;
    # tam build 6900+ sayfa yazar). Deploy yine main()'in tamamını koşar.
    if "--sadece-taban" in sys.argv[1:]:
        harita = uret_taban_fiyatlar()
        print("OK: taban-fiyatlar.js uretildi (%d urun)." % len(harita))
        return

    with open(JSON_PATH, encoding="utf-8") as f:
        products = json.load(f)

    # Elle korunan dört içerik sayfasında yalnız işaretli attribution bloğunu yenile.
    # CI aynı dosyaları yayın klasörüne kopyaladığı için ayrı varlık/deploy değişikliği gerekmez.
    for slug in STATIK_SAYFALAR:
        statik_yol = os.path.join(ROOT, slug, "index.html")
        with open(statik_yol, encoding="utf-8") as f:
            statik_html = f.read()
        yenilenmis = attribution_ekle(statik_html)
        if yenilenmis != statik_html:
            with open(statik_yol, "w", encoding="utf-8") as f:
                f.write(yenilenmis)

    # eski urun/ klasörünü temizle (silinen ürünler kalmasın)
    if os.path.isdir(URUN_DIR):
        shutil.rmtree(URUN_DIR)
    os.makedirs(URUN_DIR, exist_ok=True)

    for p in products:
        pdir = os.path.join(URUN_DIR, p["id"])
        os.makedirs(pdir, exist_ok=True)
        with open(os.path.join(pdir, "index.html"), "w", encoding="utf-8") as f:
            f.write(render_product(p, products))

    # içerik/yasal sayfalar (/<slug>/index.html)
    for slug, title, meta, fn in CONTENT_PAGES:
        cdir = os.path.join(ROOT, slug)
        os.makedirs(cdir, exist_ok=True)
        with open(os.path.join(cdir, "index.html"), "w", encoding="utf-8") as f:
            f.write(render_content_page(slug, title, meta, fn()))

    # deploy.yml beyaz-listesi için TEK KAYNAK manifesti: içerik/yasal sayfa dizinleri
    # (statik hakkimizda/iletisim/sss/gizlilik + üretilen CONTENT_PAGES) = SITEMAP_SLUGS.
    # CI bu dosyayı okuyup her slug'ı _site'a kopyalar; böylece yeni CONTENT_PAGES eklenince
    # deploy.yml elle güncellenmese de SESSİZCE 404 olmaz (eski elle beyaz-liste tuzağı).
    with open(os.path.join(ROOT, "_yayin-icerik-dizinleri.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(SITEMAP_SLUGS) + "\n")

    # sitemap.xml
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(render_sitemap(products))

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
        f.write("/* tools/build.py uretir — ELLE DUZENLEME. Tek kaynak: tools/filamentler.json */\n"
                "window.PRUVO_FILAMENT = "
                + json.dumps(fil_ref, ensure_ascii=False, separators=(",", ":"))
                + ";\n")

    # taban-fiyatlar.js — sarı kart "X TL'den başlayan" haritası (tek kaynak: şemalar)
    uret_taban_fiyatlar()

    # index.built.html — ana sayfanin YAYIN kopyasi: script src'leri ?v=<hash> ile
    # surumlenir (KAYNAK index.html degismez). deploy.yml bunu _site/index.html yapar.
    # taban-fiyatlar.js YUKARIDA uretildi -> hash'i artik hesaplanabilir.
    with open(os.path.join(ROOT, "index.built.html"), "w", encoding="utf-8") as f:
        f.write(yayin_index())

    # robots.txt
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\n\nSitemap: " + SITE + "/sitemap.xml\n")

    # .nojekyll  (GitHub Pages tüm dosyaları olduğu gibi sunsun)
    open(os.path.join(ROOT, ".nojekyll"), "w").close()

    print("OK: %d urun sayfasi + sitemap.xml + robots.txt + merchant-feed.xml (%d urun) uretildi."
          % (len(products), feed_n))


if __name__ == "__main__":
    main()
