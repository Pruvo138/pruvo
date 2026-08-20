# SPEC — B7 tur-2: geri al → yeniden uygula → kabul + regresyon (İŞÇİ, mekanik)

> **KOD YAZMA.** Komutları sırayla koş, HAM çıktıyı dosyaya dök. Yorum/özet/tablo YOK.
> Bir adım kırmızıysa **DURMA**, sonrakileri de koş. `git commit`/`git push` YOK.

Çıktı dizini: `/Users/okan/.claude/cron/b7-kanit2` (yoksa oluştur)

## ADIM 1 — önceki yamayı GERİ AL

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b7-kur.py --geri-al 20260820T134632Z
```
→ `/Users/okan/.claude/cron/b7-kanit2/01-geri-al.txt` (+ `RC=` satırı)

## ADIM 2 — TABAN (yamasız) regresyon ölçümü

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/b7-kanit2/02-taban.txt` (+ `RC=` satırı)

## ADIM 3 — düzeltilmiş yamayı uygula

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b7-kur.py --uygula
```
→ `/Users/okan/.claude/cron/b7-kanit2/03-uygula.txt` (+ `RC=` satırı)

## ADIM 4 — sözdizimi

```
python3 -m py_compile /Users/okan/.claude/cron/nobet-kapi.py /Users/okan/.claude/cron/nobet-kabul-test.py /Users/okan/.claude/cron/testler.py
```
```
zsh -n /Users/okan/.claude/cron/isci.sh
```
→ `/Users/okan/.claude/cron/b7-kanit2/04-sozdizimi.txt` (`PYCOMPILE_RC=` ve `ZSH_N_RC=` satırlarıyla)

## ADIM 5 — B7 KABUL BATARYASI

```
python3 /Users/okan/.claude/cron/nobet-tur-izolasyon-test.py
```
→ `/Users/okan/.claude/cron/b7-kanit2/05-b7-kabul.txt` (+ `RC=` satırı)
~1-3 dakika sürer, **kesme**.

## ADIM 6 — REGRESYON (ADIM 2 ile aynı komut)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/b7-kanit2/06-sonra.txt` (+ `RC=` satırı)

## ADIM 7 — mutasyon bataryası (komşu)

```
python3 /Users/okan/.claude/cron/nobet-kapi-mutasyon.py
```
→ `/Users/okan/.claude/cron/b7-kanit2/07-mutasyon.txt` (+ `RC=` satırı)

## ADIM 8 — artık taraması

```
ls -la /Users/okan/.claude/cron/isci-tur-cikti
```
```
ls /Users/okan/.claude/cron | grep -c "^profil-kimi-ev-izo"
```
→ `/Users/okan/.claude/cron/b7-kanit2/08-artik.txt`

## SON MESAJIN — yalnızca şu blok

```
ADIM1_RC=<n>
ADIM2_RC=<n>
ADIM3_RC=<n>
ADIM4_PYCOMPILE_RC=<n> ADIM4_ZSH_RC=<n>
ADIM5_RC=<n>
ADIM6_RC=<n>
ADIM7_RC=<n>
KANIT_DIZINI=/Users/okan/.claude/cron/b7-kanit2
```

🔴 `✅ İŞ BİTTİ` jetonu YAZMA. Hüküm mimarındır.
