#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mimar-commit-kapisi.py — git commit backstop for source/data changes.

Kural:
- Ana repo'da kaynak/veri staged ise ve PRUVO_MIMAR_ONAY != "worker" ise commit'i blokla.
- Worktree'de veya worker onayinda serbest gec.

Test kolayligi icin:
- --stdin: staged dosya listesini stdin'den oku.
- --toplevel YOL: repo toplevel'ini elle ver.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

ANA_REPO = "/Users/okan/dev/pruvo"
KAYNAK_UZANTI = {".py", ".js", ".mjs", ".ts", ".html", ".css", ".sql"}
KAYNAK_BASENAME = {"urunler.json", ".urun-kaynaklari.json"}


def kaynak_mi(yol: str) -> bool:
    """Dosya yolu kaynak/veri mi?"""
    if not yol:
        return False
    temiz = yol.strip().replace("\\", "/")
    if not temiz:
        return False
    basename = os.path.basename(temiz)
    if basename in KAYNAK_BASENAME:
        return True
    _, uzanti = os.path.splitext(basename)
    return uzanti in KAYNAK_UZANTI


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


def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--stdin", action="store_true", help="staged dosyalari stdin'den oku")
    parser.add_argument("--toplevel", help="repo toplevel yolunu elle ver")
    args = parser.parse_args()

    kok = toplevel(args.toplevel)
    if kok != ANA_REPO:
        return 0

    if os.environ.get("PRUVO_MIMAR_ONAY") == "worker":
        return 0

    staged = staged_dosyalar(args.stdin)
    bloklanan = [yol for yol in staged if kaynak_mi(yol)]
    if bloklanan:
        sys.stderr.write(
            "COMMIT ENGELLENDI (mimar kod-kilidi / Layer 2): kaynak/veri degisikligi worker isidir. "
            "Delege edilmis is ise: PRUVO_MIMAR_ONAY=worker git commit ...\n"
        )
        for yol in bloklanan:
            sys.stderr.write(f"{yol}\n")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
