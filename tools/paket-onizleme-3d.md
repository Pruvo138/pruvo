# İŞ PAKETİ — Sarı Seri İnteraktif 3D Önizleme (Faz C: Pilot)

Mimar paketi, 2026-07-16. Mühendis bu dosyayı baştan sona okur, sonra CLAUDE.md kurallarına
uyarak uygular. Sorular Okan'a DEĞİL mimara raporlanır.

## Karar çerçevesi (Okan, 16 Tem — DEĞİŞTİRİLEMEZ)

- Sarı seri ürünlerde müşteri parametreleri girer, "Oluştur" butonuyla modeli **canlı 3D**
  görür, biz üretip göndeririz (MakerWorld "Parametric Model Maker" UX'i referans).
- **Tek motor: üyelik üreteçleri** (`.uyelik-kodlar/*.scad`, gitignore'lu, BOSL2 bağımlı).
  `pruvo-jenerator` BU İŞTE KULLANILMAZ (ancak sıfırdan baskı testiyle kanıtlanırsa, ayrı karar).
- **Üreteç kodu istemciye ASLA gitmez** (lisans + ticari mahremiyet). Derleme sunucuda;
  tarayıcıya yalnızca derlenmiş mesh gider. openscad-wasm-tarayıcıda seçeneği REDDEDİLDİ.
- **Derleme sunucusu: Cloudflare Containers** (Okan seçimi; D1/R2/shop worker zaten CF'de).
- **Fiyat bu paketten ETKİLENMEZ:** hacim kapalı-form (`jenerator/hacim.js`), parametrik ödeme
  kanalı kapalı (`PARAMETRIK_ODEME_ACIK=false`). Bu paket salt GÖRSEL katman.
- Tedarikçi adı hiçbir commit'e, public dosyaya, rapora yazılmaz (repo PUBLIC).

## Keşif ölçümleri (Faz A, 16 Tem — tekrar ölçme, kullan)

- 18 ailenin 15'inin .scad'ı `.uyelik-kodlar/`'da; eksik 3 (bağlantı-konektör, montaj-braketi,
  dişli) bu pakete GİRMEZ (ayrı iş, Codex kaynak erişimini kontrol ediyor).
- Headless derleme (bu Mac, OpenSCAD 2026.06.12): tipik 0.2–0.9 s, tavan 1.36 s (pervane 6
  kanat Ø300). STL gzip tipik 40–260 KB; tavan 4 MB → önizleme SABİT DÜŞÜK $fn ile üretilir.
- STL watertight doğrulandı (o-ring hacmi kapalı-form torusla birebir).
- kase (damga) ailesi boş `metin` ile derlenmiyor → metin alanı zorunlu (pilot dışı, nota al).

## Pilot kapsamı

İki aile: **olcuye-ozel-profil-beam** (beamgenerator) + **olcuye-ozel-oring-conta**
(oringgenerator). İkisi de hafif (0.2–0.3 s, gzip <200 KB), yaygın ürünler. Diğer 13 aile
Faz D'de şema-güdümlü açılır — pilot mimarisi buna göre genel yazılır (aile = konfig satırı).

## Mimari

```
Ürün sayfası (pilot 2 aile)
  parametre formu (mevcut sarı konfigüratör şeması)
  "Önizle (3D)" butonu
    → POST /api/onizleme/olustur {aile, parametreler}
       Worker: şema doğrulama (shop/src/parametrik.js kapısı yeniden kullanılır)
               R2 önbellek bak (anahtar = aile + SHA-256(normalize parametreler))
               yoksa → Container binding: openscad -D ... (düşük $fn) → binary STL
               → R2'ye yaz → cevap
    ← gzip binary STL (veya R2 URL'si)
  viewer.js: saf WebGL mini gösterici (döndür/zoom/flat shading, ~300-600 satır,
             harici kütüphane YOK, repo dosyası)
```

## Adımlar ve KAPILAR

0. **Ön koşul keşfi (DUR-kapıları):**
   - Cloudflare hesabında Workers **Paid** planı aktif mi? (Containers şartı, $5/ay taban.)
     Değilse **DUR** → mimara rapor. Plan yükseltme = ödeme kararı = Okan; kendin yükseltme,
     Codex'e de yükselttirme.
   - Bu makinede Docker (veya wrangler'ın container build yolu) var mı? Yoksa **DUR** → rapor.
1. **POC imajı + soğuk başlatma ölçümü:** minimal imaj (debian-slim + openscad + BOSL2 +
   `.uyelik-kodlar` kopyası — imaj PRIVATE registry'de kalır). Basit HTTP servis: parametre →
   derle → STL. Deploy et, ölç: soğuk başlatma p50/p95 (≥10 istek), sıcak istek gecikmesi.
   **KAPI:** soğuk p95 > 10 s VE önbellekle maskelenemiyorsa **DUR** → mimara rapor
   (VPS'e dönüş kararı mimarın).
2. **Worker ucu:** `/api/onizleme/olustur` — şema kapısı + R2 önbellek + rate limit
   (IP başına 10/dk; önbellek isabetleri muaf) + derleme timeout 5 s + çıktı tavanı (2 MB).
   Metin/string parametreler OpenSCAD'e kaçışlanarak geçer — `-D` enjeksiyonu imkânsız olmalı.
3. **Ön yüz:** viewer.js + pilot 2 ailenin ürün sayfasında "Önizle (3D)" akışı (build.py
   şablonu). Mobil öncelikli: dokunmatik döndürme, yüklenirken iskelet/spinner.
   `.github/workflows/deploy.yml` BEYAZ LİSTESİNE yeni dosyaları eklemeyi UNUTMA
   (unutulursa canlıda 404 — sepette yaşandı).
4. **Kabul testleri (çalıştırılabilir script, "bakıldı" kabul değildir):**
   a. Şema dışı parametre → 400 (min/max/adım/tanımsız anahtar, curl).
   b. String parametreyle enjeksiyon denemesi (`"; cube(999); //` benzeri) → reddedilir,
      derlenmez.
   c. Aynı parametre 2. istek → R2 önbellek isabeti (ölçülebilir şekilde hızlı, Container'a
      gitmez).
   d. Dönen STL hacmi ile `jenerator/hacim.js` kapalı-form hacmi ≤ %3 sapma (2 ailede N=5
      rastgele parametre seti).
   e. Gecikme raporu: soğuk/sıcak/önbellek p50-p95 tablosu.
   f. Rate limit: 11. istek/dk → 429.
   g. Canlı ürün sayfasında viewer yükleniyor (endpoint 200 + gzip boyut tavanı).
5. **Teslim:** commit+push (isimsiz mesaj), Actions yeşil, canlı doğrulama, DEVAM.md
   güncelle (yazmadan önce YENİDEN OKU), mimara rapor: ölçüm tabloları + kabul çıktısı +
   yargı noktaları.

## Yapma / dikkat

- `.uyelik-kodlar/*.scad` içeriğini rapora/commit'e/public dosyaya KOPYALAMA.
- urunler.json'a dokunma; secenekler.js'e dokunacaksan tek kaynak ilkesini koru.
- Başka oturumun dosyasına dokunma (git status'ta yabancı değişiklik = bırak).
- Harici kütüphane/CDN yok; viewer dahil her şey bizim kod.
- Container imajına gereksiz şey koyma (imaj küçük = soğuk başlatma kısa).
