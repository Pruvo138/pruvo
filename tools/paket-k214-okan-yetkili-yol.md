# SPEC — K214 EKSEN (iii): `claude` EMEKLİ iken OKAN'ın YETKİLİ ÇIKIŞI kapanıyor mu?

> 🔴🔴 **KAPSAM KİLİDİ — BU TURDA YASAK OLANLAR (ihlal = tur BAŞARISIZ sayılır):**
> - **HİÇBİR `git` KOMUTU KOŞMA.** `git rebase` / `git merge` / `git checkout` / `git commit` /
>   `git reset` **KESİNLİKLE YASAK.** Önceki tur bu ağaçta izinsiz 56 commit'lik bir interaktif
>   rebase başlattı ve ağacı çakışmada bıraktı; o iş GERİ ALINDI. Bir daha olmayacak.
> - Bu worktree'deki **hiçbir izlenen dosyayı SİLME/TAŞIMA.**
> - Ölçüm YALNIZ `/tmp/k214-eksen3/` kopya ağacında koşar; iş bitince kopya SİLİNİR.
> - Yazma iznin olan TEK yer: raporun EK bölümü (aşağıda) ve gerekirse
>   `tools/mimar-kilit-test.py`'ye YENİ VAKA EKLEME (mevcut vakaları BOZMADAN).

## Bağlam (ölçüldü, tekrar ölçme)
`tools/mimar-icra-kapisi.py` kol sırası:
```
:540  if emekli_motor_mu(motor): return emekli_gerekcesi(motor)     # ÖNCE
:543  if (motor == "claude" and EV_ADI in SERT_BLOK_EVLER and
:544          os.environ.get("PRUVO_CLAUDE_ISCI_IZNI") != "OKAN"):   # SONRA
```
Önceki tur ölçtü: mutantsız red kolu **`SERT_BLOK`**, `claude` emekli kümesine sokulunca
red kolu **`EMEKLI`** oluyor (vakalar 920/921/922, `mimar-kilit-test.py` 297/297).

## ÖLÇÜLECEK TEK ŞEY (eksen iii)
Bugün `PRUVO_CLAUDE_ISCI_IZNI=OKAN` iken KraL/MaCiT'te `claude` **GEÇİYOR** (yetkili çıkış).
Soru: **`claude` EMEKLİ kümesindeyken bu yetkili çıkış hâlâ çalışıyor mu?**

Kopya ağaçta DÖRT ölçüm, her birinde **HÜKÜM (GEÇER/RED) + RED KOLU (`SERT_BLOK`/`EMEKLI`)** yaz:

| # | `claude` emekli mi | `PRUVO_CLAUDE_ISCI_IZNI` | beklenen |
|---|---|---|---|
| Ⓐ | HAYIR (bugünkü hâl) | yok | RED · kol=`SERT_BLOK` |
| Ⓑ | HAYIR (bugünkü hâl) | `OKAN` | **GEÇER** (yetkili çıkış açık) |
| Ⓒ | EVET (mutant) | yok | RED · kol=`EMEKLI` |
| Ⓓ | EVET (mutant) | **`OKAN`** | **← ASIL SORU** |

🔴 **Ⓓ RED ve kol=`EMEKLI` çıkarsa:** yetkili çıkış SESSİZCE KAPANMIŞ demektir → bu bir
**davranış regresyonudur**, raporda `REGRESYON: EVET` yaz.
🔴 **Ⓓ GEÇER çıkarsa:** yetkili çıkış korunuyor → `REGRESYON: YOK` yaz.
Ⓑ'yi ölçmeden Ⓓ'yi yorumlama — Ⓑ zaten RED ise Ⓓ'nin RED'i regresyon DEĞİLDİR (taban öyleymiş).
**Taban ölçülmeden hüküm YAZILMAZ** (bu evde ölçülmüş kural: taban kırmızıysa mutant anlamsızdır).

🔴 Kimlik ekseni SÖKÜLSÜN ve söküm DOĞRULANSIN (`kimlik_ekseni(...)` = `None`); sökemezsen
`MUAF_BAGLAM` yaz, "YEŞİL" YAZMA.

## Kalıcı kabul
Ⓑ ve Ⓓ'yi `tools/mimar-kilit-test.py`'ye **923 / 924** numaralı vaka olarak ekle (920–922'yi
BOZMADAN), sonra `python3 .../tools/mimar-kilit-test.py` koştur; rc + `SONUC:` satırını yaz.

## RAPOR
Projenin mimar raporu için mandat ettiği kanonik ada (CLAUDE.md İLETİŞİM PROTOKOLÜ) **EK BÖLÜM**
olarak ekle — var olanı EZME. Her satırın arkasında komut + rc olsun.
Ölçemediğine `ÖLÇÜLEMEDİ + sebep`. Temizlik: `/tmp/k214-eksen3` sil, silindiğini `ls` ile kanıtla.
