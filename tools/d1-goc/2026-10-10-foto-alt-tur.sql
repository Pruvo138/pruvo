-- GOC: foto_isler.alt_tur (6 model, 10 Eki). Figur alt turu ('insan'|'pet'|'model'); siparis model kapisi
-- (fotoKalemFiyatla) figur isinin modelini bundan cozer. '' = eski/alt tursuz satir -> figur modeli KAPALI.
-- Okuma (isAltTuru) sutun yokken "" doner (500 YOK, fail-closed); ama alt turlu figur onizlemesi (panel ornek dahil)
-- sutun yokken INSERT'te duser -> kod yayina cikmadan ONCE uygulanir (once onizleme D1, sonra canli D1). Bir kez.
ALTER TABLE foto_isler ADD COLUMN alt_tur TEXT NOT NULL DEFAULT '';
