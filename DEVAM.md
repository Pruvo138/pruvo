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
⚠️ Budama turu bu bolumu de arsive tasidi (lossless, kayip 0 — ayrinti arsivde). ACIK olan
kalem arsive inmez; guncel hal mimar eliyle asagiya yeniden yazildi.

- 🔴 **HESAP TASINMASI ACIK.** 23 Tem'deki MAKINE gocu bitti; envanterdeki is AYRI:
  **hesap devirleri** (kod deposu, edge saglayici, calisma alani, odeme, mesajlasma,
  not/CRM, model saglayici). Migration Assistant hesap devretmez. Olculdu: mevcut
  oturumlar hala eski hesapta -> **hic baslamamis.**
  ⚠️ Ozet listedeki "19" EKSIK SAYIM: tablolardaki atamalar **24 ayri eyleme** iniyor.
  ✅ Bloklayici **6 -> 5**: "yedeksiz gizli dosyalari eski makineden aktar" KAPANDI
  (19 kalemin 19'u da bu makinede; 13'u goc oncesi tarihli, icerik ACILMADI).
  🔴 Yerine gecen risk: iki sigorta paketi (~33 MB) YALNIZ bu makinede. **Karar:**
  paylasilan yedege GIRMEYECEK (temizlik oncesi icerik tasiyorlar) — otomatik yedegin
  degil, tasinmanin **ELLE** kalemidir, sifreli elden gecirilir.
  Envanter + yedek raporu `raporlar/` altinda: gitignore'lu, yedek kapsaminda, sha256
  ozdesligi ve yedek tazeligi dogrulandi.
- ⚠️ **Envanterin kendi "yedekte YOK" hukmu BAYAT** — yedek araci envanterden SONRA
  genisletildi; kardes hafiza uzaylari ve uyelik/fiyat kayitlari Drive'da fiilen VAR.
  Saf sirlarin Drive'da olmamasi BOSLUK DEGIL, sir nobetinin kasitli karari.
  Duzeltme isciye verildi (eski metin silinmeden, "olculdu" notuyla).
- ⚠️ **Goc dogrulayicisi yanlis alarm veriyor** (rc=1): gomulu referansi symlink yonu
  duzeltilmeden onceki hali bekliyor. Gercek kirmizi 0. DAR onarim isciye verildi —
  referans TOPTAN tazelenmeyecek, yoksa bugunku hal "dogru" diye muhurlenir.
- ⚠️ **Yedekte KAPSAM DISI 2 giris:** biri turetilmis artefakt (dogru), digeri kardes evde
  bir cikti klasoru — neredeyse ayni adli komsusu kapsamda VAR. Sessiz kapsam daralmasi
  sinifi; ayri gorev acildi.
- **KARDES MIMAR / OKAN:** onceki turun acik kalemleri (kardes depo gosterim sapmasi ·
  cron tetikleyici karari · filament fiksturu · nobetci borcu) arsivde duruyor;
  son ikisi bu oturumda isciye verildi.

## TABAN (yeniden olc, ezberleme)
Bu bolume SAYI YAZMA — gun icinde bayatliyor ve bayat sayi yanlis guven veriyor
(bugun olculdu: katalog tek oturumda 16589 -> 16672 hareket etti, elle tutulan agac
listesi de tutmuyordu). Tek dogruluk kaynagi kosulan komut:
- Katalog / D1: `python3 tools/d1-sync.py --durum`
- Calisma alani: `git -C /Users/okan/dev/pruvo worktree list`
- Kapilar: `python3 tools/durum.py`
