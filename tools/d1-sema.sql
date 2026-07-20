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
  marka     TEXT NOT NULL DEFAULT '[]',   -- JSON dizi
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
  hs_govde_kok   TEXT NOT NULL DEFAULT ''   -- ayni metin, kelimeler kokune cevrilmis
);

-- Kategori/marka filtresi + siralama icin.
CREATE INDEX IF NOT EXISTS urunler_seq  ON urunler(seq DESC);
CREATE INDEX IF NOT EXISTS urunler_kat  ON urunler(kategori, seq DESC);

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
  atif            TEXT NOT NULL DEFAULT ''
);
