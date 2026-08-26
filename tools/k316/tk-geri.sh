#!/bin/sh
# K316 — yedekten GERI YUKLE (yamayi bastan uygulamak icin).
# Kullanim: sh tk-geri.sh <UTC-damga>
D="$1"
C=/Users/okan/.claude/cron
for f in gozcu-mutasyon.py gozcu-test.py nobet-kapi.py nobet-kabul-test.py onarim-el-kitabi.md
do
  cp -p "$C/$f.yedek-tabankirmizi-$D" "$C/$f"
  echo "GERI $C/$f"
done
