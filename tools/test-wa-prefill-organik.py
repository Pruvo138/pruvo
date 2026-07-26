#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kabul testi — ürün-sayfası BAĞLAM-KÖR WhatsApp prefill'leri (organik + malzeme notu).

Sorun: bu iki buton wa.me ?text= prefill'inde ürün adı/URL taşımıyordu -> Ege hangi ürün
sayfasından gelindiğini bilemiyor, lead düşüyor.

⚠️ NİYET EKSENİ (yalnız ad+URL YETMEZ):
  * help-cta-btn'in KENDİ metni "Aradığınız parçayı bulamadınız mı? ... üretelim!" ->
    butona basan müşteri SAYFADAKİ ürünü İSTEMİYOR, bulamadığı BAŞKA parçayı arıyor.
    Prefill "bu ürünü istiyorum" derse Ege yanlış niyetle o ürün için fiyat/malzeme
    akışı başlatır — bağlamsız olmasından BETER. Bu test bağlamın VAR olduğunu VE
    yanlış niyetin OLMADIĞINI BİRLİKTE assert eder.
  * malzeme-not linkinin niyeti AYRI (mühendislik malzemesi / özel üretim sorusu) ->
    o niyet KORUNMALI, help-cta'nın "bulamadım" niyetiyle karıştırılmamalı.

REF/reklam-atıf butonu (orderAlt "WhatsApp'tan Sor") FARKLI ve zaten doğru — bu test
onun BOZULMADIĞINI da (ad+URL hâlâ var) regresyon olarak doğrular.

🔴 NUMARA EKSENİ (ölçülmüş kör nokta, 26 Tem):
  Prefill nöbetleri LİNK LİNK yazılmıştı -> yalnız ADI GEÇEN butonlar korunuyordu.
  Ölçüm: wa_href() (ana sipariş butonu / orderAlt) numarası arama hattına çevrildiğinde
  23 CI kapısının HİÇBİRİ kırmızı yanmadı; aynı mutasyon help_cta_href()'te 2 kapı
  yakaladı. Yani koruma "hangi butonu saydıysam o" düzeyindeydi ve YENİ eklenen her
  buton NÖBETSİZ doğuyordu. Bu yüzden numara nöbeti KÜME olarak kurulur: sayfadaki
  TÜM WhatsApp URL'leri (wa.me · api./web.whatsapp.com/send?phone= · whatsapp://send)
  taranır, her birinin numarası tek tek doğrulanır -> gelecekte eklenen 4. bir buton
  hiçbir şey yazılmadan kapsama girer.
  FAIL-CLOSED: numarası AYRIŞTIRILAMAYAN bir WhatsApp linki (boşluklu/tireli/noktalı,
  eksik haneli) SESSİZCE ATLANMAZ -> KIRMIZI. Aksi halde link kümeye girip numarasız
  sayılıyor, sayı tabanın altına düşmediği için kaçak sahte-yeşil geçiyordu (ölçüldü).
  ÖLÇÜLEMEYEN TEK HAL (açıkça beyan edilir, her koşumda basılır): numarası kaynakta
  literal geçmeyen, JS'te değişkenle kurulan link parçası — bugünkü tek örneği
  attribution-ref.js eşleştirme dizesi, onun numarası TARGET_PHONE assert'iyle kapanır.
  Kural (CLAUDE.md): WhatsApp hattı = tüm wa.me linkleri · arama hattı = YALNIZ tel:/
  JSON-LD contactPoint. İki yön de denetlenir (arama hattı wa.me'de YOK, WhatsApp
  hattı tel:/contactPoint'te YOK).
  ⚠️ Numaralar bu dosyaya HARDCODE EDİLMEZ: build.py'nin kendi sabitlerinden türetilir
  (WhatsApp = build.WHATSAPP, arama = build.SELLER["tel"]) — aksi halde sabit değişince
  nöbetçi sessizce bayatlar.

🔴 KAPSAM GENİŞLETMESİ — ANA SAYFA + YASAL/İÇERİK SAYFALARI (26 Tem, ikinci ölçüm):
  Yukarıdaki numara nöbeti YALNIZ ürün sayfası düzlemini (build.render_product)
  kapatıyordu. Ölçüm: `index.html` ve `tools/sayfalar.py` (yasal + 168 içerik sayfası)
  düzleminde yanlış numara yayına girse HİÇBİR kapı yanmıyordu — oysa ana sayfanın
  sipariş butonlarının TAMAMI index.html'deki `var WHATSAPP` sabitinden kuruluyor
  (tek karakterlik sapma = tüm sipariş trafiği arama hattına gider) ve içerik
  sayfalarında numara 185 kez GÖRÜNÜR METİN olarak basılıyor.
  Bu yüzden nöbet 4 düzleme birden bakar (aynı sözleşme, tek dosya — ikinci nöbetçi
  dosya AÇILMADI):
    1) WhatsApp URL kümesi (yukarıdaki numara_kontrol — her belgede aynı)
    2) TERS YÖN: tel: href + JSON-LD telephone/contactPoint + pv-kodlu künye telefonu
       (yasal sayfada telefon düz metin değil, data-özniteliğine parçalanmış basılır ->
       nöbetçi pv çözücüsüyle okur, yoksa o alan tamamen kör kalırdı)
    3) JS TELEFON SABİTİ: `var WHATSAPP = "..."` / `var TARGET_PHONE = "..."` gibi
       linki ÇALIŞMA ZAMANINDA kuran sabitler (link literali sayfada yok -> URL taraması
       bunları göremez; adına göre hangi hatta ait olduğu belirlenir)
    4) GÖRÜNÜR METİN: sayfada basılan `+90 ...` biçimli telefon literali — WhatsApp
       bağlamı (whatsapp|wa.me geçen ±140 karakterlik pencere) içindeyse WhatsApp
       hattı olmak ZORUNDA. Ölçüldü: 186 gerçek literal, 0 yanlış-pozitif.
  ⚠️ KAPSAM TUZAĞI (bu repoda ölçülmüş): kapı "hangi elemanı koruyorum" ekseninde
  kurulmaz — numarayla İLGİSİZ rutin bir CSS/metin düzenlemesi bu nöbetçiyi ASLA
  kırmızı yakmamalı, yoksa tüm site deploy'u alakasız bir düzenlemeyle durur. Bu
  yüzden `fikstur_kontrol()` her koşumda İLGİSİZ RUTİN DÜZENLEME fikstürünü (yorum
  ekleme + meta açıklama değiştirme + renk değiştirme) çalıştırıp YEŞİL kalmayı da
  assert eder. Sabit sayı/SHA çapası KOYULMAZ: pozitif taban ya belgenin kendi
  içeriğinden ya da sayfalar.py KAYNAĞINDAKİ wa.me literal sayısından TÜRETİLİR.

Çalıştır:  python3 tools/test-wa-prefill-organik.py
Başarı = çıkış 0 + "PASS". Herhangi bir assert kırmızı = çıkış 1 + "FAIL".
"""
import json
import os
import re
import sys
import html as _html
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import sayfalar  # noqa: E402  (yasal/içerik sayfalarının TEK kaynağı)

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Türkçe karakterlerin TAMAMINI (ç ğ ı ö ş ü İ) + boşluk + em-dash içeren örnek ürün.
URUN = {
    "id": "test-turkce-baglanti-parcasi",
    "kategori": "Otomobil",
    "marka": ["Ford"],
    "baslik": u"Çğıöşü Bağlantı Parçası — Ön Döşeme İç",
    "aciklama": u"Test açıklaması.\nYaklaşık dış ölçüler: 10 × 20 × 30 mm",
    "fiyat": "850 TL",
    "gorseller": ["https://media.pruvo3d.com/urunler/test-1.jpg"],
}

# NUMARA nöbeti ÜRÜN TİPİNDEN bağımsız olmalı: parametrik (sarı) sayfa farklı buton
# seti basar (.order-wa vs .ikon-wa), lisanslı üründe atıf bloğu eklenir. Kör nokta tam
# olarak "başka şablon dalı = nöbetsiz link" sınıfıydı -> numara kontrolü üç tipte de koşar.
URUN_LISANSLI = {
    "id": "test-lisansli-urun",
    "kategori": "Ev",
    "marka": [],
    "baslik": u"Lisanslı Test Ürünü",
    "aciklama": u"Test açıklaması.\nYaklaşık dış ölçüler: 5 × 5 × 5 mm",
    "fiyat": "300 TL",
    "gorseller": ["https://media.pruvo3d.com/urunler/test-lisans-1.jpg"],
    "lisans": {"tasarimci": "stensino", "tur": "CC BY 4.0"},
}
URUN_PARAMETRIK = {
    "id": "test-parametrik-urun",
    "kategori": u"Jeneratör",
    "marka": [],
    "baslik": u"Parametrik Test Kelepçesi",
    "aciklama": u"Ölçüye özel üretilir.",
    "fiyat": "",
    "parametrik": True,
    "gorseller": ["https://media.pruvo3d.com/urunler/test-param-1.jpg"],
}

# ÇALIŞAN WhatsApp link biçimlerinin TAMAMI (şema opsiyonel: JS içinde "wa.me/" +
# değişken biçiminde de kurulabiliyor). Doğrulanmış biçimler:
#   https://wa.me/<numara>?text=...               Click-to-Chat — sitenin kullandığı biçim
#   https://api.whatsapp.com/send?phone=<numara>  eski resmî biçim (attribution-ref.js de tanır)
#   https://web.whatsapp.com/send?phone=<numara>  masaüstü web akışı — ÇALIŞAN link
#   whatsapp://send?phone=<numara>                uygulama derin-linki (custom scheme)
# ⚠️ web.whatsapp.com bu regex'te YOKTU (26 Tem bypass avı): o biçimde eklenen bir buton
# müşteriyi sessizce ARAMA hattına gönderebilirdi ve hiçbir kapı yanmazdı.
# KAPSAM DIŞI (bilerek, numara TAŞIMADIĞI için): chat.whatsapp.com/<davet-kodu> = grup daveti.
# ?text= içeriği KASITLI olarak tarama dışı (orada ürün URL'i/ölçüsü kaynaklı uzun rakam
# dizisi yanlış-pozitif üretirdi) — numara YALNIZ yoldan ya da ?phone='dan okunur.
# TARAMA BELGE GENELİDİR, "href=" ile SINIRLI DEĞİL: sipariş butonunun href'i JS'te de
# kuruluyor (orderAlt.href = "https://wa.me/..."), href'e daraltmak o yolu nöbetsiz
# bırakırdı. BEYAN EDİLEN SONUÇ: sayfaya GÖRÜNÜR METİN olarak yazılmış bir
# "wa.me/<numara>" dizisi de denetlenir (ör. ürün başlığında). Bu bilerekdir — arama
# hattını wa.me ile yan yana BASMAK da aynı kuralın ihlalidir. Ölçüldü: 344 gerçek
# üründe bu yüzden tek bir kırmızı bile yok (sentetik olarak zorlandığında yanıyor).
# ⚠️ IGNORECASE: host ve şema HARF-DUYARSIZ eşleşir — "https://WA.ME/<numara>" ve "Wa.Me/..."
# tarayıcıda AYNI linktir (host case-insensitive), ama nöbetçiden kaçıyordu (ölçüldü: N14/N15).
# Bayrak YALNIZ URL yakalamayı etkiler; numara/?phone= AYRIŞTIRMASI ayrı fonksiyonda ve
# rakam kalıbı harf içermediği için davranışı DEĞİŞMEZ. Ölçüldü: 12.234 üründe 0 fazladan
# eşleşme. chat.whatsapp.com harf-duyarsızlıkla da kapsama GİRMEZ (alternasyonda yok).
WA_URL_RE = re.compile(
    r"(?<![\w.-])(?:https?://)?(?:wa\.me|api\.whatsapp\.com|web\.whatsapp\.com)/[^\s\"'<>]*"
    r"|(?<![\w.-])whatsapp://[^\s\"'<>]*", re.IGNORECASE)
# Geçerli uluslararası numara: yalnız rakam (baştaki + serbest), 10-15 hane. Boşluklu/
# tireli/noktalı bir "numara" bu kalıba UYMAZ -> ayrıştırılamaz sayılır (fail-closed).
GECERLI_NUMARA_RE = re.compile(r"\+?\d{10,15}")
# "Belgede literal numaralı wa.me linki VAR MI" sorusunun BAĞIMSIZ cevabı (WA_URL_RE'den
# ayrı kalıp): pozitif nöbetin çapası budur -> WA_URL_RE körleşirse bu hâlâ görür.
LITERAL_WA_RE = re.compile(r"wa\.me/\d{6,}", re.IGNORECASE)
# Sayfaya gömülen ref-atıf betiğinin wa.me EŞLEŞTİRME sabiti (attribution-ref.js).
# build.WHATSAPP'tan sapması sessiz hatadır: linkler doğru numarayı taşır ama betik
# onları WhatsApp linki olarak TANIMAZ -> reklam atfı (ref) sessizce düşer.
TARGET_PHONE_RE = re.compile(r'TARGET_PHONE\s*=\s*"([^"]*)"')
# Ters yön: arama hattına ait alanlar.
TEL_HREF_RE = re.compile(r'href="\s*(tel:[^"]*)"')
TEL_ALAN_ANAHTARLARI = ("telephone", "contactPoint", "faxNumber")
# Numara TAŞIMASI beklenen skaler alanlar: değeri boşsa/rakamsızsa KIRMIZI (kırık alan).
# "contactPoint" bir KAPSAYICIDIR (içinde e-posta da olabilir) -> boşluğu kırmızı değildir.
TEL_SKALER_ANAHTARLAR = ("telephone", "faxNumber")

# --- pv (kişisel veri koruması) çözücü: yasal sayfada telefon DÜZ METİN basılmaz.
# sayfalar.pv_html değeri 2-3 karakterlik parçalara bölüp data-a..data-l özniteliklerine
# KARIŞIK SIRADA koyar; tarayıcı doğru sırada birleştirir. Nöbetçi de aynı sırayı
# uygular, yoksa künye telefonu (= arama hattı) TAMAMEN kör kalırdı: oraya WhatsApp
# numarası yazılsa ham metinde hiçbir arama tutmazdı (ölçüldü).
PV_SPAN_RE = re.compile(r'<span class="pv pv-blok"((?:\s+data-[a-l]="[^"]*")+)\s*></span>')
PV_ATTR_RE = re.compile(r'data-([a-l])="([^"]*)"')
PV_ALFABE = "abcdefghijkl"
# Künye tablosundaki telefon hücresi (sayfalar._seller_table) + JS'in tel: kuracağı bağ.
# ⚠️ Etiket metni ESNEK eşleşir ("Telefon", "Telefon (arama)", "Telefon / Faks"): etiketi
# birebir çapalamak, alakasız bir etiket düzenlemesinde pozitif nöbeti sessizce öldürürdü.
PV_TELEFON_HUCRE_RE = re.compile(r"<td>\s*Telefon[^<]*</td>\s*<td>(.*?)</td>", re.S)
PV_TEL_BAG_RE = re.compile(r'<a[^>]*data-pv-link="tel"[^>]*>(.*?)</a>', re.S)

# --- JS telefon sabiti: linki ÇALIŞMA ZAMANINDA kuran numara (URL taraması göremez).
# ör. index.html `var WHATSAPP = "905451386526";` -> ana sayfadaki TÜM sipariş
# butonlarının numarası buradan gelir; attribution-ref.js `var TARGET_PHONE = "..."`.
JS_TEL_SABIT_RE = re.compile(
    r'(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=\s*"([+\d][\d\s().+\-]{8,22})"')
# Sabitin hangi hatta ait olduğu ADINDAN belirlenir. ARAMA önce bakılır ki "CALL_PHONE"
# gibi iki kümeye de uyan bir ad WhatsApp sanılmasın.
ARAMA_ADI_RE = re.compile(r"(?:^|_)(TEL|CALL|ARAMA|SABIT|CAGRI)(?:_|$)", re.I)
WA_ADI_RE = re.compile(r"whats?app|wa_?(?:num|no|phone|hat)|phone", re.I)

# --- görünür metin düzlemi: sayfaya BASILAN telefon literali.
# KATI +90 biçimi (ölçüm gerekçesi): gevşek "10-15 hane" kalıbı etiket temizliğinden
# sonra cümleler arası rakamları birleştirip sahte aday üretiyordu (168 sayfada 2 adet:
# "...6526" + " 3-5 iş günü"). Katı biçim + rakam-lookahead ile 168 sayfada 185 gerçek
# literal, 0 sahte aday ölçüldü.
KATI_TEL_RE = re.compile(
    r"\+90[\s.\-]?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{2}[\s.\-]?\d{2}(?!\d)")
WA_BAGLAM_RE = re.compile(r"whatsapp|wa\.me", re.I)
# Nötr bağlamdaki literalin NİYETİNİ sınıflandırmak için (kural DEĞİL, yalnız ÖLÇÜM):
# "... numarasına GÖNDERİN/YAZIN/İLETİN" = mesajlaşma niyeti -> pratikte WhatsApp hattı.
# Bu sınıflandırma kırmızı yakmaz; kör nokta raporunda SAYIYLA yayınlanır ki kuralın
# yazılabilir olup olmadığı ölçümle görülsün (bugün: hepsi tek "Sipariş" şablonundan).
MESAJ_FIIL_RE = re.compile(r"gönderin|gonderin|yazın|yazin|iletin|at[ıi]n", re.I)
GORUNUR_PENCERE = 140          # literalin SOLUNDA bakılan karakter (bağlam cümlesi)

# Sayfada GEÇERLİ numara taşıyan EN AZ bu kadar WhatsApp linki bulunmalı (bugün ölçülen:
# 4 — help-cta, malzeme-not, orderAlt statik href, orderAlt'ı JS'te yeniden kuran satır).
# TABAN'dır, çapa DEĞİL: yeni buton eklenince kırmızı yanmaz, ama linkler toptan
# kaybolup küme kontrolü BOŞ kümeye bakarak sahte-yeşil yanamaz.
# ⚠️ TABAN ARTIK "YUTMAZ": ayrıştırılamayan numara sayıyı düşürüp tabanın altına saklanmak
# yerine DOĞRUDAN kırmızı yakar (aşağıda fail-closed), yani taban bir mazeret yolu değil.
WA_URL_TABAN = 3

# help-cta prefill'inde BULUNMAMASI gereken "bu ürünü istiyorum" niyet kalıpları.
# (Buton "aradığını bulamayan" müşteri içindir — sayfadaki ürünü talep ETMEZ.)
YANLIS_NIYET = [
    u"bu ürünü istiyorum",
    u"bu parça hakkında bilgi almak istiyorum",
    u"bu ürün hakkında bilgi almak istiyorum",
    u"şu ürünle ilgileniyorum",
    u"bu ürünle ilgileniyorum",
]


def _wa_text(href):
    """wa.me href'inden ?text= parametresini alıp URL-decode eder.
    Önce HTML-unescape (attribute bağlamı), sonra percent-decode."""
    href = _html.unescape(href)
    parts = href.split("?text=", 1)
    if len(parts) != 2:
        return None
    return unquote(parts[1])


def _kodlama_kontrol(ad, href, metin, fails):
    """Ortak kodlama/numara nöbetleri (her wa.me linki için aynı sözleşme)."""
    if ("wa.me/" + build.WHATSAPP) not in href:
        fails.append("%s: doğru WhatsApp numarasını kullanmıyor" % ad)
    if "4005" in href:
        fails.append("%s: arama numarası (4005) var — yasak" % ad)
    # Ham (kodlanmamış) Türkçe karakter / boşluk URL'de OLMAMALI.
    for ham in u"çğıöşü ":
        if ham in href:
            fails.append("%s: HAM kodlanmamış karakter var: %r" % (ad, ham))
            break
    # Decode sonrası '%' kalıntısı = double-encode şüphesi.
    if metin and "%" in metin:
        fails.append("%s: decode sonrası '%%' kalıntısı — double-encode şüphesi" % ad)


def _rakam(s):
    return re.sub(r"\D", "", s or "")


def numaralar():
    """(whatsapp, arama) — İKİSİ DE build.py'nin kendi sabitlerinden TÜRETİLİR.

    whatsapp = build.WHATSAPP (tüm wa.me linklerinin numarası)
    arama    = build.SELLER["tel"] (künye/yasal sayfa telefonu = arama hattı)
    Teste hardcode edilmemesinin sebebi: sabit değişince nöbetçi sessizce bayatlar
    (eski numarayı doğru sanıp yeni yanlışı görmez)."""
    return _rakam(build.WHATSAPP), _rakam((build.SELLER or {}).get("tel"))


def wa_numara_adaylari(url):
    """Bir WhatsApp linkinin numara TAŞIYAN yerlerini [(kaynak, ham değer)] döndür.

    Biçime göre değişir (ezberle değil, gerçek link biçimlerine göre):
      * wa.me      -> numara YOLDA          (wa.me/<numara>)
      * send'li biçimler (api./web.whatsapp.com, whatsapp://) -> ?phone= SORGUSUNDA
        (yolları sabit "send"dir, numara taşımaz -> yol taranmaz, yoksa "send" hep
        ayrıştırılamayan numara sanılıp yanlış-pozitif üretirdi)
      * wa.me/message/<KOD> -> KISA LİNK, numara TAŞIMAZ (aşağıdaki wa_kisa_link_mi)
    Boş liste = link numara literali taşımıyor (JS'te değişkenle kuruluyor)."""
    # Şema/host HARF-DUYARSIZ karşılaştırılır (WA.ME/... tarayıcıda aynı linktir; küçük
    # harfe indirmezsek host eşleşmesi tutmaz ve numara YOLDAN hiç okunmazdı -> N14/N15).
    # Numaranın KENDİSİ asla küçültülmez/değiştirilmez (rakam, harf-duyarsızlığı yok).
    if url.lower().startswith("whatsapp://"):
        host, kalan = "whatsapp", url[len("whatsapp://"):]
    else:
        kalan = re.sub(r"^https?://", "", url, flags=re.IGNORECASE)
        host, _, kalan = kalan.partition("/")
        host = host.lower()
    yol, _, sorgu = kalan.partition("?")
    adaylar = []
    if host == "wa.me":
        seg = yol.strip("/")
        if seg:
            adaylar.append(("yol", unquote(seg)))
    # Anahtar adı da harf-duyarsız aranır (?Phone=). "(?:^|&)" çapası sayesinde
    # "telephone=" gibi daha uzun bir anahtarın sonuna yanlış eşleşmez.
    q = re.search(r"(?:^|&)phone=([^&]*)", sorgu, re.IGNORECASE)
    if q and q.group(1):
        adaylar.append(("phone=", unquote(q.group(1))))
    return adaylar


def wa_kisa_link_mi(url):
    """RESMÎ kısa link mi: https://wa.me/message/<KOD> (numara TAŞIMAZ) -> KOD, yoksa None.

    ⚠️ Bu biçim numara içermez; kod WhatsApp Business hesabına bağlıdır. Numara kuralı
    UYGULANAMAZ -> "ayrıştırılamadı" diye KIRMIZI yakmak YANLIŞ-POZİTİFTİR (meşru resmî
    link tüm site deploy'unu durdururdu). SESSİZCE de yutulmaz: her koşumda görünür bir
    bilgi satırı basılır ve kör nokta listesinde yer alır — o kod BAŞKA bir numaraya
    bağlı olabilir ve bunu bu nöbetçi ÖLÇEMEZ (kodun hangi hatta gittiği yalnız WhatsApp
    Business panelinden görülür)."""
    if url.lower().startswith("whatsapp://"):
        return None
    kalan = re.sub(r"^https?://", "", url, flags=re.IGNORECASE)
    host, _, kalan = kalan.partition("/")
    if host.lower() != "wa.me":
        return None
    yol = kalan.partition("?")[0].strip("/")
    parcalar = yol.split("/")
    if len(parcalar) >= 2 and parcalar[0].lower() == "message" and parcalar[1]:
        return parcalar[1]
    return None


def numara_kontrol(ad, doc, fails, taban=None, sessiz=False):
    """KÜME nöbeti: sayfadaki TÜM WhatsApp URL'lerinin numarasını doğrula.

    Tek tek href yakalamak yerine belgedeki her wa.me/api.whatsapp.com URL'i taranır
    -> sonradan eklenen butonlar da otomatik kapsanır (kör noktanın kendisi buydu).

    taban:  literal numara taşıyan link için pozitif alt sınır. None = belge tipine
            özel sayı YOK; bunun yerine TÜRETİLMİŞ boş-küme nöbeti çalışır (aşağıda).
            Ürün sayfası WA_URL_TABAN ile çağrılır (mevcut davranış korunur).
    sessiz: 168 içerik sayfası taranırken satır satır rapor basmamak için.

    Dönüş: (literal_link_sayisi, dinamik_link_sayisi) — çağıran korpus toplamı alabilsin."""
    wa, arama = numaralar()
    # Sabitlerin kendisi sağlam mı (fail-closed: türetme çalışmıyorsa nöbet anlamsız).
    if len(wa) < 10:
        fails.append("%s: build.WHATSAPP geçersiz/boş (%r) — numara nöbeti kurulamaz" % (ad, wa))
        return (0, 0)
    # Arama hattı yalnız TEŞHİSİ zenginleştirir (hangi yanlış numara?) — türetilemese
    # bile wa.me küme taraması SÜRER (kırmızı yine yanar), sadece kaydedilir.
    if len(arama) < 10:
        fails.append("%s: arama hattı build.SELLER['tel']'den türetilemedi (%r) — "
                     "ters yön denetimi kör kalır" % (ad, arama))
    elif wa == arama:
        fails.append("%s: WhatsApp ve arama numarası AYNI (%s) — CLAUDE.md hat ayrımı "
                     "çökmüş" % (ad, wa))

    bulunan = []          # (url, numara) — GEÇERLİ ayrıştırılmış numaralar (HAM metinden)
    dinamik = []          # numara LİTERALİ taşımayan link parçası (JS'te değişkenle kurulan)
    kisa = []             # wa.me/message/<KOD> — numara TAŞIMAYAN resmî kısa link
    gorulen = set()       # aynı ihlali iki taramada iki kez bildirme

    def _tara(metin, tabana_say):
        for m in WA_URL_RE.finditer(metin):
            url = _html.unescape(m.group(0))
            kod = wa_kisa_link_mi(url)
            if kod:
                # Numara TAŞIMAYAN resmî biçim -> numara kuralı uygulanamaz (kapsam dışı).
                # KIRMIZI YAKILMAZ (meşru link deploy'u durduramaz) ama SESSİZ de kalmaz:
                # aşağıda görünür bilgi satırı basılır.
                if tabana_say:
                    kisa.append((url, kod))
                continue
            adaylar = wa_numara_adaylari(url)
            if not adaylar:
                if tabana_say:
                    dinamik.append(url)
                continue
            for kaynak, ham in adaylar:
                if not GECERLI_NUMARA_RE.fullmatch(ham):
                    # FAIL-CLOSED: ayrıştırılamayan numara SESSİZCE ATLANMAZ. Boşluk/tire/
                    # nokta ya da eksik hane -> link ya bozuk ya da denetimden kaçırma
                    # girişimi; atlanırsa taban(3) onu "yutar", kaçak sahte-yeşil geçerdi.
                    anahtar = ("ayristirilamaz", url, ham)
                    if anahtar not in gorulen:
                        gorulen.add(anahtar)
                        fails.append(
                            "%s: WhatsApp linkinin numarası AYRIŞTIRILAMADI (%s=%r, rakama "
                            "indirgenince %r%s) — sessizce ATLANMAZ, KIRMIZI -> %r"
                            % (ad, kaynak, ham, _rakam(ham),
                               ", bu ARAMA hattı" if _rakam(ham) == arama else "", url[:120]))
                    continue
                n = _rakam(ham)
                if tabana_say:
                    bulunan.append((url, n))
                if n != wa:
                    anahtar = ("yanlis", url, n)
                    if anahtar not in gorulen:
                        gorulen.add(anahtar)
                        fails.append(
                            "%s: WhatsApp linki YANLIŞ numara taşıyor (%s, beklenen %s)%s "
                            "-> %r"
                            % (ad, n, wa,
                               " — bu ARAMA hattı, WhatsApp linkinde ASLA olmaz"
                               if n == arama else "", url[:120]))

    _tara(doc, True)
    # İKİNCİ TARAMA — VARLIK-KODLU gizleme: href="https://wa&#46;me/<numara>" tarayıcıda
    # ÇALIŞAN bir linktir ama ham metinde regex'e görünmez (ölçüldü). Çözülmüş metin
    # YALNIZ İHLAL ARAR: tabana ve dinamik listesine SAYILMAZ, yoksa her link iki kez
    # sayılıp taban anlamsızlaşırdı (pozitif nöbetçiyi kapsam büyütmeyle öldürme tuzağı).
    cozulmus = _html.unescape(doc)
    if cozulmus != doc:
        _tara(cozulmus, False)
    if not sessiz:
        print("  [%s] WhatsApp link sayısı=%d, numaralar=%s"
              % (ad, len(bulunan), sorted(set(n for _, n in bulunan)) or "-"))
    if dinamik and not sessiz:
        # Bu biçimin numarası kaynakta LİTERAL geçmez -> burada ÖLÇÜLEMEZ (açıkça beyan).
        # Bugünkü tek örneği attribution-ref.js'in eşleştirme dizesi; onun numarası
        # aşağıdaki TARGET_PHONE assert'iyle kapatılıyor.
        print("  [%s] NOT: numara LİTERALİ taşımayan %d WhatsApp link parçası — numarası "
              "ÖLÇÜLEMEZ (değişkenle kuruluyor): %s" % (ad, len(dinamik), dinamik[:2]))
    if kisa and not sessiz:
        print("  [%s] BİLGİ: %d adet wa.me/message/<KOD> kısa linki — numara TAŞIMAZ, "
              "numara kuralı UYGULANAMAZ (kod başka bir hatta bağlı olabilir, bu "
              "nöbetçi ÖLÇEMEZ): %s" % (ad, len(kisa), [k for _u, k in kisa][:3]))
    if taban is not None and len(bulunan) < taban:
        fails.append("%s: geçerli numara taşıyan WhatsApp linki %d < taban %d — sipariş/"
                     "iletişim linkleri kaybolmuş ya da regex artık tutmuyor (küme "
                     "kontrolü BOŞ kümeye bakıp sahte-yeşil yanamaz)"
                     % (ad, len(bulunan), taban))
    # TÜRETİLMİŞ boş-küme nöbetleri (her belgede, SAYI ÇAPASI OLMADAN). İkisi de
    # belgenin KENDİ içeriğinden türer; başka bir dosyanın sayısına BAĞLANMAZ
    # (kaynak dosyadaki literal sayısına bağlamak meşru değişimi kırmızı yakıyordu:
    # sayfa CONTENT_PAGES'ten çıkınca korpus düşer, kaynağa yorum eklenince kaynak artar).
    # (1) belgede "wa.me/" geçiyorsa tarama en az bir şey üretmeli (regex tamamen bozuldu mu)
    if "wa.me/" in doc.lower() and not bulunan and not dinamik and not kisa:
        fails.append("%s: belgede 'wa.me/' geçiyor ama numara taraması HİÇ link "
                     "üretmedi — WA_URL_RE artık tutmuyor, küme nöbeti kör" % ad)
    # (2) belgede LİTERAL numaralı bir wa.me linki geçiyorsa en az bir tanesi
    #     AYRIŞTIRILMIŞ olmalı (literal tarayıcı körleşti mi)
    if LITERAL_WA_RE.search(doc) and not bulunan:
        fails.append("%s: belgede literal 'wa.me/<numara>' var ama ayrıştırılmış link "
                     "YOK — literal tarayıcı kör (numara nöbeti sahte-yeşil yanardı)" % ad)

    # Gömülü ref-atıf betiğinin eşleştirme sabiti de AYNI numara olmalı (sessiz drift).
    hedefler = TARGET_PHONE_RE.findall(doc)
    if not hedefler and not sessiz:
        print("  [%s] NOT: TARGET_PHONE sabiti sayfada yok — ref-atıf eşleşmesi "
              "ÖLÇÜLEMEDİ" % ad)
    for t in hedefler:
        if _rakam(t) != wa:
            fails.append("%s: gömülü ref-atıf betiğinin TARGET_PHONE'u (%s) "
                         "build.WHATSAPP (%s) ile UYUŞMUYOR — linkler doğru numarayı "
                         "taşısa bile betik onları tanımaz, ref atfı sessizce düşer"
                         % (ad, t, wa))
    return (len(bulunan), len(dinamik))


def pv_coz(parca):
    """pv-kodlu (parçalanmış data-özniteliği) değerleri gerçek metne çevirir.

    sayfalar.py kişisel veriyi (ad/adres/VKN/TELEFON/e-posta) düz metin basmaz: 2-3
    karakterlik parçalara bölüp data-a..data-l özniteliklerine KARIŞIK SIRADA koyar,
    tarayıcı alfabetik sırada birleştirir. Nöbetçi de aynısını yapar; yoksa künye
    telefonu (arama hattı) ham metinde HİÇ görünmediği için o alan tamamen kör kalır."""
    cikti = []
    for m in PV_SPAN_RE.finditer(parca):
        d = dict(PV_ATTR_RE.findall(m.group(1)))
        cikti.append(_html.unescape("".join(d.get(k, "") for k in PV_ALFABE)))
    return cikti


def ters_yon_kontrol(ad, doc, fails, sessiz=False):
    """TERS YÖN: WhatsApp numarası ARAMA alanlarında GEÇMEZ + oradaki numara TANINIR.

    Arama hattı alanları: tel: href · JSON-LD telephone/contactPoint/faxNumber ·
    yasal sayfa künyesindeki pv-kodlu "Telefon" hücresi (+ data-pv-link="tel" bağı).
    İki yönlü fail-closed:
      * alanda WhatsApp numarası -> KIRMIZI (hat ayrımı ihlali)
      * alandaki numara arama hattı DEĞİLSE (tanınmayan/ayrıştırılamayan) -> KIRMIZI;
        sessizce "bilmiyorum" denip geçilmez.
    Ürün sayfasında bu alanların hiçbiri basılmaz -> orada BOŞ KÜMEYE bakar ve bunu
    açıkça yazar (uydurma pozitif assert eklenmez)."""
    wa, arama = numaralar()
    if len(wa) < 10:
        return 0
    alanlar = []          # (nerede, ham değer)
    # tel: href taraması BETİK GÖVDELERİ ÇIKARILARAK yapılır: pv betiği içinde
    # `a.href="tel:"+d...` satırı geçiyor ve ham metinde BOŞ bir tel: href gibi
    # görünüyordu -> 168 sayfada sahte kırmızı (ölçüldü, bu yüzden ayrı düzlem).
    # O yolun GERÇEK numarası pv parçalarından gelir ve aşağıda pv bağı olarak okunur.
    doc_betiksiz = re.sub(r"<script.*?</script>", " ", doc, flags=re.S)
    for m in TEL_HREF_RE.finditer(doc_betiksiz):
        alanlar.append(("tel: href", m.group(1)))
    for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', doc, re.S):
        try:
            veri = json.loads(m.group(1))
        except ValueError:
            continue      # JSON-LD biçim denetimi AYRI testlerin işi (test-jsonld-*)
        yigin = [veri]
        while yigin:
            d = yigin.pop()
            if isinstance(d, dict):
                for k, v in d.items():
                    if k in TEL_ALAN_ANAHTARLARI:
                        alanlar.append(("JSON-LD " + k, json.dumps(v, ensure_ascii=False)))
                    yigin.append(v)
            elif isinstance(d, list):
                yigin.extend(d)
    # pv-kodlu künye telefonu (yasal/içerik sayfaları): çözülüp aynı sözleşmeye sokulur.
    for m in PV_TELEFON_HUCRE_RE.finditer(doc):
        for deger in pv_coz(m.group(1)):
            alanlar.append(("künye pv Telefon hücresi", deger))
    for m in PV_TEL_BAG_RE.finditer(doc):
        for deger in pv_coz(m.group(1)):
            alanlar.append(('data-pv-link="tel" bağı', deger))
    # KÜRESEL NEGATİF pv nöbeti: HİÇBİR pv bloğu WhatsApp numarası taşımaz (künye
    # tablosu dışında düz cümle içinde de pv telefon basılıyor — ör. "cayma bildirimini
    # ... numarasından iletin"). Pozitif "arama hattı OLMALI" kuralı yalnız Telefon
    # hücresine uygulanır: pv blokları adres/VKN gibi rakam taşıyan başka değerler de
    # içerir, hepsine numara şartı koymak alakasız kırmızı üretirdi.
    # (negatif küresel · pozitif sayfa bazlı — bu repoda ölçülmüş kapsam kuralı)
    for deger in set(pv_coz(doc)):
        if wa in _rakam(deger):
            fails.append("%s: pv-kodlu (kişisel veri korumalı) blokta WHATSAPP numarası "
                         "(%s) var — pv blokları satıcı künyesi/arama hattı içindir: %r"
                         % (ad, wa, deger[:120]))
    if not alanlar:
        if not sessiz:
            print("  [%s] TERS YÖN ÖLÇÜLEMEDİ: sayfada hiç tel: href / JSON-LD %s alanı / "
                  "pv künye telefonu yok" % (ad, "|".join(TEL_ALAN_ANAHTARLARI)))
        return 0
    if not sessiz:
        print("  [%s] ters yön alan sayısı=%d" % (ad, len(alanlar)))
    for nerede, deger in alanlar:
        d = _rakam(deger)
        if wa in d:
            fails.append("%s: %s alanında WHATSAPP numarası (%s) var — orada YALNIZ "
                         "arama hattı olur: %r" % (ad, nerede, wa, deger[:120]))
            continue
        if not d:
            # KAPSAYICI alan (contactPoint) numarasız olabilir (yalnız e-posta/saat
            # taşıyabilir) -> not düşülür. SKALER telefon alanı / tel: bağı / künye
            # telefon hücresi numarasız olamaz -> KIRMIZI (fail-closed).
            if nerede == "JSON-LD contactPoint":
                if not sessiz:
                    print("  [%s] NOT: JSON-LD contactPoint numarasız (kapsayıcı) — "
                          "ÖLÇÜLEMEZ: %r" % (ad, deger[:80]))
            else:
                fails.append("%s: %s alanında hiç rakam YOK (%r) — arama hattı alanı "
                             "numarasız kalamaz, sessizce ATLANMAZ" % (ad, nerede, deger[:120]))
            continue
        if len(arama) >= 10 and d != arama:
            fails.append("%s: %s alanındaki numara TANINMIYOR (%s; beklenen arama hattı "
                         "%s) — fail-closed KIRMIZI: %r"
                         % (ad, nerede, d, arama, deger[:120]))
    return len(alanlar)


def js_sabit_kontrol(ad, doc, fails, sessiz=False):
    """JS TELEFON SABİTİ nöbeti: linki ÇALIŞMA ZAMANINDA kuran numara.

    index.html'in sipariş butonlarının TAMAMI `var WHATSAPP = "..."` sabitinden
    kuruluyor -> sayfada o linklerin numara literali YOK, URL taraması onları göremez.
    Sabit arama hattına çevrilirse tüm sipariş trafiği sessizce telefona giderdi.
    Hangi hatta ait olduğu ADINDAN belirlenir (ARAMA kümesi önce bakılır ki
    "CALL_PHONE" gibi iki kümeye de uyan ad WhatsApp sanılmasın). Adı hiçbir kümeye
    uymayan telefon-benzeri sabit YARGILANMAZ ve kör nokta olarak SAYILIR."""
    wa, arama = numaralar()
    if len(wa) < 10:
        return (0, 0)
    yargilanan = yargisiz = 0
    for m in JS_TEL_SABIT_RE.finditer(doc):
        isim, ham = m.group(1), m.group(2)
        d = _rakam(ham)
        if len(d) < 10:
            continue                      # telefon değil (sürüm/tarih dizesi vb.)
        if ARAMA_ADI_RE.search(isim):
            beklenen, hat = arama, "arama"
        elif WA_ADI_RE.search(isim):
            beklenen, hat = wa, "WhatsApp"
        else:
            yargisiz += 1
            continue
        yargilanan += 1
        if len(beklenen) < 10:
            continue                      # sabit türetilemedi (yukarıda zaten kırmızı)
        if d != beklenen:
            fails.append(
                "%s: JS sabiti %s = %r %s hattı OLMALI (%s) ama %s taşıyor%s — bu sabitten "
                "kurulan TÜM linkler yanlış hatta gider"
                % (ad, isim, ham, hat, beklenen, d,
                   " (bu DİĞER hat)" if d in (wa, arama) else " (TANINMAYAN numara)"))
    if not sessiz:
        print("  [%s] JS telefon sabiti: yargılanan=%d, adı sınıflanamayan=%d"
              % (ad, yargilanan, yargisiz))
    return (yargilanan, yargisiz)


def gorunur_metin(doc):
    """Sayfanın GÖRÜNÜR metni (script/style atılır, etiketler boşlukla değiştirilir)."""
    m = re.sub(r"<script.*?</script>", " ", doc, flags=re.S)
    m = re.sub(r"<style.*?</style>", " ", m, flags=re.S)
    m = re.sub(r"<!--.*?-->", " ", m, flags=re.S)
    return _html.unescape(re.sub(r"<[^>]+>", " ", m))


def gorunur_numara_kontrol(ad, doc, fails, sessiz=False):
    """GÖRÜNÜR METİN nöbeti: sayfaya BASILAN telefon literali (link değil, yazı).

    İçerik sayfalarında numara 185 kez düz yazı olarak geçiyor ("... WhatsApp
    hattımıza gönderin: +90 ... "). Link taraması bunları GÖRMEZ; yanlış hat
    yazılırsa müşteri WhatsApp sanıp telefonu tuşlar (ya da tersi) ve hiçbir kapı
    yanmazdı. İki assert:
      (1) her literal BİLİNEN bir hat olmalı (değilse fail-closed KIRMIZI),
      (2) literal WhatsApp bağlamı içindeyse (GORUNUR_PENCERE karakterlik pencerede
          whatsapp|wa.me geçiyorsa) WhatsApp hattı OLMAK ZORUNDA.
    Nötr bağlamdaki literalin hangi hat olması gerektiği YARGILANMAZ (kör nokta)."""
    wa, arama = numaralar()
    if len(wa) < 10:
        return (0, 0, 0)
    metin = gorunur_metin(doc)
    wa_baglam = notr = notr_mesaj = 0
    for m in KATI_TEL_RE.finditer(metin):
        d = _rakam(m.group(0))
        pencere = metin[max(0, m.start() - GORUNUR_PENCERE):m.end() + 60]
        wa_icinde = bool(WA_BAGLAM_RE.search(pencere))
        if wa_icinde:
            wa_baglam += 1
        else:
            notr += 1
            # ÖLÇÜM (kural değil): nötr literal aslında mesajlaşma cümlesinde mi?
            if MESAJ_FIIL_RE.search(pencere):
                notr_mesaj += 1
        if d not in (wa, arama):
            fails.append("%s: görünür metinde TANINMAYAN telefon literali %r (%s) — "
                         "ne WhatsApp (%s) ne arama (%s) hattı, fail-closed KIRMIZI"
                         % (ad, m.group(0), d, wa, arama))
            continue
        if wa_icinde and d != wa:
            fails.append("%s: WhatsApp bağlamında ARAMA hattı basılmış (%s) — müşteri "
                         "WhatsApp sanıp o numaraya yazar, mesaj hiç ulaşmaz: ...%s..."
                         % (ad, d, pencere[-120:].replace("\n", " ")))
    if not sessiz:
        print("  [%s] görünür telefon literali: WhatsApp bağlamı=%d, nötr bağlam=%d "
              "(%d'si mesajlaşma fiilli; nötr olanın hattı YARGILANMAZ)"
              % (ad, wa_baglam, notr, notr_mesaj))
    return (wa_baglam, notr, notr_mesaj)


def belge_denetle(ad, doc, fails, taban=None, sessiz=False):
    """Bir BELGE için numara sözleşmesinin TAMAMI (4 düzlem, tek çağrı).

    Aynı sözleşme ürün sayfasına, ana sayfaya ve yasal/içerik sayfalarına uygulanır ->
    yeni bir sayfa tipi eklendiğinde tek satırla kapsama girer (kör noktanın sınıfı
    'hangi sayfayı saydıysam o' idi)."""
    literal, dinamik = numara_kontrol(ad, doc, fails, taban=taban, sessiz=sessiz)
    ters = ters_yon_kontrol(ad, doc, fails, sessiz=sessiz)
    js_y, js_s = js_sabit_kontrol(ad, doc, fails, sessiz=sessiz)
    g_wa, g_notr, g_notr_mesaj = gorunur_numara_kontrol(ad, doc, fails, sessiz=sessiz)
    return {"wa_literal": literal, "wa_dinamik": dinamik, "ters_alan": ters,
            "js_yargilanan": js_y, "js_yargisiz": js_s,
            "gorunur_wa": g_wa, "gorunur_notr": g_notr,
            "gorunur_notr_mesaj": g_notr_mesaj}


def _topla(hedef, kaynak):
    for k, v in kaynak.items():
        hedef[k] = hedef.get(k, 0) + v
    return hedef


def icerik_sayfalari():
    """(ad, html) — tools/sayfalar.py'nin ÜRETİLEN çıktı düzlemi.

    Kaynak dosyayı grep'lemek YETMEZ: kural üretilen sayfada ihlal edilir (şablon,
    künye tablosu, gömülü betik kaynakta ayrı ayrı durur). Bu yüzden her içerik/yasal
    sayfa build.render_content_page ile GERÇEKTEN üretilip taranır."""
    for slug, title, meta, fn in sayfalar.CONTENT_PAGES:
        yield ("sayfalar.py:" + slug, build.render_content_page(slug, title, meta, fn()))


def statik_sayfalar():
    """(ad, html) — elle yazılmış yasal/kurumsal sayfalar (hakkimizda/iletisim/sss/gizlilik).

    Bunlar build.py'nin ÜRETMEDİĞİ, repoda duran dosyalardır; aynı numara sözleşmesine
    tabidirler (iletisim sayfasında JSON-LD telephone = arama hattı, wa.me CTA'ları =
    WhatsApp hattı)."""
    for slug in sayfalar.STATIK_SAYFALAR:
        yol = os.path.join(KOK, slug, "index.html")
        if not os.path.exists(yol):
            continue
        with open(yol, encoding="utf-8") as f:
            yield (slug + "/index.html", f.read())


def ana_sayfa_metni():
    with open(os.path.join(KOK, "index.html"), encoding="utf-8") as f:
        return f.read()


def sayfa_duzlemi(fails):
    """ANA SAYFA + YASAL/İÇERİK SAYFALARI düzlemi (bu genişletmenin kapattığı boşluk)."""
    print("\nSAYFA DÜZLEMİ — index.html + tools/sayfalar.py (üretilen çıktı) + statik yasal")
    belge_denetle("index.html", ana_sayfa_metni(), fails)
    statik = 0
    for ad, doc in statik_sayfalar():
        belge_denetle(ad, doc, fails)
        statik += 1
    # Kaç statik sayfa TARANDI açıkça yazılır: dosya yoksa sessizce atlanıyor, o zaman
    # o sayfa nöbetsizdir ve bunun görünmesi gerekir (sessiz kapsam kaybı).
    if statik < len(sayfalar.STATIK_SAYFALAR):
        print("  [statik] UYARI: %d/%d statik sayfa dosyası bulundu — bulunamayanlar "
              "TARANMADI (%s)" % (statik, len(sayfalar.STATIK_SAYFALAR),
                                  ", ".join(sayfalar.STATIK_SAYFALAR)))

    # ---- üretilen içerik/yasal sayfa korpusu (168 sayfa): tek tek yargı, toplu rapor
    toplam, sayfa = {}, 0
    for ad, doc in icerik_sayfalari():
        _topla(toplam, belge_denetle(ad, doc, fails, sessiz=True))
        sayfa += 1
    print("  [sayfalar.py korpusu] üretilen sayfa=%d, wa literal link=%d, dinamik=%d, "
          "ters yön alan=%d, JS sabiti=%d, görünür literal=%d (WhatsApp bağlamı) + %d "
          "(nötr; %d'si mesajlaşma fiilli)"
          % (sayfa, toplam.get("wa_literal", 0), toplam.get("wa_dinamik", 0),
             toplam.get("ters_alan", 0), toplam.get("js_yargilanan", 0),
             toplam.get("gorunur_wa", 0), toplam.get("gorunur_notr", 0),
             toplam.get("gorunur_notr_mesaj", 0)))
    if sayfa == 0:
        fails.append("sayfalar.py: hiç içerik sayfası üretilmedi — CONTENT_PAGES boş mu? "
                     "(korpus nöbeti BOŞ kümeye bakıp sahte-yeşil yanamaz)")
    # ⚠️ KORPUS TABANI KAYNAK SAYISINA BAĞLANMAZ (kaldırıldı, gerekçe ölçülmüş):
    # "korpus literal sayısı >= sayfalar.py kaynağındaki literal sayısı" kuralı bugün
    # 12 == 12 ile SIFIR PAYLA çalışıyordu -> kaynağa açıklama satırı olarak örnek bir
    # wa.me yazmak (kaynak 13) ya da bir sayfayı CONTENT_PAGES'ten çıkarmak (korpus 11)
    # gibi numarayla İLGİSİZ meşru düzenlemeler tüm site deploy'unu durduruyordu.
    # Boş-küme sahte-yeşiline karşı koruma artık BELGE BAZINDA ve belgenin kendi
    # içeriğinden türeyerek çalışıyor (numara_kontrol içindeki iki türetilmiş nöbet).
    # Bilinen kör nokta: CONTENT_PAGES'e bağlanmamış bir sayfa gövdesi hiç üretilmediği
    # için hiç taranmaz — kör nokta listesinde yazılı.
    return toplam


# --------------------------------------------------------------------- FİKSTÜRLER
# Nöbetçinin KENDİ kabul testi: her koşumda hem KIRMIZI mutasyonları hem de İLGİSİZ
# RUTİN DÜZENLEME fikstürünü çalıştırır. İkincisi olmadan kapı "hangi elemanı
# koruyorum" eksenine kayar ve numarayla ilgisi olmayan bir CSS/metin düzenlemesi tüm
# site deploy'unu durdurur (bu repoda ÖLÇÜLMÜŞ tuzak).
# 🔴 ÇAPA YOKLUĞU = "ÖLÇEMEDİM", "İHLAL VAR" DEĞİL (bağımsız çürütücü bulgusu, 27 Tem).
# Fikstür çapası bulunamayınca KIRMIZI yakmak yanlış-pozitiftir: `var WA_NO=...;
# var WHATSAPP=WA_NO;` refaktörü, künye etiketinin "Telefon (arama)" olması ya da basılan
# numaranın tipografisinin değişmesi (65 26 / 6526) NUMARAYI BOZMAZ ama çapayı yok eder;
# adım continue-on-error taşımadığı için bunların her biri TÜM EKİBİN yayınını durduruyordu.
# Artık: görünür "ÖLÇÜLEMEDİ" satırı + sayaç, çıkış 0. Sessiz ölmesin diye ÖLÜ-NÖBETÇİ
# kontrolü var: hiçbir kırmızı fikstür koşamadıysa (self-test tamamen ölmüş) O ZAMAN kırmızı.
FIKSTUR_SAYAC = {"kirmizi_kosan": 0, "yesil_kosan": 0, "olculemedi": 0}


def _olculemedi(ad, sebep):
    FIKSTUR_SAYAC["olculemedi"] += 1
    print("     %-46s -> ÖLÇÜLEMEDİ (%s)" % (ad, sebep))


def _yargila(ad, doc, mutant, fails, kirmizi_bekle):
    if mutant == doc:
        _olculemedi(ad, "mutasyon belgeyi değiştirmedi")
        return
    yerel = []
    belge_denetle("fikstür/" + ad, mutant, yerel, sessiz=True)
    if kirmizi_bekle:
        FIKSTUR_SAYAC["kirmizi_kosan"] += 1
        if not yerel:
            fails.append("FİKSTÜR: %s mutasyonu KIRMIZI yakmadı — nöbetçi bu ihlali "
                         "GÖRMÜYOR" % ad)
    else:
        FIKSTUR_SAYAC["yesil_kosan"] += 1
        if yerel:
            fails.append("FİKSTÜR: İLGİSİZ rutin düzenleme (%s) nöbetçiyi KIRMIZI yaktı — "
                         "kapı kapsamı yanlış eksende, alakasız düzenleme deploy'u "
                         "durdurur: %s" % (ad, yerel[:2]))
    print("     %-46s -> %s (%d bulgu)"
          % (ad, "KIRMIZI" if yerel else "yeşil", len(yerel)))


def _mutasyon(ad, doc, eski, yeni, fails, kirmizi_bekle):
    """Metin çapalı mutasyon. Çapa NUMARA SABİTİNDEN türetilir (hardcode yok).
    Çapa yoksa ÖLÇÜLEMEDİ (kırmızı DEĞİL) — gerekçe yukarıdaki blokta."""
    if doc is None:
        _olculemedi(ad, "fikstür belgesi seçilemedi")
        return
    if eski not in doc:
        _olculemedi(ad, "mutasyon çapası belgede yok: %r" % (eski[:48],))
        return
    # TÜM geçişler değiştirilir: tek geçiş değiştirilseydi mutasyon yanlış yere düşüp
    # (ör. künye tablosu yerine düz cümledeki aynı pv değeri) fikstür sahte-yeşil
    # yanabilirdi — ölçüldü, bu yüzden replace(count) YOK.
    _yargila(ad, doc, doc.replace(eski, yeni), fails, kirmizi_bekle)


def _mutasyon_re(ad, doc, kalip, yeni_fn, fails, kirmizi_bekle):
    """TÜRETİLMİŞ çapa: kalıp belgenin YAPISINDAN eşleşir, yeni değer eşleşenden üretilir.

    ⚠️ İki tuzak da ölçüldü: sabit ÇAPA (ör. `--navy:#12294d`) alakasız bir renk
    düzenlemesinde yok olur; sabit YENİ DEĞER ise belge zaten o değerdeyse mutasyonu
    etkisiz bırakır. İkisi de fikstürü sahte kırmızıya çevirir."""
    if doc is None:
        _olculemedi(ad, "fikstür belgesi seçilemedi")
        return
    m = re.search(kalip, doc, re.S)
    if not m:
        _olculemedi(ad, "türetilmiş çapa kalıbı belgede yok: %r" % kalip)
        return
    _yargila(ad, doc, doc[:m.start()] + yeni_fn(m) + doc[m.end():], fails, kirmizi_bekle)


def gorunur_bicim(d):
    """905451386526 -> '+90 545 138 6526' (numara sabitinden türetilmiş YAZIM biçimi).

    ⚠️ Yalnız YENİ DEĞER üretmek için kullanılır, ÇAPA olarak DEĞİL: sayfadaki
    tipografi başka gruplanabilir ("+90 545 138 65 26") ve çapa olarak kullanılsa
    alakasız bir tipografi düzenlemesi fikstürü öldürürdü (ölçüldü)."""
    return "+%s %s %s %s" % (d[:2], d[2:5], d[5:8], d[8:])


def gorunur_literal_bul(doc, hane):
    """Belgede BASILI duran, rakamları `hane` olan telefon literalini OLDUĞU GİBİ döndür.

    Tipografiden bağımsız (KATI_TEL_RE her gruplamayı tanır) -> görünür metin fikstürü
    yazım biçimi değişse de yaşar."""
    if not doc:
        return None
    for m in KATI_TEL_RE.finditer(gorunur_metin(doc)):
        if _rakam(m.group(0)) == hane:
            return m.group(0)
    return None


def ornek_sayfa(kosul):
    """İçerik korpusundan koşulu SAĞLAYAN ilk üretilmiş sayfa (fikstür belgesi).

    Sabit slug seçmek çapadır (o sayfa değişince fikstür sessizce ölür) -> sayfa
    İÇERİĞİNE göre seçilir. Hiçbiri uymuyorsa None -> fikstür ÖLÇÜLEMEDİ sayılır."""
    for _ad, doc in icerik_sayfalari():
        if kosul(doc):
            return doc
    return None


def _korpus_fikstur(fails):
    """A09 sınıfı: bir sayfa CONTENT_PAGES'ten ÇIKARILINCA korpus nöbeti YEŞİL kalmalı.

    Eski sürümde korpus tabanı sayfalar.py kaynağındaki literal sayısına bağlıydı ve
    sıfır payla çalışıyordu -> sayfayı listeden çıkarmak (gövde kaynakta kalır) tüm
    deploy'u durduruyordu. Bu fikstür o regresyonun geri gelmesini engeller."""
    asil = sayfalar.CONTENT_PAGES
    if len(asil) < 2:
        _olculemedi("İLGİSİZ: sayfayı CONTENT_PAGES'ten çıkarmak", "korpus çok küçük")
        return
    yerel = []
    try:
        sayfalar.CONTENT_PAGES = asil[:-1]
        sayfa = 0
        for ad, doc in icerik_sayfalari():
            belge_denetle(ad, doc, yerel, sessiz=True)
            sayfa += 1
        if sayfa == 0:
            yerel.append("korpus boş")
    finally:
        sayfalar.CONTENT_PAGES = asil
    FIKSTUR_SAYAC["yesil_kosan"] += 1
    if yerel:
        fails.append("FİKSTÜR: İLGİSİZ rutin düzenleme (sayfayı CONTENT_PAGES'ten "
                     "çıkarmak) nöbetçiyi KIRMIZI yaktı: %s" % yerel[:2])
    print("     %-46s -> %s (%d bulgu)"
          % ("İLGİSİZ: sayfayı CONTENT_PAGES'ten çıkarmak",
             "KIRMIZI" if yerel else "yeşil", len(yerel)))


def fikstur_kontrol(fails):
    wa, arama = numaralar()
    if len(wa) < 10 or len(arama) < 10:
        fails.append("FİKSTÜR: numara sabitleri türetilemedi — mutasyon fikstürleri "
                     "koşturulamaz (fail-closed)")
        return
    arama_yazi = gorunur_bicim(arama)
    idx = ana_sayfa_metni()
    print("\nFİKSTÜRLER (nöbetçinin kendi kabul testi — her koşumda koşar)")
    icerik = ornek_sayfa(lambda d: ("wa.me/" + wa) in d)
    gorunur_s = ornek_sayfa(lambda d: gorunur_literal_bul(d, wa) is not None)
    yasal = ornek_sayfa(lambda d: PV_TELEFON_HUCRE_RE.search(d) is not None)

    # ---------------- KIRMIZI beklenen: index.html numara ihlalleri
    _mutasyon("index.html wa.me -> arama hattı", idx,
              "wa.me/" + wa, "wa.me/" + arama, fails, True)
    _mutasyon("index.html JSON-LD contactPoint -> WhatsApp", idx,
              '"telephone":"+' + arama + '"', '"telephone":"+' + wa + '"', fails, True)
    _mutasyon("index.html var WHATSAPP -> arama hattı", idx,
              'WHATSAPP = "' + wa + '"', 'WHATSAPP = "' + arama + '"', fails, True)
    _mutasyon("index.html wa.me -> AYRIŞTIRILAMAZ numara", idx,
              "wa.me/" + wa, "wa.me/90 545-138.65", fails, True)
    # Kural bazında ÖLÜ NÖBETÇİ kontrolü — bu üç kuralın fikstürü YOKTU (çürütücü bulgusu):
    #   (1) VARLIK-KODLU (entity) ikinci tarama  (2) harf-duyarsız host  (3) türetilmiş
    #   literal-pozitif nöbeti
    _mutasyon("index.html VARLIK-KODLU (entity) gizlenmiş arama hattı", idx,
              "</body>",
              '<a href="https://wa&#46;me/' + arama + '">gizli</a>\n</body>', fails, True)
    _mutasyon("index.html BÜYÜK HARF WA.ME + arama hattı", idx,
              "</body>",
              '<a href="https://WA.ME/' + arama + '">buyuk</a>\n</body>', fails, True)
    _mutasyon("index.html literal tarayıcı körlenmesi (pozitif nöbet)", idx,
              "https://wa.me/" + wa, "https://xwa.me/" + wa, fails, True)

    # ---------------- KIRMIZI beklenen: sayfalar.py ÜRETİLEN çıktı düzlemi
    _mutasyon("sayfalar.py çıktısı wa.me -> arama hattı", icerik,
              "wa.me/" + wa, "wa.me/" + arama, fails, True)
    _mutasyon("sayfalar.py çıktısı görünür metin -> arama hattı", gorunur_s,
              gorunur_literal_bul(gorunur_s, wa) or "", arama_yazi, fails, True)
    _mutasyon("sayfalar.py künye pv Telefon -> WhatsApp", yasal,
              sayfalar.pv_html(sayfalar.SELLER["tel"]),
              sayfalar.pv_html(gorunur_bicim(wa)), fails, True)
    _mutasyon("sayfalar.py TARGET_PHONE -> arama hattı", icerik,
              'TARGET_PHONE = "' + wa + '"', 'TARGET_PHONE = "' + arama + '"', fails, True)

    # ---------------- YEŞİL kalması ZORUNLU: numarayla İLGİSİZ rutin düzenlemeler
    # Çapa da yeni değer de BELGEDEN türetilir (ikisinin de sabit olması ölçülmüş tuzak).
    _mutasyon_re("İLGİSİZ: index.html'e HTML yorumu eklemek", idx,
                 r"</body>", lambda m: "<!-- rutin duzenleme -->\n" + m.group(0),
                 fails, False)
    _mutasyon_re("İLGİSİZ: index.html ilk renk kodunu değiştirmek", idx,
                 r"#[0-9a-fA-F]{6}\b",
                 lambda m: m.group(0)[:-1] + ("1" if m.group(0)[-1] != "1" else "2"),
                 fails, False)
    _mutasyon_re("İLGİSİZ: index.html meta açıklamasını değiştirmek", idx,
                 r'<meta name="description" content="([^"]*)"',
                 lambda m: '<meta name="description" content="Rutin pazarlama cümlesi. %s"'
                           % m.group(1), fails, False)
    _mutasyon_re("İLGİSİZ: içerik sayfasında paragraf eklemek", icerik,
                 r"<p>", lambda m: "<p>Rutin metin düzenlemesi. ", fails, False)
    _mutasyon_re("İLGİSİZ: yasal sayfada madde metnini değiştirmek", yasal,
                 r"<li>(.*?)</li>",
                 lambda m: "<li>Rutin olarak güncellenmiş madde. %s</li>" % m.group(1),
                 fails, False)
    # --- Bağımsız çürütücünün SAHTE KIRMIZI bulduğu 6 senaryo (A09/A16/A17/A19/A21/A22),
    #     bir daha kaçmasın diye her biri kendi fikstürüyle:
    _mutasyon_re("İLGİSİZ (A16): resmî wa.me/message/<KOD> kısa linki", idx,
                 r"</body>",
                 lambda m: '<a href="https://wa.me/message/ABCDEFGHIJKL2">kisa</a>\n'
                           + m.group(0), fails, False)
    _mutasyon_re("İLGİSİZ (A17): örnek wa.me'li HTML yorumu", idx,
                 r"</body>",
                 lambda m: "<!-- ornek: https://wa.me/%s?text=... -->\n%s"
                           % (wa, m.group(0)), fails, False)
    _mutasyon("İLGİSİZ (A19): var WA_NO refaktörü (numara DOĞRU)", idx,
              'WHATSAPP = "' + wa + '"',
              'WA_NO = "' + wa + '";\n  var WHATSAPP = WA_NO', fails, False)
    _mutasyon_re("İLGİSİZ (A21): künye etiketi 'Telefon (arama)'", yasal,
                 r"<td>\s*Telefon\s*</td>", lambda m: "<td>Telefon (arama)</td>",
                 fails, False)
    _mutasyon("İLGİSİZ (A22): basılan numaranın tipografisi", gorunur_s,
              gorunur_literal_bul(gorunur_s, wa) or "",
              "+%s %s %s %s %s" % (wa[:2], wa[2:5], wa[5:8], wa[8:10], wa[10:]),
              fails, False)
    _korpus_fikstur(fails)                      # A09

    # ---------------- ÖLÜ NÖBETÇİ kontrolü (çapa yokluğu artık kırmızı yakmadığı için)
    print("     -> fikstür özeti: %d kırmızı koştu, %d ilgisiz-yeşil koştu, %d ÖLÇÜLEMEDİ"
          % (FIKSTUR_SAYAC["kirmizi_kosan"], FIKSTUR_SAYAC["yesil_kosan"],
             FIKSTUR_SAYAC["olculemedi"]))
    if FIKSTUR_SAYAC["kirmizi_kosan"] == 0:
        fails.append("FİKSTÜR: HİÇBİR kırmızı mutasyon fikstürü koşamadı (hepsinin çapası "
                     "kayıp) — nöbetçinin duyarlılığı ARTIK ÖLÇÜLMÜYOR, ölü nöbetçi riski")
    if FIKSTUR_SAYAC["yesil_kosan"] == 0:
        fails.append("FİKSTÜR: HİÇBİR 'ilgisiz rutin düzenleme' fikstürü koşamadı — "
                     "kapının yanlış-pozitif ekseni ARTIK ÖLÇÜLMÜYOR")


def kor_noktalar(toplam):
    """Nöbetçinin ÖLÇMEDİĞİ şeyler — her koşumda SAYIYLA ilan edilir (repo standardı)."""
    notr = toplam.get("gorunur_notr", 0)
    notr_mesaj = toplam.get("gorunur_notr_mesaj", 0)
    print("""
KÖR NOKTALAR (bu nöbetçinin ÖLÇMEDİĞİ şeyler — sessiz kalmasın diye SAYIYLA yazılır):
  1. Numarası kaynakta LİTERAL geçmeyen, JS'te değişkenle kurulan link parçası; yalnız
     sabitin KENDİSİ (var WHATSAPP / TARGET_PHONE) doğrulanır, o sabitten kurulan URL
     çalışma zamanında oluşur -> tarayıcıda koşulmaz.
  2. Adı ne WhatsApp ne arama kümesine uyan telefon-benzeri JS sabiti YARGILANMAZ
     (rapordaki 'adı sınıflanamayan' sayısı bunu gösterir).
  3. 🔴 CANLI KAÇAK (beyan): görünür metinde NÖTR bağlamdaki telefon literalinin HANGİ
     HATTA ait olması gerektiği YARGILANMAZ -> bugün korpusta %d nötr literal var ve
     bunların %d'si "... numarasına GÖNDERİN/YAZIN/İLETİN" gibi MESAJLAŞMA cümlesinde.
     Yani biri arama hattına çevrilse nöbetçi YEŞİL kalır, müşteri WhatsApp sanıp
     arama hattına yazar. Kural BİLEREK zorlanmadı: "arama bağlamı" kuralı 168 SEO
     sayfasında (telefon tutucu/klipsi gibi ÜRÜN cümleleri yüzünden) yanlış-kırmızı
     üretirdi. Ölçüm hepsinin TEK bir "Sipariş" şablonundan geldiğini gösteriyor ->
     kural yazılabilir; AYRI turda kapatılacak.
  4. Görünür metin taraması KATI +90 biçimini arar; ölçüm gerekçesi: gevşek kalıp
     etiket temizliğinden sonra cümleler arası rakamları birleştirip sahte aday
     üretiyordu. Yerel/uluslararası başka biçimde (0545..., 0090...) basılan numara
     GÖRÜLMEZ.
  5. wa.me/message/<KOD> kısa linkleri numara TAŞIMAZ -> numara kuralı uygulanamaz;
     kırmızı yakılmaz, koşum başına bilgi satırı basılır. O kodun hangi hatta bağlı
     olduğu YALNIZ WhatsApp Business panelinden görülür, burada ÖLÇÜLEMEZ.
     chat.whatsapp.com grup davet linkleri de (numara taşımaz) kapsam dışıdır.
  6. CONTENT_PAGES'e BAĞLANMAMIŞ sayfa gövdesi hiç üretilmediği için hiç TARANMAZ
     (kaynak dosya grep'lenmez: kaynağa bağlı sayım meşru düzenlemeyi kırmızı yakıyordu).
  7. Ege (WhatsApp botu) tarafındaki numara/metin bu testin düzlemi DEĞİLDİR; canlı
     yayındaki HTML de doğrulanmaz (kaynak + üretilen çıktı düzlemi doğrulanır).
  8. Fikstür çapası kaybolduğunda o fikstür ÖLÇÜLEMEDİ sayılır (kırmızı değil);
     duyarlılık ölçümü o tur için düşer — özet satırındaki sayı bunu gösterir."""
          % (notr, notr_mesaj))


def main():
    html_doc = build.render_product(URUN, [URUN])
    url = build.product_url(URUN["id"])
    baslik = URUN["baslik"]
    fails = []

    # ------------------------------------------------ ORGANİK buton (help-cta-btn)
    m = re.search(r'class="help-cta-btn"[^>]*\shref="(https://wa\.me/[^"]+)"', html_doc)
    if not m:
        print("FAIL: help-cta-btn wa.me href bulunamadı (buton kayıp mı?)")
        return 1
    organik_href = m.group(1)
    organik_text = _wa_text(organik_href)
    print("ORGANİK (help-cta-btn) decoded text=:")
    print("   ", repr(organik_text))

    if organik_text is None:
        fails.append("organik href'te ?text= yok")
    else:
        # (a) BAĞLAM: ürün başlığı + canonical URL
        if baslik not in organik_text:
            fails.append("organik prefill ürün BAŞLIĞINI içermiyor: %r" % baslik)
        if url not in organik_text:
            fails.append("organik prefill canonical URL'i içermiyor: %r" % url)
        # (b) NİYET: "bu ürünü istiyorum" DEMEMELİ (butonun anlamı bunun TERSİ)
        dusuk = organik_text.lower()
        for kotu in YANLIS_NIYET:
            if kotu.lower() in dusuk:
                fails.append(
                    "organik prefill YANLIŞ NİYET taşıyor (%r) — buton 'aradığını "
                    "bulamayan' müşteri için, sayfadaki ürünü TALEP ETMEZ" % kotu)
        # (c) NİYET: "bulamadım/üretebilir misiniz" niyetini TAŞIMALI
        if not (u"bulamad" in dusuk and (u"üretebilir" in dusuk or u"üretelim" in dusuk)):
            fails.append("organik prefill 'aradığımı bulamadım, üretebilir misiniz?' "
                         "niyetini taşımıyor")
    _kodlama_kontrol("organik", organik_href, organik_text, fails)

    # ------------------------------------------------ MALZEME NOTU (malzeme-not)
    mm = re.search(r'class="malzeme-not"(?:.(?!</p>))*?href="(https://wa\.me/[^"]+)"',
                   html_doc, re.S)
    if not mm:
        fails.append("malzeme-not wa.me href bulunamadı")
    else:
        malz_href = mm.group(1)
        malz_text = _wa_text(malz_href)
        print("MALZEME NOTU (malzeme-not) decoded text=:")
        print("   ", repr(malz_text))
        if malz_text is None:
            fails.append("malzeme-not href'te ?text= yok")
        else:
            # BAĞLAM eklenmiş olmalı
            if baslik not in malz_text:
                fails.append("malzeme-not prefill ürün BAŞLIĞINI içermiyor")
            if url not in malz_text:
                fails.append("malzeme-not prefill canonical URL'i içermiyor")
            # KENDİ niyeti (malzeme/özel üretim) KORUNMALI
            md = malz_text.lower()
            if not (u"malzeme" in md and u"özel üretim" in md):
                fails.append("malzeme-not KENDİ niyetini (mühendislik malzemesi / "
                             "özel üretim sorusu) KAYBETTİ")
            # help-cta'nın niyeti buraya SIZMAMALI
            if u"bulamad" in md:
                fails.append("malzeme-not'a help-cta niyeti ('bulamadım') SIZDI")
        _kodlama_kontrol("malzeme-not", malz_href, malz_text, fails)

    # ------------------------------------------------ REGRESYON: REF butonu (orderAlt)
    mo = re.search(r'id="orderAlt"[^>]*\shref="(https://wa\.me/[^"]+)"', html_doc)
    if not mo:
        fails.append("orderAlt (REF butonu) wa.me href bulunamadı — regresyon")
    else:
        ref_text = _wa_text(mo.group(1))
        print("REF (orderAlt) decoded text=:")
        print("   ", repr(ref_text))
        if ref_text is None or baslik not in ref_text or url not in ref_text:
            fails.append("orderAlt (REF) prefill ad+URL bağlamını KAYBETTİ — regresyon")
        # REF butonu ÜRÜN TALEBİ butonudur: onun "ilgileniyorum" niyeti KALMALI.
        if ref_text and u"ilgileniyorum" not in ref_text.lower():
            fails.append("orderAlt (REF) 'ilgileniyorum' niyetini kaybetti — regresyon")

    # -------------------------------------- NUMARA SINIFI (küme nöbeti, 3 ürün tipi)
    wa_num, arama_num = numaralar()
    print("\nNUMARA NÖBETİ — WhatsApp=%s (build.WHATSAPP), arama=%s (build.SELLER['tel'])"
          % (wa_num or "?", arama_num or "?"))
    for ad, urun, doc in (
            ("normal", URUN, html_doc),
            ("lisanslı", URUN_LISANSLI, None),
            ("parametrik", URUN_PARAMETRIK, None)):
        if doc is None:
            doc = build.render_product(urun, [urun])
        numara_kontrol(ad, doc, fails, taban=WA_URL_TABAN)
        ters_yon_kontrol(ad, doc, fails)
        js_sabit_kontrol(ad, doc, fails)
        gorunur_numara_kontrol(ad, doc, fails)

    # ---------------- ANA SAYFA + YASAL/İÇERİK SAYFALARI (kapsam genişletmesi)
    toplam = sayfa_duzlemi(fails)

    # ---------------- nöbetçinin KENDİ kabul testi (kırmızı + İLGİSİZ-yeşil fikstürler)
    fikstur_kontrol(fails)

    kor_noktalar(toplam)

    if fails:
        print("\nFAIL (%d):" % len(fails))
        for f in fails:
            print("  -", f)
        return 1
    print("\nPASS: organik + malzeme-not prefill'leri sayfa bağlamı taşıyor, niyetleri "
          "DOĞRU ve AYRI; REF butonu sağlam; ÜRÜN SAYFASI + ANA SAYFA + YASAL/İÇERİK "
          "sayfalarının hepsinde TÜM WhatsApp linkleri (wa.me · api./web.whatsapp.com · "
          "whatsapp://), JS telefon sabitleri ve görünür telefon literalleri WhatsApp "
          "hattını taşıyor; arama hattı (tel:/JSON-LD/pv künye) WhatsApp numarasından "
          "temiz; fikstürler kırmızıyı yakıyor, İLGİSİZ rutin düzenleme YEŞİL kalıyor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
