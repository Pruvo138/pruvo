# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.
## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)
- 🔴🔴 **ONARIM HATTI = BIRINCI ONCELIK (Okan, 19 Agu ~11:3xZ).** `ustuste_onarimsiz=59` ·
  ci-nobeti cron DISI, `gozcu.py --tur` saatlik :23 CANLI (kalp 08:23Z; kat_mimar=10 · isci=1) ·
  T1 penceresi **20 Agu 08:48Z BITIYOR**, `t1-kiyas.py` DALDA · SERIT B **18 Agu 11:23Z'den beri
  KIRMIZI** (32201776934: 7 job/16 adim; addc0051'e ozgu degil). Chip'ler: Onarim-merge
  (ea423a0c→main, merge-kapisi) + SeritB-teshis (salt teshis).
  Onarim dalinin 3 ACIK mimar konusu: T6 durum-dosyasi ekseni (hukum: T5 dosyasi GENISLETILIR,
  fail-closed) · T5/T6 kendini-test flakiness · merge-kanit KANITSIZ=27 dolum turu.
- 🔴 **LUNA EMRI (Okan, 19 Agu): codex kota %100 — TUM etkilesimli isciler `gpt-5.6-luna`;**
  tavanlar KALKTI; kimi/m3 YEDEK; cron hatti kimi'de. AGENTS.md + kutu duyurusu yazildi.
- 🔴 **K186 `74d6cfcd` MERGE EDILMEZ — "bayat taban" hipotezi CURUTULDU, iki kirmizi da K186'nin
  KENDI kusuru** ((b) chip'i olctu; kapi betikleri iki ucta BIREBIR → sebep VERI): ① haritada
  `tools/talep-temizlik.py` satiri YOK (`EKSIK=1`) ② `nobet.yml` 366/368/372 adimlarinda
  `if: !cancelled()` YOK (`MASKELEYEN=3`, komsularin hepsinde var). Merge cakismasi tek dosya
  `nobet.yml` (capa; kabul: her `- name:` birlesimde TAM 1 kez, adim=main+3). Yan bulgu: bayat
  taban K186'nin LEHINEYDI — tazeleme kirmizi EKLER. **ONARIM RECETESI (3 madde) kutuda; sonra
  (b) KOSUMLA kapanir.** K184 → K190 sirada. **→ 19 Agu: ONARIM KAPANDI `aa40200f` (kabul-4 ✅✅✅; onizleme
  `4b27f054` YESIL: EKSIK=0 · MASKELEYEN=0 · adim 270=main+3). MERGE ICRASI Onarim-merge
  chip'ine devredildi — sira: stoic-albattani → K186.**
- 🔧 **K200 (19 Agu, YENI — saklama YURURLUKTE):** K190 "arac dogru"yu, K200 "saklama fiilen
  isliyor"u iddia eder. (i) canli `--kuru --d1` **⚖️ OKAN KAPISI — uc yol da OLCULEREK kapali,
  gerekce KUTUDA**; "chip kosturur" PLAN DEGIL. (ii) periyodik kablolama (MIMARDA, K198
  arkasinda), (iii) kablolamanin KOSTUGU kanit (zaman damgali iz + tetiklenmezse KIRMIZI).
  Sira: sema, tesisat, trafik.
- 🔧 **K199 (19 Agu, KraL):** `is-akisi-kapisi.py`'nin "etkili tasiyici" tanimi LITERALE capali;
  varlik turetilmis mekanizmaya gecince kapi korlesiyor (K193'te olctuk). Kalici care: sonucu olc
  ya da makine-okunur beyani tasiyici say. Mutant + negatif vaka sart. · 🔧 **K201 SINIF: KAYIT
  KENDINI OLCMEZ** — bes vaka: K192 damga · K197 yorumdaki maliyet · K189'un kablo defteri (4 vs 5)
  · capa tablosu (18'de kaldi) · `--kendini-test 17` (dogrusu 12). Kural: her kayit ya TURETILIR
  ya kendi sayisiyla KABUL EDILIR; "EKLE" yetmez, SONUC SAYISI sart.
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
- 🟠 **K205 (19 Agu, YENI — K202 icrasi IKI SURUM, uzlastirma MIMARDA):** main'e giren `addc0051`
  (BASKA oturum itti; K19 bosaldi, deploy YESIL) ile chip'in 5/5-yesil surumu `4ed39e42`
  (dal `claude/priceless-lamport-4c2db5`, origin'e YEDEKLENDI) AYNI DEGIL: 3 dosya 75+/61−.
  Chip'te FAZLADAN: `rozet_capraz_sinif_imzasi()` kapisi (ROZET→BEKLER sessiz kaydirma korlugunu
  kapatir — kontrol mutanti buldu) + M-K202 mutanti. kabul: diff okunur, sinif-imza kapisi main'e
  tasinir, M-K202 main'de KIRMIZI/yesil dongusuyle kanitlanir. · 🔧 **K202-kendini-test** (chip
  olctu, TABANDAN geliyor): dalda 4 dusuyor (M06 cokme + M17/M20/M31 bayat capa), taban 20 —
  dal yeni kirmizi URETMEDI. kabul: capalar govdeden turetilir count==1, `beklentiyi tutmayan: 0`.
  **→ 19 Agu: diff MIMARCA OKUNDU, hukum verildi (deny/allow tablolari MAIN KANONIK — allow imzasi
  iki ucta ozdes `f3ccf9b717a42de5`; yalniz SINIF-IMZA kapisi + M-K202 tasinir; sabit main'de
  YENIDEN turetilir, mutant capasi main govdesinden count==1). TASIMA CHIP'I PANELE KONDU.**
- 🟠 **K206 (19 Agu, TeKiN→KraL; 3 KARAR VERILDI, icra chip'i sirada):** 8 uretec sari seriye.
  Kararlar: saklama AYRI AILE · gyro site semasinda `doku=duz` (.scad degismez) · 8 fiyat ONAY
  (280/190/170/350=TAVAN/160/240/140/220). ⚠️ kupler render guncelligi RAPORDA CELISKILI — chip
  OLCECEK. kabul: ONIZLEME_AILELER 22→30 · taban-fiyat-tablosu 21→29 · urunler.json +8 sari
  kayit (parametrik:true, fiyat:"") · 8 gorsel R2'de 200 · kategori-parite yesil.

## KraL SON DURUM (19 Agu ~12:0xZ; eski kapanis blogu ARSIVDE)
✅ **K190+K187 KAPANDI — MIMARCA TEYIT** (`kral/k190-canli-temizlik` `91479a60`): `22/22`,
K187 `KV=4/4`. Merge K186 arkasinda; kalan tek kalem K200(i). · 🔧 **K203:** tavan kapisi worktree
ICINDEN rol eksenini kaybediyor (sebep onek DEGIL cagri baglami). · 🔧 **K204:** `OKSUZ` fiilen
"kirli mi" olcuyor; TEK BASINA kaldirma gerekcesi DEGIL. · 🔧 **K188 yarim yedek OLCULEBILIR**
(`§7` izi buldu, pid 3594 YOK); kabul: `YEDEK=TAM/YARIM` jetonu + fikstur.
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
- 🔧 **K176 (18 Agu):** D1 kilit mesaji YANLIS PID basiyor (`d1-sync.py:157` engellenenin pid'i). Yayini bloklamaz. kabul: tutani basar ya da OLCULEMEDI + mutant.
- ⛔ **`origin/k152-link-temiz` MERGE EDILMEYECEK** (main atasi degil, −20.339 satir geri sarardi; icerik `83aaf4e2`de). SILINEBILIR.
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
- 🔧 **K140 (17 Agu — hukum verildi, icra kaldi):** kapi EVREN KAYNAGI hatasi (cip evreni kuratorlu). Tam metin ARSIVDE. kabul: `marka-invaryant-kapisi.py` 7 jeton DUSMUS + `Rover` DURUYOR + mutasyon 4/4.
- 🔧 **17 Agu KALEMLERI (tam metinleri ARSIVDE, kabul satirlari orada):** **K163** fail-silent ciplak
  `except OSError: pass` · **K162** canli turun profili CANLI sayilmiyor (tur cokme riski) · **K157**
  kimi hatti (⚖️ Okan: 22 Agu'ya kadar KAPALI, yeni olcum turu ACILMAZ) · **K158** isci tarayicisi
  yalniz kimi'de · **K146** nobet dosyalari yedeksiz · **K142** 14 R2 anahtari `NoSuchKey` (MaCiT) ·
  **K118** pre-push kapisi bicim-kaydiran partide butceyi yapisal asiyor.
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
- 🔧 **TARIFE KARAR KURALI (olculdu, onaya hazir):** $20 KALIR; kota %80'e yaklasirsa ikinci saglayicinin $39 basamagi ($50 tek-saglayici yerine CESITLILIK). TAM GEREKCE ARSIVDE.
- 🔧 **22 Agu:** kimi/codex motor karari (K157) · $100 plan karari (once yanma olcumu).
- 📅 **20 Agu (TAKVIM, Okan emri 18 Agu):** CLAUDE.md'deki codex istisna blogu (⏳ 17→20 Agu)
  SILINECEK; ayni gun `codex-tam-yol` hafiza satiri da arsive tasinabilir.
- Olculen maliyet tabani: $18,72 / 1.081.021.287 token / 8.639 istek = yaklasik $17,3/milyar; $20/ay ve yaklasik 4,6 milyar/ay = yaklasik $4,3/milyar.

## ARSIVDE (tam metinler `DEVAM-ARSIV.md`'de)
14-15 Agu saatlik CI nobeti turlari · 15 Agu gece oturum kapanisi · K101/K103 kapanislari · yayin ve odeme etiketi bloklari · dorduncu motorun hatta baglanmasi · HD/Kawasaki/Ducati ekleme bloklari · sabah oturumunun tam olcum blogu · defterin sikistirma oncesi 196 satirlik tam hali · 17 Agu ROTASYON-2 (K147 · K154 · K155 · K156 · K133 · K91 · K101 · K103 · K113-119 · K120 · K123-125 · K128 · K121 · K127 · K138 · K137).