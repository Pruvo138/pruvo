#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N3 bataryasini cron duzlemine KUR / GERI AL.

Kaynak dogrusu depodadir (`tools/n3/n3_tatbikat.py`); cron duzlemine
konan sey INCE bir kosucudur — ikinci kopya DEGIL, tek satirlik cagri.
([[agents-md-tek-kaynak]] ailesi: ikiz tanim sessizce ayrisir.)

  KUR:      python3 tools/n3/n3-kur.py --kur
  GERI AL:  python3 tools/n3/n3-kur.py --geri-al <damga>
  DURUM:    python3 tools/n3/n3-kur.py --durum
"""

import argparse
import os
import shutil
import sys
import time

CRON_KOKU = "/Users/okan/.claude/cron"
TESTLER = os.path.join(CRON_KOKU, "testler.py")
KOSUCU_ADI = "n3-tatbikat-test.py"
KOSUCU = os.path.join(CRON_KOKU, KOSUCU_ADI)

# 🔴 Kosucu kaynagi SIRAYLA arar: once ANA CHECKOUT (merge sonrasi kalici
# yer), sonra bu betigin oturdugu agac (merge oncesi dal/worktree). Tek bir
# mutlak yola civilenirse worktree silindiginde batarya SESSIZCE degil ama
# GEREKSIZCE kirmizi yanar ve butun testler.py takimini asagi ceker.
ANA_KAYNAK = "/Users/okan/dev/pruvo/tools/n3/n3_tatbikat.py"
YEREL_KAYNAK = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "n3_tatbikat.py")
KAYNAK_ADAYLARI = (ANA_KAYNAK, YEREL_KAYNAK)


def kaynak_coz():
    for aday in KAYNAK_ADAYLARI:
        if os.path.isfile(aday):
            return aday
    return None


KAYNAK = kaynak_coz() or YEREL_KAYNAK

# testler.py PAKETLER listesine eklenecek satirin CAPASI: son paket.
CAPA = '    "nobet-merdiven-test.py",\n'
YENI = CAPA + '    "%s",\n' % KOSUCU_ADI

KOSUCU_GOVDESI = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N3 tatbikat bataryasi — INCE KOSUCU (kaynak dogrusu depodadir).

Bu dosya mantik TASIMAZ; depodaki tek kaynagi cagirir. Hicbir aday
yoksa FAIL-CLOSED: KABUL=KALDI, rc=1 (sessiz yesil YOK).
"""

import importlib.util
import os
import sys

KAYNAK_ADAYLARI = %r


def main():
    kaynak = None
    for aday in KAYNAK_ADAYLARI:
        if os.path.isfile(aday):
            kaynak = aday
            break
    if kaynak is None:
        print("KAYNAK_YOK adaylar=%%s" %% (KAYNAK_ADAYLARI,))
        print("KABUL=KALDI")
        return 1
    print("KAYNAK=%%s" %% kaynak)
    for kok in ("/Users/okan/.claude/cron", "/Users/okan/dev/pruvo/tools"):
        if kok not in sys.path:
            sys.path.insert(0, kok)
    spec = importlib.util.spec_from_file_location("n3_tatbikat_kaynak", kaynak)
    modul = importlib.util.module_from_spec(spec)
    sys.modules["n3_tatbikat_kaynak"] = modul
    spec.loader.exec_module(modul)
    return modul.main(["--tam"])


if __name__ == "__main__":
    sys.exit(main())
'''


def _damga():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def durum():
    with open(TESTLER, encoding="utf-8") as dosya:
        metin = dosya.read()
    kayitli = ('"%s"' % KOSUCU_ADI) in metin
    print("KOSUCU_VAR=%s yol=%s" % (os.path.isfile(KOSUCU), KOSUCU))
    print("TESTLER_KAYITLI=%s yol=%s" % (kayitli, TESTLER))
    print("KAYNAK_VAR=%s yol=%s" % (os.path.isfile(KAYNAK), KAYNAK))
    # 🔴 [[kapinin-menzili-cagri-yeridir]]: kayitli olmak KOSULUYOR demek
    # degildir. testler.py'nin KENDI cagri yeri de basilir.
    cagiranlar = []
    aranan_kokler = (CRON_KOKU,
                     "/Users/okan/dev/pruvo/.github",
                     "/Users/okan/dev/pruvo/tools")
    for kok in aranan_kokler:
        for dizin, _alt, dosyalar in os.walk(kok):
            if "/.git" in dizin or "__pycache__" in dizin or "worktrees" in dizin:
                continue
            if "tarayici-profili" in dizin or "m3-profil" in dizin:
                continue
            for ad in dosyalar:
                if not ad.endswith((".py", ".sh", ".yml", ".yaml", ".md")):
                    continue
                if ad in ("testler.py", os.path.basename(__file__)):
                    continue
                yol = os.path.join(dizin, ad)
                try:
                    with open(yol, encoding="utf-8", errors="replace") as dosya:
                        if "testler.py" in dosya.read():
                            cagiranlar.append(yol)
                except OSError:
                    continue
    print("TESTLER_CAGRI_YERI_SAYISI=%d" % len(cagiranlar))
    for yol in sorted(cagiranlar):
        print("  CAGRI_YERI=%s" % yol)
    return 0 if (os.path.isfile(KOSUCU) and kayitli) else 1


def kur():
    if not os.path.isfile(KAYNAK):
        print("KAYNAK_YOK=%s" % KAYNAK)
        print("KABUL=KALDI")
        return 1
    damga = _damga()
    with open(KOSUCU, "w", encoding="utf-8") as dosya:
        dosya.write(KOSUCU_GOVDESI % (KAYNAK_ADAYLARI,))
    os.chmod(KOSUCU, 0o700)
    print("KOSUCU_YAZILDI=%s" % KOSUCU)

    with open(TESTLER, encoding="utf-8") as dosya:
        metin = dosya.read()
    if ('"%s"' % KOSUCU_ADI) in metin:
        print("TESTLER_ZATEN_KAYITLI=1 (degistirilmedi)")
        print("GERI_AL_DAMGASI=-")
        print("KABUL=GECTI")
        return 0
    if metin.count(CAPA) != 1:
        # Fail-closed: capa tekil degilse SESSIZCE atlamak yerine KIRMIZI.
        print("CAPA_TEKIL_DEGIL sayi=%d — testler.py ELLE incelenmeli"
              % metin.count(CAPA))
        print("KABUL=KALDI")
        return 1
    yedek = "%s.yedek-n3-%s" % (TESTLER, damga)
    shutil.copy2(TESTLER, yedek)
    with open(TESTLER, "w", encoding="utf-8") as dosya:
        dosya.write(metin.replace(CAPA, YENI, 1))
    print("TESTLER_YEDEK=%s" % yedek)
    print("TESTLER_KAYIT_EKLENDI=%s" % KOSUCU_ADI)
    print("GERI_AL_DAMGASI=%s" % damga)
    print("KABUL=GECTI")
    return 0


def geri_al(damga):
    yedek = "%s.yedek-n3-%s" % (TESTLER, damga)
    if not os.path.isfile(yedek):
        print("YEDEK_YOK=%s" % yedek)
        print("KABUL=KALDI")
        return 1
    shutil.copy2(yedek, TESTLER)
    if os.path.isfile(KOSUCU):
        os.remove(KOSUCU)
    print("TESTLER_GERI_ALINDI=%s" % yedek)
    print("KOSUCU_SILINDI=%s" % KOSUCU)
    print("KABUL=GECTI")
    return 0


def main(argv=None):
    ayrist = argparse.ArgumentParser()
    ayrist.add_argument("--kur", action="store_true")
    ayrist.add_argument("--durum", action="store_true")
    ayrist.add_argument("--geri-al", default=None)
    args = ayrist.parse_args(argv)
    if args.geri_al:
        return geri_al(args.geri_al)
    if args.kur:
        rc = kur()
        durum()
        return rc
    return durum()


if __name__ == "__main__":
    sys.exit(main())
