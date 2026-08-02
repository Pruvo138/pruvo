# DEVAM (KraL) — 31 Tem 2026

Onceki ayrintili kayitlar DEVAM-ARSIV.md'de (git disi, lossless).

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
  (`merge-base --is-ancestor` exit 0), ardil kosum `30745500956` izleniyor.

## OTURUM KAPANISI — 2 Agu 2026 (KraL · uyum ekseni + alt kategori taksonomisi + sayfa agirligi)

**CANLIYA GITTI (SHA + olculen sonuc):**
- `4f122b84`+`9e61416e` yonetim paneli girisi cerez oturumuna gecti; anahtar ayrica yenilendi.
  Odeme ucu regresyonsuz. Ayrinti + olcumler DEVAM-ARSIV.md'de.
  ⚠️ Shop worker'i hicbir is akisi yayinlamiyor — **elle yayinlandi**. Bu bir surec bosluğu, kayitli.
- `68c92a44`+`66da9cd8` sayfa agirligi: ortalama urun sayfasi **60.426 → 36.753 bayt**,
  yayin **1,029 → 0,609 GB** (Pages ~1 GB siniri; tavan ~16.8k urunden ~28k urune kaydi).
  Tekrar eden CSS/JS icerik-adresli same-origin varliklara tasindi; atif/fiyat/sepet yerinde.
- `e3edbd15`+`8d36eb9c` uyum ekseni paketi (spec) · `986b052e` uyum sozlugu + semasi + fail-closed
  kapi (**tuketici YOK**): kapali marka kumesi 169 jeton, 29 iddia, 13/13 mutant.
- `31fc16b1` alt kategori taksonomisi **12 deger/1 kategori → 60 deger/6 kategori** + deterministik
  uc gecisli siniflandirici (102 iddia, 7/7 mutant) · `7930a93e` kapi **dagilim degil gecerlilik**
  olcuyor (asagida) · `ead0bcb6` **backfill 16.646 kayit**, bos kalan 0.
- `fc53e7ce` devam kaydi sinif temizligi · `cb337803`, `9d8d0cf8` devam kayitlari.

**OLCULEN KARARLAR:**
- `marka = tekillestir(uyum[].marka + uyum[].model)` — yalniz markadan turetmek `Focus`/`F-150`
  gibi jetonlari arama metninden dusururdu (sessiz kayip). 13.616 kayitta ayrisan 0.
- Alt kategori ekseni **YER/SISTEM**, sekil DEGIL: sekil ekseni 60 grup / %89 cakisma / en buyuk
  grup %37; yer ekseni 16 grup / %24,9 / %16,3.
- Kategori <100 urunse alt kategori ALMAZ (8 kategori) · grup <15 urunse acilmaz. **KARAR.**
- Okan karari: siniflanamayan urun **bos kalmaz** — uc gecisli atama (kesin → turetilmis sozlukle
  yakinlik → artik kova). Gecisler 15.491 / 373 / 782. Koruma: bir grubun >%50'si 2./3. gecisten
  geliyorsa kirmizi isaretlenir; bugun **0** grup isaretli.
- Uyum A4: **576 kirli kayit HARIC**, temiz ~13.040 yazilir; kanoniklestirme AYRI tur ve
  arama paritesi ONCE/SONRA olculmeden kapanmaz.
- Marka-model sayfalari **EDGE**'de uretilecek (bayt tavani), statik DEGIL.

**🔴 DERS — bugun iki kez yayin hatti tikandi, ikisi de mimar hatasi:**
1. Curutme merge'e **paralel** kosturuldu; bulgu merge'den sonra geldi. Bloklayici CI adimi getiren
   dalda curutme **merge'in ONUNDE** bitecek.
2. Bir kapi **gecerlilik degil dagilim** olcuyordu ve bloklayiciydi: baska evlerin mesru isi
   (2 urun eklemek) yayini durduruyordu. Ilke: **bloklayici olan sey IHLAL olmali, veri DAGILIMI
   degil.** `7930a93e` ile onarildi; dagilim `--rapor` kolunda sayiyla duruyor.

**KOSUYOR:**
- MaCiT: uyum backfill (A4 karari verildi, temiz kayitlar yaziliyor).
- `claude/cool-rhodes-92cdf1` (Okan'in actigi is): CI kapsam kapisi, 11 ileri — **benim delegem degil.**
- KraL delegesi kosan is YOK; tum isciler kapandi, dallar temizlendi.

**BEKLIYOR — kim neyle bloke:**
- 🔴 **HocA — alt kategori zincirinin SON halkasi.** Uc `altkategori`'yi **donduruyor ama
  FILTRELEMIYOR** (olculdu: parametre sessizce yok sayiliyor; kontrol ekseniyle kanitlandi).
  Site yuzeyi buna bagli, mühendis kod yazmadan DURDURULDU — yazsaydik cip gorunur, tiklayinca
  liste degismezdi ve alarm calmazdi. 6 maddelik uc sozlesmesi HocA'ya verildi (ucuncu eksen +
  sayim onbellek anahtari surumu + kontrol eksenli kabul testi). Gelince yuzey ayni gun baglanir.
- HocA (ikinci): telefon kanoniklestirmesi — `wa-siparis-onarim` merge BENDE bekliyor.
- KaaN: parametrik hacim/fiyat ayrismasi (7 aile, en buyugu %51). Devredildi, sayi bekleniyor.
- ArTisT: marka-model sayfasi acma esigi N onerisi.
- **BENDE:** D1 `uyum` kolonu (`--sema` ONCE, dogrula, SONRA kod) · `urun-ekle.py`'de `marka`
  tekillestirmesi yok · alt kategori filtre yuzeyi (HocA'ya bagli, spec hazir) ·
  `koru/faz3-edge-arama` + `kurtarma/nobetci-tur3`: icerikleri main'de **olculdu**, silinmedi
  cunku ikincisi uzakta YOK (tek kopya).

**OKAN'DA BEKLEYEN:** cayma-hakki kalemi **KAPANDI** (Okan hukmu: celiski yok, sayfalarda ikisi de
yazili). Yeni Okan-kapili karar YOK; sayfa acma esigi N ArTisT'ten oneri gelince gelecek.

## MERGE — 2 Agu 2026 (yetki kabul kumesi: cok-eksenli VE iddialari eksenine bolundu)

`431f60ec` main'e alindi ve itildi (`7930a93e..431f60ec`). Kapsam merge-base'den (`1e4d0b20`)
**3 dosya / +373 -37**: `shop/src/yonet.js` (YALNIZ YORUM), `shop/test/kabul.js`,
`tools/yonet-cerez-mutasyon.py`. `urunler.json` / `worker/` / arama diffte YOK → parite testleri
GEREKMEDI (olculdu: bu yollarda 0 dosya, atlanmadi). Sizinti taramasi: 0 vurus.

**Olculen sayilar (hepsi DALIN worktree'sinde, cikis kodlari gorulerek):**
- `node shop/test/kabul.js --yonet-cerez` → `SONUC: 70 gecti, 0 kaldi`, `IDDIA SAYISI: 70`, RC=0.
  **65 → 70** (onceki tur 66'ya cikmisti; 66 → 70). Hicbir turda DUSMEDI.
- **8 eksenin 8'inde de kendi TEK-KIRMIZI mutanti var:** `C15a`·`C15b`·`C15c`·`C22a`·`C22b`·
  `C22c`·`C22d`·`C22e`. Yeni mutantlar M16–M23; surucu 26 kayit (23 kirmizi-beklentili + 3 kontrol).
- `python3 tools/yonet-cerez-mutasyon.py` → RC=0, `TUM MUTANTLAR YAKALANDI, KONTROLLER YESIL`.
  Kaynak sha256 basta/sonda ayni — mutant diske sizmadi.
- **Nobetci olcutu SERTLESTI:** mutant kaydindaki `olcut` alani `tek_eksen` → **ESIT**
  (kirmizi kume == beyan; fazlalik KUSUR), `genis` → **KAPSAR** (beyan ⊆ kirmizi). Eskiden hepsi
  KAPSAR'di. Olcut kurulur kurulmaz iki bayat beyani (M14/M15) kendi kosumunda yakaladi.
- Diger kapilar (dalin agacinda, RC): `--sema-paritesi` 0 · `kisisel-veri-test.py` 0 ·
  `ci-kapsam-test.py` 0 (161 kesfedilen / 125 kosulan / 36 muaf) · `kapi-envanteri.py` 0 (**7/7**).
- Merge SONRASI ana checkout'ta bagimsiz teyit: kabul `IDDIA SAYISI: 70` RC=0 · surucu RC=0.
- `yasal-sayfa-drift-kapisi.py` → YESIL, 0/4 sapan.
- `d1-sync.py --durum`: **16874 == 16874**, hash uyusmaz 0 / eksik 0 / fazla 0, sema ekseni temiz.
- **CI:** kosum `30743814411`, `headSha` = `431f60ec` **birebir** (`merge-base --is-ancestor` exit 0).
  7 isin 7'si success (cron-nabzi · envanter · mesaj-nobeti · serit-b · build · deploy · yayin);
  `Yonet anahtar/cerez kabul testi` adimi **success** (bloklayici, `continue-on-error` YOK).

**🔴 CURUTUCUNUN BIRINCI TURDA BULDUGU KAPSAM KAYBI — onarildi.** Ozellik-kapali `GET /` sondasi
"yuklemi baska bir iddiayla ozdes" gerekcesiyle silinmisti; gerekce **durumsuzluk varsayiyordu**,
oysa modul duzeyi durum istekler ARASI yasiyor. Sonda silinince panel koku IKI degil BIR kez
yoklaniyordu ve "ilk cagri temiz, IKINCI cagri sizdiriyor" sinifi bir mutant KACIYORDU
(olculdu: onarim oncesi ayni mutant cikis=0 → KACAK; onarim sonrasi cikis=1, 2 iddia kirmizi).
Sonda iddialariyla birlikte geri kondu, sinif tasiyicisi mutant surucuye eklendi. Ikinci turda
bagimsiz curutucu uc agaci ayri cikarip ayni mutant metinleriyle kiyasladi: kacak kapandi,
YENI kayip yok, `tek_eksen`→`genis` yeniden siniflandirmasinda suistimal 0 (26 kaydin hepsi
kosuldu, beyan-olcum uyusmazligi 0).

**ACIK MADDELER (merge'i BLOKLAMADI, ayri dalda ele alinacak — bu dalda ONARILMADI):**
1. Surucudeki `olcut` alaninin yazim hatasina karsi davranisi sert DEGIL; sinifi ve olcumu
   DEVAM-ARSIV.md'de. Tek satirlik care var, bu dalda uygulanmadi.
2. 14 `KAPSAR` kaydinin **11'inin** kirmizi kumesi bugun beyanina birebir esit — bedava capa
   kaciriliyor (ESIT'e cevrilebilecek 11 kayit).

**OLCULEMEDI:** `sabitEsit` zamanlama yan-kanali. Beyan **yapisal** (kod okumasiyla), calisma
zamaninda **olculmedi** — bu depoda deterministik bir zamanlama olcegi yok. "Yesil" DEMIYORUM.
Ayrica acik kayit: ozellik-kapali `/liste` kolunda ordinal (ilk/ikinci cagri) sinifi ARANMADI.

**Temizlik:** `worktree-agent-a24619011271d9d79` dali (yerel + **uzak**) ve worktree'si silindi
(porcelain bos, icerik main'de, ana agacta yetim degisiklik yok). Ana agactaki `urunler.json`
degisikligi ve `uyum-backfill.py` BASKA oturumun isi — DOKUNULMADI.

**DERS:** "iki iddianin yuklemi ozdes" gerekcesiyle sonda silmek, durum tasiyan bir uctan cagri
**sirasini** da siler. Cagri ordinali olcumun parcasidir; ozdeslik yalnizca durumsuz uclarda gecerli.

## MERGE — 2 Agu 2026 (yonet giris kapisi: iki secret kapisi AYRI AYRI olculuyor)

`db9d6de6` main'e **fast-forward** alindi ve itildi (`b0b98509..db9d6de6`). Kapsam merge-base'den
**4 dosya / +89 -28**: `shop/src/yonet.js`, `shop/test/kabul.js`, `.github/workflows/deploy.yml`,
`tools/yonet-cerez-mutasyon.py`. Urun verisi / `worker/` / arama diffte YOK → parite testleri
GEREKMEDI (olculdu, atlanmadi).

**Kapatilan delik (olculdu):** giris ekseninin iki katmani artik AYRI AYRI olculuyor — tek iddia uc
iddiaya bolundu, alt katman TEK BASINA olculebilir hale geldi (davranis DEGISMEDI, yalnizca
olculebilirlik). Sinif + ayrinti + olcumler DEVAM-ARSIV.md'de.

**Olculen sayilar:**
- `node shop/test/kabul.js --yonet-cerez` → **65 gecti / 0 kaldi**, `IDDIA SAYISI: 65`, RC=0
  (onceki taban 63 — DUSMEDI). `--sema-paritesi` 2/0 RC=0.
- `python3 tools/yonet-cerez-mutasyon.py` → **13 kosum: 10 kirmizi-beklentili + 3 kontrol**, hepsi
  PASS, her kosumda `iddia=65/65` (hicbir mutant testi cokertmedi), kaynak sha256 degismedi, RC=0.
  Surucudeki **beyan edilmis SURVIVOR `K4`** kirmizi-beklentili `M10`'a cevrildi.
- 🔴 **CURUTME (asil sinav):** dalin `kabul.js`'i merge-base haline dondurulup surucu tekrar
  kosuldu → **`M10` YAKALANAMADI** (`cikis=0 kirmizi=0 isaret=EKSIK:C22a`), surucu RC=1.
  Yani `M10` sahte kirmizi DEGIL, gercekten `C22a`'ya bagli. Geri alma sonrasi porcelain BOS.
- Surucu diffinde **gevsetme YOK** (elle okundu): silinen mutant / daraltilan beklenti /
  `continue`-`skip` kolu / kaldirilan kontrol / zayiflatilan sha256-iddia sayisi teyidi — hicbiri.
- Kapilar (dalin worktree'sinde, cikis kodlari goruldu): `kisisel-veri-test.py` RC=0 (5 nobetci
  YESIL) · `ci-kapsam-test.py` RC=0 · `kapi-envanteri.py` RC=0 (**7/7 VAR+BAGLI+NOBETTE**) ·
  `is-akisi-kapisi.py` RC=0.
- `d1-sync.py --durum`: **16874 == 16874**, hash uyusmaz 0 / eksik 0 / fazla 0, sema ekseni temiz.
- **CI (yerelde olculemeyen tek eksen):** kosum `30740041326`, `headSha` = `db9d6de6` **birebir**.
  `Yonet anahtar/cerez kabul testi` adimi **success** (node 20, bloklayici, `continue-on-error` YOK).
  Kosumun TAMAMI **success** (cron-nabzi · envanter · mesaj-nobeti · build · serit-b · deploy · yayin).

**Temizlik:** `worktree-agent-ae5d5bf43b9f176b0` dali + worktree'si silindi (porcelain bos, ucu
main'de, ana agacta yetim degisiklik yok).

**DERS:** "beyan edilmis SURVIVOR" bir nobetcide tehlikeli kaliptir — "bugun yesil kalmasi normal,
onundeki kapi tutuyor" gerekcesi, o katmanin HIC olculmedigini gizler. Bir katmanin savunma
derinligi oldugu iddiasi ancak o katman **TEK BASINA** olculuyorsa kanittir.

## TEYIT — 2 Agu 2026 (yonet mutasyon surucusu ANA CHECKOUT'ta bagimsiz kosuldu)

Merge sonrasi surucu dalin worktree'sinde degil **ana checkout'ta** (`main`, `1e4d0b20`) bir kez
daha kosuldu — kapinin dalin agacina degil main'in agacina bagli oldugu ayrica olculsun diye.

- `python3 tools/yonet-cerez-mutasyon.py` → **RC=0**. Taban `IDDIA SAYISI: 65`. **13 kosum:
  `M1`..`M10` KIRMIZI (hepsi `iddia=65/65`, isaret TAM) · `K1`..`K3` YESIL (0 kirmizi)**.
  `shop/src/yonet.js` sha256 basta ve sonda AYNI (`5fe2d520…`) — mutant diske sizmadi.
- Isaret eslesmeleri: `M3`→`C15,C22a` · `M10`→`C22a` (beyan edilmis SURVIVOR'in kapattigi delik
  ana agacta da kapali) · `M6`→`C18a,C18b,C19b` · `M8`/`M9` ayrica `C10f` yakiyor (ikisi de ortak
  `CEREZ_BAYRAK` kaynagindan turuyor).

**KAYIP — ayri kalem:** ayni pencerede `tools/altkategori-sinifla-test.py` uzerindeki
COMMIT'LENMEMIS degisiklik kayboldu; yeni commit YOK, stash BOS. `git fsck --dangling` ile 45
dangling blob tarandi (`--lost-found` KULLANILMADI, diske yazardi) — dosyanin hicbir surumu YOK.
**KURTARILAMAZ:** degisiklik hic stage'lenmemis, git object DB'ye hic girmemis. Surucu yalnizca
gecici aynaya yazar ve kendi sha256 nobeti temiz gecti; yine de neyin sildigi KANITLANAMADI.

**DERS:** uzun yasayan bir calisma-agaci duzenlemesi `add`'lenmeden birakilirsa, geri alinmasi
HICBIR IZ BIRAKMAZ — reflog da stash de bos kalir. Eszamanli oturumlarin ustuste bindigi bu
depoda tek koruma ara commit, en azindan `git add`.

## OTURUM — 2 Agu 2026 gunduz (KraL · uyum ekseni + panel anahtari + sayfa agirligi + taksonomi)

**CANLIYA GITTI (olculdu, itildi, canli teyit alindi):**
- `4f122b84`+`9e61416e` **yonetim anahtari URL'den cikti** → cerez tabanli giris. Kabul 63 iddia,
  17 mutant; bagimsiz denetimin actigi 4 kalem kapatildi ve canli dogrulandi. Yayin yolu bu is icin
  ELLE yurutuldu (otomatiklestirme ACIK kalem). Sinif + ayrinti + olcumler DEVAM-ARSIV.md'de.
- **Yonetim anahtari DONDURULDU** (Okan onayi). Eski anahtar canlida gecersiz, yeni calisiyor,
  odeme regresyonsuz; kopya taramasi temiz cikti. Parmak izi ve yayilma zamanlamasi olcumu
  DEVAM-ARSIV.md'de.
- `986b052e` **uyum ekseni sozlugu + semasi + kapisi** (tuketici YOK). Kapali marka kumesi 169
  jeton, `URETICI_MARKA` 14, `ELENEN` 17; 29 iddia, 13/13 mutant; parite site 1199 ✅ Ege 845 ✅.
  Curutucu iki bloklayici buldu, ikisi de kapandi: S2 **sayiyi degil kimligi** koruyor artik
  (kova bazinda donmus imza), mukerrer jeton ELE kovasinda (yayini dusurmuyor).
- `68c92a44`+`66da9cd8` **sayfa agirligi**: ortalama urun sayfasi **60.426 → 36.753 bayt** (canli
  olculdu), yayin **1,029 → 0,609 GB** (Pages ~1 GB siniri, %39 bosluk). Varlik URL'leri 200,
  atif/fiyat/sepet yerinde. `tools/paket-uyum-ekseni.md` (`e3edbd15`,`8d36eb9c`) spec olarak main'de.

**OLCULEN KARARLAR (gerekce DEVAM disinda, pakette):**
- `marka = tekillestir(uyum[].marka + uyum[].model)` — yalniz markadan turetseydik `Focus`/`F-150`
  backfill iner inmez **haystack'ten duserdi**, sessiz arama kaybi. 13.616 kayitta ayrisan 0.
- Marka-model sayfalari **EDGE**'de uretilecek, statik DEGIL (bayt tavani).
- Alt kategori ekseni **YER/SISTEM**, SEKIL degil: sekil ekseni 60 grup/%89 cakisma/en buyuk grup
  %37; yer ekseni 16 grup/%24,9 cakisma/%16,3. Otomobil 16 grup kilitleniyor.
- Kategori <100 urunse alt kategori ALMAZ (8 kategori) · grup <15 urunse acilmaz. **KARAR, eksiklik degil.**
- Okan karari: siniflanamayan urun **bos KALMAYACAK**, uc gecisli atama (kesin → turetilmis
  sozlukle yakinlik → artik kova). Koruma: bir grubun >%50'si 2./3. gecisten geliyorsa KIRMIZI isaretlenir.

**🔴 ACIK — KAPI KARANLIGI (bugun uc bagimsiz olcumden ayni desen):**
Yazilmis ama CI'da KOSMAYAN nobetciler var; `ci-kapsam-test.py` *dosya* kesfediyor, *bayrak* degil.
- `jenerator/test/kabul.py` **TEST 1 gercek kosumda KIRMIZI ve PARA ekseni**: `hacim.js` ↔ OpenSCAD
  7 ailede ayrisiyor (pervane **%51,2**, izgara %39,9, rulman %35,9, kayis %28,7, kasnak %20,6,
  huni %9,8, petek %7,6). Sari seride fiyat hacimden turedigi icin **fiyat yanlis olabilir**.
  Is akisindaki cagri bicimi ACIK kalem (ayrinti arsivde). **KaaN'a devredildi.**
- `filament-test.py` ve `konfigur-nobet-mutasyon.py` hicbir workflow'da gecmiyor.
- `yayin-ic-dil-kapisi` varlik kolunda ACIK bir olcum eksigi var; sinifi + recetesi arsivde.
- Spec yazildi: `spec-kapi-karanligi.md` (scratchpad). Okan'in actigi iki arka plan isi
  (`c14cd59b`,`bf788be6`,`b9facc26`) 63 iddialik kumeyi CI'ya bagladi — ilk parca kapandi.

**KOSUYOR:** `altkategori-kume-kilit` dali (14 kategorinin taksonomisi + deterministik
siniflandirici, uc gecisli atama). Bitince main'e alinacak (Okan: "bittiginde main'e al").

**BEKLIYOR — kim neyle bloke:**
- **HocA:** kart sozlesmesine `altkategori` (Okan'in gordugu yuzey; canli olculdu, uc HALA inmemis
  — `/ara` ve `mod=ege` alan listelerinde alan YOK). Okan istegiyle oturumu uyandirildi.
  Ikinci kalem: telefon kanoniklestirmesi (`wa-siparis-onarim` merge bende bekliyor).
- **MaCiT:** uyum backfill'i YESIL verildi; `Sierra` (149 kayit: 141 Marin / 8 Otomobil) kayit
  basina karar noktasi.
- **KaaN:** parametrik hacim/fiyat ayrismasi (yukarida).
- **BENDE:** D1 `uyum` kolonu (`--sema` ONCE, sonra kod) · `urun-ekle.py`'de `marka` tekillestirmesi
  yok · panel oturum ekseninde iki ACIK kalem (sinifi + recetesi arsivde) ·
  iki eski dal (`koru/faz3-edge-arama`, `kurtarma/nobetci-tur3`) **olculdu: icerikleri main'de**
  (`22b42cb8` / `9c90741b`), silinmedi cunku `kurtarma/nobetci-tur3` uzakta YOK, tek kopya.

## OTURUM KAPANISI — 2 Agu 2026 (KraL · yayin hatti + altkategori + ucuncu denetim)

**CANLIYA GITTI (hepsi olculdu, itildi, canli teyit alindi):**
`89a72022` yayin hatti tikanmasi onarildi (kapi kendi kapattigi deligi "hala acik" saniyordu;
ONCE kaniti artik repoya gomulu fiksturden turuyor) · `09b76410`+`467f8fa8` olcum araci artik
"olculemedi"yi "bozuk" diye suclamiyor · `235fb25a`+`d379ffb7` altkategori izinli kumesi 11->12
ve katalog<->D1 sessiz metin ayrismasi fail-closed kapatildi (kapi 35->42 iddia, mutasyon 17/17)
· `aa114660` altkategori MUSTERI YUZEYINDE (935 sayfa degisti, 15.939 bayt-esit, fail-safe 4/4)
· `d4806461`+`267b0f5a` yayin gecikme nobetcisi + kendi kusurunun onarimi (olcum IS duzeyine indi)
· `782cd74e` panonun sahte anahtar alarmi (Okan eliyle) · devam kayitlari `4e08b0f5`, `7f186361`,
`a2be7d66`. Kapanis olcumu: ana agac TEMIZ, HEAD=origin/main=`a2be7d66`, D1 16874=16874
(hash uyusmaz/eksik/fazla 0), nobetci 🟢 AKIYOR, agac 5->4 (kendi artigim silindi).

**KOSUYOR:** bu oturumun delege ettigi TUM isler kapandi ve raporlandi. Koşan is YOK.

**BEKLIYOR — kim neyle bloke:**
- **HocA (dal `wa-siparis-onarim`, worktree DURUYOR, DOKUNULMADI):** ucuncu denetim yapildi,
  uc eski acik KAPANDI ama teslimin EKLEDIGI 409 savunmasi meshru tekrari ikiz siparise
  ceviriyor (telefon genis kabul edilip TAM DIZE karsilastiriliyor; 7 yazimin 4'u carpiyor,
  olculdu: ayni musteriye 2 satir). Recete kutuda. **Merge BENDE, ondan sonra sema gocu +
  worker deploy + anahtar paylasimi.** Bir para mutanti da hala kaciyor (govde+kalem tutari
  ayni anda sifirdan buyuk tek fikstur yeter).
- **HocA (ikinci, ONCELIKLI — Okan'in bekledigi gorunur is):** kategori sayfasindaki altkategori
  filtresi icin uc kart sozlesmesi genisleyecek. Sema isi YOK, D1 kolonu var ve dolu. Site tarafi
  HAZIR bekliyor; alan gelince cip/filtre + kirilim dugumu ayni gun aciliyor.
- **BENDE (siradaki tur):** panel giris yuzeyinde bir ACIK kalem (sinifi + recetesi arsivde) ·
  fikstur hijyeni (firmanin kendi numarasi fikstürde kullanilmis) · iki eski dal
  (`koru/faz3-edge-arama`, `kurtarma/nobetci-tur3`) main'de olmayan is tasiyor, siniflandirilmadi.
- **Baska oturumlarin agaclari** (`angry-lederberg-d7aa53`, `ci-duzeltme-54cca90a`) duruyor —
  ucu main'de ama sahipleri aktif, DOKUNULMADI.

## OTURUM — 1 Agu 2026 aksam (KraL · yayin hatti + ikinci denetim turu)

- Yayin hatti tikanmasi ve kalici onarimi (`89a72022`) — kapi kendi kapattigi deligi "hala acik"
  saniyordu; ONCE kaniti artik repoya gomulu fiksturden turuyor. Ayrinti arsivde.
- Olcum aracinin yanlis suclamasi kapatildi (`09b76410` + `467f8fa8`) — uc cevap vermeyince
  "bozuk" deniyordu; artik OLCULEMEDI ile BOZUK ayri. Ayrinti arsivde.

### KARARLAR (bu tur)
- Ege kapisinda sirket sesi birinci cogulun da yanmasi KABUL EDILDI: o metin Ege'ye kendi
  bilgisi olarak besleniyor, orada "belirleriz" demek Ege'ye vaat ettirmektir. Kapi
  musteriye gorunen sayfalari okumaz; yasal metinlerde olcum 0.
- Iade kargo bedeli metne YAZILMADI — ticari karar Okan'da; kapi, cevap gelmeden o cumlenin
  yazilmasini kirmizi yakiyor.
- Is bolumu (Okan kurali): is kimin duzlemindeyse o yapar; baskalarini da etkileyen
  degisiklikte karar verici mimar devam eder. Siparis ucunun olcum ekseni kardes mimara
  devredildi, Ege tarafi sahibinde kaldi, sema/odeme/merge bende.

### BEKLIYOR
⚠️ Budama turu bu bolumu de arsive tasidi (lossless, kayip 0 — ayrinti arsivde). ACIK olan
kalem arsive inmez; guncel hal mimar eliyle asagiya yeniden yazildi.

- 🔴 **HESAP TASINMASI ACIK.** 23 Tem'deki MAKINE gocu bitti; envanterdeki is AYRI:
  **hesap devirleri** (kod deposu, edge saglayici, calisma alani, odeme, mesajlasma,
  not/CRM, model saglayici). Migration Assistant hesap devretmez. Olculdu: mevcut
  oturumlar hala eski hesapta -> **hic baslamamis.**
  ⚠️ Ozet listedeki "19" EKSIK SAYIM: tablolardaki atamalar **24 ayri eyleme** iniyor.
  ✅ Bloklayici **6 -> 5**: "yedeksiz gizli dosyalari eski makineden aktar" KAPANDI
  (19 kalemin 19'u da bu makinede; 13'u goc oncesi tarihli, icerik ACILMADI).
  🔴 Yerine gecen risk: iki sigorta paketi (~33 MB) YALNIZ bu makinede. **Karar:**
  paylasilan yedege GIRMEYECEK (temizlik oncesi icerik tasiyorlar) — otomatik yedegin
  degil, tasinmanin **ELLE** kalemidir, sifreli elden gecirilir.
  Envanter + yedek raporu `raporlar/` altinda: gitignore'lu, yedek kapsaminda, sha256
  ozdesligi ve yedek tazeligi dogrulandi.
  ✅ Envanterin "yedekte YOK" hukmu ve goc dogrulayicisinin yanlis alarmi bu oturumda
  KAPANDI: dogrulayici artik **rc=0**, ev sayisi **4 -> 6** (iki ev hic dogrulanmiyordu),
  yesil 62 -> 80, hic dusmedi. Kayit disi kancanin yeni makine tasinabilirligiyle ilgili
  risk kapatildi; ayrintisi git disi arsive tasindi.
  ⚠️ Kalan tek kalinti: eski bir `pre-push` yedegi — siniflandirmasi bende, icerigi acilmadi.

### 🔴 OKAN'DA BEKLEYEN
- **Hesap tasinmasinin 5 bloklayici kalemi** (yukarida) — hicbiri kodla acilamaz.
- **Siparis onay e-postasinin gercek govdesi** hic goruLMEDI: yan etkisiz yolu yok,
  dusuk tutarli GERCEK bir siparis gerekir. Uretilen mantik offline rc=0, ama uctan uca
  "musteriye giden metin" **olculmemistir** — yesil demiyorum.
- ✅ KARAR ALINDI: iade kargo bedeli icin sozlesmeye CUMLE YAZILMAYACAK; sonucu bilincli,
  bedel yasal olarak bizde. Eksiklik DEGIL, karardir — "unutulmus" diye tamamlanmasin.

### KARDES MIMARLARDA
- **HocA — UCUNCU denetim yapildi, MERGE YINE YOK (dal `wa-siparis-onarim`).** Uc ESKI acik
  bagimsiz olcumde KAPANDI: bos dis kimlikte 12/12 cagri reddediliyor ve **0 siparis** aciliyor
  (eskiden 4 cagri = 4 siparis) · 5'li GERCEK yarista tek satir, 500 yok · benim kacirdigim uc
  para mutantinin ucu de artik yakalaniyor. Site kanali regresyonsuz, yetki 8 senaryoda fail-closed.
  🔴 **Ama bu teslimin EKLEDIGI savunma yeni delik acti:** telefon genis kabul edilip (onekli/
  oneksiz/bosluklu hepsi gecerli) kimlik TAM DIZE karsilastiriliyor — 7 yazimin 4'u ayni musteriyi
  yabanci sayip reddediyor ve onerilen care izlenince **ayni musteriye 2 siparis** aciliyor.
  Yani mukerrer siparisi onlemek icin eklenen savunma mukerrer siparis uretiyor; bu girdide yeni
  kod eskisinden KOTU. Recete verildi (kanonik karsilastirma + onek farki fiksturu). Ayrica bir
  para mutanti hala kaciyor (govde ve kalem tutari ayni anda sifirdan buyuk olan tek fikstur yeter).
  Kapanip mutant yakalama tam olunca merge + sema gocu + deploy sirasi BENDE.
- **HocA (ikinci kalem, ONCELIKLI):** kategori sayfasindaki altkategori filtresi icin uc kart
  sozlesmesi genisleyecek — Okan'in bekledigi gorunur is. Sema isi YOK, D1 kolonu var ve dolu.
- **ArTisT:** WhatsApp kanalinin GA4 olcum ekseni devredildi; beni bloklamiyor.
- **MaCiT:** gorselsiz parti icin YESIL verildi (`ed135702`); katalogda henuz gorselsiz
  urun YOK, yani ilk parti bu yolun canli ilk kullanicisi olacak.

### KOSUYOR
- Bu oturumun delege ettigi TUM isler kapandi, merge edildi, dal/worktree temizlendi.
  Kalan iki worktree BASKA OTURUMLARIN — dokunulmadi.

## TABAN (yeniden olc, ezberleme)
Bu bolume SAYI YAZMA — gun icinde bayatliyor ve bayat sayi yanlis guven veriyor
(bugun olculdu: katalog tek oturumda 16589 -> 16672 hareket etti, elle tutulan agac
listesi de tutmuyordu). Tek dogruluk kaynagi kosulan komut:
- Katalog / D1: `python3 tools/d1-sync.py --durum`
- Calisma alani: `git -C /Users/okan/dev/pruvo worktree list`
- Kapilar: `python3 tools/durum.py`
