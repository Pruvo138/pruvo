# DEVAM (KraL) — 8 Agu 2026

## 🧹 WORKTREE + ARTIK ENVANTERI — 8 Agu 15:00 turu KAPANDI (dokum ARSIVDE)
Worktree 8 -> 3, izlenmeyen artik 7 -> 0, uc kalem .gitignore'a alindi (0e918189). Kaldirilan 6 kaydin nereye gittigi, iki bayat "bekleyen" kalemin curutulmesi ve worktree-ici commit "BAYATTI" tuzagi: DEVAM-ARSIV.md.
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

## ⏱ SAATLIK CI NOBETI — 8 Agu 20:37Z turu (ev DOGRU: ~/dev/pruvo)

**Supurme (kosulsuz, §0.5):** eslesen "Run failed" **2** → Cop'e **2** · tur sonu kalan **0**.
Pozitif tanima izi: ayni taramada `notifications@github.com` toplami da **2** (>0 → hukum
OLCULDU). Birlesik gelen kutusu `contains` ile toplu tarandi, ornekleme YOK; Cop BOSALTILMADI,
alt kutulara girilmedi, baska maile dokunulmadi.

**Onceki turun ILK isi KAPANDI — kok neden 2 (izinsiz altkategori) MaCiT tarafindan onarildi.**
`609f0e70` sha'sinda `serit-a2` **success** (20:09:32Z → 20:26:24Z). Sifirdan teshise girilmedi.

**Uctaki kosum `31274951249` (sha `609f0e70`) — YARIM:** `build` success (20:09:31→20:22:36Z) ·
`serit-a2` success · `serit-a3` success (→20:24:28Z) · **`serit-a4` HALA UCUSTA** (20:09:32Z'den
beri; 20:55Z'de gorulen adim "Model baslik kolu mutasyon bataryasi"). `deploy`/`yayin` job'lari
HENUZ OLUSMADI — **yok ≠ basarisiz**. Tur ici bekleme tavani (~25 dk, §3.5) doldu.

**Kirmizi alarm kolu GERCEK ARIZAYI gosteriyor, yayini BLOKLAMIYOR:** "Paket tazeligi alarmi"
15:04:47Z'den beri kesintisiz **9 kirmizi** (son yesil 14:38:59Z, sha `7af8b137`). Kok neden:
`yayin-nabzi` job'unun `tools/yayin-gecikme-nobeti.py --alarm` adimi **rc=3** — log: "taranan 8
kosumda YOK (pencere 40)", yani penceredeki hicbir kosum `deploy`'u basariyla bitirmemis.
Bagimsiz teyit: son 15 `deploy.yml` kosumunun HICBIRI `deploy`'u yesil bitirmemis. Bloklamama
kaniti: workflow `on:` yalniz `schedule`+`workflow_dispatch`, `deploy.yml`'de `needs:` bagi YOK,
ayri `concurrency` grubu. → Alarm dogru calisiyor; zincir yesile donunce kendiliginden soner.

**20:54:32Z'de yeni push geldi** (kosum `31278032695` kuyrukta). `concurrency: pages` +
`cancel-in-progress: false` → KOSAN zincir korunur, yalniz kuyruktaki duser; icerik kaybolmaz
(§4.5 — `cancelled` sayma, SUREDEN olc).

**Sonraki turun ILK isi:** `31274951249`'un `serit-a4` sonucunu ve `deploy`/`yayin` job'larini
olc. Yesilse canli teyit (artefakt zaman damgasi + canli katalog sayisi + en yeni 3 urun 200) ve
"Paket tazeligi alarmi"nin kendiliginden yesile donup donmedigini olc. Kirmiziysa `--log-failed`
ile kok neden. **SIFIRDAN TESHISE BASLAMA.**

## ✅ NOBET NOBETCILERI SERTLESTI — dal main'e ALINDI (8 Agu 22:20, dokum ARSIVDE)
Merge --ff-only d9485a0d, kapsam 3 dosya +589/-61, sizinti 0. Olu koruma 48 birim kapatildi (tablo 18/18, pay 0). Merge sonrasi kapilar: D1 dort eksen rc=0 (22685) · CI kapsam rc=0 (246 kesif) · is-akisi rc=0 + kendini-test rc=0 (204 iddia) · nobetci mutasyon 7/7 + kontrol YESIL. Ders: ff uygunlugu YEREL main ile olculur. Temizlik bilerek yapilmadi. Tam dokum: DEVAM-ARSIV.md.
## Onceki turlarin VE 7 Agu oturumunun TAM dokumu — ARSIVDE (DEVAM-ARSIV.md, git disi).
