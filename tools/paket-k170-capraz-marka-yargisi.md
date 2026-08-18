# PAKET K170 — 17 çapraz-marka çiftinin allow/deny yargısı

**Mimar:** KraL · **Tarih:** 18 Ağu 2026 · **Kalem:** K170
**Amaç:** `tools/model-uyelik-kapisi.py` K19 kırmızısını kapatmak. Kırmızının kaynağı VERİ
değil YARGI: 17 çapraz-marka çifti ne `ROZET_CAPRAZ_IZINLI` (allow) ne `ROZET_DISI_CIFT`
(deny) tablosunda. ETKİLENEN_ÜRÜN = 0 (ölçüldü); bu paket yalnız yargı yazar.

> 🔴 **BU PAKET HİÇBİR SAYFA AÇMAZ/KAPATMAZ diye VARSAYILMAZ, ÖLÇÜLÜR.** Üretim
> (`yayimlanir_mi`) yalnız deny tarafına bakar; deny'e giren 7 çiftin BUGÜN sayfası varsa
> o sayfa kapanır. Kabul satırında K11 `kaybolan=0` ekseni ZORUNLUDUR (ürün kaybolmaz;
> sayfa kapanabilir — kapanan sayfa RAPORLANIR, sessiz geçmez).

---

## MİMAR HÜKMÜ (bağlayıcı — gerekçeler satır satır tabloya yazılacak)

Uygulanan kural, 4 Ağu'da yazılmış olanın aynısıdır (yeni kural YOK):
**"Bir `/marka/X/M/` sayfası ancak M modeli GERÇEKTEN X rozetiyle satılmışsa doğar. Aynı
fiziksel araç başka marque'ta BAŞKA ADLA satılıyorsa, o marque'in sayfası KENDİ adıyla
açılır; ikizin adıyla AÇILMAZ."** Buna iki yerleşik alt-sınıf eklenir:
- **AD ÇAKIŞMASI** (emsal `Ford|sierra`/`Suzuki|sierra`, `BMW|gs`/`Lexus|gs`): aynı adı
  taşıyan AYRI araçlar → **iki kol da ROZET**.
- **ŞASİ/NESİL KODU** (emsal `Toyota|AE86` KUSAK_DISI): marka o adla bir araç SATMADI →
  **deny**, ürünler marka ağacında kalır.

### A) `ROZET_CAPRAZ_IZINLI` (allow) — 10 satır EKLENİR

| anahtar | sınıf | gerekçe (tabloya yazılacak öz) |
|---|---|---|
| `Ducati\|916` | ROZET | Ducati 916 gerçek superbike rozeti (1994-1998); Alfa'nın `916`'sı ŞASİ kodudur → AD ÇAKIŞMASI, emsal `Ford\|sierra` |
| `Alfa Romeo\|stelvio` | ROZET | Alfa Romeo Stelvio gerçek SUV rozeti (2016→) |
| `Moto Guzzi\|stelvio` | ROZET | Moto Guzzi Stelvio 1200 gerçek motosiklet rozeti (2008→); ikisi de Stelvio Geçidi'nden adını alır, rozet mühendisliği DEĞİL → AD ÇAKIŞMASI |
| `Citroen\|c5` | ROZET | Citroën C5 gerçek rozet |
| `Toyota\|aygo` | ROZET | Toyota Aygo gerçek rozet (A-segment üçlüsü 107/C1/Aygo); emsal BİREBİR mevcut `Peugeot\|107` ve `Citroen\|c1` satırları |
| `Vespa\|gts` | ROZET | Vespa GTS gerçek rozet |
| `Vespa\|primavera` | ROZET | Vespa Primavera gerçek rozet |
| `Vespa\|px` | ROZET | Vespa PX gerçek rozet |
| `Vespa\|largeframe` | ROZET | Vespa Largeframe gövde AİLE adı; emsal BİREBİR mevcut `("Vespa","Smallframe")` satırı |
| `Volvo\|mk1` | **BEKLER** | `Mk1` bir NESİL işaretidir, rozet DEĞİL — `Ford\|mk1` / `Volkswagen\|mk1` ile AYNI bekleyen hükmün üyesi. Sınıf hükmü K172'de verilir; BEKLER hata DEĞİL, görünür rapor kalemidir |

🔴 `Volvo|mk1` neden BEKLER, deny değil: `Ford|mk1` ve `Volkswagen|mk1` bugün BEKLER'dedir.
Volvo kolunu tek başına deny yazmak **aynı alana iki hüküm** koyardı
([[ayni-alan-iki-hukum-biri-sessiz]]). Üç kol TEK turda, TEK hükümle kapanır → **K172**.

### B) `ROZET_DISI_CIFT` (deny) — 7 satır EKLENİR

| anahtar | gerekçe (tabloya yazılacak öz) |
|---|---|
| `("Alfa Romeo", "916")` | `916` Alfa'nın TİP/ŞASİ kodudur (GTV/Spider 1995-2006); Alfa `916` rozetiyle araç SATMADI. Ürünler Alfa Romeo ağacında kalır; `916` sayfası Ducati'nindir |
| `("Peugeot", "C5")` | C5 Citroën rozetidir; Peugeot C5 diye bir araç satılmadı (PSA platform ortaklığı) — gerçek sayfa `/marka/citroen/c5/`. Emsal BİREBİR `("Audi","Golf")` |
| `("Peugeot", "C1")` | Peugeot'nun rozeti 107/108; C1 Citroën'in — gerçek sayfa `/marka/citroen/c1/`. Emsal BİREBİR mevcut `("Toyota","C1")` satırı (aynı A-segment üçlüsü, eksik kalmış üye) |
| `("Piaggio", "GTS")` | GTS bir VESPA rozetidir; Piaggio ana marque'tır, `Piaggio GTS` diye araç satılmadı — gerçek sayfa `/marka/vespa/gts/` |
| `("Piaggio", "Primavera")` | Primavera VESPA rozetidir — gerçek sayfa `/marka/vespa/primavera/` |
| `("Piaggio", "PX")` | PX VESPA rozetidir — gerçek sayfa `/marka/vespa/px/` |
| `("Piaggio", "Largeframe")` | Largeframe VESPA gövde aile adıdır (Smallframe'in karşılığı), Piaggio rozeti DEĞİL — gerçek sayfa `/marka/vespa/largeframe/` |

**Toplam:** allow 57 → **67** · deny 39 → **46** · yargısız 17 → **0**.

---

## İCRA (işçi)

1. `tools/arama.py` — `ROZET_CAPRAZ_IZINLI` sözlüğüne A tablosundaki 10 satırı, mevcut
   biçimde (yorum bloğu + `"marka|canon": ("SINIF", "gerekçe")`) EKLE. Yorum bloğu şunu
   taşısın: tarih (18 Ağu), kalem (K170), K166'nın kusuru ÜRETMEDİĞİ GÖRÜNÜR KILDIĞI,
   ETKİLENEN_ÜRÜN=0.
2. `tools/arama.py` — `ROZET_DISI_CIFT` sözlüğüne B tablosundaki 7 satırı EKLE.
3. `ROZET_CAPRAZ_IZINLI_SAYISI` / `ROZET_DISI_SAYISI` sayaçlarını güncelle.
4. `ROZET_CAPRAZ_IZINLI_IMZA` / `ROZET_DISI_IMZA` imzalarını **hesaplayarak** yaz —
   `python3 -c "import sys; sys.path.insert(0,'tools'); import arama; print(arama.rozet_capraz_imzasi(), arama.rozet_disi_imzasi())"`.
   🔴 İmzayı kapının hata metninden KOPYALAMA; fonksiyonu ÇAĞIRIP yaz.
5. Yeni anahtarların kanonu kapının okuduğu kanonla AYNI olmalı (`_bagimsiz_kanon`).
   `Alfa Romeo` / `Moto Guzzi` gibi BOŞLUKLU marka adlarının kapıdaki yazımını ÖLÇ, tahmin
   etme — yanlış yazım çifti yargısız BIRAKIR ve kapı yine kırmızı yanar.

## KABUL (hepsi ZORUNLU, çıktılar rapora BİREBİR yapıştırılır)

```
python3 tools/model-uyelik-kapisi.py            → rc=0, K19 ÇAPRAZ=0, YARGISIZ=0, ÇELİŞKİ=0, BAYAT=0
python3 tools/arama-test.py                     → rc=0   (yoksa: tools/testler.py rc=0)
python3 tools/marka-invaryant-kapisi.py         → K170 ÖNCESİ ile AYNI hüküm (Rover DURUYOR)
python3 tools/kategori-parite-test.py           → rc=0
node --check index.html  (ya da parite-test.js) → rc=0
```

**K11 KAYBOLAN EKSENİ (ZORUNLU):** kapının K11 ölçümünde `kaybolan=0`. Deny'e giren 7 çiftten
BUGÜN sayfası olan varsa **tek tek listele** (marka, canon, ürün sayısı, sayfa açık mıydı) —
"0 sayfa kapandı" iddiası ÖLÇÜLMEDEN yazılmaz ([[olculdu-diyen-hukum-kaniti]]).

**MUTASYON BATARYASI (3 mutant, hepsi KIRMIZI yakmalı):**
- M1: `Vespa|gts` satırını SİL → kapı `YARGISIZ` verip rc=1.
- M2: `("Piaggio","GTS")` deny satırını `Piaggio|gts` olarak allow'a da yaz (çelişki) → `CELISKI` rc=1.
- M3: `ROZET_CAPRAZ_IZINLI_IMZA`yı eski değerde (`9c01bf09e4d0bab6`) bırak → imza ekseni rc=1.
Mutant uygulanmadıysa `UYGULANAMADI` yaz, 0 sayma ([[mutasyon-capasi-olu-kola-nisanlanir]]).

## RAPOR
Dalda, projenin kanonik mühendis raporu adıyla (başka ad YASAK — ad için
`~/.claude/cron/baglam/` işçi bağlamına bak). Ham çıktılar + yukarıdaki her satırın rc'si.
`urunler.json`'a DOKUNMA. Worktree kendi dalında; iş bitince temizlik kanıtı (`du` öncesi/sonrası).
