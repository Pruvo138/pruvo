#!/usr/bin/env python3
"""serit-b-katalog-aynasi.py kabul bataryasi — AG YOK, sentetik git deposu (tempfile).

Vakalar:
  V1 dal geride + katalog dokunulmamis -> AYNA=UYGULANDI, dosya == origin/main surumu
  V2 dal katalogu degistirmis          -> AYNA=YOK, dosya == dalin surumu
  V3 ref=main (yerel main origin/main'in gerisinde) -> AYNA=GEREKSIZ, dosya DEGISMEZ
  V4 dal ve main katalogu esit          -> AYNA=GEREKSIZ
  V5 origin/main yok                    -> rc=2 OLCULEMEDI, dosya DEGISMEZ
  V6 --geri                             -> dosya HEAD surumu, `git status` temiz
Mutantlar (IZOLE kopya; once mutasyonsuz TABAN tum vakalarda yesil olmali; kirmizi kume
hedef kumeyi KAPSAMALI):
  MA dal-degisiklik kontrolu kalkar -> {V2}
  MB dosya yazimi kalkar            -> {V1}
  MC ref=main kolu kalkar           -> {V3}
Kendi deposuna YAZMAZ: tum git islemleri tempfile altindaki sentetik depoda.
"""
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "serit-b-katalog-aynasi.py")
sys.path.insert(0, os.path.join(KOK, "tools"))
from git_ortami import git_ortami, sentetik_git  # noqa: E402

# Kanca icinden kosulursa miras GIT_DIR/GIT_INDEX_FILE sentetik depoyu GERCEK depoya
# baglardi ([[kanca-icinde-test-git-init-gercek-depoyu-bare-yapar]]) -> kanonik yardimci.
ORTAM = git_ortami()


def g(d, *a):
    r = sentetik_git(d, *a, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("git " + " ".join(a) + ": " + r.stderr)
    return r.stdout.strip()


def yaz(d, ad, metin):
    with open(os.path.join(d, ad), "w", encoding="utf-8") as f:
        f.write(metin)


def oku(d, ad="urunler.json"):
    with open(os.path.join(d, ad), encoding="utf-8") as f:
        return f.read()


def depo(kok, senaryo):
    """senaryo: geride | dal-degistirdi | main-geride | esit | origin-yok"""
    d = os.path.join(kok, senaryo)
    os.makedirs(d)
    g(d, "init", "-q", "-b", "main")
    g(d, "config", "user.email", "t@t")
    g(d, "config", "user.name", "t")
    g(d, "config", "commit.gpgsign", "false")
    yaz(d, "urunler.json", '[{"id":"a"}]\n')
    yaz(d, "kod.txt", "1\n")
    g(d, "add", "-A")
    g(d, "commit", "-q", "-m", "taban")
    taban = g(d, "rev-parse", "HEAD")
    g(d, "checkout", "-q", "-b", "dal")
    yaz(d, "kod.txt", "2\n")
    if senaryo == "dal-degistirdi":
        yaz(d, "urunler.json", '[{"id":"a"},{"id":"dal"}]\n')
    g(d, "add", "-A")
    g(d, "commit", "-q", "-m", "dal isi")
    if senaryo != "origin-yok":
        g(d, "checkout", "-q", "main")
        if senaryo != "esit":
            yaz(d, "urunler.json", '[{"id":"a"},{"id":"jeep"}]\n')
        else:
            yaz(d, "kod.txt", "3\n")
        g(d, "add", "-A")
        g(d, "commit", "-q", "-m", "main ilerledi")
        g(d, "update-ref", "refs/remotes/origin/main", g(d, "rev-parse", "HEAD"))
        if senaryo == "main-geride":
            g(d, "reset", "-q", "--hard", taban)   # yerel main origin/main'in gerisinde
        else:
            g(d, "checkout", "-q", "dal")
    return d


def kos(arac, d, *arg):
    r = subprocess.run([sys.executable, arac, "--kok", d, *arg], capture_output=True, text=True, env=ORTAM)
    return r.returncode, r.stdout + r.stderr


def vakalar(arac):
    s = {}
    with tempfile.TemporaryDirectory() as t:
        d = depo(t, "geride")
        rc, o = kos(arac, d, "--uygula", "--ref", "dal")
        s["V1"] = rc == 0 and "AYNA=UYGULANDI" in o and oku(d) == '[{"id":"a"},{"id":"jeep"}]\n'
        rc, o = kos(arac, d, "--geri")
        s["V6"] = (rc == 0 and "AYNA_GERI=TAMAM" in o and oku(d) == '[{"id":"a"}]\n'
                   and g(d, "status", "--porcelain") == "")

        d = depo(t, "dal-degistirdi")
        rc, o = kos(arac, d, "--uygula", "--ref", "dal")
        s["V2"] = rc == 0 and "AYNA=YOK" in o and oku(d) == '[{"id":"a"},{"id":"dal"}]\n'

        d = depo(t, "main-geride")
        rc, o = kos(arac, d, "--uygula", "--ref", "main")
        s["V3"] = rc == 0 and "AYNA=GEREKSIZ" in o and oku(d) == '[{"id":"a"}]\n'

        d = depo(t, "esit")
        rc, o = kos(arac, d, "--uygula", "--ref", "dal")
        s["V4"] = rc == 0 and "AYNA=GEREKSIZ" in o and oku(d) == '[{"id":"a"}]\n'

        d = depo(t, "origin-yok")
        rc, o = kos(arac, d, "--uygula", "--ref", "dal")
        s["V5"] = rc == 2 and "OLCULEMEDI" in o and oku(d) == '[{"id":"a"}]\n'
    return s


VAKALAR = ["V1", "V2", "V3", "V4", "V5", "V6"]
MUTANTLAR = [
    ("MA dal-degisiklik kontrolu kalkar",
     'if git(kok, "diff", "--quiet", taban, "HEAD", "--", KATALOG).returncode != 0:', "if False:", {"V2"}),
    ("MB dosya yazimi kalkar", "        f.write(icerik.stdout)", "        pass", {"V1"}),
    ("MC ref=main kolu kalkar", '    if ref == "main":', "    if False:", {"V3"}),
]


def main():
    kirmizi = 0
    taban = vakalar(ARAC)
    for v in VAKALAR:
        ok = taban.get(v) is True
        kirmizi += 0 if ok else 1
        print(("  YESIL   " if ok else "  KIRMIZI ") + v)
    if kirmizi:
        print("SONUC: KIRMIZI %d (taban kirmiziyken mutant olcumu anlamsiz)" % kirmizi)
        return 1
    kaynak = open(ARAC, encoding="utf-8").read()
    with tempfile.TemporaryDirectory() as t:
        for ad, eski, yeni, hedef in MUTANTLAR:
            n = kaynak.count(eski)
            if n != 1:
                print("  KIRMIZI " + ad + " — capa TEK kez bulunmali, isabet " + str(n))
                kirmizi += 1
                continue
            kopya = os.path.join(t, ad.split()[0] + ".py")
            with open(kopya, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(eski, yeni))
            s = vakalar(kopya)
            yanan = {v for v in VAKALAR if s.get(v) is not True}
            ok = hedef <= yanan
            kirmizi += 0 if ok else 1
            print(("  YESIL   " if ok else "  KIRMIZI ") + ad + " -> yanan " + (",".join(sorted(yanan)) or "YOK"))
    print("SONUC: " + ("YESIL (%d vaka + %d mutant)" % (len(VAKALAR), len(MUTANTLAR)) if kirmizi == 0
                      else "KIRMIZI %d" % kirmizi))
    return 0 if kirmizi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
