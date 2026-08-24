codex-muafiyet: K260 kat-kovasi kurulum + kabul/mutasyon/canli tur kosumu — ölçüm

# K260 KOSUM PAKETI — ISCI GOREVI (KraL-K260KatSec)

## SEN NE YAPACAKSIN
Asagidaki **BES komutu SIRAYLA** kosacaksin. Baska hicbir sey yapmayacaksin.

🔴 **YASAKLAR (ihlal = is REDDEDILIR):**
- Hicbir dosyayi DUZENLEME, hicbir kusuru ONARMA, hicbir testi DEGISTIRME.
- `git` komutu KOSMA (commit / checkout / stash / merge YOK).
- Ciktiyi OZETLEME, YORUMLAMA, TABLO UYDURMA. Hukum MIMARINDIR.
- Bir komut kirmizi donerse **DUR DEME, SIRADAKINE GEC** — rc dosyaya yazilir.
- Adim atlama, komutu degistirme, yol kisaltma YOK. Yollar BIREBIR.

## KOMUTLAR (birebir, sirayla)

1.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k260-kanit --faz taban
```

2.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k260-kanit --faz kur
```

3.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k260-kanit --faz kabul
```

4.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k260-kanit --faz tur-kuru
```

5.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k260-kanit --faz tur-canli
```

## RAPORUN
Yalnizca her komutun bastigi `ADIM=... RC=... DOSYA=...` satirlarini AYNEN
yapistir. Yorum ekleme. Ham cikti dosyalarda duruyor; mimar oradan okuyacak.

## NEDEN BOYLE
Her adim `subprocess` ile kosulur, stdout+stderr AYNEN dosyaya yazilir ve rc
BORUSUZ olculur — boru rc'si isci olcumunu yalanlar
([[boru-rc-isci-olcumunu-yalanlar]]), yesil tablo uydurulabilir
([[ucuz-isci-yesil-tablo-uydurur]]). Bu yuzden senin isin KOSTURMAK, HUKUM
VERMEK DEGIL.
