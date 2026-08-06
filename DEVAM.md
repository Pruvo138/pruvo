# DEVAM (KraL) — 6 Agu 2026

## 🔚 OTURUM KAPANISI — 6 Agu · CANLIYA GIDENLER / KOSAN / BEKLEYEN

**CANLIDA (SHA):** model sayfasi uyelik yuklemi `061d2918`+`b00a1f99` (sayfa 576→892, sayfada
gorunen tekil urun 8.839→12.879, `/marka/suzuki/vitara/` **27→66** canli dogrulandi, kaybolan
urun 0 · slug degisen 0) · parite referanslari tek kaynaga `82ab7fea`+`99a2fe3b`+`2819d561`
(site **1199/1199**, uc **847/847**, marka ekseni **142/142 ayrisan 0**; 11.152 kalem → 0) ·
olcek tavani katalogdan turuyor `128d7b34` · cron nabiz esigi canli orandan `ac533601` ·
kapali sozluk + AL3 kabul evreni `e10a91ce`+`c358cb3d` · anlatim yuzeyi kolu `493b286c` ·
**D1 DORDUNCU EKSEN** (turetilmis kolonlar artik sessiz bayatlayamaz) `d23eeb88` · model
kapisi olu giris onarimlari `9654b7c2` · yayin olcegi olcumu `e10ef665`+`482713d1` ·
Volvo Penta veri+taban tek commit `fcf0db57`. Ana repo temiz, `main`=`origin/main`=`ca86d941`.

**KOSAN:** yok — delege edilen tum isler kapandi.

**BEKLEYEN:**
1. Dal `worktree-agent-ab4cf53b74000b09c` **MERGE'E HAZIR, alinmadi**: bloklamayan nobet kollari
   ayri bir is akisina tasindi, kabul **40 iddia · 9 oldurucu · 5 kontrol · sapan 0**,
   `deploy: needs` KUCULMEDI. Alinmama sebebi: yayin kosumu **GitHub'in kendi arizasi** yuzunden
   tamamlanamiyor, canli dogrulama IMKANSIZ. Ariza gecince merge + job duzeyi teyidi.
2. **269 MiB'lik varlik kaldiraci** (her sayfaya inline basilan atif blogu, `build.py:114`) —
   artefakt 827,7 MiB / 1 GB'in %80,8'i; tasima 558,7 MiB'a indirir, kaybolan URL 0.
   Kabul testi repoda hazir (`varlik-test.py` 10 eksen). Muhendis isi, acik.
3. HocA → ADIM 2 (`?model=` uyelik yuklemi); hedefler canlidan tazelenecek (sayfa buyudu).
4. MaCiT → 2 kayit geri cekilecek (hukum kutuda: baskida wordmark + agiz temasli sinif).

**OKAN'DA KARAR YOK.** Secret degeri duzeldi; D1 kollari yesil.

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

## CI NOBETI (6 Agu 11:37 turu) — KAPANDI (yayin tavani + 28 mail); ayrinti DEVAM-ARSIV.md de (git disi).

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

