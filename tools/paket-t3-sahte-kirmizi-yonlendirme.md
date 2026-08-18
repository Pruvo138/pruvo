# PAKET T3 — "veri şeridi sahte kırmızısı SAHİBİNİN defterine düşer"

> MİMAR HÜKMÜ (18 Ağu 2026, KraL). BaBa tatbikat programı T3.
> Ön koşul: `tools/sahiplik-haritasi.tsv` SAHİPLİ (EV=BILINMIYOR olan satıra
> yönlendirme YAZILAMAZ — sahipsiz harita üstüne tatbikat kurulmaz).

## ÖLÇÜLEN BUGÜNKÜ DURUM (iddia değil)

- `~/.claude/cron/nobet-kapi.py` kalemleri YALNIZ **KAT** ekseninde dağıtıyor
  (`kat_sec()`: OKAN / MIMAR / işçi motorları). **EV (ev sahipliği) ekseni YOK.**
- `EV_KOKU` sabit `/Users/okan/dev/pruvo`; kalem kaynağı KraL'ın `acik-kalemler.md`si.
  Yani hangi evin mekanizması kırmızı yanarsa yansın, kalem KraL'da kalıyor.
- 18 Ağu 11:23Z nöbet turu: `ACIK_KALEM=12 KAPANAN=0 DAGITILAN=0 ONARIM=0
  KAT_MIMAR=10`. Nöbet koşuyor, onarmıyor; 12 kalemin 10'u mimarda yığılı.
- Aynı gün `32158268667` koşumunda 13 kör kırmızı nöbetçi SAHİPSİZ kaldı.
  Bunların sahiplik haritasındaki karşılıkları TEK EV DEĞİL: ör. CTA denge ve
  feed politikası ArTisT, `duzelt`/model üyeliği/marka invaryantı MaCiT.

## HÜKÜM

### 1) EV ekseni KAT ekseninden AYRIDIR
`KAT` = işi hangi katın yapacağı (motor). `EV` = kalemin hangi evin defterine
düşeceği. İkisi BİRBİRİNİN YERİNE GEÇMEZ; bir kalem hem `KAT=MIMAR` hem
`EV=MaCiT` olabilir (MaCiT'in mimarı yapar).

### 2) EV çözümü YALNIZ haritadan
`ev_sec(kalem)`:
- kalem metninden mekanizma çözülür (`tools/<ad>.py` yolu ya da `MEKANIZMA` adı);
- `tools/sahiplik-haritasi.tsv` içindeki satırın `EV` sütunu döner;
- **eşleşme yoksa `BILINMIYOR` döner ve kalem MIMAR'da kalır** — varsayılan eve
  SESSİZCE düşmek YASAK. `BILINMIYOR` ayrı sayaçla raporlanır (`SAHIPSIZ=n`).

### 3) Yönlendirme: yazma + devir izi
`EV != KraL` olan kalem:
- hedef evin posta kutusuna yazılır:
  `~/.claude/projects/-Users-okan-dev-pruvo-<hasat|pazarlama|bot|jenerator>/memory/mimar-posta-kutusu.md`
  (yoksa OLUŞTURULUR). Satır: damga · mekanizma · koşum id · kırmızı adım ·
  haritadaki `KABUL_KOMUTU` · "sahte mi gerçek mi ÖLÇÜLMEDİ" notu.
- KraL'ın kaleminde satır SİLİNMEZ, `DEVREDILDI: <EV> <damga>` ile işaretlenir.
  🔴 Silme YOK: devredilen kalem iki uçta da görünür, yoksa devir kaybolur.

### 4) TATBİKAT (asıl iş): sentetik SAHTE kırmızı
`veri` şeridinden bir mekanizma için (ör. `r2-purge`) SENTETİK bir kırmızı
kalem üretilir ve tam yol koşturulur. Tatbikat ÖLÇER:
- (a) kalem MaCiT'in posta kutusunda GÖRÜNÜR (mekanizma adı + koşum id ile),
- (b) KraL'ın `KAT_MIMAR` kümesinde GÖRÜNMEZ,
- (c) tatbikat SONUNDA sentetik satır İKİ UÇTAN DA SİLİNİR ve silindiği
  yeniden okunarak KANITLANIR (Okan'ın 13 Ağu disk emri: üreten temizler).
  Temizlik kanıtı yoksa tatbikat EKSİKTİR.

### 5) MUTANTLAR — her biri HEDEF KOLU öldürdüğünü AYRICA kanıtlar (K182)
| mutant | hedef kol | beklenen |
|---|---|---|
| M1: haritada `r2-purge` satırının EV'i `MaCiT`→`ArTisT` | `T3-YON` | kalem ArTisT kutusuna düşer (yönlendirme haritayı OKUYOR, sabit değil) |
| M2: mekanizma haritada YOK | `T3-SAHIPSIZ` | `BILINMIYOR` + kalem MIMAR'da KALIR + `SAHIPSIZ` sayacı artar (sessiz varsayılan YOK) |
| M3: hedef kutuya yazma BAŞARISIZ (yol yazılamaz) | `T3-OLCULEMEDI` | tatbikat KIRMIZI + `OLCULEMEDI`; "teslim edildi" DEMEZ (fail-closed) |

Her mutant için kabul, "kırmızı geldi" DEĞİL, **o kolun mesajının çıktıda
görünmesidir**. Mutant başka bir kolu yakıp geçerse iş REDDEDİLİR.

## KABUL
```bash
python3 /Users/okan/dev/pruvo/tools/t3-yonlendirme-kapisi.py --kendini-test
```
→ `rc=0` · `MUTANT=3/3` · her mutantın hedef kol adı çıktıda GEÇER ·
`SAHIPSIZ` sayacı AYRI basılır · temizlik kanıtı (`TEMIZ=EVET`) basılır.

Ayrıca CI: kapı `SERIT B`de KOŞAN bir adım olarak görünür (`skipped` DEĞİL) —
K178'in sınıfı: kablo "koşuyor" demek değildir.

## BİLİNEN SINIR (yazılacak, gizlenmeyecek)
Bu tatbikat kalemin SAHTE mi GERÇEK mi olduğunu ölçmez; yalnız YÖNLENDİRMEYİ
ölçer. "Sahte kırmızı" ayrımı ayrı kalemdir (K182 sınıfı) ve bu pakette
KAPSAM DIŞIDIR.
