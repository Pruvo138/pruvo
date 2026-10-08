-- GOC: foto ek renk (Okan 8 Eki 13:3x: "4 renk secimi olmali, ilk renk ucretsiz, her + renk icin +100 TL";
-- 14:2x plaket/figur/bust: "Musteri 1-4 renk secsin").
-- foto_uretim: siparisin renk sayisi (saglayici renk adimi max_colors) + secilen renkler (JSON, operator icin).
-- tools/d1-sema.sql'deki CREATE TABLE IF NOT EXISTS VAR OLAN tabloya sutun eklemez; bu dosya
-- D1'e BIR KEZ uygulanir. Sunucu odenen siparisi kuyruga alirken bu sutunlara yazar: uygulanmadan
-- once uretim kuyrugu 500 doner (fail-closed) -> kod yayina cikmadan ONCE uygulanir.
ALTER TABLE foto_uretim ADD COLUMN renk_sayisi INTEGER NOT NULL DEFAULT 0;
ALTER TABLE foto_uretim ADD COLUMN renkler TEXT NOT NULL DEFAULT '';
