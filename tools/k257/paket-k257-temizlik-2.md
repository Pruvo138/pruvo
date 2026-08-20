# SPEC — K257 tur-4 temizliği (İŞÇİ TURU) — disk kuralı: ÜRETEN TEMİZLER

> **KOD YAZMA. YORUM YAZMA.** Komutları SIRAYLA koş, HAM çıktıyı dosyaya dök.
> `git commit` / `git push` YOK. 🔴 `✅ İŞ BİTTİ` jetonu YAZMA.
>
> 🔴 **SİLİNMEYECEKLER:** `*.yedek-k257-20260820T202429Z` ile biten DÖRT dosya
> (canlı yamanın `--geri-al` yolu) ve `nobet_merdiven.py`,
> `nobet-merdiven-test.py`, `nobet-kapi.py`, `testler.py`,
> `nobet-kapi-mutasyon.py`, `nobet-kabul-test.py`.

Kanıt dizini: `/Users/okan/.claude/cron/k257-temizlik2` (yoksa oluştur)

## ADIM 1 — ÖNCE ölçümü

```
du -sk /Users/okan/.claude/cron
```
→ `/Users/okan/.claude/cron/k257-temizlik2/01-du-once.txt` (+ `RC=`)

## ADIM 2 — kanıt dizinini sil

```
rm -rf /Users/okan/.claude/cron/k257-kanit4
```
→ `/Users/okan/.claude/cron/k257-temizlik2/02-kanit-sil.txt` (+ `RC=`)

## ADIM 3 — bayat (tur-3) yedekleri sil — SON damga KALIR

```
rm -f /Users/okan/.claude/cron/nobet-kapi.py.yedek-k257-20260820T163510Z /Users/okan/.claude/cron/testler.py.yedek-k257-20260820T163510Z /Users/okan/.claude/cron/nobet-kapi-mutasyon.py.yedek-k257-20260820T163510Z
```
→ `/Users/okan/.claude/cron/k257-temizlik2/03-bayat-yedek-sil.txt` (+ `RC=`)

## ADIM 4 — geri-al yolunun SAĞLAM olduğunu kanıtla (DÖRT dosya)

```
ls -la /Users/okan/.claude/cron/nobet-kapi.py.yedek-k257-20260820T202429Z /Users/okan/.claude/cron/testler.py.yedek-k257-20260820T202429Z /Users/okan/.claude/cron/nobet-kapi-mutasyon.py.yedek-k257-20260820T202429Z /Users/okan/.claude/cron/nobet-kabul-test.py.yedek-k257-20260820T202429Z
```
→ `/Users/okan/.claude/cron/k257-temizlik2/04-geri-al-yolu.txt` (+ `RC=`)

## ADIM 5 — artık taraması

```
ls -a /Users/okan/.claude/cron
```
→ `/Users/okan/.claude/cron/k257-temizlik2/05-artik.txt` (+ `RC=`)

## ADIM 6 — kabul bataryası HÂLÂ YEŞİL mi

```
python3 /Users/okan/.claude/cron/nobet-merdiven-test.py
```
→ `/Users/okan/.claude/cron/k257-temizlik2/06-kabul.txt` (+ `RC=`)

## ADIM 7 — SONRA ölçümü

```
du -sk /Users/okan/.claude/cron
```
→ `/Users/okan/.claude/cron/k257-temizlik2/07-du-sonra.txt` (+ `RC=`)

## SON MESAJIN — YALNIZCA şu blok

```
ADIM1_RC=<n> ADIM2_RC=<n> ADIM3_RC=<n> ADIM4_RC=<n> ADIM5_RC=<n> ADIM6_RC=<n> ADIM7_RC=<n>
DU_ONCE_KB=<n> DU_SONRA_KB=<n>
KABUL_SATIRI=<06-kabul.txt icindeki son KABUL= satiri birebir>
```
