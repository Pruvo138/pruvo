-- GOC: foto kredi DILIM defteri (10 Eki; tavan = ZINCIR/DILIM TOPLAMI, koşum başı değil).
-- Olculen sorun: Kredi.taban koşum başı D1 toplamıydı -> tavan koşum başına; figür zinciri 2 koşum x 66 = 132
-- harcadı, tavan 70 "tuttu" sanıldı. tools/foto-ornek-uc-uca.py her yeni is_no'yu (ornek-onizleme POST'u ve
-- --devam-is) bu tabloya `--dilim` etiketiyle yazar; dilim harcanan = SUM(foto_kredi.kredi) WHERE is_no IN
-- (dilimin is_no'ları). YALNIZ ONIZLEME D1 (betigin yazim siniri); betik bu DDL'i kendisi de uygular
-- (IF NOT EXISTS, idempotent). Canli D1'e uygulanmaz (canlida ornek kredi zinciri kosmaz).
CREATE TABLE IF NOT EXISTS foto_kredi_dilim (dilim TEXT NOT NULL, is_no TEXT NOT NULL, tarih TEXT NOT NULL, PRIMARY KEY (dilim, is_no));
