-- panel_ustyazim — YONETIM PANELI YAZMA KUYRUGU (T1, mimar hakem hukmu 29 Agu 2026).
--
-- BU TABLO BIR "PARALEL GERCEK" DEGIL, BIR KUYRUKTUR: panel (Okan) satir yazar,
-- CI uygulayicisi (tools/panel-uygulayici.py) TEK uygulayici olarak kuyrugu
-- urunler.json TABANINA isler ve satiri damgalar. urunler.json TEK okuma kaynagi
-- olarak KALIR; site/build/D1 senkron zinciri bu tabloyu HIC okumaz.
-- d1-sync.py bu tabloya ne okur ne yazar (yalniz `urunler` + `senkron_kilit`) —
-- bayat-yazici ezmesi SEMAYLA imkansiz, yeni kapi/denetim katmani YOK.
--
-- hal UC DEGERLIDIR (iki kovali siniflama ucuncu sinifi yutar — olculmus sinif):
--   'beklemede' : panel yazdi, uygulayici henuz islemedi.
--   'islendi'   : tabana islendi (islendi_commit = urunler.json commit'i) ya da
--                 taban zaten esitti (sebep='TABAN_ZATEN_ESIT').
--   'hata'      : islenemedi; sebep kolonu NEDENI adiyla tasir (or.
--                 ALAN_BEYAZ_LISTE_DISI, FIYAT_BICIMI, PARAMETRIK_FIYAT, URUN_YOK,
--                 YERINE_YENISI:<id>, DUZELT_RED:<rc>). Sessiz dusme YOK.
--
-- Uygulama: npx wrangler d1 execute pruvo-katalog --remote --file tools/panel-ustyazim-sema.sql
-- (idempotent; mevcut tablolara DOKUNMAZ). Kaynak link / uyelik / STL yeri gibi gizli
-- alanlar bu kuyruga GIRMEZ (beyaz liste uygulayicinin icinde: fiyat|baslik|aciklama).
CREATE TABLE IF NOT EXISTS panel_ustyazim (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  urun_id        TEXT NOT NULL,
  alan           TEXT NOT NULL,
  deger          TEXT NOT NULL,
  yazan          TEXT NOT NULL DEFAULT 'panel',
  ts             TEXT NOT NULL,
  hal            TEXT NOT NULL DEFAULT 'beklemede',
  islendi_ts     TEXT,
  islendi_commit TEXT,
  sebep          TEXT
);
CREATE INDEX IF NOT EXISTS panel_ustyazim_hal ON panel_ustyazim (hal);
CREATE INDEX IF NOT EXISTS panel_ustyazim_urun ON panel_ustyazim (urun_id, alan);
