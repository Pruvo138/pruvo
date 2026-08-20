# SPEC — K214: I3 / I5 hedef-kol atfının ONARIMI doğrulansın

> 🔴🔴 **KAPSAM KİLİDİ (ihlal = tur BAŞARISIZ):**
> - **HİÇBİR `git` KOMUTU KOŞMA** (`rebase`/`merge`/`checkout`/`commit`/`reset`/`stash` YASAK).
> - **HİÇBİR izlenen dosyayı SİLME/TAŞIMA.** `tools/parti-kapisi.py`'ye DOKUNMA (K230).
> - Kod DEĞİŞTİRME. **SALT ÖLÇÜM.** Kırmızı çıkarsa ONARMA, sayıyı RAPOR ET.

## Ölçülen kusur ve onarım (bağlam)
Önceki tur `mimar-kapi-mutasyon-test.py` **rc=1** verdi: **I3** ve **I5** mutantları
`OLCULEMEDI`ye düştü — beklenen kırmızı vaka sayısı I3'te `5` iken **7**, I5'te `8` iken **12** geldi.
Sebep: K214 turunda `mimar-kilit-test.py`'ye eklenen **920–924** vakaları claude kolunu ölçüyor;
I3 o kolu öldürdüğü için 921/922 de, I5 kuralı komple kapattığı için 921/922/923/924 de
**haklı olarak** kızarıyor. Yani kapsam ARTTI, beklenen küme BAYAT kaldı
([[batarya-kapsam-tabani-sayiyla-civilenir]] sınıfı).

**Onarım (uygulandı):** beklenen kümeler gerçeğe çekildi —
- I3: `{613,614,615,707,712}` → `{613,614,615,707,712,921,922}`, sayı `5` → **7**
- I5: `{600,601,602,603,604,631,708,709}` → `+{921,922,923,924}`, sayı `8` → **12**

## A — MUTASYON BATARYASI
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zen-varahamihira-287215/tools/mimar-kapi-mutasyon-test.py
```
YAZ: **rc** · `SONUC:` satırı birebir.
🔴 **I3 ve I5 satırlarını AYRI AYRI yaz** ve her biri için **TEK KOL** mu yoksa `OLCULEMEDI` mi
olduğunu belirt. Beklenen: rc=0, ikisi de **TEK KOL**.
Başka mutant `OLCULEMEDI`ye düştüyse ADIYLA yaz.

## B — 🔴 I3 ↔ I5 AYRIŞMASI HÂLÂ DURUYOR MU (asıl risk)
Onarım iki mutantı aynı ize eritmiş olabilir — o zaman biri diğerini gölgeler.
Çıktıdan **I3'ün ve I5'in kırmızı vaka KÜMELERİNİ** yaz ve şunu açıkça belirt:
**I3'ün kümesi I5'in kümesinden FARKLI mı?** (I3'te 923/924 YEŞİL kalmalı; I5'te kızarmalı.)
Aynıysa `AYRISMA KAYBOLDU` yaz — bu onarımın kabul edilemez yan etkisidir.

## C — MİMAR KİLİT BATARYASI (yan eksen bozulmadı mı)
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zen-varahamihira-287215/tools/mimar-kilit-test.py
```
YAZ: `TOPLAM VAKA:` + `SONUC:` + **rc**. Beklenen: **299/299**, rc=0.

## RAPOR
Projenin mimar raporu için mandat ettiği kanonik ada **EK BÖLÜM** olarak ekle — var olanı EZME.
Her satırın arkasında komut + rc. Kırmızıyı GİZLEME. Geçici dosya bırakma.
