# SPEC — B4 tur-3: R2 mutasyon çapası onarıldı, batarya yeniden koşulur

> **KOD YAZMA.** Komutları sırayla koş, HAM çıktıyı dosyaya dök. Yorum YOK.
> Bir adım kırmızıysa **DURMA**. `git commit`/`git push` YOK.

Çıktı dizini: `/Users/okan/.claude/cron/b4-kanit3` (yoksa oluştur)

## ADIM 1 — düzeltilmiş bataryayı kur

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b4-kur.py --uygula
```
→ `/Users/okan/.claude/cron/b4-kanit3/01-uygula.txt` (+ `RC=` satırı)

## ADIM 2 — B4 KABUL BATARYASI

```
python3 /Users/okan/.claude/cron/nobet-eskalasyon-bayat-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit3/02-b4-kabul.txt` (+ `RC=` satırı)

## ADIM 3 — TAM REGRESYON

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit3/03-nobet-kabul.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kapi-mutasyon.py
```
→ `/Users/okan/.claude/cron/b4-kanit3/03b-mutasyon.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/gozcu-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit3/03c-gozcu.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-tetik-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit3/03d-tetik.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-tur-izolasyon-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit3/03e-b7.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-sayac-cikis-yollari-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit3/03f-b8.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-icra-hali-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit3/03g-b6.txt` (+ `RC=` satırı)

```
python3 /Users/okan/.claude/cron/nobet-kosum-hukmu-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit3/03h-b5.txt` (+ `RC=` satırı)

```
python3 /Users/okan/dev/pruvo/tools/nobet-sayac-durustluk-test.py
```
→ `/Users/okan/.claude/cron/b4-kanit3/03i-sayac-durustluk.txt` (+ `RC=` satırı)

## ADIM 4 — KURU tur (canlıya YAZMAZ)

```
cat /Users/okan/.claude/cron/nobet-onarimsiz-sayac.json
```
```
python3 /Users/okan/.claude/cron/nobet-kapi.py --tur-kapat --kuru
```
→ `/Users/okan/.claude/cron/b4-kanit3/04-kuru-tur.txt` (+ `RC=` satırı)

## ADIM 5 — TEMİZLİK (Okan disk kuralı)

```
du -sk /Users/okan/.claude/cron
```
```
rm -rf /Users/okan/.claude/cron/b7-kanit /Users/okan/.claude/cron/b7-kanit2 /Users/okan/.claude/cron/b8-kanit /Users/okan/.claude/cron/b6-kanit /Users/okan/.claude/cron/b5-kanit /Users/okan/.claude/cron/b4-kanit /Users/okan/.claude/cron/b4-kanit2
```
```
du -sk /Users/okan/.claude/cron
```
```
ls -a /Users/okan/.claude/cron | grep -E "^\.b[4-8]-"
```
```
ls /Users/okan/.claude/cron | grep "yedek-b[4-8]-"
```
Ara koşum yedeklerinden **her dosya için yalnız EN ESKİ olanı** bırak (o,
N4B öncesi hâle dönüş yolu); aynı dosyanın daha yeni ara yedeklerini sil:

```
rm -f /Users/okan/.claude/cron/isci.sh.yedek-b7-20260820T135100Z /Users/okan/.claude/cron/nobet-kapi.py.yedek-b7-20260820T135100Z /Users/okan/.claude/cron/testler.py.yedek-b7-20260820T135100Z /Users/okan/.claude/cron/nobet-kapi.py.yedek-b8-20260820T142528Z /Users/okan/.claude/cron/testler.py.yedek-b8-20260820T142528Z /Users/okan/.claude/cron/gozcu.py.yedek-b6-20260820T141451Z /Users/okan/.claude/cron/gozcu.py.yedek-b6-20260820T142529Z /Users/okan/.claude/cron/nobet-tetik.py.yedek-b6-20260820T141451Z /Users/okan/.claude/cron/nobet-tetik.py.yedek-b6-20260820T142529Z /Users/okan/.claude/cron/testler.py.yedek-b6-20260820T141451Z /Users/okan/.claude/cron/testler.py.yedek-b6-20260820T142529Z /Users/okan/.claude/cron/gozcu.py.yedek-b5-20260820T142529Z /Users/okan/.claude/cron/nobet-kapi.py.yedek-b5-20260820T142529Z /Users/okan/.claude/cron/testler.py.yedek-b5-20260820T142529Z /Users/okan/.claude/cron/gozcu-test.py.yedek-b5-20260820T142529Z /Users/okan/.claude/cron/nobet-kapi.py.yedek-b4-20260820T143210Z /Users/okan/.claude/cron/testler.py.yedek-b4-20260820T143210Z /Users/okan/.claude/cron/nobet-kabul-test.py.yedek-b4-20260820T143210Z
```
```
ls /Users/okan/.claude/cron | grep "yedek-b[4-8]-"
```
→ hepsinin çıktısı `/Users/okan/.claude/cron/b4-kanit3/05-temizlik.txt`
🔴 `b4-kanit3` dizinini SİLME (kanıt orada).
🔴 Yukarıda ADI GEÇMEYEN hiçbir yedeği SİLME.

## SON MESAJIN — yalnızca şu blok

```
ADIM1_RC=<n>
ADIM2_RC=<n>
ADIM3_RC=<n> ADIM3B_RC=<n> ADIM3C_RC=<n> ADIM3D_RC=<n> ADIM3E_RC=<n> ADIM3F_RC=<n> ADIM3G_RC=<n> ADIM3H_RC=<n> ADIM3I_RC=<n>
ADIM4_RC=<n>
DU_ONCE_KB=<n> DU_SONRA_KB=<n>
KANIT_DIZINI=/Users/okan/.claude/cron/b4-kanit3
```

🔴 `✅ İŞ BİTTİ` jetonu YAZMA. Hüküm mimarındır.
