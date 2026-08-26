#!/bin/sh
# K316 / KraL-TabanKirmizi-27Agu — DETERMINISTIK KOSUCU.
# Tek is: iki bataryayi kostur, HAM ciktiyi + rc'yi dosyaya yaz. Yorum YOK, ozet YOK.
# Kullanim: sh tk-kos.sh <cikti-dizini> <etiket>
DIZ="$1"
ETIKET="$2"
mkdir -p "$DIZ"

python3 /Users/okan/.claude/cron/gozcu-mutasyon.py > "$DIZ/v1-$ETIKET.txt" 2>&1
echo "RC=$?" >> "$DIZ/v1-$ETIKET.txt"

python3 /Users/okan/.claude/cron/nobet-kabul-test.py > "$DIZ/v2-$ETIKET.txt" 2>&1
echo "RC=$?" >> "$DIZ/v2-$ETIKET.txt"

echo "YAZILDI $DIZ/v1-$ETIKET.txt $DIZ/v2-$ETIKET.txt"
