#!/bin/sh
# K316 — ~/.claude/cron/ SURUM KONTROLU DISIDIR: duzenlemeden ONCE yedek al.
# Kullanim: sh tk-yedek.sh <UTC-damga>
D="$1"
C=/Users/okan/.claude/cron
for f in gozcu-mutasyon.py gozcu-test.py nobet-kapi.py nobet-kabul-test.py onarim-el-kitabi.md
do
  cp -p "$C/$f" "$C/$f.yedek-tabankirmizi-$D"
  echo "YEDEK $C/$f.yedek-tabankirmizi-$D"
done
