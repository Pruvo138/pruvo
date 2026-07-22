#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kabul testi: tools/mimar-commit-kapisi.py (daraltilmis worker bypass).

Kapiyi --stdin/--toplevel ile ANA-REPO kosullarinda sinar; GERCEK ana checkout'a
DOKUNMAZ (yalniz sentetik staged listesi + env verilir). Dogrulanan yeni davranis:

  - PRUVO_MIMAR_ONAY=worker + staged YALNIZ veri (urunler.json/.urun-kaynaklari.json)
      -> exit 0   (urun-ekleme hatti korunur; MaCiT'in sahasi)
      T3 (22 Tem): log kategorisi 'veri-duzlemi-gecis' (allow-escape DEGIL) —
      mesru veri partisi escape muhasebesini kirletmez.
  - PRUVO_MIMAR_ONAY=worker + staged'de HERHANGI kaynak dosyasi (.py/.js/... )
      -> exit 1   (worker onayi KAYNAGI ACMAZ; kaynak isi worktree'de commit'lenir)
  - PRUVO_MIMAR_ONAY=worker + staged bos YA DA veri-disi dosya iceriyor
      -> exit 0 AMA log 'allow-escape' (gercek istisna gurultulu KALIR)
  - env yok: kaynak+veri bloklanir (exit 1); .md serbest (exit 0)  [bugunku davranis]
  - --toplevel worktree yolu -> exit 0 (worktree muafiyeti, env'den bagimsiz)

VAKA 4 = ONCE-KIRMIZI TANIGI: bypass daraltilmadan onceki surumde exit 0 idi;
daraltmadan sonra exit 1. Ayni test dosyasi eski gate yoluyla cagirilirsa (argv[1])
bu vaka KIRMIZI yanar -> mutasyon kaniti.
VAKA 1-3 = T3 ONCE-KIRMIZI TANIKLARI: eski gate veri-duzlemi commit'ini
'allow-escape' diye loglardi; log beklentisi 'veri-duzlemi-gecis' oldugu icin
eski gate ile KIRMIZI yanarlar. VAKA 16-17 = genisletme nobetcileri: gecis yolu
veri-disi dosyaya genisletilirse (or. 'her staged' -> 'en az bir veri') KIRMIZI.

Kullanim:
    python3 tools/mimar-commit-kapisi-test.py                 # kardes gate (bu worktree)
    python3 tools/mimar-commit-kapisi-test.py /yol/eski-gate.py   # once-kirmizi olcumu

Cikis kodu 0 = hepsi gecti, 1 = en az bir vaka kirmizi.
"""
import os
import subprocess
import sys
import tempfile

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
    (16, 0, True,  MAIN, ["notlar/olcum.txt"],
     "worker + veri-DISI dosya -> ACIK ama allow-escape (gurultu korunur)"),
    (17, 0, True,  MAIN, ["urunler.json", "notlar/olcum.txt"],
     "worker + veri+not KARISIK -> ACIK ama allow-escape (gecis SAF veri icin)"),
]

# T3 LOG MUHASEBESI — no -> (log'da OLMASI gereken karar, OLMAMASI gereken karar).
# Sadece exit kodu yetmez: gecis yolunun SINIFLANDIRMASI da kabuldur. Bu tablo
# ayni zamanda genisletme mutasyonunun (gecis kosulu 'her staged veri' ->
# 'en az bir veri' / 'kosulsuz') nobetcisidir: 14/16/17 o durumda KIRMIZI yanar.
LOG_BEKLENTISI = {
    1: ("veri-duzlemi-gecis", "allow-escape"),
    2: ("veri-duzlemi-gecis", "allow-escape"),
    3: ("veri-duzlemi-gecis", "allow-escape"),
    14: ("allow-escape", "veri-duzlemi-gecis"),
    16: ("allow-escape", "veri-duzlemi-gecis"),
    17: ("allow-escape", "veri-duzlemi-gecis"),
}


def kostur(worker, toplevel, satirlar):
    """Kapiyi VAKAYA OZEL gecici --gitdir ile kosturur; (exit, log_icerigi) doner.
    Gecici gitdir sayesinde log denetimi hermetiktir — gercek .git'e yazilmaz ve
    vakalar birbirinin kaydini gormez."""
    gitdir = tempfile.mkdtemp(prefix="kapi-test-gd-")
    ortam = dict(os.environ)
    ortam.pop("PRUVO_MIMAR_ONAY", None)
    if worker:
        ortam["PRUVO_MIMAR_ONAY"] = "worker"
    sonuc = subprocess.run(
        [sys.executable, GATE, "--stdin", "--toplevel", toplevel, "--gitdir", gitdir],
        input="".join(s + "\n" for s in satirlar),
        capture_output=True, text=True, env=ortam,
    )
    log_icerigi = ""
    log_yolu = os.path.join(gitdir, "pruvo-kapi-log.jsonl")
    try:
        with open(log_yolu, encoding="utf-8") as f:
            log_icerigi = f.read()
    except OSError:
        log_icerigi = ""
    return sonuc.returncode, log_icerigi


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
        olculen, log_icerigi = kostur(worker, toplevel, satirlar)
        gecti = (olculen == beklenen)
        # T3: exit yetmez — log SINIFLANDIRMASI da kabul kosulu (beklenen kategori
        # VAR + yasak kategori YOK). Eski gate ile 1-3 burada KIRMIZI yanar.
        if gecti and no in LOG_BEKLENTISI:
            olmali, olmamali = LOG_BEKLENTISI[no]
            log_ok = (olmali in log_icerigi) and (olmamali not in log_icerigi)
            if not log_ok:
                gecti = False
                aciklama = aciklama + " [log: +%s -%s bekleniyordu; olculen: %s]" % (
                    olmali, olmamali, (log_icerigi.strip().replace("\n", " | ") or "(bos)"))
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
