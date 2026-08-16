# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.



## 16 Agu (~19:00Z) — OTURUM KAPANISI (KraL)
**CANLIYA GIDEN:** `cadf9acb` K123 yayin-yasi nobetcisi + mukerrer istisnasi worktree'de · `04b48b36` K113 uretici butunluk kapisi BLOKLAYICI serit + K114 r2-purge (yayin ACILDI: deploy+yayin success) · `b68d9eb7` K124 turetilmis-hal saglik yuklemi (urun partisi artik yayini durdurmuyor; 14'luk parti beyansiz yesil gecti) · `ce5164d2`+`25c5cc34` K39 defter kotasi kancada, 2 evde canli · `5df50d78` K120 gizli kaynak kaydi izlemeden cikti (yokluk kolu: degisen 0, bloklayici 0).
**KOSUYOR:** KraL tarafinda is YOK — tum delege turlari sayisal kabul satiriyla kapandi; worktree 1 (yalniz ana agac).
**BEKLIYOR:** yerel main'de yabanci parti commit'i `2d1d8814` push bekliyor (D1 yazici kilidi UCUSTA, PID 75749 — sira, ariza degil; sahibinin turu itecek) · yabanci ` M tools/marka-uyelik-test.py` DOKUNULMADI · `kurtarma/k122-yabanci-is` dali sahibinde.
🔴 **EKIBE:** gizli kaynak kaydi artik IZLENMIYOR — `git add` EDILMEZ, yerel diskte tutulur.


## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)

- 🔧 **K126 (yeni, 16 Agu, ONCEDEN VARDI — K125 kirmizisi bunu MASKELIYORDU):** `hijyen-a2`
  icindeki **`Marka uyelik kabul testi`** kirmizi: `POZ: /marka/<X>/ urun kumesi = index.html
  marka filtresi` — **sapan marka 65** (Ford 0/3, BMW 0/1, Toyota …; sayfa kumesi bos, filtre
  dolu). Yeni DEGIL: `b68d9eb7` (12:16) · `6865b918` (14:14) · `8117a3a5` (15:26) kosumlarinda
  da AYNI adim kirmizi — yani gun boyu kirmiziydi, 16:12 kosumunda K125'in R2 adimi ondan ONCE
  dustugu icin bu adim HIC KOSMADI ve gorunmedi. **YAYINI BLOKLAMAZ** (`deploy`+`yayin`
  success; hijyen seridi). ⚠️ `tools/marka-uyelik-test.py` uzerinde YABANCI ` M` var ve ayni
  dosya `kurtarma/k122-yabanci-is` dalinda duruyor → sahibi K122 kaleminde; DOKUNULMADI.
  kabul: `python3 tools/marka-uyelik-test.py`
- ✅ **K127 KAPANDI (16 Agu, merge `e5f5c32b`):** rotasyona MADDE GRANULU kol eklendi — acik
  blogun icindeki KAPALI madde artik arsive tasinir, acik maddeye DOKUNULMAZ; cikti
  `TASINAN_MADDE=<n>` (eski `TASINAN=` jetonu korundu). Mimar kod denetimi IKI kusur buldu ve
  ikisi de vaka+mutantla kapatildi: (1) `- KAPANDI (arsivde): ...` **indeks** satiri
  supruluyordu (kayit degil isaretci) → veto + V7/M4; (2) `ACIK` ciplak alt-dize eslesiyordu
  (`ACIKLAMA` blogu sonsuza kadar defterde tutardi — kilitli dongunun ta kendisi) → kelime
  siniri + V8/V9/M5. **OLCUM:** fikstur **15/15**, yeni vaka **9/9**, mutant **5/5**,
  `ci-kapsam` rc=0 (yeni test CI kesfine otomatik girdi), kapsam **yalniz 2 dosya**
  (+690/-49). Gercek defterin KOPYASI uzerinde prova: indeks satiri AYNEN durdu, acik kalem
  **6/6** yerinde. D1 5 eksende temiz (28783=28783). Worktree+dal (yerel+uzak) silindi.
  kabul: `python3 tools/defter-rotasyon-test.py`
- 🔧 **K118:** pre-push sizinti kapisi bicim-kaydiran urun partisinde butceyi yapisal olarak
  asiyor (tam-dosya diff). Yon: butceyi buyutmek DEGIL, `urunler.json`'u icerik ekseninde
  ayri ele almak. `kabul:` alani BOS — kapanmadan once doldurulacak.
- 🟠 **Navlungo dilim-1 MERGE BEKLIYOR:** dal `il-ilce-dilim1` (`5d57c918`). Okan kapisi:
  `.navlungo-kimlik.json` doldurulmasi.
- 🔴 **K104 / K104B:** nobet is akisi sicili + iki kapi main'de de kirmizi (mutasyon
  capalari M06/M31 + iki kapinin kanca kablosu envanterde yok). HUKUM MIMARDA.
- **K99** bag kolonu spec'i · **K100** defter sinifinda satir-sonu muafiyet kusuru ·
  **K102** nobet yazicisi kok deftere yasakli ic dosya adi uretiyor.
- 🔧 **Iki acik kapi kalemi:** (a) shop bayatlik alarminin TETIK ekseni raporladigi bundle
  evreniyle AYNI DEGIL; (b) `devam-sinif-kapisi.py` is-akisi muafiyeti `norm`/`ham`
  ekseninde ayrisiyor.
- 🟠 **K122:** `kurtarma/k122-yabanci-is` dali DURUYOR — peer'in dusurulen commitsiz isi
  (deploy.yml serit tasima · marka-uyelik-test.py · kalibrasyon 4 dosya). Sahibi uygulayacak.
- 🟡 **Kosum sinyali kirli (yeni, olculdu):** `hijyen-a2` + `hijyen-a3` yayin zincirine bagli
  DEGIL ama kosumun genel `conclusion`'ini `failure` yapiyor — "yayin durdu" yanlis hukmu
  doguyor. `is-akisi-kapisi` bunu 5 bulgunun 4'unde soyluyor; cozum joblari `nobet.yml`'e
  tasimak. Bugun iki kez bu yuzden "kirmizi" gorundu, yayin akiyordu.
  🔴 **AMA (16 Agu ~19:30Z olculdu — ters yonlu ders):** "hijyen kirmizisi = gurultu" HUKMU
  KURULAMAZ. Bugunku kosumda `hijyen-a3` gercekten beyan edilmis borctu (is ADINDA yaziyor:
  "M3b acik"), ama `hijyen-a2` **GERCEK ve CANLI bir veri kusuru** buldu (K125, 11 urun bozuk
  gorsel anahtari). Iki kirmizi ayni kosumda, biri gurultu digeri musteriye bozuk gorsel.
  Kural: koşumun genel `conclusion`'ina degil, **is bazinda** bakilir; job tasima isi
  kirmiziyi susturmak DEGIL, yayin hukmunu ayirmak icindir.
- KAPANDI (arsivde): K91 · K101 · K103 · K113 · K114 · K115 · K116 · K117 · K119 · K120 · K123 · K125 · K124.



## OKAN'DA

- 🔧 **TARIFE KARAR KURALI (olculdu, onaya hazir):** mevcut $20 plan KALIR. Haftalik kota %80'e yaklasirsa ikinci saglayicinin $39 basamagi TERCIH EDILIR — ayni para bandinda hem kota hem **ikinci saglayici** (429/kesinti/kota duvarinda yedek) verir; mevcut saglayicinin $50 basamagi yalniz kota verir, tek-saglayici riski surer. Ikinci saglayici bekleme listesindeyse tek uygulanabilir yol $50 (0 kod degisikligi). Ust basamagin iki "deneysel" ozelligi bizim hatta GIRMEZ — biz yalnizca Anthropic-uyumlu API ucundan MODEL cagiriyoruz. Kota sayilari iki adayda da yayimlanmiyor, yani secimi fiyat degil CESITLILIK belirliyor. Ekleme bedeli motor basina 6 kod noktasi.
- Olculen maliyet tabani: $18,72 / 1.081.021.287 token / 8.639 istek = yaklasik $17,3/milyar; $20/ay ve yaklasik 4,6 milyar/ay = yaklasik $4,3/milyar.



## KOSUYOR (baska mimarlar)

MaCiT — Ducati d1 sub-slice 2/3 ve 3/3 (taban artik 27420) + 261 kaynak kaydi dolgusu.



## ARSIVDE (tam metinler `DEVAM-ARSIV.md`'de)

14-15 Agu saatlik CI nobeti turlari · 15 Agu gece oturum kapanisi · K101/K103 kapanislari · yayin ve odeme etiketi bloklari · dorduncu motorun hatta baglanmasi · HD/Kawasaki/Ducati ekleme bloklari · sabah oturumunun tam olcum blogu · defterin sikistirma oncesi 196 satirlik tam hali.