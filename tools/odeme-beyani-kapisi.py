#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÖDEME BEYANI KAPISI — statik sayfalardaki sipariş/ödeme anlatımı canlı akışla uyumlu mu?

Çalıştır: python3 tools/odeme-beyani-kapisi.py
"""

import html
import json
import os
import re
import sys
from html.parser import HTMLParser


TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
STATIK = ["sss", "gizlilik", "hakkimizda", "iletisim"]
STATIK_DOSYALAR = [os.path.join(ROOT, slug, "index.html") for slug in STATIK]
KOK_INDEX = os.path.join(ROOT, "index.html")
SAYFALAR = os.path.join(TOOLS, "sayfalar.py")
SECENEKLER = os.path.join(ROOT, "secenekler.js")

sonuclar = []


def oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def rel(yol):
    return os.path.relpath(yol, ROOT)


def temiz_metin(metin):
    metin = html.unescape(re.sub(r"<[^>]+>", " ", metin))
    return re.sub(r"\s+", " ", metin).strip()


def kontrol(no, ad, kosul, detay="", kapsam=""):
    sonuclar.append((no, ad, bool(kosul), detay, kapsam))


class JsonLdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_jsonld = False
        self.bloklar = []
        self.parcalar = []

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if tag.lower() == "script" and attr.get("type", "").lower() == "application/ld+json":
            self.in_jsonld = True
            self.parcalar = []

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self.in_jsonld:
            self.bloklar.append("".join(self.parcalar).strip())
            self.in_jsonld = False

    def handle_data(self, data):
        if self.in_jsonld:
            self.parcalar.append(data)


class DetailsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.details = []
        self.in_details = False
        self.in_summary = False
        self.depth = 0
        self.current = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "details":
            self.in_details = True
            self.depth = 1
            self.current = {"summary": [], "answer": [], "summary_done": False}
            return
        if self.in_details:
            self.depth += 1
            if tag == "summary":
                self.in_summary = True

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.in_details and tag == "summary":
            self.in_summary = False
            self.current["summary_done"] = True
        if self.in_details:
            self.depth -= 1
            if tag == "details" and self.depth == 0:
                self.details.append((
                    temiz_metin(" ".join(self.current["summary"])),
                    temiz_metin(" ".join(self.current["answer"])),
                ))
                self.in_details = False
                self.current = None

    def handle_data(self, data):
        if not self.in_details:
            return
        if self.in_summary:
            self.current["summary"].append(data)
        elif self.current["summary_done"]:
            self.current["answer"].append(data)


def jsonld_bloklari(html_metin):
    parser = JsonLdParser()
    parser.feed(html_metin)
    return parser.bloklar


def details_cevaplari(html_metin):
    parser = DetailsParser()
    parser.feed(html_metin)
    return dict(parser.details)


def faq_jsonld(veriler):
    for veri in veriler:
        if veri.get("@type") == "FAQPage":
            return veri
    return None


tum_statik = {yol: oku(yol) for yol in STATIK_DOSYALAR}
sss_html = tum_statik[os.path.join(ROOT, "sss", "index.html")]
kok_html = oku(KOK_INDEX)
sayfalar_py = oku(SAYFALAR)
secenekler_js = oku(SECENEKLER)

# --- TARANAN GÖVDE KÜMESİ ---------------------------------------------------
# Kontrol 1/5/6/8 yalnız 4 statik sayfayı tarıyordu; aynı bayat ifade
# CONTENT_PAGES landing gövdelerine girdiğinde kapı SESSİZCE yeşil yanıyordu.
# Kapsam: 4 statik sayfa (diskteki HTML) + CONTENT_PAGES landing gövdeleri
# (build.py KOŞTURULMADAN, kaynak sayfalar.py import edilip fonksiyon çağrılarak).
# Gövdeler HAM HTML tutulur: kontrol 5 (<input>/<iframe>) ve kontrol 8 (wa.me/tel:)
# işaretlemenin kendisine bakar; metin kontrolleri temiz_metin ile düzleştirir.
def _landing_govdeleri():
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    import sayfalar as _mod
    govdeler = {}
    for _slug, _baslik, _meta, _fn in _mod.CONTENT_PAGES:
        govdeler["landing:%s" % _slug] = _fn()
    if not govdeler:
        raise RuntimeError("CONTENT_PAGES boş — landing gövdesi üretilmedi")
    return govdeler


TUM_GOVDELER = {}
GOVDE_HATASI = None
for _yol, _metin in tum_statik.items():
    TUM_GOVDELER[rel(_yol)] = _metin
try:
    TUM_GOVDELER.update(_landing_govdeleri())
except Exception as _e:
    GOVDE_HATASI = "landing gövdeleri üretilemedi: %s" % _e
if GOVDE_HATASI is None and not TUM_GOVDELER:
    GOVDE_HATASI = "taranacak gövde yok (boş küme)"


def kapsamli_kontrol(no, ad, tarayici):
    """tarayici(etiket, ham_html) -> ihlal etiketleri listesi.

    FAIL-CLOSED: gövde kümesi üretilemediyse ya da BOŞSA kontrol KIRMIZI döner
    (sessiz-yeşil yok — boş küme üzerinde 'ihlal bulunamadı' kanıt değildir).
    """
    if GOVDE_HATASI is not None:
        kontrol(no, ad, False, GOVDE_HATASI, "kapsam BELİRSİZ (fail-closed)")
        return
    if not TUM_GOVDELER:
        kontrol(no, ad, False, "hiç sayfa taranmadı (boş küme)", "0 sayfa tarandı")
        return
    ihlaller = []
    for etiket, ham in TUM_GOVDELER.items():
        ihlaller.extend(tarayici(etiket, ham))
    kontrol(no, ad, not ihlaller, ", ".join(ihlaller),
            "%d sayfa tarandı, ihlal %d" % (len(TUM_GOVDELER), len(ihlaller)))


# 1) Bayat ödeme beyanları yok (statik + landing).
yasaklar = [
    r"online\s+ödeme\s+yoktur",
    r"sitede\s+kart\s+ile\s+ödeme\s+yapılamaz",
    r"ödeme\s+whatsapp\s+üzerinden",
    r"whatsapp\s+üzerinden\s+ödeme",
]


def _bayat_odeme_tara(etiket, ham):
    duz = temiz_metin(ham).lower()
    return ["%s:%s" % (etiket, desen) for desen in yasaklar
            if re.search(desen, duz, re.I)]


kapsamli_kontrol(1, "Statik + landing gövdelerinde bayat ödeme/WhatsApp ödeme beyanı yok",
                 _bayat_odeme_tara)

# 2) SSS JSON-LD blokları geçerli JSON.
json_bloklar = jsonld_bloklari(sss_html)
json_veriler = []
json_hatalari = []
for i, blok in enumerate(json_bloklar, 1):
    try:
        json_veriler.append(json.loads(blok))
    except json.JSONDecodeError as e:
        json_hatalari.append("blok %d: %s" % (i, e))
kontrol(2, "SSS JSON-LD blokları json.loads ile ayrışıyor", bool(json_bloklar) and not json_hatalari, ", ".join(json_hatalari))

# 3) FAQPage acceptedAnswer ile görünen details cevapları sipariş/ödeme için örtüşüyor.
details = details_cevaplari(sss_html)
faq = faq_jsonld(json_veriler) if not json_hatalari else None
faq_map = {}
if faq:
    for item in faq.get("mainEntity", []):
        faq_map[item.get("name", "")] = item.get("acceptedAnswer", {}).get("text", "")

ortusme_hatalari = []
beklenen = {
    "Nasıl sipariş verebilirim?": ["Sepete Ekle", "Kartla Güvenli Öde", "WhatsApp ile Sipariş Ver", "malzeme", "renk"],
    "Ödemeyi nasıl yapıyorum? Sitede kartla ödeme var mı?": ["kartla güvenli online ödeme", "iyzico", "WhatsApp"],
}
for soru, anahtarlar in beklenen.items():
    json_cevap = faq_map.get(soru, "")
    gorunen = details.get(soru, "")
    for anahtar in anahtarlar:
        if anahtar.lower() not in json_cevap.lower() or anahtar.lower() not in gorunen.lower():
            ortusme_hatalari.append("%s -> %s" % (soru, anahtar))
kontrol(3, "SSS JSON-LD ve görünen sipariş/ödeme cevapları aynı kanal ve butonları anlatıyor", not ortusme_hatalari, ", ".join(ortusme_hatalari))

# 4) SSS sipariş cevabındaki buton etiketleri kök index.html davranışında var.
siparis_cevap = faq_map.get("Nasıl sipariş verebilirim?", "")
buton_hatalari = []
for etiket in ["Kartla Güvenli Öde", "WhatsApp ile Sipariş Ver"]:
    if etiket not in siparis_cevap:
        buton_hatalari.append("SSS cevabında yok: %s" % etiket)
    if etiket not in kok_html:
        buton_hatalari.append("index.html içinde yok: %s" % etiket)
kontrol(4, "SSS sipariş cevabındaki buton etiketleri kök index.html içinde var", not buton_hatalari, ", ".join(buton_hatalari))

# 5) Statik + landing gövdelerinde kart formu veya ödeme iframe'i yok.
kart_input = re.compile(r"<input\b[^>]*(card|kart|cc|credit|pan|cvc|cvv|expiry|expire)", re.I)
odeme_iframe = re.compile(r"<iframe\b[^>]*(iyzico|payment|ödeme|odeme|checkout|pay)", re.I)
kart_ifade = re.compile(r"kart\s+numaras[ıi]|cvv|cvc|son\s+kullanma\s+tarihi", re.I)


def _kart_formu_tara(etiket, ham):
    ihlal = []
    if kart_input.search(ham):
        ihlal.append("%s:<input kart alanı" % etiket)
    if odeme_iframe.search(ham):
        ihlal.append("%s:<iframe ödeme" % etiket)
    if kart_ifade.search(temiz_metin(ham)):
        ihlal.append("%s:kart verisi ifadesi" % etiket)
    return ihlal


kapsamli_kontrol(5, "Statik + landing gövdelerinde kart alanı/ödeme iframe'i/kart verisi ifadesi yok",
                 _kart_formu_tara)

# 6) Teslim süresi ifadesi tek rakam: 3-5 iş günü var, rakip aralık yok (statik + landing).
rakip_desen = re.compile(r"\b(5-7|3-6|2-4)\s+iş\s+günü\b", re.I)
dogru_desen = re.compile(r"3-5\s+iş\s+günü", re.I)
if GOVDE_HATASI is not None:
    kontrol(6, "Teslim süresi 3-5 iş günü ve rakip süre yok (statik + landing)",
            False, GOVDE_HATASI, "kapsam BELİRSİZ (fail-closed)")
elif not TUM_GOVDELER:
    kontrol(6, "Teslim süresi 3-5 iş günü ve rakip süre yok (statik + landing)",
            False, "hiç sayfa taranmadı (boş küme)", "0 sayfa tarandı")
else:
    rakip_ihlaller = []
    dogru_sayi = 0
    for etiket, ham in TUM_GOVDELER.items():
        duz = temiz_metin(ham)
        for eslesme in rakip_desen.findall(duz):
            rakip_ihlaller.append("%s:%s iş günü" % (etiket, eslesme))
        dogru_sayi += len(dogru_desen.findall(duz))
    kontrol(6, "Teslim süresi 3-5 iş günü ve rakip süre yok (statik + landing)",
            dogru_sayi >= 1 and not rakip_ihlaller,
            "3-5 sayısı=%d, rakip=%s" % (dogru_sayi, ", ".join(rakip_ihlaller) or "-"),
            "%d sayfa tarandı, ihlal %d (3-5 ifadesi %d yerde)" % (
                len(TUM_GOVDELER), len(rakip_ihlaller), dogru_sayi))

# 7) Ölü ikiz fonksiyonlar yeniden doğmamış.
olu_fonksiyonlar = re.findall(r"^def\s+(_(?:sss|gizlilik|hakkimizda|iletisim))\s*\(", sayfalar_py, re.M)
kontrol(7, "tools/sayfalar.py içinde ölü statik gövde fonksiyonları yok", not olu_fonksiyonlar, ", ".join(olu_fonksiyonlar))

# 8) Telefon ayrımı korunuyor (statik + landing).
def _telefon_tara(etiket, ham):
    ihlal = []
    if re.search(r"https?://wa\.me/[^\"'\s>]*4005", ham):
        ihlal.append("%s:wa.me 4005" % etiket)
    if re.search(r"tel:[^\"'\s>]*6526", ham):
        ihlal.append("%s:tel 6526" % etiket)
    return ihlal


kapsamli_kontrol(8, "wa.me içinde 4005 yok, tel: içinde 6526 yok (statik + landing)",
                 _telefon_tara)

# 9) Parametrik ödeme AÇIKKEN "parametrik/ölçüye özel ... WhatsApp kanalından ilerler" iddiası YOK.
#    ÇAPRAZ DOĞRULAMA: beklenti secenekler.js:PARAMETRIK_ODEME_ACIK bayrağından türetilir.
#    Bayrak true  -> parametrik kalemler de sepet/kartla ilerler; "WhatsApp'tan ilerler" iddiası BAYAT -> FAIL.
#    Bayrak false -> parametrik gerçekten WhatsApp'tan ilerler; aynı iddia MEŞRU -> geçer.
#    Kapsam: 4 statik sayfa + CONTENT_PAGES'ten türetilen landing gövdeleri (build.py KOŞTURULMADAN,
#    kaynak sayfalar.py'den import edilip fonksiyonlar çağrılarak).
bayrak_m = re.search(r"var\s+PARAMETRIK_ODEME_ACIK\s*=\s*(true|false)\b", secenekler_js)
parametrik_bayat_desen = re.compile(
    r"(parametrik|ölçüye özel)[^.]{0,120}whatsapp\s+kanal[^.]{0,40}ilerl", re.I)

parametrik_govdeler = {}
for yol, metin in tum_statik.items():
    parametrik_govdeler[rel(yol)] = temiz_metin(metin)

landing_import_hatasi = None
try:
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    import sayfalar as _sayfalar_mod
    for _slug, _baslik, _meta, _fn in _sayfalar_mod.CONTENT_PAGES:
        try:
            parametrik_govdeler["landing:%s" % _slug] = temiz_metin(_fn())
        except Exception as e:
            landing_import_hatasi = "landing gövdesi üretilemedi (%s): %s" % (_slug, e)
except Exception as e:
    landing_import_hatasi = "sayfalar.py import edilemedi: %s" % e

parametrik_ihlaller = []
for etiket, duz in parametrik_govdeler.items():
    if parametrik_bayat_desen.search(duz):
        parametrik_ihlaller.append(etiket)

if bayrak_m is None:
    # Bayrak okunamadı -> fail-closed (kodla çapraz doğrulama yapılamıyor).
    kontrol(9, "Parametrik→WhatsApp iddiası bayrakla çapraz doğrulandı",
            False, "secenekler.js içinde PARAMETRIK_ODEME_ACIK bulunamadı")
elif landing_import_hatasi is not None:
    # Landing gövdeleri taranamadı -> fail-closed (kapsam eksik kalır).
    kontrol(9, "Parametrik→WhatsApp iddiası bayrakla çapraz doğrulandı (statik + landing)",
            False, landing_import_hatasi)
elif bayrak_m.group(1) == "true":
    kontrol(9, "PARAMETRIK_ODEME_ACIK=true iken parametrik→WhatsApp bayat iddiası yok (statik + landing)",
            not parametrik_ihlaller, ", ".join(parametrik_ihlaller),
            "%d sayfa tarandı, ihlal %d" % (len(parametrik_govdeler), len(parametrik_ihlaller)))
else:
    # Bayrak false: parametrik gerçekten WhatsApp'tan ilerliyor -> iddia meşru, kapı geçer.
    kontrol(9, "PARAMETRIK_ODEME_ACIK=false iken parametrik→WhatsApp iddiası meşru (çapraz doğrulama)",
            True, "bayrak kapalı; %d gövdede iddia meşru sayıldı" % len(parametrik_ihlaller))

# 10) Bağlayıcı yasal sayfa gövdelerinde (teslimat-iade + mesafeli-satis) teslim süresi
#     KARGO-HARİÇ çerçeveyle yazılmış mı? (Okan kararı, sss ile tutarlı: ürün 3-5 iş günü
#     içinde KARGOYA VERİLİR; kargo transit süresi ayrı.) Kaynak sayfalar.py üretim
#     fonksiyonları (_teslimat_iade / _mesafeli_satis) çağrılıp gövde metni taranır.
#     - Kargo-DAHİL çerçeve kalıbı bulunursa -> FAIL (bayat taahhüt).
#     - "kargoya verilir" çerçevesi iki sayfada da YOKSA -> FAIL (pozitif doğrulama).
kargo_dahil_desen = re.compile(
    r"kargo\s+süresini\s+kapsar|kargo\s+dahil|üretim\s*\+\s*kargo|"
    r"teslim\s+süresi\s+üretim", re.I)
kargoya_verilir_desen = re.compile(r"kargoya\s+veril", re.I)

baglayici_hatasi = None
baglayici_govdeler = {}
try:
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    import sayfalar as _sayfalar_mod2
    baglayici_govdeler["teslimat-iade"] = temiz_metin(_sayfalar_mod2._teslimat_iade())
    baglayici_govdeler["mesafeli-satis"] = temiz_metin(_sayfalar_mod2._mesafeli_satis())
except Exception as e:
    baglayici_hatasi = "sayfalar.py bağlayıcı gövdeleri üretilemedi: %s" % e

if baglayici_hatasi is not None:
    kontrol(10, "Bağlayıcı sayfa gövdeleri kargo-HARİÇ teslim çerçevesi taşıyor",
            False, baglayici_hatasi)
else:
    dahil_ihlaller = [slug for slug, duz in baglayici_govdeler.items()
                      if kargo_dahil_desen.search(duz)]
    eksik_pozitif = [slug for slug, duz in baglayici_govdeler.items()
                     if not kargoya_verilir_desen.search(duz)]
    kontrol(10, "Bağlayıcı sayfalarda kargo-DAHİL çerçeve yok ve 'kargoya verilir' çerçevesi var",
            not dahil_ihlaller and not eksik_pozitif,
            "kargo-DAHİL: %s | kargoya-verilir eksik: %s" % (
                ",".join(dahil_ihlaller) or "-", ",".join(eksik_pozitif) or "-"),
            "%d sayfa tarandı, ihlal %d" % (
                len(baglayici_govdeler), len(dahil_ihlaller) + len(eksik_pozitif)))

print()
gecen = 0
for no, ad, ok, detay, kapsam in sonuclar:
    print("%s  %d %s%s%s" % (
        "PASS" if ok else "FAIL", no, ad,
        ("  [" + kapsam + "]") if kapsam else "",
        ("  -> " + detay) if (detay and not ok) else ""))
    gecen += 1 if ok else 0
print("-" * 48)
print("Toplam: %d  |  PASS: %d  |  FAIL: %d" % (len(sonuclar), gecen, len(sonuclar) - gecen))
sys.exit(0 if gecen == len(sonuclar) else 1)
