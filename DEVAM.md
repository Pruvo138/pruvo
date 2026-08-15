# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 15 Agu (~12:1xZ) — K19 KAPANDI + NOBETIN ONARIM ZORUNLULUGU KURULDU (KraL)

**BLOK RITMI: 1 eklendi / 2 arsive tasindi** (arsiv 1.654.486->1.659.688 B, 54=54 lossless).

**`b9e5c507` — K19 capraz-marka yargisi kapandi, yayin acildi.** Hukum: `Adventure` KTM'nin
KENDI model ailesi adi -> `KTM|adventure` ROZET; BMW'de aile rozeti GS, `Adventure` onun
VARYANT eki -> `("BMW","Adventure")` ROZET_DISI, urunler `/marka/bmw/gs/`de durur (emsal
Fiat|scudo / Peugeot|Scudo). Olcum: YARGISIZ=0 BAYAT=0 CELISKI=0 · allow 56->57 ·
deny 38->39 (iki imza tazelendi) · dort kapi rc=0 · parite-ege 893/893 · D1 27646 bes eksen
yesil. Ayni commit'te macit ankor dusus beyani AILE olarak yeniden yazildi (ilk yazim
dosyadan dusmustu; nobetci isi DEGIL, kayip HALA aciklanmadi).

🔴 **NOBETIN ONARIM BACAGI — OLCULDU VE ZORUNLU KILINDI (Okan emri).** ONCE 167 tur / 0
onarim / 16 tasima · SONRA (14 Agu 11:00'den) **55 tur (hepsi KOSTU), 2 onarim, 17 tasima,
50 tur `ONARIMSIZ_TUR` ile dustu** — tur kosuyor, mail temizliyor, onarmiyor; kapi 50 kez
ayni hukmu basmis, kimse gormemis. Iki degisiklik (`~/.claude/cron/`, git disi):
(1) **CI kirmizisi yetki istisnasi** — CI'i kirmizi birakan arizada "tek-yazarli alan"
ayrimi UYGULANMAZ, nobet kendi onarir+push eder (yasak listesi aynen durur);
(2) **onarimsiz supurme YASAK** — mail ancak sinifi olculerek kapaninca Cop'e gider.
Kapiya `HUKUM=ONARIMSIZ_SUPURME` + ard arda 3 onarimsiz turda `ESKALASYON=OKAN` sayaci
eklendi. Kabul: **VAKA=30 DUSEN=0** (27+3, 2 mutant KIRMIZI).

🔧 **YENI KALEM — K110 CIPLAK SAYI PARITE SAPMASI:** `parite-test.js` q="1290"da `/ara`=1
yerel=0 (test `arama.py`yi HIC okumaz — K19'dan DEGIL). `1290` KTM partisiyle MODEL evrenine
girdi; yerel plan sorguyu marka/model koluna alip haystack'i kullanmiyor, uc ise D1 `hs`
kolonunda ALT-DIZE eslesip `9641290J00` parca numarasini yakaliyor. Supurme: **65 ciplak
sayi jetonunda gercek yanlis-pozitif TEK**, kalani senkron gecikmesi. Hukum MIMARDA;
uc `pruvo-bot` evinde, HocA'ya dusecek.

🔧 **K111 BAGLAM REGRESYONU (kok neden ACIK):** oturum ACILIS maliyeti pruvo evinde **14 Agu
11:10'da 43,5K'dan 73,5K'ya sicradi**, geri inmedi (17 oturum 68,6-71,6K). Iki eksende
birden: `cache_read` +14,9K (arac envanteri) · `cache_creation` +15,0K (ev metinleri).
O saatte degisen ayar BULUNAMADI ama olcum yalniz son 12 saate bakti — yeniden olculecek.

## 15 Agu (~11:0xZ) — OTURUM KAPANISI (KraL)

**CANLIYA GIDEN (main'de, push'lu):** `280eee20` yayin acildi (eski fiyat fiksturu kanonik
`ilan_kurus`tan turer) · `3d2adabf` K108 curutuldu · `81a2a32a` konsolidasyon defteri ·
`96aa9d75` indeks hukmu. Dogrulama: `280eee20` kosumu **completed success**, alti isin ALTISI
yesil (`deploy` + `yayin` SKIPPED DEGIL KOSTU); canli `urunler.json` 27420 = o commit'in
katalogu; sabah silinen yasak urun `th3812744-...` canlida **HTTP 404**.

**KOSUYOR:** kendi delege ettigim is YOK — bu turdaki tum Codex isleri (kok neden olcumu ·
fikstur onarimi · taban mutasyon olcumu · canli dogrulama · defter konsolidasyonu · indeks
turetme · uc yedek kosumu) SONUCLANDI, kabul satirlari alindi. Acilan tek worktree
(`kral/eski-fiyat-fikstur`) merge sonrasi SILINDI; `git worktree list` = yalniz ana agac.
Arka plan gorevi kalmadi.

🔴 **YAYIN YINE BLOKLU — AMA FARKLI SINIF (bu tur acildi, BENDE):** `81a2a32a` ve `db3de830`
kosumlari `serit-a2` "Marka->model pilot kabul testi" + `serit-a3` "Model uyeligi kapisi"
adimlarinda KIRMIZI: **K19 CAPRAZ-MARKA CIFTI YARGISIZ — `BMW|adventure` ve `KTM|adventure`**
(87 cift/40 model icinde 2 yargisiz cift; 1/29 iddia KALDI). Sebep K106 DEGIL: MaCiT'in KTM partisi
`adventure` model jetonunu getirdi, ayni jeton BMW'de de esliyor. Bu K95'in AYNI SINIFI
(Fiat|scudo · Nissan|primastar emsali) ve hukum MIMARDA: iki cift ya yargi tablosuna ya BEKLER
listesine yazilacak. **Sonraki oturumun ILK isi budur.**

**BEKLIYOR (baskasinda):** MaCiT — `ff88e3ec` (KTM SLICE 2, +106, katalog 27646) main'de ama
**PUSH EDILMEMIS**; baskasinin commit'i oldugu icin ELLENMEDI. MaCiT kendi kapilarini kosup
itecek; yukaridaki K19 kirmizisi cozulmeden o itme de yayina inmez.

🔴 **REGRESYON NOTU (bu turda olculdu, sonra GERI GITTI):** `.yedek-dusus-izin.json` icine
`posta-kutusu-macit-izleme-ankor.txt` icin yazdigim `surekli`/4096 beyani dosyadan DUSMUS
(su an yalniz `DEVAM.md` + kaan ankoru var). Beyan yokken `yedekle.py` **rc=1** dusuyor
(618 -> 188 B karantinasi). Beyan AILE olarak yeniden yazilmali — ikizi beyanli, kardesi degil.

**OKAN'DA:** motor tarifesi karari · eski yedek klasorunu backup-v2'ye tasima · K89 olcum
eylemi silme karari · (yeni) indeksi gercekten kucultmek icin ikinci kademe indeks karari —
hangi girisler oturum basinda HER SEFERINDE gerekli degil, kategori kategori onaya sunulacak.

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
