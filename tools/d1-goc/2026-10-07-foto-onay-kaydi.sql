-- GOC: aydinlatma onayi kaydi (tek onay kutusu, metin surumu 2026-10-07-taslak-2).
-- foto_isler: onay ani + onaylanan metin surumu (musteri kolunda her onizleme satirina yazilir).
-- foto_uretim: ayni iki alan is satirindan kopyalanir (siparisle kalan onay kaydi).
-- tools/d1-sema.sql'deki CREATE TABLE IF NOT EXISTS VAR OLAN tabloya sutun eklemez; bu dosya
-- D1'e BIR KEZ uygulanir. Sunucu bu sutunlara HER musteri onizlemesinde yazar: uygulanmadan
-- once onizleme/siparis kuyrugu 500 doner (fail-closed) -> kod yayina cikmadan ONCE uygulanir.
ALTER TABLE foto_isler ADD COLUMN onay_tarih TEXT NOT NULL DEFAULT '';
ALTER TABLE foto_isler ADD COLUMN onay_surum TEXT NOT NULL DEFAULT '';
ALTER TABLE foto_uretim ADD COLUMN onay_tarih TEXT NOT NULL DEFAULT '';
ALTER TABLE foto_uretim ADD COLUMN onay_surum TEXT NOT NULL DEFAULT '';
