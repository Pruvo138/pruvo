-- GOC: foto anahtarlik turu SILINDI (Okan 14 Eki 2026 "Anahtarlik - yazi sil" + "Anahtarlik - figur sil").
-- foto_acik'ta eski tur satiri ('anahtarlik') ve iki model satiri ('anahtarlik_yazi', 'anahtarlik_figur') kalmaz;
-- kod bu kodlari artik tanimaz (shop/src/foto.js MODELLER 4 model). Canli D1'de satirlar zaten silindi (0 etkiler);
-- dosya sema goc zinciri icindir. Idempotent; once onizleme D1, sonra canli D1. Sema kaynagi tools/d1-sema.sql.
DELETE FROM foto_acik WHERE tur IN ('anahtarlik','anahtarlik_yazi','anahtarlik_figur');
