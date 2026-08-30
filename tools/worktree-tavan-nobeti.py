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
import gecici_worktree


TAVAN_MIMAR = 2
TAVAN = TAVAN_MIMAR
TAVAN_CHIP = 12
BAYAT_DAKIKA = 90
OLU_CHIP_DAKIKA = 240
SENTETIK_AD = "Fikstur"
SENTETIK_EPOSTA = "fikstur@ornek.gecersiz"
KIMLIK_DEGISKENLERI = (
    "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL",
    "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL",
)


def git(depo, *args, env=None):
    try:
        p = subprocess.run(["git", "-C", depo] + list(args), capture_output=True,
                           text=True, timeout=30,
                           env=git_ortami() if env is None else env)
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


def chip_agaci_mi(yol, ana_kok):
    chip_koku = os.path.realpath(os.path.join(ana_kok, ".claude", "worktrees"))
    return os.path.realpath(yol).startswith(chip_koku + os.sep)  # WORKTREE_MUTANT_ROLE


# 🔴 IKIZ TANIM KAPATILDI (28 Agu 2026, cip `KraL-DiskFikstur-28Agu`): "gecici kok"
# turetimi burada AYRI bir govde olarak yaziliydi ve `tools/gecici_worktree.py` ayni
# yuklemi ikinci kez tanimlamak zorunda kalacakti. Iki govde SESSIZCE ayrisir
# ([[ikiz-tanim-sessiz-ayrisma]]) — tanim artik TEK KAYNAKTA.
_gecici_kokler = gecici_worktree.gecici_kokler
gecici_altinda_mi = gecici_worktree.gecici_altinda_mi


def fikstur_agaci_mi(entry):
    """UCUNCU KOVA (K223, 19 Agu 2026) — baska bir kapinin SANIYELIK self-test agaci.

    🔴 NEDEN VAR (olculdu 19 Agu): rol siniflandirmasi YALNIZ iki kova biliyordu ve
    `.claude/worktrees/` altinda OLMAYAN her agac MIMAR sayiliyordu. Sistem temp'indeki
    `pruvo-kapi-test-*/kayitli-wt` fiksturleri (tools/mimar-kilit-test.py +
    tools/mimar-kapi-mutasyon-test.py, `worktree add --no-checkout --detach`) push
    aninda MIMAR kovasina dusuyor, nobetci `TAVAN ASILDI ROL=MIMAR SAYI=3` yakiyordu.
    O uyari SAHTE idi: `ls` iki dizini YOK gosterdi, saniyeler sonra `git worktree list`
    BASKA IKI fiksturu listeledi, bir sonraki push `MIMAR=2/2` bastı. Sahte kirmizi
    GERCEK kirmiziyi gorunmez yapar.

    YUKLEM IKI KOLUN **VE**'sidir ve ikisi de gereklidir:
      * gecici dizin altinda (turetilmis kokler — [[gecici_kokler]])
      * detached (fiksturler HEAD'e detach ile baglanir; GERCEK mimar agaci daldadir)
    Yalniz "gecici dizin" olsaydi, gecici dizinde kurulan mutasyon/senaryo depolarinin
    DALLI mimar agaclari da yutulur, gercek tavan asimi gorunmez olurdu."""
    return gecici_altinda_mi(entry["yol"]) and bool(entry["detached"])  # FIKSTUR_MUTANT_ROLE


def rol_belirle(entry, ana_kok):
    """UC KOVA: CHIP · FIKSTUR · MIMAR. SIRA ANLAMLIDIR — chip koku ONCE bakilir ki
    gecici dizinde kurulmus bir chip agaci FIKSTUR'e kacmasin."""
    if chip_agaci_mi(entry["yol"], ana_kok):
        return "CHIP"
    if fikstur_agaci_mi(entry):
        return "FIKSTUR"
    return "MIMAR"


def rapor_cikis_kodu():
    return 0


def rapor(depo, simdi=None):
    simdi = time.time() if simdi is None else simdi
    try:
        liste = agaclar(depo)
        satirlar = []
        kok_rc, ana_kok, kok_hata = git(depo, "rev-parse", "--show-toplevel")
        if kok_rc != 0 or not ana_kok:
            raise RuntimeError("ana agac kokune ulasilamadi: %s" % (kok_hata or kok_rc))
        roller = [(entry, rol_belirle(entry, ana_kok)) for entry in liste]
        mimar_sayisi = sum(rol == "MIMAR" for _entry, rol in roller)
        chip_sayisi = sum(rol == "CHIP" for _entry, rol in roller)
        # FIKSTUR hicbir tavana sayilmaz — ama SESSIZCE de yutulmaz (asagida GORUNUR).
        fikstur_sayisi = sum(rol == "FIKSTUR" for _entry, rol in roller)
        mimar_uyari = mimar_sayisi > TAVAN_MIMAR
        chip_uyari = chip_sayisi > TAVAN_CHIP
        if mimar_uyari:
            satirlar.append(
                "!! UYARI: WORKTREE TAVANI ASILDI — ROL=MIMAR SAYI=%d TAVAN=%d" %
                (mimar_sayisi, TAVAN_MIMAR))
        if chip_uyari:
            satirlar.append(
                "!! UYARI: WORKTREE TAVANI ASILDI — ROL=CHIP SAYI=%d TAVAN=%d" %
                (chip_sayisi, TAVAN_CHIP))
        if mimar_uyari or chip_uyari:
            satirlar.append(
                "!! YORDAM: once yama + izlenmeyen dosya kopyasi arsivle; yama icin "
                "git apply --check dogrula; main disi commit varsa bundle al; SONRA kaldir.")
        satirlar.append("WORKTREE SAYI=%d TAVAN=%d MIMAR=%d/%d CHIP=%d/%d FIKSTUR=%d" %
                        (len(liste), TAVAN, mimar_sayisi, TAVAN_MIMAR,
                         chip_sayisi, TAVAN_CHIP, fikstur_sayisi))
        if fikstur_sayisi:
            satirlar.append(
                "NOT: FIKSTUR=%d agac baska bir kapinin SANIYELIK self-test worktree'si "
                "(gecici dizin + detached). HICBIR TAVANA sayilmaz; SESSIZCE de "
                "yutulmaz — asagida ROL=FIKSTUR olarak listelenir." % fikstur_sayisi)
        kirilim = {"agent-*": 0, "muh/": 0, "onarim/": 0, "claude/": 0,
                    "detached": 0, "BILINMEYEN": 0}
        olu_adaylari = []
        for sira, (entry, rol) in enumerate(roller):
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
                "MAIN_DISI_COMMIT=%s ACILIS=%s ROL=%s" %
                (entry["yol"], sinif, "EVET" if dirty else "HAYIR",
                 "TAZE" if fresh else "BAYAT", yas_yazi,
                 commit if commit >= 0 else "OLCULEMEDI", acilis, rol))
            if (rol == "CHIP" and commit == 0 and yas != float("inf") and
                    yas > OLU_CHIP_DAKIKA):
                olu_adaylari.append((entry["yol"], yas_yazi))
            if commit == 0:
                satirlar.append(
                    "  NOT: main'de olmayan commit 0; kaybolacak tek sey commit'lenmemis calismadir.")
            elif commit > 0:
                satirlar.append("  !! BUNDLE GEREKIR: main'de olmayan %d commit var." % commit)
        satirlar.append("OLU_CHIP_ADAYI=%d (main disi commit YOK + YAS>%d dk)" %
                        (len(olu_adaylari), OLU_CHIP_DAKIKA))
        for yol, yas_yazi in olu_adaylari:
            satirlar.append(
                "OLU_CHIP_ADAYI AGAC=%s YAS=%s — is bittiyse kaldir "
                "(kaybolacak sey YOK: main disi commit 0)" % (yol, yas_yazi))
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


def fikstur_ekle(kok, yol):
    """BASKA bir kapinin self-test worktree'sinin BIREBIR sekli (olculdu:
    tools/mimar-kilit-test.py `gecici_worktree_kur` ve tools/mimar-kapi-mutasyon-test.py):
    gecici dizinde, `--no-checkout --detach`. Yol `kok`un DISINDA olmalidir — fikstur
    ana agacin altina degil, sistem temp'ine kurulur."""
    sentetik_g(kok, "worktree", "add", "-q", "--no-checkout", "--detach", yol, "main")


def betik_kos(betik, depo):
    return subprocess.run([sys.executable, betik, "--depo", depo],
                          capture_output=True, text=True, timeout=60,
                          env=git_ortami())


def _uyari_var(cikti, rol):
    return "!! UYARI: WORKTREE TAVANI ASILDI — ROL=%s" % rol in cikti


def _senaryo(betik, gecici, ad, chip_sayisi, mimar_sayisi, fikstur_sayisi=0):
    kok = os.path.join(gecici, ad)
    depo_kur(kok)
    chip_koku = os.path.join(kok, ".claude", "worktrees")
    for sira in range(chip_sayisi):
        agac_ekle(kok, os.path.join(chip_koku, "chip-%d" % sira),
                  "chip-%d" % sira)
    for sira in range(max(0, mimar_sayisi - 1)):
        agac_ekle(kok, os.path.join(kok, "mimar-%d" % sira),
                  "mimar-%d" % sira)
    # 🔴 Fikstur agaclari `kok`un DISINA, dogrudan gecici koke kurulur: gercek vakada da
    # baska bir kapinin fiksturu bizim repo agacimizin altinda DEGILDIR.
    for sira in range(fikstur_sayisi):
        fikstur_ekle(kok, os.path.join(gecici, ad + "-fikstur-%d" % sira))
    return betik_kos(betik, kok)


def _eskit(yol, dakika):
    eski = time.time() - dakika * 60
    for yuru_kok, _dizinler, dosyalar in os.walk(yol):
        for ad in dosyalar:
            tam = os.path.join(yuru_kok, ad)
            if os.path.basename(tam) != ".git":
                os.utime(tam, (eski, eski))


def _olu_chip_senaryosu(betik, gecici, ad="olu-chip-depo"):
    kok = os.path.join(gecici, ad)
    depo_kur(kok)
    chip_koku = os.path.join(kok, ".claude", "worktrees")
    commitli = os.path.join(chip_koku, "commitli")
    commitsiz = os.path.join(chip_koku, "commitsiz")
    agac_ekle(kok, commitli, "olu-commitli")
    yaz(os.path.join(commitli, "yeni.txt"), "commitli\n")
    sentetik_g(commitli, "add", "yeni.txt")
    sentetik_g(commitli, "commit", "-q", "-m", "main disi")
    agac_ekle(kok, commitsiz, "olu-commitsiz")
    _eskit(commitli, OLU_CHIP_DAKIKA + 10)
    _eskit(commitsiz, OLU_CHIP_DAKIKA + 10)
    return betik_kos(betik, kok)


def kendini_test():
    betik = os.path.abspath(__file__)
    gecici = tempfile.mkdtemp(prefix="pruvo-worktree-nobet-")
    hatalar = []
    rc_listesi = []
    w_kontrolleri = ()      # try bloğu erken duserse ozet satiri NameError vermesin
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
        sinir_kok = os.path.join(gecici, "sinir-depo")
        depo_kur(sinir_kok)
        sinir_agac = os.path.join(gecici, "sinir-agac")
        agac_ekle(sinir_kok, sinir_agac, "sinir")
        sinir_mtime = en_yeni_mtime(sinir_agac)
        sinir_cikti = rapor(sinir_kok, sinir_mtime + BAYAT_DAKIKA * 60)
        if "TAZELIK=BAYAT" not in sinir_cikti:
            hatalar.append("l:90 dakika siniri BAYAT olmadi")

        w1 = _senaryo(betik, gecici, "w1", 6, 1)
        w2 = _senaryo(betik, gecici, "w2", 0, 3)
        w3 = _senaryo(betik, gecici, "w3", 13, 1)
        w4 = _senaryo(betik, gecici, "w4", 6, 3)
        w5 = _olu_chip_senaryosu(betik, gecici)
        # --- K223: UCUNCU KOVA (FIKSTUR) ---
        # W6 POZITIF: gercek ana agac + BIR fikstur (gecici + detached) -> fikstur
        #    MIMAR sayilmaz, tavan asilmaz, ama FIKSTUR=1 satirda GORUNUR.
        # W7 NEGATIF: ayni fikstur + GERCEK 3 mimar agaci -> tavan uyarisi HALA yanar
        #    (fikstur muafiyeti gercek asimi MASKELEMEZ).
        w6 = _senaryo(betik, gecici, "w6", 0, 1, 1)
        w7 = _senaryo(betik, gecici, "w7", 0, 3, 1)
        w_kontrolleri = (
            ("W1", w1, not _uyari_var(w1.stdout, "CHIP") and
             not _uyari_var(w1.stdout, "MIMAR") and
             "MIMAR=1/2" in w1.stdout and "CHIP=6/12" in w1.stdout),
            ("W2", w2, _uyari_var(w2.stdout, "MIMAR") and
             not _uyari_var(w2.stdout, "CHIP") and w2.returncode == 0),
            ("W3", w3, _uyari_var(w3.stdout, "CHIP") and w3.returncode == 0),
            ("W4", w4, _uyari_var(w4.stdout, "MIMAR") and
             not _uyari_var(w4.stdout, "CHIP") and w4.returncode == 0),
            ("W5", w5, "OLU_CHIP_ADAYI=1" in w5.stdout and w5.returncode == 0),
            # 🔴 FIKSTUR sayisi OZET SATIRINDAN okunur, alt-dize aramasiyla DEGIL:
            # aciklama ("NOT: FIKSTUR=1 agac ...") de ayni metni tasiyor, dolayisiyla
            # `"FIKSTUR=1" in stdout` ozet satirini sifirlayan mutanti GORMEZ
            # ([[ad-iki-rolde-mutanti-golgeler]]).
            ("W6", w6, not _uyari_var(w6.stdout, "MIMAR") and
             not _uyari_var(w6.stdout, "CHIP") and
             "MIMAR=1/2" in w6.stdout and _ozet_alani(w6.stdout, "FIKSTUR") == "1" and
             "ROL=FIKSTUR" in w6.stdout and w6.returncode == 0),
            ("W7", w7, _uyari_var(w7.stdout, "MIMAR") and
             "MIMAR=3/2" in w7.stdout and _ozet_alani(w7.stdout, "FIKSTUR") == "1" and
             w7.returncode == 0),
        )
        for ad, p_vaka, tamam in w_kontrolleri:
            if not tamam:
                hatalar.append("%s:beklenmeyen hukum rc=%d" % (ad, p_vaka.returncode))
        if any(p_vaka.returncode != 0 for _ad, p_vaka, _tamam in w_kontrolleri):
            hatalar.append("m:rapor-only yeni vakalarindan biri rc!=0")
        eski_git_dir = os.environ.get("GIT_DIR")
        os.environ["GIT_DIR"] = os.path.join(gecici, "olmayan-git-dir")
        env_p = betik_kos(betik, kok)
        if eski_git_dir is None:
            os.environ.pop("GIT_DIR", None)
        else:
            os.environ["GIT_DIR"] = eski_git_dir
        if "WORKTREE SAYI=" not in env_p.stdout:
            hatalar.append("n:git baglami temizlenmedi")
        if any(rc != 0 for rc in rc_listesi):
            hatalar.append("g:rapor-only vakalarindan biri rc!=0")
        if rapor_cikis_kodu() != 0:
            hatalar.append("k:rapor-only cikis kodu 0 degil")
        for ad in KIMLIK_DEGISKENLERI:
            if ad in os.environ:
                hatalar.append("j:kimlik ana surece sizdi:" + ad)
    except Exception as exc:
        hatalar.append("fikstur:%s" % exc)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    # 🔴 SAYILAR TURETILIR, ELLE YAZILMAZ: eski satir sabit `IDDIA=15 YENI_VAKA=5`
    # basiyordu; vaka eklenince o sayi SESSIZCE bayatlar ve rapor kendi kapsamini
    # YANLIS beyan ederdi ([[ikiz-tanim-sessiz-ayrisma]]).
    w_yazi = " ".join("%s=%s" % (ad, "YESIL" if tamam else "KIRMIZI")
                      for ad, _p, tamam in w_kontrolleri)
    if hatalar:
        print("KENDINI_TEST=KIRMIZI W_VAKA=%d %s | %s" %
              (len(w_kontrolleri), w_yazi, " | ".join(hatalar)))
        return 1
    print("KENDINI_TEST=YESIL W_VAKA=%d RAPOR_ONLY_VAKA=%d/%d %s" %
          (len(w_kontrolleri), sum(rc == 0 for rc in rc_listesi),
           len(rc_listesi), w_yazi))
    return 0


def _ozet_alani(cikti, anahtar):
    """Ozet satirindan (`WORKTREE SAYI=...`) tek alani OKU. Alan HIC yoksa 'YOK' —
    boylece "gorunurluk" mutanti (alani silen/sifirlayan) hukumde AYIRT EDILIR."""
    for satir in cikti.splitlines():
        if satir.startswith("WORKTREE SAYI="):
            for parca in satir.split():
                if parca.startswith(anahtar + "="):
                    return parca.split("=", 1)[1]
    return "YOK"


def _mutant_hukumlari(betik, gecici, mutant_adi):
    tag = "%s-%d" % (mutant_adi, time.time_ns())
    # (vaka, chip_sayisi, mimar_sayisi, fikstur_sayisi)
    vakalar = {
        "tavan-mimar": (("W2", 0, 3, 0), ("W4", 6, 3, 0)),
        "tavan-chip": (("W3", 13, 1, 0),),
        "rol-siniflama": (("W1", 6, 1, 0),),
        "rol-tersine": (("W2", 0, 3, 0), ("W4", 6, 3, 0)),
        "olu-chip": (("W5", 0, 0, 0),),
        # K223 — ucuncu kova. Her mutant HEDEF KOLUNU ayri kanitlar:
        #   fikstur-tanima   : W6'da fikstur MIMAR'a doner (MIMAR 1->2, FIKSTUR 1->0)
        #   fikstur-detached : W2/W7'de DALLI mimar agaclari da yutulur -> uyari SONER
        #   fikstur-gorunur  : W6'da sayi gorunmez olur (FIKSTUR 1->0) ama roller AYNI
        "fikstur-tanima": (("W6", 0, 1, 1), ("W7", 0, 3, 1)),
        "fikstur-detached": (("W2", 0, 3, 0), ("W7", 0, 3, 1)),
        "fikstur-gorunur": (("W6", 0, 1, 1),),
    }
    sonuclar = []
    for vaka, chip_sayisi, mimar_sayisi, fikstur_sayisi in vakalar[mutant_adi]:
        if vaka == "W5":
            p = _olu_chip_senaryosu(betik, gecici, tag + "-W5")
        else:
            p = _senaryo(betik, gecici, tag + "-" + vaka,
                          chip_sayisi, mimar_sayisi, fikstur_sayisi)
        aday = "OLU_CHIP_ADAYI=1" in p.stdout
        sonuclar.append("%s[rc=%d MIMAR_UYARI=%s CHIP_UYARI=%s OLU=%s MIMAR=%s FIKSTUR=%s]" %
                        (vaka, p.returncode,
                         "VAR" if _uyari_var(p.stdout, "MIMAR") else "YOK",
                         "VAR" if _uyari_var(p.stdout, "CHIP") else "YOK",
                         "1" if aday else "0",
                         _ozet_alani(p.stdout, "MIMAR"),
                         _ozet_alani(p.stdout, "FIKSTUR")))
    return ",".join(sonuclar)


def mutasyon():
    kaynak_metin = open(os.path.abspath(__file__), encoding="utf-8").read()
    oldurucular = [
        ("tavan-mimar", "mimar_uyari = mimar_sayisi " + "> TAVAN_MIMAR",
         "mimar_uyari = mimar_sayisi > 99"),
        ("tavan-chip", "chip_uyari = chip_sayisi " + "> TAVAN_CHIP",
         "chip_uyari = chip_sayisi > 999"),
        ("rol-siniflama", "return os.path.realpath(yol).startswith(chip_koku + os." +
         "sep)  # WORKTREE_MUTANT_ROLE",
         "return False  # WORKTREE_MUTANT_ROLE"),
        ("rol-tersine", "return os.path.realpath(yol).startswith(chip_koku + os." +
         "sep)  # WORKTREE_MUTANT_ROLE",
         "return True  # WORKTREE_MUTANT_ROLE"),
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
        ("env-sizinti", "env=git_ortami() if env is None " + "else env",
         "env=None)"),
        ("olu-chip", "if (rol == \"CHIP\" and commit == 0 and yas != float(\"inf\") and\n                    yas > OLU_CHIP_DAKIKA):",
         "if (rol == \"CHIP\" and yas != float(\"inf\") and\n                    yas > OLU_CHIP_DAKIKA):"),
        # --- K223 UCUNCU KOVA (FIKSTUR) ---
        # Arama metinleri BILEREK parcali yazilir: aksi halde bu satirin kendisi ikinci
        # esleme olur, `count(eski) != 1` capasi duser ve mutant SESSIZCE atlanirdi.
        ("fikstur-tanima",
         'return gecici_altinda_mi(entry["yol"]) and bool(entry["deta' +
         'ched"])  # FIKSTUR_MUTANT_ROLE',
         "return False  # FIKSTUR_MUTANT_ROLE"),
        ("fikstur-detached",
         'return gecici_altinda_mi(entry["yol"]) and bool(entry["deta' +
         'ched"])  # FIKSTUR_MUTANT_ROLE',
         'return gecici_altinda_mi(entry["yol"])  # FIKSTUR_MUTANT_ROLE'),
        ("fikstur-gorunur",
         "chip_sayisi, TAVAN_CHIP, fiks" + "tur_sayisi))",
         "chip_sayisi, TAVAN_CHIP, 0))"),
    ]
    kontroller = [("yorum", kaynak_metin + "\n# kontrol mutanti\n"),
                  ("bosluk", kaynak_metin + "\n\n")]
    gecici = tempfile.mkdtemp(prefix="pruvo-worktree-mutasyon-")
    tutan = 0
    kontrol_yesil = 0
    hayatta = []
    try:
        for _yardimci in ("git_ortami.py", "gecici_worktree.py"):
            shutil.copyfile(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         _yardimci),
                            os.path.join(gecici, _yardimci))
        yeni_adlar = {"tavan-mimar", "tavan-chip", "rol-siniflama",
                      "rol-tersine", "olu-chip",
                      "fikstur-tanima", "fikstur-detached", "fikstur-gorunur"}
        for ad, eski, yeni in oldurucular:
            if kaynak_metin.count(eski) != 1:
                hayatta.append(ad + ":capa")
                continue
            yol = os.path.join(gecici, ad + ".py")
            yaz(yol, kaynak_metin.replace(eski, yeni, 1))
            p = subprocess.run([sys.executable, yol, "--kendini-test"],
                               capture_output=True, text=True, timeout=120)
            if ad in yeni_adlar:
                hukum_kok = tempfile.mkdtemp(prefix="pruvo-worktree-hukum-")
                try:
                    taban_yol = os.path.join(hukum_kok, "taban.py")
                    yaz(taban_yol, kaynak_metin)
                    for _yardimci in ("git_ortami.py", "gecici_worktree.py"):
                        shutil.copyfile(
                            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         _yardimci),
                            os.path.join(hukum_kok, _yardimci))
                    taban_hukum = _mutant_hukumlari(taban_yol, hukum_kok, ad)
                    mutant_hukum = _mutant_hukumlari(yol, hukum_kok, ad)
                    print("MUTANT_HUKUM=%s MUTANTSIZ=%s MUTANTLI=%s" %
                          (ad, taban_hukum, mutant_hukum))
                finally:
                    shutil.rmtree(hukum_kok, ignore_errors=True)
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
