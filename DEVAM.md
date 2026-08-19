# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔁 DEVIR — 19 Agu 2026 22:1xZ, eski hesap → yeni hesap (KraL)
**SIRADAKI TEK IS:** Uc hazir dali merge kapisindan gecirip main'e al — `kral/n1-gozcu-kablolama`
`fd6b6d8d` · `kral/n2-kirleten-onarir` `a87f1809` · `kral/k184-talep-sihirbazi` `f623d712`.
**Nerede kaldim:** main=origin `83dab393`, ana agac TEMIZ. Bugun canliya: K190 `4340c0b9` ·
K216 `8634bc49` · K206 `7ce644ae` · K223 `9965c4fb` · K212 `df7425ea` · K224 (isci hatti) ·
shop worker Okan'in deploy'uyla taze (`5606ffbe`, TALEP_SAYAC KV bagli) · D1 bes eksen YESIL.
🟢 **N1 KABLOLAMASI CANLI** (cron repo disi): `crontab` gozcu `8,23,38,53` (15 dk) + `ci-nobeti.sh`
artik once `nobet-tetik.py --karar` kosuyor; kalp `22:08Z` (1 dk taze). Dal merge BEKLIYOR.
**Acik worktree/dal:** 3 agac, ucu de TEMIZ ve chip'leri kapandi — `nostalgic-noyce`(N1) ·
`magical-mcclintock`(N2) · `optimistic-blackburn`(K184); merge sonrasi kapatilacak. Ayrica
`kral/k195-defter-rotasyon` (DEVAM.md CAKISMASI var, once cozulecek) + `kral/k214-motor-tek-kaynak`.
**Baskasinin calisma kopyasinda duran:** YOK (uc agac da porcelain temiz).
**Zamanlanmis nobetler:** `7 * * * *` ci-nobeti.sh (⚠️ `.ci-token`'a BAGLI — yeni hesapta ILK IS
tazelemek) · `8,23,38,53 * * * *` gozcu.py (deterministik) · `41 6` kota-olcum · `10 9`/`10 21`
kimi-nabiz. Scheduled-tasks KAYITLARI hesapta yasar → yeniden kurulacak.
**Okan'da bekleyen karar:** yok (shop deploy bugun yapildi; K200(i) canli `--kuru --d1` duruyor).



## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)
- 🔴 **K212 (SeritB chip'i buldu — `tools/yedekle.py` iki GERCEK kusur, BEKLETMEDE):** tam metin
  + kabul ARSIVDE. Ayri kalem; onarim SeritB kapsaminda DEGIL.
- ✅ **19 AGU KAPANANLAR — K186 · K205 · K210 · K211 · K190 `4340c0b9` · K215/K80 · SeritB `d46747d0` · K224** (tam bloklar ARSIVDE + kutuda). · 🟠 **K209 kalintisi (KAPANDI, ARSIVDE):** `33b663e4` canlida degil; care ikinci `wrangler deploy` (Okan).
- 🔴 **MOTOR KARARI (Okan, 19 Agu aksam — LUNA EMRINI GECERSIZ KILAR):** kapali kume `minimax-m3 kimi claude`; deepseek/codex/luna **RED** (K224'te uygulandi, cron kimi'de kaldi).
- 🔧 **K200 (saklama YURURLUKTE — TAM METIN ARSIVDE):** (i) canli `--kuru --d1` ⚖️ OKAN KAPISI ·
  (ii) periyodik kablolama MIMARDA · (iii) kablolamanin KOSTUGU kanit. Sira: sema→tesisat→trafik.
- 🔴 **K213 (19 Agu, MaCiT olctu → hukum KraL'da, sahibi MaCiT):** CC BY/BY-SA **50 kayitta**
  `lisans.tasarimci` yer tutucu (`?` 49 + `...` 1) → canlida atif KOSULU karsilanmiyor.
  HUKUM KUTUDA (4 madde: urun CEKILMEZ + `lisans` SILINMEZ · ad KAYNAKTAN · kurtarilamayanda
  K27'nin dar kaynak-LINKI kolu · 2. vaka oldugu icin KALICI fail-closed KAPI).
  kabul: kapi + mutant + ihlal sayisi duser + `denetim-kapisi` yesil.
- 🔧 **K199 (19 Agu, KraL):** `is-akisi-kapisi.py` "etkili tasiyici" tanimi LITERALE capali;
  varlik turetilmis mekanizmaya gecince korlesiyor (K193). Care: sonucu olc ya da makine-okunur
  beyani tasiyici say; mutant + negatif vaka sart. · 🔧 **K201 SINIF: KAYIT KENDINI OLCMEZ** — bes vaka;
  her kayit ya TURETILIR ya kendi sayisiyla KABUL EDILIR, "EKLE" yetmez SAYI sart.
- 🔧 **K196 (DEPO GENELI):** CI node 20 / yerel 25.8.1 → yerel JS yesilleri CI surumunde OLCULMEMIS. ARSIVDE.
- 🔧 **K197 (19 Agu):** pre-push maliyet beyani 3,16 sn diyor, olculen medyan **6,11 sn** (5 sn esigi asilmis); sayiyi YORUM soyluyor, dogrulayan yok. ARSIVDE.
- 🔧 **K217 (19 Agu, KraL push ciktisinda OLCTU):** tavan nobetcisi, baska kapinin self-test fiksturlerini
  (temp `pruvo-kapi-test-*`, detached, saniyelik) MIMAR sayip sahte `TAVAN ASILDI SAYI=3` yaziyor (kanit: `ls`
  iki dizini YOK gosterdi, saniyeler sonra BASKA iki fikstur listelendi); yordam "kaldir" dedigi icin GERCEK
  agac silinebilir. kabul: fikstur duzlemi sayimdan DUSER + mutant hedef-kol atfi + gercek 3. agac YAKALANIR.
- 🔧 **K189** (`ci-kapsam-test.py` hukum ekseni; kabul: aday>0 iken `OLCULEMEDI`+sifir-disi rc +
  ayri jeton + mutant hedef-kol atfi) · 🔧 **K191** (tarama SPEC'i isi ONCULDEN aliyor; sahibi
  MaCiT; kabul: ILK blok KAPSAM ON-OLCUMU + tazelik capasi). **Ikisinin tam metni ARSIVDE.**
- 🟠 **K184 — TEK KALEM:** dal `867cc80e` origin'de, K80 ARTIK BLOKLAMIYOR; kalan kirmizi
  `talep-sihirbazi-test.py` VAKA 36 (batarya kabuk metnini olcuyor, adim araca tasindi).
  Kalan is + delege plani POSTA KUTUSUNDA. Uc daldan CIKTI; HocA E6 dumani bu merge'e bagli.
- 🔧 **K192** (Okan: kalem ac DOKUNMA): `kimi` KURULU kapisinda YOK, dagitim kaniti VARLIK olcuyor. ARSIVDE.
- 🔧 **K202-kendini-test** (M06 cokme + bayat capa) — 🔴 SAHIPSIZ: SeritB chip'i "bende HIC olmadi" diye olctu (onun uyesi K203'tu, YESIL kapandi). kabul: capa govdeden count==1, `beklentiyi tutmayan: 0`.
- 🟠 **K206 (TeKiN→KraL; 3 KARAR VERILDI, icra chip'i sirada):** 8 uretec sari seriye — saklama AYRI
  AILE · gyro `doku=duz` · 8 fiyat ONAY (280/190/170/350=TAVAN/160/240/140/220); kupler render CELISKILI.
  PAKET main'de (`7ce644ae`). kabul (icra): ONIZLEME_AILELER 22→30 · taban-fiyat 21→29 · +8 sari kayit · 8 gorsel R2 200 · parite yesil.
- 🔴 **K222:** `uzlastirici-onarim.py:161` `if rc == 0`, `:178` bayatlik kolundan ONCE; kapi yazmayi
  bloklayip rc=0 donunce surucu "ONARILDI" cikiyor (`32272271453`). kabul: imza varsa TEKRAR
- 🔧 **K220 (KraL):** `marka_yazimlari()`+`taninmis_mi()` TEK listeden besleniyor; liste iki rol tasiyor
  ("baslikta aranan ad" + "MODEL OLAMAZ jetonu"). Range Rover'i markaya yazmak CANLI `/marka/land-rover/range-rover/`
  sayfasini (6 urun) OLDURUYOR — ayrilmadan dokunma. Girdi: K216 raporu EK + `arama.py:2201`. SIRA: D bitti, sirada A.



## KraL ACIK ARTIKLAR (19 Agu anlati blogu ARSIVE TASINDI; kota uyarisi da orada)
🔧 **K203:** tavan kapisi worktree ICINDEN rol eksenini kaybediyor (sebep onek DEGIL cagri baglami);
K223'un FIKSTUR kovasi fikstur eksenini kapatti, ROL ekseni ACIK. · 🔧 **K204:** `OKSUZ` fiilen
"kirli mi" olcuyor, TEK BASINA kaldirma gerekcesi DEGIL. · 🔧 **K188:** yarim yedek OLCULEBILIR;
kabul `YEDEK=TAM/YARIM` jetonu + fikstur.
- 🔴 **T1 pencere muhasebesi + T3/T4 kaniti:** `OLCULEMEDI_TUR=2` ayri satir; nobet kosuyor ama `ONARIM=0`, 10 kalem MIMAR'da. **Tam metin ARSIVDE.**
- 🔧 **K195 (19 Agu — 4. TEKRAR):** `defter-rotasyon.py` kapali madde yokken TASIMIYOR → kota her oturumda ELLE rotasyon istiyor. **Tam metin ARSIVDE.**
- 🔧 **K198 (19 Agu — ⚖️ OKAN KAPISI):** izlenen yapilandirmada ticari alan var, nobetci o duzlemi
  taramiyor (muafiyette de yok). **Tam metin ARSIVDE.** kabul: OLCER ya da `KAPSAM DISI` + mutant.
- ✅ **19 Agu KAPANANLAR: liste ARSIVDE.** **KALAN ACIK ARTIKLAR:** T3 `SAHIPSIZ=44→24 (Onarim
  dali olctu)` · T4/T5 canli kablo (Okan kapisi) · T5 hareket damgasi 7/7 `OLCULEMEDI` ·
  K188 kancasi BAGLI DEGIL · Escape olcumu yok — hepsi chip'lerde.
- 🔧 **K179 (18 Agu):** `RECETE=9 REDDEDILEN=8 EVREN=390`; kalan 6 RED gercek. Hukum `tools/paket-k179-recete-ayiklama.md`. kabul: `AYIKLANAMADI` ayri kova + 3 mutant.
- 🔧 **K182 (18 Agu — SINIF, bugun UC KEZ cikti):** mutant "kirmizi geldi" diye kanit
  sayiliyor ama kirmizinin SEBEBI hedef kol mu olculmuyor (recete M1 · K178 tek eksen ·
  ③g M5). kabul: her mutant, hedef kolu oldurdugunu AYRICA kanitlar.
- 🔧 **K176:** D1 kilit mesaji YANLIS PID basiyor (`d1-sync.py:157`); yayini bloklamaz. kabul: tutani basar ya da OLCULEMEDI + mutant. · ⛔ **`origin/k152-link-temiz` MERGE EDILMEYECEK** (main atasi degil; icerik `83aaf4e2`de) — SILINEBILIR.
- 🔧 **K171 (18 Agu, MaCiT→KraL DEVIR; PAKET HAZIR `cc6fece2`, icra bekliyor):** gizli kaynak
  duzleminde 15 artik kayit; kanonik arac o duzleme dokunmuyor. Hukum+kabul `tools/paket-k171-kaynak-temizle.md`de.
- 🔧 **K135 (17 Agu, MaCiT→KraL):** `cgt-ekle.py::fetch()` tek satir UA ile CGTrader WAF'ina takiliyor (HTTP 202 + placeholder);
  kalici `--yerel` yolu KraL'da, sonraki dilim oncesi. Tam metin ARSIVDE. `kabul:` alani BOS.
- 🔵 **K136 (17 Agu, KAYIT):** ana agacta `tools/marka-uyelik-test.py` BES oturumdur
  commit'siz (K126 "tek govde" yuklemini ham donguye geri aliyor). DOKUNULMADI.
- 🟠 **K139 (17 Agu, Okan emri — CANLI DURUM, ekip bilmeli):** crontab'ta 3 gorev
  yorumlandi; 181 → **25 atesleme/gun**. 🔴 ETKI: posta kutusu OTOMATIK izlenmiyor **ve
  urun partileri kendiliginden ILERLEMIYOR**. Tam metin ARSIVDE. `kabul:` alani BOS.
- 🟠 **K144 (UCUSTAKI KOSUM):** ardarda push'lar build'i `cancelled` ediyor (ARIZA DEGIL);
  hukum her turda guncel uca tasiniyor. Tam metin ARSIVDE.
  kabul: guncel ucu ICEREN kosum `conclusion=success` **VE** cache-bust'SIZ canli teyit.
- 🔧 **K140 (17 Agu — hukum verildi, icra kaldi):** kapi EVREN KAYNAGI hatasi (cip evreni kuratorlu). Tam metin ARSIVDE. kabul: `marka-invaryant-kapisi.py` 7 jeton DUSMUS + `Rover` DURUYOR + mutasyon 4/4.
- 🔧 **17 Agu KALEMLERI (tam metinleri ARSIVDE, kabul satirlari orada):** **K163** fail-silent ciplak
  `except OSError: pass` · **K162** canli turun profili CANLI sayilmiyor (tur cokme riski) · **K157**
  kimi hatti (⚖️ Okan: 22 Agu'ya kadar KAPALI, yeni olcum turu ACILMAZ) · **K158** isci tarayicisi
  yalniz kimi'de · **K146** nobet dosyalari yedeksiz · **K142** 14 R2 anahtari `NoSuchKey` (MaCiT) ·
  **K118** pre-push kapisi bicim-kaydiran partide butceyi yapisal asiyor.
- 🔴 **K104 / K104B:** nobet sicili + iki kapi main'de kirmizi. HUKUM MIMARDA. · **K99**
  bag kolonu · **K100** satir-sonu muafiyeti · **K102** yasakli ic dosya adi.
- 🟠 **K152 (17 Agu — OKAN KARARI kapsami belirledi):** "sitede bulunan tum urunler satilabilir." Tam metin ARSIVDE.
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
- 🔧 **TARIFE KARAR KURALI (olculdu, onaya hazir):** $20 KALIR; kota %80'e yaklasirsa ikinci saglayicinin $39 basamagi ($50 tek-saglayici yerine CESITLILIK). TAM GEREKCE ARSIVDE.
- 🔧 **22 Agu:** kimi/codex motor karari (K157) · $100 plan karari (once yanma olcumu).
- Olculen maliyet tabani: $18,72 / 1.081.021.287 token / 8.639 istek = yaklasik $17,3/milyar; $20/ay ve yaklasik 4,6 milyar/ay = yaklasik $4,3/milyar.
- 🔧 **ODEME WORKER DEPLOY (19 Agu 16:29Z):** pruvo-shop bayatlik nabzi KIRMIZI (134,1 dk / esik 120); yayinlanmamis TEK fark `0f590d11` icindeki `shop/src/talep.js` YORUM satiri, davranis farki YOK. Kapatan eylem `npx wrangler deploy` = OKAN KAPISI. Detay ci-nobeti.log.




## ARSIVDE (tam metinler `DEVAM-ARSIV.md`'de)
14-15 Agu saatlik CI nobeti turlari · 15 Agu gece oturum kapanisi · K101/K103 kapanislari · yayin ve odeme etiketi bloklari · dorduncu motorun hatta baglanmasi · HD/Kawasaki/Ducati ekleme bloklari · sabah oturumunun tam olcum blogu · defterin sikistirma oncesi 196 satirlik tam hali · 17 Agu ROTASYON-2 (K147 · K154 · K155 · K156 · K133 · K91 · K101 · K103 · K113-119 · K120 · K123-125 · K128 · K121 · K127 · K138 · K137).