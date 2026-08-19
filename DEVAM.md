# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.
## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)
- 🔴🔴 **ONARIM HATTI = BIRINCI ONCELIK (Okan, 19 Agu).** ✅ T-altyapisi `74475c70` CANLIDA
  (deploy 32235503924; `t1-kiyas.py` main'de — pencere 20 Agu 08:48Z, hukum BaBa'da).
  **SERIT B teshisi KAPANDI:** kirmizi 12 Agu 11:58Z'den beri; 22 dusen adim = **7 SINIF**,
  merge'ler HICBIRINI kapatmiyor; tablo+P1-P7 KUTUDA. DAGITIM: P1/P3/P4/P6/P7 + hijyen-a3 →
  `KraL-SeritB onarim` chip'i KOSUYOR (dal `kral/seritb-onarim`) · P2/P5 → MaCiT ·
  gozcu-eskalasyon → BaBa. Dalin 3 acik T-konusu suruyor (T6 · flakiness · KANITSIZ=27). ARSIVDE.
- 🔴 **K212 (19 Agu, SeritB-onarim chip'i buldu — `tools/yedekle.py` iki GERCEK kusur,
  BEKLETMEDE):** tam metin + kabul olcutu ARSIVDE (sinif kapisi geregi). Ayri kalem yurur;
  onarim SeritB chip'inin kapsaminda DEGIL.
- ✅ **19 AGU KAPANANLAR — K186 · K205 · K210 · K211** (SHA/kapi/deploy kanitlari + K202 devri ARSIVDE). K211'in SON teyidi HocA'da KAPANDI: `sqlite_master`=1 satir · PRAGMA=11 kolon · kod-sema sapmasi 0.
- 🔴 **K190 MERGE EDILMEDI — DAL-ICI KIRMIZI, TARIHLENDI (chip PANELDE):** `talep-hatti-test.py`
  rc=1 (50 iddia beklenirken 54 kostu · DUSEN L9 · D11 capasi ValueError) + `talep-temizlik.py
  --kendini-test` rc=1 (L9). Kok: dalin KENDI `76c8444f` (K187 KV) commit'i `talep.js:165`'i
  degistirdi, `ba6d9d77`'deki capa/beklenti guncellenmedi — main mb'den beri 5 dosyaya
  DOKUNMADI, birlesim SUCSUZ. Recete: D11 capasi bugunku govdeden + beklenti 50→54 + L9 ekseni.
  kabul: iki komut rc=0 + mutant hedef-kol atfi, sonra merge.
- ✅ **K209 KAPANDI — worker CANLI** (kanit ARSIVDE). 🟠 Kalinti ACIK: `33b663e4` (K210'un TEK
  yorum satiri, davranis AYNI) canlida degil → alarm 102,5/120 dk; care ikinci `wrangler deploy`.
- 🔴 **LUNA EMRI (Okan, 19 Agu): codex kota %100 — TUM etkilesimli isciler `gpt-5.6-luna`;** tavanlar KALKTI, kimi/m3 YEDEK, cron kimi'de. AGENTS.md + kutu yazildi.
- 🔧 **K200 (19 Agu, YENI — saklama YURURLUKTE):** K190 "arac dogru"yu, K200 "saklama fiilen
  isliyor"u iddia eder. (i) canli `--kuru --d1` **⚖️ OKAN KAPISI — uc yol da OLCULEREK kapali,
  gerekce KUTUDA**; "chip kosturur" PLAN DEGIL. (ii) periyodik kablolama (MIMARDA, K198
  arkasinda), (iii) kablolamanin KOSTUGU kanit (zaman damgali iz + tetiklenmezse KIRMIZI).
  Sira: sema, tesisat, trafik.
- 🔴 **K213 (19 Agu, MaCiT olctu → hukum KraL'da, sahibi MaCiT):** CC BY/BY-SA **50 kayitta**
  `lisans.tasarimci` yer tutucu (`?` 49 + `...` 1) → canlida atif KOSULU karsilanmiyor.
  HUKUM KUTUDA (4 madde): urun CEKILMEZ + `lisans` SILINMEZ · ad KAYNAKTAN doldurulur ·
  kurtarilamayanda K27'nin izin verdigi dar kolla kaynak LINKI (ucretli/uyelikli kayda SICRAMAZ) ·
  **2. vaka oldugu icin KALICI KAPI SART** (tarama/ekleme katmani, fail-closed).
  kabul: kapi + mutant + ihlal sayisi duser + `denetim-kapisi` yesil.
- 🔧 **K199 (19 Agu, KraL):** `is-akisi-kapisi.py` "etkili tasiyici" tanimi LITERALE capali;
  varlik turetilmis mekanizmaya gecince korlesiyor (K193). Care: sonucu olc ya da makine-okunur
  beyani tasiyici say; mutant + negatif vaka sart. · 🔧 **K201 SINIF: KAYIT KENDINI OLCMEZ** —
  bes vaka (K192 damga · K197 maliyet · K189 kablo defteri · capa tablosu · `--kendini-test`).
  Kural: her kayit ya TURETILIR ya kendi sayisiyla KABUL EDILIR; "EKLE" yetmez, SAYI sart.
- 🔧 **K196 (DEPO GENELI):** CI node 20 / yerel 25.8.1 → yerel JS yesilleri CI surumunde OLCULMEMIS. ARSIVDE.
- 🔧 **K197 (19 Agu, K189 chip olctu — YAYIN YOLU MALIYETI, RATCHET YOK):** pre-push kancasinin
  maliyet beyani 3,16 sn (9 Agu) diyor, **bugun olculen medyan 6,11 sn** → 5 sn esigi zaten asilmis;
  sayiyi YORUM soyluyor, dogrulayan yok. **Tam metin ARSIVDE.**
- 🔧 **K189** (`ci-kapsam-test.py` hukum ekseni; kabul: aday>0 iken `OLCULEMEDI`+sifir-disi rc +
  ayri jeton + mutant hedef-kol atfi) · 🔧 **K191** (tarama SPEC'i isi ONCULDEN aliyor; sahibi
  MaCiT; kabul: ILK blok KAPSAM ON-OLCUMU + tazelik capasi). **Ikisinin tam metni ARSIVDE.**
- 🟠 **K184 — MERGE CHIP'I PANELDE** (dal `kral/k184-talep-sihirbazi`, ucu chip olcer).
  🔴 MIMAR HUKMU 19 Agu: uc (`/talep` handler + kendi DDL'i) DALDAN CIKAR, yalniz istemci kalir;
  K186'nin semasi/ucu KANONIK (canli D1 K211 ile o semada) ve uctan uca olcum K186'nin ucune karsi
  YENIDEN kosulur. HocA E6 dumani bu merge'e bagli.
- 🔧 **K192** (Okan: kalem ac DOKUNMA): `kimi` KURULU kapisinda YOK, dagitim kaniti VARLIK olcuyor. ARSIVDE.
- 🔧 **K202-kendini-test** (M06 cokme + M17/M20/M31 bayat capa) = SeritB S1 uyesi, `KraL-SeritB
  onarim` chip'inde; kabul: capa govdeden count==1, `beklentiyi tutmayan: 0`.
- 🟠 **K206 (TeKiN→KraL; 3 KARAR VERILDI, icra chip'i sirada):** 8 uretec sari seriye — saklama
  AYRI AILE · gyro semasinda `doku=duz` · 8 fiyat ONAY (280/190/170/350=TAVAN/160/240/140/220);
  ⚠️ kupler render guncelligi CELISKILI, chip OLCECEK. kabul: ONIZLEME_AILELER 22→30 ·
  taban-fiyat 21→29 · +8 sari kayit (parametrik, fiyat boş) · 8 gorsel R2'de 200 · parite yesil.

## KraL SON DURUM (19 Agu ~15:xxZ; eski kapanis blogu ARSIVDE)
🧹 **TEMIZLIK (mimar eli, olculdu):** worktree **3→1** (yalnizca CANLI `gallant-shirley` =
SeritB onarim kaldi; `dreamy-mclean`+`suspicious-cerf` temiz+icerik-main'de kanitiyla silindi,
raporlari scratchpad'e yedeklendi) · **10 zombi yerel dal silindi** (`-d`, hepsi main'e merged).
✅ **K190+K187 mimarca teyitli** (`91479a60`): `22/22`, K187 `KV=4/4` — ama MERGE ICIN
onarim sart (yukarida). · 🔧 **K203:** tavan kapisi worktree
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
- 🔧 **K176:** D1 kilit mesaji YANLIS PID basiyor (`d1-sync.py:157`); yayini bloklamaz. kabul: tutani basar ya da OLCULEMEDI + mutant. · ⛔ **`origin/k152-link-temiz` MERGE EDILMEYECEK** (main atasi degil; icerik `83aaf4e2`de) — SILINEBILIR.
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
- ✅ **20 Agu TAKVIMI ERKEN KAPANDI (Okan emri 19 Agu, chip `KraL-Hijyen`):** CLAUDE.md'nin iki tarihli codex blogu ARSIVE tasindi, yasayan motor kurali TEK SATIR kaldi; `codex-tam-yol` hafiza satiri YASIYOR (codex birincil oldu), tasinmadi.
- Olculen maliyet tabani: $18,72 / 1.081.021.287 token / 8.639 istek = yaklasik $17,3/milyar; $20/ay ve yaklasik 4,6 milyar/ay = yaklasik $4,3/milyar.

## ARSIVDE (tam metinler `DEVAM-ARSIV.md`'de)
14-15 Agu saatlik CI nobeti turlari · 15 Agu gece oturum kapanisi · K101/K103 kapanislari · yayin ve odeme etiketi bloklari · dorduncu motorun hatta baglanmasi · HD/Kawasaki/Ducati ekleme bloklari · sabah oturumunun tam olcum blogu · defterin sikistirma oncesi 196 satirlik tam hali · 17 Agu ROTASYON-2 (K147 · K154 · K155 · K156 · K133 · K91 · K101 · K103 · K113-119 · K120 · K123-125 · K128 · K121 · K127 · K138 · K137).