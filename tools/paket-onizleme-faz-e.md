# PAKET — Sarı Seri 3D Önizleme FAZ E: kalan 13 ailenin eşlem düzeltme turu
## (Hedef Okan kararı: önizleme TÜM sarı ailelerde — Faz D ölçümü hiçbirini geçirmedi)

**Kat:** Claude Mühendis (yüksek efor). Gizli eşlem + hacim semantiği = sessiz hata sınıfı.
**Çalışma şekli:** worktree; merge = yayın kapısı (mimar). `urunler.json`'a dokunma.
**Önce oku:** DEVAM.md Faz D blokları (aile aile ölçülmüş sapma tablosu), `onizleme/test/
eslem-olcum.py`, `tools/paket-onizleme-faz-d.md` (D kalemi kuralları aynen geçerli).

## Durum (Faz D ölçümünden, aile başına 9 set)
Kıl payı kalanlar: yay (grid %1.59 ama kare boy=62 %5.22 / testere boy=45 %4.10),
cetvel düz %1.0 (üçgen/L-gönye motorda YOK), jeton %2.4 (kabartma stili %5.7),
rampa düz %0 / tırtıklı %1 (basamaklı %13 — farklı semantik).
Büyük sapanlar: huni %11.4 (iç geometri; dış zarf birebir), rulman %20.9 (+3 boş derleme),
kayış %22.2, kasnak %45.4, vida %91 (+fiyat formülü çapa duyarsız — AYRI paket),
petek %99 (kabartma modu kolon dikiyor), kaşe %107 (taban metin bbox'undan; kare/yuvarlak
YOK), pervane %179 (burun konisi/dış ring modelleri farklı; yalın %2), ızgara %238
(panjur sabit 8 satır, doldurma yok).

## Kurallar
1. **Kapı değişmedi:** aile ancak 4d-benzeri ölçümde (9+ set, ≤%3, uç noktalar dahil)
   geçerse `ONIZLEME_AILELER`'e girer. Uydurma/ortalamayla geçirme YOK — Faz D'deki yay
   dersi: grid ortalaması %1.59'ken uç nokta %5.22'ydi; uç noktalar da sınır içinde olmalı.
2. **Sapmanın kökü İKİ sınıftan biri:** (a) eşlem hatası/eksiği → gizli eşlem düzeltilir
   (`eslem-ozel.json`, kanonik R2 paketi yeni sürümle); (b) hacim.js formülü üretim
   motorundan farklı GEOMETRİ varsayıyor → hacim.js üretim motoruna kalibre edilir; bu
   FİYATI değiştirir → aile başına fiyat etkisi %'siyle MİMARA listelenir, mimar Okan'a
   taşır; ONAY GELMEDEN o ailenin hacim.js değişikliği merge edilmez (o-ring %6 deseni).
3. **Motorda karşılığı olmayan varyant** (cetvel üçgen/L-gönye, kaşe kare/yuvarlak,
   pervane burun konisi/dış ring, ızgara doldurma vb.): uydurulmaz. Seçenek listesiyle
   mimara raporla — konfigüratörden varyantı kaldırmak/`uretilemez` işaretlemek ayrı
   karar (Okan). O varyant hariç kalan küme ≤%3'se aile listelenebilir (varyant kısıtı
   şema kapısına yazılır, müşteri seçemez).
4. Boş derleme (rulman +3) = hata: kök nedeni bul (parametre kombinasyonu üretilemezse
   422 sınıfına düşmeli, sessiz boş STL ASLA).
5. Sır hijyeni Faz D paketiyle aynı (tedarikçi adı hiçbir public dosyada/commitde).

## Kabul (mimar koşacak)
1. `python3 onizleme/test/eslem-olcum.py` — geçen HER yeni aile için 9+ set ≤%3 (uç
   noktalar raporda); geçemeyenler ölçülen sapma + kök neden sınıfı (a/b/c) ile tablo.
2. `node onizleme/test/kabul.js` — kapsam yeni listeye genişlemiş, tümü yeşil.
3. `node jenerator/test/fiyat-test.js` + `node jenerator/test/kalibrasyon-senkron.js` +
   `node shop/test/kabul.js` yeşil (hacim.js'e dokunulan her ailede fiyat regresyonu).
4. Parite 2'li yeşil. 5. Deploy sonrası kapi1 nihai listeyle p95 ≤ 10 sn.
6. Fiyat etkisi listesi (kural 2b) — boşsa "hacim.js'e dokunulmadı" beyanı.

## Rapor
Aile × (önceki sapma → yeni sapma → listeye girdi mi → fiyat etkisi → mimar kararı
bekleyen varyantlar) tablosu + DEVAM.md. Yargı mimara (KraL), Okan'a değil.
