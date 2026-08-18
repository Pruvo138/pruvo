# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.


## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)
- 🟠 **K186 CHIP `KraL-Ege reformu altyapi`** — TUR 2d kosuyor (serit hukmu YARIM uygulanmisti,
  chip kendi yakaladi: `--capa` acilacak, G5 kendi bayragina tasinacak 17→16, serit-a3'e 2. adim).
  🔴 **MERGE SARTI (19 Agu):** ya Node 20 ile kosmus ham cikti ya da SHA'yi iceren YESIL CI kosumu —
  yerel 50/50 tek basina YETMEZ. Tam metin KUTUDA.
- 🔧 **K196 (19 Agu, DEPO GENELI):** CI node 20 / yerel 25.8.1 → yereldeki JS yesilleri CI surumunde OLCULMEMIS. **Tam metin ARSIVDE.** K186 merge sartina bagli.
- 🔧 **K197 (19 Agu, K189 chip olctu — YAYIN YOLU MALIYETI, RATCHET YOK):** pre-push kancasinin
  maliyet beyani 3,16 sn (9 Agu) diyor, **bugun olculen medyan 6,11 sn** → 5 sn esigi zaten asilmis;
  sayiyi YORUM soyluyor, dogrulayan yok. **Tam metin ARSIVDE.**
- 🔧 **K189 (SAHIPLENILDI 19 Agu — KraL; CHIP ACILDI):** `tools/ci-kapsam-test.py` hukum ekseni
  kusurlu. **Tam metin ARSIVDE.** kabul: aday>0 iken `OLCULEMEDI`+sifir-disi rc, ayri jeton, mutant
  hedef kolu kanitli (K182).
- 🔧 **K191 (19 Agu, KraL olctu → sahibi MaCiT; SINIF):** tarama SPEC'i isi ONCULDEN aliyor.
  **Tam metin ARSIVDE + KUTUDA.** kabul: ILK blok KAPSAM ON-OLCUMU degilse RED + tazelik capasi.
- 🟠 **K184 CHIP `KraL-Faz-1 sihirbaz`** — dal `42c47288` KAPANDI, **merge SIRADA (K186'dan SONRA)**.
  🔴 MIMAR HUKMU 19 Agu: uc (`/talep` handler + kendi DDL'i) DALDAN CIKAR, yalniz istemci kalir;
  K186'nin semasi/ucu KANONIK ve uctan uca olcum K186'nin ucune karsi YENIDEN kosulur. Tam metin KUTUDA.
- 🔧 **K192 (19 Agu → Okan: "kalem ac, DOKUNMA"):** `kimi` bes evin KURULU kapisinda YOK + dagitim kaniti VARLIK olcup yesil yaniyor. **Tam metin ARSIVDE.** (BaBa serhi: 20 Agu codex bitisi.)
- 🔧 **K193 · K194 (19 Agu, K184 chip):** varlik `cp` satiri iki yerde (ikiz tanim; kabul: tek
  kaynaktan turer + ayrisinca kapi KIRMIZI) · kaynak kosum takimina gore bukuldu (sahte DOM; koruma
  KALIR + SEBEP satiri zorunlu, kalici care kosum takimi). **Ikisinin tam metni ARSIVDE.**




## 🔻 KraL SON DURUM — 19 Agu ~04:0xZ (kapanis blogunun tam metni ARSIVDE)
**CANLIYA:** K181d · K177 · K141 · K183 `77bb3195` · T3 `8ca4c716` · T4 `893d278d`. **KOSUYOR (hepsi CHIP):** K184 · K185 (donuk, merge sirasinda) · K186 · K188. **BEKLIYOR:** HocA Faz-2 · MaCiT Honda (K191).
🔧 **K187 — ⚖️ OKAN KARARI 19 Agu: KV BINDING** (Logpush DEGIL). Icra K186 chip'te (binding tanimi + `talepOlayiSay()` govdesi); namespace acma + deploy Okan kapisi.
🔧 **K190 — ⚖️ OKAN KARARI 19 Agu: CANLI D1'e BAGLANACAK, talep hatti canliya cikmadan ONCE.** `talep-temizlik.py` yerel sqlite'a bagliydi → 90 gunluk saklama fiilen yururlukte DEGILDI. Icra K186 chip'te (`--kuru` olcumune kadar); canli kosum + zamanlanmis is Okan/mimar kapisi.
- 🔴 **T1 pencere muhasebesi + T3/T4 kaniti (baglayici):** olculen baslangic `11:23:00Z`,
  `OLCULEMEDI_TUR=2` AYRI satir; nobet kosuyor ama `ONARIM=0`, 10 kalem MIMAR'da. **Tam metin ARSIVDE.**
- 🔧 **K195 (19 Agu — 4. TEKRAR, tekil yama YASAK):** `defter-rotasyon.py` kapali madde yokken
  TASIMIYOR → kota her oturumda ELLE rotasyon istiyor (bugun 4 kez). **Tam metin ARSIVDE.**
- ✅ **19 Agu MERGE EDILDI:** **K185** chip duzeni (14/14 · 9/9 · tavan 12/12 · aday=0) · **K188** kutu
  esik kapisi (11/11 · 7/7; ⚠️ KANCA BAGLI DEGIL → kapi main'de ama CANLI DEGIL, chip acildi) ·
  T3 `8ca4c716` · T4 `893d278d`. Iki chip agaci + bes artik dal temizlendi (worktree 7→4).
- ✅ **KAPANANLAR (tam metin ARSIVDE):** ③ `4270c95e` (sahiplik haritasi kapisi canlida SUCCESS) ·
  K178+K178b (SERIT B'de skipped 114→2, 13 kor kirmizi gorunur oldu → [[kablo-da-kosuyor-demek-degil]]) ·
  K183 `77bb3195` (dispatch kendi grubunda, canli kabul YESIL, kosum `32176203099` 59 dk) ·
  K167 (defter durum kapisi) · 13 KOR KIRMIZI NOBETCI'nin SAHIPLIK dagilimi (6'si KraL DISI).
- 🟠 **T3 (`8ca4c716`, CI success) + T4 (`893d278d`) + T5 (`f07b40aa`) KURULDU:** ucu de SERIT B'de, `MUTANT=4/4`; T3'te DORT curutme "hedef kol oldurulunce mutant SESSIZ" verdi (C2 KENETLIYDI → `T3-EV-GECERSIZ` ayrildi), `DEVREDILDI` izi yaziliyor (yazilamazsa fail-closed); T4+T5'te ayrica `CURUTME=4/4`.
  ACIK: T3 `SAHIPSIZ=44` · T4/T5 canli kablo BILEREK YOK (Okan kapisi) · **T5 gercek defterde 7/7 `OLCULEMEDI`: kalemde HAREKET DAMGASI YOK** → damga alani ayri dilim, T5 canli veride olcemez.
- 🔧 **K179 (18 Agu):** `RECETE=9 REDDEDILEN=8 EVREN=390`; kalan 6 RED gercek. Hukum `tools/paket-k179-recete-ayiklama.md`. kabul: `AYIKLANAMADI` ayri kova + 3 mutant.
- 🔧 **K182 (18 Agu — SINIF, bugun UC KEZ cikti):** mutant "kirmizi geldi" diye kanit
  sayiliyor ama kirmizinin SEBEBI hedef kol mu olculmuyor (recete M1 · K178 tek eksen ·
  ③g M5). kabul: her mutant, hedef kolu oldurdugunu AYRICA kanitlar.
- 🔧 **K176 (18 Agu, OLCULDU — D1 yazici kilidi mesaji YANLIS PID basiyor):** `d1-sync.py:157`
  `os.getpid()` — ENGELLENEN surecin pid'i, TUTANIN degil; MaCiT'i 4 tur hayalet kovalatti.
  Yayini BLOKLAMAZ. kabul: mesaj tutani basar ya da "OLCULEMEDI" der + mutant.
- ⛔ **Dal `origin/k152-link-temiz` MERGE EDILMEYECEK (olculdu):** main'in atasi DEGIL, merge 76 dosya / −20.339 satir geri sarardi; icerik zaten `83aaf4e2` ile main'de. SILINEBILIR.
- 🔧 **K171 (18 Agu, MaCiT→KraL DEVIR; PAKET HAZIR `cc6fece2`, icra bekliyor):** gizli kaynak
  duzleminde 15 artik kayit; kanonik arac o duzleme dokunmuyor. Hukum+kabul
  `tools/paket-k171-kaynak-temizle.md`de; tam metin ARSIVDE.
- 🔧 **K135 (17 Agu, MaCiT→KraL):** `cgt-ekle.py::fetch()` tek satir UA ile CGTrader WAF'ina takiliyor (HTTP 202 + placeholder);
  Tam metin ARSIVDE.
  Kalici `--yerel` yolu KraL'da, sonraki dilim oncesi. `kabul:` alani BOS.
- 🔵 **K136 (17 Agu, KAYIT):** ana agacta `tools/marka-uyelik-test.py` BES oturumdur
  commit'siz (K126 "tek govde" yuklemini ham donguye geri aliyor). DOKUNULMADI.
- 🟠 **K139 (17 Agu, Okan emri — CANLI DURUM, ekip bilmeli):** crontab'ta 3 gorev
  yorumlandi; 181 → **25 atesleme/gun**. 🔴 ETKI: posta kutusu OTOMATIK izlenmiyor **ve
  urun partileri kendiliginden ILERLEMIYOR**. Tam metin ARSIVDE. `kabul:` alani BOS.
- 🟠 **K144 (UCUSTAKI KOSUM):** ardarda push'lar build'i `cancelled` ediyor (ARIZA DEGIL);
  hukum her turda guncel uca tasiniyor. Tam metin ARSIVDE.
  kabul: guncel ucu ICEREN kosum `conclusion=success` **VE** cache-bust'SIZ canli teyit.
- 🔧 **K140 (17 Agu — ACIK SORU MIMARCA KAPATILDI, icra kaldi):** hukum **kapinin MODEL hatasi degil, EVREN KAYNAGI hatasi**: 185 urunun 184'unde model jetonu gercek markanin YANINDA, ve `index.html:3148` cip evreni KURATORLU (model kodu CIP OLMAZ) → kapi sitede OLMAYAN bir baglanti icin sayfa istiyor.
  Tam metin ARSIVDE.
  kabul: `python3 tools/marka-invaryant-kapisi.py` — 7 model jetonu DUSMUS **VE** `Rover` DURUYOR **VE** mutasyon 4/4.
- 🔧 **K163 (17 Agu — K149'un ARTIGI, fail-silent sinifi):** `isci-temizlik.py:168-169` ciplak
  `except OSError: pass`; 45/63/125'te listeleme hatasi `return 0` ile "olculemedi"yi 0 okuyor.
  Tam metin ARSIVDE. kabul: `grep -c "except OSError: pass"` → **0** VE `OLCULEMEDI` isareti.
- 🔴 **K162 (17 Agu — canli turun profili "CANLI" sayilmiyor; tur cokme riski):** profil adi
  `profil-<MODEL>-<ETIKET>` iken canli kontrol `pgrep` ciktisinin SON token'ini karsilastiriyor.
  Tek koruma 2 saatlik tazelik penceresi. Tam metin ARSIVDE. kabul: canli tur fiksturuyle
  profil silinmez **VE** mutant KIRMIZI yakar.
- 🔴 **K157 (17 Agu — kimi hatti kok neden BULUNDU, karar OKAN'DA; 22 Agu'ya kadar KAPALI):**
  tam metin ARSIVDE. ⚖️ Okan emri: yeni olcum turu ACILMAZ; motor plani 20 Agu'ya kadar
  codex (alt model), sonra m3. kabul: 22 Agu'da nabiz `SAGLIK=YESIL` ise kapanir.
- 🔵 **K158 (17 Agu, TASARIM ACIGI — KAYIT):** isci tarayicisi YALNIZ kimi motorunda var
  (m3'te yok) → kimi dustugunde paneli okuyacak yol da kapaniyor; tek tarayicili motorun
  dususu TESHIS yolunu da kesiyor. Yon: tarayiciyi motordan bagimsiz kola tasi. `kabul:` BOS.
- 🔧 **K146 (17 Agu — nobet dosyalari YEDEKSIZ):** `~/.claude/cron/` versiyon kontrolu
  DISINDA → curutucu, iscinin kabul-testi fiksturunu MESRU mu degistirdi OLCEMEDI
  (eksen KOR). Yon: otomatik yedek + `yedekle.py` kapsam teyidi. `kabul:` alani BOS.
- 🔧 **K142 (17 Agu, KraL olctu → MaCiT):** pre-push kapak taramasi **14 R2 anahtari `NoSuchKey`** buldu, hepsi `c3d*` onekli (Cults3D partisi).
  Tam metin ARSIVDE.
  kutuya yazildi. Sahibi veri seridi. `kabul:` alani BOS.
- 🔧 **K118:** pre-push sizinti kapisi bicim-kaydiran urun partisinde butceyi yapisal
  asiyor (tam-dosya diff). Yon: butce buyutmek DEGIL, `urunler.json`'u icerik ekseninde
  AYRI ele almak. `kabul:` alani BOS.
- 🔴 **K104 / K104B:** nobet sicili + iki kapi main'de kirmizi. HUKUM MIMARDA. · **K99**
  bag kolonu · **K100** satir-sonu muafiyeti · **K102** yasakli ic dosya adi.
- 🟠 **K152 (17 Agu — ⚖️ OKAN KARARI KAPSAMI BELIRLEDI; onceki iki hukum de DUSTU):** Okan (birebir): **"sitede bulunan tum urunler satilabilir.
  Tam metin ARSIVDE.
  kabul: `python3 tools/koken-bul.py --eksik` → `EKSIK` DUSER **VE** `--kendini-test` rc=0.
- 🔧 **Iki acik kapi kalemi:** (a) shop bayatlik alarminin TETIK ekseni raporladigi bundle
  evreniyle AYNI DEGIL; (b) `devam-sinif-kapisi.py` is-akisi muafiyeti `norm`/`ham`
  ekseninde ayrisiyor. · 🟠 **K122:** `kurtarma/k122-yabanci-is` dali DURUYOR — peer'in dusurulen commitsiz isi
  (deploy.yml serit tasima · marka-uyelik-test.py · kalibrasyon 4 dosya). Sahibi uygulayacak.
- 🔧 **K151 (yedek dusus beyani her rotasyonda ELLE yeniden yaziliyor; sinif):** karantina
  cozuldu (dususler MESRU olcuLdu, arsivler dususten FAZLA buyudu). Beyan TAM boyuta bagli
  → 3. tekrar. **Yon:** ROTASYON CIFTI invaryanti. Tam metin ARSIVDE.
- 🔧 **K161 (17 Agu — marka dili KIP ekseni KAPANDI, KALINTI ayri parti):** kapi kapsaminda ama Okan onayli kalip tablosu DISINDA kalan **ELLE=10** kayit + karma cumle yuzunden bilerek atlanan 1 kayit. Kural dokumu, id'ler ve gerekce POSTA KUTUSUNDA. kabul: `python3 tools/denetim-kapisi.py --tum-katalog --envanter` vurus ≤21.





## OKAN'DA

- 🔧 Eski yedek klasorunu backup-v2 icine tasima · K89 olcum eylemi silme karari.
  (16 Agu: rotasyon bunu bir kez arsive supurdu, geri konuldu; sinif kusuru K128.)
- 🔧 **TARIFE KARAR KURALI (olculdu, onaya hazir):** mevcut $20 plan KALIR. Haftalik kota %80'e yaklasirsa ikinci saglayicinin $39 basamagi TERCIH EDILIR — ayni para bandinda hem kota hem **ikinci saglayici** (429/kesinti/kota duvarinda yedek) verir; mevcut saglayicinin $50 basamagi yalniz kota verir, tek-saglayici riski surer. Ikinci saglayici bekleme listesindeyse tek uygulanabilir yol $50 (0 kod degisikligi). Ust basamagin iki "deneysel" ozelligi bizim hatta GIRMEZ — biz yalnizca Anthropic-uyumlu API ucundan MODEL cagiriyoruz. Kota sayilari iki adayda da yayimlanmiyor, yani secimi fiyat degil CESITLILIK belirliyor. Ekleme bedeli motor basina 6 kod noktasi.
- 🔧 **22 Agu:** kimi/codex motor karari (K157) · $100 plan karari (once yanma olcumu).
- 📅 **20 Agu (TAKVIM, Okan emri 18 Agu):** CLAUDE.md'deki codex istisna blogu (⏳ 17→20 Agu)
  SILINECEK; ayni gun `codex-tam-yol` hafiza satiri da arsive tasinabilir.
- Olculen maliyet tabani: $18,72 / 1.081.021.287 token / 8.639 istek = yaklasik $17,3/milyar; $20/ay ve yaklasik 4,6 milyar/ay = yaklasik $4,3/milyar.





## ARSIVDE (tam metinler `DEVAM-ARSIV.md`'de)
14-15 Agu saatlik CI nobeti turlari · 15 Agu gece oturum kapanisi · K101/K103 kapanislari · yayin ve odeme etiketi bloklari · dorduncu motorun hatta baglanmasi · HD/Kawasaki/Ducati ekleme bloklari · sabah oturumunun tam olcum blogu · defterin sikistirma oncesi 196 satirlik tam hali · 17 Agu ROTASYON-2 (K147 · K154 · K155 · K156 · K133 · K91 · K101 · K103 · K113-119 · K120 · K123-125 · K128 · K121 · K127 · K138 · K137).