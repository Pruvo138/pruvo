#!/bin/sh
# K316 — GECICI olcum ciktilarini sil (Okan kurali: ureten temizler).
K=/Users/okan/dev/pruvo/.claude/worktrees/angry-sammet-c8311a/tools/k316
echo "ONCE:"
du -sk "$K"
rm -rf "$K/cikti"
rm -rf "$K/__pycache__"
rm -rf /Users/okan/.claude/cron/__pycache__
echo "SONRA:"
du -sk "$K"
ls -1 "$K"
