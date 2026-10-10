#!/usr/bin/env python3
"""Wrangler debug-log nobetcisi — `~/.wrangler/logs` birikimini OLCER ve (istenirse) BUDAR.

NEDEN (9 Eki 2026, BaBa teftisi + KraL-WranglerLog olcumu): `~/.wrangler/logs` 2,5 gunde
3,1 GB / 11.427 dosyaya cikti. Wrangler her cagrida `wrangler-<UTC zaman>.log` yazar ve
yalniz 30 GUNDEN eski dosyayi kendisi siler (4.149.0 `cleanupOldLogFiles`). Okan kurali
(13 Agu, USTUN): makinede iz birakma — log GECICI siniftir. Kaynakta kapatma
`WRANGLER_WRITE_LOGS=false` (bkz. `tools/d1-sync.py::WRANGLER_LOG_KAPALI`); bu nobetci
kapatilmamis kalan cagiranlarin birikimini sinirlar ve esik asilinca KIRMIZI basar.

Kullanim:
  python3 tools/wrangler-log-nobetcisi.py                 # yalniz olc
  python3 tools/wrangler-log-nobetcisi.py --budama        # eski + kapali dosyalari sil, sonra olc
  [--dizin D] [--esik-bayt N] [--esik-dosya N] [--yas-dk N] [--lsof YOL]

Cikis: 0 YESIL · 1 KIRMIZI (esik asildi) · 2 OLCULEMEDI (dizin okunamadi / lsof yok /
guvensiz dizin). Budama YALNIZ su dosyalari siler: adi `LOG_ADI` kalibina birebir uyan,
sembolik bag OLMAYAN duz dosya, son yazimi `--yas-dk` dakikadan eski ve hicbir surecin
ACIK tuttugu dosya degil. Alt dizine inmez, dizin silmez. lsof calismazsa HICBIR sey
silinmez (fail-closed).
"""
import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
import time

VARSAYILAN_DIZIN = os.path.expanduser("~/.wrangler/logs")
ESIK_BAYT = 50 * 1024 * 1024      # kabul: `du -sh ~/.wrangler/logs` <= 50 MB
ESIK_DOSYA = 2000                 # olculen tabanda saatte ~150 dosya; budama 60 dk'da bir
YAS_DK = 60                       # bundan taze dosya YAZILIYOR olabilir -> dokunulmaz
LOG_ADI = re.compile(r"^wrangler-\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_\d{3}\.log$")
LSOF_ADAYLARI = ("/usr/sbin/lsof", "/usr/bin/lsof")


def olc(dizin):
    """(dosya_sayisi, bayt) — yalniz dizinin dogrudan icindeki duz dosyalar."""
    n = b = 0
    with os.scandir(dizin) as it:
        for g in it:
            if g.is_file(follow_symlinks=False):
                n += 1
                b += g.stat(follow_symlinks=False).st_size
    return n, b


def acik_dosyalar(dizin, lsof):
    """Dizinde herhangi bir surecin acik tuttugu dosyalarin TAM yollari. None = olculemedi."""
    # `+d` = yalniz dizinin dogrudan icerigi (budama da alt dizine inmez); `+D`'nin
    # ozyinelemeli taramasi olculen 11k dosyalik dizinde gereksiz yavasti.
    try:
        r = subprocess.run([lsof, "-Fn", "+d", os.path.realpath(dizin)], capture_output=True,
                           text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    # rc=1: eslesme yok YA DA bazi sureclerin dosyalari okunamadi (kismi uyari); ikisinde de
    # stdout'taki eslesmeler gecerlidir. Baska her rc olculemedi demektir.
    if r.returncode not in (0, 1):
        return None
    return {s[1:] for s in r.stdout.splitlines() if s.startswith("n")}


def guvenli_dizin_mi(dizin):
    gercek = os.path.realpath(dizin)
    yasak = {"/", os.path.realpath(os.path.expanduser("~"))}
    return gercek not in yasak and os.path.basename(gercek) != ""


def buda(dizin, yas_dk, lsof):
    """(budanan, korunan_acik, korunan_taze) ya da None (olculemedi -> hicbir sey silinmedi)."""
    acik = acik_dosyalar(dizin, lsof)
    if acik is None:
        return None
    sinir = time.time() - yas_dk * 60
    budanan = korunan_acik = korunan_taze = 0
    with os.scandir(dizin) as it:
        adaylar = list(it)
    for g in adaylar:
        if not LOG_ADI.match(g.name):
            continue
        st = os.lstat(g.path)
        if not stat.S_ISREG(st.st_mode):
            continue
        if st.st_mtime > sinir:
            korunan_taze += 1
            continue
        if os.path.realpath(g.path) in acik or g.path in acik:
            korunan_acik += 1
            continue
        try:
            os.unlink(g.path)
            budanan += 1
        except FileNotFoundError:
            pass
    return budanan, korunan_acik, korunan_taze


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dizin", default=VARSAYILAN_DIZIN)
    ap.add_argument("--esik-bayt", type=int, default=ESIK_BAYT)
    ap.add_argument("--esik-dosya", type=int, default=ESIK_DOSYA)
    ap.add_argument("--yas-dk", type=int, default=YAS_DK)
    ap.add_argument("--budama", action="store_true")
    ap.add_argument("--lsof", default=None)
    a = ap.parse_args(argv)

    if not os.path.isdir(a.dizin):
        print("WRANGLER_LOG DIZIN=%s DIZIN_YOK DOSYA=0 BAYT=0 HAL=YESIL" % a.dizin)
        return 0
    if not guvenli_dizin_mi(a.dizin):
        print("WRANGLER_LOG DIZIN=%s GUVENSIZ_DIZIN HAL=OLCULEMEDI" % a.dizin)
        return 2

    if a.budama:
        lsof = a.lsof or next((y for y in LSOF_ADAYLARI if os.path.exists(y)), None) \
            or shutil.which("lsof")
        sonuc = buda(a.dizin, a.yas_dk, lsof) if lsof else None
        if sonuc is None:
            print("WRANGLER_LOG BUDAMA=OLCULEMEDI (lsof=%s) — hicbir dosya silinmedi" % lsof)
            print("WRANGLER_LOG DIZIN=%s HAL=OLCULEMEDI" % a.dizin)
            return 2
        print("WRANGLER_LOG BUDANAN=%d KORUNAN_ACIK=%d KORUNAN_TAZE=%d YAS_DK=%d"
              % (sonuc + (a.yas_dk,)))

    try:
        n, b = olc(a.dizin)
    except OSError as e:
        print("WRANGLER_LOG DIZIN=%s OKUNAMADI (%s) HAL=OLCULEMEDI" % (a.dizin, e))
        return 2
    kirmizi = []
    if b > a.esik_bayt:
        kirmizi.append("BAYT")
    if n > a.esik_dosya:
        kirmizi.append("DOSYA")
    hal = "KIRMIZI" if kirmizi else "YESIL"
    print("WRANGLER_LOG DIZIN=%s DOSYA=%d BAYT=%d ESIK_DOSYA=%d ESIK_BAYT=%d HAL=%s%s"
          % (a.dizin, n, b, a.esik_dosya, a.esik_bayt, hal,
             (" ASAN=" + ",".join(kirmizi)) if kirmizi else ""))
    return 1 if kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())
