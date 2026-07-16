# pruvo-shop — kurulum ve canliya gecis (is paketi: tools/paket-shop-odeme.md)

Self-servis satin alma worker'i: urun sayfasinda filament+renk+adet -> localStorage sepet ->
`/api/shop/baslat` (fiyat D1'den, iyzico Checkout Form initialize) -> musteri iyzico'nun
HOSTED sayfasinda oder (kart bilgisi SITEDE ASLA girilmez) -> iyzico `/api/shop/donus`a
token POST'lar -> worker `retrieve` ile SUNUCUDA dogrular -> D1 `siparisler` + Telegram.

## Dosyalar

- `wrangler.toml`     — worker tanimi + route (`pruvo3d.com/api/shop/*`) + D1 binding
- `config.json`       — SADECE sepet kalem siniri + taksit. **Katsayi/renk/adet BURADA DEGIL**,
  `/secenekler.js`'te (tek kaynak — asagidaki "Mimari notlar").
- `src/index.js`      — uclar: /baslat, /donus (fiyat hesabi + iyzico + D1 + Telegram)
- `src/iyzico.js`     — IYZWSv2 (HMACSHA256) istemcisi: CF initialize + retrieve
- `src/parametrik.js` — sari seri sunucu-tarafi yeniden hesabi (kanal kapali; asagida)
- `src/semalar.js`    — parametrik sema haritasi (jenerator/urunler/*.json statik import)
- `test/kabul.js`     — 11 kabul testi (asagida)
- `.dev.vars.example` — yerel/sandbox anahtar sablonu (gercekleri `.dev.vars`a, gitignore'da)

## Kabul testleri

    node shop/test/kabul.js              # 1,2,3,4m,5,6,7,8,9,10,11 — mock iyzico + yerel D1
    node shop/test/kabul.js --paritesiz  # 7'siz hizli tur
    node shop/test/kabul.js --sandbox    # 4: GERCEK sandbox uctan uca (anahtar + elle test karti)

Not: 7 numarali parite testleri guncel `urunler.json` ister (canli D1 ile karsilastirir);
bayat worktree kopyasiyla kirmizi yanar — ana repodan (guncel katalogla) kostur.

## Deploy (sandbox'la yayin) — mimarin/Okan'in adimlari

1. D1 semasi (siparisler tablosu dahil):  `python3 tools/d1-sync.py --sema`
2. Secret'lar (deger repoya/sohbete YAZILMAZ):
       cd shop  # veya --config shop/wrangler.toml
       npx wrangler secret put IYZICO_API_KEY      # sandbox-...
       npx wrangler secret put IYZICO_SECRET_KEY
       npx wrangler secret put TELEGRAM_TOKEN      # mevcut PRUVO botunun token'i — OKAN ONAYIYLA
3. Worker:  `npx wrangler deploy`  (route: pruvo3d.com/api/shop/* — zone yetkisi ister)
4. Site: index.html + build.py + secenekler.js degisiklikleri main'e girince Actions yayinlar
   (secenekler.js deploy.yml beyaz listesinde — 2eed40a; build.py onu repo kokunden okur).
5. Duman testi: sitede sepet -> Kartla Guvenli Ode -> iyzico sandbox sayfasi acilir;
   sandbox test karti 5528790000000008 12/30 123 -> donuste "Odemeniz alindi" + Telegram.

## Canliya gecis (iyzico basvurusu onaylaninca — AYRI kucuk is)

1. `wrangler.toml` -> `IYZICO_BASE_URL = "https://api.iyzipay.com"`
2. Canli anahtarlar: `wrangler secret put IYZICO_API_KEY` / `IYZICO_SECRET_KEY`
3. `npx wrangler deploy` + gercek kartla dusuk tutarli duman testi + iade.

## Mimari notlar

- **TEK KAYNAK `/secenekler.js`** (Faz 1 modulu): katsayi tablosu (FILAMENT_FARK), renk
  listesi + "Diger" %15, adet araligi (1-99), parametrik odeme anahtari ve fiyat hesabi
  (`satirOzeti` / `hesaplaFiyatKurus` / `parametrikFiyatKurus`) ORADA.
  - Worker onu **import eder** (`shop/src/index.js` -> `import "../../secenekler.js"`; IIFE
    globalThis'e yazar) ve sunucu tutarini AYNI fonksiyonla hesaplar.
  - `tools/build.py` secici HTML'inin "(+%30)" etiketlerini o dosyadan **okur** (regex ile
    FILAMENT_FARK/RENK_SECENEKLERI/ADET_*), katsayi degisince etiket eskimez.
  - Yani katsayinin ikinci kopyasi YOK. Degistirmek icin: `secenekler.js` -> worker'i yeniden
    deploy et + site build'i (Actions) — `shop/config.json`'da SADECE sepet siniri + taksit var.
- Fiyat HER ZAMAN sunucuda: D1 `urunler.fiyat` -> `satirOzeti` -> katsayi, sonra "Diger" renk
  +%15, sonra adet. **YUVARLAMA YOK (Okan, 16 Tem):** kusurat aynen korunur, kurusuyla tahsil
  edilir (333 x 1.30 = 432,90; x3 = 1.298,70 — ara yuvarlama da yok).
- **KARGO (Okan, 16 Tem — KESIN; tools/paket-shop-kargo.md):** urun toplami < 2.500,00 TL ->
  250,00 TL gonderim; >= 2.500,00 TL (tam 2.500 DAHIL) -> bedava. Kural TEK yerde:
  `secenekler.js` `kargoKurus()` (KARGO_UCRET_KURUS=25000, KARGO_BEDAVA_ESIK_KURUS=250000) —
  sepet paneli ve Worker ayni fonksiyonu okur, degistirmek icin sadece orayi duzenle
  (degisiklik yetkisi SADECE Okan'da). Worker kargoyu iyzico'ya AYRI kalem (`id: "gonderim"`)
  gecirir, D1 `siparisler.kargo_kurus` kolonuna yazar (tahsilat = tutar_kurus + kargo_kurus).
  Istemciden gelen kargo/tutar alanlari OKUNMAZ (kabul testi 10). Canli tabloya kolonu
  `python3 tools/d1-sync.py --sema` ekler (kolon_goc — deploy adimi 1 yeterli).
- **Para TAMSAYI KURUSTA** (`hesaplaFiyatKurus`; D1 kolonu `tutar_kurus`, JSON alanlari
  `birim_kurus`/`tutar_kurus`). TL'de carpim yapilsa `333*1.30 = 432.90000000000003` gelir ve
  tutar sessizce kayar; iyzico'ya giden metin de tamsayidan uretilir (`kurusMetin` -> "432.90",
  toFixed degil). Gosterim 2 ondalik, virgullu. Tek yuvarlama kurusun ALTI icindir (yarim kurus
  tahsil edilemez; ör. "Diger" renkte 333 -> 497,835 -> 497,84).
- Kabul testi 1 beklentiyi tek kaynaktan TURETIR (zinciri sinar), test 8 ise SPEC degerlerini
  SABIT tutar (katsayi tablosu yanlis degistirilirse yakalar) — ikisi birlikte hem kod hem
  tablo kaymasini yakalar. Kanit: yuvarlama geri konuldugunda 1 ve 8 kirmizi yaniyor.
- **Adet araligi disi istek REDDEDILIR** (400), sessizce 1-99'a cekilmez (test 8).
- **Boy secimi Worker'da REDDEDILIR** (`boy-desteklenmiyor`): D1 katalogunda `boy_secenekleri`
  kolonu YOK -> sunucu boy farkini dogrulayamaz. Bugun hicbir urunde kullanilmiyor; ileride
  eklenirse once D1'e kolon + d1-sync.py alani, sonra buradaki red kaldirilir. Sessizce 0 TL
  fark uygulayip eksik tahsil etmektense istek reddedilir.

## Parametrik ("olcuye ozel" sari seri) — altyapi HAZIR, kanal KAPALI

- **Bugunku davranis:** parametrik kalem odeme akisina GIREMEZ, WhatsApp'a yonlendirilir
  (kabul testi 5). Sebep: taban fiyatlar bos (`jenerator/urunler/*.json` -> `tabanFiyatTL`
  18/18 null) VE `secenekler.js` icindeki `PARAMETRIK_ODEME_ACIK = false`.
- **Sunucu-tarafi yeniden hesap** (`shop/src/parametrik.js`): istemcinin gonderdigi
  `hacim_mm3` / `parametrik_fiyat_kurus` OKUNMAZ. Worker semayi kendi bundle'indan alir
  (`shop/src/semalar.js`), parametreleri min/max/adim ile dogrular (`KONF.dogrula`), hacmi
  `jenerator/hacim.js` ile kendi hesaplar, fiyati `parametrikFiyatKurus` ile cikarir —
  hepsi sitenin yukledigi dosyalarin AYNISI. Kabul testi 9 bunu kaniti ile dogrular
  (istemci hacim=1/fiyat=1 gonderir, sunucu 184,00 TL bulur).
- **Red yollari:** aralik disi parametre (`parametre-araligi`), semada olmayan alan
  (`bilinmeyen-parametre` — sessizce yok sayilmaz), taban fiyat yok (`taban-fiyat-yok`),
  parametresiz kalem (`parametre-yok`), semasi olmayan parametrik urun (WhatsApp).
- **ACMA ADIMLARI (mimar karari; tek basina taban fiyat girmek ACMAZ):**
  1. Okan taban fiyatlari verir -> `jenerator/urunler/*.json` `tabanFiyatTL` doldurulur
     (`tools/taban-fiyat-tablosu.md`).
  2. `secenekler.js` -> `PARAMETRIK_ODEME_ACIK = true`.
  3. Kabul testi 5 "parametrik dislama" -> "parametrik dogrulanmis-dahil"e evrilir
     (spec: paket-sari-konfigurator.md "SHOP ENTEGRASYONU"); testi mimar gunceller.
  4. `npx wrangler deploy` + sandbox duman testi.
  Iki asamali olmasi KASITLI: fiyat girildi diye odeme kanali sessizce acilmasin.
- **Sema listesi elle senkron** (`shop/src/semalar.js`): Worker'da glob yok, semalar statik
  import edilir. Kabul testi 9(a) listeyi `jenerator/urunler/` ile karsilastirir — yeni sema
  eklenip liste guncellenmezse test KIRMIZI yanar (sessizce "sema yok -> red"e dusmez).
- Istemciden gelen tutar alanlari OKUNMAZ (kabul testi 1 bunu sinar).
- `parametrik:true` / fiyati bos urun odeme akisina giremez (test 5); WhatsApp kanali durur.
- Callback idempotent: `siparisler.token` UNIQUE; 'odendi'ye gecis tek sefer (test 3),
  bildirim tek sefer. Uydurma token -> 404, kayit olusmaz (test 2).
- Retrieve ALTYAPI hatasi (status:failure, or. 1001) -> siparis 'basarisiz' DEGIL **'incele'**
  + Telegram uyarisi: odemenin gercek durumu bilinmiyor, parasi cekilmis musteri sessizce
  dusurulmez; retrieve duzelince ayni token 'odendi'ye ilerler (test 11; DEVAM.md bulgusu).
- Tutar/kimlik uyusmazliginda siparis 'incele' durumuna duser + Telegram uyarisi (otomatik
  onay YOK).
- Ayni D1 (pruvo-katalog) kullanilir ama `siparisler` tablosu d1-sync'ten bagimsizdir.

