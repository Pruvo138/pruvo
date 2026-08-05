# DEVAM (KraL) — 5 Agu 2026

## 🟢 PARITE REFERANSI TEK KAYNAGA BAGLANDI — `82ab7fea` (site↔uc marka sorgusu)

- **Kusur SITE'de DEGILDI, TESTTEYDI.** `tools/parite-test.js`'in elle kopyalanmis
  `norm/haystack/filtered` uclusu, `8913db28` + uctaki gecis sonrasi BAYAT AYNA'ya donmustu.
  Uc yuzey ayri ayri olculdu (uc `/ara` · index.html'in KENDI yuklemi · eski referans):
  mini **69/69**/1134 · haval **2/2**/600 · rover **9/9**/91 · mercedes **1037/1037**/1041 ·
  seat **90/90**/120 · aksanli citroen **413/413**/69. **(a) ile (b) 7/7 BIREBIR.**
- **Musteri kusuru YOK.** Canli `index.html` satir 1629 `EDGE_KATALOG = true` → arama uca
  gider; yerel/yedek kol da AYNI plandan gecer (`aramaPlani(query)` x4, marka-liste-test
  bunu olcuyor). Uretim kodunda **0 satir** degisiklik.
- **AKSAN ekseni ayri kok DEGIL:** eski referansin `norm()`'u aksanli `e`yi sadelestirmiyordu;
  uc de index.html de kanona indiriyor → onarimdan sonra sapma 0.
- **Onarim:** yeni `tools/index-arama-referansi.js` — index.html'in kanonik bloklarini
  AYIKLAYIP `node:vm`'de CALISTIRIR (ikinci yuklem YAZILMADI). Cip indeksi uretim
  ureticisinden gelir (uydurulmaz; index.html o indeks yokken gevsek davranir, uc davranmaz —
  bos gecilseydi cip evreni markalarinda YENI ayrisma dogardi).
- **Fail-closed, dogru birimde:** referans olcumden ONCE kurulur; index.html yok / capa bozuk /
  uretec yok → **rc=3 (OLCULEMEDI)**, kontrol rc=0.
- **Kapilar:** canli `parite-test.js` **1199/1199 rc=0** (onceki tur 33 ayrisim) · mutasyon
  **25/25** · parite-fikstur **226/0** · yayin-fikstur **140/0** · marka-liste **34/0** ·
  ci-kapsam YESIL · kisisel-veri YESIL.
- **Korelme olculdu ve kapatildi:** onbelleksiz surumde uretici surec-basina ~1 sn → mutasyon
  25/25'ten **9/25**'e dustu (yuk, gerileme degil). Taban degismemis agacta 25/25 olculerek
  suclu bulundu, hipotez `PARITE_CIP_INDEKS` ile kanitlandi, iki girdinin damgasiyla
  anahtarlanan disk onbellegi eklendi → onbelleksiz **25/25, 262,1 sn**.
- **MARKA EKSENI (bagimsiz kanit, dal `worktree-agent-a85a9c2f60dce9910`):**
  taban site **69 marka / 6.539 kalem** + uc **77 marka / 4.613 kalem** ayrisikti;
  bugun IKI yuzeyde de **130 olculdu / 130 gecti / 0 ayrisik / 0 olculemedi (rc=0)**.
  Toplam **11.152 kalem → 0**. (Dalin KENDI bayat kataloguyla 4 marka OLCULEMEDI cikiyordu;
  Honda farki tam **126** = dilim 5 → guncel katalogla dordu de kapandi, veri kusuru DEGIL.)
- **D1:** `--durum` uc eksen YESIL — SAYI 19252 = 19252 · SEMA temiz · ICERIK 19252/19252
  (uyusmaz 0, eksik 0, fazla 0). Parite ciktisindaki `canli=19126` **bayat olcumdu**;
  126 urun D1'e INMIS, senkron kosturmaya gerek olmadi.
- 🔴 **ACIK KALEM (BASKA DEPO, dokunulmadi):** `parite-ege.js` hala **rc=1, 35/848** ve
  sapanlarin TAMAMI marka adi sorgusu (24 marka). Sebep: botta IKI govde var — `/ara` D1 yolu
  kurali benimsedi, bellek-ici arama govdesi benimsemedi (ornek: mercedes uc 1037 ↔ 1509,
  haval 2 ↔ 1359). Karar MIMARIN: o govde de gecsin mi, yoksa "Ege semantigi ayridir" diye mi
  kapatilsin.

## CI NOBETI (18:37 turu) — yayin seridi YESIL, 2 mail Cop'e
- Kutu: son ~70 dk'da **5** "Run failed" maili (inbox 7558, toplu cekim, ornekleme YOK).
  Dagilim: **2** yayin seridi + **3** bagimsiz alarm kolu.
- **Yayin seridi (Build & deploy):** `82ab7fea` ve `fac2223b` kosumlarinda `build=success`,
  `serit-a2`/`serit-a3`=failure, `deploy`/`yayin`=**skipped**. Kok neden ikisinde de AYNI ve
  DEVAM.md'nin KENDI satirlarindaki sinif ihlaliydi (kapinin yazdigi cozum: satirlari arsive
  TASI, silme YOK). **Duzeltme zaten `88f111f7` ile inmisti** — bu turda kod DEGISMEDI,
  commit/push YAPILMADI (`DEGISEN_DOSYALAR=YOK`).
- **Bagimsiz teyit (job sorgusu OLCULEMEDI, davranissal kanit YESIL):** canli `pruvo3d.com`
  200 · `sitemap.xml` 200 · canli `urunler.json` **19325** = yerel **19325** · `d1-sync --durum`
  uc eksen YESIL (SAYI 19325=19325 · SEMA temiz · ICERIK 19325/19325, uyusmaz 0/eksik 0/fazla 0).
  19325 katalogu `fac2223b` ile geldi ve o kosumda `deploy` SKIPPED'ti → canlida gorunmesi
  `88f111f7` kosumunun fiilen teslim ettiginin kanitidir.
- **Alarm kolu (`Spec/tasarim ifsasi`) DOKUNULMADI** — DUR kosulunda (ayni kok neden 3+ kosum),
  yayin zincirinin on kosulu DEGIL. Ona ait **3 mail kutuda BIRAKILDI**.
- **2/2 mail Cop'e** (yalniz "Build & deploy" konulu ikisi; inbox 7558→7556, Cop BOSALTILMADI).
- 🔴 **ACIK KALEM — olcum yuzeyi daraldi:** job-duzeyi `gh run view --json jobs` sorgusu bu turda
  **OLCULEMEDI** (kimliksiz istek → API kota tavani). Hukum canli+D1 davranisindan verildi.
  Arac/kimlik tikanmasinin ayrintisi sinif geregi `DEVAM-ARSIV.md`'de (git disi).

## CI NOBETI (17:37 turu) — kapandi; ayrinti ARSIVDE
- Yayin seridi o turda bagimsiz olculdu ve YESILDI; acik kalan bagimsiz alarm kolu
  yayin zincirinin on kosulu DEGIL.
- Turun tum olcumleri, acik kalemi ve arac/kimlik tikanmasi sinif geregi
  `DEVAM-ARSIV.md`'ye tasindi (silinmedi).

## CI NOBETI (16:37 turu) — kapandi; ayrinti ARSIVDE
- Onceki yayin kirmizisi kendi kendine kapandi: `tools/marka-arama-d1-test.py` HEAD'de 54/54, rc=0.
- Turun geri kalan olcumleri ve acik kalemi sinif geregi `DEVAM-ARSIV.md`'ye tasindi (silinmedi).

## 🟢 IKI DAL MAIN'DE — sozluk `e10a91ce` · cron nabiz esigi `ac533601`
- **Sozluk (4 ad):** on kosul BAGIMSIZ olculdu — sozluk ACIKKEN `uyum-kapisi` **39/0 YESIL**;
  pozitif kontrol: 7 kayit onarimindan ONCEKI veriyle (`16501e39`) ayni sozluk **A1 KIRMIZI 38/1**.
  Sozlugu tuketen kapilar: `altkategori-sinifla-test` 114/0 · `marka-uyelik-test` YESIL ·
  `model-uyelik-kapisi` 21/21. D1 uc eksen 19.126 birebir (merge oncesi ve sonrasi).
- **Cron nabiz esigi:** A0/A3 tavani 9→18 sa GEVSEDI, A4 (zarar ekseni) **9 sa'te KALDI**.
  Mimar tarafinda BAGIMSIZ curutme (dalin fiksturlerinden ayri, 23 iddia / **0 kusur**):
  ayni teslim rejiminde A0/A3=18 · A4=9; paket damgasi 10,0/14,4/17,0 sa bayatken A4 KIRMIZI,
  8,0 sa'te yesil. Teslim 96→0 taramasinda esik 3/6/11/15/18 seyredip A5 tabani altinda **9'a
  GERI DUSUYOR** (kendini susturma yok); 18,4/19/24/30/47 sa sessizlik KIRMIZI (korelme yok).
  Kapinin kendi kosumu 196 iddia/0 kirmizi · mutasyon **29 oldurucu + 6 kontrol, 0 kusur, sapan 0**
  · `ci-kapsam-test` YESIL. `deploy.yml` job grafigine dokunulmadi (kapsam 3 dosya, hepsi `tools/`).
- **Temizlik:** worktree 5→3 (main + korunan 2), iki dal silindi (porcelain temiz + icerik main'de
  + ana agacta yetim is yok). Ortak kutu 285→215 satir, 4 kapanmis blok arsive TASINDI (silinmedi;
  285 satirin 284'u kutuda ya da arsivde birebir dogrulandi, fark yalniz frontmatter damgasi).

**🔴 BU TURDAN ACIK KALEM (benim merge'lerimden DEGIL, olculdu):**
1. `serit-a2` (`marka-arama-d1-test.py`) **KALDI AL3** — `marka_arama` kolonundaki 4 deger kanonik
   marka/alias degil. ⚠️ `50554385` kosumunda **birebir ayni iddia, birebir ayni 4 adla** zaten
   kirmiziydi; sozluk merge'i onu ne acti ne kapatti (AL3 `marka_kanon`/alias tablosundan besleniyor).
   Duzlem: `?q=` gecisi. **Yayin bu yuzden SKIPPED.**
2. 🔴 `serit-a3` (`jenerator/test/vitrin-kabul.js` test 6) **DETERMINIST DEGIL** — degismemis main'de
   15 kosum: **13 yesil / 2 kirmizi**, ayni urunle bir kez 1. bir kez 2. kartta. Kok neden
   `index.html` `VITRIN_SEED = Math.random()`. Kapi `deploy: needs` zincirinde ve `continue-on-error`
   YOK -> rastgele ~%13 ihtimalle TUM ekibin yayinini durduruyor. Tohum sabitlenmeli ya da iddia
   "ilk 4"ten "parametrik on blok"a cekilmeli.

## 🟢 CI NOBETI (12:00 turu) — yayin kosumunun RENGI onarildi, 24 mail Cop'e
- Kutuda 4 Agu 17:00'den beri birikmis **24** "Run failed" maili tarandi (inbox 7565 mesaj,
  toplu cekim, ornekleme YOK). Dagilim: 21 yayin is akisi + 2 D1 sapma alarmi + 1 yayin erisim alarmi.
- **Kok neden yayin arizasi DEGIL:** bloklamayan bir alarm job'i yayin is akisinin ICINDE kosuyor,
  kendi kirmizisini kosum sonucuna tasiyordu; 11 kosum bu yuzden kirmizi gorundu.
- **Onarim (Codex, commit `5945c21e`):** o job deploy.yml'den AYRI bir push is akisina tasindi.
  Komutlari AYNI, fail-closed AYNI, kapi SILINMEDI/gevsetilmedi, `continue-on-error` EKLENMEDI.
  `is-akisi-kapisi.py::SERIT_B` tabani 43→41 (tasinan iki kol dustu).
- **Bagimsiz teyit (mimar eliyle, job duzeyinde):** kosum `30990002466` / sha `5945c21e` →
  `build`+`deploy`+`yayin`+`cron-nabzi` **success**. `D1 sapma alarmi` success (`30990906980`);
  `Yayin erisim alarmi` elle tetiklenip **success** (`30991066350`).
- **24/24 mail Cop'e tasindi** (inbox 7565→7541, Cop BOSALTILMADI); bulunamayan 0, coklu eslesme 0.

**🟡 BU TURDAN ACIK KALEM (mimar karari, dokunulmadi):**
1. Ayrilan alarm is akisi HALA kirmizi (bilinerek; kaynak onarimi ayri dalda, worktree
   `agent-a294bf9bc19a3c740`). ⚠️ Yan etki: her `main` push'unda o is akisi adina **YENI**
   "Run failed" maili gelecek — kutu gurultusu bitmedi, yalnizca yayin kosumundan AYRILDI.
2. **OLCULMEDI:** "bloklamayan job mutanti ana kosumun `conclusion`'ini DEGISTIRMEMELI · yayini
   durduran job mutanti DEGISTIRMELI" cift yonlu kabul testi bu turda kosulmadi. Yapisal kural
   uygulandi ama kendi kabul testi hala YOK.
3. Yeni is akisi dosyasi `is-akisi-kapisi.py` kapsam tablosunda beyanli DEGIL — adimlari sessizce
   silinebilir mi olculmedi (kapsam kapisi ekseni).

## 🔴 5 AGU OTURUM ACILISI — HASAR TARAMASI (kota kesintisi sonrasi)
**Kayip is YOK.** Bes deponun (pruvo · hasat · jenerator · pazarlama · bot) calisma agaci TEMIZ;
dort worktree'nin hicbirinde commit'lenmemis degisiklik yok, ana checkout `origin/main` ile senkron.
`d1-sync --durum` uc eksen YESIL: **18.997** urun, sayi/sema/icerik birebir.

**🔴 GERCEK HASAR — ONARILDI, YAYIN ZINCIRI YESIL: canli 18.550 → 18.997 (447 urun).**

🔴 **ONCE MIMARIN KENDI OKUMA HATASI — DERS BUDUR (`[[hukum-yanlis-birimde]]` birebir tekrari):**
"28 ardisik kosum kirmizi" DOGRU ama bundan **"deploy hic kosmadi"** hukmunu cikarmak YANLISTI.
Job duzeyinde olculdu: o 28 kosumun **14'unde `deploy`+`yayin` YESIL kostu**; kosumlari kirmiziya
boyayan sey **bloklamayan** bir alarm job'iydi (adi + dokum DEVAM-ARSIV.md de, git disi). Yayini fiilen durduran **tek** kosum
sonuncusuydu (`ecc01a25`). Yani hasar "11 saat / ~1.500 urun" DEGIL, **tek commit / 447 urun**.
**Kural: kosum duzeyi sonuc, job duzeyi hukmu VERMEZ — `gh api` ile job'a bak.**

**Kok neden: VERI degil KOD da degil — YARGI BOSLUGU.** Bisect: `f35c421f` agaci 21/21 yesil,
`ecc01a25` 1/21; fark **yalniz `urunler.json`** (+8795 satir, 0 kod satiri). `Ford|raptor` zaten
yayindaydi, son parti `Yamaha|raptor`'u 2→6 urune cikarip esigin ustune tasidi, cift **YARGISIZ**
kaldi (K19). Ford Raptor (kamyonet) ≠ Yamaha Raptor (ATV) — ad cakismasi, emsal
`Ford|sierra`/`Suzuki|sierra`. Hukum: `ROZET_CAPRAZ_IZINLI`'ye 2 gerekceli giris
(`SAYISI` 22→24, `IMZA` hesaplandi). Kapi gevsetmesi YOK, `urunler.json`'a dokunulmadi,
MaCiT'e devir 0 kayit.

**Bagimsiz curutme (uc iddia da dogrulandi):** diff 1 dosya +12/−2, deny tablosu imzasi iki agacta
AYNI · batarya 31 oldurucu + 6 kontrol, beklentiyi tutmayan 0 · capraz kume iki kosumda da
43 cift / 20 model, main'in tek KALDI ekseni `YARGISIZ=[Ford|raptor, Yamaha|raptor]`, dalda `-`
→ **bu 2 giris disinda hicbir ciftin yargisi degismiyor** (olculdu, varsayilmadi).

**Merge + ikinci kilit:** merge `a4bcaf60`; ardindan `serit-a2/a3` **daha erken** bir adimda kirmizi
yandi — `devam-sinif-kapisi.py`, bu dosyanin kendi satirlarinda 2 sinif ihlali (kaynak: mimarin
push edilmemis `6d519e84` notu). Kapinin yazdigi cozum uygulandi (silme yok, arsive tasima),
commit `ca01b743`. 📌 Ders: DEVAM.md'ye yazilan hasar notunun KENDISI yayini durdurabiliyor.

**Canli dogrulama (kosum 30983315565, `--is-ancestor` rc=0):** `deploy` **success** · canli
`urunler.json` canonical + cache-bust'siz **18.997**, 25 rastgele yeni urun sayfasi 25/25 HTTP 200 ·
`d1-sync --durum` uc eksen yesil · **tam parite ana checkout'tan:** `parite-test.js` 1199 sorgu
BIREBIR (cikis 0), `parite-ege.js` 848 sorgu BIREBIR (cikis 0) — merge oncesi ikisi de OLCULEMEDI'ydi.
`yayin` job'i once failure verdi: tasarlanmis tavan (447 > `AZAMI_ADAY=300`); `yayin-kapisi.py
--geriye-doldur` ile kapatildi → `yayinda=18997 · taslak=0`, geri-okuma dogrulandi.

**🟡 ACIK KALEMLER (bu turda DOKUNULMADI, mimar karari):**
1. Bir alarm job'i kirmizi — bloklamayan; job adi + onarim dalinin adi DEVAM-ARSIV.md de (git disi). Onarim dali
   (164 isabet → 0) merge kuyrugunda. Kirmizi kaldigi surece "yayin zinciri kirmizi" sinyali
   gercek yayin arizasindan **ayirt edilemiyor** — bugunku 11 saatlik yanlis okumanin sebebi budur.
2. **`yayin` 300 tavani:** 447'lik parti tekrarlanirsa ayni kirmizi yeniden dogar (MaCiT'e yazildi).
3. `cron-nabzi` kirmizi — `d1-uzlastirici.yml` zamanlanmis teslimi 9,2 saattir yok
   (mevcut "A0 DAMGA" acik kaleminin ayni sinifi, bu merge'le ilgisiz).
4. OLCULEMEDI: `kanca-kablolama-nobeti.py --ci` 18 ekseninin 2'si (16 yesil, 0 kirmizi, cikis 0).
5. Depo hijyeni: 4 worktree → 3 (merge edilen silindi) + 3 push'suz yerel dal, tavan 2.

**OKAN HUKMU (bugun):** (1) hat yesile donene kadar diger mimar oturumlari acilmayacak — **kosul
KARSILANDI, acilabilir**; (2) worktree/dal hijyeni onarimdan SONRA. Ayrica bir hesabin kredisi
07:15'te bitti; oturum acilis sirasi kotaya gore secilecek.

# DEVAM (KraL) — 4 Agu 2026

## 🟠 ACIK KALEM (kanca kablolama dali, agent-aabf841a) — bu turda GENISLETILMEDI
`tools/is-akisi-kapisi.py::SERIT_B` tablosu (is_akisi, job, **betik-yolu**) granulunde
anahtarlaniyor. Yani bir betik SERIT_B'de beyanliysa o betigin GELECEKTEKI TUM bayrakli
cagrilari da sessizce muaf sayilir. Bu dalin getirdigi bir gerileme DEGIL — mevcut tasarim;
`kanca-kablolama-test.py`nin `--mutasyon` kolu da bu yuzden ayrica beyan istemeden gecti.
Gelecek is: SERIT_B'yi (is_akisi, job, betik, **bayrak**) granulune tasimak (bu turda kapsam disi).

## 🔚 OTURUM KAPANISI — 4 Agu · YENI OTURUM ONCE BUNU OKU

### ✅ 5 AGU GECE TURU — CANLIYA GIDENLER
- `f6569d7f` kapi agaci sinifi kapandi — ayrinti DEVAM-ARSIV.md de (git disi).
- `c912548f` yayin kilidi (tek urun) · `d3638a5c` DEVAM budamasi — ikisi de kapandi.

**🔴 SIRADAKI TUR — MERGE KUYRUGU (hepsi dal, hicbiri canlida degil):**
1. **marka aramasi -> uyelik yuklemi** (Okan hukmunun ana kaldiraci): `sayfa != arama`
   **79 marka / 6.507 kalem -> 20 marka / 75 kalem (-%98,8)**, kaybolan urun 0. Merge kapisinda.
   🔴 Capa DINAMIKLESTIRILDI: havuz `srch - sayfa`dan DEGIL **veri iliskisinden** kuruluyor —
   arama kumesinden turese kendini dogrulayan capa olurdu, `srch = set(sayfa)` mutanti havuzu
   da bosaltip kapiyi "olculemedi"ye dusururdu. Bos kume -> rc=2 OLCULEMEDI (M14).
2. **`model_kanon` kolonu** (8.727 urun / 549 deger) — 3 commit: `1) kolon · 2) taban · 3) sozluk`.
   🔴 **MODEL EKSENI MARKADAN FARKLI:** kanon hamin UST KUMESI DEGIL — 1.572 jeton / 5.572 kalem
   kolonda hic gecmiyor, yayimlanan etiketlerde bile "ham eslesiyor kanon eslesmiyor" 16 kova /
   276 kalem. **Uc BIRLESIM kullanmali** (HocA'ya yazildi). Sayfa<->uc farki 96 kova/390 kalem -> 0/0.
   🔴 Commit 3 (sozluk) TEK BASINA MERGE EDILEMEZ: sozluk acilinca 7 kaydin `uyum[].model`'i
   yazim varyanti oluyor -> `uyum-kapisi` A1 KIRMIZI + `urun_hash` bayat -> sonraki senkron o 7
   urunun `uyum`unu D1'de `[]` yapar (Ege uyum bilgisini KAYBEDER). MaCiT'in 7 kayitlik
   duzeltmesiyle AYNI merge'de inecek.
3. **`ege-bilgi.md` tavan payi 27 -> 369** (5 tur curutme). Mayin gercekti: eski pay 27 < en ucuz
   filaman kaleminin 52 birimi, **1 kalem bile tasiriyordu** (KaaN/MaCiT'in isini kirardi).
   🔴 Tur-4 dersi: sikistirma iddia DUSURMEDI ama **iddia EKLEDI** — `cozum DAIMA filament olsun`
   mutlak hukmu, belgenin kendi onayli gomme-somun istisnasiyla (metal) celisiyordu; ikisi de her
   prompta gidiyordu. Denetim tek yonluydu (yalniz kaybolani sayiyordu), cift yonlu yapildi.
4. ACIK KALEM: depo hijyeni ve kapi daraltma — dokum DEVAM-ARSIV.md de (git disi).
5. **Yayin hatti:** bu gece deploy **74 dk durdu** (bir commit inline JS ekleyip `varlik-test.py`i
   kirdi) ve **hicbir alarm atesle­medi** — `deploy-aclik-kapisi` esigi 4 ardisik skipped'e ayarli.
   Ayrica parite esigi bayat: pay 3,0x -> **1,33x**, normal kosulda bile "OLCULEMEDI" uretebilir;
   kritik yol `serit-a3` pencerenin **%93'u**. Ucu birden mühendiste.

**BEKLEYEN KUCUK KALEMLER (bende):** `_isi_yuvasi()` cift-onek korumasi (tek satir) ·
"eklenen jeton gerekce tablosu" **calistirilabilir arac degil**, anlati — bir gun kapiya donerse
ilk fiksturu "hukum ekleyip BICIM diye etiketleme" mutanti olsun · `/marka/bmw/motorrad/` hukmu
(model degil marka KOLU, `PSA`/`VAG` sinifi — kapatilacak) + `Mercedes|A/S/V` (TEK HARF ama
GERCEK model, kapatilmayacak, kanonik gosterime baglanacak) · C kovasi 87 urun · duvar-susu
kapisinin yapisal cozumu (cip evreninden MODEL adi ara).

**CI nobeti:** son tur dokumu DEVAM-ARSIV.md de (git disi).

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

ACIK KALEM: onceki tur kuyrugu — dokum DEVAM-ARSIV.md de (git disi).

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
