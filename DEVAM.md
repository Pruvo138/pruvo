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

- **Paket tazelik alarmi** (`b4ee5e03`). Elle deploy edilen paketin bayatligi artik gorunur.
  Zamanlanmis AYRI is akisi; yayini YAPISAL olarak durduramaz (itme tetikleyicisi yok,
  hicbir is ona bagli degil) ve bu uc sart KOSULAN kapiyla olculuyor. Hata-yutma bayragi
  KULLANILMADI. Nabiz iki katli: "kosum yesildi" ile "olcum yapildi" ayri olculuyor.
  Ag/uc yoksa hal OLCULEMEDI = kirmizi. Once-kirmizi fikstürle alindi.
- **Filament kirmizisi + nobetci borcu** (`5e4e90e5`). Test 7/25 veriyordu ve CI'da muaf
  oldugu icin gorunmuyordu; uc fikstür de KONUM tabanliydi ve katalogun basi artik hazir
  malla dolu. Onarim fikstüre yapildi, hicbir iddia gevsetilmedi: **7/25 -> 26/26**
  (merge SONRASI guncel agacta yeniden olculdu, katalog 16814, TEST 26 temiz).
  Borc kapandi: uc eksende KELIME degil BICIM iddiasi (64 iddia). Veri kolonu taramasi
  tum argumanlari gezdigi icin KOLON TAKASINI goremiyordu; artik pozisyon da iddia
  ediliyor. Dokuz mutant KALICI repoda: her kosumda "eski gecirdi / yeni yakaladi" olcer.
- **Gorselsiz hazir urun icin DAR istisna** (`724a69b2`). Muafiyet uc kosul BIRLIKTE
  saglanmadan dogmaz (acik beyan alani + hazir mal sinifi + gercekten hic gorsel yok);
  ornuk cikarim YOK, ozel uretimde bayrak muafiyet VERMEZ, onek kurali durur.
  Her kosumda "gorselsiz kabul edilen: N" basilir (N=0 dahil).
- **Gorselsiz render onarimi + ticari hal kapisi** (`ed135702`). Istisna canliya cikmadan
  once olculdu ve ISTISNAYLA ILGISI OLMAYAN IKI ESKI KUSUR buldu: (1) urun sayfasi kapagi
  gorsel yoksa depoda BULUNMAYAN dosyaya dusuyordu, canli HTTP 404 — ayni 404 sosyal
  onizleme ve yapisal veriye de giriyordu; (2) ilgili urunler kartinda CAPRAZ BULASMA
  (gorselsiz komsu, bulunulan sayfanin kapagiyla ciziliyordu). Ikisi de onarildi; gorsel
  yoksa yapisal veride ilgili anahtar HIC yazilmiyor (kirik adres yerine durust eksiklik).
  Bayrak tek yonlu kapi olmaktan cikti ama SINIF ATLAMASI acik gerekce ISTER ve izlenebilir
  kaydedilir (sinif = fiyat + cayma hakki). Beyan edilmemis ikinci delik de kapandi: tekil
  alan silme yolu izinli kumeye BAKMIYORDU. Regresyon **0 / 16814 sayfa**, mutasyon 15/15.
- **Yedek beyani gercekle hizalandi** (`0d13d4ae`). "Paylasma" uyarisi yalniz bir alt kolda
  basiliyordu, artik kosulsuz; uyari nobetin SINIRINI da soyluyor — eleme AD desenine gore,
  ICERIGE gore degil. Bu bugun isirdi: finansal kimlik tasiyan bir belge ad desenine
  takilmadigi icin kapsama girmisti. Kapsam/mantik DEGISMEDI, test 184/0.

fazla tahsilat kapandi, ayrinti arsivde.

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
  ✅ Envanterin "yedekte YOK" hukmu ve goc dogrulayicisinin yanlis alarmi bu oturumda
  KAPANDI: dogrulayici artik **rc=0**, ev sayisi **4 -> 6** (iki ev hic dogrulanmiyordu),
  yesil 62 -> 80, hic dusmedi. Kayit disi bir kanca da tabloya girdi — commit mesajinda
  tedarikci kimligi gecerse commit'i fail-closed durduran kanca, git ile TASINMIYOR ve
  yeni makinede sessizce duserdi.
  ⚠️ Kalan tek kalinti: eski bir `pre-push` yedegi — siniflandirmasi bende, icerigi acilmadi.

### 🔴 OKAN'DA BEKLEYEN
- **Hesap tasinmasinin 5 bloklayici kalemi** (yukarida) — hicbiri kodla acilamaz.
- **Siparis onay e-postasinin gercek govdesi** hic goruLMEDI: yan etkisiz yolu yok,
  dusuk tutarli GERCEK bir siparis gerekir. Uretilen mantik offline rc=0, ama uctan uca
  "musteriye giden metin" **olculmemistir** — yesil demiyorum.
- ✅ KARAR ALINDI: iade kargo bedeli icin sozlesmeye CUMLE YAZILMAYACAK; sonucu bilincli,
  bedel yasal olarak bizde. Eksiklik DEGIL, karardir — "unutulmus" diye tamamlanmasin.

### KARDES MIMARLARDA
- **HocA:** `wa-siparis-ucu` dali (worktree'si duruyor, DOKUNULMADI). Bagimsiz curutme
  yaptim, **merge DEGIL DUZELTILSIN**: bos dis kimlikte sinirsiz mukerrer siparis
  (olculdu: 4 cagri = 4 siparis) · es zamanli yarista sozlesme yerine 500 · para ekseni
  mutasyona kapali degil (KDV kaymasi 96/96 yesilken KACTI). Uc kapaninca merge + sema
  gocu + deploy sirasi BENDE.
- **ArTisT:** WhatsApp kanalinin GA4 olcum ekseni devredildi; beni bloklamiyor.
- **MaCiT:** gorselsiz parti icin YESIL verildi (`ed135702`); katalogda henuz gorselsiz
  urun YOK, yani ilk parti bu yolun canli ilk kullanicisi olacak.

### KOSUYOR
- Bu oturumun delege ettigi TUM isler kapandi, merge edildi, dal/worktree temizlendi.
  Kalan iki worktree BASKA OTURUMLARIN — dokunulmadi.

## TABAN (yeniden olc, ezberleme)
Bu bolume SAYI YAZMA — gun icinde bayatliyor ve bayat sayi yanlis guven veriyor
(bugun olculdu: katalog tek oturumda 16589 -> 16672 hareket etti, elle tutulan agac
listesi de tutmuyordu). Tek dogruluk kaynagi kosulan komut:
- Katalog / D1: `python3 tools/d1-sync.py --durum`
- Calisma alani: `git -C /Users/okan/dev/pruvo worktree list`
- Kapilar: `python3 tools/durum.py`
