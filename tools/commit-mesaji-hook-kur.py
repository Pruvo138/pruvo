#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`commit-msg` kancasina COMMIT MESAJI NOBETI BLOGUNU kurar (idempotent).

🖥️ YENI MAKINEDE / GOCTEN SONRA TEK YAPILACAK SEY:
        python3 tools/commit-mesaji-hook-kur.py
    Kancalar `.git/hooks` altinda yasar ve GIT'E GIRMEZ -> her makinede yeniden kurulur.
    Kurulu mu: `python3 tools/commit-mesaji-hook-kur.py --dogrula`.
    (Drive yedegi `tools/yedekle.py` ile `.git/hooks` klasorunu oldugu gibi tasir;
     `tools/yedek-hook-kur.py --geri-yukle` bu kancayi da geri koyar.)

NE YAPAR: `<git-common-dir>/hooks/commit-msg` icine isaretli bir blok ekler. Blok her
commit'te `tools/commit-mesaji-kapisi.py --commit-msg "$1"` cagirir; kapi kirmizi
yanarsa COMMIT DURUR.

🔴 NEDEN `commit-msg` (pre-commit ya da CI degil) — eksen olcumuyle secildi:
  * pre-commit kancasi mesaj dosyasini ALMAZ (git ona mesaji vermez) -> tarayacak metin
    YOKTUR. Mesaj ekseninde tek dogru kanca budur.
  * CI (deploy.yml) yalniz `push: branches: [main]` ile ve PUSH'TAN SONRA kosar. O anda
    commit ZATEN public remote'tadir; commit MESAJI nesnenin bir parcasidir ve
    DEGISTIRILEMEZ — tek onarim tarihce yeniden yazimi + force-push'tur. Yani CI'nin
    tamir degeri SIFIRDIR; bu eksenin butun degeri ONLEMEDIR.
  * Olculen olayin 7 vurusunun 5'i DAL push'unda olusmustu; deploy.yml o dallari HIC
    gormez. CI kolu yine de vardir ama ikinci hattir (gorunurluk), birinci hat DEGIL.

🔴 FAIL-CLOSED (bilincli): betik bulunamazsa/patlarsa COMMIT DURUR. Blokta `exit 1`
   VARDIR. Mesru tikanmada cikis yolu git'in kendi `--no-verify` bayragidir (gurultulu),
   kapiyi sessizce gevsetmek DEGIL.

Kullanim:
    python3 tools/commit-mesaji-hook-kur.py            # kur / guncelle
    python3 tools/commit-mesaji-hook-kur.py --kuru     # ne yapacagini goster, YAZMA
    python3 tools/commit-mesaji-hook-kur.py --dogrula  # kurulu mu (cikis 0/1)
    python3 tools/commit-mesaji-hook-kur.py --kaldir   # yalniz bu blogu cikar
    python3 tools/commit-mesaji-hook-kur.py --repo YOL # baska bir depoya kur (test)
"""
import os
import shutil
import stat
import subprocess
import sys
from git_ortami import git_ortami

BAS = ("# >>> PRUVO COMMIT MESAJI NOBETI BLOGU "
       "(tools/commit-mesaji-hook-kur.py uretir — ELLE DUZENLEME) >>>")
SON = "# <<< PRUVO COMMIT MESAJI NOBETI BLOGU <<<"

BLOK = BAS + """
# FAIL-CLOSED: commit mesajinda tedarikci/satici kimligi varsa COMMIT DURUR.
# Gerekce + kanca secimi: tools/commit-mesaji-hook-kur.py basligi.
pruvo_cm_kok=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$pruvo_cm_kok" ] || [ ! -f "$pruvo_cm_kok/tools/commit-mesaji-kapisi.py" ]; then
  echo "!! COMMIT MESAJI NOBETI KOSULAMADI (tools/commit-mesaji-kapisi.py yok) — COMMIT DURDURULDU."
  echo "!! Sizinti kapisi fail-closed'dir. Kasten atlamak icin: git commit --no-verify"
  exit 1
fi
if ! python3 "$pruvo_cm_kok/tools/commit-mesaji-kapisi.py" --commit-msg "$1"; then
  echo "!! COMMIT DURDURULDU — commit mesajinda tedarikci/satici kimligi."
  exit 1
fi
""" + SON


def hook_yolu(repo):
    """Ortak git dizinindeki hooks/commit-msg (worktree'de de ANA depoyu gosterir)."""
    p = subprocess.run(["git", "-C", repo, "rev-parse", "--path-format=absolute",
                        "--git-common-dir"], capture_output=True, text=True,
                       env=git_ortami())
    if p.returncode != 0 or not p.stdout.strip():
        return None
    return os.path.join(p.stdout.strip(), "hooks", "commit-msg")


def yeni_icerik(mevcut, kaldir=False):
    """Blogu ekler/gunceller/cikarir. (yeni_metin, eylem) doner."""
    if mevcut is None:
        if kaldir:
            return None, "hook yok — yapacak bir sey yok"
        return "#!/bin/sh\n" + BLOK + "\n", "YENI hook olusturuldu"
    if BAS in mevcut and SON in mevcut:
        bas = mevcut.index(BAS)
        son = mevcut.index(SON) + len(SON)
        yeni = mevcut[:bas] + ("" if kaldir else BLOK) + mevcut[son:]
        if kaldir:
            yeni = yeni.replace("\n\n\n", "\n\n")
        return yeni, ("blok CIKARILDI" if kaldir else "mevcut blok GUNCELLENDI")
    if kaldir:
        return mevcut, "blok zaten yok"
    # Blok YOK -> shebang'in hemen ardina (baska bir blogun `exit 0`'indan ONCE).
    satirlar = mevcut.splitlines(True)
    yer = 1 if satirlar and satirlar[0].startswith("#!") else 0
    return ("".join(satirlar[:yer]) + BLOK + "\n" + "".join(satirlar[yer:]),
            "blok EKLENDI (basa)")


def kurulu_mu(yol):
    if not yol or not os.path.isfile(yol):
        return False
    try:
        with open(yol, encoding="utf-8", errors="replace") as f:
            metin = f.read()
    except OSError:
        return False
    return BAS in metin and "--commit-msg" in metin


def kur(repo, kuru=False, kaldir=False, sessiz=False):
    """(rc, yol). Yazar/gunceller/cikarir."""
    yol = hook_yolu(repo)
    if not yol:
        if not sessiz:
            print("HATA: git deposu bulunamadi: " + repo, file=sys.stderr)
        return 1, None
    mevcut = None
    if os.path.isfile(yol):
        with open(yol, encoding="utf-8", errors="replace") as f:
            mevcut = f.read()
    yeni, eylem = yeni_icerik(mevcut, kaldir=kaldir)
    if not sessiz:
        print("hook: " + yol)
        print("eylem: " + eylem)
    if yeni is None or yeni == mevcut:
        if not sessiz:
            print("degisiklik YOK (idempotent).")
        return 0, yol
    if kuru:
        if not sessiz:
            print("KURU KOSUM — yazilmadi.")
        return 0, yol
    kopya = yol + ".pruvo-mesaj-oncesi"
    if mevcut is not None and not os.path.exists(kopya):
        shutil.copy2(yol, kopya)
        if not sessiz:
            print("guvenlik kopyasi: " + kopya)
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(yeni)
    os.chmod(yol, os.stat(yol).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    if not sessiz:
        print("yazildi + calistirilabilir yapildi.")
    return 0, yol


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "-h" in argv or "--help" in argv:
        print(__doc__.strip())
        return 0
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if "--repo" in argv:
        i = argv.index("--repo")
        if i + 1 >= len(argv):
            print("HATA: --repo bir yol ister", file=sys.stderr)
            return 2
        repo = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    bilinmeyen = [a for a in argv if a not in ("--kuru", "--kaldir", "--dogrula")]
    if bilinmeyen:
        print("HATA: bilinmeyen arguman: " + ", ".join(bilinmeyen), file=sys.stderr)
        return 2
    if "--dogrula" in argv:
        yol = hook_yolu(repo)
        var = kurulu_mu(yol)
        print("hook: %s\ncommit mesaji nobeti blogu: %s"
              % (yol, "KURULU" if var else "YOK"))
        return 0 if var else 1
    rc, _ = kur(repo, kuru="--kuru" in argv, kaldir="--kaldir" in argv)
    return rc


if __name__ == "__main__":
    sys.exit(main())
