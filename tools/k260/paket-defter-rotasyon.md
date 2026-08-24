codex-muafiyet: DEVAM.md LOSSLESS rotasyonu, kanonik NO-OP gozlemi + acik hedef — ölçüm

# DEFTER (DEVAM.md) ROTASYONU — ISCI GOREVI (KraL-K260KatSec)

DEVAM.md tavani asti (kardes mimar `ls -l` ile 12.641 B olctu, tavan 12.288).
Iki bicim SIRAYLA kosulacak: ① kanonik (NO-OP donmesi K272'nin gozlemidir)
② acik hedef (`--tavan-bayt 11400`, asil tasima).

Betik `lossless` iddiasini ARACIN SOZUNE BIRAKMAZ: DEVAM.md + DEVAM-ARSIV.md'nin
BOS OLMAYAN SATIR KUMESI once/sonra karsilastirilir, kaybolan satir AYRICA
listelenir. Ayrica kardes mimarin bu turda ekledigi K271 ve K275 satirlarinin
DEVAM.md'de KALIP KALMADIGI ayri ayri basilir.

## SEN NE YAPACAKSIN
Yalnizca su **tek komutu** kosacaksin.
🔴 `git` KOSMA · dosya DUZENLEME · satir SILME/KIRPMA · ek bayrak EKLEME ·
yorum EKLEME · tablo UYDURMA. Kirmizi donerse ONARMA, hukum mimarindir.

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k260-defter-kanit --faz defter-rotasyon
```

## RAPORUN
Komutun bastigi TUM satirlari AYNEN yapistir — ozellikle `ONCE ...`,
`ONCE_JETON ...`, `KANONIK_SONRASI ...`, `KANONIK_NO_OP=...`, `SONRA ...`,
her `TASINAN_SATIR ...`, varsa her `!! KAYIP_SATIR ...`, `SONRA_JETON ...`,
`DEFTER_ROTASYON ...`, `SATIR_KORUNUMU ...`, `BAYT_DEVRI ...`,
`KOTA_SONRASI_RC=...`. Ozetleme, kisaltma, yorumlama.
