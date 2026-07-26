#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pre-push hook'una YEDEK BLOGUNU kurar (idempotent, tekrar-kosulabilir).

🖥️ YENI MAKINEDE / GOCTEN SONRA TEK YAPILACAK SEY:
        python3 tools/yedek-hook-kur.py
    Hook'lar `.git/hooks` altinda yasar ve GIT'E GIRMEZ -> her makinede yeniden kurulur.
    Elle hatirlanacak bir adim BIRAKILMASIN diye bu betik var; iki kez kosmak zararsiz.

NE YAPAR: `.git/hooks/pre-push` icine isaretli bir blok ekler. Blok her push'ta
`tools/yedekle.py --gerekliyse` cagirir (son damgadan beri degisiklik yoksa hicbir sey
kopyalanmaz -> push yavaslamaz).

NEDEN VAR (26 Tem olcumu): yedekle.py DOGRU calisiyordu ama ELLE cagriliyordu; 5 gun
kosulmadi ve mutasyon-kanitli skill dosyalari yedekte bayat kaldi. Otomasyon tek basina
yetmez (sessizce durabilir) -> gorunurluk `tools/durum.py` bolum 7'de, otomasyon burada.

🔴 FAIL-OPEN (pazarliksiz): yedek patlasa, Drive bagli olmasa, python3 bulunmasa bile
   PUSH DEVAM EDER. Blok icinde `exit` YOKTUR ve cagri `|| true` ile susturulur.
   Push'u durduran bir yedek kabul edilemez — D1 senkron blogunun emsali de budur.

GUVENLI KURULUM:
  * Mevcut pre-push (D1 senkronu) KORUNUR — blok isaretler arasina yazilir, dosyanin
    geri kalanina dokunulmaz. Ilk degisiklikte yanina `.pruvo-yedek-oncesi` kopyasi alinir.
  * Blok SEBEKE/D1 blogundan ONCE yerlestirilir: D1 blogu urunler.json degismediyse
    `exit 0` ile CIKIYOR -> sona eklenen bir blok cogu push'ta HIC CALISMAZDI.
  * Tekrar kosum blogu GUNCELLER, ikinci kopya YIGMAZ.

Kullanim:
    python3 tools/yedek-hook-kur.py           # kur / guncelle
    python3 tools/yedek-hook-kur.py --kuru    # ne yapacagini goster, YAZMA
    python3 tools/yedek-hook-kur.py --kaldir  # yalniz yedek blogunu cikar
"""
import os
import shutil
import stat
import subprocess
import sys

BAS = "# >>> PRUVO YEDEK BLOGU (tools/yedek-hook-kur.py uretir — ELLE DUZENLEME) >>>"
SON = "# <<< PRUVO YEDEK BLOGU <<<"

BLOK = BAS + """
# FAIL-OPEN: yedek patlasa/Drive olmasa bile push ASLA durmaz (blokta 'exit' YOK).
# UCUZ: --gerekliyse son damgadan beri degisiklik yoksa tek dosya bile kopyalamaz.
# Gorunurluk: python3 tools/durum.py  -> "7) YEDEK TAZELIGI"
pruvo_kok=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -n "$pruvo_kok" ] && [ -f "$pruvo_kok/tools/yedekle.py" ]; then
  if ! python3 "$pruvo_kok/tools/yedekle.py" --gerekliyse >/dev/null 2>&1; then
    echo "!! YEDEK alinamadi (push DEVAM ediyor) — kontrol: python3 tools/durum.py"
  fi
fi
""" + SON


def hook_yolu(repo):
    """Ortak git dizinindeki hooks/pre-push (worktree'de de ANA depoyu gosterir)."""
    p = subprocess.run(["git", "-C", repo, "rev-parse", "--path-format=absolute",
                        "--git-common-dir"], capture_output=True, text=True)
    if p.returncode != 0 or not p.stdout.strip():
        return None
    return os.path.join(p.stdout.strip(), "hooks", "pre-push")


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

    # Blok YOK -> shebang'in hemen ardina koy (D1 blogunun 'exit 0'larindan ONCE).
    satirlar = mevcut.splitlines(True)
    yer = 1 if satirlar and satirlar[0].startswith("#!") else 0
    return "".join(satirlar[:yer]) + BLOK + "\n" + "".join(satirlar[yer:]), "blok EKLENDI (basa)"


def main():
    kuru = "--kuru" in sys.argv
    kaldir = "--kaldir" in sys.argv
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__.strip())
        return 0
    bilinmeyen = [a for a in sys.argv[1:] if a not in ("--kuru", "--kaldir")]
    if bilinmeyen:
        print("HATA: bilinmeyen arguman: " + ", ".join(bilinmeyen), file=sys.stderr)
        return 2

    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    yol = hook_yolu(repo)
    if not yol:
        print("HATA: git deposu bulunamadi: " + repo, file=sys.stderr)
        return 1

    mevcut = None
    if os.path.isfile(yol):
        with open(yol, encoding="utf-8", errors="replace") as f:
            mevcut = f.read()

    yeni, eylem = yeni_icerik(mevcut, kaldir=kaldir)
    print("hook: " + yol)
    print("eylem: " + eylem)
    if yeni is None or yeni == mevcut:
        print("degisiklik YOK (idempotent).")
        return 0
    if kuru:
        print("KURU KOSUM — yazilmadi.")
        return 0

    # Ilk degisiklikte tek seferlik guvenlik kopyasi (D1 blogu kaybolmasin).
    kopya = yol + ".pruvo-yedek-oncesi"
    if mevcut is not None and not os.path.exists(kopya):
        shutil.copy2(yol, kopya)
        print("guvenlik kopyasi: " + kopya)

    with open(yol, "w", encoding="utf-8") as f:
        f.write(yeni)
    os.chmod(yol, os.stat(yol).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print("yazildi + calistirilabilir yapildi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
