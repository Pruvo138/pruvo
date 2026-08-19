# PAKET — K195 defter rotasyonu: OKAN KAPISI tek `&&` zinciri

## NEDEN OKAN KAPISI (chip bunu KENDI ELIYLE olcemedi)

Uc icra yolunun UCU DE kapali olctu (20 Agu, chip `KraL-K195`):

| yol | sonuc |
|---|---|
| `python3 ... .py` (chip'in kendi eliyle) | **RED** — mimar icra kapisi; muafiyet DIZINE degil `agent_id`'ye bagli, worktree ICINDEN de reddediyor |
| `Agent` / alt-ajan | **YASAK** — AGENT-KAPISI (13 Agu, Okan emri) |
| `~/.claude/cron/isci.sh` | **RED** — N2B parti kapisi, ev KraL acik kalem **34** |

Yani daldaki `8/8 yesil` DAL SAHIBININ beyanidir; bu tur onu **BAGIMSIZ olcemedi**.
Asagidaki zincir tam olarak o bagimsiz olcumu yapar, sonra merge eder.

## ON KOSUL (zincire girmeden once)

1. `origin/main` **K184'u ICERMELI** (kardes oturumun `a15cfc83` merge'i itilmis olmali).
   Zincir bunu kendi olcer ve icermiyorsa ILK ADIMDA durur.
2. Ana checkout (`/Users/okan/dev/pruvo`) **TEMIZ** olmali.

**MERGE SIRASI (mimar verdi):** K184 → T4 kirigi → **K195 (bu paket)** → K214 → P1.
Zincirin ilk halkasi zaten K184'u bekledigi icin sirayi elle takip etmene gerek yok.

## ZINCIR — tek satir, fail-closed

Kirmizi adim zinciri KESER; `git push` satirina **hic gelinmez**. Testler merge'den
ONCE kosar, yani kirmizi bir kabul main'e **dokunmaz** bile.

```bash
git -C /Users/okan/dev/pruvo fetch origin && git -C /Users/okan/dev/pruvo merge-base --is-ancestor a15cfc83 origin/main && python3 /Users/okan/dev/pruvo/.claude/worktrees/k195-rotasyon/tools/defter-rotasyon-cifti-test.py && python3 /Users/okan/dev/pruvo/.claude/worktrees/k195-rotasyon/tools/defter-isaretciye-indirme-test.py && python3 /Users/okan/dev/pruvo/.claude/worktrees/k195-rotasyon/tools/defter-rotasyon-test.py && python3 /Users/okan/dev/pruvo/.claude/worktrees/k195-rotasyon/tools/defter-rotasyon.py --kendini-test && python3 /Users/okan/dev/pruvo/.claude/worktrees/k195-rotasyon/tools/defter-kota-kapisi.py --kendini-test && python3 /Users/okan/dev/pruvo/.claude/worktrees/k195-rotasyon/tools/defter-kota-kapsam-disi-test.py && git -C /Users/okan/dev/pruvo merge --no-ff origin/kral/k195-defter-rotasyon-merged -m "merge: K195 — defter rotasyonu sinif cozumu (isaretciye indirme + 1:1 LOSSLESS + acik kalem vetosu)" && git -C /Users/okan/dev/pruvo push origin main
```

## BEKLENEN SAYILAR (bunlari gormezsen zincir zaten kesilmis olur)

* `defter-rotasyon-cifti-test.py` son satir: **`VAKA=5/5 MUTANT=3/3 HEDEF_KOL_ATFI=3/3 DUSEN=0`**
* `defter-isaretciye-indirme-test.py`: **7/7 + 4/4**
* `defter-rotasyon-test.py`: **`FIKSTUR=23/23 YENI_VAKA=14/14`**
* `defter-rotasyon.py --kendini-test`: **`DUSEN=0`**
* `defter-kota-kapisi.py --kendini-test`: **6/6**

Odevin kabul ekseni dalda **C3** vakasidir: kapali madde ICERMEYEN, kotayi ASAN
fikstur ile arac kosar ve dosya tavanin **ALTINA** iner (`b0 > 900`, `b1 <= 900`),
`ISARETCIYE_INDIRILDI` basar. Mutant kolu `MUTANTLAR` tablosundadir ve her mutant
YALNIZ kendi hedef kolunu oldurur (K182 hedef-kol atfi).

## ZINCIR KESILIRSE

* **`merge-base --is-ancestor` durduysa:** K184 henuz itilmemis. Bekle, kardes oturum itsin.
* **Bir kabul kirmizi geldiyse:** dal EKSIKTIR, merge ETME; ciktiyi mimara ver.
* **`merge` gecti ama `push` inmediyse:** ana checkout'ta **itilmemis bir merge kalir**
  (bkz. [[ana-checkout-lokal-merge-komsu-pushu]]). Geri sarma zincirde YOKTUR — mimara haber ver.

## MERGE SONRASI ARTIK KALEM (K221 — bu dal KAPATMAZ)

Bu dal, kota asiminda **sessiz yesili** (rc=0 + `TASINAN=0`) oldurur ve yerine ADIYLA
konusan bir hukum koyar. Ama elle budamayi **tumden bitirmez**: indirme BLOK
granulundedir, `_indirme_vetosu()` acik jeton tasiyan blogu tumden vetolar. Defter
yalniz ACIK + KORUMALI bloklardan ibaretse arac `rc=4 OLCULEMEDI` verir ve budama yine
ELDE kalir (dal sahibinin gercek defterde olcumu: `blok=5, hepsi vetolu`).
Defterin KENDI teamulu ise MADDE granuludur (`**Tam metin ARSIVDE.**` satirlari).
**K221 kabul:** madde granullu indirme + o kolu bozan mutant KIRMIZI + kirmizinin sebebi o kol.

## MERGE SONRASI TEK DOGRULAMA (bu dal main'in defterini kotaya GERI SOKUYOR)

```bash
git -C /Users/okan/dev/pruvo cat-file -s origin/main:DEVAM.md
```

**12288'in ALTINDA** olmali (beklenen ~**12259**). Ustunde cikarsa merge defteri kotaya
sokmamis demektir — mimara haber ver. Merge ONCESI deger **12324** idi (asim 36 bayt).

## AYRICA OLCULDU — TABAN KUSURU (K195'ten AYRI, mimarda **K225**)

`origin/main:DEVAM.md` = **12324 bayt**, tavan **12288** → **main'in kendisi 36 bayt
kota USTUNDE**. Push kapisi bunu bagimsiz dogruladi:
`DEFTER KOTASI BYPASS SAYILDI — HEAD'deki DEVAM.md 124 satir / 12324 bayt`.

Kusurun ADI "defter sismis" DEGIL: **kota kapisi MERGE'e KORDUR.** Kapi yalnizca DEVAM.md
**stage'de iken** bloklar (`_devam_stage_de`), merge yoluyla gelen buyume hic olculmez —
asimi N1 merge'i acti (K139 kalemini uzatti) ve hicbir kapi gormedi. Sonuc: deftere dokunan
HER commit main'de bloklu, dokunmayan `KAPSAM_DISI_ASIM` sayilip gecer.
Bu **mimarda K225** olarak ayri kalem; K195'in kabul olcutunu BUYUTMEZ.
Bu dal merge'i, chip KENDI kalemini (K195 satiri) ~155 bayttan ~90 bayta indirerek
gecirebildi — komsu satirlara DOKUNULMADI. Ders: [[olcut-civilenirken-taban-olculmeli]].
