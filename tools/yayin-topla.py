#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/yayin-topla.py — YAYIN KLASORUNU (`_site`) TOPLAYAN TEK KAYNAK.

NE YAPAR: `deploy.yml::build` isinin "Yayin klasorunu topla (beyaz liste)" adiminin
GOVDESIDIR. build.py'nin urettigi dosyalari BEYAZ LISTE ile `_site/` altina toplar.
Yayina SADECE sitenin ihtiyac duydugu dosyalar girer (eskiden `path: .` tum repoyu
yayinliyordu -> tools/*.py canli siteden indirilebiliyordu; denetim 2026-07-15).

NEDEN PYTHON (19 Agu 2026, KraL/mimar hukmu — K80 blokajinin (a) yolu): ayni is
`run: |` altinda 39 satirlik bir KABUK bloguydu (`mkdir` · `cp` · `if [ ... ]` ·
`while IFS= read -r`). tools/is-akisi-kapisi.py'nin K80 kolu DEGISEN her CI adimini
hedef commitin agacinda KOSTURUP yesil gormek zorundadir; kosturucusu ise yalniz
`python3 <betik>` / `node <betik>` bicimini ayristirir (K80_META kabuk metakarakteri
gorurse OLCULEMEDI). Sonuc: yayin adiminin METNI her degistiginde K80 fail-closed
BLOKLUYOR ve o adim CI'ya girmeden ONCE hicbir yerde OLCULEMIYORDU. (b) yolu — K80'e
"kabuk blogu muafiyeti" eklemek — REDDEDILDI: kapinin cekirdek amaci tam olarak
"degisen yayin adimi olculmeden gecmesin"dir, muafiyet o ekseni oldururdu
([[kapi-kapsam-genisletme-tuzagi]]). Bu yuzden ADIM araca tasindi, KAPI GEVSETILMEDI.

🔴 DAVRANIS BIREBIR KORUNDU. Tasima sirasinda hicbir kural gevsemedi:
  * `mkdir _site` -> `_site` ZATEN VARSA HATA (kabukta `mkdir -p` DEGILDI).
  * her kopyalama kaynagi eksikse SIFIR-DISI rc + EKSIK YOLUN ADI basilir
    (kabukta `set -e` altinda `cp` hata verip adimi dusuruyordu).
  * `varlik/` yok ya da BOSSA rc=1 (sayfalar ciplak kalirdi).
  * `_yayin-icerik-dizinleri.txt` yok/bossa rc=1; icindeki her slug icin dizin
    yoksa rc=1 + SLUG ADI.
Esdegerlik ANLATILMADI, OLCULDU: refaktor oncesi kabuk blogu ile bu arac ayni
fikstur agacinda kosturulup uretilen `_site` agaci DOSYA SAYISI + HER YOLUN SHA256'si
duzleminde karsilastirildi (fark 0). Olcum `--kendini-test` kolunda YASAR.

KOL SECIMI (deploy.yml adimi TEK SATIR: `python3 tools/yayin-topla.py`):
  * BAYRAKSIZ  -> once HERMETIK OZ-TEST (fikstur + oldurucu mutant), sonra GERCEK
                  toplama. Oz-testin her yayinda kosmasi BILINCLIDIR: aracin kendisi
                  her yayin oncesi kanitlanir ve maliyeti milisaniyedir.
  * --kendini-test -> YALNIZ hermetik batarya (fikstur + esdegerlik + mutantlar).

🔴 KAYNAK AGACI KOLU (K80'in kosturdugu hal) — GEVSETME DEGIL, BEYAN: K80 adimi
hedef commitin TEMIZ bir worktree'sinde kosturur. build.py'nin URETTIGI girdilerin
tamami .gitignore'dadir (`/urun/`, `/_yayin/`, `/varlik/`, `/index.built.html`,
`/_yayin-icerik-dizinleri.txt`, `/ozet.json`, `/sitemap.xml`, ...) -> o agacta
URETILEN girdi YOKTUR (izlenen `urunler.json`/`CNAME`/`ege-bilgi.md`/
`jenerator/urunler` orada DA vardir ve hazirlik sinyali SAYILMAZ; YALNIZ izlenen kume
elle beyan edilir, uretilenler onun TUMLEYENIDIR ve oz-test bolmenin TAM oldugunu +
beyan edilen her izlenen girisin depoda GERCEKTEN durdugunu her kosumda dogrular).
Bu halde arac:
  * `GITHUB_ACTIONS` ORTAMDAYSA (yani GERCEK yayin hattinda) rc=1 verir — CI'da
    "build.py kosmamis" sessiz-yesil OLAMAZ, kural BUGUNKUNDEN SIKIDIR;
  * ortam disinda (yerel pre-push K80 dumani) hermetik oz-testin SONUCUNU dondurur
    ve `KAYNAK AGACI` satirini BASAR. Yani K80'in gordugu yesil bir NO-OP degil,
    kosulmus bir OLCUMDUR.
YARIM hazirlikta (girdilerin bir kismi var) kol AYRIM YAPMAZ: rc=1 + eksik yol.

TEK KAYNAK SOZLESMESI (kopyalama = drift): `MANIFESTO` yayin adiminin TEK kaynagidir.
YAYINLANACAK JS KUMESI ise burada TEKRARLANMAZ — `build.py::SOYULACAK_JS`ten gelir
(build onu `_yayin/site-varliklari.txt`e yazar, bu arac oradan kopyalar). Boylece yeni
bir JS varligi tek yerde beyan edilir ve yayina kendiliginden girer; elle beyaz liste
TUTULMAZ (K184'te `talep-alanlari.js` bu yoldan geldi). Arac o sabiti METIN ARAYARAK
degil `ast.literal_eval` ile DEGER olarak okur -> yoruma alinmis satir iddiayi
dogrulayamaz. "Yayin hatti su varligi tasiyor mu" sorusunu soran tuketiciler de METIN
ARAMAZ, `yayin_varligi_tasiniyor_mu()` fonksiyonunu cagirir:
  * tools/is-akisi-kapisi.py     -> E_ZORUNLU_VARLIKLAR nobeti (CI'da BLOKLAYICI)
  * jenerator/test/kabul.py      -> TEST 4 (hacim.js tek kaynak + yayin kopyasi)

Cikis kodlari: 0 = YESIL · 1 = KIRMIZI.
"""
import argparse
import ast
import collections
import hashlib
import io
import os
import shutil
import sys
import tempfile

# ---------------------------------------------------------------------------
# MANIFESTO — YAYIN BEYAZ LISTESI (TEK KAYNAK)
# ---------------------------------------------------------------------------
# Adim turleri (kabuk karsiliklari yaninda yazili):
#   DIZIN_KUR      -> `mkdir <hedef>`            (VARSA HATA; `-p` DEGIL)
#   DIZIN_KUR_P    -> `mkdir -p <hedef>`         (idempotent; varlik kolu kurmus olabilir)
#   DOSYA          -> `cp <kaynak> <hedef>`      (tek dosya, ADI DEGISEBILIR)
#   DOSYALAR       -> `cp <k1> <k2> ... <hedef>/`(coklu dosya, ayni ada)
#   AGAC           -> `cp -r <kaynak> <hedef>`   (dizin agaci)
#   DIZIN_DOLU     -> `if [ ! -d x ] || [ -z "$(ls -A x)" ]; then ... exit 1; fi`
#   MANIFEST_DONGU -> `while IFS= read -r slug; do ... cp -r "$slug" "_site/$slug"; done`
#   VARLIK_KOPYA   -> JS varlik manifesti (`_yayin/site-varliklari.txt`) dongusu
#   VARLIK_DOGRULA -> ayni manifest uzerinde "kopya var ve BOS DEGIL" gecisi
#   KRITIK_VARLIK  -> `test -s <yol>` + sha256 okunabilirligi (kucuk kritik kume)
Adim = collections.namedtuple("Adim", "tur kaynaklar hedef tani")

SITE = "_site"
ICERIK_MANIFESTI = "_yayin-icerik-dizinleri.txt"
# JS yayin varliklarinin manifesti — build.py YAZAR (tek kaynagi `build.SOYULACAK_JS`),
# bu arac OKUR. Elle beyaz liste TUTULMAZ: yeni bir JS varligi build tarafinda listeye
# eklenince yayina kendiliginden girer (K184'te `talep-alanlari.js` boyle geldi).
VARLIK_MANIFESTI = "_yayin/site-varliklari.txt"
# Yokluğu ÜRETİM OLAYI olan kucuk kritik kume (manifest dogrulamasindan AYRI, bilincli
# olarak DAR): parametrik konfiguratorun hacim/fiyat cekirdegi.
KRITIK_VARLIKLAR = (SITE + "/jenerator/hacim.js",)

MANIFESTO = (
    Adim("DIZIN_KUR", (), SITE,
         "yayin klasoru"),
    # Ana sayfa: build.py'nin urettigi YAYIN kopyasi (script src'leri ?v=<hash> ile
    # onbellek-kirici surumlu). KAYNAK index.html yayina GIRMEZ.
    Adim("DOSYA", ("index.built.html",), SITE + "/index.html",
         "ana sayfanin yayin kopyasi"),
    # JS varliklari _yayin/'dan gelir: build.py onlarin YORUMU SOYULMUS yayin kopyasini
    # oraya yazar (kaynak dosyalar depoda tam dokumantasyonla KALIR, tarayiciya inmez).
    # Manifest ya da bir dosya yoksa kol HATA verir -> yayin durur (fail-closed; sessizce
    # yorumlu kaynak yayinlanamaz, sessizce EKSIK varlik da yayinlanamaz).
    Adim("VARLIK_KOPYA", (VARLIK_MANIFESTI,), SITE,
         "yorumu soyulmus JS yayin kopyalari (manifest kolu)"),
    Adim("VARLIK_DOGRULA", (VARLIK_MANIFESTI,), SITE,
         "her yayin varligi hedefte VAR ve BOS DEGIL"),
    Adim("KRITIK_VARLIK", KRITIK_VARLIKLAR, None,
         "kritik varlik kumesi (yoklugu uretim olayi)"),
    # ozet.json = FAZ 3 ilk-boyama dosyasi (build.py render_ozet uretir). Bayrak
    # (index.html EDGE_KATALOG) KAPALIYKEN site onu cekmez; yine de yayina girer ki bayrak
    # acildigi an dosya CDN'de hazir olsun (eklenmeseydi bayrak acilinca ana sayfa 404
    # alip bos kalirdi). konfigur.js = dekor konfiguratoru modulu (varlik manifestinde;
    # bugun konfigurlu urun yok, dosya yayinda hazir bekler — taban-fiyatlar deseni).
    Adim("DOSYALAR", ("urunler.json", "ozet.json", "CNAME", "ege-bilgi.md",
                      "robots.txt", "sitemap.xml", "merchant-feed.xml", ".nojekyll"),
         SITE, "katalog + kok meta dosyalari"),
    Adim("AGAC", ("urun",), SITE + "/urun",
         "urun sayfalari"),
    # SAYFA VARLIKLARI (/varlik/*.css,*.js): build.py'nin urettigi icerik-adresli
    # same-origin dosyalar. Sayfalar bunlara REFERANS verir (gomulu degil) -> dizin
    # eksik/bos gelirse TUM sayfalar CIPLAK yayinlanirdi; fail-closed kontrol edilir.
    # Yorumlari uretim aninda soyulmustur (build.varlik_adres), bu yuzden _yayin/ yok.
    Adim("DIZIN_DOLU", ("varlik",), None,
         "varlik/ yok veya bos (build.py kosmadi mi?) -> sayfalar ciplak kalir"),
    Adim("AGAC", ("varlik",), SITE + "/varlik",
         "icerik-adresli sayfa varliklari"),
    # Icerik/yasal sayfa dizinleri: build.py'nin urettigi manifestten (TEK KAYNAK
    # sayfalar.py SITEMAP_SLUGS + marka/hub/kategori dizinleri) kopyalanir -> yeni
    # CONTENT_PAGES otomatik yayina girer, elle beyaz-liste tutulmaz (eskiden buraya
    # eklenmeyen sayfa sessizce 404'tu).
    Adim("MANIFEST_DONGU", (ICERIK_MANIFESTI,), SITE,
         "icerik/yasal sayfa dizinleri"),
    # Parametrik konfigurator varliklari — SADECE public dosyalar (test/ GIRMEZ):
    # konfigurator JS'leri VARLIK MANIFESTINDEN gelir (hacim.js · konfigurator.js ·
    # viewer.js); burada yalniz sema agaci kopyalanir. Dizin varlik kolunda ZATEN
    # kurulmus olabilir -> `-p` idempotentlik icindir.
    Adim("DIZIN_KUR_P", (), SITE + "/jenerator",
         "parametrik konfigurator klasoru"),
    Adim("AGAC", ("jenerator/urunler",), SITE + "/jenerator/urunler",
         "parametrik urun semalari"),
)


# ---- GIRDI SINIFLARI: "build.py kosmus mu" sorusunun TEK KAYNAGI --------------
# 🔴 NEDEN ELLE SINIFLANDIRMA (olculdu 19 Agu 2026): ilk yazimda "hicbir girdi yoksa
# kaynak agacidir" denmisti ve bu YANLIS cikti — `urunler.json` · `CNAME` ·
# `ege-bilgi.md` · `jenerator/urunler` GIT'TE IZLENIR, yani TEMIZ bir checkout'ta da
# VARDIR. Sonuc: temiz agacta kol "yarim hazirlik" sanip `index.built.html` yok diye
# KIRMIZI donuyordu (K80 dumani kirmizi). Ayrim IZLENEN/URETILEN ekseninde yapilir:
#   URETILEN  -> .gitignore'da; SADECE build.py yazar. Hicbiri yoksa build.py KOSMAMIS.
#   IZLENEN   -> depoda commit'li; temiz checkout'ta da vardir, hazirlik SINYALI DEGIL.
# Iki kume manifestonun kaynaklarini TAM BOLER; kendini_test bunu her kosumda dogrular
# -> manifestoya siniflandirilmamis yeni bir kaynak eklemek KIRMIZI yakar (sessiz drift
# imkansiz, [[ikiz-tanim-sessiz-ayrisma]]).
# 🔴 ASIMETRI BILINCLIDIR: YALNIZ IZLENEN kume ELLE BEYAN EDILIR, uretilenler ONUN
# TUMLEYENIDIR. Ters kurulum tehlikeli yonde yanilirdi — build.py'nin urettigi yeni bir
# girdi yanlislikla "izlenen" sayilsaydi "kaynak agaci" hukmu GENISLER ve CI'da yarim
# hazirlik sessiz-yesile donebilirdi. Bu yonde yanilma DARALTIR: beyan edilmemis bir
# izlenen dosya "uretilen" sayilir ve kol yalnizca daha erken KIRMIZI verir.
IZLENEN_GIRDILER = (
    "urunler.json", "CNAME", "ege-bilgi.md", "jenerator/urunler",
)


def uretilen_girdiler(manifesto=MANIFESTO, build_yolu=None):
    """build.py'nin URETTIGI girdiler = tum kaynaklar + iki manifest, IZLENEN haric."""
    hepsi = list(yayin_kaynaklari(manifesto, build_yolu or BUILD_YOLU))
    for m in (ICERIK_MANIFESTI, VARLIK_MANIFESTI):
        if m not in hepsi:
            hepsi.append(m)
    return tuple(y for y in hepsi if y not in IZLENEN_GIRDILER)


class YayinHatasi(Exception):
    """Toplama DURDU. Mesaj HANGI YOLUN sorun cikardigini SOYLER (sessiz hata YASAK)."""


# ---------------------------------------------------------------------------
# TUKETICI SOZLESMESI — "yayin hatti su varligi tasiyor mu"
# ---------------------------------------------------------------------------
BUILD_YOLU = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build.py")


def soyulacak_js(build_yolu=BUILD_YOLU):
    """build.py::SOYULACAK_JS'in DEGERI (yayinlanacak JS varliklarinin TEK KAYNAGI).

    🔴 AST ILE OKUNUR, METIN ARANMAZ. Neden: bu deger yayin beyaz listesidir ve onu
    "dosyada `hacim.js` gecıyor mu" diye olcmek, yoruma alinmis/olu bir satirin iddiayi
    dogru gostermesine izin verirdi — 30 Tem'de deploy.yml metninde oldurulen delik
    sinifinin ta kendisi. `ast.literal_eval` ATAMANIN DEGERINI okur: satir silinirse ya
    da yoruma alinirsa burasi HATA verir, sessizce True donmez.

    FAIL-CLOSED: okunamazsa YayinHatasi firlatir — 'olculemedi' bu iddiada sessiz-yesille
    aynidir."""
    if not os.path.isfile(build_yolu):
        raise YayinHatasi("HATA: %s YOK — yayin JS beyaz listesi OKUNAMADI" % build_yolu)
    try:
        with io.open(build_yolu, encoding="utf-8") as f:
            agac = ast.parse(f.read(), filename=build_yolu)
    except (OSError, SyntaxError) as e:
        raise YayinHatasi("HATA: %s ayristirilamadi (%s)" % (build_yolu, e))
    for dugum in agac.body:
        if not isinstance(dugum, ast.Assign):
            continue
        if not any(isinstance(h, ast.Name) and h.id == "SOYULACAK_JS"
                   for h in dugum.targets):
            continue
        try:
            deger = ast.literal_eval(dugum.value)
        except ValueError as e:
            raise YayinHatasi("HATA: build.py::SOYULACAK_JS sabit bir deger DEGIL (%s)" % e)
        if not deger or not all(isinstance(x, str) and x for x in deger):
            raise YayinHatasi("HATA: build.py::SOYULACAK_JS bos ya da dize olmayan giris "
                              "tasiyor: %r" % (deger,))
        return tuple(deger)
    raise YayinHatasi("HATA: build.py icinde SOYULACAK_JS ATAMASI YOK (sozlesme degismis) "
                      "— yayin JS beyaz listesi olculemedi")


def yayin_kaynaklari(manifesto=MANIFESTO, build_yolu=BUILD_YOLU):
    """Yayina TASINAN tum kaynak yollari (sirali, tekrarsiz).

    Iki kaynaktan birlesir:
      * MANIFESTO'nun DOSYA/DOSYALAR/AGAC adimlari (statik yollar);
      * VARLIK_KOPYA adimi -> `_yayin/<x>` for x in build.py::SOYULACAK_JS.
    Kontrol adimlari (DIZIN_DOLU · VARLIK_DOGRULA · KRITIK_VARLIK) ve dizin kurma
    KAYNAK SAYILMAZ: onlar bir varligi YAYINA TASIMAZ, on-kosul/son-kosul olcerler."""
    yollar = []
    for adim in manifesto:
        if adim.tur == "VARLIK_KOPYA":
            for rel in soyulacak_js(build_yolu):
                yol = "_yayin/" + rel
                if yol not in yollar:
                    yollar.append(yol)
            continue
        if adim.tur not in ("DOSYA", "DOSYALAR", "AGAC"):
            continue
        for k in adim.kaynaklar:
            if k not in yollar:
                yollar.append(k)
    return yollar


def yayin_varligi_tasiniyor_mu(varlik, manifesto=MANIFESTO, build_yolu=BUILD_YOLU):
    """<varlik> yayin hattinda GERCEKTEN kopyalaniyor mu? (bool)

    NEDEN FONKSIYON, NEDEN METIN ARAMA DEGIL: iddia 30 Tem'e kadar deploy.yml
    METNINDE `jenerator/hacim.js` alt-dizesini ariyordu; satir `echo cp ...`'a
    cevrilse ya da yoruma alinsa iddia HALA True kaliyordu. Satir Python'a tasininca
    ayni delik "kaynak dosyada gecen dize" olarak geri gelirdi. Bu yuzden hukum
    VERI'den (MANIFESTO'dan) turer: satiri silmek fonksiyonu False yapar.

    Eslesme: tam yol VEYA yol-soneki (`jenerator/hacim.js` ->
    `_yayin/jenerator/hacim.js`). Soyulmus yayin kopyasi ile kaynagin ayni varligi
    gosterdigi tek yer burasidir."""
    hedef = os.path.normpath(varlik)
    for kaynak in yayin_kaynaklari(manifesto, build_yolu):
        n = os.path.normpath(kaynak)
        if n == hedef or n.endswith("/" + hedef):
            return True
    return False


# ---------------------------------------------------------------------------
# TOPLAMA — GERCEK IS
# ---------------------------------------------------------------------------
def _tam(kok, rel):
    return os.path.join(kok, rel.replace("/", os.sep))


def _dizin_kur(kok, hedef):
    yol = _tam(kok, hedef)
    if os.path.exists(yol):
        raise YayinHatasi("HATA: %s ZATEN VAR — yayin klasoru temiz agaca kurulur "
                          "(kabuk karsiligi `mkdir`, `-p` DEGIL)" % hedef)
    try:
        os.mkdir(yol)
    except OSError as e:
        raise YayinHatasi("HATA: %s kurulamadi: %s" % (hedef, e))


def _dosya_kopyala(kok, kaynak, hedef_yol):
    k = _tam(kok, kaynak)
    if not os.path.isfile(k):
        raise YayinHatasi("HATA: yayin kaynagi YOK: %s (build.py kosmadi mi?)" % kaynak)
    try:
        shutil.copy2(k, _tam(kok, hedef_yol))
    except OSError as e:
        raise YayinHatasi("HATA: %s -> %s kopyalanamadi: %s" % (kaynak, hedef_yol, e))


def _agac_kopyala(kok, kaynak, hedef):
    k = _tam(kok, kaynak)
    if not os.path.isdir(k):
        raise YayinHatasi("HATA: yayin dizini YOK: %s (build.py kosmadi mi?)" % kaynak)
    try:
        # symlinks=True: kabuk `cp -r` de baglantiyi BAGLANTI olarak kopyalar
        # (GNU cp -R varsayilani); dereference etmek agaci sessizce SISIRIRDI.
        shutil.copytree(k, _tam(kok, hedef), symlinks=True)
    except (OSError, shutil.Error) as e:
        raise YayinHatasi("HATA: %s -> %s agaci kopyalanamadi: %s" % (kaynak, hedef, e))


def _dizin_dolu(kok, kaynak, tani):
    yol = _tam(kok, kaynak)
    if not os.path.isdir(yol) or not os.listdir(yol):
        raise YayinHatasi("HATA: %s" % tani)


def _varlik_manifesti_oku(kok, manifest_rel):
    """Manifest satirlarini dondur. BOS SATIR HATADIR (icerik dizini dongusunden FARKLI:
    orada bos satir ATLANIR, burada yayin varligi manifestinde bos satir bir URETIM
    kusurudur ve fail-closed durdurulur — kabuk kolunun davranisi birebir korundu)."""
    yol = _tam(kok, manifest_rel)
    if not os.path.isfile(yol) or os.path.getsize(yol) == 0:
        raise YayinHatasi("HATA: %s bos/yok (build.py kosmadi mi?)" % manifest_rel)
    with io.open(yol, encoding="utf-8") as f:
        ham = f.read()
    satirlar = ham.split("\n")
    if satirlar and satirlar[-1] == "":       # kabuk `read` son yeni satiri kayit saymaz
        satirlar = satirlar[:-1]
    return [s.strip("\r") for s in satirlar]


def _varlik_kopya(kok, manifest_rel, hedef_kok):
    kopyalanan = 0
    for varlik in _varlik_manifesti_oku(kok, manifest_rel):
        if not varlik:
            raise YayinHatasi("HATA: site varlik manifestinde bos satir")
        kaynak = "_yayin/" + varlik
        if not os.path.isfile(_tam(kok, kaynak)):
            raise YayinHatasi("HATA: manifest varligi yok: %s" % kaynak)
        hedef = hedef_kok + "/" + varlik
        ust = os.path.dirname(_tam(kok, hedef))
        if ust and not os.path.isdir(ust):
            os.makedirs(ust)
        _dosya_kopyala(kok, kaynak, hedef)
        kopyalanan += 1
    return kopyalanan


def _varlik_dogrula(kok, manifest_rel, hedef_kok):
    """Kopyalama SONRASI gecis: her varlik hedefte VAR ve BOS DEGIL.

    Ayri bir gecistir cunku "kopyaladim" ile "yayinda duruyor ve icerigi var" ayni sey
    DEGILDIR (bos dosya kopyalamak sessizce basarilidir; tarayici bos JS'i hatasiz yukler
    ve sayfa islevsiz kalir)."""
    sayi = 0
    for varlik in _varlik_manifesti_oku(kok, manifest_rel):
        if not varlik:
            raise YayinHatasi("HATA: varlik dogrulama manifestinde bos satir")
        hedef = hedef_kok + "/" + varlik
        yol = _tam(kok, hedef)
        if not os.path.isfile(yol) or os.path.getsize(yol) == 0:
            raise YayinHatasi("HATA: yayin varligi yok/bos: %s" % hedef)
        sayi += 1
    return sayi


def _kritik_varlik(kok, yollar):
    """Kucuk KRITIK kume: dosya var + BOS DEGIL + baytlari okunabilir (sha256 hesaplanir).

    Manifest dogrulamasindan AYRI ve BILINCLI OLARAK DAR tutulur: bu kumedeki bir
    dosyanin yoklugu bir URETIM OLAYIDIR (parametrik urun sayfasi fiyat hesaplamaz)."""
    for hedef in yollar:
        yol = _tam(kok, hedef)
        if not os.path.isfile(yol) or os.path.getsize(yol) == 0:
            raise YayinHatasi("HATA: KRITIK yayin varligi yok/bos: %s" % hedef)
        try:
            with open(yol, "rb") as f:
                h = hashlib.sha256()
                for parca in iter(lambda: f.read(65536), b""):
                    h.update(parca)
        except OSError as e:
            raise YayinHatasi("HATA: KRITIK yayin varligi okunamadi: %s (%s)" % (hedef, e))


def _manifest_dongu(kok, manifest_rel, hedef_kok):
    yol = _tam(kok, manifest_rel)
    if not os.path.isfile(yol) or os.path.getsize(yol) == 0:
        raise YayinHatasi("HATA: %s bos/yok (build.py kosmadi mi?)" % manifest_rel)
    with io.open(yol, encoding="utf-8") as f:
        ham = f.read()
    kopyalanan = 0
    for satir in ham.split("\n"):
        slug = satir.strip("\r")
        if not slug:                      # kabuk: `if [ -z "$slug" ]; then continue; fi`
            continue
        if not os.path.isdir(_tam(kok, slug)):
            raise YayinHatasi("HATA: icerik dizini yok: %s" % slug)
        _agac_kopyala(kok, slug, hedef_kok + "/" + slug)
        kopyalanan += 1
    return kopyalanan


def topla(kok, manifesto=MANIFESTO):
    """<kok> agacinda MANIFESTO'yu uygular; (adim_sayisi, slug_sayisi, varlik_sayisi).

    Hata halinde YayinHatasi firlatir — mesaj HANGI YOL oldugunu soyler."""
    slug_sayisi = 0
    varlik_sayisi = 0
    for adim in manifesto:
        if adim.tur == "DIZIN_KUR":
            _dizin_kur(kok, adim.hedef)
        elif adim.tur == "DIZIN_KUR_P":
            yol = _tam(kok, adim.hedef)
            if not os.path.isdir(yol):
                os.makedirs(yol)
        elif adim.tur == "VARLIK_KOPYA":
            _varlik_kopya(kok, adim.kaynaklar[0], adim.hedef)
        elif adim.tur == "VARLIK_DOGRULA":
            varlik_sayisi = _varlik_dogrula(kok, adim.kaynaklar[0], adim.hedef)
        elif adim.tur == "KRITIK_VARLIK":
            _kritik_varlik(kok, adim.kaynaklar)
        elif adim.tur == "DOSYA":
            _dosya_kopyala(kok, adim.kaynaklar[0], adim.hedef)
        elif adim.tur == "DOSYALAR":
            for kaynak in adim.kaynaklar:
                _dosya_kopyala(kok, kaynak,
                               adim.hedef + "/" + os.path.basename(kaynak))
        elif adim.tur == "AGAC":
            _agac_kopyala(kok, adim.kaynaklar[0], adim.hedef)
        elif adim.tur == "DIZIN_DOLU":
            _dizin_dolu(kok, adim.kaynaklar[0], adim.tani)
        elif adim.tur == "MANIFEST_DONGU":
            slug_sayisi = _manifest_dongu(kok, adim.kaynaklar[0], adim.hedef)
        else:
            raise YayinHatasi("HATA: bilinmeyen manifesto adim turu: %r" % (adim.tur,))
    return len(manifesto), slug_sayisi, varlik_sayisi


# ---------------------------------------------------------------------------
# AGAC OLCUMU — esdegerlik kanitinin ortak dili
# ---------------------------------------------------------------------------
def agac_ozeti(kok):
    """{rel_yol: sha256} — <kok> altindaki TUM dosyalar (baglanti hedefi de icerik sayilir).

    Esdegerlik olcumunun TEK dili budur: dosya SAYISI + her yolun SHA256'si.
    Kip/zaman damgasi BILEREK disarida: `cp` onlari zaten umask'a gore degistirir,
    yayina giden sey ICERIKTIR."""
    ozet = {}
    for dizin, _alt, dosyalar in os.walk(kok):
        for ad in dosyalar:
            tam = os.path.join(dizin, ad)
            rel = os.path.relpath(tam, kok).replace(os.sep, "/")
            if os.path.islink(tam):
                ozet[rel] = "symlink:" + os.readlink(tam)
                continue
            h = hashlib.sha256()
            with open(tam, "rb") as f:
                for parca in iter(lambda: f.read(65536), b""):
                    h.update(parca)
            ozet[rel] = h.hexdigest()
    return ozet


# ---------------------------------------------------------------------------
# HERMETIK OZ-TEST — fikstur + esdegerlik + oldurucu mutantlar
# ---------------------------------------------------------------------------
# Fikstur: MANIFESTO'nun HER adimini fiilen surer (her kaynak turu, dolu dizin
# kontrolu, manifest dongusu, ic ice agac, alt dizin).
FIKSTUR_DOSYALAR = {
    "index.built.html": "<!doctype html><title>ana</title>",
    "urunler.json": "[]",
    "ozet.json": "{}",
    "CNAME": "ornek.gecersiz\n",
    "ege-bilgi.md": "# bilgi\n",
    "robots.txt": "User-agent: *\n",
    "sitemap.xml": "<urlset/>",
    "merchant-feed.xml": "<rss/>",
    ".nojekyll": "",
    "urun/aaa/index.html": "urun aaa",
    "urun/bbb/index.html": "urun bbb",
    "varlik/sayfa-1.css": "body{}",
    "varlik/urun-2.js": "//u",
    "jenerator/urunler/ornek.json": "{\"id\":\"ornek\"}",
    "sss/index.html": "sss",
    "marka/renault/index.html": "renault",
    "kategori/marin/index.html": "marin",
    ICERIK_MANIFESTI: "sss\nmarka\nkategori\n",
}

# JS yayin varliklari fiksturu — manifest kolunu surer. Kok seviyesinde VE alt dizinde
# varlik var (alt dizin `_site/jenerator/` kurulumunu, kok `_site/` yolunu olcer).
FIKSTUR_VARLIKLARI = (
    "secenekler.js", "konfigur.js", "talep-alanlari.js",
    "jenerator/hacim.js", "jenerator/konfigurator.js", "jenerator/viewer.js",
    "filament-veri.js", "taban-fiyatlar.js",
)
for _rel in FIKSTUR_VARLIKLARI:
    FIKSTUR_DOSYALAR["_yayin/" + _rel] = "// yayin kopyasi: %s\n" % _rel
FIKSTUR_DOSYALAR[VARLIK_MANIFESTI] = "\n".join(FIKSTUR_VARLIKLARI) + "\n"

# Fikstur, aracin GERCEK `build.py` bagimliligini da surer: sentetik bir build.py yazilir
# ve `soyulacak_js()` ONDAN okur. Boylece "beyaz liste build.py'den gelir" iddiasi
# hermetik olarak olculur (gercek build.py'ye bagimli DEGIL, ondan BAGIMSIZ da degil:
# ayni AST yolu kosar).
FIKSTUR_BUILD_PY = (
    "# sentetik build.py (yalniz SOYULACAK_JS okunur)\n"
    "YAYIN_DIR = \"_yayin\"\n"
    "SOYULACAK_JS = (\n%s)\n"
    % "".join("    %r,\n" % r for r in FIKSTUR_VARLIKLARI)
)

# 🔴 BEKLENEN AGAC ELLE YAZILIR — MANIFESTO'DAN TURETILMEZ.
# Turetilseydi olcum TAUTOLOJI olurdu: manifesto satiri silinince beklenti de
# kuculur ve iki taraf BIRLIKTE duserdi ([[isci-yesil-tablo-ic-olcumu-bosaltir]]).
# Bu liste refaktor ONCESI kabuk blogunun URETTIGI agactir (bayt-esdegerlik olcumu
# bu listeyle kapatildi).
BEKLENEN_SITE_YOLLARI = (
    "index.html",
    "secenekler.js", "konfigur.js", "talep-alanlari.js",
    "filament-veri.js", "taban-fiyatlar.js",
    "urunler.json", "ozet.json", "CNAME", "ege-bilgi.md", "robots.txt",
    "sitemap.xml", "merchant-feed.xml", ".nojekyll",
    "urun/aaa/index.html", "urun/bbb/index.html",
    "varlik/sayfa-1.css", "varlik/urun-2.js",
    "sss/index.html", "marka/renault/index.html", "kategori/marin/index.html",
    "jenerator/hacim.js", "jenerator/konfigurator.js", "jenerator/viewer.js",
    "jenerator/urunler/ornek.json",
)

# Kaynak -> `_site` altinda hangi yola dusmeli (icerik ESITLIGI bu eslemeden olculur).
BEKLENEN_ESLEM = {
    "index.html": "index.built.html",
    "secenekler.js": "_yayin/secenekler.js",
    "konfigur.js": "_yayin/konfigur.js",
    "talep-alanlari.js": "_yayin/talep-alanlari.js",
    "filament-veri.js": "_yayin/filament-veri.js",
    "taban-fiyatlar.js": "_yayin/taban-fiyatlar.js",
    "jenerator/hacim.js": "_yayin/jenerator/hacim.js",
    "jenerator/konfigurator.js": "_yayin/jenerator/konfigurator.js",
    "jenerator/viewer.js": "_yayin/jenerator/viewer.js",
    "urun/aaa/index.html": "urun/aaa/index.html",
    "varlik/sayfa-1.css": "varlik/sayfa-1.css",
    "sss/index.html": "sss/index.html",
    "jenerator/urunler/ornek.json": "jenerator/urunler/ornek.json",
}


def _fikstur_kur(kok):
    for rel, govde in FIKSTUR_DOSYALAR.items():
        yol = _tam(kok, rel)
        ust = os.path.dirname(yol)
        if ust and not os.path.isdir(ust):
            os.makedirs(ust)
        with io.open(yol, "w", encoding="utf-8") as f:
            f.write(govde)
    os.makedirs(_tam(kok, "tools"))
    with io.open(_tam(kok, "tools/build.py"), "w", encoding="utf-8") as f:
        f.write(FIKSTUR_BUILD_PY)


def _fikstur_agacinda_topla(manifesto=MANIFESTO, bozan=None):
    """(hata_metni_ya_da_None, site_ozeti) — temiz fiksturde toplamayi kostur.

    `bozan(kok)` verilirse fikstur kurulduktan SONRA cagrilir (ariza enjeksiyonu)."""
    gecici = tempfile.mkdtemp(prefix="pruvo-yayin-topla-")
    try:
        _fikstur_kur(gecici)
        if bozan is not None:
            bozan(gecici)
        try:
            topla(gecici, manifesto)
        except YayinHatasi as e:
            return str(e), None
        return None, agac_ozeti(_tam(gecici, SITE))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def _esdegerlik_hatalari(ozet, tespit_acik=True):
    """Uretilen `_site` agaci BEKLENEN_SITE_YOLLARI ile BIREBIR ayni mi.

    `tespit_acik=False` MUTASYON CAPASIDIR ([[mutasyon-capasi-olmadan-kapi-korlesir]]):
    hukum susturulur. Batarya bu kolda YESIL kalirsa esdegerlik olcumu HICBIR SEY
    olcmuyor demektir — `_mutasyon_kontrol()` tam bunu surer."""
    if not tespit_acik:
        return []
    hatalar = []
    if ozet is None:
        return ["ESDEGERLIK: temiz fiksturde toplama HIC calismadi"]
    beklenen = set(BEKLENEN_SITE_YOLLARI)
    bulunan = set(ozet)
    eksik = sorted(beklenen - bulunan)
    fazla = sorted(bulunan - beklenen)
    if len(ozet) != len(BEKLENEN_SITE_YOLLARI):
        hatalar.append("ESDEGERLIK: dosya SAYISI %d, beklenen %d"
                       % (len(ozet), len(BEKLENEN_SITE_YOLLARI)))
    if eksik:
        hatalar.append("ESDEGERLIK: EKSIK yol(lar): %s" % ", ".join(eksik))
    if fazla:
        hatalar.append("ESDEGERLIK: FAZLA yol(lar): %s" % ", ".join(fazla))
    for hedef, kaynak in sorted(BEKLENEN_ESLEM.items()):
        beklenen_sha = hashlib.sha256(
            FIKSTUR_DOSYALAR[kaynak].encode("utf-8")).hexdigest()
        if ozet.get(hedef) != beklenen_sha:
            hatalar.append("ESDEGERLIK: %s icerigi kaynagiyla (%s) AYNI DEGIL "
                           "(sha256 %r != %r)"
                           % (hedef, kaynak, ozet.get(hedef), beklenen_sha))
    return hatalar


def _manifestten_cikar(manifesto, kaynak):
    """<kaynak>'i TASIYAN adimi manifestodan dusuren MUTANT manifesto."""
    yeni = []
    for adim in manifesto:
        if kaynak in adim.kaynaklar:
            kalan = tuple(k for k in adim.kaynaklar if k != kaynak)
            if not kalan:
                continue
            yeni.append(adim._replace(kaynaklar=kalan))
            continue
        yeni.append(adim)
    return tuple(yeni)


def kendini_test(tespit_acik=True):
    """(hatalar, iddia_sayisi) — hermetik batarya.

    `tespit_acik=False` MUTASYON CAPASIDIR: esdegerlik hukmunu oldurur. Batarya bu
    kolda YESIL kalirsa olcum sahtedir ([[mutasyon-capasi-olmadan-kapi-korlesir]])."""
    hatalar = []
    iddia = 0

    # ---- T1 TEMIZ KOSUM: uretilen agac beklenenle BIREBIR ayni --------------
    iddia += 1
    hata, ozet = _fikstur_agacinda_topla()
    if hata:
        hatalar.append("T1: temiz fiksturde toplama KIRMIZI: %s" % hata)
    else:
        hatalar.extend("T1: " + h for h in _esdegerlik_hatalari(ozet, tespit_acik))

    # ---- T2 OLDURUCU MUTANT — STATIK MANIFESTO (HEDEF KOL ATIFLI) ----------
    # Hedef kol: `topla()` — GERCEK uretim fonksiyonu; mutant SADECE manifestoyu
    # budar ve AYNI fonksiyondan gecer. Boylece "mutant izole bir kopyada oldu"
    # tautolojisi imkansizdir: olcum uretim yolunun TA KENDISIDIR.
    iddia += 1
    mutant = _manifestten_cikar(MANIFESTO, "varlik")
    m_hata, m_ozet = _fikstur_agacinda_topla(mutant)
    m_bulgu = [m_hata] if m_hata else _esdegerlik_hatalari(m_ozet, tespit_acik)
    if not m_bulgu:
        hatalar.append("T2: OLDURUCU MUTANT SAG KALDI — `varlik` agaci manifestodan "
                       "dusuruldugu halde `topla()` ciktisi beklenen agacla AYNI "
                       "gorundu; esdegerlik olcumu SAHTE")

    # ---- T2b OLDURUCU MUTANT — YAYIN BEYAZ LISTESI -------------------------
    # Yayinlanacak JS kumesi artik VERIDIR (build.py::SOYULACAK_JS -> manifest dosyasi).
    # Bu mutant o veriden `jenerator/hacim.js`i DUSURUR ve UC ayri iddiayi birden surer:
    #   (a) `topla()` KIRMIZI olmali — KRITIK VARLIK kolu bunu yakalar (yoklugu URETIM
    #       OLAYIDIR: parametrik urun sayfasi hacim.js'i 404 alir, fiyat hesaplanmaz);
    #   (b) tani HANGI YOLU kaybettigimizi SOYLEMELI (sessiz hata YASAK);
    #   (c) `yayin_varligi_tasiniyor_mu` False donmeli — yoksa tuketici nobetleri
    #       (is-akisi-kapisi E_ZORUNLU_VARLIKLAR · jenerator/test/kabul.py TEST 4) KOR.
    iddia += 1
    kalan = tuple(r for r in FIKSTUR_VARLIKLARI if r != "jenerator/hacim.js")

    def _beyaz_liste_buda(kok):
        with io.open(_tam(kok, VARLIK_MANIFESTI), "w", encoding="utf-8") as f:
            f.write("\n".join(kalan) + "\n")
        with io.open(_tam(kok, "tools/build.py"), "w", encoding="utf-8") as f:
            f.write("SOYULACAK_JS = (\n%s)\n" % "".join("    %r,\n" % r for r in kalan))

    b_hata, _b_ozet = _fikstur_agacinda_topla(bozan=_beyaz_liste_buda)
    if not b_hata:
        hatalar.append("T2b: OLDURUCU MUTANT SAG KALDI — `jenerator/hacim.js` yayin beyaz "
                       "listesinden dusuruldugu halde toplama rc=0 verdi; KRITIK VARLIK "
                       "kolu OLU")
    elif "jenerator/hacim.js" not in b_hata:
        hatalar.append("T2b: tani SESSIZ — kritik varlik dusunce mesaj hangi yolun "
                       "kaybedildigini SOYLEMIYOR: %r" % b_hata)
    gecici = tempfile.mkdtemp(prefix="pruvo-yayin-beyaz-")
    try:
        mutant_build = os.path.join(gecici, "build.py")
        with io.open(mutant_build, "w", encoding="utf-8") as f:
            f.write("SOYULACAK_JS = (\n%s)\n" % "".join("    %r,\n" % r for r in kalan))
        if yayin_varligi_tasiniyor_mu("jenerator/hacim.js", build_yolu=mutant_build):
            hatalar.append("T2b: `yayin_varligi_tasiniyor_mu` budanmis beyaz listede HALA "
                           "True — tuketici nobetleri KOR")
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    # ---- T3 SOZLESME: temiz beyaz listede zorunlu varlik GORUNUR -----------
    iddia += 1
    try:
        if not yayin_varligi_tasiniyor_mu("jenerator/hacim.js"):
            hatalar.append("T3: temiz beyaz listede `jenerator/hacim.js` GORUNMUYOR — "
                           "build.py::SOYULACAK_JS ya da yol-soneki eslesmesi bozulmus "
                           "(tuketiciler sahte-KIRMIZI yanar)")
        if yayin_varligi_tasiniyor_mu("tools/yayin-topla.py"):
            hatalar.append("T3: KANARYA — yayina GIRMEYEN bir ic arac `tasiniyor` sayildi; "
                           "eslesme cok genis (her sorguya True diyen govde)")
    except YayinHatasi as e:
        hatalar.append("T3: yayin beyaz listesi OKUNAMADI (fail-closed): %s" % e)

    # ---- T3b BEYAZ LISTE FAIL-CLOSED: build.py okunamazsa YESIL SAYILMAZ ---
    iddia += 1
    gecici = tempfile.mkdtemp(prefix="pruvo-yayin-beyaz2-")
    try:
        for ad, govde in (("yok.py", None),
                          ("bos.py", "# SOYULACAK_JS ATAMASI YOK\n"),
                          ("dinamik.py", "SOYULACAK_JS = tuple(x for x in ())\n")):
            yol = os.path.join(gecici, ad)
            if govde is not None:
                with io.open(yol, "w", encoding="utf-8") as f:
                    f.write(govde)
            try:
                soyulacak_js(yol)
            except YayinHatasi:
                continue
            hatalar.append("T3b: FAIL-OPEN — `%s` halinde beyaz liste SESSIZCE okundu; "
                           "'olculemedi' bu iddiada sessiz-yesille aynidir" % ad)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    # ---- T4..T8 FAIL-CLOSED KOLLARI: sessiz hata YASAK ---------------------
    for no, ad, bozan, beklenen_parca in (
        ("T4", "eksik kaynak dosya",
         lambda k: os.remove(_tam(k, "_yayin/konfigur.js")),
         "_yayin/konfigur.js"),
        ("T5", "varlik/ BOS",
         lambda k: [os.remove(_tam(k, "varlik/sayfa-1.css")),
                    os.remove(_tam(k, "varlik/urun-2.js"))],
         "varlik/"),
        ("T6", "icerik manifesti BOS",
         lambda k: io.open(_tam(k, ICERIK_MANIFESTI), "w").close(),
         ICERIK_MANIFESTI),
        ("T7", "manifestteki dizin YOK",
         lambda k: shutil.rmtree(_tam(k, "marka")),
         "marka"),
        ("T8", "_site ZATEN VAR",
         lambda k: os.mkdir(_tam(k, SITE)),
         SITE),
        ("T10", "varlik manifesti BOS",
         lambda k: io.open(_tam(k, VARLIK_MANIFESTI), "w").close(),
         VARLIK_MANIFESTI),
        ("T11", "varlik manifestinde BOS SATIR",
         lambda k: io.open(_tam(k, VARLIK_MANIFESTI), "w", encoding="utf-8").write(
             "secenekler.js\n\njenerator/hacim.js\n"),
         "bos satir"),
        # 🔴 BU KOL MANIFEST DOGRULAMASININ VARLIK SEBEBI: bos bir dosyayi kopyalamak
        # SESSIZCE BASARILIDIR. Tarayici bos JS'i hatasiz yukler, sayfa islevsiz kalir
        # ve hicbir yerde alarm calmaz. Kopyalama kolu bunu GORMEZ, dogrulama kolu gorur.
        ("T12", "yayin varligi BOS kopyalandi",
         lambda k: io.open(_tam(k, "_yayin/talep-alanlari.js"), "w").close(),
         "talep-alanlari.js"),
    ):
        iddia += 1
        hata, _ozet = _fikstur_agacinda_topla(bozan=bozan)
        if not hata:
            hatalar.append("%s: FAIL-OPEN — '%s' halinde toplama SESSIZCE gecti "
                           "(rc=0 olurdu; yayin eksik/bozuk cikar)" % (no, ad))
        elif beklenen_parca not in hata:
            hatalar.append("%s: tani SESSIZ — '%s' halinde mesaj hangi yolun sorun "
                           "oldugunu SOYLEMIYOR: %r" % (no, ad, hata))

    # ---- T9b GIRDI SINIFLANDIRMASI MANIFESTOYU TAM BOLUYOR MU --------------
    # Bu iddia olmadan: manifestoya YENI bir kaynak eklenip siniflandirilmazsa,
    # `_hazirlik()` onu gormezden gelir. build.py'nin URETTIGI bir dosya izlenmis
    # sayilirsa "kaynak agaci" hukmu genisler ve CI'da yarim hazirlik SESSIZ YESIL
    # olabilirdi. Iki kume kaynak kumesini TAM bolmek ZORUNDA.
    iddia += 1
    try:
        kaynaklar = set(yayin_kaynaklari()) | {ICERIK_MANIFESTI, VARLIK_MANIFESTI}
        uretilen = set(uretilen_girdiler())
        izlenen = set(IZLENEN_GIRDILER)
        if izlenen - kaynaklar:
            hatalar.append("T9b: IZLENEN_GIRDILER'de olup yayin kaynaklarinda OLMAYAN "
                           "giris: %s (bayat kayit — kaldirilmazsa uretilen bir dosya "
                           "yanlislikla 'izlenen' sayilabilir)"
                           % ", ".join(sorted(izlenen - kaynaklar)))
        if uretilen & izlenen:
            hatalar.append("T9b: bir girdi HEM uretilen HEM izlenen sayilmis: %s"
                           % ", ".join(sorted(uretilen & izlenen)))
        if uretilen | izlenen != kaynaklar:
            hatalar.append("T9b: siniflandirma kaynak kumesini TAM BOLMUYOR (fark: %s)"
                           % ", ".join(sorted(kaynaklar ^ (uretilen | izlenen))))
        # Beyan KAGITTA kalmasin: izlenen sayilan her giris GERCEKTEN depoda durmali.
        # Durmuyorsa build.py onu URETIYOR demektir ve "kaynak agaci" hukmu genislerdi.
        depo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        yok = [y for y in sorted(izlenen) if not os.path.exists(os.path.join(depo, y))]
        if yok:
            hatalar.append("T9b: IZLENEN sayilan giris depoda YOK: %s — build.py'nin "
                           "URETTIGI bir dosya izlenen sayilmis olabilir" % ", ".join(yok))
    except YayinHatasi as e:
        hatalar.append("T9b: siniflandirma OLCULEMEDI (fail-closed): %s" % e)

    # ---- T9 AGAC OLCERI kendisi calisiyor mu (olcerin nobeti) --------------
    iddia += 1
    gecici = tempfile.mkdtemp(prefix="pruvo-yayin-olcer-")
    try:
        with io.open(os.path.join(gecici, "a.txt"), "w", encoding="utf-8") as f:
            f.write("x")
        os.mkdir(os.path.join(gecici, "d"))
        with io.open(os.path.join(gecici, "d", "b.txt"), "w", encoding="utf-8") as f:
            f.write("y")
        o = agac_ozeti(gecici)
        beklenen = {
            "a.txt": hashlib.sha256(b"x").hexdigest(),
            "d/b.txt": hashlib.sha256(b"y").hexdigest(),
        }
        if o != beklenen:
            hatalar.append("T9: agac_ozeti() yanlis olcuyor: %r" % (o,))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    return hatalar, iddia


def _mutasyon_kontrol():
    """Tespit kolu olu -> batarya KIRMIZI; temiz mekanizma -> YESIL (tautoloji kanaryasi)."""
    oldurucu, _ = kendini_test(tespit_acik=False)
    kontrol, _ = kendini_test(tespit_acik=True)
    hatalar = []
    if not oldurucu:
        hatalar.append("M1: esdegerlik TESPIT KOLU sokulunce batarya YESIL kaldi — "
                       "hukum hicbir sey olcmuyor")
    if kontrol:
        hatalar.append("M1: KANARYA — temiz mekanizma KIRMIZI (%r)" % (kontrol,))
    return hatalar, 2


# ---------------------------------------------------------------------------
# HAZIRLIK OLCUMU — "build.py kosmus mu"
# ---------------------------------------------------------------------------
def _hazirlik(kok):
    """(uretilen_var, uretilen_eksik) — build.py URETTIGI girdilerden hangisi diskte.

    Hukum YALNIZ URETILEN_GIRDILER'e bakar: izlenen dosyalar temiz checkout'ta da
    vardir ve "build.py kosmus mu" sorusuna cevap VERMEZ."""
    var_olan, eksik = [], []
    for rel in uretilen_girdiler():
        (var_olan if os.path.exists(_tam(kok, rel)) else eksik).append(rel)
    return var_olan, eksik


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="deploy.yml yayin klasoru (_site) toplama adimi")
    ap.add_argument("--kendini-test", action="store_true",
                    help="YALNIZ hermetik batarya (fikstur + esdegerlik + mutantlar)")
    args = ap.parse_args()

    hatalar, iddia = kendini_test()
    m_hata, m_iddia = _mutasyon_kontrol()
    hatalar.extend(m_hata)
    iddia += m_iddia

    if args.kendini_test:
        print("YAYIN TOPLA — HERMETIK BATARYA (%d iddia)" % iddia)
    if hatalar:
        for h in hatalar:
            print("  ❌ " + h)
        print("SONUC: KIRMIZI ❌ (OZ-TEST)")
        print("OZ_TEST=KIRMIZI IDDIA=%d HATA=%d" % (iddia, len(hatalar)))
        return 1
    if args.kendini_test:
        print("  ✅ ESDEGERLIK: %d yol, sha256 eslemesi %d kayit"
              % (len(BEKLENEN_SITE_YOLLARI), len(BEKLENEN_ESLEM)))
        print("  ✅ OLDURUCU MUTANT (statik): manifestodan `varlik` agaci dusurulunce "
              "`topla()` KIRMIZI")
        print("  ✅ OLDURUCU MUTANT (beyaz liste): `jenerator/hacim.js` "
              "build.py::SOYULACAK_JS'ten dusurulunce KRITIK VARLIK kolu KIRMIZI + "
              "`yayin_varligi_tasiniyor_mu` False")
        print("  ✅ FAIL-CLOSED: eksik kaynak · bos varlik/ · bos icerik manifesti · "
              "eksik icerik dizini · dolu _site · bos varlik manifesti · manifestte "
              "bos satir · BOS kopyalanan yayin varligi · okunamayan beyaz liste")
        print("SONUC: YESIL ✅")
        print("OZ_TEST=YESIL IDDIA=%d HATA=0" % iddia)
        return 0

    kok = os.getcwd()
    try:
        uretilen_var, uretilen_eksik = _hazirlik(kok)
    except YayinHatasi as e:
        print(str(e))
        print("YAYIN_TOPLA=KIRMIZI SEBEP=BEYAZ_LISTE_OKUNAMADI")
        return 1
    if not uretilen_var:
        # KAYNAK AGACI: build.py URETTIGI girdilerin HICBIRI yok (K80'in temiz commit
        # worktree'si). CI'da bu hal FAIL-CLOSED; disarida oz-test hukmu konusur.
        if os.environ.get("GITHUB_ACTIONS"):
            print("HATA: YAYIN HAZIRLIGI YOK — build.py ciktilarinin HICBIRI yok "
                  "(_yayin/, varlik/, urun/, index.built.html ...). Yayin adimi "
                  "build.py'den SONRA kosmak ZORUNDA.")
            print("YAYIN_TOPLA=KIRMIZI SEBEP=HAZIRLIK_YOK EKSIK=%d" % len(uretilen_eksik))
            return 1
        print("KAYNAK AGACI: build.py ciktisi YOK (%d uretilen girdinin hicbiri diskte "
              "degil) -> toplanacak girdi yok; HERMETIK OZ-TEST kosuldu ve YESIL."
              % len(uretilen_eksik))
        print("YAYIN_TOPLA=OZ_TEST_YESIL IDDIA=%d TOPLANAN=0" % iddia)
        return 0

    try:
        adim_sayisi, slug_sayisi, varlik_sayisi = topla(kok)
    except YayinHatasi as e:
        print(str(e))
        print("YAYIN_TOPLA=KIRMIZI SEBEP=TOPLAMA")
        return 1
    ozet = agac_ozeti(_tam(kok, SITE))
    print("YAYIN VARLIGI DOGRULANDI: %d" % varlik_sayisi)
    print("KRITIK_VARLIK=TAMAM")
    print("OK: %s toplandi — %d manifesto adimi, %d icerik dizini, %d dosya."
          % (SITE, adim_sayisi, slug_sayisi, len(ozet)))
    print("YAYIN_TOPLA=YESIL ADIM=%d SLUG=%d VARLIK=%d DOSYA=%d"
          % (adim_sayisi, slug_sayisi, varlik_sayisi, len(ozet)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
