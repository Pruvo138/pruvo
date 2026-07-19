-- OCI #1 — wa.me lead attribution: REF -> click-id (gclid/gbraid/wbraid) kalici eslemesi.
--
-- Landing (attribution-ref.js) paid oturumda REF uretir; lead aninda beacon
-- (POST /api/shop/ref) bu tabloya yazar. first-write-wins: REF PRIMARY KEY, worker
-- INSERT OR IGNORE kullanir -> ayni REF ikinci kez gelirse ilk kayit korunur.
--
-- Retention: ~90 gun (landing localStorage TTL + Google OCI tik penceresiyle uyumlu).
-- Prune opsiyonel/sonra (hacim dusuk); created_at indeksi o zaman kullanilir.
--
-- Veritabani: pruvo-katalog (binding KATALOG, id 3d99d15e-2342-4c23-9c2d-cb266f19c1ee).
-- REMOTE'A ELLE CALISTIRILIR (Okan/deploy kapisi) — shop dizininden:
--   npx wrangler d1 execute pruvo-katalog --remote --file ../tools/d1-reklam-ref-gclid.sql

CREATE TABLE IF NOT EXISTS reklam_ref_gclid (
  ref        TEXT PRIMARY KEY,
  gclid      TEXT,
  gbraid     TEXT,
  wbraid     TEXT,
  grup       TEXT,
  src        TEXT,
  ts         INTEGER,
  created_at INTEGER
);

CREATE INDEX IF NOT EXISTS idx_reklam_ref_gclid_created ON reklam_ref_gclid(created_at);
