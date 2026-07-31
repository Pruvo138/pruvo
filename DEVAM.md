# DEVAM (KraL) — 31 Tem 2026

Onceki ayrintili kayitlar DEVAM-ARSIV.md'de (git disi, lossless).

## 🔴 HESAP TASINMASI
- Envanter + yedek raporu kalici yerde ve Drive kopyalariyla sha256 esit dogrulandi.
  Envanter 117 kalem, 10 asamali tasinma gunu sirasi; Okan'dan elle gereken 19.
- Yedek 2645 dosya / 745824642 bayt; eksik 0, boyut farki 0.
- Yeni kurulumda yerel otomasyon ve yol bagimliliklari geri yukleme rehberine gore
  kurulup kendini-test ile dogrulanmali.
- Diger 4 mimara tasinma talimati Okan tarafindan iletildi.
- Tasinma sonrasina birakilan temizlik ve yenileme isi var; ayrinti DEVAM-ARSIV.md'de.

## 🔴 YARIM IS — FIZIKSEL URUN HATTI
- Verilen kararlar, olculen durum, kapanmamis kusurlar ve siradaki adimlar
  DEVAM-ARSIV.md'de. Devralan oradan devam etsin.
- Kod acilmadan once cayma hakki ayrimi ile ticari sozlesme/sartlar Okan kapisinda.
  Ardindan sema, katalog senkronu ve Ege entegrasyonu tamamlanacak.

## KUYRUKTA (isci verilmedi)
- Metin temizligi plani kardes mimara devredildi.
- Denetim kapisinin rapor kolunda 8 `auto_sil` ve 6 eskalasyon adayi var; bunlar
  urun verisi duzleminde.
- Parite korpusu uc ve uzeri kelimeli sorgulara yapisal olarak KOR; korpus uretimi
  gozden gecirilmeli.
- Arama maliyet kapisi su an bloklamayan seritte; Serit A'ya tasima karari acik.
- Vida ailesi icin PUL-only karari verildi; teslim kardes mimarda.

## KARARLAR
- 200 TL taban tum urunlerde gecerli; parametrik sari seri haric.
- Ustu cizili fiyat parametrik sari seride kapali; konfigur urunler kapsam disi.
- Edge kartlarinda gosterim kismi fakat fail-closed; tam kapsam kardes mimarin duzlemi.
- JSON-LD'ye `priceSpecification` eklenmedi.
- Bayat UPSERT bloklanir; yayinlanan konfigur paritesi bloklayici seritte olculur.
- DEVAM.md public ve git takibinde; hassas ayrinti yalniz DEVAM-ARSIV.md'ye yazilir.

## OTURUM KAPANISI — KAPANDI
- Capa kalkani fail-closed: `7ef7427d`.
- Yedek imzasi tek plandan turetildi: `cdadc477`.
- Nobetci desenine kelime siniri eklendi: `cbe6c2a6`.
- Zamanlanmis is nabiz alarmi eklendi: `0db2aafb`.
- Taban fiyat kapisi tum kataloga genislendi: `26bf2777`.
- Arama maliyet kapisi ve onarimi: `2a08ebe7`.
- Sema ikizi tek kaynaktan turetildi: `0df44170`.
- Okan karari uygulandi: parametrik sari seri haric tum urunlerde taban 200 TL.
  1761 kayit 200 TL'ye cekildi (`4a9e2d89`); yazim sonrasi taban alti 0.
  D1 sayi ve hash ekseninde teyitli.
- Canli olay: site aramasinda cok kelimeli sorgular hata veriyordu. Olculen
  basarisizlik 30 istekte 5, yani yuzde 16,7. Kok neden sorgu planinin cevrilmesiydi;
  onarim tek kelimelik ve semantik degismiyor. Canli olcum 13275 milisaniyeden
  3,6 milisaniyeye indi. Duzeltme kardes depoda ve Okan karari geregi kardes mimar
  uygulayacak; KraL tarafinda yalnizca kapi eklendi.
- Yayin suresi medyani 1296 saniye, MAD 115 saniye, 7 kosum.
- Kaynak tarayan bayrak 8 dosya goruyor: 6'si izlenen, 2'si uretilen.
- Temizlik: worktree 5'ten 2'ye, yerel dal 16'dan 8'e indi. Kaldirilan
  worktree'lerin commit'siz isi yama olarak raporlar dizininde.

## POSTA KUTUSU ARSIVLEYICISI — ALINDI + TETIGE BAGLANDI
- Dal main'e alindi: `364095f6` (ileri-sarma, taban `e84b2a65`); 4 dosya, 1153 satir eklendi,
  silinen 0. Kabul testi bagimsiz kosuldu: 14 vaka / 85 iddia / 0 kirmizi.
- Cift yonlu mutasyon kopyada 3/3: kayipsizlik dogrulamasi oldurulunce 16 iddia dustu,
  kilit oldurulunce 4 iddia dustu, ilgisiz degisiklik yesil kaldi; canli dosya imzasi degismedi.
- Kapilar dalin agacinda: CI kapsami 143 kesif / 107 kosulan / 36 muaf; kapi envanteri 7/7;
  is akisi serit beyani 39; kisisel veri nobetcisi yesil. Sizinti taramasi 1153 eklenen
  satirda 10 desen, 0 vurus.
- MIMAR KARARI uygulandi: arac hicbir yerden cagrilmiyordu, izlenen pre-push kanca
  sablonuna jetonsuz ve fail-open baglandi (`fcda5576`). Arac patlasa da kilit baskasinda
  olsa da push durmaz; yalnizca anlamli satirlar gorunur.
- Tetik ICRAYLA kanitlandi: bos depoda gercek push araci atesledi; kanca kaldirilinca ayni
  iz uretilmedi. Iki vaka kabul testine kalici eklendi (toplam 32 kontrol, 0 kirmizi);
  mutasyonda cagri silinince 3 iddia dustu, ilgisiz degisiklikte yesil.
- Gercek kutuya YAZILMADI: yalniz kuru kosum; 290 satir, tavan 300, tasinacak blok 0 —
  push oncesi ve sonrasi dosya imzasi ayni.
- Olcum tuzagi: senkron teyidi ana agacta bir ara tum kayitlari bayat gosterdi. Sebep
  baska bir oturumun commit'siz hash degisikligiydi; ayni teyit temiz agacta 0 uyusmazlik
  verdi. Kirli agacta alinan senkron olcumu HUKUM DEGILDIR.

## TABAN (yeniden olc, ezberleme)
- Katalog: taban alti 0; D1 sayi ve hash ekseninde uyumlu.
- Yayin suresi: medyan 1296 saniye, MAD 115 saniye, 7 kosum.
- Calisma alani: 2 worktree, 8 yerel dal.
