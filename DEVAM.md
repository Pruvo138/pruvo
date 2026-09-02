# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔁 2 EYL 15:3xZ — MIMAR OTURUMU (supurme turu; katalog 32.790, MaCiT partileri akiyor)
**SILME HATTI KAPANDI (Okan deploy etti):** `pruvo-shop` surum `1a964648` **13:52:59Z**; CANLI
bundle (387.811 B, CF API) `/urun-sil`=2 · `panelUrunSil`=4 · buton `Sil (arşive)`=1 (esbuild
ASCII kacisi — duz `arşive` aramasi 0 doner, TUZAK). Anonim uctan olculemez: yanlis anahtar da
yok-uc da 404 (tasarim) → hukum BUNDLE ICERIGINDEN verildi. Panelde buton RENDER ediyor;
🟢 **NEGATIF KOL CANLIDA:** yanlis onay id'si → "birebir ayni degil, kuyruga YAZILMADI", kuyruk
9/9 max id 9 bekleyen 0 DEGISMEDI, gerekce sorusu hic sorulmadi. 🔧 **POZITIF KOL BENDE BLOKLANDI**
(izin siniflandiricisi) → Okan panelden tiklarsa kuyruk satirini olcup Iptal ile geri alirim.
**SUPURME:** cip agaclari **237→107 MB** (`eager-shtern-b4ec5c` + `frosty-robinson-4ec3be`;
capalari `origin/claude/quizzical-nobel-b53ffb`'de DURUYOR — izlenmeyen 48 MB render `--force`
ile gitti, V5 HTML dalda commit'li, gorseller Okan'a teslim edilmisti). 3 dal silindi;
`yedek/k337-*` + `ileri>0` 40 dal DURUYOR. Canli iki agaca dokunulmadi.
**MaCiT'e HUKUM VERILDI (2 kez bildirmisti, 16 urun tikaniyordu):** `model` yazimi = aksan INER
(ASCII), ureticinin AYRAC yazimi KORUNUR, celiski karara tasinir, `arama.py` marka listesine
DOKUNULMAZ (K220). Rehbere yazildi. 🔴 **Onculu olctum, rapor YANLISTI:** 32.790 kayit/1534
model yazimi, celiski **0** → is migrasyon degil YAZIM KURALI; katalog verisi degismez.
**K359:** arac "tasinabilir blok tukendi 267>250" dedi (ev kilitleniyordu) → 7 bayat 31 Agu ACILIS
blogu ELLE, KAYIPSIZ arsive (kutu −5440 B / arsiv +5438 B, 7/7 birebir dogrulandi); kutu **218**.
**KOSAN CIPLER:** `task_cd35b252` K359 kalici onarim · `task_5b33bae3` V5 ana sayfa uygulamasi.
**BEKLIYOR:** 🟠 15:47Z `schedule` → `cron-nabiz` A3 · 🟠 parti cron tik 20:33 yerel ·
🟠 40 dal ileri. **OKAN'DA:** panel-tik pozitif kolu (tek tik, kobay kartinda).

## ✅ 2 EYL — PANEL TEKIL URUN SILME CANLI (Okan emri; cip KraL-UrunSilmeButonu-2Eyl)
Merge `8c018800` (dal commit `e35f092d`, origin/main atasi rc=0). Hat: /urun-sil (cift onay+
gerekce, yonetim anahtari) -> panel_ustyazim alan='sil' -> uygulayici duzelt --toplu {id,sil} +
arsiv/urunler-arsiv.json (GEREKCE public'e YAZILMAZ) -> build/D1 otomatik. Offline: uygulayici
VAKA=51 MUTANT=5/5 · urunler-panel 127 iddia · geri-yukle VAKA=7 · komsu bataryalar yesil
(V9d kol tabani 21'e karsi 22 TARIHLI beyan). CANLI KOBAY: kuyruk id=9 -> commit `460d8726`
(sil=1; katalog 32544->32543 commit sinirinda) -> sayfa 200->404 -> feed/sitemap iz 0 -> D1 6/6
(32543) -> GERI: `urun-geri-yukle.py` + `94096e9d` -> D1 6/6 (32544). 🔧 ACIK: worker deploy =
OKAN TIKI (`cd /Users/okan/dev/pruvo/shop && npx wrangler deploy`); deploy sonrasi panel-tik
provasi (Sil (arsive) butonu + STL'li urunde M12 kolu) olculecek. Yordam: tools/urun-silme-yordami.md.

## ✅ K353 + T1/T2 + K354 (29-30 Agu) — TAM METIN `DEVAM-ARSIV.md`'de (kural 11)
🔴 **CANLI TALIMAT, SILINMEZ:** K353 merge'unden SONRA `kanca-kur.py` kosulur (once kosulursa filo felci).
✅ **"3 ARAC KALICI OLANA KADAR AGAC KALDIRILMAZ" SARTI OLCTUM, TUTUYOR** → `nice-swanson-706912`
KALDIRILDI (olcum: `ls-tree HEAD` 5 dosya + `nobet.yml:2116-2119` iki bataryayi KOSUYOR; ucuncusunun
disarida kalmasi dosyada GEREKCELI. Ayrinti arsivde.)
🔧 **ACIK:** T1a — worker deploy = OKAN kapisi; "deploy edildi (`b26cedd8`)" iddiasi CURUTULDU.

## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)
- 🟠 **K359 (cip `task_cd35b252`, 2 Eyl; bayat `task_c6f5192b` geri cekildi) — 🔴 TARIF YENIDEN OLCULDU.** Bana
  "`kutu-arsivle.py` `✅…KAPANDI` bloklarinin KENDISINI acik sayiyor, 7 blok" diye geldi. Kutuyu blok
  blok olctum: **17 blok GERCEKTEN acik** (cip kapanis HIC yazmamis — arac HAKLI) · **1 blok sahte**
  (kapanis bloginin basliginda `basliyorum` yalniz TIRNAK ICINDE proza) · ve `macit-parti-surucusu`
  adinin **9 blogu**, kapanislari kutuda DURDUGU HALDE kilitli (arac `✅ … **KAPANDI (delta=0…)**`
  bicimini kapanis SAYMIYOR). **Kutunun 309 satira cikmasinin bas sebebi ARAC DEGIL, kapanis yazmayan
  17 cip.** Taban: `--kuru` `ACIK_BASLIYORUM=21 kilitledi=21`, test **40 vaka/303 iddia/0 kirmizi**.
  Kabul: test >303 + 0 kirmizi · sahte blok duser · `macit-parti-surucusu` listeden CIKAR ·
  kapanisi OLMAYAN adlar LISTEDE KALIR (hepsi duserse KIRMIZI) · 4 negatif fikstur · mutant >=4.
  🔴 `kilitledi=0` HEDEF DEGIL — 17 cipi serbest birakan onarim KUSURDUR.
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
