# SPEC — K257 kurulum + kabul koşumu (İŞÇİ TURU, mekanik)

> **KOD YAZMA. YORUM YAZMA. TABLO YAZMA.** Komutları SIRAYLA koş, HAM çıktıyı
> dosyaya dök. Bir adım kırmızıysa **DURMA**, sonrakileri de koş.
> `git commit` / `git push` YOK. `k257-kur.py` dışında hiçbir şey
> `~/.claude/cron` altına yazmayacak.
> 🔴 `✅ İŞ BİTTİ` jetonu YAZMA. Hüküm mimarındır.

Kanıt dizini: `/Users/okan/.claude/cron/k257-kanit` (yoksa oluştur)

Her adımda: komutu koş, stdout+stderr'i belirtilen dosyaya yaz, dosyanın
SONUNA `RC=<donen kod>` satırı ekle.

## ADIM 1 — sözdizimi (yama ÖNCESİ)

```
python3 -m py_compile /Users/okan/dev/pruvo/.claude/worktrees/silly-mendel-3965d4/tools/k257/nobet_merdiven.py /Users/okan/dev/pruvo/.claude/worktrees/silly-mendel-3965d4/tools/k257/nobet-merdiven-test.py /Users/okan/dev/pruvo/.claude/worktrees/silly-mendel-3965d4/tools/k257/k257-kur.py
```
→ `/Users/okan/.claude/cron/k257-kanit/01-pycompile.txt`

## ADIM 2 — TABAN (yama ÖNCESİ, ZORUNLU)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit/02a-taban-kabul.txt`

```
python3 /Users/okan/.claude/cron/nobet-kapi-mutasyon.py
```
→ `/Users/okan/.claude/cron/k257-kanit/02b-taban-mutasyon.txt`

```
python3 /Users/okan/.claude/cron/nobet-tetik-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit/02c-taban-tetik.txt`

```
python3 /Users/okan/dev/pruvo/tools/nobet-sayac-durustluk-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit/02d-taban-sayac-durustluk.txt`

## ADIM 3 — kurulum ÖNCESİ envanter

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/silly-mendel-3965d4/tools/k257/k257-kur.py
```
→ `/Users/okan/.claude/cron/k257-kanit/03-once.txt`

## ADIM 4 — yamayı uygula

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/silly-mendel-3965d4/tools/k257/k257-kur.py --uygula
```
→ `/Users/okan/.claude/cron/k257-kanit/04-uygula.txt`

## ADIM 5 — yama SONRASI sözdizimi

```
python3 -m py_compile /Users/okan/.claude/cron/nobet-kapi.py /Users/okan/.claude/cron/nobet_merdiven.py /Users/okan/.claude/cron/testler.py
```
→ `/Users/okan/.claude/cron/k257-kanit/05-sozdizimi.txt`

## ADIM 6 — K257 KABUL BATARYASI (asıl ölçüm)

```
python3 /Users/okan/.claude/cron/nobet-merdiven-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit/06-k257-kabul.txt`

## ADIM 7 — KURU TUR (canlı düzlemde, yan etkisiz)

```
python3 /Users/okan/.claude/cron/nobet-kapi.py --kuru
```
→ `/Users/okan/.claude/cron/k257-kanit/07-kuru-tur.txt`

## ADIM 8 — REGRESYON (ADIM 2 ile AYNI dört komut)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit/08a-sonra-kabul.txt`

```
python3 /Users/okan/.claude/cron/nobet-kapi-mutasyon.py
```
→ `/Users/okan/.claude/cron/k257-kanit/08b-sonra-mutasyon.txt`

```
python3 /Users/okan/.claude/cron/nobet-tetik-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit/08c-sonra-tetik.txt`

```
python3 /Users/okan/dev/pruvo/tools/nobet-sayac-durustluk-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit/08d-sonra-sayac-durustluk.txt`

## ADIM 9 — N4B kardeş bataryaları (aynı dosyaya dokunuyorlar)

```
python3 /Users/okan/.claude/cron/nobet-sayac-cikis-yollari-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit/09a-b8.txt`

```
python3 /Users/okan/.claude/cron/nobet-tur-izolasyon-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit/09b-b7.txt`

```
python3 /Users/okan/.claude/cron/nobet-kosum-hukmu-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit/09c-b5.txt`

```
python3 /Users/okan/.claude/cron/nobet-icra-hali-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit/09d-b6.txt`

```
python3 /Users/okan/.claude/cron/nobet-eskalasyon-bayat-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit/09e-b4.txt`

## ADIM 10 — artık taraması

```
ls -a /Users/okan/.claude/cron
```
→ `/Users/okan/.claude/cron/k257-kanit/10-artik.txt`

## SON MESAJIN — YALNIZCA şu blok, başka HİÇBİR ŞEY

```
ADIM1_RC=<n>
ADIM2A_RC=<n> ADIM2B_RC=<n> ADIM2C_RC=<n> ADIM2D_RC=<n>
ADIM3_RC=<n>
ADIM4_RC=<n>
ADIM5_RC=<n>
ADIM6_RC=<n>
ADIM7_RC=<n>
ADIM8A_RC=<n> ADIM8B_RC=<n> ADIM8C_RC=<n> ADIM8D_RC=<n>
ADIM9A_RC=<n> ADIM9B_RC=<n> ADIM9C_RC=<n> ADIM9D_RC=<n> ADIM9E_RC=<n>
KANIT_DIZINI=/Users/okan/.claude/cron/k257-kanit
```
