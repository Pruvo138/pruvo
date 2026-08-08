# DEVAM (KraL) — 8 Agu 2026

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

**ACIK WORKTREE (5 + main):** `muh-marka-tek-sayfa` (KOSUYOR, benim) · `muh-yayin-iki-kirmizi` (bekliyor, benim) · `agent-a3bff0d31c85f5714` · `agent-ad8653d553f9bde31` (`muh/marka-bolum-kimligi` — Okan hukmuyle CELISIYOR, karti 200→174 dusuruyor, MERGE EDILMEYECEK) · `agent-aecb6db6145c47ad2` · `blissful-mcnulty-e7162d` (son dordu **baskasinin**, DOKUNULMADI).

## ⏱ SAATLIK CI NOBETI — 8 Agu 10:37Z turu (ev DOGRU: ~/dev/pruvo)

🔴 **ONCEKI UC TURUN "KUTU TEMIZ" HUKMU CURUTULDU — supurme SESSIZ SIFIR KAPSAMLA gecmis.**
07:37 · 08:37 · 09:37 turlari "tasinan 0" yazdi; 09:37 bunu "inbox 7546 mesaj TOPLU tarandi,
ornekleme YOK" diye gerekcelendirdi. Kapsam dogruydu, **ESLESTIRICI** tutmuyordu: Mail'de `sender`
gorunen adi da tasir (`GitHub <notifications@github.com>`) → tam esitlik hicbir zaman tutmaz.
Bu turda `contains` ile bakilinca kutuda 7 Agu'dan kalma **30** "Run failed" maili cikti.
**Tasinan 30 · tur sonu kalan 0** (Cop BOSALTILMADI, alt kutulara girilmedi, baska maile
dokunulmadi). Gorev dosyasina KALICI kural islendi: substring zorunlu + `TASINAN=0` yazacak tur
daha genis pozitif kumeyi de bassin; o da 0 ise hukum "temiz" degil **OLCULEMEDI**.

**Gercek ariza YOK — Codex CAGRILMADI.** `--status failure` ile son 40 kosum tarandi: en yeni
kirmizi `31245852100` (07:18Z, uzlastirici GORUNURLUK kolu). 07:18Z'den bu yana `failure` **0**.

**Yayin ILERLEDI (§4.5'in UC ekseni de olculdu):**
(a) KOSAN zincir VAR: `31251166602` (head `85e3e523` = main HEAD), push 09:42:37Z.
(b) Tavani yine **`serit-a4`** koyuyor: ayni kosumda `serit-a3` 10:05:28 · `build` 10:06:59 ·
`serit-a2` 10:14:49 **success**; `serit-a4` 09:54:02'den beri `in_progress` (~44 dk; olculen tipik
bant 32-58 dk) → normal seyir, TIKANMA DEGIL.
(c) Son basarili `Build & deploy` = **`31249072863`** (head `af02f7c1`, bitis 09:53:53Z) → onceki
turun "af02f7c1 ucusta" hukmu KAPANDI, CANLIDA. Ucusta kalan tek commit `85e3e523` (onceki turun
kendi defter commit'i); beklenen.

## ⏱ SAATLIK CI NOBETI — 8 Agu 09:37Z turu (ev DOGRU: ~/dev/pruvo)

**Mail supurmesi (kosulsuz emir):** birlesik `inbox` **7546** mesaj TOPLU tarandi (ornekleme YOK;
sender + subject tek Apple Event ile cekildi, satir sayisi `count of messages of inbox` ile
esitlendi). Eslesen `notifications@github.com` + "Run failed" **0** → tasinan **0** · tur sonu
kalan **0**. Alt kutulara girilmedi, Cop BOSALTILMADI, baska maile dokunulmadi.

**Gercek ariza YOK — Codex CAGRILMADI.** Son 20 kosumda `conclusion=failure` **0**, `cancelled` **0**.
Onceki turun tek kirmizisi (`31245852100`, uzlastirici GORUNURLUK kolu — kasitli `exit 1`)
pencereden dustu; YENI kirmizi YOK.

**Yayin ILERLEDI (§4.5'in UC ekseni de olculdu, tek eksen tek basina yazilmadi):**
(a) KOSAN zincir VAR: `31249072863` (head `af02f7c1` = main HEAD), push tetikli, 08:45:04Z.
(b) Tavani yine **`serit-a4`** koyuyor: ayni kosumda `build` · `serit-a2` · `serit-a3` **success**,
`serit-a4` hala `in_progress` (bu job tipik 32-58 dk surer) → normal seyir, TIKANMA DEGIL.
(c) Son basarili `Build & deploy` = **`31246716497`** (head `82967d41`, bitis 09:08:46Z) → onceki
turun "`9ab89786` + `82967d41` ucusta" hukmu KAPANDI, ikisi de CANLIDA. `merge-base --is-ancestor
af02f7c1 82967d41` **rc=1** → yalnizca onceki turun defter commit'i (`af02f7c1`) ucusta; beklenen.

## Onceki turlarin VE 7 Agu oturumunun TAM dokumu — ARSIVDE (DEVAM-ARSIV.md, git disi).
