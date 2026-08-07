#!/usr/bin/env python3
"""r2_anahtar.py — R2 gorsel anahtari turetmenin TEK DOGRULUK KAYNAGI.

Neden: anahtar turetme 4 ayri dosyada satir-ici kopyalanmisti (urun-ekle.py,
printables-ekle.py, makerworld-ekle.py, gorsel-cakisma-onar.py). Kopyalar birbirinden
kaydiginda iki urunun gorseli AYNI R2 anahtarina yazilir ve biri digerini EZER
(yayindaki gorsel kirilir). Artik tek yer burasi.

TEMEL KURAL: anahtar KAYNAK-ID'den turer (th<tid> / pr<pid> / mw<did> / cgt-<itemid> /
c3d<slug>), urun BASLIGINDAN degil. Iki farkli urun ayni Turkce basligi uretse bile
anahtarlari cakismaz.

⚠️ TARIHSEL TUZAK (7 Agu 2026 KraL hukmuyle KAPANDI) — CGTrader oneginde ESKIDEN
FAZLADAN TIRE vardi ("cgt-"), th/pr/mw/c3d'de hic olmadi. Kanonik onek artik TIRESIZ
"cgt" (ikiz hasat_ortak.PLATFORMLAR="cgt" · canli katalogda 101 tiresiz / 16 tireli ·
CLAUDE.md "pr/th/cgt"). ESKI 16 tireli canli anahtar ("cgt-<itemid>-<n>.jpg") OLDUGU
GIBI KALIR (uzerine yazmak yasak) ve YENIDEN BASILMAZ; hukum yalniz BUNDAN SONRA
uretilecek anahtarlari baglar. YENI platform eklerken bu eski hatayi TEKRARLAMA —
onek tiresiz olsun ("mw" gibi).

Cults3D'de kaynak kimligi SLUG'dir (cults3d.com/.../<slug>), sayisal id degil — "c3d"
oneki + slug kullan (bkz r2-onek-gelenek-kapisi.py, `gkey("Cults3D", slug)`). Canli
katalogda 1047/1063 kayit zaten bu gelenekle uyumlu (7 Agu 2026 olcumu); 15 kayit
sayisal-id + 1 kayit "x" (bilinmeyen-onek) oneki tasiyan TARIHSEL kalinti — bunlar
DEGISTIRILMEZ (ayni R2 anahtarinin uzerine yazmak yasak), yalniz YENILERININ dogmasi
tools/r2-onek-gelenek-kapisi.py ile engellenir.

Kullanim (MaCiT migrasyonu dahil):

    import importlib.util, os
    _s = importlib.util.spec_from_file_location("r2_anahtar", "/Users/okan/dev/pruvo/tools/r2_anahtar.py")
    r2k = importlib.util.module_from_spec(_s); _s.loader.exec_module(r2k)

    r2k.gkey("Thingiverse", "6543210")     -> "th6543210"
    r2k.gkey("Printables", 1234567)        -> "pr1234567"
    r2k.gkey("MakerWorld", 998877)         -> "mw998877"
    r2k.gkey("CGTrader", "6267929")        -> "cgt6267929"    (7 Agu 2026'dan sonra; eski canli "cgt-<id>" degismez)
    r2k.gkey("Cults3D", "some-model-slug") -> "c3dsome-model-slug"
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

#: platform adi -> R2 anahtar oneki. CGTrader "cgt" (tiresiz) 7 Agu 2026 KraL hukmuyle
#: kanonik oldu (ikiz hasat_ortak.PLATFORMLAR="cgt" · canli 101 tiresiz/16 tireli ·
#: CLAUDE.md pr/th/cgt); ESKI 16 tireli canli anahtar ("cgt-...") DEGISMEZ, yeniden
#: basilmaz — hukum yalniz BUNDAN SONRAKI mint'leri baglar (bkz modul docstring).
#: Cults3D "c3d" (tiresiz) 7 Agu 2026 mimar hukmuyle eklendi — canli katalogda zaten
#: BASKIN gelenek (1047/1063), sayisal-id azinlik (15) TARIHSEL kalinti (bkz
#: r2-onek-gelenek-kapisi.py). BURAYA yeni platform eklerken canli veriyle DOGRULA.
ONEKLER = {
    "Thingiverse": "th",
    "Printables": "pr",
    "MakerWorld": "mw",
    "CGTrader": "cgt",   # 7 Agu 2026 KraL hukmu: tiresiz kanonik; eski "cgt-" canlida degismeden kalir
    "Cults3D": "c3d",
}

#: bilinmeyen platform icin onek (gorsel-cakisma-onar.py'nin eski davranisi, yalniz
#: bilinmeyen_sessiz=True ile erisilir — bkz gkey())
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


class BilinmeyenPlatform(ValueError):
    """gkey() bilinmeyen bir platform icin cagrildi ve bilinmeyen_sessiz=False (varsayilan).
    FAIL-CLOSED: sessizce "x<id>" uretip devam etmek yerine burada durur — bkz modul
    docstring'indeki 7 Agu 2026 olcumu (Cults3D bosluk 1 canli kaydi "x" onekiyle
    yayina soktu, farkedilmesi haftalar surdu)."""


def gkey(platform, kaynak_id, yedek=True, bilinmeyen_sessiz=False):
    """(platform, kaynak-id) -> R2 gorsel anahtari. Anahtarin TEK uretim yolu budur.

    platform: "Thingiverse" | "Printables" | "MakerWorld" | "CGTrader" | "Cults3D"
    yedek=False: normalizasyon bos dizeye duserse ham degere DONMEZ (gorsel-cakisma-onar
    davranisi).
    bilinmeyen_sessiz=False (varsayilan): ONEKLER'de olmayan platform icin BilinmeyenPlatform
    firlatir (FAIL-CLOSED — bkz 7 Agu 2026 Cults3D "x" onek olayi, modul docstring).
    bilinmeyen_sessiz=True: eski davranisa doner ("x<id>" uretir, stderr'e UYARI basar) —
    yalniz gorsel-cakisma-onar.py'nin cok-kaynakli (ONEKLER'de YER ALMAYAN ama gecerli
    kaynak etiketleri tasiyan) collision-onarim akisinda ACIKCA istenmeli. Kaynak ADLARI
    PUBLIC repoya YAZILMAZ (CLAUDE.md GIZLILIK); dagilim .urun-kaynaklari.json'dadir."""
    if platform not in ONEKLER:
        if not bilinmeyen_sessiz:
            raise BilinmeyenPlatform(
                "gkey: bilinmeyen platform %r (kaynak_id=%r) — ONEKLER'e ekle ya da "
                "kasitliyse bilinmeyen_sessiz=True gec" % (platform, kaynak_id))
        import sys as _sys
        print("UYARI r2_anahtar.gkey: bilinmeyen platform %r -> %r oneki (id=%r)"
              % (platform, BILINMEYEN_ONEK, kaynak_id), file=_sys.stderr)
        onek = BILINMEYEN_ONEK
    else:
        onek = ONEKLER[platform]
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
