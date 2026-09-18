#!/usr/bin/env python3
"""PRUVO NOBET GOZCUSU — olay-tetikli nobet (BaBa (2) maddesi).

Pahali olan cron degil, DURUMDAN BAGIMSIZ donen LLM turudur. Bu dosya turu ACMAZ;
turun acilip acilmayacagina DETERMINISTIK karar verir (sifir jeton). Icra AYNEN
`nobet-kapi.py`'de kalir (H1-H7 orada); burada IKINCI bir kat tablosu ya da IKINCI
bir defter ayristiricisi YOKTUR — hepsi importlib ile nobet-kapi'den gelir.

Kabul: python3 /Users/okan/.claude/cron/gozcu-test.py
Curutucu: python3 /Users/okan/.claude/cron/gozcu-mutasyon.py
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
import time

# 🔴 W2 (16 Eyl 2026) — bkz. nobet-kapi.py ayni sabit: env SET EDILMEZSE
# davranis BIREBIR eskisi; yalniz izole sandbox/CI kosumu mumkun olur.
CRON_KOKU = os.environ.get("PRUVO_CRON_KOKU") or "/Users/okan/.claude/cron"
NOBET_KAPI_YOLU = os.path.join(CRON_KOKU, "nobet-kapi.py")

DURUM_YOLU = os.path.join(CRON_KOKU, "gozcu-durum.json")
KALP_YOLU = os.path.join(CRON_KOKU, "gozcu-kalp.json")
LOG_YOLU = os.path.join(CRON_KOKU, "gozcu.log")
KILIT_DIZINI = os.path.join(CRON_KOKU, "gozcu-kilit")
ESKALASYON_YOLU = os.path.join(CRON_KOKU, "gozcu-eskalasyon.md")

LOG_TAVANI = 2000
# 45 dk (N1, 19 Agu 2026): gozcu artik 15 dk'da bir kosar; 3 kacirilan tur
# BAYATLIKTIR. Bu sayi TEK KAYNAKTIR — nobet-tetik.py buradan ITHAL eder.
KALP_BAYATLIK_SN = 2700
ARTIK_YAS_ESIGI_SN = 7200
GH_ZAMAN_ASIMI_SN = 90
BILINEN_BIN_DIZINLERI = ("/opt/homebrew/bin", "/usr/local/bin", "/Users/okan/.local/bin")
# ONEK KUMESI TAM LISTEDIR — genisletmek YASAK (spec 3.9).
ARTIK_ONEKLERI = (".isci-cikti.", ".bekci-cikti.")

# 3. onarim da duserse disari eskalasyon (BaBa (2)-2).
ESKALASYON_ESIGI = 3
# OLCULEMEDI YESIL DEGILDIR: gh duserse ya da defter okunamazsa KIRMIZI biteriz.
OLCULEMEDI_RC = 2
# Ele alinmis kabul edilen kayit durumlari (yeniden isci acilmaz).
KAPALI_DURUMLAR = ("ESKALASYON", "KAPANDI", "TABAN")


def _nobet_kapi_yukle(yol=NOBET_KAPI_YOLU):
    """nobet-kapi.py tek kaynaktir; tire iceren ad yuzunden importlib ile yuklenir."""
    spec = importlib.util.spec_from_file_location("nobet_kapi", yol)
    modul = importlib.util.module_from_spec(spec)
    # Disk kurali: yukleme __pycache__ birakmasin (arkamizda iz kalmaz).
    onceki = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(modul)
    finally:
        sys.dont_write_bytecode = onceki
    return modul


NK = _nobet_kapi_yukle()

# 🔴 UCUNCU HAL JETONU TEK KAYNAKTAN. Yuklenemezse `None` kalir ve asagidaki
# sessizlestirme kolu HIC ATESLEMEZ — fail-closed: jetonu OKUYAMADIGIMIZ bir
# turda hicbir sey susturulmaz.
LLM_KOLU_KAPALI = getattr(NK, "HUKUM_LLM_KOLU_KAPALI", None)


# --- CIP-DOGUM BEKCISI (26 Agu 2026) ---------------------------------------
# Okan istegi / BaBa yonu: "kral-sabah.py bir sabah atesLEMEZSE cip DOGMAZ ve
# hicbir kol bunu goremez." Bu bir SEVIYE sorusudur — kenar-tetikli kollar
# (yeni kirmizi/yeni satir) bir YOKLUGU olay olarak URETMEZ
# ([[kenar-tetikli-kol-seviye-sorusunu-cevaplayamaz]]).
# YENI CRON SATIRI ACILMADI: bekci bu hatta ILISTIRILDI (96 tur/gun).
# TEK KAYNAK modul: cip_dogum_bekcisi.py (karar + bildirim + tekillik damgasi);
# ikinci bir esik/kanit tanimi BURADA URETILMEZ.
# FAIL-CLOSED: modul yuklenemez ya da kol duserse hukum OLCULEMEDI'dir ve rc
# YUKSELIR — "bekciyi kosturamadim" SESSIZCE "cip dogdu" DEMEK DEGILDIR.
try:
    import cip_dogum_bekcisi as CDB
    CDB_HATASI = ""
except BaseException as _cdb_hata:            # sebebi TASI, yutma
    CDB = None
    CDB_HATASI = "%s: %s" % (type(_cdb_hata).__name__, _cdb_hata)


def _bekci_kolu(simdi, kuru):
    """KOL_ADI=BEKCI_KOL — gozcu turunun bekci bacagi.

    Mutant atfi BU JETONDAN okunur: kabul bataryasi bir mutanti oldururken
    kirmizinin SEBEBININ bu kol oldugunu `KOL_ADI=BEKCI_KOL` ile dogrular
    ([[ad-iki-rolde-mutanti-golgeler]] sinifina karsi).
    """
    if CDB is None:
        return {"hukum": "OLCULEMEDI", "sebep": "MODUL_YOK", "kirmizi": True,
                "kol": "BEKCI_KOL", "ayrinti": CDB_HATASI[:120], "bildirim": {}}
    try:
        k = CDB.kol(simdi=simdi, kuru=kuru)
    except BaseException as hata:
        return {"hukum": "OLCULEMEDI", "sebep": "KOL_DUSTU_%s" % type(hata).__name__,
                "kirmizi": True, "kol": "BEKCI_KOL",
                "ayrinti": str(hata)[:120], "bildirim": {}}
    k = dict(k)
    k["kol"] = "BEKCI_KOL"
    k["kirmizi"] = bool(CDB.kirmizi_mi(k))
    return k


# --- N2 (K263): 4 saatlik otomatik devir — CANLI KABLOLAMA -----------------
# nobet_devir.py karar fonksiyonunu her turda acar. Devir mekanizmasi
# gozcuden SORUMLU (gozcu her turda acik kalemleri gecirecek); karar
# DEVREDILDI ise kalem KraL'a devredilir, kutuya jeton dusmez (sadece
# iz dosyasina yazilir — gercek kutu mimar-posta-kutusu.md), kaciran
# evin hanesine IHLAL sayaci islenir.
NOBET_DEVIR_YOLU = os.path.join(CRON_KOKU, "nobet_devir.py")
DEVIR_IZ_YOLU = os.path.join(CRON_KOKU, "nobet-devir-iz.json")


def _nobet_devir_yukle():
    """nobet_devir.py modulu (karar fonksiyonu + esik sabiti)."""
    if not os.path.isfile(NOBET_DEVIR_YOLU):
        return None
    spec = importlib.util.spec_from_file_location("gozcu_nobet_devir",
                                                  NOBET_DEVIR_YOLU)
    if spec is None or spec.loader is None:
        return None
    modul = importlib.util.module_from_spec(spec)
    onceki = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(modul)
    except Exception:
        return None
    finally:
        sys.dont_write_bytecode = onceki
    if not hasattr(modul, "devir_karari"):
        return None
    return modul


def _devir_iz_oku():
    """Kalici iz dosyasi: hangi kalem hangi tarihte devredildi + ihlal sayaci."""
    if not os.path.exists(DEVIR_IZ_YOLU):
        return {"kalemler": {}, "ihlal": {}, "son_damga": ""}
    try:
        with open(DEVIR_IZ_YOLU, encoding="utf-8") as dosya:
            veri = json.load(dosya)
    except (OSError, ValueError):
        return {"kalemler": {}, "ihlal": {}, "son_damga": ""}
    if not isinstance(veri, dict):
        return {"kalemler": {}, "ihlal": {}, "son_damga": ""}
    veri.setdefault("kalemler", {})
    veri.setdefault("ihlal", {})
    veri.setdefault("son_damga", "")
    return veri


def _devir_iz_yaz(veri):
    """Atomik: mkstemp + fsync + os.replace."""
    dizin = os.path.dirname(DEVIR_IZ_YOLU) or "."
    os.makedirs(dizin, exist_ok=True)
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=".devir-iz-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as dosya:
            json.dump(veri, dosya, ensure_ascii=False, indent=2, sort_keys=True)
            dosya.write("\n")
            dosya.flush()
            os.fsync(dosya.fileno())
        os.replace(gecici, DEVIR_IZ_YOLU)
    except BaseException:
        try:
            os.unlink(gecici)
        except OSError:
            pass
        raise


def n2_devir_kararlari(kalemler, simdi, modul=None):
    """Her acik kalem icin devir_karari() kosar; sonucu iz dosyasina yazar.

    IKI YONLU: 4 saatte devir OLUR (yas >= 14400) ve 4 saatten ONCE
    OLMAZ (yas < 14400). KAPALI/ZATEN_DEVREDILMIS kalemler yasa
    bakilmaksizin devredilmez. Yarim is KESILMEZ: kalem listesi
    DEGISTIRILMEZ — devir yalnizca iz/sayac dosyalarina yansir, ana
    is akisi (dagitim, eskalasyon) AYNI kalem uzerinden devam eder.
    """
    sayac = {"DEVREDILDI": 0, "SLA_ICINDE": 0, "KAPALI": 0,
             "ZATEN": 0, "ihlal_eklenen": 0, "hata": False}
    if not kalemler:
        return sayac
    if modul is None:
        modul = _nobet_devir_yukle()
    if modul is None:
        sayac["hata"] = True
        return sayac
    iz = _devir_iz_oku()
    damga = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(simdi))
    for kalem in kalemler:
        kimlik = str(kalem.get("id") or kalem.get("kimlik") or "")
        if not kimlik:
            continue
        onceki = iz["kalemler"].get(kimlik)
        if onceki and onceki.get("devredildi"):
            sayac["ZATEN"] += 1
            continue
        try:
            sonuc = modul.devir_karari(kalem, simdi)
        except Exception:
            sayac["hata"] = True
            continue
        sebep = sonuc.get("sebep", "")
        if not sonuc.get("devredildi"):
            if sebep == "KAPALI":
                sayac["KAPALI"] += 1
            elif sebep == "SLA_ICINDE":
                sayac["SLA_ICINDE"] += 1
            elif sebep == "ZATEN_DEVREDILDI":
                sayac["ZATEN"] += 1
            continue
        # DEVREDILDI — kalem KraL'a devredildi; iz'e yaz + ihlal sayac artir.
        iz["kalemler"][kimlik] = {
            "devredildi": True,
            "eski_sahip": sonuc.get("eski_sahip"),
            "yeni_sahip": sonuc.get("yeni_sahip"),
            "damga": damga,
        }
        if sonuc.get("ihlal_delta"):
            ev = str(sonuc.get("eski_sahip") or "-")
            iz["ihlal"][ev] = int(iz["ihlal"].get(ev, 0)) + int(sonuc["ihlal_delta"])
            sayac["ihlal_eklenen"] += int(sonuc["ihlal_delta"])
        sayac["DEVREDILDI"] += 1
    iz["son_damga"] = damga
    _devir_iz_yaz(iz)
    return sayac


# K160 dilim-1: TEK KAYNAK kilit govdesi (kilit.py). Diske bytecode YAZILMAZ.
_eski_pyc = sys.dont_write_bytecode
sys.dont_write_bytecode = True
import kilit  # noqa: E402
sys.dont_write_bytecode = _eski_pyc


# --- saf karar fonksiyonlari ----------------------------------------------

def kirmizi_kosumlar(kosumlar, dal="main"):
    """KIRMIZI = conclusion == failure VE headBranch == dal.

    `cancelled` ARIZA DEGILDIR (yeni push eskisini iptal eder); `pending`/
    `in_progress` de kirmizi DEGILDIR; `databaseId` yoksa satir ATLANIR.
    """
    sonuc = []
    for ham in kosumlar or []:
        if not isinstance(ham, dict):
            continue
        if (ham.get("headBranch") or "") != dal:
            continue
        if (ham.get("conclusion") or "") != "failure":
            continue
        kimlik = ham.get("databaseId")
        if not kimlik:
            continue
        sonuc.append({
            "id": str(kimlik),
            "ad": ham.get("name") or ham.get("workflowName") or "",
            "sha": ham.get("headSha") or "",
        })
    return sonuc


def ardilsiz_kirmizilar(kosumlar, dal="main"):
    """K326 — SEVIYE ekseni: ARDILI OLMAYAN kirmizilar (W2-2, 18 Eyl 2026).

    `kirmizi_toplam = len(kirmizi_kosumlar(...))` 40-kosumluk PENCERENIN
    fonksiyonuydu, agacin DEGIL (olculdu 27 Agu: ayni is akisinin uc eski SHA
    dususu 3 ayri kirmizi sayildi; o uc kosum pencereden dusunce hicbir sey
    onarilmadan 3 -> 0). Canli ikinci olcum (18 Eyl): `Build & deploy`
    35346692885 failure'inin ARDILI 35350167808 success iken pencere onu hala
    kirmizi sayiyordu; ESKALASYON sayaci da ayni sebeple ~3 gun `1`de kaldi
    (K311 YUZ B).

    ARDIL = ayni DAL + ayni is akisi ADI + daha BUYUK `databaseId` + conclusion
    `success`. `cancelled`/`in_progress` ardil DEGILDIR — iptal edilen ya da
    suren kosum kirmiziyi COZMEZ (duran kirmizi gorunur kalir; ters yon
    korlugu geri gelmez). Pencere sayaci (`kirmizi_toplam`) SILINMEZ; bu
    fonksiyon onun YANINA ikinci ekseni koyar.
    """
    son_basari = {}
    for ham in kosumlar or []:
        if not isinstance(ham, dict):
            continue
        if (ham.get("headBranch") or "") != dal:
            continue
        if (ham.get("conclusion") or "") != "success":
            continue
        ad = ham.get("name") or ham.get("workflowName") or ""
        try:
            kimlik = int(ham.get("databaseId") or 0)
        except (TypeError, ValueError):
            continue
        if kimlik > son_basari.get(ad, 0):
            son_basari[ad] = kimlik
    sonuc = []
    for kirmizi in kirmizi_kosumlar(kosumlar, dal):
        try:
            kimlik = int(kirmizi["id"])
        except (TypeError, ValueError):
            sonuc.append(kirmizi)     # olculemeyen kimlik ELENMEZ (fail-closed)
            continue
        if son_basari.get(kirmizi.get("ad") or "", 0) > kimlik:
            continue                  # ardili yesil: kirmizi COZULMUS
        sonuc.append(kirmizi)
    return sonuc


def icra_anahtari(tetik, icra_denendi, hedef_run, simdi):
    """K334 — gozcunun ACTIGI turun ANAHTARI (W2-2, 18 Eyl 2026).

    `nobet-tetik.karar()` cift atesleme yasagini `icra_denendi` BAYRAGI
    uzerinden BLANKET uyguluyordu: gozcu HANGI turu actiysa acsin, tetigin
    tur ACAN iki kolu (4 CI_KIRMIZI · 5 GUNLUK_DEFTER) ulasilamaz oluyordu.
    Yasak ANAHTAR eksenine cekilir: gozcu actigi turun anahtarini bu
    fonksiyonla kalbe yazar; tetik yalniz AYNI anahtar icin ACMA der.
    Anahtar bicimi tetigin tuketim damgasiyla AYNI sozlesmedir
    (`kirmizi:<run-id>` · `gunluk:<YYYY-AA-GG>`). DEFTER_DAGITIM turunun
    anahtari `dagitim:<gun>`dur: o tur gunluk defter turu DEGILDIR.
    Tur acilmadiysa "" doner.
    """
    if not icra_denendi:
        return ""
    gun = time.strftime("%Y-%m-%d", time.gmtime(simdi))
    if tetik == "CI_KIRMIZI" and hedef_run:
        return "kirmizi:%s" % hedef_run
    if tetik == "GUNLUK_DEFTER":
        return "gunluk:%s" % gun
    if tetik == "DEFTER_DAGITIM":
        return "dagitim:%s" % gun
    return ""


def yeni_kirmizilar(kirmizilar, durum):
    """Daha once ele alinmamis kirmizilar (flapping freni)."""
    kayitlar = (durum or {}).get("kosumlar") or {}
    yeni = []
    for kirmizi in kirmizilar:
        kayit = kayitlar.get(str(kirmizi["id"]))
        if kayit:
            if (kayit.get("durum") or "") in KAPALI_DURUMLAR:
                continue
            try:
                deneme = int(kayit.get("deneme") or 0)
            except (TypeError, ValueError):
                deneme = 0
            if deneme >= ESKALASYON_ESIGI:
                continue
        yeni.append(kirmizi)
    return yeni


def dagitilabilir_kalemler(kalemler):
    """K147'nin olctugu sinif: MIMAR ve OKAN katlari DAGITILMAZ."""
    return [k for k in NK.onarim_kalemleri(kalemler)
            if NK.kat_sec(k) not in (NK.KAT_MIMAR, NK.KAT_OKAN)]


def kat_sayaci(kalemler):
    sayac = {"MIMAR": 0, "OKAN": 0, "ISCI": 0}
    for kalem in NK.onarim_kalemleri(kalemler):
        kat = NK.kat_sec(kalem)
        if kat == NK.KAT_MIMAR:
            sayac["MIMAR"] += 1
        elif kat == NK.KAT_OKAN:
            sayac["OKAN"] += 1
        else:
            sayac["ISCI"] += 1
    return sayac


def gunluk_tur_gerekli_mi(durum, simdi):
    bugun = time.strftime("%Y-%m-%d", time.gmtime(simdi))
    return ((durum or {}).get("son_gunluk_tur") or "") != bugun


def tetik_karari(yeni_kirmizi, dagitilabilir, gunluk_gerekli, ci_olculdu, defter_olculdu):
    """Tek karar noktasi -> (tetik, llm_turu, rc)."""
    if not ci_olculdu or not defter_olculdu:
        return ("OLCULEMEDI", False, OLCULEMEDI_RC)
    if yeni_kirmizi > 0:
        return ("CI_KIRMIZI", True, 0)
    if dagitilabilir > 0:
        return ("DEFTER_DAGITIM", False, 0)
    if gunluk_gerekli:
        return ("GUNLUK_DEFTER", True, 0)
    return ("YOK", False, 0)


def kilit_karari(icerik, simdi, pid_canli_mi):
    """Semantik nobet-kapi ile AYNI olmali -> oradan cagrilir, kopyalanmaz."""
    return NK.kilit_karari(icerik, simdi, pid_canli_mi)


def deneme_sonraki(kayit, basarili):
    try:
        onceki = int((kayit or {}).get("deneme") or 0)
    except (TypeError, ValueError):
        onceki = 0
    deneme = onceki + 1
    if basarili:
        durum = "KAPANDI"
    elif deneme >= ESKALASYON_ESIGI:
        durum = "ESKALASYON"
    else:
        durum = "DUSTU"
    return {"deneme": deneme, "durum": durum}


def _epok_oku(kalp):
    if not isinstance(kalp, dict):
        return None
    try:
        epok = float(kalp.get("epok"))
    except (TypeError, ValueError):
        return None
    if epok <= 0:
        return None
    return epok


def kalp_bayat_mi(kalp, simdi, tavan_sn=KALP_BAYATLIK_SN):
    epok = _epok_oku(kalp)
    if epok is None:
        return True
    return (simdi - epok) > tavan_sn


def tur_artigi_temizle(dizin, yas_esik=ARTIK_YAS_ESIGI_SN, simdi=None):
    """Disk kurali (Okan, USTUN): ureten temizler. 17 Agu: 2095 tur artigi olculdu.

    Yalniz ARTIK_ONEKLERI ile BASLAYAN, dosya olan ve yasi esigi ASAN girdiler silinir.
    Dizinler (profil-*) bu kolun DISINDADIR: canli turun profili silinirse tur coker.
    """
    simdi = simdi if simdi is not None else time.time()
    try:
        adlar = os.listdir(dizin)
    except OSError:
        return 0
    silinen = 0
    for ad in adlar:
        if not ad.startswith(ARTIK_ONEKLERI):
            continue
        yol = os.path.join(dizin, ad)
        try:
            if not os.path.isfile(yol):
                continue
            if (simdi - os.path.getmtime(yol)) <= yas_esik:
                continue
            os.unlink(yol)
            silinen += 1
        except OSError:
            continue
    return silinen


# === N2-SAHIP-KOPRUSU BAS ===
# N2 (A), 19 Agu 2026 — kirmizi kosumun SAHIBI HARITADAN turetilir.
# TEK KAYNAK: /Users/okan/dev/pruvo/tools/ev-serit-haritasi.tsv
# TEK OKUYUCU: /Users/okan/dev/pruvo/tools/ev-sahip-kapisi.py:kirmizi_sahibi
# Gozcu kendi ev tablosunu TUTMAZ. Harita bozulursa SEBEP=olculemedi doner ve
# tur KIRMIZI biter — "sessiz KraL'a yikma" davranisi YOKTUR.
N2_SAHIP_KAPISI = "/Users/okan/dev/pruvo/tools/ev-sahip-kapisi.py"
N2_REPO_KOKU = "/Users/okan/dev/pruvo"


def n2_sahip_coz(sha, kapi_yolu=None, repo_koku=None):
    """headSha -> (SAHIP, SEBEP). Kapi/harita yuklenemezse ('KraL','olculemedi')."""
    kapi_yolu = kapi_yolu or N2_SAHIP_KAPISI
    repo_koku = repo_koku or N2_REPO_KOKU
    if not sha:
        return ("KraL", "olculemedi")
    try:
        import importlib.util as _n2_ilu
        _n2_spec = _n2_ilu.spec_from_file_location("pruvo_n2a_sahip", kapi_yolu)
        if _n2_spec is None or _n2_spec.loader is None:
            return ("KraL", "olculemedi")
        _n2_mod = _n2_ilu.module_from_spec(_n2_spec)
        _n2_spec.loader.exec_module(_n2_mod)
        _s = _n2_mod.kirmizi_sahibi(repo_koku, sha)
        return (_s.get("SAHIP") or "KraL", _s.get("SEBEP") or "olculemedi")
    except Exception:
        return ("KraL", "olculemedi")


# === N2-SAHIP-KOPRUSU SON ===

# --- B6-ICRA-HALI (20 Agu 2026, KraL-N4B) — K241'in IKINCI yuzeyi ----------
# Olculdu (09:23:00Z): kalpte `icra_rc: 0` (yesil) yaziyordu, ayni turun log
# satiri `NOBET ATLANDI HUKUM=ONCEKI_TUR_SURUYOR` idi -> tur HIC KOSMADI.
# Tek skaler uc hali tasiyor, ucuncusu birincisiyle AYNI degere esleniyordu.
ICRA_HALLERI = ("KOSULMADI", "ATLANDI", "KOSTU_BASARILI", "KOSTU_DUSTU")

# --- K311-URETKEN-HUKUM (26 Agu 2026) --------------------------------------
# OLCULDU (taban): 67 kosum hukmunun 44'u OLCULEMEDI ve 44'unun de GOZCU satiri
# `rc=0` (YESIL) idi; `TUR_HALI=KOSTU_ONARDI` bir kez bile olmadi. KOK:
# `kosum_hukmu` durustce hesaplanip kalbe yaziliyordu ve rc yolunda TEK
# TUKETICISI YOKTU — rc sadece `icra_hal == "KOSTU_DUSTU"` kolundan yukseliyor,
# o alan ise SURECIN rc'sinden turedigi icin "kostu ama IS GORMEDI" halini
# IFADE EDEMIYORDU.
# ([[kapinin-menzili-cagri-yeridir]] · [[iki-kovali-siniflama-ucuncu-sinifi-yutar]])
URETKEN_KOSUM_HUKUMLERI = ("TEMIZ", "ONARIM_DENENDI")


def uretken_mi(kalp):
    """K311: (uretken, sebep) — "bu tur IS GORDU MU?" TEK KARAR NOKTASI.

    Hem gozcunun kendi rc'si hem `nobet-tetik.py`nin 3. basamagi BURADAN okur;
    ikiz kural URETILMEZ (ikiz kural sessizce ayrisir).

    🔴 BEYAZ LISTE + FAIL-CLOSED: yalniz `URETKEN_KOSUM_HUKUMLERI` uretkendir.
    `KOSUM_HUKUMLERI`ne yarin yeni bir deger eklenirse buraya YAZILMADIKCA
    KIRMIZI sayilir — "tanimadigim hukum" SESSIZCE yesil olamaz.

    Iki hal SORUYU ANLAMSIZ kilar ve uretken sayilir:
      · `icra_denendi` false  -> ortada acilmis tur YOK, uretkenlik borcu YOK.
      · `icra_hal == ATLANDI` -> onceki tur suruyor; ikinci turun borcu YOK
        (yoksa kilit dolu her turda hat kirmizi yanar — yanlis pozitif).
    """
    kalp = kalp or {}
    if not kalp.get("icra_denendi"):
        return True, "ICRA_DENENMEDI"
    if (kalp.get("icra_hal") or "KOSULMADI") == "ATLANDI":
        return True, "ATLANDI"
    hukum = kalp.get("kosum_hukmu") or "OLCULEMEDI"
    if hukum in URETKEN_KOSUM_HUKUMLERI:
        return True, hukum
    return False, hukum


def eskalasyon_acik_say(durum, kirmizilar):
    """K311: `gozcu-eskalasyon.md`nin EKSIK TUKETICISI.

    OLCULDU: dosyaya 19-26 Agu arasi 42 satir yazildi (ISTISNASIZ `deneme=3`)
    ve gozcu.py / nobet-kapi.py / nobet_merdiven.py icinde o dosyayi OKUYAN TEK
    SATIR YOKTU. Eskalasyon bir DOSYA KAYDIYDI, bir KARAR DEGILDI.

    Burada esas alinan sey dosyanin METNI degil, eskalasyon satirini yazan AYNI
    kayittir (`durum["kosumlar"][run]["durum"] == "ESKALASYON"`); kesisim ise
    CANLI kirmizi kumesidir. Boylece sayac KENDILIGINDEN duser (run yesile
    donunce) — elle sifirlama YOK ([[silme-sayaci-diskten-dogrulanmali]]).
    """
    kosumlar = (durum or {}).get("kosumlar") or {}
    canli = set()
    for k in (kirmizilar or []):
        try:
            canli.add(str(k.get("id")))
        except AttributeError:
            continue
    acik = 0
    for run_id, kayit in kosumlar.items():
        if str(run_id) in canli and (kayit or {}).get("durum") == "ESKALASYON":
            acik += 1
    return acik

_KOSUM_HUKMU_DESENI = re.compile(r"(?<![A-Za-z0-9_])KOSUM_HUKMU\s*=\s*([A-Z_]+)")


def kosum_hukmunu_ayikla(cikti):
    """B5: RUN-ID denemesi DEFTER bacagindan DEGIL, kosumun KENDI hukmunden.

    Jeton yoksa `OLCULEMEDI` doner (fail-closed): "okuyamadim" SESSIZCE
    "temiz" DEMEK DEGILDIR — deneme yine artar, eskalasyon yolu ACIK kalir.
    """
    eslesme = _KOSUM_HUKMU_DESENI.findall(cikti or "")
    return eslesme[-1] if eslesme else "OLCULEMEDI"


_TUR_HALI_DESENI = re.compile(r"(?<![A-Za-z0-9_])TUR_HALI\s*=\s*([A-Z_]+)")

# 🔴 KOL B4 (27 Agu 2026, KraL-NobetTuru-27Agu)
# `icra_hal=KOSTU_DUSTU` kalbe yaziliyordu ama SEBEBI hicbir yere
# yazilmiyordu: `icra_cikti` yakalanip ATILIYOR ([[gozcu.py]] `tur_kosucu`
# ciktisi yalniz jeton taramasinda kullaniliyordu). Okuyan elinde tek
# "sebep" olarak `OLCULEMEDI` kaliyordu -- ki o bir SEBEP DEGIL, olcum
# EKSIKLIGIDIR. Bu kol menzili daraltir: dusen icranin hukmu, sureç rc'si
# ve son anlamli satirin imzasi ADIYLA kaydedilir.
_ICRA_HUKUM_DESENI = re.compile(r"(?<![A-Za-z0-9_])HUKUM\s*=\s*([A-Z][A-Z0-9_]*)")


def icra_sebebini_ayikla(icra_hal, icra_rc, cikti, tavan=80):
    """(sebep_str) — dusen icranin sebebi ADIYLA.

    Sira: (1) ciktidaki SON makine `HUKUM=` degeri; (2) yoksa son bos
    olmayan satirin kisaltilmis imzasi. Ikisi de yoksa `CIKTI_BOS`.
    Hicbir kolda cikplak `OLCULEMEDI` DONMEZ -- her hal bir MENZIL bildirir.
    """
    if icra_hal != "KOSTU_DUSTU":
        return "-"
    metin = cikti or ""
    eslesme = _ICRA_HUKUM_DESENI.findall(metin)
    if eslesme:
        return "HUKUM=%s rc=%s" % (eslesme[-1], icra_rc)
    satirlar = [s.strip() for s in metin.splitlines() if s.strip()]
    if not satirlar:
        return "CIKTI_BOS rc=%s" % (icra_rc,)
    imza = satirlar[-1]
    if len(imza) > tavan:
        imza = imza[:tavan] + "..."
    return "SON_SATIR=%r rc=%s" % (imza, icra_rc)


def icra_halini_coz(denendi, ham_rc, cikti):
    """B6: (icra_hal, icra_rc) — uc hal UC degere ayrilir.

    Kaynak sirasi: (1) turun KENDI beyani `TUR_HALI=` — nobet-kapi B8'den
    beri HER cikis yolunda basar; (2) `NOBET ATLANDI` satiri (B8 oncesi
    kalintilar ve eski loglar icin); (3) ham rc.
    ATLANDI'da `icra_rc` None doner: "kostu ve basardi" ile "HIC KOSMADI"
    ayni degere DUSMEZ.
    """
    if not denendi or ham_rc is None:
        return "KOSULMADI", None
    metin = cikti or ""
    beyanlar = _TUR_HALI_DESENI.findall(metin)
    if (beyanlar and beyanlar[-1] == "ATLANDI") or "NOBET ATLANDI" in metin:
        return "ATLANDI", None
    if ham_rc == 0:
        return "KOSTU_BASARILI", 0
    return "KOSTU_DUSTU", ham_rc


def kalp_satiri(kalp):
    """Insana basilan satir kalp DOSYASIYLA ayni alanlardan turer (tek kaynak)."""
    kalp = kalp or {}
    n2 = kalp.get("n2_devir") or {}
    return ("GOZCU %s TETIK=%s LLM_TURU=%d YENI_KIRMIZI=%d DAGITILABILIR=%d "
            "KAT_MIMAR=%d KAT_OKAN=%d GUNLUK=%d ARTIK_SILINEN=%d CI_SEBEP=%s rc=%d SAHIP=%s SEBEP=%s "
            "N2_D=%d S=%d K=%d Z=%d I=%d BEKCI=%s BEKCI_SEBEP=%s BEKCI_BILDIRIM=%s "
            "TESLIM_KANCA=%s TESLIM_KALP=%.1fh TESLIM_OLU=%s "
            "ICRA_HAL=%s ICRA_SEBEP=%s") % (
        kalp.get("damga") or "-",
        kalp.get("tetik") or "-",
        1 if kalp.get("llm_turu") else 0,
        int(kalp.get("yeni_kirmizi") or 0),
        int(kalp.get("dagitilabilir") or 0),
        int(kalp.get("kat_mimar") or 0),
        int(kalp.get("kat_okan") or 0),
        1 if kalp.get("gunluk_gerekli") else 0,
        int(kalp.get("artik_silinen") or 0),
        kalp.get("ci_sebep") or "-",
        int(kalp.get("rc") or 0),
        kalp.get("sahip") or "-",
        kalp.get("sahip_sebep") or "-",
        int(n2.get("DEVREDILDI") or 0),
        int(n2.get("SLA_ICINDE") or 0),
        int(n2.get("KAPALI") or 0),
        int(n2.get("ZATEN") or 0),
        int(n2.get("ihlal_eklenen") or 0),
        kalp.get("bekci_hukum") or "-",
        kalp.get("bekci_sebep") or "-",
        kalp.get("bekci_bildirim") or "-",
        kalp.get("bekci_teslim_kanca"),
        float(kalp.get("bekci_teslim_kalp_saat") or -1.0),
        kalp.get("bekci_teslim_olu") or "-",
        kalp.get("icra_hal") or "-",
        kalp.get("icra_sebep") or "-",
    )


# --- yan etkili yardimcilar -----------------------------------------------

def _json_oku(yol, varsayilan):
    try:
        with open(yol, encoding="utf-8") as dosya:
            veri = json.load(dosya)
    except (OSError, ValueError):
        return dict(varsayilan)
    if not isinstance(veri, dict):
        return dict(varsayilan)
    for anahtar, deger in varsayilan.items():
        veri.setdefault(anahtar, deger)
    return veri


def _json_yaz(veri, yol):
    """Atomik: mkstemp + fsync + os.replace (geri_iz_yaz deseninin aynisi)."""
    dizin = os.path.dirname(yol) or "."
    os.makedirs(dizin, exist_ok=True)
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=".gozcu-gecici.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as dosya:
            json.dump(veri, dosya, ensure_ascii=False, indent=2, sort_keys=True)
            dosya.write("\n")
            dosya.flush()
            os.fsync(dosya.fileno())
        os.replace(gecici, yol)
    except BaseException:
        try:
            os.unlink(gecici)
        except OSError:
            pass
        raise


def durum_oku(yol=None):
    return _json_oku(yol or DURUM_YOLU,
                     {"kosumlar": {}, "son_gunluk_tur": "", "taban_alindi": False})


def kalp_oku(yol=None):
    yol = yol or KALP_YOLU
    if not os.path.exists(yol):
        return None
    return _json_oku(yol, {})


def _damga(simdi):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(simdi))


def _loga_yaz(satirlar, yol, tavan=LOG_TAVANI):
    try:
        with open(yol, "a", encoding="utf-8") as dosya:
            for satir in satirlar:
                dosya.write(satir.rstrip("\n") + "\n")
        with open(yol, encoding="utf-8") as dosya:
            hepsi = dosya.read().split("\n")
        if len(hepsi) > tavan:
            with open(yol, "w", encoding="utf-8") as dosya:
                dosya.write("\n".join(hepsi[-tavan:]))
    except OSError:
        pass


def _kilit_al(yol, simdi, pid_canli, _araya_gir=None):
    """Adaptör — govde kilit.py'de (TEK KAYNAK, K160 dilim-1)."""
    return kilit.al(yol, simdi, pid_canli, "%.3f", lambda: _damga(simdi), _araya_gir)[0]


def _kilit_birak(yol):
    """Adaptör — govde kilit.py'de (TEK KAYNAK, K160 dilim-1)."""
    return kilit.birak(yol)


def _gh_ikili():
    bulunan = shutil.which("gh")
    if bulunan:
        return bulunan
    for aday in (os.path.join(dizin, "gh") for dizin in BILINEN_BIN_DIZINLERI):
        if os.path.isfile(aday) and os.access(aday, os.X_OK):
            return aday
    return None


def _path_genislet():
    mevcut = os.environ.get("PATH", "").split(os.pathsep)
    eklenecek = [dizin for dizin in BILINEN_BIN_DIZINLERI
                 if os.path.isdir(dizin) and dizin not in mevcut]
    os.environ["PATH"] = os.pathsep.join(eklenecek + mevcut)


def _gh_kosumlar(dal="main", limit=40):
    """CI kosumlarini ve fail-closed olcum sebebini dondurur."""
    ikili = _gh_ikili()
    if ikili is None:
        return (None, "IKILI_YOK")
    komut = [ikili, "run", "list", "--branch", dal, "--limit", str(limit),
             "--json", "databaseId,name,conclusion,status,headBranch,headSha,createdAt"]
    try:
        sonuc = subprocess.run(komut, cwd=NK.EV_KOKU, capture_output=True,
                               text=True, timeout=GH_ZAMAN_ASIMI_SN)
    except subprocess.TimeoutExpired:
        return (None, "ZAMAN_ASIMI")
    except (OSError, subprocess.SubprocessError):
        return (None, "IKILI_YOK")
    if sonuc.returncode != 0:
        return (None, "RC:%d" % sonuc.returncode)
    try:
        veri = json.loads(sonuc.stdout)
    except ValueError:
        return (None, "JSON_BOZUK")
    if not isinstance(veri, list):
        return (None, "JSON_BOZUK")
    return (veri, "TAMAM")


def _defter_kalemleri():
    try:
        return NK.defter_oku()
    except (OSError, ValueError):
        return None


def _gercek_tur_kosucu(bayraklar):
    komut = [sys.executable, NOBET_KAPI_YOLU] + list(bayraklar)
    try:
        sonuc = subprocess.run(komut, cwd=CRON_KOKU, capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError) as hata:
        return (1, "ICRA_DUSTU: %s" % hata)
    return (sonuc.returncode, (sonuc.stdout or "") + (sonuc.stderr or ""))


def _eskalasyon_yaz(yol, kirmizi, kayit, damga):
    try:
        with open(yol, "a", encoding="utf-8") as dosya:
            dosya.write("- %s run=%s ad=%s deneme=%d DURUM=ESKALASYON\n"
                        % (damga, kirmizi.get("id"), kirmizi.get("ad") or "-",
                           kayit.get("deneme", 0)))
    except OSError:
        pass


def varsayilan_yollar():
    return {
        "durum": DURUM_YOLU,
        "kalp": KALP_YOLU,
        "log": LOG_YOLU,
        "kilit_dizini": KILIT_DIZINI,
        "eskalasyon": ESKALASYON_YOLU,
        "artik_dizini": CRON_KOKU,
    }


# --- tur ------------------------------------------------------------------

def tur(kuru=False, simdi=None, kosum_okuyucu=None, defter_okuyucu=None,
        tur_kosucu=None, yollar=None, pid_canli=None):
    """Bir gozcu turu. `kuru=True` hicbir sey acmaz/yazmaz/silmez."""
    simdi = simdi if simdi is not None else time.time()
    yollar = dict(varsayilan_yollar(), **(yollar or {}))
    kosum_okuyucu = kosum_okuyucu or _gh_kosumlar
    defter_okuyucu = defter_okuyucu or _defter_kalemleri
    tur_kosucu = tur_kosucu or _gercek_tur_kosucu
    pid_canli = pid_canli or NK._pid_canli

    durum = durum_oku(yollar["durum"])

    kosum_sonucu = kosum_okuyucu()
    if (isinstance(kosum_sonucu, tuple) and len(kosum_sonucu) == 2
            and isinstance(kosum_sonucu[1], str)):
        ham_kosumlar, ci_sebep = kosum_sonucu
    else:
        ham_kosumlar = kosum_sonucu
        ci_sebep = "TAMAM" if ham_kosumlar is not None else "OLCULEMEDI"
    ci_olculdu = ci_sebep == "TAMAM" and ham_kosumlar is not None
    kirmizilar = kirmizi_kosumlar(ham_kosumlar or [])
    # K326: SEVIYE ekseni — ardili yesil olan kirmizi DURAN kirmizi degildir.
    ardilsiz = ardilsiz_kirmizilar(ham_kosumlar or [])

    kalemler = defter_okuyucu()
    defter_olculdu = kalemler is not None
    kalemler = kalemler or []

    # K263 CANLI KABLOLAMA: her GERCEK turda acik kalemlere devir_karari()
    # kosar. Yarim is KESILMEZ — kalem listesi DEGISMEZ; devir yalniz
    # iz/sayac dosyalarina yansir. IKI YONLU: devir_karari() 4 saatten
    # ONCE devir OLMAZ, 4 saatte OLUR kararini ZATEN verir. kuru=True
    # durumunda dosya yazilmaz (test karari): sayac sifir kalir.
    devir_sayaci = (n2_devir_kararlari(kalemler, simdi)
                    if not kuru
                    else {"DEVREDILDI": 0, "SLA_ICINDE": 0, "KAPALI": 0,
                          "ZATEN": 0, "ihlal_eklenen": 0, "hata": False})

    taban_alinan = 0
    if not durum.get("taban_alindi"):
        # Ilk kosum: gecmisin TUM kirmizilarina birden isci acmayiz (isci firtinasi).
        if ci_olculdu:
            for kirmizi in kirmizilar:
                durum.setdefault("kosumlar", {})[str(kirmizi["id"])] = {
                    "deneme": 0, "durum": "TABAN", "ad": kirmizi.get("ad", ""),
                    "damga": _damga(simdi)}
                taban_alinan += 1
            durum["taban_alindi"] = True

    yeni = yeni_kirmizilar(kirmizilar, durum)
    dagitilabilir = dagitilabilir_kalemler(kalemler)
    sayac = kat_sayaci(kalemler)
    gunluk = gunluk_tur_gerekli_mi(durum, simdi)

    tetik, llm_turu, rc = tetik_karari(len(yeni), len(dagitilabilir), gunluk,
                                       ci_olculdu, defter_olculdu)

    # N1 (19 Agu 2026): tetigin (nobet-tetik.py) "o run-id icin TEK tur" garantisini
    # verebilmesi icin HEDEF run-id kalbe damgalanir. Kuru turda da yazilir (karar
    # ayni, yalniz icra yok). Kirmizi disi tetiklerde BOS kalir.
    hedef_run = str(yeni[0]["id"]) if (tetik == "CI_KIRMIZI" and yeni) else ""

    artik_silinen = 0
    if not kuru:
        artik_silinen = tur_artigi_temizle(yollar["artik_dizini"], simdi=simdi)

    icra_rc = None
    icra_cikti = ""
    icra_notu = ""
    icra_hal = "KOSULMADI"    # B6: hal, rc'den AYRI alandir
    kosum_hukmu = "KOSULMADI"  # B5: RUN-ID denemesinin AYRI oznesi
    icra_denendi = False      # B6: "tur ACILDI MI" sorusu rc'den AYRIDIR
    if not kuru and tetik == "CI_KIRMIZI":
        hedef = yeni[0]
        kilit_yolu = os.path.join(yollar["kilit_dizini"], "%s.kilit" % hedef["id"])
        if not _kilit_al(kilit_yolu, simdi, pid_canli):
            icra_notu = "KILIT=DOLU run=%s" % hedef["id"]
        else:
            icra_denendi = True
            try:
                icra_rc, icra_cikti = tur_kosucu(["--tur"])
            finally:
                _kilit_birak(kilit_yolu)
            icra_hal, icra_rc = icra_halini_coz(True, icra_rc, icra_cikti)
            kosum_hukmu = kosum_hukmunu_ayikla(icra_cikti)
            # 🔴 B6: ATLANAN tur DENEME SAYMAZ. Onceden kosul `icra_rc == 0`
            # idi ve atlanan tur `0` dondugu icin deneme sayaci SAHTE bir
            # "basarili" kaydiyla kapaniyordu — kosmayan tur basarili sayilamaz.
            if icra_hal in ("KOSTU_BASARILI", "KOSTU_DUSTU"):
                kayit = (durum.get("kosumlar") or {}).get(str(hedef["id"])) or {}
                # 🔴 B5: run-id denemesi DEFTER bacagindan DEGIL, KOSUMUN
                # kendi hukmunden turer. `icra_hal` surecin rc'sidir ve defter
                # bacagi ONARIMSIZ_TUR yazinca CI temiz olsa bile DUSTU olur.
                yeni_kayit = deneme_sonraki(kayit, kosum_hukmu == "TEMIZ")
                yeni_kayit["ad"] = hedef.get("ad", "")
                yeni_kayit["damga"] = _damga(simdi)
                durum.setdefault("kosumlar", {})[str(hedef["id"])] = yeni_kayit
                if yeni_kayit["durum"] == "ESKALASYON":
                    _eskalasyon_yaz(yollar["eskalasyon"], hedef, yeni_kayit, _damga(simdi))
    elif not kuru and tetik == "DEFTER_DAGITIM":
        icra_denendi = True
        icra_rc, icra_cikti = tur_kosucu(["--tur-kapat"])
        icra_hal, icra_rc = icra_halini_coz(True, icra_rc, icra_cikti)
        kosum_hukmu = kosum_hukmunu_ayikla(icra_cikti)
    elif not kuru and tetik == "GUNLUK_DEFTER":
        icra_denendi = True
        icra_rc, icra_cikti = tur_kosucu(["--tur"])
        icra_hal, icra_rc = icra_halini_coz(True, icra_rc, icra_cikti)
        kosum_hukmu = kosum_hukmunu_ayikla(icra_cikti)
        durum["son_gunluk_tur"] = time.strftime("%Y-%m-%d", time.gmtime(simdi))

    # B6: KIRMIZI hukmu artik HAL'den okunur. ATLANDI turu (bugunku gibi) rc'yi
    # YUKSELTMEZ — ama artik SESSIZ YESIL de degildir: kalbe `icra_hal=ATLANDI`
    # yazilir ve "ardisik yesil tur" sayan hicbir tuketici onu SAYAMAZ.
    # 🔴 KOL B4: dusen icranin sebebi ADIYLA hesaplanir (kalbe + insan satirina).
    icra_sebep = icra_sebebini_ayikla(icra_hal, icra_rc, icra_cikti)
    if icra_hal == "KOSTU_DUSTU":
        rc = max(rc, 1)

    # 🔴 BAYAT OKUYUCU ONARIMI (29 Agu 2026, cip KraL-K350-TeslimTatbikati-29Agu).
    # `tetik_karari` "tur GEREKIR" der; alan adi "tur ACILDI" diye OKUNUR. Kol
    # 28 Agu'da kapatildi -> canli 23:08:01Z turu `KOSUM_HUKMU=LLM_KOLU_KAPALI`
    # dondururken Okan'in gordugu satir `LLM_TURU=1` basiyordu. Alan artik
    # GERCEGI soyler: ACILMAYAN tur 0'dir. Bilgi KAYBI yok — "tur gerekiyordu"
    # bilgisi `TETIK=CI_KIRMIZI` alaninda ZATEN duruyor.
    # KARAR MANTIGI DEGISMEDI: `tetik_karari` esikleri ve eskalasyon AYNI; bu
    # deger bu noktadan sonra HICBIR karara girmez (yalniz `kalp` + `satir`).
    # TEK KAYNAK: jeton `NK.HUKUM_LLM_KOLU_KAPALI`; ikinci literal YAZILMADI.
    # FAIL-CLOSED + DAR: jeton okunamazsa (None) hicbir sey susturulmaz; yalniz
    # TAM O hukum susturur ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
    if LLM_KOLU_KAPALI is not None and kosum_hukmu == LLM_KOLU_KAPALI:
        llm_turu = False

    # 🔴 K311 YUZ A — KOSTU ama IS GORMEDI: SESSIZ YESIL URETME.
    # Taban: 44 OLCULEMEDI turun 44'u de rc=0 donuyordu. Karar TEK NOKTADAN
    # (`uretken_mi`) okunur; `nobet-tetik.py` de AYNI fonksiyonu cagirir.
    uretken, uretken_sebep = uretken_mi({
        "icra_denendi": icra_denendi,
        "icra_hal": icra_hal,
        "kosum_hukmu": kosum_hukmu,
    })
    # 🔴 UCUNCU HAL: kol KAPALIYSA tur "IS GORMEDI" ama bu bir ARIZA DEGIL.
    # Sessizlestirme DAR: yalniz TAM O jeton. `OLCULEMEDI` dahil diger her
    # uretken-olmayan hukum KIRMIZI KALIR ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
    if not uretken and not (LLM_KOLU_KAPALI is not None
                            and uretken_sebep == LLM_KOLU_KAPALI):
        rc = max(rc, 1)

    # 🔴 K311 YUZ B — eskalasyon artik TUKETILIYOR. Hala kirmizi olan bir
    # run-id ESKALASYON'a dustuyse gozcu KIRMIZI kapanir; 42 sessiz satirin
    # sinifi budur.
    # 🔴 W2-2 (18 Eyl 2026) — kesisim kumesi PENCERE degil ARDILSIZ kirmizi.
    # Olculdu: run 35323115483 (SERIT B) ESKALASYON'a dustu, ardili
    # 35328100912 SUCCESS oldu; sayac yine de `1`de kaldi ve ci-nobeti
    # `HUKUM=ESKALASYON_ACIK rc=1` basmaya devam etti — ta ki kosum 40'lik
    # pencereden dusene kadar (onarimla degil, ZAMANLA). Basarisiz bir kosum
    # ASLA yesile donmez; "cozuldu" sorusunun cevabi ARDILDADIR.
    eskalasyon_acik = eskalasyon_acik_say(durum, ardilsiz)
    if eskalasyon_acik:
        rc = max(rc, 1)

    # 🔴 CIP-DOGUM BEKCISI (26 Agu 2026) — KOL_ADI=BEKCI_KOL.
    # Kural: yerel saat >= 09:00 VE bugunun `KraL-Tamirci-<YYYYAAGG>.md` dogum
    # kaniti YOK -> KIRMIZI + Okan'a UYGULAMA BILDIRIMI (gun basina en fazla 1).
    # `kuru=True` turda karar VERILIR ama bildirim GONDERILMEZ.
    bekci = _bekci_kolu(simdi, kuru)
    if bekci.get("kirmizi"):
        rc = max(rc, 1)

    # N2 (A): kirmizi kosumun SAHIBI — harita TEK KAYNAK.
    n2_sahip = ("-", "-")
    if tetik == "CI_KIRMIZI" and yeni:
        n2_sahip = n2_sahip_coz(yeni[0].get("sha"))
        if n2_sahip[1] == "olculemedi":
            rc = max(rc, 1)   # harita/git olculemedi -> GOZCU KIRMIZI

    kalp = {
        "damga": _damga(simdi),
        "sahip": n2_sahip[0],
        "sahip_sebep": n2_sahip[1],
        "epok": simdi,
        "tetik": tetik,
        "llm_turu": bool(llm_turu),
        "yeni_kirmizi": len(yeni),
        "hedef_run": hedef_run,
        "kirmizi_toplam": len(kirmizilar),     # PENCERE ekseni (SILINMEZ)
        "kirmizi_ardilsiz": len(ardilsiz),     # K326 SEVIYE ekseni
        "dagitilabilir": len(dagitilabilir),
        "kat_mimar": sayac["MIMAR"],
        "kat_okan": sayac["OKAN"],
        "kat_isci": sayac["ISCI"],
        "gunluk_gerekli": bool(gunluk),
        "artik_silinen": artik_silinen,
        "taban_alinan": taban_alinan,
        "ci_olculdu": ci_olculdu,
        "ci_sebep": ci_sebep,
        "defter_olculdu": defter_olculdu,
        "icra_rc": icra_rc,        # B6: ATLANDI'da None
        "icra_hal": icra_hal,      # B6: uc hal UC deger
        "icra_sebep": icra_sebep,  # KOL B4: KOSTU_DUSTU'nun SEBEBI, adiyla
        "kosum_hukmu": kosum_hukmu,  # B5: run-id oznesi, defterden AYRI
        "icra_denendi": bool(icra_denendi),
        # K334: cift atesleme yasagi ANAHTAR ekseninde (nobet-tetik.karar).
        "icra_anahtar": icra_anahtari(tetik, icra_denendi, hedef_run, simdi),
        # K311: rc yolunun FIILEN TUKETTIGI alanlar. `k311-baglanti-kapisi.py`
        # bu alanlarin canli tuketicisini SAYARAK olcer.
        "uretken": bool(uretken),
        "uretken_sebep": uretken_sebep,
        "eskalasyon_acik": eskalasyon_acik,
        # CIP-DOGUM BEKCISI: rc yolunun FIILEN tukettigi alanlar.
        "bekci_hukum": bekci.get("hukum") or "OLCULEMEDI",
        "bekci_sebep": bekci.get("sebep") or "-",
        "bekci_kanit": bekci.get("kanit_adi") or "-",
        "bekci_saat": bekci.get("saat"),
        "bekci_kirmizi": bool(bekci.get("kirmizi")),
        "bekci_kanal": (bekci.get("bildirim") or {}).get("kanal") or "-",
        # TESLIM KOLUNUN KENDI OLCUMU — "bekci yesil ama sesi ulasmiyor" hali
        # bu iki alanla GORUNUR olur (mimar ek maddesi, 26 Agu).
        "bekci_teslim_kanca": (bekci.get("teslim") or {}).get("kanca"),
        "bekci_teslim_kalp_saat": (bekci.get("teslim") or {}).get("kalp_saat"),
        "bekci_teslim_sebep": (bekci.get("teslim") or {}).get("sebep") or "-",
        # Olu kol SAG hukum altinda bile BASILIR — yedeklilik is gorse de
        # bakim borcu gizlenmez (15:00/17:00 kolu bunu KraL blogunda basar).
        "bekci_teslim_olu": ",".join((bekci.get("teslim") or {}).get("olu") or []) or "-",
        "bekci_bildirim": (bekci.get("bildirim") or {}).get("teslim") or "-",
        "bekci_bildirim_rc": (bekci.get("bildirim") or {}).get("rc"),
        "bekci_gonderildi": bool((bekci.get("bildirim") or {}).get("gonderildi")),
        "rc": rc,
        "kuru": bool(kuru),
        "n2_devir": devir_sayaci,    # K263 CANLI KABLOLAMA sayaci
    }
    satir = kalp_satiri(kalp)

    if not kuru:
        _json_yaz(durum, yollar["durum"])
        _json_yaz(kalp, yollar["kalp"])
        satirlar = [satir]
        if icra_notu:
            satirlar.append("  " + icra_notu)
        if icra_cikti:
            satirlar.extend("  " + s for s in icra_cikti.strip().split("\n") if s.strip())
        _loga_yaz(satirlar, yollar["log"])

    return {"tetik": tetik, "llm_turu": llm_turu, "rc": rc, "kalp": kalp,
            "satir": satir, "icra_rc": icra_rc, "icra_notu": icra_notu,
            "icra_hal": icra_hal, "icra_denendi": bool(icra_denendi),
            "bekci": bekci}


def kalp_hukmu(simdi=None, yol=None):
    simdi = simdi if simdi is not None else time.time()
    kalp = kalp_oku(yol)
    if kalp is None:
        return ("GOZCU_KALP=YOK", 1)
    if kalp_bayat_mi(kalp, simdi):
        return (kalp_satiri(kalp) + " KALP=BAYAT", 1)
    return (kalp_satiri(kalp) + " KALP=TAZE", 0)


def main(argv=None):
    ayristirici = argparse.ArgumentParser(description="PRUVO nobet gozcusu (olay tetigi)")
    ayristirici.add_argument("--tur", action="store_true", help="tam gozcu turu")
    ayristirici.add_argument("--kuru", action="store_true",
                             help="hicbir sey acmaz/yazmaz/silmez; karari basar")
    ayristirici.add_argument("--kalp", action="store_true",
                             help="son kalp atisi; BAYAT ise rc=1")
    args = ayristirici.parse_args(argv)

    if args.kalp:
        satir, rc = kalp_hukmu()
        print(satir + (" rc=%d" % rc if "rc=" not in satir else ""))
        return rc
    if args.kuru:
        sonuc = tur(kuru=True)
        print(sonuc["satir"])
        return sonuc["rc"]
    if args.tur:
        _path_genislet()
        sonuc = tur()
        print(sonuc["satir"])
        return sonuc["rc"]
    ayristirici.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
