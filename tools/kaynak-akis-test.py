#!/usr/bin/env python3
r"""KABUL TESTI (GÖREV B) — 3 yeni kaynagin ekleme AKISINA baglandigini dogrular.

Iki tur:
  1. SMOKE: makerworld-ara.py / cults3d-ara.py / myminifactory-ara.py `--help` ile CRASH ETMEDEN
     exit 0 doner (bu scriptler argparse KULLANMAZ — `--help` bir arama terimi gibi islenir ama
     "kimlik yok"/"ag hatasi" yollari zarifçe yakalanir -> exit 0; yani gercek smoke: import/sozdizim
     patlamiyor + main yolu cokmuyor). Ag/anahtar OLMADAN da exit 0 (istisna ic loop'ta yakalanir).
  2. GREP: paket-marka-ekleme.md 3 kaynagi (ara+ekle komutlariyla) iceriyor; 3 skill dosyasi
     (.claude/commands/*.md) mevcut ve her biri dogru KAYNAK=<Ad>'i referansliyor.

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


# --- 1) SMOKE: ara scriptleri --help ile cokmez, exit 0 ----------------------
print("--- SMOKE (*-ara.py --help exit 0, crash yok) ---")
for script in ("makerworld-ara.py", "cults3d-ara.py", "myminifactory-ara.py"):
    path = os.path.join(TOOLS, script)
    try:
        p = subprocess.run(["python3", path, "--help"], capture_output=True, text=True, timeout=120)
        rc = p.returncode
        crashed = "Traceback (most recent call last)" in (p.stderr or "")
    except subprocess.TimeoutExpired:
        rc, crashed = "TIMEOUT", True
    check("%s --help exit 0 (crash yok)" % script, rc == 0 and not crashed)


# --- 2) GREP: spec dosyasi 3 kaynagi ara+ekle ile iceriyor -------------------
print("--- GREP: paket-marka-ekleme.md ---")
spec = ""
spec_path = os.path.join(TOOLS, "paket-marka-ekleme.md")
if os.path.exists(spec_path):
    spec = open(spec_path, encoding="utf-8").read()
check("paket-marka-ekleme.md mevcut", bool(spec))
for ad, ara, ekle in (
    ("MakerWorld", "makerworld-ara.py", "makerworld-ekle.py"),
    ("Cults3D", "cults3d-ara.py", "cults3d-ekle.py"),
    ("MyMiniFactory", "myminifactory-ara.py", "myminifactory-ekle.py"),
):
    check("spec '%s' adini iceriyor" % ad, ad in spec)
    check("spec '%s' ara komutu" % ad, ara in spec)
    check("spec '%s' ekle komutu" % ad, ekle in spec)
# olcusuz notu + API-anahtar env adlari
check("spec ÖLÇÜSÜZ notu", "ÖLÇÜSÜZ" in spec or "ölçüsüz" in spec or "ölçü satırı" in spec)
check("spec Cults3D env adlari", "CULTS_USERNAME" in spec and "CULTS_API_KEY" in spec)
check("spec MMF env adi", "MMF_KEY" in spec)


# --- 3) GREP: 3 skill dosyasi mevcut + dogru KAYNAK=<Ad> ---------------------
print("--- GREP: .claude/commands skill dosyalari ---")
for fname, kaynak in (
    ("makerworld.md", "MakerWorld"),
    ("cults3d.md", "Cults3D"),
    ("myminifactory.md", "MyMiniFactory"),
):
    fpath = os.path.join(CMDS, fname)
    var = ""
    if os.path.exists(fpath):
        var = open(fpath, encoding="utf-8").read()
    check("%s mevcut" % fname, bool(var))
    check("%s KAYNAK=%s referansi" % (fname, kaynak), ("KAYNAK=%s" % kaynak) in var)
    check("%s description'da '%s'" % (fname, kaynak), kaynak in var.split("---")[1] if "---" in var else False)
# API-anahtar notu yalniz cults3d + mmf skill'inde
c3 = open(os.path.join(CMDS, "cults3d.md"), encoding="utf-8").read() if os.path.exists(os.path.join(CMDS, "cults3d.md")) else ""
mmf = open(os.path.join(CMDS, "myminifactory.md"), encoding="utf-8").read() if os.path.exists(os.path.join(CMDS, "myminifactory.md")) else ""
check("cults3d.md API-anahtar notu (CULTS_USERNAME)", "CULTS_USERNAME" in c3)
check("myminifactory.md API-anahtar notu (MMF_KEY)", "MMF_KEY" in mmf)


print()
if FAILS:
    print("BASARISIZ — %d kontrol KALDI:" % len(FAILS), file=sys.stderr)
    for ad in FAILS:
        print("  x %s" % ad, file=sys.stderr)
    sys.exit(1)
print("TUM TESTLER GECTI.")
sys.exit(0)
