# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔁 CANLI DURUM — 25 Agu 2026 (KraL)
**24 Agu: 12 merge** (K260·K256/K269/K276·K271·K268·K280·K284·K285·K86), D1 alti eksen YESIL,
rotasyon 374 turdur calisir halde (K268 acti). Curuyen: **K281** (`KILIT_MUMKUN=0`).
✅ **OKAN'IN 18:04 KIRMIZISI KAPANDI:** `BAGLAM_KANIT TASINAN=1 KAYIP_KURAL=0` — 15 hedefin 13'u
o gun HIC degismemis (mtime), yani 1 blok TASINDI, 14'un okuyucusu ZATEN vardi. Tam metin KUTUDA.
🔴 **ACIK:** K286 (K80 nobetcisi YORUM satirini cagri sayiyor) · K287 (birim-saglik buyuk sapmayi
kaciriyor; kabul: buyuk-uc esigi + mutant).
📌 **BICIM:** nobet hukmu TUR NUMARASIYLA yazilir (`HUKUM=<hal>@tur<N>`).
- 🔧 **K288 (25 Agu, Okan: "olcumu chip'e ver, tavani sonra"):** `isci.log` tur basina token
  TASIMIYOR → baglam kucultme talimatinin OKUYUCUSU yok. kabul: tur basina tuketim satiri +
  kaynak mutabakati + dusen turda `OLCULEMEDI` (sahte sifir YOK) + mutant. TAVAN BU TURDA YOK.
  Olculen sayilar ve gerekce HAFIZADA (`sabit-kota-vs-token-tarifesi`).
**Okan'da:** ① gecmis temizligi · ② K200(i) · ③ CLAUDE.md tavan ONERISI · ④ K284 canli dogrulama.
- 🔴 **K255 (SINIF, 3.):** etiket bir kapida ONEK, otekinde TOKEN; `panel-k236` RED, `tarayici-kabul-k236` GECTI. KUTUDA.
- 🔴 **K257 (Okan) — CHIP ACILDI 20 Agu (`KraL-K257Merdiven`):** merdiven m3(2)→kimi(1)→mimar(1)→KraL→BaBa→Okan;
  sayac ISLE TASINIR, kapi reddi YUKARI CIKMAZ. BaBa basamagi = hukum/teshis, sayaca dahil DEGIL (24s SLA). KUTUDA.
- 🔧 **K245** bitis satiri isci ciktisinda belirir · 🔧 **K240**
  kapi yardim metni bayat · 🔴 **K245 2. YUZ:** satir kutuya duser, SON PANEL MESAJINA dusmez ·
  🔧 **K241 (SINIF, UC YUZEY)** · 🔧 **K242** mutasyon kolu YOK · 🔧 **K244** kabul listesi ≠ CI
  kapsami. (K243 KAPANDI `951059fa`.) Tam metinler KUTUDA.
- 🔧 **K260:** N4B gocunun 15 kaydindan 10'u `kat_sec` ile yine MIMAR'a dusup `[DAGITILMAZ]` kaliyor. kabul: yuklem + mutant.
- 🔧 **K233:** batarya beklenen kumeleri ELLE tasiniyor (SINIF; kabul: sayi TURETILIR + mutant) ·
  🔧 **K238:** `marka-sayfa-mutasyon` taban kirmizisinda KENDINI KAPATIYOR (kabul: bagimsiz kosar
  ya da `KAPSAM=0` jetonu BASAR).
- 🔧 **K234:** CAYMA_RE "iade"yi yakalamiyor (m.15 disi hak vaadi gorunmez); kabul: olcer+3 mutant. ·
  🔧 **K235 (SINIF):** hukuki beyan kapilari `hijyen-a3`te, `deploy.needs` DISINDA — UCU BIRDEN
  karara baglanir, tekil tasima YASAK.
- 🔧 **K269 (24 Agu, K256'dan DOGDU — CAGRI YERI YOK):** nabiz hukmunu OKUYAN taraf YOK; atiflar =
  2 crontab kosum satiri + 1 crontab yedegi + 1 ilgisiz `baglam-olcum.tsv` etiketi, kovayi TUKETEN
  **0** ([[kapinin-menzili-cagri-yeridir]]). kabul: >=1 tuketici + tuketicinin KOVAYA GORE davranis
  degistirdigini kanitlayan mutant; jeton taramasi kabul DEGIL.
- 🔧 **K276 (24 Agu, K256'dan DOGDU — KABUL CI DISINDA):** `kimi-nabiz-test.py` repo DISINDA
  (`~/.claude/cron/`), kapsam kapisinin duzlemi repo ici → hicbir is akisindan kosmuyor, yalniz
  ELLE olculuyor. kabul: bir CI adimindan kosar (hijyen seridi) + `CI_KAPSAM_RC` basar + mutant:
  kol bozulunca O ADIM kirmizi yanar. Muafiyet listesi kabul DEGIL. · 🔧 **K275** `ci-kapsam`
  yalniz `tools/` DOGRUDAN altini tariyor (`k260/`,`n4b/` MENZIL DISI). · 🔧 **K272·K273·K274·
  K277** defter/kutu ailesi: rotasyon vetosu · numara atomik DEGIL (bugun 3 cakisma) · rc=2
  gozcude CI_KIRMIZI · arsiv jetonu okunmadan tasiniyor. **Bes kalemin tam metni KUTUDA.**
- 🔧 **K230/K231/K232 (K214 devri):** kanca bagimliligi · kilit testi CI'da CAGRISIZ · sessiz kayit. KUTUDA.
- 🔧 **K283:** baslik kolunun capa ekseni
  ureticiden BAGIMSIZ degil; kabul: ayri capa + `M4` mutanti KIRMIZI. Tam metin KUTUDA.
- ⚠️ **K86 BABA basamaginda** (`SEBEP=YETENEK SAYAC=5`, tur 663 diske yazdi, kova `OKAN_KAPISI`) —
  BaBa karari bekler. **K281 CURUDU** (`KILIT_MUMKUN=0`: isci her tur olse de 13 turda BABA'ya
  cikiyor). · 🔧 **K282 (OLCULEMEDI):** `DURUM_BITMEYEN_TUR`, `DAGITILMAZ_DURUMLAR` disinda —
  BABA'daki kalem geri dusebilir; kabulun 1. kolu ERISILEBILIRLIK, uretilemezse `KAPSAM_DISI`.

## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)
- 🔴 **K212 (`tools/yedekle.py` iki GERCEK kusur, BEKLETMEDE):** tam metin+kabul ARSIVDE; SeritB kapsaminda DEGIL.
- 🔴 **MOTOR (20 Agu):** kapali kume `minimax-m3`(BIRINCIL) `kimi`(yedek) `claude`; digerleri RED. Tek kaynak `mimar_kimlik.py`.
- 🔧 **K200 (saklama YURURLUKTE — TAM METIN ARSIVDE):** (i) canli `--kuru --d1` ⚖️ OKAN KAPISI ·
  (ii) periyodik kablolama MIMARDA · (iii) kablolamanin KOSTUGU kanit. Sira: sema→tesisat→trafik.
- 🔧 **K199 (19 Agu, KraL):** `is-akisi-kapisi.py` "etkili tasiyici" tanimi LITERALE capali;
  varlik turetilmis mekanizmaya gecince korlesiyor (K193). Care: sonucu olc ya da makine-okunur
  beyani tasiyici say; mutant + negatif vaka sart. · 🔧 **K201 SINIF: KAYIT KENDINI OLCMEZ** — bes vaka;
  her kayit ya TURETILIR ya kendi sayisiyla KABUL EDILIR, "EKLE" yetmez SAYI sart.
- 🔧 **K196 (DEPO GENELI):** CI node 20 / yerel 25.8.1 → yerel JS yesilleri CI surumunde OLCULMEMIS. ARSIVDE.
- 🔴 **K197: 19 Ağu mimara giden rapor içeriği (239 satır / 11.617 B) KAYBEDİLDİ — gitignore deseni + ağaç silme sırası.** Birebir cümle + öz KUTUDA.
- 🔧 **K217 (19 Agu, KraL push ciktisinda OLCTU):** tavan nobetcisi, baska kapinin self-test fiksturlerini
  (temp `pruvo-kapi-test-*`, detached, saniyelik) MIMAR sayip sahte `TAVAN ASILDI SAYI=3` yaziyor (kanit
  hafizada: [[iki-kovali-siniflama-ucuncu-sinifi-yutar]]); yordam "kaldir" dedigi icin GERCEK agac silinebilir. kabul: fikstur duzlemi sayimdan DUSER + mutant hedef-kol atfi + gercek 3. agac YAKALANIR.
- 🔧 **K189** (`ci-kapsam-test.py` hukum ekseni; kabul: aday>0 iken `OLCULEMEDI`+sifir-disi rc +
  ayri jeton + mutant hedef-kol atfi) · 🔧 **K191** (tarama SPEC'i isi ONCULDEN aliyor; sahibi
  MaCiT; kabul: ILK blok KAPSAM ON-OLCUMU + tazelik capasi). **Ikisinin tam metni ARSIVDE.**
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
- 🔧 **K228 (20 Agu, KraL — K220'nin KARDESI, ayni govde DEGIL):** `marka=` ekseninde iki yuzey
  FARKLI yuklem kosuyor — uc `marka ∋ HAM` OR `marka_kanon ∋ katla(v)` (=`markaUyeMi ∪ baslikMarkalari`),
  yerel (`parite-marka-sinifi.js`) YALNIZ `markaUyeMi` → yon DAIMA `/ara ≥ yerel` (47 ayrisim /
  1331 sorgu). YON: iki yuzeyi TEK KAYNAKTAN turet ("once testi duzelt" DEGIL). TAM METIN+kabul ARSIVDE.

## KraL ACIK ARTIKLAR (19 Agu anlati blogu ARSIVE TASINDI; kota uyarisi da orada)
🔧 **K203:** tavan kapisi worktree ICINDEN rol eksenini kaybediyor (sebep onek DEGIL cagri baglami);
K223'un FIKSTUR kovasi fikstur eksenini kapatti, ROL ekseni ACIK. · 🔧 **K204:** `OKSUZ` fiilen
"kirli mi" olcuyor, TEK BASINA kaldirma gerekcesi DEGIL. · 🔧 **K188:** yarim yedek OLCULEBILIR;
kabul `YEDEK=TAM/YARIM` jetonu + fikstur.
- 🔴 **T1 pencere muhasebesi + T3/T4 kaniti:** `OLCULEMEDI_TUR=2` ayri satir; nobet kosuyor ama `ONARIM=0`, 10 kalem MIMAR'da. **Tam metin ARSIVDE.**
  **19 Agu KALAN ACIK ARTIKLAR:** T3 `SAHIPSIZ=44→24 (Onarim dali olctu)` · T4/T5 canli kablo
  (Okan kapisi) · T5 hareket damgasi 7/7 `OLCULEMEDI` · K188 kancasi BAGLI DEGIL · Escape olcumu
  yok — hepsi chip'lerde.
- 🔧 **K218 · K219 · K221:** tam metinler ARSIVDE. (K195 merge edildi `528da42d`.)
- 🔧 **K198 (19 Agu — ⚖️ OKAN KAPISI):** izlenen yapilandirmada ticari alan var, nobetci o duzlemi
  taramiyor (muafiyette de yok). **Tam metin ARSIVDE.** kabul: OLCER ya da `KAPSAM DISI` + mutant.
- 🔧 **K179 (18 Agu):** `RECETE=9 REDDEDILEN=8 EVREN=390`; kalan 6 RED gercek. Hukum `tools/paket-k179-recete-ayiklama.md`. kabul: `AYIKLANAMADI` ayri kova + 3 mutant.
- 🔧 **K182 (18 Agu — SINIF, bugun UC KEZ cikti):** mutant "kirmizi geldi" diye kanit
  sayiliyor ama kirmizinin SEBEBI hedef kol mu olculmuyor (recete M1 · K178 tek eksen ·
  ③g M5). kabul: her mutant, hedef kolu oldurdugunu AYRICA kanitlar.
- 🔧 **K176:** D1 kilit mesaji YANLIS PID basiyor (`d1-sync.py:157`); yayini bloklamaz. kabul: tutani basar ya da OLCULEMEDI + mutant. · ⛔ `origin/k152-link-temiz` MERGE EDILMEZ (icerik `83aaf4e2`de) — SILINEBILIR.
- 🔧 **K171 (18 Agu, MaCiT→KraL DEVIR; PAKET HAZIR `cc6fece2`, icra bekliyor):** gizli kaynak
  duzleminde 15 artik kayit; kanonik arac o duzleme dokunmuyor. Hukum+kabul `tools/paket-k171-kaynak-temizle.md`de.
- 🔧 **K135 (17 Agu, MaCiT→KraL):** `cgt-ekle.py::fetch()` tek satir UA ile CGTrader WAF'ina takiliyor (HTTP 202 + placeholder);
  kalici `--yerel` yolu KraL'da, sonraki dilim oncesi. Tam metin ARSIVDE. `kabul:` alani BOS.
- 🟠 **K139+N1 (CANLI CRON DURUMU, ekip bilmeli):** gozcu `8,23,38,53` (15 dk); ci-nobeti `7 * * * *`
  artik KOSULSUZ DEGIL — `nobet-tetik.py` gozcunun kalbini okur (24 kayit replay: acilan tur
  **24/gun → 0**; canli 21:07 `acilan_tur=0`). 🔧 N1-kalem: uzun tur kendi kalbini bayat gosterir.
- 🟠 **K144 (UCUSTAKI KOSUM):** ardarda push'lar build'i `cancelled` ediyor (ARIZA DEGIL);
  hukum her turda guncel uca tasiniyor. Tam metin ARSIVDE.
  kabul: guncel ucu ICEREN kosum `conclusion=success` **VE** cache-bust'SIZ canli teyit.
- 🔧 **K140 (17 Agu — hukum verildi, icra kaldi):** kapi EVREN KAYNAGI hatasi (cip evreni kuratorlu). Tam metin ARSIVDE. kabul: `marka-invaryant-kapisi.py` 7 jeton DUSMUS + `Rover` DURUYOR + mutasyon 4/4.
- 🔧 **17 Agu KALEMLERI:** K163 · K162 · K157 (⚖️ Okan, 22 Agu) · K158 · K146 · K142 (MaCiT) · K118. TAM METIN ARSIVDE.
- 🔴 **K104 / K104B:** nobet sicili + iki kapi main'de kirmizi. HUKUM MIMARDA. · **K99**
  bag kolonu · **K100** satir-sonu muafiyeti · **K102** yasakli ic dosya adi.
- 🟠 **K152 (17 Agu — OKAN KARARI kapsami belirledi):** "sitede bulunan tum urunler satilabilir." Tam metin ARSIVDE.
  kabul: `python3 tools/koken-bul.py --eksik` → `EKSIK` DUSER **VE** `--kendini-test` rc=0.
- 🔧 **Iki acik kapi kalemi:** (a) shop bayatlik TETIK ekseni ≠ bundle evreni; (b) `devam-sinif-kapisi.py`
  is-akisi muafiyeti `norm`/`ham` ayrisiyor. · 🟠 **K122:** `kurtarma/k122-yabanci-is` dali DURUYOR. ARSIVDE.
- 🔧 **K151 · K161 (17-19 Agu):** ikisinin de TAM METNI ARSIVDE (20 Agu 1:1 tasima blogu).

## OKAN'DA

- 🔧 Eski yedek klasorunu backup-v2 icine tasima · K89 olcum eylemi silme karari. (K128; ARSIVDE.)
- 🔧 **TARIFE KARAR KURALI (olculdu, onaya hazir):** $20 KALIR; kota %80'e yaklasirsa ikinci saglayicinin $39 basamagi ($50 tek-saglayici yerine CESITLILIK). TAM GEREKCE ARSIVDE.
- 🔧 **22 Agu:** kimi/codex motor karari (K157) · $100 plan karari (once yanma olcumu).
- 🔧 **ODEME WORKER DEPLOY (19 Agu 16:29Z · 20 Agu 14:2xZ TAZELENDI):** pruvo-shop bayatlik nabzi KIRMIZI **373,2 dk** / esik 120; yayinlanmamis fark artik 2 commit ve YORUM DEGIL — K252 siparis durum secici DAVRANISI canliya INMEDI. Kapatan eylem `npx wrangler deploy` = OKAN KAPISI. Detay ci-nobeti.log.

## ARSIVDE
14-20 Agu kapananlar `DEVAM-ARSIV.md`'de.