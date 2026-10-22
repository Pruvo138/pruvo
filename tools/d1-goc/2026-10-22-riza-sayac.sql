-- GOC: riza_sayac (kimliksiz riza sayaci, BaBa 22 Eki 2026). POST /api/shop/riza (shop/src/riza-sayac.js) bandin
-- kararini (kabul|ret|kapat) gun bazli SAYAR; kisisel veri YOK (IP/UA/cerez/URL ne okunur ne saklanir). Tablo YOKKEN
-- kod sessizdir: UPSERT patlar, hata metni loglanir, istemciye yine 204 doner (sayim kaybi, kullanici etkisi yok).
-- Siraya gerek yok (idempotent, IF NOT EXISTS). Sema kaynagi tools/d1-sema.sql.
CREATE TABLE IF NOT EXISTS riza_sayac (gun TEXT NOT NULL, karar TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (gun,karar));
