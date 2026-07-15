# MÜHENDİS İŞ PAKETİ — Filament Rehberi + Ürün Bazlı Tavsiye

**Kat:** MÜHENDİS = Claude Opus (kaynak kod: build.py şablonu, index.html, sayfalar; içerik
metinleri bu spec'te — Okan onayına tabi, tek kaynak). Kabul testlerini mimar koşturur.
**Karar sahibi:** Okan (16 Tem 2026) — "müşteri filament isimlerini görmeli, mouse üstüne gelince
uzun açıklama, ürüne göre tavsiye ettiğimiz filament görünmeli."

## MİMARİ İLKE (bağlayıcı)

**Filament bilgisi ürün verisine YAZILMAZ — kuraldan türetilir.** 7.171 ürüne alan ekleme göçü
YOK (guard ile çatışır, gereksiz). Tek merkezi referans + kategori haritası; render anında
uygulanır. Sadece istisnalar için opsiyonel override alanı: `"tavsiyeFilament": ["ASA"]`
(yeni üründe ekleme scripti koyabilir; mevcutta tek tek `tools/duzelt.py`).
**`aciklama` alanına filament metni EKLENMEZ** — arama dizini değişmesin (parite korunur);
filament bloğu şablonda ayrı çizilir.

## MERKEZİ REFERANS — `tools/filamentler.json` (yeni; tek kaynak)

Alanlar: `ad, kisaEtiket, isiDayanimi, kisa, uzun`. Metinler (Okan onayına tabi; dürüst
aralıklar — abartma, taahhüt sayılır; "3D baskı" İFADESİ HİÇBİR METİNDE GEÇMEZ, "her renk" DENMEZ):

- **PLA** — "Ev içi" — ~55-60°C — İç mekân, dekoratif ve hafif kullanım parçaları için idealdir.
  Uzun: "Ev ve ofis içi kullanım için ideal malzeme. Sert ve boyutsal olarak kararlıdır, pürüzsüz
  yüzey verir. Isı dayanımı ~55-60°C olduğundan güneş altında, araç içinde veya sıcak ortamlarda
  önerilmez. İç mekân aparatları, dekorasyon ve masaüstü ürünlerde ilk tercihtir."
- **PETG** — "Dış mekân / genel amaçlı" — ~70-75°C — Darbeye ve neme dayanıklı güvenli seçim.
  Uzun: "İç ve dış mekânda genel amaçlı dayanıklı malzeme. Darbeye, neme ve kimyasallara karşı
  dirençlidir, hafif esnekliğiyle kırılmadan yük taşır. Isı dayanımı ~70-75°C. Araç içi parçalar,
  braketler, tutucular ve fonksiyonel yedek parçalar için dengeli tercihtir."
- **ASA** — "Güneş + su" — ~90-95°C — UV ve suya en dayanıklı; dış mekânın şampiyonu.
  Uzun: "Dış mekânın şampiyonu. Güneş ışığına (UV) ve suya karşı en dayanıklı malzemedir; rengi
  solmaz, formu bozulmaz. Isı dayanımı ~90-95°C. Tekne/marin parçaları, araç dışı aksamlar, bahçe
  ekipmanı ve sürekli güneş gören her parça için önerilir."
- **ABS** — "Isıya dayanıklı" — ~95-100°C — Isınan ortamların malzemesi.
  Uzun: "Isıya dayanıklı mühendislik malzemesi (~95-100°C). Motor bölmesi yakını, cihaz içi ve
  ısınan ortamlar için uygundur. Dayanıklı ve işlenebilirdir; doğrudan güneş altında uzun süreli
  kullanım için ASA daha iyi seçimdir."
- **Karbon katkılı (PETG-CF/PA-CF)** — "En yüksek dayanım" — ~80-120°C (taşıyıcıya göre) —
  Yük ve titreşim altındaki parçalar için en sert sınıf.
  Uzun: "Karbon fiber katkılı en yüksek dayanım sınıfı. Üstün sertlik ve mukavemet; yük, titreşim
  ve zorlu kullanım altındaki parçalar için önerilir. Isı dayanımı taşıyıcı malzemeye göre
  ~80-120°C. Fiyatı standart malzemelerden yüksektir; kritik parçalarda değerini fazlasıyla verir."

## KATEGORİ → TAVSİYE HARİTASI (varsayılan; tek yerde config)

`Otomobil, Motosiklet, Bisiklet: [PETG, ASA]` (ilki varsayılan tavsiye; ASA "güneş gören parça"
notuyla) · `Marin: [ASA]` · `Bahçe: [PETG, ASA]` · `Ev, Ofis, Dekorasyon, Oyun/Hobi: [PLA]` ·
`Elektronik, Kamera: [PETG, ABS]` (ABS "ısınan ortam" notuyla) · `Tamirat: [PETG]`.
Override alanı `tavsiyeFilament` varsa harita yerine o geçer.

## UI (saf HTML/CSS/JS; kütüphane YOK; lacivert #12294d düzeni)

1. **Ürün sayfası** (build.py şablonu): fiyat bloğunun altında "Malzeme" bölümü — 5 filament
   çipi; tavsiye edilen(ler)de "Tavsiyemiz" rozeti; hover'da (mobilde dokunmada) uzun açıklama
   balonu (CSS tooltip; `title=` yetmez, mobil çalışmalı). Isı dayanımı çipin üstünde görünür.
2. **Ana sayfa kartları**: kartta sadece tavsiye çipi (küçük, örn. "Tavsiye: PETG") — kalabalık yapma.
3. **Malzeme Rehberi sayfası**: `tools/sayfalar.py`'ye yeni statik sayfa `/malzeme-rehberi/`;
   5 malzemenin tam açıklaması + karşılaştırma tablosu (ısı/UV/su/darbe); footer'dan link; SSS'e
   "Hangi malzemeyi seçmeliyim?" maddesi eklenir, rehbere link verir.
4. **Parametrik (sarı seri)**: mevcut "malzeme&dayanıklılık" anlatısı korunur; filament bloğu
   parametrik sayfada da görünür (tavsiye: kullanım alanına göre "size sorarak belirleriz" notu).

## ENTEGRASYONLAR

- **Ekleme boru hattı:** `.urun-kaynaklari.json`'daki `baski` alanında malzeme önerisi varsa
  (örn. "PETG önerilir") ekleme scripti ürüne `tavsiyeFilament` override'ı yazar — tasarımcı adı/
  kaynak izi İÇERMEDEN (sadece malzeme adı geçer; gizlilik kuralı).
- **Ege:** `ege-bilgi.md` "MALZEME KAPSAMI" bölümü bu referansla ÇELİŞMESİN — build.py ya da ayrı
  küçük script `filamentler.json`'dan o bölümü üretsin/güncellesin (tek kaynak; ege-bilgi.md
  public, sır yok). pruvo-bot reposuna DOKUNMA (ege-bilgi.md bu repoda).
- **Shop paketi** (`tools/paket-shop-odeme.md`): varyant seçicinin filament listesi + varsayılan
  seçim bu referanstan gelir (koordinasyon: iki paket aynı dosyaya yazacaksa filamentler.json'u
  ÖNCE bu paket koyar, shop onu okur).

## KABUL TESTLERİ (çalıştırılabilir; hepsi yeşil olmadan kapanmaz)

1. `urunler.json` DEĞİŞMEMİŞ (git diff boş — bu paket ürün verisine dokunmaz).
2. Build sonrası rastgele 20 ürün sayfasında: 5 çip + tavsiye rozeti + tooltip içeriği
   `filamentler.json`'daki metinle birebir; kategoriye göre doğru tavsiye (haritayla karşılaştıran
   script).
3. Hiçbir üretilen sayfada "3D bask" ve "her renk" ifadesi yok (grep testi).
4. `/malzeme-rehberi/` sayfası üretiliyor, footer linki var, sitemap'te.
5. `node tools/parite-test.js` + `node tools/parite-ege.js` YEŞİL (aciklama değişmedi kanıtı).
6. Override testi: `tavsiyeFilament` alanlı sahte ürünle build → harita değil override basılıyor.
7. Mobil tooltip: dokunmayla açılıp kapandığının testi (en azından DOM/CSS düzeyinde doğrulama).

## TESLİM

Kod + `tools/filamentler.json` + rapor (değişen dosyalar, test çıktıları). **Commit ETME** —
commit/push mimarın. Isı değerleri ve metinler Okan onayından geçmeden CANLIYA ALINMAZ
(mimar, raporla birlikte metinleri Okan'a sunar).
