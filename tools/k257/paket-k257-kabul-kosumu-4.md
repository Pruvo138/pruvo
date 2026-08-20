# SPEC — K257 TUR 4: TAM TÜRETİM + vaka 39 yeni hüküm (İŞÇİ TURU)

> **KOD YAZMA. YORUM YAZMA. TABLO YAZMA.** Komutları SIRAYLA koş, HAM çıktıyı
> dosyaya dök. Bir adım kırmızıysa **DURMA**, sonrakileri de koş.
> `git commit` / `git push` YOK. `k257-kur.py` dışında hiçbir şey
> `~/.claude/cron` altına yazmayacak.
> 🔴 `✅ İŞ BİTTİ` jetonu YAZMA. Hüküm mimarındır.

Kanıt dizini: `/Users/okan/.claude/cron/k257-kanit4` (yoksa oluştur)

Her adımda: komutu koş, stdout+stderr'i belirtilen dosyaya yaz, dosyanın
SONUNA `RC=<donen kod>` satırı ekle.

## ADIM 1 — ÖNCEKİ TURUN YAMASINI GERİ AL

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/silly-mendel-3965d4/tools/k257/k257-kur.py --geri-al 20260820T163510Z
```
→ `/Users/okan/.claude/cron/k257-kanit4/01-geri-al.txt`

## ADIM 2 — TABAN (yama YOKKEN, ZORUNLU)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/02a-taban-kabul.txt`

```
python3 /Users/okan/.claude/cron/nobet-kapi-mutasyon.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/02b-taban-mutasyon.txt`

```
python3 /Users/okan/.claude/cron/nobet-tetik-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/02c-taban-tetik.txt`

```
python3 /Users/okan/dev/pruvo/tools/nobet-sayac-durustluk-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/02d-taban-durustluk.txt`

```
python3 /Users/okan/.claude/cron/nobet-sayac-cikis-yollari-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/02e-taban-b8.txt`

```
python3 /Users/okan/.claude/cron/nobet-tur-izolasyon-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/02f-taban-b7.txt`

```
python3 /Users/okan/.claude/cron/nobet-kosum-hukmu-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/02g-taban-b5.txt`

```
python3 /Users/okan/.claude/cron/nobet-icra-hali-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/02h-taban-b6.txt`

```
python3 /Users/okan/.claude/cron/nobet-eskalasyon-bayat-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/02i-taban-b4.txt`

## ADIM 3 — sözdizimi + kurulum ÖNCESİ envanter

```
python3 -m py_compile /Users/okan/dev/pruvo/.claude/worktrees/silly-mendel-3965d4/tools/k257/nobet_merdiven.py /Users/okan/dev/pruvo/.claude/worktrees/silly-mendel-3965d4/tools/k257/nobet-merdiven-test.py /Users/okan/dev/pruvo/.claude/worktrees/silly-mendel-3965d4/tools/k257/k257-kur.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/03a-pycompile.txt`

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/silly-mendel-3965d4/tools/k257/k257-kur.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/03b-once.txt`

## ADIM 4 — yamayı uygula

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/silly-mendel-3965d4/tools/k257/k257-kur.py --uygula
```
→ `/Users/okan/.claude/cron/k257-kanit4/04-uygula.txt`

## ADIM 5 — yama SONRASI sözdizimi

```
python3 -m py_compile /Users/okan/.claude/cron/nobet-kapi.py /Users/okan/.claude/cron/nobet_merdiven.py /Users/okan/.claude/cron/testler.py /Users/okan/.claude/cron/nobet-kapi-mutasyon.py /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/05-sozdizimi.txt`

## ADIM 6 — K257 KABUL BATARYASI (asıl ölçüm)

```
python3 /Users/okan/.claude/cron/nobet-merdiven-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/06-k257-kabul.txt`

## ADIM 7 — KURU TUR (canlı düzlemde, yan etkisiz)

```
python3 /Users/okan/.claude/cron/nobet-kapi.py --kuru
```
→ `/Users/okan/.claude/cron/k257-kanit4/07-kuru-tur.txt`

## ADIM 8 — REGRESYON (ADIM 2 ile AYNI dokuz komut, AYNI SIRA)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/08a-sonra-kabul.txt`

```
python3 /Users/okan/.claude/cron/nobet-kapi-mutasyon.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/08b-sonra-mutasyon.txt`

```
python3 /Users/okan/.claude/cron/nobet-tetik-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/08c-sonra-tetik.txt`

```
python3 /Users/okan/dev/pruvo/tools/nobet-sayac-durustluk-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/08d-sonra-durustluk.txt`

```
python3 /Users/okan/.claude/cron/nobet-sayac-cikis-yollari-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/08e-sonra-b8.txt`

```
python3 /Users/okan/.claude/cron/nobet-tur-izolasyon-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/08f-sonra-b7.txt`

```
python3 /Users/okan/.claude/cron/nobet-kosum-hukmu-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/08g-sonra-b5.txt`

```
python3 /Users/okan/.claude/cron/nobet-icra-hali-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/08h-sonra-b6.txt`

```
python3 /Users/okan/.claude/cron/nobet-eskalasyon-bayat-test.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/08i-sonra-b4.txt`

## ADIM 9 — 🔴 İÇERİK FARKI (rc YETMEZ)

Dokuz `diff` komutunu koş; çıktıyı dosyaya yaz, sonuna `RC=` ekle.

```
diff /Users/okan/.claude/cron/k257-kanit4/02a-taban-kabul.txt /Users/okan/.claude/cron/k257-kanit4/08a-sonra-kabul.txt
```
→ `/Users/okan/.claude/cron/k257-kanit4/09a-fark-kabul.txt`

```
diff /Users/okan/.claude/cron/k257-kanit4/02b-taban-mutasyon.txt /Users/okan/.claude/cron/k257-kanit4/08b-sonra-mutasyon.txt
```
→ `/Users/okan/.claude/cron/k257-kanit4/09b-fark-mutasyon.txt`

```
diff /Users/okan/.claude/cron/k257-kanit4/02c-taban-tetik.txt /Users/okan/.claude/cron/k257-kanit4/08c-sonra-tetik.txt
```
→ `/Users/okan/.claude/cron/k257-kanit4/09c-fark-tetik.txt`

```
diff /Users/okan/.claude/cron/k257-kanit4/02d-taban-durustluk.txt /Users/okan/.claude/cron/k257-kanit4/08d-sonra-durustluk.txt
```
→ `/Users/okan/.claude/cron/k257-kanit4/09d-fark-durustluk.txt`

```
diff /Users/okan/.claude/cron/k257-kanit4/02e-taban-b8.txt /Users/okan/.claude/cron/k257-kanit4/08e-sonra-b8.txt
```
→ `/Users/okan/.claude/cron/k257-kanit4/09e-fark-b8.txt`

```
diff /Users/okan/.claude/cron/k257-kanit4/02f-taban-b7.txt /Users/okan/.claude/cron/k257-kanit4/08f-sonra-b7.txt
```
→ `/Users/okan/.claude/cron/k257-kanit4/09f-fark-b7.txt`

```
diff /Users/okan/.claude/cron/k257-kanit4/02g-taban-b5.txt /Users/okan/.claude/cron/k257-kanit4/08g-sonra-b5.txt
```
→ `/Users/okan/.claude/cron/k257-kanit4/09g-fark-b5.txt`

```
diff /Users/okan/.claude/cron/k257-kanit4/02h-taban-b6.txt /Users/okan/.claude/cron/k257-kanit4/08h-sonra-b6.txt
```
→ `/Users/okan/.claude/cron/k257-kanit4/09h-fark-b6.txt`

```
diff /Users/okan/.claude/cron/k257-kanit4/02i-taban-b4.txt /Users/okan/.claude/cron/k257-kanit4/08i-sonra-b4.txt
```
→ `/Users/okan/.claude/cron/k257-kanit4/09i-fark-b4.txt`

## ADIM 10 — canlı zincir + vaka 39 tek satır ölçümü

```
grep -n "TUR_MOTOR_ZINCIRI" /Users/okan/.claude/cron/nobet-kapi.py
```
→ `/Users/okan/.claude/cron/k257-kanit4/10a-zincir.txt`

```
grep -n "39 nobet zincir" /Users/okan/.claude/cron/k257-kanit4/08a-sonra-kabul.txt
```
→ `/Users/okan/.claude/cron/k257-kanit4/10b-vaka39.txt`

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
KANIT_DIZINI=/Users/okan/.claude/cron/k257-kanit4
```
