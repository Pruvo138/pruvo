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
  hs        TEXT NOT NULL,                -- SITE aramasi (arama.py haystack — JS ile birebir)

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
