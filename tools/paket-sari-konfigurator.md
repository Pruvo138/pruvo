# MÜHENDİS İŞ PAKETİ — Sarı Seri Müşteri Konfigüratörü (Parametrik Ürün + Hacim-Orantılı Fiyat)

**Kat:** MÜHENDİS = **CODEX güçlü model + yüksek efor (İLK CODEX-MÜHENDİS PİLOTU — Okan
direktifi 16 Tem).** Yürütme deseni: bir oturum `codex exec`'i orkestre eder (thing-codex.py
deseni: iş Codex'te koşar, oturum bağlamına hacim girmez), kabul testlerini koşturur.
**İSTİSNA — Worker tarafı (ödeme sınıfı):** aşağıdaki "SHOP ENTEGRASYONU" bölümü bu pakette
YAPILMAZ; Opus shop mühendisine ek iştir (tools/paket-shop-odeme.md sahibi).
**Karar sahibi:** Okan (16 Tem): müşteri sarı üründe ölçü/parametreleri kendisi girer,
fiyat SADECE ürün hacmine orantılı otomatik artar ("hacim %8 büyüdüyse fiyat 100→108"),
kapsam mevcut 18 sarı ürün.

## AMAÇ

Sarı seri (parametrik:true) ürün sayfalarına müşteri konfigüratörü: parametre girişi
(ölçü/kalınlık/uzunluk/kesit...) → anında hacim → anında fiyat → sepete eklenebilir kalem.

## FİYAT KURALI (bağlayıcı; Okan)

`fiyat = tabanFiyat × (hacim / tabanHacim) × filamentKatsayı × renkFaktör`
- tabanFiyat: ürünün VARSAYILAN parametrelerdeki PLA fiyatı — **OKAN VERECEK** (mühendis
  18 ürünün varsayılan parametre + taban hacim tablosunu çıkarıp Okan'a fiyat şablonu sunar;
  tabanFiyat gelene kadar konfigüratör fiyatı "—" gösterir, altyapı hazır bekler).
- hacim oranı LİNEER, sınırsız hassasiyet; YUVARLAMA YOK (kuruş korunur: [[filament-fiyat-katsayilari]]).
- filamentKatsayı: PLA 1.00 / PETG 1.30 / ABS 1.50 / TPU 1.55 / ASA 1.60 / Karbon 2.00.
- renkFaktör: Siyah/Beyaz/Gri 1.00, "Diğer" 1.15. (Sarı seri rengi de artık müşteri seçer;
  "her renk" DENMEZ → "farklı renk seçenekleri".)

## PARAMETRE ŞEMA DOSYALARI ("jeneratör bölümü")

- Yeni dizin: `jenerator/urunler/<id>.json` — 18 sarı ürünün HER BİRİNE bir dosya:
  `{ parametreler: [{ad, birim, min, max, adim, varsayilan, aciklama}], hacimFormulu: "<js-fn-adi>",
  tabanHacimMm3, tabanFiyatTL|null }`.
- Hacim formülleri: `jenerator/hacim.js` — aile başına kapalı-form fonksiyon (torus, ekstrüzyon,
  koni-kabuk, plaka-ızgara...). SAF JS, tek modül: hem sitede (client) hem Worker'da AYNI dosya
  kullanılacak (tek kaynak — kopya yasak).
- **GİZLİLİK:** Tedarikçi izi hiçbir public dosyada GEÇMEZ (alan adları Türkçe/jenerik; kaynak
  eşleme gizli `.urun-kaynaklari.json`'da kalır). Şema İÇERİĞİ bizim yazdığımız matematik/
  aralıklar — public olabilir; tedarikçinin kodu/adı OLAMAZ.
- **KURULUM REHBERİ (Okan istedi):** `jenerator/KURULUM.md` — yeni parametrik ürün nasıl
  eklenir: şema dosyası yazımı → hacim fonksiyonu seçimi/yazımı → OpenSCAD doğrulama testi →
  taban fiyat → yayın. Adım adım, bir örnek üzerinden.

## UI (saf JS; sarı seri sayfa düzeni korunur)

Ürün sayfasında (build.py şablonu, parametrik dalı): parametre alanları (kaydırıcı/sayı girişi,
min-max/adım şemadan), canlı hacim + fiyat göstergesi (kuruşlu), malzeme + renk seçici
(secenekler.js/PRUVO_SECENEK ile aynı bileşenler), "Sepete Ekle" (parametre seti sepet satırına
JSON olarak girer). "Ölçüye Özel" sarı rozet ve mevcut açıklama yapısı KORUNUR. WhatsApp
sipariş butonu da kalır (parametreleri mesaja gömerek — self-servis istemeyen müşteri için).

## SHOP ENTEGRASYONU (BU PAKETTE YAPILMAZ — Opus shop mühendisine ek)

Worker, parametrik kalemde fiyatı İSTEMCİDEN ALMAZ: şema + hacim.js + taban fiyatla kendisi
yeniden hesaplar; parametreler min-max dışındaysa reddeder. Shop paketindeki "parametrik
dışlama" kabul testi (#5), bu altyapı yayına girince "parametrik doğrulanmış-dahil" testine
evrilir. Koordinasyonu mimar yapar.

## KABUL TESTLERİ (çalıştırılabilir; mimar koşturur)

1. **Hacim doğruluğu (kritik):** her ürün için ≥3 rastgele geçerli parametre setinde
   `hacim.js` sonucu ile OpenSCAD render STL hacmi (`/opt/homebrew/bin/openscad` yerelde
   kurulu) arasında sapma ≤%3. Test scripti seti üretir, koşar, tabloyu yazdırır.
2. **Fiyat orantısı:** taban×1.08 hacimli sette fiyat TAM ×1.08 (kuruş korunur, yuvarlama yok);
   filament+renk çarpanlarıyla bileşik örnek: taban 100 TL, hacim +%8, ASA, Diğer renk →
   100×1.08×1.60×1.15 = 198,72 TL birebir.
3. **Sınır doğrulama:** min-max/adım dışı giriş client'ta engellenir (alan kızarır, sepete
   eklenemez).
4. **Tek kaynak:** sitenin yüklediği hacim.js ile jenerator/hacim.js bayt-özdeş (test karşılaştırır).
5. **Gizlilik:** public dosyalarda (jenerator/, site çıktıları) tedarikçi adı geçmez — grep testi.
6. **Sarı seri kuralları:** "3D bask" ve "her renk" hiçbir çıktıda yok; rozet/fiyatsız düzen
   tabanFiyat=null ürünlerde korunuyor.
7. **Kurulum rehberi canlı testi:** KURULUM.md adımları izlenerek SAHTE bir örnek ürün uçtan
   uca eklenir (şema→hacim→test→temizlik) — rehber çalışıyor kanıtı.
8. **18/18 kapsam:** her sarı ürünün şema dosyası var ve şema alanları site açıklamasındaki
   "Neyi ayarlıyoruz?" maddeleriyle tutarlı (script kontrol eder, eksikler listelenir).

## TESLİM

- `jenerator/` dizini (şemalar + hacim.js + KURULUM.md) + build.py/urun şablonu değişikliği +
  test scriptleri + Okan'a taban fiyat tablosu şablonu (18 satır: ürün, varsayılan ölçüler,
  taban hacim, fiyat=___ TL).
- **Commit ETME** — rapor + test çıktılarıyla dön; commit/push ve canlıya alma mimarın.
  Taban fiyatlar Okan'dan gelmeden fiyat gösterimi açılmaz (altyapı bayrakla hazır durur).
