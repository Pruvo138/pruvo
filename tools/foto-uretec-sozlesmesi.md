# Fotoğraftan / ölçüden özel üretim — ÜRETEÇ SÖZLEŞMESİ v1 (KraL, 7 Eki 2026)

Sahibi: KraL (kategori motoru). Uyan: TeKiN üreteçleri (D ve R kolu). Tek kaynak bu dosyadır; repoya
`tools/foto-uretec-sozlesmesi.md` olarak girer. Değişiklik = sürüm artışı (`sozlesme: 2`), sessiz değişiklik YOK.

## 1. Çağrı
```
<uretec-komutu> --girdi <dizin>/girdi.json --cikti <bos-dizin>
```
- **rc 0** = başarı, çıktı dizininde §3'teki üç dosya VAR.
- **rc 2** = girdi reddi (ölçü aralık dışı, okunamayan dosya, boş metin, izinsiz malzeme…). Çıktı dizini BOŞ kalır; stderr'e tek satır `RED <sebep-kodu>: <açıklama>`. Sipariş `elle` aşamasına düşer.
- **diğer rc** = arıza (yeniden denenebilir). Yarım çıktı bırakılmaz (önce geçici dizine yaz, sonra taşı).
- Ağ YOK (veri kategorileri 21–24 dahil: rakım/OSM/yıldız verisi önceden yerel önbellekte), süre ≤ 300 sn, deterministik: aynı `girdi.json` + aynı girdi dosyaları → **aynı `model.3mf` sha256**.

## 2. `girdi.json`
```json
{
  "sozlesme": 1,
  "kategori": "litofan",
  "siparis_no": "PRV-…",
  "kalem": 0,
  "olcu_mm": 150,
  "renkler":   { "panel": "Beyaz", "ayak": "Siyah" },
  "malzemeler":{ "panel": "PLA",   "ayak": "PETG" },
  "parametreler": { },
  "dosyalar":  { "foto": "foto.png" }
}
```
- `olcu_mm` = ürünün **EN UZUN KENARI** (mm, tam sayı). Fiyatın ekseni de budur (`max(600 TL, olcu_mm × 10 TL)`, taban tür kaydında `fiyat.taban_tl`).
- `renkler` / `malzemeler` anahtarları = manifestteki `renk_bolgeleri[].kod`; değerler manifestteki izinli listeden. Liste dışı → rc 2.
- `parametreler` = manifest satırındaki `form` şemasının doldurulmuş hâli (dalga 2 parametrik: iç çap, diş sayısı…; metin kategorileri: `metin`, `url`; veri: `enlem`, `boylam`, `tarih`). Şema dışı anahtar → rc 2.
- `dosyalar` = girdi dizinine göre göreli yollar: `foto` (PNG/JPEG), `gri_harita` (PNG, litofan/rölyef — tarayıcıda çıkarılır), `svg`, `ses` (WAV ≤ 60 sn). Kategori yalnız manifestte beyan ettiği girdileri alır.

## 3. Çıktı dizini (üçü birden, başka dosya YOK)
| dosya | şart |
|---|---|
| `model.3mf` | `unit="millimeter"`, en çok **4 renk** (filament slotu), tek plaka, her parça **sızdırmaz** (manifold, kendini kesmeyen), tabanı Z=0, plaka **300×300 mm** içinde (sınır manifest `PLAKA_MM`; 7 Eki 2026: 250 → 300, H2D paylaşılan bant X 25–325 — çok parçalı ürün (yapboz) parçalarını bu banda raf düzeniyle dizer; geriye uyumlu ek, `sozlesme` sürümü aynı). Uzun kenar toleransı 3MF GEOMETRİSİNDEN ölçülür (koşucu; raf düzenindeki parçalar `ozet.parcalar[].tasima_mm` çıkarılarak birleşik ürün), özetteki nominal değerden DEĞİL. Ayaklı ürünlerde ayak AYNI dosyada ayrı obje. |
| `onizleme.png` | ≥ 1024 px uzun kenar, nötr fon, ürünün kendisi (müşteriye gösterilir; render olduğunu bölüm söyler). |
| `olcu.json` | aşağıdaki şema |

```json
{
  "sozlesme": 1,
  "kategori": "litofan",
  "uzun_kenar_mm": 150.0,
  "kutu_mm": { "x": 150.0, "y": 112.4, "z": 3.2 },
  "renk_sayisi": 2,
  "sizdirmaz": true,
  "ucgen": 412880,
  "hacim_cm3": 38.6,
  "alt_kenar_mm": 3.2,
  "parcalar": [ { "ad": "panel", "renk": "Beyaz" }, { "ad": "ayak", "renk": "Siyah" } ],
  "girdi_sha256": "…",
  "model_sha256": "…"
}
```
- `sizdirmaz` **true olmak ZORUNDA**; üreteç false üretirse rc ≠ 0 döner (false ile rc 0 = sözleşme ihlali).
- `uzun_kenar_mm` = `olcu_mm` ± %1 (D kolu). R kolu ± %3. **Tanım (Okan 7 Eki 15:4x):** nesnenin sınır kutusunun EN UZUN boyutu (x/y/z hangisi büyükse, ayak/çerçeve dahil tek nesne) — yalnız X/Y değil. Sunucu `kutu_mm.z` > `uzun_kenar_mm` (+tol) ise RED eder (`uzun-kenar-tolerans`); sağlayıcı kolunda 3MF geometrisi x/y/z'den ölçülür. Üreteç tarafındaki `ozet.json` netleştirmesi (`sozlesme: 2` notu) TeKiN işidir.
- `alt_kenar_mm` = ürün dik duruyorsa ayağa oturan kenarın ölçülen kalınlığı (plaket/litofan/rölyef). Ayak üreteci nominal değil BUNU kullanır (TeKiN 6 Eki bulgusu: plaket nominal 3,0 → ölçülen 6,61).
- `girdi_sha256` = kanonik girdi parmak izi: sha256(`girdi.json`'dan `sozlesme · kategori · olcu_mm · renkler · malzemeler · parametreler` + beyan edilen her dosyanın sha256'sı); **`siparis_no` ve `kalem` HARİÇ**. Üreteç boş bırakabilir — koşucu her başarılı üretimde bu değerle DAMGALAR. Sipariş öncesi önizlemenin modeli, sipariş girdisinin parmak izi AYNIYSA yeniden üretilmeden kopyalanır (7 Eki, geriye uyumlu ek — `sozlesme` sürümü aynı). `model_sha256` = `model.3mf` dosyasının sha256'sı.

## 4. Akış (sunucu ↔ üreteç)
Ödenen D/R siparişi `uretec-bekliyor` aşamasına girer. Üreteç koşucusu (Mac, TeKiN):
`GET /api/shop/yonet/foto/uretec-girdi?siparis=&kalem=` → girdi.json + dosyalar → komut → 
`POST /api/shop/yonet/foto/uretec-yukle?siparis=&kalem=` gövde = `model.3mf` (+ `olcu.json`, `onizleme.png` aynı çağrı ailesiyle) → sunucu `olcu.json`'u doğrular (§3 şartları + manifest aralığı) → `hazir`. Doğrulama düşerse `elle` + sebep.

## 5. Kabul (her kategori için, TeKiN tarafı)
- Manifest aralığının en az / orta / en çok ölçüsünde 3 + kategoriye özgü kenar vaka ≥ 2 = **≥ 5 set**, hepsi `sizdirmaz:true`, `uzun_kenar_mm` toleransta, renk ≤ 4.
- Determinizm: aynı girdiyle iki koşum sha256 eşit.
- Red kolu: aralık dışı ölçü + izinsiz malzeme + boş/bozuk girdi → rc 2, çıktı 0.
- Mutant: sızdırmazlık kontrolü kaldırılınca test KIRMIZI (SURVIVOR=0).
- Yasak: logo/marka içeren hazır şablon, "3D baskı" ifadesi, şehir adı (örnek görsellerde dahil).

## 6. Manifest satırı (KraL tarafı — kategori eklemek = üreteç + bu satır)
`kod · ad · aciklama · girdi[] · motor (D|M|R) · uretec (komut kimliği) · olcu_mm {en_az,en_cok} · renk_bolgeleri[] · malzemeler{} · form (parametre şeması) · ornek_kanit_izni[] · fiyat {formul:"mm_x_10tl", adim_mm:10}`.
`form` şemasında her alan `etiket` (gösterim adı, bölümde alanın başlığı) taşır; geriye uyumlu ek — `sozlesme` sürümü AYNI kalır.
Fiyat tablosu YOK (Okan 7 Eki 15:4x): `fiyat_kurus = olcu_mm × 1000` (cm × 100 TL), tek formül `foto-uretim-veri.js` `VERI.fiyatKurus`; sürgü adımı `fiyat.adim_mm`. `olcu_mm` = nesnenin sınır kutusunun EN UZUN boyutu (x/y/z hangisi büyükse, ayak/çerçeve dahil) — `uzun_kenar_mm` bu değerdir. Türün satışa açılması D1 `foto_acik` anahtarıyla (varsayılan KAPALI).
