#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAYIN IC-DIL KAPISI — tarayiciya inen KOD METNINDE ic gelistirici dili aramaz-olsun.

NEYI KORUR (olculmus sessiz hata, 31 Tem 2026):
  Katalog metninde (urunler.json) uretim-sureci dilini denetim-kapisi yasakliyordu; ayni
  dil sitenin KENDI kodunun YORUMLARINDA serbestce duruyordu ve o yorumlar tarayiciya
  INIYORDU. Olculdu (yayin ciktisinin tamami, build.py sonrasi): 209 TEKIL yorum yerinde
  yasakli dil vardi — 'filament', '.scad'/'OpenSCAD', 'STL', 'brim'; ayrica IC DOSYA YOLU
  (tools/*.py, shop/src/*.js, onizleme/..., jenerator/test/...) ve ISLETME SAHIBININ ADI
  ticari kararlarla birlikte ("KARGO (<ad>, 16 Tem — KESIN)", "+75 TL tahsilati durduruldu").
  Sayfa kaynagina bakan HERKES goruyordu; hicbir kapi bakmadigi icin aylarca kaldi.
  Ayrica bir canli dogrulama olcumu bu yuzden YANLISLIKLA kirmizi yandi (<style> blogu
  ayiklanmayinca 'filament' esletti) — yani kirlilik OLCUMU de bozuyordu.

IDDIA (bloklayici): YAYIN BEYAZ LISTESINDEKI her .html/.js dosyasinin YORUM YUZEYINDE
  (HTML yorumu + <style> icindeki CSS yorumu + JS yorumlari) yasakli dil vurusu = 0.

IDDIA 2 (bloklayici, HIZALAMA): olculen bayt = YAYINLANAN bayt. JS varliklarinin
  yayin kopyasi build.py tarafindan _yayin/'a yazilir (yorumu soyulmus) ve deploy.yml
  _site'a ORADAN kopyalar; bu kapi da _yayin/'i olcer. deploy.yml sessizce kaynaktan
  kopyalamaya donerse tarayiciya YORUMLU dosya iner ama kapi soyulmus kopyayi olcup
  YESIL yanardi -> soyma da kapi da OLU. Hizalama kontrolu bunu KIRMIZI yakar.

NEDEN "YORUM YUZEYI" (eksen secimi — olculmus gerekce):
  * VERI BAGISIKLIGI: urun metni sayfaya DIZGE/OBJE literali olarak girer, YORUM olarak
    ASLA. Yorumla sinirlamak, kapiyi katalog ekseninden (denetim-kapisi) tamamen ayirir:
    ayni ihlal iki kapida birden yanmaz, ve katalogdaki mesru bir kelime ("Nozul Tutucu"
    urun adi) bu kapiyi KIRMIZI yakamaz. Olculdu: yorum-disi taransaydi yayin ciktisinda
    30.889 vurus cikardi ve hepsi urun verisiydi.
  * TANIMLAYICI/CALISMA-ZAMANI DIZGESI KAPSAM DISI (bilincli, KAYITLI): FILAMENT_FARK
    (shop Worker'inin import ettigi PUBLIC API adi), stlCoz, "stl-binary-degil" gibi
    tanimlayicilar ve hata dizgeleri KOD'dur, prose degil; yeniden adlandirmak odeme
    yolundaki Worker'i da degistirmeyi gerektirir (ayri deploy). Bu kapi onlari GORMEZ.
    Kalan ifsa: /filament-veri.js yayin dosyasinin ADI + yuku. 🔴 GUNCELLEME (11 Agu
    2026): "bugun HICBIR sayfa onu yuklemiyor" beyani ARTIK GECERSIZ — ana sayfa dosyayi
    YENIDEN yukluyor (onden secili malzemeye gore ilan edilen kart tutari o referanstan
    turer). Yani ifsa yuzeyi buyudu, bu kapinin kapsami DEGISMEDI. Bu ayri bir is;
    kapinin kapsaminda OLMADIGI burada ACIKCA yazilidir ki "kapi yesil = her sey
    temiz" sanilmasin.

SOZLUK TEK KAYNAK: uretim-sureci kovalari tools/denetim-kapisi.py `_IFSA_SERT_RE`'den
  IMPORT edilir — ikinci kopya YOK. Katalogda yasak olan dil burada da yasaktir; kural
  degisirse iki kapi BIRLIKTE degisir (uydurulmus ikinci sozluk yok).

KAPSAM (fail-closed): yayin beyaz listesi .github/workflows/deploy.yml'dekiyle AYNI kume.
  index.built.html · urun/*/index.html · <icerik dizinleri>/index.html · secenekler.js ·
  konfigur.js · filament-veri.js · taban-fiyatlar.js · jenerator/{hacim,konfigurator,viewer}.js
  TABAN KUME kontrolu: index.built.html + en az 100 urun sayfasi + 3 JS varlik BULUNMAK
  ZORUNDA; bulunamazsa OLCULEMEDI (cikis 3) — sessiz "0 vurus" YESIL'i imkansizdir.
  Veri dosyalari (urunler.json/merchant-feed.xml/sitemap.xml/ozet.json) YORUM TASIYAMAZ,
  bu yuzden ayrica muaf yazilmasina gerek YOKTUR (eksen zaten disliyor).

KAYNAK KOLU (--kaynak) — NEDEN VAR (olculmus regresyon, 31 Tem 2026):
  Bu kapi YAYIN ciktisini olcer ve o cikti ancak build.py'den SONRA vardir. Sonucu:
  tarayiciya AYNEN inen bir KAYNAK dosyaya (index.html satir-ici <script> yorumu) ic
  dosya yolu yazan bir degisiklik dalda hicbir yerde kirmizi yanmadi, main'e girdi ve
  CI'yi ~4 dakika sonra dusurdu -> deploy + yayin SKIPPED, yayin durdu.
  `--kaynak` AYNI sozlugu ve AYNI yorum lexer'ini, build GEREKTIRMEDEN, tarayiciya
  AYNEN giden KAYNAK dosyalara uygular (index.html + yayinlanan JS varliklari).
  Ikinci sozluk/ikinci lexer YOKTUR — yalniz kapsam degisir; iki kol ayrisamaz.
  Bu kol yayin kolunun YERINE GECMEZ: uretilen urun/icerik sayfalari yalniz yayin
  kolunda olculur (build.py sablonlarindan dogarlar).

Kullanim:
    python3 tools/yayin-ic-dil-kapisi.py            # olcum (build.py'den SONRA; bloklayici)
    python3 tools/yayin-ic-dil-kapisi.py --kaynak   # KAYNAK kolu (build GEREKMEZ; bloklayici)
    python3 tools/yayin-ic-dil-kapisi.py --kendini-test    # ic nobetci (build GEREKMEZ)

Cikis kodu: 0 = temiz · 1 = IHLAL · 3 = OLCULEMEDI (kapsam bulunamadi / sozluk yuklenemedi).
"""
import argparse
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")

# --------------------------------------------------------------------------- sozluk
def _denetim_sozlugu():
    """denetim-kapisi.py'den uretim-sureci desenlerini + tr_lower'i alir (TEK KAYNAK)."""
    import importlib.util
    yol = os.path.join(TOOLS, "denetim-kapisi.py")
    spec = importlib.util.spec_from_file_location("_dk_sozluk", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # ⚠️ INDISLE OKU, SABIT-UZUNLUKTA ACMA: `_IFSA_SERT_RE` girisleri 31 Tem'de
    #   (ad, rx, gerekce) -> (ad, rx, gerekce, eleme) oldu. Sabit-uzunluk acma o gun
    #   bu kapiyi ValueError ile OLCULEMEDI'ye dusururdu (sozluk TEK KAYNAK oldugu icin
    #   komsu kapinin sema degisikligi buraya sizar). Indisle okuma ileri-uyumludur.
    return [(t[0], t[1]) for t in mod._IFSA_SERT_RE], mod.tr_lower


# IC GELISTIRICI DILI — bu kapiya OZGU kovalar (katalog metninde anlamsiz oldugu icin
# denetim-kapisi'nda yoklar). Her desenin YANINDA olculmus yanlis-pozitif nobeti vardir.
#
# ⚠️ (?<![/\w]) ZORUNLU: 'onizleme/' gibi bir dizin adi PUBLIC bir API yolunun ICINDE de
#    gecer ("/api/onizleme/olustur" — musteriye acik uc, ifsa DEGIL). Lookbehind olmadan
#    olculdu: 2 YANLIS-POZITIF. Bir '/' ya da harf ONCESINDE geliyorsa ic yol SAYILMAZ.
# ⚠️ Uzanti listesine ".js" GIRMEZ: secenekler.js/konfigur.js/hacim.js YAYINLANAN dosya
#    adlaridir, ic yol degil. Yalniz YAYINLANMAYAN uzantilar (py/scad/mjs/toml/yml/cjs).
# ⚠️ 'kabul testi'/'mutasyon'/'fikstur'/'NOBETCI' KOVA DEGIL: bunlar genel muhendislik
#    sozcugudur, ifsa degil. Kova yapilsaydi kapi, deponun "her kuralin yanina nobetcisini
#    yaz" kulturunu bloklardi (olculdu: 9 mesru yorum satiri kirmizi yanardi).
_IC_DIL = (
    ("ic-dosya-yolu",
     r"(?<![/\w])(?:tools|shop/src|shop/test|worker/src|olcum|onizleme|jenerator/test|\.github|\.claude)"
     r"/[A-Za-z0-9_./-]+"
     r"|/Users/[A-Za-z0-9_.-]+"
     r"|pruvo-(?:jenerator|bot|pazarlama|hasat)\b"
     r"|[A-Za-z0-9_-]+\.(?:py|scad|mjs|toml|yml|cjs)\b",
     "ic arac/test/dosya yolu — 2026-07-15 denetiminde tools/*.py YAYINDAN cikarilmisti; "
     "adini yorumda yazmak ayni envanteri geri sizdirir"),
    ("gelistirici-notu",
     r"\bTODO\b|\bFIXME\b|\bHACK\b|\bXXX\b",
     "yarim is isareti — musteri sayfasinda 'burasi eksik' beyani"),
    ("ic-sahis-adi",
     r"\bokan\b|\bkral\b|\bmacit\b|\bkaan\b|\bartist\b|\bhoca\b",
     "isletme sahibinin/ic ajan adlarinin TICARI KARARLARLA birlikte yayinlanmasi"),
)


# ------------------------------------------------------------------- yorum ayiklayici
def js_yorumlari(kaynak):
    """(offset, govde) — JS kaynagindaki // ve /* */ yorumlari.

    Dizge ('"`), sablon ve REGEX literalleri atlanir: icinde '//' gecen bir dizge
    yorum SANILMAZ (yanlis-pozitif) ve icinde '/*' gecen bir regex kapiyi CILDIRTMAZ.
    """
    out = []
    i, n = 0, len(kaynak)
    onceki = ""                       # son anlamli karakter (regex literal ayrimi)
    while i < n:
        c = kaynak[i]
        ikili = kaynak[i:i + 2]
        if ikili == "//":
            j = kaynak.find("\n", i)
            j = n if j < 0 else j
            out.append((i, kaynak[i + 2:j]))
            i = j
            continue
        if ikili == "/*":
            j = kaynak.find("*/", i + 2)
            j = n if j < 0 else j
            out.append((i, kaynak[i + 2:j]))
            i = j + 2
            continue
        if c in "\"'`":
            q = c
            i += 1
            while i < n:
                if kaynak[i] == "\\":
                    i += 2
                    continue
                if kaynak[i] == q:
                    i += 1
                    break
                i += 1
            onceki = q
            continue
        if c == "/" and onceki in "(,=:[!&|?{};+-*%~^<>":
            i += 1
            sinif = False
            while i < n:
                if kaynak[i] == "\\":
                    i += 2
                    continue
                if kaynak[i] == "[":
                    sinif = True
                elif kaynak[i] == "]":
                    sinif = False
                elif kaynak[i] == "/" and not sinif:
                    i += 1
                    break
                elif kaynak[i] == "\n":
                    break
                i += 1
            onceki = "/"
            continue
        if not c.isspace():
            onceki = c
        i += 1
    return out


_CSS_YORUM = re.compile(r"/\*(.*?)\*/", re.S)
_STYLE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S | re.I)
_SCRIPT = re.compile(r"<script\b[^>]*>(.*?)</script>", re.S | re.I)
_HTML_YORUM = re.compile(r"<!--(.*?)-->", re.S)


def html_yorumlari(kaynak):
    """(sinif, offset, govde) — HTML yorumu + <style> icindeki CSS yorumu + <script>
    icindeki JS yorumu. Urun VERISI (dizge/obje literali) HICBIRINE girmez."""
    out = []
    for m in _HTML_YORUM.finditer(kaynak):
        out.append(("html-yorum", m.start(), m.group(1)))
    for m in _STYLE.finditer(kaynak):
        taban = m.start(1)
        for mm in _CSS_YORUM.finditer(m.group(1)):
            out.append(("css-yorum", taban + mm.start(), mm.group(1)))
    for m in _SCRIPT.finditer(kaynak):
        taban = m.start(1)
        for off, t in js_yorumlari(m.group(1)):
            out.append(("js-yorum", taban + off, t))
    return out


def dosya_yorumlari(yol, metin):
    if yol.endswith(".js"):
        return [("js-yorum", o, t) for o, t in js_yorumlari(metin)]
    if yol.endswith(".css"):
        return [("css-yorum", m.start(), m.group(1)) for m in _CSS_YORUM.finditer(metin)]
    return html_yorumlari(metin)


# ------------------------------------------------------------------------- kapsam
SABIT_VARLIKLAR = ("index.built.html", "secenekler.js", "konfigur.js",
                   "filament-veri.js", "taban-fiyatlar.js",
                   "jenerator/hacim.js", "jenerator/konfigurator.js", "jenerator/viewer.js")
TABAN_JS = ("secenekler.js", "konfigur.js", "jenerator/hacim.js")
EN_AZ_URUN = 100
# JS varliklarinin YAYINLANAN kopyasi build.py tarafindan buraya yazilir (yorumu
# soyulmus). deploy.yml _site'a BURADAN kopyalar -> kapi da BURAYI olcmeli, yoksa
# tarayiciya inmeyen KAYNAK dosyayi olcup yanlis yerde kirmizi/yesil yanar.
YAYIN_DIR = "_yayin"
# Yorumu SOYULMAYAN, bilerek kapsam disi yuzey: elle yazilmis 4 statik yasal sayfa
# (hakkimizda/iletisim/sss/gizlilik). Onlar commit'li kaynaktir
# (tools/yasal-sayfa-drift-kapisi.py bayt-esitlik ister), build.py'nin yayin_html()
# donusumunden GECMEZ — ama BU kapinin kapsamindan CIKMAZLAR: ic-dil ekseni onlarda da
# olculur (soyulmadiklari icin yorumlari yayina AYNEN iner).


def _yayin_kopyasi(kok, rel):
    """(olculecek_yol, soyulmus_mu) — _yayin/<rel> varsa YAYINLANAN kopya odur."""
    y = os.path.join(YAYIN_DIR, rel)
    if os.path.exists(os.path.join(kok, y)):
        return y, True
    return rel, False


# ------------------------------------------------- OLCUM HEDEFI = YAYINLANAN BAYT
# 🔴 IKI KORUMA BIRBIRINI OLU BIRAKMASIN. Bu kapi JS varliklarini _yayin/<rel>'den
# olcer; o dosyalarin GERCEKTEN yayinlanan baytlar olmasi deploy.yml'in onlari
# _site'a _yayin/'DAN kopyalamasina baglidir. deploy.yml sessizce kaynaktan
# kopyalamaya donerse: tarayiciya YORUMLU dosya iner, bu kapi ise soyulmus kopyayi
# olcup YESIL yanar — yani soyma da kapi da olur. Asagidaki hizalama kontrolu o
# sessiz hatayi BLOKLAYICI yapar: beyaz listedeki her JS icin deploy.yml'de
# `_yayin/<rel>` kopyasi ZORUNLU, ciplak `<rel>` kopyasi YASAK.
_CP_SATIRI = re.compile(r"^\s*cp\s+(?P<govde>.+)$", re.M)


def deploy_kopya_jetonlari(yml_metni):
    """deploy.yml'deki `cp ...` satirlarinin KAYNAK jetonlari (hedef haric)."""
    jetonlar = set()
    for m in _CP_SATIRI.finditer(yml_metni or ""):
        parcalar = m.group("govde").split()
        if len(parcalar) < 2:
            continue
        for p in parcalar[:-1]:                     # son jeton = HEDEF
            if not p.startswith("-"):               # -r gibi secenekler haric
                jetonlar.add(p)
    return jetonlar


def hizalama_ihlalleri(yml_metni):
    """[(rel, sebep)] — olculen bayt ile YAYINLANAN bayt ayrisiyorsa dolu doner."""
    jetonlar = deploy_kopya_jetonlari(yml_metni)
    ihlaller = []
    for rel in SABIT_VARLIKLAR:
        if not rel.endswith(".js"):
            continue                                # index.built.html zaten build urunu
        if rel in jetonlar:
            ihlaller.append((rel, "deploy.yml KAYNAKTAN kopyaliyor (yorumlu bayt yayinlanir)"))
        elif (YAYIN_DIR + "/" + rel) not in jetonlar:
            ihlaller.append((rel, "deploy.yml _yayin/%s kopyasini HIC kopyalamiyor" % rel))
    return ihlaller


def kapsam(kok):
    """(dosyalar, eksik) — yayin beyaz listesindeki .html/.js yollari.
    `dosyalar` deploy'un _site'a KOYDUGU baytlari gosterir (JS icin _yayin/<rel>)."""
    dosyalar, eksik = [], []
    for rel in SABIT_VARLIKLAR:
        yol, _soyuldu = _yayin_kopyasi(kok, rel)
        if os.path.exists(os.path.join(kok, yol)):
            dosyalar.append(yol)
        elif rel in TABAN_JS or rel == "index.built.html":
            eksik.append(rel)
    idx = os.path.join(kok, "_yayin-icerik-dizinleri.txt")
    if os.path.exists(idx):
        for s in io.open(idx, encoding="utf-8").read().split():
            p = os.path.join(s, "index.html")
            if os.path.exists(os.path.join(kok, p)):
                dosyalar.append(p)
    # SAYFA VARLIKLARI (/varlik/*.css, *.js) — build.py'nin ayirdigi ortak CSS/JS.
    # 2 Agu'da yeni bir YAYIN YUZEYI oldular: eskiden bu baytlar urun sayfasinin
    # <style>/<script> govdesindeydi ve BU kapinin kapsamindaydi. Blok sayfadan cikip
    # kendi dosyasina tasinirken kapsam da tasinmazsa ic-dil olcumu SESSIZCE korelir
    # (olculen yuzey kucuulur, kapi yine yesil yanar) -> burada acikca eklenir.
    varlik_kok = os.path.join(kok, "varlik")
    if os.path.isdir(varlik_kok):
        for a in sorted(os.listdir(varlik_kok)):
            if a.endswith(".css") or a.endswith(".js"):
                dosyalar.append(os.path.join("varlik", a))

    urun_kok = os.path.join(kok, "urun")
    urun_sayisi = 0
    if os.path.isdir(urun_kok):
        for u in sorted(os.listdir(urun_kok)):
            p = os.path.join("urun", u, "index.html")
            if os.path.exists(os.path.join(kok, p)):
                dosyalar.append(p)
                urun_sayisi += 1
    if urun_sayisi < EN_AZ_URUN:
        eksik.append("urun/*/index.html (%d < %d — build.py kosmadi mi?)" % (urun_sayisi, EN_AZ_URUN))
    return dosyalar, eksik


# KAYNAK kolu: tarayiciya AYNEN inen kaynak dosyalar (index.html -> index.built.html'in
# govdesi; JS varliklari _site'a aynen kopyalanir). build.py GEREKMEZ.
KAYNAK_VARLIKLAR = ("index.html",) + tuple(r for r in SABIT_VARLIKLAR if r != "index.built.html")
KAYNAK_TABAN = ("index.html",) + TABAN_JS


def kaynak_kapsam(kok):
    """(dosyalar, eksik) — build GEREKTIRMEYEN kaynak yuzeyi. TABAN kume yoksa OLCULEMEDI:
    bos kumede 'vurus 0' YESIL'i imkansiz olsun."""
    dosyalar, eksik = [], []
    for rel in KAYNAK_VARLIKLAR:
        if os.path.exists(os.path.join(kok, rel)):
            dosyalar.append(rel)
        elif rel in KAYNAK_TABAN:
            eksik.append(rel)
    return dosyalar, eksik


# -------------------------------------------------------------------------- olcum
def desenleri_derle():
    sert, tr_lower = _denetim_sozlugu()
    ic = [(ad, re.compile(d, re.UNICODE), g) for ad, d, g in _IC_DIL]
    return sert, ic, tr_lower


def tara(metin, yol, sert, ic, tr_lower):
    """[(kova, sinif, ifade, baglam)] — bu dosyanin yorum yuzeyindeki vuruslar."""
    bulgu = []
    for sinif, off, govde in dosya_yorumlari(yol, metin):
        kucuk = tr_lower(govde)
        for kova, rx in sert:
            for m in rx.finditer(kucuk):
                bulgu.append((kova, sinif, m.group(0),
                              govde[max(0, m.start() - 50):m.end() + 50].replace("\n", " ")))
        for kova, rx, _g in ic:
            for hedef in (kucuk, govde):
                for m in rx.finditer(hedef):
                    bulgu.append((kova, sinif, m.group(0),
                                  govde[max(0, m.start() - 50):m.end() + 50].replace("\n", " ")))
    return bulgu


DEPLOY_YML = os.path.join(ROOT, ".github", "workflows", "deploy.yml")


def olc(kok, ayrintili=True, yml_metni=None, kapsam_fn=None, etiket="yayin"):
    """(cikis_kodu, satirlar). kapsam_fn: yayin kolu `kapsam`, kaynak kolu `kaynak_kapsam`
    — sozluk ve yorum lexer'i IKI KOLDA DA AYNI, yalniz dosya kumesi degisir.

    HIZALAMA KAPISI yalniz YAYIN kolunda kosar: iddiasi "bu kapinin OLCTUGU _yayin/
    baytlari ile deploy.yml'in YAYINLADIGI baytlar ayni" — KAYNAK kolu tanimi geregi
    kaynak dosyalari olcer, o iddia oraya uygulanamaz. Yayin kolunda AYNEN duruyor."""
    R = []
    kapsam_fn = kapsam_fn or kapsam
    try:
        sert, ic, tr_lower = desenleri_derle()
    except Exception as e:                                     # noqa: BLE001
        return 3, ["OLCULEMEDI: sozluk (denetim-kapisi.py) yuklenemedi -> %s" % e]

    if etiket == "yayin":
        if yml_metni is None:
            try:
                yml_metni = io.open(DEPLOY_YML, encoding="utf-8").read()
            except OSError as e:
                return 3, ["OLCULEMEDI: deploy.yml okunamadi -> %s" % e,
                           "  (olculen bayt ile YAYINLANAN bayt hizasi dogrulanamaz)"]
        kaymalar = hizalama_ihlalleri(yml_metni)
        if kaymalar:
            R.append("IHLAL: OLCUM HEDEFI SAPMASI — bu kapi _yayin/ kopyasini olcerken "
                     "deploy.yml baska baytlari yayinliyor (%d varlik)" % len(kaymalar))
            for rel, sebep in kaymalar:
                R.append("  %s  -> %s" % (rel, sebep))
            R.append("COZUM: deploy.yml'de _site'a JS varliklari _yayin/<rel>'den kopyalanmali "
                     "(build.py o kopyalari uretir; uretemezse zaten exit 1).")
            return 1, R

    dosyalar, eksik = kapsam_fn(kok)
    if eksik:
        return 3, ["OLCULEMEDI: %s kapsami eksik -> %s" % (etiket, ", ".join(eksik)),
                   "  (yayin kolu build.py'den SONRA kosar; urun/ + index.built.html sart)"]

    R.append("Kapsam: %d %s dosyasi (%d desen kovasi)" % (len(dosyalar), etiket,
                                                          len(sert) + len(ic)))
    toplam = 0
    dosya_basi = []
    for rel in dosyalar:
        p = os.path.join(kok, rel)
        try:
            metin = io.open(p, encoding="utf-8", errors="strict").read()
        except (OSError, UnicodeDecodeError) as e:
            return 3, ["OLCULEMEDI: %s okunamadi -> %s" % (rel, e)]
        bulgu = tara(metin, rel, sert, ic, tr_lower)
        if bulgu:
            toplam += len(bulgu)
            dosya_basi.append((rel, bulgu))

    if not dosya_basi:
        R.append("TEMIZ: %s yorum yuzeyinde yasakli dil vurusu 0" % etiket)
        return 0, R

    R.append("IHLAL: %d vurus / %d dosya" % (toplam, len(dosya_basi)))
    for rel, bulgu in dosya_basi[:40]:
        R.append("  %s  (%d)" % (rel, len(bulgu)))
        if ayrintili:
            for kova, sinif, ifade, baglam in bulgu[:6]:
                R.append("      [%s|%s] %r  ...%s..." % (kova, sinif, ifade, baglam[:150]))
    if len(dosya_basi) > 40:
        R.append("  ... +%d dosya daha" % (len(dosya_basi) - 40))
    R.append("COZUM: yorumu SIL ya da ic dil tasimayan bir ifadeyle DEGISTIR.")
    return 1, R


# --------------------------------------------------------------------- kendini test
_IDDIA = []


def _iddia(ad, kosul, ek=""):
    _IDDIA.append((ad, bool(kosul), ek))


def _sahte_agac(kok, urun_govdesi, varlik_govdesi="", icerik_govdesi=None,
                ana_govdesi=None):
    """Kapsam TABAN KUMESINI saglayan sentetik bir yayin agaci kurar.

    Her yayin YUZEYI ayri parametreyle beslenir (urun sayfasi / JS varlik / icerik
    sayfasi / ana sayfa): boylece 'sadece urun sayfasina bakan' bir kapi mutasyonu
    fikstur tarafindan SAG BIRAKILAMAZ."""
    os.makedirs(kok, exist_ok=True)
    io.open(os.path.join(kok, "index.built.html"), "w", encoding="utf-8").write(
        ana_govdesi or "<html><head><style>/* kart duzeni */</style></head><body>x</body></html>")
    os.makedirs(os.path.join(kok, "jenerator"), exist_ok=True)
    for rel in ("secenekler.js", "konfigur.js", "jenerator/hacim.js"):
        io.open(os.path.join(kok, rel), "w", encoding="utf-8").write(
            "/* PRUVO modul */\n" + varlik_govdesi + "\nvar a = 1;\n")
    # icerik (yasal/SEO) sayfalari — deploy.yml bunlari _yayin-icerik-dizinleri.txt'ten kopyalar
    io.open(os.path.join(kok, "_yayin-icerik-dizinleri.txt"), "w", encoding="utf-8").write(
        "gizlilik\nmalzeme-rehberi\n")
    for s in ("gizlilik", "malzeme-rehberi"):
        d = os.path.join(kok, s)
        os.makedirs(d, exist_ok=True)
        io.open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(
            icerik_govdesi or "<html><body><!-- yasal sayfa --></body></html>")
    for i in range(EN_AZ_URUN + 5):
        d = os.path.join(kok, "urun", "u%03d" % i)
        os.makedirs(d, exist_ok=True)
        io.open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(urun_govdesi)


def kendini_test():
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="yid-nobet-")
    try:
        # ---------------- NEGATIF (kanarya): temiz agac YESIL olmali -----------------
        temiz_urun = (
            "<html><head><style>/* kart duzeni: sepet paneli ustte kalir */</style></head>"
            "<body><!-- vitrin karti -->"
            "<script>\n"
            "  /* Malzeme bolumu: sitede satilan malzeme cipleri + tavsiye rozeti. */\n"
            "  var URUN = {\"baslik\":\"Nozul Tutucu Braketi\","
            "\"aciklama\":\"PETG malzemededir. 3D baski tablasi icin nozul capi 0.4 mm.\"};\n"
            "  var yol = \"https://pruvo3d.com/api/onizleme/olustur\";  // public uc\n"
            "  var re1 = /http:\\/\\/eski/;  // regex icinde // var\n"
            "  var s = \"bu bir // yorum DEGIL, dizge\";\n"
            "  var t = `sablon icinde /* yorum gibi */ metin`;\n"
            "</script></body></html>")
        # Temiz agacta HER YUZEYDE mesru-ama-benzer metin bulunur: public API yolu ve
        # YAYINLANAN dosya adi YORUM ICINDE gecer (bunlar ifsa DEGIL). Boylece
        # lookbehind'i / uzanti listesini gevseten bir mutasyon fikstur tarafindan
        # yakalanabilir hale gelir.
        temiz_icerik = ("<html><head><style>/* malzeme bolumu: cip satiri + rozet */</style>"
                        "</head><body><!-- yasal sayfa: kunye blogu -->"
                        "<script>/* onizleme ucu: /api/onizleme/olustur — public */\n"
                        "/* tek kaynak: secenekler.js + konfigur.js */</script></body></html>")
        temiz_ana = ("<html><head><style>/* kart duzeni: sepet paneli ustte */</style></head>"
                     "<body><!-- vitrin: kategori seridi --><script>"
                     "/* fiyat: secenekler.js hesaplar */</script></body></html>")
        kok = os.path.join(tmp, "temiz")
        _sahte_agac(kok, temiz_urun, icerik_govdesi=temiz_icerik, ana_govdesi=temiz_ana)
        kod, satirlar = olc(kok, ayrintili=False)
        _iddia("K1 TEMIZ agac YESIL (urun VERISI + public API yolu + yayinlanan .js adi + "
               "dizge/regex/sablon icindeki yorum-benzeri metin vurmaz)",
               kod == 0, "kod=%d %s" % (kod, satirlar[-1:]))

        # ---------------- POZITIF: her kova x her YUZEY ayri ayri KIRMIZI ------------
        pozitifler = [
            ("filament", "renk cipi: filament katsayisi burada uygulanir"),
            ("dosya-ifsasi", "govde ayni .scad dosyasindan surulur"),
            ("makine-parametresi", "kenar: brim payi eklenir"),
            ("ic-dosya-yolu", "TEK KAYNAK: tools/build.py feed_id"),
            # AYNI KOVANIN AYRI KOLLARI (biri otekini maskelemesin — olculdu: yalniz
            # 'tools/build.py' fikstur olsaydi 'dizin yolu kolu' mutasyonu SAG KALIRDI,
            # cunku o metin UZANTI kolundan da eslesiyor):
            ("ic-dosya-yolu/dizin", "Worker kolu: shop/src/index.js icinde"),
            ("ic-dosya-yolu/test-dizini", "esleme: jenerator/test/esleme/cerceve.json"),
            ("ic-dosya-yolu/mutlak", "yerel kok: /Users/okan/dev/pruvo"),
            ("ic-dosya-yolu/kardes-depo", "ayri repo: pruvo-bot deposunda"),
            ("ic-sahis-adi", "KARGO (Okan, 16 Tem — KESIN): 250 TL"),
            ("gelistirici-notu", "TODO: bu blok yeniden yazilacak"),
        ]
        for ad, govde in pozitifler:
            js_yorum = "  /* " + govde + " */"
            html_yorum = "<!-- " + govde + " -->"
            css_yorum = "/* " + govde + " */"
            # (a) urun sayfasi <script> yorumu
            k = os.path.join(tmp, "poz-js-" + ad)
            _sahte_agac(k, temiz_urun.replace("<script>\n", "<script>\n" + js_yorum + "\n"),
                        icerik_govdesi=temiz_icerik, ana_govdesi=temiz_ana)
            _iddia("P/%s urun <script> yorumu KIRMIZI" % ad, olc(k, ayrintili=False)[0] == 1)
            # (b) urun sayfasi HTML yorumu
            k = os.path.join(tmp, "poz-html-" + ad)
            _sahte_agac(k, temiz_urun.replace("<body>", "<body>" + html_yorum),
                        icerik_govdesi=temiz_icerik, ana_govdesi=temiz_ana)
            _iddia("P/%s urun HTML yorumu KIRMIZI" % ad, olc(k, ayrintili=False)[0] == 1)
            # (c) urun sayfasi <style> icindeki CSS yorumu
            k = os.path.join(tmp, "poz-css-" + ad)
            _sahte_agac(k, temiz_urun.replace("<style>", "<style>" + css_yorum),
                        icerik_govdesi=temiz_icerik, ana_govdesi=temiz_ana)
            _iddia("P/%s urun CSS yorumu KIRMIZI" % ad, olc(k, ayrintili=False)[0] == 1)
            # (d) JS varlik yorumu
            k = os.path.join(tmp, "poz-varlik-" + ad)
            _sahte_agac(k, temiz_urun, varlik_govdesi=js_yorum,
                        icerik_govdesi=temiz_icerik, ana_govdesi=temiz_ana)
            _iddia("P/%s JS VARLIK yorumu KIRMIZI" % ad, olc(k, ayrintili=False)[0] == 1)
            # (e) ICERIK (yasal/SEO) sayfasi yorumu
            k = os.path.join(tmp, "poz-icerik-" + ad)
            _sahte_agac(k, temiz_urun, icerik_govdesi=temiz_icerik.replace("<body>", "<body>" + html_yorum),
                        ana_govdesi=temiz_ana)
            _iddia("P/%s ICERIK sayfasi yorumu KIRMIZI" % ad, olc(k, ayrintili=False)[0] == 1)
            # (f) ANA SAYFA yayin kopyasi yorumu
            k = os.path.join(tmp, "poz-ana-" + ad)
            _sahte_agac(k, temiz_urun, icerik_govdesi=temiz_icerik,
                        ana_govdesi=temiz_ana.replace("<body>", "<body>" + html_yorum))
            _iddia("P/%s ANA SAYFA yorumu KIRMIZI" % ad, olc(k, ayrintili=False)[0] == 1)

        # ------------- KANARYA: ihlal YORUM DISINDA ise (tanimlayici/dizge) YESIL ----
        kanaryalar = [
            ("tanimlayici", "  var FILAMENT_FARK = { \"PLA\": 0 };"),
            ("hata-dizgesi", "  throw new Error(\"stl-binary-degil\");"),
            ("public-api", "  var u = \"/api/onizleme/olustur\";"),
            ("urun-adi-dizgesi", "  var b = \"Nozul Tutucu\";"),
        ]
        for ad, kod_satiri in kanaryalar:
            k = os.path.join(tmp, "kan-" + ad)
            _sahte_agac(k, temiz_urun, varlik_govdesi=kod_satiri,
                        icerik_govdesi=temiz_icerik, ana_govdesi=temiz_ana)
            kod, _s = olc(k, ayrintili=False)
            _iddia("K/%s yorum DISI -> YESIL (tanimlayici/dizge ekseni bu kapida DEGIL)" % ad,
                   kod == 0, "kod=%d" % kod)

        # MESRU-AMA-BENZER metin YORUM ICINDE de YESIL kalmali (gevsetme degil, AYRIM):
        for ad, yorum in (("public-api-yolu", "  /* uc: /api/onizleme/olustur (musteriye acik) */"),
                          ("yayinlanan-js-adi", "  /* fiyat: secenekler.js + konfigur.js ortak */"),
                          ("yayinlanan-jenerator-js", "  /* hacim: jenerator/hacim.js kapali-formu */")):
            k = os.path.join(tmp, "kanyorum-" + ad)
            _sahte_agac(k, temiz_urun, varlik_govdesi=yorum,
                        icerik_govdesi=temiz_icerik, ana_govdesi=temiz_ana)
            kod, _s = olc(k, ayrintili=False)
            _iddia("K/%s YORUM icinde bile YESIL (public yuzey ic yol DEGIL)" % ad,
                   kod == 0, "kod=%d" % kod)

        # ---------------- OLCULEMEDI kollari (fail-closed) ---------------------------
        k = os.path.join(tmp, "bos")
        os.makedirs(k, exist_ok=True)
        kod, _s = olc(k, ayrintili=False)
        _iddia("O1 BOS agac -> OLCULEMEDI (sessiz YESIL degil)", kod == 3, "kod=%d" % kod)

        k = os.path.join(tmp, "azurun")
        _sahte_agac(k, temiz_urun)
        import shutil as _sh
        for i in range(EN_AZ_URUN + 5):
            _sh.rmtree(os.path.join(k, "urun", "u%03d" % i))
        kod, _s = olc(k, ayrintili=False)
        _iddia("O2 urun/ BOS -> OLCULEMEDI (build.py kosmadan YESIL yanamaz)", kod == 3,
               "kod=%d" % kod)

        k = os.path.join(tmp, "eksikjs")
        _sahte_agac(k, temiz_urun)
        os.remove(os.path.join(k, "secenekler.js"))
        kod, _s = olc(k, ayrintili=False)
        _iddia("O3 TABAN JS varligi eksik -> OLCULEMEDI", kod == 3, "kod=%d" % kod)

        # ---------------- KAYNAK KOLU (--kaynak): build GEREKTIRMEYEN yuzey ----------
        # Regresyonun kendisi: index.html'in satir-ici <script> yorumuna ic dosya yolu
        # yazildi, dalda hicbir kapi yanmadi, main'de CI ~4 dk sonra dustu (yayin durdu).
        def _kaynak_agac(kok, index_govdesi, varlik_govdesi="/* PRUVO modul */\nvar a=1;\n"):
            os.makedirs(kok, exist_ok=True)
            os.makedirs(os.path.join(kok, "jenerator"), exist_ok=True)
            io.open(os.path.join(kok, "index.html"), "w", encoding="utf-8").write(index_govdesi)
            for rel in TABAN_JS:
                io.open(os.path.join(kok, rel), "w", encoding="utf-8").write(varlik_govdesi)

        temiz_index = (
            "<html><head><style>/* kart duzeni: sepet paneli ustte */</style></head><body>"
            "<script>\n"
            "  /* Ustu cizili fiyat: KALIP derleyici tarafiyla AYNI; kabul testinde kilitli. */\n"
            "  var s = \"tools/build.py\";  /* dizge DEGIL yorum degil: bu yorumda yol YOK */\n"
            "</script></body></html>")
        k = os.path.join(tmp, "kaynak-temiz")
        _kaynak_agac(k, temiz_index)
        kod, satirlar = olc(k, ayrintili=False, kapsam_fn=kaynak_kapsam, etiket="kaynak")
        _iddia("KS1 TEMIZ kaynak agaci YESIL (yorumda ic yol yok)", kod == 0,
               "kod=%d %s" % (kod, satirlar[-1:]))

        k = os.path.join(tmp, "kaynak-index-yol")
        _kaynak_agac(k, temiz_index.replace(
            "KALIP derleyici tarafiyla AYNI",
            "KALIP tools/build.py'deki ile AYNI"))
        kod, _s = olc(k, ayrintili=False, kapsam_fn=kaynak_kapsam, etiket="kaynak")
        _iddia("KS2 index.html <script> YORUMUNDA ic dosya yolu -> KIRMIZI (regresyon vakasi)",
               kod == 1, "kod=%d" % kod)

        k = os.path.join(tmp, "kaynak-varlik-yol")
        _kaynak_agac(k, temiz_index, "/* TEK KAYNAK: tools/build.py feed_id */\nvar a=1;\n")
        kod, _s = olc(k, ayrintili=False, kapsam_fn=kaynak_kapsam, etiket="kaynak")
        _iddia("KS3 yayinlanan JS VARLIGI yorumunda ic yol -> KIRMIZI", kod == 1, "kod=%d" % kod)

        k = os.path.join(tmp, "kaynak-dizge")
        _kaynak_agac(k, temiz_index.replace(
            "var s = \"tools/build.py\";",
            "var s = \"tools/build.py\"; var u = \"jenerator/test/x.json\";"))
        kod, _s = olc(k, ayrintili=False, kapsam_fn=kaynak_kapsam, etiket="kaynak")
        _iddia("KS4 yorum DISINDAKI ic yol (dizge) YESIL — eksen yorum yuzeyi", kod == 0,
               "kod=%d" % kod)

        k = os.path.join(tmp, "kaynak-eksik")
        _kaynak_agac(k, temiz_index)
        os.remove(os.path.join(k, "index.html"))
        kod, _s = olc(k, ayrintili=False, kapsam_fn=kaynak_kapsam, etiket="kaynak")
        _iddia("KS5 index.html YOK -> OLCULEMEDI (bos kumede sessiz YESIL imkansiz)",
               kod == 3, "kod=%d" % kod)

        # ---------------- LEXER nobetleri (dogrudan) --------------------------------
        y = js_yorumlari("var s = \"// degil\"; // yorum\n")
        _iddia("L1 dizge icindeki // yorum SAYILMAZ",
               len(y) == 1 and y[0][1].strip() == "yorum", repr(y))
        y = js_yorumlari("var r = /[/*]/; /* gercek */\n")
        _iddia("L2 regex icindeki /* yorum SAYILMAZ",
               len(y) == 1 and y[0][1].strip() == "gercek", repr(y))
        y = js_yorumlari("var t = `a /* b */ c`; // son\n")
        _iddia("L3 sablon icindeki /* */ yorum SAYILMAZ",
               len(y) == 1 and y[0][1].strip() == "son", repr(y))
        y = js_yorumlari("/* bir */ kod // iki\n")
        _iddia("L4 iki yorum bicimi de yakalanir", len(y) == 2, repr(y))

        # ------- HIZALAMA: olculen bayt == YAYINLANAN bayt (iki koruma birbirini
        #         olu birakmasin). Mutasyonlar deploy.yml METNI uzerinde yapilir;
        #         depodaki dosyaya DOKUNULMAZ.
        try:
            gercek_yml = io.open(DEPLOY_YML, encoding="utf-8").read()
        except OSError:
            gercek_yml = ""
        _iddia("H0 gercek deploy.yml HIZALI (JS'ler _yayin/'dan kopyalaniyor)",
               gercek_yml and not hizalama_ihlalleri(gercek_yml),
               repr(hizalama_ihlalleri(gercek_yml))[:200])

        mutant = gercek_yml.replace("_yayin/secenekler.js", "secenekler.js")
        _iddia("H1 MUTANT deploy KAYNAKTAN kopyaliyor -> KIRMIZI",
               any(r == "secenekler.js" for r, _s in hizalama_ihlalleri(mutant)))
        k = os.path.join(tmp, "hizalama-kaynak")
        _sahte_agac(k, temiz_urun, icerik_govdesi=temiz_icerik, ana_govdesi=temiz_ana)
        kod, _s = olc(k, ayrintili=False, yml_metni=mutant)
        _iddia("H2 TEMIZ agac + MUTANT deploy -> yine de KIRMIZI (sessiz yesil YOK)",
               kod == 1, "kod=%d" % kod)

        mutant2 = gercek_yml.replace("_yayin/jenerator/hacim.js ", "")
        _iddia("H3 MUTANT yayin kopyasini HIC kopyalamiyor -> KIRMIZI",
               any(r == "jenerator/hacim.js" for r, _s in hizalama_ihlalleri(mutant2)))
        kod, _s = olc(k, ayrintili=False, yml_metni="")
        _iddia("H4 deploy.yml BOS -> KIRMIZI (hizalama dogrulanamaz)", kod == 1,
               "kod=%d" % kod)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen = sum(1 for _a, k, _e in _IDDIA if k)
    for ad, k, ek in _IDDIA:
        print("  %s %s%s" % ("OK  " if k else "HATA", ad, ("   [%s]" % ek) if not k else ""))
    print("\nkendini-test: %d/%d" % (gecen, len(_IDDIA)))
    return 0 if gecen == len(_IDDIA) else 1


def main():
    ap = argparse.ArgumentParser(description="Yayin ciktisinda ic gelistirici dili kapisi")
    ap.add_argument("--kendini-test", action="store_true")
    ap.add_argument("--kaynak", action="store_true",
                    help="KAYNAK kolu: build GEREKTIRMEDEN tarayiciya AYNEN inen kaynak "
                         "dosyalari (index.html + yayinlanan JS varliklari) olcer")
    ap.add_argument("--kok", default=ROOT, help="olculecek yayin agaci (varsayilan: depo koku)")
    a = ap.parse_args()
    if a.kendini_test:
        return kendini_test()
    if a.kaynak:
        kod, satirlar = olc(a.kok, kapsam_fn=kaynak_kapsam, etiket="kaynak")
    else:
        kod, satirlar = olc(a.kok)
    for s in satirlar:
        print(s)
    return kod


if __name__ == "__main__":
    sys.exit(main())
