# PAKET — K206: 8 üretecin sarı seri SİTE düzlemine bağlanması

**Tarih:** 19 Ağustos 2026 · **Yazan:** KraL-K206 site chip'i · **Dal:** `kral/k206-uretec-baglama`
**Kaynak teslim:** TeKiN'in 17 Ağu tarihli mühendis raporu (`~/dev/pruvo-jenerator`) + `render-teslim/*.png`

Bu paket, TeKiN'in teslim ettiği 8 üreteci (gyro · kupler · masatabela · planetdisli ·
saklama · spinner · zar · zincir) siteye bağlamak için **ölçülmüş** bağımlılık haritasını,
çivilenmiş kararları ve kalan ödevi taşır. Öncül yok; her satırın arkasında koşulmuş bir
komut var.

---

## 1. BAĞLAMA GERÇEKTE KAÇ TEMAS NOKTASI? (ölçüldü — mimar spec'i 5 sayıyordu, 7 çıktı)

Bir sarı seri ailesinin siteye bağlanması için değişmesi gereken yerler:

| # | Temas noktası | Düzlem | Zorunlu kılan kapı |
|---|---|---|---|
| 1 | `jenerator/urunler/<id>.json` şeması | **KraL** | — (veri kaynağı) |
| 2 | `urunler.json` kaydı (`parametrik:true`) | **MaCiT** | `jenerator/test/kabul.py` TEST 8 |
| 3 | `jenerator/hacim.js` `<aile>()` fonksiyonu | **TeKiN** | `jenerator/test/kabul.py` TEST 8 |
| 4 | `jenerator/test/esleme/<aile>.json` | **TeKiN** | `jenerator/test/dogrula.py` |
| 5 | `jenerator/test/fiyat-test.js` üç kilit | **KraL** | `fiyat-test.js` (drift kilidi) |
| 6 | `secenekler.js` `HACIM_DOGRULANMIS_AILELER` | **TeKiN ölçer, KraL yazar** | `parametrikFiyatKurus` |
| 7 | `ONIZLEME_AILELER` + `eslem-ozel.json` + derleyici paketi | **TeKiN + paket** | `tools/onizleme-kapisi.py` |

**#5'in üç kilidi** (`jenerator/test/fiyat-test.js`): `esit("şema sayısı 23", …)` (satır 114) ·
`TABAN_FIYATLAR` haritası (satır 79) · `KAPALI_AILELER` / `ACIK_AILELER` listeleri (satır 336-341,
sayaç iddiası dâhil). Üçü de aile eklenince ELLE güncellenir; biri unutulursa test kırmızı.

### 🔴 Bulgu 1 — dilim BÖLÜNEMEZ: şema tek başına inemez
`jenerator/test/kabul.py:546`:
```python
eksikler = ["KAPSAM DISI (sema var, test edilmiyor): " + uid
            for uid in sorted(sema_tanimli - test_edilen)]
```
`test_edilen` **`urunler.json`'daki `parametrik:true` kayıtlarından** gelir. Yani
`jenerator/urunler/` içine kayıtsız bir şema koymak CI'ı (nöbet `kabul.yml` → `nobet.yml:2346`)
KIRMIZI yakar. Muafiyet kümesi (`SEMA_FIXTURE`) yalnız `ornek-plaka` fikstürünü tutar ve
**bir ölçümü alabilmek için genişletilmez** ([[ucuncu-tekrar-sinif-kapisi]]).

**ÖLÇÜM — üç nokta, tek eksen (kabul.py TEST 8; `rc` değil EKSEN ölçüldü, çünkü rc tabanda da 1):**

| Aşama | TEST 8 | Basılan satır |
|---|---|---|
| TABAN (dokunulmamış dal) | **YEŞİL** | `[YESIL] TEST 8 — kapsam 23/23 + sema-aciklama tutarliligi` |
| PROBE (1 şema, `urunler.json` kaydı YOK) | **KIRMIZI** | `[KIRMIZI] TEST 8 — kapsam 23/24` + `KAPSAM DISI (sema var, test edilmiyor): olcuye-ozel-gyro-sonsuz-donen` |
| GERİ (şema silindi — çürütücü kontrol) | **YEŞİL** | eksen geri döndü, `git status --porcelain` BOŞ |

Aynı probe'da `node jenerator/test/fiyat-test.js` **0 → 1**: `şema sayısı 23 → 24` ·
`tabanFiyatTL <yeni id> → 280 (beklenen undefined)` · `kapı kapsamı → ["gyro"]`.

→ **Şema + `urunler.json` kaydı + `hacim.js` fonksiyonu AYNI dilimde iner.** K206'nın
"site düzlemi şimdi, kayıtlar sonra" ayrımı uygulanabilir değildir; mimar hükmü ister.

### 🔴 Bulgu 2 — fiyat, hacim kalibrasyonu olmadan ÜRÜN YÜZEYİNE ÇIKMAZ
`secenekler.js` `parametrikFiyatKurus` ilk satırı:
```js
if (!hacimDogrulanmisMi(aile)) { return null; }
```
`HACIM_DOGRULANMIS_AILELER`'de olmayan aile **null** döner → ürün sayfasında sayısal fiyat
YOK, JSON-LD'de `price` YOK, kartta "Ölçüye özel fiyat", Worker sepeti 400
`hacim-dogrulanmamis` ile reddeder. Bunu `tools/kapali-aile-fiyat-kapisi.py` ölçer ve
KORUR (bu bir kusur değil, kasıtlı fail-closed).

Listeye giriş şartı, `hacim.js` formülünün **gerçek üretim motoruna (OpenSCAD)** karşı
ölçülmüş sapmasıdır (kabul sınırı %3; tabloda her ailenin en kötü sapması yazılıdır).
Bu ölçüm OpenSCAD + `.scad` ister → **TeKiN düzlemi.** TeKiN bugüne kadar yalnız
*varsayılan noktadaki taban hacmi* ölçtü (divergence teoremi), **sapma ızgarası ölçmedi.**

→ 8 ailenin **taban fiyatı ancak TeKiN'in kalibrasyonundan sonra müşteriye görünür.**
Kalibrasyonsuz inerlerse 8 ürün "satışa kapalı" olarak yayınlanır (sayfa var, fiyat yok,
sipariş WhatsApp'a düşer) — bu meşru bir ara durumdur ama **karar mimarındır.**

### 🔴 Bulgu 3 — 3D önizleme, derleyici paketine bağlı
`onizleme/derleyici/paket-parmakizi.json` derleyici imajındaki dosyaları sayar: **25 `.scad`
+ `eslem-ozel.json`**; 8 üretecin HİÇBİRİ pakette yok. `tools/onizleme-kapisi.py:816`
"SERVIS-DISI AILE" ile kırmızı yanar: bir aileyi `ONIZLEME_AILELER`'e eklemek =
"Önizle (3D)" düğmesinin O ÜRÜN SAYFALARINDA MÜŞTERİYE görünmesi (`ONIZLEME_3D_ACIK = true`).
`eslem-ozel.json` repoda YOK (gitignore; R2 paketinden gelir).

→ **`ONIZLEME_AILELER` bu dilimde DOKUNULMAZ.** Önizleme, 8 `.scad` derleyici paketine
girip imaj yeniden kurulduktan sonra AYRI bir dilimdir.

---

## 2. ÇİVİLENMİŞ KARARLAR (mimar, 19 Ağu — yeniden yargılanmaz)

1. **`saklama` AYRI AİLE** — kavanoz ailesine seçenek olarak katılmaz.
2. **`gyro` şema varsayılanı `doku="duz"`** — `.scad`'a DOKUNULMAZ (motor varsayılanı `elmas` kalır).
3. **8 taban fiyat (PLA, TL):**

| Aile | Taban fiyat | TeKiN'in ölçtüğü taban hacim (mm³) | Ölçüm noktası |
|---|---|---|---|
| gyro | **280** | 5 780 | ⚠️ `doku="elmas"` (bkz. Bulgu 4) |
| kupler | **190** | 53 370 | varsayılan |
| masatabela | **170** | 14 150 | varsayılan |
| planetdisli | **350** | 22 270 | varsayılan (katalog tavanına eşit, aşım YOK) |
| saklama | **160** | 20 950 | varsayılan |
| spinner | **240** | 12 020 | varsayılan |
| zar | **140** | 6 750 | varsayılan |
| zincir | **220** | 9 790 | varsayılan |

### 🔴 Bulgu 4 — karar ②, gyro'nun taban hacmini GEÇERSİZ KILDI (ölçüldü)
`jeneratorler/gyro.scad:218` `_doku_neg()` bir **NEGATİF** modüldür (satır 272'de `difference`
ile gövdeden ÇIKARILIR). Yani `doku="elmas"` malzeme **eksiltir**; `doku="duz"` hacmi
**BÜYÜKTÜR**. TeKiN'in 5 780 mm³ ölçümü `elmas` ile alındı.

Taban fiyat sözleşmesi (`tools/taban-fiyat-tablosu.md`): *"Taban fiyat = ürünün **varsayılan
ölçülerdeki** PLA satış fiyatı"* ve formül `fiyat = taban × max(1, hacim/tabanHacim) × …`.
Şema varsayılanı `duz` olurken `tabanHacimMm3` `elmas` değeri kalırsa, **sitenin kendi
varsayılanında oran > 1 olur ve müşteri 280 TL'nin ÜSTÜNDE bir tutar görür.** Sessiz para
kusuru sınıfı.

→ **ÖDEV (TeKiN):** `gyro`'nun taban hacmini `doku="duz"` varsayılanıyla YENİDEN ölç;
5 780 sayısı bu şemada KULLANILMAZ.

### 🔴 Bulgu 5 — 8 ürün ZATEN KATALOGDA, sabit fiyatla satılıyor → iş "EKLEME" değil "DÖNÜŞTÜRME"
`urunler.json`'da, bu 8 üretecin ÜRETTİĞİ ÜRÜNLER **parametrik olmayan, sabit fiyatlı
kayıtlar** olarak zaten yayında. Hepsi `lisans` YOK (kendi tasarımımız sınıfı), 2-3 görselli.
Eşleşme isim benzerliği DEĞİL — açıklamalar `.scad` parametre sözlüğünü birebir tekrarlıyor:

- `kisiye-ozel-harf-sayi-kupleri` → *"kırlangıç-kuyruğu bağlantısıyla birbirine geçer"* =
  `kupler.scad` `birlesim="dovetail"`.
- `kisiye-ozel-oyun-zari` → *"d4, d6, d8, d10, d12, d20, d32…"* = `zar.scad` `tip` listesi.
- `moduler-saklama-kabi-pod` → *"segmentleri birbirine vidalayıp kule"* = `saklama.scad` `segment`.
- `dekoratif-zincir` → *"Kolye · Bileklik · Anahtarlık"* + *"bakla şekli, boyut, uzunluk"* =
  `zincir.scad` `kullanim` / `bakla_sekli` / `bakla_boyut` / `uzunluk`.
- `kisiye-ozel-masa-tabelasi` → *"Meşgul / Müsait / Toplantıda"* = `masatabela.scad`
  varsayılanı `yazi="OKAN|MÜSAİT"`.
- `masaustu-gyro-fidget-spinner` = `spinner.scad` · `kisiye-ozel-gyro-kolye-madalyon` =
  `gyro.scad` (bail/kolye + merkez yazı) · `planet-disli-fidget-stem` = `planetdisli.scad`.

| Yeni sarı aile | Önerilen taban | Kataloğdaki İKİZ (sabit fiyat, `parametrik:false`) | Fark |
|---|---|---|---|
| gyro (280) | 280 | `kisiye-ozel-gyro-kolye-madalyon` — Dekorasyon, **500 TL** | −44% |
| spinner (240) | 240 | `masaustu-gyro-fidget-spinner` — Oyun/Hobi, **500 TL** | −52% |
| kupler (190) | 190 | `kisiye-ozel-harf-sayi-kupleri` — Oyun/Hobi, **200 TL** | −5% |
| masatabela (170) | 170 | `kisiye-ozel-masa-tabelasi` — Dekorasyon, **500 TL** | −66% |
| planetdisli (350) | 350 | `planet-disli-fidget-stem` — Oyun/Hobi, **500 TL** | −30% |
| saklama (160) | 160 | `moduler-saklama-kabi-pod` — Ev, **650 TL** | −75% |
| zincir (220) | 220 | `dekoratif-zincir` — Dekorasyon, **300 TL (30 cm)** | −27% |
| zar (140) | 140 | `kisiye-ozel-oyun-zari` — Oyun/Hobi, **200 TL** ("RPG · D&D · d4–d60") | −30% |

**İKİ SONUÇ:**

**① İş yeniden tarif edilmeli.** Bu dilim `urunler.json`'a 8 YENİ kayıt EKLEMEZ — **mevcut 8
kaydı DÖNÜŞTÜRÜR**: `"parametrik": true` + `"fiyat": ""` (boş) + `"kategori": "Jeneratör"`.
Yeni kayıt eklemek aynı ürünü sitede İKİ KERE listelerdi; dönüştürme hem mükerrerliği hem
[[okan-hukmu-urun-silinmez-koken-intern]] ("ürün SİLİNMEZ") sorununu kökten kaldırır. Ürün
id'leri KORUNUR → mevcut `/urun/<id>/` adresleri, SEO ve R2 görselleri **kırılmaz**.
Yan etki: 3 kategori (Oyun/Hobi, Dekorasyon, Ev) → `Jeneratör`'e taşınır; kategori sayaçları
ve hub sayfaları değişir (`tools/kategori-parite-test.py` + `kategori-kapisi.py` ölçer).

**② Fiyat DÜŞÜŞÜ Okan kapısıdır.** TeKiN fiyatları **parametrik katalog bandına**
(kutu/dişli/kavanoz) oturttu; **bu ürünlerin bugünkü kendi satış fiyatlarıyla kıyaslamadı.**
Dönüştürme, 8 ürünün başlangıç fiyatını yukarıdaki tabloda görülen oranlarda **düşürür**
(saklama −75%, masatabela −66%, spinner −52%). Sabit fiyat "her ölçüde tek fiyat",
parametrik taban ise "en küçük ölçünün zemini" olduğu için düşüş bir kısmı MEŞRUDUR — ama
%75'lik fark fiyat kararıdır, mühendislik kararı değil.
→ **Karar çıkmadan dönüştürme yapılmaz.**

---

## 3. KUPLER HÜKMÜ — BAĞLANIR (ölçüldü, çelişki çözüldü)

TeKiN'in raporu kupler için kendi içinde çelişiyordu: bir bölüm "düzeltildi, render
güncellendi, OKAN düz ve doğru sırada", hemen altındaki paragraf "kusuru olduğu gibi
gösterir — katalog görseli olarak KULLANILMAZ".

**Ölçüm:**
- Düzeltme commit'i `2a58c2af` — `2026-08-17 17:01:57 +0300`.
- Teslim commit'i `39fe65a7` — `2026-08-17 17:05:54 +0300`, "BLOKE cozuldu";
  `render-teslim/kupler.png` **Bin 1075802 → 1120701** (dosya gerçekten değişti),
  mühendis raporu +12/−11 (başlık `🔴 BLOKE` → `✅ DÜZELTİLDİ`).
- Dosya damgası: `kupler.png` **17:05**; diğer 7 render **16:21** (düzeltme öncesi parti).
- Görsel denetimi (`Read`): dört küp soldan sağa **O · K · A · N**; glifler AYNALI DEĞİL,
  söz sırası DOĞRU.

**Hüküm: `kupler` BAĞLANIR.** Çelişen paragraf, düzeltme commit'inin silmeyi unuttuğu
**bayat artıktır** (aynı commit başlığı değiştirmiş, o paragrafa dokunmamış). TeKiN'den
taze render İSTENMEZ.

→ Küçük ödev (TeKiN, bloklamaz): mühendis raporundaki bayat paragraf silinsin ki üçüncü
bir okuyucu aynı çelişkiye düşmesin.

---

## 4. ŞEMA TASLAKLARI — parametreler `.scad`'dan OKUNDU

Aşağıdaki parametre adları/varsayılanları `~/dev/pruvo-jenerator/jeneratorler/<aile>.scad`
kaynağından birebir alındı (uydurma YOK). **`[a:b]` yazan yerlerde aralık `.scad`'da
BEYAN EDİLMİŞTİR; beyansız sayısal parametrelerin `min`/`max`/`adim` değerleri
TeKiN'in ölçtüğü ÜRETİLEBİLİRLİK ZARFINDAN gelir — KraL uydurmaz.**

> 🔴 **Neden uydurulmaz:** bu depoda ölçülmüş kusur sınıfı tam budur — şema kapısından
> GEÇEN ama üretim ucunun 400/422 ile REDDETTİĞİ aralıklar (`petek` %50,0 · `cetvel` %66,7).
> Bugün `cetvel`/`kase`/`petek`/`vida` ailelerinin satışa kapalı olmasının sebebi fiyat
> formülü değil, **şema aralığı kusurudur**. Aralığı ölçmeden yazmak o dört aileyi
> sekize çıkarır.

| Aile | `.scad` parametreleri (varsayılan) | `.scad`'da beyanlı aralık | TeKiN'den ÖLÇÜM istenen |
|---|---|---|---|
| **gyro** | `yazi=OKAN` · `halka_sayisi=2` · `cap=45` · `doku=elmas`→**şemada `duz`** · `kalinlik=4` · `bosluk=0.35` · `pim_bosluk=0.25` | `halka_sayisi [1:4]` · `cap [20:100]` | `kalinlik` · `bosluk` · `pim_bosluk` zarfı + **`duz` taban hacmi** |
| **kupler** | `icerik=OKAN` · `tip=harf` · `birlesim=dovetail` · `boyut=24` · `kose=2` · `stil=emboss` | seçim listeleri beyanlı | `boyut` · `kose` zarfı · `icerik` uzunluk tavanı |
| **masatabela** | `yazi=OKAN\|MÜSAİT` · `stil=emboss` · `cerceve=true` · `cift_yuz=false` · `yazi_boyutu=10` · `panel_kalinlik=3` · `yatma=14` | seçim listeleri beyanlı | `yazi_boyutu` · `panel_kalinlik` · `yatma` zarfı |
| **planetdisli** | `gezegen_sayisi=4` · `boyut=orta` · `helis=false` · `merkez_delik=6` · `backlash=0.35` · `kalinlik=8` | `gezegen_sayisi [3:6]` · `boyut` listesi | `merkez_delik` · `backlash` · `kalinlik` zarfı |
| **saklama** | `parca=ikisi` · `cap=40` · `yukseklik=45` · `duvar=2` · `doku=ribs` · `bolme=false` · `dis_adim=3.5` · `bosluk=0.15` | seçim listeleri beyanlı | `cap` · `yukseklik` · `duvar` · `dis_adim` · `bosluk` zarfı |
| **spinner** | `yazi=""` · `halka_sayisi=5` · `cap=60` · `donus=floating` · `doku=duz` · `kalinlik=5` · `bosluk=0.4` | `halka_sayisi [1:20]` · `cap [10:140]` | `kalinlik` · `bosluk` zarfı |
| **zar** | `tip=d6` · `icerik=sayi` · `boyut=19` · `yuvarlatma=0.8` · `isaret_z=1.1` · `kenar_pay=0.8` | `tip` 8 değer · `icerik` 3 değer | `boyut` · `yuvarlatma` · `isaret_z` · `kenar_pay` zarfı |
| **zincir** | `kullanim=kolye` · `uzunluk=30` · `bakla_sekli=circle` · `bakla_boyut=orta` · `bosluk=0.45` | seçim listeleri beyanlı | `uzunluk` · `bosluk` zarfı |

**Sarı seri kuralları (BAĞLAYICI, `urunler.json` kayıtları yazılırken):**
`"parametrik": true` · `lisans`/atıf **YOK** · `"fiyat": ""` **BOŞ** (taban fiyat
`taban-fiyatlar.js`'ten gelir) · `"kategori": "Jeneratör"` · açıklamada **"her renk" DEME** ·
açıklamada **"3D baskı" DEME** · `Yaklaşık dış ölçüler: A × B × C mm` (TeKiN'in bbox'ı).

---

## 5. ÖDEV — sıradaki dilim için TAM liste

### TeKiN'e (kendi evi, OpenSCAD orada)
1. 8 aile için `jenerator/hacim.js` fonksiyonu (analitik hacim) — `hacimFormulu` adıyla birebir.
2. 8 aile için `jenerator/test/esleme/<aile>.json` (`scad`, `fonksiyon`, `esleme`, `sabit`).
3. 8 aile için **sapma ızgarası ölçümü** (hacim.js ↔ üretim motoru, kabul sınırı %3) →
   `HACIM_DOGRULANMIS_AILELER` satırına yazılacak "en kötü sapma %" sayısı.
4. 8 aile için **üretilebilirlik zarfı**: yukarıdaki tabloda "ÖLÇÜM istenen" sütunundaki
   her parametrenin `min`/`max`/`adim` değeri (şema kapısından geçip motorun reddettiği
   nokta sayısı **0** olacak şekilde).
5. **`gyro` taban hacmi `doku="duz"` ile yeniden ölçülsün** (Bulgu 4).
6. Mühendis raporundaki bayat kupler paragrafı silinsin (Bölüm 3).

### MaCiT'e (katalog yazıcısı — d2b dilimleri bitince)
7. 🔴 **YENİ KAYIT EKLEME — MEVCUT 8 KAYDI DÖNÜŞTÜR** (Bulgu 5①). Şu 8 id'de:
   `kisiye-ozel-gyro-kolye-madalyon` · `masaustu-gyro-fidget-spinner` ·
   `kisiye-ozel-harf-sayi-kupleri` · `kisiye-ozel-masa-tabelasi` · `planet-disli-fidget-stem` ·
   `moduler-saklama-kabi-pod` · `kisiye-ozel-oyun-zari` · `dekoratif-zincir`
   → `"parametrik": true` · `"fiyat": ""` (BOŞ) · `"kategori": "Jeneratör"`; `id` ve
   `gorseller` KORUNUR. **Şema dosyalarıyla AYNI commit'te** inmeli (Bulgu 1).
   Fiyat düşüşü Okan onayına bağlıdır (Bulgu 5②) — onaysız dönüştürme YOK.
8. Görsel işi: bu 8 kaydın görselleri ZATEN R2'de (2-3 adet/kayıt). TeKiN'in
   `render-teslim/*.png` karelerinin eklenmesi/değiştirilmesi AYRI ve isteğe bağlıdır.

### KraL'a (bu ev, yukarıdakiler gelince mekanik)
9. `jenerator/urunler/<id>.json` × 8 (Bölüm 4'ün parametreleri + TeKiN'in zarfı +
   `tabanHacimMm3` + Bölüm 2'nin `tabanFiyatTL`'si).
10. `jenerator/test/fiyat-test.js`: `şema sayısı 23` → `31` · `TABAN_FIYATLAR`'a 8 satır ·
    `KAPALI_AILELER`/`ACIK_AILELER` + `[4, 19]` sayaç iddiası güncellensin.
11. `secenekler.js` `HACIM_DOGRULANMIS_AILELER` — **yalnız TeKiN'in ölçtüğü sapma sayısıyla.**
12. `tools/taban-fiyat-tablosu.md` yeniden üretilsin (`python3 jenerator/test/fiyat-tablosu-uret.py`).

### AYRI DİLİM (bu paketin kapsamı DIŞI)
13. 8 `.scad` derleyici paketine + `eslem-ozel.json` eşlemi + imaj yeniden kurulumu →
    ancak ondan sonra `ONIZLEME_AILELER` (Bulgu 3).

---

## 6. KABUL — sıradaki dilim neyi koşturacak

```
python3 tools/kategori-parite-test.py
python3 tools/kategori-kapisi.py
python3 tools/onsecim-parite-kapisi.py
node    jenerator/test/vitrin-kabul.js
python3 tools/kapali-aile-fiyat-kapisi.py
python3 tools/ci-kapsam-test.py
python3 jenerator/test/kabul.py
node    jenerator/test/fiyat-test.js
```
Hepsi rc=0 olmadan dal main'e alınmaz.

🔴 **"Eklendi" kabul DEĞİL — SONUÇ SAYISI şart** (K201 sınıfı: kayıt kendini ölçmez).
Fiyatın ürün yüzeyine yansıdığı `tools/kapali-aile-fiyat-kapisi.py`'nin **C/F eksenleriyle**
ölçülür (açık ailede sayfada sayısal "…,… TL" VAR + JSON-LD'de `price` VAR + kart metninde
sayısal tutar VAR + taban haritasındaki değer şemanın `tabanFiyatTL`'siyle AYNI).
8 aile kalibrasyonsuz inerse **B/E eksenlerinde** (kapalı aile: fiyat YOK, `InStock` YOK,
açıklayıcı metin VAR) ölçülür — hangisi olacağı mimarın Bulgu 2 hükmüne bağlıdır.
