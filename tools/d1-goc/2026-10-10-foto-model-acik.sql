-- GOC: foto acilis anahtari MODEL duzeyinde (6 model, 10 Eki; "canlida YALNIZ gecen model").
-- foto_acik.tur artik MODEL KODU tasir: anahtarlik_yazi | insan | pet | plaket | anahtarlik_figur | model
-- (modelsiz turler — bust, yapboz, litofan, ... — tur koduyla AYNEN). Modelli turun ESKI satiri ('anahtarlik',
-- 'figur') kodda TEK BASINA HICBIR modeli acmaz (fail-closed; foto.js acikTurler/modelAcik).
-- Geriye uyum karari (ucretli prova 10 Eki: uctan uca YALNIZ anahtarlik_yazi + plaket gecti):
--   eski 'anahtarlik' acik -> 'anahtarlik_yazi' acik  (anahtarlik_figur onarim arizasi: ACILMAZ)
--   eski 'figur' acik      -> HICBIR model            (insan/pet/model DENGE RED: ACILMAZ)
--   'plaket' ve modelsiz tur satirlari AYNEN.
-- Eski satirlar SILINIR (olu anahtar birakilmaz). Tekrar kosulabilir (INSERT OR IGNORE + DELETE).
-- UYGULAMA: mimar; once onizleme D1, sonra canli D1. Bu dosya kendisi HICBIR yere uygulanmaz.
INSERT OR IGNORE INTO foto_acik (tur, acik, guncel)
  SELECT 'anahtarlik_yazi', 1, strftime('%Y-%m-%dT%H:%M:%SZ', 'now') FROM foto_acik WHERE tur = 'anahtarlik' AND acik = 1;
DELETE FROM foto_acik WHERE tur IN ('anahtarlik', 'figur');
