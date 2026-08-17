# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)

- 🔧 **K134 (defter kotasi SINIF kalemi; BaBa 3. kez kirmizi dedi, SPEC HAZIR):** care
  (`defter-rotasyon.py`) mimar kod kilidinde YASAK. 🔴 Kota bu oturumda **YEDI kez** elle
  indirildi — ceza yazma aninda degil **COMMIT aninda** odeniyor. Kok: kanca **INDEX**,
  BaBa **CALISMA AGACI** olcuyor ([[hukum-yanlis-birimde]]) → kanca "yesil" derken diskte
  140 satir olabiliyor. Yon: `CARE:` metni 1:1 tasimayi gostersin + calisma-agaci kolu
  UYARI olsun. Spec: `SPEC-defter-kota-1e1.md` (5 vaka + 4 mutant).
  kabul: `python3 /Users/okan/dev/pruvo/tools/defter-rotasyon-test.py`
- 🔧 **K135 (17 Agu, MaCiT→KraL):** `cgt-ekle.py::fetch()` tek satir UA ile CGTrader WAF'ina
  takiliyor (HTTP 202 + placeholder); yon: retry/backoff + tam Chrome baslik seti. Ayrica
  `tools/arsiv/cgt-ara.py:41` yanlis dizinde ariyor → `FileNotFoundError`.
  🔴 **EK-2:** arac HALA Codex'e bagimli; MaCiT her dilimde YENIDEN gecici betik yaziyor.
  Kalici `--yerel` yolu KraL'da, sonraki dilim oncesi. `kabul:` alani BOS.
- 🔵 **K136 (17 Agu, KAYIT):** ana agacta `tools/marka-uyelik-test.py` DORT oturumdur
  commit'siz (K126 "tek govde" yuklemini ham donguye geri aliyor). DOKUNULMADI.
- 🔵 **K132 (17 Agu, KAYIT — yayini BLOKLAMAZ):** `isci-tur-tavani-test.py` tek basina
  KALDI, `testler.py` icinden GECTI; celiski uretilemedi. Tam metin + kabul ARSIVDE.
- 🟠 **K139 (17 Agu, Okan emri — CANLI DURUM, ekip bilmeli):** crontab'ta 3 gorev
  yorumlandi; 181 → **25 atesleme/gun**. 🔴 ETKI: posta kutusu OTOMATIK izlenmiyor **ve
  urun partileri kendiliginden ILERLEMIYOR**. Tam metin ARSIVDE. `kabul:` alani BOS.
- 🔴 **K150 (UZLASTIRICI YANLIS SINIFLANDIRIYOR; ② ICIN BLOKER):** kosum `32026332006`
  KIRMIZI: senkron **tasarim geregi ATLANDI** (`SEBEP=YAZICI_UCUSTA`), surucu bunu
  **"GERCEK HATA, YENIDEN DENENMEZ"** ilan etti. Ayni `rc=4` `deploy.yml`'de **0**,
  uzlastiricida **1**; surucu yalniz IKI imza taniyor, tanimadigini GERCEK HATA'ya dusuruyor.
  Spec: `SPEC-k150-uzlastirici-rc4.md` (rc=5 ERTELENDI + RETRY + kapsam kapisi).
  kabul: `python3 /Users/okan/dev/pruvo/tools/uzlastirici-onarim.py --kendini-test`
- 🟠 **K144 (UCUSTAKI KOSUM):** ardarda push'lar build'i `cancelled` ediyor (ARIZA DEGIL);
  hukum her turda guncel uca tasiniyor. Tam metin ARSIVDE.
  kabul: guncel ucu ICEREN kosum `conclusion=success` **VE** cache-bust'SIZ canli teyit.
- 🔧 **K140 (17 Agu — ACIK SORU MIMARCA KAPATILDI, icra kaldi):** hukum **kapinin MODEL
  hatasi degil, EVREN KAYNAGI hatasi**: 185 urunun 184'unde model jetonu gercek markanin
  YANINDA, ve `index.html:3148` cip evreni KURATORLU (model kodu CIP OLMAZ) → kapi sitede
  OLMAYAN bir baglanti icin sayfa istiyor. `Rover` ise GERCEK kayip (2 urun).
  Spec: `SPEC-k140-marka-evreni.md`. 🔴 Hedef rc=0 DEGIL **dogru kirmizi**: `Rover` KALMALI.
  kabul: `python3 tools/marka-invaryant-kapisi.py` — 7 model jetonu DUSMUS **VE** `Rover`
  DURUYOR **VE** mutasyon 4/4.
- ✅ **K153 KAPANDI (17 Agu, `5050fbed` push):** mid-array INSERT ikili bolme yapiyordu,
  `taban=atanan` ile boslugu USTEL tuketiyordu (`SEQ_ADIM=1e6` bir boslukta ~20 ardisik
  ekleme kaldirir, parti 26 idi). Care: `kuyruk_blok` kolunun blok-oranli adimi mid-array
  koluna GENELLENDI (`adim=(yuksek-alt)//(k+1)`, alt blogun ILK uyesinde SABIT) + fail-loud
  mesaji normalize plani BOSSA ayri kola ayrildi (eski metin kullaniciyi donguye sokuyordu:
  MaCiT 1, KraL 5 kez). Olcum IKI BAGIMSIZ turda uyustu: `TEST_RC=0 GECEN=10 KALAN=0 ·
  MUTANT=4/4 KONTROL=YESIL · CI_ADIM=VAR`; ayrica elle iki mutant (blok kolunu geri alma,
  `adim<1` gevsetme) testi KIRMIZI yakti → test gercekten olcuyor.
  **CANLI SONUC:** push gecti (bes denemedir duvardaydi), D1 **28980 → 29012**, bes eksen
  de yesil (SAYI 29012=29012 · SEQ tam-sayi-olmayan=0 sapan=0 · SEMA · TURETILMIS 5/5
  GUNCEL · ICERIK hash uyusmaz=0). Peugeot 26 + Chevrolet 6 artik Ege'de GORUNUYOR.
- ✅ **K147 KAPANDI** (sayac 63 → 65, DUSMEDI) → karar ②'ye gecti, devami K148. ARSIVDE.
- 🟠 **K148 (GOZCU FAZ-1 KOSTU ve BAGIMSIZ DOGRULANDI; faz-2 + canliya baglama kaldi):**
  uc dosya `~/.claude/cron/` altinda, **repo ayak izi SIFIR**; tetik gozcude, icra AYNEN
  `nobet-kapi.py`'de. Bagimsiz olcum (ayri isci): `GECEN=63/63` · `MUTANT=10/10
  KONTROL=YESIL` · kuru tur `TETIK=DEFTER_DAGITIM LLM_TURU=0` · `YAN_ETKI=HAYIR`.
  🔴 **FAZ-2 (mimar denetiminde; testler goremedi, SPEC eksikti):** F1 `_kilit_al` O_EXCL
  DEGIL · F2 `_kilit_birak` sahiplik denetimsiz · F3 esik IKIZ.
  Spec: `SPEC-gozcu-kilit-onarimi.md`. Sahipsiz — bos bir oturuma verilecek.
  kabul: `python3 /Users/okan/.claude/cron/gozcu-test.py` (rc=0) **VE** `MUTANT=13/13`.
- 🔧 **K149 (DOSYA KOLU KAPANDI, URETEN-KOLU ACIK):** `~/.claude/cron/` **2495 → 576
  girdi** (SILINEN=1919; kalanlar 2 saatten TAZE). `profil-*` 243=243 DOKUNULMADI,
  token'lar YERINDE. 🔴 ACIK: (a) ureten betikler hala toplamiyor (otomatik kol + test),
  (b) 243 `profil-*` dizini ayri kural ister (canli turun profili silinirse tur coker).
  kabul: `ls -1a /Users/okan/.claude/cron | grep -c "^\.isci-cikti\."` iki tur ust uste
  DUSMELI.
- 🔧 **K146 (17 Agu — nobet dosyalari YEDEKSIZ):** `~/.claude/cron/` versiyon kontrolu
  DISINDA → curutucu, iscinin kabul-testi fiksturunu MESRU mu degistirdi OLCEMEDI
  (eksen KOR). Yon: otomatik yedek + `yedekle.py` kapsam teyidi. `kabul:` alani BOS.
- 🔴 **K141 (17 Agu — OLCULEMEYEN NOBET, sinif kalemi):** `kapi-envanteri.py` main'de DE
  kirmizi: `mimar-icra-kapisi` + `mimar-kod-kilidi` "NOBETTE degil — reddetmesi gerekeni
  REDDETMEDI". Yapisal: nobet testi **isci turunda** kosuyor, muafiyet kolu "reddetmeli"
  vakasini gecirmiyor; mimar ayni komutu KENDI kosamaz → **iki mimar kapisinin canliligi
  hicbir yerden olculemiyor** ([[makineyi-olctuk-urunu-olcmedik]]). Yon: nobet vakasi
  muafiyet kolundan BAGIMSIZ altsurecte kossun. `kabul:` alani BOS.
- 🔧 **K142 (17 Agu, KraL olctu → MaCiT):** pre-push kapak taramasi **14 R2 anahtari
  `NoSuchKey`** buldu, hepsi `c3d*` onekli (Cults3D partisi). Canlida 404 veren URUN
  KAPAKLARI — K125 ile AYNI SINIF ([[gorsel-anahtar-cakismasi]]). Tam liste push logunda,
  kutuya yazildi. Sahibi veri seridi. `kabul:` alani BOS.
- ✅ **K133 KAPANDI** (`42e28cf7` merge, `c5225016` push) — tam metin ARSIVDE; kuyruk K140.
- 🔧 **K118:** pre-push sizinti kapisi bicim-kaydiran urun partisinde butceyi yapisal
  asiyor (tam-dosya diff). Yon: butce buyutmek DEGIL, `urunler.json`'u icerik ekseninde
  AYRI ele almak. `kabul:` alani BOS.
- 🟠 **Navlungo dilim-1 MERGE BEKLIYOR:** dal `il-ilce-dilim1` (`5d57c918`); Okan kapisi.
- 🔴 **K104 / K104B:** nobet sicili + iki kapi main'de kirmizi. HUKUM MIMARDA. · **K99**
  bag kolonu · **K100** satir-sonu muafiyeti · **K102** yasakli ic dosya adi.
- 🟠 **K152 (17 Agu — ⚖️ OKAN KARARI KAPSAMI BELIRLEDI; onceki iki hukum de DUSTU):**
  Okan (birebir): **"sitede bulunan tum urunler satilabilir. SAKIN siteden bir urun
  SILME."** Yapilacak TEK is: isaret ettigi kaynak grubunun urunlerine **uretici linki**
  eklemek, ayni durumdaki digerlerine de. **"SORU SATILABILIRLIK YA DA LISANS KONTROLU
  DEGIL, EKSIK LINKLERI TAMAMLAMA."**
  Ek emir: **"public'e link KESINLIKLE YASAK, sadece bizde intern kaydedin, ben istedigimde
  HEMEN bulunacak."** Silme/`yayinda=0`/`auto_sil` YASAK; dusen iki hukum ARSIVDE.
  🔴 PUBLIK↔KAYIT birlesim ekseni de olculdu (`ebf61902`, `tools/koken-bul.py --eksik`):
  `EKSIK=259` — **KAYIT_YOK=197** (public urunun gizli kaydi HIC yok, kayit evreninde
  GORUNMEZ) · linksiz-cults3d 44 · dizge 12 · kokensiz 6 (+25 kaynak alani bos).
  Duzlem VERI = MaCiT (parti yazicisi UCUSTA; flock + `duzelt.py`). Eski kabul
  (`denetim-kapisi` rc=0) DUSTU: rc=0 ulasilamaz (3154 ihlal) ve caresi SILME.
  kabul: `python3 tools/koken-bul.py --eksik` → `EKSIK` DUSER **VE** `--kendini-test` rc=0.
- 🔧 **Iki acik kapi kalemi:** (a) shop bayatlik alarminin TETIK ekseni raporladigi bundle
  evreniyle AYNI DEGIL; (b) `devam-sinif-kapisi.py` is-akisi muafiyeti `norm`/`ham`
  ekseninde ayrisiyor.
- 🟠 **K122:** `kurtarma/k122-yabanci-is` dali DURUYOR — peer'in dusurulen commitsiz isi
  (deploy.yml serit tasima · marka-uyelik-test.py · kalibrasyon 4 dosya). Sahibi uygulayacak.
- 🟡 **Kosum sinyali kirli (olculdu):** `hijyen-a2`/`a3` yayin zincirinde DEGIL ama genel
  `conclusion`'i `failure` yapiyor. Kural: genel hukme degil **is bazinda** bakilir
  (hijyen kirmizisi gurultu DEGIL — K125'i o buldu). Tam metin ARSIVDE.
- 🔧 **K151 (yedek dusus beyani her rotasyonda ELLE yeniden yaziliyor; sinif):** karantina
  cozuldu (dususler MESRU olcuLdu, arsivler dususten FAZLA buyudu). Beyan TAM boyuta bagli
  → 3. tekrar. **Yon:** ROTASYON CIFTI invaryanti. Tam metin ARSIVDE.
- KAPANDI (arsivde): K91 · K101 · K103 · K113 · K114 · K115 · K116 · K117 · K119 · K120 · K123 · K124 · K125 · K128 (madde olcutu ILK SATIR sartina daraltildi, `6dc1a94e`, fikstur 20/20 mutant 7/7; ders hafizada) · K121 (17 Agu: supurme Okan emriyle acildi, denetlendi, acik KAPATILDI — zamanlanan giris noktasi kanonik `github-mail-cope.applescript` yoluna YONLENDIRILDI; kabul `DERLEME_RC=0 MAIL_ERISIMI=0 KENDINI_TEST_RC=0 KOMSU_ALARM=4 SILINEN_MAIL=0`; olculen acik = v2'nin uc emniyeti YOKTU + `ATLANAN>0` 6 kosumda yani message-id cakismasi gercek; detay posta kutusunda, ders [[korelasyon-mekanizma-teshisi-degildir]]) · K127 rotasyon madde granulu kol (`e5f5c32b`) · **K138** (mail ARIZA SINYALI degildi — nobet metni "maile guvenme" diyor, olcum `gh run list`; Okan GitHub bildirimini kapatti, crontab satiri KALDIRILDI **ve** nobet gorev metnindeki supurme adimlari §0.4+§1+§4 EMEKLI isaretlendi — yalniz crontab'i kaldirmak silme yolunu AJAN elinde canli birakirdi; otomatik mail silicisi KALMADI, bundan sonra mail kaybolursa sebep KESINLIKLE ucuncu bir yol; geri acma OKAN KAPISI, ikisi AYNI turda) · **K137** (birkac saat `crontab` YAZIMI asildi — okuma calisiyordu, asili surec `pgrep` ile teyitli, SIGKILL gerekti; 11:00 civari acildi. Tuzak: `crontab <dosya>` dosyayi BULAMAZSA stdin'den okur ve SESSIZCE asilir — once `ls`, sonra `crontab -l` ile FARK olc).

## OKAN'DA

- 🔧 Eski yedek klasorunu backup-v2 icine tasima · K89 olcum eylemi silme karari.
  (16 Agu: rotasyon bu maddeyi bir kez arsive supurdu — parantezdeki kapali kalem atfi
  yuzunden; geri konuldu, sinif kusuru K128.)
- 🔧 **TARIFE KARAR KURALI (olculdu, onaya hazir):** mevcut $20 plan KALIR. Haftalik kota %80'e yaklasirsa ikinci saglayicinin $39 basamagi TERCIH EDILIR — ayni para bandinda hem kota hem **ikinci saglayici** (429/kesinti/kota duvarinda yedek) verir; mevcut saglayicinin $50 basamagi yalniz kota verir, tek-saglayici riski surer. Ikinci saglayici bekleme listesindeyse tek uygulanabilir yol $50 (0 kod degisikligi). Ust basamagin iki "deneysel" ozelligi bizim hatta GIRMEZ — biz yalnizca Anthropic-uyumlu API ucundan MODEL cagiriyoruz. Kota sayilari iki adayda da yayimlanmiyor, yani secimi fiyat degil CESITLILIK belirliyor. Ekleme bedeli motor basina 6 kod noktasi.
- Olculen maliyet tabani: $18,72 / 1.081.021.287 token / 8.639 istek = yaklasik $17,3/milyar; $20/ay ve yaklasik 4,6 milyar/ay = yaklasik $4,3/milyar.

## KOSUYOR (baska mimarlar)

MaCiT — Peugeot×Cults3D dilim-2 (`658d0333`, `peugeot-push-tmp` worktree'de, K153'e BLOKE).
K152 iki oturum: `musing-shaw` SALT OKUMA (koken bulucu) · `xenodochial-bardeen` TEK YAZICI
(yalniz gizli kayit duzlemi, flock + public sha256 nobeti). Sahiplik KraL'ca kesildi.

## ARSIVDE (tam metinler `DEVAM-ARSIV.md`'de)

14-15 Agu saatlik CI nobeti turlari · 15 Agu gece oturum kapanisi · K101/K103 kapanislari · yayin ve odeme etiketi bloklari · dorduncu motorun hatta baglanmasi · HD/Kawasaki/Ducati ekleme bloklari · sabah oturumunun tam olcum blogu · defterin sikistirma oncesi 196 satirlik tam hali.