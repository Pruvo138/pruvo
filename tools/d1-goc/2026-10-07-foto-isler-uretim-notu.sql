-- GOC: foto_isler.uretim_notu ("Nasil olsun?" notu, <=300 karakter, temiz; e-posta/telefon RED).
-- tools/d1-sema.sql'deki CREATE TABLE IF NOT EXISTS VAR OLAN tabloya sutun eklemez; bu dosya
-- canli D1'e BIR KEZ uygulanir (bolum acilmadan once). Uygulanmadan once bos not yolu calisir
-- (sunucu sutunu yalniz not doluysa yazar), dolu not 500 doner -> acilis oncesi sart.
ALTER TABLE foto_isler ADD COLUMN uretim_notu TEXT NOT NULL DEFAULT '';
