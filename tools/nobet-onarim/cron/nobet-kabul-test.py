#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nobet-kapi.py kabul testi — saf fikstur; canli cron/mail/ag GEREKTIRMEZ.

Kosum: python3 /Users/okan/.claude/cron/nobet-kabul-test.py   (rc=0 => YESIL)
Vaka 1-9   : SPEC-nobet-onarim-bacagi.md "KABUL TESTI" (mutant M1..M5)
Vaka 10-19 : SPEC-kabul-komutu-el-kitabi.md C1..C6 — KABUL KOMUTU ekseni (mutant N1..N6)
Vaka 28-30 : 15 Agu ONARIMSIZ_SUPURME + ustuste onarimsiz sayaci (mutant M-A/M-B)
Vaka 31-34 : 15 Agu tur suresi tavani + atlama sayaci (mutant M-C/M-D/M-E)
Her vaka en az bir OLDURUCU MUTANT'i kirmizi yakmak icin vardir.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

# Kanonik dosya adi tire tasiyor; modul olarak yoldan yuklenir (ikinci kopya ACILMAZ).
_YOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nobet-kapi.py")
_SPEC = importlib.util.spec_from_file_location("nobet_kapi", _YOL)
kapi = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(kapi)


# --- fikstur yardimcilari --------------------------------------------------

# 🔴 W2 (16 Eyl 2026) — K316 SINIFI, FIKSTUR TARAFI. Geri-iz fiksturlerinde
# kalemin katini ELLE YAZILI `"kimi"` tasiyordu. 6 Eyl motor kararindan sonra
# `kimi` EMEKLI oldu; emekli ad turun basinda `ESKALASYON_BAYAT` gocunu
# tetikliyor ve merdiven sayacini BIR BASAMAK ileri itiyor (olculdu 16 Eyl:
# vaka 6'da SAYILIR=1 SAYAC=4 BASAMAK=KRAL->BABA, kalem HEM eskale edilip HEM
# yeniden dagitildi -> `dagitilan=1`, beklenen 0). Fikstur kati artik TEK
# KAYNAKTAN (mimar_kimlik -> CANLI_ISCI_MOTORLARI) turer; motor sirasi bir daha
# degistiginde bu vakalar SESSIZCE ayrisamaz.
#
# 🔴 OLCULDU VE GERI ALINDI (16 Eyl 2026, W2): dort fiksturun DORDU birden
# `FIKSTUR_KAT`e cevrilince vaka 6 ve 8 YESILE dondu ama vaka 5 · 11 KIRMIZI
# yandi (`dagitilan=0 hukum=ONARIMSIZ_TUR`) ve K316 mutant ankraji TEKIL
# olmaktan cikti (`ankraj: 0`). Yani `"kimi"` literali bu uc vakada YUK
# TASIYOR — emekli ad, goc kolunu ve dagitim kolunu BILEREK tetikliyor.
# Toplu cevirme bu yuzden SINIF ONARIMI DEGIL, uc vakayi sessizce baska bir
# davranisa tasiyan bir DARALTMA olurdu. Dogru onarim: goc kolunu ozne alan
# vakalar (5 · 11 · 41) emekli adi ACIKCA tasir, geri kalanlar tek kaynaktan
# turer — ve bu ayrim vaka 6'nin merdiven basamagi ile BIRLIKTE olculur.
# SIRADAKI DILIME BIRAKILDI (mimara giden is raporunun "kalan" bolumu).
FIKSTUR_KAT = (kapi.CANLI_ISCI_MOTORLARI[0] if kapi.CANLI_ISCI_MOTORLARI
               else kapi.VARSAYILAN_KAT)

DEFTER_BASI = "\n".join([
    "# fikstur defteri",
    "",
    "| id | tarih | kimden→kime | iş (tek cümle) | durum | kapanış kanıtı |",
    "|---|---|---|---|---|---|",
])


def satir(kimlik, kime, metin, durum, kabul=""):
    kanit = "—" if not kabul else "— · kabul: `%s`" % kabul
    return "| %s | 2026-08-14 | Tamirci→%s | %s | %s | %s |" % (
        kimlik, kime, metin, durum, kanit)


def defter(satirlar):
    return DEFTER_BASI + "\n" + "\n".join(satirlar) + "\n"


class Tezgah(object):
    """kapi modulunun disk yollarini gecici dizine baglar (fikstur izolasyonu)."""

    def __init__(self, defter_metni, geri_iz=None, raporlar=None, betikler=None):
        self.defter_metni = defter_metni
        self.geri_iz = geri_iz or {"tur_no": 0, "kalemler": {}}
        self.raporlar = raporlar or {}
        self.betikler = betikler or {}      # {"ad.py": cikis_kodu}
        self.dagitim_komutlari = []

    def __enter__(self):
        self.kok = tempfile.mkdtemp(prefix="nobet-kabul-")
        self.eski = {ad: getattr(kapi, ad) for ad in
                     ("DEFTER_YOLU", "GERI_IZ_YOLU", "RAPOR_DIZINI",
                      "SPEC_DIZINI", "KILIT_YOLU", "ONARIMSIZ_SAYAC_YOLU",
                      "ATLANAN_SAYAC_YOLU", "KARANTINA_YOLU",
                      "DONDURMA_BAYRAK_YOLU")}
        kapi.DEFTER_YOLU = os.path.join(self.kok, "acik-kalemler.md")
        kapi.GERI_IZ_YOLU = os.path.join(self.kok, "geri-iz.json")
        kapi.RAPOR_DIZINI = os.path.join(self.kok, "raporlar")
        kapi.SPEC_DIZINI = os.path.join(self.kok, "specler")
        kapi.KILIT_YOLU = os.path.join(self.kok, "tur.kilit")
        kapi.ONARIMSIZ_SAYAC_YOLU = os.path.join(self.kok, "onarimsiz-sayac.json")
        kapi.ATLANAN_SAYAC_YOLU = os.path.join(self.kok, "atlanan-sayac.json")
        kapi.KARANTINA_YOLU = os.path.join(self.kok, "motor-karantina")
        # Dondurma bayragi: gercek dosyayi degil, YOK bir yola bagla — boylece
        # 40 eski vaka bayraksiz gibi calisir. D1-D4 vakalari env ile AÇIK/KAPALI
        # yapar (kapinin `PRUVO_NOBET_DONDURMA` ezmesi oncelikli).
        kapi.DONDURMA_BAYRAK_YOLU = os.path.join(self.kok, "nobet-dondurma.json")
        os.makedirs(kapi.RAPOR_DIZINI)
        os.makedirs(kapi.SPEC_DIZINI)
        # C4 beyaz listesi fikstur icin gecici koke baglanir: kabul komutlari
        # GERCEK dogrulama + GERCEK kosum yolundan gecer, ama repoya/cron'a dosya
        # birakmaz. Guvenlik vakalari (14-16) GERCEK beyaz listeyi kullanir.
        self.betik_koku = os.path.join(self.kok, "betikler")
        os.makedirs(self.betik_koku)
        self.kabul_cagrilari = []
        for ad, cikis in self.betikler.items():
            self.betik(ad, cikis)
        # `{BETIK}` = fikstur beyaz liste koku (dizin __enter__'da dogar).
        with open(kapi.DEFTER_YOLU, "w", encoding="utf-8") as dosya:
            dosya.write(self.defter_metni.replace("{BETIK}", self.betik_koku))
        for ad, icerik in self.raporlar.items():
            with open(os.path.join(kapi.RAPOR_DIZINI, ad), "w", encoding="utf-8") as dosya:
                dosya.write(icerik.replace("{BETIK}", self.betik_koku))
        kapi.geri_iz_yaz(self.geri_iz, kapi.GERI_IZ_YOLU)
        return self

    def __exit__(self, *_):
        for ad, deger in self.eski.items():
            setattr(kapi, ad, deger)
        shutil.rmtree(self.kok, ignore_errors=True)
        return False

    def calistirici(self, komut, log):
        self.dagitim_komutlari.append(komut)
        return 40000 + len(self.dagitim_komutlari)

    def betik(self, ad, cikis=0):
        """Beyaz liste kokune `cikis` koduyla donen bir kabul betigi koyar."""
        yol = os.path.join(self.betik_koku, ad)
        with open(yol, "w", encoding="utf-8") as dosya:
            dosya.write("import sys\nsys.exit(%d)\n" % cikis)
        return yol

    def kabul_kosucu(self, komut):
        """GERCEK dogrulama + GERCEK kosum; yalniz beyaz liste koku fiksturdur."""
        self.kabul_cagrilari.append(komut)
        return kapi.kabul_komutu_kos(komut, koklar=(self.betik_koku,))

    def kapat(self, kuru=False, kabul_kosucu=None, defter_once=None, tasinan=0):
        return kapi.tur_kapat(kuru=kuru, calistirici=self.calistirici,
                              kabul_kosucu=kabul_kosucu or self.kabul_kosucu,
                              defter_once=defter_once, tasinan=tasinan)


# --- vakalar ---------------------------------------------------------------

def vaka1_onarimsiz_tur_basarisiz():
    """1) ACIK_KALEM=3, KAPANAN=0, DAGITILAN=0 -> tur BASARISIZ (M1)."""
    metin = defter([satir("K01", "Okan", "🔧 iyzico ödeme paneli kararı", "🔧"),
                    satir("K02", "Okan", "🔧 shop worker deploy hükmü", "🔧"),
                    satir("K03", "Okan", "🔧 üyelik yenileme kararı", "🔧")])
    with Tezgah(metin) as t:
        s = t.kapat()
    assert s["acik"] == 3, s["acik"]
    assert s["kapanan"] == 0 and s["dagitilan"] == 0, s
    assert s["rc"] != 0, "onarimsiz tur rc=0 dondu (H1 kapisi YOK)"
    assert s["hukum"] == "ONARIMSIZ_TUR", s["hukum"]
    # saf kural da ayni yonde
    assert kapi.tur_hukmu(3, 0, 0)[0] != 0
    assert kapi.tur_hukmu(3, 0, 0)[1] == "ONARIMSIZ_TUR"
    return "ACIK=3 KAPANAN=0 DAGITILAN=0 -> rc=%d %s" % (s["rc"], s["hukum"])


def vaka2_dagitim_mesru_kapanistir():
    """2) ACIK_KALEM=3, KAPANAN=0, DAGITILAN=2 -> tur GECER."""
    metin = defter([satir("K01", "Okan", "🔧 iyzico ödeme paneli kararı", "🔧"),
                    satir("K02", "Tamirci", "🔧 tarama kök neden sessizce geçiyor", "🔧"),
                    satir("K03", "Tamirci", "🔧 log okuma sayım taşıması eksik", "🔧")])
    with Tezgah(metin) as t:
        s = t.kapat()
    assert s["acik"] == 3, s
    assert s["dagitilan"] == 2, s["dagitilan"]
    assert s["kapanan"] == 0, s
    assert s["rc"] == 0 and s["hukum"] == "ONARIM_ILERLIYOR", s
    assert len(t.dagitim_komutlari) == 2, t.dagitim_komutlari
    return "ACIK=3 DAGITILAN=2 -> rc=0 %s" % s["hukum"]


def vaka3_gercekten_temiz_tur():
    """3) ACIK_KALEM=0 -> tur GECER (tek mesru 'temiz tur')."""
    metin = defter([satir("K01", "KraL", "kapandı iş", "KAPANDI"),
                    satir("K02", "KraL", "uçuşta iş", "UCUSTA")])
    with Tezgah(metin) as t:
        s = t.kapat()
    assert s["acik"] == 0 and s["dagitilan"] == 0 and s["kapanan"] == 0, s
    assert s["rc"] == 0 and s["hukum"] == "TEMIZ", s
    return "ACIK=0 -> rc=0 TEMIZ"


def vaka4_fanout_tavani_ve_sirada():
    """4) 9 bagimsiz kirmizi -> 4 es zamanli dagitilir, SIRADA=5 basilir (M2)."""
    satirlar = [satir("K%02d" % i, "Tamirci", "🔧 tarama kök neden kırmızı %d" % i, "🔧")
                for i in range(1, 10)]
    with Tezgah(defter(satirlar)) as t:
        s = t.kapat()
        rapor = s["rapor"]
    assert s["acik"] == 9, s["acik"]
    assert s["dagitilan"] == 4, "fan-out tavani 4 degil: %d" % s["dagitilan"]
    assert s["sirada"] == 5, "SIRADA yanlis: %d" % s["sirada"]
    assert "SIRADA=5" in rapor, "SIRADA satiri BASILMADI (sessiz dusurme)"
    assert len(t.dagitim_komutlari) == 4, t.dagitim_komutlari
    assert s["rc"] == 0, s
    return "ACIK=9 DAGITILAN=4 SIRADA=5"


def vaka5_raporsuz_is_duser_ve_yeniden_dagitilir():
    """5) Dagitilan kalem 2 tur rapor uretmezse DUSTU + YENIDEN dagitim (M3)."""
    metin = defter([satir("K01", "Tamirci", "🔧 tarama kök neden bulunacak", "🔧")])
    geri_iz = {"tur_no": 2, "kalemler": {"K01": {
        "id": "K01", "etiket": "nobet-K01-t1", "tur": 1, "kat": "kimi",
        "rapor_yolu": "/yok/rapor-yok.md", "durum": "DAGITILDI",
        "dagitim_sayisi": 1}}}
    with Tezgah(metin, geri_iz=geri_iz) as t:
        s = t.kapat()
        yeni = kapi.geri_iz_oku(kapi.GERI_IZ_YOLU)
    assert s["kapanan"] == 0, "rapor YOKken kalem KAPANDI sayildi (fail-open)"
    assert s["dagitilan"] == 1, "dusen kalem YENIDEN dagitilmadi: %s" % s
    assert yeni["kalemler"]["K01"]["dagitim_sayisi"] == 2, yeni["kalemler"]["K01"]
    # kontrol kolu: rapor VARSA, HUKUM=KAPANDI ise VE kabul komutu rc=0 verirse kapanir
    # (C3, 14 Agu: rapor tek basina yetmez — komut kosulur.)
    geri_iz2 = {"tur_no": 2, "kalemler": {"K01": {
        "id": "K01", "etiket": "nobet-K01-t1", "tur": 1, "kat": "kimi",
        "rapor_yolu": "KAPANDI_RAPORU", "durum": "DAGITILDI", "dagitim_sayisi": 1}}}
    metin2 = defter([satir("K01", "Tamirci", "🔧 tarama kök neden bulunacak", "🔧",
                           kabul="python3 {BETIK}/yesil.py")])
    with Tezgah(metin2, geri_iz=geri_iz2, betikler={"yesil.py": 0},
                raporlar={"nobet-K01-t1.md": "KABUL: TEST_RC=0\nHUKUM=KAPANDI\n"}) as t:
        t.geri_iz["kalemler"]["K01"]["rapor_yolu"] = os.path.join(
            kapi.RAPOR_DIZINI, "nobet-K01-t1.md")
        kapi.geri_iz_yaz(t.geri_iz, kapi.GERI_IZ_YOLU)
        s2 = t.kapat()
    assert s2["kapanan"] == 1, "HUKUM=KAPANDI raporu sayilmadi: %s" % s2
    return "raporsuz -> DUSTU+yeniden (dagitim=2) · HUKUM=KAPANDI -> KAPANAN=1"


def vaka6_ucuncu_turda_eskalasyon():
    """6) 3. dagitimda hala acik -> ESKALASYON=OKAN."""
    metin = defter([satir("K01", "Tamirci", "🔧 tarama kök neden bulunacak", "🔧")])
    geri_iz = {"tur_no": 2, "kalemler": {"K01": {
        "id": "K01", "etiket": "nobet-K01-t1", "tur": 1, "kat": "kimi",
        "rapor_yolu": "/yok/rapor-yok.md", "durum": "DAGITILDI",
        "dagitim_sayisi": 3}}}
    with Tezgah(metin, geri_iz=geri_iz) as t:
        s = t.kapat()
        yeni = kapi.geri_iz_oku(kapi.GERI_IZ_YOLU)
        # ikinci tur: eskale kalem YENIDEN dagitilmaz, ama satiri basilmaya devam eder
        s2 = t.kapat()
    assert s["eskalasyon"] == ["K01"], s["eskalasyon"]
    assert "ESKALASYON=OKAN" in s["rapor"], "eskalasyon satiri basilmadi"
    assert s["dagitilan"] == 0, "eskale kalem yine dagitildi: %s" % s
    assert s["rc"] != 0, "eskalasyon turu sessiz yesil gecti"
    assert yeni["kalemler"]["K01"]["durum"] == "ESKALASYON", yeni["kalemler"]["K01"]
    assert s2["dagitilan"] == 0, "eskale kalem sonraki turda yeniden dagitildi"
    assert "ESKALASYON=OKAN" in s2["rapor"], "eskalasyon satiri sonraki turda kayboldu"
    return "3. dagitim raporsuz -> ESKALASYON=OKAN (yeniden dagitim 0, satir kalici)"


def vaka7_motor_dusmesi_sessiz_olmaz():
    """7) Motor 429 -> yedege duser; hepsi duserse MOTOR_YOK + rc!=0 (M4)."""
    dusen = {"deepseek-pro": (1, "API Error: 429 Token Plan usage limit reached"),
             "deepseek-flash": (1, "Error 429 rate limit"),
             "codex": (1, "quota exceeded")}
    sonuc = kapi.motor_zinciri_kos(("deepseek-pro", "deepseek-flash", "codex"),
                                   lambda m: dusen[m])
    assert sonuc["rc"] != 0, "hepsi duserken rc=0 dondu (429 sessizce yutuldu)"
    assert sonuc["hukum"] == "MOTOR_YOK", sonuc["hukum"]
    assert [d["sebep"] for d in sonuc["denemeler"]] == ["KOTA", "KOTA", "KOTA"], sonuc
    # yedege dusme kolu: ilk motor 429, ikincisi yesil
    kismi = {"minimax-m3": (1, "429 usage limit"), "deepseek-pro": (0, "SUMMARY: ...")}
    s2 = kapi.motor_zinciri_kos(("minimax-m3", "deepseek-pro"), lambda m: kismi[m])
    assert s2["rc"] == 0 and s2["motor"] == "deepseek-pro", s2
    # kosum id'si icindeki 429 kota reddi SAYILMAZ (yanlis pozitif nobeti)
    assert kapi.kota_reddi_mi("gh run 31740898072 failed", 1) is False
    assert kapi.kota_reddi_mi("429 usage limit", 0) is False
    return "3 motor 429 -> MOTOR_YOK rc=%d · yedege dusme calisti" % sonuc["rc"]


def vaka8_sessiz_hata_sinifi_mimara_gider():
    """8) Sessiz-hata sinifi kalem Claude'a DEGIL MIMAR'a yonlendirilir (M5)."""
    sessiz = [
        {"is": "🔧 `ic-rapor-adi-kapisi.py` kancada YOK, kapı sessizce fail-open",
         "kime": "Tamirci", "durum_ham": "🔧"},
        {"is": "🔧 `d1-sync.py` yazici yolunda kilit YOK (flock)", "kime": "Tamirci",
         "durum_ham": "🔧"},
        {"is": "🔧 ödeme sunucusu kalemi reddediyor", "kime": "Tamirci", "durum_ham": "🔧"},
        {"is": "🔧 şema göçü kolon eksik", "kime": "Tamirci", "durum_ham": "🔧"},
        {"is": "🔧 mutasyon bataryası kapsam deliği bildiriyor", "kime": "Tamirci",
         "durum_ham": "🔧"},
    ]
    for kalem in sessiz:
        kat = kapi.kat_sec(kalem)
        assert kat == "MIMAR", "sessiz-hata sinifi %s katina gitti: %s" % (kat, kalem["is"])
    # hicbir kalem HICBIR kosulda claude iscisine gitmez
    havuz = sessiz + [
        {"is": "log okuma sayım taşıması", "kime": "Tamirci", "durum_ham": "🔧"},
        {"is": "teşhis: kök neden bulunacak", "kime": "Tamirci", "durum_ham": "🔧"},
        {"is": "hiçbir jetona uymayan iş", "kime": "Tamirci", "durum_ham": "🔧"},
        {"is": "shop worker deploy hükmü", "kime": "Okan", "durum_ham": "🔧"},
    ]
    for kalem in havuz:
        assert kapi.kat_sec(kalem) != "claude", kalem
    assert kapi.kat_sec(havuz[-1]) == "OKAN", "Okan kalemi dagitildi"
    # 🔴 K316: MOTOR ADI ELLE YAZILMAZ. Bu satirlar 20 Agu'da Okan sirayi ters
    # cevirene (m3 BIRINCIL) kadar dogruydu, sonra kaynaktan SESSIZCE ayristi ve
    # 7 gun bataryayi kirmizi yakti. Iddia artik ADA degil SINIFA baglanir:
    # FLASH jetonu -> mekanik kat · PRO jetonu -> tarama kati · jetonsuz ->
    # varsayilan (birincil). Adlar TEK KAYNAKTAN turer.
    # 🔴 W2 (16 Eyl 2026) — K316'nin AYNI SINIFI, IKINCI KEZ: burada
    # `CANLI_ISCI_MOTORLARI[1]` ELLE YAZILMIS bir ARITE VARSAYIMIYDI. 6 Eyl
    # motor karariyla canli kume TEKE indi (`minimax-m3`); kaynak (nobet-kapi.py
    # :217) bu hali ZATEN dogru ele aliyor (`len>1 degilse KAT_MEKANIK=KAT_TARAMA`)
    # ama batarya indeksi sabit tuttugu icin IndexError ile COKTU — yani
    # "turetilebilir degerin elle kopyalanmasi" kusuru olcen tarafa gocmusti.
    # Beklenti artik AYNI TEK KAYNAKTAN, AYNI arite kuraliyla turer.
    motorlar = tuple(kapi.CANLI_ISCI_MOTORLARI)
    assert motorlar, "canli motor kumesi OLCULEMEDI (mimar_kimlik yuklenemedi)"
    assert kapi.KAT_TARAMA == motorlar[0], kapi.KAT_TARAMA
    beklenen_mekanik = motorlar[1] if len(motorlar) > 1 else motorlar[0]
    assert kapi.KAT_MEKANIK == beklenen_mekanik, kapi.KAT_MEKANIK
    assert kapi.VARSAYILAN_KAT == kapi.KAT_TARAMA, kapi.VARSAYILAN_KAT
    # 🔴 KAT AYRIMI SESSIZCE ATLANMAZ, ADIYLA BASILIR: tek motorlu kumede iki
    # katin AYNI motora dusmesi DOGRU davranistir, ama bu bir KAPSAM KAYBIDIR
    # (yuk bolme kolu fiilen yok) ve rapor satirinda GORUNUR kalir.
    if len(motorlar) > 1:
        assert kapi.KAT_TARAMA != kapi.KAT_MEKANIK, "iki kat AYNI motora dustu"
        kat_ayrimi = "VAR"
    else:
        assert kapi.KAT_TARAMA == kapi.KAT_MEKANIK, "tek motorlu kumede kat AYRISTI"
        kat_ayrimi = "YOK(tek-motor)"
    assert kapi.kat_sec(havuz[-4]) == kapi.KAT_MEKANIK, kapi.kat_sec(havuz[-4])
    assert kapi.kat_sec(havuz[-3]) == kapi.KAT_TARAMA, kapi.kat_sec(havuz[-3])
    assert kapi.kat_sec(havuz[-2]) == kapi.VARSAYILAN_KAT, "varsayilan kat AYRISTI"
    # zincirlerin HICBIRINDE claude yok
    for zincir in kapi.ISCI_YEDEK_ZINCIRI.values():
        assert "claude" not in zincir, zincir
    return ("5 sessiz-hata kalemi -> MIMAR · claude 0 kez · MOTOR_SAYISI=%d "
            "KAT_AYRIMI=%s" % (len(motorlar), kat_ayrimi))


def vaka9_kilit_es_zamanli_turu_engeller():
    """9) Onceki tur suruyorsa yeni tur ONCEKI_TUR_SURUYOR ile rc=0 ciker."""
    kok = tempfile.mkdtemp(prefix="nobet-kilit-")
    try:
        yol = os.path.join(kok, "tur.kilit")
        alindi, hukum = kapi.kilit_al(yol)
        assert alindi and hukum == "KILIT_ALINDI", (alindi, hukum)
        alindi2, hukum2 = kapi.kilit_al(yol)
        assert alindi2 is False, "kilit doluyken ikinci tur atesledi (es zamanli tur)"
        assert hukum2 == "ONCEKI_TUR_SURUYOR", hukum2
        # bayat kilit calinir: olu PID
        assert kapi.kilit_karari("PID=999999\nEPOK=%d\n" % kapi.time.time(),
                                 kapi.time.time(), lambda p: False) == "BAYAT"
        # yasli kilit calinir
        assert kapi.kilit_karari("PID=1\nEPOK=1\n", 10 ** 10, lambda p: True) == "BAYAT"
        # canli PID + taze damga: DOLU
        assert kapi.kilit_karari("PID=%d\nEPOK=%d\n" % (os.getpid(), kapi.time.time()),
                                 kapi.time.time(), lambda p: True) == "DOLU"
        assert kapi.kilit_birak(yol) is True
        alindi3, _ = kapi.kilit_al(yol)
        assert alindi3 is True, "birakilan kilit yeniden alinamadi"
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return "kilit: 2. tur ONCEKI_TUR_SURUYOR (rc=0), bayat kilit calinir"


# --- C paketi: KABUL KOMUTU ekseni (vaka 10-19) ----------------------------

KAPANDI_RAPORU = "KALEM=K01\nKABUL: TEST_RC=0\nHUKUM=KAPANDI\n"


def _tek_kalem_tezgahi(kabul="", rapor=KAPANDI_RAPORU, betikler=None):
    """Tek DAGITILDI kalemi + raporu olan tezgah (C paketi vakalarinin iskeleti)."""
    metin = defter([satir("K01", "Tamirci", "🔧 tarama kök neden bulunacak", "🔧", kabul=kabul)])
    geri_iz = {"tur_no": 1, "kalemler": {"K01": {
        "id": "K01", "etiket": "nobet-K01-t1", "tur": 1, "kat": "kimi",
        "rapor_yolu": "KAPANDI_RAPORU", "durum": "DAGITILDI", "dagitim_sayisi": 1}}}
    return Tezgah(metin, geri_iz=geri_iz, betikler=betikler or {},
                  raporlar={"nobet-K01-t1.md": rapor})


def _kalem_kapat(tezgah):
    """Rapor yolunu fikstur dizinine baglar ve turu kapatir."""
    tezgah.geri_iz["kalemler"]["K01"]["rapor_yolu"] = os.path.join(
        kapi.RAPOR_DIZINI, "nobet-K01-t1.md")
    kapi.geri_iz_yaz(tezgah.geri_iz, kapi.GERI_IZ_YOLU)
    return tezgah.kapat()


def vaka10_kabul_dolu_rc0_kapanir():
    """10) C3: kabul dolu + rapor KAPANDI + komut rc=0 -> KAPANDI (N1 kontrol kolu)."""
    with _tek_kalem_tezgahi(kabul="python3 {BETIK}/yesil.py",
                            betikler={"yesil.py": 0}) as t:
        s = _kalem_kapat(t)
        yeni = kapi.geri_iz_oku(kapi.GERI_IZ_YOLU)
    assert s["kapanan"] == 1, "kosulan komut rc=0 iken kalem KAPANMADI: %s" % s
    assert len(t.kabul_cagrilari) == 1, "kabul komutu KOSULMADI: %s" % t.kabul_cagrilari
    assert yeni["kalemler"]["K01"]["kabul_rc"] == 0, yeni["kalemler"]["K01"]
    assert "rc=0" in (yeni["kalemler"]["K01"].get("kanit") or ""), yeni["kalemler"]["K01"]
    return "kabul dolu + rc=0 -> KAPANAN=1 (kanit: kosulan komut)"


def vaka11_beyan_var_kanit_yok():
    """11) C3: rapor KAPANDI ama komut rc!=0 -> BEYAN_VAR_KANIT_YOK, kalem ACIK (N1)."""
    with _tek_kalem_tezgahi(kabul="python3 {BETIK}/kirmizi.py",
                            betikler={"kirmizi.py": 3}) as t:
        s = _kalem_kapat(t)
        yeni = kapi.geri_iz_oku(kapi.GERI_IZ_YOLU)
    assert s["kapanan"] == 0, "komut rc!=0 iken kalem KAPANDI sayildi (beyan kanit oldu)"
    assert s["beyan_var_kanit_yok"] == ["K01"], s["beyan_var_kanit_yok"]
    assert "BEYAN_VAR_KANIT_YOK=1" in s["rapor"], "hukum satiri basilmadi"
    assert "rc=3" in s["rapor"], "olculen rc rapora basilmadi: %s" % s["rapor"]
    assert s["dagitilan"] == 1, "acik kalan kalem YENIDEN dagitilmadi: %s" % s
    assert yeni["kalemler"]["K01"]["durum"] != "KAPANDI", yeni["kalemler"]["K01"]
    assert yeni["kalemler"]["K01"]["dagitim_sayisi"] == 2, yeni["kalemler"]["K01"]
    # saf kural: rc!=0 -> BEYAN_VAR_KANIT_YOK (rapor ne derse desin)
    hukum = kapi.kalem_kabul_hukmu("HUKUM=KAPANDI", "python3 /x.py",
                                   lambda k: {"hukum": "KOSTU_KIRMIZI", "rc": 3})
    assert hukum["hukum"] == "BEYAN_VAR_KANIT_YOK" and hukum["rc"] == 3, hukum
    return "rapor KAPANDI + rc=3 -> BEYAN_VAR_KANIT_YOK, kalem ACIK + yeniden dagitildi"


def vaka12_kabul_bos_kalem_kapanamaz():
    """12) C2: kabul alani BOS + rapor KAPANDI -> kalem KAPANMAZ (N2)."""
    with _tek_kalem_tezgahi(kabul="", rapor="KALEM=K01\nHUKUM=KAPANDI\n") as t:
        s = _kalem_kapat(t)
        yeni = kapi.geri_iz_oku(kapi.GERI_IZ_YOLU)
    assert s["kapanan"] == 0, "kabul komutu YOKken kalem KAPANAN sayacina girdi"
    assert s["kabul_yok"] == ["K01"], s["kabul_yok"]
    assert "KABUL_KOMUTU_YOK=1" in s["rapor"], s["rapor"]
    assert yeni["kalemler"]["K01"]["durum"] == "DAGITILDI", yeni["kalemler"]["K01"]
    assert t.kabul_cagrilari == [], "bos alanla komut kosuldu: %s" % t.kabul_cagrilari
    assert s["kabul_bos"] == 1 and s["kabul_dolu"] == 0, s
    return "kabul BOS -> KAPANAN=0, kalem en fazla DAGITILDI (KABUL_BOS=1)"


def vaka13_rapor_bos_alani_doldurur_dolu_alani_ezmez():
    """13) C2: rapordaki KABUL_KOMUTU= BOS alani doldurur, DOLU alani EZMEZ."""
    rapor = "KALEM=K01\nKABUL_KOMUTU=python3 {BETIK}/yesil.py\nHUKUM=KAPANDI\n"
    with _tek_kalem_tezgahi(kabul="", rapor=rapor, betikler={"yesil.py": 0}) as t:
        s = _kalem_kapat(t)
        bos_yazilacak = dict(s["kabul_yazilacak"])
        bos_kapanan = s["kapanan"]
    assert bos_kapanan == 1, "rapordan gelen komut kosulmadi/kapatmadi: %s" % bos_kapanan
    assert list(bos_yazilacak) == ["K01"], bos_yazilacak
    assert bos_yazilacak["K01"].endswith("yesil.py"), bos_yazilacak
    # DOLU alan: defterdeki komut kazanir, rapordaki EZMEZ (yazilacak alan BOS kalir)
    with _tek_kalem_tezgahi(kabul="python3 {BETIK}/defter.py", rapor=rapor,
                            betikler={"yesil.py": 0, "defter.py": 0}) as t:
        s2 = _kalem_kapat(t)
        cagrilar = list(t.kabul_cagrilari)
    assert s2["kabul_yazilacak"] == {}, "DOLU kabul alani rapordan EZILDI: %s" % s2
    assert cagrilar and cagrilar[0].endswith("defter.py"), cagrilar
    # saf kural da ayni yonde
    hukum = kapi.kalem_kabul_hukmu("KABUL_KOMUTU=X\nHUKUM=KAPANDI", "DEFTERDEKI",
                                   lambda k: {"hukum": "KOSTU_YESIL", "rc": 0})
    assert hukum["kabul"] == "DEFTERDEKI" and hukum["yazilacak_kabul"] == "", hukum
    return "BOS alan rapordan DOLDU · DOLU alan EZILMEDI"


def vaka14_guvenlik_metakarakter_reddedilir():
    """14) 🔴 C4: metakarakter -> KOMUT_REDDEDILDI, HICBIR SEY kosulmaz (N3)."""
    kotu = "python3 /Users/okan/dev/pruvo/tools/x.py; rm -rf /tmp/x"
    argv, sebep = kapi.kabul_komutu_dogrula(kotu)
    assert argv is None, "zincirli komut GECERLI sayildi: %s" % argv
    assert sebep.startswith("METAKARAKTER"), sebep
    kosulan = []
    sonuc = kapi.kabul_komutu_kos(kotu, kosucu=lambda a, z: kosulan.append(a) or 0)
    assert sonuc["hukum"] == "KOMUT_REDDEDILDI", sonuc
    assert kosulan == [], "reddedilen komut YINE DE kosuldu: %s" % kosulan
    for kotu2 in ("python3 /Users/okan/dev/pruvo/tools/x.py && curl http://a",
                  "python3 /Users/okan/dev/pruvo/tools/x.py | tee /tmp/x",
                  "python3 /Users/okan/dev/pruvo/tools/x.py $(whoami)",
                  "python3 /Users/okan/dev/pruvo/tools/x.py > /tmp/x",
                  "python3 /Users/okan/dev/pruvo/tools/x.py `id`"):
        assert kapi.kabul_komutu_dogrula(kotu2)[0] is None, kotu2
    # 🔴 shell=False DINAMIK kanit: metakarakter tasiyan ARGUMAN kabuga DEGIL,
    # betige duz metin olarak gider. shell=True mutantinda betik hic kosmaz.
    kok = tempfile.mkdtemp(prefix="nobet-shell-")
    try:
        cikti = os.path.join(kok, "iz.txt")
        betik = os.path.join(kok, "yaz.py")
        with open(betik, "w", encoding="utf-8") as dosya:
            dosya.write("import sys\n"
                        "open(sys.argv[1], 'w').write(sys.argv[2])\n")
        rc = kapi._kabul_gercek_kosucu(["python3", betik, cikti, "; echo kacak"], 30)
        assert rc == 0, "gercek kosucu betigi calistiramadi rc=%s" % rc
        with open(cikti, encoding="utf-8") as dosya:
            iz = dosya.read()
        assert iz == "; echo kacak", "arguman kabuktan gecti (shell=True): %r" % iz
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return "zincir/boru/genisletme REDDEDILDI (0 kosum) · argv shell=False duz gecti"


def vaka15_guvenlik_beyaz_liste_disi_reddedilir():
    """15) 🔴 C4: yorumlayici + kok beyaz listesi (N4)."""
    kotular = [
        '/bin/sh -c "python3 /Users/okan/dev/pruvo/tools/x.py"',
        "/bin/sh -c python3",
        "bash /Users/okan/dev/pruvo/tools/x.sh",
        "python3 /etc/passwd.py",
        "python3 /Users/okan/dev/baska/x.py",
        "node /tmp/kotu.js",
        "python3 tools/gorece-yol.py",
        "python3 /Users/okan/dev/pruvo/tools/x.txt",
        "python3",
    ]
    for kotu in kotular:
        argv, sebep = kapi.kabul_komutu_dogrula(kotu)
        assert argv is None, "beyaz liste disi komut GECTI: %s (%s)" % (kotu, sebep)
    # kontrol kolu: beyaz liste ICINDEKI gercek arac GECER
    argv, sebep = kapi.kabul_komutu_dogrula(
        "python3 /Users/okan/dev/pruvo/tools/d1-sync.py --durum")
    assert argv is not None and sebep == "GECERLI", (argv, sebep)
    assert argv[0] == "python3" and argv[-1] == "--durum", argv
    # kapi kendi dosyalarini ve git/rm gibi adlari cagiramaz
    for yasak in ("python3 /Users/okan/.claude/cron/nobet-kapi.py --tur",
                  "python3 /Users/okan/.claude/cron/nobet-kabul-test.py",
                  "python3 /Users/okan/dev/pruvo/tools/x.py git",
                  "python3 /Users/okan/dev/pruvo/tools/x.py /usr/bin/rm"):
        argv2, sebep2 = kapi.kabul_komutu_dogrula(yasak)
        assert argv2 is None, "yasak ad GECTI: %s" % yasak
    return "9 beyaz-liste-disi + 4 yasak ad REDDEDILDI · gercek arac GECTI"


def vaka16_guvenlik_realpath_kok_disina_cikamaz():
    """16) 🔴 C4: `..` ile kok disina cikis realpath sonrasi REDDEDILIR (N5)."""
    kotu = "python3 /Users/okan/dev/pruvo/tools/../../../tmp/kotu.py"
    argv, sebep = kapi.kabul_komutu_dogrula(kotu)
    assert argv is None, "kok disina cikan yol GECTI: %s" % argv
    assert sebep == "BEYAZ_LISTE_DISI", sebep
    # sembolik link de cozulur: link beyaz listede, hedef DISARIDA
    kok = tempfile.mkdtemp(prefix="nobet-link-")
    try:
        hedef = os.path.join(kok, "disarida.py")
        with open(hedef, "w", encoding="utf-8") as dosya:
            dosya.write("import sys\nsys.exit(0)\n")
        link = os.path.join(kapi.BEYAZ_LISTE_KOKLERI[1], ".nobet-kabul-link-test.py")
        try:
            os.symlink(hedef, link)
            argv2, sebep2 = kapi.kabul_komutu_dogrula("python3 %s" % link)
            assert argv2 is None, "beyaz listedeki LINK disariyi gosterirken GECTI"
            assert sebep2 == "BEYAZ_LISTE_DISI", sebep2
        finally:
            if os.path.islink(link):
                os.unlink(link)
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return "`..` cikisi ve beyaz-liste-ici SEMBOLIK LINK realpath ile REDDEDILDI"


def vaka17_zaman_asimi_yesil_sayilmaz():
    """17) C4: 300 sn tavani asilirsa OLCULEMEDI, kalem KAPANMAZ (N6)."""
    assert kapi.KABUL_ZAMAN_ASIMI_SN == 300, kapi.KABUL_ZAMAN_ASIMI_SN

    def _zaman_asan(argv, zaman_asimi):
        raise subprocess.TimeoutExpired(argv, zaman_asimi)

    sonuc = kapi.kabul_komutu_kos(
        "python3 /Users/okan/dev/pruvo/tools/d1-sync.py --durum", kosucu=_zaman_asan)
    assert sonuc["hukum"] == "OLCULEMEDI", "zaman asimi YESIL sayildi: %s" % sonuc
    assert sonuc["rc"] != 0, sonuc
    hukum = kapi.kalem_kabul_hukmu("HUKUM=KAPANDI", "python3 /x.py",
                                   lambda k: {"hukum": "OLCULEMEDI", "rc": None})
    assert hukum["hukum"] == "OLCULEMEDI", hukum
    # gercek kosucu zaman asimini GERCEKTEN uyguluyor mu (1 sn'lik kanit)
    kok = tempfile.mkdtemp(prefix="nobet-zaman-")
    try:
        betik = os.path.join(kok, "uyu.py")
        with open(betik, "w", encoding="utf-8") as dosya:
            dosya.write("import time\ntime.sleep(30)\n")
        try:
            kapi._kabul_gercek_kosucu(["python3", betik], 1)
            raise AssertionError("zaman asimi ATESLEMEDI (tavan gecirilmiyor)")
        except subprocess.TimeoutExpired:
            pass
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    # tur duzleminde: OLCULEMEDI kalem KAPANMAZ
    with _tek_kalem_tezgahi(kabul="python3 {BETIK}/yok.py") as t:
        s = _kalem_kapat(t)
    assert s["kapanan"] == 0, "olculemeyen kalem KAPANDI sayildi: %s" % s
    return "zaman asimi -> OLCULEMEDI (rc!=0) · tavan 300 sn · gercek kosucuda ATESLEDI"


def vaka18_defter_yazma_siniri():
    """18) C5: yalniz durum + BOS kabul yazilir; satir sayisi oynarsa GERI ALINIR."""
    kok = tempfile.mkdtemp(prefix="nobet-defter-")
    try:
        yol = os.path.join(kok, "acik-kalemler.md")
        metin = defter([satir("K01", "Tamirci", "🔧 kapı fail-open", "🔧"),
                        satir("K02", "Tamirci", "🔧 ikinci kalem", "🔧",
                              kabul="python3 /Users/okan/dev/pruvo/tools/eski.py")])
        with open(yol, "w", encoding="utf-8") as dosya:
            dosya.write(metin)
        sonuc = kapi.defter_yaz({
            "K01": {"durum": "KAPANDI", "kabul": "python3 /a/b/yeni.py"},
            "K02": {"kabul": "python3 /a/b/ezme.py"},
        }, yol=yol)
        with open(yol, encoding="utf-8") as dosya:
            yeni = dosya.read()
        assert sonuc["hukum"] == "DEFTER_YAZMA=TAMAM", sonuc
        assert len(yeni.split("\n")) == len(metin.split("\n")), "satir sayisi degisti"
        kalemler = {k["id"]: k for k in kapi.defter_ayristir(yeni)}
        assert kalemler["K01"]["durum"] == "KAPANDI", kalemler["K01"]
        assert kalemler["K01"]["kabul"] == "python3 /a/b/yeni.py", kalemler["K01"]
        assert kalemler["K02"]["kabul"].endswith("eski.py"), "DOLU kabul alani EZILDI"
        assert kalemler["K02"]["durum"] == "🔧", "dokunulmayan durum degisti"
        # komsu hucreler BAYT BAYT ayni kalir
        eski_satir = [s for s in metin.split("\n") if s.startswith("| K01")][0].split("|")
        yeni_satir = [s for s in yeni.split("\n") if s.startswith("| K01")][0].split("|")
        assert eski_satir[1:5] == yeni_satir[1:5], (eski_satir, yeni_satir)
        # satir sayisini oynatan bir donusum: yazma GERI ALINIR, dosya DEGISMEZ
        onceki = yeni

        def _satir_ekleyen(icerik, guncellemeler):
            return icerik + "| K99 | kacak satir |\n", 1

        geri = kapi.defter_yaz({"K01": {"durum": "ACIK"}}, yol=yol,
                               donusturucu=_satir_ekleyen)
        with open(yol, encoding="utf-8") as dosya:
            son = dosya.read()
        assert geri["hukum"] == "DEFTER_YAZMA=GERI_ALINDI", geri
        assert geri["yazilan"] == 0, geri
        assert son == onceki, "GERI_ALINDI hukmune ragmen defter DEGISTI"
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return "durum+BOS kabul yazildi · DOLU alan ezilmedi · satir sayisi oynayinca GERI_ALINDI"


def vaka19_el_kitabi_spece_kabul_komutu_ekler():
    """19) C6: bilinen sinif icin dagitilan SPEC'e dogru kabul komutu satiri girer."""
    satirlar = kapi.el_kitabi_oku()
    assert len(satirlar) >= 8, "el kitabi %d satir (en az 8 sinif bekleniyor)" % len(satirlar)
    beklenen = {
        "🔧 `d1-sync.py` yazici yolunda D1 senkron drift":
            "/Users/okan/dev/pruvo/tools/d1-sync.py --durum",
        "🔧 arama paritesi Ege tarafinda kirmizi":
            "/Users/okan/dev/pruvo/tools/parite-ege.js",
        "🔧 kisisel veri sizinti nobetcisi":
            "/Users/okan/dev/pruvo/tools/kisisel-veri-test.py",
        "🔧 yeni kapi CI'da kosmuyor (ci kapsam)":
            "/Users/okan/dev/pruvo/tools/ci-kapsam-test.py",
    }
    for metin, komut in beklenen.items():
        secilen = kapi.el_kitabi_satiri_sec(metin, satirlar)
        assert secilen is not None, "el kitabi sinifi bulunamadi: %s" % metin
        assert komut in secilen["kabul"], (metin, secilen["kabul"])
        spec = kapi.spec_metni({"id": "K01", "tarih": "2026-08-14",
                                "kimden_kime": "Tamirci→Tamirci", "is": metin,
                                "durum_ham": "🔧"}, "codex", "/tmp/rapor.md",
                               "nobet-K01-t1", secilen)
        assert komut in spec, "SPEC'e kabul komutu satiri GIRMEDI: %s" % metin
        assert "KABUL_KOMUTU=" in spec, "SPEC KABUL_KOMUTU satirini istemiyor"
    # bilinmeyen sinif: satir YOK, ama SPEC yine KABUL_KOMUTU ister (C2)
    assert kapi.el_kitabi_satiri_sec("🔧 hicbir sinifa uymayan is", satirlar) is None
    spec = kapi.spec_metni({"id": "K02", "tarih": "2026-08-14",
                            "kimden_kime": "Tamirci→Tamirci",
                            "is": "🔧 hicbir sinifa uymayan is", "durum_ham": "🔧"},
                           "codex", "/tmp/rapor.md", "nobet-K02-t1", None)
    assert "KABUL_KOMUTU=" in spec and "ILK ISIN" in spec, spec
    # el kitabinin `kat` sutunu kat_sec'ten TURETILMISTIR (ikiz tanim ayrisamaz)
    for kayit in satirlar:
        beklenen_kat = kapi.kat_sec({"is": " ".join(kayit["jetonlar"]), "durum_ham": ""})
        assert kayit["kat"] == beklenen_kat, (
            "el kitabi kat sutunu kat_sec'ten AYRISTI: %s -> %s != %s" % (
                kayit["sinif"], kayit["kat"], beklenen_kat))
    # kabul komutlarinin BICIMI C4'ten geciyor mu (beyaz liste centigi bilinen istisna)
    disarida = []
    for kayit in satirlar:
        argv, sebep = kapi.kabul_komutu_dogrula(kayit["kabul"])
        if argv is None:
            disarida.append((kayit["sinif"], sebep))
    assert all(s == "BEYAZ_LISTE_DISI" for _, s in disarida), disarida
    assert len(disarida) <= 1, "el kitabinda C4'ten dusen %d satir var: %s" % (
        len(disarida), disarida)
    return "8 sinif · 4 kalem dogru kabul komutunu aldi · kat sutunu kat_sec ile ESIT"


# --- G paketi: kardes depo kokleri + K49/K53/K54 kabul atamasi (vaka 20-24) --

def vaka20_kardes_depo_gecerli_kabul():
    """20) G1: kardes depo kokundeki gecerli komut KABUL edilir (P1 kontrol kolu)."""
    argv, sebep = kapi.kabul_komutu_dogrula(
        "python3 /Users/okan/dev/pruvo-hasat/olcum/x.py")
    assert argv is not None and sebep == "GECERLI", (argv, sebep)
    assert argv[0] == "python3", argv
    assert argv[1] == os.path.realpath("/Users/okan/dev/pruvo-hasat/olcum/x.py"), argv
    return "kardes depo yolundaki gecerli komut KABUL (GECERLI)"


def vaka21_kardes_depo_disi_reddedilir():
    """21) G1/P1: kardes depo koku DISI yol REDDEDILIR (P1 bunu genisletir)."""
    argv, sebep = kapi.kabul_komutu_dogrula("python3 /Users/okan/dev/baska/x.py")
    assert argv is None, argv
    assert sebep == "BEYAZ_LISTE_DISI", sebep
    return "kardes depo disi yol (/dev/baska) REDDEDILDI"


def vaka22_kardes_depo_nokta_kacisi():
    """22) G1/P2: kardes depo yolunda `..` kacisi realpath sonrasi REDDEDILIR."""
    argv, sebep = kapi.kabul_komutu_dogrula(
        "python3 /Users/okan/dev/pruvo-hasat/../../../tmp/kotu.py")
    assert argv is None, argv
    assert sebep == "BEYAZ_LISTE_DISI", sebep
    return "kardes depo `..` kacisi realpath sonrasi REDDEDILDI"


def vaka23_kardes_depo_metakarakter_reddedilir():
    """23) G1/P3: kardes depo yolunda metakarakter REDDEDILIR, hicbir sey kosulmaz."""
    kotu = "python3 /Users/okan/dev/pruvo-hasat/olcum/x.py; rm -rf /tmp/x"
    argv, sebep = kapi.kabul_komutu_dogrula(kotu)
    assert argv is None, argv
    assert sebep.startswith("METAKARAKTER"), sebep
    kosulan = []
    sonuc = kapi.kabul_komutu_kos(kotu, kosucu=lambda a, z: kosulan.append(a) or 0)
    assert sonuc["hukum"] == "KOMUT_REDDEDILDI", sonuc
    assert kosulan == [], "reddedilen kardes depo komutu yine kosuldu: %s" % kosulan
    # shell=False dinamik kanit (kardes depo yolunda): metakarakterli ARGUMAN
    # kabuga DEGIL betige duz metin gider; shell=True mutantinda betik kirilir.
    kok = tempfile.mkdtemp(prefix="nobet-kardes-shell-")
    try:
        cikti = os.path.join(kok, "iz.txt")
        betik = os.path.join(kok, "yaz.py")
        with open(betik, "w", encoding="utf-8") as dosya:
            dosya.write("import sys\nopen(sys.argv[1], 'w').write(sys.argv[2])\n")
        rc = kapi._kabul_gercek_kosucu(["python3", betik, cikti, "; echo kacak"], 30)
        assert rc == 0, "gercek kosucu betigi calistiramadi rc=%s" % rc
        with open(cikti, encoding="utf-8") as dosya:
            iz = dosya.read()
        assert iz == "; echo kacak", "arguman kabuktan gecti (shell=True): %r" % iz
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return "kardes depo metakarakter REDDEDILDI (0 kosum) · shell=False duz gecti"


def vaka24_kardes_depo_kabul_dolu_kapanir():
    """24) G2: kardes depo yolundaki kabul komutu DOLU + rc=0 -> kalem KAPANDI (uctan uca)."""
    # (1) uc gercek kabul komutu (K49/K53/K54) G1 koklerinden GECERLI dogrulanir.
    for komut in ("python3 /Users/okan/dev/pruvo/tools/d1-yazici-kilit-test.py",
                  "python3 /Users/okan/dev/pruvo-hasat/test/hasat_denetim_kabul.py",
                  "python3 /Users/okan/dev/pruvo-hasat/olcum/_tcgt_kabul_icmekan.py"):
        argv, sebep = kapi.kabul_komutu_dogrula(komut)
        assert argv is not None and sebep == "GECERLI", (komut, sebep)
    # (2) DOLU kabul + rc=0 -> KAPANDI (kardes depo komutu, kalem_kabul_hukmu).
    hukum = kapi.kalem_kabul_hukmu(
        "HUKUM=KAPANDI",
        "python3 /Users/okan/dev/pruvo-hasat/test/hasat_denetim_kabul.py",
        lambda k: {"hukum": "KOSTU_YESIL", "rc": 0})
    assert hukum["hukum"] == "KAPANDI", hukum
    # (3) ayni komut rc!=0 ise BEYAN_VAR_KANIT_YOK (fail-closed, uctan uca).
    hukum2 = kapi.kalem_kabul_hukmu(
        "HUKUM=KAPANDI",
        "python3 /Users/okan/dev/pruvo-hasat/test/hasat_denetim_kabul.py",
        lambda k: {"hukum": "KOSTU_KIRMIZI", "rc": 3})
    assert hukum2["hukum"] == "BEYAN_VAR_KANIT_YOK", hukum2
    return "3 kardes depo kabul komutu GECERLI + DOLU&rc=0 -> KAPANDI (rc!=0 fail-closed)"


# --- H8: kok defter buyume kapisi (vaka 25-27) ----------------------------

def _h8_buyume_kos(eklenen, kalem_defteri=None):
    """Sahte kok defteri `eklenen` satir buyutup olculmus bir tur kapatir."""
    with Tezgah(kalem_defteri if kalem_defteri is not None else defter([])) as t:
        kok_defter = os.path.join(t.kok, "DEVAM.md")
        with open(kok_defter, "w", encoding="utf-8") as dosya:
            dosya.write("# sahte kok defter\n")
        defter_once = kapi._defter_satir_sayisi(kok_defter)
        with open(kok_defter, "a", encoding="utf-8") as dosya:
            dosya.writelines("durum-%d\n" % i for i in range(eklenen))

        gercek_sayici = kapi._defter_satir_sayisi

        def _sahte_kok_sayici(yol=kapi.KOK_DEFTER_YOLU):
            return gercek_sayici(kok_defter)

        kapi._defter_satir_sayisi = _sahte_kok_sayici
        try:
            sonuc = t.kapat(defter_once=defter_once)
        finally:
            kapi._defter_satir_sayisi = gercek_sayici
    return sonuc


def vaka25_defter_tavan_alti():
    """25) H8: kok defter 1 satir buyurse turun mevcut hukum/rc'si degismez."""
    beklenen_rc, beklenen_hukum = kapi.tur_hukmu(0, 0, 0)
    sonuc = _h8_buyume_kos(1)
    assert sonuc["rc"] == beklenen_rc, sonuc
    assert sonuc["hukum"] == beklenen_hukum, sonuc
    assert sonuc["defter_buyumesi"] == 1, sonuc
    assert "DEFTER_BUYUMESI=1" in sonuc["rapor"], sonuc["rapor"]
    return "buyume=1 -> rc/hukum degismedi"


def vaka26_defter_tavan_ustu():
    """26) H8: kok defter 12 satir buyurse tur DEFTER_SISIRME ile duser."""
    sonuc = _h8_buyume_kos(12)
    assert sonuc["rc"] != 0, "tavan asildi ama rc=0 kaldi"
    assert sonuc["hukum"] == "DEFTER_SISIRME", sonuc
    assert sonuc["defter_buyumesi"] == 12, sonuc
    assert "DEFTER_BUYUMESI=12" in sonuc["rapor"], sonuc["rapor"]
    # Mevcut ARIZA hukmu ve onun sifir-disi rc'si H8 tarafindan EZILMEZ.
    ariza_defteri = defter([
        satir("K01", "Okan", "🔧 deploy hukmu bekliyor", "🔧")])
    ariza = _h8_buyume_kos(12, ariza_defteri)
    ariza_rc, ariza_hukmu = kapi.tur_hukmu(1, 0, 0)
    assert ariza["rc"] == ariza_rc, ariza
    assert ariza["hukum"] == ariza_hukmu, ariza
    return "buyume=12 -> rc=%d DEFTER_SISIRME" % sonuc["rc"]


def vaka27_defter_olculmedi():
    """27) H8: baslangic olcumu yoksa fail-open; mevcut hukum/rc degismez."""
    beklenen_rc, beklenen_hukum = kapi.tur_hukmu(0, 0, 0)
    with Tezgah(defter([])) as t:
        assert kapi._defter_satir_sayisi(os.path.join(t.kok, "olmayan-DEVAM.md")) == 0
        sonuc = t.kapat()
    assert sonuc["rc"] == beklenen_rc, sonuc
    assert sonuc["hukum"] == beklenen_hukum, sonuc
    assert sonuc["defter_buyumesi"] is None, sonuc
    assert "DEFTER_BUYUMESI=OLCULMEDI" in sonuc["rapor"], sonuc["rapor"]
    return "olcum yok -> rc/hukum degismedi"


def vaka28_onarimsiz_supurme_turu_dusurur():
    """28) ONARIM=0 + TASINAN>0 -> daha agir ONARIMSIZ_SUPURME (M-A)."""
    with Tezgah(defter([])) as t:
        sonuc = t.kapat(tasinan=2)
    assert sonuc["onarim"] == 0 and sonuc["tasinan"] == 2, sonuc
    assert sonuc["rc"] == 1, "onarimsiz supurme rc=0 gecti"
    assert sonuc["hukum"] == "ONARIMSIZ_SUPURME", sonuc
    assert "GEREKCE=onarilmadan alarm kanali susturuldu" in sonuc["rapor"], sonuc["rapor"]
    ariza = kapi.tur_hukmu(0, 0, 0, tasinan=2, mevcut_hukum="ARIZA")
    assert ariza == (1, "ARIZA"), "mevcut ARIZA hukmu ezildi: %s" % (ariza,)
    assert kapi.tur_olcumu_ayikla("SUPURME_TASINAN=99\nTASINAN=2", "TASINAN") == 2
    assert kapi.tur_hukmu_ayikla("HUKUM=SUPURULDU\nHUKUM=ARIZA_VAR") == "ARIZA_VAR"
    return "ONARIM=0 TASINAN=2 -> rc=1 ONARIMSIZ_SUPURME"


def vaka29_onarimli_supurme_yanlis_pozitif_uretmez():
    """29) ONARIM>0 + TASINAN>0 -> supurme hukmu dogmaz (yanlis-pozitif yok)."""
    metin = defter([satir("K01", "Tamirci", "🔧 tarama kök neden bulunacak", "🔧")])
    with Tezgah(metin) as t:
        sonuc = t.kapat(tasinan=1)
    assert sonuc["onarim"] > 0 and sonuc["tasinan"] == 1, sonuc
    assert sonuc["hukum"] != "ONARIMSIZ_SUPURME", sonuc
    assert sonuc["rc"] == 0, sonuc
    return "ONARIM=%d TASINAN=1 -> %s" % (sonuc["onarim"], sonuc["hukum"])


def vaka30_ustuste_sayaci_kova_bossa_sifirlar_gercek_dustude_artan():
    """30) Kova bos + eskalasyon yok ise sayac sifirlanir (yapacak is yoktu,
    onarimsizlik ANLAMSIZ); gercek onarim DENENDI ve DUSTU ise sayac ARTMALI
    (M-B). Onarim>0 ise sayac sifirlanir (M-A/M-B yolu)."""
    # POZITIF: kova bos + eskalasyon yok -> sayac hep 0, eskalasyon satiri YOK.
    with Tezgah(defter([])) as t:
        bir = t.kapat()
        iki = t.kapat()
        uc = t.kapat()
        assert bir["ustuste_onarimsiz"] == 0, bir
        assert iki["ustuste_onarimsiz"] == 0, iki
        assert uc["ustuste_onarimsiz"] == 0, uc
        assert "ESKALASYON=OKAN USTUSTE_ONARIMSIZ=" not in uc["rapor"], uc["rapor"]
    # NEGATIF: onarim DENENDI ve DUSTU -> sayac artar (M-B mutant yalniz 0
    # dondurur, KOSTU_DUSTU kolunda sayacin ARTMASINI bekleyerek yakalanir).
    with Tezgah(defter([])) as t:
        _sayaci_sifirla(t)
        bir = kapi.tur_sayacini_kaydet("KOSTU_DUSTU", 0)
        assert bir[0] == 1, bir
        iki = kapi.tur_sayacini_kaydet("KOSTU_DUSTU", 0)
        assert iki[0] == 2, iki
        uc = kapi.tur_sayacini_kaydet("KOSTU_ONARDI", 1)
        assert uc[0] == 0, uc
    # IS_YOK kapisi: kova bos halde dogrudan sifirlar (sayac != 0 olsa bile).
    with Tezgah(defter([])) as t:
        _sayaci_sifirla(t)
        kapi.ustuste_onarimsiz_guncelle(0)  # KOSTU_DUSTU: 0 -> 1
        assert kapi.ustuste_onarimsiz_oku() == 1
        yeni = kapi.tur_sayacini_kaydet("IS_YOK", 0)
        assert yeni[0] == 0, yeni
    return "kova bos -> sayac=0 · KOSTU_DUSTU 1->2->KOSTU_ONARDI 0 · IS_YOK sifirlar"


def _sayaci_sifirla(tezgah):
    """Tezgah baglaminda sayac dosyasini 0'a cek (dogrudan JSON yaz)."""
    import json as _json
    with open(kapi.ONARIMSIZ_SAYAC_YOLU, "w", encoding="utf-8") as dosya:
        _json.dump({"ustuste_onarimsiz": 0}, dosya)


def vaka31_onarim_yokken_25dk_sure_tavani():
    """31) Onarim ilerlemiyorsa 25 dk'da isci kesilir, tur SURE_TAVANI ile duser."""
    beklemeler = []
    sonlandirmalar = []

    def _bekle(tavan):
        beklemeler.append(tavan)
        raise subprocess.TimeoutExpired("sahte-isci", tavan,
                                        output=b"KAPANAN=0\nDAGITILAN=0\nHUKUM=TEMIZ\n")

    rc, cikti = kapi._sureli_isci_bekle(
        _bekle, lambda: sonlandirmalar.append("KESILDI"))
    assert rc == 1, "sure tavani rc=1 yerine %s" % rc
    assert kapi.tur_hukmu_ayikla(cikti) == "SURE_TAVANI", cikti
    assert "SURE_TAVANI_ASILDI=1" in cikti, cikti
    assert beklemeler == [1500], "onarimsiz isci 25 dk'da kesilmedi: %s" % beklemeler
    assert sonlandirmalar == ["KESILDI"], "isci sonlandirilmadi: %s" % sonlandirmalar
    # Sure tavani motor hatasi degildir: yedek motorla yeni bir 25 dk daha BASLAMAZ.
    motorlar = []

    def _motor_kos(motor):
        motorlar.append(motor)
        return rc, cikti

    zincir = kapi.motor_zinciri_kos(("m1", "m2"), _motor_kos)
    assert zincir["hukum"] == "SURE_TAVANI", zincir
    assert motorlar == ["m1"], "sure tavani yedek motor baslatti: %s" % motorlar
    # Yeni hafif hukum mevcut bir ARIZA hukmunu ezemez.
    _, ariza = kapi._sure_tavani_sonucu(
        "HUKUM=ARIZA_MAIL\n", lambda: None, kapi.TUR_ZAMAN_ASIMI_SN)
    assert kapi.tur_hukmu_ayikla(ariza) == "ARIZA_MAIL", ariza
    return "onarimsiz 25 dk -> isci KESILDI · rc=1 HUKUM=SURE_TAVANI"


def vaka32_onarim_ilerlerken_30dk_kesilmez():
    """32) Onarim ilerliyorsa 25 dk kesmez; 30 dk'da biten turun hukmu degismez."""
    beklemeler = []
    sonlandirmalar = []
    cikti = "KAPANAN=1\nDAGITILAN=0\nHUKUM=ONARIM_ILERLIYOR\n"

    def _bekle(tavan):
        beklemeler.append(tavan)
        if len(beklemeler) == 1:
            raise subprocess.TimeoutExpired("sahte-isci", tavan,
                                            output=cikti.encode("utf-8"))
        return 0, cikti

    rc, sonuc = kapi._sureli_isci_bekle(
        _bekle, lambda: sonlandirmalar.append("KESILDI"))
    assert rc == 0, sonuc
    assert kapi.tur_hukmu_ayikla(sonuc) == "ONARIM_ILERLIYOR", sonuc
    assert "SURE_TAVANI_ASILDI=1" not in sonuc, sonuc
    assert beklemeler == [1500, 1500], "50 dk tavan ayrimi uygulanmadi: %s" % beklemeler
    assert sonlandirmalar == [], "ilerleyen onarim 25 dk'da kesildi"
    return "onarim ilerliyor + 30 dk -> KESILMEDI · HUKUM=ONARIM_ILERLIYOR"


def vaka33_atlama_sayilir_normal_tur_sifirlar():
    """33) Her kilit atlamasi artar; normal kosan ilk tur sayaci sifirlar."""
    with Tezgah(defter([])):
        assert kapi.atlanan_ardisik_guncelle(True) == 1
        assert kapi.atlanan_ardisik_guncelle(True) == 2
        assert kapi.atlanan_ardisik_oku() == 2
        assert kapi.atlanan_ardisik_guncelle(False) == 0
        assert kapi.atlanan_ardisik_oku() == 0
    return "atlama 1->2 sayildi · normal tur sonrasi ATLANAN_ARDISIK=0"


def vaka34_ikinci_atlama_eskalasyon_basar():
    """34) Ikinci ardisik atlama Okan eskalasyonu basar; ilk atlama basmaz."""
    with Tezgah(defter([])):
        bir = kapi.atlanan_ardisik_guncelle(True)
        satir1 = kapi.atlama_satiri("ONCEKI_TUR_SURUYOR", bir, "D1")
        iki = kapi.atlanan_ardisik_guncelle(True)
        satir2 = kapi.atlama_satiri("ONCEKI_TUR_SURUYOR", iki, "D2")
    assert "ATLANAN_ARDISIK=1" in satir1, satir1
    assert "ESKALASYON=OKAN" not in satir1, satir1
    assert "ESKALASYON=OKAN ATLANAN_ARDISIK=2" in satir2, satir2
    return "=1 eskalasyon YOK · =2 ESKALASYON=OKAN ATLANAN_ARDISIK=2"


def vaka35_karantina_motoru_ayakta_sayilmaz():
    """35) Karantinadaki motor zincirden ATLANIR (kimi -> minimax-m3'e dusulur)."""
    # Gercek evde kimi anahtari var; isci.sh kota yazmis gibi KARANTINA_YOLU'na
    # bir satir dolduruyoruz. motor_ayakta("kimi") False, minimax-m3 hala True.
    with Tezgah(defter([])) as t:
        with open(kapi.KARANTINA_YOLU, "w", encoding="utf-8") as d:
            d.write("kimi %d\n" % int(kapi.time.time()))
        assert kapi.motor_ayakta("kimi") is False, "kimi karantinada, zincirden atlanmali"
        assert kapi.motor_ayakta("minimax-m3") is True, "minimax-m3 karantinada degil"
        zincir = [m for m in kapi.TUR_MOTOR_ZINCIRI if kapi.motor_ayakta(m)]
        assert zincir == ["minimax-m3"], "kimi atlanmadi: %s" % zincir
    return "kimi karantinada -> motor_ayakta=False, zincir minimax-m3'e dustu"


def vaka36_karantina_omru_dolunca_motor_geri_doner():
    """36) Karartina 6 saati dolan motoru temizle_ve_oku dosyadan dusurur."""
    with Tezgah(defter([])) as t:
        # 7 saat once yazildi -> omur doldu
        eski = int(kapi.time.time()) - kapi.KARANTINA_OMUR_SN - 3600
        # 1 saat once yazildi -> hala karantinada
        taze = int(kapi.time.time()) - 3600
        with open(kapi.KARANTINA_YOLU, "w", encoding="utf-8") as d:
            d.write("kimi %d\nminimax-m3 %d\n" % (eski, taze))
        # karantina_kayitlari zaten 6h+ eski olanlari filtreler -> kimi yok.
        once = kapi.karantina_kayitlari()
        assert "kimi" not in once, "eski kimi oncekinden zaten filtrelenmis: %s" % once
        assert "minimax-m3" in once, "taze minimax-m3 gorunmedi: %s" % once
        # temizle_ve_oku dosyayi atomik yazar, eski satiri dusurur.
        sonra = kapi.karantina_temizle_ve_oku()
        assert "kimi" not in sonra, "omru dolmus kimi dusurulmedi: %s" % sonra
        assert "minimax-m3" in sonra, "taze minimax-m3 dusuruldu: %s" % sonra
        # Dosya icerigi de temizlenmis olmali (surekli buyuyen dosya engeli).
        with open(kapi.KARANTINA_YOLU, encoding="utf-8") as d:
            satirlar = d.read().splitlines()
        assert "kimi" not in "\n".join(satirlar), "dosyada omru dolmus kimi kalmis"
        assert any("minimax-m3" in s for s in satirlar), "taze motor dosyadan ucmus"
    return "6h+1 omru dolmus kimi dusuruldu · minimax-m3 (1h) karantinada kaldi"


def vaka37_karantina_tum_zincir_doldugunda_en_eskiyi_dener():
    """37) Tum zincir karantinadaysa en eski karantinaiyi sec (fail-open)."""
    with Tezgah(defter([])) as t:
        # Zincir (kimi, minimax-m3). minimax-m3 daha eski karantinaya alinmis.
        eski = int(kapi.time.time()) - 2 * 3600         # 2h once
        yeni = int(kapi.time.time()) - 30 * 60          # 30dk once
        with open(kapi.KARANTINA_YOLU, "w", encoding="utf-8") as d:
            d.write("kimi %d\nminimax-m3 %d\n" % (yeni, eski))
        secilen = kapi.karantina_en_eski(kapi.TUR_MOTOR_ZINCIRI)
        assert secilen == "minimax-m3", "en eski minimax-m3 secildi, got=%s" % secilen
        # Hicbiri karantinada degilse None.
        with open(kapi.KARANTINA_YOLU, "w", encoding="utf-8") as d:
            d.write("")
        assert kapi.karantina_en_eski(kapi.TUR_MOTOR_ZINCIRI) is None
    return "en eski karantinai minimax-m3 (2h once) · hicbiri karantinada None"


def vaka38_karantina_kayitlari_ekle_mukerrer_engeli():
    """38) Ayni motor saniye farkiyla 2 kez yazilirsa TEK satir kalir (guncellenir)."""
    with Tezgah(defter([])) as t:
        t1 = int(kapi.time.time()) - 60
        t2 = int(kapi.time.time())
        with open(kapi.KARANTINA_YOLU, "w", encoding="utf-8") as d:
            d.write("kimi %d\ndeepseek-pro %d\nkimi %d\n" % (t1, t1, t2))
        sonuc = kapi.karantina_kayitlari()
        assert len(sonuc) == 2, "mukerrer kimi dusurulmedi: %s" % sonuc
        assert sonuc["kimi"] == t2, "kimi'nin damgasi en tazesine guncellenmedi: %s" % sonuc
        assert "deepseek-pro" in sonuc
    return "kimi 2 kez yazildi -> 1 satir (damga güncel) + deepseek-pro ayri"


def vaka39_nobet_zincir_tam_turetilir():
    """39) K257(e) (mimar hukmu, 20 Agu 2026): nobet TUR_MOTOR_ZINCIRI CANLI
    kumeden TAM TURETILIR — elle yazilmis ya da kirpilmis liste YOK.

    🔴 HUKUM DEGISTI; ESKI VAKA SILINMEDI, YERINE BU GECTI:
      ESKI (16 Agu, BaBa): "cron nobetleri Kimi'ye BAGLANMAZ" -> zincir kimi
        ICERMEZ. Gerekce: Kimi haftalik 5s limit, cok-turlu nobet tasariminda
        baglayici.
      YENI (20 Agu, mimar K257(e) + Okan'in 20 Agu motor karari): zincir CANLI
        kumeden TAM turer. BaBa'nin GEREKCESI KALDIRILMADI — (3). madde onu
        ayrica civiliyor: kimi zincire girer ama ASLA BIRINCI DEGILDIR, yani
        nobet Kimi'ye BAGLANMAZ, yalniz m3 dustugunde Kimi'ye DUSER.

    🔴 TAUTOLOJI FRENI: birincil kati "zincir[0] == CANLI_ISCI_MOTORLARI[0]"
    diye olcmek YETMEZ — sira ters cevrilirse IKISI BIRDEN doner ve vaka YESIL
    kalir ([[isci-yesil-tablo-ic-olcumu-bosaltir]]). Birincil kat BAGIMSIZ bir
    capaya, Okan'in 20 Agu kararindaki ADA baglanir. Sira degisirse bu vaka
    KIRMIZI yanar ve degisikligi bir INSAN onaylar.
    """
    zincir = tuple(kapi.TUR_MOTOR_ZINCIRI)
    canli = tuple(kapi.CANLI_ISCI_MOTORLARI)
    assert isinstance(kapi.TUR_MOTOR_ZINCIRI, (tuple, list)), (
        "TUR_MOTOR_ZINCIRI tuple/list degil: %r" % (zincir,))
    # (1) TAM TURETIM: kirpilmis ya da elle yazilmis zincir REDDEDILIR.
    assert zincir == canli, (
        "zincir CANLI kumeden TAM turemiyor: zincir=%r canli=%r" % (zincir, canli))
    # (2) BIRINCIL KAT — BAGIMSIZ capa (Okan, 20 Agu: m3 BIRINCIL, kimi YEDEK).
    assert zincir and zincir[0] == "minimax-m3", (
        "nobet BIRINCIL kati minimax-m3 OLMALI (Okan 20 Agu karari): %r" % (zincir,))
    # (3) BaBa 16 Agu GEREKCESI KORUNUR: kimi zincirde OLABILIR, BIRINCI OLAMAZ.
    assert "kimi" not in zincir or zincir.index("kimi") > 0, (
        "kimi BIRINCI olamaz — nobet Kimi'ye BAGLANAMAZ (BaBa 16 Agu): %r"
        % (zincir,))
    return "zincir=%s · TAM turetildi · birincil=%s · kimi yedek" % (
        zincir, zincir[0])


# --- K160 dilim-2: NOBET YUZEYI KILIT KENDI BASINA OLSUN (N-a..N-f) ---------

def _k160_rakip_canli_icerik(simdi):
    """CANLI rakip icerigi — PID=os.getpid(), taze EPOK. karar=DOLU beklenir."""
    return "PID=%d\nEPOK=%d\nDAMGA=\n" % (os.getpid(), simdi)


def vaka_N_a_dikiste_rakip_canli_dogar():
    """N-a) Dikişte CANLI rakip kilit doğar -> (False, ONCEKI_TUR_SURUYOR). M11/M15."""
    kok = tempfile.mkdtemp(prefix="k160c-N-a-")
    try:
        yol = os.path.join(kok, "kilit")
        # Baslangic: AL (dosya yok). kapi.kilit_al cagrildiginda karar()=AL olur,
        # ardindan _araya_gir() kosar; bizim seam CANLI rakip icerigi YAZAR.
        # os.open(O_EXCL) FileExistsError, taze okuma karar=DOLU -> ONCEKI_TUR_SURUYOR.
        simdi = kapi.time.time()
        olusturulan = []
        def seam():
            with open(yol, "w", encoding="utf-8") as dosya:
                dosya.write(_k160_rakip_canli_icerik(simdi))
            olusturulan.append(True)
        alindi, hukum = kapi.kilit_al(yol, simdi=simdi, _araya_gir=seam)
        assert olusturulan == [True], "seam kosmamis: %r" % (olusturulan,)
        assert alindi is False, "kilit alindi (CANLI rakip varken OLMAMALI): %r" % (alindi,)
        assert hukum == "ONCEKI_TUR_SURUYOR", (
            "hukum ONCEKI_TUR_SURUYOR olmaliydi: %r" % (hukum,))
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return "seam kosmali CANLI rakip doardi; ONCEKI_TUR_SURUYOR dondu"


def vaka_N_b_dikiste_dosya_calinmaz():
    """N-b) N-a kosu sonrasi dosya bayt bayt seam'in yazdigi (calinmadi). M11/M15."""
    kok = tempfile.mkdtemp(prefix="k160c-N-b-")
    try:
        yol = os.path.join(kok, "kilit")
        simdi = kapi.time.time()
        rakip = _k160_rakip_canli_icerik(simdi)
        def seam():
            with open(yol, "w", encoding="utf-8") as dosya:
                dosya.write(rakip)
        alindi, _hukum = kapi.kilit_al(yol, simdi=simdi, _araya_gir=seam)
        assert alindi is False, "kilit alindi: %r" % (alindi,)
        with open(yol, encoding="utf-8") as dosya:
            icerik = dosya.read()
        assert icerik == rakip, (
            "icerik seam yazdigindan farkli (calinmis olabilir):\nSEAM=%r\nGERCEK=%r"
            % (rakip, icerik))
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return "rakip CANLI icerigi BYTE-BYTE korundu (calinmadi)"


def vaka_N_c_sifir_baytlik_artik_kilit_devralinir():
    """N-c) SIFIR BAYTLIK artik kilit -> (True, KILIT_ALINDI), icerikte PID=kendi. M14."""
    kok = tempfile.mkdtemp(prefix="k160c-N-c-")
    try:
        yol = os.path.join(kok, "kilit")
        with open(yol, "w", encoding="utf-8") as dosya:
            dosya.write("")  # sifir baytlik artik
        alindi, hukum = kapi.kilit_al(yol)
        assert alindi is True, "sifir baytlik devralinamadi: %r" % (alindi,)
        assert hukum == "KILIT_ALINDI", (
            "hukum KILIT_ALINDI olmaliydi: %r" % (hukum,))
        with open(yol, encoding="utf-8") as dosya:
            icerik = dosya.read()
        assert ("PID=%d" % os.getpid()) in icerik, (
            "kendi PID'imiz yazilmadi: %r" % (icerik,))
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return "sifir baytlik -> KILIT_ALINDI, icerikte PID=kendi"


def vaka_N_d_baskasinin_kilidini_birakamaz():
    """N-d) Baskasinin pid'li kilitte kilit_birak -> False, dosya DURUR. M12."""
    kok = tempfile.mkdtemp(prefix="k160c-N-d-")
    try:
        yol = os.path.join(kok, "kilit")
        # 999999 (veya 1) canli olmayan PID; karar=BAYAT olur ama bizim test
        # kilit_birak'a odaklanir; kilit_birak sahiplik denetimi yapar.
        with open(yol, "w", encoding="utf-8") as dosya:
            dosya.write("PID=999999\nEPOK=%d\n" % kapi.time.time())
        sonuc = kapi.kilit_birak(yol)
        assert sonuc is False, "baskasinin kilidi birakildi (olmamali): %r" % (sonuc,)
        assert os.path.exists(yol), (
            "dosya silinmis (sahiplik denetimi gecildi): %s" % yol)
        with open(yol, encoding="utf-8") as dosya:
            icerik = dosya.read()
        assert "PID=999999" in icerik, (
            "icerik bozulmus: %r" % (icerik,))
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return "baskasinin PID'li kilidi SILINMEDI (sahiplik korundu)"


def vaka_N_e_kendi_kilidini_birakir():
    """N-e) KENDI kilidinde kilit_birak -> True, dosya SILINIR. (regresyon)."""
    kok = tempfile.mkdtemp(prefix="k160c-N-e-")
    try:
        yol = os.path.join(kok, "kilit")
        alindi, hukum = kapi.kilit_al(yol)
        assert alindi is True and hukum == "KILIT_ALINDI", (alindi, hukum)
        assert os.path.exists(yol), "kilit alindi ama dosya yok: %s" % yol
        sonuc = kapi.kilit_birak(yol)
        assert sonuc is True, "kendi kilidimizi birakamadik: %r" % (sonuc,)
        assert not os.path.exists(yol), (
            "kendi kilidimizi biraktik ama dosya hala duruyor: %s" % yol)
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return "kendi kilidimiz SILINDI"


def vaka_N_f_dikis_verilmeden_ardisik_kilit_al():
    """N-f) Dikis verilmeden kilit_al 2 kez ARDISIK -> ikinci ONCEKI_TUR_SURUYOR.

    Bu vaka dikis parametresinin uretimde OLMEDIGINI (default None) kanitlar;
    mevcut kilit davranisi degismemis olmali.
    """
    kok = tempfile.mkdtemp(prefix="k160c-N-f-")
    try:
        yol = os.path.join(kok, "kilit")
        alindi1, hukum1 = kapi.kilit_al(yol)
        assert alindi1 is True and hukum1 == "KILIT_ALINDI", (alindi1, hukum1)
        # Dikis verilmeden ikinci cagri: default _araya_gir=None.
        alindi2, hukum2 = kapi.kilit_al(yol)
        assert alindi2 is False, (
            "ikinci tur da kilit aldi (dikis uretimde OLU): %r" % (alindi2,))
        assert hukum2 == "ONCEKI_TUR_SURUYOR", (
            "hukum ONCEKI_TUR_SURUYOR olmaliydi: %r" % (hukum2,))
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return "ardisik kilit_al: 1. KILIT_ALINDI, 2. ONCEKI_TUR_SURUYOR (dikis olmeden)"


def vaka40_dagitilmaz_sebep_alani_dolu():
    """40) O4B: [DAGITILMAZ] satirlarinda SEBEP= alani kova_sec'ten turetilir ve doludur."""
    metin = defter([
        satir("K701", "Okan", "bakim isi", "🔧"),
        satir("K702", "Tamirci", "yeni kapi tasarimi", "🔧"),
    ])
    with Tezgah(metin) as t:
        sonuc = t.kapat(kuru=True)
    rapor = sonuc["rapor"]
    dagitilmaz = [l for l in rapor.splitlines() if "[DAGITILMAZ]" in l]
    assert len(dagitilmaz) == 2, "beklenen 2 DAGITILMAZ satir, bulunan %d" % len(dagitilmaz)
    for l in dagitilmaz:
        assert "SEBEP=" in l, "SEBEP= alani yok: %s" % l
        sebep = l.split("SEBEP=", 1)[1].strip()
        assert sebep, "SEBEP= alani bos: %s" % l
    assert "KALEM K701 -> OKAN [DAGITILMAZ] SEBEP=OKAN_KAPISI" in rapor
    assert "KALEM K702 -> MIMAR [DAGITILMAZ] SEBEP=MIMAR_KATI_GERCEK" in rapor
    return "[DAGITILMAZ] satirlarinda SEBEP= alani turetilmis ve dolu"


def _dondurma_env_kur(deger):
    """PRUVO_NOBET_DONDURMA env'ini kur; cikista eski haline don."""
    eski = os.environ.get("PRUVO_NOBET_DONDURMA")
    if deger is None:
        os.environ.pop("PRUVO_NOBET_DONDURMA", None)
    else:
        os.environ["PRUVO_NOBET_DONDURMA"] = deger
    return eski


def _dondurma_env_geri(eski):
    if eski is None:
        os.environ.pop("PRUVO_NOBET_DONDURMA", None)
    else:
        os.environ["PRUVO_NOBET_DONDURMA"] = eski


def vakaD1_dondurma_bayragi_dagitimi_durdurur():
    """D1) Bayrak AÇIK + aday >=1: dagitim kolu CALISMAZ, rapor damga tasir."""
    eski = _dondurma_env_kur("1")
    try:
        metin = defter([satir("K01", "Tamirci", "🔧 tarama kök neden bulunacak", "🔧"),
                        satir("K02", "Tamirci", "🔧 log okuma sayim tasimasi eksik", "🔧")])
        with Tezgah(metin) as t:
            s = t.kapat()
            rapor = s["rapor"]
        assert len(t.dagitim_komutlari) == 0, \
            "calistirici HICBIR kalemde cagrilmamali: %d" % len(t.dagitim_komutlari)
        assert s["dagitilan"] == 0, s["dagitilan"]
        assert "DONDURULDU@tur" in rapor, rapor
        assert "ATIF=BAYRAK" in rapor, rapor
        assert "DONDURMA_ISIRDI=1" in rapor, rapor
        assert "ENGELLENEN=" in rapor, rapor
    finally:
        _dondurma_env_geri(eski)
    return "ADAY=2 bayrak ACIK -> calistirici=0 DAGITILDI yok, DONDURMA_ISIRDI=1"


def vakaD2_bayrak_kalkinca_dagitim_geri_gelir():
    """D2) Bayrak KAPALI: dagitim kolu YINE calisir (yuklem gercekten bayrak)."""
    eski = _dondurma_env_kur("0")
    try:
        metin = defter([satir("K01", "Tamirci", "🔧 tarama kök neden bulunacak", "🔧"),
                        satir("K02", "Tamirci", "🔧 log okuma sayim tasimasi eksik", "🔧")])
        with Tezgah(metin) as t:
            s = t.kapat()
            rapor = s["rapor"]
        assert len(t.dagitim_komutlari) >= 1, \
            "bayrak KAPALI iken dagitim YINE calismali: %d" % len(t.dagitim_komutlari)
        assert s["dagitilan"] >= 1, s["dagitilan"]
        assert "DONDURULDU@tur" not in rapor, \
            "bayrak KAPALI iken DONDURULDU damgasi OLMAMALI: %s" % rapor
    finally:
        _dondurma_env_geri(eski)
    return "bayrak KAPALI -> calistirici>=1 DONDURULDU damgasi YOK"


def vakaD3_aday_sifirken_bayrak_isirmis_gibi_gorunmez():
    """D3) Bayrak AÇIK + ADAY=0: ISIRDI=0 (K311 — iki sebebi AYIR)."""
    eski = _dondurma_env_kur("1")
    try:
        metin = defter([satir("K01", "KraL", "kapandi is", "KAPANDI"),
                        satir("K02", "KraL", "ucusta is", "UCUSTA")])
        with Tezgah(metin) as t:
            s = t.kapat()
            rapor = s["rapor"]
        assert "DONDURMA_ISIRDI=0" in rapor, rapor
        assert "ADAY_ZATEN_0" in rapor, rapor
        assert "DONDURMA_ISIRDI=1" not in rapor, \
            "ADAY=0 iken ISIRDI=1 YANLIS sinif: %s" % rapor
    finally:
        _dondurma_env_geri(eski)
    return "ADAY=0 bayrak ACIK -> ISIRDI=0 ADAY_ZATEN_0"


def vakaD4_dondurma_eskalasyon_ve_gozcu_kollarini_degistirmez():
    """D4) REGRESYON: eskalasyon/SLA/merdiven satirlari bayrak oncesi/sonrasi BIREBIR."""
    eski_on = _dondurma_env_kur("1")
    try:
        metin = defter([satir("K01", "Okan", "🔧 iyzico odeme paneli karari", "🔧"),
                        satir("K02", "Tamirci", "🔧 tarama kok neden sessizce geciyor", "🔧"),
                        satir("K03", "Tamirci", "🔧 log okuma sayim tasimasi eksik", "🔧")])
        with Tezgah(metin) as t:
            s_on = t.kapat()
            rapor_on = s_on["rapor"]
    finally:
        _dondurma_env_geri(eski_on)

    eski_off = _dondurma_env_kur("0")
    try:
        metin2 = defter([satir("K01", "Okan", "🔧 iyzico odeme paneli karari", "🔧"),
                         satir("K02", "Tamirci", "🔧 tarama kok neden sessizce geciyor", "🔧"),
                         satir("K03", "Tamirci", "🔧 log okuma sayim tasimasi eksik", "🔧")])
        with Tezgah(metin2) as t:
            s_off = t.kapat()
            rapor_off = s_off["rapor"]
    finally:
        _dondurma_env_geri(eski_off)

    # Spec: sadece bu 5 satir tipi BIREBIR AYNI olmali (eskalasyon kolu
    # etkilenmemis). DAGITILDI / DONDURULDU / DAGITILAN= / HUKUM= vb. farkli
    # olabilir — onlar dagitim kolunun eseridir ve KAPSAM DISI.
    def _filtrele(rapor):
        out = []
        for l in rapor.splitlines():
            if l.startswith("ESKALASYON_BAYAT_GOC="):
                out.append(l)
            elif l.startswith("MERDIVEN_"):
                out.append(l)
            elif l.startswith("ACIK_KALEM="):
                out.append(l)
            elif l.startswith("KALEM ") and "[DAGITILMAZ]" in l:
                out.append(l)
        return out
    f_on = _filtrele(rapor_on)
    f_off = _filtrele(rapor_off)
    assert f_on == f_off, \
        "regresyon: eskalasyon kolu etkilenmis.\nON:\n%s\n\nOFF:\n%s" % (
            "\n".join(f_on), "\n".join(f_off))
    return "eskalasyon/SLA/merdiven satirlari ON/OFF BIREBIR AYNI"


def vaka41_el_kitabi_ureticisi_kat_sutununu_turetir():
    """41) K316: el kitabinin `kat` sutunu URETILIR — elle yazilmaz.

    (a) CANLI el kitabinda uretici SIFIR fark bulur (sutun kaynakla ESIT).
    (b) Fiksturde bozulan hucreyi uretici ONARIR; dosya BIREBIR geri gelir.
    (c) `kuru=True` dosyaya TEK BAYT yazmaz. (d) Uretici IDEMPOTENT.
    """
    canli = kapi.el_kitabi_kat_uret(kuru=True)
    assert canli["okunan"] >= 8, canli
    assert canli["degisen"] == 0, (
        "el kitabi kat sutunu kaynaktan AYRISMIS (uretici kosulmamis): %s" % (canli["fark"],))
    kok = tempfile.mkdtemp(prefix="nobet-elkitabi-")
    try:
        with open(kapi.EL_KITABI_YOLU, encoding="utf-8") as dosya:
            metin = dosya.read()
        satirlar = kapi.el_kitabi_oku()
        assert satirlar, "el kitabi BOS"
        bozuk = metin.replace("| %s |" % satirlar[0]["kat"], "| SAHTE-KAT |", 1)
        assert bozuk != metin, "fikstur bozulamadi (kat hucresi bulunamadi)"
        fikstur = os.path.join(kok, "onarim-el-kitabi.md")
        with open(fikstur, "w", encoding="utf-8") as dosya:
            dosya.write(bozuk)
        kuru = kapi.el_kitabi_kat_uret(yol=fikstur, kuru=True)
        assert kuru["degisen"] == 1, kuru
        with open(fikstur, encoding="utf-8") as dosya:
            assert dosya.read() == bozuk, "KURU tur dosyaya YAZDI"
        islak = kapi.el_kitabi_kat_uret(yol=fikstur, kuru=False)
        assert islak["yazildi"] and islak["degisen"] == 1, islak
        with open(fikstur, encoding="utf-8") as dosya:
            onarilan = dosya.read()
        assert onarilan == metin, "uretici dosyayi BIREBIR geri getirmedi"
        assert kapi.el_kitabi_kat_uret(yol=fikstur, kuru=True)["degisen"] == 0, \
            "uretici IDEMPOTENT degil"
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return "uretici: canli fark=0 · fikstur BIREBIR onarildi · idempotent · kuru YAZMAZ"


VAKALAR = [
    ("1 onarimsiz tur BASARISIZ", vaka1_onarimsiz_tur_basarisiz),
    ("2 dagitim mesru kapanis", vaka2_dagitim_mesru_kapanistir),
    ("3 gercekten temiz tur", vaka3_gercekten_temiz_tur),
    ("4 fan-out tavani + SIRADA", vaka4_fanout_tavani_ve_sirada),
    ("5 raporsuz is DUSTU + yeniden", vaka5_raporsuz_is_duser_ve_yeniden_dagitilir),
    ("6 3. turda ESKALASYON=OKAN", vaka6_ucuncu_turda_eskalasyon),
    ("7 429 -> yedek motor / MOTOR_YOK", vaka7_motor_dusmesi_sessiz_olmaz),
    ("8 sessiz-hata sinifi -> MIMAR", vaka8_sessiz_hata_sinifi_mimara_gider),
    ("9 kilit es zamanli turu engeller", vaka9_kilit_es_zamanli_turu_engeller),
    ("10 kabul dolu + rc=0 -> KAPANDI", vaka10_kabul_dolu_rc0_kapanir),
    ("11 rc!=0 -> BEYAN_VAR_KANIT_YOK", vaka11_beyan_var_kanit_yok),
    ("12 kabul BOS -> kapanamaz", vaka12_kabul_bos_kalem_kapanamaz),
    ("13 rapor BOS alani doldurur", vaka13_rapor_bos_alani_doldurur_dolu_alani_ezmez),
    ("14 GUVENLIK metakarakter", vaka14_guvenlik_metakarakter_reddedilir),
    ("15 GUVENLIK beyaz liste", vaka15_guvenlik_beyaz_liste_disi_reddedilir),
    ("16 GUVENLIK realpath kok", vaka16_guvenlik_realpath_kok_disina_cikamaz),
    ("17 zaman asimi OLCULEMEDI", vaka17_zaman_asimi_yesil_sayilmaz),
    ("18 defter yazma siniri", vaka18_defter_yazma_siniri),
    ("19 el kitabi -> SPEC kabul komutu", vaka19_el_kitabi_spece_kabul_komutu_ekler),
    ("20 kardes depo gecerli KABUL", vaka20_kardes_depo_gecerli_kabul),
    ("21 kardes depo disi REDDEDILDI", vaka21_kardes_depo_disi_reddedilir),
    ("22 kardes depo .. kacisi", vaka22_kardes_depo_nokta_kacisi),
    ("23 kardes depo metakarakter", vaka23_kardes_depo_metakarakter_reddedilir),
    ("24 kardes depo kabul dolu uctan uca", vaka24_kardes_depo_kabul_dolu_kapanir),
    ("defter-tavan-alti", vaka25_defter_tavan_alti),
    ("defter-tavan-ustu", vaka26_defter_tavan_ustu),
    ("defter-olculmedi", vaka27_defter_olculmedi),
    ("onarimsiz-supurme", vaka28_onarimsiz_supurme_turu_dusurur),
    ("onarimli-supurme", vaka29_onarimli_supurme_yanlis_pozitif_uretmez),
    ("ustuste-sayaci-kova-bos-sifirlar", vaka30_ustuste_sayaci_kova_bossa_sifirlar_gercek_dustude_artan),
    ("sure-tavani-onarimsiz-25dk", vaka31_onarim_yokken_25dk_sure_tavani),
    ("sure-tavani-onarimli-50dk", vaka32_onarim_ilerlerken_30dk_kesilmez),
    ("atlama-sayaci-sifirlama", vaka33_atlama_sayilir_normal_tur_sifirlar),
    ("atlama-ikinci-eskalasyon", vaka34_ikinci_atlama_eskalasyon_basar),
    ("35 karantina motor_ayakta=False", vaka35_karantina_motoru_ayakta_sayilmaz),
    ("36 karantina 6h omur dolunca dusurulur", vaka36_karantina_omru_dolunca_motor_geri_doner),
    ("37 tum zincir karantinada -> en eski (fail-open)", vaka37_karantina_tum_zincir_doldugunda_en_eskiyi_dener),
    ("38 karantina mukerrer eklemez (gunceller)", vaka38_karantina_kayitlari_ekle_mukerrer_engeli),
    ("39 nobet zincir TAM TURETILIR (K257e)", vaka39_nobet_zincir_tam_turetilir),
    ("N-a dikiste CANLI rakip dogar -> ONCEKI", vaka_N_a_dikiste_rakip_canli_dogar),
    ("N-b rakip kilit BYTE-BYTE korunur", vaka_N_b_dikiste_dosya_calinmaz),
    ("N-c sifir baytlik artik devralinir", vaka_N_c_sifir_baytlik_artik_kilit_devralinir),
    ("N-d baskasinin kilidi SILINMEZ", vaka_N_d_baskasinin_kilidini_birakamaz),
    ("N-e kendi kilidimizi SILERIZ", vaka_N_e_kendi_kilidini_birakir),
    ("N-f dikis verilmeden 2x kilit_al", vaka_N_f_dikis_verilmeden_ardisik_kilit_al),
    ("40 dagitilmaz sebep alani dolu", vaka40_dagitilmaz_sebep_alani_dolu),
    ("D1 dondurma dagitimi durdurur", vakaD1_dondurma_bayragi_dagitimi_durdurur),
    ("D2 bayrak kalkinca dagitim doner", vakaD2_bayrak_kalkinca_dagitim_geri_gelir),
    ("D3 ADAY=0 bayrak isirmis gorunmez", vakaD3_aday_sifirken_bayrak_isirmis_gibi_gorunmez),
    ("D4 dondurma komsu kollari bozmaz", vakaD4_dondurma_eskalasyon_ve_gozcu_kollarini_degistirmez),
    ("41 el kitabi kat sutunu URETILIR", vaka41_el_kitabi_ureticisi_kat_sutununu_turetir),
]


def h8_mutasyon_bataryasi():
    """H8 karsilastirmasini olduren mutant, tavan-ustu vakasini kirmizi yakmali."""
    with open(_YOL, encoding="utf-8") as dosya:
        kaynak = dosya.read()
    ankraj = "        if defter_buyumesi > DEFTER_BUYUME_TAVANI:"
    if kaynak.count(ankraj) != 1:
        raise AssertionError("H8 mutant ankraji TEKIL degil: %d" % kaynak.count(ankraj))
    mutant_kaynak = kaynak.replace(
        ankraj, "        if False and defter_buyumesi > DEFTER_BUYUME_TAVANI:", 1)

    kok = tempfile.mkdtemp(prefix="nobet-h8-mutasyon-")
    canli_kapi = globals()["kapi"]
    try:
        mutant_yolu = os.path.join(kok, "nobet-kapi.py")
        with open(mutant_yolu, "w", encoding="utf-8") as dosya:
            dosya.write(mutant_kaynak)
        mutant_spec = importlib.util.spec_from_file_location("nobet_kapi_h8_mutant", mutant_yolu)
        mutant_kapi = importlib.util.module_from_spec(mutant_spec)
        mutant_spec.loader.exec_module(mutant_kapi)
        globals()["kapi"] = mutant_kapi
        try:
            vaka26_defter_tavan_ustu()
        except AssertionError:
            return 1
        return 0
    finally:
        globals()["kapi"] = canli_kapi
        shutil.rmtree(kok, ignore_errors=True)


def yeni_mutasyon_bataryasi():
    """M-A ve M-B ancak ilgili yeni vaka kirmizi yakarsa oldurulmus sayilir."""
    with open(_YOL, encoding="utf-8") as dosya:
        kaynak = dosya.read()
    mutantlar = [
        ("M-A", "    if onarim == 0 and tasinan > 0 and hukum in hafif_hukumler:",
         "    if False and onarim == 0 and tasinan > 0 and hukum in hafif_hukumler:",
         vaka28_onarimsiz_supurme_turu_dusurur),
        # 🔴 K341 (28 Agu 2026): E1 bu satira `dondu` yuklemini ekledi;
        # ankraj onunla birlikte tasindi. Mutant AYNI SEYI olcer: yuklem
        # tumden olurse kova_bos kolu da olur.
        ("M-B", "    if kova_bos or dondu or onarim > 0:",
         "    if False:", vaka30_ustuste_sayaci_kova_bossa_sifirlar_gercek_dustude_artan),
    ]
    oldurulen = 0
    for ad, ankraj, degisim, vaka in mutantlar:
        if kaynak.count(ankraj) != 1:
            raise AssertionError("%s mutant ankraji TEKIL degil: %d" % (
                ad, kaynak.count(ankraj)))
        mutant_kaynak = kaynak.replace(ankraj, degisim, 1)
        kok = tempfile.mkdtemp(prefix="nobet-%s-mutasyon-" % ad.lower())
        canli_kapi = globals()["kapi"]
        try:
            mutant_yolu = os.path.join(kok, "nobet-kapi.py")
            with open(mutant_yolu, "w", encoding="utf-8") as dosya:
                dosya.write(mutant_kaynak)
            mutant_spec = importlib.util.spec_from_file_location(
                "nobet_kapi_%s_mutant" % ad.lower().replace("-", "_"), mutant_yolu)
            mutant_kapi = importlib.util.module_from_spec(mutant_spec)
            mutant_spec.loader.exec_module(mutant_kapi)
            globals()["kapi"] = mutant_kapi
            try:
                vaka()
            except AssertionError:
                oldurulen += 1
                print("MUTANT_KIRMIZI %s" % ad)
            else:
                print("MUTANT_YESIL %s" % ad)
        finally:
            globals()["kapi"] = canli_kapi
            shutil.rmtree(kok, ignore_errors=True)
    return oldurulen


def tur_suresi_mutasyon_bataryasi():
    """M-C/M-D/M-E ancak yeni sure ve atlama vakalari kirmizi yakarsa oldurulur."""
    with open(_YOL, encoding="utf-8") as dosya:
        kaynak = dosya.read()
    mutantlar = [
        ("M-C",
         "            return _sure_tavani_sonucu(cikti, sonlandirici, kisa_tavan, tur_cikti_yolu)",
         "            return 0, _metne_cevir(cikti)",
         vaka31_onarim_yokken_25dk_sure_tavani),
        ("M-D", "        if not onarim_ilerliyor_mu(cikti):",
         "        if True:", vaka32_onarim_ilerlerken_30dk_kesilmez),
        ("M-E", "    yeni = onceki + 1 if atlandi else 0",
         "    yeni = 0", vaka33_atlama_sayilir_normal_tur_sifirlar),
    ]
    oldurulen = 0
    for ad, ankraj, degisim, vaka in mutantlar:
        if kaynak.count(ankraj) != 1:
            raise AssertionError("%s mutant ankraji TEKIL degil: %d" % (
                ad, kaynak.count(ankraj)))
        mutant_kaynak = kaynak.replace(ankraj, degisim, 1)
        kok = tempfile.mkdtemp(prefix="nobet-%s-mutasyon-" % ad.lower())
        canli_kapi = globals()["kapi"]
        try:
            mutant_yolu = os.path.join(kok, "nobet-kapi.py")
            with open(mutant_yolu, "w", encoding="utf-8") as dosya:
                dosya.write(mutant_kaynak)
            mutant_spec = importlib.util.spec_from_file_location(
                "nobet_kapi_%s_mutant" % ad.lower().replace("-", "_"), mutant_yolu)
            mutant_kapi = importlib.util.module_from_spec(mutant_spec)
            mutant_spec.loader.exec_module(mutant_kapi)
            globals()["kapi"] = mutant_kapi
            try:
                vaka()
            except AssertionError:
                oldurulen += 1
                print("MUTANT_KIRMIZI %s" % ad)
            else:
                print("MUTANT_YESIL %s" % ad)
        finally:
            globals()["kapi"] = canli_kapi
            shutil.rmtree(kok, ignore_errors=True)
    return oldurulen


K316_FIKSTUR_KIMLIK = '''"""K316 FIKSTUR — TEK KAYNAGIN birincili BASKA bir ad."""
ISCI_MOTORLARI = ("K316-SAHTE-BIRINCIL", "kimi", "deepseek-pro", "deepseek-flash", "claude")
CANLI_ISCI_MOTORLARI = ("K316-SAHTE-BIRINCIL", "kimi")
EMEKLI_ISCI_MOTORLARI = ("codex", "deepseek-pro", "deepseek-flash")


def canli_kata_goc(motor):
    return motor if motor in CANLI_ISCI_MOTORLARI else CANLI_ISCI_MOTORLARI[0]
'''


def k316_el_kitabi_mutasyon_bataryasi():
    """K316/K3: TEK KAYNAGIN birincili degisince EL KITABI kolu KIRMIZI yanar.

    🔴 HEDEF-KOL ATFI (K182 sinifi): "kirmizi geldi" kanit DEGILDIR. Kirmizinin
    METNI el kitabi kolunun KENDI cumlesini tasimali; baska bir iddia dustuyse
    mutant OLDURULMUS SAYILMAZ. Ayrica KONTROL (mutasyonsuz) kol YESIL olmali.

    Mutasyon CANLI dosyada DEGIL, FIKSTUR kopyasinda: gecici bir kok altina
    `tools/mimar_kimlik.py` yazilir ve `nobet-kapi.py` kopyasinin `EV_KOKU`su
    oraya cevrilir — yani gercekten TEK KAYNAK degistirilir, kat sabiti elle
    ezilmez.
    """
    with open(_YOL, encoding="utf-8") as dosya:
        kaynak = dosya.read()
    ankraj = 'EV_KOKU = "/Users/okan/dev/pruvo"'
    if kaynak.count(ankraj) != 1:
        raise AssertionError("K316 mutant ankraji TEKIL degil: %d" % kaynak.count(ankraj))

    # KONTROL: mutasyonsuz kolda vaka 19 YESIL olmali.
    try:
        vaka19_el_kitabi_spece_kabul_komutu_ekler()
    except AssertionError as hata:
        print("MUTANT_YESIL K316-EL-KITABI (KONTROL zaten KIRMIZI: %s)" % hata)
        return 0
    print("KONTROL_YESIL K316-EL-KITABI")

    kok = tempfile.mkdtemp(prefix="nobet-k316-mutasyon-")
    canli_kapi = globals()["kapi"]
    eski_kimlik = sys.modules.pop("mimar_kimlik", None)
    try:
        araclar = os.path.join(kok, "tools")
        os.makedirs(araclar)
        with open(os.path.join(araclar, "mimar_kimlik.py"), "w", encoding="utf-8") as dosya:
            dosya.write(K316_FIKSTUR_KIMLIK)
        mutant_yolu = os.path.join(kok, "nobet-kapi.py")
        with open(mutant_yolu, "w", encoding="utf-8") as dosya:
            dosya.write(kaynak.replace(ankraj, "EV_KOKU = %r" % kok, 1))
        sys.path.insert(0, araclar)
        try:
            mutant_spec = importlib.util.spec_from_file_location(
                "nobet_kapi_k316_mutant", mutant_yolu)
            mutant_kapi = importlib.util.module_from_spec(mutant_spec)
            mutant_spec.loader.exec_module(mutant_kapi)
        finally:
            if araclar in sys.path:
                sys.path.remove(araclar)
        if mutant_kapi.KAT_TARAMA != "K316-SAHTE-BIRINCIL":
            print("MUTANT_YESIL K316-EL-KITABI (fikstur ISIRMADI: KAT_TARAMA=%r)"
                  % (mutant_kapi.KAT_TARAMA,))
            return 0
        globals()["kapi"] = mutant_kapi
        try:
            vaka19_el_kitabi_spece_kabul_komutu_ekler()
        except AssertionError as hata:
            if "el kitabi kat sutunu kat_sec'ten AYRISTI" in str(hata):
                print("MUTANT_KIRMIZI K316-EL-KITABI (hedef kol: %s)" % str(hata)[:90])
                return 1
            print("MUTANT_YESIL K316-EL-KITABI (BASKA kol dustu: %s)" % str(hata)[:90])
            return 0
        print("MUTANT_YESIL K316-EL-KITABI")
        return 0
    finally:
        globals()["kapi"] = canli_kapi
        if eski_kimlik is not None:
            sys.modules["mimar_kimlik"] = eski_kimlik
        else:
            sys.modules.pop("mimar_kimlik", None)
        shutil.rmtree(kok, ignore_errors=True)


def main():
    dusen = 0
    for ad, fonksiyon in VAKALAR:
        try:
            not_ = fonksiyon()
            print("YESIL  %-34s %s" % (ad, not_))
        except AssertionError as hata:
            dusen += 1
            print("KIRMIZI %-33s %s" % (ad, hata))
        except Exception as hata:  # beklenmeyen cokme de KIRMIZI'dir
            dusen += 1
            print("KIRMIZI %-33s (cokme) %s: %s" % (ad, type(hata).__name__, hata))
    try:
        mutasyon_kirmizi = h8_mutasyon_bataryasi()
    except Exception as hata:
        mutasyon_kirmizi = 0
        print("MUTASYON H8 BOZUK (%s: %s)" % (type(hata).__name__, hata))
    try:
        yeni_mutant_kirmizi = yeni_mutasyon_bataryasi()
    except Exception as hata:
        yeni_mutant_kirmizi = 0
        print("MUTASYON YENI BOZUK (%s: %s)" % (type(hata).__name__, hata))
    try:
        tur_suresi_mutant_kirmizi = tur_suresi_mutasyon_bataryasi()
    except Exception as hata:
        tur_suresi_mutant_kirmizi = 0
        print("MUTASYON TUR_SURESI BOZUK (%s: %s)" % (type(hata).__name__, hata))
    try:
        k316_mutant_kirmizi = k316_el_kitabi_mutasyon_bataryasi()
    except Exception as hata:
        k316_mutant_kirmizi = 0
        print("MUTASYON K316 BOZUK (%s: %s)" % (type(hata).__name__, hata))
    rc = 1 if (dusen or mutasyon_kirmizi < 1 or yeni_mutant_kirmizi < 2
               or tur_suresi_mutant_kirmizi < 3 or k316_mutant_kirmizi < 1) else 0
    print("VAKA=%d DUSEN=%d YENI_VAKA=6 MUTASYON_KIRMIZI=%d "
          "ONCEKI_MUTANT_KIRMIZI=%d/2 MUTANT_KIRMIZI=%d/3 K316_MUTANT_KIRMIZI=%d/1 RC=%d" % (
              len(VAKALAR), dusen, mutasyon_kirmizi, yeni_mutant_kirmizi,
              tur_suresi_mutant_kirmizi, k316_mutant_kirmizi, rc))
    return rc


if __name__ == "__main__":
    sys.exit(main())
