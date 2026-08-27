# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔚 27 AGU KAPANIS · main=origin `25b2879b` SHA-BIREBIR · agac TEMIZ · worktree 9→5 · kosan cip 4
✅ **CANLIYA GIDEN (7 merge):** `051b74d0` kutu kilidi SINIF · `2c6640ac` sabah teslim · `3eee64d4`
K314 · `05d5df85` **K184 sihirbazi KOKUNDEN kalkti** (canli: buton VAR→YOK, konsol 0, odeme yolu
davranisla saglam) · `34ca7283` defter rotasyon birimi · `23098ae2` ORTAM kolu TURETIYOR ·
`25b2879b` yedek dususu sessiz gecemez. Uc merge BAGIMSIZ dogrulayici tarafindan olculdu; git
ekseni mimar elinde: 14 dosya hepsi `tools/`, `urunler.json` DOKUNULMADI, sizinti taramasi **0**.
🟢 **GUNUN SINIFI:** *olcut yanlis ekseni okuyunca koruma yayin durdurur* — kutu kilidi 5 commit'i
durdurmustu; ① jeton yalniz KAPANIS satirinda sayilir ② korumali blok rotasyona GIRMEZ ③ kapi
aracin HUKMUNU okur.
Canli kanit: kutu 570→220, sonra 331→230, `KAYIP=0` uc eksende.
🔴 **KOSUYOR (4, motor Claude):** `KraL-IcraKapisiKimlik` (dal `kral/icra-kapisi-kimlik-27agu`
`82a30b41` — kapi cipteki isciyi mimar sayiyor, MaCiT hatti haftalardir BLOKE) · `KraL-BelgeOnbellegi`
(HTML belgesi `max-age=14400`) · `KraL-KarantinaHukmu` (dal `kral/nobet-turu-27agu`) · `KraL-DogrulaMerge`.
🔴 **BEKLIYOR — "neyi olcmek kapatir":** ⓐ `nobet-turu` **MERGE YOK** (iddia 21/21, olculen **20/21**
`DUSEN=C5`) → *hukum indi: ardisik ESIK kazanir, C5 iki yonlu yazilir; rc=0 + KONTROL 10/10* ·
ⓑ `--yaz-sonrasi` kolu main'de ama **KABLOSUZ** → *kilit-guvenli + tavan altinda no-op + eszamanli
cagride bayt-birebir olcusun, sonra mimar kabloyu takar* · ⓒ **HTML 4 saat** → *belge TTL dusuk,
varlik TTL sabit, `Age` serisiyle* · ⓓ K321 karantina · ⓔ ⑦ bekci vakalari · ⓕ K314 acik ucu.
**Okan'da bekleyen: `pruvo-jenerator` icin GitHub App repository access (TeKiN talebi).**

## 🔁 25 AGU — IKINCI TUR — aktif kalemler (header ARSIVDE)
- ✅ **25-26 Agu KAPANAN 4 KALEM (K250·K302·K303·K305) — TAM METIN ARSIVDE**, "KAPANAN 4 KALEM" basligi.
- 🔧 **K250 KALAN:** KaaN·ArTisT·HocA·BaBa — her biri tek satirlik `expanduser` duzeltmesi, KENDI
  mimarlarinda; KraL kardes depoya yazmaz. · 🔧 **K302 KALAN:** kok neden MaCiT'in `olcum/hasat_ekle.py`
  dosyasinda, kutuda bildirildi.
- 🔧 K307 yan bulgu (kalem KAPANDI `32909205580`): isci probu 206'yi "olu" saydi → [[prob-kendi-baglamini-olcer]]
- 🔴 **K304 (SINIF: BAYAT TEK KAYNAK):** `skills/codex-isci` motor sirasini KOPYALIYORDU; uc kopya
  SILINDI. kabul: `yedekle.py` BORCLU (surum kontrolu disi dizin).
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
- 🔧 **K282 (OLCULEMEDI):** `DURUM_BITMEYEN_TUR`, `DAGITILMAZ_DURUMLAR` disinda; kabulun 1. kolu
  ERISILEBILIRLIK. (K86 merdiven kaydi KONUSUZ — kalem 25 Agu'da kapandi; **K281 CURUDU**.)

## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)
- 🔴 **26 AGU KALEMLERI — TAM METIN KAYNAK-DOGRUSUNDA (`acik-kalemler.md`) + KUTUDA; burada yalniz
  ISARETCI** (uzun hali `DEVAM-ARSIV.md` 26 Agu ROTASYON blogu 1/5): K306 MERGE `df3b0d48` · K308 ACIK ·
  K309 DILIM-1 MERGE `25b38a82` (DILIM-2 MIMARDA) · K310 ACIK · K212 MERGE `97370cc2` KAPANDI · K222
  KAPANDI · K311 MERGE `bcbdb1dd` ACIK (①-④ GECMEDI; ④ GERI ALINDI) · **K312 ACILDI**.
- 🔴 **MOTOR (20 Agu):** kapali kume `minimax-m3`(BIRINCIL) `kimi`(yedek) `claude`; digerleri RED. Tek kaynak `mimar_kimlik.py`.
- 🔧 **K200 (TAM METIN ARSIVDE):** (i) kuru kosum OLCULDU 25 Agu (1512/234, sir elemesi 5/5; BULGU:
  gurultu budamasi memory agacinda KOSMUYOR → 13 gecici dosya Drive'a) · (ii) kablolama MIMARDA · (iii) kostugu kanit.
- 🔧 **K199 (19 Agu):** `is-akisi-kapisi.py` "etkili tasiyici" LITERALE capali; varlik turetilmis
  mekanizmaya gecince korlesir (K193). Care: sonucu olc ya da makine-okunur beyani tasiyici say;
  mutant+negatif sart. · 🔧 **K201 SINIF: KAYIT KENDINI OLCMEZ** — 5 vaka; ya TURETILIR ya SAYIYLA.
- 🔧 **K196 (DEPO GENELI):** CI node 20 / yerel 25.8.1 → yerel JS yesilleri CI surumunde OLCULMEMIS. ARSIVDE.
- 🔴 **K197: 19 Ağu mimara giden rapor içeriği (239 satır / 11.617 B) KAYBEDİLDİ — gitignore deseni + ağaç silme sırası.** Birebir cümle + öz KUTUDA.
- 🔧 **K217** tavan fiksturu. (K311 tam metni kaynak-dogrusunda; defterdeki ikinci kopya ARSIVE indi 2/5.)
- 🔧 **K189** (`ci-kapsam-test.py` hukum ekseni; kabul: aday>0 iken `OLCULEMEDI`+sifir-disi rc +
  ayri jeton + mutant hedef-kol atfi) · 🔧 **K191** (tarama SPEC'i isi ONCULDEN aliyor; sahibi
  MaCiT; kabul: ILK blok KAPSAM ON-OLCUMU + tazelik capasi). **Ikisinin tam metni ARSIVDE.**
- 🔧 **K192** (Okan: kalem ac DOKUNMA): `kimi` KURULU kapisinda YOK, dagitim kaniti VARLIK olcuyor. ARSIVDE.
- 🔧 **K202-kendini-test** (M06 cokme + bayat capa) — 🔴 SAHIPSIZ: SeritB chip'i "bende HIC olmadi" diye olctu (onun uyesi K203'tu, YESIL kapandi). kabul: capa govdeden count==1, `beklentiyi tutmayan: 0`.
- 🟠 **K206 (TeKiN→KraL; 3 KARAR VERILDI, icra chip'i sirada):** 8 uretec sari seriye — saklama AYRI
  AILE · gyro `doku=duz` · 8 fiyat ONAY (280/190/170/350=TAVAN/160/240/140/220); kupler render CELISKILI.
  PAKET main'de (`7ce644ae`). kabul (icra): ONIZLEME_AILELER 22→30 · taban-fiyat 21→29 · +8 sari kayit · 8 gorsel R2 200 · parite yesil.
- 🔧 **K220 (KraL):** `marka_yazimlari()`+`taninmis_mi()` TEK listeden besleniyor; liste iki rol tasiyor
  ("baslikta aranan ad" + "MODEL OLAMAZ jetonu"). Range Rover'i markaya yazmak CANLI `/marka/land-rover/range-rover/`
  sayfasini (6 urun) OLDURUYOR — ayrilmadan dokunma. Girdi: K216 raporu EK + `arama.py:2201`. SIRA: D bitti, sirada A.

## KraL ACIK ARTIKLAR (19 Agu anlati blogu ARSIVE TASINDI; kota uyarisi da orada)
🔧 **K203:** tavan kapisi worktree ICINDEN rol eksenini kaybediyor (sebep onek DEGIL cagri baglami);
K223'un FIKSTUR kovasi fikstur eksenini kapatti, ROL ekseni ACIK. · 🔧 **K204:** `OKSUZ` fiilen
"kirli mi" olcuyor, TEK BASINA kaldirma gerekcesi DEGIL. · 🔧 **K188** → kaynak-dogrusunda (5/5, `KraL-K309D2`: rc=0 ama eksen bataryada YOK).
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
- 🟠 **K139+N1 (CANLI CRON, ekip bilmeli):** gozcu `8,23,38,53` (15 dk); ci-nobeti `7 * * * *` artik
  KOSULSUZ DEGIL (`nobet-tetik.py` kalbi okur; 24/gun→0). 🔧 N1: uzun tur kalbini bayat gosterir.
- 🟠 **K144 (UCUSTAKI KOSUM):** ardarda push'lar build'i `cancelled` eder (ARIZA DEGIL); hukum guncel
  uca tasinir. kabul: guncel ucu ICEREN kosum `success` **VE** cache-bust'SIZ canli teyit. ARSIVDE.
- 🔧 **K140** → kaynak-dogrusunda (ikinci kopya ARSIVE indi 4/5, `KraL-K309D2`: kosum kaniti orada).
- 🔧 **17 Agu KALEMLERI:** K163 · K162 · K157 (⚖️ Okan, 22 Agu) · K158 · K146 · K142 (MaCiT) · K118. TAM METIN ARSIVDE.
- 🔴 **K104 / K104B:** nobet sicili + iki kapi main'de kirmizi. HUKUM MIMARDA. · **K99**
  bag kolonu · **K100** satir-sonu muafiyeti · **K102** yasakli ic dosya adi.
- 🟠 **K152** → kaynak-dogrusunda (ikinci kopya ARSIVE indi 3/5, `KraL-K309D2`: kabul araci main'de YOK).
- 🔧 **Iki acik kapi kalemi:** (a) shop bayatlik TETIK ekseni ≠ bundle evreni; (b) `devam-sinif-kapisi.py`
  is-akisi muafiyeti `norm`/`ham` ayrisiyor. · 🟠 **K122:** `kurtarma/k122-yabanci-is` dali DURUYOR. ARSIVDE.
- 🔧 **K151** (17-19 Agu): TAM METNI ARSIVDE (20 Agu 1:1 tasima blogu). · 🔧 **K161** → ISARETCI: KAYNAK-DOGRUSUNDA (26 Agu, `KraL-K309D2`).

## OKAN'DA
- ✅ 25 Agu penceresi: 9 kalem kapandi → [[okan-25agu-kapatilan-konular]]; 🔴 yeniden ACILMAZ.
- 🔧 **K297·K298·K299·K300·K301:** SERIT B hijyen kirmizisi · iki ayri K29 · K86 metni bayat ·
  K55 sayisi **197** · `T4-OLCUTSUZ` tum evlerde. Tam metinler KUTUDA.

## 🔧 K318 CIP-ROL — dal `kral/icra-kapisi-kimlik-27agu` `82a30b41`, MERGE BEKLIYOR
Kapi ROL olcer: ANA RED, cip GECER, olculemez RED. 299→314 vaka. MaCiT'e merge ile GELMEZ.

## ARSIVDE — 14-20 Agu `DEVAM-ARSIV.md`'de.