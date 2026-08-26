#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K311 KAPANIS — artik temizligi + IKINCI TUR teyidi (tek turdan hukum verme).

[[tek-turdan-hukum-verme-anomali-kolu]]: bir kosum anomali tasiyabilir; kabul
IKI turda AYNI sayiyi vermelidir. Bu betik kritik bataryalari YENIDEN kosar ve
ilk turun sayilariyla KIYASLANABILIR bicimde basar.

TEMIZLIK (Okan'in USTUN disk kurali — "ureten temizler"):
  · KORUNUR: `*.yedek-k311-20260826T110225Z` (K311 ONCESI taban — bu duzlemde
    surum kontrolu YOK, tek geri donus yolu budur) ve `gozcu-test.py`nin
    kendi taban yedegi.
  · SILINIR: ara turlarin MUKERRER yedekleri, `.k311-e2e-tetik-*` artiklari,
    `__pycache__`.
  🔴 Budama kaniti budama ANINDA yazilir ([[budama-kaniti-budama-aninda-yazilir]]):
  silinen her dosyanin adi + boyutu BASILIR, sonra silinir.

KOSUM: python3 tools/k311/k311-kapanis.py --cikti /tam/yol/KAPANIS.txt
"""

import argparse
import io
import os
import re
import subprocess
import sys

CRON = "/Users/okan/.claude/cron"
BU = os.path.dirname(os.path.abspath(__file__))

# K311 ONCESI taban — SILINMEZ.
KORUNAN_DAMGALAR = ("20260826T110225Z",)
# gozcu-test.py bu damgada henuz hedef degildi; kendi tabani 110934Z'dedir.
KORUNAN_TEKIL = ("gozcu-test.py.yedek-k311-20260826T110934Z",)

BATARYALAR = (
    ("TETIK", [sys.executable, os.path.join(CRON, "nobet-tetik-test.py")]),
    ("GOZCU", [sys.executable, os.path.join(CRON, "gozcu-test.py")]),
    ("K311_KAPI", [sys.executable, os.path.join(BU, "k311-baglanti-kapisi.py")]),
    ("K311_MUTANT", [sys.executable, os.path.join(BU, "k311-mutasyon.py")]),
    ("KUR_DURUM", [sys.executable, os.path.join(BU, "k311-kur.py")]),
)


def _yaz(a, s):
    a.write(s.rstrip("\n") + "\n")


def dizin_boyutu(yol):
    toplam = 0
    for kok, _, adlar in os.walk(yol):
        for ad in adlar:
            try:
                toplam += os.path.getsize(os.path.join(kok, ad))
            except OSError:
                continue
    return toplam


def temizle(akis):
    _yaz(akis, "=== BOLUM 1: ARTIK TEMIZLIGI (budama kaniti) ===")
    once = dizin_boyutu(CRON)
    _yaz(akis, "DIZIN_BOYUTU_ONCE=%d" % once)

    adaylar = []
    for ad in sorted(os.listdir(CRON)):
        if ad in KORUNAN_TEKIL:
            continue
        if ".yedek-k311-" in ad:
            if any(d in ad for d in KORUNAN_DAMGALAR):
                continue
            adaylar.append(ad)
        elif ad.startswith(".k311-e2e-tetik-"):
            adaylar.append(ad)

    silinen = 0
    bayt = 0
    for ad in adaylar:
        yol = os.path.join(CRON, ad)
        try:
            boyut = os.path.getsize(yol)
        except OSError:
            continue
        _yaz(akis, "SILINIYOR %s (%d bayt)" % (ad, boyut))
        try:
            os.unlink(yol)
            silinen += 1
            bayt += boyut
        except OSError as hata:
            _yaz(akis, "  SILINEMEDI: %s" % hata)

    pyc = os.path.join(CRON, "__pycache__")
    if os.path.isdir(pyc):
        import shutil
        boyut = dizin_boyutu(pyc)
        _yaz(akis, "SILINIYOR __pycache__/ (%d bayt)" % boyut)
        shutil.rmtree(pyc, ignore_errors=True)
        bayt += boyut

    _yaz(akis, "SILINEN_DOSYA=%d SILINEN_BAYT=%d" % (silinen, bayt))
    _yaz(akis, "DIZIN_BOYUTU_SONRA=%d" % dizin_boyutu(CRON))
    _yaz(akis, "KORUNAN_TABAN=%s" % ", ".join(
        a for a in sorted(os.listdir(CRON)) if ".yedek-k311-" in a))


def teyit(akis):
    _yaz(akis, "")
    _yaz(akis, "=== BOLUM 2: IKINCI TUR TEYIDI (ciplak rc) ===")
    for etiket, komut in BATARYALAR:
        try:
            s = subprocess.run(komut, cwd=CRON, capture_output=True,
                               text=True, timeout=1200)
            rc = s.returncode
        except subprocess.TimeoutExpired:
            rc, s = "TAVAN", None
        _yaz(akis, "TUR2_RC %s = %s" % (etiket, rc))
        if s is not None:
            ozet = [l for l in s.stdout.split("\n")
                    if re.search(r"VAKA=|KIRIK |KURULU=|K311_BAGLANTI|"
                                 r"K311_MUTASYON|MUTANT=|OLUM_ESLESMESI|"
                                 r"OLU_ALAN|KONTROL=|E2E=", l)]
            for l in ozet:
                _yaz(akis, "  %s" % l)


def main(argv=None):
    ap = argparse.ArgumentParser(description="K311 kapanis")
    ap.add_argument("--cikti", required=True)
    args = ap.parse_args(argv)
    t = io.StringIO()
    temizle(t)
    teyit(t)
    with io.open(args.cikti, "w", encoding="utf-8") as f:
        f.write(t.getvalue())
    print("KAPANIS_YAZILDI=%s" % args.cikti)
    return 0


if __name__ == "__main__":
    sys.exit(main())
