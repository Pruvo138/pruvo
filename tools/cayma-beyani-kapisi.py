#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CAYMA BEYANI KAPISI — hazir/stok urun ile ozel uretim ayriminin BEYAN yolunda
(sipariş onay e-postasi · odeme ekrani · teslimat/sozlesme metni · urun sayfasi)
gercekten yasadigini olcer.

NEDEN VAR (olculdu, 1 Agu — SESSIZ HUKUKI KUSUR)
------------------------------------------------
`urunler.json`da 16.589 kayittan 659'u `"tur":"fiziksel"` (+`"stokta":true`) tasir; kalan
15.930'da alan YOKTUR (fail-closed = ozel uretim). Bu alan yalniz PARA yolunu suruyordu
(malzeme/renk carpanini 1,00'e sabitler). HICBIR HUKUKI BEYANI surmuyordu:

  shop/src/eposta.js  siparis onay e-postasi KOSULSUZ
      "Ürünleriniz özel olarak üretilip gönderilecektir."
      havale kolu     "ödemeniz hesabımıza geçtiğinde üretime başlanır."

Sozlesme (tools/sayfalar.py `_mesafeli_satis` §6) "bu urunler siparis sirasinda ACIKCA ozel
uretim olarak TEYIT EDILIR" der. Yani e-posta, 659 HAZIR TICARI MAL siparisinde de o teyidi
veriyordu: musterinin Mesafeli Sozlesmeler Yonetmeligi m.15 disinda kalan 14 GUNLUK CAYMA
HAKKINI reddetmeye yarayacak cumle, siparis aninda yaziliyordu. Kusur TERS YONDE bir
ihlaldir ve SESSIZDIR — site yesil yanar, yanlis beyan gercek musteriye gider.

BU KAPININ IDDIASI
------------------
Sinif (`tur`) BEYANI SURUYOR ve ayrim HER YUZEYDE ayni yonde:
  A  SIPARIS ONAY E-POSTASI  — hazir sepette URETIM DILI YOK + 14 gun cayma yazili;
                               ozel sepette bugunku dil AYNEN; KARMA sepette KALEM BAZINDA.
  B  URUN SAYFASI            — fiziksel urun sayfasinda HAZIR sinif beyani VAR; `tur`suz
                               urunde o beyan YOK ama OZEL URETIM TESLIM BEYANI VAR
                               (B4/B5/B6, 10 Agu — asagida).
  C  TESLIMAT / SOZLESME     — teslimat kolu IKI SINIFLI ("olcu onayi" hazir uruna dayatilmaz).
  D  ODEME EKRANI            — sepet sinifina gore metin; hepsi ozel iken BUGUNKU metin.
  E  TEK KAYNAK              — cumleler secenekler.js BEYAN'inda; build.py/eposta.js/index.html
                               onu TUKETIR, ikinci kopya yazmaz (ikiz tanim sessizce ayrisamaz).

🔴 FAIL-CLOSED YONU (para yoluyla AYNI): kural "fiziksel ISE hazir de", "3D ISE ozel de"
DEGIL. `tur` YOKSA ya da taninmayan bir deger tasiyorsa beyan BUGUNKU gibi (ozel uretim)
uretilir -> 15.930 ozel uretim kaydinda regresyon 0. A9/B3 bunu BAYT-ESITLIKLE olcer.

KAPSAM DISI (C4 ile NOBET TUTULUR): iade kargo bedelinin kime ait oldugu Okan'a soruldu,
cevap BEKLIYOR. Metne "kargo bedeli su tarafa aittir" cumlesi YAZILAMAZ; C4 bir baskasinin
bu boslugu sessizce doldurmasini KIRMIZI yakar.

TESLIM BEYANI EKSENI (B4/B5/B6/E5 — 10 Agu, Okan karari)
--------------------------------------------------------
Urun sayfasi teslim SURESINI hic soylemiyordu: 23.968 ozel uretim urununde beyan HIC
yoktu, 943 hazir/stok urununde de gun sayisi YAZILI DEGILDI. Musteri "ne zaman elime
gecer" bilmeden odeme karari veriyordu. Okan sureyi IKI SINIF icin de 3-5 is gunu
olarak karara bagladi; TETIKLEYICI ayri kaldi (ozel: "olcu onayindan sonra" · hazir:
"odemeniz onaylandiktan sonra" — hazir uruNde olcu onayi asamasi YOKTUR).

🔴 BU YUZEY NEDEN NOBETSIZDI: odeme-beyani-kapisi.py #6 rakip-sure taramasi 84
yasal/landing govdesini tarar; `urun/` sayfalari o kumede YOKTUR. Yani urun sayfasina
yazilacak bir gun sayisini o gun hicbir kapi olcmuyordu. B4/B5/B6 o kor noktayi kapatir.

ONCE-KIRMIZI: degisiklikten ONCEKI agacta A4/A5/A6/A7/A8 (kosulsuz e-posta), B1, C1/C2,
D1-D6 ve E1-E3 KIRMIZI yanar; A1/A2/A3/A9/B2/B3/C3/C4/C5 (regresyon capalari) YESILDIR.
B4/B5/E5 ise 10 Agu oncesi agacta KIRMIZI (beyan hic basilmiyordu).

node ZORUNLU (deploy.yml setup-node kurar) — yoksa FAIL-CLOSED kirmizi: e-posta ve odeme
iddialari olculmeden bu kapi YESIL VEREMEZ.

Offline (ag yok), GERCEK urunler.json OKUNMAZ (sentetik fiksturler), repoya DOSYA YAZMAZ.

Kullanim:
    python3 tools/cayma-beyani-kapisi.py
    python3 tools/cayma-beyani-kapisi.py --mutasyon

--mutasyon UC AILE kosar:
  1. eposta.js sinif karari no-op (3 mutant)                 -> A/E ekseni olmeli
  2. build.py urun sayfasi teslim beyani (6 mutant, 12 iddia) -> B/E ekseni olmeli;
     kabul KATI: beklenen iddialarin HEPSI dusecek, beklenen DISINDA hicbiri dusmeyecek
  3. KONTROL mutanti (1) — masum bicim rotusunda kapi YESIL kalmali (iddia dar mi?)

Cikis kodlari: 0 = YESIL (butun iddialar olculdu ve gecti) · 1 = KIRMIZI.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
BUILD_YOL = os.path.join(TOOLS, "build.py")
SECENEKLER_YOL = os.path.join(ROOT, "secenekler.js")
EPOSTA_YOL = os.path.join(ROOT, "shop", "src", "eposta.js")
INDEX_YOL = os.path.join(ROOT, "index.html")

# --------------------------------------------------------------------------- sozluk
# SINIF SOZ DAGARCIGI — kapinin olctugu sey CUMLE DEGIL ANLAMDIR. Buraya BEYAN'daki
# cumlelerin kopyasi YAZILMAZ (yazilsaydi kapi kendi kopyasini dogrular, ayrisma gorunmezdi);
# yalnizca "uretim dili" ve "sinif etiketi" soz dagarcigi durur. Cumlelerin BIREBIR ayni
# kaynaktan geldigi AYRI bir eksende (E2/E3) olculur.
URETIM_DILI = re.compile(
    r"üretil|üretim|üretime|üretiliyor|ölçü onay|ölçünüz|kişiye özel|ölçüye özel", re.I)
HAZIR_ETIKET_RE = re.compile(r"Hazır ürün", re.I)
OZEL_ETIKET_RE = re.compile(r"Özel üretim", re.I)
# 🔴 KELIME SINIRI ZORUNLU (olculdu 10 Agu, GERCEK katalog):
#   "cayma"     -> `Porsche Boxster & Cayman` 2 uruNde eslesiyordu (gevsek 2, kati 0).
#   "14\s*gün"  -> `Nissan Rogue 2014 Güneşlik` uruNde eslesiyordu (gevsek 3, kati 2;
#                  kalan 2 "14 güne kadar dayanır" olup GERCEK bir ifadedir).
# CAYMA_RE NEGATIF iddialarda kullaniliyor (A3/B2/B5) -> yanlis-pozitif TUM YAYINI
# durdurur ([[tekil-yama-sinifi-kapatmaz]]). Bugun fikstur dar oldugu icin yesildi;
# B9 bu iki gercek vakayi KONTROL FIKSTURU olarak nobetler.
CAYMA_RE = re.compile(r"\bcayma\b", re.I)
ONDORT_GUN_RE = re.compile(r"\b14\s*gün", re.I)
# RAKIP TESLIM ARALIGI — bilinen bayat araliklarin KARA LISTESI. 🔴 TEK BASINA KABUL
# DEGILDIR: sayili kara liste bir sonraki varyanti (10-20, 15-30, 7-10 ...) sessizce
# gecirir — olculdu, 5 icerik mutanti bu yuzden yesil gecmisti. Asil olcu KANONIK
# SURE POZITIF sarti + "kanonik disinda hicbir sure YOK" negatifi (bkz. _sureler).
RAKIP_SURE_RE = re.compile(r"\b(5-7|3-6|2-4)\s+iş\s+günü\b", re.I)
# TESLIM SURESI JETONU — "3-5 iş günü", "10-20 iş gününde", "7 iş günü" hepsi.
# Kanonik deger BEYAN'dan TURETILIR, buraya YAZILMAZ.
SURE_JETONU_RE = re.compile(r"(\d+\s*[-–]\s*\d+|\d+)\s*iş\s+gün", re.I)
# Sinif beyani blogu (urun sayfasi). Icerik BAYT-BIREBIR karsilastirilir: `_etiketsiz`
# normalizasyonu iki bosluk/kacis farkini yutar, bu desen YUTMAZ.
BEYAN_DIV_RE = re.compile(r'<div class="sinif-beyan"[^>]*>(.*?)</div>', re.S)
# HAZIR/STOK sinifinda BULUNMAMASI gereken ifade: hazir ticari malda "olcu onayi"
# diye bir asama YOKTUR (C1/C2'nin var olma sebebi).
OLCU_ONAY_RE = re.compile(r"ölçü\s*onay|ölçüye\s+özel|kişiye\s+özel", re.I)

# --------------------------------------------------------------- TETIKLEYICI SINIFLARI
# "Sayac hangi olayla baslar?" — teslim taahhudunun BAGLANDIGI olay. Ayni musteri iki
# yuzeyde (urun sayfasi / siparis onay e-postasi) iki farkli baslangic GORMEMELI.
# 🔴 "olcu onayi" ozel uretim sinifinin %99,84'unde VAR OLMAYAN bir asamadir
# (parametrik/konfigurlu yalniz 39 kayit; odeme akisi iyzico hosted, boyle bir adim yok).
TETIK_OLCU_RE = re.compile(r"ölçü\w*\s+(?:onay|teyid|netleş)", re.I)
TETIK_SIPARIS_RE = re.compile(
    r"sipariş\w*\s+(?:onaylandı|onaylandıktan|üzerine|alındıktan)"
    r"|siparişiniz(?:den)?\s+sonra", re.I)
TETIK_ODEME_RE = re.compile(r"ödemeniz\s+onaylandık", re.I)
TETIKLEYICILER = (("ölçü onayı", TETIK_OLCU_RE),
                  ("sipariş onayı", TETIK_SIPARIS_RE),
                  ("ödeme onayı", TETIK_ODEME_RE))

# HAK REDDI DILI — urun sayfasina ASLA basilmaz (iki sinifta da). Hakkin KAPSAMI
# yasal govdede anlatilir; urun sayfasinda "hakkiniz yoktur" demek, m.15 istisnasini
# urun bazinda dayatmaktir. B2'nin POZITIF ikizi (B8).
HAK_REDDI_RE = re.compile(
    r"(?:cayma|iade|değişim|geri\s+ödeme)\s*(?:hakk\w*)?\s*"
    r"(?:yoktur|bulunmamaktadır|bulunmaz|kabul\s+edilmez|edilemez|mümkün\s+değildir)"
    r"|(?:iade|değişim)\s+edilemez", re.I)


def _sureler(metin):
    """Metindeki teslim suresi jetonlarinin KUMESI ("3-5", "10-20" ...).

    Bosluk/tire varyantlari normalize edilir ki "3 - 5" ile "3-5" AYNI jeton sayilsin;
    kabul araligi ile karsilastirma araligi TEK fonksiyondan turer
    ([[kabul-araligi-karsilastirma-araligi]])."""
    out = set()
    for m in SURE_JETONU_RE.finditer(metin or ""):
        out.add(re.sub(r"\s+", "", m.group(1)).replace("–", "-"))
    return out


# OLUMSUZLAMA — bir tetikleyici IFADESI, hemen ardindan reddediliyorsa TETIKLEYICI
# DEGILDIR. Olculdu: yasal stok cumlesi "Hazır/stok ürünlerde ÖLÇÜ ONAYI AŞAMASI
# YOKTUR; ... ödemeniz onaylandıktan sonra ..." der — orada "ölçü onayı" sayacin
# baslangici degil, TAM TERSI bir REDDIR. Olumsuzlamayi saymamak bu kapinin en
# temel ayrimini (hazir malda olcu onayi asamasi yoktur) yanlis okurdu.
OLUMSUZLAMA_RE = re.compile(
    r"^[^.;]{0,40}?\b(?:yoktur|yok|bulunmaz|bulunmamaktadır|değildir|geçerli\s+değildir)\b",
    re.I)


def _tetikleyiciler(metin):
    """Metindeki tetikleyici SINIFLARININ kumesi (OLUMSUZLANAN ifadeler sayilmaz)."""
    metin = metin or ""
    out = set()
    for ad, desen in TETIKLEYICILER:
        for m in desen.finditer(metin):
            if OLUMSUZLAMA_RE.match(metin[m.end():]):
                continue                     # "... asamasi YOKTUR" -> tetikleyici degil
            out.add(ad)
            break
    return out

# Bugunku (degisiklik ONCESI) e-posta cumleleri — REGRESYON CAPASI. Hepsi ozel uretim olan
# sepette govde BU cumleleri AYNEN tasimali; degisirse 15.930 kayitlik sinifin metni
# kaymis demektir.
CAPA_ODENDI_OZEL = ("Ödemeniz alındı, siparişiniz onaylandı. Ürünleriniz özel olarak "
                    "üretilip gönderilecektir.")
CAPA_HAVALE_OZEL = ("Siparişiniz alındı. Havale/EFT ödemeniz hesabımıza geçtiğinde "
                    "üretime başlanır.")
# Odeme ekraninin bugunku (ozel uretim) metinleri — ayni regresyon capasi.
CAPA_ODEME_HAVALE_OZEL = ("Devam ettiğinizde siparişiniz kaydedilir ve ödeme için IBAN "
                          "bilgileri gösterilir; ödemeniz hesabımıza geçince üretim başlar.")
CAPA_HAVALE_KUTU_OZEL = ("Ödemeniz hesabımıza geçince üretim başlar; dilerseniz dekontu "
                         "WhatsApp'tan iletebilirsiniz.")

# C4 — Okan'in cevabini BEKLEYEN alan. Bu desenlerden biri yasal gövdeye girerse KIRMIZI.
IADE_KARGO_DESENI = re.compile(
    r"(iade|cayma)[^.]{0,120}kargo\s+(bedeli|ücreti|masrafı)[^.]{0,40}(ait|karşılan|öden)"
    r"|kargo\s+(bedeli|ücreti)[^.]{0,60}(alıcı|tüketici|müşteri)ya?\s+ait", re.I)


# --------------------------------------------------------------------------- yardimcilar
def _node(betik_metni):
    """Verilen ESM betigini node ile kostur, son satirdaki JSON'u dondur.

    Betik SISTEM gecici dizinine yazilir (DEPO AGACI KIRLENMEZ); import'lar mutlak
    file:// URL'leri oldugu icin betigin konumu sonucu etkilemez."""
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", encoding="utf-8",
                                     delete=False) as f:
        f.write(betik_metni)
        yol = f.name
    try:
        r = subprocess.run([os.environ.get("NODE", "node"), yol],
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        raise SystemExit("KIRMIZI: node kosturulamadi (%s) — e-posta/odeme iddialari "
                         "olculemedi. deploy.yml setup-node BLOKLAYICI on-kosuldur." % e)
    finally:
        os.unlink(yol)
    if r.returncode != 0:
        raise SystemExit("KIRMIZI: node probe'u kosmadi (exit %d):\n%s"
                         % (r.returncode, (r.stderr or r.stdout or "")[:3000]))
    cikti = (r.stdout or "").strip().splitlines()
    if not cikti:
        raise SystemExit("KIRMIZI: node probe'u bos cikti verdi.")
    return json.loads(cikti[-1])


PROBE = r"""
import "%(secenekler)s";
const E = await import("%(eposta)s");
const S = globalThis.PRUVO_SECENEK || null;

const SIPARIS = { siparis_no: "PR-TEST-0001", musteri_ad: "Sinama Musteri",
                  musteri_adres: "Sinama Mah. No:1 / Mugla" };
const DOKUM = { tutarKurus: 100000, kargoKurus: 25000, kdvKurus: 20833,
                tahsilatKurus: 125000 };

// HAZIR kalem: Worker sepetiFiyatla'nin fiziksel kolunda kurdugu satirin AYNISI
// (malzeme/renk/renk_ozel BOS + tur POZITIF isaret).
function hazir(id, tur) {
  const s = { id: id, baslik: "Hazir Sinama Urunu", kategori: "Marin", gorsel: "",
              malzeme: "", renk: "", renk_ozel: "", adet: 1,
              birim_kurus: 100000, tutar_kurus: 100000 };
  if (tur !== undefined) { s.tur = tur; }
  return s;
}
// OZEL kalem: `tur` alani HIC YOK (15.930 baski urununun satiri).
function ozel(id) {
  return { id: id, baslik: "Ozel Sinama Urunu", kategori: "Otomobil", gorsel: "",
           malzeme: "PLA", renk: "Siyah", renk_ozel: "", adet: 2,
           birim_kurus: 50000, tutar_kurus: 100000 };
}

const H = hazir("sinama-hazir", "fiziksel");
const O = ozel("sinama-ozel");

// FAIL-CLOSED ekseni: taninmayan `tur` degerleri `tur`suz satirla AYNI govdeyi vermeli.
const TANINMAYAN = ["Fiziksel", "FIZIKSEL", " fiziksel", "fiziksel ", "fiziksel-degil",
                    "3d", "", null, 0, 1, true, false, [], ["fiziksel"], {t:"fiziksel"}];
const tursuz = E.onayEpostasiHtml(SIPARIS, [hazir("sinama-hazir")], DOKUM, false);
const failClosed = {};
for (const d of TANINMAYAN) {
  failClosed[JSON.stringify(d) === undefined ? "undefined" : JSON.stringify(d)] =
    (E.onayEpostasiHtml(SIPARIS, [hazir("sinama-hazir", d)], DOKUM, false) === tursuz);
}

const cikti = {
  beyan: (S && S.BEYAN) ? S.BEYAN : null,
  sepetSinifiVar: !!(S && typeof S.sepetSinifi === "function"),
  odemeBeyaniVar: !!(S && typeof S.odemeBeyani === "function"),
  havaleKutuVar: !!(S && typeof S.havaleKutuBeyani === "function"),
  sinif: (S && typeof S.sepetSinifi === "function") ? {
    bos: S.sepetSinifi([]),
    hepsi_ozel: S.sepetSinifi([undefined, undefined]),
    hepsi_hazir: S.sepetSinifi(["fiziksel", "fiziksel"]),
    karma: S.sepetSinifi(["fiziksel", undefined]),
    taninmayan: S.sepetSinifi(["Fiziksel", " fiziksel", null, 0, [], ""]),
  } : null,
  odeme: (S && typeof S.odemeBeyani === "function") ? {
    ozel_havale: S.odemeBeyani("ozel"),
    hazir_havale: S.odemeBeyani("hazir"),
    karma_havale: S.odemeBeyani("karma"),
    bilinmeyen_havale: S.odemeBeyani("zirva"),
  } : null,
  cayma: (S && typeof S.caymaBeyani === "function") ? {
    ozel: S.caymaBeyani("ozel"),
    hazir: S.caymaBeyani("hazir"),
    karma: S.caymaBeyani("karma"),
    bilinmeyen: S.caymaBeyani("zirva"),
  } : null,
  havaleKutu: (S && typeof S.havaleKutuBeyani === "function") ? {
    ozel: S.havaleKutuBeyani("ozel"),
    hazir: S.havaleKutuBeyani("hazir"),
    karma: S.havaleKutuBeyani("karma"),
    bilinmeyen: S.havaleKutuBeyani("zirva"),
  } : null,
  eposta: {
    ozel_kart: E.onayEpostasiHtml(SIPARIS, [O], DOKUM, false),
    ozel_havale: E.onayEpostasiHtml(SIPARIS, [O], DOKUM, true),
    hazir_kart: E.onayEpostasiHtml(SIPARIS, [H], DOKUM, false),
    hazir_havale: E.onayEpostasiHtml(SIPARIS, [H], DOKUM, true),
    karma_kart: E.onayEpostasiHtml(SIPARIS, [H, O], DOKUM, false),
    karma_havale: E.onayEpostasiHtml(SIPARIS, [H, O], DOKUM, true),
  },
  failClosed: failClosed,
};
console.log(JSON.stringify(cikti));
"""


def probe_calistir(secenekler_yol=None, eposta_yol=None):
    return _node(PROBE % {
        "secenekler": "file://" + (secenekler_yol or SECENEKLER_YOL),
        "eposta": "file://" + (eposta_yol or EPOSTA_YOL),
    })


def build_modulu(kaynak=None):
    """tools/build.py'yi MODUL olarak yukler (main() kosmaz, diske yazmaz).

    `kaynak` verilirse DISKTEKI dosya yerine o metin derlenir — build.py mutantlari
    boylece DISKE HIC YAZILMAZ: ne agac kirlenir, ne de "ayni uzunlukta mutant ayni
    saniyede yazilinca uygulanmaz" bytecode/mtime tuzagi devreye girer.
    Yuklenen kaynak modulde saklanir; kaynak duzeyinde olcen iddialar (E1/E5)
    diskteki dosyayi DEGIL, FIILEN DERLENEN metni yargilar."""
    if kaynak is None:
        with open(BUILD_YOL, encoding="utf-8") as f:
            kaynak = f.read()
    mod = types.ModuleType("build_cayma")
    mod.__file__ = BUILD_YOL
    mod.__name__ = "build_cayma"
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    exec(compile(kaynak, BUILD_YOL, "exec"), mod.__dict__)
    mod._KAPI_BUILD_KAYNAK = kaynak
    return mod


def sayfalar_modulu(kaynak=None):
    """tools/sayfalar.py — `kaynak` verilirse o metin derlenir (mutant, diske yazmaz)."""
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    if kaynak is None:
        import sayfalar
        return sayfalar
    yol = os.path.join(TOOLS, "sayfalar.py")
    mod = types.ModuleType("sayfalar_cayma")
    mod.__file__ = yol
    mod.__name__ = "sayfalar_cayma"
    exec(compile(kaynak, yol, "exec"), mod.__dict__)
    return mod


def _yorumsuz(py_kaynak):
    """Python kaynagindan `#` yorumlarini siler; DIZE icindekilere DOKUNMAZ.

    🔴 NEDEN VAR (curutucu, 10 Agu): E5'in "BEYAN'i OKUYOR" ayagi bir YORUM SATIRIYLA
    tatmin oluyordu — curutucu cagriyi kacis dizeli bir ikize cevirdi, geriye metin
    yalnizca yorumda kaldi ve kapi rc=0 verdi. Kaynak duzeyinde olcen her iddia
    artik YORUMSUZ metni yargilar."""
    cikti = []
    for satir in py_kaynak.splitlines():
        tirnak = None
        i = 0
        n = len(satir)
        while i < n:
            c = satir[i]
            if tirnak:
                if c == "\\":
                    i += 2
                    continue
                if c == tirnak:
                    tirnak = None
            elif c in "\"'":
                tirnak = c
            elif c == "#":
                satir = satir[:i]
                break
            i += 1
        cikti.append(satir)
    return "\n".join(cikti)


def _secenekler_beyanli(yeni_beyan):
    """BEYAN sozlugu DEGISTIRILMIS bir GECICI AGAC kurar. Doner: (dizin, js, eposta).

    🔴 NEDEN TAM AGAC: yalnizca secenekler.js kopyalansaydi node probe'u MUTANTI
    GORMEZDI — `shop/src/eposta.js` kendi icinde `../../secenekler.js`'i import eder
    ve ESM o URL'yi AYRI bir modul olarak yukleyip `globalThis.PRUVO_SECENEK`'i
    GERCEK dosyayla ezer. Olculdu: probe orijinal cumleyi, build.py mutant cumleyi
    doner -> mutant "capraz ayrisma" gibi gorunur, gercek iddia olculmez.
    (Ayni tuzak eposta.js mutant ailesinde de gecici agacla cozulmustu.)

    E5'in DAVRANISSAL ayagi icin de kullanilir: tek kaynak degisince build.py
    ciktisi da degismeli; kacis dizileriyle yazilmis bir ikiz bunu GECEMEZ."""
    with open(SECENEKLER_YOL, encoding="utf-8") as f:
        js = f.read()
    m = re.search(r"var\s+BEYAN\s*=\s*(\{.*?\});", js, re.S)
    if not m:
        return None, None, None
    yeni_govde = json.dumps(yeni_beyan, ensure_ascii=False, indent=4)
    ged = tempfile.mkdtemp(prefix="cayma-tekkaynak-")
    yol = os.path.join(ged, "secenekler.js")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(js[:m.start(1)] + yeni_govde + js[m.end(1):])
    src_dizin = os.path.join(ged, "shop", "src")
    os.makedirs(src_dizin)
    eposta_yolu = os.path.join(src_dizin, "eposta.js")
    shutil.copyfile(EPOSTA_YOL, eposta_yolu)
    return ged, yol, eposta_yolu


# SECENEKLER_JS atamasi — ZATEN yeniden baglanmis bir kaynak da kabul edilir
# (mutant aileleri ust uste binebilir; capa "bir kez uygulanmis" halde de tutmali).
_SEC_JS_ATAMA_RE = re.compile(r"^SECENEKLER_JS\s*=\s*.+$", re.M)


def _build_baska_secenekle(build_kaynak, secenekler_yolu):
    """build.py'yi, secenekler.js'i BASKA bir yoldan okuyacak sekilde yukler.

    Yalnizca SECENEKLER_JS atamasi yeniden baglanir; olculen davranis (cumlenin
    nereden geldigi) DEGISTIRILMEZ."""
    if len(_SEC_JS_ATAMA_RE.findall(build_kaynak)) != 1:
        return None
    return build_modulu(_SEC_JS_ATAMA_RE.sub(
        lambda _m: "SECENEKLER_JS = %r" % secenekler_yolu, build_kaynak, count=1))


def _urun(uid, tur=Ellipsis, kategori="Marin", ek=None):
    """Sentetik urun kaydi (fiziksel-urun-kapisi.py ile AYNI fikstur ekseni).

    `kategori` + `ek` ile ayni sinifin FARKLI RENDER YOLLARI kurulur (opsiyon
    zincirinin dallari): kart-secim · konfigur · semasiz-parametrik · panelsiz."""
    u = {
        "id": uid,
        "baslik": "Sinama Urunu",
        "kategori": kategori,
        "marka": ["Sinama"],
        "fiyat": "1000 TL",
        "aciklama": "Sinama aciklamasi.\nIkinci satir.",
        "gorseller": ["https://media.example/%s-1.jpg" % uid],
    }
    if tur is not Ellipsis:
        u["tur"] = tur
    if ek:
        u.update(ek)
    return u


# KONFIGUR (dekor konfiguratoru) dalinin sentetik semasi — GERCEK urunler.json
# OKUNMAZ. Alanlar render_product'in FIILEN okudugu asgari kume.
SENTETIK_KONFIGUR = {
    "renkler": ["Siyah", "Beyaz"],
    "renkGorselIndeks": {"Siyah": 0, "Beyaz": 0},
    "boyutMm": {"min": 60, "max": 300, "adim": 10, "varsayilan": 150,
                "etiket": "Yükseklik"},
    "hacim": {"refYukseklikMm": 150, "refHacimCm3": 300.0},
    "fiyatCapalari": [[60, 500], [300, 2500]],
}


def _ana_govde(html):
    """<main> icerigi, script/style cikarilmis (footer + satir-ici JS sizmasin)."""
    m = re.search(r"<main\b.*?</main>", html, re.S)
    g = m.group(0) if m else html
    g = re.sub(r"<script\b.*?</script>", "", g, flags=re.S)
    return re.sub(r"<style\b.*?</style>", "", g, flags=re.S)


def _etiketsiz(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _icerik(html):
    """E-postanin SIPARISE OZGU govdesi: cerceve basligindan (</h3>) SONRASI.

    KAPSAM NEDEN DAR: cerceve her e-postaya sabit bir marka satiri basar —
    "Endüstriyel Parça Üretimi · Fethiye". "Uretim dili yok" iddiasi TUM govdede
    aransaydi, marka satirindaki 'Üretimi' iddiayi HER ZAMAN dusururdu; iddia o
    zaman sinif ayrimini degil marka satirini olcerdi (ayni tuzak
    fiziksel-urun-kapisi.py'de footer 'Malzeme Rehberi' linkiyle olculdu ve orada
    da bolgeyle kapatildi). </h3> capasi bugunku sablonda ZATEN vardir; iddia
    boylece siparise ozgu metni olcer."""
    return html.split("</h3>", 1)[-1]


def _satirlar(html):
    """E-postadaki URUN tablosunun <tbody> satirlari.

    KAPSAM DAR TUTULUR: e-postada ikinci bir tablo daha var (ara toplam/kargo/KDV
    dokumu, 4 satir). Tum <tr>'leri saysaydik "kalem sayisi" iddiasi dokum satirlariyla
    dolar ve kalem-bazli beyan olculemezdi."""
    m = re.search(r"<tbody>(.*?)</tbody>", html, re.S)
    if not m:
        return []
    return re.findall(r"<tr\b.*?</tr>", m.group(1), re.S)


def _inline_script(html):
    """index.html'in sepet/arama satir-ici <script> blogu (icerik imzasi: cartLines)."""
    for m in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S):
        if "cartLines" in m.group(1):
            return m.group(1)
    return ""


# --------------------------------------------------------------------------- iddialar
def kosum(probe, mod, sayfalar):
    """Butun iddialari olcer; (hatalar, satirlar) dondurur. hatalar bos = YESIL."""
    hatalar, rapor = [], []

    def ol(kod, aciklama, gecti, kanit=""):
        rapor.append("  %-4s %-62s %s%s"
                     % (kod, aciklama, "✔" if gecti else "✘",
                        ("  " + kanit) if kanit else ""))
        if not gecti:
            hatalar.append("%s %s%s" % (kod, aciklama, ("  -> " + kanit) if kanit else ""))

    ep = probe["eposta"]
    beyan = probe["beyan"]

    # ================================================== A — SIPARIS ONAY E-POSTASI
    rapor.append("A) SIPARIS ONAY E-POSTASI (shop/src/eposta.js · onayEpostasiHtml)")
    ol("A1", "hepsi OZEL + kart: bugunku cumle AYNEN (regresyon capasi)",
       CAPA_ODENDI_OZEL in ep["ozel_kart"])
    ol("A2", "hepsi OZEL + havale: bugunku cumle AYNEN (regresyon capasi)",
       CAPA_HAVALE_OZEL in ep["ozel_havale"])
    ol("A3", "hepsi OZEL govdesine hazir-urun etiketi + cayma beyani SIZMADI",
       not HAZIR_ETIKET_RE.search(_etiketsiz(ep["ozel_kart"]))
       and not HAZIR_ETIKET_RE.search(_etiketsiz(ep["ozel_havale"]))
       and not CAYMA_RE.search(_etiketsiz(ep["ozel_kart"])))

    hazir_kart_duz = _etiketsiz(_icerik(ep["hazir_kart"]))
    hazir_havale_duz = _etiketsiz(_icerik(ep["hazir_havale"]))
    # FAIL-CLOSED: bolge BOSSA "uretim dili bulunamadi" KANIT DEGILDIR (bos kume uzerinde
    # her negatif iddia bedavaya gecer) -> bolgenin dolu oldugu ayrica sart kosulur.
    u1 = URETIM_DILI.findall(hazir_kart_duz)
    ol("A4", "hepsi HAZIR + kart: URETIM DILI YOK (siparise ozgu govde)",
       bool(hazir_kart_duz) and not u1,
       ("sizan: %s" % sorted(set(u1))) if u1 else ("BOLGE BOS" if not hazir_kart_duz else ""))
    u2 = URETIM_DILI.findall(hazir_havale_duz)
    ol("A5", "hepsi HAZIR + havale: URETIM DILI YOK (siparise ozgu govde)",
       bool(hazir_havale_duz) and not u2,
       ("sizan: %s" % sorted(set(u2))) if u2
       else ("BOLGE BOS" if not hazir_havale_duz else ""))
    ol("A6", "hepsi HAZIR: 14 gun + cayma beyani VAR",
       bool(ONDORT_GUN_RE.search(hazir_kart_duz)) and bool(CAYMA_RE.search(hazir_kart_duz))
       and bool(ONDORT_GUN_RE.search(hazir_havale_duz))
       and bool(CAYMA_RE.search(hazir_havale_duz)))

    # A7 — KALEM BAZINDA: karma sepette her satir KENDI sinifini tasimali. Govde
    # duzeyinde "iki sinif da geciyor" YETMEZ: musteri hangi kalemin hangi sinifta
    # oldugunu satirinda gormeli (mimar karari; tek cumleye indirgeme YASAK).
    karma_satirlar = _satirlar(ep["karma_kart"])
    a7_kanit = "satir=%d" % len(karma_satirlar)
    a7 = False
    if len(karma_satirlar) == 2:
        hazir_satir = [t for t in karma_satirlar if "sinama-hazir" in t]
        ozel_satir = [t for t in karma_satirlar if "sinama-ozel" in t]
        if hazir_satir and ozel_satir:
            h_duz, o_duz = _etiketsiz(hazir_satir[0]), _etiketsiz(ozel_satir[0])
            a7 = (bool(HAZIR_ETIKET_RE.search(h_duz)) and not OZEL_ETIKET_RE.search(h_duz)
                  and bool(OZEL_ETIKET_RE.search(o_duz))
                  and not HAZIR_ETIKET_RE.search(o_duz))
            a7_kanit = "hazir satir=%r | ozel satir=%r" % (h_duz[:70], o_duz[:70])
    ol("A7", "KARMA sepet: sinif KALEM BAZINDA satirda gorunuyor", a7, "" if a7 else a7_kanit)

    karma_duz = _etiketsiz(ep["karma_kart"])
    ol("A8", "KARMA sepet: iki sinifin da beyani geciyor (tek cumleye indirgenmemis)",
       bool(HAZIR_ETIKET_RE.search(karma_duz)) and bool(OZEL_ETIKET_RE.search(karma_duz))
       and bool(ONDORT_GUN_RE.search(karma_duz)) and bool(CAYMA_RE.search(karma_duz)))

    sapan = [k for k, v in probe["failClosed"].items() if not v]
    ol("A9", "FAIL-CLOSED: 15 taninmayan `tur` degeri `tur`suzle BAYT-ESIT", not sapan,
       ("sapan: %s" % sapan) if sapan else "%d deger" % len(probe["failClosed"]))

    with open(EPOSTA_YOL, encoding="utf-8") as f:
        eposta_src = f.read()
    elle_dize = re.findall(r'[=!]==\s*"fiziksel"|"fiziksel"\s*[=!]==', eposta_src)
    devir = [ad for ad in ("S.sepetSinifi(", "S.satirBeyani(", "S.epostaDurumBeyani(",
                           "S.caymaBeyani(") if ad not in eposta_src]
    ol("A10", "eposta.js sinif kararini secenekler.js'e DEVREDIYOR (elle dize karsilastirmasi yok)",
       not devir and not elle_dize,
       "" if (not devir and not elle_dize)
       else "eksik devir=%s elle_dize=%s" % (devir, elle_dize))

    # ================================================== B — URUN SAYFASI
    rapor.append("B) URUN SAYFASI (tools/build.py render_product · sentetik fikstur)")
    fiz, nrm = _urun("sinama-fiziksel", tur="fiziksel"), _urun("sinama-normal")
    tum = [fiz, nrm]
    fiz_html = mod.render_product(fiz, tum)
    nrm_html = mod.render_product(nrm, tum)
    fiz_govde = _etiketsiz(_ana_govde(fiz_html))
    nrm_govde = _etiketsiz(_ana_govde(nrm_html))
    ol("B1", "fiziksel urun sayfasinda hazir-urun + cayma beyani VAR",
       bool(HAZIR_ETIKET_RE.search(fiz_govde)) and bool(CAYMA_RE.search(fiz_govde))
       and bool(ONDORT_GUN_RE.search(fiz_govde)))
    ol("B2", "`tur`suz urun sayfasina beyan SIZMADI (regresyon)",
       not HAZIR_ETIKET_RE.search(nrm_govde) and not CAYMA_RE.search(nrm_govde))
    b3_sapan = []
    for deger in ["fiziksel-degil", "3d", "Fiziksel", "FIZIKSEL", " fiziksel", "fiziksel ",
                  "", None, 0, 1, True, False, [], ["fiziksel"], {"t": "fiziksel"}]:
        if mod.render_product(_urun("sinama-normal", tur=deger), tum) != nrm_html:
            b3_sapan.append(repr(deger))
    ol("B3", "FAIL-CLOSED: 15 taninmayan `tur` degeri `tur`suz sayfayla BAYT-ESIT",
       not b3_sapan, ("sapan: %s" % b3_sapan) if b3_sapan else "")

    # ---------------------------------------------- B4/B5/B6 — TESLIM BEYANI (10 Agu)
    # 🔴 NEDEN VAR: 23.968 ozel uretim urununun sayfasinda teslim suresi HIC yoktu ve
    # 943 hazir/stok urununde de sayi YAZILI DEGILDI — ziyaretci "ne zaman elime gecer"
    # bilmeden odeme karari veriyordu. Okan sureyi iki sinif icin de 3-5 is gunu olarak
    # karara bagladi. Yuzey NOBETSIZDI: odeme-beyani-kapisi.py #6 rakip-sure taramasi
    # 84 yasal/landing govdesini tarar, `urun/` sayfalari o kumede YOKTUR.
    # Cumleler BURAYA KOPYALANMAZ; BEYAN sozlugunden okunur (ikiz tanim yasagi).
    ozel_dallar = [
        ("kart-secim", nrm_html),
        # Konfigur dalinda liste fiyati capa-1 fiyatiyla AYNI olmak zorundadir
        # (JSON-LD Offer.price = asgari fiyat beyani); fikstur o kurala uyar.
        ("konfigur", mod.render_product(
            _urun("sinama-konfigur", kategori="Dekorasyon",
                  ek={"konfigur": SENTETIK_KONFIGUR, "fiyat": "500 TL"}), tum)),
        ("semasiz-parametrik", mod.render_product(
            _urun("sinama-parametrik-semasiz", ek={"parametrik": True}), tum)),
        ("panelsiz", mod.render_product(
            _urun("sinama-panelsiz", kategori="Jeneratör"), tum)),
    ]
    ozel_cumle = beyan.get("SAYFA_OZEL") if isinstance(beyan, dict) else None
    hazir_cumle = beyan.get("SAYFA_HAZIR") if isinstance(beyan, dict) else None
    ozel_duz = _etiketsiz(ozel_cumle) if isinstance(ozel_cumle, str) else ""

    # B4 — POZITIF: cumle DORT render yolunda da VAR ve blok BAYT-BIREBIR tek kaynaktan.
    b4_hata = []
    if not ozel_duz:
        b4_hata.append("BEYAN['SAYFA_OZEL'] yok/bos")
    else:
        for ad, h in ozel_dallar:
            if ozel_duz not in _etiketsiz(_ana_govde(h)):
                b4_hata.append("%s: metin YOK" % ad)
            elif BEYAN_DIV_RE.findall(h) != [mod.esc(ozel_cumle)]:
                b4_hata.append("%s: blok bayt-birebir DEGIL (%d adet)"
                               % (ad, len(BEYAN_DIV_RE.findall(h))))
    ol("B4", "OZEL URETIM sayfasinda teslim beyani VAR (4 render yolu, bayt-birebir)",
       not b4_hata, ("%s" % b4_hata) if b4_hata else "%d dal" % len(ozel_dallar))

    # B5 — SURE: POZITIF + KAPALI KUME (kara liste TEK BASINA kabul DEGIL).
    # 🔴 NEDEN DEGISTI (curutucu, 10 Agu): B5 yalniz sayili kara liste (5-7|3-6|2-4)
    # kullaniyordu; "10-20 is gunu", "15-30 is gunu", "7-10 is gunu" mutantlari ve
    # taahhudun TAMAMEN SILINMESI kapidan SESSIZCE gecti. Muafiyet/yasak kume
    # KANONIK KUMEDEN turemezse bir sonraki varyant sizar
    # ([[tekil-yama-sinifi-kapatmaz]]). Artik her SINIFIN sayfasinda O SINIFIN
    # kanonik sure jetonu VAR olacak ve sayfada kanonik disinda HICBIR sure jetonu
    # bulunmayacak. Kanonik deger BEYAN'dan TURETILIR (kapiya yazilmaz).
    b5_hata = []
    ozel_kanonik = _sureler(ozel_cumle)
    hazir_kanonik = _sureler(hazir_cumle)
    if len(ozel_kanonik) != 1:
        b5_hata.append("BEYAN['SAYFA_OZEL'] tek sure jetonu tasimiyor: %s"
                       % sorted(ozel_kanonik))
    if len(hazir_kanonik) != 1:
        b5_hata.append("BEYAN['SAYFA_HAZIR'] tek sure jetonu tasimiyor: %s"
                       % sorted(hazir_kanonik))
    for ad, h, kanonik in ([(a, x, ozel_kanonik) for a, x in ozel_dallar]
                           + [("hazir/stok", fiz_html, hazir_kanonik)]):
        g = _etiketsiz(_ana_govde(h))
        if not g:
            b5_hata.append("%s: BOLGE BOS" % ad)
            continue
        sayfa = _sureler(g)
        eksik = kanonik - sayfa
        fazla = sayfa - kanonik
        if eksik:
            b5_hata.append("%s: kanonik sure YOK (%s)" % (ad, sorted(eksik)))
        if fazla:
            b5_hata.append("%s: kanonik DISI sure (%s)" % (ad, sorted(fazla)))
        if RAKIP_SURE_RE.search(g):          # kara liste: ikinci savunma katmani
            b5_hata.append("%s: bilinen bayat aralik" % ad)
    for ad, h in ozel_dallar:                # sinif etiketi/cayma sozu sizmasi
        g = _etiketsiz(_ana_govde(h))
        if HAZIR_ETIKET_RE.search(g):
            b5_hata.append("%s: hazir sinif etiketi SIZDI" % ad)
        if CAYMA_RE.search(g):
            b5_hata.append("%s: cayma sozu SIZDI" % ad)
    ol("B5", "SURE: her sinif sayfasinda KANONIK jeton VAR, kanonik disinda sure YOK",
       not b5_hata, ("%s" % b5_hata) if b5_hata
       else "ozel=%s hazir=%s" % (sorted(ozel_kanonik), sorted(hazir_kanonik)))

    # B6 — CAPRAZ SIZMA, IKI YONLU. Iki sinif AYNI SAYIYI tasir ama AYNI GEREKCEYI
    # TASIMAZ: hazir uruNde "olcu onayi" asamasi YOKTUR. Yanlis yondeki sizma
    # (hazir mala ozel uretim gerekcesi) musterinin 14 gunluk cayma hakkini
    # reddetmeye yarayacak bir teyide donusur — 1 Agu'da olculen kusurun ta kendisi.
    b6_hata = []
    if not isinstance(beyan, dict) or not hazir_cumle or not ozel_cumle:
        b6_hata.append("BEYAN yok/eksik")
    else:
        fiz_bloklar = BEYAN_DIV_RE.findall(fiz_html)
        if fiz_bloklar != [mod.esc(hazir_cumle)]:
            b6_hata.append("hazir sayfada SAYFA_HAZIR blogu bayt-birebir DEGIL (%d adet)"
                           % len(fiz_bloklar))
        if mod.esc(ozel_cumle) in fiz_html:
            b6_hata.append("OZEL metni HAZIR sayfaya sizdi")
        if OLCU_ONAY_RE.search(fiz_govde):
            b6_hata.append("hazir sayfada OLCU ONAYI dili: %s"
                           % sorted(set(OLCU_ONAY_RE.findall(fiz_govde))))
        for ad, h in ozel_dallar:
            if mod.esc(hazir_cumle) in h:
                b6_hata.append("%s: HAZIR metni OZEL sayfaya sizdi" % ad)
    ol("B6", "IKI SINIF CAPRAZ SIZMIYOR: hazir sayfa hazir metnini, ozel sayfa ozel "
             "metnini tasir", not b6_hata, ("%s" % b6_hata) if b6_hata else "")

    # B7 — TETIKLEYICI CELISKISI (sayacin basladigi olay).
    # 🔴 NEDEN VAR (curutucu, 10 Agu): urun sayfasi "olcu onayindan sonra" derken
    # siparis onay e-postasi "siparisinizden sonra uretilir" diyordu. Ayni musteri
    # iki yuzeyde IKI FARKLI saat baslangici goruyordu ve HICBIR iddia bunu olcmuyordu.
    # Ustelik "olcu onayi" ozel uretim sinifinin %99,84'unde VAR OLMAYAN bir asamadir
    # (parametrik/konfigurlu yalniz 39 kayit) -> taahhudun saati HIC BASLAMAZ; ayrica
    # "olcuye ozel" damgasi m.15 cayma istisnasinin anahtar ifadesidir.
    # Iddia SINIF duzeyindedir: cumleler ayni olmak zorunda DEGIL, TETIKLEYICI SINIFI
    # ayni olmak zorunda.
    b7_hata = []
    if not ozel_cumle or not hazir_cumle:
        b7_hata.append("BEYAN yok/eksik")
    else:
        sayfa_ozel_t = _tetikleyiciler(ozel_cumle)
        eposta_ozel_t = (_tetikleyiciler(beyan.get("SATIR_OZEL", ""))
                         | _tetikleyiciler(beyan.get("EPOSTA_ODENDI_OZEL", "")))
        if not sayfa_ozel_t:
            b7_hata.append("ozel urun sayfasi beyaninda TETIKLEYICI YOK (sayac baslangici belirsiz)")
        if not eposta_ozel_t:
            b7_hata.append("ozel e-posta/satir beyaninda TETIKLEYICI YOK")
        if sayfa_ozel_t and eposta_ozel_t and sayfa_ozel_t != eposta_ozel_t:
            b7_hata.append("OZEL sinif CELISKI: urun sayfasi=%s · siparis e-postasi=%s"
                           % (sorted(sayfa_ozel_t), sorted(eposta_ozel_t)))
        # Hazir kol: urun sayfasi <-> baglayici yasal stok cumlesi.
        sayfa_hazir_t = _tetikleyiciler(hazir_cumle)
        stok_t = _tetikleyiciler(getattr(sayfalar, "STOK_TESLIM_CUMLESI", "") or "")
        if not sayfa_hazir_t:
            b7_hata.append("hazir urun sayfasi beyaninda TETIKLEYICI YOK")
        if sayfa_hazir_t and stok_t and sayfa_hazir_t != stok_t:
            b7_hata.append("HAZIR sinif CELISKI: urun sayfasi=%s · yasal stok cumlesi=%s"
                           % (sorted(sayfa_hazir_t), sorted(stok_t)))
        # Ozel uretim urun sayfasina "olcu onayi/olcuye ozel" damgasi BASILMAZ.
        for ad, h in ozel_dallar:
            g = _etiketsiz(_ana_govde(h))
            blok = " ".join(BEYAN_DIV_RE.findall(h))
            if TETIK_OLCU_RE.search(blok) or OLCU_ONAY_RE.search(blok):
                b7_hata.append("%s: sinif beyaninda OLCU ONAYI/OLCUYE OZEL damgasi" % ad)
            if not g:
                b7_hata.append("%s: BOLGE BOS" % ad)
    ol("B7", "TETIKLEYICI CELISMIYOR: urun sayfasi ile siparis e-postasi (ozel) ve "
             "yasal stok cumlesi (hazir) AYNI olayi gosteriyor",
       not b7_hata, ("%s" % b7_hata) if b7_hata
       else "ozel=%s hazir=%s" % (sorted(_tetikleyiciler(ozel_cumle or "")),
                                  sorted(_tetikleyiciler(hazir_cumle or ""))))

    # B8 — HAK REDDI DILI (B2'nin POZITIF ikizi). Urun sayfasi hakkin KAPSAMINI
    # daraltan bir cumle TASIMAZ: "iade hakkiniz yoktur" gibi bir ifade, m.15
    # istisnasini urun bazinda dayatir ve hazir/stok sinifinda dogrudan yanlistir.
    # Kapsam IKI SINIF birden — hazir sayfada "cayma hakkiniz VARDIR" duruyor,
    # desen yalnizca REDDI yakalar.
    b8_hata = []
    for ad, h in ozel_dallar + [("hazir/stok", fiz_html)]:
        g = _etiketsiz(_ana_govde(h))
        if not g:
            b8_hata.append("%s: BOLGE BOS" % ad)
            continue
        v = HAK_REDDI_RE.findall(g)
        if v:
            b8_hata.append("%s: hak REDDI dili %s" % (ad, sorted({str(x) for x in v})[:3]))
    ol("B8", "urun sayfasinda HAK REDDI dili YOK ('iade/cayma hakkiniz yoktur' vb.)",
       not b8_hata, ("%s" % b8_hata) if b8_hata else "%d sayfa" % (len(ozel_dallar) + 1))

    # B9 — YANLIS-POZITIF KONTROL FIKSTURU (GERCEK katalogdan).
    # 🔴 NEDEN VAR: sinif kelimeleri NEGATIF iddialarda kullaniliyor (A3/B2/B5); bir
    # yanlis-pozitif TUM EKIBIN yayinini durdurur. Gercek katalogda olculdu:
    #   "Porsche Boxster & Cayman ..."  -> gevsek r"cayma" 2 uruNde eslesiyordu
    #   "Nissan Rogue 2014 Güneşlik ..." -> gevsek r"14\s*gün" eslesiyordu
    # Iddia POZITIF TANIMA IZI tasir: desenler bu iki metinde eslesMEmeli AMA
    # gercek beyan cumlelerinde eslesMELI (yoksa "hic eslesmeyen desen" de gecerdi
    # -> [[olculdu-diyen-hukum-kaniti]]).
    b9_hata = []
    yp_urun = _urun("sinama-yanlis-pozitif", kategori="Otomobil", ek={
        "baslik": "Porsche Boxster & Cayman (981) Güneşlik Sabitleme Klipsi",
        "aciklama": "Nissan Rogue 2014 Güneşlik Tutucu Klipsi ile ayni yuvaya oturur.\n"
                    "Ikinci satir."})
    yp_html = mod.render_product(yp_urun, tum)
    # KAPSAM: URUNUN KENDI METNI. Sinif beyani blogu bilerek CIKARILIR — iddia
    # "beyan cumlesinde cayma geciyor mu" DEGIL, "urun basligi/aciklamasindaki
    # 'Cayman' ve '2014 Güneşlik' sinif kelimelerine YANLIS eslesiyor mu"dur.
    # Blok icerde birakilsaydi, beyani bozan bir mutant bu ekseni de dusurur ve
    # yanlis-pozitif nobetinin kendi olcusu baska bir kusurla KARISIRDI.
    yp_govde = _etiketsiz(BEYAN_DIV_RE.sub(" ", _ana_govde(yp_html)))
    if not ("Cayman" in yp_govde and "2014 Güneşlik" in yp_govde):
        b9_hata.append("KONTROL FIKSTURU SAYFAYA BASILMAMIS (olcum yapilamadi)")
    if CAYMA_RE.search(yp_govde):
        b9_hata.append("CAYMA_RE 'Cayman'a eslesiyor (yanlis-pozitif)")
    if ONDORT_GUN_RE.search(yp_govde):
        b9_hata.append("ONDORT_GUN_RE '2014 Güneşlik'e eslesiyor (yanlis-pozitif)")
    # POZITIF TANIMA IZI: ayni desenler GERCEK beyan cumlelerinde eslesmeli.
    if not CAYMA_RE.search(hazir_cumle or ""):
        b9_hata.append("CAYMA_RE gercek hazir beyaninda ESLESMIYOR (desen olmus)")
    if not ONDORT_GUN_RE.search(hazir_cumle or ""):
        b9_hata.append("ONDORT_GUN_RE gercek hazir beyaninda ESLESMIYOR (desen olmus)")
    ol("B9", "YANLIS-POZITIF: 'Porsche Cayman' + '2014 Güneşlik' sinif kelimelerine "
             "eslesMIYOR, gercek beyanda eslesIYOR", not b9_hata,
       ("%s" % b9_hata) if b9_hata else "2 gercek katalog vakasi")

    # ================================================== C — TESLIMAT / SOZLESME
    rapor.append("C) TESLIMAT + MESAFELI SATIS (tools/sayfalar.py)")
    tes = _etiketsiz(sayfalar._teslimat_iade())
    mes = _etiketsiz(sayfalar._mesafeli_satis())
    stok_cumle = getattr(sayfalar, "STOK_TESLIM_CUMLESI", None)
    stok_duz = _etiketsiz(stok_cumle) if isinstance(stok_cumle, str) else None
    ol("C1", "teslimat-iade teslimat kolu IKI SINIFLI (stok kolunda 'olcu onayi' dayatilmiyor)",
       bool(stok_duz) and stok_duz in tes,
       "" if (stok_duz and stok_duz in tes) else "sayfalar.STOK_TESLIM_CUMLESI=%r" % stok_cumle)
    ol("C2", "mesafeli-satis m.4 ayni ayrimi tasiyor",
       bool(stok_duz) and stok_duz in mes)
    ol("C3", "iki govdede de 14 gun cayma + m.15 istisnasi duruyor (regresyon)",
       all(ONDORT_GUN_RE.search(g) and CAYMA_RE.search(g) and "m.15" in g for g in (tes, mes)))
    c4 = [ad for ad, g in (("teslimat-iade", tes), ("mesafeli-satis", mes))
          if IADE_KARGO_DESENI.search(g)]
    ol("C4", "iade kargo bedeli cumlesi YAZILMAMIS (Okan cevabi BEKLENIYOR)", not c4,
       ("yazilmis: %s" % c4) if c4 else "")
    # Desen MODUL duzeyinde TEK TANIM (RAKIP_SURE_RE) — B5 ayni desenden turer.
    ol("C5", "iki govdede de '3-5 is gunu' duruyor, rakip aralik yok (regresyon)",
       all("3-5 iş günü" in g and not RAKIP_SURE_RE.search(g) for g in (tes, mes)))

    # C6 — BAGLAYICI YASAL GOVDE ile URUN SAYFASI SURESI AYNI.
    # 🔴 NEDEN VAR (curutucu, 10 Agu): sayfalar.py stok cumlesindeki sure "7-10 is
    # gunu"na kaydirildiginda hicbir kapi gormedi. C5 yalniz "3-5 var mi + bilinen
    # bayat aralik var mi" diye bakiyor; YENI bir aralik EKLENMESI onun kor noktasi.
    # Iddia KUME ESITLIGIDIR: yasal govdelerdeki sure jetonlari = urun sayfasi
    # beyanlarinin sure jetonlari. Iki sinif ileride FARKLI sayi tasirsa da calisir
    # (kume ikisini de icerir), ama govdeye BEYAN DISI bir sure girerse KIRMIZI.
    sayfa_sureleri = _sureler(ozel_cumle or "") | _sureler(hazir_cumle or "")
    govde_sureleri = _sureler(tes) | _sureler(mes)
    c6_hata = []
    if not sayfa_sureleri:
        c6_hata.append("urun sayfasi beyanlarinda sure jetonu YOK")
    if not govde_sureleri:
        c6_hata.append("yasal govdelerde sure jetonu YOK (bos kume)")
    if sayfa_sureleri and govde_sureleri and sayfa_sureleri != govde_sureleri:
        c6_hata.append("AYRISMA: urun sayfasi=%s · yasal govde=%s"
                       % (sorted(sayfa_sureleri), sorted(govde_sureleri)))
    stok_sureleri = _sureler(stok_cumle if isinstance(stok_cumle, str) else "")
    if stok_sureleri and not stok_sureleri <= sayfa_sureleri:
        c6_hata.append("stok teslim cumlesi urun sayfasi disinda sure tasiyor: %s"
                       % sorted(stok_sureleri - sayfa_sureleri))
    ol("C6", "yasal baglayici govde ile urun sayfasi teslim SURESI ayni (kume esitligi)",
       not c6_hata, ("%s" % c6_hata) if c6_hata
       else "sayfa=%s govde=%s" % (sorted(sayfa_sureleri), sorted(govde_sureleri)))

    # ================================================== D — ODEME EKRANI
    rapor.append("D) ODEME EKRANI (index.html + secenekler.js saf fonksiyonlari)")
    s = probe["sinif"]
    ol("D1", "sepetSinifi() uc sinifi ayiriyor; bos sepet + taninmayan `tur` -> 'ozel'",
       bool(s) and s == {"bos": "ozel", "hepsi_ozel": "ozel", "hepsi_hazir": "hazir",
                         "karma": "karma", "taninmayan": "ozel"},
       "" if s else "sepetSinifi YOK", )
    od, hk, cy = probe["odeme"], probe["havaleKutu"], probe["cayma"]
    ol("D2", "odemeBeyani('ozel') + havaleKutuBeyani('ozel') bugunku metni AYNEN veriyor; "
             "caymaBeyani('ozel') BOS",
       bool(od) and bool(hk) and bool(cy is not None)
       and od["ozel_havale"] == CAPA_ODEME_HAVALE_OZEL
       and hk["ozel"] == CAPA_HAVALE_KUTU_OZEL
       and cy["ozel"] == "",
       "" if (od and hk and cy is not None) else "fonksiyon YOK")
    d3 = (bool(od) and bool(hk) and bool(cy)
          and not URETIM_DILI.search(od["hazir_havale"])
          and not URETIM_DILI.search(hk["hazir"])
          and not URETIM_DILI.search(cy["hazir"])
          and bool(ONDORT_GUN_RE.search(cy["hazir"])) and bool(CAYMA_RE.search(cy["hazir"])))
    ol("D3", "hazir sepette odeme/havale/cayma metninde URETIM DILI YOK, 14 gun VAR", d3,
       "" if (od and hk and cy) else "fonksiyon YOK")
    ol("D4", "karma sepette iki sinif da soyleniyor (odeme + cayma metni)",
       bool(od) and bool(cy) and bool(HAZIR_ETIKET_RE.search(od["karma_havale"]))
       and bool(OZEL_ETIKET_RE.search(od["karma_havale"]))
       and bool(HAZIR_ETIKET_RE.search(cy["karma"]))
       and bool(OZEL_ETIKET_RE.search(cy["karma"])))
    ol("D5", "FAIL-CLOSED: taninmayan sinif adi -> 'ozel' metni (bugunku davranis)",
       bool(od) and bool(hk) and bool(cy is not None)
       and od["bilinmeyen_havale"] == CAPA_ODEME_HAVALE_OZEL
       and hk["bilinmeyen"] == CAPA_HAVALE_KUTU_OZEL and cy["bilinmeyen"] == "")
    with open(INDEX_YOL, encoding="utf-8") as f:
        index_src = f.read()
    betik = _inline_script(index_src)
    eksik_cagri = [ad for ad in ("sepetSinifi(", "odemeBeyani(", "havaleKutuBeyani(",
                                 "caymaBeyani(")
                   if ad not in betik]
    ol("D6", "index.html satir-ici betigi bu fonksiyonlari FIILEN CAGIRIYOR",
       bool(betik) and not eksik_cagri,
       ("eksik cagri: %s" % eksik_cagri) if (betik and eksik_cagri)
       else ("" if betik else "satir-ici betik bulunamadi"))
    index_elle = re.findall(r'[=!]==\s*"fiziksel"|"fiziksel"\s*[=!]==', betik)
    ol("D7", "index.html sinif kararini elle TEKRARLAMIYOR", not index_elle,
       ("elle karsilastirma: %s" % index_elle) if index_elle else "")

    # ================================================== E — TEK KAYNAK / IKIZ
    rapor.append("E) TEK KAYNAK (secenekler.js BEYAN · ikiz tanim sessizce ayrisamaz)")
    # KAYNAK: FIILEN DERLENEN metin (build.py mutantinda diskteki dosya DEGIL o metin
    # yargilanir; yoksa mutant kaynak duzeyindeki iddialari sessizce atlatirdi).
    build_src = getattr(mod, "_KAPI_BUILD_KAYNAK", None)
    if build_src is None:
        with open(BUILD_YOL, encoding="utf-8") as f:
            build_src = f.read()
    ol("E1", "secenekler.js BEYAN sozlugu var ve build.py onu _js_sabiti ile OKUYOR",
       isinstance(beyan, dict) and bool(beyan)
       and '_js_sabiti(_SEC_JS, "BEYAN")' in build_src,
       "" if isinstance(beyan, dict) else "BEYAN=%r" % (beyan,))
    if isinstance(beyan, dict):
        sayfa_cumle = _etiketsiz(beyan.get("SAYFA_HAZIR", ""))
        ol("E2", "urun sayfasi beyani BEYAN['SAYFA_HAZIR'] ile BIREBIR ayni",
           bool(sayfa_cumle) and sayfa_cumle in fiz_govde,
           "" if sayfa_cumle else "SAYFA_HAZIR bos")
        eposta_cumle = _etiketsiz(beyan.get("EPOSTA_ODENDI_HAZIR", ""))
        ol("E3", "hazir e-postasi BEYAN['EPOSTA_ODENDI_HAZIR'] ile BIREBIR ayni",
           bool(eposta_cumle) and eposta_cumle in hazir_kart_duz,
           "" if eposta_cumle else "EPOSTA_ODENDI_HAZIR bos")
        # Python tarafi AYNI sozlugu okuyabiliyor mu (build.py'nin _js_sabiti yolu)?
        # 🔴 KAYNAK, OLCULEN MODULUN OKUDUGU DOSYADIR — sabit yol DEGIL. Sabit yola
        # bakilirsa kapi, modulun fiilen tukettigi dosyayi degil kendi varsayimini
        # olcer; olculdu: tek kaynagi degistiren mutant ailesinde E4 "ayrisma" diye
        # SAHTE KIRMIZI verdi ve kontrol mutantini da dusurdu.
        sec_yolu = getattr(mod, "SECENEKLER_JS", SECENEKLER_YOL)
        py_beyan = None
        try:
            m = re.search(r"var\s+BEYAN\s*=\s*(\{.*?\});",
                          open(sec_yolu, encoding="utf-8").read(), re.S)
            py_beyan = json.loads(m.group(1)) if m else None
        except Exception as e:                                     # noqa: BLE001
            py_beyan = "AYRISTIRILAMADI: %s" % e
        # Ayrica build.py'nin URETIMDE kullandigi sozlugun ta kendisi (mod.BEYAN)
        # JS calisma zamani degeriyle ayni mi — bu, iki tarafin GERCEK karsilastirmasi.
        uretim_beyan = getattr(mod, "BEYAN", None)
        ol("E4", "BEYAN Python (build.py) ve JS (worker/site) tarafinda AYNI degeri veriyor",
           py_beyan == beyan and uretim_beyan == beyan,
           "" if (py_beyan == beyan and uretim_beyan == beyan)
           else "python=%r uretim=%r" % (py_beyan, uretim_beyan))
        # E5 — TESLIM BEYANI TEK KAYNAKTAN: **DAVRANISSAL** olcum.
        # 🔴 NEDEN DEGISTI (curutucu, 10 Agu): E5 once yalniz KAYNAK TARIYORDU.
        # Curutucu `esc(BEYAN["SAYFA_OZEL"])` cagrisini kacis dizeleriyle ("Ö...")
        # yazilmis modul duzeyi bir ikize cevirdi; geriye metin YALNIZCA YORUM
        # satirinda kaldi, kapi rc=0 verdi ve hicbir iddia dusmedi. Yani "BEYAN'i
        # OKUYOR" ayagi bir YORUMLA, "sabit kopya YOK" ayagi kacis/birlestirmeyle
        # atlatilabiliyordu ([[hukum-ezme-sozdiziminde-karar-verilemez]]).
        # ASIL AYAK ARTIK DAVRANISSAL: tek kaynaktaki (secenekler.js BEYAN) deger
        # calisma zamaninda degistirilir ve build.py'nin URETTIGI ciktinin da
        # degistigi olculur. Sozdizimsel hicbir kacis bu olcumu gecemez.
        e5_hata = []
        if not ozel_cumle or not hazir_cumle:
            e5_hata.append("SAYFA_OZEL/SAYFA_HAZIR bos")
        else:
            damga = "ZZ-TEK-KAYNAK-SINAMASI-ZZ"
            sinama_beyan = dict(beyan)
            sinama_beyan["SAYFA_OZEL"] = ozel_cumle + " " + damga
            sinama_beyan["SAYFA_HAZIR"] = hazir_cumle + " " + damga
            ged, sec_yol, _ = _secenekler_beyanli(sinama_beyan)
            if sec_yol is None:
                e5_hata.append("secenekler.js BEYAN blogu ayristirilamadi (olculemedi)")
            else:
                try:
                    sinama_mod = _build_baska_secenekle(build_src, sec_yol)
                    if sinama_mod is None:
                        e5_hata.append("SECENEKLER_JS capasi bulunamadi (olculemedi)")
                    else:
                        o_html = sinama_mod.render_product(nrm, tum)
                        h_html = sinama_mod.render_product(fiz, tum)
                        if damga not in o_html:
                            e5_hata.append("OZEL cikti tek kaynagi IZLEMIYOR "
                                           "(sabit kopya/ikiz suruyor)")
                        if damga not in h_html:
                            e5_hata.append("HAZIR cikti tek kaynagi IZLEMIYOR "
                                           "(sabit kopya/ikiz suruyor)")
                except Exception as exc:                            # noqa: BLE001
                    e5_hata.append("davranissal olcum COKTU: %s" % str(exc)[:90])
                finally:
                    if ged:
                        shutil.rmtree(ged, ignore_errors=True)
            # IKINCI KATMAN (tek basina kabul DEGIL): kaynakta sabit kopya izi.
            # YORUMLAR SOYULUR — yorum bir iddiayi tatmin edemez.
            src_yorumsuz = _yorumsuz(build_src)
            if ozel_cumle in src_yorumsuz or hazir_cumle in src_yorumsuz:
                e5_hata.append("cumle build.py'ye (yorum disi) SABIT KOPYA yazilmis")
        ol("E5", "urun sayfasi teslim beyani TEK KAYNAGI IZLIYOR (davranissal: BEYAN "
                 "degisince cikti degisiyor) + kaynakta sabit kopya YOK",
           not e5_hata, ("%s" % e5_hata) if e5_hata else "damga iki sinifta da izlendi")
    else:
        ol("E2", "urun sayfasi beyani BEYAN['SAYFA_HAZIR'] ile BIREBIR ayni", False, "BEYAN yok")
        ol("E3", "hazir e-postasi BEYAN['EPOSTA_ODENDI_HAZIR'] ile BIREBIR ayni", False,
           "BEYAN yok")
        ol("E4", "BEYAN Python ve JS tarafinda AYNI degeri veriyor", False, "BEYAN yok")
        ol("E5", "urun sayfasi teslim beyani BEYAN'dan OKUNUYOR", False, "BEYAN yok")

    return hatalar, rapor


# --------------------------------------------------------------------------- mutasyon
# Her mutant DAR bir probe'dur: eposta.js'in SINIF KARARINI no-op eder ve hangi iddialarin
# dusmesi gerektigi ONCEDEN yazilir. Baska bir eksen dusuyorsa probe genistir = hata.
MUTANTLAR = [
    ('  return S.sepetSinifi((satirlar || []).map((s) => (s || {}).tur));',
     '  return "ozel";',
     "sepet sinifi DAIMA ozel -> hazir/karma sepet eski kosulsuz metni alir",
     ("A4", "A5", "A6", "A7", "A8", "E3")),
    ('  return S.sepetSinifi((satirlar || []).map((s) => (s || {}).tur));',
     '  return "hazir";',
     "sepet sinifi DAIMA hazir -> 15.930 ozel uretim siparisi hazir-urun beyani alir",
     ("A1", "A2", "A3")),
    ('kac(S.satirBeyani(s && s.tur))', 'kac(S.BEYAN.SATIR_OZEL)',
     "kalem etiketi sinifi bilmiyor -> hazir kalem 'Özel üretim' diye isaretlenir",
     ("A4", "A5", "A7")),
]


# --- build.py MUTANTLARI — URUN SAYFASI TESLIM BEYANI (B4/B5/B6/E5) icin.
# Bicim: (capa, yeni_uretici(beyan) -> metin, aciklama, DUSMESI BEKLENEN iddialar).
# 🔴 KABUL BURADA DAHA KATI: beklenen iddialarin HEPSI dusmeli VE beklenen disinda
# hicbir iddia dusmemeli. "En az biri dustu" olcutu, iddialarin VEYA'sini olcer ve
# tek tek olduruculugu kanitlamaz ([[beyan-edilmis-survivor]]).
# 🔴 CUMLE BU DOSYAYA YAZILMAZ: sabit-kopya mutanti cumleyi CALISMA ZAMANINDA
# BEYAN'dan uretir — yoksa nobetci kendi dosyasinda ikinci bir tanim tasirdi
# ([[nobetci-kendi-dosyasinda-sizinti]]).
BUILD_MUTANTLARI = [
    # Taahhut TAMAMEN silinir. Uc bagimsiz eksen birden duser ve DUSMELIDIR:
    # B4 (varlik), B5 (kanonik sure POZITIF sarti), E5 (cikti artik tek kaynagi
    # izlemiyor — damga ciktida hic gorunmuyor).
    ('ozel_beyan=("" if fiziksel else OZEL_TESLIM_BEYAN_HTML),',
     lambda b: 'ozel_beyan="",',
     "ozel uretim sayfasina teslim beyani HIC basilmaz (23.968 sayfa beyansiz)",
     ("B4", "B5", "E5")),
    ('ozel_beyan=("" if fiziksel else OZEL_TESLIM_BEYAN_HTML),',
     lambda b: 'ozel_beyan=OZEL_TESLIM_BEYAN_HTML,',
     "sinif kapisi kalkar -> ozel uretim gerekcesi HAZIR/STOK sayfasina da sizar",
     ("B6",)),
    ('\') % esc(BEYAN["SAYFA_OZEL"])',
     lambda b: '\') % esc(BEYAN["SAYFA_OZEL"].replace("3-5", "2-4"))',
     "teslim araligi BILINEN bayat degere kayar (3-5 -> 2-4 is gunu)",
     ("B4", "B5")),
    # 🔴 KARA LISTE DISI VARYANT — B5'in asil sinavi. Sayili kara liste (5-7|3-6|2-4)
    # bunu GORMEZ; kabul KANONIK KUME uzerinden verilmek zorunda.
    ('\') % esc(BEYAN["SAYFA_OZEL"])',
     lambda b: '\') % esc(BEYAN["SAYFA_OZEL"].replace("3-5", "10-20"))',
     "teslim araligi KARA LISTE DISI degere kayar (3-5 -> 10-20 is gunu)",
     ("B4", "B5")),
    # HAZIR kolun suresi kayar — sozlesme 3-5 derken sayfa 15-30 der.
    ('beyan=esc(BEYAN["SAYFA_HAZIR"]))',
     lambda b: 'beyan=esc(BEYAN["SAYFA_HAZIR"].replace("3-5", "15-30")))',
     "HAZIR/STOK sayfasinin suresi kayar (3-5 -> 15-30 is gunu; sozlesme 3-5 diyor)",
     ("B5", "B6", "E2")),
    # HAK REDDI urun sayfasina sizar — m.15 istisnasini urun bazinda dayatan cumle.
    ('ozel_beyan=("" if fiziksel else OZEL_TESLIM_BEYAN_HTML),',
     lambda b: ('ozel_beyan=("" if fiziksel else OZEL_TESLIM_BEYAN_HTML'
                ' + "<p>Bu üründe iade hakkınız yoktur.</p>"),'),
     "urun sayfasina HAK REDDI cumlesi eklenir ('iade hakkiniz yoktur')",
     ("B8",)),
    # 🔴 KACIS IKIZI — curutucunun 10 Agu'da kapiyi gectigi mutant. Cumle build.py'ye
    # UNICODE KACIS DIZILERIYLE yazilir: kaynak taramasi HICBIR SEY gormez, cikti
    # bayt-bayt AYNI kalir. Yalnizca E5'in DAVRANISSAL ayagi (tek kaynagi degistirip
    # ciktinin izledigini olcmek) bunu yakalayabilir.
    ('esc(BEYAN["SAYFA_OZEL"])',
     lambda b: "esc('%s')" % (b["SAYFA_OZEL"].encode("unicode_escape").decode("ascii")
                              .replace("'", "\\'")),
     "cumle build.py'ye KACIS DIZELI IKIZ olarak yazilir (kaynak taramasi kor; cikti AYNI)",
     ("E5",)),
    # CAPRAZ SIZMA — TERS YON (hazir metni OZEL sayfaya). Ozel uretim urununde
    # "14 gun cayma hakkiniz vardir" demek MUSTERIYE OLMAYAN BIR HAK BEYAN ETMEKTIR.
    ('esc(BEYAN["SAYFA_OZEL"])',
     lambda b: 'esc(BEYAN["SAYFA_HAZIR"])',
     "hazir/stok metni OZEL URETIM sayfasina sizar (olmayan cayma hakki beyan edilir)",
     # B2 de duser ve DUSMELIDIR: sizan cumle "Hazır ürün" + "cayma" kelimelerini
     # tasir, yani 1 Agu'dan beri duran regresyon capasi da bu sizmayi goruyor.
     ("B2", "B4", "B5", "B6")),
    # HAZIR KOLUN BAYT CAPASI CANLI MI: fiziksel dal baska bir BEYAN anahtarini
    # basarsa hazir sayfanin sinif beyani sessizce degisir.
    ('beyan=esc(BEYAN["SAYFA_HAZIR"]))',
     lambda b: 'beyan=esc(BEYAN["SATIR_HAZIR"]))',
     "hazir/stok sayfasi baska bir BEYAN anahtarini basar (cayma + teslim taahhudu duser)",
     ("B1", "B5", "B6", "E2", "E5")),
]

# KONTROL MUTANTLARI — masum degisiklik. Kapi bunlarda YESIL kalmali; kalmiyorsa
# iddialar GENIS (bicime capalanmis) demektir ve her bicim rotusu yayini durdurur.
BUILD_KONTROL_MUTANTLARI = [
    ('\'<div class="sinif-beyan" id="sinifBeyan" style="margin-top:10px;font-size:13px;',
     lambda b: '\'<div class="sinif-beyan" id="sinifBeyan" style="margin-top:12px;font-size:13px;',
     "masum bicim rotusu (ozel blok margin-top 10px -> 12px)"),
]

# --- tools/sayfalar.py MUTANTLARI — BAGLAYICI YASAL GOVDE (C6).
SAYFALAR_MUTANTLARI = [
    ('"3-5 iş günü içinde stoktan hazırlanıp kargoya verilir."',
     lambda b: '"7-10 iş günü içinde stoktan hazırlanıp kargoya verilir."',
     "yasal stok teslim cumlesinin suresi kayar (3-5 -> 7-10 is gunu)",
     ("C6",)),
]
SAYFALAR_KONTROL_MUTANTLARI = [
    ('STOK_TESLIM_CUMLESI = (',
     lambda b: 'STOK_TESLIM_CUMLESI  = (',
     "masum bicim rotusu (sayfalar.py bosluk)"),
]

# --- secenekler.js BEYAN MUTANTLARI — TEK KAYNAGIN KENDISI degisince ne olur?
# Bicim: (beyan -> yeni_beyan, aciklama, beklenen). Mutant JS DISKE yazilmaz, GECICI
# dizine yazilir; hem node probe'u hem build.py o kopyadan okur.
BEYAN_MUTANTLARI = [
    (lambda b: dict(b, SAYFA_OZEL=TETIK_SIPARIS_RE.sub("ölçü onayından", b["SAYFA_OZEL"])),
     "urun sayfasi tetikleyicisi 'olcu onayindan sonra'ya geri cevrilir "
     "(var olmayan asama + siparis e-postasiyla CELISKI)",
     ("B7",)),
]
BEYAN_KONTROL_MUTANTLARI = [
    (lambda b: dict(b, SAYFA_OZEL=b["SAYFA_OZEL"].replace(" — ", " - ")),
     "masum noktalama rotusu (uzun tire -> kisa tire); tetikleyici + sure AYNI"),
]


def _hukum_yaz(aciklama, etiketler, beklenen, kontrol):
    """Tek mutantin hukmunu basar; True = mutant BEKLENDIGI GIBI davrandi."""
    dusen = [e for e in etiketler if e in beklenen]
    dusmeyen = [e for e in beklenen if e not in etiketler]
    eksen_disi = [e for e in etiketler if e not in beklenen]
    print("  mutant: %s" % aciklama)
    if kontrol:
        print("    beklenen: HICBIR iddia dusmemeli | dusen: %s -> %s"
              % (etiketler or "-",
                 "YESIL ✔" if not etiketler else "KIRMIZI ✘ (IDDIA GENIS)"))
    else:
        print("    beklenen=%s | dusen=%s | DUSMEYEN=%s | eksen disi=%s -> %s"
              % (list(beklenen), dusen or "-", dusmeyen or "-", eksen_disi or "-",
                 "OLDU ✔" if (not dusmeyen and not eksen_disi) else "KALDI ✘"))
    return not (dusmeyen or eksen_disi)


def _kaynak_mutant_turu(baslik, kaynak, mutantlar, kur, beyan, kontrol=False):
    """KAYNAK METNI bozan mutant ailesi (build.py / sayfalar.py).

    `kur(mutant_kaynak)` -> (probe, mod, sayfalar) uclusunu dondurur; mutant DISKE
    YAZILMAZ, dogrudan derlenir ([[mutasyon-diske-yazma-tuzagi]] +
    [[mutasyon-bytecode-onbellegi]] ikisi birden devre disi).
    Doner: (tamam_mi, olculen_iddia_sayisi)."""
    print("=== %s" % baslik)
    tamam, olculen = True, 0
    for giris in mutantlar:
        if kontrol:
            capa, uret, aciklama = giris
            beklenen = ()
        else:
            capa, uret, aciklama, beklenen = giris
        if kaynak.count(capa) != 1:
            print("  MUTASYON CAPASI KAYIP/COKLU (%d adet): %r" % (kaynak.count(capa), capa))
            tamam = False
            continue
        mut_kaynak = kaynak.replace(capa, uret(beyan), 1)
        if mut_kaynak == kaynak:
            print("  MUTANT UYGULANMADI (metin degismedi): %s" % aciklama)
            tamam = False
            continue
        try:
            probe, mod, sayfalar = kur(mut_kaynak)
            hatalar, _ = kosum(probe, mod, sayfalar)
        except Exception as e:                                          # noqa: BLE001
            # COKME KIRMIZIYLA KARISIR: mutant patlarsa iddia OLCULMEMISTIR.
            print("  mutant COKTU -> iddia OLCULEMEDI (%s): %s" % (aciklama, e))
            tamam = False
            continue
        etiketler = sorted({h.split()[0] for h in hatalar})
        olculen += len(beklenen) if not kontrol else 1
        if not _hukum_yaz(aciklama, etiketler, beklenen, kontrol):
            tamam = False
    print()
    return tamam, olculen


def _beyan_mutant_turu(baslik, build_kaynak, mutantlar, sayfalar, beyan, kontrol=False):
    """TEK KAYNAGIN KENDISINI (secenekler.js BEYAN) bozan aile.

    Mutant sozluk gecici bir secenekler.js kopyasina yazilir; node probe'u DA build.py
    DA o kopyadan okur -> iki yuzey ayni kaynagi gorur ve "cumleler ayristi mi" degil
    "SINIF/TETIKLEYICI celisiyor mu" olculur."""
    print("=== %s" % baslik)
    tamam, olculen = True, 0
    for giris in mutantlar:
        if kontrol:
            uret, aciklama = giris
            beklenen = ()
        else:
            uret, aciklama, beklenen = giris
        yeni_beyan = uret(beyan)
        if yeni_beyan == beyan:
            print("  MUTANT UYGULANMADI (BEYAN degismedi): %s" % aciklama)
            tamam = False
            continue
        ged, sec_yol, ep_yol = _secenekler_beyanli(yeni_beyan)
        if sec_yol is None:
            print("  secenekler.js BEYAN blogu ayristirilamadi -> OLCULEMEDI")
            tamam = False
            continue
        try:
            probe = probe_calistir(secenekler_yol=sec_yol, eposta_yol=ep_yol)
            mod = _build_baska_secenekle(build_kaynak, sec_yol)
            if mod is None:
                print("  SECENEKLER_JS capasi bulunamadi -> OLCULEMEDI")
                tamam = False
                continue
            hatalar, _ = kosum(probe, mod, sayfalar)
        except Exception as e:                                          # noqa: BLE001
            print("  mutant COKTU -> iddia OLCULEMEDI (%s): %s" % (aciklama, e))
            tamam = False
            continue
        finally:
            shutil.rmtree(ged, ignore_errors=True)
        etiketler = sorted({h.split()[0] for h in hatalar})
        olculen += len(beklenen) if not kontrol else 1
        if not _hukum_yaz(aciklama, etiketler, beklenen, kontrol):
            tamam = False
    print()
    return tamam, olculen


def mutasyon_kosumu():
    print("=== MUTASYON: eposta.js sinif karari no-op edilince kapi KIRMIZI mi?")
    with open(EPOSTA_YOL, encoding="utf-8") as f:
        kaynak = f.read()
    mod = build_modulu()
    sayfalar = sayfalar_modulu()
    tamam = True
    for eski, yeni, aciklama, beklenen in MUTANTLAR:
        if kaynak.count(eski) != 1:
            print("  MUTASYON CAPASI KAYIP/COKLU (%d adet): %r" % (kaynak.count(eski), eski))
            tamam = False
            continue
        # Mutant DEPOYA YAZILMAZ: gecici agac kurulur (secenekler.js kopyasi + mutant
        # eposta.js), boylece "../../secenekler.js" goreli import'u cozulur.
        ged = tempfile.mkdtemp(prefix="cayma-mutant-")
        try:
            shutil.copyfile(SECENEKLER_YOL, os.path.join(ged, "secenekler.js"))
            src_dizin = os.path.join(ged, "shop", "src")
            os.makedirs(src_dizin)
            mut_yol = os.path.join(src_dizin, "eposta.js")
            with open(mut_yol, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(eski, yeni, 1))
            probe = probe_calistir(eposta_yol=mut_yol)
            hatalar, _ = kosum(probe, mod, sayfalar)
        finally:
            shutil.rmtree(ged, ignore_errors=True)
        etiketler = sorted({h.split()[0] for h in hatalar})
        # Mutant YALNIZ eposta.js'i bozar; digerlerinin (B/C/D) durumu degismez, o yuzden
        # dusen kume BEKLENEN eksene INDIRGENIR ve o eksenin BOS OLMAMASI aranir.
        eksende = [e for e in etiketler if e in beklenen]
        disarida = [e for e in etiketler if e.startswith("A") and e not in beklenen]
        durum = "KIRMIZI ✔" if eksende else "YESIL ✘ (OLU IDDIA)"
        print("  mutant: %s -> %s" % (yeni, aciklama))
        print("    sonuc: %s | dusen A-iddialari eksende: %s | eksen disi A: %s"
              % (durum, eksende or "-", disarida or "-"))
        if not eksende or disarida:
            tamam = False
    print()

    # --- IKINCI AILE: urun sayfasi teslim beyani (build.py). Ayri aile cunku ayri
    # dosyayi bozar ve ayri iddialari (B4/B5/B6/E5) hedefler.
    with open(BUILD_YOL, encoding="utf-8") as f:
        build_kaynak = f.read()
    temiz_probe = probe_calistir()
    beyan = temiz_probe.get("beyan") or {}
    if not isinstance(beyan, dict) or "SAYFA_OZEL" not in beyan:
        print("=== MUTASYON-2: BEYAN['SAYFA_OZEL'] YOK -> urun sayfasi beyan mutantlari "
              "OLCULEMEDI (fail-closed KIRMIZI).")
        return 1
    with open(os.path.join(TOOLS, "sayfalar.py"), encoding="utf-8") as f:
        sayfalar_kaynak = f.read()

    def _kur_build(src):
        return temiz_probe, build_modulu(src), sayfalar

    def _kur_sayfalar(src):
        return temiz_probe, mod, sayfalar_modulu(src)

    b_tamam, b_olculen = _kaynak_mutant_turu(
        "MUTASYON-2: urun sayfasi TESLIM BEYANI (tools/build.py) olduruculugu",
        build_kaynak, BUILD_MUTANTLARI, _kur_build, beyan)
    s_tamam, s_olculen = _kaynak_mutant_turu(
        "MUTASYON-3: BAGLAYICI YASAL GOVDE (tools/sayfalar.py) olduruculugu",
        sayfalar_kaynak, SAYFALAR_MUTANTLARI, _kur_sayfalar, beyan)
    t_tamam, t_olculen = _beyan_mutant_turu(
        "MUTASYON-4: TEK KAYNAK (secenekler.js BEYAN) olduruculugu",
        build_kaynak, BEYAN_MUTANTLARI, sayfalar, beyan)

    kb_tamam, kb_olculen = _kaynak_mutant_turu(
        "MUTASYON-5a: KONTROL — build.py masum degisiklik (kapi YESIL kalmali)",
        build_kaynak, BUILD_KONTROL_MUTANTLARI, _kur_build, beyan, kontrol=True)
    ks_tamam, ks_olculen = _kaynak_mutant_turu(
        "MUTASYON-5b: KONTROL — sayfalar.py masum degisiklik (kapi YESIL kalmali)",
        sayfalar_kaynak, SAYFALAR_KONTROL_MUTANTLARI, _kur_sayfalar, beyan, kontrol=True)
    kt_tamam, kt_olculen = _beyan_mutant_turu(
        "MUTASYON-5c: KONTROL — BEYAN masum noktalama (kapi YESIL kalmali)",
        build_kaynak, BEYAN_KONTROL_MUTANTLARI, sayfalar, beyan, kontrol=True)

    kontrol_tamam = kb_tamam and ks_tamam and kt_tamam
    kontrol_sayisi = kb_olculen + ks_olculen + kt_olculen
    tamam = tamam and b_tamam and s_tamam and t_tamam and kontrol_tamam
    print("OLCULEN: eposta %d mutant · build %d mutant (%d iddia) · sayfalar %d mutant "
          "(%d iddia) · BEYAN %d mutant (%d iddia) · KONTROL %d mutant"
          % (len(MUTANTLAR), len(BUILD_MUTANTLARI), b_olculen,
             len(SAYFALAR_MUTANTLARI), s_olculen,
             len(BEYAN_MUTANTLARI), t_olculen, kontrol_sayisi))
    print("MUTASYON: %s" % ("GECTI — sinif karari, teslim beyani, yasal govde suresi ve "
                            "tek kaynak bozulunca kapi KIRMIZI yaniyor; masum rotusta "
                            "YESIL kaliyor."
                            if tamam else "KALDI — iddia OLU, probe genis ya da "
                                          "kontrol mutanti kirmizi yakti."))
    return 0 if tamam else 1


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Cayma hakki sinif beyani kapisi")
    ap.add_argument("--mutasyon", action="store_true",
                    help="eposta.js sinif kararini no-op edip kapinin KIRMIZI yandigini kanitla")
    args = ap.parse_args()

    os.chdir(ROOT)
    if args.mutasyon:
        return mutasyon_kosumu()

    probe = probe_calistir()
    mod = build_modulu()
    sayfalar = sayfalar_modulu()
    hatalar, rapor = kosum(probe, mod, sayfalar)

    print("=== CAYMA BEYANI KAPISI (hazir/stok vs ozel uretim ayrimi BEYAN yolunda)")
    for s in rapor:
        print(s)
    print()
    if hatalar:
        print("KIRMIZI — %d iddia ihlal edildi:" % len(hatalar))
        for h in hatalar:
            print("  ✘ " + h)
        return 1
    print("YESIL — sinif ayrimi dort beyan yuzeyinde de yasiyor; 15.930 ozel uretim "
          "kaydinda regresyon YOK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
