#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/git-kanarya.py — PRE-PUSH KANARYASI: test yuku gercek depoya DOKUNDU MU?

OLCULEN OLAY (9 Eki 2026): pre-push icinde kosan bir oz-test vakasi miras `GIT_DIR`
ile gecici dizin yerine GERCEK depoda `git init` kostu -> ortak `.git/config`
`core.bare=true` + sahte `refs/remotes/origin/*`. Statik kapi
(`tools/fikstur-git-sizinti-kapisi.py`) vakayi yakaladi ama yalniz SERIT B'de
kosuyordu: kirmizi push'tan SONRA geldi. Kanarya ayni sinifi DAVRANISTAN olcer:
bataryadan ONCE ve SONRA ayni uc ekseni okur, fark varsa push DURUR.

EKSENLER:
  bare        `git config --get core.bare` (yoksa "yok")
  origin_ref  `git for-each-ref refs/remotes/origin` satir sayisi
  config      `git config --list --local` ciktisinin sha256'si (ilk 16 hane)

Kanaryanin KENDI git cagrilari miras GIT_* baglamini SOKER (kanonik `git_ortami`,
[[kanca-git-dir-kok-cozumu]]): olcum hedefi daima ACIK `-C <depo>`dur.

Kullanim:
  python3 tools/git-kanarya.py --olc [--depo <yol>]
      tek satir anlik goruntu basar (bare=.. origin_ref=.. config=..), rc 0
  python3 tools/git-kanarya.py --karsilastir "<onceki satir>" [--depo <yol>]
      esitse  `KANARYA=YESIL bare=<b> origin_ref=<n>`  rc 0
      farkta  her eksen icin `KANARYA=KIRMIZI <eksen> once=<x> sonra=<y>`  rc 1
  Olcum yapilamazsa `KANARYA=OLCULEMEDI <sebep>` rc 2 (fail-closed; cagiran DURUR).
"""
import hashlib
import os
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
from git_ortami import git_ortami  # noqa: E402  (kanonik GIT_* scrub)

EKSENLER = ("bare", "origin_ref", "config")


class Olculemedi(Exception):
    pass


def _git(depo, *args):
    try:
        p = subprocess.run(["git", "-C", depo] + list(args), env=git_ortami(),
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        raise Olculemedi("git calistirilamadi: %s" % type(exc).__name__)
    return p.returncode, p.stdout


def olc(depo):
    rc, bare = _git(depo, "config", "--get", "core.bare")
    if rc not in (0, 1):  # 1 = anahtar yok
        raise Olculemedi("core.bare okunamadi rc=%d" % rc)
    rc, refler = _git(depo, "for-each-ref", "--format=%(refname)", "refs/remotes/origin")
    if rc != 0:
        raise Olculemedi("for-each-ref rc=%d" % rc)
    rc, liste = _git(depo, "config", "--list", "--local")
    if rc != 0:
        raise Olculemedi("config --list --local rc=%d" % rc)
    return {
        "bare": bare.strip() or "yok",
        "origin_ref": str(len([s for s in refler.splitlines() if s.strip()])),
        "config": hashlib.sha256(liste.encode("utf-8")).hexdigest()[:16],
    }


def satir(goruntu):
    return " ".join("%s=%s" % (e, goruntu[e]) for e in EKSENLER)


def coz(metin):
    goruntu = {}
    for parca in (metin or "").split():
        if "=" in parca:
            k, v = parca.split("=", 1)
            goruntu[k] = v
    if set(goruntu) != set(EKSENLER):
        raise Olculemedi("onceki goruntu ayrisamadi: %r" % metin)
    return goruntu


def karsilastir(once, sonra):
    """(rc, satirlar) — rc 0 esit, 1 fark."""
    fark = ["KANARYA=KIRMIZI %s once=%s sonra=%s" % (e, once[e], sonra[e])
            for e in EKSENLER if once[e] != sonra[e]]
    if fark:
        return 1, fark
    return 0, ["KANARYA=YESIL bare=%s origin_ref=%s" % (sonra["bare"], sonra["origin_ref"])]


def main(argv):
    depo = os.path.dirname(TOOLS)
    if "--depo" in argv:
        i = argv.index("--depo")
        if i + 1 >= len(argv):
            print("KANARYA=OLCULEMEDI --depo degersiz")
            return 2
        depo = argv[i + 1]
    try:
        if "--olc" in argv:
            print(satir(olc(depo)))
            return 0
        if "--karsilastir" in argv:
            i = argv.index("--karsilastir")
            if i + 1 >= len(argv):
                raise Olculemedi("--karsilastir onceki goruntu istiyor")
            rc, satirlar = karsilastir(coz(argv[i + 1]), olc(depo))
            for s in satirlar:
                print(s)
            return rc
    except Olculemedi as exc:
        print("KANARYA=OLCULEMEDI %s" % exc)
        return 2
    print(__doc__.strip().splitlines()[0])
    print("KANARYA=OLCULEMEDI bayrak yok (--olc | --karsilastir)")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
