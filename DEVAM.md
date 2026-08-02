# DEVAM (KraL) — 31 Tem 2026

Onceki ayrintili kayitlar DEVAM-ARSIV.md'de (git disi, lossless).

## MERGE — 2 Agu 2026 · Yayin gecikme nobetcisi: yas tabani + kosum omru ekseni (`1d19ce96`)

- **Merge SHA `1d19ce96`** (merge-base `17cdc675`). Kapsam **10 dosya / +1391 −475**:
  `tools/yayin-gecikme-nobeti.py`, `-test.py`, `-mutasyon.py` + 7 fikstur. `deploy.yml` 0 satir;
  `urunler.json`, `worker/`, is akislari dokunulmadi. Cakisma yok (`merge-tree` yalniz agac
  OID'i `7d40150b`), sizinti taramasi 0 vurus, agac temizligi 0 sapma / 0 yabanci.
- **Kapilar dalin worktree'sinde kosuldu — hepsi exit 0:** kabul testi **38/38 iddia** ·
  mutasyon surucusu **20 mutant (16 kirmizi-beklentili + 4 kontrol), 8/8 eksende TEK-KIRMIZI
  mutant, kosum sonu 6/6 kaynak dosya sha256 bastakiyle ayni** · `ci-kapsam-test.py` YESIL
  (132 .py olculdu; 32 js/mjs **OLCULEMEDI**, bayrak cikarimi yapilmiyor) ·
  `kapi-envanteri.py` **7/7 VAR+BAGLI+NOBETTE** · `kisisel-veri-test.py` yesil ·
  `is-akisi-kapisi.py` yesil (166 kapi cagrisi, **0** etkisizlestirilmis).
- **Bagimsiz curutucu (9 eksen, hukum SARTLI — merge edilebilir):** 3029 noktada eski ve yeni
  mantik yan yana kosturuldu. Yeni yanlis-kirmizi **0 dakika**; dongu biriminde kirmizi
  **7/90 → 4/90**, sari **37/90 → 6/90**; gercek tikanma **7/7** senaryoda yakalandi; kapsam
  kaybi yok; 6/6 dosya sha256 esit.
- **Merge sonrasi bagimsiz teyit (ana checkout):** kabul **38/38** rc 0, mutasyon **20 mutant /
  8 eksen** rc 0.
- **D1 teyidi:** SAYI **16874 = 16874** · SEMA ekseni temiz (`urunler_yayin`,
  `urunler_yayin_kat` KURULU) · ICERIK 16874 satirda hash uyusmazlik/eksik/fazla **0**.
- **CI (SHA-KANITLI):** kosum **`30756610271`**, headSha **`1d19ce96…`** (birebir),
  conclusion **success**; `merge-base --is-ancestor` **rc 0**. Job'lar: cron-nabzi, envanter,
  build, mesaj-nobeti, serit-b — hepsi success.
- **Yayin gecikmesi (`durum.py`):** merge'den hemen sonra 🟢 AKIYOR — 2 commit bekliyor,
  en eskisi **43 dk** (esiklerin altinda); deploy bittikten sonra 🟢 AKIYOR — **0 commit
  geride**, bekleyen yok, son yayinlanan sha `1d19ce96`.
- **Temizlik:** worktree porcelain temiz · icerik main'de (`durum.py`: "0 ileri | ucu main'de")
  · ana agac temiz → worktree + dal silindi.

### 🔴 ACIK KALEM 1 — sabah/gece KALINTI SINIFI (curutucunun kayit sarti)
- Pencere icindeki **2 sabahin 2'sinde** tekrarladi.
- 2 Agu 07:28:22 AKIYOR (`geride=0`) → 07:29:22 **TIKALI, "en oldest bekleyen commit 392 dk"**,
  oysa icerik main'de **1 dakikadir**. 1 Agu'da 07:11 AKIYOR → 07:12 TIKALI "82 dk".
- Kirmizi kalma suresi **23 dk** ve **73 dk**; tepe yas **464,1 dk**.
- **ESKI kodda birebir ayni** → regresyon DEGIL, kalinti sinif.
- Mekanizma: sabahki push, committer tarihi son yayindan eski dal commit'leri tasiyor;
  `max(en_eski, yayin_ani)` gece yarisindaki yayina tabanlaniyor.
- **Bu dal yanlis-kirmiziyi AZALTIYOR (7/90→4/90 dongu), KAPATMIYOR.**
- Onarimi **ayri tur**: tabana ucuncu alt sinir (push'un GELDIGI an).

### 🔴 ACIK KALEM 2 — sozlesme nobeti TEK YONLU
`OLCULEN_KOSUM_OMRU_MAX_DK` / `OLCULEN_SAGLIKLI_YAS_TAVANI_DK` sabitini **YUKARI** kaydirmak
yakalaniyor, **ASAGI** kaydirmak sessizce geciyor (49.1→5.0 ve 51.8→10.0 sag kaldi).
Bugun zararsiz, ama cit uydurmanin yapilacagi yonde acik.

## OTURUM KAPANISI — 2 Agu 2026 · Uyum ekseni: yazma yolu + kapi sertlestirmesi + D1 kolonu

- **CANLIYA GITTI (uc commit):** `e6254d30` `uyum` **yazma yolu** — `duzelt.py`'de `uyum` alani +
  `RC_UYUM=7`; `marka` artik `uyum`dan turetiliyor ve ayni cagrida ikisini birden vermek
  **REDDEDILIYOR**. Kabul **35 iddia / 8 eksen**, mutasyon **16 mutant, 8/8 tek-kirmizi**. ·
  `0b26431e` `uyum-kapisi` **sertlestirmesi** — iddia **36**, taban capasi **yalniz dususte**
  kirmizi yakiyor, mutant **23**, `KAPSAR` olcutu **tamamen KALDIRILDI**. · `aa0f839c` D1 `uyum`
  **kolonu + `d1-sync` hash kapsami** — tam senkron **43 parca / 50.623 satir**, `--durum` uc
  eksen yesil, canli geri-okuma **DEGER 21/21**.
- **OLCULEN KARAR — bilesik marka icin global takma REDDEDILDI:** Turkce kok kirpma
  `benzin` -> `benz` yaptigi icin takma, `benzin` sorgusunu **550 -> 1428** (**+878 alakasiz**)
  sisiriyor ve **1011 kaydin 1001'inde** gercek A1/A2 ihlali doguruyordu. Yerine **5 baslik
  duzeltmesi** (**+25 bayt**, yanlis-pozitif **0**) MaCiT'e verildi.
- 🔴 **DERS (yeni — sema sira kuralina ekleniyor):** "sema once, kod sonra" `no such column`
  tuzagini kapatir **ama hash TANIMINI degistiren kolonlarda veri ancak kod main'e vardiktan
  sonra yakinsar** — arada eski kodla kosan her yazici hash'i geri sarar ve `--durum` herkeste
  kirmizi yanar.
- **BENDE (acik):** `d1-sync --durum` uc ekseni **tek cikis kodunu** paylasiyor — yalniz rc'ye
  bakan cagiran (merge kapimin D1 adimi) gercek sapmayi gurultuden ayiramiyor · `parite-test.js`
  marka filtresi UI'dan ayrisiyor (`markaKatla` vs tam jeton; cip evreninde **8 marka / 82 urun**,
  her kosumda fiilen **5 deger / 696 urun**) · `uyum-kapisi`'nde **7 iddianin** (S1, S3, S4, S7,
  V3, A3, A4) tek-kirmizi mutanti YOK, kosumda sayisiyla basiliyor.
- **BEKLIYOR:** MaCiT 5 baslik · HocA `uyum` kolonunu okuyan uc (kolon canlida DOLU, uc YOK) +
  `d1-sync.py`/`d1-sema.sql` sira koordinasyonu · CI/yayin kuyrugu (asagidaki olcum).
- **CI — OLCULEMEDI (rerun DENENMEDI):** `aa0f839c` tasiyan **tamamlanmis kosum YOK**.
  `gh run list --limit 20` cikis **0**: `30752012022` headSha `aa0f839c` ile **BIREBIR** ama hala
  **`in_progress`**; ardil kosum `30752548642` (headSha `4ad59e11`; `merge-base --is-ancestor`
  cikis **0** -> atalik **KANITLANDI**) **`pending`**. `--limit 1` yesili kanit sayilmadi.
- **YAYIN GECIKMESI (`tools/durum.py`, 🟡 rc 1):** canli main'den **4 commit geride**, en eski
  bekleyen **60 dk** (uyari esigi **45**) · son yayinlanan sha **`0b26431e`** (`deploy` isi
  basarili, 14:30 UTC) · ardisik iptal **1** (aclik esigi 6), ardisik hata **0** (tikanma esigi 4)
  · pencere **40 kosum** (38 tamamlandi / 2 kosuyor-bekliyor). Yani **`aa0f839c` henuz CANLIDA
  DEGIL** — kolon ve kod main'de, yayin kuyrukta.
- **HIJYEN — olu ic-rapor isaretcisi (public depo):** izlenen dosyalarda tarama **21 dosya /
  46 satir**. Bunun **31'i CANLI protokol** (nobetci `kisisel-veri-test.py` **22** fikstur +
  docstring, `mimar-kod-kilidi.py` muafiyet **1**, `durum.py` calisma-zamani okumasi **2**,
  `olculmemis-siparis-test.py` teslim talimati **1**, paket `.md`'lerinde isci teslim talimati
  **5**) -> **DOKUNULMADI**. **15'i OLU isaretci.** `tools/paket-uyum-ekseni.md:164` duzeltildi:
  gonderme (`Olcum + kabul: tools/RAPOR-MIMARA.md`) **silinmedi, sonucla degistirildi** ->
  "Olculdu ve kapandi (`aa0f839c`): tam senkron 43 parca / 50.623 satir, `--durum` uc eksen
  yesil, canli geri-okuma DEGER 21/21". Kalan **14 olu isaretci / 13 `.py` dosyasi**
  (`ci-kapsam-test` · `d1-sync` · `denetim-kapisi` x2 · `derin-cap-test` · `durum-yedek-test` ·
  `gorsel-boyut-test` · `icra-suzgeci` · `iki-govde-kapisi` · `is-akisi-kapisi` ·
  `metin-eslem-test` · `myminifactory-api` · `uretim-butunluk-kapisi` · `yayin-kapisi`) —
  **YAPILMADI**, sebep: `.py` **KAYNAK**'tir ve mimar commit kapisi ana checkout'ta kaynak
  commit'ini ACMAZ (`KAYNAK_UZANTI`); ayri worktree turu gerekir. `.gitignore` korumasina
  dokunulmadi; `raporlar/RAPOR-MIMARA.md` diskte VAR ama **izlenmiyor** (koruma calisiyor).

## MERGE — 2 Agu 2026 · WA siparis ucu yetki ekseni (`a3bd3a79`) + bilesik marka (`d05c3662`)

- **`d05c3662`** bilesik marka adi kanoniklestirmesi: kapali tablo, bagimsiz kod yolu. Parite
  **1199 + 845** sorgu exit 0 · `uyum-kapisi` **36/0** · mutasyon **22/22** (3 kontrol mutanti
  yesil, canli sha256 degismedi) · D1 **16874=16874** · canli kosum SHA-kanitli.
- **`a3bd3a79`** WA siparis ucu. Bayat `404` iddiasi SILINMEDI, **5 ayri iddiaya bolunerek**
  guclendirildi; `YONET_ANAHTAR` kapisi `/wa-siparis` blogunun **ONUNE** alindi (fail-closed) ve
  olu `yonetAnahtar: null` dugmesi canlandirildi. Surucu `tools/wa-yetki-mutasyon.py` repoda,
  mutant **kopyaya**: **5/5**, ikisi TEK-EKSEN ayirt edici (M1b 3/0, M2 2/0). Takim
  **158 -> 164 iddia / 0 kalan**.
- 🔴 **Merge aninda sessiz katalog geri-sarmasi yakalandi ve merge'e GIRMEDI:** guard, merge
  ortasinda HEAD'i yetkili sanip main'den gelen katalogu geri sariyordu — **urun SAYISI 16874
  dogru kaldigi icin sayi ekseni gormuyordu**, ama **16149 urunde `uyum` ALANI dusuyordu**
  (13.040 kayitlik backfill). Katalog main'in yetkili surumune esitlendi, merge `urunler.json`'a
  **sifir satir** dokundu; atlanan kancanin kontrolleri elle kosuldu (uc kapi da exit 0).
- Yan onarim: `tools/yonet-cerez-mutasyon.py` **6 capasi bayat dusup 25 mutanti olcusuz**
  birakiyordu → capa onarildi (25 kirmizi + 3 kontrol yesil). D1'de **3674 bayat hash** vardi
  (`69fd4a08` backfill'i inmemis) → `d1-sync` kosuldu, uc eksen temiz.
- **Hijyen (EMIR):** DEVAM.md 410 -> 87 sat / 29908 -> 6431 B, ARSIV 7417 -> 7740 (silinen =
  eklenen **birebir 323**, sinif kapisi exit 0, `d5d76782`) · CLAUDE.md 12262 -> **11768 B**
  (bosluk payi 26 -> 520 B, link/yol/skill kumeleri birebir) · kutu 353 -> **217** · `uyum-backfill.py`
  referans 0 → silindi · **KraL worktree 7 -> 0**; tavan Okan hukmuyle artik SAHIPLIK bazli
  sayiliyor.

## MERGE — 2 Agu 2026 · Yonet giris kapisi nobetcisi KAPANIS turu (vakum yesili + aklama + gecikme ekseni)

- **Merge SHA `e192941c`** (dal ucu `f8100a61`, merge-base `d05c3662`; merge aninda main
  `92496003`). Kapsam **3 dosya / +285 −29**: `tools/yonet-cerez-mutasyon.py`,
  `shop/test/kabul.js`, `.github/workflows/deploy.yml` (4 satirin **hepsi yorum**).
  `shop/src/yonet.js` DEGISMEDI — sha256 dalda ve o anki main'de birebir ayni. `urunler.json`
  ve urun kaynak kaydi dokunulmadi. Cakisma yok; sizinti taramasi 0 vurus (desen + elle okuma).
- **Uc kapi kapandi:** (1) surucunun **vakum yesili** (bos kayit listesiyle rc=0) kapatildi;
  (2) survivor'i `beklenen=[]` ile "kontrol" diye **aklama** kapatildi — sinif artik `kontrol()`
  ile BEYAN ediliyor; (3) olculmemis `GIRIS_GECIKME_MS` eksenine **`C23`** iddiasi eklendi.
  **IDDIA 70 -> 71**, surucu **28 -> 29 kayit**.
- **`C23` (olculdu):** yalniz **ALT SINIR** (>= 100 ms), **ust sinir YOK** — bloklayici alt
  kumede yanlis-kirmizi riski alinmadi. Kaynaktaki deger 250 ms, esik 100 ms; esik siniri
  birebir olculdu (250 -> 100 **yesil**, 250 -> 99 **kirmizi**). Ayirt edici mutant **M26**
  (250 -> 0), TEK kirmizi. **103 kosumda** cikis kodu kumesi `{0}`, IDDIA kumesi `{71}` —
  sifir sallanma. node 20'de sonda yamasi takilamazsa **fail-closed**.
- **Kapilar DALIN worktree'sinde kosuldu, hepsi cikis 0** (yerel node **v25.8.1**):
  `kabul.js --yonet-cerez` **SONUC 71 gecti / 0 kaldi, IDDIA SAYISI 71** (70'ten DUSMEDI) ·
  `yonet-cerez-mutasyon.py` **29 kayit, TUM MUTANTLAR YAKALANDI, KONTROLLER YESIL**, taban
  iddia 71, `yonet.js` sha256 basta = sonda · `--sema-paritesi` **2/2** · kisisel veri testi
  (272 sayfa / 441 izlenen dosya) · `ci-kapsam-test.py` **YESIL** (162 kesfedilen / 126 kosan /
  36 muaf) · `kapi-envanteri.py` **7/7**.
- **Parite KOSULMADI — olcerek:** diff'te `worker/`, arama yolu ve `urunler.json` **YOK**.
- **CI:** kosum `30750275722`, headSha **`e192941c` ile BIREBIR** (ardil arama gerekmedi;
  `merge-base --is-ancestor` cikis 0). Kosum **completed/success**, **7 isin 7'si success**
  (serit-b · envanter · mesaj-nobeti · cron-nabzi · build · deploy · yayin). Bloklayici
  **"Yonet anahtar/cerez kabul testi (admin giris kapisi — deterministik alt kume)"** adimi
  **success** — `C23` node 20'de ILK KEZ kostu ve gecti. Kosum logunda
  **`sonda yamasi=TAKILDI`** (`olculen=250 ms · istenen=[250] · gecen=2 ms`), `IDDIA SAYISI: 71`.
- **D1 teyidi (merge sonrasi, IKI kez olculdu):** ilkinde SAYI **16874 = 16874** ✅ + sema temiz ✅
  ama ICERIK ekseni **3674 bayat hash** (eksik/fazla 0). **Bu dalin isi DEGIL** — `urunler.json`
  bu dalda dokunulmadi; baska bir duzlemin akan yazma turundan. Kapanista TEKRAR olculdu:
  **16874 = 16874, sema temiz, uyusmaz/eksik/fazla 0/0/0** ✅ — drift kapandi.
- **Merge SONRASI capraz dogrulama:** ayri bir dal (`a3bd3a79`) main'e girip `shop/src/yonet.js`'i
  **+468 satir** degistirdi (sha256 `ef0849d1…` -> `be8189c1…`). Yeni nobetci o degismis kaynak
  uzerinde ANA agacta yeniden olculdu (`0b26431e`): `--yonet-cerez` **71/71 rc 0** · surucu
  **29 kayit, TUM MUTANTLAR YAKALANDI** · `M26` hala TEK kirmizi (`C23`). Kapanis turu kaynak
  degisimine **dayandi**.
- **Temizlik:** worktree kaldirildi; dal **yerel + uzak** silindi. Uc on-kontrol yesildi:
  porcelain temiz · `is-ancestor f8100a61 origin/main` cikis **0** · ana agacta yetim
  degisiklik yok.

**ACIK MADDELER — bu turda ONARILMADI, merge'i BLOKLAMADI:**
1. Surucude benzersizlik yalniz **ETIKET** uzerinde denetleniyor, **mutasyon METNI** uzerinde
   DEGIL: bir kayit silinip yerine baska bir kaydin metninin kopyasi YENI etiketle konursa sayi
   korunur ve surucu rc=0 verir. Kaynaktaki "ayni kodu iki kez kaydedip sayi sisirmek artik
   kusur" ifadesi bu yuzden FAZLA IDDIALI.
2. Gercek bir survivor `kontrol()` ile BEYAN edilirse yine aklanabilir — aklama mekanik degil,
   **insan beyanina** bagli.
3. `kabul.js`'te `C23` icin "IKI BAGIMSIZ TANIK" ifadesi **yanlis**: taniklar birbirini DISLEYEN
   iki KIP. Anlatim kusuru; olcum dogru.
4. `yamaTakildi` hicbir iddiayla **capalanmiyor** — yalniz `C23`'un detay metninde raporlaniyor.
   (Bu tur CI logundan **okundu**: node 20'de TAKILDI.)
5. 🔴 **IKI ON-VAROLAN OLCULMEMIS EKSEN** — dalin regresyonu DEGIL, merge-base `d05c3662`'de de
   yakalanmiyordu; **ayri tura kayit**. Dokumu **DEVAM-ARSIV.md**'de (sinif kapisi).
6. Zamanlama yan-kanali (sabit-zamanli karsilastirmanin gercek sabit-zamanliligi) hala
   **OLCULMEDI** — beyan korundu, yeni eksen acilmadi.

## MERGE — 2 Agu 2026 · Nobetci gecme olcutu fail-closed (yonet cerez mutasyon surucusu)

- **Merge SHA `1b643886`** (dal ucu `7fa6392c`, merge-base `9d8d0cf8`). Kapsam **2 dosya /
  +179 −29**: `tools/yonet-cerez-mutasyon.py` ve `shop/test/kabul.js` (kabul.js'te +12 satirin
  tamami yorum). `shop/src/yonet.js` diff **BOS** — kaynak davranisi degismedi, sha256 basta =
  sonda. `urunler.json` ve urun kaynak kaydi dokunulmadi. Cakisma yok; sizinti taramasi 0 vurus.
- **Olcut fail-closed:** taninmayan/eksik `olcut` degeri artik varsayilana DUSMEZ (kosum oncesi
  dogrulayici + tuketim yerinde varsayilan dal YOK). Bagimsiz curutucu **12 gecersiz-deger
  denemesinin 12'sini** kirmizi olctu; ayni sapma **eski surucude cikis 0** veriyordu.
  Deneme kumesinin dokumu DEVAM-ARSIV.md'de.
- **Kayit dagilimi (olculdu):** 28 kayit = **22 ESIT** (11 tek_eksen + 11 esit_kume) +
  **3 KAPSAR** (M6/M8/M9, kirmizi kumesi beyandan gercekten genis, gerekcesi kaydinda) +
  **3 kontrol**. Yeni kayit **M24/M25** (`/liste` kolunun iki cagri ordinali), her biri TEK kirmizi.
- **Oynaklik ekseni:** 67 kosumda (beyan sirasi + ters + karisik) oynak kayit **0**;
  IDDIA SAYISI hep **70** — yanlis-kirmizi riski sifir olculdu.
- **Kapilar DALIN worktree'sinde kosuldu, hepsi cikis 0:** `kabul.js --yonet-cerez`
  **70 gecti / 0 kaldi, IDDIA SAYISI 70** (dusmedi) · mutasyon surucusu **28 kayit, TUM MUTANTLAR
  YAKALANDI** · `--sema-paritesi` **2/2** · kisisel veri testi (272 sayfa / 437 izlenen dosya) ·
  CI kapsam kapisi (**161 kesfedilen / 125 kosan / 36 muaf**) · kapi envanteri **7/7**.
- **Parite KOSULMADI — olcerek:** diff'te `worker/`, arama yolu ve `urunler.json` **YOK**.
- **D1 teyidi (merge sonrasi):** urun **16874 = 16874**; sema ekseni temiz; icerik ekseni
  16874 satirda hash uyusmazlik / eksik / fazla **0**.
- **CI:** kendi SHA'sinin deploy kosumu `30746287431` escamanlilikla **cancelled**. SHA-kanitli
  yesil **ardil** kosum `30746642484` (headSha `e6254d30`; `merge-base --is-ancestor 1b643886
  e6254d30` cikis **0**) — kosum **completed/success**, **7 isin 7'si success**
  (envanter · serit-b · cron-nabzi · build · mesaj-nobeti · deploy · yayin); bloklayici
  **"Yonet anahtar/cerez kabul testi (admin giris kapisi — deterministik alt kume)"** adimi
  **success**. Ayrica `1b643886`
  headSha'li iki yardimci is akisi success (`30746394593`, `30746436977`).
- **Temizlik:** worktree kaldirildi; dal **yerel + uzak** silindi.
- **Kuyruk ayri oturumda kapatildi (surec olduruldu, durum kayboldu).** §6/§4/§7 ana checkout'ta
  guncel main (`d05c3662`) uzerinde YENIDEN olculdu: `kabul.js --yonet-cerez` **SONUC 70 gecti /
  0 kaldi, IDDIA SAYISI 70** (rc 0) · `yonet-cerez-mutasyon.py` **28 kayit, TUM MUTANTLAR
  YAKALANDI**, taban iddia 70, `yonet.js` sha256 basta = sonda (rc 0) · `kapi-envanteri.py`
  **7/7** (rc 0) · `ci-kapsam-test.py` **YESIL** (rc 0; bu kosumda **162 kesfedilen / 36 muaf** —
  ustteki 161 dalin worktree'sinde olculmustu, aradaki fark main'in ilerlemesi) · D1 **16874 =
  16874**, sema temiz, icerik ekseni 0/0/0.
  ⚠️ **Bu bloktaki 70 iddia / 28 kayit O TARIHIN olcumudur.** Guncel deger `e192941c`'ten
  itibaren **71 iddia / 29 kayit** — ustteki bloga bak.
  Zombi **YOK**: `worktree-agent-ad6c23c2a535991b1`
  ne worktree listesinde ne yerel ne uzak dalda var; `merge-base --is-ancestor 7fa6392c
  origin/main` cikis **0** ve M24/M25 kayitlari ana agactaki surucude MEVCUT.

**ACIK MADDELER — o turda ONARILMADI. 1-3 `e192941c` ile KAPANDI (ustteki bloga bak); 4 ACIK.**
1. ✅ KAPANDI (`e192941c`): `MUTANTLAR` listesi **bos** birakilirsa surucu cikis 0 + "TUM
   MUTANTLAR YAKALANDI" basiyordu — vakum yesili.
2. ✅ KAPANDI (`e192941c`): bir mutant `beklenen=[]` ile "kontrol" diye kaydedilirse yesil
   geciyordu; sinif artik `kontrol()` ile BEYAN ediliyor.
3. ✅ KAPANDI (`e192941c`): giris gecikmesi sabiti 250 → 0 alt kumede **SURVIVOR**'di; artik
   `C23` iddiasi + `M26` mutanti var.
4. 🔴 **ACIK** — Zamanlama yan-kanali (sabit-zamanli karsilastirmanin gercek sabit-zamanliligi)
   hala **OLCULMEDI**; beyan korundu, yeni eksen acilmadi.

## MERGE — 2 Agu 2026 · CI kapsam kapisi (opt-in alt kume + coklu is akisi tetigi)

- **Merge SHA `8559518f`** (dal `claude/cool-rhodes-92cdf1`, merge-base `ead0bcb6`).
  Kapsam **4 dosya / +2081 −30**: `tools/ci-kapsam-test.py`, `tools/yaml-oku.py`,
  `shop/test/kabul.js`, `.gitignore`. `deploy.yml` 0 satir; `urunler.json` ve
  urun kaynak kaydi dokunulmadi. Cakisma yok, sizinti taramasi 0 vurus.
- **Kapilar dalin worktree'sinde kosuldu (hepsi exit 0):** CI kapsam kapisi
  **161 kabul testi kesfedildi · 4 is akisi (3 otomatik / 1 elle) · 125 otomatikte kosuyor ·
  36 muaf · 2 beyan edilen alt kume (2/2 kapsandi) · 18 muaf alt kume**;
  `--kendini-test` 6 nobetci yesil (48 + 53 sentetik fikstur);
  kapi envanteri **7/7 VAR+BAGLI+NOBETTE**; gitignore kapisi temiz (267 uretilen dizin);
  shop kabul testi **28/28**, ic parite 300 (site) + 845 (Ege) birebir.
- **Bilinen sinir:** iki-kol YAML paritesi bu ortamda **OLCULEMEDI** (tek gercek kol vardi);
  sabit kumede sapma 0 olarak raporlandi, kume disi girdi ayri madde olarak duruyor.
- **D1 teyidi (merge sonrasi):** urun **16874 = 16874** (D1 == urunler.json benzersiz);
  sema ekseni temiz; icerik ekseni 16874 satirda hash uyusmazlik/eksik/fazla **0**.
- **CI:** koşum `30745372063` headSha `8559518f` **failure** — tek kirmizi adim
  "Varlik (ortak CSS/JS harici dosya) kabul testi". **Dalin degil:** ayni adim merge-base
  `ead0bcb6` kosumunda (merge'den ONCE) da kirmiziydi ve dal o kapinin dosyasina hic dokunmadi.
  Dalin kendi iki adimi ("CI kapsam kapisi" + "oz-nobetcileri") ayni kosumda **success**.
  Onarim baska bir oturumda `95d19364` ile main'e alindi; `8559518f` o SHA'nin **atasi**
  (`merge-base --is-ancestor` exit 0) ve ardil kosum `30745500956` **success** — 71 adimin
  hepsi yesil, varlik adimi dahil. SHA-kanitli yesil bu kosumdur.

## TABAN (yeniden olc, ezberleme)
Bu bolume SAYI YAZMA — gun icinde bayatliyor ve bayat sayi yanlis guven veriyor
(bugun olculdu: katalog tek oturumda 16589 -> 16672 hareket etti, elle tutulan agac
listesi de tutmuyordu). Tek dogruluk kaynagi kosulan komut:
- Katalog / D1: `python3 tools/d1-sync.py --durum`
- Calisma alani: `git -C /Users/okan/dev/pruvo worktree list`
- Kapilar: `python3 tools/durum.py`
