#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CURUTME 03 — EKSEN 7: "bayrak KAPALI iken artefakt FAZ 2 oncesi v2 ile BAYT ES" iddiasi.

Iddia kaynagi: tools/build.py OZET_TEMSIL_SURUM yorumu + paket-ozet-butce.md FAZ 2b
("artefakt v2, bayragin oncesiyle BAYT BAYT ayni").

Yordam (bagimsiz yeniden uretim):
  1. TABAN build.py = `git show <taban>:tools/build.py` -> tools/_curut-taban-build.py
     (ROOT kendi konumundan turedigi icin tools/ icinde durmali)
  2. Iki koda da AYNI katalogu ver, ozet uret, BAYT karsilastir.
  3. Temizlik: taban kopya silinir.
Cikis: 0 = bayt es · 1 = ayrisma · 2 = OLCULEMEDI.
"""
import hashlib
import os
import subprocess
import sys
import tempfile

TABAN_COMMIT = "19635ab7"
KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOLS = os.path.join(KOK, "tools")
TABAN_YOL = os.path.join(TOOLS, "_curut-taban-build.py")
KATALOG = os.path.join(KOK, "urunler.json")


def uret(build_yol, cikti, ek=None):
    argv = ["python3", build_yol, "--sadece-ozet", "--katalog", KATALOG, "--cikti", cikti]
    if ek:
        argv += ek
    r = subprocess.run(argv, capture_output=True, text=True)
    return r


def sha(yol):
    with open(yol, "rb") as f:
        h = f.read()
    return len(h), hashlib.sha256(h).hexdigest()[:16]


def main():
    r = subprocess.run(["git", "-C", KOK, "show", "%s:tools/build.py" % TABAN_COMMIT],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("OLCULEMEDI: taban build.py alinamadi: %s" % r.stderr.strip()[:200])
        return 2
    with open(TABAN_YOL, "w", encoding="utf-8") as f:
        f.write(r.stdout)
    gec = tempfile.mkdtemp(prefix="curut-bayt-")
    try:
        taban_cikti = os.path.join(gec, "taban-ozet.json")
        yeni_cikti = os.path.join(gec, "yeni-ozet.json")
        r1 = uret(TABAN_YOL, taban_cikti)
        if r1.returncode != 0:
            print("OLCULEMEDI: TABAN build.py rc=%d -> %s"
                  % (r1.returncode, (r1.stderr or r1.stdout).strip()[-300:]))
            return 2
        r2 = uret(os.path.join(TOOLS, "build.py"), yeni_cikti)
        if r2.returncode != 0:
            print("OLCULEMEDI: GUNCEL build.py rc=%d -> %s"
                  % (r2.returncode, (r2.stderr or r2.stdout).strip()[-300:]))
            return 2
        tb, th = sha(taban_cikti)
        yb, yh = sha(yeni_cikti)
        print("TABAN  (%s) : %d B  sha=%s" % (TABAN_COMMIT, tb, th))
        print("GUNCEL (bayrak varsayilani) : %d B  sha=%s" % (yb, yh))
        # Ayrica v3 kolu:
        v3_cikti = os.path.join(gec, "v3-ozet.json")
        r3 = uret(os.path.join(TOOLS, "build.py"), v3_cikti, ["--ozet-surum", "3"])
        if r3.returncode == 0:
            vb, vh = sha(v3_cikti)
            print("GUNCEL --ozet-surum 3      : %d B  sha=%s  (kazanc %d B, %%%.1f)"
                  % (vb, vh, yb - vb, 100.0 * (yb - vb) / yb))
        if (tb, th) == (yb, yh):
            print("\nHUKUM: BAYT ES ✔ — bayrak KAPALI iken artefakt FAZ 2 oncesiyle AYNI.")
            return 0
        r4 = subprocess.run(["cmp", taban_cikti, yeni_cikti], capture_output=True, text=True)
        print("\nHUKUM: AYRISMA ✘ — %s" % (r4.stdout or r4.stderr).strip()[:300])
        return 1
    finally:
        try:
            os.remove(TABAN_YOL)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
