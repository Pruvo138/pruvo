# K252 — SIPARIS DURUM SECICI (kargosuz tamamlama + geri alma)

> **SAHIP:** KraL · **KAT:** chip (`KraL-K252`) + isci hatti · **KARAR:** Okan, 20 Agu 2026
> (soru penceresi: "Serbest secim — 'kargolandi' HARIC").
> Bu paket ODEME/SIPARIS YASAM DONGUSUNE dokunur. Bypass YOK, `--no-verify` YOK,
> `wrangler deploy` YOK (deploy OKAN KAPISI — merge canliya inmez).

## 1. OLCULEN ARIZA (spec yazilmadan ONCE olculdu, bu blok ON-OLCUMDUR)

Panelde sipariş **takip kodu girmeden tamamlandi olarak isaretlenemiyor**. Sebep tasarimdir,
kaza degil:

| yer | olculen |
|---|---|
| `shop/src/yonet.js:39-44` | `IZINLI` tablosu: `odendi→uretimde` · `uretimde→kargolandi` · `kargolandi→tamamlandi` · `havale-bekliyor→odendi` |
| `shop/src/yonet.js:57-61` | `gecisGecerli`: `iptal` her durumdan; digerleri YALNIZ `IZINLI` |
| `shop/src/yonet.js:675-676` | `POST /yonet/durum` hedef `kargolandi` ise **400 `kargo-ucunu-kullan`** |
| `shop/src/yonet.js:750-772` | `kargolandi`ya TEK yol `/yonet/kargo`; firma+kod ZORUNLU |
| `tools/d1-sema.sql:381-383` | ayni kural sema yorumunda da yazili |
| `shop/src/yonet.js:1550-1559` | paneldeki `<select id="durumSuzgec">` **liste suzgecidir**, siparis durum seticisi DEGILDIR |

Yani `uretimde` durumundan cikisin tek kapisi `kargolandi`, o da takip kodu istiyor →
`tamamlandi` kodsuz **ULASILAMAZ**. Siparis basina durum secici de YOK.

## 2. HUKUM (Okan karari + KraL'in odeme ekseni sarti)

**(A) Operasyon ekseninde SERBEST secim, geri alma DAHIL.** Panelden `uretimde`, `tamamlandi`,
`iptal` her mevcut durumdan secilebilir; yanlis isaretleme GERI ALINABILIR
(`tamamlandi → uretimde` gecerlidir).

**(B) `kargolandi` ISTISNADIR — degismez.** `/yonet/durum` ucu `kargolandi` hedefini
**REDDETMEYE DEVAM EDER** (400 `kargo-ucunu-kullan`); o duruma yalnizca firma+kod isteyen
`/yonet/kargo` ucundan gecilir. Guvence korunur: **takip kodsuz `kargolandi` satiri OLUSAMAZ.**
Secicide `Kargolandi` secenegi **BULUNMAZ** (kargo formu zaten kartta duruyor).

**(C) 🔴 ODEME-KAYNAKLI DURUMLAR SECICIDE YOKTUR** (KraL sarti, Okan'a bildirildi):
`bekliyor` · `basarisiz` · `havale-bekliyor` · `incele` · `odendi` **elle setlenemez** —
bunlari odeme sistemi yazar. Elle `odendi` isaretlemek **tahsilat yalani** uretir
(odenmemis siparis odenmis gorunur). TEK istisna **geri alma**: mevcut durum
`{uretimde, kargolandi, tamamlandi}` ise `odendi` hedefine donulebilir (o siparis zaten
odenmisti; yalan uretmez). `bekliyor|basarisiz|havale-bekliyor|incele → odendi` **400**.

## 3. YAPILACAK

1. **`shop/src/yonet.js` gecis kurali.** `gecisGecerli` (ya da onun cagirdigi saf fonksiyon)
   §2'yi uygular. `IZINLI` tablosu ile ikiz mantik OLMAYACAK — **tek saf fonksiyon**, hem
   `/durum` ucu hem panelin sundugu kume ONDAN turetilecek.
2. **Panel: siparis basina durum secici.** Karta `<select>` + "Uygula" butonu; secenekler
   **sunucunun kabul ettigi kumeden TURETILIR** (elle yazilmis ikinci liste YASAK —
   [[ayni-alan-iki-hukum-biri-sessiz]]). Mevcut `iptal` butonu ve kargo formu YERINDE KALIR.
3. **`tools/d1-sema.sql:381-389` yorumu guncellenir** — yeni kural yazilir; sema yorumu
   koddan farkli kalirsa yalan soyler.
4. Musteriye giden e-posta akisi **DEGISTIRILMEZ** (kargo bildirimi `/kargo` ucuna bagli kalir).

## 4. KABUL — CIVILENMIS, MUTANTLI (ölçüt bu bloktur; bulgu ÇIKARSA kalem acilir, ölçüt BUYUMEZ)

Kabul `shop/test/` altinda kosan bir dosyada toplanir, `ci-kapsam-test.py` gorecek sekilde
baglanir (kapinin menzili CAGRI YERIDIR — [[kapinin-menzili-cagri-yeridir]]).

| # | iddia | beklenen |
|---|---|---|
| ① | **kargosuz tamamlama** `uretimde → tamamlandi` | **200** · D1'de `kargo_kodu`/`kargo_firma` **NULL kalir** · `durum_gecmisi`ne satir DUSER |
| ② | **geri alma** `tamamlandi → uretimde` | **200** |
| ③ | **darlik** `/durum` hedef `kargolandi` (mevcut `odendi`·`uretimde`·`tamamlandi` UCUNDEN) | **400 `kargo-ucunu-kullan`** — uc kez |
| ④ | **odeme ekseni** `bekliyor→odendi` · `basarisiz→odendi` · `havale-bekliyor→odendi` · `incele→odendi` | **400** (dorduncu de) |
| ⑤ | **geri alma istisnasi** `tamamlandi→odendi` · `uretimde→odendi` | **200** |
| ⑥ | `iptal` her durumdan (mevcut `iptal` HARIC) | bugunku davranis AYNEN |
| ⑦ | **panel/sunucu TEK KAYNAK** | panelin sundugu secenek kumesi sunucunun kabul kumesinden TURETILIYOR (`panel-kaynak.mjs` olcer) · `Kargolandi` secicide **0 kez** geciyor |

**MUTANTLAR (her biri: hedef kol KIRMIZI + yan eksen YESIL = ATIF olculur):**
- **M1 DARLIK:** `/durum` ucundaki `kargolandi` reddi KALDIRILIR → ③ OLMELI, ①②④ YASAMALI.
- **M2 TAHSILAT:** `odendi` hedefinin "yalniz geri alma" sarti KALDIRILIR → ④ OLMELI, ⑤ YASAMALI.
- **M3 IKIZ LISTE:** panele elle fazladan bir durum eklenir → ⑦ OLMELI, ①②③ YASAMALI.
- **K0 KONTROL:** ilgisiz bir kol (or. rozet rengi) bozulur → **hicbir iddia OLMEMELI.**

**REGRESYON TABANI (once/sonra AYNI olmali, sayiyla yazilir):**
`shop/test/kabul.js` · `shop/test/kisit-fail-closed.mjs` · `shop/test/panel-kaynak.mjs` ·
`shop/test/uretim-kaynak.mjs` · `tools/olculmemis-siparis-test.py` · `tools/ci-kapsam-test.py`.
**Taban ONCE olculur** ([[olcut-civilenirken-taban-olculmeli]]) — main kirmizi cikarsa o kirmizi
bu kalemin kapsami DEGILDIR, ayri kalem acilir.

## 5. YASAK / KAPSAM

- `urunler.json` · `.urun-kaynaklari.json` **DOKUNULMAZ**.
- Fiyat/tahsilat kodu (`sepetiFiyatla`, kalem cozumleme beyaz listesi) **ELLENMEZ**.
- `wrangler deploy` **YOK** — panel Worker'da kosar, **merge canliya INMEZ**; deploy OKAN KAPISI.
- `--no-verify`, kapi bypass, `git push --force` **YOK**.
- Bitince: gecici dosya/worktree artigi **0** (uretens temizler).
