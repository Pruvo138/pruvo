#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""onarim-commit.py — iscinin onarimini yayina indiren TEK komut (stash -> worktree ->
commit -> --ff-only merge -> push -> temizlik).

NEDEN VAR (olculdu 14 Agu 2026, iki tur yandi): ana checkout'ta KAYNAK commit'i
tools/mimar-commit-kapisi.py tarafindan KIMLIKTEN BAGIMSIZ reddedilir
(PRUVO_MIMAR_ONAY=worker bile YALNIZ veri duzlemini acar). Dogru yordam
"stash -> worktree -> commit -> --ff-only merge -> push -> temizlik"tir ama her isci onu
YENIDEN KESFEDIYOR: bir isci onarimi bitirdi ama commit edemedi (is calisma agacinda ASILI
kaldi), ikincisi SIRF commit icin acilip ayni kapiya carpti, ucuncu turda mimar yordami
elle kurdu. Nobetler artik ONARIM yapacagi icin bu, tur basina tekrar edecek bir kayipti.

CAGRI:
    python3 /Users/okan/dev/pruvo/tools/onarim-commit.py \
        --etiket kanca-kok \
        --mesaj-dosyasi /private/tmp/.../mesaj.txt \
        --dosya tools/kancalar/pre-push --dosya tools/kanca-kur.py

FAIL-CLOSED KURALLARI (hepsi tools/onarim-commit-test.py'de KOSULAN vakadir):
  F1  --dosya listesi BOSSA DUR. "Her seyi commit et" yolu YOKTUR (rc=1).
  F2  Stage'e verilen listenin DISINDA bir yol girerse DUR + geri al (stash iade edilir).
  F3  --ff-only merge basarisizsa DUR; MERGE COMMIT'I URETILMEZ (mimar hukmu gerekir),
      worktree + dal KORUNUR (is kaybolmasin), HUKUM=FF_IMKANSIZ.
  F4  Push reddedilirse fetch + merge <taban> + tekrar push (EN FAZLA 1 kez). Hala
      reddediliyorsa DUR. `--force` / `--force-with-lease` KAYNAKTA GECMEZ.
  F5  Stash uygulamasi cakisirsa DUR, cakisan dosyalari bas, worktree KORUNUR; otomatik
      cozme YOK.
  F6  Herhangi bir adim yarim kalirsa stash KAYBOLMAZ; arac cikmadan STASH_ONCE/STASH_SONRA
      basar.
  F7  --kuru verilince HICBIR yazma yapilmaz; yalnizca ne yapacagi basilir.
  F8  Yasak yollar (urunler.json / .urun-kaynaklari.json / .r2-credentials.json / CNAME)
      --dosya ile verilseler bile REDDEDILIR: veri duzlemi MaCiT'in kanonik araclarinindir
      (flock'lu hasat_ekle.py / urun-ekle.py / duzelt.py), sirlar ise hicbir commit'e girmez.

🔴 NEDEN `stash apply` + BASARIDA `stash drop` (spec'teki "stash pop" yerine): F6 ve kabul
vakasi 7 "adim yarida kesilirse `git stash list` BOS DEGIL" diyor. `pop` stash'i worktree'ye
uygular uygulamaz DUSURUR -> merge/push adiminda beklenmedik bir hata olsa is YALNIZ dalda
kalir ve stash agi YOK olur. `apply` + basarida `drop` ile is IKI YERDE birden durur
(dal + stash) ve yarim kalan kosumda hicbiri kaybolmaz. Ayni sebeple F5 (cakisma) stash'i
otomatik dusurmez.

🔴 TEST DIKISI (uretimde OLU): PRUVO_ONARIM_TEST_KANCA="<NOKTA>:<komut>" yalnizca repo koku
/Users/okan/dev/pruvo DEGILKEN calisir; ana repoda KOSULSUZ yok sayilir. Noktalar:
WORKTREE_SONRA (cwd=worktree) · ADD_ONCE (cwd=worktree) · MERGE_ONCE (cwd=repo koku).
Komut rc!=0 verirse arac o adimda DURUR (yarida kesme enjeksiyonu). Dikis hicbir kapiyi
GEVSETEMEZ: yalnizca ek komut kosturur, karar mantigina dokunmaz.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys

ANA_REPO = "/Users/okan/dev/pruvo"

# F8 — veri duzlemi (MaCiT'in kanonik + flock'lu araclari yazar) ve sirlar. Kontrol
# BASENAME-GENIS: 'tools/urunler.json' ya da 'a/b/CNAME' de reddedilir (fail-closed yon;
# mimar-commit-kapisi.py::veri_mi ile ayni disiplin).
YASAK_ADLAR = ("urunler.json", ".urun-kaynaklari.json", ".r2-credentials.json", "CNAME")

ETIKET_DESENI = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")

TEST_KANCA_ENV = "PRUVO_ONARIM_TEST_KANCA"


def bas(satir: str) -> None:
    print(satir, flush=True)


def git(kok: str, *argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", kok, *argv], capture_output=True, text=True, check=False
    )


def git_ok(kok: str, *argv: str) -> str:
    sonuc = git(kok, *argv)
    return sonuc.stdout.strip() if sonuc.returncode == 0 else ""


def satirlar(metin: str) -> list[str]:
    return [s for s in (metin or "").splitlines() if s.strip()]


def stash_sayisi(kok: str) -> int:
    return len(satirlar(git(kok, "stash", "list").stdout))


def stash_indeksi(kok: str, etiket: str) -> int:
    """BIZIM stash girisinin GUNCEL indeksi (-1 = yok).

    🔴 Neden indeks aranir: stash yigini TUM worktree'ler ve TUM oturumlar icin ORTAKTIR
    (refs/stash ortak git dizinindedir). Baska bir oturum biz calisirken stash acarsa
    stash@{0} ARTIK BIZIM DEGILDIR -> koru koru `stash drop` / `stash pop` KOMSUNUN isini
    silerdi. Giris kendi mesajimizla (`onarim-commit:<etiket>`) bulunur."""
    imza = f"onarim-commit:{etiket}"
    for i, satir in enumerate(satirlar(git(kok, "stash", "list").stdout)):
        if imza in satir:
            return i
    return -1


def stash_sha_indeksi(kok: str, sha: str) -> int:
    """Kendi girdimizin GUNCEL indeksini SHA ile bulur (-1 = yok).

    `git stash drop` RAW SHA kabul ETMEZ (yalniz `stash@{i}`); bu yuzden SHA, yigin
    listesindeki her girdinin `rev-parse stash@{i}` ciktisiyla KARSILASTIRILARAK guncel
    indekse cevrilir. Etiket aramasindan (stash_indeksi) USTUNDUR: iki isci ayni etiketi
    kullansa bile SHA ayrisir; indeks iki islem arasinda kaymis olsa bile SHA degismez."""
    if not sha:
        return -1
    for i, _ in enumerate(satirlar(git(kok, "stash", "list").stdout)):
        if git_ok(kok, "rev-parse", f"stash@{{{i}}}") == sha:
            return i
    return -1


def es_zamanli_isci_sayisi(kok: str, kendi_sha: str) -> int:
    """Yiginda KENDI girdimiz DISINDA kalan `onarim-commit:` etiketli girdi sayisi (S3).

    Yarisi GORUNUR kilar: baska bir isci ayni anda onarim-commit.py kosturuyorsa sayi > 0.
    Islem DURDURULMAZ (SHA ile guvenli), yalnizca uyari basilir."""
    n = 0
    for i, satir in enumerate(satirlar(git(kok, "stash", "list").stdout)):
        if "onarim-commit:" in satir and git_ok(kok, "rev-parse", f"stash@{{{i}}}") != kendi_sha:
            n += 1
    return n


def worktree_satirlari(kok: str) -> int:
    return len(satirlar(git(kok, "worktree", "list").stdout))


def test_kancasi(nokta: str, cwd: str, kok: str) -> int:
    """Bkz. baslik: uretimde OLU test dikisi. Ana repoda KOSULSUZ 0 doner."""
    ham = os.environ.get(TEST_KANCA_ENV, "")
    if not ham:
        return 0
    try:
        if os.path.realpath(kok) == os.path.realpath(ANA_REPO):
            return 0
    except Exception:
        return 0
    ad, _, komut = ham.partition(":")
    if ad.strip() != nokta or not komut.strip():
        return 0
    sonuc = subprocess.run(komut, shell=True, cwd=cwd, capture_output=True, text=True)
    bas(f"TEST_KANCA NOKTA={nokta} RC={sonuc.returncode}")
    return sonuc.returncode


def yol_normalle(kok: str, ham: str) -> tuple[str, str]:
    """(yol, hata) — repo KOKUNE gore duz, ileri-bolu yol uretir."""
    temiz = (ham or "").strip().replace("\\", "/")
    if not temiz:
        return "", "bos yol"
    if os.path.isabs(temiz):
        try:
            temiz = os.path.relpath(temiz, kok).replace(os.sep, "/")
        except Exception:
            return "", f"repo disi mutlak yol: {ham}"
    while temiz.startswith("./"):
        temiz = temiz[2:]
    temiz = temiz.strip("/")
    if not temiz:
        return "", "bos yol"
    if ".." in temiz.split("/"):
        return "", f"repo disina cikan yol: {ham}"
    return temiz, ""


def yasak_mi(yol: str) -> bool:
    """F8 — tam yol VEYA basename yasak listesindeyse True (basename-GENIS)."""
    ad = yol.rsplit("/", 1)[-1]
    return yol in YASAK_ADLAR or ad in YASAK_ADLAR


def kirli_yollar(kok: str) -> list[str]:
    """git status --porcelain'den (rename dahil) calisma agacindaki yollar."""
    sonuc = git(kok, "status", "--porcelain")
    yollar: list[str] = []
    for satir in sonuc.stdout.splitlines():
        if len(satir) < 4:
            continue
        govde = satir[3:]
        if " -> " in govde:
            govde = govde.split(" -> ", 1)[1]
        govde = govde.strip()
        if govde.startswith('"') and govde.endswith('"'):
            try:
                govde = govde[1:-1].encode().decode("unicode_escape")
            except Exception:
                govde = govde[1:-1]
        if govde:
            yollar.append(govde.rstrip("/"))
    return yollar


def kirli_kapsiyor(kirli: str, istenen: str) -> bool:
    """`--dosya` bir dizin de olabilir: kirli yol o dizinin altindaysa kapsanir."""
    return kirli == istenen or kirli.startswith(istenen.rstrip("/") + "/")


class Durum:
    def __init__(self) -> None:
        self.etiket = ""
        self.stash_once = 0
        self.stash_sha = ""
        self.stash_kuruldu = False
        self.stash_dusuruldu = False
        self.worktree_yolu = ""
        self.dal = ""
        self.commit = "YOK"
        self.push_rc = -1
        self.hukum = "BASLAMADI"


def kapat(kok: str, durum: Durum, rc: int) -> int:
    """F6 — arac HANGI yoldan cikarsa ciksin stash muhasebesi basilir."""
    sonra = stash_sayisi(kok)
    bas(
        f"SONUC STASH_ONCE={durum.stash_once} STASH_SONRA={sonra} "
        f"COMMIT={durum.commit} PUSH_RC={durum.push_rc} "
        f"WORKTREE_SATIR={worktree_satirlari(kok)} HUKUM={durum.hukum}"
    )
    return rc


def worktree_temizle(kok: str, durum: Durum) -> int:
    """worktree + dal siler; kalan worktree satir sayisini doner."""
    if durum.worktree_yolu:
        git(kok, "worktree", "remove", "--force", durum.worktree_yolu)
    if durum.dal:
        git(kok, "branch", "-D", durum.dal)
    git(kok, "worktree", "prune")
    return worktree_satirlari(kok)


def stash_iade(kok: str, durum: Durum) -> None:
    """Is HENUZ commit'lenmeden iptal edildiginde calisma agacini geri koyar.

    Giris KIMLIKLE bulunur (stash_indeksi) — koru koru `stash pop` komsu oturumun
    girisini alabilirdi."""
    if durum.stash_kuruldu and not durum.stash_dusuruldu:
        i = stash_indeksi(kok, durum.etiket)
        if i < 0:
            bas("STASH_IADE RC=-1 (giris bulunamadi)")
            return
        sonuc = git(kok, "stash", "pop", f"stash@{{{i}}}")
        bas(f"STASH_IADE RC={sonuc.returncode}")
        if sonuc.returncode == 0:
            durum.stash_dusuruldu = True


def kuru_plan(kok: str, args, yollar: list[str], wt_yolu: str, dal: str) -> None:
    bas("KURU=EVET (hicbir yazma yapilmadi)")
    bas(f"PLAN stash push -u -- {' '.join(shlex.quote(y) for y in yollar)}")
    bas(f"PLAN git worktree add {wt_yolu} -b {dal}")
    bas("PLAN git stash apply  (worktree'de)")
    bas(f"PLAN git add -- {' '.join(shlex.quote(y) for y in yollar)}")
    bas(f"PLAN git commit -F {args.mesaj_dosyasi}")
    bas(f"PLAN git merge --ff-only {dal}")
    bas("PLAN git push origin <dal>")
    bas(f"PLAN git worktree remove --force {wt_yolu} + git branch -D {dal}")


def main() -> int:
    ayrist = argparse.ArgumentParser(add_help=True)
    ayrist.add_argument("--etiket", required=True, help="kisa ad: fix/<etiket> dali")
    ayrist.add_argument("--mesaj-dosyasi", required=True, help="commit mesaji dosyasi (tam yol)")
    ayrist.add_argument("--dosya", action="append", default=[], help="commit'lenecek yol (tekrarlanir)")
    ayrist.add_argument("--kuru", action="store_true", help="F7: hicbir yazma yapma")
    ayrist.add_argument("--taban", default="origin/main", help="uzak taban ref (varsayilan origin/main)")
    ayrist.add_argument("--repo", default=None, help="repo koku (varsayilan: bulundugun repo)")
    args = ayrist.parse_args()

    durum = Durum()
    durum.etiket = args.etiket or ""

    kok = args.repo or git_ok(os.getcwd(), "rev-parse", "--show-toplevel")
    if not kok or not os.path.isdir(kok):
        bas("HUKUM=REPO_YOK")
        return 2
    kok = os.path.realpath(kok)

    if not ETIKET_DESENI.match(args.etiket or ""):
        durum.hukum = "ETIKET_GECERSIZ"
        bas(f"HATA etiket deseni [a-z0-9-]{{1,41}} olmali: {args.etiket!r}")
        return kapat(kok, durum, 2)

    if not os.path.isfile(args.mesaj_dosyasi):
        durum.hukum = "MESAJ_DOSYASI_YOK"
        bas(f"HATA mesaj dosyasi bulunamadi: {args.mesaj_dosyasi}")
        return kapat(kok, durum, 2)

    # ---- F1: bos liste ----------------------------------------------------------------
    # 🔴 Bu satirda YEDEK LISTE YOKTUR. `args.dosya or ["."]` gibi bir "makul varsayilan"
    # araci sessizce "her seyi commit et"e cevirir — yasak olan tam olarak budur.
    istenen_ham = args.dosya or []
    if not istenen_ham:
        durum.hukum = "BOS_LISTE"
        bas("HATA F1: --dosya listesi BOS. 'her seyi commit et' yolu YOKTUR.")
        return kapat(kok, durum, 2)

    yollar: list[str] = []
    for ham in istenen_ham:
        yol, hata = yol_normalle(kok, ham)
        if hata:
            durum.hukum = "YOL_GECERSIZ"
            bas(f"HATA {hata}")
            return kapat(kok, durum, 2)
        # ---- F8: yasak yollar ---------------------------------------------------------
        if yasak_mi(yol):
            durum.hukum = "YASAK_YOL"
            bas(f"HATA F8: yasak yol REDDEDILDI: {yol}")
            bas("VERI DUZLEMI kanonik araclarindir (hasat_ekle.py / urun-ekle.py / duzelt.py); SIR commit'lenmez.")
            return kapat(kok, durum, 2)
        if yol not in yollar:
            yollar.append(yol)

    dal = f"fix/{args.etiket}"
    wt_bagil = os.path.join(".claude", "worktrees", args.etiket)
    wt_yolu = os.path.join(kok, wt_bagil)

    # ---- ADIM 1: on-olcum -------------------------------------------------------------
    kirli = kirli_yollar(kok)
    kapsanan = [k for k in kirli if any(kirli_kapsiyor(k, y) for y in yollar)]
    yabanci = [k for k in kirli if k not in kapsanan]
    bas(f"ADIM1 YABANCI={len(yabanci)} ISTENEN={len(yollar)} KIRLI_ISTENEN={len(kapsanan)}")
    for y in yabanci:
        bas(f"YABANCI_YOL {y}   (DOKUNULMAZ)")

    if not kapsanan:
        durum.hukum = "DEGISIKLIK_YOK"
        bas("HATA istenen yollarin hicbirinde calisma agaci degisikligi YOK.")
        return kapat(kok, durum, 2)

    # ---- ADIM 2: fetch + ILERI/GERI ---------------------------------------------------
    ana_dal = git_ok(kok, "rev-parse", "--abbrev-ref", "HEAD") or "main"
    fetch_rc = 0
    if not args.kuru:
        fetch_rc = git(kok, "fetch", "origin").returncode
    ileri = geri = -1
    sayim = git(kok, "rev-list", "--left-right", "--count", f"{ana_dal}...{args.taban}")
    if sayim.returncode == 0 and sayim.stdout.split():
        parca = sayim.stdout.split()
        ileri, geri = int(parca[0]), int(parca[1])
    bas(f"ADIM2 DAL={ana_dal} TABAN={args.taban} FETCH_RC={fetch_rc} ILERI={ileri} GERI={geri}")

    durum.stash_once = stash_sayisi(kok)

    # ---- F7: kuru kosum ---------------------------------------------------------------
    if args.kuru:
        kuru_plan(kok, args, yollar, wt_bagil, dal)
        durum.hukum = "KURU"
        return kapat(kok, durum, 0)

    if os.path.exists(wt_yolu):
        durum.hukum = "WORKTREE_VAR"
        bas(f"HATA worktree yolu ZATEN VAR: {wt_yolu} (once temizle)")
        return kapat(kok, durum, 2)
    if git(kok, "rev-parse", "--verify", "--quiet", dal).returncode == 0:
        durum.hukum = "DAL_VAR"
        bas(f"HATA dal ZATEN VAR: {dal} (once temizle)")
        return kapat(kok, durum, 2)

    # ---- ADIM 3: pathspec'li stash ----------------------------------------------------
    stash = git(kok, "stash", "push", "-u", "-m", f"onarim-commit:{args.etiket}", "--", *yollar)
    yeni_sayi = stash_sayisi(kok)
    bas(f"ADIM3 STASH_ONCE={durum.stash_once} STASH_PUSH_RC={stash.returncode} STASH_YENI={yeni_sayi}")
    if stash.returncode != 0 or yeni_sayi != durum.stash_once + 1:
        durum.hukum = "STASH_KURULAMADI"
        bas((stash.stderr or stash.stdout).strip()[:800])
        return kapat(kok, durum, 2)
    durum.stash_kuruldu = True
    # S1: kendi girdimizin SHA'sini PUSH'TAN HEMEN SONRA yakala — o an stash@{0} kesin bizim
    # girdi (sonra indeks kayabilir, etiket bile baska iscide tekrarlanabilir; SHA degismez).
    # S3: es-zamanli isci sayaci + STASH_SHA/STASH_YIGIN ciktiya.
    durum.stash_sha = git_ok(kok, "rev-parse", "stash@{0}")
    bas(f"ADIM3 STASH_SHA={durum.stash_sha} STASH_YIGIN={yeni_sayi} "
        f"ES_ZAMANLI_ISCI={es_zamanli_isci_sayisi(kok, durum.stash_sha)}")

    # ---- ADIM 4: worktree + apply + add + commit --------------------------------------
    os.makedirs(os.path.dirname(wt_yolu), exist_ok=True)
    wt = git(kok, "worktree", "add", wt_bagil, "-b", dal)
    if wt.returncode != 0:
        durum.hukum = "WORKTREE_KURULAMADI"
        bas((wt.stderr or wt.stdout).strip()[:800])
        stash_iade(kok, durum)
        return kapat(kok, durum, 2)
    durum.worktree_yolu = wt_yolu
    durum.dal = dal

    if test_kancasi("WORKTREE_SONRA", wt_yolu, kok) != 0:
        durum.hukum = "ADIM_HATASI"
        bas("HATA WORKTREE_SONRA noktasinda kesildi — worktree + dal + stash KORUNDU.")
        return kapat(kok, durum, 3)

    # F5/F6: `apply` (pop DEGIL) — stash basariya kadar ag olarak DURUR. S1: SHA ile uygula;
    # argumansiz `apply` yigin TEPESINI (stash@{0}) alir = baska iscinin girdisini yayinlar.
    uygula = git(wt_yolu, "stash", "apply", durum.stash_sha)
    bas(f"ADIM4A UYGULA_RC={uygula.returncode}")
    if uygula.returncode != 0:
        durum.hukum = "STASH_CAKISMASI"
        bas("HATA F5: stash uygulamasi cakisti — otomatik cozme YOK, worktree KORUNDU.")
        for satir in satirlar(git(wt_yolu, "diff", "--name-only", "--diff-filter=U").stdout):
            bas(f"CAKISAN {satir}")
        bas((uygula.stderr or uygula.stdout).strip()[:800])
        return kapat(kok, durum, 3)

    if test_kancasi("ADD_ONCE", wt_yolu, kok) != 0:
        durum.hukum = "ADIM_HATASI"
        bas("HATA ADD_ONCE noktasinda kesildi — worktree + dal + stash KORUNDU.")
        return kapat(kok, durum, 3)

    # F2: YALNIZ verilen yollar stage'lenir. `git add -A` YASAK.
    ekle = git(wt_yolu, "add", "--", *yollar)
    if ekle.returncode != 0:
        durum.hukum = "ADD_HATASI"
        bas((ekle.stderr or ekle.stdout).strip()[:800])
        worktree_temizle(kok, durum)
        stash_iade(kok, durum)
        return kapat(kok, durum, 2)

    staged = satirlar(git(wt_yolu, "diff", "--cached", "--name-only").stdout)
    fazla = [y for y in staged if not any(kirli_kapsiyor(y, i) for i in yollar)]
    bas(f"ADIM4B STAGE={len(staged)} FAZLA={len(fazla)}")
    if fazla:
        durum.hukum = "YABANCI_STAGE"
        bas("HATA F2: verilen listenin DISINDA yol stage'lendi — GERI ALINIYOR.")
        for y in fazla:
            bas(f"FAZLA_YOL {y}")
        worktree_temizle(kok, durum)
        durum.worktree_yolu = ""
        durum.dal = ""
        stash_iade(kok, durum)
        return kapat(kok, durum, 2)
    if not staged:
        durum.hukum = "STAGE_BOS"
        bas("HATA stage BOS — commit'lenecek degisiklik yok.")
        worktree_temizle(kok, durum)
        durum.worktree_yolu = ""
        durum.dal = ""
        stash_iade(kok, durum)
        return kapat(kok, durum, 2)

    commit = git(wt_yolu, "commit", "-F", os.path.abspath(args.mesaj_dosyasi))
    if commit.returncode != 0:
        durum.hukum = "COMMIT_REDDEDILDI"
        bas((commit.stderr or commit.stdout).strip()[:1200])
        bas("HATA commit reddedildi — worktree + dal + stash KORUNDU.")
        return kapat(kok, durum, 3)
    durum.commit = git_ok(wt_yolu, "rev-parse", "HEAD")[:12] or "YOK"
    bas(f"ADIM4C COMMIT={durum.commit} DAL={dal}")

    # ---- ADIM 5: --ff-only merge ------------------------------------------------------
    if test_kancasi("MERGE_ONCE", kok, kok) != 0:
        durum.hukum = "ADIM_HATASI"
        bas("HATA MERGE_ONCE noktasinda kesildi — is DAL'da ve STASH'te DURUYOR (F6).")
        return kapat(kok, durum, 3)

    merge = git(kok, "merge", "--ff-only", dal)
    bas(f"ADIM5 FF_RC={merge.returncode} MAIN={git_ok(kok, 'rev-parse', 'HEAD')[:12]}")
    if merge.returncode != 0:
        durum.hukum = "FF_IMKANSIZ"
        bas("HATA F3: --ff-only merge basarisiz — MERGE COMMIT URETILMEDI (mimar hukmu gerekir).")
        bas(f"KORUNDU worktree={wt_bagil} dal={dal} stash=+1")
        bas((merge.stderr or merge.stdout).strip()[:800])
        return kapat(kok, durum, 3)

    # ---- ADIM 6: push (F4: en fazla 1 tekrar, --force ASLA) ---------------------------
    deneme = 1
    itme = git(kok, "push", "origin", ana_dal)
    if itme.returncode != 0:
        bas(f"ADIM6A PUSH_RC={itme.returncode} (reddedildi — fetch + merge {args.taban} + TEK tekrar)")
        bas((itme.stderr or itme.stdout).strip()[:500])
        git(kok, "fetch", "origin")
        birlestir = git(kok, "merge", args.taban)
        bas(f"ADIM6B UZAK_MERGE_RC={birlestir.returncode}")
        if birlestir.returncode != 0:
            durum.push_rc = itme.returncode
            durum.hukum = "UZAK_MERGE_CAKISMASI"
            bas("HATA uzak taban ile merge cakisti — insan/mimar karari gerekir.")
            return kapat(kok, durum, 3)
        deneme = 2
        itme = git(kok, "push", "origin", ana_dal)
    durum.push_rc = itme.returncode
    bas(f"ADIM6 PUSH_RC={itme.returncode} DENEME={deneme}")
    if itme.returncode != 0:
        durum.hukum = "PUSH_REDDEDILDI"
        bas("HATA F4: push ikinci kez de reddedildi — DUR. --force KULLANILMAZ.")
        bas((itme.stderr or itme.stdout).strip()[:500])
        return kapat(kok, durum, 3)

    # ---- ADIM 7: temizlik -------------------------------------------------------------
    kalan = worktree_temizle(kok, durum)
    durum.worktree_yolu = ""
    durum.dal = ""
    # S2: DROP da indeks/etiket degil SHA ile. SHA bulunamazsa DROP ETME (fail-closed):
    # komsu oturumun isi yigunda KORUNUR.
    i = stash_sha_indeksi(kok, durum.stash_sha)
    if i < 0:
        durum.hukum = "STASH_KORUNDU"
        bas("HATA: kendi stash girdisi SHA ile bulunamadi — DROP EDILMEDI (STASH_KORUNDU).")
        bas(f"ADIM7 WORKTREE_SATIR={kalan} STASH_DROP_RC=-1")
        return kapat(kok, durum, 0)
    dusur = git(kok, "stash", "drop", f"stash@{{{i}}}")
    if dusur.returncode == 0:
        durum.stash_dusuruldu = True
    bas(f"ADIM7 WORKTREE_SATIR={kalan} STASH_DROP_RC={dusur.returncode}")

    durum.hukum = "KAPANDI"
    return kapat(kok, durum, 0)


if __name__ == "__main__":
    raise SystemExit(main())
