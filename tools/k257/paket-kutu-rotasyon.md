# SPEC — ortak posta kutusu rotasyonu (İŞÇİ TURU, mekanik)

> **KOD YAZMA. YORUM YAZMA.** İki komutu sırayla koş, HAM çıktıyı dosyaya dök.
> `git commit` / `git push` YOK. Başka hiçbir dosyaya DOKUNMA.
> 🔴 `✅ İŞ BİTTİ` jetonu YAZMA.

Sebep: pre-commit kapısı ortak kutuyu 332 satır / 30088 bayt ölçtü (tavan 300).
Araç LOSSLESS'tır: hiçbir şey silinmez, en eski bloklar arşive TAŞINIR.

Kanıt dizini: `/Users/okan/.claude/cron/kutu-rotasyon-kanit` (yoksa oluştur)

## ADIM 1 — KURU koşum (önce ölç)

```
python3 /Users/okan/dev/pruvo/tools/kutu-arsivle.py --kuru
```
→ `/Users/okan/.claude/cron/kutu-rotasyon-kanit/01-kuru.txt` (+ `RC=` satırı)

## ADIM 2 — gerçek rotasyon

```
python3 /Users/okan/dev/pruvo/tools/kutu-arsivle.py
```
→ `/Users/okan/.claude/cron/kutu-rotasyon-kanit/02-rotasyon.txt` (+ `RC=` satırı)

## ADIM 3 — sonraki ölçüm

```
wc -l -c /Users/okan/.claude/projects/-Users-okan-dev-pruvo/memory/mimar-posta-kutusu.md
```
→ `/Users/okan/.claude/cron/kutu-rotasyon-kanit/03-sonra.txt` (+ `RC=` satırı)

## SON MESAJIN — YALNIZCA şu blok

```
ADIM1_RC=<n> ADIM2_RC=<n> ADIM3_RC=<n>
SONRA_SATIR=<n> SONRA_BAYT=<n>
```
