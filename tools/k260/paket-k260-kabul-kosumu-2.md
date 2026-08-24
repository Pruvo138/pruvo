codex-muafiyet: K260 tur-2 — tur-1 yamasini geri al, duzeltilmis yamayi kur, kabul/mutasyon/canli tur kosumu — ölçüm

# K260 KOSUM PAKETI TUR-2 — ISCI GOREVI (KraL-K260KatSec)

## NEDEN TUR-2
Tur-1 yamasi KURULDU (12/12) ama canli olcum `DAGITILABILIR=0` verdi: metin
maskelemesi tek basina yetmedi. Yapisal eksen olculdu (`nobet-geri-iz.json`):
MIMAR'a kilitli 11 kalemin **10'u** `durum=BAYAT_GOC motor=kimi
eski_motor=codex dagitim_sayisi=3` kaydi tasiyor. Duzeltilmis yama bu YAPISAL
izi dagitim kararina baglar. Ankorlar ORIJINAL metne yasli oldugu icin once
tur-1 yamasi GERI ALINIR.

## SEN NE YAPACAKSIN
Asagidaki **ALTI komutu SIRAYLA** kosacaksin. Baska hicbir sey yapmayacaksin.

🔴 **YASAKLAR (ihlal = is REDDEDILIR):**
- Hicbir dosyayi DUZENLEME, hicbir kusuru ONARMA, hicbir testi DEGISTIRME.
- `git` komutu KOSMA (commit / checkout / stash / merge YOK).
- Ciktiyi OZETLEME, YORUMLAMA, TABLO UYDURMA. Hukum MIMARINDIR.
- Bir komut kirmizi donerse **DUR DEME, SIRADAKINE GEC** — rc dosyaya yazilir.
- Adim atlama, komutu degistirme, yol kisaltma YOK. Yollar BIREBIR.

## KOMUTLAR (birebir, sirayla)

1.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k260-kanit2 --faz geri-al --damga 20260824T125221Z
```

2.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k260-kanit2 --faz kur
```

3.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k260-kanit2 --faz kabul
```

4.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k260-kanit2 --faz tur-kuru
```

5.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k260-kanit2 --faz tur-canli
```

6.
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/kind-elbakyan-b81e21/tools/k260/k260-kosum.py --cikti /Users/okan/.claude/cron/k260-kanit2 --faz tur-kuru2
```

## RAPORUN
Yalnizca her komutun bastigi `ADIM=... RC=... DOSYA=...` satirlarini AYNEN
yapistir. Yorum ekleme. Ham cikti dosyalarda duruyor; mimar oradan okuyacak.
