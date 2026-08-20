# SPEC — B4 tur-2: mükerrer satırı temizle → düzeltilmiş yamaları kur → tam kabul

> **KOD YAZMA.** Komutları sırayla koş, HAM çıktıyı dosyaya dök. Yorum/özet/tablo YOK.
> Bir adım kırmızıysa **DURMA**, sonrakileri de koş. `git commit`/`git push` YOK.

Çıktı dizini: `/Users/okan/.claude/cron/b4-kanit2` (yoksa oluştur)

## ADIM 1 — sözdizimi

```
python3 -m py_compile /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b4-kur.py /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b6-kur.py /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/nobet-eskalasyon-bayat-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit2/01-pycompile.txt` (+ `RC=` satırı)

## ADIM 2 — B4 yamasını GERİ AL, sonra gozcu.py'deki mükerrer satırı temizle

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b4-kur.py --geri-al 20260820T142548Z
```
→ `/Users/okan/.claude/cron/b4-kanit2/02-b4-geri-al.txt` (+ `RC=` satırı)
(Damga farklıysa: `ls /Users/okan/.claude/cron | grep "yedek-b4-"` ile bul ve o damgayı kullan; kullandığın damgayı dosyaya yaz.)

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b6-kur.py --geri-al 20260820T142529Z
```
→ `/Users/okan/.claude/cron/b4-kanit2/02b-b6-geri-al.txt` (+ `RC=` satırı)

```
grep -n "icra_hal = " /Users/okan/.claude/cron/gozcu.py
```
→ `/Users/okan/.claude/cron/b4-kanit2/02c-mukerrer-kontrol.txt`
(Beklenen: `icra_hal = "KOSULMADI"` satırı **TAM 1** kez.)

## ADIM 3 — TABAN (B4 ÖNCESİ, ZORUNLU)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit2/03-taban-nobet-kabul.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/gozcu-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit2/03b-taban-gozcu.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-icra-hali-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit2/03c-taban-b6.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kosum-hukmu-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit2/03d-taban-b5.txt` (+ `RC=` satırı)

## ADIM 4 — B6 envanterini ve B4'ü uygula

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b6-kur.py
```
→ `/Users/okan/.claude/cron/b4-kanit2/04-b6-envanter.txt` (+ `RC=` satırı)

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b4-kur.py --uygula
```
→ `/Users/okan/.claude/cron/b4-kanit2/04b-b4-uygula.txt` (+ `RC=` satırı)

## ADIM 5 — sözdizimi

```
python3 -m py_compile /Users/okan/.claude/cron/nobet-kapi.py /Users/okan/.claude/cron/gozcu.py /Users/okan/.claude/cron/nobet-kabul-test.py /Users/okan/.claude/cron/testler.py
```
→ `/Users/okan/.claude/cron/b4-kanit2/05-sozdizimi.txt` (+ `RC=` satırı)

## ADIM 6 — B4 KABUL BATARYASI

```
python3 /Users/okan/.claude/cron/nobet-eskalasyon-bayat-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit2/06-b4-kabul.txt` (+ `RC=` satırı)

```
python3 /Users/okan/dev/pruvo/tools/nobet-sayac-durustluk-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit2/06b-sayac-durustluk.txt` (+ `RC=` satırı)

## ADIM 7 — REGRESYON (ADIM 3 ile AYNI dört komut + üç komşu)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit2/07-sonra-nobet-kabul.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/gozcu-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit2/07b-sonra-gozcu.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-icra-hali-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit2/07c-sonra-b6.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kosum-hukmu-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit2/07d-sonra-b5.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-tur-izolasyon-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit2/07e-sonra-b7.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-sayac-cikis-yollari-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit2/07f-sonra-b8.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kapi-mutasyon.py
```
→ `/Users/okan/.claude/cron/b4-kanit2/07g-sonra-mutasyon.txt` (+ `RC=` satırı)

## ADIM 8 — KURU tur (canlıya YAZMAZ) + canlı sayaç

```
cat /Users/okan/.claude/cron/nobet-onarimsiz-sayac.json
```
```
python3 /Users/okan/.claude/cron/nobet-kapi.py --tur-kapat --kuru
```
→ `/Users/okan/.claude/cron/b4-kanit2/08-kuru-tur.txt` (+ `RC=` satırı)

## ADIM 9 — artık taraması

```
ls -a /Users/okan/.claude/cron | grep -E "^\.b[4-8]-"
```
```
ls -la /Users/okan/.claude/cron/isci-tur-cikti
```
→ `/Users/okan/.claude/cron/b4-kanit2/09-artik.txt`

## SON MESAJIN — yalnızca şu blok

```
ADIM1_RC=<n>
ADIM2_RC=<n> ADIM2B_RC=<n> KULLANILAN_B4_DAMGASI=<damga>
ADIM3_RC=<n> ADIM3B_RC=<n> ADIM3C_RC=<n> ADIM3D_RC=<n>
ADIM4_RC=<n> ADIM4B_RC=<n>
ADIM5_RC=<n>
ADIM6_RC=<n> ADIM6B_RC=<n>
ADIM7_RC=<n> ADIM7B_RC=<n> ADIM7C_RC=<n> ADIM7D_RC=<n> ADIM7E_RC=<n> ADIM7F_RC=<n> ADIM7G_RC=<n>
ADIM8_RC=<n>
KANIT_DIZINI=/Users/okan/.claude/cron/b4-kanit2
```

🔴 `✅ İŞ BİTTİ` jetonu YAZMA. Hüküm mimarındır.
