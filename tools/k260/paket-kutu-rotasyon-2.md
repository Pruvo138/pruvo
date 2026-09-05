isci-muafiyet: ortak posta kutusu LOSSLESS rotasyonu, blok envanteri once/sonra — ölçüm

# KUTU ROTASYONU (yeni agac yolu) — ISCI GOREVI (KraL-K260KatSec)

Kutu tavani asti (342/300) ve commit kapisini BLOKLUYOR. LOSSLESS rotasyon
kosulacak: en eski bloklar arsive TASINIR, hicbir sey silinmez/kirpilmaz.
Betik `lossless` iddiasini ARACIN SOZUNE BIRAKMAZ; kutu + arsiv blok basliklarini
ONCE/SONRA cikarir ve kaybolan basligi AYRICA listeler.

## SEN NE YAPACAKSIN
Yalnizca su **tek komutu** kosacaksin.
🔴 `git` KOSMA · dosya DUZENLEME · blok SILME/KIRPMA · ek bayrak EKLEME ·
yorum EKLEME · tablo UYDURMA. Kirmizi donerse ONARMA.

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/gallant-nightingale-333576/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k260-kutu-kanit --faz kutu-rotasyon
```

## RAPORUN
Komutun bastigi TUM satirlari AYNEN yapistir — ozellikle `ONCE ...`, `SONRA ...`,
her `TASINAN_BLOK ...`, varsa her `!! KAYIP_BLOK ...`, `KUTU_ROTASYON ...`,
`BLOK_KORUNUMU ...`, `KOTA_SONRASI_RC=...`.
