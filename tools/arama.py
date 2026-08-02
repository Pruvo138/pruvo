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

import copy
import hashlib
import json
import re
import unicodedata

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
#
# GENISLETME (2026-08-02, MIMAR KARARI, ucuncu tur): kume 12 -> 60; 1 kategori -> 6.
# SEBEP olculdu: alt kategori tanimli TEK kategori `Marin`di ve katalogun %94'unde alan
# BOSTU — kategori sayfalari yiginla urunle aciliyor, daraltma yuzeyi YOKTU.
#
# EKSEN (K1, mimar karari): grup adi YER / SISTEM / KULLANIM ALANI adlandirir, SEKIL
# DEGIL. OLCULDU (12.481 Otomobil urunu): sekil ekseni (`Kapaklar`, `Klipsler`,
# `Tutucular`) 60 grup uretiyor, urunlerin %88,99'u BIRDEN FAZLA gruba dusuyor, en buyuk
# grup katalogun %37,37'si — yigilmayi cozmuyor, adini degistiriyor. Yer/sistem ekseni:
# 16 grup, cakisma %24,89, en buyuk grup %13,80. Bu yuzden `Kapaklar ve Tapalar` (Marin,
# 240 ham eslesme), `Kablo ve Klipsler` (188), `Standlar` (Ev, 50), `Telefon Tutucuları`
# (Motosiklet, 85) gibi BICIM adlari — kac urun tasirsa tasisin — kumeye ALINMADI.
# Reddedilen adlarin tamami gerekcesiyle tools/altkategori-sinifla.py ADAYLAR tablosunda
# `SEKIL_RED`/`ELENEN` sinifiyla KAYITLIDIR (bir sonraki tur yeniden tartismasin).
#
# ESIKLER (K4): kategori >=100 urun tasimazsa alt kategori ALMAZ — bugun hak eden 6
# kategori asagidadir; `Ofis` 71 · `Bisiklet` 31 · `Bahçe` 25 · `Tamirat` 25 ·
# `Jeneratör` 23 · `Kamera` 21 · `Skan Art` 17 · `Oyun/Hobi` 15 alt kategori ALMAZ ve bu
# bir EKSIKLIK DEGIL KARARDIR. Grup >=15 urun tasimazsa kumeye GIRMEZ (olculdu ve elendi:
# Elektronik `Mutfak Cihazları` 14 -> `Ev ve Mutfak Cihazları` icinde eritildi;
# Dekorasyon `Bardak Altlıkları` 10, `Kitap Destekleri` 5; Ev `Huniler` 11).
#
# 🔴 MARIN'IN MEVCUT 12 DEGERI BAYT OLARAK KORUNDU (K3): 935 kayit onlari kullaniyor,
# ad degistirmek/silmek veriyi bozar ve kapiyi kirar. Uzerine 5 yeni deger EKLENDI.
# Kume ile tools/altkategori-sinifla.py'nin grup tablosu IKIZDIR ve ayrisirsa
# tools/altkategori-sinifla-test.py KIRMIZI yanar (S ekseni) — kume BURADA tek kaynaktir,
# siniflandirici onun ONUNE GECEMEZ (fail-closed: kume disi ad "" olur).
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
        # ── 2 Agu eki (yukaridaki 12 MIRAS deger AYNEN durur) ──
        "Bağlama Ekipmanları",
        "Güverte ve Donanım",
        "Kano ve Kayak",
        "Montaj Ekipmanları",
        "Olta Ekipmanları",
    ),
    "Otomobil": (
        "Aydınlatma",
        "Ayna ve Silecek",
        "Bagaj ve Taşıma",
        # ── 2 Agu (2. tur) eki: TIP ekseni — bkz. altkategori-sinifla.py K5 ──
        "Bardaklık",
        "Dış Aksam",
        "Kapı ve Cam",
        "Klima ve Havalandırma",
        "Koltuk ve Kemer",
        "Konsol ve Torpido",
        # `Montaj ve Bağlantı` -> ADI DEGISTI (K6): "baglanti" tarafina tabloda tek terim
        # dusmuyordu; olculen icerik montaj/kapak/tutucu/klips/tapa/braket.
        "Montaj Parçaları ve Klipsler",
        "Motor Bölümü",
        # `Multimedya ve Elektronik` -> IKIYE BOLUNDU (K7): iki ayri merkez olculdu.
        "Ses ve Multimedya",
        "Sürüş Kumandaları",
        "Tavan ve Güneşlik",
        "Tekerlek ve Jant",
        "Telefon ve Şarj",
        "Yakıt ve Egzoz",
        "İç Aksam",
    ),
    "Motosiklet": (
        "Aydınlatma",
        "Depo ve Yakıt",
        "Elektrik",
        "Fren ve Süspansiyon",
        "Gidon ve Kumandalar",
        "Grenaj ve Kaporta",
        "Gösterge ve Kokpit",
        # Otomobil ile AYNI ad (ortak etiket ilkesi): rename + bolme burada da uygulandi.
        "Montaj Parçaları ve Klipsler",
        "Motor Bölümü",
        "Sele ve Sehpa",
        "Ses ve Multimedya",
        "Tekerlek ve Aktarma",
        "Telefon ve Şarj",
        "Çanta ve Bagaj",
    ),
    "Dekorasyon": (
        "Bitki ve Saksı",
        "Dekoratif Objeler",
        "Duvar ve Raf",
        "Heykel ve Figür",
        "Mum ve Aydınlatma",
        "Servis ve Sunum",
        "Vazo ve Çiçeklik",
    ),
    "Ev": (
        "Banyo",
        "Duvar ve Askı",
        "Mutfak",
        "Saklama ve Düzen",
    ),
    "Elektronik": (
        "Cihaz Parçaları",
        "Ev ve Mutfak Cihazları",
        "Ses ve Müzik",
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


# ─────────────────────────────────────────────────────────────────────────────
# UYUM EKSENI (`uyum`) — urunun NEYE UYDUGU. Kategori "urun NE" der, uyum "neye takilir".
#
# NEDEN BURADA (altkategori/tur/stokta ile AYNI gerekce): bu alan ileride hem urun_hash'e
# hem D1 kolonuna girecek. Iki yerde AYRI turetilseydi hash "degismedi" derken kolon
# degisir (ya da tersi) ve D1 SESSIZCE eski degeri servis ederdi. Tek fonksiyon = tek kaynak.
#
# 🔴 BU TURDA TUKETICI YOK — bilerek: urun_hash'e KATILMADI, d1-sema/d1-sync'e kolon
# EKLENMEDI, index.html/build.py'ye DOKUNULMADI. Sozluk once main'e iner, parti SONRA
# yazilir; ters sira fail-closed reddedilir (`Elektrik` kaleminde olculdu).
#
# SEMA (tools/paket-uyum-ekseni.md §2): dizi; her oge
#   {"marka": <KAPALI kumeden, ZORUNLU>, "model": <opsiyonel>, "motor": <opsiyonel>,
#    "yil": [bas, son] ya da [], "oem": <opsiyonel>}
# Alan YOKSA / bos dizi ise kayit UYUMSUZDUR — bu GECERLIDIR, hata degil (16.874 kaydin
# tamami bugun boyle; olculdu: `uyum` dolu kayit = 0).
#
# 🔴 K2 — SUPHE DAIMA "MARKA DEGIL" YONUNE DUSER. Modeli yanlislikla marka saymak
# musteriye SAHTE MARKA SAYFASI uretir (geri alinamaz itibar zarari); markayi yanlislikla
# model saymak yalnizca o sayfayi acmaz (gorunmez, geri alinabilir).
#
# ── K3 BUDAMA (olculdu 2026-08-02, 16.874 kayit / 1.704 tekil `marka` jetonu) ─────────
# Girdi bir ONERIDIR: sinyal tabanli siniflandirma 169 marka / 806 model / 729 belirsiz
# verdi. Uc kume asagida TEK TEK yargilanarak ayrildi ve UCU BIRDEN saklanir; birlesimleri
# ONERININ TAMAMINA esittir (kapi bu aritmetigi CALISTIRARAK dogrular) — boylece budama
# karari denetlenebilir ve elenen bir jeton sessizce geri sizamaz.
#
# OLCULEN DUZELTME: mimarin "169'un icinde Focus/F-150/Fiesta/Golf/E46/Mustang gibi acik
# modeller var" beklentisi ADRESINDE DEGILDI — olculdu, o jetonlarin HICBIRI marka
# onerisinde degil (Focus/F-150/Fiesta/Golf/E46/Mustang/Corsa/Mondeo/Transit/Ranger/
# Maverick = `model`, Tacoma/Sierra = `belirsiz`). 169'daki gercek kirlilik baska tipte:
# jenerik kelimeler, standart kodlari, ikiz yazimlar ve PARCA URETICILERI.
#
# AYIRMA OLCUTU (uygulanabilir, tek cumle): jeton bir EV SAHIBI mi adlandiriyor —
# uretilen parcanin TAKILDIGI arac/tekne/motor/makine/cihaz — yoksa TAKILAN sarf/parcanin
# ureticisi mi? "Bu urun <X> ...'a takilir" anlamli ise UYUM; urunun KENDISI o markanin
# malı ise (buji, tutya, yapistirici, temizleyici, zimpara) URETICI.
UYUM_MARKA_IZINLI = frozenset({
    "Abus", "Alfa Romeo", "Anet", "Apple", "Aprilia", "Arora", "Attwood", "Audi",
    "Aukey", "BMW", "BYD", "Bafang", "Baier", "Bajaj", "Baofeng", "Beneteau", "Bentley",
    "Black and Decker", "Borbet", "Briggs & Stratton", "CFMoto", "Cadillac", "Canon",
    "Chrysler", "Citroen", "Cupra", "DJI", "Dacia", "Daewoo", "Datsun", "Dimplex",
    "Ducati", "Dürkopp Adler", "Einhell", "Fiamma", "Flashforge", "Ford", "GMC",
    "Geely", "Grunhelm", "Haval", "Honda", "Hummer", "Husqvarna", "Huter", "Hyundai",
    "IKEA", "Isuzu", "Itiwit", "Iveco", "Jabsco", "Jaguar", "Jawa", "Jeep",
    "John Deere", "KTM", "Kanuni", "Kayo", "Kazuma", "Kuba", "Kärcher", "Lalizas",
    "Lancia", "Land Rover", "Lifetime", "Line 6", "MAN", "Magic Bullet", "Mahindra",
    "Mariner", "Massey Ferguson", "Mazda", "Mercedes", "Mercury", "Miele", "Mini",
    "Minn Kota", "Mitsubishi", "Mondial", "Motoran", "Motorola", "Moulinex", "NODET",
    "Nikon", "Nissan", "OMC", "ObdEleven", "Old Town", "Opel", "Pelican", "Peugeot",
    "Philips", "Porsche", "Prusa", "Puch", "Pössl", "Quechua", "Quicksilver", "Renault",
    "Rial", "Rover", "Rule", "Ryobi", "Saab", "Saeco", "Scania", "Scarlett", "Seaflo",
    "Seat", "Segway", "Sherwood", "Shimano", "Sigma", "Skoda", "Skyteam", "Sodastream",
    "Speeduino", "SsangYong", "Stihl", "Suzuki", "TMC", "Tesla", "Thermomix", "Tofaş",
    "Tohatsu", "Toyota", "Twin Disc", "Vespa", "Vetus", "Volkswagen", "Volvo",
    "Weinsberg", "Xbox", "Xiaomi", "Yamaha", "Yunteng", "Zelmer", "Zodiac", "Zontes",
    # ── MIMAR ELIYLE EKLENEN (asagidaki UYUM_MARKA_MIMAR_EKI ile AYNI 30 jeton) ──
    # 1. tur: paket §2'nin ornek degerleri.
    "Volvo Penta", "Yanmar",
    # 2. tur, A grubu (17) — arac / tekne / deniz motoru markasi. Heuristik bunlari
    # KACIRMISTI; kok sebep olculdu: ev sahibini "baskin tek partneri var" diye model
    # saniyor (`Vauxhall` 71 kaydin 68'inde `Opel` ile geciyor).
    "Chery", "Chevrolet", "Dodge", "Fiat", "Infiniti", "Jeanneau", "Johnson Pump",
    "Kawasaki", "Kia", "Lamborghini", "Lexus", "Maserati", "Mercruiser", "Scion",
    "Smart", "Subaru", "Vauxhall",
    # 2. tur, B grubu (11) — ev sahibi CIHAZ/EKIPMAN ureticisi (kumedeki DJI/Canon/Prusa
    # ile ayni sinif): bir GoPro aparati GoPro'ya TAKILIR. Adetlerin dusuk olmasi (1-12)
    # olcut DEGIL: sozluk "gecerli mi"yi belirler, "sayfasi acilir mi"yi degil — ikincisi
    # paket §4'teki sayfa acma esigi N'in isidir.
    "Anker", "Garmin", "GoPro", "Kenwood", "Krups", "Pioneer", "Raspberry Pi", "Remis",
    "Rode", "Samsung", "Sony",
})

# 🔴 ONERI DISINDAN, MIMAR ONAYIYLA eklenen jetonlar. AYRI tutulmalari SART: budama
# aritmetigi (S2) "sozluk = yargilanmis oneri" der; onaysiz bir jeton o esitligi kirar.
# Bu kume, esitligi kiran TEK mesru yoldur ve her uyesi ADIYLA kayda gecer.
#
# K2 NETLESTIRILDI (mimar, 2 Agu): "belirsiz jeton VARSAYILAN olarak modeldir; mimar
# ACIK gerekceyle ev-sahibi marka olarak kabul edebilir." Mutlak degil, VARSAYILAN.
#   `Volvo Penta` (51 kayit, Codex `belirsiz`) — deniz motoru markasi. Okan'in talebindeki
#     iki ornekten biri BIREBIR bu; paket §2 ornegi de buna dayaniyor. Kumede olmamasi
#     amiral kullanim durumunun calismamasi demekti.
#   `Yanmar` (7 kayit, Codex `model`) — deniz motoru markasi, paket §2'nin ikinci ornegi.
# Ikisi de bu turun kendi olcutuyle TARTISMASIZ EV SAHIBI: parca onlara TAKILIR.
#
# ⚠️ `Volvo` ile `Volvo Penta` AYRI EV SAHIPLERIDIR (otomobil ile deniz motoru). Tek jetona
# indirilmezler ve model_normalize onlari CAKISTIRMAZ (`volvo` != `volvopenta`) — kapi bunu
# AYRI bir iddia olarak olcer (V13), cunku "Penta" ekini kirpan bir normalizasyon iki farkli
# uyum evrenini sessizce tek sayfaya yigardi.
UYUM_MARKA_MIMAR_EKI = frozenset({
    "Volvo Penta", "Yanmar",
    "Chery", "Chevrolet", "Dodge", "Fiat", "Infiniti", "Jeanneau", "Johnson Pump",
    "Kawasaki", "Kia", "Lamborghini", "Lexus", "Maserati", "Mercruiser", "Scion",
    "Smart", "Subaru", "Vauxhall",
    "Anker", "Garmin", "GoPro", "Kenwood", "Krups", "Pioneer", "Raspberry Pi", "Remis",
    "Rode", "Samsung", "Sony",
})

# 🔴 REDDEDILEN ADAYLAR (2 Agu, mimar karari) — kayda geciyor ki bir sonraki tur ayni
# jetonlari yeniden "kesfetmesin" ve karar yeniden tartisilmasin:
#   `PSA` (15) · `VAG` (13)  grup kisaltmasi, marque DEGIL — musteri "VAG parcasi" aramaz
#   `Alpine` (5)             cift anlam: Renault Alpine (marque) / Alpine oto ses (cihaz)
#   `Brodit` (2)             telefon tutucu ureticisi, sinirda
#   `Gurtner` (2)            karburator ureticisi -> URETICI tarafi, uyum ekseni degil
#   `Sierra` (149)           🔴 SOZLUK sorunu DEGIL, VERI sorunu — asagida.
# `Sierra` jetonu IKI FARKLI seyi adlandiriyor ve dogru cozum KAYIT BASINA ayrismadir.
# OLCULDU: 149 kaydin 141'i kategori `Marin`, 8'i `Otomobil`; otomobil tarafindaki
# partnerler `Ford`(4), `Suzuki`(4), `Samurai`(3), `Jimny`(3), `SJ413`(3) — yani orada
# `Sierra` bir MODEL (Ford/GMC/Suzuki Sierra). Marin tarafindaki 141 kayit ise deniz
# yedek parca markasidir. Karar BACKFILL ANINDA verilecek (MaCiT duzlemi), sozlukte degil.
URETICI_MARKA_MIMAR_EKI = frozenset({"Bosch"})

# URETICI EKSENI — GERCEK markalardir ama UYUM ekseni DEGILDIR: bunlar takilan sarf/parcanin
# ureticisidir (buji, tutya, dolgu/yapistirici, tekne boyasi, temizleyici, zimpara, direksiyon
# kablosu). "Bu urun NGK'ya takilir" cumlesi anlamsizdir; "bu urun bir NGK bujisidir" anlamlidir.
# AYRI kume tutulmasinin sebebi: (1) uyum[].marka'da GECERSIZ olmalari fail-closed sart —
# aksi halde "NGK" diye SAHTE bir uyum sayfasi acilir; (2) tek kumede eritilselerdi bu yargi
# kaybolur ve bir sonraki tur onlari yeniden "marka" diye geri koyardi. Bu turda TUKETICISI
# YOKTUR; ileride "uretici/parca markasi" filtresi gerekirse kaynak burasidir.
URETICI_MARKA = frozenset({
    "Bosch",         # 🔴 MIMAR EKI (oneri disi): el aleti = ev sahibi, oto elektrik
                     # parcasi = uretici. Bu CIFT SINIF tam olarak bu kumenin tanimidir;
                     # supheli jeton uyum ekseninde GECERSIZ olur (fail-closed yon).
    "3M",            # zimpara / bant / yapistirici
    "Champion",      # buji (ayrica jeneratör — belirsiz, fail-closed yonu URETICI)
    "Denso",         # buji / elektrik parcasi
    "International", # yat boyasi (AkzoNobel) — ayrica jenerik Ingilizce kelime, capraz-anlamli
    "Martyr",        # tutya / anot
    "NGK",           # buji
    "Nordlinger",    # dolgu / yapistirici
    "Seafirst",      # tekne boyasi
    "Sika",          # dolgu / yapistirici
    "Star Brite",    # tekne bakim kimyasali
    "Teak Wonder",   # tik bakim kimyasali
    "Tecnoseal",     # tutya / anot
    "Teleflex",      # direksiyon/kumanda kablosu (mimarin ornegi)
})

# ELENEN — "marka" onerildi ama MARKA DEGIL (ya da kanonik yazim DEGIL). Kume SAKLANIR ki
# elenmis bir jeton bir sonraki turda sessizce geri sizmasin ve budama aritmetigi
# CALISTIRILABILIR kalsin (kapi: uc kume ayrik + birlesim = 169).
#   jenerik kelime / urun tipi : Generic, Turbo, Motorhome, Android, Victoria
#   motor / donanim adi        : Coyote (Ford 5.0 motoru)
#   standart / kod             : DIN1, CTC
#   tanimsiz tekil jeton       : Canora, DiveTalk, RocketStart, STORM Racing, Toplife
#   jeneriklesmis tur adi      : Mobylette (moped tur adi; Motobecane model hatti)
#   IKIZ YAZIM (K4 kaybeden)   : MINI (Mini=24 > MINI=1) · Mercedes-Benz (Mercedes=1011 >
#                                Mercedes-Benz=21) · Ssangyong (SsangYong=6 > Ssangyong=3)
UYUM_MARKA_ELENEN = frozenset({
    "Android", "CTC", "Canora", "Coyote", "DIN1", "DiveTalk", "Generic", "MINI",
    "Mercedes-Benz", "Mobylette", "Motorhome", "RocketStart", "STORM Racing",
    "Ssangyong", "Toplife", "Turbo", "Victoria",
})

# Codex'in URETTIGI oneri kumesinin buyuklugu. Uc kumenin birlesimi buna ESIT olmali —
# esit degilse ya bir jeton sessizce dusmus ya da sozluge oneride OLMAYAN bir deger
# elle eklenmistir. Ikisi de denetimsiz genisleme, kapi KIRMIZI yakar.
UYUM_MARKA_ONERI_SAYISI = 169

# 🔴 SAYI KORUMASI YETMEZ, KIMLIK KORUMASI SART (bagimsiz curutucu olctu, 2 Agu).
# Onceki hal yalnizca BIRLESIMIN BUYUKLUGUNU sabitliyordu. Bu, bir jetonu ELENEN'den
# cikarip IZINLI'ye TASIMAYI gormuyordu: birlesim sabit kaliyor (200), S1 ayrikligi
# bozulmuyor (jeton TASINDI, kopyalanmadi), S4 ikiz uretmiyor. Curutucu tam olarak bunu
# yapti — `Turbo` ELENEN'den IZINLI'ye tasindi ve kapi YESIL kaldi. Yani "elenen jeton
# sessizce geri sizamaz" iddiasi FIILEN YANLISTI: `Generic`/`Motorhome`/`Coyote` gibi
# bilerek elenmis bir jeton denetimsiz sekilde geri donup SAHTE MARKA SAYFASI acabilirdi
# — K2'nin onlemek icin var oldugu seyin ta kendisi.
#
# Cozum: YARGILANMIS BOLUMLEMENIN kimligi donduruluyor. Imza uc bolumun HER BIRI icin
# AYRI hesaplanir; boylece degisim oldugunda HANGI kovanin oynadigi da gorunur (tek
# birlesik hash "bir sey degisti" der, hangisi oldugunu SOYLEMEZ).
#
# ⚠️ BU IMZA DEGISMEMELI. Yargilanmis bolumleme KAPANMIS bir karardir; sozlugu genisletme
# yolu MIMAR EKI kumeleridir ve onlar imzaya GIRMEZ (yani mesru genisleme imzayi
# BOZMAZ). Imza kirmizi yaniyorsa ya kapanmis bir karar yeniden acilmistir — ki bu
# BILEREK ve GORUNUR yapilmali, imza da elle guncellenmeli — ya da jeton kaymasi vardir.
UYUM_MARKA_YARGI_IMZA = ("8d0bdf607d0079f9", "e6c2f91212ba9f04", "cec09f9fee6f6211")
# Bolum buyuklukleri: imza kirmizi yandiginda okunabilir bir ilk teshis verir.
UYUM_MARKA_YARGI_SAYILARI = (139, 13, 17)


def uyum_yargi_bolumleri():
    """YARGILANMIS bolumleme: (izinli−eki, uretici−eki, elenen). Mimar eki DISARIDA."""
    return (sorted(UYUM_MARKA_IZINLI - UYUM_MARKA_MIMAR_EKI),
            sorted(URETICI_MARKA - URETICI_MARKA_MIMAR_EKI),
            sorted(UYUM_MARKA_ELENEN))


def uyum_yargi_imzasi():
    """Yargilanmis bolumlemenin KIMLIK imzasi — bolum basina bir ozet."""
    return tuple(
        hashlib.sha256(json.dumps(b, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
        for b in uyum_yargi_bolumleri())

# `uyum` ogesinde TANINAN alanlar. Kume KAPALI: taninmayan anahtar REDDEDILIR (sessizce
# YUTULMAZ). Yutulsaydi yazim hatasi (`yıl`, `oem_no`) veri kaybi olarak sessizce gecerdi.
UYUM_ALANLARI = ("marka", "model", "motor", "yil", "oem")

# Serbest metin alanlari (model/motor/oem) icin BEYAZ LISTE — kara liste DEGIL:
# gorulmemis bir enjeksiyon bicimi sessizce gecmesin. Olculdu (1.704 jeton): gecen
# ozel karakterler '-' 82, '.' 8, '&' 3, '/' 2, '+' 1; harflerin TAMAMI Latin; en uzun
# jeton 18 karakter, en cok kelime 3.
#
# AYIRAC ile EK ayrimi KASITLI: ayiraca KONUM kurali uygulanir (asagida), eke uygulanmaz.
#   AYIRAC " -./"  yol/slug anlami tasir -> yalniz IKI alfanumerigin ARASINDA durabilir.
#   EK     "+"     yol anlami YOK, mesru model sonekidir (olculdu: `206+` Peugeot modeli).
# '&' BILEREK HICBIRINDE DEGIL (HTML varlik isareti). OLCULEN BEDEL: bu kural katalogun
# 1.704 jetonundan 3'unu reddeder — 'Briggs & Stratton' (zaten KAPALI marka kumesinde,
# serbest metin kuralindan gecmesi GEREKMEZ), 'K&N' (filtre ureticisi, uyum ekseni degil),
# 'Town & Country' (Chrysler modeli — backfill'de ELE kalir, sayiyla raporlanir).
UYUM_SERBEST_AYIRAC = frozenset(" -./")
UYUM_SERBEST_EK = frozenset("+")
UYUM_SERBEST_AZAMI_UZUNLUK = 40
UYUM_SERBEST_AZAMI_KELIME = 5

# `yil` araligi. 0 = ACIK UC ve YALNIZ son elemanda gecerlidir ([2015, 0] = "2015'ten beri").
# [0, 2015] REDDEDILIR: acik BAS diye bir sey yok, 0 orada veri hatasidir.
UYUM_YIL_ACIK_UC = 0
UYUM_YIL_EN_ERKEN = 1900
UYUM_YIL_EN_GEC = 2100

_MODEL_AYIRAC_RE = re.compile(r"[.\-\s]")


def _latin_harf(c):
    """Harf VE Latin yazisinda mi? Kiril/Yunan homoglifi ('А', 'Ѕ') buradan GECMEZ —
    gorunuste ayni, normalize sonucu FARKLI bir jeton uretir (sessiz ikiz uretici)."""
    return c.isalpha() and unicodedata.name(c, "").startswith("LATIN")


def uyum_marka_kanonik(deger):
    """Ham jetonu KANONIK markaya indirir ya da "" (kume disi / bicimsiz).

    🔴 SESSIZ KIRPMA YOK — uyelik testi HAM deger uzerinde yapilir. ' Ford' KABUL EDILMEZ;
    kabul edilseydi (strip() uyelik testinin ICINE alinsaydi) kataloga ' Ford', D1'e 'Ford'
    giderdi: site ile Ege ayni urunu FARKLI yazimla gorurdu ve hicbir hash/senkron ekseni
    bunu yakalamazdi. Bu tam olarak `altkategori`de OLCULEN kusurdur (1 Agu, ' Elektrik').

    KABUL EDILEN deger AYNEN doner -> "kataloga yazilan metin" ile "D1'e giden metin"
    ayrisamaz (ucuncu bir hal yoktur).
    """
    if not isinstance(deger, str):
        return ""
    if deger not in UYUM_MARKA_IZINLI:
        return ""
    return deger


def model_metin(deger):
    """`model`/`motor`/`oem` alanlarinin KANONIK metin bicimi — TEK KAYNAK.

    altkategori_metin ile AYNI SOZLESME: sebebi() kanonik OLMAYAN her degeri REDDEDER,
    kanonik() ise kabul edilen degeri BU fonksiyondan gecirir. Yani katalog metni ile D1
    metni ayni fonksiyondan turer ve AYRISAMAZ.
    """
    if not isinstance(deger, str):
        return ""
    return deger.strip()


def model_normalize(deger):
    """Model IKIZ tespiti icin katlama anahtari — kataloga/D1'e ASLA YAZILMAZ.

    K4: ayni araci anlatan farkli ham yazimlar TEK anahtara duser
    (`F-150` == `F150`, `XSR 700` == `XSR700`, `ID.Buzz` == `ID Buzz`, `Zoé` == `Zoe`),
    ama FARKLI araclar ayrik kalir (`Focus` != `Focuss`).

    Model kumesi ACIK oldugu icin onceden sayilamaz; ikiz ancak KATLAMA ile gorulur.
    Katlama norm()'dan (sitenin TEK kaynagi) turer -> ikinci bir Turkce kucultme kopyasi
    dogmaz. Uzerine NFKD aksan soyme + [.-bosluk] silme gelir.
    """
    m = model_metin(deger)
    if not m:
        return ""
    m = norm(m)
    m = "".join(c for c in unicodedata.normalize("NFKD", m)
                if not unicodedata.combining(c))
    return _MODEL_AYIRAC_RE.sub("", m)


# Kapali kumenin NORMALIZE anahtarlari. Modul yuklenirken BIR KEZ turetilir — kumenin
# KENDISINDEN, ikinci bir liste tutulmaz (ikiz tanim yasagi).
_UYUM_MARKA_ANAHTARLARI = frozenset(model_normalize(m) for m in UYUM_MARKA_IZINLI)


def marka_varyanti_sebebi(ad, deger):
    """model/motor degeri KAPALI kumedeki bir markanin YAZIM VARYANTI mi? Sebep ya da None.

    🔴 NEDEN SART (bu tur olculdu): kumeye `Kia` ve `Smart` girdi; katalogda `KIA` (1) ve
    `SMART` (1) yazimlari da var. Kural olmasaydi backfill `marka: "Kia"` ile `model: "KIA"`
    yazabilir, AYNI gercek iki ayri alanda iki ayri sayfa uretirdi — S4'un sozluk ICINDE
    yasakladigi ikizin marka/model SINIRINDAN sizan hali. Sinir da kapatiliyor.

    OLCUM (16.874 kayit, 1.704 jeton): kumeye duson AMA kanonik olmayan yazim TAM 7 tane —
    `BaoFeng`(1), `Citroën`(4), `Ikea`(2), `KIA`(1), `MINI`(1), `SMART`(1), `Ssangyong`(3).
    Yedisi de gercekten MARKA yazimidir, yani kuralin YANLIS-POZITIFI OLCULEN VERIDE 0.
    """
    n = model_normalize(deger)
    if not n or n not in _UYUM_MARKA_ANAHTARLARI:
        return None
    return ("%s KAPALI marka kumesindeki bir markanin YAZIM VARYANTI (%r -> %r) — marka "
            "`marka` alanina yazilir, model/motor alanina DEGIL" % (ad, deger, n))


# ─────────────────────────────────────────────────────────────────────────────
# BILESIK MARKA ADI — `Mercedes-Benz` -> `Mercedes` (Okan hukmu, tools/paket-bilesik-marka.md)
#
# 🔴 NEDEN AYRI FONKSIYON, `marka_varyanti_sebebi()`'ye EKLENMEDI: yukaridaki 7'li kume
# olculmus bir YAZIM VARYANTI listesidir (`KIA`/`Kia`, `MINI`/`Mini` — ayni adin farkli
# YAZIMI). `Mercedes-Benz` yazim varyanti DEGILDIR: kanonik markayi ICEREN, kendi basina
# dogru yazilmis bir BILESIK ADDIR. Iki kural sinifini tek fonksiyonda eritmek 7'li capayi
# anlamsiz kilardi (MaCiT'in kova ayrimi o capaya dayaniyor). Ayri sinif -> ayri tablo,
# ayri fonksiyon, ayri iddia. Bu blok `marka_varyanti_*`nin BAYRAGINI OKUMAZ ve tersi de
# dogrudur -> iki BAGIMSIZ kod yolu, iki AYRI iddia ([[beyan-edilmis-survivor]]).
#
# 🔴 GENEL NORMALIZASYON YASAK. "Tire/bosluk kirp, iceriyorsa esle" turu bir kural
# YAZILMAZ: mesru jetonlari yer (OLCULEN katalog verisi — `F-150`, `Rolls-Royce`,
# `D2-55`, `206+`, `K5`). Tablo KAPALI ve ELLE yazilmistir; tabloda OLMAYAN bir bilesik ad
# sessizce eslenmez, OLDUGU GIBI kalir (fail-closed = uydurma esleme YOK).
#
# ⚠️ TEK TOHUM. Okan yalnizca bu esitligi verdi. Tablonun buyumesi GORUNUR bir karardir;
# kabul testi tablonun ICERIGINI dondurur, yani sessiz genisleme kapi KIRMIZI yakar.
BILESIK_MARKA_KANONIK = {
    "Mercedes-Benz": "Mercedes",
}


def bilesik_marka_kanonik(deger):
    """Bilesik marka adini KAPALI tablodan kanonik markaya indirir.

    Tabloda YOKSA deger AYNEN doner (uyum_marka_kanonik gibi "" DONDURMEZ: burasi bir
    UYELIK testi degil, bir ESLEME'dir; eslemesi olmayan deger gecerli olabilir).
    Metin olmayan deger de aynen doner -> cagiran taraf tip kontrolunu kaybetmez.
    """
    if not isinstance(deger, str):
        return deger
    return BILESIK_MARKA_KANONIK.get(deger, deger)


def bilesik_marka_sebebi(deger):
    """Deger KANONIKLESTIRILMESI GEREKEN bir bilesik marka adi mi? Sebep ya da None.

    UYELIK testidir (tablonun ANAHTARI mi), esleme sonucuna BAKMAZ: tablonun degeri
    yanlis yazilsa bile "bu deger tabloya tabidir" yargisi ayakta kalir -> iki eksen
    (esleme dogru mu / hangi kayitlar tabloya tabi) ayri ayri olculebilir.
    """
    if not isinstance(deger, str) or deger not in BILESIK_MARKA_KANONIK:
        return None
    return ("%r BILESIK marka adidir ve kanonik markaya indirilir (%r) — kapali tablo, "
            "genel normalizasyon YOK" % (deger, BILESIK_MARKA_KANONIK[deger]))


def arama_jetonu_korunuyor(u, jeton):
    """`jeton` sorgusu bu kaydi HALA buluyor mu? (sitenin KENDI ucluşu ile olculur)

    haystack() + tokenlar() + esles() = index.html'in arama yolunun birebir karsiligi.
    Ikinci bir arama kopyasi YAZILMAZ: kopya yazilsaydi "kapida yesil, sitede kayip"
    ayrismasi dogar ve tam da onlemek istedigimiz sessiz kayip olculemez hale gelirdi.
    """
    return esles(haystack(u), tokenlar(jeton))


def bilesik_marka_kanoniklestir(u):
    """Kaydin `marka` dizisinin BILESIK-AD kanoniklestirilmis hali — ARAMA JETONU KAYIPSIZ.

    🔴 BU PAKETIN VARLIK SEBEBI. `marka` yalnizca bir etiket degil, ARAMA METNIDIR
    (haystack() ve ege_govde() onu okur). `Mercedes-Benz` -> `Mercedes` yazildiginda
    "Mercedes-Benz" sorgusu tek bir jetona ayrisir (`mercedes-benz`) ve ALT-DIZE olarak
    aranir; ham yazim kaydin arama metninden tamamen dustuyse urun o sorguyla BULUNAMAZ.
    Hicbir alarm calmaz — sessiz kayip sinifi.

    OLCULDU (16.874 kayit): `marka` alaninda `Mercedes-Benz` tasiyan 21 kayit var; duz
    kanoniklestirme bunlarin 5'inde sorgu jetonunu DUSURUYOR (kalan 16'sinda ham yazim
    baslik/aciklamada oldugu icin ayakta kaliyor).

    KURAL: kanoniklestirme once yapilir, SONRA sonuc kaydin arama metninde OLCULUR. Jeton
    dustuyse ham yazim dizinin SONUNA ARAMA TAKMASI olarak korunur.
      - Kayip YOKSA takma EKLENMEZ -> arama yuzeyi GENISLEMEZ (gereksiz genisleme de bir
        davranis degisikligidir; `Mercedes` tasiyan 1.011 kayit bundan ETKILENMEZ).
      - `marka` cipleri/sayfalari zaten katliyor (index.html markaKatla: `Mercedes-Benz`
        -> `Mercedes`, ayni urunde baz+varyant cifti TEK sayilir) -> takma SAHTE marka
        sayfasi ACMAZ, yalnizca arama metnini korur.
    Bilesik ad TASIMAYAN kayitta cikti girdiyle BIREBIR aynidir (regresyon 0).
    """
    marka = list(u.get("marka") or [])
    yeni, dusen = [], []
    for m in marka:
        k = bilesik_marka_kanonik(m)
        if k != m:
            dusen.append(m)
        if k not in yeni:
            yeni.append(k)
    if not dusen:
        return yeni
    aday = dict(u, marka=yeni)
    for ham in dusen:
        if not arama_jetonu_korunuyor(aday, ham) and ham not in yeni:
            yeni.append(ham)
    return yeni


def _serbest_sebebi(ad, deger):
    """model/motor/oem gibi ACIK metin alani gecerli mi? Sebep metni ya da None.

    BOS/eksik GECERLIDIR (alanlar opsiyonel). Kural BEYAZ LISTEDIR: yalniz Latin harf,
    rakam ve UYUM_SERBEST_AYIRAC gecer -> HTML/SQL benzeri her deger ('<b>', "' OR 1=1--",
    '${x}', ';DROP') ve Latin disi homoglif REDDEDILIR.
    """
    if deger is None:
        return None
    if not isinstance(deger, str):
        return "%s metin olmali, %s degil" % (ad, type(deger).__name__)
    d = model_metin(deger)
    # 🔴 FAIL-CLOSED, SESSIZ DUZELTME DEGIL (altkategori_sebebi ile ayni cizgi).
    if d != deger:
        return ("%s KANONIK DEGIL: %r — bas/son bosluk tasiyor; kanonik bicim %r"
                % (ad, deger, d))
    if not d:
        return None
    if len(d) > UYUM_SERBEST_AZAMI_UZUNLUK:
        return "%s cok uzun (%d > %d karakter)" % (ad, len(d), UYUM_SERBEST_AZAMI_UZUNLUK)
    if len(d.split()) > UYUM_SERBEST_AZAMI_KELIME:
        return "%s cok fazla kelime (%d > %d)" % (ad, len(d.split()),
                                                  UYUM_SERBEST_AZAMI_KELIME)
    govde = False
    for c in d:
        if c.isdigit() or _latin_harf(c):
            govde = True
            continue
        if c in UYUM_SERBEST_AYIRAC or c in UYUM_SERBEST_EK:
            continue
        return ("%s izinsiz karakter (%r) — beyaz liste: Latin harf, rakam, %r"
                % (ad, c, "".join(sorted(UYUM_SERBEST_AYIRAC | UYUM_SERBEST_EK))))
    if not govde:
        return "%s alfanumerik govde tasimiyor (%r)" % (ad, d)
    # 🔴 AYIRAC KONUMU DA KURALDIR — karakter beyaz listesi TEK BASINA YETMEZ (OLCULDU:
    # '../../etc/passwd' yalniz '.', '/' ve harf tasidigi icin karakter suzgecinden GECTI
    # ve V10 ekseni bu turda KIRMIZI yandi). Ayirac ancak IKI alfanumerigin ARASINDA
    # durabilir: bas/son ayirac ve ARDISIK ayirac reddedilir -> '..', '//', './' ve
    # bas/son nokta bicimleri kapanir. Mesru veriyi kesmez (olculdu): 'F-150', '5.0',
    # 'ID.Buzz', '85.12.345/A', 'Quad Lock', '206+' gecer.
    if d[0] in UYUM_SERBEST_AYIRAC or d[-1] in UYUM_SERBEST_AYIRAC:
        return "%s ayirac ile basliyor/bitiyor (%r)" % (ad, d)
    for onceki, simdiki in zip(d, d[1:]):
        if onceki in UYUM_SERBEST_AYIRAC and simdiki in UYUM_SERBEST_AYIRAC:
            return ("%s ARDISIK ayirac (%r) — yol gecisi/bicim bozuklugu sinyali"
                    % (ad, onceki + simdiki))
    return None


def uyum_yil_sebebi(deger):
    """`yil` gecerli mi? Sebep metni ya da None.

    GECERLI: [] (bilinmiyor — UYDURMA YOK) · [bas, son] · [bas, 0] (acik uc).
    GECERSIZ: tek elemanli, ikiden fazla, metin ("2015"), bool (True), ters aralik,
    acik BAS ([0, 2015]), aralik disi yil.
    """
    if deger is None:
        return None
    if not isinstance(deger, list):
        return "yil dizi olmali, %s degil" % type(deger).__name__
    if not deger:
        return None
    if len(deger) != 2:
        return "yil [bas, son] olmali (%d elemanli) — acik uc icin [bas, 0]" % len(deger)
    bas, son = deger
    for ad, v in (("bas", bas), ("son", son)):
        # 🔴 bool BILEREK ELENIR: Python'da isinstance(True, int) -> True. Kontrol
        # olmasaydi [True, False] "[1, 0]" diye GECERDI (stokta_kanonik'teki tuzagin aynisi).
        if isinstance(v, bool) or not isinstance(v, int):
            return "yil %s tam sayi olmali, %r degil" % (ad, v)
    if not (UYUM_YIL_EN_ERKEN <= bas <= UYUM_YIL_EN_GEC):
        return ("yil bas %d araligin disinda (%d–%d) — 0 yalniz SON elemanda acik uctur"
                % (bas, UYUM_YIL_EN_ERKEN, UYUM_YIL_EN_GEC))
    if son == UYUM_YIL_ACIK_UC:
        return None
    if not (UYUM_YIL_EN_ERKEN <= son <= UYUM_YIL_EN_GEC):
        return "yil son %d araligin disinda (%d–%d)" % (son, UYUM_YIL_EN_ERKEN,
                                                        UYUM_YIL_EN_GEC)
    if son < bas:
        return "yil araligi TERS: [%d, %d]" % (bas, son)
    return None


def uyum_ogesi_sebebi(oge):
    """Tek bir `uyum` ogesi gecerli mi? Sebep metni ya da None."""
    if not isinstance(oge, dict):
        return "uyum ogesi sozluk olmali, %s degil" % type(oge).__name__
    fazla = sorted(k for k in oge if k not in UYUM_ALANLARI)
    if fazla:
        return ("taninmayan alan %s — izinli: %s (yazim hatasi sessizce YUTULMAZ)"
                % (fazla, ", ".join(UYUM_ALANLARI)))
    ham = oge.get("marka")
    if uyum_marka_kanonik(ham) == "":
        return ("marka ZORUNLU ve KAPALI kumeden olmali — %r kumede YOK "
                "(kume %d deger; bosluklu/kucuk-buyuk harf farkli yazim da REDDEDILIR)"
                % (ham, len(UYUM_MARKA_IZINLI)))
    for ad in ("model", "motor", "oem"):
        sebep = _serbest_sebebi(ad, oge.get(ad))
        if sebep:
            return sebep
    for ad in ("model", "motor"):
        sebep = marka_varyanti_sebebi(ad, oge.get(ad))
        if sebep:
            return sebep
    return uyum_yil_sebebi(oge.get("yil"))


def marka_uyumdan_turet(u):
    """K5 — `marka` alaninin `uyum`dan TURETILMIS hali (tekil, ilk gorulme sirasinda).

        marka = tekillestir( uyum[].marka + uyum[].model )

    IKIZ TANIM YASAGI: `marka` ile `uyum` ayni gercegi iki yerde tutar ve SESSIZCE
    ayrisir. Kural: `uyum` varsa `marka` ondan TURETILIR, elle yazilmaz.

    🔴 MODEL DE GIRER — KURAL 2 AGU'DA DEGISTI, SEBEBI OLCULDU. Once yalniz
    `uyum[].marka` turetiliyordu. Ama bugunku `marka` alani marka VE model karisimidir
    (olculdu: 6.918 kayit tam 2 elemanli, `["Ford","Focus"]` bicimi) ve `marka`
    haystack()/ege_govde() araciligiyla ARAMA metnine giriyor. Yalniz markadan
    turetseydik backfill iner inmez `Focus` haystack'ten DUSER ve "focus" aramasi
    yalnizca baslik/aciklamadan eslesirdi: SESSIZ bir arama kaybi, hicbir alarm calmaz.
    Model de girince `marka` bugunku anlamini BIREBIR korur -> arama yuzeyi degismez,
    parite riski sifir ve haystack genisletmesi backfill'i BLOKLAMAZ (paket §5'teki
    sira bagimliligi kalkti).

    SIRA KASITLI: her oge icin ONCE marka SONRA model -> bugunku `["marka", "model"]`
    dizilimi korunur. `motor`/`oem` GIRMEZ: bunlar bugun `marka` alaninda yok, eklemek
    arama metnini GENISLETIR ve pariteyi bu sefer TERS yonde kaydirirdi.
    """
    turetilen = []
    for oge in (u.get("uyum") or []):
        if not isinstance(oge, dict):
            continue
        jetonlar = (uyum_marka_kanonik(oge.get("marka")),
                    model_metin(oge.get("model")))
        for deger in jetonlar:
            if deger and deger not in turetilen:
                turetilen.append(deger)
    return turetilen


def uyum_sebebi(u):
    """Kaydin `uyum` alani gecerli mi? Sebep metni ya da None (gecerli).

    ALAN YOK / None / [] -> GECERLI (opsiyonel; bugun 16.874 kaydin TAMAMI boyle).
    """
    deger = u.get("uyum")
    if deger is None:
        return None
    if not isinstance(deger, list):
        return "uyum dizi olmali, %s degil" % type(deger).__name__
    if not deger:
        return None
    for i, oge in enumerate(deger):
        sebep = uyum_ogesi_sebebi(oge)
        if sebep:
            return "uyum[%d]: %s" % (i, sebep)
    imzalar = [json.dumps([o.get(k) for k in UYUM_ALANLARI], ensure_ascii=False,
                          sort_keys=True) for o in deger]
    if len(set(imzalar)) != len(imzalar):
        return "uyum MUKERRER oge tasiyor (%d oge, %d tekil)" % (len(imzalar),
                                                                 len(set(imzalar)))
    # 🔴 K5 IKIZ KAPISI — `uyum` DOLU iken `marka` ondan TURETILMIS olmak ZORUNDA.
    # Siralama da olculur: `marka` bir DIZIDIR, uc onu SIRAYLA gosterir; sira kaymasi
    # da bir ayrismadir. `uyum` bos olan ESKI kayitlarda bu dal HIC calismaz (regresyon 0).
    turetilen = marka_uyumdan_turet(u)
    mevcut = u.get("marka")
    if mevcut != turetilen:
        return ("IKIZ TANIM: `marka` %r, `uyum`dan turetilen %r — `uyum` doluyken "
                "`marka` elle yazilmaz, TURETILIR" % (mevcut, turetilen))
    return None


def uyum_kanonik(u):
    """D1/edge'e gidecek kanonik `uyum` degeri. FAIL-CLOSED: gecersiz her deger [].

    Neden fail-closed (altkategori_kanonik deseni): .git/hooks/pre-push d1-sync'i push'tan
    ONCE kosar, CI kapisi push'tan SONRA — yani bozuk bir deger kapi kirmizi yanmadan once
    D1'e, oradan Ege'ye ve musteriye ulasabilirdi. [] yazmak urunu KAYBETTIRMEZ (urun kendi
    kategorisi altinda bulunur), yalnizca uyum yuzeyini dusurur; tools/uyum-kapisi.py ayni
    degeri KIRMIZI yakar, yani sessiz KALMAZ.

    KABUL EDILEN kayitta girdi AYNEN (derin kopya) doner -> katalog metni ile D1 metni
    BIREBIR AYNI. Derin kopya sart: cagiran donen listeyi degistirirse katalog bozulmamali.
    """
    if uyum_sebebi(u) is not None:
        return []
    return copy.deepcopy(u.get("uyum") or [])


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
        # UYUM (arac uyumlulugu): HASH'E GIRMESI SART — alan D1'de Ege'nin cevaplayabildigi
        # bir SORUYU besler ("bu parca Passat B8 2.0 TDI'ye uyar mi"). Hash kapsamasaydi bir
        # urunun uyum listesi degistiginde hash AYNI kalir, diff_plan satiri "degismemis"
        # sayar ve D1'e HIC YAZMAZDI: Ege bayat uyum servis eder, musteriye YANLIS uyum
        # vaadi gider ve hicbir alarm calmaz. tur/stokta/altkategori ile AYNI sinif — alan
        # PUBLIC urunler.json'da yasar, CI de yerel de AYNI degeri gorur ([[d1-baski-hash-
        # thrash]]'in gizli-kayit sorunu burada YOK). KANONIK deger yazilir (ham degil) ->
        # hash'in gordugu deger ile D1 kolonuna giden deger (d1-sync.uyum_metin) AYNI
        # fonksiyondan besleniyor, ayrisma INSAATAN imkansiz.
        uyum_kanonik(u),
    ], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(ozet.encode("utf-8")).hexdigest()[:16]
