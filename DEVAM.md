# DEVAM (KraL) — 8 Agu 2026

## 🧹 WORKTREE + ARTIK ENVANTERI KAPANDI — 8 Agu 15:00 turu

**Worktree 8 → 3** (kalan 2'si BASKASININ CANLI isi, ucuncusu ana checkout).
Kaldirilan 6 kayit ve isin nereye gittigi:
- `agent-a3bff0d31c85f5714` → commit'siz 5 dosya (792 ekleme) **commit'lendi + itildi**
  (`worktree-agent-a3bff0d31c85f5714`, yeni uzak dal); dal SILINMEDI. Merge hukmu YOK.
- `muh-marka-tek-sayfa` → commit'siz 6 dosya (468 ekleme) **commit'lendi + itildi**
  (`muh/marka-tek-sayfa` `c02edb79`→`73adb519`); dal SILINMEDI, uctaki is korundu.
- `agent-ad8653d553f9bde31` (`muh/marka-bolum-kimligi`) → dal uzakla ESIT, **dal SILINMEDI**
  (Okan'in hukmuyle celisiyor, MERGE EDILMEYECEK); izlenmeyen 8 olcum betigi silinmedi,
  `.claude/olcum-arsiv/` altina TASINDI (32 KB).
- `agent-aecb6db6145c47ad2` (`muh/yedekle-desen-kilidi`) → temizdi, ucu main'in ATASI
  (`--is-ancestor` rc=0) → worktree + **yerel dal SILINDI** (uzak duruyor).
- `blissful-mcnulty-e7162d` (detached `76ca1341`) → temizdi, commit main'in ATASI → kaldirildi.
- `muh-yayin-iki-kirmizi` (`muh/yayin-acan-iki-kirmizi` `1cb3ee6c`) → temiz, uzakla ESIT,
  main'de DEGIL (1 ileri) → kaldirildi, **dal SILINMEDI**.
- 🔴 **DOKUNULMADI:** `agent-aa5db29d7f2d4d1ad` (`muh/erisim-5xx-tekrar`) — kirli ve sahibi
  ~50 dk once yaziyordu; isi kaybolmasin diye commit'lendi + itildi (`39600935`, 304 ekleme)
  ama worktree BIRAKILDI. Tur sirasinda ucuncu bir worktree (`muh-mcp-tarayici`) BASKA bir
  oturum tarafindan acildi (3 dk once, kirli) — dokunulmadi.

**Izlenmeyen artik 7 → 0** (`git status --short` = **1 satir**, o da bu turun kendi commit'i
oncesiydi; simdi **0**). Hicbir sey kaybolmadi:
- 4 adet `shop/src-fiyat-tmp-*` **silindi** (21,7 MB; uretilebilir mutasyon kopyasi,
  `tools/` + `.github/` icinde referans **0**).
- `.scratch-ci-nobeti/` **DURUYOR** — o an (3 dk once) yaziliyordu, canli oturum.
- `.scratch-ozet/` + `urun-gorsel-koken/` **DURUYOR** — koken manifestlerinin kanonik evi
  kardes depo, oradaki listede bu 2 kayit **YOK** (benzersiz).
- `0e918189` — ucu birden `.gitignore`'a alindi (`.scratch-*/`, `urun-gorsel-koken/`,
  `shop/src-fiyat-tmp-*/`): diskte durur, izlenmez, bir daha baska mimarin temizlik
  olcumunu kirletmez.

**Iki "bekleyen" kalem OLCULDU, ikisi de KAPALI (liste bayatmis):**
- `tools/arama.py` **TEMIZ** (porcelain bos); son commit'i zaten `d81349b6` (main'de, rc=0).
  `model-baslik-kolu-test.py` **rc=0 · 29/29 iddia GECTI** → calisma kopyasi = HEAD, catisma YOK.
- 4 dosya (`deploy.yml` · `nobet.yml` · `cron-nabiz-kapisi.py` · `is-akisi-kapisi.py`)
  ana checkout'ta **commit'siz DEGIL** — hepsi temiz.

**Yayin ACIK (olculdu):** son basarili `Build & deploy` = **`31253585287`** (head `2dba2718`,
bitis **11:55:14Z**). `c61bd9b7` o yesil kosumda **YOK** (`--is-ancestor` rc=1); kendi kosumu
(`31256056859`) `serit-a3`'te kirmizi yandi → `deploy`+`yayin` **skipped**. Ama `c61bd9b7`
main HEAD `39df8c98`'in ATASI (rc=0) ve onun kosumu (`31256999280`) **UCUSTA** → commit ucusta,
yayin kapali DEGIL. "21:24:13Z'den beri kapali, 12 commit inmedi" hukmu **CURUTULDU**.

**`d1-sync --durum` DORT EKSEN YESIL:** sayi 22476 == urunler.json benzersiz 22476 · sema
3 goc indeksi KURULU · turetilmis kolon 5/5 GUNCEL · icerik 22476 urun_hash birebir
(uyusmaz 0 · eksik 0 · fazla 0).

⚠️ **YENI TUZAK (dokumu ARSIVDE):** worktree icinden atilan commit kanca kurulumunu
tetikliyor; ilk commit denemesi hep "BAYATTI, tekrar dene" ile duser, ikincisi gecer.
Tur sonunda ana checkout'ta `durum.py` §8 **13 eksen yesil** ile teyit edildi.

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

## ⏱ SAATLIK CI NOBETI — 8 Agu 13:37Z turu (ev DOGRU: ~/dev/pruvo)

**Supurme (kosulsuz, §0.5):** eslesen "Run failed" **1** → Cop'e **1** · tur sonu kalan **0**.
Pozitif tanima izi: ayni taramada `notifications@github.com` toplami da **1** (>0 → hukum
OLCULDU, "olculemedi" degil). Inbox 7541 mesaj TOPLU tarandi (`contains` ile, ornekleme YOK);
Cop BOSALTILMADI, alt kutulara girilmedi, baska maile dokunulmadi.

**Tek kirmizi PENCERE-GORELI cikti — Codex CAGRILMADI, kod DEGISMEDI.**
Kirmizi: kosum `31258673406` (13:03Z), tazelik alarmi workflow'unun nabiz kolu; kardes is yesil.
Betigin BES ekseninden yalnizca BIRI asilmisti: "en eski bekleyen commit yasi" **69 dk**
(esik 65 dk). Diger dordu TEMIZ: ardisik iptal 2/6 · ardisik hata 0/4 · ardisik yayinsiz 0/2 ·
en uzun kosan kosum omru 44/75 dk. Ardisik kirmizi **1** (ayni kol onceki 5 kosumda success)
→ DUR kosulu tetiklenmedi. Alarmi gevsetme / esik buyutme / susturma YAPILMADI.

**Sinif TAHMINLE degil OLCUMLE kapandi:** izlenen yayin kosumu `31256999280` **success**
(kirik is YOK) → yayinlanan sha `2dba2718` → **`39df8c98`** ilerledi, yani alarmin yas tabani
sifirlandi. Ardindan `31259572161` (head `70fe3e4c` = main HEAD) uctu.
§4.5'in uc ekseni de olculdu: (a) kosan zincir VAR · (b) tavani yine **serit-a4** koyuyor:
**60 dk** — onceki turlarda olculen 32-58 dk bandinin USTUNDE ve alarmin 75 dk omur tavanina
15 dk kalmis (izlenecek kalem: esik degil SURE) · (c) son yesil yayin main'in atasi, kuyrukta
bekleyen tek kosum guncel HEAD'i tasiyor.

## ✅ NOBET NOBETCILERI SERTLESTI — dal main'e ALINDI (8 Agu 22:20 turu)

**Merge `--ff-only`: `d9485a0d`** (merge-base `f6aaabf8` = main ucu; `is-ancestor` rc=0 ile
kanitlandi). Push `f6aaabf8..d9485a0d`, yalniz bu dalin 5 commit'i. Kapsam **3 dosya
+589/-61**, eklenen/silinen dosya YOK, sizinti taramasi **0 vurus**.

Ilk denemede merge YAPILMADI: dal `origin/main`'e gore ff-able olmasina ragmen YEREL main
2 commit ilerideydi (baska oturumun itilmemis isi) -> `--ff-only` reddedilecekti. Dal yerel
main'e yeniden taban aldi, sonra ff temiz gecti. **Ders:** ff uygunlugu `origin/main` ile
degil YEREL main ile olculur (`merge-base --is-ancestor main <uc>`).

**Kapatilan olu koruma 48 birim** (tam-esitlige cevrilen sayaclar): tablo payi 5 + G payi 1
+ kendini-test taban payi 42. Tablo artik **18/18, pay 0**. Surucu bataryasi: **7 oldurucu +
3 kanarya + 5 ayirt edici** mutant; iki checkout seklinde de yesil.

**Merge SONRASI kapilar (ana checkout, her biri ayri rc):**
- D1 durum **rc=0** — D1 == urunler.json benzersiz **22685**; sema, turetilmis kolon ve
  icerik eksenleri temiz (hash uyusmaz 0 · eksik 0 · fazla 0)
- CI kapsam **rc=0** — kesfedilen kabul testi 246, otomatikte kosan 191
- Is akisi kapisi **rc=0** (olculen kapi cagrisi 248 · etkisizlestirilmis 0) ·
  `--kendini-test` **rc=0** (204 iddia)
- Nobetci mutasyon **rc=0** — `oldurulen=7/7 · kontrol=YESIL · 15 varyant · 349 sn`
  (iki bagimsiz kosumda tekrarlandi: 351 sn ve 349 sn)

**CI: merge SHA'sini BIREBIR tasiyan 6 kosum var** (`headSha` esit); 4'u success, yayin
zinciri ile nobet seridi olcum aninda **hala kosuyordu -> o eksen OLCULEMEDI** (uydurulmadi).
Yayin kilidi bu dalin DISINDA: onceki sha'da da deploy kirmiziydi, kok neden ustteki turda
yazili ve baska bir mimarin duzleminde.

**Temizlik YAPILMADI (bilerek):** hicbir worktree/dal silinmedi, bu dalin worktree'sinde
aktif oturum var. Envanter: 4 aktif worktree, 16 dal (2'si ucu main'de).

## Onceki turlarin VE 7 Agu oturumunun TAM dokumu — ARSIVDE (DEVAM-ARSIV.md, git disi).
