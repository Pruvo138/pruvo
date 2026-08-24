#!/usr/bin/env python3
"""K271 KURUCU — dagitim `eskalasyon_bayat` gocu damgasini DUSURMEZ; dusen
kalem yeniden kilitlenmez. Ayrica ZATEN DUSMUS damgalari KANITTAN geri yukler.

CHIP: KraL-K260KatSec.  DUZLEM: ~/.claude/cron (git YOK) -> idempotent + yedekli.

ARIZA (K260 kapanisinda kalem edildi, ayni gun KANADI):
  `kalem_dagit` geri-iz kaydini SIFIRDAN kurar (`kayit = {...}`). Hemen 3 satir
  altinda `merdiven` gecmisi ACIKCA tasinir ve yorumu tam da bu sinifi anlatir:
  "kayit YENIDEN kuruldugu icin merdiven gecmisi burada DUSERDI". Ama K260'in
  dagitim kararini BAGLADIGI `eskalasyon_bayat` damgasi TASINMIYOR.
  Sonuc: dagitilan kalem DUSERSE yapisal iz kaybolur, kalem metin kuraliyla
  yine MIMAR'a kilitlenir ve K260'in kapattigi ariza BIR TURDA geri gelir.

OLCULDU (gozcu.log, canli nobet turlariyla, tur tur):
  1595  KALEM K86  -> kimi [DAGITILACAK]      (K86 DAGITILABILIR kovasinda)
  1607  DAGITILDI K86  etiket=nobet-K86-t647  motor=kimi pid=40272
  1623  K260_KOVA_MIMAR_KATI_GERCEK=...,K86   (AYNI TURDAN SONRA kilitlendi)
  1637  KALEM K108 -> kimi [DAGITILACAK]
  1646  DAGITILDI K108 etiket=nobet-K108-t648 motor=kimi pid=45394
  1661  K260_KOVA_MIMAR_KATI_GERCEK=...,K108
  Bugun ikisi de `durum=BITMEYEN_TUR bayat=YOK dagitim=4` ve hattin
  dagitilabilir kuyrugu 0.

CARE — IKI PARCA:
  P1 (KOD, kalicidir): `kalem_dagit` damgayi `merdiven` ile AYNI bicimde tasir.
  R1 (VERI, TEK SEFERLIK): dusmus damgalar KANITTAN geri yuklenir.

🔴 R1 UYDURMAZ, TURETIR — ve her adimda FAIL-CLOSED:
  · Aday kume gozcu.log'dan TURER: `DAGITILDI <ID> ... motor=<CANLI>` satiri
    olan kalemler. Kod-disi bir liste ELLE YAZILMAZ.
  · Bir kalemin damgasiz halde DAGITILABILIR kovasina girmesi K260 kodunda
    IMKANSIZDIR; dolayisiyla "dagitildi + bugun damgasiz + metni MIMAR'a
    cikiyor" ucluu, damganin VAR OLUP DUSTUGUNUN kanitidir.
  · `eski_motor` TAHMIN EDILMEZ: ayni dosyada HAYATTA KALAN
    `eskalasyon_bayat.eski_motor` degerlerinden TUREYEN TEKIL deger kullanilir.
    Tekil degilse ya da hic yoksa -> OLCULEMEDI, kalem ATLANIR.
  · Damgasi OLAN kayda DOKUNULMAZ (idempotans). `dagitim_sayisi`, `merdiven`,
    `durum`, `motor` AYNEN kalir — sayac ELLE SIFIRLANMAZ.
  · Geri yuklenen damga `geri_yuklendi` alt kaydiyla ISARETLENIR: bu bir
    ONARIMDIR, "orijinal damga" gibi gosterilmez.

🔴 DOKUNULMAYANLAR: `tur_hukmu` · `ustuste_onarimsiz` · `IS_YOK` (K264 alani) ·
`kat_sec` metin kolu · emekli/canli motor kumeleri · kapi esikleri.

KOSUM:
    python3 tools/k271/k271-kur.py                 # yalniz OLCER
    python3 tools/k271/k271-kur.py --uygula        # P1 (kod yamasi)
    python3 tools/k271/k271-kur.py --geri-yukle    # R1 (veri onarimi)
    python3 tools/k271/k271-kur.py --geri-yukle --kuru
    python3 tools/k271/k271-kur.py --geri-al DAMGA
"""

import argparse
import ast
import json
import os
import shutil
import sys
import tempfile
import time

CRON_KOKU = "/Users/okan/.claude/cron"
NOBET_KAPI = os.path.join(CRON_KOKU, "nobet-kapi.py")
TESTLER = os.path.join(CRON_KOKU, "testler.py")
GERI_IZ = os.path.join(CRON_KOKU, "nobet-geri-iz.json")
GOZCU_LOG = os.path.join(CRON_KOKU, "gozcu.log")
DEFTER_YOLU = ("/Users/okan/.claude/projects/-Users-okan-dev-pruvo/memory/"
               "acik-kalemler.md")
TEST_ADI = "nobet-damga-tasima-test.py"
TEST_HEDEF = os.path.join(CRON_KOKU, TEST_ADI)
TEST_KAYNAK = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEST_ADI)
HEDEFLER = (NOBET_KAPI, TESTLER, GERI_IZ)
YEDEK_ONEKI = "yedek-k271"

# --- P1: damga `merdiven` ile AYNI bicimde tasinir --------------------------
P1_ESKI = '''    # 🔴 (c) OLCULMUS TASINIR: kayit YENIDEN kuruldugu icin merdiven gecmisi
    # burada DUSERDI; ust kat sifirdan olcmesin diye ACIKCA tasinir.
    if onceki.get("merdiven"):
        kayit["merdiven"] = onceki["merdiven"]
'''

P1_YENI = '''    # 🔴 (c) OLCULMUS TASINIR: kayit YENIDEN kuruldugu icin merdiven gecmisi
    # burada DUSERDI; ust kat sifirdan olcmesin diye ACIKCA tasinir.
    if onceki.get("merdiven"):
        kayit["merdiven"] = onceki["merdiven"]
    # 🔴 K271 — AYNI SINIFIN IKINCI VAKASI, caresi bir ustteki satirdaydi.
    # `eskalasyon_bayat`, B4 gocunun YAPISAL izidir ve K260 dagitim kararini
    # ONA bagladi (`_emekli_kattan_gocmus`). Kayit yeniden kuruldugu icin
    # burada DUSUYORDU; dagitilan kalem duserse iz kaybolur ve kalem metin
    # kuraliyla YINE MIMAR'a kilitlenirdi. Olculdu (gozcu.log): K86 t647'de,
    # K108 t648'de DAGITILABILIR iken dagitildi, AYNI turdan sonra ikisi de
    # MIMAR_KATI_GERCEK'e dondu ve hattin dagitilabilir kuyrugu 0'a indi.
    # 🔴 SONSUZ DONGU YOK: damganin KORUNMASI gocu TEKRARLATMAZ — tersine,
    # `eskalasyon_bayat_mi` damgali kaydi ELER (goc BIR KEZ olur).
    if onceki.get("eskalasyon_bayat"):
        kayit["eskalasyon_bayat"] = onceki["eskalasyon_bayat"]
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


def _cagri_govdesinde(kaynak, fonksiyon, aranan):
    """`fonksiyon` govdesinde `aranan` adli bir alan atamasi/erisimi var mi?
    (ast — docstring'e takilmaz, komsu fonksiyon SIZMAZ.)"""
    try:
        agac = ast.parse(kaynak)
    except SyntaxError:
        return False
    for dugum in ast.walk(agac):
        if not (isinstance(dugum, ast.FunctionDef) and dugum.name == fonksiyon):
            continue
        for alt in ast.walk(dugum):
            if isinstance(alt, ast.Constant) and alt.value == aranan:
                return True
        return False
    return False


def olculer():
    nk = oku(NOBET_KAPI)
    return [
        ("P1 damga kalem_dagit'te tasiniyor",
         _cagri_govdesinde(nk, "kalem_dagit", "eskalasyon_bayat")),
        ("P1b tasima satiri birebir",
         'kayit["eskalasyon_bayat"] = onceki["eskalasyon_bayat"]' in nk),
        # Kabul-2: goc ELEME kolu YERINDE (damga korunsa da goc tekrarlamaz).
        ("P2 goc eleme kolu duruyor",
         'if kayit.get("eskalasyon_bayat"):' in nk),
        ("T1 batarya kuruldu", os.path.isfile(TEST_HEDEF)),
        ("T2 testler.py'ye kayitli (CAGRI YERI)", TEST_ADI in oku(TESTLER)),
    ]


def olc():
    try:
        liste = olculer()
    except OSError as hata:
        print("HUKUM=OLCULEMEDI sebep=%s" % hata)
        return 2
    kurulu = sum(1 for _, v in liste if v)
    for ad, var in liste:
        print("YAMA=%-42s DURUM=%s" % (ad, "VAR" if var else "YOK"))
    print("K271_KURULU=%d/%d" % (kurulu, len(liste)))
    print("HUKUM=%s" % ("KURULU" if kurulu == len(liste) else "EKSIK"))
    return 0 if kurulu == len(liste) else 1


def uygula():
    damga = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    nk = oku(NOBET_KAPI)
    yedek_nk = yedekle(NOBET_KAPI, damga)
    if P1_YENI in nk:
        durum = "ZATEN_VARDI"
    elif nk.count(P1_ESKI) != 1:
        durum = "ANKOR_YOK(sayi=%d)" % nk.count(P1_ESKI)
    else:
        nk = nk.replace(P1_ESKI, P1_YENI, 1)
        yaz(NOBET_KAPI, nk)
        durum = "UYGULANDI"
    print("YAMA=P1 damga tasima          SONUC=%s" % durum)

    if os.path.isfile(TEST_KAYNAK):
        shutil.copy2(TEST_KAYNAK, TEST_HEDEF)
        os.chmod(TEST_HEDEF, 0o755)
        print("YAMA=T1 batarya kuruldu       SONUC=UYGULANDI")
    else:
        print("YAMA=T1 batarya kuruldu       SONUC=ANKOR_YOK")

    tst = oku(TESTLER)
    yedek_tst = yedekle(TESTLER, damga)
    if TEST_ADI in tst:
        print("YAMA=T2 testler.py kaydi      SONUC=ZATEN_VARDI")
    else:
        ankor = '    "nobet-kat-kovasi-test.py",\n'
        if ankor in tst:
            yaz(TESTLER, tst.replace(ankor, ankor + '    "%s",\n' % TEST_ADI, 1))
            print("YAMA=T2 testler.py kaydi      SONUC=UYGULANDI")
        else:
            print("YAMA=T2 testler.py kaydi      SONUC=ANKOR_YOK")

    print("YEDEK=%s" % yedek_nk)
    print("YEDEK=%s" % yedek_tst)
    print("DAMGA=%s" % damga)
    print("HUKUM=%s" % ("UYGULANDI" if "ANKOR_YOK" not in durum else "ANKOR_YOK"))
    print("--- KURULUM SONRASI OLCUM ---")
    olc()
    return 0 if "ANKOR_YOK" not in durum else 1


# ===========================================================================
# R1 — DUSMUS DAMGAYI KANITTAN GERI YUKLE (TEK SEFERLIK, FAIL-CLOSED)
# ===========================================================================

def _log_dagitilanlar(canli):
    """gozcu.log'dan `DAGITILDI <ID> ... motor=<CANLI>` kalemlerini TURETIR."""
    adaylar = {}
    try:
        with open(GOZCU_LOG, encoding="utf-8", errors="replace") as d:
            for satir in d:
                duz = satir.strip()
                if not duz.startswith("DAGITILDI "):
                    continue
                parca = duz.split()
                if len(parca) < 2:
                    continue
                kimlik = parca[1]
                motor = ""
                for p in parca[2:]:
                    if p.startswith("motor="):
                        motor = p[len("motor="):]
                if motor in canli:
                    adaylar.setdefault(kimlik, duz)
    except OSError as hata:
        print("GOZCU_LOG=OKUNAMADI sebep=%s" % hata)
        return {}
    return adaylar


def _hayatta_kalan_eski_motor(geri_iz, emekli):
    """`eski_motor` TAHMIN EDILMEZ: dosyada HAYATTA KALAN damgalardan TUREN
    TEKIL deger kullanilir. Tekil degilse (0 ya da >1) -> None (fail-closed)."""
    degerler = set()
    for kayit in (geri_iz.get("kalemler") or {}).values():
        deger = (kayit.get("eskalasyon_bayat") or {}).get("eski_motor")
        if deger in emekli:
            degerler.add(deger)
    return degerler.pop() if len(degerler) == 1 else None


def geri_yukle(kuru=False):
    sys.path.insert(0, CRON_KOKU)
    import importlib.util
    spec = importlib.util.spec_from_file_location("_k271_nk", NOBET_KAPI)
    nk = importlib.util.module_from_spec(spec)
    sys.modules["_k271_nk"] = nk
    spec.loader.exec_module(nk)

    canli = tuple(nk.CANLI_ISCI_MOTORLARI)
    emekli = tuple(nk.EMEKLI_ISCI_MOTORLARI)
    if not canli or not emekli:
        print("HUKUM=OLCULEMEDI sebep=motor_kumesi_bos")
        return 2

    with open(GERI_IZ, encoding="utf-8") as d:
        geri_iz = json.load(d)
    with open(DEFTER_YOLU, encoding="utf-8") as d:
        kalemler = {k["id"]: k for k in nk.defter_ayristir(d.read())}

    eski_motor = _hayatta_kalan_eski_motor(geri_iz, emekli)
    print("TUREYEN_ESKI_MOTOR=%s" % (eski_motor or "TEKIL_DEGIL"))
    if eski_motor is None:
        print("HUKUM=OLCULEMEDI sebep=eski_motor_turetilemedi")
        return 2

    adaylar = _log_dagitilanlar(canli)
    print("LOG_ADAYI=%d KALEM=%s"
          % (len(adaylar), ",".join(sorted(adaylar)) or "-"))

    damga = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    onarilan, atlanan = [], []
    for kimlik in sorted(adaylar):
        kayit = (geri_iz.get("kalemler") or {}).get(kimlik)
        kalem = kalemler.get(kimlik)
        if kayit is None:
            atlanan.append((kimlik, "geri-iz kaydi YOK"))
            continue
        if kayit.get("eskalasyon_bayat"):
            atlanan.append((kimlik, "damga ZATEN VAR (idempotans)"))
            continue
        if kalem is None:
            atlanan.append((kimlik, "defterde ACIK degil"))
            continue
        # Damgasiz halde DAGITILABILIR kovasina girmek IMKANSIZ oldugu icin,
        # metni MIMAR'a cikan bir kalemin dagitilmis olmasi damganin VAR OLUP
        # DUSTUGUNUN kanitidir. Metni zaten canli kata cikiyorsa damga GEREKMEZ.
        if nk.kat_sec(kalem) != nk.KAT_MIMAR:
            atlanan.append((kimlik, "metni zaten CANLI kata cikiyor"))
            continue
        if (kayit.get("motor") or kayit.get("kat")) not in canli:
            atlanan.append((kimlik, "bugunku motor CANLI degil"))
            continue
        onarilan.append(kimlik)
        if not kuru:
            kayit["eskalasyon_bayat"] = {
                "eski_motor": eski_motor,
                "eski_durum": "ESKALASYON",
                "damga": damga,
                "geri_yuklendi": {
                    "kalem": "K271",
                    "sebep": "kalem_dagit kaydi yeniden kururken damgayi dusurdu",
                    "kanit": adaylar[kimlik],
                    "kanit_kaynagi": GOZCU_LOG,
                    "eski_motor_kaynagi": "hayatta kalan damgalardan TUREYEN tekil deger",
                },
            }

    for kimlik in onarilan:
        print("GERI_YUKLENDI %s eski_motor=%s kanit=%s"
              % (kimlik, eski_motor, adaylar[kimlik][:110]))
    for kimlik, sebep in atlanan:
        print("ATLANDI %s sebep=%s" % (kimlik, sebep))

    if kuru:
        print("KURU=EVET yazma YAPILMADI")
    elif onarilan:
        yedek = yedekle(GERI_IZ, damga)
        print("YEDEK=%s" % yedek)
        fd, gecici = tempfile.mkstemp(dir=CRON_KOKU, prefix=".nobet-geri-iz.")
        with os.fdopen(fd, "w", encoding="utf-8") as d:
            json.dump(geri_iz, d, ensure_ascii=False, indent=2)
        os.replace(gecici, GERI_IZ)
        print("YAZILDI=%s (atomik)" % GERI_IZ)

    print("GERI_YUKLENEN=%d ATLANAN=%d" % (len(onarilan), len(atlanan)))
    print("HUKUM=%s" % ("ONARILDI" if onarilan else "ONARILACAK_KALEM_YOK"))
    return 0


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
    ap = argparse.ArgumentParser(description="K271 kurucu (damga tasima)")
    ap.add_argument("--uygula", action="store_true")
    ap.add_argument("--geri-yukle", action="store_true")
    ap.add_argument("--kuru", action="store_true")
    ap.add_argument("--geri-al", metavar="DAMGA")
    args = ap.parse_args(argv)
    if args.geri_al:
        return geri_al(args.geri_al)
    if args.geri_yukle:
        return geri_yukle(kuru=args.kuru)
    if args.uygula:
        return uygula()
    return olc()


if __name__ == "__main__":
    sys.exit(main())
