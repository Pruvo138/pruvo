#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mimar-commit-kapisi.py — git commit backstop for source/data changes.

Kural:
- Ana repo'da kaynak (.py/.js/.mjs/.ts/.html/.css/.sql) VEYA veri (urunler.json /
  .urun-kaynaklari.json) staged ise commit'i blokla; .md vb. serbest.
- Worktree'de her sey serbest (mühendis alani).

BILINEN-BYPASS (sessiz degil, DAR): PRUVO_MIMAR_ONAY=worker YALNIZCA veri düzlemini
(urunler.json / .urun-kaynaklari.json) açar — ürün-ekleme partileri ana checkout'ta bu
dosyalari commit'ler (MaCiT'in sahasi, kirilmamali). Env=worker staged'de HERHANGI bir
KAYNAK dosyasi varken commit'i AÇMAZ: kaynak isi worktree'de commit'lenir. Bu daraltma,
env bypass'inin geçmiste mimarin kaynak-koda kaçis kapisina (tools/*.py'nin ana
checkout'a bu yolla girmesi) dönüsmesini kapatir; bilinen tek gevseme belgeli ve dar.

BYPASS MUHASEBESI (kapi bir DISIPLIN cihazidir, hapishane degil — hepsi KAYITLI):
  1. PRUVO_MIMAR_ONAY=worker  → yalniz VERI duzlemi; stderr + log satiri "allow-escape".
  2. Sequencer suruyor (MERGE_HEAD/CHERRY_PICK_HEAD/REVERT_HEAD/rebase-*) → commit
     ENGELLENMEZ; stderr + log satiri "allow-sequencer". Tek 'Write .git/MERGE_HEAD'
     ile SAHTE sequencer durumu kurulabilir — bu yol artik SESSIZ DEGIL.
  3. git commit --no-verify → kapi hic kosmaz (git'in kendi kapisi; ayni zincirdeki
     urunler-guard'i da oldurur, bu yuzden hata metni bu yolu ONERMEZ).
  4. 'git worktree add <yol>' → mimar kendine tam muaf bir bolge acar (worktree
     toplevel'i bu kapinin kapsami disidir). BILEREK acik: kapi disiplin cihazi.
  Haftalik olcum:
     grep -c allow- /Users/okan/dev/pruvo/.git/pruvo-kapi-log.jsonl

Test kolayligi icin:
- --stdin: staged dosya listesini stdin'den oku.
- --toplevel YOL: repo toplevel'ini elle ver.
- --gitdir YOL: git dizinini elle ver (sequencer testi + log hedefi).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

ANA_REPO = "/Users/okan/dev/pruvo"
KAYNAK_UZANTI = {".py", ".js", ".mjs", ".ts", ".html", ".css", ".sql"}
VERI_BASENAME = {"urunler.json", ".urun-kaynaklari.json"}

# Bir merge/cherry-pick/revert/rebase surerken commit ENGELLENMEZ: cakismayi elle
# kapatmak mimarin kapisidir (yanlis pozitifin bedeli bu riskten pahalidir).
SEQUENCER_DOSYA = ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD")
SEQUENCER_DIZIN = ("rebase-merge", "rebase-apply")


def _basename(yol: str) -> str:
    if not yol:
        return ""
    temiz = yol.strip().replace("\\", "/")
    if not temiz:
        return ""
    return os.path.basename(temiz)


def veri_mi(yol: str) -> bool:
    """Dosya yolu VERI düzlemi mi? (urunler.json / .urun-kaynaklari.json)"""
    return _basename(yol) in VERI_BASENAME


def kaynak_mi(yol: str) -> bool:
    """Dosya yolu KAYNAK kodu mu? (.py/.js/.mjs/.ts/.html/.css/.sql; veri HARIC)

    Uzanti karsilastirmasi KUCUK HARFE indirilir — 'tools/x.PY' olculmus bir kacakti
    (macOS dosya sistemi harf duyarsiz, git yolu oldugu gibi tasir)."""
    basename = _basename(yol)
    if not basename or basename in VERI_BASENAME:
        return False
    _, uzanti = os.path.splitext(basename)
    return uzanti.lower() in KAYNAK_UZANTI


def korunan_mi(yol: str) -> bool:
    """Dosya kaynak VEYA veri mi? (env yoksa ikisi de bloklanir)"""
    return kaynak_mi(yol) or veri_mi(yol)


def _git_cikti(komut: list[str]) -> str:
    sonuc = subprocess.run(
        komut,
        capture_output=True,
        text=True,
        check=False,
    )
    if sonuc.returncode != 0:
        return ""
    return sonuc.stdout


def staged_dosyalar(stdin_modu: bool) -> list[str]:
    if stdin_modu:
        return [satir.strip() for satir in sys.stdin if satir.strip()]
    cikti = _git_cikti(["git", "diff", "--cached", "--name-only"])
    return [satir.strip() for satir in cikti.splitlines() if satir.strip()]


def toplevel(args_toplevel: str | None) -> str:
    if args_toplevel:
        return os.path.normpath(args_toplevel)
    cikti = _git_cikti(["git", "rev-parse", "--show-toplevel"]).strip()
    return os.path.normpath(cikti) if cikti else ""


def git_dizini(kok: str, args_gitdir: str | None) -> str:
    if args_gitdir:
        return os.path.normpath(args_gitdir)
    cikti = _git_cikti(["git", "-C", kok, "rev-parse", "--git-dir"]).strip()
    if cikti:
        if not os.path.isabs(cikti):
            cikti = os.path.join(kok, cikti)
        return os.path.normpath(cikti)
    return os.path.join(kok, ".git")


def sequencer_suruyor(gitdir: str) -> bool:
    """merge / cherry-pick / revert / rebase devam ediyor mu?"""
    try:
        for ad in SEQUENCER_DOSYA:
            if os.path.exists(os.path.join(gitdir, ad)):
                return True
        for ad in SEQUENCER_DIZIN:
            if os.path.isdir(os.path.join(gitdir, ad)):
                return True
    except Exception:
        return False
    return False


def bypass_kaydet(gitdir: str, kok: str, karar: str, mesaj: str, staged_sayisi: int) -> None:
    """Her BYPASS yolu GURULTULU + LOGLU olur; karar DEGISMEZ (kapi bir kilit degil,
    bir hatirlaticidir). Log yazilamazsa yine de stderr satiri kalir.

    Muhasebe: grep -c allow- <gitdir>/pruvo-kapi-log.jsonl
    'allow-escape'    = PRUVO_MIMAR_ONAY=worker (veri duzlemi)
    'allow-sequencer' = merge/cherry-pick/revert/rebase suruyor (SAHTE de kurulabilir)"""
    try:
        sys.stderr.write(mesaj + "\n")
    except Exception:
        pass
    try:
        satir = json.dumps({
            "t": int(time.time()),
            "karar": karar,
            "kok": kok,
            "staged": staged_sayisi,
        }, ensure_ascii=False)
        with open(os.path.join(gitdir, "pruvo-kapi-log.jsonl"), "a", encoding="utf-8") as f:
            f.write(satir + "\n")
    except Exception:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--stdin", action="store_true", help="staged dosyalari stdin'den oku")
    parser.add_argument("--toplevel", help="repo toplevel yolunu elle ver")
    parser.add_argument("--gitdir", help="git dizinini elle ver (test icin)")
    args = parser.parse_args()

    kok = toplevel(args.toplevel)
    if kok != ANA_REPO:
        return 0

    gitdir = git_dizini(kok, args.gitdir)
    staged = staged_dosyalar(args.stdin)
    kaynaklar = [yol for yol in staged if kaynak_mi(yol)]

    # Merge/cherry-pick/revert/rebase cakismasini elle kapatan commit ENGELLENMEZ.
    # KAYDA GECEN BYPASS: tek 'Write .git/MERGE_HEAD' ile sahte sequencer durumu
    # kurulabilir → bu yol SESSIZ OLAMAZ (stderr + jsonl).
    if sequencer_suruyor(gitdir):
        bypass_kaydet(
            gitdir, kok, "allow-sequencer",
            "SEQUENCER ISTISNASI (merge/cherry-pick/revert/rebase suruyor) — commit "
            "kapisi atlandi. Bu yol loglanir: grep -c allow-sequencer " +
            os.path.join(gitdir, "pruvo-kapi-log.jsonl"),
            len(staged),
        )
        return 0

    if os.environ.get("PRUVO_MIMAR_ONAY") == "worker":
        # DAR bypass: worker onayi YALNIZ veri düzlemini açar. Kaynak varsa reddet.
        if kaynaklar:
            sys.stderr.write(
                "COMMIT ENGELLENDI: PRUVO_MIMAR_ONAY=worker YALNIZ urunler.json / "
                ".urun-kaynaklari.json commit'ini açar; KAYNAK kodunu AÇMAZ. "
                "Kaynak isi worktree'de commit'lenir, ana checkout'a girmez.\n"
            )
            for yol in kaynaklar:
                sys.stderr.write(f"{yol}\n")
            return 1
        bypass_kaydet(
            gitdir, kok, "allow-escape",
            "ESCAPE HATCH KULLANILDI (PRUVO_MIMAR_ONAY=worker, veri duzlemi) — commit "
            "kapisi atlandi. Bu yol loglanir: grep -c allow-escape " +
            os.path.join(gitdir, "pruvo-kapi-log.jsonl"),
            len(staged),
        )
        return 0

    bloklanan = [yol for yol in staged if korunan_mi(yol)]
    if bloklanan:
        sys.stderr.write(
            "COMMIT ENGELLENDI (mimar kod-kilidi / Layer 2): kaynak/veri degisikligi worker isidir. "
            "PRUVO_MIMAR_ONAY=worker YALNIZ urunler.json / .urun-kaynaklari.json commit'ini açar "
            "(kaynak kodu worktree'de commit'lenir).\n"
        )
        for yol in bloklanan:
            sys.stderr.write(f"{yol}\n")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
