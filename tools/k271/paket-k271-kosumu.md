codex-muafiyet: K271 damga tasima onarimi + dusmus damganin kanittan geri yuklenmesi — ölçüm

# K271 KOSUM PAKETI — ISCI GOREVI (KraL-K260KatSec)

Alti komut SIRAYLA kosulacak. Her adim `subprocess` ile kosulur, ham cikti ve
BORUSUZ rc dosyaya yazilir.

🔴 **YASAKLAR (ihlal = is REDDEDILIR):**
- Hicbir dosyayi DUZENLEME, hicbir kusuru ONARMA, hicbir testi DEGISTIRME.
- `git` KOSMA (commit / checkout / stash / merge YOK).
- Ciktiyi OZETLEME, YORUMLAMA, TABLO UYDURMA. Hukum MIMARINDIR.
- Bir komut kirmizi donerse **DUR DEME, SIRADAKINE GEC** — rc dosyaya yazilir.
- Adim atlama, komut degistirme, yol kisaltma YOK. Yollar BIREBIR.

## KOMUTLAR (birebir, sirayla)

1.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k271-kanit --faz k271-taban
```

2.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k271-kanit --faz k271-kur
```

3.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k271-kanit --faz k271-geri-yukle
```

4.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k271-kanit --faz k271-kabul
```

5.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k271-kanit --faz k271-tur-kuru
```

6.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k271-kanit --faz k271-tur-canli
```

## RAPORUN
Yalnizca her komutun bastigi `ADIM=... RC=... DOSYA=...` ve `OZET ...`
satirlarini AYNEN yapistir. Yorum ekleme; ham cikti dosyalarda duruyor.
