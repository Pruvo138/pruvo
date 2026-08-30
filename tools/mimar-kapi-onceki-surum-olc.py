#!/usr/bin/env python3
"""ONCE/SONRA OLCUMU — bir git ref'indeki kapi dosyalarini GECICI dizine cikarir ve
GUNCEL kabul testini (tools/mimar-kilit-test.py) O KOPYAYA kosturur.

Neden: "su kusur vardi, kapattim" iddiasi ancak ESKI SURUMUN yeni fikstürleri KIRMIZI
yaktigi olculerek kanitlanir. Bu arac o kaniti UREtir (elle 'git show' + gecici dizin
kurmak yerine tek komut, yeniden kosulabilir).

    python3 tools/mimar-kapi-onceki-surum-olc.py                 # ref=HEAD
    python3 tools/mimar-kapi-onceki-surum-olc.py --ref ccb4482e  # belirli surum

Cikti: ref'te KIRMIZI yanan vaka numaralari (= o surumde davranis FARKLIYDI). Cikis kodu
DAIMA 0 — bu bir kapi degil, bir OLCUM aracidir (yargiyi mimar verir).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)
TEST = os.path.join(TOOLS, "mimar-kilit-test.py")

DOSYALAR = (
    "mimar-kod-kilidi.py",
    "mimar-icra-kapisi.py",
    "mimar-commit-kapisi.py",
    "mimar-kapi-kur.py",
    "mimar-kilit-test.py",
)


def main():
    argv = sys.argv[1:]
    ref = argv[argv.index("--ref") + 1] if "--ref" in argv else "HEAD"

    dizin = os.path.realpath(tempfile.mkdtemp(prefix="pruvo-onceki-surum-"))
    try:
        for dosya in DOSYALAR:
            sonuc = subprocess.run(
                ["git", "-C", KOK, "show", ref + ":tools/" + dosya],
                capture_output=True, text=True)
            if sonuc.returncode != 0:
                print("CIKARILAMADI: " + ref + ":tools/" + dosya)
                sys.exit(0)
            with open(os.path.join(dizin, dosya), "w", encoding="utf-8") as f:
                f.write(sonuc.stdout)

        kosum = subprocess.run([sys.executable, TEST, dizin],
                               capture_output=True, text=True)
        kirmizi = []
        for satir in (kosum.stdout or "").splitlines():
            m = re.match(r"\s*vaka (\d+): beklenen=(\S+) olculen=(\S+)", satir)
            if m:
                kirmizi.append((int(m.group(1)), m.group(2), m.group(3)))

        print("REF               : " + ref)
        print("GECICI DIZIN      : " + dizin)
        print("TEST              : " + TEST + " (GUNCEL fikstürler)")
        print("REF'TE KIRMIZI    : " + str(len(kirmizi)))
        for no, beklenen, olculen in sorted(kirmizi):
            print("  vaka {:<4} beklenen={:<6} ref'te olculen={}".format(no, beklenen, olculen))
        if not kirmizi:
            print("  (yok — ref bu fikstürlerin hepsinde GUNCEL surumle AYNI davraniyor)")
    finally:
        shutil.rmtree(dizin, ignore_errors=True)
    sys.exit(0)


main()
