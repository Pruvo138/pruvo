#!/usr/bin/env python3
"""KOR GOZ KURUCU — iki dar kalemin TEK SINIF onarimi (KraL-KorGoz-27Agu).

SINIF (mimar hukmu, 27 Agu 2026): *bir taraf degeri YAZIYOR, tuketicisi ya HIC
OKUMUYOR ya BASKA SOZLUKTEN okuyor.* Tekil yama YASAK — iki yuz TEK kurucuda.

  (a) `nobet-tetik.py::karar()` KENAR-tetikli; soru ise SEVIYE.
      `gozcu.py:876` `kirmizi_toplam` YAZAR, okuyan YOKTU (yazan=1 okuyan=0).
      TABAN OLCULDU: F2 (`kirmizi_toplam=11`) ve F3 (KONTROL, 0) BIREBIR
      `rc=10` -> `F2_F3_ESIT=1`. Ariza uzadikca "yeni" olmaktan cikip
      GORUNMEZ oluyordu.
  (b) `nobet-kapi.py::onarim_kalemleri()` YALNIZ 🔧 sayiyor.
      TABAN OLCULDU: defterin durum kolonunda 🔧 degeri **0 kez** geciyor;
      kanonik deger `ACIK` ve 11 satir tasiyor. Yani okuyucu, defterde HIC
      BULUNMAYAN bir degeri ariyordu -> `ACIK_KALEM=0`, `DAGITILAN=0`,
      `ONARIM=0`, ve `kat_sayaci` bu liste uzerinde dondugu icin `kat_okan`
      0->1 YAPISAL OLARAK ULASILAMAZ.
      Ayni defteri IKINCI okuyucu (`tools/parti-borc-kapisi.py`) `ACIK=12`,
      UCUNCU okuyucu (ciplak kolon-5) `ACIK=11 + BILINMIYOR=3` okuyor.

🔴 SINIF ONARIMI (tekil yama DEGIL): kume artik ELLE YAZILMIS bir literal
degil, defterin KANONIK durum kumesinin (`DURUM_DEGERLERI`) TAM PARTISYONUDUR
ve partisyon butunlugu MODUL YUKLENIRKEN fail-loud olculur. Yarin deftere yeni
bir durum degeri eklenirse bu dosya onu SESSIZCE "kapali" saymaz — patlar.
Ayrica hicbir kovaya girmeyen satirlar (`BILINMIYOR`, taban=3) artik her turda
SAYIYLA basilir; sessiz dusme sinifi kapanir.

⚖️ DONDURMA EMRI KORUNUR: burada DAGITIM kolu DIRILTILMEZ. (a) yalniz ACMA
hukmunun YESIL mi KIRMIZI mi oldugunu degistirir — `karar()`in 4. basamagi
(yeni kirmizi -> AC) ve cift-atesleme yasagi AYNEN durur.

KULLANIM
  python3 korgoz_kur.py --kuru            # capalari DOGRULA, dosyaya dokunma
  python3 korgoz_kur.py --kur             # yedek al + yamala
  python3 korgoz_kur.py --kur --hedef DIR # DIR icindeki KOPYALARI yamala
  python3 korgoz_kur.py --geri-al DAMGA   # .yedek-korgoz-<DAMGA> geri yukle

Cikis: 0 = tamam · 1 = capa/dogrulama DUSTU (fail-loud) · 2 = kullanim hatasi.
"""

import argparse
import os
import shutil
import sys
import time

CRON = "/Users/okan/.claude/cron"
MARKER = "KORGOZ_K311_SEVIYE"          # (a) kurulu mu?
MARKER_B = "KORGOZ_K311_SOZLUK"        # (b) kurulu mu?


# ==========================================================================
# (a) nobet-tetik.py
# ==========================================================================
A1_CAPA = "def karar(kalp, simdi, bugun, bayat_tavani=None):"

A1_YENI = '''def seviye_kirmizisi(kalp):
    """KORGOZ_K311_SEVIYE — "SU AN kac kirmizi DURUYOR?" (SEVIYE, kenar DEGIL).

    `gozcu.py` kalbe `kirmizi_toplam` YAZAR; 27 Agu 2026'ya kadar bu alanin
    OKUYANI YOKTU (yazan=1 okuyan=0; kiyas `yeni_kirmizi` 1/1). Olculmus
    sonuc: F2 (`kirmizi_toplam=11`, 11 duran kirmizi) ile F3 (KONTROL, 0
    kirmizi) BIREBIR ayni ciktiyi veriyordu -> `rc=10` ("ACMA, kirmizi YOK").
    4,7 saatlik yayin kesintisi boyunca hat bu yuzden "kirmizi YOK" dedi:
    kirmiziyi GORMEDI degil, GORDU ve `yeni_kirmizilar()` filtresinde ELEDI
    ([[kenar-tetikli-kol-seviye-sorusunu-cevaplayamaz]]).

    🔴 BU KOL TUR ACMAZ. Dondurma emri yururlukte; degisen yalniz ACMA
    hukmunun YESIL mi KIRMIZI mi oldugudur.

    FAIL-CLOSED: alan YOKSA (eski kalp / yarim kurulum) SESSIZ SIFIR
    URETILMEZ -> -1 doner ve cagiran bunu OLCULEMEDI sayar. Sessiz sifir,
    tam da kapatmaya calistigimiz korlugun kendisidir.
    """
    kalp = kalp or {}
    if "kirmizi_toplam" not in kalp:
        return -1
    try:
        return max(0, int(kalp.get("kirmizi_toplam") or 0))
    except (TypeError, ValueError):
        return -1


def seviye_karari(kalp):
    """SEVIYE kolunun TEK KARAR NOKTASI. Doner: Karar ya da None (kol susar).

    `karar()` merdiveninde IKI yerde cagrilir (3. basamagin ici + kuyruk);
    ikiz kural URETILMEZ — ikiz kural sessizce ayrisir
    ([[ayni-alan-iki-hukum-biri-sessiz]]). Mutant (`M-SEVIYE`) BU fonksiyonu
    hedefler: oldurulunce F2 yeniden F3'e esitlenir ve F4 DEGISMEZ.
    """
    seviye = seviye_kirmizisi(kalp)
    if seviye < 0:
        return Karar("ACMA", "SEVIYE_OLCULEMEDI", "", (), True)
    if seviye > 0:
        return Karar("ACMA", "SEVIYE_KIRMIZI_%d" % seviye, "", (), True)
    return None


''' + A1_CAPA

A2_CAPA = '''        if int(kalp.get("eskalasyon_acik") or 0) > 0:
            return Karar("ACMA", "ESKALASYON_ACIK", "", (), True)
        return Karar("ACMA", "GOZCU_ICRA_ETTI", "", (), olculemedi)'''

A2_YENI = '''        if int(kalp.get("eskalasyon_acik") or 0) > 0:
            return Karar("ACMA", "ESKALASYON_ACIK", "", (), True)
        # 3b. KORGOZ_K311_SEVIYE — "gozcu bir tur ACTI MI?" ile "SU AN kac
        # kirmizi DURUYOR?" AYRI sorulardir. Duran kirmizi, cozulmusle ayni
        # kovada kalmaz. Hukum HALA "ACMA" (cift atesleme yasagi DEGISMEDI).
        _seviye = seviye_karari(kalp)
        if _seviye is not None:
            return _seviye
        return Karar("ACMA", "GOZCU_ICRA_ETTI", "", (), olculemedi)'''

A3_CAPA = '''    # 7. Yesil: tur ACILMAZ.
    return Karar("ACMA", "YESIL", "", (), False)'''

A3_YENI = '''    # 6b. KORGOZ_K311_SEVIYE — yeni kirmizi YOK ama DURAN kirmizi VAR.
    # Bu basamak 6'dan SONRA gelir: olcum yapilamadiysa `kirmizi_toplam`
    # zaten guvenilmezdir, OLCULEMEDI daha dogru bir cevaptir.
    _seviye = seviye_karari(kalp)
    if _seviye is not None:
        return _seviye

    # 7. Yesil: tur ACILMAZ. (Gercekten sakin hat BOS TUR ACMAZ — kol
    # "hep AC"a cevrilmedi; F3 KONTROL fiksturu bunu her koşumda olcer.)
    return Karar("ACMA", "YESIL", "", (), False)'''

A4_CAPA = "      7.   yesil                   -> ACMA"
A4_YENI = ("      6b.  DURAN kirmizi (SEVIYE) -> ACMA + KIRMIZI (tur ACILMAZ)\n"
           "      7.   yesil                   -> ACMA")


# ==========================================================================
# (b) nobet-kapi.py
# ==========================================================================
B1_CAPA = '''DURUM_DEGERLERI = ("KAPANDI", "OKAN-KAPISI", "UCUSTA", "ACIK")
ONARIM_DURUMU = "\\U0001f527"  # 🔧'''

B1_YENI = '''DURUM_DEGERLERI = ("KAPANDI", "OKAN-KAPISI", "UCUSTA", "ACIK")
ONARIM_DURUMU = "\\U0001f527"  # 🔧

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
# --- KORGOZ_K311_SOZLUK sonu ----------------------------------------------'''

B2_CAPA = '''def onarim_kalemleri(kalemler):
    """H1/H4 anlaminda ACIK kalem = durumu 🔧 olan satir."""
    return [k for k in kalemler if k["durum"] == ONARIM_DURUMU]'''

B2_YENI = '''def onarim_kalemleri(kalemler):
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
    return [k for k in kalemler if k["durum"] not in bilinen]'''

B3_CAPA = '''    satirlar.append("ACIK_KALEM=%d" % acik)'''

B3_YENI = '''    satirlar.append("ACIK_KALEM=%d" % acik)
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
            "%s(%s)" % (k["id"], k["durum"]) for k in _bilinmeyen))'''


# ==========================================================================
# (c) VAKALAR MEVCUT BATARYALARA EKLENIR — yeni test dosyasi ACILMAZ, taban
#     kacirilmaz. `nobet-tetik-test.py` (a) ekseni · `nobet-kat-kovasi-test.py`
#     (b) ekseni; ikincisi `testler.py` paket listesinde ZATEN kosuyor.
# ==========================================================================
C1_CAPA = '''        T.esit("A5 saf karar YESIL", NT.karar(_kalp(simdi), simdi, bugun),
               NT.Karar("ACMA", "YESIL", "", (), False))'''

C1_YENI = C1_CAPA + '''

        # ---------- S. SEVIYE KOLU (KORGOZ_K311_SEVIYE, 27 Agu 2026) --------
        # 🔴 TABAN OLCULDU (onarimdan ONCE, birebir): F1=10 F2=10 F3=10 F4=0.
        # Yani F2 (11 DURAN kirmizi) ile F3 (KONTROL, 0 kirmizi) AYNI ciktiyi
        # veriyordu; `kirmizi_toplam` yazan=1 okuyan=0'di. Ariza uzadikca
        # "yeni" olmaktan cikip GORUNMEZ oluyordu — 4,7 saatlik yayin
        # kesintisinde hat bu yuzden 18 turda "kirmizi YOK" dedi.
        # ⚖️ DONDURMA: bu kol TUR ACMAZ; degisen yalniz ACMA hukmunun rengi.
        def _seviye_rc(kalp):
            return NT.cikis_kodu(NT.karar(kalp, simdi, bugun))

        s_f1 = _kalp(simdi, kirmizi_toplam=11, icra_denendi=True,
                     icra_hal="KOSTU", kosum_hukmu="TEMIZ", uretken=True,
                     uretken_sebep="TEMIZ")
        s_f2 = _kalp(simdi, kirmizi_toplam=11)
        s_f3 = _kalp(simdi, kirmizi_toplam=0)
        s_f4 = _kalp(simdi, tetik="CI_KIRMIZI", hedef_run="99887766",
                     yeni_kirmizi=1, kirmizi_toplam=1)
        T.esit("S1 F1 gozcu icra etti + 11 DURAN kirmizi -> ACMA+KIRMIZI",
               _seviye_rc(s_f1), NT.RC_ACMA_KIRMIZI)
        T.esit("S2 F2 11 DURAN kirmizi -> ACMA+KIRMIZI",
               _seviye_rc(s_f2), NT.RC_ACMA_KIRMIZI)
        T.esit("S3 F3 KONTROL 0 kirmizi -> ACMA+YESIL (sakin hat BOS TUR ACMAZ)",
               _seviye_rc(s_f3), NT.RC_ACMA_YESIL)
        T.dogru("S4 F2 != F3 — kol artik KENAR degil SEVIYE okuyor",
                _seviye_rc(s_f2) != _seviye_rc(s_f3))
        T.esit("S5 F4 gercek YENI kirmizi -> TUR ACILIR (4. basamak DEGISMEDI)",
               _seviye_rc(s_f4), NT.RC_AC_YESIL)
        T.yanlis("S6 duran kirmizida 'sebep=YESIL' BASILMAZ",
                 "sebep=YESIL" in NT.karar_satiri(NT.karar(s_f2, simdi, bugun)))
        T.dogru("S7 duran kirmizida KIRMIZI=1 basilir",
                "KIRMIZI=1" in NT.karar_satiri(NT.karar(s_f2, simdi, bugun)))
        T.dogru("S8 SEVIYE kolu TUR ACMAZ (dondurma emri korunur)",
                NT.karar(s_f2, simdi, bugun).hukum == "ACMA")
        # FAIL-CLOSED: alan YOKSA sessiz sifir URETILMEZ — sessiz sifir tam da
        # kapatmaya calistigimiz korlugun kendisidir.
        s_eksik = _kalp(simdi)
        s_eksik.pop("kirmizi_toplam", None)
        T.esit("S9 kirmizi_toplam alani YOK -> SEVIYE_OLCULEMEDI",
               NT.karar(s_eksik, simdi, bugun).sebep, "SEVIYE_OLCULEMEDI")
        T.esit("S10 bozuk deger -> SEVIYE_OLCULEMEDI",
               NT.karar(_kalp(simdi, kirmizi_toplam="abc"), simdi, bugun).sebep,
               "SEVIYE_OLCULEMEDI")'''


C2_CAPA = "def _batarya(nk, yol, ek):"

C2_YENI = '''def bolum_g(nk, ek=""):
    """KORGOZ_K311_SOZLUK — ACIK KALEM SOZLUGU TEK KAYNAK (27 Agu 2026).

    TABAN OLCULDU: `onarim_kalemleri()` YALNIZ 🔧 sayiyordu ve defterin durum
    KOLONUNDA 🔧 degeri **0 kez** geciyordu -> liste her turda BOS
    (`ACIK_KALEM=0` x 63 tur). Kanonik deger `ACIK`ti ve 11 satir tasiyordu.
    """
    print("--- BOLUM G%s: ACIK KALEM SOZLUGU (KORGOZ_K311_SOZLUK) ---" % ek)

    def _durumlu(kimlik, durum):
        kalem = _kalem(nk, kimlik, M_K77)
        kalem["durum"] = durum
        kalem["durum_ham"] = durum
        return kalem

    kume = [_durumlu("K901", "ACIK"), _durumlu("K902", nk.ONARIM_DURUMU),
            _durumlu("K903", "UCUSTA"), _durumlu("K904", "OKAN-KAPISI"),
            _durumlu("K905", "KAPANDI"), _durumlu("K906", "DEVREDILDI (ArTisT)")]
    onarilacak = [k["id"] for k in nk.onarim_kalemleri(kume)]
    vaka("G1-ACIK-sayiliyor%s" % ek, "VAR",
         "VAR" if "K901" in onarilacak else "YOK")
    vaka("G2-onarim-emojisi-sayiliyor%s" % ek, "VAR",
         "VAR" if "K902" in onarilacak else "YOK")
    # UCUSTA/OKAN-KAPISI ACIK ama SAHIPLI: yeniden dagitmak ayni isi iki kez
    # actirir (UCUSTA'yi bir cip tasiyor; OKAN-KAPISI insan karari).
    vaka("G3-UCUSTA-dagitilmaz%s" % ek, "YOK",
         "VAR" if "K903" in onarilacak else "YOK")
    vaka("G4-OKAN-KAPISI-dagitilmaz%s" % ek, "YOK",
         "VAR" if "K904" in onarilacak else "YOK")
    vaka("G5-KAPANDI-sayilmaz%s" % ek, "YOK",
         "VAR" if "K905" in onarilacak else "YOK")
    vaka("G6-onarilacak-adedi%s" % ek, 2, len(onarilacak))
    vaka("G7-sahipli-adedi%s" % ek, 2, len(nk.sahipli_kalemler(kume)))
    # 🔴 Hicbir kovaya girmeyen satir SESSIZ DUSMEZ (canli defterde 3 tane var).
    vaka("G8-bilinmeyen-gorunur%s" % ek, "K906",
         ",".join(k["id"] for k in nk.bilinmeyen_durumlu_kalemler(kume)))
    kanonik = set(nk.DURUM_DEGERLERI) | {nk.ONARIM_DURUMU}
    birlesim = (set(nk.ONARILACAK_DURUMLAR) | set(nk.SAHIPLI_DURUMLAR)
                | set(nk.KAPALI_DURUMLAR_DEFTER))
    vaka("G9-partisyon-tam%s" % ek, "TAM",
         "TAM" if kanonik == birlesim else "EKSIK")
    # CANLI defter, BAGIMSIZ okuyucu: ciplak kolon-5 taramasi ile okuyucunun
    # sayisi ESIT olmali. Defter tamamen kapanirsa ikisi de 0 olur — bu vaka
    # komsuyu kirmiziya YAKMAZ.
    ham_acik = 0
    try:
        with open(DEFTER_YOLU, encoding="utf-8") as _d:
            for _s in _d:
                if not _s.startswith("| K"):
                    continue
                # 🔴 K382 kanonik BOLUCU (nk uzerinden tek kaynaktan gelir).
                # Bagimsizlik iddiasi DURUM SOZLUGU duzlemindedir (asagidaki
                # literal), AYIRICI duzleminde DEGIL.
                _kol = nk.hucrelere_bol(_s)
                if len(_kol) < 7:
                    continue
                if _kol[5].strip() in nk.ONARILACAK_DURUMLAR:
                    ham_acik += 1
    except OSError:
        ham_acik = -1
    vaka("G10-canli-ciplak-grep-esit%s" % ek, ham_acik,
         len(nk.onarim_kalemleri(nk.defter_oku())) if ham_acik >= 0 else -1)


# KORGOZ_K311_SOZLUK mutantlari: IKI hedef-kol atifli + BIR kontrol.
MUTANTLAR = MUTANTLAR + (
    ("M8_SOZLUK_TABANA_DONDU",
     'ONARILACAK_DURUMLAR = (ONARIM_DURUMU, "ACIK")\\n'
     'SAHIPLI_DURUMLAR = ("UCUSTA", "OKAN-KAPISI")\\n'
     'KAPALI_DURUMLAR_DEFTER = ("KAPANDI",)\\n',
     'ONARILACAK_DURUMLAR = (ONARIM_DURUMU,)\\n'
     'SAHIPLI_DURUMLAR = ("UCUSTA", "OKAN-KAPISI")\\n'
     'KAPALI_DURUMLAR_DEFTER = ("KAPANDI", "ACIK")\\n',
     ("G1-", "G6-", "G10-"), False),
    ("M9_BILINMEYEN_KOL_KALDIRILDI",
     "    return [k for k in kalemler if k[\\"durum\\"] not in bilinen]",
     "    return []",
     ("G8-",), False),
    ("M10_KONTROL_SOZLUK",
     "# --- KORGOZ_K311_SOZLUK sonu",
     "# --- KORGOZ_K311_SOZLUK sonu (KONTROL MUTANTI)",
     (), True),
)


def _batarya(nk, yol, ek):'''

C3_CAPA = '''    bolum_f(nk, ek)
    bolum_e(yol, ek)
    return list(VAKALAR)'''

C3_YENI = '''    bolum_f(nk, ek)
    bolum_g(nk, ek)
    bolum_e(yol, ek)
    return list(VAKALAR)'''


# --------------------------------------------------------------------------
# EK YAMA (27 Agu, mutasyon kolu OLCTU): G10 TOTOLOJIKTI.
# `--mutasyon` kosuldu: M8_SOZLUK_TABANA_DONDU G1 ve G6'yi oldurdu ama G10'u
# OLDUREMEDI (`tum_dusen=2`). Sebep: G10 karsilastirdigi kumeyi
# (`nk.ONARILACAK_DURUMLAR`) BIZZAT o kumeyi degistiren mutanttan okuyordu —
# iki taraf birlikte kayiyor, vaka hicbir zaman kirmizi yanamiyor.
# 🔴 IKINCI GORUS OLMASI GEREKEN VAKA, BIRINCI GORUSU TEKRAR EDIYORDU
# ([[kabul-fiksturu-yasagi-kutsar]] ailesi). Duzeltme: bu TEK yerde literal
# BILEREK sabitlenir — vakanin isi bagimsiz bir okuyucu olmaktir.
# --------------------------------------------------------------------------
G10_CAPA = '''                if _kol[5].strip() in nk.ONARILACAK_DURUMLAR:
                    ham_acik += 1'''

G10_YENI = '''                # 🔴 LITERAL BILEREK SABIT — bu vaka BAGIMSIZ IKINCI GORUSTUR.
                # `nk.ONARILACAK_DURUMLAR` okunursa mutant iki tarafi birden
                # kaydirir ve vaka hicbir zaman kirmizi yanmaz (olculdu: M8
                # G1+G6'yi oldurdu, G10'u OLDUREMEDI).
                if _kol[5].strip() in ("ACIK", "\\U0001f527"):
                    ham_acik += 1'''

EK_YAMALAR = {
    "nobet-kat-kovasi-test.py": [
        ("G10 totoloji onarimi", G10_CAPA, G10_YENI),
    ],
}


YAMALAR = {
    "nobet-tetik.py": [
        ("A4 merdiven docstring", A4_CAPA, A4_YENI),
        ("A1 seviye_kirmizisi + seviye_karari", A1_CAPA, A1_YENI),
        ("A2 3. basamak seviye kolu", A2_CAPA, A2_YENI),
        ("A3 kuyruk seviye kolu", A3_CAPA, A3_YENI),
    ],
    "nobet-kapi.py": [
        ("B1 durum partisyonu", B1_CAPA, B1_YENI),
        ("B2 onarim_kalemleri", B2_CAPA, B2_YENI),
        ("B3 tur ciktisi", B3_CAPA, B3_YENI),
    ],
    "nobet-tetik-test.py": [
        ("C1 S bolumu (seviye vakalari)", C1_CAPA, C1_YENI),
    ],
    "nobet-kat-kovasi-test.py": [
        ("C2 G bolumu + mutantlar", C2_CAPA, C2_YENI),
        ("C3 _batarya kaydi", C3_CAPA, C3_YENI),
    ],
}


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def _yaz(yol, metin):
    gecici = yol + ".korgoz-tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        f.write(metin)
    os.replace(gecici, yol)


def dosya_yamala(yol, adimlar, kuru, satirlar):
    metin = _oku(yol)
    ad = os.path.basename(yol)
    if MARKER in metin or MARKER_B in metin:
        satirlar.append("YAMA %s ZATEN_KURULU (marker VAR) — atlandi" % ad)
        return True, metin, False
    tamam = True
    for etiket, capa, yeni in adimlar:
        adet = metin.count(capa)
        satirlar.append("CAPA %s :: %s adet=%d" % (ad, etiket, adet))
        if adet != 1:
            satirlar.append("CAPA_DUSTU %s :: %s beklenen=1 gercek=%d" % (
                ad, etiket, adet))
            tamam = False
            continue
        metin = metin.replace(capa, yeni, 1)
    if not tamam:
        return False, metin, False
    if kuru:
        satirlar.append("KURU %s — capalar TAMAM, dosya DEGISMEDI" % ad)
        return True, metin, False
    return True, metin, True


def main(argv=None):
    ap = argparse.ArgumentParser(description="KOR GOZ kurucu")
    ap.add_argument("--kuru", action="store_true")
    ap.add_argument("--kur", action="store_true")
    ap.add_argument("--hedef", default=CRON,
                    help="yamalanacak dizin (varsayilan canli ~/.claude/cron)")
    ap.add_argument("--geri-al", default="", metavar="DAMGA")
    ap.add_argument("--ek-yama", action="store_true",
                    help="kurulum SONRASI onarimlar (marker muafiyeti YOK)")
    args = ap.parse_args(argv)

    satirlar = []
    hedef = os.path.abspath(args.hedef)

    if args.geri_al:
        rc = 0
        for ad in YAMALAR:
            yedek = os.path.join(hedef, "%s.yedek-korgoz-%s" % (ad, args.geri_al))
            canli = os.path.join(hedef, ad)
            if not os.path.exists(yedek):
                satirlar.append("GERI_AL_DUSTU yedek YOK: %s" % yedek)
                rc = 1
                continue
            shutil.copy2(yedek, canli)
            satirlar.append("GERI_ALINDI %s <- %s" % (canli, yedek))
        print("\n".join(satirlar))
        return rc

    if args.ek_yama:
        damga = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        rc = 0
        for ad, adimlar in EK_YAMALAR.items():
            yol = os.path.join(hedef, ad)
            metin = _oku(yol)
            for etiket, capa, yeni in adimlar:
                adet = metin.count(capa)
                satirlar.append("EK_CAPA %s :: %s adet=%d" % (ad, etiket, adet))
                if adet != 1:
                    satirlar.append("EK_CAPA_DUSTU %s :: %s (zaten kurulu ya da "
                                    "capa kaymis)" % (ad, etiket))
                    rc = 1
                    continue
                metin = metin.replace(capa, yeni, 1)
            if rc == 0:
                shutil.copy2(yol, "%s.yedek-korgoz-%s" % (yol, damga))
                _yaz(yol, metin)
                satirlar.append("EK_YAMALANDI %s (yedek damgasi=%s)" % (yol, damga))
        satirlar.append("HUKUM=%s" % ("TAMAM" if rc == 0 else "EK_CAPA_DUSTU"))
        print("\n".join(satirlar))
        return rc

    if not (args.kuru or args.kur):
        ap.print_help()
        return 2

    damga = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    satirlar.append("KORGOZ_KURUCU hedef=%s damga=%s mod=%s"
                    % (hedef, damga, "KURU" if args.kuru else "KUR"))

    hazir = {}
    tamam = True
    for ad, adimlar in YAMALAR.items():
        yol = os.path.join(hedef, ad)
        if not os.path.isfile(yol):
            satirlar.append("DOSYA_YOK %s" % yol)
            tamam = False
            continue
        ok, metin, yazilacak = dosya_yamala(yol, adimlar, args.kuru, satirlar)
        tamam = tamam and ok
        if yazilacak:
            hazir[yol] = metin

    if not tamam:
        satirlar.append("HUKUM=CAPA_DUSTU — HICBIR DOSYA DEGISTIRILMEDI")
        print("\n".join(satirlar))
        return 1

    # 🔴 Iki dosya da hazir olmadan HICBIRI yazilmaz: yarim kurulum, kapatmaya
    # calistigimiz "bir taraf degisti, tuketici eski kaldi" sinifinin ta kendisi.
    for yol, metin in hazir.items():
        yedek = "%s.yedek-korgoz-%s" % (yol, damga)
        shutil.copy2(yol, yedek)
        _yaz(yol, metin)
        satirlar.append("YAMALANDI %s (yedek=%s)" % (yol, os.path.basename(yedek)))

    satirlar.append("YEDEK_DAMGASI=%s" % damga)
    satirlar.append("HUKUM=TAMAM yamalanan=%d" % len(hazir))
    print("\n".join(satirlar))
    return 0


if __name__ == "__main__":
    sys.exit(main())
