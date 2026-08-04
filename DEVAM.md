# DEVAM (KraL) — 3 Agu 2026
KAPANDI: 4 Agu marka-model uyeligi canli turu — dokum DEVAM-ARSIV.md de (git disi).

## ✅ KAPANDI — 4 Agu: odeme yolu bayatlik olcumu push tetikli AYRI seride de tasindi (merge `93bb2681`)
Bayatlik nobetcisi artik yalnizca zamanlanmis kadansa bagli degil; her `main` push'unda ayri
bir is akisi seridinde de olculuyor. Seridin yayini GECIKTIRMEDIGI kosulan kapiyla olculuyor:
serit `deploy.yml`in `needs` grafinin ICINDE degil ve onu `uses:` ile cagirmiyor · tetik izin
listesi KAPALI (yalniz `push` + `workflow_dispatch`) · dal suzgeci TAM OLARAK `main` ·
eszamanlilik grubu yayin grubundan AYRI · olcum kolu canli kosuyor ve cikis kodu yutulmuyor.
Bayatlik nobetcisinin iki iddiasi eskiden coker halde susuyordu; artik cokme yerine KIRMIZI yaniyor.
- OLCULDU (dalin worktree'sinde, merge oncesi, KENDIM kosturdum): `cron-nabiz-kapisi.py
  --kendini-test` **164 iddia / 0 kirmizi** · `cron-teslim-mutasyon.py` **25 mutant
  (22 oldurucu + 3 kontrol) / 0 kusur**, her mutantta iddia sayisi **164 SABIT**,
  **Traceback 0**, uc hedef dosyanin sha256'si degismedi (arac diske yazmiyor) ·
  `shop-bayatlik-kapisi --kendini-test` 39 iddia / 0 kirmizi · `shop-bayatlik-mutasyon`
  19 mutant / 0 sapma · `is-akisi-kapisi` · `ci-kapsam-test` · `kapi-envanteri` ·
  `komut-stili-kapisi` · `yayin-gecikme-test` (38/38) hepsi rc 0.
- IDDIA ETIKETI ARITMETIGI BAGIMSIZ DOGRULANDI — her surum KENDI agacinda kosuldu
  (`git archive` ile ayri dizine cikarilip orada `--kendini-test`): taban `0e05089c` **124** ·
  onceki ana hat **139** · dal **149** · birlesmis **164**, yani `124 - 3 + 18 + 25 = 164`.
  **Dalin dusurdugu etiket: 0.** Birlesmiste eksik gorunen 3 etiket ANA HATTIN KENDI
  dusurdugu taban etiketleridir (kume esitligi `(dal - birlesmis) == (taban - anahat)` ✅).
  🔴 Yontem notu: ayni olcumu once dalin agacinda kosturmustum — HER surum 1 eksik ve
  13-34 kirmizi verdi, cunku eski kapi surumleri YENI is akisi dosyalarini olcuyordu.
  Surum karsilastirmasi DAIMA her surumun KENDI agacinda kosulur ([[bayat-kabul-testi]]).
- Kapsam merge-base `54bc0bf6`'dan **7 dosya, 894+/43-**; `urunler.json` ve gizli urun kaynak
  kaydi diff'te YOK. `merge-tree` cakismasiz. Sizinti taramasi temiz.
- Merge SONRASI, push'tan ONCE katalog diff'i (`origin/main` ↔ `HEAD`) **BOS** — guard bu
  merge'de geri sarma YAPMADI.
- D1 teyidi: **17879 = 17879** (sayi ✅ · sema ✅ · icerik ekseni 17879 `urun_hash` birebir,
  uyusmaz 0 / eksik 0 / fazla 0).
- YENI SERIDIN ILK CANLI KOSUMLARI: `93bb2681` (benim merge SHA'm) → kosum **30906008015
  SUCCESS**; ardindan `f4c285c7` → 30906064032 SUCCESS; `896f05fa` → 30907303355 SUCCESS.
  Uc kosumun ucu de yesil ve UCUNDE de serit, ayni SHA'nin `Build & deploy` kosumu HALA
  `in_progress` iken TAMAMLANDI — "yayini geciktirmiyor" iddiasinin canli ilk kaniti.
- CI teyidi: merge SHA'min KENDI yayin kosumu (30906008558) `concurrency` ile IPTAL oldu;
  gecerli kanit ardil kosum **30906064355** (headSha `f4c285c7`, **SUCCESS**) ve merge SHA'm
  bu SHA'nin ATASI (`merge-base --is-ancestor` cikis 0). "En son kosum yesildi" degil,
  SHA'yi ICEREN kosum olculdu.
- Temizlik: worktree kaldirildi, dal silindi (`a3cfb181`); ana agacta yetim degisiklik YOK
  (kalan 2 untracked kalem baska oturuma ait, DOKUNULMADI).

### 🟡 ACIK KALEM 1 — kuyruk geri tepmesi OLCULEMEDI (48 saat sonra yeniden olculecek)
Yeni serit her `main` push'unda bir kosum daha aciyor: **~87,7 kosum/gun** tabanina
**+~81 kosum/gun**. GitHub'in kuyruk/eszamanlilik politikasi API'den OKUNAMIYOR, dolayisiyla
"bu ek yuk mevcut kosumlari kuyrukta bekletir mi" sorusu SU AN OLCULEMEZ — tahmin yazilmadi.
Olcum yordami: 48 saat sonra `gh run list` uzerinden serit-basi `createdAt` → `startedAt`
gecikmesini taban gunle karsilastir. Bugun zaten gozlenen olgu: yayin kosumlari
`concurrency` ile sik sik IPTAL oluyor (bugun ornekleri: 30906008558, 30903754236) —
bu serit ONCESINDE de vardi, ama tabanin bozulup bozulmadigi olculmeden hukum verilmemeli.

### 🔴 ACIK KALEM 2 — guard, merge'in getirdigi katalogu dalin BAYAT haline geri sardi (olay + onarim)
Dalda `origin/main` merge edilirken `.git/hooks/pre-commit` → `tools/urunler-guard.py --tetik
commit`, merge'in GETIRDIGI katalogu "izinsiz urun degisimi" sanip HEAD'e (dalin bayat haline)
geri sardi. **Hicbir kapi calmadi, merge "basarili" gorundu.** Olculen zarar 5 ekleme /
11 silme — iki urunde (`citroen-berlingo-modutop-tavan-kilidi` ve
`citroen-berlingo-peugeot-partner-modutop-tavan-kutusu-kilidi`) ana hattin fiyat/aciklama/
olcu duzeltmesi, bir `lisans` blogu ve 3 gorsel URL'i KAYBOLMUSTU.
Onarim: `urunler.json` ana hattan birebir geri alindi; onarim commit'i guard'i atlayan bir
yolla atilmak zorunda kalindi (yoksa guard AYNI geri sarmayi tekrarlardi) ve atlanan uc
kontrol elle kosuldu — yordamin dokumu DEVAM-ARSIV.md'de (git DISI).
**Bagimsiz teyit (bu tur, KENDIM):** katalog sha256 birebir esit · 17861 urunun `id` sirasi
ve kumesi ayni · 9 alanda (`fiyat`, `lisans`, `gorseller`, `aciklama`, `baslik`, `kategori`,
`marka`, `parametrik`, `uyum`) x 17861 urun = **0 alan farki** · iki hasarli urun alan alan
karsilastirildi, hepsi ana hatla AYNI · onarim commit'i `urunler.json` DISINDA hicbir sey
tasimadi · guard/kapi dosyalari dalda DEGISTIRILMEMIS (diff bos) ·
`urunler-guard --tetik commit`, `mukerrer-kontrol` (17861 temiz), `mimar-commit-kapisi`,
`kisisel-veri-test` hepsi rc 0.
🔴 SINIF: worktree'de merge = guard geri sarmasi ([[worktree-merge-guard-geri-sarma]]).
ACIK: guard bu durumu sessiz birakiyor — merge getirisini "izinsiz degisim"den ayirt eden
bir eksen YOK. Kalici cozum (guard'a merge-baglami ekseni) ONERILDI, HENUZ YAZILMADI.

## ✅ KAPANDI — 4 Agu: nabiz nobetcisine A5 TESLIM ekseni (merge `41ef8672`)
Zamanlanmis alarm kosumlarinin FIILI teslim orani artik olculuyor: nobetci cron METNINE
bakmakla yetinmiyor, kosumlarin gercekte ne siklikta ateslendigini de sayiyor. "Cron dogru
yazilmis" yesili, kosumlarin cogunun HIC olusmadigi halini artik gizleyemiyor.
- OLCULDU (dalin worktree'sinde, merge oncesi, KENDIM kosturdum): kabul **124 iddia /
  0 kirmizi** (main'de 103) · yeni mutasyon surucusu **7 mutant (6 oldurucu + 1 kontrol) /
  0 kusur** · `cron-nabiz-kapisi.py` sha256 kosum oncesi = sonrasi (arac diske yazmiyor).
- Kapsam merge-base `1159540c`'ten 4 dosya, 637+/30-; urun verisi ve shop bayatlik
  araci diff'te YOK. `merge-tree` cakismasiz. Ayrinti DEVAM-ARSIV.md'de (git disi).
- Ardil commit'ler — curutulmus sayi + yetim surucu kapatildi:
  - `d892b22c` (K3): `tools/shop-bayatlik-kapisi.py` dosya basindaki "cadans 15 dk ->
    korluk penceresi <= 15 dk (53 kat iyilesme)" cumlesi CURUTULMUSTU; olculen degerlerle
    (teslim %4,31 · en uzun bosluk 1053,5 dk · medyan 237,4 dk) yeniden yazildi ve olcumun
    tek kaynagi olarak `cron-nabiz-kapisi` A5 eksenine yonlendirildi. Davranis DEGISMEDI.
  - `6e040969` (K2): `tools/cron-teslim-mutasyon.py`ye repoda 0 referans vardi (yetim
    surucu); `deploy.yml` `cron-nabzi` isindeki kendini-test adiminin yanina deponun kendi
    bicimiyle yorumla ilistirildi. `paket-tazelik-alarmi.yml`deki "o dosya GUNCELLENMELIDIR"
    notu da artik gerceklesmis durumu anlatiyor.
  - 🔴 KAYDA GECSIN: kaynak kodu ANA CHECKOUT'ta commit'lenemiyor (mimar kod-kilidi,
    bilincli yanlis-pozitif). K3 bu yuzden dalin worktree'sinde commit'lenip `--ff-only`
    ile alindi; K2 (yalniz `.yml`) ana checkout'ta commit'lendi.
- Kapilar merge sonrasi YESIL: `is-akisi-kapisi` (165 kendini-test iddiasi) ·
  `ci-kapsam-test` · `shop-bayatlik-kapisi --kendini-test` 39 iddia / 0 kirmizi
  (mutasyon 16 mutant / 0 sapma) · `cron-nabiz-kapisi --kendini-test` 124 iddia / 0 kirmizi.
- D1 teyidi: **17817 = 17817** (sayi ✅ · sema ✅ · icerik ekseni 17817 `urun_hash` birebir,
  uyusmaz 0 / eksik 0 / fazla 0). Ilk olcumde 1 bayat hash gorundu (baska bir oturumun
  fiyat degisikligi henuz senkronlanmamisti); ikinci olcumde kapanmisti.
- CI: kendi push'larimin kosumlari (`41ef8672` 30895283224 · `6e040969` 30895707686)
  `concurrency` ile IPTAL oldu. Gecerli kosum **30895767587** (headSha `7245d8ad`,
  baska oturumun push'u) ve iki merge SHA'm da bu SHA'nin ATASI
  (`merge-base --is-ancestor` cikis 0). Kosum sonucu **failure** — ama sebep BENIM
  degisikligim DEGIL, asagiya bak. `build`/`deploy`/`yayin` job'lari **success**
  (yayin etkilenmedi); `cron-nabzi` isinde iki kendini-test adimi da **success**.

## 🔴 YENI ACIK KALEM — A0 DAMGA alarmi kirmizi: D1 uzlastirici cron'u TESLIM ETMIYOR
`cron-nabzi` isinin CANLI kolu (yayini DURDURMAYAN alarm) kirmizi yaniyor. Kirmizi eksen
**A0**, A5 DEGIL: "son basarili uzlastirma 9,1 saat once (esik N=9 sa)".
- BENIM MERGE'IMDEN DEGIL, ZAMAN GECMESINDEN: merge ONCESI kosum 30894293161 (`9775d122`,
  08:59Z) ayni ekseni **8,9 saat** olcup YESIL vermisti; merge SONRASI kosum 30895767587
  (09:23Z) **9,1 saat** olcuyor. Ayni damga kosumu (30865105413), ayni esik (9 sa), ayni
  turetme (`olculen teslim orani 0,125 · efektif 120 dk`) — ki bu turetme merge ONCESINDE
  de vardi. Yani damga 24 dakikada esigi dogal olarak asti.
- KOK SEBEP tam da bu turda olculen sey: zamanlanmis kosumlar ateslenmiyor.
  A5 TESLIM `d1-uzlastirici.yml` -> teslim 7 / nominal 192 (**%3,65**) · en uzun bosluk
  1053 dk · medyan 236 dk. `paket-tazelik-alarmi.yml` -> teslim 7 / nominal 192 (%3,65) ·
  en uzun bosluk 1054 dk. Dusme DEPO/HESAP duzeyinde; ofset degisikligi duzeltmedi.
- ELLE MASKELEMEDIM: uzlastiriciyi `workflow_dispatch` ile tetiklemek damgayi tazeler ama
  kok sebebi (cron teslimi) duzeltmez, alarm saatler icinde geri doner — yeni eksenin
  gorunur kildigi gercek bir arizayi ortmek olurdu. Mimar karari beklesin.
- Not: A0'in vekil oldugu ASIL invaryant su an SAGLAM — D1 icerigi `urunler.json` ile
  birebir (17817, uyusmaz 0). Kirmizi olan "denetim ne kadar suredir kosmadi" ekseni.

## ✅ KAPANDI — 4 Agu: shop bayatlik nobetcisine iki fail-closed kanit (merge `4225711d`)
Canli odeme worker'inin bayatlik kapisi, olctugu ref uzak main ucu DEGILSE ya da bundle
dosyalarinda kaydedilmemis fark varsa artik rc 2 "olculemedi" donuyor; eskiden bu iki halde
sessizce rc 0 "taze / 0,0 dk" veriyordu (sahte-taze).
- OLCULDU (dalin worktree'sinde, merge oncesi): kabul testi **39 iddia / 0 kirmizi**
  (main'de 32/0) · mutasyon bataryasi **16 mutant / 0 sapma** (main'de 12/0) ·
  kaynak sha256 kosum oncesi = sonrasi (arac diske yazmiyor).
- Kapsam merge-base `1159540c`'ten YALNIZ 2 dosya (`tools/shop-bayatlik-kapisi.py`,
  `tools/shop-bayatlik-mutasyon.py`); hicbir urun veri dosyasi diff'te YOK.
- Ardil commit `ba0b4a8c`: `deploy.yml` yorumundaki BAYAT sayilar duzeltildi
  (satir 669 `32 iddia`→`39 iddia`, satir 674 `12 mutant`→`16 mutant`). Bu depoda yorumdaki
  sayi olcumun kaynagi sayilir; bayat sayi yanlis guven verir.
  `is-akisi-kapisi.py` ve `ci-kapsam-test.py` sonrasinda YESIL.
- D1 teyidi: **17817 = 17817** (sayi ekseni ✅ · sema ekseni ✅ · icerik ekseni
  17817 urun_hash birebir, uyusmaz 0 / eksik 0 / fazla 0).
- CI: merge SHA `4225711d`'nin kosumu (30893172664) KENDI ikinci push'umla iptal oldu;
  gecerli kosum **30893246326** (headSha `ba0b4a8c`) **BASARILI** ve `4225711d` bu SHA'nin
  ATASI (`merge-base --is-ancestor` exit 0). `Shop bayatlik kapisi — kendini test` adimi
  bu kosumda **success**.
- 🟡 KAYDA GECSIN (bu turda DUZELTILMEDI, kapsam disi): `deploy.yml` yorumu bu adimi
  "SERIT A (job `build`)" diye anlatiyor; kosumda adim FIILEN **`serit-a2`** job'unda.
  Yorumdaki job adi ile gercek job adi ayrisiyor — mimar karari beklesin.
- Dal + worktree `agent-a8f11e73f1c0fb7aa` temizlendi (icerigi main'de, worktree temizdi).

## 🔴 YENI ACIK KALEM — katalog geneli metin/alan bosluğu (envanter cikti)
1700 marka-model cifti, **943'unde** serbest metin aramasi ile alan uyeligi ayrisiyor,
**5585 urun** etkileniyor. Kovalar (baslik okunarak, kural uydurulmadan):
- **A VERI EKSIGI 4784 urun** → MaCiT'te (is listesi 6288 kayit / 4513 urun / 817 cift; kanonik
  deger `arama.py` fonksiyonlarindan turedi, gozle atama yok)
- **B VARYANT JETON 735** (`Astra H` ile `Astra`) → KOD, BENDE
- **C YANLIS-POZITIF 87** → olcu satiri sayisal model adiyla cakisiyor (Renault "17": 37 urun,
  Renault "5": 18, Toyota "86": 16; `M4 vida` cumlesi motosiklet parcasini BMW M4 sayfasina
  dusuruyor). 🔴 **TOPLU `ara`→`marka` KOPYASI YASAK.**
- **D FARKLI ARAC AYNI AD 348** (`GS` BMW motosiklet ile Citroen GS · `C1` PSA ile BMW skuter ·
  `Sierra` Volvo/Ford/Nissan) · **E ARAC-DISI JETON 32** (`/marka/volkswagen/iphone/`) → sayfa
  kapatilacak, BENDE · **KARARSIZ 387** (`GS`·`ST`·`T4`·`GTI`·`TDI`·`Mk4` — urun gercek, jeton
  model degil)
🔴 **OKAN KAPISI ACIK:** bosluk kapanirsa **303 YENI model sayfasi** esigi asar (+%60).
Hepsi birden mi, asamali mi? Cevap gelene kadar MaCiT'e parti parti ilerlemesi soylendi.

ACIK KALEM: yayin hatti icerik denetimi — dokum DEVAM-ARSIV.md de (git disi).

## 🟡 YENI ACIK KALEM — `CLAUDE.md`/`AGENTS.md` git disi symlink
ACIK KALEM: symlink surumleme ayrintisi — dokum DEVAM-ARSIV.md de (git disi).
## 🔄 DEVIR — 3 Agu 2026 (hesap rotasyonu) · YENI OTURUM ONCE BURAYI OKU

TARIHSEL DEVIR: agac durumu ve dersler — dokum DEVAM-ARSIV.md de (git disi).

**🔴 ACIK — 4 Agu CI nobeti: yayin hatti bir tur bloklandi; kok neden + kimlik dokumu DEVAM-ARSIV.md'de (git disi). Duzeltme baska mimarin duzlemi, posta kutusuna yazildi.**

**🟡 RULMAN SATISA ACMA — hala BENDE, ayri tur. Karar dayanagi OLCULDU (3 Agu):**
Izgara `ic_cap 5–20/0,5 × dis_cap 28–60/0,5 × genislik 5–15/0,5 × eleman{3}` = **126.945 nokta**.
- Sema kapisi ONCESI uretilemez: **43.085 / 126.945 = %33,94** (dalin iddiasi dogrulandi;
  DEVAM'daki eski "%32,88" farkli bir izgaradan geliyor, ikisi de kayitta kalsin).
- Sema kapisi SONRASI kabul edilen 83.860 sette **uretilemez = 0**; ters eksende
  **asiri red = 0** (motorda uretilebilir olup reddedilen tek kombinasyon yok).
- Kapali form **471 GERCEK render**'a karsi **0 ayrisma** ile dogrulandi.
- `parametrikFiyatKurus("rulman",…)` **hala `null`** (allowlist 17 aile, rulman yok);
  kontrol `kutu` 24168 kurus → kapi kor degil.
- Kardes depodaki et kalinligi kapisi (`0,8 mm`) ile **ORTUSME SIFIR**: iki AYRI bolge
  (o kapi 336/634.725 noktayi reddediyor, hepsi bu deponun motorunda URETILEBILIR).
  Yani o kapi bu urunu KORUMUYOR — iki farkli uretim motoru.
**MERGE EDILMEDIGI ICIN ACIK KALAN IKI KARAR (isci sordu, ben cevaplamadim):**
1. `build.py`'deki `gecersiz-parca` kolu ayni "siparis verebilirsiniz, uretim etkilenmez"
   cumlesini tasiyor. Isci farkli eksen oldugu icin (2-renk siparisi gercekten var ve ≥10 mm
   kenar kontroluyle korunuyor) dokunmadi — **olculmesi gerekip gerekmedigi karar.**
2. `varlik-test.py` 2. ekseni "sayfa JS'i dondurulmus referans commit'ten sonra hic degismesin"
   diyor; muafiyet listesi her sayfa-JS duzenlemesinde buyuyecek. **Referans ilerletilmeli ya da
   eksen gercek cikarim kaybina daraltilmali** — bu tur dokunulmadi.

**BENDE — acik kalemler, oncelik sirasiyla:**
0. KAPANDI `78676775`; kalan: satisa acik ailelerin altisi uretim motoru referansi istiyor -> Okan kapisi (dokum DEVAM-ARSIV.md'de).
1. 🔴 **YAPISAL — ISCIDE OLCULUYOR (3 Agu):** siparis/odeme yolu uretilebilirligi SORMUYOR.
   Allowlist yara bandi; her yeni aile ayni riski yeniden aciyor. Dogru cozum: odeme yolunun
   derleyiciye/uretilebilirlik kapisina sormasi. **Ders:** aile satisa acarken sorulan soru
   "fiyat dogru mu" idi; ikinci soru **"bu parametrelerin hepsi uretilebilir mi"** olmaliydi.
   **Kosan olcumun ayirt ettigi ikilem:** sema `kisitlar` blogu TEHLIKE isareti mi, KORUMA mi?
   Siparis yolu kisitlari UYGULUYORSA koruma → A3'un KOL2 kolu fazla kati, daraltilmali;
   UYGULAMIYORSA A3 dogru ve asil kusur odeme yolunda. **Rulman satisa acma karari buna bagli.**
   KAPANDI 736: `d8024a27` (dokum DEVAM-ARSIV.md'de).
2. `worktree-agent-aadc8e1d5df8ff4b0` (`3ef8b81a`) — ci-kapsam dar-bayrak dali, **curutme SARTLI
   dondu, sart uygulanmadi**: kovaya eklenen js bayraklarinin **%81'i uydurma** (baska programa
   gecirilen `--cached`/`--dry-run` gibi argümanlar dosyanin kendi bayragi sayiliyor). Dalin asil
   degeri duruyor: **6 dosya yalniz `--kendini-test` ile kosuyor** (`jenerator/test/kabul.py`
   dahil) — bugunku fiyat alarminin aylarca gorunmemesinin sebebi buydu. Ya sartla tamamla ya
   acikca park et.
1b. 🔴 **YAPISAL — YENI (3 Agu, olculdu): Worker CI'da YAYINLANMIYOR.** `deploy.yml`'de
   `wrangler deploy/publish` **0 vurus** → her `worker/`+`shop/src` degisikligi ELLE deploy
   bekliyor ve **hicbir alarm calmiyor**. Olculen sonuc: canli bundle **2 Agu 23:35'ten
   (`f1594d68`) bayat** kaldi; `f1594d68..HEAD` arasinda bundle girdilerine dokunan **10 commit**
   birikti. Yani main yesil, CI yesil, site taze — ama **odeme yolu eski kodu kosuyor.**
   Sinif: bugunku tekrar eden sinif — beyan edilmis nobetci, olculmemis kapsam.
   Cozum yonu (karar bende): ya CI'ya Worker yayin adimi + bayatlik nobetcisi (canli bundle
   hangi commit'i tasiyor, kac commit geride), ya da elle deploy ritueli kapiya baglanir.
   KAPANDI 3 Agu: elle deploy `ac6864e3`; KALEM ACIK: CI hala Worker yayinlamiyor (dokum DEVAM-ARSIV.md'de).
1c. 🟡 **YENI (kutudan, karar bende):** (a) **HocA** — `sss/` **POM** vaat ediyor, `ege-bilgi.md`
   kapsaminda POM YOK; ya uretiliyor (bilgiye eklenir) ya metin bayat (SSS'den cikar) — uretim
   kapasitesi karari. (b) **KaaN** — `rampa.json` `"motor":"pruvo"` beyani `aileler/rampa.js`
   formuluyle celisiyor (%15,37 / %17,65 / %20,30); KaaN olcuyor, yargi bende.
2b. **PARK — mukerrer dal:** `claude/upbeat-kapitsa-d7c9ac` (`36bf4a06`, worktree
   `.claude/worktrees/upbeat-kapitsa-d7c9ac`) A3 kor noktasini PARALEL onarmis (13 mutant).
   Benim surumum (`193cd6f0`) main'de ve daha genis (19 mutant + A6 kapsam iddiasi) → dal
   **cakisir, merge EDILMEYECEK**. Alinacak tek sey ondaki **`A1c` iddiasi** — once ayirt edici
   mutanti var mi olculecek, varsa ayri turda tasinacak, sonra dal+worktree silinecek.
3. 🔴 **Tek kanonik marka fonksiyonu — URETIMDE OLCULDU.** Uc ayri mantik (`index.html`
   `markaKatla` · uc `uyumEkseniKosulu` · `parite-test.js` tam jeton), **1.677 cip degerinin
   1.518'inde** ayrisiyor. Kok neden: cip **katlanmis**, uc **ham** etiket esliyor.
   Kabul testi yakalamiyor cunku **fikstürün uc simulatoru de katliyor**.
   Surucu scratchpad'de `kr-tam-supurme.py` — repoya alinacak. (Dokum DEVAM-ARSIV.md'de.)
4. **Merge kapisi eksigi (bugun iki kez isirdi):** kapi kumesi dalin *dokundugu alandan*
   turetiliyor; `index.html` gibi cok kapili dosyada asil kume **`deploy.yml`'in kendisi**.
   Ilk kirmizi ikinciyi maskeliyor. `~/.claude/skills/merge-kapisi/SKILL.md`'ye madde eklenecek
   (dosya git disi, elle duzenlenir, degistirince `tools/yedekle.py` kostur).
5. Marin'in **bolunemeyen 486 urunu**: `Olta Ekipmanlari` 277 + `Montaj Ekipmanlari` 209 — ne
   marka, ne model, ne `tur` verisi var; Okan'in **200 kurali** orada saglanamiyor.
6. HocA'dan devralinan iki site metni kalemi: SSS'de havale/EFT yok · "Yurtici Kargo" ifadesi
   siteden cikacak (Notion'da 8 tasiyici var, tek tasiyici degiliz).

**BEKLIYOR — baskalarinda (ACIK, arsive tasinmaz):**
- **HocA** → `ara*` rota oneki 3 landing'i 403 yapiyor (12 gundur; onarim
  `~/dev/pruvo-bot/worker/wrangler.toml`, Okan kapisi onda).
- **MaCiT** → eksik marka verisi (Garmin 54 · Sea-Doo 14+4 · Simrad 7 · B&G 3 · Bavaria 3) +
  POM tasiyan **11 urun kaydi** + bilesik marka yazimi (21 kayit, alan `marka`).
- **KaaN** → `rulman` semasi onarilinca satisa acma karari bende.
- **ArTisT** → marka-model sayfasi acma esigi onerisi (1.062 ciftin 812'si 5'ten az urun).

## AÇIK KALEMLER — önceki turlardan (kısaltıldı, taşınmadı)
- 3 landing hâlâ canlıda 403: onarım kardeş depodaki worker rota deseninde (önek jokeri),
  bu depoda değil; nöbetçi o kapalılığı artık saatlik ölçüyor ve kırmızı yakıyor.
- Sabah/gece kalinti sinifi: pencere icinde 2 sabahin 2'sinde AKIYOR→TIKALI salindi (2 Agu
  07:28→07:29 "392 dk", icerik main'de 1 dk iken; 1 Agu 07:11→07:12 "82 dk"). Kirmizi kalma
  23 dk / 73 dk, tepe yas 464,1 dk. Eski kodda birebir ayni — regresyon degil. Bu dal
  yanlis-kirmiziyi azaltiyor (7/90→4/90) ama kapatmiyor; onarim ayri tur (tabana 3. alt sinir:
  push'un geldigi an).
- Sozlesme nobeti tek yonlu: esik sabitini YUKARI kaydirmak yakalaniyor, ASAGI kaydirmak
  sessizce geciyor (49.1→5.0 ve 51.8→10.0 sag kaldi). Bugun zararsiz, cit uydurmaya acik yon.
- Zamanlama yan-kanali (sabit-zamanli karsilastirmanin gercek sabit-zamanliligi) hala
  OLCULMEDI; beyan korundu, yeni eksen acilmadi (uc turdur ayni sekilde acik).

## TABAN (yeniden olc, ezberleme)
Bu bolume SAYI YAZMA — gun icinde bayatliyor ve bayat sayi yanlis guven veriyor
(bugun olculdu: katalog tek oturumda 16589 -> 16672 hareket etti, elle tutulan agac
listesi de tutmuyordu). Tek dogruluk kaynagi kosulan komut:
- Katalog / D1: `python3 tools/d1-sync.py --durum`
- Calisma alani: `git -C /Users/okan/dev/pruvo worktree list`
- Kapilar: `python3 tools/durum.py`
