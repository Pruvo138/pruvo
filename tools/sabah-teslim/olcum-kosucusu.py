#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KraL-SabahYorumlayici-27Agu — ONARIM OLCUM KOSUCUSU (deterministik).

Neden repoda bir kosucu var: bu kalemin kabulu "kod dogru gorunuyor" DEGIL,
"KURULU KOPYA crontab'in KENDI yorumlayicisiyla kostu ve artefakt URETTI".
O olcumun tekrarlanabilir olmasi icin adimlarin YORUMA yer birakmayan tek bir
komutta durmasi gerekir ([[emir-canliligi-kurulu-kopyadan-olculur]]).

🔴 CIKTI YOLU GIT-DISINA CIVILI (K314 dersi): ic kosum raporu IZLENEN agaca
   yazilirsa `kisisel-veri-test` KURAL A yayini durdurur. Tum ciktilar
   `/private/tmp/pruvo-sabah-teslim/` altina duser.

Sira:
  0  TABAN   — canli kurulu kopyada COGALMA olcumu (SALT OKUMA, `--kuru`)
  1  YEDEK   — canli dosyalarin `.yedek-<UTC>` kopyasi + GERI YUKLEME KANITI
  2  KUR     — worktree -> ~/.claude/cron (ARGUMANSIZ)
  3  KUR2    — ARGUMANSIZ IKINCI KOSUM (idempotens kaniti: bayt birebir)
  4  BATARYA — KURULU `sabah-kabul.py`, faz=on
  5  CANLI   — crontab'in KENDI yorumlayicisiyla `kral-sabah.py` (artefakt+log)
  6  LOG     — `kral-sabah.log`da onarim SONRASI TypeError sayisi

Kosum:  python3 tools/sabah-teslim/olcum-kosucusu.py
        python3 tools/sabah-teslim/olcum-kosucusu.py --yalniz-taban   (adim 0)
"""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import time

WT = os.path.dirname(os.path.abspath(__file__))
CRON = "/Users/okan/.claude/cron"
KURUCU = os.path.join(WT, "kur.py")
DAMGA = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

# 🔴 GIT-DISI DUZLEM — izlenen agaca TEK BAYT yazilmaz.
CIKTI = "/private/tmp/pruvo-sabah-teslim"
OLCUM = os.path.join(CIKTI, "olcum-k320-%s.txt" % DAMGA)
GERI_YUKLEME = os.path.join(CIKTI, "geri-yukleme-kaniti-%s" % DAMGA)

HEDEFLER = ("kral-sabah.py", "sabah-kabul.py", "cip_dogum_bekcisi.py",
            "bekci-kabul.py", "bekci-kur.py")

S = []


def yaz(m=""):
    S.append(m)
    print(m)


def basli(m):
    yaz("")
    yaz("=" * 78)
    yaz(m)
    yaz("=" * 78)


def kos(argv, zaman=900):
    t0 = time.time()
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=zaman)
        rc, cikti = r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        rc, cikti = 125, "%s: %s" % (type(e).__name__, e)
    yaz("$ %s" % " ".join(argv))
    yaz("rc=%d sure=%.1fs" % (rc, time.time() - t0))
    for satir in cikti.splitlines():
        yaz("  | %s" % satir)
    return rc, cikti


def sha(yol):
    with open(yol, "rb") as f:
        ham = f.read()
    return len(ham), hashlib.sha256(ham).hexdigest()[:16]


def iz(baslik):
    yaz("-- PARMAK IZI (%s)" % baslik)
    d = {}
    for ad in HEDEFLER:
        y = os.path.join(CRON, ad)
        if os.path.isfile(y):
            d[ad] = sha(y)
            yaz("   %-26s bayt=%-8d sha=%s" % (ad, d[ad][0], d[ad][1]))
        else:
            d[ad] = None
            yaz("   %-26s YOK" % ad)
    return d


def crontab_yorumlayicisi():
    """🔴 IKIZ TANIM YOK: yorumlayici adi ELLE tasinmaz, crontab'tan OKUNUR."""
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=30)
    except Exception as e:
        return None, "OKUNAMADI (%s)" % type(e).__name__
    for satir in (r.stdout or "").splitlines():
        s = satir.strip()
        if not s or s.startswith("#") or "kral-sabah.py" not in s:
            continue
        p = s.split()
        for i, x in enumerate(p):
            if x.endswith("kral-sabah.py") and i > 0 and "python" in os.path.basename(p[i - 1]):
                return p[i - 1], s
    return None, "kral-sabah.py satiri YOK"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yalniz-taban", action="store_true",
                    help="yalniz adim 0 (SALT OKUMA) — canli duzleme DOKUNMAZ")
    a = ap.parse_args()

    os.makedirs(CIKTI, exist_ok=True)
    yaz("KraL-SabahYorumlayici-27Agu OLCUM  damga=%s  kosan_python=%s"
        % (DAMGA, sys.version.split()[0]))

    py_cron, cron_satiri = crontab_yorumlayicisi()
    yaz("CRONTAB_SATIRI: %s" % cron_satiri)
    yaz("CRONTAB_YORUMLAYICI: %s" % (py_cron or "OKUNAMADI"))

    # ---------------------------------------------------------------- 0 TABAN
    basli("0  TABAN — canli kurulu kopyada COGALMA olcumu (SALT OKUMA, --kuru)")
    iz("kurulum ONCESI")
    rc0, c0 = kos([sys.executable, KURUCU, "--kuru",
                   "--cikti-dizin", os.path.join(CIKTI, "log-taban")])
    yaz("TABAN_OZET rc=%d" % rc0)

    if a.yalniz_taban:
        basli("OZET (yalniz-taban)")
        yaz("OLCUM=%s" % OLCUM)
        with open(OLCUM, "w", encoding="utf-8") as f:
            f.write("\n".join(S) + "\n")
        print("\nOLCUM DOSYASI: %s" % OLCUM)
        return 0

    # ---------------------------------------------------------------- 1 YEDEK
    basli("1  YEDEK + GERI YUKLEME KANITI (canli duzlem, surum kontrolu DISI)")
    os.makedirs(GERI_YUKLEME, exist_ok=True)
    kanitlar = []
    for ad in HEDEFLER:
        kaynak = os.path.join(CRON, ad)
        if not os.path.isfile(kaynak):
            yaz("   %-26s YOK — yedeklenmedi" % ad)
            continue
        hedef = os.path.join(CRON, ad + ".yedek-" + DAMGA)
        shutil.copy2(kaynak, hedef)
        # GERI YUKLEME KANITI: yedegi BASKA bir yere geri sarip bayt kiyasi.
        deneme = os.path.join(GERI_YUKLEME, ad)
        shutil.copy2(hedef, deneme)
        ayni = sha(kaynak) == sha(deneme)
        kanitlar.append(ayni)
        yaz("   %-26s YEDEK=%s geri_yukleme_birebir=%d"
            % (ad, os.path.basename(hedef), int(ayni)))
    yaz("YEDEK_KANITI adet=%d hepsi_birebir=%d"
        % (len(kanitlar), int(bool(kanitlar) and all(kanitlar))))

    # ------------------------------------------------------------------ 2 KUR
    basli("2  KUR — worktree -> ~/.claude/cron (ARGUMANSIZ)")
    rc1, _ = kos([sys.executable, KURUCU, "--cikti-dizin", os.path.join(CIKTI, "log-kur1")])
    iz1 = iz("BIRINCI kurulumdan SONRA")

    # ----------------------------------------------------------------- 3 KUR2
    basli("3  KUR2 — ARGUMANSIZ IKINCI KOSUM (idempotens kaniti)")
    rc2, _ = kos([sys.executable, KURUCU, "--cikti-dizin", os.path.join(CIKTI, "log-kur2")])
    iz2 = iz("IKINCI kurulumdan SONRA")
    birebir = iz1 == iz2
    yaz("IDEMPOTENS bayt_birebir=%d" % int(birebir))
    for ad in HEDEFLER:
        if iz1.get(ad) != iz2.get(ad):
            yaz("   🔴 SAPMA %s: T1=%s T2=%s" % (ad, iz1.get(ad), iz2.get(ad)))

    # --------------------------------------------------------------- 4 BATARYA
    basli("4  BATARYA — KURULU sabah-kabul.py (faz=on)")
    py_b = py_cron if (py_cron and os.path.exists(py_cron)) else sys.executable
    # 🔴 `--kurucu` ZORUNLU: batarya kurulu kopyadan kosar, kur.py orada YOK ve
    #    yol verilmezse sessizce ANA CHECKOUT'un (bayat) kopyasi olculur.
    rc4, _ = kos([py_b, os.path.join(CRON, "sabah-kabul.py"),
                  "--faz", "on", "--kurucu", KURUCU], 1200)
    yaz("BATARYA rc=%d yorumlayici=%s kurucu=%s" % (rc4, py_b, KURUCU))

    # ----------------------------------------------------------------- 5 CANLI
    basli("5  CANLI — kral-sabah.py, CRONTAB'IN KENDI yorumlayicisiyla")
    rc5 = -1
    if not py_cron:
        yaz("🔴 OLCULEMEDI: crontab satiri okunamadi — sebep: %s" % cron_satiri)
    else:
        yaz("-- 5a `--asgari` (on-ucus turetme)")
        kos([py_cron, os.path.join(CRON, "kral-sabah.py"), "--asgari"], 300)
        yaz("-- 5b GERCEK KOSUM (cron satirinin AYNISI; artefakt URETIR)")
        log = os.path.join(CRON, "kral-sabah.log")
        onceki = os.path.getsize(log) if os.path.isfile(log) else 0
        rc5, c5 = kos([py_cron, os.path.join(CRON, "kral-sabah.py")], 900)
        # 🔴 TESLIMAT = DOSYAYA YAZILAN SATIRLAR, ekran ciktisi DEGIL
        #    ([[onarim-kosulmadan-gunluk-artefakt-eksik-kalir]] madde 4).
        with open(log, "a", encoding="utf-8") as f:
            f.write(c5 if c5.endswith("\n") else c5 + "\n")
        yaz("LOG_YAZIMI onceki_bayt=%d yeni_bayt=%d" % (onceki, os.path.getsize(log)))
        spec = None
        for satir in c5.splitlines():
            if satir.startswith("SONUC_KOLU=") and " yol=" in satir:
                spec = satir.split(" yol=")[1].split()[0]
        if spec and os.path.isfile(spec):
            yaz("ARTEFAKT yol=%s bayt=%d" % (spec, os.path.getsize(spec)))
        else:
            yaz("ARTEFAKT 🔴 YOK (spec=%s)" % spec)

    # ------------------------------------------------------------------- 6 LOG
    basli("6  LOG — onarim SONRASI TypeError")
    log = os.path.join(CRON, "kral-sabah.log")
    metin = ""
    if os.path.isfile(log):
        with open(log, encoding="utf-8", errors="replace") as f:
            metin = f.read()
    yaz("kral-sabah.log bayt=%d TypeError_TOPLAM=%d" % (len(metin), metin.count("TypeError")))
    # Onarim SONRASI kosumlar `ASGARI_KAYNAK=` jetonunu tasir (eski surumde YOK).
    parcalar = metin.split("ASGARI_KAYNAK=")
    yaz("ONARIM_SONRASI_KOSUM(ASGARI_KAYNAK jetonu)=%d" % (len(parcalar) - 1))
    if len(parcalar) > 1:
        son = "ASGARI_KAYNAK=" + parcalar[-1]
        yaz("ONARIM_SONRASI_TypeError=%d  (Okan olcutu: 0)" % son.count("TypeError"))

    # -------------------------------------------------------------- 7 TEMIZLIK
    # 🔴 URETEN TEMIZLER (Okan, 13 Agu): bu kosucunun URETTIGI kanit kopyalari
    #    geri silinir. `kur.py`nin KENDI `.yedek-sabahteslim-*` agi DOKUNULMAZ —
    #    gercek emniyet agi odur; silinen yalnizca BURADA uretilen ikizdir.
    basli("7  TEMIZLIK — bu kosumun urettigi kanit kopyalari GERI SILINIR")
    silinen = 0
    bayt = 0
    for ad in HEDEFLER:
        y = os.path.join(CRON, ad + ".yedek-" + DAMGA)
        if os.path.isfile(y):
            bayt += os.path.getsize(y)
            os.remove(y)
            silinen += 1
            yaz("   SILINDI %s" % os.path.basename(y))
    if os.path.isdir(GERI_YUKLEME):
        for kok, _, dosyalar in os.walk(GERI_YUKLEME):
            for d in dosyalar:
                bayt += os.path.getsize(os.path.join(kok, d))
        shutil.rmtree(GERI_YUKLEME)
        yaz("   SILINDI %s/" % GERI_YUKLEME)
    kalan = len([x for x in os.listdir(CRON) if ".yedek-sabahteslim-" in x])
    yaz("TEMIZLIK silinen=%d geri_kazanilan_bayt=%d kur_yedegi_KALAN=%d"
        % (silinen, bayt, kalan))

    basli("OZET")
    yaz("kur1_rc=%d kur2_rc=%d idempotens_birebir=%d batarya_rc=%d canli_rc=%d"
        % (rc1, rc2, int(birebir), rc4, rc5))
    yaz("OLCUM=%s" % OLCUM)

    with open(OLCUM, "w", encoding="utf-8") as f:
        f.write("\n".join(S) + "\n")
    print("\nOLCUM DOSYASI: %s" % OLCUM)
    return 0


if __name__ == "__main__":
    sys.exit(main())
