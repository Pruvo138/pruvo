# SPEC — K214 MERGE KAPISI ÖLÇÜMLERİ (dört komut, SAYIYLA)

> 🔴🔴 **KAPSAM KİLİDİ (ihlal = tur BAŞARISIZ):**
> - **HİÇBİR `git` KOMUTU KOŞMA** — `rebase`/`merge`/`checkout`/`commit`/`reset`/`stash` **YASAK.**
>   (Bir önceki tur bu ağaçta spec'te hiç geçmeyen 56 commit'lik interaktif rebase başlattı.)
> - **HİÇBİR izlenen dosyayı SİLME/TAŞIMA/DEĞİŞTİRME.** Özellikle `tools/parti-kapisi.py`'ye
>   DOKUNMA — ağaçtan düşerse PreToolUse kancası tüm oturumu kilitler (K230).
> - Bu tur **SALT ÖLÇÜM**dür. Kod düzeltme YOK. Kırmızı çıkarsa **ONARMA, RAPOR ET.**

Ağaç: `/Users/okan/dev/pruvo/.claude/worktrees/zen-varahamihira-287215`
(taban güncel `origin/main` = `50f43744`, uç `09d653ac`)

## ① Mimar kilit bataryası
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zen-varahamihira-287215/tools/mimar-kilit-test.py
```
YAZ: `TOPLAM VAKA:` satırı (birebir) · `SONUC:` satırı (birebir) · **rc**.
Ayrıca **920/921/922/923/924** vakalarının HER BİRİNİN çıktı satırını ayrı ayrı yaz.

## ② 🔴 Kişisel veri nöbetçisi (MERGE ÖN-ŞARTI — gözle değil MAKİNEYLE)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zen-varahamihira-287215/tools/kisisel-veri-test.py
```
YAZ: **rc** · **kaç iddia YEŞİL** (sayı) · varsa isabet/ihlal satırlarını AYNEN.
Bağlam: bu nöbetçi geçen tur yayını 3 commit kapattı; bu yüzden merge ön-şartı.

## ③ Motor tek-kaynak nöbetçisi — öz-test
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zen-varahamihira-287215/tools/motor-tek-kaynak-kapisi.py --kendini-test
```
YAZ: **rc** · vaka/mutant sayıları (`MUTANT=…` benzeri satırları birebir) · `SONUC:` satırı.

## ④ Mimar kapı mutasyon bataryası — 🔴 K182 ATFI ŞART
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zen-varahamihira-287215/tools/mimar-kapi-mutasyon-test.py
```
YAZ: **rc** · sonuç satırı · **her mutantın HEDEF KOLU öldürüp öldürmediği**.
🔴 Her mutant için açıkça belirt: **TEK KOL** mu (yalnız hedef kol kırmızı) yoksa
**`OLCULEMEDI`** mi (birden çok kol düştü / atıf kurulamadı). "Mutant öldü" TEK BAŞINA
kanıt DEĞİLDİR — hedef kol atfı olmadan o mutant ÖLÇÜLMEMİŞ sayılır (K182).

## RAPOR
Projenin mimar raporu için mandat ettiği kanonik ada (CLAUDE.md İLETİŞİM PROTOKOLÜ) **EK BÖLÜM**
olarak ekle — var olanı EZME. Her satırın arkasında **komut + rc** olsun.
🔴 **KIRMIZI ÇIKARSA GİZLEME, UYDURMA, ONARMAYA ÇALIŞMA** — sayıyı olduğu gibi yaz.
Ölçemediğine `ÖLÇÜLEMEDİ + sebep`. Geçici dosya bırakma.
