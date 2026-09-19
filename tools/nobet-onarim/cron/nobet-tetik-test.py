#!/usr/bin/env python3
"""NOBET TETIGI KABUL TESTI — spec N1 §2'deki DAVRANIS olcutlerinin fiksturu.

Her bolum bir kabul olcutune capalidir:
  A = YESIL GUN SIFIR TUR · B = KIRMIZI TEK TUR · C = GUNLUK 24 SAATTE 1
  D = FAIL-LOUD (olu gozcu sessiz kalamaz) · E = cift atesleme yasagi
  F = OLCULEMEDI != YESIL · G = damga hijyeni · H = cikis kodu sozlesmesi

Mutasyon kosucusu `kos(NT)` fonksiyonunu MUTANT modulle cagirir — bu yuzden
testler modulu global import'tan DEGIL, PARAMETREDEN alir.
Uctan uca kabuk kosumu (J) mutant'a acilmaz; `main()` icinden ayri cagrilir.

Cikis: `VAKA=<n> DUSEN=<n>`; tumu gecmezse rc=1.
"""

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time

KOK = os.path.dirname(os.path.abspath(__file__))
TETIK_YOLU = os.path.join(KOK, "nobet-tetik.py")
CI_NOBETI_YOLU = os.path.join(KOK, "ci-nobeti.sh")


class Testler:
    def __init__(self):
        self.gecen = 0
        self.toplam = 0
        self.hatalar = []

    def esit(self, ad, gercek, beklenen):
        self.toplam += 1
        if gercek == beklenen:
            self.gecen += 1
        else:
            self.hatalar.append("%s: beklenen=%r gercek=%r" % (ad, beklenen, gercek))

    def dogru(self, ad, deger):
        self.esit(ad, bool(deger), True)

    def yanlis(self, ad, deger):
        self.esit(ad, bool(deger), False)


def _kalp(simdi, **ek):
    """Varsayilan = SAGLIKLI + YESIL kalp. Vakalar yalniz farki yazar."""
    temel = {
        "damga": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(simdi)),
        "epok": simdi,
        "tetik": "YOK",
        "llm_turu": False,
        "yeni_kirmizi": 0,
        "kirmizi_toplam": 0,
        "hedef_run": "",
        "dagitilabilir": 0,
        "kat_mimar": 0,
        "kat_okan": 0,
        "kat_isci": 0,
        "gunluk_gerekli": False,
        "artik_silinen": 0,
        "taban_alinan": 0,
        "ci_olculdu": True,
        "ci_sebep": "TAMAM",
        "defter_olculdu": True,
        "icra_rc": None,
        "rc": 0,
        "kuru": False,
    }
    temel.update(ek)
    return temel


def _kalp_yaz(yol, veri):
    with open(yol, "w", encoding="utf-8") as dosya:
        json.dump(veri, dosya, ensure_ascii=False)


def _damgalar(dizin):
    try:
        return sorted(a for a in os.listdir(dizin) if a.endswith(".tuketildi"))
    except OSError:
        return []


def kos(NT):
    T = Testler()
    simdi = 1_755_000_000.0
    bugun = time.strftime("%Y-%m-%d", time.gmtime(simdi))
    kok = tempfile.mkdtemp(prefix="tetik-test-")
    try:
        def ortam(ad):
            alt = os.path.join(kok, ad)
            os.makedirs(os.path.join(alt, "kilit"), exist_ok=True)
            return (os.path.join(alt, "kalp.json"),
                    os.path.join(alt, "kilit"),
                    os.path.join(alt, "gozcu-cron.log"))

        # ---------- A. YESIL GUN = SIFIR TUR --------------------------------
        kalp_y, kilit_y, log_y = ortam("A")
        acilan = 0
        satir_sayaci = 0
        rc_kumesi = set()
        for i in range(4):
            an = simdi + i * 900
            _kalp_yaz(kalp_y, _kalp(an))
            satirlar, rc = NT.kos(simdi=an, kalp_yolu=kalp_y, kilit_dizini=kilit_y,
                                  gozcu_log=log_y)
            rc_kumesi.add(rc)
            if any(s.startswith("TUR ACILIYOR") for s in satirlar):
                acilan += 1
            if any("TUR ACILMADI sebep=YESIL" in s for s in satirlar):
                satir_sayaci += 1
        T.esit("A1 yesil 4 kosum -> acilan tur 0", acilan, 0)
        T.esit("A2 4x 'TUR ACILMADI sebep=YESIL'", satir_sayaci, 4)
        T.esit("A3 rc daima ACMA_YESIL", rc_kumesi, {NT.RC_ACMA_YESIL})
        T.esit("A4 damga URETILMEDI", _damgalar(kilit_y), [])
        T.esit("A5 saf karar YESIL", NT.karar(_kalp(simdi), simdi, bugun),
               NT.Karar("ACMA", "YESIL", "", (), False))

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
               "SEVIYE_OLCULEMEDI")

        # ---------- B. KIRMIZI = TEK TUR ------------------------------------
        kalp_y, kilit_y, log_y = ortam("B")
        kirmizi_kalp = _kalp(simdi, tetik="CI_KIRMIZI", llm_turu=True,
                             yeni_kirmizi=3, kirmizi_toplam=9,
                             hedef_run="32268266710")
        _kalp_yaz(kalp_y, kirmizi_kalp)
        satirlar1, rc1 = NT.kos(simdi=simdi, kalp_yolu=kalp_y, kilit_dizini=kilit_y,
                                gozcu_log=log_y)
        T.esit("B1 ilk kosum ACAR", rc1, NT.RC_AC_YESIL)
        T.dogru("B1b satirda sebep=CI_KIRMIZI",
                any("TUR ACILIYOR sebep=CI_KIRMIZI" in s for s in satirlar1))
        T.esit("B2 damga kondu", _damgalar(kilit_y),
               ["kirmizi_32268266710.tuketildi"])
        satirlar2, rc2 = NT.kos(simdi=simdi + 60, kalp_yolu=kalp_y,
                                kilit_dizini=kilit_y, gozcu_log=log_y)
        T.esit("B3 AYNI run-id ikinci kez ACMAZ", rc2, NT.RC_ACMA_YESIL)
        T.dogru("B3b sebep=CI_KIRMIZI_TUKETILDI",
                any("TUR ACILMADI sebep=CI_KIRMIZI_TUKETILDI" in s for s in satirlar2))
        acilan_b = 0
        for i in range(5):
            satirlar, _rc = NT.kos(simdi=simdi + 120 + i * 60, kalp_yolu=kalp_y,
                                   kilit_dizini=kilit_y, gozcu_log=log_y)
            if any(s.startswith("TUR ACILIYOR") for s in satirlar):
                acilan_b += 1
        T.esit("B4 5 kosum daha -> 0 tur", acilan_b, 0)
        _kalp_yaz(kalp_y, _kalp(simdi, tetik="CI_KIRMIZI", llm_turu=True,
                                yeni_kirmizi=1, hedef_run="99999"))
        _satirlar, rc_b5 = NT.kos(simdi=simdi + 600, kalp_yolu=kalp_y,
                                  kilit_dizini=kilit_y, gozcu_log=log_y)
        T.esit("B5 FARKLI run-id yeniden ACAR (kapi kor susturucu DEGIL)",
               rc_b5, NT.RC_AC_YESIL)

        # ---------- C. GUNLUK TUR = 24 SAATTE TAM 1 -------------------------
        kalp_y, kilit_y, log_y = ortam("C")
        gunluk_kalp = _kalp(simdi, tetik="GUNLUK_DEFTER", llm_turu=True,
                            gunluk_gerekli=True)
        _kalp_yaz(kalp_y, gunluk_kalp)
        _s, rc_c1 = NT.kos(simdi=simdi, kalp_yolu=kalp_y, kilit_dizini=kilit_y,
                           gozcu_log=log_y)
        T.esit("C1 gunluk tur ACILIR", rc_c1, NT.RC_AC_YESIL)
        # Uretimde gozcu HER dongude TAZE kalp yazar; fikstur de yazmali. Bayat
        # kalp birakmak C2'yi FAIL-LOUD koluna dusurur (rc=11) — olculen sey degisir.
        _kalp_yaz(kalp_y, _kalp(simdi + 3600, tetik="GUNLUK_DEFTER", llm_turu=True,
                                gunluk_gerekli=True))
        _s, rc_c2 = NT.kos(simdi=simdi + 3600, kalp_yolu=kalp_y,
                           kilit_dizini=kilit_y, gozcu_log=log_y)
        T.esit("C2 ayni gun ikinci kez ACILMAZ", rc_c2, NT.RC_ACMA_YESIL)
        # C3/C4 TEMIZ ortamda: C1 zaten `gunluk:<gun>` damgasini tuketti, ayni
        # kilit dizininde 24 saatlik pencere olculemez (fikstur kendi kendini
        # susturur). Yeni ortam = pencerenin gercek sayimi.
        kalp_y, kilit_y, log_y = ortam("C3")
        gun_basi = simdi - (simdi % 86400)
        acilan_c = 0
        for saat in range(24):
            an = gun_basi + saat * 3600 + 420
            _kalp_yaz(kalp_y, _kalp(an, tetik="GUNLUK_DEFTER", llm_turu=True,
                                    gunluk_gerekli=True))
            satirlar, _rc = NT.kos(simdi=an, kalp_yolu=kalp_y, kilit_dizini=kilit_y,
                                   gozcu_log=log_y)
            if any(s.startswith("TUR ACILIYOR") for s in satirlar):
                acilan_c += 1
        T.esit("C3 24 saatlik pencerede TAM 1 gunluk tur", acilan_c, 1)
        ertesi = gun_basi + 86400 + 420
        _kalp_yaz(kalp_y, _kalp(ertesi, tetik="GUNLUK_DEFTER", llm_turu=True,
                                gunluk_gerekli=True))
        _s, rc_c4 = NT.kos(simdi=ertesi, kalp_yolu=kalp_y, kilit_dizini=kilit_y,
                           gozcu_log=log_y)
        T.esit("C4 ERTESI gun yeniden ACILIR", rc_c4, NT.RC_AC_YESIL)

        # ---------- D. FAIL-LOUD: OLU GOZCU SESSIZ KALAMAZ ------------------
        # Fikstur KRITIK: kalbin ICERIGI kusursuz YESIL, yalniz EPOK bayat.
        # "Sessiz yesil" hatasi tam bu fiksturde dogar.
        kalp_y, kilit_y, log_y = ortam("D")
        olu_an = simdi + 3600
        _kalp_yaz(kalp_y, _kalp(simdi))          # 60 dk once atmis kalp
        satirlar_d, rc_d = NT.kos(simdi=olu_an, kalp_yolu=kalp_y,
                                  kilit_dizini=kilit_y, gozcu_log=log_y)
        T.dogru("D1 'KALP BAYAT' satiri var",
                any(s.startswith("KALP BAYAT") for s in satirlar_d))
        T.esit("D2 hukum AC + KIRMIZI", rc_d, NT.RC_AC_KIRMIZI)
        T.esit("D3 saf karar sebebi", NT.karar(_kalp(simdi), olu_an, bugun).sebep,
               "KALP_BAYAT")
        T.dogru("D4 AYNI donguda hem BAYAT satiri hem tur karari",
                any(s.startswith("KALP BAYAT") for s in satirlar_d)
                and any(s.startswith("TUR ACILIYOR") for s in satirlar_d))
        # Savunmaci okuma: bayatlik kolu OLDURULDUGUNDE bu dosya HIC yazilmaz.
        # `open()` ile patlamak mutanti ISTISNAYLA oldurur ("KOL OLCULMEDI");
        # kol IDDIAYLA olculmelidir.
        gozcu_log_icerik = ""
        if os.path.exists(log_y):
            with open(log_y, encoding="utf-8") as dosya:
                gozcu_log_icerik = dosya.read()
        T.dogru("D5 KALP BAYAT gozcu-cron.log'a da dustu",
                "KALP BAYAT" in gozcu_log_icerik)
        kalp_y2, kilit_y2, log_y2 = ortam("D6")
        _s, rc_d6 = NT.kos(simdi=simdi, kalp_yolu=kalp_y2, kilit_dizini=kilit_y2,
                           gozcu_log=log_y2)
        T.esit("D6 kalp DOSYASI YOK -> AC + KIRMIZI", rc_d6, NT.RC_AC_KIRMIZI)
        T.yanlis("D7a 44 dk BAYAT DEGIL",
                 NT.karar(_kalp(simdi), simdi + 2640, bugun).sebep == "KALP_BAYAT")
        T.esit("D7b 46 dk BAYAT",
               NT.karar(_kalp(simdi), simdi + 2760, bugun).sebep, "KALP_BAYAT")
        # D8: gunluk damga ZATEN tuketilmisken bile SES kesilmez.
        _s, _rc = NT.kos(simdi=olu_an + 60, kalp_yolu=kalp_y, kilit_dizini=kilit_y,
                         gozcu_log=log_y)
        satirlar_d8, rc_d8 = NT.kos(simdi=olu_an + 120, kalp_yolu=kalp_y,
                                    kilit_dizini=kilit_y, gozcu_log=log_y)
        T.dogru("D8a damga tuketilmisken de KALP BAYAT satiri var",
                any(s.startswith("KALP BAYAT") for s in satirlar_d8))
        T.esit("D8b hukum hala KIRMIZI", rc_d8, NT.RC_ACMA_KIRMIZI)

        # ---------- E. CIFT ATESLEME YASAGI ---------------------------------
        kalp_y, kilit_y, log_y = ortam("E")
        _kalp_yaz(kalp_y, _kalp(simdi, tetik="CI_KIRMIZI", llm_turu=True,
                                hedef_run="777", icra_rc=0))
        satirlar_e, rc_e = NT.kos(simdi=simdi, kalp_yolu=kalp_y,
                                  kilit_dizini=kilit_y, gozcu_log=log_y)
        T.esit("E1 gozcu ZATEN actiysa ikinci tur ACILMAZ", rc_e, NT.RC_ACMA_YESIL)
        T.dogru("E1b sebep=GOZCU_ICRA_ETTI",
                any("sebep=GOZCU_ICRA_ETTI" in s for s in satirlar_e))
        T.esit("E2 icra_rc=1 de ikinci tur ACMAZ",
               NT.karar(_kalp(simdi, tetik="CI_KIRMIZI", hedef_run="777", icra_rc=1),
                        simdi, bugun).hukum, "ACMA")

        # ---------- F. OLCULEMEDI != YESIL ----------------------------------
        kalp_y, kilit_y, log_y = ortam("F")
        _kalp_yaz(kalp_y, _kalp(simdi, tetik="OLCULEMEDI", ci_olculdu=False,
                                ci_sebep="RC:1", rc=2))
        _s, rc_f1 = NT.kos(simdi=simdi, kalp_yolu=kalp_y, kilit_dizini=kilit_y,
                           gozcu_log=log_y)
        T.esit("F1 ci olculemedi -> ACMA ama KIRMIZI", rc_f1, NT.RC_ACMA_KIRMIZI)
        kalp_y, kilit_y, log_y = ortam("F2")
        _kalp_yaz(kalp_y, _kalp(simdi, defter_olculdu=False, gunluk_gerekli=True))
        _s, rc_f2 = NT.kos(simdi=simdi, kalp_yolu=kalp_y, kilit_dizini=kilit_y,
                           gozcu_log=log_y)
        T.esit("F2 defter olculemedi + gunluk -> AC + KIRMIZI", rc_f2,
               NT.RC_AC_KIRMIZI)

        # ---------- G. DAMGA HIJYENI (ureten temizler) ----------------------
        kok_g = os.path.join(kok, "G", "kilit")
        os.makedirs(kok_g, exist_ok=True)
        eski = simdi - 30 * 86400
        for ad in ("gunluk_2026-07-01.tuketildi", "kirmizi_1.tuketildi"):
            yol = os.path.join(kok_g, ad)
            with open(yol, "w", encoding="utf-8") as dosya:
                dosya.write("x")
            os.utime(yol, (eski, eski))
        taze_yol = os.path.join(kok_g, "kirmizi_2.tuketildi")
        with open(taze_yol, "w", encoding="utf-8") as dosya:
            dosya.write("x")
        os.utime(taze_yol, (simdi - 60, simdi - 60))
        kilit_yol = os.path.join(kok_g, "4242.kilit")
        with open(kilit_yol, "w", encoding="utf-8") as dosya:
            dosya.write("PID=1\n")
        os.utime(kilit_yol, (eski, eski))
        silinen = NT.damga_temizle(kok_g, simdi=simdi)
        T.esit("G1 yalniz ESKI damgalar silindi", silinen, 2)
        T.dogru("G2 gozcunun .kilit dosyasina DOKUNULMADI",
                os.path.exists(kilit_yol))
        T.dogru("G3 taze damga DURUYOR", os.path.exists(taze_yol))

        # ---------- H. CIKIS KODU SOZLESMESI (ci-nobeti.sh buna bagli) ------
        T.esit("H1 AC + yesil = 0",
               NT.cikis_kodu(NT.Karar("AC", "x", "a", ("--tur",), False)), 0)
        T.esit("H2 AC + kirmizi = 1",
               NT.cikis_kodu(NT.Karar("AC", "x", "a", ("--tur",), True)), 1)
        T.esit("H3 ACMA + yesil = 10",
               NT.cikis_kodu(NT.Karar("ACMA", "x", "", (), False)), 10)
        T.esit("H4 ACMA + kirmizi = 11",
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

        # --- N. UCUNCU HAL: LLM_KOLU_KAPALI (28 Agu 2026, Okan emri) --------
        # 🔴 Bu bolum UC ekseni birden civiler: (1) hal SESSIZ ve KENDI ADIYLA,
        # (2) M1 gercek OLCULEMEDI hala KIRMIZI, (3) M2 dusen kosum bu kolla
        # SUSTURULAMAZ. Jeton ELLE YAZILMAZ, moduldan TURETILIR.
        jeton = getattr(NT, "LLM_KOLU_KAPALI", None)
        T.dogru("N0 jeton tek kaynaktan TURETILDI (elle yazilmadi)",
                jeton == "LLM_KOLU_KAPALI")
        kalp_n1 = _kalp(simdi, icra_denendi=True, icra_hal="KOSTU_BASARILI",
                        icra_rc=0, kosum_hukmu=jeton or "LLM_KOLU_KAPALI")
        n1 = NT.karar(kalp_n1, simdi, bugun)
        T.esit("N1a kol KAPALI -> ACMA/YESIL (saatlik sabit kirmizi biter)",
               NT.cikis_kodu(n1), NT.RC_ACMA_YESIL)
        T.esit("N1b sebep KENDI ADIYLA basilir", n1.sebep, "LLM_KOLU_KAPALI")
        T.yanlis("N1c hal KIRMIZI DEGILDIR", n1.kirmizi)

        # M1 EMNIYETI: GERCEK olcememe hali KIRMIZI KALIR.
        kalp_n2 = _kalp(simdi, icra_denendi=True, icra_hal="KOSTU_BASARILI",
                        icra_rc=0, kosum_hukmu="OLCULEMEDI")
        n2 = NT.karar(kalp_n2, simdi, bugun)
        T.esit("N2 M1: gercek OLCULEMEDI hala KIRMIZI",
               NT.cikis_kodu(n2), NT.RC_ACMA_KIRMIZI)

        # M2 EMNIYETI: DUSEN kosum, jetonu tasisa bile SUSTURULAMAZ.
        kalp_n3 = _kalp(simdi, icra_denendi=True, icra_hal="KOSTU_DUSTU",
                        icra_rc=1, kosum_hukmu=jeton or "LLM_KOLU_KAPALI")
        n3 = NT.karar(kalp_n3, simdi, bugun)
        T.esit("N3 M2: dusen kosum bu kolla SUSTURULAMAZ",
               NT.cikis_kodu(n3), NT.RC_ACMA_KIRMIZI)

        # N4 KONTROL: uretken hat AYNI kolda YESIL kalir (gevsetme olcumu).
        kalp_n4 = _kalp(simdi, icra_denendi=True, icra_hal="KOSTU_BASARILI",
                        icra_rc=0, kosum_hukmu="TEMIZ")
        T.esit("N4 KONTROL ureten hat YESIL kalir",
               NT.cikis_kodu(NT.karar(kalp_n4, simdi, bugun)), NT.RC_ACMA_YESIL)

        # N5 — FAIL-CLOSED'IN KENDISI OLCULUR. Jeton zinciri
        # (nobet-kapi -> gozcu -> tetik) KOPARSA sessizlestirme kolu ATESLEMEZ
        # ve hat ESKISI GIBI KIRMIZI kalir. "Fail-closed'dir" bir BEYANDIR;
        # vakasi yoksa bir gun sessizce fail-open olur (bu depoda olculdu).
        _jeton_yedek = getattr(NT, "LLM_KOLU_KAPALI", None)
        try:
            NT.LLM_KOLU_KAPALI = None
            T.esit("N5 jeton OKUNAMADI -> hal SUSTURULMAZ, KIRMIZI kalir",
                   NT.cikis_kodu(NT.karar(kalp_n1, simdi, bugun)),
                   NT.RC_ACMA_KIRMIZI)
        finally:
            NT.LLM_KOLU_KAPALI = _jeton_yedek

        # N6 — `kol_hali` ALANI: IKI DEGERI DE URETIR (sart ②). Tek deger
        # basan alan olculemez: "kapali" ile "alan bozulmus" ayirt edilemez.
        T.esit("N6a kapali kolda alan JETONU tasir",
               NT.kol_hali(NT.karar(kalp_n1, simdi, bugun)), "LLM_KOLU_KAPALI")
        T.esit("N6b ureten hatta alan ACIK",
               NT.kol_hali(NT.karar(kalp_n4, simdi, bugun)), "ACIK")
        T.dogru("N6c karar satiri alani TASIR",
                "kol_hali=LLM_KOLU_KAPALI" in
                NT.karar_satiri(NT.karar(kalp_n1, simdi, bugun)))
        _jeton_yedek2 = getattr(NT, "LLM_KOLU_KAPALI", None)
        try:
            NT.LLM_KOLU_KAPALI = None
            T.esit("N6d jeton OKUNAMADI -> 'ACIK' DENMEZ, OLCULEMEDI",
                   NT.kol_hali(NT.karar(kalp_n4, simdi, bugun)), "OLCULEMEDI")
        finally:
            NT.LLM_KOLU_KAPALI = _jeton_yedek2
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return T


# --- J. UCTAN UCA: GERCEK ci-nobeti.sh, SAHTE nobet-kapi -------------------
# Mutant'a acilmaz (kabuk gercek dosyayi kosar). `main()` icinden cagrilir.

# 🔴 KACIS DIZISI YOK (olculdu: `+ '\n'` yazilinca uretilen sahte dosyanin ICINE
# GERCEK satir sonu dustu, dizge kapanmadi, python3 SyntaxError verdi ve sayac
# bos kaldi — J0/J2/J3/J4 "0 cagri" gordu). `print(..., file=d)` satir sonunu
# KENDI koyar; tirnak icinde tek bir kacis kalmaz.
# ci-nobeti.sh her ikisini de `python3 <yol>` ile cagirir -> ikisi de PYTHON.
_SAHTE_KAPI = (
    "import os, sys\n"
    "with open(os.environ['PRUVO_TEST_SAYAC'], 'a', encoding='utf-8') as d:\n"
    "    print('CAGRI', *sys.argv[1:], file=d)\n"
    "sys.exit(int(os.environ.get('PRUVO_TEST_KAPI_RC', '0')))\n"
)
_DUSEN_TETIK = "import sys\nsys.exit(99)\n"


def _yaz_calistirilabilir(yol, icerik):
    with open(yol, "w", encoding="utf-8") as dosya:
        dosya.write(icerik)
    os.chmod(yol, os.stat(yol).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def kablo_kontrol():
    """ci-nobeti.sh GERCEKTEN tetige mi bagli? Sayarak olculur, okuyarak degil."""
    T = Testler()
    if not os.path.exists(CI_NOBETI_YOLU):
        T.esit("J0 ci-nobeti.sh var", False, True)
        return T
    kok = tempfile.mkdtemp(prefix="tetik-e2e-")
    try:
        sahte_kapi = os.path.join(kok, "sahte-nobet-kapi.py")
        _yaz_calistirilabilir(sahte_kapi, _SAHTE_KAPI)
        dusen_tetik = os.path.join(kok, "dusen-tetik.sh")
        _yaz_calistirilabilir(dusen_tetik, _DUSEN_TETIK)
        kalp_y = os.path.join(kok, "kalp.json")
        kilit_y = os.path.join(kok, "kilit")
        os.makedirs(kilit_y, exist_ok=True)
        log_y = os.path.join(kok, "ci-nobeti.log")
        gozcu_log_y = os.path.join(kok, "gozcu-cron.log")
        sayac = os.path.join(kok, "sayac.txt")

        def calistir(tetik=None):
            ortam = dict(os.environ)
            ortam.update({
                "PRUVO_NOBET_KOK": KOK,
                "PRUVO_NOBET_LOG": log_y,
                "PRUVO_NOBET_EV": kok,
                "PRUVO_NOBET_KAPI": sahte_kapi,
                "PRUVO_TETIK_KALP": kalp_y,
                "PRUVO_TETIK_KILIT": kilit_y,
                "PRUVO_TETIK_GOZCU_LOG": gozcu_log_y,
                "PRUVO_TEST_SAYAC": sayac,
            })
            if tetik:
                ortam["PRUVO_NOBET_TETIK"] = tetik
            # 🔴 19 Eyl 2026 (Tamirci): ci-nobeti.sh `#!/bin/zsh`; Linux CI
            # kosucusunda zsh YOK -> dogrudan exec shebang'de FileNotFoundError
            # verdi ve W2 kabul kapisi 3 koşum kirmizi kaldi. Kabulun `_kabuk()`
            # deseni: zsh, yoksa bash (soz dizimi uyumlu). Mac'te davranis AYNI.
            kabuk = shutil.which("zsh") or shutil.which("bash")
            sonuc = subprocess.run([kabuk, CI_NOBETI_YOLU], env=ortam, cwd=kok,
                                   capture_output=True, text=True, timeout=120)
            return sonuc.returncode

        def cagri_sayisi():
            if not os.path.exists(sayac):
                return 0
            with open(sayac, encoding="utf-8") as dosya:
                return len([s for s in dosya.read().split("\n") if s.strip()])

        def log_metni():
            if not os.path.exists(log_y):
                return ""
            with open(log_y, encoding="utf-8") as dosya:
                return dosya.read()

        def tetik_kararlari():
            """Log'daki HER `TETIK_HUKMU` satirindan `tetik_karari=` degerini toplar."""
            degerler = []
            for satir in log_metni().split("\n"):
                if not satir.startswith("TETIK_HUKMU "):
                    continue
                for parca in satir.split():
                    if parca.startswith("tetik_karari="):
                        degerler.append(parca.split("=", 1)[1])
            return degerler

        def iddia_edilen_tur():
            """Hattin KENDI iddiasi: butun `acilan_tur=` alanlarinin TOPLAMI.

            🔴 BEKLENTI ELLE YAZILMAZ, BURADAN TURER. Once her vaka icin
            "AC halinde 1 cagri" diye ELLE sayi yaziliydi; sozlesme degisince
            o sayilar BAYATLADI. Olculen sey artik PARITE: hattin `acilan_tur`
            iddiasi GERCEKTEN sayilan cagriya ESIT mi, ve iddia SIFIR mi.
            Turu geri koyan bir mutant iki ekseni birden bozar.
            """
            toplam = 0
            for satir in log_metni().split("\n"):
                if not satir.startswith("TETIK_HUKMU "):
                    continue
                for parca in satir.split():
                    if parca.startswith("acilan_tur="):
                        try:
                            toplam += int(parca.split("=", 1)[1])
                        except ValueError:
                            toplam += 10 ** 6
            return toplam

        simdi = time.time()

        # J-pre: fiksturun KENDISI saglam mi? Bozuk sahte dosya "tur acilmadi"
        # gibi gorunur ve "0 cagri" iddialarini SAHTE YESILE cevirir.
        try:
            compile(_SAHTE_KAPI, "sahte-nobet-kapi.py", "exec")
            compile(_DUSEN_TETIK, "dusen-tetik.py", "exec")
            fikstur_saglam = True
        except SyntaxError:
            fikstur_saglam = False
        T.dogru("J-pre sahte fiksturler PYTHON olarak derleniyor", fikstur_saglam)

        def sifirla():
            if os.path.exists(sayac):
                os.unlink(sayac)

        # J0 POZITIF KONTROL — SAYAC CANLI MI? "0 cagri" iddiasi ancak sayac
        # CALISIYORSA anlam tasir; KOPUK sayacta da 0 gorunur (K182 sinifi:
        # mutantin yasamasi "kol saglam" degil "kol OLCULEMEDI" demektir).
        # LLM kolu 28 Agu'da KAPANDIGI icin ci-nobeti.sh kapiyi artik HIC
        # cagirmaz -> pozitif kontrol sahte kapiyi DOGRUDAN cagirir.
        ortam_j0 = dict(os.environ)
        ortam_j0["PRUVO_TEST_SAYAC"] = sayac
        subprocess.run([sys.executable, sahte_kapi, "--tur"], env=ortam_j0,
                       capture_output=True, text=True, timeout=60)
        T.esit("J0 POZITIF KONTROL: sayac CANLI (dogrudan cagri 1 sayilir)",
               cagri_sayisi(), 1)
        sifirla()

        # 🔴 BURADAN SONRA SAYAC SIFIRLANMAZ: J1-J6b'nin TUM kosumlari ayni
        # sayacta birikir ve J7 paritesi o kumulatif sayiyi hattin kendi
        # iddiasiyla kiyaslar. Arada sifirlamak, turu geri koyan bir mutanta
        # kacis penceresi acardi.

        # J1 YESIL: 4 kosum -> tetik ACMA der, kapi zaten HIC cagrilmaz
        _kalp_yaz(kalp_y, _kalp(simdi))
        rc_kumesi = set()
        for _ in range(4):
            rc_kumesi.add(calistir())
        T.esit("J1a yesil 4 kosumda nobet-kapi cagrisi 0", cagri_sayisi(), 0)
        T.esit("J1b cikis kodu daima 0", rc_kumesi, {0})
        T.esit("J1c log'da 4x TUR ACILMADI sebep=YESIL",
               log_metni().count("TUR ACILMADI sebep=YESIL"), 4)
        T.esit("J1d dort kosumun tetik karari ACMA",
               tetik_kararlari().count("ACMA"), 4)

        # J2 KIRMIZI: AYNI run-id 3 kosum. Tetik kilidi DURUYOR (TAM 1 kez
        # "AC" der) — ama LLM kolu kapali oldugu icin cagri YINE 0.
        j2_once = len(tetik_kararlari())
        _kalp_yaz(kalp_y, _kalp(simdi, tetik="CI_KIRMIZI", llm_turu=True,
                                yeni_kirmizi=2, hedef_run="55501"))
        for _ in range(3):
            calistir()
        j2_kararlar = tetik_kararlari()[j2_once:]
        T.esit("J2a ayni run-id 3 kosumda tetik TAM 1 kez AC der",
               j2_kararlar.count("AC"), 1)
        T.esit("J2b CAGRI_YERI YOK: AC karari verilse de bu betik cagirmaz",
               cagri_sayisi(), 0)

        # J3 OLU GOZCU: bayat kalp -> tetik AC der, cikis KIRMIZI, KALP BAYAT
        # loglanir; tur YINE ACILMAZ.
        j3_once = len(tetik_kararlari())
        _kalp_yaz(kalp_y, _kalp(simdi - 3600))
        rc_j3 = calistir()
        T.esit("J3a olu gozcude tetik AC der", tetik_kararlari()[j3_once:], ["AC"])
        T.dogru("J3b cikis kodu KIRMIZI", rc_j3 != 0)
        T.dogru("J3c log'da KALP BAYAT", "KALP BAYAT" in log_metni())
        T.esit("J3d CAGRI_YERI YOK: olu gozcude de bu betik cagirmaz",
               cagri_sayisi(), 0)

        # J4 FAIL-CLOSED: tetik kapisi coker (rc=99) -> KIRMIZI ayak DURUR,
        # tur-acma ayagi DUSTU.
        j4_once = len(tetik_kararlari())
        _kalp_yaz(kalp_y, _kalp(simdi))
        rc_j4 = calistir(tetik=dusen_tetik)
        T.esit("J4a kapi coktu -> tetik karari AC (fail-closed)",
               tetik_kararlari()[j4_once:], ["AC"])
        T.dogru("J4b cikis kodu KIRMIZI", rc_j4 != 0)
        T.dogru("J4c log'da BILINMEYEN rc uyarisi",
                "BILINMEYEN rc=99" in log_metni())
        T.esit("J4d CAGRI_YERI YOK: fail-closed'da da bu betik cagirmaz",
               cagri_sayisi(), 0)

        # J5 TUKETICI PARITESI — `ci-nobeti.log`'un BITIS satirini OKUYAN arac
        # `tools/t1-kiyas.py`'dir. Desen KOPYALANMAZ, tuketiciden ITHAL edilir:
        # ikiz desen sessizce ayrisir ve kirilma KIRMIZI YAKMADAN olur.
        # 🔴 19 Eyl 2026 (Tamirci): sabit Mac yolu CI kosucusunda YOK -> J5b ithal
        # edemedi. Ev koku kabulun verdigi `PRUVO_EV_KOKU`dan; canlida bos ise ESKI yol.
        t1_yolu = os.path.join(os.environ.get("PRUVO_EV_KOKU") or "/Users/okan/dev/pruvo",
                               "tools", "t1-kiyas.py")
        bitis_satirlari = [s for s in log_metni().split("\n") if " BITIS " in s]
        T.dogru("J5a log'da BITIS satiri URETILDI", len(bitis_satirlari) > 0)
        t1_regex = None
        try:
            spec_t1 = importlib.util.spec_from_file_location("t1_kiyas_tuketici", t1_yolu)
            modul_t1 = importlib.util.module_from_spec(spec_t1)
            sys.dont_write_bytecode = True
            spec_t1.loader.exec_module(modul_t1)
            t1_regex = modul_t1._RE_ESKI_BITIS
        except BaseException:
            t1_regex = None
        T.dogru("J5b tuketici regexi ITHAL edildi (kopya DEGIL)", t1_regex is not None)
        if t1_regex is None:
            T.esit("J5c HER BITIS satiri tuketici regexine uyar", "OLCULEMEDI", 0)
        else:
            eslesen = [s for s in bitis_satirlari if t1_regex.search(s)]
            T.esit("J5c HER BITIS satiri tuketici regexine uyar",
                   len(eslesen), len(bitis_satirlari))

        # ---------- J6. K311 UCTAN UCA: SAHTE YESIL GERCEKTEN KAPANDI MI? --
        j6_log_once = log_metni()

        # J6a — ASIL VAKA: gozcu turu ACTI, tur KOSTU, ama hicbir sey URETMEDI.
        _kalp_yaz(kalp_y, _kalp(simdi, icra_denendi=True,
                                icra_hal="KOSTU_BASARILI",
                                kosum_hukmu="OLCULEMEDI"))
        rc_j6a = calistir()
        j6a_yeni = log_metni()[len(j6_log_once):]
        T.dogru("J6a1 URETMEYEN hat rc=0 DONEMEZ", rc_j6a != 0)
        T.esit("J6a2 o kosumda BITIS rc=0 URETILMEDI",
               j6a_yeni.count("BITIS rc=0"), 0)
        T.esit("J6a3 tur ACILMADI", cagri_sayisi(), 0)
        T.dogru("J6a4 log sebebi TASIR", "GOZCU_URETMEDI" in j6a_yeni)
        T.esit("J6a5 satirin acilan_tur alani 0", j6a_yeni.count("acilan_tur=0"), 1)

        # J6b — NEGATIF KONTROL: URETEN hat AYNI kolda YESIL kalir.
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

        # J6c — IKI YON DE OLCULDU MU? `acilan_tur` artik DAIMA 0; olculen
        # eksen `tetik_karari`dir: log HEM `AC` HEM `ACMA` uretmis olmali.
        # Tek yonlu olcum hukum vermez.
        tum_kararlar = tetik_kararlari()
        T.dogru("J6c1 log'da tetik_karari=AC URETILDI (tetik ACMAK ISTEDI)",
                tum_kararlar.count("AC") >= 1)
        T.dogru("J6c2 log'da tetik_karari=ACMA URETILDI (tetik ACMAK ISTEMEDI)",
                tum_kararlar.count("ACMA") >= 1)
        T.yanlis("J6c3 log'da acilan_tur=1 HIC uretilmedi",
                 "acilan_tur=1" in log_metni())

        # ---------- J7. CAGRI_YERI — HEDEF KOL, ADIYLA --------------------
        # 🔴 SOZLESME (DAR): bu BETIK nobet kapisinin tur cagrisini YAPMAZ.
        # 🔴 BU BOLUM "LLM turu 0" DEMEZ — o iddianin tek olcum yeri
        # `nobet-kapi.py` GOVDESIDIR (gozcu.py de kapiyi kendisi cagirir).
        # Burada olculen sey yalnizca CAGRI YERININ kaldirilmis olmasidir.
        # Beklenti ELLE YAZILMAZ: bu betigin KENDI `acilan_tur`
        # iddiasi ile GERCEKTEN sayilan cagri KIYASLANIR (parite), ve iddianin
        # kendisi 0 olmalidir. Turu geri koyan mutant IKI ekseni birden bozar.
        T.esit("J7a CAGRI_YERI: olculen cagri = bu betigin acilan_tur iddiasi",
               cagri_sayisi(), iddia_edilen_tur())
        T.esit("J7b CAGRI_YERI: bu betigin acilan_tur iddiasi 0",
               iddia_edilen_tur(), 0)
        T.esit("J7c CAGRI_YERI: butun J kosumlarinda bu betik hic cagirmadi",
               cagri_sayisi(), 0)
        sifirla()

        # I. YABANCI DIZINDEN KOSUM — kapi cagiranin cwd'sine BAGIMLI OLMAMALI.
        # Olculdu (19 Agu): scratchpad'den kosan bir olcum betigi `import kilit`i
        # cozemedi, `GZ=None` kaldi ve kapi 24 kaydin 24'unde fail-closed
        # varsayilanini dondu — "olcum" diye SABIT cevap uretti.
        yabanci = tempfile.mkdtemp(prefix="tetik-yabanci-")
        try:
            ortam_i = dict(os.environ)
            ortam_i.update({
                "PRUVO_TETIK_KALP": kalp_y,
                "PRUVO_TETIK_KILIT": kilit_y,
                "PRUVO_TETIK_GOZCU_LOG": gozcu_log_y,
            })
            ortam_i.pop("PYTHONPATH", None)
            sonuc_i = subprocess.run(
                [sys.executable, os.path.join(KOK, "nobet-tetik.py"), "--kuru"],
                cwd=yabanci, env=ortam_i, capture_output=True, text=True, timeout=120)
            cikti_i = sonuc_i.stdout + sonuc_i.stderr
            T.yanlis("I1 yabanci dizinde GOZCU YUKLENEMEDI CIKMAZ",
                     "GOZCU YUKLENEMEDI" in cikti_i)
            T.yanlis("I2 yabanci dizinde GOZCU_YUKLENEMEDI sebebi CIKMAZ",
                     "sebep=GOZCU_YUKLENEMEDI" in cikti_i)
            T.dogru("I3 yabanci dizinde GERCEK karar satiri basilir",
                    ("TUR ACILMADI sebep=" in cikti_i) or ("TUR ACILIYOR sebep=" in cikti_i))
        finally:
            shutil.rmtree(yabanci, ignore_errors=True)

    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return T


def _modul_yukle(yol=TETIK_YOLU):
    spec = importlib.util.spec_from_file_location("nobet_tetik", yol)
    modul = importlib.util.module_from_spec(spec)
    onceki = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(modul)
    finally:
        sys.dont_write_bytecode = onceki
    return modul


def main():
    NT = _modul_yukle()
    T = kos(NT)
    for hata in T.hatalar:
        print("KIRIK " + hata)
    J = kablo_kontrol()
    for hata in J.hatalar:
        print("KIRIK " + hata)
    print("VAKA=%d DUSEN=%d KABLO=%d/%d" %
          (T.toplam, T.toplam - T.gecen, J.gecen, J.toplam))
    return 0 if (T.gecen == T.toplam and J.gecen == J.toplam) else 1


if __name__ == "__main__":
    sys.exit(main())
