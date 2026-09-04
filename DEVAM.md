# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔁 4 EYL ~23:xZ — MIMAR OTURUM KAPANISI (main `366dd3cf` = origin **SHA-BIREBIR**, agac TEMIZ, worktree 0)
**🟢 YAYIN ACILDI — uc itmedir kapali olan kol yesil.** `Build & deploy` `366dd3cf` **SUCCESS**,
alti job'in altisi: `serit-a2/a3/a4` ✓ `build` ✓ **`deploy` ✓ `yayin` ✓** (SKIPPED DEGIL).
Hukum API `status/conclusion`'dan alindi.

**① YABANCI IS KURTARMASI (TELAFI, yordam DEGIL):** itilmemis `39e5e5bb`, d47'nin 6 urunluk
metin duzeltmesinin YANINDA **MaCiT'in ucustaki 36 Harley urununu** de yutmustu (`+867/-6`). Commit
`commit-tree`+`update-ref` ile **yalniz 6 duzeltmeye indirildi** (`8b3d6ef2`); calisma agacindaki
dosyaya **ELIMI SURMEDIM** — yabanci is commit'siz kaldi (`git diff HEAD` = **925 satir, SALT
EKLEME, 0 silme**) ve **sahibi kendi itti** (`686ef449`, 38 canli). Push aninda D1 senkronu 39
kaydi dogru sekilde disarida birakti ("yalniz agacta 39 — senkrona GIRMEYECEK"), katalog 33977 sabit.
🔴 **SINIF:** duzeltme yamasi paylasilan TEK-DOSYA duzleminde (`urunler.json`) `git add <dosya>`
yaparsa komsunun ucustaki partisini YUTAR — **stage birimi DOSYA degil KAYIT olmali.**

**② YAYIN ACICI (`366dd3cf`):** `686ef449` serit-a3'u `denetim-kapisi` **IHLAL=1** ile durduruyordu;
tek ihlal **YANLIS POZITIF** — SLA = Sealed Lead Acid = **kursun-asit AKU**, stereolitografi DEGIL.
**OLCUM (tam katalog 34015 kayit): `\bsla\b` eslesen kayit = 1, hepsi aku baglamli, gercek ifsa = 0**
— jeton canlida SIFIR ihlal yakalayip BIR yanlis-pozitifle yayini durduruyordu. Jeton **SILINMEDI**:
kendi `surec-teknolojisi-sla` kuralina alinip **KURAL-YEREL** `eleme` suzgeci verildi. Ayri kural
SART — `eleme` CUMLE kapsamli; ayni kuralda kalsaydi ayni cumledeki GERCEK `fdm` bulgusunu da
susturur. Sinif, dosyada zaten belgeli `nozul`(otomotiv) / `SLS`(Mercedes suspansiyon)
istisnalariyla AYNI (tam gerekce ARSIVDE + commit `366dd3cf` govdesinde).
**KABUL `--kendini-test` ICINE GOMULDU (60/60 → 67/67, CI kolunda kosar):** 3 vaka · M1 [OLDURUCU]
`eleme->None` aku kaydi YENIDEN ihlal · M2 [OLDURUCU] naif tek-kural: gercek `fdm`
`['surec-teknolojisi']` → `[]` · M3 [KONTROL] davranis sabit · DISK sha once==sonra. Kardesler:
kardes bataryalarin DORDU de yesil (rc=0; biri 7/7 mutant) — ad listesi ARSIVDE.

**🔴 UC DERS (ucu de bugun CANLI olculdu):**
① **Mutant kirmizi geldi diye KANIT degildir (K182 yine).** M2'nin ilk hali kirmizi verdi ama sebebi
hedef kol DEGILDI (ana kuralda `eleme` yoktu, `fdm` kaybolmamisti). Karsi-olguyu kuracak bicimde
YENIDEN yazildi; ancak o zaman gerekce sayiyla dogrulandi.
② **Kurucunun capasi kendi yazdigi metnin ICINDE cogalir.** M3'un capasi (gerekce dizgesi) oz-teste
gomulunce **1 → 3** oldu, mutant HIC kurulamadi (`OLCULEMEDI` yandi). Capa, gerekce METNI degil
**KURAL BLOGUNUN TAMAMI** yapildi. → [[kurucu-capa-yeni-icinde-cogaltir]]
③ 🔴 **`gh run watch ... | tail` rc'si YALAN SOYLER:** boru rc'yi `tail`'e devreder — failure
kosumda **exit 0** dondu, deploy/yayin SKIPPED'di. → [[boru-rc-isci-olcumunu-yalanlar]]

**BEKLIYOR (yaninda "neyi olcmek kapatir"):** 🟠 `gramer-artigi-kapisi.py` **rc=1** — MaCiT'in
`6212540` kaydinda cift-bosluk (**SERIT B, yayini BLOKLAMAZ**; urun metni = MaCiT duzlemi, kutuda
adiyla). *Kapatan:* `gramer-artigi-kapisi.py` rc=0. · 🟠 41 yerel dal main'e girmemis ·
🔧 `cip-kapat.py` dal silme ayagi `branch 'HEAD' not found`.

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
