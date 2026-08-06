-- PRUVO katalog — Cloudflare D1 semasi (arama edge'e tasindi; FAZ 1).
-- Kurulum: python3 tools/d1-sync.py --sema
--
-- NEDEN trigram: index.html filtered() aramasi ALT-DIZE arar (token, arama metninin
-- herhangi bir yerinde gecebilir — kelime basi olmak zorunda degil). Standart FTS5
-- yalnizca kelime-oneki arar, bu yuzden site ile BIREBIR ayni sonucu vermez.
-- FTS5 trigram tokenizer'i LIKE '%...%' sorgusunu INDEKS uzerinden calistirir:
-- hem birebir parite hem indeks hizi. (D1'de sinandi: rows_read tam tarama degil.)
-- Not: trigram indeksi >= 3 harfli parcalar icin calisir; 1-2 harfli token (or. "a4")
-- indekssiz suzulur — /ara bunu bilerek en secici token'i indekse verecek sekilde kurar.

CREATE TABLE IF NOT EXISTS urunler (
  rid       INTEGER PRIMARY KEY,          -- FTS5 icin sabit rowid (urun silinmedikce degismez)
  id        TEXT NOT NULL UNIQUE,         -- urunler.json'daki kebab-id
  hash      TEXT NOT NULL,                -- icerik ozeti — diff-upsert bununla karar verir
  seq       INTEGER NOT NULL,             -- sabit sira anahtari; DESC = en yeni ustte
  baslik    TEXT NOT NULL,
  kategori  TEXT NOT NULL,
  -- ALT KATEGORI — kategori ICINDEKI daraltma etiketi ("Marin" > "Boya - Bakım").
  -- '' (bos) = urunun altkategorisi YOK (katalogun ~%99'u; olculdu 2026-08-01: 16.033
  -- kaydin 100'unde dolu). Veri urunler.json "altkategori" alaninda YASIYORDU ama HICBIR
  -- yerde islenmiyordu -> musteriye ULASMIYORDU. Bu kolon o yolu acar.
  -- KAYNAK + FAIL-CLOSED: arama.altkategori_kanonik(u) — izinli (kategori, altkategori)
  -- kumesi disindaki / tedarikci imzasi tasiyan her deger '' olur (bkz. arama.py
  -- ALTKATEGORI_IZINLI + altkategori_imza_sebebi). HASH'E GIRER (tur/stokta deseni,
  -- taban_fiyat/konfigur'un TERSI): alan PUBLIC urunler.json'da yasar ve icerik alanidir;
  -- hash kapsamasaydi altkategori degisimi satiri yeniden yazdirmaz, D1 sessizce bayat
  -- alt-filtre servis ederdi.
  altkategori TEXT NOT NULL DEFAULT '',
  marka     TEXT NOT NULL DEFAULT '[]',   -- JSON dizi (urunler.json'daki HAM deger)
  -- KANONIK MARKA UYELIGI — urunun UYE OLDUGU /marka/<slug>/ sayfalarinin kanonik adlari,
  -- JSON dizi. '[]' = hicbir kanonik markaya uye degil (jenerik urun).
  --
  -- NEDEN VAR (OLCULEN SESSIZ HATA, 4 Agu 2026 — musteri urunu KAYBEDIYOR ve alarm YOK):
  -- Uctaki (Worker) `?marka=` kolu `marka` kolonunda HAM STRING ESITLIGI ariyor; site ise
  -- markayi KATLIYOR (index.html markaKatla: "Volvo Penta" -> "Volvo", "Citroen" aksani,
  -- "Black and Decker" == "Black+Decker", "KIA" -> "Kia"). Sonuc: 128 kanonik markanin
  -- 9'unda cip ile sayfa AYRISIYOR, 120 urun-kalemi musteri CIPE BASINCA KAYBOLUYOR
  -- (olculdu: Volvo sayfa 726 · cip 620 = 106 kalem "Volvo Penta"; Citroen 4, IKEA 2,
  -- Opel 3, Datsun/Smart/Kia/Mini/Black+Decker 1'er). Site dogru gosterir, cip kaybeder,
  -- hicbir sey kirmizi yanmaz.
  --
  -- 🔴 NEDEN KOLON, NEDEN WORKER'DA KATLAMA DEGIL: katlama mantigini Worker'a KOPYALAMAK
  -- IKINCI GOVDE dogururdu ([[ikiz-tanim-sessiz-ayrisma]]) — index.html'deki kuratorluk
  -- (TANINMIS_MARKALAR + MARKA_ALIAS + cip evreni) degistiginde uc SESSIZCE ayrisirdi.
  -- Bunun yerine kanonik deger SENKRON ANINDA, deponun TEK KAYNAGINDAN
  -- (marka_model_build.marka_uyelikleri — ana sayfa filtresinin ta kendisi) turetilip
  -- ONCEDEN yazilir. Uc yalnizca hazir degeri okur; yeni bir kural OGRENMEZ.
  --
  -- BICIM: json.dumps(uyeler, kompakt ayirac). SIRA marka_uyelikleri'nden gelir (urunun
  -- kendi `marka` dizisinin sirasi); UYELIK anlami siradan BAGIMSIZDIR.
  --
  -- 🔴 HASH'e KARISMAZ (konfigur/taban_fiyat deseni, tur/stokta/uyum'un TERSI) — BILEREK:
  -- deger yalnizca urunun `marka` dizisine DEGIL, index.html'deki KURATORLUGE de baglidir.
  -- Yeni bir marka TANINMIS_MARKALAR'a eklendiginde HICBIR urunun hash'i degismez; icerik
  -- upsert'ine baglansaydi kolon o urunler icin SONSUZA DEK BAYAT kalirdi ve uc, cipi yeni
  -- markaya basan musteriye BOS sayfa dondururdu. Bu yuzden HEDEFLI UPDATE + TAM DIFF
  -- (d1-sync.marka_kanon_plan / sema_plan): her senkron urunler.json'dan turetilen HEDEFI
  -- D1'dekiyle karsilastirir, kuratorluk degisimi de yakalanir. Yan fayda: content-rewrite
  -- ve FTS thrash uretmez (hs'e dokunulmaz).
  --
  -- 🔴 FAIL-CLOSED YONU "ATLA", "BOSALT" DEGIL: katlama tek kaynagi (index.html / cip
  -- indeksi) okunamazsa d1-sync bu kolonun senkronunu GURULTULU ATLAR ve eski degeri
  -- OLDUGU GIBI birakir. Hedefleri bos kabul edip '[]' yazmak, TEK bir okuma hatasinda
  -- TUM katalogu marka cipinden dusururdu — bayat deger, bos degerden iyidir.
  marka_kanon TEXT NOT NULL DEFAULT '[]',
  -- KANONIK MODEL UYELIGI — urunun UYE OLDUGU /marka/<marka>/<model>/ SAYFALARININ kanonik
  -- ETIKETLERI (cip etiketiyle AYNI metin), JSON dizi. '[]' = hicbir yayimlanan model
  -- kovasina uye degil. marka_kanon'un MODEL EKSENINDEKI IKIZI — ayni sinif, ayni desen.
  --
  -- NEDEN VAR (OLCULEN SESSIZ HATA, 5 Agu 2026): uctaki `model` kolu degeri `uyum[].model`
  -- alaninda TAM ESITLIKLE ariyor (uyum bossa `marka[]`e dusuyor); site ise modeli KUSAK/
  -- VARYANT duzeyinde KATLIYOR (index.html modelEsler + kusakTabanlari: "Fiesta ST" -> Fiesta,
  -- "T4"/"T5" -> Transporter, "Golf 4"/"Golf Mk4"/"Golf IV" -> Golf). Olculdu (bu depoda,
  -- 18.362 urun · 553 yayimlanan model kovasi): 96 kovada sayfa ile uc suzgeci AYRISIYOR,
  -- 390 urun-kalemi musteri MODEL CIPINE BASINCA KAYBOLUYOR (en agiri Volkswagen/Transporter
  -- 99, Opel/Astra 49, Volkswagen/Golf 17, Renault/Megane 11). Site dogru gosterir, cip
  -- kaybeder, hicbir sey kirmizi yanmaz — marka ekseninde 4 Agu'da kapatilan sinifin AYNISI.
  --
  -- 🔴 UC BUNU HAM `model`in YERINE DEGIL, BIRLESIM OLARAK OKUR. Sebep OLCULDU (varsayilmadi):
  -- ucun model ekseninin bugun eslesebildigi HAM jeton evreni 2.120 jeton / 14.796 urun-kalemi;
  -- bunlarin 1.572'si (5.572 kalem) bu kolonda HIC GECMEZ (kolon yalnizca 549 YAYIMLANAN
  -- kova etiketini tasir). Dahasi marka ekseninin aksine kanon burada hamin UST KUMESI DEGIL:
  -- "ham eslesiyor ama kanon eslesmiyor" 16 kova / 276 kalem (Sierra 129 — Marin'de deniz
  -- parca markasi, otomobilde model). WHERE'i bu kolona CEVIRMEK toplu OLU LINK uretirdi;
  -- BIRLESIM ise sayfa<->suzgec kaybini 390 -> 0 indirir (olculdu).
  --
  -- KAYNAK + IKINCI TABLO YASAGI: deger SAYFA URETICISININ KENDI YUKLEMINDEN turer
  -- (marka_model_build.gruplandir -> kova["urunler"] + yayimlanir_mi + kanonik gosterim);
  -- yani kusak katlamasi, rozet kapisi ve model-olmayan cift yargilari OLDUGU GIBI gecerlidir.
  -- Worker'a ikinci bir katlama govdesi KOPYALANMAZ ([[ikiz-tanim-sessiz-ayrisma]]).
  -- YAYIMLANMAYAN kova BILEREK DISARIDA: etiketi mimarin KAPATTIGI bir sayfanin adidir
  -- (`Focus ST`, Audi altindaki `Golf`); kanonik deger diye yazilsaydi kapali sayfayi uc
  -- tarafindan geri acardi. Urun KAYBOLMAZ — kusak katlamasi onu ANA kovaya zaten koyar
  -- (olculdu: `Fiesta ST` tasiyan 14 urunun 14'unde deger `Fiesta`, `T4` 27/27 + `T5` 39/39
  -- `Transporter`). Cip evreni de bu kumenin ALTINDADIR (olculdu: cip \ yayimlanan = 0).
  --
  -- BICIM: json.dumps(SIRALI etiketler, kompakt ayirac). SIRA ALFABETIK — marka_kanon'un
  -- aksine urunun kendi dizisinden gelen dogal bir sira YOK; sirasiz birakilsaydi kova
  -- yineleme sirasi degistiginde metin degisir ve HER senkron sahte UPDATE uretirdi.
  --
  -- 🔴 HASH'e KARISMAZ + HEDEFLI UPDATE (marka_kanon/konfigur/taban_fiyat sinifi): deger
  -- urunun kendi alanlarina DEGIL, index.html kuratorlugune (TANINMIS_MARKALAR, MODEL_ALIAS,
  -- KUSAK_*) ve KATALOGUN TAMAMINA baglidir (kova esigi ESIK=3 ve kanonik gosterim, o
  -- kovadaki TUM urunlerin yazimlarindan turer). Icerik upsert'ine baglansaydi baska bir
  -- urunun eklenmesi bu urunun degerini degistirir ama hash'i AYNI kalir -> kolon SONSUZA
  -- DEK bayat kalirdi. Bu yuzden TAM DIFF (d1-sync.model_kanon_plan / sema_plan).
  --
  -- 🔴 FAIL-CLOSED YONU "ATLA", "BOSALT" DEGIL (marka_kanon ile birebir): tek kaynak
  -- okunamazsa senkron GURULTULU ATLANIR ve eski deger OLDUGU GIBI kalir. Hedefleri bos
  -- kabul edip '[]' yazmak, TEK bir okuma hatasinda TUM katalogu model cipinden dusururdu.
  model_kanon TEXT NOT NULL DEFAULT '[]',
  -- MARKA ARAMA UYELIGI (5 Agu 2026) — `?q=<marka>` kolunun UCTA cozulebilmesi icin gereken
  -- deger: urunun MARKA SORGUSUYLA eslesecegi marka adlari (JSON dizi).
  --
  -- OLCULEN SESSIZ HATA: uctaki `?q=` kolu `hs` uzerinde ALT-DIZE aramasi yapiyor; marka
  -- adiyla yapilan sorgu bu yuzden marka SAYFASINDAN cok daha fazla urun donduruyor
  -- ("Mandali" -> MAN, "Havalandirma" -> Haval, "43mm" -> 3M, "Land Rover" -> Rover).
  -- Site tarafi 8913db28 ile duzeltildi (fark 74 marka/6.089 kalem -> 20/75) ama CANLI arama
  -- UCTAN geliyor (index.html EDGE_KATALOG -> Worker /ara): merge sonrasi bile olculdu
  -- `?q=MAN` = 3539, `?q=Haval` = 581. Yani musteri HALA eski sonucu goruyor.
  --
  -- 🔴 `model_kanon` ILE AYNI SINIF, FARKLI HUKUM: model_kanon MODEL ekseninde ham
  -- `uyum[].model` ile BIRLESIM olarak okunur (kanon, hamin UST KUMESI DEGIL). Bu kolon
  -- MARKA eksenindedir ve ham `marka` esitligini KAPSAR (olculdu: birlesim 0 kalem ekler)
  -- -> uc bunu TEK BASINA okur. Iki kolonun UCTAKI OKUMA KURALI AYNI DEGILDIR.
  --
  -- 🔴 NEDEN AYRI KOLON, NEDEN `marka_kanon` GENISLETILMEDI (mimar karari, olculu):
  -- `marka_kanon` UYELIK tanimini tasir ve anasayfa CIPINI besler; ona baslik uyumu
  -- eklenseydi cip sayfadan FAZLA urun sayar ve marka-invaryant-kapisi.py'nin FILTRE ekseni
  -- bozulurdu. Iki kolon arasindaki iliski `marka_arama ⊇ marka_kanon` olarak nobetlenir
  -- (tools/marka-arama-d1-test.py, S ekseni) — ihlal KIRMIZI yanar.
  --
  -- 🔴 DEGER IKINCI KEZ TANIMLANMAZ: aday markalar urunun IKI tek kaynagindan gelir
  -- (marka_model_build.marka_uyelikleri = sayfa/cip yuklemi · arama.baslik_marka_uyumlari =
  -- baslikta TAM KELIME) ve kolona yazilmadan once GECIS YUKLEMININ TA KENDISINDEN
  -- (arama.marka_sorgusu_esler) gecirilir. Yuklem degisirse kolon KENDILIGINDEN izler;
  -- katlama/jetonlama govdesi burada YENIDEN YAZILMAZ ([[ikiz-tanim-sessiz-ayrisma]]).
  --
  -- 🔴 ALIAS YAZIMLARI DA GIRER (5 Agu, MIMAR HUKMU): kolon "hangi marka SORGULARIYLA
  -- eslesir" degerini tasir, yalniz kanonik adi DEGIL. Site `?q=Vauxhall` sorgusunu Opel'e
  -- KATLAR ve Opel'in TAM kumesini dondurur; kolon alias yazimini tasimasaydi uc o sorguyu
  -- HIC cozemez ve musteri 493 urunluk bir markayi canli aramada BULAMAZDI. Alias tablosunu
  -- uca KOPYALAMAK ise ikiz tanim olurdu. Bu yuzden alias, kanonigi tasiyan HER satira
  -- eklenir (yalniz `marka[]`inda o yazim GECEN satirlara degil — site kumesi kanonigin
  -- TAMAMIDIR). Kaynak: index.html MARKA_ALIAS + AYNI marka-adi yargisi
  -- (d1-sync.marka_alias_tersi). `marka_kanon` BUNDAN ETKILENMEZ: cip/sayfa evreni kanonik
  -- kalir, marka-invaryant-kapisi.py FILTRE ekseni bozulmaz.
  --
  -- HASH'e KARISMAZ + HEDEFLI UPDATE (marka_kanon/model_kanon ile AYNI gerekce): deger
  -- urunun `marka` dizisine oldugu kadar BASLIGINA ve index.html kuratorlugune de baglidir;
  -- icerik upsert'ine baglansaydi kuratorluk degisimi hicbir hash'i degistirmez ve kolon
  -- SONSUZA DEK bayat kalirdi. FAIL-CLOSED YONU "ATLA", "BOSALT" DEGIL (ayni gerekce).
  marka_arama TEXT NOT NULL DEFAULT '[]',
  -- UYUM (arac uyumlulugu) — JSON dizi, ogeler {marka,model,motor,yil,oem} (arama.UYUM_ALANLARI).
  -- '[]' = uyum bilgisi YOK. Veri urunler.json "uyum" alaninda YASIYORDU (olculdu 2026-08-02:
  -- 16.874 kaydin 13.040'inda DOLU) ama d1-sync'in alan listesinde HIC yoktu -> D1'e, oradan
  -- Ege'ye ULASMIYORDU: musteri "Passat B8 2.0 TDI'ye uyar mi" diye sorunca bot cevaplayamiyordu
  -- (site urunu dogru gosterir, Ege goremez = sessiz satis kaybi).
  -- KAYNAK + FAIL-CLOSED: arama.uyum_kanonik(u) — bicimsiz/sozluk disi/mukerrer oge tasiyan ya da
  -- `marka` ikizi ayrismis (K5) her kayit '[]' olur; tools/uyum-kapisi.py ayni veriyi KIRMIZI yakar,
  -- yani sessiz KALMAZ. BICIM: json.dumps(..., sort_keys=True, kompakt ayirac) — d1-sync.uyum_metin();
  -- `marka`nin JSON-dizi deseni + konfigur'un kanoniklestirme deseni (anahtar sirasi degisimi sahte
  -- UPDATE uretmesin).
  -- 🔴 HASH'E GIRER (tur/stokta/altkategori deseni; taban_fiyat/konfigur'un TERSI): alan PUBLIC
  -- urunler.json'da yasar, yani CI de yerel de AYNI degeri gorur ([[d1-baski-hash-thrash]]'in gizli
  -- kayit sorunu burada YOK) ve icerik upsert'i (KOLONLAR + satir_sql) ile yazilir. Hash
  -- kapsamasaydi bir urunun uyum listesi degistiginde hash AYNI kalir, diff_plan satiri
  -- "degismemis" sayar ve D1'e HIC YAZMAZDI -> Ege bayat uyum servis eder, hicbir alarm calmaz.
  -- KANONIK deger yazilir (ham degil): hash'in gordugu deger ile kolona giden deger AYNI
  -- fonksiyondan (uyum_kanonik) gelir -> "hash degisti ama kolon degismedi" ayrismasi imkansiz.
  uyum      TEXT NOT NULL DEFAULT '[]',
  fiyat     TEXT NOT NULL DEFAULT '',
  gorsel    TEXT,                         -- gorseller[0] (kart kapagi)
  parametrik INTEGER NOT NULL DEFAULT 0,
  -- PARAMETRIK TABAN FIYAT (TL, tam sayi). Parametrik ("olcuye ozel", sari seri) urunun
  -- public fiyat'i BOS ('') — taban fiyat jenerator/urunler/<id>.json tabanFiyatTL'de yasar
  -- ve site kartinda "X TL'den baslayan" olarak build.py'nin taban-fiyatlar.js'inden gelir.
  -- Ege (WhatsApp botu) urunu D1'den okur; bu kolon olmadan parametrik urunde fiyat gormez,
  -- saniyeler icinde kartla kapanacak siparisi insana devreder (sessiz satis kaybi). 0 =
  -- taban yok (normal urun ya da tabanFiyatTL null) -> Ege fiyat gostermez (mevcut davranis).
  -- KAYNAK: d1-sync.py taban_fiyat_haritasi() jenerator/urunler/<id>.json'dan okur (git'te
  -- var; CI'da da erisilir). taban-fiyatlar.js DEGIL (o gitignore/build ciktisi). HASH'e
  -- KARISMAZ: hedefli UPDATE (taban_senkron_sql) ile senkronlanir (baski_senkron_sql deseni),
  -- boylece taban degisimi content-rewrite/FTS-thrash uretmez, D1 yazma limitine yuklenmez.
  taban_fiyat INTEGER NOT NULL DEFAULT 0,
  -- KONFIGUR SEMASI (JSON metin, kanonik: sort_keys + kompakt ayirac). "Olcuye ozel dekor"
  -- (Skan Art / *-serit-dekoratif-figur) urununun boy araligi + fiyat capalari + malzeme
  -- katsayilari. Bugune kadar bu veri YALNIZ Worker bundle'indaydi (shop/src/konfigurlar.js,
  -- tools/konfigur-bundle-kapisi.py ureten artefakt) -> urun D1'e OTOMATIK (pre-push hook)
  -- girerken sema ELLE uretilip Worker ELLE deploy edilmek zorundaydi. IKI KAYNAK = iki elle
  -- adim; 30 Tem'de ikisi de atlandi (biri urunu karta kapali birakti, digeri CI'i durdurup
  -- 23 urunun yayinini blokladi). Kolon o ikinci kaynagi D1'e tasir.
  -- '' (bos) = urun konfigurlu DEGIL (katalogun ~%99,9'u) ya da konfigur verisi BOZUK
  -- (bozukta bilerek BOSALTILIR: Worker fail-closed 400 -> WhatsApp; "siparis kaybetmek
  -- yanlis tahsilattan iyidir" — bkz. shop/src/konfigur-beklenen.js).
  -- KAYNAK: d1-sync.py konfigur_haritasi_d1(), urunler.json'daki "konfigur" alanindan;
  -- dogrulama + sayi normalizasyonu konfigur-bundle-kapisi.py'nin AYNI fonksiyonlariyla
  -- yapilir (bundle ile D1 insaatan ayrisamaz).
  -- 🔴 HASH'e KARISMAZ (arama.urun_hash konfigur'u GORMEZ — olculdu): icerik-upsert yoluna
  -- konsaydi konfigur degisen urunun hash'i AYNI kalir, satir yeniden yazilmaz ve D1 SESSIZCE
  -- eskimis sema servis ederdi. Bu yuzden taban_fiyat deseni: HEDEFLI UPDATE
  -- (konfigur_senkron_sql / konfigur_plan) — content-rewrite ve FTS thrash uretmez.
  konfigur  TEXT NOT NULL DEFAULT '',
  hs        TEXT NOT NULL,                -- SITE aramasi (arama.py haystack — JS ile birebir)
  -- BASKI ONERISI (siparis yonetimi paketi): gizli .urun-kaynaklari.json'daki "baski"
  -- alanindan d1-sync.py DOLDURUR (public urunler.json'a YAZILMAZ — D1 ozeldir, sizinti degil).
  -- Yonetim sayfasindaki baski fisi bunu gosterir; bos ise malzeme bazli fallback devreye girer.
  baski     TEXT NOT NULL DEFAULT '',

  -- FAZ 2 — EGE tarafi. Hepsi AYNI satirda: ek kolon = ek SATIR YAZMASI DEGIL,
  -- yani D1'in gunluk 100.000 yazma limitine etkisi YOK (urun basina hala 5 satir).
  -- Ege'nin metni site'ninkinden ayri normalize edilir (nrm: alfanumerik olmayan ->
  -- bosluk), o yuzden hs'e bindirilemez.
  aciklama  TEXT NOT NULL DEFAULT '',     -- Ege'ye giden urun satiri icin (ham metin)
  ege       TEXT NOT NULL DEFAULT '',     -- urune ozel Ege notu (urunler.json "ege")
  hs_baslik      TEXT NOT NULL DEFAULT '',  -- nrm(baslik)            -> skor +3
  hs_baslik_kok  TEXT NOT NULL DEFAULT '',  -- ayni metin, kelimeler kokune cevrilmis
  hs_govde       TEXT NOT NULL DEFAULT '',  -- nrm(id+baslik+kategori+marka+aciklama) -> +1
  hs_govde_kok   TEXT NOT NULL DEFAULT '',  -- ayni metin, kelimeler kokune cevrilmis

  -- ATOMIK YAYIN (31 Tem) — "karti gorunen urun asla 404 vermez".
  -- OLCULEN PENCERE (bu kolonun VAR OLMA SEBEBI, ham sayilar muhendis raporunda):
  --   .git/hooks/pre-push d1-sync'i push'tan ONCE kosar -> urun D1'e girer; Pages deploy'u
  --   ise CI'nin sonunda biter. Son 8 basarili kosumda push -> canli MEDYAN 593 sn (9,9 dk),
  --   max 740 sn. CI KIRMIZI olursa pencere CI kirmizi kaldigi surece SURER: 31 Tem
  --   run#1079..1082 arasi 3.241 sn (54 dk) olculdu, o sure boyunca 98 urun D1'DEYDI ama
  --   /urun/<id>/ 404 donuyordu. 31 Tem 07:33Z'de CANLI teyit: 8/8 yeni id D1'de, 3/3
  --   ornek sayfa HTTP 404.
  -- SEMANTIK:
  --   yayinda=0  TASLAK — satir D1'de var (senkron gecikmesin) ama HICBIR KESIF
  --              yuzeyinde (arama/katalog/Ege) GOSTERILMEZ. Yeni satir DAIMA 0 girer.
  --   yayinda=1  YAYINDA — o id'nin /urun/<id>/ sayfasi CANLIDA 200 dondugu FIILEN
  --              dogrulandiktan sonra tools/yayin-kapisi.py yazar. Tek yon: 0 -> 1.
  --   release_id yayina alan commit SHA'si (denetim izi; hangi deploy yayinladi).
  -- 🔴 CONTENT UPSERT'E KARISMAZ: d1-sync KOLONLAR listesinde YOK -> mevcut (yayinda=1)
  --   bir urunun icerigi degisince satir yeniden yazilir ama yayinda 1 KALIR. Aksi halde
  --   her toplu duzeltme TUM katalogu ~10 dk boyunca Ege'den gizlerdi (sessiz satis kaybi)
  --   — ve 404 riski de YOKTUR: id degismedigi surece sayfa zaten canlidadir.
  yayinda    INTEGER NOT NULL DEFAULT 0,
  release_id TEXT NOT NULL DEFAULT '',

  -- ── TICARI HAL (31 Tem, HocA talebi) — Ege fiziksel urunu ALGILASIN ────────────────
  -- Katalogda iki AYRI ticari hal var: (a) OZEL URETIM — siparis uzerine uretilir, stok
  -- kavrami UYGULANMAZ (katalogun ~%99,7'si); (b) FIZIKSEL — hazir ticari mal (tekne
  -- boyasi, vernik, maskeleme bandi...), 3D baskiyla URETILMEZ, fiyati SABIT ve TUKENIR.
  -- Bu ayrim bugune dek YALNIZ urunler.json + build.py sayfa uretiminde vardi; D1'de HIC
  -- YOKTU -> Ege (WhatsApp botu, katalogu D1'DEN okur) fiziksel urunu ozel uretim sanip
  -- "size uretiriz" der ya da hicbir sey oneremez.
  --
  -- tur: '' = OZEL URETIM (varsayilan) · 'fiziksel' = hazir ticari mal.
  --   FAIL-CLOSED: yalniz TAM 'fiziksel' dizesi bu hali acar (build.py render_product ile
  --   AYNI kural; taninmayan deger '' olur). KAYNAK: arama.tur_kanonik().
  --
  -- stokta: UC DEGERLI (bilerek INTEGER, bilerek 3 hal).
  --   -1 BILINMIYOR    urunler.json'da `stokta` alani YOK. Ozel uretim urununun normal
  --                    hali. Fiziksel urunde gorulurse VERI EKSIK -> stok VAAT EDILMEZ.
  --    0 STOKTA DEGIL  alan VAR ama true DEGIL (false ya da taninmayan deger).
  --    1 STOKTA        alan tam olarak boolean true — "stokta" diyebilen TEK deger.
  --   🔴 NEDEN INTEGER, NEDEN TEXT DEGIL: bu kolonu okuyan uc taraf (Ege/Worker) JS'tir ve
  --   JS'te Boolean('0') === true. TEXT affinity'sinde SQLite tamsayi 0'i '0' METNINE
  --   cevirir -> TUKENMIS urun uc tarafta STOKTA gorunur = musteriye yanlis vaat, sessiz.
  --   INTEGER affinity'de deger 0 kalir ve yanlislik uretilemez. (Kabul testi:
  --   tools/stok-d1-kapisi.py — PRAGMA tipi + geri-okuma tipi + JS dogruluk ekseni.)
  --   🔴 NEDEN IKILI (0/1) DEGIL: ikilide "alan hic yok" ile "acikca tukendi" AYNI hucreye
  --   duser. 0'i "tukendi" okuyan uc 15.930 ozel uretim urununu STOKTA DEGIL ilan eder;
  --   0'i "bilinmiyor" okuyan uc GERCEKTEN tukenmis urunu satar. Iki hata da sessizdir.
  --
  -- 🔴 HASH'E GIRER (taban_fiyat/konfigur deseninin AKSINE — bilerek): bu iki alan PUBLIC
  -- urunler.json'da yasar, yani CI de yerel de AYNI degeri gorur (baski'nin gizli kayittan
  -- gelme sorunu YOK) ve icerik upsert'i (KOLONLAR + satir_sql) ile yazilir. Hash'e
  -- girmeseydi "tukendi" isareti hash'i degistirmez, satir yeniden yazilmaz ve D1 eski
  -- stok halini KALICILASTIRIRDI. KAYNAK: arama.urun_hash().
  tur       TEXT NOT NULL DEFAULT '',
  stokta    INTEGER NOT NULL DEFAULT -1
);

-- Kategori/marka filtresi + siralama icin.
CREATE INDEX IF NOT EXISTS urunler_seq  ON urunler(seq DESC);
CREATE INDEX IF NOT EXISTS urunler_kat  ON urunler(kategori, seq DESC);

-- ATOMIK YAYIN indeksleri (urunler_yayin / urunler_yayin_kat): okuma tarafi WHERE'ine
-- `yayinda=1` girince yukaridaki iki indeksin ONEK'i bozulur (katalogD1 OFFSET taramasi
-- indeks yerine tam taramaya duserdi); yayinda ONDE olan iki indeks o siralamayi korur.
-- 🔴 DDL'leri BU DOSYADA DEGIL, d1-sync.py YAYIN_INDEKS listesindedir ve kolon_goc()'un
-- ALTER'larindan SONRA kosar. NEDEN (olculdu 31 Tem, canli D1): bu dosya --sema'da
-- kolon gocunden ONCE uygulanir; tablo zaten var oldugu icin CREATE TABLE IF NOT EXISTS
-- atlanir, dolayisiyla `yayinda` kolonu henuz YOKTUR ve indeks ifadesi
-- "no such column: yayinda ... SQLITE_ERROR" ile TUM sema kosumunu dusurur.

-- Arama indeksi. content='urunler' -> metin iki kez saklanmaz (yalnizca indeks yazilir).
CREATE VIRTUAL TABLE IF NOT EXISTS urunler_fts USING fts5(
  hs,
  content='urunler',
  content_rowid='rid',
  tokenize='trigram'
);

-- FTS'i tabloyla senkron tutan tetikleyiciler (elle bakim = sessiz ayrisma riski).
-- DROP+CREATE (IF NOT EXISTS DEGIL): tanim degisince eskisi sessizce KALIRDI.
-- Tetikleyici yeniden kurmak bedava; --sema her calistiginda guncel tanim yuklenir.
DROP TRIGGER IF EXISTS urunler_ai;
DROP TRIGGER IF EXISTS urunler_ad;
DROP TRIGGER IF EXISTS urunler_au;

CREATE TRIGGER urunler_ai AFTER INSERT ON urunler BEGIN
  INSERT INTO urunler_fts(rowid, hs) VALUES (new.rid, new.hs);
END;
CREATE TRIGGER urunler_ad AFTER DELETE ON urunler BEGIN
  INSERT INTO urunler_fts(urunler_fts, rowid, hs) VALUES ('delete', old.rid, old.hs);
END;

-- WHEN old.hs <> new.hs — FTS'i SADECE arama metni degistiyse tazele.
-- Kosulsuz hali her UPDATE'te 4 FTS shadow satiri yazdiriyordu; oysa fiyat/gorsel/
-- aciklama degisiminde hs ayni kalabilir ve FTS'in tazelenmesine GEREK YOKTUR
-- (rowid sabit, indekslenen metin ayni). OLCULDU (6.086 urun, FAZ 2 gocu, hs hic
-- degismedi): urun basina yazma 5 -> **2** (tahmin 1'di; kalan 1 satir tablo/indeks
-- maliyeti). Toplam 30.432 yerine 12.173. 50k urunde "hs'e dokunmayan" toplu
-- degisiklik 250.000 (limitin 2,5 kati) yerine ~100.000 -> limitin sinirinda ama
-- icinde. hs degisirse tetikleyici normal calisir (o zaman yine 5).
CREATE TRIGGER urunler_au AFTER UPDATE ON urunler WHEN old.hs <> new.hs BEGIN
  INSERT INTO urunler_fts(urunler_fts, rowid, hs) VALUES ('delete', old.rid, old.hs);
  INSERT INTO urunler_fts(rowid, hs) VALUES (new.rid, new.hs);
END;

-- Senkron durumu (son calisma, urun sayisi) — tanilama icin.
CREATE TABLE IF NOT EXISTS senkron (
  anahtar TEXT PRIMARY KEY,
  deger   TEXT NOT NULL
);

-- SHOP — self-servis siparisler (shop/ worker'i yazar; is paketleri tools/paket-shop-odeme.md
-- + tools/paket-shop-kargo.md).
-- Katalog senkronundan BAGIMSIZ: d1-sync.py bu tabloya dokunmaz, urun silinse de siparis kalir.
-- durum akisi: bekliyor -> odendi | basarisiz | incele ; havale-bekliyor -> odendi
--   YONETIM ilerlemesi (siparis yonetimi paketi, anahtar korumali /api/shop/yonet/durum):
--     odendi -> uretimde -> kargolandi -> tamamlandi ; her durum -> iptal
--     (kargolandi'ya SADECE /yonet/kargo ucundan gecilir — kargo firma+kod zorunlu; boylece
--      takip kodsuz 'kargolandi' satiri olusmaz. Gecis tablosu shop/src/yonet.js IZINLI'de.)
--   'odendi'          kartta SADECE iyzico retrieve dogrulamasindan gecince (worker /donus);
--                     havalede elle onay — yonetim sayfasi (havale-bekliyor->odendi) ya da
--                     shop/KURULUM.md'deki wrangler komutu (ayni gecis, AYNI kosul: tek yol).
--   'incele'          retrieve altyapi hatasi VEYA tutar/kimlik uyusmazligi (elle bak)
--   'havale-bekliyor' musteri Havale/EFT secti; para HENUZ gorulmedi, uretim BASLAMAZ
--   'uretimde'        uretim basladi (yonetim) ; 'kargolandi' kargo firma+kod girildi (yonetim)
--   'tamamlandi'      teslim edildi ; 'iptal' iptal (her durumdan)
CREATE TABLE IF NOT EXISTS siparisler (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  siparis_no      TEXT NOT NULL UNIQUE,   -- PR-yyMMdd-HHmmss-XXX (conversationId/basketId olarak iyzico'ya gider)
  token           TEXT UNIQUE,            -- iyzico checkout form token — idempotens anahtari (havalede NULL)
  tarih           TEXT NOT NULL,          -- ISO 8601 UTC
  durum           TEXT NOT NULL DEFAULT 'bekliyor',
  -- Para KURUS tamsayisinda saklanir: katsayi kusurati aynen korunur (Okan, 16 Tem — yuvarlama
  -- YOK), REAL saklansa kayan nokta tutari sessizce kaydirirdi. 43290 = 432,90 TL.
  -- TAHSILAT = tutar_kurus + kargo_kurus (iyzico paidPrice bununla karsilastirilir).
  tutar_kurus     INTEGER NOT NULL,       -- SUNUCUDA hesaplanan URUN toplami (kurus, kargo HARIC)
  -- KARGO (Okan, 16 Tem — KESIN): urun toplami < 2.500,00 TL -> 25000 (250,00 TL);
  -- >= 2.500,00 TL (tam 2.500 dahil) -> 0. Kural tek kaynagi /secenekler.js kargoKurus().
  -- Eski satirlarda 0 kalir (o siparislerde kargo tahsil edilmedi) — mevcut veri bozulmaz.
  -- DIKKAT: tablo canlida zaten kuruluysa CREATE atlanir; kolonu d1-sync.py --sema
  -- ALTER ile tamamlar (kolon_goc — urunler'deki FAZ 2 gocuyle ayni mekanizma).
  kargo_kurus     INTEGER NOT NULL DEFAULT 0,
  -- KDV (Okan KESIN %20, 16 Tem gece): fiyatlar KDV DAHIL, tahsilat degismez — bu kolon
  -- fatura/kayit icin dokumdur: kdv_kurus = brut(tutar+kargo) - round(brut*100/120).
  -- Oran tek kaynak /secenekler.js KDV_YUZDE. Eski satirlarda 0 kalir (dokum yoktu).
  kdv_kurus       INTEGER NOT NULL DEFAULT 0,
  odeme_yontemi   TEXT NOT NULL DEFAULT 'kart',  -- 'kart' (iyzico) | 'havale'
  -- Sozlesme onayi ISPAT KAYDI (kalem 9): /baslat'ta onay yoksa 400; onay aninin ISO
  -- damgasi. Eski satirlarda '' (o siparisler onay kutusu oncesi).
  sozlesme_onay   TEXT NOT NULL DEFAULT '',
  urunler         TEXT NOT NULL,          -- JSON [{id,baslik,filament,renk,adet,birim_kurus,tutar_kurus}]
  filament        TEXT NOT NULL DEFAULT '',
  renk            TEXT NOT NULL DEFAULT '',
  iyzico_odeme_id TEXT,
  musteri_ad      TEXT NOT NULL DEFAULT '',
  musteri_tel     TEXT NOT NULL DEFAULT '',
  musteri_eposta  TEXT NOT NULL DEFAULT '',
  musteri_adres   TEXT NOT NULL DEFAULT '',
  -- KARGO (siparis yonetimi paketi): /yonet/kargo ucu firma+kodu yazar, durum 'kargolandi'ya
  -- cekilir + musteriye kargo e-postasi tetiklenir. Eski satirlarda '' (kargolanmamis).
  kargo_firma     TEXT NOT NULL DEFAULT '',
  kargo_kodu      TEXT NOT NULL DEFAULT '',
  -- DURUM GECMISI: her durum degisiminde AYNI satira eklenen kompakt JSON denetim izi
  -- [{"d":"uretimde","z":"ISO"}...] — ek SATIR yazmaz (D1 gunluk limit etkisi yok),
  -- yonetim sayfasi gecmisi gosterir. Eski satirlarda '' .
  durum_gecmisi   TEXT NOT NULL DEFAULT '',
  -- REKLAM ROI OLCUMU (reklam-roi-sistemi.md Faz 0): odeme ONCESI (/baslat) tarayicidan
  -- yakalanan atif kimlikleri, kompakt JSON: {ga_client_id, fbp, fbc, utm_source, utm_medium,
  -- utm_campaign, utm_id}. redirect'te URL param/cerez DUSER -> order kaydina yazilir; purchase
  -- event (donus'ta, iyzico OK aninda) bunlari GA4 client_id / Meta fbp-fbc / UTM atfi icin okur.
  -- PII YOK (v1): email/telefon YAZILMAZ. Eski satirlarda '' (atif oncesi).
  atif            TEXT NOT NULL DEFAULT '',
  -- KANAL AYRACI (1 Agu 2026, Okan talebi): siparis HANGI kanaldan kapandi.
  --   'site'     -> pruvo3d.com self-servis akisi (shop/src/index.js /baslat) — VARSAYILAN
  --   'whatsapp' -> Ege botunun kapattigi siparis (shop/src/yonet.js /wa-siparis)
  -- DEFAULT 'site': ALTER anindan itibaren MEVCUT TUM satirlar dogru degeri alir (o siparislerin
  -- hepsi site akisindan geldi) -> geriye doldurma GEREKMEZ, rapor/ekran bozulmaz.
  -- 🔴 OLCUM: reklam Purchase olayi YALNIZ kanal='site' satirlarda tetiklenir (yonet.js
  -- durumDegistir KANAL kapisi). WhatsApp cirosu tarayicidan gecmez, `atif` bostur; GA4'e
  -- sentetik client_id ile gonderilseydi web disi ciro "direct" satis gibi gorunup site ROI
  -- raporunu sisirirdi.
  kanal           TEXT NOT NULL DEFAULT 'site',
  -- DIS SIPARIS NUMARASI: kaynak sistemin KENDI numarasi (Ege: PR-yyMMdd-HHmmss, sonek YOK).
  -- Bu tablonun `siparis_no`'su HER ZAMAN burada uretilir (PR-yyMMdd-HHmmss-XXX); dis_no
  -- yalnizca MUTABAKAT anahtaridir (Ege'nin Sheet kaydiyla eslesme) ve /wa-siparis ucunun
  -- IDEMPOTENS anahtaridir (ayni dis_no ikinci kez gelirse yeni siparis acilmaz).
  -- Site siparislerinde '' (bos = dis kaynak yok).
  dis_no          TEXT NOT NULL DEFAULT ''
);

-- 🔴 DIS NUMARA TEKILLIK INDEKSI BU DOSYADA DEGIL — d1-sync.py GOC_INDEKS kayit defterinde
-- (`siparisler_kanal_dis_no`). BURAYA KOYULMASI OLCULDU VE ARIZALIYDI (1 Agu 2026):
-- bu dosya kolon gocunden ONCE uygulanir; canlida `siparisler` ZATEN VAR oldugu icin
-- yukaridaki CREATE TABLE IF NOT EXISTS ATLANIR -> kanal/dis_no kolonlari HENUZ YOKTUR ->
-- "no such column: kanal" ile TUM `--sema` kosumu duser ve kolon_goc() HIC KOSMAZ:
-- kolonlar canliya ASLA eklenemez (tam tikanma, kendi kuyrugunu yiyen goc). urunler_yayin
-- indeksleri 31 Tem'de AYNI sebeple bu dosyadan cikarilmisti (bkz. 145. satir yorumu).
-- Dogru yer: ALTER'lardan SONRA kosan ve kurulusu DOGRULANAN GOC_INDEKS kaydi.
