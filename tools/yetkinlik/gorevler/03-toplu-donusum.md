# GÖREV 3 — Toplu deterministik dönüşüm

> Koşucu, `<CALISMA>` yerine gerçek geçici dizin yolunu yazar.

Girdi: `<CALISMA>/girdi.tsv` — başlık satırı + 40 veri satırı, sütunlar:
`id`, `baslik`, `fiyat_tl`, `marka` (marka boş olabilir).

Üret: `<CALISMA>/cikti.json` — **UTF-8, 2 boşluk girintili, anahtar sırası aşağıdaki gibi**,
dizi olarak ve girdi sırasını KORUYARAK:

```json
[{ "id": "...", "baslik": "...", "fiyat": "850 TL", "marka": ["Audi"] }]
```

Kurallar:
- `fiyat`: `fiyat_tl` sayısının sonuna tek boşluk + `TL` (ör. `850` → `"850 TL"`).
- `marka`: boşsa `[]`, doluysa tek elemanlı dizi. Virgülle ayrılmışsa çok elemanlı, her eleman
  kırpılmış (trim).
- `baslik`: baştaki/sondaki boşluklar kırpılır, içerideki çoklu boşluk TEK boşluğa iner.
- Dosya sonunda tek `\n`.

## KABUL — son satır
SATIR=<uretilen eleman sayisi> · DOSYA=<cikti.json tam yolu>
