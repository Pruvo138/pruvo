# DEVAM (KraL) — 31 Tem 2026

Onceki ayrintili kayitlar DEVAM-ARSIV.md'de (git disi, lossless).

## OTURUM KAPANISI — 1 Agu 2026 (KraL · CI kirmizilari turu)

### CANLIYA GITTI
Not: iki SHA gecmis yeniden yaziminda degisti; varlik ICERIK ekseninde dogrulandi.
- **D1 istemci hata siniflandirmasi + fail-loud cikti cozumu** (`GECICI_KODLAR` main'de).
  `yayin` isi, D1'in CPU-tavani sifirlama kodunu KALICI sayip yeniden denemiyordu; tirnakli
  JSON bicimindeki TUM kod kollari oluydu. Artan geri cekilme 2/8 sn, tavan 10 sn. Kabul 104 iddia.
  Bagimsiz curutucu 1. turda onarimin bagiran hata davranisini SESSIZ GECISE cevirdigini
  buldu -> geri cekildi.
- **Fiziksel urun sayfasindan 3D-baski secim arayuzu kaldirildi** — merge `1a938405`
  (`tools/fiziksel-urun-kapisi.py` main'de). 15930 baski urununde uretilen sayfa BAYT-ESIT.
- **Fiziksel uruntte malzeme/renk fiyat carpani SUNUCUDA kapatildi** — merge `e31aaf8a`
  (`fizikselMi` main'de). Gercek tahsilat ucunda dogrulandi: her secim liste fiyati.
  961.980 kombinasyonda baski-urunu regresyonu 0. Ayrica edge kartina `tur` alani eklendi
  (canli olcum: 0 -> 148 kart) ve fiziksel siparis kaydindan malzeme/renk beyani kaldirildi.
- **Icerik sinifi kabul testindeki yanlis-pozitif capalandi** — merge `0ea09977` + `3be869ac`.
  Bir urun partisi commit basligi desene takiliyordu. Desen DARALTILMADI; dar beyaz liste +
  sart-basi fikstur eklendi. Curutucu olcumu: 1,4M sentetik ornekte 0 kacak.

### KOSUYOR
- Yok. Bu oturumun delege ettigi tum isler kapandi, dal/worktree temizlendi.
  Okan'in ayri oturumda baslattigi commit-msg nobetcisi performans butcesi isi AYRI;
  `mesaj-nobeti` su an YESIL.

### BEKLIYOR
- **KARDES DEPO (bot deposu):** edge Worker kart alan listesinde `tur` YOK -> sepet panelinde
  GOSTERILEN tutar sunucununkinden farkli kalir. Main katalogunda 237 fiziksel urunun 137'si
  bu koldan geliyor. Tahsilat DOGRU; sapma yalniz GOSTERIM. Olculdu, kutuya yazildi.
- **OKAN KARARI:** `d1-uzlastirici` cron tetikleyicisinin deploy sonuna alinmasi.
  Olculdu: 15 dk'lik cron 3,5 saatte 0 kez atesledi (GitHub zamanlanmis is best-effort).
- **SIRADAKI IS (mimar):** `filament-test.py` 7/25 — fiksturu artik bir fiziksel urune dusuyor;
  CI'da muaf ama gercek kirmizi.
- **NOBETCI BORCU** (bugunku davranis DOGRU, gelecek regresyon icin yazili iddia EKSIK): odeme kalem adi
  bicimi ve veri kolonu bicimi KELIME ariyor (bicim degil); yonetim ekranindaki fiziksel kolun
  iddiasi yok.

### DERS (olculdu)
- Uc kez kabul testi yemyesilken bagimsiz curutucu gercek kusur buldu; ikisi ayni sinifti —
  duzeltme, kapattigi deligin YANINDA yeni bir sessiz ayrisma aciyordu. Kapi yazmak yetmiyor;
  kapinin GORMEDIGI ekseni ayri bir goz aramali.
- Gecmis yeniden yazildiktan sonra DUZ MERGE, temizlenmis commit mesajlarini geri getirir.
  Bu turdaki uc merge de cherry-pick + ff-only ile alindi.

## KARARLAR
- 1 Agu icerik denetimi: DEVAM.md'de kalan 4 sinifli blok
  maskeleme nobetcisi karsilastirmasi, kanca hata davranisi, temizlik oncesi gecmise
  isaretciler) DEVAM-ARSIV.md'ye BIREBIR tasindi, yerlerine notr isaretci birakildi.

## OTURUM KAPANISI — 1 Agu 2026 (KraL)

### CANLIYA GITTI
- `7da1124a` — toplu ekleme yolunda altkategori dogrulamasi + cikis kodu kabul testi.
  Iki commit guncel main uzerine cherry-pick ile alindi (duz merge YOK: dal tabani
  yeniden yazilmis gecmisin oncesindeydi). Kapsam 2 dosya / +286 satir; urun verisi
  dosyasi diffte YOK. Bagimsiz kosulan kabul: dal testi rc=0 / 180 iddia · altkategori
  kapisi rc=0 / 35 iddia · CI kapsam rc=0 · kapi envanteri rc=0 / 21 iddia · is akisi
  rc=0 · kisisel veri rc=0 · kanca nobeti rc=0. Eklenen 286 satir 8 desen sinifina
  karsi tarandi, 0 vurus.
- `204a076d` — izlenen kok belgeler icin icerik sinifi nobetcisi; CI `build` isinde iki
  adim. Nobetci ad-BAGIMSIZ (kok seviyedeki izlenen belge uzantilari), muafiyet listesi
  TUTMAZ. Kendini-test 62 kontrol. Kaynak daldaki metin tasimasi bayat taban uzerindeydi;
  tasima bu kayitta guncel metin uzerinde YENIDEN yapildi (asagida).
- Bu kayit — DEVAM.md tavan tazelemesi: 253 satir arsive BIREBIR tasindi (kayip 0),
  nobetci ayni agacta rc=0.

### KOSUYOR
- Bu listenin elle tutulan hali BAYATLIYORDU (11 dal yaziliydi, agac sayisi tutmuyordu).
  Tek dogruluk kaynagi artik olculen git ciktisi: `git -C /Users/okan/dev/pruvo worktree list`.
  Ezberleme, olc.

### 1 AGU 15:00 TURU — olculdu
- **Ege bilgi kaynagi fiyat/malzeme vaadi notrlestirildi** — merge (dal tek commit
  `5e8dc5fa`, taban `627159df` main'in GERCEK atasi, ata testi yesil). Kapsam TAM 2 dosya,
  +11 / -6; urun verisi diffte YOK, cakisma YOK.
  Spec 2 satir isaret etti, isci tam okumayla **4** buldu; ikisi spec disiydi (biri Ege'ye
  hazir agiz cumlesi olarak yaziliydi). Bir satir URETILEN blok icindeydi -> elle degil
  **ureteci** duzeltildi, yoksa ilk kosumda geri gelirdi. Kabul: 6 kapi rc=0
  (ic nobetci 73/73, mutasyon 14 mutant / 0 sag kalan). Kapi GEVSETILMEDI.
- 🔴 **OLCULEN ACIK: kapi bu zarar sinifina KOR.** Yasak kaliba ait 4 ozgun satirin
  dordu de kapinin kendi bulgu fonksiyonundan **0 bulguyla** gecti. Dahasi kapinin
  fikstürlerinden biri yasak cumleyi **beklenen-YESIL** olarak kayitli tutuyor — yani kapi
  bu sinifta sertlestirilemez durumda. Fikstür TERSINE CEVRILMELI; CI'da yayin durduran
  dosya oldugu icin isci DOKUNMADI, karar bende. **SIRADAKI IS.**
- **Marin altkategori izinli kumesi 3 -> 11.** Mimar karari: istenen yazimlardan uctu
  duzeltildi (satici vitrininden kopyalanmis yazim hatasi + yabanci yazim), biri
  EKLENMEDI (o bolum kalici kapandi, sifir urun tasiyacak olu yapilandirma olurdu).
  Carpisma 0 · imza nobeti 11/11 temiz · altkategori kapisi rc=0 · toplu test rc=0.
- **Parite (ag acik, yeniden kosuldu):** semantik gerileme **0/1199 site · 0/844 Ege**.
  Kirmizinin tek sebebi ayri: **6 urun yerelde var, D1'de yok** — urun verisi duzleminin
  senkron gecikmesi, bu turun degisikligiyle ilgisi YOK.
- Ilk kosumda parite ag KAPALI ortamda kirmizi yanmisti (tum sorgular basarisiz);
  "gerileme" degil **olculmemis**ti. Ag gerektiren kabul ayri kosumla alinir.

### BEKLIYOR
- OKAN: fiziksel urun hattinda cayma hakki ayrimi + ticari sozlesme/sartlar.
- OKAN: hesap tasinmasinda elle gereken 19 kalem.
- MIMAR KARARI: arama maliyet kapisinin bloklayan serite tasinmasi.
- ISCI VERILMEDI: denetim kapisi rapor kolundaki adaylar (urun verisi duzlemi).
- KARDES MIMAR: vida ailesi PUL-only teslimi, metin temizligi plani.

## TABAN (yeniden olc, ezberleme)
- Katalog: D1 sayi ekseni 16542 == 16542; icerik ekseni birebir, uyusmaz 0 / eksik 0 / fazla 0.
- Calisma alani: 6 worktree, 13 yerel dal (kapanista 3 worktree + 8 olu dal temizlendi).

## EK — mesaj-nobeti kirmizisi: geri-donus kapisi kapandi (1 Agu, kapanis ek kaydi)

- mesaj-nobeti kirmizisinin ikinci sebebi kapandi: geri-donus kapisi taban cozumu
  onarildi (`f85ca982`, S1).
- Kok sebep: force-push sonrasi olay yukundeki `before` nesnesi YETIM kaliyordu;
  `fetch-depth: 0` yetmez (nesne hicbir ref'te degil). Cozum: `cat-file -e` patlayinca
  yedege dusmeden once `git fetch --no-tags <uzak> <sha>` ile nesneyi kurtar (yalniz CI;
  kanca kolu bu yola girmez). Fetch basarisizsa davranis aynen eskisi.
- Olculen: yedek 50 commit penceresi 231140 aday = butcenin %154'u (yapisal asim);
  dogru menzil 18 commit / 67998 aday (%45,3). Gercek itmeler: medyan 1, p95 4, maks 45.
- Kirpma (`f416842d`, paralel oturum) KORUNDU ama artik SESSIZ DEGIL: kirpildiginde
  taranmayan commit + aday sayisi basiliyor, "temiz" hukmu EKSIK OLCUMLU oldugunu soyluyor.
- Kabul: kapinin kendini-testi 49 vaka / 0 hata (40 -> +9); mutasyon bataryasi 17/17
  olduruculu OLDU, 3/3 ilgisiz yesil.
- CI teyidi: kosum 30695623857, `mesaj-nobeti` **success**, taban COZULDU
  (yedege dusmedi), taranan 1 commit / 1789 aday = butcenin %1,2'si.
- NOT: o kosumda `before` yetim DEGILDI (saglikli hal); yetim-kurtarma yolunun gercek
  GH Actions ortaminda calistigi ayni job'un kendini-test adiminda goruldu (vaka 12c).
- Butce (150000) ve yedek pencere (50) BILEREK degistirilmedi.


## MERGE — marka muafiyeti kayitli alan adi govdesinden (1 Agu, olculdu)

- Merge `f6840e3f` (taban `11334fef`, dal tek commit `b85f5b4b`). Kapsam TAM 2 dosya,
  +259 / -4. Cakisma YOK. Kendi desen taramam: 6 sinifta 0 vurus.
- **Sorun:** muafiyet host'un ILK etiketinden okunuyordu. Olculdu (n=1294 katalog
  markasi, alan adi ekseni tek basina): marka etiketi one alinmis bayi bicimi
  **1294/1294 gecer** (kacak tamamen acik), on ekli mesru marka adresleri
  **1293/1294 durur** (yanlis-pozitif). Batarya bu ekseni HIC olcmuyordu.
- **Cozum:** muafiyet kayitli govde etiketinden turer; ikinci seviye kayit ekleri
  icin bir ust etikete bakilir. Kacak yonu **1294 -> 0**, cok parcali uzantili
  bicimde **1294 -> 0**, yanlis-pozitif **1293 -> 0**, duz marka tabani
  **1294/1294 degismedi**.
- **Beyan edilmis takas:** ters bicim (alt alan marka sahibinin kayitli alani
  altinda) **1/1294 -> 1294/1294**, cok parcali uzantida **0 -> 1294/1294**. Gerekce
  kodda: o alan yalniz marka sahibinin tekelinde; ad ozet artefaktindaysa ikinci hat
  tutar. Ikinci hattin iki ekseni ve tireli yazimdaki kalinti olcumle yazildi.
- **Dokunulmayan:** maskeleme ve desen dilim taramasi fonksiyonlarinin govdeleri main
  ile **birebir ayni** (sha256 karsilastirildi); degisen tek kod satiri muafiyet kolu.
- **Kabul:** kendini-test **84 -> 95** iddia rc=0; mutasyon **28/28 oldurucu OLDU**,
  3/3 ilgisiz kontrol yesil, sag kalan 0, canli dosya sha256 esitligi TAM.
  Yedi kapi rc=0 (kendini-test, kaynak-tara, ci-kapsam 149/113/36, kapi envanteri 7/7,
  kanca nobeti 12 eksen 12 yesil, kisisel veri testi, mutasyon).
- **D1 teyidi:** sayi ekseni 16542 == 16542; icerik ekseni 16542 urun_hash birebir,
  uyusmaz 0 / eksik 0 / fazla 0.
- **Temizlik:** merge edilen worktree + dali silindi (uc on kontrol temiz). Baska bir
  oturumun aktif agaci ve dali KORUNDU, dokunulmadi.
- 🔴 **OLU DAL — DIRILTMEYIN:** bu isin ILK turu eski taban uzerinde kurulmus bir dalda
  yapilmisti ve **merge EDILMEDI**. Sebep: (a) taban gecmis yeniden yaziminin
  oncesindeydi, duz merge temizlenmis adlari public gecmise geri getirirdi; (b) o dalin
  maskeleme onarimi main'de zaten VARDI ve main surumu daha guclu (fail-closed) idi,
  merge GERILEME olurdu. Is guncel main uzerine YENIDEN turetildi; alinan surum budur.
  O dal artik ISLEVSIZ.
