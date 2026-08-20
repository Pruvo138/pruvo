#!/usr/bin/env python3
"""B5 KURUCU — DEFTER bacaginin rc'si RUN-ID denemesine YAZILMASIN.

PAKET: tools/paket-n4b-onarim-hatti-kalanlar.md, blok B5.
DUZLEM: ~/.claude/cron (git YOK) -> idempotent + yedekli.
🔴 ON KOSUL: B6 KURULU olmali (bu yama B6'nin actigi kollara baglanir).

NEDEN (olculdu, gozcu.log:1365-1371, 19 Agu 22:53Z): motor kostu (`rc=0`),
cikti "🟢 CI temiz" dedi, tur yine `HUKUM=ONARIMSIZ_TUR rc=1` ile kapandi ve
O RUN-ID'NIN deneme sayaci ARTTI. N4A'nin saydigi 10 eskalasyonun 4'u bu
yoldan dogdu.

KOK: iki AYRI OZNE tek sayaca yaziliyordu.
  · DEFTER bacagi (`tur_kapat` H1): "bu EVDE acik kalem borcu var mi" —
    ONARIMSIZ_TUR bunu olcer. Turun actigi CI kirmizisiyla ILGISI YOKTUR.
  · KOSUM oznesi: "bu run-id'nin kirmizisi icin acilan tur ne yapti".
`tur_kos` ikincisini basmiyordu, `gozcu.py` de birincinin rc'sini
`deneme_sonraki`ye veriyordu.

CARE: `KOSUM_HUKMU=` jetonu — YALNIZ o kosuma dair kollardan turer
(motor rc · turun KENDI hukmu · turun KENDI KAPANAN/DAGITILAN olcumu).
Defterin hukmu buraya GIRMEZ. Gozcunun KENDI rc'si DEGISMEZ (kabul-4):
tur kirmizi kapandiysa gozcu yine kirmizidir — degisen yalniz KIME YAZILDIGI.

KOSUM:
    python3 tools/n4b/b5-kur.py            # yalniz OLCER
    python3 tools/n4b/b5-kur.py --uygula
    python3 tools/n4b/b5-kur.py --geri-al DAMGA
"""

import argparse
import os
import shutil
import sys
import time

CRON_KOKU = "/Users/okan/.claude/cron"
NOBET_KAPI = os.path.join(CRON_KOKU, "nobet-kapi.py")
GOZCU = os.path.join(CRON_KOKU, "gozcu.py")
TESTLER = os.path.join(CRON_KOKU, "testler.py")
TEST_ADI = "nobet-kosum-hukmu-test.py"
TEST_HEDEF = os.path.join(CRON_KOKU, TEST_ADI)
TEST_KAYNAK = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEST_ADI)

HEDEFLER = (NOBET_KAPI, GOZCU, TESTLER,
            os.path.join(CRON_KOKU, "gozcu-test.py"))


# --- nobet-kapi.py ---------------------------------------------------------

N1_ANKOR = 'TUR_HALLERI = ("KOSTU_ONARDI", "KOSTU_DUSTU", "ATLANDI")\n'

N1_YENI = '''
# --- B5-KOSUM-HUKMU (20 Agu 2026, KraL-N4B) --------------------------------
# RUN-ID denemesinin oznesi DEFTER bacagindan AYRIDIR. Olculdu
# (gozcu.log:1365-1371): motor rc=0 + "CI temiz" iken tur ONARIMSIZ_TUR rc=1
# kapandi ve o run-id'nin denemesi ARTTI; 10 eskalasyonun 4'u boyle dogdu.
KOSUM_HUKUMLERI = ("TEMIZ", "ONARIM_DENENDI", "MOTOR_DUSTU", "OLCULEMEDI")


def kosum_hukmu_coz(motor_rc, tur_hukmu, kapanan=0, dagitilan=0):
    """B5: bu KOSUMUN hukmu — yalniz kosuma dair kollardan turer.

    TEMIZ          -> motor kostu ve turun KENDI hukmu temiz: deneme KAPANIR.
    ONARIM_DENENDI -> motor kostu ama is bitmedi: deneme ARTAR (eskalasyon YASAR).
    MOTOR_DUSTU    -> motor hic bitiremedi (rc!=0, sure tavani, motor yok).
    OLCULEMEDI     -> hukum okunamadi; fail-closed, deneme ARTAR.
    🔴 Defter bacaginin ONARIMSIZ_TUR hukmu bu fonksiyona GIRMEZ.
    """
    if motor_rc is None:
        return "OLCULEMEDI"
    if motor_rc != 0:
        return "MOTOR_DUSTU"
    hukum = (tur_hukmu or "").strip()
    if hukum in ("TEMIZ", "KAPANDI", "ONARIM_YOK"):
        return "TEMIZ"
    if hukum == "ONARIM_ILERLIYOR" or (kapanan + dagitilan) > 0:
        return "ONARIM_DENENDI"
    if not hukum:
        return "OLCULEMEDI"
    return "ONARIM_DENENDI"


'''

N2_ESKI = '''def _tur_dustu(sebep):
    """B8: KOSUP DUSEN her kol bu kapidan gecer ve rc=1 doner."""
    sayac, yazildi = tur_sayacini_kaydet("KOSTU_DUSTU")
    _tur_hali_bas("KOSTU_DUSTU", sebep, sayac, yazildi)
    return 1
'''
N2_YENI = '''def _tur_dustu(sebep):
    """B8: KOSUP DUSEN her kol bu kapidan gecer ve rc=1 doner.

    B5: ayni kol RUN-ID hukmunu de basar — dusen tur "temiz kosum" DEGILDIR
    ve bu hukum defter bacagindan BAGIMSIZDIR.
    """
    sayac, yazildi = tur_sayacini_kaydet("KOSTU_DUSTU")
    _tur_hali_bas("KOSTU_DUSTU", sebep, sayac, yazildi)
    print("KOSUM_HUKMU=MOTOR_DUSTU MOTOR_RC=- TUR_HUKMU=%s" % sebep)
    sys.stdout.flush()
    return 1
'''

N3_ESKI = '''        mevcut_hukum = tur_hukmu_ayikla(sonuc["cikti"])
        kapi = tur_kapat(defter_once=once, tasinan=tasinan,
                         mevcut_hukum=mevcut_hukum)
'''
N3_YENI = '''        mevcut_hukum = tur_hukmu_ayikla(sonuc["cikti"])
        # 🔴 B5: RUN-ID hukmu DEFTER bacagindan ONCE ve ONDAN BAGIMSIZ basilir.
        # `tur_kapat` birazdan ONARIMSIZ_TUR yazabilir; o hukum EVIN borcunu
        # olcer, bu run'in kirmizisini DEGIL. Ikisi ayni sayaca yazilinca
        # 10 eskalasyonun 4'u sahte dogdu (gozcu.log:1365-1371).
        print("KOSUM_HUKMU=%s MOTOR_RC=%s TUR_HUKMU=%s" % (
            kosum_hukmu_coz(sonuc["rc"], mevcut_hukum,
                            tur_olcumu_ayikla(sonuc["cikti"], "KAPANAN"),
                            tur_olcumu_ayikla(sonuc["cikti"], "DAGITILAN")),
            sonuc["rc"], mevcut_hukum or "-"))
        sys.stdout.flush()
        kapi = tur_kapat(defter_once=once, tasinan=tasinan,
                         mevcut_hukum=mevcut_hukum)
'''


# --- gozcu.py --------------------------------------------------------------

G1_ANKOR = 'ICRA_HALLERI = ("KOSULMADI", "ATLANDI", "KOSTU_BASARILI", "KOSTU_DUSTU")\n'

G1_YENI = '''_KOSUM_HUKMU_DESENI = re.compile(r"(?<![A-Za-z0-9_])KOSUM_HUKMU\\s*=\\s*([A-Z_]+)")


def kosum_hukmunu_ayikla(cikti):
    """B5: RUN-ID denemesi DEFTER bacagindan DEGIL, kosumun KENDI hukmunden.

    Jeton yoksa `OLCULEMEDI` doner (fail-closed): "okuyamadim" SESSIZCE
    "temiz" DEMEK DEGILDIR — deneme yine artar, eskalasyon yolu ACIK kalir.
    """
    eslesme = _KOSUM_HUKMU_DESENI.findall(cikti or "")
    return eslesme[-1] if eslesme else "OLCULEMEDI"


'''

G2_ESKI = '    icra_hal = "KOSULMADI"    # B6: hal, rc\'den AYRI alandir\n'
G2_YENI = ('    icra_hal = "KOSULMADI"    # B6: hal, rc\'den AYRI alandir\n'
           '    kosum_hukmu = "KOSULMADI"  # B5: RUN-ID denemesinin AYRI oznesi\n')

G3_ESKI = '            icra_hal, icra_rc = icra_halini_coz(True, icra_rc, icra_cikti)\n'
G3_YENI = ('            icra_hal, icra_rc = icra_halini_coz(True, icra_rc, icra_cikti)\n'
           '            kosum_hukmu = kosum_hukmunu_ayikla(icra_cikti)\n')

G4_ESKI = '''                yeni_kayit = deneme_sonraki(kayit, icra_hal == "KOSTU_BASARILI")
'''
G4_YENI = '''                # 🔴 B5: run-id denemesi DEFTER bacagindan DEGIL, KOSUMUN
                # kendi hukmunden turer. `icra_hal` surecin rc'sidir ve defter
                # bacagi ONARIMSIZ_TUR yazinca CI temiz olsa bile DUSTU olur.
                yeni_kayit = deneme_sonraki(kayit, kosum_hukmu == "TEMIZ")
'''

G5_ESKI = '''        icra_rc, icra_cikti = tur_kosucu(["--tur-kapat"])
        icra_hal, icra_rc = icra_halini_coz(True, icra_rc, icra_cikti)
'''
G5_YENI = '''        icra_rc, icra_cikti = tur_kosucu(["--tur-kapat"])
        icra_hal, icra_rc = icra_halini_coz(True, icra_rc, icra_cikti)
        kosum_hukmu = kosum_hukmunu_ayikla(icra_cikti)
'''

G6_ESKI = '''        icra_rc, icra_cikti = tur_kosucu(["--tur"])
        icra_hal, icra_rc = icra_halini_coz(True, icra_rc, icra_cikti)
        durum["son_gunluk_tur"] = time.strftime("%Y-%m-%d", time.gmtime(simdi))
'''
G6_YENI = '''        icra_rc, icra_cikti = tur_kosucu(["--tur"])
        icra_hal, icra_rc = icra_halini_coz(True, icra_rc, icra_cikti)
        kosum_hukmu = kosum_hukmunu_ayikla(icra_cikti)
        durum["son_gunluk_tur"] = time.strftime("%Y-%m-%d", time.gmtime(simdi))
'''

# --- P8: KOMSU FIKSTURUN SEKLI (regresyon onarimi) -------------------------
# `gozcu-test.py::SahteKosucu` turun ciktisini `"SAHTE_TUR rc=%d"` diye uretir;
# gercek `tur_kos` ise B5'ten beri HER kolda `KOSUM_HUKMU=` basar. Sekli
# eksik fikstur, jetonu bulamayinca fail-closed `OLCULEMEDI` alir ve "basarili
# onarim KAPANDI" vakasi DUSTU'ye doner. Olculdu (b5-kanit): gozcu-test
# DUSEN 1 -> 4. 🔴 Care fail-closed'i gevsetmek DEGIL, FIKSTURU gercek
# sozlesmeye uydurmaktir ([[sahte-bagimlilik-sekli-negatif-blogu-kutsar]]).
P8_ESKI = '''    def __call__(self, bayraklar):
        self.cagrilar.append(list(bayraklar))
        return (self.rc, "SAHTE_TUR rc=%d" % self.rc)
'''
P8_YENI = '''    def __call__(self, bayraklar):
        self.cagrilar.append(list(bayraklar))
        # B5: gercek tur HER kolda KOSUM_HUKMU basar; fikstur o sekli TASIR.
        return (self.rc, "SAHTE_TUR rc=%d\\nKOSUM_HUKMU=%s\\n"
                % (self.rc, "TEMIZ" if self.rc == 0 else "MOTOR_DUSTU"))
'''
GOZCU_TEST = os.path.join(CRON_KOKU, "gozcu-test.py")


G7_ESKI = '        "icra_hal": icra_hal,      # B6: uc hal UC deger\n'
G7_YENI = ('        "icra_hal": icra_hal,      # B6: uc hal UC deger\n'
           '        "kosum_hukmu": kosum_hukmu,  # B5: run-id oznesi, defterden AYRI\n')


# ---------------------------------------------------------------------------

def oku(yol):
    with open(yol, encoding="utf-8") as dosya:
        return dosya.read()


def yaz(yol, metin):
    with open(yol, "w", encoding="utf-8") as dosya:
        dosya.write(metin)


def yedekle(yol, damga):
    hedef = "%s.yedek-b5-%s" % (yol, damga)
    if not os.path.exists(hedef):
        shutil.copy2(yol, hedef)
    return hedef


def degistir(metin, eski, yeni):
    if yeni in metin:
        return metin, False
    if metin.count(eski) != 1:
        return metin, None
    return metin.replace(eski, yeni, 1), True


DURUM_ADLARI = {True: "UYGULANDI", False: "ZATEN_VARDI", None: "ANKOR_YOK"}


def olculer():
    nk = oku(NOBET_KAPI)
    gz = oku(GOZCU)
    tst = oku(TESTLER)
    return [
        ("N1 kosum_hukmu_coz TEK KAYNAK", "def kosum_hukmu_coz(" in nk),
        ("N2 dusen kol RUN-ID hukmu basiyor",
         "KOSUM_HUKMU=MOTOR_DUSTU" in nk),
        ("N3 normal kol RUN-ID hukmu basiyor",
         'print("KOSUM_HUKMU=%s MOTOR_RC=%s TUR_HUKMU=%s"' in nk),
        ("G1 kosum_hukmunu_ayikla", "def kosum_hukmunu_ayikla(" in gz),
        ("G2 kosum_hukmu ilklendi", 'kosum_hukmu = "KOSULMADI"' in gz),
        ("G4 deneme KOSUM hukmunden",
         'deneme_sonraki(kayit, kosum_hukmu == "TEMIZ")' in gz),
        ("G4b defter rc'si sayaca YAZMIYOR",
         'deneme_sonraki(kayit, icra_hal == "KOSTU_BASARILI")' not in gz),
        ("G7 kalpte kosum_hukmu", '"kosum_hukmu": kosum_hukmu,' in gz),
        ("T1 kabul bataryasi kuruldu", os.path.isfile(TEST_HEDEF)),
        ("T2 testler.py'ye kayitli (CAGRI YERI)", TEST_ADI in tst),
        ("P8 komsu fikstur sekli guncel",
         "KOSUM_HUKMU=%s" in oku(GOZCU_TEST)),
    ]


def olc():
    try:
        liste = olculer()
    except OSError as hata:
        print("HUKUM=OLCULEMEDI sebep=%s" % hata)
        return 2
    kurulu = 0
    for ad, var in liste:
        print("YAMA=%-38s DURUM=%s" % (ad, "VAR" if var else "YOK"))
        kurulu += 1 if var else 0
    print("B5_KURULU=%d/%d" % (kurulu, len(liste)))
    print("HUKUM=%s" % ("KURULU" if kurulu == len(liste) else "EKSIK"))
    return 0 if kurulu == len(liste) else 1


def uygula():
    if "def icra_halini_coz(" not in oku(GOZCU):
        print("HUKUM=ON_KOSUL_YOK sebep=B6 kurulu degil (icra_halini_coz yok)")
        return 2
    damga = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    rapor = []

    nk = oku(NOBET_KAPI)
    yedek_nk = yedekle(NOBET_KAPI, damga)
    if "def kosum_hukmu_coz(" in nk:
        rapor.append(("N1 tek kaynak", False))
    elif nk.count(N1_ANKOR) == 1:
        nk = nk.replace(N1_ANKOR, N1_ANKOR + N1_YENI, 1)
        rapor.append(("N1 tek kaynak", True))
    else:
        rapor.append(("N1 tek kaynak", None))
    for ad, eski, yeni in (("N2 dusen kol", N2_ESKI, N2_YENI),
                           ("N3 normal kol", N3_ESKI, N3_YENI)):
        nk, d = degistir(nk, eski, yeni)
        rapor.append((ad, d))
    yaz(NOBET_KAPI, nk)

    gz = oku(GOZCU)
    yedek_gz = yedekle(GOZCU, damga)
    if "def kosum_hukmunu_ayikla(" in gz:
        rapor.append(("G1 ayiklayici", False))
    elif gz.count(G1_ANKOR) == 1:
        gz = gz.replace(G1_ANKOR, G1_ANKOR + G1_YENI, 1)
        rapor.append(("G1 ayiklayici", True))
    else:
        rapor.append(("G1 ayiklayici", None))
    for ad, eski, yeni in (("G2 ilklendirme", G2_ESKI, G2_YENI),
                           ("G3 CI kolu", G3_ESKI, G3_YENI),
                           ("G4 deneme oznesi", G4_ESKI, G4_YENI),
                           ("G5 defter dagitim kolu", G5_ESKI, G5_YENI),
                           ("G6 gunluk defter kolu", G6_ESKI, G6_YENI),
                           ("G7 kalp alani", G7_ESKI, G7_YENI)):
        gz, d = degistir(gz, eski, yeni)
        rapor.append((ad, d))
    yaz(GOZCU, gz)

    gt = oku(GOZCU_TEST)
    yedek_gt = yedekle(GOZCU_TEST, damga)
    gt, d = degistir(gt, P8_ESKI, P8_YENI)
    rapor.append(("P8 komsu fikstur", d))
    if d:
        yaz(GOZCU_TEST, gt)

    if os.path.isfile(TEST_KAYNAK):
        shutil.copy2(TEST_KAYNAK, TEST_HEDEF)
        os.chmod(TEST_HEDEF, 0o755)
        rapor.append(("T1 batarya kuruldu", True))
    else:
        rapor.append(("T1 batarya kuruldu", None))

    tst = oku(TESTLER)
    yedek_tst = yedekle(TESTLER, damga)
    if TEST_ADI in tst:
        rapor.append(("T2 testler.py kaydi", False))
    else:
        ankor = '    "kilit-tatbikat.py",\n'
        if ankor in tst:
            tst = tst.replace(ankor, ankor + '    "%s",\n' % TEST_ADI, 1)
            yaz(TESTLER, tst)
            rapor.append(("T2 testler.py kaydi", True))
        else:
            rapor.append(("T2 testler.py kaydi", None))

    for ad, durum in rapor:
        print("YAMA=%-26s SONUC=%s" % (ad, DURUM_ADLARI[durum]))
    ankorsuz = sum(1 for _, d in rapor if d is None)
    for y in (yedek_nk, yedek_gz, yedek_tst, yedek_gt):
        print("YEDEK=%s" % y)
    print("DAMGA=%s" % damga)
    print("ANKORSUZ=%d" % ankorsuz)
    print("HUKUM=%s" % ("UYGULANDI" if ankorsuz == 0 else "ANKOR_YOK"))
    return 0 if ankorsuz == 0 else 1


def geri_al(damga):
    n = 0
    for yol in HEDEFLER:
        yedek = "%s.yedek-b5-%s" % (yol, damga)
        if os.path.isfile(yedek):
            shutil.copy2(yedek, yol)
            n += 1
            print("GERI_ALINDI=%s" % yol)
    print("GERI_ALINAN=%d" % n)
    return 0 if n else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="B5 kurucu (kosum hukmu ayrimi)")
    ap.add_argument("--uygula", action="store_true")
    ap.add_argument("--geri-al", metavar="DAMGA")
    args = ap.parse_args(argv)
    if args.geri_al:
        return geri_al(args.geri_al)
    if args.uygula:
        rc = uygula()
        print("--- KURULUM SONRASI OLCUM ---")
        olc()
        return rc
    return olc()


if __name__ == "__main__":
    sys.exit(main())
