# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 15 Agu (~16:xxZ) — YAYIN ZINCIRI IKI KATMANA AYRILDI (Okan emri, KraL)

**BLOK RITMI: 1 eklendi / 2 arsive tasindi** (arsiv 1.659.688->1.664.490 B, 69=69 lossless).

**OKAN'IN EMRI:** *"gelen mail bir hata yuzunden geliyor, bu gelen hata tum mimarlari
tikiyor, burayi cozmemiz cok onemli."* Mail SEMPTOMDU; ariza yayin hattinin kapanmasiydi.

**OLCUM (11-15 Agu, 200 kosum):** 68 success · 85 failure · 47 cancelled ·
**TOPLAM YAYIN KESINTISI 54,08 saat** (en uzun tek kesinti 8,38 s). 136 kirmizi adimin
ilk BESI toplamin yalnizca %35'i — ariza KRONIK DEGIL **DAGINIK**: her gun BASKA kapi
yakiyor. Sebep yapisal: `deploy.needs`teki dort iste **171 adim**, `continue-on-error`
yalniz 2'sinde → 169 adimin HERHANGI BIRI kirmizi yaninca BES EVIN push'u inemiyor.

**HUKUM + SONUC (`1b482873`, `beed3486`, `bdd3564f`, `eda23fe7` — hepsi push'lu):**
Turnusol: "bu kapi kirmiziyken commit canliya inerse musteri yanlis para oder mi · gizli
veri sizar mi · yasak urun satilir mi · site/odeme calismaz mi?" → 171 adim **63 BLOKLAYICI
/ 108 HIJYEN**. Hijyen adimlari `hijyen-*` islerine TASINDI (`continue-on-error` KULLANILMADI
— o, kosumu `success` yapip mail kanalini oldururdu). **KANIT (kosum `eda23fe7`):
hijyen-a2=failure · hijyen-a3=failure · deploy=SUCCESS · yayin=SUCCESS · canli 27.949 =
yerel 27.949.** Yayin, hijyen kirmiziyken AKTI.

**NOBET (ayni emrin ikinci yarisi):** kapi oncesi 167 tur/0 onarim · sonrasi 55 tur/2
onarim/50 `ONARIMSIZ_TUR`. Iki kural degisti: CI kirmizisinda "tek-yazarli alan" bahanesi
YOK · **onarimsiz supurme YASAK**. Kapiya `ONARIMSIZ_SUPURME`, 3 turda `ESKALASYON=OKAN`,
duruma bagli **sure tavani** (onarim ilerliyorsa 50 dk, degilse 25) ve `ATLANAN_ARDISIK`
sayaci eklendi. Kabul: `nobet-kabul-test.py` **VAKA=34 DUSEN=0**, 5 mutant KIRMIZI.
Sahada dogrulandi: nobet bugun `0dc9ff67` (altkategori B3) ve `15fc2a53` (FAZ3/Vespa)
kirmizilarini KENDI onardi.

🔴 **K80'IN UC KUSURU (hepsi bu turda olculdu ve onarildi, `eda23fe7`):** (1) TASINAN adimi
"yeni" sayiyordu — komut kumesi 158->158, GERCEKTEN_YENI=0 iken 101 adimi kosturup push'u
durdurdu → **tasima muafiyeti** (`TASINDI=101` raporlanir, bloklamaz); (2) `.mjs` ve
`shop/`,`jenerator/` koklerini TANIMIYOR, "olcemedigini yasakliyordu" → kok/uzanti kumesi
KAPALI bicimde genisletildi; (3) **IKIZ TANIM**: kosturucu kendi uzanti listesini tutuyordu,
`.mjs` adim ayristiriciyi gecip `IndexError` ile push'u dusurdu → tek kaynak
(`_k80_uzantilar`/`_k80_betik_yolu`). Ayrica zincir DISI ise eklenen adimdan artik yesil
sarti ARANMAZ. Batarya 5 -> **12 iddia**, T1-T7 + 5 oldurucu mutant.

**FIYAT KAPISI KARMAYDI, EKSEN AYRILDI (`bdd3564f`):** kirmizinin sebebi para DEGILDI
(fiyat uyusmazligi **0**), testin kendi mutasyon bataryasindaki `M3b` deligiydi ve TABANDA
da vardi. `--yalniz-parite` BLOKLAYICI (rc=0), `--yalniz-mutasyon` HIJYEN (rc=1, delik
GORUNUR). Batarya SILINMEDI, esik DEGISMEDI, bayraksiz cagri birebir ayni kaldi.

🔧 **ACIK (kanitli, bayat DEGIL):** (a) 2 hijyen isi hala kirmizi — tabandan gelir, nobetin
onarim kuyrugunda; (b) `M3b` cagri-silme mutanti yakalanmiyor; (c) motor basina sure tavani
YOK — 72 saatte 6 tur zaman asimindan yandi (%5,5), 12:37 turu 61 dk surdu; (d) **kendi
siniflandirma hatam**: `Kanca kablolama nobeti` hijyene alinmisti, peer oturum serit-a3'e
GERI tasiyor (adimin kendi yorumu "BLOKLAYICI olmali" diyor) — dogru duzeltme, dokunulmadi;
(e) karma kapilar (`Devam sinif kapisi`, `Alt kategori kapisi`) guvenli tarafta BLOKLAYICI
birakildi, eksen ayrimi bekliyor.

## ACIK KALEMLER (kaynak-dogrusu: `acik-kalemler.md`)

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

## VERI OLAYI (kapandi, kalici kayip var)

Gizli kaynak kaydi bir boru kazasiyla 0 bayta dustu; yedekten ATOMIK geri yuklendi (10.060.282 bayt, sha256 birebir, 27.817 kayit). **261 urunun kaynak kaydi KAYIP**; 65'i katalogda lisans tasiyor (site atfi SAGLAM), kalan ~196'si ticari kayit sinifi. Dort kurtarma yolu olculdu, DORDU DE kapali. Dolgu MaCiT'te; sirasi once ticari sinif. (Okan teyidi: SINIF B'deki 196 kaydin cogu FIZIKI urun, dijital dosya/lisansi zaten yoktu — "asil ticari bosluk" cercevesi ABARTILIYDI.)

## OKAN'DA

- Motor tarifesi satin alma karari · eski yedek klasorunu backup-v2 icine tasima · K89 olcum eylemi silme karari.
- 🔧 **TARIFE KARAR KURALI (olculdu, onaya hazir):** mevcut $20 plan KALIR. Haftalik kota %80'e yaklasirsa ikinci saglayicinin $39 basamagi TERCIH EDILIR — ayni para bandinda hem kota hem **ikinci saglayici** (429/kesinti/kota duvarinda yedek) verir; mevcut saglayicinin $50 basamagi yalniz kota verir, tek-saglayici riski surer. Ikinci saglayici bekleme listesindeyse tek uygulanabilir yol $50 (0 kod degisikligi). Ust basamagin iki "deneysel" ozelligi bizim hatta GIRMEZ — biz yalnizca Anthropic-uyumlu API ucundan MODEL cagiriyoruz. Kota sayilari iki adayda da yayimlanmiyor, yani secimi fiyat degil CESITLILIK belirliyor. Ekleme bedeli motor basina 6 kod noktasi.
- Olculen maliyet tabani: $18,72 / 1.081.021.287 token / 8.639 istek = yaklasik $17,3/milyar; $20/ay ve yaklasik 4,6 milyar/ay = yaklasik $4,3/milyar.

## KOSUYOR (baska mimarlar)

MaCiT — Ducati d1 sub-slice 2/3 ve 3/3 (taban artik 27420) + 261 kaynak kaydi dolgusu.

## MOTOR A/B (ayni spec, ayni kabul, iki kol)

Sure 1.221 sn vs 1.997 sn · zorunlu rapor VAR vs YOK (ikincisi rc=1 ile dustu) · mukerrer deger 14 vs 0 · istisna ihlali 0 vs 0. Hukum: biri hizli ve disiplinli, digeri veri hijyeninde temiz; **kabul satiri vermeyen kol kapatilamaz.**

## ARSIVDE (tam metinler `DEVAM-ARSIV.md`'de)

14-15 Agu saatlik CI nobeti turlari · 15 Agu gece oturum kapanisi · K101/K103 kapanislari · yayin ve odeme etiketi bloklari · dorduncu motorun hatta baglanmasi · HD/Kawasaki/Ducati ekleme bloklari · sabah oturumunun tam olcum blogu · defterin sikistirma oncesi 196 satirlik tam hali.
