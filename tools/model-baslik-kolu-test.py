#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — MODEL SAYFASI ÜYELİK YÜKLEMİ: marka üyeliği ∧ model.

  python3 tools/model-baslik-kolu-test.py                 # kabul (çapalara karşı ölçer)
  python3 tools/model-baslik-kolu-test.py --kendini-test  # ayırt edici mutasyon bataryası
  python3 tools/model-baslik-kolu-test.py --kok /yol      # BAŞKA ağaçtan oku (mutasyon için)

NE ÖLÇER — model disjunkt'ının ÜÇ KOLU AYRI AYRI:
    (1) ham `uyum[].model`   (2) `model_kanon` kuşak/kanon katlaması   (3) BAŞLIKTA TAM KELİME
ve başlık kolunun KADEMELİ kuralını (güvenli jeton / tehlike sınıfı).

🔴 ÇAPALAR ÇAKILI, TOTOLOJİ DEĞİL: beklenen sayılar geçişten ÖNCE HEAD ağacından ve canlı
uçtan tespit edildi; kabul bu SABİT sayılara karşı ölçer, kendi ürettiği kümeye DEĞİL.
Katalog büyüdükçe sayı ARTABİLİR (yüklem yalnız genişletir) — bu yüzden ölçüt ">= çapa" ve
"asla küçülmez"dir; çapanın ALTINA düşmek KIRMIZI'dır.

🔴 AYIRT EDİCİ MUTANTLAR ÜÇ FARKLI SAYFADA ÜÇ FARKLI YÖNE kayar (tek bir "daima kırmızı"
kapı hepsini geçemez):
    M1 kanon/kuşak kolunu düşür  -> Transporter sınıfında DÜŞER
    M2 başlık kolunu düşür       -> Vitara sınıfında DÜŞER
    M3 tehlike korumasını düşür  -> Renault|5 turnusolunda ARTAR
    M4 bitişikliği `markaKatla()` ile yaz -> tehlike koruması ÖLÜR (Renault|5 ARTAR) ama
       Subaru|86 turnusolu M3'ten AYIRT EDER (M3'te artar, M4'te artmaz)
    + KONTROLLER (sıralama · davranışsız yeniden adlandırma · ilgisiz alan) YEŞİL kalmalı.
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

DIR = os.path.dirname(os.path.abspath(__file__))
GERCEK_KOK = os.path.dirname(DIR)

# ---------------------------------------------------------------- ÇAKILI ÇAPALAR
# (marka, model adı, ÖNCE, SONRA-en az) — ÖNCE değeri HEAD ağacından (5 Ağu, katalog 19.461),
# SONRA değeri aynı koşumda yeni yüklemle ölçüldü. Canlı teyit: `?ara=Vitara` 68 · resmî
# üyelik 8 · sayfa 27 -> 66 (Senyor Advisor ölçümü, 5 Ağu 16:00 TRT).
CAPALAR = [
    ("Suzuki", "Vitara", 27, 66),          # BAŞLIK kolu (kazancın tamamı bu koldan)
    ("Volkswagen", "Transporter", 144, 145),   # KANON/KUŞAK kolu taşıyor (KUSAK_ESLEME)
    ("Volkswagen", "Golf", 290, 300),
    ("Ford", "Focus", 305, 305),           # DEĞİŞMEYEN çapa: kol bu sayfada iş yapmıyor
    ("Ford", "Fiesta", 231, 231),          # DEĞİŞMEYEN çapa
    ("Opel", "Astra", 126, 128),
    ("Toyota", "Corolla", 128, 133),
]

# TURNUSOL — TEHLİKE SINIFI (kısa ya da tamamen sayısal jeton).
# Renault|5: korumayla başlık kolundan +3 ürün girer ("Renault 5 …" BİTİŞİK);
# koruma düşerse çıplak `\b5\b` "Clio 5"/"Espace 5" kuşak sayılarını da yakalar ve sayı ARTAR.
TEHLIKE_TURNUSOL = [
    ("Renault", "5", 11, 14),
]
# M3 ile M4'ü AYIRT EDEN turnusol: başlıkta "Subaru BRZ 86" geçer.
#   · doğru bitişiklik  -> "subaru 86" ARANIR, BULUNMAZ (marka ile jeton yan yana DEĞİL)
#   · markaKatla ile    -> "subaru brz" -> katla() -> "Subaru" -> EŞLEŞİR (koruma ölür)
#   · koruma tümden yok -> çıplak "86" EŞLEŞİR
# Yani M3 ve M4 bu turnusolu AYNI yönde ama FARKLI kümede kaydırır; ikisi de tabandan farklı.
AYIRT_TURNUSOL = ("Subaru", "86")

# BAŞLIK KOLU KADEMELİ KURAL FİKSTÜRÜ — (jeton, TEHLİKE mi).
# Kural TÜRETİLİR (uzunluk >= 4 ∧ sayısal değil = güvenli); sabit liste YOKTUR.
SINIF_FIKSTURU = [
    ("Vitara", False), ("Corolla", False), ("Transporter", False), ("Sync", False),
    ("iPhone", False), ("F-150", False),
    ("5", True), ("A", True), ("V", True), ("205", True), ("300", True), ("C5", True),
    ("E30", True), ("T4", True), ("FL", True), ("86", True), ("M54", True), ("N47", True),
]

# BİTİŞİKLİK FİKSTÜRÜ — (başlık, marka, jeton, kabul mü).
# 🔴 M4'ün ÇALIŞTIRILABİLİR KANITI: 2. ve 3. satır `markaKatla()` ile yazılmış bir
# bitişiklikte KABUL'e döner (önek kuralı "Renault Espace"i "Renault"a katlar).
# 🔴 İKİ AYRI EKSEN — M3 (koruma yok) ile M4'ü (katlamalı bitişiklik) AYIRT EDER:
#   MARKASIZ : jetondan önce markaya benzer HİÇBİR şey yok. Koruma yoksa GEÇER (M3 kırmızı);
#              katlamalı bitişiklik ÖNEK bulamaz, GEÇMEZ (M4 bu ekseni GEÇER).
#   KATLAMALI: jetondan önce "<marka> <başka model>" var. Koruma yoksa da, katlamalı
#              bitişiklikte de GEÇER (M3 ve M4 birlikte kırmızı).
# Böylece M3'ün kırmızı kümesi M4'ünkinden GERÇEKTEN farklı olur.
BITISIKLIK_MARKASIZ = [
    ("Clio 5 Cam Krikosu Dişlisi", "Renault", "5", False),
    ("Bardaklık 300 ml Kutu Adaptörü", "Chrysler", "300", False),
    ("BRZ 86 Şanzıman Kuyruk Mili Tapası", "Subaru", "86", False),
]
BITISIKLIK_KATLAMALI = [
    ("Renault 5 E-Tech Kapı Gözleri", "Renault", "5", True),
    ("Renault Espace 5 Bardaklık", "Renault", "5", False),
    ("Renault Clio 5 Cam Krikosu", "Renault", "5", False),
    ("Subaru BRZ / Toyota 86 Şanzıman Tapası", "Subaru", "86", False),
    ("Subaru 86 Şanzıman Tapası", "Subaru", "86", True),
    ("Suzuki Vitara İç Aydınlatma", "Suzuki", "Vitara", True),
    ("Grand Vitara Tavan Rayı", "Suzuki", "Vitara", True),   # güvenli jeton: çıplak YETER
]

# ---------------------------------------------------- H1/H3 ŞEKİL FİKSTÜRÜ (6 Ağu, mimar)
# (kova adı, H1 ŞASİ/MOTOR KODU mu, H3 AYRI ARAÇ ADI mı, DONANIM KUYRUKLU mu)
# 🔴 ÜÇ EKSEN AYRI AYRI ÇİVİLİ: tek bayrak yazsaydık "her şey sayfa alır" mutantı ile
# "hiçbir şey almaz" mutantı AYNI satırı kırardı ve ayırt edilemezlerdi.
# 🔴 ÇIPLAK SAYI satırları H1'in SINIRIDIR — mimar hükmü açık: `57`/`86`/`17` H1 DIŞI.
SEKIL_FIKSTURU = [
    # şasi/motor kodu (TEK jeton, harf+rakam) -> H1 ALLOW
    ("E46", True, False, False), ("M54", True, False, False), ("M57", True, False, False),
    ("N47", True, False, False), ("T4", True, False, False), ("W638", True, False, False),
    ("4AGE", True, False, False), ("SW20", True, False, False), ("325i", True, False, False),
    # ÇIPLAK SAYI -> H1 DIŞI (tehlike sınıfında kalır)
    ("57", False, False, False), ("86", False, False, False), ("17", False, False, False),
    ("660", False, False, False), ("5", False, False, False),
    # rakamsız tek jeton -> ne H1 ne H3 (yargı envanterde/mimarda)
    ("Custom", False, False, False), ("GSX", False, False, False), ("DR", False, False, False),
    ("Ducato", False, False, False),
    # çok jetonlu, kuyruğu DONANIM DEĞİL -> H3 ALLOW (ayrı araç adı)
    ("Corsa D", False, True, False), ("Megane II", False, True, False),
    ("Passat B8", False, True, False), ("Transporter T5", False, True, False),
    ("Zafira Life", False, True, False), ("Transit MK3", False, True, False),
    ("Megane E-Tech", False, True, False), ("Golf 4", False, True, False),
    ("Astra H", False, True, False), ("E46 M3", False, True, False),
    # çok jetonlu, kuyruğu DONANIM -> H3 DENY (tabana YAPIŞIK; katlanır, sayfa açmaz)
    ("Focus ST", False, False, True), ("Fiesta ST", False, False, True),
    ("206 GTI", False, False, True), ("Megane RS", False, False, True),
    ("Clio GT", False, False, True), ("Astra GTC", False, False, True),
]

# H2 — DENY'in BİLEŞİK (son-kelime) kolu YALNIZ DEĞİŞTİRİCİLERE işler.
# (marka, kova adı, MODEL DEĞİL mi = sayfası kapanır mı)
DENY_BILESIK_FIKSTURU = [
    ("Ford", "ST", True),                 # çıplak deny jetonu
    ("Ford", "Focus ST", True),           # DEĞİŞTİRİCİ kuyruğu -> bileşik de kapanır
    ("Ford", "Fiesta ST", True),
    ("Ford", "Focus Mk1", True),          # `MK1` kuşak değiştiricisi
    ("Volkswagen", "Golf Mk2", True),
    ("Renault", "E-Tech", True),          # çıplak rozet -> KAPANIR
    ("Renault", "5 E-Tech", False),       # ROZET kuyruğu değiştirici DEĞİL -> AÇIK KALIR
    ("Renault", "Megane E-Tech", False),
    ("Ford", "Focus EcoBoost", False),    # `EcoBoost` değiştirici DEĞİL -> bileşik AÇIK
    ("Volkswagen", "Golf iPhone", False),
    ("Ford", "Focus", False),             # ilgisiz kontrol
]

# H4 — AKSAN İKİZLERİ: iki yazım AYNI kanonik anahtara düşmeli.
# H1 / H3 KURAL KOLLARININ CANLI VERİ ÇAPALARI — (marka, kova adı, en az ürün).
# 🔴 İKİ KÜME AYRIK: H1 çapaları TEK JETON şasi/motor kodu, H3 çapaları ÇOK JETONLU ad.
# H1 kuralını düşüren mutant yalnız birinciyi, H3'ü düşüren yalnız ikinciyi kırar —
# "daima kırmızı" tek bir eksen ikisini birden geçemez.
H1_CAPA_SAYFA = [
    ("Mercedes", "W638", 16), ("Toyota", "SW20", 18), ("BMW", "M54", 8),
    ("BMW", "E92", 11), ("Mercedes", "W220", 11),
]
H3_CAPA_SAYFA = [
    ("Opel", "Corsa D", 25), ("Renault", "Megane II", 15), ("Volkswagen", "Passat B8", 14),
    ("Volkswagen", "Transporter T5", 9), ("Ford", "Transit MK3", 8),
]

# ------------------------------------------- ADIM 3 HÜKÜM FİKSTÜRLERİ (6 Ağu, mimar hükmü)
# 🔴 HER HÜKÜM AYRI EKSENDE ÇİVİLİ: A/B/D'nin DENY tarafları AYRI listelerdir; tek listeye
# yazılsaydı "bir deny'i allow'a çeviren" mutantların hepsi AYNI iddiayı kırar ve birbirinden
# AYIRT EDİLEMEZ olurlardı ([[beyan-edilmis-survivor]]).
#
# A) ÇAPRAZ MARKA ROZETİ — DENY: model o markanın KENDİ rozetiyle satılmadı -> SAYFA YOK.
HUKUM_A_DENY = [
    ("Chevrolet", "Ampera"), ("Citroen", "Aygo"), ("Citroen", "Boxer"),
    ("Citroen", "Combo"), ("Citroen", "Expert"), ("Citroen", "Rifter"),
    ("Citroen", "Scudo"), ("Opel", "Primastar"), ("Opel", "Volt"),
    ("Peugeot", "Aygo"), ("Peugeot", "Combo"), ("Peugeot", "Ducato"),
    ("Renault", "Primastar"), ("Seat", "Golf"), ("Seat", "Sharan"),
    ("Volkswagen", "Alhambra"), ("Volkswagen", "CITIGO"),
]
# B) ÇIPLAK AİLE ÖNEKİ — DENY: çıplak sayı, hangi aracı adlandırdığı BELİRSİZ.
HUKUM_B_DENY = [("Yamaha", "660")]
# D) TEKİL MODEL ADI — DENY: kamper dönüştürücüsü, VW'nin modeli DEĞİL.
HUKUM_D_DENY = [("Volkswagen", "Westfalia")]
# ALLOW tarafları — (marka, ad, EN AZ ürün). Sayılar bu turda ÖLÇÜLDÜ (katalog 19.999);
# ölçüt ">= çapa"dır, yüklem yalnız genişletir.
HUKUM_ALLOW = [
    ("Citroen", "Relay", 3),          # A — Jumper'ın GERÇEK İngiltere rozeti
    ("Toyota", "86", 9),              # A — ÇIPLAK SAYI, TEKİL giriş (kural değişmedi)
    ("Honda", "CBR", 9), ("Honda", "CRF", 9), ("Honda", "GX", 4),       # B — aile öneki
    ("Suzuki", "DR", 31), ("Suzuki", "GSX", 22), ("Suzuki", "RM", 3),   # B
    ("Mitsubishi", "Evolution", 6),                                     # B
    ("Ford", "Custom", 30), ("Honda", "Legend", 3),                     # D — tekil model adı
    ("Honda", "Prologue", 3), ("Honda", "Recon", 3), ("Honda", "Sabre", 3),
    ("Honda", "Stepwgn", 3), ("Honda", "Zoomer", 3), ("Volkswagen", "Vocho", 3),
]
# E) ARAÇ DIŞI — sayfa KALIR ama ŞEKİL KURALIYLA DEĞİL, TEKİL GİRİŞLE doğar.
# (marka, ad, EN AZ ürün): P-45 dijital piyano (H1 şekli) · Recording Custom davul (H3 şekli)
HUKUM_E_MUAF = [("Yamaha", "P-45", 4), ("Yamaha", "Recording Custom", 3)]

AKSAN_IKIZ_FIKSTURU = [
    ("Renault", "Zoe", "Zoé"),
    ("Yamaha", "Tenere", "Ténéré"),
    ("Yamaha", "Tenere 700", "Ténéré 700"),
    ("Citroen", "Citroen C3", "Citroën C3"),
    ("Skoda", "Skoda Octavia", "Škoda Octavia"),
]


# ---------------------------------------------------------------- BAĞIMSIZ ŞEKİL ORACLE'I
# 🔴 ÜRETİM GÖVDESİ ÇAĞRILMAZ: B8/B8a/B8b eksenlerinde kullanılan şekil yüklemleri BURADA
# ELLE yazılır. `mm.sasi_motor_kodu_mu` çağrılsaydı "yargısız doğan=0" iddiası totoloji
# olurdu ([[beyan-edilmis-survivor]]); B10 fikstürü ise ÜRETİM gövdesini bu bağımsız
# beklentilere karşı ölçer — iki eksen bilerek ayrıdır.
_DONANIM_BAGIMSIZ = frozenset(("gt", "gtc", "gtd", "gti", "rs", "st"))


def _sade(s):
    t = unicodedata.normalize("NFKD", (s or "").replace("ı", "i").replace("İ", "i").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", t)


def _aksanli(s):
    return any(unicodedata.combining(c) for c in unicodedata.normalize("NFD", s or ""))


def _donanim_kuyruklu(ad):
    toks = (ad or "").split()
    return len(toks) >= 2 and _sade(toks[-1]) in _DONANIM_BAGIMSIZ


def _sasi_kodu(ad):
    if len((ad or "").split()) != 1:
        return False
    j = _sade(ad)
    return bool(j) and any(c.isalpha() for c in j) and any(c.isdigit() for c in j)


def _ayri_arac(ad):
    return len((ad or "").split()) >= 2 and not _donanim_kuyruklu(ad)


def _ciplak_sayi(ad):
    j = _sade(ad)
    return bool(j) and j.isdigit()


def _modul(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ad] = mod
    spec.loader.exec_module(mod)
    return mod


class Olculemedi(Exception):
    pass


def olc(kok):
    """(sayfa_sayilari, evren, mm) — hüküm VERMEZ, sayı üretir."""
    araclar = os.path.join(kok, "tools")
    if araclar not in sys.path:
        sys.path.insert(0, araclar)
    for _m in ("arama", "model_kanon", "marka_model_build"):
        sys.modules.pop(_m, None)
    try:
        mm = _modul(os.path.join(araclar, "marka_model_build.py"), "marka_model_build")
        with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
            urunler = json.load(f)
        with open(os.path.join(kok, "index.html"), encoding="utf-8") as f:
            index_html = f.read()
    except Exception as e:                                        # noqa: BLE001
        raise Olculemedi("katalog/jeneratör okunamadı: %r" % (e,))
    if not urunler:
        raise Olculemedi("urunler.json BOŞ")
    try:
        evren = mm.MarkaEvreni(index_html)
        ek = mm.cip_evreni_markalari(urunler, index_html)
        veri = mm.gruplandir(urunler, evren, ek)
    except SystemExit as e:                                       # noqa: BLE001
        raise Olculemedi("jeneratör fail-closed durdu: %r" % (e,))
    if not veri:
        raise Olculemedi("jeneratör HİÇ kova üretmedi")
    kova = {}
    for marka, d in veri.items():
        for canon, g in d["gruplar"].items():
            kova[(marka, canon)] = (len(g["urunler"]), mm.yayimlanir_mi(g),
                                    len(g.get("baslik_ekli") or ()),
                                    bool(g.get("birincil"))
                                    and (marka, canon) not in mm.ROZET_DISI
                                    and not mm.model_olmayan_cift_mi(marka, g["display"]),
                                    g["display"])
    return kova, evren, mm


def sayi(kova, evren, marka, ad):
    """Kovanın ürün sayısı (kova YOKSA 0) — sayfa yayımda olmasa da ölçülür ki
    yargı kapısı (BASLIK_DOGAN_ALLOW) iddiayı gizlemesin."""
    canon = evren.model_anahtari(marka, ad)
    if not canon:
        return 0
    return (kova.get((marka, canon)) or (0, False, 0, False, ""))[0]


def kabul(kok):
    kaldi, gecen = [], []

    def dogrula(ad, kosul, detay=""):
        (gecen if kosul else kaldi).append(ad)
        print("  %s %s%s" % ("GECTI" if kosul else "KALDI", ad, (" — " + detay) if detay else ""))

    kova, evren, mm = olc(kok)
    yayin = sum(1 for v in kova.values() if v[1])
    kalem = sum(v[0] for v in kova.values() if v[1])
    print("  SAYFA=%d KALEM=%d KOVA=%d" % (yayin, kalem, len(kova)))

    dogrula("B0 FAIL-CLOSED: ÖLÇÜLEN SAYFA VAR", yayin >= 500,
            "sayfa=%d (dejenere ölçüm YEŞİL geçemez)" % yayin)

    # --- A) ÇAPALAR: çakılı sayılara karşı, kendi kümemize karşı DEĞİL --------------
    capa_sapan = []
    for marka, ad, _once, beklenen in CAPALAR:
        n = sayi(kova, evren, marka, ad)
        if n < beklenen:
            capa_sapan.append("%s/%s: %d < çapa %d" % (marka, ad, n, beklenen))
    dogrula("B1 ÇAKILI ÇAPALARIN HEPSİ TUTUYOR (%d çapa; yüklem yalnız GENİŞLETİR)"
            % len(CAPALAR), not capa_sapan, "sapan=%s · ölçülen=%s"
            % (capa_sapan or "-",
               ["%s/%s=%d" % (m, a, sayi(kova, evren, m, a)) for m, a, _o, _b in CAPALAR]))

    # --- B) KOL AYRIMI: her kol AYRI sayfada iş yapıyor -----------------------------
    vitara = sayi(kova, evren, "Suzuki", "Vitara")
    transporter = sayi(kova, evren, "Volkswagen", "Transporter")
    dogrula("B2 BAŞLIK KOLU İŞ YAPIYOR (Vitara sınıfı: resmî üyelik 27 -> %d)" % vitara,
            vitara >= 66, "vitara=%d (çapa 66; başlık kolu düşerse 27'ye iner)" % vitara)
    dogrula("B3 KANON/KUŞAK KOLU İŞ YAPIYOR (Transporter sınıfı: %d)" % transporter,
            transporter >= 145,
            "transporter=%d (çapa 145; kanon kolu düşerse ~101 kalem/4 sayfa kaybolur)"
            % transporter)

    # --- C) TEHLİKE SINIFI: kural TÜRETİLİYOR (sabit liste değil) -------------------
    sinif_sapan = [(j, b, mm.tehlike_jetonu_mu(j))
                   for j, b in SINIF_FIKSTURU if mm.tehlike_jetonu_mu(j) != b]
    dogrula("B4 TEHLİKE SINIFI KURALI FİKSTÜRE UYUYOR (%d jeton; uzunluk<=3 YA DA sayısal)"
            % len(SINIF_FIKSTURU), not sinif_sapan, "sapan=%s" % (sinif_sapan or "-"))

    # --- D) BİTİŞİKLİK: `markaKatla()` DEĞİL, DÜZ İFADE ----------------------------
    def _bit(fikstur):
        sapan = []
        for baslik, marka, jeton, beklenen in fikstur:
            adlar = [mm._kelimeler(x) for x in mm.marka_yazimlari(marka, evren)]
            g = mm.baslikta_tam_kelime(mm._kelimeler(baslik), adlar, jeton)
            if g != beklenen:
                sapan.append("%r + %s|%s -> %s (beklenen %s)"
                             % (baslik, marka, jeton, g, beklenen))
        return sapan

    _s1 = _bit(BITISIKLIK_MARKASIZ)
    dogrula("B5a TEHLİKE JETONU MARKASIZ BAŞLIKTA GEÇMEZ (%d fikstür; koruma düşerse "
            "KIRMIZI)" % len(BITISIKLIK_MARKASIZ), not _s1, "sapan=%s" % (_s1[:3] or "-"))
    _s2 = _bit(BITISIKLIK_KATLAMALI)
    dogrula("B5b BİTİŞİKLİK ÖNEK KATLAMASINDAN BAĞIMSIZ (%d fikstür; 'Renault Espace 5' ve "
            "'Subaru BRZ / Toyota 86' REDDEDİLİR)" % len(BITISIKLIK_KATLAMALI),
            not _s2, "sapan=%s" % (_s2[:3] or "-"))

    # --- E) TURNUSOLLAR: tehlike sınıfı gürültüsü sayfaya SIZMIYOR ------------------
    tur_sapan = []
    for marka, ad, _once, tavan in TEHLIKE_TURNUSOL:
        n = sayi(kova, evren, marka, ad)
        if n > tavan:
            tur_sapan.append("%s/%s: %d > TAVAN %d (tehlike koruması gevşedi)"
                             % (marka, ad, n, tavan))
    dogrula("B6 TEHLİKE TURNUSOLU TAVANI AŞMIYOR (%s)"
            % ", ".join("%s|%s<=%d" % (m, a, t) for m, a, _o, t in TEHLIKE_TURNUSOL),
            not tur_sapan, "sapan=%s · ölçülen=%s"
            % (tur_sapan or "-",
               ["%s/%s=%d" % (m, a, sayi(kova, evren, m, a))
                for m, a, _o, _t in TEHLIKE_TURNUSOL]))
    _ac = evren.model_anahtari(*AYIRT_TURNUSOL)
    ayirt = (kova.get((AYIRT_TURNUSOL[0], _ac)) or (0, False, 0, False, ""))[2]
    dogrula("B7 AYIRT EDİCİ TURNUSOL: %s|%s kovasına BAŞLIK KOLUNDAN ürün GİRMİYOR "
            "(katalogda 'Subaru <marka-dışı jeton> 86 …' başlıkları var; marka+model "
            "BİTİŞİK değil)" % AYIRT_TURNUSOL, ayirt == 0,
            "başlık kolundan eklenen=%d (0 olmalı; hem koruma düşerse hem de bitişiklik "
            "markaKatla ile yazılırsa dolar)" % ayirt)

    # --- F) YARGI KAPISI: yargısız sayfa DOĞMAZ ------------------------------------
    try:
        sys.path.insert(0, os.path.join(kok, "tools"))
        import arama as _arama                                     # noqa: PLC0415
        izin = set((mk, _arama.model_normalize(jt))
                   for mk, jt in _arama.BASLIK_DOGAN_ALLOW)
    except Exception as e:                                         # noqa: BLE001
        raise Olculemedi("arama.BASLIK_DOGAN_ALLOW okunamadı: %r" % (e,))
    # 🔴 BİRİM: "hüküm BEKLEYEN" = başlık kolu olmadan eşiği geçemeyen AMA başlık koluyla
    # eşiği geçen kova (yani hükmedilseydi SAYFA OLACAK olan). Eşiğin altında kalan kovalar
    # bir karar gerektirmez ve bu sayıya KARIŞMAZ — model-uyelik-kapisi K21 ile aynı birim.
    yargisiz_dogan, bekleyen = [], 0
    ciplak_sayi_dogan, donanim_dogan, kural_dogan = [], [], 0
    for (mk, canon), (n, yayimda, bek, aday, dsp) in kova.items():
        if not bek:
            continue
        if n - bek >= mm.ESIK:
            continue                     # başlık kolu OLMADAN da eşiği geçiyordu
        envanterde = (mk, _arama.model_normalize(canon)) in izin
        if yayimda:
            if not (envanterde or _sasi_kodu(dsp) or _ayri_arac(dsp)):
                yargisiz_dogan.append("%s|%s" % (mk, canon))
            elif not envanterde:
                kural_dogan += 1
            # H1 SINIRI: ÇIPLAK SAYI kural koluyla DOĞAMAZ (`86`, `660`).
            if not envanterde and _ciplak_sayi(dsp):
                ciplak_sayi_dogan.append("%s|%s" % (mk, dsp))
            # H3 DENY KOLU: donanım kuyruklu kova SAYFA AÇMAZ (`Focus ST`).
            if _donanim_kuyruklu(dsp):
                donanim_dogan.append("%s|%s" % (mk, dsp))
        if not yayimda and n >= mm.ESIK and aday:
            bekleyen += 1
    # 📌 Bu sayı, model-uyelik-kapisi K21'in bastığı sayıdan BİRKAÇ kova az olabilir ve bu
    # BEKLENENDİR: burada ölçüt SAYIMDIR (`n - başlık ekli < ESIK`), K21'de üreticinin
    # `baslik_dogan` bayrağıdır (eşik VE birincillik). Aradaki fark = başlık koluyla
    # BİRİNCİLLİK kazanan kovalar. İki ölçüt BİLEREK bağımsızdır (aynısı olsaydı iddia
    # totoloji olurdu); ikisi de aynı sıfırı — "yargısız doğan=0" — savunur.
    dogrula("B8 YARGISIZ SAYFA DOĞMUYOR (başlık kolu sayesinde eşiği geçen kova ancak "
            "ENVANTERDE ya da H1/H3 KURALINDA yargılanmışsa yayımlanır; SAYIM birimiyle "
            "%d kova hüküm BEKLİYOR ve DOĞMADI, %d kova KURALLA doğdu)"
            % (bekleyen, kural_dogan),
            not yargisiz_dogan, "yargısız doğan=%s" % (yargisiz_dogan[:5] or "-"))
    # --- H1/H3 KURAL KOLLARININ SINIRLARI (ayırt edici; kural gevşerse KIRMIZI) -----
    dogrula("B8a H1 SINIRI: ÇIPLAK SAYI kural koluyla SAYFA AÇMIYOR (`86`, `660`, `17` "
            "harf taşımaz -> H1 dışı; yalnız envanterle doğabilir)",
            not ciplak_sayi_dogan, "çıplak sayı doğmuş=%s" % (ciplak_sayi_dogan[:5] or "-"))
    dogrula("B8b H3 DENY KOLU: DONANIM kuyruklu kova SAYFA AÇMIYOR (`Focus ST` tabana "
            "YAPIŞIK -> katlanır, sayfa açmaz)",
            not donanim_dogan, "donanım kuyruklu doğmuş=%s" % (donanim_dogan[:5] or "-"))
    # --- H1/H3 ŞEKİL FİKSTÜRÜ: kural, katalogdan BAĞIMSIZ olarak da çivilenir -------
    # 🔴 NEDEN FİKSTÜR DE VAR: bugünkü katalogda donanım kuyruklu her kova ya deny
    # tablosunda ya eşik altında (ölçüldü: 16 kova, 14'ü eşik altı) — yani B8b canlı
    # veriyle TEK BAŞINA kırmızı yakılamaz. Fikstür ekseni mutantı yine de öldürür.
    _sekil_sapan = []
    for ad, b_sasi, b_ayri, b_donanim in SEKIL_FIKSTURU:
        for etiket, gercek, beklenen in (("sasi", mm.sasi_motor_kodu_mu(ad), b_sasi),
                                         ("ayri", mm.ayri_arac_adi_mi(ad), b_ayri),
                                         ("donanim", mm.donanim_kuyruklu_mu(ad), b_donanim)):
            if gercek != beklenen:
                _sekil_sapan.append("%r %s -> %s (beklenen %s)"
                                    % (ad, etiket, gercek, beklenen))
    dogrula("B10 H1/H3 ŞEKİL KURALI FİKSTÜRE UYUYOR (%d ad × 3 eksen; ÇIPLAK SAYI ve "
            "DONANIM kuyruğu ayrı ayrı çivili)" % len(SEKIL_FIKSTURU),
            not _sekil_sapan, "sapan=%s" % (_sekil_sapan[:4] or "-"))
    # --- H2: DENY'in SON-KELİME kolu YALNIZ DEĞİŞTİRİCİLERE işler ------------------
    _h2_sapan = []
    for marka, ad, beklenen in DENY_BILESIK_FIKSTURU:
        g = mm.model_olmayan_cift_mi(marka, ad)
        if g != beklenen:
            _h2_sapan.append("%s|%s -> %s (beklenen %s)" % (marka, ad, g, beklenen))
    dogrula("B11 H2 DENY SON-KELİME KOLU YALNIZ DEĞİŞTİRİCİYE İŞLER (%d fikstür; "
            "`Focus ST` KAPANIR, `5 E-Tech`/`Megane E-Tech` AÇIK KALIR)"
            % len(DENY_BILESIK_FIKSTURU), not _h2_sapan, "sapan=%s" % (_h2_sapan[:4] or "-"))
    _etech = [k for k in kova
              if k[0] == "Renault" and evren.model_anahtari("Renault", "E-Tech") == k[1]]
    _etech_yayin = any(kova[k][1] for k in _etech)
    _5etech = kova.get(("Renault", evren.model_anahtari("Renault", "5 E-Tech")))
    dogrula("B12 H2 TURNUSOLU: çıplak `E-Tech` SAYFA AÇMAZ, `5 E-Tech` sayfası AÇIK KALIR, "
            "`Renault|5` ürün sayısı DÜŞMEZ (>=14)",
            (not _etech_yayin) and bool(_5etech) and _5etech[1]
            and sayi(kova, evren, "Renault", "5") >= 14,
            "E-Tech yayında=%s · 5 E-Tech yayında=%s · Renault|5=%d"
            % (_etech_yayin, bool(_5etech) and _5etech[1],
               sayi(kova, evren, "Renault", "5")))
    # --- H1/H3 CANLI VERİ ÇAPALARI: kural kolları GERÇEKTEN sayfa doğuruyor ---------
    def _capa_sapan(capalar):
        sapan = []
        for marka, ad, en_az in capalar:
            c = evren.model_anahtari(marka, ad)
            v = kova.get((marka, c))
            if not v or not v[1] or v[0] < en_az:
                sapan.append("%s|%s: yayın=%s n=%s (en az %d)"
                             % (marka, ad, bool(v) and v[1], bool(v) and v[0], en_az))
        return sapan

    _h1s = _capa_sapan(H1_CAPA_SAYFA)
    dogrula("B14a H1 KURALI CANLI VERİDE SAYFA DOĞURUYOR (%d çapa; şasi/motor kodu "
            "sayfaları YAYINDA)" % len(H1_CAPA_SAYFA), not _h1s, "sapan=%s" % (_h1s[:3] or "-"))
    _h3s = _capa_sapan(H3_CAPA_SAYFA)
    dogrula("B14b H3 KURALI CANLI VERİDE SAYFA DOĞURUYOR (%d çapa; ayrı araç adı "
            "sayfaları YAYINDA)" % len(H3_CAPA_SAYFA), not _h3s, "sapan=%s" % (_h3s[:3] or "-"))
    # --- H4: AKSAN KANONDA ÇÖZÜLÜYOR — ikiz kova KALMIYOR --------------------------
    _aksan_ikiz = []
    for marka, a, b in AKSAN_IKIZ_FIKSTURU:
        ka, kb = evren.model_anahtari(marka, a), evren.model_anahtari(marka, b)
        if ka != kb:
            _aksan_ikiz.append("%s|%s(%s) != %s(%s)" % (marka, a, ka, b, kb))
        elif (marka, ka) in kova and (marka, kb) in kova and ka != kb:
            _aksan_ikiz.append("%s: İKİ KOVA %s/%s" % (marka, ka, kb))
    _ayri_kova = sorted(set(c for (_m, c) in kova
                            if c != _arama.model_normalize(c) or _aksanli(c)))
    dogrula("B13 H4 AKSAN KANONDA ÇÖZÜLÜYOR (%d ikiz çifti TEK anahtara düşüyor; aksanlı "
            "kanon anahtarı KALMADI)" % len(AKSAN_IKIZ_FIKSTURU),
            not _aksan_ikiz and not _ayri_kova,
            "ikiz sapan=%s · aksanlı kanon=%s" % (_aksan_ikiz[:3] or "-",
                                                  _ayri_kova[:3] or "-"))

    # --- ADIM 3 HÜKÜMLERİ (6 Ağu) — DENY tarafları AYRI AYRI ölçülür ----------------
    def _yayimda(marka, ad):
        c = evren.model_anahtari(marka, ad)
        v = kova.get((marka, c)) if c else None
        return (bool(v) and v[1], (v or (0,))[0])

    def _deny_sapan(fikstur):
        sapan = []
        for marka, ad in fikstur:
            yayimda, n = _yayimda(marka, ad)
            if yayimda:
                sapan.append("%s|%s SAYFA DOĞDU (n=%d)" % (marka, ad, n))
        return sapan

    _a = _deny_sapan(HUKUM_A_DENY)
    dogrula("B15a HÜKÜM A — ÇAPRAZ MARKA ROZETİ DENY: %d çiftin HİÇBİRİ sayfa AÇMIYOR "
            "(model o markanın KENDİ rozetiyle satılmadı; ürünler gerçek rozet sayfasında "
            "ve marka sayfasında durur)" % len(HUKUM_A_DENY),
            not _a, "sahte sayfa=%s" % (_a[:4] or "-"))
    _b = _deny_sapan(HUKUM_B_DENY)
    dogrula("B15b HÜKÜM B — ÇIPLAK SAYI DENY: `Yamaha|660` sayfa AÇMIYOR (hangi aracı "
            "adlandırdığı belirsiz; 3 ürün için tekil giriş AÇILMADI)",
            not _b, "sahte sayfa=%s" % (_b or "-"))
    _d = _deny_sapan(HUKUM_D_DENY)
    dogrula("B15c HÜKÜM D — MODEL OLMAYAN AD DENY: `Volkswagen|Westfalia` sayfa AÇMIYOR "
            "(kamper dönüştürücüsü, VW modeli DEĞİL)",
            not _d, "sahte sayfa=%s" % (_d or "-"))
    _allow_sapan = []
    for marka, ad, en_az in HUKUM_ALLOW:
        yayimda, n = _yayimda(marka, ad)
        if not yayimda or n < en_az:
            _allow_sapan.append("%s|%s: yayın=%s n=%d (en az %d)"
                                % (marka, ad, yayimda, n, en_az))
    dogrula("B16 HÜKÜM A/B/D ALLOW — hükmedilen %d sayfanın hepsi YAYINDA ve çapasını "
            "tutuyor (tekil giriş GERÇEKTEN sayfa doğuruyor)" % len(HUKUM_ALLOW),
            not _allow_sapan, "sapan=%s" % (_allow_sapan[:4] or "-"))
    # 🔴 ÇIPLAK SAYI KURALI GEVŞEMEDİ — CANLI VERİ EKSENİ (B10 fikstür eksenidir, bu değil):
    # `Toyota|86` TEKİL GİRİŞLE açıldı; kuralın kendisi çıplak sayıya HÂLÂ kapalı olmalı.
    _ciplak_kural = sorted("%s|%s" % (mk, dsp) for (mk, _c), (_n, _y, _b, _a, dsp)
                           in kova.items() if _ciplak_sayi(dsp) and mm.sasi_motor_kodu_mu(dsp))
    dogrula("B8c H1 KURALI ÇIPLAK SAYIYA KAPALI (katalog geneli: üretim yüklemi çıplak "
            "sayılı hiçbir kova adına ŞASİ/MOTOR KODU demiyor; `Toyota|86` sayfası "
            "ENVANTERDEN doğdu, kuraldan DEĞİL)",
            not _ciplak_kural, "kural çıplak sayıya True dedi=%s" % (_ciplak_kural[:5] or "-"))
    # --- E) ARAÇ DIŞI MUAFİYETİ: sayfa DURUYOR ama KURAL onu doğurmuyor -------------
    # 🔴 ÜÇ PARÇALI İDDİA: (1) çift GERÇEKTEN şekil kuralının şeklinde (muafiyet iş yapıyor,
    # ölü giriş değil — bağımsız oracle ile ölçülür), (2) ÜRETİM kuralı ona yargı VERMİYOR,
    # (3) sayfa yine de YAYINDA (tekil giriş onu taşıyor). Yalnız (3) yazılsaydı muafiyeti
    # düşüren mutant sayfayı bozmadığı için YEŞİL geçerdi.
    _muaf_sapan = []
    for marka, ad, en_az in HUKUM_E_MUAF:
        c = evren.model_anahtari(marka, ad)
        v = kova.get((marka, c)) if c else None
        dsp = (v or (0, False, 0, False, ad))[4] or ad
        if not (_sasi_kodu(dsp) or _ayri_arac(dsp)):
            _muaf_sapan.append("%s|%s ŞEKİL KURALININ ŞEKLİNDE DEĞİL -> muafiyet ÖLÜ giriş"
                               % (marka, ad))
        if mm.sekil_kurali_yargisi(marka, c, dsp):
            _muaf_sapan.append("%s|%s ÜRETİM ŞEKİL KURALI YARGI VERİYOR (muafiyet ÖLÜ)"
                               % (marka, ad))
        if (marka, c) not in mm.SEKIL_MUAF:
            _muaf_sapan.append("%s|%s SEKIL_MUAF'ta YOK" % (marka, ad))
        if not v or not v[1] or v[0] < en_az:
            _muaf_sapan.append("%s|%s SAYFA DÜŞTÜ (yayın=%s n=%s)"
                               % (marka, ad, bool(v) and v[1], bool(v) and v[0]))
    dogrula("B20 HÜKÜM E — ARAÇ DIŞI SAYFA TEKİL GİRİŞLE DOĞUYOR, ŞEKİL KURALIYLA DEĞİL "
            "(%d çift: şekli kurala uyuyor, üretim kuralı SUSUYOR, sayfa YAYINDA)"
            % len(HUKUM_E_MUAF), not _muaf_sapan, "sapan=%s" % (_muaf_sapan[:4] or "-"))

    # --- G) KAYBEDEN YOK: hiçbir ürün kovasından DÜŞMEZ ----------------------------
    # (Kol yalnız EKLER; ölçüt yapısal: başlık kolu hiçbir kovadan ürün ÇIKARMAZ.)
    dogrula("B9 KONTROL: ölçüm dejenere değil (başlık kolu GERÇEKTEN üyelik ekliyor)",
            sum(v[2] for v in kova.values()) > 1000,
            "başlık kolundan eklenen (kova,ürün) üyeliği=%d"
            % sum(v[2] for v in kova.values()))

    print("\nSONUC: %d/%d iddia %s" % (len(kaldi) if kaldi else len(gecen),
                                       len(gecen) + len(kaldi),
                                       "KALDI ❌" if kaldi else "GECTI ✔"))
    return 1 if kaldi else 0


# ---------------------------------------------------------------- mutasyon bataryası
MUTANTLAR = [
    # --- ÖLDÜRÜCÜ: üç kol + tehlike koruması, ÜÇÜ FARKLI SAYFADA ---
    ("tools/marka_model_build.py",
     "            for taban, _etiket in evren.kusak_tabanlari(kan, t):",
     "            for taban, _etiket in ():", "KIRMIZI",
     "M1 KANON/KUŞAK KOLUNU DÜŞÜR -> Transporter sınıfında sayı DÜŞER (B3 kırmızı; "
     "Vitara ve Renault|5 DEĞİŞMEZ -> eksen ayırt edici)"),
    ("tools/marka_model_build.py",
     "                if not any(baslikta_tam_kelime(baslik_kelimeleri, ad_kelimeleri, y)\n"
     "                           for y in yazimlar):\n                    continue",
     "                if True:\n                    continue", "KIRMIZI",
     "M2 BAŞLIK KOLUNU DÜŞÜR -> Vitara 66 -> 27 (B2 kırmızı; Transporter neredeyse "
     "değişmez -> eksen ayırt edici)"),
    ("tools/marka_model_build.py",
     "    j = \"\".join(_kelimeler(jeton))\n    return (not j) or len(j) <= 3 or j.isdigit()",
     "    j = \"\".join(_kelimeler(jeton))\n    return not j", "KIRMIZI",
     "M3 TEHLİKE SINIFI KORUMASINI DÜŞÜR -> çıplak `5` 'Clio 5'/'Espace 5'i yakalar, "
     "Renault|5 TAVANI AŞAR (B6) ve Subaru|86 kovası DOĞAR (B7)"),
    ("tools/marka_model_build.py",
     "    for aw in marka_ad_kelimeleri:\n"
     "        if aw and _dizi_iceriyor(baslik_kelimeleri, aw + jw):\n"
     "            return True\n    return False",
     "    for i in range(len(baslik_kelimeleri) - len(jw) + 1):\n"
     "        if baslik_kelimeleri[i:i + len(jw)] != jw or i == 0:\n"
     "            continue\n"
     "        if _MARKA_KATLA and _MARKA_KATLA(\" \".join(baslik_kelimeleri[:i])) \\\n"
     "                in _KATLA_HEDEF:\n"
     "            return True\n    return False", "KIRMIZI",
     "M4 BİTİŞİKLİĞİ `markaKatla()` İLE YAZ -> önek kuralı 'Renault Espace'i 'Renault'a "
     "katlar, tehlike koruması SESSİZCE ölür (B5 fikstürü + B7 Subaru|86 turnusolu)"),
    # --- ÖLDÜRÜCÜ: H1 / H2 / H3 / H4 (6 Ağu, mimar hükmü) — kırmızı kümeleri AYRI ---
    ("tools/marka_model_build.py",
     "    return bool(j) and any(c.isalpha() for c in j) and any(c.isdigit() for c in j)",
     "    return False", "KIRMIZI",
     "M5 H1 ŞASİ/MOTOR KODU DESENİNİ KALDIR -> `M54`/`W638`/`SW20` sayfaları ÖLÜR "
     "(B14a çapaları + B10 fikstürü; H3 çapaları B14b DEĞİŞMEZ -> ayırt edici)"),
    ("tools/marka_model_build.py",
     "    j = \"\".join(_kelimeler(deger))\n"
     "    return bool(j) and any(c.isalpha() for c in j) and any(c.isdigit() for c in j)",
     "    j = \"\".join(_kelimeler(deger))\n    return bool(j) and any(c.isdigit() for c in j)",
     "KIRMIZI",
     "M6 H1'e ÇIPLAK SAYIYI SOK -> `Toyota|86` ve `Yamaha|660` sayfaları DOĞAR "
     "(B8a + B10; H1 çapaları AYAKTA kalır -> M5'ten AYIRT EDİCİ)"),
    ("tools/marka_model_build.py",
     "    return (toks[-1] or \"\").lower() in set(x.lower() for x in model_kanon.KUSAK_DONANIM)",
     "    return False", "KIRMIZI",
     "M7 H3 KATLAMA KURALINI 'HER DEĞİŞTİRİCİ SAYFA ALIR'A ÇEVİR -> donanım kuyruklu kova "
     "sayfa adayı olur (B10 + B8b; `Focus ST` sınıfı)"),
    ("tools/marka_model_build.py",
     "    if len(toks) < 2 or not degistirici_jetonu_mu(toks[-1]):\n        return False",
     "    if len(toks) < 2:\n        return False", "KIRMIZI",
     "M8 H2 KATLAMA/DENY DARALTMASINI KALDIR (son-kelime kolu kayıtsız koşsun) -> "
     "`/marka/renault/5-e-tech/` ve `megane-e-tech` KAPANIR (B11 + B12)"),
    ("tools/arama.py",
     "    (\"Renault\", \"E-Tech\"): \"elektrifikasyon/guc aktarma rozeti",
     "    (\"Renault\", \"E-TechYOK\"): \"elektrifikasyon/guc aktarma rozeti", "KIRMIZI",
     "M9 H2 DENY'İNİ DÜŞÜR -> çıplak `E-Tech` kovası SAYFA AÇAR (B12; `5 E-Tech` AYAKTA "
     "kalır -> M8'den AYIRT EDİCİ, ters yöne kayar)"),
    ("tools/model_kanon.py",
     "    t = unicodedata.normalize(\"NFD\", t)\n"
     "    t = \"\".join(ch for ch in t if not unicodedata.combining(ch))\n"
     "    return _AYIRAC.sub(\"\", t)",
     "    return _AYIRAC.sub(\"\", t)", "KIRMIZI",
     "M10 H4 AKSAN ÇÖZÜMÜNÜ KALDIR -> `Zoe`/`Zoé` yeniden İKİ kova, `Ténéré` ikizi geri "
     "gelir (B13)"),
    # --- ÖLDÜRÜCÜ: ADIM 3 hükümleri (6 Ağu) — A / B / D / E, kırmızı kümeleri AYRI ------
    # 🔴 HER MUTANT TEK BİR HÜKMÜ VURUR: A/B/D'nin deny'leri AYRI iddialara (B15a/b/c)
    # bağlı olduğu için "deny -> allow" mutantları birbirinden AYIRT EDİLEBİLİR.
    # 6. eleman = EK DÜZENLEME listesi (deny'i kaldır + allow'a yaz aynı mutantta olmalı;
    # yalnız birini yapmak sayfayı doğurmaz ve eksen ÖLÇÜLMEZ).
    ("tools/arama.py",
     "    (\"Citroen\", \"Aygo\"): \"Citroen'in rozeti C1;",
     "    (\"Citroen\", \"AygoYOK\"): \"Citroen'in rozeti C1;", "KIRMIZI",
     "M11 HÜKÜM A DENY'İNİ ALLOW'A ÇEVİR (`Citroen|Aygo`) -> SAHTE çapraz-rozet sayfası "
     "/marka/citroen/aygo/ DOĞAR (B15a; B15b/B15c DEĞİŞMEZ -> ayırt edici)",
     [("tools/arama.py",
       "    (\"Citroen\", \"C8\"): \"arac/motosiklet model adi\",",
       "    (\"Citroen\", \"C8\"): \"arac/motosiklet model adi\",\n"
       "    (\"Citroen\", \"Aygo\"): \"MUTANT allow\",")]),
    ("tools/arama.py",
     "    (\"Yamaha\", \"660\"): \"ciplak sayi",
     "    (\"Yamaha\", \"660YOK\"): \"ciplak sayi", "KIRMIZI",
     "M12 HÜKÜM B DENY'İNİ ALLOW'A ÇEVİR (`Yamaha|660`) -> ÇIPLAK SAYI sayfası DOĞAR "
     "(B15b; A ve D deny'leri AYAKTA -> ayırt edici)",
     [("tools/arama.py",
       "    (\"Yamaha\", \"Seca\"): \"arac/motosiklet model adi\",",
       "    (\"Yamaha\", \"660\"): \"MUTANT allow\",\n"
       "    (\"Yamaha\", \"Seca\"): \"arac/motosiklet model adi\",")]),
    ("tools/arama.py",
     "    (\"Volkswagen\", \"Westfalia\"): \"kamper donusturucusu",
     "    (\"Volkswagen\", \"WestfaliaYOK\"): \"kamper donusturucusu", "KIRMIZI",
     "M13 HÜKÜM D DENY'İNİ ALLOW'A ÇEVİR (`Volkswagen|Westfalia`) -> kamper "
     "dönüştürücüsüne MODEL sayfası DOĞAR (B15c; A ve B deny'leri AYAKTA -> ayırt edici)",
     [("tools/arama.py",
       "    (\"Volkswagen\", \"Vento\"): \"arac/motosiklet model adi\",",
       "    (\"Volkswagen\", \"Vento\"): \"arac/motosiklet model adi\",\n"
       "    (\"Volkswagen\", \"Westfalia\"): \"MUTANT allow\",")]),
    ("tools/arama.py",
     "    (\"Toyota\", \"86\"): \"Toyota 86 GERCEK rozet",
     "    (\"Toyota\", \"86YOK\"): \"Toyota 86 GERCEK rozet", "KIRMIZI",
     "M14 `Toyota|86` TEKİL GİRİŞİNİ KURALA ÇEVİR (envanterden çıkar + H1'i çıplak sayıya "
     "aç) -> ÇIPLAK SAYI KORUMASI ÖLÜR ve sayfa KURALDAN doğar (B8a + B8c + B10; M6'dan "
     "B8a ile AYRILIR — M6 girişi envanterde BIRAKIR)",
     [("tools/marka_model_build.py",
       "    j = \"\".join(_kelimeler(deger))\n"
       "    return bool(j) and any(c.isalpha() for c in j) and any(c.isdigit() for c in j)",
       "    j = \"\".join(_kelimeler(deger))\n"
       "    return bool(j) and any(c.isdigit() for c in j)")]),
    ("tools/arama.py",
     "    (\"Suzuki\", \"DR\"): \"arac/motosiklet AILE adi (DR serisi)\",",
     "    (\"Suzuki\", \"DRYOK\"): \"arac/motosiklet AILE adi (DR serisi)\",", "KIRMIZI",
     "M15 HÜKÜM B ALLOW'UNU DÜŞÜR (`Suzuki|DR`) -> hükmedilen sayfa DOĞMAZ (B16; deny "
     "eksenleri B15a/b/c DEĞİŞMEZ -> ters yön, ayırt edici)"),
    ("tools/marka_model_build.py",
     "    if (marka, canon) in SEKIL_MUAF:\n        return False\n"
     "    return sasi_motor_kodu_mu(ad) or ayri_arac_adi_mi(ad)",
     "    return sasi_motor_kodu_mu(ad) or ayri_arac_adi_mi(ad)", "KIRMIZI",
     "M16 HÜKÜM E MUAFİYETİNİ DÜŞÜR (tekil girişi ŞEKİL KURALINA geri bağla) -> araç DIŞI "
     "sayfa (`Yamaha|P-45`, `Recording Custom`) KURALLA/YARGISIZ doğar (B20 TEK BAŞINA)"),
    # --- KONTROL (YEŞİL bekleniyor) ---
    ("tools/arama.py",
     "    (\"Audi\", \"AdBlue\"): \"dizel egzoz katki sivisi (AdBlue) — arac modeli degil\",\n"
     "    (\"Audi\", \"Coupe\"): \"govde tipi sozcugu (Audi 80/B2 Coupe) — bagimsiz model adi degil\",",
     "    (\"Audi\", \"Coupe\"): \"govde tipi sozcugu (Audi 80/B2 Coupe) — bagimsiz model adi degil\",\n"
     "    (\"Audi\", \"AdBlue\"): \"dizel egzoz katki sivisi (AdBlue) — arac modeli degil\",",
     "YESIL",
     "K4 KONTROL: DENY tablosunu YENİDEN SIRALA -> küme ve davranış AYNI (daima-kırmızı "
     "bir H2 ekseni M8/M9'u da geçerdi)"),
    ("tools/marka_model_build.py",
     "    (\"BMW\", \"kserisi\"): \"K Serisi\",\n",
     "    (\"BMW\", \"kserisi\"): \"K Serisi\",  # yorum (davranış AYNI)\n", "YESIL",
     "K1 KONTROL: davranış değiştirmeyen yorum -> iddia bozulmamalı (daima-kırmızı bir "
     "kabul M1-M4'ü de geçerdi)"),
    ("tools/arama.py",
     "    (\"Audi\", \"Q3\"): \"arac/motosiklet model adi\",\n"
     "    (\"Audi\", \"TT\"): \"arac/motosiklet model adi\",",
     "    (\"Audi\", \"TT\"): \"arac/motosiklet model adi\",\n"
     "    (\"Audi\", \"Q3\"): \"arac/motosiklet model adi\",", "YESIL",
     "K2 KONTROL: allow envanterini YENİDEN SIRALA -> küme ve davranış AYNI"),
    ("tools/cip-indeks.py", "SURUM = 1", "SURUM = 2", "YESIL",
     "K3 KONTROL: İLGİSİZ ALAN (çip indeksi sürümü) model üyeliğinde rol OYNAMAZ"),
]

# M4 mutantının ihtiyaç duyduğu kanca — üretim gövdesine SIZMAZ, yalnız mutant kopyada
# anlam kazanır (gerçek ağaçta ikisi de None/boş kümedir).
_M4_KANCA = ("_MARKA_KATLA = None\n_KATLA_HEDEF = frozenset()\n\n\n"
             "def baslikta_tam_kelime(")


def _kok_kur(tmp):
    os.makedirs(os.path.join(tmp, "tools"))
    for ad in os.listdir(os.path.join(GERCEK_KOK, "tools")):
        k = os.path.join(GERCEK_KOK, "tools", ad)
        if os.path.isfile(k):
            shutil.copy2(k, os.path.join(tmp, "tools", ad))
    shutil.copy2(os.path.join(GERCEK_KOK, "index.html"), os.path.join(tmp, "index.html"))
    for ad in os.listdir(GERCEK_KOK):
        if ad in ("tools", "index.html", ".git"):
            continue
        os.symlink(os.path.join(GERCEK_KOK, ad), os.path.join(tmp, ad))


def kendini_test():
    print("MUTASYON — başlık kolu (mutant KOPYAYA uygulanır; gerçek ağaç DEĞİŞMEZ)")
    basarisiz, olcum = [], []
    for i, m in enumerate(MUTANTLAR, 1):
        dosya, eski, yeni, beklenen, aciklama = m[:5]
        # 6. eleman (opsiyonel): EK DÜZENLEME listesi — bir hüküm ancak İKİ tabloda birden
        # oynanınca ölçülebiliyorsa (deny'i kaldır + allow'a yaz) tek mutantta yapılır;
        # yarısını yapmak sayfayı doğurmaz ve eksen SESSİZCE ölçülmemiş olurdu.
        ek_duzenleme = m[5] if len(m) > 5 else ()
        tmp = tempfile.mkdtemp(prefix="baslik-kolu-mut-")
        try:
            _kok_kur(tmp)
            yol = os.path.join(tmp, *dosya.split("/"))
            with open(yol, encoding="utf-8") as f:
                metin = f.read()
            # 🔴 ÇAPA TAM BİR KEZ EŞLEŞMELİ: kayan çapa "geçti" DEĞİL, eksen ÖLÇÜLMEMİŞ demektir.
            if metin.count(eski) != 1:
                print("  HATA M%02d: mutant ÇAPASI %d eşleşme (%s) | EKSEN ÖLÇÜLMEDİ -> %s"
                      % (i, metin.count(eski), dosya, aciklama))
                basarisiz.append("M%02d capa %d" % (i, metin.count(eski)))
                continue
            metin = metin.replace(eski, yeni, 1)
            # EK DÜZENLEMELER — her biri de TAM BİR KEZ eşleşmeli (aynı fail-closed disiplin).
            _ek_hata = None
            for _d2, _e2, _y2 in ek_duzenleme:
                _yol2 = os.path.join(tmp, *_d2.split("/"))
                _m2 = metin if _yol2 == yol else open(_yol2, encoding="utf-8").read()
                if _m2.count(_e2) != 1:
                    _ek_hata = "ek capa %d (%s)" % (_m2.count(_e2), _d2)
                    break
                _m2 = _m2.replace(_e2, _y2, 1)
                if _yol2 == yol:
                    metin = _m2
                else:
                    with open(_yol2, "w", encoding="utf-8") as f:
                        f.write(_m2)
            if _ek_hata:
                print("  HATA M%02d: %s | EKSEN ÖLÇÜLMEDİ -> %s" % (i, _ek_hata, aciklama))
                basarisiz.append("M%02d %s" % (i, _ek_hata))
                continue
            if "_MARKA_KATLA" in yeni:
                metin = metin.replace("def baslikta_tam_kelime(", _M4_KANCA, 1)
                # Mutantın GERÇEKTEN katlama yapması için kancayı evrene bağla.
                metin = metin.replace(
                    "        ad_kelimeleri = [_kelimeler(a) for a in marka_yazimlari(marka, evren)]",
                    "        ad_kelimeleri = [_kelimeler(a) for a in marka_yazimlari(marka, evren)]\n"
                    "        globals()[\"_MARKA_KATLA\"] = evren.katla\n"
                    "        globals()[\"_KATLA_HEDEF\"] = frozenset([marka])", 1)
            with open(yol, "w", encoding="utf-8") as f:
                f.write(metin)
            p = subprocess.run([sys.executable,
                                os.path.join(tmp, "tools", "model-baslik-kolu-test.py"),
                                "--kok", tmp], capture_output=True, text=True, timeout=3600)
            kirmizi = [s for s in (p.stdout or "").splitlines() if s.strip().startswith("KALDI")]
            # 🔴 ÇÖKME KIRMIZIYLA KARIŞMAZ: kabul ölçütü çıkış kodu DEĞİL, ölçülen iddia + işaret.
            if p.returncode not in (0, 1) or (p.returncode == 1 and not kirmizi):
                print("  HATA M%02d [%s] -> COKME/OLCULEMEDI (rc=%d) | %s"
                      % (i, beklenen, p.returncode, aciklama))
                print("        " + ((p.stderr or p.stdout or "").strip().splitlines()
                                    or [""])[-1][:180])
                basarisiz.append("M%02d [cokme]" % i)
                continue
            gercek = "YESIL" if p.returncode == 0 else "KIRMIZI"
            ok = gercek == beklenen
            print("  %-4s M%02d [%s] -> %s (%d iddia kırmızı) | %s"
                  % ("OK" if ok else "HATA", i, beklenen, gercek, len(kirmizi), aciklama))
            for s in kirmizi[:2]:
                print("        " + s.strip()[:170])
            olcum.append((i, beklenen, gercek, tuple(s.strip()[:12] for s in kirmizi)))
            if not ok:
                basarisiz.append("M%02d" % i)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    # AYIRT EDİCİLİK: öldürücü mutantların KIRMIZI YAKTIĞI İDDİA KÜMELERİ birbirinden
    # FARKLI olmalı — aynı küme çıkarsa "daima kırmızı" tek bir eksen hepsini geçmiş olur.
    oldurucu = [(i, k) for i, b, _g, k in olcum if b == "KIRMIZI"]
    kumeler = {}
    for i, k in oldurucu:
        kumeler.setdefault(k, []).append(i)
    ayirt_edilemeyen = [v for v in kumeler.values() if len(v) > 1]
    if ayirt_edilemeyen:
        print("  UYARI: aynı iddia kümesini kırmızı yakan mutantlar (AYIRT EDİLEMİYOR): %s"
              % ayirt_edilemeyen)
        basarisiz.append("ayirt-edilemeyen %s" % ayirt_edilemeyen)
    kontrol = sum(1 for _i, b, _g, _k in olcum if b == "YESIL")
    print("\nMUTASYON: %d öldürücü + %d kontrol koştu · ayırt edici küme=%d · "
          "beklentiyi tutmayan: %d %s"
          % (len(oldurucu), kontrol, len(kumeler), len(basarisiz), basarisiz or ""))
    return 1 if basarisiz else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kok", default=GERCEK_KOK)
    ap.add_argument("--kendini-test", action="store_true")
    a = ap.parse_args()
    if a.kendini_test:
        return kendini_test()
    try:
        return kabul(a.kok)
    except Olculemedi as e:
        print("\nSONUC: OLCULEMEDI ❓  %s" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
