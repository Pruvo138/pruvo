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
--                 YERINE_YENISI:<id>, DUZELT_RED:<rc>, URUN_SILINECEK). Sessiz dusme YOK.
--
-- TEKIL SILME (2 Eyl 2026): alan='sil' satiri (deger=GEREKCE) ayni kuyruktan akar;
-- worker onu YALNIZ /urun-sil cift-onay ucundan yazar, uygulayici duzelt --toplu
-- {"id","sil"} + arsiv/urunler-arsiv.json ile isler. Sema DEGISMEDI (alan TEXT
-- serbesttir) — migration gerekmez. Yordam: tools/urun-silme-yordami.md.
--
-- Uygulama: npx wrangler d1 execute pruvo-katalog --remote --file tools/panel-ustyazim-sema.sql
-- (idempotent; mevcut tablolara DOKUNMAZ). Kaynak link / uyelik / STL yeri gibi gizli
-- alanlar bu kuyruga GIRMEZ (beyaz liste uygulayicinin icinde:
-- fiyat|baslik|aciklama|gorseller|sil).
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

-- panel_kaynak — PANEL-DOGUMLU URETICI KAYNAK LINKI (T2, gizli D1 duzlemi).
--
-- 🔴 NEDEN `urun_kaynak`'a YAZILMAZ: o tabloyu tools/d1-kaynak-sync.py gizli kayittan
-- diff-upsert + SILME ile yonetir — panelden oraya yazilan satir "gizli kayitta yok"
-- sayilip SONRAKI senkronda SILINIRDI ([[d1-bayat-yazici-silme]] sinifi). Ayri tablo =
-- semayla izolasyon (panel_ustyazim/d1-sync ile ayni desen); d1-kaynak-sync bu tabloya
-- ne okur ne yazar.
--
-- 🔒 GIZLILIK: bu tablo tabana (urunler.json) ve hicbir public yuzeye ISLENMEZ;
-- kuyruk beyaz listesine giremez. Okuyan tek yer yonetim uclari (yonet.js). Okuma
-- birlesimi: panel_kaynak satiri VARSA o kazanir (link='' = "cikarildi" golgesi —
-- sync'ten gelen linki de listeden dusurur), yoksa urun_kaynak. MaCiT'in mukerrer/
-- kaynak taramasi bu tabloyu DA sayar (kutu mutabakati, 30 Agu 2026).
CREATE TABLE IF NOT EXISTS panel_kaynak (
  id   TEXT PRIMARY KEY,
  link TEXT NOT NULL,
  ts   TEXT NOT NULL
);
