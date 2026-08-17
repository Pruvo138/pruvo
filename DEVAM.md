# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)

- 🔧 **K134 (17 Agu — defter kotasi SINIF kalemi; BaBa 3. kez kirmizi dedi, SPEC HAZIR):**
  care (`defter-rotasyon.py`) mimar kod kilidinde YASAK; isciye verilince `TASINAN=0`.
  🔴 Bu oturumda kota **ALTI kez** elle indirildi (151→125·137→130·133→130·131→130·
  140→130·131→130) — ceza yazma aninda degil **COMMIT aninda** odeniyor. Kok: K39 kancasi
  **INDEX** olcuyor, BaBa **CALISMA AGACI** olcuyor; hukum farkli birimlerde
  ([[hukum-yanlis-birimde]]) → kanca "yesil" derken diskte 140 satir olabiliyor.
  Yon: (a) `CARE:` metni **1:1 tasimayi** gostersin (rolun kosabilecegi yol),
  (b) calisma-agaci kolu UYARI olarak eklensin (BLOKLAYICI olursa kotayi dusuren
  commit'in kendisi bloklanir). Spec: `SPEC-defter-kota-1e1.md` (5 vaka + 4 mutant).
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
- 🔴 **K150 (17 Agu — UZLASTIRICI YANLIS SINIFLANDIRIYOR; ② ICIN BLOKER):** kosum
  `32026332006` KIRMIZI: baska makinede D1 yazicisi vardi, senkron **tasarim geregi
  ATLANDI** (`SEBEP=YAZICI_UCUSTA`); surucu bunu **"GERCEK HATA, YENIDEN DENENMEZ"** ilan
  etti. Kok: ayni `rc=4` `deploy.yml`'de **0**, uzlastiricida **1** — `onar()` `--adim`SIZ
  cagiriyor, yalniz IKI imza taniyor, tanimadigi her red `else`'ten GERCEK HATA'ya dusuyor.
  🔴 ② blokeri: gozcu her `failure`'a LLM turu acar → MaCiT her D1'e yazdiginda yanlis
  kirmizi. Spec: `SPEC-k150-uzlastirici-rc4.md` (rc=5 ERTELENDI + RETRY + kapsam kapisi).
  kabul: `python3 /Users/okan/dev/pruvo/tools/uzlastirici-onarim.py --kendini-test`
- 🟠 **K144 (UCUSTAKI KOSUM):** ardarda push'lar build'i `cancelled` ediyor (ARIZA DEGIL);
  hukum her turda guncel uca tasiniyor. Tam metin ARSIVDE.
  kabul: guncel ucu ICEREN kosum `conclusion=success` **VE** cache-bust'SIZ canli teyit.
- 🔧 **K140 (17 Agu — ACIK SORU MIMARCA KAPATILDI, icra kaldi):** hukum: **kapinin MODEL
  hatasi degil, EVREN KAYNAGI hatasi**. Olculdu: (1) 8 jetonu tasiyan 185 urunun **184'unde
  jeton gercek markanin YANINDA** (`Yamaha+MT-07`, `KTM+1290`), tek istisna `["Rover"]`;
  (2) `index.html:3148` cip evreni KURATORLU — model/motor kodu **CIP OLMAZ**, yani o
  baglanti sitede YOK; (3) `TANINMIS_MARKALAR`'da 7 model jetonu **YOK**, `Rover` **VAR**.
  Yani kapi olmayan bir baglanti icin sayfa istiyor → evren, ciplerin kullandigi AYNI
  kuratorlu kaynaktan turemeli (K133 sinifinin aynisi). `Rover` ise GERCEK kayip (2 urun).
  Spec: `kalibrasyon/SPEC-k140-marka-evreni.md`. 🔴 Hedef rc=0 DEGIL, **dogru kirmizi**:
  daraltmadan sonra `Rover` KALMALI, dusrse kapi korlesmistir (mutant M2).
  kabul: `python3 tools/marka-invaryant-kapisi.py` — `FILTRE_KAYIP`'ta 7 model jetonu
  DUSMUS **VE** `Rover` DURUYOR **VE** mutasyon 4/4.
- ✅ **K147 KAPANDI** (sayac 63 → 65, DUSMEDI) → karar ②'ye gecti, devami K148. ARSIVDE.
- 🟠 **K148 (17 Agu — GOZCU FAZ-1 KOSTU ve BAGIMSIZ DOGRULANDI; faz-2 + canliya baglama
  kaldi):** Okan izniyle Claude iscisi uc dosya uretti (`gozcu.py` · `gozcu-test.py` ·
  `gozcu-mutasyon.py`, hepsi `~/.claude/cron/`, **repo ayak izi SIFIR**). Tasarim: tetik
  gozcude, icra AYNEN `nobet-kapi.py`'de. **BAGIMSIZ olcum** (ayri isci, ayri surec):
  `GECEN=63/63` · `MUTANT=10/10 KONTROL=YESIL` · kuru tur `TETIK=DEFTER_DAGITIM LLM_TURU=0`
  · `KALP=YOK rc=1` (dogru) · `YAN_ETKI=HAYIR`. Oz-rapor ile bagimsiz kosum UYUSTU.
  🔴 **FAZ-2 (mimar denetiminde bulundu — testler goremedi, SPEC eksikti):** F1 `_kilit_al`
  O_EXCL DEGIL (TOCTOU) · F2 `_kilit_birak` sahiplik denetimsiz · F3 `deneme >= 3` sabiti
  `ESKALASYON_ESIGI` ile IKIZ. Spec: `SPEC-gozcu-kilit-onarimi.md` (+3 mutant). Canliya
  baglama (48s paralel) faz-2'den SONRA; crontab'a DOKUNULMADI.
  kabul: `python3 /Users/okan/.claude/cron/gozcu-test.py` (rc=0) **VE** `MUTANT=13/13`.
- 🔧 **K149 (17 Agu — DOSYA KOLU KAPANDI, URETEN-KOLU ACIK):** `~/.claude/cron/`
  **2495 → 576 girdi** (SILINEN=1919; `.isci-cikti.*` 1209→3, `.bekci-cikti.*` 900→187 —
  kalanlar 2 saatten TAZE). `profil-*` **243=243 DOKUNULMADI**, token dosyalari YERINDE.
  🔴 ACIK KALAN: (a) ureten (`isci.sh`, `isci-tur-bekcisi.py`) hala toplamiyor — otomatik
  kol + testi gerek; (b) **243 `profil-*` dizini** (en eski 4 gun, en yeni 1 dk) ayri
  kural ister: canli turun profili silinirse tur coker.
  kabul: `ls -1a /Users/okan/.claude/cron | grep -c "^\.isci-cikti\."` iki tur ust uste
  dusmeli (ureten kolu calisiyor demektir).
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
  🔴 Dolayisiyla (a) HocA'nin "eksik alan" bulgusu → ISLENECEK, (b) benim "geri doldurma
  ihlal olur" hukmum → **EZILDI**, (c) "fail-closed satistan cekilme" ekseni → **IPTAL**.
  Silme/`yayinda=0` YASAK. Olculen sayilar + iki dusen hukum ARSIVDE (kayit icin).
  Duzlem VERI = MaCiT; yazim flock + `duzelt.py`, MaCiT'in parti yazicisi UCUSTA.
  kabul: `python3 /Users/okan/dev/pruvo/tools/denetim-kapisi.py` (rc=0).
- 🔧 **Iki acik kapi kalemi:** (a) shop bayatlik alarminin TETIK ekseni raporladigi bundle
  evreniyle AYNI DEGIL; (b) `devam-sinif-kapisi.py` is-akisi muafiyeti `norm`/`ham`
  ekseninde ayrisiyor.
- 🟠 **K122:** `kurtarma/k122-yabanci-is` dali DURUYOR — peer'in dusurulen commitsiz isi
  (deploy.yml serit tasima · marka-uyelik-test.py · kalibrasyon 4 dosya). Sahibi uygulayacak.
- 🟡 **Kosum sinyali kirli (olculdu):** `hijyen-a2`/`a3` yayin zincirinde DEGIL ama genel
  `conclusion`'i `failure` yapiyor. Kural: genel hukme degil **is bazinda** bakilir
  (hijyen kirmizisi gurultu DEGIL — K125'i o buldu). Tam metin ARSIVDE.
- 🔧 **K151 (17 Agu — YEDEK DUSUS BEYANI HER ROTASYONDA YENIDEN YAZILIYOR; sinif kalemi):**
  karantina `DEVAM.md` + `mimar-posta-kutusu.md` yedegini durdurdu; ikisi de MESRU rotasyon
  (OLCULDU: kutu -104079 B / arsivi **+107530 B** · defter -20961 B / arsivi **+59657 B**).
  Beyan TAM boyuta bagli, her rotasyonda ELLE yeniden yaziliyor (3. tekrar → tekil yama
  YASAK). **Yon:** ROTASYON CIFTI invaryanti — dusus ancak esi o kadar BUYUDUYSE mesru.
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