# PAKET T6b — T6'nin CANLI DUZLEMI BOS: aranan jeton gercek defterde HIC GECMIYOR

Chip: `KraL-Onarim grubu devami` · 19 Agu 2026 · hedef kat: ISCI · kabul MIMARDA.

---

## 0. OLCULEN OLGU (chip olctu; ham kanit)

`tools/okan-kapisi-penceresi.py` (T6, commit `04c5ccd9`) kuruldu:
`MUTANT=4/4 HEDEF_KOL_ATFI=4/4 CURUTME=4/4 KONTROL=2/2`. Ama gercek defterde:

```
--gercek : T6 KALEM=0 DUSTU=0 PENCEREDE=0 OLCULEMEDI=0 ESIK_SAAT=24
grep -c "OKAN-KAPISI" /Users/okan/dev/pruvo/DEVAM.md   ->  0
```

🔴 **`KALEM=0`, "hicbir kalem Okan'da beklemiyor" DEMEK DEGIL.** Suzgecin aradigi
jeton (`OKAN-KAPISI` / `OKAN KAPISI`) defterin **acik kalem bolgesinde** hic
gecmiyor. Yani T6 tam da T5'in dogdugu kusurla dogdu: **kapi VAR, yesil, ama
OLCTUGU DUZLEM BOS.** Sentetik fiksturde calisiyor, canli veride hicbir sey
olcmuyor.

Defterin FIILI park yuzeyleri (chip olctu, `grep -o "OKAN[ '-]*[A-Z]*"`):

| Yuzey | Ornek | Park mi? |
|---|---|---|
| `## OKAN'DA` **BOLUMU** | bolumun altindaki maddeler | **EVET** — kalemler orada park ediyor |
| satir ici `OKAN KAPISI` | `🔧 **K198 (19 Agu — ⚖️ OKAN KAPISI):**` | **EVET** — Okan'in hukmu bekleniyor |
| satir ici `OKAN KARARI` | `🔧 **K190 — ⚖️ OKAN KARARI 19 Agu: ...**` | 🔴 **HAYIR** |

## 1. HUKUM — suzgec GERCEK yuzeylere baglanir, `OKAN KARARI` DISARIDA KALIR

🔴 **AYRIM (mimar hukmu, baglayici):** `OKAN KARARI` bir park etiketi DEGILDIR —
Okan'in **ZATEN VERDIGI** karari isaretler. Suzgece katilirsa verilmis kararlar
"24 saattir bekliyor" diye yuzeye cikar ve pencere tetigi GURULTU uretir; kapi
kendi guvenilirligini yakar. Bu ayrim KONTROL vakasiyla KANITLANACAK.

Yeni suzgec (ikisinden BIRI yeterli):

1. Kalem `## OKAN'DA` bolumunun ALTINDA yer aliyor, **VEYA**
2. Kalem satiri `OKAN-KAPISI` / `OKAN KAPISI` ibaresini tasiyor (case-insensitive).

**HARIC:** yalnizca `OKAN KARARI` tasiyip yukaridaki ikisine de uymayan kalem.
(Bir kalem hem `## OKAN'DA` altindaysa hem `OKAN KARARI` diyorsa **DAHILDIR** —
konum kazanir; gerekce: bolum uyeligi acik bir park beyanidir.)

🔴 **FAIL-CLOSED KORUNUR:** suzgece giren ama damgasi yok/bozuk/gelecek olan kalem
`T6-OLCULEMEDI` KALIR; "pencerede" SAYILMAZ, dusurulmez de.
🔴 **KAPSAM GENISLETME YOK:** T6'nin DUSTU/PENCEREDE/OLCULEMEDI/IZ kol mantigi
DEGISMEZ; yalniz hangi kalemlerin kovaya girecegi degisir.
🔴 **HUKUM TEK YERDE:** etiket suzgeci TEK bir fonksiyonda kalir; ikinci bir
"park mi" karar noktasi ACILMAZ.

## 2. KABUL (calistirilabilir)

```
python3 /Users/okan/dev/pruvo/tools/okan-kapisi-penceresi.py --kendini-test
python3 /Users/okan/dev/pruvo/tools/okan-kapisi-penceresi.py --curutme
python3 /Users/okan/dev/pruvo/tools/okan-kapisi-penceresi.py --gercek
```

Mevcut `MUTANT=4/4 HEDEF_KOL_ATFI=4/4 CURUTME=4/4 KONTROL=2/2` **AYNEN gecmeye
devam etmeli** (gerileme nobeti); uzerine yeni vakalar. Son satirlar + rc=0.

### 2.1 Yeni mutantlar — 2/2 KIRMIZI, hedef kol AYRICA kanitli

🔴 **K182 BAGLAYICI:** her mutant (a) hedef kol KIRMIZI VE (b) yan eksenler YESIL
ayrica gosterilir; `HEDEF_KOL_ATFI=<EVET|HAYIR>` basilir. Ikisi de EVET olmadan
`MUTANT=n/n` YAZILMAZ ([[mutant-yan-ekseni-de-tetikliyorsa-olcmez]]).

| # | Mutasyon | Dusmesi gereken |
|---|---|---|
| M5 | `## OKAN'DA` bolum uyeligini suzgecten cikar (yalniz satir ici ibare kalsin) | bolum-uyeligi vakasi KIRMIZI; satir-ici ibare kolu YESIL kalmali |
| M6 | `OKAN KARARI` tasiyan kalemi de suzgece KAT | `OKAN KARARI` haric-tutma vakasi KIRMIZI; `OKAN KAPISI` kolu YESIL kalmali |

### 2.2 Yeni kontroller — 2/2 YESIL

* **K3** — `## OKAN'DA` altinda olup ayrica `OKAN KARARI` diyen kalem **DAHILDIR**
  (konum kazanir); suzgecten DUSMEZ.
* **K4** — Hicbir park ibaresi/konumu tasimayan kalem hicbir kovaya GIRMEZ ve
  sayaclari DEGISTIRMEZ (mevcut K1'in devami).

### 2.3 Fikstur kurali

Sentetik defter. **Gercek `DEVAM.md` ve gercek posta kutusu DEGISMEZ**; kapanista
md5 oncesi/sonrasi rapora yazilir, `KUTU_DEGISMEDI=EVET`. Gecici kok SILINIR,
`TEMIZ=EVET`.

## 3. 🔴 GERCEK KOSUM — ASIL KABUL BURADA

`--gercek` gercek defterde kosulur, **ham cikti tamami** rapora girer.

🔴 **`KALEM=0` DONERSE BU TUR BASARISIZDIR** — suzgec hala bos duzlem olcuyor
demektir. O halde `OLCULEMEDI` + SEBEP yazilir ve **onarim denenmez**, mimara
donulur. Beklenen bir DUSTU/PENCEREDE dagilimi YOKTUR; ne cikarsa o yazilir —
ama `KALEM` sifirdan BUYUK olmalidir, cunku defterde park edilmis kalem fiilen
VARDIR (`## OKAN'DA` bolumu dolu, K198 `OKAN KAPISI` tasiyor).

Ayrica raporda: suzgece giren kalemlerin **kimlik listesi** (kac tanesi bolum
uyeliginden, kac tanesi satir ici ibareden geldi).

## 4. SINIRLAR

* Canli kablo (cron/kanca) KURULMAZ — parti akisini durdurmak Okan kapisi.
* Arac hicbir kalemi KAPATMAZ / karar VERMEZ; yalniz YUZEYE CIKARIR.
* `DEVAM.md`'ye YAZILMAZ (defter mimarindir).
* `.github/workflows/nobet.yml`'e DOKUNULMAZ.

## 5. ISCI TALIMATI (baglayici)

* Calisma agaci **YALNIZ** `/Users/okan/dev/pruvo/.claude/worktrees/dreamy-mclean-669442`.
  Mutlak yol kullan; ana agaca (`/Users/okan/dev/pruvo`) **YAZMA**
  ([[isci-worktree-yerine-ana-agaca-yazar]]).
* 🔴 Ana agacta `urunler.json` BASKA bir oturumun commit'siz isi olarak KIRLI —
  **DOKUNMA**, `git checkout`/`restore`/`stash` ile geri ALMA. KABUL KAPISI
  ([[isci-merge-blokunu-checkoutla-cozer]]). Kapanista `git reflog -n 10` raporla.
* **COMMIT ATMA** — commit'i chip atar.
* Rapor: dalda **kanonik muhendis raporu dosyasi** (bu evde tek ad, izlenmez);
  varsa BASINA damgayla EKLE, uzerine YAZMA.
* Olcemedigine `OLCULEMEDI` + SEBEP; sessiz yesil YASAK.
* Tavan ~30 tur, tek dilim. Alt ajan / paralel gorev ACMA.
