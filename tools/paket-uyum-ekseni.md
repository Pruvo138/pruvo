# PAKET — UYUM EKSENİ (marka / model / motor) ve jeneratif marka-model sayfaları

**Sahibi:** KraL (baş mimar) · **Kaynak:** Okan → BaBa (2 Ağu 2026) → KraL
**Durum:** SPEC — icra başlamadı. Sayı içeren her satır ölçümle dolacak, tahmin yazılmayacak.

## 0. NİYET (Okan'ın cümlesi — kabul bunun üstüne kurulur)

> Müşteri bir marka/model ya da motor sayfasına girdiğinde (ör. Toyota Corolla, Volvo Penta)
> ona uyan **TÜM** ürünleri — **fiziki + bizim üretim** — **tek seferde** görmeli.

Bugünkü hâl bunu vermiyor: kategoriler yığılıyor ve uyum bilgisi yapılandırılmış bir alanda
değil. Bu paket o eksiği kapatır.

---

## 1. KARAR — İKİ EKSEN AYRILIR (yığılmanın kökü budur)

| Eksen | Ne anlatır | Nerede durur | Örnek |
|---|---|---|---|
| **Kategori** | ürünün TÜRÜ / çalışma prensibi | `kategori` + `altkategori` | Marin > Elektrik |
| **Uyum** | ürünün NEYE UYDUĞU | **yeni** `uyum` alanı | Volvo Penta D2-55 |

🔴 **Marka / model / motor adı kategori ağacına GİRMEZ.** Yığılmanın sebebi tek ağaca hem tür
hem uyum bilgisi yüklemekti. 935 dolu `altkategori` işi TÜR eksenidir, aynen sürer.

---

## 1.5 ÖLÇÜLEN GERÇEK (2 Ağu, 16.874 kayıt — tasarımı bu değiştirdi)

| Eksen | Sayı |
|---|---|
| Toplam kayıt | 16.874 |
| `marka` dolu / boş | 14.555 / 2.319 |
| Tekil `marka` jetonu | 1.704 |
| Dizi uzunluğu | 0→2.319 · 1→6.921 · **2→6.918** · 3+→716 |
| İkiz yazım | **48 küme / 672 kayıt** |
| Kategori/altkategoride marka adı | **0** ✅ (kabul ölçütü 2 zaten sağlanıyor) |
| `tur: "fiziksel"` | 943 · `stokta` 943 |
| Metinde yıl deseni / OEM benzeri jeton | ~2.027 / ~2.341 (kaba tahmin) |

🔴 **En önemli bulgu: `marka` alanı zaten marka VE model karışımı.** En sık değerler arasında
`Ford` (2.572) ile birlikte `Focus` (272), `F-150` (198), `Fiesta` (188), `Golf` (182), `E46`
(104), `Mustang` (98) var — bunlar model. 6.918 kayıt tam 2 eleman taşıyor, yani fiilen
`[marka, model]` çifti zaten yazılmış ama **ayrım yok**.

**Sonucu:** backfill "metinden çıkar" işi DEĞİL, ağırlıkla "mevcut diziyi ayır" işi — maliyet
düşer, güven artar. 1.704 tekil jeton marka/model olarak sınıflandırılacak; ölçülebilir sinyal
ortak-geçiş derecesidir (marka çok farklı partnerle geçer, model tek partnerle). İkiz kümelerin
çoğu da model yazımı (`F-150|F150`, `RAV4|Rav-4`).

## 2. KARAR — `uyum` ŞEMASI

`marka` alanı **kaldırılmaz** (index.html filtresi, build.py, D1, edge kart sözleşmesi ve Ege
onu okuyor — blast radius kabul edilemez). Yerine:

```json
"uyum": [
  { "marka": "Volvo Penta", "model": "D2-55", "motor": "", "yil": [2003, 2015], "oem": "3580310" },
  { "marka": "Yanmar",      "model": "3YM30", "motor": "", "yil": [],           "oem": "" }
]
```

- **Dizi**, düz alan değil: bir ürün birden çok araca uyabilir. Düz `marka[]`+`model[]` çifti
  KARTEZYEN yalan üretir (Volvo D2-55 + Yanmar 3YM30 → "Volvo 3YM30" gibi olmayan eşleşme).
- `marka` **ZORUNLU**, kapalı sözlükten. `model` zorunlu değil ama boşsa sayfa üretmez.
- `motor` yalnız aynı modelin farklı motor seçenekleri ayrışıyorsa doldurulur.
- `yil`: `[baş, son]`; açık uç `[2015, 0]`. Boş dizi = bilinmiyor (uydurma YOK).
- `oem`: varsa orijinal/muadil parça no. Fiziki üründe kimlik zaten budur.
- Alan **yoksa** ürün uyumsuz sayılır — fail-closed, mevcut 16.874 kayıt bozulmaz.

### 2.1 İKİZ TANIM YASAĞI (bu evin en pahalı hata sınıfı)
`marka` ile `uyum[].marka` aynı gerçeği iki yerde tutar → sessizce ayrışır ([[ikiz-tanim-sessiz-ayrisma]]).
Kural: **`uyum` varsa `marka` ondan TÜRETİLİR** (tekilleştirilmiş `uyum[].marka` kümesi), elle
yazılmaz. Kapı bunu **fail-closed** ölçer: `uyum` dolu ve `marka != türetilen küme` → KIRMIZI.
`uyum` boş olan eski kayıtlarda `marka` yazıldığı gibi kalır (regresyon 0).

### 2.2 KANONİK SÖZLÜK — TEK KAYNAK
- **Marka = KAPALI küme.** Tek kaynak `tools/arama.py` (`ALTKATEGORI_IZINLI` ile aynı desen).
  Kümede olmayan marka partiden GEÇMEZ. "V.Penta / VolvoPenta / Volvo Penta" ikizi doğmadan boğulur.
- **Model = AÇIK küme** (önceden sayılamaz), ama **normalize edilir** ve normalize sonrası
  çakışan farklı ham yazımlar KIRMIZI yanar (aynı normalize değere düşen 2+ ham değer = ikiz).
- Kümeyi genişletmek `Elektrik` kaleminde izlenen yolun aynısı: önce küme main'e iner, sonra
  parti yazılır. Tersi fail-closed reddedilir.

---

## 3. KARAR — FİZİKİ / ÜRETİM AYRIMI: YENİ ALAN AÇILMAZ

Ayrım için alan **zaten kararlı**: `"tur": "fiziksel"`, alan yoksa özel üretim
([[fiziksel-urun-ayrimi]], 31 Tem Okan kararı). İkinci bir alan açmak ikiz tanım üretir.
Marka-model sayfasında ayrım **ayrı sayfa değil**, kartta rozet + filtre çipidir.

### 🔴 3.1 OKAN KAPISI — CAYMA HAKKI (kod kapatamaz)
Fiziki üründe 14 gün cayma hakkı VAR, özel üretimde YOK; mesafeli satış + teslimat-iade
sayfaları şu an **tek dil** konuşuyor. Bu paket ikisini **yan yana** gösterdiği için risk
görünür hâle gelir. Sayfalar ayrışana kadar bu HUKUKİ açıktır ve karar Okan'dadır.
Bu paket o kararı beklemeden ilerleyebilir; **canlıya alma** o karara bağlıdır.

---

## 4. KARAR — MARKA-MODEL SAYFASI NASIL ÜRETİLİR

Sayfa = uyum alanı eşleşen tüm ürünler (fiziki + üretim yan yana), tür çipleriyle daraltma.
Elle kategori bakımı YOK.

### ✅ KARAR VERİLDİ — SAYFALAR **EDGE**'DE ÜRETİLİR (ölçüldü 2 Ağu, 12/12 canlı sayfa)

| Ölçüm | Değer |
|---|---|
| Ortalama ürün sayfası | **59.873 bayt** (~60 KB) |
| Sıkıştırılmamış yayın tahmini | **1,02 GB** |
| Bildirilen sıkıştırılmış artefakt | 0,286 GB |
| Sitemap | 17.634 URL (50.000 tavanına **32.366** yer) |

**Karar:** marka-model sayfaları `build.py` ile **statik üretilmeyecek**, **edge'de** render
edilecek. Gerekçe ölçülü: yayın zaten ~1,02 GB'ta, GitHub Pages'in ~1 GB sınırına **dayanmış**;
binlerce yeni sayfa × 60 KB bu duvarı kesin aşar. Sitemap tarafında yer VAR (32k), yani sınır
sayfa sayısı değil **bayt**tır. Edge sayfası ayrıca ürün eklendikçe kendiliğinden tazelenir,
build/deploy kuyruğuna girmez.

### 🔴 BU ÖLÇÜMÜN ÇIKARDIĞI AYRI RİSK (bu paketin parçası DEĞİL, ama kritik yolda)
Yayın **bugün** ~1,02 GB — yani hiçbir yeni sayfa eklemesek de sınıra dayalıyız ve katalog
büyüdükçe aşacağız. Kök sebep sayfa **ağırlığı**: 60 KB bir ürün sayfası için çok fazla (SEO
zenginleştirmesiyle 9,4 KB → 60 KB, ~6×). Sayfa ağırlığını düşürmek artık ayrı ve **öncelikli**
bir kalemdir; uyum ekseni onu beklemez ama katalog büyümesi ona bağlıdır. Kalem KraL'da.

⏳ **AÇIK PARAMETRE — sayfa açma eşiği:** bir marka-model çifti en az **N** ürün eşlerse sayfa
açılır. N ölçümden gelecek (marka başına ürün dağılımı). Sebep: tek ürünlük binlerce ince sayfa
= doorway/thin-content SEO riski. Eşiğin altındaki eşleşmeler marka sayfasında filtre olarak
kalır, kendi sayfası olmaz.

---

## 5. SIRA (bağımlılık zinciri — atlanırsa canlı kırılır)

1. **Sözlük + şema + kapı** (kod, tüketici YOK) — `tools/arama.py` kanonik marka kümesi,
   `uyum` doğrulayıcı, parti kapısı fail-closed. **KraL düzlemi.**
2. **D1 kolonu ÖNCE canlıya** — `python3 tools/d1-sync.py --sema`, `PRAGMA table_info` ile
   VAR olduğu doğrulanır, **ANCAK ONDAN SONRA** kolonu SELECT eden kod push'lanır. Ters sıra
   tüm oturumların push'unu kırar ([[ege-d1-bagimliligi]] şema sıra kuralı).
   ⚠️ Yeni kolon `urun_hash`'e **KATILMAZ** (yerel↔CI thrash, [[d1-baski-hash-thrash]]);
   hedefli UPDATE yazılır.
3. **Backfill** — token yakan amele iş → **Codex partileri**, dar spec + `-o son-mesaj.txt`.
   🔴 `urunler.json`'a yazan **tek yazar MaCiT**'tir; partiler onun düzleminde koşar, KraL yazmaz.
4. **Uç + arama** — edge kart sözleşmesine alan, gerekiyorsa haystack. 🔴 Haystack'e giriyorsa
   **site ve Ege AYNI ANDA** genişler; tek taraflı değişiklik pariteyi sessizce ayırır.
   **HocA düzlemi.**
5. **Sayfa üretimi + kırılım (breadcrumb) + sitemap** — KraL düzlemi, madde 4'ün kararına göre.
6. **Ağaç budama + 301** — marka adı taşıyan kategori düğümleri kaldırılır, eskiler yeni sayfaya
   yönlendirilir. ⚠️ GitHub Pages sunucu tarafı 301 vermez; yönlendirme yolu (Cloudflare kuralı
   ya da sayfa içi) ayrıca kararlaştırılacak.
7. **Yeni ürün doğuştan alanlı** — MaCiT hasat hattı, KaaN jeneratör kendi düzleminde.

---

## 6. KABUL (hepsi ÇALIŞTIRILABİLİR — "bakıldı iyi" kabul değil)

1. Örnek bir marka-model sayfasında **fiziki + üretim ürün BİRLİKTE** listeleniyor (test).
2. Kategori ağacında marka/model adı taşıyan düğüm sayısı = **0** (test).
3. Parti kapısı: biçimsiz / sözlük dışı / kartezyen uyum kaydı partiden **GEÇMEZ** (fail-closed,
   mutasyon tablosuyla kanıtlanır).
4. İkiz kapısı: `uyum` dolu iken `marka` elle bozulursa **KIRMIZI** (2.1).
5. Backfill kapsamı **sayıyla** raporlanır: kaç kayıt eşlendi / kaç ELE kaldı / kaç ret.
6. Parite: `node tools/parite-test.js` + `node tools/parite-ege.js` değişiklikten sonra da
   BİREBİR; ölçülemeyen eksene "yeşil" denmez, **ÖLÇÜLEMEDİ** yazılır.
7. D1 içerik ekseni: `d1-sync.py --durum` hash uyuşmaz/eksik/fazla = 0. ⚠️ Sayı teyidi alan
   değişimini GÖRMEZ — yazılan değer **geri okunarak** doğrulanır.
