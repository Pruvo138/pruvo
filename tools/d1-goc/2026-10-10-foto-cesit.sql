-- GOC: foto cesit (TUR-C2a, 10 Eki; Okan 22:0x anahtarlik "a yazi ile, b figur olarak").
-- foto_isler.cesit: isin cesidi (VERI.cesitler; anahtarlik 'yazi'|'figur'); '' = turun varsayilan kolu (eski satir).
-- Sunucu dallanmasi (figurKolu) bu sutundan okunur; isGetir sutunu SECER ve onizleme satiri ona yazar:
-- uygulanmadan once onizleme/durum uclari 500 doner (fail-closed) -> kod yayina cikmadan ONCE uygulanir
-- (once onizleme D1, sonra canli D1).
ALTER TABLE foto_isler ADD COLUMN cesit TEXT NOT NULL DEFAULT '';
