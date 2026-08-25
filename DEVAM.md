# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔁 CANLI TUR — 25 Agu ogleden sonra (KraL) · main=origin `4cd20a92`, agac TEMIZ
📌 **BICIM:** nobet hukmu TUR NUMARASIYLA yazilir (`HUKUM=<hal>@tur<N>`).

✅ **KAPANDI:** **K288** (git ucu ata + 38 sayili/12 fail-closed tur, kanit mimar elinde; mutabakat
kolu **`OLCULEMEDI`** — panel yuzeyinde saatlik satir YOK, 25 Agu Okan'in onayiyla acilip olculdu)
· **sahipsiz lisans dali** (tek commit'i Okan'in 24 Agu emrinin yasakladigi kapiydi → SILINDI `0818f269`).
🔴 **Kendi hatam:** `main..dal=0` "merge edildi" de olabilir; ayirici `merge-base --is-ancestor`.
🔵 **5 CHIP** (ana oturumda kosan is YOK): K289·K290·K287·K286·K295.
⏳ **TAVAN (Okan: "bir hafta daha olc"):** olcum **1 Eyl'de** turetilir — limit 31 Agu'a kadar %50 BOOST'lu (panelde okundu), simdiki veriden turetilen esik SISIRILMIS olur.
- 🔴 **K289 (KRAL EVI BLOKLU — turun 1. isi):** `parti-borc-kapisi --ev KraL` `ACIK=26` RED; okudugu
  `memory/acik-kalemler.md` BAYAT (K86 merge'li, K98 iki SHA'da success) → SINIF K201. kabul: 26/26
  hukum + SHA kaniti + LOSSLESS arsiv + olcutsuz kalemi REDDEDEN kol + mutant.
- 🔴 **K291:** parti kapisi DAVRANIS degil DIZGE olcuyor, SALT-OKUMA reddediliyor. kabul: okuma↔baslatma AYRI kol + mutant. → [[n2b-kapisi-dizge-olcer]].
- 🔧 **K292 (MaCiT 4 belirti/3+ tekrar, SINIF):** `merge_safe()` id-soneki yardimci ize yansimiyor;
  kabul: ORTAK yardimci + >=1 TUKETICI okur + davranis mutanti. · 🔧 **K293 (MaCiT 3 kez):** pre-push
  D1 senkron lease/race; kabul: fikstur + senkron bitmeden CIKMAZ ya da `OLCULEMEDI` + mutant.
  · 🔧 **K295:** `MEMORY.md` 19,6/24,4 KB; kabul <17,1 KB + `KAYIP_KAYIT=0`.
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
- 🔧 **K217** (tavan nobetcisi fiksturu MIMAR sayiyor) · 🔴 **T1/T3/T4/T5** (nobet kosuyor ama `ONARIM=0`, 10 kalem MIMAR'da). Ikisi de KUTUDA.
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

- ✅ **KAPANDI — 25 Agu Okan penceresi: dokuz kalem karara baglandi.** Adlari ve hukumleri hafizada:
  [[okan-25agu-kapatilan-konular]]. 🔴 Bu konularda yeniden kalem ACILMAZ.
- 🔧 **K76 (Okan ONAYLADI, chip acildi):** iki yasal sayfa 6502 m.11'den DAR (`/teslimat-iade` 0/4,
  `/mesafeli-satis` 2/4); dort hak yazilir, metin yayindan ONCE Okan'a okutulur.
- 🔧 **K200(i):** Okan "kuru kos" dedi; komut `yedekle.py --kuru` (`--d1` bayragi YOK, kaynaktan
  dogrulandi), cikti bekleniyor. · 🔧 **K296 chip:** odeme bayatligi olculuyor, deploy komutu
  HAZIRLANIR ama KOSULMAZ.
- 🔧 **ODEME WORKER DEPLOY:** Okan "once olctur" dedi → **K296 chip'ine gecti**, deploy olcumden sonra.

## ARSIVDE
14-20 Agu kapananlar `DEVAM-ARSIV.md`'de.