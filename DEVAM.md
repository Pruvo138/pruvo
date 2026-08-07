# DEVAM (KraL) — 7 Agu 2026

## ⏱ SAATLIK CI NOBETI — 7 Agu 10:37 turu (ev DOGRU: ~/dev/pruvo)

**Mail supurmesi (kosulsuz, her tur):** tasinan **3** · tur sonu inbox'ta "Run failed" **0**
(inbox toplami 7541). Cop BOSALTILMADI. Alakasiz maile dokunulmadi — Cop'teki eslesmeyen kova
islem boyunca **14..14** sabit kaldi (adli teyit).

**Olculen CI (HEAD `9969e256`):**
- 🔴 `r2-onek-nobeti` (nobet.yml, `deploy: needs`'te DEGIL → yayini durdurmaz) **7 kosumdur ust
  uste kirmizi**; ilk kirmizi kapinin girdigi merge `e3880c89`. Kok neden **TEK DEGIL, IKI**:
  - **B2 = gercek veri sapmasi** — 1 kayit bilinmeyen `x` onekli R2 anahtariyla yayinda
    (`raymarine-st60-...` → `xraymarine-st60-...`). **MaCiT duzlemi**, nobetin YASAK listesinde
    `urunler.json` var → DOKUNULMADI, olcum posta kutusuna yazildi. (DEVAM'daki bilinen acik kalem.)
  - **E3/E4 = ortam eksikligi** — ikiz tanim kaynagi kardes (private) depoda, workflow yalniz bu
    depoyu checkout ediyor → yol runner'da **hicbir zaman var olmayacak**. HEAD'deki kapi bu
    eksikligi `ok=False` ile **gercek kirmizi** sayiyor (metinde "OLCULEMEDI" yazsa da notr ucuncu
    hal DEGIL) → deterministik kalici kirmizi. **Onarim ZATEN UCUSTA:** kardes oturumun calisma
    kopyasinda `M tools/r2-onek-gelenek-kapisi.py` (+144 satir, capa fallback + gercek notr
    OLCULEMEDI ekseni). **Yabanci degisiklige dokunulmadi/commit'lenmedi.** → [[olculdu-diyen-hukum-kaniti]]
- 🔴 `serit-a3` adim **"Ic rapor adi kapisi"** kosum `31168200266`'da (headSha `3f5b62aa`) dustu —
  bu job `deploy: needs`'te, yani **yayini DURDURUR**. Onarimi **baska bir oturum** HEAD `9969e256`
  ile push etmis (benim onarimim DEGIL). Teyit BEKLIYOR: kosum `31170570974` hala **pending**,
  cunku `pages` grubunu `31168200266`'nin `serit-a4` bataryasi tutuyor (~50+ dk, bilinen kalem 5).
- 🟢 D1 sapma sinifi **kendiliginden kapandi**: `d1-kadans / uzlastir` HEAD'de success, bagimsiz
  uzlastirici kosumu `31170816343` success. (`197fd396`'daki kirmizisi gecti.)
- ⚪ `5f5ae7b9`'da ayri sinif: `yayin` job'u "Atomik yayin" adiminda dusmustu — HEAD'de tekrar
  edip etmedigi kosum sirada bekledigi icin **OLCULEMEDI** (yesil DEGIL).

**Tur sonu olculen (nobet.yml `31170571384` TAMAMLANDI):** `serit-b` · `envanter` · `mesaj-nobeti` ·
`cron-nabzi` · `d1-kadans` **success**, tek kirmizi **`r2-onek-nobeti`** → yani o seritte
**baska hicbir arıza yok**, kirmizi tek kaynakli.

**`serit-a3` icin LOKAL SINYAL (yesili sahiplenmiyorum — onarim `9969e256`, BASKA oturumun):**
o commit yalnizca `tools/kisisel-veri-test.py`'yi degistiriyor (1 satir) ve bu tur o arac
lokalde kosuldu → **rc=0, tum alt-nobetciler YESIL** (327 sayfa · 535 dosya · ic rapor nobetcisi
Kural A 23 kirmizi+35 yesil fikstur, Kural B 28 kirmizi+20 yesil fikstur). Beklenti guclu ama
**CI'da OLCULMEDI** — kosum hala sirada.

**⚠️ SONRAKI COMMIT ICIN TUZAK (bende DEGIL, haber veriyorum):** `devam-sinif-kapisi.py` su an
**rc=1 / 6 ihlal** basiyor (iki ayri sinif; dokumu ARSIVDE). Ihlallerin TAMAMI
DEVAM.md'nin **commit'lenmemis** bolumunde — `git show --stat` ile olculdu: DEVAM.md ne `9969e256`
ne `3f5b62aa` icinde, yani **commit'li HEAD TEMIZ** ve siradaki build bu yuzden patlamayacak.
AMA DEVAM.md'yi bir sonraki commit'leyen `build`'i kirar → `deploy`+`yayin` **skipped** (3 Agu'daki
olayin aynisi). Ilgili satirlar arsive tasinmali (silme degil TASIMA).
**Kendi blogumu AYRI olcturdum** (kapi iki kez kosuldu): toplam **6..6 DEGISMEDI**, benim
blogumda **0** — yani not eklemek kapiyi tetiklemedi. (Ilk yazimda sinif adlarini birebir
yazmistim; ilgili hafiza dersi geregi genel ifadeye cevirdim, dokum arsivde — capa adi da orada.)
→ [[nobet-kendi-defteri-yayini-durdurur]]

**`serit-a4` suresi (kalem 5 icin taze sayi):** basladi **10:19:45Z**, tur kapanirken hala
kosuyordu → **≥46 dk**, bilinen 42-50 dk bandinin ICINDE (anomali degil). `pages` grubunu
bu job tutuyor, HEAD kosumunun sirada beklemesinin sebebi bu.

**DEVIR — sonraki turun ILK isi:** `31170570974` kosumunun `serit-a3` + `deploy` + `yayin`
JOB'larini olc (sifirdan teshise BASLAMA). Beklenen: `serit-a3` yesil (baskasinin onarimi).
Hala kirmizi ise kok neden ayni demektir → **DUR kosulu** yaklasiyor.

**Codex NOT:** kredi kotasi **TUKENDI** (yenilenme 8 Agu 10:19) → bu turun teshisi Claude iscisine
dustu. Sonraki tur da Codex'siz planlanmali.

## 🔚 OTURUM KAPANISI — 7 Agu · YAYIN ZINCIRINDEKI 4 ENGELIN 4'U KALKTI

**MAIN'E GIREN (SHA + olculen sayi):**
1. **Varlik kaldiraci `8bbd760c`** — atif modulu her urun sayfasindan tek same-origin varliga.
   Artefakt **833,6 → 617,1 MiB** (1 GB tavaninda **%81,4 → %60,3**), sayfa basi
   **61.625 → 26.252 bayt**, **kaybolan URL 0** (iki yonde 22.511=22.511).
   🔴 `enjeksiyon-kapisi.py` **2b ekseni DISSIZDI** — uretilen sayfada HTML yorumu ariyordu ama
   uretim yorumlari SOYUYOR → hep bos dize olcuyordu. 4 davranissal eksenle degistirildi (9→12).
   Curutme: oldurucu 5/5 KIRMIZI, kontrol 2/2 YESIL, artefakt deltasi bagimsiz hesapla birebir.
   **Yasal eksen elendi:** tasinan blok CC BY atfi DEGIL; CC BY atfi ayri ve **statik HTML**.
2. **Nobet ayrimi `ffc72a6a`** — 6 bloklamayan job `deploy.yml`'den `nobet.yml`'e.
   `deploy: needs` **4..4** · bloklayici adim **132..132** · tasinan **6/6** · **KAYBOLAN 0**.
   🟢 **CONCURRENCY KILIDI COZULDU:** `pages` grubunda kalan 6/6 job yayin zincirinde.
3. **Denetim kapisi `3b369e34`** — `--evet-sil N` onayi (tavan 50). Onaysiz toplu silme
   **rc=4 / silinen 0 / sha256 DEGISMEDI**; kendini-test 50 iddia. (760 kayitlik silme kaleminin kapisi.)
4. **Kanca koku `3aec9eba`** — worktree'de kanca icinden `GIT_DIR` **mutlak** geldigi icin kok
   `<wt>/tools` cikiyor → rc=2 → **commit BLOK** → isciyi kanca atlamaya itiyordu. Kok artik
   `-C` kesfinden turuyor. Kapali-kalma curutmesinin dokumu ARSIVDE; yuzey **214.553..214.553**.
5. **Ata-lisans kapisi `c3c23d2e`** — turev kaydin atasi kendi verisinde gorunmuyor; ata ancak
   baglantinin **HOST**'undan platform+id cikarilip o platformun API'sine gidilerek cozuluyor.
   Ilk surumde **12 sessiz gecis** vardi (en agiri: turev detayi 404 → "ata yok" → temiz sayiliyordu);
   **12..0**, yanlis-pozitif **0/31**, yanlis-negatif **0/22**, iddia 28→54, oldurucu 20/20.
   🔴 Batarya kendi korlugunu de tasiyordu: ayni uzunluktaki mutasyon ayni saniyede yazilinca
   bytecode onbellegi yuzunden UYGULANMIYOR; mutant kirmizi yaniyor ama dusen **bir oncekinin**
   iddiasi. Onarildi ve bagimsiz yeniden uretildi. → hafiza `[[mutasyon-bytecode-onbellegi]]`
6. **`serit-a3` + is-akisi kapisi `336a16bc`** — mutant tek bir **sabit kodlanmis kurban** uzerinden
   olcuyordu, serit ayrimi o kapinin kolunu tasiyinca fikstur curudu. Altinda gercek delik: bloklayici
   adim silinince tum kapilar rc=0 kaliyordu, `SERIT_B` bunu "bloklayicidir" diye **beyan ediyor ama
   olcmuyordu**. Kurban artik **kanonik** seciliyor.
7. **`serit-a4` ayirt edicilik `07f4bb44`+`1141be85`** — iki mutant dusen iddialarin **KIMLIGINDE**
   ayrismiyordu; M14'un ekledigi vaka zaten kirmizi listenin icinde gizleniyordu. Kolay yol
   (mutant birlestirme) SECILMEDI; gercekten ayri olan davranis icin yeni provenans ekseni eklendi.
   `ayirt-edilemeyen` **1..0**, mutant sayisi **DUSMEDI**.
8. **6 kayit `marka` duzeltmesi `67820319`** — ⚠️ **OKAN'IN ACIK IZNIYLE, TEK SEFERLIK duzlem
   sinir asimi** (urun verisi normalde baska mimarin). `uyum-kapisi` **rc 1→0**
   (`gecen 42 · kalan 0 · iddia 42 · taban 42` — susturma yok), katalog **21376..21376**
   (silme 0), **arama kaybi 0** (dusen 6 jetonun 6/6'si kendi kaydinin basliginda duruyor),
   D1 dort eksen yesil. Kapinin "6 mi 7 mi" celiskisi sahteydi: 7. kayit kapinin kendi
   POZITIF-KONTROL sentetigi.
9. **Defter budama `33e0a27e`+`7eed7d68`** — kayipsiz arsivleme, sinif kapisi 0 ihlal.

**TEMIZLIK:** mukerrer bir CI dali **merge EDILMEDEN silindi** — icerigi main'de VE **gerileme
tasiyordu** (hesap kimligini `secrets.` yerine duz metne ceviriyordu). `git worktree list`
oturum boyunca **6 → 2**; kalanlar baska oturumlarin, DOKUNULMADI.

**KOSUYOR:** yayin nobeti 13. vardiya — kosum **`31154170116`** (headSha `67820319`) izleniyor.
Kabul: `deploy` **JOB**'u success + canli urun sayisi = hedef + yeni urun sayfasi 200.

**BEKLEYEN:**
1. ✅ **YAYIN ACILDI — 19 SAATLIK TIKANIKLIK KAPANDI.** Kosum `31155302659` (HEAD `655ae5e2`)
   JOB birimiyle TAMAMI yesil: `build` · **`serit-a2` (6 kayitlik duzeltme TUTTU)** · `serit-a3` ·
   `serit-a4` · **`deploy` success** · `yayin` success. Canli katalog **20.849 → 21.376** = yerel
   → **acik 527 KAPANDI** (iki bagimsiz olcumde de 21.376).
   `serit-a4` suresi olculdu: basladi 07:24:10Z, **~50 dk** (madde 5 hala gecerli).
   ✅ **"404 anomalisi" COZULDU — kusur OLCUMDEYDI, sitede degil.** Kanonik adres `/urun/<id>/`;
   yoklanan `/urun/<id>.html` biçimi HIC VAR OLMADI (build.py turetme yapmaz, `id` + `index.html`).
   Dogru bicimle: katmanli ornek **60/60 → 200**, sitemap `<loc>` **21.376 = kayit**, artefakt
   **40,7 MB = 1 GB tavaninin %3,8'i** (tavan endisesi de elendi), CDN elendi (bayt-birebir ayni sha256).
   ETKILENEN KAYIT **0**. → hafiza [[kanonik-adres-olcum-yanlisi]]
   🔴 **YAN BULGU (yeni kalem, BENDE):** `tools/yayin-kapisi.py` yalnizca D1'de `yayinda=0` olan
   TASLAK satirlarin adresine HTTP atar; **taslak yoksa hicbir sayfa olcmeden success verir**.
   Yani `yayin` job'unun yesili "katalog yayinda" demek DEGILDIR — [[beyan-edilmis-survivor]] sinifi.
   🔓 main donu KALKTI (deploy hukmu dustu); bekleyen dallar merge kapisindan gecirilebilir.
2. **`uyum-kapisi.py` kirpma korlugu — TEK DOSYADA IKI YAZAR.** Kapi ihlalleri 5'te kesiyor ama
   kestigini/toplami BASMIYOR (`sema ihlali 6` sayarken 5 basti; bu gece bir onarim eksik
   yapilacakti). Kardes oturumun onarimi ana agacta commit'siz duruyor ve **raporlama tasarimi
   daha iyi** — ustune YAZILMADI. Benim dalimdan (`muh/a4-uyum-kesme`, origin'de) alinacak tek
   sey **mutasyon kanit katmani**. Karar: kardes surum taban, kanit katmani asilanir.
3. **Ata-lisans — 5 GIZIL delik + veto genisligi.** Derin ic-ice zarf · ayni duzeyde iki zarf
   anahtari · alan adi buyuk/kucuk harf varyanti → hala `ALAN-YOK` (rc=0). Bugunku tek taranan
   platformda **erisilemez**, ama bir platform olculmeden acilirsa dogar. Ayrica veto ekseni
   genis: 6 sentetik mesru lisansin 4'unu yiyor (yon fail-closed). Cip kostu, **sonucu olculmedi**.
4. **`uyum` semasina varyant alani** (sasi/varyant kodu) — 8. maddedeki duzeltme jetonu DUSURDU;
   dogru uzun vadeli cozum turetmenin onu URETMESI. Sema + kapi + D1 kolonu isi, BENDE.
5. **`serit-a4` bataryasi 42-50 dk** — yayin seridini uzatiyor ve `pages` grubunu tutuyor. BENDE.
6. ✅ **`r2_anahtar.py` onek onarimi MAIN'E GIRDI — merge `e3880c89`, deploy `31162365695` success**
   (birebir headSha kaniti), canli **21376**, ornek urun sayfasi **200**, D1 dort eksen yesil
   (21376==21376, indeks 3/3, turetilmis 5 kolon guncel, icerik hash uyusmaz 0).
   🔴 **Push ILK denemede kirmizi durdu — nobetci ARA COMMIT `46325df0`'in DIFF'inde sinif
   bulgusu olctu** (nihai agac temizdi; dokum ARSIVDE). Cozum, kapinin etrafindan dolasmak
   DEGIL: dal taze main uzerinde tek commit'e sikistirildi (agac bayt bayt ayni), push temiz gecti.
   ➡️ **Ders: nihai agac temiz olmasi YETMEZ, ARA COMMIT'IN DIFF'i de public.**
   🟢 **PARITE hukmu duzeltildi:** guncel main ana checkout'ta `parite-test.js` **1199/1199** ve
   `parite-ege.js` **848/848**, **rc=0**. Onceki "rc=3 / OLCULEMEDI" olcumu **dal worktree'sinden**
   geliyordu — arac bayat tabanda fail-closed davraniyor. → hafiza [[parite-testi-olculemedi-basiyor]]
   Yeni kapi yayin seridine GIRMEDI: ayri `r2-onek-nobeti` job'u, `deploy: needs`'te YOK,
   `continue-on-error` da YOK (zorunlu `SERIT_B` beyani ile). `deploy.yml`'e dokunulmadi.
   ⚠️ Kapinin **E3/E4 ekseni CI'da OLCULEMEDI** verir — ikiz tanim kaynagi kardes depoda, runner'da
   yok; sessiz atlama yerine gorunur kirmizi secildi, o eksenin yesili yalniz yerelde anlamli.
   ⏭ Kalan: **CGTrader tek gelenek (tiresiz) uygulamasi** + `x` onekli 1 kaydin anahtari (MaCiT).
   📌 Yol boyunca olculen (kayit): ilk surum SARTLI dondu, bagimsiz curutucu **uc kabul iddiasini
   da kirdi** — `DEGISEN_ANAHTAR=0` yanlis birimdeydi (**75 farkli + 988 coken**; yayina etki 0
   cunku hicbir arac mevcut anahtarlari yeniden yazmiyor) ve "6/6 oldurucu" sisikti (dusmanca
   8 mutantin **5'i sag kaldi**). Onarimdan sonra kabul: iddia 14/14 · oldurucu 18/18 ·
   kontrol 4/4 · ayrisan-olmayan 0. **Ders: isçinin kabul sayisi curutulmeden alinmaz.**
7. `pages` grubundaki **6/6 job'da `timeout-minutes` YOK** (varsayilan 360 dk) — ikincil
   sertlestirme; workflow degisikligi Okan kapisi.
8. HocA → ADIM 2 (`?model=` uyelik yuklemi). MaCiT → iki worktree merge karari + 2 kayit geri cekme.

9. 🔴 **GIZLILIK TARAMASI (yeni, dalda hazir: `worktree-agent-adbd962096b205e05` / `b3f3e3da`).**
   PUBLIC repoda **2 bulgu** olculdu: **1'i onarildi** (kod tarafi, bu dalda); **1'i dokunulmadi**
   — MaCiT'in duzlemi, posta kutusuna yazildi. Hangi dosya/kayit ve bulgu turu ARSIVDE.
   **Nobetci kor noktasi olculdu ve kapatildi:** `kisisel-veri-test.py` kanonik desen kaynagini
   YALNIZ commit-mesaji ekseninde okuyordu; **533 izlenen dosyanin icerigi** onunla kesisimi BOS olan
   3 elle yazilmis literalle taraniyordu. Iddia **5** · oldurucu **7/7** · kontrol **2/2** ·
   ayrisan-olmayan **0**. → hafiza [[nobetci-kanonik-kaynagi-tek-eksende]]
   ⚠️ **KALAN SINIR:** ad (ozet) ekseni dosya icerigine baglanamadi — PBKDF2 tam tarama
   **3.996.480 aday / 188 sn**. O eksen dosya iceriginde **OLCULEMEDI**, yesil DEGIL.
   Merge sirasi: r2 dali once, bu dal sonra (ikisi de `tools/` altina dokunuyor).
10. ⏸ **GIT GECMISI — OKAN HUKMU VERILDI: DOKUNULMAYACAK.** 2610 commit tarandi, **6 commit
   mesajinda** sinif bulgusu var (dokum ARSIVDE). Okan'in karari (7 Agu): **simdilik
   temizlenmeyecek, kayit altina alindi.**
   Gerekce: sizan sinif ad/alan-adi; **anahtar/sifre DEGIL** → yenilenecek sir yok, ve temizlik
   force-push demek (tum klonlar/dallar/CI SHA bagi kirilir). Bundan SONRAKI commit'leri nobetci
   bloklar. Karar acik, yeniden acilabilir.
11. **Homonim markada ikinci kapi (ortak arac, BENDE).** Kardes olcum: `genesis` literalini gecen
   9 kaydin **6'si (%67)** arac-disiydi (konsol/oyun/plaket/anime). Kanonik `hasat_tara.py`
   marka-literal kapisindan sonra **arac-baglam kapisi YOK**; yuksek-homonimli markalarda
   (Genesis · muhtemelen Lincoln/Cupra/Polestar/Smart/Ram/Jaguar) yanlis urun canliya gidebilir.
   O hucrede elle konuldu, kalicilastirma bende.

**OKAN'DA KARAR (1):** kardes mimarin sordugu **satin-alma fiyatlandirmasi** — ucretli ama ticari
yeniden-satis hakki veren 109 kayitlik kuyruk icin maliyet fiyata nasil yansiyacak
(sabit marj mi, maliyet+X TL mi)? Yanit gelmeden o kuyruk islenmez.

## Onceki turlarin dokumu (saatlik CI nobetleri, A20 capasi, kok turetimi, diriltme kapisi,
## backfill gorsel-gate) — ARSIVDE (DEVAM-ARSIV.md, git disi).
