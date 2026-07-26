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
# Sayfaya gömülen ref-atıf betiğinin wa.me EŞLEŞTİRME sabiti (attribution-ref.js).
# build.WHATSAPP'tan sapması sessiz hatadır: linkler doğru numarayı taşır ama betik
# onları WhatsApp linki olarak TANIMAZ -> reklam atfı (ref) sessizce düşer.
TARGET_PHONE_RE = re.compile(r'TARGET_PHONE\s*=\s*"([^"]*)"')
# Ters yön: arama hattına ait alanlar.
TEL_HREF_RE = re.compile(r'href="\s*(tel:[^"]*)"')
TEL_ALAN_ANAHTARLARI = ("telephone", "contactPoint", "faxNumber")

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


def numara_kontrol(ad, doc, fails):
    """KÜME nöbeti: sayfadaki TÜM WhatsApp URL'lerinin numarasını doğrula.

    Tek tek href yakalamak yerine belgedeki her wa.me/api.whatsapp.com URL'i taranır
    -> sonradan eklenen butonlar da otomatik kapsanır (kör noktanın kendisi buydu)."""
    wa, arama = numaralar()
    # Sabitlerin kendisi sağlam mı (fail-closed: türetme çalışmıyorsa nöbet anlamsız).
    if len(wa) < 10:
        fails.append("%s: build.WHATSAPP geçersiz/boş (%r) — numara nöbeti kurulamaz" % (ad, wa))
        return
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
    gorulen = set()       # aynı ihlali iki taramada iki kez bildirme

    def _tara(metin, tabana_say):
        for m in WA_URL_RE.finditer(metin):
            url = _html.unescape(m.group(0))
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
    print("  [%s] WhatsApp link sayısı=%d, numaralar=%s"
          % (ad, len(bulunan), sorted(set(n for _, n in bulunan)) or "-"))
    if dinamik:
        # Bu biçimin numarası kaynakta LİTERAL geçmez -> burada ÖLÇÜLEMEZ (açıkça beyan).
        # Bugünkü tek örneği attribution-ref.js'in eşleştirme dizesi; onun numarası
        # aşağıdaki TARGET_PHONE assert'iyle kapatılıyor.
        print("  [%s] NOT: numara LİTERALİ taşımayan %d WhatsApp link parçası — numarası "
              "ÖLÇÜLEMEZ (değişkenle kuruluyor): %s" % (ad, len(dinamik), dinamik[:2]))
    if len(bulunan) < WA_URL_TABAN:
        fails.append("%s: geçerli numara taşıyan WhatsApp linki %d < taban %d — sipariş/"
                     "iletişim linkleri kaybolmuş ya da regex artık tutmuyor (küme "
                     "kontrolü BOŞ kümeye bakıp sahte-yeşil yanamaz)"
                     % (ad, len(bulunan), WA_URL_TABAN))

    # Gömülü ref-atıf betiğinin eşleştirme sabiti de AYNI numara olmalı (sessiz drift).
    hedefler = TARGET_PHONE_RE.findall(doc)
    if not hedefler:
        print("  [%s] NOT: TARGET_PHONE sabiti sayfada yok — ref-atıf eşleşmesi "
              "ÖLÇÜLEMEDİ" % ad)
    for t in hedefler:
        if _rakam(t) != wa:
            fails.append("%s: gömülü ref-atıf betiğinin TARGET_PHONE'u (%s) "
                         "build.WHATSAPP (%s) ile UYUŞMUYOR — linkler doğru numarayı "
                         "taşısa bile betik onları tanımaz, ref atfı sessizce düşer"
                         % (ad, t, wa))


def ters_yon_kontrol(ad, doc, fails):
    """TERS YÖN: WhatsApp numarası tel:/JSON-LD contactPoint alanlarında GEÇMEZ.

    Bugün ürün sayfası bu alanlardan HİÇBİRİNİ basmıyor (JSON-LD yalnız Product +
    BreadcrumbList; künye/tel: bloğu yasal sayfalarda — tools/sayfalar.py). Bu yüzden
    kontrol BUGÜN BOŞ KÜMEYE bakar (ölçülemez) ve bunu açıkça yazar; uydurma bir
    pozitif assert eklenmez. İleride sayfaya tel:/contactPoint girerse nöbet ısırır."""
    wa, _ = numaralar()
    if len(wa) < 10:
        return
    alanlar = []          # (nerede, ham değer)
    for m in TEL_HREF_RE.finditer(doc):
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
    if not alanlar:
        print("  [%s] TERS YÖN ÖLÇÜLEMEDİ: sayfada hiç tel: href / JSON-LD %s alanı yok "
              "(bu alanlar yasal sayfalarda üretiliyor, ürün sayfasında değil)"
              % (ad, "|".join(TEL_ALAN_ANAHTARLARI)))
        return
    print("  [%s] ters yön alan sayısı=%d" % (ad, len(alanlar)))
    for nerede, deger in alanlar:
        if wa in _rakam(deger):
            fails.append("%s: %s alanında WHATSAPP numarası (%s) var — orada YALNIZ "
                         "arama hattı olur: %r" % (ad, nerede, wa, deger[:120]))


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
        numara_kontrol(ad, doc, fails)
        ters_yon_kontrol(ad, doc, fails)

    if fails:
        print("\nFAIL (%d):" % len(fails))
        for f in fails:
            print("  -", f)
        return 1
    print("\nPASS: organik + malzeme-not prefill'leri sayfa bağlamı taşıyor, niyetleri "
          "DOĞRU ve AYRI; REF butonu sağlam; 3 ürün tipinde de TÜM WhatsApp linkleri "
          "(wa.me · api./web.whatsapp.com · whatsapp://) WhatsApp hattını taşıyor, "
          "hepsi ayrıştırılabilir, arama hattı hiçbirinde yok.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
