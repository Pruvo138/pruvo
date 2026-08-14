#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""onarim-commit-test.py — tools/onarim-commit.py KABUL TESTI (ag YOK, canli agaca YAZMAZ).

Her vaka GECICI bir dizinde SENTETIK bir git deposu (bare uzak + yerel klon) kurar ve araci
GERCEKTEN kosar. Metin eslemesi DEGIL: hukum, commit icerigi, uzak depo ve calisma agaci
KOSUM SONRASI olculur. Butun gecici depolar kosum sonunda SILINIR (disk emri).

# CI-ALT-KUME: --mutasyon

VAKALAR
  V1  mutlu yol: 2 dosya -> commit + ff-merge + push + worktree 0 kaldi + stash bosaldi
  V2  F1 bos liste -> rc!=0 (HUKUM=BOS_LISTE), depo DEGISMEDI
  V3  yabanci kirli dosya -> commit'e GIRMEDI, calisma agacinda AYNEN duruyor
  V3B worktree'de bassiz (untracked) artik -> commit'e GIRMEDI, kosum YESIL
  V4  F3 ff imkansiz (main ilerledi) -> DUR, dal + worktree KORUNDU, FF_IMKANSIZ
  V5  F4 push bir kez reddedilir -> fetch+merge sonrasi basarili, UZAKTAKI commit KAYBOLMADI
  V5B push HER SEFERINDE reddedilir -> ikinci redde DUR (DENEME=2)
  V6  F5 stash cakismasi -> DUR, worktree KORUNUR, cakisan dosya adi basilir
  V7  F6 yarida kesme (adim 5'te hata enjekte) -> stash BOS DEGIL, is dalda kurtarilabilir
  V8  F8 urunler.json verilir -> REDDEDILIR, depo DEGISMEDI
  V9  --kuru -> HEAD/status/stash/worktree/dal listesi KOSUM ONCESI ile AYNI
  V10 kaynak taramasi: "--force" / "--force-with-lease" / "--no-verify" KAYNAKTA GECMEZ

MUTASYON BATARYASI (--mutasyon): kanonik kaynak GECICI dizine kopyalanir, TEK satir
degistirilir ve o mutanta karsi ILGILI vaka kosulur. Vaka YESIL kalirsa mutant HAYATTADIR
(kapi kordur). Kanonik kaynak sha256 ile kosum oncesi/sonrasi karsilastirilir — batarya
canli dosyaya DOKUNMAZ.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

BURASI = os.path.dirname(os.path.abspath(__file__))
KANONIK_ARAC = os.path.join(BURASI, "onarim-commit.py")

ORTAM = dict(os.environ)
ORTAM["GIT_CONFIG_GLOBAL"] = os.devnull
ORTAM["GIT_CONFIG_SYSTEM"] = os.devnull
ORTAM["GIT_AUTHOR_NAME"] = "pruvo-test"
ORTAM["GIT_AUTHOR_EMAIL"] = "test@example.invalid"
ORTAM["GIT_COMMITTER_NAME"] = "pruvo-test"
ORTAM["GIT_COMMITTER_EMAIL"] = "test@example.invalid"
ORTAM["GIT_TERMINAL_PROMPT"] = "0"
ORTAM.pop("PRUVO_ONARIM_TEST_KANCA", None)
ORTAM.pop("PRUVO_MIMAR_ONAY", None)


# --------------------------------------------------------------------------- yardimcilar
def kos(argv: list[str], cwd: str | None = None, ortam: dict | None = None):
    return subprocess.run(
        argv, cwd=cwd, env=ortam or ORTAM, capture_output=True, text=True, check=False
    )


def g(kok: str, *argv: str, ortam: dict | None = None):
    return kos(["git", "-C", kok, *argv], ortam=ortam)


def gs(kok: str, *argv: str) -> str:
    return g(kok, *argv).stdout.strip()


def yaz(yol: str, icerik: str) -> None:
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(icerik)


def oku(yol: str) -> str:
    with open(yol, encoding="utf-8") as f:
        return f.read()


def hukum_al(cikti: str) -> str:
    for satir in reversed(cikti.splitlines()):
        if satir.startswith("SONUC ") and "HUKUM=" in satir:
            return satir.split("HUKUM=", 1)[1].strip()
    return "YOK"


def alan(cikti: str, anahtar: str) -> str:
    """Ciktidaki son `<anahtar>=<deger>` jetonunu doner."""
    deger = ""
    for satir in cikti.splitlines():
        for jeton in satir.split():
            if jeton.startswith(anahtar + "="):
                deger = jeton.split("=", 1)[1]
    return deger


def fikstur(tepe: str) -> tuple[str, str]:
    """bare uzak + yerel klon; taban commit'i: tools/x.py, tools/z.py, yabanci.txt"""
    uzak = os.path.join(tepe, "uzak.git")
    yerel = os.path.join(tepe, "yerel")
    kos(["git", "init", "--bare", "-b", "main", uzak])
    kos(["git", "init", "-b", "main", yerel])
    yaz(os.path.join(yerel, "tools", "x.py"), "print('taban x')\n")
    yaz(os.path.join(yerel, "tools", "z.py"), "print('taban z')\n")
    yaz(os.path.join(yerel, "yabanci.txt"), "yabanci taban\n")
    g(yerel, "add", "-A")
    g(yerel, "commit", "-m", "taban")
    g(yerel, "remote", "add", "origin", uzak)
    g(yerel, "push", "-u", "origin", "main")
    return uzak, yerel


def mesaj_dosyasi(tepe: str, metin: str = "onarim: kabul testi commit'i\n") -> str:
    yol = os.path.join(tepe, "mesaj.txt")
    yaz(yol, metin)
    return yol


def arac_kos(arac: str, yerel: str, *argv: str, kanca: str | None = None):
    ortam = dict(ORTAM)
    if kanca:
        ortam["PRUVO_ONARIM_TEST_KANCA"] = kanca
    return kos(["python3", arac, "--repo", yerel, *argv], ortam=ortam)


def commit_dosyalari(kok: str, ref: str) -> list[str]:
    return sorted(
        s for s in gs(kok, "show", "--name-only", "--pretty=format:", ref).splitlines() if s.strip()
    )


def ata_mi(kok: str, ata: str, torun: str) -> bool:
    return g(kok, "merge-base", "--is-ancestor", ata, torun).returncode == 0


# ------------------------------------------------------------------------------- vakalar
def v1_mutlu_yol(arac: str, tepe: str) -> tuple[bool, str]:
    uzak, yerel = fikstur(tepe)
    yaz(os.path.join(yerel, "tools", "x.py"), "print('onarildi x')\n")
    yaz(os.path.join(yerel, "tools", "y.py"), "print('yeni y')\n")
    sonuc = arac_kos(
        arac, yerel, "--etiket", "mutlu", "--mesaj-dosyasi", mesaj_dosyasi(tepe),
        "--dosya", "tools/x.py", "--dosya", "tools/y.py",
    )
    if sonuc.returncode != 0:
        return False, f"rc={sonuc.returncode} bekleniyordu 0\n{sonuc.stdout}{sonuc.stderr}"
    if hukum_al(sonuc.stdout) != "KAPANDI":
        return False, f"HUKUM={hukum_al(sonuc.stdout)}\n{sonuc.stdout}"
    dosyalar = commit_dosyalari(yerel, "HEAD")
    if dosyalar != ["tools/x.py", "tools/y.py"]:
        return False, f"commit icerigi {dosyalar}"
    if gs(yerel, "rev-parse", "HEAD") != gs(uzak, "rev-parse", "main"):
        return False, "uzak main yerel main'e esit degil (push inmedi)"
    if len([s for s in gs(yerel, "worktree", "list").splitlines() if s.strip()]) != 1:
        return False, "worktree list tek satir degil"
    if gs(yerel, "stash", "list"):
        return False, "stash bosalmadi"
    if g(yerel, "rev-parse", "--verify", "--quiet", "fix/mutlu").returncode == 0:
        return False, "fix/mutlu dali silinmedi"
    if os.path.exists(os.path.join(yerel, ".claude", "worktrees", "mutlu")):
        return False, "worktree dizini diskte kaldi"
    if gs(yerel, "status", "--porcelain"):
        return False, f"calisma agaci kirli kaldi: {gs(yerel, 'status', '--porcelain')}"
    return True, "commit+ff+push+temizlik"


def v2_bos_liste(arac: str, tepe: str) -> tuple[bool, str]:
    uzak, yerel = fikstur(tepe)
    yaz(os.path.join(yerel, "tools", "x.py"), "print('onarildi x')\n")
    once = (gs(yerel, "rev-parse", "HEAD"), gs(yerel, "status", "--porcelain"))
    sonuc = arac_kos(arac, yerel, "--etiket", "bos", "--mesaj-dosyasi", mesaj_dosyasi(tepe))
    if sonuc.returncode == 0:
        return False, f"F1 acildi: rc=0\n{sonuc.stdout}"
    if hukum_al(sonuc.stdout) != "BOS_LISTE":
        return False, f"HUKUM={hukum_al(sonuc.stdout)} (BOS_LISTE bekleniyordu)\n{sonuc.stdout}"
    if (gs(yerel, "rev-parse", "HEAD"), gs(yerel, "status", "--porcelain")) != once:
        return False, "depo degisti"
    if gs(uzak, "rev-parse", "main") != once[0]:
        return False, "uzak depo degisti"
    return True, "rc!=0 + BOS_LISTE + depo degismedi"


def v3_yabanci_kirli(arac: str, tepe: str) -> tuple[bool, str]:
    uzak, yerel = fikstur(tepe)
    yaz(os.path.join(yerel, "tools", "x.py"), "print('onarildi x')\n")
    yaz(os.path.join(yerel, "yabanci.txt"), "BASKA OTURUMUN CANLI ISI\n")
    yaz(os.path.join(yerel, "yabanci-yeni.txt"), "izlenmeyen yabanci\n")
    sonuc = arac_kos(
        arac, yerel, "--etiket", "yabanci", "--mesaj-dosyasi", mesaj_dosyasi(tepe),
        "--dosya", "tools/x.py",
    )
    if sonuc.returncode != 0:
        return False, f"rc={sonuc.returncode}\n{sonuc.stdout}{sonuc.stderr}"
    dosyalar = commit_dosyalari(yerel, "HEAD")
    if dosyalar != ["tools/x.py"]:
        return False, f"commit icerigi {dosyalar} (yabanci sizdi)"
    if oku(os.path.join(yerel, "yabanci.txt")) != "BASKA OTURUMUN CANLI ISI\n":
        return False, "yabanci.txt icerigi degisti"
    if oku(os.path.join(yerel, "yabanci-yeni.txt")) != "izlenmeyen yabanci\n":
        return False, "yabanci-yeni.txt icerigi degisti"
    if "yabanci.txt" not in gs(yerel, "status", "--porcelain"):
        return False, "yabanci.txt artik kirli degil (stash'e girmis)"
    if alan(sonuc.stdout, "YABANCI") != "2":
        return False, f"YABANCI sayaci {alan(sonuc.stdout, 'YABANCI')} (2 bekleniyordu)"
    return True, "yabanci commit'e girmedi + agacta AYNEN duruyor"


def v3b_worktree_artigi(arac: str, tepe: str) -> tuple[bool, str]:
    """ADD_ONCE dikisi worktree'ye izlenmeyen bir artik birakir (or. bir aracin uretttigi
    ara dosya). Kanonik arac YALNIZ verilen yollari stage'ler -> artik commit'e GIRMEZ."""
    uzak, yerel = fikstur(tepe)
    yaz(os.path.join(yerel, "tools", "x.py"), "print('onarildi x')\n")
    sonuc = arac_kos(
        arac, yerel, "--etiket", "artik", "--mesaj-dosyasi", mesaj_dosyasi(tepe),
        "--dosya", "tools/x.py",
        kanca="ADD_ONCE:printf 'artik\\n' > worktree-artigi.txt",
    )
    if sonuc.returncode != 0:
        return False, f"rc={sonuc.returncode} (artik commit'e sizdi / F2 tetiklendi)\n{sonuc.stdout}"
    dosyalar = commit_dosyalari(yerel, "HEAD")
    if dosyalar != ["tools/x.py"]:
        return False, f"commit icerigi {dosyalar} (worktree artigi sizdi)"
    return True, "worktree artigi stage'lenmedi"


def v4_ff_imkansiz(arac: str, tepe: str) -> tuple[bool, str]:
    uzak, yerel = fikstur(tepe)
    yaz(os.path.join(yerel, "tools", "x.py"), "print('onarildi x')\n")
    kanca = "MERGE_ONCE:printf 'ileri\\n' > ileri.txt && git add ileri.txt && git commit -q -m ileri"
    sonuc = arac_kos(
        arac, yerel, "--etiket", "ffyok", "--mesaj-dosyasi", mesaj_dosyasi(tepe),
        "--dosya", "tools/x.py", kanca=kanca,
    )
    if sonuc.returncode == 0:
        return False, f"F3 acildi: rc=0 (merge commit uretilmis olabilir)\n{sonuc.stdout}"
    if hukum_al(sonuc.stdout) != "FF_IMKANSIZ":
        return False, f"HUKUM={hukum_al(sonuc.stdout)} (FF_IMKANSIZ bekleniyordu)\n{sonuc.stdout}"
    if gs(yerel, "log", "-1", "--pretty=%s") != "ileri":
        return False, "main'de merge commit'i uretilmis (ff-only ihlali)"
    if len(gs(yerel, "log", "-1", "--pretty=%p").split()) != 1:
        return False, "main ucu iki ebeveynli (merge commit)"
    if g(yerel, "rev-parse", "--verify", "--quiet", "fix/ffyok").returncode != 0:
        return False, "dal KORUNMADI (is kayboldu)"
    if not os.path.isdir(os.path.join(yerel, ".claude", "worktrees", "ffyok")):
        return False, "worktree KORUNMADI"
    if not gs(yerel, "stash", "list"):
        return False, "stash KORUNMADI"
    return True, "DUR + merge commit YOK + dal/worktree/stash korundu"


def v5_push_bir_kez_red(arac: str, tepe: str) -> tuple[bool, str]:
    uzak, yerel = fikstur(tepe)
    ikinci = os.path.join(tepe, "yerel2")
    kos(["git", "clone", uzak, ikinci])
    yaz(os.path.join(ikinci, "uzak-ilerledi.txt"), "baska mimarin isi\n")
    g(ikinci, "add", "-A")
    g(ikinci, "commit", "-m", "uzak ilerledi")
    g(ikinci, "push", "origin", "main")
    uzak_sha = gs(uzak, "rev-parse", "main")

    yaz(os.path.join(yerel, "tools", "x.py"), "print('onarildi x')\n")
    sonuc = arac_kos(
        arac, yerel, "--etiket", "itme", "--mesaj-dosyasi", mesaj_dosyasi(tepe),
        "--dosya", "tools/x.py",
    )
    if sonuc.returncode != 0:
        return False, f"rc={sonuc.returncode} (fetch+merge sonrasi push basarili olmaliydi)\n{sonuc.stdout}{sonuc.stderr}"
    # EN AGIR EKSEN ONCE OLCULUR: veri kaybi (uzaktaki commit'in ezilmesi).
    yeni_uzak = gs(uzak, "rev-parse", "main")
    if not ata_mi(uzak, uzak_sha, yeni_uzak):
        return False, "UZAKTAKI commit KAYBOLDU (zorlamali itme yapilmis)"
    if not ata_mi(uzak, gs(yerel, "rev-parse", "HEAD"), yeni_uzak):
        return False, "kendi commit'imiz uzaga inmedi"
    if alan(sonuc.stdout, "DENEME") != "2":
        return False, f"DENEME={alan(sonuc.stdout, 'DENEME')} (2 bekleniyordu)"
    return True, "bir red + fetch/merge + tekrar; uzaktaki commit korundu"


def v5b_push_hep_red(arac: str, tepe: str) -> tuple[bool, str]:
    uzak, yerel = fikstur(tepe)
    kanca_yolu = os.path.join(uzak, "hooks", "pre-receive")
    yaz(kanca_yolu, "#!/bin/sh\necho 'uzak reddetti' >&2\nexit 1\n")
    os.chmod(kanca_yolu, 0o755)
    yaz(os.path.join(yerel, "tools", "x.py"), "print('onarildi x')\n")
    sonuc = arac_kos(
        arac, yerel, "--etiket", "hepred", "--mesaj-dosyasi", mesaj_dosyasi(tepe),
        "--dosya", "tools/x.py",
    )
    if sonuc.returncode == 0:
        return False, f"ikinci redde DURMADI: rc=0\n{sonuc.stdout}"
    if hukum_al(sonuc.stdout) != "PUSH_REDDEDILDI":
        return False, f"HUKUM={hukum_al(sonuc.stdout)}\n{sonuc.stdout}"
    if alan(sonuc.stdout, "DENEME") != "2":
        return False, f"DENEME={alan(sonuc.stdout, 'DENEME')} (tam 2 bekleniyordu)"
    return True, "iki deneme sonrasi DUR"


def v6_stash_cakismasi(arac: str, tepe: str) -> tuple[bool, str]:
    uzak, yerel = fikstur(tepe)
    yaz(os.path.join(yerel, "tools", "x.py"), "print('isci onarimi')\n")
    kanca = (
        "WORKTREE_SONRA:printf \"print('cakisan icerik')\\n\" > tools/x.py "
        "&& git add tools/x.py && git commit -q -m cakisma"
    )
    sonuc = arac_kos(
        arac, yerel, "--etiket", "cakisma", "--mesaj-dosyasi", mesaj_dosyasi(tepe),
        "--dosya", "tools/x.py", kanca=kanca,
    )
    if sonuc.returncode == 0:
        return False, f"cakismada DURMADI: rc=0\n{sonuc.stdout}"
    if hukum_al(sonuc.stdout) != "STASH_CAKISMASI":
        return False, f"HUKUM={hukum_al(sonuc.stdout)}\n{sonuc.stdout}"
    if "CAKISAN tools/x.py" not in sonuc.stdout:
        return False, f"cakisan dosya adi basilmadi\n{sonuc.stdout}"
    if not os.path.isdir(os.path.join(yerel, ".claude", "worktrees", "cakisma")):
        return False, "worktree KORUNMADI"
    if not gs(yerel, "stash", "list"):
        return False, "stash KORUNMADI"
    return True, "DUR + cakisan dosya basildi + worktree/stash korundu"


def v7_yarida_kesme(arac: str, tepe: str) -> tuple[bool, str]:
    uzak, yerel = fikstur(tepe)
    yaz(os.path.join(yerel, "tools", "x.py"), "print('onarildi x')\n")
    sonuc = arac_kos(
        arac, yerel, "--etiket", "kesik", "--mesaj-dosyasi", mesaj_dosyasi(tepe),
        "--dosya", "tools/x.py", kanca="MERGE_ONCE:exit 7",
    )
    if sonuc.returncode == 0:
        return False, f"enjekte edilen hatada DURMADI: rc=0\n{sonuc.stdout}"
    if not gs(yerel, "stash", "list"):
        return False, "F6 IHLALI: stash listesi BOS (is kayboldu)"
    if g(yerel, "rev-parse", "--verify", "--quiet", "fix/kesik").returncode != 0:
        return False, "dal yok (is kurtarilamaz)"
    dal_icerik = gs(yerel, "show", "fix/kesik:tools/x.py")
    if "onarildi x" not in dal_icerik:
        return False, "dal onarimi tasimiyor"
    if alan(sonuc.stdout, "STASH_SONRA") != str(int(alan(sonuc.stdout, "STASH_ONCE")) + 1):
        return False, f"STASH muhasebesi tutmuyor: {sonuc.stdout}"
    return True, "stash + dal ikisi birden korundu"


def v8_yasak_yol(arac: str, tepe: str) -> tuple[bool, str]:
    uzak, yerel = fikstur(tepe)
    yaz(os.path.join(yerel, "urunler.json"), "[]\n")
    g(yerel, "add", "-A")
    g(yerel, "commit", "-m", "urunler taban")
    g(yerel, "push", "origin", "main")
    yaz(os.path.join(yerel, "urunler.json"), '[{"id":"sahte"}]\n')
    yaz(os.path.join(yerel, "tools", "x.py"), "print('onarildi x')\n")
    once = (gs(yerel, "rev-parse", "HEAD"), gs(yerel, "status", "--porcelain"), gs(yerel, "stash", "list"))
    sonuc = arac_kos(
        arac, yerel, "--etiket", "yasak", "--mesaj-dosyasi", mesaj_dosyasi(tepe),
        "--dosya", "tools/x.py", "--dosya", "urunler.json",
    )
    if sonuc.returncode == 0:
        return False, f"F8 acildi: rc=0\n{sonuc.stdout}"
    if hukum_al(sonuc.stdout) != "YASAK_YOL":
        return False, f"HUKUM={hukum_al(sonuc.stdout)}\n{sonuc.stdout}"
    if (gs(yerel, "rev-parse", "HEAD"), gs(yerel, "status", "--porcelain"), gs(yerel, "stash", "list")) != once:
        return False, "depo degisti"
    return True, "urunler.json REDDEDILDI + depo degismedi"


def v9_kuru(arac: str, tepe: str) -> tuple[bool, str]:
    uzak, yerel = fikstur(tepe)
    yaz(os.path.join(yerel, "tools", "x.py"), "print('onarildi x')\n")
    yaz(os.path.join(yerel, "tools", "y.py"), "print('yeni y')\n")

    def anlik():
        return (
            gs(yerel, "rev-parse", "HEAD"),
            gs(yerel, "status", "--porcelain"),
            gs(yerel, "stash", "list"),
            gs(yerel, "worktree", "list"),
            gs(yerel, "branch", "--list"),
            gs(uzak, "rev-parse", "main"),
        )

    once = anlik()
    sonuc = arac_kos(
        arac, yerel, "--etiket", "kuru", "--mesaj-dosyasi", mesaj_dosyasi(tepe),
        "--dosya", "tools/x.py", "--dosya", "tools/y.py", "--kuru",
    )
    if sonuc.returncode != 0:
        return False, f"rc={sonuc.returncode}\n{sonuc.stdout}{sonuc.stderr}"
    if hukum_al(sonuc.stdout) != "KURU":
        return False, f"HUKUM={hukum_al(sonuc.stdout)}\n{sonuc.stdout}"
    if anlik() != once:
        return False, "F7 IHLALI: --kuru kosumu depoyu degistirdi"
    return True, "hicbir yazma yok"


def v10_kaynak_taramasi(arac: str, tepe: str) -> tuple[bool, str]:
    """F4'un STATIK sirti: zorlamali itme bayraklari ve kapi atlatma KAYNAKTA GECMEZ.
    (Davranissal kanit V5'tedir; bu vaka ikinci eksendir.)"""
    kaynak = oku(arac)
    bulunan = [j for j in ('"--force-with-lease"', '"--no-verify"') if j in kaynak]
    for no, satir in enumerate(kaynak.splitlines(), start=1):
        if '"push"' in satir and "--force" in satir:
            bulunan.append(f"satir {no}: zorlamali itme")
    if bulunan:
        return False, f"yasak bayrak kaynakta: {bulunan}"
    return True, "zorlamali/atlatma bayragi yok"


def v11_stash_yarisi(arac: str, tepe: str) -> tuple[bool, str]:
    """YARIS (bu isin kalbi): A push -> B push (WORKTREE_SONRA dikisi yigina IKINCI girdi
    birakir) -> A apply -> A KENDI degisikligini alir (B'ninkini DEGIL). Commit iceriginde
    A'nin dosyasi olmali, B'nin dosyasi OLMAMALI."""
    uzak, yerel = fikstur(tepe)
    yaz(os.path.join(yerel, "tools", "x.py"), "print('A iscinin onarimi')\n")
    kanca = "WORKTREE_SONRA:printf 'B\\n' > b-dosyasi.txt && git stash push -u -q -m onarim-commit:b-diger"
    sonuc = arac_kos(
        arac, yerel, "--etiket", "yaris", "--mesaj-dosyasi", mesaj_dosyasi(tepe),
        "--dosya", "tools/x.py", kanca=kanca,
    )
    if sonuc.returncode != 0:
        return False, f"rc={sonuc.returncode} bekleniyordu 0\n{sonuc.stdout}{sonuc.stderr}"
    if hukum_al(sonuc.stdout) != "KAPANDI":
        return False, f"HUKUM={hukum_al(sonuc.stdout)}\n{sonuc.stdout}"
    dosyalar = commit_dosyalari(yerel, "HEAD")
    if dosyalar != ["tools/x.py"]:
        return False, f"commit icerigi {dosyalar} (B'nin dosyasi sizdi)"
    if "A iscinin onarimi" not in gs(yerel, "show", "HEAD:tools/x.py"):
        return False, "A'nin icerigi commit'te degil (B uygulanmis olabilir)"
    return True, "A kendi degisikligini aldi, B commit'e girmedi"


def v12_drop_komsuyu_korur(arac: str, tepe: str) -> tuple[bool, str]:
    """A drop -> B'nin girdisi yiginda AYNEN durur (komsunun isi dusmez)."""
    uzak, yerel = fikstur(tepe)
    yaz(os.path.join(yerel, "tools", "x.py"), "print('A iscinin onarimi')\n")
    kanca = "WORKTREE_SONRA:printf 'B\\n' > b-dosyasi.txt && git stash push -u -q -m onarim-commit:b-diger"
    sonuc = arac_kos(
        arac, yerel, "--etiket", "komsu", "--mesaj-dosyasi", mesaj_dosyasi(tepe),
        "--dosya", "tools/x.py", kanca=kanca,
    )
    if sonuc.returncode != 0:
        return False, f"rc={sonuc.returncode}\n{sonuc.stdout}{sonuc.stderr}"
    liste = gs(yerel, "stash", "list")
    if "onarim-commit:b-diger" not in liste:
        return False, f"B'nin girdisi yiginda YOK (komsunun isi dustu):\n{liste}"
    if "onarim-commit:komsu" in liste:
        return False, f"A'nin kendi girdisi hala yiginda:\n{liste}"
    return True, "A dustu, B yiginda AYNEN durdu"


def v13_sha_yok_korunur(arac: str, tepe: str) -> tuple[bool, str]:
    """SHA bulunamazsa drop YAPILMAZ ve girdi korunur (HUKUM=STASH_KORUNDU)."""
    uzak, yerel = fikstur(tepe)
    yaz(os.path.join(yerel, "komsu.txt"), "komsu oturumun isi\n")
    g(yerel, "stash", "push", "-u", "-m", "gecici: komsu")
    yaz(os.path.join(yerel, "tools", "x.py"), "print('A iscinin onarimi')\n")
    kanca = "MERGE_ONCE:git stash drop 'stash@{0}'"
    sonuc = arac_kos(
        arac, yerel, "--etiket", "shayok", "--mesaj-dosyasi", mesaj_dosyasi(tepe),
        "--dosya", "tools/x.py", kanca=kanca,
    )
    if sonuc.returncode != 0:
        return False, f"rc={sonuc.returncode} (STASH_KORUNDU rc=0 olmaliydi)\n{sonuc.stdout}{sonuc.stderr}"
    if hukum_al(sonuc.stdout) != "STASH_KORUNDU":
        return False, f"HUKUM={hukum_al(sonuc.stdout)} (STASH_KORUNDU bekleniyordu)\n{sonuc.stdout}"
    if "gecici: komsu" not in gs(yerel, "stash", "list"):
        return False, "komsu girdi korunmadi"
    return True, "SHA yok -> DROP YOK, komsu korundu (STASH_KORUNDU)"


def v14_alakasiz_eski_girdiler(arac: str, tepe: str) -> tuple[bool, str]:
    """Yiginda ALAKASIZ eski girdiler varken (iki 'gecici: ...') arac dogru calisir ve
    onlara DOKUNMAZ — bugunku gercek durum (yiginda 10 Agu'dan kalma girdiler var)."""
    uzak, yerel = fikstur(tepe)
    yaz(os.path.join(yerel, "eski1.txt"), "eski1\n")
    g(yerel, "stash", "push", "-u", "-m", "gecici: eski1")
    yaz(os.path.join(yerel, "eski2.txt"), "eski2\n")
    g(yerel, "stash", "push", "-u", "-m", "gecici: eski2")
    yaz(os.path.join(yerel, "tools", "x.py"), "print('A iscinin onarimi')\n")
    sonuc = arac_kos(
        arac, yerel, "--etiket", "eski", "--mesaj-dosyasi", mesaj_dosyasi(tepe),
        "--dosya", "tools/x.py",
    )
    if sonuc.returncode != 0:
        return False, f"rc={sonuc.returncode}\n{sonuc.stdout}{sonuc.stderr}"
    if hukum_al(sonuc.stdout) != "KAPANDI":
        return False, f"HUKUM={hukum_al(sonuc.stdout)}\n{sonuc.stdout}"
    liste = gs(yerel, "stash", "list")
    if "gecici: eski1" not in liste or "gecici: eski2" not in liste:
        return False, f"alakasiz eski girdi dustu:\n{liste}"
    if "onarim-commit:eski" in liste:
        return False, f"kendi girdimiz dusmedi:\n{liste}"
    if len([s for s in liste.splitlines() if s.strip()]) != 2:
        return False, f"yigin sayisi 2 bekleniyordu (yalniz 2 eski kalmali):\n{liste}"
    return True, "eski girdiler korundu, yalniz kendi girdimiz dustu"


def v15_es_zamanli_sayac(arac: str, tepe: str) -> tuple[bool, str]:
    """ES_ZAMANLI_ISCI sayaci: yiginda onceden baska bir onarim-commit girdisi varken
    sayac 1 basilir; STASH_SHA basilir; komsu girdi korunur."""
    uzak, yerel = fikstur(tepe)
    yaz(os.path.join(yerel, "diger.txt"), "diger isci dosyasi\n")
    g(yerel, "stash", "push", "-u", "-m", "onarim-commit:diger-isci")
    yaz(os.path.join(yerel, "tools", "x.py"), "print('A iscinin onarimi')\n")
    sonuc = arac_kos(
        arac, yerel, "--etiket", "sayac", "--mesaj-dosyasi", mesaj_dosyasi(tepe),
        "--dosya", "tools/x.py",
    )
    if sonuc.returncode != 0:
        return False, f"rc={sonuc.returncode}\n{sonuc.stdout}{sonuc.stderr}"
    if hukum_al(sonuc.stdout) != "KAPANDI":
        return False, f"HUKUM={hukum_al(sonuc.stdout)}\n{sonuc.stdout}"
    if alan(sonuc.stdout, "ES_ZAMANLI_ISCI") != "1":
        return False, f"ES_ZAMANLI_ISCI={alan(sonuc.stdout, 'ES_ZAMANLI_ISCI')} (1 bekleniyordu)\n{sonuc.stdout}"
    if len(alan(sonuc.stdout, "STASH_SHA")) != 40:
        return False, f"STASH_SHA={alan(sonuc.stdout, 'STASH_SHA')} (40 hex bekleniyordu)\n{sonuc.stdout}"
    if "onarim-commit:diger-isci" not in gs(yerel, "stash", "list"):
        return False, "diger iscinin girdisi korunmadi"
    return True, "ES_ZAMANLI_ISCI=1 + STASH_SHA basildi + komsu korundu"


VAKALAR = [
    ("V1  mutlu yol", v1_mutlu_yol),
    ("V2  F1 bos liste", v2_bos_liste),
    ("V3  yabanci kirli dosya", v3_yabanci_kirli),
    ("V3B worktree artigi", v3b_worktree_artigi),
    ("V4  F3 ff imkansiz", v4_ff_imkansiz),
    ("V5  F4 push bir kez red", v5_push_bir_kez_red),
    ("V5B push hep red", v5b_push_hep_red),
    ("V6  F5 stash cakismasi", v6_stash_cakismasi),
    ("V7  F6 yarida kesme", v7_yarida_kesme),
    ("V8  F8 yasak yol", v8_yasak_yol),
    ("V9  F7 kuru kosum", v9_kuru),
    ("V10 kaynak taramasi", v10_kaynak_taramasi),
    ("V11 stash yarisi (A kendini alir)", v11_stash_yarisi),
    ("V12 drop komsuyu korur", v12_drop_komsuyu_korur),
    ("V13 SHA yok -> STASH_KORUNDU", v13_sha_yok_korunur),
    ("V14 alakasiz eski girdiler", v14_alakasiz_eski_girdiler),
    ("V15 es-zamanli isci sayaci", v15_es_zamanli_sayac),
]

VAKA_ADI = {ad.split()[0]: (ad, fn) for ad, fn in VAKALAR}


def vaka_kos(anahtar: str, arac: str, kok_tmp: str) -> tuple[bool, str]:
    ad, fn = VAKA_ADI[anahtar]
    tepe = tempfile.mkdtemp(prefix=f"onarim-{anahtar}-", dir=kok_tmp)
    try:
        return fn(arac, tepe)
    except Exception as hata:  # vaka cokerse KIRMIZI say
        return False, f"ISTISNA {type(hata).__name__}: {hata}"
    finally:
        shutil.rmtree(tepe, ignore_errors=True)


# ---------------------------------------------------------------------- mutasyon bataryasi
# (eski satir -> yeni satir, oldurmesi beklenen vaka, gerekce)
MUTANTLAR = [
    (
        '    istenen_ham = args.dosya or []',
        '    istenen_ham = args.dosya or ["."]',
        "V2", "F1 kaldirilir: bos liste 'her seyi commit et'e duser",
    ),
    (
        '    ekle = git(wt_yolu, "add", "--", *yollar)',
        '    ekle = git(wt_yolu, "add", "-A")',
        "V3B", "F2 yerine `git add -A`: worktree artigi commit'e sizar",
    ),
    (
        '    merge = git(kok, "merge", "--ff-only", dal)',
        '    merge = git(kok, "merge", "--no-ff", "-m", "otomatik merge", dal)',
        "V4", "F3'te ff yerine MERGE COMMIT uretilir",
    ),
    (
        # \n ANKRAJI ZORUNLU: ayni cagri TEKRAR kolunda 8 bosluk girintiyle de gecer ve
        # 4-bosluklu desen onun ALT DIZESIDIR -> ankrajsiz desen "2 kez gecti" der.
        '\n    itme = git(kok, "push", "origin", ana_dal)',
        '\n    itme = git(kok, "push", "--force", "origin", ana_dal)',
        "V5", "F4'e --force eklenir: uzaktaki commit ezilir",
    ),
    (
        'YASAK_ADLAR = ("urunler.json", ".urun-kaynaklari.json", ".r2-credentials.json", "CNAME")',
        'YASAK_ADLAR = ()',
        "V8", "F8 listesi bosaltilir: urunler.json commit'lenebilir olur",
    ),
    (
        # Q1 — stash yarisi kapanisi: argumansiz `apply` yigin tepesini (B'nin girdisini) alir.
        '    uygula = git(wt_yolu, "stash", "apply", durum.stash_sha)',
        '    uygula = git(wt_yolu, "stash", "apply")',
        "V11", "S1 kaldirilir: apply argumansiz, yigin tepesi (baska iscinin isi) uygulanir",
    ),
    (
        # Q2 — drop, SHA yerine sabit stash@{0}: komsunun girdisini duserir.
        '    i = stash_sha_indeksi(kok, durum.stash_sha)',
        '    i = 0',
        "V12", "S2 kaldirilir: drop stash@{0} ile komsunun isini duserir",
    ),
    (
        # Q3 — SHA yoksa yine de drop eder: koruma kosulu atlanir (STASH_KORUNDU YOK).
        '\n    if i < 0:\n        durum.hukum = "STASH_KORUNDU"',
        '\n    if False:\n        durum.hukum = "STASH_KORUNDU"',
        "V13", "S2 kaldirilir: SHA bulunamasa da drop yoluna girer (fail-closed acilir)",
    ),
]

# KONTROL mutanti: yalnizca YORUM degisir -> davranis DEGISMEZ -> hedef vaka YESIL kalmali.
# (Batarya disiplini: davranis degistirmeyen bir mutasyon KIRMIZI yakmamali.)
KONTROL_MUTANTLAR = [
    (
        '    # S3: es-zamanli isci sayaci + STASH_SHA/STASH_YIGIN ciktiya.',
        '    # S3: es-zamanli isci sayaci + STASH_SHA/STASH_YIGIN ciktiya (kontrol: yorum).',
        "V15", "KONTROL: yalniz yorum — davranis DEGISMEZ, vaka YESIL kalmali",
    ),
]


def mutasyon_bataryasi(kok_tmp: str) -> int:
    """0=basari (tum oldurucular olduruldu + kontrol yesil), 1=basarisiz, 2=kanonik bozuldu."""
    kaynak = oku(KANONIK_ARAC)
    once_sha = hashlib.sha256(kaynak.encode()).hexdigest()
    kirmizi = 0
    print("MUTANT TABLOSU (eski -> yeni | vaka | sonuc)")
    for i, (eski, yeni, vaka, gerekce) in enumerate(MUTANTLAR, start=1):
        if kaynak.count(eski) != 1:
            print(f"M{i} OLCULEMEDI: desen {kaynak.count(eski)} kez gecti -> {eski!r}")
            continue
        mutant = os.path.join(kok_tmp, f"mutant-{i}.py")
        yaz(mutant, kaynak.replace(eski, yeni, 1))
        gecti, not_ = vaka_kos(vaka, mutant, kok_tmp)
        durum = "KIRMIZI ✅" if not gecti else "HAYATTA ❌"
        if not gecti:
            kirmizi += 1
        print(f"M{i} [{vaka}] {durum}  {gerekce}")
        print(f"     eski: {eski.strip()}")
        print(f"     yeni: {yeni.strip()}")
        print(f"     vaka notu: {not_.splitlines()[0] if not_ else ''}")
    kontrol_yesil = 0
    print("KONTROL TABLOSU (eski -> yeni | vaka | sonuc)")
    for j, (eski, yeni, vaka, gerekce) in enumerate(KONTROL_MUTANTLAR, start=1):
        if kaynak.count(eski) != 1:
            print(f"K{j} OLCULEMEDI: desen {kaynak.count(eski)} kez gecti -> {eski!r}")
            continue
        mutant = os.path.join(kok_tmp, f"kontrol-{j}.py")
        yaz(mutant, kaynak.replace(eski, yeni, 1))
        gecti, not_ = vaka_kos(vaka, mutant, kok_tmp)
        durum = "YESIL ✅" if gecti else "KIRMIZI ❌"
        if gecti:
            kontrol_yesil += 1
        print(f"K{j} [{vaka}] {durum}  {gerekce}")
        print(f"     eski: {eski.strip()}")
        print(f"     yeni: {yeni.strip()}")
        print(f"     vaka notu: {not_.splitlines()[0] if not_ else ''}")
    sonra_sha = hashlib.sha256(oku(KANONIK_ARAC).encode()).hexdigest()
    print(f"KANONIK_SHA256_ONCE={once_sha}")
    print(f"KANONIK_SHA256_SONRA={sonra_sha}")
    if once_sha != sonra_sha:
        print("KIRMIZI: batarya kanonik kaynagi DEGISTIRDI")
        return 2
    print(f"MUTANT_KIRMIZI={kirmizi}/{len(MUTANTLAR)}")
    print(f"KONTROL_YESIL={kontrol_yesil}/{len(KONTROL_MUTANTLAR)}")
    if kirmizi < len(MUTANTLAR):
        print("KIRMIZI: hayatta kalan oldurucu mutant var")
        return 1
    if kontrol_yesil < len(KONTROL_MUTANTLAR):
        print("KIRMIZI: kontrol mutanti olduruldu (kanonik davranis bozuldu)")
        return 1
    return 0


def main() -> int:
    mutasyon = "--mutasyon" in sys.argv
    if not os.path.isfile(KANONIK_ARAC):
        print(f"KIRMIZI: arac yok: {KANONIK_ARAC}")
        return 1
    if kos(["git", "--version"]).returncode != 0:
        print("OLCULEMEDI: git yok")
        return 1

    kok_tmp = tempfile.mkdtemp(prefix="onarim-commit-test-")
    try:
        if mutasyon:
            rc = mutasyon_bataryasi(kok_tmp)
            if rc != 0:
                print("SONUC: KIRMIZI ❌")
                return 1
            print("SONUC: YESIL ✅ (tum mutantlar olduruldu, kontrol yesil)")
            return 0

        basarisiz = []
        for ad, _ in VAKALAR:
            anahtar = ad.split()[0]
            gecti, notu = vaka_kos(anahtar, KANONIK_ARAC, kok_tmp)
            print(f"{'✅' if gecti else '❌'} {ad}: {notu.splitlines()[0] if notu else ''}")
            if not gecti:
                basarisiz.append((ad, notu))
        print(f"VAKA_TOPLAM={len(VAKALAR)} KIRMIZI={len(basarisiz)}")
        for ad, notu in basarisiz:
            print(f"--- {ad} ---\n{notu}")
        if basarisiz:
            print("SONUC: KIRMIZI ❌")
            return 1
        print("SONUC: YESIL ✅")
        return 0
    finally:
        shutil.rmtree(kok_tmp, ignore_errors=True)
        print(f"TEMIZLIK gecici_kok={kok_tmp} kaldi_mi={os.path.exists(kok_tmp)}")


if __name__ == "__main__":
    raise SystemExit(main())
