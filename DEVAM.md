# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔁 31 AGU ~21:1x — MIMAR OTURUM KAPANISI
**CANLIYA GIDEN:** main **`d31d2613`** = `origin/main` BIREBIR, agac TEMIZ. Bu oturumda merge edilenler:
K352 `23bc7b0b` · K356 `f283d8e2` (errorCode logu) · K357 kanal gorunurlugu `ff1a7870`.
**KOSUYOR:** 0. `KraL-Raymarine-31Agu` KAPANDI — MUKERRER OLCULDU (dal `68e32d3f` kayit olarak durur,
MERGE EDILMEDI: davranis main ile ozdes + bayat taban DEVAM.md'den 2 satir dusururdu). `nice-swanson-706912`
yabanci, DOKUNULMADI.
**BEKLIYOR:** 🟠 K359 (asagida) · Okan tikini bekleyen 2 cip: `task_9166f0e8` (K358 odeme) ·
`task_c50a1c41` (K360 hafiza indeksi). **K360 SPEC'LENDI:** MEMORY.md **22.222 B** (kanca hedefi 17,1 KB,
okuma siniri 24,4 KB — asilirsa indeks HIC okunmaz, hafiza sessizce korlesir; pay ~2,7 KiB). Indekste
KOMSU EVLERIN satirlari da var ([[indeks-ile-silme-komsuyu-siler]]) → GIRDI SILINMEZ, yalniz metin
kisalir. Taban: 283 bag / 280 benzersiz hedef / hedefsiz bag 0 / 385 dosya / 20 bolum sayaci civilendi.
**Kapatan olcum:** bayt < 17.510 VE bag 283=283 VE 20 bolum sayaci BIREBIR.
**OKAN'DA:** 0 karar. Deploy borcu YOK — `14:45:00Z` dogrulandi.

**TEMIZLIK:** worktree **6 -> 3** (`sharp-hamilton-2796ff` · `KraL-TerkEdilmisOdeme-30Agu` ·
`infallible-benz-e131fe`; ucunun de `status --porcelain` BOS, ucu de main'de) · yerel dal **5 silindi**
(hepsi main'de) · bu oturumun gecici dosyasi: **0**.

## ✅ ODEME KARARI VERILDI (Okan, 31 Agu penceresi) → K358 SPEC'LENDI, cip `task_9166f0e8` sirada
Karar: kesin-basarisiz iyzico kodlari otomatik `iptal`e cekilsin. 🔴 **ONCUL DUZELTILDI:** kalem "yeni iptal
kolu ac" diye tasiniyordu — kol `terkSupur()`'de ZATEN VAR; kosmuyor cunku `odemeHukmu()` IKI KOVALI ve
`status!="success"` her seyi `altyapi-hatasi`ya atiyor, iyzico CEVAP VERDIGI (kod dolu) hal de oraya dusuyor
([[iki-kovali-siniflama-ucuncu-sinifi-yutar]]). Is = ucuncu sinifi ADIYLA ayirmak: KAPALI kod kumesi
(`5122`/`10054`/`10057`, her uyenin gerekcesi yazili) + TEK yuklem; bilinmeyen/bos kod ve `det===null`
FAIL-CLOSED KALIR (emniyet cekirdegi, ayri kabul ekseni). Iki tuketici de ayni turda olculur — `donus()`
canli musteri yolunda artik `incele`+Telegram yerine `basarisiz` yazacak, bu KASITLI ve ADIYLA olculecek.
**Taban civilendi:** `terk-supurme.mjs` **98/0** · `terk-supurme-mutasyon.py` **10/10 YESIL**. Kabul: test
toplami 98'den BUYUK + 0 kirmizi · mutant >=13, her biri HEDEF iddiayi oldurdugunu ADIYLA kanitlar.

- 🟠 **K359 (YENI, `KraL-Raymarine-31Agu` cipinden devraldim — sinif, her evde tekrar edecek):**
  `tools/kutu-arsivle.py` `✅ ... KAPANDI` bloklarinin KENDISINI ACIK "BASLIYORUM" sayiyor (govdede alt-dizge
  geciyor, #10/#15) VE kapanisi yalniz `SAYILI KAPANIS` basligindan taniyor — MaCiT cron'u `KAPANDI (delta=0…)`
  yazdigi icin kutuda 3 kapanis VARKEN arac 7 blogun hepsine "eslesen kapanis YOK" diyor. Kusur ARACTA mi
  BICIMDE mi: hukum mimarda. **Kapatan olcum:** eslestirici alt-dizge yerine BASLIK ROLUNDEN turetilir +
  fikstur (kapanisli/kapanissiz cift) ONCE yanlis SONRA dogru sayar + mutant.

## ✅ K355+K356 KAPANDI (31 Agu) — SUPURME "INERT" DEGILMIS: ODENMEMIS SEPET, tahsil edilecek para YOK
K356 `f283d8e2` main'de, deploy `14:45:00Z` dogrulandi, 18:17 supurmesi 5/5 SEBEP basti. DAGILIM
`5122`x3 + `10057` + `10054`. HUKUM: "gecici ariza" ve "token omru yapisal" IKISI DE CURUDU; ucuncu hal
ADIYLA **odenmemis sepet** — tahsil edilecek para YOK, `degisen=0` DOGRU. Tam metin ARSIVDE.
🟠 ACIK KARAR (Okan/mimar): kesin-basarisiz (`5122/10057/10054`) aged `bekliyor` → `iptal` kolu
acilsin mi — odeme duzlemi, yeni spec + kabul testi ister; elle gecis YOK.

## ✅ K353 + T1/T2 + K354 (29-30 Agu) — TAM METIN `DEVAM-ARSIV.md`'de (kural 11)
🔴 **CANLI TALIMAT, SILINMEZ:** K353 merge'unden SONRA `kanca-kur.py` kosulur (once kosulursa filo felci).
🔴 **CANLI TALIMAT, SILINMEZ:** `nice-swanson-706912` agaci, Okan'in 30 Agu hukmundeki 3 arac
(`worktree-tavan-nobeti` · `mimar-commit-kapisi` · `chip-duzeni-kapisi`) KALICI olana kadar KALDIRILMAZ;
`ca8c3815` KAZA DEGIL KASITLI supurmedir ([[silme-kaza-mi-karar-mi-silenin-kapanisina-bakilir]]).
🔧 **ACIK:** T1a — worker deploy = OKAN kapisi; kutunun "deploy edildi (`b26cedd8`)" iddiasi CURUTULDU
(SHA 5 evin HICBIRINDE yok). K353'un sayilari (kutu 253->196, defter esikleri, mutant kanitlari) arsivde.

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
  · 31 Agu K220-NEGATIFI OLCULDU (`Raymarine`, dal `68e32d3f`; main icin de GECERLI — dal/main turetilmis
  kumeler 5/5 OZDES, kontrol capasi dejenere degil): `uyum[].model`/`motor`/`marka`/`oem` = 0 · URL 1757=1757 ·
  kaybolan 0 · dogan 0. Yordam: izole ROOT, kume IKI bagimsiz eksenden (sitemap BEYANI + diskteki fiziksel
  yollar), ekleme ONCESI+SONRASI kosum, kiyas SAYIYLA DEGIL KUME FARKIYLA. Sayi-only kolun korlugu mutantla
  kanitli (bir sayfa oldurulup bir dogumla takas edildi: sayi-only 0 dedi, kume-farki YAKALADI). Yeni jeton
  bu iki olcumle ONCEDEN sinanir.

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
