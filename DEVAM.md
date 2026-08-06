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

## Saatlik CI nobeti — 6 Agu 15:37Z turu (YARIM KAPANDI, sonraki tur DEVRALSIN)
- **Mail supurmesi (kosulsuz, Okan emri) TAMAM:** birlesik `inbox`ta `notifications@github.com`
  + "Run failed" = **5** mail, **5**'i Cop'e tasindi, tur sonu kalan **0** (bagimsiz ikinci
  sayimla dogrulandi). Cop BOSALTILMADI.
- **CI kirmizisi — kok neden DEPO DEGIL, GitHub altyapisi.** Kosum `31115417788`
  (headSha `e10ef665`) `build` job'u tek adimda dustu: "Set up job". Ham job logu alintisi:
  `Failed to resolve action download info. Error: Internal Server Error` / `Service
  Unavailable`. Duzeltilecek kaynak kod YOK → dogru onarim yeniden kosum. DEGISEN DOSYA: YOK.
- **Codex kotasi DOLU** ("You've hit your usage limit", 8 Agu 10:19'a kadar) → is Claude
  iscisine dustu; isci `sleep` dongusunde ucu ucuna kapanmadi, olcumu mimar `gh` ile aldi.
- **Tikanma olculdu — `concurrency: group: pages, cancel-in-progress: false`** (deploy.yml:33).
  `31115417788` hala `in_progress` (yalniz `serit-a4` kosuyor) → sonraki tum build/deploy
  kosumlari KUYRUKTA. `serit-a4` HUNG DEGIL: onceki basarili kosumda suresi 13:46:40→14:34:35
  = ~48 dk; bu tur 15:21:24'te basladi, ~16:09'da bitmesi beklenir.
- **Tetiklenen temiz kosum: `31117484955`** (`workflow_dispatch`, headSha `482713d1`).
  Tur sonunda hala `pending` (kuyrukta) → **build/deploy/yayin OLCULEMEDI** (yesil DEGIL).
  ➡️ SONRAKI TURUN ILK ISI: `gh run view 31117484955 --repo Pruvo138/pruvo --json jobs` ile
  `build`/`deploy`/`yayin` conclusion'ini olc; kirmiziysa `--log-failed` ile kok nedeni alintila.
- **Izlenecek AYRI sinif:** kosum `31107527748` `deploy` job'u
  `##[error]Timeout reached, aborting!` (GitHub Pages yayin adimi, 13:46→14:57). Bu turda
  KOD DEGISTIRILMEDI. Ayni sinif bir kez daha duserse `deploy-pages` timeout parametresi
  degerlendirilir; ucuncu tekrarda DUR kosulu isler.
- DUR kosulu bu turda ISLEMEDI (ayni kok neden 3 kosum ust uste tekrarlamadi). Okan'a cikilmadi.

