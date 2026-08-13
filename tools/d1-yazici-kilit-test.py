#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D1 yazici flock kabul testi; offline, D1'e ve repo verisine dokunmaz."""
import argparse
import importlib.util
import os
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YOL = os.path.join(KOK, "tools", "d1-sync.py")
SPEC = importlib.util.spec_from_file_location("d1_sync_yazici_kilit", YOL)
D1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D1)


def alt_surec(yol):
    try:
        fd = D1.yazici_kilidi_al(yol)
    except SystemExit as e:
        print(e.code)
        return 23
    D1.yazici_kilidi_birak(fd)
    return 0


def ana_test():
    gecen = 0
    toplam = 5
    with tempfile.TemporaryDirectory(prefix="pruvo-d1-kilit-") as gecici:
        kilit = os.path.join(gecici, "kilit")
        with open(kilit, "w", encoding="utf-8"):
            pass
        birinci = D1.yazici_kilidi_al(kilit)
        basla = time.monotonic()
        ikinci = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--alt", kilit],
            capture_output=True, text=True, timeout=5)
        sure = time.monotonic() - basla
        mesaj = ikinci.stdout + ikinci.stderr
        if ikinci.returncode == 23 and "D1 YAZICI UCUSTA" in mesaj:
            gecen += 1
            print("GECTI ikinci yazici fail-closed rc=23")
        else:
            print("KALDI ikinci yazici rc=%d cikti=%r" % (ikinci.returncode, mesaj))
        if sure < 2.0:
            gecen += 1
            print("GECTI kilit non-blocking sure=%.3fs" % sure)
        else:
            print("KALDI kilit bekletti sure=%.3fs" % sure)
        D1.yazici_kilidi_birak(birinci)
        ucuncu = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--alt", kilit],
            capture_output=True, text=True, timeout=5)
        if ucuncu.returncode == 0 and "D1 yazici kilidi ALINDI" in ucuncu.stdout:
            gecen += 1
            print("GECTI birinci bitince sonraki yazici kilidi aldi")
        else:
            print("KALDI kilit serbest kalmadi rc=%d cikti=%r"
                  % (ucuncu.returncode, ucuncu.stdout + ucuncu.stderr))

    def kip(**degisen):
        temel = dict(kendini=False, bayatlik=False, seq_normalize=False,
                     sema=False, durum=False, kuru=False)
        temel.update(degisen)
        return argparse.Namespace(**temel)

    yazicilar = [kip(), kip(sema=True), kip(seq_normalize=True),
                 kip(seq_normalize=True, kuru=True)]
    saltlar = [kip(durum=True), kip(kuru=True), kip(bayatlik=True), kip(kendini=True)]
    if all(D1.yazici_yolu_mu(a) for a in yazicilar) \
            and not any(D1.yazici_yolu_mu(a) for a in saltlar):
        gecen += 1
        print("GECTI tum yazici kipleri kilitli; salt-okuma/kuru/test kipleri kilitsiz")
    else:
        print("KALDI yazici yol siniflandirmasi")
    ortak = D1.yazici_kilit_yolu()
    if os.path.isfile(ortak) and os.path.basename(ortak) == "config":
        gecen += 1
        print("GECTI varsayilan kilit mevcut ortak Git config inode'u (artik dosya YOK)")
    else:
        print("KALDI varsayilan ortak kilit yolu: %r" % ortak)
    print("SONUC: %d/%d" % (gecen, toplam))
    return 0 if gecen == toplam else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--alt", default=None)
    a = ap.parse_args()
    raise SystemExit(alt_surec(a.alt) if a.alt else ana_test())
