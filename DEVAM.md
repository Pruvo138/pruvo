# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔁 4 EYL ~03:5xZ — MIMAR OTURUM KAPANISI (`9927c03f` = `origin/main` BIREBIR, agac TEMIZ)
**CANLIYA GIDEN (bu oturum, 7 commit):** `249a0c5a` K372 dali (olcu TEK KAYNAK `olcu_parca` +
hasat_ekle RED kapisi) · `450e5b0e` taban-alti 4 fiyat 300 TL · `40753159`+`042d7ca2`+`729ed1f8`+
`5668a9c3` ARSIV KAPISI · `9927c03f` CIP KAPANIS KANCASI · defter/kutu commit'leri.
**① KUTU:** girerken **277/250 `KUTU_ASILDI`** (bes evin commit'i kilitli) → gece boyunca **5 kez**
kanonik rotasyon, her biri `lossless=GECTI`; cikista **`KUTU_YESIL` satir=242**.
**② K372 DALI ALINDI** (`claude/focused-faraday-ba999a`): kapsam merge-base'den **10 dosya +643/−19**,
`urunler.json` diff **0**, sizinti 0. Dalin agacinda `olcu-en-buyuk-parca-test` **7 vaka/37 iddia/37**,
`olcu-saglik` **8/8**, `ci-kapsam` YESIL; 7 komsu kapi dal↔main **ONCE=SONRA ayni**. D1 **33443** 6/6 ✅.
**③ TABAN-ALTI FIYAT KAPANDI (Okan karari):** 31 Tem'de 1.761 kayit taban altindaydi, kalan **4**'u
`duzelt.py --toplu` ile 150/175→**300 TL** (kural kendi `kademeli_hedef`i, yeni sayi URETILMEDI) →
`denetim-kapisi-test.py` **rc=1→rc=0, 31 Tem'den beri ILK**. D1 geri-okuma 4/4; canli dogrulandi
(kanonik URL, cache-bust'siz): 33443 kayit, dort id de 300 TL. Yayin ekseni **TIKALI→🟢 AKIYOR**.
**④ ARSIV KAPISI KURULDU** (`tools/arsiv-kapisi.py`): `archive` worktree'yi SILER, kirli agac ya da
main'de olmayan icerik SESSIZCE kayboluyordu. 4 kol UC HALLI, fail-closed rc=0/1/2; K4 hukmu
`kutu-arsivle.py::kapanan_cipler`den IMPORT. Kabul **11 vaka/37 iddia/37 GECTI**, mutasyon **9+kontrol
KIRMIZI=0**. Ilk canli kosumda UC gercek korluk bulunup kapandi: kardes evlerde K4 hep OLCULEMEDI ·
rotasyonla arsive tasinan kapanis GORUNMUYORDU · karar satiri rc=1'i COKME gibi gosteriyordu.
**⑤ CIP KAPANIS KANCASI KURULDU (`9927c03f`) — Okan emri, ALTI EVDE CANLI** (`pruvo · hasat ·
pazarlama · bot · jenerator · faralya`; advisor HARIC, BaBa cip acmiyor). `Stop` kancasi cip agacinda
kapiyi kosturur, `rc≠0` ise oturum DURAMAZ. Sozlesme docs'tan degil BU MAKINEDE olculdu (gecici sonda
kuruldu, log alindi, sonda+log+tetik SILINDI): bloklama **stdout-JSON + exit 0**. Iki emniyet kolu
kod govdesinde belgeli; mimar oturumlari MUAF. Kabul **11/11**, mutasyon **4+kontrol KIRMIZI=0**
(ilk turda dordu de ULASMADI — kusur kancada DEGIL bataryadaydi: `kos(kanca=…)` iletilmiyordu).
**KOSUYOR:** MaCiT ana oturumu (hasat). Bu evde koşan cip **YOK**, worktree **YOK**.
**BEKLIYOR:** 🟠 **39 yerel dal main'e girmemis** — hicbirinin kutuda kapanisi yok, merge prosedürü
rapor+curutucu ister; hicbiri bu oturumun isi. · 🟠 **MaCiT'te 4 cip** (`suspicious-chatelet` 13 dosya
+1970 · `recursing-yalow` 1/+27 · `admiring-ardinghelli` 1/+37 · `eloquent-hawking` 31/+5536) —
dordu de ITILMIS ve agaci TEMIZ, eksik olan MERGE + iki KAPANIS; **spec kutuda, icra MaCiT'te.**
*Neyi olcmek kapatir:* dort agacta kapi `rc=0` ∧ `ACIK_BASLIYORUM` listesinde bu dort ad YOK.
· 🟠 **FaR:** `MaiL SUREKLI cip` 24 saatte **%18,91** yakti; olcum+spec kutuda, icra FaR+BaBa'da.
*Neyi olcmek kapatir:* sonraki 24 saatte payi **<%5** ∧ yeni transcript >400 tur / >250K zirve YOK.
**OKAN'DA:** FaR/BaBa spec hukmu · cron kadansi (%1'lik, `Teftis takip`+`Gunluk mimar ihtar` gunde 2)
· tek oksuz hafiza `defter-tavan-bagli-rotasyon.md` (indeksle ya da sil).
**TEMIZLIK:** scratchpad **0/0 B** · pycache 0 · worktree 0 · sonda+log SILINDI · gun icinde 105 MB
worktree + 8 dal + 31 oturum + 1 olu zamanli gorev.
**HAFIZA NOBETI (yargi YOK):** memory **387** dosya · OKSUZ **1** (yalnizca RAPOR) · bu turda
degisen: `mimar-posta-kutusu.md`, `mimar-posta-kutusu-arsiv.md`.
**OZ-OLCUM:** **592 tur · zirve 545.827** → iki esik de ASILDI; sonrakini 400 tur / 250K'da kes.
**MOTOR ORANI:** Claude tam · m3 0 · kimi 0 — is kapi/kanca kodu, sozlesme olcumu ve merge hukmuydu
(CLAUDE.md "Claude'da kalan"); BaBa'nin 4 Eyl 09:00 sablon odevi ACIK, sonraki tura kaldi.

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
