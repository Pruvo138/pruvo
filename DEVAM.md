# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## ✅ 2 EYL — ACIK KUYRUK BOSALTILDI (kalan tek olcum: 15:47Z A3 teyidi)
`~/.claude/cron` **VERSIYONLANDI** (yerel depo, uzak YOK): 328 betik, BEYAZ LISTE
(`*` reddedilir, yalniz betik uzantilari acilir) — dizinde CANLI API anahtarlari + tarayici
profili + m3 jsonl'lari var; kara liste unutulan tek deseni SESSIZCE gecirirdi. Kabul: izlenen kumede sir
isabeti **0** (fail-closed; isabet olsaydi depo geri alinacakti). SONRA `.yedek` supurmesi
MESRU oldu: **175/175 kaldirildi (5,18 MB)**, her biri silinmeden once `cat-file -e` ile
gecmiste KANITLANDI; 4 tanesi beyaz liste disi kaldigi icin ONCE versiyonlandi SONRA silindi.
`kral-sabah.py` ayrismasi KAPANDI (`067d473e`): K356 yalniz CANLI kopyadaydi; repodaki 10
"fazla" satirin hepsi K356'nin degistirdigi ESKI kod cikti, yon TEK (canli→repo). `kur.py`
KOSULMADI (K357). Cron `parti-surucusu` satiri **GERI ACILDI** (BaBa hukmu) — oncul
SINANDI: hasat'ta `isci/parti-28`+`isci/parti-yamaha-d9` duruyor, KAPI-1 gorunce m3
cagirmaz, ilk tik $0. crontab 81→82 satir, hedef disi satirlar BIREBIR.
TEMIZLIK: 3 cip agaci kaldirildi (raporlari once arsive tasindi, 38 KB) · **47 dal silindi**
(6 yerel + 41 uzak; olcut UC KATLI, `ileri>0` olan 79 dala DOKUNULMADI — K337 dersi) ·
`yedek/k337-olcum-08276ead` KORUNDU. Kapanista 6 kapi YESIL, agac temiz, worktree 1.

## ✅ 2 EYL — GUNUN INEN ISLERI (TAM METIN ARSIVDE; hepsi `origin/main`de, `is-ancestor` ile teyitli)
K361 `2562741f` (ev tablosu repo DISINA) · SERIT B tamiri `4b28c796` (5 kirmizi kokunden) ·
onarim `3930fe33` (K361'in CI'da biraktigi kirmizi — kendi simulasyon hatam) · K337 `7ac9880f`
(2 ic olcum dosyasi MERGE DISI, girseydi `kisisel-veri-test` rc=1 ile TUM EKIBIN yayinini durdururdu) ·
K372 `765eeb29` (yayin-yasi nobetcisi yanlis alarmi: bekleme yasi YAZILMA degil GIRIS anindan) ·
K373 `7e14eeaa` (kapi sozlesmesi 2->3 kol + `schedule`; SERIT B artik garantili hukum alir) ·
K375 `bdf5425e` (23:00 gunluk motor raporu; cron CANLI, kabul 21/21 mutasyon 6/6).
**SERIT B kirmizi adim 17 -> 10** (CI'nin kendi adim listesinden, kume farkiyla).

## ✅ K353 + T1/T2 + K354 (29-30 Agu) — TAM METIN `DEVAM-ARSIV.md`'de (kural 11)
🔴 **CANLI TALIMAT, SILINMEZ:** K353 merge'unden SONRA `kanca-kur.py` kosulur (once kosulursa filo felci).
✅ **"3 ARAC KALICI OLANA KADAR AGAC KALDIRILMAZ" SARTI OLCTUM, TUTUYOR** → `nice-swanson-706912`
KALDIRILDI (olcum: `ls-tree HEAD` 5 dosya + `nobet.yml:2116-2119` iki bataryayi KOSUYOR; ucuncusunun
disarida kalmasi dosyada GEREKCELI. Ayrinti arsivde.)
🔧 **ACIK:** T1a — worker deploy = OKAN kapisi; "deploy edildi (`b26cedd8`)" iddiasi CURUTULDU.

## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)
- 🟠 **K359 (cip `task_c6f5192b` sirada) — 🔴 DEVRALDIGIM TARIF YANLISTI, YENIDEN OLCTUM.** Bana
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
