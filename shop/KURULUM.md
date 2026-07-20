# pruvo-shop — kurulum ve canliya gecis (is paketleri: tools/paket-shop-odeme.md + tools/paket-shop-kargo.md)

Self-servis satin alma worker'i: urun sayfasinda filament+renk+adet -> localStorage sepet ->
`/api/shop/baslat` (fiyat + kargo + KDV dokumu D1'den/sunucuda; zorunlu sozlesme onayi) ->
KART: iyzico Checkout Form (HOSTED sayfa; kart bilgisi SITEDE ASLA girilmez) -> iyzico
`/api/shop/donus`a token POST'lar -> worker `retrieve` ile SUNUCUDA dogrular -> D1
`siparisler` + Telegram. HAVALE/EFT: iyzico'ya gidilmez; siparis 'havale-bekliyor' +
musteriye IBAN/unvan/TAM tutar ekrani + Telegram "HAVALE BEKLENIYOR".

## Yonetim sayfasi (siparis yonetimi paketi — tools/paket-siparis-yonetimi.md)

`https://pruvo3d.com/api/shop/yonet?anahtar=<YONET_ANAHTAR>` — tek dosyalik, mobil uyumlu
sayfa (worker icinde gomulu; harici kutuphane yok). `YONET_ANAHTAR` wrangler secret
(`openssl rand -hex 24`); TANIMSIZSA tum /yonet* uclari 404 doner (varlik sizmasin).
- **Liste**: son 50 siparis (durum suzgeci), PII yalniz anahtarli yanitta. Her satirda
  **FILAMENT + RENK vurgulu** + baski onerisi (D1 `urunler.baski` — gizli kayittan
  d1-sync ile; yoksa malzeme fallback'i) + "Yerel komut kopyala" (`python3 tools/yazdir.py
  <no>` — arac ayri mikro paket).
- **Durum makinesi** (`POST /yonet/durum`): odendi→uretimde→kargolandi→tamamlandi;
  havale-bekliyor→odendi; her durum→iptal. Bilinmeyen durum/izinsiz gecis 400.
  'kargolandi'ya SADECE kargo formundan gecilir (takip kodu zorunlu). Her gecis
  `durum_gecmisi` kolonuna ISO damgayla islenir (ayni satir; ek yazma maliyeti yok).
- **Kargo** (`POST /yonet/kargo` {siparis_no, kargo_firma, kargo_kodu}): durum
  'kargolandi' + musteriye kargo e-postasi (Resend).
- **Uretim dosyasi** (`GET /yonet/stl?siparis_no=..&kalem=N`): sari (parametrik) satirda
  siparisteki parametrelerle onizleme worker'inin `/api/onizleme/ic-derle` ucundan STL
  URETIR (IC_DERLE_ANAHTAR ile; musteri kotasi/onbellegi yenmez); normal satirda OZEL R2
  kovasindan (`pruvo-ozel`, `stl/<urun-id>.stl|.3mf`) stream eder. Dosya adi
  `<siparis_no>-<urun-id>.stl|.3mf`. R2'de yoksa 404 + "stl/ klasoru / Drive / gizli
  kaynak kaydina bak" notu (tedarikci bilgisi sayfaya YAZILMAZ). Toplu yukleme:
  `python3 tools/stl-r2-yukle.py` (idempotent; yanlis adlanani raporlar, tahmin etmez).

## E-posta (Resend — siparis yonetimi paketi Faz 2)

Gonderen `PRUVO <siparis@pruvo3d.com>`; sablonlar Turkce sade HTML (`src/eposta.js`).
Tetikler: (1) siparis 'odendi' (kart callback) ve 'havale-bekliyor' (havale baslatma) →
musteriye onay (satirlar + parametre detayi + tutar/kargo/KDV dokumu + adres + WhatsApp
linki) + `BILDIRIM_EPOSTA`'ya (vars: info@pruvo3d.com) satici kopyasi; (2) kargo ucu →
musteriye firma + takip kodu. `RESEND_API_KEY` YOKSA e-posta sessizce atlanMAZ: Telegram'a
"e-posta gönderilemedi (anahtar yok)" duser, siparis akisi BOZULMAZ (kabul testi 23);
e-posta hatasi odemeyi asla dusurmez (ctx.waitUntil + try/catch). Callback idempotens
e-postayi da kapsar: ayni token 2. kez → e-posta tekrarlanmaz (test 21).

## Havale/EFT onayi

Para iyzico'dan gecmedigi icin otomatik dogrulama yok; Okan dekontu gorunce **yonetim
sayfasindan** siparisi `havale-bekliyor → odendi` yapar (TEK YOL BU). Sayfa/anahtar yoksa
esdeger yedek komut (AYNI SQL kosulu — iki yol celismez, ikisi de `durum='havale-bekliyor'`
sartiyla gecer):

    npx wrangler d1 execute pruvo-katalog --remote --command \
      "UPDATE siparisler SET durum='odendi' WHERE siparis_no='PR-...' AND durum='havale-bekliyor'"

Istemciden erisilebilen HICBIR uc durumu degistiremez (havale satirinin `token`'i NULL —
`/donus` onu hicbir token'la bulamaz; kabul testi 13'un negatif adimi; yonetim uclari
anahtarsiz 404). `durum='havale-bekliyor'` kosulu yanlis siparisi ezmeyi onler; komut 0
satir degistirdiyse numarayi kontrol et. Siparis 'odendi' ISARETLENMEDEN uretim baslamaz,
"odeme geldi" bildirimi atilmaz.

⚠️ **REKLAM OLCUMU — yonetim sayfasini kullan, ham SQL'i degil.** 20 Tem'den itibaren
`havale-bekliyor → odendi` gecisi **yonetim sayfasindan** yapilirsa Purchase olayi Meta
CAPI + GA4'e gider (`event_id = siparis_no`, kart akisiyla ayni dedup anahtari) — havale
cirosu artik reklam raporlarinda GORUNUR. Yukaridaki **ham SQL yedegi worker kodundan
gecmez**, dolayisiyla o yoldan isaretlenen siparisin cirosu Meta/GA4'te GORUNMEZ (satis
kaydi ve uretim akisi etkilenmez, yalniz reklam olcumu eksik kalir). Ham SQL yalniz
yonetim sayfasina/anahtara erisilemedigi durumda kullanilmali. Olayin gidip gitmedigi
Cloudflare Logs'ta `olcum {...}` satirlarindan gorulur (`[observability]` acik).

## Dosyalar

- `wrangler.toml`     — worker tanimi + route (`pruvo3d.com/api/shop/*`) + D1 binding
- `config.json`       — SADECE sepet kalem siniri + taksit. **Katsayi/renk/adet BURADA DEGIL**,
  `/secenekler.js`'te (tek kaynak — asagidaki "Mimari notlar").
- `src/index.js`      — uclar: /baslat, /donus (fiyat hesabi + iyzico + D1 + Telegram)
- `src/iyzico.js`     — IYZWSv2 (HMACSHA256) istemcisi: CF initialize + retrieve
- `src/parametrik.js` — sari seri sunucu-tarafi yeniden hesabi (kanal kapali; asagida)
- `src/semalar.js`    — parametrik sema haritasi (jenerator/urunler/*.json statik import)
- `src/yonet.js`      — anahtar korumali yonetim sayfasi + uclari (liste/durum/kargo/stl)
- `src/eposta.js`     — Resend istemcisi + Turkce siparis/kargo e-posta sablonlari
- `test/kabul.js`     — 23 kabul testi (asagida; 10 kargo, 11 retrieve-incele,
  12 siparis no, 13 havale/eft, 14 kdv, 15 sozlesme onayi, 18-23 siparis yonetimi+e-posta)
- `.dev.vars.example` — yerel/sandbox anahtar sablonu (gercekleri `.dev.vars`a, gitignore'da)

## Kabul testleri

    node shop/test/kabul.js              # 15 test — mock iyzico + yerel D1
    node shop/test/kabul.js --paritesiz  # 7'siz hizli tur
    node shop/test/kabul.js --sandbox    # 4: GERCEK sandbox uctan uca (anahtar + elle test karti)

Ayni makinede baska bir oturum da kabul kosuyorsa portlar cakisir (EADDRINUSE) —
`KABUL_WORKER_PORT` / `KABUL_MOCK_PORT` env degiskenleriyle ez.

Not: 7 numarali parite testleri guncel `urunler.json` ister (canli D1 ile karsilastirir);
bayat worktree kopyasiyla kirmizi yanar — ana repodan (guncel katalogla) kostur.

## Deploy (sandbox'la yayin) — mimarin/Okan'in adimlari

1. D1 semasi (siparisler tablosu dahil):  `python3 tools/d1-sync.py --sema`
2. Secret'lar (deger repoya/sohbete YAZILMAZ):
       cd shop  # veya --config shop/wrangler.toml
       npx wrangler secret put IYZICO_API_KEY      # sandbox-...
       npx wrangler secret put IYZICO_SECRET_KEY
       npx wrangler secret put TELEGRAM_TOKEN      # mevcut PRUVO botunun token'i — OKAN ONAYIYLA
       npx wrangler secret put YONET_ANAHTAR       # openssl rand -hex 24 (yonetim sayfasi)
       npx wrangler secret put RESEND_API_KEY      # Resend (Okan hesabi acinca; yoksa e-posta atlanir+Telegram uyarisi)
       npx wrangler secret put IC_DERLE_ANAHTAR    # onizleme worker'inda da AYNI degerle koyulur (parametrik STL)
   HAVALE_IBAN / HAVALE_UNVAN secret DEGIL: musteriye zaten gosterilen bilgi —
   wrangler.toml [vars]'ta (Okan verdi, 16 Tem; IBAN mod-97 dogrulandi). Ayni adla secret
   TANIMLAMA (vars+secret cakismasi deploy'u dusurur); degistirmek icin toml'u duzenle.
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
  Istemciden gelen kargo/tutar alanlari OKUNMAZ (kabul testi 10). Canli tabloya kolonlari
  (`kargo_kurus`, `kdv_kurus`, `odeme_yontemi`, `sozlesme_onay`) `python3 tools/d1-sync.py
  --sema` ekler (kolon_goc — deploy adimi 1 yeterli; SIRA: once sema, sonra worker deploy,
  tersi INSERT patlatir).
- **SIPARIS NO (kalem 5):** `PR-yyMMdd-HHmmss-XXX` (Europe/Istanbul; XXX = ayni-saniye
  carpismasina karsi rastgele sonek, 0/O-1/I'siz alfabe). Sunucuda uretilir; D1 UNIQUE +
  INSERT oncesi on-kontrol. iyzico `conversationId`/`basketId` = siparis no; musteri donus
  sayfasinda, havale ekraninda ve Telegram'da gorunur (kabul testi 12).
- **KDV (kalem 8; Okan KESIN %20):** fiyatlar KDV DAHIL, tahsilat DEGISMEZ — dokum + kayit.
  Oran TEK yerde: `secenekler.js` `KDV_YUZDE`; ayristirma `kdvAyristir` (net = brut/(1+oran)
  kurusta, fark KDV'ye yedirilir -> net+KDV=brut BIREBIR). Dokum kargo dahil genel toplam
  uzerinden: sepet paneli + havale ekrani + donus sayfasi (worker ok yonlendirmesine
  t/kdv paramlari ekler). D1 `kdv_kurus` (fatura icin; kabul testi 14).
- **SOZLESME ONAYI (kalem 9, yasal):** odeme adiminda (kart+havale) zorunlu kutu — linkler
  MEVCUT yasal sayfalara (On Bilgilendirme -> /teslimat-iade/, Mesafeli Satis ->
  /mesafeli-satis/; yeni sayfa yazilmadi). ASIL zorunluluk sunucuda: `/baslat`ta
  `sozlesme_onay: true` yoksa 400 `sozlesme-onay-yok`; onay ani D1 `sozlesme_onay`
  kolonuna ISO damgasiyla yazilir (ispat kaydi; kabul testi 15).
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

