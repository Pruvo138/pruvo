# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 16 Agu (~16:00Z) — K113 + K114 KAPANDI · YAYIN ACILDI · KOK NEDEN BULUNDU (K124 ACILDI) (KraL)

**Merge `04b48b36`** (origin/main). Worktree+dal SILINDI. **`deploy`=success · `yayin`=success.**
Canli dogrulama (onbellek kirma YOK, kanonik adres): `pr80134` **200** · `pr66488` **200** ·
`c3dred-bull-250ml-adaptoru` **200** · `/marka/vespa/` **200** · kok **200** ·
canli `urunler.json` **28682** (= D1 = agac). Yayin-yasi nobetcisi canli hukum: **ACIK**.

**(A) K113 — uretici butunluk kapisi BLOKLAYICI oldu.** Adim `hijyen-build`ten `build` isine
TASINDI (kopya BIRAKILMADI). Kapi kanonik adresi olcer; `deploy: needs` disindayken 16 Agu'da
bozuk ID'leri GORDU ama yayini durdurmadi. Tasimadan ONCE canli CI kaydindan yesil oldugu
olculdu (`hijyen-build` icindeki adim `success`); ilk kosumda **`build` yesil gecti**.

**(B) K114 — `onarim/r2-purge` birlesti** (`tools/r2-purge.py` + `tools/r2-purge-test.py`),
batarya `nobet.yml` `r2-onek-nobeti` isine baglandi (SERIT B, agsiz). `ci-kapsam` KAPSAMSIZ
kirmizisi kapandi (rc=0, taban 0).

**(C) K123 ardil onarimi:** `is-akisi-kapisi::NOBET_DOSYALARI`'na `yayin-yasi-alarmi.yml`
eklendi; kapi **6 sorun -> 5**. Kalan 5 tabanda da var (hijyen isleri kosumun genel
`conclusion`'ini kirletiyor).

## 16 Agu (~17:00Z) — K124 KAPANDI (KALICI COZUM CANLIDA) · K35 BUDAMA · K38 WORKTREE (KraL)

**K124 merge `b68d9eb7`.** Turetilmis sinifta soru DEGISTI: "insan beyan etti mi" YERINE
**"yeni hal saglikli mi"** (`varlik-test.py::turetilmis_hal_saglikli_mi`): sayfa turetilmis
hedeflerini KAYBETMEMIS · her hedef katalogda VAR · gorsel anahtari GELENEGE uygun. Ucu de
saglanirsa bulgu bloklamaz, taban kendiliginden tazelenir; saglanmazsa davranis BUGUNKUNUN
AYNISI (beyan aranir, yoksa KIRMIZI) — kol yalniz EKLER.
- **Kabul:** beyan dosyasi GECICI KALDIRILARAK rc=**0** (12 sayfa "BEYANSIZ gecti", saglik
  kolu GECMEDI satiri 0) · beyanli rc=0 · **SURVIVOR=0** (8 vaka + 5 mutant, her kosumda) ·
  ci-kapsam 0 · taban (kolsuz main) rc=1.
- **Canli sinav:** ayni push'ta 14 urunluk parti vardi (`e3371c0b`) — `serit-a3` **success**,
  yani parti indi ve kapi **beyansiz** yesil gecti.
- Bugun elle yazilan 6 urunluk beyan blogu GERI ALINDI (saglik kolu isini yapiyor; duran
  beyan ileride "saglıksiz" bir hali sessizce gecirirdi).
- 🔬 Batarya KENDI kodumda OLU KOL buldu: "baglanti azalmasi" kolu gorsel kolunun golgesinde
  hic karar vermiyordu (SURVIVOR). Iki ekseni AYIRAN fikstur (S2b) eklendi.

**K35 (defter kotasi):** DEVAM.md **442 -> 65 satir · 33.058 -> 4.745 bayt**; DEVAM-ARSIV.md
**18.354 -> 18.734 satir** (lossless: tasinan bayt = silinen bayt). Ortak kutu **298 -> 274**,
kutu arsivi **29.724 -> 29.760**.
**K38 (worktree):** `k119e` LOSSLESS kapandi — commitsiz taslak `fcec82eb` ile commit'lendi,
`origin/fix/k119e`'e itildi, worktree kaldirildi. **worktree 3 -> 1.**

## 🔴 YAYIN NEDEN SUREKLI KAPANIYOR — KOK NEDEN OLCULDU (K124 ILE KAPANDI)

Bugun uc kapanmanin ucu de ayni sekil: bloklayici `serit-a3` kirmizi -> `deploy` calismiyor.
Bu kez sebep **varlik kapisi** idi ve KUSUR VERIDE DEGIL:
- Rel-card (ilgili urun) havuzu **KATALOGDAN TURETILIR**; her yeni parti komsu sayfalarin
  gosterdigi urunu degistirir. Kapi bunu `CIKARIM KAYBI` sayar.
- Bu sinif **beyan edilebilir**: gecmesi icin birinin etkilenen urun kimliklerini elle
  `tools/varlik-cikarim-beyani.json`'a yazmasi gerekir. Her partide yazilmadigi icin kapi
  kirmizi kaliyor. `--referans-tazele` de kirmiziyken calismayi REDDEDIYOR -> taban kendini
  onaramiyor (kilitli dongu).
- **Veri kusuru YOK (olculdu):** dusen iki gorselin ikisi de canlida **200**, hicbiri sayfanin
  KENDI gorseli degil; katalogda bicim disi gorsel URL'i **0/82462**. Urun ekleme hatti
  suclu DEGIL.
- **Ikinci incelik (olculdu):** ayni iyi huylu kayma IKI sinif uretiyor — rel-card GORSELI
  (`rel-card-hedefleri`) ve rel-card BAGLANTISI; kapi `/urun/<id>/` tasiyan baglantiyi
  `breadcrumb-adresi` sayiyor. Tek sinif beyan edilince kapi KIRMIZI KALDI.

**Yayin bugun 6 sayfa beyan edilerek acildi** (blok 2, urun 36; `varlik-test` rc=0, 10 eksen
yesil; `varlik-beyan-test` VAKA=8 DUSEN=0 — blanket beyan hala RED).

🔴 **UCUNCU INCELIK (olculdu):** kapi her kosumda katalogdan **RASTGELE 12 urun** ornekler.
28.682 urun beyan EDILEMEZ; yazilan beyan ancak o kimlikler TEKRAR ornekle gelirse ise yarar.
Beyan yolu bu yuzden YAPISAL OLARAK kapanamazdi — K124 tam bu nedenle gerekliydi.

## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)

- 🔐 **K120 (OKAN KARARI, uygulanmadi):** gizli kaynak kaydi git'ten CIKACAK. 🔴 Cikarmadan
  ONCE o dosyayi okuyan HER kapinin YOKLUK KOLU olculmeli — sessiz yesil sayan kapi,
  dosya izlemeden ciktiginda korumasini kaybeder. **Olcum turu KOSUYOR.**
- 🔧 **K118:** pre-push sizinti kapisi bicim-kaydiran urun partisinde butceyi yapisal olarak
  asiyor (tam-dosya diff). Yon: butceyi buyutmek DEGIL, `urunler.json`'u icerik ekseninde
  ayri ele almak. `kabul:` alani BOS — kapanmadan once doldurulacak.
- 🟠 **Navlungo dilim-1 MERGE BEKLIYOR:** dal `il-ilce-dilim1` (`5d57c918`). Okan kapisi:
  `.navlungo-kimlik.json` doldurulmasi.
- 🔴 **K104 / K104B:** nobet is akisi sicili + iki kapi main'de de kirmizi (mutasyon
  capalari M06/M31 + iki kapinin kanca kablosu envanterde yok). HUKUM MIMARDA.
- **K99** bag kolonu spec'i · **K100** defter sinifinda satir-sonu muafiyet kusuru ·
  **K102** nobet yazicisi kok deftere yasakli ic dosya adi uretiyor.
- 🔧 **Iki acik kapi kalemi:** (a) shop bayatlik alarminin TETIK ekseni raporladigi bundle
  evreniyle AYNI DEGIL; (b) `devam-sinif-kapisi.py` is-akisi muafiyeti `norm`/`ham`
  ekseninde ayrisiyor.
- 🟠 **K122:** `kurtarma/k122-yabanci-is` dali DURUYOR — peer'in dusurulen commitsiz isi
  (deploy.yml serit tasima · marka-uyelik-test.py · kalibrasyon 4 dosya). Sahibi uygulayacak.
- 🟡 **Kosum sinyali kirli (yeni, olculdu):** `hijyen-a2` + `hijyen-a3` yayin zincirine bagli
  DEGIL ama kosumun genel `conclusion`'ini `failure` yapiyor — "yayin durdu" yanlis hukmu
  doguyor. `is-akisi-kapisi` bunu 5 bulgunun 4'unde soyluyor; cozum joblari `nobet.yml`'e
  tasimak. Bugun iki kez bu yuzden "kirmizi" gorundu, yayin akiyordu.
- KAPANDI (arsivde): K91 · K101 · K103 · K113 · K114 · K115 · K116 · K117 · K119 · K123 · K124.

## 16 Agu (~18:00Z) — K39 KAPANDI: DEFTER KOTASI ARTIK KANCADA (KraL)

**Merge `ce5164d2`.** Elle budama 4. kez tasmisti; artik sinif kapisi var.
- `tools/defter-rotasyon.py` — KAPALI bloklari arsive LOSSLESS tasir, **CANLI BAS
  DOKUNULMAZ**. Kesme olcutu TARIH DEGIL: blokta ACIK isaretci varsa TASINMAZ; tasinmak icin
  KAPANDI/KAPANIS/✅ ZORUNLU. Suphede KALIR. Bayt esitligi tutmazsa iki dosya da geri yazilir.
- `tools/defter-kota-kapisi.py` + `kancalar/pre-commit` adim 8: DEVAM.md STAGE'DE ve INDEX
  blob'u >130 satirsa commit RED + ekrana CARE komutu. Kapsam DAR (defter stage'de degilse
  hicbir commit etkilenmez).
- 🔴 **SAYAC KOLU `pre-push`'ta ve DURDURMAZ:** kapinin kosmadigi haller ancak SONUCUNDAN
  sayilabilir; kol HEAD'deki defteri olcer, kota asilmissa repo DISI sayaca satir yazar
  (yol + mekanik DEVAM-ARSIV.md'de; gunluk 15:00 olcumune eksen olarak girer).
- **Olcum:** rotasyon FIKSTUR **6/6** · MUTANT **OLDU** (acik-blok vetosunu bozan mutant
  kirmizi yakti) · sayac vakalari **1/0/0** (kota asan / kota alti / deftersiz ev) ·
  KraL RED **rc=1** + CARE satiri VAR · KraL KONTROL **rc=0** · MaCiT RED **rc=1** + CARE VAR.
  **Iki evde canli.** MaCiT'te `tools/kancalar/` yoktu; kablo `.git/hooks/pre-commit`
  (commit'e girmez), o evin izlenen dosyalarina DOKUNULMADI.

## OKAN'DA

- Eski yedek klasorunu backup-v2 icine tasima · K89 olcum eylemi silme karari.
  (Motor tarifesi kalemi 16 Agu'da KAPANDI: kimi + minimax-m3 ust aboneligine gecildi.)
- 🔧 **TARIFE KARAR KURALI (olculdu, onaya hazir):** mevcut $20 plan KALIR. Haftalik kota %80'e yaklasirsa ikinci saglayicinin $39 basamagi TERCIH EDILIR — ayni para bandinda hem kota hem **ikinci saglayici** (429/kesinti/kota duvarinda yedek) verir; mevcut saglayicinin $50 basamagi yalniz kota verir, tek-saglayici riski surer. Ikinci saglayici bekleme listesindeyse tek uygulanabilir yol $50 (0 kod degisikligi). Ust basamagin iki "deneysel" ozelligi bizim hatta GIRMEZ — biz yalnizca Anthropic-uyumlu API ucundan MODEL cagiriyoruz. Kota sayilari iki adayda da yayimlanmiyor, yani secimi fiyat degil CESITLILIK belirliyor. Ekleme bedeli motor basina 6 kod noktasi.
- Olculen maliyet tabani: $18,72 / 1.081.021.287 token / 8.639 istek = yaklasik $17,3/milyar; $20/ay ve yaklasik 4,6 milyar/ay = yaklasik $4,3/milyar.

## KOSUYOR (baska mimarlar)

MaCiT — Ducati d1 sub-slice 2/3 ve 3/3 (taban artik 27420) + 261 kaynak kaydi dolgusu.

## ARSIVDE (tam metinler `DEVAM-ARSIV.md`'de)

14-15 Agu saatlik CI nobeti turlari · 15 Agu gece oturum kapanisi · K101/K103 kapanislari · yayin ve odeme etiketi bloklari · dorduncu motorun hatta baglanmasi · HD/Kawasaki/Ducati ekleme bloklari · sabah oturumunun tam olcum blogu · defterin sikistirma oncesi 196 satirlik tam hali.
