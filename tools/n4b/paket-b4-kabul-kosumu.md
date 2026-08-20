# SPEC — düzeltilmiş bataryalar + B4 kurulum/kabul (İŞÇİ TURU, mekanik)

> **KOD YAZMA.** Komutları sırayla koş, HAM çıktıyı dosyaya dök. Yorum/özet/tablo YOK.
> Bir adım kırmızıysa **DURMA**, sonrakileri de koş. `git commit`/`git push` YOK.
> Yalnız `b*-kur.py` betikleri `~/.claude/cron` altına yazar.

Çıktı dizini: `/Users/okan/.claude/cron/b4-kanit` (yoksa oluştur)

## ADIM 1 — sözdizimi

```
python3 -m py_compile /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b4-kur.py /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/nobet-eskalasyon-bayat-test.py /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/nobet-sayac-cikis-yollari-test.py /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/nobet-icra-hali-test.py /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b5-kur.py
```
→ `/Users/okan/.claude/cron/b4-kanit/01-pycompile.txt` (+ `RC=` satırı)

## ADIM 2 — düzeltilmiş B6/B8 bataryalarını ve B5 P8 yamasını kur

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b8-kur.py --uygula
```
→ `/Users/okan/.claude/cron/b4-kanit/02-b8-uygula.txt` (+ `RC=` satırı)

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b6-kur.py --uygula
```
→ `/Users/okan/.claude/cron/b4-kanit/02b-b6-uygula.txt` (+ `RC=` satırı)

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b5-kur.py --uygula
```
→ `/Users/okan/.claude/cron/b4-kanit/02c-b5-uygula.txt` (+ `RC=` satırı)

## ADIM 3 — TABAN (B4 yaması ÖNCESİ, ZORUNLU)

```
python3 /Users/okan/.claude/cron/nobet-tur-izolasyon-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit/03-taban-b7.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-sayac-cikis-yollari-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit/03b-taban-b8.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-icra-hali-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit/03c-taban-b6.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kosum-hukmu-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit/03d-taban-b5.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/gozcu-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit/03e-taban-gozcu.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit/03f-taban-nobet-kabul.txt` (+ `RC=` satırı)

## ADIM 4 — B4 envanteri ve uygulaması

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b4-kur.py
```
→ `/Users/okan/.claude/cron/b4-kanit/04-once.txt` (+ `RC=` satırı)

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b4-kur.py --uygula
```
→ `/Users/okan/.claude/cron/b4-kanit/04b-uygula.txt` (+ `RC=` satırı)

## ADIM 5 — yama SONRASI sözdizimi

```
python3 -m py_compile /Users/okan/.claude/cron/nobet-kapi.py /Users/okan/.claude/cron/gozcu.py /Users/okan/.claude/cron/testler.py /Users/okan/.claude/cron/gozcu-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit/05-sozdizimi.txt` (+ `RC=` satırı)

## ADIM 6 — B4 KABUL BATARYASI (asıl ölçüm)

```
python3 /Users/okan/.claude/cron/nobet-eskalasyon-bayat-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit/06-b4-kabul.txt` (+ `RC=` satırı)

```
python3 /Users/okan/dev/pruvo/tools/nobet-sayac-durustluk-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit/06b-sayac-durustluk.txt` (+ `RC=` satırı)

## ADIM 7 — REGRESYON (ADIM 3 ile AYNI altı komut)

```
python3 /Users/okan/.claude/cron/nobet-tur-izolasyon-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit/07-sonra-b7.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-sayac-cikis-yollari-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit/07b-sonra-b8.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-icra-hali-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit/07c-sonra-b6.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kosum-hukmu-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit/07d-sonra-b5.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/gozcu-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit/07e-sonra-gozcu.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit/07f-sonra-nobet-kabul.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kapi-mutasyon.py
```
→ `/Users/okan/.claude/cron/b4-kanit/07g-sonra-mutasyon.txt` (+ `RC=` satırı)

## ADIM 8 — CANLI DURUM (salt okuma, YAZMA YOK)

```
cat /Users/okan/.claude/cron/nobet-onarimsiz-sayac.json
```
```
python3 /Users/okan/.claude/cron/nobet-kapi.py --tur-kapat --kuru
```
→ ikisinin çıktısı `/Users/okan/.claude/cron/b4-kanit/08-kuru-tur.txt` (+ `RC=` satırı)
(`--kuru` YAZMAZ; yalnız planı basar.)

## ADIM 9 — artık taraması

```
ls -a /Users/okan/.claude/cron | grep -E "^\.b[4-8]-"
```
```
ls -la /Users/okan/.claude/cron/isci-tur-cikti
```
→ `/Users/okan/.claude/cron/b4-kanit/09-artik.txt`

## SON MESAJIN — yalnızca şu blok

```
ADIM1_RC=<n>
ADIM2_RC=<n> ADIM2B_RC=<n> ADIM2C_RC=<n>
ADIM3_RC=<n> ADIM3B_RC=<n> ADIM3C_RC=<n> ADIM3D_RC=<n> ADIM3E_RC=<n> ADIM3F_RC=<n>
ADIM4_RC=<n> ADIM4B_RC=<n>
ADIM5_RC=<n>
ADIM6_RC=<n> ADIM6B_RC=<n>
ADIM7_RC=<n> ADIM7B_RC=<n> ADIM7C_RC=<n> ADIM7D_RC=<n> ADIM7E_RC=<n> ADIM7F_RC=<n> ADIM7G_RC=<n>
ADIM8_RC=<n>
KANIT_DIZINI=/Users/okan/.claude/cron/b4-kanit
```

🔴 `✅ İŞ BİTTİ` jetonu YAZMA. Hüküm mimarındır.
