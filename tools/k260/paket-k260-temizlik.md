isci-muafiyet: K260 kanit dizinleri + supersede olmus tur-1 yedekleri silinir, once/sonra boyut olculur — ölçüm

# K260 TEMIZLIK — ISCI GOREVI (KraL-K260KatSec)

🔴 DISK — OKAN KURALI: makinede iz birakilmaz, URETEN TEMIZLER.
Silinecek: `k260-kanit`, `k260-kanit2` kanit dizinleri + SUPERSEDE olmus tur-1
yedekleri (`*.yedek-k260-20260824T125221Z`). KORUNAN: aktif `--geri-al` yolu
(`*.yedek-k260-20260824T125857Z`) — canli yamanin tek geri donus yolu odur.

## SEN NE YAPACAKSIN
Yalnizca su **tek komutu** kosacaksin, baska hicbir sey yapmayacaksin.
`git` KOSMA, dosya DUZENLEME, yorum EKLEME.

```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k260-temizlik-izi --faz temizlik
```

## RAPORUN
Komutun bastigi TUM satirlari AYNEN yapistir (`ONCE ...`, `SONRA ...`,
`KORUNAN ...`, `TEMIZLIK ...`, `HUKUM=...`). Yorum ekleme.
