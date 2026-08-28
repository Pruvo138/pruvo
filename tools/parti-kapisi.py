#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/parti-kapisi.py — N2 (B): ACIK 🔧 VARKEN YENI PARTI/ISCI **REDDEDILIR**.

Okan'in vakasi (birebir): "MaCiT 100-100 urun ekliyor, iletiyi gormedi, isine
devam etti; tamirat yapilmadigi icin tum mimarlar MaCiT'i bekledi."
HUKUM: **mesaj kacar, KAPI kacmaz.** Bu dosya iletiyi kapiya cevirir.

🔴 YARIM IS KESILMEZ. Bu kapi YALNIZ **YENI** is baslatmayi durdurur. Suren
   parti, yarim kalan toplu is, o partinin commit'i, `duzelt.py`, `git`
   — HICBIRI dokunulmaz. Okan'in vakasinda 100-100'un ORTASINDA kesmek
   zarardir; istenen, MaCiT'in **101.'yi baslatamamasidir**.
   Bu ayrim `N2B-YENI` / `N2B-SUREN` kollariyla makinece olculur ve M2
   mutantiyla kanitlanir (kol yanlis genislerse yarim is kesilir -> KUSUR).

IKI YUZEY (ikisi de ayni karar fonksiyonundan turer — ikinci mantik YOK)
------------------------------------------------------------------------
  1. `--isci-kapi <MOTOR> <EV_KOKU> <SPEC> <ETIKET>`
     `~/.claude/cron/isci.sh` govdesinden cagrilir. **CRON'u da kapsar** —
     `macit-parti-surucusu.sh` gibi surucler dogrudan crontab'tan kosar,
     PreToolUse kancasi onlari GORMEZ. Tek bogaz burasidir.
  2. `--kanca` (varsayilan; stdin'de PreToolUse JSON'u)
     Ajan oturumlarindaki Bash cagrilarini kapsar. 6 eve
     `tools/mimar-kapi-kur.py --parti-kapisi` ile dagitilir (IKINCI KURUCU YOK).

YEDI KOL (her birinin MUTANTI ve HEDEF KOL ATFI vardir — K182)
--------------------------------------------------------------
  N2B-YENI        cagri YENI is baslatiyor          -> T4 borc sorgusuna girer
  N2B-SUREN       cagri yeni is DEGIL (suren/yarim) -> GECER, ASLA kesilmez
  N2B-RED         sahibinin evinde acik kalem var   -> **RED** + kalem + `kabul:`
  N2B-MUAF        etiketin bir TOKEN'i tamir/onarim/ -> GECER (yoksa onarim
                  kabul/nobet/posta/devir ile basliyor  KENDINI bloklar: kilit)
  N2B-DEFTER-YOK  evin defter DOSYASI hic YOK       -> GECER ama SESSIZ DEGIL
                  (defter gelenegini benimsememis)     (jeton hukum satirinda
                                                       GORUNUR ve SAYILIR)
  N2B-OLCULEMEDI  ev cozulemedi / defter VAR ama    -> **RED** (fail-closed),
                  okunamadi (bos/bozuk/IO)             yalniz YENI is yolunda
  N2B-CAGRI-YERI  (N4A) muafiyet sozlesmesi GERCEK  -> batarya kolu: cagri
                  kaynak dosyalardan dogrulanir        yeri kayarsa KIRMIZI

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
     Bu yuzden defter VAR ama BOS/BOZUK ise kol HALA `N2B-OLCULEMEDI` = RED'dir.
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
    son satir + rc=0:  MUTANT=9/9 HEDEF_KOL_ATFI=9/9 KONTROL=10/10

  python3 tools/parti-kapisi.py --cagri-yeri   (N4A: cagri yeri sozlesmesi)
    rc=0 GECER · 1 RED (ihlal) · 2 OLCULEMEDI (kapsam tabani tutmadi)

  python3 tools/parti-kapisi.py --kontrol --ev MaCiT      (salt-okunur)
  python3 tools/parti-kapisi.py --t4-durum                (dagitim teshisi)

Cikis kodu (--isci-kapi): 0 = GECER · 1 = RED · 2 = OLCULEMEDI (RED sayilir).
Kanca modunda cikis kodu DAIMA 0'dir; hukum `permissionDecision` ile tasinir.
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
N2B_RED_JETON        = "N2B-RED"
N2B_MUAF_JETON       = "N2B-MUAF"
N2B_OLCULEMEDI_JETON = "N2B-OLCULEMEDI"
N2B_CAGRI_YERI_JETON = "N2B-CAGRI-YERI"
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
# 🔴 Gevsetme DEGIL: hukum yine RED (fail-closed korunur), yalniz SEBEBI dogru.
N2B_ETIKET_OKUNAMADI_JETON = "N2B-ETIKET-OKUNAMADI"
# Asagidaki iki jeton hukum satirinda GORUNMEZ; mutant ATFININ kol ADIDIR
# (her mutant YALNIZ kendi kolunu kirmizi yakmali — K182).
N2B_RED_METNI_JETON      = "N2B-RED-METNI"
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
SEBEP_MUAF             = "MUAF"
SEBEP_ACIK_KALEM       = "ACIK_KALEM"
SEBEP_ETIKET_OKUNAMADI = "ETIKET_OKUNAMADI"
SEBEP_OLCULEMEDI       = "OLCULEMEDI"
SEBEP_DEFTER_YOK       = "DEFTER_YOK"
SEBEP_TEMIZ            = "TEMIZ"

MUTANT_HEDEF = {
    "M1": N2B_YENI_JETON,
    "M2": N2B_SUREN_JETON,
    "M3": N2B_RED_JETON,
    "M4": N2B_OLCULEMEDI_JETON,
    "M5": N2B_MUAF_JETON,
    "M6": N2B_CAGRI_YERI_JETON,
    "M7": N2B_CAGRI_YERI_JETON,
    # 🔴 CAKISMA COZUMU (K229 tazeleme, 20 Agu): K229 dalinda bu iki mutant
    # M6/M7 idi; main'de N4A ayni numaralari CAGRI-YERI kolu icin ALDI. Ayni ada
    # iki rol verilseydi mutant KENDI kolunu degil komsununkini oldururdu ve
    # "yasadi" cikan sonuc "kol saglam" diye OKUNURDU [[ad-iki-rolde-mutanti-golgeler]].
    # Bu yuzden K229'un mutantlari M8/M9'a TASINDI (davranis AYNI, ad AYRI):
    #   M8 = kol BOZULUR      -> defteri olmayan ev yine RED yer (kilitlenme geri gelir)
    #   M9 = kol BIRLESTIRILIR-> hukum GECER kalir ama JETON OLCULEMEDI'ye doner
    #                            (ucuncu kova KAYBOLUR; yalniz HUKUM'e bakan test
    #                            bunu GORMEZ — jeton kontrolu SART)
    "M8": N2B_DEFTER_YOK_JETON,
    "M9": N2B_DEFTER_YOK_JETON,
    # 🔴 K345 — dort AYRI oldurme yolu, dort AYRI kol:
    #   M10 red metninin TURETILMISLIGI (elle ikinci kopya geri gelir)
    #   M11 etiket cikariminin BORU ONEKI normalizasyonu geri alinir
    #   M12 fail-closed GEVSETILIR (okunamayan etiket MUAF sayilir) -> KIRMIZI
    #   M13 sebep kovalari BIRLESTIRILIR (ucuncu kova yutulur)
    "M10": N2B_RED_METNI_JETON,
    "M11": N2B_ETIKET_CIKARIM_JETON,
    "M12": N2B_ETIKET_OKUNAMADI_JETON,
    "M13": N2B_ETIKET_OKUNAMADI_JETON,
    # 🔴 K345-C — okuma/baslatma kolunun IKI ayri oldurme yolu:
    #   M14 okuma kolu KALDIRILIR  -> salt-okuma yine RED yer (canli vaka geri)
    #   M15 baslatma "okuma" sayilir -> GERCEK baslatma SIZAR (kabul edilemez)
    "M14": N2B_OKUMA_JETON,
    "M15": N2B_OKUMA_JETON,
}

# 🔴 MUAF ETIKETLER — onarim hattinin KENDINI bloklamasini engeller.
# Acik kalem varken tamiri baslatamamak KILITLENMEDIR: kalem asla kapanmaz.
# Muafiyet DAR ve GORUNURDUR: hukum satirina `KOL=N2B-MUAF` yazilir.
# `posta` = posta kutusu izleyicisi — evin kalemi OGRENDIGI yol; bloklanirsa
# ev haberi hic almaz (Okan'in vakasinin ta kendisi).
MUAF_ETIKET_ONEKLERI = ("tamir", "onarim", "kabul", "nobet", "posta", "devir")

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


def muaf_onek_dizgesi():
    """Red metninin bastigi MUAF onek listesi — `MUAF_ETIKET_ONEKLERI`den TURER.

    🔴 Bu dizge ELLE YAZILMAZ. K11 kontrolu metindeki karsiligini bu ciktiya
    BIREBIR esitler (iki yonlu: `makine ⊆ metin` VE `metin ⊆ makine`).
    """
    return " · ".join(MUAF_ETIKET_ONEKLERI)


def dogru_cagri_bicimi():
    """Etiketi OKUNABILEN cagri sekilleri — `SARMALAYICI_ARGUMANLARI`dan TURER."""
    return ["%s/%s %s" % (SARMALAYICI_DIZINI, ad,
                          " ".join(SARMALAYICI_ARGUMANLARI[ad]))
            for ad in sorted(SARMALAYICI_ARGUMANLARI)]

# ==============================================================================
# 🔴 N4A (20 Agu 2026) — MUAFIYET, JETON LISTESIYLE DEGIL CAGRI YERIYLE OLCULUR
# ==============================================================================
# OLCULEN ARIZA: `MUAF_ETIKET_ONEKLERI` bir ONEK listesiydi ve eslesme
# `etiket.startswith(onek)` idi. Onarim hattinin GERCEK cagri yeri
# (`~/.claude/cron/nobet-kapi.py:1262`) etiketi **"ci-nobeti"** olarak yolluyor.
# `"ci-nobeti".startswith("nobet")` -> **False**: etiket "nobet"i ICERIR ama
# onunla BASLAMAZ. Sonuc (19 Agu 23:53Z -> 20 Agu 08:xxZ, gozcu.log'da sayildi):
#   * 21/21 CI_KIRMIZI turunda `isci.sh` **exit 3** (N2B-RED),
#   * `nobet-kapi.py` -> `HUKUM=MOTOR_YOK rc=1`, gozcu kalbinde `icra_rc=1`,
#   * `ustuste_onarimsiz` 105'e cikti ve DUSMEDI.
# Yani kapinin "onarim hatti kendini bloklamasin" diye konmus MUAF kolu, tam da
# onarim hattini bloklladi — ve batarya YESIL yandi, cunku sentetik vakalari
# (`tamir-k99`, `posta-macit`) UYDURULMUS etiketlerdi: GERCEK cagri yerinin
# etiketi bataryada HIC yoktu ([[kapinin-menzili-cagri-yeridir]]).
#
# SINIF COZUMU (tekil yama DEGIL):
#   (a) Eslesme TOKEN SINIRINDA yapilir — etiket `[^a-z0-9]` ile parcalanir ve
#       HERHANGI bir parca bir onekle basliyorsa MUAF. "ci-nobeti" -> ["ci",
#       "nobeti"] -> "nobeti".startswith("nobet") -> True. Genisleme DAR kalir:
#       serbest ALT-DIZE degil, TOKEN BASI.
#   (b) Muafiyet artik GERCEK CAGRI YERLERINE karsi olculur: asagidaki tablo
#       kaynak dosyalari + BEKLENEN muafiyeti listeler; K8 kontrolu dosyalari
#       OKUYUP etiket literalini CIKARIR ve hukmu dogrular. Bir cagri yeri
#       yeniden adlandirilirsa ya da yeni bir cagri yeri eklenirse batarya
#       kirmizi yanar — sessiz ayrisma imkansizlasir.
#   (c) KAPSAM TABANI SAYIYLA CIVILENIR (`CAGRI_YERI_TABANI`): tarayici hicbir
#       sey bulamazsa "ihlal yok" diye YESIL yanmaz, `OLCULEMEDI` doner
#       ([[batarya-kapsam-tabani-sayiyla-civilenir]]). M6 mutanti bunu olcer.
#
# BEKLENTI KAYNAGIN ROLUNDEN gelir, etiketinden DEGIL — aksi halde tablo
# tautoloji olurdu ("etiket muaf cunku muaf listesinde"). `parti-surucusu`
# satiri POZITIF DEGIL NEGATIF kontroldur: muaf OLMAMALIDIR.
CAGRI_YERI_KAYNAKLARI = (
    # (yol, beklenen_muaf, rol)
    ("/Users/okan/.claude/cron/nobet-kapi.py", True, "onarim-hatti"),
    ("/Users/okan/.claude/cron/posta-kutusu-macit-izleme.sh", True, "posta-hatti"),
    ("/Users/okan/.claude/cron/posta-kutusu-kaan-izleme.sh", True, "posta-hatti"),
    ("/Users/okan/.claude/cron/macit-parti-surucusu.sh", False, "parti-hatti"),
)
# 🔴 Kapsam tabani: bu sayidan AZ cagri yeri cozulurse hukum OLCULEMEDI'dir.
CAGRI_YERI_TABANI = 4

# Etiket literali cikarimi — IKI bicim, ikisi de DAR:
#   (py) `[ISCI_SH, motor, EV_KOKU, GOREV_YOLU, "ci-nobeti"]`
#   (sh) `ETIKET=posta-macit` / `ETIKET="posta-macit"`
_PY_ETIKET_RE = re.compile(
    r"""ISCI_SH\s*,[^\[\]]*?["']([A-Za-z0-9][A-Za-z0-9._-]*)["']\s*\]""")
_SH_ETIKET_RE = re.compile(
    r"""^\s*ETIKET=["']?([A-Za-z0-9][A-Za-z0-9._-]*)["']?\s*$""", re.M)

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
RC_RED = 1
RC_OLCULEMEDI = 2


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
    ters = {}
    for ev, dizin in t4.EV_DIZIN.items():
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
# YENI IS MI? — N2B-YENI / N2B-SUREN kollari
# ------------------------------------------------------------------------------
def etiket_parcalari(etiket):
    """Etiketi TOKEN'lara ayirir: `ci-nobeti` -> ['ci', 'nobeti'].

    Ayirici `[^a-z0-9]+`: tire, altcizgi, nokta, bosluk. Bos parcalar atilir.
    """
    e = (etiket or "").strip().lower()
    return [p for p in re.split(r"[^a-z0-9]+", e) if p]


def muaf_etiket_mi(etiket, *, mutant=None):
    """Etiket onarim/nobet/posta hattina mi ait? (N2B-MUAF kolu)

    🔴 N4A: eslesme TOKEN SINIRINDADIR, dize BASI degil. `ci-nobeti` gercek
    cagri yerinin (nobet-kapi.py:1262) etiketidir ve `startswith("nobet")`
    ile ESLESMIYORDU -> onarim hatti 21 turda kendini blokladi. Genisleme DAR:
    serbest alt-dize DEGIL, yalniz bir TOKEN'in onekle baslamasi.
    """
    if mutant == "M5":
        return False          # muafiyet oldurulur -> onarim kendini bloklar
    if mutant == "M7":
        # 🔴 REGRESYON MUTANTI: N4A oncesi davranis (yalniz dize basi). Bu
        # mutant altinda GERCEK cagri yeri `ci-nobeti` muaf OLMAZ -> K8 kirmizi.
        e = (etiket or "").strip().lower()
        return any(e.startswith(on) for on in MUAF_ETIKET_ONEKLERI)
    parcalar = etiket_parcalari(etiket)
    return any(p.startswith(on) for p in parcalar
               for on in MUAF_ETIKET_ONEKLERI)


# ------------------------------------------------------------------------------
# CAGRI YERI TARAMASI — muafiyet sozlesmesi GERCEK kaynak dosyalara baglanir
# ------------------------------------------------------------------------------
def _etiket_literalleri(metin, yol):
    """Bir kaynak dosyanin metninden `isci.sh` etiket literallerini cikarir."""
    if yol.endswith(".py"):
        return _PY_ETIKET_RE.findall(metin)
    return _SH_ETIKET_RE.findall(metin)


def cagri_yeri_taramasi(kaynaklar=None, *, mutant=None):
    """Cagri yerlerini okur; (yol, rol, etiket, beklenen, gercek) uretir.

    🔴 FAIL-LOUD: dosya VAR ama etiket literali cikarilamiyorsa `etiket` None
    dondurulur ve bu bir KAPSAM KAYBIDIR (sessizce atlanmaz).
    🔴 Dosyanin HIC OLMAMASI ayri bir haldir (`VAR: False`) — CI kosucusunda
    `~/.claude/cron` yoktur ve bu bir kusur DEGILDIR; hukum fonksiyonu ikisini
    AYIRIR (KAPSAM_DISI vs OLCULEMEDI).
    """
    kaynaklar = CAGRI_YERI_KAYNAKLARI if kaynaklar is None else kaynaklar
    bulgular = []
    for yol, beklenen, rol in kaynaklar:
        temel = {"YOL": yol, "ROL": rol, "BEKLENEN": beklenen,
                 "ETIKET": None, "GERCEK": None, "VAR": False, "HATA": None}
        if not os.path.isfile(yol):
            temel["HATA"] = "DOSYA YOK (bu makinede onarim hatti kurulu degil)"
            bulgular.append(temel)
            continue
        temel["VAR"] = True
        try:
            with open(yol, encoding="utf-8", errors="replace") as dosya:
                metin = dosya.read()
        except OSError as hata:
            temel["HATA"] = "%s: %s" % (type(hata).__name__, hata)
            bulgular.append(temel)
            continue
        # M6: dosya YERINDE ama tarayici korlesiyor — "kapsam kaybi" kolu.
        etiketler = [] if mutant == "M6" else _etiket_literalleri(metin, yol)
        if not etiketler:
            temel["HATA"] = "etiket literali CIKARILAMADI"
            bulgular.append(temel)
            continue
        for etiket in etiketler:
            kayit = dict(temel)
            kayit["ETIKET"] = etiket
            kayit["GERCEK"] = muaf_etiket_mi(etiket, mutant=mutant)
            bulgular.append(kayit)
    return bulgular


def cagri_yeri_hukmu(kaynaklar=None, *, mutant=None, taban=None):
    """Cagri yerlerinin muafiyeti BEKLENEN ile ortusuyor mu?

    HUKUM:
      KAPSAM_DISI — kaynaklarin HICBIRI bu makinede yok (CI kosucusu). Kusur
                    DEGILDIR: olculecek sozlesme fiziksel olarak burada degil.
                    🔴 Bu kol bir muafiyet DELIGI olmasin diye mekanizmanin
                    kendisi HERMETIK FIKSTURLERLE ayrica mutasyona tabi tutulur
                    (bkz. `_fikstur_kaynaklari`) ve K8'in uctan-uca ayagi
                    (gercek etiket -> gercek kapi) her ortamda kosar.
      OLCULEMEDI  — kaynak VAR ama cozulen sayisi TABAN'in altinda (kapsam kaybi)
      RED         — en az bir cagri yerinde beklenen != gercek
      GECER       — taban tutuyor ve ihlal yok
    """
    taban = CAGRI_YERI_TABANI if taban is None else taban
    bulgular = cagri_yeri_taramasi(kaynaklar, mutant=mutant)
    mevcut = [b for b in bulgular if b["VAR"]]
    cozulen = [b for b in bulgular if b["ETIKET"] is not None]
    ihlal = [b for b in cozulen if b["BEKLENEN"] != b["GERCEK"]]
    kapsam_kaybi = [b for b in bulgular if b["VAR"] and b["ETIKET"] is None]
    if not mevcut:
        hukum = "KAPSAM_DISI"
    elif len(cozulen) < taban:
        hukum = "OLCULEMEDI"
    elif ihlal:
        hukum = "RED"
    else:
        hukum = "GECER"
    return {"HUKUM": hukum, "KOL": N2B_CAGRI_YERI_JETON, "SAYI": len(cozulen),
            "TABAN": taban, "IHLAL": ihlal, "KAPSAM_KAYBI": kapsam_kaybi,
            "MEVCUT": len(mevcut), "BULGULAR": bulgular}


# --- HERMETIK FIKSTURLER ------------------------------------------------------
# 🔴 Mutant olcumu ORTAMA BAGLI OLAMAZ. Gercek cron dosyalari CI kosucusunda
# yoktur; mutantlari yalniz onlarla olcseydik CI'da M6/M7 "olculemedi" olur ve
# batarya kendi kapsamini SESSIZCE kaybederdi. Bu yuzden mekanizma (tarayici +
# eslesme + hukum) HER ORTAMDA var olan iki fiksturle mutasyona tabi tutulur;
# GERCEK dosyalar ise K8'de AYRICA olculur (ikisi birbirinin yerine GECMEZ).
# Fikstur govdeleri gercek cagri yerlerinin BICIMINI birebir tasir.
_FIKSTUR_PY = (
    "import subprocess\n"
    "ISCI_SH = '/x/isci.sh'\n"
    "def _kos(motor, EV_KOKU, GOREV_YOLU):\n"
    "    return subprocess.Popen(\n"
    "        [ISCI_SH, motor, EV_KOKU, GOREV_YOLU, \"ci-nobeti\"],\n"
    "    )\n"
)
_FIKSTUR_SH = (
    "#!/bin/sh\n"
    "EV_KOKU=/x\n"
    "ETIKET=parti-surucusu\n"
    "exec /x/isci.sh minimax-m3 \"$EV_KOKU\" \"$SPEC\" \"$ETIKET\"\n"
)
FIKSTUR_TABANI = 2


def _fikstur_kaynaklari(dizin):
    """Iki hermetik cagri yeri yazar: biri MUAF olmali, biri OLMAMALI."""
    py_yolu = os.path.join(dizin, "fikstur-nobet-kapi.py")
    sh_yolu = os.path.join(dizin, "fikstur-parti-surucusu.sh")
    with open(py_yolu, "w", encoding="utf-8") as dosya:
        dosya.write(_FIKSTUR_PY)
    with open(sh_yolu, "w", encoding="utf-8") as dosya:
        dosya.write(_FIKSTUR_SH)
    return ((py_yolu, True, "onarim-hatti-fikstur"),
            (sh_yolu, False, "parti-hatti-fikstur"))


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
    sonuc = {"HUKUM": "RED", "KOL": N2B_OLCULEMEDI_JETON, "EV": None,
             "ACIK": 0, "KALEMLER": [], "KABUL_KOMUTU": None,
             "SEBEP": None, "SEBEP_KODU": SEBEP_OLCULEMEDI, "HATA": None,
             "ETIKET": etiket}

    if muaf_etiket_mi(etiket, mutant=mutant):
        sonuc["HUKUM"] = "GECER"
        sonuc["KOL"] = N2B_MUAF_JETON
        sonuc["SEBEP_KODU"] = SEBEP_MUAF
        # 🔴 K345: onek listesi burada IKINCI KEZ YAZILMAZ — TURETILIR.
        sonuc["SEBEP"] = ("%s onarim hatti — kilitlenmemek icin muaf "
                          "(etiket=%s · muaf onekler: %s)"
                          % (N2B_MUAF_JETON, etiket, muaf_onek_dizgesi()))
        if ev is None and t4 is not None:
            ev, _h = ev_coz(ev_koku, t4=t4)
        sonuc["EV"] = ev
        return sonuc

    # 🔴 K345 — UCUNCU KOVA: ETIKET OKUNAMADI.
    # Bos etiket zaten MUAF DEGILDI (yukaridaki kol onu gecirmez); ONCEDEN
    # sessizce "muaf olmayan etiket" kovasina dusuyor ve acik kalem sayimina
    # gidiyordu. Sonuc: red metni YANLIS SEBEBI gosteriyordu (30 kalem
    # siralaniyordu, oysa kusur etiketteydi) — ve kalemsiz evde HIC olcum
    # yapilmadan GECIYORDU (fail-OPEN sizintisi). Artik KENDI kovasi var:
    # hukum RED (fail-closed KORUNUR), sebep ETIKET_OKUNAMADI.
    if not (etiket or "").strip():
        if mutant == "M12":
            # GEVSETME MUTANTI: okunamayan etiket MUAF sayilir. Bu mutant
            # KIRMIZI YANMALIDIR — muafiyeti etiketin ICERIGI degil
            # OKUNABILMESI verir ([[isci-cagrisinda-echo-stdin-etiketi-yutar]]).
            sonuc["HUKUM"] = "GECER"
            sonuc["KOL"] = N2B_MUAF_JETON
            sonuc["SEBEP_KODU"] = SEBEP_MUAF
            sonuc["SEBEP"] = "M12: okunamayan etiket MUAF sayildi"
        elif mutant == "M13":
            # KOVA BIRLESTIRME MUTANTI: ucuncu kova ikinciye indirgenir.
            # HUKUM ayni kalabilir (RED) — yalniz HUKUM'e bakan bir test bunu
            # GORMEZ; JETON + SEBEP KODU kontrolu SART ([[M9 dersi]]).
            sonuc["KOL"] = N2B_RED_JETON
            sonuc["SEBEP_KODU"] = SEBEP_ACIK_KALEM
            sonuc["SEBEP"] = "M13: etiket kovasi acik-kalem kovasina yutuldu"
        else:
            sonuc["KOL"] = N2B_ETIKET_OKUNAMADI_JETON
            sonuc["SEBEP_KODU"] = SEBEP_ETIKET_OKUNAMADI
            sonuc["SEBEP"] = (
                "%s cagrinin ETIKETI okunamadi (yok / gomulu / belirsiz). "
                "Muafiyeti etiketin ICERIGI degil OKUNABILMESI verir; "
                "okunamayan etiket fail-closed REDDEDILIR."
                % N2B_ETIKET_OKUNAMADI_JETON)
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
    if ev is None or ev not in t4.EV_BILINEN:
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
        if mutant == "M3":
            sonuc["HUKUM"] = "GECER"          # RED kolu oldurulur
            sonuc["KOL"] = N2B_SUREN_JETON
            sonuc["SEBEP"] = "M3: RED yutuldu"
            return sonuc
        kalemler, _okundu, _h = t4.acik_kalem_listesi(borc["DEFTER_YOLU"] or "")
        sonuc["KALEMLER"] = kalemler
        sonuc["KOL"] = N2B_RED_JETON
        sonuc["HUKUM"] = "RED"
        sonuc["SEBEP_KODU"] = SEBEP_ACIK_KALEM
        sonuc["KABUL_KOMUTU"] = kabul_komutu(ev)
        sonuc["SEBEP"] = borc["RED_SEBEBI"]
        return sonuc

    sonuc["HUKUM"] = "GECER"
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


# Red metnindeki TURETILMIS bloklarin sinir dizgeleri. K11 kontrolu metni bu
# sinirlarla parcalayip turetilmis ciktiya BIREBIR esitler; sinir tekil degilse
# hukum `OLCULEMEDI` = KIRMIZI (fail-closed) — yoksa metin yeniden yazildiginda
# kol sessizce yesile donerdi ([[kapi-red-metni-ikinci-kopyadir]]).
RED_METNI_ONEK_SINIRI = "MUAF ETIKET ONEKLERI: "
RED_METNI_CAGRI_BASLIGI = ("GECEN CAGRI BICIMI (kaynaktan TURETILDI — bu "
                           "metinde ikinci liste YOKTUR):")
RED_METNI_CAGRI_ONEKI = "  $ "


def red_metni(sonuc, *, mutant=None):
    """RED gerekcesinin insan-okur govdesi.

    🔴 K345 — bu metin artik UC seyi birden tasir:
      (1) SEBEP AYRIMI: `ACIK_KALEM` ile `ETIKET_OKUNAMADI` **AYRI SATIRLARDIR**
          ve hangisinin atesledigi isaretlenir. Onceden tek gerekce vardi
          ("acik kalem varken yeni parti BASLATILAMAZ") ve etiketi okunamayan
          bir cagri o metni okuyup YANLIS kusuru kapatmaya calisiyordu.
      (2) CALISAN CAGRI BICIMI — `SARMALAYICI_ARGUMANLARI`den TURETILIR.
      (3) MUAF ONEKLER — `MUAF_ETIKET_ONEKLERI`den TURETILIR.
    (2) ve (3) ELLE YAZILMAZ; K11 kontrolu iki yonlu esitlikle olcer.
    """
    kod = sonuc.get("SEBEP_KODU") or "-"
    satirlar = []
    satirlar.append("N2B PARTI KAPISI — YENI IS REDDEDILDI (ev=%s · sebep=%s)."
                    % (sonuc["EV"], kod))
    satirlar.append("🔴 SUREN IS KESILMEZ — bu kapi yalnizca YENI is acmayi "
                    "durdurur.")

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
    satirlar.append("(kalem KAPANDI olunca ayni komut GECER doner; kapi "
                    "kalici kilit DEGILDIR.)")

    # --- TURETILMIS BLOK: CALISAN CAGRI YOLU ------------------------------
    satirlar.append(RED_METNI_CAGRI_BASLIGI)
    for bicim in dogru_cagri_bicimi():
        satirlar.append(RED_METNI_CAGRI_ONEKI + bicim)
    if mutant == "M10":
        # TURETIM KIRMA MUTANTI: onek listesi ELLE yazilir (ikinci kopya geri
        # gelir). K11 iki yonlu esitlikte bunu KIRMIZI yakmalidir.
        satirlar.append(RED_METNI_ONEK_SINIRI + "tamir · onarim · kabul")
    else:
        satirlar.append(RED_METNI_ONEK_SINIRI + muaf_onek_dizgesi())
    # 🔴 Ornek etiket de TURETILIR (elle ikinci onek yazilmaz): listenin ILK
    # onegi alinir ve token-sinirini gosteren bir ornek uretilir.
    _ornek_onek = MUAF_ETIKET_ONEKLERI[0]
    satirlar.append(
        "ETIKET KURALI 1/2: eslesme TOKEN sinirindadir — `ci-%si` de MUAF'tir "
        "(`%s` onegiyle BASLAYAN bir token tasir), dize BASI sart degildir."
        % (_ornek_onek, _ornek_onek))
    satirlar.append(
        "ETIKET KURALI 2/2: boru/yonlendirme SERBESTTIR (onekteki `echo \"\" |` "
        "artik etiketi YUTMAZ); ama etiket okunamazsa hukum fail-closed RED'dir "
        "— muafiyeti etiketin ICERIGI degil OKUNABILMESI verir.")
    return "\n".join(satirlar)


def hukum_satiri(sonuc):
    """Makine-okur tek satir. Kabul testleri BU satiri arar.

    🔴 K345: `SEBEP=` alani SONA EKLENDI (mevcut alanlarin sirasi/adi
    DEGISMEDI — eski okuyucular kirilmaz). Uc kova artik UC AYRI satir basar:
    `KOL=N2B-MUAF ... SEBEP=MUAF` · `KOL=N2B-RED ... SEBEP=ACIK_KALEM` ·
    `KOL=N2B-ETIKET-OKUNAMADI ... SEBEP=ETIKET_OKUNAMADI`.
    """
    kalem = ",".join(k["kimlik"] for k in sonuc["KALEMLER"]) or "-"
    return "N2B HUKUM=%s KOL=%s EV=%s ACIK=%d KALEM=%s SEBEP=%s" % (
        sonuc["HUKUM"], sonuc["KOL"], sonuc["EV"] or "-", sonuc["ACIK"], kalem,
        sonuc.get("SEBEP_KODU") or "-")


# ------------------------------------------------------------------------------
# K345 — RED METNI TURETIM PROBU (K11'in olcen govdesi)
# ------------------------------------------------------------------------------
def red_metni_turetim_hukmu(*, mutant=None):
    """Red metnindeki TURETILMIS bloklari kaynaga BIREBIR esitler.

    🔴 IKI YONLU: `makine ⊆ metin` YETMEZ — `metin ⊆ makine` de olculur, yoksa
    metin makinenin izin VERMEDIGI bir seyi vaat edebilir ve nobetci susar
    ([[kapi-red-metni-ikinci-kopyadir]] 28 Agu eki).
    🔴 Sinir dizgesi TEKIL degilse hukum `OLCULEMEDI` = KIRMIZI (fail-closed).

    Return: {"HUKUM": "GECER"|"RED"|"OLCULEMEDI", "IHLAL": [...],
             "ELLE_KOPYA": int}
    """
    ornek = {"HUKUM": "RED", "KOL": N2B_RED_JETON, "EV": "MaCiT", "ACIK": 30,
             "KALEMLER": [{"kimlik": "K901", "durum": "🔧", "is": "ornek"}],
             "KABUL_KOMUTU": kabul_komutu("MaCiT"),
             "SEBEP_KODU": SEBEP_ACIK_KALEM, "SEBEP": None, "HATA": None,
             "ETIKET": "parti-surucusu"}
    metin = red_metni(ornek, mutant=mutant)
    satirlar = metin.splitlines()
    ihlal = []

    # (a) MUAF ONEK BLOGU — sinir TEKIL mi?
    onek_satirlari = [s for s in satirlar if s.startswith(RED_METNI_ONEK_SINIRI)]
    if len(onek_satirlari) != 1:
        return {"HUKUM": "OLCULEMEDI", "ELLE_KOPYA": -1,
                "IHLAL": ["muaf-onek siniri TEKIL DEGIL (adet=%d)"
                          % len(onek_satirlari)]}
    metindeki = onek_satirlari[0][len(RED_METNI_ONEK_SINIRI):]
    turetilen = muaf_onek_dizgesi()
    if metindeki != turetilen:
        ihlal.append("muaf onek: metin=%r != turetilen=%r"
                     % (metindeki, turetilen))

    # (b) CAGRI BICIMI BLOGU — sinir TEKIL mi?
    baslik_indeksleri = [i for i, s in enumerate(satirlar)
                         if s == RED_METNI_CAGRI_BASLIGI]
    if len(baslik_indeksleri) != 1:
        return {"HUKUM": "OLCULEMEDI", "ELLE_KOPYA": -1,
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

    # (c) ELLE IKINCI KOPYA SAYIMI — metnin GERI KALANINDA muaf onek listesi
    #     yeniden sayiliyor mu? (turetilmis satirlar HARIC tutulur)
    elle = 0
    for s in satirlar:
        if s.startswith(RED_METNI_ONEK_SINIRI):
            continue
        parcalar = [p for p in re.split(r"[^a-z0-9]+", s.lower()) if p]
        kac = len({on for p in parcalar for on in MUAF_ETIKET_ONEKLERI
                   if p.startswith(on)})
        if kac >= 2:
            elle += 1
            ihlal.append("ELLE IKINCI KOPYA (>=2 muaf onek tek satirda): %r"
                         % s[:80])
    return {"HUKUM": "RED" if ihlal else "GECER", "IHLAL": ihlal,
            "ELLE_KOPYA": elle}


# 🔴 K345 — PROB KORLUK FIKSTURU (hermetik, git'e ve ortama BAGIMSIZ).
# `URETIM=0` iki AYRI seyin cikti olabilir: "kaynak temiz" ya da "prob kor".
# Bu fikstur ikisini ayirir: probun GORMESI GEREKEN bir uretim kopyasi ve
# GORMEMESI gereken bir mutant yuku ayni metinde durur.
# Uretim satiri HEAD'deki GERCEK kopyanin birebir kendisidir (512. satir).
# 🔴 Fikstur METNI de TURETILIR: govdesine elle bir onek listesi yazsaydik
# probun KENDI kaynagi bir "uretim kopyasi" sayilirdi (ilk surumde tam bu
# oldu, K11 KIRMIZI yandi — kurucu kendi kapisina takilir).
_KORLUK_BEKLENEN = {"URETIM": 1, "DOCSTRING": 1, "MUTANT_YUKU": 1}


def _korluk_fiksturu():
    liste = "/".join(MUAF_ETIKET_ONEKLERI[:3])
    return (
        "def f(etiket, *, mutant=None):\n"
        '    """belge: %s"""\n'
        "    if muaf_etiket_mi(etiket, mutant=mutant):\n"
        '        return "%s hatti — kilitlenmemek icin muaf"\n'
        "    if mutant == 'M10':\n"
        '        return "%s"\n'
        '    return ""\n' % (liste, liste, " · ".join(MUAF_ETIKET_ONEKLERI)))


def elle_kopya_kaynak_sayimi(yol=None, *, kaynak=None):
    """KAYNAKTA kalan ELLE muaf-onek listesi sayisi (uretim yolunda).

    🔴 `red_metni_turetim_hukmu` URETILEN METNI olcer; bu fonksiyon KAYNAGI
    olcer. Ikisi ayri eksendir: metin bugun temiz olabilir ve kaynakta uyuyan
    ikinci bir liste yarin baska bir kolda basilabilir.

    HARIC TUTULANLAR (ve NEDEN):
      * docstring'ler — cikti degil, BELGEdir (ayri sayilir, ayri basilir).
      * `if mutant == ...` govdesindeki literaller — MUTANT YUKUDUR; M10'un
        elle listesi olmadan turetim kolunun isirdigi ISPATLANAMAZ
        ([[kabul-fiksturu-yasagi-kutsar]] tersi: burada fikstur yasagi
        KUTSAMIYOR, mutantin KENDISI oluyor).
    Return: {"URETIM": int, "DOCSTRING": int, "MUTANT_YUKU": int,
             "SATIRLAR": [...], "HATA": str|None}
    """
    import ast
    yol = yol or os.path.abspath(__file__)
    try:
        if kaynak is not None:
            pass                              # cagiran kaynagi DOGRUDAN verdi
        elif isinstance(yol, str) and yol.startswith("git:"):
            # `git:<ref>` — ONCE/SONRA sayisini ayni tanimla olcmek icin.
            ref = yol[4:]
            kaynak = subprocess.run(
                ["git", "-C", os.path.dirname(os.path.abspath(__file__)),
                 "show", "%s:tools/parti-kapisi.py" % ref],
                capture_output=True, text=True, check=True).stdout
        else:
            kaynak = open(yol, encoding="utf-8").read()
        agac = ast.parse(kaynak)
    except Exception as e:                      # fail-closed: olculemedi
        return {"URETIM": -1, "DOCSTRING": -1, "MUTANT_YUKU": -1,
                "SATIRLAR": [], "HATA": "%s: %s" % (type(e).__name__, e)}

    docstring_idleri = set()
    for d in ast.walk(agac):
        govde = getattr(d, "body", None) or []
        if isinstance(d, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                          ast.ClassDef)) and govde:
            ilk = govde[0]
            if (isinstance(ilk, ast.Expr)
                    and isinstance(ilk.value, ast.Constant)
                    and isinstance(ilk.value.value, str)):
                docstring_idleri.add(id(ilk.value))

    # `if mutant == "MXX":` govdelerindeki tum literalleri isaretle.
    # 🔴 KOSUL DAR TUTULUR: SOL TARAFI CIPLAK `mutant` ADI olan bir
    # KARSILASTIRMA. Gevsek eslesme (kosul metninde "mutant" GECIYOR mu?)
    # `if muaf_etiket_mi(etiket, mutant=mutant):` govdesini de muaf sayardi ve
    # URETIM yolundaki GERCEK ikinci kopyayi (HEAD'deki SEBEP dizgesi) MUTANT
    # YUKU diye AKLARDI — olculdu, ilk surumde tam bu oldu.
    mutant_idleri = set()
    for d in ast.walk(agac):
        if not isinstance(d, ast.If):
            continue
        test = d.test
        if not (isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name)
                and test.left.id == "mutant"):
            continue
        for alt in d.body:
            for x in ast.walk(alt):
                if isinstance(x, ast.Constant) and isinstance(x.value, str):
                    mutant_idleri.add(id(x))

    sayac = {"URETIM": 0, "DOCSTRING": 0, "MUTANT_YUKU": 0}
    satirlar = []
    for d in ast.walk(agac):
        if not (isinstance(d, ast.Constant) and isinstance(d.value, str)):
            continue
        parcalar = [p for p in re.split(r"[^a-z0-9]+", d.value.lower()) if p]
        kac = len({on for p in parcalar for on in MUAF_ETIKET_ONEKLERI
                   if p.startswith(on)})
        if kac < 2:
            continue
        if id(d) in docstring_idleri:
            sayac["DOCSTRING"] += 1
        elif id(d) in mutant_idleri:
            sayac["MUTANT_YUKU"] += 1
        else:
            sayac["URETIM"] += 1
            satirlar.append("satir %d: %r" % (d.lineno,
                                              d.value[:70].replace("\n", " ")))
    sayac["SATIRLAR"] = satirlar
    sayac["HATA"] = None
    return sayac


# ------------------------------------------------------------------------------
# YUZEY 1: --isci-kapi (isci.sh govdesinden; CRON'u da kapsar)
# ------------------------------------------------------------------------------
def isci_kapi(motor, ev_koku, spec, etiket, *, esik=None, koku_root=None,
              mutant=None, t4=_MIRAS, t4_hata=None):
    """isci.sh'in cagirdigi kol. rc: 0 GECER · 1 RED · 2 OLCULEMEDI."""
    sonuc = parti_karari(ev_koku, etiket, esik=esik, koku_root=koku_root,
                         mutant=mutant, t4=t4, t4_hata=t4_hata)
    if sonuc["HUKUM"] == "RED":
        if sonuc["KOL"] == N2B_OLCULEMEDI_JETON:
            sys.stderr.write((sonuc["HATA"] or N2B_OLCULEMEDI_JETON) + "\n")
            sys.stderr.write(hukum_satiri(sonuc) + "\n")
            return RC_OLCULEMEDI
        sys.stderr.write(red_metni(sonuc) + "\n")
        sys.stderr.write(hukum_satiri(sonuc) + "\n")
        return RC_RED
    # 🔴 K229: GECER ama SESSIZ DEGIL — ucuncu kova gerekcesini isci.sh
    # gunlugune de yazar (jeton zaten hukum satirinda).
    if sonuc["KOL"] == N2B_DEFTER_YOK_JETON and sonuc["SEBEP"]:
        sys.stderr.write(sonuc["SEBEP"] + "\n")
    sys.stdout.write(hukum_satiri(sonuc) + "\n")
    return RC_GECER


# ------------------------------------------------------------------------------
# YUZEY 2: --kanca (PreToolUse)
# ------------------------------------------------------------------------------
def _reddet(neden):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": neden,
        }
    }, ensure_ascii=False))
    return 0


def kanca(girdi, *, esik=None, koku_root=None, mutant=None, t4=_MIRAS,
          t4_hata=None):
    """PreToolUse girdisini hukme baglar. DAIMA rc=0; hukum JSON'da."""
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
    if sonuc["HUKUM"] == "RED":
        if sonuc["KOL"] == N2B_OLCULEMEDI_JETON:
            return _reddet("%s\n%s" % (sonuc["HATA"] or N2B_OLCULEMEDI_JETON,
                                       hukum_satiri(sonuc)))
        return _reddet("%s\n%s" % (red_metni(sonuc), hukum_satiri(sonuc)))
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
        # MaCiT'in evinde acik kalem VAR -> yeni parti REDDEDILIR
        ("macit-yeni-parti", kok_hasat, "parti-surucusu",
         "%s minimax-m3 %s /tmp/s.md parti-surucusu" % (isci, kok_hasat),
         "RED", N2B_RED_JETON),
        # ayni evde onarim etiketi -> MUAF (kilitlenme yok)
        ("macit-tamir", kok_hasat, "tamir-k99",
         "%s kimi %s /tmp/s.md tamir-k99" % (isci, kok_hasat),
         "GECER", N2B_MUAF_JETON),
        # ayni evde posta izleyicisi -> MUAF (kalem HABERI bu yoldan gelir)
        ("macit-posta", kok_hasat, "posta-macit",
         "%s minimax-m3 %s /tmp/s.md posta-macit" % (isci, kok_hasat),
         "GECER", N2B_MUAF_JETON),
        # KraL'in evinde acik kalem YOK -> yeni parti GECER
        ("kral-yeni-parti", kok_kral, "parti-surucusu",
         "%s kimi %s /tmp/s.md parti-surucusu" % (isci, kok_kral),
         "GECER", N2B_SUREN_JETON),
        # 🔴 K229 UCUNCU KOVA: HocA'nin evinde defter DOSYASI hic YOK
        # -> GECER + KENDI jetonu (ne RED, ne sessiz gecis)
        ("hoca-defter-yok", kok_bot, "parti-surucusu",
         "%s kimi %s /tmp/s.md parti-surucusu" % (isci, kok_bot),
         "GECER", N2B_DEFTER_YOK_JETON),
        # 🔴 SINIR: defter VAR ama BOS -> olculmemis sifir, HALA fail-closed RED
        # (ucuncu kova ikinci kovayi YUTMAZ)
        ("tekin-defter-bos", kok_jen, "parti-surucusu",
         "%s kimi %s /tmp/s.md parti-surucusu" % (isci, kok_jen),
         "RED", N2B_OLCULEMEDI_JETON),
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

    fikstur_dizini = os.path.join(gecici_kok, "cagri-yeri-fikstur")
    os.makedirs(fikstur_dizini, exist_ok=True)
    fikstur_kaynaklari = _fikstur_kaynaklari(fikstur_dizini)

    print("N2B PARTI KAPISI — KENDINI-TEST")
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
        # N4A: cagri yeri MEKANIZMASI hermetik fiksturlerle olculur (her
        # ortamda ayni). GERCEK cron dosyalari K8'de AYRICA olculur.
        out["_cagri_yeri"] = cagri_yeri_hukmu(fikstur_kaynaklari,
                                              mutant=mutant,
                                              taban=FIKSTUR_TABANI)
        # 🔴 K345 — BORU ONEKI ve UCUNCU KOVA vakalar (kanca yuzeyinin girdisi
        # KOMUT METNIDIR; etiket oradan CIKARILIR, argv'den DEGIL).
        out["_boru"] = parti_karari(
            kok_hasat, _etiket_cikar(K345_BORU_KOMUTU, mutant=mutant),
            koku_root=gecici_kok, mutant=mutant)
        out["_boru_etiketsiz"] = parti_karari(
            kok_hasat, _etiket_cikar(K345_BORU_ETIKETSIZ, mutant=mutant),
            koku_root=gecici_kok, mutant=mutant)
        # 🔴 KALEMSIZ evde de okunamayan etiket RED'dir. Bu vaka M13'un
        # (kova birlestirme) FAIL-OPEN sizintisini gorunur kilar: kovalar
        # birlesince kalemsiz ev "temiz" diye GECER verir.
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
    cy = normal["_cagri_yeri"]
    cy_ok = (cy["HUKUM"] == "GECER" and cy["SAYI"] >= cy["TABAN"])
    print("  %-18s (fikstur) HUKUM=%s SAYI=%d/TABAN=%d ihlal=%d "
          "(beklenen GECER) %s"
          % ("cagri-yeri", cy["HUKUM"], cy["SAYI"], cy["TABAN"],
             len(cy["IHLAL"]), "✓" if cy_ok else "✗"))
    # 🔴 K345 tabani — UC KOVA + turetilmis metin (hepsi ONCE olculur)
    k345_beklenen = (
        ("_boru", "GECER", N2B_MUAF_JETON, SEBEP_MUAF),
        ("_boru_etiketsiz", "RED", N2B_ETIKET_OKUNAMADI_JETON,
         SEBEP_ETIKET_OKUNAMADI),
        ("_etiketsiz_temiz_ev", "RED", N2B_ETIKET_OKUNAMADI_JETON,
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
    rm_ok = (rm["HUKUM"] == "GECER" and rm["ELLE_KOPYA"] == 0)
    print("  %-20s HUKUM=%s ELLE_KOPYA=%d ihlal=%d (beklenen GECER/0) %s"
          % ("red-metni-turetim", rm["HUKUM"], rm["ELLE_KOPYA"],
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
    taban_ok = (taban_ok and yeni_ok and suren_ok and cy_ok and k345_ok
                and rm_ok and okuma_ok and baslatma_ok)
    print("")
    if not taban_ok:
        print("TABAN KIRMIZI — mutant olcumu ANLAMSIZ.")
        for b in cy["BULGULAR"]:
            print("    | cagri-yeri %s etiket=%r beklenen=%s gercek=%s %s"
                  % (b["ROL"], b["ETIKET"], b["BEKLENEN"], b["GERCEK"],
                     b["HATA"] or ""))
        print("MUTANT=0/13 HEDEF_KOL_ATFI=0/13 KONTROL=0/12")
        return 1

    # --- MUTANTLAR ---------------------------------------------------------
    # Her mutant icin: (hedef vaka kumesi, yan eksen kumesi)
    HEDEF_VAKA = {
        "M1": ("_yeni",),                       # yeni-is tanima
        "M2": ("_suren",),                      # suren-is korumasi
        "M3": ("macit-yeni-parti",),            # RED kolu
        # M4 fail-closed kolu: bilinmeyen ev koku (sentetik) VE defteri BOS ev
        # — ikincisi K229'dan sonra AYNI kolun ikinci yuzeyidir; yan eksene
        # yazilirsa M4'un ATFI hatali biçimde KUSUR okunur.
        "M4": ("_olculemedi", "tekin-defter-bos"),
        # M5 muafiyeti KOKTEN oldurur; `_cagri_yeri` MUAF'in downstream'idir,
        # bu yuzden hedef kumeye DAHILDIR (yan eksen degil — sahte KUSUR olmasin).
        # `_boru` de MUAF'in downstream'idir (borulu cagrinin etiketi MUAF bir
        # onek tasir) — yan eksene yazilirsa M5'in ATFI sahte KUSUR okunur.
        "M5": ("macit-tamir", "macit-posta", "_cagri_yeri", "_boru"),
        # N4A: cagri yeri kolu — iki AYRI oldurme yolu
        "M6": ("_cagri_yeri",),                 # kapsam tabani (tarayici korlesir)
        "M7": ("_cagri_yeri",),                 # regresyon (startswith-only)
        # K229: ucuncu kova — iki AYRI oldurme yolu (eski adlari M6/M7 idi)
        "M8": ("hoca-defter-yok",),             # ucuncu kova — kol BOZULUR
        "M9": ("hoca-defter-yok",),             # ucuncu kova — kol BIRLESTIRILIR
        # 🔴 K345 — dort AYRI kol, dort AYRI hedef kume
        "M10": ("_red_metni",),                 # metin TURETIMI kirilir
        "M11": ("_boru",),                      # boru ONEKI normalizasyonu
        # M12/M13 ETIKET_OKUNAMADI kovasinin IKI ayri oldurme yolu; ikisi de
        # HEM borulu HEM kalemsiz-ev vakasini bozar (kova tek yerde yasamaz).
        "M12": ("_boru_etiketsiz", "_etiketsiz_temiz_ev"),
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
            hedef_kirmizi = (n4["HUKUM"] == "RED"
                             and n4["KOL"] == N2B_OLCULEMEDI_JETON
                             and m4["HUKUM"] == "GECER")
            print("  bilinmeyen ev: normal=%s | mutant=%s"
                  % (hukum_satiri(n4), hukum_satiri(m4)))
        else:
            for hv in HEDEF_VAKA[ad]:
                n, mm = normal[hv], m[hv]
                if hv == "_cagri_yeri":
                    # Normalde GECER; mutant altinda GECER OLMAMALIDIR.
                    if n["HUKUM"] == "GECER" and mm["HUKUM"] != "GECER":
                        hedef_kirmizi = True
                    print("  _cagri_yeri: normal=HUKUM=%s SAYI=%d ihlal=%d | "
                          "mutant=HUKUM=%s SAYI=%d ihlal=%d"
                          % (n["HUKUM"], n["SAYI"], len(n["IHLAL"]),
                             mm["HUKUM"], mm["SAYI"], len(mm["IHLAL"])))
                    for b in mm["IHLAL"]:
                        print("      | IHLAL %s etiket=%r beklenen=%s gercek=%s"
                              % (b["ROL"], b["ETIKET"], b["BEKLENEN"],
                                 b["GERCEK"]))
                    continue
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
                    # Turetim kolu: normalde GECER; mutant altinda GECER
                    # OLMAMALIDIR (elle ikinci kopya geri gelmis olur).
                    if n["HUKUM"] == "GECER" and mm["HUKUM"] != "GECER":
                        hedef_kirmizi = True
                    print("  _red_metni: normal=HUKUM=%s elle_kopya=%d | "
                          "mutant=HUKUM=%s elle_kopya=%d"
                          % (n["HUKUM"], n["ELLE_KOPYA"],
                             mm["HUKUM"], mm["ELLE_KOPYA"]))
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
                print("  -> M8 altinda defteri OLMAYAN ev yine %s/%s yerdi: "
                      "ev duzeyinde KILITLENME geri gelirdi"
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
        if ("_cagri_yeri" not in HEDEF_VAKA[ad]
                and normal["_cagri_yeri"]["HUKUM"] != m["_cagri_yeri"]["HUKUM"]):
            yan_bozulan.append("_cagri_yeri")
        # 🔴 K345 yan eksenleri — hedef DISINDAKI dort kol da bozulmamali
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

    # K1: RED ciktisi kalem KIMLIGINI ve `kabul:` komutunu BASAR (spec §2)
    red = normal["macit-yeni-parti"]
    metin = red_metni(red)
    k1 = ("K901" in metin and "K902" in metin and "kabul: " in metin
          and "parti-borc-kapisi.py --ev MaCiT" in metin)
    print("KONTROL K1 RED ciktisi kalem + `kabul:` basar: %s"
          % ("GECTI" if k1 else "KUSUR"))
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
    k3 = (sonra["HUKUM"] == "GECER" and sonra["KOL"] == N2B_SUREN_JETON)
    print("KONTROL K3 kalem kapaninca AYNI komut GECER: %s (%s)"
          % ("GECTI" if k3 else "KUSUR", hukum_satiri(sonra)))
    kontrol += 1 if k3 else 0
    # defteri geri koy (sonraki kontrolleri etkilemesin)
    _sentetik_defter(os.path.join(gecici_kok, "MaCiT", "memory",
                                  "acik-kalemler.md"),
                     [("K901", "🔧"), ("K902", "ACIK"), ("K903", "KAPANDI")])

    # K4: RED bir UYARI degil, gercek RED — isci_kapi rc=1 doner
    rc = isci_kapi("minimax-m3", kok_hasat, "/tmp/s.md", "parti-surucusu",
                   koku_root=gecici_kok)
    k4 = (rc == RC_RED)
    print("KONTROL K4 isci_kapi RED rc: %s (rc=%d, beklenen %d)"
          % ("GECTI" if k4 else "KUSUR", rc, RC_RED))
    kontrol += 1 if k4 else 0

    # K5: KANCA yuzeyi uctan uca + ETIKET cikarimi (yonlendirme kuyruklu komut)
    #     Kanca modu DAIMA rc=0 doner; hukum JSON'un icindedir.
    isci = "/Users/okan/.claude/cron/isci.sh"
    vaka_kanca = (
        # (ad, komut, beklenen_deny)
        ("yeni-parti",
         "%s minimax-m3 %s /tmp/s.md parti-surucusu >> /tmp/l.log 2>&1"
         % (isci, kok_hasat), True),
        ("tamir-muaf",
         "%s kimi %s /tmp/s.md tamir-k99 >> /tmp/l.log 2>&1"
         % (isci, kok_hasat), False),
        ("suren-is", "git -C %s commit -m 'parti 47/100'" % kok_hasat, False),
    )
    k5 = True
    for ad, komut, bekle_deny in vaka_kanca:
        girdi = {"tool_name": "Bash", "tool_input": {"command": komut},
                 "cwd": kok_hasat}
        tampon = io.StringIO()
        with redirect_stdout(tampon):
            rc_k = kanca(girdi, koku_root=gecici_kok)
        ham = tampon.getvalue().strip()
        deny = False
        if ham:
            try:
                deny = (json.loads(ham).get("hookSpecificOutput", {})
                        .get("permissionDecision") == "deny")
            except Exception:
                deny = False
        etiket = _etiket_cikar(komut)
        ok = (rc_k == 0 and deny == bekle_deny)
        k5 = k5 and ok
        print("  kanca[%-11s] rc=%d deny=%-5s (beklenen %-5s) etiket=%r %s"
              % (ad, rc_k, deny, bekle_deny, etiket, "✓" if ok else "✗"))
    print("KONTROL K5 kanca yuzeyi + etiket cikarimi: %s"
          % ("GECTI" if k5 else "KUSUR"))
    kontrol += 1 if k5 else 0

    # K6: 🔴 T4-YUKLENEMEZ MUTANTI — kapi KIRMIZI yanar VE sebebi (aranan YOL +
    #     istisna TURU) ciktida GORUNUR. 20 Agu vakasinda sessiz `return None`
    #     yuzunden bes evin isci hatti oldu ve NEDENI hicbir satirda yoktu.
    #     Uc ayak birlikte olculur (K182: "kirmizi geldi" tek basina kanit degil):
    #       (a) MUTANT   : T4 erisilemez -> RED + KOL=N2B-OLCULEMEDI + SEBEP basar
    #       (b) NEGATIF  : T4 yerinde iken AYNI cagri YESIL (kirmizinin sebebi
    #                      hedef koldur, ambiyans degil)
    #       (c) YAN EKSEN: mutant altinda MUAF kolu BOZULMAZ (kirmizi genel degil)
    yok_yol = os.path.join(gecici_kok, "T4-YOK", _T4_ADI)
    _yok_mod, _yok_yuklenen, t4_hata = _t4_yukle([yok_yol])
    m6 = parti_karari(kok_kral, "parti-surucusu", koku_root=gecici_kok,
                      t4=None, t4_hata=t4_hata)
    n6 = parti_karari(kok_kral, "parti-surucusu", koku_root=gecici_kok)
    y6 = parti_karari(kok_hasat, "tamir-k99", koku_root=gecici_kok,
                      t4=None, t4_hata=t4_hata)
    hata6 = m6["HATA"] or ""
    k6 = (_yok_mod is None
          and m6["HUKUM"] == "RED" and m6["KOL"] == N2B_OLCULEMEDI_JETON
          and yok_yol in hata6 and "FileNotFoundError" in hata6
          and n6["HUKUM"] == "GECER" and n6["KOL"] == N2B_SUREN_JETON
          and y6["HUKUM"] == "GECER" and y6["KOL"] == N2B_MUAF_JETON)
    print("KONTROL K6 T4 yuklenemezse KIRMIZI + SEBEP (yol+istisna) basar: %s"
          % ("GECTI" if k6 else "KUSUR"))
    print("    | mutant  : %s" % hukum_satiri(m6))
    print("    | SEBEP   : %s" % (hata6 or "(BOS — SESSIZ YUTMA)"))
    print("    | negatif : %s  (T4 yerinde, AYNI cagri)" % hukum_satiri(n6))
    print("    | yan eks.: %s  (MUAF kolu bozulmadi)" % hukum_satiri(y6))
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

    # K8: 🔴 N4A — MUAFIYET SOZLESMESI GERCEK CAGRI YERLERINE BAGLI
    #     20 Agu vakasi: batarya 5/5 + 7/7 YESIL iken onarim hattinin TEK
    #     gercek cagri yeri (`nobet-kapi.py:1262`, etiket `ci-nobeti`) kapidan
    #     RED aliyordu; sentetik etiketler (`tamir-k99`) uyduruimustu, gercek
    #     etiket bataryada HIC yoktu ([[kapinin-menzili-cagri-yeridir]]).
    #     Dort ayak birlikte olculur:
    #       (a) POZITIF : uc onarim/posta cagri yeri MUAF olmali
    #       (b) NEGATIF : `parti-surucusu` cagri yeri MUAF OLMAMALI (tautoloji
    #                     degil — tablo "her buldugunu muaf sayan" bir sey degil)
    #       (c) KAPSAM  : cozulen cagri yeri sayisi TABAN'a esit (sayiyla civili)
    #       (d) UCTAN UCA: gercek etiketle `parti_karari` cagrisi GECER/MUAF
    #                      doner — yani hukum yalniz yardimci fonksiyonda degil
    #                      KAPININ KENDISINDE de dogru
    cy_g = cagri_yeri_hukmu()          # GERCEK cron kaynaklari
    pozitif = [b for b in cy_g["BULGULAR"] if b["BEKLENEN"] is True]
    negatif = [b for b in cy_g["BULGULAR"] if b["BEKLENEN"] is False]
    cozulen_poz = [b for b in pozitif if b["ETIKET"] is not None]
    cozulen_neg = [b for b in negatif if b["ETIKET"] is not None]

    # 🔴 HER ORTAMDA KOSAN CEKIRDEK — bu ayak fiziksel dosyaya BAGLI DEGIL:
    #    gercek etiket dizesi ('ci-nobeti') GERCEK kapidan MUAF gecmeli.
    #    KAPSAM_DISI kolunun bir muafiyet deligine donusmesini bu engeller.
    uctan_uca = parti_karari(kok_kral, "ci-nobeti", koku_root=gecici_kok)
    cekirdek = (uctan_uca["HUKUM"] == "GECER"
                and uctan_uca["KOL"] == N2B_MUAF_JETON)

    if cy_g["HUKUM"] == "KAPSAM_DISI":
        # CI kosucusu: `~/.claude/cron` yok. Sozlesme burada FIZIKSEL OLARAK
        # olculemez; mekanizma zaten fiksturlerle M6/M7'ye tabi tutuldu.
        kaynak_ayagi = True
        kaynak_notu = ("KAPSAM_DISI — %d kaynagin hicbiri bu makinede yok "
                       "(CI kosucusu); mekanizma fiksturlerle olculdu"
                       % len(CAGRI_YERI_KAYNAKLARI))
    else:
        kaynak_ayagi = (cy_g["HUKUM"] == "GECER"
                        and cy_g["SAYI"] == CAGRI_YERI_TABANI
                        and not cy_g["IHLAL"]
                        and not cy_g["KAPSAM_KAYBI"]
                        and len(cozulen_poz) >= 3
                        and all(b["GERCEK"] is True for b in cozulen_poz)
                        and len(cozulen_neg) >= 1
                        and all(b["GERCEK"] is False for b in cozulen_neg)
                        and any(b["ETIKET"] == "ci-nobeti" for b in cozulen_poz))
        kaynak_notu = ("HUKUM=%s SAYI=%d/TABAN=%d ihlal=%d kapsam_kaybi=%d"
                       % (cy_g["HUKUM"], cy_g["SAYI"], CAGRI_YERI_TABANI,
                          len(cy_g["IHLAL"]), len(cy_g["KAPSAM_KAYBI"])))
    # 🔴 CI KOLU HERMETIK OLARAK OLCULUR — "CI'da yesil yanar" IDDIA DEGIL.
    #    (a) kaynaklar YOKSA -> KAPSAM_DISI (kusur degil)
    #    (b) kaynak VAR ama tarayici korse -> OLCULEMEDI (kusur) — ikisi
    #        birbirine KARISMAMALI, yoksa CI kolu bir muafiyet deligi olurdu.
    yok_kaynaklar = (
        (os.path.join(gecici_kok, "YOK", "nobet-kapi.py"), True, "yok-1"),
        (os.path.join(gecici_kok, "YOK", "parti-surucusu.sh"), False, "yok-2"),
    )
    ci_kolu = cagri_yeri_hukmu(yok_kaynaklar, taban=2)
    kor_kolu = cagri_yeri_hukmu(fikstur_kaynaklari, mutant="M6",
                                taban=FIKSTUR_TABANI)
    ci_ayagi = (ci_kolu["HUKUM"] == "KAPSAM_DISI"
                and kor_kolu["HUKUM"] == "OLCULEMEDI")

    k8 = kaynak_ayagi and cekirdek and ci_ayagi
    print("KONTROL K8 muafiyet GERCEK cagri yerlerine bagli: %s"
          % ("GECTI" if k8 else "KUSUR"))
    print("    | CI kolu      : kaynak YOK -> %s (beklenen KAPSAM_DISI) · "
          "kaynak VAR + tarayici KOR -> %s (beklenen OLCULEMEDI) %s"
          % (ci_kolu["HUKUM"], kor_kolu["HUKUM"], "✓" if ci_ayagi else "✗"))
    print("    | kaynak ayagi : %s" % kaynak_notu)
    for b in cy_g["BULGULAR"]:
        print("    | %-22s %-32s etiket=%-16r beklenen=%-5s gercek=%-5s %s"
              % (b["ROL"], os.path.basename(b["YOL"]), b["ETIKET"],
                 b["BEKLENEN"], b["GERCEK"], b["HATA"] or ""))
    print("    | CEKIRDEK (her ortamda): kapinin KENDISI, etiket='ci-nobeti' "
          "-> %s" % hukum_satiri(uctan_uca))
    kontrol += 1 if k8 else 0

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
            rc8 = isci_kapi("kimi", kok_bot, "/tmp/s.md", "parti-surucusu",
                            koku_root=gecici_kok)
    finally:
        sys.stderr = _eski_err
    cikti8 = tampon8.getvalue()
    gerekce8 = hata8.getvalue()
    k9 = (dy["HUKUM"] == "GECER"
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
    #     (a) defteri VAR + acik kalemli ev  -> HALA RED/N2B-RED    (davranis DEGISMEDI)
    #     (b) defteri VAR + kalemi kapali ev -> GECER/N2B-SUREN     (degismedi)
    #     (c) defteri VAR ama BOS ev         -> HALA RED/N2B-OLCULEMEDI
    #         (bos dosya "olculmus sifir" SAYILMAZ — K201)
    a9 = normal["macit-yeni-parti"]
    b9 = normal["kral-yeni-parti"]
    c9 = normal["tekin-defter-bos"]
    k10 = (a9["HUKUM"] == "RED" and a9["KOL"] == N2B_RED_JETON and a9["ACIK"] == 2
           and b9["HUKUM"] == "GECER" and b9["KOL"] == N2B_SUREN_JETON
           and c9["HUKUM"] == "RED" and c9["KOL"] == N2B_OLCULEMEDI_JETON)
    print("KONTROL K10 defteri OLAN evde davranis DEGISMEDI + bos defter HALA "
          "RED: %s" % ("GECTI" if k10 else "KUSUR"))
    print("    | acik kalemli : %s" % hukum_satiri(a9))
    print("    | kalemsiz     : %s" % hukum_satiri(b9))
    print("    | BOS defter   : %s  (SEBEP: %s)"
          % (hukum_satiri(c9), c9["HATA"] or "-"))
    kontrol += 1 if k10 else 0

    # K11: 🔴 K345 — RED METNI TURETILMIS MI? (iki yonlu esitlik + elle kopya)
    #      Kapinin dogru karar vermesi YETMEZ: okuyan METNE gore davranir.
    #      Bu kontrol metnin CALISAN CAGRI YOLUNU tasidigini olcer.
    t11 = red_metni_turetim_hukmu()
    ornek11 = {"HUKUM": "RED", "KOL": N2B_ETIKET_OKUNAMADI_JETON, "EV": "KraL",
               "ACIK": 0, "KALEMLER": [], "KABUL_KOMUTU": kabul_komutu("KraL"),
               "SEBEP_KODU": SEBEP_ETIKET_OKUNAMADI, "SEBEP": None,
               "HATA": None, "ETIKET": ""}
    metin11 = red_metni(ornek11)
    # metin, CALISAN cagri bicimini ve muaf onekleri GERCEKTEN tasiyor mu?
    tasiyor = (all(b in metin11 for b in dogru_cagri_bicimi())
               and muaf_onek_dizgesi() in metin11)
    kaynak11 = elle_kopya_kaynak_sayimi()
    # 🔴 KORLUK AYRIMI: `URETIM=0` "kaynak temiz" DE olabilir "prob kor" DA.
    # Fikstur, probun GORMESI GEREKENI gorup GORMEMESI GEREKENI birakmasini
    # ayni kosumda kanitlar; tutmazsa K11 KIRMIZI ([[batarya-kapsam-tabani-
    # sayiyla-civilenir]]).
    korluk = elle_kopya_kaynak_sayimi(kaynak=_korluk_fiksturu())
    korluk_ok = all(korluk[k] == v for k, v in _KORLUK_BEKLENEN.items())
    k11 = (t11["HUKUM"] == "GECER" and t11["ELLE_KOPYA"] == 0 and tasiyor
           and kaynak11["URETIM"] == 0      # -1 (olculemedi) de KUSUR'dur
           and korluk_ok)
    print("KONTROL K11 red metni TURETILMIS (iki yonlu) + elle kopya=0: %s"
          % ("GECTI" if k11 else "KUSUR"))
    print("    | hukum=%s metin_elle_kopya=%d ihlal=%d cagri_bicimi_metinde=%s"
          % (t11["HUKUM"], t11["ELLE_KOPYA"], len(t11["IHLAL"]), tasiyor))
    print("    | KAYNAK elle kopya: URETIM=%d (beklenen 0) · docstring=%d · "
          "mutant_yuku=%d · hata=%s"
          % (kaynak11["URETIM"], kaynak11["DOCSTRING"],
             kaynak11["MUTANT_YUKU"], kaynak11["HATA"] or "-"))
    for s in kaynak11["SATIRLAR"]:
        print("    |   🔴 %s" % s)
    print("    | PROB KOR DEGIL (fikstur): URETIM=%d/%d DOCSTRING=%d/%d "
          "MUTANT_YUKU=%d/%d %s"
          % (korluk["URETIM"], _KORLUK_BEKLENEN["URETIM"],
             korluk["DOCSTRING"], _KORLUK_BEKLENEN["DOCSTRING"],
             korluk["MUTANT_YUKU"], _KORLUK_BEKLENEN["MUTANT_YUKU"],
             "✓" if korluk_ok else "✗"))
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
    k12 = (kova_a["HUKUM"] == "GECER" and kova_a["KOL"] == N2B_MUAF_JETON
           and kova_a["SEBEP_KODU"] == SEBEP_MUAF
           and kova_b["HUKUM"] == "RED" and kova_b["KOL"] == N2B_RED_JETON
           and kova_b["SEBEP_KODU"] == SEBEP_ACIK_KALEM and kova_b["ACIK"] == 30
           and kova_c["HUKUM"] == "RED"
           and kova_c["KOL"] == N2B_ETIKET_OKUNAMADI_JETON
           and kova_c["SEBEP_KODU"] == SEBEP_ETIKET_OKUNAMADI
           and len(hukumler) == 3)          # UC AYRI hukum satiri
    print("KONTROL K12 uc kova / uc AYRI hukum (30 acik kalemli fikstur): %s"
          % ("GECTI" if k12 else "KUSUR"))
    print("    | (a) muaf etiket + boru ONEKI : %s" % hukum_satiri(kova_a))
    print("    | (b) muaf-DISI etiket + kalem : %s" % hukum_satiri(kova_b))
    print("    | (c) etiket OKUNAMADI (boru)  : %s" % hukum_satiri(kova_c))
    print("    | ayri hukum satiri sayisi=%d (beklenen 3)" % len(hukumler))
    # 🔴 Sebep AYRIMI metne de yansiyor mu? (b) ve (c) AYNI metni BASMAMALI
    print("    | (c) red metni sebep satirlari:")
    for satir in red_metni(kova_c).splitlines():
        if "SEBEP[" in satir:
            print("    |   %s" % satir)
    kontrol += 1 if k12 else 0
    # fikstur higyeni: defteri onceki haline dondur
    _sentetik_defter(os.path.join(gecici_kok, "MaCiT", "memory",
                                  "acik-kalemler.md"),
                     [("K901", "🔧"), ("K902", "ACIK"), ("K903", "KAPANDI")])

    # K13: 🔴 K345-C — OKUMA GECER **ve** BASLATMA HALA RED, ikisi de KANCA
    #      yuzeyinde UCTAN UCA (karar fonksiyonu degil, GERCEK hook girdisi).
    #      Ev MaCiT: 2 acik kalem VAR — yani okuma kolu "ev temiz oldugu icin"
    #      degil, GERCEKTEN okuma oldugu icin geciyor.
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
    baslatma_gecenler = [k for k in K345_BASLATMA_KOMUTLARI
                         if not _kanca_deny(k)[0]]
    k13 = (not okuma_denyleri
           and okuma_jetonu == len(K345_OKUMA_KOMUTLARI)
           and not baslatma_gecenler)
    print("KONTROL K13 OKUMA gecer + BASLATMA hala RED (kanca yuzeyi, "
          "acik kalemli ev): %s" % ("GECTI" if k13 else "KUSUR"))
    print("    | okuma  : %d vaka · deny=%d (beklenen 0) · %s jetonu=%d/%d"
          % (len(K345_OKUMA_KOMUTLARI), len(okuma_denyleri), N2B_OKUMA_JETON,
             okuma_jetonu, len(K345_OKUMA_KOMUTLARI)))
    for k in okuma_denyleri:
        print("    |   🔴 REDDEDILDI (olmamaliydi): %s" % k[:88])
    print("    | baslatma: %d vaka · GECEN=%d (beklenen 0)"
          % (len(K345_BASLATMA_KOMUTLARI), len(baslatma_gecenler)))
    for k in baslatma_gecenler:
        print("    |   🔴 SIZDI (kapiya tabi olmaliydi): %s" % k[:88])
    kontrol += 1 if k13 else 0

    print("")
    print("MUTANT=%d/15 HEDEF_KOL_ATFI=%d/15 KONTROL=%d/13"
          % (mutant_sayaci, atif_sayaci, kontrol))
    return 0 if (mutant_sayaci == 15 and atif_sayaci == 15
                 and kontrol == 13) else 1


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
    ap.add_argument("--elle-kopya", nargs="?", const="", metavar="YOL",
                    help="K345: kaynakta kalan ELLE muaf-onek listesi sayisi. "
                         "YOL bos ise bu dosya; `git:<ref>` bicimi o ref'teki "
                         "surumu olcer (ONCE/SONRA ayni tanimla).")
    ap.add_argument("--cagri-yeri", action="store_true",
                    help="N4A: muafiyet sozlesmesini GERCEK cagri yerlerine "
                         "karsi olcer (0 GECER · 1 RED · 2 OLCULEMEDI)")
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

    if args.cagri_yeri:
        sonuc = cagri_yeri_hukmu()
        print("N2B-CAGRI-YERI HUKUM=%s SAYI=%d TABAN=%d MEVCUT=%d IHLAL=%d "
              "KAPSAM_KAYBI=%d"
              % (sonuc["HUKUM"], sonuc["SAYI"], sonuc["TABAN"],
                 sonuc["MEVCUT"], len(sonuc["IHLAL"]),
                 len(sonuc["KAPSAM_KAYBI"])))
        for b in sonuc["BULGULAR"]:
            print("  %-12s %-32s etiket=%-16r beklenen=%-5s gercek=%-5s %s"
                  % (b["ROL"], os.path.basename(b["YOL"]), b["ETIKET"],
                     b["BEKLENEN"], b["GERCEK"], b["HATA"] or ""))
        if sonuc["HUKUM"] == "GECER":
            return RC_GECER
        return RC_RED if sonuc["HUKUM"] == "RED" else RC_OLCULEMEDI

    if args.elle_kopya is not None:
        s = elle_kopya_kaynak_sayimi(args.elle_kopya or None)
        print("N2B-ELLE-KOPYA URETIM=%d DOCSTRING=%d MUTANT_YUKU=%d HATA=%s"
              % (s["URETIM"], s["DOCSTRING"], s["MUTANT_YUKU"],
                 s["HATA"] or "-"))
        for satir in s["SATIRLAR"]:
            print("  %s" % satir)
        return RC_GECER if s["URETIM"] == 0 else RC_RED

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
        if sonuc["HUKUM"] == "RED" and sonuc["KOL"] == N2B_RED_JETON:
            print(red_metni(sonuc))
        elif sonuc["KOL"] == N2B_DEFTER_YOK_JETON:
            print("UCUNCU KOVA: %s" % (sonuc["SEBEP"] or ""))
        elif sonuc["HATA"]:
            print("HATA: %s" % sonuc["HATA"])
        print(hukum_satiri(sonuc))
        return RC_GECER if sonuc["HUKUM"] == "GECER" else RC_RED

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
