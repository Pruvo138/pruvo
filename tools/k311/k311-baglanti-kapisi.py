#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K311 SINIF KAPISI — "beyan edilen HUKUM bir TUKETICIYE baglanir".

## NEDEN BU KAPI VAR (ucuncu tekrar)

Bu evde AYNI sinif UC KEZ dogdu:
  · 14 Agu 2026 `ci-nobeti.sh` basligi: "son 7 gunde 167 tur kostu,
    ONARIM_YAPAN=0, hepsi rc=0 + yesil rapor verdi." -> H1-H7 kapilari eklendi.
  · 19 Agu 2026 N1: gozcu DOGRU karari uretiyordu, `ci-nobeti.sh` o karari
    OKUMUYORDU. -> `nobet-tetik.py` (eksik kablo) yazildi.
  · 26 Agu 2026 K311: `kosum_hukmu` DURUSTCE hesaplaniyor, kalbe yaziliyor —
    ve rc yolunda TEK TUKETICISI YOK. 44 uretmeyen tur rc=0 ile kapandi;
    `gozcu-eskalasyon.md`ye 42 satir yazildi, TEK BIR OKUYUCUSU YOKTU.

Uc vakanin da koku AYNI: **hukum uretildi, tuketici kurulmadi.**
[[ucuncu-tekrar-sinif-kapisi]] geregi ucuncu tekrarda TEKIL YAMA YASAKTIR;
tedavi edilecek sey semptom degil SINIFTIR. Bu kapi o sinifi olcer.

## KAPI NEYI OLCER

EKSEN 1 — KALP ALANI SINIFLAMASI. `gozcu.py`nin kalbe yazdigi HER alan
  ya `HUKUM` (bir karari degistirmeli: canli tuketicisi ZORUNLU)
  ya `TELEMETRI` (yalniz insana/log'a bakar: tuketici aranmaz)
  olarak burada SINIFLANIR. Siniflanmamis YENI alan = KIRMIZI. Yani yarin
  kalbe yeni bir hukum alani eklenirse, kablosu kurulana kadar kapi yanar.
  🔴 Fail-closed yon: varsayilan "TELEMETRI" DEGIL, "SINIFLANMAMIS"tir.

EKSEN 2 — TUKETICI SAYIMI. Her `HUKUM` alani icin, URETIM dosyalarinda
  (yedek/test/mutasyon HARIC) alanin YAZILDIGI yer disinda en az bir OKUMA
  bulunmali. Sayi BASILIR ([[aracin-teshis-cumlesi-olcum-degil]]).

EKSEN 3 — YAZ-ONLY DURUM DOSYALARI. Uretimin YAZDIGI durum dosyalarinin
  bir URETIM OKUYUCUSU olmali. `gozcu-eskalasyon.md` tam olarak bu eksenden
  kirmizi yanardi (42 satir, 0 okuyucu).

## KOSUM

    python3 tools/k311/k311-baglanti-kapisi.py            # olcer, rc=1 = KIRMIZI
    python3 tools/k311/k311-baglanti-kapisi.py --kendini-test
"""

import argparse
import os
import re
import sys

CRON_KOKU = "/Users/okan/.claude/cron"
GOZCU = os.path.join(CRON_KOKU, "gozcu.py")

# URETIM dosyalari — kapi TUKETICIYI yalniz burada arar. Yedek/test/mutasyon
# dosyalari BILEREK disaridadir: bir alanin tek okuyucusu kendi testi ise o
# alan URETIMDE OLU demektir ([[kapinin-menzili-cagri-yeridir]] madde 2).
URETIM_DOSYALARI = (
    os.path.join(CRON_KOKU, "gozcu.py"),
    os.path.join(CRON_KOKU, "nobet-tetik.py"),
    os.path.join(CRON_KOKU, "nobet-kapi.py"),
    os.path.join(CRON_KOKU, "nobet_merdiven.py"),
    os.path.join(CRON_KOKU, "nobet_devir.py"),
)

# --- EKSEN 1: kalp alanlarinin SINIFLAMASI --------------------------------
# HUKUM     = bir karari (rc / tur acma / dagitim / eskalasyon) degistirmeli.
# TELEMETRI = yalniz raporlanir; tuketici ARANMAZ (ama BEYAN zorunludur).
ALAN_SINIFI = {
    # --- HUKUM ---
    "rc": "HUKUM",
    "icra_denendi": "HUKUM",        # nobet-tetik 3. basamak
    "icra_hal": "HUKUM",            # gozcu rc kolu + uretken_mi
    "kosum_hukmu": "HUKUM",         # K311: uretken_mi -> rc  (ONCE OLUYDU)
    "uretken": "HUKUM",             # K311 YUZ A
    "uretken_sebep": "HUKUM",       # K311: sebep karar satirina TASINIR
    "eskalasyon_acik": "HUKUM",     # K311 YUZ B  (ONCE OLUYDU)
    "ci_olculdu": "HUKUM",
    "defter_olculdu": "HUKUM",
    "tetik": "HUKUM",
    "hedef_run": "HUKUM",
    "gunluk_gerekli": "HUKUM",
    "epok": "HUKUM",                # bayatlik yuklemi
    # --- TELEMETRI ---
    "damga": "TELEMETRI",
    "sahip": "TELEMETRI",
    "sahip_sebep": "TELEMETRI",
    "llm_turu": "TELEMETRI",
    "yeni_kirmizi": "TELEMETRI",
    "kirmizi_toplam": "TELEMETRI",
    "dagitilabilir": "TELEMETRI",
    "kat_mimar": "TELEMETRI",
    "kat_okan": "TELEMETRI",
    "kat_isci": "TELEMETRI",
    "artik_silinen": "TELEMETRI",
    "taban_alinan": "TELEMETRI",
    "ci_sebep": "TELEMETRI",
    "icra_rc": "TELEMETRI",         # hal alani hukmu tasir; rc yalniz teshis
    "n2_devir": "TELEMETRI",
    # `kuru` gozcunun KENDI kosum kipidir ve etkiledigi karar kalp YAZILMADAN
    # ONCE verilir (gozcu.py `if not kuru:` kollari). Kalptekі kopya bir KAYIT
    # olduguna gore tuketici aranmaz — ama BEYAN zorunlu oldugu icin burada
    # ADIYLA durur. 🔴 Sessizce atlanmasi YASAK: siniflanmamis alan KIRMIZIDIR.
    "kuru": "TELEMETRI",
}

# --- EKSEN 3: uretimin YAZDIGI durum dosyalari ----------------------------
# (dosya, o dosyayi OKUYAN uretim kodunda aranacak desen)
DURUM_DOSYALARI = (
    ("gozcu-eskalasyon.md", r"eskalasyon_acik_say|ESKALASYON_YOLU\s*\)?\s*,?\s*['\"]r"),
    ("gozcu-kalp.json", r"kalp_oku|KALP_YOLU"),
)


def oku(yol):
    try:
        with open(yol, encoding="utf-8") as dosya:
            return dosya.read()
    except OSError:
        return None


def kalp_alanlarini_cikar(kaynak):
    """gozcu.py'deki `kalp = {` sozluk literalinin ANAHTARLARINI cikarir.

    Elle tutulan bir liste DEGIL — kaynaktan turer; yoksa yeni alan eklenince
    kapi kor kalir ([[emir-canliligi-kurulu-kopyadan-olculur]]).
    """
    bas = kaynak.find("\n    kalp = {\n")
    if bas < 0:
        return None
    son = kaynak.find("\n    }\n", bas)
    if son < 0:
        return None
    blok = kaynak[bas:son]
    return re.findall(r'^\s*"([a-z0-9_]+)":', blok, re.MULTILINE)


def tuketici_say(alan, kalp_blok_araligi, kaynaklar):
    """Alanin URETIMDE kac kez OKUNDUGUNU sayar.

    Yazma yeri (`"alan": ...` kalp literali) ELENIR; yalniz `get("alan")` /
    `["alan"]` bicimindeki OKUMALAR sayilir.
    """
    desen = re.compile(r'(?:\.get\(\s*["\']%s["\']|\[\s*["\']%s["\']\s*\])'
                       % (re.escape(alan), re.escape(alan)))
    toplam = 0
    yerler = []
    for yol, metin in kaynaklar.items():
        if metin is None:
            continue
        for n, satir in enumerate(metin.split("\n"), 1):
            if yol == GOZCU and kalp_blok_araligi and \
               kalp_blok_araligi[0] <= n <= kalp_blok_araligi[1]:
                continue          # kalp literali = YAZMA yeri, okuma degil
            if desen.search(satir):
                toplam += 1
                yerler.append("%s:%d" % (os.path.basename(yol), n))
    return toplam, yerler


def kalp_blok_satirlari(kaynak):
    satirlar = kaynak.split("\n")
    bas = son = None
    for n, s in enumerate(satirlar, 1):
        if s == "    kalp = {":
            bas = n
        elif bas is not None and s == "    }":
            son = n
            break
    return (bas, son) if bas and son else None


def olc():
    kaynaklar = {yol: oku(yol) for yol in URETIM_DOSYALARI}
    gozcu_metin = kaynaklar.get(GOZCU)
    satirlar = []
    kirmizi = 0

    if gozcu_metin is None:
        print("EKSEN1 KIRMIZI: gozcu.py OKUNAMADI")
        return 1

    alanlar = kalp_alanlarini_cikar(gozcu_metin)
    if not alanlar:
        print("EKSEN1 KIRMIZI: kalp literali AYRISTIRILAMADI "
              "(kapi kor kalamaz — fail-closed)")
        return 1
    aralik = kalp_blok_satirlari(gozcu_metin)

    # --- EKSEN 1 ---
    print("=== EKSEN 1: KALP ALANI SINIFLAMASI ===")
    siniflanmamis = [a for a in alanlar if a not in ALAN_SINIFI]
    print("ALAN_TOPLAM=%d SINIFLANMAMIS=%d" % (len(alanlar), len(siniflanmamis)))
    for a in siniflanmamis:
        print("  🔴 SINIFLANMAMIS ALAN=%s — HUKUM mu TELEMETRI mi? "
              "k311-baglanti-kapisi.py:ALAN_SINIFI'na YAZ." % a)
        kirmizi += 1
    # Ters yon: siniflamada VAR ama kalpte YOK olan alan = BAYAT siniflama.
    bayat = [a for a in ALAN_SINIFI if a not in alanlar]
    print("BAYAT_SINIFLAMA=%d" % len(bayat))
    for a in bayat:
        print("  🔴 BAYAT SINIFLAMA ALAN=%s — kalpte YOK." % a)
        kirmizi += 1

    # --- EKSEN 2 ---
    print("")
    print("=== EKSEN 2: HUKUM ALANLARININ CANLI TUKETICISI ===")
    hukum_alanlari = [a for a in alanlar if ALAN_SINIFI.get(a) == "HUKUM"]
    olu = 0
    for a in hukum_alanlari:
        n, yerler = tuketici_say(a, aralik, kaynaklar)
        damga = "OK" if n > 0 else "🔴 OLU"
        print("  %-18s TUKETICI=%d %s  %s"
              % (a, n, damga, ",".join(yerler[:4]) or "-"))
        if n == 0:
            olu += 1
            kirmizi += 1
    print("HUKUM_ALANI=%d OLU_ALAN=%d" % (len(hukum_alanlari), olu))

    # --- EKSEN 3 ---
    print("")
    print("=== EKSEN 3: YAZ-ONLY DURUM DOSYALARI ===")
    birlesik = "\n".join(m for m in kaynaklar.values() if m)
    for ad, desen in DURUM_DOSYALARI:
        var = re.search(desen, birlesik) is not None
        print("  %-24s OKUYUCU=%s" % (ad, "VAR" if var else "🔴 YOK"))
        if not var:
            kirmizi += 1

    print("")
    print("K311_BAGLANTI KIRMIZI=%d" % kirmizi)
    return 1 if kirmizi else 0


# ---------------------------------------------------------------------------
# Kendini test: kapinin KENDISI dusebiliyor mu? (mutant, fikstur uzerinde)
# ---------------------------------------------------------------------------

_FIKSTUR = '''
    kalp = {
        "damga": _damga(simdi),
        "rc": rc,
        "yeni_alan_hukum": 1,
    }
'''


def kendini_test():
    T = []

    def vaka(ad, gercek, beklenen):
        T.append((ad, gercek == beklenen, gercek, beklenen))

    # 1. Ayristirici kalp anahtarlarini GERCEKTEN cikariyor mu?
    vaka("A1 fikstur alanlari", kalp_alanlarini_cikar(_FIKSTUR),
         ["damga", "rc", "yeni_alan_hukum"])
    # 2. Bozuk kaynak -> None (fail-closed girdisi)
    vaka("A2 kalp literali yoksa None", kalp_alanlarini_cikar("x = 1\n"), None)
    # 3. Tuketici sayaci OKUMAYI sayar, YAZMAYI saymaz
    sahte = {"/x/uretim.py": 'kalp = {"a": 1}\nif veri.get("a"):\n    pass\n'}
    n, _ = tuketici_say("a", None, sahte)
    vaka("A3 get() okumasi sayilir", n, 1)
    n2, _ = tuketici_say("damga", None, sahte)
    vaka("A4 okunmayan alan 0", n2, 0)
    n3, _ = tuketici_say("a", None, {"/x/u.py": 'v["a"] = 1\nx = v["a"]\n'})
    vaka("A5 kose parantez okumasi sayilir", n3, 2)
    # 4. Siniflama sozlugu HUKUM/TELEMETRI disinda deger TASIMAZ
    vaka("A6 siniflama degerleri kapali kume",
         sorted(set(ALAN_SINIFI.values())), ["HUKUM", "TELEMETRI"])

    dusen = [t for t in T if not t[1]]
    for ad, _, gercek, beklenen in dusen:
        print("KIRIK %s: beklenen=%r gercek=%r" % (ad, beklenen, gercek))
    print("KENDINI_TEST VAKA=%d DUSEN=%d" % (len(T), len(dusen)))
    return 1 if dusen else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="K311 baglanti kapisi")
    ap.add_argument("--kendini-test", action="store_true")
    args = ap.parse_args(argv)
    if args.kendini_test:
        return kendini_test()
    return olc()


if __name__ == "__main__":
    sys.exit(main())
