-- FOTO FIYAT TABLOSU KALKAR -> ACILIS ANAHTARI (Okan 7 Eki 15:4x: "fiyat bu ürünlerin tamamında aynı
-- per cm/100tl"). Fiyat artik TEK formul (foto-uretim-veri.js VERI.fiyatKurus = en uzun boyut mm x 1000
-- kurus); turun acik/kapali hali `foto_acik`ta. Bu goc HICBIR turu ACMAZ: tablo bos kurulur, satir yok =
-- KAPALI. Eski `foto_fiyat` satirlari acilis anahtarina TASINMAZ (11:2x kapatmasi o satirlari silmisti;
-- acmak panelden "Aç" ile, bilincli). Uygulama: mimar hukmu (canli D1), bu dalda UYGULANMADI.
CREATE TABLE IF NOT EXISTS foto_acik (
  tur          TEXT PRIMARY KEY,
  acik         INTEGER NOT NULL DEFAULT 0,
  guncel       TEXT NOT NULL
);
DROP TABLE IF EXISTS foto_fiyat;
