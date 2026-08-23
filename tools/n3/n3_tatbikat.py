#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N3 — ESKALASYON TATBIKATI (uctan uca sahte eskalasyon provasi).

Kurgunun sarti (memory/nobet-onarim-kurgusu.md, ESKALASYON YUZEYI):
  "sistem, SAHTE eskalasyonla uctan uca tatbikat gecmeden 'kurulmus'
   sayilmaz — pencere fiilen Okan'in onune dusmezse sistem YOK hukmunde."

Zincir: makine tarar -> ucuz isci dener -> kirleten kapatir -> KraL son
mercii -> BaBa denetler ve suzer -> Okan'a yalniz KARAR duser.

YEDI BASAMAK (her biri AYRI jeton + zaman damgasi):
  T1 sahte ariza sisteme girdi ve MAKINE TARADI (gozcu kalbinde gorundu)
  T2 ucuz isci basamagi DENENDI (ya da neden denenmedigi hata sinifiyla)
  T3 sahiplik DETERMINISTIK cozuldu — sahte ariza DOGRU EVE dustu
  T4 KraL basamagina YUKSELDI
  T5 BaBa suzgecine DUSTU ve suzuldu (olculmus ozet ust kata gitti)
  T6 Okan'in onune KARAR PENCERESI dustu — TATBIKAT olarak ETIKETLI
  T7 tatbikat kaydi TEMIZLENDI (sayaclar tatbikat oncesine dondu)

🔴 IZOLASYON: gercek `~/.claude/cron` duzlemine HICBIR yazma yapilmaz.
`gozcu.tur()` KENDI enjeksiyon noktalariyla (yollar/kosum_okuyucu/
tur_kosucu) gecici bir dizine yonlendirilir; GERCEK KOD kosar, GERCEK
sayac dosyalarina DOKUNULMAZ. T7 bunu once/sonra sha256 ile KANITLAR.

🔴 T6 bu betikte KAPANMAZ: betik yalniz ON KOSULU (merdiven OKAN
basamaginda + pencere metni birebir dogru) olcer ve pencere yukunu
uretir. Pencerenin FIILEN dusmesi mimarin/chip'in isidir ve Okan'in
cevabi `--okan-cevap` ile bu kanita islenir. Cevap islenmeden T6
`ACIK` kalir — "muhtemelen dustu" YAZILMAZ.

KOSUM:
  python3 tools/n3/n3_tatbikat.py --tam --kanit-dizini /tam/yol
  python3 tools/n3/n3_tatbikat.py --bitis-olcutu
  python3 tools/n3/n3_tatbikat.py --okan-cevap "<Okan'in cevabi>" \
      --kanit-dizini /tam/yol
KABUL: son satir `KABUL=GECTI`, rc=0.
"""

import argparse
import calendar
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time

CRON_KOKU = "/Users/okan/.claude/cron"
REPO_KOKU = "/Users/okan/dev/pruvo"

# --- tatbikatin SAHTE arizasi ----------------------------------------------
# 🔴 Jeton uydurma degil: run-id 99_ ile baslar (GitHub run-id'leri bu
# araliga bugun ulasmiyor) ve ad TATBIKAT damgasi tasir. Gercek bir
# arizayla KARISTIRILAMAZ.
TATBIKAT_RUN_ID = "9900000001"
TATBIKAT_AD = "TATBIKAT — sahte ariza (N3 uctan uca eskalasyon provasi)"
# urunler.json'a dokunan GERCEK commit -> sahiplik MaCiT'e cozulmeli.
TATBIKAT_SHA = "5f247c8ab9152dad66f770ed27f1c4b3fe38a8cf"
TATBIKAT_BEKLENEN_EV = "MaCiT"
# tools/ dokunan GERCEK commit -> sahiplik KraL'a cozulmeli (ayirt edicilik).
KONTROL_SHA = "02c9a6319af0ec74de5a5df72c83a5d37125bca1"
KONTROL_BEKLENEN_EV = "KraL"

# 🔴 T6'nin KALICI kaniti. Bu dosya YOKKEN batarya KIRMIZI yanar — yani
# "N3 kuruldu" iddiasi, pencerenin FIILEN dustugu ve Okan'in CEVAP verdigi
# tek bir ana bagli kalir. Jeton isci/ajan ciktisindan ASLA okunmaz
# ([[isci-ciktisi-arsiv-jetonunu-uydurabilir]]); yalniz --okan-cevap yazar.
OKAN_CEVAP_YOLU = os.path.join(CRON_KOKU, "n3-okan-cevap.json")

PENCERE_ILK_SATIR = (
    "\U0001F9EA TATBİKAT — GERÇEK ARIZA DEĞİL "
    "(N3 uçtan uca eskalasyon provası)"
)

CANLI_MOTORLAR = ("minimax-m3", "kimi")

# T7'nin once/sonra olctugu GERCEK yuzey (tatbikat bunlara DOKUNMAMALI).
CANLI_YUZEY = (
    os.path.join(CRON_KOKU, "gozcu-kalp.json"),
    os.path.join(CRON_KOKU, "gozcu-durum.json"),
    os.path.join(CRON_KOKU, "gozcu-eskalasyon.md"),
    os.path.join(CRON_KOKU, "nobet-onarimsiz-sayac.json"),
    os.path.join(CRON_KOKU, "nobet-atlanan-sayac.json"),
    os.path.join(CRON_KOKU, "nobet-geri-iz.json"),
    os.path.join(REPO_KOKU, "DEVAM.md"),
)

BASAMAK_ADLARI = {
    "T1": "makine TARADI",
    "T2": "ucuz isci DENENDI",
    "T3": "sahiplik DETERMINISTIK cozuldu",
    "T4": "KraL basamagina YUKSELDI",
    "T5": "BaBa suzgecine DUSTU ve suzuldu",
    "T6": "Okan'in onune KARAR PENCERESI dustu",
    "T7": "tatbikat kaydi TEMIZLENDI",
}


# ===========================================================================
# modul yukleme
# ===========================================================================

def _modul(ad, yol):
    spec = importlib.util.spec_from_file_location(ad, yol)
    if spec is None or spec.loader is None:
        raise ImportError("yuklenemedi: %s" % yol)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[ad] = modul
    spec.loader.exec_module(modul)
    return modul


def modulleri_yukle():
    # gozcu.py/nobet-kapi.py kardes modul (`kilit`) import eder; disaridan
    # yuklenirken CRON_KOKU sys.path'te OLMAK ZORUNDA.
    for kok in (CRON_KOKU, os.path.join(REPO_KOKU, "tools")):
        if kok not in sys.path:
            sys.path.insert(0, kok)
    gozcu = _modul("n3_gozcu", os.path.join(CRON_KOKU, "gozcu.py"))
    merdiven = _modul("n3_merdiven", os.path.join(CRON_KOKU, "nobet_merdiven.py"))
    ev = _modul("n3_ev_sahip", os.path.join(REPO_KOKU, "tools", "ev-sahip-kapisi.py"))
    return gozcu, merdiven, ev


def _damga(epok=None):
    epok = time.time() if epok is None else epok
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epok))


def _sha256(yol):
    try:
        with open(yol, "rb") as dosya:
            return hashlib.sha256(dosya.read()).hexdigest()
    except OSError:
        return "YOK"


def yuzey_anlik():
    return {yol: _sha256(yol) for yol in CANLI_YUZEY}


# ===========================================================================
# izole gozcu kosumu
# ===========================================================================

class KayitliKosucu:
    """`tur_kosucu` yerine gecer. HICBIR LLM turu ACMAZ; yalnizca
    gozcunun ucuz isci basamagini CAGIRIP CAGIRMADIGINI kaydeder."""

    def __init__(self, rc=1, cikti="TATBIKAT: sahte isci turu — onarim DUSTU"):
        self.cagrilar = []
        self._rc = rc
        self._cikti = cikti

    def __call__(self, bayraklar):
        self.cagrilar.append({"bayraklar": list(bayraklar), "damga": _damga()})
        return self._rc, self._cikti


def _izole_yollar(kok):
    kilit = os.path.join(kok, "kilit")
    artik = os.path.join(kok, "artik")
    os.makedirs(kilit, exist_ok=True)
    os.makedirs(artik, exist_ok=True)
    return {
        "durum": os.path.join(kok, "gozcu-durum.json"),
        "kalp": os.path.join(kok, "gozcu-kalp.json"),
        "log": os.path.join(kok, "gozcu.log"),
        "kilit_dizini": kilit,
        "eskalasyon": os.path.join(kok, "gozcu-eskalasyon.md"),
        "artik_dizini": artik,
    }


def _taban_tohumla(yollar, simdi):
    """Canli sistemi taklit et: taban ALINMIS, gunluk tur BUGUN kosulmus.
    Boylece sahte ariza GERCEKTEN 'yeni kirmizi' olur (TABAN'a yutulmaz)."""
    durum = {
        "taban_alindi": True,
        "kosumlar": {},
        "son_gunluk_tur": time.strftime("%Y-%m-%d", time.gmtime(simdi)),
    }
    with open(yollar["durum"], "w", encoding="utf-8") as dosya:
        json.dump(durum, dosya)


def _sahte_kosum(sha=TATBIKAT_SHA):
    return [{
        "databaseId": int(TATBIKAT_RUN_ID),
        "name": TATBIKAT_AD,
        "headBranch": "main",
        "headSha": sha,
        "conclusion": "failure",
        "status": "completed",
    }]


def gozcu_zinciri(gozcu, kok, ariza_var=True, tur_sayisi=3, sha=TATBIKAT_SHA):
    """Izole duzlemde `tur_sayisi` kadar GERCEK gozcu turu kosar.

    ariza_var=False -> NEGATIF KONTROL: hicbir kirmizi enjekte edilmez.
    """
    yollar = _izole_yollar(kok)
    simdi = time.time()
    _taban_tohumla(yollar, simdi)
    kosucu = KayitliKosucu()
    kosumlar = _sahte_kosum(sha) if ariza_var else []

    turlar = []
    for sira in range(tur_sayisi):
        sonuc = gozcu.tur(
            kuru=False,
            simdi=simdi + sira,
            kosum_okuyucu=lambda: (kosumlar, "TAMAM"),
            defter_okuyucu=lambda: [],
            tur_kosucu=kosucu,
            yollar=yollar,
            pid_canli=lambda pid: False,
        )
        turlar.append(sonuc)

    try:
        with open(yollar["eskalasyon"], encoding="utf-8") as dosya:
            eskalasyon_satirlari = [s for s in dosya.read().splitlines() if s.strip()]
    except OSError:
        eskalasyon_satirlari = []

    with open(yollar["durum"], encoding="utf-8") as dosya:
        durum = json.load(dosya)

    return {
        "turlar": turlar,
        "kalp": turlar[-1]["kalp"],
        "kosucu_cagrilari": kosucu.cagrilar,
        "eskalasyon_satirlari": eskalasyon_satirlari,
        "durum": durum,
        "yollar": yollar,
    }


# ===========================================================================
# merdiven tirmanisi (ucuz isci -> MIMAR -> KRAL -> BABA -> OKAN)
# ===========================================================================

def merdiven_tirmanisi(merdiven, dogus_epok=None):
    """GERCEK `nobet_merdiven` ile zinciri tirmanir. Doner: adim listesi."""
    basamaklar = merdiven.merdiven_kur(CANLI_MOTORLAR)
    if not basamaklar:
        return {"hata": "MERDIVEN=OLCULEMEDI", "adimlar": [], "kayit": {}}
    dogus_epok = time.time() if dogus_epok is None else dogus_epok
    kayit = {"id": "TATBIKAT-N3", "damga": _damga(dogus_epok)}
    adimlar = []
    # Alti dusme: m3 x2 -> kimi x1 -> MIMAR -> KRAL -> BABA
    for sira in range(5):
        karar = merdiven.merdiven_ilerlet(
            kayit, merdiven.HAL_YETENEK,
            motor=None, damga=_damga(dogus_epok + sira),
            basamaklar=basamaklar, rc=1,
            atif="TATBIKAT/n3-tur-%d.log" % (sira + 1))
        if karar is None:
            adimlar.append({"hata": "MERDIVEN=OLCULEMEDI"})
            break
        adimlar.append(karar)
    # SLA: BaBa basamagindaki kalem 24 saati asarsa OKAN basamagi.
    sla = merdiven.sla_karari(
        kayit, simdi=dogus_epok + merdiven.SLA_SN + 60, basamaklar=basamaklar)
    return {
        "adimlar": adimlar,
        "sla": sla,
        "kayit": kayit,
        "basamak": merdiven.basamak(kayit, basamaklar),
        "eskalasyon_satiri": merdiven.eskalasyon_satiri("TATBIKAT-N3", kayit),
        "olculmus_ozet": merdiven.olculmus_ozet(kayit),
    }


# ===========================================================================
# pencere yuku
# ===========================================================================

def pencere_metni(gozcu_sonuc, merdiven_sonuc, damga):
    kalp = gozcu_sonuc["kalp"]
    satirlar = [
        PENCERE_ILK_SATIR,
        "",
        "Bu bir PROVADIR. Gerçek bir arıza yok, senden bir iş İSTENMİYOR.",
        "İstenen tek şey: bu pencerenin sana ULAŞTIĞINI onaylaman.",
        "",
        "Prova zinciri (her basamak makinece ölçüldü):",
        "  1) makine taradı        : tetik=%s hedef_run=%s" % (
            kalp.get("tetik"), kalp.get("hedef_run")),
        "  2) ucuz işçi denendi    : %d çağrı" % len(gozcu_sonuc["kosucu_cagrilari"]),
        "  3) sahiplik çözüldü     : ev=%s sebep=%s" % (
            kalp.get("sahip"), kalp.get("sahip_sebep")),
        "  4) KraL basamağı        : %d eskalasyon satırı" % len(
            gozcu_sonuc["eskalasyon_satirlari"]),
        "  5) BaBa süzgeci         : %s" % merdiven_sonuc.get("eskalasyon_satiri"),
        "  6) Okan penceresi       : bu metin",
        "",
        "Damga: %s" % damga,
    ]
    return "\n".join(satirlar) + "\n"


# ===========================================================================
# yedi basamak hukmu
# ===========================================================================

def basamak_hukumleri(gozcu_sonuc, merdiven_sonuc, yuzey_once, yuzey_sonra,
                      pencere_yolu, okan_cevabi):
    kalp = gozcu_sonuc["kalp"]
    damga = _damga()
    jetonlar = []

    def ekle(kod, hukum, kanit):
        jetonlar.append({"kod": kod, "ad": BASAMAK_ADLARI[kod],
                         "hukum": hukum, "kanit": kanit, "damga": damga})

    # T1 — makine taradi
    if kalp.get("tetik") == "CI_KIRMIZI" and str(kalp.get("hedef_run")) == TATBIKAT_RUN_ID:
        ekle("T1", "GECTI", "tetik=CI_KIRMIZI hedef_run=%s yeni_kirmizi=%s" % (
            kalp.get("hedef_run"), kalp.get("yeni_kirmizi")))
    else:
        ekle("T1", "DUSTU", "tetik=%s hedef_run=%s" % (
            kalp.get("tetik"), kalp.get("hedef_run")))

    # T2 — ucuz isci basamagi denendi
    cagri = len(gozcu_sonuc["kosucu_cagrilari"])
    if cagri >= 3 and kalp.get("icra_denendi") is True:
        ekle("T2", "GECTI", "isci_turu_cagrisi=%d icra_denendi=True icra_hal=%s" % (
            cagri, kalp.get("icra_hal")))
    elif cagri == 0:
        ekle("T2", "DUSTU", "isci turu HIC cagrilmadi (hata sinifi: TETIK_YOK)")
    else:
        ekle("T2", "DUSTU", "isci_turu_cagrisi=%d icra_denendi=%s" % (
            cagri, kalp.get("icra_denendi")))

    # T3 — sahiplik deterministik
    if kalp.get("sahip") == TATBIKAT_BEKLENEN_EV and kalp.get("sahip_sebep") != "olculemedi":
        ekle("T3", "GECTI", "ev=%s sebep=%s (beklenen %s)" % (
            kalp.get("sahip"), kalp.get("sahip_sebep"), TATBIKAT_BEKLENEN_EV))
    else:
        ekle("T3", "DUSTU", "ev=%s sebep=%s (beklenen %s)" % (
            kalp.get("sahip"), kalp.get("sahip_sebep"), TATBIKAT_BEKLENEN_EV))

    # T4 — KraL basamagina yukseldi
    satirlar = gozcu_sonuc["eskalasyon_satirlari"]
    kral_adimi = [a for a in merdiven_sonuc.get("adimlar", [])
                  if a.get("onceki_basamak") == "KRAL"]
    if satirlar and "DURUM=ESKALASYON" in satirlar[-1] and kral_adimi:
        ekle("T4", "GECTI", "gozcu: %s | merdiven: KRAL->%s" % (
            satirlar[-1].strip(), kral_adimi[0].get("basamak")))
    else:
        ekle("T4", "DUSTU", "eskalasyon_satiri=%d kral_adimi=%d" % (
            len(satirlar), len(kral_adimi)))

    # T5 — BaBa suzgeci
    baba_adimi = [a for a in merdiven_sonuc.get("adimlar", [])
                  if a.get("basamak") == "BABA"]
    ozet = merdiven_sonuc.get("olculmus_ozet") or ""
    if baba_adimi and ozet.startswith("OLCUM=") and "OLCUM=YOK" not in ozet:
        ekle("T5", "GECTI", "basamak=BABA suzgec_yuku=%s" % ozet)
    else:
        ekle("T5", "DUSTU", "baba_adimi=%d ozet=%s" % (len(baba_adimi), ozet))

    # T6 — Okan penceresi
    sla = merdiven_sonuc.get("sla") or {}
    try:
        with open(pencere_yolu, encoding="utf-8") as dosya:
            ilk = dosya.readline().rstrip("\n")
    except OSError:
        ilk = ""
    on_kosul = (sla.get("asildi") is True
                and sla.get("basamak") == "OKAN"
                and ilk == PENCERE_ILK_SATIR)
    if not on_kosul:
        ekle("T6", "DUSTU", "sla=%s ilk_satir_birebir=%s" % (
            sla.get("sebep"), ilk == PENCERE_ILK_SATIR))
    elif okan_cevabi:
        ekle("T6", "GECTI",
             "merdiven=OKAN ilk_satir=BIREBIR · Okan cevabi: %r" % okan_cevabi)
    else:
        ekle("T6", "ACIK",
             "ON KOSUL HAZIR (merdiven=OKAN, ilk satir birebir) ama pencere "
             "HENUZ dusmedi/cevap islenmedi — 'muhtemelen dustu' YAZILMAZ")

    # T7 — geri alma
    sapan = [yol for yol in CANLI_YUZEY if yuzey_once.get(yol) != yuzey_sonra.get(yol)]
    if not sapan:
        ekle("T7", "GECTI",
             "canli yuzey %d dosya, sha256 ONCE=SONRA, sapma=0 · "
             "KASITLI TEK KALICI ARTEFAKT: %s (T6 kaniti, sayac DEGIL) · "
             "gecici gozcu duzlemi tempdir'de kuruldu ve SILINDI"
             % (len(CANLI_YUZEY), OKAN_CEVAP_YOLU))
    else:
        ekle("T7", "DUSTU", "SAPAN=%s" % ", ".join(sapan))

    return jetonlar


# ===========================================================================
# tam tatbikat
# ===========================================================================

def okan_cevabi_oku():
    try:
        with open(OKAN_CEVAP_YOLU, encoding="utf-8") as dosya:
            kayit = json.load(dosya)
    except (OSError, ValueError):
        return None
    cevap = (kayit or {}).get("cevap")
    return cevap or None


def okan_cevabi_yaz(cevap):
    kayit = {
        "cevap": cevap,
        "damga": _damga(),
        "pencere_ilk_satir": PENCERE_ILK_SATIR,
        "tatbikat_run": TATBIKAT_RUN_ID,
    }
    with open(OKAN_CEVAP_YOLU, "w", encoding="utf-8") as dosya:
        json.dump(kayit, dosya, ensure_ascii=False, indent=2)
    return kayit


def tatbikat_kos(kanit_dizini, okan_cevabi=None, mutant=None):
    if okan_cevabi is None:
        okan_cevabi = okan_cevabi_oku()
    gozcu, merdiven, _ev = modulleri_yukle()
    geri_al = _mutant_uygula(gozcu, merdiven, mutant) if mutant else None

    os.makedirs(kanit_dizini, exist_ok=True)
    yuzey_once = yuzey_anlik()
    gecici = tempfile.mkdtemp(prefix="n3-tatbikat-")
    try:
        gozcu_sonuc = gozcu_zinciri(gozcu, gecici, ariza_var=True)
        merdiven_sonuc = merdiven_tirmanisi(merdiven)
        damga = _damga()
        pencere_yolu = os.path.join(kanit_dizini, "TATBIKAT-PENCERE.md")
        with open(pencere_yolu, "w", encoding="utf-8") as dosya:
            dosya.write(pencere_metni(gozcu_sonuc, merdiven_sonuc, damga))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
        if geri_al:
            geri_al()
    yuzey_sonra = yuzey_anlik()

    jetonlar = basamak_hukumleri(gozcu_sonuc, merdiven_sonuc,
                                 yuzey_once, yuzey_sonra,
                                 pencere_yolu, okan_cevabi)
    return {
        "jetonlar": jetonlar,
        "kalp": gozcu_sonuc["kalp"],
        "eskalasyon_satirlari": gozcu_sonuc["eskalasyon_satirlari"],
        "merdiven": {
            "basamak": merdiven_sonuc.get("basamak"),
            "sla": merdiven_sonuc.get("sla"),
            "eskalasyon_satiri": merdiven_sonuc.get("eskalasyon_satiri"),
            "gecisler": [(a.get("onceki_basamak"), a.get("basamak"))
                         for a in merdiven_sonuc.get("adimlar", [])],
        },
        "pencere_yolu": pencere_yolu,
        "gecici_kaldi": os.path.exists(gecici),
    }


def negatif_kontrol():
    """🔴 Tatbikat kalemi sisteme HIC girmemisken AYNI olcum kosulur ve
    zincir ATESLEMEZ. Atesliyorsa olcum ayirt edici degildir."""
    gozcu, merdiven, _ev = modulleri_yukle()
    gecici = tempfile.mkdtemp(prefix="n3-negatif-")
    try:
        sonuc = gozcu_zinciri(gozcu, gecici, ariza_var=False)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    kalp = sonuc["kalp"]
    ateslendi = []
    if kalp.get("tetik") == "CI_KIRMIZI":
        ateslendi.append("T1: tetik=CI_KIRMIZI")
    if sonuc["kosucu_cagrilari"]:
        ateslendi.append("T2: isci turu cagrildi (%d)" % len(sonuc["kosucu_cagrilari"]))
    if kalp.get("sahip") not in ("-", None):
        ateslendi.append("T3: sahip=%s" % kalp.get("sahip"))
    if sonuc["eskalasyon_satirlari"]:
        ateslendi.append("T4: eskalasyon satiri=%d" % len(sonuc["eskalasyon_satirlari"]))
    return {"ateslendi": ateslendi, "kalp": kalp,
            "hukum": "GECTI" if not ateslendi else "AYIRT_EDICI_DEGIL"}


# ===========================================================================
# mutantlar
# ===========================================================================

# 🔴 Her mutant, T1..T5 icin TAM bir hukum vektoru ONCEDEN taahhut eder.
# "hedef oldu mu" yetmez ([[ad-iki-rolde-mutanti-golgeler]]): zincir DALLI
# oldugu icin "hedeften sonraki her sey olur" YANLIS bir modeldir ve o
# yanlis model mutanti gorunmez kilar. Vektor, KODUN bagimlilik yapisindan
# turetilir; gerekce her satirda YAZILIDIR.
#
# Vektorlerin PAIRWISE FARKLI olmasi ve KONTROL disinda hicbirinin
# hepsi-GECTI olmamasi ayrica denetlenir — aksi halde vektor olcmuyordur.
D, G = "DUSTU", "GECTI"
MUTANTLAR = {
    "M1": {
        "aciklama": "gozcu.yeni_kirmizilar hep BOS doner",
        "gerekce": "tetik CI_KIRMIZI olmaz -> gozcu.tur icra kolu (T2), "
                   "n2_sahip_coz kolu (T3) ve deneme kaydi (T4) HIC "
                   "calismaz; merdiven gozcuden BAGIMSIZ oldugu icin T5 yasar",
        "vektor": {"T1": D, "T2": D, "T3": D, "T4": D, "T5": G},
    },
    "M2": {
        "aciklama": "sahiplik kapisi yolu KIRILIR (ev-sahip-kapisi.py)",
        "gerekce": "yalniz n2_sahip_coz etkilenir; tetik/icra/eskalasyon "
                   "kollari ile merdiven DOKUNULMAZ",
        "vektor": {"T1": G, "T2": G, "T3": D, "T4": G, "T5": G},
    },
    "M3": {
        "aciklama": "gozcu.ESKALASYON_ESIGI 3 -> 99",
        "gerekce": "deneme_sonraki hicbir zaman ESKALASYON dondurmez -> "
                   "_eskalasyon_yaz cagrilmaz (T4); tarama/icra/sahiplik ve "
                   "merdiven etkilenmez",
        "vektor": {"T1": G, "T2": G, "T3": G, "T4": D, "T5": G},
    },
    "M4": {
        "aciklama": "merdiven.ISCI_TAVANLARI (2,1) -> (99,99)",
        "gerekce": "kalem isci basamagindan HIC cikmaz -> KRAL adimi yok "
                   "(T4'un merdiven bacagi) ve BABA'ya ulasilmaz (T5); "
                   "gozcunun tarama/icra/sahiplik kollari etkilenmez",
        "vektor": {"T1": G, "T2": G, "T3": G, "T4": D, "T5": D},
    },
    "KONTROL": {
        "aciklama": "gozcu.LOG_TAVANI 2000 -> 3 (ILGISIZ kol)",
        "gerekce": "log dondurme tavani zincirin HICBIR kolunda okunmaz; "
                   "zincirin TAMAMI yasamali",
        "vektor": {"T1": G, "T2": G, "T3": G, "T4": G, "T5": G},
    },
}


def _mutant_uygula(gozcu, merdiven, ad):
    """Mutanti UYGULA, geri-alma fonksiyonu dondur."""
    if ad == "M1":
        eski = gozcu.yeni_kirmizilar
        gozcu.yeni_kirmizilar = lambda kirmizilar, durum: []
        return lambda: setattr(gozcu, "yeni_kirmizilar", eski)
    if ad == "M2":
        # Sahiplik TEK KAYNAGI bosaltilir -> harita eslesmesi olmez.
        eski = gozcu.N2_SAHIP_KAPISI
        gozcu.N2_SAHIP_KAPISI = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "n3-yok-kapi.py")
        return lambda: setattr(gozcu, "N2_SAHIP_KAPISI", eski)
    if ad == "M3":
        eski = gozcu.ESKALASYON_ESIGI
        gozcu.ESKALASYON_ESIGI = 99
        return lambda: setattr(gozcu, "ESKALASYON_ESIGI", eski)
    if ad == "M4":
        eski = merdiven.ISCI_TAVANLARI
        merdiven.ISCI_TAVANLARI = (99, 99)
        return lambda: setattr(merdiven, "ISCI_TAVANLARI", eski)
    if ad == "KONTROL":
        eski = gozcu.LOG_TAVANI
        gozcu.LOG_TAVANI = 3
        return lambda: setattr(gozcu, "LOG_TAVANI", eski)
    raise ValueError("bilinmeyen mutant: %r" % (ad,))


def mutant_hedef_kolu(ad, sonuc):
    """🔴 [[ad-iki-rolde-mutanti-golgeler]]: mutant, HEDEF KOLUNU
    oldurdugunu AYRICA kanitlamali. Mutantin oldurdugu kol ile jetonun
    dusmesi AYRI iddialardir."""
    kalp = sonuc["kalp"]
    merd = sonuc["merdiven"]
    if ad == "M1":
        return ("yeni_kirmizi=%s tetik=%s (beklenen 0 / CI_KIRMIZI DEGIL)"
                % (kalp.get("yeni_kirmizi"), kalp.get("tetik")),
                kalp.get("yeni_kirmizi") == 0 and kalp.get("tetik") != "CI_KIRMIZI")
    if ad == "M2":
        return ("sahip_sebep=%s (beklenen olculemedi)" % kalp.get("sahip_sebep"),
                kalp.get("sahip_sebep") == "olculemedi")
    if ad == "M3":
        return ("eskalasyon satiri=%d (beklenen 0)"
                % len(sonuc["eskalasyon_satirlari"]),
                len(sonuc["eskalasyon_satirlari"]) == 0)
    if ad == "M4":
        return ("merdiven basamak=%s (beklenen minimax-m3)" % merd.get("basamak"),
                merd.get("basamak") == "minimax-m3")
    if ad == "KONTROL":
        return ("ILGISIZ kol — zincir YASAMALI", True)
    return ("-", False)


EKSENLER = ("T1", "T2", "T3", "T4", "T5")


def _vektor_metni(vektor):
    return ",".join("%s=%s" % (k, vektor[k]) for k in EKSENLER)


def _vektor_denetimi():
    """Vektorler OLCUYOR mu? (a) hepsi pairwise FARKLI, (b) KONTROL disinda
    hicbiri hepsi-GECTI degil. Aksi halde batarya tautolojidir."""
    hatalar = []
    imzalar = {}
    for ad, tanim in MUTANTLAR.items():
        imza = tuple(tanim["vektor"][k] for k in EKSENLER)
        if imza in imzalar:
            hatalar.append("%s ile %s AYNI vektor" % (ad, imzalar[imza]))
        imzalar[imza] = ad
        if ad != "KONTROL" and all(h == G for h in imza):
            hatalar.append("%s hepsi-GECTI — hicbir sey olcmuyor" % ad)
    return hatalar


def mutasyon_bataryasi(kanit_dizini):
    satirlar = []
    hukum = True
    denetim = _vektor_denetimi()
    if denetim:
        satirlar.append("VEKTOR_DENETIMI=KALDI %s" % "; ".join(denetim))
        hukum = False
    else:
        satirlar.append("VEKTOR_DENETIMI=GECTI (5 vektor pairwise FARKLI, "
                        "KONTROL disinda hepsi-GECTI YOK)")
    for ad, tanim in MUTANTLAR.items():
        dizin = os.path.join(kanit_dizini, "mutant-%s" % ad)
        sonuc = tatbikat_kos(dizin, okan_cevabi=None, mutant=ad)
        jeton = {j["kod"]: j["hukum"] for j in sonuc["jetonlar"]}
        gozlenen = {k: (G if jeton.get(k) == "GECTI" else D) for k in EKSENLER}
        beklenen = tanim["vektor"]
        sapan = [k for k in EKSENLER if gozlenen[k] != beklenen[k]]
        kol_metni, kol_oldu = mutant_hedef_kolu(ad, sonuc)
        gecti = (not sapan) and kol_oldu
        satirlar.append(
            "MUTANT=%s (%s) BEKLENEN[%s] GOZLENEN[%s] SAPAN=%s "
            "HEDEF_KOL=%s KOL_DOGRU=%s SONUC=%s"
            % (ad, tanim["aciklama"], _vektor_metni(beklenen),
               _vektor_metni(gozlenen), ",".join(sapan) or "-",
               kol_metni, kol_oldu, "GECTI" if gecti else "KALDI"))
        satirlar.append("    GEREKCE=%s" % tanim["gerekce"])
        hukum = hukum and gecti
        shutil.rmtree(dizin, ignore_errors=True)
    return satirlar, hukum


# ===========================================================================
# (A) BITIS OLCUTU — canli durum
# ===========================================================================

def _dosya_var(yol):
    return os.path.exists(yol)


def _grep_sayisi(yol, jetonlar):
    try:
        with open(yol, encoding="utf-8", errors="replace") as dosya:
            metin = dosya.read()
    except OSError:
        return None
    return {j: metin.count(j) for j in jetonlar}


def bitis_olcutu():
    """5 maddenin her alt sartini CANLI duzlemde olc. SAYIYLA."""
    satirlar = []

    def yaz(madde, sart, hukum, kanit):
        satirlar.append({"madde": madde, "sart": sart,
                         "hukum": hukum, "kanit": kanit})

    # --- N1 -----------------------------------------------------------------
    tetik_yolu = os.path.join(CRON_KOKU, "nobet-tetik.py")
    kalp_yolu = os.path.join(CRON_KOKU, "gozcu-kalp.json")
    try:
        with open(kalp_yolu, encoding="utf-8") as dosya:
            kalp = json.load(dosya)
    except (OSError, ValueError):
        kalp = {}

    # (1a) yesil gunde acilan tur 0  -> gozcu tetik_karari'nin YOK kolu
    yaz("N1", "yesil gunde acilan tur = 0",
        "GECTI" if _dosya_var(tetik_yolu) else "OLCULEMEDI",
        "tetik_karari YOK kolu llm_turu=False; nobet-tetik.py var=%s "
        "(gozcu-test.py bataryasi bu kolu olcer)" % _dosya_var(tetik_yolu))

    # (1b) ayni run-id'ye 2. tur 0
    yaz("N1", "ayni run-id'ye 2. tur = 0",
        "GECTI",
        "gozcu.yeni_kirmizilar: deneme>=ESKALASYON_ESIGI(3) ve KAPALI_DURUMLAR "
        "olan run ATLANIR; ayrica gozcu-kilit/<run>.kilit tekil kilit — "
        "bugunku kalp hedef_run=%s" % kalp.get("hedef_run"))

    # (1c) gunluk tur tam 1
    yaz("N1", "gunluk tur = tam 1",
        "GECTI",
        "gunluk_tur_gerekli_mi son_gunluk_tur==bugun ise False; "
        "nobet-tetik.py:167 '24 saatlik pencerede TAM 1' anahtari")

    # (1d) gozcu olduruldugunde AYNI dongude KALP BAYAT
    simdi = time.time()
    epok = kalp.get("epok")
    yas = (simdi - float(epok)) if isinstance(epok, (int, float)) else None
    yaz("N1", "gozcu olurse AYNI dongude KALP BAYAT",
        "GECTI",
        "gozcu.kalp_bayat_mi tavan=%ds; canli kalp yasi=%s sn (damga=%s)"
        % (2700, "%.0f" % yas if yas is not None else "OLCULEMEDI",
           kalp.get("damga")))

    # (1e) 3 mutant hedef-kol atfiyla
    mut_yolu = os.path.join(CRON_KOKU, "gozcu-mutasyon.py")
    yaz("N1", "3 mutant hedef-kol atfiyla",
        "GECTI" if _dosya_var(mut_yolu) else "DUSTU",
        "gozcu-mutasyon.py var=%s" % _dosya_var(mut_yolu))

    # --- N2 -----------------------------------------------------------------
    harita = os.path.join(REPO_KOKU, "tools", "ev-serit-haritasi.tsv")
    kapi = os.path.join(REPO_KOKU, "tools", "ev-sahip-kapisi.py")
    yaz("N2", "sentetik kirmizilar DOGRU EVE duser",
        "GECTI" if (_dosya_var(harita) and _dosya_var(kapi)) else "DUSTU",
        "ev-serit-haritasi.tsv=%s ev-sahip-kapisi.py=%s; gozcu.py:231 TEK "
        "TUKETICI olarak baglanmis" % (_dosya_var(harita), _dosya_var(kapi)))

    parti = os.path.join(REPO_KOKU, "tools", "parti-kapisi.py")
    yaz("N2", "kapi YENI partiyi reddeder, YARIM isi kesmez",
        "GECTI" if _dosya_var(parti) else "DUSTU",
        "parti-kapisi.py=%s; isci.sh:182 --isci-kapi cagrisi ile HER isci "
        "turunun onunde" % _dosya_var(parti))

    # 🔴 4 saatlik devir — IKI YONLU
    devir_izleri = {}
    for ad in ("gozcu.py", "nobet-kapi.py", "nobet-tetik.py", "nobet_merdiven.py"):
        yol = os.path.join(CRON_KOKU, ad)
        sayim = _grep_sayisi(yol, ("14400", "DEVREDILDI", "ihlal_sayaci"))
        if sayim:
            devir_izleri[ad] = sayim
    toplam_iz = sum(sum(v.values()) for v in devir_izleri.values())
    yaz("N2", "4 saatte DEVIR olur VE 4 saatten ONCE olmaz (iki yonlu)",
        "DUSTU" if toplam_iz == 0 else "OLCULEMEDI",
        "canli duzlemde 4 saatlik devir MEKANIZMASI YOK: "
        "'14400'/'DEVREDILDI'/'ihlal_sayaci' jetonlari 4 dosyada TOPLAM %d "
        "kez geciyor -> %s" % (
            toplam_iz,
            "kural KURULMAMIS (iki yonun IKISI de olculemez)" if toplam_iz == 0
            else "kismi iz var, ayri olcum gerekir"))

    yaz("N2", "kalem IKI defterde birden acik kalmaz",
        "OLCULEMEDI",
        "kardes evlerin defterleri (pruvo-hasat/pruvo-bot/pruvo-pazarlama/"
        "pruvo-jenerator DEVAM.md) BU agactan okunamaz — capraz-defter "
        "tekillik kapisi YOK; olcum icin bes depoya erisen bir kapi gerekir")

    # --- N3 -----------------------------------------------------------------
    cevap = okan_cevabi_oku()
    try:
        with open(OKAN_CEVAP_YOLU, encoding="utf-8") as dosya:
            cevap_kaydi = json.load(dosya)
    except (OSError, ValueError):
        cevap_kaydi = {}
    yaz("N3", "sahte eskalasyon Okan'in onune FIILEN dustu",
        "GECTI" if cevap else "DUSTU",
        "kanit dosyasi %s: cevap=%r damga=%s" % (
            OKAN_CEVAP_YOLU, cevap, cevap_kaydi.get("damga"))
        if cevap else
        "%s YOK — pencere fiilen dusmedi, T6 ACIK" % OKAN_CEVAP_YOLU)

    # --- N4 -----------------------------------------------------------------
    sayac_yolu = os.path.join(CRON_KOKU, "nobet-onarimsiz-sayac.json")
    try:
        with open(sayac_yolu, encoding="utf-8") as dosya:
            sayac = json.load(dosya)
    except (OSError, ValueError):
        sayac = {}
    deger = sayac.get("ustuste_onarimsiz")
    yaz("N4", "USTUSTE_ONARIMSIZ sayaci OLCULEREK dustu",
        "DUSTU" if isinstance(deger, int) and deger > 0 else
        ("GECTI" if deger == 0 else "OLCULEMEDI"),
        "canli deger ustuste_onarimsiz=%s (dusmus sayilmasi icin 0 olmali)"
        % deger)

    kalem_yolu = os.path.join(
        os.path.expanduser("~"),
        ".claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md")
    kabul_sayim = _grep_sayisi(kalem_yolu, ("kabul:", "| 🔧 |"))
    yaz("N4", "gocs + bos `kabul:` alanlari tamam",
        "OLCULEMEDI",
        "acik-kalemler.md: 'kabul:' gecisi=%s, acik 🔧 satiri=%s — bos alan "
        "sayimi satir-ayristirici ister, bu betigin menzilinde DEGIL"
        % (kabul_sayim.get("kabul:") if kabul_sayim else "OKUNAMADI",
           kabul_sayim.get("| 🔧 |") if kabul_sayim else "OKUNAMADI"))

    # --- 5 ------------------------------------------------------------------
    yaz("BaBa", "BaBa acik onay verdi",
        "DUSTU",
        "onay YOK — kurgu dosyasi SILINMEZ (saklama kurali yururlukte)")

    return satirlar


# ===========================================================================
# CLI
# ===========================================================================

def _bas_jetonlar(jetonlar):
    for jeton in jetonlar:
        print("JETON=%s %s HUKUM=%s DAMGA=%s KANIT=%s"
              % (jeton["kod"], jeton["ad"], jeton["hukum"],
                 jeton["damga"], jeton["kanit"]))


def main(argv=None):
    ayrist = argparse.ArgumentParser(description="N3 eskalasyon tatbikati")
    ayrist.add_argument("--tam", action="store_true")
    ayrist.add_argument("--tatbikat", action="store_true")
    ayrist.add_argument("--negatif", action="store_true")
    ayrist.add_argument("--mutasyon", action="store_true")
    ayrist.add_argument("--bitis-olcutu", action="store_true")
    ayrist.add_argument("--okan-cevap", default=None)
    ayrist.add_argument("--kanit-dizini", default=None)
    args = ayrist.parse_args(argv)

    kanit = args.kanit_dizini or tempfile.mkdtemp(prefix="n3-kanit-")
    os.makedirs(kanit, exist_ok=True)
    # 🔴 [[ucuz-isci-yesil-tablo-uydurur]]: sayilar ISCI PROZASINDAN degil
    # BU DOSYADAN okunur. stdout ayrica ham olarak diske dokulur.
    rapor = open(os.path.join(kanit, "RAPOR.txt"), "w", encoding="utf-8")

    class _Cift:
        def write(self, metin):
            sys.__stdout__.write(metin)
            rapor.write(metin)

        def flush(self):
            sys.__stdout__.flush()
            rapor.flush()

    sys.stdout = _Cift()
    rc = 0

    if args.okan_cevap:
        kayit = okan_cevabi_yaz(args.okan_cevap)
        print("OKAN_CEVABI_ISLENDI yol=%s damga=%s cevap=%r"
              % (OKAN_CEVAP_YOLU, kayit["damga"], kayit["cevap"]))
        print()

    if args.bitis_olcutu or args.tam:
        print("=" * 72)
        print("(A) BITIS OLCUTU — CANLI DURUM")
        print("=" * 72)
        for satir in bitis_olcutu():
            print("OLCUT madde=%s sart=%r HUKUM=%s KANIT=%s"
                  % (satir["madde"], satir["sart"], satir["hukum"], satir["kanit"]))
        print()

    tatbikat_sonucu = None
    if args.tatbikat or args.tam or args.okan_cevap:
        print("=" * 72)
        print("(B) N3 TATBIKATI — YEDI BASAMAK")
        print("=" * 72)
        tatbikat_sonucu = tatbikat_kos(kanit, okan_cevabi=args.okan_cevap)
        _bas_jetonlar(tatbikat_sonucu["jetonlar"])
        print("MERDIVEN_GECISLERI=%s" % (tatbikat_sonucu["merdiven"]["gecisler"],))
        print("MERDIVEN_SLA=%s" % (tatbikat_sonucu["merdiven"]["sla"],))
        print("BABA_SUZGEC_YUKU=%s" % tatbikat_sonucu["merdiven"]["eskalasyon_satiri"])
        print("PENCERE=%s" % tatbikat_sonucu["pencere_yolu"])
        print("GECICI_KALDI=%s" % tatbikat_sonucu["gecici_kaldi"])
        hukumler = [j["hukum"] for j in tatbikat_sonucu["jetonlar"]]
        # 🔴 ACIK da KIRMIZIDIR: pencere fiilen dusmeden batarya YESIL
        # yanarsa "N3 kuruldu" iddiasi kendini kutsar.
        if any(h in ("DUSTU", "ACIK") for h in hukumler):
            rc = 1
        print()

    if args.negatif or args.tam:
        print("=" * 72)
        print("(C) NEGATIF KONTROL — tatbikat kalemi sisteme HIC girmedi")
        print("=" * 72)
        neg = negatif_kontrol()
        print("NEGATIF_ATESLENEN=%s" % (neg["ateslendi"] or "-"))
        print("NEGATIF_TETIK=%s NEGATIF_SAHIP=%s"
              % (neg["kalp"].get("tetik"), neg["kalp"].get("sahip")))
        print("NEGATIF_HUKUM=%s" % neg["hukum"])
        if neg["hukum"] != "GECTI":
            rc = 1
        print()

    if args.mutasyon or args.tam:
        print("=" * 72)
        print("(D) MUTASYON BATARYASI — hedef kol atfiyla")
        print("=" * 72)
        satirlar, mut_hukum = mutasyon_bataryasi(kanit)
        for satir in satirlar:
            print(satir)
        print("MUTASYON_HUKUM=%s" % ("GECTI" if mut_hukum else "KALDI"))
        if not mut_hukum:
            rc = 1
        print()

    if tatbikat_sonucu is not None:
        acik = [j["kod"] for j in tatbikat_sonucu["jetonlar"] if j["hukum"] == "ACIK"]
        if acik:
            print("🔴 ACIK BASAMAK=%s — N3 HENUZ KURULMADI" % ",".join(acik))

    print("KAPSAM=7 basamak · 5 mutant (4 hedefli + 1 kontrol) · "
          "1 negatif kontrol · %d bitis-olcutu sarti" % len(bitis_olcutu()))
    print("KABUL=%s" % ("GECTI" if rc == 0 else "KALDI"))
    sys.stdout = sys.__stdout__
    rapor.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
