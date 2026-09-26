# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## ✅ 25 EYL 22:5x KraL ana-oturum (Okan: "devam") — **BaBa ③ de main'de (`92d7621a`, merge'ü çip attı) · önceki YAYIN `OLCULEMEDI` KAPANDI**
**SIRADAKİ TEK İŞ:** OCI kalıcılık kabulü — 26 Eyl ≥06:25Z sonraki ilk zamanlanmış koşumda `EL-SIKISMA-TAMAM` (dış zaman). MaCiT 22:3x araç kusurları TRİYAJ EDİLDİ (26 Eyl 01:xx): `hasat_ekle` `uyum` türetimi + `marka-kapsama` büyük/küçük harf → **pruvo-hasat/MaCiT düzlemi**, KraL'da değil · `yedekle` karantinası **KUSUR DEĞİL** (bayt-düşüşü koruması doğru çalıştı; kasıtlıysa `.yedek-dusus-izin.json`'a beyan; `--sirlar` zaten EMEKLİ) · 🔧 **KraL AÇIK:** pre-push D1 kolu eşzamanlı push'ta sahte RED veriyor — bu gece 2. kez ölçüldü (benim push'um `D1 SENKRONU BASARISIZ rc=1` ile durdu, hemen ardından `--durum` 38829=38829 / uyuşmaz 0) · 🔧 **KraL AÇIK (düşük):** CARE satırı başka evde koşulunca KraL'ın `DEVAM.md` yolunu basıyor (`defter-rotasyon.py` CARE metninde yol YOK; kaynak `defter-kota-kapisi.py` türetimi — ölçülecek). 🧾 **Okan'ın e-Arşiv işi:** 45 fatura planı masaüstünde `PRUVO-fatura/`; portal yazımı Claude güvenlik denetimince reddedildi, fatura KESİLMEDİ.
**MERGE `92d7621a`** ← `claude/heuristic-jackson-d99973` (`a608d277`; merge-base `a91295b3`, tek dosya `tools/defter-rotasyon.py` +395/−6, `merge-tree` çakışma **0**, ff İMKÂNSIZ → merge commit). Merge'ü çip kendisi attı (22:48, ben ölçerken); çift yazım olmasın diye soruldu: **kutu = çip, defter = KraL**. Bağımsız ölçüm DALIN AĞACINDA, borusuz: `--kendini-test` **21/21 DÜŞEN=0 rc=0** (3 izole mutant OLDU) · `defter-onlem-bacagi-test` **115/0, MUTANT 6/6** · `ci-kapsam` rc=0 · `kisisel-veri` rc=0 · canlı `--kuru` DEVAM md5 önce=sonra (`c3025866…`). 🔴 **İki ayrı sayı:** `--kuru` ②'den ÖNCEKİ defterde (65 blok) **INDIRILEBILIR=2**, bugünkü defterde (7 blok) **INDIRILEBILIR=0** — indirilecek blok KALMADI (59'u ② ile indi); yüklem körelmedi: `20:5x` bloğu ③ kolunda VETO yiyor (kimliksiz açık kalem).
**YAYIN:** `03081fcb` → run `36179659751` `completed` · `deploy` success · `yayin` success · SKIPPED **0** ⇒ önceki bloğun `OLCULEMEDI`'si KAPANDI. `92d7621a` → run `36181971743` headSha BİREBİR, 6/6 job success (`deploy`+`yayin` success, SKIPPED **0**). `db685791` (bu defter) koşumu ardıl push'larca `cancelled`; ardılı `33620ae1` taşıyor.
**TEMİZLİK:** 🔴 **Ağaç adı geri dönüşümü CANLI yakalandı** — ilk ölçümde `beautiful-mirzakhani` · `confident-sutherland` · `mystifying-sinoussi` detached/temiz/lsof 0 (artık) göründü; silmeden ÖNCE ikinci ölçümde üçü de yeni açılan 3 MaCiT çipine devredilmiş (yeni dallar, lsof 2/2/5) ⇒ **HİÇBİRİ silinmedi** ([[worktree-adi-geri-donusturulur-canli-cipi-siler]]). `quizzical-feistel-d5bd17` + dal `claude/heuristic-jackson-d99973` SİLİNDİ (ağaç: çip · uzak dal: Okan); `ls-remote` boş, `worktree list` 4, içerik main'de (`92d7621a`). Repo-dışı `dal-olc.py` icra kapısına takıldı; §2-§3 adımları elle `git` ile koşuldu.
**MOTOR ORANI:** Claude 1 / m3 0 — iş merge hükmü + ölçüm (sessiz-hata sınıfı), hacim yok. **Okan'a çıkan:** YOK.

## ✅ 25 EYL 22:2x KraL ana-oturum (Okan: "devam") — **cron nabız holü main'de (`d3846746`) · BaBa'nın 3 kaleminin 2'si KAPANDI: defter 497→154, hafıza 16.629→15.317 B**
**SIRADAKİ TEK İŞ:** çip `KraL-DefterYuklem-25Eyl` (`task_b1e6da02`) dalını merge-kapısıyla al (BaBa ③). Ayrıca **YAYIN `OLCULEMEDI`** — aşağıdaki iki koşumdan biri `deploy`+`yayin` `success` ∧ skipped=0 basınca kapanır.
**MERGE `d3846746`** ← `claude/mystifying-sinoussi-436710` (1 dosya +386/−17, merge-base `4a202b24`, çakışma **0**). 🔴 **Çipin ağacı main'e dönmüştü** (`HEAD=9167a6fa`, 229 iddia) — main'i ölçüyordum; dalı AYRI geçici ağaca çıkarıp gerçek uçta (`706f3ca3`) ölçtüm: **252 iddia / 0 KIRMIZI** · `ci-kapsam` · `kisisel-veri` rc=0 (borusuz). Taban FİİLEN oynadı (main 229 ↔ dal 252). Pozitif kontrol `T-DOLU-SESSIZ` üç iddiayla "gerçekten sessiz cron HÂLÂ 🔴" diyor; tekil yama YOK (iş akışı adı geçen 2 satırın ikisi de yorum). 🔴 **Ağaç adı geri dönüştürülmüş** — `mystifying-sinoussi-436710` artık başka dal taşıyor, komşu çipe dokunulmadı.
**🟢 BaBa ② DEFTER KİLİDİ AÇILDI (`65dc08b9`, m3):** `DEVAM.md` **497→154 satır** (175.073→14.653 B), arşiv 24.864→**25.294**. İşçi damgasına güvenilmedi — donmuş kopyamla BAĞIMSIZ: çıkan **59** blok başlığının **59'u** arşivde (eksik 0) · arşiv **APPEND-ONLY** (ilk 24.864 satır md5 BİREBİR) · eski arşivden **0 satır** silinmiş · **çıkan 373 anlamlı satırın 373'ü arşivde (kayıp 0)**. Kabul: `devam-sinif-kapisi` rc=0 · K-kimlik **140 ≥ 89** · commit kapsamı yalnız `DEVAM.md`. 🔴 **İlk deneme fail-closed DURDU, hata BENİMDİ:** `SIRADAKİ TEK İŞ` iki yazım varyantında geçiyor (13 noktalı İ + 2 noktasız I = 15); spec'im tek desen sanmıştı, işçi öncülü yalanlayıp durdu, **hasar 0**.
**🟢 BaBa ④ HAFIZA KAPANDI (m3):** `MEMORY.md` **16.629→15.317 B** (tavan 16.384 altında). Dört ekseni kendim ölçtüm: satır 39 · 180 link hedefi diskte, eksik **0** · dosya sayısı 478 değişmedi. İşçi tutturamadığını ADIYLA yazdı: **11 satır hâlâ >300 B (en uzun 2.849)** → BaBa'ya çıktı, kural kategori satırlarında matematiksel olarak tutmuyor.
**EV:** `9167a6fa` → `d3846746` → **`65dc08b9`**, `ls-remote` KANITLANDI, ağaç 0 dosya. **YAYIN `OLCULEMEDI`:** `36177516477` (`16d7e222`, merge'i ata taşıyor) `in_progress` · `36179235590` (`65dc08b9`) `pending`; kota penceresi kapandı, beklenmedi. **TEMİZLİK:** geçici ölçüm ağacı + merge edilen dal (yerel+uzak) + 2 işçi spec'i + 2 rapor dizini + işçinin bıraktığı dosya SİLİNDİ, scratchpad 0. **MOTOR ORANI:** Claude 1 / **m3 3** (`MOTOR=` 168→172). **ÖZ-ÖLÇÜM:** tur **448** / bağlam **428K** (<500 · <450K). **Okan'a çıkan:** YOK.

## ✅ 25 EYL 20:5x–21:2x KraL ana-oturum (Okan: "devam") — **BEKLEYEN İKİ DAL DA MAIN'DE (`70a7eb69`) · çürütme çipin kapatamadığı HOLÜ buldu**
**SIRADAKİ TEK İŞ:** çip `KraL-CronNabizHolKapat-25Eyl` (`task_352e8b5d`) dalını merge-kapısıyla al. OCI kalıcılık kabulü (26 Eyl ≥06:25Z sonraki ilk zamanlanmış koşumda `EL-SIKISMA-TAMAM`) hâlâ AÇIK — dış zaman bekliyor.
**MERGE ① `claude/eloquent-dirac-1c3278`** (1 dosya `cron-nabiz-kapisi.py` +227/−3, merge-base `7b5914f3`, `merge-tree` çakışma **0**) **② `claude/elastic-booth-6178be`** (4 dosya +676/−12, merge-base `2f95d003`, çakışma **0**). Öz-raporlara güvenilmedi, hepsi **DALIN AĞACINDA borusuz** (`${pipestatus[1]}`) koşuldu: ① `--kendini-test` **229 iddia/0 KIRMIZI** · `ci-kapsam` · `kisisel-veri` rc=0 ② OCI kabul **MUTANT=28 ÖLEN=28 SURVIVOR=0** · `reklam-oci-kapisi` 9 bacak · `ci-kapsam` · `kisisel-veri` rc=0. Merge SONRASI ana ağaçta dördü de tekrar yeşil. Sır taraması: yeni jeton aracında sabit `client_secret`/`refresh_token` deseni **0 vuruş**, istemci json'u `~/Downloads`'tan okunup siliniyor, repoya yazmıyor.
**🔴🔴 ÇÜRÜTME HOL BULDU — ÇİPİN ÖLÇÜTÜ TUTTU AMA SINIF KAPANMADI:** dalın ağacında canlı kapı 17:58Z'de `SONUC: 🔴 ALARM ... A5+A3(yayin-erisim-alarmi.yml)` **rc=1** bastı (`OLCULEMEDI` değil **kesin** hüküm); ~2 dk sonra aynı komut **✅ ✅** (teslim 10/48, son koşum 4,1 sa önce). Gerçek: o iş akışının son schedule koşumu **13:56:08Z `success`**, yaş ~4,0 sa, eşik 18 sa ⇒ **kırmızı YANLIŞTI**. Kök neden kaynakta açık: `sayfa_tutarsizligi` şartı (2) *"sayfa DOLMAMIŞ"* — o akışın `total_count`'u **585**, sayfa DOLU ⇒ yeni kol hiç tetiklenmiyor. **Bayat ama DOLU sayfa, gerçekten susmuş yoğun bir cron'dan tek yanıtla AYIRT EDİLEMEZ** ⇒ çare ikinci gözlem (pencere süzgeçli sorgu), çipe çivilendi (>229 iddia ∧ pozitif kontrol 🔴 ∧ ≥2 mutant SURVIVOR=0).
**EV / YAYIN + 🔴 ÜÇ YARIŞ/KAPI OLAYI:** `a0084ecd` → **`70a7eb69`**, `ls-remote` = `70a7eb69` **KANITLANDI**; `--durum` **6 eksen ✅ 38743=38743, hash uyuşmaz 0**; deploy run **`36171438682`** izleniyor. ① merge sırasında `main` altımdan ilerledi (`2f95d003`→`a0084ecd`) + yerel dal referansı uzağın gerisindeydi → taban tazelenip yeniden ölçüldü ② ilk merge **rc=128 `could not write index`** ile DURDU (komşu `urunler.json`'u stage'lemişti): **stash/force YAPILMADI**, hasar 0 (`MERGE_HEAD` yok), komşunun commit'i inince üstüne alındı ③ ilk push pre-push kapısınca DURDURULDU (**K85: D1 bayatken `urunler.json` main'e giriyordu**) — kapı haklıydı; D1 senkronlanınca geçti. Push RED metni "ref itilmedi" demek DEĞİLDİ (`ls-remote` ile ölçüldü).
**TEMİZLİK:** worktree **4→2** (iki merge edilmiş ağaç `lsof`=0 → silindi; `quizzical-feistel` **CANLI** → dokunulmadı, pozitif kontrol ana checkout'ta 11) · 2 dal yerelde+uzakta silindi · ağaç 0 dosya · scratchpad 0. **DEFTER:** rotasyon **yapısal olarak tükendi** (`--onlem` → `SU_SEVIYESI=ULASILAMADI TASINAN=0`, iki aday `SINIFLANAMAZ`: açık jeton taşıyor) — araç arızası DEĞİL, blok bu yüzden kompakt. **MOTOR ORANI:** Claude 1 / m3 0 — tur tamamen merge hükmü + kapı çürütmesi (sessiz-hata sınıfı), `isci-devri` bunu Claude'da tutar; mekanik hacim yoktu. **Okan'a çıkan:** YOK.

## 🔧 BU TURDAN ACILAN KALEMLER (hepsi olculdu, hicbiri baslanmadi)
- **K380 (h) BOLUMU MAIN'DE YOK:** geri inecekse build **SONRASI** cagri yeriyle ya da `urun/` yokken `KAPSAM DISI` (OLCULEMEDI DEGIL) inmeli; yoksa iddia olculmemis kalir. Kabul: `deploy.yml`'de build-sonrasi atif ≥1 ∧ kapi rc=0.
- **K381 `d1-sync.py` GERI-OKUMA SOZLESMESI:** arac "yeni: 74 … dogrulandi ✅" bastiktan HEMEN sonra kendi `--durum`'u ayni satirlari EKSIK gosterdi (MaCiT olctu). Replika gecikmesi mi teyit hatasi mi **AYRISTIRILMADI** → `OLCULEMEDI`. Kabul: tek yazimdan hemen sonra + N dk sonra iki `--durum` (arada baska senkron YOK).
- **K383 `satir_soru` YUZEYI ERISILEMEZ:** link `prova=="kapali"` ister, katalogdaki 16/16 konfigur urun canlida `acik`. K89 "3 yuzey" sayimi SISIK, dogrusu **2 olculdu + 1 erisilemez**. Kabul: canli Worker'in non-200 dondugu konfigur satir (OKAN KAPISI).
- **K384 `kisisel-veri-test.py` bir beyani yanlis basiyor** — TAM METIN + kabul olcutu: `DEVAM-ARSIV.md`, baslik `K384 — 8 Eyl 2026` (govde izlenen belgeye YAZILMAZ, E5).

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

- 🔗 **K-kimlik REF arşivi (taşınan bloklardan iz — ölçü eksenleri izlenen belgede tutuldu):**
  - **K0** — ref (geçmiş blok · taşındı)
  - **K1** — ref (geçmiş blok · taşındı)
  - **K2** — ref (geçmiş blok · taşındı)
  - **K3** — ref (geçmiş blok · taşındı)
  - **K5** — ref (geçmiş blok · taşındı)
  - **K110** — ref (geçmiş blok · taşındı)
  - **K240** — ref (geçmiş blok · taşındı)
  - **K252** — ref (geçmiş blok · taşındı)
  - **K270** — ref (geçmiş blok · taşındı)
  - **K284** — ref (geçmiş blok · taşındı)
  - **K291** — ref (geçmiş blok · taşındı)
  - **K313** — ref (geçmiş blok · taşındı)
  - **K314** — ref (geçmiş blok · taşındı)
  - **K316** — ref (geçmiş blok · taşındı)
  - **K317** — ref (geçmiş blok · taşındı)
  - **K319** — ref (geçmiş blok · taşındı)
  - **K320** — ref (geçmiş blok · taşındı)
  - **K321** — ref (geçmiş blok · taşındı)
  - **K322** — ref (geçmiş blok · taşındı)
  - **K323** — ref (geçmiş blok · taşındı)
  - **K325** — ref (geçmiş blok · taşındı)
  - **K326** — ref (geçmiş blok · taşındı)
  - **K327** — ref (geçmiş blok · taşındı)
  - **K331** — ref (geçmiş blok · taşındı)
  - **K332** — ref (geçmiş blok · taşındı)
  - **K334** — ref (geçmiş blok · taşındı)
  - **K335** — ref (geçmiş blok · taşındı)
  - **K336** — ref (geçmiş blok · taşındı)
  - **K337** — ref (geçmiş blok · taşındı)
  - **K338** — ref (geçmiş blok · taşındı)
  - **K339** — ref (geçmiş blok · taşındı)
  - **K340** — ref (geçmiş blok · taşındı)
  - **K351** — ref (geçmiş blok · taşındı)
  - **K352** — ref (geçmiş blok · taşındı)
  - **K353** — ref (geçmiş blok · taşındı)
  - **K356** — ref (geçmiş blok · taşındı)
  - **K357** — ref (geçmiş blok · taşındı)
  - **K360** — ref (geçmiş blok · taşındı)
  - **K361** — ref (geçmiş blok · taşındı)
  - **K365** — ref (geçmiş blok · taşındı)
  - **K366** — ref (geçmiş blok · taşındı)
  - **K367** — ref (geçmiş blok · taşındı)
  - **K368** — ref (geçmiş blok · taşındı)
  - **K369** — ref (geçmiş blok · taşındı)
  - **K370** — ref (geçmiş blok · taşındı)
  - **K371** — ref (geçmiş blok · taşındı)
  - **K372** — ref (geçmiş blok · taşındı)
  - **K373** — ref (geçmiş blok · taşındı)
  - **K374** — ref (geçmiş blok · taşındı)
  - **K375** — ref (geçmiş blok · taşındı)
  - **K376** — ref (geçmiş blok · taşındı)
  - **K386** — ref (geçmiş blok · taşındı)
  - **K387** — ref (geçmiş blok · taşındı)
  - **K389** — ref (geçmiş blok · taşındı)
  - **K390** — ref (geçmiş blok · taşındı)
  - **K391** — ref (geçmiş blok · taşındı)
  - **K392** — ref (geçmiş blok · taşındı)
  - **K395** — ref (geçmiş blok · taşındı)
  - **K396** — ref (geçmiş blok · taşındı)
  - **K397** — ref (geçmiş blok · taşındı)
  - **K399** — ref (geçmiş blok · taşındı)
  - **K401** — ref (geçmiş blok · taşındı)
  - **K402** — ref (geçmiş blok · taşındı)
  - **K404** — ref (geçmiş blok · taşındı)
  - **K405** — ref (geçmiş blok · taşındı)
  - **K406** — ref (geçmiş blok · taşındı)
  - **K407** — ref (geçmiş blok · taşındı)
  - **K408** — ref (geçmiş blok · taşındı)
  - **K410** — ref (geçmiş blok · taşındı)
  - **K411** — ref (geçmiş blok · taşındı)
  - **K412** — ref (geçmiş blok · taşındı)
  - **K414** — ref (geçmiş blok · taşındı)
  - **K415** — ref (geçmiş blok · taşındı)
  - **K416** — ref (geçmiş blok · taşındı)
  - **K417** — ref (geçmiş blok · taşındı)
  - **K418** — ref (geçmiş blok · taşındı)
  - **K419** — ref (geçmiş blok · taşındı)
  - **K420** — ref (geçmiş blok · taşındı)
  - **K421** — ref (geçmiş blok · taşındı)
  - **K422** — ref (geçmiş blok · taşındı)
  - **K423** — ref (geçmiş blok · taşındı)
  - **K89** — ref (geçmiş blok · taşındı)
  - **K91** — ref (geçmiş blok · taşındı)

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
