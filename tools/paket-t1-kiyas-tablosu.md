# PAKET T1 — 48 SAATLIK PARALEL PENCERENIN KIYAS TABLOSU (aracla URETILIR, ELLE YAZILMAZ)

Chip: `KraL-Onarim grubu devami` · 19 Agu 2026 · hedef kat: ISCI · kabul MIMARDA.

🔴 **TARIHLI.** Pencere `~/.claude/cron/t1-pencere.json`: `2026-08-18T08:48:05Z` →
`2026-08-20T08:48:05Z`. Tablo pencere KAPANMADAN once hazir olmali; arac pencere
kapaninca YENIDEN kosulup nihai tabloyu uretecek.

---

## 1. NEDEN — bu is neden ELLE yazilamaz

BaBa'nin T1 hukmu "pencere sonunda kiyas tablosu (yakalanan kirmizilar + LLM tur sayisi
once/sonra)" diyor. Bugune kadar boyle bir tablo YOK. Elle yazilan tablo bu evde kabul
degildir — beyan olcum degildir ([[tahmin-degil-olcum-okan-uyarisi]]). Tablo, ham
loglardan **TURETILEN** bir aracin ciktisi olacak; ayni komut pencere kapaninca yeniden
kosulup nihai tabloyu uretecek.

🔴 **BAGLAYICI MUHASEBE KURALI (K175 §6, defterde ve arsivde yazili):**
`ci_olculdu=false` olan tur **"kirmizi bulunmadi" SAYILMAZ**. Ayri satirda
`OLCULEMEDI_TUR=<n>` olarak raporlanir ve pencerenin **fiilen olculen** baslangici
(ilk olculen turun damgasi) tabloya YAZILIR. Olculemeyen saat yesil saat degildir.

**Olculen olgu (bu paketin yazildigi an, ham dosya `~/.claude/cron/gozcu-cron.log`):**
nominal baslangic `08:48:05Z`, ilk iki tur (`09:23:00Z` · `10:23:01Z`)
`TETIK=OLCULEMEDI`, ilk fiilen olculen tur `11:23:00Z`. Yani `OLCULEMEDI_TUR=2` ve
`FIILEN_BASLANGIC=2026-08-18T11:23:00Z`. Arac bu iki sayiyi **kendisi turetmeli**;
spec'ten kopyalamamali (aksi halde arac degil sabit olurdu).

## 2. TESLIM EDILECEK — `tools/t1-kiyas.py`

Salt okuma. Hicbir log/durum dosyasini DEGISTIRMEZ.

### 2.1 Girdi kaynaklari (hepsi repo DISI, salt okuma)

| Kaynak | Ne verir |
|---|---|
| `~/.claude/cron/t1-pencere.json` | pencere `baslangic` / `bitis` / `sure_saat` |
| `~/.claude/cron/gozcu-cron.log` | YENI HAT turlari (`GOZCU <damga> TETIK=… LLM_TURU=… YENI_KIRMIZI=… … rc=<n>`) |
| `~/.claude/cron/ci-nobeti.log` | ESKI HAT turlari (paralel kosan `:07` hatti) |

Yollar **tek yerde sabit** tanimlanir ve `--kok <dizin>` ile ezilebilir (kabul testi
sentetik kok kullanacagi icin sart).

### 2.2 Tur SINIFLANDIRMASI — uc kova, ikisi ASLA birlestirilmez

Pencere icinde BEKLENEN tur kumesi takvimden turetilir (yeni hat saatte bir `:23`).
Her beklenen tur icin tam olarak bir kova:

* **`OLCULDU`** — log satiri VAR ve turu fiilen olculmus (`TETIK` jetonu `OLCULEMEDI`
  DEGIL). Yalnizca bu kovadaki turlar "kirmizi bulundu/bulunmadi" hukmune girer.
* **`OLCULEMEDI`** — log satiri VAR ama `TETIK=OLCULEMEDI` (olcum kolu dusmus).
  🔴 Bu kova `OLCULDU`'ya KATILMAZ ve "kirmizi bulunmadi" SAYILMAZ.
* **`KOSMADI`** — beklenen turun log satiri HIC YOK (cron atesle(ye)memis).
  🔴 Bu da `OLCULDU`'ya KATILMAZ ve `OLCULEMEDI` ile de AYNI SATIRA yazilmaz —
  ayri kok neden, ayri sayac. (Bugun sifir olabilir; sifir olmasi kovanin
  gereksiz oldugunu gostermez, pencere daha kapanmadi.)

### 2.3 Cikti — iki bolum

**(a) Insan okur kiyas tablosu** — iki sutun: `ESKI HAT (ci-nobeti :07)` ve
`YENI HAT (gozcu :23)`; satirlar: beklenen tur · kosan tur · yakalanan yeni kirmizi
(toplam) · LLM turu (toplam) · tetiklenen tur sayisi.

**(b) Makine-okunur SON SATIR** (kabul grep'i bunu okur):

```
T1 PENCERE=<baslangic>..<bitis> FIILEN_BASLANGIC=<damga|YOK> BEKLENEN_TUR=<n> OLCULDU_TUR=<n> OLCULEMEDI_TUR=<n> KOSMADI_TUR=<n> YENI_KIRMIZI=<n> LLM_TURU_YENI=<n> LLM_TURU_ESKI=<n> DURUM=<ACIK|KAPANDI>
```

🔴 `FIILEN_BASLANGIC` = ilk `OLCULDU` turunun damgasi; hic yoksa `YOK` (nominal
baslangic YAZILMAZ — bu M3'un olduruldugu koldur).
🔴 `DURUM=ACIK` iken tablo "nihai" DEMEZ; basligina `ARA TABLO (pencere ACIK)` yazar.
🔴 Bir eksen okunamiyorsa (`ci-nobeti.log` yok vb.) o eksene `0` YAZILMAZ →
`OLCULEMEDI` yazilir ve rc≠0 doner ([[sessiz-sifir-yasak]]).

## 3. KABUL (calistirilabilir)

```
python3 /Users/okan/dev/pruvo/tools/t1-kiyas.py --kendini-test
```

son satir + rc=0:

```
VAKA=<n> DUSEN=0 MUTANT=4/4 HEDEF_KOL_ATFI=4/4 KONTROL=2/2
```

Ayrica gercek veri kolu (yazmaz, yalniz basar):

```
python3 /Users/okan/dev/pruvo/tools/t1-kiyas.py --gercek
```

### 3.1 Mutasyon bataryasi — 4/4 KIRMIZI, her biri HEDEF KOLUNU AYRICA kanitlar

🔴 **K182 KURALI BAGLAYICI:** her mutant icin (a) hedef kolun kirmizi yandigi VE
(b) **yan eksenlerin YESIL kaldigi** ayrica gosterilecek. Mutant birden cok ekseni
birden yakiyorsa hedef kol olu olsa da kirmizi gelirdi — o mutant kanit SAYILMAZ,
daraltilir ([[mutant-yan-ekseni-de-tetikliyorsa-olcmez]]). Cikti her mutant icin
`HEDEF_KOL_ATFI=<EVET|HAYIR>` basar; dordu de EVET olmadan `MUTANT=4/4` YAZILMAZ.

| # | Mutasyon | Dusmesi gereken |
|---|---|---|
| M1 | `OLCULEMEDI` turlarini `OLCULDU` kovasina kat | `OLCULEMEDI_TUR` ekseni KIRMIZI; `KOSMADI` ekseni YESIL kalmali |
| M2 | `KOSMADI` turlarini `OLCULDU` kovasina kat | `KOSMADI_TUR` ekseni KIRMIZI; `OLCULEMEDI` ekseni YESIL kalmali |
| M3 | `FIILEN_BASLANGIC`'i nominal baslangica esitle | baslangic ekseni KIRMIZI; kova sayaclari YESIL kalmali |
| M4 | `YENI_KIRMIZI`/`LLM_TURU` toplamini log yerine beyandan al | toplam ekseni KIRMIZI; kova sayaclari YESIL kalmali |

### 3.2 Kontrol mutantlari — 2/2 YESIL kalacak

* **K1** — pencere DISINDA kalan log satirlari (once/sonra) hicbir kovaya girmez;
  eklenmeleri sayaclari DEGISTIRMEZ.
* **K2** — `ci-nobeti.log`'da yeni hat bicimine benzemeyen satirlar bulunmasi araci
  COKERTMEZ; eski hat sayaci yine uretilir.

### 3.3 Fikstur kurali

Kabul testi **sentetik kok** kullanir (`--kok <gecici>`); gercek
`~/.claude/cron/` dosyalarina **DOKUNULMAZ**. Testin sonunda gecici kok SILINIR ve
son satirda `TEMIZ=EVET` kanitlanir (13 Agu disk emri).

## 4. GERCEK KOSUM — rapora BIREBIR

Isci `--gercek` kolunu kosar ve **ham ciktinin tamamini** rapora yapistirir. Ozet tek
basina kabul degildir. Beklenen (bu paketin yazildigi anda; degisirse OLCULEN yazilir,
spec'teki sayi DEGIL): `OLCULEMEDI_TUR=2` · `FIILEN_BASLANGIC=2026-08-18T11:23:00Z`.
🔴 Arac bu sayilari uretmiyorsa **onarim ARACTA yapilir, sayi spec'ten KOPYALANMAZ.**

## 5. SINIRLAR

* Arac hicbir log/durum/crontab dosyasini YAZMAZ; `t1-pencere.json` DEGISMEZ.
* Pencereyi kapatma/uzatma karari MIMARIN; arac yalniz `DURUM=ACIK|KAPANDI` basar.
* `gh`/ag cagrisi YOK — yalniz yerel loglar.
* Gizlilik: cikti hicbir jeton/anahtar icermez; kapanista
  `python3 /Users/okan/dev/pruvo/tools/kisisel-veri-test.py` → 0 bulgu.

## 6. ISCI TALIMATI (baglayici)

* Calisma agaci **YALNIZ** `/Users/okan/dev/pruvo/.claude/worktrees/dreamy-mclean-669442`.
  Mutlak yol kullan; ana agaca (`/Users/okan/dev/pruvo`) **YAZMA**
  ([[isci-worktree-yerine-ana-agaca-yazar]]).
* **COMMIT ATMA** — commit'i chip atar. Isini bitirince dosyalar agacta DURSUN.
* Baska oturumun kirli dosyasina DOKUNMA; `git checkout`/`restore` ile kimsenin
  commit'siz isini geri ALMA — bu bir KABUL KAPISIDIR, tavsiye degil
  ([[isci-merge-blokunu-checkoutla-cozer]]). Kapanista `git reflog -n 10` raporla.
* Rapor: dalda **kanonik muhendis raporu dosyasi** (bu evde tek ad kullanilir, baska ad
  YASAK; dosya izlenmez). Varsa dosyanin BASINA damgayla EKLE, uzerine YAZMA.
* Olcemedigine `OLCULEMEDI` + SEBEP yaz; sessiz yesil YASAK.
* Tavan ~40 tur, tek dilim. Alt ajan / paralel gorev ACMA.
