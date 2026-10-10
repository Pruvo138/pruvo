#!/usr/bin/env python3
"""Kabul bataryasi — `tools/wrangler-log-nobetcisi.py` (vaka + mutant).

HERMETIK: her vaka `tempfile.TemporaryDirectory()` altinda SENTETIK bir `logs` dizini kurar;
gercek `~/.wrangler/logs`'a ne okur ne yazar (arac her cagrida `--dizin <gecici>` alir).
Mutantlar aracin IZOLE kopyasinda (gecici dizin) yasar; canli govdeye dokunulmaz.
Her mutant capasinin kaynakta BIREBIR bulundugu once dogrulanir (capa kayarsa mutant
sessizce kimligini yitirmesin). Cikis: 0 = tum vakalar yesil + tum mutantlar OLDU.
"""
import os
import subprocess
import sys
import tempfile
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "wrangler-log-nobetcisi.py")
ESKI = time.time() - 3 * 3600          # 3 saat once
AD = "wrangler-2026-10-09_%02d-00-00_000.log"


def _yaz(yol, bayt=10, mtime=ESKI):
    with open(yol, "wb") as f:
        f.write(b"x" * bayt)
    os.utime(yol, (mtime, mtime))


def _kos(arac, *argv):
    r = subprocess.run([sys.executable, arac] + list(argv), capture_output=True, text=True,
                       timeout=180)
    return r.returncode, r.stdout + r.stderr


def v_bos(arac, t):
    d = os.path.join(t, "logs"); os.mkdir(d)
    rc, o = _kos(arac, "--dizin", d)
    return rc == 0 and "HAL=YESIL" in o and "DOSYA=0" in o, (rc, o)


def v_dizin_yok(arac, t):
    rc, o = _kos(arac, "--dizin", os.path.join(t, "var-olmayan", "logs"))
    return rc == 0 and "DIZIN_YOK" in o, (rc, o)


def v_bayt_esik(arac, t):
    d = os.path.join(t, "logs"); os.mkdir(d)
    _yaz(os.path.join(d, AD % 1), bayt=2048)
    rc, o = _kos(arac, "--dizin", d, "--esik-bayt", "1000")
    rc2, o2 = _kos(arac, "--dizin", d, "--esik-bayt", "4096")
    return (rc == 1 and "ASAN=BAYT" in o and rc2 == 0), (rc, o, rc2, o2)


def v_dosya_esik(arac, t):
    d = os.path.join(t, "logs"); os.mkdir(d)
    for i in range(5):
        _yaz(os.path.join(d, AD % i))
    rc, o = _kos(arac, "--dizin", d, "--esik-dosya", "4")
    rc2, o2 = _kos(arac, "--dizin", d, "--esik-dosya", "5")
    return (rc == 1 and "ASAN=DOSYA" in o and rc2 == 0), (rc, o, rc2, o2)


def v_budama_secici(arac, t):
    """Eski+kalipli dosya SILINIR; taze, kalip-disi, sembolik bag, alt dizin KALIR."""
    d = os.path.join(t, "logs"); os.mkdir(d)
    disari = os.path.join(t, "disari.txt"); _yaz(disari)
    eski = os.path.join(d, AD % 1); _yaz(eski)
    taze = os.path.join(d, AD % 2); _yaz(taze, mtime=time.time())
    yabanci = os.path.join(d, "notlar.log"); _yaz(yabanci)
    bag = os.path.join(d, AD % 3); os.symlink(disari, bag)
    os.utime(bag, (ESKI, ESKI), follow_symlinks=False)   # yas kolu bagi tek basina korumasin
    alt = os.path.join(d, "alt"); os.mkdir(alt); _yaz(os.path.join(alt, AD % 4))
    rc, o = _kos(arac, "--dizin", d, "--budama")
    ok = (rc == 0 and not os.path.exists(eski) and os.path.exists(taze)
          and os.path.exists(yabanci) and os.path.islink(bag) and os.path.exists(disari)
          and os.path.exists(os.path.join(alt, AD % 4)) and "BUDANAN=1" in o)
    return ok, (rc, o, sorted(os.listdir(d)))


def v_budama_acik(arac, t):
    """Bir surecin ACIK tuttugu eski dosya silinmez (lsof)."""
    d = os.path.join(t, "logs"); os.mkdir(d)
    acik = os.path.join(d, AD % 5); _yaz(acik)
    kapali = os.path.join(d, AD % 6); _yaz(kapali)
    with open(acik, "rb"):
        rc, o = _kos(arac, "--dizin", d, "--budama")
    ok = rc == 0 and os.path.exists(acik) and not os.path.exists(kapali) and "KORUNAN_ACIK=1" in o
    return ok, (rc, o)


def v_lsof_yok(arac, t):
    """lsof calismazsa fail-closed: rc=2, HICBIR dosya silinmez."""
    d = os.path.join(t, "logs"); os.mkdir(d)
    eski = os.path.join(d, AD % 7); _yaz(eski)
    rc, o = _kos(arac, "--dizin", d, "--budama", "--lsof", os.path.join(t, "lsof-yok"))
    return rc == 2 and os.path.exists(eski) and "OLCULEMEDI" in o, (rc, o)


def v_budama_esik_alti(arac, t):
    """Esik ustundeki birikim budamayla esik altina iner -> rc 0."""
    d = os.path.join(t, "logs"); os.mkdir(d)
    for i in range(6):
        _yaz(os.path.join(d, AD % i), bayt=1000)
    rc0, o0 = _kos(arac, "--dizin", d, "--esik-bayt", "2000")
    rc, o = _kos(arac, "--dizin", d, "--esik-bayt", "2000", "--budama")
    return rc0 == 1 and rc == 0 and "DOSYA=0" in o, (rc0, o0, rc, o)


def v_guvensiz_dizin(arac, t):
    rc, o = _kos(arac, "--dizin", "/", "--budama")
    return rc == 2 and "GUVENSIZ_DIZIN" in o, (rc, o)


VAKALAR = [v_bos, v_dizin_yok, v_bayt_esik, v_dosya_esik, v_budama_secici, v_budama_acik,
           v_lsof_yok, v_budama_esik_alti, v_guvensiz_dizin]

# (ad, capa, yerine, oldurmesi beklenen vaka)
MUTANTLAR = [
    ("BAYT-KOR", "if b > a.esik_bayt:", "if False:", "v_bayt_esik"),
    ("DOSYA-KOR", "if n > a.esik_dosya:", "if False:", "v_dosya_esik"),
    ("KALIP-GEVSEK", "if not LOG_ADI.match(g.name):", "if False:", "v_budama_secici"),
    ("YAS-KOR", "if st.st_mtime > sinir:", "if False:", "v_budama_secici"),
    ("BAG-KOR", "if not stat.S_ISREG(st.st_mode):", "if False:", "v_budama_secici"),
    ("ACIK-KOR", "if os.path.realpath(g.path) in acik or g.path in acik:", "if False:",
     "v_budama_acik"),
    ("LSOF-FAIL-OPEN", "        return None\n    # rc=1:", "        return set()\n    # rc=1:",
     "v_lsof_yok"),
    ("GUVENLIK-KOR", "    if not guvenli_dizin_mi(a.dizin):", "    if False:", "v_guvensiz_dizin"),
    ("KIRMIZI-RC0", "return 1 if kirmizi else 0", "return 0", "v_bayt_esik"),
]


def vakalari_kos(arac):
    sonuc = {}
    for v in VAKALAR:
        with tempfile.TemporaryDirectory(prefix="wlog-test-") as t:
            ok, ayr = v(arac, t)
        sonuc[v.__name__] = (ok, ayr)
    return sonuc


def main():
    kirmizi = 0
    print("== VAKALAR (canli arac) ==")
    for ad, (ok, ayr) in vakalari_kos(ARAC).items():
        print("%-20s %s" % (ad, "YESIL" if ok else "KIRMIZI %r" % (ayr,)))
        kirmizi += 0 if ok else 1
    kaynak = open(ARAC, encoding="utf-8").read()
    print("== MUTANTLAR (izole kopya) ==")
    for ad, capa, yerine, hedef in MUTANTLAR:
        if kaynak.count(capa) != 1:
            print("%-16s CAPA-YOK (%d eslesme) -> KIRMIZI" % (ad, kaynak.count(capa)))
            kirmizi += 1
            continue
        with tempfile.TemporaryDirectory(prefix="wlog-mutant-") as m:
            kopya = os.path.join(m, "wrangler-log-nobetcisi.py")
            with open(kopya, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(capa, yerine))
            sonuc = vakalari_kos(kopya)
        olen = sorted(k for k, (ok, _) in sonuc.items() if not ok)
        oldu = hedef in olen
        print("%-16s %s (kirmizi vakalar: %s)" % (ad, "OLDU" if oldu else "YASADI", ",".join(olen)))
        kirmizi += 0 if oldu else 1
    print("WRANGLER_LOG_TEST VAKA=%d MUTANT=%d KIRMIZI=%d" % (len(VAKALAR), len(MUTANTLAR), kirmizi))
    return 1 if kirmizi else 0


if __name__ == "__main__":
    sys.exit(main())
