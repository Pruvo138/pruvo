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
}

# 🔴 MUAF ETIKETLER — onarim hattinin KENDINI bloklamasini engeller.
# Acik kalem varken tamiri baslatamamak KILITLENMEDIR: kalem asla kapanmaz.
# Muafiyet DAR ve GORUNURDUR: hukum satirina `KOL=N2B-MUAF` yazilir.
# `posta` = posta kutusu izleyicisi — evin kalemi OGRENDIGI yol; bloklanirsa
# ev haberi hic almaz (Okan'in vakasinin ta kendisi).
MUAF_ETIKET_ONEKLERI = ("tamir", "onarim", "kabul", "nobet", "posta", "devir")

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


def yeni_is_mi(komut, *, mutant=None):
    """Bir Bash komutu YENI is baslatiyor mu? (N2B-YENI / N2B-SUREN ayrimi)

    🔴 Fail-OPEN yon BILEREK: taninmayan komut `SUREN` sayilir ve GECER.
    Bu kapi yeni is baslatmayi durdurur; suren/yarim isi DURDURMAZ. Yanlis
    pozitif burada YARIM IS KESER — kabul edilemez zarar (Okan'in vakasi).
    """
    if mutant == "M1":
        return False          # yeni-is tanima oldurulur -> parti hep gecer
    if mutant == "M2":
        return True           # her komut yeni-is sayilir -> YARIM IS KESILIR
    if not isinstance(komut, str) or not komut.strip():
        return False
    return any(d.search(komut) for d in YENI_IS_DESENLERI)


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
             "SEBEP": None, "HATA": None}

    if muaf_etiket_mi(etiket, mutant=mutant):
        sonuc["HUKUM"] = "GECER"
        sonuc["KOL"] = N2B_MUAF_JETON
        sonuc["SEBEP"] = ("%s onarim/nobet/posta hatti — kilitlenmemek icin "
                          "muaf (etiket=%s)" % (N2B_MUAF_JETON, etiket))
        if ev is None and t4 is not None:
            ev, _h = ev_coz(ev_koku, t4=t4)
        sonuc["EV"] = ev
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
        sonuc["KABUL_KOMUTU"] = kabul_komutu(ev)
        sonuc["SEBEP"] = borc["RED_SEBEBI"]
        return sonuc

    sonuc["HUKUM"] = "GECER"
    sonuc["KOL"] = N2B_SUREN_JETON
    sonuc["SEBEP"] = borc["GECER_MESAJI"]
    return sonuc


def kabul_komutu(ev):
    """Kalemi kapatinca YESILE donmeyi kanitlayan calistirilabilir komut.

    🔴 YUKLENEN T4'un yolunu basar: enjekte kopyada (`<ev>/.claude/`) kardes
    dosya YOKTUR, oradaki `_BU_DIZIN` yolu CALISMAYAN bir komut uretirdi.
    """
    return ("python3 %s --ev %s" % (T4_YOLU or _T4_KANONIK, ev))


def red_metni(sonuc):
    """RED gerekcesinin insan-okur govdesi: kalem KIMLIGI + `kabul:` komutu."""
    satirlar = []
    satirlar.append(
        "N2B PARTI KAPISI — YENI IS REDDEDILDI (ev=%s, acik kalem=%d)."
        % (sonuc["EV"], sonuc["ACIK"]))
    satirlar.append(
        "Bu evde acik 🔧 kalem varken YENI parti/isci BASLATILAMAZ. "
        "🔴 SUREN IS KESILMEZ — yarim partine devam et, KAPAT, sonra yenisini ac.")
    if sonuc["KALEMLER"]:
        satirlar.append("ACIK KALEMLER:")
        for k in sonuc["KALEMLER"]:
            satirlar.append("  - %s [%s] %s" % (k["kimlik"], k["durum"], k["is"]))
    else:
        satirlar.append("ACIK KALEMLER: (kimlik cozulemedi — defteri elle ac)")
    satirlar.append("kabul: %s" % (sonuc["KABUL_KOMUTU"] or "-"))
    satirlar.append("(kalem KAPANDI olunca ayni komut GECER doner; kapi "
                    "kalici kilit DEGILDIR.)")
    return "\n".join(satirlar)


def hukum_satiri(sonuc):
    """Makine-okur tek satir. Kabul testleri BU satiri arar."""
    kalem = ",".join(k["kimlik"] for k in sonuc["KALEMLER"]) or "-"
    return "N2B HUKUM=%s KOL=%s EV=%s ACIK=%d KALEM=%s" % (
        sonuc["HUKUM"], sonuc["KOL"], sonuc["EV"] or "-", sonuc["ACIK"], kalem)


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

    if not yeni_is_mi(komut, mutant=mutant):
        # 🔴 N2B-SUREN: yeni is DEGIL. Suren/yarim is ASLA kesilmez.
        return 0

    ev_koku = girdi.get("cwd") or ""
    etiket = _etiket_cikar(komut)
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
# isci.sh      : <MOTOR> <EV_KOKU> <SPEC> <ETIKET>   -> 3
# m3-isci.sh   : <EV_KOKU> <SPEC> <ETIKET>           -> 2
# parti-surucusu.sh: argumansiz — etiket govdesinde gomulu, ciakarilamaz -> None
_ETIKET_INDEKS = {"isci.sh": 3, "m3-isci.sh": 2}


def _etiket_cikar(komut):
    """`isci.sh <motor> <ev> <spec> <etiket>` icindeki ETIKET'i cikarir.

    🔴 Bulamazsa BOS doner ve bos etiket MUAF DEGILDIR (fail-closed yon):
    etiketi okuyamadigimiz bir cagriyi "onarim hatti" sayip gecirmeyiz.
    Yonlendirme/boru kuyrugu (`>> log 2>&1`, `| tee`) once ATILIR — aksi
    halde etiket son token olmaz ve MUAF cagrilar bosuna bloklanirdi.
    """
    ham = (komut or "").strip()
    # yonlendirme/boru kuyrugunu at (etiket bunlardan ONCE gelir)
    for ayrac in (">>", "2>", ">", "|", "&&", ";"):
        i = ham.find(ayrac)
        if i >= 0:
            ham = ham[:i]
    m = _ETIKET_RE.search(ham.strip())
    if not m:
        return ""
    sarmalayici = os.path.basename(m.group(1))
    indeks = _ETIKET_INDEKS.get(sarmalayici)
    if indeks is None:
        return ""
    argumanlar = (m.group(2) or "").split()
    if len(argumanlar) <= indeks:
        return ""
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
    taban_ok = taban_ok and yeni_ok and suren_ok and cy_ok
    print("")
    if not taban_ok:
        print("TABAN KIRMIZI — mutant olcumu ANLAMSIZ.")
        for b in cy["BULGULAR"]:
            print("    | cagri-yeri %s etiket=%r beklenen=%s gercek=%s %s"
                  % (b["ROL"], b["ETIKET"], b["BEKLENEN"], b["GERCEK"],
                     b["HATA"] or ""))
        print("MUTANT=0/9 HEDEF_KOL_ATFI=0/9 KONTROL=0/10")
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
        "M5": ("macit-tamir", "macit-posta", "_cagri_yeri"),
        # N4A: cagri yeri kolu — iki AYRI oldurme yolu
        "M6": ("_cagri_yeri",),                 # kapsam tabani (tarayici korlesir)
        "M7": ("_cagri_yeri",),                 # regresyon (startswith-only)
        # K229: ucuncu kova — iki AYRI oldurme yolu (eski adlari M6/M7 idi)
        "M8": ("hoca-defter-yok",),             # ucuncu kova — kol BOZULUR
        "M9": ("hoca-defter-yok",),             # ucuncu kova — kol BIRLESTIRILIR
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
                if (n["HUKUM"], n["KOL"]) != (mm["HUKUM"], mm["KOL"]):
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

    print("")
    print("MUTANT=%d/9 HEDEF_KOL_ATFI=%d/9 KONTROL=%d/10"
          % (mutant_sayaci, atif_sayaci, kontrol))
    return 0 if (mutant_sayaci == 9 and atif_sayaci == 9 and kontrol == 10) else 1


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
