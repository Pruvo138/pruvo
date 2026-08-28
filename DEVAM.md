# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## K350 KAPANDI — teslim tatbikati + K331 kabulu + C: `llm_turu` bayat okuyucu; TAM HUKUM KUTUDA
`bekci-kabul` rc 1->0 (103/8 -> 111/0), NET VAKA 0, M2/M2b `F-SEBEP` ile yeniden OLUYOR; canli duzlem ONCE=SONRA.
K350-A: K332 CANLI DEGIL (`_ortak_altyapi_muaf` diskte YOK, yalniz `6941b626`). K350-B: `bekci-kabul.py` git DISI.

## 🔁 28 AGU 18:00 CANLI DURUM — OKAN 17:00 EMRININ BES KALEMI DE KAPANDI (onceden -> sonra)
🔴 **N2B BORU ONEKI SINIFI → HAFIZADA:** [[isci-cagrisinda-echo-stdin-etiketi-yutar]] (K345 ile kapandi).
🔴 **K337:** butce kesintisi sade `rc=1` donuyor, karantina dusus sayiyor (3 ardisik = 6 saat). META=RAF.
🟠 **OKSUZ AGAC (2):** `practical-dirac-a95ed1` -> `44c92f6e` (K258/K168 tek-kaynak modulu `serbest_cagrilar.py`)
ve `sweet-cartwright-b59181` -> `a24550ce` (`kutu-arsivle.py` jeton isleme) — oturumlari OLU, commit'leri
main'de DEGIL, tabanlari bayat (iki-nokta diff `urunler.json`'da 1828 satiri yanlislikla "silinmis" gosteriyor).
Cip `KraL-OksuzAgaclar-28Agu` tasiyor; **katalog geri sarilmayacak** (kabul sarti).
🔵 **WORKTREE 13 -> 11** (`trusting-sutherland-157a62` birlesmisti + oturumu oludu, kaldirildi). Kalan
agaclarin hepsinin oturumu CANLI ya da uzerinde birlesmemis is var -> dusurulmedi.
**BEKLIYOR:** MaCiT dilim'leri (K332 blokeri kalkti).
✅ **K330 KAPANDI** (`c1070d3d`, CI job `success` `33165127457`): batarya kendi tabanini sifirliyor
(3 beyanin birlesimi, izlenen yola DOKUNMAZ) + beyandan BAGIMSIZ fail-closed on kontrol
(`OLCULEMEDI: taban artikli` rc=3). Kok DARALDI: hukmu landing degil BILINEN yollarin tabanda
durmasi ceviriyor — uretilebilir. Ardisik UC kosum `TABAN_ARTIK_ONCE` 425-0-0, ucu de
`OLDURULDU rc=0`; `--kendini-test` MUTANT=4/4 KONTROL=3/3. → [[artik-yuzey-mutant-dedektorunu-korlestirir]]

defter kotasi 28 Agu: 12.287 B -> 8113 B (rotasyon, kayipsiz; arsiv 22204 -> 22254 satir)

🟢 **K344 OKSUZ AGACLAR KAPANDI (cip `KraL-OksuzAgaclar-28Agu`, main `a5fc8f22`):** iki dalin isi de main'de.
`44c92f6e` (A) +978/-303 · `a24550ce`+`c665031f` (B) +525/-50, ikisi de TASINDI (SUBSUME degil). 🔴 **Katalog
GERI SARILMADI: `urunler.json` 693.472 -> 693.472 satir BIREBIR**; "1828 satir silme" iki-nokta artefaktiydi.
`serbest-kume-tekkaynak-test` **19 vaka/4 KIRMIZI -> 22 vaka/0 KIRMIZI** · `mimar-kilit-test` 314/307 DEGISMEDI ·
bekci `--teslim-karari` YESIL · `kutu-arsivle --kapanislari-isle --kuru` ana agacta **`CEVRIM=1`** (K341'in civisi).
Worktree 11->10, disk 504M->454M. 🔴 **YENI KALEM K344-A:** A ve main'in K343'u AYNI sinif isi iki kez yapmisti;
K343'un M6/M7/M8 mutantlari bekci tablosunu bozup DEFTER CARE'inin RED olmasini bekledigi icin kirmiziydi (yanlis
eksene civili) — eksen `MX5`'e TASINDI (dar mutant: bekci RED, komsu defter GECER). 🔴 **YENI KALEM K344-B:**
`C3` yalniz kaynak->arac yonunu olcuyor; arac->kaynak yonu (araca eklenen bayrak tabloya yazilmamis) HIC olculmuyor —
`--kapanislari-isle` tam bu bosluktan dustu, elle kapatildi (`a5fc8f22`). Kabul: ters yon kolu + onu olduren mutant.

## 🔁 28 AGU 23:3x — OKAN EMIRLERI SIRAYA KONDU (mimar oturumu; icra chip'te)
- 🔴 **CLAUDE YAKIMI DURDU (Okan ~20:2xZ):** K340 cipine (`frosty-meitner-deb9f0`) SAYILI KAPANIS emri;
  yeni Claude cipi YOK — istisna urun kirmizisi + Okan isi. **CF ana sayfa TTL YESIL `BELGE_TTL_SN=600`**
  (Okan Save'e basti). K337 = dal `claude/nice-swanson-706912`, sahibi olu → META=RAF + oksuz-dal kalemi.
- 🔴 **NOBETIN LLM TUR-ACMA KOLU KAPATILIYOR (Okan ~20:0xZ, icra KraL):** cip `KraL-NobetLlmKolu-28Agu`
  acildi ve **A+B SAYIYLA KAPANDI:** `nobet-tetik-test` 81/0 KABLO=36/36 · `nobet-uc-kol-kabul` 26/26
  MUTANT=13/13 HEDEF_KOL_ATFI=13/13 · `cf-durum --kendini-test` 7/7 (taban 81/0·25/25·12/12, dusme YOK).
- 🟢 **NOBET A5 CANLI=YESIL:** 20:07:01Z gercek cron turu — `acilan_tur=0` · `tetik_karari=ACMA` SONDA ·
  `nobet_rc=KOSMADI` · `BITIS` bicimi BOZULMAMIS · fail-closed KIRMIZI ayagi CANLIDA calisti (`tetik_rc=11`
  → rc=1, degismezlik tuttu). 19:11:59Z'den beri `acilan_tur=1` sayisi **0**.
  🔴 **MENZIL DUZELTMESI:** tur acan tek yer `ci-nobeti.sh` DEGILMIS, `gozcu.py:831,857` de cagiriyor.
  HUKUM: **gövde (`nobet-kapi.py`) ENFORCER, `ci-nobeti.sh` olu cagri TEMIZLIGI**; "LLM turu 0" TEK eksende.
- 🟢 **K347+K348 BIRLESTI, SAATLIK SABIT KIRMIZI BITTI.** Teshis: gozcu susmuyordu, susan TURUN HUKMU;
  govde donusu jetonsuzdu → fail-closed `OLCULEMEDI` → nobet her saat KIRMIZI (bilgi tasimayan kirmizi).
  Care: adlandirilmis ucuncu hal `LLM_KOLU_KAPALI`, TEK KAYNAK, tum okuyucular ayni teslimde.
  **CANLI: 19:07 rc=1 · 20:07 rc=1 · 21:07 rc=0** (`sebep=LLM_KOLU_KAPALI KIRMIZI=0`, `BITIS` bozulmamis).
  🔴 **IKI TUZAK OLCULDU** (birim 8/8 YESIL iken): jeton kardes desene uydu → yama INERT; dogru desen TEK
  BASINA catch-all `ONARIM_DENENDI` → `URETKEN` beyaz listesi → **SAHTE YESIL** olurdu.
  → [[yeni-hal-cozucunun-varsayilan-kovasina-duser]]
  🔴 **CIVI CELISKISI, HUKUM (c):** hal `HUKUM=` satirina YAZILMAZ (degismez `HUKUM=TEMIZ ⇔ rc=0` kirilirdi);
  `TETIK_HUKMU` SONUNA `kol_hali=` alani eklenir (`tetik_karari` emsali). Kabul: **22:07 + 23:07**.
  ⑤ `onarim-durum.py` markoru YALNIZ o alandan okur; ara pencerede `ACIK` DEMEZ, `OLCULEMEDI` der.
- 🔴 **ISCI YALANI SAYACI = 2** (ikisi de `serbest-kume` icin "onceden vardi" atfi; temiz agacta 30/30
  KIRMIZI=0 olculdu, kirmizi iscinin `tools/` altina biraktigi ARTIKtan). **UCUNCUDE tekil yama YASAK.**
- 📌 **MERGE (K347+K348 sonrasi):** `wonderful-cerf-9d42fc` + `relaxed-wiles-04ee6e`.
- 🏗️ **SHOP PANELI — TASARIM DEGISTI; TAM HUKUM KUTUDA (`~00:1xZ`), burada ISARETCI.** Ilk tasarimin "okuma
  yolu taban ⊕ ust yazim" maddesi OLCUMLE CURUTULDU (urun sayfasi statik, fetch=0). YENI: `panel_ustyazim`
  duzlem DEGIL **YAZMA KUYRUGU**, **CI git'e yazan TEK kol**, `urunler.json` TEK okuma kaynagi. **T4 ZATEN
  CANLI** → korunacak; **T1 = panele "Urunler" sekmesi.** T1 kabulu ve gizli-alan siniri kutuda.
- 📮 Kutu 399 → **229 satir** (tavan 300; `kutu-arsivle --kapanislari-isle`, CEVRIM=6, lossless GECTI, 5 blok arsive).

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
