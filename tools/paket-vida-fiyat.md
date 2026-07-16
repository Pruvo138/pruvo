# PAKET — Vida ailesi fiyat formülü düzeltmesi (çap duyarlılığı)
## (Faz D bulgusu; Okan'ın vida taban fiyatı 100 TL hazır, formül düzelmeden GİRİLMEZ)

**Kat:** Claude Mühendis (fiyat semantiği). **Worktree'de çalış; urunler.json'a dokunma.**
**Önce oku:** DEVAM.md Faz D "D) 13 AILE OLCUMU" vida notu, `tools/paket-sari-fiyat.md`
(zemin formülü + vida istisnası), `jenerator/hacim.js` vida bölümü.

## Sorun (ölçülmüş)
`hacim.js` vida ailesinde **M ölçüsüne (çapa) duyarsız** — M5'e çakılı; somun sabit
157 mm³. Üretim motoru doğru büyütüyor. Yani taban fiyat girilseydi M12 cıvata M5
fiyatına satılırdı (hacim çarpanı hiç değişmediği için zemin de kurtarmaz).

## İş
1. hacim.js vida ailesini üretim motoruna kalibre et: cıvata/somun/pul/saplama tipleri ×
   M ölçüsü × boy × geçme boşluğu — hacim fonksiyonu gerçek parametrelerden hesaplasın.
   Referans: gerçek OpenSCAD STL hacimleri (kalibrasyon-senkron deseni: dondurulmuş
   fixture seti üret, `jenerator/test/kalibrasyon-referans-uret.py` örneği).
2. Kalibrasyon hedefi ≤%3 (uç noktalar dahil: en küçük M, en büyük M, en uzun boy).
3. Düzeltme yeşilse `tabanFiyatTL: 100` girilir (Okan kesin değeri) + taban-fiyat
   tablosu yeniden üretilir + vida sayfası "100,00 TL'den başlayan" gösterir.
4. Önizleme eşlemi BU PAKETİN İŞİ DEĞİL (Faz E'de) — sadece fiyat formülü + taban fiyat.

## Kabul (mimar koşacak)
1. Yeni vida kalibrasyon testi (fixture'lı): ≤%3, uç noktalar raporda; önce ESKİ
   formülde KIRMIZI kanıtı (M12 ≈ M5 çıktığını gösteren koşum).
2. `node jenerator/test/fiyat-test.js` — vida artık DOLU aile olarak (17→18) yeşil;
   zemin kuralı vida için de test edilir (M5'ten küçük set → 100 TL tabanı).
3. `node jenerator/test/kalibrasyon-senkron.js` + `node shop/test/kabul.js` yeşil
   (shop r3 sentetik null override'ı vida dolunca da yeşil kalmalı — fiyat mühendisi
   bunu öngörüp sentetiğe çevirmişti, doğrula).
4. Parite 2'li yeşil. 5. Build sonrası vida sayfası ekran görüntüsü (fiyatlı).

## Rapor
Kalibrasyon tablosu (tip × M × sapma) + fiyat örnekleri (M5/M8/M12 aynı boyda kaç TL —
Okan'a gösterilecek) + DEVAM.md. Yargı mimara (KraL).
