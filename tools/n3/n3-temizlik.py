#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N3 TEMIZLIK — ureten temizler (Okan disk kurali, USTUN).

Once/sonra `du` ile OLCER, siler, tekrar olcer. Temizliksiz spec EKSIK.
KALICI birakilanlar (gerekcesiyle):
  - ~/.claude/cron/n3-tatbikat-test.py   : kayitli batarya kosucusu
  - ~/.claude/cron/n3-okan-cevap.json    : T6'nin tek kaniti
  - ~/.claude/cron/testler.py.yedek-n3-* : geri-al yolunun EN YENI yedegi
  - depo tools/n3/*                      : is urunu (commit'lenir)

  KOSUM: python3 tools/n3/n3-temizlik.py --uygula --rapor /tam/yol.txt
"""

import argparse
import os
import shutil
import subprocess
import sys

CRON_KOKU = "/Users/okan/.claude/cron"
AGAC = "/Users/okan/dev/pruvo/.claude/worktrees/elegant-engelbart-b3b4c4"

OLCULEN = (CRON_KOKU, AGAC)


def _du_kb(yol):
    try:
        proc = subprocess.run(["du", "-sk", yol], capture_output=True,
                              text=True, timeout=300)
        return int((proc.stdout or "0").split()[0])
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def olc(etiket):
    olcum = {}
    for yol in OLCULEN:
        kb = _du_kb(yol)
        olcum[yol] = kb
        print("DU %s %s = %s KB" % (etiket, yol, kb))
    return olcum


def hedefleri_topla():
    hedefler = []

    # 1) Kanit dizini (rapor + pencere) — okundu, kalici degil.
    kanit = os.path.join(AGAC, ".n3-kanit")
    if os.path.isdir(kanit):
        hedefler.append(("dizin", kanit, "kanit dizini (raporlar okundu)"))

    # 2) Isci spec'leri — `.gitignore:533 SPEC-*.md` geregi IZLENMEZ, yani
    # depo politikasi onlari GECICI sayar. Yeniden uretim yolu kaybolmaz:
    # her `.py` kendi KOSUM: satirini docstring'inde tasir.
    n3_dizini = os.path.dirname(os.path.abspath(__file__))
    for ad in sorted(os.listdir(n3_dizini)):
        if ad.startswith("SPEC-") and ad.endswith(".md"):
            hedefler.append(("dosya", os.path.join(n3_dizini, ad),
                             "izlenmeyen isci spec'i (gitignore:533)"))

    # 2b) Tek kullanimlik betikler (izlenmiyor, islerini gordular).
    for ad in ("n3-kutu-blok.py", "k262-ac.py"):
        yol = os.path.join(n3_dizini, ad)
        if os.path.isfile(yol):
            hedefler.append(("dosya", yol, "tek kullanimlik betik"))

    # 3) Bu turun isci cikti loglari.
    cikti = os.path.join(CRON_KOKU, "isci-tur-cikti")
    if os.path.isdir(cikti):
        for ad in sorted(os.listdir(cikti)):
            if ad.startswith(("kabul-n3-",)):
                hedefler.append(("dosya", os.path.join(cikti, ad),
                                 "bu turun isci tur logu"))

    # 3) Eski n3 yedekleri — EN YENISI KALIR (geri-al yolu sağlam kalsin).
    yedekler = sorted(a for a in os.listdir(CRON_KOKU)
                      if a.startswith("testler.py.yedek-n3-"))
    for ad in yedekler[:-1]:
        hedefler.append(("dosya", os.path.join(CRON_KOKU, ad),
                         "mukerrer n3 yedegi (en yenisi KALIR)"))

    # 4) Modul yuklemenin birakabilecegi pyc artiklari.
    pycache = os.path.join(CRON_KOKU, "__pycache__")
    if os.path.isdir(pycache):
        for ad in sorted(os.listdir(pycache)):
            if ad.startswith(("n3_", "n3-")):
                hedefler.append(("dosya", os.path.join(pycache, ad),
                                 "n3 modul pyc artigi"))
    return hedefler


def main(argv=None):
    ayrist = argparse.ArgumentParser()
    ayrist.add_argument("--uygula", action="store_true")
    ayrist.add_argument("--rapor", required=True)
    args = ayrist.parse_args(argv)

    rapor = open(args.rapor, "w", encoding="utf-8")

    class _Cift:
        def write(self, metin):
            sys.__stdout__.write(metin)
            rapor.write(metin)

        def flush(self):
            sys.__stdout__.flush()
            rapor.flush()

    sys.stdout = _Cift()

    once = olc("ONCE")
    hedefler = hedefleri_topla()
    print("HEDEF_SAYISI=%d" % len(hedefler))
    silinen = 0
    for tur, yol, sebep in hedefler:
        print("  HEDEF=%s (%s) %s" % (yol, tur, sebep))
        if not args.uygula:
            continue
        try:
            if tur == "dizin":
                shutil.rmtree(yol, ignore_errors=True)
            else:
                os.remove(yol)
            silinen += 1
        except OSError as hata:
            print("  SILINEMEDI=%s (%s)" % (yol, hata))
    print("SILINEN=%d" % silinen)
    sonra = olc("SONRA")

    for yol in OLCULEN:
        a, b = once.get(yol), sonra.get(yol)
        if a is None or b is None:
            print("FARK %s = OLCULEMEDI" % yol)
        else:
            print("FARK %s = %d KB (%d -> %d)" % (yol, b - a, a, b))

    # 🔴 Kalicilarin YERINDE oldugunu ayrica dogrula.
    kaliciler = (
        os.path.join(CRON_KOKU, "n3-tatbikat-test.py"),
        os.path.join(CRON_KOKU, "n3-okan-cevap.json"),
    )
    eksik = [y for y in kaliciler if not os.path.isfile(y)]
    for yol in kaliciler:
        print("KALICI=%s VAR=%s" % (yol, os.path.isfile(yol)))
    yedek_kaldi = [a for a in os.listdir(CRON_KOKU)
                   if a.startswith("testler.py.yedek-n3-")]
    print("GERI_AL_YEDEGI_SAYISI=%d %s" % (len(yedek_kaldi), yedek_kaldi))
    if not yedek_kaldi:
        eksik.append("geri-al yedegi")

    rc = 0 if not eksik else 1
    if eksik:
        print("KALICI_EKSIK=%s" % eksik)
    print("KABUL=%s" % ("GECTI" if rc == 0 else "KALDI"))
    sys.stdout = sys.__stdout__
    rapor.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
