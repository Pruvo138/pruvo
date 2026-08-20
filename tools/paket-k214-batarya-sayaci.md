# SPEC — K214: batarya SAYACI onarımının doğrulanması (tek komut)

> 🔴🔴 **KAPSAM KİLİDİ (ihlal = tur BAŞARISIZ):**
> - **HİÇBİR `git` KOMUTU KOŞMA.** `rebase`/`merge`/`checkout`/`commit`/`reset` **YASAK.**
>   (Önceki bir tur bu ağaçta izinsiz 56 commit'lik interaktif rebase başlattı; geri alındı.)
> - **HİÇBİR dosyayı SİLME/TAŞIMA.** Özellikle `tools/parti-kapisi.py`'ye DOKUNMA —
>   o dosya ağaçtan düşerse PreToolUse kancası tüm oturumu kilitler (K230).
> - Kod DEĞİŞTİRME. Bu tur **yalnız ÖLÇÜM**dür.

## Yapılacak TEK iş
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zen-varahamihira-287215/tools/mimar-kilit-test.py
```

## Ölçülen kusur (bağlam)
`ek_vaka` K214 vaka sayısını ELLE `3` taşıyordu; 923/924 eklenince `k214_vaka_sayisi` 5 oldu
ama `ek_vaka` **3'te DONDU** → batarya 299 vaka koşarken **"297/297"** basıyordu; kapsam kaybı
oranın İÇİNDE görünmüyordu ([[batarya-kapsam-tabani-sayiyla-civilenir]]). Sayı tek yerde
tanımlanıp `ek_vaka` ondan TÜRETİLDİ; mükerrer `TOPLAM VAKA` satırı kaldırıldı.

## KABUL — sayıyla
1. `TOPLAM VAKA:` satırını **birebir** yaz. **`299` olmalı** (297 DEĞİL).
2. `TOPLAM VAKA:` satırı çıktıda **YALNIZ BİR KEZ** geçmeli (mükerrer kalktı mı) — kaç kez
   geçtiğini SAY ve yaz.
3. `SONUC:` satırını birebir yaz + **rc**. Beklenen `299/299` ve rc=0.
4. **920, 921, 922, 923, 924** vakalarının HER BİRİNİN çıktı satırını ayrı ayrı yaz
   (beşi de gerçekten koştu mu — "toplam yeşil" beşinin koştuğunun kanıtı DEĞİLDİR).

🔴 Sayı `299` çıkmazsa **UYDURMA** — gerçek sayıyı ve `SONUC:` satırını olduğu gibi yaz,
`BEKLENEN=299 GELEN=<n>` diye işaretle.

## RAPOR
Projenin mimar raporu için mandat ettiği kanonik ada (CLAUDE.md İLETİŞİM PROTOKOLÜ) **EK BÖLÜM**
olarak ekle — var olanı EZME. Ölçemediğine `ÖLÇÜLEMEDİ + sebep`.
