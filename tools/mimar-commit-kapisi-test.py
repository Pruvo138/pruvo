#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kabul testi: tools/mimar-commit-kapisi.py (daraltilmis worker bypass).

Kapiyi --stdin/--toplevel ile ANA-REPO kosullarinda sinar; GERCEK ana checkout'a
DOKUNMAZ (yalniz sentetik staged listesi + env verilir). Dogrulanan yeni davranis:

  - PRUVO_MIMAR_ONAY=worker + staged YALNIZ veri (urunler.json/.urun-kaynaklari.json)
      -> exit 0   (urun-ekleme hatti korunur; MaCiT'in sahasi)
  - PRUVO_MIMAR_ONAY=worker + staged'de HERHANGI kaynak dosyasi (.py/.js/... )
      -> exit 1   (worker onayi KAYNAGI ACMAZ; kaynak isi worktree'de commit'lenir)
  - env yok: kaynak+veri bloklanir (exit 1); .md serbest (exit 0)  [bugunku davranis]
  - --toplevel worktree yolu -> exit 0 (worktree muafiyeti, env'den bagimsiz)

VAKA 4 = ONCE-KIRMIZI TANIGI: bypass daraltilmadan onceki surumde exit 0 idi;
daraltmadan sonra exit 1. Ayni test dosyasi eski gate yoluyla cagirilirsa (argv[1])
bu vaka KIRMIZI yanar -> mutasyon kaniti.

Kullanim:
    python3 tools/mimar-commit-kapisi-test.py                 # kardes gate (bu worktree)
    python3 tools/mimar-commit-kapisi-test.py /yol/eski-gate.py   # once-kirmizi olcumu

Cikis kodu 0 = hepsi gecti, 1 = en az bir vaka kirmizi.
"""
import os
import subprocess
import sys

GATE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "mimar-commit-kapisi.py")
MAIN = "/Users/okan/dev/pruvo"
WORKTREE = MAIN + "/.claude/worktrees/agent-x"

# (no, beklenen_exit, worker?, toplevel, staged_satirlar, aciklama)
VAKALAR = [
    (1, 0, True,  MAIN, ["urunler.json"],
     "worker + yalniz urunler.json -> ACIK (mevcut hat korunur)"),
    (2, 0, True,  MAIN, [".urun-kaynaklari.json"],
     "worker + yalniz gizli kayit -> ACIK"),
    (3, 0, True,  MAIN, ["urunler.json", ".urun-kaynaklari.json"],
     "worker + iki veri dosyasi -> ACIK"),
    (4, 1, True,  MAIN, ["tools/x.py"],
     "ONCE-KIRMIZI: worker + kaynak .py -> KAPALI (eski surumde exit 0)"),
    (5, 1, True,  MAIN, ["urunler.json", "tools/x.py"],
     "worker + veri+kaynak birlikte -> KAPALI (kaynak var)"),
    (6, 1, True,  MAIN, ["index.html"],
     "worker + kaynak .html -> KAPALI"),
    (7, 1, True,  MAIN, ["tools/build.js"],
     "worker + kaynak .js -> KAPALI"),
    (8, 1, False, MAIN, ["urunler.json"],
     "env yok + urunler.json -> KAPALI"),
    (9, 1, False, MAIN, ["tools/x.py"],
     "env yok + kaynak -> KAPALI"),
    (10, 0, False, MAIN, ["README.md"],
     "env yok + README.md -> ACIK"),
    (11, 0, False, MAIN, ["DEVAM.md", "notlar/degisiklik.md"],
     "env yok + yalniz .md -> ACIK"),
    (12, 0, True,  WORKTREE, ["tools/x.py"],
     "worktree toplevel + worker + kaynak -> ACIK (muafiyet)"),
    (13, 0, False, WORKTREE, ["urunler.json"],
     "worktree muafiyeti env'den bagimsiz -> ACIK"),
    (14, 0, True,  MAIN, [],
     "worker + staged bos -> ACIK"),
    (15, 0, False, MAIN, [],
     "env yok + staged bos -> ACIK"),
]


def kostur(worker, toplevel, satirlar):
    ortam = dict(os.environ)
    ortam.pop("PRUVO_MIMAR_ONAY", None)
    if worker:
        ortam["PRUVO_MIMAR_ONAY"] = "worker"
    sonuc = subprocess.run(
        [sys.executable, GATE, "--stdin", "--toplevel", toplevel],
        input="".join(s + "\n" for s in satirlar),
        capture_output=True, text=True, env=ortam,
    )
    return sonuc.returncode


def main():
    if not os.path.isfile(GATE):
        print("EKSIK GATE: " + GATE)
        return 1
    print("=" * 74)
    print("MIMAR-COMMIT-KAPISI KABUL TESTI")
    print("gate: " + GATE)
    print("=" * 74)
    print("{:<4}{:<10}{:<10}{:<9}{}".format("No", "Beklenen", "Olculen", "Sonuc", "Vaka"))
    print("-" * 74)
    basarisiz = []
    for no, beklenen, worker, toplevel, satirlar, aciklama in VAKALAR:
        olculen = kostur(worker, toplevel, satirlar)
        gecti = (olculen == beklenen)
        if not gecti:
            basarisiz.append((no, beklenen, olculen, aciklama))
        print("{:<4}exit {:<5}exit {:<5}{:<9}{}".format(
            no, beklenen, olculen, "OK" if gecti else "KIRMIZI", aciklama[:36]))
    print("-" * 74)
    if basarisiz:
        print("SONUC: %d/%d gecti — KIRMIZI:" % (len(VAKALAR) - len(basarisiz), len(VAKALAR)))
        for no, b, o, a in basarisiz:
            print("  vaka %d: beklenen=exit%d olculen=exit%d (%s)" % (no, b, o, a))
        return 1
    print("SONUC: %d/%d vaka GECTI." % (len(VAKALAR), len(VAKALAR)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
