#!/usr/bin/env python3
"""Gizli kaynak D1 kasasinin hicbir Worker kaynagi/binding'ine baglanmadigini zorlar."""
import os
import subprocess
import sys


KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YASAK = (b"pruvo-kaynak-kasa", b"kaynak_kasa", b"kaynak-kasa")
WORKER_KOKLERI = ("worker/", "workers/", "shop/src/", "onizleme/src/")


def izlenenler():
    p = subprocess.run(["git", "-C", KOK, "ls-files", "-z"], capture_output=True)
    if p.returncode != 0:
        raise RuntimeError("git izlenen yuzeyi olculemedi")
    return [x.decode("utf-8") for x in p.stdout.split(b"\0") if x]


def worker_yuzeyi(yol):
    kucuk = yol.lower()
    taban = os.path.basename(kucuk)
    return kucuk.startswith(WORKER_KOKLERI) or taban.startswith("wrangler.")


def main():
    try:
        yuzey = [yol for yol in izlenenler() if worker_yuzeyi(yol)]
        if not yuzey:
            raise RuntimeError("worker/wrangler yuzeyi bos")
        ihlal = 0
        for yol in yuzey:
            with open(os.path.join(KOK, yol), "rb") as f:
                icerik = f.read().lower()
            ihlal += sum(1 for imza in YASAK if imza in icerik)
    except (OSError, UnicodeError, RuntimeError) as e:
        print("IZOLASYON_RC=2 YUZEY=0 IHLAL=0 HATA=%s" % type(e).__name__)
        return 2
    print("IZOLASYON_RC=%d YUZEY=%d IHLAL=%d" % (0 if ihlal == 0 else 1, len(yuzey), ihlal))
    return 0 if ihlal == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
