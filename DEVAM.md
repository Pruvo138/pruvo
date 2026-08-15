# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 15 Agu (sabah) — bu turda canliya giden

- Shop DAGITILDI (Okan acik onayi): canli `34d4db64` yerine `01d41b07`; bayatlik kapisi TAZE rc=0. 27 turdur yanan alarm kapandi.
- PARCA 2 `53f090e7`: 274 urunde birincil tavsiye PETG yerine ABS (PETG-ilk 274 sonra 0 · ABS-ilk 13 sonra 287 · ezmeli 433 sabit). Ayni commit'e MaCiT'in Ducati partisi (167) karisti — paylasilan agac; olculdu, mesaja yazildi, kutuya bildirildi.
- Mimar karari `9e18833e`: 4 yasak-tur urun silindi (1 maket · 2 logo/plaket · 1 surec adi). Katalog **27420**, D1 geri-okuma DOGRULANDI. MaCiT'in rozet/plaket icin "KEEP" secenegi REDDEDILDI.
- Yedek zinciri iki kez KIRIKTI, ikincisinde SINIF kapatildi (`4a97fda5` sonra `7f5d45b6`): tek dosyanin reddi artik kosumu oldurmuyor — reddedilen ATLANIR (kanonik yedegi degismez), kosum surer, atlama karantina defterine yazilir + rc=1. Kabul 5/5 + mutasyon 5/5. Canli: yedek TAMAMLANDI, KARANTINA=1. Ders: [[koruma-kurali-korudugunu-durdurur]].
- Defter: sinif kapisi acildi (`fec2daf9`, 177 satir arsive), sonra defterin tam hali arsive alinip hedefe indirildi.

## 15 Agu 12:3xZ — saatlik CI nobeti turu

- **Supurme (12:07Z):** BULUNAN=5 TASINAN=5 ATLANAN=0 CIKAN=5 KOMSU_KAYIP=0 KUME_DIFF=OLCULDU KALAN=0 HUKUM=SUPURULDU rc=0. 5 mail (D1 uzlastirici x2 + Build & deploy x2 + Paket tazeligi) Cop'e tasindi; hepsi `notifications@github.com` + "Run failed" yukumune uyuyor.
- **Cop denetimi:** tum MESRU; YANLIS=0 (K77/K84 sinifi bu turda ateslenmedi).
- **gh teyit:** HEAD=`85886380`; D1 uzlastirici `31875841662` (HEAD 8588638) **failure** — `D1=27424 != urunler.json=27420` (4 karantinada Ducati kalem: `th2965898-yazici-dugmesi-teker`, `th3812744-1199-siluet-rozet`, `th4100448-1199-superbike-montajli`, `th6559546-multistradav4-plaket`; 9e18833 mimar karariyla cikarildi). K51 tasarim davranisi (karantina + ikinci gozlemde farkli SHA ile sil), workflow entegrasyonu K49/K71 kapsaminda MUHENDIS isi — hourly nöbet tek tarafli fix YAPMAZ.
- **Tamirci (🔧):** geri-iz degismedi (K49, K53, K55, K70, K77, K80, K84, K86, K96 acik; yeni yok, dagitim yok, kapanan yok).
- **Okan'a cikti:** YOK (rutin, K49 ESKALASYON, K96 MaCiT tek-yazar; MIMAR karari zaten acidan acik).

## ACIK KALEMLER (kaynak-dogrusu: `acik-kalemler.md`)

- 🔴 **K104** — nobet is akisi 200 kosumda 11 success / 77 failure / 110 cancelled; son yesil 12 Agu 11:17Z. Teshis Codex'te, HUKUM MIMARDA.
- **K104B** — nobet is akisinda IKI kapi main'de de KIRMIZI (mutasyon capalari M06/M31 + 2 kapinin kanca kablosu envanterde yok). Tabanda olculdu, dalin getirdigi DEGIL.
- **K99** bag kolonu spec'i · **K100** defter sinifinda satir-sonu muafiyet kusuru (sinif onarimi bende) · **K102** nobet yazicisi kok deftere yasakli ic dosya adi uretiyor.
- 🔧 **Bu turda acilan uc kapi kalemi:** (a) shop bayatlik alarminin TETIK ekseni raporladigi bundle evreniyle AYNI DEGIL — 25 tur kirmizi yandi, delta 0 dosyaydi; (b) `devam-sinif-kapisi.py` is-akisi muafiyeti norm/ham ekseninde ayrisiyor; (c) ✅ KAPANDI, asagida (eski hali: yedek karantinasi IKI dosya tutuyor — izleme ankoru (485 sonra 185 B) ve **DEVAM.md'nin KENDISI** (24.578 sonra 5.308 B, KASITLI sikistirma). Ikisi de MESRU kucultme; yani her bilincli defter sikistirmasi bundan sonra karantinaya duser ve o dosyanin yedegi BAYAT kalir. Kalici cozum ad-bazli istisna DEGIL, `.diriltme-izin.json` deseninde bir BEYAN mekanizmasi (dusus bir kez kasitli ilan edilir, kapi beyani gorunce gecirir).
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
