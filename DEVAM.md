# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## ✅ 6 EYL — `KraL-BorcKapisi-6Eyl` [Opus 5]: **T4: OKAN-KAPISI kilidi KALKTI + sessiz atlama KOL OLDU** (BaBa)
**(a)** T4-BORC sayimi **OKAN-KAPISI'ni SAYMIYOR** (`BORC_DURUMLARI`=ACIK/UCUSTA/🔧). PARSER sozlesmesi `ACIK_DURUMLAR` DEGISMEDI — onu 4 okuyucu daha okuyor (devir · korgoz x2 · parti-kapisi); daraltmak onlari oynatir. Baski KALDI: `OKAN_KAPISI=N` satiri + 23:00 ozetinde ayri satir. **FaR `acik_kalem=5` → `ACIK_KALEM=2` + `OKAN_KAPISI=3`.** Olcut kolu (K289) da BORCLU'ya daraltildi — yoksa `kabul:`siz tek OKAN-KAPISI satiri evi gene kilitler, (a) INERT kalirdi.
**(b)** Durum hucresi kanonik BES degerin disindaysa satir **ATLANMIYOR**: `T4-OLCULEMEDI durum gecersiz <kimlik>=<metin>` fail-closed RED. F08 kalibi (`ACIK (Okan kapisi KALKTI)`) iki kumeye de girmedigi icin **SESSIZCE ATLANIYORDU** = yanlis-yesil. 🔴 **TUZAK:** markdown AYRAC satiri 8 kolon uretip `kolonlar[5]="---"` verir — elenmeseydi HER defter kirmizi yanardi (kapi kendi ayracina takilir).
**FILO ON-OLCUMU (8 ev, ONCE):** gecersiz hucre **HocA 6 · KraL 7 · ORTAK 7 · digeri 0**. HocA'nin `OKAN-KAPISI (dusuk oncelik)` satiri **sessizce sayilmiyordu** → HocA `GECER`→`OLCULEMEDI` (KraL/ORTAK zaten RED). 🔴 Ev defterini KENDI duzeltir.
**KABUL:** `--kendini-test` **8/8 + KONTROL 1/1** (M-a/M-b IZOLE KOPYADA: benzersiz ad + `dont_write_bytecode`, canli govdeye yama YOK) · `--curutme` **4/4** · **OLDURUCU 3/3** · 23:00 ozet kolu **3/3** (T4 yok/cokuyor → `ÖLÇÜLEMEDİ`).
**YAYIN ✅:** `34041734321` @ `f22dfa96` **success**, 6/6 is yesil, **deploy+yayin zincirinde SKIPPED=0** (zincir-disi 3 = "yalniz KIRMIZI kosumda" adimi; onceki 2 success'te de AYNI → gerileme degil; ders KUTUDA).
**TABAN URETILDI:** `parti-kapisi` **12/13** + `korgoz` **KX=4/7** HEAD'de de AYNI → regresyon **0**. Yesil: `ev-haritasi` 9/9+4/4 · `chip-duzeni` 14/14+9/9 · `devir` 5/5+4/4 · `nobet-kabul` 51/0 · `is-akisi` · `ci-kapsam` · D1 34602 birebir. `nobet.yml` adim adi bayatti ("4 mutant"→8+1+4); kablo KORUNDU.
## ✅ 6 EYL — `KraL-CapaFikstur-6Eyl` [Opus 5]: **M7 capasi DIRILDI + fikstur 245/3 → 248/0** (uzunu ARSIVDE)
**M7:** capa `ZORUNLU_KOLONLAR`in eski uclu yazimina civiliydi → liste buyuyunce `CAPA-YOK(0)`, mutant AYLARCA uygulanmadi (koruma SESSIZCE OLU). Capa artik KAYNAKTAN TURETILIR; cozulemezse ADIYLA KIRMIZI. Batarya **17/1 → 18/0**, `CAPA-YOK` **1→0**, M7 ODURUYOR (`KALDI=1 GECTI=55`); `--kendini-test` **16/0** + `--mutasyon` **6/2** CI'da.
**S8+SM1 KOKU TEKTI:** `parite-marka-sinifi.js` yolu MODUL YUKLENIRKEN cozuyordu → sentetik katalogun `marka_kanon`u URETIM katalogundan turuyordu. SM1 uc **3**/yerel **4**; S8'de kanon ureteci SENKRON+**~22 sn**, bedel ISTEK ISLEYICISINDE (`288ms → 21860ms`) → 400 ms esigi TEK SORGU siniflandirilmadan oluyordu (esik/zaman asimi buyutmek ISE YARAMADI — ayrinti ARSIVDE). Yol artik CAGRI ANINDA cozulur → **248/0**
Yeni kapi `parite-fikstur-olcum-ortami-mutasyon.py` **4/4** (bagli); parite **1334**+**897** ✅.
## 🔴 6 EYL — SERIT B: **3 CIP KAPANDI (16 adim)**, 3 CIP ACIK; EV+OTURUM TEMIZLIGI YAPILDI
✅ **`KraL-Fiyat10x-6Eyl` BITTI** (main `d3dd8f6d`) — **PARA SINIFI (Okan emri):** tip sozlesmesi `fiyat`ta yalniz JSON tipini olcuyordu, `"250.0 TL"` de `str` → **616 kayit**, noktayi binlik ayraci sanan **3 okuyucuda ON KAT** (`price_number`+`feed_price`, ve `secenekler.js::fiyatSayisi` = **SEPET/ODEME**); `FIYAT_ARA_RE` ayni kaydi HIC eslemiyordu (10x ↔ FIYATSIZ celiskisi bile alarm uretmedi). 🔴 **TAHSILAT: 34 siparisin 36 kaleminde bu 616'dan HICBIRI YOK → yanlis tutar FIILEN TAHSIL EDILMEDI (0 siparis).** Tekil yama DEGIL: kanonik bicim + **TEK ayristirma noktasi** `arama.py`de, `katalog_alan_tip_sebebi("fiyat",…)` icine bagli → tum okuyucular tek kapidan fail-closed; 12 Agu'nun `"350 TL (12 cm)"`→**35012** ayrisimi da kapandi. VERI (`duzelt.py --toplu`): **bicim 616 / DEGER 0 / baska alan 0**; `###.# TL` **616→0**, toplam **34523** sabit. Panel kurusu **YUKARI** yuvarlar (`200,1`→`201 TL`), menzil bilerek DAR (ilk surum 2 redi kabule cevirmisti → daraltildi). OLCUM: **12/12** + **MUTANT 4/4** (M1="nokta yine binlik") + **KONTROL 2/2** · panel **218/218** · `ilan-tutari` **34523/34523 sapan 0** · parite **1334**+**897** · D1 **616, geri-okuma DOGRULANDI**. → [[tip-sozlesmesi-para-alaninin-bicimini-olcmez]]
**TABAN (olculdu, `34024037240` @ `b8816685`):** toplam **17** — `serit-b` 11 · `hijyen-a2` 2 · `hijyen-a3` 3 · `marka-invaryant-sayac` 1. Onceki tur: 19→17, kok "capa komsuya nisanliydi" (`b8816685`). YAYIN ACIK: `34024037115` deploy+yayin **success, SKIPPED 0**; D1 **34479** birebir.
🔴 **Push kosumlarinin `cancelled` olmasi ARIZA DEGIL, TASARIM** (`nobet.yml` L38-41): push grubu TEK, olcum `schedule` kolundan gelir — yogun gunde push kosumundan sayi beklenmez.
🟠 **ACIK 1 CIP `[Opus 5]`:** `KraL-CapaFikstur-6Eyl` (M7 capasi `CAPA-YOK(0)`, capa KAYNAKTAN turetilecek · `parite-fikstur-test.js` 245/3). KAPANDI: `CapaKapisi-6Eyl` · `Kota500-6Eyl`.
🟠 **MIMARDA — K133, 2 yapisal soru:** (a) model jetonuna marka sayfasi uyeligi (**21 markada kanon≠sayfa**) · (b) `marka[]` BOS + baslikta tam jeton (**159 kalem / 25 marka**). 🔴 Ikisi de [[k220-menzil-on-olcumu-uc-turdur-eksik]] menzilinde — on-olcum yapilmadan HUKUM VERILMEZ.
**TEMIZLIK:** worktree **2→1** (`gifted-curran-39fdbb` kapi hukmuyle kaldirildi + dal silindi) · defter rotasyonu 5 blok/10 dolu satir arsive, **eksik 0** (12.225→10.932 B).

## 🔁 5-6 EYL ISARETCILERI — **TAM METIN ARSIVDE** (md5 birebir, eksik 0). ACIK iplikler: MODEL adindan marka turetimi · hafiza ekseni SILAHSIZ · baglam kotasi 2 vaka · `d1-sync --durum` 71,2 sn · MaCiT CLAUDE.md 13.060 B · `defter-rotasyon.py` 13/13 vetolu · MaCiT `Kahve` 79 kayit · LCP ArTisT'te (Okan'a: PSI anahtari).
## 🔴 CANLI TALIMAT (K353 blogu ARSIVE indi, tam metin `DEVAM-ARSIV.md`'de)
K353 merge'unden SONRA `kanca-kur.py` kosulur (once kosulursa filo felci).

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
