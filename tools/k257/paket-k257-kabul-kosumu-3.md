# SPEC — K257 TUR 3: geri al → uygula → ölç → **İÇERİK FARKI** (İŞÇİ TURU)

> **KOD YAZMA. YORUM YAZMA. TABLO YAZMA.** Komutları SIRAYLA koş, HAM çıktıyı
> dosyaya dök. Bir adım kırmızıysa **DURMA**, sonrakileri de koş.
> `git commit` / `git push` YOK. `k257-kur.py` dışında hiçbir şey
> `~/.claude/cron` altına yazmayacak.
> 🔴 `✅ İŞ BİTTİ` jetonu YAZMA. Hüküm mimarındır.

Kanıt dizini: `/Users/okan/.claude/cron/k257-kanit3` (yoksa oluştur)

Her adımda: komutu koş, stdout+stderr'i belirtilen dosyaya yaz, dosyanın
SONUNA `RC=<donen kod>` satırı ekle.

## ADIM 1 — ÖNCEKİ TURUN YAMASINI GERİ AL

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/silly-mendel-3965d4/tools/k257/k257-kur.py --geri-al 20260820T162954Z
```
→ `/Users/okan/.claude/cron/k257-kanit3/01-geri-al.txt`

## ADIM 2 — TABAN (yama YOKKEN, ZORUNLU)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/02a-taban-kabul.txt`

```
python3 /Users/okan/.claude/cron/nobet-kapi-mutasyon.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/02b-taban-mutasyon.txt`

```
python3 /Users/okan/.claude/cron/nobet-tetik-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/02c-taban-tetik.txt`

```
python3 /Users/okan/dev/pruvo/tools/nobet-sayac-durustluk-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/02d-taban-durustluk.txt`

```
python3 /Users/okan/.claude/cron/nobet-sayac-cikis-yollari-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/02e-taban-b8.txt`

```
python3 /Users/okan/.claude/cron/nobet-tur-izolasyon-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/02f-taban-b7.txt`

```
python3 /Users/okan/.claude/cron/nobet-kosum-hukmu-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/02g-taban-b5.txt`

```
python3 /Users/okan/.claude/cron/nobet-icra-hali-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/02h-taban-b6.txt`

```
python3 /Users/okan/.claude/cron/nobet-eskalasyon-bayat-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/02i-taban-b4.txt`

## ADIM 3 — sözdizimi + kurulum ÖNCESİ envanter

```
python3 -m py_compile /Users/okan/dev/pruvo/.claude/worktrees/silly-mendel-3965d4/tools/k257/nobet_merdiven.py /Users/okan/dev/pruvo/.claude/worktrees/silly-mendel-3965d4/tools/k257/nobet-merdiven-test.py /Users/okan/dev/pruvo/.claude/worktrees/silly-mendel-3965d4/tools/k257/k257-kur.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/03a-pycompile.txt`

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/silly-mendel-3965d4/tools/k257/k257-kur.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/03b-once.txt`

## ADIM 4 — yamayı uygula

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/silly-mendel-3965d4/tools/k257/k257-kur.py --uygula
```
→ `/Users/okan/.claude/cron/k257-kanit3/04-uygula.txt`

## ADIM 5 — yama SONRASI sözdizimi

```
python3 -m py_compile /Users/okan/.claude/cron/nobet-kapi.py /Users/okan/.claude/cron/nobet_merdiven.py /Users/okan/.claude/cron/testler.py /Users/okan/.claude/cron/nobet-kapi-mutasyon.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/05-sozdizimi.txt`

## ADIM 6 — K257 KABUL BATARYASI (asıl ölçüm)

```
python3 /Users/okan/.claude/cron/nobet-merdiven-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/06-k257-kabul.txt`

## ADIM 7 — KURU TUR (canlı düzlemde, yan etkisiz)

```
python3 /Users/okan/.claude/cron/nobet-kapi.py --kuru
```
→ `/Users/okan/.claude/cron/k257-kanit3/07-kuru-tur.txt`

## ADIM 8 — REGRESYON (ADIM 2 ile AYNI dokuz komut, AYNI SIRA)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/08a-sonra-kabul.txt`

```
python3 /Users/okan/.claude/cron/nobet-kapi-mutasyon.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/08b-sonra-mutasyon.txt`

```
python3 /Users/okan/.claude/cron/nobet-tetik-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/08c-sonra-tetik.txt`

```
python3 /Users/okan/dev/pruvo/tools/nobet-sayac-durustluk-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/08d-sonra-durustluk.txt`

```
python3 /Users/okan/.claude/cron/nobet-sayac-cikis-yollari-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/08e-sonra-b8.txt`

```
python3 /Users/okan/.claude/cron/nobet-tur-izolasyon-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/08f-sonra-b7.txt`

```
python3 /Users/okan/.claude/cron/nobet-kosum-hukmu-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/08g-sonra-b5.txt`

```
python3 /Users/okan/.claude/cron/nobet-icra-hali-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/08h-sonra-b6.txt`

```
python3 /Users/okan/.claude/cron/nobet-eskalasyon-bayat-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit3/08i-sonra-b4.txt`

## ADIM 9 — 🔴 İÇERİK FARKI (rc YETMEZ; hüküm BURADAN çıkar)

Aşağıdaki DOKUZ `diff` komutunu koş. Her birinin çıktısını belirtilen dosyaya
yaz ve dosyanın sonuna `RC=<donen kod>` ekle. `diff` rc=0 ise dosyalar
BİREBİR AYNI demektir.

```
diff /Users/okan/.claude/cron/k257-kanit3/02a-taban-kabul.txt /Users/okan/.claude/cron/k257-kanit3/08a-sonra-kabul.txt
```
→ `/Users/okan/.claude/cron/k257-kanit3/09a-fark-kabul.txt`

```
diff /Users/okan/.claude/cron/k257-kanit3/02b-taban-mutasyon.txt /Users/okan/.claude/cron/k257-kanit3/08b-sonra-mutasyon.txt
```
→ `/Users/okan/.claude/cron/k257-kanit3/09b-fark-mutasyon.txt`

```
diff /Users/okan/.claude/cron/k257-kanit3/02c-taban-tetik.txt /Users/okan/.claude/cron/k257-kanit3/08c-sonra-tetik.txt
```
→ `/Users/okan/.claude/cron/k257-kanit3/09c-fark-tetik.txt`

```
diff /Users/okan/.claude/cron/k257-kanit3/02d-taban-durustluk.txt /Users/okan/.claude/cron/k257-kanit3/08d-sonra-durustluk.txt
```
→ `/Users/okan/.claude/cron/k257-kanit3/09d-fark-durustluk.txt`

```
diff /Users/okan/.claude/cron/k257-kanit3/02e-taban-b8.txt /Users/okan/.claude/cron/k257-kanit3/08e-sonra-b8.txt
```
→ `/Users/okan/.claude/cron/k257-kanit3/09e-fark-b8.txt`

```
diff /Users/okan/.claude/cron/k257-kanit3/02f-taban-b7.txt /Users/okan/.claude/cron/k257-kanit3/08f-sonra-b7.txt
```
→ `/Users/okan/.claude/cron/k257-kanit3/09f-fark-b7.txt`

```
diff /Users/okan/.claude/cron/k257-kanit3/02g-taban-b5.txt /Users/okan/.claude/cron/k257-kanit3/08g-sonra-b5.txt
```
→ `/Users/okan/.claude/cron/k257-kanit3/09g-fark-b5.txt`

```
diff /Users/okan/.claude/cron/k257-kanit3/02h-taban-b6.txt /Users/okan/.claude/cron/k257-kanit3/08h-sonra-b6.txt
```
→ `/Users/okan/.claude/cron/k257-kanit3/09h-fark-b6.txt`

```
diff /Users/okan/.claude/cron/k257-kanit3/02i-taban-b4.txt /Users/okan/.claude/cron/k257-kanit3/08i-sonra-b4.txt
```
→ `/Users/okan/.claude/cron/k257-kanit3/09i-fark-b4.txt`

## ADIM 10 — disk ölçümü + artık taraması

```
du -sk /Users/okan/.claude/cron
```
→ `/Users/okan/.claude/cron/k257-kanit3/10a-disk.txt`

```
ls -a /Users/okan/.claude/cron
```
→ `/Users/okan/.claude/cron/k257-kanit3/10b-artik.txt`

## SON MESAJIN — YALNIZCA şu blok, başka HİÇBİR ŞEY

```
ADIM1_RC=<n>
ADIM2_RC=<a> <b> <c> <d> <e> <f> <g> <h> <i>
ADIM3A_RC=<n> ADIM3B_RC=<n>
ADIM4_RC=<n>
ADIM5_RC=<n>
ADIM6_RC=<n>
ADIM7_RC=<n>
ADIM8_RC=<a> <b> <c> <d> <e> <f> <g> <h> <i>
FARK_RC=<a> <b> <c> <d> <e> <f> <g> <h> <i>
KANIT_DIZINI=/Users/okan/.claude/cron/k257-kanit3
```
