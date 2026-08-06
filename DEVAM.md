# DEVAM (KraL) — 6 Agu 2026

## 🔚 OTURUM KAPANISI — 6 Agu aksam · 4 MERGE CANLIYA HAZIR, YAYIN ALTYAPIDA TAKILI

**MAIN'E GIREN (SHA + olculen sayi):**
1. **Varlik kaldiraci `8bbd760c`** — her urun sayfasina GOMULU basilan atif modulu tek
   same-origin varliga (`/varlik/atif-<sha256>.js`) tasindi. Artefakt **833,6 → 617,1 MiB**
   (1 GB tavaninda **%81,4 → %60,3**), sayfa basi **61.625 → 26.252 bayt**, **kaybolan URL 0**
   (sitemap ve sayfa yolu iki yonde de 22.511=22.511). `varlik-test` 10/10 · `varlik-mutasyon`
   M1-M5 KIRMIZI / M6 kontrol YESIL · yasal-sayfa drift 4/4 birebir · gitignore temiz.
   🔴 Yoldan cikan bulgu: `enjeksiyon-kapisi.py` **2b ekseni DISSIZDI** — uretilen sayfada
   HTML yorumu ariyordu ama `yayin_html` yorumlari SOYUYOR → hep bos dize olcuyordu (uretilen
   sayfada isaret gecisi **0**). 4 davranissal eksenle degistirildi, kapi **9 → 12 iddia**.
   Bagimsiz curutme: oldurucu 5/5 KIRMIZI, kontrol 2/2 YESIL, artefakt deltasi bagimsiz
   hesapla **birebir tuttu** (227.007.713 bayt). **Yasal eksen elendi:** tasinan blok CC BY
   lisans atfi DEGIL (pazarlama/yonlendirme modulu); CC BY atfi ayri ve **statik HTML**,
   diff ona dokunmuyor — JS kosmasa da gorunur.
2. **Nobet ayrimi `ffc72a6a`** — 6 bloklamayan nobet/alarm job'u `deploy.yml`'den `nobet.yml`'e.
   `deploy: needs` **4..4** · yayin zincirindeki bloklayici adim **132..132** · tasinan **6/6** ·
   **KAYBOLAN 0** · batarya 40 iddia / 9 oldurucu / 5 kontrol (beyanla birebir) · susturma 0.
   🟢 **YAN KAZANC — CONCURRENCY KILIDI COZULDU:** kilidi tutan `d1-kadans / uzlastir` artik
   `nobet.yml`'de, grubu `nobet-serit-b`, `pages`'i PAYLASMIYOR. `pages` grubunda kalan 6/6
   job'un hepsi yayin zincirinde → grubu tutan kosum artik **her zaman yayinlayabilen** kosum.
3. **Denetim kapisi kapsam-patlamasi korumasi `3b369e34`** — `--evet-sil N` onayi, tavan 50.
   Curutme sentetik depoda: onaysiz toplu silme **rc=4 / silinen 0 / sha256 DEGISMEDI**;
   karsi-vaka dogru N ile 6 kayit silindi, tavan alti mesru parti kirilmadi. Oldurucu mutant
   KIRMIZI (4/50 dustu), kontrol mutanti YESIL. Kendini-test **50 iddia rc=0**.
4. **Kanca koku `3aec9eba`** — `diriltme-kapisi.py` worktree'de KANCA ICINDEN kosarken koku
   yanlis buluyordu: `GIT_DIR` **mutlak** geldigi icin `rev-parse --show-toplevel` cwd'yi
   donuyor → kok `<wt>/tools` → **rc=2 OLCULEMEDI → commit BLOK**. Ana checkout'ta gorunmuyordu
   (orada `GIT_DIR` set edilmiyor). Onarim: kok ortamdan degil `-C` kesfinden turuyor.
   Curutme: **fail-closed dogrulandi** (kesfi bozan 6 baglamin hicbirinde rc=0 yok), yuzey
   **214.553..214.553 KUCULMEDI**, oldurucu 3 KIRMIZI / kontrol 2 YESIL, kendini-test 78 → 85.
   🔴 Bu kusur isciyi kanca atlama bayragina itiyordu — kapinin kendisini es gecmeyi
   normallestiriyordu.

**TEMIZLIK:** mukerrer bir CI dali **merge EDILMEDEN silindi** — dal adi arsivde (icerigi `14a378bb`'de,
16 dosyanin 13'u birebir ayni blob) VE **gerileme tasiyordu**: `onizleme-imaj.yml`'de hesap
kimligini `secrets.` yerine **duz metne** geri ceviriyordu (2 satir). `git worktree list`
**6 → 1 satir** (yalniz ana checkout). `DEVAM.md` olculdu: **119 satir / 9160 bayt**, hedefin
(≤130 / ≤12288) altinda — kardes oturum onceden budamis, tasima gerekmedi.

**🔴 ACIK — YAYIN (tek kirmizi eksen, depo kaynakli DEGIL):** canli **20.849 urun /
19.864.882 bayt**, hedef **21.221** → acik **372 urun**; yeni urun sayfasi **404**.
Onbellek elendi: onbellekli ve `?cb=` olcumu **bayt-birebir ayni** → **origin bayat, CDN degil**.
Kok neden **GitHub'in kendi arizasi**: durum sayfasi Actions+Pages **`major_outage`**, olay
`investigating`, 15:22Z'den beri; tum kirmizilar `Set up job` (`Failed to resolve action
download info` / `not acquired by Runner`), **depo kaynakli hata 0**. `gh run rerun` bu
durumda reddediliyor (`cannot be rerun; This workflow is already running`) → 4 vardiyada
**0 deneme**, hicbir kosum iptal EDILMEDI. Ariza gecince `deploy` **JOB**'unun (kosum-duzeyi
conclusion DEGIL) success'i beklenecek, sonra iki olcumle canli dogrulama.

**BEKLEYEN:**
1. **2 IKIZ kok-turetme** — iki CI kapisi betigi (adlari arsivde) ayni deseni
   (`-C <alt dizin>` + ortam scrub'i YOK) tasiyor; yalniz CI'da kostuklari icin gizil.
2. `pages` grubundaki **6/6 job'da `timeout-minutes` YOK** (varsayilan 360 dk) — kilit
   yapisal olarak cozuldu, bu artik ikincil sertlestirme. Workflow degisikligi Okan kapisi.
3. HocA → ADIM 2 (`?model=` uyelik yuklemi); hedefler canlidan tazelenecek.
4. MaCiT → 2 kayit geri cekilecek (baskida wordmark + agiz temasli sinif).

**OKAN'DA KARAR YOK.** Concurrency kilidi merge ile kapandi; kalan engel GitHub arizasi.

## 🟢 KOK COZUM TARAMASI MAIN'DE `fd801a88` — bir TESHIS olculerek CURUTULDU

- **Giren:** `tools/kok-cozum-taramasi.py` (yeni surucu) + `diriltme-kapisi.py`'de IKI bayat
  yorumun duzeltmesi. Onarimin KENDISI degismedi, yalniz gerekcesi olcume cekildi.
- **Surucu ne olcer:** gercek `git worktree add` + gercek pre-commit kancasi kurup kancadan
  cagrilan **6 aracin** kok cozum ifadesinin o baglamda hangi yolu dondurdugunu. GIT_DIR elle
  KURULMAZ; ihrac edilen degiskeni surucu RAPORDA BASAR.
- 🔴 **CURUTULEN TESHIS:** "ana checkout'ta GIT_DIR **GORELI** (`.git`) gelir, cagri basarisiz
  olur, kod ikinci adaya duser" YANLIS. Olculen: ana checkout `GIT_DIR='<yok>'` (kesif calisir,
  ILK aday zaten dogru) · linked worktree `GIT_DIR=<mutlak>`. Ikinci adaya HIC dusulmuyor.
- **Sayilar:** taranan arac **6** · olculen ifade **9** · ANA CHECKOUT kolunda yanlis kok cozen
  **0** · WORKTREE kolunda **2** (biri onarimin geri alindigi hal = sinifin gosterimi, biri
  BEYAN EDILEN SINIR). Kabul: surucu rc=0 · `--kanca-mutasyon` rc=0 **19 iddia** (korelme yok) ·
  `ci-kapsam-test.py` rc=0 · `mimar-commit-kapisi-test.py` rc=0 **26 vaka**.
- 🔴 **DUSURULEN IS (bagimsiz curutucu hukmu, MERGE EDILMEDI):** ayni turda hazirlanan
  mimar-commit-kapisi **kok sertlestirmesi** main'e ALINMADI. Curutucu davranissal etkisini
  GERCEK exit koduyla **dort baglamda da SIFIR** olctu: o kapi `kok != ANA_REPO -> return 0`
  der, worktree'de hem `<agac>` hem `<agac>/tools` ANA_REPO'dan farklidir → ayni hukum
  (tasarlanmis muafiyet). Ustelik sertlestirmenin kendisi realpath'siz dizge kiyasi yuzunden
  (E5 sinifina giren ayrinti ARSIVDE: DEVAM-ARSIV.md). Ayni turun diriltme onarimi da DUSURULDU: main'deki
  (`3aec9eba`) daha genis (85/19 iddia, W1..W4 vs 84/18, W1..W3).
  **DERS:** "kok yanlis cozuluyor" bulgusu tek basina kusur DEGIL — o kokun HUKMU degistirdigi
  gosterilmeli. Ayirt edici mutant yoksa eksen ayri iddia olarak main'e girmez.
  **Dusurulen dal SILINDI** (yerel + uzak). Kayit icin iki commit: `badc84a1` (mimar kapisi
  kok sertlestirmesi + 27-29 vakalari + M11) · `0d5ef292` (diriltme kok onarimi, main'deki
  `3aec9eba`'nin DAR ikizi). Kurtarilan tek parca `kok-cozum-taramasi.py` zaten `fd801a88`de.
- **BEKLEYEN 1 (2 IKIZ kok-turetme) ile iliski:** surucu tam da o soruyu olcumle yanitlayan
  arac; kardes oturum ayni sinifta calisiyor, mukerrer is riski var.
- 🔴 **YAYIN ACIK (depo kaynakli DEGIL):** `durum.py` §9 **ACLIK rc 4** — son 38 tamamlanmis
  kosumun **7'si IPTAL**, taranan 8 kosumda `deploy` isini BASARIYLA kosan kosum **YOK**, bir
  kosum **89 dk**dir bitmiyor (omur tavani 75 dk). `fd801a88` icin Actions'ta **hic kosum kaydi
  yok** (kuyruk `3aec9eba`'da queued/pending). Canli dogrulama **OLCULEMEDI — sebep: kuyruk**.
  Bu commit site icerigini degistirmiyor (yalniz `tools/`), yayin etkisi yok.

## 🟢 DIRILTME KUSURU KAPANDI — kayit cikarildi + alarmin TEK ATIMLIK sonmesi onarildi

Uc commit: `867c1b0d` (veri) · `a964d385` (kapi kolu) · `08b86c34` (taban). Ucu de push edildi.

- **Kayit CIKARILDI, mesrulastirilmadi.** Feed politikasi gerekcesiyle `c912548f`'te cikarilan
  id, bir toplu ekleme dilimiyle (`841aab67`) geri dirilmis, sonra borc tabanina yazilarak kapi
  susturulmustu. Karar: kayit sakincalidir -> `duzelt.py --sil`, **katalog 20850 -> 20849**,
  gizli kaynak kaydi da temizlendi. `.diriltme-izin.json` **ACILMADI**.
- **Parti taramasi:** **1073** id'lik yasak kumeye karsi dirilen = **1**. Alan gerilemesi = **0**.
- 🔴 **OLCULEN SINIF — alarm TEK ATIMLIKTI.** Yasak kume `ever_seen − <taban>` ile turuyor,
  ihlal commit'lendigi an bir sonraki tabana GIRIYOR ve alarm KENDI KENDINE SONUYOR.
  **Aynadaki tuzak:** tabani daha eskiye cekmek duyarliligi ARTIRMIYOR — ekle/sil/geri-ekle
  dongusunun tamami tabanin sonrasinda kalinca kayit "yeni id" sayiliyor ve kapi kor kaliyor.
- **ONARIM (`a964d385`):** pre-commit'e bloklayici `--calisma-agaci` kolu; `urunler.json`
  degismediyse tarama kosmuyor ama **gerekce BASILIYOR**; rc=2 OLCULEMEDI yesil sayilmiyor.
  Kabul **78 iddia rc=0**, sekizi DAVRANISSAL. Kontrol mutanti yeniden uretilebilir.
- **YAPISKAN EKSEN OLCULDU ve UYGULANMADI:** terk-edilmis ∩ HEAD = **18.227** id (**%87,4**).
  Esik 20'ydi; uygulansaydi yayin KALICI dururdu.
- **TABAN BOSALTILDI (`08b86c34`):** `kok` **7 -> 0** VE `kok_baslangic` **7 -> 0**, AYNI
  commit'te. Mandal geride biraksaydik ratchet 7 yeni borca kadar sessiz kalacakti — KARSI-OLGU
  olarak olculdu: `kok_baslangic`=7 iken 1 yeni borc eklenince uyari **URETILMEDI**.

## 🟢 BACKFILL GORSEL-GATE KALEMLERI KAPANDI — ARSIVDE (DEVAM-ARSIV.md)

## CI NOBETI 20:37Z turu — DEPO KAYNAKLI ARIZA 0, ENGEL DIS ARIZA (olculdu)

- Ev dogrulandi. Mail supurmesi **tasinan 0 / kalan 0** (7542 mesaj tarandi, eslesme yok).
- **Depo kaynakli hata 0:** son `failure` **17:08:46Z**; son 70 dk'da basarisiz kosum yok.
- **Dis ariza SURUYOR:** Actions+Pages **`major_outage`**, olay `investigating` 15:22Z'den beri,
  webhook **%15**e kisik → kuyruktakiler kosucu ALAMIYOR.
- **Yayin acigi 372 → 410:** canli **20.849 / 19.864.882 bayt**, yerel **21.259**; `?cb=` olcumu
  bayt-birebir ayni (**origin bayat, CDN degil**); en yeni urun sayfasi **404**.
- `pages` grubunu **17:37Z `ffc72a6a`** tutuyor (4 job 3 saattir `queued`, `cancel-in-progress:
  false`); en yeni push **`86246f46` 19:08Z** arkasinda `pending`. Bayat isgalciyi dusurme
  DENENDI → **`gh run cancel` HTTP 502 reddetti** (`rerun` gibi `cancel` de arizada gecmiyor);
  deneme 1 / basarili 0. Ariza gecince `deploy` **JOB** success'i + iki olcumle canli dogrulama.
  **Okan'da karar yok** (dis servis arizasi).

## CI NOBETI 11:37 / 15:37Z / 16:37Z / 19:37Z turlari — dokum `DEVAM-ARSIV.md`de (git disi).
