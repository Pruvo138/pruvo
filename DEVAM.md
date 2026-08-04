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

**Saatlik CI nobeti 4 Agu ~16:45Z — KIRMIZI BULUNDU, ONARILDI, OLCULDU.**
Dort ardisik main kosumu ayni kok nedenle failure: `dced48c` · `f8698eb` · `31769d8` ·
`20fbff6`. Kirilan job'lar `serit-a2` + `serit-a3`; `build` YESILDI ama `deploy` ve `yayin`
**skipped** — yani site dort commit boyunca yayina cikmadi (tek kol kirmizisi degil, gercek
yayin durmasi). Kok neden: `DEVAM.md` icerik-sinifi kapisi 2 satiri ihlal olarak isaretledi
("satirlari DEVAM-ARSIV.md'ye TASI, notr isaretci birak; silme YOK, tasima VAR").
Onarim Codex'e delege edildi; commit `8073ea6f` yalnizca `DEVAM.md`'de 2 satiri notrlestirdi
(katalog/secret/workflow dosyasina DOKUNULMADI, adim silme / `continue-on-error` / esik
gevsetme YOK — kapi susturulmadi, kapinin gosterdigi sey duzeltildi).
Bagimsiz teyit: kosum **`30930607187`** (headSha `8073ea6f`) — `build` · `serit-a2` ·
`serit-a3` · `serit-b` · **`deploy`** · **`yayin`** hepsi `success`.
Mail: gonderen+konu+sha uclu kriteriyle 4 hata maili Cop'e TASINDI (kalici silme yok,
Cop bosaltilmadi); tasima sonrasi inbox'ta eslesen mail 0.
Not: `a35d53fd` kosumu cancelled (mukerrer push), `6f7ac890` kosumu o an in_progress —
ikisi de baska oturumun akan isi, bu nobetin kapsaminda degil, sonraki tur olcer.

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

### ✅ KAPANDI (4 Agu) — model cip satiri kanoniklestirildi + K19 capraz-marka (rozet) kapisi
Merge SHA **`d91ea881`**, kosum `30923737314` headSha BIREBIR **success** (bir onceki main
kosumu `cancelled` idi — `--limit 1` yesili yaniltirdi). Kapsam merge-base `3017d46c`'ten
6 dosya +722/-33; katalog kaynaklari degismedi (ayrinti DEVAM-ARSIV.md'de).
CANLI DELTA (canonical, cache-bust'siz): `/marka/peugeot/iphone/` **404** ·
`/marka/mitsubishi/electric/` **404** · `/marka/peugeot/206/` **200** ve `numberOfItems=58`
cip `n=58` ile BIREBIR · sitemap model sayfasi **534** (552 -> 534 beklenen delta tuttu) ·
canli cip evreni **467 model / 58 marka**.
BAGIMSIZ CURUTME (isci, A/B ayni katalog 17962 — dalin kendi olcumu 17914 ile BAYAT tabandaydi,
kapilar taze katalogla deneme-merge agacinda kosuldu):
- `kaybolan urun 0` **ONAYLANDI** — marka sayfasinda gorunen urun 15539 -> 15539, her yoldan
  dusen 0. Nuans: **7 urun** (5 Mitsubishi Electric + 2 Peugeot iPhone) yalnizca model-sayfasi
  rotasini kaybetti, kasitli eleme sinifi, marka sayfasi + arama ACIK.
- `cip == sayfa` **ONAYLANDI** ama "467==467" ifadesi yaniltici: asil olculen kusur **olu uc**,
  eski 20 oksuz cip -> **0**. Kalan 5 sapma (Lancer/Civic/Sprinter/Goldwing/V-Strom) YAPISAL ve
  ONCEDEN VARDI (eski kodda ayni siniftan 74 tane).
- Parite ANA CHECKOUT'tan, merge SONRASI: `parite-test.js` 1199 sorgu / `parite-ege.js` 846
  sorgu, aciklanamayan **0**. Kapilar CI'da gercekten kosuyor (3 `run:` satiri, `continue-on-error` YOK).
Kapilar: 20/20 · 122/122 · `ci-kapsam` 146 dosya · `is-akisi` 192 cagri, bulgu 0 ·
`kapi-envanteri` 7/7 · `kisisel-veri` 487 dosya · `gitignore` 311 dizin temiz ·
`d1-sync --durum` 17962 = 17962 uc eksen. Worktree + dal silindi, zombi birakilmadi.
OLCULEMEDI: `cip-indeks-test.py --mutasyon` (~1760 s, CI'da degil) yerelde kosulmadi.

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

### ✅ KAPANDI (4-5 Agu) — DORT DAL CANLIYA GITTI + YAYIN KILIDI ACILDI
- **`4a21466a`** kararsiz jeton SINIF 1: paketin varsayimi CURUTULDU (is tabanda zaten yapilmis;
  `GS` 13 urun, `T1`-`T6` hepsi yayinda, `Transporter` 143->143). Gercek boslukcuk **ciplak tek
  harf**: `BMW|k` ayri oksuz kova, esigi gectigi gun `/marka/bmw/k/` TEK HARFLI sayfa sessizce
  dogacakti. Canli: `/marka/bmw/k/` **404**, sitemap tek karakterli slug yalniz `renault/5`.
- **`455de764`** `ege-bilgi.md` l.44 hizalandi + kapiya `(E)` ekseni. **UC TUR curutme** (ayri
  dusman ajan; mutasyonu muhendis YAZMADI): tur-1 l.14 daralmasi canlida SATILAN STL/cizim
  kanalini reddettiriyordu (3/3 mutant yesil, hicbir kapi gormuyordu) · tur-2 yeni kanat 13 mesru
  cumlenin 8'ini kirmizi yakiyordu + `tanınmış`(=unlu) kelimesini negatif sayan REGEX HATASI ·
  tur-3 5 yeni nobetci KIRMIZI YANAMIYOR (bos iddia). Hepsi kapandi; canli drift kapandi
  (`ege-bilgi.md` 6531->6573 bayt, l.14 degismedi).
- **`8d5e3874`** marka invaryant kapisi + **D1 `marka_kanon` kolonu**. Kapi taban-civili CIRCIR
  (bugunku borc bloklamaz, ARTIS kirmizi yakar; **dusus de kirmizi** — mimar karari). Sema gocu
  7 adimda: ALTER -> `PRAGMA` dogrulama (27 kolon) -> senkron -> **canli 15.717 satir dolu**,
  128 kanonik deger, `Volvo Penta` -> `["Volvo"]`. Mutasyon 6/6, model canli ile 128/128 birebir.
- **`2d73448c`** Turkce I/i katlama kacagi (`NISSAN`/`MITSUBISHI`/`FIAT` esleşmeyi kaciriyordu,
  MaCiT canlida 2 KEZ gordu) + `.obj` olcumu + duvar-susu kapisi. Sisme **+7 / %0,043**
  (3.308.640 cift), gerileme 0, 7'sinin tamami dogru pozitif. Merge kapisi **IKI KEZ IADE ETTI**:
  once gevsetme fail-closed'i FAIL-OPEN yapmisti (15 sizinti: `Audi rings wall art` sinifi),
  sonra "75/75 kapandi" iddiasi CURUTULDU — batarya onarima gore yeniden yazilmis, kendi
  duzeltmesini olcuyordu ([[test-hatali-davranisi-kutsar]]). Gercek kalan kacak 20, canli 448
  baslikta insidans **0** -> kapatilmadi, **ILAN EDILDI + circir altina alindi** (batarya 220).
- **`c912548f` YAYIN KILIDI ACILDI (Okan karari).** `serit-a2`/Feed politika kapisi `61867dab`'dan
  beri kirmiziydi, `deploy` SKIPPED -> 9+ commit yayinlanmiyordu. Tek suclu ölçüldü (kontrol
  mutanti: urun cikinca rc=0, kalinca rc=1); Okan **katalogdan cikarma** dedi (metin gizleme ve
  taban'a borc yazma REDDEDILDI). Kosum `30948373105`: `serit-a2` failure->**success**,
  **`deploy` success**, **`yayin` success**. Canli: urun 404, Nissan 394->393.
  ⚠️ Toplu kosum rozeti `failure` GORUNUYOR ama yayin ACIK (`serit-b`+`ifsa-nobeti` `needs`'te YOK).
- **Shop deploy (Okan karari):** `12dca32f` -> `68b262a1`, bayatlik nabzi 183,5 dk -> **0 dk**.

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
1b. 🔴 **`ic-rapor-adi-kapisi.py` YANLIS AGACTA YESIL YAKIYOR** (merge kapisi olctu): koku
   `git rev-parse --show-toplevel` ile **cwd**'den turetiyor, ana checkout'tan kosunca dalin
   dosyalarini HIC gormuyor. Gercek bir sizintiyi (`d1-sync.py:585`) tam da bu yuzden kacirdi.
   CI'da bloklayici; ayni sinif baska kapilarda da olabilir, **kapi envanterini bu eksende tara.**
1c. `ifsa-nobeti` **dogdugu andan beri kirmizi** (164 muafiyet-disi isabet / 37 dosya, hepsi
   ONCEDEN VAR OLAN borc). Yayini BLOKLAMIYOR (`deploy: needs`'te yok). Karar bende: 164 satirin
   hangisi mesru hangisi gercek ifsa — `--muafiyet-hash`'i toptan kullanmak "kapiyi susturma"
   olur, tek tek yargi gerekiyor.
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

KAPANDI: 4 Agu marka-model uyeligi canli turu — dokum DEVAM-ARSIV.md de (git disi).

KAPANDI: odeme yolu bayatlik seridi — dokum DEVAM-ARSIV.md de (git disi).

### 🟡 ACIK KALEM 1 — kuyruk geri tepmesi OLCULEMEDI (48 saat sonra yeniden olculecek)
ACIK: ayrinti DEVAM-ARSIV.md de (git disi).

### ✅ KAPANDI (4 Agu) — guard, merge'in getirdigi katalogu dalin BAYAT haline geri sariyordu
Onarim main'de: merge SHA `0f8f5c01` (dal 2 commit, 5 dosya, +1276/-141; katalog dosyalari
diff'e GIRMEDI). Guard artik merge halini gorur: iki ebeveynden birinden gelen degisim
mesrudur; provenans cozulemedigi halde veriyi SESSIZCE degistirmek yerine commit'i
gerekceyle REDDEDER ve calisan cikis yollarini basar.
BAGIMSIZ OLCUM (curutucu): kabul testi **26 iddia / 0 kirmizi**, 5 kosumda ayni imza
(determinist); mutasyon bataryasi **16 mutant + kontrol mutanti (bos kume), SAPMA 0**,
TABAN_IDDIA 26, Traceback 0, izlenen 5 canli dosyanin sha256'si once=sonra AYNI.
Kabul testi artik yayini BLOKLAYAN seritte kosuyor (`build` isi, sayfa uretiminden ONCE;
yumusatma yok) — `is-akisi-kapisi.py` rc=0, olculen kapi cagrisi 192, serit tablosuna
giris EKLENMEDI (dosya dala hic dokunmadi); ayni agacta onceki commit rc=1 veriyordu.
Davranissal parite: urun partisi · merge (olay senaryosu) · rebase · amend · cakisma
cozumu — 5 akisin 5'inde onceki commit ile ayni rc + ayni katalog sha; atif/gorsel/
aciklama korundu. Yerel sure 2,6 s. Kapilar 8/8 rc=0. D1 teyidi 17914 = 17914 (uc eksen).

### ✅ KAPANDI (4 Agu) — kabul testi ortam degiskeni kirliligine kirilgandi
Onarim main'de: merge SHA `96069154` (dal 2 commit, 3 dosya, +275/-29; katalog dosyalari
diff'e GIRMEDI, sizinti taramasi 7 eksende 0). Kirli `GIT_*` mirasi altinda test artik
28 iddianin 28'inde YESIL (once tek basina `GIT_WORK_TREE` 23 iddiayi yanlis-pozitif
kirmizi yakiyordu). Ayrica X1'e POZITIF CAPA kondu: iz artik kendisiyle degil BEKLENEN
degerle (rc + katalog sha256 + geri-sarma bayragi) kiyaslaniyor, ustune POTENS kontrolu
(temizliksiz kosum SAPMALI) eklendi.
BAGIMSIZ OLCUM: temiz 28/0 · yedi kirli ortam kombinasyonunun (tek/ciftli/hepsi) her
birinde 28/0, Traceback 0 · determinizm 3/3 · CI taklidi (bos HOME, gitconfig kapali)
28/0 · mutasyon 22 mutant, SAPMA 0, kontrol mutanti BOS kume, TABAN_IDDIA 28, izlenen
5 dosyanin sha256'si once=sonra AYNI · olcumu bosaltan/daraltan/sabitleyen 4 mutant ve
BAGIMSIZ yazilan 4 curutucu (potens vakumu · guard cagrisinin uydurulmasi · fiksturun
kurcalamasinin kaldirilmasi · tautoloji capa + sabit iz) X1'i TEK BASINA kirmizi
yakiyor · genisletilen iki beyan (`{K1,X1}`, `{G1,X1}`) olculene TAM ESIT, hicbir beyan
DARALTILMADI · guard'in fonksiyon AST'si degismedi (16 fonksiyon, 0 fark; tek delta
modul aciklamasi) · kapilar 7/7 rc=0 · D1 uc eksen 17962 = 17962.
YAYIN: bu SHA'nin kendi kosumu eszamanlilik yuzunden IPTAL oldu (adim hic kosmadi);
merge'i ICEREN sonraki kosumda `build` isindeki provenans adimi FIILEN kostu ve
`success` verdi, `deploy` isi de basarili.

### 🟡 ACIK KALEM — korumanin tasinabilirligi (uc kalem)
(a) Koruma her ortamda ayni sekilde durdurmuyor (durum DEGISMEDI); ayrinti
DEVAM-ARSIV.md de (git disi). Ilgili dosya depoya girmedigi icin dal icinden
kapatilamaz — ayri tur gerekiyor.
(b) Kapi `pre-commit`/`pre-push` icinden cagrildiginda git kendi kancalarini
`GIT_DIR`/`GIT_INDEX_FILE` TANIMLI olarak kosar; yani (a) kapandiginda ortam kirliligi
GERCEK bir yol olur — bu tur tam o yolu kapatti, kayda gecsin.
(c) KAPANDI — ic isci-rapor protokol adina yapilan atiflarin hijyeni: asagidaki
"public depo hijyeni" kalemine bak (merge 20fbff61).

KAPANDI: nabiz nobetcisi A5 TESLIM ekseni — dokum DEVAM-ARSIV.md de (git disi).

## 🔴 YENI ACIK KALEM — A0 DAMGA alarmi kirmizi: D1 uzlastirici cron'u TESLIM ETMIYOR
ACIK: ayrinti DEVAM-ARSIV.md de (git disi).

KAPANDI: shop bayatlik fail-closed kanitlari — dokum DEVAM-ARSIV.md de (git disi).

## 🔴 YENI ACIK KALEM — katalog geneli metin/alan bosluğu (envanter cikti)
ACIK: ayrinti DEVAM-ARSIV.md de (git disi).

ACIK KALEM: yayin hatti icerik denetimi — dokum DEVAM-ARSIV.md de (git disi).

## 🟡 YENI ACIK KALEM — `CLAUDE.md`/`AGENTS.md` git disi symlink
ACIK KALEM: symlink surumleme ayrintisi — dokum DEVAM-ARSIV.md de (git disi).

## ✅ KAPANDI — public depo hijyeni: ic surec dosyasi adina yorum atiflari (merge `20fbff61`)
Izlenen dosyalarda ic isci-rapor protokol adina YORUM/DOCSTRING metni olarak yapilan
atiflar notrlestirildi; tekrarini engelleyen nobetci `tools/ic-rapor-adi-kapisi.py`
CI'da (`serit-a3`, `deploy: needs` listesinde) BLOKLAYICI kosuyor.
BAGIMSIZ OLCUM (curutucu): dal oncesi 55 vurus / 27 dosya · dal sonrasi muaf 31 vurus /
7 dosya · temizlenen 24 satir / 20 dosya (55 − 31 = 24, aritmetik TUTUYOR; iscinin
beyaniyla TAM ESIT). Oldurucu: temizlenmis dosyaya desen geri konunca TEK KIRMIZI,
dogru dosya:satir basildi. Kontrol: benzer ama kapsam disi 4 metin YESIL (yanlis
pozitif yok). Muafiyet ICERIK-hash'ine bagli dogrulandi — kayitli satirin metni
degisince VE ayni satir baska dosyaya kopyalaninca muafiyet DUSTU, ikisinde de kirmizi;
yol-bazli genel kacis DEGIL. Determinizm 3/3 ayni, sure 0,24 sn, sig checkout'ta
calisiyor (489 dosya). Mutasyon: 2 mutantin her biri IDDIA kumesinde TEK KIRMIZI,
Traceback 0, iddia sayisi 2→2 sabit, canli dosya sha256 once=sonra AYNI.
Kod davranisi DEGISMEDI: 14 `.py`de docstring-normalize AST 0 fark (ham AST'de 12
dosyada fark → edit gercekten docstring icinde), 4 JS/MJS `node --check` rc=0.
Kapilar rc=0: is-akisi · ci-kapsam (+kendini-test) · kapi-envanteri 7/7 · kisisel-veri ·
urunler-guard-provenans 28/0 · mukerrer-kontrol · duzelt-toplu. Katalog dosyalari
kapsam DISI (push oncesi `origin/main..HEAD` urun diffi BOS). D1 uc eksen 18008 = 18008.

MUAFIYET HUKMU (mimar karari icin): 31 muaf vurusun 30'u MESRU — `tools/durum.py` (2)
protokol adini fiilen arayan kod + ona bagli print etiketi; `tools/kisisel-veri-test.py`
(22) kardes sizinti nobetcisinin KENDI kirmizi/yesil fikstur ve hata-mesaji verisi;
`tools/paket-*.md` (6 satir / 4 dosya) delegasyon spec'lerinin TESLIM talimatinin
kendisi ("bu ad ZORUNLU", "baska ad YASAK") — metnin KENDISI mekanizma oldugu icin
genellestirilirse spec islevini yitirir, `durum.py` ile ayni gerekce sinifinda.
1 KACI: `tools/olculmemis-siparis-test.py` (1) — bir `print()` etiketi; "calisan kod,
yorum degil" ayrimi bicimsel, hicbir test bu dizgeye dayanmiyor, genellestirilmesinin
davranissal maliyeti SIFIR. Ayri turde kapatilabilir (muafiyet govdesinden cikarilir).
ARTIK POZ (daha genis eksen, bu dalin isi DEGIL): `tools/paket-*.md` delegasyon
spec'lerinin PUBLIC depoda DURUYOR olmasi, ic surec gorunurlugu acisindan dosya
adindan daha buyuk bir yuzey — ayri karar (Okan/mimar).
BILINEN KOR NOKTA: olculdu ve dar kapsamli, kardes nobetcinin ayni desenli istisnasiyla
tutarli; dokum DEVAM-ARSIV.md de (git disi). Kapatilmasi istenirse ayri tur.

YAYIN: bu SHA'nin kosumunda (id 30929902990) yeni IKI adim FIILEN kostu ve `success`
verdi (`5/5 gecti` + `temiz (0 muafiyet-disi isabet)`). Kosum yine de KIRMIZI, `deploy`
SKIPPED — sebep BASKA ve ONCEDEN VAR: `devam-sinif-kapisi` (serit-a2 + serit-a3), ayni
iki adim `dced48ce`/`f8698ebe`/`31769d88` kosumlarinda da kirmiziydi, yani dal ONCESI.
Dal DEVAM ile ilgili hicbir dosyaya dokunmadi. Baska bir oturum `8073ea6f` ile ihlalleri
arsivledi; kapi yerelde artik YESIL (0 sinif ihlali) — sonraki kosumda yayin beklenir.

## ✅ KAPANDI — numune-olmadan sayfasindaki KOSULSUZ uretim vaadi kapasite sinirina baglandi (merge `6f7ac890`)
Canli ve indeksli SEO sayfasi `/numune-olmadan-plastik-parca-yaptirilir-mi/` govdesindeki tek
`<p>`, bot tarafinda bugun kapatilan ayni kuralla hizalandi: marka/model/yildan taniniyorsa akis
surer; taninamiyorsa VE elde numune de yoksa net sinir ("tahminle uretim yapmayiz, once yeterli
referans isteriz"). Sayfa yayinda kaldi, yalniz metin duzeltildi.
KAPSAM (merge-base `f8698ebe`'ten olculdu, `main..HEAD` DEGIL): 1 dosya `tools/sayfalar.py`,
+1/-1 satir. Push oncesi `origin/main..HEAD` net farki da ayni tek dosya/tek satir — baskasinin
isi geri alinmadi. Cakisma on-testi temiz (`merge-tree` yalniz agac OID'i bastı). Public-depo
metin taramasi (dalin ekledigi satirlar): desen vurusu 0.
KAPILAR (dalin KENDI agacinda, izole klonda, exit kodlari goruldu): build ONCESI **15/15 YESIL**
— kisisel-veri · odeme-beyani · landing-hukuk · malzeme-dayanak · ege-kabiliyet (+`--ic-nobetci`) ·
fiziksel-urun · cayma-beyani · yayin-ic-dil `--kaynak` · devam-sinif · yasal-sayfa-drift · is-akisi ·
onizleme-vaat · gramer-artigi · iki-govde. Build SONRASI **4/4 YESIL** — `build.py` · yayin-ic-dil ·
uretim-butunluk · enjeksiyon. `gitignore-kapisi` TEMIZ (311 uretilen dizin). `kapi-envanteri` 7/7.
DEVRALINAN KIRMIZI TARIHLE COZULDU (baseline diye gecilmedi): ilk turda `devam-sinif-kapisi`
KIRMIZI idi (`DEVAM.md:26` E3 + `DEVAM.md:41` E5). Dalin sucu DEGIL — DEVAM.md blob'u dalda,
main'de ve merge-base'te BIREBIR ayni (`4f68c5be`). Baska bir oturum `8073ea6f` ile ihlalleri
arsivleyince guncel tabanda kapi **0 sinif ihlali** ile yesile dondu.
URETILEN HTML: yeni cumle **1**, eski cumle **0**; govde bag sayisi degismedi (duzenlenen
paragrafta oncesinde de sonrasinda da 1 bag).
D1 UC EKSEN: **18008 = 18008** · sema goc indeksleri KURULU · `urun_hash` uyusmazlik 0 / eksik 0 /
fazla 0.
CANLI (canonical, cache-bust'SIZ): HTTP **200** · yeni cumle **1** · eski cumle **0**.
Kosum `30931519589` headSha **BIREBIR** `6f7ac890`, conclusion **success**; 11 isten `build`,
`deploy` ve `yayin` UCU de success (`--limit 1` yesiline guvenilmedi — bir onceki main kosumu
`cancelled` idi). Push bir kez non-fast-forward reddedildi (main arada iki kez ilerledi);
`--force` KULLANILMADI, fetch + merge ile tekrarlandi. Gecici klon ve iki yerel dal silindi.

## ✅ KAPANDI — git kanca kablolamasi depoya alindi (merge `2a49b8b1`)
Kanca kablolama dali taze main'e alindi: mutlak-yol kurulum betigi, fail-closed bayat/golge
tespiti, post-merge/post-checkout otomatik tazeleme; kablolama nobetcisi deploy.yml serit-a3'te
bloklayici; is-akisi kapisina beyan/gercek ayrisma ekseni (Bolum F).
KAPSAM taze main'den olculdu (merge-base `8d5e3874`, `main..HEAD` DEGIL): 13 dosya, +3185/-2 —
hicbir urun-veri dosyasi YOK. Cakisma on-testi temiz (merge-tree yalniz agac OID bastı).
DALIN TESTLERI izole worktree'de, exit kodlari goruldu: is-akisi rc0 · is-akisi `--kendini-test`
173 iddia rc0 · nobetci `--ci` rc0 (18 eksen: 16 yesil / 0 kirmizi / 2 olculemedi — kurulum
yapilmadigi icin) · kanca-kablolama-test 62 iddia rc0. (`--kendini-test` bayragi is-akisi-kapisi'nda,
nobetci'de degil.)
MERGE URUN-VERI TEMIZ: `c912548f..2a49b8b1` urun-veri farki BOS (arada bir baska oturum urun
commit'i `c912548f` main'e girdi; merge onun uzerine SIFIR urun-veri ekledi).
Merge git-yerel kanca kurulumunu TETIKLEMEDI — konfigurasyon merge oncesiyle ayni (dogrulandi).
Push tamamlandi (istemci 2 dk'da
timeout etti ama pre-push kacak taramasi 0 bulgu + ref transfer oldu); merge origin/main'in ATASI
(dogrulandi). Uzerine baska oturum urun partisi `d72fc2a9` commit'ledi. Deploy kosumu id
`30948373105` (headSha `d72fc2a9`, merge ATA — dogrulandi); CI WATCH KURULMADI. Dal worktree'si +
yerel dal silindi.

UC OKAN KAPISI (acik):
(a) `kanca-kur.py` Okan tarafindan AYRICA kosulmali — kosulana kadar git-native koruma bu makinede
AKTIF DEGIL (merge yalniz dosyalari aldi, kurulumu tetiklemez).
(b) CLAUDE.md'deki "hook'lar commit EDILMEZ" cumlesi (yaklasik satir 86) artik yanlis — kancalar
artik izlenen dosya; elle guncellenmeli.
(c) Kapak thumbnail uretim blogu (pre-push) `pagespeed-thumb-fix` dali ile sira koordinasyonu
gerektirir — ayni yuzeye dokunuyorlar.

GOZLEM (bu dalin isi DEGIL, notr): merge sonrasi D1 durum drift gosterdi (D1 sayisi urunler.json'dan
88 geride + 1 fazla) — urun partisi `d72fc2a9`'un senkronu tamamlanmamis. Urun-veri tek-yazar alani;
merge iscisi COZMEDI, urun oturumuna birakildi.
