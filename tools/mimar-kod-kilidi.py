#!/usr/bin/env python3
"""PreToolUse kilidi: mimar oturumu kaynak/veri dosyalarını Edit/Write ile degistiremez."""
import json
import os
import sys

try:
    girdi = json.load(sys.stdin)
except Exception:
    sys.exit(0)

fp = (girdi.get("tool_input") or {}).get("file_path") or ""
if not fp:
    sys.exit(0)

fp = os.path.normpath(fp)

if fp.endswith(".md"):
    sys.exit(0)

if fp.startswith("/private/tmp/") and "/scratchpad/" in fp:
    sys.exit(0)

# Worktree worker'lari (Agent isolation:worktree) mesru muhendistir — muaf.
# normpath sayesinde ../ ile worktree disina cikan yol bu kontrolu gecemez (guvenli).
if "/.claude/worktrees/" in fp:
    sys.exit(0)

repo_prefix = "/Users/okan/dev/pruvo/"
if not fp.startswith(repo_prefix):
    sys.exit(0)

basename = os.path.basename(fp)
blocked = (
    fp.endswith(".py")
    or fp.endswith(".js")
    or fp.endswith(".mjs")
    or fp.endswith(".ts")
    or fp.endswith(".html")
    or fp.endswith(".css")
    or fp.endswith(".sql")
    or basename == "urunler.json"
    or basename == ".urun-kaynaklari.json"
    or fp.endswith("/.claude/settings.json")
    or fp.endswith("/.claude/settings.local.json")
    or basename == "mimar-kod-kilidi.py"
)

if blocked:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "MİMAR KOD-KİLİDİ (Okan 18 Tem): kaynak/veri dosyasına Edit/Write "
                "YASAK — işi Codex'e ya da worktree worker'a DELEGE et, spec'i .md "
                "dosyasına yaz. Kilidin kendisini de değiştiremezsin. İzinli: *.md, "
                "scratchpad, koordinasyon dosyaları."
            ),
        }
    }, ensure_ascii=False))
sys.exit(0)
