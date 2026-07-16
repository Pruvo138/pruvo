# FAZ 3 — /ara + /katalog önbellek & purge stratejisi

Mühendis notu (16 Tem 2026). Kararı mimar/Okan verir; burada **ne yapıldığı + neden**
ve **açık bırakılan seçim** yazılı. Kod yorumu değil buraya yazıldı: bu bir işletme
kararı (tazelik ↔ maliyet), kodun detayı değil.

## Bugün ne var

| Uç | Başlık | TTL |
|---|---|---|
| `/ara?q=` | `cache-control: public, max-age=60` | 60 sn |
| `/katalog?...` | `cache-control: public, max-age=60` | 60 sn |
| `/katalog?ids=` | aynı (60 sn) | 60 sn |
| `ozet.json` (Pages) | Pages/Cloudflare varsayılanı + deploy sonrası `purge_everything` | — |
| `urunler.json` (Pages) | `fetch(..., {cache:"no-cache"})` → ETag revalidation | — |

`/ara`'daki 60 sn **bu paketten önce de vardı** (FAZ 1) — dokunulmadı.

## Neden 60 sn (ve neden daha uzun değil)

- Katalog **push ile** değişir (günde birkaç kez), saniyede değil. 60 sn'lik bir
  pencere, yeni ürünün görünmesini en fazla 1 dk geciktirir — sipariş akışında
  farkedilmez.
- Karşılığında: aynı kategori sayfası / popüler arama edge'den döner, **D1 okuması ve
  Worker çağrısı harcanmaz**. 20k ürün + artan trafikte asıl koruma bu.
- Daha uzun TTL (ör. 1 saat) tazelik kaybını görünür hale getirirdi: Okan ürün ekler,
  sitede "yok" görünür → "site bozuk" algısı. 60 sn bu riski satın almaya değmez.

## Purge stratejisi

**Bugünkü hâl (yeterli, ek iş YOK):** `.github/workflows/deploy.yml` her `main` push'unda
Pages'e yayınladıktan sonra Cloudflare'de `purge_everything` çağırıyor. Bu, **site
kaynaklarını** (index.html, ozet.json, urunler.json) tazeler.

**DİKKAT — purge_everything Worker yanıtlarını KAPSAMAZ.** `pruvo-whatsapp-bot.gmlmz.workers.dev`
site zone'unda (`pruvo3d.com`) değil, `workers.dev` alt alan adında. Yani D1 senkronundan
sonra `/katalog` ve `/ara` cevapları **en fazla 60 sn** boyunca eski kalır.

Bu **kabul edilebilir** çünkü:
1. Pencere zaten 60 sn (TTL kadar), sınırsız değil — kendi kendine kapanır.
2. Yayın zinciri sıralı: Actions build → Pages yayın → D1 senkronu. `ozet.json` ile
   `/katalog` arasındaki en kötü tutarsızlık 60 sn sürer ve sonuç "yeni ürün 1 dk geç
   göründü"dür — veri kaybı ya da yanlış fiyat değil.
3. Kartların kalıcı adresi (`/urun/<id>/`) bu önbellekten bağımsız; SEO ve sipariş linki
   etkilenmez.

**Sıkı tazelik gerekirse (mimarın kararı — BUGÜN YAPILMADI):** iki yol var:
- **(a) Cache API + tag'li purge:** Worker içinde `caches.default` ile elle önbellekleme
  + D1 senkronu sonunda `d1-sync.py`'nin bir `/purge?anahtar=...` ucunu çağırması.
  Maliyet: Worker'da elle önbellek yönetimi (yeni sessiz-hata yüzeyi).
- **(b) Worker'ı `pruvo3d.com/api/*` route'una almak:** o zaman mevcut
  `purge_everything` Worker cevaplarını da kapsar ve **ek kod gerekmez** — ayrıca CORS
  ihtiyacı da kalkar (aynı origin). Bedeli: production route değişikliği (bu paket
  üretime dokunmuyor → yargı listesine yazıldı).

**Öneri (mühendis görüşü):** bayrak açılacağı gün (b). Bugün gereksiz; 60 sn zaten yeterli
ve (b) production route'u değiştirmek demek — bu paketin kırmızı çizgisi.

## Testte önbellek TUZAĞI (yaşanmış ders)

`/ara` ve `/katalog` **60 sn önbellekli döndüğü için**, önbellek kırıcısı olmayan bir test
Worker'ı değil **CDN'i** ölçer: bozuk kod, 60 sn önce önbelleğe girmiş DOĞRU cevapla
**YEŞİL yanar**. FAZ 2'de yaşandı ([[d1-arama-tuzaklari]]).

Bu yüzden her test benzersiz `_nonce` gönderir:
- `tools/parite-test.js`, `tools/parite-ege.js` → çalışma başına tek `NONCE` (zaten vardı)
- `tools/faz3-sayfalama.js` → çalışma başına `NONCE`
- `tools/faz3-gecikme.js` → **istek başına** ayrı nonce (gecikme ölçüldüğü için her
  istek Worker'a + D1'e kadar gitmeli)

İstekteki `cache-control: no-cache` başlığı **TEK BAŞINA YETMEZ** — Cloudflare edge'i
yok sayar. Nonce'u kaldırma.
