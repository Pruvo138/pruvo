# PAKET T3b — `SAHIPSIZ=44`: mutasyon aileleri kapiya BAGLANAMIYOR

Chip: `KraL-Onarim grubu devami` · 19 Agu 2026 · hedef kat: ISCI · kabul MIMARDA.

---

## 0. ILK BLOK — KAPSAM ON-OLCUMU (K191 geregi; ONCULDEN IS URETME)

🔴 **Bu paket "44 kalem" oncululle BASLAMAZ.** Isci ONCE olcer, sonra is uretir:

```
python3 /Users/okan/dev/pruvo/tools/t3-yonlendirme-kapisi.py --sahipsiz-listele
```

Ham cikti **oldugu gibi** rapora yapistirilir. Bu koda gore:

* `SAHIPSIZ=<n>` gercekten kac? (paketin yazildigi anda beyan edilen sayi **44**;
  **farkli cikarsa OLCULEN sayi gecerlidir**, spec'teki DEGIL)
* Kac tanesi `-mutasyon` ailesinden, kac tanesi baska sinif?

🔴 Olculen tablo beyandan SAPIYORSA is ona gore daralir/genisler; sapma rapora
`SAPMA=` satiriyla yazilir. Bayat oncul uzerine is kosturmak bu depoda yasak
([[spec-oncul-kapsam-on-olcumu]]).

## 1. NEDEN (olculen mekanizma)

`tools/t3-yonlendirme-kapisi.py :: mekanizma_icin_ev()` bir mutant bataryasinin EV'sini
**yalniz DOSYA ADINDAN** turetiyor: `X-mutasyon.py` → `X-kapisi` / `X` denenir, bulunamazsa
`BILINMIYOR`. Gercek depoda mutant dosyasinin adi olctugu kapinin adiyla cogu zaman
ORTUSMUYOR — bu yuzden aile kapiya baglanamiyor.

Kapinin kendi yorumunda yazan kural dogru: **"`X-mutasyon.py` icin EV, olctugu kapinin
EV'idir."** Kusur kuralda degil, kuralin **AD BENZERLIGIYLE** uygulanmasinda.

## 2. HUKUM — EV, ADDAN degil ICERIKTEN turetilir

🔴 **SAHIP UYDURULMAZ.** Bu turda hicbir eve elle sahip atanmaz. Kural:

> Bir `-mutasyon` dosyasinin EV'i, o dosyanin **fiilen REFERANS VERDIGI** kapi(lar)in
> haritadaki EV'idir.

Uygulama (`mekanizma_icin_ev()` icinde YENI adim, mevcut 1-2-3 adimlarindan SONRA,
onlarin davranisini DEGISTIRMEDEN):

1. Mutant dosyasinin metni okunur; icinde gecen `tools/` altindaki betik adlari
   (`<ad>.py` / `<ad>.js`) toplanir. Kendi adi ve `-test`/`-mutasyon` turevleri haric.
2. Bulunan adlarin haritadaki EV'leri cikarilir; `BILINMIYOR` olanlar atilir.
3. **Tam olarak BIR** ayirt edici EV kaldiysa → o EV.
4. **SIFIR** kaldiysa → `BILINMIYOR` (SAHIPSIZ KALIR — durust sonuc, kusur degil).
5. **BIRDEN COK** ayrik EV kaldiysa → `BILINMIYOR` **ve** `CAKISMA` sayaci artar.
   🔴 Coklu adaydan **SESSIZCE BIRI SECILMEZ**; secim mimarin isidir.

🔴 **FAIL-OPEN YASAGI:** yeni adim hicbir kosulda `BILINMIYOR`'u bir EV'e cevirmek icin
varsayilan/ilk-eslesen/alfabetik secim YAPMAZ. `SAHIPSIZ` sayaci DUSMEK ZORUNDA DEGIL —
durust bir `SAHIPSIZ=<k>` , uydurulmus bir `SAHIPSIZ=0`'dan IYIDIR. Dosya okunamazsa
(IO/encoding) o mekanizma `BILINMIYOR` KALIR ve `OKUNAMADI` sayaci artar; sessiz `0` yasak.

## 3. TESLIM EDILECEK

* `tools/t3-yonlendirme-kapisi.py` — yukaridaki 4. adim + sayaclar.
* `--analiz` / `--sahipsiz-listele` ciktisina EK son satir:
  ```
  SAHIPSIZ=<n> COZULDU_ICERIKTEN=<n> CAKISMA=<n> OKUNAMADI=<n>
  ```
* Harita (`tools/sahiplik-haritasi.tsv`) **DEGISTIRILMEZ** — bu turda satir eklenmez.

## 4. KABUL (calistirilabilir)

```
python3 /Users/okan/dev/pruvo/tools/t3-yonlendirme-kapisi.py --kendini-test
```

Mevcut `MUTANT=4/4` **AYNEN gecmeye devam etmeli** (gerileme yok); uzerine yeni vakalar.
Son satir + rc=0.

### 4.1 Yeni mutantlar — 3/3 KIRMIZI, her biri HEDEF KOLUNU AYRICA kanitlar

🔴 **K182 BAGLAYICI:** her mutant hedef kolun kirmizi yandigini VE yan eksenlerin YESIL
kaldigini AYRICA gosterir; `HEDEF_KOL_ATFI=<EVET|HAYIR>` basilir. Hepsi EVET degilse
`MUTANT=n/n` YAZILMAZ ([[mutant-yan-ekseni-de-tetikliyorsa-olcmez]]).

| # | Mutasyon | Dusmesi gereken |
|---|---|---|
| M5 | Coklu ayrik EV'de ILKINI sec (sessiz secim) | `CAKISMA` vakasi KIRMIZI; tekil-EV kolu YESIL kalmali |
| M6 | Sifir aday kalinca varsayilan bir EV dondur | `SAHIPSIZ` kolu KIRMIZI; `COZULDU_ICERIKTEN` YESIL kalmali |
| M7 | Referans taramasina dosyanin KENDI adini da kat | oz-referans vakasi KIRMIZI; `CAKISMA` kolu YESIL kalmali |

### 4.2 Kontroller — 2/2 YESIL kalacak

* **K3** — Ad ekseninden ZATEN cozulen bir mekanizmanin EV'i DEGISMEZ (yeni adim
  eskiyi EZMEZ; 4. adim yalniz `BILINMIYOR` kalanlar icin calisir).
* **K4** — Mevcut 4 mutant (M1-M4) AYNEN gecer (gerileme nobeti).

### 4.3 Fikstur kurali

Sentetik kok + sentetik harita; **gercek `tools/sahiplik-haritasi.tsv` DEGISMEZ**.
Kapanista `git status` ile `HARITA_DEGISMEDI=EVET` kanitlanir. Gecici kok SILINIR,
`TEMIZ=EVET`.

## 5. GERCEK KOSUM — rapora BIREBIR

Onarimdan SONRA `--sahipsiz-listele` yeniden kosulur; **once/sonra iki ham cikti** da
rapora girer. Beklenen bir sayi YOKTUR; `SAHIPSIZ` dusmeyebilir de — o zaman
`COZULEMEDI` gerekcesi (CAKISMA / referanssiz dosya) sayiyla yazilir.

## 6. SINIRLAR

* Sahiplik ATAMASI (haritaya yeni satir) bu turda YAPILMAZ — mimar kapisi.
* Kapinin YON/OLCULEMEDI/IZ kollarina DOKUNULMAZ.
* `DEVAM.md`'ye YAZILMAZ.

## 7. ISCI TALIMATI (baglayici)

* Calisma agaci **YALNIZ** `/Users/okan/dev/pruvo/.claude/worktrees/dreamy-mclean-669442`.
  Mutlak yol kullan; ana agaca (`/Users/okan/dev/pruvo`) **YAZMA**
  ([[isci-worktree-yerine-ana-agaca-yazar]]).
* **COMMIT ATMA** — commit'i chip atar.
* `.github/workflows/nobet.yml`'e **DOKUNMA** (CI kablolamasi ayri dilim).
* Baska oturumun kirli dosyasina DOKUNMA; `git checkout`/`restore` ile kimsenin
  commit'siz isini geri ALMA — KABUL KAPISI ([[isci-merge-blokunu-checkoutla-cozer]]).
  Kapanista `git reflog -n 10` raporla.
* Rapor: dalda **kanonik muhendis raporu dosyasi** (bu evde tek ad, izlenmez); varsa
  BASINA damgayla EKLE, uzerine YAZMA.
* Olcemedigine `OLCULEMEDI` + SEBEP; sessiz yesil YASAK.
* Tavan ~40 tur, tek dilim. Alt ajan / paralel gorev ACMA.
