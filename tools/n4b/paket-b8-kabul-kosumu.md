# SPEC — B8 kurulum + kabul koşumu (İŞÇİ TURU, mekanik)

> **KOD YAZMA.** Komutları sırayla koş, HAM çıktıyı dosyaya dök. Yorum/özet/tablo YOK.
> Bir adım kırmızıysa **DURMA**, sonrakileri de koş. `git commit`/`git push` YOK.
> `b8-kur.py` dışında hiçbir şey `~/.claude/cron` altına yazmayacak.

Çıktı dizini: `/Users/okan/.claude/cron/b8-kanit` (yoksa oluştur)

## ADIM 1 — sözdizimi (yama ÖNCESİ)

```
python3 -m py_compile /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b8-kur.py /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/nobet-sayac-cikis-yollari-test.py
```
→ `/Users/okan/.claude/cron/b8-kanit/01-pycompile.txt` (+ `RC=` satırı)

## ADIM 2 — TABAN (yama ÖNCESİ, ZORUNLU)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/b8-kanit/02-taban-kabul.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kapi-mutasyon.py
```
→ `/Users/okan/.claude/cron/b8-kanit/02b-taban-mutasyon.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-tur-izolasyon-test.py
```
→ `/Users/okan/.claude/cron/b8-kanit/02c-taban-b7.txt` (+ `RC=` satırı)

## ADIM 3 — kurulum ÖNCESİ envanter

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b8-kur.py
```
→ `/Users/okan/.claude/cron/b8-kanit/03-once.txt` (+ `RC=` satırı)

## ADIM 4 — yamayı uygula

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b8-kur.py --uygula
```
→ `/Users/okan/.claude/cron/b8-kanit/04-uygula.txt` (+ `RC=` satırı)

## ADIM 5 — yama SONRASI sözdizimi

```
python3 -m py_compile /Users/okan/.claude/cron/nobet-kapi.py /Users/okan/.claude/cron/testler.py
```
→ `/Users/okan/.claude/cron/b8-kanit/05-sozdizimi.txt` (+ `RC=` satırı)

## ADIM 6 — B8 KABUL BATARYASI (asıl ölçüm)

```
python3 /Users/okan/.claude/cron/nobet-sayac-cikis-yollari-test.py
```
→ `/Users/okan/.claude/cron/b8-kanit/06-b8-kabul.txt` (+ `RC=` satırı)

## ADIM 7 — REGRESYON (ADIM 2 ile AYNI üç komut)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/b8-kanit/07-sonra-kabul.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kapi-mutasyon.py
```
→ `/Users/okan/.claude/cron/b8-kanit/07b-sonra-mutasyon.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-tur-izolasyon-test.py
```
→ `/Users/okan/.claude/cron/b8-kanit/07c-sonra-b7.txt` (+ `RC=` satırı)

## ADIM 8 — artık taraması

```
ls -la /Users/okan/.claude/cron/isci-tur-cikti
```
```
ls -a /Users/okan/.claude/cron | grep "b8-mutant"
```
→ `/Users/okan/.claude/cron/b8-kanit/08-artik.txt`

## SON MESAJIN — yalnızca şu blok

```
ADIM1_RC=<n>
ADIM2_RC=<n> ADIM2B_RC=<n> ADIM2C_RC=<n>
ADIM3_RC=<n>
ADIM4_RC=<n>
ADIM5_RC=<n>
ADIM6_RC=<n>
ADIM7_RC=<n> ADIM7B_RC=<n> ADIM7C_RC=<n>
KANIT_DIZINI=/Users/okan/.claude/cron/b8-kanit
```

🔴 `✅ İŞ BİTTİ` jetonu YAZMA. Hüküm mimarındır.
