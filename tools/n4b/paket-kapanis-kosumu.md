# SPEC — N4B KAPANIŞ KOŞUMU: B5 N4/N5 + B4 R2 onarımı + tam kabul (İŞÇİ, mekanik)

> **KOD YAZMA.** Komutları sırayla koş, HAM çıktıyı dosyaya dök. Yorum YOK.
> Bir adım kırmızıysa **DURMA**. `git commit`/`git push` YOK.

Çıktı dizini: `/Users/okan/.claude/cron/n4b-kapanis` (yoksa oluştur)

## ADIM 1 — sözdizimi

```
python3 -m py_compile /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b5-kur.py /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b4-kur.py /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/nobet-kosum-hukmu-test.py /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/nobet-eskalasyon-bayat-test.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/01-pycompile.txt` (+ `RC=` satırı)

## ADIM 2 — TABAN (yeni yamalar ÖNCESİ)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/02-taban-nobet-kabul.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/gozcu-test.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/02b-taban-gozcu.txt` (+ `RC=` satırı)

## ADIM 3 — B5 (N4/N5) ve B4 (R2 bataryası) yamalarını uygula

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b5-kur.py --uygula
```
→ `/Users/okan/.claude/cron/n4b-kapanis/03-b5-uygula.txt` (+ `RC=` satırı)

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b4-kur.py --uygula
```
→ `/Users/okan/.claude/cron/n4b-kapanis/03b-b4-uygula.txt` (+ `RC=` satırı)

```
python3 -m py_compile /Users/okan/.claude/cron/nobet-kapi.py /Users/okan/.claude/cron/gozcu.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/03c-sozdizimi.txt` (+ `RC=` satırı)

## ADIM 4 — BEŞ KABUL BATARYASI

```
python3 /Users/okan/.claude/cron/nobet-tur-izolasyon-test.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/04-b7.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-sayac-cikis-yollari-test.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/04b-b8.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-icra-hali-test.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/04c-b6.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kosum-hukmu-test.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/04d-b5.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-eskalasyon-bayat-test.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/04e-b4.txt` (+ `RC=` satırı)

## ADIM 5 — REGRESYON (ADIM 2 ile AYNI iki komut + üç komşu)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/05-sonra-nobet-kabul.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/gozcu-test.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/05b-sonra-gozcu.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kapi-mutasyon.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/05c-mutasyon.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-tetik-test.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/05d-tetik.txt` (+ `RC=` satırı)

```
python3 /Users/okan/dev/pruvo/tools/nobet-sayac-durustluk-test.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/05e-sayac-durustluk.txt` (+ `RC=` satırı)

## ADIM 6 — ÇAĞRI YERİ: testler.py kayıtları

```
grep -n "nobet-" /Users/okan/.claude/cron/testler.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/06-cagri-yeri.txt` (+ `RC=` satırı)

## ADIM 7 — CANLI DURUM (salt okuma / KURU)

```
cat /Users/okan/.claude/cron/nobet-onarimsiz-sayac.json
```
```
python3 /Users/okan/.claude/cron/nobet-kapi.py --tur-kapat --kuru
```
→ `/Users/okan/.claude/cron/n4b-kapanis/07-kuru-tur.txt` (+ `RC=` satırı)

```
grep -n "TUR_CIKTI=\|KOSUM_HUKMU=\|TUR_HALI=\|ESKALASYON_BAYAT" /Users/okan/.claude/cron/gozcu.log
```
→ `/Users/okan/.claude/cron/n4b-kapanis/07b-canli-jetonlar.txt` (+ `RC=` satırı)

## ADIM 8 — TEMİZLİK (Okan disk kuralı)

```
du -sk /Users/okan/.claude/cron
```
```
rm -rf /Users/okan/.claude/cron/b4-kanit3
```
```
du -sk /Users/okan/.claude/cron
```
```
ls -a /Users/okan/.claude/cron | grep -E "^\.b[4-8]-"
```
```
ls -la /Users/okan/.claude/cron/isci-tur-cikti
```
→ hepsinin çıktısı `/Users/okan/.claude/cron/n4b-kapanis/08-temizlik.txt`
🔴 `n4b-kapanis` dizinini SİLME · `*.yedek-b[4-8]-*` dosyalarını SİLME.

## SON MESAJIN — yalnızca şu blok

```
ADIM1_RC=<n>
ADIM2_RC=<n> ADIM2B_RC=<n>
ADIM3_RC=<n> ADIM3B_RC=<n> ADIM3C_RC=<n>
ADIM4_RC=<n> ADIM4B_RC=<n> ADIM4C_RC=<n> ADIM4D_RC=<n> ADIM4E_RC=<n>
ADIM5_RC=<n> ADIM5B_RC=<n> ADIM5C_RC=<n> ADIM5D_RC=<n> ADIM5E_RC=<n>
ADIM6_RC=<n>
ADIM7_RC=<n>
DU_ONCE_KB=<n> DU_SONRA_KB=<n>
KANIT_DIZINI=/Users/okan/.claude/cron/n4b-kapanis
```

🔴 `✅ İŞ BİTTİ` jetonu YAZMA. Hüküm mimarındır.
