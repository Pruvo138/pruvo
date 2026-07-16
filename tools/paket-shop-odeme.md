# MÜHENDİS İŞ PAKETİ — Self-Servis Shop + iyzico Hosted Ödeme

**Kat:** MÜHENDİS (Opus yüksek efor). Kaynak kod işi; ödeme/güvenlik içerir, hatası sessiz olabilir.
**Karar sahibi:** Okan (16 Tem 2026) — "müşteri ödemeyi yaparken iyzico'ya gider, ödemesini yapar,
bize geri döner; onaylandıysa siparişi işleme koyarız."
**Mimar:** KraL. Sorular yargı listesine; iş DURDURULMAZ, karar mimara çıkar.

## AMAÇ

pruvo3d.com'a müşterinin tek başına tamamladığı satın alma akışı:
ürün sayfasında **filament + renk seçimi** → **sepet** → **iyzico hosted ödeme sayfası**
(yönlendirme; müşteri kartı iyzico'da girer, 3DS dahil) → dönüş + **sunucu-tarafı doğrulama** →
sipariş kaydı + bildirim. WhatsApp/Ege kanalı aynen kalır (ikinci kapı).

## OKAN'IN KARARLARI (16 Tem)

1. **Filament fiyatı katsayılı (Okan ONAYLI, 16 Tem — kesin değerler):** liste fiyatı = PLA
   taban. `PLA 1.00 / PETG 1.30 / ABS 1.50 / TPU 1.55 / ASA 1.60 / Karbon katkılı 2.00`.
   TEK yerde config; Okan sonradan değiştirebilir. (Önceki taslak 1.15/1.30 GEÇERSİZ.)
   TPU (esnek) seçenek listesine DAHİL — malzeme metinleri `tools/filamentler.json`'dan.
2. **Renk (Okan KESİN kararı, 16 Tem): Siyah / Beyaz / Gri (fark yok) + "Diğer" (+%15).**
   secenekler.js'teki mevcut model (RENK_SECENEKLERI + RENK_DIGER_YUZDE=15) AYNEN kalır —
   değiştirme. "Diğer" seçilirse +%15 filament katsayısından SONRA uygulanır ve Worker
   sunucu-tarafı hesapta da aynı sırayla doğrular (kuruş korunur, yuvarlama yok).
   Envanter bağlantısı YOK (Faz 2). Sarı seri kuralı: "her renk" DENMEZ → "farklı renk seçenekleri".
3. **iyzico canlı anahtar YOK, başvuru sürecinde.** Geliştirme + kabul testleri
   **iyzico SANDBOX** anahtarlarıyla yapılır (sandbox-api.iyzipay.com; sandbox hesabını
   mühendis kendisi açabilir, ücretsiz). Canlıya geçiş ayrı küçük iş: Okan anahtarları
   getirince secret değişimi + smoke test.

## MİMARİ (bağlayıcı çerçeve)

- **Front:** saf HTML/CSS/JS (kütüphane/CDN YASAK — CLAUDE.md). Varyant seçici + sepet UI:
  `index.html` ve `tools/build.py` ürün sayfası şablonuna eklenir. Sepet **localStorage**.
  MEVCUT TABAN: `/secenekler.js` (PRUVO_SECENEK, Faz 1) — üstüne inşa et, kopyalama.
  **ADET (Okan, 16 Tem):** ürün sayfasında adet seçici (varsayılan 1, aralık 1-99) + sepet
  panelinde satır başına +/- kontrolü; satır tutarı = kuruşlu birim fiyat × adet, sepet
  toplamı satırların toplamı. Adet, sepet veri modeline (PRUVO_SECENEK satırı) ve Worker'a
  giden sipariş kalemlerine de girer — Worker tutarı D1 fiyatı × katsayı × adet olarak
  kendisi hesaplar.
  Tasarım: lacivert #12294d ana, kırmızı sadece vurgu; "3D baskı" İFADESİ HİÇBİR YERDE
  KULLANILMAZ ("özel üretim" dili).
- **Backend: YENİ Cloudflare Worker `pruvo-shop`** — kodu bu repoda `shop/` dizininde
  (wrangler.toml dahil). **`~/dev/pruvo-bot` reposuna DOKUNMA** (o Hoca'nın alanı; desen
  bakmak serbest, yazmak yasak). Ege worker'ına route eklenmez; ayrı worker, ayrı secret seti.
- **Fiyat SUNUCUDA hesaplanır:** Worker, sepetteki id'lerin fiyatını **D1 `pruvo-katalog`**'dan
  okur, katsayıyı uygular; istemciden gelen tutara ASLA güvenilmez. Parametrik (`parametrik:true`)
  ve fiyatı boş ürünler bu akışın DIŞINDA (butonları WhatsApp'a gitmeye devam eder).
- **Ödeme:** iyzico **Checkout Form (hosted/redirect)** — `retrieve` ile sunucu-tarafı sonuç
  doğrulaması yapılmadan sipariş "ödendi" OLMAZ. Müşterinin dönüş URL'sine/istemci verisine
  güvenilmez. Callback idempotent (aynı token iki kez gelirse tek sipariş).
- **Sipariş kaydı:** D1'de yeni tablo `siparisler` (şema: id, tarih, urunler-json, tutar,
  filament, renk, iyzico-odeme-id, durum, musteri-ad/tel/adres). D1 günlük yazma limitine
  dikkat (sipariş hacmi düşük, sorun beklenmez). Şema dosyası: `tools/d1-sema.sql`'e ek.
- **Bildirim:** ödeme onayında Okan'a Telegram mesajı (yeni bot token'ı Okan'dan İSTEME —
  mevcut PRUVO Telegram botunun token'ı Wrangler secret olarak `pruvo-shop`'a da tanımlanır;
  bu adım deploy sırasında Okan onayıyla). Notion CRM entegrasyonu Faz 2 (bu pakette YOK).
- **Sır hijyeni (repo PUBLIC):** anahtar/token/secret repoya ASLA girmez — hepsi
  `wrangler secret`. `shop/` dizininde örnek `.dev.vars.example` (değersiz şablon) bırakılır.
- **Yasal:** mevcut Gizlilik/Teslimat-İade/Mesafeli Satış sayfaları ödeme sayfasından linklenir.

## KAPSAM DIŞI (yapma)

- Sitede kart formu (iframe dahil) — model REDIRECT.
- Notion CRM yazımı, stok/envanter bağlantısı, kargo takibi, üyelik/hesap sistemi — Faz 2+.
- `urunler.json`'a yazma (ürün verisi değişmiyor; varyantlar config'ten gelir).
- Canlı anahtarla deploy (sandbox'a kadar; canlı geçiş ayrı iş).

## KABUL TESTLERİ (çalıştırılabilir; hepsi yeşil olmadan iş kapanmaz)

`shop/test/` altına, tek komutla koşan test scripti (`python3 shop/test/kabul.py` veya
`node shop/test/kabul.js`; CLAUDE.md komut stiline uygun — shell değişkeni yok):

1. **Fiyat bütünlüğü:** istemci 1 TL'lik sahte tutar gönderir → Worker D1 fiyatı × katsayı ile
   hesaplar, sahte tutarı YOK SAYAR (test: yaratılan iyzico oturumundaki tutar ≠ istemci tutarı,
   = sunucu hesabı).
2. **Sahte callback reddi:** geçersiz/uydurma token ile callback → sipariş OLUŞMAZ, 4xx döner.
3. **İdempotens:** aynı geçerli ödeme sonucu iki kez işlenir → TEK sipariş kaydı.
4. **Sandbox uçtan uca:** sandbox test kartıyla gerçek akış — sepet → redirect → ödeme →
   dönüş → `retrieve` doğrulaması → D1'de sipariş satırı + (kurulduysa test kanalına) bildirim.
   Kanıt: sandbox ödeme id + D1 satırı test çıktısında.
5. **Parametrik dışlama:** `parametrik:true` ürün sepete eklenemez / ödeme oturumuna giremez.
6. **Sır taraması:** `git grep` ile shop/ altında anahtar deseni yok (test scripti kontrol eder).
7. **Regresyon:** `node tools/parite-test.js` ve `node tools/parite-ege.js` YEŞİL kalır
   (arama koduna dokunulmuyor ama D1'e şema eklendiği için koşulacak).
8. **Katsayı doğruluğu (Okan uyarısı: başka oturumlar YANLIŞ hesapladı):** 100 TL'lik ürün için
   beklenen fiyatlar birebir doğrulanır: PLA 100 / PETG 130 / ABS 150 / TPU 155 / ASA 160 /
   Karbon 200 TL. **YUVARLAMA YAPILMAZ (Okan, 16 Tem):** küsurat aynen korunur ve kuruşuyla
   tahsil edilir — örn. 333×1.30 = 432,90 TL. Test: 333 TL'lik üründe PETG fiyatı TAM 432,90;
   sepet toplamı = kalemlerin kuruşlu fiyatlarının toplamı (ara yuvarlama da yok). Gösterim
   2 ondalık, TL formatı virgüllü. **Adet dahil:** 3 adet 333 TL'lik ürün PETG'de satır tutarı
   TAM 1.298,70 TL (432,90×3); istemciden gelen adet Worker'da 1-99 aralığına doğrulanır,
   aralık dışı istek reddedilir.

## TESLİM

- Kod `shop/` + build.py/index.html değişiklikleri; **commit ETME** — değişiklik listesi +
  test çıktılarıyla rapor ver, commit/push mimarındır.
- Rapor: ne kuruldu, secret listesi (adları, değerleri DEĞİL), canlıya geçiş için kalan adımlar
  (Okan'ın iyzico anahtarları + DNS/route + Telegram secret onayı), yargı listesi.
