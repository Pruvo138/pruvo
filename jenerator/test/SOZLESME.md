# AİLE İŞİ SÖZLEŞMESİ (Codex mühendis alt-işleri için — BAĞLAYICI)

Görevin: SANA VERİLEN TEK AİLE için üç dosya üretmek ve doğrulama testini
YEŞİL yapmak. Başka hiçbir dosyaya dokunma.

## Üretilecek üç dosya

### 1) `jenerator/urunler/<urunId>.json` — müşteri parametre şeması (PUBLIC)

```json
{
  "id": "<urunId>",
  "hacimFormulu": "<aile>",
  "parametreler": [
    {"ad": "ic_cap", "etiket": "İç çap", "birim": "mm", "tip": "sayi",
     "min": 5, "max": 200, "adim": 0.5, "varsayilan": 30,
     "aciklama": "Halkanın iç çapı"},
    {"ad": "profil", "etiket": "Kesit profili", "tip": "secim",
     "secenekler": [{"deger": "yuvarlak", "etiket": "Yuvarlak"},
                    {"deger": "kare", "etiket": "Kare"}],
     "varsayilan": "yuvarlak", "aciklama": "Kesit şekli"},
    {"ad": "yazi", "etiket": "Üzerindeki yazı", "tip": "metin",
     "varsayilan": "PRUVO", "maksUzunluk": 20,
     "aciklama": "Ürün üzerine işlenecek metin"}
  ],
  "tabanHacimMm3": 12345.6,
  "tabanFiyatTL": null
}
```

Kurallar:
- `ad`: ASCII küçük harf snake_case TÜRKÇE kök (ic_cap, kesit, kalinlik, dis_sayisi...).
  `etiket`/`aciklama`: düzgün Türkçe (UTF-8 serbest).
- Müşteriye 3–6 anlamlı parametre aç (`sayi`/`secim`); gerisini eşleme dosyasında
  `sabit`e koy. Yazı/logo gibi hacmi belirlemeyen sipariş bilgileri `tip:"metin"`
  olabilir (hacim fonksiyonuna GİRMEZ, sipariş satırına girer).
- Ürün açıklamasındaki "Neyi ayarlıyoruz?" maddeleri YOL GÖSTERİCİ, oradaki
  AÇIK aralıklar (örn. "çap (20–80 mm)") BAĞLAYICIDIR: min/max birebir o aralık.
  Açık aralık yoksa jeneratörün makul/güvenli çalıştığı aralığı seç (uçları test et).
- `adim`: müşteri açısından anlamlı (0.1/0.5/1...). `varsayilan` = tipik kullanım;
  `tabanHacimMm3` TAM OLARAK hacim fonksiyonunun varsayılanlardaki değeri
  (node ile hesapla, aynen yaz; test %0.1 toleransla karşılaştırır).
- `tabanFiyatTL`: her zaman `null` (fiyatı Okan verecek).

### 2) `jenerator/test/aileler/<aile>.js` — kapalı-form hacim fonksiyonu

- İçerik SADECE: `function <aile>(p) { ... return mm3; }` + gerekirse
  `<aile>_` önekli yardımcı fonksiyonlar. Global durum, require, IIFE YASAK
  (dosyalar birlestir.py ile tek modülde toplanır).
- `p`: şemadaki `ad` alanları anahtar; `sayi` → number, `secim` → string.
  `metin` parametreleri fonksiyona GELMEYEBİLİR — kullanma.
- Dönüş: yaklaşık KATI hacim mm³ (baskı dolgusundan bağımsız, geometrik katı).
  Kapalı-form: integral/analitik yaklaşım serbest, sayısal döngü (küçük, sabit
  adımlı toplam dahil) da kabul — yeter ki saf, deterministik, hızlı (<1 ms) olsun.
- Hedef: OpenSCAD render hacmine sapma TÜM GEÇERLİ aralıkta ≤ %3.
  Delikler/boşluklar/pahlar hacimde önemliyse MODELLE; metin kabartma/oyma gibi
  ikincil etkiler varsayılan metinle kalibre edilebilir (gerekirse sabit düzeltme
  çarpanını türet ve yorum satırında gerekçele).

### 3) `jenerator/test/esleme/<aile>.json` — test eşlemesi (şema → OpenSCAD)

```json
{
  "urunId": "<urunId>",
  "scad": "<aile>.scad",
  "fonksiyon": "<aile>",
  "esleme": {"ic_cap": "Inside_Diameter", "kesit": "Cross_Section", "profil": "Profile"},
  "deger_esleme": {"profil": {"yuvarlak": "round", "kare": "square"}},
  "sabit": {"Segments": 120}
}
```

- `esleme`: şemadaki her `sayi`/`secim` parametresi → .scad'daki değişken adı.
  (`metin` parametresi eşlenebilir ya da `sabit`te tutulur.)
- `sabit`: müşteriye açılmayan .scad değişkenlerini testte sabitler. Çözünürlük
  ($fn/Segments) değişkenlerini YÜKSEK tut ki render hacmi analitik değere yakınsasın
  (kapalı-formda düşük-poligon düzeltmesi yapma; segment sayısını sabitle yeter).

## Doğrulama döngüsü (bitmeden çıkma)

```
python3 jenerator/test/dogrula.py <aile> --set 5
python3 jenerator/test/dogrula.py <aile> --set 5 --seed 1
python3 jenerator/test/dogrula.py <aile> --set 5 --seed 2
```

Üçü de YEŞİL olana kadar formülü/aralıkları düzelt. Sapma sınırda geziyorsa
aralığı daraltmak yerine formülü iyileştir; aralık daraltma SON çare ve
açıklamadaki açık aralık ASLA daraltılamaz. openscad: /opt/homebrew/bin/openscad.
Scad kaynağı: sana verilen yol (oku, geometriyi oradan çıkar; tahmin etme).

## KIRMIZI ÇİZGİLER (ihlal = iş reddedilir)

- OpenSCAD'i `arch -x86_64`/Rosetta ile ÇALIŞTIRMA (yalnız arm64; çökerse
  dogrula.py kendisi yeniden dener, ısrarla çökerse aile CI'a kalır).

- Ürettiğin hiçbir dosyada gizli üyelik markasının adı ("k••lm" — adı bu dosyaya
  dahi yazılmaz; kabul testi #5 grep'ler) hiçbir varyantıyla GEÇMEZ.
- "3D b•sk…" ile başlayan üretim ifadeleri ve "her r•nk" kalıbı GEÇMEZ
  (maskeli yazdık ki bu dosya kendi taramasına takılmasın; "farklı renk
  seçenekleri" de yazma, renk zaten ayrı bileşende).
- `urunler.json`a, `tools/`a, `secenekler.js`e, Worker/ödeme koduna DOKUNMA.
- Git komutu ÇALIŞTIRMA (commit/push yasak).

## Bitiş çıktısı (son mesajın)

Tek JSON: `{"aile": "...", "durum": "yesil|kirmizi", "parametreSayisi": N,
"tabanHacimMm3": X, "enKotuSapmaYuzde": Y, "notlar": "..."}`
