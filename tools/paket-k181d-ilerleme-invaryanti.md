# PAKET K181d — ikinci kol GERÇEK defteri BOZDU: iki invaryant eklenecek

**Mimar:** KraL · **Tarih:** 18 Ağu 2026 · **ÜÇÜNCÜ deneme — kapsam ÇOK DAR**

## OLGU (mimar ölçtü, gerçek `DEVAM.md` üzerinde)
K181 + K181c fikstürlerinde kusursuz çalıştı. **Gerçek defterde felaket:**
```
64 gecis dondu; her gecis: TASINAN=0 TASINAN_MADDE=0
DEVAM.md: 133 satir / 12085 bayt  ->  131 satir / 13243 bayt   (KUCULMESI gereken arac BUYUTTU)
Tek bir kalem satiri yok edildi: ayni satira "** Tam metin ARSIVDE." eki ~60 kez eklendi.
```
Defter git'ten geri alındı; araç main'e **girmedi** (commit'ler geri sarıldı). Arşiv temiz
(1,78 MB / 19.827 satır ≈ 90 bayt/satır — normal, hasar YOK).

## KÖK NEDEN (tek satır, koddan okundu)
Özet çıkarma kolunda **sessiz yedek**: `ozet = "(özet çıkarılamadı)"`. Kodda `KAYIP → DUR`
dalı VAR ama bu yedek onun ÖNÜNE geçiyor. Gerçek defterdeki `T1 PENCERE MUHASEBESI` kalemi
`K###` kimliği taşımıyor → ayrıştırma düştü → yer tutucu yazıldı → satır küçülmedi → tavan
hâlâ aşılı → döngü yeniden yazdı. 64 kez.
Fikstür bunu göremezdi: fikstürdeki maddelerin **hepsi iyi biçimliydi.**

## MİMAR HÜKMÜ — İKİ İNVARYANT (başka hiçbir şey)

**I1 — İLERLEME İNVARYANTI.** Her geçiş defterin **bayt sayısını KESİN azaltmalı.**
Geçiş sonrası bayt `>=` geçiş öncesi ise: hiçbir şey yazma, `ILERLEME_YOK` bas, **rc≠0 ile DUR.**
Bu tek başına 64 geçişlik döngüyü imkânsız kılar.

**I2 — SESSİZ YEDEK KALDIRILIR.** `"(özet çıkarılamadı)"` yer tutucusu SİLİNİR. Kimlik ya
da özet çıkarılamıyorsa: **YAZMA**, `KAYIP: <satirin ilk 60 karakteri>` bas, **rc≠0 ile DUR.**
Kalemi "elden geçir" demek, kalemi EZMEKTEN iyidir.

## KABUL
```
python3 tools/defter-rotasyon.py --kendini-test    → DUSEN=0  (mevcut vakalar KORUNUR)
python3 tools/defter-kota-kapisi.py --kendini-test → DUSEN=0
```
🔴 **BELİRLEYİCİ FİKSTÜR (bu paketin varlık sebebi) — KÖTÜ BİÇİMLİ MADDE:**
tavanı aşan, kapanmış maddesi olmayan, ve içinde **`K###` kimliği OLMAYAN** bir madde bulunan
defter (ör. satır `- 🔴 **T1 PENCERE MUHASEBESI (baglayici):** ...`).
**Beklenen: dosya HİÇ DEĞİŞMEZ (bayt birebir), `KAYIP` basılır, rc≠0.**
Bugünkü kod bu vakada dosyayı BOZUYOR; fikstür ÖNCE kırmızı, onarımdan SONRA yeşil olmalı.

🔴 **İKİNCİ FİKSTÜR — İLERLEME:** ikinci kolu "hiçbir şey küçültmeyen" hâle getiren bir
mutantla koş; beklenen `ILERLEME_YOK` + rc≠0 + **dosya bayt birebir**. Sonsuz döngü YOK.

**MUTASYON (2):** M1 I1'i kaldır → ilerleme fikstürü kırmızı. M2 I2'yi kaldır (yer tutucuyu
geri koy) → kötü biçimli fikstür kırmızı. Yalıtılamazsa `YALITILAMADI` yaz.

## SINIR — İHLALİ İŞİ GEÇERSİZ KILAR
- 🔴 **GERÇEK `DEVAM.md`ye ASLA DOKUNMA.** Ne oku-yaz, ne dene. Tüm testler geçici kopyada.
- **Sana verilen ağaçta çalış.** Mutlak yol (`/Users/okan/dev/pruvo/...`) KULLANMA. Ana ağaca YAZMA.
- Bu dilim YALNIZ I1 + I2 + iki fikstür + iki mutant. Yeni özellik EKLEME, refactor YAPMA.
- Önce kod ve fikstür; docstring EN SON.
- 🔴 **DALDA COMMIT ET**, SHA'yı rapora yaz. Main'e push ETME.

## RAPOR
Dalda, projenin kanonik mühendis raporu adıyla. Son satır:
`K181d KENDINI_TEST=<rc> KOTUBICIM_ONCE_BAYT=<n> KOTUBICIM_SONRA_BAYT=<n> ILERLEME_RC=<rc> MUTANT=<n>/2`
