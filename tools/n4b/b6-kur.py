#!/usr/bin/env python3
"""B6 KURUCU — `icra_rc=0` UC HALI IKI DEGERE SIKISTIRMASIN (K241, yuzey 2).

PAKET: tools/paket-n4b-onarim-hatti-kalanlar.md, blok B6.
DUZLEM: ~/.claude/cron (git YOK) -> idempotent + yedekli.

NEDEN (olculdu, 2026-08-20T09:23:00Z): `gozcu-kalp.json` `icra_rc: 0`, `rc: 0`
yani YESIL. Ayni turun log satiri (`gozcu.log:1999`):
    === 2026-08-20T09:23:02Z NOBET ATLANDI HUKUM=ONCEKI_TUR_SURUYOR ... ===
Tur HIC KOSMADI: onceki tur (09:08) hala ucustaydi.
`nobet-kapi.py` kilit yoksa `return 0` verir; `gozcu.py:496` o `0`'i dogrudan
`icra_rc` yapar; `gozcu.py:512` `icra_rc == 0` diye rc'yi yukseltmez.

🔴 Tek skaler UC hali tasiyordu — `KOSTU_BASARILI` · `KOSTU_DUSTU` · `ATLANDI` —
ve UCUNCUSU BIRINCISIYLE AYNI degere (`0`) esleniyordu. Sonuc: N4A'nin
"icra_rc yesile dondu ve iki ARDISIK turda goruldu" sarti, arka arkaya
ATLANAN iki turla SAHTE olarak saglanabiliyordu.

CARE (uc alan, uc soru — hepsi AYRI):
  `icra_hal`     : KOSULMADI / ATLANDI / KOSTU_BASARILI / KOSTU_DUSTU
  `icra_rc`      : YALNIZ gercekten kosmus turda anlamli; ATLANDI'da None
  `icra_denendi` : "gozcu bir tur ACTI MI" — bu rc'den BASKA bir sorudur

🔴 TUKETICI ENVANTERI (iddia duzeyinde DEGIL, olculerek):
`icra_rc`'yi gozcu.py DISINDA okuyan TEK yer `nobet-tetik.py:155`
(`if kalp.get("icra_rc") is not None:` = "gozcu turu ZATEN acti mi").
`icra_rc` ATLANDI'da None olunca o kol "acmadi" derdi ve IKINCI tur acilirdi.
Bu yuzden o tuketici `icra_denendi`'ye tasindi (eski kalpler icin geri donuk
kol korunarak). [[tasima-tuketici-envanteri-iddia-duzeyinde]]

KOSUM:
    python3 tools/n4b/b6-kur.py            # yalniz OLCER
    python3 tools/n4b/b6-kur.py --uygula
    python3 tools/n4b/b6-kur.py --geri-al DAMGA
"""

import argparse
import os
import shutil
import sys
import time

CRON_KOKU = "/Users/okan/.claude/cron"
GOZCU = os.path.join(CRON_KOKU, "gozcu.py")
TETIK = os.path.join(CRON_KOKU, "nobet-tetik.py")
TESTLER = os.path.join(CRON_KOKU, "testler.py")
TEST_ADI = "nobet-icra-hali-test.py"
TEST_HEDEF = os.path.join(CRON_KOKU, TEST_ADI)
TEST_KAYNAK = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEST_ADI)

HEDEFLER = (GOZCU, TETIK, TESTLER)


G0_ESKI = "import os\nimport shutil\n"
G0_YENI = "import os\nimport re\nimport shutil\n"


G1_ANKOR = "def kalp_satiri(kalp):\n"

G1_YENI = '''# --- B6-ICRA-HALI (20 Agu 2026, KraL-N4B) — K241'in IKINCI yuzeyi ----------
# Olculdu (09:23:00Z): kalpte `icra_rc: 0` (yesil) yaziyordu, ayni turun log
# satiri `NOBET ATLANDI HUKUM=ONCEKI_TUR_SURUYOR` idi -> tur HIC KOSMADI.
# Tek skaler uc hali tasiyor, ucuncusu birincisiyle AYNI degere esleniyordu.
ICRA_HALLERI = ("KOSULMADI", "ATLANDI", "KOSTU_BASARILI", "KOSTU_DUSTU")
_TUR_HALI_DESENI = re.compile(r"(?<![A-Za-z0-9_])TUR_HALI\\s*=\\s*([A-Z_]+)")


def icra_halini_coz(denendi, ham_rc, cikti):
    """B6: (icra_hal, icra_rc) — uc hal UC degere ayrilir.

    Kaynak sirasi: (1) turun KENDI beyani `TUR_HALI=` — nobet-kapi B8'den
    beri HER cikis yolunda basar; (2) `NOBET ATLANDI` satiri (B8 oncesi
    kalintilar ve eski loglar icin); (3) ham rc.
    ATLANDI'da `icra_rc` None doner: "kostu ve basardi" ile "HIC KOSMADI"
    ayni degere DUSMEZ.
    """
    if not denendi or ham_rc is None:
        return "KOSULMADI", None
    metin = cikti or ""
    beyanlar = _TUR_HALI_DESENI.findall(metin)
    if (beyanlar and beyanlar[-1] == "ATLANDI") or "NOBET ATLANDI" in metin:
        return "ATLANDI", None
    if ham_rc == 0:
        return "KOSTU_BASARILI", 0
    return "KOSTU_DUSTU", ham_rc


'''


G2_ESKI = '''    icra_rc = None
    icra_cikti = ""
    icra_notu = ""
'''
G2_YENI = '''    icra_rc = None
    icra_cikti = ""
    icra_notu = ""
    icra_hal = "KOSULMADI"    # B6: hal, rc'den AYRI alandir
    icra_denendi = False      # B6: "tur ACILDI MI" sorusu rc'den AYRIDIR
'''


G3_ESKI = '''            try:
                icra_rc, icra_cikti = tur_kosucu(["--tur"])
            finally:
                _kilit_birak(kilit_yolu)
            kayit = (durum.get("kosumlar") or {}).get(str(hedef["id"])) or {}
            yeni_kayit = deneme_sonraki(kayit, icra_rc == 0)
            yeni_kayit["ad"] = hedef.get("ad", "")
            yeni_kayit["damga"] = _damga(simdi)
            durum.setdefault("kosumlar", {})[str(hedef["id"])] = yeni_kayit
            if yeni_kayit["durum"] == "ESKALASYON":
                _eskalasyon_yaz(yollar["eskalasyon"], hedef, yeni_kayit, _damga(simdi))
'''
G3_YENI = '''            icra_denendi = True
            try:
                icra_rc, icra_cikti = tur_kosucu(["--tur"])
            finally:
                _kilit_birak(kilit_yolu)
            icra_hal, icra_rc = icra_halini_coz(True, icra_rc, icra_cikti)
            # 🔴 B6: ATLANAN tur DENEME SAYMAZ. Onceden kosul `icra_rc == 0`
            # idi ve atlanan tur `0` dondugu icin deneme sayaci SAHTE bir
            # "basarili" kaydiyla kapaniyordu — kosmayan tur basarili sayilamaz.
            if icra_hal in ("KOSTU_BASARILI", "KOSTU_DUSTU"):
                kayit = (durum.get("kosumlar") or {}).get(str(hedef["id"])) or {}
                yeni_kayit = deneme_sonraki(kayit, icra_hal == "KOSTU_BASARILI")
                yeni_kayit["ad"] = hedef.get("ad", "")
                yeni_kayit["damga"] = _damga(simdi)
                durum.setdefault("kosumlar", {})[str(hedef["id"])] = yeni_kayit
                if yeni_kayit["durum"] == "ESKALASYON":
                    _eskalasyon_yaz(yollar["eskalasyon"], hedef, yeni_kayit, _damga(simdi))
'''


G4_ESKI = '''    elif not kuru and tetik == "DEFTER_DAGITIM":
        icra_rc, icra_cikti = tur_kosucu(["--tur-kapat"])
    elif not kuru and tetik == "GUNLUK_DEFTER":
        icra_rc, icra_cikti = tur_kosucu(["--tur"])
        durum["son_gunluk_tur"] = time.strftime("%Y-%m-%d", time.gmtime(simdi))

    if icra_rc is not None and icra_rc != 0:
        rc = max(rc, 1)
'''
G4_YENI = '''    elif not kuru and tetik == "DEFTER_DAGITIM":
        icra_denendi = True
        icra_rc, icra_cikti = tur_kosucu(["--tur-kapat"])
        icra_hal, icra_rc = icra_halini_coz(True, icra_rc, icra_cikti)
    elif not kuru and tetik == "GUNLUK_DEFTER":
        icra_denendi = True
        icra_rc, icra_cikti = tur_kosucu(["--tur"])
        icra_hal, icra_rc = icra_halini_coz(True, icra_rc, icra_cikti)
        durum["son_gunluk_tur"] = time.strftime("%Y-%m-%d", time.gmtime(simdi))

    # B6: KIRMIZI hukmu artik HAL'den okunur. ATLANDI turu (bugunku gibi) rc'yi
    # YUKSELTMEZ — ama artik SESSIZ YESIL de degildir: kalbe `icra_hal=ATLANDI`
    # yazilir ve "ardisik yesil tur" sayan hicbir tuketici onu SAYAMAZ.
    if icra_hal == "KOSTU_DUSTU":
        rc = max(rc, 1)
'''


G5_ESKI = '        "icra_rc": icra_rc,\n'
G5_YENI = ('        "icra_rc": icra_rc,        # B6: ATLANDI\'da None\n'
           '        "icra_hal": icra_hal,      # B6: uc hal UC deger\n'
           '        "icra_denendi": bool(icra_denendi),\n')


G6_ESKI = ('    return {"tetik": tetik, "llm_turu": llm_turu, "rc": rc, "kalp": kalp,\n'
           '            "satir": satir, "icra_rc": icra_rc, "icra_notu": icra_notu}\n')
G6_YENI = ('    return {"tetik": tetik, "llm_turu": llm_turu, "rc": rc, "kalp": kalp,\n'
           '            "satir": satir, "icra_rc": icra_rc, "icra_notu": icra_notu,\n'
           '            "icra_hal": icra_hal, "icra_denendi": bool(icra_denendi)}\n')


T1_ESKI = '    if kalp.get("icra_rc") is not None:\n'
T1_YENI = ('    # B6: soru "rc ne?" DEGIL, "gozcu bir tur ACTI MI?" — iki soru AYRI\n'
           '    # alandadir. `icra_rc` ATLANDI\'da None olur; bu kol ona bakarsa\n'
           '    # ucustaki turun ustune IKINCI tur acar. Eski kalplerde\n'
           '    # `icra_denendi` yoktur -> geriye donuk kol korunur.\n'
           '    if kalp.get("icra_denendi", kalp.get("icra_rc") is not None):\n')


# ---------------------------------------------------------------------------

def oku(yol):
    with open(yol, encoding="utf-8") as dosya:
        return dosya.read()


def yaz(yol, metin):
    with open(yol, "w", encoding="utf-8") as dosya:
        dosya.write(metin)


def yedekle(yol, damga):
    hedef = "%s.yedek-b6-%s" % (yol, damga)
    if not os.path.exists(hedef):
        shutil.copy2(yol, hedef)
    return hedef


def degistir(metin, eski, yeni):
    """Ankor TEKIL degilse yama UYGULANMAZ (fail-closed)."""
    if yeni in metin:
        return metin, False
    if metin.count(eski) != 1:
        return metin, None
    return metin.replace(eski, yeni, 1), True


DURUM_ADLARI = {True: "UYGULANDI", False: "ZATEN_VARDI", None: "ANKOR_YOK"}


def olculer():
    gz = oku(GOZCU)
    tt = oku(TETIK)
    tst = oku(TESTLER)
    return [
        ("G0 gozcu.py re importu", "\nimport re\n" in gz),
        ("G1 icra_halini_coz TEK KAYNAK", "def icra_halini_coz(" in gz),
        ("G2 icra_hal/icra_denendi ilklendi", 'icra_hal = "KOSULMADI"' in gz),
        # 🔴 Olcum KORUYUCU KOLA baglanir, `deneme_sonraki`nin ARGUMANINA
        # degil: B5 o argumani `kosum_hukmu == "TEMIZ"` yapiyor ve olcum
        # BAYATLIYOR (olculdu: b4-kanit/02b, G3 "YOK" dedi ama kol yerindeydi).
        ("G3 ATLANDI deneme SAYMIYOR",
         'if icra_hal in ("KOSTU_BASARILI", "KOSTU_DUSTU"):' in gz),
        ("G4 rc HAL'den okunuyor", 'if icra_hal == "KOSTU_DUSTU":' in gz),
        ("G5 kalpte icra_hal alani", '"icra_hal": icra_hal,' in gz),
        ("G6 donus sozlugunde icra_hal", '"icra_hal": icra_hal, "icra_denendi"' in gz),
        ("T1 tuketici icra_denendi'ye tasindi",
         'kalp.get("icra_denendi"' in tt),
        ("T2 eski icra_rc kolu KALMADI",
         'if kalp.get("icra_rc") is not None:' not in tt),
        ("T3 kabul bataryasi kuruldu", os.path.isfile(TEST_HEDEF)),
        ("T4 testler.py'ye kayitli (CAGRI YERI)", TEST_ADI in tst),
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
    print("B6_KURULU=%d/%d" % (kurulu, len(liste)))
    print("HUKUM=%s" % ("KURULU" if kurulu == len(liste) else "EKSIK"))
    return 0 if kurulu == len(liste) else 1


def uygula():
    damga = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    rapor = []

    gz = oku(GOZCU)
    yedek_gz = yedekle(GOZCU, damga)
    if "\nimport re\n" in gz:
        rapor.append(("G0 re importu", False))
    else:
        gz, d = degistir(gz, G0_ESKI, G0_YENI)
        rapor.append(("G0 re importu", d))
    if "def icra_halini_coz(" in gz:
        rapor.append(("G1 tek kaynak", False))
    elif gz.count(G1_ANKOR) == 1:
        gz = gz.replace(G1_ANKOR, G1_YENI + G1_ANKOR, 1)
        rapor.append(("G1 tek kaynak", True))
    else:
        rapor.append(("G1 tek kaynak", None))
    # 🔴 IDEMPOTENS BELIRTECI AYRI: `degistir`in "yeni metin zaten var mi"
    # testi, ARADAN baska bir yama (B5) satir sokunca YANILIR ve ayni blogu
    # IKINCI kez ekler. Her yamanin kendi belirteci olur (olculdu: b4-kanit/02b,
    # G2 "UYGULANDI" deyip mukerrer ilklendirme yazdi).
    for ad, eski, yeni, belirtec in (
            ("G2 ilklendirme", G2_ESKI, G2_YENI, 'icra_hal = "KOSULMADI"'),
            ("G3 ATLANDI deneme", G3_ESKI, G3_YENI,
             'if icra_hal in ("KOSTU_BASARILI", "KOSTU_DUSTU"):'),
            ("G4 rc HAL'den", G4_ESKI, G4_YENI, 'if icra_hal == "KOSTU_DUSTU":'),
            # Belirtecler AYIRT EDICI olmali: G5 ve G6 ayni alan adlarini
            # tasir, genel bir belirtec digerini yanlislikla "zaten var" yapar.
            ("G5 kalp alanlari", G5_ESKI, G5_YENI,
             '"icra_hal": icra_hal,      # B6'),
            ("G6 donus sozlugu", G6_ESKI, G6_YENI,
             '"icra_hal": icra_hal, "icra_denendi"'),
    ):
        if belirtec in gz:
            rapor.append((ad, False))
            continue
        gz, d = degistir(gz, eski, yeni)
        rapor.append((ad, d))
    yaz(GOZCU, gz)

    tt = oku(TETIK)
    yedek_tt = yedekle(TETIK, damga)
    tt, d = degistir(tt, T1_ESKI, T1_YENI)
    rapor.append(("T1 tuketici tasindi", d))
    yaz(TETIK, tt)

    if os.path.isfile(TEST_KAYNAK):
        shutil.copy2(TEST_KAYNAK, TEST_HEDEF)
        os.chmod(TEST_HEDEF, 0o755)
        rapor.append(("T3 batarya kuruldu", True))
    else:
        rapor.append(("T3 batarya kuruldu", None))

    tst = oku(TESTLER)
    yedek_tst = yedekle(TESTLER, damga)
    if TEST_ADI in tst:
        rapor.append(("T4 testler.py kaydi", False))
    else:
        ankor = '    "kilit-tatbikat.py",\n'
        if ankor in tst:
            tst = tst.replace(ankor, ankor + '    "%s",\n' % TEST_ADI, 1)
            yaz(TESTLER, tst)
            rapor.append(("T4 testler.py kaydi", True))
        else:
            rapor.append(("T4 testler.py kaydi", None))

    for ad, durum in rapor:
        print("YAMA=%-24s SONUC=%s" % (ad, DURUM_ADLARI[durum]))
    ankorsuz = sum(1 for _, d in rapor if d is None)
    for y in (yedek_gz, yedek_tt, yedek_tst):
        print("YEDEK=%s" % y)
    print("DAMGA=%s" % damga)
    print("ANKORSUZ=%d" % ankorsuz)
    print("HUKUM=%s" % ("UYGULANDI" if ankorsuz == 0 else "ANKOR_YOK"))
    return 0 if ankorsuz == 0 else 1


def geri_al(damga):
    n = 0
    for yol in HEDEFLER:
        yedek = "%s.yedek-b6-%s" % (yol, damga)
        if os.path.isfile(yedek):
            shutil.copy2(yedek, yol)
            n += 1
            print("GERI_ALINDI=%s" % yol)
    print("GERI_ALINAN=%d" % n)
    return 0 if n else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="B6 kurucu (icra hali uc deger)")
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
