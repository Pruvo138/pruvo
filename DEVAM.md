# DEVAM (KraL) — 3 Agu 2026

Onceki ayrintili kayitlar DEVAM-ARSIV.md'de (git disi, lossless).

## 🔄 DEVIR — 3 Agu 2026 (hesap rotasyonu) · YENI OTURUM ONCE BURAYI OKU

Ritüel: `tools/DEVIR-KONTROL-LISTESI.md` (`2382c7f1`). Claude hesabi disinda **hicbir sey
degismedi** — git/GitHub/Cloudflare/D1/R2/hafiza diskte ve aynen duruyor.

**AGAC DURUMU (3 Agu, olculdu): worktree 1 (yalniz main).** Uzerinde is olan her dal origin'e itildi;
uzerinde is olan her dal **origin'e itildi**, tek kopya kalan dal YOK. Devam etmek icin:
`git -C /Users/okan/dev/pruvo worktree add .claude/worktrees/<ad> <dal>`.
🔴 **Devir taramasinin dersi:** iki dal yalniz yerelde duruyordu, biri **detached HEAD**'de ve
uretici oturumu kapanmisti — worktree silinseydi commit'e ulasan ref kalmayacakti. Bundan sonra
devir listesinin 3. adimi (dallari push et) **her agac icin ayri ayri** kosulacak.

**✅ 1. IS — KAPANDI 3 Agu: merge `73149015` (dokum DEVAM-ARSIV.md'de).**

**✅ 2. IS — KAPANDI 3 Agu: merge `bd8b8abb` + onarim `78b6651f` (dokum DEVAM-ARSIV.md'de).**

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
0. ✅ **KAPANDI (`78676775`)** — hacim tahsilat mutanti artik CI'da bloklayici kapida olculuyor
   (dokum DEVAM-ARSIV.md'de). **Kalan:** satisa acik 7 aile (huni, izgara, kasnak, kayis, oring,
   pervane, profil) icin altisi uretim motoru referansi istiyor → **Okan kapisi** (butce/erisim).
   Kapsam disi olcum (fikstürde beyanli): `rampa` sapma **%24,7**, `profil` sapma **%0,1469**.
   (Hangi kapinin hangi aileyi kapsamadigina dair detay: DEVAM-ARSIV.md.)
1. 🔴 **YAPISAL — ISCIDE OLCULUYOR (3 Agu):** siparis/odeme yolu uretilebilirligi SORMUYOR.
   Allowlist yara bandi; her yeni aile ayni riski yeniden aciyor. Dogru cozum: odeme yolunun
   derleyiciye/uretilebilirlik kapisina sormasi. **Ders:** aile satisa acarken sorulan soru
   "fiyat dogru mu" idi; ikinci soru **"bu parametrelerin hepsi uretilebilir mi"** olmaliydi.
   **Kosan olcumun ayirt ettigi ikilem:** sema `kisitlar` blogu TEHLIKE isareti mi, KORUMA mi?
   Siparis yolu kisitlari UYGULUYORSA koruma → A3'un KOL2 kolu fazla kati, daraltilmali;
   UYGULAMIYORSA A3 dogru ve asil kusur odeme yolunda. **Rulman satisa acma karari buna bagli.**
   ✅ **736 KAPANDI (`d8024a27`, dokum DEVAM-ARSIV.md'de) — MaCiT'te yazim: `urunler.json`, 21 kayit, alan `marka`.**
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
   ✅ **Bugun ELLE deploy edildi (Okan onayiyla): `ac6864e3` canlida** — surum
   `cecc9d4f`, oncesi `9d5ab6ed` (rollback hedefi kayitli, kosulmadi). Bundle **13 sa 15 dk**
   eskiymis. **34 olcum onaylanan tabloya BIREBIR uydu** (ayni 21 · kapali→fiyat 12 · kurus
   degisen 1 · beklenmeyen **0**); canli SONRA = yerel `ac6864e3` **34/34 fark 0**. L1
   `hacim-dogrulanmamis` → `parametre-araligi`, `kutu` 15.000 kurus (kapi kor degil), `rulman`
   ACILMADI. 🔴 **KALEM ACIK: CI hala Worker yayinlamiyor.**
1c. 🟡 **YENI (kutudan, karar bende):** (a) **HocA** — `sss/` **POM** vaat ediyor, `ege-bilgi.md`
   kapsaminda POM YOK; ya uretiliyor (bilgiye eklenir) ya metin bayat (SSS'den cikar) — uretim
   kapasitesi karari. (b) **KaaN** — `rampa.json` `"motor":"pruvo"` beyani `aileler/rampa.js`
   formuluyle celisiyor (%15,37 / %17,65 / %20,30); KaaN olcuyor, yargi bende.
2b. **PARK — mukerrer dal:** `claude/upbeat-kapitsa-d7c9ac` (`36bf4a06`, worktree
   `.claude/worktrees/upbeat-kapitsa-d7c9ac`) A3 kor noktasini PARALEL onarmis (13 mutant).
   Benim surumum (`193cd6f0`) main'de ve daha genis (19 mutant + A6 kapsam iddiasi) → dal
   **cakisir, merge EDILMEYECEK**. Alinacak tek sey ondaki **`A1c` iddiasi** — once ayirt edici
   mutanti var mi olculecek, varsa ayri turda tasinacak, sonra dal+worktree silinecek.
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

**✅ KAPANDI 3 Agu: merge `242e4496` — uyum kapisi yorumundaki bayat mutant sayisi (dokum DEVAM-ARSIV.md'de).**

**✅ KAPANDI 3 Agu: merge `88f3e63d` + kablolama onarimi `7fc61f98` — shop worker BAYATLIK NOBETI.**
Olculen delik: yayin akisinda worker yayin adimi vurusu **0** (30 "wrangler" satirinin hepsi
YORUM) -> canli bundle **13 sa 15 dk** bayat kaldi, hicbir alarm calmadi. Yeni
`tools/shop-bayatlik-kapisi.py`: bundle dosya kumesini ITHALAT GRAFINDAN turetir (**42 dosya** —
elle liste `secenekler.js`/`jenerator/*`'i kacirirdi), canli KOD surumunu okur ve main'den kac
commit geride oldugunu basar. **Esik 120 dk**, gerekcesi olculen dagilimdan (73 commit; ayni
oturumda deploy edilen kumenin maksimumu 89,2 dk; olay 795 dk). Dort hal: taze/bekliyor rc 0 ·
bayat rc 1 · **olculemedi rc 2** (ag/yetki yoksa "guncel" varsayilmaz).
Kabul testi **32 iddia / 0 kirmizi** (bloklayici, `build`); curutme `tools/shop-bayatlik-mutasyon.py`
**12 mutant / 0 sapma** (kontrol mutanti dahil, kaynak sha256 bas=son). Canli kol
`paket-tazelik-alarmi.yml`de (cron 15 dk) — yayini DURDURMAZ; **korluk penceresi 795 dk -> <=15 dk.**
CI'da olculdu (kosum `30822060140`): mevcut CI kimligi salt-okuma dagitim/surum listesi icin
YETIYOR, adim 12,6 sn, durum TAZE (aktif surum `cecc9d4f`, 0 commit geride).
🔴 Bu turun iki dersi (ikisini de KAPI yakaladi, goz degil): (1) adimi komsu adimin yanina
koymak IS sinirini gormez — adim `serit-b`ye dustu, "bloklayici" iddiasi yalandi, is akisi bicim
kapisi kirmizi yakti (bir kosum yayin durdu, kosum `30822306545`); (2) GitHub `if:` kosullarina
ortuk `success()` ekler — yeni adim damga adimlarindan once durunca kirmizi bir olcum damgayi
atlatip nabiz A4'u yanlis yakiyordu, adim isin sonuna alindi.
ACIK (mimar karari): kanal ZAMAN temelli — bayat AGACTAN yapilan deploy taze gorunur; kimlik
temelli hukum icin bundle'a commit damgasi + okuma ucu gerekir (bir deploy penceresi ister).

## ✅ ONIZLEME KISIT BEYANI KOSULLU HALE GETIRILDI — merge `45f30fd7` (3 Agu)
Vida/civata kolu disindaki M3-M4 bolgesi artik yanlis bloklanmiyor; kisit yargisi tek kaynakta
toplandi, uc katmanli kabul testi CI'ya bagli. Olculen sayilar (dal + bagimsiz curutucu):
- kapsam: 5 dosya, +660/−14 · cakisma 0 · sizinti 0 · kapilar 10/10 rc=0
- parite: `parite-test.js` 1199 + `parite-ege.js` 845 sorgu birebir
- kabul: 12 iddia · mutasyon 19/19 mutant PASS (her biri once KIRMIZI) · yeni test dosyasi 43 iddia
- vida izgarasi: yeni biçimde blok 2/44 · eski biçimde 8/44 (yanlis bloklanan 6 nokta acildi)
Merge ff-only yapildi (merge commit yok, baska oturumun staged dosyasi supurulmedi).
D1 teyidi merge sonrasi: 17010 == 17010, hash uyusmazlik 0.

## ✅ YAYIN ERİŞİM NÖBETÇİSİ — merge `7e2277c0` (3 Ağu)
Kapatılan sınıf: yayınlanan içeriğin ÜRETİLDİĞİ ölçülüyordu, ERİŞİLEBİLDİĞİ ölçülmüyordu
(üç landing 12 gün 403 döndü, her kapı yeşildi). Yeni: `tools/yayin-erisim-nobeti.py`
(+ `-test.py`, `-mutasyon.py`) ve saatlik `.github/workflows/yayin-erisim-alarmi.yml`.
- küme: `sayfalar.py::SITEMAP_SLUGS` ∪ hub ∪ kök ∪ build manifesti ∪ yerel sitemap (elle
  liste yok); yerelde 295, CI'da 306 URL; taban altı küme = ÖLÇÜLEMEDİ
- yöntem GET (HEAD 200 / GET 403 ölçüldü) · 200 dışı KAPALI · 3xx zinciri izlenir
- bugünkü canlı ölçüm: 295 URL · 292 açık · 3 kapalı (403, `/araba-…` `/arac-…`) · 166 s
- kabul: 48 iddia · 16 öldürücü + 4 kontrol mutantı, 7 eksenin hepsinde tek-kırmızı mutant
- kol seçimi: canlı ölçüm deploy.yml'e BAĞLANMADI (ağ bağımlı yanlış-pozitif tüm yayını
  durdurur); cron alarm kolu, `push` tetikleyicisi yok, ayrı concurrency, `|| true` yok
- kapılar dal↔main delta 0 (ci-kapsam · is-akisi · kisisel-veri · cron-nabiz · yayin-gecikme)
- CI: koşum 30844877057 (headSha 7e2277c0) `serit-b` success, adım logunda 48/48
- D1 merge sonrası: 17030 == 17030, hash uyuşmazlık 0

## ✅ ÖNİZLEME KISIT KOŞUL DEĞERİ FAIL-CLOSED — merge `f6f6492d` (3 Ağu)
`45f30fd7`in üstüne: `eger` koşulunun DEĞER eşleşmesi sertleştirildi, kural artık şemadan
türüyor — `secim` → tanımlı seçenek üyeliği, `sayi` → sayı/sayısal-metin + `gecerliDegerler`,
bilinmeyen tip → ihlal. Docstring garanti metniyle davranış eşitlendi (ikiz tanım tek kaynaktan).
- kabul: `onizleme-kisit-kosul-test.py` **43 → 115 iddia**; 5 öldürücü mutant kırmızı, 2 kontrol
  mutantı yeşil
- vaat kapısı: 12 iddia + 19/19 mutant · parite `parite-test.js` **1199 sorgu birebir**
- vida ızgarası: 44 konfigürasyonda bloklu küme **tam olarak 2** (`civata-M3`, `civata-M4`)
- CANLI DOĞRULANDI: koşum `30846897166` (`51588d55`, `f6f6492d` atası) success, `deploy`+`yayin`
  skipped DEĞİL. Canonical `secenekler.js`: 3-argümanlı `onizlemeKisitIhlali` imzası 1,
  `kosulDegeriEslesebilirMi` 2, vida girdisi 1; `age: 0`, `cf-cache-status: MISS` (bayat önbellek
  değil). D1: 17032 == 17032, üç eksen temiz.

**Yayın hattı bu turda İKİ KEZ yabancı kırmızıyla kesildi — ikisi de GERÇEK sapma değil BAYAT
BEKLENTİ olarak sınıflandırıldı:**
1. `yayin-ic-dil-kapisi --kaynak` 13 ihlal → başka oturum `e86bbf8a` ile kapattı.
2. `marka-uyelik-test.py` bayat yüklem: marka sayfası evreni artık ÇİP EVRENİNDEN türüyor, test
   ise küratörlü listeyi tutuyordu. Sapan 13 markanın hepsi küratörlük dışı çip markası, sayfada
   eksik ürün **0**; 727 sapanın **704**'ünde testin "birincil"i hesaplanamıyor, **23**'ünde
   uyumluluk markasına gidiyordu. Başka oturum `51588d55` ile kapattı.
   → Aşağıdaki AÇIK KALEMLER'in "🔴 YAYIN DURUYOR … `marka-uyelik-test.py`" maddesi bu tur KAPANDI.

**AÇIK KALEM:** `claude/marka-uyelik-tazeleme` (`a9c7a22d`) **merge EDİLMEYECEK**; yalnız hasat
edilecek bir FAZLA nöbetçi taşıyor — genişletilmiş marka ekseni bir gün boşalırsa "sapan: 0"
iddia değil boş kümenin sessizliğidir (ölçüm: çip evreni 49, küratörlük dışı 13).

**AÇIK KALEM:** CI yayın açlığı — `build` ~35 dk, ürün push'ları eşzamanlılıkla koşan koşumu
iptal ediyor (3 Ağu'da 5 iptal). Ayrı oturumda ele alınıyor.

## AÇIK KALEMLER — önceki turlardan (kısaltıldı, taşınmadı)
- 🔴 YAYIN DURUYOR (başka düzlem, 3 Ağu 19:26): `build` adım 32 `marka-uyelik-test.py`
  KIRMIZI → `deploy` skipped. Sapan marka 13 (marka sayfası ↔ index filtresi), ürün çip
  haritası 727 kayıtta birincil markaya gitmiyor. Merge'ümden ÖNCE de kırmızıydı
  (01c58587 18:58, 9f7ee22f 19:05) — marka/çip düzleminin sahibine ait.
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
