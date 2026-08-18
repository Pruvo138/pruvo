# PAKET T1b — UCUNCU KOVA IKI KOK NEDENI BIRLESTIRIYOR: `KOSMADI` ↔ `BEKLEMEDE`

Chip: `KraL-Onarim grubu devami` · 19 Agu 2026 · hedef kat: ISCI · kabul MIMARDA.

🔴 **TARIHLI.** Pencere `2026-08-20T08:48:05Z`'de kapaniyor. Bu onarim NIHAI tablo
uretilmeden ONCE girmeli, yoksa nihai tablo da ayni kusurla basilir.

---

## 0. OLCULEN KUSUR (chip olctu, ham kanit commit `54016a42` mesajinda)

`tools/t1-kiyas.py` beklenen her tur icin uc kova uretiyor: `OLCULDU` /
`OLCULEMEDI` / `KOSMADI`. Kod (`t1-kiyas.py`, siniflandirma dongusu):

```
kayit = kayit_dict.get(dak)
if kayit is None:
    kova = "KOSMADI"
```

Yani **log kaydi olmayan HER beklenen tur** `KOSMADI` sayiliyor — turun **vakti
gelmis olsun ya da olmasin**. Gercek kosumda:

```
BEKLENEN_TUR=48 OLCULDU_TUR=12 OLCULEMEDI_TUR=2 KOSMADI_TUR=34 DURUM=ACIK
```

48 turun yalnizca 14'u gecti; kalan **34 tur HENUZ VAKTI GELMEDI**. Yani bugun
`KOSMADI_TUR=34` "cron atesleyemedi"yi degil, neredeyse tamamen "sirasi gelmedi"yi
sayiyor.

🔴 **NEDEN KUSUR:** T1'in kendi baglayici kurali kovalari BIRLESTIRMEMEKTIR.
`OLCULEMEDI`yi `OLCULDU`dan ayirmanin gerekcesi neyse (iki ayri kok neden tek
sayida erimesin), `KOSMADI` icinde "vakti gelmemis" ile "vakti gelmis ama kayit
yok"un erimesi de aynen kusurdur. Ustelik yon YANILTICI: pencere kapanisinda
`KOSMADI` gercekten "kacirilmis tur" anlamina gelecek, ama bugunku ara tabloyu
okuyan biri 34 turun kacirildigini sanir.

## 1. HUKUM — ucuncu kova IKIYE ayrilir

| Kova | Tanim |
|---|---|
| `OLCULDU` | kayit VAR, `TETIK` jetonu `OLCULEMEDI` DEGIL |
| `OLCULEMEDI` | kayit VAR ama `TETIK=OLCULEMEDI` |
| `KOSMADI` | kayit YOK **ve** turun beklenen damgasi **`simdi`den KUCUK/ESIT** (vakti geldi, kayit yok → gercekten kacirildi) |
| `BEKLEMEDE` | kayit YOK **ve** turun beklenen damgasi **`simdi`den BUYUK** (henuz vakti gelmedi) |

* `simdi` **enjekte edilebilir** olmali (`--simdi <ISO>`) ki kabul testi
  determinist kosabilsin; 🔴 **varsayilani GERCEK UTC saati** olacak.
  (Bu turda ayni depoda bir kez daha olculdu: gelecege ayarli bir "simdi",
  esik tabanli bir kapinin canli olcumunu SESSIZCE gecersiz kilar — T5'in
  `--gercek` kolu tam bu yuzden yeniden kosuldu.)
* Sayaclarin toplami DEGISMEZ:
  `OLCULDU + OLCULEMEDI + KOSMADI + BEKLEMEDE == BEKLENEN_TUR`.
* `DURUM=KAPANDI` iken `BEKLEMEDE` **0 olmalidir**; 0 degilse bu bir ic tutarsizlik
  isaretidir → `OLCULEMEDI` + SEBEP, rc≠0 (sessiz gecme YOK).

### 1.1 Son satir (makine-okunur) — `BEKLEMEDE` EKLENIR

```
T1 PENCERE=<..> FIILEN_BASLANGIC=<..> BEKLENEN_TUR=<n> OLCULDU_TUR=<n> OLCULEMEDI_TUR=<n> KOSMADI_TUR=<n> BEKLEMEDE_TUR=<n> YENI_KIRMIZI=<n> LLM_TURU_YENI=<n> LLM_TURU_ESKI=<n> DURUM=<ACIK|KAPANDI>
```

🔴 Mevcut jetonlarin adi ve anlami **DEGISMEZ** (yalniz `KOSMADI` daralir,
`BEKLEMEDE` eklenir). Insan-okur tabloya da ayri satir olarak girer.

## 2. KABUL (calistirilabilir)

```
python3 /Users/okan/dev/pruvo/tools/t1-kiyas.py --kendini-test
python3 /Users/okan/dev/pruvo/tools/t1-kiyas.py --gercek
```

Mevcut `MUTANT=4/4 HEDEF_KOL_ATFI=4/4 KONTROL=2/2` **AYNEN gecmeye devam etmeli**
(gerileme nobeti); uzerine yeni vakalar. Son satir + rc=0.

### 2.1 Yeni mutantlar — 2/2 KIRMIZI, hedef kol AYRICA kanitli

🔴 **K182 BAGLAYICI:** her mutant (a) hedef kolun kirmizi yandigini VE (b) yan
eksenlerin YESIL kaldigini AYRICA gosterir; `HEDEF_KOL_ATFI=<EVET|HAYIR>` basilir.
Ikisi de EVET olmadan `MUTANT=n/n` YAZILMAZ
([[mutant-yan-ekseni-de-tetikliyorsa-olcmez]]).

| # | Mutasyon | Dusmesi gereken |
|---|---|---|
| M5 | `BEKLEMEDE` turlarini yine `KOSMADI` say (ayrim kaldirilir) | `BEKLEMEDE` ekseni KIRMIZI; `OLCULDU`/`OLCULEMEDI` sayaclari YESIL kalmali |
| M6 | `BEKLEMEDE` turlarini `OLCULDU` kovasina kat | `OLCULDU` ekseni KIRMIZI; `KOSMADI` ekseni YESIL kalmali |

### 2.2 Yeni kontroller — 2/2 YESIL

* **K3** — Pencere KAPANMIS bir fiksturde `BEKLEMEDE=0` ve `KOSMADI` gercekten
  kacirilan turlari sayar (yani ayrim kapanista dogru colluyor).
* **K4** — Toplam invaryanti: dort kovanin toplami `BEKLENEN_TUR`e ESIT
  (rastgele uretilmis en az 3 fiksturde).

### 2.3 Fikstur kurali

Sentetik kok (`--kok <gecici>`) + enjekte `--simdi`. **Gercek `~/.claude/cron/`
dosyalarina DOKUNULMAZ.** Gecici kok SILINIR, `TEMIZ=EVET` son satirda.

## 3. GERCEK KOSUM — rapora BIREBIR

`--gercek` (simdi ENJEKTE EDILMEDEN, arac kendi UTC saatini kullansin) kosulur ve
**ham ciktinin tamami** rapora girer. Beklenen bir sayi YOKTUR. Ayrica bir
cumleyle: `KOSMADI` bu kosumda kac, `BEKLEMEDE` kac — ve onceki tek-kovali
tablodan farki ne.

## 4. SINIRLAR

* Arac hicbir log/durum/crontab dosyasini YAZMAZ; `t1-pencere.json` DEGISMEZ.
* Pencereyi kapatma/uzatma karari MIMARIN.
* `.github/workflows/nobet.yml`'e DOKUNULMAZ (CI kablolamasi ayri dilim).
* `DEVAM.md`'ye YAZILMAZ.

## 5. ISCI TALIMATI (baglayici)

* Calisma agaci **YALNIZ** `/Users/okan/dev/pruvo/.claude/worktrees/dreamy-mclean-669442`.
  Mutlak yol kullan; ana agaca (`/Users/okan/dev/pruvo`) **YAZMA**
  ([[isci-worktree-yerine-ana-agaca-yazar]]).
* **COMMIT ATMA** — commit'i chip atar.
* Baska oturumun kirli dosyasina DOKUNMA; `git checkout`/`restore` ile kimsenin
  commit'siz isini geri ALMA — KABUL KAPISI ([[isci-merge-blokunu-checkoutla-cozer]]).
  Kapanista `git reflog -n 10` raporla.
* Rapor: dalda **kanonik muhendis raporu dosyasi** (bu evde tek ad, izlenmez);
  varsa BASINA damgayla EKLE, uzerine YAZMA.
* Olcemedigine `OLCULEMEDI` + SEBEP; sessiz yesil YASAK.
* Tavan ~30 tur, tek dilim. Alt ajan / paralel gorev ACMA.
