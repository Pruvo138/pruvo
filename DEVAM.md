# DEVAM (KraL) — 3 Agu 2026

Onceki ayrintili kayitlar DEVAM-ARSIV.md'de (git disi, lossless).

## 🔄 DEVIR — 3 Agu 2026 (hesap rotasyonu) · YENI OTURUM ONCE BURAYI OKU

Ritüel: `tools/DEVIR-KONTROL-LISTESI.md` (`2382c7f1`). Claude hesabi disinda **hicbir sey
degismedi** — git/GitHub/Cloudflare/D1/R2/hafiza diskte ve aynen duruyor.

**AGAC DURUMU: worktree 1 (yalniz main), `git status --short` BOS.** Tum worktree'ler kaldirildi;
uzerinde is olan her dal **origin'e itildi**, tek kopya kalan dal YOK. Devam etmek icin:
`git -C /Users/okan/dev/pruvo worktree add .claude/worktrees/<ad> <dal>`.
🔴 **Devir taramasinin dersi:** iki dal yalniz yerelde duruyordu, biri **detached HEAD**'de ve
uretici oturumu kapanmisti — worktree silinseydi commit'e ulasan ref kalmayacakti. Bundan sonra
devir listesinin 3. adimi (dallari push et) **her agac icin ayri ayri** kosulacak.

**✅ 1. IS — KAPANDI 3 Agu: merge `73149015` (dokum DEVAM-ARSIV.md'de).**

**✅ 2. IS — KAPANDI 3 Agu: merge `bd8b8abb` + onarim `78b6651f` (itildi).**
Kurtarilan dal `kurtarma/rulman-sema-araligi` (`89ab5da6`) merge kapisindan gecirildi.
Kapsam 6 dosya / +596 −3, merge-base `33ebff71`, cakisma YOK. `secenekler.js` ve `.github/`
DOKUNULMADI — satis allowlist'i acilmadi.
- **Kapi deltasi:** dalin getirdigi 3 yeni test `ci-kapsam-test.py`'yi KIRMIZI yakiyordu
  (ANA MAIN'de ayni kapi YESIL → dalin kusuru). Ucu de olculmus gerekceyle izin listesine
  yazildi; `deploy.yml`'de degisen satir **0**, hicbir kapi gevsetilmedi. Diger kapilar
  (kapi-envanteri · kisisel-veri · is-akisi · yayin-ic-dil · onizleme-vaat +kendini-test ·
  shop kabul 28/0 · fiyat-test 176 iddia) merge sonrasi agacta exit 0.
- **Mutasyon ayirt ediciligi (dalin kendi surucusu):** taban 22 iddia / 0 kirmizi;
  **12 olduruculuk mutanti KIRMIZI (isaret sartiyla) + 2 KONTROL mutanti YESIL**;
  kaynak butunlugu sha256 basta=sonda saglam.
- **Yan onarim:** olcum aracinin sifir-olcum kolu sertlestirildi; mutasyon kaniti
  eski kol rc=0 · yeni kol rc=3 (ayrinti DEVAM-ARSIV.md'de).
- **Parite (guncel main, ana checkout):** site 1199 sorgu BIREBIR · Ege 845 sorgu BIREBIR.
- **D1 uc eksen:** SAYI 16874==16874 · SEMA temiz · ICERIK 16874 hash birebir.

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
- ✅ **KAPANDI (3 Agu, main'de):** `onizleme-vaat-kapisi.py` A3 kuralinin kisit kaynagi
  birlestirildi — "kisitli aile" kumesi = ONIZLEME_KISITLAR ∪ semadaki `kisitlar` bloklari,
  tek sema okuyucudan turer. Kor nokta once olculdu (kopyada rulman/vida allowlist'e
  eklendiginde eski kapi rc=0 + A3 [OK]); simdi ikisi de A3'u tek basina kirmizi yakiyor.
  Sema okunamaz/bicim taninmaz ise A3 hic basilmaz, kosum OLCULEMEDI (fail-closed).
  Temiz agacta IDDIA 11 -> 12 (yeni A6 kapsam iddiasi), KIRMIZI=0, acik 17 ailede
  yanlis-pozitif yok; kendini-test 10 -> 19 mutant (10 oldurucu, 5 kontrol, 4 fail-closed).
  🟡 Rulman satisa ACILMADI — allowlist'e dokunulmadi, karar hala BENDE.

**MERGE EDILMEDIGI ICIN ACIK KALAN IKI KARAR (isci sordu, ben cevaplamadim):**
1. `build.py`'deki `gecersiz-parca` kolu ayni "siparis verebilirsiniz, uretim etkilenmez"
   cumlesini tasiyor. Isci farkli eksen oldugu icin (2-renk siparisi gercekten var ve ≥10 mm
   kenar kontroluyle korunuyor) dokunmadi — **olculmesi gerekip gerekmedigi karar.**
2. `varlik-test.py` 2. ekseni "sayfa JS'i dondurulmus referans commit'ten sonra hic degismesin"
   diyor; muafiyet listesi her sayfa-JS duzenlemesinde buyuyecek. **Referans ilerletilmeli ya da
   eksen gercek cikarim kaybina daraltilmali** — bu tur dokunulmadi.

**BENDE — acik kalemler, oncelik sirasiyla:**
0. ✅ **KAPANDI (`78676775`)** — hacim tahsilat mutanti artik CI'da bloklayici kapida olculuyor
   (dokum DEVAM-ARSIV.md'de). **Kalan:** satisa acik 7 aile (huni, izgara, kasnak, kayis, oring,
   pervane, profil) icin altisi uretim motoru referansi istiyor → **Okan kapisi** (butce/erisim).
   Kapsam disi olcum (fikstürde beyanli): `rampa` sapma **%24,7**, `profil` sapma **%0,1469**.
   (Hangi kapinin hangi aileyi kapsamadigina dair detay: DEVAM-ARSIV.md.)
1. 🔴 **YAPISAL:** siparis/odeme yolu uretilebilirligi SORMUYOR. Allowlist yara bandi; her yeni
   aile ayni riski yeniden aciyor. Dogru cozum: odeme yolunun derleyiciye/uretilebilirlik
   kapisina sormasi. **Ders:** aile satisa acarken sorulan soru "fiyat dogru mu" idi; ikinci soru
   **"bu parametrelerin hepsi uretilebilir mi"** olmaliydi — hacim dogrulamasi onu kapsamiyor.
2. `worktree-agent-aadc8e1d5df8ff4b0` (`3ef8b81a`) — ci-kapsam dar-bayrak dali, **curutme SARTLI
   dondu, sart uygulanmadi**: kovaya eklenen js bayraklarinin **%81'i uydurma** (baska programa
   gecirilen `--cached`/`--dry-run` gibi argümanlar dosyanin kendi bayragi sayiliyor). Dalin asil
   degeri duruyor: **6 dosya yalniz `--kendini-test` ile kosuyor** (`jenerator/test/kabul.py`
   dahil) — bugunku fiyat alarminin aylarca gorunmemesinin sebebi buydu. Ya sartla tamamla ya
   acikca park et.
3. 🔴 **Tek kanonik marka fonksiyonu — ve bu kusur ARTIK URETIMDE OLCULDU.**
   Uc ayri mantik var (`index.html` `markaKatla` · uc `uyumEkseniKosulu` · `parite-test.js` tam
   jeton) ve **1.677 cip degerinin 1.518'inde** ucu ayrisiyor.
   **Canli tam supurme (1.081 kombinasyon, `3569bb97` sonrasi): 12 OLU UC** — `Marin/Volvo` 11 +
   `Otomobil/Kia` 1 — ve **159 sayi sapmasi** (uc >0 ama indeksin dedigi sayidan farkli).
   Kok neden: `cip-indeks.py` cipi **katlanmis** etiketle uretiyor, uc **ham** etiketi esliyor →
   `marka=Volvo` **0**, `marka=Volvo Penta` **51** (katalogda "Volvo" etiketi hic yok).
   **Gerileme DEGIL** — `9f491fcf` tabaninda da vardi, olculdu. Ama paketin mansset iddiasi
   ("gorunen her cip >0") uretimde bu 12 kombinasyonda **TUTMUYOR**, ve kabul testi bunu
   yakalamiyor cunku **fikstürün uc simulatoru de katliyor** — yani test, uretimi degil kendi
   varsayimini aynaliyor. Bu oturumun tekrar eden sinifi.
   Surucu hazir ama repoda DEGIL: scratchpad `kr-tam-supurme.py` — kalici hale getirilmeli.
4. **Merge kapisi eksigi (bugun iki kez isirdi):** kapi kumesi dalin *dokundugu alandan*
   turetiliyor; `index.html` gibi cok kapili dosyada asil kume **`deploy.yml`'in kendisi**.
   Ilk kirmizi ikinciyi maskeliyor. `~/.claude/skills/merge-kapisi/SKILL.md`'ye madde eklenecek
   (dosya git disi, elle duzenlenir, degistirince `tools/yedekle.py` kostur).
5. Marin'in **bolunemeyen 486 urunu**: `Olta Ekipmanlari` 277 + `Montaj Ekipmanlari` 209 — ne
   marka, ne model, ne `tur` verisi var; Okan'in **200 kurali** orada saglanamiyor.
6. HocA'dan devralinan iki site metni kalemi: SSS'de havale/EFT yok · "Yurtici Kargo" ifadesi
   siteden cikacak (Notion'da 8 tasiyici var, tek tasiyici degiliz).

**BEKLIYOR — baskalarinda:** KaaN: `rulman` semasi onarilinca satisa acma karari bende ·
ArTisT: marka-model sayfasi acma esigi onerisi (veri verildi: 1.062 marka-model ciftinin 812'si
5'ten az urun) · HocA: bende bekleyen yok.

## AÇIK KALEMLER — önceki turlardan (kısaltıldı, taşınmadı)
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
