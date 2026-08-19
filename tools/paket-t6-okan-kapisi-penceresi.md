# PAKET T6 — `OKAN-KAPISI` PENCERE TETIGI: sahte OKAN-KAPISI kalemi 24 SAATTE duser

Chip: `KraL-Onarim grubu devami` · 19 Agu 2026 · hedef kat: ISCI · kabul MIMARDA.

---

## 0. NEDEN (BaBa denetimi, 18 Agu — birebir hukum)

Denetim tablosunda T6 satiri: *"sahte OKAN-KAPISI kalemi 24 saatte pencereyle duser"* →
bulunan mekanizma: **`OKAN-KAPISI` yalniz bir DURUM ETIKETI; pencere tetigi yok** →
hukum **KURULMAMIS**.

Yani bugun bir kalem `OKAN-KAPISI` etiketini alinca **sinirsiz** orada durabiliyor.
Etiket bir bekleme yeri degil, bir **pencere** olmali: 24 SAAT (birim ACIK, `24s` YASAK)
dolunca kalem sessizce beklemeye devam EDEMEZ — yuzeye cikar.

## 1. HUKUM — pencere DOLUNCA kalem DUSER, ama SESSIZCE COZULMEZ

* Pencere = **24 SAAT**. Etiketin damgasindan itibaren.
* Pencere dolunca kalem `OKAN-KAPISI` durumundan **DUSER** ve `T6-IZ` satiriyla mimar
  posta kutusuna yuzeye cikarilir.
* 🔴 **Kalem KAPATILMAZ, cozulmez, kararı VERILMEZ.** Pencere yalniz "bu kalem 24 saattir
  Okan'da bekliyor" olgusunu GORUNUR kilar. Karar Okan'indir; arac karar YERINE GECMEZ.
* 🔴 **FAIL-CLOSED:** damga yok / bozuk / gelecek tarihli ise kalem `T6-OLCULEMEDI` olur;
  **"pencere icinde" SAYILMAZ** ve **dusurulmez de**. Olculemeyen kalem ne yesil ne
  islenmis sayilir.

## 2. TEK KAYNAK — damga ureticisi PAYLASILIR, IKIZLENMEZ

🔴 Hareket damgasi bu depoda **tek** yerden turetilir: `tools/durgun-kalem-kapisi.py`
icindeki `--damga-uret` kolu (T5b paketi, ayni dilimde teslim edildi) — damgayi
`DEVAM.md`'nin GIT GECMISINDEN turetir.

**T6 kendi damga ureticisini YAZMAZ**; T5'in ureticisini **import ederek** kullanir.
Ikinci bir turetme yolu acilirsa iki tanim sessizce ayrisir
([[ikiz-tanim-sessiz-ayrisma]]) — bu turda o yasak KABUL KAPISIDIR, tavsiye degil.
Ayni sekilde damga COZUMLEME (`_damga_coz`) ve gelecek-tarihli/bozuk siniflandirmasi da
T5'ten alinir; T6 yalniz **esigi** (24 SAAT) ve **etiket suzgecini** (`OKAN-KAPISI`) ekler.

## 3. TESLIM EDILECEK — `tools/okan-kapisi-penceresi.py`

Kollar (her biri MUTANT tarafindan hedef kolu kanitlanacak):

| Kol | Anlam |
|---|---|
| `T6-DUSTU` | etiket damgasi >= 24 SAAT → kalem duser + `T6-IZ` yazilir |
| `T6-PENCEREDE` | < 24 SAAT → DOKUNULMAZ (yanlis-pozitif nobeti) |
| `T6-OLCULEMEDI` | damga yok/bozuk/gelecek → fail-closed; ne duser ne pencerede sayilir |
| `T6-IZ` | dusen kalem icin mimar posta kutusuna iz satiri (yazilamazsa KIRMIZI) |

Kollar:

* `--kendini-test` — sentetik fikstur; son satir + rc=0.
* `--curutme` — her mutantin hedef kolunu **AYRICA** kanitlar (asagi bkz).
* `--gercek` — gercek defter + T5 ureticisinin damgalariyla siniflandirma **BASAR**;
  🔴 **YAZMAZ** (canli devir/dusurme Okan kapisi). Cikti son satiri:
  ```
  T6 KALEM=<n> DUSTU=<n> PENCEREDE=<n> OLCULEMEDI=<n> ESIK_SAAT=24
  ```
  Bir eksen olculemiyorsa `0` YAZILMAZ → `OLCULEMEDI` + SEBEP, rc≠0.

## 4. KABUL (calistirilabilir)

```
python3 /Users/okan/dev/pruvo/tools/okan-kapisi-penceresi.py --kendini-test
python3 /Users/okan/dev/pruvo/tools/okan-kapisi-penceresi.py --curutme
```

son satirlar + rc=0:

```
VAKA=<n> DUSEN=0 MUTANT=4/4 HEDEF_KOL_ATFI=4/4 KONTROL=2/2 TEMIZ=EVET
CURUTME=4/4
```

### 4.1 Mutasyon bataryasi — 4/4 KIRMIZI, her biri HEDEF KOLUNU AYRICA kanitlar

🔴 **K182 BAGLAYICI:** her mutant icin (a) hedef kol kirmizi VE (b) yan eksenler YESIL
ayrica gosterilir; `HEDEF_KOL_ATFI=<EVET|HAYIR>` basilir. Dordu de EVET olmadan
`MUTANT=4/4` YAZILMAZ ([[mutant-yan-ekseni-de-tetikliyorsa-olcmez]]).

| # | Mutasyon | Dusmesi gereken |
|---|---|---|
| M1 | Esigi 24 SAAT yerine sonsuz yap (hicbir kalem dusmez) | `T6-DUSTU` kolu KIRMIZI; `T6-PENCEREDE` YESIL kalmali |
| M2 | Pencere icindeki kalemi de dusur | `T6-PENCEREDE` kolu KIRMIZI; `T6-DUSTU` YESIL kalmali |
| M3 | Damgasi yok/bozuk kalemi "pencerede" say (fail-open) | `T6-OLCULEMEDI` kolu KIRMIZI; diger kollar YESIL kalmali |
| M4 | `T6-IZ` yazimini sessizce atla (yazamayinca yine de basarili say) | `T6-IZ` kolu KIRMIZI; siniflandirma kollari YESIL kalmali |

### 4.2 Curutme bataryasi — 4/4

Her kol icin: o kolun GOVDESI oldurulunce nisanlandigi mutantin **SESSIZ** kalmadigi
(yani mutantin gercekten O kolu olctugu) gosterilir. `CURUTME=4/4` yazilmadan kabul YOK.

### 4.3 Kontroller — 2/2 YESIL

* **K1** — `OKAN-KAPISI` etiketi TASIMAYAN kalemler hicbir kovaya girmez; eklenmeleri
  sayaclari DEGISTIRMEZ (etiket suzgeci gercekten suzuyor).
* **K2** — T5'in mevcut `--kendini-test` ve `--curutme` sonuclari T6 eklendikten sonra
  AYNEN gecer (gerileme nobeti; paylasilan uretici bozulmadi).

### 4.4 Fikstur kurali

Sentetik kok + sentetik defter + sentetik posta kutusu. **Gercek `DEVAM.md`, gercek
`memory/mimar-posta-kutusu.md` ve gercek durum dosyasi DEGISMEZ.** Kapanista `git status`
+ kutunun bayt boyutu once/sonra rapora yazilir ve `KUTU_DEGISMEDI=EVET` kanitlanir.
Gecici kok SILINIR, `TEMIZ=EVET` son satirda.

## 5. SINIRLAR

* Canli kablo (cron/kanca) bu turda **KURULMAZ** — parti akisini durdurmak Okan kapisi.
  Yalniz olcum kolu acilir. CI (SERIT B) kablolamasi AYRI dilim (chip yapar).
* Arac hicbir kalemi KAPATMAZ / karar VERMEZ.
* `DEVAM.md`'ye YAZILMAZ (defter mimarindir).
* `.github/workflows/nobet.yml`'e DOKUNULMAZ.

## 6. ISCI TALIMATI (baglayici)

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
