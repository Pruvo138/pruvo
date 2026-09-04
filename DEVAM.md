# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔁 5 EYL ~01:xZ — BaBa 4 KALEM (main `074d7c9f` YERELDE · origin `e021e922`)
**KAPANAN:** ① D1 · ② KORUMALI blok tasinmaz · ④ filo dersi 5 evde · **Okan: ArTisT sayfa izni.**
③ baglam kotasi kapisi YAZILDI + 6 evde KURULU, commit YERELDE — push CI kapsam kapisinda DURDU.

**① D1** (`e021e922`): her wrangler cagrisi KALICI OZEL cache'te (soguk 27,9 → isinmis **1,4 sn**;
`--version` kabul GECTI). Tavan iki kollu: ISINMIS **120** sn (olculen en yavas 11,1) · SOGUK **450**
(olculen 307,1) — tek 120 mesru doldurmayi keserdi. `10043` GECICI kovasina alindi: tam senkron
onunla rc=1 dustu, retry YAPILMADI, 51 urunluk yazma bosa gitti; AYNI komut degisiklik olmadan rc=0
verdi (geri-okuma **51/51 ✅**). Kabul: tani-test **39/39** · mutasyon **13/13, OLDUREN 10/10,
HEDEF_KOL_ATFI 10/10, YAMA_TUTMADI 0** · `--kendini-test` 157/0.
🔴 **Batarya kendi KALICI kaynagini SILMISTI** (E kolu `finally`si ayrim yapmiyordu; cache **0 B**
olculdu) — E3/E4 ile ayrildi. 🟠 `--durum` **rc=0 ama 71,2 sn** (kabul <60): 42,25 sn'si YEREL
turetim (`marka_kanon` 20,59 + `model_kanon` 20,41), wrangler DEGIL. Tekillestirme denendi,
**olculdu ve CURUDU** (pencere isabet etmiyor: `evren`/`ek` her cagride yeni nesne) → GERI ALINDI;
kanonik uretici yoluna no-op kod BIRAKILMADI. *Kapatan:* iki ureticinin kaynak nesnesi TEKILLESIP
`--durum` 60 sn alti.

**② KORUMALI** (`e021e922`): basliginda `KORUMALI` gecen blok rotasyona GIRMEZ (K329 ile ayni konum
olcutu, `sabit_indeksler`e 4. kaynak). Kabul **50 vaka / 466 iddia**; mutant vetonun yuk tasidigini
gosteriyor. CANLI: 22:2x BaBa blogu arsivden kutuya GERI TASINDI (arsivde 0 / kutuda 1, satir
bazinda kayipsiz), gercek rotasyon `KORUMALI_ETIKETLI=1 kilitledi=1` basti, blok YERINDE ATLANDI.

**③ BAGLAM KOTASI — kabul 23/23** (2 OLDURUCU + KONTROL + disk). 6 evin `settings.json`'una
KANONIK YOLLA baglandi (kopya YOK → bayatlik yapisal olarak imkansiz), geri-okuma teyitli.
🔴 **CANLI KANIT — KAPI KENDI YAZARINI RED ETTI:** bu oturum **591 tur / 501K**; kapi once commit
betigimi, sonra CI kablosunu kesti. 🔴 **ILK KOSUMDA BULUNAN TASARIM KUSURU:** kapanis sinifi,
BEKLEYEN bir commit'in push'u icin gereken kabloyu (`.github/workflows` tek satir) KAPSAMIYOR →
koruma korudugunu durduruyor. *Kapatan:* kapanis sinifi bu hali kapsar + 1 vaka.
🟠 **NET-0 YAPILAMADI:** bayat kapi OLCULMEDI (`icra-kapisi.py` calisiyor); kor silme YOK.

**BEKLIYOR:** 🔴 `074d7c9f` PUSH EDILEMEDI — `baglam-kotasi-*.py` CI kapsam kapisinda KAPSAMSIZ.
*Kapatan:* `nobet.yml` SERIT B'ye `python3 tools/baglam-kotasi-test.py` adimi + push rc=0.
· 🟠 MaCiT CLAUDE.md **13.060 B** (tavan 12.288; benim filo satirimdan ONCE de 12.621'di) — net-0
kirpma MaCiT'te, baska evin kuralini KOR KESMEDIM. · 🟠 `gramer-artigi-kapisi.py` rc=1 (`6212540`).

## 🔁 4 EYL ~23:xZ — YAYIN ACILDI → **ISARETCI: tam metin `DEVAM-ARSIV.md` + commit `366dd3cf`**
Alti job'in altisi yesil (`deploy`+`yayin` SKIPPED DEGIL). Uc kalem, tam metin commit
govdelerinde: ① yabanci is kurtarmasi (`8b3d6ef2`) — SINIF: paylasilan tek-dosya duzleminde
`git add <dosya>` komsunun ucustaki partisini YUTAR, **stage birimi DOSYA degil KAYIT**.
② SLA yanlis-pozitifi = yayin acici (`366dd3cf`, `--kendini-test` 60/60 → 67/67).
③ UC DERS: mutant kirmizisi tek basina KANIT degil (K182) · kurucunun capasi kendi metninde
COGALIR → [[kurucu-capa-yeni-icinde-cogaltir]] · `gh run watch | tail` rc'si YALAN SOYLER →
[[boru-rc-isci-olcumunu-yalanlar]]. Kalan: 41 yerel dal main'e girmemis · `cip-kapat.py` dal
silme ayagi `branch 'HEAD' not found`.

## 🔁 4 EYL ~20:xZ — MIMAR OTURUM KAPANISI → **ISARETCI: TAM METIN `DEVAM-ARSIV.md`'de**
Yayin blokeri (d47, 12 ihlal) **KAPANDI** — bkz ustteki 23:xZ blogu. O turun merge'leri
(`f2faddac` K361 · `e53d56f6` K373 · `5c378aa5` kilit yolu · `f3548db5` sozluk 9. tur) main'de.

## ✅ 3 EYL — STL DOSYA ADI (Okan kalemi 2 Eyl) — KAPANDI, TAM METIN `DEVAM-ARSIV.md`'de
Kod `1908cf1c`; `urunler-panel.mjs` **208/208**, mutant **6/6**, dilim-1 CI `33728849026` SUCCESS.
🔧 ACIK ISARETCI: shop worker deploy = **OKAN KAPISI** (kutuda tek satir) · `uretim-kaynak.mjs` K40 SERIT B (Tamirci dalinin isi, bende degil).

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
