# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔁 DEVIR — 7 Eyl 2026, KraL (ana oturum) → yeni hesap
**SIRADAKI TEK IS:** BaBa 18:5x **B maddesi** — durust-sinir sinifindaki **22 gorunur kaydin 13'unu `gizli:true`, 9'unu MUAF** isaretle (olcut `sayfalar.py:4562`: hava tasiyan fan/cark URETIRIZ, sivi tasiyan pompa carki + tekneyi iten pervane URETMEYIZ; alet/tahrik dislisi muaf).
**Nerede kaldim:** 6 cip kapandi, **hepsi bagimsiz komutla dogrulandi**: sitemap oncul CURUK (45 benzersiz lastmod) · llms.txt canli **200** · JSON-LD **476/476** · impeller celisen **5→0** + kapi 26/26 · K377 kardes-depo checkout **success** (token ILK KEZ olculdu) · K378 butunluk **1→26/26**, `OLCULEMEDI` aile **9→0**. Kapi taban kuyrugu **22** bekliyor = B maddesi. CF ①-④ KAPANDI (ayrinti KUTUDA).
**Acik worktree/dal:** worktree **0** (ana checkout tek). Itilmemis dal **0** — uc dal uzaga alindi, MERGE KARARI YENI OTURUMDA: `claude/marka-uyelik-tazeleme` (a9c7a22d, mesajinda "MERGE EDILMEYECEK mukerrer") · `kral/k35-k36-site-kusurlari` (f343b398) · `onarim/kanca-fikstur-kanonik` (61f940b7).
**Baskasinin calisma kopyasinda duran:** YOK (`git status --short` = 0; MaCiT'in partisi commit'lendi).
**Zamanlanmis nobetler (YENIDEN KURULACAK — once `list_scheduled_tasks`, AYNIYSA DOKUNMA):** `gunluk-mimar-ihtar` `0 9,15` 🔴 09 kaldirilamaz (`cip_dogum_bekcisi.ESIK_SAAT`=9) · `teftis-takip` `0 17,23`. Crontab `37 * * * *` CI nobeti **`.ci-token`'a BAGLI → ILK IS tazeleme** (kabul: `~/.claude/cron/ci-nobeti.log` `rc=0`).
**Okan'da bekleyen karar:** ① CF **usage alert $20** (harcama tavani YOK, tek emniyet) ② duzeltilmis billing ticket (asagida) ③ `pruvo-ozel` icin AYRI S3 kimlik dosyasi YOK (tam ad KUTUDA) → `pruvo-ozel`de 1.618 nesne / 6,22 GB **OLCULEMEDI** ④ token Read kapsamlari (Zone Settings + API Tokens) (Tiered Cache ekseni BaBa hukmuyle DUSTU).
🔴 **TICKET METNI DUZELTILDI — eskisi YANLISTI:** `qty` toplam DEGIL **ucretli asim** (13.174.870 − 10M ≈ faturadaki 3.206.886) → "10M dahil celiskisi" YOK; tek gercek anomali **$0,29**. Duzeltilmis metin KUTUDA.

## ✅ 7 EYL — `KraL-ImpellerSinif-7Eyl` [Opus 5]: **durust-sinir SINIF KAPISI; celisen 5→0**
🔴 ONCUL: metin birebir **1** yerde (`sayfalar.py:4562`), "5 yuzey" DEGIL. 🔴 `duzelt.py` CLI `gizli` TIPSIZ (`--deger true`=DIZE) → `--toplu` boolean. TAM METIN KUTUDA+ARSIVDE.
## ✅ 7 EYL — `KraL-JsonLdEskiWave-7Eyl` [Opus 5]: **eski dalga landing'lerinde JSON-LD eksigi KAPANDI (432 sayfa)**
**TABAN→SONUC:** 476 landing, JSON-LD **44 → 476/476** (uretilen 432), sema ihlali 0, ikiz 0. ONCUL YANLIS: sinir 41 degil **44** (`wave-43` de 0/11). IKINCI KUSUR: 8 sayfa ayni URL icin cift Article tasiyordu, kaldirildi. CI kablosu KOSUMLA kanitli: run `34114292147` adim `Landing JSON-LD kapisi` success. TAM METIN KUTUDA+ARSIVDE.
🔴 **MERGE YARISI (olculdu, kayip 0):** merge commit'im `8eb5d047` es zamanli oturumun `amend`'iyle DUSTU; 5 dosyanin blob'lari dal commit'iyle BIREBIR dogrulandi, merge TEKRAR kosuldu → `1e1c38ac`. KUTUDA.
**EV:** `ee6406e3` → `1e1c38ac` (dal `883a338f`, 5 dosya, +432/-9). **YAYIN:** run `34114292147` @ `1e1c38ac` — 6/6 is yesil, `deploy` **success** · `yayin` **success**, SKIPPED **0**
**Okan'a cikan:** YOK. 🔴 **BASKASININ DUZLEMI (dokunulmadi):** `d1-sync --durum` D1=35451 vs `urunler.json`=35526 — **75 eksik**, kaynak komsu cipin `82547f0a` (dilim-60, 75 EKLE) commit'i; ayni kosumun `build` isindeki D1 senkron adimi bunu kapatir, elle `d1-sync` KOSULMADI. `kapi-envanteri` 5/8 (3 kanca KURULU DEGIL) — BaBa'nin 6 Eyl kalemi, benim menzilim disi, CI'da kosmaz.
## ✅ 7 EYL — ana oturum: **3 CIP KAPANDI, EV TEMIZ; KraL'in `serit-b` kirmizisi 0**
**TEMIZLIK:** worktree 4→1 (`arsiv-kapisi` rc=0 + `lsof`) · 3 dal · 2 oturum · kutu 455→399 st (lossless, 18 KORUMALI) · `SERIT B 17→6` arsive (7 st, eksik 0).
**CIP KABULLERI:** `BorcParser` → `GECERSIZ_DURUM 7→0` + `ACIK_KALEM 43→48` · `SeritB2` → `recete AYIKLANAMADI 1→0` + `cip-kapat 24/24` · `KapiEnvanteri` → **BaBa ONCULUNU CURUTTU** (`5/8` DOGRU) — karar BaBa'da. ARSIVDE.
**T4:** `GECERSIZ_DURUM=0 OLCUTSUZ_KALEM=0` (K339-EK+K329-EK'e `kabul:` yazildi); RED sebebi artik yalniz **borc = 48 acik kalem** (esik 0, tasarim).
🔴 **KENDI OLCUMUM CURUTULDU** (cip `bold-poitras`): "push kolundan 0 hukum" YANLIS — **152/373 = %41**, `failure` de HUKUMDUR. MIMAR KARARI: olcut HEAD garantili hukum; `concurrency`yi SHA'li yapmak G9 ile YASAK. ARSIVDE.
**SERIT B** (`34063854360` @ `66a461ad`): `serit-b` 1 = `LCP` **ArTisT** · `hijyen-a3` 1 = `Arama parite` (cip `NodeEkseni`; 4 komut da YERELDE YESIL) · `hijyen-a2` 1 = `Feed politika` **MaCiT**.
**YAYIN ✅:** `34060159828` @ `66a461ad` — 6/6 yesil, deploy+yayin success, SKIPPED **0** (BaBa'nin 2 ardisik SKIPPED kirmizisi KAPANDI).
**K377+K378 ✅ (`c34f9712`):** `hacim-tam-takim` on-kosul R2'ye; butunluk **1 dosya → 26/26 sha256** (ORTAK arac). `PRUVO_PAKET_DIR` → **OLCULEMEDI 9→0** (run `34125512781`). Kabul 10 kol+3 mutant. 🔴 ARIZA YER DEGISTIRDI: 9 aile CI openscad `derleme hatasi`. KUTUDA.
**KimiIptal-7Eyl:** isci.sh/uc/crontab 0, MOTOR-YOK 3/3, vaka 619. KUTUDA.
**KAPANIS 08:2xZ:** 4 cip kabul · tamirci dali MERGE `019e8efe`→`535005fd` · `hijyen-a3`=`PVC` landing · YAYIN `34098909326` SKIPPED **0**. KUTUDA.
**10:3xZ:** 3 CIP EMRI ICRA · `(Impeller)` ikizi `ee6406e3` · K376 · kutu 461→191 (lossless). **✅ `LlmsTxt`:** `llms.txt` **404→200** (`771c001c`, run `34113014132` SKIPPED 0) — MANIFESTO+nobetci 1→2, mutant 7/7. KUTUDA.
## 🔴 6 EYL — `KraL-KapiEnvanteri-6Eyl` [Opus 5]: **hukmun ONCULU CURUDU — uc kapi KURULU DEGIL; `5/8` DOGRU** (tam hesap KUTUDA)
**ONCUL+AKIM:** 3 atfin ucu de PROZA (biri `SILINDI`); 29 Agu supurmesi kabloyu sokmus. Canli: 3 kapi da deny URETMEDI (`git commit` rc=0), POZITIF KONTROL deny verdi; mutant 4/4. **Kapilar KURULMADI → BaBa karari.** TAM METIN KUTUDA.

## 🔁 5-6 EYL ISARETCILERI — **TAM METIN ARSIVDE** (md5 birebir, eksik 0). ACIK iplikler: MODEL adindan marka turetimi · hafiza ekseni SILAHSIZ · baglam kotasi 2 vaka · `d1-sync --durum` 71,2 sn · MaCiT CLAUDE.md 13.060 B · `defter-rotasyon.py` 13/13 vetolu · MaCiT `Kahve` 79 kayit · LCP ArTisT'te (Okan'a: PSI anahtari).
## 🔴 CANLI TALIMAT (K353 blogu ARSIVE indi, tam metin `DEVAM-ARSIV.md`'de)
K353 merge'unden SONRA `kanca-kur.py` kosulur (once kosulursa filo felci).

## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)
- 🔴 **26 AGU KALEMLERI — TAM METIN KAYNAK-DOGRUSUNDA (`acik-kalemler.md`) + KUTUDA; burada yalniz
  ISARETCI** (uzun hali `DEVAM-ARSIV.md` 26 Agu ROTASYON blogu 1/5): K306 MERGE `df3b0d48` · K308 ACIK ·
  K309 DILIM-1 MERGE `25b38a82` (DILIM-2 MIMARDA) · K310 ACIK · K212 MERGE `97370cc2` KAPANDI · K222
  KAPANDI · K311 MERGE `bcbdb1dd` ACIK (①-④ GECMEDI; ④ GERI ALINDI) · **K312 ACILDI**.
- 🔴 **MOTOR (6 Eyl; 20 Agu GECERSIZ):** `minimax-m3` TEK + `claude`; `kimi` EMEKLI. Yedek YOK — m3 duserse `HAL=MOTOR-YOK rc=1`. Kaynak `mimar_kimlik.py`.
- 🔧 **K200 (TAM METIN ARSIVDE):** (i) kuru kosum OLCULDU 25 Agu (1512/234, sir elemesi 5/5; BULGU:
  gurultu budamasi memory agacinda KOSMUYOR → 13 gecici dosya Drive'a) · (ii) kablolama MIMARDA · (iii) kostugu kanit.
- 🔧 **K199 (19 Agu):** `is-akisi-kapisi.py` "etkili tasiyici" LITERALE capali; varlik turetilmis
  mekanizmaya gecince korlesir (K193). Care: sonucu olc ya da makine-okunur beyani tasiyici say;
  mutant+negatif sart. · 🔧 **K201 SINIF: KAYIT KENDINI OLCMEZ** — 5 vaka; ya TURETILIR ya SAYIYLA.
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
- 🔧 **K220 (KraL) → ISARETCI, TAM METIN `DEVAM-ARSIV.md`'de:** `marka_yazimlari()`+`taninmis_mi()` TEK listeden besleniyor, liste IKI rol tasiyor;
  Range Rover'i markaya yazmak CANLI `/marka/land-rover/range-rover/` sayfasini OLDURUYOR — **menzil on-olcumu yapilmadan dokunma**
  ([[k220-menzil-on-olcumu-uc-turdur-eksik]]). 31 Agu negatif olcumu (`Raymarine`, kume-farki yordami, sayi-only kolun korlugu mutantla kanitli) ARSIVDE. SIRA: D bitti, sirada A.
## KraL ACIK ARTIKLAR (19 Agu anlati blogu ARSIVE TASINDI; kota uyarisi da orada)
🔧 **K203:** tavan kapisi worktree ICINDEN rol eksenini kaybediyor (sebep onek DEGIL cagri baglami);
K223'un FIKSTUR kovasi fikstur eksenini kapatti, ROL ekseni ACIK. · 🔧 **K204:** `OKSUZ` fiilen
"kirli mi" olcuyor, TEK BASINA kaldirma gerekcesi DEGIL. · 🔧 **K188** → kaynak-dogrusunda (5/5, `KraL-K309D2`: rc=0 ama eksen bataryada YOK).
- 🔧 **K218 · K219 · K221:** tam metinler ARSIVDE. (K195 merge edildi `528da42d`.)
- 🔧 **K198** → ARSIVDE · izlenen yapilandirmada ticari alan var, nobetci o duzlemi
- 🔧 **K182 (18 Agu — SINIF, bugun UC KEZ cikti):** mutant "kirmizi geldi" diye kanit
  sayiliyor ama kirmizinin SEBEBI hedef kol mu olculmuyor (recete M1 · K178 tek eksen ·
  ③g M5). kabul: her mutant, hedef kolu oldurdugunu AYRICA kanitlar.
- 🔧 **K176** → ARSIVDE · D1 kilit mesaji YANLIS PID basiyor (`d1-sync.py:157`); yayini bloklamaz · kabul: tutani basar ya da OLCULEMEDI + mutant.
- 🔧 **K171** → ARSIVDE · gizli kaynak
- 🔧 **K140** → ACIK_KALEMLER · ikinci kopya ARSIVE indi 4/5, `KraL-K309D2`: kapi EVREN KAYNAGI hatasi (cip evreni kuratorlu) · kabul: `marka-invaryant-kapisi.py` 7 jeton DUSMUS + `Rover` DURUYOR + mutasyon 4/4.
- 🔧 **17 Agu KALEMLERI:** K163 · K162 · K157 (⚖️ Okan, 22 Agu) · K158 · K146 · K142 (MaCiT) · K118. TAM METIN ARSIVDE.
- 🔴 **K104 / K104B:** nobet sicili + iki kapi main'de kirmizi. HUKUM MIMARDA. · **K99**
  bag kolonu · **K100** satir-sonu muafiyeti · **K102** yasakli ic dosya adi.
- 🔧 **K179 · K135 · K152** · 🟠 **K139 · K144** → ISARETCIYE INDIRILDI (7 Eyl, elle: `defter-rotasyon.py` 10/10 blogu K195 §1.2 ile VETOLADI, ilerleme uretemedi). TAM METIN `DEVAM-ARSIV.md`'de — arsiv isabeti K135=4 K139=2 K144=8 K152=11 K179=7, kalem kimlikleri KORUNDU.
- 🔧 **Iki acik kapi kalemi:** (a) shop bayatlik TETIK ekseni ≠ bundle evreni; (b) `devam-sinif-kapisi.py`
  is-akisi muafiyeti `norm`/`ham` ayrisiyor. · 🟠 **K122:** `kurtarma/k122-yabanci-is` dali DURUYOR. ARSIVDE.
- 🔧 **K151** (17-19 Agu): TAM METNI ARSIVDE (20 Agu 1:1 tasima blogu). · 🔧 **K161** → ISARETCI: KAYNAK-DOGRUSUNDA (26 Agu, `KraL-K309D2`).

## OKAN'DA
- ✅ 25 Agu penceresi: 9 kalem kapandi → [[okan-25agu-kapatilan-konular]]; 🔴 yeniden ACILMAZ.
- 🔧 **K297·K298·K299·K300·K301:** SERIT B hijyen kirmizisi · iki ayri K29 · K86 metni bayat ·
  K55 sayisi **197** · `T4-OLCUTSUZ` tum evlerde. Tam metinler KUTUDA.
- 🔧 **K329 (28 Agu, CI nobeti):** iki kapi dosyasi kanonik `git_ortami.sentetik_git`'e gecirildi, yerelde YESIL olculdu; main'e INEMEDI — kutu 306>300, 6 blok `ARŞİVLENEBİLİRİM` bekliyor (**Okan arsivi**), is `ci-nobet-git-ortami` dalinda stage'li.

## ARSIVDE — 14-20 Agu `DEVAM-ARSIV.md`'de.
