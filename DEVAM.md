# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔁 31 AGU ~21:1x — MIMAR OTURUM KAPANISI
**CANLIYA GIDEN:** main **`38b2d512`** = `origin/main` BIREBIR, agac TEMIZ. Merge edilenler: K352
`23bc7b0b` · K356 `f283d8e2` · K357 `ff1a7870` · Raymarine `13f0ecbc` (Okan emri) · **K358 `38b2d512`**.
**KOSUYOR:** 0. 🔴 **`KraL-Raymarine-31Agu` MERGE EDILDI `13f0ecbc` — benim "merge etme" hukmumu
OKAN'IN DOGRUDAN EMRI gecersiz kildi** (peer hukmu Okan'i ezmez, dogru is bu). Hukmun DAVRANIS kismi
yine de dogruydu: katki `tools/arama.py` **+19/-0**, BASKA DOSYA YOK, davranis ozdes (181/42/139, imza
True) — kazanc yalniz YORUM + K220 ikinci-rol olcumu (main'de, `HEAD:tools/arama.py` 1 isabet, ben
ayrica deftere de tasimistim). 🔴 **BAYAT TABAN UYARISI OLCUMLE BUYUDU:** "2 satir dusurur" dedigim
zarar, merge aninda **38 SATIR SILME** cikti (K359 · `task_9166f0e8` · MEMORY.md kalemleri dahil);
cip yakalayip `DEVAM.md`'yi `origin/main`'den aynen geri aldi. Bagimsiz teyit ettim: main'de K359 **2**
isabet, `task_c50a1c41` **1** isabet — **geri sarma YOK.** `nice-swanson-706912` = K358 dalinin agaci.
**KOSAN CIP:** `task_c50a1c41` **K360** (`youthful-montalcini-2e348f`) — MEMORY.md 22.222 B'dan 17,1 KB
altina; indekste KOMSU EV satirlari var, GIRDI SILINMEZ ([[indeks-ile-silme-komsuyu-siler]]).
**Kapatan olcum:** bayt < 17.510 VE bag 283=283 VE 20 bolum sayaci BIREBIR. · 🟠 K359 (asagida).
**OKAN'DA:** 0. ✅ **DEPLOY KOSULDU (Okan, 20:47Z) ve OLCULDU:** canli surum `d2d78692` @ `20:47:02Z`,
yayinlanmamis commit **0**, `shop-bayatlik-kapisi` **TAZE rc=0**; 5 saattir bekleyen K357 de indi.
(Onceki "deploy borcu YOK — 14:45:00Z" satiri **6 DAKIKA sonra** bayatlamisti; yas 324,9 dk'ya cikti.)

## ✅ K358 MERGE EDILDI `38b2d512` (dal `claude/jovial-engelbart-1a1040` @ `f7695966`)
Kesin-basarisiz iyzico kodlari UCUNCU SINIF oldu; `terkSupur()`'un ZATEN VAR olan `iptal` kolu fiilen
acildi. Kume KAPALI + elle sayili (`5122`/`10054`/`10057`), yuklem TEK KAYNAK (`iyzico.js::
kesinBasarisizMi`) ve UCU BIRDEN arar (det VAR + iyzico "failure" BEYAN ETTI + kod kumede) —
bilinmeyen/bos kod, taninmayan `status`, `det` yoklugu ESKI fail-closed yolunda KALIR.
**MIMARIN BAGIMSIZ OLCUMU** (dalin agacinda, cipin raporundan DEGIL): `terk-supurme.mjs` **98/0 →
204/0** · mutasyon **10/10 → 15/15 YESIL** (12 hedef oldu, 3 kontrol oldurmedi, agac dokunulmadi;
mutant hedef-kol atfi `38b2d512` mesajinda) · `olcum.mjs` 198/0 · `ci-kapsam-test` YESIL ·
`kisisel-veri-test` 5/5, siparis-no deseni **0** · kapsam 4 dosya/+446-9 · D1 **6/6, uyusmaz 0**.
🔴 **ZAMANLAMA OLCULDU (Okan'in "yarin sabahki tur" beklentisi YANLIS):** siparis no
`Europe/Istanbul` uretir (`siparis-no.js`) → bugunku 17:54:51 **+03** = `14:54:51Z`; esik 24 sa, cron
`17 * * * *` UTC → o satir pencereye **1 Eyl 14:54:51Z**'de girer, goren ILK tur **15:17Z = 18:17
yerel**. Sabah DEGIL aksam turu. Eskiyen 5 satir icin ilk tur ise **31 Agu 21:17Z** (deploy 20:47Z).
🔧 **ACIK — UCTAN UCA KANIT (cip `task_77e7c185`, SALT OKUMA):** 21:17Z turunda beklenen ve ONCEDEN
civilenen sayilar: `bakilan`=5 · `iptal`=5 · `degisen`=5 · `ulasilamadi`=0 · `odendi`=0 · `incele`=0,
`atlandi`=`kesin-basarisiz`; ikinci eksen D1 `bekliyor` **6 → 1**. `ulasilamadi>0` cikarsa kod KAPALI
KUMEDE DEGIL demektir — kumeye kendiliginden EKLENMEZ, hukum mimarin. `odendi>0` = para kurtarildi,
"terk" onculu o satir icin YANLISTI → derhal Okan'a.

**TEMIZLIK (bu oturum):** worktree **4 -> 2** — kaldirilan `bold-keller-82f052` + `nice-swanson-706912`;
IKISININ DE `status --porcelain` ciktisini **kendim** okudum (cipin beyaniyla DEGIL — beyan bir kez
curudu, [[temizlik-beyani-dogrulama-turuyle-curur]]), ikisi de BOS ve icerikleri `--is-ancestor` ile
main'de. Kalan 2 = ana agac + CANLI K360 cipi (`youthful-montalcini-2e348f`, DOKUNULMADI). Yerel dal
**13 silindi** (`durum.py` "artik" siniflamasi + 2 merge edilen dal). Gecici dosya: yalniz 2 cipin
bekledigi spec, scratchpad'de.

## ✅ K355/K356 + K358 SPEC TURU — TAM METIN `DEVAM-ARSIV.md`'de (kural 11)
Ikisinin de acik kalemi yukaridaki **K358 MERGE** blogunda KAPANDI. Arsivde duran: K356'nin canli
`errorCode` dagilimi (`5122`x3 + `10057` + `10054`, tahsil edilecek para YOK, `degisen=0` DOGRU) ·
"gecici ariza" ve "token omru yapisal" hipotezlerinin CURUTULMESI · K358'in spec turu (oncul
duzeltmesi: kol zaten vardi, sinif iki kovaliydi) ve civilenen taban (98/0, 10/10).

## ✅ K353 + T1/T2 + K354 (29-30 Agu) — TAM METIN `DEVAM-ARSIV.md`'de (kural 11)
🔴 **CANLI TALIMAT, SILINMEZ:** K353 merge'unden SONRA `kanca-kur.py` kosulur (once kosulursa filo felci).
✅ **O TALIMAT KAPANDI — SARTI OLCTUM, TUTUYOR** (`nice-swanson-706912` KALDIRILDI): Okan'in 30 Agu
hukmundeki 3 arac main'de KALICI — `git ls-tree HEAD` 5 dosya (`chip-duzeni-kapisi.py` ·
`mimar-commit-kapisi.py` + `-test` + `-mutasyon` · `worktree-tavan-nobeti.py`). Dosya varligi YETMEZ
diye kablolamayi da olctum: `nobet.yml:2116-2119` chip-duzeni + mimar-commit bataryalarini KOSUYOR
(`continue-on-error` YOK). `worktree-tavan-nobeti` o adimda BILEREK yok — gerekce dosyada YAZILI
(dis batarya HIC yok, olculdu; nobetcisi kendi `--kendini-test`i + pre-push rapor-only kolu).
`ca8c3815` KAZA DEGIL KASITLI supurmeydi ([[silme-kaza-mi-karar-mi-silenin-kapanisina-bakilir]]).
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
