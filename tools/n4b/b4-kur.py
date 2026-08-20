#!/usr/bin/env python3
"""B4 KURUCU — EMEKLI motora eskale edilmis kalem HICBIR kapida beklemesin.

PAKET: tools/paket-n4b-onarim-hatti-kalanlar.md, blok B4.
DUZLEM: ~/.claude/cron (git YOK) -> idempotent + yedekli.

NEDEN (olculdu): `nobet-geri-iz.json` icinde
    "K55": {"durum": "ESKALASYON", "motor": "deepseek-pro", "dagitim_sayisi": 3}
`deepseek-pro` 15 Agu 2026'da EMEKLI. K55 ona atanmis, rapor uretmemis, 3
denemede eskale olmus ve `eskale_kalemler` (nobet-kapi.py:320-327) onu bir daha
ASLA aday havuzuna sokmuyor.

O gerekce DOGRU (eskale kalem havuza girseydi dagitim sayaci her turda
sifirlanir ve eskalasyon bir daha ates almazdi) — ama bir yan etkisi
olculmemisti: 🔴 **eskalasyonu ureten motor ARTIK YOKSA, kalem insan kapisinda
degil HICBIR kapida beklemektedir.** Ayni sinif `nobet-kapi.py:68-73` yorumunda
zaten bir kez olculmustu ("bir kati emekli etmek o kata ATANMIS isleri
TASIMIYOR"). Bu IKINCI vaka -> tekil yama YASAK, SINIF cozumu.

CARE: geri izdeki bir kaydin `motor` alani `CANLI_ISCI_MOTORLARI` kumesinde
DEGILSE o eskalasyon BAYAT sayilir ve kalem CANLI kata GOC EDER
(`canli_kata_goc` zaten var). Goc BIR KEZ olur ve loga
`ESKALASYON_BAYAT kalem=... eski_motor=... yeni_kat=...` satiri duser.

🔴 GOC NELERE DOKUNMAZ:
  · `ustuste_onarimsiz` sayacina (B8 TEK KAPISI cagrilmaz — kabul-4),
  · `dagitim_sayisi`na (deneme gecmisi KAYBOLMAZ),
  · `gozcu-eskalasyon.md` dosyasina (KANITTIR, silinmez/temizlenmez — kabul-6).
Eski durum ve motor `eskalasyon_bayat` alaninda SAKLANIR.

🔴 FAIL-CLOSED (kabul-3): canli motor kumesi BOS donerse HICBIR SEY gocmez ve
hukum OLCULEMEDI olur — "hepsi bayat" diye toplu goc ETTIRILMEZ.

KOSUM:
    python3 tools/n4b/b4-kur.py            # yalniz OLCER
    python3 tools/n4b/b4-kur.py --uygula
    python3 tools/n4b/b4-kur.py --geri-al DAMGA
"""

import argparse
import os
import shutil
import sys
import time

CRON_KOKU = "/Users/okan/.claude/cron"
NOBET_KAPI = os.path.join(CRON_KOKU, "nobet-kapi.py")
TESTLER = os.path.join(CRON_KOKU, "testler.py")
TEST_ADI = "nobet-eskalasyon-bayat-test.py"
TEST_HEDEF = os.path.join(CRON_KOKU, TEST_ADI)
TEST_KAYNAK = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEST_ADI)

HEDEFLER = (NOBET_KAPI, TESTLER)


P1_ANKOR = "def eskale_kalemler(geri_iz):\n"

P1_YENI = '''# --- B4-ESKALASYON-BAYAT (20 Agu 2026, KraL-N4B) ---------------------------
# Eskalasyonu URETEN motor emekliyse, kalem insan kapisinda DEGIL HICBIR
# kapida bekler. Olculdu: K55 durum=ESKALASYON motor=deepseek-pro (emekli
# 15 Agu 2026), dagitim_sayisi=3, rapor YOK, 105+ turdur DAGITILAN=0.
BAYAT_GOC_DURUMU = "BAYAT_GOC"


def eskalasyon_bayat_mi(kayit, canli_motorlar=None):
    """B4: bu eskalasyon EMEKLI bir motordan mi dogdu?

    Fail-closed: canli kume BOS ise "bayat" DEMEYIZ (olcemedigimiz seyi
    bayat ilan etmek toplu goc demektir — kabul-3).
    Goc BIR KEZ olur: `eskalasyon_bayat` damgasi varsa bir daha ates almaz.
    Insan katlari (MIMAR/OKAN) emekli olmaz, onlar KAPSAM DISIDIR.
    """
    canli = CANLI_ISCI_MOTORLARI if canli_motorlar is None else tuple(canli_motorlar)
    if not canli:
        return False
    kayit = kayit or {}
    if kayit.get("durum") != "ESKALASYON":
        return False
    if kayit.get("eskalasyon_bayat"):
        return False
    motor = kayit.get("motor") or kayit.get("kat") or ""
    if motor in (KAT_MIMAR, KAT_OKAN):
        return False
    return motor not in canli


def bayat_eskalasyonlari_gocur(geri_iz, damga=None, canli_motorlar=None):
    """B4: BAYAT eskalasyonlari CANLI kata gocurur. Doner: (satirlar, sayi).

    🔴 Sayaca DOKUNMAZ (`tur_sayacini_kaydet` CAGRILMAZ), `dagitim_sayisi`
    AYNEN kalir, `gozcu-eskalasyon.md` dosyasina DOKUNULMAZ.
    Yeni durum BAYAT_GOC'tur: `eskale_kalemler` artik onu DISLAMAZ, kalem aday
    havuzuna BIR KEZ geri girer. Canli katta yeniden 3 kez duserse durum yine
    ESKALASYON olur ve motor CANLI oldugu icin bir daha GOCMEZ (sonsuz dongu YOK).
    """
    canli = CANLI_ISCI_MOTORLARI if canli_motorlar is None else tuple(canli_motorlar)
    if not canli:
        return ["ESKALASYON_BAYAT=OLCULEMEDI sebep=canli_motor_kumesi_bos"], 0
    damga = damga or _damga()
    satirlar = []
    sayi = 0
    for kalem_id, kayit in sorted((geri_iz.get("kalemler") or {}).items()):
        if not eskalasyon_bayat_mi(kayit, canli):
            continue
        eski_motor = kayit.get("motor") or kayit.get("kat") or "-"
        yeni_kat = canli_kata_goc(eski_motor) or canli[0]
        kayit["eskalasyon_bayat"] = {
            "eski_motor": eski_motor,
            "eski_durum": kayit.get("durum"),
            "damga": damga,
        }
        kayit["durum"] = BAYAT_GOC_DURUMU
        kayit["motor"] = yeni_kat
        kayit["kat"] = yeni_kat
        satirlar.append("ESKALASYON_BAYAT kalem=%s eski_motor=%s yeni_kat=%s"
                        % (kalem_id, eski_motor, yeni_kat))
        sayi += 1
    return satirlar, sayi


'''

P2_ESKI = '''    if not KAT_KAYNAGI_OLCULDU:
        satirlar = [
            "=== %s NOBET ONARIM BACAGI tur=%d%s ===" % (
                _damga(), tur_no, " KURU" if kuru else ""),
            "KAT_KAYNAGI=OLCULEMEDI sebep=%s" % KAT_KAYNAGI_SEBEBI,
            "HUKUM=KAT_KAYNAGI_OLCULEMEDI rc=2",
        ]
'''
P2_YENI = '''    # B4 kabul-3 (fail-closed): canli kume BOS ise hicbir sey gocmez ve tur
    # OLCULEMEDI ile kapanir. "Hepsi bayat" diye TOPLU goc ETTIRILMEZ.
    if not KAT_KAYNAGI_OLCULDU or not CANLI_ISCI_MOTORLARI:
        _kaynak_sebebi = KAT_KAYNAGI_SEBEBI or "canli_motor_kumesi_bos"
        satirlar = [
            "=== %s NOBET ONARIM BACAGI tur=%d%s ===" % (
                _damga(), tur_no, " KURU" if kuru else ""),
            "KAT_KAYNAGI=OLCULEMEDI sebep=%s" % _kaynak_sebebi,
            "HUKUM=KAT_KAYNAGI_OLCULEMEDI rc=2",
        ]
'''

P3_ESKI = '''    yeniden = set(olcum["dusen"])
    plan = fanout_plani(kalemler, geri_iz, FANOUT_TAVANI, yeniden=yeniden,
                        haric=set(olcum["kapanan"]))

    satirlar = []
    satirlar.append("=== %s NOBET ONARIM BACAGI tur=%d%s ===" % (
        _damga(), tur_no, " KURU" if kuru else ""))
'''
P3_YENI = '''    yeniden = set(olcum["dusen"])
    # 🔴 B4: BAYAT eskalasyonlar fanout'tan ONCE gocer — goc kalemi aday
    # havuzuna geri sokar, sonra sokulursa bu tur yine DAGITILAN=0 kalir.
    goc_satirlari, goc_sayisi = bayat_eskalasyonlari_gocur(geri_iz)
    plan = fanout_plani(kalemler, geri_iz, FANOUT_TAVANI, yeniden=yeniden,
                        haric=set(olcum["kapanan"]))

    satirlar = []
    satirlar.append("=== %s NOBET ONARIM BACAGI tur=%d%s ===" % (
        _damga(), tur_no, " KURU" if kuru else ""))
    satirlar.extend(goc_satirlari)
    satirlar.append("ESKALASYON_BAYAT_GOC=%d" % goc_sayisi)
'''


# ---------------------------------------------------------------------------

def oku(yol):
    with open(yol, encoding="utf-8") as dosya:
        return dosya.read()


def yaz(yol, metin):
    with open(yol, "w", encoding="utf-8") as dosya:
        dosya.write(metin)


def yedekle(yol, damga):
    hedef = "%s.yedek-b4-%s" % (yol, damga)
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


def _fonksiyon_govdesi(kaynak, ad):
    """Bir fonksiyonun kaynak govdesi (ast; metin bolme YOK)."""
    import ast as _ast
    try:
        agac = _ast.parse(kaynak)
    except SyntaxError:
        return ""
    for dugum in _ast.walk(agac):
        if isinstance(dugum, _ast.FunctionDef) and dugum.name == ad:
            return _ast.get_source_segment(kaynak, dugum) or ""
    return ""


def olculer():
    nk = oku(NOBET_KAPI)
    tst = oku(TESTLER)
    return [
        ("P1a eskalasyon_bayat_mi", "def eskalasyon_bayat_mi(" in nk),
        ("P1b bayat_eskalasyonlari_gocur",
         "def bayat_eskalasyonlari_gocur(" in nk),
        ("P2 fail-closed bos kume", "not CANLI_ISCI_MOTORLARI:" in nk),
        ("P3 fanout ONCESI cagri", "goc_satirlari, goc_sayisi" in nk),
        ("P3b goc sayisi raporlaniyor", 'ESKALASYON_BAYAT_GOC=%d' in nk),
        # Kabul-4: goc yolu sayaci DOGRUDAN sifirlamaz. Govde ast ile alinir
        # (metin bolme ile degil — komsu fonksiyon sizarsa olcum yalan olur).
        ("P4 goc yolu sayaca DOKUNMUYOR",
         "ustuste_onarimsiz" not in _fonksiyon_govdesi(
             nk, "bayat_eskalasyonlari_gocur")),
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
    print("B4_KURULU=%d/%d" % (kurulu, len(liste)))
    print("HUKUM=%s" % ("KURULU" if kurulu == len(liste) else "EKSIK"))
    return 0 if kurulu == len(liste) else 1


def uygula():
    damga = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    rapor = []
    nk = oku(NOBET_KAPI)
    yedek_nk = yedekle(NOBET_KAPI, damga)

    if "def eskalasyon_bayat_mi(" in nk:
        rapor.append(("P1 goc fonksiyonlari", False))
    elif nk.count(P1_ANKOR) == 1:
        nk = nk.replace(P1_ANKOR, P1_YENI + P1_ANKOR, 1)
        rapor.append(("P1 goc fonksiyonlari", True))
    else:
        rapor.append(("P1 goc fonksiyonlari", None))
    for ad, eski, yeni in (("P2 fail-closed", P2_ESKI, P2_YENI),
                           ("P3 cagri yeri", P3_ESKI, P3_YENI)):
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
        ankor = '    "kilit-tatbikat.py",\n'
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
        yedek = "%s.yedek-b4-%s" % (yol, damga)
        if os.path.isfile(yedek):
            shutil.copy2(yedek, yol)
            n += 1
            print("GERI_ALINDI=%s" % yol)
    print("GERI_ALINAN=%d" % n)
    return 0 if n else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="B4 kurucu (bayat eskalasyon gocu)")
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
