#!/bin/sh
# K316 — son temizlik + disk olcumu.
K=/Users/okan/dev/pruvo/.claude/worktrees/angry-sammet-c8311a/tools/k316
rm -f "$K/commit-mesaji.txt"
rm -rf "$K/__pycache__"
rm -rf /Users/okan/.claude/cron/__pycache__
echo "SON DISK:"
du -sk "$K"
echo "KUTU SATIR:"
wc -l /Users/okan/.claude/projects/-Users-okan-dev-pruvo/memory/mimar-posta-kutusu.md
