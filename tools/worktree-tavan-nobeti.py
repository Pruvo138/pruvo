#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yerel worktree envanterini gorunur kilan, ASLA bloklamayan nobetci."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time

from git_ortami import (GIT_BAGLAM_DEGISKENLERI, git_ortami,
                        sentetik_git)


TAVAN = 2
BAYAT_DAKIKA = 90
SENTETIK_AD = "Fikstur"
SENTETIK_EPOSTA = "fikstur@ornek.gecersiz"
KIMLIK_DEGISKENLERI = (
    "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL",
    "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL",
)


def git(depo, *args, env=None):
    try:
        p = subprocess.run(["git", "-C", depo] + list(args), capture_output=True,
                           text=True, timeout=30, env=env)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)


def agaclar(depo):
    rc, cikti, hata = git(depo, "worktree", "list", "--porcelain")
    if rc != 0:
        raise RuntimeError("git worktree list olculemedi: %s" % (hata or rc))
    sonuc = []
    cari = None
    for satir in cikti.splitlines() + [""]:
        if satir.startswith("worktree "):
            if cari:
                sonuc.append(cari)
            cari = {"yol": satir[9:], "dal": None, "detached": False}
        elif cari is not None and satir.startswith("branch refs/heads/"):
            cari["dal"] = satir[len("branch refs/heads/"):]
        elif cari is not None and satir == "detached":
            cari["detached"] = True
        elif not satir and cari:
            sonuc.append(cari)
            cari = None
    return sonuc


def kirli_mi(yol):
    rc, cikti, _hata = git(yol, "status", "--porcelain", "--untracked-files=all")
    return rc == 0 and bool(cikti)


def en_yeni_mtime(yol):
    en_yeni = 0.0
    try:
        for kok, dizinler, dosyalar in os.walk(yol):
            dizinler[:] = [ad for ad in dizinler if ad != ".git"]
            for ad in dosyalar:
                tam = os.path.join(kok, ad)
                if os.path.basename(tam) == ".git":
                    continue
                try:
                    en_yeni = max(en_yeni, os.path.getmtime(tam))
                except OSError:
                    pass
    except OSError:
        pass
    return en_yeni


def kaynak(entry):
    if entry["detached"] or not entry["dal"]:
        return "detached"
    dal = entry["dal"].removeprefix("worktree-")
    if dal.startswith("agent-"):
        return "agent-*"
    for onek in ("muh/", "onarim/", "claude/"):
        if dal.startswith(onek):
            return onek
    return "BILINMEYEN"


def rapor_cikis_kodu():
    return 0


def rapor(depo, simdi=None):
    simdi = time.time() if simdi is None else simdi
    try:
        liste = agaclar(depo)
        satirlar = []
        if len(liste) > TAVAN:
            satirlar.extend([
                "!! UYARI: WORKTREE TAVANI ASILDI — SAYI=%d TAVAN=%d" %
                (len(liste), TAVAN),
                "!! YORDAM: once yama + izlenmeyen dosya kopyasi arsivle; yama icin "
                "git apply --check dogrula; main disi commit varsa bundle al; SONRA kaldir.",
            ])
        satirlar.append("WORKTREE SAYI=%d TAVAN=%d" % (len(liste), TAVAN))
        kirilim = {"agent-*": 0, "muh/": 0, "onarim/": 0, "claude/": 0,
                    "detached": 0, "BILINMEYEN": 0}
        for sira, entry in enumerate(liste):
            dirty = kirli_mi(entry["yol"])
            mtime = en_yeni_mtime(entry["yol"])
            yas = float("inf") if not mtime else max(0.0, (simdi - mtime) / 60.0)
            fresh = yas < BAYAT_DAKIKA
            if sira == 0:
                sinif = "ANA AGAC"
                acilis = "ANA"
            else:
                sinif = "CANLI" if dirty and fresh else "OKSUZ"
                acilis = kaynak(entry)
                kirilim[acilis] += 1
            rc, adet, _hata = git(entry["yol"], "rev-list", "--count", "main..HEAD")
            commit = int(adet) if rc == 0 and adet.isdigit() else -1
            yas_yazi = "BILINMIYOR" if yas == float("inf") else "%.1fdk" % yas
            satirlar.append(
                "AGAC=%s SINIF=%s KIRLI=%s TAZELIK=%s YAS=%s "
                "MAIN_DISI_COMMIT=%s ACILIS=%s" %
                (entry["yol"], sinif, "EVET" if dirty else "HAYIR",
                 "TAZE" if fresh else "BAYAT", yas_yazi,
                 commit if commit >= 0 else "OLCULEMEDI", acilis))
            if commit == 0:
                satirlar.append(
                    "  NOT: main'de olmayan commit 0; kaybolacak tek sey commit'lenmemis calismadir.")
            elif commit > 0:
                satirlar.append("  !! BUNDLE GEREKIR: main'de olmayan %d commit var." % commit)
        satirlar.append("ACILIS_KIRILIMI " + " ".join(
            "%s=%d" % (ad, kirilim[ad]) for ad in
            ("agent-*", "muh/", "onarim/", "claude/", "detached", "BILINMEYEN")))
        return "\n".join(satirlar)
    except Exception as exc:
        return "!! WORKTREE NOBETI OLCULEMEDI (push DEVAM): %s" % exc


def yaz(yol, metin):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as dosya:
        dosya.write(metin)


def g(depo, *args, env=None):
    rc, cikti, hata = git(depo, *args, env=env)
    if rc != 0:
        raise RuntimeError("git %s: %s" % (" ".join(args), hata or cikti))
    return cikti


def sentetik_g(depo, *args):
    p = sentetik_git(depo, *args, kimlik_ad=SENTETIK_AD,
                      kimlik_eposta=SENTETIK_EPOSTA,
                      capture_output=True, text=True, timeout=30)
    if p.returncode != 0:
        raise RuntimeError("git %s: %s" % (" ".join(args), p.stderr or p.stdout))
    return p.stdout.strip()


def depo_kur(kok):
    os.makedirs(kok, exist_ok=True)
    sentetik_g(kok, "init", "-q", "-b", "main")
    yaz(os.path.join(kok, "taban.txt"), "taban\n")
    sentetik_g(kok, "add", "taban.txt")
    sentetik_g(kok, "commit", "-q", "-m", "taban")


def agac_ekle(kok, yol, dal):
    sentetik_g(kok, "worktree", "add", "-q", "-b", dal, yol, "main")


def betik_kos(betik, depo):
    return subprocess.run([sys.executable, betik, "--depo", depo],
                          capture_output=True, text=True, timeout=60,
                          env=git_ortami())


def kendini_test():
    betik = os.path.abspath(__file__)
    gecici = tempfile.mkdtemp(prefix="pruvo-worktree-nobet-")
    hatalar = []
    rc_listesi = []
    try:
        kok = os.path.join(gecici, "depo")
        depo_kur(kok)
        canli = os.path.join(gecici, "canli")
        agac_ekle(kok, canli, "agent-taze")
        yaz(os.path.join(canli, "taze.txt"), "kirli\n")
        p = betik_kos(betik, kok)
        rc_listesi.append(p.returncode)
        if "UYARI: WORKTREE TAVANI ASILDI" in p.stdout:
            hatalar.append("a:tavan altinda uyari basildi")
        if "SINIF=CANLI KIRLI=EVET TAZELIK=TAZE" not in p.stdout:
            hatalar.append("d:kirli+taze CANLI olmadi")

        bayat = os.path.join(gecici, "bayat")
        agac_ekle(kok, bayat, "onarim/bayat")
        bayat_dosya = os.path.join(bayat, "bayat.txt")
        yaz(bayat_dosya, "kirli\n")
        eski = time.time() - (BAYAT_DAKIKA + 10) * 60
        for yuru_kok, _dizinler, dosyalar in os.walk(bayat):
            for ad in dosyalar:
                tam = os.path.join(yuru_kok, ad)
                if os.path.basename(tam) != ".git":
                    os.utime(tam, (eski, eski))
        p = betik_kos(betik, kok)
        rc_listesi.append(p.returncode)
        if not p.stdout.startswith("!! UYARI: WORKTREE TAVANI ASILDI"):
            hatalar.append("b:tavan ustunde uyari basta degil")
        if "SINIF=OKSUZ KIRLI=EVET TAZELIK=BAYAT" not in p.stdout:
            hatalar.append("c:kirli+bayat OKSUZ olmadi")

        commit_kok = os.path.join(gecici, "commit-depo")
        depo_kur(commit_kok)
        commit_agac = os.path.join(gecici, "commit-agac")
        agac_ekle(commit_kok, commit_agac, "muh/commitli")
        yaz(os.path.join(commit_agac, "yeni.txt"), "yeni\n")
        sentetik_g(commit_agac, "add", "yeni.txt")
        sentetik_g(commit_agac, "commit", "-q", "-m", "yeni")
        p = betik_kos(betik, commit_kok)
        rc_listesi.append(p.returncode)
        if "MAIN_DISI_COMMIT=1" not in p.stdout or "BUNDLE GEREKIR" not in p.stdout:
            hatalar.append("e:main disi commit ayri isaretlenmedi")

        bilinmeyen_kok = os.path.join(gecici, "bilinmeyen-depo")
        depo_kur(bilinmeyen_kok)
        bilinmeyen = os.path.join(gecici, "bilinmeyen")
        agac_ekle(bilinmeyen_kok, bilinmeyen, "ozel/dal")
        p = betik_kos(betik, bilinmeyen_kok)
        rc_listesi.append(p.returncode)
        if "BILINMEYEN=1" not in p.stdout:
            hatalar.append("f:bilinmeyen dal dusuruldu")

        worktree_agent_kok = os.path.join(gecici, "worktree-agent-depo")
        depo_kur(worktree_agent_kok)
        worktree_agent = os.path.join(gecici, "worktree-agent")
        agac_ekle(worktree_agent_kok, worktree_agent,
                  "worktree-agent-ac7f1acfbc8289984")
        p = betik_kos(betik, worktree_agent_kok)
        rc_listesi.append(p.returncode)
        if "ACILIS=agent-*" not in p.stdout or "agent-*=1" not in p.stdout:
            hatalar.append("h:worktree-agent dali agent sinifina dusmedi")

        worktree_bilinmeyen_kok = os.path.join(gecici, "worktree-bilinmeyen-depo")
        depo_kur(worktree_bilinmeyen_kok)
        worktree_bilinmeyen = os.path.join(gecici, "worktree-bilinmeyen")
        agac_ekle(worktree_bilinmeyen_kok, worktree_bilinmeyen,
                  "worktree-yepyeni-desen")
        p = betik_kos(betik, worktree_bilinmeyen_kok)
        rc_listesi.append(p.returncode)
        if "ACILIS=BILINMEYEN" not in p.stdout or "BILINMEYEN=1" not in p.stdout:
            hatalar.append("i:tanimadigi worktree dali BILINMEYEN kalmadi")
        if any(rc != 0 for rc in rc_listesi):
            hatalar.append("g:rapor-only vakalarindan biri rc!=0")
        for ad in KIMLIK_DEGISKENLERI:
            if ad in os.environ:
                hatalar.append("j:kimlik ana surece sizdi:" + ad)
    except Exception as exc:
        hatalar.append("fikstur:%s" % exc)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    if hatalar:
        print("KENDINI_TEST=KIRMIZI IDDIA=10 YENI_VAKA=1 " + " | ".join(hatalar))
        return 1
    print("KENDINI_TEST=YESIL IDDIA=10 YENI_VAKA=1 RAPOR_ONLY_VAKA=%d/%d" %
          (sum(rc == 0 for rc in rc_listesi), len(rc_listesi)))
    return 0


def mutasyon():
    kaynak_metin = open(os.path.abspath(__file__), encoding="utf-8").read()
    oldurucular = [
        ("tavan", "if len(liste) " + "> TAVAN:",
         "if len(liste) " + ">= TAVAN:"),
        ("mtime", "fresh = yas " + "< BAYAT_DAKIKA",
         "fresh = yas " + ">= BAYAT_DAKIKA"),
        ("porcelain", 'sinif = "CANLI" if dirty and ' + 'fresh else "OKSUZ"',
         'sinif = "CANLI" if ' + 'dirty else "OKSUZ"'),
        ("commit", '"main..' + 'HEAD"', '"HEAD..' + 'main"'),
        ("bilinmeyen", 'return "BILIN' + 'MEYEN"', 'return "det' + 'ached"'),
        ("worktree-oneki", 'dal = entry["dal"].remove' + 'prefix("worktree-")',
         'dal = entry["dal"]'),
        ("rapor-only", "def rapor_cikis_kodu():\n" + "    return 0",
         "def rapor_cikis_kodu():\n" + "    return 9"),
        ("env-sizinti", "ortam = os.environ." + "copy()",
         "ortam = os.environ"),
    ]
    kontroller = [("yorum", kaynak_metin + "\n# kontrol mutanti\n"),
                  ("bosluk", kaynak_metin + "\n\n")]
    gecici = tempfile.mkdtemp(prefix="pruvo-worktree-mutasyon-")
    tutan = 0
    kontrol_yesil = 0
    hayatta = []
    try:
        for ad, eski, yeni in oldurucular:
            if kaynak_metin.count(eski) != 1:
                hayatta.append(ad + ":capa")
                continue
            yol = os.path.join(gecici, ad + ".py")
            yaz(yol, kaynak_metin.replace(eski, yeni, 1))
            p = subprocess.run([sys.executable, yol, "--kendini-test"],
                               capture_output=True, text=True, timeout=120)
            if p.returncode != 0:
                tutan += 1
            else:
                hayatta.append(ad)
        for ad, metin in kontroller:
            yol = os.path.join(gecici, "kontrol-" + ad + ".py")
            yaz(yol, metin)
            p = subprocess.run([sys.executable, yol, "--kendini-test"],
                               capture_output=True, text=True, timeout=120)
            if p.returncode == 0:
                kontrol_yesil += 1
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    print("MUTASYON=%d/%d KONTROL=%d/%d HAYATTA_KALAN=%d" %
          (tutan, len(oldurucular), kontrol_yesil, len(kontroller), len(hayatta)))
    if hayatta:
        print("TEST_KUSURU: hayatta kalan mutantlar: %s" % ", ".join(hayatta))
    return 0 if tutan == len(oldurucular) and kontrol_yesil == len(kontroller) else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--depo", default=os.getcwd())
    parser.add_argument("--kendini-test", action="store_true")
    parser.add_argument("--mutasyon", action="store_true")
    args = parser.parse_args()
    if args.kendini_test:
        return kendini_test()
    if args.mutasyon:
        return mutasyon()
    print(rapor(os.path.abspath(args.depo)))
    return rapor_cikis_kodu()


if __name__ == "__main__":
    sys.exit(main())
