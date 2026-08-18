# PAKET K179 — Reçete kapısı KOŞTU ve KIRMIZI verdi; ama `REDDEDILEN=8`'in bir kısmı PARSER ARTEFAKTI

Mimar: KraL · 18 Ağu 2026 · hedef kat: İŞÇİ · kabul MİMARDA.
K168'in halefi. **Kapı iyi haber verdi: taşınabilir, koşucuda çalıştı, evren 390.**
Sorun hükümde değil, hükmü besleyen AYIKLAMADA.

## 1. ÖLÇÜLEN OLGU (canlı CI koşumu `32136228242`, `serit-b`)

```
RECETE=9 REDDEDILEN=8 EVREN=390        rc=1
```

✅ **Kapı gerçek koşucuda çalıştı** (`/Users/okan/...` yokken, `EVREN=390`) — ③f'nin
taşınabilirlik dersi tutmuş. ✅ H1 kanıtlandı, tek `RECETE-OK` tam da o:
```
RECETE-OK  tools/defter-kota-kapisi.py:124 [CARE:] python3 /Users/okan/dev/pruvo/tools/defter-rotasyon.py /Users/okan/dev/pruvo/DEVAM.md /Users/okan/dev/pruvo/DEVAM-ARSIV.md
```

🔴 **Ama 8 REDDEDILEN'in hepsi gerçek bulgu DEĞİL.** Ham çıktıdan (birebir):
```
RECETE-RED tools/onizleme-kapisi.py:211     [COZUM:] python3 tools/onizleme-paket-yukle.py). if not taze:
RECETE-RED tools/marka-invaryant-kapisi.py:123 [COZUM:] python3 tools/marka-invaryant-kapisi.py --taban-yaz return 1
RECETE-RED tools/komut-stili-kapisi.py:34   [COZUM:] python3 /tam/yol/betik.py ile düz
RECETE-RED tools/konfigur-canli-kapisi.py:1 [COZUM:] python3 tools/konfigur-canli-kapisi
RECETE-RED tools/yasal-sayfa-drift-kapisi.py:205 [COZUM:] python3 tools/build.py kostur uretilen sayfayi
```
`). if not taze:` · `return 1` · `ile düz` · `kostur uretilen sayfayi` — bunlar **komutun
parçası değil**, ayıklayıcının yuttuğu koddan/düzyazıdan artıklar. `konfigur-canli-kapisi`
uzantısız (`.py` düşmüş). Yani kapı **kendi uydurduğu komutu** icra kapısına sorup "red"
alıyor. Bu depoda adı konmuş bir hata: **parser taklidi yapma**
([[mimar-kapi-parser-taklidi]]).

Geriye kalanlar (`--yaz` bayraklı gerçek reçeteler: `konfigur-bundle-kapisi.py --yaz` ·
`sema-bundle-kapisi.py --yaz`) **muhtemelen GERÇEK bulgu** — ama "muhtemelen" hüküm değildir;
ayıklama düzelmeden hiçbirine karar verilmez.

## 2. HÜKÜM

**H1 — Ayıklama muhafazakâr olur; şüphede RED değil `AYIKLANAMADI`.**
Reçete satırından komut çıkarılırken:
* komut, ilk **satır sonu** ya da ilk **kod/düzyazı sınırı** işaretinde biter
  (`)`, `.` + boşluk, `,`, tırnak kapanışı, `return`/`if`/`else` gibi Python anahtar sözcüğü);
* çıkarılan ilk jeton **var olan bir dosya yolu** değilse (repo-göreli `os.path.exists`),
  o satır **RED sayılmaz** → ayrı kova `AYIKLANAMADI=<n>`;
* `AYIKLANAMADI` **yeşil değildir** ama `REDDEDILEN` de değildir; ayrı basılır ve
  hükmü ayrı verilir. Ölçülemeyeni ne 0 ne de kırmızı say
  ([[kapi-varlik-olcer-yokluk-olcmez]]).

**H2 — Çıktı satırı hükmü taşır.** Her satırda: dosya:satır · çıkarılan **komut** ·
hüküm (`OK` / `RED` / `AYIKLANAMADI`) · ve RED ise icra kapısının **gerekçesi**.
Bugünkü çıktı gerekçeyi kırpıyor ("Mimar tara…"), tam gerekçe yazılsın (gerekirse 200 karakter).

**H3 — Kabul sayısı yeniden ölçülür.** Ayıklama düzeldikten sonra `RECETE` / `REDDEDILEN` /
`AYIKLANAMADI` **yeniden** ölçülür ve rapora ONCESI/SONRASI olarak yazılır. K168'in
`REDDEDILEN=0` kabulü **canlıda hiç karşılanmadı** (yerelde 0, CI'da 8) — bu paket o
farkı da açıklayacak: yerel koşum neden 0 verdi?

🔴 **KAPI SUSTURULMAZ.** Amaç kırmızıyı yeşile çevirmek değil, kırmızının **doğru** olmasını
sağlamak. Ayıklama düzeldikten sonra kalan gerçek `REDDEDILEN`ler **kapanmaz, kalem olur** —
her biri "bir kapının reçete ettiği çare mimarca koşulamıyor" vakasıdır ve ayrı hüküm ister.

## 3. KABUL (çalıştırılabilir)

```
python3 tools/recete-kapisi.py --kendini-test
python3 tools/recete-kapisi.py
```
son satır:
```
RECETE=<n> REDDEDILEN=<n> AYIKLANAMADI=<n> EVREN=<n> MUTANT=<k>/<k> KONTROL=<k>/<k>
```

### Vakalar (sentetik fikstür dosyalarıyla, gerçek kapılara DOKUNMADAN)
| # | Fikstür satırı | Beklenen |
|---|---|---|
| V1 | `# COZUM: python3 tools/x.py --yaz` (dosya VAR) | komut birebir `python3 tools/x.py --yaz`, hüküm ölçülür |
| V2 | `# COZUM: python3 tools/x.py). if not taze:` | komut `python3 tools/x.py`, artık YUTULMAZ |
| V3 | `# COZUM: python3 tools/x.py --taban-yaz return 1` | komut `python3 tools/x.py --taban-yaz` |
| V4 | `# COZUM: python3 /tam/yol/betik.py ile düz` (yol YOK) | `AYIKLANAMADI`, RED DEĞİL |
| V5 | `# COZUM: python3 tools/yok-boyle-dosya` (yol YOK) | `AYIKLANAMADI` |

### Mutantlar (3/3 KIRMIZI)
* **M1** — H1'i geri al (artığı yut) → V2/V3 DÜŞER.
* **M2** — `AYIKLANAMADI`yı `REDDEDILEN`e kat → V4/V5 DÜŞER.
* **M3** — `AYIKLANAMADI` varken rc=0 döndür → batarya KIRMIZI (ölçülemeyen yeşil sayılamaz).

### Kontroller (2/2 YEŞİL)
* **K1** — `defter-rotasyon.py` reçetesi AYNEN `RECETE-OK` kalır (H1 regresyonu yok).
* **K2** — Gerçek `--yaz` reçeteleri (`konfigur-bundle` / `sema-bundle`) `AYIKLANAMADI`ya
  DÜŞMEZ; ayıklama muhafazakârlığı gerçek bulguyu gizlememeli.

## 4. SINIRLAR

* Bulunan gerçek `REDDEDILEN`ler bu pakette ÇÖZÜLMEZ — listelenir, kalem açılır.
* `mimar-icra-kapisi.py`'ye DOKUNULMAZ (K168 H1 dışında hiçbir kural değişmez).
* Kapının CI adımı KALDIRILMAZ, muafiyete alınmaz.
* K178 (SERİT B maskeleme) ayrı paket; bu paket onu beklemeden koşabilir.

## 5. İŞÇİ TALİMATI

* Tavan ~30-40 tur, tek dilim. Alt ajan / paralel görev AÇMA. Tarayıcı GEREKMEZ.
* Bütçenin yarısında elindekini commit et, raporu kapat.
* Raporu ÖNCE oluştur; başka turun raporunun ÜZERİNE YAZMA, başa EKLE.
* **DOKUNMA:** `urunler.json` · `crontab` · `DEVAM.md` · `~/.claude/cron/` ·
  `.github/workflows/` (K178 turu orada çalışıyor).
