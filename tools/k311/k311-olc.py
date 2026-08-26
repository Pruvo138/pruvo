#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K311 OLCUM KOSUCUSU — nobet hattinin TABANINI ve SONRASINI ayni aletle olcer.

NEDEN AYRI DOSYA: chip `python3` calistiramaz (mimar-icra-kapisi); olcumu ucuz
kat kosturur. Isci PROZASINA guvenilmez -> bu betik HAM ciktiyi dosyaya doker,
sayilari mimar kendi `cat`/`grep`iyle okur ([[ucuz-isci-yesil-tablo-uydurur]]).

KOSUM:
    python3 tools/k311/k311-olc.py --cikti /tam/yol/OLCUM.txt

Ciktiya YALNIZ olculen sey yazilir; hukum YOK. Boru KULLANILMAZ (rc dogrudan).
"""

import argparse
import io
import os
import re
import subprocess
import sys

CRON = "/Users/okan/.claude/cron"

# (etiket, komut) — hepsi CIPLAK kosar; rc dogrudan okunur, boru YOK.
BATARYALAR = (
    ("TETIK", [sys.executable, os.path.join(CRON, "nobet-tetik-test.py")]),
    ("TETIK_MUTANT", [sys.executable, os.path.join(CRON, "nobet-tetik-mutasyon.py")]),
    ("GOZCU", [sys.executable, os.path.join(CRON, "gozcu-test.py")]),
    ("KOSUM_HUKMU", [sys.executable, os.path.join(CRON, "nobet-kosum-hukmu-test.py")]),
    # ② eksenini olcen fikstur: `ACIK=3 DAGITILAN=2 -> GECER` vakalari
    # buradadir. Canli logdaki ONARIM=0'in "bacak olu" mu "kuyruk bos" mu
    # oldugunu AYIRAN tek olcum bu bataryadir.
    ("KABUL", [sys.executable, os.path.join(CRON, "nobet-kabul-test.py")]),
    ("K311_KAPI", [sys.executable, os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "k311-baglanti-kapisi.py")]),
    ("K311_KAPI_KENDINI", [sys.executable, os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "k311-baglanti-kapisi.py"),
        "--kendini-test"]),
    ("K311_MUTANT", [sys.executable, os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "k311-mutasyon.py")]),
    ("N3_TATBIKAT", [sys.executable, os.path.join(CRON, "n3-tatbikat-test.py")]),
)

# Canli duzlemden sayilan jetonlar: (etiket, dosya, desen)
SAYIMLAR = (
    ("ci.acilan_tur=1", "ci-nobeti.log", r"acilan_tur=1"),
    ("ci.acilan_tur=0", "ci-nobeti.log", r"acilan_tur=0"),
    ("ci.BITIS_rc=0", "ci-nobeti.log", r"BITIS rc=0"),
    ("ci.BITIS_rc!=0", "ci-nobeti.log", r"BITIS rc=[^0]"),
    ("gz.KOSUM_HUKMU=TEMIZ", "gozcu.log", r"KOSUM_HUKMU=TEMIZ"),
    ("gz.KOSUM_HUKMU=ONARIM_DENENDI", "gozcu.log", r"KOSUM_HUKMU=ONARIM_DENENDI"),
    ("gz.KOSUM_HUKMU=MOTOR_DUSTU", "gozcu.log", r"KOSUM_HUKMU=MOTOR_DUSTU"),
    ("gz.KOSUM_HUKMU=OLCULEMEDI", "gozcu.log", r"KOSUM_HUKMU=OLCULEMEDI"),
    ("gz.GOZCU_rc=0", "gozcu.log", r"^GOZCU .* rc=0 "),
    ("gz.GOZCU_rc=1", "gozcu.log", r"^GOZCU .* rc=1 "),
    ("gz.TUR_HALI=KOSTU_ONARDI", "gozcu.log", r"TUR_HALI=KOSTU_ONARDI"),
    ("gz.TUR_HALI=KOSTU_DUSTU", "gozcu.log", r"TUR_HALI=KOSTU_DUSTU"),
    ("gz.ONARIM=0", "gozcu.log", r"^ *ONARIM=0"),
    ("gz.ONARIM>0", "gozcu.log", r"^ *ONARIM=[1-9]"),
    ("gz.DAGITILAN=0", "gozcu.log", r"^ *DAGITILAN=0"),
    ("gz.DAGITILAN>0", "gozcu.log", r"^ *DAGITILAN=[1-9]"),
    # 🔴 ② EKSENININ AYIRICISI: ONARIM=0 "bacak olu" mu, "kuyruk BOS" mu?
    # ACIK_KALEM daima 0 ise onarimsizlik ANLAMSIZDIR (nobet-kapi.py:1741
    # IS_YOK kolunun kendi gerekcesi).
    ("gz.ACIK_KALEM=0", "gozcu.log", r"^ *ACIK_KALEM=0"),
    ("gz.ACIK_KALEM>0", "gozcu.log", r"^ *ACIK_KALEM=[1-9]"),
    ("gz.KAPANAN>0", "gozcu.log", r"^ *KAPANAN=[1-9]"),
    ("gz.GOZCU_URETMEDI", "gozcu-cron.log", r"GOZCU_URETMEDI"),
    ("esk.deneme=3", "gozcu-eskalasyon.md", r"deneme=3"),
    ("esk.satir", "gozcu-eskalasyon.md", r"^- 20"),
)


def _yaz(akis, satir):
    akis.write(satir.rstrip("\n") + "\n")


def sayimlari_bas(akis):
    _yaz(akis, "=== BOLUM 1: CANLI DUZLEM SAYIMLARI ===")
    for etiket, dosya, desen in SAYIMLAR:
        yol = os.path.join(CRON, dosya)
        try:
            with io.open(yol, encoding="utf-8", errors="replace") as f:
                metin = f.read()
        except OSError as hata:
            _yaz(akis, "%s = OKUNAMADI (%s)" % (etiket, hata))
            continue
        n = len(re.findall(desen, metin, re.MULTILINE))
        _yaz(akis, "%s = %d" % (etiket, n))


def kalbi_bas(akis):
    _yaz(akis, "")
    _yaz(akis, "=== BOLUM 2: CANLI KALP ===")
    for ad in ("gozcu-kalp.json", "nobet-onarimsiz-sayac.json",
               "nobet-atlanan-sayac.json"):
        yol = os.path.join(CRON, ad)
        try:
            with io.open(yol, encoding="utf-8", errors="replace") as f:
                _yaz(akis, "--- %s ---" % ad)
                _yaz(akis, f.read())
        except OSError as hata:
            _yaz(akis, "--- %s --- OKUNAMADI (%s)" % (ad, hata))


def bataryalari_kos(akis):
    _yaz(akis, "")
    _yaz(akis, "=== BOLUM 3: KABUL BATARYALARI (ciplak rc) ===")
    rcler = {}
    for etiket, komut in BATARYALAR:
        if not os.path.isfile(komut[1]):
            _yaz(akis, "RC %s = YOK (%s)" % (etiket, komut[1]))
            rcler[etiket] = None
            continue
        try:
            sonuc = subprocess.run(komut, cwd=CRON, capture_output=True,
                                   text=True, timeout=900)
            rc = sonuc.returncode
        except subprocess.TimeoutExpired:
            rc = "TAVAN"
            sonuc = None
        rcler[etiket] = rc
        _yaz(akis, "RC %s = %s" % (etiket, rc))
        if sonuc is not None:
            _yaz(akis, "--- %s STDOUT ---" % etiket)
            _yaz(akis, sonuc.stdout)
            _yaz(akis, "--- %s STDERR ---" % etiket)
            _yaz(akis, sonuc.stderr)
    _yaz(akis, "")
    _yaz(akis, "=== BOLUM 4: RC OZETI ===")
    for etiket, _ in BATARYALAR:
        _yaz(akis, "OZET_RC %s = %s" % (etiket, rcler.get(etiket)))
    return rcler


def main(argv=None):
    ap = argparse.ArgumentParser(description="K311 nobet hatti olcumu")
    ap.add_argument("--cikti", required=True, help="ham ciktinin yazilacagi TAM yol")
    args = ap.parse_args(argv)

    tampon = io.StringIO()
    sayimlari_bas(tampon)
    kalbi_bas(tampon)
    bataryalari_kos(tampon)

    with io.open(args.cikti, "w", encoding="utf-8") as f:
        f.write(tampon.getvalue())
    print("OLCUM_YAZILDI=%s" % args.cikti)
    return 0


if __name__ == "__main__":
    sys.exit(main())
