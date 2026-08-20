# SPEC — K257 temizliği (İŞÇİ TURU, mekanik) — disk kuralı: ÜRETEN TEMİZLER

> **KOD YAZMA. YORUM YAZMA.** Komutları SIRAYLA koş, HAM çıktıyı dosyaya dök.
> `git commit` / `git push` YOK. 🔴 `✅ İŞ BİTTİ` jetonu YAZMA.
>
> 🔴 **SİLİNMEYECEKLER (dokunma):** `*.yedek-k257-20260820T163510Z` ile biten
> ÜÇ dosya — bunlar canlı yamanın `--geri-al` yoludur. `nobet_merdiven.py`,
> `nobet-merdiven-test.py`, `nobet-kapi.py`, `testler.py`,
> `nobet-kapi-mutasyon.py` de KALIR.

Kanıt dizini: `/Users/okan/.claude/cron/k257-temizlik` (yoksa oluştur)

## ADIM 1 — ÖNCE ölçümü

```
du -sk /Users/okan/.claude/cron
```
→ `/Users/okan/.claude/cron/k257-temizlik/01-du-once.txt` (+ `RC=` satırı)

## ADIM 2 — kanıt dizinlerini sil (dördü)

```
rm -rf /Users/okan/.claude/cron/k257-kanit /Users/okan/.claude/cron/k257-kanit2 /Users/okan/.claude/cron/k257-kanit3 /Users/okan/.claude/cron/kutu-rotasyon-kanit
```
→ `/Users/okan/.claude/cron/k257-temizlik/02-kanit-sil.txt` (+ `RC=` satırı)

## ADIM 3 — ARADAN KALAN (bayat) yedekleri sil — SON damga KALIR

```
rm -f /Users/okan/.claude/cron/nobet-kapi.py.yedek-k257-20260820T162216Z /Users/okan/.claude/cron/nobet-kapi.py.yedek-k257-20260820T162954Z /Users/okan/.claude/cron/testler.py.yedek-k257-20260820T162216Z /Users/okan/.claude/cron/testler.py.yedek-k257-20260820T162954Z
```
→ `/Users/okan/.claude/cron/k257-temizlik/03-bayat-yedek-sil.txt` (+ `RC=` satırı)

## ADIM 4 — geri-al yolunun HÂLÂ SAĞLAM olduğunu kanıtla

```
ls -la /Users/okan/.claude/cron/nobet-kapi.py.yedek-k257-20260820T163510Z /Users/okan/.claude/cron/testler.py.yedek-k257-20260820T163510Z /Users/okan/.claude/cron/nobet-kapi-mutasyon.py.yedek-k257-20260820T163510Z
```
→ `/Users/okan/.claude/cron/k257-temizlik/04-geri-al-yolu.txt` (+ `RC=` satırı)

## ADIM 5 — artık taraması (mutant/yazım artığı KALMAMALI)

```
ls -a /Users/okan/.claude/cron
```
→ `/Users/okan/.claude/cron/k257-temizlik/05-artik.txt` (+ `RC=` satırı)

## ADIM 6 — kabul bataryası HÂLÂ YEŞİL mi (temizlik bir şey kırmadı mı)

```
python3 /Users/okan/.claude/cron/nobet-merdiven-test.py
```
→ `/Users/okan/.claude/cron/k257-temizlik/06-kabul.txt` (+ `RC=` satırı)

## ADIM 7 — SONRA ölçümü

```
du -sk /Users/okan/.claude/cron
```
→ `/Users/okan/.claude/cron/k257-temizlik/07-du-sonra.txt` (+ `RC=` satırı)

## SON MESAJIN — YALNIZCA şu blok

```
ADIM1_RC=<n> ADIM2_RC=<n> ADIM3_RC=<n> ADIM4_RC=<n> ADIM5_RC=<n> ADIM6_RC=<n> ADIM7_RC=<n>
DU_ONCE_KB=<n> DU_SONRA_KB=<n>
KABUL_SATIRI=<06-kabul.txt icindeki son KABUL= satiri birebir>
```
