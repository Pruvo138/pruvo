# PAKET ⑤b — MERGE-KANIT TABLOSU: arac VAR, kanca VAR, **TABLO BESLENMIYOR** + CI kablosu YOK

Chip: `KraL-Onarim grubu devami` · 19 Agu 2026 · hedef kat: ISCI · kabul MIMARDA.

---

## 0. ILK BLOK — KAPSAM ON-OLCUMU (K191; oncul DEGIL olcum)

⑤ "KURULMAMIS" diye devredildi. **Bu oncul KISMEN CURUK** — chip olctu, ham kanit:

* `tools/merge-kanit.py` main'de **VAR** (`e1a6f628` K173 + `bedb06e9` K173-b), 350 satir.
* `tools/kancalar/pre-push` icinde uyari kolu **VAR** (satir 306-330) ve
  **KURULU kopyada da var** (`.git/pruvo-kancalar/pre-push`, `grep -c merge-kanit` = 2;
  kaynak ve kurulu kopya ikisi de 357 satir). `core.hooksPath=.git/pruvo-kancalar`.
* `~/.claude/cron/merge-kanit.tsv` icinde **YALNIZ 2 SATIR**, ikisi de **18 Agu**,
  ikisi de aracin KENDI teslim dalina (`kral/k173-merge-kanit`) ait.

🔴 **GERCEK BOSLUK BU:** 18 Agu'dan bu yana main'e alinan dallarin (K185 · K188 ·
T3 · T4 · T5 · K195 · ③e …) **hicbiri** icin kanit satiri YOK. Yani tablo kuruldu,
kanca uyariyi basiyor, ama **kimse `--kaydet` kosmuyor** ve uyari BLOKLAMADIGI icin
gormezden geliniyor. Sinif: kapi VAR, kosuyor, ama **URETMIYOR**.
Ikinci boslik: `--kendini-test` **hicbir OTOMATIK is akisinda kosmuyor**
(`grep -rn merge-kanit .github/workflows/` → **0 vurus**) — "kapi var, kosmuyor".

**Isci ONCE bu on-olcumu YENIDEN kosar ve ham ciktiyi rapora yapistirir**
(sapma varsa `SAPMA=` satiriyla yazar; spec'teki sayi degil OLCULEN gecerlidir):

```
python3 /Users/okan/dev/pruvo/tools/merge-kanit.py --kendini-test
grep -c "" /Users/okan/.claude/cron/merge-kanit.tsv
grep -rn "merge-kanit" /Users/okan/dev/pruvo/.github/workflows/
```

## 1. TESLIM EDILECEK

### 1a. GERILEME NOBETI (once bu)

`--kendini-test` bugun de GECMELI. Beklenen son satir:
`VAKA=<n> DUSEN=0 MUTANT=3/3 KONTROL=2/2` + rc=0.
🔴 Gecmezse **ONARIM ONCELIKLIDIR**; 1b/1c'ye gecme, raporla ve DUR.

### 1b. `--eksikler` — BESLENMEYEN TABLOYU OLCEN YENI KOL

Bugun arac yalniz "bu dal icin satir var mi" (`--dogrula <dal>`) diyebiliyor. Eksik olan
**toplu** gorunum: main'e fiilen alinmis ama kaniti OLMAYAN birlesimler.

* Girdi: `git log --merges` + `git log` ile main'in ilk-ebeveyn gecmisi (pencere
  `--sinir <ISO damga>` ile daraltilabilir; varsayilan: kanit dosyasindaki EN ESKI satir).
* Cikti: kaniti olmayan her birlesim icin bir satir + makine-okunur son satir:
  ```
  MERGE_KANIT BIRLESIM=<n> KANITLI=<n> KANITSIZ=<n> PENCERE=<baslangic>..<HEAD>
  ```
* 🔴 **GERIYE DONUK SATIR URETMEZ.** Paket ⑤ §5 baglayici: *"Bu dilim geriye donuk kanit
  URETMEZ; gecmis merge'ler icin satir uydurulmaz."* Kol yalniz **SAYAR ve LISTELER**.
  Uydurulmus `RC=0` satiri yazan bir kol EKLENMEZ (M1'in oldurdugu kol tam olarak budur).
* Kanit dosyasi okunamazsa `0` YAZILMAZ → `OLCULEMEDI` + SEBEP, rc≠0.

### 1c. SERIT B KABLOSU

`.github/workflows/nobet.yml` icindeki **SERIT B** isine (yayini BLOKLAMAYAN serit;
`durgun-kalem-kapisi.py --kendini-test` adiminin bulundugu is akisi) iki adim eklenir —
mevcut adimlarin bicimine BIREBIR uyarak (`if: ${{ !cancelled() }}` dahil):

```yaml
      - name: "Merge-kanit tablosu — kendini test (3 mutant + 2 kontrol)"
        if: ${{ !cancelled() }}
        run: python3 tools/merge-kanit.py --kendini-test
```

🔴 `--eksikler` CI'ya **BLOKLAYICI olarak BAGLANMAZ** (bugun `KANITSIZ>0`; dogdugu gun
bloklayan kapi kuyruktaki mesru isleri durdurur — [[kapi-birikimi-yayin-gecikmesi]]).
Yalniz `--kendini-test` baglanir.

🔴 **CAKISMA UYARISI:** `nobet.yml`e ayni dilimde baska adimlar da eklenebilir. Dosyayi
**yeniden yazma**; yalniz yukaridaki blogu ekle ve `git diff --stat` ile yalniz
`+N satir` eklendigini rapora yaz.

## 2. KABUL (calistirilabilir)

```
python3 /Users/okan/dev/pruvo/tools/merge-kanit.py --kendini-test
python3 /Users/okan/dev/pruvo/tools/merge-kanit.py --eksikler
python3 /Users/okan/dev/pruvo/tools/ci-kapsam-test.py
```

son satirlar + rc=0. `ci-kapsam-test.py` ciktisinda `merge-kanit.py` **adiyla**
"OTOMATIK'te kosulan" listesinde GORUNMELI — kablo beyan degil, erisilebilir olmali
([[kablo-da-kosuyor-demek-degil]]).

### 2.1 Yeni mutantlar — 2/2 KIRMIZI, hedef kol AYRICA kanitli

🔴 **K182 BAGLAYICI:** `HEDEF_KOL_ATFI=<EVET|HAYIR>`; ikisi de EVET olmadan
`MUTANT=n/n` YAZILMAZ ([[mutant-yan-ekseni-de-tetikliyorsa-olcmez]]).

| # | Mutasyon | Dusmesi gereken |
|---|---|---|
| M4 | `--eksikler` kanitsiz birlesimi KANITLI saysin | `KANITSIZ` ekseni KIRMIZI; `BIRLESIM` sayaci YESIL kalmali |
| M5 | Kanit dosyasi okunamayinca `KANITSIZ=0` yazsin (sessiz sifir) | `OLCULEMEDI` ekseni KIRMIZI; normal sayim kolu YESIL kalmali |

Mevcut `MUTANT=3/3 KONTROL=2/2` **AYNEN** gecmeye devam etmeli (gerileme nobeti).

### 2.2 Fikstur kurali

Sentetik git deposu + sentetik kanit dosyasi. **Gercek
`~/.claude/cron/merge-kanit.tsv` DEGISMEZ**; kapanista bayt boyutu once/sonra rapora
yazilir ve `TSV_DEGISMEDI=EVET` kanitlanir. Gecici kok SILINIR, `TEMIZ=EVET`.

## 3. GERCEK KOSUM — rapora BIREBIR

`--eksikler` gercek depoda kosulur; **ham cikti tamami** rapora girer. Beklenen bir sayi
YOKTUR; kac birlesim kanitsizsa o yazilir. Bu sayi ⑤'nin gercek durumudur.

## 4. SINIRLAR

* Kanca kolunu BLOKLAYICIYA cevirme karari MIMARIN — bu turda uyari KALIR.
* Gecmise donuk kanit satiri URETILMEZ.
* Kardes depolar kapsam DISI.
* `DEVAM.md`'ye YAZILMAZ.

## 5. ISCI TALIMATI (baglayici)

* Calisma agaci **YALNIZ** `/Users/okan/dev/pruvo/.claude/worktrees/dreamy-mclean-669442`.
  Mutlak yol kullan; ana agaca (`/Users/okan/dev/pruvo`) **YAZMA**
  ([[isci-worktree-yerine-ana-agaca-yazar]]).
* **COMMIT ATMA** — commit'i chip atar.
* Baska oturumun kirli dosyasina DOKUNMA; `git checkout`/`restore` ile kimsenin
  commit'siz isini geri ALMA — KABUL KAPISI ([[isci-merge-blokunu-checkoutla-cozer]]).
  Kapanista `git reflog -n 10` raporla.
* Rapor: dalda **kanonik muhendis raporu dosyasi** (bu evde tek ad, izlenmez); varsa
  BASINA damgayla EKLE, uzerine YAZMA.
* Olcemedigine `OLCULEMEDI` + SEBEP; sessiz yesil YASAK.
* Tavan ~40 tur, tek dilim. Alt ajan / paralel gorev ACMA.
