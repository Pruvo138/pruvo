isci-muafiyet: K271 bataryasi fikstur onarimi sonrasi yeniden kosum — ölçüm

# K271 KOSUM TUR-2 — ISCI GOREVI (KraL-K260KatSec)

Tur-1'de KOD yesildi ama BATARYA iki fikstur hatasiyla kirmizi dondu (beklenti
motor adina civilenmisti; negatif kollar MIMAR metinli kalemle dagitim
deniyordu, `kalem_dagit` haklı olarak reddediyor). Fiksturler onarildi.
Bu tur bataryayi YENIDEN kurar ve kabul + mutasyon + kova olcumunu tekrarlar.

## SEN NE YAPACAKSIN
Uc komut SIRAYLA.
🔴 `git` KOSMA · dosya DUZENLEME · kusur ONARMA · yorum EKLEME · tablo UYDURMA.
Bir komut kirmizi donerse DURMA, sonrakini de kos.

1.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k271-kanit2 --faz k271-kur
```

2.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k271-kanit2 --faz k271-kabul
```

3.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k271-kanit2 --faz k271-tur-kuru
```

## RAPORUN
Yalnizca `ADIM=... RC=... DOSYA=...` ve `OZET ...` satirlarini AYNEN yapistir.
