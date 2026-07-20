#!/usr/bin/env python3
"""r2_anahtar.py — R2 gorsel anahtari turetmenin TEK DOGRULUK KAYNAGI.

Neden: anahtar turetme 4 ayri dosyada satir-ici kopyalanmisti (urun-ekle.py,
printables-ekle.py, makerworld-ekle.py, gorsel-cakisma-onar.py). Kopyalar birbirinden
kaydiginda iki urunun gorseli AYNI R2 anahtarina yazilir ve biri digerini EZER
(yayindaki gorsel kirilir). Artik tek yer burasi.

TEMEL KURAL: anahtar KAYNAK-ID'den turer (th<tid> / pr<pid> / mw<did> / cgt-<itemid>),
urun BASLIGINDAN degil. Iki farkli urun ayni Turkce basligi uretse bile anahtarlari
cakismaz.

⚠️ TARIHSEL TUZAK — `cgt` onekinde FAZLADAN TIRE var ("cgt-"), th/pr/mw'de yok.
Yayindaki CGTrader anahtarlari "cgt-<itemid>-<n>.jpg" bicimindedir. Bu bir tutarsizlik
ama DUZELTILMEZ: tireyi kaldirmak gecmis anahtarlarla uyumsuzluk yaratir ve canli
gorsel URL'lerini kirar (CGTrader zaten emekli platform). YENI platform eklerken bu
hatayi TEKRARLAMA — onek tiresiz olsun ("mw" gibi).

Kullanim (MaCiT migrasyonu dahil):

    import importlib.util, os
    _s = importlib.util.spec_from_file_location("r2_anahtar", "/Users/okan/dev/pruvo/tools/r2_anahtar.py")
    r2k = importlib.util.module_from_spec(_s); _s.loader.exec_module(r2k)

    r2k.gkey("Thingiverse", "6543210")     -> "th6543210"
    r2k.gkey("Printables", 1234567)        -> "pr1234567"
    r2k.gkey("MakerWorld", 998877)         -> "mw998877"
    r2k.gkey("CGTrader", "6267929")        -> "cgt-6267929"   (tarihsel tire, bkz yukarisi)
    r2k.gkey_ham("th6543210")              -> "th6543210"     (onek zaten yapistiysa)
    r2k.gorsel_yolu("th6543210", 1)        -> "urunler/th6543210-1.jpg"
    r2k.gorsel_url("th6543210", 1)         -> "https://media.pruvo3d.com/urunler/th6543210-1.jpg"
    r2k.urun_slug("Kapı Kolu Çerçevesi")   -> "kap-kolu-erevesi"   (JSON id/SEO; ANAHTAR DEGIL)
    r2k.url_kacir("https://x/ö.jpg")       -> ASCII-guvenli URL

ASCII-disi/Unicode: anahtar normalizasyonu [a-z0-9-] disindaki HER SEYI (Turkce harf,
bosluk, tirnak, emoji) tireye cevirir -> anahtar daima ASCII'dir. Uzak URL'leri
kacirmak icin url_kacir() kullan; safe kumesi thing-hazirla.py / thingiverse-gallery.py
ile AYNIdir (":/?=&%") — orada ayrismasin diye buraya tasindi.
"""
import re
import urllib.parse

#: platform adi -> R2 anahtar oneki. cgt'deki tire TARIHSEL, korunuyor (bkz modul docstring).
ONEKLER = {
    "Thingiverse": "th",
    "Printables": "pr",
    "MakerWorld": "mw",
    "CGTrader": "cgt-",
}

#: bilinmeyen platform icin onek (gorsel-cakisma-onar.py'nin eski davranisi)
BILINMEYEN_ONEK = "x"

#: R2'de gorsellerin durdugu klasor
GORSEL_KLASOR = "urunler"

#: gorsellerin yayinlandigi CDN koku
CDN_KOK = "https://media.pruvo3d.com"

#: URL kacisinda dokunulmayacak karakterler (thing-hazirla.py / thingiverse-gallery.py ile AYNI)
URL_SAFE = ":/?=&%"

_ANAHTAR_TEMIZ = re.compile(r"[^a-z0-9-]+")
_SLUG_TEMIZ = re.compile(r"[^a-z0-9]+")


def normalize(ham):
    """Ham anahtar dizesini R2-guvenli bicime indirger: kucuk harf, [a-z0-9-] disi -> tire,
    bastaki/sondaki tireler atilir. ASCII-disi karakterler (ö, ı, ' , bosluk) tireye doner."""
    return _ANAHTAR_TEMIZ.sub("-", str(ham).lower()).strip("-")


def gkey_ham(ham, yedek=True):
    """Onek + kaynak-id zaten birlestirilmisse ("th123", "pr456") anahtari uretir.
    yedek=True: normalizasyon BOS dizeye duserse ham degeri aynen dondurur (eski davranis)."""
    k = normalize(ham)
    if k:
        return k
    return str(ham) if yedek else k


def gkey(platform, kaynak_id, yedek=True):
    """(platform, kaynak-id) -> R2 gorsel anahtari. Anahtarin TEK uretim yolu budur.

    platform: "Thingiverse" | "Printables" | "MakerWorld" | "CGTrader" (bilinmeyen -> "x")
    yedek=False: normalizasyon bos dizeye duserse ham degere DONMEZ (gorsel-cakisma-onar
    davranisi)."""
    onek = ONEKLER.get(platform, BILINMEYEN_ONEK)
    return gkey_ham(onek + str(kaynak_id), yedek=yedek)


def gorsel_yolu(anahtar, sira):
    """R2 nesne yolu: urunler/<anahtar>-<sira>.jpg (sira 1'den baslar)."""
    return "%s/%s-%d.jpg" % (GORSEL_KLASOR, anahtar, int(sira))


def gorsel_url(anahtar, sira):
    """Yayindaki tam gorsel URL'si."""
    return "%s/%s" % (CDN_KOK, gorsel_yolu(anahtar, sira))


def anahtar_coz(url_ya_da_yol):
    """Var olan bir gorsel URL/yolundan (anahtar, sira) cikarir; eslesmezse (None, None).
    Migrasyon/denetimde 'yayindaki anahtar' ile 'uretilen anahtar' karsilastirmasi icin."""
    m = re.search(r"/%s/(.+?)-(\d+)\.jpg$" % GORSEL_KLASOR, str(url_ya_da_yol))
    if not m:
        m = re.match(r"^%s/(.+?)-(\d+)\.jpg$" % GORSEL_KLASOR, str(url_ya_da_yol))
    if not m:
        return (None, None)
    return (m.group(1), int(m.group(2)))


def urun_slug(metin, yedek="", uzunluk=60):
    """urunler.json id'si / SEO URL'si icin baslik slug'i. DIKKAT: bu ANAHTAR DEGILDIR —
    R2 anahtarini ASLA baslik slug'indan turetme (cakisma/ezme sebebi)."""
    s = _SLUG_TEMIZ.sub("-", str(metin or yedek).lower()).strip("-")[:uzunluk]
    return s or str(yedek)


def url_kacir(u):
    """Uzak (kaynak) URL'sini ASCII-guvenli hale getirir. ASCII-disi karakter iceren CDN
    url'leri urllib'de UnicodeEncodeError ile cokuyordu."""
    return urllib.parse.quote(str(u), safe=URL_SAFE)
