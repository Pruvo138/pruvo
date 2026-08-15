# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 15 Agu (sabah) — bu turda canliya giden

- Shop DAGITILDI (Okan acik onayi): canli `34d4db64` yerine `01d41b07`; bayatlik kapisi TAZE rc=0. 27 turdur yanan alarm kapandi.
- PARCA 2 `53f090e7`: 274 urunde birincil tavsiye PETG yerine ABS (PETG-ilk 274 sonra 0 · ABS-ilk 13 sonra 287 · ezmeli 433 sabit). Ayni commit'e MaCiT'in Ducati partisi (167) karisti — paylasilan agac; olculdu, mesaja yazildi, kutuya bildirildi.
- Mimar karari `9e18833e`: 4 yasak-tur urun silindi (1 maket · 2 logo/plaket · 1 surec adi). Katalog **27420**, D1 geri-okuma DOGRULANDI. MaCiT'in rozet/plaket icin "KEEP" secenegi REDDEDILDI.
- Yedek zinciri iki kez KIRIKTI, ikincisinde SINIF kapatildi (`4a97fda5` sonra `7f5d45b6`): tek dosyanin reddi artik kosumu oldurmuyor — reddedilen ATLANIR (kanonik yedegi degismez), kosum surer, atlama karantina defterine yazilir + rc=1. Kabul 5/5 + mutasyon 5/5. Canli: yedek TAMAMLANDI, KARANTINA=1. Ders: [[koruma-kurali-korudugunu-durdurur]].
- Defter: sinif kapisi acildi (`fec2daf9`, 177 satir arsive), sonra defterin tam hali arsive alinip hedefe indirildi.

## ACIK KALEMLER (kaynak-dogrusu: `acik-kalemler.md`)

- 🔴 **K104** — nobet is akisi 200 kosumda 11 success / 77 failure / 110 cancelled; son yesil 12 Agu 11:17Z. Teshis Codex'te, HUKUM MIMARDA.
- **K104B** — nobet is akisinda IKI kapi main'de de KIRMIZI (mutasyon capalari M06/M31 + 2 kapinin kanca kablosu envanterde yok). Tabanda olculdu, dalin getirdigi DEGIL.
- **K99** bag kolonu spec'i · **K100** defter sinifinda satir-sonu muafiyet kusuru (sinif onarimi bende) · **K102** nobet yazicisi kok deftere yasakli ic dosya adi uretiyor.
- 🔧 **Bu turda acilan uc kapi kalemi:** (a) shop bayatlik alarminin TETIK ekseni raporladigi bundle evreniyle AYNI DEGIL — 25 tur kirmizi yandi, delta 0 dosyaydi; (b) `devam-sinif-kapisi.py` is-akisi muafiyeti norm/ham ekseninde ayrisiyor; (c) yedek karantinasindaki `posta-kutusu-kaan-izleme-ankor.txt` (485 sonra 185 bayt, MESRU rolling dusus) her kosumda rc=1 uretecek — kalici cozum ad-bazli istisna DEGIL, `.diriltme-izin.json` deseninde bir BEYAN mekanizmasi.
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
