# YENİ PARAMETRİK ÜRÜN EKLEME REHBERİ (Ölçüye Özel / sarı seri)

Bu rehber, siteye **müşterinin ölçü girip anında fiyat gördüğü** yeni bir parametrik
ürün eklemenin adımlarını, uçtan uca BİR ÖRNEK üzerinden anlatır. Örnek:
`ornek-plaka` (dikdörtgen plaka; en × boy × kalınlık).

Fiyat kuralı (değişmez): `fiyat = tabanFiyat × (hacim / tabanHacim) × filamentKatsayı × renkFaktör`
— kuruş korunur, TL'ye yuvarlama yapılmaz. Taban fiyatı YALNIZ Okan verir;
verilene kadar `tabanFiyatTL: null` kalır ve sayfada fiyat "—" görünür.

## Ön koşullar

- OpenSCAD: `/opt/homebrew/bin/openscad` (BOSL2 kütüphanesi `~/Documents/OpenSCAD/libraries`)
- Node.js (`node`) ve Python 3
- Üretici .scad dosyaları: `~/dev/pruvo-jenerator/jeneratorler/` (kendi kodumuz)

## Adım 1 — Üreteci hazırla (.scad)

Ürünün geometrisini üreten OpenSCAD dosyası `~/dev/pruvo-jenerator/jeneratorler/<aile>.scad`
altında olmalı (yeni yazılacaksa o repodaki üsluba uy: parametreler dosya başında,
`-D` ile ezilebilir). Örnek için geçici bir dosya yeterli:

```scad
// ornek-plaka.scad — dikdörtgen plaka
En = 60;         // mm
Boy = 100;       // mm
Kalinlik = 3;    // mm
cube([En, Boy, Kalinlik]);
```

Hızlı deneme için bu dosyayı geçici bir klasöre koyup testte `PRUVO_SCAD_DIR`
ortam değişkeniyle o klasörü gösterebilirsin (Adım 5).

## Adım 2 — Müşteri şeması: `jenerator/urunler/<urun-id>.json`

Ürünün sitedeki id'siyle aynı adda bir şema dosyası yaz. Alan formatının tam
tanımı ve kuralları: `jenerator/test/SOZLESME.md`. Örnek:

```json
{
  "id": "ornek-plaka",
  "hacimFormulu": "ornekplaka",
  "parametreler": [
    {"ad": "en", "etiket": "En", "birim": "mm", "tip": "sayi",
     "min": 20, "max": 200, "adim": 1, "varsayilan": 60, "aciklama": "Plakanın kısa kenarı"},
    {"ad": "boy", "etiket": "Boy", "birim": "mm", "tip": "sayi",
     "min": 20, "max": 300, "adim": 1, "varsayilan": 100, "aciklama": "Plakanın uzun kenarı"},
    {"ad": "kalinlik", "etiket": "Kalınlık", "birim": "mm", "tip": "sayi",
     "min": 1, "max": 10, "adim": 0.5, "varsayilan": 3, "aciklama": "Plaka kalınlığı"}
  ],
  "tabanHacimMm3": 18000,
  "tabanFiyatTL": null
}
```

Püf noktaları:
- `ad` ASCII snake_case Türkçe; müşteriye görünen ad `etiket`te.
- Site açıklamasında AÇIK aralık geçiyorsa (örn. "çap 20–80 mm") min/max birebir o olmalı.
- `tabanHacimMm3` = hacim fonksiyonunun VARSAYILAN değerlerdeki sonucu (Adım 5'teki
  test bunu %0,1 toleransla doğrular; önce kaba yaz, testin bastığı değerle düzelt).

## Adım 3 — Hacim fonksiyonu: `jenerator/test/aileler/<aile>.js`

Kapalı-form, saf JS; SADECE `function <aile>(p) { ... }` (+ `<aile>_` önekli
yardımcılar). Örnek (`ornekplaka.js`):

```js
function ornekplaka(p) {
  return p.en * p.boy * p.kalinlik; // mm3
}
```

`jenerator/hacim.js`'i ELLE DÜZENLEME — o dosya `birlestir.py` ile bu klasörden
otomatik üretilir (site ve sipariş doğrulaması aynı dosyayı kullanır, kopya yasak).

## Adım 4 — Test eşlemesi: `jenerator/test/esleme/<aile>.json`

Şema parametrelerini .scad değişkenlerine bağlar; müşteriye açılmayan .scad
değişkenleri `sabit`e girer. Örnek (`ornekplaka.json`):

```json
{
  "urunId": "ornek-plaka",
  "scad": "ornek-plaka.scad",
  "fonksiyon": "ornekplaka",
  "esleme": {"en": "En", "boy": "Boy", "kalinlik": "Kalinlik"},
  "sabit": {}
}
```

## Adım 5 — OpenSCAD doğrulama testi (yeşil olmadan devam etme)

> **Rosetta YASAK (mimar kuralı, 16 Tem 2026):** Doğrulama YALNIZ arm64 openscad
> ile yerelde ya da GitHub Actions'ta koşar; `arch -x86_64` / Rosetta üzerinden
> openscad ASLA çalıştırılmaz (macOS Intel-uyumluluk uyarısı tetikliyor).
> openscad yerelde açılışta çökerse dogrula.py 2 kez yeniden dener; ısrarla
> çökerse aile "yerel doğrulanamadı" notuyla CI doğrulamasına bırakılır.

### Doğrulama artık CI'da (mimar bildirimi, 16 Tem 2026)

Bulut doğrulama yayında: **github.com/Pruvo138/pruvo-jenerator** (private) →
Actions → **"Sarı-seri hacim doğrula"** workflow'u (main'de yeşil; elle tetikleme
`workflow_dispatch` ile Actions sekmesinden). Kurallar:

- **Yerel openscad GEREKMEZ; Rosetta ASLA.** Yerelde koşmak istersen dogrula.py
  `PRUVO_OPENSCAD` env değişkeniyle herhangi bir arm64 openscad ikilisine
  yönlendirilebilir (yol sırası: env → brew → /Applications → yerel kopya).
- CI, şema/hacim/eşleme dosyalarının **main'e girmiş** hâlini doğrular — henüz
  commit edilmemiş yerel değişiklikleri DOĞRULAMAZ; yeni aile eklerken ya yerel
  arm64 openscad'la koş ya da değişikliği push edip workflow'u dispatch et.

```
python3 jenerator/test/dogrula.py ornekplaka --set 5
python3 jenerator/test/dogrula.py ornekplaka --set 5 --seed 1
python3 jenerator/test/dogrula.py ornekplaka --set 5 --seed 2
```

(Geçici .scad klasörü kullanıyorsan başına `PRUVO_SCAD_DIR=/gecici/klasor` ekle.)
Test; varsayılan set + rastgele setlerde JS hacmini OpenSCAD render hacmiyle
karşılaştırır, sapma > %3 ise KIRMIZI. Formülü düzelt, aralığı daraltarak "geçirme"
yoluna sapma. `tabanHacimMm3` uyuşmazlığını da bu test yakalar.

## Adım 6 — Ürünü siteye bağla

- `urunler.json`'a ürün normal akışla eklenir ve `"parametrik": true` olur
  (ürün ekleme rehberi: `tools/URUN-EKLEME-REHBERI.md`).
- `tools/build.py` sayfayı üretirken `jenerator/urunler/<id>.json` şemasını bulur
  ve konfigüratörü otomatik basar; şema yoksa eski "Ölçüye Özel" düzen sürer.
- Açıklamadaki "Neyi ayarlıyoruz?" maddeleri şema parametreleriyle tutarlı olmalı
  (kabul testi `kabul.py` bunu tarar).

## Adım 7 — Taban fiyat

Okan'dan ürünün VARSAYILAN ölçülerdeki PLA fiyatını al, `tabanFiyatTL`'ye yaz.
(Şablon tablo: `tools/taban-fiyat-tablosu.md`.) Null kaldığı sürece müşteri
fiyat yerine "—" görür; sipariş WhatsApp teklifiyle ilerler.

## Adım 8 — Yayın

Commit/push kurallı akışla (guard hook'ları çalışır durumda). Deploy beyaz
listesi (`.github/workflows/deploy.yml`) `jenerator/hacim.js`, `konfigurator.js`
ve `urunler/` şemalarını yayına kopyalar; `jenerator/test/` YAYINA GİRMEZ.

## Temizlik (örneği geri alma)

Örnek üründen geriye dosya bırakma:

```
rm jenerator/urunler/ornek-plaka.json
rm jenerator/test/aileler/ornekplaka.js
rm jenerator/test/esleme/ornekplaka.json
python3 jenerator/test/birlestir.py   # hacim.js'i örneksiz yeniden üret
```
