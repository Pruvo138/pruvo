isci-muafiyet: ortak posta kutusu LOSSLESS rotasyonu, blok envanteri once/sonra — ölçüm

# KUTU ROTASYONU — ISCI GOREVI (KraL-K260KatSec)

Ortak posta kutusu tavani asti (319/300 satir) ve commit kapisini BLOKLUYOR.
Kardes mimarin emri: LOSSLESS rotasyon kosulacak — en eski bloklar arsive
TASINIR, hicbir sey silinmez/kirpilmaz.

Betik once KURU kosum yapar, sonra GERCEK kosum, ve `lossless` iddiasini
ARACIN SOZUNE BIRAKMADAN kendisi olcer: kutu + arsiv `## ` blok basliklari
ONCE ve SONRA cikarilir, kaybolan baslik kumesi ayrica hesaplanir.

## SEN NE YAPACAKSIN
Yalnizca su **tek komutu** kosacaksin.
🔴 `git` KOSMA · dosya DUZENLEME · blok SILME/KIRPMA · ek bayrak EKLEME ·
yorum EKLEME · tablo UYDURMA. Kirmizi donerse ONARMA, hukum mimarindir.

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k260-kutu-kanit --faz kutu-rotasyon
```

## RAPORUN
Komutun bastigi TUM satirlari AYNEN yapistir — ozellikle `ONCE ...`,
`SONRA ...`, her `TASINAN_BLOK ...`, varsa her `!! KAYIP_BLOK ...`,
`KUTU_ROTASYON ...`, `BLOK_KORUNUMU ...`, `KOTA_SONRASI_RC=...`.
Ozetleme, kisaltma, yorumlama.
