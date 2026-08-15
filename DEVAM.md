# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 16 Agu (~00:xxZ) — UCUZ KAT YENIDEN KURULDU: CODEX + DEEPSEEK EMEKLI, KIMI BIRINCIL (KraL)

**Okan karari, olcumle kapatildi.** Yeni hat: `isci.sh` → **kimi BIRINCIL · minimax-m3 YEDEK**;
DS ve Codex'e yeni is YOLLANMAZ (abonelik iptali Okan kapisi).

**Kanit — `tools/yetkinlik/` bataryasi** (6 sinif, hukum deterministik dogrulayicida; commit
`54e9f4c7`). Iki kosum (1 tekrar + 3 tekrar), cevap verilen turda dogruluk:
**kimi 18/18 · m3 21/22 · codex 14/15 (+1 yalan)**.
- kimi'nin ham skorunu dusuren 6 tur **yetenek degil uc hatasi**: `motor_rc=1`, 2,3-4,3 sn,
  ardisik alti tur; yeniden kosumda ayni tur **6/6**. → `isci.sh`'e **kisa-surede-rc≠0 →
  1 kez otomatik tekrar** korumasi kondu.
- **m3'un olculmus zafiyeti: uzun baglam / cagri grafi** (g5'te UYDURMA satir verdi). O sinif
  kimi'ye ya da capraz dogrulamaya.
- Batarya **kendisi 3 kez yanildi** (`ONERI=` satiri kabul satirini golgeledi · yol oneki ·
  kirilim sirasi) — ucunde de once "motor kaldi" gorundu. Olcer `mutasyon.py` ile kanitlanir
  (12 mutasyon, SURVIVOR=0; `dogrula-test.py` 21 vaka).

**Tarayici tekeli kirildi.** Isci playwright ile **giris yapilmis panele giriyor**
(`PANEL=ACIK`, Cloudflare). Iki mod: etiket `tarayici*` → HEADLESS (pencere yok, izole),
`panel*` → HEADFUL + kalici profil. macOS ekran-disi konumu EZIYOR (pencere `(0,31)`'e
cekiliyor), headless ise panelde bot dogrulamasina takiliyor → panel turunda pencere
kacinilmaz, o yuzden **panel isi ONCE API**: yeni `tools/cf-durum.py` (salt okuma)
D1/R2/Pages'i tarayicisiz veriyor.

**ACIK KALEM (Okan):** cf-durum DNS kapsami icin salt-okuma CF jetonu lazim — ayrinti
DEVAM-ARSIV.md'de (git disi).

## ACIK KALEMLER (kaynak-dogrusu: `acik-kalemler.md`)

- 🔴 **K113 (YENI, 16 Agu)** — `Uretici butunluk kapisi` YANLIS SERITTE: `hijyen-build`'de, oysa URL-guvensiz ID kanonik adresi bozar = BLOKLAYICI olmali. Bugun tam bu yuzden bozuk ID'yi yakaladi ama yayini durdurmadi. `deploy.yml`'e yazmayi gerektirir; **peer'in commit'siz isi bekleniyor**.
- 🔴 **K114 (YENI, 16 Agu)** — `onarim/r2-purge` dali (`9f7aaf77`, worktree `/private/tmp/pruvo-purge`) MERGE BEKLIYOR: tek engel `ci-kapsam-test.py` rc=1 (`tools/r2-purge-test.py` CI kapsaminda degil). K113 ile AYNI dosyaya yazilacak, ayni turda kapanmali.
- 🟠 **K115 (YENI, 16 Agu) — IC LINK TESHISI OLCULDU (Okan'in 2. konusu, uygulama BASLAMADI).** Ham HTML'de ic link hatti KOPUK: ana sayfa **0** urun linki (kartlar JS ile basiliyor) · urun sayfasi yalnizca **8** rel-card (ayni kategori, `build.py` `[:8]`) · marka hub'i ilk sayfada ~484-616 urun gosteriyor ama toplam 2357 (gerisi `man.yuk` JS'iyle) · sitemap `/urun/` sayisi katalogla BIREBIR (fark 0) · **30 urunluk orneklemde 27'si (%90) hicbir HTML sayfadan link ALMIYOR** (katalog geneline ~25 bin). Googlebot JS kosarsa tablo degisir; hukum "yetim" degil "**yalniz JS ile ulasilabilir**". Aday cozum (ucuzdan pahaliya): marka hub'lari icin SSR sayfalama (`/marka/<x>/2/` + rel=next/prev) — her urun en az bir statik sayfadan link alir, ~50-100 ek sayfa maliyeti.
- 🟠 **K116 (YENI, 16 Agu)** — `kimi` isci motoru **KOTA DOLDU** (403 "usage limit for this billing cycle"). Bugun tarayici/panel tekelini kiran iki motordan biriydi; m3'e devredildi. Kota yenilenene kadar tarayicili is m3'te.
- 🔴 **K104** — nobet is akisi 200 kosumda 11 success / 77 failure / 110 cancelled; son yesil 12 Agu 11:17Z. Teshis Codex'te, HUKUM MIMARDA.
- ✅ **KAPANDI (15 Agu 13:5xZ, koşum 31887287227) — serit-a2 B3 + serit-a3 FAZ3 YESIL:** `Ayna ve Silecek`/`Sele ve Sehpa` çakışması `0dc9ff67` (marka_kimlikleri arama.py'de kanonik) + `15fc2a53` (faz3 TEST 7 "Vespa" yanlış-kırmızısı, K112) ile çözüldü; build+a2+a3+a4+deploy SUCCESS. **Yayın hâlâ bloklu ama YENİ sınıf:** `yayin` adımı 358 taslak > 300 tavan → `yayin-kapisi.py --geriye-doldur` = OKAN KAPISI (13:54Z log'da eskalasyon yazıldı).
- 🟠 **12:11Z nobet turu: 4 koşumda aynı kök neden (DUR eşiği 3 AŞILDI).** `81a2a32` (konsolidasyon 10:35) + `96aa9d75` (MEMORY.md 10:52) + `2c3d2064` (defter kapanisi 11:16) + `b9e5c50` (yargi K19 11:38) — dördünde de `serit-a2::altkategori-kapisi::B3` aynı çakışmayı basıyor; son başarılı deploy `31877923321` (sha 280eee2, 09:48Z); §3 DUR KOŞULU tetiklendi (YASAK = `urunler.json` teması + 3+ kopu), push etmiyorum, Okan'a tek cümle çıktı. Marka adları (`Ayna`, `Sehpa`) `urunler.json`'da VAR; 383 ürün "Ayna ve Silecek" + 59 ürün "Sele ve Sehpa" altkategori taşıyor — MaCiT paketi hazır (K109).
- **K104B** — nobet is akisinda IKI kapi main'de de KIRMIZI (mutasyon capalari M06/M31 + 2 kapinin kanca kablosu envanterde yok). Tabanda olculdu, dalin getirdigi DEGIL.
- **K99** bag kolonu spec'i · **K100** defter sinifinda satir-sonu muafiyet kusuru (sinif onarimi bende) · **K102** nobet yazicisi kok deftere yasakli ic dosya adi uretiyor.
- 🔧 **Bu turda acilan IKI kapi kalemi (ikisi de ACIK, gate kodu = Claude kati):** (a) shop bayatlik alarminin TETIK ekseni raporladigi bundle evreniyle AYNI DEGIL — 25 tur kirmizi yandi, delta 0 dosyaydi; (b) `devam-sinif-kapisi.py` is-akisi muafiyeti `norm`/`ham` ekseninde ayrisiyor (ofsetler bir eksende, arama otekinde). Uctuncu kalem (yedek karantinasi) bu turda KAPANDI, asagida.
- ✅ **K108 CURUTULDU (KraL, 10:1xZ) — koşum TAKILI DEĞİLDİ, UÇUŞTAYDI.** `31877923321` **completed success**; alti isin ALTISI da yesil (`build` · `serit-a2` · `serit-a3` · `serit-a4` · **`deploy`** · **`yayin`**) — yani `deploy` SKIPPED degil KOSTU. Canli dogrulama (kanonik adres, cache-bust YOK): `pruvo3d.com/urunler.json` **27420** = 280eee20 katalogu · sabah silinen yasak urun `th3812744-1199-siluet-rozet` **HTTP 404** (silme canliya indi). Canlinin yerelden (27540) geride gorunmesi BAYATLIK DEGIL: aradaki fark MaCiT'in 12:59'da push'ladigi `db3de830` (KTM SLICE 1, +120) ve o kosum HALA UCUSTA. **Sinif dersi:** uctaki `in_progress` bir kosumu "takildi" diye kaleme yazmak yanlis alarm uretir — hukum kosum BITINCE verilir ([[ucustaki-kosum-yesil-degildir]] tersi yonu). ESKI TESHIS: `31877923321` (280eee2) zincir koşumu 09:48Z'den beri in_progress; build 09:58'de bitti ama `serit-a2` #40 (`Marka->model pilot kabul testi (Ford + BMW)`) + `serit-a3` #96 (`Model uyeligi kapisi`) 3s+ takılı.** Kuyrukta 21b28ccd + db3de830. §4.5 üçlüsü: (a) KOŞAN zincir VAR, (b) TAVAN adım serit-a2 #40, (c) son başarılı deploy `a4622a7` 280eee2'yi atasında → **yayın BLOKLU, 7+ saat**. K106 kök nedeni (eski fiyat fikstür) çözüldü; **farklı sınıf**: K106 = fikstür bayatlığı, K108 = koşan zincirin test adımlarında GH Actions runner takılması (altyapı).
- ✅ **Yedek karantinasi KAPANDI — DUSUS BEYANI kuruldu (`6fa022b1`):** kasitli kucultme `.yedek-dusus-izin.json` icinde BIR KEZ ilan edilir, kapi beyani gorunce gecirir. Beyan BLANKET DEGIL: `tek-seferlik` yalniz ilan edilen kaynak boyutuna baglidir (dosya baska boyuta duserse ESLESMEZ), `surekli` ise zorunlu `azami_bayt` tavaniyla sinirlidir (buyuk bir veri dosyasi "rolling" ilan edilip sessizce kaybedilemez). Beyan dosyasi yoksa/bozuksa koruma TAM GUCTE. Beyanla gecen her dusus adiyla+gerekcesiyle BASILIR — beyan muafiyet degil KAYITTIR. Kabul: 7/7 davranis + 8/8 mutant (blanket beyan · tavansiz surekli · kaydetmeyen beyan ayri ayri oldurulur). **Canli: yedek rc=0 · BEYANLI=2 · KARANTINA=0 · YARIM_KALMIS=YOK** — zincir bugun ilk kez tam yesil.
- ✅ **Defter sismesi KAPATILDI (H8):** saatlik nobet artik tur gunlugunu `ci-nobeti.log`'a yaziyor; kok deftere yalniz DURUM DEGISIKLIGI tek satir duser. Zorlayan sey metin degil OLCU: `nobet-kapi.py` turun defteri kac satir buyuttugunu olcer (`DEFTER_BUYUMESI=n TAVAN=3`), asilirsa TUR duser (`HUKUM=DEFTER_SISIRME`). Kapi hicbir commit'i BLOKLAMAZ — tikanma tam da "kapi her commit'i durdurdu" seklinde yasandigi icin eksen bilerek TUR'dur. Kabul: `nobet-kabul-test.py` VAKA=27 DUSEN=0 (mevcut 24 vaka bozulmadi, 3 yeni iki-yonlu vaka + 1 mutant).
- **Bu turun uc dersi:** kapi kirmiziyken defter sessizce sisiyor (7,5 saatte 217 satir) · `denetim-kapisi` yalniz "yeni urun" kumesini yargilar, kume bosken yesil KANIT DEGILDIR · ayni sinif ikinci kez vurdugunda kol degil SINIF kapatilir.
- KAPANDI: K91 · K101 · K103 (kanitlar arsivde).

## VERI OLAYI (kapandi — tam metin arsivde)

Gizli kaynak kaydi 0 bayta dustu, yedekten atomik geri yuklendi. **261 urunun kaynak kaydi KAYIP** (65'i katalogda lisans tasiyor, site atfi SAGLAM). Dort kurtarma yolu kapali; dolgu MaCiT'te, once ticari sinif.

## OKAN'DA

- Motor tarifesi satin alma karari · eski yedek klasorunu backup-v2 icine tasima · K89 olcum eylemi silme karari.
- 🔧 **TARIFE KARAR KURALI (olculdu, onaya hazir):** mevcut $20 plan KALIR. Haftalik kota %80'e yaklasirsa ikinci saglayicinin $39 basamagi TERCIH EDILIR — ayni para bandinda hem kota hem **ikinci saglayici** (429/kesinti/kota duvarinda yedek) verir; mevcut saglayicinin $50 basamagi yalniz kota verir, tek-saglayici riski surer. Ikinci saglayici bekleme listesindeyse tek uygulanabilir yol $50 (0 kod degisikligi). Ust basamagin iki "deneysel" ozelligi bizim hatta GIRMEZ — biz yalnizca Anthropic-uyumlu API ucundan MODEL cagiriyoruz. Kota sayilari iki adayda da yayimlanmiyor, yani secimi fiyat degil CESITLILIK belirliyor. Ekleme bedeli motor basina 6 kod noktasi.
- Olculen maliyet tabani: $18,72 / 1.081.021.287 token / 8.639 istek = yaklasik $17,3/milyar; $20/ay ve yaklasik 4,6 milyar/ay = yaklasik $4,3/milyar.

## KOSUYOR (baska mimarlar)

MaCiT — Ducati d1 sub-slice 2/3 ve 3/3 (taban artik 27420) + 261 kaynak kaydi dolgusu.

## ARSIVDE (tam metinler `DEVAM-ARSIV.md`'de)

14-15 Agu saatlik CI nobeti turlari · 15 Agu gece oturum kapanisi · K101/K103 kapanislari · yayin ve odeme etiketi bloklari · dorduncu motorun hatta baglanmasi · HD/Kawasaki/Ducati ekleme bloklari · sabah oturumunun tam olcum blogu · defterin sikistirma oncesi 196 satirlik tam hali.
