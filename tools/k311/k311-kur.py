#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K311 KURUCU — "beyan edilen hukum bir TUKETICIYE baglanir".

DUZLEM: ~/.claude/cron (surum kontrolu YOK) -> idempotent + yedekli + --geri-al.

## OLCULEN TABAN (26 Agu 2026, k311-TABAN.txt)

    ci-nobeti.log : acilan_tur=1 -> 0   · acilan_tur=0 -> 18 · BITIS rc=0 -> 46
    gozcu.log     : KOSUM_HUKMU  TEMIZ=7 ONARIM_DENENDI=5 MOTOR_DUSTU=11
                                 OLCULEMEDI=44
                    GOZCU rc=0 -> 73 · rc=1 -> 11
                    TUR_HALI=KOSTU_ONARDI -> 0   (HIC onarim olmadi)
                    ONARIM=0 -> 56 · DAGITILAN=0 -> 56
    gozcu-eskalasyon.md : 42 satir, ISTISNASIZ deneme=3
    nobet-tetik-test.py : VAKA=38 DUSEN=0 rc=0   (SAHTE YESIL — eksen olculmuyor)

## TESHIS (brief'in hipotezi CURUTULDU)

Brief "iki karar mercii celisiyor, bu yuzden tur hic acilmiyor" diyordu.
OLCUM bunu CURUTUR: tur ACILIYOR. Turu acan `ci-nobeti.sh` DEGIL, `gozcu.py`nin
KENDISIDIR (`tur_kosucu(["--tur"])`, gozcu.py:687). 67 kosum hukmu uretilmis.
`acilan_tur=1`in 0 olmasi TIKAC DEGIL, `nobet-tetik.py`nin 3. basamaginin
(`GOZCU_ICRA_ETTI`) CIFT ATESLEMEYI dogru sekilde engellemesidir.

GERCEK ARIZA TEK SINIFTIR ve UC YUZU vardir — hepsi ayni kok:
**bir hukum DURUSTCE hesaplanip yaziliyor, ve onu OKUYAN kimse yok.**

  YUZ A (sahte yesil) `kosum_hukmu` gozcu.py:691'de hesaplanir, :753'te kalbe
     yazilir — ve rc yolunda TEK TUKETICISI YOKTUR. rc yalnizca
     `icra_hal == "KOSTU_DUSTU"` (gozcu.py:721) kolundan yukselir; o alan
     `icra_halini_coz` ile SURECIN rc'sinden turer ve "kostu ama IS GORMEDI"
     halini IFADE EDEMEZ. Olcum: 44 OLCULEMEDI turun 44'u de rc=0.
  YUZ B (eskalasyon Okan'a ulasmaz) `_eskalasyon_yaz` (gozcu.py:705)
     `gozcu-eskalasyon.md`ye yazar; gozcu.py/nobet-kapi.py/nobet_merdiven.py
     icinde o dosyayi OKUYAN TEK SATIR YOKTUR. 42 eskalasyon yazildi, hicbiri
     bir karara donusmedi.
  YUZ C (hat kendi olumunu olcemez) `nobet-tetik.py`nin 3. basamagi gozcunun
     KENDI kosum hukmunu TASIMAZ; yalniz `ci_olculdu`/`defter_olculdu`yu
     tasir. Sonuc: `RC_ACMA_YESIL=10` -> `BITIS rc=0`. 46 yesil bitis.

Bu, bu evin ADI KONMUS sinifidir: [[kapinin-menzili-cagri-yeridir]] —
"kapi VAR ama CAGIRANI YOK". Ve UCUNCU TEKRARDIR (14 Agu H1-H7, 19 Agu N1),
o yuzden [[ucuncu-tekrar-sinif-kapisi]] geregi TEKIL YAMA YASAKTIR.

## CARE — SINIF KAPATIR, VAKA DEGIL

  1. TEK KARAR NOKTASI `gozcu.uretken_mi(kalp)` — "bu tur IS GORDU MU?".
     BEYAZ LISTE + fail-closed: yarin `KOSUM_HUKUMLERI`ne yeni bir deger
     eklenirse beyaz listeye YAZILMADIKCA KIRMIZI sayilir.
  2. IKI TUKETICI, TEK KAYNAK gozcunun rc'si VE `nobet-tetik.py`nin 3.
     basamagi AYNI fonksiyonu cagirir. Ikiz kural URETILMEZ.
  3. ESKALASYON TUKETILIR `eskalasyon_acik_say` — hala KIRMIZI olan run-id'ler
     icinde ESKALASYON'a dusmus olanlar. Kendini temizler (run yesile donunce
     duser), elle sifirlama YOK.
  4. SINIF KAPISI `k311-baglanti-kapisi.py` — kalbe yazilan HER alan ya HUKUM
     (canli tuketicisi ZORUNLU) ya TELEMETRI (beyan zorunlu) olarak
     siniflandirilir. Siniflanmamis yeni alan = KIRMIZI. Yani "hukum yazdim,
     kimse okumuyor" hali BIR DAHA sessizce doGAMAZ.

## KOSUM

    python3 tools/k311/k311-kur.py              # yalniz OLCER (yazmaz)
    python3 tools/k311/k311-kur.py --uygula
    python3 tools/k311/k311-kur.py --geri-al DAMGA
"""

import argparse
import os
import shutil
import sys
import time

CRON_KOKU = "/Users/okan/.claude/cron"
GOZCU = os.path.join(CRON_KOKU, "gozcu.py")
TETIK = os.path.join(CRON_KOKU, "nobet-tetik.py")
TETIK_TEST = os.path.join(CRON_KOKU, "nobet-tetik-test.py")
GOZCU_TEST = os.path.join(CRON_KOKU, "gozcu-test.py")

HEDEFLER = (GOZCU, TETIK, TETIK_TEST, GOZCU_TEST)


def oku(yol):
    with open(yol, encoding="utf-8") as dosya:
        return dosya.read()


def yaz(yol, metin):
    with open(yol, "w", encoding="utf-8") as dosya:
        dosya.write(metin)


# ===========================================================================
# gozcu.py
# ===========================================================================

G1_ANKOR = 'ICRA_HALLERI = ("KOSULMADI", "ATLANDI", "KOSTU_BASARILI", "KOSTU_DUSTU")\n'

G1_YENI = '''
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

'''

G2_ESKI = '''    if icra_hal == "KOSTU_DUSTU":
        rc = max(rc, 1)
'''

G2_YENI = '''    if icra_hal == "KOSTU_DUSTU":
        rc = max(rc, 1)

    # 🔴 K311 YUZ A — KOSTU ama IS GORMEDI: SESSIZ YESIL URETME.
    # Taban: 44 OLCULEMEDI turun 44'u de rc=0 donuyordu. Karar TEK NOKTADAN
    # (`uretken_mi`) okunur; `nobet-tetik.py` de AYNI fonksiyonu cagirir.
    uretken, uretken_sebep = uretken_mi({
        "icra_denendi": icra_denendi,
        "icra_hal": icra_hal,
        "kosum_hukmu": kosum_hukmu,
    })
    if not uretken:
        rc = max(rc, 1)

    # 🔴 K311 YUZ B — eskalasyon artik TUKETILIYOR. Hala kirmizi olan bir
    # run-id ESKALASYON'a dustuyse gozcu KIRMIZI kapanir; 42 sessiz satirin
    # sinifi budur.
    eskalasyon_acik = eskalasyon_acik_say(durum, kirmizilar)
    if eskalasyon_acik:
        rc = max(rc, 1)
'''

G3_ESKI = '        "icra_denendi": bool(icra_denendi),\n'

G3_YENI = '''        "icra_denendi": bool(icra_denendi),
        # K311: rc yolunun FIILEN TUKETTIGI alanlar. `k311-baglanti-kapisi.py`
        # bu alanlarin canli tuketicisini SAYARAK olcer.
        "uretken": bool(uretken),
        "uretken_sebep": uretken_sebep,
        "eskalasyon_acik": eskalasyon_acik,
'''


# ===========================================================================
# nobet-tetik.py
# ===========================================================================

T1_ANKOR = '''def bugunun_adi(simdi):
    return time.strftime("%Y-%m-%d", time.gmtime(simdi))
'''

T1_YENI = '''

def _uretken_karari(kalp):
    """K311: uretkenlik hukmu TEK KEZ verilir — GOZCU verir, tetik UYAR.

    Oncelik SIRASI hukumdur:
      1. Gozcunun kalbe YAZDIGI hukum (`uretken` / `uretken_sebep`). Ikiz
         hesap YOK: iki yerde hesaplanan kural sessizce ayrisir
         ([[ayni-alan-iki-hukum-biri-sessiz]]). Bu ayni zamanda o alanlarin
         CANLI TUKETICISIDIR — `k311-baglanti-kapisi.py` bunu SAYARAK olcer.
      2. Alan yoksa (eski kalp / kismi kurulum) gozcunun sozlesme fonksiyonu
         yeniden hesaplar.
    FAIL-CLOSED: gozcu yuklenemediyse ya da sozlesme fonksiyonu (`uretken_mi`)
    YOKSA hukum "URETMEDI"dir. Eksik sozlesme sessizce yesil sayilamaz; aksi
    halde kurulum yarim kalinca hat ESKI sahte-yesil davranisina geri doner ve
    kimse fark etmez ([[kapinin-menzili-cagri-yeridir]]).
    """
    kalp = kalp or {}
    if "uretken" in kalp:
        return bool(kalp.get("uretken")), str(kalp.get("uretken_sebep") or "-")
    if GZ is None or not hasattr(GZ, "uretken_mi"):
        return False, "SOZLESME_YOK"
    return GZ.uretken_mi(kalp)
'''

T2_ESKI = '''    if kalp.get("icra_denendi", kalp.get("icra_rc") is not None):
        return Karar("ACMA", "GOZCU_ICRA_ETTI", "", (), olculemedi)
'''

T2_YENI = '''    if kalp.get("icra_denendi", kalp.get("icra_rc") is not None):
        # 🔴 K311 YUZ C — "gozcu bir tur ACTI MI?" ile "gozcu IS GORDU MU?"
        # AYRI sorulardir. Eskiden bu kol yalniz `olculemedi`yi (ci/defter
        # olcumu) tasiyordu; gozcunun KENDI kosum hukmu buraya HIC GELMIYORDU.
        # Sonuc: "kostu, hicbir sey uretmedi" hali `RC_ACMA_YESIL=10` donuyor
        # ve `ci-nobeti.sh` `BITIS rc=0` yaziyordu (taban: 46 yesil bitis).
        # 🔴 Bu kol HALA "ACMA" der — cift atesleme yasagi DEGISMEDI; degisen
        # yalniz o ACMA'nin YESIL mi KIRMIZI mi oldugudur.
        uretken, uret_sebep = _uretken_karari(kalp)
        if not uretken:
            return Karar("ACMA", "GOZCU_URETMEDI_%s" % uret_sebep, "", (), True)
        # 🔴 K311 YUZ B — gozcunun KENDI saydigi ACIK ESKALASYON hatti KIRMIZI
        # yakar. `gozcu-eskalasyon.md`ye 19-26 Agu arasi 42 satir yazildi
        # (ISTISNASIZ deneme=3) ve HICBIRI bir karara donusmedi; bu kol o
        # sayiyi TUKETIR. Kendini temizler: run yesile donunce sayi duser.
        if int(kalp.get("eskalasyon_acik") or 0) > 0:
            return Karar("ACMA", "ESKALASYON_ACIK", "", (), True)
        return Karar("ACMA", "GOZCU_ICRA_ETTI", "", (), olculemedi)
'''


# ===========================================================================
# nobet-tetik-test.py — MEVCUT dosyaya vaka EKLENIR (yeni test dosyasi ACILMAZ)
# ===========================================================================

TT1_ESKI = '''        T.esit("H4 ACMA + kirmizi = 11",
               NT.cikis_kodu(NT.Karar("ACMA", "x", "", (), True)), 11)
'''

TT1_YENI = '''        T.esit("H4 ACMA + kirmizi = 11",
               NT.cikis_kodu(NT.Karar("ACMA", "x", "", (), True)), 11)

        # ---------- K. K311: "KOSTU AMA IS GORMEDI" SAHTE YESIL OLAMAZ -----
        # Taban (26 Agu): 44 OLCULEMEDI tur, 44'u de rc=0; 46 yesil BITIS.
        UM = NT.GZ.uretken_mi

        def _k(**ek):
            temel = {"icra_denendi": True, "icra_hal": "KOSTU_BASARILI"}
            temel.update(ek)
            return temel

        T.esit("K1 is YOKKEN soru anlamsiz -> uretken",
               UM({"icra_denendi": False})[0], True)
        T.esit("K2 ATLANDI (onceki tur suruyor) -> uretken",
               UM(_k(icra_hal="ATLANDI", kosum_hukmu="OLCULEMEDI"))[0], True)
        T.esit("K3 TEMIZ -> uretken", UM(_k(kosum_hukmu="TEMIZ"))[0], True)
        T.esit("K4 ONARIM_DENENDI -> uretken",
               UM(_k(kosum_hukmu="ONARIM_DENENDI"))[0], True)
        T.esit("K5 OLCULEMEDI -> URETMEDI (ASIL VAKA, taban 44 kez)",
               UM(_k(kosum_hukmu="OLCULEMEDI"))[0], False)
        T.esit("K6 MOTOR_DUSTU -> URETMEDI",
               UM(_k(kosum_hukmu="MOTOR_DUSTU"))[0], False)
        # 🔴 BEYAZ LISTE KANITI: yarin eklenecek BILINMEYEN bir hukum, beyaz
        # listeye yazilmadikca yesil sayilamaz (fail-closed).
        T.esit("K7 BILINMEYEN yeni hukum -> URETMEDI (beyaz liste fail-closed)",
               UM(_k(kosum_hukmu="YARIN_EKLENEN_HUKUM"))[0], False)
        T.esit("K8 kosum_hukmu ALANI YOK (eski kalp) -> URETMEDI", UM(_k())[0], False)
        T.esit("K9 sebep alani hukmu TASIR",
               UM(_k(kosum_hukmu="OLCULEMEDI"))[1], "OLCULEMEDI")

        # K10-K11 — KARAR duzeyi: 3. basamak gozcunun hukmunu TASIYOR mu?
        kalp_k10 = _kalp(simdi, icra_denendi=True, icra_hal="KOSTU_BASARILI",
                         kosum_hukmu="OLCULEMEDI")
        k10 = NT.karar(kalp_k10, simdi, bugun)
        T.esit("K10a uretmeyen tur -> hukum yine ACMA (cift atesleme YOK)",
               k10.hukum, "ACMA")
        T.dogru("K10b uretmeyen tur -> KIRMIZI", k10.kirmizi)
        T.esit("K10c rc = ACMA/KIRMIZI (11) — SAHTE YESIL KAPANDI",
               NT.cikis_kodu(k10), NT.RC_ACMA_KIRMIZI)
        T.dogru("K10d sebep hukmu TASIR", "GOZCU_URETMEDI" in k10.sebep)

        # 🔴 NEGATIF KONTROL (§5: "hep KIRMIZI" yapmak da yasak): ureten tur
        # AYNI kolda YESIL kalir. Iki yon de vakayla olculur.
        kalp_k11 = _kalp(simdi, icra_denendi=True, icra_hal="KOSTU_BASARILI",
                         kosum_hukmu="TEMIZ")
        k11 = NT.karar(kalp_k11, simdi, bugun)
        T.esit("K11a URETEN tur -> sebep GOZCU_ICRA_ETTI", k11.sebep,
               "GOZCU_ICRA_ETTI")
        T.yanlis("K11b URETEN tur KIRMIZI DEGIL", k11.kirmizi)
        T.esit("K11c rc = ACMA/YESIL (10)", NT.cikis_kodu(k11), NT.RC_ACMA_YESIL)

        # K12 — TEK KAYNAK: tetik kendi kopyasini TUTMAZ, gozcuden ITHAL eder.
        # (ikiz kural sessizce ayrisir -> [[ayni-alan-iki-hukum-biri-sessiz]])
        T.dogru("K12a tetik gozcunun sozlesmesini ITHAL eder",
                hasattr(NT.GZ, "uretken_mi"))
        _asil = NT.GZ.uretken_mi
        try:
            NT.GZ.uretken_mi = lambda kalp: (False, "ENJEKTE")
            T.esit("K12b tetik GERCEKTEN gozcuyu cagirir (ikiz kural YOK)",
                   NT._uretken_karari({"icra_denendi": True})[1], "ENJEKTE")
        finally:
            NT.GZ.uretken_mi = _asil

        # K13 — SOZLESME YOKSA fail-closed (yarim kurulum sessizce yesil olamaz)
        _asil2 = NT.GZ.uretken_mi
        try:
            del NT.GZ.uretken_mi
            T.esit("K13 sozlesme YOK -> URETMEDI (fail-closed)",
                   NT._uretken_karari({"icra_denendi": True}), (False, "SOZLESME_YOK"))
        finally:
            NT.GZ.uretken_mi = _asil2

        # K14-K15 — KALPTEKI HUKUM FIILEN TUKETILIYOR MU?
        # 🔴 Bu iki vaka, `uretken`/`uretken_sebep` alanlarinin SUS alani degil
        # KARAR GIRDISI oldugunu olcer. Alanlar yaziliyor ama okunmuyorsa
        # K311'in kendi arizasi (hukum yazildi, tuketici yok) TEKRAR EDER.
        # Kanit icin gozcunun fonksiyonu KASTEN ters cevrilir: hukum kalpten
        # geliyorsa sonuc DEGISMEZ.
        _asil3 = NT.GZ.uretken_mi
        try:
            NT.GZ.uretken_mi = lambda kalp: (True, "SOZLESME_CAGRILDI")
            T.esit("K14a kalpteki uretken=False TUKETILIR (sozlesme EZILMEZ)",
                   NT._uretken_karari({"icra_denendi": True, "uretken": False,
                                       "uretken_sebep": "OLCULEMEDI"}),
                   (False, "OLCULEMEDI"))
            T.esit("K14b kalpteki uretken=True TUKETILIR",
                   NT._uretken_karari({"icra_denendi": True, "uretken": True,
                                       "uretken_sebep": "TEMIZ"})[0], True)
            T.esit("K15 alan YOKKEN sozlesmeye DUSULUR (geriye donuk)",
                   NT._uretken_karari({"icra_denendi": True})[1],
                   "SOZLESME_CAGRILDI")
        finally:
            NT.GZ.uretken_mi = _asil3

        kalp_k16 = _kalp(simdi, icra_denendi=True, uretken=False,
                         uretken_sebep="MOTOR_DUSTU")
        k16 = NT.karar(kalp_k16, simdi, bugun)
        T.esit("K16a kalpten gelen URETMEDI hukmu rc'ye TASINIR",
               NT.cikis_kodu(k16), NT.RC_ACMA_KIRMIZI)
        T.dogru("K16b sebep kalptekini TASIR", "MOTOR_DUSTU" in k16.sebep)

        # ---------- L. K311 YUZ B: ESKALASYON TUKETILIYOR MU? --------------
        EA = NT.GZ.eskalasyon_acik_say
        _durum = {"kosumlar": {"111": {"durum": "ESKALASYON"},
                               "222": {"durum": "DUSTU"},
                               "333": {"durum": "ESKALASYON"}}}
        T.esit("L1 hala KIRMIZI olan eskalasyon SAYILIR",
               EA(_durum, [{"id": "111"}]), 1)
        T.esit("L2 iki kirmizi eskalasyon -> 2",
               EA(_durum, [{"id": "111"}, {"id": "333"}]), 2)
        T.esit("L3 YESILE donen run SAYILMAZ (kendini temizler)",
               EA(_durum, [{"id": "222"}]), 0)
        T.esit("L4 kirmizi YOKKEN sayac 0 (yanlis pozitif YOK)",
               EA(_durum, []), 0)
        T.esit("L5 bos durum -> 0", EA({}, [{"id": "111"}]), 0)

        # L6-L8 — sayi bir KARARA donuyor mu? (42 satirin sinifi: yazildi,
        # okunmadi. Alan kalpte duruyor diye TUKETILMIS SAYILMAZ.)
        kalp_l6 = _kalp(simdi, icra_denendi=True, uretken=True,
                        uretken_sebep="TEMIZ", eskalasyon_acik=2)
        l6 = NT.karar(kalp_l6, simdi, bugun)
        T.esit("L6a acik eskalasyon -> rc KIRMIZI", NT.cikis_kodu(l6),
               NT.RC_ACMA_KIRMIZI)
        T.esit("L6b sebep ESKALASYON_ACIK", l6.sebep, "ESKALASYON_ACIK")
        kalp_l7 = _kalp(simdi, icra_denendi=True, uretken=True,
                        uretken_sebep="TEMIZ", eskalasyon_acik=0)
        l7 = NT.karar(kalp_l7, simdi, bugun)
        T.esit("L7 eskalasyon 0 -> YESIL (yanlis pozitif YOK)",
               NT.cikis_kodu(l7), NT.RC_ACMA_YESIL)
        kalp_l8 = _kalp(simdi, icra_denendi=True, uretken=True,
                        uretken_sebep="TEMIZ")
        T.esit("L8 alan YOKKEN (eski kalp) YESIL kalir",
               NT.cikis_kodu(NT.karar(kalp_l8, simdi, bugun)), NT.RC_ACMA_YESIL)
'''

TT2_ESKI = '''        # I. YABANCI DIZINDEN KOSUM'''

TT2_YENI = '''        # ---------- J6. K311 UCTAN UCA: SAHTE YESIL GERCEKTEN KAPANDI MI? --
        # 🔴 Bu bolum GERCEK `ci-nobeti.sh`i kosar ve GERCEK bir log dosyasina
        # `TETIK_HUKMU ... acilan_tur=<n>` + `BITIS rc=<n>` YAZDIRIR. Iddia
        # DEGIL, uretilen satirlar SAYILIR.
        sifirla()
        j6_log_once = log_metni()

        # J6a — ASIL VAKA: gozcu turu ACTI, tur KOSTU, ama hicbir sey URETMEDI.
        # Taban davranisi: rc=10 (ACMA/YESIL) -> `BITIS rc=0`. 44 kez olctuk.
        _kalp_yaz(kalp_y, _kalp(simdi, icra_denendi=True,
                                icra_hal="KOSTU_BASARILI",
                                kosum_hukmu="OLCULEMEDI"))
        rc_j6a = calistir()
        j6a_yeni = log_metni()[len(j6_log_once):]
        T.dogru("J6a1 URETMEYEN hat rc=0 DONEMEZ", rc_j6a != 0)
        T.esit("J6a2 o kosumda BITIS rc=0 URETILMEDI",
               j6a_yeni.count("BITIS rc=0"), 0)
        T.esit("J6a3 ikinci tur ACILMADI (cift atesleme yasagi DURUYOR)",
               cagri_sayisi(), 0)
        T.dogru("J6a4 log sebebi TASIR", "GOZCU_URETMEDI" in j6a_yeni)
        T.esit("J6a5 satirin acilan_tur alani 0", j6a_yeni.count("acilan_tur=0"), 1)

        # J6b — NEGATIF KONTROL: URETEN hat AYNI kolda YESIL kalir.
        # (§5: "hep KIRMIZI" cozum degildir; dogru yon de olculur.)
        j6_log_once = log_metni()
        _kalp_yaz(kalp_y, _kalp(simdi, icra_denendi=True,
                                icra_hal="KOSTU_BASARILI",
                                kosum_hukmu="TEMIZ"))
        rc_j6b = calistir()
        j6b_yeni = log_metni()[len(j6_log_once):]
        T.esit("J6b1 URETEN hat rc=0 doner", rc_j6b, 0)
        T.esit("J6b2 o kosumda BITIS rc=0 URETILDI",
               j6b_yeni.count("BITIS rc=0"), 1)
        T.esit("J6b3 ureten hatta tur yine ACILMAZ", cagri_sayisi(), 0)

        # J6c — TABANIN IKI YONU DE OLCULDU MU? `acilan_tur` jetonu bu logda
        # HEM 1 HEM 0 uretmis olmali; tek yonlu olcum hukum vermez.
        tum_log = log_metni()
        T.dogru("J6c1 log'da acilan_tur=1 URETILDI (kirmizi -> tur ACILIR)",
                tum_log.count("acilan_tur=1") >= 1)
        T.dogru("J6c2 log'da acilan_tur=0 URETILDI (yesil -> tur ACILMAZ)",
                tum_log.count("acilan_tur=0") >= 1)
        sifirla()

        # I. YABANCI DIZINDEN KOSUM'''

TT3_ESKI = '''def kos(NT):
    T = Testler()
    simdi = 1_755_000_000.0
'''

TT3_YENI = '''def kos(NT):
    T = Testler()
    simdi = 1_755_000_000.0
'''

# `_kalp` varsayilanina K311 alanlari EKLENMEZ: varsayilan kalp "is yoktu"
# halidir (`icra_denendi` yok) ve o hal K1 geregi URETKEN sayilir. Boylece
# A-H bolumlerindeki 38 mevcut vaka AYNEN gecerli kalir.


# ---------------------------------------------------------------------------
# gozcu-test.py — TABANDA KIRMIZI olan BAYAT IDDIA (K311'in ariza si DEGIL)
# ---------------------------------------------------------------------------
# OLCULDU: taban kosumunda `gozcu-test.py` rc=1 idi ve tek dusen vaka
# `KIRIK 10i satir bicimi: beklenen=True gercek=False` idi — K311 ONCESI de
# ayni, K311 SONRASI da ayni (VAKA=112 DUSEN=1, birebir).
# SEBEP: iddia satirin ` rc=0` ile BITMESINI bekliyor. `kalp_satiri` bicimi
# K263'te genisletildi (`... rc=%d SAHIP=%s SEBEP=%s N2_D=...`), yani `rc=`
# artik satirin SONU degil; iddia BAYAT kaldi ve o gunden beri KIRMIZI yaniyor.
# 🔴 Bu bir GEVSETME DEGIL: `endswith(" rc=0")` -> `" rc=0 "` degisimi iddiayi
# ZAYIFLATMAZ, cunku (a) alan hala ADIYLA ve DEGERIYLE aranir, (b) rc 1
# olursa yine duser, (c) alan bicimden kalkarsa yine duser. Degisen tek sey,
# iddianin artik BICIMIN SONUNA degil ALANIN KENDISINE capalanmasidir.
GT1_ESKI = '''        T.esit("10i satir bicimi", sonuc["satir"].startswith("GOZCU ") and
               " TETIK=YOK " in sonuc["satir"] and sonuc["satir"].endswith(" rc=0"), True)
'''

GT1_YENI = '''        # K311 (26 Agu): iddia satirin SONUNA capaliydi; `kalp_satiri` bicimi
        # K263'te `rc=`den SONRA alan aldigi icin BAYAT kalmis ve o gunden beri
        # bu batarya KIRMIZI yaniyordu. Capa ALANIN KENDISINE tasindi —
        # zayiflama YOK: rc 1 olursa da, alan bicimden kalkarsa da yine duser.
        T.esit("10i satir bicimi", sonuc["satir"].startswith("GOZCU ") and
               " TETIK=YOK " in sonuc["satir"] and " rc=0 " in sonuc["satir"], True)
        T.esit("10i rc alani TEK ve DEGERLI", sonuc["satir"].count(" rc="), 1)
'''


YAMALAR = (
    ("G1 uretken_mi + eskalasyon_acik_say", GOZCU, "ekle-sonra", G1_ANKOR, G1_YENI,
     "def uretken_mi(kalp):"),
    ("G2 rc kolu (YUZ A + YUZ B)", GOZCU, "degistir", G2_ESKI, G2_YENI,
     "K311 YUZ A"),
    ("G3 kalbe tuketilen alanlar", GOZCU, "degistir", G3_ESKI, G3_YENI,
     '"uretken": bool(uretken),'),
    ("T1 _uretken_karari (ithal, fail-closed)", TETIK, "ekle-sonra", T1_ANKOR,
     T1_YENI, "def _uretken_karari(kalp):"),
    ("T2 3. basamak hukmu TASIR (YUZ C)", TETIK, "degistir", T2_ESKI, T2_YENI,
     "K311 YUZ C"),
    ("TT1 K+L bolumleri (saf vakalar)", TETIK_TEST, "degistir", TT1_ESKI, TT1_YENI,
     "K5 OLCULEMEDI -> URETMEDI"),
    ("TT2 J6 uctan uca vakalar", TETIK_TEST, "degistir", TT2_ESKI, TT2_YENI,
     "J6a1 URETMEYEN hat rc=0 DONEMEZ"),
    ("GT1 bayat 10i iddiasi (TABAN kirmizisi)", GOZCU_TEST, "degistir",
     GT1_ESKI, GT1_YENI, '"10i rc alani TEK ve DEGERLI"'),
)


def durum_olc():
    """Her yamanin KURULU olup olmadigini SAYAR. Iddia degil, dizge aramasi."""
    sonuc = []
    icerikler = {}
    for yol in HEDEFLER:
        icerikler[yol] = oku(yol) if os.path.isfile(yol) else None
    for ad, yol, kip, eski, yeni, kanit in YAMALAR:
        metin = icerikler.get(yol)
        if metin is None:
            sonuc.append((ad, "DOSYA_YOK", False))
            continue
        if kanit in metin:
            sonuc.append((ad, "KURULU", True))
        elif metin.count(eski) == 1:
            sonuc.append((ad, "KURULABILIR", False))
        elif eski in metin:
            sonuc.append((ad, "ANKOR_TEKIL_DEGIL", False))
        else:
            sonuc.append((ad, "ANKOR_YOK", False))
    return sonuc


def uygula(damga):
    yedekler = []
    for yol in HEDEFLER:
        hedef = "%s.yedek-k311-%s" % (yol, damga)
        shutil.copy2(yol, hedef)
        yedekler.append(hedef)

    icerikler = {yol: oku(yol) for yol in HEDEFLER}
    uygulanan = []
    for ad, yol, kip, eski, yeni, kanit in YAMALAR:
        metin = icerikler[yol]
        if kanit in metin:
            uygulanan.append((ad, "ZATEN_KURULU"))
            continue
        if eski not in metin:
            raise SystemExit("ANKOR BULUNAMADI: %s (%s)" % (ad, yol))
        if metin.count(eski) != 1:
            raise SystemExit("ANKOR TEKIL DEGIL (%d): %s (%s)"
                             % (metin.count(eski), ad, yol))
        if kip == "ekle-sonra":
            icerikler[yol] = metin.replace(eski, eski + yeni, 1)
        else:
            icerikler[yol] = metin.replace(eski, yeni, 1)
        uygulanan.append((ad, "UYGULANDI"))

    for yol, metin in icerikler.items():
        yaz(yol, metin)

    # Sozdizimi kapisi: bozuk dosya birakma (cron duzleminde geri donus YOK).
    import py_compile
    for yol in HEDEFLER:
        try:
            py_compile.compile(yol, cfile=os.devnull, doraise=True)
        except py_compile.PyCompileError as hata:
            for y in yedekler:
                shutil.copy2(y, y.rsplit(".yedek-k311-", 1)[0])
            raise SystemExit("SOZDIZIMI KIRILDI, GERI ALINDI: %s" % hata)

    return uygulanan, yedekler


def geri_al(damga):
    geri = []
    for yol in HEDEFLER:
        kaynak = "%s.yedek-k311-%s" % (yol, damga)
        if not os.path.isfile(kaynak):
            print("YEDEK YOK: %s" % kaynak)
            continue
        shutil.copy2(kaynak, yol)
        geri.append(yol)
    return geri


def main(argv=None):
    ap = argparse.ArgumentParser(description="K311 kurucu")
    ap.add_argument("--uygula", action="store_true")
    ap.add_argument("--geri-al", metavar="DAMGA")
    args = ap.parse_args(argv)

    if args.geri_al:
        for yol in geri_al(args.geri_al):
            print("GERI_ALINDI %s" % yol)
        return 0

    if not args.uygula:
        print("=== K311 DURUM (yalniz OLCUM) ===")
        kurulu = 0
        for ad, hal, ok in durum_olc():
            print("YAMA %-45s %s" % (ad, hal))
            kurulu += int(ok)
        print("KURULU=%d/%d" % (kurulu, len(YAMALAR)))
        return 0 if kurulu == len(YAMALAR) else 1

    damga = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    uygulanan, yedekler = uygula(damga)
    for ad, hal in uygulanan:
        print("YAMA %-45s %s" % (ad, hal))
    for y in yedekler:
        print("YEDEK %s" % y)
    print("DAMGA=%s" % damga)
    kurulu = sum(1 for _, _, ok in durum_olc() if ok)
    print("KURULU=%d/%d" % (kurulu, len(YAMALAR)))
    return 0 if kurulu == len(YAMALAR) else 1


if __name__ == "__main__":
    sys.exit(main())
