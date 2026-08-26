#!/bin/sh
# K316 — disk olcumu (Okan kurali: oncesi-sonrasi basilir).
du -sk "$1"
du -sk /Users/okan/.claude/cron
ls -1 /Users/okan/.claude/cron/*.yedek-tabankirmizi-* | wc -l
