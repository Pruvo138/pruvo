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
- 🟠 **K148 (GOZCU FAZ-1 KOSTU ve BAGIMSIZ DOGRULANDI; faz-2 + canliya baglama kaldi):** uc dosya `~/.claude/cron/` altinda, **repo ayak izi SIFIR**;
  Tam metin ARSIVDE.
  kabul: `python3 /Users/okan/.claude/cron/gozcu-test.py` (rc=0) **VE** `MUTANT=13/13`.
- 🔧 **K149 (URETEN KOLU KURULDU; `profil-*` ekseni ACIK ve BEYAN CELISKILI):** 17 Agu
  `isci-temizlik.py` + 5/5 test yazildi, `isci.sh:757`'ye baglandi (`TEMIZLIK_CAGRISI=VAR`).
  🔴 Bir tur `PROFIL_SILINEN=239` beyan etti; BAGIMSIZ sayim **253 dizin** buldu ve
  **hepsi 2 saatten TAZE** (en eski 114,9 dk) → yas kurali hicbirini silemiyor. Iki
  ihtimal ayirt EDILEMEDI: silme hic olmadi VEYA temizlik gecisi dizin mtime'larini
  tazeleyip kurali kendi kendine etkisiz kildi. Sonraki tur bunu OLCSUN (mtime'i
  degistirmeyen bir yas olcutu: dizin ADINDAKI tur damgasi ya da ic dosya mtime'i).
  kabul: iki ardisik turda `profil-*` sayisi DUSMELI **VE** canli tur profili silinmemis olmali.
- 🔴 **K157 (17 Agu — KIMI HATTI KOK NEDEN BULUNDU, karar OKAN'DA):** iki m3 olcum turu:
  `max_tokens=1`'in **200'u SAHTE** (`content[0].text=""`, `stop_reason=null`, `type/role` bos)
  → "1 token calisiyor" kapasite DEGIL olcum artefakti; **gercek uretim SIFIR**. `>=2` daima
  403 `permission_error`, govde byte-byte ayni. 10x15.007=**150.070 girdi token** mt=1 ile
  gecti, esigi DEGISTIRMEDI → girdi ekseni ilgisiz. Kota basligi/`request-id` **yok**, kota
  okuma ucu icin **47 aday 404** → API'den kota OKUNAMIYOR. `/coding/v1/me`=200,
  `status=USER_STATUS_NORMAL`, `created_time=2026-08-14` (anahtar mtime + 15 Eyl yenilemesiyle
  tutarli) → anahtar Okan'in KENDI hesabinda; "baska plan" teshisi dustu. 403 TAM metni careyi
  soyluyor (TAM 403 metni ARSIVDE — satici URL'i guvenlik geregi tasindi).
  ✅ **Panel celiskisi COZULDU** (Okan'in sorusu + saticinin oz dokumani): Kimi Code'un AYRI
  kredisi YOK, uyelik havuzunu paylasir (ucuncu parti API dahil) ve **krediler 7 GUNDE BIR,
  abonelik tarihinden yenilenir, artan devretmez**. Panelin **%19,99'u AYLIK** sayac; tukenen
  **haftalik dilim**. "5s Kod %0 / 7g Kod %0" ise HIZ penceresi (kredi sayaci degil) — saatlerdir
  her istek reddedildigi icin bos okuyorlar. 403'un "next cycle"i = **~22 Agu**, 15 Eyl DEGIL →
  **odeme GEREKMIYOR**. **Yanlislanabilir kanit kuruldu:** `~/.claude/cron/kimi-nabiz.py`
  gunde 2x (09:10/21:10) GERCEK is atar (`max_tokens=1024`) ve UC sarta bakar (200 + icerik
  bos degil + `stop_reason` null degil); `kimi-nabiz-test.py` **5/5 vaka, 2/2 mutasyon YESIL**,
  crontab **36→38** teyitli. Ilk olcum `2026-08-17T15:51:09Z SAGLIK=KIRMIZI http=403
  tip=permission_error icerik=bos stop=null`.
  kabul: 22 Agu'da `kimi-nabiz.log` **SAGLIK=YESIL** → haftalik dongu DOGRULANDI; hala KIRMIZI
  ise aylik tavan hipotezi kazanir ve **karar Okan'a doner** (extra usage / plan yukseltme).
- 🔵 **K158 (17 Agu, TASARIM ACIGI — KAYIT):** isci tarayicisi YALNIZ kimi motorunda var
  (m3'te yok) → kimi dustugunde paneli okuyacak yol da kapaniyor; tek tarayicili motorun
  dususu TESHIS yolunu da kesiyor. Yon: tarayiciyi motordan bagimsiz kola tasi. `kabul:` BOS.
- 🔧 **K146 (17 Agu — nobet dosyalari YEDEKSIZ):** `~/.claude/cron/` versiyon kontrolu
  DISINDA → curutucu, iscinin kabul-testi fiksturunu MESRU mu degistirdi OLCEMEDI
  (eksen KOR). Yon: otomatik yedek + `yedekle.py` kapsam teyidi. `kabul:` alani BOS.
- 🔴 **K141 (17 Agu — OLCULEMEYEN NOBET, sinif kalemi):** `kapi-envanteri.py` main'de DE kirmizi: `mimar-icra-kapisi` + `mimar-kod-kilidi` "NOBETTE degil — reddetmesi gerekeni REDDETMEDI".
  Tam metin ARSIVDE.
  muafiyet kolundan BAGIMSIZ altsurecte kossun. `kabul:` alani BOS.
- 🔧 **K142 (17 Agu, KraL olctu → MaCiT):** pre-push kapak taramasi **14 R2 anahtari `NoSuchKey`** buldu, hepsi `c3d*` onekli (Cults3D partisi).
  Tam metin ARSIVDE.
  kutuya yazildi. Sahibi veri seridi. `kabul:` alani BOS.
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


## OKAN'DA

- 🔧 Eski yedek klasorunu backup-v2 icine tasima · K89 olcum eylemi silme karari.
  (16 Agu: rotasyon bu maddeyi bir kez arsive supurdu — parantezdeki kapali kalem atfi
  yuzunden; geri konuldu, sinif kusuru K128.)
- 🔧 **TARIFE KARAR KURALI (olculdu, onaya hazir):** mevcut $20 plan KALIR. Haftalik kota %80'e yaklasirsa ikinci saglayicinin $39 basamagi TERCIH EDILIR — ayni para bandinda hem kota hem **ikinci saglayici** (429/kesinti/kota duvarinda yedek) verir; mevcut saglayicinin $50 basamagi yalniz kota verir, tek-saglayici riski surer. Ikinci saglayici bekleme listesindeyse tek uygulanabilir yol $50 (0 kod degisikligi). Ust basamagin iki "deneysel" ozelligi bizim hatta GIRMEZ — biz yalnizca Anthropic-uyumlu API ucundan MODEL cagiriyoruz. Kota sayilari iki adayda da yayimlanmiyor, yani secimi fiyat degil CESITLILIK belirliyor. Ekleme bedeli motor basina 6 kod noktasi.
- Olculen maliyet tabani: $18,72 / 1.081.021.287 token / 8.639 istek = yaklasik $17,3/milyar; $20/ay ve yaklasik 4,6 milyar/ay = yaklasik $4,3/milyar.


## KOSUYOR (baska mimarlar)

K152: `xenodochial-bardeen` TEK YAZICI (gizli kayit duzlemi, flock + public sha256 nobeti);
worktree'sinde main'de OLMAYAN 1 commit var → temizlikte bilerek ATLANDI, bundle ister.
(`musing-shaw` ve MaCiT'in peugeot/chevy worktree'leri kapandi; K153 blokeri kalkti.)

## CANLI OLCUM (17 Agu, K153 sonrasi — cache-bust'SIZ, kanonik adres)
`SITE_HTTP=200 · canli urunler.json benzersiz id=29012 · D1=29012 · yeni urun sayfalari 200`
CI `2c092d5c`: `build`+`serit-a2`+`deploy`+`yayin` **success**; kirmizi yalniz `hijyen-a2`
(K140) + `hijyen-a3` (M3b) — hijyen seridi, yayini DURDURMAZ.


## ARSIVDE (tam metinler `DEVAM-ARSIV.md`'de)

14-15 Agu saatlik CI nobeti turlari · 15 Agu gece oturum kapanisi · K101/K103 kapanislari · yayin ve odeme etiketi bloklari · dorduncu motorun hatta baglanmasi · HD/Kawasaki/Ducati ekleme bloklari · sabah oturumunun tam olcum blogu · defterin sikistirma oncesi 196 satirlik tam hali · 17 Agu ROTASYON-2 (K147 · K154 · K155 · K156 · K133 · K91 · K101 · K103 · K113-119 · K120 · K123-125 · K128 · K121 · K127 · K138 · K137).