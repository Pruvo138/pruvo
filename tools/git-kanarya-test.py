#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/git-kanarya-test.py — pre-push kanaryasi + sizinti kapisi MUTANT kabul testi.

Gercek depoya DOKUNMADAN: gecici dizinde sentetik bir "gercek depo" (+ linked
worktree) kurulur, 9 Eki 2026 olayinin fiksturu (miras GIT_DIR ile `git init` +
sahte origin ref'i) ONA karsi kosulur.

  K1  temiz koşum (hook benzeri miras GIT_DIR/GIT_WORK_TREE ile) -> `KANARYA=YESIL`, rc 0
  K2  mutant 4b: miras GIT_DIR'li fikstur -> `KANARYA=KIRMIZI bare` (+ origin_ref), rc 1
  K3  mutant 4a: ayni fikstur `fikstur-git-sizinti-kapisi.py --dizin` -> SIZDIRIYOR, rc 1
  K4  kontrol: kanonik `sentetik_git` fiksturu ayni kapida rc 0
  K5  kanarya depo disinda OLCULEMEDI rc 2 (fail-closed)
  K6  GERCEK depo kanaryasi testin ONCESI == SONRASI (test yuku sizmadi)

Pre-push benzeri ortamda da kosulur:
  GIT_DIR=<ana>/.git/worktrees/<ad> GIT_WORK_TREE=<agac> python3 tools/git-kanarya-test.py
"""
import importlib.util
import os
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
from git_ortami import git_ortami, sentetik_git  # noqa: E402  (kanonik kurucu)

KANARYA = os.path.join(TOOLS, "git-kanarya.py")
KAPI = os.path.join(TOOLS, "fikstur-git-sizinti-kapisi.py")

# 9 Eki olayinin bicimi: hedef GECICI, ortam MIRAS -> GIT_DIR gercek depoya iner.
MUTANT = (
    "import subprocess, sys, tempfile\n"
    "d = tempfile.mkdtemp(dir=sys.argv[1])\n"
    "subprocess.run([\"git\", \"init\", \"-q\", d])\n"
    "subprocess.run([\"git\", \"update-ref\", \"refs/remotes/origin/kral/x\", \"HEAD\"])\n"
)
KONTROL = (
    "from git_ortami import sentetik_git\n"
    "def kur(d):\n"
    "    sentetik_git(d, \"init\", \"-q\", d)\n"
)


def _kanarya_mod():
    spec = importlib.util.spec_from_file_location("git_kanarya", KANARYA)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _kos(argv, ortam):
    p = subprocess.run([sys.executable] + argv, env=ortam, capture_output=True,
                       text=True, timeout=120)
    return p.returncode, (p.stdout + p.stderr).strip()


def main():
    mod = _kanarya_mod()
    gercek = os.path.dirname(TOOLS)
    gercek_once = mod.olc(gercek)
    hata = []

    def iddia(ad, kosul, ayrinti):
        print("%s %s — %s" % ("OK" if kosul else "FAIL", ad, ayrinti))
        if not kosul:
            hata.append(ad)

    with tempfile.TemporaryDirectory(prefix="pruvo-git-kanarya-") as d:
        ana = os.path.join(d, "ana")
        wt = os.path.join(d, "wt")
        sentetik_git(d, "init", "-q", ana, check=True)
        with open(os.path.join(ana, "OKUBENI.md"), "w", encoding="utf-8") as f:
            f.write("sentetik gercek depo\n")
        sentetik_git(ana, "add", "-A", check=True)
        sentetik_git(ana, "commit", "-q", "--no-verify", "-m", "ilk", check=True)
        sentetik_git(ana, "update-ref", "refs/remotes/origin/main", "HEAD", check=True)
        sentetik_git(ana, "worktree", "add", "-q", wt, check=True)
        wt_gitdir = os.path.join(ana, ".git", "worktrees", "wt")

        # Hook benzeri ortam: git, linked worktree kancasina MUTLAK GIT_DIR ihrac eder.
        kanca = git_ortami()
        kanca.update(GIT_DIR=wt_gitdir, GIT_WORK_TREE=wt)

        # K1 — temiz kosum
        rc, once = _kos([KANARYA, "--olc", "--depo", wt], kanca)
        iddia("K1-olc", rc == 0 and "bare=false" in once, "rc=%d %s" % (rc, once))
        sentetik_git(d, "init", "-q", os.path.join(d, "zararsiz"), ek_ortam=kanca, check=True)
        rc, cikti = _kos([KANARYA, "--karsilastir", once, "--depo", wt], kanca)
        iddia("K1-yesil", rc == 0 and cikti.startswith("KANARYA=YESIL bare=false origin_ref=1"),
              "rc=%d %s" % (rc, cikti))

        # K2 — mutant 4b: miras GIT_DIR (GIT_WORK_TREE yok — olaydaki bicim)
        mutant = os.path.join(d, "mutant.py")
        with open(mutant, "w", encoding="utf-8") as f:
            f.write(MUTANT)
        miras = git_ortami()
        miras["GIT_DIR"] = wt_gitdir
        subprocess.run([sys.executable, mutant, d], env=miras, capture_output=True,
                       cwd=d, timeout=60)
        rc, cikti = _kos([KANARYA, "--karsilastir", once, "--depo", wt], kanca)
        iddia("K2-bare", rc == 1 and "KANARYA=KIRMIZI bare once=false sonra=true" in cikti,
              "rc=%d %s" % (rc, cikti.replace("\n", " | ")))
        iddia("K2-origin_ref", "KANARYA=KIRMIZI origin_ref once=1 sonra=2" in cikti,
              cikti.replace("\n", " | "))

        # K3 — mutant 4a: statik kapi
        kirli = os.path.join(d, "kapi-kirli")
        os.mkdir(kirli)
        with open(os.path.join(kirli, "mutant_test.py"), "w", encoding="utf-8") as f:
            f.write(MUTANT)
        rc, cikti = _kos([KAPI, "--dizin", kirli], kanca)
        iddia("K3-kapi-kirmizi", rc == 1 and "SIZDIRIYOR: mutant_test.py" in cikti,
              "rc=%d %s" % (rc, cikti.replace("\n", " | ")))

        # K4 — kontrol fiksturu
        temiz = os.path.join(d, "kapi-temiz")
        os.mkdir(temiz)
        with open(os.path.join(temiz, "kontrol_test.py"), "w", encoding="utf-8") as f:
            f.write(KONTROL)
        rc, cikti = _kos([KAPI, "--dizin", temiz], kanca)
        iddia("K4-kapi-kontrol", rc == 0, "rc=%d %s" % (rc, cikti.replace("\n", " | ")))

        # K5 — depo disi
        bos = os.path.join(d, "bos")
        os.mkdir(bos)
        rc, cikti = _kos([KANARYA, "--olc", "--depo", bos], git_ortami())
        iddia("K5-olculemedi", rc == 2 and cikti.startswith("KANARYA=OLCULEMEDI"),
              "rc=%d %s" % (rc, cikti))

    # K6 — gercek depo
    rc, satirlar = mod.karsilastir(gercek_once, mod.olc(gercek))
    iddia("K6-gercek-depo", rc == 0, " | ".join(satirlar))

    if hata:
        print("SONUC: KIRMIZI — %d iddia: %s" % (len(hata), ", ".join(hata)))
        return 1
    print("SONUC: YESIL — iddia 9")
    return 0


if __name__ == "__main__":
    sys.exit(main())
