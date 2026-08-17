# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.



## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)

- 🔧 **K134 (17 Agu — defter rotasyonu SINIF kalemi):** kota kancasinin gosterdigi care
  (`defter-rotasyon.py`) mimar kod kilidinde YASAK; isciye verilince arac `TASINAN=0` dondu
  (tarihli kapanis bloklari govdesinde `BEKLIYOR`/`KOSUYOR`/🔴 tasiyordu → acik-isaretci
  vetosu). **Kok kusur ARACTA DEGIL DEFTERDE:** tarihli blok TARIH olmali, canli durum
  kalem bolumlerinde. Temizlenince rotasyon 5 blok aldi (233 -> 178).
  **Yon:** (a) kancanin `CARE:` metni ROLUN kosabilecegi yolu gostersin, (b) "tarihli
  blokta acik-isaretci jetonu KULLANILMAZ" doktrine gecsin, (c) teste "canli durum tasiyan
  tarihli blok" fiksturu + mutant. [[kapinin-recete-ettigi-care-baska-kapida-yasak]].
  🔴 **17 Agu EK:** rotasyon 2 blok aldi (185→152) ama kota yine kirmizi — kalem bolumu TEK BASINA tavani asiyor; kapanis 7 ardisik elle kisaltma gerektirdi.
  kabul: `python3 /Users/okan/dev/pruvo/tools/defter-rotasyon-test.py`
- 🔧 **K135 (17 Agu, MaCiT→KraL):** `tools/cgt-ekle.py::fetch()` tek satir UA ile CGTrader'in
  AWS WAF JS-challenge'ina takiliyor (HTTP 202 + ~2KB placeholder); buyuk partilerde IP bazli
  rate-limit. Dilim-2'de 15 KEEP bloke kaldi. Yon: `fetch()`'e retry/backoff + tam Chrome
  baslik seti. Ayrica `tools/arsiv/cgt-ara.py:41` `printables-api.py`'yi `arsiv/` altinda
  ariyor ama dosya ust dizinde — arsivdeki haliyle `FileNotFoundError`.
  Mukerrer kanca sinifi K143'e devredildi. `kabul:` alani BOS.
  🔴 **17 Agu EK-2:** arac HALA Codex'e bagimli; MaCiT Ford dilim-3 + Volvo dilim-2'yi her
  seferinde YENIDEN yazilan gecici bir final betigiyle asti (ikisi de silindi). Kalici
  `--yerel` yolu KraL'da; bir sonraki dilim oncesi baglanacak.
- 🔵 **K136 (17 Agu, KAYIT):** ana agacta `tools/marka-uyelik-test.py` DORT oturumdur
  commit'siz; agac hali K126'nin "tek govde" yuklemini ham donguye GERI ALIYOR
  (commit'lenirse K126 regresyonu). Sahibi belirsiz, DOKUNULMADI.
- 🔵 **K132 (17 Agu, KAYIT — yayini BLOKLAMAZ):** `isci-tur-tavani-test.py` TEK BASINA
  kosumda vaka 1 KALDI verdi, `testler.py` icinden GECTI; kontrol kosumu celiskiyi YENIDEN
  URETEMEDI. Muhtemel kok: eszamanli kosumdan kalan bekci sureci — KANITLANMADI.
  Yon: `temiz_env()` env-dump. KAT: Claude/Opus. Yasak: yesile boyama · esik gevsetme.
  kabul: `python3 /Users/okan/.claude/cron/isci-tur-tavani-test.py` (rc=0) **VE**
  `python3 /Users/okan/.claude/cron/testler.py` (`HUKUM=GECTI`), ARDISIK 3 kosumda ayni hukum.
- 🟠 **K139 (17 Agu, Okan emri — CANLI DURUM DEGISIKLIGI, ekip bilmeli):** crontab'tan UC
  zamanli gorev kaldirildi (satirlar silinmedi, yorumlandi): posta kutusu izleyicileri
  (MaCiT + TeKiN, 144 tur/gun) ve **MaCiT parti surucusu** (12 tur/gun). Canli teyit
  `crontab -l` = **2 aktif** (ci-nobeti + kota-olcum), 181 -> **25 atesleme/gun**.
  🔴 ETKI: posta kutusu OTOMATIK izlenmiyor (oturum basinda ELLE okunacak) ve **urun
  partileri kendiliginden ILERLEMIYOR**. Ders: kota keserken EN COK YAKANI olc — 16 Agu
  kesintisi 144 turluk izleyici ciftine hic dokunmamisti. `kabul:` alani BOS.
- 🟠 **K144 (17 Agu — UCUSTAKI KOSUM, sonraki turun ILK isi):** `c5225016` (K133 merge'i)
  CI kosumu ucusta birakildi; push seridinin iki nabzi success, `build`+nobet seridi pending.
  [[ucustaki-kosum-yesil-degildir]] — yesil DENMEDI. kabul: `gh -R Pruvo138/pruvo run list`
  ile `c5225016`'yi ICEREN kosum `conclusion=success` **VE** canonical URL'den cache-bust'SIZ
  canli teyit (marka cipi genisledi mi).
- 🔴 **K143 (17 Agu — UCUNCU TEKRAR, tekil yama YASAK → sinif kalemi):** mukerrer kancasi
  ayni gerekce ile **bu oturumda 3 kez** commit'imi engelledi (RE Himalayan camurluk)
  ve MaCiT de ayni gerekceyle Ford dilim-3 + Volvo dilim-2'de belgeli atlama yolunu
  kullandi. **Yani kapi fiilen DEVRE DISI — herkes atliyor.** Iki katmanli kok kusur:
  (a) bu cift **MIMARCA DOGRULANMIS MESRU** (farkli tasarimci — kutuda yazili) ama
  `.mukerrer-istisna.json`'a HIC islenmemis, yani dogrulama hicbir yere COKMEMIS;
  (b) kanca **stage disi TUM agaci** yargiliyor — `DEVAM.md` commit'inin urunle ilgisi yok
  ([[kanca-stage-disi-agaci-tarar]]). Yon: dogrulanmis cift istisnaya YAZILIR + kanca
  kapsami **stage'lenmis** degisiklige daraltilir. KAT: Claude/Opus (yargi + kapi kodu).
  kabul: atlama yolu KULLANILMADAN `git commit -- DEVAM.md` rc=0 **VE** gercek bir
  mukerrer ciftte kanca HALA rc=1 (mutant: istisnayi genisletip gercek mukerreri kacirma).
- 🔧 **K140 (17 Agu — K133'un KALAN kuyrugu, YAYINI BLOKLAMAZ):** `marka-invaryant-kapisi.py`
  hala 5 kontrol kirmizi (`FILTRE_KAYIP=23/197` · `ARAMA_KAYIP=4/105`). Olculdu: kalan kayip
  jetonlarin **7/8'i MARKA DEGIL MODEL jetonu** (`1290` `690` `Ciao` `DL650` `MT-07` `MT-09`
  `V-Strom`; yalniz `Rover` gercek marka). Dal bunlari BILEREK haric tuttu
  (`marka_kanon_haritasi` `_hedef_markalar` yalniz `marka_only>0`).
  **Acik soru MIMARDA:** model jetonu icin `/marka/<jeton>/` sayfasi beklemek kapinin MODEL
  hatasi mi, uretec mi eksik? Once bu ayrim. ⚠️ Taban BAYAT (`142 -> 155`).
  kabul: `python3 tools/marka-invaryant-kapisi.py` (rc=0) **VE** hukum notunda hangi
  sinifin secildigi YAZILI.
- 🔴 **K141 (17 Agu — OLCULEMEYEN NOBET, sinif kalemi):** `tools/kapi-envanteri.py` main'de
  DE kirmizi (`rc=1`): `mimar-icra-kapisi` ve `mimar-kod-kilidi` icin
  **"NOBETTE degil — reddetmesi gerekeni REDDETMEDI"**. Sebep yapisal: bu iki kapinin
  nobet testi **isci turunda** kosuyor ve kapilarin isci/agent muafiyet kolu "reddetmeli"
  vakasini gecirmiyor; mimar ise ayni komutu KENDI kosamaz (kapi mimarin Bash'ini
  reddediyor). Yani **iki mimar kapisinin
  canliligi hicbir yerden olculemiyor** — [[makineyi-olctuk-urunu-olcmedik]] ile ayni aile,
  [[parite-testi-olculemedi-basiyor]] ile ayni mekanik. Yon: nobet vakasi muafiyet kolundan
  BAGIMSIZ bir altsurecte kosmali (muafiyeti taklit etmeyen temiz ortam).
  `kabul:` alani BOS — kapanmadan once doldurulacak.
- 🔧 **K142 (17 Agu, KraL olctu → MaCiT):** pre-push kapak taramasi **14 R2 anahtari
  `NoSuchKey`** buldu, hepsi `c3d*` onekli (Cults3D partisi). Canlida 404 veren URUN
  KAPAKLARI — K125 ile AYNI SINIF ([[gorsel-anahtar-cakismasi]]). Tam liste push logunda,
  kutuya yazildi. Sahibi veri seridi. `kabul:` alani BOS.
- ✅ **K133 KAPANDI** (`42e28cf7` merge, `c5225016` push): marka cipi ile marka sayfasi tek
  govdeden (`markaSorgusuEsler`) turuyor; FILTRE farki `68/535` iken `23/197`, ARAMA farki
  `11/118` iken `4/105`; degisikligi olcen canli JS testi + mutasyon bataryasi (11/11, 5/5)
  CI'a baglandi. Tam gerekce, tutma karari ve iki curutme turunun sayilari ARSIVDE
  (17 Agu 09:5x blogu). Kalan kuyruk K140, ucustaki kosum K144.
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
- 🟡 **Kosum sinyali kirli (olculdu):** `hijyen-a2` + `hijyen-a3` yayin zincirine bagli DEGIL
  ama kosumun genel `conclusion`'ini `failure` yapiyor → "yayin durdu" yanlis hukmu. Cozum:
  joblari `nobet.yml`'e tasimak. 🔴 AMA "hijyen kirmizisi = gurultu" HUKMU KURULAMAZ:
  16 Agu kosumunda `hijyen-a3` beyan edilmis borctu, `hijyen-a2` ise GERCEK canli veri
  kusuru buldu (K125, 11 urun bozuk gorsel anahtari). Kural: genel `conclusion`'a degil
  **is bazinda** bakilir; job tasima kirmiziyi susturmak degil yayin hukmunu ayirmak icin.
- KAPANDI (arsivde): K91 · K101 · K103 · K113 · K114 · K115 · K116 · K117 · K119 · K120 · K123 · K124 · K125 · K128 (madde olcutu ILK SATIR sartina daraltildi, `6dc1a94e`, fikstur 20/20 mutant 7/7; ders hafizada) · K121 (17 Agu: supurme Okan emriyle acildi, denetlendi, acik KAPATILDI — zamanlanan giris noktasi kanonik `github-mail-cope.applescript` yoluna YONLENDIRILDI; kabul `DERLEME_RC=0 MAIL_ERISIMI=0 KENDINI_TEST_RC=0 KOMSU_ALARM=4 SILINEN_MAIL=0`; olculen acik = v2'nin uc emniyeti YOKTU + `ATLANAN>0` 6 kosumda yani message-id cakismasi gercek; detay posta kutusunda, ders [[korelasyon-mekanizma-teshisi-degildir]]) · K127 rotasyon madde granulu kol (`e5f5c32b`) · **K138** (mail ARIZA SINYALI degildi — nobet metni "maile guvenme" diyor, olcum `gh run list`; Okan GitHub bildirimini kapatti, crontab satiri KALDIRILDI **ve** nobet gorev metnindeki supurme adimlari §0.4+§1+§4 EMEKLI isaretlendi — yalniz crontab'i kaldirmak silme yolunu AJAN elinde canli birakirdi; otomatik mail silicisi KALMADI, bundan sonra mail kaybolursa sebep KESINLIKLE ucuncu bir yol; geri acma OKAN KAPISI, ikisi AYNI turda) · **K137** (birkac saat `crontab` YAZIMI asildi — okuma calisiyordu, asili surec `pgrep` ile teyitli, SIGKILL gerekti; 11:00 civari acildi. Tuzak: `crontab <dosya>` dosyayi BULAMAZSA stdin'den okur ve SESSIZCE asilir — once `ls`, sonra `crontab -l` ile FARK olc).



## OKAN'DA

- 🔧 Eski yedek klasorunu backup-v2 icine tasima · K89 olcum eylemi silme karari.
  (16 Agu: rotasyon bu maddeyi bir kez arsive supurdu — parantezdeki kapali kalem atfi
  yuzunden; geri konuldu, sinif kusuru K128.)
- 🔧 **TARIFE KARAR KURALI (olculdu, onaya hazir):** mevcut $20 plan KALIR. Haftalik kota %80'e yaklasirsa ikinci saglayicinin $39 basamagi TERCIH EDILIR — ayni para bandinda hem kota hem **ikinci saglayici** (429/kesinti/kota duvarinda yedek) verir; mevcut saglayicinin $50 basamagi yalniz kota verir, tek-saglayici riski surer. Ikinci saglayici bekleme listesindeyse tek uygulanabilir yol $50 (0 kod degisikligi). Ust basamagin iki "deneysel" ozelligi bizim hatta GIRMEZ — biz yalnizca Anthropic-uyumlu API ucundan MODEL cagiriyoruz. Kota sayilari iki adayda da yayimlanmiyor, yani secimi fiyat degil CESITLILIK belirliyor. Ekleme bedeli motor basina 6 kod noktasi.
- Olculen maliyet tabani: $18,72 / 1.081.021.287 token / 8.639 istek = yaklasik $17,3/milyar; $20/ay ve yaklasik 4,6 milyar/ay = yaklasik $4,3/milyar.



## KOSUYOR (baska mimarlar)

MaCiT — Ducati d1 sub-slice 2/3 ve 3/3 (taban artik 27420) + 261 kaynak kaydi dolgusu.



## ARSIVDE (tam metinler `DEVAM-ARSIV.md`'de)

14-15 Agu saatlik CI nobeti turlari · 15 Agu gece oturum kapanisi · K101/K103 kapanislari · yayin ve odeme etiketi bloklari · dorduncu motorun hatta baglanmasi · HD/Kawasaki/Ducati ekleme bloklari · sabah oturumunun tam olcum blogu · defterin sikistirma oncesi 196 satirlik tam hali.