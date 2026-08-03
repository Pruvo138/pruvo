# DEVAM (KraL) — 3 Agu 2026

Onceki ayrintili kayitlar DEVAM-ARSIV.md'de (git disi, lossless).

KAPANDI 3 Agu: oturum kapanisi SHA dokumu (DEVAM-ARSIV.md'de).

## 🔄 DEVIR — 3 Agu 2026 (hesap rotasyonu) · YENI OTURUM ONCE BURAYI OKU

Ritüel: `tools/DEVIR-KONTROL-LISTESI.md` (`2382c7f1`). Claude hesabi disinda **hicbir sey
degismedi** — git/GitHub/Cloudflare/D1/R2/hafiza diskte ve aynen duruyor.

**AGAC DURUMU (3 Agu, olculdu): worktree 1 (yalniz main).** Uzerinde is olan her dal origin'e itildi;
uzerinde is olan her dal **origin'e itildi**, tek kopya kalan dal YOK. Devam etmek icin:
`git -C /Users/okan/dev/pruvo worktree add .claude/worktrees/<ad> <dal>`.
🔴 **Devir taramasinin dersi:** iki dal yalniz yerelde duruyordu, biri **detached HEAD**'de ve
uretici oturumu kapanmisti — worktree silinseydi commit'e ulasan ref kalmayacakti. Bundan sonra
devir listesinin 3. adimi (dallari push et) **her agac icin ayri ayri** kosulacak.

**🔴 ACIK — 4 Agu CI nobeti: yayin hatti bir tur bloklandi; kok neden + kimlik dokumu DEVAM-ARSIV.md'de (git disi). Duzeltme baska mimarin duzlemi, posta kutusuna yazildi.**

**✅ 1. IS — KAPANDI 3 Agu: merge `73149015` (dokum DEVAM-ARSIV.md'de).**

**✅ 2. IS — KAPANDI 3 Agu: merge `bd8b8abb` + onarim `78b6651f` (dokum DEVAM-ARSIV.md'de).**

**KAPANDI 3 Agu: 3. IS yayin hatti acligi + build duvar saati — `2c016309` (dokum DEVAM-ARSIV.md'de).**

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
- ✅ **A3 kor noktasi KAPANDI (`193cd6f0`, dokum DEVAM-ARSIV.md'de). 🟡 Rulman satisa ACILMADI — karar hala BENDE.**

**MERGE EDILMEDIGI ICIN ACIK KALAN IKI KARAR (isci sordu, ben cevaplamadim):**
1. `build.py`'deki `gecersiz-parca` kolu ayni "siparis verebilirsiniz, uretim etkilenmez"
   cumlesini tasiyor. Isci farkli eksen oldugu icin (2-renk siparisi gercekten var ve ≥10 mm
   kenar kontroluyle korunuyor) dokunmadi — **olculmesi gerekip gerekmedigi karar.**
2. `varlik-test.py` 2. ekseni "sayfa JS'i dondurulmus referans commit'ten sonra hic degismesin"
   diyor; muafiyet listesi her sayfa-JS duzenlemesinde buyuyecek. **Referans ilerletilmeli ya da
   eksen gercek cikarim kaybina daraltilmali** — bu tur dokunulmadi.

**BENDE — acik kalemler, oncelik sirasiyla:**
0. KAPANDI `78676775`; kalan: satisa acik ailelerin altisi uretim motoru referansi istiyor -> Okan kapisi (dokum DEVAM-ARSIV.md'de).
1. 🔴 **YAPISAL — ISCIDE OLCULUYOR (3 Agu):** siparis/odeme yolu uretilebilirligi SORMUYOR.
   Allowlist yara bandi; her yeni aile ayni riski yeniden aciyor. Dogru cozum: odeme yolunun
   derleyiciye/uretilebilirlik kapisina sormasi. **Ders:** aile satisa acarken sorulan soru
   "fiyat dogru mu" idi; ikinci soru **"bu parametrelerin hepsi uretilebilir mi"** olmaliydi.
   **Kosan olcumun ayirt ettigi ikilem:** sema `kisitlar` blogu TEHLIKE isareti mi, KORUMA mi?
   Siparis yolu kisitlari UYGULUYORSA koruma → A3'un KOL2 kolu fazla kati, daraltilmali;
   UYGULAMIYORSA A3 dogru ve asil kusur odeme yolunda. **Rulman satisa acma karari buna bagli.**
   KAPANDI 736: `d8024a27` (dokum DEVAM-ARSIV.md'de).
2. `worktree-agent-aadc8e1d5df8ff4b0` (`3ef8b81a`) — ci-kapsam dar-bayrak dali, **curutme SARTLI
   dondu, sart uygulanmadi**: kovaya eklenen js bayraklarinin **%81'i uydurma** (baska programa
   gecirilen `--cached`/`--dry-run` gibi argümanlar dosyanin kendi bayragi sayiliyor). Dalin asil
   degeri duruyor: **6 dosya yalniz `--kendini-test` ile kosuyor** (`jenerator/test/kabul.py`
   dahil) — bugunku fiyat alarminin aylarca gorunmemesinin sebebi buydu. Ya sartla tamamla ya
   acikca park et.
1b. 🔴 **YAPISAL — YENI (3 Agu, olculdu): Worker CI'da YAYINLANMIYOR.** `deploy.yml`'de
   `wrangler deploy/publish` **0 vurus** → her `worker/`+`shop/src` degisikligi ELLE deploy
   bekliyor ve **hicbir alarm calmiyor**. Olculen sonuc: canli bundle **2 Agu 23:35'ten
   (`f1594d68`) bayat** kaldi; `f1594d68..HEAD` arasinda bundle girdilerine dokunan **10 commit**
   birikti. Yani main yesil, CI yesil, site taze — ama **odeme yolu eski kodu kosuyor.**
   Sinif: bugunku tekrar eden sinif — beyan edilmis nobetci, olculmemis kapsam.
   Cozum yonu (karar bende): ya CI'ya Worker yayin adimi + bayatlik nobetcisi (canli bundle
   hangi commit'i tasiyor, kac commit geride), ya da elle deploy ritueli kapiya baglanir.
   KAPANDI 3 Agu: elle deploy `ac6864e3`; KALEM ACIK: CI hala Worker yayinlamiyor (dokum DEVAM-ARSIV.md'de).
1c. 🟡 **YENI (kutudan, karar bende):** (a) **HocA** — `sss/` **POM** vaat ediyor, `ege-bilgi.md`
   kapsaminda POM YOK; ya uretiliyor (bilgiye eklenir) ya metin bayat (SSS'den cikar) — uretim
   kapasitesi karari. (b) **KaaN** — `rampa.json` `"motor":"pruvo"` beyani `aileler/rampa.js`
   formuluyle celisiyor (%15,37 / %17,65 / %20,30); KaaN olcuyor, yargi bende.
2b. **PARK — mukerrer dal:** `claude/upbeat-kapitsa-d7c9ac` (`36bf4a06`, worktree
   `.claude/worktrees/upbeat-kapitsa-d7c9ac`) A3 kor noktasini PARALEL onarmis (13 mutant).
   Benim surumum (`193cd6f0`) main'de ve daha genis (19 mutant + A6 kapsam iddiasi) → dal
   **cakisir, merge EDILMEYECEK**. Alinacak tek sey ondaki **`A1c` iddiasi** — once ayirt edici
   mutanti var mi olculecek, varsa ayri turda tasinacak, sonra dal+worktree silinecek.
3. 🔴 **Tek kanonik marka fonksiyonu — URETIMDE OLCULDU.** Uc ayri mantik (`index.html`
   `markaKatla` · uc `uyumEkseniKosulu` · `parite-test.js` tam jeton), **1.677 cip degerinin
   1.518'inde** ayrisiyor. Kok neden: cip **katlanmis**, uc **ham** etiket esliyor.
   Kabul testi yakalamiyor cunku **fikstürün uc simulatoru de katliyor**.
   Surucu scratchpad'de `kr-tam-supurme.py` — repoya alinacak. (Dokum DEVAM-ARSIV.md'de.)
4. **Merge kapisi eksigi (bugun iki kez isirdi):** kapi kumesi dalin *dokundugu alandan*
   turetiliyor; `index.html` gibi cok kapili dosyada asil kume **`deploy.yml`'in kendisi**.
   Ilk kirmizi ikinciyi maskeliyor. `~/.claude/skills/merge-kapisi/SKILL.md`'ye madde eklenecek
   (dosya git disi, elle duzenlenir, degistirince `tools/yedekle.py` kostur).
5. Marin'in **bolunemeyen 486 urunu**: `Olta Ekipmanlari` 277 + `Montaj Ekipmanlari` 209 — ne
   marka, ne model, ne `tur` verisi var; Okan'in **200 kurali** orada saglanamiyor.
6. HocA'dan devralinan iki site metni kalemi: SSS'de havale/EFT yok · "Yurtici Kargo" ifadesi
   siteden cikacak (Notion'da 8 tasiyici var, tek tasiyici degiliz).

**BEKLIYOR — baskalarinda (ACIK, arsive tasinmaz):**
- **HocA** → `ara*` rota oneki 3 landing'i 403 yapiyor (12 gundur; onarim
  `~/dev/pruvo-bot/worker/wrangler.toml`, Okan kapisi onda).
- **MaCiT** → eksik marka verisi (Garmin 54 · Sea-Doo 14+4 · Simrad 7 · B&G 3 · Bavaria 3) +
  POM tasiyan **11 urun kaydi** + bilesik marka yazimi (21 kayit, alan `marka`).
- **KaaN** → `rulman` semasi onarilinca satisa acma karari bende.
- **ArTisT** → marka-model sayfasi acma esigi onerisi (1.062 ciftin 812'si 5'ten az urun).

**KAPANDI 3 Agu: uyum yorumu, Worker bayatlik, onizleme kisitlari ve yayin erisimi — `242e4496` `88f3e63d` `7fc61f98` `45f30fd7` `7e2277c0` `f6f6492d` (dokum DEVAM-ARSIV.md'de).**
## AÇIK KALEMLER — önceki turlardan (kısaltıldı, taşınmadı)
- KAPANDI 3 Agu: marka uyelik ikiz tanimi — `51588d55` (dokum DEVAM-ARSIV.md'de).
- 3 landing hâlâ canlıda 403: onarım kardeş depodaki worker rota deseninde (önek jokeri),
  bu depoda değil; nöbetçi o kapalılığı artık saatlik ölçüyor ve kırmızı yakıyor.
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
