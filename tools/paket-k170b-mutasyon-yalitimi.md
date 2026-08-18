# PAKET K170-B — mutasyon bataryası YALITILMAMIŞ, yeniden koşulacak

**Mimar:** KraL · **Tarih:** 18 Ağu 2026 · **Dal:** `kral/k170-capraz-yargi` (`be67db2b` üstüne)

## NE DOĞRU (mimar bağımsız doğruladı, tekrar ölçülmeyecek)
- Yargı BİREBİR indi: allow **67** anahtar (kendi `grep -c`'imle sayıldı), BEKLER **7**
  (6 mevcut + `Volvo|mk1`), deny **+7** satır.
- Kapsam temiz: tek dosya `tools/arama.py`, +62/-4; `urunler.json` ve gizli kaynak düzlemi
  DOKUNULMADI (`git diff` boş).
- `arama-test.py` / `testler.py` gerçekten YOK — `UYGULANAMADI` beyanı DÜRÜST (doğruladım).
- K11 tablosu 7 sayfa için tek tek verilmiş, `kaybolan=0`.

## 🔴 NE KUSURLU — M1 ve M2 HİÇBİR ŞEY KANITLAMIYOR

Ham çıktı bunu kendisi söylüyor:

```
M1 (Vespa|gts silindi):  YARGISIZ=['Vespa|gts'] · imza=a9b53e95… beklenen=d3f5c345… sayı=66 beklenen=67
M2 (Piaggio|gts çelişki): çelişki=['Piaggio|gts'] · imza=7df226fc… beklenen=d3f5c345… sayı=68 beklenen=67
```

Her iki mutantta **SAYI ve İMZA eksenleri de aynı anda kırmızı yanıyor.** Yani YARGISIZ kolu
ya da ÇELİŞKİ kolu **ÖLÜ olsaydı bile** mutant yine kırmızı verirdi. Mutant, nişanlandığı kolu
DEĞİL, yanındaki imza kolunu ölçmüş oluyor
([[mutasyon-capasi-olu-kola-nisanlanir]] · [[kirmizi-adim-sonrakini-maskeler]]).
Bu, "3/3 mutant kırmızı" satırını kanıt olmaktan çıkarır.

## İCRA — M1 ve M2 YALITILMIŞ olarak yeniden koşulacak

**M1′ (yargısız kolu YALNIZ):** `Vespa|gts` satırını sil **VE** `ROZET_CAPRAZ_IZINLI_SAYISI`yı
**66** yap **VE** `ROZET_CAPRAZ_IZINLI_IMZA`yı mutasyonlu sözlük için **yeniden HESAPLA**
(`rozet_capraz_imzasi()` çağrısı). Böylece sayı ve imza eksenleri YEŞİL kalır; kapı kırmızı
yanıyorsa bunu **yalnız** YARGISIZ kolu yapmıştır.
Beklenen: `rc=1` ve raporlanan TEK ihlal `YARGISIZ=['Vespa|gts']`.

**M2′ (çelişki kolu YALNIZ):** `Piaggio|gts` anahtarını allow'a da ekle (deny'de kalsın)
**VE** `SAYISI`yı **68** yap **VE** `IMZA`yı yeniden HESAPLA.
Beklenen: `rc=1` ve raporlanan TEK ihlal `deny/allow çelişkisi=['Piaggio|gts']`.

**M3** olduğu gibi geçerli, TEKRARLANMAZ.

🔴 **KABUL ÇITASI:** M1′ ve M2′ çıktısında imza/sayı satırları **beklenen=gerçek** olmalı.
Hâlâ ikinci bir eksen yanıyorsa mutant YALITILMAMIŞTIR — `YALITILAMADI` yaz, "geçti" YAZMA.
🔴 Mutant kırmızı YANMAZSA bu bir başarısızlık DEĞİL, **BULGU**dur: ilgili kol ölüdür,
aynen raporla — yeşile boyama YOK.

## İKİNCİ İŞ (aynı turda, küçük)
`("Alfa Romeo", "916")` deny gerekçesindeki `gercek sayfa /marka/ducati/916/` ifadesi YANILTICI:
Ducati sayfası Alfa parçasının adresi değildir. Metni şuna çevir: *"Alfa Romeo `916` rozetiyle
araç SATMADI (tip/sasi kodu); urunler Alfa Romeo agacinda durur. `916` model sayfasi
Ducati'nindir."* Sadece YORUM/gerekçe metni değişir — **anahtar DEĞİŞMEZ**, imza da değişmez;
imzanın değişmediğini ölçüp raporla.

## RAPOR
Aynı dalda, projenin kanonik mühendis raporu adıyla; M1′/M2′ ham çıktıları BİREBİR.
Rapor tablosuna giren her satırın ham çıktıda karşılığı olacak; özet ham dosyayla
desteklenmiyorsa tabloya GİRMEZ. İş bitince temizlik kanıtı.
