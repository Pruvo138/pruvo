# SPEC — B4 R2 mutantı yeniden tanımlandı: batarya yeniden koşulur (İŞÇİ, mekanik)

> **KOD YAZMA.** Komutları sırayla koş, HAM çıktıyı dosyaya dök. Yorum YOK.
> Bir adım kırmızıysa **DURMA**. `git commit`/`git push` YOK.

Çıktı dizini: `/Users/okan/.claude/cron/n4b-kapanis` (VAR, silme — içine ekle)

## ADIM 1 — düzeltilmiş bataryayı kur

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b4-kur.py --uygula
```
→ `/Users/okan/.claude/cron/n4b-kapanis/09-b4-uygula.txt` (+ `RC=` satırı)

## ADIM 2 — B4 KABUL BATARYASI

```
python3 /Users/okan/.claude/cron/nobet-eskalasyon-bayat-test.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/09b-b4-kabul.txt` (+ `RC=` satırı)

## ADIM 3 — REGRESYON (dört komşu)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/09c-nobet-kabul.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kapi-mutasyon.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/09d-mutasyon.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/gozcu-test.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/09e-gozcu.txt` (+ `RC=` satırı)

```
python3 /Users/okan/dev/pruvo/tools/nobet-sayac-durustluk-test.py
```
→ `/Users/okan/.claude/cron/n4b-kapanis/09f-sayac-durustluk.txt` (+ `RC=` satırı)

## ADIM 4 — TEMİZLİK

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
→ hepsinin çıktısı `/Users/okan/.claude/cron/n4b-kapanis/09g-temizlik.txt`
🔴 `n4b-kapanis` dizinini SİLME · `*.yedek-b[4-8]-*` dosyalarını SİLME.

## SON MESAJIN — yalnızca şu blok

```
ADIM1_RC=<n>
ADIM2_RC=<n>
ADIM3_RC=<n> ADIM3B_RC=<n> ADIM3C_RC=<n> ADIM3D_RC=<n>
DU_ONCE_KB=<n> DU_SONRA_KB=<n>
KANIT_DIZINI=/Users/okan/.claude/cron/n4b-kapanis
```

🔴 `✅ İŞ BİTTİ` jetonu YAZMA. Hüküm mimarındır.
