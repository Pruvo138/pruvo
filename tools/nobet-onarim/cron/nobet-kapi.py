#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRUVO nobet ONARIM BACAGI kapisi (etiket: nobet-onarim-bacagi, 14 Agu 2026).

Tesis: nobet metninde "DUZELT" + "DAGIT" ZATEN yaziliydi, ama bir turu HICBIR SEY
kapatmadan rc=0 + yesil rapor ile bitirmeyi engelleyen bir OLCU yoktu. Son 7 gunde
167 tur kostu, ONARIM_YAPAN=0. Bu dosya o zorlayan olcuyu koyar:

  H1 tur kabul kapisi : ACIK_KALEM>0 VE KAPANAN=0 VE DAGITILAN=0  =>  rc!=0
  H2 fan-out          : bagimsiz kirmizilarin HEPSI ayni turda dagitilir (tavan 4, kalan SIRADA)
  H3 kat secimi       : sessiz-hata sinifi Codex'e; Claude iscisi ASLA acilmaz
  H4 geri-iz          : kalem-id -> etiket -> tur damgasi; rapor yoksa 2 turda DUSTU + yeniden
  H5 motor dusmesi    : 429/kota reddinde yedek motora dusulur; hepsi duserse MOTOR_YOK + rc!=0
  H7 kilit            : onceki tur suruyorsa yeni tur ONCEKI_TUR_SURUYOR ile rc=0 ciker

Kabul testi: python3 /Users/okan/.claude/cron/nobet-kabul-test.py (saf fikstur, ag/cron istemez).
"""

import argparse
import datetime
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time

# K160 dilim-1: TEK KAYNAK kilit modulu. Diske bytecode YAZILMAZ.
_eski_pyc = sys.dont_write_bytecode
sys.dont_write_bytecode = True
import kilit  # noqa: E402
# K257: eskalasyon merdiveni (m3 2 · kimi 1 · MIMAR 1 · KRAL 1 · BABA SLA · OKAN).
import nobet_merdiven as MERDIVEN  # noqa: E402
sys.dont_write_bytecode = _eski_pyc

# --- sabitler -------------------------------------------------------------

# 🔴 W2 (16 Eyl 2026) — YOL KOKU ENV ILE EZILEBILIR, VARSAYILAN DEGISMEDI.
# Sebep: bu iki sabit ELLE YAZILI mutlak yoldu; CI'da (ve herhangi bir izole
# sandbox'ta) `~/.claude/cron` YOKTUR, dolayisiyla bu dosyanin kabul bataryasi
# CI'da KOSAMIYORDU — "sessiz yesil" riskinin kendisi. Env SET EDILMEZSE
# davranis BIREBIR eskisi: uretimde hicbir sey degismez.
CRON_KOKU = os.environ.get("PRUVO_CRON_KOKU") or "/Users/okan/.claude/cron"
EV_KOKU = os.environ.get("PRUVO_EV_KOKU") or "/Users/okan/dev/pruvo"
DEFTER_YOLU = "/Users/okan/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md"
GERI_IZ_YOLU = os.path.join(CRON_KOKU, "nobet-geri-iz.json")
RAPOR_DIZINI = os.path.join(CRON_KOKU, "nobet-raporlar")
SPEC_DIZINI = os.path.join(CRON_KOKU, "nobet-specler")
KILIT_YOLU = os.path.join(CRON_KOKU, "nobet-tur.kilit")
NOBET_LOGU = os.path.join(CRON_KOKU, "ci-nobeti.log")
GOREV_YOLU = os.path.join(CRON_KOKU, "ci-nobeti-gorev.md")
ISCI_SH = os.path.join(CRON_KOKU, "isci.sh")
ONARIMSIZ_SAYAC_YOLU = os.path.join(CRON_KOKU, "nobet-onarimsiz-sayac.json")
ATLANAN_SAYAC_YOLU = os.path.join(CRON_KOKU, "nobet-atlanan-sayac.json")
KARANTINA_YOLU = os.path.join(CRON_KOKU, ".motor-karantina")
KARANTINA_OMUR_SN = 6 * 3600   # 15 Agu 2026: 6 saat karantina, sure dolunca geri gelir

# 🔴🔴 26 Agu 2026 — OKAN EMRI (kutu: "NOBET OTOMATIK-ONARIM KOLU DONDURULDU";
# onarim artik GUNLUK TAMIRCI CIPI'nde). KAPSAM BIREBIR EMIRDEN, GENISLETILMEDI:
#   DURAN : otomatik isci DAGITIM kolu (asagidaki `kalem_dagit` dongusu) +
#           hatta yeni kurulum/batarya turu (yeni B-kalemi ACILMAZ).
#   KALAN : gozcu · deterministik kapi · eskalasyon kaydi · BILDIRIM — bu
#           dosyada o kollarin TEK SATIRI DEGISMEDI (regresyon kabulu ④).
# Emir "mevcut kurulum SOKULMEZ — bayrakla pasiflestir" diyor: hicbir kol
# silinmedi, yalniz bayrakla ATLANIR. Bayrak KALDIRILINCA kol yeniden
# dagitmayi DENER — yani yuklem GERCEKTEN bayraktir (mutant D2 bunu olcer).
DONDURMA_BAYRAK_YOLU = os.environ.get("PRUVO_NOBET_DONDURMA_BAYRAK") or os.path.join(
    CRON_KOKU, "nobet-dondurma.json")


# 🔴 K341 E4: dondurma KAC GUNDUR duruyor. Esik asilinca Okan'a ESKALE edilir.
# Bu kol eskalasyon kanalini SUSTURMAZ, DOGRULTUR: eskiden her turda anlamsiz
# `USTUSTE_ONARIMSIZ=154` gidiyordu; artik gercek karar sorusu gidiyor.
DONDURMA_ESKALASYON_GUN = 1


def dondurma_seviyesi(yol=None, simdi=None, env=None):
    """(gun: int|None, sebep: str) — dondurma KAC GUNDUR duruyor.

    🔴 SEVIYE, sayacin KENARINDAN degil BAYRAGIN KENDI damgasindan okunur:
    araya giren saglikli bir tur bu degeri SIFIRLAYAMAZ
    ([[saglikli-kosum-sayaci-sifirlar-kronik-ariza-birikmez]]).
    Damga yoksa/bozuksa None doner -> cagri yeri FAIL-CLOSED eskale eder;
    "olculemedi" sessiz sifira DUSMEZ.
    """
    donduruldu, karar_sebep = dondurma_karari(yol=yol, env=env)
    if not donduruldu:
        return (None, "DONMUS_DEGIL:%s" % karar_sebep)
    yol = yol or DONDURMA_BAYRAK_YOLU
    try:
        with open(yol, encoding="utf-8") as dosya:
            veri = json.load(dosya)
        damga = str((veri or {}).get("damga") or "")
    except (OSError, ValueError):
        return (None, "BAYRAK_OKUNAMADI")
    if not damga:
        return (None, "DAMGA_YOK")
    try:
        baslangic = datetime.datetime.strptime(damga[:10], "%Y-%m-%d").date()
    except ValueError:
        return (None, "DAMGA_BOZUK:%s" % damga[:16])
    # 🔴 `utcnow()` DEGIL: canli gozcu `/opt/homebrew/bin/python3` **3.14.6**
    # ile kosuyor ve nobet-kapi'yi `sys.executable` ile cagiriyor; orada
    # `utcnow()` HER TURDA `DeprecationWarning` basar (olculdu; 3.9.6'da
    # basmiyor — kabuk yesili canli davranisi ANLATMAZ,
    # [[patha-sorulan-ikili-cron-da-yok]] ailesi). Ikame timezone-aware'dir;
    # `.date()` iki tarafta da ayni gunu verir.
    bugun = (simdi or datetime.datetime.now(datetime.timezone.utc)).date()
    return (max(0, (bugun - baslangic).days), "DAMGA=%s" % damga[:10])


def dondurma_karari(yol=None, env=None):
    """(donduruldu: bool, sebep: str) — DAGITIM kolunun TEK KAYNAGI.

    Oncelik: env ezmesi (YALNIZ kabul testi/mutant) -> bayrak dosyasi -> DONMUS DEGIL.

    🔴 Bayrak YOKSA hukum "DONMUS DEGIL"dir. Emir "bayrakla pasiflestir" diyor,
    yani bayrak YUKLEMDIR: yoklugu eski davranisi geri getirmelidir, yoksa
    "bayrak yuzunden durdu" iddiasi KANITSIZ kalir (mutant D2 tam bunu olcer).
    Bozuk bayrak sessiz gecmez — sebep dizgesi loga TASINIR.
    """
    env = os.environ if env is None else env
    ezme = env.get("PRUVO_NOBET_DONDURMA")
    if ezme is not None:
        ezme = str(ezme).strip()
        if ezme in ("", "0", "kapali", "KAPALI", "hayir", "HAYIR"):
            return (False, "ENV_KAPALI")
        return (True, "ENV_ACIK")
    yol = yol or DONDURMA_BAYRAK_YOLU
    try:
        with open(yol, encoding="utf-8") as dosya:
            veri = json.load(dosya)
    except FileNotFoundError:
        return (False, "BAYRAK_YOK")
    except (OSError, ValueError) as hata:
        return (False, "BAYRAK_BOZUK_%s" % type(hata).__name__)
    if not isinstance(veri, dict) or not veri.get("dagitim_donduruldu"):
        return (False, "BAYRAK_PASIF")
    return (True, str(veri.get("sebep") or "BAYRAK_ACIK"))

# K263 CANLI KABLOLAMA — savunma katmani: nobet-kapi da nobet_devir modulunu
# okur ve devir kararini KENDI tur ciktisina yazar. gozcudeki n2_devir_kararlari
# asil mekanizma; burasi ek bir cagri yeri kanitidir (>=3 dosya + iki yollu).
NOBET_DEVIR_YOLU = os.path.join(CRON_KOKU, "nobet_devir.py")

# Kok defter tur gunlugu degildir: tur gunlugu ci-nobeti.log'a yazilir; deftere
# yalniz DURUM DEGISIKLIGI tek satir duser. Tavan asilirsa TUR duser ama HICBIR
# COMMIT BLOKLANMAZ; bu olcu kapi commit akisina dokunmaz.
KOK_DEFTER_YOLU = os.path.join(EV_KOKU, "DEVAM.md")
DEFTER_BUYUME_TAVANI = 3
FANOUT_TAVANI = 4          # H2: es zamanli isci tavani (kota freni)
DUSME_TUR_ESIGI = 2        # H4: rapor yoksa 2 tur sonra DUSTU
# 🔴 K257 (20 Agu 2026): bu TEK ESIK ARTIK OKUNMUYOR. Merdiven basamak basamak
# `nobet_merdiven` modulunde sayilir (m3 2 · kimi 1 · MIMAR 1 · KRAL 1 · BABA SLA
# · OKAN). Sabit yalniz eski geri-iz kayitlarini okuyan araclar ADIYLA bulsun
# diye birakildi; hicbir uretim kolu onu okumaz — okuyan kol IKINCI BIR ESIK
# demektir ve kabul bataryasi (S7g) bunu ast ekseninde REDDEDER.
ESKALASYON_DAGITIM = 3     # KULLANILMIYOR (K257 oncesi H4 esigi)
KILIT_BAYATLIK_SN = kilit.KILIT_BAYATLIK_SN   # H7: re-export (tek kaynak kilit.py)
TUR_ZAMAN_ASIMI_SN = 1500          # onarim ilerlemiyorsa tur tavani (25 dk)
TUR_ONARIM_ZAMAN_ASIMI_SN = 3000  # onarim ilerliyorsa tur tavani (50 dk)

# --- B7-TUR-IZOLASYONU (20 Agu 2026, KraL-N4B) -----------------------------
# Olculdu (gozcu.log:1993-1999): tur 1500 sn dolup oldurulunce hukme yalnizca
# `SURE_TAVANI_ASILDI=1` yaziliyor; turun kendi ciktisindan HICBIR satir
# gecmiyor ve paylasilan `isci.log` eszamanli turlarla ic ice oldugu icin
# "neden asildi" sorusu logsuz kaliyor. Care: her turun IZOLE dosyasi + tavan
# asiminda o dosyanin SON 50 satirinin hukme eklenmesi.
TUR_CIKTI_DIZINI = os.path.join(CRON_KOKU, "isci-tur-cikti")
TUR_SON_SATIR = 50
# 🔴 Gomulu kanit satiri makine jetonu tasiyabilir (`HUKUM=TEMIZ`,
# `DAGITILAN=7`). `tur_hukmu_ayikla` SONUNCU esleseni aldigi icin ham gomme
# SURE_TAVANI hukmunu EZERDI (fail-open). Gomulu satirda `JETON=` -> `JETON:`.
_MAKINE_JETONU = re.compile(r"(?<![A-Za-z0-9_])([A-Z][A-Z0-9_]{2,})\s*=")
SPEC_OMRU_SN = 24 * 3600   # gecici spec dosyasi omru (disk: iz birakma)
RAPOR_OMRU_SN = 7 * 24 * 3600
OLU_MTIME_ESIK_SN = 900    # K72: isci rapor damgasi bu yastan eskiyse OLU (ilerleme izi yok)

# 🔴 KAT ADLARI MOTOR ADI DEGIL ROL'DUR; motor eslemesi CANLI kumeden TURETILIR.
# Olculdu (17 Agu 2026, KraL): bu tablo `codex` / `deepseek-pro` / `deepseek-flash`
# katlarina is yolluyordu ve UCU DE 15 Agu'da EMEKLI edilmisti; VARSAYILAN kat da
# `deepseek-pro` idi, yani jetonu eslesmeyen HER kalem is-gonderilmeyen bir kuyruga
# dusuyordu. Nobet 76 tur boyunca "dagitti" ama hicbiri kosmadi: ONARIM=0 KAPANAN=0,
# USTUSTE_ONARIMSIZ=63. Bir kati emekli etmek o kata ATANMIS isleri TASIMIYOR
# ([[goc-yolu-eski-kapiya-takilir]] · [[makineyi-olctuk-urunu-olcmedik]]).
#
# TEK KAYNAK: canli/emekli ayrimi ~/dev/pruvo/tools/mimar_kimlik.py'dedir; burada
# IKINCI bir motor listesi TUTULMAZ ([[ikiz-tanim-sessiz-ayrisma]]). Import edilemezse
# FAIL-LOUD: sessizce emekli bir kata dusmek yerine dagitim OLCULEMEDI sayilir.
_kimlik_yolu = os.path.join(EV_KOKU, "tools")
if _kimlik_yolu not in sys.path:
    sys.path.insert(0, _kimlik_yolu)
try:
    from mimar_kimlik import (CANLI_ISCI_MOTORLARI, EMEKLI_ISCI_MOTORLARI,
                              canli_kata_goc)
    KAT_KAYNAGI_OLCULDU = True
    KAT_KAYNAGI_SEBEBI = ""
except Exception as _e:                                            # noqa: BLE001
    CANLI_ISCI_MOTORLARI = ()
    # K260 fail-closed: kume OLCULEMEDIYSE goc kolu HIC atesleyemez — davranis
    # bugunkuyle AYNI kalir, "hepsi emekli" diye TOPLU goc ETTIRILMEZ.
    EMEKLI_ISCI_MOTORLARI = ()
    KAT_KAYNAGI_OLCULDU = False
    KAT_KAYNAGI_SEBEBI = "%s: %s" % (type(_e).__name__, _e)

    def canli_kata_goc(motor):                                     # noqa: D103
        return None

# H3: kat secimi sinif tablosu. Sira ONEMLI: OKAN > sessiz-hata > tarama > mekanik.
KAT_OKAN = "OKAN"
# 🔴 SESSIZ-HATA SINIFI ISCIYE VERILMEZ (CLAUDE.md: kapi/odeme/guvenlik/gizlilik/sema/
# lisans/merge hukmu Claude'da kalir) ve Claude iscisi KraL evinde KOSULSUZ RED. Bu kalem
# bir isci turuna DEGIL, MIMARA eskale edilir. Eskiden bu sinif `codex` katina gidiyordu;
# Codex emekli olunca kalemler orada oldu — sinif artik ADIYLA anilir.
KAT_MIMAR = "MIMAR"
# Uzun baglam / tarama / kapsam cikarma -> birincil canli motor.
KAT_TARAMA = CANLI_ISCI_MOTORLARI[0] if CANLI_ISCI_MOTORLARI else None
# Hacim / mekanik / donusum -> yedek canli motor (yuku bolmek icin).
KAT_MEKANIK = CANLI_ISCI_MOTORLARI[1] if len(CANLI_ISCI_MOTORLARI) > 1 else KAT_TARAMA
VARSAYILAN_KAT = KAT_TARAMA   # suphede BIRINCIL canli kat   # supheda BIRINCIL canli kat

# Geriye donuk adlar (defterde/gecmis izde gecen eski kat adlari CANLI kata goc eder).
KAT_CODEX = KAT_MIMAR          # eski ad; sessiz-hata sinifi artik mimara gider
KAT_PRO = KAT_TARAMA
KAT_FLASH = KAT_MEKANIK

ISCI_YEDEK_ZINCIRI = {
    m: tuple(CANLI_ISCI_MOTORLARI[i:] + CANLI_ISCI_MOTORLARI[:i])
    for i, m in enumerate(CANLI_ISCI_MOTORLARI)
}

# H5: nobet TURUNUN motor zinciri (kota reddinde sirayla dusulur)
# 🔴 K257(e) — 20 Agu 2026, mimar hukmu. Burada ELLE YAZILMIS tekil bir tuple
# duruyordu (`("minimax-m3",)`): hicbir seyden TUREMEDIGI icin SIRA MUTANTI
# bu satiri OLDURMUYORDU — motor sirasi tersine cevrilse bile nobet eski
# motorda kalirdi. Ikinci motor listesi TUTULMAZ ([[ikiz-tanim-sessiz-ayrisma]]).
#
# 🔴 HUKUM DEGISIKLIGI (20 Agu 2026, mimar) — GORUNUR OLSUN DIYE YAZILIYOR:
#   ESKI (16 Agu, BaBa): "cron nobetleri Kimi'ye BAGLANMAZ" -> zincir TEKIL.
#     Gerekce: Kimi haftalik 5s limit, cok-turlu nobet tasariminda baglayici.
#   YENI (20 Agu, mimar K257(e) + Okan'in 20 Agu motor karari): zincir CANLI
#     kumeden TAM turer. BaBa'nin GEREKCESI KALDIRILMADI, BASKA BIR YERDE
#     korunuyor: kimi zincire girer ama ASLA BIRINCI DEGILDIR. Nobet m3'te
#     BASLAR; kimi yalniz kota/karantina reddinde denenir (K257(b) YANA
#     hamlesinin TUR ekseni). Yani "Kimi'ye BAGLANMAK" olmaz, "Kimi'ye
#     DUSMEK" olur — limit ancak m3 dustugunde tuketilir.
#   `nobet-kabul-test.py` vaka 39 bu YENI hukmu olcer (eski vaka SILINMEDI,
#   yerine gecen vaka ESKI GEREKCEYI de ayrica civiler: kimi BIRINCI OLAMAZ).
# Zincir tamamen kotaya girerse `karantina_en_eski` fail-open kolu devrede.
TUR_MOTOR_ZINCIRI = tuple(CANLI_ISCI_MOTORLARI)

OKAN_JETONLARI = (
    "okan kapisi", "okan kapısı", "okan karari", "okan kararı", "okan onayi",
    "okan onayı", "okan yetkisi", "merge kapisi", "merge kapısı", "merge hukmu",
    "merge hükmü", "deploy hukmu", "deploy hükmü", "merge/deploy", "iyzico",
    "uyelik", "üyelik", "wrangler deploy", "ads paneli", "panel erisimi",
    "panel karari",
)
# 🔴 Cıplak "panel" jetonu 14 Agu kuru turunda K54'u (parca adlari listesi, icinde
# "door panel" geciyor) DAGITILMAZ/OKAN kovasina dusurdu — Okan yetkisi jetonu
# YAPISAL olmali: birincil isaret `kime == Okan` sutunudur, metin jetonu daralttildi.
EMEKLI_MOTOR_JETONLARI = (
    "kapi", "kapı", "nobetci", "nöbetçi", "guvenlik", "güvenlik", "secret", "sir ",
    "gizlilik", "sema", "şema", "lisans", "odeme", "ödeme", "fiyat", "mutasyon",
    "fail-open", "fail-closed", "kilit", "flock", "kanca", "hook", "kabul testi",
)
PRO_JETONLARI = (
    "teshis", "teşhis", "kok neden", "kök neden", "tarama", "kor ", "kör ",
    "sessizce", "olcum", "ölçüm", "drift", "ayrisma", "ayrışma", "yaris", "yarış",
)
FLASH_JETONLARI = (
    "tasima", "taşıma", "sayim", "sayım", "log okuma", "temizlik", "arsiv",
    "arşiv", "yeniden yaz", "kopya",
)

# H5: kota/429 reddinin makine izleri. "429" yalniz kelime sinirinda aranir —
# kosum id'leri (31740898072) icinde gecen 429 yanlis pozitif verirdi.
KOTA_DESENLERI = (
    r"\b429\b",
    r"usage limit",
    r"quota exceeded",
    r"rate limit",
    r"insufficient balance",
    r"too many requests",
    r"kota (dolu|asildi|aşıldı)",
)

DURUM_DEGERLERI = ("KAPANDI", "OKAN-KAPISI", "UCUSTA", "ACIK")
ONARIM_DURUMU = "\U0001f527"  # 🔧

# --- KORGOZ_K311_SOZLUK: ACIK KALEM SOZLUGU TEK KAYNAK (27 Agu 2026) -------
# 🔴 OLCULDU (cip KraL-KorGoz-27Agu, taban): `onarim_kalemleri()` YALNIZ 🔧
# sayiyordu; defterin durum kolonunda 🔧 degeri **0 kez** geciyor. Kanonik
# deger `ACIK` ve 11 satir tasiyor. Yani okuyucu, defterde HIC BULUNMAYAN bir
# degeri ariyordu. Sonuc: `ACIK_KALEM=0` x 63 tur / `ACIK_KALEM>=1` x 0,
# `DAGITILAN=0`, `ONARIM=0`, ve `kat_sayaci` bu liste uzerinde dondugu icin
# `kat_okan` 0->1 YAPISAL OLARAK ULASILAMAZ.
#
# Ayni defteri BASKA okuyucular BASKA sozluklerle okuyor (taban olcumu):
#   `tools/parti-borc-kapisi.py::ACIK_DURUMLAR` = {ACIK, UCUSTA, OKAN-KAPISI, 🔧}
#       -> N2B `ACIK=12`
#   ciplak kolon-5 sayimi -> ACIK=11 · UCUSTA=1 · OKAN-KAPISI=2 · BILINMIYOR=3
# Sinif budur: UC okuyucu, UC sozluk.
#
# 🔴 SINIF ONARIMI — kume ELLE YAZILMIS literal DEGIL, kanonik kumenin TAM
# PARTISYONUDUR ve butunluk MODUL YUKLENIRKEN olculur. Yarin deftere yeni bir
# durum degeri eklenirse burasi onu SESSIZCE "kapali" saymaz: ACILISTA patlar.
#
# UCUSTA / OKAN-KAPISI neden ONARILACAK degil (yazili gerekce): ikisi de ACIK
# ama SAHIPLI — UCUSTA'yi bir cip zaten tasiyor, yeniden dagitmak ayni isi iki
# kez actirir; OKAN-KAPISI insan kararidir ve isci katina DAGITILMAZ. Ikisi de
# asagida AYRI kovada sayilir, sessizce dusmez.
ONARILACAK_DURUMLAR = (ONARIM_DURUMU, "ACIK")
SAHIPLI_DURUMLAR = ("UCUSTA", "OKAN-KAPISI")
KAPALI_DURUMLAR_DEFTER = ("KAPANDI",)
BILINMEYEN_DURUM = "BILINMIYOR"


def _partisyon_dogrula():
    """Fail-loud butunluk: kanonik kumenin HER degeri TAM BIR kovada olmali."""
    kovalar = (ONARILACAK_DURUMLAR, SAHIPLI_DURUMLAR, KAPALI_DURUMLAR_DEFTER)
    kanonik = set(DURUM_DEGERLERI) | {ONARIM_DURUMU}
    birlesim = set()
    for kova in kovalar:
        for deger in kova:
            if deger in birlesim:
                raise RuntimeError(
                    "KORGOZ_K311_SOZLUK: %r birden fazla kovada — partisyon DEGIL"
                    % (deger,))
            birlesim.add(deger)
    eksik = kanonik - birlesim
    fazla = birlesim - kanonik
    if eksik or fazla:
        raise RuntimeError(
            "KORGOZ_K311_SOZLUK: durum partisyonu KANONIK KUMEYLE ayristi "
            "(eksik=%s fazla=%s). Deftere yeni durum degeri eklendiyse kovasini "
            "YAZ — sessizce 'kapali' sayilamaz." % (sorted(eksik), sorted(fazla)))


_partisyon_dogrula()
# --- KORGOZ_K311_SOZLUK sonu ----------------------------------------------

# --- C paketi: KABUL KOMUTU ekseni (14 Agu 2026) ---------------------------
# C3: KAPANAN sayaci artik iscinin OZ-RAPORUNDAN degil, KOSULAN komuttan turer.
# Olculmus sinif: ucuz kat isci hic kosmadigi 12 komutun rc=0 tablosunu diskteki
# dosyalardan kurup "olctum" dedi. Beyan kanit degildir.
EL_KITABI_YOLU = os.path.join(CRON_KOKU, "onarim-el-kitabi.md")
KABUL_ZAMAN_ASIMI_SN = 300       # C4: asilirsa OLCULEMEDI (yesil SAYILMAZ)
# C4: kabul komutu YALNIZ bu koklerin ALTINDAN kosulur (realpath sonrasi).
# G1 (14 Agu): beyaz listeye kardes depolar eklendi. Guvenlik GEVSEMEDI: yorumlayici
# kumesi, metakarakter yasagi, realpath `..` kacisi, yasak adlar ve 300 sn tavani aynen
# kaldi; yalniz izinli KOK sayisi 2'den 6'ya cikti. Liste TEK yerde durur (ikinci kopya YASAK).
BEYAZ_LISTE_KOKLERI = (
    "/Users/okan/dev/pruvo",
    "/Users/okan/.claude/cron",
    "/Users/okan/dev/pruvo-hasat",
    "/Users/okan/dev/pruvo-bot",
    "/Users/okan/dev/pruvo-pazarlama",
    "/Users/okan/dev/pruvo-jenerator",
)
KABUL_YORUMLAYICILARI = {"python3": (".py",), "node": (".js", ".mjs", ".cjs")}
# C4: defteri ISCILER yaziyor -> kabul alani GUVENILMEZ GIRDIDIR. Kabuk asla
# kullanilmaz (shell=False), bu karakterlerin BIRI bile varsa komut REDDEDILIR.
METAKARAKTERLER = ";|&><$`(){}[]*?~!#\\'\"\n\r\t\x00"
# C4: adi bunlardan biri olan hicbir yol (yorumlayici ya da arguman) kabul edilmez.
# Son iki ad kapinin KENDI dosyalaridir: kapi kendini cagirip yesil uretemez.
YASAK_ADLAR = ("git", "rm", "mv", "curl", "wget", "chmod", "launchctl", "crontab",
               "nobet-kapi.py", "nobet-kabul-test.py")
# C1: kabul alani MAKINE alanidir. Defterde 11 Ağu'dan beri prose "Kabul: <cumle>"
# metinleri var; alan YALNIZ yorumlayici jetonuyla baslarsa alan sayilir, yoksa BOS
# kabul edilir (C2 gereği kalem yine KAPANAMAZ — prose bir kanit degildir).
KABUL_DESENI = re.compile(
    r"kabul\s*:\s*`?\s*(?P<komut>(?:python3|node)\s+[^|`·]+)", re.IGNORECASE)
RAPOR_KABUL_DESENI = re.compile(r"^[^\n]*?KABUL_KOMUTU\s*=\s*(?P<komut>[^\n]+)$",
                                re.MULTILINE)


# --- saf fonksiyonlar (kabul testi bunlari cagirir) ------------------------

def durum_normalize(hucre):
    """Defterdeki durum hucresini bes kanonik degerden birine indirger.

    Hucre `**KAPANDI (12 Agu)**` gibi sus tasiyabilir; 🔧 her seyin onunde gelir.
    """
    ham = (hucre or "").strip()
    if ONARIM_DURUMU in ham:
        return ONARIM_DURUMU
    sade = ham.replace("*", "").replace("`", "").strip().upper()
    for deger in DURUM_DEGERLERI:
        if sade.startswith(deger):
            return deger
    return "BILINMIYOR"


def kabul_ayikla(hucre):
    """C1: kalem satirinin KANIT hucresindeki `kabul: <komut>` alanini dondurur.

    Alan yoksa "" doner (C2: bos alan = kalem KAPANAMAZ). Defterde komut cogu kez
    ters-tirnak icinde yazilir; tirnaklar burada soyulur — metakarakter denetimi
    komutun KENDISINE uygulanir, susune degil.
    """
    if not hucre:
        return ""
    eslesme = KABUL_DESENI.search(hucre)
    if not eslesme:
        return ""
    ham = eslesme.group("komut").strip()
    ham = ham.strip("`").strip()
    return ham


def rapor_kabul_komutu(metin):
    """C2: iscinin raporundaki `KABUL_KOMUTU=<komut>` satiri (yoksa "")."""
    if not metin:
        return ""
    eslesme = RAPOR_KABUL_DESENI.search(metin)
    if not eslesme:
        return ""
    return eslesme.group("komut").strip().strip("`").strip()


# ==============================================================================
# 🔴 K382 (6 Eyl 2026) — KACIS KORLUGU: KANONIK HUCRE BOLUCU TEK KAYNAKTAN.
# ==============================================================================
# TEK KAYNAK: ~/dev/pruvo/tools/parti-borc-kapisi.py::hucrelere_bol /
# hucreleri_birlestir. Burada IKINCI bir bolucu TANIMLANMAZ
# ([[ikiz-tanim-sessiz-ayrisma]]) — ikizler daima gevsek yone ayrisir.
#
# NEDEN BURASI KRITIK: bu dosya defteri yalniz OKUMAZ, YAZAR da
# (`_satir_guncelle`). Ham `satir.split("|")` ile `parcalar[5]` kacisli bir
# satirda DURUM hucresi DEGILDIR; o hale yazmak `is` hucresinin ortasini
# EZERDI. Kuru kosumla olculdu (6 Eyl): canli defterde 7 satirda `parcalar[5]`
# yanlis hucreyi gosteriyordu.
#
# FAIL-LOUD: bolucu import edilemezse SESSIZCE ham split'e DUSULMEZ — o hal
# tam da kapatilan korlugu geri getirirdi. Yukleme hatasi ADIYLA saklanir ve
# yazma yolu OLCULEMEDI sayilir.
_bolucu_yolu = os.path.join(EV_KOKU, "tools", "parti-borc-kapisi.py")
try:
    import importlib.util as _iu_bol
    _spec_bol = _iu_bol.spec_from_file_location("pruvo_t4_bolucu", _bolucu_yolu)
    _mod_bol = _iu_bol.module_from_spec(_spec_bol)
    _spec_bol.loader.exec_module(_mod_bol)
    hucrelere_bol = _mod_bol.hucrelere_bol
    hucreleri_birlestir = _mod_bol.hucreleri_birlestir
    KalemKimligi = _mod_bol.KalemKimligi
    BOLUCU_OLCULDU = True
    BOLUCU_SEBEBI = ""
except Exception as _eb:                                           # noqa: BLE001
    hucrelere_bol = None
    hucreleri_birlestir = None
    KalemKimligi = None
    BOLUCU_OLCULDU = False
    BOLUCU_SEBEBI = "%s: %r" % (_bolucu_yolu, _eb)


def _kimlik_uygun(kimlik):
    """Kanonik kalem-kimligi kalibi; bolucu yoksa FAIL-LOUD (dar kaliba dusmez)."""
    if not BOLUCU_OLCULDU:
        raise RuntimeError(
            "K382 KIMLIK KALIBI OLCULEMEDI (%s). Dar `^K\\d+$` kalibina "
            "sessizce dusmek `K339-EK` sinifi kalemleri nobet hukmunden "
            "DUSURUR." % BOLUCU_SEBEBI)
    return bool(KalemKimligi.match(kimlik))


def _bol(satir):
    """Kanonik bolucu; yoksa FAIL-LOUD (ham split'e SESSIZCE dusmez)."""
    if not BOLUCU_OLCULDU:
        raise RuntimeError(
            "K382 BOLUCU OLCULEMEDI — defter satiri ayristirilamaz (%s). "
            "Ham `split(\"|\")`e dusmek `\\|` kacisini kaydirir ve YAZMA "
            "yolunda `is` hucresini EZER." % BOLUCU_SEBEBI)
    return hucrelere_bol(satir)


def defter_ayristir(metin):
    """acik-kalemler.md tablo satirlarini kalem sozluklerine cevirir."""
    kalemler = []
    for satir_no, satir in enumerate(metin.split("\n"), 1):
        duz = satir.strip()
        if not duz.startswith("|"):
            continue
        # 🔴 K382 kanonik bolucu. `strip("|")` yerine bas/son bos jeton atilir —
        # kacisli bir satirda `strip("|")` de yanlis yerden kirpardi.
        hucreler = [h.strip() for h in _bol(duz)[1:-1]]
        if len(hucreler) < 5:
            continue
        kimlik = hucreler[0]
        # 🔴 K382 (d): kanonik kimlik kalibi TEK KAYNAKTAN. Dar `^K\d+$`
        # kalibi `K339-EK`/`K329-EK`/`K351-31AGU`/`K320b` kimliklerini
        # GORMUYORDU — o kalemler nobet hukmune HIC girmiyordu.
        if not _kimlik_uygun(kimlik):
            continue
        kimden_kime = hucreler[2]
        kime = kimden_kime.split("→")[-1].strip() if "→" in kimden_kime else ""
        kanit_ham = hucreler[5] if len(hucreler) > 5 else ""
        kalemler.append({
            "id": kimlik,
            "tarih": hucreler[1],
            "kimden_kime": kimden_kime,
            "kime": kime,
            "is": hucreler[3],
            "durum_ham": hucreler[4],
            "durum": durum_normalize(hucreler[4]),
            "kanit_ham": kanit_ham,
            "kabul": kabul_ayikla(kanit_ham),   # C1
            "satir_no": satir_no,
        })
    return kalemler


def kabul_haritasi_kur(kalemler):
    """C1: kalem-id -> kabul komutu (bos olabilir)."""
    return {k["id"]: k.get("kabul", "") for k in kalemler}


def onarim_kalemleri(kalemler):
    """H1/H4 anlaminda ONARILACAK kalem: durumu 🔧 ya da ACIK olan satir.

    KORGOZ_K311_SOZLUK (27 Agu 2026): eskiden YALNIZ 🔧 sayilirdi ve defterde
    o degeri tasiyan durum hucresi HIC YOKTU -> liste her turda BOS donuyordu.
    Kume artik `ONARILACAK_DURUMLAR` partisyonundan gelir; literal TEKRAR
    EDILMEZ.
    """
    return [k for k in kalemler if k["durum"] in ONARILACAK_DURUMLAR]


def sahipli_kalemler(kalemler):
    """ACIK ama DAGITILMAZ olanlar (UCUSTA = bir cip tasiyor · OKAN-KAPISI)."""
    return [k for k in kalemler if k["durum"] in SAHIPLI_DURUMLAR]


def bilinmeyen_durumlu_kalemler(kalemler):
    """KORGOZ_K311_SOZLUK — hicbir kovaya girmeyen satirlar SESSIZ DUSMEZ.

    `durum_normalize()` tanimadigi hucreye "BILINMIYOR" der ve o satir bugune
    kadar HER okuyucunun gozunden kaciyordu (taban olcumu: 3 satir). Sayisi
    artik her turda basilir; gorunmeyen kuyruk olusmaz.
    """
    bilinen = set(ONARILACAK_DURUMLAR) | set(SAHIPLI_DURUMLAR) | set(
        KAPALI_DURUMLAR_DEFTER)
    return [k for k in kalemler if k["durum"] not in bilinen]


def _jeton_var(metin, jetonlar):
    for jeton in jetonlar:
        if jeton in metin:
            return True
    return False


# --- K260 KAT KOVASI (24 Agu 2026, KraL-K260KatSec) ------------------------
# 🔴 Sinif jetonu CIPLAK ALT-DIZE olarak arandiginda kalem, jetonun ANLAMI
# yuzunden degil GECTIGI YER yuzunden insan katina kilitleniyordu. Olculdu:
#   K77  -> "kapi" YALNIZ `[[kapi-ozeti-hukumden-ayrisir]]` link slug'inda
#   K262 -> "kapi" YALNIZ `nobet-kapi.py` DOSYA ADI icinde
#   K108 -> "kabul testi" YALNIZ tirnakli CI ADIM ADI icinde
# Ayni sinif bu dosyada BIR KEZ daha olculmustu (bkz. satir 169-171: cıplak
# "panel" jetonu K54'u OKAN kovasina dusurdu). IKINCI vaka -> SINIF cozumu:
# sinif jetonlari yalniz SERBEST METINDE aranir.
#
# 🔴 MASKELEME OKAN KAPISINA UYGULANMAZ: insan kapisi DARALTILMAZ (fail-closed).
_MASKE_HAFIZA_LINKI = re.compile(r"\[\[[^\]]*\]\]")
_MASKE_KOD_ACIKLIGI = re.compile(r"`[^`]*`")


def _serbest_metin(metin):
    """Sinif jetonlarinin aranacagi metin: link slug'lari + kod acikliklari MASKELI."""
    metin = _MASKE_HAFIZA_LINKI.sub(" ", metin)
    metin = _MASKE_KOD_ACIKLIGI.sub(" ", metin)
    return metin


def _emekli_kat_gocur(kat):
    """H1 (K260): kat adi EMEKLI bir motorsa CANLI kata gocer.

    Insan katlari (MIMAR/OKAN) emekli OLMAZ — kapsam disi.
    Fail-closed: EMEKLI kume BOS ise (olculemedi) hicbir sey gocmez.
    """
    if kat in (KAT_MIMAR, KAT_OKAN):
        return kat
    if not EMEKLI_ISCI_MOTORLARI or kat not in EMEKLI_ISCI_MOTORLARI:
        return kat
    return canli_kata_goc(kat) or (
        CANLI_ISCI_MOTORLARI[0] if CANLI_ISCI_MOTORLARI else kat)


def _emekli_kattan_gocmus(kalem, geri_iz):
    """🔴 K260 HUKUM-1'in YAPISAL yuklemi: kalem EMEKLI bir ISCI katindan CANLI
    kata GOCMUS mu?

    Olculdu (24 Agu 2026, `nobet-geri-iz.json`): bugun MIMAR'a kilitli 11
    kalemin 10'unun kaydi `durum=BAYAT_GOC motor=kimi eski_motor=codex
    dagitim_sayisi=3`. Yani bu kalemler EMEKLI bir motora UC KEZ DAGITILMIS —
    hicbiri hicbir zaman insan kati olmamistir; bugunku MIMAR hukmu yalnizca
    `KAT_CODEX = KAT_MIMAR` TAKMA ADININ artigidir. B4 gocu kaydi CANLI kata
    tasidi ama DAGITIM KARARINI ezmedi (N4B kapanisi: "gocen 15 kaydin 10'u
    kat_sec ile yine MIMAR'a dusup DAGITILMAZ kaliyor") — K260 tam bu kalintidir.

    🔴 FAIL-CLOSED. False doner (kalem MIMAR_KATI_GERCEK'te KALIR) su hallerde:
      · geri-iz VERILMEDI ya da kaydi YOK        -> olcemedigimizi dagitmayiz
      · B4 goc damgasi YOK                       -> emekli kattan gelmemis
      · eski motor EMEKLI kumede DEGIL           -> gerekce emekli-ad DEGIL
      · yeni motor CANLI kumede DEGIL            -> goc tamamlanmamis
      · EMEKLI ya da CANLI kume BOS (olculemedi) -> toplu goc ETTIRILMEZ
    Insan katindan gocmus olamaz: `bayat_eskalasyonlari_gocur` MIMAR/OKAN
    kayitlarini KAPSAM DISI birakir (B4, kabul-3).
    """
    if geri_iz is None or not EMEKLI_ISCI_MOTORLARI or not CANLI_ISCI_MOTORLARI:
        return False
    kayit = (geri_iz.get("kalemler") or {}).get(kalem.get("id")) or {}
    damga = kayit.get("eskalasyon_bayat") or {}
    if damga.get("eski_motor") not in EMEKLI_ISCI_MOTORLARI:
        return False
    return (kayit.get("motor") or kayit.get("kat")) in CANLI_ISCI_MOTORLARI


def _gocmus_kat(kalem, geri_iz):
    """Gocmus kalemin CANLI kati — B4 zaten sectI, IKINCI secim YAPILMAZ."""
    kayit = (geri_iz.get("kalemler") or {}).get(kalem.get("id")) or {}
    return kayit.get("motor") or kayit.get("kat")


# UC KOVA (H2, K260). Kova `kat_sec`ten ve eskale kumesinden TURER — ikinci
# siniflama TUTULMAZ ([[ikiz-tanim-sessiz-ayrisma]]). Supheli kalem
# MIMAR_KATI_GERCEK'te kalir ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
KOVA_DAGITILABILIR = "DAGITILABILIR"
KOVA_MIMAR_GERCEK = "MIMAR_KATI_GERCEK"
KOVA_OKAN = "OKAN_KAPISI"
KOVA_ADLARI = (KOVA_DAGITILABILIR, KOVA_MIMAR_GERCEK, KOVA_OKAN)


def kat_sec(kalem, geri_iz=None):
    """H3 sinif tablosu. Claude iscisi HICBIR kosulda donmez.

    `geri_iz` VERILIRSE hukum-1 uygulanir: emekli isci katindan CANLI kata
    gocmus kalem MIMAR'a KILITLENMEZ, B4'un sectigi CANLI kata gider.
    Verilmezse davranis K260 oncesiyle AYNIDIR (geriye donuk uyum).
    """
    ham = ((kalem.get("is") or "") + " " + (kalem.get("durum_ham") or "")).lower()
    kime = (kalem.get("kime") or "").lower()
    # OKAN kapisi TAM METIN uzerinde olculur (maskeleme UYGULANMAZ) ve hukum-1
    # gocunden ONCE gelir: Okan kalemi HICBIR kolda dagitima girmez (hukum 3).
    if kime.startswith("okan") or _jeton_var(ham, OKAN_JETONLARI):
        return KAT_OKAN
    metin = _serbest_metin(ham)
    if _jeton_var(metin, EMEKLI_MOTOR_JETONLARI):
        # 🔴 HUKUM-1: emekli-kat artigi MIMAR hukmunu EZEMEZ.
        if _emekli_kattan_gocmus(kalem, geri_iz):
            return _gocmus_kat(kalem, geri_iz)
        return KAT_CODEX
    if _jeton_var(metin, PRO_JETONLARI):
        return _emekli_kat_gocur(KAT_PRO)
    if _jeton_var(metin, FLASH_JETONLARI):
        return _emekli_kat_gocur(KAT_FLASH)
    return _emekli_kat_gocur(VARSAYILAN_KAT)


def kova_sec(kalem, geri_iz=None):
    """K260: kalem UC KOVADAN hangisinde? FAIL-CLOSED.

    · Kat kaynagi OLCULEMEDIYSE kalem DAGITILABILIR SAYILMAZ.
    · `kime=Okan` / Okan jetonu -> OKAN_KAPISI (hukum 3, DOKUNULMAZ).
    · Insan kapisinda bekleyen (eskale/merdiven) kalem -> OKAN_KAPISI.
    · Gercek mimar kati (sessiz-hata sinifi) -> MIMAR_KATI_GERCEK.
    · Kalani -> DAGITILABILIR.
    """
    if not KAT_KAYNAGI_OLCULDU:
        return KOVA_MIMAR_GERCEK
    kat = kat_sec(kalem, geri_iz)
    if kat == KAT_OKAN:
        return KOVA_OKAN
    if geri_iz is not None and kalem.get("id") in set(eskale_kalemler(geri_iz, {kalem.get("id")})):
        return KOVA_OKAN
    if kat == KAT_MIMAR:
        return KOVA_MIMAR_GERCEK
    return KOVA_DAGITILABILIR


def kova_dagilimi(kalemler, geri_iz=None):
    """K260: kova -> kalem id listesi. Toplam = len(kalemler) (KAYIP YOK)."""
    dagilim = {ad: [] for ad in KOVA_ADLARI}
    for kalem in kalemler:
        dagilim[kova_sec(kalem, geri_iz)].append(kalem.get("id"))
    return dagilim




def ucusta_kalemler(geri_iz):
    return [k for k, v in geri_iz.get("kalemler", {}).items()
            if v.get("durum") == "DAGITILDI"]


# --- B4-ESKALASYON-BAYAT (20 Agu 2026, KraL-N4B) ---------------------------
# Eskalasyonu URETEN motor emekliyse, kalem insan kapisinda DEGIL HICBIR
# kapida bekler. Olculdu: K55 durum=ESKALASYON motor=deepseek-pro (emekli
# 15 Agu 2026), dagitim_sayisi=3, rapor YOK, 105+ turdur DAGITILAN=0.
BAYAT_GOC_DURUMU = "BAYAT_GOC"


def eskalasyon_bayat_mi(kayit, canli_motorlar=None):
    """B4: bu eskalasyon EMEKLI bir motordan mi dogdu?

    Fail-closed: canli kume BOS ise "bayat" DEMEYIZ (olcemedigimiz seyi
    bayat ilan etmek toplu goc demektir — kabul-3).
    Goc BIR KEZ olur: `eskalasyon_bayat` damgasi varsa bir daha ates almaz.
    Insan katlari (MIMAR/OKAN) emekli olmaz, onlar KAPSAM DISIDIR.
    """
    canli = CANLI_ISCI_MOTORLARI if canli_motorlar is None else tuple(canli_motorlar)
    if not canli:
        return False
    kayit = kayit or {}
    if kayit.get("durum") != "ESKALASYON":
        return False
    if kayit.get("eskalasyon_bayat"):
        return False
    motor = kayit.get("motor") or kayit.get("kat") or ""
    if motor in (KAT_MIMAR, KAT_OKAN):
        return False
    return motor not in canli


def bayat_eskalasyonlari_gocur(geri_iz, damga=None, canli_motorlar=None):
    """B4: BAYAT eskalasyonlari CANLI kata gocurur. Doner: (satirlar, sayi).

    🔴 Sayaca DOKUNMAZ (`tur_sayacini_kaydet` CAGRILMAZ), `dagitim_sayisi`
    AYNEN kalir, `gozcu-eskalasyon.md` dosyasina DOKUNULMAZ.
    Yeni durum BAYAT_GOC'tur: `eskale_kalemler` artik onu DISLAMAZ, kalem aday
    havuzuna BIR KEZ geri girer. Canli katta yeniden 3 kez duserse durum yine
    ESKALASYON olur ve motor CANLI oldugu icin bir daha GOCMEZ (sonsuz dongu YOK).
    """
    canli = CANLI_ISCI_MOTORLARI if canli_motorlar is None else tuple(canli_motorlar)
    if not canli:
        return ["ESKALASYON_BAYAT=OLCULEMEDI sebep=canli_motor_kumesi_bos"], 0
    damga = damga or _damga()
    satirlar = []
    sayi = 0
    for kalem_id, kayit in sorted((geri_iz.get("kalemler") or {}).items()):
        if not eskalasyon_bayat_mi(kayit, canli):
            continue
        eski_motor = kayit.get("motor") or kayit.get("kat") or "-"
        yeni_kat = canli_kata_goc(eski_motor) or canli[0]
        kayit["eskalasyon_bayat"] = {
            "eski_motor": eski_motor,
            "eski_durum": kayit.get("durum"),
            "damga": damga,
        }
        kayit["durum"] = BAYAT_GOC_DURUMU
        kayit["motor"] = yeni_kat
        kayit["kat"] = yeni_kat
        satirlar.append("ESKALASYON_BAYAT kalem=%s eski_motor=%s yeni_kat=%s"
                        % (kalem_id, eski_motor, yeni_kat))
        sayi += 1
    return satirlar, sayi


def eskale_kalemler(geri_iz, acik_idler=None):
    """H4: Okan'a eskale edilmis kalem YENIDEN dagitilmaz — insan kapisindadir.

    K86/K55 vakasi: defterde KAPANDI/DEVREDILDI olduktan sonra geri-izdeki
    ESKALASYON damgasi bayat kalabilir; kova ACIK tanimini kalem durumundan turetir.
    """
    # K257: insan kapisindaki kalemlere ek olarak ARAC_KUSURU (kapi reddi,
    # sahibine dondu) ve KOTA_BEKLEMEDE (tum canli motorlar kotada) kalemleri
    # de bu turda DAGITILMAZ. Liste merdiven modulunden TURER, burada IKINCI
    # bir kopya tutulmaz.
    return [k for k, v in geri_iz.get("kalemler", {}).items()
            if v.get("durum") in MERDIVEN.DAGITILMAZ_DURUMLAR
            and (acik_idler is None or k in acik_idler)]


def fanout_plani(kalemler, geri_iz, tavan=FANOUT_TAVANI, yeniden=(), haric=()):
    """H2: bagimsiz kirmizilarin HEPSI ayni turda dagitilir; tavan asilirsa SIRADA.

    yeniden: H4'te DUSTU isaretlenmis, yeniden dagitilacak kalem id'leri (oncelikli).
    haric: BU TURDA kapanmis kalemler — defter satiri henuz 🔧 gorunse de yeniden
      dagitilmaz (yoksa kapanan kalem ayni turda bir isciyi daha yakardi).
    """
    ucusta = set(ucusta_kalemler(geri_iz))
    acik_idler = {k["id"] for k in kalemler}
    eskale = set(eskale_kalemler(geri_iz, acik_idler))
    okan = [k for k in kalemler if kat_sec(k, geri_iz) == KAT_OKAN]
    mimar = [k for k in kalemler if kat_sec(k, geri_iz) == KAT_MIMAR]
    okan_idler = set(k["id"] for k in okan)
    mimar_idler = set(k["id"] for k in mimar)
    adaylar = [k for k in kalemler
               if k["id"] not in okan_idler and k["id"] not in mimar_idler
               and k["id"] not in ucusta
               and k["id"] not in eskale and k["id"] not in set(haric)]
    # yeniden dagitilacaklar basa alinir
    adaylar.sort(key=lambda k: (0 if k["id"] in set(yeniden) else 1, k["satir_no"]))
    bos_yer = max(0, tavan - len(ucusta))
    dagitilacak = adaylar[:bos_yer]
    sirada = adaylar[bos_yer:]
    return {
        "dagitilacak": dagitilacak,
        "sirada": sirada,
        "okan": okan,
        "mimar": mimar,
        "ucusta": sorted(ucusta),
        "eskale": sorted(eskale),
    }


def _kok_altinda(yol, koklar):
    for kok in koklar:
        gercek_kok = os.path.realpath(kok)
        if yol.startswith(gercek_kok + os.sep):
            return True
    return False


def kabul_komutu_dogrula(komut, koklar=None):
    """C4: guvenilmez defter metnini KOSULABILIR argv'ye cevirir ya da REDDEDER.

    Doner: (argv | None, sebep). argv None ise komut KOSULMAZ — cagiran taraf
    hicbir kosulda yedek/kabuk yolu denemez (bu maddenin ihlali = uzaktan kod
    calistirma).
    """
    koklar = koklar if koklar is not None else BEYAZ_LISTE_KOKLERI
    ham = (komut or "").strip()
    if not ham:
        return None, "KOMUT_BOS"
    for karakter in METAKARAKTERLER:
        if karakter in ham:
            return None, "METAKARAKTER(%s)" % repr(karakter)
    parcalar = ham.split()
    if len(parcalar) < 2:
        return None, "BICIM"
    yorumlayici, yazili_yol = parcalar[0], parcalar[1]
    uzantilar = KABUL_YORUMLAYICILARI.get(yorumlayici)
    if not uzantilar:
        return None, "YORUMLAYICI_DISI(%s)" % yorumlayici
    if not yazili_yol.startswith("/"):
        return None, "MUTLAK_YOL_DEGIL"
    if not yazili_yol.endswith(uzantilar):
        return None, "UZANTI"
    # `..` ile disari cikis: link cozulur, kok denetimi COZULMUS yol uzerinde yapilir.
    gercek = os.path.realpath(yazili_yol)
    if not _kok_altinda(gercek, koklar):
        return None, "BEYAZ_LISTE_DISI"
    for parca in list(parcalar) + [gercek]:
        if parca in YASAK_ADLAR or os.path.basename(parca) in YASAK_ADLAR:
            return None, "YASAK_AD(%s)" % os.path.basename(parca)
    return [yorumlayici, gercek] + parcalar[2:], "GECERLI"


def _kabul_gercek_kosucu(argv, zaman_asimi):
    """C4: kabuk YOK — argv listesi dogrudan exec edilir (shell=False)."""
    sonuc = subprocess.run(
        argv, shell=False, cwd=EV_KOKU, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, timeout=zaman_asimi,
    )
    return sonuc.returncode


def kabul_komutu_kos(komut, zaman_asimi=None, kosucu=None, koklar=None):
    """C3+C4: kabul komutunu OLCER. Doner: {hukum, rc, sebep, argv}.

    hukum: KOMUT_REDDEDILDI (kosulmadi) · OLCULEMEDI (zaman asimi/kosulamadi) ·
           KOSTU_YESIL (rc=0) · KOSTU_KIRMIZI (rc!=0).
    """
    zaman_asimi = KABUL_ZAMAN_ASIMI_SN if zaman_asimi is None else zaman_asimi
    argv, sebep = kabul_komutu_dogrula(komut, koklar)
    if argv is None:
        return {"hukum": "KOMUT_REDDEDILDI", "rc": None, "sebep": sebep,
                "argv": None, "komut": komut}
    kosucu = kosucu or _kabul_gercek_kosucu
    try:
        rc = kosucu(argv, zaman_asimi)
    except subprocess.TimeoutExpired:
        # Zaman asimi YESIL DEGILDIR: olculemeyen eksen kapanmaz.
        return {"hukum": "OLCULEMEDI", "rc": None, "sebep": "ZAMAN_ASIMI(%ds)" % zaman_asimi,
                "argv": argv, "komut": komut}
    except OSError as hata:
        return {"hukum": "OLCULEMEDI", "rc": None, "sebep": "KOSULAMADI(%s)" % hata,
                "argv": argv, "komut": komut}
    if rc == 0:
        return {"hukum": "KOSTU_YESIL", "rc": 0, "sebep": "rc=0", "argv": argv,
                "komut": komut}
    return {"hukum": "KOSTU_KIRMIZI", "rc": rc, "sebep": "rc=%s" % rc, "argv": argv,
            "komut": komut}


def kalem_kabul_hukmu(rapor_metni, defter_kabul, kabul_kosucu=None):
    """C2+C3: bir kalemin kapanip kapanmadigina KOSULAN komutla karar verir.

    Doner: {hukum, kabul, rc, sebep, yazilacak_kabul}
      KAPANDI              — rapor KAPANDI + kabul komutu var + rc=0
      BEYAN_VAR_KANIT_YOK  — rapor KAPANDI ama komut rc!=0 (kalem ACIK kalir)
      KABUL_KOMUTU_YOK     — C2: kabul alani BOS, kalem en fazla DAGITILDI
      KOMUT_REDDEDILDI     — C4 kisitlarindan biri gecmedi (kosulmadi)
      OLCULEMEDI           — zaman asimi / komut kosulamadi
    """
    kabul_kosucu = kabul_kosucu or (lambda komut: kabul_komutu_kos(komut))
    rapor_kabul = rapor_kabul_komutu(rapor_metni)
    defter_kabul = (defter_kabul or "").strip()
    # C2: rapordan gelen komut YALNIZ BOS alani doldurur, DOLU alani EZMEZ.
    kabul = defter_kabul or rapor_kabul
    yazilacak = rapor_kabul if (not defter_kabul and rapor_kabul) else ""
    if not kabul:
        return {"hukum": "KABUL_KOMUTU_YOK", "kabul": "", "rc": None,
                "sebep": "C2 kabul alani BOS", "yazilacak_kabul": ""}
    olcum = kabul_kosucu(kabul)
    esleme = {"KOSTU_YESIL": "KAPANDI", "KOSTU_KIRMIZI": "BEYAN_VAR_KANIT_YOK"}
    hukum = esleme.get(olcum.get("hukum"), olcum.get("hukum"))
    return {"hukum": hukum, "kabul": kabul, "rc": olcum.get("rc"),
            "sebep": olcum.get("sebep"), "yazilacak_kabul": yazilacak}


def rapor_kapandi_mi(metin):
    """H4: raporda HUKUM=KAPANDI varsa kalem kapandi sayilir."""
    if not metin:
        return False
    return re.search(r"HUKUM\s*=\s*KAPANDI", metin) is not None


def _kalemi_dusur(kayit, kimlik, sonuc, hal=None, metin=None, rc=1,
                 varsayilan=None):
    """K257 MERDIVENI: dusmenin SINIFI yonu belirler (dort hal, UC ayri yon).

    Eskiden TEK esik vardi ("3. dagitimda Okan") ve HER dusme ayni kovaya
    giriyordu: kota reddi de, kapi reddi de, sure tavani da "yetenek yok"
    sayiliyordu. K236 aylarca "motor yetersiz" sanildi cunku KAPI_REDDI kolu
    YOKTU. Artik:
      KOTA         -> YANA     (m3 -> kimi), sayac ARTMAZ
      YETENEK      -> YUKARI   , sayac ARTAR
      BITMEYEN_TUR -> B7 KOVASI, ayni tur YENIDEN KURULMAZ
      KAPI_REDDI   -> SAHIBINE , NE YANA NE YUKARI (arac kusuru)
    """
    sinif = hal or MERDIVEN.hal_coz(
        rc, metin, kota_reddi_mi,
        varsayilan=varsayilan or MERDIVEN.HAL_YETENEK)
    if sinif is None:                       # rc=0 gelirse fail-closed
        sinif = MERDIVEN.HAL_YETENEK
    karar = MERDIVEN.merdiven_ilerlet(
        kayit, sinif, motor=kayit.get("motor"), damga=_damga(),
        canli_motorlar=CANLI_ISCI_MOTORLARI, rc=rc,
        atif=kayit.get("rapor_yolu"), metin=metin)
    if karar is None:
        # Canli kume BOS: kalem HICBIR yone tasinmaz (fail-closed).
        kayit["durum"] = "MERDIVEN_OLCULEMEDI"
        sonuc.setdefault("merdiven_olculemedi", []).append(kimlik)
        sonuc.setdefault("merdiven_satirlari", []).append(
            MERDIVEN.merdiven_satiri(kimlik, None))
        return None
    sonuc.setdefault("merdiven_satirlari", []).append(
        MERDIVEN.merdiven_satiri(kimlik, karar))
    durum = karar["durum"]
    if durum == MERDIVEN.DURUM_ESKALASYON:
        sonuc["eskalasyon"].append(kimlik)
        # (c) Ust kata giden is OLCULMUSU de goturur.
        sonuc.setdefault("eskalasyon_satirlari", []).append(
            MERDIVEN.eskalasyon_satiri(kimlik, kayit))
    elif durum == MERDIVEN.DURUM_ARAC_KUSURU:
        sonuc.setdefault("arac_kusuru", []).append(kimlik)
    elif durum == MERDIVEN.DURUM_BITMEYEN_TUR:
        sonuc.setdefault("bitmeyen_tur", []).append(kimlik)
    elif durum == MERDIVEN.DURUM_KOTA_BEKLEMEDE:
        sonuc.setdefault("kota_beklemede", []).append(kimlik)
    else:
        sonuc["dusen"].append(kimlik)
    return karar


def isci_olu_mu(kayit, tur_no, simdi=None, pid_canli=None, mtime_esik=None):
    """K72: DAGITILDI iscinin bu turda OLU sayilip sayilmayacagina karar verir.

    Iki iz: (1) surec PID'i canli degil + onceki turda dagitilmis => olmus;
    (2) rapor damgasi VAR ama bayat (mtime esigi asilmis) => asilmis/olmus.
    Bu turda yeni dagitilan (yas<=0) isci henuz olculemez (UCUSTA kalir).
    """
    simdi = simdi if simdi is not None else time.time()
    pid_canli = pid_canli or _pid_canli
    mtime_esik = OLU_MTIME_ESIK_SN if mtime_esik is None else mtime_esik
    yas = tur_no - int(kayit.get("tur", tur_no))
    if yas <= 0:
        return False
    pid = int(kayit.get("pid") or 0)
    if pid and not pid_canli(pid):
        return True
    rapor_yolu = kayit.get("rapor_yolu")
    if rapor_yolu:
        try:
            if simdi - os.path.getmtime(rapor_yolu) > mtime_esik:
                return True
        except OSError:
            pass
    return False


def geri_iz_degerlendir(geri_iz, tur_no, rapor_okuyucu, kabul_haritasi=None,
                        kabul_kosucu=None, pid_canli=None, simdi=None):
    """H4+C3: dagitilan kalemlerin akibetini olcer.

    rapor_okuyucu(yol) -> metin ya da None (rapor yok).
    kabul_haritasi: kalem-id -> defterdeki kabul komutu (C1).
    kabul_kosucu(komut) -> kabul_komutu_kos ciktisi (test/kuru tur enjekte eder).

    C3: `rapor HUKUM=KAPANDI` TEK BASINA yetmez — kalem ancak kabul komutu
    KOSULUP rc=0 alindiysa KAPANAN sayacina girer.
    """
    kabul_haritasi = kabul_haritasi or {}
    sonuc = {"kapanan": [], "dusen": [], "eskalasyon": [], "ucusta": [],
             "olu": [], "beyan_var_kanit_yok": [], "kabul_yok": [],
             "reddedilen": [], "olculemedi": [], "kabul_yazilacak": {},
             "kabul_olcumleri": {}}
    for kimlik, kayit in sorted(geri_iz.get("kalemler", {}).items()):
        if kayit.get("durum") != "DAGITILDI":
            continue
        metin = rapor_okuyucu(kayit.get("rapor_yolu"))
        yas = tur_no - int(kayit.get("tur", tur_no))
        if rapor_kapandi_mi(metin):
            hukum = kalem_kabul_hukmu(metin, kabul_haritasi.get(kimlik, ""),
                                      kabul_kosucu)
            kayit["kabul_komutu"] = hukum["kabul"]
            kayit["kabul_hukum"] = hukum["hukum"]
            kayit["kabul_rc"] = hukum["rc"]
            kayit["kabul_sebep"] = hukum["sebep"]
            # Olcum sonucu AYRICA olcum sozlugunde tutulur: kalem ayni turda
            # yeniden dagitilirsa kayit yenilenir ve kanit rapordan SILINIRDI.
            sonuc["kabul_olcumleri"][kimlik] = {
                "kabul": hukum["kabul"], "rc": hukum["rc"],
                "sebep": hukum["sebep"], "hukum": hukum["hukum"]}
            if hukum["yazilacak_kabul"]:
                sonuc["kabul_yazilacak"][kimlik] = hukum["yazilacak_kabul"]
            if hukum["hukum"] == "KAPANDI":
                kayit["durum"] = "KAPANDI"
                kayit["kanit"] = "%s + %s (rc=0)" % (kayit.get("rapor_yolu"),
                                                     hukum["kabul"])
                sonuc["kapanan"].append(kimlik)
                continue
            if hukum["hukum"] == "BEYAN_VAR_KANIT_YOK":
                # C3: beyan var, kanit yok -> kalem ACIK kalir ve YENIDEN dagitilir.
                sonuc["beyan_var_kanit_yok"].append(kimlik)
                # Is GERCEKTEN denendi ve kabul dustu -> varsayilan YETENEK.
                _kalemi_dusur(kayit, kimlik, sonuc, metin=metin,
                              rc=hukum.get("rc") or 1,
                              varsayilan=MERDIVEN.HAL_YETENEK)
                continue
            if hukum["hukum"] == "KOMUT_REDDEDILDI":
                sonuc["reddedilen"].append(kimlik)
                # 🔴 K257(b): kabul komutu C4 kapisinca REDDEDILDI -> komut HIC
                # KOSMADI. Bu bir ARAC KUSURUDUR, yetenek kusuru DEGIL:
                # ne yana ne yukari, sayaca DAHIL DEGIL.
                _kalemi_dusur(
                    kayit, kimlik, sonuc, hal=MERDIVEN.HAL_KAPI_REDDI,
                    metin="kabul-komutu-kapisi sebep=%s" % hukum.get("sebep"),
                    rc=1)
                continue
            if hukum["hukum"] == "KABUL_KOMUTU_YOK":
                # C2: kabul komutu yoksa kalem en fazla DAGITILDI kalir.
                sonuc["kabul_yok"].append(kimlik)
            else:                                   # OLCULEMEDI (+ kuru tur)
                sonuc["olculemedi"].append(kimlik)
        if isci_olu_mu(kayit, tur_no, simdi, pid_canli):
            sonuc["olu"].append(kimlik)
            # Isci basladi ama BITIREMEDI -> B7 kovasi (varsayilan). Metinde
            # kota/kapi izi varsa `hal_coz` onu USTUN tutar.
            _kalemi_dusur(kayit, kimlik, sonuc, metin=metin, rc=1,
                          varsayilan=MERDIVEN.HAL_BITMEYEN_TUR)
            continue
        if yas >= DUSME_TUR_ESIGI:
            _kalemi_dusur(kayit, kimlik, sonuc, metin=metin, rc=1,
                          varsayilan=MERDIVEN.HAL_YETENEK)
        else:
            sonuc["ucusta"].append(kimlik)
    return sonuc


def kota_reddi_mi(cikti, rc):
    """H5: bu dusme bir kota/429 reddi mi?"""
    if rc == 0:
        return False
    duz = (cikti or "").lower()
    for desen in KOTA_DESENLERI:
        if re.search(desen, duz):
            return True
    return False


def motor_zinciri_kos(zincir, kosucu):
    """H5: sirayla motor dener; hepsi duserse MOTOR_YOK + rc!=0.

    kosucu(motor) -> (rc, cikti)
    """
    denemeler = []
    for motor in zincir:
        rc, cikti = kosucu(motor)
        kota = kota_reddi_mi(cikti, rc)
        denemeler.append({
            "motor": motor,
            "rc": rc,
            "sebep": "KOTA" if kota else ("YESIL" if rc == 0 else "HATA"),
        })
        if "SURE_TAVANI_ASILDI=1" in (cikti or ""):
            return {"motor": motor, "rc": 1,
                    "hukum": tur_hukmu_ayikla(cikti) or "SURE_TAVANI",
                    "denemeler": denemeler, "cikti": cikti}
        if rc == 0:
            return {"motor": motor, "rc": 0, "hukum": "MOTOR_KOSTU",
                    "denemeler": denemeler, "cikti": cikti}
    return {"motor": None, "rc": 1, "hukum": "MOTOR_YOK",
            "denemeler": denemeler, "cikti": ""}


def tur_hukmu(acik_kalem, kapanan, dagitilan, tasinan=0, mevcut_hukum=None,
              dondurma_isirdi=False):
    """H1 + 15 Agu supurme kapisi: sessiz yesil bir daha mumkun degil.

    🔴 KOL B1 (27 Agu 2026, KraL-NobetTuru-27Agu) — UCUNCU KOVA.
    OLCULDU: Okan'in 26 Agu DONDURMA emri `dagitilan`i YAPISAL olarak 0'da
    tutuyor; bu kol ise "acik kalem var + hicbir sey dagitilmadi" halini
    KOSULSUZ `ONARIMSIZ_TUR/rc=1` sayiyordu. Sonuc: 27 Agu 00:07-12:07 arasi
    13 ardisik saat `BITIS rc=1` -- hicbiri gercek ariza degil, hepsi EMRIN
    KENDISI. "Emirle dagitmadi" ile "dagitacakti, DAGITAMADI" AYNI KOVAYA
    giremez ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).

    `DONDURMA_ISIRDI=1` satiri 26 Agu'dan beri rapora YAZILIYORDU; uretimde
    OKUYAN YOKTU (`yazan=1 okuyan=0` -> [[kapinin-menzili-cagri-yeridir]]).
    `dondurma_isirdi` parametresi o satirin TUKETICISIDIR.

    🔴 GEVSETME DEGIL: bayrak ISIRMADIYSA (`ADAY=0` -- ortada dagitilacak
    kalem zaten yoktu) eski hukum AYNEN durur ve tur KIRMIZI kapanir. Kabul
    bataryasinin KONTROL vakasi tam olarak budur.
    """
    onarim = kapanan + dagitilan
    if acik_kalem > 0 and kapanan == 0 and dagitilan == 0:
        if dondurma_isirdi:
            rc, hukum = 0, "DAGITIM_DONDURULDU"
        else:
            rc, hukum = 1, "ONARIMSIZ_TUR"
    elif acik_kalem == 0:
        rc, hukum = 0, "TEMIZ"
    else:
        rc, hukum = 0, "ONARIM_ILERLIYOR"
    # Model turunun olctugu ARIZA hukmu kapinin daha sonraki eksenlerince EZILMEZ.
    if (mevcut_hukum or "").startswith("ARIZA"):
        return 1, mevcut_hukum
    # ONARIMSIZ_SUPURME, ONARIMSIZ_TUR'dan agirdir; gercek bir ARIZA/agir hukum
    # varsa onu EZMEZ. Bilinmeyen hukumler de hafif varsayilmaz (fail-closed).
    # 🔴 DAGITIM_DONDURULDU da HAFIFTIR: dondurma emri, "onarmadan alarm
    # kanalini susturma" (ONARIMSIZ_SUPURME) kapisini KALDIRMAZ -- o kapi
    # dondurma altinda da ISIRMALIDIR.
    hafif_hukumler = {"ONARIMSIZ_TUR", "TEMIZ", "ONARIM_ILERLIYOR",
                      "DAGITIM_DONDURULDU"}
    if onarim == 0 and tasinan > 0 and hukum in hafif_hukumler:
        return 1, "ONARIMSIZ_SUPURME"
    return rc, hukum


def tur_olcumu_ayikla(metin, alan):
    """Model turu ciktisindaki son `ALAN=<dogal sayi>` olcumunu dondurur."""
    desen = re.compile(r"(?<![A-Za-z0-9_])%s\s*=\s*(\d+)" % re.escape(alan))
    eslesmeler = desen.findall(metin or "")
    return int(eslesmeler[-1]) if eslesmeler else 0


def tur_hukmu_ayikla(metin):
    """Model turu ciktisindaki son makine `HUKUM=` degerini dondurur."""
    eslesmeler = re.findall(r"(?<![A-Za-z0-9_])HUKUM\s*=\s*([A-Z][A-Z0-9_+-]*)",
                            metin or "")
    return eslesmeler[-1] if eslesmeler else None


def kilit_karari(icerik, simdi, pid_canli_mi):
    """H7: adaptör — govde kilit.py'de (TEK KAYNAK, K160 dilim-1)."""
    return kilit.karar(icerik, simdi, pid_canli_mi)


# --- yan etkili yardimcilar ------------------------------------------------

def _pid_canli(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def geri_iz_oku(yol=None):
    # Yollar CAGRI aninda cozulur: varsayilan argumana baglanirsa fikstur izolasyonu
    # (ve her turlu yol degisimi) SESSIZCE etkisiz kalir.
    yol = yol or GERI_IZ_YOLU
    try:
        with open(yol, encoding="utf-8") as dosya:
            veri = json.load(dosya)
    except (FileNotFoundError, ValueError):
        veri = {}
    if not isinstance(veri, dict):
        veri = {}
    veri.setdefault("tur_no", 0)
    veri.setdefault("kalemler", {})
    return veri


def geri_iz_yaz(veri, yol=None):
    yol = yol or GERI_IZ_YOLU
    dizin = os.path.dirname(yol)
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=".nobet-geri-iz.")
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
        except FileNotFoundError:
            pass
        raise


def ustuste_onarimsiz_oku(yol=None):
    """Ard arda ONARIM=0 tur sayisini bozuk/eksik durumda sifirdan baslatir."""
    yol = yol or ONARIMSIZ_SAYAC_YOLU
    try:
        with open(yol, encoding="utf-8") as dosya:
            veri = json.load(dosya)
        sayac = int(veri.get("ustuste_onarimsiz", 0))
        return max(0, sayac)
    except (FileNotFoundError, ValueError, TypeError, AttributeError):
        return 0


def ustuste_onarimsiz_sonraki(onceki, onarim, kova_bos=False, dondu=False):
    """Ilk ONARIM>0 turunda sifirlar; kova bos ise sifirlar; aksi halde ard arda sayaci bir artirir.

    🔴 D-sayac (25 Agu 2026): "yapacak is yoktu" (kova bos + eskalasyon yok)
    ile "onarim DENENDI ve DUSTU" hali AYRIDIR. Bos kova sayaci ANLAMSIZ artirir
    ve yanlis eskalasyon uretirdi (olculdu: bir tur OKAN_KAPISI=0 basip USTUSTE_
    ONARIMSIZ=82 kaldi).

    🔴 E-sayac (28 Agu 2026, K341): UCUNCU sifirlayici — `dondu`. Okan'in
    DONDURMA emri dagitim kolunu YAPISAL olarak kapatinca `onarim` daima 0
    kalir; eski yuklem bunu "onarim DENENDI ve DUSTU" sayip her turda +1
    atiyordu (olculdu: 89 -> 129 -> 154, uc gun MONOTON, HIC dusmedi).
    "Emirle yapmadi" ile "yapacakti, YAPAMADI" ayni kovaya GIREMEZ
    ([[emir-ariza-kovasina-duserse-hat-kendi-kendine-kirmizi-yanar]]).
    `kova_bos` ile AYRI parametre: "kova bostu" ile "kova doluydu ama emir
    kapatti" AYRI iddialardir ve kayitta ayri okunur.
    """
    if kova_bos or dondu or onarim > 0:
        return 0
    return onceki + 1


def ustuste_onarimsiz_guncelle(onarim, yol=None, kova_bos=False, dondu=False,
                               hal=None, sebep=None):
    """Ard arda onarimsiz sayacini atomik yazar ve yeni degeri dondurur.

    🔴 E3 (K341): dosya artik SAYIYI DEGIL KAYDI tasir — `son_hal`/`son_iso`/
    `son_sebep`. Onceden diskte tek sayi vardi ve "sayac neden bu degerde"
    sorusu dosyadan CEVAPLANAMIYORDU. `ustuste_onarimsiz_oku` yalniz
    `ustuste_onarimsiz` alanini okur, yani geriye donuk uyum KORUNUR.
    🔴 `ilk_*` alani BILEREK YOK: sifirlama yolunda duran bir "ilk gorulme"
    alani kendi kendini yalanlar
    ([[saglikli-kosum-sayaci-sifirlar-kronik-ariza-birikmez]]); seviye sorusu
    `dondurma_seviyesi()` ile BAYRAGIN damgasindan okunur.
    """
    yol = yol or ONARIMSIZ_SAYAC_YOLU
    yeni = ustuste_onarimsiz_sonraki(ustuste_onarimsiz_oku(yol), onarim,
                                     kova_bos=kova_bos, dondu=dondu)
    dizin = os.path.dirname(yol)
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=".nobet-onarimsiz-sayac.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as dosya:
            json.dump({"ustuste_onarimsiz": yeni,
                       "son_hal": hal or "-",
                       "son_iso": _damga(),
                       "son_sebep": sebep or "-"},
                      dosya, ensure_ascii=False,
                      indent=2, sort_keys=True)
            dosya.write("\n")
            dosya.flush()
            os.fsync(dosya.fileno())
        os.replace(gecici, yol)
    except BaseException:
        try:
            os.unlink(gecici)
        except FileNotFoundError:
            pass
        raise
    return yeni


def atlanan_ardisik_oku(yol=None):
    """Ard arda kilit atlamalarini bozuk/eksik durumda sifirdan baslatir."""
    yol = yol or ATLANAN_SAYAC_YOLU
    try:
        with open(yol, encoding="utf-8") as dosya:
            veri = json.load(dosya)
        sayac = int(veri.get("atlanan_ardisik", 0))
        return max(0, sayac)
    except (FileNotFoundError, ValueError, TypeError, AttributeError):
        return 0


def atlanan_ardisik_sonraki(onceki, atlandi):
    """Atlamada artirir; normal kosan ilk turda sifirlar."""
    yeni = onceki + 1 if atlandi else 0
    return yeni


def atlanan_ardisik_guncelle(atlandi, yol=None):
    """Kilit atlama sayacini atomik yazar ve yeni degeri dondurur."""
    yol = yol or ATLANAN_SAYAC_YOLU
    yeni = atlanan_ardisik_sonraki(atlanan_ardisik_oku(yol), atlandi)
    dizin = os.path.dirname(yol)
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=".nobet-atlanan-sayac.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as dosya:
            json.dump({"atlanan_ardisik": yeni}, dosya, ensure_ascii=False,
                      indent=2, sort_keys=True)
            dosya.write("\n")
            dosya.flush()
            os.fsync(dosya.fileno())
        os.replace(gecici, yol)
    except BaseException:
        try:
            os.unlink(gecici)
        except FileNotFoundError:
            pass
        raise
    return yeni


def atlama_satiri(hukum, atlanan_ardisik, damga=None):
    """H7 atlamasini sayac ve ikinci atlamadan itibaren eskalasyonla raporlar."""
    alanlar = ["===", damga or _damga(), "NOBET ATLANDI", "HUKUM=%s" % hukum]
    if atlanan_ardisik >= 2:
        alanlar.append("ESKALASYON=OKAN")
    alanlar.append("ATLANAN_ARDISIK=%d" % atlanan_ardisik)
    alanlar.append("===")
    return " ".join(alanlar)


def defter_oku(yol=None):
    yol = yol or DEFTER_YOLU
    with open(yol, encoding="utf-8") as dosya:
        return defter_ayristir(dosya.read())


def _satir_guncelle(satir, durum=None, kabul=None):
    """C5: tek tablo satirinda YALNIZ durum hucresini ve BOS kabul alanini yazar.

    Satir ham haliyle bolunur ve DOKUNULMAYAN hucreler bayt bayt korunur —
    yeniden bicimlendirme, komsu hucrenin sessizce degismesi demektir.
    """
    # 🔴 K382: KANONIK bolucu. Ham split, `\|` tasiyan bir satirda `parcalar[5]`i
    # DURUM degil `is` hucresinin ortasi yapar — oraya yazmak kalemin metnini
    # EZER (kuru kosumla olculdu: canli defterde 7 satir).
    parcalar = _bol(satir)
    if len(parcalar) < 7:            # | id | tarih | kimden→kime | is | durum | kanit |
        return satir, False
    degisti = False
    if durum:
        parcalar[5] = " %s " % durum
        degisti = True
    if kabul and not kabul_ayikla(parcalar[6]):
        parcalar[6] = "%s · kabul: `%s` " % (parcalar[6].rstrip(), kabul)
        degisti = True
    # 🔴 YAZMA: `"|".join` DEGIL — kacis geri konmazsa hucre icindeki `|`
    # ayiriciya doner ve satir bir sonraki okumada KALICI olarak parcalanir.
    return hucreleri_birlestir(parcalar), degisti


def _defter_donustur(metin, guncellemeler):
    """Doner: (yeni_metin, yazilan_satir_sayisi). Satir SILMEZ, satir EKLEMEZ."""
    yazilan = 0
    satirlar = metin.split("\n")
    for indeks, satir in enumerate(satirlar):
        duz = satir.strip()
        if not duz.startswith("|"):
            continue
        hucreler = [h.strip() for h in _bol(duz)[1:-1]]   # 🔴 K382 kanonik bolucu
        if not hucreler or not _kimlik_uygun(hucreler[0]):   # 🔴 K382 (d)
            continue
        istek = guncellemeler.get(hucreler[0])
        if not istek:
            continue
        yeni, degisti = _satir_guncelle(satir, istek.get("durum"), istek.get("kabul"))
        if degisti:
            satirlar[indeks] = yeni
            yazilan += 1
    return "\n".join(satirlar), yazilan


def defter_yaz(guncellemeler, yol=None, donusturucu=None):
    """C5: deftere ATOMIK yazar; satir sayisi degistiyse yazmayi GERI ALIR.

    guncellemeler: {kalem_id: {"durum": "KAPANDI", "kabul": "<komut>"}}
    Doner: {"hukum": ..., "yazilan": n}
    """
    yol = yol or DEFTER_YOLU
    donusturucu = donusturucu or _defter_donustur
    with open(yol, encoding="utf-8") as dosya:
        eski = dosya.read()
    yeni, yazilan = donusturucu(eski, guncellemeler)
    if len(yeni.split("\n")) != len(eski.split("\n")):
        # Defter baska mimarlarin da kaynak dogrusu: satir sayisi oynadiysa
        # yazma HIC yapilmaz (dosya diskte oldugu gibi kalir).
        return {"hukum": "DEFTER_YAZMA=GERI_ALINDI", "yazilan": 0,
                "sebep": "SATIR_SAYISI %d->%d" % (len(eski.split("\n")),
                                                  len(yeni.split("\n")))}
    if yeni == eski:
        return {"hukum": "DEFTER_YAZMA=DEGISIKLIK_YOK", "yazilan": 0}
    dizin = os.path.dirname(os.path.abspath(yol))
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=".acik-kalemler.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as dosya:
            dosya.write(yeni)
            dosya.flush()
            os.fsync(dosya.fileno())
        os.replace(gecici, yol)
    except BaseException:
        try:
            os.unlink(gecici)
        except FileNotFoundError:
            pass
        raise
    return {"hukum": "DEFTER_YAZMA=TAMAM", "yazilan": yazilan}


def el_kitabi_oku(yol=None):
    """C6: onarim el kitabi tablosunu okur (sinif -> arac -> kabul komutu -> kat).

    El kitabi IKINCI BIR DOGRULUK KAYNAGI DEGILDIR: kural tasimaz, YALNIZ
    "hangi sinif hangi araca ve hangi kabul komutuna gider" defteridir.
    """
    yol = yol or EL_KITABI_YOLU
    satirlar = []
    try:
        with open(yol, encoding="utf-8") as dosya:
            metin = dosya.read()
    except FileNotFoundError:
        return satirlar
    for satir in metin.split("\n"):
        duz = satir.strip()
        if not duz.startswith("|"):
            continue
        hucreler = [h.strip().strip("`").strip() for h in duz.strip("|").split("|")]
        if len(hucreler) < 5:
            continue
        if hucreler[0].lower().startswith("sinif") or set(hucreler[0]) <= set("-: "):
            continue
        jetonlar = [j.strip().lower() for j in hucreler[1].split(",") if j.strip()]
        satirlar.append({"sinif": hucreler[0], "jetonlar": jetonlar,
                         "arac": hucreler[2], "kabul": hucreler[3],
                         "kat": hucreler[4]})
    return satirlar


def el_kitabi_kat_uret(yol=None, kuru=True):
    """K316 (27 Agu 2026) — EL KITABININ `kat` SUTUNUNU URETIR (elle YAZILMAZ).

    🔴 OLCULEN KUSUR (K316/V2): `onarim-el-kitabi.md` `kat` sutunu ELLE yazili
    motor adlari tasiyordu. Kat ise TEK KAYNAKTAN turer:
    `~/dev/pruvo/tools/mimar_kimlik.py::CANLI_ISCI_MOTORLARI` -> KAT_TARAMA /
    KAT_MEKANIK -> `kat_sec`. 20 Agu'da Okan sirayi ters cevirince (m3 BIRINCIL)
    elle yazili sutun kaynaktan SESSIZCE ayristi; `nobet-kabul-test.py` vaka 19
    bunu KIRMIZI yakti ama duzeltmenin TEK yolu yine ELLE yazmakti — yani ayni
    ariza bir sonraki motor kararinda BIREBIR geri gelirdi
    ([[ucuncu-tekrar-sinif-kapisi]] · [[ikiz-tanim-sessiz-ayrisma]]).

    COZUM = URETICI + NOBETCI (biri tek basina sinifi KAPATMAZ):
      · URETICI = bu yuklem. `kat` hucresi jetonlardan `kat_sec` ile TURETILIR ve
        dosyaya MAKINE yazar (`--el-kitabi-uret`). Elle yazim gerekmez.
      · NOBETCI = `nobet-kabul-test.py` vaka 19 (sutun == `kat_sec`) + vaka 41
        (uretici idempotent + fiksturdeki ayrismayi ONARIR) + K316 mutant
        bataryasi (tek kaynagin birincili degisince el kitabi kolu KIRMIZI).

    🔴 SUTUN SILINMEZ: silinseydi `CANLI_ISCI_MOTORLARI` degistiginde ayrisabilecek
    bir sey kalmaz, nobetci de olcecek bir sey bulamazdi (kapsam sessizce daralirdi).

    Doner: {"okunan": n, "degisen": m, "yazildi": bool, "fark": [(sinif, eski, yeni)]}
    `kuru=True` iken dosyaya TEK BAYT yazilmaz.
    """
    yol = yol or EL_KITABI_YOLU
    try:
        with open(yol, encoding="utf-8") as dosya:
            metin = dosya.read()
    except FileNotFoundError:
        return {"okunan": 0, "degisen": 0, "yazildi": False, "fark": []}
    satirlar = metin.split("\n")
    okunan = 0
    fark = []
    for indeks, satir in enumerate(satirlar):
        duz = satir.strip()
        if not duz.startswith("|"):
            continue
        hucreler = [h.strip().strip("`").strip() for h in duz.strip("|").split("|")]
        if len(hucreler) < 5:
            continue
        if hucreler[0].lower().startswith("sinif") or set(hucreler[0]) <= set("-: "):
            continue
        jetonlar = [j.strip().lower() for j in hucreler[1].split(",") if j.strip()]
        okunan += 1
        # 🔴 vaka 19'un OLCTUGU YUKLEMIN AYNISI cagrilir; ikinci bir turetim
        # yazilmaz — yoksa ikiz tanim bir kat yukari tasinmis olurdu.
        beklenen = kat_sec({"is": " ".join(jetonlar), "durum_ham": ""})
        if hucreler[4] == beklenen:
            continue
        parcalar = satir.split("|")
        if len(parcalar) < 6:
            continue
        parcalar[5] = " %s " % beklenen
        satirlar[indeks] = "|".join(parcalar)
        fark.append((hucreler[0], hucreler[4], beklenen))
    yazildi = False
    if fark and not kuru:
        gecici = yol + ".k316-tmp"
        with open(gecici, "w", encoding="utf-8") as dosya:
            dosya.write("\n".join(satirlar))
            dosya.flush()
            os.fsync(dosya.fileno())
        os.replace(gecici, yol)
        yazildi = True
    return {"okunan": okunan, "degisen": len(fark), "yazildi": yazildi, "fark": fark}


def el_kitabi_satiri_sec(metin, satirlar):
    """C6: kalem metnine uyan ILK el kitabi satiri (yoksa None)."""
    duz = (metin or "").lower()
    for satir in satirlar:
        for jeton in satir["jetonlar"]:
            if jeton and jeton in duz:
                return satir
    return None


def rapor_oku(yol):
    if not yol:
        return None
    try:
        with open(yol, encoding="utf-8", errors="replace") as dosya:
            return dosya.read()
    except (FileNotFoundError, IsADirectoryError):
        return None


def _damga():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def artik_temizle(simdi=None):
    """Disk kurali: ureten temizler. Bayat spec/rapor dosyalarini siler."""
    simdi = simdi if simdi is not None else time.time()
    silinen = 0
    for dizin, omur in ((SPEC_DIZINI, SPEC_OMRU_SN), (RAPOR_DIZINI, RAPOR_OMRU_SN)):
        if not os.path.isdir(dizin):
            continue
        for ad in os.listdir(dizin):
            yol = os.path.join(dizin, ad)
            try:
                if simdi - os.path.getmtime(yol) > omur:
                    os.unlink(yol)
                    silinen += 1
            except OSError:
                continue
    return silinen


# --- kilit ----------------------------------------------------------------

def kilit_al(yol=None, simdi=None, _araya_gir=None):
    """Doner: (alindi_mi, hukum). Adaptör — govde kilit.py'de (TEK KAYNAK, K160 dilim-1).

    Donus sozlesmesi BIREBIR KORUNUR (nobet-kabul-test.py:290-304):
      alindi=True  -> "KILIT_ALINDI"
      alindi=False -> "ONCEKI_TUR_SURUYOR"
    `DEVRALINDI` / `YAZILAMADI` hukumleri DISARIYA SIZDIRILMAZ.

    K160 dilim-2: `_araya_gir` DIKIS YALNIZ TEST icin — uretimde daima None.
    Kilit alimi ile dosya yazma arasindaki TOCTOU penceresini DETERMINISTIK
    olarak uretmek icin testler tarafindan cagrilir (N-a: CANLI rakip kilit
    dikişte dogar). Imza geriye uyumlu — mevcut cagrilar (tur_kos vb.)
    _araya_gir gecirmez.
    """
    alindi, _hukuk = kilit.al(
        yol or KILIT_YOLU,
        simdi if simdi is not None else time.time(),
        _pid_canli, "%.0f", _damga, _araya_gir,
    )
    if alindi:
        return True, "KILIT_ALINDI"
    return False, "ONCEKI_TUR_SURUYOR"


def kilit_birak(yol=None):
    """Adaptör — govde kilit.py'de (TEK KAYNAK, K160 dilim-1)."""
    return kilit.birak(yol or KILIT_YOLU)


# --- dagitim --------------------------------------------------------------

def spec_metni(kalem, kat, rapor_yolu, etiket, el_kitabi_satiri=None):
    el_kitabi_blogu = []
    if el_kitabi_satiri:
        el_kitabi_blogu = [
            "## ONARIM EL KITABI (bu sinif icin)",
            "- sinif: %s" % el_kitabi_satiri["sinif"],
            "- arac: %s" % el_kitabi_satiri["arac"],
            "- KABUL_KOMUTU (aday): `%s`" % el_kitabi_satiri["kabul"],
            "Aday komut BASLANGIC noktasidir: kalemi gercekten olcmuyorsa daha dar",
            "bir komut belirle ve onu bildir.",
            "",
        ]
    return "\n".join([
        "# SPEC — 🔧 %s onarimi (nobet dagitimi, etiket: %s)" % (kalem["id"], etiket),
        "",
        "EV: %s · Kat: %s · Kaynak: acik-kalemler.md" % (EV_KOKU, kat),
        "",
        "## KALEM",
        "- id: %s" % kalem["id"],
        "- tarih: %s" % kalem["tarih"],
        "- kimden→kime: %s" % kalem["kimden_kime"],
        "- is: %s" % kalem["is"],
        "- defterdeki kanit sutunu: %s" % kalem["durum_ham"],
        "",
    ] + el_kitabi_blogu + [
        "## GOREV",
        "0. ILK ISIN: bu kalemin KABUL KOMUTUNU belirle ve raporunda",
        "   `KABUL_KOMUTU=<komut>` satiriyla bildir; komut YOKSA isi KAPATMA.",
        "   Komut, kalemin kapandigini BAGIMSIZ olcen TEK bir komuttur ve su bicimi",
        "   tasir: `python3 /tam/yol.py [arg]` ya da `node /tam/yol.js [arg]`;",
        "   yol `/Users/okan/dev/pruvo/tools/` ya da `/Users/okan/.claude/cron/`",
        "   altinda olmali, kabuk metakarakteri (`;` `|` `&` `$` ...) TASIYAMAZ.",
        "   🔴 Rapor `HUKUM=KAPANDI` dese bile kapi bu komutu KENDISI kosar: rc!=0",
        "   ise kalem `BEYAN_VAR_KANIT_YOK` ile ACIK kalir ve sana geri doner.",
        "1. Kalemin KOK NEDENINI olc (iddia degil, kosulan komut).",
        "2. EN KUCUK onarimi yap; kirmizi bir kapiyi GEVSETME (esik dusurme, adim silme,",
        "   `continue-on-error`, `--no-verify`, muafiyet satiri YASAK).",
        "3. Onarimi CALISTIRILABILIR bir testle kanitla; test yoksa once testi yaz.",
        "4. `urunler.json` / `.urun-kaynaklari.json` icerigine, secret dosyalarina ve",
        "   `CNAME`'e DOKUNMA. Force push / gecmis yeniden yazma YOK. Alt gorev ACMA.",
        "5. Sonucu su dosyaya YAZ (zorunlu): %s" % rapor_yolu,
        "",
        "## ILERLEME IZI (ZORUNLU — olursen canlilik kanitin budur)",
        "Rapor dosyasina ISE BASLAR BASLAMAZ bir WIP damgasi yaz: `HUKUM=UCUSTA`",
        "satirini UTC zamanla birlikte ekle. Ilerledikce (en az her 15 dk) bu damgayi",
        "GUNCELLE. Bitince `HUKUM=KAPANDI`/`HUKUM=BLOKE` ile degistir. Damga YOKSA",
        "nobet isciyi OLMUS sayar ve isi ayni turda yeniden dagitir.",
        "",
        "## RAPOR BICIMI (bu dosyaya yazilacak — raporsuz is DUSMUS sayilir)",
        "```",
        "KALEM=%s" % kalem["id"],
        "KABUL_KOMUTU=<kalemi bagimsiz olcen TEK komut>",
        "KOK_NEDEN=<tek cumle>",
        "DEGISEN_DOSYALAR=<liste ya da YOK>",
        "KANIT=<kosulan komut + rc / SHA / olculen sayi>",
        "KABUL: TEST_RC=<n> KANIT=<...>",
        "HUKUM=<KAPANDI|BLOKE>",
        "ONERI=<tek cumle>",
        "```",
        "`HUKUM=KAPANDI` yalniz onarim OLCULEREK dogrulandiysa yazilir; olcemedigin eksene",
        "`OLCULEMEDI` yaz, TAHMIN YAZMA. Kosmadigin komutun sonucunu YAZMA.",
        "",
        "## TEMIZLIK",
        "Urettigin gecici dosyalari (worktree, scratchpad, cache) is bitince SIL.",
        "",
    ])


# 🔴 UCUNCU HAL — TEK JETON (28 Agu 2026, Okan emri; cip KraL-NobetVeSirKolu-28Agu).
# "tur acilmadi" DEGIL, "acilmasi YAPISAL OLARAK IMKANSIZ". Ne TEMIZ (sahte
# yesil) ne OLCULEMEDI (sahte kirmizi). Jeton BURADA tanimlanir; `gozcu.py` ve
# `nobet-tetik.py` ONDAN TURETIR. Bes dosyada bes literal, bugun teshis
# ettigimiz hastaligin ta kendisidir ([[tuketici-yazilirken-tum-okuyucular-sayilir]]).
HUKUM_LLM_KOLU_KAPALI = "LLM_KOLU_KAPALI"


def _gercek_calistirici(komut, log_yolu):
    """28 Agu 2026 (Okan emri) — LLM tur-acma kolu KAPALI; tetik+gh+hukum+log AYNI kalir."""
    with open(os.path.join(CRON_KOKU, "ci-nobeti.log"), "a", encoding="utf-8") as _lk:
        _lk.write("HUKUM=%s sebep=OKAN_EMRI_28AGU komut=%s\n"
                  % (HUKUM_LLM_KOLU_KAPALI, " ".join(komut)))
    return 0  # isci.sh baslatilmaz; pid=0 => geri-iz "yasanamamis" sayar


def isci_komutu(motor, spec_yolu, rapor_yolu, etiket):
    """Canli motorlar icin isci sarmalayici komutu (emekli motorlar bu kola girmez)."""
    return [ISCI_SH, motor, EV_KOKU, spec_yolu, etiket]


def kalem_dagit(kalem, tur_no, geri_iz, calistirici=None, yeniden=False):
    """Tek kalemi kendi isçisine dagitir; geri-ize kaydeder. Doner: kayit."""
    calistirici = calistirici or (lambda komut, log: _gercek_calistirici(komut, log))
    kat = kat_sec(kalem, geri_iz)
    if kat == KAT_MIMAR:
        raise ValueError("KAT_MIMAR kalemi isci turuna dagitilamaz: %s" % kalem["id"])
    zincir = ISCI_YEDEK_ZINCIRI.get(kat, (kat,))
    onceki = geri_iz.get("kalemler", {}).get(kalem["id"], {})
    # 🔴 K257(a): SAYAC SIFIRDAN BASLAMAZ. Burada `yeniden` False iken sayi
    # 1'e EZILIYORDU: BITMEYEN_TUR kovasindan sonraki turda geri gelen kalem
    # (`yeniden` listesinde DEGILDIR) gecmisini kaybediyordu. Gecmisi olan
    # kalem bir daha 1'e DUSMEZ.
    _onceki_sayi = int(onceki.get("dagitim_sayisi", 0) or 0)
    sayi = _onceki_sayi + 1 if (yeniden or _onceki_sayi) else 1
    etiket = "nobet-%s-t%d" % (kalem["id"], tur_no)
    os.makedirs(SPEC_DIZINI, exist_ok=True)
    os.makedirs(RAPOR_DIZINI, exist_ok=True)
    rapor_yolu = os.path.join(RAPOR_DIZINI, "%s.md" % etiket)
    spec_yolu = os.path.join(SPEC_DIZINI, "%s.md" % etiket)
    el_kitabi_satiri = el_kitabi_satiri_sec(
        "%s %s" % (kalem.get("is", ""), kalem.get("durum_ham", "")), el_kitabi_oku())
    with open(spec_yolu, "w", encoding="utf-8") as dosya:
        dosya.write(spec_metni(kalem, kat, rapor_yolu, etiket, el_kitabi_satiri))
    # H5: kat motoru dusukse yedek zincirin ilk AYAKTA olan motoru secilir.
    motor = zincir[0]
    for aday in zincir:
        if motor_ayakta(aday):
            motor = aday
            break
    # K257: merdiven yalniz raporda degil ICRADA da yon verir — kalemin
    # basamagi CANLI bir isci motoruysa dagitim O basamaga yapilir.
    _basamak = MERDIVEN.merdiven_kaydi(onceki).get("basamak")
    if _basamak in CANLI_ISCI_MOTORLARI and motor_ayakta(_basamak):
        motor = _basamak
    komut = isci_komutu(motor, spec_yolu, rapor_yolu, etiket)
    pid = calistirici(komut, os.path.join(CRON_KOKU, "isci.log"))
    kayit = {
        "id": kalem["id"],
        "etiket": etiket,
        "tur": tur_no,
        "damga": _damga(),
        "kat": kat,
        "motor": motor,
        "spec_yolu": spec_yolu,
        "rapor_yolu": rapor_yolu,
        "pid": pid,
        "durum": "DAGITILDI",
        "dagitim_sayisi": sayi,
    }
    # 🔴 (c) OLCULMUS TASINIR: kayit YENIDEN kuruldugu icin merdiven gecmisi
    # burada DUSERDI; ust kat sifirdan olcmesin diye ACIKCA tasinir.
    if onceki.get("merdiven"):
        kayit["merdiven"] = onceki["merdiven"]
    # 🔴 K271 — AYNI SINIFIN IKINCI VAKASI, caresi bir ustteki satirdaydi.
    # `eskalasyon_bayat`, B4 gocunun YAPISAL izidir ve K260 dagitim kararini
    # ONA bagladi (`_emekli_kattan_gocmus`). Kayit yeniden kuruldugu icin
    # burada DUSUYORDU; dagitilan kalem duserse iz kaybolur ve kalem metin
    # kuraliyla YINE MIMAR'a kilitlenirdi. Olculdu (gozcu.log): K86 t647'de,
    # K108 t648'de DAGITILABILIR iken dagitildi, AYNI turdan sonra ikisi de
    # MIMAR_KATI_GERCEK'e dondu ve hattin dagitilabilir kuyrugu 0'a indi.
    # 🔴 SONSUZ DONGU YOK: damganin KORUNMASI gocu TEKRARLATMAZ — tersine,
    # `eskalasyon_bayat_mi` damgali kaydi ELER (goc BIR KEZ olur).
    if onceki.get("eskalasyon_bayat"):
        kayit["eskalasyon_bayat"] = onceki["eskalasyon_bayat"]
    geri_iz.setdefault("kalemler", {})[kalem["id"]] = kayit
    return kayit


def motor_ayakta(motor):
    """Anahtari olmayan canli motor dusmus sayilir (H5 on kontrolu)."""
    if motor in karantina_kayitlari():
        return False   # 15 Agu 2026: 6 saatlik kota karantinasinda, zincirden atlanir
    anahtarlar = {
        "minimax-m3": os.path.join(CRON_KOKU, ".minimax-anahtar"),
        "kimi": os.path.join(CRON_KOKU, ".kimi-anahtar"),
    }
    yol = anahtarlar.get(motor)
    if not yol:
        return False
    try:
        return os.path.getsize(yol) > 0
    except OSError:
        return False


def karantina_kayitlari(yol=None):
    """Karantina dosyasindaki 6 saatten taze motorlari {ad: epoch} sozlugu olarak
    dondurur. Sure dolanlari DOSYADAN dusurmez (temizle_ve_oku'ya birakir), yalniz
    filtreler — motor_ayakta() her cagirida dosyaya yazmaz."""
    yol = yol or KARANTINA_YOLU
    simdi = time.time()
    sonuc = {}
    try:
        with open(yol, encoding="utf-8") as dosya:
            for satir in dosya.read().splitlines():
                parca = satir.strip().split()
                if len(parca) < 2:
                    continue
                try:
                    damga = int(parca[1])
                except ValueError:
                    continue
                if simdi - damga < KARANTINA_OMUR_SN:
                    sonuc[parca[0]] = damga
    except FileNotFoundError:
        return {}
    return sonuc


def karantina_temizle_ve_oku(yol=None):
    """Karantina dosyasindan 6 saati dolmus satirlari silip dosyayi atomik yazar.
    Yenilenmis kayitlari dondurur. Zincir kurulmadan ONCE cagirilmali — sure dolan
    motoru ATLAmadan once dosyayi ter temiz tutar (surekli buyuyen dosya engeli)."""
    yol = yol or KARANTINA_YOLU
    simdi = time.time()
    tutulan = []
    try:
        with open(yol, encoding="utf-8") as dosya:
            ham = dosya.read()
    except FileNotFoundError:
        return {}
    for satir in ham.splitlines():
        parca = satir.strip().split()
        if len(parca) < 2:
            continue
        try:
            damga = int(parca[1])
        except ValueError:
            continue
        if simdi - damga < KARANTINA_OMUR_SN:
            tutulan.append("%s %d" % (parca[0], damga))
    sonuc = {}
    for s in tutulan:
        parca = s.split()
        sonuc[parca[0]] = int(parca[1])
    dizin = os.path.dirname(yol)
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=".motor-karantina.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as dosya:
            dosya.write("\n".join(tutulan) + ("\n" if tutulan else ""))
            dosya.flush()
            os.fsync(dosya.fileno())
        os.replace(gecici, yol)
    except BaseException:
        try:
            os.unlink(gecici)
        except FileNotFoundError:
            pass
        raise
    return sonuc


def karantina_en_eski(zincir, yol=None):
    """Tum zincir karantinadaysa fail-open icin en eski karantinaiyi dondurur.
    Zincir bossa None; hicbir karantinada yoksa None."""
    kayitlar = karantina_kayitlari(yol)
    adaylar = [m for m in zincir if m in kayitlar]
    if not adaylar:
        return None
    # En eski damga = en kucuk epoch; min kullaniyoruz.
    return min(adaylar, key=lambda m: kayitlar[m])


# --- tur akisi ------------------------------------------------------------

def _metne_cevir(cikti):
    if isinstance(cikti, bytes):
        return cikti.decode("utf-8", "replace")
    return cikti or ""


def onarim_ilerliyor_mu(cikti):
    """Kapinin ONARIM_ILERLIYOR hukmunu doguran ayni ONARIM>0 durumunu olcer."""
    metin = _metne_cevir(cikti)
    if tur_hukmu_ayikla(metin) == "ONARIM_ILERLIYOR":
        return True
    kapanan = tur_olcumu_ayikla(metin, "KAPANAN")
    dagitilan = tur_olcumu_ayikla(metin, "DAGITILAN")
    return kapanan + dagitilan > 0


def tur_cikti_yolu_uret(etiket="ci-nobeti", damga=None, pid=None):
    """B7: bu turun IZOLE cikti dosyasinin yolu (paylasilan isci.log DEGIL)."""
    damga = damga or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    pid = os.getpid() if pid is None else pid
    return os.path.join(TUR_CIKTI_DIZINI, "%s-%s-%d.log" % (etiket, damga, pid))


def tur_son_satirlar(yol, adet=TUR_SON_SATIR):
    """B7 kabul-2: (satirlar, sebep) doner.

    Bos/olmayan dosya SESSIZ bos string DEGIL, adi konmus bir OLCUMDUR:
    CIKTI_AKMADI = motor tavan boyunca TEK SATIR uretmedi (hat ekseni),
    OKUNAMADI    = dosya var ama okunamadi, YOL_YOK = yol hic verilmedi.
    """
    if not yol:
        return [], "YOL_YOK"
    try:
        with open(yol, encoding="utf-8", errors="replace") as dosya:
            satirlar = [s.rstrip("\n") for s in dosya]
    except OSError:
        return [], "OKUNAMADI"
    if not satirlar:
        return [], "CIKTI_AKMADI"
    return satirlar[-adet:], "TAMAM"


def _jetonlari_etkisizlestir(satir):
    """Gomulu kanit satiri hukum/olcum ayikcilarini YANILTMASIN."""
    return _MAKINE_JETONU.sub(lambda m: m.group(1) + ":", satir)


def _tur_son_blogu(tur_cikti_yolu, adet=TUR_SON_SATIR):
    """B7 kabul-2: son N satir + kaynak + sebep + MASKELENEN sayisi.

    Maskeleme SAYIYLA raporlanir: sessiz bir donusum degil, olculen bir islem.
    """
    satirlar, sebep = tur_son_satirlar(tur_cikti_yolu, adet)
    maskeli = []
    maskelenen = 0
    for satir in satirlar:
        yeni = _jetonlari_etkisizlestir(satir)
        if yeni != satir:
            maskelenen += 1
        maskeli.append("S%d| %s" % (adet, yeni))
    blok = "TUR_SON_%d_KAYNAK=%s\n" % (adet, tur_cikti_yolu or "-")
    blok += "TUR_SON_%d_SATIR=%d SEBEP=%s MASKELENEN=%d\n" % (
        adet, len(maskeli), sebep, maskelenen)
    if maskeli:
        blok += "--- TUR SON %d ---\n" % adet
        blok += "\n".join(maskeli) + "\n"
        blok += "--- TUR SON %d SONU ---\n" % adet
    return blok


def _sure_tavani_sonucu(cikti, sonlandirici, tavan, tur_cikti_yolu=None):
    """Isciyi sonlandirir; hafif hukmu SURE_TAVANI yapar, ARIZA'yi korur.

    B7: son-50 blogu HUKUM satirindan ONCE yazilir ve gomulu satirlarin
    makine jetonlari maskelidir -> `tur_hukmu_ayikla` yine SURE_TAVANI okur.
    """
    sonlandirici()
    metin = _metne_cevir(cikti)
    mevcut_hukum = tur_hukmu_ayikla(metin)
    hukum = mevcut_hukum if (mevcut_hukum or "").startswith("ARIZA") else "SURE_TAVANI"
    metin += "\nSURE_TAVANI_ASILDI=1 TAVAN_SN=%d\n" % tavan
    metin += _tur_son_blogu(tur_cikti_yolu)
    metin += "HUKUM=%s rc=1\n" % hukum
    return 1, metin


def _sureli_isci_bekle(bekleyici, sonlandirici, kisa_tavan=None, uzun_tavan=None,
                       tur_cikti_yolu=None):
    """Isciyi 25 dk; onarim ilerleme izi varsa toplam 50 dk bekler.

    bekleyici(saniye) -> (rc, cikti); sure dolunca subprocess.TimeoutExpired firlatir.
    Bu ayrim testte sahte bekleyiciyle saniye beklemeden olculur.
    B7: `tur_cikti_yolu` tavan asiminda son-50 teshisinin KAYNAGIDIR; kolun
    kendisi degismez, yalnizca hukme kanit eklenir.
    """
    kisa_tavan = TUR_ZAMAN_ASIMI_SN if kisa_tavan is None else kisa_tavan
    uzun_tavan = (TUR_ONARIM_ZAMAN_ASIMI_SN if uzun_tavan is None else uzun_tavan)
    try:
        return bekleyici(kisa_tavan)
    except subprocess.TimeoutExpired as hata:
        cikti = hata.output or b""
        if not onarim_ilerliyor_mu(cikti):
            return _sure_tavani_sonucu(cikti, sonlandirici, kisa_tavan, tur_cikti_yolu)
    kalan = max(0, uzun_tavan - kisa_tavan)
    try:
        return bekleyici(kalan)
    except subprocess.TimeoutExpired as hata:
        return _sure_tavani_sonucu(hata.output or cikti, sonlandirici, uzun_tavan,
                                   tur_cikti_yolu)


def _surec_grubunu_sonlandir(surec):
    """isci.sh ve actigi alt sureclerin tamamini once TERM, gerekirse KILL ile keser."""
    if surec.poll() is not None:
        return
    try:
        os.killpg(surec.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        surec.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(surec.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    surec.wait()


def _nobet_turunu_kos(motor):
    """28 Agu 2026 (Okan emri) — LLM tur-acma kolu KAPALI; tetik+gh+hukum+log AYNI kalir.

    🔴 DONUS METNI `HUKUM=` JETONUNU TASIR — `KOSUM_HUKMU=` DEGIL. Metni okuyan
    `kosum_tur_hukmu()` -> `tur_hukmu_ayikla()` deseni
    `(?<![A-Za-z0-9_])HUKUM\\s*=`dir ve `KOSUM_HUKMU` icinde `HUKUM` alt-dizgesi
    YOKTUR (`_HUKMU` != `HUKUM`). Ilk surum bu yuzden INERT kaldi: zincir
    `hukum=""` -> `kosum_hukmu_coz` -> `OLCULEMEDI` basiyordu ve kalp
    degismiyordu (canli kanit: 20:38:00Z nabzi).
    Jetonsuz hali de OLCULDU (28 Agu): 19:07 ve 20:07 turlari
    `GOZCU_URETMEDI_OLCULEMEDI` ile KIRMIZI kapandi — KAPALI bir kol,
    OLCULEMEYEN bir kol gibi gorunuyordu. Iki hal AYNI SEY DEGILDIR.
    """
    hukum = "HUKUM=%s sebep=OKAN_EMRI_28AGU motor=%s" % (
        HUKUM_LLM_KOLU_KAPALI, motor)
    print("TUR_CIKTI=<%s>" % HUKUM_LLM_KOLU_KAPALI)
    sys.stdout.flush()
    with open(NOBET_LOGU, "a", encoding="utf-8") as _lk:
        _lk.write(hukum + "\n")
    return 0, hukum


def _kuru_kabul_kosucu(komut):
    """Kuru turda kabul komutu KOSULMAZ (yan etkisiz plan turu)."""
    return {"hukum": "KURU_KOSULMADI", "rc": None, "sebep": "KURU", "argv": None,
            "komut": komut}


def _defter_satir_sayisi(yol=KOK_DEFTER_YOLU):
    """Kok defter satir sayisi; olculemeyen dosya turu dusurmez (fail-open)."""
    try:
        with open(yol, encoding="utf-8", errors="replace") as dosya:
            return sum(1 for _ in dosya)
    except OSError:
        return 0


# --- B8-TEK-SAYAC-KAPISI (20 Agu 2026, KraL-N4B) ---------------------------
# Bir turun sayac etkisi BURADAN gecer; `tur_kos`'un HER cikis yolu bu kapiya
# ugrar. Onceden 5 `return` vardi ve UCU (SURE_TAVANI, MOTOR_YOK x2) sayaci
# hic gormuyordu: kosup DUSEN tur "onarimsiz tur" sayilmiyordu.
# 🔴 K341 (28 Agu 2026): DORDUNCU hal `DONDURULDU`. Ucuncu kova `tur_hukmu`ye
# 27 Agu'da ogretildi (B1) ama AYNI OLGUNUN IKINCI OKUYUCUSU olan bu kapi
# ogretilmedi -> rc yesile dondu, sayac tirmanmaya DEVAM etti (154). Arizanin
# onarilmasi degil YER DEGISTIRMESIYDI ([[ucuncu-tekrar-sinif-kapisi]]).
TUR_HALLERI = ("KOSTU_ONARDI", "KOSTU_DUSTU", "ATLANDI", "IS_YOK",
               "DONDURULDU")

# --- B5-KOSUM-HUKMU (20 Agu 2026, KraL-N4B) --------------------------------
# RUN-ID denemesinin oznesi DEFTER bacagindan AYRIDIR. Olculdu
# (gozcu.log:1365-1371): motor rc=0 + "CI temiz" iken tur ONARIMSIZ_TUR rc=1
# kapandi ve o run-id'nin denemesi ARTTI; 10 eskalasyonun 4'u boyle dogdu.
KOSUM_HUKUMLERI = ("TEMIZ", "ONARIM_DENENDI", "MOTOR_DUSTU", "OLCULEMEDI")


def kosum_tur_hukmu(cikti):
    """B5: turun KENDI hukmu — N2B PARTI KAPISININ satirlari ELENEREK.

    Kapi da `HUKUM=` deseniyle yazar (`N2B HUKUM=GECER`); ayni desen oldugu
    icin `tur_hukmu_ayikla` onu turun hukmu sanabiliyordu (olculdu: canli
    14:23Z turu, `TUR_HUKMU=GECER`).
    """
    metin = "\n".join(s for s in (cikti or "").splitlines()
                      if not s.lstrip().startswith("N2B "))
    return tur_hukmu_ayikla(metin) or ""


def kosum_hukmu_coz(motor_rc, tur_hukmu, kapanan=0, dagitilan=0):
    """B5: bu KOSUMUN hukmu — yalniz kosuma dair kollardan turer.

    TEMIZ          -> motor kostu ve turun KENDI hukmu temiz: deneme KAPANIR.
    ONARIM_DENENDI -> motor kostu ama is bitmedi: deneme ARTAR (eskalasyon YASAR).
    MOTOR_DUSTU    -> motor hic bitiremedi (rc!=0, sure tavani, motor yok).
    OLCULEMEDI     -> hukum okunamadi; fail-closed, deneme ARTAR.
    LLM_KOLU_KAPALI-> kol YAPISAL OLARAK kapali: uretken DEGIL ama ARIZA da DEGIL.
    🔴 Defter bacaginin ONARIMSIZ_TUR hukmu bu fonksiyona GIRMEZ.
    """
    if motor_rc is None:
        return "OLCULEMEDI"
    if motor_rc != 0:
        return "MOTOR_DUSTU"
    hukum = (tur_hukmu or "").strip()
    # 🔴 UCUNCU HAL — ADIYLA GECER, KOVALARA DUSMEZ (28 Agu 2026).
    # Bu satir OLMAZSA jeton en alttaki `return "ONARIM_DENENDI"`e duser; o
    # hukum `gozcu.URETKEN_KOSUM_HUKUMLERI` icindedir ve KAPALI bir kol
    # "IS GORDU" diye okunur — sahte yesil. TEMIZ kovasina da girmez.
    if hukum == HUKUM_LLM_KOLU_KAPALI:
        return HUKUM_LLM_KOLU_KAPALI
    if hukum in ("TEMIZ", "KAPANDI", "ONARIM_YOK"):
        return "TEMIZ"
    if hukum == "ONARIM_ILERLIYOR" or (kapanan + dagitilan) > 0:
        return "ONARIM_DENENDI"
    if not hukum:
        return "OLCULEMEDI"
    return "ONARIM_DENENDI"




def tur_sayacini_kaydet(hal, onarim=0, yaz=True, yol=None, kova_bos=False,
                        sebep=None):
    """Turun `ustuste_onarimsiz` etkisini TEK kapidan gecirir.

    KOSTU_ONARDI -> sifirlanir · KOSTU_DUSTU -> +1 · DONDURULDU -> sifirlanir
    (K341: bayrak GERCEKTEN isirdi; onarimsizlik EMRIN sonucu, arizanin
    degil) · IS_YOK -> sifirlanir
    (kova bos + eskalasyon yok: "yapacak is yoktu", onarimsizlik ANLAMSIZ) ·
    ATLANDI -> DEGISMEZ.
    Doner: (yeni_sayac, yazildi_mi). ATLANDI'da yazma YAPILMAZ ama cagri
    KAYDA gecer: "sayaca hic ugramayan kol" kalmaz.
    Bilinmeyen hal SESSIZCE gecmez -> ValueError (fail-closed).
    """
    if hal not in TUR_HALLERI:
        raise ValueError("bilinmeyen tur hali: %r" % (hal,))
    if hal == "ATLANDI" or not yaz:
        return ustuste_onarimsiz_oku(yol), False
    if hal in ("IS_YOK", "DONDURULDU"):
        # Ikisi de sifirlar ama AYRI yuklemle ve kayitta AYRI adla: "kova
        # bostu" ile "kova doluydu, EMIR kapatti" ayri iddialardir.
        return ustuste_onarimsiz_guncelle(
            0, yol, kova_bos=(hal == "IS_YOK"), dondu=(hal == "DONDURULDU"),
            hal=hal, sebep=sebep), True
    return ustuste_onarimsiz_guncelle(onarim if hal == "KOSTU_ONARDI" else 0,
                                      yol, hal=hal, sebep=sebep), True


def _tur_hali_bas(hal, sebep, sayac, yazildi):
    """Turun hali TEK bicimde raporlanir (tuketici desen kurabilsin)."""
    print("TUR_HALI=%s SEBEP=%s USTUSTE_ONARIMSIZ=%d SAYAC_YAZILDI=%d"
          % (hal, sebep, sayac, int(yazildi)))
    sys.stdout.flush()


def _tur_dustu(sebep):
    """B8: KOSUP DUSEN her kol bu kapidan gecer ve rc=1 doner.

    B5: ayni kol RUN-ID hukmunu de basar — dusen tur "temiz kosum" DEGILDIR
    ve bu hukum defter bacagindan BAGIMSIZDIR.
    """
    sayac, yazildi = tur_sayacini_kaydet("KOSTU_DUSTU")
    _tur_hali_bas("KOSTU_DUSTU", sebep, sayac, yazildi)
    print("KOSUM_HUKMU=MOTOR_DUSTU MOTOR_RC=- TUR_HUKMU=%s" % sebep)
    sys.stdout.flush()
    return 1


def tur_kapat(kuru=False, calistirici=None, yaz=True, kabul_kosucu=None,
              pid_canli=None, simdi=None, defter_once=None, tasinan=0,
              mevcut_hukum=None):
    """H1+H2+H4+C3+supurme ekseni: dagitimi yapar ve tur hukmunu doner."""
    geri_iz = geri_iz_oku()
    tur_no = int(geri_iz.get("tur_no", 0)) + 1
    # B4 kabul-3 (fail-closed): canli kume BOS ise hicbir sey gocmez ve tur
    # OLCULEMEDI ile kapanir. "Hepsi bayat" diye TOPLU goc ETTIRILMEZ.
    if not KAT_KAYNAGI_OLCULDU or not CANLI_ISCI_MOTORLARI:
        _kaynak_sebebi = KAT_KAYNAGI_SEBEBI or "canli_motor_kumesi_bos"
        satirlar = [
            "=== %s NOBET ONARIM BACAGI tur=%d%s ===" % (
                _damga(), tur_no, " KURU" if kuru else ""),
            "KAT_KAYNAGI=OLCULEMEDI sebep=%s" % _kaynak_sebebi,
            "HUKUM=KAT_KAYNAGI_OLCULEMEDI rc=2",
        ]
        return {
            "rc": 2, "hukum": "KAT_KAYNAGI_OLCULEMEDI", "acik": 0,
            "kapanan": 0, "dagitilan": 0, "sirada": 0, "okan": 0,
            "kat_sayaci": {}, "eskalasyon": [], "rapor": "\n".join(satirlar),
            "tur_no": tur_no, "kabul_dolu": 0, "kabul_bos": 0,
            "beyan_var_kanit_yok": [], "olu": [], "kabul_yok": [],
            "reddedilen": [], "kabul_olculemedi": [], "kabul_yazilacak": {},
            "defter_hukmu": "DEFTER_YAZMA=ATLANDI", "defter_buyumesi": None,
            "onarim": 0, "tasinan": tasinan,
            "ustuste_onarimsiz": ustuste_onarimsiz_oku(),
        }
    tum_kalemler = defter_oku()
    kalemler = onarim_kalemleri(tum_kalemler)
    kabul_haritasi = kabul_haritasi_kur(tum_kalemler)
    if kabul_kosucu is None and kuru:
        kabul_kosucu = _kuru_kabul_kosucu
    olcum = geri_iz_degerlendir(geri_iz, tur_no, rapor_oku, kabul_haritasi,
                                kabul_kosucu, pid_canli, simdi)
    yeniden = set(olcum["dusen"])
    # 🔴 B4: BAYAT eskalasyonlar fanout'tan ONCE gocer — goc kalemi aday
    # havuzuna geri sokar, sonra sokulursa bu tur yine DAGITILAN=0 kalir.
    goc_satirlari, goc_sayisi = bayat_eskalasyonlari_gocur(geri_iz)
    # 🔴 K257(d): BaBa basamagi HUKUM/TESHIS katidir, icra kati DEGIL. Orada
    # SAYAC islemez, SLA isler: kalem yasi 24 saati asarsa Okan basamagi.
    # Bu kol `denemeler` listesine DOKUNMAZ (sayaca dahil DEGIL).
    sla_satirlari = []
    for _sla_id, _sla_kayit in sorted((geri_iz.get("kalemler") or {}).items()):
        _sla = MERDIVEN.sla_karari(_sla_kayit,
                                   canli_motorlar=CANLI_ISCI_MOTORLARI)
        if _sla and _sla.get("asildi"):
            sla_satirlari.append(
                "MERDIVEN_SLA kalem=%s BASAMAK=BABA->OKAN YAS_SN=%d SAYAC=%d"
                % (_sla_id, int(_sla["yas_sn"]), _sla["sayac"]))
    # K257(b): BITMEYEN_TUR kalemi B7'nin kovasindadir — AYNI TUR YENIDEN
    # KURULMAZ, kalem BU turda aday havuzuna girmez (sonraki turda girer).
    plan = fanout_plani(kalemler, geri_iz, FANOUT_TAVANI, yeniden=yeniden,
                        haric=set(olcum["kapanan"])
                        | set(olcum.get("bitmeyen_tur") or ()))

    satirlar = []
    satirlar.append("=== %s NOBET ONARIM BACAGI tur=%d%s ===" % (
        _damga(), tur_no, " KURU" if kuru else ""))
    satirlar.extend(goc_satirlari)
    satirlar.append("ESKALASYON_BAYAT_GOC=%d" % goc_sayisi)
    satirlar.extend(sla_satirlari)
    satirlar.extend(olcum.get("merdiven_satirlari") or ())
    satirlar.extend(olcum.get("eskalasyon_satirlari") or ())
    satirlar.append("MERDIVEN_ARAC_KUSURU=%d MERDIVEN_BITMEYEN_TUR=%d "
                    "MERDIVEN_KOTA_BEKLEMEDE=%d MERDIVEN_OLCULEMEDI=%d"
                    % (len(olcum.get("arac_kusuru") or ()),
                       len(olcum.get("bitmeyen_tur") or ()),
                       len(olcum.get("kota_beklemede") or ()),
                       len(olcum.get("merdiven_olculemedi") or ())))
    kat_sayaci = {KAT_MIMAR: 0, KAT_TARAMA: 0, KAT_MEKANIK: 0, KAT_OKAN: 0}
    for kalem in kalemler:
        kat = kat_sec(kalem, geri_iz)
        kat_sayaci[kat] = kat_sayaci.get(kat, 0) + 1
    for kalem in plan["dagitilacak"]:
        satirlar.append("KALEM %s -> %s [%s]" % (
            kalem["id"], kat_sec(kalem, geri_iz),
            "YENIDEN" if kalem["id"] in yeniden else "DAGITILACAK"))
    for kalem in plan["sirada"]:
        satirlar.append("KALEM %s -> %s [SIRADA]" % (
            kalem["id"], kat_sec(kalem, geri_iz)))
    for kalem in plan["mimar"]:
        satirlar.append("KALEM %s -> MIMAR [DAGITILMAZ] SEBEP=%s" % (
            kalem["id"], kova_sec(kalem, geri_iz)))
    for kalem in plan["okan"]:
        satirlar.append("KALEM %s -> OKAN [DAGITILMAZ] SEBEP=%s" % (
            kalem["id"], kova_sec(kalem, geri_iz)))

    dagitilan = 0
    _dondu, _dondu_sebep = dondurma_karari()
    _aday = len(plan["dagitilacak"])
    if _dondu:
        # 🔴 KAPSAM: YALNIZ dagitim. Ustteki goc/SLA/merdiven/eskalasyon
        # satirlari ZATEN yazildi ve DEGISMEDI (regresyon kabulu ④).
        satirlar.append(
            "DONDURULDU@tur%d KOL=DAGITIM ATIF=BAYRAK sebep=%s ADAY=%d SIRADA=%d bayrak=%s"
            % (tur_no, _dondu_sebep, _aday, len(plan["sirada"]),
               DONDURMA_BAYRAK_YOLU))
        # 🔴 IKI SEBEBI AYIR ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]):
        # "bayrak ISIRDI" ile "dagitilacak kalem ZATEN YOKTU" (K311 ekseni)
        # AYNI CIKTI DEGILDIR. ADAY=0 iken bayragin ISIRDIGI SOYLENEMEZ.
        if _aday:
            satirlar.append("DONDURMA_ISIRDI=1 ENGELLENEN=%d" % _aday)
        else:
            satirlar.append(
                "DONDURMA_ISIRDI=0 ENGELLENEN=0 UYARI=ADAY_ZATEN_0 "
                "sebep_sinifi=K311_DAGITILACAK_KALEM_YOK bayrak_ISIRMADI")
    elif not kuru:
        for kalem in plan["dagitilacak"]:
            try:
                kayit = kalem_dagit(kalem, tur_no, geri_iz, calistirici,
                                    yeniden=kalem["id"] in yeniden)
                dagitilan += 1
                satirlar.append("DAGITILDI %s etiket=%s motor=%s pid=%s" % (
                    kalem["id"], kayit["etiket"], kayit["motor"], kayit["pid"]))
            except Exception as hata:  # dagitim duserse SESSIZ olmaz
                satirlar.append("DAGITIM_DUSTU %s sebep=%s" % (kalem["id"], hata))
    else:
        dagitilan = _aday

    kapanan = len(olcum["kapanan"])
    acik = len(kalemler)
    onarim = kapanan + dagitilan
    # 🔴 KOL B2: `DONDURMA_ISIRDI=1` satirinin TUKETICISI. Bayrak yalniz
    # GERCEKTEN engelledi ise (aday>0) hukum ucuncu kovaya duser.
    _dondurma_isirdi = bool(_dondu and _aday)
    rc, hukum = tur_hukmu(acik, kapanan, dagitilan, tasinan=tasinan,
                          mevcut_hukum=mevcut_hukum,
                          dondurma_isirdi=_dondurma_isirdi)
    # 🔴 D-sayac: eskale listelerini ONCE hesapla; sayac karari buna BAGLI.
    # "Kova bos + eskalasyon yok" hali "onarim DENENDI ve DUSTU" halinden
    # AYRIDIR — birincide sayac ARTMAZ ve sifirlanir (yapacak is yoktu).
    mimar_eskale = sorted(set(k["id"] for k in plan["mimar"]))
    okan_eskale = sorted((set(olcum["eskalasyon"]) | set(plan["eskale"])) - set(mimar_eskale))
    if not kuru and yaz:
        kova_bos_hali = (acik == 0 and onarim == 0
                         and not mimar_eskale and not okan_eskale)
        # 🔴 K341 E2: `DONDURMA_ISIRDI=1` satirinin IKINCI tuketicisi.
        # SIRA onemli: gercek onarim (KOSTU_ONARDI) dondurmayi EZER — donmus
        # bir turda kalem KAPANMIS olabilir, o hal onarimdir.
        # 🔴 GEVSETME DEGIL: `_dondurma_isirdi` yalniz ADAY>0 iken True'dur;
        # bayrak acik ama dagitilacak kalem zaten yoksa eski KOSTU_DUSTU
        # AYNEN durur ve sayac ARTAR (kabul bataryasinin KONTROL vakasi).
        ustuste_onarimsiz, _ = tur_sayacini_kaydet(   # B8 TEK KAPI
            "IS_YOK" if kova_bos_hali
            else "KOSTU_ONARDI" if onarim > 0
            else "DONDURULDU" if _dondurma_isirdi
            else "KOSTU_DUSTU", onarim, sebep=_dondu_sebep if _dondu else None)
    else:
        ustuste_onarimsiz = ustuste_onarimsiz_oku()
    # Eskale kalem HER TURDA basilir: bir kez basilip kaybolursa ilgili kapi unutulur.
    if okan_eskale:
        satirlar.append("ESKALASYON=OKAN kalemler=%s" % ",".join(okan_eskale))
    if mimar_eskale:
        satirlar.append("ESKALASYON=MIMAR kalemler=%s" % ",".join(mimar_eskale))
    eskale_hepsi = sorted(set(okan_eskale) | set(mimar_eskale))
    if ustuste_onarimsiz >= 3:
        satirlar.append("ESKALASYON=OKAN USTUSTE_ONARIMSIZ=%d" % ustuste_onarimsiz)
    # 🔴 K341 E4 TUKETICI: seviye YAZILIP OKUNUR. Yazilip okunmayan alan kayit
    # degil SUStur ([[kapinin-menzili-cagri-yeridir]]); ve duran bir emir
    # gorunmez olursa hat en cok gereken anda korlesir
    # ([[kenar-tetikli-kol-seviye-sorusunu-cevaplayamaz]]).
    if _dondurma_isirdi:
        _dgun, _dgun_sebep = dondurma_seviyesi()
        _dgun_metin = "OLCULEMEDI" if _dgun is None else str(_dgun)
        satirlar.append(
            "DONDURMA_SEVIYE GUN=%s SEBEP=%s ENGELLENEN=%d SAYAC_HAL=DONDURULDU"
            % (_dgun_metin, _dgun_sebep, _aday))
        if _dgun is None or _dgun >= DONDURMA_ESKALASYON_GUN:
            satirlar.append(
                "ESKALASYON=OKAN DONDURMA_GUN=%s ENGELLENEN=%d SIRADA=%d bayrak=%s"
                % (_dgun_metin, _aday, len(plan["sirada"]),
                   DONDURMA_BAYRAK_YOLU))

    # C1/C2: kabul komutu OLMAYAN kalem KAPANAN sayacina giremez -> sayisi basilir.
    kabul_dolu = len([k for k in kalemler if k.get("kabul")])
    kabul_bos = len(kalemler) - kabul_dolu
    defter_hukmu = "DEFTER_YAZMA=ATLANDI"
    if not kuru and yaz:
        guncellemeler = {}
        for kimlik in olcum["kapanan"]:
            guncellemeler.setdefault(kimlik, {})["durum"] = "KAPANDI"
        for kimlik, komut in olcum["kabul_yazilacak"].items():
            guncellemeler.setdefault(kimlik, {})["kabul"] = komut
        if guncellemeler:
            try:
                defter_hukmu = defter_yaz(guncellemeler)["hukum"]
            except OSError as hata:      # defter yazilamadiysa SESSIZ olmaz
                defter_hukmu = "DEFTER_YAZMA=HATA(%s)" % hata
        else:
            defter_hukmu = "DEFTER_YAZMA=DEGISIKLIK_YOK"

    satirlar.append("ACIK_KALEM=%d" % acik)
    # KORGOZ_K311_SOZLUK: sozlugun UC kovasi da her turda SAYIYLA basilir.
    # Toplam DEFTER_SATIR'a esit olmali; esit degilse bir kova sessizce yutuyor.
    _sahipli = sahipli_kalemler(tum_kalemler)
    _bilinmeyen = bilinmeyen_durumlu_kalemler(tum_kalemler)
    satirlar.append(
        "DURUM_SOZLUGU DEFTER_SATIR=%d ONARILACAK=%d SAHIPLI=%d KAPALI=%d "
        "BILINMEYEN_DURUM=%d" % (
            len(tum_kalemler), acik, len(_sahipli),
            len([k for k in tum_kalemler
                 if k["durum"] in KAPALI_DURUMLAR_DEFTER]),
            len(_bilinmeyen)))
    if _bilinmeyen:
        satirlar.append("BILINMEYEN_DURUM_KALEM=%s" % ",".join(
            "%s(%s)" % (k["id"], k["durum"]) for k in _bilinmeyen))
    satirlar.append("KAPANAN=%d" % kapanan)
    satirlar.append("DAGITILAN=%d" % dagitilan)
    satirlar.append("ONARIM=%d" % onarim)
    satirlar.append("TASINAN=%d" % tasinan)
    satirlar.append("USTUSTE_ONARIMSIZ=%d" % ustuste_onarimsiz)
    satirlar.append("SIRADA=%d" % len(plan["sirada"]))
    satirlar.append("UCUSTA=%d" % len(olcum["ucusta"]))
    satirlar.append("OLU=%d" % len(olcum["olu"]))
    satirlar.append("OKAN_KALEMI=%d" % len(plan["okan"]))
    satirlar.append("KAT_MIMAR=%d KAT_TARAMA=%d KAT_MEKANIK=%d KAT_OKAN=%d" % (
        kat_sayaci[KAT_MIMAR], kat_sayaci[KAT_TARAMA],
        kat_sayaci[KAT_MEKANIK], kat_sayaci[KAT_OKAN]))
    # K260: uc kovanin SAYISI her turda basilir (oran DEGIL sayi). Toplam
    # ACIK_KALEM'e esittir — kayip olursa satirdan GORUNUR.
    _kova = kova_dagilimi(kalemler, geri_iz)
    satirlar.append(
        "K260_KOVA DAGITILABILIR=%d MIMAR_KATI_GERCEK=%d OKAN_KAPISI=%d TOPLAM=%d"
        % (len(_kova[KOVA_DAGITILABILIR]), len(_kova[KOVA_MIMAR_GERCEK]),
           len(_kova[KOVA_OKAN]),
           sum(len(v) for v in _kova.values())))
    for _kova_adi in KOVA_ADLARI:
        if _kova[_kova_adi]:
            satirlar.append("K260_KOVA_%s=%s" % (
                _kova_adi, ",".join(sorted(_kova[_kova_adi]))))
    satirlar.append("KABUL_DOLU=%d KABUL_BOS=%d KABUL_OLCULEMEDI=%d "
                    "BEYAN_VAR_KANIT_YOK=%d" % (
                        kabul_dolu, kabul_bos,
                        len(olcum["olculemedi"]),
                        len(olcum["beyan_var_kanit_yok"])))
    satirlar.append("KABUL_KOMUTU_YOK=%d KOMUT_REDDEDILDI=%d" % (
                        len(olcum["kabul_yok"]), len(olcum["reddedilen"])))
    for kimlik in olcum["beyan_var_kanit_yok"]:
        olculen = olcum["kabul_olcumleri"].get(kimlik, {})
        satirlar.append("BEYAN_VAR_KANIT_YOK %s kabul=%s rc=%s" % (
            kimlik, olculen.get("kabul"), olculen.get("rc")))
    for kimlik in olcum["reddedilen"]:
        olculen = olcum["kabul_olcumleri"].get(kimlik, {})
        satirlar.append("KOMUT_REDDEDILDI %s sebep=%s" % (kimlik, olculen.get("sebep")))
    satirlar.append(defter_hukmu)
    satirlar.append("TAHMINI_TUR_SAYISI_GUNLUK=48")
    defter_buyumesi = None
    if defter_once is None:
        satirlar.append("DEFTER_BUYUMESI=OLCULMEDI")
    else:
        simdiki = _defter_satir_sayisi()
        defter_buyumesi = max(0, simdiki - defter_once)
        satirlar.append("DEFTER_BUYUMESI=%d TAVAN=%d" % (
            defter_buyumesi, DEFTER_BUYUME_TAVANI))
        if defter_buyumesi > DEFTER_BUYUME_TAVANI:
            if rc == 0:
                rc = 1
                hukum = "DEFTER_SISIRME"
    if hukum == "ONARIMSIZ_SUPURME":
        satirlar.append("GEREKCE=onarilmadan alarm kanali susturuldu")
    satirlar.append("HUKUM=%s rc=%d" % (hukum, rc))

    if not kuru and yaz:
        geri_iz["tur_no"] = tur_no
        geri_iz["son_damga"] = _damga()
        geri_iz_yaz(geri_iz)
        artik_temizle()

    return {
        "rc": rc, "hukum": hukum, "acik": acik, "kapanan": kapanan,
        "dagitilan": dagitilan, "sirada": len(plan["sirada"]),
        "okan": len(plan["okan"]), "kat_sayaci": kat_sayaci,
        "eskalasyon": eskale_hepsi, "rapor": "\n".join(satirlar),
        "tur_no": tur_no, "kabul_dolu": kabul_dolu, "kabul_bos": kabul_bos,
        "beyan_var_kanit_yok": olcum["beyan_var_kanit_yok"],
        "olu": olcum["olu"],
        "kabul_yok": olcum["kabul_yok"], "reddedilen": olcum["reddedilen"],
        "kabul_olculemedi": olcum["olculemedi"],
        "kabul_yazilacak": olcum["kabul_yazilacak"],
        "defter_hukmu": defter_hukmu,
        "defter_buyumesi": defter_buyumesi,
        "onarim": onarim, "tasinan": tasinan,
        "ustuste_onarimsiz": ustuste_onarimsiz,
    }


def _n2_devir_logla():
    """K263 savunma katmani: nobet-kapi da nobet_devir modulu ile devir karari
    alir; devir karari olculup loga basilir. gozcudeki n2_devir_kararlari asil
    mekanizma — burasi ek cagri yeri kanitidir (>=3 dosya + iki yollu).
    """
    try:
        if not os.path.isfile(NOBET_DEVIR_YOLU):
            return
        spec = importlib.util.spec_from_file_location("nk_nobet_devir",
                                                      NOBET_DEVIR_YOLU)
        if spec is None or spec.loader is None:
            return
        modul = importlib.util.module_from_spec(spec)
        eski = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec.loader.exec_module(modul)
        finally:
            sys.dont_write_bytecode = eski
        if not hasattr(modul, "devir_karari"):
            return
        kalemler = defter_oku() or []
        if not kalemler:
            print("N2_DEVIR bos=0 devir_karari=cagrildi")
            return
        simdi = time.time()
        sayac = {"DEVREDILDI": 0, "SLA_ICINDE": 0, "KAPALI": 0, "ZATEN": 0,
                 "ihlal": 0, "hata": 0}
        for kalem in kalemler:
            try:
                sonuc = modul.devir_karari(kalem, simdi)
            except Exception as hata:
                sayac["hata"] += 1
                continue
            if not sonuc.get("devredildi"):
                sebep = sonuc.get("sebep", "")
                if sebep == "SLA_ICINDE":
                    sayac["SLA_ICINDE"] += 1
                elif sebep == "KAPALI":
                    sayac["KAPALI"] += 1
                elif sebep == "ZATEN_DEVREDILDI":
                    sayac["ZATEN"] += 1
                continue
            sayac["DEVREDILDI"] += 1
            if sonuc.get("ihlal_delta"):
                sayac["ihlal"] += int(sonuc["ihlal_delta"])
        print("N2_DEVIR D=%d S=%d K=%d Z=%d I=%d H=%d devir_karari=cagrildi"
              % (sayac["DEVREDILDI"], sayac["SLA_ICINDE"], sayac["KAPALI"],
                 sayac["ZATEN"], sayac["ihlal"], sayac["hata"]))
    except Exception as hata:
        print("N2_DEVIR HATA=%s devir_karari=cagrildi" % hata)


def tur_kos():
    """ci-nobeti.sh'in tek girisi: kilit -> motor zinciri -> H1 kapisi.

    B8: bu fonksiyonun HER cikis yolu `tur_sayacini_kaydet`'e ugrar.
    Cikis yolu envanteri CIVILIDIR ve `nobet-sayac-cikis-yollari-test.py`
    tarafindan ast ekseninde sayilir: 5 `return`, uc hal.
    """
    _n2_devir_logla()
    alindi, hukum = kilit_al()
    if not alindi:
        atlanan_ardisik = atlanan_ardisik_guncelle(True)
        print(atlama_satiri(hukum, atlanan_ardisik))
        _tur_hali_bas("ATLANDI", "KILIT_DOLU", *tur_sayacini_kaydet("ATLANDI"))
        return 0
    try:
        atlanan_ardisik_guncelle(False)
        print("=== %s BASLANGIC (nobet-kapi) ===" % _damga())
        sys.stdout.flush()
        once = _defter_satir_sayisi()
        # 15 Agu 2026: 6 saati dolan karantinalari once dusur (surekli buyuyen
        # dosya engeli). motor_ayakta() karantinayi zaten filtreler.
        karantina = karantina_temizle_ve_oku()
        if karantina:
            print("KOTAKARANTINA motorlar=%s omur=6h" % ",".join(sorted(karantina)))
        zincir = [m for m in TUR_MOTOR_ZINCIRI if motor_ayakta(m)]
        if not zincir:
            # H5: tum motorlar karantinadaysa en eski karantinaiyi dene
            # (fail-open: is tamamen durmasin); sonucu logla.
            en_eski = karantina_en_eski(TUR_MOTOR_ZINCIRI)
            if en_eski:
                print("KOTAKARANTINA=fail-open en_eski=%s" % en_eski)
                zincir = [en_eski]
            else:
                print("HUKUM=MOTOR_YOK sebep=ayakta motor yok")
                return _tur_dustu("MOTOR_YOK_AYAKTA")
        sonuc = motor_zinciri_kos(zincir, _nobet_turunu_kos)
        for deneme in sonuc["denemeler"]:
            print("MOTOR_DENEME motor=%s rc=%d sebep=%s" % (
                deneme["motor"], deneme["rc"], deneme["sebep"]))
        if sonuc["cikti"]:
            print(sonuc["cikti"])
        if "SURE_TAVANI_ASILDI=1" in sonuc["cikti"]:
            return _tur_dustu("SURE_TAVANI")
        if sonuc["hukum"] == "MOTOR_YOK":
            print("HUKUM=MOTOR_YOK rc=1")
            return _tur_dustu("MOTOR_YOK_ZINCIR")
        print("MOTOR=%s" % sonuc["motor"])
        tasinan = tur_olcumu_ayikla(sonuc["cikti"], "TASINAN")
        mevcut_hukum = tur_hukmu_ayikla(sonuc["cikti"])
        # 🔴 B5: RUN-ID hukmu DEFTER bacagindan ONCE ve ONDAN BAGIMSIZ basilir.
        # `tur_kapat` birazdan ONARIMSIZ_TUR yazabilir; o hukum EVIN borcunu
        # olcer, bu run'in kirmizisini DEGIL. Ikisi ayni sayaca yazilinca
        # 10 eskalasyonun 4'u sahte dogdu (gozcu.log:1365-1371).
        _kosum_hukmu = kosum_tur_hukmu(sonuc["cikti"])
        print("KOSUM_HUKMU=%s MOTOR_RC=%s TUR_HUKMU=%s" % (
            kosum_hukmu_coz(sonuc["rc"], _kosum_hukmu,
                            tur_olcumu_ayikla(sonuc["cikti"], "KAPANAN"),
                            tur_olcumu_ayikla(sonuc["cikti"], "DAGITILAN")),
            sonuc["rc"], _kosum_hukmu or "-"))
        sys.stdout.flush()
        kapi = tur_kapat(defter_once=once, tasinan=tasinan,
                         mevcut_hukum=mevcut_hukum)
        print(kapi["rapor"])
        return kapi["rc"]
    finally:
        kilit_birak()
        _logu_kirp()


def _logu_kirp(yol=NOBET_LOGU, tavan=3000):
    try:
        with open(yol, encoding="utf-8", errors="replace") as dosya:
            satirlar = dosya.readlines()
    except FileNotFoundError:
        return
    if len(satirlar) <= tavan:
        return
    with open(yol, "w", encoding="utf-8") as dosya:
        dosya.writelines(satirlar[-tavan:])


def main(argv=None):
    ayristirici = argparse.ArgumentParser(description="PRUVO nobet onarim bacagi kapisi")
    ayristirici.add_argument("--tur", action="store_true",
                             help="tam tur: kilit + motor zinciri + H1 kapisi")
    ayristirici.add_argument("--tur-kapat", action="store_true",
                             help="yalniz onarim bacagi (dagitim + H1 hukmu)")
    ayristirici.add_argument("--kuru", action="store_true",
                             help="kuru tur: GERCEK isci ACMAZ, plani basar")
    ayristirici.add_argument("--kilit-al", action="store_true")
    ayristirici.add_argument("--kilit-birak", action="store_true")
    ayristirici.add_argument("--el-kitabi-uret", action="store_true",
                             help="K316: el kitabi `kat` sutununu kat_sec'ten URET "
                                  "(--kuru ile YAZMADAN farki basar)")
    args = ayristirici.parse_args(argv)

    if args.el_kitabi_uret:
        sonuc = el_kitabi_kat_uret(kuru=bool(args.kuru))
        for sinif, eski, yeni in sonuc["fark"]:
            print("KAT_AYRISMASI %-40s %s -> %s" % (sinif[:40], eski, yeni))
        print("EL_KITABI OKUNAN=%d DEGISEN=%d YAZILDI=%s KURU=%s" % (
            sonuc["okunan"], sonuc["degisen"], sonuc["yazildi"], bool(args.kuru)))
        return 0

    if args.kilit_al:
        alindi, hukum = kilit_al()
        print("HUKUM=%s" % hukum)
        return 0 if alindi else 75
    if args.kilit_birak:
        print("HUKUM=%s" % ("KILIT_BIRAKILDI" if kilit_birak() else "KILIT_YOK"))
        return 0
    if args.kuru:
        sonuc = tur_kapat(kuru=True)
        print(sonuc["rapor"])
        return 0
    if args.tur_kapat:
        sonuc = tur_kapat()
        print(sonuc["rapor"])
        # 🔴 KOL B3 (27 Agu 2026): bu yol `KOSUM_HUKMU=` jetonunu HIC
        # basmiyordu. Jeton `--tur` yolunda (kosum hukmu satiri) ve
        # `_tur_dustu`ta VARDI, burada YOKTU. `gozcu.py` DEFTER_DAGITIM
        # turunda tam da bu yolu kosar ve ciktida o jetonu ARAR; bulamayinca
        # fail-closed `OLCULEMEDI` yazar ve tur KIRMIZI kapanir.
        # "Okuyan var, YAZAN yok" -- olcum eksikligi, ariza DEGIL.
        # Fail-closed korunur: rc!=0 iken jeton ASLA TEMIZ olmaz.
        print("KOSUM_HUKMU=%s MOTOR_RC=- TUR_HUKMU=%s" % (
            "TEMIZ" if sonuc["rc"] == 0 else "DAGITIM_BACAGI_DUSTU",
            sonuc.get("hukum") or "-"))
        sys.stdout.flush()
        return sonuc["rc"]
    if args.tur:
        return tur_kos()
    ayristirici.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
