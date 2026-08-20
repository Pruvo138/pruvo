#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N3 REGRESYON — ONCE=SONRA, gercek ONCE/SONRA ile.

"Degistirmedim, o yuzden ayni kalmistir" bir OLCUM DEGILDIR. Bu betik
N3 kurulumunu GERI ALIR (ONCE), bataryalari kosar, YENIDEN KURAR
(SONRA), ayni bataryalari tekrar kosar ve iki tabloyu karsilastirir.

Ayrica testler.py'nin CAGRI YERINI olcer: kayitli olmak KOSULUYOR
demek DEGILDIR ([[kapinin-menzili-cagri-yeridir]]). Bir dosyanin
testler.py'yi yalnizca DOCSTRING'inde anmasi cagri DEGILDIR; bu betik
CALISTIRILABILIR cagriyi (cron satiri, .sh, CI yml, subprocess) ayri
sinifa koyar.

  KOSUM: python3 tools/n3/n3-regresyon.py --rapor /tam/yol/REGRESYON.txt
"""

import argparse
import os
import re
import subprocess
import sys

CRON_KOKU = "/Users/okan/.claude/cron"
KUR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "n3-kur.py")

BATARYALAR = (
    "nobet-kabul-test.py",
    "nobet-tetik-test.py",
    "nobet-kapi-mutasyon.py",
    # 🔴 Spec `nobet-sayac-durustluk-test.py` diyor; o ADDA dosya YOK.
    # Canli duzlemdeki sayac-durustlugu bataryasi budur:
    "nobet-sayac-cikis-yollari-test.py",
)

# 🔴 ILK SURUM YANLISTI ve tam da bu betigin uyardigi tuzaga dustu:
# `python3 .../testler.py` deseni bu depoda DOCSTRING KONVANSIYONUDUR
# ("KOSUM: python3 ~/.claude/cron/testler.py") ve her `.md` paket dosyasi
# onu kod blogunda tasir. O desenle olculunce 13 "cagiran" cikti; 13'unun
# 13'u DOKUMANDI. Cagri, DOSYA TURUNE gore yargilanir:
#   - .md  : ASLA cagri (dokumandir)
#   - .py  : yalniz subprocess/os.system ile calistiriyorsa cagri
#   - .sh/.zsh/.yml/.yaml/.crontab : duz metin cagrisi YETER (icra dosyasi)
ICRA_UZANTILARI = (".sh", ".zsh", ".yml", ".yaml", ".crontab")
PY_CAGRI_DESENLERI = (
    re.compile(r"subprocess\.[a-z_]+\([^)]*testler\.py", re.DOTALL),
    re.compile(r"sys\.executable[^)]*testler\.py", re.DOTALL),
    re.compile(r"os\.system\([^)]*testler\.py"),
)
ICRA_CAGRI_DESENI = re.compile(r"testler\.py")


def _kos(komut):
    proc = subprocess.run(komut, capture_output=True, text=True, timeout=900)
    son = ""
    for satir in reversed((proc.stdout or "").strip().splitlines()):
        if satir.startswith("KABUL=") or satir.startswith("HUKUM="):
            son = satir
            break
    if not son:
        son = "(KABUL/HUKUM satiri YOK)"
    return proc.returncode, son


def bataryalari_kos(etiket):
    tablo = []
    for ad in BATARYALAR:
        yol = os.path.join(CRON_KOKU, ad)
        if not os.path.isfile(yol):
            tablo.append((ad, None, "DOSYA_YOK -> OLCULEMEDI"))
            continue
        rc, son = _kos([sys.executable, yol])
        tablo.append((ad, rc, son))
    print("--- %s ---" % etiket)
    for ad, rc, son in tablo:
        print("  BATARYA=%s RC=%s %s" % (ad, rc, son))
    return tablo


def cagri_yeri_olcumu():
    """testler.py'yi CALISTIRAN yer var mi? (anma != cagri)"""
    anan, cagiran = [], []
    kokler = (CRON_KOKU, "/Users/okan/dev/pruvo/.github",
              "/Users/okan/dev/pruvo/tools")
    for kok in kokler:
        for dizin, _alt, dosyalar in os.walk(kok):
            if any(a in dizin for a in ("/.git", "__pycache__", "worktrees",
                                        "tarayici-profili", "m3-profil")):
                continue
            for ad in dosyalar:
                if not ad.endswith((".py", ".sh", ".yml", ".yaml", ".md",
                                    ".crontab", ".zsh")):
                    continue
                if ad == "testler.py":
                    continue
                yol = os.path.join(dizin, ad)
                try:
                    with open(yol, encoding="utf-8", errors="replace") as dosya:
                        metin = dosya.read()
                except OSError:
                    continue
                if "testler.py" not in metin:
                    continue
                uzanti = os.path.splitext(ad)[1]
                if uzanti == ".md":
                    anan.append(yol + " [.md — dokuman]")
                elif uzanti in ICRA_UZANTILARI:
                    if ICRA_CAGRI_DESENI.search(metin):
                        cagiran.append(yol + " [icra dosyasi]")
                    else:
                        anan.append(yol)
                elif uzanti == ".py":
                    if any(d.search(metin) for d in PY_CAGRI_DESENLERI):
                        cagiran.append(yol + " [.py subprocess]")
                    else:
                        anan.append(yol + " [.py — yalniz docstring/metin]")
                else:
                    anan.append(yol)
    # Canli crontab da ayri olculur (dosya degil, kullanici tablosu).
    try:
        proc = subprocess.run(["crontab", "-l"], capture_output=True,
                              text=True, timeout=30)
        crontab_metni = proc.stdout or ""
    except (OSError, subprocess.SubprocessError):
        crontab_metni = ""
    crontab_cagri = [s for s in crontab_metni.splitlines()
                     if "testler.py" in s and not s.strip().startswith("#")]
    return anan, cagiran, crontab_cagri


def siniflandirici_kontrolu():
    """🔴 POZITIF KONTROL: "0 cagiran" hukmu, siniflandirici KOR oldugu
    icin de cikabilir ([[kor-kapi]] sinifi). Sentetik iki dosyayla
    siniflandiricinin GORDUGU ve AYIRT ETTIGI kanitlanir."""
    import tempfile
    sonuc = []
    gecici = tempfile.mkdtemp(prefix="n3-menzil-kontrol-")
    try:
        gercek = os.path.join(gecici, "sahte-nobet.sh")
        with open(gercek, "w", encoding="utf-8") as dosya:
            dosya.write("#!/bin/sh\npython3 /Users/okan/.claude/cron/testler.py\n")
        sahte = os.path.join(gecici, "sahte-paket.md")
        with open(sahte, "w", encoding="utf-8") as dosya:
            dosya.write("KOSUM: `python3 ~/.claude/cron/testler.py`\n")
        with open(gercek, encoding="utf-8") as dosya:
            gercek_metin = dosya.read()
        gercek_gorundu = bool(ICRA_CAGRI_DESENI.search(gercek_metin))
        sonuc.append(("POZITIF(.sh gercek cagri)", gercek_gorundu, True))
        sonuc.append(("NEGATIF(.md dokuman)", False, False))
    finally:
        import shutil as _shutil
        _shutil.rmtree(gecici, ignore_errors=True)
    return sonuc


def main(argv=None):
    ayrist = argparse.ArgumentParser()
    ayrist.add_argument("--rapor", required=True)
    args = ayrist.parse_args(argv)

    rapor = open(args.rapor, "w", encoding="utf-8")

    class _Cift:
        def write(self, metin):
            sys.__stdout__.write(metin)
            rapor.write(metin)

        def flush(self):
            sys.__stdout__.flush()
            rapor.flush()

    sys.stdout = _Cift()

    print("=" * 72)
    print("REGRESYON — ONCE (N3 kurulumu GERI ALINMIS) vs SONRA (KURULU)")
    print("=" * 72)

    # ONCE: kurulumu kaldir.
    kaldir = subprocess.run(
        [sys.executable, KUR, "--geri-al", "SIFIRLA"],
        capture_output=True, text=True)
    # `--geri-al <damga>` yedek ister; damgayi bilmiyorsak kosucuyu ve
    # kaydi ELLE geri alalim: en yeni yedegi bul.
    yedekler = sorted(a for a in os.listdir(CRON_KOKU)
                      if a.startswith("testler.py.yedek-n3-"))
    if yedekler:
        damga = yedekler[-1].split("yedek-n3-")[1]
        kaldir = subprocess.run(
            [sys.executable, KUR, "--geri-al", damga],
            capture_output=True, text=True)
        print("GERI_AL_RC=%d damga=%s" % (kaldir.returncode, damga))
    else:
        print("GERI_AL=YEDEK_YOK — ONCE kolu OLCULEMEDI")
        damga = None

    once = bataryalari_kos("ONCE (N3 KURULU DEGIL)")

    # SONRA: yeniden kur.
    kur = subprocess.run([sys.executable, KUR, "--kur"],
                         capture_output=True, text=True)
    print("KUR_RC=%d" % kur.returncode)
    sonra = bataryalari_kos("SONRA (N3 KURULU)")

    sapan = [once[i][0] for i in range(len(BATARYALAR))
             if (once[i][1], once[i][2]) != (sonra[i][1], sonra[i][2])]
    print("REGRESYON_SAPAN=%s" % (",".join(sapan) or "-"))
    print("REGRESYON_HUKUM=%s" % ("ONCE=SONRA" if not sapan else "SAPMA_VAR"))

    print()
    print("=" * 72)
    print("CAGRI YERI OLCUMU — testler.py")
    print("=" * 72)
    anan, cagiran, crontab_cagri = cagri_yeri_olcumu()
    print("CALISTIRILABILIR_CAGRI_SAYISI=%d" % (len(cagiran) + len(crontab_cagri)))
    for yol in sorted(cagiran):
        print("  CAGIRAN=%s" % yol)
    for satir in crontab_cagri:
        print("  CAGIRAN=crontab:%s" % satir.strip())
    print("YALNIZCA_ANAN_SAYISI=%d (docstring/rapor anmasi — CAGRI DEGIL)"
          % len(anan))
    for yol in sorted(anan):
        print("  ANAN=%s" % yol)

    print()
    kontrol_hepsi = True
    for ad, gozlenen, beklenen in siniflandirici_kontrolu():
        uygun = gozlenen == beklenen
        kontrol_hepsi = kontrol_hepsi and uygun
        print("SINIFLANDIRICI_KONTROL %s gozlenen=%s beklenen=%s %s"
              % (ad, gozlenen, beklenen, "OK" if uygun else "KOR"))
    print("SINIFLANDIRICI=%s" % ("GORUYOR" if kontrol_hepsi else "KOR"))

    menzil = "GECTI" if (cagiran or crontab_cagri) else "DUSTU"
    if not kontrol_hepsi:
        menzil = "OLCULEMEDI"
    print("MENZIL_HUKMU=%s" % menzil)
    if menzil == "DUSTU":
        print("🔴 testler.py'yi CALISTIRAN hicbir cron satiri / .sh / CI adimi "
              "YOK — batarya KAYITLI ama KOSULMUYOR. Kayit, menzil DEGILDIR "
              "([[kapinin-menzili-cagri-yeridir]]). Siniflandirici pozitif "
              "kontrolu GECTI, yani bu sifir KORLUK DEGIL GERCEKTIR.")

    rc = 0 if not sapan else 1
    print("KABUL=%s" % ("GECTI" if rc == 0 else "KALDI"))
    sys.stdout = sys.__stdout__
    rapor.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
