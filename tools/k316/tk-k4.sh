#!/bin/sh
# K316/K4 — capa bayatliginin FIKSTURDE uretilip ADIYLA raporlandigini olc.
DIZ="$1"
mkdir -p "$DIZ"
python3 /Users/okan/.claude/cron/gozcu-mutasyon.py --kendini-test > "$DIZ/k4.txt" 2>&1
echo "RC=$?" >> "$DIZ/k4.txt"
cat "$DIZ/k4.txt"
