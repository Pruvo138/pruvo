#!/usr/bin/env python3
"""K86: SERIT B'deki uc kapsam deligini tek, bagimsiz komutla olcer."""
import os
import subprocess
import sys


TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)
KOMUTLAR = (
    ("IS_AKISI", "is-akisi-kapisi.py", ()),
    ("MARKA_CIP", "marka-cip-mutasyon.py", ("--k86",)),
    ("MARKA_BOLUM", "marka-bolum-mutasyon.py", ("--k86",)),
    ("MODEL_BASLIK", "model-baslik-kolu-test.py", ("--kendini-test", "--k86")),
)


def main():
    sonuclar = []
    for ad, betik, ek in KOMUTLAR:
        komut = [sys.executable, os.path.join(TOOLS, betik)] + list(ek)
        print("K86_BASLA=%s" % ad, flush=True)
        cp = subprocess.run(komut, cwd=KOK)
        sonuclar.append((ad, cp.returncode))
        print("K86_SONUC=%s RC=%d" % (ad, cp.returncode), flush=True)
    kalan = [(ad, rc) for ad, rc in sonuclar if rc != 0]
    print("K86_OZET=" + ",".join("%s:%d" % x for x in sonuclar))
    print("HUKUM=" + ("YESIL" if not kalan else "KIRMIZI"))
    return 0 if not kalan else 1


if __name__ == "__main__":
    sys.exit(main())
