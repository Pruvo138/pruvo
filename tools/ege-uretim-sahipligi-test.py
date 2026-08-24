#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EGE URETIM-SAHIPLIGI KAPISI (K285) — iki yonlu siniflandirma yasagi.

NEDEN VAR
=========
`ege-bilgi.md`'deki uretim-sahipligi satiri 24 Agu 2026'ya kadar TEK YONLU idi:
yalniz "isaretli kalemde 'ozel uretiyoruz' DEME" diyordu. TERS YON serbestti —
Ege bizim GERCEKTEN urettigimiz bir parcaya "hazir / tedarikciden / orijinal
urun" diyebilirdi ve hicbir kapi bunu olcmuyordu. Canli `SISTEM_TALIMATI`
("STOK YOK" maddesi) ise IKI YONU de yasakliyordu. Yani ayni prompt'a giren iki
kaynak ayni eksende AYRISIYORDU; model rastgele birini secer.

Bu kapi UC seyi olcer:
  (a) IKI YON AYRI VAKA — isaretli kalemde URETIM iddiasi YASAK **ve** isaretsiz
      kalemde TEDARIK iddiasi YASAK. Tek yon YETMEZ.
  (c) CELISKI KOLU — ayni vaka `ege-bilgi.md`'ye ve gomulu `SISTEM_TALIMATI`'na
      sorulur; iki kaynak AYRISIRSA KIRMIZI.
  (d) ESANLAMLI KOLU — talimat "ve esanlamlilarini DEME" der; kapi birebir tek
      dizeyi degil, TEDARIK ailesinin 4 ayri ifadesini tek tek olcer.

🔴 NEDEN KELIME ARAMASI DEGIL
=============================
Bu repoda OLCULDU: kelime arayan bir kabul testi yesil yanarken anlami tersine
ceviren 25 mutasyonun 22'si testten gecti. Bu yuzden kapi metinden bir KURAL
NESNESI TURETIR (hangi KOSUL hangi IDDIA'yi yasakliyor) ve vakalari o nesneye
sorar. Yon bilgisi KONUMDAN gelir: kosul isaretcileri (VARSA / YOKSA) metni
boler, yasak/olgu cumleleri hangi bolumdeyse O KOSULA baglanir. Cumleyi tersine
ceviren bir mutasyon butun kelimeleri ("DEME" dahil) korusa bile bolumleri
takas eder -> vakalar TERS cevap verir -> KIRMIZI.

Kapinin kendi mutasyon alt-kosumu HER kosumda calisir (bayrakla acilmaz; bayrak
CI'da sessizce dusebilir — bkz deploy.yml "DOSYA kesfeder, BAYRAK KESFETMEZ").

⚠️ NE OLCULMEZ (kor noktalar, gizlenmedi)
=========================================
  * Bu kapi Ege'nin GERCEK cevabini olcmez; iki KAYNAK METNIN ayni hukmu
    tasiyip tasimadigini olcer. Modelin talimata uymasini garanti ETMEZ.
  * SISTEM_TALIMATI bu repoda YOK (pruvo-bot/worker/src/index.js, HocA duzlemi).
    Burada CIVILENMIS FIKSTUR duruyor. Tazelik: pruvo-bot yerelde varsa bayt
    karsilastirmasi YAPILIR (bayatsa KIRMIZI); yoksa OLCULEMEDI diye BASILIR —
    sessiz yesil verilmez.
  * SURE/GUN ekseni HUKME BAGLANMAZ: iki kaynak orada bilerek AYRISIK durumda
    (K285-2). Kapi ayrismayi CIVILER ve ayrisma COZULURSE KIRMIZI yanar; boylece
    "cozuldu ama kimse pini kaldirmadi" hali sessiz kalamaz. Hukum KraL'da.

Kullanim:
    python3 tools/ege-uretim-sahipligi-test.py
    python3 tools/ege-uretim-sahipligi-test.py --dosya /gecici/mutant.md
"""
import argparse
import os
import re
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
VARSAYILAN_DOSYA = os.path.join(ROOT, "ege-bilgi.md")

# Capraz-repo kaynak (varsa tazelik olculur, yoksa OLCULEMEDI basilir).
BOT_INDEX = "/Users/okan/dev/pruvo-bot/worker/src/index.js"

# ---------------------------------------------------------------------------
# CIVILENMIS FIKSTUR — canli SISTEM_TALIMATI'nin "STOK YOK" maddesi.
# Kaynak: pruvo-bot/worker/src/index.js (commit dd66343 + 9c01082), 24 Agu 2026.
# BU BIR KOPYADIR. Tazeligi tazelik_olc() olcer; elle guncelleme YAPMA, kaynaktan
# kopyala.
# ---------------------------------------------------------------------------
TALIMAT_FIKSTUR = (
    "- STOK YOK: hiçbir ürün hazır/rafta değil. KATALOGDAKİ bir ürünün siparişini "
    "aldıktan sonra onu size özel üretir, sonra kargoya veririz (katalogda OLMAYAN "
    "parça için bu cümleyi KURMA — bkz KATALOGDA GÖRMEDİĞİN PARÇA). TEK İSTİSNA — "
    "*[FİZİKSEL/TEDARİKÇİ ÜRÜNÜ...]* işaretli kalem: onu biz üretmiyoruz. 🔴 İŞARET "
    "YOKSA İSTİSNA DA YOK: o ürünü BİZ ÜRETİYORUZ — \"biz üretmiyoruz / tedarikçiden "
    "geliyor / hazır bir ürün / orijinal ürün\" ve eşanlamlılarını DEME. İşaret \", "
    "STOKTA\" diyorsa ürünün elimizde hazır olduğunu söyleyebilirsin; \", SİPARİŞ "
    "ÜZERİNE TEDARİK\" diyorsa hazır DEME. Süre sorusunun cevabı stoktan BAĞIMSIZ ve "
    "her kalemde AYNI: *gönderim süremiz 3-5 iş günü* (bkz TESLİMAT)."
)

# ege-bilgi.md'deki bloğu bulan CAPA. Bulunamazsa/mukerrerse KIRMIZI (fail-closed):
# capa bayatlarsa kapi sessizce hicligi olcmus olur ([[capa-cokmesi-...]]).
EGE_CAPA = "üretim sahipliği"


# ---------------------------------------------------------------------------
# Turkce-guvenli kucultme. Python'un .lower()'i 'İ' -> 'i'+birlesik nokta (2 kod
# noktasi) uretir ve KONUM kayar; konum tabanli bolutleme bozulur. Once 1:1
# haritalama yapip sonra lower() cagiriyoruz ve uzunlugu DOGRULUYORUZ.
# ---------------------------------------------------------------------------
def kucult(s):
    d = s.replace("İ", "i").replace("I", "ı").lower()
    if len(d) != len(s):
        raise AssertionError("kucult() uzunlugu bozdu: %d != %d" % (len(d), len(s)))
    return d


# --- Aile / ifade sozlugu (hepsi kucult() duzleminde yazilidir) --------------
# Anahtar = IFADE KIMLIGI (esanlamli kolu bunlari TEK TEK olcer), deger = regex.
IFADELER = {
    "TEDARIK.uretmiyoruz":  r"biz üretmiyoruz",
    "TEDARIK.tedarikciden": r"tedarikçiden",
    "TEDARIK.hazir_urun":   r"hazır (?:bir )?ürün",
    "TEDARIK.orijinal":     r"orijinal ürün",
    "URETIM.biz":           r"biz üretiyoruz",
    "URETIM.ozel":          r"özel üret(?:iyoruz|ilir|ir)",
}
AILE = {k: k.split(".")[0] for k in IFADELER}
KARSIT = {"URETIM": "TEDARIK", "TEDARIK": "URETIM"}

YASAK_OP = re.compile(r"\b(deme|kurma|verme|söyleme|yasak)\b")
IZIN_OP = re.compile(r"(söyleyebilirsin|diyebilirsin)")

# Kosul isaretcileri. VAR: isaretli kalem kolu. YOK: isaretsiz kalem kolu.
VAR_RE = re.compile(r"(?:işaret\s+varsa|tek istisna|işaretli kalem)")
YOK_RE = re.compile(r"işaret\s+yoksa")

# Isaret literalini aile taramasindan CIKAR: '*[FİZİKSEL/TEDARİKÇİ ÜRÜNÜ...]*'
# icindeki 'TEDARİKÇİ' bir IDDIA degil, isaretin ADIdir.
ISARET_LITERAL = re.compile(r"\*\[[^\]]*\]\*")
TIRNAK = re.compile(r"\"([^\"]*)\"|“([^”]*)”")

GENEL_STOK_YOK = re.compile(r"hiçbir ürün[^.]{0,40}(?:hazır|rafta)[^.]{0,20}değil")


class KuralHatasi(Exception):
    """Kuralin TURETILEMEDIGI hal — olculecek sey yok, sessiz yesil verilmez."""

    def __init__(self, kimlik, mesaj):
        Exception.__init__(self, mesaj)
        self.kimlik = kimlik


def _blok_ege(metin):
    ham = [s for s in metin.split("\n") if EGE_CAPA in kucult(s)]
    if len(ham) != 1:
        raise KuralHatasi(
            "CAPA_YOK",
            "ege-bilgi.md'de %r capasi %d kez gecti (1 bekleniyor). Kapi hicligi "
            "olcemez: satir yeniden adlandirildiysa kapiyi da guncelle." % (EGE_CAPA, len(ham)))
    return ham[0]


def _bolutle(blok):
    """Blogu GENEL / <ilk kosul> / <ikinci kosul> olarak boler.

    Yon bilgisi TAMAMEN KONUMDAN gelir: hangi kosul isaretcisi once geliyorsa
    onun bolumu once baslar. VARSA<->YOKSA takasi yapan bir mutasyon butun
    kelimeleri korusa bile bolumleri takas eder.
    """
    d = kucult(blok)
    mv = VAR_RE.search(d)
    my = YOK_RE.search(d)
    if not mv:
        raise KuralHatasi("MARKER_YOK", "ISARETLI kalem kolunu acan kosul cumlesi YOK "
                                        "(VARSA / TEK ISTISNA / isaretli kalem).")
    if not my:
        raise KuralHatasi("MARKER_YOK", "ISARETSIZ kalem kolunu acan kosul cumlesi YOK "
                                        "(ISARET YOKSA). Metin TEK YONLU — K285'in kapattigi kusur.")
    sinir = sorted([("VAR", mv.start()), ("YOK", my.start())], key=lambda t: t[1])
    (ad1, p1), (ad2, p2) = sinir
    if p1 == p2:
        raise KuralHatasi("MARKER_CAKISTI", "iki kosul isaretcisi ayni konumda.")
    return {"GENEL": d[:p1], ad1: d[p1:p2], ad2: d[p2:]}


def _span_kurali(span):
    """Bir bolumden {ifade_kimligi: 'YASAK'/'IZIN'} turetir.

    IKI TURETIM YOLU:
      1) TIRNAK ICI + ARDINDAN YASAK OPERATORU  -> tirnaktaki her ifade YASAK.
         (Ev uslubu: yasak iddia listesi tirnak icinde yazilir, sonra 'DEME'.)
      2) TIRNAK DISI OLGU CUMLESI -> o aile IZIN, KARSIT aile YASAK.
         ("onu biz üretmiyoruz" = tedarik olgusu -> uretim iddiasi yasak.)
    Ayni aile hem IZIN hem YASAK alirsa IC_CELISKI (metin kendini yalanliyor).
    """
    temiz = ISARET_LITERAL.sub(" ", span)
    hukum = {}
    aile_hukmu = {}

    def koy(kimlik, deger):
        onceki = hukum.get(kimlik)
        if onceki and onceki != deger:
            raise KuralHatasi("IC_CELISKI", "ayni bolumde %s hem %s hem %s" % (kimlik, onceki, deger))
        hukum[kimlik] = deger

    def aile_koy(aile, deger):
        onceki = aile_hukmu.get(aile)
        if onceki and onceki != deger:
            raise KuralHatasi("IC_CELISKI", "ayni bolumde %s ailesi hem %s hem %s" % (aile, onceki, deger))
        aile_hukmu[aile] = deger
        for kimlik, a in AILE.items():
            if a == aile and re.search(IFADELER[kimlik], temiz) is None:
                # aile hukmu, o bolumde GECMEYEN ifadelere de yayilir (kapsayici):
                koy(kimlik, deger)

    # (1) tirnak ici yasak listeleri
    tirnak_araliklari = []
    for m in TIRNAK.finditer(temiz):
        icerik = m.group(1) if m.group(1) is not None else (m.group(2) or "")
        tirnak_araliklari.append((m.start(), m.end()))
        kuyruk = temiz[m.end():m.end() + 40]
        if YASAK_OP.search(kuyruk):
            for kimlik, desen in IFADELER.items():
                if re.search(desen, icerik):
                    koy(kimlik, "YASAK")

    # (2) tirnak DISI olgu cumleleri
    disi = list(temiz)
    for a, b in tirnak_araliklari:
        for i in range(a, b):
            disi[i] = " "
    disi = "".join(disi)
    for kimlik, desen in IFADELER.items():
        if re.search(desen, disi):
            aile = AILE[kimlik]
            koy(kimlik, "IZIN")
            aile_koy(aile, "IZIN")
            aile_koy(KARSIT[aile], "YASAK")
    return hukum, aile_hukmu


def _stok_kurali(blok):
    """Stok ekseni: '<isaret literali>' diyorsa <hukum> kaliplarini okur.

    🔴 KUYRUK SINIRI BIR SONRAKI TIRNAKTIR, sabit karakter penceresi DEGIL.
    Olculdu (K285 tur-1): 80 karakterlik pencere KOMSU kolun 'DEME'sini yutuyordu
    -> stok yonunu takas eden M4 mutanti V11 kolundan KACTI (mutantin yasamasi
    "kol saglam" degil "kol OLCULEMEDI" demektir, [[ad-iki-rolde-mutanti-golgeler]]).
    """
    d = kucult(ISARET_LITERAL.sub(" ", blok))
    sonuc = {"genel_hazir_yok": bool(GENEL_STOK_YOK.search(d)),
             "stokta_izin": False, "siparis_hazir_yasak": False}
    tirnaklar = [(m.start(), m.end(),
                  m.group(1) if m.group(1) is not None else (m.group(2) or ""))
                 for m in TIRNAK.finditer(d)]
    for i, (_, bit, icerik) in enumerate(tirnaklar):
        kuyruk = d[bit:tirnaklar[i + 1][0]] if i + 1 < len(tirnaklar) else d[bit:]
        yasak = bool(YASAK_OP.search(kuyruk))
        izin = bool(IZIN_OP.search(kuyruk))
        if "stokta" in icerik and "sipariş" not in icerik:
            if izin and not yasak:
                sonuc["stokta_izin"] = True
        if "sipariş üzerine tedarik" in icerik:
            if yasak and not izin:
                sonuc["siparis_hazir_yasak"] = True
    return sonuc


def kural_cikar(blok):
    bolumler = _bolutle(blok)
    kural = {"STOK": _stok_kurali(blok)}
    for kol in ("VAR", "YOK"):
        try:
            hukum, aile = _span_kurali(bolumler[kol])
        except KuralHatasi as e:
            raise KuralHatasi(e.kimlik, "[%s kolu] %s" % (kol, e))
        kural[kol] = hukum
    return kural


def hukum(kural, kol, ifade_kimligi):
    return kural[kol].get(ifade_kimligi, "BELIRSIZ")


# ---------------------------------------------------------------------------
# VAKA TABLOSU — her vaka IKI kaynaga da sorulur (celiski kolu).
#   (a) iki yon: V1 (isaretli + uretim iddiasi) ve V2 (isaretsiz + tedarik iddiasi)
#   (d) esanlamli: V5/V6/V7 birebir dizeyi degil AYRI ifadeleri olcer
# ---------------------------------------------------------------------------
VAKALAR = [
    ("V1", "ISARETLI kalemde 'biz uretiyoruz' iddiasi", "VAR", "URETIM.biz", "YASAK"),
    ("V2", "ISARETSIZ kalemde 'biz uretmiyoruz' iddiasi", "YOK", "TEDARIK.uretmiyoruz", "YASAK"),
    ("V3", "ISARETLI kalemde 'biz uretmiyoruz' iddiasi", "VAR", "TEDARIK.uretmiyoruz", "IZIN"),
    ("V4", "ISARETSIZ kalemde 'biz uretiyoruz' iddiasi", "YOK", "URETIM.biz", "IZIN"),
    ("V5", "ISARETSIZ + esanlamli 'hazir urun'", "YOK", "TEDARIK.hazir_urun", "YASAK"),
    ("V6", "ISARETSIZ + esanlamli 'orijinal urun'", "YOK", "TEDARIK.orijinal", "YASAK"),
    ("V7", "ISARETSIZ + esanlamli 'tedarikciden geliyor'", "YOK", "TEDARIK.tedarikciden", "YASAK"),
    ("V8", "ISARETLI kalemde 'ozel uretiyoruz' iddiasi", "VAR", "URETIM.ozel", "YASAK"),
]
STOK_VAKALARI = [
    ("V9", "genel: hicbir urun rafta hazir DEGIL", "genel_hazir_yok", True),
    ("V10", "isaret ', STOKTA' ise hazir denebilir", "stokta_izin", True),
    ("V11", "isaret ', SIPARIS UZERINE TEDARIK' ise hazir DENEMEZ", "siparis_hazir_yasak", True),
]

# --- SURE/GUN AYRISMASI (K285-2) — CIVILENMIS, hukum KraL'da ----------------
# ege-bilgi.md: "kendiliginden stok ya da gun SOZU verme"
# SISTEM_TALIMATI: "Sure sorusunun cevabi stoktan BAGIMSIZ ve her kalemde AYNI"
# Ikisi ayni eksende ZIT. Pin: ayrisma BUGUN VAR. Ayrisma cozulurse pin KIRILIR
# (KIRMIZI) -> "cozuldu ama kimse kapiyi guncellemedi" hali sessiz kalamaz.
GUN_YASAK_RE = re.compile(r"gün sözü verme")
GUN_EMIR_RE = re.compile(r"süre sorusunun cevabı[^.]{0,60}aynı")
GUN_AYRISMA_PIN = True


def gun_ekseni(ege_blok, talimat_blok):
    e = bool(GUN_YASAK_RE.search(kucult(ege_blok)))
    t = bool(GUN_EMIR_RE.search(kucult(talimat_blok)))
    return e, t


def tazelik_olc():
    """Fikstur canli kaynakla BAYT BIREBIR mi? Kaynak yoksa OLCULEMEDI."""
    if not os.path.exists(BOT_INDEX):
        return "OLCULEMEDI", ("pruvo-bot yerelde YOK (%s) — fikstur tazeligi OLCULEMEDI. "
                              "CI'da beklenen hal." % BOT_INDEX)
    try:
        with open(BOT_INDEX, encoding="utf-8") as f:
            kaynak = f.read()
    except Exception as e:                                   # noqa: BLE001
        return "OLCULEMEDI", "pruvo-bot okunamadi: %s" % e
    if TALIMAT_FIKSTUR in kaynak:
        return "TAZE", "fikstur canli SISTEM_TALIMATI ile BAYT BIREBIR."
    return "BAYAT", ("fikstur canli kaynakta BULUNAMADI — SISTEM_TALIMATI degismis ya da "
                     "fikstur bayatlamis. Kaynaktan yeniden kopyala: %s" % BOT_INDEX)


def calistir(dosya):
    """(bulgular, notlar) dondurur. bulgular BOS ise YESIL."""
    bulgular = []
    notlar = []
    with open(dosya, encoding="utf-8") as f:
        metin = f.read()

    try:
        ege_blok = _blok_ege(metin)
    except KuralHatasi as e:
        return [(e.kimlik, str(e))], notlar
    talimat_blok = TALIMAT_FIKSTUR

    kurallar = {}
    for ad, blok in (("EGE", ege_blok), ("TALIMAT", talimat_blok)):
        try:
            kurallar[ad] = kural_cikar(blok)
        except KuralHatasi as e:
            bulgular.append((e.kimlik, "[%s] %s" % (ad, e)))
    if len(kurallar) != 2:
        return bulgular, notlar

    for vid, ad, kol, ifade, beklenen in VAKALAR:
        e = hukum(kurallar["EGE"], kol, ifade)
        t = hukum(kurallar["TALIMAT"], kol, ifade)
        if e != t:
            bulgular.append((vid, "AYRISMA — %s: ege-bilgi.md=%s, SISTEM_TALIMATI=%s" % (ad, e, t)))
        if e != beklenen:
            bulgular.append((vid, "ege-bilgi.md yanlis hukum — %s: %s (beklenen %s)" % (ad, e, beklenen)))
        if t != beklenen:
            bulgular.append((vid, "SISTEM_TALIMATI yanlis hukum — %s: %s (beklenen %s)" % (ad, t, beklenen)))

    for vid, ad, alan, beklenen in STOK_VAKALARI:
        e = kurallar["EGE"]["STOK"][alan]
        t = kurallar["TALIMAT"]["STOK"][alan]
        if e != t:
            bulgular.append((vid, "AYRISMA (stok) — %s: ege=%s, talimat=%s" % (ad, e, t)))
        if e != beklenen:
            bulgular.append((vid, "ege-bilgi.md stok hukmu — %s: %s (beklenen %s)" % (ad, e, beklenen)))
        if t != beklenen:
            bulgular.append((vid, "SISTEM_TALIMATI stok hukmu — %s: %s (beklenen %s)" % (ad, t, beklenen)))

    ege_gun, talimat_gun = gun_ekseni(ege_blok, talimat_blok)
    ayrisik = ege_gun and talimat_gun
    if ayrisik != GUN_AYRISMA_PIN:
        bulgular.append(("GUN_PIN", "SURE/GUN ayrismasi PIN'i kirildi (ege_gun_yasagi=%s, "
                                    "talimat_gun_emri=%s, pin=%s). Ayrisma cozulduyse pin'i "
                                    "KALDIR ve hukmu defterle." % (ege_gun, talimat_gun, GUN_AYRISMA_PIN)))
    else:
        notlar.append("K285-2 SURE/GUN AYRISMASI CIVILI: ege-bilgi.md 'gun SOZU verme' der (%s), "
                      "SISTEM_TALIMATI 'sure her kalemde AYNI' der (%s). HUKUM KraL'da; bu kapi "
                      "karar VERMEZ, ayrismayi TUTAR." % (ege_gun, talimat_gun))
    return bulgular, notlar


# ---------------------------------------------------------------------------
# MUTASYON ALT-KOSUMU — her kosumda calisir.
# Her mutant HEDEF KOL beyan eder; KIRMIZI yanmasi YETMEZ, DOGRU koldan yanmali.
# ---------------------------------------------------------------------------
def _satirda(metin, fn):
    """Mutasyonu YALNIZ sahiplik satirina uygular.

    Dosya genelinde takas yapmak yan hasar uretir (or. 'YOKSA' SSS satirinda da
    gecer) ve mutantin hangi kolu oldurdugu bulanir — atif bozulur.
    """
    satirlar = metin.split("\n")
    hedef = [i for i, s in enumerate(satirlar) if EGE_CAPA in kucult(s)]
    if len(hedef) != 1:
        return metin
    i = hedef[0]
    satirlar[i] = fn(satirlar[i])
    return "\n".join(satirlar)


def _takas(metin, a, b):
    ara = "\x00TAKAS\x00"
    return metin.replace(a, ara).replace(b, a).replace(ara, b)


def _m1(m):
    return _satirda(m, lambda s: _takas(s, "VARSA", "YOKSA"))


def _m2(m):
    return _satirda(m, lambda s: _takas(
        s, "\"özel üretiyoruz\"",
        "\"biz üretmiyoruz / tedarikçiden geliyor / hazır ürün / orijinal ürün\""))


def _m3(m):
    return _satirda(m, lambda s: re.sub(r"İŞARET YOKSA.*?eşanlamlılarını DEME\. ", "", s))


def _m4(m):
    return _satirda(m, lambda s: _takas(s, "STOKTA", "SİPARİŞ ÜZERİNE TEDARİK"))


def _k1(m):
    return m.replace("Pazar kapalı", "Pazar günü kapalı")


# hedef = mutantin OLDURMESI GEREKEN kollarin TAMAMI (ALT KUME sarti, kesisim DEGIL).
# Kesisim sarti gevsektir: iki kollu bir mutant tek koldan yanip digerini OLCULMEMIS
# birakabilir ve tablo yine "TAMAM" basar (K285 tur-1'de tam bu oldu, M4/V11).
MUTANTLAR = [
    ("M1", "yon takasi: VARSA <-> YOKSA (butun kelimeler, 'DEME' dahil KORUNUR)",
     _m1, "KIRMIZI", {"V1", "V2"}),
    ("M2", "aile takasi: iki koldaki yasak iddia listeleri yer degistirir",
     _m2, "KIRMIZI", {"IC_CELISKI"}),
    ("M3", "ters yon silinir (24 Agu oncesi TEK YONLU metne geri donus)",
     _m3, "KIRMIZI", {"MARKER_YOK"}),
    ("M4", "stok yon takasi: ', STOKTA' <-> ', SIPARIS UZERINE TEDARIK'",
     _m4, "KIRMIZI", {"V10", "V11"}),
    ("K1", "KONTROL (ilgisiz): calisma saati cumlesi — anlam eksenine DOKUNMAZ",
     _k1, "YESIL", set()),
]


def mutasyon_kosumu(dosya):
    with open(dosya, encoding="utf-8") as f:
        taban = f.read()
    satirlar = []
    kirik = 0
    for mid, ad, fn, beklenen, hedef in MUTANTLAR:
        mutant = fn(taban)
        if mutant == taban:
            satirlar.append("  %-3s %-8s %s  <-- MUTASYON UYGULANMADI (metin degismedi)"
                            % (mid, "SAKAT", ad))
            kirik += 1
            continue
        gecici = tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False)
        try:
            gecici.write(mutant)
            gecici.close()
            bulgular, _ = calistir(gecici.name)
        finally:
            os.unlink(gecici.name)
        gorulen = "KIRMIZI" if bulgular else "YESIL"
        kimlikler = sorted({b[0] for b in bulgular})
        if gorulen != beklenen:
            durum = "SAKAT"
            kirik += 1
        elif beklenen == "KIRMIZI" and not hedef.issubset(set(kimlikler)):
            durum = "YANLIS_KOL"
            kirik += 1
        else:
            durum = "TAMAM"
        satirlar.append("  %-3s %-10s beklenen=%-8s gorulen=%-8s kol=%s\n       %s"
                        % (mid, durum, beklenen, gorulen,
                           ",".join(kimlikler) if kimlikler else "-",
                           ad + ("  [hedef=%s]" % ",".join(sorted(hedef)) if hedef else "")))
    return satirlar, kirik


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dosya", default=VARSAYILAN_DOSYA)
    a = ap.parse_args()

    print("EGE URETIM-SAHIPLIGI KAPISI (K285) — %s" % a.dosya)
    hal, mesaj = tazelik_olc()
    print("FIKSTUR TAZELIGI: %s — %s" % (hal, mesaj))

    bulgular, notlar = calistir(a.dosya)
    print("\nVAKALAR: %d uretim/esanlamli + %d stok, HER BIRI IKI KAYNAGA soruldu."
          % (len(VAKALAR), len(STOK_VAKALARI)))
    for n in notlar:
        print("  NOT: %s" % n)
    if bulgular:
        print("  KIRMIZI — %d bulgu:" % len(bulgular))
        for kimlik, m in bulgular:
            print("    [%s] %s" % (kimlik, m))
    else:
        print("  YESIL — iki kaynak %d vakanin hepsinde AYNI hukmu veriyor." %
              (len(VAKALAR) + len(STOK_VAKALARI)))

    print("\nMUTASYON ALT-KOSUMU (%d mutant; hedef-kol atfi zorunlu):" % len(MUTANTLAR))
    satirlar, kirik = mutasyon_kosumu(a.dosya)
    for s in satirlar:
        print(s)

    if hal == "BAYAT":
        print("\nSONUC: KIRMIZI (fikstur bayat)")
        return 1
    if bulgular:
        print("\nSONUC: KIRMIZI (%d bulgu)" % len(bulgular))
        return 1
    if kirik:
        print("\nSONUC: KIRMIZI (%d mutant sakat/yanlis kol — kapi anlami olcmuyor)" % kirik)
        return 1
    print("\nSONUC: YESIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
