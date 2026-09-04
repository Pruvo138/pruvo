# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔁 4 EYL ~1x:xZ — YAYIN ACILDI (main `e53d56f6`, agac TEMIZ, **itilmemis 0**, worktree **0**)
**BaBa kuyrugunun ② ve ① kalemleri KAPANDI.** 16 commit `origin/main`'e gitti (`a3cac856..e53d56f6`);
D1'e **172 yeni urun** yazildi, geri-okuma **176/176 DOGRULANDI**, 172 kapak uretildi.
`--durum` ANA checkout'tan **rc=0**: 33860=33860 — SAYI · SAYAC · SEQ · SEMA · TURETILMIS KOLON ·
ICERIK, alti eksenin altisi ✅. (Ayni komut BAYAT dal agacinda 146 "FAZLA" bastirdi — sahte sapma,
karar DAIMA guncel main ana checkout'tan.)
**② D1 ASILMASI — SINIF KAPANDI (K361, merge `f2faddac`).** Terk edilmis `hungry-banach-7c4ce1`
cipinin isi COMMIT'LENMEMISTI; mimar eliyle **degistirilmeden** olculup kurtarildi (`b5f29bcc`).
Uc kol: zaman asimi (TAVAN=900 sn / TABAN=450, olculen en yavas *basarili* kosum 364,0 sn'nin
uzerinde; env TABANIN ALTINA INEMEZ) · TEK UCUS (ikinci kilit KURULMADI, mevcut flock ARAC koluna
parametreyle acildi; bekleme 480 sn ZAMAN ASIMI sayacina GIRMEZ ve SESSIZ DEGIL) · `npx` yok kolu
(cron PATH'i) · EPERM gecici npm cache artik SILINIR. Kabul **3/3 -> 33/33**, mutasyon **10/10**
(7 oldurucu + 3 kontrol), **HEDEF_KOL_ATFI 7/7** (K182 sarti). Iki batarya serit B'ye bagli.
🔴 **CANLI KANIT:** onarim oncesi `--durum` sifir ciktiyla sonsuz asiliyordu; sonrasinda **72,3 sn**
ve **69,3 sn**'de rc ile dondu, sonra ana agacta **71,4 sn / rc=0**.
**K373 kutu kimlik ekseni MERGE (`e53d56f6`, dal `funny-jepsen-5ceeba`):** kucuk harfli harness
adlari sekil kolundan gorunur. Kabul **49 vaka / 454 iddia / KIRMIZI=0**, mutasyon **33/33**,
YAMA_TUTMADI=0, **HEDEF_KOL_ATFI 32/32**, canli arac sha256 ESIT (mutant sizmadi).
Iki dalin da `ci-kapsam-test.py`'si KENDI agacinda YESIL; sizinti taramasi 0; kapsam 4 ve 2 dosya.
**TEMIZLIK:** iki worktree + iki dal, uc kontrolden (porcelain TEMIZ · `main..dal` BOS · dosya farki)
sonra kaldirildi -> worktree **2 -> 0**. Kutu push'ta kendi kendine doner: 5 blok / 48 satir arsive.
**BEKLIYOR — yaninda "neyi olcmek kapatir":**
· 🟠 **CI:** `e53d56f6` uzerinde 2/4 kosum SUCCESS, `Build & deploy` + `SERIT B` KOSUYORDU.
  *Kapatan:* SHA'yi ICEREN kosumun `conclusion` alani (bkz. `--limit 1` tuzagi). Onceki `a3cac856`'da
  SERIT B ve Paket-tazeligi ZATEN kirmiziydi — bizim degil, DEVRALINDI.
· 🟠 **41 yerel dal** main'e girmemis (43'ten indi). *Kapatan:* dal basina kapanis+merge ya da budama.
· 🟠 **HocA `hungry-panini-55aff5`** acik (baska ev). *Kapatan:* HocA'nin sayili kapanisi.
· 🔧 **`cip-kapat.py` KUSUR:** `--uygula` dal silme ayagi `branch 'HEAD' not found` veriyor.
  *Kapatan:* `worktree list --porcelain`den dal adi turetilip mutantla sinanmasi.
· 🔧 **`mimar-icra-kapisi.py`** (hasat evi): ucuncu tarafca silinmis worktree'nin cipi ROL=ANA'ya
  dusuyor ve kendi kapanisini yazamiyor. BENIM EVIM DEGIL. *Kapatan:* MaCiT/BaBa hukmu.
**DERS (kayda):** terk edilmis cipin isi PAYLASILAN agacta commit'siz duruyordu — kapanis yazilmadan
dusen her cip bu riski birakir. Olculdu: is saglamdi, kaybolmasi an meselesiydi. Ayrica cip kendi
govdesine yazamadigi bir ic rapor adini yorumda ANDI ve `ic-rapor-adi-kapisi.py` commit'i DURDURDU —
karsiliksiz atif genel ifadeye cevrildi.

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
