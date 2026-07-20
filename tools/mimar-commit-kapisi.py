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
VERI_BASENAME = {"urunler.json", ".urun-kaynaklari.json"}


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
    """Dosya yolu KAYNAK kodu mu? (.py/.js/.mjs/.ts/.html/.css/.sql; veri HARIC)"""
    basename = _basename(yol)
    if not basename or basename in VERI_BASENAME:
        return False
    _, uzanti = os.path.splitext(basename)
    return uzanti in KAYNAK_UZANTI


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


def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--stdin", action="store_true", help="staged dosyalari stdin'den oku")
    parser.add_argument("--toplevel", help="repo toplevel yolunu elle ver")
    args = parser.parse_args()

    kok = toplevel(args.toplevel)
    if kok != ANA_REPO:
        return 0

    staged = staged_dosyalar(args.stdin)
    kaynaklar = [yol for yol in staged if kaynak_mi(yol)]

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
