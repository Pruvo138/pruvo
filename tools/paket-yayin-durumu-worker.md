# PAKET — ATOMİK YAYIN, OKUMA TARAFI (worker `yayinda=1` şartı)

**Veren:** KraL mühendisi (dal `kral/atomik-yayin`) · **Uygulayacak ev:** `~/dev/pruvo-bot` (**HocA**)
**Neden burada:** `worker/src/index.js` HocA'nın evindedir; KraL mühendisi başka mimarın deposuna
yazmaz. Bu dosya, uygulanacak değişikliğin **birebir** tarifidir; D1 tarafı KraL'da BİTMİŞTİR.

---

## 0. NE YAPILDI (KraL tarafı, canlı D1'de UYGULANDI)

| Ne | Durum |
|---|---|
| `urunler.yayinda INTEGER NOT NULL DEFAULT 0` + `release_id TEXT` | canlı D1'de VAR (31 Tem) |
| `urunler_yayin(yayinda, seq DESC)` + `urunler_yayin_kat(yayinda, kategori, seq DESC)` | kuruldu |
| Yeni ürün D1'e **taslak** girer (`yayinda=0`) | `tools/d1-sync.py` (V36–V41 kabul) |
| Var olan ürünün içeriği değişince `yayinda` **korunur** | `KOLONLAR` listesinde yok (V37) |
| Yayına alma = `/urun/<id>/` canlıda **200** doğrulanınca tek UPDATE | `tools/yayin-kapisi.py --yayinla`, CI `yayin` işi |
| **Geriye doldurma** (canlıdaki 15.479 ürün → `yayinda=1`) | **KOŞULDU**, doğrulandı |

Ölçüm (31 Tem, geriye doldurmadan hemen sonra): `toplam=15558 · yayinda=15479 · taslak=79`
— o 79 satır, tam da o an deploy kuyruğunda olan (D1'de var, sayfası **henüz** canlıda olmayan)
ürünlerdir. Kapatılan pencere budur.

## 1. DEĞİŞMEZ (invariant)

> `yayinda=1` olan her id'nin `/urun/<id>/` sayfası CANLIDA vardır.

İki bloklayıcı kapı birlikte verir:
* `tools/uretim-butunluk-kapisi.py` (CI, build'den sonra): yayınlanan `urunler.json`'daki **her**
  id'nin sayfası üretilmiş + sitemap/feed'deki her ürün URL'inin dosyası var.
* `tools/yayin-kapisi.py`: `yayinda=1` yalnızca canlı 200 doğrulandıktan sonra yazılır;
  `--durum` "yayinda=1 olup canlı `urunler.json`'da olmayan" sayısını ölçer (0 olmalı).

## 2. UYGULANACAK DEĞİŞİKLİK — `worker/src/index.js`

**Kural:** ürün **KEŞİF** yüzeylerinin hepsine `yayinda = 1` şartı eklenir. Şart **fail-closed**
yöndedir: taslak ürün gösterilmez (satış gecikir), asla 404 veren kart üretilmez.

### 2.1 `araD1()` — site araması (`/ara`)
`katMarkaKosulu(...)` çağrısından hemen sonra, `kaynak`/`nere` kurulmadan önce:

```js
  kosul.push("u.yayinda = 1");   // ATOMIK YAYIN: taslak urun aramada GORUNMEZ
```
`kaynak` token yokken `"urunler u"` olduğu için `u.` öneki iki dalda da geçerlidir.

### 2.2 `katalogD1()` — sayfalı katalog (`/katalog`)
Aynı satır, `katMarkaKosulu(...)` çağrısından sonra:

```js
  kosul.push("u.yayinda = 1");
```
⚠️ `katalogSayimAnahtari(kategori, marka)` KV önbelleği: şart eklendiği an **eski sayımlar
bayat** olur. Anahtar şemasına bir sürüm eki geçirin (ör. `"v2|" + kategori + "|" + marka`),
yoksa taslak ürünleri de sayan eski toplam TTL boyunca servis edilir.

### 2.3 `araEgeD1()` — Ege modu (`mod=ege`)
İç SELECT'e WHERE eklenir; **skor mantığına, kategori/marka filtresine DOKUNULMAZ**
(HocA'nın açık maddesi):

```js
    "SELECT " + alanlar + ", seq, " + skor + " AS skor FROM urunler WHERE yayinda = 1" +
```

### 2.4 `/katalog?ids=...` — sepet kartı beslemesi
`"SELECT " + KART_ALANLARI + " FROM urunler u WHERE u.id IN (" + yer + ")"`
→ sonuna ` AND u.yayinda = 1` eklenir. (Yayın **tek yönlüdür**: yayına giren ürün geri
taslağa DÜŞMEZ, dolayısıyla sepetteki ürün bu şartla kaybolmaz.)

### 2.5 🔴 DOKUNULMAYACAK — `urunleriIdIleGetir()` (iyzico devir bloğu)
`SELECT id, baslik, fiyat, gorsel, aciklama FROM urunler WHERE id IN (...)` **filtrelenmez.**
Burası keşif değil **kayıt zenginleştirme** yoludur (tamamlanmış siparişin ürün satırı).
Şart eklenirse geçmiş bir siparişin satırı boşalır = para/kayıt yolunda sessiz veri kaybı.

## 3. SIRA (bozulursa TÜM KATALOG gizlenir)

1. ✅ şema + geriye doldurma (KraL, YAPILDI — `taslak` yalnız deploy kuyruğundakiler).
2. ⬜ **Deploy'dan hemen önce** teyit: `python3 tools/yayin-kapisi.py --durum` →
   `DEGISMEZ IHLALI = 0` ve `taslak` sayısı yalnızca o an uçuşta olan partiye eşit.
3. ⬜ worker değişikliği + kabul testi (§4) yeşil → `wrangler deploy` (KraL/Okan kapısı).
4. ⬜ Deploy sonrası: `/ara?q=...` toplamı ile site toplamı arasında fark = o anki taslak sayısı
   kadar olmalı; `python3 tools/parite-ege.js` **taze** main checkout'unda koşulur.

## 4. KABUL (worker tarafı — HocA yazar, çalıştırılabilir)

`worker/test/` içine, mevcut `katalog-kabul.mjs`/`ege-arama-kabul.mjs` desenine göre:

1. **POZİTİF:** `yayinda=1` ürün `/ara`, `/katalog`, `mod=ege`, `?ids=` dördünde de DÖNER.
2. **NEGATİF (asıl vaka):** `yayinda=0` ürün dördünde de DÖNMEZ ve `toplam` sayımına GİRMEZ.
3. **KIRMIZI-MUTASYON:** dört sorgudan her birinden şart tek tek silinir → ilgili negatif vaka
   KIRMIZI yanmalı (4 mutant, 4 kırmızı). Sağ kalan mutant = ölü test.
4. **PARA YOLU NÖBETİ:** `urunleriIdIleGetir()` taslak ürünü HÂLÂ döndürür (§2.5 bilinçli).
5. **ÖNBELLEK:** `/katalog` sayım anahtarı sürümlendi mi — eski anahtarla yazılmış sayım
   yeni şartlı sorguya servis EDİLEMEZ.
