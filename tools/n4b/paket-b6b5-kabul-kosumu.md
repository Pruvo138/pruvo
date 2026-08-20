# SPEC — B6 yeniden koşum + B5 kurulum/kabul (İŞÇİ TURU, mekanik)

> **KOD YAZMA.** Komutları sırayla koş, HAM çıktıyı dosyaya dök. Yorum/özet/tablo YOK.
> Bir adım kırmızıysa **DURMA**, sonrakileri de koş. `git commit`/`git push` YOK.
> Yalnız `b6-kur.py` / `b5-kur.py` `~/.claude/cron` altına yazar.

Çıktı dizini: `/Users/okan/.claude/cron/b5-kanit` (yoksa oluştur)

## ADIM 1 — sözdizimi

```
python3 -m py_compile /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b5-kur.py /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/nobet-kosum-hukmu-test.py /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/nobet-icra-hali-test.py
```
→ `/Users/okan/.claude/cron/b5-kanit/01-pycompile.txt` (+ `RC=` satırı)

## ADIM 2 — B6 bataryasının DÜZELTİLMİŞ kopyasını kur ve YENİDEN koş

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b6-kur.py --uygula
```
→ `/Users/okan/.claude/cron/b5-kanit/02-b6-uygula.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-icra-hali-test.py
```
→ `/Users/okan/.claude/cron/b5-kanit/02b-b6-kabul.txt` (+ `RC=` satırı)

## ADIM 3 — TABAN (B5 yaması ÖNCESİ)

```
python3 /Users/okan/.claude/cron/gozcu-test.py
```
→ `/Users/okan/.claude/cron/b5-kanit/03-taban-gozcu.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/b5-kanit/03b-taban-nobet-kabul.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-tetik-test.py
```
→ `/Users/okan/.claude/cron/b5-kanit/03c-taban-tetik.txt` (+ `RC=` satırı)

## ADIM 4 — B5 envanteri ve uygulaması

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b5-kur.py
```
→ `/Users/okan/.claude/cron/b5-kanit/04-once.txt` (+ `RC=` satırı)

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b5-kur.py --uygula
```
→ `/Users/okan/.claude/cron/b5-kanit/04b-uygula.txt` (+ `RC=` satırı)

## ADIM 5 — yama SONRASI sözdizimi

```
python3 -m py_compile /Users/okan/.claude/cron/gozcu.py /Users/okan/.claude/cron/nobet-kapi.py /Users/okan/.claude/cron/testler.py
```
→ `/Users/okan/.claude/cron/b5-kanit/05-sozdizimi.txt` (+ `RC=` satırı)

## ADIM 6 — B5 KABUL BATARYASI (asıl ölçüm)

```
python3 /Users/okan/.claude/cron/nobet-kosum-hukmu-test.py
```
→ `/Users/okan/.claude/cron/b5-kanit/06-b5-kabul.txt` (+ `RC=` satırı)

## ADIM 7 — REGRESYON (ADIM 3 ile AYNI üç komut + komşu bataryalar)

```
python3 /Users/okan/.claude/cron/gozcu-test.py
```
→ `/Users/okan/.claude/cron/b5-kanit/07-sonra-gozcu.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/b5-kanit/07b-sonra-nobet-kabul.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-tetik-test.py
```
→ `/Users/okan/.claude/cron/b5-kanit/07c-sonra-tetik.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-icra-hali-test.py
```
→ `/Users/okan/.claude/cron/b5-kanit/07d-sonra-b6.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-sayac-cikis-yollari-test.py
```
→ `/Users/okan/.claude/cron/b5-kanit/07e-sonra-b8.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-tur-izolasyon-test.py
```
→ `/Users/okan/.claude/cron/b5-kanit/07f-sonra-b7.txt` (+ `RC=` satırı)

## ADIM 8 — artık taraması

```
ls -a /Users/okan/.claude/cron | grep -E "^\.b[5678]-"
```
→ `/Users/okan/.claude/cron/b5-kanit/08-artik.txt`

## SON MESAJIN — yalnızca şu blok

```
ADIM1_RC=<n>
ADIM2_RC=<n> ADIM2B_RC=<n>
ADIM3_RC=<n> ADIM3B_RC=<n> ADIM3C_RC=<n>
ADIM4_RC=<n> ADIM4B_RC=<n>
ADIM5_RC=<n>
ADIM6_RC=<n>
ADIM7_RC=<n> ADIM7B_RC=<n> ADIM7C_RC=<n> ADIM7D_RC=<n> ADIM7E_RC=<n> ADIM7F_RC=<n>
KANIT_DIZINI=/Users/okan/.claude/cron/b5-kanit
```

🔴 `✅ İŞ BİTTİ` jetonu YAZMA. Hüküm mimarındır.
