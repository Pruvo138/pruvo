# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 15 Agu (~09:5xZ) — YAYIN ACILDI (KraL)

**`280eee20` — 7,5 saatlik yayin tikanikligi kaldirildi.** `serit-a2` (`eski-fiyat-test.py`)
07:22Z'den beri her itmede kirmiziydi, `deploy` isi `needs` zinciriyle SKIPPED kaliyordu; son
basarili yayin 02:04Z (`a4622a7b`) idi — canli site sabahki her seyin (167 Ducati, 274 ABS
tavsiyesi, 4 silinen yasak urun) gerisindeydi.
Kok neden olculdu: PETG'den ABS'e gecen politika ayni fikstur urunun ilan tutarini 110.500'den
**136.000 kurusa** cikardi; testin sabit `1.200 TL` (120.000) fiksturu ilanin ALTINDA kaldi ve
`eski_fiyat_html` onu **DOGRU** davranarak basmayi birakti. Kural degil FIKSTUR bayatti.
**Hukum: kural gevsetilmedi, `build.py`'ye dokunulmadi**; kabul degeri artik kanonik
`ilan_kurus`tan turer. Kabul: rc=0 / 0 ihlal · mutasyon 11/13 KIRMIZI = **taban 11/13 ile
birebir** (M2/M3 tabanda da OLCULEMEDI) · degisen dosya 1 · D1 27420, bes eksen yesil.

## 15 Agu (oglen) — OTURUM KAPANISI (KraL)

**CANLIYA GIDEN (main'de, push'lu — HEAD `7cd7405d`):**
- `fec2daf9` — defter sinif kapisi acildi: 177 satirlik nobet gunlugu arsive TASINDI (lossless), kapi 0 ihlal. 7,5 saattir HICBIR commit inemiyordu.
- `f977963b` — **shop DAGITILDI** (Okan acik onayi): canli `34d4db64` yerine `01d41b07`; bayatlik kapisi **TAZE rc=0**, 27 turdur yanan alarm kapandi.
- `4a97fda5` + `7f5d45b6` + `6fa022b1` — **yedek zinciri 3 katmanda onarildi** (dogru esik → dogru granulerlik → kasit beyani). Kabul 7/7 davranis + 8/8 mutant. Canli: rc=0 · BEYANLI=2 · KARANTINA=0 · YARIM_KALMIS=YOK.
- `53f090e7` — **PARCA 2**: 274 urunde birincil tavsiye PETG yerine ABS (PETG-ilk 274 sonra 0 · ABS-ilk 13 sonra 287 · ezmeli 433 sabit). Ayni commit'e MaCiT'in Ducati partisi (167) karisti — paylasilan agac; olculdu, mesaja yazildi, kutuya bildirildi.
- `9e18833e` — mimar karari: 4 yasak-tur urun silindi (1 maket · 2 logo/plaket · 1 surec adi). MaCiT'in rozet/plaket icin "KEEP" secenegi REDDEDILDI.
- `85886380` — defter K27 hedefine indirildi: 196 satir / 24.462 B yerine **42 satir / 4.754 B**; tam hal arsivde, prefix karsilastirmasiyla dogrulandi.
- `7aa406c1` — nobetin defter sismesi **H8 ekseniyle** kapatildi (cron tarafi: `nobet-kapi.py` + gorev metni, git DISI, yedege alindi).

**KAPANIS KAPISI BIR SEY YAKALADI (cozuldu):** `d1-sync.py --durum` kapanista **FAZLA=4** verdi — mimar kararıyla silinen 4 yasak urun D1'de duruyordu, yani **Ege onlari hala goruyordu** (silme iki fazli: karantina + ikinci gozlemde farkli SHA). `d1-sync.py` kosuldu: silinen 4, geri-okuma DOGRULANDI. Son hal: **D1 27420 = urunler.json 27420 · FAZLA=0 · EKSIK=0 · hash UYUSMAZ=0**, bes eksen yesil.

**KOSUYOR:** kendi delege ettigim is YOK — tum Codex isleri sonuclandi, kabul testleri kosuldu, dallar merge edildi, uc onarim worktree'si silindi (`git worktree list` = yalniz ana agac). Ana agac TEMIZ, main push'lu, uzak ile ayni.

**BEKLIYOR (bende, bloke degil):** K104 hukmu (teshis Codex'te) · K104B (2 kapi tabanda kirmizi) · K99 · K100 · K102 · bu turda acilan 2 kapi kalemi (shop bayatlik alarminin tetik ekseni · defter sinif kapisi muafiyet ayrismasi).

**BEKLIYOR (baskasinda):** MaCiT — Ducati sub-slice 2/3 ve 3/3 (taban 27420) + 261 kaynak kaydi dolgusu; ayrica bir sonraki nobet turunda `DEFTER_BUYUMESI=` 3'un altina inmeli (ilk olcum 9 cikti, sozlesme kutuda).

## ACIK KALEMLER (kaynak-dogrusu: `acik-kalemler.md`)

- 🔴 **K104** — nobet is akisi 200 kosumda 11 success / 77 failure / 110 cancelled; son yesil 12 Agu 11:17Z. Teshis Codex'te, HUKUM MIMARDA.
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
