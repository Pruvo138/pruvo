# DEVAM (KraL) — 5 Agu 2026

## 🟢 DIRILTME KUSURU KAPANDI — kayit cikarildi + alarmin TEK ATIMLIK sonmesi onarildi

Uc commit: `867c1b0d` (veri) · `a964d385` (kapi kolu) · `08b86c34` (taban). Ucu de push edildi.

- **Kayit CIKARILDI, mesrulastirilmadi.** Feed politikasi gerekcesiyle `c912548f`'te cikarilan
  id, bir toplu ekleme dilimiyle (`841aab67`) geri dirilmis, sonra borc tabanina yazilarak kapi
  susturulmustu. Karar: kayit sakincalidir -> `duzelt.py --sil`, **katalog 20850 -> 20849**,
  gizli kaynak kaydi da temizlendi (yetim birakilmadi). `.diriltme-izin.json` **ACILMADI** —
  muafiyet yazmak onceki karari geri almak olurdu.
- **Parti taramasi (genis pencere):** **1073** id'lik yasak kumeye karsi dirilen = **1**
  (yalnizca bu kayit). Alan gerilemesi (EKSEN 2) = **0**. Kapinin kendini-testi 66/66 rc=0.
- 🔴 **OLCULEN SINIF — alarm TEK ATIMLIKTI.** Kapi diriltme push'unda gercekten kirmizi yandi
  ve deploy atlandi, ama bir SONRAKI push'ta yesile dondu: yasak kume `ever_seen − <taban>`
  ile turuyor, ihlal commit'lendigi an bir sonraki tabana GIRIYOR ve alarm KENDI KENDINE
  SONUYOR. Hunide (yazim oncesi) hicbir katman "bir zamanlar vardi ve cikarildi" kumesine
  bakmiyordu. **Aynadaki tuzak:** tabani daha eskiye cekmek duyarliligi ARTIRMIYOR —
  ekle/sil/geri-ekle dongusunun tamami tabanin sonrasinda kalinca kayit "yeni id" sayiliyor
  ve kapi kor kaliyor (ayni vaka: yakin taban KIRMIZI, uzak taban YESIL).
- **ONARIM (`a964d385`):** pre-commit'e bloklayici `diriltme-kapisi.py --calisma-agaci` kolu.
  `urunler.json` degismediyse tarama kosmuyor ama **gerekce BASILIYOR** (sessiz atlama yok);
  rc=2 OLCULEMEDI yesil sayilmiyor. Kabul **78 iddia rc=0**, sekizi DAVRANISSAL (sentetik
  depoda gercek `git commit` denenip HEAD'in kaymadigi ve id'nin commit'e girmedigi olculuyor,
  beyan degil). Kontrol mutanti yeniden uretilebilir (`--kanca-mutasyon`, 12 iddia):
  iki oldurucu mutant pozitif vakayi yesile dondurdu, kontrol mutanti **dondurmedi**.
  Kanca nobetcileri 47 ve 62 iddia yesil; kanca kablolamasi DEGISMEDI (bayt-esit dogrulandi,
  dokum `DEVAM-ARSIV.md`).
- **YAPISKAN EKSEN OLCULDU ve UYGULANMADI:** terk-edilmis ∩ HEAD = **18.227** id
  (**%87,4** — gecmisteki toplu yeniden-girintileme yuzunden `-U0` diffinde neredeyse her id
  icin `-"id"` satiri var). Esik 20'ydi. Uygulansaydi yayin KALICI dururdu ve 18.227 satirlik
  beyan yazilamazdi. Gerekce olculen sayilarla kapi basligina dusuldu.
- **TABAN BOSALTILDI (`08b86c34`):** 7 kaydin 7'si de kapinin KENDI fonksiyonlariyla olculdu —
  feed'e **hala giriyorlar** (yanlis-negatif degil) ama bloklayici jeton tasimiyorlar, borc
  gercekten odenmis. `kok` **7 -> 0** VE `kok_baslangic` **7 -> 0**, AYNI commit'te.
  🔴 Mandal geride biraksaydik ratchet **7 yeni borca** kadar sessiz kalacakti — bu varsayim
  degil, KARSI-OLGU olarak olculdu: `kok_baslangic`=7 iken 1 yeni borc eklenince uyari
  **URETILMEDI**. Gevseme nobeti: +1 kayitli sentetik tabanda uyari URETILDI, esit sayida
  URETILMEDI. Feed kapisi rc=0, taban/baslangic 0/0, RAPOR katmani birebir DEGISMEDI
  (164/20879).
## 🟢 BACKFILL GORSEL-GATE KALEMLERI KAPANDI — `33ecfa4a` (katalog 20949 -> 20948)

Kardes mimarin bildirdigi 2 kalem gozle olculdu: **1 dogrulandi, 1 curutuldu, 1 YENI kusur cikti.**

- **DOGRULANDI -> SILINDI:** bir motosiklet aparatinda ucuncu-taraf wordmark 4 gorselin 2'sinde,
  biri **gercek baski fotografi** — yani model geometrisinde, basildiginda da orada. "Tasarimcinin
  kendi imzasi" savunmasi olculerek dustu (kaynak metninde **0** isabet, tasarimcinin adiyla
  ortusmuyor, diger 9 modelinde iz yok). Yasak tur -> `duzelt.py --sil`; gizli kaynak kaydi da
  temizlendi (21690 -> 21689). 4 kapi rc=0 (guard · diriltme · feed · mukerrer 20948 tarandi).
- 🔴 **CURUTULDU (iddia yanlis olculmus):** jenerik sanilan bir muzik aleti parcasinda marka
  iddiasi MESRU — kaynagin etiket+aciklamasinda marka **3** isabet; yalnizca kaynagin BASLIGI
  markasiz. **DERS: marka iddiasini basliktan degil, kaynagin etiket+aciklama metninden olc;**
  baslik tek basina yanlis-pozitif uretiyor. Kategori de sapma degil (katalogdaki 74 muzik parcasinin
  45'i ayni kategoride, emsal kayit da orada).
- 🆕 **OLCUM SIRASINDA CIKAN UCUNCU KUSUR -> DUZELTILDI:** ayni kaydin kart kapagi bizim bastigimiz
  parca DEGILDI, ticari bir urunun fotografiydi (parlak, katman izi yok, aksesuarlari takili; ayni
  modelin kendi render'inda govde isaretsiz). Musteriyi yaniltir. Fotograf listeden cikarildi, notr
  render kapak oldu (`gorseller` 2 -> 1); R2'ye HICBIR SEY yuklenmedi, hicbir anahtarin uzerine
  yazilmadi. 🔴 **EKSEN ACIGI: gorsel-gate "logo var mi" diye soruyor ama "bu gorsel BIZIM
  urunumuz mu" diye SORMUYOR.** Parti/backfill hunilerinde olculmeye deger.
- 🟡 **ACIK KALEM (kardes mimarin duzlemi, devredildi):** duzeltilen kayit artik **1 gorselli**
  (3-4 kuralinin altinda), notr render eklenmeli.
- 🟡 **ACIK KALEM (siraya alindi, bu turda ele ALINMADI):** bir denetim aracinin tum-katalog kipi
  rapor degil FIILEN silme uyguluyor (kardes mimar bilmeden 760 kaydi silmis, commit oncesi geri
  onarmis); ayrica yetim SECIM kayitlari R2 kilidine dusuyor. Ikisi de ayri karar konusu.

## CI NOBETI (6 Agu 11:37 turu) — `yayin` tavani KAPANDI, 28 mail Cop'e

- **Mail toplu cekildi, ORNEKLEME YOK:** gelen kutusu tek Apple Event ile alindi, cekilen
  satir sayisi kutu sayisiyla esitlendi. `notifications@github.com` + "Run failed" =
  **36** mail (son 90 dk: **6** · daha eski: **30**).
- **ONARILDI — `yayin` job'i; kok neden TASARLANMIS TAVAN, kusur DEGIL.** Kosum
  `31080098990`: `build`+`deploy`=success, tek kirmizi `yayin`. Log alintisi:
  `TASLAK: 493 · aday: 493` + `ADAY SAYISI TAVANI ASTI: 493 > 300`. Ayni kok neden bir
  onceki kosumu da (`31078248697`) dusurmustu. **Emsale birebir uyuldu; esik BUYUTULMEDI,
  kaynak kod DEGISMEDI:** `yayin-kapisi.py --geriye-doldur` -> **493 kayit**.
- **Bagimsiz teyit (`--durum`, aracin kendi geri-okumasi):** ONCE `20850:20212:638` ->
  SONRA `20850:20705:145`. **YAYIN GECIKMESI 0** · DEGISMEZ IHLALI 0. Kalan 145 taslak
  canli `urunler.json`'da bulunmayan en yeni dilim — tasarim geregi taslak, kirmizi degil.
- **28 mail Cop'e TASINDI** (Cop BOSALTILMADI, kalici silme YOK): yalnizca `gh` ile YESIL
  DOGRULANAN iki alarm koluna ait mailler (ikisi de son iki HEAD'de `success`). Hala
  kirmizi olan `Build & deploy` (3) ve odeme-yolu bayatlik (5) mailleri KUTUDA KALDI.
  Iki bagimsiz tarama birbirini tutuyor: 36 - 28 = **8** kalan.
- 🔴 **ACIK KALEM 1 SURUYOR — su an TEK bloklayici, OKAN KAPISI (yetki):** depo secret'i
  `CLOUDFLARE_ACCOUNT_ID` degeri gecersiz. Bu turda BAGIMSIZ dogrulandi (kosum
  `31083433353` kadans kolu logu): `Could not route to /accounts/***/d1/database, perhaps
  your object identifier is invalid? [code: 7003]`. Etki: D1'e dokunan HER CI adimi —
  kadans kolu, odeme-yolu bayatlik olcumu ve **bundan sonraki `yayin` adimi** —
  `OLCULEMEDI/rc=1`. Kod dogru, **DEGER yanlis**. Nobet secret'a DOKUNMAZ (YASAK liste).
  ⚠️ Bu turun geriye-doldurmasi D1'de DOGRU; ama secret duzelene kadar CI'daki `yayin`
  yine kirmizi yanabilir — artik TAVAN sebebiyle degil, KIMLIK sebebiyle. Ayrimi karistirma.
- ✅ **ACIK KALEM 2 KAPANDI (6 Agu):** `serit-a3` diriltme kapisi kirmizisi — katalogdan
  cikarilmis id geri gelmisti. Kayit tekrar cikarildi ve alarmin sonme sinifi onarildi;
  ayrinti icin yukaridaki "DIRILTME KUSURU KAPANDI" bolumu.

## 🟢 ANLATIM-YUZEY NOBETI KAPANDI — `493b286c` (dal main'e alindi)

- **Kol YESIL:** ilgili is akisi 6 Agu 08:04 kosumunda **success** (5 Agu 21:56'dan beri
  kesintisiz kirmiziydi). Uc adimi da gecti: kendini-test **26/26**, mutasyon bataryasi
  **26/26 TEK KIRMIZI** (Traceback 0), asil kapi **0 isabet / rc=0**.
- **Dusus AYRISTIRILDI (dort kombinasyon, ayni surumlerle):** taban 164/37 dosya ·
  yalniz desen daraltmasi **164 -> 6** (-158) · yalniz kaynak onarimi **164 -> 157** (-7) ·
  birlesik **0**. Yani daraltma gercek bulgulari **elemiyor**: onarilmamis agacta 6 gercek
  isabetin ALTISINI de yakalamaya devam ediyor.
- **Bagimsiz enjeksiyon sondasi:** calisan-kod yuzeyinde HIC gecmeyen sentetik jetonlu satir
  her eksene tek tek enjekte edildi -> **6/6 KIRMIZI**; jetonlari calisan kodda gercekten
  gecen iki kontrol satiri -> **2/2 YESIL** (eleme calisiyor, olu degil). Sonda hedef dosyayi
  degistirmedi (sha256 esit). Ayrintili dokum: `DEVAM-ARSIV.md`.
- **Cakisma tek satirdaydi ve SESSIZ tuzak tasiyordu:** iki taraf da `BEKLENEN_IDDIA_SAYISI=24`
  diyordu ama AYNI 24 degildi (biri 22+2, digeri 22+2 BASKA iddia). Birlesik kapi 26 uretiyor;
  sabit **26**'ya cekildi. Main'in agac-kok ekseni birlesmede korundu.
- **Dalin worktree'sinde 20 kapi rc=0** (ci-kapsam · kisisel-veri 26 ad · ic-rapor-adi ·
  is-akisi · kapi-envanteri 7/7 · gitignore · devam-sinif · kategori 20705 · yasal-sayfa-drift ·
  cerez mutasyonu 27+3 · d1-sync kendini-test 126 · shop kabul 72 iddia · ref-route 50/50 ...).
- **D1 `--durum` uc eksen YESIL:** SAYI 20705 = 20705 · SEMA temiz · ICERIK 20705/20705
  (uyusmaz 0, eksik 0, fazla 0).
- **Parite:** `parite-test.js` **1199 gecti / 0 aciklanamayan**, `parite-ege.js`
  **847 gecti / 0 aciklanamayan**; ikisi de **rc=3 OLCULEMEDI** — sebep KARDES MIMARIN
  493 taslak satiri (`yayinda=0`, sayfa probu tavanini asti). **KIRMIZI DEGIL.**
- 🔴 **ACIK KALEM 1 (OKAN KAPISI, yetki):** depo secret'i `CLOUDFLARE_ACCOUNT_ID` 6 Agu
  07:49'da eklendi ama **degeri gecerli bir hesap tanimlayicisi degil** — bulut API'si
  `object identifier is invalid [code: 7003]` donuyor. Deterministik (iki denemede ayni).
  Etki: D1 uzlastirici kolu + odeme-yolu bayatlik olcumu + yayin adimi **OLCULEMEDI/rc=1**.
  Ayni adimlar 07:13 kosumunda, kaynaktaki duz metin deger ile CALISIYORDU. Kod dogru,
  **deger yanlis**. Cozum: secret'i dogru degerle guncelle.
- 🔴 **ACIK KALEM 2 (BASKA MIMARIN DUZLEMI, dokunulmadi):** diriltme kapisi bu kosumda
  KIRMIZI yandi — `nissan-rogue-...-adaptoru` id'si feed politikasi geregi `c912548f`'te
  katalogdan CIKARILMISTI, `841aab67` ile GERI GELDI. **Merge'in sucu DEGIL:** `urunler.json`
  blob'u merge oncesi/sonrasi **birebir ayni** (`1b5b91a1`). Kapi bugun kirmizi yandi cunku
  merge commit'inin `HEAD^1`'i 103 commit geride ve pencere genisledi; sonraki push'ta pencere
  daralir ve bulgu **tekrar gorunmez olur**. Karar MaCiT/Okan'da.

## 🟢 PARITE REFERANSI TEK KAYNAGA BAGLANDI — `82ab7fea` (site↔uc marka sorgusu)

- **Kusur SITE'de DEGILDI, TESTTEYDI.** `tools/parite-test.js`'in elle kopyalanmis
  `norm/haystack/filtered` uclusu, `8913db28` + uctaki gecis sonrasi BAYAT AYNA'ya donmustu.
  Uc yuzey ayri ayri olculdu (uc `/ara` · index.html'in KENDI yuklemi · eski referans):
  mini **69/69**/1134 · haval **2/2**/600 · rover **9/9**/91 · mercedes **1037/1037**/1041 ·
  seat **90/90**/120 · aksanli citroen **413/413**/69. **(a) ile (b) 7/7 BIREBIR.**
- **Musteri kusuru YOK.** Canli `index.html` satir 1629 `EDGE_KATALOG = true` → arama uca
  gider; yerel/yedek kol da AYNI plandan gecer (`aramaPlani(query)` x4, marka-liste-test
  bunu olcuyor). Uretim kodunda **0 satir** degisiklik.
- **AKSAN ekseni ayri kok DEGIL:** eski referansin `norm()`'u aksanli `e`yi sadelestirmiyordu;
  uc de index.html de kanona indiriyor → onarimdan sonra sapma 0.
- **Onarim:** yeni `tools/index-arama-referansi.js` — index.html'in kanonik bloklarini
  AYIKLAYIP `node:vm`'de CALISTIRIR (ikinci yuklem YAZILMADI). Cip indeksi uretim
  ureticisinden gelir (uydurulmaz; index.html o indeks yokken gevsek davranir, uc davranmaz —
  bos gecilseydi cip evreni markalarinda YENI ayrisma dogardi).
- **Fail-closed, dogru birimde:** referans olcumden ONCE kurulur; index.html yok / capa bozuk /
  uretec yok → **rc=3 (OLCULEMEDI)**, kontrol rc=0.
- **Kapilar:** canli `parite-test.js` **1199/1199 rc=0** (onceki tur 33 ayrisim) · mutasyon
  **25/25** · parite-fikstur **226/0** · yayin-fikstur **140/0** · marka-liste **34/0** ·
  ci-kapsam YESIL · kisisel-veri YESIL.
- **Korelme olculdu ve kapatildi:** onbelleksiz surumde uretici surec-basina ~1 sn → mutasyon
  25/25'ten **9/25**'e dustu (yuk, gerileme degil). Taban degismemis agacta 25/25 olculerek
  suclu bulundu, hipotez `PARITE_CIP_INDEKS` ile kanitlandi, iki girdinin damgasiyla
  anahtarlanan disk onbellegi eklendi → onbelleksiz **25/25, 262,1 sn**.
- **MARKA EKSENI (bagimsiz kanit, dal `worktree-agent-a85a9c2f60dce9910`):**
  taban site **69 marka / 6.539 kalem** + uc **77 marka / 4.613 kalem** ayrisikti;
  bugun IKI yuzeyde de **130 olculdu / 130 gecti / 0 ayrisik / 0 olculemedi (rc=0)**.
  Toplam **11.152 kalem → 0**. (Dalin KENDI bayat kataloguyla 4 marka OLCULEMEDI cikiyordu;
  Honda farki tam **126** = dilim 5 → guncel katalogla dordu de kapandi, veri kusuru DEGIL.)
- **D1:** `--durum` uc eksen YESIL — SAYI 19252 = 19252 · SEMA temiz · ICERIK 19252/19252
  (uyusmaz 0, eksik 0, fazla 0). Parite ciktisindaki `canli=19126` **bayat olcumdu**;
  126 urun D1'e INMIS, senkron kosturmaya gerek olmadi.
- 🔴 **ACIK KALEM (BASKA DEPO, dokunulmadi):** `parite-ege.js` hala **rc=1, 35/848** ve
  sapanlarin TAMAMI marka adi sorgusu (24 marka). Sebep: botta IKI govde var — `/ara` D1 yolu
  kurali benimsedi, bellek-ici arama govdesi benimsemedi (ornek: mercedes uc 1037 ↔ 1509,
  haval 2 ↔ 1359). Karar MIMARIN: o govde de gecsin mi, yoksa "Ege semantigi ayridir" diye mi
  kapatilsin.

## CI NOBETI (01:37 turu) — 🟢 YAYIN ZINCIRI UCTAN UCA YESIL; onceki turun kirmizisi KAPANDI
- **Push kapisi ACIK:** `origin/main` = `81199aee`, bekleyen commit 0. Bir onceki turun
  "push kimlik kapisinda bekliyor" acik kalemi KAPANDI.
- 🟢 **YAYIN ZINCIRI YESIL** — kosum `31050753590` / `81199aee`, job DUZEYINDE olculdu:
  `build`+`serit-a2`+`serit-a3`+`serit-a4`+`serit-b`+**`deploy`**+**`yayin`**+`envanter`+
  `cron-nabzi`+`mesaj-nobeti`+`d1-kadans`=**success** · `hacim-tam-takim`=skipped.
  Onceki turun sinif kapisi kirmizisi (`31046966630` / `14d40f86`, `serit-a2`+`serit-a3`
  failure -> `deploy`/`yayin` skipped) bu kosumda KAPANDI: onarim TUTTU.
  **Bu turda CI'da duzeltilecek YENI kusur cikmadi** — kod DEGISMEDI, merge YAPILMADI.
- Kutu: inbox **7567**, TOPLU cekim (sender/subject/date uc listesinin uzunlugu 7567 =
  `count of messages of inbox` 7567; ORNEKLEME_RISKI=HAYIR). "Run failed" maili:
  son ~70 dk'da **3**, kutuda kalmis eski **25**.
- **9 mail Cop'e TASINDI** (Cop BOSALTILMADI, kalici silme YOK): **8**'i yayin seridine ait
  (1 taze + 7 eski; kolun kendisi HEAD'de yesil OLCULDU) + **1**'i sonraki dort kosumu
  success olculen ayri bir alarm kolunun maili. Atlanan 0, coklu eslesme 0.
- 🔴 **SAPMA ACILDI VE KAPATILDI (papatya yapilmadi):** silme sonrasi ilk sayim
  `TASINAN=9` ama `FARK=8` verdi. Iki rakip hipotez ayri ayri OLCULDU; hukum **birim
  degistirilerek** verildi — toplu sayi degil, **kalem kalem** geri-okuma: 9 mailin
  9'u da `INBOXTA=HAYIR`, kalan "Run failed" maili **19** ve **hepsi** ayni bagimsiz
  alarm koluna ait. Ikinci sayim **7558 = 7567 − 9** ile birebir oturdu; ilk turdaki
  fark gecikmeli sayactan kaynaklandi, eksik silme DEGIL.
- **19 mail KUTUDA KALDI (bilerek):** kural "yesil OLCULMEYEN kosumun maili silinmez";
  bu 19'un kosumu hala kirmizi.
- 🔵 **BAGIMSIZ ALARM KOLU 10/10 ARALIKSIZ KIRMIZI — YENI kusur DEGIL.** Kol `deploy`e
  `needs:` ile bagli DEGIL, yayini bloklamiyor. Mimar karari 23:37 turunda alindi ve
  KAYITLI: kapatilmasi desen daraltmasi degil kaynak temizligi isidir, saatlik nobetin
  "en kucuk duzeltme" kapsamina girmez, ayri pakete alindi. Bu yuzden DUR kosulu
  ISLETILMEDI — ortada kuyruga alinmis bir temizlik borcu var, acik bir CI arizasi yok.

## CI NOBETI (00:37 turu) — 🔴 YAYIN ZINCIRI DURMUSTU: SINIF KAPISI KIRMIZISI ONARILDI (lokalde YESIL), PUSH KIMLIK KAPISINDA
- Kutu: inbox **7566**, TOPLU cekim (taranan 7566 = toplam 7566, ORNEKLEME_RISKI=HAYIR).
  "Run failed" maili: son ~70 dk'da **3**, kutuda kalmis eski **24**. **Hicbir mail Cop'e
  TASINMADI** (bu turda dogrulanmis yesil YOK -> silme YOK).
- 🔴 **GERCEK YAYIN KIRMIZISI (bagimsiz teyit, job duzeyinde):** kosum `31046966630` /
  `14d40f86` -> `build`=success ama **`serit-a2`=failure**, **`serit-a3`=failure**,
  **`deploy`=SKIPPED**, **`yayin`=SKIPPED**. Yani yayin zinciri DURDU. Onceki turun "uctan
  uca yesil" hukmu `061d2918` icindi; **nobetin KENDI commit'i zinciri kirdi.**
- **KOK NEDEN (logdan alintili):** `tools/devam-sinif-kapisi.py`, izlenen kok defteri
  `DEVAM.md`'nin 54/60/71. satirlarini **E6 sinifinda** reddetti ("SINIF IHLALI ... Eslesen
  metin BILEREK yazilmiyor"). `serit-a3` ayni bulgunun kapinin canli-korpus oz-testine
  yansimasi — **fikstur bayat DEGIL, kapi bozuk DEGIL, kusur METINDE.** Kapi DOGRU calisti.
- **ONARIM (en kucuk duzeltme):** uc ihlal satiri notr ozete cevrildi, dokum sinif geregi
  git-disi `DEVAM-ARSIV.md`'ye tasindi. **Kapi betigi DEGISMEDI** (desen daraltilmadi,
  istisna eklenmedi, `continue-on-error` eklenmedi). Lokal kosum: `serit-a2` **rc=0**,
  `serit-a3` **rc=0**.
- 🔴 **PUSH REDDEDILDI — kimlik kapisi:** commit `6afb4642` (yalniz `DEVAM.md`, 24+/29-)
  lokalde hazir, `main...origin/main [ahead 1]`. `git push` -> "could not read Username";
  `gh auth status` -> "The token in default is invalid"; SSH anahtari YOK, credential helper
  osxkeychain'de jeton gecersiz. Yeniden giris OAuth = **OKAN KAPISI**.
- **ACIK KALEM:** push acilana kadar canli yayin `061d2918`'de kaliyor -> `14d40f86`'nin
  getirdigi model sayfasi marka uyeligi yuklemi **YAYINDA DEGIL**.
- **DERS (yeni):** saatlik nobetin KENDI defter yazisi yayin zincirini durdurabilir; alarm
  kolunun adi/bulgu dokumu izlenen deftere yazilamaz — ozet defterde, dokum arsivde.

## CI NOBETI (23:37 turu) — 🟢 YAYIN ZINCIRI TAM YESIL; alarm kolu TASARIM GEREGI kirmizi, iki aday dal da REDDEDILDI
- **Push kapisi ACILDI** (4 turdur kapaliydi): `origin/main` = `061d2918` (23:28). Bekleyen
  commit 0.
- 🟢 **YAYIN ZINCIRI ILK KEZ UCTAN UCA YESIL** — kosum `31044260148` / `061d2918`, job duzeyi
  olculdu: `build`+`serit-a2`+`serit-a3`+`serit-a4`+`serit-b`+**`deploy`**+**`yayin`**+
  `envanter`+`cron-nabzi`+`mesaj-nobeti`+`d1-kadans`=**success** · `hacim-tam-takim`=skipped.
  Onceki turlarin "yayin" ve "gramer" kirmizilari kapandi.
- Kutu: son ~70 dk'da **2** "Run failed" maili (inbox **7566**, TOPLU cekim — taranan 7566 =
  toplam 7566, LISTE_TUTARLI=evet, ORNEKLEME_RISKI=HAYIR). **Ikisi de yalniz alarm koluna ait**
  (`061d291` + `555202a`); yayin seridine ait mail YOK. **Hicbir mail Cop'e TASINMADI**
  (alarm kolu yesil degil -> silme yok; kural: yesil YOKSA silme YOK).
- 🔵 **BAGIMSIZ ALARM KOLU KIRMIZI — BIR CI KUSURU DEGIL, KAPI BOZUK DEGIL** (olculdu,
  varsayilmadi). Kolun kirmizi yanmasi kapi betiginin KENDI govdesinde BEKLENEN olarak
  beyan ediliyor; `deploy`e `needs:` bagi YOK, yayini bloklamiyor. Kol adi, sayilari ve
  dosya dokumu sinif geregi `DEVAM-ARSIV.md`'de.
- 🔴 **IKI ADAY ONARIM DALI DA REDDEDILDI (mimar hukmu).** Ikisi de ayni basligi tasiyordu;
  mukerrer dal main'i GERILETIR diye AYRI tartildi. Ozet gerekce:
  - **(A)** main'e temiz merge oluyor ve kolu sifirliyor, AMA **mutasyon bataryasi KIRMIZI
    (28 sapma)**: kapi 26 iddia uretirken `BEKLENEN_IDDIA_SAYISI` 24'te birakilmis. Merge,
    workflow'un kirmizisini bir adim ONCEYE TASIR, yesil YAPMAZ.
  - **Dort kombinasyonlu olcum:** dususun **%96,3'u desen DARALTMASI**, kaynak temizligi
    DEGIL. Enjeksiyon testi A'nin toptan susturma olmadigini gosterdi, ama **beyan edilmemis
    bir kor nokta olculdu**: elenen isabetlerin buyuk cogunlugu tek bir sinifta ve o sinifin
    GORULEBILIR kaldigini olcen capa YOK.
  - **(B)** A'nin 50 commit daha bayat ikizi: main'e **CAKISIYOR**, **80 commit** bayat,
    dosyalarina main'de **16** commit dokunmus (deploy.yml serit bolumlemesi, d1-sync kaynak
    secimi, D1 kanon kolonlari geri gider) ve kapinin main'de `2d5982e6` ile onarilan `--kok`
    kok eksenini GERI ALIYOR ("yanlis agacta yesil yakma" sessiz-hata sinifi). **Kesin hayir.**
  - Dal adlari, sinif dokumu ve eksen kirilimi `DEVAM-ARSIV.md`'de.
- **KARAR (mimar, 23:37 turunda alindi):** alarm kolunun kirmizisi bir yayin engeli DEGIL,
  bir TEMIZLIK BORCU. Kapatilmasinin dogru yolu deseni daraltmak degil, kaynagi temizlemek +
  daraltma yapilacaksa her daraltilan sinif icin AYRI capa iddiasi yazmak. Bu is hacimlidir,
  saatlik nobetin "en kucuk duzeltme" kapsamina girmez -> ayri paket olarak kuyruga alindi.
  Iki aday dal **merge edilmeyecek**; A'nin daraltma olcumleri (dort kombinasyon +
  enjeksiyon) yeni pakette girdi olarak kullanilir.
- Bu turda: kod DEGISMEDI, merge YAPILMADI, push YAPILMADI, mail SILINMEDI.

## CI NOBETI (22:37 turu) — YAYIN KIRMIZISI BAYAT CIKTI, alarm kolu GERCEK; push hala kapida
- Kutu: son ~70 dk'da **2** "Run failed" maili (inbox 7563, TOPLU cekim — taranan 7563 =
  toplam 7563, ORNEKLEME_RISKI=HAYIR), ikisi de ayni HEAD (`f926e0df`): **1** yayin seridi +
  **1** bagimsiz alarm kolu. **Hicbir mail Cop'e TASINMADI** (yesil yok -> silme yok).
- **Bagimsiz teyit job DUZEYINDE** (kimliksiz REST; `gh` bu turda kimlik kapisinda):
  kosum `31036905871` / `f926e0df` -> `build`+`serit-a2`+`serit-a3`+`serit-a4`+`serit-b`+
  **`deploy`**+`envanter`+`cron-nabzi`+`mesaj-nobeti`+`d1-kadans`=**success** ·
  `hacim-tam-takim`=skipped · tek kirmizi **`yayin`**, adim
  "Atomik yayin: canli 200 dogrulanan taslaklari yayina al".
- 🟢 **O KIRMIZI ARTIK BAYAT — OLCULDU, VARSAYILMADI:** `yayin-kapisi.py --durum` (CI'nin
  kendi salt-okunur komutu) -> toplam **19733 · yayinda 19733 · TASLAK 0**. Aday kumesi
  yalniz taslak satirlardan beslendigi icin **su anki aday sayisi 0**; 21:37 turunun
  `--geriye-doldur`u TUTMUS. Yani bu adim taze bir kosumda gecer, CI'da duzeltilecek yeni
  kusur yok — **var olan yesilin renginin guncellenememesi var** (kosum yeniden
  KOSTURULAMADI: yazma islemleri kapida). Ikinci bagimsiz geri-okuma: `d1-sync --durum`
  uc eksen TEMIZ (SAYI 19733=19733 · SEMA temiz · ICERIK 19733/19733, uyusmaz/eksik/fazla 0).
- 🔴 **BAGIMSIZ ALARM KOLU GERCEK KIRMIZI (bayat DEGIL):** kosum `31036905530` yerelde birebir
  uretildi -> `--kendini-test` **24/24**, mutasyon bataryasi **24/24 tek-kirmizi, taban 0 dusen**,
  asil kapi **rc=1 / 164 ihlal / 37 dosya**. **164 sayisi 12:00 turunun kayitli onarim dalinin
  "164 isabet -> 0" olcumuyle BIREBIR ayni** — yani bu kol icin cozum zaten kuyrukta, YENI
  kusur degil. Dosya/eksen dokumu sinif geregi `DEVAM-ARSIV.md`'de (git disi). Bu kol
  `deploy`/`yayin` zincirinin on kosulu DEGIL.
- 🛑 **DUR KOSULU ISLETILDI (4. ardisik tur):** `origin/main` hala `f926e0df`, yerelde bekleyen
  commit **2** (ikisi de nobet defteri). Push mimar eliyle YENIDEN denendi ve ayni kapida
  dustu; alternatif kimlik yolu da BAGIMSIZ olculdu ve **kapali** (ayrinti sinif geregi
  arsivde). Bu turda kod DEGISMEDI, merge YAPILMADI, mail SILINMEDI.

## CI NOBETI (21:37 turu) — YENI kok neden BULUNDU+ONARILDI (yerelde), push OKAN KAPISINDA
- Kutu: son ~70 dk'da **2** "Run failed" maili (inbox 7560, TOPLU cekim — taranan 7560 =
  toplam 7560, ornekleme YOK; ORNEKLEME_RISKI=HAYIR): **1** yayin seridi + **1** bagimsiz
  alarm kolu, ikisi de ayni HEAD (`c245624`). **Hicbir mail Cop'e TASINMADI** (yesil yok -> silme yok).
- **Kok neden ONCEKI TURLARINKI DEGIL — DEGISTI.** `serit-a2` (onceki 3 turun suclusu)
  bu kosumda **YESIL**; yani DEVAM.md sinif onarimi tuttu. Job duzeyi olculdu, kosum
  `31031776322` / `c2456249`: `build`+`serit-a2`+`serit-a4`+`serit-b`+`envanter`+`cron-nabzi`+
  `mesaj-nobeti`+`d1-kadans`=success · **`serit-a3`=failure** ·
  `hacim-tam-takim`/`deploy`/`yayin`=**skipped**.
- **Adim duzeyinde daraltildi:** `serit-a3`in 69 adiminin 1-57'si success, **adim 58 =
  `Gramer artigi kapisi`** kirmizi, 59+ skipped. Yerelde birebir uretildi: rc=1, **1 ihlal**.
- **KUSUR METINDE DEGIL KAPIDA (mimar hukmu).** Ihlal: `Honda Civic 7., 8. ve 9. nesil ...`
  — bu **kusursuz Turkce** (sira sayisi noktayla yazilir, listede virgul alir).
  `gramer-artigi-kapisi.py`nin `cift-noktalama` deseni `\.\s*,` kolu bunu enkaz saniyordu.
  `urunler.json` MaCiT duzlemi + bu nobetin YASAK listesinde -> metin DEGISTIRILMEDI;
  dogru Turkce'yi bozmak ayni yanlis-pozitifi her gelecek sira sayisinda yeniden dogururdu.
- **Onarim `f926e0df` (TEK dosya, `tools/gramer-artigi-kapisi.py`):** kol `(?<!\d)\.\s*,`e
  daraltildi, diger uc kol AYNEN kaldi. Daraltmadan ONCE kapsam olculdu: kolun canli katalogda
  **toplam 1 isabeti** var ve **1'i rakam-onceli, 0'i harf-onceli** — yani kolun tek atesLEMEsi
  bu yanlis-pozitifti, daraltma gercek enkaz kaybettirmiyor.
- **Kabul (hepsi KOSULDU):** `--kendini-test` **rc=0**, iddia **56 -> 60** · canli katalog
  kosumu **rc=0, 0 ihlal** · degisen dosya **1**. Mesru cumle `_MESRU`ya civilendi (dosyanin
  kendi emsali: gevsetme girisimi oz-testi kirmizi yakar).
- 🔴 **MUTASYON — daraltma ile SILME ayirt edildi (kritik):** `_BOZUK`a harf-onceli gercek
  enkaz vakasi (`A5`) eklendi; onsuz "kolu daralt" ile "kolu tamamen sil" mutantlari
  birbirinden ayirt EDILEMIYORDU. **M1** (kol tamamen silinir) **KIRMIZI**, **M2** (kol eski
  gevsek haline doner) **KIRMIZI**, kontrol yesil. Mutasyon surucusu diskte birakildi
  (anlatilan batarya kanit degil) — kaynak dosya mutasyona ugratilmadi, gecici kopya kullanildi.
- 🔴 **ACIK KALEM — PUSH EDILEMEDI (3. ardisik tur):** `origin/main` hala `c2456249`;
  yerelde bekleyen commit **2** (`96d168d8` baska oturumun urun partisi, katalog 19597 -> 19733
  + `f926e0df` bu onarim). Push mimar eliyle BAGIMSIZ denendi, ayni kapida durdu — sebep
  sinif geregi `DEVAM-ARSIV.md`'de (git disi). **Yayin zinciri bu kapi acilana kadar kirmizi
  kalir**; CI'da duzeltilecek YENI kusur yok, var olan onarimin canliya inememesi var.
- Yedek: onarim commit'i `gramer-sira-sayisi` dal referansinda da duruyor (push inince silinecek).

### 🟢 SONUC — ONARIM CANLIYA INDI, YAYIN ZINCIRI ACILDI
- `f926e0df` origin'e INDI (mimarin kendi push'uyla DEGIL; baska bir oturumun push'u
  tasidi — mimar eliyle push iki kez denendi, ikisinde de ayni kimlik kapisinda dustu).
- **Kosum `31036905871` job duzeyi:** `build`+`serit-a2`+**`serit-a3`**+`serit-a4`+`serit-b`+
  **`deploy`** = **success** · tek kirmizi **`yayin`**. Yani gramer kapisi onarimi TUTTU,
  `serit-a3` geri gelmedi ve **site canliya indi** (deploy 4 turdur ilk kez success).
- **`yayin` kirmizisi YENI kusur DEGIL, bilinen TASARLANMIS TAVAN** (DEVAM.md'de zaten acik
  kalemdi): logdan alinti — `ADAY SAYISI TAVANI ASTI: 408 > 300`. Tahmin dogrulandi:
  19.325 (son yesil yayin) -> 19.733 = **408 aday**.
- **Emsale gore kapatildi, esik BUYUTULMEDI:** `yayin-kapisi.py --geriye-doldur` -> **408 kayit**.
  🔴 Esigi yukseltmek YASAKTI ve yapilmadi; asilan esik VERIYLE kapatildi.
- **Bagimsiz geri-okuma (aracin kendi sayisina guvenilmedi):** `d1-sync.py --durum` uc eksen
  TEMIZ — SAYI 19733/19733 · SEMA temiz · ICERIK 0 uyusmaz. **`yayinda=19733, taslak=0`**
  -> tum katalog Ege'ye de gorunur durumda.
- 🟡 **OLCULEMEDI:** dusen `yayin` job'i YENIDEN KOSULAMADI (kimlik kapisi yazma islemlerini
  de kapatiyor; okuma calisiyor cunku depo public). Bu yuzden kosumun GitHub'daki rengi
  `failure` kaldi, oysa altindaki kosul giderildi. Sonraki push taze kosum uretecek.
- **MAIL SILINMEDI (bilerek):** kural "yeni kosum success OLCULDU" diyor; kosumun rengi
  hala failure. Alt-olcumlerin iyi olmasi belirtilen BIRIMIN yerine gecmez -> 2 mail kutuda kaldi.
- Ikinci bagimsiz alarm kolunun ayrintisi sinif geregi arsive tasindi (silinmedi).

## CI NOBETI (20:37 turu) — DUR kosulu: ayni kok neden, onarim YERELDE, push OKAN KAPISINDA
- Kutu: son ~75 dk'da **2** "Run failed" maili (inbox 7558, TOPLU cekim — taranan 7558 =
  toplam 7558, ornekleme YOK): **1** yayin seridi + **1** bagimsiz alarm kolu.
  **Hicbir mail Cop'e TASINMADI** (yesil yok -> silme yok).
- **Bagimsiz teyit job DUZEYINDE OLCULDU** (18:37'de OLCULEMEDI olan yuzey bu turda geri
  geldi): kosum `31027016757` (Build & deploy, `bf6af02d`) 13 job ->
  `build`=success · `serit-b`/`serit-a4`/`cron-nabzi`/`envanter`/`mesaj-nobeti`/
  `d1-kadans`=success · **`serit-a2`=failure** (adim "Devam sinif kapisi") ·
  **`serit-a3`=failure** (ic nobetci) · `hacim-tam-takim`/`deploy`/`yayin`=**skipped**.
- **KOK NEDEN YENI DEGIL, AYNISI:** `deploy` zincirini durduran sey `bf6af02d`'nin
  tasidigi DEVAM.md sinif ihlali. Onarim (`b943fe40`) **19:37'de yapildi ve lokalde
  duruyor**; `origin/main` hala `bf6af02d`. Yani CI'da duzeltilecek YENI bir kusur yok —
  var olan duzeltmenin canliya inememesi var.
- 🛑 **DUR KOSULU ISLETILDI:** ayni kok neden 3+ ardisik kosumda acik; cozum kod
  degisikligi degil, push yetkisi. Bu turda kod DEGISMEDI, push DENENMEDI
  (`DEGISEN_DOSYALAR=YOK`; sebep + risk gerekcesi sinif geregi `DEVAM-ARSIV.md`'de).
- Lokalde bekleyen commit sirasi: **3** (`b943fe40` onarim + 2 nobet defteri blogu).
- Ikinci alarm kolu (spec/tasarim) DOKUNULMADI — yayin zincirinin on kosulu DEGIL.

## CI NOBETI (19:37 turu) — yayin seridi KIRMIZI, duzeltme YERELDE, push OKAN KAPISINDA
- Kutu: son ~70 dk'da **2** "Run failed" maili (inbox 7558, toplu cekim, ornekleme YOK):
  **1** yayin seridi + **1** bagimsiz alarm kolu. Hicbir mail Cop'e TASINMADI (yesil
  yok -> silme yok).
- **Bagimsiz teyit (kimliksiz REST, HTTP 200):** kosum `31023498467` (Build & deploy,
  `cf075c83`) -> `build`=success, `serit-a2`=failure (adim "Devam sinif kapisi"),
  `serit-a3`=failure (adim "Devam sinif kapisi ic nobetci"), `deploy`=**skipped**,
  `yayin`=**skipped**. Ikinci bagimsiz alarm kolu ayni HEAD'de failure (ayrinti
  sinif geregi DEVAM-ARSIV.md'de, git disi).
- **Kok neden LOKALDE birebir uretildi:** `devam-sinif-kapisi.py` -> DEVAM.md'nin
  KENDI satirinda 1 sinif ihlali (18:37 turunun yazdigi madde). Kapinin yazdigi
  cozum uygulandi: satir arsive TASINDI (silinmedi), yerine notr isaretci birakildi.
- **Kapilar:** `devam-sinif-kapisi.py` rc=0 · `--kendini-test` **63/63 rc=0**.
  Commit `b943fe40` (yalniz DEVAM.md).
- 🔴 **ACIK KALEM:** `b943fe40` **PUSH EDILEMEDI**; `origin/main` hala `bf6af02d`.
  Bu yuzden `deploy`/`yayin` hala skipped ve onarim CANLIYA INMEDI. Sebep sinif
  geregi DEVAM-ARSIV.md'de (git disi). Okan kapisi acilana kadar sonraki nobet
  turleri de push edemez.
- Ikinci alarm kolu (spec/tasarim, ayrinti ARSIVDE) DOKUNULMADI — DUR kosulunda,
  yayin zincirinin on kosulu DEGIL, bu turda kapsam disi.

## CI NOBETI (18:37 turu) — yayin seridi YESIL, 2 mail Cop'e
- Kutu: son ~70 dk'da **5** "Run failed" maili (inbox 7558, toplu cekim, ornekleme YOK).
  Dagilim: **2** yayin seridi + **3** bagimsiz alarm kolu.
- **Yayin seridi (Build & deploy):** `82ab7fea` ve `fac2223b` kosumlarinda `build=success`,
  `serit-a2`/`serit-a3`=failure, `deploy`/`yayin`=**skipped**. Kok neden ikisinde de AYNI ve
  DEVAM.md'nin KENDI satirlarindaki sinif ihlaliydi (kapinin yazdigi cozum: satirlari arsive
  TASI, silme YOK). **Duzeltme zaten `88f111f7` ile inmisti** — bu turda kod DEGISMEDI,
  commit/push YAPILMADI (`DEGISEN_DOSYALAR=YOK`).
- **Bagimsiz teyit (job sorgusu OLCULEMEDI, davranissal kanit YESIL):** canli `pruvo3d.com`
  200 · `sitemap.xml` 200 · canli `urunler.json` **19325** = yerel **19325** · `d1-sync --durum`
  uc eksen YESIL (SAYI 19325=19325 · SEMA temiz · ICERIK 19325/19325, uyusmaz 0/eksik 0/fazla 0).
  19325 katalogu `fac2223b` ile geldi ve o kosumda `deploy` SKIPPED'ti → canlida gorunmesi
  `88f111f7` kosumunun fiilen teslim ettiginin kanitidir.
- Alarm kolu ayri degerlendirildi; ayrinti sinif geregi DEVAM-ARSIV.md'de (git disi).
- **2/2 mail Cop'e** (yalniz "Build & deploy" konulu ikisi; inbox 7558→7556, Cop BOSALTILMADI).
- 🔴 **ACIK KALEM — olcum yuzeyi daraldi:** job-duzeyi `gh run view --json jobs` sorgusu bu turda
  **OLCULEMEDI** (kimliksiz istek → API kota tavani). Hukum canli+D1 davranisindan verildi.
  Arac/kimlik tikanmasinin ayrintisi sinif geregi `DEVAM-ARSIV.md`'de (git disi).

## CI NOBETI (17:37 turu) — kapandi; ayrinti ARSIVDE
- Yayin seridi o turda bagimsiz olculdu ve YESILDI; acik kalan bagimsiz alarm kolu
  yayin zincirinin on kosulu DEGIL.
- Turun tum olcumleri, acik kalemi ve arac/kimlik tikanmasi sinif geregi
  `DEVAM-ARSIV.md`'ye tasindi (silinmedi).

## CI NOBETI (16:37 turu) — kapandi; ayrinti ARSIVDE
- Onceki yayin kirmizisi kendi kendine kapandi: `tools/marka-arama-d1-test.py` HEAD'de 54/54, rc=0.
- Turun geri kalan olcumleri ve acik kalemi sinif geregi `DEVAM-ARSIV.md`'ye tasindi (silinmedi).

## 🟢 IKI DAL MAIN'DE — sozluk `e10a91ce` · cron nabiz esigi `ac533601`
- **Sozluk (4 ad):** on kosul BAGIMSIZ olculdu — sozluk ACIKKEN `uyum-kapisi` **39/0 YESIL**;
  pozitif kontrol: 7 kayit onarimindan ONCEKI veriyle (`16501e39`) ayni sozluk **A1 KIRMIZI 38/1**.
  Sozlugu tuketen kapilar: `altkategori-sinifla-test` 114/0 · `marka-uyelik-test` YESIL ·
  `model-uyelik-kapisi` 21/21. D1 uc eksen 19.126 birebir (merge oncesi ve sonrasi).
- **Cron nabiz esigi:** A0/A3 tavani 9→18 sa GEVSEDI, A4 (zarar ekseni) **9 sa'te KALDI**.
  Mimar tarafinda BAGIMSIZ curutme (dalin fiksturlerinden ayri, 23 iddia / **0 kusur**):
  ayni teslim rejiminde A0/A3=18 · A4=9; paket damgasi 10,0/14,4/17,0 sa bayatken A4 KIRMIZI,
  8,0 sa'te yesil. Teslim 96→0 taramasinda esik 3/6/11/15/18 seyredip A5 tabani altinda **9'a
  GERI DUSUYOR** (kendini susturma yok); 18,4/19/24/30/47 sa sessizlik KIRMIZI (korelme yok).
  Kapinin kendi kosumu 196 iddia/0 kirmizi · mutasyon **29 oldurucu + 6 kontrol, 0 kusur, sapan 0**
  · `ci-kapsam-test` YESIL. `deploy.yml` job grafigine dokunulmadi (kapsam 3 dosya, hepsi `tools/`).
- **Temizlik:** worktree 5→3 (main + korunan 2), iki dal silindi (porcelain temiz + icerik main'de
  + ana agacta yetim is yok). Ortak kutu 285→215 satir, 4 kapanmis blok arsive TASINDI (silinmedi;
  285 satirin 284'u kutuda ya da arsivde birebir dogrulandi, fark yalniz frontmatter damgasi).

**🔴 BU TURDAN ACIK KALEM (benim merge'lerimden DEGIL, olculdu):**
1. `serit-a2` (`marka-arama-d1-test.py`) **KALDI AL3** — `marka_arama` kolonundaki 4 deger kanonik
   marka/alias degil. ⚠️ `50554385` kosumunda **birebir ayni iddia, birebir ayni 4 adla** zaten
   kirmiziydi; sozluk merge'i onu ne acti ne kapatti (AL3 `marka_kanon`/alias tablosundan besleniyor).
   Duzlem: `?q=` gecisi. **Yayin bu yuzden SKIPPED.**
2. 🔴 `serit-a3` (`jenerator/test/vitrin-kabul.js` test 6) **DETERMINIST DEGIL** — degismemis main'de
   15 kosum: **13 yesil / 2 kirmizi**, ayni urunle bir kez 1. bir kez 2. kartta. Kok neden
   `index.html` `VITRIN_SEED = Math.random()`. Kapi `deploy: needs` zincirinde ve `continue-on-error`
   YOK -> rastgele ~%13 ihtimalle TUM ekibin yayinini durduruyor. Tohum sabitlenmeli ya da iddia
   "ilk 4"ten "parametrik on blok"a cekilmeli.

## 🟢 CI NOBETI (12:00 turu) — yayin kosumunun RENGI onarildi, 24 mail Cop'e
- Kutuda 4 Agu 17:00'den beri birikmis **24** "Run failed" maili tarandi (inbox 7565 mesaj,
  toplu cekim, ornekleme YOK). Dagilim: 21 yayin is akisi + 2 D1 sapma alarmi + 1 yayin erisim alarmi.
- **Kok neden yayin arizasi DEGIL:** bloklamayan bir alarm job'i yayin is akisinin ICINDE kosuyor,
  kendi kirmizisini kosum sonucuna tasiyordu; 11 kosum bu yuzden kirmizi gorundu.
- **Onarim (Codex, commit `5945c21e`):** o job deploy.yml'den AYRI bir push is akisina tasindi.
  Komutlari AYNI, fail-closed AYNI, kapi SILINMEDI/gevsetilmedi, `continue-on-error` EKLENMEDI.
  `is-akisi-kapisi.py::SERIT_B` tabani 43→41 (tasinan iki kol dustu).
- **Bagimsiz teyit (mimar eliyle, job duzeyinde):** kosum `30990002466` / sha `5945c21e` →
  `build`+`deploy`+`yayin`+`cron-nabzi` **success**. `D1 sapma alarmi` success (`30990906980`);
  `Yayin erisim alarmi` elle tetiklenip **success** (`30991066350`).
- **24/24 mail Cop'e tasindi** (inbox 7565→7541, Cop BOSALTILMADI); bulunamayan 0, coklu eslesme 0.

**🟡 BU TURDAN ACIK KALEM (mimar karari, dokunulmadi):**
1. Ayrilan alarm is akisi HALA kirmizi (bilinerek; kaynak onarimi ayri dalda, worktree
   `agent-a294bf9bc19a3c740`). ⚠️ Yan etki: her `main` push'unda o is akisi adina **YENI**
   "Run failed" maili gelecek — kutu gurultusu bitmedi, yalnizca yayin kosumundan AYRILDI.
2. **OLCULMEDI:** "bloklamayan job mutanti ana kosumun `conclusion`'ini DEGISTIRMEMELI · yayini
   durduran job mutanti DEGISTIRMELI" cift yonlu kabul testi bu turda kosulmadi. Yapisal kural
   uygulandi ama kendi kabul testi hala YOK.
3. Yeni is akisi dosyasi `is-akisi-kapisi.py` kapsam tablosunda beyanli DEGIL — adimlari sessizce
   silinebilir mi olculmedi (kapsam kapisi ekseni).

## 🔴 5 AGU OTURUM ACILISI — HASAR TARAMASI (kota kesintisi sonrasi)
**Kayip is YOK.** Bes deponun (pruvo · hasat · jenerator · pazarlama · bot) calisma agaci TEMIZ;
dort worktree'nin hicbirinde commit'lenmemis degisiklik yok, ana checkout `origin/main` ile senkron.
`d1-sync --durum` uc eksen YESIL: **18.997** urun, sayi/sema/icerik birebir.

**🔴 GERCEK HASAR — ONARILDI, YAYIN ZINCIRI YESIL: canli 18.550 → 18.997 (447 urun).**

🔴 **ONCE MIMARIN KENDI OKUMA HATASI — DERS BUDUR (`[[hukum-yanlis-birimde]]` birebir tekrari):**
"28 ardisik kosum kirmizi" DOGRU ama bundan **"deploy hic kosmadi"** hukmunu cikarmak YANLISTI.
Job duzeyinde olculdu: o 28 kosumun **14'unde `deploy`+`yayin` YESIL kostu**; kosumlari kirmiziya
boyayan sey **bloklamayan** bir alarm job'iydi (adi + dokum DEVAM-ARSIV.md de, git disi). Yayini fiilen durduran **tek** kosum
sonuncusuydu (`ecc01a25`). Yani hasar "11 saat / ~1.500 urun" DEGIL, **tek commit / 447 urun**.
**Kural: kosum duzeyi sonuc, job duzeyi hukmu VERMEZ — `gh api` ile job'a bak.**

**Kok neden: VERI degil KOD da degil — YARGI BOSLUGU.** Bisect: `f35c421f` agaci 21/21 yesil,
`ecc01a25` 1/21; fark **yalniz `urunler.json`** (+8795 satir, 0 kod satiri). `Ford|raptor` zaten
yayindaydi, son parti `Yamaha|raptor`'u 2→6 urune cikarip esigin ustune tasidi, cift **YARGISIZ**
kaldi (K19). Ford Raptor (kamyonet) ≠ Yamaha Raptor (ATV) — ad cakismasi, emsal
`Ford|sierra`/`Suzuki|sierra`. Hukum: `ROZET_CAPRAZ_IZINLI`'ye 2 gerekceli giris
(`SAYISI` 22→24, `IMZA` hesaplandi). Kapi gevsetmesi YOK, `urunler.json`'a dokunulmadi,
MaCiT'e devir 0 kayit.

**Bagimsiz curutme (uc iddia da dogrulandi):** diff 1 dosya +12/−2, deny tablosu imzasi iki agacta
AYNI · batarya 31 oldurucu + 6 kontrol, beklentiyi tutmayan 0 · capraz kume iki kosumda da
43 cift / 20 model, main'in tek KALDI ekseni `YARGISIZ=[Ford|raptor, Yamaha|raptor]`, dalda `-`
→ **bu 2 giris disinda hicbir ciftin yargisi degismiyor** (olculdu, varsayilmadi).

**Merge + ikinci kilit:** merge `a4bcaf60`; ardindan `serit-a2/a3` **daha erken** bir adimda kirmizi
yandi — `devam-sinif-kapisi.py`, bu dosyanin kendi satirlarinda 2 sinif ihlali (kaynak: mimarin
push edilmemis `6d519e84` notu). Kapinin yazdigi cozum uygulandi (silme yok, arsive tasima),
commit `ca01b743`. 📌 Ders: DEVAM.md'ye yazilan hasar notunun KENDISI yayini durdurabiliyor.

**Canli dogrulama (kosum 30983315565, `--is-ancestor` rc=0):** `deploy` **success** · canli
`urunler.json` canonical + cache-bust'siz **18.997**, 25 rastgele yeni urun sayfasi 25/25 HTTP 200 ·
`d1-sync --durum` uc eksen yesil · **tam parite ana checkout'tan:** `parite-test.js` 1199 sorgu
BIREBIR (cikis 0), `parite-ege.js` 848 sorgu BIREBIR (cikis 0) — merge oncesi ikisi de OLCULEMEDI'ydi.
`yayin` job'i once failure verdi: tasarlanmis tavan (447 > `AZAMI_ADAY=300`); `yayin-kapisi.py
--geriye-doldur` ile kapatildi → `yayinda=18997 · taslak=0`, geri-okuma dogrulandi.

**🟡 ACIK KALEMLER (bu turda DOKUNULMADI, mimar karari):**
1. Bir alarm job'i kirmizi — bloklamayan; job adi + onarim dalinin adi DEVAM-ARSIV.md de (git disi). Onarim dali
   (164 isabet → 0) merge kuyrugunda. Kirmizi kaldigi surece "yayin zinciri kirmizi" sinyali
   gercek yayin arizasindan **ayirt edilemiyor** — bugunku 11 saatlik yanlis okumanin sebebi budur.
2. **`yayin` 300 tavani:** 447'lik parti tekrarlanirsa ayni kirmizi yeniden dogar (MaCiT'e yazildi).
3. `cron-nabzi` kirmizi — `d1-uzlastirici.yml` zamanlanmis teslimi 9,2 saattir yok
   (mevcut "A0 DAMGA" acik kaleminin ayni sinifi, bu merge'le ilgisiz).
4. OLCULEMEDI: `kanca-kablolama-nobeti.py --ci` 18 ekseninin 2'si (16 yesil, 0 kirmizi, cikis 0).
5. Depo hijyeni: 4 worktree → 3 (merge edilen silindi) + 3 push'suz yerel dal, tavan 2.

**OKAN HUKMU (bugun):** (1) hat yesile donene kadar diger mimar oturumlari acilmayacak — **kosul
KARSILANDI, acilabilir**; (2) worktree/dal hijyeni onarimdan SONRA. Ayrica bir hesabin kredisi
07:15'te bitti; oturum acilis sirasi kotaya gore secilecek.

# DEVAM (KraL) — 4 Agu 2026

## 🟠 ACIK KALEM (kanca kablolama dali, agent-aabf841a) — bu turda GENISLETILMEDI
`tools/is-akisi-kapisi.py::SERIT_B` tablosu (is_akisi, job, **betik-yolu**) granulunde
anahtarlaniyor. Yani bir betik SERIT_B'de beyanliysa o betigin GELECEKTEKI TUM bayrakli
cagrilari da sessizce muaf sayilir. Bu dalin getirdigi bir gerileme DEGIL — mevcut tasarim;
`kanca-kablolama-test.py`nin `--mutasyon` kolu da bu yuzden ayrica beyan istemeden gecti.
Gelecek is: SERIT_B'yi (is_akisi, job, betik, **bayrak**) granulune tasimak (bu turda kapsam disi).

## 🔚 OTURUM KAPANISI — 4 Agu · YENI OTURUM ONCE BUNU OKU

### ✅ 5 AGU GECE TURU — CANLIYA GIDENLER
- `f6569d7f` kapi agaci sinifi kapandi — ayrinti DEVAM-ARSIV.md de (git disi).
- `c912548f` yayin kilidi (tek urun) · `d3638a5c` DEVAM budamasi — ikisi de kapandi.

**🔴 SIRADAKI TUR — MERGE KUYRUGU (hepsi dal, hicbiri canlida degil):**
1. **marka aramasi -> uyelik yuklemi** (Okan hukmunun ana kaldiraci): `sayfa != arama`
   **79 marka / 6.507 kalem -> 20 marka / 75 kalem (-%98,8)**, kaybolan urun 0. Merge kapisinda.
   🔴 Capa DINAMIKLESTIRILDI: havuz `srch - sayfa`dan DEGIL **veri iliskisinden** kuruluyor —
   arama kumesinden turese kendini dogrulayan capa olurdu, `srch = set(sayfa)` mutanti havuzu
   da bosaltip kapiyi "olculemedi"ye dusururdu. Bos kume -> rc=2 OLCULEMEDI (M14).
2. **`model_kanon` kolonu** (8.727 urun / 549 deger) — 3 commit: `1) kolon · 2) taban · 3) sozluk`.
   🔴 **MODEL EKSENI MARKADAN FARKLI:** kanon hamin UST KUMESI DEGIL — 1.572 jeton / 5.572 kalem
   kolonda hic gecmiyor, yayimlanan etiketlerde bile "ham eslesiyor kanon eslesmiyor" 16 kova /
   276 kalem. **Uc BIRLESIM kullanmali** (HocA'ya yazildi). Sayfa<->uc farki 96 kova/390 kalem -> 0/0.
   🔴 Commit 3 (sozluk) TEK BASINA MERGE EDILEMEZ: sozluk acilinca 7 kaydin `uyum[].model`'i
   yazim varyanti oluyor -> `uyum-kapisi` A1 KIRMIZI + `urun_hash` bayat -> sonraki senkron o 7
   urunun `uyum`unu D1'de `[]` yapar (Ege uyum bilgisini KAYBEDER). MaCiT'in 7 kayitlik
   duzeltmesiyle AYNI merge'de inecek.
3. **`ege-bilgi.md` tavan payi 27 -> 369** (5 tur curutme). Mayin gercekti: eski pay 27 < en ucuz
   filaman kaleminin 52 birimi, **1 kalem bile tasiriyordu** (KaaN/MaCiT'in isini kirardi).
   🔴 Tur-4 dersi: sikistirma iddia DUSURMEDI ama **iddia EKLEDI** — `cozum DAIMA filament olsun`
   mutlak hukmu, belgenin kendi onayli gomme-somun istisnasiyla (metal) celisiyordu; ikisi de her
   prompta gidiyordu. Denetim tek yonluydu (yalniz kaybolani sayiyordu), cift yonlu yapildi.
4. ACIK KALEM: depo hijyeni ve kapi daraltma — dokum DEVAM-ARSIV.md de (git disi).
5. **Yayin hatti:** bu gece deploy **74 dk durdu** (bir commit inline JS ekleyip `varlik-test.py`i
   kirdi) ve **hicbir alarm atesle­medi** — `deploy-aclik-kapisi` esigi 4 ardisik skipped'e ayarli.
   Ayrica parite esigi bayat: pay 3,0x -> **1,33x**, normal kosulda bile "OLCULEMEDI" uretebilir;
   kritik yol `serit-a3` pencerenin **%93'u**. Ucu birden mühendiste.

**BEKLEYEN KUCUK KALEMLER (bende):** `_isi_yuvasi()` cift-onek korumasi (tek satir) ·
"eklenen jeton gerekce tablosu" **calistirilabilir arac degil**, anlati — bir gun kapiya donerse
ilk fiksturu "hukum ekleyip BICIM diye etiketleme" mutanti olsun · `/marka/bmw/motorrad/` hukmu
(model degil marka KOLU, `PSA`/`VAG` sinifi — kapatilacak) + `Mercedes|A/S/V` (TEK HARF ama
GERCEK model, kapatilmayacak, kanonik gosterime baglanacak) · C kovasi 87 urun · duvar-susu
kapisinin yapisal cozumu (cip evreninden MODEL adi ara).

**CI nobeti:** son tur dokumu DEVAM-ARSIV.md de (git disi).

**BEKLIYOR — baskalarinda:**
- **MaCiT** → metin/alan boslugu 1. PARTI (en buyuk 50 model; kaynak liste kararsiz jetonlar
  cikarilmis 6288 kayit / 4513 urun / 817 cift) + EK PARTI (616 urun, **0 yeni sayfa**).
  Parti bitmeden 2. parti acilmiyor. Ayrica hasat aciklama SABLONU kok nedeni.
- **HocA** → (`ara*` rota kalemi KAPANDI: kutuda kapanis notu, main `c01b70e`, deploy `7830b5f2`;
  kalici kapi `rota-yuzey-nobetci.mjs` kuruldu) · **ACIK:** uc `model` parametresini
  `uyum[].model`'de TAM eslesmeyle suzuyor; 467 cipin 210'unda cip ile ucun teslimi ayrisiyor
  (965 urun-kalemi). Musteriye sayi gosterilmiyor; ucun katlamayi almasi karari onda.
- **KaaN** → `rulman` semasi onarilinca satisa acma karari bende · **ArTisT** → marka-model
  sayfa esigi onerisi.

**OKAN'DA KARAR YOK.** Bugun sorulan uc karar verildi ve uygulandi: asamali git (1. parti 50
model) · Zafira sayfasi 28 hedefi, `Zafira Life` ayri bolumde · yayin hattini KraL acsin.

ACIK KALEM: onceki tur kuyrugu — dokum DEVAM-ARSIV.md de (git disi).

### 🟡 ACIK KALEM 1 — kuyruk geri tepmesi OLCULEMEDI (48 saat sonra yeniden olculecek)
ACIK: ayrinti DEVAM-ARSIV.md de (git disi).

### 🟡 ACIK KALEM — korumanin tasinabilirligi (uc kalem)
(a) Koruma her ortamda ayni sekilde durdurmuyor (durum DEGISMEDI); ayrinti
DEVAM-ARSIV.md de (git disi). Ilgili dosya depoya girmedigi icin dal icinden
kapatilamaz — ayri tur gerekiyor.
(b) Kapi `pre-commit`/`pre-push` icinden cagrildiginda git kendi kancalarini
`GIT_DIR`/`GIT_INDEX_FILE` TANIMLI olarak kosar; yani (a) kapandiginda ortam kirliligi
GERCEK bir yol olur — bu tur tam o yolu kapatti, kayda gecsin.
(c) KAPANDI — ic isci-rapor protokol adina yapilan atiflarin hijyeni: asagidaki
"public depo hijyeni" kalemine bak (merge 20fbff61).

## 🔴 YENI ACIK KALEM — A0 DAMGA alarmi kirmizi: D1 uzlastirici cron'u TESLIM ETMIYOR
ACIK: ayrinti DEVAM-ARSIV.md de (git disi).

## 🔴 YENI ACIK KALEM — katalog geneli metin/alan bosluğu (envanter cikti)
ACIK: ayrinti DEVAM-ARSIV.md de (git disi).

ACIK KALEM: yayin hatti icerik denetimi — dokum DEVAM-ARSIV.md de (git disi).

## 🟡 YENI ACIK KALEM — `CLAUDE.md`/`AGENTS.md` git disi symlink
ACIK KALEM: symlink surumleme ayrintisi — dokum DEVAM-ARSIV.md de (git disi).
