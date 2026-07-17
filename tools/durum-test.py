#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DURUM PANOSU KABUL TESTLERI — tools/paket-durum-panosu.md'deki 5 madde.

    python3 tools/durum-test.py

Testler GECICI repo kurar (tempfile + git init) — GERCEK repoda dal acilmaz/silinmez
(guard katmani + eszamanli oturumlar bozulmasin). Tek istisna madde 5: gercek repoda
durum.py'yi SALT-OKUNUR kosar ve `git status --porcelain`in oncesi/sonrasi ayni
kaldigini kanitlar.

  1. Ucu main'de olan dal        -> "icerigi main'de" sinifi (ucu-main-de)
  2. SQUASH-MERGE edilmis dal    -> yine "icerigi main'de"  <-- ASIL RISK
     `git branch --merged` bunu KACIRIR; test bunu ayrica kanitlar (2b).
  3. Gercekten bitmemis dal      -> "devam ediyor"
  4. Aktif worktree'si olan dal  -> "artik dal" listesine DUSMEZ
  5. durum.py gercek repoda exit 0 + repo durumunu DEGISTIRMIYOR
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import durum  # noqa: E402

SONUC = []


def kayit(no, ad, gecti, detay=""):
    SONUC.append((no, ad, gecti))
    print("  %s TEST %s — %s%s" % ("✅" if gecti else "❌", no, ad,
                                   (" | " + detay) if detay else ""), flush=True)


def kos(repo, *args):
    p = subprocess.run(["git", "-C", repo] + list(args),
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("git %s -> %s" % (" ".join(args), p.stderr.strip()))
    return p.stdout.strip()


def yaz(repo, ad, icerik):
    with open(os.path.join(repo, ad), "w") as f:
        f.write(icerik)


def sahne_kur(tmp):
    """Dort dalli gecici repo: ucu-merged, squash-merged, bitmemis, worktree'li."""
    repo = os.path.join(tmp, "repo")
    os.makedirs(repo)
    kos(repo, "init", "-q", "-b", "main")
    kos(repo, "config", "user.email", "test@example.invalid")
    kos(repo, "config", "user.name", "durum-test")
    yaz(repo, "a.txt", "taban\n")
    kos(repo, "add", "-A")
    kos(repo, "commit", "-q", "-m", "taban")

    # (1) ucu main'de olan dal: normal (fast-forward olmayan) merge
    kos(repo, "checkout", "-q", "-b", "dal-uc-merged")
    yaz(repo, "b.txt", "uc\n")
    kos(repo, "add", "-A")
    kos(repo, "commit", "-q", "-m", "uc dal isi")
    kos(repo, "checkout", "-q", "main")
    kos(repo, "merge", "-q", "--no-ff", "-m", "merge: uc", "dal-uc-merged")

    # (2) squash-merge: dalda UC commit, main'de TEK commit
    #     -> dal ucu main'in atasi DEGIL, tek tek patch-id'ler de TUTMAZ.
    kos(repo, "checkout", "-q", "-b", "dal-squash")
    yaz(repo, "c.txt", "birinci\n")
    kos(repo, "add", "-A")
    kos(repo, "commit", "-q", "-m", "squash isi 1")
    yaz(repo, "c.txt", "birinci\nikinci\n")
    kos(repo, "add", "-A")
    kos(repo, "commit", "-q", "-m", "squash isi 2")
    yaz(repo, "d.txt", "ucuncu\n")
    kos(repo, "add", "-A")
    kos(repo, "commit", "-q", "-m", "squash isi 3")
    kos(repo, "checkout", "-q", "main")
    kos(repo, "merge", "-q", "--squash", "dal-squash")
    kos(repo, "commit", "-q", "-m", "squash merge: dal-squash (3 commit tek committe)")

    # main baska bir isle ilerlesin (gercek hayat: merge sonrasi main durmuyor)
    yaz(repo, "e.txt", "main devam\n")
    kos(repo, "add", "-A")
    kos(repo, "commit", "-q", "-m", "main: alakasiz is")

    # (3) gercekten bitmemis dal
    kos(repo, "checkout", "-q", "-b", "dal-devam", "main")
    yaz(repo, "f.txt", "yarim is\n")
    kos(repo, "add", "-A")
    kos(repo, "commit", "-q", "-m", "yarim is")
    kos(repo, "checkout", "-q", "main")

    # (4) worktree'si olan, icerigi main'de olan dal (artik listesine DUSMEMELI)
    kos(repo, "checkout", "-q", "-b", "dal-worktreeli")
    yaz(repo, "g.txt", "wt\n")
    kos(repo, "add", "-A")
    kos(repo, "commit", "-q", "-m", "wt isi")
    kos(repo, "checkout", "-q", "main")
    kos(repo, "merge", "-q", "--no-ff", "-m", "merge: wt", "dal-worktreeli")
    kos(repo, "worktree", "add", "-q", os.path.join(tmp, "wt"), "dal-worktreeli")
    return repo


def test_1_2_3(repo):
    s1 = durum.dal_sinifi(repo, "dal-uc-merged")
    kayit(1, "ucu main'de olan dal -> icerigi main'de",
          s1 in ("ucu-main-de", "icerigi-main-de"), "sinif=%s" % s1)

    s2 = durum.dal_sinifi(repo, "dal-squash")
    kayit(2, "SQUASH-MERGE edilmis dal -> icerigi main'de",
          s2 in ("ucu-main-de", "icerigi-main-de"), "sinif=%s" % s2)

    # 2b: `git branch --merged` bu dali KACIRIYOR mu? Kacirmiyorsa test 2 anlamsiz
    #     olur (tuzak yeniden uretilememis demektir) -> bilerek dogruluyoruz.
    merged = kos(repo, "branch", "--merged", "main", "--format=%(refname:short)").splitlines()
    kayit("2b", "tuzak gercek: `git branch --merged` squash dali KACIRIYOR",
          "dal-squash" not in merged, "--merged listesi=%s" % merged)

    s3 = durum.dal_sinifi(repo, "dal-devam")
    kayit(3, "bitmemis dal -> devam ediyor", s3 == "devam", "sinif=%s" % s3)


def test_4(repo, tmp):
    wt_dallari = set(w["dal"] for w in durum.worktreeler(repo) if w["dal"])
    dallar = [d for d in durum.yerel_dallar(repo) if d != "main"]
    artik = [d for d in dallar
             if durum.dal_sinifi(repo, d) != "devam" and d not in wt_dallari]
    kayit(4, "aktif worktree'li dal ARTIK listesine dusmuyor",
          "dal-worktreeli" not in artik and "dal-worktreeli" in wt_dallari,
          "artik=%s" % artik)


def test_5():
    once = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"],
                          capture_output=True, text=True).stdout
    p = subprocess.run([sys.executable, os.path.join(TOOLS, "durum.py")],
                       capture_output=True, text=True)
    sonra = subprocess.run(["git", "-C", ROOT, "status", "--porcelain"],
                           capture_output=True, text=True).stdout
    kayit(5, "gercek repoda exit 0 + repo durumu DEGISMEDI",
          p.returncode == 0 and once == sonra,
          "exit=%d, durum ayni=%s" % (p.returncode, once == sonra))
    if p.returncode != 0:
        print(p.stderr[:600])
    return p.stdout


def test_sizinti(cikti):
    """Repo PUBLIC + cikti yerelde okunuyor -> uc ayri sizinti kapisi.

    NOT: "cikti icinde 'secret' kelimesi geciyor mu" diye BAKMIYORUZ — ilk
    surumde oyleydi ve YANLIS ALARM verdi: gercek bir commit basligi
    ("...yukle.py artik secret...") kelimeyi masumca iceriyordu. Kelime degil
    SIR DEGERI ve SIR OKUMA aranir.
    """
    # (a) statik: durum.py sir dosyalarina hic dokunmuyor
    with open(os.path.join(TOOLS, "durum.py")) as f:
        kaynak = f.read()
    dokunulan = [ad for ad in (".r2-credentials", ".urun-kaynaklari", ".env",
                               "wrangler.toml", "credentials")
                 if ad in kaynak]
    kayit("6a", "durum.py sir dosyasi OKUMUYOR (statik)", not dokunulan,
          "gecen ad=%s" % dokunulan)

    # (b) sir DEGERLERI ciktida gecmiyor (deger asla basilmaz, sadece sayi)
    sirlar = []
    # Sir dosyalari gitignore'da: worktree'de DEGIL, ANA repo kokunde durur.
    # (Ilk surum ROOT'a bakti -> 0 aday buldu -> test BOSA gecti. Bos gecen test
    #  test degildir; ana repo koku alinir.)
    sir_kok = durum.ana_repo(ROOT)
    for ad in (".r2-credentials.json", ".urun-kaynaklari.json"):
        yol = os.path.join(sir_kok, ad)
        if not os.path.isfile(yol):
            continue
        try:
            with open(yol, errors="replace") as f:
                veri = json.load(f)
        except (ValueError, OSError):
            continue
        yigin = [veri]
        while yigin:
            o = yigin.pop()
            if isinstance(o, dict):
                yigin.extend(o.values())
            elif isinstance(o, list):
                yigin.extend(o)
            elif isinstance(o, str) and len(o) >= 12:
                sirlar.append(o)
    sizan = sum(1 for s in sirlar if s in cikti)
    kayit("6b", "sir DEGERI ciktida yok (deger basilmaz)", sizan == 0,
          "%d aday deger tarandi, %d sizinti" % (len(sirlar), sizan))

    # (c) kimlik-bicimli dizgi (IBAN / uzun anahtar / telefon) ciktida yok
    desenler = {
        "IBAN": r"TR\d{24}",
        "uzun-anahtar": r"\b[A-Za-z0-9/+]{40,}\b",
        "telefon": r"\b(?:90|\+90)?5\d{9}\b",
    }
    yakalanan = [ad for ad, d in desenler.items() if re.search(d, cikti)]
    kayit("6c", "ciktida kimlik-bicimli dizgi yok", not yakalanan,
          "yakalanan=%s" % yakalanan)


def main():
    print("\nDURUM PANOSU KABUL TESTLERI (gecici repo — gercek repoya dokunulmaz)\n")
    tmp = tempfile.mkdtemp(prefix="durum-test-")
    try:
        repo = sahne_kur(tmp)
        test_1_2_3(repo)
        test_4(repo, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    cikti = test_5()
    test_sizinti(cikti)

    basarisiz = [s for s in SONUC if not s[2]]
    print("\n%s  %d/%d test gecti\n"
          % ("✅ HEPSI YESIL" if not basarisiz else "❌ KIRMIZI",
             len(SONUC) - len(basarisiz), len(SONUC)))
    return 1 if basarisiz else 0


if __name__ == "__main__":
    sys.exit(main())
