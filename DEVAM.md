# DEVAM (KraL) — 31 Tem 2026

Onceki ayrintili kayitlar DEVAM-ARSIV.md'de (git disi, lossless).

## 🔴 HESAP TASINMASI
- Envanter + yedek raporu kalici yerde ve Drive kopyalariyla sha256 esit dogrulandi.
  Envanter 117 kalem, 10 asamali tasinma gunu sirasi; Okan'dan elle gereken 19.
- Yedek 2645 dosya / 745824642 bayt; eksik 0, boyut farki 0.
- Yeni kurulumda yerel otomasyon ve yol bagimliliklari geri yukleme rehberine gore
  kurulup kendini-test ile dogrulanmali.
- Diger 4 mimara tasinma talimati Okan tarafindan iletildi.
- Tasinma sonrasina birakilan temizlik ve yenileme isi var; ayrinti DEVAM-ARSIV.md'de.

## 🔴 YARIM IS — FIZIKSEL URUN HATTI
- Verilen kararlar, olculen durum, kapanmamis kusurlar ve siradaki adimlar
  DEVAM-ARSIV.md'de. Devralan oradan devam etsin.
- Kod acilmadan once cayma hakki ayrimi ile ticari sozlesme/sartlar Okan kapisinda.
  Ardindan sema, katalog senkronu ve Ege entegrasyonu tamamlanacak.

## KUYRUKTA (isci verilmedi)
- Metin temizligi plani kardes mimara devredildi.
- Denetim kapisinin rapor kolunda 8 `auto_sil` ve 6 eskalasyon adayi var; bunlar
  urun verisi duzleminde.
- Parite korpusu uc ve uzeri kelimeli sorgulara yapisal olarak KOR; korpus uretimi
  gozden gecirilmeli.
- Arama maliyet kapisi su an bloklamayan seritte; Serit A'ya tasima karari acik.
- Vida ailesi icin PUL-only karari verildi; teslim kardes mimarda.

## KARARLAR
- 200 TL taban tum urunlerde gecerli; parametrik sari seri haric.
- Ustu cizili fiyat parametrik sari seride kapali; konfigur urunler kapsam disi.
- Edge kartlarinda gosterim kismi fakat fail-closed; tam kapsam kardes mimarin duzlemi.
- JSON-LD'ye `priceSpecification` eklenmedi.
- Bayat UPSERT bloklanir; yayinlanan konfigur paritesi bloklayici seritte olculur.
- DEVAM.md public ve git takibinde (`b28051b3`, 31 Tem — bilincli karar, gitignore'da tek
  istisna); DEVAM-ARSIV.md git DISI kalir. Tedarikci/oran/kur/sir, gizli dosya adi ve
  guvenlik-bypass ayrintisi YALNIZ arsive yazilir. Ayni kural CLAUDE.md "BILGI NEREDE"
  satirinda birebir yazili; iki metin CELISIRSE olculen git durumu hakemdir.
- 1 Agu icerik denetimi: DEVAM.md'de kalan 4 hassas blok (acik sunucu fiyat kusuru,
  maskeleme nobetcisi karsilastirmasi, kanca hata davranisi, temizlik oncesi gecmise
  isaretciler) DEVAM-ARSIV.md'ye BIREBIR tasindi, yerlerine notr isaretci birakildi.

## OTURUM KAPANISI — KAPANDI
- Capa kalkani fail-closed: `7ef7427d`.
- Yedek imzasi tek plandan turetildi: `cdadc477`.
- Nobetci desenine kelime siniri eklendi: `cbe6c2a6`.
- Zamanlanmis is nabiz alarmi eklendi: `0db2aafb`.
- Taban fiyat kapisi tum kataloga genislendi: `26bf2777`.
- Arama maliyet kapisi ve onarimi: `2a08ebe7`.
- Sema ikizi tek kaynaktan turetildi: `0df44170`.
- Okan karari uygulandi: parametrik sari seri haric tum urunlerde taban 200 TL.
  1761 kayit 200 TL'ye cekildi (`4a9e2d89`); yazim sonrasi taban alti 0.
  D1 sayi ve hash ekseninde teyitli.
- Canli olay: site aramasinda cok kelimeli sorgular hata veriyordu. Olculen
  basarisizlik 30 istekte 5, yani yuzde 16,7. Kok neden sorgu planinin cevrilmesiydi;
  onarim tek kelimelik ve semantik degismiyor. Canli olcum 13275 milisaniyeden
  3,6 milisaniyeye indi. Duzeltme kardes depoda ve Okan karari geregi kardes mimar
  uygulayacak; KraL tarafinda yalnizca kapi eklendi.
- Yayin suresi medyani 1296 saniye, MAD 115 saniye, 7 kosum.
- Kaynak tarayan bayrak 8 dosya goruyor: 6'si izlenen, 2'si uretilen.
- Temizlik: worktree 5'ten 2'ye, yerel dal 16'dan 8'e indi. Kaldirilan
  worktree'lerin commit'siz isi yama olarak raporlar dizininde.

## POSTA KUTUSU ARSIVLEYICISI — ALINDI + TETIGE BAGLANDI
- Dal main'e alindi: `364095f6` (ileri-sarma, taban `e84b2a65`); 4 dosya, 1153 satir eklendi,
  silinen 0. Kabul testi bagimsiz kosuldu: 14 vaka / 85 iddia / 0 kirmizi.
- Cift yonlu mutasyon kopyada 3/3: kayipsizlik dogrulamasi oldurulunce 16 iddia dustu,
  kilit oldurulunce 4 iddia dustu, ilgisiz degisiklik yesil kaldi; canli dosya imzasi degismedi.
- Kapilar dalin agacinda: CI kapsami 143 kesif / 107 kosulan / 36 muaf; kapi envanteri 7/7;
  is akisi serit beyani 39; kisisel veri nobetcisi yesil. Sizinti taramasi 1153 eklenen
  satirda 10 desen, 0 vurus.
- MIMAR KARARI uygulandi: arac hicbir yerden cagrilmiyordu, izlenen pre-push kanca
  sablonuna baglandi (`fcda5576`). Baglama bicimi ve hata davranisi DEVAM-ARSIV.md'de.
- Tetik ICRAYLA kanitlandi: bos depoda gercek push araci atesledi; kanca kaldirilinca ayni
  iz uretilmedi. Iki vaka kabul testine kalici eklendi (toplam 32 kontrol, 0 kirmizi);
  mutasyonda cagri silinince 3 iddia dustu, ilgisiz degisiklikte yesil.
- Gercek kutuya YAZILMADI: yalniz kuru kosum; 290 satir, tavan 300, tasinacak blok 0 —
  push oncesi ve sonrasi dosya imzasi ayni.
- Olcum tuzagi: senkron teyidi ana agacta bir ara tum kayitlari bayat gosterdi. Sebep
  baska bir oturumun commit'siz hash degisikligiydi; ayni teyit temiz agacta 0 uyusmazlik
  verdi. Kirli agacta alinan senkron olcumu HUKUM DEGILDIR.

## FIZIKSEL URUN SUNUCU FIYAT GARDI + EDGE KART `tur` (ALINDI + CANLI)
- main'e ALINDI: `e31aaf8a` (ileri-sarma). Kapsam TAM 9 dosya, +927/-45: `shop/src/index.js`,
  `secenekler.js`, `shop/src/yonet.js`, `shop/src/eposta.js`, `tools/build.py`,
  yeni `tools/edge-kart-kapisi.py` (+252), `shop/test/fiyat-prova.mjs` (+482),
  `jenerator/test/vitrin-kabul.js`, `.github/workflows/deploy.yml` (+15).
  `urunler.json` diffte YOK. Onarim commit'i: `86665da5`.
- 🔴 DUZ MERGE DEGIL CHERRY-PICK — sebep OLCULDU. Dalin tabani, kardes oturumun commit
  mesajlarindaki satici kimligini temizlemek icin kostugu `filter-branch` + force-push ile
  yeniden yazildi (yerel main 45 commit ayristi, agac icerigi ayniydi). Duz merge dalin
  38 ESKI commit'ini geri getirecekti; bunlarin 4'unde commit MESAJINDA satici adi vardi.
  Yani duz merge, PUBLIC depoda az once kapatilan sizintiyi GERI ACARDI. Cherry-pick
  sonrasi 9 dosyanin 8'i dalla birebir; `deploy.yml` main'de 58 satir ileri (kardes
  oturumlarin yeni kapilari) ve dalin +15 satirini iceriyor.
  DERS: yeniden yazilmis bir tabana dayanan dalda `merge-base` ESKI bir ataya duser ->
  kapsam olcumu 31 dosya/5111 satir gibi SISER ve `urunler.json` sahte cakisma verir.
  Dogru olcum `origin/main...<dal>` uc-nokta ile alindi: 9 dosya.
- Kapilar ENTEGRE durumda (main katalogu + iki commit) kosuldu: 17/17 YESIL — fiyat-prova
  12/12, sepet-panel 14, eposta 17, konfigur-fail-closed 5/5, vitrin-kabul 9,
  edge-kart-kapisi YESIL + mutasyon 3/3 KIRMIZI, fiziksel-urun-kapisi YESIL + mutasyon GECTI,
  ci-kapsam YESIL, kapi-envanteri 7/7, yasal-sayfa-drift 4/4 TEMIZ, odeme-beyani 10/10,
  stok-d1 41, yazdir 8/8, is-akisi YESIL.
- 🔴 ELLE SECILEN KAPI LISTESI YETMEDI — CI KIRMIZI YANDI. Ilk kosum (`30676683982`)
  `build` isinde dustu: `yayin-ic-dil-kapisi.py --kaynak`, 8 vurus / 1 dosya
  (`secenekler.js`). Sebep: `secenekler.js` tarayiciya AYNEN gider; eklenen yorumlar ic
  arac/dosya adlari ve marka dil kuralinin yasakladigi isim halini tasiyordu. Bu kapi
  DALIN TABANINDA YOKTU, kardes oturum sonradan ekledi. Onarimda yorumlarin OZU korundu,
  yalniz ifsa eden ifadeler degistirildi; kod/imza/davranis DEGISMEDI.
  DERS: kapi listesi elle secilmez — `deploy.yml`'den CIKARILIR. Ikinci turda 60 yerel
  CI kapisi cikarilip kosuldu, gercek kirmizi 0.
- Kaynak commit'i ANA CHECKOUT'ta mimar kod-kilidine takildi (Layer 2). Dogru yol: yama
  gecici worktree'ye tasindi, orada commit'lendi, ana agaca `--ff-only` alindi, worktree silindi.
- `ozet.json` BAYATLIK RISKI GERCEK DEGIL: dosya `.gitignore`'da ve CI her yayinda
  `build.py` ile YENIDEN URETIYOR. Yine de main'in guncel katalogundan uretildi:
  16.167 urun -> 134.271 bayt (butce 150 KB), 271 kart, `tur` tasiyan 148; agac TEMIZ.
- "tur tasiyan kart ~237 olmali" beklentisi HATALIYDI: `ozet.json` tam katalog degil,
  271 kartlik VITRIN ozeti. 237 = katalogtaki fiziksel urun sayisi; 148 = bunlardan
  vitrine giren kart. Iki sayi ayni eksende DEGIL.
- D1 senkron teyidi: sayi ekseni 16.167 == 16.167; icerik ekseni 16.167 urun_hash birebir,
  uyusmaz 0 / eksik 0 / fazla 0.
- CI: `merge-base --is-ancestor` exit 0 ile KANITLANDI. Kosum `30678515290` (`86665da5`):
  envanter/serit-b/cron-nabzi/build/deploy/yayin YESIL. Genel sonuc `failure`, sebebi AYRI
  bir is: kardes oturumun YENI `mesaj-nobeti` kapisi kendini testinde 56/58 — dusen iki
  iddia PERFORMANS BUTCESI (700 jeton 6438 ms / butce 3000 ms; 50 jeton 524 ms / butce 400 ms).
  Dogruluk iddialarinin hepsi yesil; bu is BIZIM degisiklikle ILGISIZ ve ayri is olarak isaretlendi.
- CANLI DOGRULAMA (cache-bust'SIZ, UA basligi ile):
  · fiziksel urun sayfasi (4 ornek): kapinin kendi 9 kancasi ANA GOVDEDE 0/9, kalmasi
    zorunlu 3 oge 3/3 VAR. Nobetcinin NEGATIF yonu ayni kosumda olculdu: bir baski urunu
    9/9 kanca gosteriyor -> olcum CANLI, olu DEGIL.
  · canli `ozet.json`: `tur` tasiyan kart DAGITIM ONCESI 0 -> DAGITIM SONRASI 148
    (271 kart). Alan edge'e INDI.
- ONCEDEN KIRMIZI (bu isle ILGISIZ, ayri is): `shop/test/kabul.js` test 7 (agli parite,
  26 gecti / 1 kaldi) ve `tools/filament-test.py` (7/25 — fikstur bir fiziksel urun seciyor).
  Ikisi de dalin tabaninda da kirmiziydi.
- Dal worktree'si AKTIF oturumda -> §7 temizligi BILEREK YAPILMADI. `durum.py` dali
  "38 ileri / DEVAM EDIYOR" gosterir; bu cherry-pick'in beklenen sonucudur, kapsamdaki
  9 dosyanin 8'i main'de BIREBIR, 9.'su (deploy.yml) main'de daha ileri.

## FIZIKSEL URUN SAYFASI — 3D-BASKI SECIM UI'I KALDIRILDI (ALINDI + CANLI)
- Dal main'e alindi: `1a938405` (merge-base `39036e18`). Kapsam TAM 3 dosya, +408/-5:
  `tools/build.py` (+52/-5), yeni `tools/fiziksel-urun-kapisi.py` (+345),
  `.github/workflows/deploy.yml` (+16). Cakisma yok, taban taze olculdu.
- Sebep: fiziksel urun sayfasi 3D-baski secim arayuzunu basiyordu. Renk "Diger"
  secimindeki +%15 yalniz gorsel degildi; `secenekler.js` hesaplaFiyatKurus'u
  `shop/src/index.js` sepetiFiyatla da cagirdigi icin SUNUCUDA DA tahsil ediliyordu.
- Merge oncesi 9 kapi dalin agacinda kosuldu, hepsi exit 0: fiziksel-urun-kapisi
  (+ --mutasyon), ci-kapsam-test (142 kesif / 106 kosulan / 36 muaf), kapi-envanteri
  7/7, yasal-sayfa-drift 0/4 sapma, konfigur-test, jsonld-offers (15948 offers'li,
  0 ihlal), merchant-feed, odeme-beyani 10/10.
- D1 senkron teyidi: 15975 == 15975; hash uyusmazlik 0, eksik 0, fazla 0.
- CI: kendi SHA'sinin kosumu (30661423450) eszamanlilikla IPTAL edildi. Kabul, SHA'yi
  ata olarak tasiyan ardil kosumdan alindi: 30661557861, headSha `e84b2a65`,
  `merge-base --is-ancestor` exit 0. build/deploy/yayin ucu de success. Genel kosum
  `failure` gorunur; sebep ILGISIZ `cron-nabzi` alarm isidir (yayini durdurmaz).
- CANLI olcum (canonical URL, cache-bust YOK, UA basligi verildi). Onarim ONCESI ayni
  olcum 14 ihlal veriyordu (olcum duyarli, tautoloji degil). SONRASI, GERCEK DOM ogesi
  ekseninde fiziksel sayfa / `tur`suz kontrol sayfasi:
    id=renkButonlar 0/1 · id=filCipler 0/1 · id=renkOzel 0/1 · class=renk-btn 0/4
    class=fil-cip 0/5 · data-renk 0/4 · data-malzeme 0/4 · urun-ici rehber linki 0/0
    KART_SECIM=false 1/0 · KART_SECIM=true 0/1 · "Diger (+%15)" 0/1 · "+%15" 0/1
    "Tavsiyemiz" 0/1 · adetSec 15 VAR · cartBtn 2 VAR
  Ham jeton taramasindaki 7 kalinti BAGLAMIYLA olculdu, hepsi ATIL: paylasilan CSS
  sinif tanimlari, `KART_SECIM=false` ile ulasilamayan JS dallari ve her sayfada olan
  genel alt-bilgi `/malzeme-rehberi/` linki. `tur`suz kontrol sayfasinda regresyon yok.
- 🔴 ACIK KALINTI (kapsam DISI, kapanmadi): sunucu fiyatlama tarafinda kapanmamis bir
  kusur var; olculen ayrinti ve tekrar uretim adimlari DEVAM-ARSIV.md'de. Isci verilmedi.
- Temizlik YAPILMADI: `claude/exciting-hodgkin-91ec53` dali ve worktree'si aktif bir
  oturumda kullaniliyordu; `worktree remove` / `branch -D` bilerek kosulmadi.

## SIZINTI NOBETCISI — KENDI DOSYASINDAKI ORNEK ADLAR TEMIZLENDI (ALINDI)
- `tools/commit-mesaji-kapisi.py` kendi docstring/yorumlarinda iki gercek yasakli adi
  ORNEK olarak duz yaziyordu — dosyanin kendi basligindaki "yasakli ad bu dosyada
  yazmaz" beyani kendi icinde ihlal ediliyordu. Depo PUBLIC.
- OLCUM: bildirilen 2 konum yerine 3 konum / 6 satir bulundu (baslik AD EKSENI blogu,
  `normalize()` ustundeki yorum, `adaylar()` docstring'i). Ucu de `_UYDURMA`
  fiksturlerindeki uydurma adlarla degistirildi; ayrica "tum ornekler uydurmadir"
  beyani iki yere kalici olarak yazildi.
- Kapsam TAM 1 dosya, +9/-6. Kod/imza/davranis DEGISMEDI (yalniz yorum ve docstring).
- Kabul: `--kendini-test` 58/58 yesil; mutasyon bataryasi 15/15 oldurucu KIRMIZI,
  3/3 ilgisiz kontrol YESIL, canli dosya sha256 esitligi TAM.
- Merge `a5fcef74` (ileri-sarma, taban `7f0735e9`). D1 teyidi: sayi ekseni
  16407 == 16407; icerik ekseni 16407 urun_hash birebir, uyusmaz 0 / eksik 0 / fazla 0.
- KANIT: `git grep -i` calisma agacinda VE `origin/main`'de VURUS 0.
- ~~🔴 GECMIS TEMIZLENMEDI — OKAN KARARI (1 Agu): blob gecmiste KALIYOR.~~
  **BU KAYIT GECERSIZ (1 Agu, Okan yeni karar):** gecmis TEMIZLENDI. Icerik ekseni
  yeniden yazildi ve `--force-with-lease` ile itildi (kaynak commit ve yedek ref adi
  DEVAM-ARSIV.md'de).
  Pencere 18 commit (1825 ata DOKUNULMADI), degisen dosya kumesi TAM OLARAK 1 dosya /
  9 commit, baska hicbir blob degismedi, UCTAKI AGAC birebir ayni, eski uc <-> yeni uc
  `git diff` BOS, mesaj/yazar/tarihler bayt-birebir korundu. Push sonrasi olcum:
  mesaj ekseni 0 (1843 commit), icerik ekseni 0 (163 blob), calisma agaci 0, uzak dal
  kalintisi 0 (34 dal). Yedek ref alindi (adi DEVAM-ARSIV.md'de).
- 🔴 TEMIZLIGIN KALICILIGI ARTIK KAPIYA BAGLI: gecmis IKI KEZ temizlenmis, IKI KEZ geri
  gelmisti; sebep her seferinde temizlik ONCESI taban uzerine kurulmus bir dalin merge
  edilmesiydi. `tools/gecmis-geri-donus-kapisi.py` (pre-push, fail-closed + CI gorunurluk
  kolu) bu ekseni kapatir: itmenin origin'e EKLEDIGI TUM commit'leri (yalniz yeni
  yazilanlari degil) mesaj VE icerik ekseninde tarar. Kabul 40 vaka / 0 hata (gercek git
  + gercek push), mutasyon 17/17 oldurucu OLDU, 3/3 ilgisiz YESIL.

## TABAN (yeniden olc, ezberleme)
- Katalog: taban alti 0; D1 sayi ve hash ekseninde uyumlu.
- Yayin suresi: medyan 1296 saniye, MAD 115 saniye, 7 kosum.
- Calisma alani: 2 worktree, 8 yerel dal.

## NOBETCI BUTCE KAPANISI (mesaj-nobeti performans ekseni)
- Performans butcesi olculdu: I1 suresinin yuzde 100,6'si PBKDF2 tabani, hash disi pay
  yuzde 0,21 -> optimize edilecek yer YOK.
- Mutlak ms butcesi tasinabilir DEGIL: ayni CPU'da kripto kutuphanesi farki 3,21 kat,
  yerel->CI 3,60 kat (kosucu I1 medyan 6313 ms MAD 13, n=9).
- Cozum main'de: sure ekseni donanimdan bagimsiz birime cevrildi (`d09cc2cf`, paralel
  oturum) + ikiz-tanim nobetcisi eklendi (`d8d378cc`, I5/I5b/I5c).
- Ikiz-tanim acigi OLCULDU: turetilen hacim degismezken gercek `_ozetle` cagrisi
  5701 -> 0 ve 5701 -> 12090 olabiliyordu; "hic ozetleme yapma" mutasyonunda sure/hacim
  iddialari YESIL kaliyordu. Simdi I5 yakaliyor.
- Kendini-test: 84/84 yesil. Regresyon olcumu: 2033 girdi, fark 0.
- ACIK KALAN: `mesaj-nobeti` hala kirmizi, sebebi FARKLI kapi — "ADAY BUTCESI ASILDI:
  157276 > 150000", `c779e6f0` geri-donus kapisi.
- Alinmayan dal: `worktree-agent-ab5e949730e4133e5` bayat kaldigi icin iptal edildi,
  kurtarilan tek parca I5.


## MERGE REDDEDILDI — eski tabanli nobetci dali (1 Agu, olculdu)

- Bir mesaj-nobetcisi dali (uc 15 ileri) main'e alinmak uzere verildi; **ALINMADI.**
  Sebep tek degil; ucu de olculdu, ucu de tek basina bloklayici.
- **(1) Taban kopuk.** Dal, gecmis yeniden yaziminden ONCEKI taban uzerinde. Dalin ucu
  main'in atasi DEGIL (`--is-ancestor` rc=1). `merge-base` cok eski bir ataya dusuyor,
  bu yuzden otomatik kapsam olcumu **12 dosya / +6604** basiyor (icinde urun verisi
  +4398 ve 6 cakisma); gercek is ise **2 dosya / +228/-16**. Uc-nokta olcum bu tuzakta
  DUZELTMIYOR (o da merge-base'e dayanir); dogru olcum dalin KENDI commitinin diffi.
- **(2) Duz merge sizintiyi geri acardi.** Merge, dalin 15 eski commitini geri baglardi;
  bu commit mesajlarinda gecmis temizliginde cikarilmis tedarik zinciri adlari duruyor.
  Depo PUBLIC. Pre-push gecmis geri-donus kapisi zaten fail-closed durdururdu.
- **(3) ASIL SEBEP — is main'de ZATEN VAR ve dal surumu GERILEME.** Ayni maskeleme
  acigini kardes oturum bagimsiz kapatmis. Iki surum karsilastirildi: main surumu
  fail-closed, dal surumu daha zayif; merge ya da cherry-pick main'in daha guclu
  maskesini dalin zayif surumuyle DEGISTIRIRDI. Iki surumun karsilastirmali ayrintisi
  DEVAM-ARSIV.md'de.
- Cherry-pick de temiz uygulanmiyor: iki dosyada da CAKISMA (kapi dosyasi 2 blok,
  mutasyon dosyasi 1 blok) — main tepesi ayni fonksiyonlarda ilerlemis.
- Dal KENDI icinde saglikli: alti kapi da dalin agacinda rc=0 (kendini-test 90/90,
  kaynak tarama 5 dosya 0 vurus, CI kapsam 148 kesif / 112 kosum / 36 muaf, kapi
  envanteri 7/7, kanca nobeti 11 eksende 11 yesil, kisisel veri testi tum kollar yesil).
  Sorun kalitede degil, **tabanda ve mukerrerlikte.**
- **KALAN TEK OZGUN PARCA:** marka muafiyetinin kayitli govdeden turetilmesi; acik takasin
  ayrintisi DEVAM-ARSIV.md'de. Bu, main'in GUNCEL kodu uzerine yeniden turetilmeli — bu dal
  uzerinden DEGIL. Paralel bir oturum su an ayni muafiyet capalari uzerinde calisiyor;
  is verilmeden once cakisma kontrol edilmeli.
- Main'e HICBIR SEY yazilmadi; gecici cherry-pick agaci ve dali silindi. Dogrulama: ana
  calisma agaci porcelain BOS, dal worktreei porcelain BOS (dal oturumu aktif, DOKUNULMADI).
  D1 teyidi: sayi ekseni 16499 == 16499; icerik ekseni 16499 urun_hash birebir,
  uyusmaz 0 / eksik 0 / fazla 0.


## 6c SIZINTI NOBETCISI BEYAZ LISTESI + CAPA ONARIMI — main'e ALINDI (1 Agu, cherry-pick)

- Alinan iki commit: `0ea09977` (dar beyaz liste + ic nobetci + CI adimi) ·
  `3be869ac` (S1..S4 sart-basi fikstur, sahte M2 onarimi, kol granulu beyani).
  Kaynak dal `claude/exciting-hodgkin-91ec53` (`f03bd0c0`/`effa4747`); dal AKTIF, dokunulmadi.
- **DUZ MERGE YAPILMADI — cherry-pick.** Dalin onceki commitleri main'e zaten cherry-pick ile
  alinmisti; dal tabani gecmis yeniden yaziminin oncesinde. Duz merge dalin eski commitlerini
  geri baglar ve temizlenmis tedarik zinciri adlarini PUBLIC gecmise geri acardi.
- **Kapsam (uc-nokta, `origin/main...HEAD`): 3 dosya / +321/-6** —
  `tools/durum-test.py` +255/-1 · `tools/is-akisi-kapisi.py` +58/-5 ·
  `.github/workflows/deploy.yml` +14. `urunler.json` GORULMEDI (MaCiT duzlemi korundu).
  Cherry-pick CAKISMASIZ uygulandi (iki kez: taban main ilerleyince yeniden turetildi).
- **Sizinti taramasi (gidecek MESAJLAR + diff):** `.urun-kaynaklari.json`'dan turetilen
  **11.357 adlik** tedarikci/tasarimci kumesine karsi **0 vurus**; telefon/eposta/RAPOR-*/
  kova/AWS/JWT/Slack/hex40 siniflarinda diff **TEMIZ**.
- **Kapilar — ENTEGRE agacta (main'in guncel katalogu), 9/9 rc=0:**
  durum-test **9/9** (6b 44.906 aday deger tarandi, 0 sizinti) · `--ic-nobetci` **12/12**
  (E1 esdegerlik: 2508 kalemlik korpus, ayrisan 0) · durum-edge 8/8 · derin-cap 3/3 ·
  kisisel-veri YESIL · ci-kapsam YESIL · kapi-envanteri 7/7 · is-akisi-kapisi YESIL
  (8 iddia, kendini-test 165) · mimar-kilit 224/224.
- **Gerekce:** CI run `30691723803` `serit-b` kirmizisi — TEST 6c bir GIT COMMIT BASLIGINI
  kimlik sandi (`TRIM/MANIFOLD/...`, 69 kr, buyuk harf + `/`, `[A-Za-z0-9/+]{40,}`
  desenine takiliyor). Gercek sir YOKTU. **Desen DARALTILMADI**, dar beyaz liste eklendi
  (her segment 2..20 ASCII harf + tek bicim). Bagimsiz curutucu: 1,4M sentetik sirda 0 kacak,
  AWS/JWT/hex40/ham base64/Slack webhook 5/5 yakalaniyor.
- **CI kaniti:** kosum `30695159960` (headSha `01e2f1881d`),
  `git merge-base --is-ancestor 3be869ac 01e2f1881d` **exit 0**.
  **`serit-b` = success** (kirmizi olan is buydu). Yeni adim
  `6c sizinti muafiyeti ic nobetcisi (mutasyon)` kosumda VAR ve success; daha once patlayan
  `Katalog/parti veri kapilari kabul testi` de success. Kendi SHA'mizin dogrudan kosumu
  (`30695091285`) escakismayla `cancelled` olmustu — `--limit 1` kanit sayilmadi, ardil
  kosum is-ancestor ile kanitlandi.
- **D1 teyidi:** sayi ekseni 16518 == 16518; icerik ekseni 16518 urun_hash birebir,
  uyusmaz 0 / eksik 0 / fazla 0. Sema degismedi, `--sema` KOSTURULMADI.
- **Canli site dogrulamasi GEREKMIYOR** — bu is yalniz CI kapisi, musteri yuzeyi degil
  (site ciktisi bayt olarak degismedi).
- Push notu: push `remote rejected` verdi cunku kardes oturum ayni anda ilerletmisti;
  o oturumun push'u BIZIM iki commitimizi ata olarak TASIDI (is-ancestor exit 0 ile
  dogrulandi), yeniden push GEREKMEDI. `--force` kullanilmadi.
