# SPEC — B7 kurulum + kabul koşumu (İŞÇİ TURU, mekanik)

> **Bu tur KOD YAZMAZ.** Bütün kod zaten yazıldı. Senin işin: **komutları sırayla
> koşturmak ve HAM çıktıyı dosyaya dökmek.** Yorum yapma, özet uydurma, tablo
> yazma. Sayıyı mimar dosyadan okuyacak.
>
> 🔴 Hiçbir adımda dosya İÇERİĞİ düzenleme. `b7-kur.py` dışında hiçbir şey
> `~/.claude/cron` altına yazmayacak.
> 🔴 Bir adım kırmızıysa **DURMA** — sonraki adımları da koş, hepsinin çıktısı lazım.
> 🔴 `git commit` / `git push` YOK.

Çıktı dizini (yoksa oluştur): `/Users/okan/.claude/cron/b7-kanit`

## ADIM 1 — sözdizimi (yama ÖNCESİ)

```
python3 -m py_compile /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b7-kur.py /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/nobet-tur-izolasyon-test.py
```
Çıktıyı (rc dahil) `/Users/okan/.claude/cron/b7-kanit/01-pycompile.txt` dosyasına yaz.
Satır sonuna `RC=<rc>` ekle.

## ADIM 2 — TABAN ölçümü (yama ÖNCESİ, ZORUNLU)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
Tüm çıktıyı `/Users/okan/.claude/cron/b7-kanit/02-taban-nobet-kabul.txt` dosyasına yaz,
sonuna `RC=<rc>` ekle. **Bu tabanın kırmızı olması senin sorunun değil** — sadece kaydet.

## ADIM 3 — kurulum ÖNCESİ yama envanteri

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b7-kur.py
```
→ `/Users/okan/.claude/cron/b7-kanit/03-once.txt` (+ `RC=<rc>`)

## ADIM 4 — yamayı uygula

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/hopeful-cerf-0c64fa/tools/n4b/b7-kur.py --uygula
```
→ `/Users/okan/.claude/cron/b7-kanit/04-uygula.txt` (+ `RC=<rc>`)

## ADIM 5 — yama SONRASI sözdizimi

```
python3 -m py_compile /Users/okan/.claude/cron/nobet-kapi.py
```
```
zsh -n /Users/okan/.claude/cron/isci.sh
```
İkisinin çıktısını ve rc'sini `/Users/okan/.claude/cron/b7-kanit/05-sozdizimi.txt`
dosyasına yaz (`PYCOMPILE_RC=<rc>` ve `ZSH_N_RC=<rc>` satırlarıyla).

## ADIM 6 — B7 KABUL BATARYASI (asıl ölçüm)

```
python3 /Users/okan/.claude/cron/nobet-tur-izolasyon-test.py
```
→ `/Users/okan/.claude/cron/b7-kanit/06-b7-kabul.txt` (+ `RC=<rc>`)
Bu adım ~1-3 dakika sürer (gerçek `isci.sh` turları koşar). **Bekle, kesme.**

## ADIM 7 — REGRESYON (yama SONRASI, ADIM 2 ile aynı komut)

```
python3 /Users/okan/.claude/cron/nobet-kabul-test.py
```
→ `/Users/okan/.claude/cron/b7-kanit/07-sonra-nobet-kabul.txt` (+ `RC=<rc>`)

## ADIM 8 — 🚫 BU TURDA KOŞMA

`testler.py` tam koşumu AYRI bir tura bırakıldı (paket başına 600 sn tavan, tur
tavanını yer). Bu turda yalnızca kaydı doğrula:

```
grep -n "nobet-tur-izolasyon-test.py" /Users/okan/.claude/cron/testler.py
```
→ `/Users/okan/.claude/cron/b7-kanit/08-cagri-yeri.txt` (+ `RC=<rc>`)

## ADIM 9 — artık taraması

```
ls -la /Users/okan/.claude/cron/isci-tur-cikti
```
```
ls /Users/okan/.claude/cron | grep -c "^profil-kimi-ev-izo"
```
İkisinin çıktısını `/Users/okan/.claude/cron/b7-kanit/09-artik.txt` dosyasına yaz.

## SON MESAJIN

Yalnızca şu biçimde, TEK blok, başka hiçbir şey yazma:

```
ADIM1_RC=<n>
ADIM2_RC=<n>
ADIM3_RC=<n>
ADIM4_RC=<n>
ADIM5_PYCOMPILE_RC=<n> ADIM5_ZSH_RC=<n>
ADIM6_RC=<n>
ADIM7_RC=<n>
ADIM8_RC=<n>
KANIT_DIZINI=/Users/okan/.claude/cron/b7-kanit
```

🔴 `✅ İŞ BİTTİ` gibi bir jeton YAZMA. Hüküm mimarındır.
