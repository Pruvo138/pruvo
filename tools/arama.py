# -*- coding: utf-8 -*-
"""Arama metni uretimi — index.html'deki norm() + haystack()'in BIREBIR karsiligi.

Neden ayri dosya: ayni mantik uc yerde lazim (d1-sync.py yazarken, parite testi
dogrularken, Worker /ara sorgularken). Tek kaynak olmazsa uc kopya sessizce
birbirinden ayrilir ve arama sonuclari site ile D1 arasinda ayrisir.

DIKKAT — Turkce buyuk/kucuk harf tuzagi:
  JS  "İ".toLocaleLowerCase("tr") -> "i"
  PY  "İ".lower()                 -> "i" + U+0307 (birlesik nokta) — FARKLI!
  JS  "I".toLocaleLowerCase("tr") -> "ı" (sonra norm onu "i" yapar)
  PY  "I".lower()                 -> "i"
Bu yuzden lower()'dan ONCE I/İ elle cevrilir. Dogrulugu varsayima birakilmadi:
tools/parite-test.js (referansi index.html'in GERCEK kodu olan test) bu ciktiyla
uretilmis D1 indeksini sitenin sonucuyla karsilastirir — burada bir harf kaysa
test kirmizi yanar.
"""

import hashlib
import json
import re

_HARF = str.maketrans({
    "ı": "i", "ç": "c", "ğ": "g", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i",
})


def norm(s):
    """index.html norm() ile birebir ayni ciktiyi verir."""
    if not s:
        return ""
    # toLocaleLowerCase("tr") taklidi: I -> ı, İ -> i (lower()'dan ONCE)
    s = s.replace("İ", "i").replace("I", "ı")
    return s.lower().translate(_HARF)


def haystack(u):
    """Urunun aranabilir metni — index.html haystack() ile birebir ayni."""
    return norm(" ".join([
        u.get("baslik") or "",
        u.get("aciklama") or "",
        " ".join(u.get("marka") or []),
        u.get("kategori") or "",
        (u.get("id") or "").replace("-", " "),
    ]))


def tokenlar(q):
    """Sorguyu index.html ile ayni sekilde parcalara ayirir + Turkce ek kirpma.

    index.html filtered(): norm(query).split().map(aramaKok) ile BIREBIR. arama_kok
    asagida (L88) tanimli; modul seviyesi ad, cagri aninda cozulur (forward-ref sorun degil).
    DIKKAT: haystack()/urun_hash() DEGISMEZ — sadece SORGU tarafi kok alir, D1 kolonu ayni.
    """
    return [arama_kok(t) for t in norm(q).split() if t]


def esles(hs, tokens):
    """filtered() ile ayni: HER token, arama metninin ALT-DIZESI olmali."""
    return all(t in hs for t in tokens)


# ─────────────────────────────────────────────────────────────────────────────
# EGE TARAFI (FAZ 2) — bot'un urunAra()'si sitenin filtered()'indan BASKA bir arama.
# Site: kati AND + alt-dize + katalog sirasi. Ege: es anlamli gruplar + Turkce ek
# kirpma + cift yonlu onek + baslik/govde SKORU. Ikisi ayri normalizasyon kullanir
# (asagidaki nrm alfanumerik olmayani BOSLUGA cevirir, yukaridaki norm cevirmez) —
# bu yuzden ayri kolonlar; tek kolona bindirmek iki aramayi da sessizce bozardi.
#
# Kaynak: pruvo-bot/worker/src/index.js -> nrm(), aramaKok(), ARAMA_EKLER.
# Ikisi ayrisirsa tools/parite-ege.js kirmizi yanar (referans = o dosyanin GERCEK kodu).

_NRM_HARF = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u"})
_NRM_TEMIZ = re.compile(r"[^a-z0-9]+")


def nrm(s):
    """index.js nrm() ile birebir. DIKKAT: â/î burada BILEREK cevrilmez —
    JS de cevirmiyor, [^a-z0-9] onlari bosluga atiyor. Sadik taklit sart."""
    s = (s or "").replace("İ", "i").replace("I", "i").lower()
    return _NRM_TEMIZ.sub(" ", s.translate(_NRM_HARF)).strip()


# index.js ARAMA_EKLER — SIRA ONEMLI (uzundan kisaya; ilk eslesen ek kirpilir).
ARAMA_EKLER = [
    "lerimiz", "larimiz", "lerim", "larim", "lerin", "larin", "imiz", "iniz", "umuz", "unuz",
    "leri", "lari", "nin", "nun", "den", "dan", "tan", "ten", "ler", "lar", "yle", "yla",
    "si", "su", "yi", "yu", "ye", "ya", "na", "ne", "de", "da", "te", "ta",
    "in", "im", "un", "um", "i", "u", "e", "a", "m", "n",
]


def arama_kok(w):
    """index.js aramaKok() — kalan kok >= 4 harfse tek geciste ek kirpar."""
    for ek in ARAMA_EKLER:
        if len(w) - len(ek) >= 4 and w.endswith(ek):
            return w[:len(w) - len(ek)]
    return w


def koke_cevir(metin):
    """Metnin HER kelimesini kokune cevirip birlestir.

    Neden: urunAra'da "kok esitligi" (mentesem <-> mentesesi) kelime bazli bir kural.
    Kokleri onceden yazmasak, SQL'de her sorgu icin ~50 aday ek denemek gerekirdi
    (kk+ek kombinasyonlari). Kokler kolonda hazir olunca kural TEK bir tam-kelime
    aramasina iner: instr(' '||hs_x_kok||' ', ' '||kk||' ').
    """
    return " ".join(arama_kok(w) for w in metin.split(" ") if w)


def ege_baslik(u):
    """urunAra titlePost kaynagi: aramaTokenlar(u.baslik)."""
    return nrm(u.get("baslik") or "")


def ege_govde(u):
    """urunAra bodyPost kaynagi — index.js'teki dizi SIRASIYLA ayni."""
    return nrm(" ".join([
        u.get("id") or "",
        u.get("baslik") or "",
        u.get("kategori") or "",
        " ".join(u.get("marka") or []),
        u.get("aciklama") or "",
    ]))


# ─────────────────────────────────────────────────────────────────────────────
# TICARI HAL (tur / stokta) — D1'e giden KANONIK degerler.
#
# NEDEN BURADA (arama.py'de) VE NEDEN KANONIK: bu iki alan hem urun_hash'e girer hem
# D1 kolonuna yazilir. Iki yerde AYRI turetilseydi (biri ham deger, digeri normalize)
# hash "degismedi" derken kolon degisir ya da tersi olur -> satir yeniden yazilmaz ve D1
# SESSIZCE eski hali servis eder. Tek fonksiyon = tek kaynak.
#
# 🔴 FAIL-CLOSED YONU — build.py render_product ile AYNI kural:
#   `tur`: SADECE tam "fiziksel" dizesi HAZIR TICARI MAL demektir. Alan YOK ya da
#   taninmayan bir deger ("3d", "Fiziksel", "", None, 0, dizi...) -> "" = OZEL URETIM
#   (katalogun varsayilani, 15.930 baski urunu). Kural "fiziksel ISE isaretle"dir,
#   "3D ISE isaretle" DEGIL -> `tur`suz urunde regresyon 0.
#
#   `stokta`: UC DEGERLI tam sayi. Ikili (0/1) yapilsaydi "alan hic yok" ile "acikca
#   tukendi" AYNI hucreye duserdi ve iki taraflı zarar verirdi: 0'i "tukendi" okuyan uc
#   15.930 ozel-uretim urununu "STOKTA DEGIL" ilan eder (kataloğun tamami olur),
#   0'i "bilinmiyor" okuyan uc ise GERCEKTEN tukenmis fiziksel urunu satar.
#     -1 STOK_BILINMIYOR  alan YOK. Ozel uretim urunlerin normal hali (stok kavrami
#                         UYGULANMAZ; urun siparis uzerine uretilir). Fiziksel bir urunde
#                         gorulurse VERI EKSIKTIR -> uc taraf STOK VAAT ETMEZ.
#      0 STOK_YOK         alan VAR ama true DEGIL (false ya da TANINMAYAN deger).
#                         "STOKTA DEGIL" olarak sunulur.
#      1 STOK_VAR         alan tam olarak boolean true. Tek "stokta" diyebilen deger.
#   Yani "STOKTA" iddiasi YALNIZ 1'den dogar; taninmayan/eksik hicbir sey 1 uretemez
#   (Okan kurali: siparis kaybetmek yanlis vaatten iyidir).
#
# TIP TUZAGI (bilerek `is True` / `isinstance(bool)`): Python'da `True == 1` ve
# `isinstance(True, int)` -> True. `u.get("stokta") == 1` yazsaydik JSON'daki sayi 1 de
# stokta sayilirdi; asagidaki kimlik testi yalniz GERCEK boolean'i gecirir.
_TUR_FIZIKSEL = "fiziksel"
STOK_BILINMIYOR = -1
STOK_YOK = 0
STOK_VAR = 1
# Uc tarafin "STOKTA" diyebilecegi TEK deger kumesi (kabul testi bunu capa alir).
STOK_VAAT_EDILEBILIR = frozenset({STOK_VAR})


def tur_kanonik(u):
    """D1'e yazilan `tur` degeri: "fiziksel" ya da "" (ozel uretim). Fail-closed."""
    return _TUR_FIZIKSEL if u.get("tur") == _TUR_FIZIKSEL else ""


def stokta_kanonik(u):
    """D1'e yazilan `stokta` degeri: -1 bilinmiyor / 0 stokta degil / 1 stokta."""
    if "stokta" not in u:
        return STOK_BILINMIYOR
    return STOK_VAR if u.get("stokta") is True else STOK_YOK


# ─────────────────────────────────────────────────────────────────────────────
# ALT KATEGORI (`altkategori`) — kategori ICINDEKI daraltma etiketi.
#
# NEDEN BURADA (tur/stokta ile AYNI gerekce): bu alan hem urun_hash'e girer hem D1
# kolonuna yazilir. Iki yerde AYRI turetilseydi hash "degismedi" derken kolon degisir
# (ya da tersi) ve D1 SESSIZCE eski degeri servis ederdi. Tek fonksiyon = tek kaynak.
#
# 🔴 IZINLI KUME DONDURULMUS BIR LISTEDIR, urunler.json'dan HER KOSUMDA YENIDEN
# HESAPLANMAZ. Hesaplansaydi kapi TAUTOLOJIYE duserdi: kataloga giren her yeni deger
# kendini otomatik "izinli" yapardi ve kapi hicbir seyi olcmezdi. Liste ASAGIDAKI
# olcumden dondu ve yalnizca bir mimar ELLE genisletir (genisletme de imza nobetinden
# gecmek ZORUNDA — bkz. altkategori_imza_sebebi).
#
# OLCUM (2026-08-01, 16.067 kayitlik katalog): `altkategori` 134 kayitta dolu, hepsi
# kategori "Marin"; 3 tekil deger; hicbir deger birden fazla kategoride gecmiyor;
# hicbiri katalogun tekil marka adlariyla carpismiyor; ucu de imza nobetinden geciyor.
#
# ⚠️ GENISLETME YOLU (kardes mimar icin): duzelt.py bu kumenin DISINDAKI her degeri
# FAIL-CLOSED reddeder — yani yeni bir altkategori once BURAYA eklenir, sonra kataloga
# yazilir. Toplu ekleme yolu (urun-ekle.py) duzelt.py'den GECMEZ: oradan giren yeni bir
# deger tools/altkategori-kapisi.py A ekseninde CI'yi KIRMIZI yakar (olculdu 1 Agu:
# "Pervaneler" tam olarak boyle geldi, 34 kayit).
#
# GENISLETME (2026-08-01, MIMAR KARARI): kume 3 -> 11 degere cikti. Ilk uc deger
# yukaridaki olcumden geldi; kalan sekizi kardes mimarin bekleyen partileri icin ELLE
# eklendi ve yazimlari mimar tarafindan kanoniklestirildi (dogru Turkce, cogul bicim).
# Bunlar HENUZ katalogda kullanilmiyor (olculdu: 134 dolu kayit, 3 tekil deger) — yani
# izinli kume katalogun ONUNDE gidiyor; bu KASITLI, cunku deger once burada olmadan
# kataloga yazilamiyor. Yeni sekiz degerin hicbiri mevcut kayitlarla carpismiyor
# (olculdu: 0) ve on birinin de imza nobetinden gectigi tek tek dogrulandi.
#
# GENISLETME (2026-08-01, MIMAR KARARI, ikinci tur): kume 11 -> 12; "Elektrik" eklendi.
# SEBEP olculdu: kardes mimarin altkategori backfill'i 636 kayit yazdi ama 30 urun
# KARSILIKSIZ kaldi (atesleme bobini, mars motoru/solenoid, distributor rotoru/kapagi,
# kontak anahtari, role, sensor, silecek motoru) — kumede elektrik grubu YOKTU. Eksik
# olan izinli DEGERDI, kapi degil: ayni deger `--toplu` ile denendiginde duzelt.py
# rc=RC_ALTKATEGORI ile REDDETMIS ve urunler.json BYTE-ESIT kalmisti (fail-closed
# dogru calisiyor). Deger olculdu: imza nobeti temiz (sebep None), katalogun 1.678
# tekil marka adiyla carpisma 0. Katalogta HENUZ kullanilmiyor — deger once burada
# olmadan kataloga yazilamadigi icin bu KASITLI (yukaridaki desen).
ALTKATEGORI_IZINLI = {
    "Marin": (
        "Boya - Bakım",
        "Bujiler",
        "Dümen ve Kumanda",
        "Elektrik",
        "Filtreler",
        "Motor Parçaları",
        "Motor Yağları",
        "Pervaneler",
        "Sintine ve Ekipmanları",
        "Soğutma",
        "Tutyalar ve Anotlar",
        "Yakıt Sistemi",
    ),
}

# ── IMZA NOBETI (depo PUBLIC) ────────────────────────────────────────────────
# Bu degerler bir TEDARIKCI VITRININDEN OLCULEREK turetiliyor. Deger GENEL bir Turkce
# kategori adi olmali ("astar", "yapistirici" gibi); bir satici katalogundan kopyalandigi
# belli olan etiket — marka/firma adi, alan adi, vitrin adi, urun kodu/SKU oneki —
# tedarikci iliskisini ELE VERIR ve public repoya/siteye/D1'e girmemelidir.
#
# KURAL BEYAZ LISTEDIR (kara liste DEGIL): "sunlar yasak" demek, gorulmemis bir imza
# turunu SESSIZCE gecirirdi. Yalnizca su BICIM kabul edilir; disindaki HER SEY supheli:
#   * yalnizca TURK ALFABESI harfleri + bosluk + '-' + '/'  (q/w/x DAHIL DEGIL: Turkce
#     alfabede yok, yabanci marka adlarinin en ucuz sinyali)
#   * RAKAM YOK (urun kodu / SKU / '2K' tipi satici etiketi)
#   * '.' ':' '&' '@' '_' '®' '™' '©' tirnak/parantez YOK (alan adi, ticari isaret, referans)
#   * en fazla 4 kelime, en fazla 40 karakter (vitrin nav etiketi kisadir; uzun dize
#     kopyalanmis satici basligi sinyalidir)
#   * 2+ harfli TAMAMI BUYUK jeton YOK (SKU oneki / kisaltilmis firma adi sinyali)
# Katalog MARKA listesiyle carpisma ekseni burada DEGIL kapida olculur (bu modul
# urunler.json okumaz) — tools/altkategori-kapisi.py B ekseni.
_ALTKAT_HARF = set("abcçdefgğhıijklmnoöprsştuüvyzABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ")
_ALTKAT_AYIRAC = set(" -/")
ALTKATEGORI_AZAMI_UZUNLUK = 40
ALTKATEGORI_AZAMI_KELIME = 4


def altkategori_imza_sebebi(deger):
    """Deger tedarikci kimligi ele verebilecek bir IMZA tasiyor mu?

    Dondurur: sebep metni (SUPHELI) ya da None (jenerik/temiz). Fail-closed —
    taninmayan her sey supheli sayilir.
    """
    if not isinstance(deger, str):
        return "metin degil (%s)" % type(deger).__name__
    d = deger.strip()
    if not d:
        return "bos"
    if len(d) > ALTKATEGORI_AZAMI_UZUNLUK:
        return "cok uzun (%d > %d karakter) — kopyalanmis satici basligi sinyali" % (
            len(d), ALTKATEGORI_AZAMI_UZUNLUK)
    kelimeler = d.split()
    if len(kelimeler) > ALTKATEGORI_AZAMI_KELIME:
        return "cok fazla kelime (%d > %d)" % (len(kelimeler), ALTKATEGORI_AZAMI_KELIME)
    for c in d:
        if c in _ALTKAT_HARF or c in _ALTKAT_AYIRAC:
            continue
        if c.isdigit():
            return "rakam iceriyor (%r) — urun kodu/SKU sinyali" % c
        return "izinsiz karakter (%r) — alan adi/ticari isaret/yabanci harf sinyali" % c
    for k in kelimeler:
        harfli = [c for c in k if c in _ALTKAT_HARF]
        if len(harfli) >= 2 and all(c.isupper() for c in harfli):
            return "TAMAMI BUYUK jeton (%r) — SKU oneki/kisaltilmis firma adi sinyali" % k
    return None


def altkategori_metin(deger):
    """`altkategori` alaninin KANONIK metin bicimi — TEK KAYNAK.

    🔴 BU FONKSIYON ILE altkategori_sebebi ARASINDAKI SOZLESME (olculdu 2026-08-01):
    sebebi() KANONIK OLMAYAN her degeri REDDEDER (asagidaki `d != deger` dali), kanonik()
    ise kabul edilen degeri BU fonksiyondan gecirir. Yani "kataloga yazilan metin" ile
    "D1'e giden metin" ayni fonksiyondan turer ve AYRISAMAZ.

    NEDEN SART (olculen kusur): once `strip()` uyelik testinin ICINDE yapiliyordu, bu
    yuzden ' Elektrik' (bastaki bosluk) KABUL EDILIYORDU (rc=0). duzelt.py kataloga HAM
    degeri (' Elektrik') yazarken altkategori_kanonik D1'e KIRPILMIS degeri ('Elektrik')
    gonderiyordu: urunler.json ile D1 arasinda SESSIZ bir metin farki — site ile Ege ayni
    urunu farkli yazimla gorurdu, hicbir hash/senkron ekseni bunu yakalamazdi.
    """
    if not isinstance(deger, str):
        return ""
    return deger.strip()


def altkategori_sebebi(kategori, deger):
    """(kategori, altkategori) ikilisi gecerli mi? Sebep metni ya da None (gecerli).

    BOS/eksik deger GECERLIDIR: alan opsiyoneldir (katalogun ~%99'unda yok).
    """
    if deger is None:
        return None
    if not isinstance(deger, str):
        return "altkategori metin olmali, %s degil" % type(deger).__name__
    d = altkategori_metin(deger)
    # 🔴 FAIL-CLOSED, SESSIZ DUZELTME DEGIL: bosluklu deger kirpilip kabul EDILMEZ,
    # cagirana REDDEDILDIGI soylenir. Alternatifi (kataloga da kirpilmis degeri yazmak)
    # ayni ayrismayi kapatirdi ama kullanicinin YAZDIGINI sessizce degistirirdi; bu evin
    # cizgisi "sessizce duzeltme, soyle". '   ' (yalniz bosluk) da buraya duser: alani
    # bosaltmak icin '' ya da --alan-sil altkategori kullanilir.
    if d != deger:
        return ("KANONIK DEGIL: %r — bas/son bosluk tasiyor; kanonik bicim %r "
                "(alani bosaltmak icin '' ya da --alan-sil altkategori)" % (deger, d))
    if not d:
        return None
    imza = altkategori_imza_sebebi(d)
    if imza:
        return "IMZA NOBETI: %r — %s" % (d, imza)
    izinli = ALTKATEGORI_IZINLI.get(kategori)
    if not izinli:
        return ("kategori %r icin TANIMLI altkategori YOK — izinli kume: %s"
                % (kategori, ", ".join(sorted(ALTKATEGORI_IZINLI)) or "(bos)"))
    if d not in izinli:
        return ("%r kategori %r icin izinli DEGIL — izinli: %s"
                % (d, kategori, ", ".join(izinli)))
    return None


def altkategori_kanonik(u):
    """D1'e yazilan `altkategori` degeri. FAIL-CLOSED: izinli kumede olmayan /
    imza tasiyan / tipi yanlis her deger "" olur.

    Neden fail-closed (tur_kanonik deseni): .git/hooks/pre-push d1-sync'i push'tan
    ONCE kosar, CI kapisi ise push'tan SONRA. Yani bozuk/sizdiran bir deger kapi
    kirmizi yanmadan ONCE D1'e — oradan da Ege'ye ve musteriye — ulasabilirdi.
    "" yazmak urunu KAYBETTIRMEZ (urun kendi kategorisi altinda bulunur), yalnizca
    alt-filtre etiketini dusurur. Sessiz KALMAZ: tools/altkategori-kapisi.py A/B
    eksenleri ayni degeri KIRMIZI yakar.

    KABUL EDILEN deger icin BU FONKSIYON GIRDIYI AYNEN DONDURUR (altkategori_metin ile
    sebebi() ayni kanonik bicimde anlasir) -> katalog metni ile D1 metni BIREBIR AYNI.
    """
    deger = u.get("altkategori")
    if altkategori_sebebi(u.get("kategori"), deger) is not None:
        return ""
    return altkategori_metin(deger)


# D1'e yazilan alanlar — biri degisirse satir yeniden yazilir, degismezse yazilmaz.
# (D1 gunluk 100.000 yazma limiti: tam rebuild yerine sadece degiseni yazmak sart.)
def urun_hash(u):
    ozet = json.dumps([
        u.get("id") or "",
        u.get("baslik") or "",
        u.get("kategori") or "",
        u.get("marka") or [],
        u.get("fiyat") or "",
        (u.get("gorseller") or [None])[0],
        bool(u.get("parametrik")),
        haystack(u),
        # FAZ 2: Ege kolonlari. aciklama/ege hash'te YOKTU — "ege" alani degisince
        # satir yeniden yazilmazdi (sessiz eskime). Ikisi de eklendi.
        u.get("aciklama") or "",
        u.get("ege") or "",
        ege_baslik(u),
        ege_govde(u),
        # TICARI HAL: `tur` + `stokta`. HASH'E GIRMESI SART — bu ikisi PUBLIC urunler.json'da
        # yasar (baski'nin aksine CI de gorur) ve D1'e ICERIK UPSERT'i ile yazilir. Hash
        # kapsamasaydi bir urun "tukendi" (stokta true -> false) olarak isaretlendiginde
        # hash AYNI kalir, diff_plan satiri "degismemis" sayar ve D1'e HIC YAZMAZDI:
        # Ege tukenmis urunu STOKTA diye satmaya devam ederdi (sessiz yanlis vaat).
        # KANONIK degerler yazilir (ham degil): D1 kolonuna giden deger ile hash'in gordugu
        # deger AYNI fonksiyondan gelir -> "hash degisti ama kolon degismedi" ayrismasi
        # INSAATAN imkansiz.
        tur_kanonik(u),
        stokta_kanonik(u),
        # ALT KATEGORI: HASH'E GIRMESI SART — alan D1'de bir KESIF yuzeyini besler
        # (kategori icinde daraltma). Hash kapsamasaydi bir urunun altkategorisi
        # degistiginde hash AYNI kalir, diff_plan satiri "degismemis" sayar ve D1'e HIC
        # YAZMAZDI: alt-filtre sessizce bayat kalir, musteri urune ULASAMAZ ve hicbir
        # alarm calmaz. KANONIK deger yazilir (ham degil) -> hash'in gordugu deger ile
        # kolona giden deger AYNI fonksiyondan gelir, ayrisma INSAATAN imkansiz.
        altkategori_kanonik(u),
    ], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(ozet.encode("utf-8")).hexdigest()[:16]
