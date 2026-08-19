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

BES KOL (her birinin MUTANTI ve HEDEF KOL ATFI vardir — K182)
--------------------------------------------------------------
  N2B-YENI        cagri YENI is baslatiyor          -> T4 borc sorgusuna girer
  N2B-SUREN       cagri yeni is DEGIL (suren/yarim) -> GECER, ASLA kesilmez
  N2B-RED         sahibinin evinde acik kalem var   -> **RED** + kalem + `kabul:`
  N2B-MUAF        etiket tamir/onarim/kabul/nobet/  -> GECER (yoksa onarim
                  posta/devir ile basliyor              KENDINI bloklar: kilit)
  N2B-OLCULEMEDI  ev/defter cozulemedi              -> **RED** (fail-closed),
                                                       yalniz YENI is yolunda

Borc olcumu TEK KAYNAK `tools/parti-borc-kapisi.py` (T4): bu dosya kendi defter
parser'ini YAZMAZ, `acik_kalem_listesi` + `parti_engeli_var_mi` cagirir.
Ev->depo eslemesi de T4'un `EV_DIZIN`inden TURETILIR (ucuncu ev tablosu YOK).
T4 evlere dagitilan kopyanin YANINDA BULUNMAZ: kardes yoksa KANONIK repo
yoluna dusulur, yuklenemezse SEBEP (aranan yol + istisna turu) BASILIR — bkz.
asagidaki "T4 YUKLEME" blogu (20 Agu 2026 canli bloker onarimi).

KABUL (calistirilabilir)
------------------------
  python3 tools/parti-kapisi.py --kendini-test
    son satir + rc=0:  MUTANT=5/5 HEDEF_KOL_ATFI=5/5 KONTROL=7/7

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

MUTANT_HEDEF = {
    "M1": N2B_YENI_JETON,
    "M2": N2B_SUREN_JETON,
    "M3": N2B_RED_JETON,
    "M4": N2B_OLCULEMEDI_JETON,
    "M5": N2B_MUAF_JETON,
}

# 🔴 MUAF ETIKETLER — onarim hattinin KENDINI bloklamasini engeller.
# Acik kalem varken tamiri baslatamamak KILITLENMEDIR: kalem asla kapanmaz.
# Muafiyet DAR ve GORUNURDUR: hukum satirina `KOL=N2B-MUAF` yazilir.
# `posta` = posta kutusu izleyicisi — evin kalemi OGRENDIGI yol; bloklanirsa
# ev haberi hic almaz (Okan'in vakasinin ta kendisi).
MUAF_ETIKET_ONEKLERI = ("tamir", "onarim", "kabul", "nobet", "posta", "devir")

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
def muaf_etiket_mi(etiket, *, mutant=None):
    """Etiket onarim/nobet/posta hattina mi ait? (N2B-MUAF kolu)"""
    if mutant == "M5":
        return False          # muafiyet oldurulur -> onarim kendini bloklar
    e = (etiket or "").strip().lower()
    return any(e.startswith(on) for on in MUAF_ETIKET_ONEKLERI)


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
def _vakalar(kok_hasat, kok_kral):
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
    )


# Yeni-is OLMAYAN komutlar: acik kalemli evde bile KESILMEMELIDIR.
SUREN_KOMUTLARI = (
    "git commit -m 'parti 47/100'",
    "python3 /Users/okan/dev/pruvo-hasat/tools/duzelt.py",
    "git -C /Users/okan/dev/pruvo-hasat push",
    "ls tools/",
    "python3 tools/d1-sync.py --durum",
)


def kendini_test(gecici_kok):
    """5 mutant + hedef kol atfi + 7 kontrol (izole sentetik defterlerle)."""
    kok_hasat = "/Users/okan/dev/pruvo-hasat"
    kok_kral = "/Users/okan/dev/pruvo"

    # Izole defterler: MaCiT'te 2 acik kalem, KraL'de hepsi KAPANDI.
    _sentetik_defter(os.path.join(gecici_kok, "MaCiT", "memory",
                                  "acik-kalemler.md"),
                     [("K901", "🔧"), ("K902", "ACIK"), ("K903", "KAPANDI")])
    _sentetik_defter(os.path.join(gecici_kok, "KraL", "memory",
                                  "acik-kalemler.md"),
                     [("K800", "KAPANDI"), ("K801", "KAPANDI")])

    print("N2B PARTI KAPISI — KENDINI-TEST")
    print("izolasyon koku (defterler): %s" % gecici_kok)
    print("T4 yuklendi: %s" % ("EVET yol=%s" % T4_YOLU if T4 is not None
                               else "HAYIR sebep=%s" % T4_HATA))
    print("")

    vakalar = _vakalar(kok_hasat, kok_kral)

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
    taban_ok = taban_ok and yeni_ok and suren_ok
    print("")
    if not taban_ok:
        print("TABAN KIRMIZI — mutant olcumu ANLAMSIZ.")
        print("MUTANT=0/5 HEDEF_KOL_ATFI=0/5 KONTROL=0/7")
        return 1

    # --- MUTANTLAR ---------------------------------------------------------
    # Her mutant icin: (hedef vaka kumesi, yan eksen kumesi)
    HEDEF_VAKA = {
        "M1": ("_yeni",),                       # yeni-is tanima
        "M2": ("_suren",),                      # suren-is korumasi
        "M3": ("macit-yeni-parti",),            # RED kolu
        "M4": ("_olculemedi",),                 # fail-closed kolu
        "M5": ("macit-tamir", "macit-posta"),   # muafiyet kolu
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
                if (n["HUKUM"], n["KOL"]) != (mm["HUKUM"], mm["KOL"]):
                    hedef_kirmizi = True
                print("  %s: normal=%s | mutant=%s"
                      % (hv, hukum_satiri(n), hukum_satiri(mm)))

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
    k7 = ((not kardes_var)                       # kardes T4 GERCEKTEN yok
          and p_iyi.returncode == RC_GECER       # NEGATIF VAKA: kanonige duser
          and "DURUM=YUKLENDI" in c_iyi
          and p_mut.returncode == RC_OLCULEMEDI  # MUTANT: erisilemez -> KIRMIZI
          and "DURUM=YUKLENEMEDI" in c_mut
          and yok_yol in c_mut and "FileNotFoundError" in c_mut)
    print("KONTROL K7 enjekte kopya (kardes T4 YOK) uctan uca: %s"
          % ("GECTI" if k7 else "KUSUR"))
    print("    | kopya   : %s (kardes %s var mi: %s)"
          % (kopya, _T4_ADI, kardes_var))
    for satir in c_iyi.strip().splitlines():
        print("    | negatif | %s" % satir)
    print("    | negatif rc=%d (beklenen %d)" % (p_iyi.returncode, RC_GECER))
    for satir in c_mut.strip().splitlines():
        print("    | mutant  | %s" % satir)
    print("    | mutant  rc=%d (beklenen %d)"
          % (p_mut.returncode, RC_OLCULEMEDI))
    kontrol += 1 if k7 else 0

    print("")
    print("MUTANT=%d/5 HEDEF_KOL_ATFI=%d/5 KONTROL=%d/7"
          % (mutant_sayaci, atif_sayaci, kontrol))
    return 0 if (mutant_sayaci == 5 and atif_sayaci == 5 and kontrol == 7) else 1


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
        if sonuc["HUKUM"] == "RED" and sonuc["KOL"] == N2B_RED_JETON:
            print(red_metni(sonuc))
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
