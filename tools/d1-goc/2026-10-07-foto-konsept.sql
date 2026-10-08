-- 2D KONSEPT TABLOSU (Okan 7 Eki 14:5x: "Nasıl olsun?" notu -> 2D sonuç nota göre). Foto + not ->
-- konsept görseli; onaylanan konsept 3D önizlemenin girdisi olur. Tablo yoksa konsept ucu KAPALI
-- (503, sağlayıcıya istek 0) — fail-closed; mevcut önizleme/sipariş yolu bu tabloya bağlı DEĞİLDİR.
-- Şema kaynağı: tools/d1-sema.sql (aynı tanım). Uygulama: mimar hükmü (canlı D1), bu dalda UYGULANMADI.
CREATE TABLE IF NOT EXISTS foto_konsept (
  konsept_no   TEXT PRIMARY KEY,
  oturum       TEXT NOT NULL,
  tur          TEXT NOT NULL,
  ziyaretci    TEXT NOT NULL,
  tarih        TEXT NOT NULL,
  asama        TEXT NOT NULL,
  gorev        TEXT NOT NULL DEFAULT '',
  son_kontrol  INTEGER NOT NULL DEFAULT 0,
  hazir_tarih  TEXT NOT NULL DEFAULT '',
  kredi        INTEGER NOT NULL DEFAULT 0,
  hata         TEXT NOT NULL DEFAULT '',
  is_no        TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_foto_konsept_oturum ON foto_konsept (oturum);
CREATE INDEX IF NOT EXISTS idx_foto_konsept_tarih ON foto_konsept (tarih);
