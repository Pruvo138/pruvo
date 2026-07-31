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
    ], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(ozet.encode("utf-8")).hexdigest()[:16]
