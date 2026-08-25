# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔁 OTURUM KAPANISI — 25 Agu aksam (KraL) · main=origin `d3cf44d7`, agac TEMIZ
📌 nobet hukmu TUR NUMARASIYLA (`HUKUM=<hal>@tur<N>`).
✅ **CANLIYA GITTI — 3 merge, git eksenini MIMAR kendi olctu:** K290 `edae6a5c` (ASCII-disi urun id
kapisi; canli katalogda 0 ihlal) · K287 `45210ada` (olcu-saglik TEK KAYNAK + buyuk-uc tavani) · K289
`011a7b07` (`T4-OLCUTSUZ` sinif kolu). Kapsam 11 dosya +1389/−94; `urunler.json`·`index.html`·`shop/`
·`worker/` YOK → site yuzeyi DEGISMEDI, sizinti taramasi 0. Deploy sonucu OLCULMEDI (kuyrukta).
✅ **9 CHIP KAPANDI:** K288 · K289 · K290 · K287 · K286 · K295 · K296 (**canli shop BAYAT DEGIL →
deploy GEREKMIYOR**) · K76 (IPTAL) · merge turu. Ayrica sahipsiz lisans dali hukumle SILINDI (`0818f269`).
🔵 **KOSUYOR — OLDURME (5 chip, motor Claude):** K86 `kral/k86-batarya` · K107 `kral/k107-para-literali`
· K99 `kral/k99-ref-bag` · K74+K27 `kral/k74-k27-olcum` (OLCUM turu, merge YOK) · K50 `kral/k50-dal-sahibi`.
🟡 **BEKLIYOR:** `admiring-thompson-5eab24` (K289 sahibi CANLI; icerik main'de birebir, sahibi kapaninca
agac+dal silinir) · borc kapisi `ACIK=9`, 5 chip kapandikca duser · 3 kalem kardes evde (K44·K29→ArTisT,
K55→MaCiT). ⏳ **TAVAN:** olcum 1 Eyl'de (limit 31 Agu'a kadar %50 BOOST'lu → simdiki veri SISIRILMIS).
🔴 **Kendi iki hatam:** `main..dal=0` "merge edildi" de olabilir (ayirici `merge-base --is-ancestor`) ·
K76'yi BAYAT sayiyla Okan'a cikardim (canli 4/4'tu) — kalemi cikarmadan CANLI hali OLC.
- 🔴 **K291:** parti kapisi DAVRANIS degil DIZGE olcuyor, SALT-OKUMA reddediliyor. kabul: okuma↔baslatma AYRI kol + mutant. → [[n2b-kapisi-dizge-olcer]].
- 🔧 **K292 (MaCiT 4 belirti/3+ tekrar, SINIF):** `merge_safe()` id-soneki yardimci ize yansimiyor;
  kabul: ORTAK yardimci + >=1 TUKETICI okur + davranis mutanti. · 🔧 **K293 (MaCiT 3 kez):** pre-push
  D1 senkron lease/race; kabul: fikstur + senkron bitmeden CIKMAZ ya da `OLCULEMEDI` + mutant.
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
- 🔧 **K283:** baslik kolunun capa ekseni ureticiden BAGIMSIZ degil; kabul: ayri capa + `M4` mutanti KIRMIZI. KUTUDA.
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

- ✅ 25 Agu penceresi: 9 kalem kapandi → [[okan-25agu-kapatilan-konular]]; 🔴 yeniden ACILMAZ.
- 🔧 **K297·K298·K299·K300·K301:** SERIT B hijyen kirmizisi · iki ayri K29 · K86 metni bayat ·
  K55 sayisi **197** · `T4-OLCUTSUZ` tum evlerde. Tam metinler KUTUDA.
- 🔧 **K200(i) — OKAN'DA TEK ACIK IS:** "kuru kos" dedi; komut `python3 tools/yedekle.py --kuru`
  (`--d1` bayragi YOK, kaynaktan dogrulandi), ciktiyi mimar yorumlayacak.

## ARSIVDE
14-20 Agu kapananlar `DEVAM-ARSIV.md`'de.