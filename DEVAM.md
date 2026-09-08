# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## ✅ 8 EYL 02:xx — ana oturum: **4 is kapandi (243 lisans · K19 yayin arizasi · K382 · ArTisT kalemi)**
**KAPANANLAR:** 243 lisans (237 SA + 6 ND; ATIF degisen 0, NC riski 0) `fdccc54d` · K19 `Saab|900` ALLOW / `Yamaha|900` DENY, kapi 1/29 → 29/29 `d0d6b8f9` · K382 ARDISIK 4 → 0 `ede460cc` · ArTisT KVKK `method` beyani koda hizalandi. TAM METIN KUTUDA.
**YAYIN:** run `34178534551` — deploy **success** · yayin **success** · SKIPPED **0** (onceki 4 kosum ayni K19 yuzunden SKIPPED'ti). Kapi mutant bataryasi 38 oldurucu + 8 kontrol, tutmayan 0.
**PARITE=OLCULEMEDI:** kanonik kosum MaCiT'in o an commit'siz 71 kaydini "D1'de yok" diye kirmizi yakti. Neyi olcmek kapatir: d64 CI'si bittikten SONRA tek kanonik kosum.

**K393 ✅ ADIM 2 KAPANDI (cip `peaceful-margulis-057d93`) — Okan ihbari "alt model 40 urunde kesiyor ya da hic gostermiyor":** istemci model yuklemi UCUNKINE esitlendi (`marka[]` ∪ kusak ∪ BASLIK; `modelEsler` girdisi URUN, 4 cagri yeri + nobetci tek govde). Canli TAM GECEN cift **3/14 → 14/14** (Corolla 0/24→24/24; 10 kovada tum sayfalar RED=0, uc 203 = istemci 203). Kapi: filtrenin goremedigi uyelik **10944 → 35**, SAYFA_DAR=0, **30/30**. Kabul `model-baslik-istemci-test.py` 12 iddia/11 mutant → deploy+nobet.

## 🔴 9 EYL KALEMLERI (TAM METIN KUTUDA — 9 Eyl KraL bloklari)
- **K388 META ATIF — SAYIM ALINDI, KOK NEDEN RIZA KAPISI DEGIL:** D1 `siparisler` (tablo adi `siparis` DEGIL), son 30 gun, yalniz VARLIK: toplam **33** · atif dolu 27 · `fbp` **19** · **`fbc` 0** · `ga_client_id` 20 · **`utm` 0**. `json_each(atif)` anahtar kumesi: SADECE `ga_client_id`/`fbp`/`ref`. Civilenen olcut EKSIKMIS (fbp=19 → riza kapisi GECILMIS); ayiran olcum `index.html:1858` — **utm yakalama riza kapisinin ARKASINDA DEGIL**, kapi yalniz `fbclid`'e. Worker borusu DOSELI (`index.js:156` + `olcum.js:255`). HUKUM: 30 gunde kampanya etiketli ziyaret satin almaya DONMEDI; CAPI arizasi YOK, kodda kalem CIKMADI. OLCULEMEDI: auto-tagging kapaliysa rizasiz Meta tiklamasi bu veride gorunmez → ArTisT'e tek soru: 8 kampanyanin URL'inde `utm_source` var mi.
- **K389 ✅ KAPANDI 9 Eyl — ONCUL CURUDU:** iki kol AYRI dosya olcuyor. `defter-kota-kapisi.py` rc'si **KUTU** ekseninden (`KUTU_ASILDI` rc=1); `DEVAM.md` ekseni "Push DURDURULMADI" basar, rc URETEMEZ. Kutu 316→240 → `KUTU_YESIL` → defter commit'i GECTI (`71f86f14`). Ders: rc'nin ekseni okunmadan sinif kapisi yazilmaz.
- **K390 → ÇİP AÇILDI** (`KraL-K390-H1`, `task_c3b8398a`): ana sayfada H1 **0** — canli 0 **ve** kaynak 0, KraL KENDI olctu (ArTisT'in sayisi DOGRULANDI). Alt sayfalar 1, `build.py` H1 atfi 1. Hukum: `index.html:1165` `.brand-sub` div→h1, metin+sinif DEGISMEZ. Kabul 1-5 + mutant (h1→h2 KIRMIZI). ONCUL: build.py index.html'i sarmalamiyor.

## 🔧 8 EYL 02:xx TURUNDAN ACILAN KALEMLER
- **K386 LISANS CAPRAZ — KALAN UC KOVA (KraL):** `G-BIZIM-BILINMEYEN` **117** (bizim deger 'kisisel'/'uyelik' gibi CC disi; otoriterle karsilastirilamaz) · `E-DIGER` **21** · `F-OTORITER-CELISKILI` **8** (ayni tid'e IKI farkli havuz degeri — hangisi otoriter OLCULMEDI). `D-CC0` 428 risk YOK (CC0 atif istemez). Kabul: uc kova da ya sinif hukmu alir ya `KAPSAM DISI` gerekcesiyle donar. Olcum araci COMMIT'LENDI: `python3 tools/lisans-capraz-olcum.py --detay` (salt okuma, rc daima 0).
- **K387 → ÇİP AÇILDI 8 Eyl** (`MaCiT-K387-LisansNormalize`, `cwd=~/dev/pruvo-hasat`; kapsam 21 kopya = 5 ana agac + 16 worktree · fikstur havuzlardan sayilan 39 gercek yazim, bosluklu `'... - Share Alike'` 648 / `'... - No Derivatives'` 24, NonCommercial yazimi 0 · kabul K1-K5 + 3 mutant · bagimsiz kol `tools/lisans-capraz-olcum.py`). Teshis:
- **K387 LISANS BUGUNUN KAYNAGI (MaCiT'te):** duzeltilen VERI'dir; `pruvo-hasat/olcum/hasat_*_mekanik.py` icindeki `lisans_normalize()` hala "sharealike"/"noncommercial" desenlerini BITISIK ariyor (d62 ve d63 kopyalari BIREBIR AYNI olculdu). Yeni dilim ayni hatayi yeniden uretir. Kabul: desen bosluk/tire toleransli + fikstur ("Creative Commons - Attribution - Share Alike" -> CC-BY-SA) + mutant.

## 🔧 BU TURDAN ACILAN KALEMLER (hepsi olculdu, hicbiri baslanmadi)
- **K380 (h) BOLUMU MAIN'DE YOK:** geri inecekse build **SONRASI** cagri yeriyle ya da `urun/` yokken `KAPSAM DISI` (OLCULEMEDI DEGIL) inmeli; yoksa iddia olculmemis kalir. Kabul: `deploy.yml`'de build-sonrasi atif ≥1 ∧ kapi rc=0.
- **K381 `d1-sync.py` GERI-OKUMA SOZLESMESI:** arac "yeni: 74 … dogrulandi ✅" bastiktan HEMEN sonra kendi `--durum`'u ayni satirlari EKSIK gosterdi (MaCiT olctu). Replika gecikmesi mi teyit hatasi mi **AYRISTIRILMADI** → `OLCULEMEDI`. Kabul: tek yazimdan hemen sonra + N dk sonra iki `--durum` (arada baska senkron YOK).
- **K383 `satir_soru` YUZEYI ERISILEMEZ:** link `prova=="kapali"` ister, katalogdaki 16/16 konfigur urun canlida `acik`. K89 "3 yuzey" sayimi SISIK, dogrusu **2 olculdu + 1 erisilemez**. Kabul: canli Worker'in non-200 dondugu konfigur satir (OKAN KAPISI).
- **K384 `kisisel-veri-test.py` bir beyani yanlis basiyor** — TAM METIN + kabul olcutu: `DEVAM-ARSIV.md`, baslik `K384 — 8 Eyl 2026` (govde izlenen belgeye YAZILMAZ, E5).
- **K385 KUTU TAVANI ARTIK BENIM MENZILIM DISI:** 316 st / 250; kalan 15 korumali blogun **13'u BaBa'nin**, 1'i ArTisT'in yorum kalemi, 5'i Okan'in arsivlemesini bekleyen cip kapanisi. BaBa ve Okan kapisi.

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
