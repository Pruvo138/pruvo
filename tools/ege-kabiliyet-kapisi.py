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
  (D) KARAR VAADI — Ege'nin fiyati / malzeme-uretilebilirlik kararini KENDISININ
      CIKARIP ILETECEGINI soylemesi (bkz. KARAR_NESNESI_RE + VAAT_*_RE):
      · karar nesnesi + URETME cekimi  ("fiyati cikarip", "belirleyip")   -> yanar
      · karar nesnesi + ILETME cekimi  ("fiyati ileteceğim", "fiyati ilet")-> yanar
      · SURE jetonu   + ILETME cekimi  ("en kisa surede ileteceğim")      -> yanar
      · karar nesnesi YOK ("talebi ekibe ileteceğini soyle")              -> YANMAZ
      · ciplak 3. tekil ("fiyati hesaplar", "fiyat ... cikar")            -> YANMAZ
  (E) ELDE-YOK KOSULSUZ VAADI — musteride OLMAYAN ya da TANINMAYAN parcada
      kosulsuz ARASTIRMA/COZUM sozu (bkz. PARCA_BAGLAM_RE + ELDE_YOK_RE +
      E_VAAT_RE + TANIMA_SARTI_RE):
      · [satirda parca] + [yokluk|taninmama] + [arastirma vaadi], cumlede
        TANIMA SARTI YOK   ("yoksa arastirip donecegini soyle")           -> yanar
      · ayni cumlede TANIMA SARTI VAR ("...TANINIYORSA arastirip donecegini
        soyle")                                                           -> YANMAZ
      · satirda parca/urun baglami YOK ("Liste fiyati yoksa ...")         -> YANMAZ
      · vaat cumleciginde olumsuzlama ("...donecegini SOYLEME")           -> YANMAZ
Bes sinif oldu. (D) 1 Agu'da MIMAR KARARIYLA eklendi — "ucu gecme" kurali ozel
olarak kaldirildi, cunku olculdu: yasak kalibin DORT ozgun satiri da (A)/(B)/(C)'den
0 bulguyla geciyordu ve fikstur Z6 yasak cumleyi beklenen-YESIL olarak KILITLIYORDU.
(E) 4 Agu'da AYNI GEREKCEYLE, MIMAR KARARIYLA eklendi: kardes mimar HocA canli
agza PARCA_ELDE_YOK_METNI'ni koyup TANINIYOR/TANINMIYOR dalini SART kosarken bu
belge hala KOSULSUZ "yoksa arastirip donecegini soyle" diyordu. Iki zit talimat
ayni prompt'a girer, model rastgele birini secer ve TANINMAYAN parcada musteriye
YERINE GETIREMEYECEGIMIZ bir arastirma sozu — yani TICARI TAAHHUT — gider.
OLCULDU: o satir (A)/(B)/(C)/(D)'den 0 bulguyla geciyordu ve fikstur M3 onu
beklenen-YESIL olarak KILITLIYORDU (Z6'nun 1 Agu'daki hikayesinin AYNISI).
ALTINCI sinifi kendi basina EKLEME. Kapsam buyutmek pozitif nobetciyi sessizce
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
# 🔴 GENEL fiiller IKI AILEYE, IKI AYRI BAGLAM LISTESINE bolundu (TUR 8).
# TUR 7'de ikisi de ayni GENIS listeyi kullaniyordu ve liste ciplak zamirlerle
# (biz|size|sizin|bunu...) genislemisti. Sonuc OLCULDU: "vermek" fiili uretim/fiyat
# DISI baglamda cok dogaldir, zamirle birlesince para/uretim jetonu OLMADAN yaniyordu:
#     "2.500 TL uzerinde kargoyu SIZE ucretsiz veririz."  -> KIRMIZI (oysa kapinin
#      KENDI fikstur aciklamasi bunu "fiyat taahhudu DEGIL" diye yaziyor)
#     "IBAN'i buradan size veririz." · "Siparisi ... size kargoya veririz."
#     "Malzeme onerisini size veririz." · "Kargo takip numarasini size veririz."
# Tetikleyici canli belgede MEVCUT ("size" l.14'te, "biz" l.13'te) -> erisilebilir.
# TUR5'e gore 6 YENI yanlis-pozitif olculdu.
URETIM_YAPARIZ_RE = re.compile(r"\byaparız\b", re.IGNORECASE)
URETIM_VERIRIZ_RE = re.compile(
    r"\bveririz\b|\bveririm\b|\bvereceğiz\b|\bvereceğim\b", re.IGNORECASE)

# GENIS (yalniz "yaparız"): "yapmak" burada is-yapma fiilidir, zamir onu musteri
# isine baglar -> "...yoksa BIZ DE yaparız" (G7, M2 parafrazi) korunur.
URUN_BAGLAM_GENIS_RE = re.compile(
    r"üret|imal|\bparça|baskı|\bözel\b|tasarım|kalıp"
    r"|sizin\s+için|size\s+özel|sizin\s+adınıza|sizin\s+yerinize|\bsize\b|\bsizin\b"
    r"|\bbiz\b|\bbizde\b|\baynısını\b|\byenisini\b|\bbunu\b|\bbunları\b|\bşunu\b"
    r"|TL['’]ye|\bfiyat|\bölçünüze\b|\bölçüye\b|\bölçüsüne\b|\bmodele\b",
    re.IGNORECASE)

# DAR (yalniz "veririz/vereceğiz") — ZAMIR YOK. "vermek" bilgi/link/kargo/oneri de
# verir; taahhut sayilmasi icin URETIM ya da FIYAT-TAAHHUDU jetonu SART.
# ⚠️ "fiyat" var ama "fiyat ÇALIŞMASI" HARIC: o, fiyatin KENDISI degil surecidir ve
#    canli belgenin l.49'unda aynen geciyor ("Fiyat calismasi birkac saat surebilir").
# ⚠️ Ciplak "TL" YOK: "2.500 TL uzerinde ... ucretsiz veririz" mesrudur.
URUN_BAGLAM_DAR_RE = re.compile(
    r"üret|imal|\bparça|baskı|\bözel\b|tasarım|kalıp"
    r"|\bindirim|TL['’]ye|\bfiyat\b(?!\s+çalışma)",
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

# --- (D) KARAR VAADI (1 Agu, mimar karari) ---------------------------------
# OKAN'IN "%100 UYULACAK" KURALI: fiyati VE uretilebilirlik/malzeme karari
# Okan/ekip verir. Ege kosulu toplar, "arastirip donecegini soyle + [DEVRET]" der.
# Ege ASLA "fiyati cikarip size ileteceğim" DEMEZ.
# OLCULDU (1 Agu, duzeltme oncesi 4 ozgun satir): (A)+(B)+(C) toplam 0 bulgu verdi.
# Yani bu zarar sinifi kapiya TAMAMEN GORUNMEZDI.
#
# TASARIM — TEK KELIME DEGIL, FIIL OBEGI. Ucuncu bir sinifin bedelini (bazi mesru
# fiillerin tek basina yanmasi, bkz. ne_olculmedi()) BUYUTMEMEK icin (D) hicbir zaman
# tek jetonla yanmaz: her zaman [karar nesnesi | sure jetonu] + [Ege-oznesi cekimi].
#
# KARAR NESNESI = Okan'in verdigi kararin KONUSU.
# ⚠️ `\bücret(?!siz)` : "ucretsiz" PARA_RE'de onek eslesiyor ve canli l.9'da GECIYOR
#    ("2.500 TL ve uzeri ucretsiz"). Ayni tuzaga (D) dusmez.
KARAR_NESNESI_RE = re.compile(
    r"\bfiyat\w*|\bücret(?!siz)\w*|\btutar\w*|\bmaliyet\w*|\bteklif\w*"
    r"|\ben\s+uygun\w*|uygun\s+filament\w*|uygun\s+malzeme\w*|\bmalzemeyi\b"
    r"|üretim\s+karar\w*|\büretilebil\w*|\büretebilece\w*",
    re.IGNORECASE)

# URETME cekimi — karari EGE'nin KENDISININ cikarmasi/belirlemesi/hesaplamasi.
# 🔴 CIPLAK 3. TEKIL ("çıkar", "hesaplar", "belirler") BILEREK YOK. Canli belgenin
#    l.7'si ("konfigüratör ... fiyatı hesaplar" — fikstur M27) ve Z3 ("Fiyat
#    konfigüratörden çıkar") tam o kaliptadir ve BETIMLEMEDIR; oraya girseydi
#    `deploy: needs: build` yuzunden TUM SITE yayini dururdu.
VAAT_URETME_RE = re.compile(
    r"\bçıkarıp\b|\bçıkarırım\b|\bçıkarırız\b|\bçıkaracağım\b|\bçıkaracağız\b"
    r"|\bçıkaracağını\b|\bçıkardığını\b|\bçıkarayım\b|\bçıkarıyorum\b"
    r"|\bbelirleyip\b|\bbelirlerim\b|\bbelirleriz\b|\bbelirleyeceğim\b"
    r"|\bbelirleyeceğiz\b|\bbelirleyeceğini\b|\bbelirlediğini\b|\bbelirleyeyim\b"
    r"|\bhesaplayıp\b|\bhesaplarım\b|\bhesaplayacağım\b|\bhesaplayacağız\b"
    r"|\bhesaplayacağını\b|\bhesapladığını\b",
    re.IGNORECASE)

# ILETME cekimi — karari musteriye ULASTIRMA sozu.
# EMIR KIPI `\bilet\b` DAHIL: Ege'ye "fiyati ilet" demek, yasak sozun TALIMAT halidir
# (Z6'nin eski cumlesi tam buydu). "iletişimi" \b sinirindan gecmez, "iletin" (=musteri
# gondersin) BILEREK YOK — o (A) eksenidir.
# 🔴 CIPLAK "söyle" YOK: belgenin her yerinde mesru emirdir ("NET söyle", "Liste
#    fiyati olani söyle"). Yalniz GELECEK cekimi sayilir.
VAAT_ILETME_RE = re.compile(
    r"\bilet\b|\biletip\b|\biletirim\b|\biletiriz\b|\bileteceğim\b|\bileteceğiz\b"
    r"|\bileteceğini\b|\bilettiğini\b|\biletiyorum\b"
    r"|\bbildiririm\b|\bbildiririz\b|\bbildireceğim\b|\bbildireceğiz\b"
    r"|\bbildireceğini\b|\bbildirdiğini\b"
    r"|\bgönderirim\b|\bgöndereceğim\b|\bgöndereceğiz\b|\bgöndereceğini\b"
    r"|\bsöyleyeceğim\b|\bsöyleyeceğini\b|\byazacağım\b|\byazacağını\b",
    re.IGNORECASE)

# SURE ALT-EKSENI — AYRI bir zarardir ve nesne eksenine BAGLANAMAZ.
# GEREKCE (olculdu): duzeltme oncesi l.50 `"en kısa sürede ileteceğim" de` cumleciginde
# KARAR NESNESI YOKTUR ("en kisa surede" = zaman). Nesne sarti korunsaydi o satir
# yine 0 bulgu alirdi — yani dort satirin biri hala gorunmez kalirdi.
# ⚠️ DAR TUTULDU: "birkaç saat" TEK BASINA jeton DEGIL, yalniz "birkaç saat İÇİNDE"
#    sayilir — cunku canli l.50 "Fiyat calismasi bizde birkac saat surebilir" der ve
#    bu MESRU bir sure BETIMLEMESIDIR, taahhut degil. Ayni sekilde l.8'in
#    "3-5 is gununde kargoya verilir" ifadesi de disaridadir.
SURE_JETONU_RE = re.compile(
    r"en\s+kısa\s+süre\w*|en\s+geç\b|\bhemen\b|\bbugün\b|\byarın\b|\bakşama\b"
    r"|birkaç\s+(?:dakika|saat|gün)\s+içinde"
    r"|\d+\s*(?:dakika|saat|gün)\s+içinde"
    r"|\b(?:dakika|saat|gün)\s+içinde\b",
    re.IGNORECASE)
# Sure kanadinda ILETME cekimlerine "dön-" gelecegi de eklenir: "en kisa surede
# döneceğim" bir TESLIM SURESI sozudur. ⚠️ CIPLAK "döneceğini söyle" EKLENMEZ —
# o, kuralin DOGRU hali ve belgede DORT yerde geciyor; sure jetonu olmadan yanmaz.
VAAT_SURE_FIIL_RE = re.compile(
    VAAT_ILETME_RE.pattern
    + r"|\bdöneceğim\b|\bdöneceğiz\b|\bdöneceğini\b|\bdönerim\b|\bdöneriz\b"
      r"|\byetiştiririm\b|\byetiştireceğim\b",
    re.IGNORECASE)

# (D)'YE OZEL OLUMSUZLAMA EKI — ortak OLUMSUZ_RE'ye DOKUNULMADI (o (A)/(B)/(C) ile
# paylasilir; oraya kelime eklemek uc sinifi da gevsetirdi).
# 🔴 NEDEN GEREKLI (olculdu, mutasyon kosumu): (D)'nin YASAKLAYAN hali dogal olarak
# tam da (D) fiillerinin -ma/-me emir olumsuzudur:
#     "Fiyatı çıkarıp iletme."   <- bu, kuralin DOGRU yazilisidir
# ve bu ekler OLUMSUZ_RE'de YOKTU ("verme/deme/isteme" var, "iletme/çıkarma" yok).
# Eksiz surumde bu cumle KIRMIZI yanardi -> `deploy: needs: build` -> TUM SITE durur.
# ⚠️ ILAN EDILEN BEDEL: her bastirici bir BYPASS yuzeyidir. Ayni cumlecige bu
# kelimelerden birini SOKUSTURAN bir metin (D)'yi susturabilir. Dar tutuldu: yalniz
# (D)'nin KENDI fiillerinin olumsuz emir/isim-fiil bicimleri.
D_OLUMSUZ_EK_RE = re.compile(
    r"\biletme\b|\biletmeyin\b|\bçıkarma\b|\bçıkarmayın\b|\bbelirleme\b"
    r"|\bbelirlemeyin\b|\bhesaplama\b|\bhesaplamayın\b|\bbildirme\b"
    r"|\bgönderme\b|\bsöyleme\b|\bdönme\b",
    re.IGNORECASE)


def d_olumsuz(c):
    """(D) icin olumsuzlama: ortak liste + (D) fiillerinin olumsuz emir bicimleri."""
    return bool(OLUMSUZ_RE.search(c)) or bool(D_OLUMSUZ_EK_RE.search(c))

# OLUMSUZLAMA — Turkce -ma/-me emir olumsuzu + yasak isaretleri.
# Cumlecik (clause) duzeyinde bakilir. SATIR duzeyinde bakmak OLUMCUL: 26 Tem'in
# hatali satiri hem "iste" hem "verme" iceriyordu; satir duzeyi olumsuzlama
# "verme"yi gorup "iste"yi MASKELER ve kapi sahte-yesil yanardi (olculdu: fikstur M1).
OLUMSUZ_RE = re.compile(
    r"\bisteme\b|\btoplama\b|\baldırma\b|\bverme\b|\betme\b|\bgeçirme\b|\bsorma\b"
    r"|\bdeme\b|\bsunma\b|\buydurma\b|\bASLA\b|\bYASAK\b|\bDEĞİL\b|\bYOK\b"
    r"|\bkapsam\s+dışı\b|\bmez\b|\bmaz\b",
    re.IGNORECASE)

# --- (E) ELDE-YOK KOSULSUZ VAADI (4 Agu 2026, mimar karari) ----------------
# CANLI KURAL (pruvo-bot/worker/src/index.js, PARCA_ELDE_YOK_METNI): musteri
# parcanin KENDISINDE olmadigini yazdiysa IKI DAL vardir —
#   (1) TANINIYORSA (arac marka+model+yili ve adiyla belli STANDART parca) ->
#       mevcut "arastirip donecegim" akisi AYNEN isler;
#   (2) TANINMIYORSA (parcanin kendisi olmadan hangi parca oldugu CIKMIYOR) ->
#       arastirma sozu VERILMEZ, ACIK KAPI BIRAKILMAZ; tek ve yalin bir cumleyle
#       parca elimize ulasmadan uretilemeyecegi soylenir.
# Bu kapinin okudugu belge ise KOSULSUZ "yoksa arastirip donecegini soyle"
# diyordu. ZARAR SINIFI: yerine getirilemeyecek bir arastirma sozu, musteriye
# TICARI TAAHHUT olarak gider ("yardimci olamiyoruz" ile ayni sey DEGILDIR).
#
# TASARIM — (D) ile AYNI disiplin: FIIL OBEGI + GEREKLI KOSUL; tek jetonla ASLA
# yanmaz. Uc sart BIRLIKTE aranir, biri eksikse YANMAZ:
#   [1] SATIRDA parca/urun baglami (PARCA_BAGLAM_RE)
#   [2] AYNI CUMLEDE yokluk / taninmama baglami (ELDE_YOK_RE)
#   [3] AYNI CUMLEDE arastirma-cozum VAADI (E_VAAT_RE)
# ve GEREKLI KOSUL cumlede YOKSA yanar: POZITIF TANIMA SARTI (TANIMA_SARTI_RE).
# 🔴 TANIMA SARTI BIR BASTIRICI DEGIL, KURALIN KENDISIDIR: vaat ancak TANIMA
# testine BAGLIYSA mesrudur. Bedeli ne_olculmedi()'de ILAN EDILIYOR.
PARCA_BAGLAM_RE = re.compile(r"\bparça\w*|\bürün\w*", re.IGNORECASE)

# YOKLUK/TANINMAMA baglami.
# 🔴 `\btanınm\w*` BILEREK BURADA: parcanin TANINMAMASI, elde olmamasiyla AYNI
# zarar dalidir (canli kuralin (2) dali). Pozitif "tanınan/tanınıyorsa" ile
# karismasin diye guard tarafinda `(?!m)` ile disarida tutulur — yani "tanınmıyorsa"
# GUARD SAYILMAZ, tam tersine (E)'nin ta kendisidir (fikstur E2).
ELDE_YOK_RE = re.compile(
    r"\byoksa\b|\byok\s+ise\b|\bbulunamayan\b|\bbulunamazsa\b|\bbulamazsa\b"
    r"|\belinde\s+yok\w*|\belimizde\s+yok\w*|\belde\s+yok\w*|\bmüşteride\s+yok\w*"
    r"|parça\w*\s+(?:\w+\s+){0,2}olmadan|\bparçasız\b"
    r"|\bkayboldu\w*|\bkayıpsa\b|\batıldıysa\b|\batılmışsa\b"
    r"|\btanınm\w*",
    re.IGNORECASE)

# ARASTIRMA/COZUM VAADI — FIIL OBEGI listesi, tek kelime DEGIL.
# 🔴 CIPLAK "araştır" BILEREK YOK: kuralin DOGRU hali "araştırma sözü VERME"
#    ve mesru "koşulu araştır" ayni koke oturur; ciplak kok sahte-kirmizi yakardi.
# 🔴 "üretip kargolarız" BILEREK YOK: canli l.14 firma-kimligi/surec anlatimidir
#    ve fikstur G3 onu beklenen-YESIL olarak nobetler (fikstur E13).
E_VAAT_RE = re.compile(
    r"araştırıp\s+dön\w*|araştırıp\s+bildir\w*|araştırıp\s+ilet\w*"
    r"|araştırıp\s+haber\s+\w+|\baraştırırız\b|\baraştırırım\b"
    r"|\baraştıracağız\b|\baraştıracağım\b"
    r"|\bçözeriz\b|\bçözebiliriz\b|çözüme\s+kavuştur\w*|çözüm\s+bul\w*",
    re.IGNORECASE)

# GEREKLI KOSUL — POZITIF tanima testi. `(?!m)` "tanınmıyorsa / tanınmayan"i
# DISARIDA tutar (yukariya bak).
TANIMA_SARTI_RE = re.compile(
    r"\btanın(?!m)\w*|\btanıyabil\w*|kimliği\s+\w*çık\w*|kimliği\s+belli",
    re.IGNORECASE)

# (E)-YE OZEL OLUMSUZLAMA EKI — ortak OLUMSUZ_RE'ye DOKUNULMADI (o (A)/(B)/(C)
# ile paylasilir; oraya kelime eklemek uc sinifi da gevsetirdi).
# GEREKCE: kuralin DOGRU yazilisi tam bu kelimelerdir —
#   "Parça elinde yoksa araştırıp döneceğini SÖYLEME."
# ve "söyleme/bırakma" ortak listede YOKTU -> eksiz surumde bu YASAK METIN
# KIRMIZI yanar, `deploy: needs: build` yuzunden TUM SITE yayini dururdu (E10).
# ⚠️ ILAN EDILEN BEDEL: her bastirici bir BYPASS yuzeyidir.
E_OLUMSUZ_EK_RE = re.compile(
    r"\bsöyleme\b|\bsöylemeyin\b|\bkurma\b|\bkurmayın\b|\bbırakma\b"
    r"|\bbırakmayın\b|\bvaat\s+etme\b",
    re.IGNORECASE)


def e_olumsuz(c):
    """(E) icin olumsuzlama: ortak liste + (E) fiillerinin olumsuz emir bicimleri."""
    return bool(OLUMSUZ_RE.search(c)) or bool(E_OLUMSUZ_EK_RE.search(c))


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


# (D) KENDI penceresi: standart ayiraclara IKI NOKTA UST USTE de eklenir.
# 🔴 NEDEN AYRI: duzeltme oncesi l.19 tek cumlecikti ->
#     `Emin değilsen uydurma: "en uygunu çıkarıp ileteceğim" + [DEVRET]`
# ve bastaki "uydurma" OLUMSUZ_RE'de oldugu icin cumlecigin TAMAMINI susturuyordu.
# Yani yasagin ARDINDAN tirnak icinde verilen ZARARLI ORNEK CUMLE gorunmez kaliyordu.
# ":" ayirici yapilinca yasak ("uydurma") ile ornek ayri pencerelere duser.
# (A)/(B)/(C)'nin ortak ayiricisina DOKUNULMADI — onlarin davranisi degismemeli.
# ⚠️ Rakam korumasi burada da gecerli ("09:00-18:00" bolunmez).
_D_AYIRAC = r"(?:(?<!\d)[.;,:]|[.;,:](?!\d))"
D_CUMLECIK_AYIRICI = re.compile(_D_AYIRAC + r"|\n|" + _BAGLAC, re.IGNORECASE)


def d_cumlecikler(satir):
    """(D) jeton penceresi: cumlecik + ':' ayirici."""
    return [p.strip() for p in D_CUMLECIK_AYIRICI.split(satir) if p and p.strip()]


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
            # (B) UC KADEME: acik uretim fiili tek basina; "yaparız" GENIS baglam,
            # "veririz/vereceğiz" DAR baglam ister (zamir yeterli DEGIL).
            if (URETIM_ACIK_RE.search(c)
                    or (URETIM_YAPARIZ_RE.search(c) and URUN_BAGLAM_GENIS_RE.search(c))
                    or (URETIM_VERIRIZ_RE.search(c) and URUN_BAGLAM_DAR_RE.search(c))):
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

        # ---- (D) KARAR VAADI: KENDI cumlecik penceresi (':' de ayirir) ----
        # Her kanat FIIL OBEGI ister; tek jetonla ASLA yanmaz.
        for c in d_cumlecikler(satir):
            if d_olumsuz(c):
                continue
            nesne = KARAR_NESNESI_RE.search(c)
            if nesne and VAAT_URETME_RE.search(c):
                out.append((no, "D/KARAR-VAADI", c,
                            "Ege karari KENDISI URETIYOR ('%s' + uretme cekimi) — "
                            "fiyat/malzeme/uretilebilirlik karari Okan'da; dogrusu "
                            "'arastirip donecegini soyle + [DEVRET]'"
                            % nesne.group(0)))
            elif nesne and VAAT_ILETME_RE.search(c):
                out.append((no, "D/KARAR-VAADI", c,
                            "Ege karari ILETMEYI TAAHHUT EDIYOR ('%s' + iletme cekimi) "
                            "— karar Okan'da, Ege yalniz [DEVRET] eder"
                            % nesne.group(0)))
            elif SURE_JETONU_RE.search(c) and VAAT_SURE_FIIL_RE.search(c):
                out.append((no, "D/SURE-VAADI", c,
                            "SURE TAAHHUDU (zaman jetonu + iletme/donus cekimi) — "
                            "ne zaman donulecegi de Okan'in karari"))

        # ---- (E) ELDE-YOK KOSULSUZ VAADI: SATIR baglami + CUMLE penceresi ----
        # Jeton/kosul penceresi CUMLE (virgul BOLMEZ): "Parça müşteride YOKSA,
        # tanınıyorsa araştırıp döneceğini söyle" TEK beyandir, virgul onu
        # bolseydi TANIMA SARTI vaatten ayrilir ve kuralin DOGRU hali KIRMIZI
        # yanardi. Olumsuzlama penceresi CUMLECIK — ayni asimetri (A)'da da var,
        # ayni gerekceyle (yasak metni sahte-kirmizi yakmasin).
        if PARCA_BAGLAM_RE.search(satir):
            for cumle in cumleler(satir):
                if not (ELDE_YOK_RE.search(cumle) and E_VAAT_RE.search(cumle)):
                    continue
                if TANIMA_SARTI_RE.search(cumle):
                    continue
                for c in cumlecikler(cumle):
                    if E_VAAT_RE.search(c) and not e_olumsuz(c):
                        out.append((no, "E/ELDE-YOK-VAADI", cumle,
                                    "musteride OLMAYAN / TANINMAYAN parcada KOSULSUZ "
                                    "arastirma-cozum sozu — canli PARCA_ELDE_YOK_METNI "
                                    "TANINIYORSA/TANINMIYORSA dalini SART kosar; "
                                    "taninmayan parcada acik kapi BIRAKILMAZ, tek yalin "
                                    "cumleyle uretilemeyecegi soylenir"))
                        break
        i += 1
    return out


def olcumu_bas(yol, metin, sessiz=False):
    b = bulgular(metin)
    if not sessiz:
        print("EGE KABILIYET-SINIRI KAPISI")
        print("  Dosya : %s" % yol)
        print("  Olcum : %d satir, %d karakter" % (len(metin.split("\n")), len(metin)))
        print("  Kapsam: (A) olcu/cizim ISTEGI · (B) uretim sozu · (C) fiyat TAAHHUDU")
        print("          · (D) KARAR VAADI (fiyat/malzeme kararini cikarip iletme sozu)")
        print("          · (E) ELDE-YOK KOSULSUZ VAADI (taninmayan parcada arastirma sozu)")
        print("          (C) = para + GUCLU kip, ya da para + YAKLASIK + ZAYIF kip.")
        print("          (C) OLCMEZ: duz kesin fiyat beyani · tahmin jetonu tasimayan")
        print("          betimleme ('fiyat sayfada yazar') — ilan edilmis kor noktalar.")
        print("          (D) = [karar nesnesi | sure jetonu] + [Ege-oznesi cekimi];")
        print("          tek jetonla yanmaz. OLCMEZ: parafraz ('bakip haber ederim').")
        print("          (E) = [satirda parca] + [yokluk/taninmama] + [arastirma vaadi],")
        print("          cumlede POZITIF TANIMA SARTI YOKKEN. OLCMEZ: parafraz vaat")
        print("          ('bakip haber ederim') · parca kelimesi gecmeyen satir.")
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
    TUR 8: "veririz/vereceğiz" ailesi AYRI ve DAR bir baglam listesi kullanir (zamir
    TETIKLEYICI DEGIL) — cunku "vermek" bilgi/link/kargo/oneri de verir. V1-V7.

  · 🔴🔴 BU DOSYAYI DUZENLEYECEK KISIYE — INDIRGENEMEZ BEDEL, ONCEDEN SOYLUYORUZ:
    Su fiiller TEK BASINA (baglam aranmadan) KIRMIZI yakar, cunku onlari baglama
    baglamak kapinin KURULUS VAKASINI (M2: "...yoksa ozel uretiriz") ve tek kelimelik
    parafrazlarini ("...yoksa hallederiz") KACIRIYORDU:
        uretiriz · uretebiliriz · uretiveririz · ustleniriz · basariz · tasarlariz
        · hallederiz · hallederim · yapabiliriz · yaptirabiliriz
    BEDELI: bu fiilleri URETIM DISI, MESRU bir cumlede kullanirsan kapi KIRMIZI yanar
    ve `deploy: needs: build` oldugu icin TUM SITE yayini durur. En olasi carpisma:
        "Sepette takilirsa WhatsApp'tan da HALLEDERIZ."   -> KIRMIZI yanar
    (canli l.7 zaten "WhatsApp'tan da hallettigini ekle" diyor, yani bu ifade bu
    belgenin dogal uslubunda.) Bu, kelime kapisinin INDIRGENEMEZ gerilimidir —
    TUR 5'ten beri aynidir, regresyon DEGILDIR.
    ALTERNATIF IFADE (kapiyi yakmadan ayni seyi soyle):
        "hallederiz"   -> "yardimci oluruz" · "cozume kavustururuz" · "ilgilenir,
                          size doneriz" · "WhatsApp'tan da ilerletebiliriz"
        "yapabiliriz"  -> "arastirip doneriz" · "degerlendirip bildiririz"
        "uretiriz"     -> (KASITLI YASAK — uretim sozu Okan'in karari, :41)
    Yani: uretim/fiyat SOZU vermeyen bir cumle kuruyorsan yukaridaki karsiliklari
    kullan; kapi seni bilerek bu yone itiyor.
    ⚠️ 1 Agu EKI: yukaridaki karsiliklara bir KARAR NESNESI (fiyat/ucret/tutar/
    maliyet/teklif/uygun malzeme-filament/uretilebilirlik) EKLERSEN (D) sinifi yanar
    — "arastirip doneriz" YESIL ama "fiyati arastirip bildiririz" KIRMIZI. Bu
    KASITLIDIR: fiyat ve malzeme/uretilebilirlik karari Okan'dadir, Ege yalniz
    kosulu toplar ve [DEVRET] eder. Nesnesiz hali kullan (fikstur D19).
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
    olumsuzlama sekli (ornegin "istemekten kacin") sahte-KIRMIZI yakar.

  ── (D) KARAR VAADI — 1 Agu'da eklendi, NEYI OLCMEDIGI ───────────────────────
  · 🔴 PARAFRAZ KACISI (D)'de de GENISTIR ve ilk maddedeki hukum aynen gecerlidir.
    (D) bir FIIL OBEGI kapisidir: [karar nesnesi | sure jetonu] + [Ege-oznesi
    cekimi]. Ayni taahhudu BASKA FIILLERLE kuran metin RAHATCA gecer. Olculdu
    (1 Agu): su varyantlar KACAR — "fiyata bakip haber ederim" · "rakami
    ogrenip donerim" · "sana bir tutar cikartip yollarim" (cikart- yazimi) ·
    "maliyeti arastirip paylasirim". Yesil, "metin dogru" DEMEK DEGILDIR.
  · 🔴 DUZ KESIN FIYAT BEYANI (D)'de de OLCULMEZ — (C) ile ayni gerekce.
    "Ozel parcaniz 1.200 TL." bu kapidan YESIL gecer.
  · KOR NOKTA — CIPLAK 3. TEKIL FIIL (D) sayilmaz: "fiyati hesaplar",
    "fiyat konfiguratorden cikar", "fiyat sayfada yazar". Bilincli: canli l.7 ve
    fiksturler M27/Z2/Z3 tam bu kaliptadir; oraya girseydi TUM SITE yayini dururdu.
    Bedeli: "Fiyati sistem cikarir ve size gonderir" tipi EDILGEN/3. TEKIL bir
    vaat YAKALANMAZ. Fiksturler D21, D24.
  · KOR NOKTA — SURE JETONU LISTESI DARDIR. Yalniz "en kisa surede / en gec /
    hemen / bugun / yarin / aksama / N (dakika|saat|gun) icinde" sayilir.
    KASITLI DISARIDA: "birkac saat" (canli l.50 aynen boyle yaziyor — D25),
    "3-5 is gununde" (canli l.8 — D20), "ayni gun" (fikstur G1). Bedeli:
    "Ayni gun ileteceğim" tipi bir sure sozu YAKALANMAZ.
  · 🔴 (D)-YE OZEL BASTIRICI VAR VE BYPASS YUZEYIDIR. D_OLUMSUZ_EK_RE, (D)
    fiillerinin olumsuz emir bicimlerini (iletme/çıkarma/belirleme/hesaplama/
    bildirme/gönderme/söyleme/dönme) bastirir. GEREKCESI olculdu: kuralin DOGRU
    yazilisi tam bu kelimelerdir ("Fiyatı çıkarıp iletme.") ve ortak OLUMSUZ_RE
    onlari ICERMIYORDU -> eksiz surum o YASAK METNI kirmizi yakip yayini
    durduruyordu (fikstur D28). BEDELI: bu kelimelerden birini ayni cumlecige
    sokusturan bir metin (D)'yi SUSTURABILIR. Ortak OLUMSUZ_RE'ye DOKUNULMADI —
    oraya kelime eklemek (A)/(B)/(C)'yi de gevsetirdi.
  · KOR NOKTA — (D) KENDI cumlecik penceresini kullanir ve ortak ayiraclara ':'
    ekler. Gerekce: duzeltme oncesi l.19'da yasak ("uydurma") ile zararli ORNEK
    ayni cumlecikteydi ve olumsuzlama ornegi MASKELIYORDU (D1). Bedeli: nesne ile
    cekim ':' ile ayrilan iki parcaya duserse (D) onlari BIRLESTIREMEZ.
  · 🔴 (D) SIRKET SESINI EGE'NIN SESINDEN AYIRAMAZ. 1. cogul "belirleriz /
    iletiriz / bildiririz" SITE metninde mesrudur ("malzemeyi birlikte
    belirleriz"), ege-bilgi.md'de ise Ege'nin agzina girdigi an yasaktir. Kapi
    ikisini AYIRT EDEMEZ. Olculdu (1 Agu, tools/sayfalar.py'nin urettigi 256
    musteri sayfasi): 7 sayfada 1'er bulgu — hepsi sirket-sesi 1. cogul, bir
    tanesi ("gereksiz yere ust sinifa cikarip fiyat sisirmeyiz") duz sozcuk
    rastlantisi. YASAL/SSS sayfalarinda 0. Bu kapi o dosyalari OKUMAZ (yalniz
    ege-bilgi.md), ama ege-bilgi.md'ye ayni uslupla yazan biri yayini durdurur.
    ALTERNATIF IFADE: "fiyati/malzemeyi ... belirleriz/iletiriz" yerine
    "arastirip donecegini soyle + [DEVRET]" (kural zaten budur).
  · KAPSAM DISI — (D) "kim karar verir" sorusunu KELIMEDEN okur. "Malzeme ve
    fiyat karari bizde" (canli l.39, D14) ile "Malzemeyi biz belirleriz" (D30
    sinifi) ANLAMCA yakin ama biri YESIL biri KIRMIZI: fark, ikincisinin bir
    TAAHHUT CEKIMI tasimasidir. Sinir kelimeseldir, anlamsal degil.

  ── (E) ELDE-YOK KOSULSUZ VAADI — 4 Agu'da eklendi, NEYI OLCMEDIGI ───────────
  · 🔴 TANIMA SARTI BIR BYPASS YUZEYIDIR VE BILEREK KABUL EDILDI. (E) "vaat,
    TANIMA testine BAGLI mi" diye sorar; testi CUMLEDE bir POZITIF tanima jetonu
    (tanınıyorsa / tanınırsa / tanınan / kimliği çıkıyorsa) olarak okur. Ayni
    cumleye ANLAMSIZCA "tanınıyorsa" sokusturan bir metin (E)'yi SUSTURUR.
    Alternatifi olculdu: sart olmadan kuralin DOGRU hali ("...TANINIYORSA
    arastirip donecegini soyle + [DEVRET]") KIRMIZI yanar ve `deploy: needs:
    build` yuzunden TUM pruvo3d.com yayini durur. Fiksturler E5/E6 sartin POZITIF
    tarafini kalici olarak nobetler.
  · 🔴 PARAFRAZ KACISI (E)'de de GENISTIR ve ilk maddedeki hukum aynen gecerlidir.
    E_VAAT_RE bir FIIL OBEGI listesidir; ayni sozu baska fiillerle kuran metin
    RAHATCA gecer: "yoksa bakip haber ederim" · "parca elinde yoksa bir yolunu
    buluruz" · "bulamazsak biz ilgilenelim". Yesil, "metin dogru" DEMEK DEGILDIR.
  · KOR NOKTA — SATIR BAGLAMI SARTI: (E) yalniz satirda parca/urun jetonu varken
    olcer. GEREKCE: "Liste fiyati yoksa arastirip donecegini soyle" FIYAT
    eksenidir ve canli talimatta ACIKCA SERBESTTIR (FIYAT_VAADI_YASAGI: "Kesin
    fiyat gerekiyorsa YALNIZCA 'sizin icin arastirip ... donecegim' de"). O satiri
    yakan bir kural tum siteyi sahte-kirmiziyla durdururdu. BEDELI: parca/urun
    kelimesi GECMEYEN bir satirda kurulan elde-yok vaadi YAKALANMAZ (fikstur E9).
  · KOR NOKTA — CUMLE PENCERESI: yokluk baglami ile vaat AYRI cumlelerdeyse
    (nokta / noktali virgul / cunku-ama-fakat-ancak-zira ile ayrilmissa) (E)
    onlari BIRLESTIREMEZ. Ornek: "Parca elinde yok. Arastirip donecegini soyle."
    -> YANMAZ. Virgul BILEREK bolmez (yoksa kuralin dogru hali kirmizi yanardi).
  · KOR NOKTA — (E) OLUMSUZLAMA EKI (söyleme/kurma/bırakma/vaat etme) bir
    BASTIRICIDIR: bu kelimelerden birini ayni cumlecige sokusturan metin (E)'yi
    susturabilir. Ortak OLUMSUZ_RE'ye DOKUNULMADI.
  · KAPSAM DISI — (E) belgenin canli SISTEM_TALIMATI ile GERCEKTEN hizali olup
    olmadigini KANITLAMAZ; yalnizca KOSULSUZ vaat KALIBININ girmedigini soyler.
    Iki dalin (TANINIYOR / TANINMIYOR) anlamca dogru yazildigi, "acik kapi
    birakilmadigi" ve cumlenin YALIN kaldigi INSAN okumasi ister.
  · KAPSAM DISI — (E) "uretip kargolariz" tipi FIRMA-KIMLIGI/surec anlatimini
    olcmez (canli l.14; fiksturler G3/E13). Orada kapsamin daraltilmis olup
    olmadigi yine INSAN hukmudur.""")


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
# 26 Tem - 4 Agu arasi l.44. (A)/(B)/(C)/(D)'den TEMIZ gecer — ama canli agizdaki
# PARCA_ELDE_YOK_METNI ile CELISIR: "yoksa arastirip donecegini soyle" KOSULSUZDUR.
# 4 Agu'da (E) sinifinin ONCE-KIRMIZI capasi oldu (fikstur M3).
L44_ONCEKI = ("- *Yapabilir misiniz?* → Parçayı tanı; katalogdakine yönlendir, yoksa "
              "araştırıp döneceğini söyle + [DEVRET]. Ölçü/çizim isteme, "
              "üretim/fiyat sözü verme.")
# 4 Agu'dan sonraki GUNCEL l.44 — iki dalli hal (fikstur E5).
L44_GUNCEL = ("- *Yapabilir misiniz?* → Parçayı tanı; katalogdakine yönlendir. "
              "Parça müşteride YOKSA: marka+model+yıl+ad ile TANINIYORSA araştırıp "
              "döneceğini söyle + [DEVRET]; TANINMIYORSA açık kapı bırakma, "
              "\"parça elimize ulaşmadan üretemeyiz\" de. Ölçü/çizim isteme, "
              "üretim/fiyat sözü verme.")
# 4 Agu'dan sonraki GUNCEL l.14 — daraltilmis kapsam cumlesi (fikstur E13).
L14_GUNCEL = ("- PRUVO — endüstriyel + oto yedek parça **özel üretimi**; elimize "
              "ulaşan ya da marka+model+yıl+ad ile TANINAN kırılan/aşınan/"
              "bulunamayan parçayı üretip kargolarız.")

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
    # 🔴 M3 4 Agu'da TERSINE CEVRILDI (mimar karari) — Z6'nun 1 Agu'daki
    # hikayesinin AYNISI. ESKI HALI: bu satir beklenen-YESIL kayitliydi, gerekcesi
    # "dort sarti da saglayan metin". Iddia DOGRUYDU ama EKSIKTI: satir (A)-(D)'den
    # temiz gecerken canli agizdaki PARCA_ELDE_YOK_METNI ile CELISIYORDU ("yoksa
    # arastirip donecegini soyle" KOSULSUZDUR; canli kural TANINMAYAN parcada
    # arastirma sozunu YASAKLAR). Fikstur o celiskiyi beklenen-YESIL olarak
    # KILITLIYORDU: (E) eklendigi an ic nobetci kirilir, muhendis "demek ki desen
    # yanlis" diye geri alirdi.
    # 🔴 SINIF CAPALI BEKLENTI ("E") — duz `True` DEGIL. Duz True katmanlarin
    # VEYA'sini olcer: (A)-(D)'de acilan bir yanlis-pozitif (E) bulgusunun
    # arkasina gizlenir ve bu fikstur yine yesil yanardi ([[beyan-edilmis-survivor]]).
    # "E" demek: satir KIRMIZI yanacak VE bulgu siniflari TAM OLARAK {E} olacak —
    # yani eski "(A)-(D)'den temiz gecer" iddiasi AYNEN korunuyor.
    ("M3 eski l.44 (KOSULSUZ arastirma sozu)", L44_ONCEKI, "E",
     "(A)-(D)'den TEMIZ gecer AMA canli kuralin TANINIYOR/TANINMIYOR ayrimini "
     "TASIMAZ -> yalniz (E) yakalamali"),
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
    # 🔴 Z6 1 Agu'da TERSINE CEVRILDI (mimar karari). ESKI HALI: ayni cumle
    # (".. fiyatı çıkar ve ilet ..") beklenen-YESIL kayitliydi ve gerekcesi
    # "'cikar' betimleme" idi. Bu, kapinin (D) sinifinda SERTLESTIRILMESINI
    # KILITLIYORDU: yeni desen eklendigi an ic nobetci kirilir, muhendis "demek ki
    # desen yanlis" diye geri alirdi. Ustelik capasi da BAYATTI — o cumle
    # ege-bilgi.md'de artik YOK (1 Agu'da notrlendi).
    # Fikstur artik GUNCEL GERCEGI capalar; eski cumle D5'te KIRMIZI vaka olarak
    # KORUNUR (regresyon nobetcisi odur).
    ("Z6 belgenin l.46 GUNCEL hali",
     "- *Kesin fiyat?* → Liste fiyatı olanı söyle; özel/parametrikte araştırıp "
     "döneceğini söyle + [DEVRET].",
     False, "kuralin DOGRU hali — 'arastirip donecegini soyle' YESIL kalmali"),
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
     "baglam: \"TL'ye\" (DAR listede); TUR 6'da KACIYORDU"),
    # ═══ TUR 8: "veririz" AILESI DAR BAGLAM — zamir tetikleyici DEGIL ═══
    # 🔴 MUT8 (iki baglam listesini BIRLESTIR) V1-V5'i kirar: TUR 7'de tek GENIS liste
    # vardi ve ciplak "size" para/uretim jetonu OLMADAN yaniyordu. Tetikleyici canli
    # belgede MEVCUT ("size" l.14, "biz" l.13) -> TUM SITE yayinini durdururdu.
    ("V1 kapinin KENDI G2 fiksturunun 'size'li hali",
     "- 2.500 TL üzerinde kargoyu size ücretsiz veririz.", False,
     "G2 ile ayni cumle + 'size' — fiyat taahhudu DEGIL, YESIL kalmali"),
    ("V2 canli l.6 capali: IBAN verme",
     "- Ödeme linkini ya da IBAN'ı buradan size veririz.", False,
     "bilgi verme; uretim/fiyat jetonu YOK"),
    ("V3 canli l.8 capali: kargoya verme",
     "- Siparişi 3-5 iş gününde size kargoya veririz.", False, "teslim betimlemesi"),
    ("V4 canli l.49 capali: fiyat CALISMASI",
     "- Fiyat çalışması sonucu size veririz.", False,
     "'fiyat calismasi' fiyatin KENDISI degil SURECI — DAR listede istisna"),
    ("V5 malzeme onerisi verme", "- Malzeme önerisini size veririz.", False,
     "oneri verme; taahhut DEGIL"),
    ("V6 DAR listenin POZITIF tarafi: 'uygun fiyat veririz'",
     "- Size uygun fiyat veririz.", True, "'fiyat' jetonu DAR listede -> yanmali"),
    ("V7 DAR liste: 'parça için indirim veririz'",
     "- Parça için indirim veririz.", True, "'parca' + 'indirim' -> yanmali"),
    # ═══ (D) KARAR VAADI — 1 Agu, YENI SINIF ═══
    # 🔴 D1-D4 = ege-bilgi.md'nin DUZELTME ONCESI DORT OZGUN SATIRI. Olculdu (1 Agu,
    # degisiklikten ONCEKI kapi surumu): dordu de 0 BULGU aliyordu. ONCE-KIRMIZI
    # kaniti budur — bu dort fikstur eski surumde HATA verir.
    # MUT: (D) blogu silinirse ya da nesne/cekim sartlarindan biri gevsetilirse
    # D1-D12 kirilir; ':' ayirici standart ayirica dondurulurse D1 kirilir.
    ("D1 duzeltme ONCESI l.19 (tirnak icinde ornek)",
     'Kullanım yerine göre seç: iç mekan → standart · dış/güneş → UV+havaya dayanıklı '
     '· motor/ısı → kaç dereceye dayanmalı sor · yük/darbe → tok+sağlam. '
     'Emin değilsen uydurma: "en uygunu çıkarıp ileteceğim" + [DEVRET].',
     True,
     "'en uygunu cikarip ileteceğim' — bastaki 'uydurma' OLUMSUZ jetonu, ':' ayirici "
     "olmasa TUM cumlecigi susturuyordu"),
    ("D2 duzeltme ONCESI l.39 (malzeme+fiyat karari)",
     "- Malzemenin KRİTİK olduğu iş: bir filamentin o şartı tam karşılayıp "
     "karşılamayacağı üretim kararıdır. Koşulu net topla (hangi sıvı/yakıt · kaç "
     "derece · esnek mi sert mi), uygun filamenti + fiyatı belirleyip ileteceğini "
     "söyle + [DEVRET]. Kesin performans garantisi verme.",
     True, "'fiyati belirleyip ileteceğini' = malzeme + fiyat kararini ustlenme"),
    ("D3 duzeltme ONCESI l.46 (SSS kesin fiyat)",
     "- *Kesin fiyat?* → Liste fiyatı olanı söyle; özel/parametrikte fiyatı çıkarıp "
     "ilettiğini söyle + [DEVRET].",
     True, "'fiyati cikarip ilettiğini' — Z6'nin bayat capasinin gercek kaynagi"),
    ("D4 duzeltme ONCESI l.50 (SURE alt-ekseni)",
     '- Fiyat çalışması birkaç saat sürebilir; soğutma, "en kısa sürede ileteceğim" '
     'de, iletişimi sürdür.',
     True,
     "KARAR NESNESI TASIMAYAN tek vaka: '\"en kisa surede ileteceğim\" de' cumleciginde "
     "nesne YOK — sure alt-ekseni olmasa bu satir gorunmez kalirdi"),
    ("D5 Z6'nin ESKI cumlesi (tersine cevrildi)",
     "- Liste fiyatı olanı söyle; özel/parametrikte fiyatı çıkar ve ilet + [DEVRET].",
     True,
     "ESKIDEN beklenen-YESIL kayitliydi ve (D)'yi kilitliyordu; 'fiyatı ... ilet' "
     "emir kipi de yasak sozun talimat halidir"),
    ("D6 uydurma fiyat: hesaplayip iletme",
     "- Fiyatı hesaplayıp size ileteceğim.", True, "zarar sinifi: uydurma fiyat"),
    ("D7 malzeme kararini ustlenme",
     "- Uygun malzemeyi belirleyip ileteceğim.", True,
     "zarar sinifi: malzeme karari Ege'de degil"),
    ("D8 uretilebilirlik sozu",
     "- Üretilebilirliğini çıkarıp bildireceğim.", True,
     "zarar sinifi: uretilebilirlik karari Okan'da"),
    ("D9 duz sure taahhudu", "- En kısa sürede döneceğim.", True,
     "zarar sinifi: sure taahhudu (nesne YOK, sure kanadi yakalar)"),
    ("D10 sure + nesne birlikte", "- Fiyatı yarın ileteceğim.", True,
     "iki kanat da yanar; tek bulgu uretilmeli"),
    ("D11 teklif: hazirlayip gonderme", "- Teklifi hazırlayıp göndereceğim.", True,
     "'hazirlayip' URETME listesinde YOK — nesne + ILETME cekimiyle yakalanir"),
    ("D12 1. cogul kanat", "- Maliyeti çıkarıp size bildiririz.", True,
     "'ben' degil 'biz' cekimi de ayni taahhut"),
    # ═══ (D) YANLIS-POZITIF NOBETCILERI — kuralin DOGRU hali YESIL kalmali ═══
    # ⚠️ `deploy: needs: build`: asagidakilerden biri kirmizi yanarsa TUM pruvo3d.com
    # yayini durur. Bunlar canli ege-bilgi.md'nin GUNCEL (1 Agu) cumleleridir.
    ("D13 canli l.19: 'arastirip donecegini soyle'",
     "- Emin değilsen uydurma: araştırıp döneceğini söyle + [DEVRET].", False,
     "kuralin DOGRU hali — sure jetonu YOK, karar nesnesi YOK"),
    ("D14 canli l.39: 'Malzeme ve fiyat karari bizde'",
     "- Malzeme ve fiyat kararı bizde. Kesin performans garantisi verme.", False,
     "karar nesnesi VAR ama vaat cekimi YOK — kuralin DOGRU hali"),
    ("D15 canli l.39 tam hali",
     "- Koşulu net topla (hangi sıvı/yakıt · sürekli mi ara sıra mı · kaç derece · "
     "esnek mi sert mi), araştırıp döneceğini söyle + [DEVRET]. Malzeme ve fiyat "
     "kararı bizde. Kesin performans garantisi verme.", False,
     "duzeltilmis l.39'un TAMAMI — D2'nin YESIL ikizi"),
    ("D16 canli l.23: filament onerisi",
     "- Ege SADECE bu aileden seçenek sunar; uygun filament(ler)i önerebilir, adını "
     "da söyleyebilir.", False,
     "'uygun filament' nesne jetonu tasir; 'öner-/söyleyebilir' vaat cekimi DEGIL — "
     "malzeme ONERMEK serbest, malzeme KARARINI ustlenmek yasak"),
    ("D17 canli l.50 guncel hali",
     "- Fiyat çalışması bizde birkaç saat sürebilir; soğutma, süre/fiyat sözü verme, "
     "araştırıp döneceğini yinele, iletişimi sürdür.", False,
     "'birkac saat' TEK BASINA sure jetonu DEGIL ('icinde' sart); 'iletişimi' \\b "
     "sinirindan gecmez — D4'un YESIL ikizi"),
    ("D18 mesru DEVRET: talebi ekibe iletme",
     "- Talebi ekibe ileteceğini söyle + [DEVRET].", False,
     "ILETME cekimi VAR ama KARAR NESNESI YOK -> (D) tek kelimeyle yanmaz. "
     "Bu fikstur (D)'nin fiil-obegi tasarimini nobetler"),
    ("D19 mesru: kosulu degerlendirip bildirme",
     "- Koşulu topla, değerlendirip bildiririz.", False,
     "ne_olculmedi()'nin ONERDIGI alternatif ifade — nesnesiz oldugu icin YESIL"),
    ("D20 canli l.8: teslim betimlemesi",
     "- Siparişi 3-5 iş gününde kargoya veririz.", False,
     "'is gununde' sure jetonu DEGIL (yalniz 'gun icinde' sayilir)"),
    ("D21 canli l.7: konfigurator fiyati hesaplar",
     "- konfigüratör girilen ölçüye göre fiyatı hesaplar, onlar da sepetten kartla "
     "ödenir.", False,
     "CIPLAK 3. tekil 'hesaplar' URETME listesinde YOK — M27'nin (D) ikizi"),
    ("D22 canli l.9: 'ucretsiz' onek tuzagi",
     "- 2.500 TL ve üzeri ücretsiz; altında gönderi başına 250 TL toplama eklenir.",
     False, "`\\bücret(?!siz)` olmasa 'ucretsiz' karar nesnesi sayilirdi"),
    ("D23 calisma saati ':' rakam korumasi",
     "- Pzt–Cmt 09:00–18:00, Pazar kapalı; fiyat listesi sayfada.", False,
     "'09:00' bolunmemeli ve hicbir vaat cekimi yok"),
    # 🔴 D24-D26: (D)'nin UC DAR SINIRININ TAM USTUNE oturan nobetciler.
    # Bunlar olmadan asagidaki mutantlar SAG KALIYORDU (olculdu, 1 Agu — mutasyon
    # kosumu): `(?!siz)` kaldir · SURE'yi ciplak "birkaç saat"e genislet ·
    # `\bilet\b` sinirini kaldir. Bir sinirin bedeli, YANINDAN gecen fiksturle
    # ispatlanmaz (bu dosyanin TUR 5 dersi).
    ("D24 'ucretsiz' + iletme cekimi (MUT: `(?!siz)` kaldir)",
     "- Kargonun ücretsiz olduğunu ileteceğini söyle.", False,
     "'ucretsiz' KARAR NESNESI DEGILDIR; kargonun bedava oldugunu soylemek l.9'un "
     "ACIK emridir ('NET söyle')"),
    ("D25 'birkac saat' + donus (MUT: SURE'yi 'içinde'siz genislet)",
     "- Fiyat çalışması bizde birkaç saat sürebilir ve araştırıp döneceğini yinele.",
     False,
     "'birkac saat' SURE JETONU DEGIL — canli l.50 aynen boyle yaziyor; yalniz "
     "'birkac saat İÇİNDE' taahhut sayilir"),
    ("D26 'iletişimi' \\b sinirinda (MUT: `\\bilet\\b` -> `ilet`)",
     "- Fiyat listesi için iletişimi sürdür.", False,
     "'iletişimi' ILETME cekimi DEGIL; sinir kaldirilirsa canli l.50 KIRMIZI yanar "
     "ve TUM SITE yayini durur"),
    # 🔴 D27-D28: (D)'nin NESNE SARTI ve OLUMSUZLAMA kontrolu — bu ikisi ilk
    # mutasyon kosumunda TESTSIZ cikti (MUT-D1a ve MUT-D10 SAG KALMISTI).
    ("D27 nesne SARTI (MUT: uretme kanadindan nesne sartini kaldir)",
     "- Müşterinin kategorisini belirleyip kataloğa yönlendir.", False,
     "URETME cekimi ('belirleyip') VAR ama KARAR NESNESI YOK -> yanmamali; "
     "(D) fiil obegi arar, tek fiil degil"),
    ("D28 (D) fiilinin OLUMSUZ emri = kuralin DOGRU yazilisi",
     "- Fiyatı çıkarıp iletme, araştırıp döneceğini söyle + [DEVRET].", False,
     "'iletme' ortak OLUMSUZ_RE'de YOKTU; D_OLUMSUZ_EK_RE olmadan bu YASAK METNI "
     "KIRMIZI yakar ve TUM SITE yayini durur"),
    ("D29 ortak OLUMSUZ_RE hala etkili", "- Fiyatı çıkarıp ileteceğini ASLA söyleme.",
     False, "'ASLA' ortak listede — (D) olumsuzlama kontrolu kaldirilirsa yanar"),
    ("D30 'malzemeyi' TEK BASINA nesne (MUT: nesne listesinden cikar)",
     "- Malzemeyi belirleyip ileteceğini söyle.", True,
     "'uygun' kelimesi CIKARILARAK kural susturulamamali — D7'nin tek-kelimelik "
     "parafrazi; bu dosyanin TUR 4 dersi"),
    # ═══ (E) ELDE-YOK KOSULSUZ VAADI — 4 Agu, YENI SINIF ═══
    # 🔴 ONCE-KIRMIZI CAPASI: M3 + E1. Ikisi de degisiklikten ONCEKI ege-bilgi.md
    # metnidir ve (E) OLMADAN 0 bulgu alir — yani bu zarar sinifi kapiya TAMAMEN
    # GORUNMEZDI (aynen (D)'nin 1 Agu'daki durumu).
    # 🔴 UC SART VE BIR GEREKLI KOSUL AYRI AYRI NOBETLENIR (TUR 5 dersi: bir
    # davranisin YANINDAN gecen fikstur seni YANILTIR). Her mutant ayri fiksturle
    # olur: E9 = satir/parca sarti · E11 = yokluk sarti · E12 = vaat sarti ·
    # E5/E6 = TANIMA SARTI · E10 = olumsuzlama.
    ("E1 elde yok + KOSULSUZ vaat",
     "- Parça müşterinin elinde yoksa araştırıp döneceğini söyle + [DEVRET].", "E",
     "canli kuralin (2) dalini YOK sayar: TANINMAYAN parcada arastirma sozu YASAK"),
    ("E2 'tanınmıyorsa' GUARD DEGILDIR",
     "- Parça tanınmıyorsa da araştırıp döneceğini söyle, açık kapı bırak.", "E",
     "olumsuz dal (E) BAGLAMIDIR; `(?!m)` olmasa TANIMA_SARTI onu guard sanip "
     "TAM ZARAR VAKASINI susturur"),
    ("E3 kayip/atilmis parcada cozum sozu",
     "- Parça kayboldu ya da atıldıysa da ürünü çözeriz.", "E",
     "parca fiziksel olarak bize ULASMADAN uretim de tarama da YAPILAMAZ"),
    ("E4 1. tekil vaat kipi", "- Ürün elinde yoksa araştırırım.", "E",
     "vaat 1. tekil de olsa ayni ticari taahhut"),
    # ═══ (E) YANLIS-POZITIF NOBETCILERI ═══
    # ⚠️ `deploy: needs: build`: asagidakilerden biri KIRMIZI yanarsa yalniz Ege
    # degil TUM pruvo3d.com yayini durur. E5/E7/E8/E11/E13 canli belgenin GUNCEL
    # cumleleridir.
    ("E5 canli l.44 GUNCEL hali (iki dalli)", L44_GUNCEL, False,
     "TANINIYORSA sartina BAGLI vaat MESRUDUR — canli kuralin (1) dali; bu satir "
     "kirmizi yanarsa yayin durur"),
    ("E6 TANIMA SARTI'nin TAM USTUNDE (MUT: sart kontrolunu kaldir)",
     "- Parça müşteride yoksa marka+model+yıl ile tanınıyorsa araştırıp "
     "döneceğini söyle + [DEVRET].", False,
     "uc sart da VAR + TANIMA SARTI VAR -> YESIL; sart kaldirilirsa KIRMIZI yanar"),
    ("E7 canli l.46: FIYAT ekseninde vaat (MUT: ELDE_YOK sartini kaldir)",
     "- *Kesin fiyat?* → Liste fiyatı olanı söyle; özel/parametrikte araştırıp "
     "döneceğini söyle + [DEVRET].", False,
     "yokluk jetonu YOK; sart dusurulurse canli l.46 yanar ve yayin durur"),
    ("E8 canli l.19: 'Emin degilsen ... arastirip donecegini soyle'",
     "- Emin değilsen uydurma: araştırıp döneceğini söyle + [DEVRET].", False,
     "yokluk jetonu YOK, parca jetonu YOK — kuralin DOGRU hali"),
    ("E9 FIYAT ekseninde 'yoksa' (MUT: satir/parca sartini kaldir)",
     "- Liste fiyatı yoksa araştırıp döneceğini söyle + [DEVRET].", False,
     "FIYAT_VAADI_YASAGI bu vaadi ACIKCA SERBEST birakir; satirda parca/urun "
     "jetonu YOK -> (E) olcmez. ILAN EDILMIS BOSLUK (ne_olculmedi)"),
    ("E10 kuralin OLUMSUZ yazilisi (MUT: e_olumsuz kontrolunu kaldir)",
     "- Parça elinde yoksa araştırıp döneceğini SÖYLEME, üretemeyeceğini yalın söyle.",
     False,
     "'söyleme' ortak OLUMSUZ_RE'de YOK; E_OLUMSUZ_EK_RE olmadan bu YASAK METIN "
     "KIRMIZI yanar ve TUM SITE yayini durur"),
    ("E11 parca VAR, vaat VAR, yokluk YOK (MUT: ELDE_YOK sartini kaldir)",
     "- Ürün için fiyat çalışması birkaç saat sürebilir; araştırıp döneceğini yinele.",
     False, "yokluk baglami YOK -> (E) tek jetonla ASLA yanmaz"),
    ("E12 parca VAR, yokluk VAR, vaat YOK (MUT: E_VAAT sartini kaldir)",
     "- Katalogda yoksa önce parçayı tanımaya çalış.", False,
     "arastirma/cozum VAADI YOK; ayrica 'tanımaya' TANIMA tarafinda"),
    ("E13 canli l.14 GUNCEL hali (kapsam cumlesi)", L14_GUNCEL, False,
     "'bulunamayan' yokluk jetonu tasir ama 'uretip kargolariz' FIRMA-KIMLIGI "
     "anlatimidir ve E_VAAT listesinde YOKTUR — G3'un (E) ikizi"),
]


def _sinif_kumesi(bulgu_listesi):
    """Bulgu sinifi etiketinin ONEKI: 'A/ISTEK' -> 'A'."""
    return set(x[1].split("/")[0] for x in bulgu_listesi)


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
        gercek_kume = _sinif_kumesi(b)
        # 🔴 IKI BEKLENTI BICIMI (4 Agu):
        #   bool  -> yalnizca KIRMIZI/YESIL (eski, gevsek: katmanlarin VEYA'si)
        #   str   -> KIRMIZI *VE* bulgu siniflari TAM OLARAK bu kume ("E", "A,B")
        # Sinif capasi, bir fiksturun birden cok iddiayi VEYA'lamasini onler:
        # (A)-(D)'de acilan bir yanlis-pozitif, (E) bulgusunun arkasina gizlenemez
        # ([[beyan-edilmis-survivor]] — "beyan edilmis survivor delik gizler").
        if isinstance(kirmizi_bekle, str):
            bekle_kume = set(p.strip() for p in kirmizi_bekle.split(",") if p.strip())
            ok = oldu and (gercek_kume == bekle_kume)
            bekle_str = "KIRMIZI[%s]" % ",".join(sorted(bekle_kume))
        else:
            ok = (oldu == kirmizi_bekle)
            bekle_str = "KIRMIZI" if kirmizi_bekle else "YESIL"
        gercek_str = ("KIRMIZI[%s]" % ",".join(sorted(gercek_kume))) if oldu else "YESIL"
        print("  [%s] %-42s bekleniyor=%-13s gercek=%-13s" % (
            "OK" if ok else "HATA", ad, bekle_str, gercek_str))
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
        print("  Dogrusu: tani -> katalogdakine yonlendir -> parca musteride yoksa")
        print("  TANINIYORSA arastirip donecegini soyle + [DEVRET], TANINMIYORSA acik")
        print("  kapi birakma. Olcu/cizim isteme, uretim/fiyat sozu verme.")
        return 1
    # 🔴 "fiyat sozu YOK" DEME — kapi duz kesin fiyat beyanini OLCMUYOR.
    # Bir kapi olcmedigi seyi olcmus gibi raporlayamaz (mimar hukmu 26 Tem).
    print("SONUC: YESIL ✅ — aranan bes kalip BULUNAMADI:")
    print("  (A) olcu/cizim istegi · (B) uretim sozu · (C) fiyat TAAHHUDU")
    print("  · (D) karar vaadi (fiyat/malzeme kararini cikarip iletme sozu)")
    print("  · (E) elde-yok KOSULSUZ vaadi (taninmayan parcada arastirma sozu)")
    print("  ⚠️  BU 'fiyat sozu yok' DEMEK DEGILDIR. (C) sunlari OLCMEZ:")
    print("      · duz kesin fiyat beyani            ('Bu parca 1.200 TL')")
    print("      · tahmin jetonu tasimayan betimleme ('Fiyat sayfada yazar')")
    print("      Ikisi de BILEREK disarida — ustteki NE OLCULMEDI listesine bak.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
