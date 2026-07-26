#!/usr/bin/env python3
"""EGE KABILIYET-SINIRI KAPISI — ege-bilgi.md musteriden URETIM olcusu/cizimi
ISTIYOR mu, ya da URETIM/FIYAT SOZU veriyor mu?

NEDEN VAR (26 Tem, mimar hukmu):
Ege'nin canli agzi (pruvo-bot/worker/src/index.js, SISTEM_TALIMATI) katalogda
esleme CIKMAYAN dalda uc yerde sunu yasakliyor:
  :41   "Musteriden uretim icin OLCU ya da teknik detay TOPLAMA ... URETIM ya da
         FIYAT SOZU VERME"
  :52   "URETIM icin musteriye olcu ALDIRMA: kumpas/serit metreyle olcu, mm degeri
         ya da merkez-merkez mesafe ISTEME"  (ISTISNA: TESHIS icin tek net foto /
         ek aci SERBEST — olcu/cizim degil)
  :2467 katalog-bos enjeksiyonu, ayni yasak
  :57   "yaklasik su kadar tutar' DEME"  -> tahmini fiyat da yasak, yalniz "kesin" degil
ege-bilgi.md her konusmada bu talimatin YANINA enjekte edilir. Oradaki bir satir
"olcu/cizim iste" ya da "ozel uretiriz" derse, ayni prompt icinde iki zit talimat
olusur ve model rastgele birini secer — yani yasak SESSIZCE delinir.

BU HATA SINIFINI OLCEN BASKA TEST YOKTU (olculdu, 26 Tem):
  · worker/test/ege-bilgi-nobetci.mjs -> 5 ekseni var (ODEME/TESLIM/KARGO/MALZEME/
    FIYAT); kabiliyet-siniri ekseni YOK.
  · worker/test/musteri-bacagi-nobetci.mjs -> sentetik fikstur okur, GERCEK
    ege-bilgi.md'ye bakmaz.
Sonuc: tam bu sinif, merge sonrasi tum testler YESIL yanarken canliya gecebiliyordu.
26 Tem'de bir kez gecti (dal metni "foto/olcu/cizim iste" idi) — bu kapi o dersin
cikti.

NE OLCER (KAPSAM DAR — bilerek):
  (A) ISTEK: musteriden URETIM icin olcu / cizim / teknik detay isteyen EMIR
  (B) URETIM SOZU — IKI KADEME (bkz. URETIM_ACIK_RE / URETIM_GENEL_RE):
      · ACIK kip tek basina ("uretiriz", "yapabiliriz", "hallederiz")    -> yanar
      · GENEL kip ("yaparız", "veririz") + MUSTERI-ISI baglami           -> yanar
        (baglam: urun/uretim jetonu · biz/size/sizin · bunu/aynisini · TL'ye · fiyat)
      · GENEL kip, baglam YOK ("Kargo cikisini ayni gun yaparız")        -> YANMAZ
  (C) FIYAT TAAHHUDU — IKI KANATLI (bkz. TAAHHUT_GUCLU_RE / TAAHHUT_ZAYIF_RE):
      · para + GUCLU kip ("800 TL tutar", "diyebiliriz", "hesaplariz")   -> yanar
        ⚠️ "veririz/vereceğiz" GUCLU DEGILDIR (TUR 6'da cikti) -> (B)/GENEL kanadinda
           baglamla yakalanir; baglamsiz "800 TL veririz" (C)'den KACAR (asagi bak)
      · para + YAKLASIK + ZAYIF kip ("yaklasik 700 TL ... yazar/olur")   -> yanar
      · para + ZAYIF kip, tahmin jetonu YOK ("fiyat sayfada yazar")      -> YANMAZ
        (BETIMLEMEDIR; belgenin l.7/l.9/l.45'i tam bu sinifta)
      + acik "fiyat sozu ver" kaliplari
  🔴 (C) DUZ KESIN FIYAT BEYANINI KAPSAMAZ ("Bu parca 1.200 TL."). Kapsayamaz:
  belgenin MESRU icerigi fiyat/TL dolu (l.9 kargo esigi + ornek hesap), duz rakam
  yakalayan bir kural TUM SITE deploy'unu sahte-kirmizi ile durdururdu. Bu bir
  ILAN EDILMIS KOR NOKTADIR; fikstur M21 onu kalici olarak nobetler.
Uctu; dordunculeri buraya EKLEME. Kapsam buyutmek pozitif nobetciyi sessizce
oldurur (olculdu, bu repoda: [[kapi-kapsam-genisletme-tuzagi]]).

⚠️ BU KAPI `build` ISINDE KOSAR VE `deploy: needs: build` -> bir YANLIS-POZITIF
yalnizca Ege'yi degil TUM pruvo3d.com yayinini durdurur. Yeni desen eklerken
yanlis-pozitif fiksturlerini (M11-M15, M21) MUTLAKA koştur.

Kullanim:
  python3 tools/ege-kabiliyet-kapisi.py                 # repo ege-bilgi.md
  python3 tools/ege-kabiliyet-kapisi.py --dosya <yol>
  python3 tools/ege-kabiliyet-kapisi.py --ic-nobetci    # kapinin KENDI hukmunu olcer
Cikis: 0 YESIL · 1 KIRMIZI · 2 kullanim hatasi
"""

import argparse
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARSAYILAN = os.path.join(KOK, "ege-bilgi.md")

# --- jeton eksenleri -------------------------------------------------------
# OLCU/CIZIM jetonu: musteriden ISTENDIGINDE yasak olan SAYISAL/GEOMETRIK girdi.
# Dikkat: "kosul" (derece, nerede kullanilacak, UV, yuk) BU LISTEDE DEGIL —
# kosul sormak SISTEM_TALIMATI:12 ile ACIKCA SERBEST. Karistirirsan l.18/l.38
# gibi mesru satirlar sahte-kirmizi yanar.
OLCU_RE = re.compile(
    r"ölçü|ölçüler|çizim|teknik\s+resim|teknik\s+detay|teknik\s+çizim"
    # \bçap\w* -> "çap/çapı/çapını/çapında".
    # 🔴 (?!raz|a) UC homografi disarida tutar (TUR 6):
    #    "çapraz" · "ÇAPA" (= Marin kategorisinin CEKIRDEK URUNU, biz capa parcasi
    #    satiyoruz) · "çapak" (baski artigi). Olculdu: bu koruma olmadan
    #    "Çapa braketini tanımak için fotoğraf iste." KIRMIZI yaniyordu — oysa bu
    #    M4 ile ACIKCA IZIN VERILMIS teshis-fotografi davranisi. Fikstur C1-C4.
    r"|\bmm\b|\bcm\b|\bsantim|\bçap(?!raz|a)\w*|kumpas"
    r"|merkez-\s*merkez|şerit\s*metre",
    re.IGNORECASE)

# ISTEK fiili — YALNIZ musteriden girdi talep eden EMIR kipleri.
# "netleştir" BILEREK YOK: l.11 ("ölçü/koşul belirsizse önce netleştir") mesru bir
# ic reflekstir, musteriden olcu talebi degil. Bu bir KOR NOKTA, asagida ilan edilir.
# 🔴 "\bsorun\b" BILEREK YOK: emir kipi "sor-un" ile Turkcenin en sik ismi "sorun"
#    (=problem) HOMOGRAF. "Olcuyle ilgili bir sorun olursa" cumlesi TUM SITE
#    deploy'unu durduruyordu (fikstur M11). Tek kelime ugruna deploy riski alinmaz.
# 🔴 "\byaz\b|\byazın\b" TUR 4'te CIKARILDI: nesnesi SERBEST oldugu icin sahte-kirmizi
#    uretiyordu — "Ölçüde sorun yaşarsanız yazın." (=bize yaz) OLCU talebi DEGIL ama
#    KIRMIZI yaniyordu. Deploy durduran bir kapida bu kabul edilemez. Bedeli ILAN
#    EDILDI: "Ölçüleri yazın" tipi talep artik YAKALANMAZ (fikstur M25).
ISTEK_RE = re.compile(
    r"\biste\b|\bisteyin\b|\bistersin\b|\btalep\s+et\b|\btalep\s+edin\b"
    r"|\btopla\b|\btoplayın\b|\baldır\b|\bölçtür\b|\bölçün\b"
    r"|\bgönder\b|\bgönderin\b|\bgöndersin\b|\bgöndermeniz\b|\bgönderiniz\b"
    r"|\biletin\b|\bpaylaşın\b",
    re.IGNORECASE)

# URETIM SOZU — 1. cogul taahhut kipi. "üretilir/üretip/üretiyoruz/ürettiğimiz"
# BILEREK YOK: bunlar firma-kimligi/akis anlatimidir ve SISTEM_TALIMATI:2467 kimlik
# cumlesini ACIKCA serbest birakir ("ozel uretim yapan bir firmayiz, AMA ... sozunu
# SEN verme"). Yasak olan, MUSTERININ PARCASI icin verilen soz.
# 🔴 IKI KADEME (TUR 6). "yaparız / veririz" gibi JENERIK 1. cogul fiiller uretim
# DISI baglamda da dogaldir ve bu belgede yazilmasi COK olasidir:
#     "Kargo cikisini ayni gun YAPARIZ."              -> uretim sozu DEGIL
#     "2.500 TL uzerinde kargoyu ucretsiz VERIRIZ."   -> fiyat taahhudu DEGIL
# Bir kargo/teslim cumlesi yuzunden tum sitenin yayini duramaz. Bu yuzden jenerik
# fiiller URUN/URETIM BAGLAMI ister; "uretiriz" gibi TEK BASINA ACIK olanlar
# standalone kalir (daraltirken (B) sinifi delinmez).
# TUTARLILIK NOTU: belgenin gercek 1. cogullari ("kargolariz" l.14, "oturturuz" l.10)
# BILEREK listede yok — musterinin parcasi icin VERILEN SOZ degil, kendi surecimizin
# anlatimidirlar.
# 🔴 TUR 7 ONARIMI — TUR 6'nin daraltmasi ASIRI-DUZELTMEYDI, GERI ALINDI.
# Olculdu: daraltmanin onledigi yanlis-pozitifler ERISILEBILIR DEGILDI
# (yaparız/veririz/hallederiz/yapabiliriz -> canli ege-bilgi.md'de x0; kapi TUR 4-5-6'da
# canli belgede zaten 0 bulgu veriyordu). Karsiliginda 28 cumlelik gercek taahhut
# korpusunda yakalama 21 -> 4 dustu; kacanlar arasinda M2'nin (26 Tem kazasi, bu kapinin
# KURULUS SEBEBI) tek kelimelik parafrazlari vardi: "...yoksa biz de yaparız."
# ASIMETRI (mimar dersi): yanlis-pozitif GURULTULUdur, dakikalar icinde duzeltilir;
# (B)/(C) kacisi SESSIZdir ve canli musteriye TICARI BEYAN olarak gider.
# ONARIM YONTEMI: bastirici/negatif veto DEGIL (TUR 4 onu bilerek oldurdu) -> BAGLAMI
# GENISLET. Olculdu: yakalama 4 -> 17+/28, mesru korpusta yanlis-pozitif 0 (degismedi).
#
# hallederiz/hallederim TUR 7'de ACIK listeye TASINDI: "...yoksa hallederiz" tek basina
# M2 sinifi bir taahhuttur ve baglam kelimesi TASIMAZ (fikstur G9).
# ACIK = tek basina KABILIYET/TAAHHUT beyani; baglam gerekmez.
# "yapabiliriz/yaptirabiliriz" TUR 7'de buraya alindi: bunlar "bunu YAPABILIRIZ" =
# duz kabiliyet iddiasidir ve tam da :41'in yasakladigi sozdur ("Elbette yapabiliriz."
# baglam kelimesi TASIMAZ ama taahhuttur — fikstur G11).
# "hallederiz/hallederim" de ACIK: "...yoksa hallederiz" M2 sinifi taahhut (G9).
URETIM_ACIK_RE = re.compile(
    r"\büretiriz\b|\büretebiliriz\b|\büretiveririz\b|\büstleniriz\b"
    r"|\bbasarız\b|\btasarlarız\b|\bhallederiz\b|\bhallederim\b"
    r"|\byapabiliriz\b|\byaptırabiliriz\b|sıfır\s+toleransla",
    re.IGNORECASE)
# GENEL = uretim DISI baglamda da dogal olan fiiller; MUSTERI-ISI baglami ister.
# Mesru kalmasi gerekenler: "Kargo cikisini ayni gun yaparız." (G1) ·
# "2.500 TL uzerinde kargoyu ucretsiz veririz." (G2)
URETIM_GENEL_RE = re.compile(
    r"\byaparız\b|\bveririz\b|\bveririm\b|\bvereceğiz\b|\bvereceğim\b",
    re.IGNORECASE)
# BAGLAM = "bu soz MUSTERININ ISI icin mi veriliyor". Urun/uretim jetonlarina ek olarak
# 1. cogul zamir + musteri-nesnesi + "TL'ye" (fiyata is alma) jetonlari.
# ⚠️ Ciplak "TL" BILEREK YOK: "2.500 TL uzerinde kargoyu ucretsiz veririz" mesrudur.
URUN_BAGLAM_RE = re.compile(
    r"üret|imal|\bparça|baskı|\bözel\b|tasarım|kalıp"
    r"|sizin\s+için|size\s+özel|sizin\s+adınıza|sizin\s+yerinize|\bsize\b|\bsizin\b"
    r"|\bbiz\b|\bbizde\b|\baynısını\b|\byenisini\b|\bbunu\b|\bbunları\b|\bşunu\b"
    r"|TL['’]ye|\bfiyat|\bölçünüze\b|\bölçüye\b|\bölçüsüne\b|\bmodele\b",
    re.IGNORECASE)

# FIYAT SOZU — kesin VEYA yaklasik. Yaklasik/tahmini yalniz PARA jetonuna yakinsa
# sayilir (l.22'deki "yaklasik aralik" isi dayanimi icindir, fiyat degil).
# Morfoloji varyantlari: "tahmini" yazip "tahminen"i, "civarinda" yazip "civari"yi
# kacirmak OLCULDU (mimar denetimi 26 Tem) — kapi ilan ettigini yakalamiyordu.
YAKLASIK_RE = re.compile(
    r"yaklaşık|tahmini|tahminen|aşağı\s*yukarı|civar\w*|bandında|banda"
    r"|ortalama|gibi\s+düşün",
    re.IGNORECASE)
PARA_RE = re.compile(r"\bfiyat|\bTL\b|\btutar|\bücret|\bmaliyet", re.IGNORECASE)

# 🔴 POZITIF SART (TUR 4 mimar hukmu — NEGATIF VETO KALDIRILDI).
# ESKI TASARIM: (C) = YAKLASIK + PARA + not BETIMLEME.  Bu BYPASS'a acikti: bastirici
# KOSULSUZ veto veriyordu, taahhut kipiyle YARISMIYOR onu EZIYORDU. Olculdu — bir fiil
# EKLEYEREK kural susturulabiliyordu:
#     "Yaklasik 900 TL tutar ve sepette GORUNUR."   -> YESIL (oysa taahhut)
#     "Yaklasik 700 TL civari bir maliyet YAZAR."   -> YESIL
# ILKE: kelime EKLEYEREK susturulabilen kural, kural degildir.
# YENI TASARIM: (C) yanar <=> ayni cumlecikte [PARA jetonu] VE [TAAHHUT isareti].
# Betimleyici cumleler taahhut isareti TASIMADIGI icin zaten yesil kalir; bastiriciya
# gerek yok. Ayrica "gecerlidir" ESKIDEN bastiriciydi — YANLISTI, o bir TAAHHUTTUR
# ("bu fiyat sizin parcaniz icin gecerlidir" baglayicidir) ve artik TAAHHUT tarafinda.
# NOT: YAKLASIK sarti KALKTI — "1.250,50 TL olur" cumlesinde tahmin jetonu yok ama
# taahhut var; eski tasarim bunu goremezdi.
# 🔴 TAAHHUT IKI KANATLIDIR (TUR 5 duzeltmesi). TUR 4'te tek listeydi ve
# `olur/olacak/gecerlidir/yazar/cikar` oraya konmustu — ROL TERSINE DONMUSTU: bunlar
# TUR 3'te BETIMLEME bastiricisiydi. PARA_RE ONEK esleseni oldugu icin
# (ucretsiz/ucreti/fiyati/tutari/maliyeti hepsi para sayilir) sonuc: para + "olur"
# iceren HER cumlecik kirmizi. OLCULDU: 17 mesru betimleyici cumlenin 15'i KIRMIZI,
# belgenin KENDI l.9/l.7/l.45 varyantlari DAHIL. `deploy: needs: build` -> bu
# satirlardan biri yazilirsa TUM pruvo3d.com yayini durardi.
#
# GUCLU  = tek basina taahhut kurar; PARA jetonuyla yanar.
# ZAYIF  = tek basina BETIMLEME de olabilir ("fiyat sayfada yazar"); yalnizca
#          YAKLASIK/tahmin jetonuyla BIRLIKTE taahhut sayilir
#          ("yaklasik 700 TL civari bir maliyet yazar").
# Boylece hem betimleme yesil kalir hem TUR 3'un yakaladigi tahmin ekseni geri gelir.
TAAHHUT_GUCLU_RE = re.compile(
    r"(?:TL|lira)\s*['’]?\s*tutar"          # "800 TL tutar" (fiil); "yaklasik tutar" (isim) DEGIL
    r"|\btutuyor\b"
    r"|\bderiz\b|\bdiyebiliriz\b|\bsöyleriz\b|\bsöyleyebiliriz\b"
    # veririz/vereceğiz/yaparız ailesi TUR 6'da BURADAN CIKTI -> URETIM_GENEL_RE
    # (jenerik; "kargoyu ucretsiz veririz" fiyat taahhudu DEGIL, baglam ister).
    r"|\bhesaplarız\b|\bhesaplarım\b",
    re.IGNORECASE)

# ⚠️ Bu listeye BETIMLEYICI edilgenler (gorunur/eklenir/gosterilir/listelenir) ASLA
# girmez: M12/M13 tam da YAKLASIK + PARA tasir, oraya konursa sahte-kirmizi yanar.
TAAHHUT_ZAYIF_RE = re.compile(
    r"\bolur\b|\bolacak\b|\bolacaktır\b|\bgeçerlidir\b|\byazar\b|\bçıkar\b"
    r"|\bhesaplar\b|\bbulur\b|\bkalır\b|\bseyreder\b"
    r"|\bseviyesinde\w*|\bbandında\w*|\bcivarında\w*",
    re.IGNORECASE)

# --- (A) "sorun" HOMOGRAFI: emir "sor-un" vs isim "sorun" (=problem) --------
# TUR 3'te jetonu tumden atmistim; TUR 4 olctu ki ikilem GERCEK DEGIL — ucuz bir
# ayirt edici isim baglamlarini disliyor ve kapinin KURULUS SEBEBI olan
# "Musteriye olculeri sorun." vakasini geri kazandiriyor.
SORUN_EMIR_RE = re.compile(r"\bsorun\b|\bsorunuz\b", re.IGNORECASE)
SORUN_ISIM_RE = re.compile(
    r"\bbir\s+sorun\b|\bsorun\s+(?:olursa|olur|varsa|var|yok|çıkar|çıkarsa|yaşa\w*)"
    r"|\bsorunu\b|\bsorunsuz\b|\bsorunla\b|\bsorunlar\w*|\bsorunlu\b",
    re.IGNORECASE)
FIYAT_SOZ_RE = re.compile(
    r"kesin\s+fiyat\s+(ver|söyle|yaz)\b|fiyat\s+(sözü|garantisi)\s+ver\b"
    r"|\bşu\s+kadar\s+tutar\b",
    re.IGNORECASE)

# OLUMSUZLAMA — Turkce -ma/-me emir olumsuzu + yasak isaretleri.
# Cumlecik (clause) duzeyinde bakilir. SATIR duzeyinde bakmak OLUMCUL: 26 Tem'in
# hatali satiri hem "iste" hem "verme" iceriyordu; satir duzeyi olumsuzlama
# "verme"yi gorup "iste"yi MASKELER ve kapi sahte-yesil yanardi (olculdu: fikstur M1).
OLUMSUZ_RE = re.compile(
    r"\bisteme\b|\btoplama\b|\baldırma\b|\bverme\b|\betme\b|\bgeçirme\b|\bsorma\b"
    r"|\bdeme\b|\bsunma\b|\buydurma\b|\bASLA\b|\bYASAK\b|\bDEĞİL\b|\bYOK\b"
    r"|\bkapsam\s+dışı\b|\bmez\b|\bmaz\b",
    re.IGNORECASE)

# Cumlecik ayirici: noktalama + BAGLAC.
# 🔴 Baglaclar (cunku/ama/fakat/ancak/zira) 26 Tem denetiminde eklendi: olumsuzlama
# maskesi bypass'i OLCULDU -> "Olcuyu gonderin CUNKU tahmin yeterli DEGIL" tek
# cumlecik sayiliyor, sondaki "degil" bastaki zararli EMRI susturuyordu (M16).
# Baglac sinirinda bolununce emir kendi cumleciginde degerlendirilir.
# 🔴 RAKAM KORUMASI (TUR 4): duz `[.;,]` TURKCE BINLIK AYRACINI da boluyordu ->
# "Yaklasik 1.500 TL tutar." -> ['- Yaklasik 1', '500 TL tutar'] -> tahmin jetonu ile
# para jetonu AYRI cumleciklere dusuyor, (C) HIC yanmiyordu. Yani (C) sinifi 1.000 TL
# ustunde TAMAMEN OLUYDU — ve gercek ticari buyuklugumuz (ozel uretim) tam orada.
# Turkce ONDALIK ayraci VIRGUL oldugu icin ("1.250,50 TL") koruma virgule de uygulanir.
# Kural: [.;,] iki RAKAM ARASINDAYSA bolme.
_AYIRAC = r"(?:(?<!\d)[.;,]|[.;,](?!\d))"
_BAGLAC = r"\bçünkü\b|\bama\b|\bfakat\b|\bancak\b|\bzira\b"
CUMLECIK_AYIRICI = re.compile(_AYIRAC + r"|\n|" + _BAGLAC, re.IGNORECASE)

# CUMLE ayirici — VIRGUL ICERMEZ. (A) sinifi bu GENIS pencerede olculur: Turkcede
# devrik/virgullu tumce dogaldir ve virgul, olcu jetonuyla emri AYIRIYORDU (TUR 4):
#   "Deliğin çapını, bize gönderin."  · "Teknik çizimi, mümkünse paylaşın."
# ⚠️ OLUMSUZLAMA yine CUMLECIK duzeyinde kalir — cumle duzeyine tasinirsa M9
# ("ölçü isteme, çizim toplama") gibi YASAK metinleri sahte-kirmizi yanar.
CUMLE_AYIRICI = re.compile(
    r"(?:(?<!\d)[.;]|[.;](?!\d))|\n|" + _BAGLAC, re.IGNORECASE)


def cumlecikler(satir):
    """Satiri cumleciklere boler (virgul DAHIL). Olumsuzlama BU pencerede aranir."""
    return [p.strip() for p in CUMLECIK_AYIRICI.split(satir) if p and p.strip()]


def cumleler(satir):
    """Satiri cumlelere boler (virgul HARIC). (A) jeton penceresi budur."""
    return [p.strip() for p in CUMLE_AYIRICI.split(satir) if p and p.strip()]


def istek_var(c):
    """Cumlecikte musteriden girdi TALEP EDEN emir var mi?
    'sorun' yalniz ISIM baglami YOKKEN emir sayilir (homograf ayirt edicisi)."""
    if ISTEK_RE.search(c):
        return True
    if SORUN_EMIR_RE.search(c) and not SORUN_ISIM_RE.search(c):
        return True
    return False


def olumsuz(c):
    return bool(OLUMSUZ_RE.search(c))


def bulgular(metin):
    """(satir_no, sinif, cumlecik, gerekce) listesi dondurur."""
    out = []
    satirlar = metin.split("\n")
    i = 0
    while i < len(satirlar):
        satir = satirlar[i]
        no = i + 1

        # ---- (A) ISTEK: jeton penceresi CUMLE, olumsuzlama penceresi CUMLECIK ----
        # Iki ayri pencere sart: cumle olmadan virgullu devrik tumce kacar (TUR 4),
        # cumlecik olmadan yasak metinleri sahte-kirmizi yanar (M9).
        for cumle in cumleler(satir):
            if not OLCU_RE.search(cumle):
                continue
            for c in cumlecikler(cumle):
                if istek_var(c) and not olumsuz(c):
                    out.append((no, "A/ISTEK", cumle,
                                "musteriden URETIM olcusu/cizimi isteniyor "
                                "(SISTEM_TALIMATI :41/:52/:2467 YASAKLIYOR)"))
                    break

        # ---- (B) ve (C): CUMLECIK duzeyi ----
        for c in cumlecikler(satir):
            if olumsuz(c):
                continue
            # (B) IKI KADEME: acik uretim fiili tek basina; jenerik fiil URUN baglami ister.
            if URETIM_ACIK_RE.search(c) or (URETIM_GENEL_RE.search(c)
                                            and URUN_BAGLAM_RE.search(c)):
                out.append((no, "B/URETIM-SOZU", c,
                            "musterinin parcasi icin uretim taahhudu "
                            "(uretecegimize Okan karar verir — :41/:2467)"))
            # POZITIF SART (negatif veto YOK), IKI KANATLI:
            #   para + GUCLU taahhut            -> yanar
            #   para + YAKLASIK + ZAYIF taahhut -> yanar
            # ZAYIF tek basina yanmaz: "fiyat sayfada yazar" BETIMLEMEDIR.
            para = PARA_RE.search(c)
            guclu = para and TAAHHUT_GUCLU_RE.search(c)
            zayif = (para and YAKLASIK_RE.search(c) and TAAHHUT_ZAYIF_RE.search(c))
            if FIYAT_SOZ_RE.search(c) or guclu or zayif:
                out.append((no, "C/FIYAT-SOZU", c,
                            "fiyat TAAHHUDU (para + %s taahhut kipi) "
                            "(:57 'yaklasik su kadar tutar' DEME)"
                            % ("GUCLU" if guclu else "YAKLASIK+ZAYIF")))
        i += 1
    return out


def olcumu_bas(yol, metin, sessiz=False):
    b = bulgular(metin)
    if not sessiz:
        print("EGE KABILIYET-SINIRI KAPISI")
        print("  Dosya : %s" % yol)
        print("  Olcum : %d satir, %d karakter" % (len(metin.split("\n")), len(metin)))
        print("  Kapsam: (A) olcu/cizim ISTEGI · (B) uretim sozu · (C) fiyat TAAHHUDU")
        print("          (C) = para + GUCLU kip, ya da para + YAKLASIK + ZAYIF kip.")
        print("          (C) OLCMEZ: duz kesin fiyat beyani · tahmin jetonu tasimayan")
        print("          betimleme ('fiyat sayfada yazar') — ilan edilmis kor noktalar.")
        print("-" * 70)
        if not b:
            print("  Bulgu YOK.")
        k = 0
        while k < len(b):
            no, sinif, c, gerekce = b[k]
            print("  KIRMIZI [%s] satir %d" % (sinif, no))
            print("     cumlecik: %s" % c[:180])
            print("     gerekce : %s" % gerekce)
            k += 1
        print("-" * 70)
    return b


def ne_olculmedi():
    # r""" ZORUNLU: govde `\bçap`, `\w*` gibi ham regex parcalari iceriyor; ham
    # olmayan dizgide bunlar SyntaxWarning uretir ve `-W error::SyntaxWarning`
    # altinda IMPORT'U KIRAR (TUR 6'da CI stderr'ine basiyordu).
    print(r"""
NE OLCULMEDI (durust liste — bu bir KELIME kapisidir, ANLAM onaylamaz):
  · 🔴 PARAFRAZ KACISI GENISTIR — bu maddeyi kucumseme. Bu kapi PROSE ONAYI VERMEZ.
    Yesil = "aranan uc kalibin SOZDIZIMI bulunamadi" demektir; "metin dogru" demek
    DEGILDIR. OLCULDU (curutucu, 26 Tem): 30 bypass varyantinin 25'i KACTI. Kacan
    ornekler: fiyat icin "gelir / duser / ongoruyoruz"; uretim icin "basabiliriz /
    hallederim"; olcu talebi icin SORU kipi "Deliğin çapı kaç mm?". Yani ayni anlami
    baska kelimelerle yazan bir metin bu kapidan RAHATCA gecer. Bu bir KUSUR DEGIL,
    kelime kapisinin DOGASIDIR — ama kapiyi "metni dogruladi" diye okuma. Ayrica bu
    repoda olculdu: anlami tersine ceviren 25 mutasyonun 22'si kelime arayan testten
    YESIL gecti.
  · KOR NOKTA — "çapa/çapak" homografi: OLCU deseni `\bçap(?!raz|a)\w*` ile
    "çapa" (MARIN kategorisinin cekirdek urunu — biz capa parcasi satiyoruz),
    "çapak" (baski artigi) ve "çapraz" DISARIDA tutulur. Bedeli: "çapa" ile
    BASLAYAN gercek bir olcu kelimesi olsaydi kacardi. Fiksturler C1-C5.
  · KOR NOKTA — GENEL fiiller ("yaparız/veririz/vereceğiz") yalniz MUSTERI-ISI
    baglami varken (B) sayilir (baglam: urun/uretim jetonu · biz/size/sizin ·
    bunu/aynisini/yenisini · TL'ye · fiyat). ACIK fiiller (uretiriz/yapabiliriz/
    hallederiz/basariz/tasarlariz/ustleniriz) baglam ISTEMEZ.
    OLCULEN BEDEL — su siniflar KACAR (26 Tem, onarim SONRASI olculdu):
      · "800 TL veririz." · "1.500 TL vereceğiz."  -> baglamsiz GENEL fiil + para.
        (C) bunlari GORMEZ cunku "veririz/vereceğiz" TUR 6'da GUCLU listeden cikti;
        (B) de gormez cunku baglam jetonu yok. ILAN EDILMIS BOSLUK.
      · "Kargo cikisini ayni gun yaparız." -> KASITLI: bu MESRU bir cumle, yanmamali.
    TUR 6 dersi: bu baglam sarti bir donem `yapabiliriz/hallederiz`e de uygulanmisti
    ve 28 cumlelik taahhut korpusunda yakalama 27 -> 10'a dusmustu (M2'nin, yani
    kapinin KURULUS VAKASININ parafrazlari dahil). TUR 7'de geri alindi: cozum
    BASTIRICI degil BAGLAM GENISLETME + acik fiilleri standalone birakma. G1-G13.
  · 🔴 DUZ KESIN FIYAT BEYANI OLCULMEZ. "Bu parca 1.200 TL." · "Fiyat 900-1100 TL."
    gibi RAKAMLI DUZ beyanlar bu kapidan YESIL gecer. Kapsanamaz: belgenin MESRU
    icerigi fiyat/TL dolu (l.9 kargo esigi + ornek hesap), duz rakam yakalayan bir
    kural TUM SITE deploy'unu sahte-kirmizi ile durdururdu. (C) yalnizca YAKLASIK/
    TAHMIN kalibini + acik "fiyat sozu ver" kaliplarini olcer. Fikstur M21 bunu
    KALICI olarak nobetler — "duzeltmeye" calisan l.9'u kirar.
  · 🔴 OLUMSUZLAMA MASKESI TAMAMEN KAPANMADI. Zararli emirle olumsuzlama AYNI
    cumlecikte kalirsa emir susturulur. Baglac sinirlari (cunku/ama/fakat/ancak/
    zira) 26 Tem'de ayirici yapildi (M16), AMA noktalama ya da baglac ICERMEYEN
    tek cumlecikte olumsuzlama HALA maskeler — or. "Olcuyu gonderin tahmin yeterli
    degil". Belgenin uslubu DEGIL/YOK/ASLA vurgusuyla dolu oldugu icin bu GERCEK
    bir risktir; prose degisikliginde INSAN okumasi sart.
  · JETON PENCERELERI FARKLI (bilerek): (A) CUMLE duzeyinde jeton arar (virgullu
    devrik tumce icin), olumsuzlamayi CUMLECIK duzeyinde kontrol eder. (B)/(C)
    tumuyle cumlecik duzeyindedir. Cok cumlecikli uzun bir satirda (A)'nin olcu
    jetonu ile emri FARKLI cumlelerdeyse yakalanmaz.
  · KOR NOKTA — "netleştir": l.11 "ölçü/koşul belirsizse netleştir" ISTEK
    fiili saymaz (mesru ic refleks kabul edildi). Biri olcu talebini "netleştir"
    diye yazarsa bu kapi GORMEZ. Bilincli sinir; genisletmek l.11/l.18/l.38'i
    sahte-kirmizi yakar.
  · KOR NOKTA — "yaz/yazın": ISTEK deseninden CIKARILDI (TUR 4). Nesnesi SERBEST
    oldugu icin sahte-kirmizi uretiyordu ("Ölçüde sorun yaşarsanız yazın" = bize
    yaz, olcu talebi DEGIL). Bedeli: "Ölçüleri yazın" tipi GERCEK bir talep artik
    YAKALANMAZ. Fikstur M25 bu bedeli kalici olarak gorunur tutar.
  · KOR NOKTA — "sorun" ayirt edicisi BIR BASTIRICIDIR: isim baglami
    ("bir sorun / sorun olursa / sorun yaşarsanız / sorunsuz") gorununce "sorun"
    emir SAYILMAZ. Yani "Ölçüyü sorun, sorun olursa yazın" gibi bir cumlede
    bastirici zararli emri de susturur. Dar tutuldu (yalniz bu homograf), ama
    BYPASS EDILEBILIR — bilerek kabul edildi, alternatifi tum siteyi durduran
    sahte-kirmiziydi.
  · 🔴 (C) ZAYIF KANAT TAHMIN JETONUNA BAGLIDIR. "Fiyat sayfada yazar" · "Kargo
    bedeli 250 TL olur" · "Sitede yazan fiyat gecerlidir" YESIL gecer — bunlar
    BETIMLEMEDIR ve belgenin kendi l.7/l.9/l.45'i tam bu sinifta. Bedeli: tahmin
    jetonu TASIMAYAN bir fiyat taahhudu ("Bu is 2.000 TL olur" gibi) YAKALANMAZ.
    Bilincli takas — alternatifi olculdu: ZAYIF kipleri kosulsuz yakan surum
    17 mesru cumlenin 15'ini KIRMIZI yakiyordu ve TUM SITE yayinini durdururdu.
    Fiksturler Z1-Z6 bu sinirin YESIL tarafini, Z7-Z12 KIRMIZI tarafini nobetler.
  · 🔴 (C) BETIMLEYICI EDILGEN CUMLEYI AYIRT EDEMEZ. Olculdu (TUR 4):
    "Kargo ucreti yaklasik 250 TL olarak sepete eklenir." (MESRU, yesil kalmali) ile
    "Fiyat yaklasik 800 TL olarak eklenir." (tahmini fiyat beyani) DILBILGISEL
    OLARAK AYNIDIR — ikisi de edilgen betimleme; yalnizca OZNE farkli. Kelime
    duzeyinde bir kapi bunlari ayiramaz; ozneye ("kargo" mu "fiyat" mi) gore kural
    yazmak kirilgan asiri-uydurma olurdu. Ikisi de YESIL gecer. Bu sinif INSAN
    okumasi ister.
  · KAPSAM DISI — ege-bilgi.md l.14 ("siparis sonrasi size ozel uretilir"):
    KOSULSUZ uretim taahhudu olarak mimar tarafindan AYRI bir acik madde olarak
    alindi (26 Tem). Pasif "üretilir" bilerek desende YOK — SISTEM_TALIMATI:2467
    firma-kimligi cumlesini serbest birakir. Bu kapi o maddeyi COZMEZ.
  · Yalniz ege-bilgi.md okunur. SISTEM_TALIMATI'nin kendisi, deploy edilmis worker,
    site sayfalari ve Ege'nin bu metni gercekten UYGULADIGI OLCULMEZ.
  · Olumsuzlama Turkce -ma/-me + yasak jetonu listesidir; listede olmayan
    olumsuzlama sekli (ornegin "istemekten kacin") sahte-KIRMIZI yakar.""")


# --------------------------------------------------------------------------
# IC NOBETCI — kapinin KENDI hukmunu fiksturlerle olcer (kirmizi-mutasyon sarti).
# Bu repoda bir kapi ancak boyle kabul edilir: yesil yanabildigi kadar KIRMIZI da
# yanabildigi GOSTERILMELIDIR.
# --------------------------------------------------------------------------
ESKI_DAL_SATIR = ("- *Yapabilir misiniz?* → Önce parçayı tanı; katalogda benzeri varsa "
                  "oradan git. Yoksa foto/ölçü/çizim iste, araştırıp döneceğini söyle "
                  "+ [DEVRET]; özel üretim ya da kesin fiyat sözü verme.")
MAIN_SATIR = ("- *Yapabilir misiniz?* → Foto/ölçü/çizim varsa kolaylaşır; katalogda "
              "benzeri varsa oradan git, yoksa özel üretiriz.")
YENI_SATIR = ("- *Yapabilir misiniz?* → Parçayı tanı; katalogdakine yönlendir, yoksa "
              "araştırıp döneceğini söyle + [DEVRET]. Ölçü/çizim isteme, "
              "üretim/fiyat sözü verme.")

# Belgenin KENDI mesru satirlari — canli metnin (C)/(A) sinifina en yakin cumleleri.
BELGE_L9 = ('- **Kargo — NET söyle, "siparişte netleşir" DEME:** 2.500 TL ve üzeri '
            'ücretsiz; altında gönderi başına **250 TL** toplama eklenir '
            '(ör. 1.500 TL + 250 TL kargo = 1.750 TL).')
BELGE_L11 = ("- **Doğru parça:** ölçü/koşul belirsizse netleştir, belirsizken "
             "sepete/siparişe geçirme.")

FIKSTURLER = [
    # (ad, metin, KIRMIZI_bekleniyor_mu, aciklama)
    # ═══ DOGRU-POZITIF (yakalama) ═══
    ("M1 eski dal metni (26 Tem kazasi)", ESKI_DAL_SATIR, True,
     "'olcu/cizim iste' EMRI — ayni satirda 'verme' olmasina ragmen yakalanmali "
     "(satir duzeyi olumsuzlama maskeleme testi)"),
    ("M2 main eski l.43", MAIN_SATIR, True, "'yoksa ozel uretiriz' = uretim taahhudu"),
    ("M6 mm degeri isteme",
     "- Deliğin çapını mm olarak gönderin, ona göre üretelim.", True,
     "'mm ... gonderin' = olcu talebi"),
    ("M7 yaklasik fiyat", "- Yaklaşık 800 TL tutar, ona göre planlayın.", True,
     ":57 'yaklasik su kadar tutar' DEME"),
    ("M10 kumpasla olctur", "- Kumpasla merkez-merkez mesafeyi ölçtür ve yaz.", True,
     "kumpas/merkez-merkez olcu talebi"),
    ("M16 baglac maskesi (MUST3)", "- Ölçüyü gönderin çünkü tahmin yeterli değil.",
     True, "'cunku' ayirici olmasa sondaki 'degil' bastaki EMRI maskelerdi"),
    ("M17 'tahminen' morfolojisi", "- Tahminen 700 TL tutar.", True,
     "'tahmini' yazip 'tahminen'i kacirmak olculdu"),
    ("M18 'civari' morfolojisi", "- 800 TL civarı olur.", True,
     "'civarinda' yazip 'civari'yi kacirmak olculdu"),
    ("M19 'ortalama ... diyebiliriz'", "- Ortalama 500 TL diyebiliriz.", True,
     "1. cogul tahmin taahhudu"),
    ("M20 'bandinda' tahmini", "- Fiyat 900-1100 TL bandında olur.", True,
     "bant tahmini de taahhuttur"),
    ("M22 teknik resim talebi", "- Teknik resim gönderin.", True, "cizim sinifi"),
    ("M23 cap/cm talebi", "- Çapı cm olarak gönderin.", True, "olcu sinifi"),
    ("M24 ortuk uretim sozu", "- Sizin için yapabiliriz.", True,
     "ortuk 1. cogul uretim sozu"),
    # ═══ TUR 4: KARSI-OLGU REGRESYON (eski surumde KIRMIZI yanan hicbir cumle
    #     yeni surumde YESIL olmayacak — negatif veto kaldirilinca geri kazanildi) ═══
    ("R1 bastirici bypass'i (gorunur)", "- Yaklaşık 900 TL tutar ve sepette görünür.",
     True, "eski BETIMLEME vetosu bunu susturuyordu; taahhut kipi 'TL tutar' yanmali"),
    ("R2 bastirici bypass'i (yazar)", "- Yaklaşık 700 TL civarı bir maliyet yazar.",
     True, "'yazar' vetosu susturuyordu; artik TAAHHUT tarafinda"),
    # ═══ TUR 4: BINLIK/ONDALIK AYRAC — (C) 1.000 TL ustunde TAMAMEN OLUYDU ═══
    ("R3 binlik ayrac 4 hane", "- Yaklaşık 1.500 TL tutar.", True,
     "'1.500' bolununce tahmin ile para ayri cumleciklere dusuyordu"),
    ("R4 binlik ayrac + diyebiliriz", "- Ortalama 2.400 TL diyebiliriz.", True,
     "ayni bolunme sinifi"),
    ("R5 ondalik VIRGUL", "- Yaklaşık 1.250,50 TL olur.", True,
     "Turkce ondalik ayraci virgul — o da bolunuyordu"),
    ("R6 bes haneli gercekci fiyat", "- Tahminen 12.750 TL tutar.", True,
     "gercek ticari buyuklugumuz 1.000+ TL; fiksturler 3 haneli kalirsa yesil bir sey ispatlamaz"),
    # ═══ TUR 4: 'sorun' homografi geri kazanildi + virgullu devrik tumce ═══
    ("R7 'sorun' EMRI (kurulus sebebi)", "- Müşteriye ölçüleri sorun.", True,
     "TUR 3'te jetonu atmistim; isim-baglami ayirt edicisiyle geri kazanildi"),
    ("R8 virgullu devrik tumce (A)", "- Deliğin çapını, bize gönderin.", True,
     "virgul olcu jetonuyla emri ayiriyordu -> (A) artik CUMLE penceresinde"),
    ("R9 virgullu devrik tumce (A/2)", "- Teknik çizimi, mümkünse paylaşın.", True,
     "ayni sinif"),
    # ═══ YANLIS-POZITIF NOBETCILERI ═══
    # ⚠️ Bu kapi `build` isinde kosar, `deploy: needs: build` -> asagidakilerden biri
    # KIRMIZI yanarsa yalniz Ege degil TUM pruvo3d.com yayini durur.
    ("M3 duzeltilmis satir", YENI_SATIR, False, "dort sarti da saglayan metin YESIL olmali"),
    ("M4 teshis fotosu",
     "- Ne olduğunu anlamak için tek bir net fotoğraf ya da ek açı isteyebilirsin.",
     False, "TESHIS fotosu SERBEST (:52 istisnasi) — kapi buna dokunmamali"),
    ("M5 kosul sorma",
     "- motor/ısı → kaç dereceye dayanmalı sor · yük/darbe → tok+sağlam.",
     False, "KOSUL sormak :12 ile serbest — olcu degil"),
    ("M8 isi araligindaki 'yaklasik'",
     "- ısı dayanımı = HDT @ 0.45 MPa, yaklaşık aralık; abartma, taahhüt sayılır.",
     False, "'yaklasik' PARA jetonu olmadan fiyat sozu degildir"),
    ("M9 olumsuz emir", "- Müşteriden ölçü isteme, çizim toplama.", False,
     "olumsuz kipte yasak metni YESIL olmali"),
    ("M11 'sorun' homografi", "- Ölçüyle ilgili bir sorun olursa [DEVRET] yap.",
     False, "'sorun'=problem ismi; emir sanilirsa TUM SITE yayini durur"),
    ("M12 arayuz betimlemesi", "- Sepette yaklaşık tutar ödeme öncesi görünür.",
     False, "BETIMLEME (gorunur), taahhut DEGIL"),
    ("M13 sabit ucret betimlemesi",
     "- Kargo ücreti yaklaşık 250 TL olarak sepete eklenir.", False,
     "BETIMLEME (eklenir), taahhut DEGIL"),
    ("M14 belgenin KENDI l.9 kargo cumlesi", BELGE_L9, False,
     "canli mesru metin — bu sinif (C)'ye bir tik uzakta, kirmizi yanmamali"),
    ("M15 belgenin KENDI l.11 'netlestir' dili", BELGE_L11, False,
     "mesru ic refleks; ISTEK fiili degil"),
    ("M21 duz kesin fiyat = ILAN EDILMIS KOR NOKTA", "- Bu parça 1.200 TL.", False,
     "KAPSAM DISI ve OYLE ILAN EDILDI — burayi 'duzeltmek' belgenin l.9'unu "
     "sahte-kirmizi yakar ve tum siteyi durdurur"),
    ("M25 'yazın' = ILAN EDILMIS KOR NOKTA", "- Ölçüde sorun yaşarsanız yazın.", False,
     "'yaz/yazın' nesnesi SERBEST -> ISTEK'ten cikarildi; bedeli: 'Ölçüleri yazın' "
     "tipi talep artik YAKALANMAZ (ne_olculmedi()'de yazili)"),
    ("M26 'sorun' isim baglami (2)", "- Ölçüyle ilgili sorun yok.", False,
     "isim baglami — emir sanilmamali"),
    ("M27 belgenin l.7 konfigurator cumlesi",
     "- konfigüratör girilen ölçüye göre fiyatı hesaplar, onlar da sepetten kartla ödenir.",
     False, "'hesaplar' ZAYIF — YAKLASIK jetonu olmadan yanmaz"),
    # ═══ TUR 5: ZAYIF KANADIN TAM USTUNE OTURAN FIKSTURLER ═══
    # 🔴 NEDEN: TUR 4'te bu dort fiil (olur/yazar/cikar/gecerlidir) BETIMLEME'den
    # TAAHHUT'e tasindi, AMA hicbir yanlis-pozitif fiksturunde PARA jetonuyla birlikte
    # gecmiyordu (M12 yalniz "gorunur", M13 yalniz "eklenir" nobetliyordu) -> 36/36
    # YESIL yandi ve bu sinif hakkinda HICBIR SEY ispatlamadi. 17 mesru cumlenin 15'i
    # kirmiziydi ve kimse gormedi. Ders: bir davranisi degistirdiginde fikstur o
    # davranisin TAM USTUNE oturmali; yanindan gecen test seni YANILTIR.
    ("Z1 PARA + 'olur' (betimleme)", "- Kargo bedeli 250 TL olur.", False,
     "ZAYIF tek basina yanmamali"),
    ("Z2 PARA + 'yazar' (betimleme)", "- Fiyat ürün sayfasında yazar.", False,
     "ZAYIF tek basina yanmamali"),
    ("Z3 PARA + 'cikar' (betimleme)", "- Fiyat konfigüratörden çıkar.", False,
     "ZAYIF tek basina yanmamali"),
    ("Z4 PARA + 'gecerlidir' (betimleme)", "- Sitede yazan fiyat geçerlidir.", False,
     "ZAYIF tek basina yanmamali"),
    ("Z5 belgenin l.9 minimal varyanti",
     "- altında gönderi başına 250 TL kargo olur.", False,
     "canli belgenin kendi kargo satirinin anlamca ayni hali — KIRMIZI olursa yayin durur"),
    ("Z6 belgenin l.45 minimal varyanti",
     "- Liste fiyatı olanı söyle; özel/parametrikte fiyatı çıkar ve ilet + [DEVRET].",
     False, "l.45 varyanti — 'cikar' betimleme"),
    # ZAYIF kanadi YAKLASIK ile BIRLIKTE yanmali (ayni fiiller, taahhut baglaminda):
    ("Z7 YAKLASIK + 'olur'", "- Yaklaşık 1.250,50 TL olur.", True, "ZAYIF + tahmin = taahhut"),
    ("Z8 YAKLASIK + 'yazar'", "- Yaklaşık 700 TL civarı bir maliyet yazar.", True,
     "ZAYIF + tahmin = taahhut"),
    ("Z9 YAKLASIK + 'gecerlidir'", "- Tahminen 2.000 TL geçerlidir.", True,
     "ZAYIF + tahmin = taahhut"),
    ("Z10 tahmin ekseni: seviyesindedir", "- Aşağı yukarı 1.700 TL seviyesindedir.",
     True, "TUR 4'te bu eksen TAMAMEN olmustu (5/5 yesil)"),
    ("Z11 tahmin ekseni: seyreder", "- 3.300 TL civarında seyreder.", True, "ayni eksen"),
    ("Z12 tahmin ekseni: bulur", "- Yaklaşık 1.400 TL'yi bulur.", True, "ayni eksen"),
    # ═══ TUR 6: 'çapa/çapak' HOMOGRAFI (bizim KENDI urunumuz) ═══
    # MUT: (?!raz|a) -> (?!raz) yapilirsa C1-C3 KIRMIZI yanar (oldurucu mutant).
    ("C1 'çapa' = Marin urunu + teshis fotosu",
     "- Çapa braketini tanımak için fotoğraf iste.", False,
     "capa MARIN kategorisinin cekirdek urunu; M4 ile izin verilmis teshis davranisi"),
    ("C2 'çapa' urun cumlesi", "- Çapa makarası parçasını katalogdan gönder.", False,
     "capa = urun adi, OLCU jetonu DEGIL"),
    ("C3 'çapak' baski artigi", "- Çapak kalırsa temizleyip gönderin.", False,
     "capak = baski artigi, OLCU jetonu DEGIL"),
    ("C4 'çapraz' (eski koruma korunuyor)", "- Çapraz bağlantıyı gönderin.", False,
     "capraz zaten disaridaydi — regresyon nobetcisi"),
    ("C5 gercek CAP talebi hala yakalaniyor", "- Deliğin çapını gönderin.", True,
     "homograf korumasi GERCEK olcu talebini delmemeli"),
    # ═══ TUR 6: JENERIK 1. COGUL FIIL BAGLAM SARTI ═══
    # MUT: baglam sarti kaldirilirsa G1-G2 KIRMIZI yanar (oldurucu mutant).
    ("G1 kargo baglaminda 'yaparız'", "- Kargo çıkışını aynı gün yaparız.", False,
     "uretim sozu DEGIL; jenerik fiil URUN baglami ister"),
    ("G2 kargo baglaminda 'veririz'",
     "- 2.500 TL üzerinde kargoyu ücretsiz veririz.", False,
     "fiyat taahhudu DEGIL; 'ucretsiz' PARA_RE onek eslesmesi + 'veririz' yanmamali"),
    ("G3 belgenin l.14 'kargolarız'",
     "- kırılan/aşınan/bulunamayan parçayı üretip kargolarız.", False,
     "kendi surecimizin anlatimi; musteriye VERILEN SOZ degil"),
    ("G4 belgenin l.10 'oturturuz'",
     "- yuvası açıp somunu oturturuz; rahatça sun.", False, "ayni sinif"),
    ("G5 URUN baglaminda 'yapabiliriz' hala yaniyor", "- Sizin için yapabiliriz.", True,
     "baglam sarti (B) sinifini DELMEMELI"),
    ("G6 URUN baglaminda 'veririz'", "- Parça için 2.000 TL fiyat veririz.", True,
     "'parca' baglami var -> uretim/fiyat sozu"),
    # ═══ TUR 7: BAGLAM SARTININ BEDELINI OLCEN FIKSTURLER ═══
    # 🔴 NEDEN: G5/G6 tam da test ettikleri baglam kelimesinin ("sizin için" / "parça")
    # USTUNE oturmustu -> baglam sartinin BEDELINI olcemiyorlardi. TUR 6'da bu yuzden
    # 59/59 yesil yanarken 28 cumlelik taahhut korpusunda yakalama 27 -> 10'a dusmustu
    # ve M2'nin (kapinin KURULUS VAKASI) parafrazlari kaciyordu. Asagidakiler o
    # bosluğun UZERINDE oturur: MUT (baglam genislemesini geri al) hepsini kirar.
    ("G7 M2 parafrazi: '...yoksa biz de yaparız'",
     "- *Yapabilir misiniz?* → katalogda benzeri varsa oradan git, yoksa biz de yaparız.",
     True, "26 Tem kazasinin TEK KELIMELIK parafrazi — kacarsa kapi kendi dogus vakasini gormez"),
    ("G8 M2 parafrazi: '...yoksa hallederiz'",
     "- *Yapabilir misiniz?* → katalogda benzeri varsa oradan git, yoksa hallederiz.",
     True, "ayni sinif; 'hallederiz' ACIK oldugu icin baglamsiz da yanar"),
    ("G9 'Sizin adınıza yapabiliriz.'", "- Sizin adınıza yapabiliriz.", True,
     "ACIK fiil — baglam olmadan da yanmali"),
    ("G10 '2.000 TL fiyat veririz.' (urun kelimesi YOK)",
     "- 2.000 TL fiyat veririz.", True, "baglam 'fiyat' jetonundan gelir"),
    ("G11 'Elbette yapabiliriz.' (HIC baglam yok)", "- Elbette yapabiliriz.", True,
     "duz kabiliyet iddiasi; TUR 6'da KACIYORDU"),
    ("G12 'Ölçünüze göre hallederiz.'", "- Ölçünüze göre hallederiz.", True,
     "ACIK fiil; TUR 6'da KACIYORDU"),
    ("G13 'Size 800 TL'ye veririz.'", "- Size 800 TL'ye veririz.", True,
     "baglam: 'size' + \"TL'ye\"; TUR 6'da KACIYORDU"),
]


def ic_nobetci():
    print("EGE KABILIYET KAPISI — IC NOBETCI (kirmizi-mutasyon)")
    print("=" * 70)
    gecen = 0
    kalan = []
    i = 0
    while i < len(FIKSTURLER):
        ad, metin, kirmizi_bekle, aciklama = FIKSTURLER[i]
        b = bulgular(metin)
        oldu = len(b) > 0
        ok = (oldu == kirmizi_bekle)
        print("  [%s] %-42s bekleniyor=%-7s gercek=%-7s" % (
            "OK" if ok else "HATA", ad,
            "KIRMIZI" if kirmizi_bekle else "YESIL",
            "KIRMIZI" if oldu else "YESIL"))
        print("        %s" % aciklama)
        if b:
            j = 0
            while j < len(b):
                print("        -> [%s] %s" % (b[j][1], b[j][2][:110]))
                j += 1
        if ok:
            gecen += 1
        else:
            kalan.append(ad)
        i += 1
    print("=" * 70)
    print("  %d/%d fikstur gecti" % (gecen, len(FIKSTURLER)))
    if kalan:
        print("  KIRMIZI — gecemeyen: %s" % ", ".join(kalan))
        return 1
    print("SONUC: YESIL ✅ — kapi hem yakaliyor hem yanlis-pozitif uretmiyor.")
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--dosya", default=VARSAYILAN)
    ap.add_argument("--ic-nobetci", action="store_true", dest="ic")
    a = ap.parse_args()

    if a.ic:
        return ic_nobetci()

    try:
        metin = open(a.dosya, "rb").read().decode("utf-8")
    except OSError as e:
        print("okunamadi: %s" % e)
        return 2

    b = olcumu_bas(a.dosya, metin)
    ne_olculmedi()
    print()
    if b:
        print("SONUC: KIRMIZI ❌ — %d bulgu. ege-bilgi.md, Ege'nin canli talimatiyla "
              "CELISEN bir kabiliyet/fiyat sozu iceriyor." % len(b))
        print("  Dogrusu: tani -> katalogdakine yonlendir -> yoksa arastirip donecegini")
        print("  soyle + [DEVRET]. Olcu/cizim isteme, uretim/fiyat sozu verme.")
        return 1
    # 🔴 "fiyat sozu YOK" DEME — kapi duz kesin fiyat beyanini OLCMUYOR.
    # Bir kapi olcmedigi seyi olcmus gibi raporlayamaz (mimar hukmu 26 Tem).
    print("SONUC: YESIL ✅ — aranan uc kalip BULUNAMADI:")
    print("  (A) olcu/cizim istegi · (B) uretim sozu · (C) fiyat TAAHHUDU")
    print("  ⚠️  BU 'fiyat sozu yok' DEMEK DEGILDIR. (C) sunlari OLCMEZ:")
    print("      · duz kesin fiyat beyani            ('Bu parca 1.200 TL')")
    print("      · tahmin jetonu tasimayan betimleme ('Fiyat sayfada yazar')")
    print("      Ikisi de BILEREK disarida — ustteki NE OLCULMEDI listesine bak.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
