# PAKET — Sarı seri taban fiyatların yerleştirilmesi + zemin formülü
## (Okan KESİN kararı, 16 Tem gece sonu — araştırma: tools/arastirma-sari-fiyat.md)

**Kat:** Claude Mühendis (fiyat semantiği — Codex'e verilmez).
**ÖN KOŞUL — BAŞLAMADAN DOĞRULA:** Faz D dalı (`claude/modest-tesla-895a82`) main'e
merge edilmiş olmalı (aynı dosyalar: jenerator/urunler, hacim.js, secenekler.js —
tek yazar). Merge edilmemişse DUR, mimara sor. Worktree'de çalış; urunler.json'a dokunma.

## 1) ZEMİN FORMÜLÜ (Okan kuralı + mimar kademe kararı: sürekli oran)
Fiyat çarpanı asla 1'in altına inmez; büyük ölçüde hacimle sürekli artar:
`fiyat = tabanFiyatTL × max(1, hacim/tabanHacim) × filamentKatsayı × renkFaktör`
Basamak YOK (araştırma gerekçesi: eşik uçurumu güven kırar + eşik-altı oynamaya iter;
rakip platformların tümü sürekli). Kuruş korunur, yuvarlama yok (mevcut kural).
Tek kaynak neredeyse (secenekler.js/hacim.js fiyat hesabı) orada değiştir; kopya yok.

## 2) TABAN FİYATLAR (Okan KESİN — araştırma önerisi +1 TL, minimum 100 TL)
`jenerator/urunler/<id>.json` → `tabanFiyatTL`:
| Aile | TL |
|---|---|
| kisiye-ozel-jeton-cip-madalyon | 150 |
| olcuye-ozel-baglanti-konektor | 170 |
| olcuye-ozel-cetvel | 130 |
| olcuye-ozel-damga-kase | 350 |
| olcuye-ozel-huni | 170 |
| olcuye-ozel-izgara-menfez-kapak | 250 |
| olcuye-ozel-montaj-braketi | 150 |
| olcuye-ozel-oring-conta | 100 |
| olcuye-ozel-pervane-fan-cark | 300 |
| olcuye-ozel-petek-delikli-panel | 200 |
| olcuye-ozel-profil-beam | 150 |
| olcuye-ozel-ramp-sim-takoz | 160 |
| olcuye-ozel-rulman | 200 |
| olcuye-ozel-triger-kasnagi | 180 |
| olcuye-ozel-triger-kayisi | 150 |
| olcuye-ozel-vida-civata-somun-pul | **GİRİLMEZ (null kalır)** |
| olcuye-ozel-yay-dalga-flexure | 130 |
| ozel-disli-kramayer-uretimi | 300 |

**VİDA İSTİSNASI:** hacim hesabı çapa duyarsız (M5'e çakılı — Faz D ölçümü). Fiyat
girilirse M12, M5 fiyatına satılır. tabanFiyatTL null KALIR → sayfada "Ölçüye özel
fiyat" sürer. Düzeltme AYRI iş (bu pakete alma); düzelince girilecek değer: 100 TL.
`tools/taban-fiyat-tablosu.md` bu tabloyla doldurulur (vida satırına istisna notu).

## 3) GÖSTERİM
Taban fiyatı dolu ailede sarı sayfa "Ölçüye özel fiyat" yerine fiyat gösterir
("X TL'den başlayan" kalıbı — normal sayfayla aynı bileşen, F kalemi düzeni). KDV
dahil satış fiyatıdır. PARAMETRİK_ODEME_ACIK bu pakette AÇILMAZ (ayrı mimar adımı).

## Kabul testleri (mimar koşacak)
1. Fiyat testi (jenerator fiyat-test genişletmesi): (a) ZEMİN — varsayılandan KÜÇÜK
   her ölçüde fiyat = taban × filament × renk (asla altına inmez; en az 3 ailede
   küçültülmüş setlerle); (b) BÜYÜME — hacim artınca fiyat monoton artar; (c) 17 aile
   dolu + vida null; (d) kuruş korunur. Zemin testinin önce ESKİ formülde KIRMIZI
   yandığı gösterilir.
2. `node jenerator/test/kalibrasyon-senkron.js` + `node onizleme/test/kabul.js` +
   `node shop/test/kabul.js` yeşil (regresyon).
3. build sonrası bir sarı sayfada fiyat görünümü (ekran görüntüsü) + vida sayfasında
   "Ölçüye özel fiyat" sürdüğü kanıtı.
4. Parite: `node tools/parite-test.js` + `node tools/parite-ege.js` yeşil.

## Rapor
Kanıtlar + DEVAM.md güncellemesi; yargı soruları mimara (KraL). Commit'ler dalda,
merge mimar kabulünden sonra.
