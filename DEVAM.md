# DEVAM (KraL) — 31 Tem 2026

Onceki ayrintili kayitlar DEVAM-ARSIV.md'de (git disi, lossless).

## OTURUM KAPANISI — 1 Agu 2026 (KraL · 15:00 emri + beyan/olcum turu)

### CANLIYA GITTI (hepsi olculdu, hepsi itildi)
- **Yasak fiyat-vaadi kalibi bilgi kaynagindan kaldirildi + KAPI ARTIK GORUYOR.** Kalip 2
  degil **4** yerdeydi; biri URETILEN blok icindeydi, ureteci duzeltildi. Kapi bu sinifa
  KORDU: dort satir da 0 bulguyla geciyordu ve bir fikstür yasak cumleyi beklenen-YESIL
  tutuyordu. Yakalama **0/4 -> 4/4**, ic nobetci **73 -> 103**, mutasyon 14/14, yanlis
  pozitif 0/3 korpus. Yol boyunca gercek bir yayin durdurucu bulundu: kuralin DOGRU yazilisi
  (yasagin olumsuz emri) ortak listede yoktu, kapi o metni kirmizi yakiyordu.
- **Marin altkategori izinli kumesi 3 -> 11** (`c86c29dc`). Uc yazim duzeltildi, biri bilerek
  eklenmedi. Carpisma 0, imza 11/11.
- **Cayma sinif beyani hatti** (`8bb161d9`). Sozlesme zaten iki sinifliydi ama ayrim BEYANA
  hic gecmemisti: siparis e-postasi kosulsuz "ozel uretim" diyordu, yani stok kaleminde
  musterinin cayma hakkini reddedecek teyit siparis aninda veriliyordu. Dort yuzey sinifa
  gore konusuyor, karisik sepette kalem bazinda. Yeni kapi 29 iddia, once-kirmizi 19/29,
  ozel uretim regresyonu 0/15930. Mutasyon turu olu kod yakaladi (sinif fonksiyonu hic
  cagrilmiyordu).
- **Kesif kapisi on-kosulu: yayin penceresi ayrildi** (`0166ccb3`). Yeni kayit TASLAK giriyor,
  uc yayin bayragini suzuyor; on-kosul bunu "kayip" sayip her partiden sonra ~yarim saat
  BLOKLUYORDU (olculen pencere 29 dk). Hal artik FIILEN okunuyor, sayi farkindan
  turetilmiyor. Gercek kayip ekseninde fail-closed korundu. Mutasyon 14 -> 22, 22/22.
- **Fiziksel fiyat yolunun canli nobetcisi** (`5b754c9d`). Kok sebep "kapsam dar" degil,
  `tur` ekseninin HIC olculmemesiydi. Nobetci "kod kirik" ile "paket bayat"i AYIRIYOR.
  Bugun kirmizi ve hakli. Offline kol CI'da bloklayici; canli kol bilerek baglanmadi.
- **Olcum kanal suzgeci + goc fail-closed** (`8ca71f82`). Goc kostugu an site disi her
  odenmis siparis "olculmemis ciro" alarmi olacakti. Ayrica ALTER gecip indeks duserse
  tek yonlu kapi aciliyordu; artik sema adimi indeks teyidi gecmeden "tamam" demiyor,
  ikiz satirlar SAYILIYOR ama silinmiyor. Once-kirmizi 3/3 + 3/3, mutasyon 11/11.

### ✅ FAZLA TAHSILAT KAPANDI (Okan deploy etti, 17:29)
Canli paket bayatti; 676 fiziksel uruntte %84'e varan fazla tahsilat olculmustu. Deploy
sonrasi yeni nobetci **rc=0**: sapma 0, nesil 0, repo-kirik 0, olculemeyen 0 (deploy oncesi
6 SAPMA + 6 NESIL idi). Ornek urun canli 270000 = liste 270000 kurus. Saglik kapisi rc=0.
Onbellek tuzagi UC bicimde elendi (ciplak uc + iki farkli atlatma damgasi + kapinin tamami
atlatan uctan): uc PoP, `no-store`, ayni sonuc. Odeme ekraninin canli kaynagi da yeni metni
tasiyor (6/6 capa, iki cekimde bayt-ayni).
🔴 **KALICI RISK:** CI'da worker deploy adimi YOK, elle yapiliyor — ayni bayatlik tekrar eder.
⚠️ **Tuzak:** `shop/.wrangler/dry/` altindaki artefakt bir kuru-kosum artigi, yayindaki paket
DEGIL; ona bakip "deploy eski" hukmu verilmesin.
**Olculemeyen tek eksen:** siparis onay e-postasinin gercek govdesi — yan etkisiz yolu yok,
gormek icin dusuk tutarli GERCEK siparis gerekir (Okan kapisi). Uretilen mantik offline rc=0.

### KARARLAR (bu tur)
- Ege kapisinda sirket sesi birinci cogulun da yanmasi KABUL EDILDI: o metin Ege'ye kendi
  bilgisi olarak besleniyor, orada "belirleriz" demek Ege'ye vaat ettirmektir. Kapi
  musteriye gorunen sayfalari okumaz; yasal metinlerde olcum 0.
- Iade kargo bedeli metne YAZILMADI — ticari karar Okan'da; kapi, cevap gelmeden o cumlenin
  yazilmasini kirmizi yakiyor.
- Is bolumu (Okan kurali): is kimin duzlemindeyse o yapar; baskalarini da etkileyen
  degisiklikte karar verici mimar devam eder. Siparis ucunun olcum ekseni kardes mimara
  devredildi, Ege tarafi sahibinde kaldi, sema/odeme/merge bende.

### BEKLIYOR
- Onceki turun acik kalemleri (kardes depo gosterim sapmasi · cron tetikleyici karari ·
  filament fiksturu · nobetci borcu) DEVAM-ARSIV.md'ye tasindi; kapanmadilar.

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
- ✅ O turda acilan "kapi bu sinifa KOR" bulgusu ayni gun KAPANDI — ust bloga bak.
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
- 🔴 **HESAP TASINMASI ACIK — kayit BAYAT DEGILDI, DOGRULANDI.** 23 Tem'deki MAKINE gocu
  bitti; envanterdeki is AYRI: **hesap devirleri** (kod deposu, edge saglayici, calisma
  alani, odeme, mesajlasma, not/CRM, model saglayici). Migration Assistant hesap devretmez.
  Olculdu: mevcut oturumlar hala eski hesapta -> **hic baslamamis.**
  ⚠️ **"19" EKSIK SAYIM:** ozet liste 19 madde ama tablolarda Okan'a atanmis satirlar
  **24 ayri eyleme** iniyor (5'i ozette YOK: worker'larin yeni hesapta yeniden yayini,
  medya alt alan adi baglamasi, baglayici yetkilendirmeleri, hasat platformlarina giris,
  destek talebi takibi). **6'si BLOKLAYICI** — o altisi yapilmadan digerleri olculemez.
  Envanter ve yedek raporu `raporlar/` altinda (gitignore'lu, yedek kapsaminda);
  sha256 ozdesligi ve yedek tazeligi dogrulandi.
- ⚠️ **Goc dogrulayicisi YANLIS ALARM veriyor** (rc=1): gomulu referansi 22 Tem'de alinmis,
  symlink yonunun 30 Tem'de duzeltilmesinden ONCE. Gercek kirmizi 0. Referans tazelenmeli,
  yoksa kirmizi gorup umursamama aliskanligi dogar.
- ⚠️ **Yedekte KAPSAM DISI 2 giris:** biri turetilmis artefakt (dogru), digeri kardes evde
  bir cikti klasoru (53 dosya / 31 MB) — neredeyse ayni adli komsu klasor kapsamda VAR,
  bu YOK. 30 Tem'de bir kez yasanan sessiz kapsam daralmasi sinifi; ayri gorev acildi.
- ✅ KAPANDI (1 Agu): "OKAN: cayma hakki ayrimi + ticari sartlar" kaydi BAYATMIS. Okan
  bildirdi, olculerek dogrulandi: sozlesme ve sayfalar iki sinifi ZATEN ayiriyor, canli
  metinler depoyla bayt-bayt ayni. Eksik olan ayrimin BEYANA gecmesiydi; o da bu tur kapandi.
- OKAN: hesap tasinmasinda elle gereken 19 kalem.
- ✅ KARAR (Okan, 1 Agu): cayma iadesinde geri gonderim kargosu icin sozlesmeye **HICBIR
  CUMLE YAZILMAYACAK.** Sonucu bilincli: yazili olmadigi surece bedel yasal olarak SATICIDA,
  yani bizde. Bu bir eksiklik DEGIL, verilmis karardir — "unutulmus" diye tamamlanmasin.
  Kapi bu cumlenin izinsiz yazilmasini kirmizi yakiyor; koruma YERINDE KALSIN.
- MIMAR KARARI: arama maliyet kapisinin bloklayan serite tasinmasi.
- ISCI VERILMEDI: denetim kapisi rapor kolundaki adaylar (urun verisi duzlemi).
- KARDES MIMAR: vida ailesi PUL-only teslimi, metin temizligi plani.

## TABAN (yeniden olc, ezberleme)
Bu bolume SAYI YAZMA — gun icinde bayatliyor ve bayat sayi yanlis guven veriyor
(bugun olculdu: katalog tek oturumda 16589 -> 16672 hareket etti, elle tutulan agac
listesi de tutmuyordu). Tek dogruluk kaynagi kosulan komut:
- Katalog / D1: `python3 tools/d1-sync.py --durum`
- Calisma alani: `git -C /Users/okan/dev/pruvo worktree list`
- Kapilar: `python3 tools/durum.py`
