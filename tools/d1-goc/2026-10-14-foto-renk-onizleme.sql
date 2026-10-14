-- GOC: foto_renk_onizleme (④ TEK RENK ONIZLEMESI, Okan 14 Eki 2026 03:0x). Tek renk (Siyah/Beyaz/Gri) secilen
-- saglayici onizlemesinde 3D build onizlemede kurulur; koşucu modeli secilen renkte cizer. Tablo YOKKEN kod
-- fail-closed: ④ bugunku gibi (saglayici gorseli), /foto/renk 503, koşucu renk kuyrugu bos (tabloYok/TabloYok).
-- Siraya gerek yok (idempotent, IF NOT EXISTS); once onizleme D1, sonra canli D1. Sema kaynagi tools/d1-sema.sql.
CREATE TABLE IF NOT EXISTS foto_renk_onizleme (
  is_no        TEXT PRIMARY KEY,
  renk         TEXT NOT NULL,
  asama        TEXT NOT NULL,
  build_gorev  TEXT NOT NULL DEFAULT '',
  build_olcu   INTEGER NOT NULL DEFAULT 0,
  tarih        TEXT NOT NULL,
  son_kontrol  INTEGER NOT NULL DEFAULT 0,
  hata         TEXT NOT NULL DEFAULT '',
  guncel       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_foto_renk_onizleme_asama ON foto_renk_onizleme (asama, guncel);
