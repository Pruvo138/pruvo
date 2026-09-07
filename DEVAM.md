# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## ✅ 7 EYL — ana oturum: **3 CIP KAPANDI, EV TEMIZ; KraL'in `serit-b` kirmizisi 0**
**TEMIZLIK:** worktree **4 → 1** (ucu de `arsiv-kapisi` rc=0 + `lsof`) · 3 dal · 2 oturum · kutu **455 → 399 st** (`lossless=GECTI`, kalan 18 blok KORUMALI) · defterden `SERIT B 17→6` arsive (**7 satir, eksik 0**).
**CIP KABULLERI (calistirilabilir, mimar kostu):** `BorcParser` → `GECERSIZ_DURUM 7→0` + `ACIK_KALEM 43→48` (5 satir ILK KEZ okundu) · `SeritB2` → `recete AYIKLANAMADI 1→0` + `cip-kapat 20/20→24/24` · `KapiEnvanteri` → **BaBa'nin ONCULUNU CURUTTU** (uc kapi KURULU DEGIL, `5/8` DOGRU; 3 canli RED vakasi URETILEMEDI cunku AKIM YOK) — karar BaBa'da.
**T4:** `GECERSIZ_DURUM=0 OLCUTSUZ_KALEM=0` (K339-EK+K329-EK'e `kabul:` yazildi); RED sebebi artik yalniz **borc = 48 acik kalem** (esik 0, tasarim).
🔴 **KENDI OLCUMUM CURUTULDU** (cip `bold-poitras`, 400 kosum): "push kolundan 0 hukum" YANLIS — **152/373 = %41**, `failure` de HUKUMDUR. **MIMAR KARARI:** olcut **HEAD garantili hukum**, SHA kapsamasi DEGIL; `concurrency`yi SHA'li yapmak **G9 ile YASAK**.
**SERIT B** (`34063854360` @ `66a461ad`): `serit-b` 1 = `LCP` **ArTisT** · `hijyen-a3` 1 = `Arama parite` (cip `NodeEkseni`; 4 komut da YERELDE YESIL) · `hijyen-a2` 1 = `Feed politika` **MaCiT**.
**YAYIN ✅:** `34060159828` @ `66a461ad` — 6/6 yesil, deploy+yayin success, SKIPPED **0** (BaBa'nin 2 ardisik SKIPPED kirmizisi KAPANDI).
**KimiIptal-7Eyl:** isci.sh/uc/crontab **0**, MOTOR-YOK 3/3, vaka 619. TAM METIN KUTUDA.
**KAPANIS 08:2xZ:** 4 cip kabul · tamirci dali MERGE `019e8efe`→`535005fd` · `hijyen-a3`=`PVC` landing · YAYIN `34098909326` SKIPPED **0**. KUTUDA.
**10:3xZ:** Okan'in **3 CIP EMRI ICRA** (Sitemap/JsonLd/LlmsTxt) · `(Impeller)` ikizi `ee6406e3` · **K376 ACILDI** · kutu **461→191** (13 koruma DUSTU, lossless). KUTUDA.
## 🔴 6 EYL — `KraL-KapiEnvanteri-6Eyl` [Opus 5]: **hukmun ONCULU CURUDU — uc kapi KURULU DEGIL; `5/8` DOGRU** (tam hesap KUTUDA)
**ONCUL+AKIM:** 3 atfin ucu de **PROZA** (biri `SILINDI` kaydi); 29 Agu supurmesi kabloyu sokmus. Canli: 3 kapi da **deny URETMEDI** (`git commit` **rc=0**, ICRA izi **0**); POZITIF KONTROL **deny** verdi. (c) menzili `ast` kod-duzlemiyle kuruldu · M4 **dogrudan kolda** korluk buldu → onarildi · mutant **4/4** · batarya SERIT B'de. **Kapilar KURULMADI → BaBa karari.**

## ✅ 6 EYL — ana oturum: **TEMIZLIK + ACIK IS SAYIMI** (2 kirmizi sinifi cipe verildi)
**TEMIZLIK:** worktree **5 → 1** (dordu de `arsiv-kapisi` **ARSIVLENEBILIR rc=0**; canlilik `lsof -a -d cwd` ile olculdu) · merge'lu 4 cip dali `-d` ile silindi · biten 2 oturum arsivlendi · `cip-supurme` **ACIK CIP YOK**.
**SAYIM → cip `KraL-BorcParser-6Eyl` ✅ `672f4b41`:** ONCUL DUZELTILDI — kacis korlugu **3** satir (K371·K313·K339); K308·K339-EK kacisSIZ gomulu `|` (defter YANLIS), K329 etiket; **K89·K91 satir sonu `|` yok → parser'in ILK satirinda SESSIZ dusuyordu, ikisi de OKAN-KAPISI**. `43/0/7 RED` → **`48/2/0`**, mutant **8/8→10/10**.
**SERIT B** (`34043459306` @ `f22dfa96`): 4 kirmizi — `Recete` **AYIKLANAMADI=1** (dun dogdu) + `Cip kapatma` **V3d** (yerel 20/20, CI 19/20 = ORTAM EKSENI) → cip `KraL-SeritB2-6Eyl` · `LCP onculuk` **ArTisT'te** · `hijyen-a3` parite yerelde **248/0**, `f7639a86` turu OLCULUYOR.
**YAYIN ✅:** `34047935969` @ `7ca9d5bc` — 6/6 is yesil, deploy+yayin **success**, SKIPPED **0**. SERIT B kolu (`34047936116`) `cancelled` (ArTisT `8b6ab3ae` ustune indi, push grubu TEK) → o eksen **OLCULEMEDI**, hukum `34048480047`'den.
## ✅ 6 EYL — `KraL-BorcKapisi-6Eyl` [Opus 5]: **T4: OKAN-KAPISI kilidi KALKTI + sessiz atlama KOL OLDU** (BaBa)
**(a)** T4-BORC sayimi **OKAN-KAPISI'ni SAYMIYOR** (`BORC_DURUMLARI`=ACIK/UCUSTA/🔧). PARSER sozlesmesi `ACIK_DURUMLAR` DEGISMEDI — onu 4 okuyucu daha okuyor (devir · korgoz x2 · parti-kapisi); daraltmak onlari oynatir. Baski KALDI: `OKAN_KAPISI=N` satiri + 23:00 ozetinde ayri satir. **FaR `acik_kalem=5` → `ACIK_KALEM=2` + `OKAN_KAPISI=3`.** Olcut kolu (K289) da BORCLU'ya daraltildi — yoksa `kabul:`siz tek OKAN-KAPISI satiri evi gene kilitler, (a) INERT kalirdi.
**(b)** Durum hucresi kanonik BES degerin disindaysa satir **ATLANMIYOR**: `T4-OLCULEMEDI durum gecersiz <kimlik>=<metin>` fail-closed RED. F08 kalibi (`ACIK (Okan kapisi KALKTI)`) iki kumeye de girmedigi icin **SESSIZCE ATLANIYORDU** = yanlis-yesil. 🔴 **TUZAK:** markdown AYRAC satiri 8 kolon uretip `kolonlar[5]="---"` verir — elenmeseydi HER defter kirmizi yanardi (kapi kendi ayracina takilir).
**FILO ON-OLCUMU (8 ev, ONCE):** gecersiz hucre **HocA 6 · KraL 7 · ORTAK 7 · digeri 0**. HocA'nin `OKAN-KAPISI (dusuk oncelik)` satiri **sessizce sayilmiyordu** → HocA `GECER`→`OLCULEMEDI` (KraL/ORTAK zaten RED). 🔴 Ev defterini KENDI duzeltir.
**KABUL:** `--kendini-test` **8/8 + KONTROL 1/1** (M-a/M-b IZOLE KOPYADA: benzersiz ad + `dont_write_bytecode`, canli govdeye yama YOK) · `--curutme` **4/4** · **OLDURUCU 3/3** · 23:00 ozet kolu **3/3** (T4 yok/cokuyor → `ÖLÇÜLEMEDİ`).
**YAYIN ✅:** `34041734321` @ `f22dfa96` **success**, 6/6 is yesil, **deploy+yayin zincirinde SKIPPED=0** (zincir-disi 3 = "yalniz KIRMIZI kosumda" adimi; onceki 2 success'te de AYNI → gerileme degil; ders KUTUDA).
**TABAN URETILDI:** `parti-kapisi` **12/13** + `korgoz` **KX=4/7** HEAD'de de AYNI → regresyon **0**. Yesil: `ev-haritasi` 9/9+4/4 · `chip-duzeni` 14/14+9/9 · `devir` 5/5+4/4 · `nobet-kabul` 51/0 · `is-akisi` · `ci-kapsam` · D1 34602 birebir. `nobet.yml` adim adi bayatti ("4 mutant"→8+1+4); kablo KORUNDU.
## 🔁 5-6 EYL ISARETCILERI — **TAM METIN ARSIVDE** (md5 birebir, eksik 0). ACIK iplikler: MODEL adindan marka turetimi · hafiza ekseni SILAHSIZ · baglam kotasi 2 vaka · `d1-sync --durum` 71,2 sn · MaCiT CLAUDE.md 13.060 B · `defter-rotasyon.py` 13/13 vetolu · MaCiT `Kahve` 79 kayit · LCP ArTisT'te (Okan'a: PSI anahtari).
## 🔴 CANLI TALIMAT (K353 blogu ARSIVE indi, tam metin `DEVAM-ARSIV.md`'de)
K353 merge'unden SONRA `kanca-kur.py` kosulur (once kosulursa filo felci).

## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)
- 🔴 **26 AGU KALEMLERI — TAM METIN KAYNAK-DOGRUSUNDA (`acik-kalemler.md`) + KUTUDA; burada yalniz
  ISARETCI** (uzun hali `DEVAM-ARSIV.md` 26 Agu ROTASYON blogu 1/5): K306 MERGE `df3b0d48` · K308 ACIK ·
  K309 DILIM-1 MERGE `25b38a82` (DILIM-2 MIMARDA) · K310 ACIK · K212 MERGE `97370cc2` KAPANDI · K222
  KAPANDI · K311 MERGE `bcbdb1dd` ACIK (①-④ GECMEDI; ④ GERI ALINDI) · **K312 ACILDI**.
- 🔴 **MOTOR (6 Eyl; 20 Agu GECERSIZ):** `minimax-m3` TEK + `claude`; `kimi` EMEKLI. Yedek YOK — m3 duserse `HAL=MOTOR-YOK rc=1`. Kaynak `mimar_kimlik.py`.
- 🔧 **K200 (TAM METIN ARSIVDE):** (i) kuru kosum OLCULDU 25 Agu (1512/234, sir elemesi 5/5; BULGU:
  gurultu budamasi memory agacinda KOSMUYOR → 13 gecici dosya Drive'a) · (ii) kablolama MIMARDA · (iii) kostugu kanit.
- 🔧 **K199 (19 Agu):** `is-akisi-kapisi.py` "etkili tasiyici" LITERALE capali; varlik turetilmis
  mekanizmaya gecince korlesir (K193). Care: sonucu olc ya da makine-okunur beyani tasiyici say;
  mutant+negatif sart. · 🔧 **K201 SINIF: KAYIT KENDINI OLCMEZ** — 5 vaka; ya TURETILIR ya SAYIYLA.
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
- 🔧 **K220 (KraL) → ISARETCI, TAM METIN `DEVAM-ARSIV.md`'de:** `marka_yazimlari()`+`taninmis_mi()` TEK listeden besleniyor, liste IKI rol tasiyor;
  Range Rover'i markaya yazmak CANLI `/marka/land-rover/range-rover/` sayfasini OLDURUYOR — **menzil on-olcumu yapilmadan dokunma**
  ([[k220-menzil-on-olcumu-uc-turdur-eksik]]). 31 Agu negatif olcumu (`Raymarine`, kume-farki yordami, sayi-only kolun korlugu mutantla kanitli) ARSIVDE. SIRA: D bitti, sirada A.
## KraL ACIK ARTIKLAR (19 Agu anlati blogu ARSIVE TASINDI; kota uyarisi da orada)
🔧 **K203:** tavan kapisi worktree ICINDEN rol eksenini kaybediyor (sebep onek DEGIL cagri baglami);
K223'un FIKSTUR kovasi fikstur eksenini kapatti, ROL ekseni ACIK. · 🔧 **K204:** `OKSUZ` fiilen
"kirli mi" olcuyor, TEK BASINA kaldirma gerekcesi DEGIL. · 🔧 **K188** → kaynak-dogrusunda (5/5, `KraL-K309D2`: rc=0 ama eksen bataryada YOK).
- 🔧 **K218 · K219 · K221:** tam metinler ARSIVDE. (K195 merge edildi `528da42d`.)
- 🔧 **K198** → ARSIVDE · izlenen yapilandirmada ticari alan var, nobetci o duzlemi
- 🔧 **K179** → ARSIVDE · `RECETE=9 REDDEDILEN=8 EVREN=390`; kalan 6 RED gercek. Hukum `tools/paket-k179-recete-ayiklama.md` · kabul: `AYIKLANAMADI` ayri kova + 3 mutant.
- 🔧 **K182 (18 Agu — SINIF, bugun UC KEZ cikti):** mutant "kirmizi geldi" diye kanit
  sayiliyor ama kirmizinin SEBEBI hedef kol mu olculmuyor (recete M1 · K178 tek eksen ·
  ③g M5). kabul: her mutant, hedef kolu oldurdugunu AYRICA kanitlar.
- 🔧 **K176** → ARSIVDE · D1 kilit mesaji YANLIS PID basiyor (`d1-sync.py:157`); yayini bloklamaz · kabul: tutani basar ya da OLCULEMEDI + mutant.
- 🔧 **K171** → ARSIVDE · gizli kaynak
- 🔧 **K135** → ARSIVDE · `cgt-ekle.py::fetch()` tek satir UA ile CGTrader WAF'ina takiliyor (HTTP 202 + placeholder); kalici `--yerel` yolu KraL'da, sonraki dilim oncesi · kabul: alani BOS.
- 🟠 **K139** → ARSIVDE · gozcu `8,23,38,53` (15 dk); ci-nobeti `7
- 🟠 **K144** → ARSIVDE · ardarda push'lar build'i `cancelled` eder (ARIZA DEGIL); hukum guncel
- 🔧 **K140** → ACIK_KALEMLER · ikinci kopya ARSIVE indi 4/5, `KraL-K309D2`: kapi EVREN KAYNAGI hatasi (cip evreni kuratorlu) · kabul: `marka-invaryant-kapisi.py` 7 jeton DUSMUS + `Rover` DURUYOR + mutasyon 4/4.
- 🔧 **17 Agu KALEMLERI:** K163 · K162 · K157 (⚖️ Okan, 22 Agu) · K158 · K146 · K142 (MaCiT) · K118. TAM METIN ARSIVDE.
- 🔴 **K104 / K104B:** nobet sicili + iki kapi main'de kirmizi. HUKUM MIMARDA. · **K99**
  bag kolonu · **K100** satir-sonu muafiyeti · **K102** yasakli ic dosya adi.
- 🟠 **K152** → ACIK_KALEMLER · (ikinci kopya ARSIVE indi 3/5, `KraL-K309D2`: kabul araci main'de YOK)
- 🔧 **Iki acik kapi kalemi:** (a) shop bayatlik TETIK ekseni ≠ bundle evreni; (b) `devam-sinif-kapisi.py`
  is-akisi muafiyeti `norm`/`ham` ayrisiyor. · 🟠 **K122:** `kurtarma/k122-yabanci-is` dali DURUYOR. ARSIVDE.
- 🔧 **K151** (17-19 Agu): TAM METNI ARSIVDE (20 Agu 1:1 tasima blogu). · 🔧 **K161** → ISARETCI: KAYNAK-DOGRUSUNDA (26 Agu, `KraL-K309D2`).

## OKAN'DA
- ✅ 25 Agu penceresi: 9 kalem kapandi → [[okan-25agu-kapatilan-konular]]; 🔴 yeniden ACILMAZ.
- 🔧 **K297·K298·K299·K300·K301:** SERIT B hijyen kirmizisi · iki ayri K29 · K86 metni bayat ·
  K55 sayisi **197** · `T4-OLCUTSUZ` tum evlerde. Tam metinler KUTUDA.
- 🔧 **K329 (28 Agu, CI nobeti):** iki kapi dosyasi kanonik `git_ortami.sentetik_git`'e gecirildi, yerelde YESIL olculdu; main'e INEMEDI — kutu 306>300, 6 blok `ARŞİVLENEBİLİRİM` bekliyor (**Okan arsivi**), is `ci-nobet-git-ortami` dalinda stage'li.

## ARSIVDE — 14-20 Agu `DEVAM-ARSIV.md`'de.
