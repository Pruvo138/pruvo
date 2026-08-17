# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.


## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)

- 🔧 **K134 (defter kotasi SINIF kalemi; BaBa 3. kez kirmizi dedi, SPEC HAZIR):** care (`defter-rotasyon.py`) mimar kod kilidinde YASAK.
  Tam metin ARSIVDE.
  kabul: `python3 /Users/okan/dev/pruvo/tools/defter-rotasyon-test.py`
- 🔧 **K135 (17 Agu, MaCiT→KraL):** `cgt-ekle.py::fetch()` tek satir UA ile CGTrader WAF'ina takiliyor (HTTP 202 + placeholder);
  Tam metin ARSIVDE.
  Kalici `--yerel` yolu KraL'da, sonraki dilim oncesi. `kabul:` alani BOS.
- 🔵 **K136 (17 Agu, KAYIT):** ana agacta `tools/marka-uyelik-test.py` DORT oturumdur
  commit'siz (K126 "tek govde" yuklemini ham donguye geri aliyor). DOKUNULMADI.
- 🔵 **K132 (17 Agu, KAYIT — yayini BLOKLAMAZ):** `isci-tur-tavani-test.py` tek basina
  KALDI, `testler.py` icinden GECTI; celiski uretilemedi. Tam metin + kabul ARSIVDE.
- 🟠 **K139 (17 Agu, Okan emri — CANLI DURUM, ekip bilmeli):** crontab'ta 3 gorev
  yorumlandi; 181 → **25 atesleme/gun**. 🔴 ETKI: posta kutusu OTOMATIK izlenmiyor **ve
  urun partileri kendiliginden ILERLEMIYOR**. Tam metin ARSIVDE. `kabul:` alani BOS.
- 🔴 **K150 (UZLASTIRICI YANLIS SINIFLANDIRIYOR; ② ICIN BLOKER):** kosum `32026332006` KIRMIZI: senkron **tasarim geregi ATLANDI** (`SEBEP=YAZICI_UCUSTA`), surucu bunu **"GERCEK HATA, YENIDEN DENENMEZ"** ilan etti.
  Tam metin ARSIVDE.
  kabul: `python3 /Users/okan/dev/pruvo/tools/uzlastirici-onarim.py --kendini-test`
- 🟠 **K144 (UCUSTAKI KOSUM):** ardarda push'lar build'i `cancelled` ediyor (ARIZA DEGIL);
  hukum her turda guncel uca tasiniyor. Tam metin ARSIVDE.
  kabul: guncel ucu ICEREN kosum `conclusion=success` **VE** cache-bust'SIZ canli teyit.
- 🔧 **K140 (17 Agu — ACIK SORU MIMARCA KAPATILDI, icra kaldi):** hukum **kapinin MODEL hatasi degil, EVREN KAYNAGI hatasi**: 185 urunun 184'unde model jetonu gercek markanin YANINDA, ve `index.html:3148` cip evreni KURATORLU (model kodu CIP OLMAZ) → kapi sitede OLMAYAN bir baglanti icin sayfa istiyor.
  Tam metin ARSIVDE.
  kabul: `python3 tools/marka-invaryant-kapisi.py` — 7 model jetonu DUSMUS **VE** `Rover` DURUYOR **VE** mutasyon 4/4.
- ✅ **K147 KAPANDI** (sayac 63 → 65, DUSMEDI) → karar ②'ye gecti, devami K148. ARSIVDE.
- 🔴 **K154 (17 Agu — K153'UN YAN HASARI, DEPLOY BLOKE):** `Build & deploy` kirmizi → `deploy`+`yayin` **skipped** (vitrin yayini durdu;
  Tam metin ARSIVDE.
  kabul: `python3 tools/d1-seq-kilit-test.py --mutasyon` rc=0 **VE** `MUTANT_KALDI=0` **VE** `CAPA_UYARISI=0`.
- 🔴 **K155 (17 Agu — serit-a2 KIRMIZI, veri kusuru):** `chevy-klasik-jant` kaydinda `"marka": ["Chevrolet", ""]` — dizide BOS JETON.
  Tam metin ARSIVDE.
  kabul: uyum kapisi rc=0 **VE** `kalan 0`.
- 🟠 **K148 (GOZCU FAZ-1 KOSTU ve BAGIMSIZ DOGRULANDI; faz-2 + canliya baglama kaldi):** uc dosya `~/.claude/cron/` altinda, **repo ayak izi SIFIR**;
  Tam metin ARSIVDE.
  kabul: `python3 /Users/okan/.claude/cron/gozcu-test.py` (rc=0) **VE** `MUTANT=13/13`.
- 🔧 **K149 (DOSYA KOLU KAPANDI, URETEN-KOLU ACIK):** `~/.claude/cron/` **2495 → 576 girdi** (SILINEN=1919;
  Tam metin ARSIVDE.
  kabul: `ls -1a /Users/okan/.claude/cron | grep -c "^\.isci-cikti\."` iki tur ust uste DUSMELI.
- 🔧 **K146 (17 Agu — nobet dosyalari YEDEKSIZ):** `~/.claude/cron/` versiyon kontrolu
  DISINDA → curutucu, iscinin kabul-testi fiksturunu MESRU mu degistirdi OLCEMEDI
  (eksen KOR). Yon: otomatik yedek + `yedekle.py` kapsam teyidi. `kabul:` alani BOS.
- 🔴 **K141 (17 Agu — OLCULEMEYEN NOBET, sinif kalemi):** `kapi-envanteri.py` main'de DE kirmizi: `mimar-icra-kapisi` + `mimar-kod-kilidi` "NOBETTE degil — reddetmesi gerekeni REDDETMEDI".
  Tam metin ARSIVDE.
  muafiyet kolundan BAGIMSIZ altsurecte kossun. `kabul:` alani BOS.
- 🔧 **K142 (17 Agu, KraL olctu → MaCiT):** pre-push kapak taramasi **14 R2 anahtari `NoSuchKey`** buldu, hepsi `c3d*` onekli (Cults3D partisi).
  Tam metin ARSIVDE.
  kutuya yazildi. Sahibi veri seridi. `kabul:` alani BOS.
- ✅ **K133 KAPANDI** (`42e28cf7` merge, `c5225016` push) — tam metin ARSIVDE; kuyruk K140.
- 🔧 **K118:** pre-push sizinti kapisi bicim-kaydiran urun partisinde butceyi yapisal
  asiyor (tam-dosya diff). Yon: butce buyutmek DEGIL, `urunler.json`'u icerik ekseninde
  AYRI ele almak. `kabul:` alani BOS.
- 🟠 **Navlungo dilim-1 MERGE BEKLIYOR:** dal `il-ilce-dilim1` (`5d57c918`); Okan kapisi.
- 🔴 **K104 / K104B:** nobet sicili + iki kapi main'de kirmizi. HUKUM MIMARDA. · **K99**
  bag kolonu · **K100** satir-sonu muafiyeti · **K102** yasakli ic dosya adi.
- 🟠 **K152 (17 Agu — ⚖️ OKAN KARARI KAPSAMI BELIRLEDI; onceki iki hukum de DUSTU):** Okan (birebir): **"sitede bulunan tum urunler satilabilir.
  Tam metin ARSIVDE.
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