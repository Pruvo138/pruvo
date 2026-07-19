#!/usr/bin/env python3
"""Codex PreToolUse: KraL ana oturumunda kod/veri yazimini ve ic Codex cagrilarini engeller."""
import json
import os
import re
import sys

ROOT = "/Users/okan/dev/pruvo"
KAYNAK_UZANTILARI = {
    ".py", ".js", ".mjs", ".ts", ".html", ".css", ".sql", ".json", ".toml",
    ".yaml", ".yml", ".sh", ".scad",
}
KRITIK_ADLAR = {"urunler.json", ".urun-kaynaklari.json"}


def yollar(data):
    inp = data.get("tool_input") or {}
    out = []
    fp = inp.get("file_path") or inp.get("path")
    if fp:
        out.append(fp)
    patch = inp.get("patch") or inp.get("input") or ""
    for m in re.finditer(r"^\*\*\* (?:Add|Update|Delete) File:\s*(.+?)\s*$", patch, re.M):
        out.append(m.group(1))
    return out


def kaynak_mi(yol):
    yol = os.path.normpath(yol)
    if not os.path.isabs(yol):
        yol = os.path.normpath(os.path.join(ROOT, yol))
    if not yol.startswith(ROOT + os.sep):
        return False
    if yol.endswith(".md"):
        return False
    if yol.startswith("/private/tmp/"):
        return False
    ad = os.path.basename(yol)
    return ad in KRITIK_ADLAR or os.path.splitext(ad)[1].lower() in KAYNAK_UZANTILARI


def reddet(neden):
    print(json.dumps({
        "systemMessage": neden,
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": neden,
        },
    }, ensure_ascii=False))


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if os.environ.get("PRUVO_CODEX_ROLE", "architect") == "worker":
        return 0
    tool = data.get("tool_name") or data.get("tool") or ""
    inp = data.get("tool_input") or {}
    if tool in {"Bash", "exec_command"}:
        komut = inp.get("command") or inp.get("cmd") or ""
        if "thing-codex.py" in komut or re.search(r"(?:^|\s)codex\s+exec(?:\s|$)", komut):
            reddet("KraL kredi kilidi: ana oturum ic Codex/model cagrisi yapamaz; temiz baglamli alt ajana delege et.")
        return 0
    bloklanan = [yol for yol in yollar(data) if kaynak_mi(yol)]
    if bloklanan:
        reddet("KraL mimar kilidi: ana oturum kod/veri yazamaz. Muhendis veya maraba alt ajanina delege et: "
                + ", ".join(bloklanan[:4]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
