#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ALT KATEGORI SINIFLANDIRICI — deterministik, UC GECISLI, urun verisine YAZMAZ.

  python3 tools/altkategori-sinifla.py --rapor          # gercek katalogda dagilim
  python3 tools/altkategori-sinifla.py --esik-tarama    # 2. gecis esigi duyarlilik olcumu

🔴 BU MODUL urunler.json'a YAZMAZ. Yalnizca HESAPLAR ve RAPORLAR. Alani yazan tek mesru
yol tools/duzelt.py'dir (MaCiT duzlemi) ve o da arama.altkategori_sebebi kapisindan gecer.

NEDEN VAR (olculdu, 2 Agu): `altkategori` yalnizca `Marin`de tanimliydi (12 deger, 935
kayit); katalogun %94'unde alan BOSTU. Kategori sayfalari yiginla urun gosteriyordu ve
daraltma yuzeyi YOKTU. Bu modul taksonomiyi TEK YERDE kurar ve hangi urunun hangi gruba
dustugunu OLCULEBILIR bir kuralla hesaplar.

── EKSEN: YER / SISTEM / KULLANIM ALANI — SEKIL DEGIL (mimar karari K1) ───────────────
OLCULDU (12.481 Otomobil urunu): sekil ekseni (`Kapaklar`, `Klipsler`, `Tutucular`) 60
grup uretiyor, urunlerin %88,99'u BIRDEN FAZLA gruba dusuyor, en buyuk grup katalogun
%37,37'si — yigilmayi COZMUYOR, adini degistiriyor. Yer/sistem ekseni: 16 grup, cakisma
%24,89, en buyuk grup %13,80. Bu yuzden bir grup adi parcanin BICIMINI ya da BAGLANTI
TURUNU adlandiriyorsa (kapak, tapa, klips, braket, conta, kablo, tutucu) kumeye GIRMEZ;
adlandirdigi sey parcanin BULUNDUGU YER, ait oldugu SISTEM ya da KULLANIM ALANI olmali.
Reddedilen sekil adlari asagida `SEKIL_RED` sinifiyla KAYITLIDIR — bir sonraki tur ayni
adaylari yeniden "kesfedip" kapanmis karari yeniden tartismasin.

── UC GECIS (Okan karari, 2 Agu: "yakin kategorilerine tasi, urunler bos kalmasin") ────
  1. GECIS  DETERMINISTIK TERIM: grup terim tablosu + oncelik sirasi. Yuksek guven.
  2. GECIS  YAKINLIK: 1. gecisten atanamayan urun, gruplarin SOZLUGUNE karsi puanlanir.
            🔴 SOZLUK ELLE YAZILMAZ — 1. GECISTE O GRUBA DUSEN URUNLERIN BASLIK
            JETONLARINDAN TURETILIR (log-odds, asagida). Yani "yakinlik" bir sezgi degil,
            VERININ KENDI OLCUSU. Puan esigin altindaysa atama YAPILMAZ, 3. gecise kalir.
  3. GECIS  ARTIK KOVA: hala atanamayan urun kategorinin artik kovasina gider -> BOS 0.

⚠️ ARTIK KOVA COPLUGE DONMESIN: isin sebebi yigilmaydi; 12 bin urunu tek gruba dokmek
yigilmayi TASIR, cozmez. Bu yuzden --rapor her grup icin gecis kirilimini basar ve bir
grubun ESIK_COPLUK_ORANI kadari (bugun %20) 2./3. gecisten geliyorsa ISARETLER. Isaret
RAPORDUR, kapiyi kirmizi yakmaz (kapi GECERLILIK olcer, dagilim degil).

── TIP / YER ONCELIGI (mimar karari K5, 2 Agu 2. tur) ──────────────────────────────────
Bir grup parcanin TIPINI adlandiriyorsa (bardaklik, kulluk, saklama, sele), YERINI
adlandiran gruptan (konsol, torpido, canta, klima menfezi) ONCE gelir. OLCULDU ki tersi
SESSIZ bir hataydi: ayni tipteki 623 bardaklik urunu 12 gruba dagiliyordu ve hicbir kapi
kirmizi yanmiyordu — her atama TEK BASINA gecerliydi, YANLIS olan gruplamaydi.

── OLCULDU AMA YAPILMADI: `pervane` (2 Agu 2. tur) ─────────────────────────────────────
`pervane` terimi 140 urunde geciyor ve 27'si `Tutyalar ve Anotlar`da. Ilk bakista bu bir
dagilma gibi duruyor; OLCUM aksini soyledi: o 27 urunun 27'sinde AYRICA tutya/anot terimi
var ve hepsinin basligi "... Şaft Tutyası"dir — yani onlar GERCEKTEN anot, pervane degil;
`pervane` yalnizca ACIKLAMADA (pervane safti) geciyor. Ters yon de olculdu: `Pervaneler`
grubunun 113 urununun 0'inda tutya/anot terimi var. `Pervaneler`i `Tutyalar ve Anotlar`in
ONUNE almak 27 ANOTU pervane rafina tasirdi — toplama degil REGRESYON. Bu yuzden Marin
sirasi DEGISTIRILMEDI. Kayit ki bir sonraki tur ayni "duzeltmeyi" yeniden onermesin.

── ESIKLER (mimar karari K4) ──────────────────────────────────────────────────────────
  * Bir KATEGORI ancak >=100 urunu varsa alt kategori ALIR. Bugun hak eden 6 kategori
    asagida; kalan 8 kategori (Ofis 71, Bisiklet 31, Bahce 25, Tamirat 25, Jenerator 23,
    Kamera 21, Skan Art 17, Oyun/Hobi 15) alt kategori ALMAZ. Bu bir EKSIKLIK DEGIL
    KARARDIR: tek ekranda gezilen kategoriye filtre seridi koymak gurultu uretir.
  * Bir GRUP ancak >=15 urun tasiyorsa kumeye girer. Altinda kalan adaylar `ELENEN`
    sinifiyla GEREKCESIYLE kayitli kalir (UYUM_MARKA_ELENEN deseni).
  * Esikler grubun ACILMASINI engeller, urunun ATANMASINI degil: esik altinda kalan
    adayin urunleri 2./3. gecisle acik bir gruba duser.

── MARIN MIRASI (mimar karari K3) ─────────────────────────────────────────────────────
Marin'in 12 mevcut degeri 935 kayitta KULLANILIYOR. Adlari BAYT OLARAK korunur; yeniden
adlandirilmaz, silinmez, >=15 esigine TABI DEGILDIR (sinif `MIRAS`). Terim yazilmasinin
sebebi backfill: olculdu ki alt kategorisi bos 1.564 Marin kaydinin bir kismi zaten bu
12 degerin sozluksel karsiligina dusuyor.
"""
import argparse
import collections
import importlib.util
import json
import math
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)


def _arama_yukle(kok=None):
    """arama.py'yi MODUL olarak yukle — izinli kume + normalizasyon TEK KAYNAK."""
    yol = os.path.join(kok or KOK, "tools", "arama.py")
    spec = importlib.util.spec_from_file_location("pruvo_arama_sinifla", yol)
    m = importlib.util.module_from_spec(spec)
    sys.modules["pruvo_arama_sinifla"] = m
    spec.loader.exec_module(m)
    return m


arama = _arama_yukle()

# ── ESIKLER (sayilar mimar kararidir; degistirmek DAGILIMI degistirir) ────────────────
ESIK_KATEGORI_URUN = 100      # kategori alt kategori almak icin bu kadar urun tasimali
ESIK_GRUP_URUN = 15           # grup kumeye girmek icin bu kadar urun tasimali
# 2. GECIS ESIGI (bit). SECIM GEREKCESI --esik-tarama ile OLCULDU; deger degistiginde
# dagilim degisir (kabul testi bunu ayri bir iddiayla olcer).
ESIK_YAKINLIK = 6.0
# 2. gecis sozluguna giren jetonun EN AZ bu kadar urunde gecmesi gerekir (nadir jeton
# gurultusu, tek urunluk kelimeler puani savurur).
YAKINLIK_ASGARI_DF = 3
# 🔴 KORUMA ESIGI (RAPOR ISARETI — KAPIYI KIRMIZI YAKMAZ). Bir grubun urunlerinin bu
# orandan FAZLASI (>=) 2./3. gecisten geliyorsa o grup "coplук riski" diye ISARETLENIR.
# %50 idi ve 0 grup isaretliyordu — yani olcut FIILEN oluydu (olculdu 2 Agu 2. tur).
# %20'de 4 grup isaretlenir; sayi rapordan okunur. BLOKLAYICI OLMAMASI KASITLIDIR: bu
# depoda olculdu ki bloklayici olan sey IHLAL olmali, veri DAGILIMI degil — dagilimi
# bloklayici tutmak "MaCiT urun ekleyince yayin durur" demektir.
ESIK_COPLUK_ORANI = 0.20
# Laplace yumusatma — sifir frekansli jeton sonsuz negatif puan uretmesin.
YAKINLIK_YUMUSATMA = 0.5

# ── SINIFLAR ─────────────────────────────────────────────────────────────────────────
BELIRGIN = "BELIRGIN"    # kumede, oncelikte ONDE
MIRAS = "MIRAS"          # Marin'in mevcut 12 degeri — kumede, esikten MUAF (K3)
ARTIK = "ARTIK"          # kumede ama oncelikte EN SONDA (artik kova)
ELENEN = "ELENEN"        # <15 urun — kumeye GIRMEZ, gerekcesiyle kayitli
SEKIL_RED = "SEKIL_RED"  # K1 ihlali (bicim/baglanti adi) — kumeye GIRMEZ

# ── ADAY TABLOSU — (ad, sinif, terimler, gerekce) ─────────────────────────────────────
# SIRA = ONCELIK: yukaridaki grup once kazanir. ARTIK sinifi listede nerede olursa olsun
# EN SONA gider (bkz. _sira: kural TEK YERDE).
# Terimler `arama.nrm` normalizasyonunda ve TAM JETON eslesir; Turkce ek/yumusama
# varyantlari ACIKCA yazilir ("kapak" ile "kapagi" ayri jetonlardir).
ADAYLAR = collections.OrderedDict([
    # ══ OTOMOBIL — 12.481 urun. 16 grup mimar karari K2; terimler ve siralama olcum
    # raporundan (otomobil-eksen-kiyas) AYNEN alindi, sayilar oradan dogrulanabilir.
    ("Otomobil", (
        # ── K5: TIP YERI YENER ─────────────────────────────────────────────────────────
        # OLCULDU (2 Agu, 2. tur): `bardaklik` 623 urun 12 GRUBA dagilmisti, en buyuk grup
        # yalnizca %38,2 (Ic Aksam 238 · Konsol ve Torpido 228 · Multimedya 105). Sebep
        # SIRAYDI: `konsol` bir YER adi ve tabloda ONDEYDI, `bardaklik` bir TIP adi ve
        # ARTIK kovasindaydi (kova daima en sonda) — "konsol bardakligi" basligi once
        # `konsol`a carpiyordu. Musteriye gorunen gruplama BOYLE sessizce dagiliyordu:
        # hicbir kapi kirmizi yanmiyordu cunku her atama TEK BASINA gecerliydi.
        # Kural: parcanin TIPINI adlandiran grup, BULUNDUGU YERI adlandiran gruptan
        # ONCE gelir. Ic Aksam da ayni sebeple ARTIK'tan BELIRGIN'e alindi (icindeki
        # kulluk/saklama/bozuk para/paspas terimleri TIP adlaridir, artik degil).
        ("Bardaklık", BELIRGIN, ("bardaklik",),
         "TIP — `konsol`/`torpido`/`multimedya` YER ve SISTEM adlarindan ONCE"),
        ("İç Aksam", BELIRGIN,
         ("kulluk", "paspas", "bozuk para", "saklama", "organizer",
          "cop poseti", "anahtarlik", "ic trim", "ic doseme"),
         "ic mekan aksesuari — TIP ekseni (2 Agu 2. tur: ARTIK -> BELIRGIN)"),
        # ── K7: `Multimedya ve Elektronik` IKIYE BOLUNDU ───────────────────────────────
        # OLCULDU: tek grup 1.725 urundu ve IKI AYRI MERKEZI vardi — telefon/sarj/usb/
        # magsafe ekseni 994 urun, ses/multimedya ekseni 731 urun. Terimler UYDURULMADI:
        # eski grubun 15 terimi ikiye BOLUNDU, hicbir yeni terim eklenmedi.
        # Telefon ekseni Klima'dan ONCE: olculdu ki `telefon`un 147 urunu "menfeze takilan"
        # yuzunden `Klima ve Havalandırma`ya dusuyordu.
        ("Telefon ve Şarj", BELIRGIN, ("telefon", "magsafe", "usb", "sarj"),
         "olculdu: 994 urun (telefon 699 · sarj 307 · usb 147 · magsafe 52)"),
        ("Ses ve Multimedya", BELIRGIN,
         ("hoparlor", "radyo", "teyp", "stereo", "multimedya", "kamera", "mikrofon",
          "tablet", "gps", "navigasyon", "elektronik"),
         "olculdu: 731 urun (hoparlor 245 · radyo 182 · multimedya 120 · kamera 72 · "
         "teyp 72) — ses kumesi en buyuk yigin, ad OLCUMDEN turedi"),
        ("Tekerlek ve Jant", BELIRGIN,
         ("jant", "bijon", "tekerlek", "lastik", "jant gobegi", "gobek kapagi"), ""),
        ("Yakıt ve Egzoz", BELIRGIN,
         ("yakit", "benzin", "depo kapagi", "egzoz", "egzost", "susturucu"), ""),
        ("Motor Bölümü", BELIRGIN,
         ("motor", "radyator", "karburator", "enjektor", "hava filtresi", "yag filtresi",
          "eksantrik", "supap", "aku", "alternator"), ""),
        ("Aydınlatma", BELIRGIN,
         ("far", "fari", "lamba", "lambasi", "stop", "aydinlatma", "reflektor"), ""),
        ("Klima ve Havalandırma", BELIRGIN,
         ("klima", "kalorifer", "havalandirma", "menfez", "hava kanali", "isitici",
          "polen filtresi"), ""),
        ("Koltuk ve Kemer", BELIRGIN,
         ("koltuk", "emniyet kemeri", "kemer tokasi", "kemer kilidi", "bas dayama"), ""),
        ("Ayna ve Silecek", BELIRGIN, ("ayna", "dikiz", "silecek", "yagmur sensoru"), ""),
        ("Sürüş Kumandaları", BELIRGIN,
         ("vites", "direksiyon", "pedal", "debriyaj", "el freni", "fren kolu",
          "gaz pedali"), ""),
        ("Bagaj ve Taşıma", BELIRGIN,
         ("bagaj", "pandizot", "portbagaj", "tavan bari", "tavan rafi", "ceki demiri",
          "romork"), ""),
        ("Kapı ve Cam", BELIRGIN, ("kapi", "cam", "pencere"), ""),
        ("Konsol ve Torpido", BELIRGIN,
         ("konsol", "torpido", "gosterge paneli", "kadran", "kolcak", "kol dayama"), ""),
        ("Tavan ve Güneşlik", BELIRGIN,
         ("tavan", "sunroof", "gunes tavan", "guneslik", "gunes siperi", "t-top",
          "targa"), ""),
        ("Dış Aksam", BELIRGIN,
         ("tampon", "camurluk", "marspiyel", "izgara", "panjur", "kaput", "plaka",
          "anten"), ""),
        # ── K6: ARTIK KOVA DURUST ADLANDIRILDI ─────────────────────────────────────────
        # 🔴 ARTIK KOVA — oncelikte EN SONDA (kural _sira()'da, TEK yerde).
        # Eski ad `Montaj ve Bağlantı` idi. OLCULDU: 1.840 urunun 737'si (%40,1) tablodaki
        # HICBIR terime uymuyor (2./3. gecisle geliyor) ve "baglanti" tarafina tabloda TEK
        # BIR terim dusmuyor — ad, tasidigi icerigi tarif ETMIYORDU. Olculen icerik:
        # montaj 484 · kapak 219 · tutucu 167 · adaptoru 111 · klips 95 · tapa 51 ·
        # braket 37. Yeni ad bu icerigi adlandiriyor. GRUP BOLUNMEDI: olculdu, icinde
        # ayri bir yer/sistem merkezi YOK (bolunecek tip cikmadi).
        ("Montaj Parçaları ve Klipsler", ARTIK,
         ("klips", "mandal", "tutucu", "braket", "montaj", "aparat", "adaptoru",
          "cerceve", "pim", "burc", "mentese", "kanca", "tapa", "kapak", "dugme",
          "kolu"),
         "artik kova (SON) — hicbir yer/sistem sinyali olmayan montaj/baglanti parcasi"),
    )),
    # ══ MARIN — 2.499 urun. 12 MIRAS deger (K3, bayt korunur) + K1'e uyan yeni adaylar.
    ("Marin", (
        ("Bujiler", MIRAS, ("buji", "bujisi", "bujileri"), ""),
        ("Tutyalar ve Anotlar", MIRAS,
         ("tutya", "tutyasi", "anot", "anodu", "anotlar", "anod"), ""),
        ("Pervaneler", MIRAS, ("pervane", "pervanesi", "pusher"), ""),
        ("Motor Yağları", MIRAS,
         ("yag", "yagi", "gres", "gresi", "sanziman yagi", "dislisi yagi"), ""),
        ("Boya - Bakım", MIRAS,
         ("boya", "boyasi", "astar", "vernik", "cila", "zehirli boya", "temizleyici",
          "temizleyicisi", "bakim", "polish", "wax", "dolgu", "macun"), ""),
        ("Filtreler", MIRAS, ("filtre", "filtresi", "filtreleri"), ""),
        ("Soğutma", MIRAS,
         ("sogutma", "sogutucu", "impeller", "impelleri", "termostat", "termostati",
          "su pompasi", "deniz suyu pompasi", "radyator", "esanjor"), ""),
        ("Sintine ve Ekipmanları", MIRAS,
         ("sintine", "sintinesi", "tahliye", "tahliyesi", "sassi pompa", "bilge"), ""),
        ("Yakıt Sistemi", MIRAS,
         ("yakit", "yakiti", "benzin", "depo", "deposu", "karburator", "karburatoru",
          "enjektor", "enjektoru", "yakit pompasi", "yakit hortumu"), ""),
        ("Dümen ve Kumanda", MIRAS,
         ("dumen", "dumeni", "kumanda", "kumandasi", "direksiyon", "direksiyonu",
          "gaz kolu", "kumanda teli", "kumanda kablosu", "sancak", "iskele kolu"), ""),
        ("Elektrik", MIRAS,
         ("elektrik", "kablo", "kablosu", "sigorta", "sigortasi", "role", "rolesi",
          "aku", "akusu", "sarj", "kontak", "mars", "marsi", "alternator", "solenoid",
          "sensor", "sensoru", "voltmetre", "sviç", "svic"), ""),
        ("Motor Parçaları", MIRAS,
         ("motor", "motoru", "silindir", "silindiri", "piston", "pistonu", "krank",
          "kavrama", "kavramasi", "keçe", "kece", "supap", "kayis", "kayisi",
          "kuyruk", "sanziman", "salmastra"), ""),
        # ── YENI ADAYLAR (olcum raporundan, K1 suzgecinden gecmis) ──
        ("Olta Ekipmanları", BELIRGIN,
         ("olta", "oltasi", "balik", "baligi", "balikci", "trolling", "kamis",
          "kamisi", "makara", "makarasi", "zoka", "capari", "misina", "olta kamisi",
          "yem", "yemi", "kepce"),
         "kullanim alani — balikcilik"),
        ("Bağlama Ekipmanları", BELIRGIN,
         ("cleat", "cleati", "baglama", "baglamasi", "halat", "halati", "usturmaca",
          "capa", "capasi", "demir atma", "sabitleme koltugu", "bosa", "sam ipi",
          "palamar"),
         "kullanim alani — baglama/demirleme"),
        ("Kano ve Kayak", BELIRGIN,
         ("kayak", "kayaklar", "kano", "kanosu", "kurek", "kuregi", "paddle", "sup",
          "kanocu"),
         "kullanim alani — kurekli tekne (kayak/kano)"),
        ("Güverte ve Donanım", BELIRGIN,
         ("guverte", "guvertesi", "korkuluk", "reling", "ray", "rayi", "makara arabasi",
          "bimini", "tente", "tentesi", "direk", "diregi", "yelken", "yelkeni",
          "mataforo", "iskele", "merdiven", "merdiveni", "ambar", "ambar kapagi"),
         "yer — guverte ve uzeri donanim"),
        # 🔴 ARTIK KOVA — Marin. K3'te "kabul edilebilir ama artik kovasi olarak en sona".
        ("Montaj Ekipmanları", ARTIK,
         ("montaj", "montaji", "braket", "braketi", "aparat", "aparati", "adaptor",
          "adaptoru", "tutucu", "tutucusu", "klips", "klipsi", "kelepce", "kelepcesi",
          "civata", "somun", "pul", "vida", "baglanti", "baglantisi", "tapa", "tapasi",
          "kapak", "kapagi", "conta", "contasi", "hortum", "hortumu", "kutu", "kutusu"),
         "artik kova (SON) — hicbir yer/sistem sinyali olmayan baglanti/montaj parcasi"),
        # ── ELENEN / REDDEDILEN (kumeye GIRMEZ; kayit ki yeniden tartisilmasin) ──
        ("Kapaklar ve Tapalar", SEKIL_RED, ("kapak", "kapagi", "tapa", "tapasi"),
         "K1 ihlali: BICIM adi. Olcumde 107 urun tasiyordu — sayisi degil EKSENI yanlis"),
        ("Kablo ve Klipsler", SEKIL_RED, ("kablo", "kablosu", "klips", "klipsi"),
         "K1 ihlali: BICIM/baglanti adi (olcumde 93 urun)"),
        ("Contalar", SEKIL_RED, ("conta", "contasi", "keçe", "kece"),
         "K1 ihlali: BICIM adi; ayrica olcumde 57 -> tekillestirmede 13 (<15)"),
        ("Egzoz Parçaları", ELENEN, ("egzoz", "egzozu", "manifold", "manifoldu"),
         "olcumde 16 ham eslesme, tekillestirmede <15"),
        ("Motor Takozları", ELENEN, ("takoz", "takozu"), "olcumde 1 urun"),
    )),
    # ══ MOTOSIKLET — 989 urun. Otomobil ile AYNI eksen; adlar bilerek ORTAK yazilir
    # (kullanici ayni etiketi iki kategoride ayni anlamda gorur).
    ("Motosiklet", (
        # 🔴 K5 (TIP YERI YENER) MOTOSIKLETTE DE: olculdu ki `sele` 25 urun 6 GRUBA
        # dagilmisti, en buyuk grup %56 — `Çanta ve Bagaj` ("sele cantasi"),
        # `Grenaj ve Kaporta`, `Depo ve Yakıt` basligi once carpiyordu. `Sele ve Sehpa`
        # tabloda BASA alindi: sele bir TIP, otekiler yer/sistem.
        ("Sele ve Sehpa", BELIRGIN,
         ("sele", "selesi", "sehpa", "sehpasi", "ayaklik", "ayakligi", "basamak",
          "yan sehpa", "orta sehpa", "koltuk"),
         "TIP — `canta`/`grenaj`/`depo` yer-sistem adlarindan ONCE"),
        ("Aydınlatma", BELIRGIN,
         ("far", "fari", "farlar", "sinyal", "sinyali", "lamba", "lambasi", "stop",
          "stopu", "led", "aydinlatma", "reflektor", "grenaji far"), ""),
        # K7 — Otomobil ile AYNI bolme ve AYNI adlar (ortak etiket ilkesi: kullanici ayni
        # etiketi iki kategoride ayni anlamda gorur). Eski grubun 16 terimi BOLUNDU,
        # yeni terim EKLENMEDI. Olculdu: telefon ekseni 55 urun · ses ekseni 82 urun
        # (ikisi de >=15 grup esigini geciyor, K4).
        ("Telefon ve Şarj", BELIRGIN, ("telefon", "usb", "sarj"), ""),
        ("Ses ve Multimedya", BELIRGIN,
         ("navigasyon", "gps", "kamera", "zumo", "tomtom", "aksiyon kamera", "ekran",
          "ekrani", "tablet", "hoparlor", "mikrofon", "telsiz", "interkom"), ""),
        ("Gösterge ve Kokpit", BELIRGIN,
         ("gosterge", "gostergesi", "gosterge paneli", "kadran", "saat", "saati",
          "voltmetre", "kilometre", "vizor", "siperlik", "on cam"), ""),
        ("Depo ve Yakıt", BELIRGIN,
         ("depo", "deposu", "yakit", "yakiti", "benzin", "karburator", "karburatoru",
          "enjektor", "enjektoru", "yakit deposu", "trompet"), ""),
        ("Motor Bölümü", BELIRGIN,
         ("motor", "motoru", "silindir", "silindiri", "piston", "pistonu", "yag",
          "yagi", "hava filtresi", "yag filtresi", "filtre", "filtresi", "radyator",
          "sogutma", "supap", "eksantrik", "kavrama", "debriyaj"), ""),
        ("Gidon ve Kumandalar", BELIRGIN,
         ("gidon", "gidonu", "kolu", "kollari", "dugme", "dugmesi", "anahtar",
          "anahtari", "kontak", "gaz kolu", "fren kolu", "ayna", "aynasi", "klipon",
          "manyeto", "vites", "pedal", "pedali"), ""),
        ("Çanta ve Bagaj", BELIRGIN,
         ("canta", "cantasi", "bagaj", "bagaji", "top case", "yan canta",
          "tank cantasi", "sele cantasi", "kutu", "kutusu", "cakmak"), ""),
        ("Grenaj ve Kaporta", BELIRGIN,
         ("grenaj", "grenaji", "kaporta", "panel", "paneli", "camurluk", "camurlugu",
          "plaka", "plakasi", "koruma", "koruyucu", "carpma demiri", "yan kapak",
          "kuyruk"), ""),
        ("Fren ve Süspansiyon", BELIRGIN,
         ("fren", "freni", "disk", "diski", "balata", "amortisor", "amortisoru",
          "salincak", "salincagi", "catal", "catali", "suspansiyon", "rulman"), ""),
        ("Tekerlek ve Aktarma", BELIRGIN,
         ("tekerlek", "tekerlegi", "jant", "janti", "lastik", "lastigi", "zincir",
          "zinciri", "disli", "dislisi", "aks", "aksi", "kasnak", "kasnagi",
          "zincir koruma"), ""),
        ("Elektrik", BELIRGIN,
         ("elektrik", "kablo", "kablosu", "aku", "akusu", "sigorta", "sigortasi",
          "role", "rolesi", "soket", "soketi", "sensor", "sensoru", "mars", "regulator",
          "bobin", "buji", "bujisi"), ""),
        # 🔴 ARTIK KOVA — Motosiklet. Otomobil ile ayni ad ve ayni gerekce (K6).
        ("Montaj Parçaları ve Klipsler", ARTIK,
         ("montaj", "montaji", "braket", "braketi", "aparat", "aparati", "adaptor",
          "adaptoru", "tutucu", "tutucusu", "klips", "klipsi", "kelepce", "kelepcesi",
          "tapa", "tapasi", "kapak", "kapagi", "yuva", "yuvasi", "baglanti",
          "baglantisi", "civata", "somun", "pul", "vida", "cerceve", "cercevesi"),
         "artik kova (SON) — hicbir yer/sistem sinyali olmayan baglanti/montaj parcasi"),
        # ── REDDEDILEN sekil adlari (olcum raporundaki adaylar) ──
        ("Kapaklar", SEKIL_RED, ("kapak", "kapagi"),
         "K1 ihlali: BICIM adi (olcumde 51 urun)"),
        ("Montaj Braketleri", SEKIL_RED, ("braket", "braketi"),
         "K1 ihlali: BAGLANTI adi; artik kova zaten ayni urunleri aliyor"),
        ("Telefon Tutucuları", SEKIL_RED, ("telefon tutucusu", "tutucu"),
         "K1 ihlali: BICIM adi ('tutucu'); kullanim alani `Telefon ve Şarj`dir. 🔴 K7 "
         "bolmesi bu karari DEGISTIRMEZ: bare 'tutucu' terimi yeni gruba da GIRMEDI"),
    )),
    # ══ DEKORASYON — 379 urun. Eksen = KULLANIM ALANI (obje ne ise yarar).
    ("Dekorasyon", (
        ("Bitki ve Saksı", BELIRGIN,
         ("saksi", "saksisi", "bonsai", "sukulent", "kaktus", "bitki", "bitkisi",
          "ekim", "sulayan", "fide", "teraryum"), ""),
        ("Vazo ve Çiçeklik", BELIRGIN,
         ("vazo", "vazosu", "cicek", "cicekli", "ciceklik", "solifleur"), ""),
        ("Servis ve Sunum", BELIRGIN,
         ("tepsi", "tepsisi", "kase", "kasesi", "bardak altligi", "altlik", "altligi",
          "atistirmalik", "ikram", "ikramlik", "kuruyemis", "pasta", "servis",
          "sunum", "peçetelik", "pecetelik"), ""),
        ("Heykel ve Figür", BELIRGIN,
         ("heykel", "heykeli", "heykelcigi", "heykelcik", "bust", "bustu", "figur",
          "figuru", "siluet", "silueti", "biblo"), ""),
        ("Mum ve Aydınlatma", BELIRGIN,
         ("mum", "mumu", "mumluk", "samdan", "samdani", "lamba", "lambasi", "abajur",
          "tealight", "fener", "feneri"), ""),
        ("Duvar ve Raf", BELIRGIN,
         ("duvar", "duvara", "raf", "rafi", "tablo", "tablosu", "pano", "panosu",
          "cerceve", "cercevesi", "kitap destegi", "aski", "askisi"), ""),
        # 🔴 ARTIK KOVA — Dekorasyon.
        ("Dekoratif Objeler", ARTIK,
         ("dekoratif", "obje", "objesi", "sus", "susu", "minimalist", "tasarim",
          "modern", "formlu", "kutu", "kutusu", "kap", "kabi", "stand", "standi",
          "organizer", "anahtarlik", "anahtar", "bozuk para", "taki", "cuzdan",
          "piramit", "halka", "seti"),
         "artik kova (SON) — belirgin bir kullanim alani sinyali olmayan dekor objesi"),
        # ── ELENEN ──
        ("Kitap Destekleri", ELENEN, ("kitap destegi", "kitap desteği"),
         "olcumde 5 urun (<15); Duvar ve Raf altinda gezilir"),
        ("Bardak Altlıkları", ELENEN, ("bardak altligi",),
         "olcumde 10 urun (<15); Servis ve Sunum altinda gezilir"),
        ("Kutular", SEKIL_RED, ("kutu", "kutusu"),
         "K1 ihlali: BICIM adi, ustelik olcumde 14 (<15)"),
    )),
    # ══ EV — 186 urun. Eksen = ODA / KULLANIM ALANI.
    ("Ev", (
        ("Mutfak", BELIRGIN,
         ("mutfak", "mutfagi", "degirmen", "degirmeni", "tuz", "tuzluk", "biber",
          "biberlik", "karabiber", "huni", "hunisi", "dolum", "catal", "kasik",
          "yumurtalik", "sise", "sisesi", "icecek", "kavanoz", "bardak", "tabak",
          "sogutucu", "pecetelik", "peçetelik", "kesme", "bicak", "pasta"), ""),
        ("Banyo", BELIRGIN,
         ("banyo", "dis fircaligi", "dis fircasi", "fircalik", "fircaligi", "sabun",
          "sabunluk", "dus", "dusu", "havlu", "tiras", "jilet", "sunger", "sungeri",
          "macun", "macunu", "tuvalet", "lavabo", "makyaj"), ""),
        ("Duvar ve Askı", BELIRGIN,
         ("duvar", "duvara", "aski", "askisi", "kanca", "kancasi", "raf", "rafi",
          "monte", "tabela", "tabelasi", "kapi", "kapisi"), ""),
        # 🔴 ARTIK KOVA — Ev.
        ("Saklama ve Düzen", ARTIK,
         ("saklama", "duzen", "duzenleyici", "organizer", "organizeri", "kutu",
          "kutusu", "sepet", "sepeti", "stand", "standi", "kumanda", "kumandasi",
          "anahtar", "anahtarlik", "hazne", "hazneli", "bolme", "bolmeli", "kap",
          "kabi", "tepsi", "tepsisi", "seti"),
         "artik kova (SON) — belirgin bir oda/kullanim sinyali olmayan ev duzeni parcasi"),
        # ── ELENEN ──
        ("Huniler", ELENEN, ("huni", "hunisi"),
         "olcumde 11 urun (<15); Mutfak altinda gezilir"),
        ("Sepetler", SEKIL_RED, ("sepet", "sepeti"),
         "K1 ihlali: BICIM adi, ustelik olcumde 7 (<15)"),
        ("Standlar", SEKIL_RED, ("stand", "standi"),
         "K1 ihlali: BICIM adi (olcumde 46 urun) — 'stand' urunun NEREYE ait oldugunu "
         "SOYLEMEZ; kumeye alinsaydi Otomobil'de reddedilen eksen geri girerdi"),
    )),
    # ══ ELEKTRONIK — 112 urun. Eksen = CIHAZ AILESI / KULLANIM ALANI.
    ("Elektronik", (
        ("Ses ve Müzik", BELIRGIN,
         ("davul", "davulu", "piyano", "piyanosu", "klavye", "klavyesi", "hoparlor",
          "hoparloru", "mikrofon", "mikrofonu", "fader", "gitar", "gitari", "saksafon",
          "nota", "notalik", "kulaklik", "kulakligi", "amfi", "mikser", "baget",
          "bagetlik", "ligatur", "agizlik", "pedal", "pedali", "midi", "receiver"), ""),
        # `Mutfak Cihazları` AYRI aday olarak olculdu: 14 urun (<15) -> ESIK ALTI. Ayri
        # grup ACILMADI; ayni kullanim ailesindeki `Ev Aletleri` ile BIRLESTIRILDI
        # (ikisi de ev cihazi). Urunler bos kalmiyor, tek grupta gezilir.
        ("Ev ve Mutfak Cihazları", BELIRGIN,
         ("supurge", "supurgesi", "dikis", "dikis makinesi", "utu", "utusu",
          "sac kurutma", "fon", "klima", "klimasi", "basincli yikama", "yikama",
          "fan", "fani", "pervane", "pervanesi", "sogutma", "toz", "hortum",
          "hortumu", "kiyma", "blender", "mutfak robotu", "kahve", "degirmen",
          "degirmeni", "thermomix", "rende", "narenciye", "tost", "su isitici",
          "cay", "mutfak"), ""),
        # 🔴 ARTIK KOVA — Elektronik.
        ("Cihaz Parçaları", ARTIK,
         ("parca", "parcasi", "disli", "dislisi", "kaplin", "kavrama", "kavramasi",
          "motor", "motoru", "pil", "pili", "kablo", "kablosu", "dugme", "dugmesi",
          "kapak", "kapagi", "kutu", "kutusu", "adaptor", "adaptoru", "braket",
          "braketi", "tutucu", "tutucusu", "stand", "standi", "sehpa", "sehpasi",
          "montaj", "aparat", "aparati", "modul", "modulu", "ekran", "ekrani",
          "kumanda", "kumandasi", "yazici", "yazicisi", "elektrik", "elektrikli"),
         "artik kova (SON) — cihaz ailesi sinyali olmayan elektronik cihaz parcasi"),
        # ── REDDEDILEN ──
        ("Mutfak Cihazları", ELENEN,
         ("kiyma", "mutfak robotu", "kahve", "degirmen", "degirmeni", "thermomix",
          "rende", "narenciye", "tost", "su isitici"),
         "1. gecis olcumu 14 urun (<15) — ayri grup ACILMADI, `Ev ve Mutfak Cihazları` "
         "ile birlestirildi (ayni kullanim ailesi)"),
        ("Tutucular", SEKIL_RED, ("tutucu", "tutucusu"),
         "K1 ihlali: BICIM adi (olcumde 13 urun)"),
        ("Adaptörler", SEKIL_RED, ("adaptor", "adaptoru"),
         "K1 ihlali: BICIM adi (olcumde 9 urun)"),
        ("Dişliler", SEKIL_RED, ("disli", "dislisi"),
         "K1 ihlali: BICIM adi (olcumde 11 urun)"),
    )),
])

# Kumeye GIRECEK siniflar. 🔴 ONCELIK KURALI TEK YERDE: _sira().
_KUMEDE = (BELIRGIN, MIRAS, ARTIK)


def kume_adlari(kategori, adaylar=None):
    """Kategorinin KILITLENEN grup adlari (sinif BELIRGIN/MIRAS/ARTIK), oncelik sirasinda."""
    return tuple(ad for ad, _t, _x, _g in _sira(kategori, adaylar))


def _sira(kategori, adaylar=None):
    """ONCELIK SIRASI — TEK KAYNAK. Once BELIRGIN/MIRAS (tablo sirasiyla), SONRA ARTIK.

    🔴 ARTIK KOVA EN SONDA: daha belirgin bir yer/sistem grubuna dusen urun artik kovaya
    GITMEZ. Kural burada, TEK bir ifadede; baska hicbir yerde siralama yapilmaz.
    """
    t = (adaylar or ADAYLAR).get(kategori, ())
    onde = tuple(e for e in t if e[1] in (BELIRGIN, MIRAS))
    sonda = tuple(e for e in t if e[1] == ARTIK)
    return onde + sonda


def artik_kovalar(kategori, adaylar=None):
    return tuple(e[0] for e in (adaylar or ADAYLAR).get(kategori, ()) if e[1] == ARTIK)


# ── METIN NORMALIZASYONU ─────────────────────────────────────────────────────────────
# Marka/model jetonlari ELENIR. Liste ELLE YAZILMAZ: arama.UYUM_MARKA_IZINLI'den TURETILIR
# (ikiz tanim yasagi). Boylece bir marka jetonu grup adi/sozluk jetonu olarak SIZAMAZ.
_MARKA_JETONLARI = tuple(sorted((arama.nrm(x) for x in arama.UYUM_MARKA_IZINLI),
                                key=len, reverse=True))
_MARKA_RE = tuple(re.compile(r"(?<![a-z0-9])" + re.escape(m) + r"(?![a-z0-9])")
                  for m in _MARKA_JETONLARI)


def markasiz(metin):
    """`arama.nrm` normalizasyonu + kapali marka kumesinin jetonlarini SIL."""
    s = " " + arama.nrm(metin or "") + " "
    for r in _MARKA_RE:
        s = r.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def urun_metni(u):
    """1. GECIS metni: baslik + aciklama (olcum raporuyla ayni kaynak)."""
    return markasiz(" ".join([u.get("baslik") or "", u.get("aciklama") or ""]))


def baslik_jetonlari(u):
    """2. GECIS jetonlari: YALNIZ baslik. Aciklama boilerplate'i sozlugu bogar."""
    return tuple(sorted({t for t in markasiz(u.get("baslik") or "").split()
                         if len(t) >= 3 and not t.isdigit()}))


_TERIM_ONBELLEK = {}


def _terim_re(terimler):
    anahtar = tuple(terimler)
    r = _TERIM_ONBELLEK.get(anahtar)
    if r is None:
        parcalar = sorted({arama.nrm(t) for t in terimler if arama.nrm(t)},
                          key=len, reverse=True)
        r = re.compile(r"(?<![a-z0-9])(?:%s)(?![a-z0-9])"
                       % "|".join(re.escape(p) for p in parcalar))
        _TERIM_ONBELLEK[anahtar] = r
    return r


# ── 1. GECIS ─────────────────────────────────────────────────────────────────────────
def grup_bul(metin, kategori, adaylar=None):
    """1. GECIS: ilk eslesen grubun HAM adi (kanoniklestirilmemis) ya da ""."""
    for ad, _sinif, terimler, _g in _sira(kategori, adaylar):
        if terimler and _terim_re(terimler).search(metin):
            return ad
    return ""


def kanonik(kategori, ad):
    """🔴 FAIL-CLOSED: deger arama.altkategori_sebebi'nden GECMIYORSA "" doner.

    Siniflandirici KUME DISI deger URETEMEZ. Kume tek kaynaktir (arama.ALTKATEGORI_IZINLI);
    bu modulun tablosu onun ONUNE gecemez.
    """
    if not ad:
        return ""
    if arama.altkategori_sebebi(kategori, ad) is not None:
        return ""
    return arama.altkategori_metin(ad)


def siniflandir(u, adaylar=None):
    """TEK URUN, 1. GECIS + fail-closed kanonik deger. Yazmaz, dondurur."""
    kategori = u.get("kategori")
    return kanonik(kategori, grup_bul(urun_metni(u), kategori, adaylar))


# ── 2. GECIS — SOZLUK TURETME (ELLE LISTE YOK) ────────────────────────────────────────
Sozluk = collections.namedtuple("Sozluk", "grup_df grup_n genel_df genel_n")


def sozluk_turet(atamalar, jetonlar):
    """1. GECIS CIKTISINDAN sozluk TURET. atamalar[i] = grup adi ya da "" ; jetonlar[i] = ()

    Elle yazilmis TEK BIR kelime YOKTUR — sozluk tamamen 1. gecisin atadigi urunlerin
    baslik jetonlarindan cikar. 1. gecis ciktisi degisirse sozluk de degisir (kabul testi
    bunu mutantla olcer: sabit listeye cevrilirse iddia KIRMIZI yanar).
    """
    grup_df = collections.defaultdict(collections.Counter)
    grup_n = collections.Counter()
    genel_df = collections.Counter()
    genel_n = 0
    for ad, jet in zip(atamalar, jetonlar):
        if not ad:
            continue
        grup_n[ad] += 1
        genel_n += 1
        for t in jet:
            grup_df[ad][t] += 1
            genel_df[t] += 1
    return Sozluk(grup_df, grup_n, genel_df, genel_n)


def yakinlik_puani(jetonlar, ad, sozluk, haric=None):
    """LOG-ODDS puan (bit): jeton grupta genel ortalamadan ne kadar fazla geciyor.

    katki(t) = log2( P(t | grup) / P(t | tum siniflanmis urunler) )
    Yumusatma Laplace; YAKINLIK_ASGARI_DF altindaki nadir jetonlar SAYILMAZ.
    Jetonlar SIRALI gezilir -> toplama sirasi sabit -> ayni girdi ayni float.

    `haric=(ad, jetonlar)`: sozlukten O URUNU DUS. Yalniz DOGRULAMA kolunda kullanilir
    (leave-one-out): 1. gecisin atadigi bir urun, KENDI katkisi cikarilmis sozluge karsi
    puanlanir; boylece esik "kendi kendini dogrulayan" bir sayi olmaz.
    """
    n_genel = sozluk.genel_n - (1 if haric else 0)
    n_grup = sozluk.grup_n.get(ad, 0) - (1 if haric and haric[0] == ad else 0)
    if n_grup <= 0 or n_genel <= 0:
        return float("-inf")
    a = YAKINLIK_YUMUSATMA
    toplam = 0.0
    for t in jetonlar:
        df_genel = sozluk.genel_df.get(t, 0)
        df_grup = sozluk.grup_df[ad].get(t, 0)
        if haric and t in haric[1]:
            df_genel -= 1
            if haric[0] == ad:
                df_grup -= 1
        if df_genel < YAKINLIK_ASGARI_DF:
            continue
        p_grup = (df_grup + a) / (n_grup + 2 * a)
        p_genel = (df_genel + a) / (n_genel + 2 * a)
        toplam += math.log(p_grup / p_genel, 2)
    return toplam


def en_yakin(jetonlar, adlar, sozluk, haric=None):
    """En yuksek puanli (ad, puan). Esitlikte ONCELIK SIRASI kazanir (ilk gelen)."""
    eniyi, enpuan = "", None
    for g in adlar:
        p = yakinlik_puani(jetonlar, g, sozluk, haric)
        if enpuan is None or p > enpuan:
            eniyi, enpuan = g, p
    return eniyi, (float("-inf") if enpuan is None else enpuan)


# ── UC GECISLI TOPLU SINIFLANDIRMA ───────────────────────────────────────────────────
def siniflandir_toplu(urunler, kategori, esik=None, adaylar=None):
    """(deger, gecis) listesi — girdi SIRASINDA. gecis: 1/2/3, deger "" ise gecis 0.

    DETERMINISTIK: 2. gecis sozlugu tum 1. gecis ciktisindan (KUME olarak) turer, jetonlar
    sirali gezilir, esitlikte ONCELIK SIRASI kazanir -> girdi sirasi sonucu DEGISTIRMEZ.
    """
    esik = ESIK_YAKINLIK if esik is None else esik
    sira = _sira(kategori, adaylar)
    adlar = [e[0] for e in sira]
    metinler = [urun_metni(u) for u in urunler]
    jetonlar = [baslik_jetonlari(u) for u in urunler]
    ham = [grup_bul(m, kategori, adaylar) for m in metinler]
    gecisler = [1 if a else 0 for a in ham]

    sozluk = sozluk_turet(ham, jetonlar)
    for i, ad in enumerate(ham):
        if ad:
            continue
        eniyi, enpuan = en_yakin(jetonlar[i], adlar, sozluk)   # ONCELIK = esitlik bozucu
        if eniyi and enpuan >= esik:
            ham[i], gecisler[i] = eniyi, 2

    kova = artik_kovalar(kategori, adaylar)
    son_kova = kova[-1] if kova else ""
    for i, ad in enumerate(ham):
        if not ad and son_kova:
            ham[i], gecisler[i] = son_kova, 3

    sonuc = []
    for ad, g in zip(ham, gecisler):
        d = kanonik(kategori, ad)
        sonuc.append((d, g if d else 0))
    return sonuc


# ── RAPOR ────────────────────────────────────────────────────────────────────────────
def katalog_oku(kok=None):
    with open(os.path.join(kok or KOK, "urunler.json"), encoding="utf-8") as f:
        return json.load(f)


def kategori_dagilimi(katalog):
    d = collections.Counter(u.get("kategori") for u in katalog if isinstance(u, dict))
    return d


def rapor(esik=None, kok=None):
    katalog = katalog_oku(kok)
    kat_sayi = kategori_dagilimi(katalog)
    toplam_gecis = collections.Counter()
    kirmizi = []
    print("=== ALT KATEGORI SINIFLANDIRICI — GERCEK KATALOG (%d kayit)" % len(katalog))
    print("    esikler: kategori>=%d urun · grup>=%d urun · yakinlik>=%.1f bit"
          % (ESIK_KATEGORI_URUN, ESIK_GRUP_URUN, ESIK_YAKINLIK if esik is None else esik))
    print("    koruma isareti: grubun >=%%%.0f'i 2./3. gecisten geliyorsa ISARETLENIR "
          "(RAPOR — kapiyi kirmizi YAKMAZ)" % (100.0 * ESIK_COPLUK_ORANI))
    for kategori in ADAYLAR:
        urunler = [u for u in katalog
                   if isinstance(u, dict) and u.get("kategori") == kategori]
        sonuc = siniflandir_toplu(urunler, kategori, esik)
        sayim = collections.OrderedDict(
            (ad, collections.Counter()) for ad in kume_adlari(kategori))
        bos = 0
        for deger, gecis in sonuc:
            if not deger:
                bos += 1
                continue
            sayim[deger][gecis] += 1
            toplam_gecis[gecis] += 1
        print("\n── %s (%d urun · kategori esigi %s)"
              % (kategori, len(urunler),
                 "GECTI" if len(urunler) >= ESIK_KATEGORI_URUN else "KALDI"))
        for ad, c in sayim.items():
            n = sum(c.values())
            sonradan = c[2] + c[3]
            bayrak = ""
            if n and sonradan >= n * ESIK_COPLUK_ORANI:
                bayrak = "  🔴 COPLUK RISKI (%%%.1f 2./3. gecis)" % (100.0 * sonradan / n)
                kirmizi.append((kategori, ad, n, sonradan))
            print("   %-28s %5d  (1.gecis %4d · 2.gecis %4d · 3.gecis %4d)%s"
                  % (ad, n, c[1], c[2], c[3], bayrak))
        print("   %-28s %5d" % ("BOS KALAN", bos))
    t = sum(toplam_gecis.values())
    print("\n=== GECIS TOPLAMI: 1.gecis %d · 2.gecis %d · 3.gecis %d (atanan %d)"
          % (toplam_gecis[1], toplam_gecis[2], toplam_gecis[3], t))
    pay = 100.0 * toplam_gecis[3] / max(1, len(katalog))
    print("    3. gecis payi katalogun %%%.2f'si%s"
          % (pay, "  🔴 %10 ESIGI ASILDI" if pay > 10 else ""))
    print("    kategori esigini gecemeyen (alt kategori ALMAYAN) kategoriler: %s"
          % ", ".join("%s %d" % (k, n) for k, n in sorted(kat_sayi.items())
                      if k not in ADAYLAR))
    print("    🔴 COPLUK RISKI isaretli grup: %d (esik %%%.0f) — ISARET RAPORDUR, cikis "
          "kodu DEGISMEZ" % (len(kirmizi), 100.0 * ESIK_COPLUK_ORANI))
    for kategori, ad, n, sonradan in kirmizi:
        print("       %-14s %-30s %5d urun · %4d sonradan (%%%.1f)"
              % (kategori, ad, n, sonradan, 100.0 * sonradan / n))
    return 0


def esik_tarama(kok=None):
    """2. gecis esigi DUYARLILIK olcumu — esik degisince dagilim nasil kayiyor."""
    katalog = katalog_oku(kok)
    print("=== 2. GECIS ESIGI TARAMASI (bit) — atanan urun sayisi gecise gore")
    print("%-8s %10s %10s %10s" % ("esik", "1.gecis", "2.gecis", "3.gecis"))
    for esik in (0.0, 2.0, 4.0, 6.0, 8.0, 12.0, 20.0, 1e9):
        t = collections.Counter()
        for kategori in ADAYLAR:
            urunler = [u for u in katalog
                       if isinstance(u, dict) and u.get("kategori") == kategori]
            for _d, g in siniflandir_toplu(urunler, kategori, esik):
                t[g] += 1
        print("%-8s %10d %10d %10d"
              % ("YOK" if esik > 1e8 else "%.1f" % esik, t[1], t[2], t[3]))
    return 0


def esik_dogrulama(kok=None):
    """ESIGIN GEREKCESI — leave-one-out: 1. gecisin ATADIGI urunu sozlukten DUS, yakinlik
    kuralina yeniden sor. Ayni grubu buluyor mu? Esik yukseldikce atama azalir, ISABET
    artar; secilen deger bu iki egrinin kesistigi yerdir (sayiyla, sezgiyle degil).
    """
    katalog = katalog_oku(kok)
    esikler = (0.0, 2.0, 4.0, 6.0, 8.0, 12.0, 20.0)
    atanan = collections.Counter()
    isabet = collections.Counter()
    toplam = 0
    for kategori in ADAYLAR:
        urunler = [u for u in katalog
                   if isinstance(u, dict) and u.get("kategori") == kategori]
        adlar = list(kume_adlari(kategori))
        jetonlar = [baslik_jetonlari(u) for u in urunler]
        ham = [grup_bul(urun_metni(u), kategori) for u in urunler]
        sozluk = sozluk_turet(ham, jetonlar)
        for i, ad in enumerate(ham):
            if not ad:
                continue
            toplam += 1
            tahmin, puan = en_yakin(jetonlar[i], adlar, sozluk, haric=(ad, jetonlar[i]))
            for e in esikler:
                if puan >= e:
                    atanan[e] += 1
                    if tahmin == ad:
                        isabet[e] += 1
    print("=== 2. GECIS ESIGININ GEREKCESI — leave-one-out dogrulama (%d urun)" % toplam)
    print("%-6s %10s %10s %10s" % ("esik", "atanan", "isabet", "isabet%"))
    for e in esikler:
        n = atanan[e]
        print("%-6.1f %10d %10d %9.1f%%"
              % (e, n, isabet[e], 100.0 * isabet[e] / max(1, n)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapor", action="store_true", help="gercek katalogda dagilim")
    ap.add_argument("--esik-tarama", action="store_true", help="esik duyarlilik olcumu")
    ap.add_argument("--esik-dogrulama", action="store_true",
                    help="leave-one-out isabet olcumu (esik secim gerekcesi)")
    ap.add_argument("--esik", type=float, default=None)
    ap.add_argument("--kok", default=None)
    a = ap.parse_args()
    if a.esik_dogrulama:
        return esik_dogrulama(a.kok)
    if a.esik_tarama:
        return esik_tarama(a.kok)
    if a.rapor:
        return rapor(a.esik, a.kok)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
