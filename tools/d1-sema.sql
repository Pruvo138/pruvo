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
  hs        TEXT NOT NULL                 -- arama metni (arama.py haystack — JS ile birebir)
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
CREATE TRIGGER IF NOT EXISTS urunler_ai AFTER INSERT ON urunler BEGIN
  INSERT INTO urunler_fts(rowid, hs) VALUES (new.rid, new.hs);
END;
CREATE TRIGGER IF NOT EXISTS urunler_ad AFTER DELETE ON urunler BEGIN
  INSERT INTO urunler_fts(urunler_fts, rowid, hs) VALUES ('delete', old.rid, old.hs);
END;
CREATE TRIGGER IF NOT EXISTS urunler_au AFTER UPDATE ON urunler BEGIN
  INSERT INTO urunler_fts(urunler_fts, rowid, hs) VALUES ('delete', old.rid, old.hs);
  INSERT INTO urunler_fts(rowid, hs) VALUES (new.rid, new.hs);
END;

-- Senkron durumu (son calisma, urun sayisi) — tanilama icin.
CREATE TABLE IF NOT EXISTS senkron (
  anahtar TEXT PRIMARY KEY,
  deger   TEXT NOT NULL
);
