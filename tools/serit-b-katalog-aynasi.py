#!/usr/bin/env python3
"""SERIT B KATALOG AYNASI — dal kosumunda parite (filament-test TEST 5) katalog eksenini
CANLI olanla (D1 = origin/main:urunler.json) hizalar.

NEDEN (BaBa 20 Eki 23:4x, ayni sinifin ayni gun 3. vakasi — gizlilik · arsiv · vekil):
dal SERIT B'si dal UCUNDAKI urunler.json ile site uretir ve sonuclari CANLI /ara Worker'iyla
(D1) kiyaslar. Dal main'in gerisindeyken (arada urun partisi indiyse) D1'de olan urunler
yerel sitede YOKTUR -> "aciklanamayan ayrisim" -> TEST 5 KIRMIZI; oysa dal kataloga hic
dokunmamistir. Kirmizi dalin degil, olculen eksenin hatasidir (~90 dk kosucu + elle istisna).

KURAL:
  * ref main -> AYNA GEREKSIZ (main'in katalogu zaten canli olandir).
  * dal urunler.json'a merge-base'ten beri DOKUNMADIYSA -> calisma agacina
    origin/main:urunler.json yazilir (AYNA=UYGULANDI). Olculen eksen = canli.
  * dal urunler.json'a DOKUNDUYSA -> ayna YOK; TEST 5 dalin kendi katalogunu olcer
    (dalin katalog farki ayri eksendir, gizlenmez).
  * origin/main okunamazsa -> OLCULEMEDI rc=2 (sessiz eski davranisa DUSMEZ).
  * --geri -> urunler.json HEAD haline doner (sonraki adimlar dalin kendi agacini olcer).

  python3 tools/serit-b-katalog-aynasi.py --uygula [--ref <ad>] [--kok <dizin>]
  python3 tools/serit-b-katalog-aynasi.py --geri [--kok <dizin>]
Kabul bataryasi: tools/serit-b-katalog-aynasi-test.py (6 vaka + 3 mutant).
"""
import argparse
import os
import subprocess
import sys

KATALOG = "urunler.json"
ANA_REF = "origin/main"


def git(kok, *arg):
    return subprocess.run(["git", "-C", kok, *arg], capture_output=True, text=True)


def blob(kok, ref):
    r = git(kok, "rev-parse", "--verify", "--quiet", ref + ":" + KATALOG)
    return r.stdout.strip() if r.returncode == 0 else ""


def uygula(kok, ref):
    if ref == "main":
        print("AYNA=GEREKSIZ sebep=ref-main")
        return 0
    if git(kok, "rev-parse", "--verify", "--quiet", ANA_REF).returncode != 0:
        print("AYNA=OLCULEMEDI sebep=" + ANA_REF + "-yok rc=2")
        return 2
    mb = git(kok, "merge-base", "HEAD", ANA_REF)
    if mb.returncode != 0 or not mb.stdout.strip():
        print("AYNA=OLCULEMEDI sebep=merge-base-yok rc=2")
        return 2
    taban = mb.stdout.strip()
    if git(kok, "diff", "--quiet", taban, "HEAD", "--", KATALOG).returncode != 0:
        print("AYNA=YOK sebep=dal-katalog-degistirdi taban=" + taban[:8])
        return 0
    dal_blob, ana_blob = blob(kok, "HEAD"), blob(kok, ANA_REF)
    if not ana_blob:
        print("AYNA=OLCULEMEDI sebep=" + ANA_REF + "-katalog-yok rc=2")
        return 2
    if dal_blob == ana_blob:
        print("AYNA=GEREKSIZ sebep=esit blob=" + ana_blob[:8])
        return 0
    icerik = subprocess.run(["git", "-C", kok, "show", ANA_REF + ":" + KATALOG], capture_output=True)
    if icerik.returncode != 0:
        print("AYNA=OLCULEMEDI sebep=git-show rc=2")
        return 2
    with open(os.path.join(kok, KATALOG), "wb") as f:
        f.write(icerik.stdout)
    print("AYNA=UYGULANDI dal=" + dal_blob[:8] + " main=" + ana_blob[:8] + " taban=" + taban[:8])
    return 0


def geri(kok):
    r = git(kok, "checkout", "HEAD", "--", KATALOG)
    if r.returncode != 0:
        print("AYNA_GERI=OLCULEMEDI rc=2 " + r.stderr.strip()[:200])
        return 2
    print("AYNA_GERI=TAMAM")
    return 0


def main():
    p = argparse.ArgumentParser()
    k = p.add_mutually_exclusive_group(required=True)
    k.add_argument("--uygula", action="store_true")
    k.add_argument("--geri", action="store_true")
    p.add_argument("--ref", default=os.environ.get("GITHUB_REF_NAME", ""))
    p.add_argument("--kok", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = p.parse_args()
    if a.geri:
        return geri(a.kok)
    if not a.ref:
        print("AYNA=OLCULEMEDI sebep=ref-bos rc=2")
        return 2
    return uygula(a.kok, a.ref)


if __name__ == "__main__":
    sys.exit(main())
