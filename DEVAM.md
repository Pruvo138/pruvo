# DEVAM (KraL) — 4 Agu 2026

## 🟠 ACIK KALEM (kanca kablolama dali, agent-aabf841a) — bu turda GENISLETILMEDI
`tools/is-akisi-kapisi.py::SERIT_B` tablosu (is_akisi, job, **betik-yolu**) granulunde
anahtarlaniyor. Yani bir betik SERIT_B'de beyanliysa o betigin GELECEKTEKI TUM bayrakli
cagrilari da sessizce muaf sayilir. Bu dalin getirdigi bir gerileme DEGIL — mevcut tasarim;
`kanca-kablolama-test.py`nin `--mutasyon` kolu da bu yuzden ayrica beyan istemeden gecti.
Gelecek is: SERIT_B'yi (is_akisi, job, betik, **bayrak**) granulune tasimak (bu turda kapsam disi).

## 🔚 OTURUM KAPANISI — 4 Agu · YENI OTURUM ONCE BUNU OKU

**CANLIYA GITTI (bu oturum, hepsi SHA-kanitli + canli olculdu):**
`bd463ee1` marka-model uyeligi `marka[1]` konumundan kurtarildi — canli Zafira **10 -> 21**,
Golf 177 -> 182, model sayfasi 433 -> 485, kaybolan urun 0 ·
`948be793` kusak/varyant katlamasi + model-olmayan sayfalarin kapanmasi + Transporter
birlestirme — Transporter **44 -> 143**, Astra 77 -> 126, Golf +17, Zafira +0 (degismemeli,
degismedi); `ford/focus-st` · `fiesta-st` · `ecoboost` 404 oldu, 14 urunun tamami korundu ·
`9cb1e3ee` cron nabiz korlugu + KADANS KURTARMA (uzlastirma artik push'a bagli, cron ikinci kol) ·
`896f05fa` D1 sapma sinyali yayin sagligi sinyalinden AYRILDI (susturulmadan; yeni
`workflow_run` alarm kanali canli ateslediği dogrulandi) · `117f1420` yayin hatti acildi ·
`4373c02f` + `01bc95f9` DEVAM.md hijyeni.

**KOSAN IS YOK.**

**Saatlik CI nobeti 4 Agu ~17:40Z — TEMIZ, ISLEM YOK (duzeltme de mail silme de yapilmadi).**
Ev kontrolu: `/Users/okan/dev/pruvo` (dogru ev). Mail taramasi isciye delege edildi:
inbox 7537 mesaj, uc toplu Apple Event listesi tutarli (ornekleme yok); son 70 dk icinde
gonderen `notifications@github.com` + konu "Run failed" eslesmesi **0** — dolayisiyla
Cop'e tasinan mail **0**. Bagimsiz teyit (`gh run list`): son 70 dk'daki tek failure
`30929902990` (headSha `20fbff61`, 16:35Z, `serit-a2`+`serit-a3`, deploy/yayin skipped) —
bu, 16:45Z turunda `8073ea6f` ile zaten kapatilan kok nedenin son kosumu; sonraki main
kosumu **`30932568804`** (headSha `cc625f42`) `build`+`serit-a2`+`serit-a3`+`serit-b`+
**`deploy`**+**`yayin`** hepsi `success` -> yeni kirmizi yok, yeni duzeltme gerekmedi.
Kapsam disi (akan is, sonraki tur olcer): `30933417243` (17:20Z) `build` yesil, `serit-a3`
hala in_progress; `30935031779` (17:40Z) yeni push ile pending. Cancelled kosumlar
(`30933307590`, `30933255362`) mukerrer push kaynakli, failure degil.

**BEKLIYOR — baskalarinda:**
- **MaCiT** → metin/alan boslugu 1. PARTI (en buyuk 50 model; kaynak liste kararsiz jetonlar
  cikarilmis 6288 kayit / 4513 urun / 817 cift) + EK PARTI (616 urun, **0 yeni sayfa**).
  Parti bitmeden 2. parti acilmiyor. Ayrica hasat aciklama SABLONU kok nedeni.
- **HocA** → (`ara*` rota kalemi KAPANDI: kutuda kapanis notu, main `c01b70e`, deploy `7830b5f2`;
  kalici kapi `rota-yuzey-nobetci.mjs` kuruldu) · **ACIK:** uc `model` parametresini
  `uyum[].model`'de TAM eslesmeyle suzuyor; 467 cipin 210'unda cip ile ucun teslimi ayrisiyor
  (965 urun-kalemi). Musteriye sayi gosterilmiyor; ucun katlamayi almasi karari onda.
- **KaaN** → `rulman` semasi onarilinca satisa acma karari bende · **ArTisT** → marka-model
  sayfa esigi onerisi.

**OKAN'DA KARAR YOK.** Bugun sorulan uc karar verildi ve uygulandi: asamali git (1. parti 50
model) · Zafira sayfasi 28 hedefi, `Zafira Life` ayri bolumde · yayin hattini KraL acsin.

**🔴 SIRADAKI TUR — bende, oncelik sirasiyla:**
1. 🔴 **OKAN HUKMU — TUM markalarda sayfa adedi == arama adedi.** Olculdu (128 marka, 18.080):
   **77 markada fark, 6.445 kalem.** Farkin **%94'u SAYFA EKSIKLIGI DEGIL, ARAMA GURULTUSU**:
   `Havalandırma`->"Haval" 562 · `Mandalı/manuel`->"MAN" 3.488 · `33mm`->"3M". Yani sayfa
   buyuyerek degil **arama daralarak** esitlenecek. Faz 0+1 canlida (yukarida); **kalan faz:
   marka jetonlu sorgunun uyelik yuklemine yonlendirilmesi** -> 6.087 kalem KENDILIGINDEN kapanir.
   🔴 **VERI partisi (486 kalem / 450 urun) AYNI ANDA gitmeli** (MaCiT: Sierra/NGK/Teleflex marin
   parcalari, baslikta "Mercury Verado" yaziyor ama `marka[]`'de yok) — yoksa "sayilar esitlendi"
   derken 450 GERCEK eslesme kaybedilir. Tam tablo: scratchpad `marka-sayfa-arama-fark.tsv`.
2. C kovasi (87 urun): olcu satiri sayisal model adiyla cakisiyor — `ara`->`marka` toplu kopya YASAK.
1b. 🔴 ACIK KALEM: kapi agaci dogrulama — dokum DEVAM-ARSIV.md de (git disi).
1c. ACIK KALEM: icerik denetimi borcu — dokum DEVAM-ARSIV.md de (git disi).
1d. Duvar-susu kapisinin YAPISAL cozumu (liste kovalamayi bitirir): kanit varsa metinde
   **cip evreninden bilinen MODEL adi** ara — varsa gec, yoksa RED. Olctur, sonra uygula.
2b. 🔴 **`ege-bilgi.md` TAVAN PAYI 27 KALDI** (5973/6000 UTF-16; bot `slice(0,6000)`).
   `filamentler.json`'a TEK filaman eklenmesi (~110 karakter) tavani asar ve CI'i kirar —
   uretilen `FILAMENT-REF` blogu dosyaya giriyor. Bu dalin hatasi degil ama pay artik kritik dar;
   ya tavan/ozetleme yeniden tasarlanmali ya blok kisaltilmali. **BASKASININ isini kirar** (KaaN/MaCiT
   filaman ekleyince), oncelikli.
2c. **`/marka/bmw/motorrad/` HUKMU (SINIF 1 muhendisinin kapsam disi bulgusu, karar bende):**
   canli, 8 urun. `Motorrad` BMW'nin motosiklet KOLU, model DEGIL — sinifi `PSA`/`VAG` ile birebir
   ayni ve onlar kapatildi. **HUKUM: model-olmayan cifte yazilacak, sayfa kapanacak** (urun
   kaybolmuyor: marka sayfasi + arama acik). Tutarlilik kazaniyor; ayri turda uygulanacak.
   Ayni turda `Mercedes|A/S/V` (2/1/1 urun, esik alti) ele alinsin: bunlar TEK HARF ama GERCEK
   model (A/S/V Serisi) — kapatilmayacak, kanonik gosterimi `A Serisi` bicimine baglanacak.
3. ~~FR-S sapmasi~~ **KARAR VERILDI (KraL, 4 Agu): DARALTMA YOK, kural oldugu gibi kaliyor.**
   `frs` canon'u SAHIPSIZ kalacak. Gerekce: `FR-S` bir Scion rozeti, Scion katalogda marque
   olarak YOK; `(Toyota, FR-S)` ya da `(Subaru, FR-S)`'i allow'a almak o adla SATILMAMIS bir
   aracin sayfasini dogururdu — K19'un kurdugu kuralin tam ihlali. **AD kayboluyor, URUN
   kaybolmuyor** (6 tekil urunun tamami `brz`/`gt86` kovalarinda, olculdu). Yeniden acilmasin.
4. Kutudan devralinanlar: gorsel-kutu bosluk kusuru (`build.py` `height` niteligi) · negatif
   onbellek Cache Rule · `hasat_kontrol.py` atif-turu kapisi.

### 🟡 ACIK KALEM 1 — kuyruk geri tepmesi OLCULEMEDI (48 saat sonra yeniden olculecek)
ACIK: ayrinti DEVAM-ARSIV.md de (git disi).

### 🟡 ACIK KALEM — korumanin tasinabilirligi (uc kalem)
(a) Koruma her ortamda ayni sekilde durdurmuyor (durum DEGISMEDI); ayrinti
DEVAM-ARSIV.md de (git disi). Ilgili dosya depoya girmedigi icin dal icinden
kapatilamaz — ayri tur gerekiyor.
(b) Kapi `pre-commit`/`pre-push` icinden cagrildiginda git kendi kancalarini
`GIT_DIR`/`GIT_INDEX_FILE` TANIMLI olarak kosar; yani (a) kapandiginda ortam kirliligi
GERCEK bir yol olur — bu tur tam o yolu kapatti, kayda gecsin.
(c) KAPANDI — ic isci-rapor protokol adina yapilan atiflarin hijyeni: asagidaki
"public depo hijyeni" kalemine bak (merge 20fbff61).

## 🔴 YENI ACIK KALEM — A0 DAMGA alarmi kirmizi: D1 uzlastirici cron'u TESLIM ETMIYOR
ACIK: ayrinti DEVAM-ARSIV.md de (git disi).

## 🔴 YENI ACIK KALEM — katalog geneli metin/alan bosluğu (envanter cikti)
ACIK: ayrinti DEVAM-ARSIV.md de (git disi).

ACIK KALEM: yayin hatti icerik denetimi — dokum DEVAM-ARSIV.md de (git disi).

## 🟡 YENI ACIK KALEM — `CLAUDE.md`/`AGENTS.md` git disi symlink
ACIK KALEM: symlink surumleme ayrintisi — dokum DEVAM-ARSIV.md de (git disi).
