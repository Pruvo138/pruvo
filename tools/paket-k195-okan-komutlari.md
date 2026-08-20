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

## ON KOSUL — zincir KENDI olcer, elle bakmana gerek yok

Zincirin ilk uc halkasi on kosulu OLCER:

1. `fetch origin` — uzak taze.
2. `diff --quiet` + `diff --cached --quiet` — ana checkout'ta commit'lenmemis is YOK.
3. `merge-base --is-ancestor main origin/main` — ana checkout'ta **itilmemis is YOK**.

3. halka neden boyle: `git rev-parse main` ile `origin/main` ciktilarini karsilastirmak kabuk
degiskeni ister (KOMUT STILI yasak). `--is-ancestor` ayni seyi **cikis koduyla** soyler ve
`&&` zincirinde doğal fail-closed olur. Main geride olsa da 0 doner — bizi ilgilendiren
"itilmemis is var mi", o da tam bu.

**MERGE SIRASI (mimar, 20 Agu guncelledi):** T4 kirigi → **K195 (bu paket)** → K214 → P1.
K184 kuyruktan CIKTI (ayri chip'in taban olcumune baglandi), bu paket ona **bagli DEGIL**.

> 🔴 **ESKI SURUM DUZELTILDI:** onceki halka `merge-base --is-ancestor a15cfc83 origin/main` idi.
> K184 merge'i inmedi (`node tools/parite-ege.js` kirmizi: `47 aciklanamayan / 1331 sorgu`),
> mimar o itilmemis merge'i geri sardi ve `main` = `origin/main` = `ba0e1c50` oldu. OLCULDU:
> `K184_ORIGIN_MAINDE=HAYIR` — yani o halka bir daha **ASLA** yesile donmezdi, zincir sonsuza
> kadar ilk adimda dururdu. (`a15cfc83` nesnesi hala VAR ama `origin/main`'in atasi DEGIL.)

## ZINCIR — tek satir, fail-closed

Kirmizi adim zinciri KESER; `git push` satirina **hic gelinmez**. Testler merge'den
ONCE kosar, yani kirmizi bir kabul main'e **dokunmaz** bile.

```bash
git -C /Users/okan/dev/pruvo fetch origin && git -C /Users/okan/dev/pruvo diff --quiet && git -C /Users/okan/dev/pruvo diff --cached --quiet && git -C /Users/okan/dev/pruvo merge-base --is-ancestor main origin/main && python3 /Users/okan/dev/pruvo/.claude/worktrees/k195-rotasyon/tools/defter-rotasyon-cifti-test.py && python3 /Users/okan/dev/pruvo/.claude/worktrees/k195-rotasyon/tools/defter-isaretciye-indirme-test.py && python3 /Users/okan/dev/pruvo/.claude/worktrees/k195-rotasyon/tools/defter-rotasyon-test.py && python3 /Users/okan/dev/pruvo/.claude/worktrees/k195-rotasyon/tools/defter-rotasyon.py --kendini-test && python3 /Users/okan/dev/pruvo/.claude/worktrees/k195-rotasyon/tools/defter-kota-kapisi.py --kendini-test && python3 /Users/okan/dev/pruvo/.claude/worktrees/k195-rotasyon/tools/defter-kota-kapsam-disi-test.py && git -C /Users/okan/dev/pruvo merge --no-ff origin/kral/k195-defter-rotasyon-merged -m "merge: K195 — defter rotasyonu sinif cozumu (isaretciye indirme + 1:1 LOSSLESS + acik kalem vetosu)" && git -C /Users/okan/dev/pruvo push origin main
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

* **`diff --quiet` durduysa:** ana checkout KIRLI — commit'lenmemis is var. Zincire girmeden temizle.
* **`merge-base --is-ancestor main origin/main` durduysa:** ana checkout'ta **itilmemis bir merge
  duruyor** (tam olarak K184'te yasanan hal). Onu once mimar cozsun; ustune merge ETME.
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
