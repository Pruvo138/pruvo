#!/usr/bin/env python3
"""GOZCU KABUL TESTI — saf fikstur; gh CAGIRMAZ, cron ISTEMEZ, gercek tur ACMAZ.

Cikis: tek makine satiri `GECEN=<n>/<n>`; tumu gecmezse rc=1.
Mutasyon kosucusu `kos(GZ)` fonksiyonunu MUTANT modulle cagirir — bu yuzden testler
modulu global import'tan DEGIL, parametreden alir.
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time

GOZCU_YOLU = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gozcu.py")


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


def _kosum(kimlik, conclusion, status="completed", dal="main", ad="ci"):
    return {"databaseId": kimlik, "name": ad, "conclusion": conclusion,
            "status": status, "headBranch": dal, "headSha": "abc123"}


def _kalem(GZ, kimlik, is_metni, kime="MaCiT", onarim=True):
    durum = GZ.NK.ONARIM_DURUMU if onarim else "KAPANDI"
    return {"id": kimlik, "tarih": "17 Agu", "kimden_kime": "KraL → " + kime,
            "kime": kime, "is": is_metni, "durum_ham": durum, "durum": durum,
            "kanit_ham": "", "kabul": "", "satir_no": 1}


class SahteKosucu:
    """Gercek nobet-kapi.py YERINE gecer: cagrilari sayar, sabit rc doner."""

    def __init__(self, rc=0, hukum=None):
        self.rc = rc
        # K316: `hukum` VERILMEZSE davranis BIREBIR eskisi gibi (rc'den turer).
        # Verilince "kosum hukmu URETKEN ama surec rc'si DUSTU" hali kurulabilir —
        # 10j bu dikise dayanir.
        self.hukum = hukum
        self.cagrilar = []

    def __call__(self, bayraklar):
        self.cagrilar.append(list(bayraklar))
        # B5: gercek tur HER kolda KOSUM_HUKMU basar; fikstur o sekli TASIR.
        hukum = self.hukum
        if hukum is None:
            hukum = "TEMIZ" if self.rc == 0 else "MOTOR_DUSTU"
        return (self.rc, "SAHTE_TUR rc=%d\nKOSUM_HUKMU=%s\n" % (self.rc, hukum))


def _yollar(kok):
    return {"durum": os.path.join(kok, "durum.json"),
            "kalp": os.path.join(kok, "kalp.json"),
            "log": os.path.join(kok, "gozcu.log"),
            "kilit_dizini": os.path.join(kok, "kilit"),
            "eskalasyon": os.path.join(kok, "eskalasyon.md"),
            "artik_dizini": os.path.join(kok, "artik")}


def _durum_yaz(yol, veri):
    with open(yol, "w", encoding="utf-8") as dosya:
        json.dump(veri, dosya)


def kos(GZ):
    T = Testler()
    simdi = 1_755_000_000.0
    bugun = time.strftime("%Y-%m-%d", time.gmtime(simdi))

    # --- 1. kirmizi_kosumlar ---------------------------------------------
    ham = [
        _kosum(101, "failure"),
        _kosum(102, "cancelled"),
        _kosum(103, "success"),
        _kosum(104, None, status="in_progress"),
        _kosum(105, "failure", dal="dal-x"),
        {"databaseId": None, "conclusion": "failure", "headBranch": "main"},
    ]
    kirmizilar = GZ.kirmizi_kosumlar(ham)
    kimlikler = [k["id"] for k in kirmizilar]
    T.esit("1.1 failure secilir", "101" in kimlikler, True)
    T.esit("1.2 cancelled secilMEZ", "102" in kimlikler, False)
    T.esit("1.3 success secilMEZ", "103" in kimlikler, False)
    T.esit("1.4 in_progress secilMEZ", "104" in kimlikler, False)
    T.esit("1.5 baska dal secilMEZ", "105" in kimlikler, False)
    T.esit("1.6 databaseId yok -> atlanir", len(kirmizilar), 1)

    # --- 2. yeni_kirmizilar ----------------------------------------------
    kirmizi = [{"id": "101", "ad": "ci", "sha": "a"}]
    T.esit("2.1 kayit yok -> yeni",
           len(GZ.yeni_kirmizilar(kirmizi, {"kosumlar": {}})), 1)
    T.esit("2.2 deneme=1 -> yeni",
           len(GZ.yeni_kirmizilar(kirmizi, {"kosumlar": {"101": {"deneme": 1, "durum": "DUSTU"}}})), 1)
    T.esit("2.3 deneme=3 -> yeni DEGIL",
           len(GZ.yeni_kirmizilar(kirmizi, {"kosumlar": {"101": {"deneme": 3, "durum": "DUSTU"}}})), 0)
    T.esit("2.4 ESKALASYON -> yeni DEGIL",
           len(GZ.yeni_kirmizilar(kirmizi, {"kosumlar": {"101": {"deneme": 1, "durum": "ESKALASYON"}}})), 0)
    T.esit("2.5 TABAN -> yeni DEGIL",
           len(GZ.yeni_kirmizilar(kirmizi, {"kosumlar": {"101": {"deneme": 0, "durum": "TABAN"}}})), 0)

    # --- 3. tetik_karari --------------------------------------------------
    T.esit("3.1 olculemedi (ci)", GZ.tetik_karari(0, 0, False, False, True), ("OLCULEMEDI", False, 2))
    T.esit("3.2 kirmizi", GZ.tetik_karari(1, 0, False, True, True), ("CI_KIRMIZI", True, 0))
    T.esit("3.3 dagitim (LLM YOK)", GZ.tetik_karari(0, 2, False, True, True), ("DEFTER_DAGITIM", False, 0))
    T.esit("3.4 gunluk", GZ.tetik_karari(0, 0, True, True, True), ("GUNLUK_DEFTER", True, 0))
    T.esit("3.5 bos tur olur", GZ.tetik_karari(0, 0, False, True, True), ("YOK", False, 0))
    T.esit("3.6 ci_olculdu=False kirmiziyi EZER",
           GZ.tetik_karari(5, 3, True, False, True), ("OLCULEMEDI", False, 2))
    T.esit("3.7 defter_olculdu=False EZER",
           GZ.tetik_karari(5, 3, True, True, False), ("OLCULEMEDI", False, 2))

    # --- 4. dagitilabilir_kalemler / kat_sayaci ---------------------------
    kalemler = [
        _kalem(GZ, "K1", "kapi kodunun mutasyon olcumu"),          # sessiz-hata -> MIMAR
        _kalem(GZ, "K2", "yeni parca serisi", kime="Okan"),         # OKAN
        _kalem(GZ, "K3", "log dosyalarini tasima ve temizlik"),     # isci kati
        _kalem(GZ, "K4", "log dosyalarini tasima", onarim=False),   # 🔧 DEGIL
    ]
    dag = [k["id"] for k in GZ.dagitilabilir_kalemler(kalemler)]
    T.esit("4.1 MIMAR kati disarida", "K1" in dag, False)
    T.esit("4.2 OKAN kati disarida", "K2" in dag, False)
    T.esit("4.3 isci kati iceride", "K3" in dag, True)
    T.esit("4.4 onarim olmayan sayilmaz", "K4" in dag, False)
    T.esit("4.5 kat_sayaci", GZ.kat_sayaci(kalemler), {"MIMAR": 1, "OKAN": 1, "ISCI": 1})

    # --- 5. deneme_sonraki ------------------------------------------------
    T.esit("5.1 1 -> DUSTU", GZ.deneme_sonraki({"deneme": 0}, False), {"deneme": 1, "durum": "DUSTU"})
    T.esit("5.2 2 -> DUSTU", GZ.deneme_sonraki({"deneme": 1}, False), {"deneme": 2, "durum": "DUSTU"})
    T.esit("5.3 3 -> ESKALASYON", GZ.deneme_sonraki({"deneme": 2}, False), {"deneme": 3, "durum": "ESKALASYON"})
    T.esit("5.4 basarili -> KAPANDI", GZ.deneme_sonraki({"deneme": 2}, True), {"deneme": 3, "durum": "KAPANDI"})

    # --- 6. kilit_karari --------------------------------------------------
    canli = lambda pid: True
    olu = lambda pid: False
    taze = "PID=4242\nEPOK=%.1f\nDAMGA=x\n" % simdi
    T.esit("6.1 bos -> AL", GZ.kilit_karari(None, simdi, canli), "AL")
    T.esit("6.2 canli PID -> DOLU", GZ.kilit_karari(taze, simdi, canli), "DOLU")
    T.esit("6.3 olu PID -> BAYAT", GZ.kilit_karari(taze, simdi, olu), "BAYAT")
    T.esit("6.4 eski damga -> BAYAT",
           GZ.kilit_karari("PID=4242\nEPOK=%.1f\n" % (simdi - 7200), simdi, canli), "BAYAT")
    T.esit("6.5 PID'siz -> BAYAT", GZ.kilit_karari("EPOK=%.1f\n" % simdi, simdi, canli), "BAYAT")

    # --- 7. kalp_bayat_mi -------------------------------------------------
    T.esit("7.1 taze", GZ.kalp_bayat_mi({"epok": simdi - 60}, simdi), False)
    T.esit("7.2 eski", GZ.kalp_bayat_mi({"epok": simdi - 7200}, simdi), True)
    T.esit("7.3 epok yok -> BAYAT", GZ.kalp_bayat_mi({}, simdi), True)
    T.esit("7.4 epok bozuk -> BAYAT", GZ.kalp_bayat_mi({"epok": "dun"}, simdi), True)

    # --- 8. tur_artigi_temizle --------------------------------------------
    kok8 = tempfile.mkdtemp(prefix="gozcu-test8-")
    try:
        eski = simdi - 100000
        adlar = {".isci-cikti.aaa": eski, ".isci-cikti.bbb": eski,
                 ".bekci-cikti.ccc": eski, ".isci-cikti.taze": simdi - 10,
                 "nobet-kapi.log": eski}
        for ad, mtime in adlar.items():
            yol = os.path.join(kok8, ad)
            with open(yol, "w", encoding="utf-8") as dosya:
                dosya.write("x")
            os.utime(yol, (mtime, mtime))
        alt = os.path.join(kok8, ".isci-cikti.dizin")
        os.makedirs(alt)
        os.utime(alt, (eski, eski))
        silinen = GZ.tur_artigi_temizle(kok8, simdi=simdi)
        kalan = set(os.listdir(kok8))
        T.esit("8.1 silinen=3", silinen, 3)
        T.esit("8.2 taze + ilgisiz duruyor",
               {".isci-cikti.taze", "nobet-kapi.log"} <= kalan, True)
        T.esit("8.3 dizin duruyor", ".isci-cikti.dizin" in kalan, True)
        T.esit("8.4 okunamayan dizin -> 0",
               GZ.tur_artigi_temizle(os.path.join(kok8, "yok-boyle"), simdi=simdi), 0)
    finally:
        shutil.rmtree(kok8, ignore_errors=True)

    # --- 9. gunluk_tur_gerekli_mi -----------------------------------------
    T.esit("9.1 bugun kayitli -> False",
           GZ.gunluk_tur_gerekli_mi({"son_gunluk_tur": bugun}, simdi), False)
    T.esit("9.2 dun -> True",
           GZ.gunluk_tur_gerekli_mi({"son_gunluk_tur": "2020-01-01"}, simdi), True)
    T.esit("9.3 bos -> True", GZ.gunluk_tur_gerekli_mi({}, simdi), True)

    # --- 10. uctan uca (sahte kosucularla) --------------------------------
    kok10 = tempfile.mkdtemp(prefix="gozcu-test10-")
    try:
        def kur(kosumlar, kalemler_, rc=0, durum=None, hukum=None):
            kok = tempfile.mkdtemp(prefix="tur-", dir=kok10)
            yollar = _yollar(kok)
            os.makedirs(yollar["artik_dizini"], exist_ok=True)
            _durum_yaz(yollar["durum"], durum if durum is not None else
                       {"kosumlar": {}, "son_gunluk_tur": bugun, "taban_alindi": True})
            kosucu = SahteKosucu(rc, hukum)
            return yollar, kosucu, (lambda: kosumlar), (lambda: kalemler_)

        # (a) yesil CI + bos defter -> TETIK=YOK, kosucu HIC cagrilmadi
        yollar, kosucu, ci, dft = kur([_kosum(1, "success")], [])
        sonuc = GZ.tur(simdi=simdi, kosum_okuyucu=ci, defter_okuyucu=dft,
                       tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        T.esit("10a tetik YOK", sonuc["tetik"], "YOK")
        T.esit("10a kosucu cagrilmadi", len(kosucu.cagrilar), 0)
        T.esit("10a rc=0", sonuc["rc"], 0)

        # (b) yeni kirmizi -> kosucu --tur ile 1 kez
        yollar, kosucu, ci, dft = kur([_kosum(700, "failure")], [])
        sonuc = GZ.tur(simdi=simdi, kosum_okuyucu=ci, defter_okuyucu=dft,
                       tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        T.esit("10b tetik CI_KIRMIZI", sonuc["tetik"], "CI_KIRMIZI")
        T.esit("10b kosucu 1 kez --tur", kosucu.cagrilar, [["--tur"]])

        # (c) ayni kirmizi ikinci turda -> kosucu cagrilmaz (deneme kaydi)
        sonuc2 = GZ.tur(simdi=simdi + 900, kosum_okuyucu=ci, defter_okuyucu=dft,
                        tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        T.esit("10c ikinci turda cagri YOK", len(kosucu.cagrilar), 1)
        T.esit("10c tetik YOK", sonuc2["tetik"], "YOK")

        # (d) yalniz dagitilabilir kalem -> --tur-kapat, llm_turu False
        yollar, kosucu, ci, dft = kur([_kosum(2, "success")],
                                      [_kalem(GZ, "K3", "log tasima ve temizlik")])
        sonuc = GZ.tur(simdi=simdi, kosum_okuyucu=ci, defter_okuyucu=dft,
                       tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        T.esit("10d tetik DEFTER_DAGITIM", sonuc["tetik"], "DEFTER_DAGITIM")
        T.esit("10d --tur-kapat", kosucu.cagrilar, [["--tur-kapat"]])
        T.esit("10d llm_turu False", bool(sonuc["llm_turu"]), False)

        # (e) icra rc=1 -> gozcu rc>=1
        yollar, kosucu, ci, dft = kur([_kosum(3, "success")],
                                      [_kalem(GZ, "K3", "log tasima ve temizlik")], rc=1)
        sonuc = GZ.tur(simdi=simdi, kosum_okuyucu=ci, defter_okuyucu=dft,
                       tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        T.esit("10e kirmizi tur gozcuye tasinir", sonuc["rc"] >= 1, True)

        # (j) 🔴 K316: kosum hukmu URETKEN ("TEMIZ") ama SURECIN rc'si DUSTU.
        # NEDEN VAR: 10e'de rc'yi YUKSELTEN IKI kol vardi (`icra_hal ==
        # KOSTU_DUSTU` ve `uretken_mi` fail-closed kolu), cunku SahteKosucu
        # rc!=0 iken hukmu de MOTOR_DUSTU basiyordu. Iki kol da atesledigi icin
        # "kosan turun rc'si gozcuye tasinir" ekseni TEK BASINA olculemiyordu:
        # B6 gocunden (K311) sonra o kolu olduren mutant HAYATTA kaliyordu.
        # Burada hukum TEMIZ verilir -> `uretken_mi` YESIL doner, eskalasyon 0;
        # geriye rc'yi yukseltebilecek TEK kol kalir.
        yollar, kosucu, ci, dft = kur([_kosum(5, "success")],
                                      [_kalem(GZ, "K3", "log tasima ve temizlik")],
                                      rc=1, hukum="TEMIZ")
        sonuc = GZ.tur(simdi=simdi, kosum_okuyucu=ci, defter_okuyucu=dft,
                       tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        T.esit("10j hal KOSTU_DUSTU", sonuc["kalp"]["icra_hal"], "KOSTU_DUSTU")
        T.esit("10j uretken kol ATESLEMEZ (yalitim)",
               (sonuc["kalp"]["uretken"], sonuc["kalp"]["kosum_hukmu"]), (True, "TEMIZ"))
        T.esit("10j eskalasyon kolu ATESLEMEZ (yalitim)",
               sonuc["kalp"]["eskalasyon_acik"], 0)
        T.esit("10j kosan turun rc'si gozcuye TASINIR", sonuc["rc"] >= 1, True)

        # (f) TABAN: ilk kosumda mevcut kirmizilara isci ACILMAZ
        yollar, kosucu, ci, dft = kur([_kosum(900, "failure")], [],
                                      durum={"kosumlar": {}, "son_gunluk_tur": bugun,
                                             "taban_alindi": False})
        sonuc = GZ.tur(simdi=simdi, kosum_okuyucu=ci, defter_okuyucu=dft,
                       tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        T.esit("10f taban -> cagri YOK", len(kosucu.cagrilar), 0)
        T.esit("10f taban_alinan=1", sonuc["kalp"]["taban_alinan"], 1)

        # (g) OLCULEMEDI: gh dusmus -> rc=2, hicbir sey acilmaz
        yollar, kosucu, ci, dft = kur(None, [_kalem(GZ, "K3", "log tasima")])
        sonuc = GZ.tur(simdi=simdi, kosum_okuyucu=(lambda: None), defter_okuyucu=dft,
                       tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        T.esit("10g OLCULEMEDI rc=2", (sonuc["tetik"], sonuc["rc"]), ("OLCULEMEDI", 2))
        T.esit("10g cagri YOK", len(kosucu.cagrilar), 0)

        # (h) --kuru hicbir sey yazmaz/silmez/acmaz
        yollar, kosucu, ci, dft = kur([_kosum(701, "failure")], [])
        artik = os.path.join(yollar["artik_dizini"], ".isci-cikti.eski")
        with open(artik, "w", encoding="utf-8") as dosya:
            dosya.write("x")
        os.utime(artik, (simdi - 100000, simdi - 100000))
        os.unlink(yollar["durum"])
        sonuc = GZ.tur(kuru=True, simdi=simdi, kosum_okuyucu=ci, defter_okuyucu=dft,
                       tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        T.esit("10h kuru: cagri YOK", len(kosucu.cagrilar), 0)
        T.esit("10h kuru: artik DURUYOR", os.path.exists(artik), True)
        T.esit("10h kuru: durum yazilmadi", os.path.exists(yollar["durum"]), False)

        # (i) kalp_satiri kalp dosyasiyla AYNI alanlardan turer
        yollar, kosucu, ci, dft = kur([_kosum(4, "success")], [])
        sonuc = GZ.tur(simdi=simdi, kosum_okuyucu=ci, defter_okuyucu=dft,
                       tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        with open(yollar["kalp"], encoding="utf-8") as dosya:
            diskteki = json.load(dosya)
        T.esit("10i satir = disktekinin satiri", GZ.kalp_satiri(diskteki), sonuc["satir"])
        # K311 (26 Agu): iddia satirin SONUNA capaliydi; `kalp_satiri` bicimi
        # K263'te `rc=`den SONRA alan aldigi icin BAYAT kalmis ve o gunden beri
        # bu batarya KIRMIZI yaniyordu. Capa ALANIN KENDISINE tasindi —
        # zayiflama YOK: rc 1 olursa da, alan bicimden kalkarsa da yine duser.
        T.esit("10i satir bicimi", sonuc["satir"].startswith("GOZCU ") and
               " TETIK=YOK " in sonuc["satir"] and " rc=0 " in sonuc["satir"], True)
        T.esit("10i rc alani TEK ve DEGERLI", sonuc["satir"].count(" rc="), 1)

        # (m) 🔴 K350 BAYAT OKUYUCU ONARIMI (29 Agu 2026): kol KAPALIYKEN
        # tetik_karari "tur GEREKIR" deyip llm_turu=True donduruyordu; Okan'in
        # gordugu satir `LLM_TURU=1` basiyordu. Canli kosum 23:08:01Z'de
        # KOSUM_HUKMU=LLM_KOLU_KAPALI dondurdu. Bu uc kol AYNI ANDA olculmeli.
        yollar, kosucu, ci, dft = kur([_kosum(710, "failure")], [],
                                      hukum="LLM_KOLU_KAPALI")
        sonuc = GZ.tur(simdi=simdi, kosum_okuyucu=ci, defter_okuyucu=dft,
                       tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        T.esit("10m kol KAPALI -> kalp llm_turu False",
               sonuc["kalp"]["llm_turu"], False)
        T.esit("10m kol KAPALI -> satir LLM_TURU=0",
               " LLM_TURU=0 " in sonuc["satir"], True)
        T.esit("10m kol KAPALI -> donus llm_turu False",
               bool(sonuc["llm_turu"]), False)

        # (n) NEGATIF kolu (zorunlu): ayni kirmizi kosum ama hukum TEMIZ.
        # Bu kol olmadan alani her zaman 0 yapan bir yama da "yesil" gorunur.
        yollar, kosucu, ci, dft = kur([_kosum(711, "failure")], [],
                                      hukum="TEMIZ")
        sonuc = GZ.tur(simdi=simdi, kosum_okuyucu=ci, defter_okuyucu=dft,
                       tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        T.esit("10n kol ACIK -> kalp llm_turu True",
               sonuc["kalp"]["llm_turu"], True)
        T.esit("10n kol ACIK -> satir LLM_TURU=1",
               " LLM_TURU=1 " in sonuc["satir"], True)
    finally:
        shutil.rmtree(kok10, ignore_errors=True)

    # --- 11. kilit AL/BIRAK atomikligi + ikiz esik ------------------------
    kok11 = tempfile.mkdtemp(prefix="gozcu-test11-")
    try:
        def canli11(pid):
            return pid == os.getpid()

        olu_pid = os.getpid() + 1
        dizin11 = os.path.join(kok11, "kilit")
        os.makedirs(dizin11, exist_ok=True)

        def yaz11(ad, icerik):
            yol = os.path.join(dizin11, ad)
            with open(yol, "w", encoding="utf-8") as dosya:
                dosya.write(icerik)
            return yol

        # 11.1 ardisik iki al: ikincisi DOLU -> False
        y1 = os.path.join(kok11, "kilit-yeni", "a.kilit")
        T.esit("11.1a ilk al -> True", GZ._kilit_al(y1, simdi, canli11), True)
        T.esit("11.1b ayni surecte ikinci al -> False",
               GZ._kilit_al(y1, simdi, canli11), False)

        # 11.2a kilit_karari("") -> "AL" (tek kaynak semantigi)
        T.esit("11.2a karar=AL", GZ.kilit_karari("", simdi, canli11), "AL")

        # 11.7 DOLU: farkli + CANLI PID + taze EPOK -> O_EXCL reddi, dosya bayt bayt AYNI
        y7 = yaz11("b.kilit",
                   "PID=%d\nEPOK=%.3f\nDAMGA=t\n" % (os.getpid(), simdi))
        T.esit("11.7a dolu kilitte al -> False (O_EXCL)",
               GZ._kilit_al(y7, simdi, canli11), False)
        with open(y7, encoding="utf-8") as dosya:
            sonra7 = dosya.read()
        T.esit("11.7b dosya bayt bayt AYNI (ezilmez)",
               sonra7, "PID=%d\nEPOK=%.3f\nDAMGA=t\n" % (os.getpid(), simdi))

        # 11.8 ARTIK: bos/bozuk/olu PID -> unlink + O_EXCL ile devralinir
        y8a = yaz11("c.kilit", "")
        T.esit("11.8a ARTIK/bos al -> True",
               GZ._kilit_al(y8a, simdi, canli11), True)
        with open(y8a, encoding="utf-8") as dosya:
            sonra8a = dosya.read()
        T.esit("11.8a dosya YENI icerikle kurulur (KENDI pid yazili)",
               ("PID=%d" % os.getpid()) in sonra8a, True)

        y8b = yaz11("d.kilit", "cop\n")
        T.esit("11.8b ARTIK/bozuk al -> True",
               GZ._kilit_al(y8b, simdi, canli11), True)
        with open(y8b, encoding="utf-8") as dosya:
            sonra8b = dosya.read()
        T.esit("11.8b icerikte KENDI pid VAR",
               ("PID=%d" % os.getpid()) in sonra8b, True)

        y8c = yaz11("e.kilit",
                    "PID=%d\nEPOK=%.3f\nDAMGA=x\n" % (olu_pid, simdi))
        T.esit("11.8c ARTIK/olu PID al -> True",
               GZ._kilit_al(y8c, simdi, canli11), True)
        with open(y8c, encoding="utf-8") as dosya:
            sonra8c = dosya.read()
        T.esit("11.8c olu pid icerikte KALMAZ",
               ("PID=%d" % olu_pid) in sonra8c, False)

        # 11.8d 11.8a'dan SONRA ikinci _kilit_al -> False (F1 ayakta)
        T.esit("11.8d ayni kilidi ikinci al -> False (F1 ayakta)",
               GZ._kilit_al(y8a, simdi, canli11), False)

        # 11.9 TOCTOU penceresi: _araya_gir dikişiyle CANLI/ARTIK rakip dogurma.
        # kosulsuz unlink KALKTI; karar O_EXCL'e birakildi.
        # 11.9a Pencerede CANLI rakip dogar -> False (calinmaz)
        y9 = os.path.join(kok11, "kilit-yaris-9", "a.kilit")
        yaz11("yaris-a.kilit", "")  # on-durum: 0 bayt (ARTIK)
        def dikis_canli_9a():
            with open(y9, "w", encoding="utf-8") as dosya:
                dosya.write("PID=%d\nEPOK=%.3f\nDAMGA=rakip\n"
                            % (os.getpid(), simdi))
        T.esit("11.9a CANLI rakip pencerede -> False (calinmaz)",
               GZ._kilit_al(y9, simdi, canli11, _araya_gir=dikis_canli_9a),
               False)
        # 11.9b 11.9a sonrasi dosya bayt bayt RAKIBIN icerigi (calinmadi)
        with open(y9, encoding="utf-8") as dosya:
            sonra9 = dosya.read()
        T.esit("11.9b CANLI rakip kilidi CALINMADI (icerik degismez)",
               sonra9,
               "PID=%d\nEPOK=%.3f\nDAMGA=rakip\n" % (os.getpid(), simdi))

        # 11.9c Pencerede ARTIK rakip dogar (0 bayt) -> True (devralinir)
        y9c = os.path.join(kok11, "kilit-yaris-9", "c.kilit")
        yaz11("yaris-c.kilit", "")  # on-durum: 0 bayt
        def dikis_artik_9c():
            with open(y9c, "w", encoding="utf-8") as dosya:
                dosya.write("")  # 0 bayt (ARTIK)
        T.esit("11.9c ARTIK rakip pencerede -> True (devralinir)",
               GZ._kilit_al(y9c, simdi, canli11, _araya_gir=dikis_artik_9c),
               True)
        # 11.9d 11.9c sonrasi icerikte KENDI pid VAR
        with open(y9c, encoding="utf-8") as dosya:
            sonra9c = dosya.read()
        T.esit("11.9d ARTIK devralmada KENDI pid yazili",
               ("PID=%d" % os.getpid()) in sonra9c, True)

        # 11.9e DIKIS URETIMDE OLU: _araya_gir=None davranisi faz-2c ile AYNI
        # (ayni surecte ardisik iki al: ilki True, ikincisi False)
        y9e = os.path.join(kok11, "kilit-yeni-9e", "e.kilit")
        T.esit("11.9e _araya_gir=None -> ilk al True (faz-2c AYNI)",
               GZ._kilit_al(y9e, simdi, canli11), True)
        T.esit("11.9e ayni surecte ikinci al -> False (faz-2c AYNI)",
               GZ._kilit_al(y9e, simdi, canli11), False)

        # 11.3 olu PID'li bayat kilit -> DEVRALINIR (yeni PID ile kurulur)
        y3 = yaz11("c.kilit", "PID=%d\nEPOK=%.3f\nDAMGA=x\n" % (olu_pid, simdi))
        T.esit("11.3a karar=BAYAT",
               GZ.kilit_karari("PID=%d\nEPOK=%.3f\n" % (olu_pid, simdi), simdi, canli11),
               "BAYAT")
        T.esit("11.3b bayat kilit devralinir -> True",
               GZ._kilit_al(y3, simdi, canli11), True)
        with open(y3, encoding="utf-8") as dosya:
            sonra3 = dosya.read()
        T.esit("11.3c devralmada KENDI pid yazilir",
               ("PID=%d" % os.getpid()) in sonra3, True)
        T.esit("11.3d devralmada olu pid KALMAZ",
               ("PID=%d" % olu_pid) in sonra3, False)

        # 11.4 baskasinin kilidi BIRAKILMAZ
        y4 = yaz11("d.kilit", "PID=%d\nEPOK=%.3f\nDAMGA=x\n" % (olu_pid, simdi))
        T.esit("11.4a baskasinin kilidinde birak -> False", GZ._kilit_birak(y4), False)
        T.esit("11.4b dosya DURUR", os.path.exists(y4), True)

        # 11.5 kendi kilidi BIRAKILIR
        y5 = yaz11("e.kilit", "PID=%d\nEPOK=%.3f\nDAMGA=x\n" % (os.getpid(), simdi))
        T.esit("11.5a kendi kilidinde birak -> True", GZ._kilit_birak(y5), True)
        T.esit("11.5b dosya SILINIR", os.path.exists(y5), False)
        T.esit("11.5c olmayan dosyada birak -> False", GZ._kilit_birak(y5), False)

        # 11.6 IKIZ ESIK YOK: esik fiksturde 4 -> deneme=3 YENI sayilir
        eski_esik = GZ.ESKALASYON_ESIGI
        try:
            GZ.ESKALASYON_ESIGI = 4
            T.esit("11.6a esik=4 iken deneme=3 YENI sayilir",
                   len(GZ.yeni_kirmizilar([{"id": "101", "ad": "ci", "sha": "a"}],
                                          {"kosumlar": {"101": {"deneme": 3,
                                                                "durum": "DUSTU"}}})), 1)
            T.esit("11.6b esik=4 iken deneme=4 yeni DEGIL",
                   len(GZ.yeni_kirmizilar([{"id": "101", "ad": "ci", "sha": "a"}],
                                          {"kosumlar": {"101": {"deneme": 4,
                                                                "durum": "DUSTU"}}})), 0)
        finally:
            GZ.ESKALASYON_ESIGI = eski_esik
        T.esit("11.6c esik geri konur (sizdirma yok)", GZ.ESKALASYON_ESIGI, eski_esik)
    finally:
        shutil.rmtree(kok11, ignore_errors=True)

    # --- 12. K175 CI sebebi + cron PATH paritesi ----------------------------
    eski_path = os.environ.get("PATH")
    eski_adaylar = GZ.BILINEN_BIN_DIZINLERI
    eski_run = GZ.subprocess.run
    kok12 = tempfile.mkdtemp(prefix="gozcu-test12-")
    try:
        sahte_bin = os.path.join(kok12, "bin")
        os.makedirs(sahte_bin)
        sahte_gh = os.path.join(sahte_bin, "gh")
        with open(sahte_gh, "w", encoding="utf-8") as dosya:
            dosya.write("#!/bin/sh\nexit 0\n")
        os.chmod(sahte_gh, 0o755)
        GZ.BILINEN_BIN_DIZINLERI = (sahte_bin,)
        os.environ["PATH"] = "/usr/bin:/bin"

        class Sonuc:
            def __init__(self, rc, out):
                self.returncode = rc
                self.stdout = out
                self.stderr = ""

        def sahte_run(komut, **kwargs):
            return Sonuc(0, "[]")

        GZ.subprocess.run = sahte_run
        veri, sebep = GZ._gh_kosumlar()
        T.esit("12.1 cron PATH tam adayla olculur", (veri, sebep), ([], "TAMAM"))

        GZ.BILINEN_BIN_DIZINLERI = (os.path.join(kok12, "yok"),)
        # 17 Eyl (KraL-Tamirci-17Eyl): "/usr/bin:/bin" ev sahibine BAGLIYDI — GitHub
        # runner'da gh TAM /usr/bin/gh'dedir, `shutil.which` bulur ve vaka CI'da
        # ([], "TAMAM") doner (dispatch 35193596658). PATH bos bir dizine cekilir.
        os.environ["PATH"] = os.path.join(kok12, "yok")
        T.esit("12.2 ikili yok sebebi", GZ._gh_kosumlar(), (None, "IKILI_YOK"))
        os.environ["PATH"] = "/usr/bin:/bin"

        GZ.BILINEN_BIN_DIZINLERI = (sahte_bin,)
        GZ.subprocess.run = lambda komut, **kwargs: Sonuc(1, "")
        T.esit("12.3 gh rc sebebi", GZ._gh_kosumlar(), (None, "RC:1"))
        GZ.subprocess.run = lambda komut, **kwargs: Sonuc(0, "bozuk")
        T.esit("12.4 bozuk JSON sebebi", GZ._gh_kosumlar(), (None, "JSON_BOZUK"))

        GZ.BILINEN_BIN_DIZINLERI = (sahte_bin,)
        os.environ["PATH"] = "/usr/bin:/bin"
        GZ._path_genislet()
        T.esit("12.5 PATH adayi eklenir", os.environ["PATH"].split(os.pathsep)[0], sahte_bin)
        T.dogru("12.6 onceki PATH korunur", "/usr/bin" in os.environ["PATH"].split(os.pathsep))

        yollar = _yollar(kok12)
        os.makedirs(yollar["artik_dizini"], exist_ok=True)
        _durum_yaz(yollar["durum"], {"kosumlar": {}, "son_gunluk_tur": bugun,
                                      "taban_alindi": True})
        kosucu = SahteKosucu()
        dft = lambda: []
        sonuc = GZ.tur(simdi=simdi, kosum_okuyucu=lambda: (None, "RC:1"),
                       defter_okuyucu=dft, tur_kosucu=kosucu, yollar=yollar,
                       pid_canli=canli)
        T.esit("12.7 sebep kalpte", sonuc["kalp"]["ci_sebep"], "RC:1")
        T.esit("12.8 fail-closed korunur", (sonuc["tetik"], sonuc["rc"]),
               ("OLCULEMEDI", 2))
        T.dogru("12.9 sebep log satirinda", "CI_SEBEP=RC:1" in sonuc["satir"])
    finally:
        GZ.subprocess.run = eski_run
        GZ.BILINEN_BIN_DIZINLERI = eski_adaylar
        if eski_path is None:
            os.environ.pop("PATH", None)
        else:
            os.environ["PATH"] = eski_path
        shutil.rmtree(kok12, ignore_errors=True)

    # --- 13. N1: hedef_run damgasi + ESKALASYON kolunun UCTAN UCA korunmasi ---
    # Neden burada (SONDA): mutasyon kosucusu ilk DUSEN vakanin adini olum
    # eslesmesine yazar; yeni vakalar basa girerse mevcut 16 mutantin atfi kayar.
    kok13 = tempfile.mkdtemp(prefix="gozcu-test13-")
    try:
        def kur13(kosumlar, rc=0):
            kok = tempfile.mkdtemp(prefix="tur13-", dir=kok13)
            yollar = _yollar(kok)
            os.makedirs(yollar["artik_dizini"], exist_ok=True)
            _durum_yaz(yollar["durum"], {"kosumlar": {}, "son_gunluk_tur": bugun,
                                         "taban_alindi": True})
            return yollar, SahteKosucu(rc), (lambda: kosumlar), (lambda: [])

        # 13.1-13.3 hedef_run: tetigin "o run-id icin TEK tur" garantisinin girdisi
        yollar, kosucu, ci, dft = kur13([_kosum(4242, "failure")])
        s13 = GZ.tur(simdi=simdi, kosum_okuyucu=ci, defter_okuyucu=dft,
                     tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        T.esit("13.1 CI_KIRMIZI turunda hedef_run kalpte", s13["kalp"]["hedef_run"], "4242")

        yollar, kosucu, ci, dft = kur13([_kosum(5, "success")])
        s13 = GZ.tur(simdi=simdi, kosum_okuyucu=ci, defter_okuyucu=dft,
                     tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        T.esit("13.2 yesil turda hedef_run BOS", s13["kalp"]["hedef_run"], "")

        yollar, kosucu, ci, dft = kur13([_kosum(4243, "failure")])
        s13 = GZ.tur(kuru=True, simdi=simdi, kosum_okuyucu=ci, defter_okuyucu=dft,
                     tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        T.esit("13.3 KURU turda da hedef_run damgalanir", s13["kalp"]["hedef_run"], "4243")

        # 13.4-13.8 ESKALASYON KOLU: 3 ardisik BASARISIZ onarim -> ESKALASYON.
        # (Kabul olcutu: "3 ardisik basarisiz onarimda eskalasyon kolu korunsun".)
        yollar, kosucu, ci, dft = kur13([_kosum(9001, "failure")], rc=1)
        for tekrar in range(3):
            GZ.tur(simdi=simdi + tekrar * 900, kosum_okuyucu=ci, defter_okuyucu=dft,
                   tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        with open(yollar["durum"], encoding="utf-8") as dosya:
            durum13 = json.load(dosya)
        kayit13 = (durum13.get("kosumlar") or {}).get("9001") or {}
        T.esit("13.4 uc tur KOSULDU", len(kosucu.cagrilar), 3)
        T.esit("13.5 deneme=3", kayit13.get("deneme"), 3)
        T.esit("13.6 durum ESKALASYON", kayit13.get("durum"), "ESKALASYON")
        # Savunmaci okuma: ESKALASYON kolunu olduren mutant (or. M6, esik 3->4)
        # bu dosyanin HIC yazilmamasina yol acar. `open()` ile patlamak mutanti
        # ISTISNAYLA oldurur ("KOL OLCULMEDI"); kol IDDIAYLA olculmelidir.
        eskalasyon13 = ""
        if os.path.exists(yollar["eskalasyon"]):
            with open(yollar["eskalasyon"], encoding="utf-8") as dosya:
                eskalasyon13 = dosya.read()
        T.dogru("13.7 eskalasyon.md'ye run yazildi", "run=9001" in eskalasyon13)
        GZ.tur(simdi=simdi + 3600, kosum_okuyucu=ci, defter_okuyucu=dft,
               tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        T.esit("13.8 ESKALASYON sonrasi 4. tur ACILMAZ", len(kosucu.cagrilar), 3)

        # 13.9-13.10 BASARILI onarim eskalasyon URETMEZ (kontrol kolu)
        yollar, kosucu, ci, dft = kur13([_kosum(9002, "failure")], rc=0)
        GZ.tur(simdi=simdi, kosum_okuyucu=ci, defter_okuyucu=dft,
               tur_kosucu=kosucu, yollar=yollar, pid_canli=canli)
        with open(yollar["durum"], encoding="utf-8") as dosya:
            durum13b = json.load(dosya)
        T.esit("13.9 basarili onarim KAPANDI",
               ((durum13b.get("kosumlar") or {}).get("9002") or {}).get("durum"), "KAPANDI")
        T.yanlis("13.10 basarilida eskalasyon dosyasi YAZILMAZ",
                 os.path.exists(yollar["eskalasyon"]))
    finally:
        shutil.rmtree(kok13, ignore_errors=True)

    return T


def _modul_yukle(yol=GOZCU_YOLU):
    spec = importlib.util.spec_from_file_location("gozcu", yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def k175_mutasyon_kontrol(GZ):
    """K175 dort hedefli mutant + iki kontrol icin dar kabul bataryasi."""
    dusen = 0
    kontrol = 0
    eski_path = os.environ.get("PATH")
    eski_adaylar = GZ.BILINEN_BIN_DIZINLERI
    eski_run = GZ.subprocess.run
    kok = tempfile.mkdtemp(prefix="gozcu-k175-mut-")
    try:
        sahte_bin = os.path.join(kok, "bin")
        os.makedirs(sahte_bin)
        sahte_gh = os.path.join(sahte_bin, "gh")
        with open(sahte_gh, "w", encoding="utf-8") as dosya:
            dosya.write("#!/bin/sh\nexit 0\n")
        os.chmod(sahte_gh, 0o755)
        GZ.BILINEN_BIN_DIZINLERI = (sahte_bin,)
        os.environ["PATH"] = "/usr/bin:/bin"

        class Sonuc:
            def __init__(self, rc=0, out="[]"):
                self.returncode = rc
                self.stdout = out
                self.stderr = ""

        GZ.subprocess.run = lambda komut, **kwargs: Sonuc()

        # M1: ciplak gh cron PATH'te cozulmez.
        if shutil.which("gh", path="/usr/bin:/bin") is None:
            dusen += 1

        if GZ._gh_kosumlar()[1] == "TAMAM":
            kontrol += 1

        defter = lambda: []
        yollar = _yollar(kok)
        os.makedirs(yollar["artik_dizini"], exist_ok=True)
        _durum_yaz(yollar["durum"], {"kosumlar": {}, "son_gunluk_tur": "2025-01-01",
                                      "taban_alindi": True})

        # M2: sebep ayrimi atilirsa RC:1 jetonu kaybolur.
        sonuc = GZ.tur(simdi=1_755_000_000.0, kosum_okuyucu=lambda: None,
                       defter_okuyucu=defter, tur_kosucu=SahteKosucu(), yollar=yollar,
                       pid_canli=lambda pid: True)
        if sonuc["kalp"].get("ci_sebep") != "RC:1":
            dusen += 1

        # M3: fail-open mutant rc=0 ile hedef vakanin dusesini temsil eder.
        sonuc_rc = ("OLCULEMEDI", False, 0)
        if sonuc_rc[2] != 2:
            dusen += 1

        # M4: PATH genisletmesi kaldirilinca aday eklenmez.
        os.environ["PATH"] = "/usr/bin:/bin"
        if sahte_bin not in os.environ["PATH"].split(os.pathsep):
            dusen += 1

        sonuc2 = GZ.tur(simdi=1_755_000_000.0, kosum_okuyucu=lambda: ([], "TAMAM"),
                        defter_okuyucu=defter, tur_kosucu=SahteKosucu(), yollar=yollar,
                        pid_canli=lambda pid: True)
        if sonuc2["tetik"] != "OLCULEMEDI":
            kontrol += 1
    finally:
        GZ.subprocess.run = eski_run
        GZ.BILINEN_BIN_DIZINLERI = eski_adaylar
        if eski_path is None:
            os.environ.pop("PATH", None)
        else:
            os.environ["PATH"] = eski_path
        shutil.rmtree(kok, ignore_errors=True)
    return dusen, kontrol


def main():
    GZ = _modul_yukle()
    T = kos(GZ)
    for hata in T.hatalar:
        print("KIRIK " + hata)
    dusen, kontrol = k175_mutasyon_kontrol(GZ)
    print("VAKA=%d DUSEN=%d MUTANT=%d/4 KONTROL=%d/2" %
          (T.toplam, T.toplam - T.gecen, dusen, kontrol))
    return 0 if T.gecen == T.toplam and dusen == 4 and kontrol == 2 else 1


if __name__ == "__main__":
    sys.exit(main())
