# PAKET K180 — 🔴 YAYIN BLOKERİ: `eski-fiyat-test.py` özet vakum nöbetçisi düştü

**Mimar:** KraL · **Tarih:** 18 Ağu 2026 · **ÖNCELİK: EN YÜKSEK — yayın KAPALI**

## DURUM (mimar ölçtü, CI koşumu `32136228054`, SHA `32875a4a`)
`serit-a2` KIRMIZI → `deploy` ve `yayin` **SKIPPED** → vitrin yayını DURDU.
Düşen adım: `python3 tools/eski-fiyat-test.py`. **Tek** iddia ihlali, (f) bölümünde:

```
  ✅ ozet A/B icin alan enjekte edilen urun (10) — vakum nobeti
  ❌ enjeksiyon ozet ciktisini GERCEKTEN degistirdi — vakum nobeti
  ✅ bugunku katalogun ozet.json kartlarinda eski_fiyat degeri YOK
  ✅ ozet A/B: enjekte edilen ozet YALNIZ eski_fiyat anahtari kadar farkli
KIRMIZI — 1 iddia ihlali
```
Diğer 60+ iddia YEŞİL (kural 29/29, parite, XSS, tarihsel kuruş tam küme 1200/1200,
JSON-LD, feed, şema kayıtları).

🔴 **ÇELİŞKİ VAR, ÖNCE ONU ÇÖZ:** aynı bölümde bir iddia "enjeksiyon çıktıyı DEĞİŞTİRMEDİ"
derken, iki satır aşağısı "enjekte edilen özet YALNIZ `eski_fiyat` anahtarı kadar FARKLI"
diyor. İki iddia aynı şeyi ölçüyorsa biri yanlış; farklı örneklem/farklı ürün kümesi
kullanıyorlarsa **ölçüm evrenleri ayrışmış** demektir. Hangi ürünleri seçtiklerini yan yana
bas ve ayrışmayı ADIYLA göster.

## İLK HİPOTEZ (mimarın; ÇÜRÜT ya da DOĞRULA, körü körüne uygulama)
Katalog bugün **29.057 → 29.280** büyüdü (kardeş evin ürün partileri). Vakum nöbetçisi
enjeksiyon için ürünü **canlı katalogdan** seçiyor olabilir; seçim parametrik (sarı) ya da
konfigürlü ürünlere kaydıysa `eski_fiyat` o kartlarda **kural gereği** basılmaz ve enjeksiyon
çıktıyı hiç değiştirmez → nöbetçi kendi fikstürü yüzünden düşer
([[fikstur-degeri-mutasyon-koru]] · [[canli-evren-bayat-agac-yarisi]]).
Karşı-kanıt ara: aynı test önceki koşumda (`45c9ec1f`) YEŞİLDİ ve o koşumdan bu yana
`tools/eski-fiyat-test.py` ile `build.py` **değişmediyse** sebep VERİdir, kod değil. Bunu
`git log` ile ÖLÇ, varsayma.

## 🔴 YASAK — İŞİ YEŞİLE BOYAMA
- İddiayı SİLME, gevşetme, `continue-on-error` EKLEME, şeridi düşürme.
- Enjeksiyon ürününü "işe yarayan bir ürüne" sabitleyip geçme — bu, nöbetçiyi kör eder
  ([[test-hatali-davranisi-kutsar]]).
- Doğru çare: seçim **kuralı** düzelsin — nöbetçi, `eski_fiyat` göstermesi MÜMKÜN olan
  (parametrik DEĞİL, konfigürlü DEĞİL) ürünlerden seçsin ve **böyle ürün bulunamazsa**
  `VAKUM: uygun urun YOK` diye **KIRMIZI** dursun, sessizce geçmesin.
- Eğer ölçüm gerçek bir REGRESYON gösteriyorsa (kart özeti geçerli `eski_fiyat`ı artık
  taşımıyor) çare testte DEĞİL üretim kodundadır — o zaman DUR ve mimara yaz.

## KABUL
```
python3 tools/eski-fiyat-test.py      → rc=0, 0 iddia ihlali
```
**MUTASYON (2 vaka, ikisi de KIRMIZI yakmalı):**
- M1: `kart_ozeti`nin `eski_fiyat` yazan kolunu ÖLDÜR → vakum nöbetçisi KIRMIZI yanmalı
  (yanmıyorsa nöbetçi hâlâ kör, iş BİTMEMİŞTİR).
- M2: seçimi kasten parametrik/konfigürlü ürüne kaydır → `VAKUM: uygun urun YOK` KIRMIZI.
🔴 Mutant birden çok ekseni tetikliyorsa YALIT ([[mutant-yan-ekseni-de-tetikliyorsa-olcmez]]).

Ayrıca: `python3 tools/build.py` rc=0 (yayın yolu yeniden açılıyor mu).

## SINIR
`urunler.json` ve gizli kaynak düzlemi **DOKUNULMAZ** — bu bir VERİ düzeltmesi değil.
Main'e push ETME, merge ETME; hüküm mimarındır.

## RAPOR
Dalda, projenin kanonik mühendis raporu adıyla. Teşhis ÖNCE: iki çelişen iddianın evrenleri ·
sebep VERİ mi KOD mu (git ölçümüyle) · sonra çare + kabul + mutasyon. Ham çıktılar birebir.
