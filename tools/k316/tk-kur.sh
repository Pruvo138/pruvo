#!/bin/sh
# K316 — yamayi uygula, sonra el kitabini URETICIDEN yaz.
# Kullanim: sh tk-kur.sh <cikti-dizini>
DIZ="$1"
mkdir -p "$DIZ"

python3 /Users/okan/dev/pruvo/.claude/worktrees/angry-sammet-c8311a/tools/k316/tk-yama.py > "$DIZ/yama.txt" 2>&1
echo "RC=$?" >> "$DIZ/yama.txt"

python3 /Users/okan/.claude/cron/nobet-kapi.py --el-kitabi-uret --kuru > "$DIZ/elkitabi-kuru.txt" 2>&1
echo "RC=$?" >> "$DIZ/elkitabi-kuru.txt"

python3 /Users/okan/.claude/cron/nobet-kapi.py --el-kitabi-uret > "$DIZ/elkitabi-yaz.txt" 2>&1
echo "RC=$?" >> "$DIZ/elkitabi-yaz.txt"

cat "$DIZ/yama.txt" "$DIZ/elkitabi-kuru.txt" "$DIZ/elkitabi-yaz.txt"
