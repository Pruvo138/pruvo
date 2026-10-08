#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTANT CANLI YAZIM KAPISI — KENDI TESTI (fikstur + gercek repo).

tools/mutant-canli-yazim-kapisi.py'nin GERCEKTEN olctugunu kanitlar:
  · K1..K3 KIRMIZI fikstur — 7 Eki 2026'da onarilan dort surucunun UC yazim bicimi
    (finally'de dogrudan canli sabite yazim · ic ice `geri_koy()` · parametresi canli yol
    listesine bagli `_geri_al(yedek)`) TEK BASINA rc=1, SAYI=1 vermeli;
  · Y1..Y2 YESIL fikstur — izole kalip (`kopyada_kos` + finally'de yalniz mkdtemp silme)
    ve yazimsiz finally rc=0, SAYI=0 kalmali (kapi her finally'ye bagirmamali);
  · O1..O2 OLCULEMEDI — bos dizin ve ayristirilamayan dosya rc=2 (fail-closed);
  · M1..M2 MUAFIYET — gerekcesiz ve BAYAT muafiyet kaydi rc=1;
  · R  — gercek repo rc=0, SAYI=0.
Fikstur yalniz kendi mkdtemp dizinine yazilir; ev agacinda hicbir yol silinmez/yazilmaz.

KOSUM: python3 tools/mutant-canli-yazim-kapisi-test.py   # rc 0 = hepsi tuttu
"""
import contextlib
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(TOOLS, "mutant-canli-yazim-kapisi.py")

_BAS = '''import os, shutil, subprocess, sys, tempfile
TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
HEDEF = os.path.join(TOOLS, "hedef-kapisi.py")
'''

KIRMIZI = {
    "K1 finally'de dogrudan canli sabite yazim (deploy-aclik bicimi)":
        _BAS + '''
def main():
    ozgun = open(HEDEF, encoding="utf-8").read()
    with open(HEDEF, "w", encoding="utf-8") as f:
        f.write(ozgun + "#mutant")
    try:
        subprocess.run([sys.executable, HEDEF])
    finally:
        with open(HEDEF, "w", encoding="utf-8") as f:
            f.write(ozgun)
''',
    "K2 finally'de ic ice geri_koy() (serit-beyani bicimi)":
        _BAS + '''
def main():
    with open(HEDEF, "rb") as f:
        orijinal = f.read()

    def geri_koy():
        with open(HEDEF, "wb") as f:
            f.write(orijinal)
    try:
        subprocess.run([sys.executable, HEDEF])
    finally:
        geri_koy()
''',
    "K3 finally'de _geri_al(yedek) — parametre canli yol listesine bagli (iletisim bicimi)":
        _BAS + '''
KAPI = os.path.join(TOOLS, "kisisel-test.py")
MUTANTLAR = [("M1", [(KAPI, "a", "b")])]

def _uygula(duzenlemeler):
    yedek = {}
    for yol, _e, _y in duzenlemeler:
        yedek[yol] = open(yol, encoding="utf-8").read()
    return yedek

def _geri_al(yedek):
    for yol, metin in yedek.items():
        with open(yol, "w", encoding="utf-8") as f:
            f.write(metin)

def main():
    for ad, duzenlemeler in MUTANTLAR:
        yedek = _uygula(duzenlemeler)
        try:
            subprocess.run([sys.executable, KAPI])
        finally:
            _geri_al(yedek)
''',
}

YESIL = {
    "Y1 izole kalip (kopyada_kos + finally'de yalniz mkdtemp silinir)":
        _BAS + '''
from mutasyon_kopya import kopya_kok, kopyada_kos

def kos(kopya):
    return subprocess.run([sys.executable, os.path.join(kopya, "tools", "hedef-kapisi.py")])

def main():
    ozgun = open(HEDEF, encoding="utf-8").read()
    kopyada_kos("x-", {"tools/hedef-kapisi.py": ozgun + "#m"}, kos)
    tmp = tempfile.mkdtemp(prefix="x-")
    try:
        kopya = kopya_kok(tmp)
        hedef = os.path.join(kopya, "tools", "hedef-kapisi.py")
        with open(hedef, "w", encoding="utf-8") as f:
            f.write(ozgun)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
''',
    "Y2 yazimsiz finally (yalniz rapor)":
        _BAS + '''
def main():
    try:
        subprocess.run([sys.executable, HEDEF])
    finally:
        print("bitti")
''',
}


def kos(kok):
    r = subprocess.run([sys.executable, "-B", KAPI, "--kok", kok],
                       capture_output=True, text=True,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    cikti = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"SAYI=(\d+)", cikti)
    return r.returncode, (int(m.group(1)) if m else None), cikti


def fikstur(tmp, ad, govde):
    d = tempfile.mkdtemp(dir=tmp)
    with open(os.path.join(d, ad), "w", encoding="utf-8") as f:
        f.write(govde)
    return d


def muafiyet_kos(kok, muafiyet):
    """Kapinin main()'ini ayni surecte, TOOLS fikstur dizinine cevrilmis olarak kosar."""
    spec = importlib.util.spec_from_file_location("mutant_canli_yazim_kapisi", KAPI)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.TOOLS, mod.MUAFIYET = kok, muafiyet
    tampon = io.StringIO()
    with contextlib.redirect_stdout(tampon):
        rc = mod.main([])
    return rc, tampon.getvalue()


def main():
    print("=" * 70)
    print("MUTANT CANLI YAZIM KAPISI — KENDI TESTI")
    print("=" * 70)
    hatali = []
    tmp = tempfile.mkdtemp(prefix="mutant-canli-yazim-test-")
    try:
        for ad, govde in KIRMIZI.items():
            rc, sayi, cikti = kos(fikstur(tmp, "sahte-mutasyon.py", govde))
            if rc == 1 and sayi == 1 and "sahte-mutasyon.py" in cikti:
                print("  ok  %s -> KIRMIZI yakalandi (rc=1 SAYI=1)" % ad)
            else:
                hatali.append("%s -> rc=%s SAYI=%s (KIRMIZI bekleniyordu)" % (ad, rc, sayi))
                print("  ❌  %s -> rc=%s SAYI=%s\n%s" % (ad, rc, sayi, cikti[-800:]))

        for ad, govde in YESIL.items():
            rc, sayi, cikti = kos(fikstur(tmp, "izole-mutasyon.py", govde))
            if rc == 0 and sayi == 0:
                print("  ok  %s -> YESIL (rc=0 SAYI=0)" % ad)
            else:
                hatali.append("%s -> rc=%s SAYI=%s (YESIL bekleniyordu)" % (ad, rc, sayi))
                print("  ❌  %s -> rc=%s SAYI=%s\n%s" % (ad, rc, sayi, cikti[-800:]))

        bos = tempfile.mkdtemp(dir=tmp)
        for ad, kok in (("O1 bos dizin (taranacak surucu yok)", bos),
                        ("O2 ayristirilamayan surucu",
                         fikstur(tmp, "bozuk-mutasyon.py", "def (:\n"))):
            rc, _sayi, cikti = kos(kok)
            if rc == 2 and "OLCULEMEDI" in cikti:
                print("  ok  %s -> OLCULEMEDI (rc=2)" % ad)
            else:
                hatali.append("%s -> rc=%s (rc=2 OLCULEMEDI bekleniyordu)" % (ad, rc))
                print("  ❌  %s -> rc=%s" % (ad, rc))

        temiz = fikstur(tmp, "izole-mutasyon.py", YESIL["Y2 yazimsiz finally (yalniz rapor)"])
        for ad, muaf, iz in (
                ("M1 gerekcesiz muafiyet", {"izole-mutasyon.py": "  "}, "GEREKCESIZ"),
                ("M2 BAYAT muafiyet (ihlal yok)", {"izole-mutasyon.py": "gerekce"}, "BAYAT")):
            rc, cikti = muafiyet_kos(temiz, muaf)
            if rc == 1 and iz in cikti:
                print("  ok  %s -> KIRMIZI (rc=1, %s)" % (ad, iz))
            else:
                hatali.append("%s -> rc=%s (rc=1 + %s bekleniyordu)" % (ad, rc, iz))
                print("  ❌  %s -> rc=%s" % (ad, rc))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    rc, sayi, cikti = kos(TOOLS)
    if rc == 0 and sayi == 0:
        print("  ok  R  gercek repo -> YESIL (rc=0 SAYI=0)")
    else:
        hatali.append("R gercek repo -> rc=%s SAYI=%s" % (rc, sayi))
        print("  ❌  R gercek repo -> rc=%s SAYI=%s\n%s" % (rc, sayi, cikti[-1500:]))

    print("-" * 70)
    if hatali:
        print("SONUC: KIRMIZI ❌")
        for h in hatali:
            print("   · " + h)
        return 1
    print("SONUC: YESIL ✅ — KIRMIZI fikstur yakalandi (%d/%d), izole kalip YESIL, "
          "gercek repo SAYI=0." % (len(KIRMIZI), len(KIRMIZI)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
