# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔁 3 EYL ~17:5xZ — MIMAR OTURUM TURU: KUTU ACILDI + K372 DALI ALINDI + FILO TEMIZLIGI (`249a0c5a`)
**① ORTAK KUTU KILIDI ACILDI:** kutu **277 satir/51.330 B** (tavan 250) → `defter-kota-kapisi.py`
kovasi **`KUTU_ASILDI` rc=1**, BES EVIN commit'i kilitliydi. `kutu-arsivle.py` kosuldu: 5 blok/83
satir arsive TASINDI, `lossless_dogrulama=GECTI` (iddia=22, oksuz_govde 0/0), KAYIPSIZLIK blok
25=20+5 ∧ bayt 51330=37652+13678 → kapi **`KUTU_YESIL` satir=199**. Cevrilen kapanis jetonu 0
(3 jeton KAPANIS KONUMUNDA DEGIL = govde anmasi, K318 KOL-1).
**② `claude/focused-faraday-ba999a` (K372 + K372-b) MAIN'E ALINDI — merge `249a0c5a`, push'landi.**
Kapsam merge-base `eac21869`'den **10 dosya +643/−19** (hepsi kod/test/CI; `urunler.json` diff **0**,
sizinti deseni 0). Cakisma YOK; FF-ONLY IMKANSIZ (yerel main tabandan 4 commit ileride) → merge commit'i.
Olculdu DALIN agacinda: `olcu-en-buyuk-parca-test` **VAKA=7 IDDIA=37 GECTI=37** (4 mutant hedef-kol
atifli + kontrol + TEK KAYNAK kolu + okuyucu envanteri 6/6) · `olcu-saglik-test` **8/8** ·
`ci-kapsam-test` **YESIL**. KOMSU ONCE=SONRA (dal vs main, 7 kapi): 6/6 rc=0 IKISINDE DE AYNI;
🔴 `denetim-kapisi-test.py` **IKISINDE DE rc=1** (taban-alti fiyat, Motosiklet 4) — ONCEDEN kirmizi,
dalin isi DEGIL, **kalem ACIK**. Merge sonrasi `d1-sync.py --durum`: **33443** — SAYI/SAYAC/SEQ/SEMA/
TURETILMIS-KOLON/ICERIK eksenlerinin **hepsi** ✅ (hash UYUSMAZ 0 · EKSIK 0 · FAZLA 0).
**③ TEMIZLIK (Okan disk kurali):** 2 worktree kaldirildi (ikisi de porcelain TEMIZ, icerikleri main'de)
→ `.claude/worktrees` **105 MB → 8 KB** · main'e tam merge olmus **8 yerel dal** silindi (her biri
`merge-base --is-ancestor` ile ayri ayri dogrulandi), yerel dal 48→**40**.
**④ OTURUM ARSIVI (Okan emri, bu turda):** bitmis **31 oturum** arsivlendi — 16x `Gunluk mimar ihtar`
+ 14x `Teftis takip` + `Tamirci ŞERİT B` cipi (isi `45f0df8e` ile main'de). DEVAM'daki "24 bitmis
oturum arsivi" kalemi KAPANDI. Acik kalan oturumlar 5 mimar evi + FaR/ZeN/OTEL + baska evlerin
CANLI cipleri (MaCiT x2, FaR x2) — bunlar bu evin hukmu DEGIL, DOKUNULMADI.
**⑤ TABAN-ALTI FIYAT KALEMI KAPANDI (Okan karari, bu turda soruldu-yanitlandi):** `denetim-kapisi-test.py`
31 Tem'den beri kirmizi tutan gercek-veri nobetcisi — o gun **1.761** kayit taban altindaydi, bugun
kalan **4**'tu (3x Yamaha MT-07 fren hazne braketi 150/175/150 TL + 1x Ducati 748 yakit sensor somunu
150 TL). Taban `FIYAT_TABANI=200`, `kademeli_hedef` dordu icin de **300 TL**. `duzelt.py --toplu` ile
TEK kilit + TEK yazimda uygulandi (guard manifesti, 4 urun/4 alan/0 silme) → **KAPI 7 IHLAL 4→0**,
`denetim-kapisi-test.py` **rc=1→rc=0** (31 Tem'den beri ilk). Commit `450e5b0e`; pre-push D1'i
senkronladi + **geri-okuma 4/4 dogrulandi**, bagimsiz `--durum` alti eksen ✅ (33443, UYUSMAZ/EKSIK/FAZLA 0).
**⑥ CANLI DOGRULANDI (kapanistan once, kanonik URL + cache-bust'SIZ):** deploy `249a0c5a`'yi 18:01Z'de,
`450e5b0e`'yi 18:16Z'de yayinladi; `durum.py` 9 **TIKALI→🟢 AKIYOR** (girerken canli `c2a58cdc`, 122 dk
gecikme). `https://pruvo3d.com/urunler.json` → **33443** kayit, dort duzeltilen id de **300 TL**.
Yabanci ` M .diriltme-izin.json` ve MaCiT dilim-41 cipinin ` M urunler.json` yazimi DOKUNULMADI.
**MOTOR ORANI:** Claude tam · m3 0 · kimi 0 — is merge hukmu, kapi olcumu ve arsiv yargisiydi
(CLAUDE.md "Claude'da kalan"); m3'e inecek mekanik dilim cikmadi.

## ✅ 3 EYL — STL DOSYA ADI (Okan kalemi 2 Eyl) — cip `KraL-StlDosyaAdi-3Eyl` (`amazing-ishizaka-2d4a0f`, Fable 5.1)
`shop/src/yonet.js` `/stl-yukle`: `.STL` harf-duyarsiz + R2 anahtarinda kucuk uzanti; Turkce→ASCII (once NFC,
macOS NFD icin); guvenlik kolu AYNEN, her RED `kural` adiyla; normalize SONRASI cakisma da 409. Kod `1908cf1c`;
`urunler-panel.mjs` 127→**150/150** (I7-I21 + I-M: KONTROL + 3 hedef-kol mutant OLDU, gecici ayna silindi);
komsu CI testleri (panel-kaynak 41, panel-atif 46, kabul --yonet-cerez 72, konfigur-fail-closed 5/5, kisisel-veri) yesil.
🔧 **shop worker deploy = OKAN** (tek satir kutuda; canli deneme: ayni dosya adiyla yukleme gecer).
**Dilim-2 (BaBa hukmu 07:4xZ, ASCII anahtar KABUL):** kanonik fonksiyon UC okuyucuda — R3 `driveKaynaklari`
(Unicode sinif + kanonik etiket: Turkce ad KIRPILMAZ) · `stlIndir`/`stlCikar` (kanonik + eski ham ad) · NFC;
Tamirci `678fdbfd` bataryasi I-K olarak tasindi → `urunler-panel.mjs` **208/208**, mutant **6/6** oldu; dilim-1
CI `33728849026` SUCCESS. Tamirci dali MERGE EDILMEDI (hukum mimarda). `uretim-kaynak.mjs` K40 (KOL_TABANI 21≠22)
main'de ZATEN kirmizi — SERIT B, Tamirci dalinin isi, bende degil. D1 `--durum`: 1 FAZLA (33114≠33113) — 49ebe540
silmesinin izi, uzlastirici kosumu `33729490106` FAILURE (mimar/BaBa duzlemi, dokunmadim).

## 🔴 CANLI TALIMAT (K353 blogu ARSIVE indi, tam metin `DEVAM-ARSIV.md`'de)
K353 merge'unden SONRA `kanca-kur.py` kosulur (once kosulursa filo felci). 🔧 ACIK: T1a — worker deploy = OKAN kapisi.

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
