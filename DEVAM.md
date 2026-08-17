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
  tarihli blok" fiksturu + mutant. Hafiza: [[kapinin-recete-ettigi-care-baska-kapida-yasak]].
  kabul: `python3 /Users/okan/dev/pruvo/tools/defter-rotasyon-test.py`
- 🔧 **K135 (yeni, 17 Agu, MaCiT→KraL):** `tools/cgt-ekle.py::fetch()` tek satir UA ile
  CGTrader'in AWS WAF JS-challenge'ina takiliyor (HTTP 202 + ~2KB placeholder); buyuk
  partilerde IP bazli rate-limit devreye giriyor. Dilim-2'de 15 KEEP bu yuzden bloke
  kaldi. Yon: `fetch()`'e retry/backoff + tam Chrome baslik seti
  (`sec-ch-ua`/`sec-fetch-*`/`Accept-Language`/`Referer`). Ayrica
  `tools/arsiv/cgt-ara.py:41` `printables-api.py`'yi `arsiv/` altinda ariyor ama dosya
  ust dizinde — arsivdeki haliyle `FileNotFoundError`.
  🔴 **17 Agu EK (MaCiT'e):** mukerrer kancasi TUM agaci yargiliyor ve **3 mukerrer cift**
  buldu (Yamaha MT-07 fren hazne braketi · RE Hunter 350 hava filtresi kapagi · RE Himalayan
  camurluk yukseltici). Urun benim duzlemim degil; mesru ciftse `.mukerrer-istisna.json`,
  degilse `duzelt.py --sil`. Kalem kapanana kadar KraL'in defter commit'leri kancanin
  belgeli atlama anahtariyla geciyor (urunlere DOKUNMADAN; anahtar adi ARSIVDE).
  `kabul:` alani BOS.
- 🔵 **K136 (17 Agu, KAYIT):** ana agacta `tools/marka-uyelik-test.py` UC oturumdur
  commit'siz duruyor; agac hali K126'nin "tek govde" yuklemini ham dongu olarak GERI ALIYOR
  → commit'lenirse K126 regresyonu. Sahibi belirsiz, DOKUNULMADI. Yon: sahibi cikmazsa
  K133B kapanisinda kanonik hale karsi olculup elenecek. `kabul:` alani BOS.
- 🔵 **K132 (17 Agu, KAYIT — yayini BLOKLAMAZ):** `isci-tur-tavani-test.py` TEK BASINA
  kosumda vaka 1 (`bekci-kesmez-kapanis-yok-rc=0`) KALDI verdi, `testler.py` icinden GECTI.
  Kontrol kosumu (kirli/temiz/kanonik ortam) celiskiyi YENIDEN URETEMEDI; ambient
  `PRUVO_ISCI_*` bulasmasi hipotezi de yapisal olarak curudu (test kendi `temiz_env()`'i ile
  filtreliyor). Muhtemel kok: eszamanli kosumdan kalan bekci sureci — KANITLANMADI.
  Yon: `temiz_env()` ciktisini env-dump olarak bastir. KAT: Claude/Opus. Yasak: vakayi
  yesile boyama · esik gevsetme · env sabitleyerek belirtiyi susturma.
  kabul: `python3 /Users/okan/.claude/cron/isci-tur-tavani-test.py` (rc=0) **VE**
  `python3 /Users/okan/.claude/cron/testler.py` (`HUKUM=GECTI`), ARDISIK 3 kosumda ayni hukum.
- 🔧 **K133 DURUM (17 Agu, dal `kral/k133-uyelik` `dbc49f45` — MERGE TUTULDU):** olcum
  ADIM-1: 533 ciftin **tamami** tek sinif (C: `marka[]` DOLU, eksik jeton orada YOK;
  A=B=D=E=**0**); gurultu riski **4/4 hayir**; 68 jeton = **45 gercek marka + 23 model
  jetonu**. ADIM-2 dali: `d1-sync.py` `marka_kanon` turetimi + kapinin FILTRE modeli
  `mmb.baslik_uyelikleri` cagiriyor (K126'daki TEK GOVDE), 23 model jetonu HARIC.
  Sayilar: `FILTRE_KAYIP 68/533 -> 23/196` · `MODEL_JETON_DEGISTI=hayir` ·
  `parite-test.js` rc=0 (1328 sorgu) · `parite-ege.js` rc=0 (893 sorgu) ·
  `marka-uyelik-test` rc=0 · `ci-kapsam` rc=0 · D1 etkisi **332 satir** · mutant 2/2.
  🔴 **MERGE NEDEN TUTULDU (mimar olctu):** `index.html`'de marka yuklemi **IKI AYRI
  YERDE**: MARKA SORGUSU blogu (`:2814`) `markaUyeMi(...) || baslikMarkalari(...)` —
  baslik kolu VAR; ama **marka CIPI/filtresi uc ayri cagri noktasinda** (`:4043` `:4239`
  `:4389`) hala ham `(p.marka||[]).some(b => markaKatla(b)===hedef)` — baslik kolu YOK.
  Yani dal D1 kolonunu ve kapinin modelini duzeltiyor, **musterinin bastigi cip hala
  urunu kaybediyor**; kapi YESILE donerken belirti CANLIDA kalirdi.
  🔴 **17 Agu — SINIF BIR KAT DAHA DERIN (mimar olctu, onceki "sonraki adim" TEK BASINA
  YETMEZ):** cagri noktasi UC degil **DORT** — `:3574` (`filtered()` `brandOk`) da ham
  `markaUyeMi` kullaniyor; `markaSorgusuEsler` (`:2813`) bugun YALNIZ `:2846`'dan
  (arama plani) cagriliyor. Dahasi iki taraf **FARKLI baslik kurali** kullaniyor:
  `index.html:2788 baslikMarkalari` **UZUN-ONCE** yapiyor (Land Rover bigrami tutunca
  tekil `Rover` URETILMEZ — 5 Agu olcumu: kural olmadan 80 kalem sizar), ama
  `marka_model_build.py:1024 baslik_uyelikleri` (sayfa kovasi FAZ 1B) uzun-once YAPMIYOR
  → sayfa cipten yapisal olarak GENIS. Yani yalnizca cagri noktalarini baglamak kapiyi
  yesile cevirir, `Rover (0/82)` sinifi CANLIDA kalirdi — tuttugum merge'in gercek sebebi.
  **MIMAR HUKMU:** uzun-once her yerde KANONIK (site JS · uretec FAZ 1B · kapi modeli);
  ters yon 80+ urunu yanlis marka sayfasina tasirdi. Kart sozlesmesi olculdu, `baslik`
  HER iki ucta da kartta VAR (`build.py:4284` · pruvo-bot `worker/src/index.js:3944`).
  **UCUSTA:** dal `kral/k133-uyelik` main ile guncellendi (`618fa25f`), worktree
  `.claude/worktrees/k133b`, spec `SPEC-K133B-CIP-TEK-GOVDE.md`, isci `kimi` etiket
  `k133b-cip`. Spec'te DURMA NOKTASI var: uzun-once uygulaninca bir marka sayfasi 0 urune
  duserse isci DURUR, hukmu mimar verir.
  kabul: `python3 tools/marka-invaryant-kapisi.py`
- 🗒️ **K133 OLCUM TABANI (kayit):** kapi 5 kontrol kaldi —
  `MARKA=155 FILTRE_FARK=68/533 ARAMA_FARK=11/118` (`FILTRE_KAYIP=68/533` ·
  `FILTRE_FAZLA=0/0` · `ARAMA_KAYIP=4/105`); ornek `1290` (0/15) · `Rover` (0/82) ·
  `V-Strom` (0/19). ⚠️ Taban BAYAT (`marka evreni 142 -> 155`); `--taban-yaz` borcu
  sifirlamaz CIMENTOLAR — once mesru gecis borcu (veri: `marka[]` eksik urunler → MaCiT)
  ile uretec kusuru ayrilacak. YAYINI BLOKLAMAZ (hijyen seridi).
- KAPANDI (arsivde): K127 rotasyon MADDE GRANULU kol (merge `e5f5c32b`) — 17 Agu rotasyonu.
- 🟡 **K138 (yeni, 17 Agu — K121'den ARTAN iki soru, BaBa'da):** (1) 3 GitHub-disi mailin
  yolu HALA bilinmiyor; kanonik yolda `KOMSU_KAYIP` alarmi oldugu icin tekrarlarsa rc<>0 ile
  GORUNUR olacak — yanarsa ucuncu silici aranacak. (2) 30 dk'lik supurme "once CI yesile
  donsun" on kosulunu ATLIYOR (v2 de atliyordu). Tempo Okan karari. `kabul:` alani BOS.
- 🔧 **K137 (yeni, 17 Agu):** bu makinede **`crontab` YAZIMI asiliyor** — okuma (`crontab -l`)
  calisiyor, `crontab <dosya>` ve `cat | crontab -` surec canli kalarak HIC BITMIYOR
  (sandbox kapali da olsa; `pgrep` ile teyitli, SIGKILL gerekti). Ilk kurulum 03:00'da
  CALISTI, sonrasi kilitlendi → K121 acigi cron satirinda degil BETIKTE kapatildi.
  Yon: `/var/at` kilidi suphesi (root); yazim acilinca `21,51` dogrudan
  `mail-supurme-kos.sh`'e cevrilecek. ⚠️ Tuzak (tekrar yasandi): `crontab <dosya>` dosyayi
  BULAMAZSA stdin'den okur ve SESSIZCE asilir — once `ls`, sonra `crontab -l` ile FARK olc.
  `kabul:` alani BOS.
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
- KAPANDI (arsivde): K91 · K101 · K103 · K113 · K114 · K115 · K116 · K117 · K119 · K120 · K123 · K124 · K125 · K128 (madde olcutu ILK SATIR sartina daraltildi, `6dc1a94e`, fikstur 20/20 mutant 7/7; ders hafizada) · K121 (17 Agu: supurme Okan emriyle acildi, denetlendi, acik KAPATILDI — zamanlanan giris noktasi kanonik `github-mail-cope.applescript` yoluna YONLENDIRILDI; kabul `DERLEME_RC=0 MAIL_ERISIMI=0 KENDINI_TEST_RC=0 KOMSU_ALARM=4 SILINEN_MAIL=0`; olculen acik = v2'nin uc emniyeti YOKTU + `ATLANAN>0` 6 kosumda yani message-id cakismasi gercek; detay posta kutusunda, ders [[korelasyon-mekanizma-teshisi-degildir]]).

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