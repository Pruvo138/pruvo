#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/parti-kapisi.py — N2 (B): ACIK 🔧 VARKEN YENI PARTI/ISCI **RAPOR EDILIR**.

🔴🔴 11 EYL 2026 — OKAN EMRI: "tum tikayicilari kaldir"
==============================================================================
Bu dosya bir zamanlar bir REDDEDICIYDI. ARTIK DEGIL. **Kaldirilan sey
REDDETME YETKISIDIR, OLCUM DEGIL.** Her kol tam olarak eskisi gibi olcer ve
teshisini AYNI alanlarla (EV · ACIK · KALEM · KOL · SEBEP) basar; yalnizca
hukum `RED` yerine **`RAPOR`** olur ve cikis kodu **0**'dir.

OLCULEN ARIZA (mimar, 11 Eyl, kendi komutuyla): salt-okuma
`grep -n "parti-kapisi\\|N2B" ~/.claude/cron/isci.sh` cagrisi
`N2B HUKUM=RED KOL=N2B-ETIKET-OKUNAMADI EV=KraL ACIK=0` ile REDDEDILDI —
hicbir is baslatmayan bir `grep`, tirnak ICINDEKI boru yuzunden "yeni is"
sayildi. Ucuncu tur ([[n2b-kapisi-dizge-olcer]]). Ustelik red metni celisikti:
"acik 🔧 kalem VAR (acik=0)".
🔴 BEDELI OLCULDU: `grep -c "N2B" ~/.claude/cron/isci.log` = **0** — kapi
cagriyi LOGLANMADAN kesiyordu, dolayisiyla "kimse m3 kullanamiyor" sikayeti
uc turdur GORUNMEZ kaldi. Bu yuzden teshis satiri SUSTURULMAZ: sayi
kaybolursa sikayet bir daha olculemez.

DOKTRIN (degismedi, YAPTIRIMI degisti)
--------------------------------------
"Acik kalem varken yeni parti acmak borcu buyutur" HALA DOGRUDUR ve HALA
olculur. Ama bu bilgi artik **okuyanin karari** icin basilir, cagriyi kesmek
icin degil. Kapinin yanlis pozitifi (bir `grep`i kesmek) olculdu ve dogru
pozitifinden PAHALI cikti: kesilen cagri loglanmiyor, sikayet olculemiyor,
ucuz kata inen yol da pahali kata inen yol da kapali kaliyordu.

🔴 SUREN/YARIM IS ZATEN KESILMEZDI, simdi HICBIR IS KESILMEZ. `N2B-YENI` /
   `N2B-SUREN` / `N2B-OKUMA` ayrimi KALDI — cunku o ayrim hukmun DEGIL
   TESHISIN parcasidir: "bu cagri ne yapiyordu" sorusunun cevabidir.

IKI YUZEY (ikisi de ayni karar fonksiyonundan turer — ikinci mantik YOK)
------------------------------------------------------------------------
  1. `--isci-kapi <MOTOR> <EV_KOKU> <SPEC> <ETIKET>`
     `~/.claude/cron/isci.sh` govdesinden cagrilir. **CRON'u da kapsar** —
     `macit-parti-surucusu.sh` gibi surucler dogrudan crontab'tan kosar,
     PreToolUse kancasi onlari GORMEZ. Tek bogaz burasidir.
  2. `--kanca` (varsayilan; stdin'de PreToolUse JSON'u)
     Ajan oturumlarindaki Bash cagrilarini kapsar. 6 eve
     `tools/mimar-kapi-kur.py --parti-kapisi` ile dagitilir (IKINCI KURUCU YOK).

ALTI KOL — HEPSI GECER, hicbiri REDDETMEZ; ayrim TESHISTEDIR
-------------------------------------------------------------
  N2B-YENI        cagri YENI is baslatiyor          -> T4 borc sorgusuna girer
  N2B-SUREN       cagri yeni is DEGIL (suren/yarim) -> GECER, sessiz
  N2B-OKUMA       sarmalayici yalniz ARGUMAN olarak -> GECER, jeton stderr'de
                  geciyor; hicbir is BASLAMIYOR
  N2B-RED         sahibinin evinde acik kalem var   -> **RAPOR** + kalem +
                  (jeton adi TARIHSEL olarak kaldi)    `kabul:` · cagri GECER
  N2B-DEFTER-YOK  evin defter DOSYASI hic YOK       -> GECER ama SESSIZ DEGIL
                  (defter gelenegini benimsememis)     (jeton hukum satirinda)
  N2B-OLCULEMEDI  ev cozulemedi / defter VAR ama    -> **RAPOR** (olcum
                  okunamadi (bos/bozuk/IO)             YAPILAMADI ilani) · GECER

🔴 `N2B-RED` JETONUNUN ADI NEDEN DEGISMEDI: jeton bes evin gunluklerinde,
   `n2b-dagitim-probu.py`de ve gecmis defter satirlarinda ARANIYOR. Adi
   degistirmek o arayicilari sessizce korlestirirdi
   ([[tuketici-yazilirken-tum-okuyucular-sayilir]]). Hukum satirindaki
   `HUKUM=` alani RAPOR'a dondu; ayirt edici alan ODUR, jeton adi degil.

🔴 SILINEN KOLLAR — ve NEDEN (ikinci kopya birakilmadi):
  `N2B-MUAF` + `MUAF_ETIKET_ONEKLERI`: onarim hattinin KENDINI bloklamasini
     engelleyen KACIS YOLUYDU. Reddetme kalkinca bloklanacak bir sey kalmadi;
     muafiyet listesi kuralin IKINCI KOPYASINA doner ve bayatlar
     ([[kapi-red-metni-ikinci-kopyadir]]). SILINDI — yoruma alinmadi.
  `N2B-CAGRI-YERI` (N4A): yalnizca `MUAF_ETIKET_ONEKLERI` sozlesmesinin
     gercek cagri yerlerine bagli oldugunu olcuyordu. Olctugu sey silindi.

🔴 K229 — UCUNCU KOVA (20 Agu 2026, canli bloker). "Defter DOSYASI YOK" ile
"defter OKUNAMADI" AYNI SEY DEGILDIR. Bes evden DORDUNDE (hasat/bot/jenerator/
pazarlama) `acik-kalemler.md` HIC YOKTU; kapi ikisini tek kovaya (OLCULEMEDI)
atinca defter gelenegini hic benimsememis evler fail-closed RED yedi ve ucuz
katlari saatlerce OLU kaldi. Kapinin KENDI doktrini bunu zaten yasakliyor:
*"acik kalem varken tamiri baslatamamak KILITLENMEDIR"* — bir evi hic sahip
olmadigi gelenekle bloklamak ayni kilitlenmenin EV DUZEYINDEKI halidir.
🔴 REDDEDILEN IKI ALTERNATIF (mimar hukmu, 20 Agu):
  ❌ "dort eve BOS defter ac" — bos dosya OLCULMEMIS bir sifiri OLCULMUS gibi
     gosterir; borc "yok" gorunur, kapi susar (K201: "EKLE yetmez, SAYI sart").
     Bu yuzden defter VAR ama BOS/BOZUK ise kol HALA `N2B-OLCULEMEDI`dir —
     artik RED degil RAPOR, ama olcum EKSIKLIGI ILANI AYNEN durur.
  ❌ "defteri olmayan evi SESSIZCE GECER say" — doktrini sessizce devre disi
     birakir. Bu yuzden jeton AYRIDIR, hukum satirinda GORUNUR, probda SAYILIR.

Borc olcumu TEK KAYNAK `tools/parti-borc-kapisi.py` (T4): bu dosya kendi defter
parser'ini YAZMAZ, `acik_kalem_listesi` + `parti_engeli_var_mi` cagirir.
Ev->depo eslemesi de T4'un `EV_DIZIN`inden TURETILIR (ucuncu ev tablosu YOK).
T4 evlere dagitilan kopyanin YANINDA BULUNMAZ: kardes yoksa KANONIK repo
yoluna dusulur, yuklenemezse SEBEP (aranan yol + istisna turu) BASILIR — bkz.
asagidaki "T4 YUKLEME" blogu (20 Agu 2026 canli bloker onarimi).

KABUL (calistirilabilir)
------------------------
  python3 tools/parti-kapisi.py --kendini-test
    OLCUMUN hala dogru oldugunu kanitlar (kovalar, defter, etiket cikarimi).

  python3 tools/tikayici-kaldirma-test.py
    🔴 TERS EKSEN: hicbir yuzeyin artik REDDETMEDIGINI **ve** teshisin
    KORUNDUGUNU kanitlar. AYRI DOSYADIR bilerek: kaldirma isi kendi
    bekcisini de susturmasin ([[fail-closed-kol-arkasindaki-kolu-maskeler]]).

  python3 tools/parti-kapisi.py --kontrol --ev MaCiT      (salt-okunur)
  python3 tools/parti-kapisi.py --t4-durum                (dagitim teshisi)

🔴 CIKIS KODU (--isci-kapi): **DAIMA 0**. Kapi artik hicbir cagriyi
   reddetmez; hukum `HUKUM=GECER` ya da `HUKUM=RAPOR` olarak stdout/stderr'de
   TASINIR. Kanca modunda da DAIMA 0 ve `permissionDecision: deny` HIC
   uretilmez — `_reddet` fonksiyonu SILINDI, yoruma alinmadi.
   Tek istisna `--t4-durum`: o bir TESHIS komutudur, kimsenin isini bloklamaz
   ve "T4 yuklenemedi" halini rc=2 ile bildirmeye DEVAM eder.
"""

import argparse
import importlib.util
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout


# ------------------------------------------------------------------------------
# T4 (parti-borc-kapisi.py) YUKLEME — TEK KAYNAK + FAIL-LOUD
# ------------------------------------------------------------------------------
# Dosya adi tireli; importlib ile yuklenir (repo geleneği:
# okan-kapisi-penceresi.py -> durgun-kalem-kapisi.py ayni deseni kullanir).
#
# 🔴 20 Agu 2026 — CANLI BLOKER ONARIMI (iki AYRI kusur):
#  (A) DAGITIM: bu kapi evlere `<ev>/.claude/parti-kapisi.py` olarak KOPYALANIR
#      (`mimar-kapi-kur.py --parti-kapisi --uygula`). Kopyanin YANINDA T4 YOKTUR
#      — "kardes dosya" tek basina yeterli DEGILDIR ve 20 Agu'da bes evin ucuz
#      kati (isci.sh) bu yuzden ölü kaldi. Ikinci bir T4 KOPYASI dagitmak TEK
#      KAYNAK ilkesini bozardi; onun yerine kardes yoksa KANONIK repo yoluna
#      dusulur. Aday listesi TEK yerdedir (`t4_adaylari`) — ikinci sabit yol YOK.
#  (B) SESSIZ YUTMA: eski surum `except Exception: return None` idi; T4
#      yuklenemeyince kapi yalnizca `N2B-OLCULEMEDI` basiyor, SEBEP (aranan yol
#      + istisna turu) hicbir yerde gorunmuyordu -> teshis imkansizdi. Artik her
#      deneme `<yol> -> <IstisnaTuru>: <mesaj>` olarak KAYDEDILIR ve hukum
#      satirinin yanindaki HATA satirinda BASILIR. `OLCULEMEDI` demek YETMEZ,
#      NEDEN olculemedigi yazilir. [[ucuz-isci-yesil-tablo-uydurur]]
#      [[aracin-teshis-cumlesi-olcum-degil]]
_BU_DIZIN = os.path.dirname(os.path.abspath(__file__))
_T4_ADI = "parti-borc-kapisi.py"
_T4_KANONIK = "/Users/okan/dev/pruvo/tools/" + _T4_ADI
_T4_YOLU = os.path.join(_BU_DIZIN, _T4_ADI)      # kardes aday (repo icindeyken)


def t4_adaylari(yollar=None):
    """T4'un aranacagi yollar, SIRAYLA. TEK KAYNAK — ikinci liste YOK.

    `yollar` verilirse aday kumesi TAMAMEN onunla degisir (hermetik mutant
    icin; uretimde verilmez).
    """
    if yollar:
        return [os.path.abspath(y) for y in yollar]
    adaylar = [os.path.abspath(_T4_YOLU)]
    if os.path.abspath(_T4_KANONIK) not in adaylar:
        adaylar.append(os.path.abspath(_T4_KANONIK))
    return adaylar


def _t4_yukle(yollar=None):
    """T4 modulunu yukler.

    Return: (mod|None, yuklenen_yol|None, hata|None). Hata METNI aranan HER
    yolu ve istisna TURUNU tasir (fail-loud).
    """
    denemeler = []
    for aday in t4_adaylari(yollar):
        try:
            if not os.path.isfile(aday):
                raise FileNotFoundError(aday)
            spec = importlib.util.spec_from_file_location("pruvo_t4_borc", aday)
            if spec is None or spec.loader is None:
                raise ImportError("spec/loader COZULEMEDI")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod, aday, None
        except Exception as e:
            denemeler.append("%s -> %s: %s" % (aday, type(e).__name__, e))
    return None, None, ("T4 (%s) YUKLENEMEDI — denenen %d yol: %s"
                        % (_T4_ADI, len(denemeler), " | ".join(denemeler)))


T4, T4_YOLU, T4_HATA = _t4_yukle()

# `t4=None` ACIKCA "T4 YOK" demektir (mutant/kabul kolu). Modul duzeyindeki
# T4'u miras almak icin arguman HIC verilmez -> asagidaki sentinel.
_MIRAS = object()


def _t4_coz(t4, t4_hata):
    """(t4, hata) ciftini normalize eder: sentinel -> modul duzeyindeki T4."""
    if t4 is _MIRAS:
        return T4, T4_HATA
    if t4 is None:
        return None, (t4_hata
                      or "T4 (%s) YUKLENEMEDI (cagiran t4=None verdi)" % _T4_ADI)
    return t4, None


# ---- sabitler -----------------------------------------------------------------
# Kol jetonlari — cikti satirinda ve mutant dogrulamada kullanilir. Kol ATIFI
# HUKUM satirindaki KOL= alaninda tasinir; her mutant YALNIZ kendi kolunu
# kirmizi yakmalidir (K182).
N2B_YENI_JETON       = "N2B-YENI"
N2B_SUREN_JETON      = "N2B-SUREN"
# 🔴 `N2B-RED` ADI KORUNDU, YETKISI KALKTI (11 Eyl 2026). Jeton bes evin
# gunluklerinde ve `n2b-dagitim-probu.py`de ARANIYOR; adi degistirmek o
# arayicilari sessizce korlestirirdi. Bu kol artik `HUKUM=RAPOR` uretir.
N2B_RED_JETON        = "N2B-RED"
N2B_OLCULEMEDI_JETON = "N2B-OLCULEMEDI"
# 🔴 K229 UCUNCU KOVA — `N2B-OLCULEMEDI`den AYRI jeton. Ayni metne indirgenirse
# ucuncu sinif ikinci kovaya yutulur ve olcememe "basari" gibi okunur.
N2B_DEFTER_YOK_JETON = "N2B-DEFTER-YOK"

# ==============================================================================
# 🔴 K345 (28 Agu 2026) — REDDIN SEBEBI IKI AYRI KOVADIR
# ==============================================================================
# OLCULEN ARIZA (mimar, iki kez): `echo "" | isci.sh ... tamir-x` cagrisi
# `KOL=N2B-RED` aldi ve red METNI 30 acik kalemi siralayip "yarim partine devam
# et" dedi. Sebep acik kalem DEGILDI — etiket okunamamisti. Iki kovali
# siniflama (MUAF / RED) ucuncu hali YUTTU ve okuyan YANLIS sebebi kapatmaya
# calisti ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
# Cozum: etiketi okunamayan cagri KENDI jetonunu + KENDI sebep kodunu alir.
# 🔴 11 Eyl: hukum artik RAPOR — ama UC AYRI KOVA ayrimi AYNEN KALDI. Kovalar
# birlesirse teshis yine yanlis sebebi gosterir; kaldirilan sey REDDETME
# yetkisidir, SINIFLANDIRMA degil.
N2B_ETIKET_OKUNAMADI_JETON = "N2B-ETIKET-OKUNAMADI"
# Asagidaki jeton hukum satirinda GORUNMEZ; mutant ATFININ kol ADIDIR
# (her mutant YALNIZ kendi kolunu kirmizi yakmali — K182).
N2B_ETIKET_CIKARIM_JETON = "N2B-ETIKET-CIKARIM"
# 🔴 K345-C (28 Agu 2026) — OKUMA ile BASLATMA AYRI KOLDUR.
# CANLI VAKA (mimar, ayni gun): `grep -n "kimi" .../isci.sh` -> `KOL=N2B-RED
# ACIK=30`. Komut hicbir is BASLATMIYOR; kapi yalnizca komut METNINDE
# sarmalayici adi gectigi icin "yeni parti" saydi ([[n2b-kapisi-dizge-olcer]]).
# Bedel tersine tesviktir: git-DISI kanit OKUMAK pahali, OLCMEMEK ucuz.
N2B_OKUMA_JETON = "N2B-OKUMA"

# Sebep KODLARI — hukum satirinin `SEBEP=` alaninda tasinir. Kod, KOL'dan
# AYRIDIR: KOL "hangi kol karar verdi", SEBEP "neden" der. Uc kovanin uc AYRI
# kodu vardir; ikisi ayni koda indirgenirse ucuncu sinif yeniden kaybolur.
SEBEP_ACIK_KALEM       = "ACIK_KALEM"
SEBEP_ETIKET_OKUNAMADI = "ETIKET_OKUNAMADI"
SEBEP_OLCULEMEDI       = "OLCULEMEDI"
SEBEP_DEFTER_YOK       = "DEFTER_YOK"
SEBEP_TEMIZ            = "TEMIZ"

# 🔴 11 EYL 2026 — MUTANT ENVANTERI DARALDI: **15 -> 9**.
# SILINEN ALTI mutant, TEK TEK sebebiyle (sayi sessizce dusmesin —
# [[batarya-kapsam-tabani-sayiyla-civilenir]]):
#   M3  "RED kolu oldurulur"      -> RED kolu ARTIK YOK; oldurulecek yetki yok.
#   M5  "muafiyet oldurulur"      -> MUAF kolu SILINDI (kacis yolu anlamsiz).
#   M6  "cagri yeri tarayicisi korlesir" \ ikisi de YALNIZ muafiyet
#   M7  "cagri yeri regresyonu"          / sozlesmesini olcuyordu.
#   M10 "muaf onek listesi ELLE yazilir" -> elle yazilacak liste kalmadi.
#   M12 "okunamayan etiket MUAF sayilir" -> gevsetilecek fail-closed yok.
# GERIYE KALAN 9 mutant OLCUMU korur: siniflandirma, defter kovalari,
# etiket cikarimi, okuma/baslatma ayrimi. Reddetme yetkisinin GERI
# GELMEDIGINI olcen kol AYRI dosyadadir (`tools/tikayici-kaldirma-test.py`).
MUTANT_HEDEF = {
    "M1": N2B_YENI_JETON,
    "M2": N2B_SUREN_JETON,
    "M4": N2B_OLCULEMEDI_JETON,
    # 🔴 CAKISMA COZUMU (K229 tazeleme, 20 Agu): K229 dalinda bu iki mutant
    # M6/M7 idi; main'de N4A ayni numaralari CAGRI-YERI kolu icin ALDI. Ayni ada
    # iki rol verilseydi mutant KENDI kolunu degil komsununkini oldururdu ve
    # "yasadi" cikan sonuc "kol saglam" diye OKUNURDU [[ad-iki-rolde-mutanti-golgeler]].
    # Bu yuzden K229'un mutantlari M8/M9'a TASINDI (davranis AYNI, ad AYRI):
    #   M8 = kol BOZULUR      -> defteri olmayan ev yine OLCULEMEDI kovasina duser
    #   M9 = kol BIRLESTIRILIR-> hukum GECER kalir ama JETON OLCULEMEDI'ye doner
    #                            (ucuncu kova KAYBOLUR; yalniz HUKUM'e bakan test
    #                            bunu GORMEZ — jeton kontrolu SART)
    "M8": N2B_DEFTER_YOK_JETON,
    "M9": N2B_DEFTER_YOK_JETON,
    # 🔴 K345:
    #   M11 etiket cikariminin BORU ONEKI normalizasyonu geri alinir
    #   M13 sebep kovalari BIRLESTIRILIR (ucuncu kova yutulur)
    "M11": N2B_ETIKET_CIKARIM_JETON,
    "M13": N2B_ETIKET_OKUNAMADI_JETON,
    # 🔴 K345-C — okuma/baslatma kolunun IKI ayri oldurme yolu:
    #   M14 okuma kolu KALDIRILIR  -> salt-okuma "yeni is" diye SINIFLANIR
    #   M15 baslatma "okuma" sayilir -> GERCEK baslatma yanlis SINIFLANIR
    #   (ikisi de artik kimseyi REDDETMEZ; bozulan sey TESHISIN dogrulugudur)
    "M14": N2B_OKUMA_JETON,
    "M15": N2B_OKUMA_JETON,
}

# ==============================================================================
# 🔴 K345 — SARMALAYICI DILBILGISI: TEK KAYNAK
# ==============================================================================
# ONCEDEN iki yerde yaziliydi: (a) `_ETIKET_INDEKS` sozlugu ayristiriciyi
# besliyordu, (b) arguman ADLARI yalnizca bir YORUM satirindaydi ve red metnine
# HIC ulasmiyordu. Sonuc: kapi dogru karar verirken red metni okuyana CALISAN
# CAGRI BICIMINI hic soylemedi; mimar dogru formu ancak KAYNAGI okuyarak buldu
# ([[kapi-red-metni-ikinci-kopyadir]]).
# Artik TEK tablo var: ayristiricinin ETIKET indeksi de, red metnindeki cagri
# bicimi de BURADAN turetilir. Tabloya bir arguman eklenirse metin KENDILIGINDEN
# degisir; degismezse K11 kontrolu KIRMIZI yanar.
SARMALAYICI_DIZINI = "/Users/okan/.claude/cron"
ETIKET_YERI = "<ETIKET>"
SARMALAYICI_ARGUMANLARI = {
    "isci.sh":    ("<MOTOR>", "<EV_KOKU>", "<SPEC.md>", ETIKET_YERI),
    "m3-isci.sh": ("<EV_KOKU>", "<SPEC.md>", ETIKET_YERI),
    # `parti-surucusu.sh` BILEREK YOK: argumansizdir, etiket govdesinde
    # GOMULUDUR ve cikarilamaz -> tablodan cozulemeyen sarmalayici
    # `ETIKET_OKUNAMADI` kovasina duser (fail-closed).
}


def dogru_cagri_bicimi():
    """Etiketi OKUNABILEN cagri sekilleri — `SARMALAYICI_ARGUMANLARI`dan TURER."""
    return ["%s/%s %s" % (SARMALAYICI_DIZINI, ad,
                          " ".join(SARMALAYICI_ARGUMANLARI[ad]))
            for ad in sorted(SARMALAYICI_ARGUMANLARI)]

# ==============================================================================
# 🔴 N4A CAGRI-YERI KOLU — 11 EYL 2026'DA SILINDI (yoruma alinmadi)
# ==============================================================================
# Bu blok `CAGRI_YERI_KAYNAKLARI` tablosunu, `CAGRI_YERI_TABANI` sayisini,
# `_PY_ETIKET_RE`/`_SH_ETIKET_RE` cikaricilarini ve `cagri_yeri_taramasi` /
# `cagri_yeri_hukmu` fonksiyonlarini tasiyordu. HEPSININ TEK ISI, silinen
# `MUAF_ETIKET_ONEKLERI` sozlesmesinin GERCEK cagri yerlerine bagli oldugunu
# dogrulamakti (20 Agu vakasi: `"ci-nobeti".startswith("nobet")` False donuyor,
# onarim hatti KENDI kapisindan RED yiyordu).
# Muafiyet, REDDETME YETKISININ bir kacis yoluydu. Yetki kalkinca kacis yolu da,
# onu olcen tarayici da konusuz kaldi. Ikisini de birakmak, bayatlayacak IKINCI
# BIR KURAL KOPYASI birakmak olurdu ([[kapi-red-metni-ikinci-kopyadir]]).
# 🔴 KAYIT: bu silme, K8 kontrolunu de goturdu. K8 bu turda ZATEN `KUSUR`
# durumdaydi (degisiklikten ONCE olculdu) — yani silinen sey YESIL bir nobetci
# DEGIL, konusu ortadan kalkmis KIRMIZI bir koldur.

# YENI IS BASLATAN yuzeyler (kanca modu, Bash komutu icinde aranir).
# 🔴 DAR TUTULUR: burada olmayan HER komut `N2B-SUREN` sayilir ve GECER.
# Genisletmek "yarim is kesilmez" invaryantini kirar (M2 mutanti bunu olcer).
YENI_IS_DESENLERI = (
    re.compile(r"/\.claude/cron/isci\.sh(\s|$)"),
    re.compile(r"/\.claude/cron/m3-isci\.sh(\s|$)"),
    re.compile(r"/\.claude/cron/[A-Za-z0-9._-]*parti-surucusu\.sh(\s|$)"),
)

# Proje dizini oneki (Claude'un yol kodlamasi: `/` -> `-`).
PROJE_ONEKI = "/Users/okan/.claude/projects/"

# EV cozumunde belirsizlik olursa (ayni proje dizinini paylasan evler)
# deterministik tercih sirasi. KraL depo sahibidir; BaBa/ORTAK onun icinde oturur.
EV_TERCIH_SIRASI = ("KraL", "MaCiT", "ArTisT", "HocA", "TeKiN", "BaBa", "ORTAK")

RC_GECER = 0
# 🔴 11 Eyl 2026 — `RC_RED` SILINDI. Kapinin reddetme yetkisi kalkti; geriye
# sifir-disi bir cikis kodu birakmak, ilk `if rc -ne 0` yazan cagiranin
# tikayiciyi SESSIZCE geri kurmasina yeterdi ([[yeni-hal-cozucunun-varsayilan-
# kovasina-duser]]). `--isci-kapi` DAIMA RC_GECER doner.
# `RC_OLCULEMEDI` YALNIZ `--t4-durum` teshis komutunda yasar: o komut kimsenin
# isini baslatmaz, "T4 yuklenemedi" halini bildirmesi bir TIKAYICI degildir.
RC_OLCULEMEDI = 2

# HUKUM sozlugu — iki deger. `RED` ARTIK URETILMEZ.
HUKUM_GECER = "GECER"
HUKUM_RAPOR = "RAPOR"


# ------------------------------------------------------------------------------
# EV COZUMU — T4'un EV_DIZIN'inden TURETILIR (ucuncu tablo YOK)
# ------------------------------------------------------------------------------
def _proje_dizini(depo_kok):
    """Bir depo kokunu Claude proje dizinine cevirir: `/a/b` -> `<oneki>-a-b`."""
    mutlak = os.path.abspath(depo_kok).rstrip("/")
    return PROJE_ONEKI + mutlak.replace("/", "-")


def ev_coz(depo_kok, *, t4=_MIRAS, t4_hata=None):
    """Bir depo kokunden (worktree dahil) EV adini turetir.

    Worktree'ler icin ust dizinlere yurunur: `.../pruvo/.claude/worktrees/x`
    once denenir, eslesmezse `.../pruvo` bulunana kadar yukari cikilir.

    Return: (ev|None, hata|None)
    """
    t4, hata_t4 = _t4_coz(t4, t4_hata)
    if t4 is None:
        return None, hata_t4
    # 🔴 K361: EV_DIZIN artik repo DISINDAN yuklenir (`~/.claude/cron/evler.json`)
    # ve OKUNAMAZSA **None**'dir (bos dict DEGIL). Bos/None tablo "hicbir ev yok"
    # -> her kok cozulemez -> fail-closed. Sebep METNI tasinir (fail-loud).
    harita = getattr(t4, "EV_DIZIN", None)
    if not harita:
        return None, ("T4 EV_DIZIN OLCULEMEDI/bos: %s"
                      % (getattr(t4, "EV_HARITASI_HATA", None) or "bos tablo"))
    ters = {}
    for ev, dizin in harita.items():
        ters.setdefault(os.path.abspath(dizin).rstrip("/"), []).append(ev)
    if not ters:
        return None, "T4 EV_DIZIN bos"

    aday = os.path.abspath(depo_kok).rstrip("/")
    gorulen = 0
    while aday and aday != "/" and gorulen < 32:
        gorulen += 1
        evler = ters.get(_proje_dizini(aday))
        if evler:
            for tercih in EV_TERCIH_SIRASI:
                if tercih in evler:
                    return tercih, None
            return sorted(evler)[0], None
        aday = os.path.dirname(aday)
    return None, "depo koku bilinen bir eve cozulemedi: %s" % depo_kok


# ------------------------------------------------------------------------------
# CAGRI SINIFLANDIRMASI — N2B-YENI / N2B-SUREN / N2B-OKUMA
# ------------------------------------------------------------------------------
# 🔴 11 Eyl 2026: bu uc kol artik hicbir cagriyi KESMIYOR. Ayrim TESHIS icin
# durur — hukum satirindaki `KOL=` alani "bu cagri ne yapiyordu" sorusunu
# cevaplar. Ayrim silinirse `isci.log`'da neyin sayildigi da olculemez olur.


# ------------------------------------------------------------------------------
# K345-C — OKUMA ↔ BASLATMA AYRIMI
# ------------------------------------------------------------------------------
# Sarmalayiciyi FIILEN CALISTIRAN sekiller. Liste DAR tutulur: burada olmayan
# her sey "okuma" degil, once DIREKT CAGRI testinden gecer.
_BASLATICI_SARMALAYICILAR = ("env", "nohup", "time", "sudo", "command", "exec",
                             "stdbuf", "caffeinate", "xargs", "parallel",
                             "watch", "setsid", "doas")
_YORUMLAYICILAR = ("sh", "bash", "zsh", "ksh", "dash", "ash", "fish",
                   "python", "python3", "perl", "ruby", "node", "eval",
                   "source", ".")
# Komut ikamesi / geri tirnak: govde CALISTIRILIR ve icerigi ayristirilamaz.
_IKAME_RE = re.compile(r"\$\(|`|\$\{")
# Pipeline ayraclari (boru DEGIL — boru pipeline'in ICINDEDIR).
_PIPELINE_AYRAC_RE = re.compile(r"&&|\|\||;|\n")


def _sarmalayici_mi(token):
    """Bir token, YENI_IS_DESENLERI'nin tanidigi bir sarmalayici yolu mu?"""
    if not token:
        return False
    return any(d.search(token) or d.search(token + " ")
               for d in YENI_IS_DESENLERI)


def _segment_tokenlari(segment):
    """Segmenti token'lara ayirir. Ayristirilamazsa None (= fail-closed)."""
    try:
        return shlex.split(segment)
    except ValueError:
        return None


def yeni_is_hukmu(komut, *, mutant=None):
    """Bir Bash komutunun UC halinden hangisi? (SUREN / OKUMA / YENI)

    🔴 K345-C: `N2B-OKUMA` UCUNCU KOVADIR, `N2B-SUREN`e indirgenmez. Ikisi de
    GECER verir ama AYRI sebeple: SUREN = "sarmalayici hic gecmiyor",
    OKUMA = "sarmalayici geciyor ama ARGUMAN olarak; is BASLAMIYOR". Ayni
    jetona indirgenirse okuma kolunun fiilen calisip calismadigi olculemez
    ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).

    🔴 FAIL-CLOSED: hangi kolda oldugu OKUNAMIYORSA hukum YENI'dir (= kapiya
    tabi). Gevsetme yalniz ISPATLANMIS okuma icindir.

    Return: ("SUREN"|"OKUMA"|"YENI", sebep)
    """
    if not isinstance(komut, str) or not komut.strip():
        return "SUREN", "komut bos"
    if not any(d.search(komut) for d in YENI_IS_DESENLERI):
        return "SUREN", "sarmalayici komutta HIC gecmiyor"
    if mutant == "M14":
        # OKUMA KOLU KALDIRILIR — canli vaka geri gelir (salt-okuma RED yer).
        return "YENI", "M14: okuma kolu yok"
    if mutant == "M15":
        # 🔴 SIZMA MUTANTI: baslatma "okuma" sayilir. KIRMIZI YANMALIDIR.
        return "OKUMA", "M15: baslatma okuma sayildi"
    if _IKAME_RE.search(komut):
        return "YENI", ("komut ikamesi/geri tirnak var — govde ayristirilamaz "
                        "(fail-closed)")

    for pipeline in _PIPELINE_AYRAC_RE.split(komut):
        if not any(d.search(pipeline) for d in YENI_IS_DESENLERI):
            continue
        segmentler = pipeline.split("|")
        pipeline_sarmalayici_gordu = False
        for segment in segmentler:
            for ayrac in _YONLENDIRME_AYRACLARI:
                i = segment.find(ayrac)
                if i >= 0:
                    segment = segment[:i]
            tokenlar = _segment_tokenlari(segment)
            if tokenlar is None:
                return "YENI", "segment ayristirilamadi (fail-closed): %r" % (
                    segment.strip()[:60])
            if not tokenlar:
                continue
            segmentte_sarmalayici = any(_sarmalayici_mi(t) for t in tokenlar)
            # ortam atamalarini (`X=Y`) atla — komut adi ONLARDAN SONRA gelir
            i = 0
            while i < len(tokenlar) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=",
                                                 tokenlar[i]):
                i += 1
            if i >= len(tokenlar):
                continue
            komut_adi = os.path.basename(tokenlar[i])
            if _sarmalayici_mi(tokenlar[i]):
                return "YENI", "DIREKT CAGRI: segmentin komutu sarmalayici"
            if (komut_adi in _BASLATICI_SARMALAYICILAR
                    and segmentte_sarmalayici):
                return "YENI", ("BASLATICI SARMALAYICI (%s) ayni segmentte "
                                "sarmalayiciyi calistiriyor" % komut_adi)
            if komut_adi in _YORUMLAYICILAR and (segmentte_sarmalayici
                                                 or pipeline_sarmalayici_gordu):
                return "YENI", ("YORUMLAYICI (%s) sarmalayici govdesini "
                                "calistirabilir" % komut_adi)
            if segmentte_sarmalayici:
                pipeline_sarmalayici_gordu = True
    return "OKUMA", ("sarmalayici yalniz ARGUMAN olarak geciyor — hicbir "
                     "segment onu CALISTIRMIYOR")


def yeni_is_mi(komut, *, mutant=None):
    """Bir Bash komutu YENI is baslatiyor mu? (N2B-YENI / N2B-SUREN ayrimi)

    🔴 Fail-OPEN yon BILEREK: taninmayan komut `SUREN` sayilir ve GECER.
    Bu kapi yeni is baslatmayi durdurur; suren/yarim isi DURDURMAZ. Yanlis
    pozitif burada YARIM IS KESER — kabul edilemez zarar (Okan'in vakasi).
    🔴 K345-C: SALT-OKUMA da yeni is DEGILDIR (bkz. `yeni_is_hukmu`).
    """
    if mutant == "M1":
        return False          # yeni-is tanima oldurulur -> parti hep gecer
    if mutant == "M2":
        return True           # her komut yeni-is sayilir -> YARIM IS KESILIR
    return yeni_is_hukmu(komut, mutant=mutant)[0] == "YENI"


# ------------------------------------------------------------------------------
# KARAR FONKSIYONU — iki yuzey de BURADAN gecer
# ------------------------------------------------------------------------------
def parti_karari(ev_koku, etiket, *, esik=None, koku_root=None, mutant=None,
                 t4=_MIRAS, t4_hata=None, ev=None):
    """Bir YENI is basvurusunu hukme baglar.

    `ev` dogrudan verilirse yol cozumu ATLANIR (`--kontrol` kolu); aksi halde
    `ev_koku`ndan T4'un EV_DIZIN'i uzerinden TURETILIR.

    Return: {"HUKUM": "GECER"|"RED", "KOL", "EV", "ACIK", "KALEMLER",
             "KABUL_KOMUTU", "SEBEP", "HATA"}
    """
    t4, hata_t4 = _t4_coz(t4, t4_hata)
    sonuc = {"HUKUM": HUKUM_RAPOR, "KOL": N2B_OLCULEMEDI_JETON, "EV": None,
             "ACIK": 0, "KALEMLER": [], "KABUL_KOMUTU": None,
             "SEBEP": None, "SEBEP_KODU": SEBEP_OLCULEMEDI, "HATA": None,
             "ETIKET": etiket}

    # 🔴 11 Eyl 2026 — MUAF KOLU BURADAYDI, SILINDI.
    # `muaf_etiket_mi(etiket)` dogruysa hemen `GECER`/`N2B-MUAF` donuyordu.
    # O kol, RED yetkisinden KACIS yoluydu; yetki kalkinca kacacak bir sey
    # kalmadi. Muaf etiketli bir cagri artik oteki cagrilarla AYNI olcumden
    # gecer ve ayni RAPOR'u alir — tek fark, kimse kesilmiyor.

    # 🔴 K345 — UCUNCU KOVA: ETIKET OKUNAMADI.
    # Bos etiket zaten MUAF DEGILDI (yukaridaki kol onu gecirmez); ONCEDEN
    # sessizce "muaf olmayan etiket" kovasina dusuyor ve acik kalem sayimina
    # gidiyordu. Sonuc: red metni YANLIS SEBEBI gosteriyordu (30 kalem
    # siralaniyordu, oysa kusur etiketteydi) — ve kalemsiz evde HIC olcum
    # yapilmadan GECIYORDU (fail-OPEN sizintisi). Artik KENDI kovasi var:
    # hukum RED (fail-closed KORUNUR), sebep ETIKET_OKUNAMADI.
    if not (etiket or "").strip():
        if mutant == "M13":
            # KOVA BIRLESTIRME MUTANTI: ucuncu kova ikinciye indirgenir.
            # HUKUM ayni kalabilir (RAPOR) — yalniz HUKUM'e bakan bir test bunu
            # GORMEZ; JETON + SEBEP KODU kontrolu SART ([[M9 dersi]]).
            sonuc["KOL"] = N2B_RED_JETON
            sonuc["SEBEP_KODU"] = SEBEP_ACIK_KALEM
            sonuc["SEBEP"] = "M13: etiket kovasi acik-kalem kovasina yutuldu"
        else:
            sonuc["KOL"] = N2B_ETIKET_OKUNAMADI_JETON
            sonuc["SEBEP_KODU"] = SEBEP_ETIKET_OKUNAMADI
            sonuc["SEBEP"] = (
                "%s cagrinin ETIKETI okunamadi (yok / gomulu / belirsiz) — "
                "okunan etiket=%r. Bu bir RED DEGIL, TESHISTIR: cagri GECTI. "
                "Etiket okunamadigi icin acik kalem sayimi bu kovada YAPILMAZ."
                % (N2B_ETIKET_OKUNAMADI_JETON, etiket or ""))
        if ev is None and t4 is not None:
            ev, _h = ev_coz(ev_koku, t4=t4)
        sonuc["EV"] = ev
        if mutant == "M13":
            # birlestirilmis kovada acik kalem sayisi da basilirdi
            sonuc["KABUL_KOMUTU"] = kabul_komutu(ev)
        return sonuc

    if t4 is None:
        # 🔴 FAIL-LOUD: `OLCULEMEDI` demek YETMEZ — aranan YOL + istisna TURU
        # hukum satirinin yanindaki HATA satirinda GORUNUR (20 Agu bloker).
        sonuc["HATA"] = "%s %s" % (N2B_OLCULEMEDI_JETON, hata_t4)
        if mutant == "M4":
            sonuc["HUKUM"] = "GECER"          # FAIL-OPEN mutanti
            sonuc["KOL"] = N2B_SUREN_JETON
        return sonuc

    hata = None
    if ev is None:
        ev, hata = ev_coz(ev_koku, t4=t4)
    sonuc["EV"] = ev
    # 🔴 K361: EV_BILINEN OLCULEMEDIYSE None'dir — `in` TypeError atardi.
    # Fail-closed: harita yoksa HIC bir ev bilinmiyor sayilir.
    _bilinen = getattr(t4, "EV_BILINEN", None)
    if ev is None or not _bilinen or ev not in _bilinen:
        if _bilinen is None:
            hata = hata or ("EV_HARITASI OLCULEMEDI: %s"
                            % (getattr(t4, "EV_HARITASI_HATA", None) or "-"))
        sonuc["HATA"] = "%s %s" % (N2B_OLCULEMEDI_JETON, hata or "EV bilinmiyor")
        if mutant == "M4":
            sonuc["HUKUM"] = "GECER"
            sonuc["KOL"] = N2B_SUREN_JETON
        return sonuc

    esik = t4.DEFAULT_ESIK if esik is None else esik
    borc = t4.parti_engeli_var_mi(ev, esik, koku_root=koku_root)
    sonuc["ACIK"] = borc["ACIK_SAYISI"]

    if borc["OLCULEMEDI"]:
        # 🔴 K229 UCUNCU KOVA — defter DOSYASI hic YOK (ev defter gelenegini
        # benimsememis). GECER, ama SESSIZ DEGIL: kendi jetonu hukum satirinda
        # GORUNUR ve `n2b-dagitim-probu.py` onu AYRI kovada SAYAR.
        # Sinir: defter VAR ama okunamadi (bos/bozuk/IO) ise buraya GIRILMEZ —
        # o hal fail-closed RED olarak KALIR (bos defter = olculmemis sifir).
        if borc.get("DEFTER_YOK") and mutant != "M8":
            sonuc["HUKUM"] = "GECER"
            sonuc["KOL"] = (N2B_OLCULEMEDI_JETON if mutant == "M9"
                            else N2B_DEFTER_YOK_JETON)
            sonuc["SEBEP_KODU"] = SEBEP_DEFTER_YOK
            sonuc["SEBEP"] = (
                "%s ev=%s defter DOSYASI yok (%s) — defter gelenegini hic "
                "benimsememis evi o gelenekle bloklamak KILITLENMEDIR; kalem "
                "olcumu YOK, bu satir o olcumun EKSIKLIGINI ilan eder."
                % (N2B_DEFTER_YOK_JETON, ev, borc["DEFTER_YOLU"] or "-"))
            return sonuc
        sonuc["HATA"] = "%s %s" % (N2B_OLCULEMEDI_JETON, borc["HATA"])
        if mutant == "M4":
            sonuc["HUKUM"] = "GECER"
            sonuc["KOL"] = N2B_SUREN_JETON
        return sonuc

    if borc["RED"]:
        # 🔴 T4 hala `RED` diyor — T4 BORC OLCERDIR, hukum organi DEGILDIR.
        # Onun `RED`i "bu evde acik kalem var" olgusudur; bu kapinin hukmu
        # artik RAPOR'dur. Ikisini ayirmak, borcu olcen kaynagi degistirmeden
        # yaptirimi kaldirmayi mumkun kilar.
        kalemler, _okundu, _h = t4.acik_kalem_listesi(borc["DEFTER_YOLU"] or "")
        sonuc["KALEMLER"] = kalemler
        sonuc["KOL"] = N2B_RED_JETON
        sonuc["HUKUM"] = HUKUM_RAPOR
        sonuc["SEBEP_KODU"] = SEBEP_ACIK_KALEM
        sonuc["KABUL_KOMUTU"] = kabul_komutu(ev)
        sonuc["SEBEP"] = borc["RED_SEBEBI"]
        return sonuc

    sonuc["HUKUM"] = HUKUM_GECER
    sonuc["KOL"] = N2B_SUREN_JETON
    sonuc["SEBEP_KODU"] = SEBEP_TEMIZ
    sonuc["SEBEP"] = borc["GECER_MESAJI"]
    return sonuc


def kabul_komutu(ev):
    """Kalemi kapatinca YESILE donmeyi kanitlayan calistirilabilir komut.

    🔴 YUKLENEN T4'un yolunu basar: enjekte kopyada (`<ev>/.claude/`) kardes
    dosya YOKTUR, oradaki `_BU_DIZIN` yolu CALISMAYAN bir komut uretirdi.
    """
    return ("python3 %s --ev %s" % (T4_YOLU or _T4_KANONIK, ev))


# Rapor metnindeki TURETILMIS bloklarin sinir dizgeleri. K11 kontrolu metni bu
# sinirlarla parcalayip turetilmis ciktiya BIREBIR esitler; sinir tekil degilse
# hukum `OLCULEMEDI` = KIRMIZI (fail-closed) — yoksa metin yeniden yazildiginda
# kol sessizce yesile donerdi ([[kapi-red-metni-ikinci-kopyadir]]).
# 🔴 `RED_METNI_ONEK_SINIRI` SILINDI: bastigi liste (`MUAF_ETIKET_ONEKLERI`)
# artik yok. Sinir dizgesini kaynaksiz birakmak, iki yonlu esitligi bos kume
# uzerinde "gecer" yapan olu bir nobetci birakirdi
# ([[grep-sifir-nobetcisi-yasak-kaydinda-oludur]]).
RED_METNI_CAGRI_BASLIGI = ("GECEN CAGRI BICIMI (kaynaktan TURETILDI — bu "
                           "metinde ikinci liste YOKTUR):")
RED_METNI_CAGRI_ONEKI = "  $ "


def red_metni(sonuc, *, mutant=None):
    """RAPOR gerekcesinin insan-okur govdesi.

    🔴 ADI `red_metni` KALDI, ICERIGI REDDETMIYOR. Fonksiyon adi bes evin
    testlerinde ve `n2b-dagitim-probu.py`de cagriliyor; yeniden adlandirmak
    okuyuculari sessizce korlestirirdi. Basilan metin artik "REDDEDILDI"
    demez — cagri GECMISTIR, bu satirlar TESHISTIR.

    🔴 K345 — bu metin iki seyi birden tasir:
      (1) SEBEP AYRIMI: `ACIK_KALEM` ile `ETIKET_OKUNAMADI` **AYRI SATIRLARDIR**
          ve hangisinin atesledigi isaretlenir. Onceden tek gerekce vardi ve
          etiketi okunamayan bir cagri YANLIS kusuru kapatmaya calisiyordu.
      (2) CALISAN CAGRI BICIMI — `SARMALAYICI_ARGUMANLARI`den TURETILIR,
          ELLE YAZILMAZ; K11 kontrolu iki yonlu esitlikle olcer.
    """
    kod = sonuc.get("SEBEP_KODU") or "-"
    satirlar = []
    satirlar.append("N2B PARTI KAPISI — RAPOR (ev=%s · sebep=%s). "
                    "🔴 CAGRI KESILMEDI." % (sonuc["EV"], kod))
    satirlar.append("Bu satirlar bir RED DEGIL, bir OLCUMDUR (Okan emri, "
                    "11 Eyl 2026: 'tum tikayicilari kaldir'). Karar SENIN.")

    # --- SEBEP AYRIMI: IKI KOVA, IKI AYRI SATIR ---------------------------
    def _im(bu_kod):
        return "→ " if kod == bu_kod else "  "
    satirlar.append(
        "%sSEBEP[%s]: bu evde acik 🔧 kalem VAR (acik=%d) — yarim partini "
        "KAPAT, sonra yenisini ac."
        % (_im(SEBEP_ACIK_KALEM), SEBEP_ACIK_KALEM, sonuc["ACIK"]))
    satirlar.append(
        "%sSEBEP[%s]: cagrinin ETIKETI okunamadi (yok / gomulu / belirsiz) — "
        "okunan etiket=%r. Acik kalem sayimi bu kovada YAPILMAZ."
        % (_im(SEBEP_ETIKET_OKUNAMADI), SEBEP_ETIKET_OKUNAMADI,
           sonuc.get("ETIKET") or ""))

    if kod == SEBEP_ACIK_KALEM:
        if sonuc["KALEMLER"]:
            satirlar.append("ACIK KALEMLER:")
            for k in sonuc["KALEMLER"]:
                satirlar.append("  - %s [%s] %s"
                                % (k["kimlik"], k["durum"], k["is"]))
        else:
            satirlar.append("ACIK KALEMLER: (kimlik cozulemedi — defteri elle ac)")
    satirlar.append("kabul: %s" % (sonuc["KABUL_KOMUTU"] or "-"))
    satirlar.append("(Kalemi kapatmak HALA dogru istir — ama artik SARTI "
                    "DEGILDIR; bu kapi kilit DEGIL, sayactir.)")

    # --- TURETILMIS BLOK: CALISAN CAGRI YOLU ------------------------------
    satirlar.append(RED_METNI_CAGRI_BASLIGI)
    for bicim in dogru_cagri_bicimi():
        satirlar.append(RED_METNI_CAGRI_ONEKI + bicim)
    satirlar.append(
        "ETIKET NOTU: etiket artik hicbir muafiyet vermez — kesilen cagri YOK, "
        "dolayisiyla muaf tutulacak bir sey de yok. Etiket YALNIZ bu raporun "
        "ve `isci.log` sayiminin okunabilirligi icindir.")
    return "\n".join(satirlar)


def hukum_satiri(sonuc):
    """Makine-okur tek satir. Kabul testleri BU satiri arar.

    🔴 K345: `SEBEP=` alani SONA EKLENDI (mevcut alanlarin sirasi/adi
    DEGISMEDI — eski okuyucular kirilmaz). Kovalar AYRI satir basar:
    `KOL=N2B-RED ... SEBEP=ACIK_KALEM` ·
    `KOL=N2B-ETIKET-OKUNAMADI ... SEBEP=ETIKET_OKUNAMADI` ·
    `KOL=N2B-SUREN ... SEBEP=TEMIZ`.
    🔴 `HUKUM=` alani artik yalniz `GECER` ya da `RAPOR` olur. `RED` degeri
    HIC URETILMEZ; bir gunlukte gorulurse o satir BAYAT bir kopyadan gelmistir.
    """
    kalem = ",".join(k["kimlik"] for k in sonuc["KALEMLER"]) or "-"
    return "N2B HUKUM=%s KOL=%s EV=%s ACIK=%d KALEM=%s SEBEP=%s" % (
        sonuc["HUKUM"], sonuc["KOL"], sonuc["EV"] or "-", sonuc["ACIK"], kalem,
        sonuc.get("SEBEP_KODU") or "-")


# ------------------------------------------------------------------------------
# K345 — RED METNI TURETIM PROBU (K11'in olcen govdesi)
# ------------------------------------------------------------------------------
def red_metni_turetim_hukmu(*, mutant=None):
    """Rapor metnindeki TURETILMIS blogu kaynaga BIREBIR esitler.

    🔴 IKI YONLU: `makine ⊆ metin` YETMEZ — `metin ⊆ makine` de olculur, yoksa
    metin makinenin izin VERMEDIGI bir seyi vaat edebilir ve nobetci susar
    ([[kapi-red-metni-ikinci-kopyadir]] 28 Agu eki).
    🔴 Sinir dizgesi TEKIL degilse hukum `OLCULEMEDI` = KIRMIZI (fail-closed).

    🔴 11 Eyl 2026 — IKI AYAK SILINDI: (a) muaf-onek blogu ve (c) elle ikinci
    kopya sayimi. Ikisi de `MUAF_ETIKET_ONEKLERI`yi olcuyordu; o liste artik
    YOK. Kalan TEK ayak — CALISAN CAGRI BICIMI — degerini KORUR: rapor metni
    okuyana etiketi okunabilen cagri seklini SOYLEMEK zorundadir, yoksa mimar
    dogru formu ancak KAYNAGI okuyarak bulur (28 Agu'nun dogus vakasi).

    Return: {"HUKUM": "GECER"|"RAPOR"|"OLCULEMEDI", "IHLAL": [...]}
    """
    ornek = {"HUKUM": HUKUM_RAPOR, "KOL": N2B_RED_JETON, "EV": "MaCiT",
             "ACIK": 30,
             "KALEMLER": [{"kimlik": "K901", "durum": "🔧", "is": "ornek"}],
             "KABUL_KOMUTU": kabul_komutu("MaCiT"),
             "SEBEP_KODU": SEBEP_ACIK_KALEM, "SEBEP": None, "HATA": None,
             "ETIKET": "parti-surucusu"}
    metin = red_metni(ornek, mutant=mutant)
    satirlar = metin.splitlines()
    ihlal = []

    # CAGRI BICIMI BLOGU — sinir TEKIL mi?
    baslik_indeksleri = [i for i, s in enumerate(satirlar)
                         if s == RED_METNI_CAGRI_BASLIGI]
    if len(baslik_indeksleri) != 1:
        return {"HUKUM": "OLCULEMEDI",
                "IHLAL": ["cagri-bicimi basligi TEKIL DEGIL (adet=%d)"
                          % len(baslik_indeksleri)]}
    blok = []
    for s in satirlar[baslik_indeksleri[0] + 1:]:
        if not s.startswith(RED_METNI_CAGRI_ONEKI):
            break
        blok.append(s[len(RED_METNI_CAGRI_ONEKI):])
    if blok != dogru_cagri_bicimi():
        ihlal.append("cagri bicimi: metin=%r != turetilen=%r"
                     % (blok, dogru_cagri_bicimi()))

    # 🔴 TERS YON (kaldirmanin KENDI nobetcisi): metin bir daha "REDDEDILDI"
    # ya da "fail-closed RED" vaat ETMEMELIDIR. Bayat bir vaat, okuyani
    # olmayan bir kilidi acmaya calismaya yollar.
    for s in satirlar:
        if "REDDEDIL" in s.upper() or "FAIL-CLOSED RED" in s.upper():
            ihlal.append("BAYAT RED VAADI metinde duruyor: %r" % s[:80])

    return {"HUKUM": HUKUM_RAPOR if ihlal else HUKUM_GECER, "IHLAL": ihlal}




# ------------------------------------------------------------------------------
# YUZEY 1: --isci-kapi (isci.sh govdesinden; CRON'u da kapsar)
# ------------------------------------------------------------------------------
def isci_kapi(motor, ev_koku, spec, etiket, *, esik=None, koku_root=None,
              mutant=None, t4=_MIRAS, t4_hata=None):
    """isci.sh'in cagirdigi kol. 🔴 rc DAIMA 0 — bu kol artik REDDETMEZ.

    ONCEDEN: `RED` -> rc=1, `OLCULEMEDI` -> rc=2 ve `isci.sh` orada `exit 3`
    ile DURUYORDU. Okculen bedel (11 Eyl): kesilen cagri LOGLANMIYORDU,
    `grep -c "N2B" ~/.claude/cron/isci.log` = 0 ve "kimse m3 kullanamiyor"
    sikayeti uc turdur olculemedi.
    SIMDI: ayni teshis AYNI alanlarla stderr'e yazilir, hukum satiri
    stdout'a gider ve cagri GECER. Sayi kaybolmaz, cagri kesilmez.
    """
    sonuc = parti_karari(ev_koku, etiket, esik=esik, koku_root=koku_root,
                         mutant=mutant, t4=t4, t4_hata=t4_hata)
    if sonuc["HUKUM"] == HUKUM_RAPOR:
        if sonuc["KOL"] == N2B_OLCULEMEDI_JETON:
            sys.stderr.write((sonuc["HATA"] or N2B_OLCULEMEDI_JETON) + "\n")
        else:
            sys.stderr.write(red_metni(sonuc) + "\n")
        # 🔴 Hukum satiri IKI yerde birden: stderr TESHIS akisi icin, stdout
        # ise `isci.sh`in gunluge aktardigi akis. Yalniz stderr'e yazilsaydi
        # `isci.log`'daki N2B sayimi YINE sifir kalirdi — bugunku arizanin ta
        # kendisi ([[tuketici-yazilirken-tum-okuyucular-sayilir]]).
        sys.stderr.write(hukum_satiri(sonuc) + "\n")
        sys.stdout.write(hukum_satiri(sonuc) + "\n")
        return RC_GECER
    # 🔴 K229: GECER ama SESSIZ DEGIL — ucuncu kova gerekcesini isci.sh
    # gunlugune de yazar (jeton zaten hukum satirinda).
    if sonuc["KOL"] == N2B_DEFTER_YOK_JETON and sonuc["SEBEP"]:
        sys.stderr.write(sonuc["SEBEP"] + "\n")
    sys.stdout.write(hukum_satiri(sonuc) + "\n")
    return RC_GECER


# ------------------------------------------------------------------------------
# YUZEY 2: --kanca (PreToolUse)
# ------------------------------------------------------------------------------
# 🔴 11 EYL 2026 — `_reddet()` SILINDI (yoruma ALINMADI).
# Fonksiyon `permissionDecision: "deny"` JSON'u basiyordu; bu kapinin TEK
# tikayici yuzeyi oydu. Yorum satiri olarak birakmak, "bir satiri ac" kadar
# kolay bir geri donus yolu birakirdi; Okan'in emri tam da bu tekrarin
# bitmesiydi ("tekrar ettirme"). Kapi artik JSON'a HIC yazmaz — stdout'a
# "allow" basmak da yanlis olurdu, cunku diger kancalarin ve izin katmaninin
# kararini EZERDI.


def kanca(girdi, *, esik=None, koku_root=None, mutant=None, t4=_MIRAS,
          t4_hata=None):
    """PreToolUse girdisini OLCUME baglar. DAIMA rc=0, DAIMA gecirir.

    🔴 Bu fonksiyon `deny` URETEMEZ: uretecek fonksiyon SILINDI. Teshis
    stderr'e yazilir; stdout'a hicbir sey yazilmaz (bos stdout = kapi karara
    KARISMIYOR demektir).
    """
    tool_name = girdi.get("tool_name") or ""
    if tool_name != "Bash":
        return 0                                  # kapsam disi — sessiz gec
    komut = (girdi.get("tool_input") or {}).get("command") or ""

    hal, hal_sebebi = ("YENI", "-")
    if mutant == "M1":
        hal = "SUREN"
    elif mutant == "M2":
        hal = "YENI"
    else:
        hal, hal_sebebi = yeni_is_hukmu(komut, mutant=mutant)
    if hal == "SUREN":
        # 🔴 N2B-SUREN: yeni is DEGIL. Suren/yarim is ASLA kesilmez.
        return 0
    if hal == "OKUMA":
        # 🔴 K345-C UCUNCU KOVA: GECER ama SESSIZ DEGIL — kolun fiilen
        # calistigi ancak bu satirdan olculebilir (kablolanmamis kol bir
        # mesajdir → [[kapinin-menzili-cagri-yeridir]]).
        sys.stderr.write("%s %s\n" % (N2B_OKUMA_JETON, hal_sebebi))
        return 0

    ev_koku = girdi.get("cwd") or ""
    etiket = _etiket_cikar(komut, mutant=mutant)
    sonuc = parti_karari(ev_koku, etiket, esik=esik, koku_root=koku_root,
                         mutant=mutant, t4=t4, t4_hata=t4_hata)
    if sonuc["HUKUM"] == HUKUM_RAPOR:
        # 🔴 ESKIDEN BURASI `_reddet(...)` IDI. Artik AYNI metin, AYNI
        # alanlarla stderr'e gider ve cagri GECER. Teshis SUSTURULMAZ:
        # susturmak, kaldirmanin bedelini olculemez kilardi.
        if sonuc["KOL"] == N2B_OLCULEMEDI_JETON:
            sys.stderr.write("%s\n" % (sonuc["HATA"] or N2B_OLCULEMEDI_JETON))
        else:
            sys.stderr.write("%s\n" % red_metni(sonuc))
        sys.stderr.write("%s\n" % hukum_satiri(sonuc))
        return 0
    # 🔴 K229: kanca yuzeyinde GECER = ciktisiz izin (stdout'a JSON YAZILMAZ;
    # "allow" basmak diger kancalari/izin katmanini EZERDI). Ucuncu kova yine de
    # SESSIZ DEGIL: gerekce + hukum satiri stderr'e (karara etkisi YOK) yazilir.
    if sonuc["KOL"] == N2B_DEFTER_YOK_JETON:
        sys.stderr.write("%s\n%s\n" % (sonuc["SEBEP"] or N2B_DEFTER_YOK_JETON,
                                       hukum_satiri(sonuc)))
    return 0


# Sarmalayici adindan SONRAKI tum argumanlari yakalar; ETIKET kacinci
# arguman oldugu sarmalayiciya gore belirlenir (asagida).
_ETIKET_RE = re.compile(
    r"(isci\.sh|m3-isci\.sh|[\w.-]*parti-surucusu\.sh)((?:\s+\S+)*)\s*$")

# sarmalayici -> ETIKET'in kacinci arguman oldugu (0-indeksli).
# 🔴 K345: bu sozluk ARTIK ELLE YAZILMIYOR — `SARMALAYICI_ARGUMANLARI`den
# TURETILIYOR. Tabloda olmayan sarmalayici (or. argumansiz `parti-surucusu.sh`)
# `None` doner ve etiket OKUNAMADI sayilir.
_ETIKET_INDEKS = {ad: args.index(ETIKET_YERI)
                  for ad, args in SARMALAYICI_ARGUMANLARI.items()
                  if ETIKET_YERI in args}

# Komut zinciri ayraclari. `||` `&&`den once denenir ki tek `|`ye dusmesin.
_AYRAC_RE = re.compile(r"\|\||&&|\||;|\n")
# Yonlendirme kuyrugu (segment ICINDE, etiketten SONRA gelir). `2>` `>`den
# once gelmeli, yoksa `2>&1` yanlis yerden kirpilir.
_YONLENDIRME_AYRACLARI = (">>", "2>", ">", "<")


def _komut_segmentleri(komut, *, mutant=None):
    """Bash komutunu boru/zincir SEGMENTLERINE ayirir, kuyruklarini kirpar.

    🔴 OLCULEN ARIZA (28 Agu 2026, mimar iki kez yasadi): eski kod komutu
    `ham.find(ayrac)` ile ILK ayracta kesiyordu. Bu, ayrac KUYRUKTAYSA dogru
    (`... tamir-x >> log 2>&1`), ama ayrac ONEKTEYSE (`echo "" | isci.sh ...
    tamir-x`) komut GOVDESININ TAMAMINI atiyordu: geriye `echo ""` kaliyor,
    sarmalayici bulunamiyor, etiket BOS donuyor ve muaf bir onarim cagrisi
    `KOL=N2B-RED` yiyordu. Kapi dogru davraniyordu, GORDUGU dizge yanlisti.

    Cozum SEGMENTASYONdur, kirpma degil: her segment ayri degerlendirilir.
    🔴 fail-closed KORUNUR — bu fonksiyon etiketi OKUNUR kilar, MUAF kilmaz;
    `_etiket_cikar` birden cok sarmalayici gorursa BELIRSIZ deyip BOS doner.
    """
    if mutant == "M11":
        # REGRESYON MUTANTI: K345 oncesi davranis (ilk ayracta kes).
        ham = (komut or "").strip()
        for ayrac in (">>", "2>", ">", "|", "&&", ";"):
            i = ham.find(ayrac)
            if i >= 0:
                ham = ham[:i]
        return [ham.strip()] if ham.strip() else []
    parcalar = []
    for ham in _AYRAC_RE.split(komut or ""):
        for ayrac in _YONLENDIRME_AYRACLARI:
            i = ham.find(ayrac)
            if i >= 0:
                ham = ham[:i]
        ham = ham.strip()
        if ham:
            parcalar.append(ham)
    return parcalar


def _etiket_cikar(komut, *, mutant=None):
    """`isci.sh <motor> <ev> <spec> <etiket>` icindeki ETIKET'i cikarir.

    🔴 Bulamazsa BOS doner ve bos etiket MUAF DEGILDIR (fail-closed yon):
    etiketi okuyamadigimiz bir cagriyi "onarim hatti" sayip gecirmeyiz.
    Boru/yonlendirme artik KORLESTIRMEZ (bkz. `_komut_segmentleri`), ama
    BELIRSIZLIK hala fail-closed: bir komutta IKI sarmalayici cagrisi varsa
    hangisinin hukme girecegi bilinemez -> BOS doner (= ETIKET_OKUNAMADI).
    """
    adaylar = [m for m in
               (_ETIKET_RE.search(seg)
                for seg in _komut_segmentleri(komut, mutant=mutant))
               if m]
    if len(adaylar) != 1:
        return ""                    # 0 = sarmalayici yok · >1 = BELIRSIZ
    m = adaylar[0]
    sarmalayici = os.path.basename(m.group(1))
    indeks = _ETIKET_INDEKS.get(sarmalayici)
    if indeks is None:
        return ""                    # tabloda yok (or. argumansiz surucu)
    argumanlar = (m.group(2) or "").split()
    if len(argumanlar) <= indeks:
        return ""                    # etiket HIC verilmemis
    return argumanlar[indeks].strip().strip("\"'")


# ------------------------------------------------------------------------------
# KENDINI-TEST — 5 mutant + hedef kol atfi + 4 kontrol
# ------------------------------------------------------------------------------
def _sentetik_defter(yol, kalemler):
    """kalemler = [(kimlik, durum), ...]. durum 'KAPANDI' ise kapali sayilir."""
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    satirlar = ["# sentetik defter", "",
                "| id | tarih | kimden→kime | iş (tek cümle) | durum | kapanış kanıtı |",
                "|---|---|---|---|---|---|"]
    for kimlik, durum in kalemler:
        satirlar.append("| %s | 2026-08-19 | X→Y | sentetik is | %s | - |"
                        % (kimlik, durum))
    with open(yol, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar) + "\n")


# Sentetik vakalar: (ad, ev_koku, etiket, komut, beklenen_hukum, beklenen_kol)
# `ev_koku` gercek depo koklerini KULLANIR (yalniz yol cozumu icin); defterler
# `koku_root` ile gecici dizine yonlendirilir — gercek deftere DOKUNULMAZ.
def _vakalar(kok_hasat, kok_kral, kok_bot, kok_jen, kok_advisor):
    isci = "/Users/okan/.claude/cron/isci.sh"
    return (
        # MaCiT'in evinde acik kalem VAR -> RAPOR (cagri GECER, sayi basilir)
        ("macit-yeni-parti", kok_hasat, "parti-surucusu",
         "%s minimax-m3 %s /tmp/s.md parti-surucusu" % (isci, kok_hasat),
         HUKUM_RAPOR, N2B_RED_JETON),
        # 🔴 11 Eyl: onarim/posta etiketleri ARTIK MUAF DEGIL — muafiyet
        # kaldirildi. Ayni evde ayni olcumu alirlar (RAPOR + N2B-RED); fark
        # yok, cunku kimse REDDEDILMIYOR. Bu iki vaka BILEREK DURUYOR: eski
        # muaf yolun sessizce geri gelmedigini olcerler.
        ("macit-tamir", kok_hasat, "tamir-k99",
         "%s minimax-m3 %s /tmp/s.md tamir-k99" % (isci, kok_hasat),
         HUKUM_RAPOR, N2B_RED_JETON),
        ("macit-posta", kok_hasat, "posta-macit",
         "%s minimax-m3 %s /tmp/s.md posta-macit" % (isci, kok_hasat),
         HUKUM_RAPOR, N2B_RED_JETON),
        # KraL'in evinde acik kalem YOK -> yeni parti GECER
        ("kral-yeni-parti", kok_kral, "parti-surucusu",
         "%s kimi %s /tmp/s.md parti-surucusu" % (isci, kok_kral),
         "GECER", N2B_SUREN_JETON),
        # 🔴 K229 UCUNCU KOVA: HocA'nin evinde defter DOSYASI hic YOK
        # -> GECER + KENDI jetonu (ne RED, ne sessiz gecis)
        ("hoca-defter-yok", kok_bot, "parti-surucusu",
         "%s kimi %s /tmp/s.md parti-surucusu" % (isci, kok_bot),
         "GECER", N2B_DEFTER_YOK_JETON),
        # 🔴 SINIR: defter VAR ama BOS -> olculmemis sifir. Hukum RAPOR, ama
        # jeton OLCULEMEDI KALIR (ucuncu kova ikinci kovayi YUTMAZ). Bos dosya
        # hala "olculmus sifir" SAYILMAZ — kaldirilan yaptirimdi, olcum degil.
        ("tekin-defter-bos", kok_jen, "parti-surucusu",
         "%s minimax-m3 %s /tmp/s.md parti-surucusu" % (isci, kok_jen),
         HUKUM_RAPOR, N2B_OLCULEMEDI_JETON),
        # 🔴 27 Agu 2026 — EV COZUMU KAPSAMI (regresyon capasi):
        # BaBa'nin kendi deposu (`pruvo-advisor`) T4 EV_DIZIN'de YOKKEN
        # `ev_coz` onu hicbir eve cozemiyor, kol `N2B-OLCULEMEDI` -> RED
        # veriyordu; BaBa'nin isci kanali BU YUZDEN kapaliydi. Bu vaka
        # kapsamin ALTI EVI de tasidigini olcer. Vaka DUSERSE mesaj sudur:
        # "ev tablosu diskteki gercekten yeniden AYRISTI" — dizge degil,
        # DAVRANIS olculur (hukum + kol).
        ("baba-advisor", kok_advisor, "parti-surucusu",
         "%s minimax-m3 %s /tmp/s.md parti-surucusu" % (isci, kok_advisor),
         "GECER", N2B_SUREN_JETON),
    )


# Yeni-is OLMAYAN komutlar: acik kalemli evde bile KESILMEMELIDIR.
SUREN_KOMUTLARI = (
    "git commit -m 'parti 47/100'",
    "python3 /Users/okan/dev/pruvo-hasat/tools/duzelt.py",
    "git -C /Users/okan/dev/pruvo-hasat push",
    "ls tools/",
    "python3 tools/d1-sync.py --durum",
)

# ------------------------------------------------------------------------------
# K345 — BORU ONEKLI CANLI VAKA (mimarin iki kez yasadigi cagrinin BIREBIR hali)
# ------------------------------------------------------------------------------
# 🔴 Bu iki dizge UYDURULMUS degil: CLAUDE.md 28 Agu'ya kadar `echo "" |` onekini
# ZORUNLU kiliyordu ve o formdaki HER cagri `KOL=N2B-RED` aliyordu. Sarmalayici
# yolu `SARMALAYICI_DIZINI`den TURER (ikinci literal yol yazilmaz).
_ISCI_SARMALAYICI = SARMALAYICI_DIZINI + "/isci.sh"
K345_BORU_KOMUTU = ('echo "" | %s minimax-m3 /Users/okan/dev/pruvo-hasat '
                    '/tmp/s.md tamir-boru-k345' % _ISCI_SARMALAYICI)
# NEGATIF yon: boru VAR ama etiket YOK -> HALA RED (gevsetme olmadi).
K345_BORU_ETIKETSIZ = ('echo "" | %s minimax-m3 /Users/okan/dev/pruvo-hasat '
                       '/tmp/s.md' % _ISCI_SARMALAYICI)

# ------------------------------------------------------------------------------
# K345-C — OKUMA ↔ BASLATMA VAKALARI (ikisi de CANLI vakadan turedi)
# ------------------------------------------------------------------------------
# 🔴 OKUMA vakalari: mimarin bugun RED yedigi komutlar. Hicbiri is BASLATMAZ.
K345_OKUMA_KOMUTLARI = (
    'grep -n "kimi" %s' % _ISCI_SARMALAYICI,
    'cat %s' % _ISCI_SARMALAYICI,
    'wc -c %s' % _ISCI_SARMALAYICI,
    'git commit -m "kapi: %s dokunuldu"' % _ISCI_SARMALAYICI,
    'grep -c BASLANGIC %s | head -1' % _ISCI_SARMALAYICI,
)
# 🔴 BASLATMA vakalari: hepsi HALA kapiya tabidir. Bu kume GEVSETILMEZ —
# okuma kolunun bir KACIS YOLUNA donmedigini olcer.
K345_BASLATMA_KOMUTLARI = (
    '%s minimax-m3 /Users/okan/dev/pruvo-hasat /tmp/s.md parti-surucusu'
    % _ISCI_SARMALAYICI,
    'cat %s | sh' % _ISCI_SARMALAYICI,                    # boruyla YORUMLAYICI
    'sh -c "%s kimi /tmp/e /tmp/s.md parti"' % _ISCI_SARMALAYICI,
    'env -C /tmp %s kimi /tmp/e /tmp/s.md parti' % _ISCI_SARMALAYICI,
    'nohup %s kimi /tmp/e /tmp/s.md parti' % _ISCI_SARMALAYICI,
    'echo $(%s kimi /tmp/e /tmp/s.md parti)' % _ISCI_SARMALAYICI,  # IKAME
    'PRUVO_ISCI_BAGLAM=kapali %s kimi /tmp/e /tmp/s.md parti'
    % _ISCI_SARMALAYICI,
)


# ------------------------------------------------------------------------------
# K248 — K7'nin HAL AYRIMI (20 Agu 2026)
# ------------------------------------------------------------------------------
# OLCULEN ARIZA: K7'nin NEGATIF ayagi, enjekte kopyanin KANONIK repo yoluna
# dusup T4'u yuklemesini bekliyor. `_T4_KANONIK` ise SABIT bir macOS yoludur
# (`/Users/okan/dev/pruvo/tools/...`). GitHub kosucusunda o yol YOKTUR ->
# `FileNotFoundError` -> K7 KUSUR -> `nobet.yml` N2 adimi KIRMIZI.
# Olculdu: kosum 32341626915 (merge ONCESI) `KONTROL K7 ... KUSUR`,
# `MUTANT=5/5 KONTROL=6/7`; kosum 32351520044 (N4A sonrasi) `KONTROL=7/8` —
# ayni K7 dusuyor. Yani bu KIRMIZI bir regresyon degil, TASINABILIRLIK kusuru.
#
# 🔴 "Turetip tasinabilir yap" COZUMU MUMKUN DEGIL — olculdu ve curutuldu:
# enjekte kopya `<ev>/.claude/` altinda oturur ve kendi konumundan repoya geri
# donecek HICBIR bagi yoktur (kardes aday zaten `_T4_YOLU`; ondan otesi bilgi
# gerektirir). Kanonik yol, tanimi geregi MAKINEYE BAGLIDIR. Dolayisiyla dogru
# cozum yolu turetmek degil, HALI AYIRMAKTIR.
#
# UC KOVA (K8/N4A ile ayni doktrin — ucuncu kova ikinciyi YUTMAZ):
#   GECTI       kanonik yol VAR ve kopya oradan yuklendi -> dagitim kanitlandi
#   KAPSAM_DISI kanonik yol bu makinede HIC YOK (CI kosucusu) -> dagitim hedefi
#               burasi degil; ayak FIZIKSEL olarak olculemez, KUSUR DEGILDIR.
#               🔴 Sessiz gecis olmasin diye: geri dusme DENENMIS olmali, yani
#               kanonik yol ciktida ADIYLA gorunmeli.
#   KUSUR       kanonik yol VAR ama yuklenemedi -> GERCEK kusur (fail-loud)
# Mutant kolu (`mutant="K7-KOVA-YUTMA"`) ucuncu kovanin ikinciyi yutmasini
# taklit eder ve KIRMIZI yanar ([[batarya-kapsam-tabani-sayiyla-civilenir]]).
K7_HALLERI = ("GECTI", "KAPSAM_DISI", "KUSUR")


def k7_negatif_hali(kanonik_var, rc, cikti, kanonik_yol=None, *, mutant=None):
    """K7'nin NEGATIF ayagi icin SAF hal karari. Ana yol da kontroller de BUNU
    cagirir (ikiz tanim YOK).

    kanonik_var : `_T4_KANONIK` bu makinede dosya olarak var mi
    rc / cikti  : enjekte kopyanin `--t4-durum` alt surec sonucu
    """
    kanonik_yol = _T4_KANONIK if kanonik_yol is None else kanonik_yol
    if mutant == "K7-KOVA-YUTMA":
        return "KAPSAM_DISI"          # kanonik VAR olsa bile kusuru yutar
    if kanonik_var:
        if rc == RC_GECER and "DURUM=YUKLENDI" in (cikti or ""):
            return "GECTI"
        return "KUSUR"
    # Kanonik yol bu makinede YOK: ayak olculemez. Ama SESSIZ gecmesin —
    # geri dusmenin DENENDIGI, yolun ciktida adiyla gecmesiyle kanitlanir.
    if rc == RC_OLCULEMEDI and kanonik_yol in (cikti or ""):
        return "KAPSAM_DISI"
    return "KUSUR"


# 🔴 KONTROL KAPSAM TABANI — SAYIYLA CIVILI ([[batarya-kapsam-tabani-sayiyla-
# civilenir]]). 11 Eyl 2026'da 13 -> 12 dustu: **yalniz K8** silindi ("muafiyet
# GERCEK cagri yerlerine bagli"), cunku olctugu sozlesme silindi ve K8 silinme
# ANINDA ZATEN `KUSUR` durumdaydi. Numaralar YENIDEN KULLANILMAZ: kontroller
# K1..K7 + K9..K13'tur, K8 bosluktur. Bu sayinin altina dusmek KUSUR'dur —
# batarya kapsamini sessizce kaybetmesin.
KONTROL_TABANI = 12


def kendini_test(gecici_kok):
    """9 mutant + hedef kol atfi + 10 kontrol (izole sentetik defterlerle).

    K8 (N4A) sentetik DEGILDIR: gercek cron kaynak dosyalarini okur.
    K9/K10 (K229) ucuncu kovayi ve onun DIGER IKI kovayi YUTMADIGINI olcer.
    """
    kok_hasat = "/Users/okan/dev/pruvo-hasat"
    kok_kral = "/Users/okan/dev/pruvo"
    kok_bot = "/Users/okan/dev/pruvo-bot"          # HocA — defteri HIC YOK
    kok_jen = "/Users/okan/dev/pruvo-jenerator"    # TeKiN — defteri VAR ama BOS
    kok_advisor = "/Users/okan/dev/pruvo-advisor"  # BaBa — kendi deposu (6. ev)

    # 🔴 K361 — BATARYA HERMETIKTIR: ev->dizin tablosu artik repo DISINDA
    # (`~/.claude/cron/evler.json`) ve KOSUCUDA (CI) O DOSYA YOKTUR. Bu batarya
    # canli tabloya BAGLI KALAMAZ; kendi fiksturunu izolasyon kokune yazar.
    # Fikstur bir TABLO KOPYASI DEGILDIR: yukaridaki depo koklerinden
    # `_proje_dizini()` ile TURETILIR — yol literali IKINCI KEZ YAZILMAZ
    # ([[tuketici-yazilirken-tum-okuyucular-sayilir]]).
    if T4 is not None and hasattr(T4, "fikstur_haritasi_yaz"):
        T4.fikstur_haritasi_yaz(
            os.path.join(gecici_kok, "evler.json"),
            {ev: _proje_dizini(kok) for ev, kok in (
                ("KraL", kok_kral),
                ("ORTAK", kok_kral),
                ("MaCiT", kok_hasat),
                ("HocA", kok_bot),
                ("TeKiN", kok_jen),
                ("BaBa", kok_advisor),
                ("ArTisT", "/Users/okan/dev/pruvo-pazarlama"),
            )})

    # Izole defterler: MaCiT'te 2 acik kalem, KraL'de hepsi KAPANDI.
    _sentetik_defter(os.path.join(gecici_kok, "MaCiT", "memory",
                                  "acik-kalemler.md"),
                     [("K901", "🔧"), ("K902", "ACIK"), ("K903", "KAPANDI")])
    _sentetik_defter(os.path.join(gecici_kok, "KraL", "memory",
                                  "acik-kalemler.md"),
                     [("K800", "KAPANDI"), ("K801", "KAPANDI")])
    # BaBa (6. ev) — defteri VAR ve kalemleri KAPANDI: bu vakada olculen sey
    # DEFTER degil, EV COZUMU kapsamidir (advisor koku -> BaBa).
    _sentetik_defter(os.path.join(gecici_kok, "BaBa", "memory",
                                  "acik-kalemler.md"),
                     [("K850", "KAPANDI")])
    # 🔴 K229 fiksturu — UC ayri hal AYNI kosumda bulunur, yoksa uc kova
    # birbirinden ayrildigi ISPATLANAMAZ:
    #   HocA  : defter DOSYASI hic YOK    -> UCUNCU KOVA (GECER + kendi jetonu)
    #   TeKiN : defter VAR ama BOS (0 B)  -> IKINCI KOVA (fail-closed RED)
    #   MaCiT : defter VAR + acik kalem   -> BIRINCI KOVA (RED, degismedi)
    _hoca_defter = os.path.join(gecici_kok, "HocA", "memory",
                                "acik-kalemler.md")
    if os.path.exists(_hoca_defter):                # fikstur higyeni
        os.remove(_hoca_defter)
    _tekin_defter = os.path.join(gecici_kok, "TeKiN", "memory",
                                 "acik-kalemler.md")
    os.makedirs(os.path.dirname(_tekin_defter), exist_ok=True)
    with open(_tekin_defter, "w", encoding="utf-8") as f:
        f.write("")

    print("N2B PARTI KAPISI — KENDINI-TEST (OLCUM ekseni)")
    print("🔴 Bu batarya kapinin DOGRU OLCTUGUNU kanitlar. Kapinin artik "
          "hicbir cagriyi REDDETMEDIGINI kanitlayan kol AYRI dosyadadir: "
          "tools/tikayici-kaldirma-test.py")
    print("izolasyon koku (defterler): %s" % gecici_kok)
    print("T4 yuklendi: %s" % ("EVET yol=%s" % T4_YOLU if T4 is not None
                               else "HAYIR sebep=%s" % T4_HATA))
    print("")

    vakalar = _vakalar(kok_hasat, kok_kral, kok_bot, kok_jen, kok_advisor)

    def kos(mutant=None):
        out = {}
        for ad, ev_koku, etiket, _komut, _bh, _bk in vakalar:
            out[ad] = parti_karari(ev_koku, etiket, koku_root=gecici_kok,
                                   mutant=mutant)
        # yeni-is ayrimi da bir vakadir: SUREN komutlar kesilmemeli
        out["_suren"] = [yeni_is_mi(k, mutant=mutant) for k in SUREN_KOMUTLARI]
        out["_yeni"] = yeni_is_mi(
            "/Users/okan/.claude/cron/isci.sh minimax-m3 %s /tmp/s.md parti"
            % kok_hasat, mutant=mutant)
        # 🔴 K345 — BORU ONEKI ve UCUNCU KOVA vakalar (kanca yuzeyinin girdisi
        # KOMUT METNIDIR; etiket oradan CIKARILIR, argv'den DEGIL).
        out["_boru"] = parti_karari(
            kok_hasat, _etiket_cikar(K345_BORU_KOMUTU, mutant=mutant),
            koku_root=gecici_kok, mutant=mutant)
        out["_boru_etiketsiz"] = parti_karari(
            kok_hasat, _etiket_cikar(K345_BORU_ETIKETSIZ, mutant=mutant),
            koku_root=gecici_kok, mutant=mutant)
        # 🔴 KALEMSIZ evde de okunamayan etiket KENDI KOVASINA duser. Bu vaka
        # M13'un (kova birlestirme) sizintisini gorunur kilar: kovalar
        # birlesince kalemsiz ev "temiz" diye GECER verir ve etiketin
        # okunamadigi TESHISI kaybolur.
        out["_etiketsiz_temiz_ev"] = parti_karari(
            kok_kral, "", koku_root=gecici_kok, mutant=mutant)
        out["_red_metni"] = red_metni_turetim_hukmu(mutant=mutant)
        # 🔴 K345-C — OKUMA / BASLATMA kollari (kume HUKUMLERI, tek tek degil:
        # bir vakanin sizmasi kumeyi bozmali)
        out["_okuma"] = [yeni_is_hukmu(k, mutant=mutant)[0]
                         for k in K345_OKUMA_KOMUTLARI]
        out["_baslatma"] = [yeni_is_hukmu(k, mutant=mutant)[0]
                            for k in K345_BASLATMA_KOMUTLARI]
        return out

    normal = kos(None)
    taban_ok = True
    print("TABAN (mutantsiz):")
    for ad, _ek, _et, _k, b_hukum, b_kol in vakalar:
        s = normal[ad]
        ok = (s["HUKUM"] == b_hukum and s["KOL"] == b_kol)
        taban_ok = taban_ok and ok
        print("  %-18s %s  (beklenen %s/%s) %s"
              % (ad, hukum_satiri(s), b_hukum, b_kol, "✓" if ok else "✗"))
    yeni_ok = (normal["_yeni"] is True)
    suren_ok = (not any(normal["_suren"]))
    print("  %-18s yeni_is(isci.sh ...)=%s (beklenen True) %s"
          % ("yeni-is-tanima", normal["_yeni"], "✓" if yeni_ok else "✗"))
    print("  %-18s yeni_is(SUREN x%d)=%s (beklenen hepsi False) %s"
          % ("suren-is-tanima", len(SUREN_KOMUTLARI), normal["_suren"],
             "✓" if suren_ok else "✗"))
    # 🔴 K345 tabani — UC KOVA + turetilmis metin (hepsi ONCE olculur)
    # `_boru`: boru ONEKLI cagrinin etiketi HALA OKUNUYOR (K345 onarimi
    # ayakta). Etiket okundugu icin kova ETIKET_OKUNAMADI DEGIL; MaCiT'te
    # acik kalem oldugundan ACIK_KALEM kovasina duser ve RAPOR alir.
    k345_beklenen = (
        ("_boru", HUKUM_RAPOR, N2B_RED_JETON, SEBEP_ACIK_KALEM),
        ("_boru_etiketsiz", HUKUM_RAPOR, N2B_ETIKET_OKUNAMADI_JETON,
         SEBEP_ETIKET_OKUNAMADI),
        ("_etiketsiz_temiz_ev", HUKUM_RAPOR, N2B_ETIKET_OKUNAMADI_JETON,
         SEBEP_ETIKET_OKUNAMADI),
    )
    k345_ok = True
    for ad, b_h, b_k, b_s in k345_beklenen:
        s = normal[ad]
        ok = (s["HUKUM"] == b_h and s["KOL"] == b_k
              and s["SEBEP_KODU"] == b_s)
        k345_ok = k345_ok and ok
        print("  %-20s %s  (beklenen %s/%s/%s) %s"
              % (ad, hukum_satiri(s), b_h, b_k, b_s, "✓" if ok else "✗"))
    rm = normal["_red_metni"]
    rm_ok = (rm["HUKUM"] == HUKUM_GECER)
    print("  %-20s HUKUM=%s ihlal=%d (beklenen GECER/0) %s"
          % ("rapor-metni-turetim", rm["HUKUM"],
             len(rm["IHLAL"]), "✓" if rm_ok else "✗"))
    for i in rm["IHLAL"]:
        print("      | %s" % i)
    okuma_ok = all(h == "OKUMA" for h in normal["_okuma"])
    baslatma_ok = all(h == "YENI" for h in normal["_baslatma"])
    print("  %-20s %d vaka -> %s (beklenen hepsi OKUMA) %s"
          % ("okuma-kolu", len(normal["_okuma"]),
             sorted(set(normal["_okuma"])), "✓" if okuma_ok else "✗"))
    for k, h in zip(K345_OKUMA_KOMUTLARI, normal["_okuma"]):
        print("      | %-6s %s" % (h, k[:88]))
    print("  %-20s %d vaka -> %s (beklenen hepsi YENI) %s"
          % ("baslatma-kolu", len(normal["_baslatma"]),
             sorted(set(normal["_baslatma"])), "✓" if baslatma_ok else "✗"))
    for k, h in zip(K345_BASLATMA_KOMUTLARI, normal["_baslatma"]):
        print("      | %-6s %s" % (h, k[:88]))
    taban_ok = (taban_ok and yeni_ok and suren_ok and k345_ok
                and rm_ok and okuma_ok and baslatma_ok)
    print("")
    if not taban_ok:
        print("TABAN KIRMIZI — mutant olcumu ANLAMSIZ.")
        print("MUTANT=0/%d HEDEF_KOL_ATFI=0/%d KONTROL=0/%d"
              % (len(MUTANT_HEDEF), len(MUTANT_HEDEF), KONTROL_TABANI))
        return 1

    # --- MUTANTLAR ---------------------------------------------------------
    # Her mutant icin: (hedef vaka kumesi, yan eksen kumesi)
    HEDEF_VAKA = {
        "M1": ("_yeni",),                       # yeni-is tanima
        "M2": ("_suren",),                      # suren-is korumasi
        # M4 fail-closed kolu: bilinmeyen ev koku (sentetik) VE defteri BOS ev
        # — ikincisi K229'dan sonra AYNI kolun ikinci yuzeyidir; yan eksene
        # yazilirsa M4'un ATFI hatali biçimde KUSUR okunur.
        "M4": ("_olculemedi", "tekin-defter-bos"),
        # K229: ucuncu kova — iki AYRI oldurme yolu (eski adlari M6/M7 idi)
        "M8": ("hoca-defter-yok",),             # ucuncu kova — kol BOZULUR
        "M9": ("hoca-defter-yok",),             # ucuncu kova — kol BIRLESTIRILIR
        "M11": ("_boru",),                      # boru ONEKI normalizasyonu
        # M13 ETIKET_OKUNAMADI kovasini acik-kalem kovasina yutar; HEM borulu
        # HEM kalemsiz-ev vakasini bozar (kova tek yerde yasamaz).
        "M13": ("_boru_etiketsiz", "_etiketsiz_temiz_ev"),
        # K345-C: M14 okuma kolunu kaldirir (yalniz `_okuma` bozulur);
        # M15 baslatmayi okuma sayar -> `_baslatma` SIZAR ve `_yeni` de duser
        # (ikisi ayni kolun iki yuzu; `_yeni` yan eksene yazilirsa M15'in
        # ATFI sahte KUSUR okunur).
        "M14": ("_okuma",),
        "M15": ("_baslatma", "_yeni"),
    }
    mutant_sayaci = 0
    atif_sayaci = 0
    for ad in sorted(MUTANT_HEDEF):
        kol = MUTANT_HEDEF[ad]
        print("MUTANT %s -> hedef kol %s" % (ad, kol))
        m = kos(ad)
        hedef_kirmizi = False
        yan_bozulan = []

        if ad == "M1":
            hedef_kirmizi = (normal["_yeni"] is True and m["_yeni"] is False)
            print("  yeni_is(parti komutu): normal=%s mutant=%s"
                  % (normal["_yeni"], m["_yeni"]))
        elif ad == "M2":
            hedef_kirmizi = (not any(normal["_suren"])) and all(m["_suren"])
            print("  yeni_is(SUREN komutlar): normal=%s mutant=%s"
                  % (normal["_suren"], m["_suren"]))
            print("  -> M2 altinda YARIM IS KESILIRDI (kol gercekten koruyor)")
        elif ad == "M4":
            # Fail-open yalniz OLCULEMEDI vakasinda gorunur: bilinmeyen ev koku.
            n4 = parti_karari("/tmp/bilinmeyen-ev-koku-n2b", "parti",
                              koku_root=gecici_kok, mutant=None)
            m4 = parti_karari("/tmp/bilinmeyen-ev-koku-n2b", "parti",
                              koku_root=gecici_kok, mutant="M4")
            hedef_kirmizi = (n4["HUKUM"] == HUKUM_RAPOR
                             and n4["KOL"] == N2B_OLCULEMEDI_JETON
                             and m4["HUKUM"] == HUKUM_GECER)
            print("  bilinmeyen ev: normal=%s | mutant=%s"
                  % (hukum_satiri(n4), hukum_satiri(m4)))
        else:
            for hv in HEDEF_VAKA[ad]:
                n, mm = normal[hv], m[hv]
                if hv in ("_yeni", "_suren"):
                    # bool / bool-listesi eksenleri (dict DEGIL)
                    n, mm = normal[hv], m[hv]
                    if n != mm:
                        hedef_kirmizi = True
                    print("  %s: normal=%s | mutant=%s" % (hv, n, mm))
                    continue
                if hv in ("_okuma", "_baslatma"):
                    n, mm = normal[hv], m[hv]
                    if n != mm:
                        hedef_kirmizi = True
                    print("  %s: normal=%s | mutant=%s"
                          % (hv, sorted(set(n)), sorted(set(mm))))
                    if hv == "_baslatma" and "OKUMA" in mm:
                        sizan = [k for k, h in
                                 zip(K345_BASLATMA_KOMUTLARI, mm)
                                 if h == "OKUMA"]
                        print("      | 🔴 SIZAN BASLATMA (%d): %s"
                              % (len(sizan), sizan[0][:80]))
                    continue
                if hv == "_red_metni":
                    if n["HUKUM"] == HUKUM_GECER and mm["HUKUM"] != HUKUM_GECER:
                        hedef_kirmizi = True
                    print("  _red_metni: normal=HUKUM=%s ihlal=%d | "
                          "mutant=HUKUM=%s ihlal=%d"
                          % (n["HUKUM"], len(n["IHLAL"]),
                             mm["HUKUM"], len(mm["IHLAL"])))
                    for i in mm["IHLAL"]:
                        print("      | IHLAL %s" % i)
                    continue
                # 🔴 SEBEP KODU da karsilastirilir: yalniz (HUKUM,KOL)'a bakan
                # bir test M13'u (kova birlestirme) YASATABILIRDI.
                if ((n["HUKUM"], n["KOL"], n.get("SEBEP_KODU"))
                        != (mm["HUKUM"], mm["KOL"], mm.get("SEBEP_KODU"))):
                    hedef_kirmizi = True
                print("  %s: normal=%s | mutant=%s"
                      % (hv, hukum_satiri(n), hukum_satiri(mm)))
            if ad == "M8":
                mm = m["hoca-defter-yok"]
                print("  -> M8 altinda defteri OLMAYAN ev yine %s/%s alirdi: "
                      "ucuncu kova kaybolur, 'olcemedik' ile 'olculecek bir "
                      "sey yok' ayni satirda gorunurdu"
                      % (mm["HUKUM"], mm["KOL"]))
            if ad == "M9":
                mm = m["hoca-defter-yok"]
                print("  -> M9 altinda HUKUM DEGISMEDI (%s) ama JETON %s'e "
                      "dondu: yalniz HUKUM'e bakan bir test bu mutanti "
                      "YASATIRDI — ucuncu kova sessizce kaybolurdu"
                      % (mm["HUKUM"], mm["KOL"]))

        # yan eksen: hedef DISINDAKI vakalar degismemeli
        for vad, _ek, _et, _k, _bh, _bk in vakalar:
            if vad in HEDEF_VAKA[ad]:
                continue
            n, mm = normal[vad], m[vad]
            if (n["HUKUM"], n["KOL"]) != (mm["HUKUM"], mm["KOL"]):
                yan_bozulan.append(vad)
        if "_yeni" not in HEDEF_VAKA[ad] and normal["_yeni"] != m["_yeni"]:
            yan_bozulan.append("_yeni")
        if "_suren" not in HEDEF_VAKA[ad] and normal["_suren"] != m["_suren"]:
            yan_bozulan.append("_suren")
        # 🔴 K345 yan eksenleri — hedef DISINDAKI kollar da bozulmamali
        for k345_ad in ("_boru", "_boru_etiketsiz", "_etiketsiz_temiz_ev"):
            if k345_ad in HEDEF_VAKA[ad]:
                continue
            n, mm = normal[k345_ad], m[k345_ad]
            if ((n["HUKUM"], n["KOL"], n.get("SEBEP_KODU"))
                    != (mm["HUKUM"], mm["KOL"], mm.get("SEBEP_KODU"))):
                yan_bozulan.append(k345_ad)
        if ("_red_metni" not in HEDEF_VAKA[ad]
                and normal["_red_metni"]["HUKUM"] != m["_red_metni"]["HUKUM"]):
            yan_bozulan.append("_red_metni")
        for c_ad in ("_okuma", "_baslatma"):
            if c_ad not in HEDEF_VAKA[ad] and normal[c_ad] != m[c_ad]:
                yan_bozulan.append(c_ad)
        yan_yesil = not yan_bozulan
        print("  yan eksen bozulan: %s" % (",".join(yan_bozulan) or "-"))

        if hedef_kirmizi:
            mutant_sayaci += 1
            print("  SONUÇ: BEKLENDI YAKALANDI (mutant yasamaz)")
        else:
            print("  SONUÇ: BEKLENDI YAKALANMADI (MUTANT YASARDI)")
        if hedef_kirmizi and yan_yesil:
            atif_sayaci += 1
            print("  ATIF : hedef kol kirmizi + yan eksen YESIL")
        else:
            print("  ATIF : KUSUR (hedef kol ya da yan eksen tutmadi)")
        print("")

    # --- KONTROLLER --------------------------------------------------------
    kontrol = 0

    # K1: RAPOR ciktisi kalem KIMLIGINI ve `kabul:` komutunu BASAR.
    # 🔴 Kaldirma sonrasi BU KONTROL DAHA ONEMLI oldu: cagri kesilmedigi icin
    # okuyanin elinde YALNIZ bu metin var. Teshis fakirlesirse kaldirma
    # "sessizlestirme"ye doner ve bugunku ariza (sayi=0) tekrarlanir.
    red = normal["macit-yeni-parti"]
    metin = red_metni(red)
    k1 = ("K901" in metin and "K902" in metin and "kabul: " in metin
          and "parti-borc-kapisi.py --ev MaCiT" in metin
          and "CAGRI KESILMEDI" in metin)
    print("KONTROL K1 RAPOR ciktisi kalem + `kabul:` + 'CAGRI KESILMEDI' "
          "basar: %s" % ("GECTI" if k1 else "KUSUR"))
    for satir in metin.splitlines():
        print("    | %s" % satir)
    kontrol += 1 if k1 else 0

    # K2: 🔴 NEGATIF — acik kalemli evde SUREN is KESILMEZ (ayni kosumda kanit)
    kesilenler = [k for k in SUREN_KOMUTLARI if yeni_is_mi(k)]
    k2 = not kesilenler
    print("KONTROL K2 yarim/suren is KESILMEZ: %s (kesilen=%s)"
          % ("GECTI" if k2 else "KUSUR", kesilenler or "-"))
    kontrol += 1 if k2 else 0

    # K3: kalem KAPANINCA ayni komut GECER (kapi kalici kilit DEGIL)
    _sentetik_defter(os.path.join(gecici_kok, "MaCiT", "memory",
                                  "acik-kalemler.md"),
                     [("K901", "KAPANDI"), ("K902", "KAPANDI"),
                      ("K903", "KAPANDI")])
    sonra = parti_karari(kok_hasat, "parti-surucusu", koku_root=gecici_kok)
    k3 = (sonra["HUKUM"] == HUKUM_GECER and sonra["KOL"] == N2B_SUREN_JETON)
    print("KONTROL K3 kalem kapaninca hukum RAPOR->GECER doner: %s (%s)"
          % ("GECTI" if k3 else "KUSUR", hukum_satiri(sonra)))
    kontrol += 1 if k3 else 0
    # defteri geri koy (sonraki kontrolleri etkilemesin)
    _sentetik_defter(os.path.join(gecici_kok, "MaCiT", "memory",
                                  "acik-kalemler.md"),
                     [("K901", "🔧"), ("K902", "ACIK"), ("K903", "KAPANDI")])

    # K4: 🔴 TERS EKSEN — `isci_kapi` acik kalemli evde bile rc=0 doner, AMA
    #     hukum satirini HEM stdout HEM stderr'e basar. Eskiden burada
    #     `rc == RC_RED` (1) araniyordu ve `isci.sh` orada `exit 3` ediyordu.
    #     Iki ayak birlikte: (a) rc=0 (b) teshis KAYBOLMADI.
    tampon4 = io.StringIO()
    hata4 = io.StringIO()
    _err4, sys.stderr = sys.stderr, hata4
    try:
        with redirect_stdout(tampon4):
            rc = isci_kapi("minimax-m3", kok_hasat, "/tmp/s.md",
                           "parti-surucusu", koku_root=gecici_kok)
    finally:
        sys.stderr = _err4
    cikti4 = tampon4.getvalue()
    gerekce4 = hata4.getvalue()
    k4 = (rc == RC_GECER
          and ("HUKUM=%s" % HUKUM_RAPOR) in cikti4
          and ("KOL=%s" % N2B_RED_JETON) in cikti4
          and "ACIK=2" in cikti4
          and "K901" in gerekce4)          # kalem kimligi teshiste DURUYOR
    print("KONTROL K4 isci_kapi rc=0 + teshis KORUNDU: %s (rc=%d, beklenen %d)"
          % ("GECTI" if k4 else "KUSUR", rc, RC_GECER))
    print("    | stdout : %s" % (cikti4.strip() or "(BOS — SAYI KAYBOLDU)"))
    print("    | stderr kalem izi: %s"
          % ("K901 VAR" if "K901" in gerekce4 else "🔴 YOK"))
    kontrol += 1 if k4 else 0

    # K5: KANCA yuzeyi uctan uca + ETIKET cikarimi (yonlendirme kuyruklu komut)
    #     🔴 Kanca modu DAIMA rc=0 doner ve ARTIK HICBIR VAKADA deny URETMEZ.
    #     `beklenen_deny` sutunu bilerek TUMUYLE False'tur: eskiden ilk satir
    #     True idi ve tikayici tam oradaydi.
    isci = "/Users/okan/.claude/cron/isci.sh"
    vaka_kanca = (
        # (ad, komut, beklenen_deny, teshis_bekleniyor_mu)
        ("yeni-parti",
         "%s minimax-m3 %s /tmp/s.md parti-surucusu >> /tmp/l.log 2>&1"
         % (isci, kok_hasat), False, True),
        ("eski-muaf-etiket",
         "%s minimax-m3 %s /tmp/s.md tamir-k99 >> /tmp/l.log 2>&1"
         % (isci, kok_hasat), False, True),
        ("suren-is", "git -C %s commit -m 'parti 47/100'" % kok_hasat,
         False, False),
    )
    k5 = True
    for ad, komut, bekle_deny, bekle_teshis in vaka_kanca:
        girdi = {"tool_name": "Bash", "tool_input": {"command": komut},
                 "cwd": kok_hasat}
        tampon = io.StringIO()
        hata5 = io.StringIO()
        _err5, sys.stderr = sys.stderr, hata5
        try:
            with redirect_stdout(tampon):
                rc_k = kanca(girdi, koku_root=gecici_kok)
        finally:
            sys.stderr = _err5
        ham = tampon.getvalue().strip()
        deny = False
        if ham:
            try:
                deny = (json.loads(ham).get("hookSpecificOutput", {})
                        .get("permissionDecision") == "deny")
            except Exception:
                deny = False
        teshis = "N2B HUKUM=" in hata5.getvalue()
        etiket = _etiket_cikar(komut)
        ok = (rc_k == 0 and deny == bekle_deny and teshis == bekle_teshis)
        k5 = k5 and ok
        print("  kanca[%-16s] rc=%d deny=%-5s (bekl %-5s) teshis=%-5s "
              "(bekl %-5s) etiket=%r %s"
              % (ad, rc_k, deny, bekle_deny, teshis, bekle_teshis, etiket,
                 "✓" if ok else "✗"))
    print("KONTROL K5 kanca yuzeyi deny URETMEZ + teshis KORUNUR: %s"
          % ("GECTI" if k5 else "KUSUR"))
    kontrol += 1 if k5 else 0

    # K6: 🔴 T4-YUKLENEMEZ MUTANTI — kapi KIRMIZI yanar VE sebebi (aranan YOL +
    #     istisna TURU) ciktida GORUNUR. 20 Agu vakasinda sessiz `return None`
    #     yuzunden bes evin isci hatti oldu ve NEDENI hicbir satirda yoktu.
    #     Uc ayak birlikte olculur (K182: "kirmizi geldi" tek basina kanit degil):
    #       (a) MUTANT   : T4 erisilemez -> RAPOR + KOL=N2B-OLCULEMEDI + SEBEP
    #       (b) NEGATIF  : T4 yerinde iken AYNI cagri TEMIZ/GECER (kirmizinin
    #                      sebebi hedef koldur, ambiyans degil)
    #       (c) YAN EKSEN: T4 yokken de ACIK KALEMLI evin hukmu AYNI kovaya
    #                      duser — kirmizi GENEL degil, hedefe ozgudur
    yok_yol = os.path.join(gecici_kok, "T4-YOK", _T4_ADI)
    _yok_mod, _yok_yuklenen, t4_hata = _t4_yukle([yok_yol])
    m6 = parti_karari(kok_kral, "parti-surucusu", koku_root=gecici_kok,
                      t4=None, t4_hata=t4_hata)
    n6 = parti_karari(kok_kral, "parti-surucusu", koku_root=gecici_kok)
    y6 = parti_karari(kok_hasat, "parti-surucusu", koku_root=gecici_kok)
    hata6 = m6["HATA"] or ""
    k6 = (_yok_mod is None
          and m6["HUKUM"] == HUKUM_RAPOR
          and m6["KOL"] == N2B_OLCULEMEDI_JETON
          and yok_yol in hata6 and "FileNotFoundError" in hata6
          and n6["HUKUM"] == HUKUM_GECER and n6["KOL"] == N2B_SUREN_JETON
          and y6["HUKUM"] == HUKUM_RAPOR and y6["KOL"] == N2B_RED_JETON)
    print("KONTROL K6 T4 yuklenemezse KIRMIZI + SEBEP (yol+istisna) basar: %s"
          % ("GECTI" if k6 else "KUSUR"))
    print("    | mutant  : %s" % hukum_satiri(m6))
    print("    | SEBEP   : %s" % (hata6 or "(BOS — SESSIZ YUTMA)"))
    print("    | negatif : %s  (T4 yerinde, AYNI cagri)" % hukum_satiri(n6))
    print("    | yan eks.: %s  (acik kalemli ev KENDI kovasinda)"
          % hukum_satiri(y6))
    kontrol += 1 if k6 else 0

    # K7: 🔴 DAGITIM UCTAN UCA — evlere KOPYALANAN kapi, T4 KARDESI OLMADAN
    #     calisir. 20 Agu vakasinin ta kendisi: kopya `<ev>/.claude/` altinda
    #     oturuyor, T4 kardes olarak araniyor, bulunamiyor, hata yutuluyordu.
    #     Gercek bir kopya + gercek bir alt surec ile olculur (iddia degil).
    enjekte = os.path.join(gecici_kok, "enjekte-ev", ".claude")
    os.makedirs(enjekte, exist_ok=True)
    kopya = os.path.join(enjekte, os.path.basename(os.path.abspath(__file__)))
    shutil.copyfile(os.path.abspath(__file__), kopya)
    kardes_var = os.path.isfile(os.path.join(enjekte, _T4_ADI))
    p_iyi = subprocess.run([sys.executable, kopya, "--t4-durum"],
                           capture_output=True, text=True)
    p_mut = subprocess.run([sys.executable, kopya, "--t4-durum",
                            "--t4-yolu", yok_yol],
                           capture_output=True, text=True)
    c_iyi = (p_iyi.stdout or "") + (p_iyi.stderr or "")
    c_mut = (p_mut.stdout or "") + (p_mut.stderr or "")
    # K248: NEGATIF ayagin hukmu SAF fonksiyondan gelir; kanonik yol bu
    # makinede yoksa (CI kosucusu) ayak KAPSAM_DISI'dir, KUSUR degil.
    kanonik_var = os.path.isfile(_T4_KANONIK)
    negatif_hal = k7_negatif_hali(kanonik_var, p_iyi.returncode, c_iyi)

    # MUTANT ayagi MAKINEDEN BAGIMSIZDIR: verilmeyen yol her yerde yoktur.
    mutant_ok = (p_mut.returncode == RC_OLCULEMEDI
                 and "DURUM=YUKLENEMEDI" in c_mut
                 and yok_yol in c_mut and "FileNotFoundError" in c_mut)

    # 🔴 K248 KOVA AYRIMI — HERMETIK, her ortamda kosar (iddia degil olcum).
    #    Ucuncu kova (KAPSAM_DISI) ikinciyi (KUSUR) yutarsa kapi korlesirdi.
    sahte_yol = "/YOK/parti-borc-kapisi.py"
    kova = [
        ("kanonik VAR + yuklendi",
         k7_negatif_hali(True, RC_GECER, "N2B-T4 DURUM=YUKLENDI"), "GECTI"),
        ("kanonik VAR + yuklenemedi",
         k7_negatif_hali(True, RC_OLCULEMEDI, "DURUM=YUKLENEMEDI"), "KUSUR"),
        ("kanonik YOK + geri dusme DENENDI",
         k7_negatif_hali(False, RC_OLCULEMEDI,
                         "DURUM=YUKLENEMEDI ... " + sahte_yol, sahte_yol),
         "KAPSAM_DISI"),
        ("kanonik YOK + geri dusme DENENMEDI (sessiz gecis)",
         k7_negatif_hali(False, RC_GECER, "DURUM=YUKLENDI", sahte_yol), "KUSUR"),
    ]
    kova_ok = all(gelen == beklenen for _ad, gelen, beklenen in kova)
    # Mutant: ucuncu kova ikinciyi YUTSUN -> "kanonik VAR + yuklenemedi" vakasi
    # KUSUR yerine KAPSAM_DISI doner; hedef kol kirmizi yanmali.
    m_hedef = k7_negatif_hali(True, RC_OLCULEMEDI, "DURUM=YUKLENEMEDI",
                              mutant="K7-KOVA-YUTMA")
    m_yan = k7_negatif_hali(True, RC_GECER, "N2B-T4 DURUM=YUKLENDI")
    kova_mutant_ok = (m_hedef != "KUSUR" and m_yan == "GECTI")

    k7 = ((not kardes_var)                       # kardes T4 GERCEKTEN yok
          and negatif_hal in ("GECTI", "KAPSAM_DISI")
          and mutant_ok
          and kova_ok and kova_mutant_ok)
    print("KONTROL K7 enjekte kopya (kardes T4 YOK) uctan uca: %s"
          % ("GECTI" if k7 else "KUSUR"))
    print("    | kopya   : %s (kardes %s var mi: %s)"
          % (kopya, _T4_ADI, kardes_var))
    print("    | kanonik : %s (bu makinede var mi: %s) -> NEGATIF HAL=%s"
          % (_T4_KANONIK, kanonik_var, negatif_hal))
    if negatif_hal == "KAPSAM_DISI":
        print("    | KAPSAM_DISI — kanonik yol bu makinede YOK (CI kosucusu); "
              "dagitim hedefi burasi degil. Geri dusme DENENDI (yol ciktida).")
    for satir in c_iyi.strip().splitlines():
        print("    | negatif | %s" % satir)
    print("    | negatif rc=%d" % p_iyi.returncode)
    for satir in c_mut.strip().splitlines():
        print("    | mutant  | %s" % satir)
    print("    | mutant  rc=%d (beklenen %d) %s"
          % (p_mut.returncode, RC_OLCULEMEDI, "✓" if mutant_ok else "✗"))
    for ad, gelen, beklenen in kova:
        print("    | kova[%-44s] %-12s (beklenen %-12s) %s"
              % (ad, gelen, beklenen, "✓" if gelen == beklenen else "✗"))
    print("    | kova mutanti (K7-KOVA-YUTMA): hedef=%s (KUSUR OLMAMALI) · "
          "yan=%s (GECTI kalmali) %s"
          % (m_hedef, m_yan, "✓" if kova_mutant_ok else "✗"))
    kontrol += 1 if k7 else 0

    # 🔴 K8 SILINDI (11 Eyl 2026) — "muafiyet GERCEK cagri yerlerine bagli".
    # Olctugu sozlesme (`MUAF_ETIKET_ONEKLERI`) bu turda silindi. K8 silinme
    # ANINDA ZATEN `KUSUR` durumdaydi (degisiklikten ONCE olculdu): silinen
    # sey YESIL bir nobetci DEGIL, konusu ortadan kalkmis KIRMIZI bir koldu.
    # Numara YENIDEN KULLANILMAZ — K9..K13 numaralari kaydi, boylece gecmis
    # defter satirlarindaki "K12 GECTI" gibi atiflar hala ayni kolu gosterir.

    # K9: 🔴 K229 UCUNCU KOVA — defteri OLMAYAN ev GECER ama SESSIZ DEGIL.
    #     Uc ayak: (a) hukum GECER + KENDI jetonu, (b) isci.sh yuzeyi rc=0
    #     (hat GERCEKTEN aciliyor), (c) jeton + gerekce CIKTIDA GORUNUR.
    dy = normal["hoca-defter-yok"]
    tampon8 = io.StringIO()
    hata8 = io.StringIO()
    _eski_err = sys.stderr
    sys.stderr = hata8
    try:
        with redirect_stdout(tampon8):
            rc8 = isci_kapi("minimax-m3", kok_bot, "/tmp/s.md",
                            "parti-surucusu", koku_root=gecici_kok)
    finally:
        sys.stderr = _eski_err
    cikti8 = tampon8.getvalue()
    gerekce8 = hata8.getvalue()
    k9 = (dy["HUKUM"] == HUKUM_GECER
          and dy["KOL"] == N2B_DEFTER_YOK_JETON
          and dy["KOL"] != N2B_OLCULEMEDI_JETON       # kovalar AYRI jetonda
          and rc8 == RC_GECER
          and ("KOL=%s" % N2B_DEFTER_YOK_JETON) in cikti8
          and N2B_DEFTER_YOK_JETON in gerekce8)
    print("KONTROL K9 defteri YOK olan ev: GECER + AYRI jeton + gorunur: %s"
          % ("GECTI" if k9 else "KUSUR"))
    print("    | karar   : %s" % hukum_satiri(dy))
    print("    | isci.sh : rc=%d (beklenen %d) stdout=%s"
          % (rc8, RC_GECER, cikti8.strip() or "(BOS)"))
    print("    | gerekce : %s" % (gerekce8.strip() or "(BOS — SESSIZ GECIS)"))

    kontrol += 1 if k9 else 0

    # K10: 🔴 NEGATIF/SINIR — ucuncu kova DIGER IKI kovayi YUTMADI (ayni kosum).
    #     (a) defteri VAR + acik kalemli ev  -> RAPOR/N2B-RED + ACIK=2 (SAYI basar)
    #     (b) defteri VAR + kalemi kapali ev -> GECER/N2B-SUREN
    #     (c) defteri VAR ama BOS ev         -> RAPOR/N2B-OLCULEMEDI
    #         (bos dosya "olculmus sifir" SAYILMAZ — K201; kaldirilan yaptirim,
    #          bu ayrim DEGIL)
    a9 = normal["macit-yeni-parti"]
    b9 = normal["kral-yeni-parti"]
    c9 = normal["tekin-defter-bos"]
    k10 = (a9["HUKUM"] == HUKUM_RAPOR and a9["KOL"] == N2B_RED_JETON
           and a9["ACIK"] == 2
           and b9["HUKUM"] == HUKUM_GECER and b9["KOL"] == N2B_SUREN_JETON
           and c9["HUKUM"] == HUKUM_RAPOR
           and c9["KOL"] == N2B_OLCULEMEDI_JETON)
    print("KONTROL K10 uc kova AYRI kaldi (acik kalem / kalemsiz / BOS "
          "defter): %s" % ("GECTI" if k10 else "KUSUR"))
    print("    | acik kalemli : %s" % hukum_satiri(a9))
    print("    | kalemsiz     : %s" % hukum_satiri(b9))
    print("    | BOS defter   : %s  (SEBEP: %s)"
          % (hukum_satiri(c9), c9["HATA"] or "-"))
    kontrol += 1 if k10 else 0

    # K11: 🔴 K345 — RAPOR METNI TURETILMIS MI? (iki yonlu esitlik)
    #      Kapinin dogru olcmesi YETMEZ: okuyan METNE gore davranir.
    #      Bu kontrol metnin CALISAN CAGRI YOLUNU tasidigini olcer VE
    #      metinde BAYAT bir "REDDEDILDI" vaadi kalmadigini dogrular.
    t11 = red_metni_turetim_hukmu()
    ornek11 = {"HUKUM": HUKUM_RAPOR, "KOL": N2B_ETIKET_OKUNAMADI_JETON,
               "EV": "KraL",
               "ACIK": 0, "KALEMLER": [], "KABUL_KOMUTU": kabul_komutu("KraL"),
               "SEBEP_KODU": SEBEP_ETIKET_OKUNAMADI, "SEBEP": None,
               "HATA": None, "ETIKET": ""}
    metin11 = red_metni(ornek11)
    tasiyor = all(b in metin11 for b in dogru_cagri_bicimi())
    bayat = [s for s in metin11.splitlines() if "REDDEDIL" in s.upper()]
    k11 = (t11["HUKUM"] == HUKUM_GECER and tasiyor and not bayat)
    print("KONTROL K11 rapor metni TURETILMIS + BAYAT RED vaadi YOK: %s"
          % ("GECTI" if k11 else "KUSUR"))
    print("    | hukum=%s ihlal=%d cagri_bicimi_metinde=%s bayat_red_satiri=%d"
          % (t11["HUKUM"], len(t11["IHLAL"]), tasiyor, len(bayat)))
    for s in bayat:
        print("    |   🔴 BAYAT: %s" % s[:100])
    for i in t11["IHLAL"]:
        print("    | IHLAL %s" % i)
    for satir in metin11.splitlines():
        print("    | %s" % satir)
    kontrol += 1 if k11 else 0

    # K12: 🔴 K345 — UC KOVA, UC AYRI HUKUM, **30 ACIK KALEMLI** fikstur.
    #      Mimarin gercek vakasi buydu: 30 kalem varken borulu MUAF cagri
    #      RED yiyordu ve metin 30 kalemi siralayip yanlis careyi veriyordu.
    #      UCU DE AYNI KOSUMDA olculur — yoksa kovalarin AYRILDIGI
    #      ispatlanamaz ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
    _sentetik_defter(os.path.join(gecici_kok, "MaCiT", "memory",
                                  "acik-kalemler.md"),
                     [("K%03d" % (900 + i), "🔧") for i in range(30)])
    kova_a = parti_karari(kok_hasat, _etiket_cikar(K345_BORU_KOMUTU),
                          koku_root=gecici_kok)
    kova_b = parti_karari(kok_hasat, "parti-surucusu", koku_root=gecici_kok)
    kova_c = parti_karari(kok_hasat, _etiket_cikar(K345_BORU_ETIKETSIZ),
                          koku_root=gecici_kok)
    hukumler = {hukum_satiri(kova_a), hukum_satiri(kova_b), hukum_satiri(kova_c)}
    # 🔴 11 Eyl: (a) ile (b) artik AYNI hukmu alir — muafiyet SILINDI. Ayrilan
    # sey ETIKET KOVASI: (c)'nin etiketi okunamadi, (a)/(b)'ninki okundu.
    # Bu yuzden AYRI HUKUM SATIRI sayisi 3 degil **2**'dir ve bu bir kayip
    # DEGIL, kaldirmanin dogrudan sonucudur — sayiyi civiliyoruz ki kova
    # ayrimi bundan SONRA sessizce ikiden bire dusmesin.
    k12 = (kova_a["HUKUM"] == HUKUM_RAPOR and kova_a["KOL"] == N2B_RED_JETON
           and kova_a["SEBEP_KODU"] == SEBEP_ACIK_KALEM
           and kova_a["ACIK"] == 30
           and kova_b["HUKUM"] == HUKUM_RAPOR and kova_b["KOL"] == N2B_RED_JETON
           and kova_b["SEBEP_KODU"] == SEBEP_ACIK_KALEM and kova_b["ACIK"] == 30
           and kova_c["HUKUM"] == HUKUM_RAPOR
           and kova_c["KOL"] == N2B_ETIKET_OKUNAMADI_JETON
           and kova_c["SEBEP_KODU"] == SEBEP_ETIKET_OKUNAMADI
           and kova_c["ACIK"] == 0          # etiket kovasinda kalem SAYILMAZ
           and len(hukumler) == 2)          # IKI AYRI hukum satiri
    print("KONTROL K12 etiket kovasi AYRI kaldi (30 acik kalemli fikstur): %s"
          % ("GECTI" if k12 else "KUSUR"))
    print("    | (a) eski MUAF etiket + boru  : %s" % hukum_satiri(kova_a))
    print("    | (b) muaf-DISI etiket + kalem : %s" % hukum_satiri(kova_b))
    print("    | (c) etiket OKUNAMADI (boru)  : %s" % hukum_satiri(kova_c))
    print("    | ayri hukum satiri sayisi=%d (beklenen 2 — muafiyet silindi, "
          "(a) ve (b) ARTIK AYNI)" % len(hukumler))
    # 🔴 Sebep AYRIMI metne de yansiyor mu? (b) ve (c) AYNI metni BASMAMALI
    print("    | (c) rapor metni sebep satirlari:")
    for satir in red_metni(kova_c).splitlines():
        if "SEBEP[" in satir:
            print("    |   %s" % satir)
    kontrol += 1 if k12 else 0
    # fikstur higyeni: defteri onceki haline dondur
    _sentetik_defter(os.path.join(gecici_kok, "MaCiT", "memory",
                                  "acik-kalemler.md"),
                     [("K901", "🔧"), ("K902", "ACIK"), ("K903", "KAPANDI")])

    # K13: 🔴 K345-C — OKUMA ile BASLATMA AYRI SINIFLANIR, **ikisi de GECER**.
    #      Kanca yuzeyinde UCTAN UCA (karar fonksiyonu degil, GERCEK hook
    #      girdisi). Ev MaCiT: 2 acik kalem VAR.
    #      🔴 KALDIRMA SONRASI DEGISEN AYAK: eskiden "BASLATMA hala RED"
    #      araniyordu (deny=7/7). Artik deny=0/0 — ama SINIFLANDIRMA ayakta
    #      kalmali: okuma vakalari `N2B-OKUMA` jetonu basmali, baslatma
    #      vakalari ise TESHIS (hukum satiri) basmali. Jeton kaybolursa
    #      "kapi fiilen calisiyor mu" sorusu bir daha olculemez
    #      ([[kapinin-menzili-cagri-yeridir]]).
    def _kanca_deny(komut):
        girdi = {"tool_name": "Bash", "tool_input": {"command": komut},
                 "cwd": kok_hasat}
        tampon = io.StringIO()
        hata = io.StringIO()
        with redirect_stdout(tampon):
            _stderr, sys.stderr = sys.stderr, hata
            try:
                kanca(girdi, koku_root=gecici_kok)
            finally:
                sys.stderr = _stderr
        ham = tampon.getvalue().strip()
        if not ham:
            return False, hata.getvalue().strip()
        try:
            return (json.loads(ham).get("hookSpecificOutput", {})
                    .get("permissionDecision") == "deny"), hata.getvalue().strip()
        except Exception:
            return False, hata.getvalue().strip()

    okuma_denyleri = []
    okuma_jetonu = 0
    for komut in K345_OKUMA_KOMUTLARI:
        deny, err = _kanca_deny(komut)
        if deny:
            okuma_denyleri.append(komut)
        if N2B_OKUMA_JETON in err:
            okuma_jetonu += 1
    # BASLATMA vakalari: deny OLMAMALI, ama TESHIS basmali.
    baslatma_denyleri = []
    baslatma_teshissiz = []
    for komut in K345_BASLATMA_KOMUTLARI:
        deny, err = _kanca_deny(komut)
        if deny:
            baslatma_denyleri.append(komut)
        if "N2B HUKUM=" not in err:
            baslatma_teshissiz.append(komut)
    k13 = (not okuma_denyleri
           and okuma_jetonu == len(K345_OKUMA_KOMUTLARI)
           and not baslatma_denyleri
           and not baslatma_teshissiz)
    print("KONTROL K13 OKUMA/BASLATMA AYRI siniflanir, ikisi de GECER + "
          "teshis basar: %s" % ("GECTI" if k13 else "KUSUR"))
    print("    | okuma   : %d vaka · deny=%d (beklenen 0) · %s jetonu=%d/%d"
          % (len(K345_OKUMA_KOMUTLARI), len(okuma_denyleri), N2B_OKUMA_JETON,
             okuma_jetonu, len(K345_OKUMA_KOMUTLARI)))
    for k in okuma_denyleri:
        print("    |   🔴 REDDEDILDI (deny yolu SILINDI, olamaz): %s" % k[:88])
    print("    | baslatma: %d vaka · deny=%d (beklenen 0) · teshis EKSIK=%d "
          "(beklenen 0)"
          % (len(K345_BASLATMA_KOMUTLARI), len(baslatma_denyleri),
             len(baslatma_teshissiz)))
    for k in baslatma_denyleri:
        print("    |   🔴 REDDEDILDI (deny yolu SILINDI, olamaz): %s" % k[:88])
    for k in baslatma_teshissiz:
        print("    |   🔴 TESHISSIZ GECTI (sayi kayboldu): %s" % k[:88])
    kontrol += 1 if k13 else 0

    print("")
    print("MUTANT=%d/%d HEDEF_KOL_ATFI=%d/%d KONTROL=%d/%d"
          % (mutant_sayaci, len(MUTANT_HEDEF), atif_sayaci, len(MUTANT_HEDEF),
             kontrol, KONTROL_TABANI))
    return 0 if (mutant_sayaci == len(MUTANT_HEDEF)
                 and atif_sayaci == len(MUTANT_HEDEF)
                 and kontrol == KONTROL_TABANI) else 1


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--isci-kapi", nargs=4,
                    metavar=("MOTOR", "EV_KOKU", "SPEC", "ETIKET"),
                    help="isci.sh govdesinden cagrilan kol")
    ap.add_argument("--kanca", action="store_true",
                    help="PreToolUse kancasi (stdin'de JSON)")
    ap.add_argument("--kontrol", action="store_true", help="salt-okunur rapor")
    ap.add_argument("--ev", help="--kontrol icin EV adi")
    ap.add_argument("--esik", type=int, default=None)
    ap.add_argument("--kendini-test", action="store_true")
    ap.add_argument("--t4-durum", action="store_true",
                    help="T4 (bagimlilik) yuklendi mi? — DAGITIM teshisi")
    ap.add_argument("--t4-yolu", nargs="+", default=None, metavar="YOL",
                    help="--t4-durum icin aday yol kumesini DEGISTIRIR "
                         "(hermetik mutant; uretimde verilmez)")
    args = ap.parse_args(argv)

    if args.t4_durum:
        # 🔴 Bu yuzeyin TEK isi SEBEBI GORUNUR kilmaktir: kapinin fiziksel
        # varligi ("dosya var") ile calisirligi ("bagimliligi yuklenebiliyor")
        # AYNI SEY DEGILDIR [[aracin-teshis-cumlesi-olcum-degil]].
        mod, yol, hata = _t4_yukle(args.t4_yolu)
        print("N2B-T4 ADAYLAR=%s" % " ; ".join(t4_adaylari(args.t4_yolu)))
        print("N2B-T4 KAPI=%s" % os.path.abspath(__file__))
        if mod is None:
            print("N2B-T4 DURUM=YUKLENEMEDI SEBEP=%s" % hata)
            return RC_OLCULEMEDI
        print("N2B-T4 DURUM=YUKLENDI YOL=%s EV_SAYISI=%d"
              % (yol, len(getattr(mod, "EV_DIZIN", {}) or {})))
        return RC_GECER

    if args.kendini_test:
        gecici = tempfile.mkdtemp(prefix="n2b-kendinitest-")
        try:
            return kendini_test(gecici)
        finally:
            shutil.rmtree(gecici, ignore_errors=True)

    if args.isci_kapi:
        motor, ev_koku, spec, etiket = args.isci_kapi
        return isci_kapi(motor, ev_koku, spec, etiket, esik=args.esik)

    if args.kontrol:
        if T4 is None:
            print("HATA: T4 yuklenemedi")
            return RC_OLCULEMEDI
        # EV dogrudan verilir; depo koku cozumune GEREK YOK (ucuncu ev
        # tablosu acmamak icin — decode kayipli olurdu: `pruvo-hasat`in
        # tiresi ile yol ayraci ayirt edilemez).
        sonuc = parti_karari(None, "parti-kontrol", esik=args.esik,
                             ev=(args.ev or "KraL"))
        print("N2B PARTI KAPISI — KONTROL (salt-okunur, YAZMAZ)")
        if sonuc["HUKUM"] == HUKUM_RAPOR and sonuc["KOL"] == N2B_RED_JETON:
            print(red_metni(sonuc))
        elif sonuc["KOL"] == N2B_DEFTER_YOK_JETON:
            print("UCUNCU KOVA: %s" % (sonuc["SEBEP"] or ""))
        elif sonuc["HATA"]:
            print("HATA: %s" % sonuc["HATA"])
        print(hukum_satiri(sonuc))
        # 🔴 `--kontrol` SALT-OKUNUR bir rapordur; rc'si de bir tikayici
        # DEGILDIR. Acik kalem VARLIGI artik sifir-disi cikis uretmez.
        return RC_GECER

    # varsayilan: kanca modu
    try:
        girdi = json.load(sys.stdin)
    except Exception:
        return 0          # girdi okunamadi -> kapsam disi, sessiz gec
    if not isinstance(girdi, dict):
        return 0
    return kanca(girdi, esik=args.esik)


if __name__ == "__main__":
    sys.exit(main())
