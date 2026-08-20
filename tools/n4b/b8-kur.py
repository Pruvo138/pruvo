#!/usr/bin/env python3
"""B8 KURUCU — turun sayac etkisi TEK KAPIDAN gecer (K241'in UCUNCU yuzeyi).

PAKET: tools/paket-n4b-onarim-hatti-kalanlar.md, blok B8.
DUZLEM: ~/.claude/cron (git YOK) -> idempotent + yedekli.

NEDEN (olculdu, 2026-08-20T09:08:02Z turu): tur KOSTU, BASARISIZ OLDU
(`SURE_TAVANI rc=1`) ve `ustuste_onarimsiz` 105 -> 105, yani ARTMADI.
`tur_kos()` `SURE_TAVANI_ASILDI=1` gorunce ERKEN doner; `tur_kapat()` hic
cagrilmaz, dolayisiyla `ustuste_onarimsiz_guncelle()` de kosmaz.
Sonuc: "ust uste onarimsiz tur" sayaci GERCEKTEN DENENIP BASARISIZ OLAN
turlari SAYMIYOR — yalniz defter bacagina ulasabilen turlari sayiyor.

K241 YUZEYLERI (ucuncu vaka -> tekil yama KESINLIKLE YASAK):
  yuzey 1 (K241): ONARIM=0  -> "is YOK" ile "DENEDI ve basaramadi" ayni kovada (FAZLA sayar)
  yuzey 2 (B6)  : icra_rc=0 -> "kostu ve basardi" ile "HIC KOSMADI" ayni degerde
  yuzey 3 (B8)  : kosan ve DUSEN tur HIC sayilmiyor (EKSIK sayar)

SINIF COZUMU: turun sayac etkisi TEK bir fonksiyondan (`tur_sayacini_kaydet`)
gecer ve `tur_kos`'un HER cikis yolu oradan gecer. Uc hal, uc deger:
  KOSTU_ONARDI -> sayac SIFIRLANIR
  KOSTU_DUSTU  -> sayac +1        (SURE_TAVANI ve MOTOR_YOK kollari DAHIL)
  ATLANDI      -> sayac DEGISMEZ  (atlanan tur onarimsiz tur DEGILDIR; B6 ile tutarli)
Sebep AYRI alanda tasinir (SEBEP=SURE_TAVANI / MOTOR_YOK_AYAKTA / MOTOR_YOK_ZINCIR):
sayac etkisi ayni olsa da anlamlar TEK degere ezilmez.

🔴 SAYACI GEVSETME YASAGI: `nobet-kapi.py:72`'de kayitli sessiz-yesil arizasi.
Bu yama sayaci yalniz EKSIK saydigi yerde DUZELTIR; hicbir kolu susturmaz.

KOSUM:
    python3 tools/n4b/b8-kur.py            # yalniz OLCER
    python3 tools/n4b/b8-kur.py --uygula
    python3 tools/n4b/b8-kur.py --geri-al DAMGA
"""

import argparse
import os
import shutil
import sys
import time

CRON_KOKU = "/Users/okan/.claude/cron"
NOBET_KAPI = os.path.join(CRON_KOKU, "nobet-kapi.py")
TESTLER = os.path.join(CRON_KOKU, "testler.py")
TEST_ADI = "nobet-sayac-cikis-yollari-test.py"
TEST_HEDEF = os.path.join(CRON_KOKU, TEST_ADI)
TEST_KAYNAK = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEST_ADI)

HEDEFLER = (NOBET_KAPI, TESTLER)


# ---------------------------------------------------------------------------
# P1 — TEK KAPI
# ---------------------------------------------------------------------------

P1_ANKOR = ("def tur_kapat(kuru=False, calistirici=None, yaz=True, "
            "kabul_kosucu=None,\n")

P1_YENI = '''# --- B8-TEK-SAYAC-KAPISI (20 Agu 2026, KraL-N4B) ---------------------------
# Bir turun sayac etkisi BURADAN gecer; `tur_kos`'un HER cikis yolu bu kapiya
# ugrar. Onceden 5 `return` vardi ve UCU (SURE_TAVANI, MOTOR_YOK x2) sayaci
# hic gormuyordu: kosup DUSEN tur "onarimsiz tur" sayilmiyordu.
TUR_HALLERI = ("KOSTU_ONARDI", "KOSTU_DUSTU", "ATLANDI")


def tur_sayacini_kaydet(hal, onarim=0, yaz=True, yol=None):
    """Turun `ustuste_onarimsiz` etkisini TEK kapidan gecirir.

    KOSTU_ONARDI -> sifirlanir · KOSTU_DUSTU -> +1 · ATLANDI -> DEGISMEZ.
    Doner: (yeni_sayac, yazildi_mi). ATLANDI'da yazma YAPILMAZ ama cagri
    KAYDA gecer: "sayaca hic ugramayan kol" kalmaz.
    Bilinmeyen hal SESSIZCE gecmez -> ValueError (fail-closed).
    """
    if hal not in TUR_HALLERI:
        raise ValueError("bilinmeyen tur hali: %r" % (hal,))
    if hal == "ATLANDI" or not yaz:
        return ustuste_onarimsiz_oku(yol), False
    return ustuste_onarimsiz_guncelle(onarim if hal == "KOSTU_ONARDI" else 0,
                                      yol), True


def _tur_hali_bas(hal, sebep, sayac, yazildi):
    """Turun hali TEK bicimde raporlanir (tuketici desen kurabilsin)."""
    print("TUR_HALI=%s SEBEP=%s USTUSTE_ONARIMSIZ=%d SAYAC_YAZILDI=%d"
          % (hal, sebep, sayac, int(yazildi)))
    sys.stdout.flush()


def _tur_dustu(sebep):
    """B8: KOSUP DUSEN her kol bu kapidan gecer ve rc=1 doner."""
    sayac, yazildi = tur_sayacini_kaydet("KOSTU_DUSTU")
    _tur_hali_bas("KOSTU_DUSTU", sebep, sayac, yazildi)
    return 1


'''


# ---------------------------------------------------------------------------
# P2 — tur_kapat TEK KAPIYI kullanir
# ---------------------------------------------------------------------------

P2_ESKI = "        ustuste_onarimsiz = ustuste_onarimsiz_guncelle(onarim)\n"
P2_YENI = ('        ustuste_onarimsiz, _ = tur_sayacini_kaydet(   # B8 TEK KAPI\n'
           '            "KOSTU_ONARDI" if onarim > 0 else "KOSTU_DUSTU", onarim)\n')


# ---------------------------------------------------------------------------
# P3 — tur_kos: HER cikis yolu sayaca ugrar
# ---------------------------------------------------------------------------

P3_ESKI = '''def tur_kos():
    """ci-nobeti.sh'in tek girisi: kilit -> motor zinciri -> H1 kapisi."""
    alindi, hukum = kilit_al()
    if not alindi:
        atlanan_ardisik = atlanan_ardisik_guncelle(True)
        print(atlama_satiri(hukum, atlanan_ardisik))
        return 0
'''

P3_YENI = '''def tur_kos():
    """ci-nobeti.sh'in tek girisi: kilit -> motor zinciri -> H1 kapisi.

    B8: bu fonksiyonun HER cikis yolu `tur_sayacini_kaydet`'e ugrar.
    Cikis yolu envanteri CIVILIDIR ve `nobet-sayac-cikis-yollari-test.py`
    tarafindan ast ekseninde sayilir: 5 `return`, uc hal.
    """
    alindi, hukum = kilit_al()
    if not alindi:
        atlanan_ardisik = atlanan_ardisik_guncelle(True)
        print(atlama_satiri(hukum, atlanan_ardisik))
        _tur_hali_bas("ATLANDI", "KILIT_DOLU", *tur_sayacini_kaydet("ATLANDI"))
        return 0
'''

P4_ESKI = '''            else:
                print("HUKUM=MOTOR_YOK sebep=ayakta motor yok")
                return 1
'''
P4_YENI = '''            else:
                print("HUKUM=MOTOR_YOK sebep=ayakta motor yok")
                return _tur_dustu("MOTOR_YOK_AYAKTA")
'''

P5_ESKI = '''        if "SURE_TAVANI_ASILDI=1" in sonuc["cikti"]:
            return 1
        if sonuc["hukum"] == "MOTOR_YOK":
            print("HUKUM=MOTOR_YOK rc=1")
            return 1
'''
P5_YENI = '''        if "SURE_TAVANI_ASILDI=1" in sonuc["cikti"]:
            return _tur_dustu("SURE_TAVANI")
        if sonuc["hukum"] == "MOTOR_YOK":
            print("HUKUM=MOTOR_YOK rc=1")
            return _tur_dustu("MOTOR_YOK_ZINCIR")
'''


# ---------------------------------------------------------------------------

def oku(yol):
    with open(yol, encoding="utf-8") as dosya:
        return dosya.read()


def yaz(yol, metin):
    with open(yol, "w", encoding="utf-8") as dosya:
        dosya.write(metin)


def yedekle(yol, damga):
    hedef = "%s.yedek-b8-%s" % (yol, damga)
    if not os.path.exists(hedef):
        shutil.copy2(yol, hedef)
    return hedef


def degistir(metin, eski, yeni):
    """Ankor TEKIL degilse yama UYGULANMAZ (fail-closed, sessiz kayma YOK)."""
    if yeni in metin:
        return metin, False
    if metin.count(eski) != 1:
        return metin, None
    return metin.replace(eski, yeni, 1), True


DURUM_ADLARI = {True: "UYGULANDI", False: "ZATEN_VARDI", None: "ANKOR_YOK"}


def olculer():
    kapi = oku(NOBET_KAPI)
    tst = oku(TESTLER)
    return [
        ("P1 tur_sayacini_kaydet TEK KAPI", "def tur_sayacini_kaydet(" in kapi),
        ("P2 tur_kapat kapiyi kullaniyor", "KOSTU_ONARDI" in kapi),
        ("P3 ATLANDI kolu kapiya ugruyor",
         '_tur_hali_bas("ATLANDI"' in kapi),
        ("P4 MOTOR_YOK(ayakta) kolu", '_tur_dustu("MOTOR_YOK_AYAKTA")' in kapi),
        ("P5a SURE_TAVANI kolu", '_tur_dustu("SURE_TAVANI")' in kapi),
        ("P5b MOTOR_YOK(zincir) kolu", '_tur_dustu("MOTOR_YOK_ZINCIR")' in kapi),
        ("P6 dogrudan sayac cagrisi TEKIL",
         kapi.count("ustuste_onarimsiz_guncelle(") == 2),   # tanim + TEK kapi
        ("T1 kabul bataryasi kuruldu", os.path.isfile(TEST_HEDEF)),
        ("T2 testler.py'ye kayitli (CAGRI YERI)", TEST_ADI in tst),
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
    print("B8_KURULU=%d/%d" % (kurulu, len(liste)))
    print("HUKUM=%s" % ("KURULU" if kurulu == len(liste) else "EKSIK"))
    return 0 if kurulu == len(liste) else 1


def uygula():
    damga = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    rapor = []
    kapi = oku(NOBET_KAPI)
    yedek_kapi = yedekle(NOBET_KAPI, damga)

    if "def tur_sayacini_kaydet(" in kapi:
        rapor.append(("P1 tek kapi", False))
    elif P1_ANKOR in kapi:
        kapi = kapi.replace(P1_ANKOR, P1_YENI + P1_ANKOR, 1)
        rapor.append(("P1 tek kapi", True))
    else:
        rapor.append(("P1 tek kapi", None))

    for ad, eski, yeni in (("P2 tur_kapat kapisi", P2_ESKI, P2_YENI),
                           ("P3 ATLANDI kolu", P3_ESKI, P3_YENI),
                           ("P4 MOTOR_YOK ayakta", P4_ESKI, P4_YENI),
                           ("P5 SURE_TAVANI + zincir", P5_ESKI, P5_YENI)):
        kapi, d = degistir(kapi, eski, yeni)
        rapor.append((ad, d))
    yaz(NOBET_KAPI, kapi)

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
        print("YAMA=%-28s SONUC=%s" % (ad, DURUM_ADLARI[durum]))
    ankorsuz = sum(1 for _, d in rapor if d is None)
    print("YEDEK=%s" % yedek_kapi)
    print("YEDEK=%s" % yedek_tst)
    print("DAMGA=%s" % damga)
    print("ANKORSUZ=%d" % ankorsuz)
    print("HUKUM=%s" % ("UYGULANDI" if ankorsuz == 0 else "ANKOR_YOK"))
    return 0 if ankorsuz == 0 else 1


def geri_al(damga):
    n = 0
    for yol in HEDEFLER:
        yedek = "%s.yedek-b8-%s" % (yol, damga)
        if os.path.isfile(yedek):
            shutil.copy2(yedek, yol)
            n += 1
            print("GERI_ALINDI=%s" % yol)
    print("GERI_ALINAN=%d" % n)
    return 0 if n else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="B8 kurucu (tek sayac kapisi)")
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
