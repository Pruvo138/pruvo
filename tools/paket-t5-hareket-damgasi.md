# PAKET T5b — HAREKET DAMGASI EKSENI: kapi CANLI VERIDE olcemiyor (gercek defterde 7/7 `OLCULEMEDI`)

Chip: `KraL-Onarim grubu devami` · 19 Agu 2026 · hedef kat: ISCI · kabul MIMARDA.

---

## 1. OLCULEN OLGU

`tools/durgun-kalem-kapisi.py` (T5, `fff7db58`) main'de, SERIT B'de, `MUTANT=4/4`,
`CURUTME=4/4`. Ama **gercek defter uzerinde kosunca 7 kalemin 7'si `T5-OLCULEMEDI`**:
kapinin okudugu durum dosyasinda (`{"kalemler": {kimlik: iso_damga}}`) hicbir kalemin
damgasi YOK. Yani kapi sentetik fiksturde calisiyor, **canli veride hicbir sey olcmuyor**.

Bu, bu depoda adi konmus bir sinif: kapi VAR, kosuyor, yesil — ama olctugu duzlem BOS.
`OLCULEMEDI` dogru jetondur (fail-closed dogru calisiyor, ARIZA DEGIL), fakat eksen
kapali kaldigi surece T5 "4 saat hareketsiz kalem devredilir" vaadini canliya
tasiyamaz.

## 2. HUKUM — damga EKLENIR, eksen kapsam disi ILAN EDILMEZ

Iki yol vardi: (a) her kaleme ELLE bakim gerektiren bir damga alani acmak,
(b) ekseni `KAPSAM DISI` ilan etmek. **IKISI DE REDDEDILDI:**

* (a) elle bakimli alan bayatlar; bayat damga "hareket var" der ve kapiyi
  **fail-open** yapar — onarimin kendisi kusur dogurur.
* (b) ekseni kapatmak T5'i sentetik-yesil birakirdi.

**SECILEN:** damga **TURETILIR** — kaynak `DEVAM.md`'nin GIT GECMISI. Bir kalemin son
hareketi = o kalemin kimligini (`K186`, `K196`, …) iceren satira DOKUNAN en son
commit'in tarihi. Elle yazilan alan YOK, ikinci hukum yeri YOK.

🔴 **FAIL-OPEN YASAGI (bu turun EN kritik kurali):** damga URETICISI hicbir kalemi
"taze" ILAN ETMEZ. Uretici yalnizca `kimlik -> damga` haritasi uretir. `T5-DURGUN` /
`T5-TAZE` / `T5-OLCULEMEDI` hukmunu **YALNIZ** mevcut `kalem_damgasi()` verir —
hukum TEK yerde kalir. Damgasi TURETILEMEYEN kalem `OLCULEMEDI` OLARAK KALIR;
"git izi yok" **asla** "taze" DEMEK DEGILDIR.

## 3. TESLIM EDILECEK

### 3.1 `tools/durgun-kalem-kapisi.py` icinde YENI KOL: `--damga-uret`

* Girdi: `DEVAM.md` (yol `--defter` ile ezilebilir) + o defterin git deposu.
* Her ACIK kalem kimligi icin: `git log` ile, `DEVAM.md`'de o kimligi iceren satira
  dokunan **en son** commit'in committer tarihi (UTC, ISO-8601) bulunur.
* Cikti: mevcut durum dosyasi bicimiyle **AYNI** JSON (`{"kalemler": {...}}`),
  atomik yazim (mevcut `durum_yaz_atomik` KULLANILIR, ikinci yazim yolu ACILMAZ).
* Damgasi bulunamayan kalem haritaya **YAZILMAZ** (yazilirsa `kalem_damgasi()` onu
  olculmus sanardi). Cikti satirinda ayrica sayilir.
* Son satir:
  ```
  DAMGA_URETILDI=<n> DAMGA_URETILEMEDI=<n> NEDEN_GIT_IZI_YOK=<n> NEDEN_DEFTER_GITSIZ=<n>
  ```
  Hicbir kalem uretilemezse rc≠0 (sessiz sifir YASAK).

### 3.2 `--gercek` kolu (varsa mevcut kolu kullan, yoksa ekle)

Gercek defter + uretilen damgalarla siniflandirma basar. Beklenen: bugunku
`7/7 OLCULEMEDI` tablosu **degisir**; kac kalem `T5-DURGUN`, kac `T5-TAZE`,
kac `T5-OLCULEMEDI` **OLCULEREK** yazilir. 🔴 Beklenen bir sayi YOKTUR — ne cikarsa
o raporlanir; spec'e uydurma YASAK.

## 4. KABUL (calistirilabilir)

```
python3 /Users/okan/dev/pruvo/tools/durgun-kalem-kapisi.py --kendini-test
python3 /Users/okan/dev/pruvo/tools/durgun-kalem-kapisi.py --curutme
```

Mevcut `MUTANT=4/4` ve `CURUTME=4/4` **AYNEN GECMEYE DEVAM ETMELI** (gerileme yok),
uzerine yeni vakalar eklenir. Son satirlar + rc=0.

### 4.1 Yeni mutantlar — 3/3 KIRMIZI, her biri HEDEF KOLUNU AYRICA kanitlar

🔴 **K182 BAGLAYICI:** her mutant icin hedef kolun kirmizi yandigi VE yan eksenlerin
YESIL kaldigi ayrica gosterilir; cikti `HEDEF_KOL_ATFI=<EVET|HAYIR>` basar. Dordu de
EVET degilse `MUTANT=n/n` YAZILMAZ ([[mutant-yan-ekseni-de-tetikliyorsa-olcmez]]).

| # | Mutasyon | Dusmesi gereken |
|---|---|---|
| M5 | Damgasi turetilemeyen kalemi haritaya `simdi` damgasiyla yaz (fail-open) | O kalem `T5-TAZE` olur → vaka KIRMIZI; DURGUN/TAZE kollari YESIL kalmali |
| M6 | `--damga-uret` kendi basina `T5-TAZE` hukmu bassin (ikinci hukum yeri) | Hukum ikilesmesi vakasi KIRMIZI; siniflandirma kollari YESIL kalmali |
| M7 | En son commit yerine EN ESKI commit'in tarihi alinsin | Turetme dogrulugu vakasi KIRMIZI; `OLCULEMEDI` kolu YESIL kalmali |

### 4.2 Kontroller — 2/2 YESIL kalacak

* **K3** — git gecmisi OLMAYAN bir defter (sentetik, deposuz) verilince arac
  COKMEZ: `NEDEN_DEFTER_GITSIZ` sayar, rc≠0 doner, hicbir kalem "taze" olmaz.
* **K4** — Mevcut 4 mutant + 4 curutme AYNEN gecer (gerileme nobeti).

### 4.3 Fikstur kurali

Sentetik kok + sentetik git deposu kullanilir; **gercek `DEVAM.md` ve gercek durum
dosyasi DEGISMEZ**. Kapanista gercek defterin `git status` ciktisi rapora yazilir ve
`DEFTER_DEGISMEDI=EVET` kanitlanir. Gecici kok SILINIR, `TEMIZ=EVET`.

## 5. SINIRLAR

* Bu paket kapinin DEVIR (`devir_yap`) davranisina DOKUNMAZ; yalniz damga eksenini acar.
* Canli kablo (kapinin gercek defterde otomatik kosup kalem DEVRETMESI) **KAPSAM DISI** —
  parti akisini durdurmak Okan kapisidir. Bu turda yalniz OLCUM acilir.
* `DEVAM.md`'ye YAZILMAZ (defter mimarindir).

## 6. ISCI TALIMATI (baglayici)

* Calisma agaci **YALNIZ** `/Users/okan/dev/pruvo/.claude/worktrees/dreamy-mclean-669442`.
  Mutlak yol kullan; ana agaca (`/Users/okan/dev/pruvo`) **YAZMA**
  ([[isci-worktree-yerine-ana-agaca-yazar]]).
* **COMMIT ATMA** — commit'i chip atar.
* `.github/workflows/nobet.yml`'e **DOKUNMA** (CI kablolamasi ayri dilim, cakisma onlemi).
* Baska oturumun kirli dosyasina DOKUNMA; `git checkout`/`restore` ile kimsenin
  commit'siz isini geri ALMA — KABUL KAPISI ([[isci-merge-blokunu-checkoutla-cozer]]).
  Kapanista `git reflog -n 10` raporla.
* Rapor: dalda **kanonik muhendis raporu dosyasi** (bu evde tek ad, izlenmez); varsa
  BASINA damgayla EKLE, uzerine YAZMA.
* Olcemedigine `OLCULEMEDI` + SEBEP; sessiz yesil YASAK.
* Tavan ~40 tur, tek dilim. Alt ajan / paralel gorev ACMA.
