#!/usr/bin/env python3
"""urunler-guard-hook.py — Claude Code PreToolUse(Bash) hook koprusudur.

stdin'den hook JSON'unu okur, tool_input.command icinde bir `git commit` ya da
`git push` var mi bakar; varsa urunler-guard.py'yi ilgili --tetik ile calistirir.
Guard working-tree urunler.json'i self-heal eder; boylece bozuk hicbir sey
commit'e/push'a giremez. `--no-verify` bunu ATLATAMAZ, cunku bu harness hook'u
git'in kendi hook'u DEGILDIR.

Cikis kodu DAIMA 0 — hook asla git komutunu bloklamaz (bozugu duzeltir, engellemez).
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, "tools", "urunler-guard.py")

# Bir kabuk segmentinde `git ... commit|push` tespiti (araya -C yol / bayrak girebilir).
_GIT_SUB = re.compile(r"\bgit\b[^\n]*?\b(commit|push)\b")


def _tetik(command):
    """Komut string'i commit mi push mu tetikliyor? Yoksa None."""
    tetik = None
    for seg in re.split(r"&&|\|\||;|\||\n", command):
        m = _GIT_SUB.search(seg)
        if not m:
            continue
        sub = m.group(1)
        if sub == "commit":
            return "commit"  # commit oncelikli
        if sub == "push":
            tetik = "push"
    return tetik


def main():
    try:
        data = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    command = (data.get("tool_input") or {}).get("command") or ""
    tetik = _tetik(command)
    if not tetik:
        return 0
    if not os.path.exists(GUARD):
        return 0  # guard henuz bu agacta yoksa sessizce gec
    try:
        subprocess.run([sys.executable or "python3", GUARD, "--tetik", tetik],
                       timeout=60)
    except Exception:
        pass  # hook asla git'i dusurmez
    return 0


if __name__ == "__main__":
    sys.exit(main())
