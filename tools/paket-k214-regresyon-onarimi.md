# SPEC — K214: yetkili-çıkış REGRESYONUNUN onarımı DOĞRULANSIN

> 🔴🔴 **KAPSAM KİLİDİ (ihlal = tur BAŞARISIZ):**
> - **HİÇBİR `git` KOMUTU KOŞMA** (`rebase`/`merge`/`checkout`/`commit`/`reset` YASAK).
> - **HİÇBİR izlenen dosyayı SİLME/TAŞIMA.** Özellikle `tools/parti-kapisi.py`'ye DOKUNMA
>   (ağaçtan düşerse PreToolUse kancası tüm oturumu kilitler — K230).
> - Repo kodunu **DEĞİŞTİRME**. Mutant denemeleri YALNIZ `/tmp` kopya ağacında.

## Onarım (mimar hükmü, uygulandı)
`tools/mimar-icra-kapisi.py`: emekli kolu artık claude'u **açıkça dışarıda bırakıyor**
```
if motor != "claude" and emekli_motor_mu(motor):
```
Gerekçe: `claude`'un dağıtımı KENDİ koluna aittir (sert blok + `PRUVO_CLAUDE_ISCI_IZNI=OKAN`
+ beyan şartı); emekli KATI listesi onu yönetmez. Onarımdan önce `claude` emekli kümesine
girseydi Okan'ın yetkili çıkışı SESSİZCE kapanıyordu (Ⓑ allow ↔ Ⓓ deny).

`tools/mimar-kilit-test.py` beklentileri buna göre güncellendi: **922 → `SERT_BLOK`**
(mutant artık ETKİSİZ), **924 → `ALLOW`** (yetkili çıkış açık kalır). 920/921/923 aynı.

## A — BATARYA
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zen-varahamihira-287215/tools/mimar-kilit-test.py
```
YAZ: `TOPLAM VAKA:` satırı (birebir, **299** beklenir) · `SONUC:` satırı · **rc** ·
**920/921/922/923/924'ün HER BİRİNİN** çıktı satırı ayrı ayrı. Beklenen: hepsi `OK`, rc=0.

## B — 🔴 ÇÜRÜTME (ASIL İŞ — bu olmadan A tautolojidir)
Onarım gerçekten ÖLÇÜLÜYOR mu? `/tmp` kopya ağacında **onarımı GERİ AL**:
`if motor != "claude" and emekli_motor_mu(motor):` → `if emekli_motor_mu(motor):`
Sonra bataryayı O KOPYADAN koştur.

**BEKLENEN: 922 ve 924 KIRMIZI yanmalı.**
- 922 `SERT_BLOK` yerine `EMEKLI` dönmeli
- 924 `ALLOW` yerine `EMEKLI` (deny) dönmeli

🔴 İkisi de KIRMIZI yanmıyorsa **onarım ölçülmüyor demektir** (vakalar onarımla birlikte
düşen tautoloji) — o zaman `TAUTOLOJI: EVET` yaz ve hangi vakanın sustuğunu belirt.
Sustuysa "yeşil" YAZMA. ([[ad-iki-rolde-mutanti-golgeler]] · K182)

YAZ: geri-alınmış kopyada 922 ve 924'ün çıktı satırları + rc.

## C — YAN EKSEN
B'deki geri-alma **YALNIZ** 922/924'ü kırmızı yakmalı; 920/921/923 ve diğer vakalar
DEĞİŞMEMELİ. Değişen başka vaka varsa ADIYLA yaz (hedef kol atfı).

## RAPOR
Projenin mimar raporu için mandat ettiği kanonik ada (CLAUDE.md İLETİŞİM PROTOKOLÜ) **EK BÖLÜM**
olarak ekle — var olanı EZME. Her satırın arkasında komut + rc olsun.
Ölçemediğine `ÖLÇÜLEMEDİ + sebep`. Temizlik: `/tmp` kopyalarını sil, `ls` ile kanıtla.
