# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## ✅ 6 EYL ~17:xx — `KraL-CapaFikstur-6Eyl` [Opus 5]: **M7 CAPASI DIRILDI + fikstur 245/3 → 248/0; iki arizanin KOKU TEKTI**
**KALEM 1 — M7 capasi:** `d1-sync.py::ZORUNLU_KOLONLAR`in ESKI UCLU yazimina civiliydi; liste 2 kolon buyuyunce `CAPA-YOK(0)` → mutant AYLARCA uygulanmadi (`Marka arama D1 kolonu`nu koruyan eksen SESSIZCE OLU). Capa artik KAYNAKTAN TURETILIR (`m7_capa`); cozulemezse ADIYLA `CAPA-COZULMEDI` KIRMIZI. Batarya **17/1 → 18/0**, `CAPA-YOK` **1→0**, M7 ODURUYOR (`KALDI=1 GECTI=55`). Yeni `--kendini-test` **16/0** (sentetik BUYUTULMUS kolon listesinde capa hala cozulur) + `--mutasyon` **6 olduruc/2 kontrol**; ikisi de `nobet.yml::serit-b`ye BAGLI. Tam batarya (~20 dk) BILEREK CI disi — `ci-kapsam-test` bayat muafiyeti DOGRU yakti, kayit dustu.
**KALEM 2 — S8+SM1'in KOKU TEKTI:** `parite-marka-sinifi.js` katalog yolunu MODUL YUKLENIRKEN cozuyordu; harness surecinde `PARITE_URUNLER` yok → sentetik katalogun `marka_kanon` haritasi **URETIM katalogundan** turuyordu. (a) SM1: sentetikte `capa-3-3 → ["Volvo","Opel"]`, uretimde `→ null` (29.298 kayit) → `uyeMi` ucta FALSE / cocukta TRUE → `?q=Opel&marka=Opel` uc **3** / yerel **4**. (b) S8: `marka-kanon-uret.py` SENKRON, uretim katalogunda **~22 sn**, bedel ISTEK ISLEYICISINDE odeniyordu (`288ms ISTEK → 21860ms YANIT`) ve 8 eszamanli istek arkasinda kuyruktaydi → 400 ms esigi TEK SORGU siniflandirilmadan oluyordu; bu yuzden esigi 25→120 yapmak da zaman asimini 400→15.000 ms buyutmek de ISE YARAMADI. Onarim: yol CAGRI ANINDA cozulur + fikstur senaryonun `canli` katalogunu isaret eder. **245/3 → 248/0**, suit **22 sn/senaryo → 15,6 sn**. S8'de `/ara=33`: `susSonraAra:25` esigi ARTIK ASILIYOR (oncul KURULDU, beklenti gevsetilmedi).
**TESHISI ACAN OLCUM:** fiksture **UC DAGILIMI** sayaci basildi — "9 istek / 0-220 sorgu" tek basina teshis etmiyordu; `/ara=5 /katalog?sayfa=1` cikinca esik ayarlamanin korlemesine atis oldugu GORUNDU. 🔴 Ilk blok olcumu YUKLU makinede alindi → [[prob-kendi-baglamini-olcer]]; bos makinede tekrarlandi, sonuc AYNI, yuk hipotezi CURUDU.
**GERI ALINAN 2 ONARIM:** referans "isitma" cagrisi + kanon onbellegi — tek tek geri alinip olculdu, ikisi de S8'i **7/0** birakiyor. Tasimayan kod BIRAKILMADI.
**YENI KAPI** `tools/parite-fikstur-olcum-ortami-mutasyon.py` **4 olduruc (3 SM1 + 1 S8 zamanlama kolu) / 4 kontrol**, `nobet.yml`e BAGLI. Harness kurulumunda olculen iki tasarim dersi + K0 kontrol mutantinin gerekcesi `DEVAM-ARSIV.md` 6 Eyl ROTASYON blogunda (sinif geregi burada DEGIL).
**PARITE:** site **1334/1334 BIREBIR ✅** · Ege **897/897 BIREBIR ✅** · `ci-kapsam` ✅ · `is-akisi-kapisi` ✅. ⚠️ `nobet.yml`e DOKUNULDU (2 adim EKLENDI, hicbiri degismedi/silinmedi) — es zamanli cip var.

## 🔁 6 EYL ~10:5x — SERIT B taban **17 KIRMIZI ADIM** + 3 cip — **ISARETCI: TAM METIN `DEVAM-ARSIV.md`'de** (md5 birebir, eksik 0). Ucu de KAPANDI: `KraL-Hijyen-6Eyl` (6 adimin 5'i yesil) · `KraL-CipKapi-6Eyl` (6 adim + kutu kimlik ekseni) · `KraL-CapaFikstur-6Eyl` (yukaridaki blok). ArTisT'te KALAN: `lcp-onculuk-kapisi` 1 adim.
## 🔁 5 EYL — OKAN ①+② (`5b86ac20`) · K366+ayrac koruma (`299e9f9b`) · BaBa 4 kalem (`074d7c9f`) — **ISARETCI: UCUNUN DE TAM METNI `DEVAM-ARSIV.md`'de** (md5 birebir, eksik 0)
🟠 **BU UC BLOKTAN ACIK KALAN IPLIKLER:** MODEL adindan marka turetimi olculdu UYGULANMADI (Apple 56 · Samsung 20→31, AYRI eksen) · hafiza ekseni **SILAHSIZ** (`PRUVO_HAFIZA_EKSENI=silahli` arma GUVENLI rc=0, YERLESIM karari MIMARDA) · baglam kotasi kapanis sinifi bekleyen-push + yayin-kirikken hallerini KAPSAMIYOR (2 vaka) · `d1-sync --durum` rc=0 ama **71,2 sn** (kabul <60; iki ureticinin kaynak nesnesi TEKILLESMELI) · MaCiT CLAUDE.md **13.060 B** (tavan 12.288, kirpma MaCiT'te) · `lcp-onculuk-kapisi` rc=2 → **ArTisT**.

## 🔁 5 EYL ~18:xxZ — kutu kilidi KOK SEBEBI + kategori paneli (`ebdfb059`) — **ISARETCI (ikisi de KAPANDI)**
**DERS:** kapanis jetonu YALNIZ SON ICERIK satirinda araniyordu, o satir **imza**ydi → kilit ULASILAMAZ; [[kapanis-kimligi-worktree-adi-ilk-backtickte]] 3. eksen.
🔴 **AYNI SINIF, 2. YUZEY ACIK — `defter-rotasyon.py`:** 13/13 blok vetolu, `ILERLEME URETEMEDI` (**7. vaka**); defter ELLE indirildi (md5 birebir). *Kapatan:* veto kolu "acik kalem" ile "acik kalemi ISARETCIDE tasiyan blok"u ayirsin.
🔴 **ACIK — MaCiT duzlemi:** Elektronik `Kahve` 79 kayit **`marka` kirliligi** (`Mitsubishi` 19 GERCEK; kuratorluk GEVSEK, uyum %33,1).

## 🔁 5 EYL ~11:2xZ — **LCP/SITE HIZI ISI TAMAMEN ArTisT'E DEVREDILDI (Okan emri: "tamamen izinleriyle artiste devret")**
**IZIN ACILDI (kalici, `AGENTS.md` L10; git DISI):** ArTisT `pruvo`da `index.html`+`build.py`'ye **YAZAR**, dalini acar+**merge eder**; degisikligi KraL'da "yabanci" SAYILMAZ. 🔴 SINIR KraL'da: `urunler.json`·`arama.py`·odeme-fiyat·secret·sema.
Taban + 3 tuzak + cip devri **KUTUDA 11:2x blogunda**; kabul DEGISMEDI, kapanisi ArTisT yazar. **Okan'a cikan:** PSI anahtari.

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
