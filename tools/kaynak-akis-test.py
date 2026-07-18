#!/usr/bin/env python3
r"""KABUL TESTI (GÖREV B) — aktif kaynak akisinin baglandigini dogrular.

Iki tur:
  1. SMOKE: aktif ara scriptleri `--help` ile CRASH ETMEDEN exit 0 doner.
  2. GREP: paket-marka-ekleme.md yalniz aktif kaynaklari ve komutlarini icerir; emekli
     slash-komut dosyalari stub durumundadir.

Kosum:  python3 tools/kaynak-akis-test.py   (cikis 0 = gecti, 1 = kaldi)
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
CMDS = os.path.join(ROOT, ".claude", "commands")
FAILS = []


def check(ad, kosul):
    print("  %s %s" % ("ok  " if kosul else "KALDI", ad))
    if not kosul:
        FAILS.append(ad)


print("--- SMOKE (*-ara.py --help exit 0, crash yok) ---")
for script in ("makerworld-ara.py", "printables-ara.py", "thing-ara.py"):
    path = os.path.join(TOOLS, script)
    try:
        p = subprocess.run(["python3", path, "--help"], capture_output=True, text=True, timeout=120)
        rc = p.returncode
        crashed = "Traceback (most recent call last)" in (p.stderr or "")
    except subprocess.TimeoutExpired:
        rc, crashed = "TIMEOUT", True
    check("%s --help exit 0 (crash yok)" % script, rc == 0 and not crashed)


print("--- GREP: paket-marka-ekleme.md ---")
spec = ""
spec_path = os.path.join(TOOLS, "paket-marka-ekleme.md")
if os.path.exists(spec_path):
    spec = open(spec_path, encoding="utf-8").read()
check("paket-marka-ekleme.md mevcut", bool(spec))
for ad, ara, ekle in (
    ("Printables", "printables-ara.py", "printables-ekle.py"),
    ("Thingiverse", "thing-ara.py", "urun-ekle.py"),
    ("MakerWorld", "makerworld-ara.py", "makerworld-ekle.py"),
):
    check("spec '%s' adini iceriyor" % ad, ad in spec)
    check("spec '%s' ara komutu" % ad, ara in spec)
    check("spec '%s' ekle komutu" % ad, ekle in spec)
check("spec emekli kaynak yok", all(x not in spec for x in ("Cults3D", "MyMiniFactory", "CGTrader")))


print("--- GREP: .claude/commands skill dosyalari ---")
for fname, kaynak in (
    ("makerworld.md", "MakerWorld"),
    ("cults3d.md", None),
    ("myminifactory.md", None),
    ("cgt.md", None),
):
    fpath = os.path.join(CMDS, fname)
    var = ""
    if os.path.exists(fpath):
        var = open(fpath, encoding="utf-8").read()
    check("%s mevcut" % fname, bool(var))
    if kaynak:
        check("%s KAYNAK=%s referansi" % (fname, kaynak), ("KAYNAK=%s" % kaynak) in var)
        check("%s description'da '%s'" % (fname, kaynak), kaynak in var.split("---")[1] if "---" in var else False)
    else:
        check("%s emekli notu" % fname, "EMEKLI" in var)
        check("%s arama baslatmiyor" % fname, "KAYNAK=" not in var and "Ara:" not in var and "DEVRET" not in var)


print()
if FAILS:
    print("BASARISIZ — %d kontrol KALDI:" % len(FAILS), file=sys.stderr)
    for ad in FAILS:
        print("  x %s" % ad, file=sys.stderr)
    sys.exit(1)
print("TUM TESTLER GECTI.")
sys.exit(0)
