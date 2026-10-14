#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kosucu-gecici-agac-test.py — foto kosucusu gecici-agac sarmalayicisinin kabul testi.

IZOLE: sahte bare repo + GERIDE ve KIRLI sahte ana checkout + sahte kosucu. GERCEK ev
yoluna hicbir yazim/silme YOK (PRUVO_KOSUCU_ANA / _D_KOK env override).

Kurulum, canli arizanin (14 Eki 2026) birebir modelidir: ana checkout origin/main'in
GERISINDE (v1 commit'li) ve calisma agaci KIRLI (v2), origin/main ise IKINCI bir
klondan push'lanmis v3'tur. Dogru sarmalayici v3'u kosar.

IDDIALAR:
  I1 origin/main'deki surum (v3) kosar — ne ana HEAD (v1) ne kirli agac (v2)
  I2 cikista gecici dizin YOK + log satirinda AGAC=... SILINDI=<n>KB
  I3 ic rc (4) disari aynen gecer
  I4 --log ic kosucuya da GECER (kosucunun HAL= satiri log'a dusmeye devam eder)

MUTASYON KANITI (sarmalayicinin KOPYASINA delik acilir; listelenen iddia KIRMIZI olmali,
sabit "OLDU" satiri BASILMAZ — her mutant KOSTURULUR):
  M1 archive origin/main yerine HEAD          -> I1
  M2 kosucu ana checkout'tan calistirilir      -> I1
  M3 fetch yapilmaz (bayat origin/main)        -> I1
  M4 cikista rm -rf yok                        -> I2
  M5 ic rc yutulur                             -> I3
  M6 --log ic kosucudan sokulur                -> I4
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from git_ortami import sentetik_git  # noqa: E402

WRAPPER = Path(__file__).resolve().parent / "kosucu-gecici-agac.sh"


def _mock(etiket):
    # --log <yol> verilirse oraya "HAL=MOCK <etiket>" ekler; MOCK_RC env ile rc verir.
    return (
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "a = sys.argv[1:]\n"
        "if '--log' in a:\n"
        "    with open(a[a.index('--log') + 1], 'a') as f:\n"
        "        f.write('HAL=MOCK %s\\n')\n"
        "print('SURUM=%s')\n"
        "sys.exit(int(os.environ.get('MOCK_RC', '0')))\n" % (etiket, etiket)
    ).encode()


def _git(kok, *args):
    sentetik_git(str(kok), *args, check=True, capture_output=True, text=True)


def _kur(kok):
    bare = kok / "bare.git"
    bare.mkdir()
    _git(bare, "init", "-q", "--bare", "--initial-branch=main")
    ana = kok / "ana"
    (ana / "tools").mkdir(parents=True)
    (ana / "tools" / "foto-uretec-kosucu.py").write_bytes(_mock("v1"))
    _git(ana, "init", "-q", "-b", "main")
    _git(ana, "config", "user.name", "t")
    _git(ana, "config", "user.email", "t@example.invalid")
    _git(ana, "add", ".")
    _git(ana, "commit", "-q", "-m", "v1")
    _git(ana, "remote", "add", "origin", str(bare))
    _git(ana, "push", "-q", "origin", "main")
    # ikinci klon origin/main'i v3'e ilerletir; ana checkout GERIDE kalir
    klon = kok / "klon"
    _git(kok, "clone", "-q", str(bare), str(klon))
    _git(klon, "config", "user.name", "t")
    _git(klon, "config", "user.email", "t@example.invalid")
    (klon / "tools" / "foto-uretec-kosucu.py").write_bytes(_mock("v3"))
    _git(klon, "commit", "-q", "-am", "v3")
    _git(klon, "push", "-q", "origin", "main")
    # ana checkout KIRLI (commit'siz v2)
    (ana / "tools" / "foto-uretec-kosucu.py").write_bytes(_mock("v2"))
    return ana


def _kos(wrapper, ana, tmp, log, rc=None):
    env = dict(os.environ, PRUVO_KOSUCU_ANA=str(ana), PRUVO_KOSUCU_D_KOK=str(tmp),
               PRUVO_KOSUCU_D_DESEN="gecici-XXXXXX")
    if rc is not None:
        env["MOCK_RC"] = str(rc)
    return subprocess.run(["bash", str(wrapper), "--uygula", "--log", str(log)],
                          capture_output=True, text=True, env=env)


def iddialari_kos(wrapper):
    """{etiket: (gecti, ayrinti)} — her cagri kendi izole kokunu kurar ve siler."""
    kok = Path(tempfile.mkdtemp(prefix="pruvo-kosucu-test-"))
    try:
        ana = _kur(kok)
        tmp = kok / "tmp"
        tmp.mkdir()
        log = kok / "kosucu.log"
        s = {}
        p = _kos(wrapper, ana, tmp, log)
        s["I1"] = ("SURUM=v3" in p.stdout and p.returncode == 0, p.stdout.strip() + p.stderr.strip())
        satirlar = log.read_text().splitlines() if log.exists() else []
        agac = [x for x in satirlar if "AGAC=" in x]
        son = agac[-1] if agac else ""
        yol = son.split("AGAC=", 1)[1].split(" ", 1)[0] if son else ""
        s["I2"] = (bool(yol) and "SILINDI=" in son and "KB" in son and not Path(yol).exists()
                   and not any(tmp.iterdir()), son)
        s["I4"] = (any(x.startswith("HAL=MOCK") for x in satirlar), "log=%r" % satirlar)
        p4 = _kos(wrapper, ana, tmp, log, rc=4)
        s["I3"] = (p4.returncode == 4, "rc=%d" % p4.returncode)
        return s
    finally:
        shutil.rmtree(kok, ignore_errors=True)


MUTANTLAR = [
    ("M1 archive origin/main yerine HEAD",
     [('archive "$SHA"', 'archive HEAD')], ["I1"]),
    ("M2 kosucu ana checkout'tan calistirilir",
     [('python3 "$D/tools/', 'python3 "$ANA_KOK/tools/'),
      ('python3 "$D/tools/', 'python3 "$ANA_KOK/tools/')], ["I1"]),
    ("M3 fetch yapilmaz (bayat origin/main)",
     [('fetch -q origin main', 'fetch -q origin YOK-DAL')], ["I1"]),
    ("M4 cikista gecici dizin silinmez",
     [('        rm -rf "$D"\n', '')], ["I2"]),
    ("M5 ic rc yutulur",
     [('exit $RC', 'exit 0')], ["I3"]),
    ("M6 --log ic kosucudan sokulur",
     [('        ARGS+=("$1" "$2")\n', '')], ["I4"]),
]


def mutant_kos(yama, beklenen):
    kaynak = WRAPPER.read_text()
    for bul, koy in yama:
        if bul not in kaynak:
            return False, "MUTASYON UYGULANAMADI: %r" % bul
        kaynak = kaynak.replace(bul, koy, 1)
    d = Path(tempfile.mkdtemp(prefix="pruvo-kosucu-mutant-"))
    try:
        kopya = d / "kosucu-gecici-agac.sh"
        kopya.write_text(kaynak)
        s = iddialari_kos(kopya)
        hayatta = [e for e in beklenen if s[e][0]]
        return not hayatta, ("hayatta: %s" % ",".join(hayatta)) if hayatta else "kirmizi: %s" % ",".join(beklenen)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    s = iddialari_kos(WRAPPER)
    gecen = 0
    for e in ("I1", "I2", "I3", "I4"):
        gecti, ayrinti = s[e]
        gecen += int(gecti)
        print("%s %s%s" % ("GECTI" if gecti else "KALDI", e, "" if gecti else " — " + ayrinti))
    print("SONUC %d/4" % gecen)
    if gecen != 4:
        print("MUTASYON ATLANDI: taban kirmizi (kirmizi tabanda mutant olumu kanit degildir)")
        return 1
    olen = 0
    for ad, yama, beklenen in MUTANTLAR:
        oldu, ayrinti = mutant_kos(yama, beklenen)
        olen += int(oldu)
        print("%s %s (%s)" % ("OLDU  " if oldu else "KALDI ", ad, ayrinti))
    print("MUTANT %d/%d OLDU" % (olen, len(MUTANTLAR)))
    return 0 if olen == len(MUTANTLAR) else 1


if __name__ == "__main__":
    sys.exit(main())
