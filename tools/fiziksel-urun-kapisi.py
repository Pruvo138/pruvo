#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FIZIKSEL URUN KAPISI — hazir ticari mal sayfasindan 3D-BASKI SECIM ARAYUZUNUN
kaldirildigini ve KARSILIGI OLMAYAN +%15 renk farkinin ULASILAMAZ oldugunu olcer.

NEDEN VAR (Okan, 31 Tem — canli kusur, ekran goruntusuyle isaretlendi)
----------------------------------------------------------------------
`urunler.json`da `"tur": "fiziksel"` tasiyan kayitlar HAZIR TICARI MALDIR (International
tekne boyasi, vernik, tiner...). Bunlari 3D baskiyla URETMIYORUZ; musteri ne malzeme ne
renk seciyor, fiyat da SABIT. Buna ragmen sayfalari `render_product` icinde
`fonksiyonel and not parametrik` daline dusuyordu (kategori "Marin" FONKSIYONEL_KATEGORILER
icinde) ve su besi basiyordu:
    1. Renk butonlari — Siyah/Beyaz/Gri/**Diğer (+%15)**
    2. Malzeme cipleri — PLA/PETG/ASA/TPU + "Tavsiyemiz" rozeti
    3. "Karbon fiber ... WhatsApp'tan bize yazin" muhendislik-malzeme notu
    4. "Hangi malzeme nerede kullanilir? Malzeme Rehberi ->" linki
    5. "1.000,00 TL'den başlayan" — oysa fiziksel urunun fiyati SABIT

🔴 BU BIR PARA KUSURUYDU, SAYFA KOZMETIGI DEGIL. "Diğer" secimi sepet satirina
`renk: "Diğer"` yazar; `secenekler.js` hesaplaFiyatKurus onu x1,15 yapar, malzeme cipi
ayrica x1,60'a (ASA) kadar cikarir. OLCULDU (secenekler.js satirOzeti — Worker'in
`sepetiFiyatla` sabit-fiyat kolunda cagirdigi AYNI fonksiyon; liste fiyati 1.000 TL):
    PLA/Siyah (varsayilan) -> 100000 kurus = 1.000,00 TL   (DOGRU)
    PLA/"Diğer"            -> 115000 kurus = 1.150,00 TL   (+150 TL karsiliksiz)
    ASA/"Diğer"            -> 184000 kurus = 1.840,00 TL   (+840 TL karsiliksiz)
Yani musteri bir boya kutusu icin var olmayan bir "ozel renk" secip %15 fazla odeyebiliyordu.

ONARIM (tools/build.py render_product): `tur == "fiziksel"` ise renk secici, malzeme
bolumu ve "…'den başlayan" metni BASILMAZ; KART_SECIM bayragi KAPATILIR; adet secici +
sepet ikonu + WhatsApp ikonu KALIR. Secici basilmadigi icin sepet satiri
`PRUVO_SECENEK.bosSatir` varsayilanlariyla (PLA/Siyah = x1,00) uretilir -> +%15 yolu
ISTEMCIDE ULASILAMAZ.

🔴 FAIL-CLOSED YONU: kosul "fiziksel ISE kaldir"dir, "3D ISE goster" DEGIL. `tur` alani
YOKSA ya da taninmayan bir deger tasiyorsa sayfa BUGUNKU gibi uretilir. Ters yazilsaydi
`tur`suz 15.930 baski urunu malzeme/renk secicisini + sepet ikonunu SESSIZCE kaybederdi.

IDDIALAR
--------
  P1 POZITIF   fiziksel fikstur sayfasinda renk butonu / data-renk / renkOzel / fil-cip /
               #filCipler / malzeme-link / "Tavsiyemiz" / "+%15" YOK (8 kanca).
               + P1-EMEKLI defteri: listeden CIKARILAN madde hala OLU MU diye olculur
               (bkz. P1_EMEKLI) — sessiz emeklilik yasak, madde dirilirse KIRMIZI.
  P2 POZITIF   AYNI sayfada adet secici + sepet butonu + WhatsApp butonu VAR
               (kaldirmayi FAZLA yapmadik — sayfa satilabilir kaldi).
  P3 ODEME     fiziksel sayfada "Diğer" rengi URETEBILECEK hicbir kanca yok
               (data-renk / #renkOzel / #renkSec YOK ve KART_SECIM = false) -> sepet satiri
               bosSatir varsayilanina duser. Iddia node ile PARAYA baglanir: gercek
               secenekler.js'te bosSatir varsayilani liste fiyatini AYNEN verir, "Diğer"
               ise +%15 uretir (yani susturulan sey GERCEKTEN para yoluydu).
  N1 NEGATIF   `tur` alani OLMAYAN normal 3D urun sayfasinda O ON BIR OGENIN HEPSI durur
               (regresyon nobetcisi).
  N1F ILAN FIYATI  AYNI sayfa (a) `#opsiyonFiyat` yuzeyi TASIR, (b) yuzey BOS DEGIL,
               (c) bastigi tutar KANONIK kaynakla (`build.ilan_kurus`) AYNI. BICIME
               BAGLANMAZ — asagidaki dersin karsiligi.
  N2 FAIL-CLOSED  `tur` alani TANINMAYAN deger tasiyan urun ("fiziksel-degil", "3d", "",
               null, 0, dizi...) `tur`suz urunle BAYT-BAYT AYNI sayfayi uretir.

🔴 DERS (11 Agu, olculdu): N1'in fiyat capasi once `"…'den başlayan"` DIZESINE bagliydi.
Commit 1e1f9d9b `ONERI_ONSECIM_ACIK`i acti; urun sayfasi baslangic tabani yerine ON-SECILI
malzemenin KESIN tutarini basmaya basladi — ticari degismez BOZULMADI, DUZELDI (ilan edilen
tutar artik sepete yazilanla ayni). Ama bicime bagli capa yayini durdurdu ve ayni dize
`onsecim-parite-kapisi.py` N5 mutantinda REGRESYON sayildigi icin iki kapi birbirine TERS
hukum kurdu: dizeyi geri koymak bu kapiyi yesile, kardes kapiyi kirmiziya cekiyordu
(olculdu: rc 0/1 <-> 1/0). Cozum capayi DEGISMEZE baglamak oldu, iddiayi kaldirmak DEGIL.

MUTASYON (--mutasyon): iki eksende probe. (1) `tur == "fiziksel"` kosulu no-op edilir (iki
yonde de). (2) ILAN FIYATI degismezi iki yonde zorlanir: yuzey tumden dusurulur · tutar
bicim BOZULMADAN saptirilir · statik tutar liste tutarinda birakilir (kardes kapinin N5
mutantinin AYNISI — iki kapi artik AYNI YONDE kirmizi yakiyor). Probe DAR: her mutant
yalnizca kendi eksenini dusurur; baska eksen dusuyorsa probe GENIS sayilir ve hata olur.

Offline (ag yok), GERCEK urunler.json OKUNMAZ (sentetik fiksturler), repoya DOSYA YAZMAZ.
node ZORUNLU (deploy.yml setup-node kurar) — yoksa FAIL-CLOSED kirmizi: para iddiasi
(P3) olculmeden bu kapi YESIL veremez.

Kullanim:
    python3 tools/fiziksel-urun-kapisi.py
    python3 tools/fiziksel-urun-kapisi.py --mutasyon

Cikis kodlari: 0 = YESIL (butun iddialar olculdu ve gecti) · 1 = KIRMIZI.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import types

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
BUILD_YOL = os.path.join(TOOLS, "build.py")
SECENEKLER_YOL = os.path.join(ROOT, "secenekler.js")

# Kaldirilmasi gereken 3D-BASKI SECIM kancalari. (ad, arama dizesi) — hepsi ANA GOVDEDE
# (<main>, script/style cikarilmis) aranir: FOOT_NAV_HTML her sayfaya bir "/malzeme-rehberi/"
# linki basar, TUM sayfada arasaydik "Malzeme Rehberi kalkti" iddiasi footer'in KENDISIYLE
# karsilanir ve govdedeki link silinse bile OLU/YESIL kalirdi (ayni tuzak konfigur-test.py
# (e) bolumunde olculdu ve orada da bolgeyle kapatildi).
#
# 🔴 BU LISTE IKI IDDIAYA BIRDEN HIZMET EDER (P1 "fizikselde YOK" + N1 "3D'de VAR"). Bu
# yuzden buraya BICIME bagli bir madde konmaz: ayni dize hem "olmamali" hem "olmali" diye
# olculdugunde, urun sayfasinin BICIMI degistigi an biri kendiliginden olur, digeri yayini
# durdurur. 11 Agu'da tam bu oldu — asagidaki P1_EMEKLI defterine bak.
BASKI_KANCALARI = [
    ("renk butonlari konteyneri", 'id="renkButonlar"'),
    ("renk butonu data-renk", "data-renk="),
    ('"Diğer (+%15)" etiketi', "Diğer (+%15)"),
    ("ozel renk metin kutusu", 'id="renkOzel"'),
    ("malzeme cipi", "fil-cip"),
    ("malzeme cipleri konteyneri", 'id="filCipler"'),
    ('"Tavsiyemiz" rozeti', "Tavsiyemiz"),
    ("Malzeme Rehberi linki", 'class="malzeme-link"'),
]

# ------------------------------------------------------------------ P1 EMEKLI DEFTERI
# Listeden CIKARILAN madde + gerekcesi. SESSIZ SILME YASAK: madde her kosumda hala
# OLU MU diye olculur ve sayi (9 -> 8) ciktida GORUNUR yazilir.
#
# `"…'den başlayan"` (11 Agu, commit 1e1f9d9b — `ONERI_ONSECIM_ACIK` false -> true):
#   Urun sayfasi artik ON-SECILI malzemenin KESIN tutarini basiyor, "baslangic tabani"
#   ifadesini DEGIL. Dize HICBIR sayfada uretilmedigi icin "fizikselde yok" iddiasi
#   kendiliginden saglaniyordu = OLU (sizinti listesi 9 yerine 8 sayiyordu). Ustelik
#   ayni dizeyi `onsecim-parite-kapisi.py` N5 mutanti REGRESYON sayar; iki kapi
#   birbiriyle CELISIYORDU. Iddia KALDIRILMADI, DEGISMEZE baglandi: N1 artik dizeyi
#   degil "sayfa bir tutar ilan eder ve o tutar tahsil edilenle AYNIDIR"i olcer
#   (asagida ilan_fiyat_ihlali).
P1_EMEKLI = [
    ('"…\'den başlayan" fiyat', "den başlayan",
     "on-secim acildi (1e1f9d9b): dize hicbir sayfada uretilmiyor -> iddia OLU. "
     "Yerini N1'in BICIMDEN BAGIMSIZ ilan-tutari degismezi aldi."),
]
P1_KANCA_ESKI_SAYI = len(BASKI_KANCALARI) + len(P1_EMEKLI)   # 9 — emeklilik oncesi taban

# Kalmasi ZORUNLU ogeler — "kaldirmayi fazla yapma" nobetcisi.
KALAN_OGELER = [
    ("adet secici", 'id="adetSec"'),
    ("sepete ekle butonu", 'id="cartBtn"'),
    ("WhatsApp butonu", 'id="orderAlt"'),
]


# --------------------------------------------------------------------------- fiksturler
def _urun(uid, tur=Ellipsis):
    """Sentetik urun kaydi. tur=Ellipsis -> `tur` ALANI HIC YOK (normal 3D urun).
    Kategori "Marin" BILEREK secildi: FONKSIYONEL_KATEGORILER icinde, yani `tur` devreye
    girmezse sayfa kart-secim (renk+malzeme) dalina duser — kapinin olctugu tam eksen."""
    u = {
        "id": uid,
        "baslik": "Sinama Urunu",
        "kategori": "Marin",
        "marka": ["Sinama"],
        "fiyat": "1000 TL",
        "aciklama": "Sinama aciklamasi.\nIkinci satir.",
        "gorseller": ["https://media.example/%s-1.jpg" % uid],
    }
    if tur is not Ellipsis:
        u["tur"] = tur
    return u


def _govde(html):
    """ANA GOVDE: <main> icerigi, script/style cikarilmis (footer/inline JS sizmasin)."""
    m = re.search(r"<main\b.*?</main>", html, re.S)
    g = m.group(0) if m else html
    g = re.sub(r"<script\b.*?</script>", "", g, flags=re.S)
    return re.sub(r"<style\b.*?</style>", "", g, flags=re.S)


# ------------------------------------------------------- ILAN EDILEN FIYAT (degismez)
def _ilan_yuzeyi(govde):
    """`#opsiyonFiyat` blogunun GOVDESI. None = fiyat yuzeyi HIC YOK."""
    m = re.search(r'id="opsiyonFiyat"[^>]*>(.*?)</div>', govde, re.S)
    if not m:
        return None
    return re.sub(r"<[^>]+>", "", m.group(1)).strip()


def _metin_kurus(metin):
    """Gorunur tutar metnini tamsayi kurusa cevirir — BICIMDEN BAGIMSIZ.
        "1.600,00 TL"                -> 160000
        "1000 TL&#39;den başlayan"   ->  100000
    None = ayristirilamadi (fail-closed: kapi bunu YESIL saymaz, KIRMIZI yakar).
    Cevrilen sey SUSLEME degil SAYIDIR; metnin etrafindaki ifade serbesttir."""
    if not metin:
        return None
    m = re.search(r"([0-9][0-9.]*)(?:,([0-9]{2}))?\s*TL", metin)
    if not m:
        return None
    return int(m.group(1).replace(".", "")) * 100 + int(m.group(2) or 0)


def _ayristirici_capasi(mod):
    """🔴 IKIZ TANIM NOBETI: yukaridaki ayristirici, tutari basan KANONIK bicimlendirici
    (`build.taban_fiyat_metni`) ile TERS yonde ayni sayiyi vermeli. Bicimlendirici
    degisirse (binlik ayraci, kurus basamagi...) ayristirici SESSIZCE bayatlar ve
    "tutar tuttu" diyen iddia OLU kalir. Gidis-donus burada olculur."""
    hatalar = []
    for k in [100000, 160000, 45500, 999, 100, 123456789]:
        metin = mod.taban_fiyat_metni(k / 100.0)
        if _metin_kurus(metin) != k:
            hatalar.append("%d krs -> %r -> %r" % (k, metin, _metin_kurus(metin)))
    return hatalar


def ilan_fiyat_ihlali(mod, urun, govde):
    """N1'in DEGISMEZI: sayfa (a) bir fiyat yuzeyi TASIR, (b) yuzey BOS DEGILDIR,
    (c) bastigi tutar KANONIK kaynakla (`build.ilan_kurus`) AYNIDIR.

    Bicime (hangi ifade, hangi ek) BAGLANMAZ: 11 Agu'da "…'den başlayan" ifadesi
    kesin tutara donusunce bicime bagli eski capa yayini durdurdu, oysa ticari
    degismez bozulmamisti — hatta duzelmisti (ilan edilen tutar artik sepete
    yazilanla ayni). Olculen sey: SAYFA BIR TUTAR ILAN EDER VE O TUTAR TAHSIL
    EDILENLE AYNIDIR. Dondurur: (hata_listesi, gorunur_metin, olculen_kurus)."""
    beklenen = mod.ilan_kurus(urun)
    metin = _ilan_yuzeyi(govde)
    if metin is None:
        return (["ilan edilen fiyat YUZEYI YOK (`#opsiyonFiyat` blogu basilmamis)"],
                None, None)
    if not metin:
        return (["ilan edilen fiyat yuzeyi BOS (`#opsiyonFiyat` var ama tutar yok)"],
                metin, None)
    olculen = _metin_kurus(metin)
    if olculen is None:
        return (["ilan edilen tutar AYRISTIRILAMADI (%r) — yuzeyde sayi yok ya da bicim "
                 "kanonik bicimlendiriciden koptu" % metin], metin, None)
    if beklenen is None:
        return (["kanonik kaynak `ilan_kurus` None dondu — tutar OLCULEMEDI, kapi bu "
                 "durumda YESIL VEREMEZ"], metin, olculen)
    if olculen != beklenen:
        return (["ILAN EDILEN TUTAR KANONIK KAYNAKTAN SAPTI: sayfa %d krs (%r), "
                 "`ilan_kurus` %d krs — musteriye gosterilen tutar ile tahsil edilen "
                 "AYRISTI" % (olculen, metin, beklenen)], metin, olculen)
    return ([], metin, olculen)


# --------------------------------------------------------------------------- build modulu
def build_modulu(mutasyon=None):
    """tools/build.py'yi (istege bagli TEK bir kaynak-kodu mutasyonuyla) yukler.

    Mutasyon DISKE YAZILMAZ — kaynak bellekte degistirilip exec edilir. Diske yazmak bu
    depoda olculmus bir tuzaktir: kosum yarida kalirsa mutant build.py commit'e sizar."""
    with open(BUILD_YOL, encoding="utf-8") as f:
        src = f.read()
    if mutasyon is not None:
        eski, yeni = mutasyon
        if src.count(eski) != 1:
            raise SystemExit("MUTASYON CAPASI KAYIP/COKLU (%d adet): %r — build.py degismis, "
                             "mutasyon capasi guncellenmeli." % (src.count(eski), eski))
        src = src.replace(eski, yeni, 1)
    mod = types.ModuleType("build_olculen")
    mod.__file__ = BUILD_YOL
    mod.__name__ = "build_olculen"       # __main__ DEGIL -> main() kendiliginden kosmaz
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    exec(compile(src, BUILD_YOL, "exec"), mod.__dict__)
    return mod


# --------------------------------------------------------------------------- node (para)
def para_olcumu():
    """GERCEK secenekler.js ile: bosSatir varsayilani vs "Diğer" rengi — kurus farki.
    Kopya/taklit YOK; Worker'in (shop/src/index.js) import ettigi AYNI dosya kosturulur."""
    betik = (
        'const S=(await import(%s)).default||globalThis.PRUVO_SECENEK;'
        'const U={kategori:"Marin",fiyat:"1000 TL",parametrik:false,boy_secenekleri:[]};'
        'const b=globalThis.PRUVO_SECENEK.bosSatir("x");'
        'const O=(r)=>globalThis.PRUVO_SECENEK.satirOzeti(U,'
        '{...b,malzeme:r.m,renk:r.r,renk_ozel:r.o||"",adet:1}).birimKurus;'
        'console.log(JSON.stringify({'
        'varsayilan_malzeme:b.malzeme,varsayilan_renk:b.renk,'
        'varsayilan_kurus:O({m:b.malzeme,r:b.renk}),'
        'diger_kurus:O({m:"PLA",r:"Diğer",o:"turuncu"}),'
        'asa_diger_kurus:O({m:"ASA",r:"Diğer",o:"turuncu"}),'
        'renkler:globalThis.PRUVO_SECENEK.RENK_SECENEKLERI}));'
    ) % json.dumps("file://" + SECENEKLER_YOL)
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", encoding="utf-8", delete=False) as f:
        f.write(betik)
        yol = f.name
    try:
        r = subprocess.run([os.environ.get("NODE", "node"), yol],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        # FAIL-CLOSED: node yoksa para iddiasi OLCULEMEZ -> kapi YESIL VEREMEZ.
        raise SystemExit("KIRMIZI: node kosturulamadi (%s) — P3 para iddiasi olculemedi. "
                         "deploy.yml setup-node BLOKLAYICI on-kosuldur." % e)
    finally:
        os.unlink(yol)
    if r.returncode != 0:
        raise SystemExit("KIRMIZI: secenekler.js node'da kosmadi:\n%s" % (r.stderr or "")[:2000])
    return json.loads(r.stdout.strip().splitlines()[-1])


# --------------------------------------------------------------------------- iddialar
def kosum(mod, para):
    """Butun iddialari olcer; (hatalar, satirlar) dondurur. hatalar bos = YESIL."""
    hatalar, satirlar = [], []

    fiz = _urun("sinama-fiziksel", tur="fiziksel")
    nrm = _urun("sinama-normal")                      # `tur` alani YOK
    tum = [fiz, nrm]

    fiz_html = mod.render_product(fiz, tum)
    fiz_g = _govde(fiz_html)
    nrm_html = mod.render_product(nrm, tum)
    nrm_g = _govde(nrm_html)

    # --- P1: baski secim kancalari fiziksel sayfada YOK
    p1_eksik = [ad for ad, ip in BASKI_KANCALARI if ip in fiz_g]
    if p1_eksik:
        hatalar.append("P1 fiziksel sayfada hala baski secim kancasi var: " + ", ".join(p1_eksik))
    satirlar.append("P1 baski secim kancalari (%d; emeklilik oncesi %d) fiziksel sayfada: %s"
                    % (len(BASKI_KANCALARI), P1_KANCA_ESKI_SAYI,
                       "HEPSI YOK ✔" if not p1_eksik else "SIZAN: %s ✘" % p1_eksik))

    # --- P1-EMEKLI defteri: cikarilan madde HALA OLU MU? (sessiz emeklilik yasak)
    # Iki yonlu: (a) fiziksel sayfada belirirse GERCEK P1 ihlalidir; (b) 3D sayfasinda
    # belirirse madde artik OLU DEGILDIR -> defter bayat, P1'e geri alinmali. Ikisi de
    # KIRMIZI: emekli madde sessizce dirilemez.
    for ad, ip, gerekce in P1_EMEKLI:
        if ip in fiz_g:
            hatalar.append("P1-EMEKLI %s fiziksel sayfada BELIRDI — emekli madde geri "
                           "geldi ve sizdi, listeye ALINMALI" % ad)
        if ip in nrm_g:
            hatalar.append("P1-EMEKLI %s `tur`suz 3D sayfada YENIDEN URETILIYOR — madde "
                           "artik OLU DEGIL, emeklilik defteri BAYAT: P1 listesine geri "
                           "alinmali (gerekce: %s)" % (ad, gerekce))
        satirlar.append("P1-EMEKLI %s: fizikselde %s · 3D'de %s (%s)"
                        % (ad, "VAR ✘" if ip in fiz_g else "yok",
                           "VAR ✘ (DIRILDI)" if ip in nrm_g else "yok (hala OLU) ✔",
                           gerekce))

    # --- P2: satilabilirlik korundu
    p2_eksik = [ad for ad, ip in KALAN_OGELER if ip not in fiz_g]
    if p2_eksik:
        hatalar.append("P2 fiziksel sayfadan FAZLA kaldirildi, eksik: " + ", ".join(p2_eksik))
    satirlar.append("P2 adet+sepet+WhatsApp fiziksel sayfada: %s"
                    % ("HEPSI VAR ✔" if not p2_eksik else "EKSIK: %s ✘" % p2_eksik))

    # --- P3: ODEME — "Diğer" uretebilecek kanca yok + KART_SECIM kapali
    p3 = []
    for ad, ip in [("renk butonu (data-renk)", "data-renk="),
                   ("ozel renk kutusu (#renkOzel)", 'id="renkOzel"'),
                   ("renk dropdown (#renkSec)", 'id="renkSec"')]:
        if ip in fiz_html:                      # TUM sayfa: inline JS DAHIL
            p3.append(ad)
    if "KART_SECIM = false" not in fiz_html:
        # KART_SECIM acik kalsaydi: (a) currentSatir seciliRenk'i satira yazan kola girer,
        # (b) hicbir cip/buton basilmadigi icin seciliMalzeme/seciliRenk sonsuza kadar bos
        #     kalir ve SEPETE EKLE butonu SESSIZCE hicbir sey yapmaz.
        p3.append("KART_SECIM bayragi kapatilmamis")
    if p3:
        hatalar.append("P3 fiziksel sayfada +%15 'Diğer' yolu HALA ULASILABILIR: " + ", ".join(p3))
    # Para capasi: susturulan seyin GERCEKTEN para oldugunu gercek secenekler.js ile kanitla.
    if para["varsayilan_kurus"] != 100000:
        hatalar.append("P3 para capasi: bosSatir varsayilani liste fiyatini vermiyor (%d kurus)"
                       % para["varsayilan_kurus"])
    if para["diger_kurus"] != 115000:
        hatalar.append("P3 para capasi: 'Diğer' rengi +%%15 uretmiyor (%d kurus) — kapinin "
                       "olctugu para ekseni degismis, gerekce guncellenmeli"
                       % para["diger_kurus"])
    if "Diğer" not in para["renkler"]:
        hatalar.append("P3 para capasi: RENK_SECENEKLERI'nde 'Diğer' yok — iddia OLU kalir")
    satirlar.append("P3 odeme: fiziksel sayfada 'Diğer' kancasi %s | bosSatir=%s/%s -> %d krs "
                    "· 'Diğer' -> %d krs · ASA+'Diğer' -> %d krs"
                    % ("YOK ✔" if not p3 else "VAR ✘",
                       para["varsayilan_malzeme"], para["varsayilan_renk"],
                       para["varsayilan_kurus"], para["diger_kurus"], para["asa_diger_kurus"]))

    # --- N1: `tur`suz normal 3D urunde HER SEY yerinde (regresyon nobetcisi)
    n1_eksik = [ad for ad, ip in BASKI_KANCALARI if ip not in nrm_g]
    n1_eksik += [ad for ad, ip in KALAN_OGELER if ip not in nrm_g]
    if "KART_SECIM = true" not in nrm_html:
        n1_eksik.append("KART_SECIM bayragi")
    if n1_eksik:
        hatalar.append("N1 REGRESYON — `tur`suz 3D urun sayfasi oge kaybetti: "
                       + ", ".join(n1_eksik))
    satirlar.append("N1 `tur`suz 3D urun sayfasi (%d oge + bayrak): %s"
                    % (len(BASKI_KANCALARI) + len(KALAN_OGELER),
                       "HEPSI YERINDE ✔" if not n1_eksik else "KAYIP: %s ✘" % n1_eksik))

    # --- N1F: ILAN EDILEN FIYAT DEGISMEZI (bicimden bagimsiz — eski dize capasinin yerine)
    capa = _ayristirici_capasi(mod)
    if capa:
        hatalar.append("N1F ayristirici KANONIK bicimlendiriciden koptu (gidis-donus "
                       "tutmadi): " + " · ".join(capa))
    n1f, gorunur, olculen = ilan_fiyat_ihlali(mod, nrm, nrm_g)
    for h in n1f:
        hatalar.append("N1F ILAN EDILEN FIYAT — `tur`suz 3D urun sayfasi: " + h)
    satirlar.append("N1F ilan edilen fiyat (yuzey VAR · DOLU · kanonik `ilan_kurus` ile "
                    "AYNI): %s | sayfa=%r -> %s krs · ilan_kurus=%s krs%s"
                    % ("TUTTU ✔" if not n1f else "IHLAL ✘", gorunur, olculen,
                       mod.ilan_kurus(nrm),
                       "" if not capa else " | ayristirici capasi KOPUK ✘"))

    # --- N2: FAIL-CLOSED — taninmayan `tur` degeri `tur`suzle BAYT-BAYT AYNI
    n2_sapan = []
    for deger in ["fiziksel-degil", "3d", "Fiziksel", "FIZIKSEL", " fiziksel", "fiziksel ",
                  "", None, 0, 1, True, False, [], ["fiziksel"], {"t": "fiziksel"}]:
        u = _urun("sinama-normal", tur=deger)
        if mod.render_product(u, tum) != nrm_html:
            n2_sapan.append(repr(deger))
    if n2_sapan:
        hatalar.append("N2 FAIL-CLOSED IHLALI — taninmayan `tur` degeri sayfayi degistirdi: "
                       + ", ".join(n2_sapan))
    satirlar.append("N2 fail-closed (16 taninmayan `tur` degeri, bayt-esitlik): %s"
                    % ("HEPSI `tur`suzle AYNI ✔" if not n2_sapan else "SAPAN: %s ✘" % n2_sapan))
    return hatalar, satirlar


# --------------------------------------------------------------------------- mutasyon
# Her mutant DAR bir probe'dur: yalnizca `tur == "fiziksel"` kosulunun yakalayabilecegi bir
# seyi bozar. Kosul no-op edilirse hangi iddianin dusecegi ONCEDEN yazilir; BASKA bir iddia
# dusuyorsa probe genis demektir ve bu da hata sayilir.
MUTANTLAR = [
    ('fiziksel = (p.get("tur") == "fiziksel")',
     'fiziksel = False',
     "kosul DAIMA yanlis -> fiziksel urun eski (baski secimli) sayfayi alir",
     ("P1", "P3")),
    # N2 BILEREK beyan edilmiyor: bu mutantta TUM urunler ayni dala dustugu icin
    # `tur`suz ile taninmayan-`tur` sayfalari hala BAYT-BAYT AYNI kalir, yani N2
    # DUSMEZ. Beyana yazsaydik hic dusmeyen bir ekseni "kapsandi" gibi gosterirdik.
    ('fiziksel = (p.get("tur") == "fiziksel")',
     'fiziksel = True',
     "kosul DAIMA dogru -> `tur`suz 3D urun secicilerini kaybeder",
     ("N1", "N1F")),
    # ---- N1F probe'lari: ilan edilen fiyat degismezi IKI YONDE de canli mi?
    # (a) YUZEY DUSERSE: sayfa hicbir tutar ilan etmez.
    ("""                fiyat_blok=fiyat_satiri(
                    eski_html,
                    '<div class="opsiyon-fiyat" id="opsiyonFiyat">%s</div>' % baslangic_fiyat))""",
     "                fiyat_blok=\"\")",
     "ilan fiyat YUZEYI tumden dusuruldu -> sayfa hicbir tutar ilan etmiyor",
     ("N1F",)),
    # (b) TUTAR SAPARSA (bicim AYNI kalir): musteriye gosterilen sayi tahsil edilenden
    #     ayrisir. Bicim degismedigi icin bu mutanti YALNIZCA sayiyi olcen bir iddia
    #     yakalayabilir — eski dize capasi bunu SESSIZ gecirirdi.
    ("            baslangic_fiyat = esc(taban_fiyat_metni(_ilan_k / 100.0))",
     "            baslangic_fiyat = esc(taban_fiyat_metni(_ilan_k / 100.0 + 1))",
     "ilan edilen tutar kanonik kaynaktan 1 TL saptirildi (BICIM ayni)",
     ("N1F",)),
    # (c) KARDES KAPIYLA CELISKI NOBETI: `onsecim-parite-kapisi.py` N5 mutanti tam olarak
    #     bu satiri geri koyar ve KIRMIZI yanmasini bekler. Eski capa bu mutantta YESIL
    #     veriyordu -> iki kapi birbirine ters hukum kuruyordu. Artik bu kapi da KIRMIZI
    #     yakiyor: iki kapi AYNI YONDE. Celiski geri gelirse burasi YESIL'e doner ve
    #     mutasyon kosumu "OLU IDDIA" der.
    #     Bu mutant IKI ekseni birden dusurur ve ikisi de DOGRUDUR: tutar sapar (N1F) VE
    #     emekli dize yeniden uretilir (P1-EMEKLI defteri bayatlar). Ikisini de beyan
    #     ediyoruz — "dusen ama beyan edilmeyen eksen" probe'u genis gosterirdi.
    ("            baslangic_fiyat = esc(taban_fiyat_metni(_ilan_k / 100.0))",
     '            baslangic_fiyat = esc(fiyat) + "&#39;den başlayan"',
     "statik tutar LISTE tutarinda birakildi (kardes kapi N5 mutantinin AYNISI)",
     ("N1F", "P1-EMEKLI")),
]


def mutasyon_kosumu(para):
    print("=== MUTASYON: `tur == \"fiziksel\"` kosulu no-op edildiginde kapi KIRMIZI mi?")
    tamam = True
    for eski, yeni, aciklama, beklenen in MUTANTLAR:
        mod = build_modulu((eski, yeni))
        hatalar, _ = kosum(mod, para)
        etiketler = sorted({h.split()[0] for h in hatalar})
        kirmizi = bool(hatalar)
        dogru_eksen = set(etiketler) and set(etiketler).issubset(set(beklenen))
        durum = "KIRMIZI ✔" if kirmizi else "YESIL ✘ (OLU IDDIA)"
        print("  mutant: %s -> %s" % (yeni, aciklama))
        print("    sonuc: %s | dusen iddialar: %s | beklenen eksen: %s%s"
              % (durum, etiketler or "-", list(beklenen),
                 "" if dogru_eksen else "  <- PROBE GENIS/KAYMIS ✘"))
        for h in hatalar:
            print("      - " + h)
        if not (kirmizi and dogru_eksen):
            tamam = False
    print()
    print("MUTASYON: %s" % ("GECTI — kosul kaldirilinca kapi KIRMIZI yaniyor (iddia CANLI)."
                            if tamam else "KALDI — iddia OLU ya da probe genis."))
    return 0 if tamam else 1


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="Fiziksel urun sayfasi 3D-baski UI kapisi")
    ap.add_argument("--mutasyon", action="store_true",
                    help="kosulu no-op edip kapinin KIRMIZI yandigini kanitla")
    args = ap.parse_args()

    os.chdir(ROOT)
    para = para_olcumu()

    if args.mutasyon:
        return mutasyon_kosumu(para)

    mod = build_modulu()
    hatalar, satirlar = kosum(mod, para)
    print("=== FIZIKSEL URUN KAPISI (tools/build.py render_product · sentetik fikstur)")
    for s in satirlar:
        print("  " + s)
    print()
    if hatalar:
        print("KIRMIZI — %d iddia ihlal edildi:" % len(hatalar))
        for h in hatalar:
            print("  ✘ " + h)
        return 1
    print("YESIL — fiziksel urun sayfasinda 3D-baski secimi YOK, +%15 renk farki "
          "ULASILAMAZ, `tur`suz 15.930 baski urununde regresyon YOK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
