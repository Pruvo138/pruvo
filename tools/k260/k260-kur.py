#!/usr/bin/env python3
"""K260 KURUCU — kat secimi UC KOVAYA ayrilir; emekli-kat/arizi-jeton kilidi kalkar.

CHIP: KraL-K260KatSec.  DUZLEM: ~/.claude/cron (git YOK) -> idempotent + yedekli.

ARIZA (23 Agu dar teshis turunda olculdu, bu tur DOGRULANDI):
  Onarim kuyrugunda 13 kalem `[DAGITILMAZ]` kaliyor. 11'i `kat_sec` tarafindan
  MIMAR katina dusuruluyor. `KAT_CODEX = KAT_MIMAR` satiri (nobet-kapi.py:133)
  EMEKLI bir motorun adini tasiyan bir kovayi INSAN katina cevirdi: codex canliyken
  o sinif bir ISCIYE dagitiliyordu, codex emekli olunca ayni sinif topluca
  DAGITILMAZ oldu. N4B'nin B4 gocu geri-izdeki `motor` alanini tasiyor ama
  DAGITIM KARARINI ezmiyor — N4B kapanisinda "ayri kalem" diye birakilan kalinti
  budur (merge 66ff84d1: "gocen 15 kaydin 10'u kat_sec ile yine MIMAR'a dusup
  DAGITILMAZ kaliyor").

  🔴 IKINCI KOK (bu turda olculdu): sinif jetonlari HAM METINDE cıplak alt-dize
  olarak araniyor. Bu yuzden jeton bir HAFIZA LINKI slug'inda
  (`[[kapi-ozeti-hukumden-ayrisir]]` -> "kapi"), bir DOSYA ADINDA
  (`nobet-kapi.py` -> "kapi") ya da tirnakli bir CI ADIM ADINDA
  (`Marka->model pilot kabul testi` -> "kabul testi") eslesince kalem
  KALICI olarak insan katina kilitleniyor. Bu SINIF dosyada ZATEN BIR KEZ
  olculmustu (satir 169-171: cıplak "panel" jetonu K54'u OKAN kovasina dusurdu,
  care "jeton YAPISAL olmali"). IKINCI vaka -> tekil yama YASAK, SINIF cozumu.

MIMAR HUKMU (baglayici):
  1. EMEKLI MOTOR ADI, KALEMI MIMAR KATINA KILITLEYEN GEREKCE DEGILDIR. Kat adi
     EMEKLI kumedeyse kalem CANLI kata GOC EDER (`canli_kata_goc`, tek kaynak
     `tools/mimar_kimlik.py`).
  2. 🔴 UCUNCU KOVA SART: "arizi jeton yuzunden mimarda" ile "GERCEKTEN mimar
     kati isi" AYRI YUKLEMLERDIR. Kovalar DAGITILABILIR / MIMAR_KATI_GERCEK /
     OKAN_KAPISI; her birinin SAYISI basilir. Supheli kalem MIMAR_KATI_GERCEK'te
     kalir (FAIL-CLOSED).
  3. OKAN KAPISI DOKUNULMAZ: `kime=Okan` jetonlu kalem dagitima GIRMEZ.
  4. Sayac elle sifirlanmaz; yapay kalem uretilmez.

CARE (uc yama, hepsi TUREYEN — ikinci liste TUTULMAZ):
  P0  `EMEKLI_ISCI_MOTORLARI` tek kaynaktan import edilir (fail-closed: import
      dusesse kume BOS ve goc kolu HIC ATESLEMEZ, davranis bugunkuyle AYNI).
  P1  Sinif jetonlari artik SERBEST METINDE aranir: `[[hafiza-linki]]` slug'lari
      ve `kod acikliklari` (dosya adi / jeton adi / tirnakli adim adi) MASKELENIR.
      🔴 OKAN kapisi TAM METIN uzerinde kalir — maskeleme insan kapisini
      DARALTMAZ (fail-closed, hukum 3).
      Ayrica kat adi EMEKLI kumedeyse CANLI kata gocer (hukum 1).
      UC KOVA yuklemi (`kova_sec` / `kova_dagilimi`) burada tanimlanir; kova
      `kat_sec`ten ve eskale kumesinden TURER, ikinci siniflama TUTULMAZ.
  P2  CAGRI YERI: canli nobet turu kova dagilimini BASAR (`K260_KOVA ...`).

🔴 BU YAMA NELERE DOKUNMAZ (K264 chip'inin alani):
  `tur_kapat`in HUKUM/SAYAC kolu — `tur_hukmu`, `ustuste_onarimsiz`, `IS_YOK`.
  P2 yalniz mevcut `KAT_MIMAR=... KAT_OKAN=...` ozet satirinin ARDINA tek satir
  ekler; sayac/hukum ifadelerine DOKUNMAZ.

KOSUM:
    python3 tools/k260/k260-kur.py              # yalniz OLCER
    python3 tools/k260/k260-kur.py --uygula
    python3 tools/k260/k260-kur.py --geri-al DAMGA
"""

import argparse
import ast
import os
import shutil
import sys
import time

CRON_KOKU = "/Users/okan/.claude/cron"
NOBET_KAPI = os.path.join(CRON_KOKU, "nobet-kapi.py")
TESTLER = os.path.join(CRON_KOKU, "testler.py")
TEST_ADI = "nobet-kat-kovasi-test.py"
TEST_HEDEF = os.path.join(CRON_KOKU, TEST_ADI)
TEST_KAYNAK = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEST_ADI)
HEDEFLER = (NOBET_KAPI, TESTLER)

YEDEK_ONEKI = "yedek-k260"

# --- P0: EMEKLI kume TEK KAYNAKTAN -----------------------------------------
P0A_ESKI = """    from mimar_kimlik import CANLI_ISCI_MOTORLARI, canli_kata_goc
    KAT_KAYNAGI_OLCULDU = True
"""
P0A_YENI = """    from mimar_kimlik import (CANLI_ISCI_MOTORLARI, EMEKLI_ISCI_MOTORLARI,
                              canli_kata_goc)
    KAT_KAYNAGI_OLCULDU = True
"""

P0B_ESKI = """except Exception as _e:                                            # noqa: BLE001
    CANLI_ISCI_MOTORLARI = ()
    KAT_KAYNAGI_OLCULDU = False
"""
P0B_YENI = """except Exception as _e:                                            # noqa: BLE001
    CANLI_ISCI_MOTORLARI = ()
    # K260 fail-closed: kume OLCULEMEDIYSE goc kolu HIC atesleyemez — davranis
    # bugunkuyle AYNI kalir, "hepsi emekli" diye TOPLU goc ETTIRILMEZ.
    EMEKLI_ISCI_MOTORLARI = ()
    KAT_KAYNAGI_OLCULDU = False
"""

# --- P1: kat_sec govdesi + uc kova yuklemi ---------------------------------
P1_ESKI = '''def kat_sec(kalem):
    """H3 sinif tablosu. Claude iscisi HICBIR kosulda donmez."""
    metin = ((kalem.get("is") or "") + " " + (kalem.get("durum_ham") or "")).lower()
    kime = (kalem.get("kime") or "").lower()
    if kime.startswith("okan") or _jeton_var(metin, OKAN_JETONLARI):
        return KAT_OKAN
    if _jeton_var(metin, CODEX_JETONLARI):
        return KAT_CODEX
    if _jeton_var(metin, PRO_JETONLARI):
        return KAT_PRO
    if _jeton_var(metin, FLASH_JETONLARI):
        return KAT_FLASH
    return VARSAYILAN_KAT
'''

P1_YENI = '''# --- K260 KAT KOVASI (24 Agu 2026, KraL-K260KatSec) ------------------------
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
_MASKE_HAFIZA_LINKI = re.compile(r"\\[\\[[^\\]]*\\]\\]")
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


# UC KOVA (H2, K260). Kova `kat_sec`ten ve eskale kumesinden TURER — ikinci
# siniflama TUTULMAZ ([[ikiz-tanim-sessiz-ayrisma]]). Supheli kalem
# MIMAR_KATI_GERCEK'te kalir ([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]).
KOVA_DAGITILABILIR = "DAGITILABILIR"
KOVA_MIMAR_GERCEK = "MIMAR_KATI_GERCEK"
KOVA_OKAN = "OKAN_KAPISI"
KOVA_ADLARI = (KOVA_DAGITILABILIR, KOVA_MIMAR_GERCEK, KOVA_OKAN)


def kat_sec(kalem):
    """H3 sinif tablosu. Claude iscisi HICBIR kosulda donmez."""
    ham = ((kalem.get("is") or "") + " " + (kalem.get("durum_ham") or "")).lower()
    kime = (kalem.get("kime") or "").lower()
    # OKAN kapisi TAM METIN uzerinde olculur (maskeleme UYGULANMAZ).
    if kime.startswith("okan") or _jeton_var(ham, OKAN_JETONLARI):
        return KAT_OKAN
    metin = _serbest_metin(ham)
    if _jeton_var(metin, CODEX_JETONLARI):
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
    kat = kat_sec(kalem)
    if kat == KAT_OKAN:
        return KOVA_OKAN
    if geri_iz is not None and kalem.get("id") in set(eskale_kalemler(geri_iz)):
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


'''

# --- P2: CAGRI YERI --------------------------------------------------------
P2_ESKI = '''    satirlar.append("KAT_MIMAR=%d KAT_TARAMA=%d KAT_MEKANIK=%d KAT_OKAN=%d" % (
        kat_sayaci[KAT_MIMAR], kat_sayaci[KAT_TARAMA],
        kat_sayaci[KAT_MEKANIK], kat_sayaci[KAT_OKAN]))
'''
P2_YENI = '''    satirlar.append("KAT_MIMAR=%d KAT_TARAMA=%d KAT_MEKANIK=%d KAT_OKAN=%d" % (
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
'''


# ---------------------------------------------------------------------------

def oku(yol):
    with open(yol, encoding="utf-8") as dosya:
        return dosya.read()


def yaz(yol, metin):
    with open(yol, "w", encoding="utf-8") as dosya:
        dosya.write(metin)


def yedekle(yol, damga):
    hedef = "%s.%s-%s" % (yol, YEDEK_ONEKI, damga)
    if not os.path.exists(hedef):
        shutil.copy2(yol, hedef)
    return hedef


def degistir(metin, eski, yeni):
    """Doner: (metin, True uygulandi / False zaten vardi / None ankor yok)."""
    if yeni in metin:
        return metin, False
    if metin.count(eski) != 1:
        return metin, None
    return metin.replace(eski, yeni, 1), True


DURUM_ADLARI = {True: "UYGULANDI", False: "ZATEN_VARDI", None: "ANKOR_YOK"}


def _cagri_var(kaynak, fonksiyon, aranan):
    """`fonksiyon` GOVDESINDE `aranan` adli bir CAGRI var mi? (ast — docstring'e
    takilmaz, komsu fonksiyon SIZMAZ; [[ad-iki-rolde-mutanti-golgeler]])."""
    try:
        agac = ast.parse(kaynak)
    except SyntaxError:
        return False
    for dugum in ast.walk(agac):
        if not (isinstance(dugum, ast.FunctionDef) and dugum.name == fonksiyon):
            continue
        for alt in ast.walk(dugum):
            if isinstance(alt, ast.Call) and isinstance(alt.func, ast.Name) \
                    and alt.func.id == aranan:
                return True
        return False
    return False


def olculer():
    nk = oku(NOBET_KAPI)
    tst = oku(TESTLER)
    return [
        ("P0 EMEKLI kume TEK KAYNAKTAN", "EMEKLI_ISCI_MOTORLARI" in nk),
        ("P0b import dusesse kume BOS",
         "    EMEKLI_ISCI_MOTORLARI = ()" in nk),
        ("P1a maskeleme yuklemi", "def _serbest_metin(" in nk),
        ("P1b emekli kat gocu", "def _emekli_kat_gocur(" in nk),
        ("P1c UC KOVA yuklemi", "def kova_sec(" in nk),
        ("P1d kova dagilimi", "def kova_dagilimi(" in nk),
        # Sinif jetonlari SERBEST metinde aranmali; OKAN kapisi HAM metinde.
        ("P1e kat_sec maskeyi KULLANIYOR",
         _cagri_var(nk, "kat_sec", "_serbest_metin")),
        ("P1f OKAN kapisi HAM metinde (fail-closed)",
         "_jeton_var(ham, OKAN_JETONLARI)" in nk),
        # CAGRI YERI: canli tur kovayi BASIYOR mu?
        ("P2 CAGRI YERI: tur kova basiyor",
         _cagri_var(nk, "tur_kapat", "kova_dagilimi")),
        ("P2b kova satiri turde", "K260_KOVA DAGITILABILIR=" in nk),
        ("T1 batarya kuruldu", os.path.isfile(TEST_HEDEF)),
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
        print("YAMA=%-42s DURUM=%s" % (ad, "VAR" if var else "YOK"))
        kurulu += 1 if var else 0
    print("K260_KURULU=%d/%d" % (kurulu, len(liste)))
    print("HUKUM=%s" % ("KURULU" if kurulu == len(liste) else "EKSIK"))
    return 0 if kurulu == len(liste) else 1


def uygula():
    damga = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    rapor = []
    nk = oku(NOBET_KAPI)
    yedek_nk = yedekle(NOBET_KAPI, damga)
    for ad, eski, yeni in (("P0a emekli import", P0A_ESKI, P0A_YENI),
                           ("P0b fail-closed kume", P0B_ESKI, P0B_YENI),
                           ("P1 kat_sec + kovalar", P1_ESKI, P1_YENI),
                           ("P2 cagri yeri", P2_ESKI, P2_YENI)):
        nk, d = degistir(nk, eski, yeni)
        rapor.append((ad, d))
    yaz(NOBET_KAPI, nk)

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
        ankor = '    "nobet-eskalasyon-bayat-test.py",\n'
        if ankor in tst:
            tst = tst.replace(ankor, ankor + '    "%s",\n' % TEST_ADI, 1)
            yaz(TESTLER, tst)
            rapor.append(("T2 testler.py kaydi", True))
        else:
            rapor.append(("T2 testler.py kaydi", None))

    for ad, durum in rapor:
        print("YAMA=%-24s SONUC=%s" % (ad, DURUM_ADLARI[durum]))
    ankorsuz = sum(1 for _, d in rapor if d is None)
    for y in (yedek_nk, yedek_tst):
        print("YEDEK=%s" % y)
    print("DAMGA=%s" % damga)
    print("ANKORSUZ=%d" % ankorsuz)
    print("HUKUM=%s" % ("UYGULANDI" if ankorsuz == 0 else "ANKOR_YOK"))
    return 0 if ankorsuz == 0 else 1


def geri_al(damga):
    n = 0
    for yol in HEDEFLER:
        yedek = "%s.%s-%s" % (yol, YEDEK_ONEKI, damga)
        if os.path.isfile(yedek):
            shutil.copy2(yedek, yol)
            n += 1
            print("GERI_ALINDI=%s" % yol)
    print("GERI_ALINAN=%d" % n)
    return 0 if n else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="K260 kurucu (kat kovasi)")
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
