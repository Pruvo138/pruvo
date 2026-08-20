# SPEC — B6 kurulum + kabul koşumu (İŞÇİ TURU, mekanik)

> **KOD YAZMA.** Komutları sırayla koş, HAM çıktıyı dosyaya dök. Yorum/özet/tablo YOK.
> Bir adım kırmızıysa **DURMA**, sonrakileri de koş. `git commit`/`git push` YOK.
> `b6-kur.py` dışında hiçbir şey `~/.claude/cron` altına yazmayacak.

Çıktı dizini: `/Users/okan/.claude/cron/b6-kanit` (yoksa oluştur)

## ADIM 1 — sözdizimi (yama ÖNCESİ)

```
python3 -m py_compile /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b6-kur.py /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/nobet-icra-hali-test.py
```
→ `/Users/okan/.claude/cron/b6-kanit/01-pycompile.txt` (+ `RC=` satırı)

## ADIM 2 — TABAN (yama ÖNCESİ, ZORUNLU)

```
python3 /Users/okan/.claude/cron/gozcu-test.py
```
→ `/Users/okan/.claude/cron/b6-kanit/02-taban-gozcu.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-tetik-test.py
```
→ `/Users/okan/.claude/cron/b6-kanit/02b-taban-tetik.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/gozcu-mutasyon.py
```
→ `/Users/okan/.claude/cron/b6-kanit/02c-taban-gozcu-mutasyon.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-tetik-mutasyon.py
```
→ `/Users/okan/.claude/cron/b6-kanit/02d-taban-tetik-mutasyon.txt` (+ `RC=` satırı)

## ADIM 3 — kurulum ÖNCESİ envanter

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b6-kur.py
```
→ `/Users/okan/.claude/cron/b6-kanit/03-once.txt` (+ `RC=` satırı)

## ADIM 4 — yamayı uygula

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b6-kur.py --uygula
```
→ `/Users/okan/.claude/cron/b6-kanit/04-uygula.txt` (+ `RC=` satırı)

## ADIM 5 — yama SONRASI sözdizimi

```
python3 -m py_compile /Users/okan/.claude/cron/gozcu.py /Users/okan/.claude/cron/nobet-tetik.py /Users/okan/.claude/cron/testler.py
```
→ `/Users/okan/.claude/cron/b6-kanit/05-sozdizimi.txt` (+ `RC=` satırı)

## ADIM 6 — B6 KABUL BATARYASI (asıl ölçüm)

```
python3 /Users/okan/.claude/cron/nobet-icra-hali-test.py
```
→ `/Users/okan/.claude/cron/b6-kanit/06-b6-kabul.txt` (+ `RC=` satırı)

## ADIM 7 — REGRESYON (ADIM 2 ile AYNI dört komut)

```
python3 /Users/okan/.claude/cron/gozcu-test.py
```
→ `/Users/okan/.claude/cron/b6-kanit/07-sonra-gozcu.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-tetik-test.py
```
→ `/Users/okan/.claude/cron/b6-kanit/07b-sonra-tetik.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/gozcu-mutasyon.py
```
→ `/Users/okan/.claude/cron/b6-kanit/07c-sonra-gozcu-mutasyon.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-tetik-mutasyon.py
```
→ `/Users/okan/.claude/cron/b6-kanit/07d-sonra-tetik-mutasyon.txt` (+ `RC=` satırı)

## ADIM 8 — komşu bataryalar (B7/B8) hâlâ yeşil mi

```
python3 /Users/okan/.claude/cron/nobet-sayac-cikis-yollari-test.py
```
→ `/Users/okan/.claude/cron/b6-kanit/08-b8.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/b6-kanit/08b-nobet-kabul.txt` (+ `RC=` satırı)

## ADIM 9 — artık taraması

```
ls -a /Users/okan/.claude/cron | grep "b6-"
```
→ `/Users/okan/.claude/cron/b6-kanit/09-artik.txt`

## SON MESAJIN — yalnızca şu blok

```
ADIM1_RC=<n>
ADIM2_RC=<n> ADIM2B_RC=<n> ADIM2C_RC=<n> ADIM2D_RC=<n>
ADIM3_RC=<n>
ADIM4_RC=<n>
ADIM5_RC=<n>
ADIM6_RC=<n>
ADIM7_RC=<n> ADIM7B_RC=<n> ADIM7C_RC=<n> ADIM7D_RC=<n>
ADIM8_RC=<n> ADIM8B_RC=<n>
KANIT_DIZINI=/Users/okan/.claude/cron/b6-kanit
```

🔴 `✅ İŞ BİTTİ` jetonu YAZMA. Hüküm mimarındır.
