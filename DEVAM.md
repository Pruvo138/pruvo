# DEVAM (KraL) — 8 Agu 2026

## 🔁 KraL DEVIR (clear oncesi yazildi) — SIRADAKI TEK IS: `muh/marka-tek-sayfa` dalini KAPAT
**Okan emri (bu gece):** dali baslat; MaCiT mesgul oldugu icin 215 urunluk VERI onarimi BEKLIYOR.
Dal: `muh/marka-tek-sayfa` **`73adb519`** (push'lu, worktree bugun KALDIRILDI → yeniden `worktree add` gerek).
Hukum (Okan): marka sayfasi markanin TUM parcalarini kart listeler, cipler **sayfa ici filtre**.
Olculen: gorunur kart **11731 → 21628** (audi 200→331 · ford 488→2583 · bmw 1010→2347), azalan marka **0**,
kimlik sapan sayfa **32 → 0**, tavani asan sayfa **11 → 0**. Iddia 10871, davranis testi 20/20.
Onceki curutme 1. turda MERGE_EDILEMEZ demis, UC kirmizi kapatilmis (teslim yolu tautolojisi ·
agirlik regresyonu → edge `/katalog?ids=` · ci-kapsam kablolama).
⏭ **EKSIK OLAN:** mutasyon bataryasi + ilk-yuk bayt tablosu → **dar curutme (yeni yuzey)** → merge + canli dogrulama.
⚠️ Merge oncesi ZORUNLU (bugun iki kez yayin durdu): `is-akisi-kapisi.py` rc=0 + yeni adim `serit-b`'ye
DUZ TEK KOMUTLA kablolu + `SERIT_B` beyani AYNI commit'te; ayrica `varlik-test.py` rc=0.
Bu dal ayrica sayfanin kendi ic sayac celiskisini kapatir (baslik 330 ↔ cip toplami+diger 370).
🔴 **KAPANMADI, ayri is (VERI duzlemi/MaCiT):** basliginda marka gecen ama `marka[]` uyesi olmayan
**215 urun** (Mini 42 · Grom 29 · K100 19 · Datsun 18…). `arama.py` gecis kolu **ONCE KAPATILMAYACAK**
(arama daralir, satis yolu). Ayrica acik: H1/H3 kurali **16 model-olmayan** degeri model sayiyor.

## ✅ BANNER LCP ONARIMI CANLIYA INDI + ONCE/SONRA OLCULDU — 9 Agu 00:46 (kosum `31284643156`, head `062f8cb2`)
`e907eac7` 8 Agu 22:16'dan beri main'deydi ama **hicbir kosum onu yayinlamamisti**; kendi kosumu
(`31281327794`) cancelled, ardil kosumlarda `serit-a2`+`serit-a3` defter sinif kapisindan kirmizi.
Kalan tikanikligin sebebi bu kirmizilar DEGILDI (onarim `e56705a2`'de; iki kapi da main tepesinde
rc=0 olculdu): kuyruk `bdddaee0` kosumunda (`31282011345`) kilitliydi — `serit-a4` ucusta, ama
`serit-a2`/`serit-a3` ZATEN kirmizi oldugu icin o kosumun `deploy`'u garanti `skipped`'ti; `pages`
grubunu tutan bu OLU kosum iptal edilince kuyruk acildi ve `31284643156` **deploy + yayin success**
verdi (artefakt `last-modified 00:45:42Z`, `cf-cache-status=HIT`, `age=0`).
**Canli kabul (canonical adres, cache-bust YOK) — 6 eksen:** `<picture>` **6** · `rel=preload`+
`as=image` **1** · `preconnect` **1** · `-v2-*.webp` benzersiz anahtar **18** · v2'siz banner webp
**0** · eski uc anahtarin toplam gecisi **0**. `fetchpriority="high"` **2** cikti; beklenti 1 idi ve
**beklenti yanlisti**: head preload + govde LCP `<img>` ikisi birden tasimak ZORUNDA (ayrisirsa
gorsel iki kez iner) — kaynakta 23. ve 1036. satir, yani 2 DOGRU sayidir.
**PSI mobil (Lighthouse 13.4.1, emule Moto G Power / yavas 4G) — ONCE (8 Agu, TEK kosum) → SONRA
(9 Agu 00:56-01:02Z, UC kosum):** performans **74 → 88 · 92 · 98** · LCP **10,7 → 2,1-3,4 sn** ·
SI **2,4 → 1,1 sn** · FCP **1,1 → 1,1 sn** · TBT **100 → 10-170 ms** · CLS **0 → 0**.
Regresyon kontrolu: erisilebilirlik **100** · en-iyi-uygulamalar **100** · SEO **100** — ucu de
UC kosumun UCUNDE de degismedi.
🔴 **Tek kosum yaziLMADI, ARALIK yazildi:** ilk kosum 98/2,1 sn okundu, bagimsiz ikinci tur 92/3,4 sn
ve onbellekten okunan ucuncu bir rapor 88 verdi. Performans ±5, TBT 10-170 ms salindi; yani tek
PSI kosumunu "sonuc" diye civilemek bu sayfada **yaniltici**. Salinimin ALTINDA kalan hukum yine de
tartisilmaz: LCP **10,7 sn → en kotu 3,4 sn**, yani en kotumser okumada bile ~3x iyilesme, ve TBT
ekseni gurultunun icinde (100 ms tabani araligin ORTASINDA) — TBT'de regresyon IDDIA EDILEMEZ.
🔴 **Atif siniri:** olculen sayfa `062f8cb2` ve bu commit `b7cdc015`'i ICERMEZ (`--is-ancestor`
rc=1) → yukaridaki kazanc **WebP kolunun TEK BASINA** kazancidir; AVIF kolunun EK katkisi HENUZ
olculmedi. Kardes turun bekledigi kosum `31286873618` (head `3e7f1b24`, `b7cdc015` ICERIR) ucusta.
ℹ️ Anahtarsiz PSI REST ucu **8 denemede de HTTP 429** verdi; sayilar PSI'nin web arayuzunden
gorsel-sinif isciye okutuldu, uydurulmadi.

## ✅ R2 AVIF WHITELIST'I + BANNER AVIF KOLU main'e ALINDI — 9 Agu 00:47 (merge `b7cdc015`)
Dal `claude/intelligent-nightingale-d5e9fb` (`6c584514`) **merge commit'iyle** alindi: ff IMKANSIZ (`--is-ancestor` rc=1), cakisma 0 (`merge-tree` yalniz agac OID'i), kapsam 8 dosya +757/-59, `urunler.json` ve gizli kayit diff'te YOK, sizinti taramasi temiz, force YOK. Dal + worktree TEMIZLENDI (`durum.py` "ucu main'de").
**1) R1 sihirli-bayt whitelist'i AVIF'e acildi** (`tools/r2-upload.py`): kabul MARKAYA bagli — `data[4:8]=="ftyp" AND data[8:12] in (avif,avis)`. `ftyp` TEK BASINA yeterli SAYILMAZ (mp4/mov/heic ayni ISO-BMFF kutusunu tasir); R2-R6 kollarina DOKUNULMADI, bilinmeyen govde HALA reddediliyor. Kabul testi AA1-AA8 (avif/avis KABUL · mp42/heic/kesik-marka/yanlis-ofset RED · cop/HTML RED): **GECTI=91 KALDI=0**. Yeni `tools/r2-avif-mutasyon-test.py`: **6/6 mutant TEK BASINA KIRMIZI** (marka kontrolu kalkti · kume HEIF'e genisledi · sabit offset ARAMA'ya dondu · esitlik PREFIX'e dondu · AVIF kolu dustu · `.avif` uzanti kolu dustu) + KONTROL mutanti (marka demetinin SIRASI) YESIL. `nobet.yml` serit-b adimi + `SERIT_B` beyani + `TABLO_TABANLARI` 86→87 AYNI commit'te; is-akisi kapisi rc=0 (olculen kapi cagrisi 250→251).
**2) Banner AVIF kolu:** R2'ye **15 YENI** anahtar (`-v2-<genislik>.avif`), ezme 0 (kuru prova 15/15 "YENI"). Canli teyit 15/15 **200 + image/avif**; kontrol ekseni (bilerek yuklenmeyen 3 skan anahtari) **404** → yoklama gercekten olcuyor. Gorsel gercek tarayicida cozuldu (naturalWidth=688). Mobil kume **201,0 → 170,9 KiB (-%15,0)**, LCP gorseli 47220 → 40007 B.
🔴 **Iki yerde OLCUM ISTEGI DUZELTTI:** (a) beklenen kazanc %19 degil **%15,0** — WebP tarafi 201,0 KiB cikinca `e907eac7`'nin sayisiyla birebir tuttu; mobil secim **DPR 1** ile turuyor, DPR 2 varsayimi 216,0 KiB verip 15 KiB'lik SESSIZ sapma birakirdi. (b) **skan-baykus-b5 AVIF'e GECMEDI**: kazanc 448'de %0,0 · 672'de %2,1 · **896'da -%5,8 (AVIF DAHA BUYUK)** → kazandirmayan formati eklemek 3 CDN nesnesi karsiligi sifir fayda, bir basamakta olculmus GERILEME yayinlardi.
**3) Uretim hatti artik REPODA** (`tools/banner-varyant-uret.py`): WebP turunda betik BIRAKILMAMISTI, bu turda kaynak anahtarlar ancak eski bir commit'in `index.html`'inden geri cikarilabildi. Kaynak = ORIJINAL JPEG (WebP'den transcode DEGIL: ikinci kayipli gecis jenerasyon kaybi uretir). R2'ye TEK BAYT YAZMAZ.
**4) `tools/lcp-onculuk-kapisi.py` FORMAT-AGNOSTIK yapildi** — eski ayristirici `type="image/webp"` LITERALINE capaliydi: AVIF `<source>`'lari HIC gormuyordu ve head AVIF'e cevrilince ikiz karsilastirmasini DAIMA WebP'ye yapip YANLIS kirmizi verirdi. Iki YENI eksen, ikisi de "sayfa dogru gorunur ama kazanc SIFIR" sinifindan: **A8 SIRA** (AVIF WebP'den SONRA yazilirsa tarayici ILK destekledigi kolu secer → AVIF ASLA servis edilmez) · **A9 PRELOAD TIPI** (head WebP on-yuklerken govde AVIF seciyorsa LCP gorseli IKI KEZ iner). LCP `<picture>` artik ADLA degil `fetchpriority=high <img>`'i ICEREN blokla bulunuyor. Mutant **8 → 11** (+K1 kontrol), kacan 0.
**Merge kapisi IKI kirmizi yakaladi, ikisi de merge'den ONCE kapandi** (biri yayin dili, biri A5 iddiasinin geri sertlestirilmesi): onarim sonrasi korelme kontrolu yapildi (kapsam DEGISMEDI) ve ayirt edici **M11** mutanti eklendi. Tam dokum: DEVAM-ARSIV.md.
**Merge sonrasi kapilar:** `d1-sync --durum` DORT eksen YESIL (**22772 == urunler.json benzersiz**, hash uyusmaz 0, eksik 0 / fazla 0, sema + 5 turetilmis kolon GUNCEL) · ci-kapsam rc=0 · kapi-envanteri **7/7** · kisisel-veri rc=0 · lcp-onculuk rc=0. CI'da yeni adim POZITIF iz ile dogrulandi: `serit-b` **adim 17 success** (yoklugu kanit saymadim).
ℹ️ `serit-b` koşumu (`31285092533`, head `bb2c6d9f`) failure ama **benim adimim degil** — dusen adim "Kanca kablolama kabul testi"; kardes dalin kancaya ekledigi yeni adim, kancayi sentetik depoda kuran kapinin ELLE tutulan arac listesini bayatlatti (kayitli, tekrar eden sinif). Yayini BLOKLAMAZ, sahibi o dal.
🔴 **`deploy` / canli HTML OLCULEMEDI (uydurulmadi) — sebep merge DEGIL, onceden var olan yayin ACLIGI:** `durum.py` §9 rc=4 (6 ardisik iptal · canli main'den 14 commit geride · en eski bekleyen 120 dk). `Build & deploy`'un son **8 koşumu ust uste cancelled**; ilerleyen tek koşum `31284643156` (head `062f8cb2`) ve o benim isimi **TASIMIYOR** (`--is-ancestor` rc=1) → yesile donse bile kanit SAYILMAZ. Isimi tasiyan `31286289520` (head `cbeb18e0`, `--is-ancestor` rc=0) kuyrukta `pending`. `rerun` TETIKLENMEDI: kuyruga bir koşum daha eklemek acligi artirir.
**SONRAKI TURUN ILK ISI:** `b7cdc015`'i ATA olarak tasiyan bir `Build & deploy` koşumu `success` olunca canlida olc — ana sayfada `type="image/avif"` **5** ve `marin-slide-1-v2-688.avif` **2** (head preload + govde source) cikmali; cikmiyorsa CANLI BAYAT. SIFIRDAN TESHISE BASLAMA, 15 AVIF nesnesi CANLI ve dogrulandi.

## ✅ KATALOG ALAN KAPISI main'e ALINDI — 8 Agu 22:35 (merge `bdddaee0`) — dokum ARSIVDE
Dal `claude/suspicious-ishizaka-414f35` merge commit'iyle alindi (ff IMKANSIZ, cakisma 0, kapsam 9 dosya +1054/-1). Merge sonrasi kapilar rc=0, D1 dort eksen YESIL. Yan etkisi (kardes fikstur ikizi) ve daha eski defter-sinifi kirmizisi KAPANDI. Tam dokum: DEVAM-ARSIV.md.
## 🔚 OTURUM KAPANISI — 8 Agu (yayin blokaji + marka sayfasi turu)

**CANLIYA GITTI (SHA'larla, hepsi `origin/main` ve canli olcumle teyitli):**
- `d3fbc1e5` — `tools/cgt-ekle.py`'deki modul-seviyesi **sabit `/Users/okan/dev/pruvo` koku** `__file__`'den turetildi. Bu kusur `serit-a3` **adim 60**'i kirmiziya cevirip `deploy`+`yayin`'i **skipped** yapiyordu. 🔴 Ders: bu sinif **yerelde ASLA kirmizi yanmaz** (temiz `git clone`'da bile yesil) → [[sabit-mutlak-yol-yerelde-yesil]].
- `b36c208b` — sinifi kapatan **`tools/mutlak-yol-kapisi.py`** (report-only, kanonik kume **203** CI'da fiilen kosan dosya) + ayni kusurun bulundugu **8 dosya** onarildi (biri `thing-hazirla.py`, tam adim 60'in zincirinde). Kardes oturumun "128 kalem kasitli" beyani **22 dosyada curutuldu**.
- `36d57ce6` — `tools/yayin-kapisi.py`'nin **kor yesili** kapandi: taslak yoksa hicbir sayfa olcmeden `success` veriyordu. Artik 4 kaynakli yuzey + uc jeton (YESIL=0 / KIRMIZI=1 / **OLCULEMEDI=2**) + kullanim hatasi 64 + yasa bagli rollout affi + soft-404 govde isareti; capa **`build.py::product_url` FONKSIYONUNDAN** cagriliyor. **223 iddia**, DORT tur bagimsiz curutme.
- `d81349b6` — `BASLIK_DOGAN_ALLOW` **elle envanteri (185 kayit) TURETMEYE cevrildi** (kalinti 102, gerekceli). 6. kez tekrarlayan drift sinif olarak kapandi; `serit-a2` adim 30 + `serit-a4` adim 5 kirmizilari yesile dondu. Sayfa/arama **kimlik** kumesi bit bit ayni (kova 950/950 · baslik-dogan 327/327 · urun→model uyelik 14078), 56 sorguda bosalan 0.
- `e94433f9` — **oksuz CI kablosu DEVRALINDI** (4 tur cagriya cevap gelmedi, mtime 4+ saat): `deploy.yml` serit-a3'e `d1-uzlastirici-kosul-test.py`, `nobet.yml` serit-b'ye `mutlak-yol-kapisi.py`. `serit-a3` **success** → yayin acildi.
- **YAYIN ACIK (canli olcum):** artefakt `21:23:07Z` → **`05:48:50Z`**; canli katalog **22376 == yerel 22376** (mahsur **157** urun sifirlandi); ana sayfa + en yeni 3 urun + kontrol urunu **200**; `d1-sync --durum` **dort eksen YESIL**.
- **Codex** (limitler yenilendi, devrede): 8 zombi dal silindi (yerel dal 20→12), uc kosullu kapiyla; worktree 7/7 ve calisma agaci dokunulmadan AYNI.

**KOSUYOR:**
- 🔧 `muh/marka-tek-sayfa` (worktree `.claude/worktrees/muh-marka-tek-sayfa`, commit `c02edb79`+) — **Okan'in hukmu:** marka sayfasi markanin TUM parcalarini kart listeler, cipler **sayfa ici filtre**. Olculen kusur: **9897 urun kartinin HICBIRI gorunmuyordu**; gorunur kart **11731 → 21628** (audi 200→331 · ford 488→2583 · bmw 1010→2347), **azalan marka 0**, kimlik sapan sayfa **32 → 0**, tavani asan sayfa **11 → 0**. Bagimsiz curutme 1. turda **MERGE_EDILEMEZ** verdi (C1 yuzey ekseni TEMIZ: mukerrer 0 · gecersiz id 0 · yanlis marka 0 · olu id 0), UC kirmizi kapatildi: (1) teslim yolu **tautolojisi** — test fetch URL'ini sayfanin kendi beyanindan okuyordu, artik `index.html`'den bagimsiz cikarilan `EDGE_UC` ile karsilastiriliyor; (2) **agirlik regresyonu** — artim kolu `/urunler.json` (3,3 MB gzip) cekiyordu, ana sayfanin kullandigi **edge `/katalog?ids=`** yoluna (100'luk parti) alindi, ilk acilista veri istegi 0; (3) `ci-kapsam-test.py` yesil→kirmizi — iki yeni nobetci `nobet.yml` **serit-b**'ye kablolandi (deploy:needs'te DEGIL), kapi YESIL. Iddia **10871**, davranis testi **20/20**.
  ⏭ **SIRADAKI TEK IS:** mutasyon bataryasi + ilk-yuk bayt tablosu gelince → **dar curutme (yeni yuzey)** → **merge + canli dogrulama** (Okan yetki verdi).

**BEKLIYOR (kim neyle bloke):**
1. `muh/yayin-acan-iki-kirmizi` (`1cb3ee6c`, worktree acik) **MERGE EDILMEDI** — butce asimi main'de YOK (22337 katalogda 153112 ≤ 153600) ve kardes oturumun "butce YUKSELTILMEZ, ozet.json deterministik SIGDIRILACAK" karariyla celisiyor. Kurtarilacak kismi: `faz3-yuk.js` **ikiz sabit turetmesi** + `ozet_olcek_dokumu`/`ilk_yuk_dokumu` tani ciktisi. **Codex'e uygun.**
2. `tools/mutlak-yol-kapisi.py` **5 sessiz kacirma** (f-string · `+` ile parcali kok · `os.path.join("/Users",…)` · `expanduser("~/…")`) + 4 yanlis-pozitif → **`--sifir-tolerans` BLOKLAYICI YAPILMAYACAK** (karar bende) ta ki kacirma sinifi kapanana kadar.
3. `tools/yayin-kapisi.py`: `IZIN_LISTESI` muafiyeti **elle 29 kalem** (kanonik turetme yok) + surucuye `--yalniz-mutasyon` kolu → B kolu (12 mutant) su an CI DISINDA.
4. H1/H3 kurali **16 model-olmayan** degeri model sayiyor (`M8x25` · `17mm` · `12V` · `Toyota Honda` …), 2'sinin sentetik olarak **sayfasi dogdu**. main'in mevcut kusuru, ayri is.
5. Sayfa↔arama asimetrisi: basliginda marka gecen ama `marka[]` uyesi olmayan **215 urun** (Mini 42 · Grom 29 · K100 19 · Datsun 18 …). Onarim **VERI duzlemi (MaCiT)**; `arama.py`'deki gecis kolu **ONCE kapatilmayacak** (arama daralir, satis yolu).
6. `serit-a4` **32-58 dk** — yayin tavanini bu job koyuyor (`model-uyelik-kapisi --kendini-test` + turetme alt bataryasi +155 sn). Kaldirac bende.
7. `pages` grubundaki 6/6 job'da `timeout-minutes` YOK (varsayilan 360 dk) — **Okan kapisi**.

**OKAN'DA BEKLEYEN KARARLAR:**
- Kardes mimarin sordugu **satin-alma kalemi** — sorunun tam metni ve kuyruk buyuklugu `DEVAM-ARSIV.md`'de (git disi). Yanit gelmeden o kuyruk islenmez.
- **GPL/LGPL/BSD satilabilir mi** (MaCiT'te bu yuzden RED edilen kayitlar var).
- Ortak Drive yedeginin kokunde **3 bayat kalem** (Temmuz tarihli); hedef ORTAK surucu → erisim cevresi olculmeli, yenileme karari Okan'in.
- `pages` job'larina `timeout-minutes` konmasi.
- ℹ️ Nobet jetonu icin **`setup-token` GEREKMIYOR**: 18:37Z rc=1'in sebebi jeton bayatligi degil eski hesabin **haftalik kotasiydi**; 19:37Z ve sonrasi rc=0.

**ACIK WORKTREE (2 + main):** `agent-aa5db29d7f2d4d1ad` ve `muh-mcp-tarayici` — IKISI DE BASKASININ CANLI isi, DOKUNULMADI. Benim actigim worktree KALMADI (8 Agu 15:00 turunda kapatildi).

## ✅ NOBET NOBETCILERI SERTLESTI — dal main'e ALINDI (8 Agu 22:20, dokum ARSIVDE)
Merge --ff-only d9485a0d, kapsam 3 dosya +589/-61, sizinti 0. Olu koruma 48 birim kapatildi (tablo 18/18, pay 0). Merge sonrasi kapilar: D1 dort eksen rc=0 (22685) · CI kapsam rc=0 (246 kesif) · is-akisi rc=0 + kendini-test rc=0 (204 iddia) · nobetci mutasyon 7/7 + kontrol YESIL. Ders: ff uygunlugu YEREL main ile olculur. Temizlik bilerek yapilmadi. Tam dokum: DEVAM-ARSIV.md.
## ⏱ SAATLIK CI NOBETI — 9 Agu 01:37Z turu (ev DOGRU: ~/dev/pruvo)

**Supurme (kosulsuz, §0.5):** kutu toplami **7538** · `notifications@github.com` toplami **1** ·
"Run failed" eslesen **1** → Cop'e **1** · tur sonu kalan **0**. Pozitif tanima izi VAR
(github toplami 0 degil) → hukum "kutu temiz", OLCULEMEDI degil. `contains` ile toplu tarama,
ornekleme YOK, alt kutulara girilmedi, Cop BOSALTILMADI.

**Kapanan iki kirmizi (bagimsiz olculdu, mimar `gh`):**
1. `serit-b` — 23:56 / 00:29 / 00:44 kosumlari failure idi; `3e7f1b24` (00:45) ve `29e9355f`
   (01:07) **success**. Sinif kapandi, mudahale gerekmedi (yoldan gecen yesil DEGIL: iki ayri
   commit'te ust uste yesil).
2. `D1 uzlastirici` — 00:34 kosumu `31286467555` failure. Logdan kok neden: onarimdan SONRA
   SAYI ekseni 22772 == 22772 ✅ okurken ICERIK ekseni ayni adimda 22792 satir okuyup ayni 20
   id'yi "D1'de FAZLA" saydi — yani **tek kosum icinde iki eksen birbiriyle celisti**
   (silme sonrasi bayat okuma sinifi). Bagimsiz teyit (`d1-sync.py --durum`, mimar eliyle,
   01:30Z): **23034 == 23034 · hash uyusmaz 0 · eksik 0 · fazla 0 · dort eksen ✅**. Sinif SU AN
   temiz → yama YAPILMADI. ⚠️ SONRAKI TUR: bu is akisinin yeni kosumu YINE ayni celiskiyle
   duserse tekrar eden sinif sayilir ve muhendislik isi acilir (tek olay icin acilmadi).

**ACIK KIRMIZI — YAYIN ACLIGI (muhendise DEVREDILDI, dal ustunde).**
`Paket tazeligi alarmi` / `yayin-nabzi` ARDISIK 2 kosumdur kirmizi (23:44 `31284655993`,
01:38 `31288690972`). Alarmin kendi hukmu: **ACLIK (cikis 4)** — canli main'den **13 commit
geride**, en eski bekleyen **53 dk** (esik 50), **6 ardisik iptal** (esik 6), ardisik hata 0.
Ayirt edici olcum: kuyrukta iptal (zararsiz) 12 · CALISIRKEN iptal 1 · build yesil ama deploy
kosmadi 4. Yani §4.5'teki "cancelled yigini zararsizdir" hukmu BURADA GECERSIZ — alarm
zararsiz kuyruk iptalini zaten ayirmis, kalan sinif gercek.
**Kok neden (dogrulanacak hipotez):** zincir ~48-53 dk (tavan `serit-a4`, bunun ~34 dk'si tek
adim), itmeler ~13-20 dk arayla → kuyruktaki `deploy` her seferinde daha yeni itmeyle dusuyor.
Son yayinlanan sha `062f8cb2` (00:46Z). **Esiklere DOKUNULMADI** (alarm dogru olcuyor).
Muhendise verilen is: tavani DUSUR, iddia sayisini KUCULTMEDEN; gevsetme/adim silme/
`continue-on-error`/`needs` daraltma/`cancel-in-progress` degistirme YASAK; main'e push YASAK,
teslim dalda `RAPOR-MIMARA.md` + `TAVAN_ONCE_SN` / `TAVAN_SONRA_SN` / `IDDIA_ONCE` /
`IDDIA_SONRA`. **SONRAKI TURUN ILK ISI:** o dalin raporunu oku, merge-kapisi ile tart —
sifirdan teshise BASLAMA.

**OLCULEMEDI (uydurulmadi):** guncel head `6b15062b` icin `deploy`/`yayin` — kosum
`31288785522` tur sonunda hala `pending`.

**Bu defter blogu commit EDILDI, PUSH EDILMEDI — bilerek.** Gerekce olculdu: `31288785522`
su an kuyrukta ve YENI bir itme onu dusurur; yani "defteri hemen it" refleksi bu turda
teshis edilen acligi BIR TUR daha uzatirdi. Commit main'de bekliyor, sonraki icerik
itmesiyle birlikte gider. Sonraki tur: bu blok hala itilmemisse ve `deploy` bir kez
yesillenmisse it.

## ⏱ SAATLIK CI NOBETI — 8 Agu 23:37Z turu (ev DOGRU: ~/dev/pruvo)

**Supurme (kosulsuz, §0.5):** eslesen "Run failed" **0** → Cop'e **0**. Pozitif tanima izi
ALINDI: ayni tarama `sender contains "github"` ile **1** mail buldu (GitHub destek bildirimi,
"Run failed" DEGIL) → eslestirici CALISIYOR; buna karsin `notifications@github.com` toplami
**0**. Kural geregi 0/0 kombinasyonu "kutu temiz" DEGIL → hukum **OLCULEMEDI** yazildi.
Kutu toplami 7537. Yalniz birlesik `inbox`, `contains` ile toplu tarama, ornekleme YOK,
Cop BOSALTILMADI, alt kutulara girilmedi.

**IKI AYRI KIRMIZI ELE ALINDI (biri yayini durduruyordu).**

**1) `serit-b` / diriltme kabul testi — KAPANDI.** Kosum `31282011513` (head `bdddaee0`)
failure; kok neden fikstur ikizi (sentetik kanca ortami gercek repo seklini taklit etmiyordu),
kapinin kendisi DOGRUYDU. Onarim kardes oturumun `e56705a2` surumuyle main'de: elle liste
kaldirildi, arac kumesi kanonik kaynaktan TURETILIYOR, fail-closed. Iddia **86 → 89**, kucul-
me yok. Bagimsiz teyit (mimar, `gh`): kosum `31283328805` (head `e56705a2`) `serit-b` **success**.

**2) `serit-a2` + `serit-a3` (defter sinif kapisi) — YAYINI BU DURDURUYORDU, KAPANDI.**
`deploy` + `yayin` **skipped** kaliyordu; son BASARILI deploy `62c7049b`, `22:10:13Z` → yayin
~1 saat kapali. Kok neden defterin KENDI icerigiydi (tani satiri deftere yazilmis); satir
silinmedi, arsive TASINDI. `serit-a3` ayri bir mantik kusuru DEGILDI — ayni ihlali olcuyordu.
Asil sinif kusuru: kapinin tek zorlayici kolu CI'daydi, ihlal ancak PUSH SONRASI yakalaniyordu
(5. tekrar). Onarim `bb2c6d9f`: commit aninda **INDEX ekseninde** olcen yeni kol eklendi
(CI kollari AYNEN duruyor, `deploy: needs` degismedi, gevsetme/`continue-on-error` YOK; yeni
kol CI'nin YERINE gecmiyor, ONUNDE duruyor). Kendini-test **62 → 70 kontrol**, mutasyon
bataryasi **15 → 19 mutant** (kontrol mutantlari yesil kaldi), kanit KUCULMEDI. Uctan uca
gercek commit denemesi: ihlal INDEX'te rc=1, ayirt edici notr kontrol rc=0.
Bagimsiz teyit (mimar, `gh`): kosum `31284643156` (head `062f8cb2`) `serit-a2` **success** +
`serit-a3` **success** + `build` success.

**OLCULEMEDI (uydurulmadi):** `deploy` / `yayin`. Tavani yine `serit-a4` SURESI koyuyor —
`31284643156`'da hala ucusta; `31285092474` (head `bb2c6d9f`) kuyrukta `pending`
(`concurrency: pages` + `cancel-in-progress: false`, §4.5 — `cancelled` yigini ariza degil).
Tur ici bekleme tavani (§3.5) doldu.

**BU DEVIR KAPANDI (01:37Z turunda olculdu):** `31284643156` alti isin ALTISI da `success`
(`serit-a2` · `serit-a3` · `serit-a4` · `build` · `deploy` · `yayin`). `31285092474` `cancelled`
+ `jobs: []` = kuyruk davranisi (§4.5), icerigi kayip DEGIL.

## Onceki turlarin VE 7 Agu oturumunun TAM dokumu — ARSIVDE (DEVAM-ARSIV.md, git disi).
