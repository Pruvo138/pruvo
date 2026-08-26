#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K316 YAMASI — `~/.claude/cron/` surum kontrolu DISIDIR; degisiklik BU BETIKTE yasar.

Betik FAIL-LOUD: her capa kaynakta TAM BIR KEZ gecmek zorunda; gecmezse HICBIR
dosya yazilmaz (kismi yama YOK). Idempotent: yama zaten uygulanmissa "ZATEN" der.
"""
import os
import shutil
import sys

CRON = "/Users/okan/.claude/cron"
BURASI = os.path.dirname(os.path.abspath(__file__))

YAMALAR = []            # (dosya, ad, eski, yeni, imza)


def yama(dosya, ad, eski, yeni, imza):
    """🔴 `imza` ZORUNLU: `yeni` metni cogu yamada `eski`yi ICERIR, bu yuzden
    "eski hala var mi" testi IDEMPOTENSI OLCEMEZ (olculdu: 4 yama IKI KEZ
    uygulandi). Idempotens YALNIZ `yeni`ye OZGU bir imzadan okunur."""
    if imza in eski:
        raise SystemExit("YAMA TANIM HATASI: imza %r `eski` icinde de var (%s)"
                         % (imza, ad))
    YAMALAR.append((dosya, ad, eski, yeni, imza))


# ===================================================================== gozcu-test.py
# (1) SahteKosucu'ya hukum dikisi — GERIYE DONUK UYUMLU (varsayilan davranis AYNI).
yama("gozcu-test.py", "T1 SahteKosucu hukum dikisi",
     '''    def __init__(self, rc=0):
        self.rc = rc
        self.cagrilar = []

    def __call__(self, bayraklar):
        self.cagrilar.append(list(bayraklar))
        # B5: gercek tur HER kolda KOSUM_HUKMU basar; fikstur o sekli TASIR.
        return (self.rc, "SAHTE_TUR rc=%d\\nKOSUM_HUKMU=%s\\n"
                % (self.rc, "TEMIZ" if self.rc == 0 else "MOTOR_DUSTU"))''',
     '''    def __init__(self, rc=0, hukum=None):
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
        return (self.rc, "SAHTE_TUR rc=%d\\nKOSUM_HUKMU=%s\\n" % (self.rc, hukum))''',
     "K316: `hukum` VERILMEZSE davranis BIREBIR eskisi gibi")

# (2) kur() hukum'u tasisin.
yama("gozcu-test.py", "T2 kur() hukum tasir",
     '''        def kur(kosumlar, kalemler_, rc=0, durum=None):
            kok = tempfile.mkdtemp(prefix="tur-", dir=kok10)
            yollar = _yollar(kok)
            os.makedirs(yollar["artik_dizini"], exist_ok=True)
            _durum_yaz(yollar["durum"], durum if durum is not None else
                       {"kosumlar": {}, "son_gunluk_tur": bugun, "taban_alindi": True})
            kosucu = SahteKosucu(rc)''',
     '''        def kur(kosumlar, kalemler_, rc=0, durum=None, hukum=None):
            kok = tempfile.mkdtemp(prefix="tur-", dir=kok10)
            yollar = _yollar(kok)
            os.makedirs(yollar["artik_dizini"], exist_ok=True)
            _durum_yaz(yollar["durum"], durum if durum is not None else
                       {"kosumlar": {}, "son_gunluk_tur": bugun, "taban_alindi": True})
            kosucu = SahteKosucu(rc, hukum)''',
     "SahteKosucu(rc, hukum)")

# (3) 10j — "kosan turun rc'si gozcuye tasinir" eksenini YALITAN vaka.
yama("gozcu-test.py", "T3 vaka 10j (icra rc kolu YALITILIR)",
     '''        # (f) TABAN: ilk kosumda mevcut kirmizilara isci ACILMAZ''',
     '''        # (j) 🔴 K316: kosum hukmu URETKEN ("TEMIZ") ama SURECIN rc'si DUSTU.
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

        # (f) TABAN: ilk kosumda mevcut kirmizilara isci ACILMAZ''',
     "10j kosan turun rc'si gozcuye TASINIR")


# ==================================================================== nobet-kapi.py
# (4) EL KITABI URETICISI — `kat` sutunu ELLE YAZILMAZ.
yama("nobet-kapi.py", "K1 el_kitabi_kat_uret ureticisi",
     '''def el_kitabi_satiri_sec(metin, satirlar):
    """C6: kalem metnine uyan ILK el kitabi satiri (yoksa None)."""''',
     '''def el_kitabi_kat_uret(yol=None, kuru=True):
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
    satirlar = metin.split("\\n")
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
            dosya.write("\\n".join(satirlar))
            dosya.flush()
            os.fsync(dosya.fileno())
        os.replace(gecici, yol)
        yazildi = True
    return {"okunan": okunan, "degisen": len(fark), "yazildi": yazildi, "fark": fark}


def el_kitabi_satiri_sec(metin, satirlar):
    """C6: kalem metnine uyan ILK el kitabi satiri (yoksa None)."""''',
     "def el_kitabi_kat_uret(")

# (5) CLI kolu.
yama("nobet-kapi.py", "K2 --el-kitabi-uret bayragi",
     '''    ayristirici.add_argument("--kilit-al", action="store_true")
    ayristirici.add_argument("--kilit-birak", action="store_true")
    args = ayristirici.parse_args(argv)

    if args.kilit_al:''',
     '''    ayristirici.add_argument("--kilit-al", action="store_true")
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

    if args.kilit_al:''',
     'ayristirici.add_argument("--el-kitabi-uret"')


# =============================================================== nobet-kabul-test.py
# (6) vaka8: motor ADLARI ELLE YAZILMAZ — kat sabitleri tek kaynaktan turer.
yama("nobet-kabul-test.py", "N1 vaka8 motor adlari TURETILIR",
     '''    assert kapi.kat_sec(havuz[-1]) == "OKAN", "Okan kalemi dagitildi"
    assert kapi.kat_sec(havuz[-4]) == "minimax-m3", kapi.kat_sec(havuz[-4])
    assert kapi.kat_sec(havuz[-3]) == "kimi", kapi.kat_sec(havuz[-3])
    assert kapi.kat_sec(havuz[-2]) == "kimi", "varsayilan kat ust kat degil"''',
     '''    assert kapi.kat_sec(havuz[-1]) == "OKAN", "Okan kalemi dagitildi"
    # 🔴 K316: MOTOR ADI ELLE YAZILMAZ. Bu satirlar 20 Agu'da Okan sirayi ters
    # cevirene (m3 BIRINCIL) kadar dogruydu, sonra kaynaktan SESSIZCE ayristi ve
    # 7 gun bataryayi kirmizi yakti. Iddia artik ADA degil SINIFA baglanir:
    # FLASH jetonu -> mekanik kat · PRO jetonu -> tarama kati · jetonsuz ->
    # varsayilan (birincil). Adlar TEK KAYNAKTAN turer.
    assert kapi.KAT_TARAMA == kapi.CANLI_ISCI_MOTORLARI[0], kapi.KAT_TARAMA
    assert kapi.KAT_MEKANIK == kapi.CANLI_ISCI_MOTORLARI[1], kapi.KAT_MEKANIK
    assert kapi.VARSAYILAN_KAT == kapi.KAT_TARAMA, kapi.VARSAYILAN_KAT
    assert kapi.KAT_TARAMA != kapi.KAT_MEKANIK, "iki kat AYNI motora dustu"
    assert kapi.kat_sec(havuz[-4]) == kapi.KAT_MEKANIK, kapi.kat_sec(havuz[-4])
    assert kapi.kat_sec(havuz[-3]) == kapi.KAT_TARAMA, kapi.kat_sec(havuz[-3])
    assert kapi.kat_sec(havuz[-2]) == kapi.VARSAYILAN_KAT, "varsayilan kat AYRISTI"''',
     "kapi.KAT_TARAMA == kapi.CANLI_ISCI_MOTORLARI[0]")

# (7) vaka41 — uretici kolu.
yama("nobet-kabul-test.py", "N2 vaka41 el kitabi ureticisi",
     '''VAKALAR = [''',
     '''def vaka41_el_kitabi_ureticisi_kat_sutununu_turetir():
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
        assert kapi.el_kitabi_kat_uret(yol=fikstur, kuru=True)["degisen"] == 0, \\
            "uretici IDEMPOTENT degil"
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return "uretici: canli fark=0 · fikstur BIREBIR onarildi · idempotent · kuru YAZMAZ"


VAKALAR = [''',
     "def vaka41_el_kitabi_ureticisi_kat_sutununu_turetir")

# (8) vaka41 kaydi.
yama("nobet-kabul-test.py", "N3 vaka41 kaydi",
     '''    ("D4 dondurma komsu kollari bozmaz", vakaD4_dondurma_eskalasyon_ve_gozcu_kollarini_degistirmez),
]''',
     '''    ("D4 dondurma komsu kollari bozmaz", vakaD4_dondurma_eskalasyon_ve_gozcu_kollarini_degistirmez),
    ("41 el kitabi kat sutunu URETILIR", vaka41_el_kitabi_ureticisi_kat_sutununu_turetir),
]''',
     '("41 el kitabi kat sutunu URETILIR"')

# (9) K316 mutant bataryasi — TEK KAYNAGIN birincili degisince el kitabi kolu KIRMIZI.
yama("nobet-kabul-test.py", "N4 K316 mutant bataryasi",
     '''def main():
    dusen = 0''',
     '''K316_FIKSTUR_KIMLIK = \'\'\'"""K316 FIKSTUR — TEK KAYNAGIN birincili BASKA bir ad."""
ISCI_MOTORLARI = ("K316-SAHTE-BIRINCIL", "kimi", "deepseek-pro", "deepseek-flash", "claude")
CANLI_ISCI_MOTORLARI = ("K316-SAHTE-BIRINCIL", "kimi")
EMEKLI_ISCI_MOTORLARI = ("codex", "deepseek-pro", "deepseek-flash")


def canli_kata_goc(motor):
    return motor if motor in CANLI_ISCI_MOTORLARI else CANLI_ISCI_MOTORLARI[0]
\'\'\'


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
    ankraj = \'EV_KOKU = "/Users/okan/dev/pruvo"\'
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
    dusen = 0''',
     "def k316_el_kitabi_mutasyon_bataryasi")

# (10) rc + rapor satirina K316 kolunu bagla.
yama("nobet-kabul-test.py", "N5 K316 kolu rc'ye baglanir",
     '''    rc = 1 if (dusen or mutasyon_kirmizi < 1 or yeni_mutant_kirmizi < 2
               or tur_suresi_mutant_kirmizi < 3) else 0
    print("VAKA=%d DUSEN=%d YENI_VAKA=6 MUTASYON_KIRMIZI=%d "
          "ONCEKI_MUTANT_KIRMIZI=%d/2 MUTANT_KIRMIZI=%d/3 RC=%d" % (
              len(VAKALAR), dusen, mutasyon_kirmizi, yeni_mutant_kirmizi,
              tur_suresi_mutant_kirmizi, rc))''',
     '''    try:
        k316_mutant_kirmizi = k316_el_kitabi_mutasyon_bataryasi()
    except Exception as hata:
        k316_mutant_kirmizi = 0
        print("MUTASYON K316 BOZUK (%s: %s)" % (type(hata).__name__, hata))
    rc = 1 if (dusen or mutasyon_kirmizi < 1 or yeni_mutant_kirmizi < 2
               or tur_suresi_mutant_kirmizi < 3 or k316_mutant_kirmizi < 1) else 0
    print("VAKA=%d DUSEN=%d YENI_VAKA=6 MUTASYON_KIRMIZI=%d "
          "ONCEKI_MUTANT_KIRMIZI=%d/2 MUTANT_KIRMIZI=%d/3 K316_MUTANT_KIRMIZI=%d/1 RC=%d" % (
              len(VAKALAR), dusen, mutasyon_kirmizi, yeni_mutant_kirmizi,
              tur_suresi_mutant_kirmizi, k316_mutant_kirmizi, rc))''',
     "K316_MUTANT_KIRMIZI=%d/1")


def main():
    # 1) TUM capalari ONCE dogrula (kismi yama YOK).
    icerikler = {}
    ozgun = {}          # 🔴 imza DAIMA OZGUN icerikte aranir: ayni kosumda daha
                        # once uygulanan bir yamanin metni imzayi TASIYABILIR.
    hazir = []
    for dosya, ad, eski, yeni, imza in YAMALAR:
        yol = os.path.join(CRON, dosya)
        if yol not in icerikler:
            with open(yol, encoding="utf-8") as f:
                icerikler[yol] = f.read()
            ozgun[yol] = icerikler[yol]
        metin = icerikler[yol]
        if imza in ozgun[yol]:
            print("ZATEN  %-40s %s" % (ad, dosya))
            continue
        adet = metin.count(eski)
        if adet != 1:
            print("CAPA_TUTMADI %-34s %s (kaynakta %d kez)" % (ad, dosya, adet))
            return 3
        icerikler[yol] = metin.replace(eski, yeni, 1)
        hazir.append(ad)

    # 2) gozcu-mutasyon.py TAM DEGISIM (capa listesi bastan turetilir).
    yeni_surucu = os.path.join(BURASI, "gozcu-mutasyon.yeni.py")
    hedef_surucu = os.path.join(CRON, "gozcu-mutasyon.py")
    with open(yeni_surucu, encoding="utf-8") as f:
        surucu_metni = f.read()
    with open(hedef_surucu, encoding="utf-8") as f:
        eski_surucu = f.read()

    # 3) YAZ.
    for yol, metin in icerikler.items():
        with open(yol, "w", encoding="utf-8") as f:
            f.write(metin)
    if surucu_metni != eski_surucu:
        shutil.copyfile(yeni_surucu, hedef_surucu)
        print("YAZILDI gozcu-mutasyon.py (TAM DEGISIM)")
    else:
        print("ZATEN  gozcu-mutasyon.py")
    for ad in hazir:
        print("YAZILDI %s" % ad)
    print("YAMA TAMAM: %d capa uygulandi" % len(hazir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
