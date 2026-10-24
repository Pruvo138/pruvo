#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D1 ZARF FIKSTUR KAPISI — D1 sonucu ayristiran her arac, GERCEK zarfla konusan bir
kabul testine bagli mi?

NEDEN VAR (17 Eki 2026, BaBa 17:4x kurali): `inis-sayac-oku.py` kabul testi 6/6 + 3/3
yesildi ama yalniz sqlite kolunu olcuyordu; canli wrangler cevabi bir zarf LISTESIDIR ve
arac onu dict sandigi icin canlida sessiz `TOPLAM=0` basti. Kural: gercek zarf TEK ortak
fikstur (`tools/fikstur/wrangler-d1-zarf.json` + `tools/d1_zarf_fikstur.py`); D1 okuyan
her aracin en az bir kabul testi o modulu kullanir. Yeni D1 okuyucusu fiksturlu test
olmadan SERIT B'den gecmez.

KAPSAM (olculur, elle liste YOK): `tools/*.py` icinde (test/mutasyon dosyalari ve bu
kapinin kendi parcalari HARIC) hem bir D1 cagrisi (`d1 execute` · `.sorgu` ·
`dosya_calistir(` · `wrangler([`) hem de sonuc ayristirma (`"results"`) gecen dosya.
BAGLI: `tools/*-test.py` icinden biri aracin dosya adini (ornek `inis-sayac-oku.py`)
ANIYOR ve `d1_zarf_fikstur` modulunu kullaniyor.

CIKTI (tek satir + eksikler):
    D1_ZARF_KAPSAM=<n> BAGLI=<k> EKSIK=<m> HAL=YESIL|KIRMIZI
    EKSIK: tools/<arac>.py   (her eksik icin)
rc: 0 YESIL · 1 KIRMIZI (eksik var) · 2 OLCULEMEDI (fikstur sekli bozuk / kapsam 0)

Kullanim:  python3 tools/d1-zarf-fikstur-kapisi.py [--kok <depo koku>]
"""
import argparse
import glob
import importlib.util
import os
import re
import sys

sys.dont_write_bytecode = True

KENDI = ("d1-zarf-fikstur-kapisi.py", "d1_zarf_fikstur.py")
D1_CAGRI = re.compile(r"d1 execute|\.sorgu\b|dosya_calistir\(|\bwrangler\(\[")
SONUC = re.compile(r"""["']results["']""")
YARDIMCI = "d1_zarf_fikstur"
# Kapsam disi BIRAKILAN arac — gerekcesiyle (bos baslar; eklenen her satir bir yargidir).
MUAF = {}   # 24 Eki 2026 K443: tek muaf `reklam-oci-kapisi.py` aracla birlikte silindi


def _oku(yol):
    try:
        with open(yol, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def kapsam(tools):
    out = []
    for yol in sorted(glob.glob(os.path.join(tools, "*.py"))):
        ad = os.path.basename(yol)
        if ad in KENDI or ad.endswith("-test.py") or "mutasyon" in ad or "mutant" in ad:
            continue
        metin = _oku(yol)
        if D1_CAGRI.search(metin) and SONUC.search(metin):
            out.append(ad)
    return out


def bagli_mi(tools, ad, testler):
    for t in testler:
        metin = _oku(t)
        if ad in metin and YARDIMCI in metin:
            return True
    return False


def fikstur_saglam(tools):
    yol = os.path.join(tools, "d1_zarf_fikstur.py")
    if not os.path.isfile(yol):
        return False
    try:
        spec = importlib.util.spec_from_file_location("d1_zarf_fikstur_kapi", yol)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        z = mod.zarf([{"a": 1}])
        return isinstance(z, list) and z[0]["results"] == [{"a": 1}]
    except Exception:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kok", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args(argv)
    tools = os.path.join(a.kok, "tools")

    if not fikstur_saglam(tools):
        print("D1_ZARF=OLCULEMEDI sebep=FIKSTUR")
        return 2
    alan = [ad for ad in kapsam(tools) if ad not in MUAF]
    if not alan:
        print("D1_ZARF=OLCULEMEDI sebep=KAPSAM-BOS")
        return 2
    testler = sorted(glob.glob(os.path.join(tools, "*-test.py")))
    eksik = [ad for ad in alan if not bagli_mi(tools, ad, testler)]
    hal = "YESIL" if not eksik else "KIRMIZI"
    print("D1_ZARF_KAPSAM=%d BAGLI=%d EKSIK=%d HAL=%s"
          % (len(alan), len(alan) - len(eksik), len(eksik), hal))
    for ad in eksik:
        print("EKSIK: tools/%s" % ad)
    return 0 if not eksik else 1


if __name__ == "__main__":
    sys.exit(main())
