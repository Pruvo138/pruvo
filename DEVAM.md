# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.


## 🔁 11 EYL ana oturum-9 KAPANIS — OKAN EMRI: TIKAYICILAR KALKTI + m3 FAN-OUT
**TAM METIN KUTUDA** — 11 Eyl 10:4x `KraL (ana-oturum-9) KAPANIS`. Deftere yalniz yurumesi gerekenler:
**🔴 OKAN KAPISI — 3 URUNDE SATIS RISKI (K386):** otoriter `satin-alma` ↔ dosyada `CC BY 4.0`: `mercedes-o309-el-freni-kolu` · `volvo-240-izgara-kilitleme-pimi` · `renault-megane-1-kap-kolu-mekanizma-klipsi`. Onerim gizli (kalici taslak), urun SILINMEZ. ⚠️ Raporun sinif aritmetigi CELISIK — 3 id somut, sayilara yaslanma. Ayrica **117 urunde** public `lisans.tur='kisisel'`, gizli kayit `ucretsiz-cc`.
✅ **MERGE KAPANDI** (ana oturum-10, 11 Eyl 18:1x) → `81190ffa` push'landi. Kabul GECTI: A=7 KOL + B=52 VAKA = **59, DUSEN=YOK**.
✅ **16 artik `claude/*` SILINDI** (hepsi main'in atasi, origin'de yedekli; `determined-cray`+`gifted-lichterman` `-D` ile — yerel uc ust-akimdan farkliydi ama IKISI DE main'de). `curut/ozet-v3` + `claude/fervent-heisenberg-2d069c` BIRAKILDI.

## 🔁 11 EYL ana oturum-10 — MERGE + TEMIZLIK; **iki YENI kalem OLCULDU**
✅ **K402 + K403 KAPANDI** (cip `keen-lewin-a2a3fb`, dal `claude/quizzical-bun-961d50`; MERGE HUKMU MIMARDA). TAM METIN + olcum matrisi `DEVAM-ARSIV.md`, baslik "K402+K403 KAPANIS — 11 Eyl 2026" (govde izlenen belgeye YAZILMAZ, E5). Ozet sayilar: batarya **52 → 68 vaka**; `tikayici-kaldirma-test.py` temiz ve isci ortaminda **AYNI** sonucu veriyor (68/68); `icra-kapisi-test.py` **43/43** (iki ortamda da); `repo_ici` prob **3 → 0**, repo DISI **5/5 aynen RED**. Olcum artefaktlari: `~/.claude/cron/isci-tur-cikti/{kirmizi-13,onek-esitlik,kabul-matrisi}/`. Cip `task_7aa8c628`.
🔧 **K402'DEN DOGAN ACIK KALEM:** `mimar-kilit-test.py` **231/323 (92 kirmizi)** — HEAD surumuyle izole kopyada olculdu, dusen vaka kumesi BIREBIR AYNI ⇒ **taban, bu tur ne acti ne kapatti**. Ayri kalem, sahibi mimar.
🔧 **MENZIL (m3 olctu, mimar dogruladi):** `tools/` icinde ayni onek/esitlik deseninden **82** nokta (A=82 · B=20 · C=810, toplam 912 — aritmetik tam). KARAR etkisi olan ve kok vakasi ERISILEBILIR olan TEK canli ornek onarildi; kalan liste `isci-tur-cikti/onek-esitlik/`.
🔧 **YAN ONARIM — filo capinda:** `memory/acik-kalemler.md`'de **3 satirin sutunu kaymisti** (146/146 → 8 sutun), bu yuzden `parti-borc-kapisi.py` durum hucresini okuyamiyor ve **tum evlerde `isci.sh` duruyordu**. Metin BIREBIR korundu, durum degerleri DOSYADAN okundu. N2B artik `ACIK=55` OLCUYOR.
🔧 **K404 (ArTisT 3. kez bildirdi, Okan 29 Tem emri 43 gundur isle**n**memis):** canlida **45 sayfa** beyaz esya tasiyor. Olcut ArTisT'in guard'i `pruvo-pazarlama/seo/dalga-guard.py:557-567` (TEK KAYNAK). Taban: `tools/sayfalar.py` **28** isabet · `index.html` 1 (kod yorumu) · `urunler.json` 1 (MaCiT'e). Cip `task_8aff727e` — 301 ZORUNLU, duz 404 YASAK.
✅ **K220 MENZIL ON-OLCUMU 3 TURDUR EKSIKTI, ARTIK OLCULDU** (`~/.claude/cron/isci-tur-cikti/k220-menzil/`): oncul GECERLI (tek liste `index.html:3031-3056`, 133 uye) · ayna N=0 temiz, M=14 KASITLI · **76 sayfali + 41 sayfasiz + 16 OLU jeton** · en agir aday `Land Cruiser` 63 urun. 🔴 `build.py` kosmadan gercek `/marka/` sayisi **OLCULEMEDI**.
🔧 **MUTANT BATARYASI AYIRT EDICI DEGIL** (`isci-tur-cikti/mutant-15/`): 15 kalemin 9'u GERCEK-BOSLUK, 1 BAYAT-CAPA, 3 OLCULEMEDI; **KONTROL mutantlari da kirmizi yaniyor** (12 vaka her degisiklige kirmizi) ⇒ once ayirt edicilik, sonra 15 kalem.
🔧 **KORUMALI BLOK** (`isci-tur-cikti/korumali-blok/`): spec 17 diyordu, gercek **3**; bugun arsive inebilecek **YOK**. KraL'in acik bacagi: `tools/odeme-beyani-kapisi.py:302` `rakip_desen` `4-8`/`10-14` gecirilmis — **3. tur, tekil yama YASAK, sinif kapisi**.
✅ **BU BACAK KAPANDI** (cip `quizzical-chatelet-4856b8`, dal `claude/quizzical-chatelet-4856b8` uc `744af70c`, merge mimarda). 🔴 **ONCUL CURUDU:** sinif kapisi ZATEN main'deydi (`bfb18b0f`); `:302` literali satir **49'da YORUM**. Tekil yama YAZILMADI. Gercek acik eksen bataryaydi: mutant atfi SABIT METIN'di, yargi yalniz `rc!=0`. Artik `DUSEN:` **kume esitligi** olculuyor + cikis kodu ekseni AYRI (S5 mutanti: 3 vaka duser, rc=0 kalir ⇒ TUTARSIZ yakalanir) + META 2 kol (atif karsilastiricisi kasitli yanlis beklentiyle oldurulur; `DUSEN:` yoksa olcum GECERSIZ). Batarya **5/5 (atif olculmuyor) → 8/8 (olculuyor)**; kapi 11/11 rc=0 DEGISMEDI; `ci-kapsam-test.py` rc=0. Envanter: `N-M is gunu` TOPLAM=103 KANONIK=94 **RAKIP=9, 9'unun TAMAMI tools/ fiksturu — sitede 0**.

## ✅ 11 EYL oturum-9 ILK YARI — ISARETCI (tam metin kutuda): A→B→C merge `f641d116`, yayin `34535784062` SKIPPED=0, D1 ✅ 36771, `build.py` FAQPage'i EZMIYOR, kutu kilidi acildi, hesap (1b) KAPANDI.
🔴 **KISIT:** kapi KABLOLU, merge dogrulamasi cipe gider · `2>&1` eki de RED (serbest komut CIPLAK kosulur) · defter rotasyonu yer ACAMAZ (`KAPALI=0`, 35 madde ACIK = arac DOGRU no-op) · `kutu-arsivle --sha-dogrula` TASIMA ONCESI kosulursa fail-closed her blogu eksik sayar, yazmaz.

## 🔁 11 EYL çip `elegant-wright-dc11d6` — OKAN EMRİ dilim 2: MİMAR KAPILARI tıkayıcıları KALKTI, defter tavanları 500
**Okan:** *"tüm tıkayıcıları kaldır"* + *"6'yı 500 yap"*. Kaldırılan **REDDETME YETKİSİ**dir, ölçüm DEĞİL: teşhis stderr'de KALDI, çıkış 0. Kabul: `tools/tikayici-kaldirma-test.py` **44 vaka / 7 mutant YEŞİL** (`nobet.yml::serit-b` — BİLEREK `deploy.yml` DEĞİL, yayını bloklamasın).
**① icra kapısı:** ölçüm/tarama (`sed/wc/head/...`) + `python3` araç koşumu ANA oturumda da GEÇER, `OLCUM-SERBEST rol=ANA sinif=...` RAPOR edilir. TABAN birebir: `sed -n '1,5p'`→deny(sed) · `wc -lc`→deny(wc) · `grep|head -25`→deny(head) · `kutu-arsivle.py --durum`→deny(allowlist). **KAPALI KALDI:** `python3 -c`, repo-dışı betik, `curl/wget` (emirde ADIYLA anılmadı).
**② kod-kilidi:** `.py/.sh` yazımı GEÇER + SAYILIR → `--rapor` `MIMAR_KOD_YAZDI=<n dosya>`. **YASAK KALDI:** `urunler.json` + gizli ürün-kaynak kaydı · `.html/.css/.sql` · `settings*.json` · CEKIRDEK. 🔴 Kapı-ADI kalkanı adım 3'ÜN ÖNÜNE alındı, yoksa erişilmez kalıyordu.
**③ komut stili:** REDDETMEZ, UYARIR + tırnak-duyarlı. ⚠️ Spec'in 2 alt-iddiası ÇÜRÜDÜ: `2>/dev/null` ve `->224` ZATEN geçiyordu; gerçek tetik `>` + BOŞLUK (`kutu 250 -> 500`). 🔴 İlk onarımım çift tırnakta `$`ı da metin saydı — **kendi kabul probum yakaladı**; POSIX'te `"$?"` GENİŞLER, maske artık desen-başına (`HEPSI`/`TEKIL`).
**④ kota:** DEVAM 130→**500** · kutu 250→**500** · MEMORY 45→**500**; **BAYT ekseni HÜKÜM VERMEZ** (`defter-kota-taban.py::BAYT_HUKUM_VERIR=False`, tek anahtar, hafıza kolu da onu okur) — gerekçe ÖLÇÜLDÜ: MEMORY bayt tavanına **36 B**, DEVAM **166 B** kalmıştı, satır 500 olsa kilit tek satır sonra dönerdi. Bayt `BAYT_RAPOR` olarak basılır. TABAN: kutu 274/250 → `KUTU_ASILDI` rc=NONZERO (evin HER commit'i kilitli) → şimdi `KUTU_YESIL 293/500` rc=0. `koru=3` duruyor, `tasinabilir=4` (rotasyon ilerleyebiliyor). **Araç kusuru kapandı:** `KORUMALI değil` artık veto ÜRETMEZ — `ETIKET_OLUMSUZ=1` blok 9/satır 149'u ADIYLA basıyor, veto 17→16 (NON-GROWTH, TR-güvenli katlama).
**MENZİL — spec öncülü YANLIŞTI, ölçüldü:** "kopyalar `~/.claude/`da, repo DIŞI, git YOK" ⇒ gerçekte `~/.claude/`da **0 kopya**; 35 kopyanın **33'ü kardeş repolarda İZLENİYOR** ⇒ YAZMADIM. 🔴 Ama KALEM 1 için propagasyon YAPISAL: kardeş 5 ev **SHIM** taşıyor (`kapi_dagitim.py`, kanonik gövdeyi ÇALIŞMA ANINDA okur) ⇒ merge'de 5 evde ANINDA canlı. `--filo`: **6 ev, 5 YEŞİL, BaBa=SHIM_BAYAT** — main'in DOKUNULMAMIŞ kopyasında da AYNI SHA ⇒ BENDEN ÖNCE bayat, BaBa'nın repo-içi dosyası, mimara kalem.
🔧 **AÇIK (mimara):** ① `kral-yordam` SKILL.md ana checkout kopyası worktree'den YAZILAMIYOR (harness engeli) + `.claude/` **gitignore**'da ⇒ skill güncellemesi git'le TAŞINMAZ; bitmiş metin worktree kopyasında, yedek `~/.claude/cron/emekli-arsiv/kral-yordam-SKILL.md.2026-09-11-tikayici-oncesi`. ② BaBa shim'i `kapi-dagitim-kur.py` ile yenilenmeli. ③ `mimar-kod-kilidi.py` 5 kardeş evde GERÇEK kopya (shim DEĞİL) ⇒ ②'nin sınıfı orada da var.
⚠️ **ÖNERİ (uygulama DURDURULMADI):** `MEMORY.md` her oturumun bağlamına yükleniyor; 500 satır tavanı oturum başına token maliyetidir. Okan bilerek istedi, uygulandı — sayı görünür kılındı.

## ✅ 10 EYL ana oturum-7 — 5 dal main'de, yayin indi, kapi kablosu ONARILDI. TAM METIN `DEVAM-ARSIV.md` + kutu (E5)
- 🔧 **ACIK:** ① YEDEK `ardisik=0` ama kronik MASKELENDI (ozne MaCiT; K338: beyan anahtari dosya ADI ekseninde) · ② `gecmis-nobeti` pre-push kancasi bu makinede KURULU DEGIL.
- 🔧 **CIPTE:** `BaBa-TamirciPrompt-10Eyl` (`task_cc6690d8`) PANELDE bekliyor.

## ✅ 9 EYL — ana oturum-3: **temizlik + K391 KILIDI ACILDI (filo commit kilidi kalkti)**
- 🔧 **TOHUM KAPSAM:** eksik 3 ev (`OteL`·`EyLüL`·`eLiF` — `OteLLa` YANLIS ad). Spec+kabul KUTUDA, F8 `OLCULEMEDI`.
- 🔧 **ACIK:** ① 17 dal envanteri arsivde, **SILINMEZ**, 30 gun atif testi basladi · ③ kota RED metni "okuma gecer" diyor ama `python3` kesiliyor (ikinci kopya) · ④ K396 `arsiv-kapisi` `BEKLIYOR` jetonu govdede YOK (`grep -c`=0, bagimsiz dogrulandi) · ⑥ **K397 ACILDI** — nobetci yesil basarken onerdigi kurulum yeri CANLI duzlem DEGIL, atif 0; TAM METIN + kabul olcutu `DEVAM-ARSIV.md`, baslik "K397 — 9 Eyl 2026" (govde izlenen belgeye YAZILMAZ, E5) · ⑦ `peaceful-margulis-057d93` artik ARTIK dal (kod blob'u main'de, yalniz defter satiri kaldi) · ⑧ ArTisT/Okan isi: kategori panel basliklarina urun sayisi — cip ACILDI.

## ✅ 10 EYL — cip `KraL-Tamirci-10Eyl` / **K401 KAPANDI** — TAM METIN `DEVAM-ARSIV.md`, baslik "K401 — 10 Eyl 2026" (govde izlenen belgeye YAZILMAZ, E5)
- 🔧 **ACIK:** ① `YEDEK_ZINCIRI_KIRIK ARDISIK=4 > TAVAN=3` — sayac 3->4, hal KRONIK; ozne MaCiT duzlemi, K338 ile ayni yerde · ② SERIT B'nin kalan 4 kirmizisinin **3'u MERGE ile kapanir** (`sharp-boyd-536a5a` + K399 dali, iki tarafta dogrulandi) · ③ `recete-kapisi REDDEDILEN=1` (K392 ailesi) DOKUNULMADI. **MOTOR ORANI:** m3 **0** — is `kapi/olcum kodu` sinifi, Claude'da KALIR.

## 🔁 10 EYL ana oturum-6 — **TAM METIN `DEVAM-ARSIV.md`** (baslik "10 EYL ana oturum-6"); 3 kapanmis isaretci de indi (md5 birebir, eksik 0)
- 🔧 **ACIK:** ① ana checkout CANLI cipin 3 dosyasini AYNILIYORDU (02:32'de HEAD'e dondu, kayip YOK) — kok neden OLCULMEDI · ② Drive `backup-v2` yok. (kapi-envanteri kalemi 10 Eyl'de KAPANDI: kablo onarildi, 8/8.)
## ✅ 10 EYL — ana oturum-5 ISARETCI (**TAM METIN `DEVAM-ARSIV.md`**, baslik "10 EYL ana oturum-5"; md5 birebir)
- 🔧 **ACIK:** ① `kurtarma/stash-8agu-baska-oturum` tek kopya KALDI (bilincli; 128 scratch dosyasi saklanmayacaksa dal SILINEBILIR — hukum BaBa'da) · ② **kanca kopyasi her push'ta BAYATLIYOR** (bugun 6 kez); her itme iki turda bitiyor, bloklamiyor ama maliyet cift (③ KAPANDI 10 Eyl: kok neden harness DEGIL, `hooks` kablosu EKSIKTI; onarildi.)
## 🔴 9 EYL KALEMLERI (TAM METIN KUTUDA — 9 Eyl KraL bloklari)

## 🔧 8 EYL 02:xx TURUNDAN ACILAN KALEMLER
- 🔧 **K386 → ISARETCI, TAM METIN ARSIVDE** (md5 birebir): kalan uc kova `G-BIZIM-BILINMEYEN` 117 · `E-DIGER` 21 · `F-OTORITER-CELISKILI` 8 (`D-CC0` 428 risk YOK). Olcum araci commit'li: `python3 tools/lisans-capraz-olcum.py --detay`. KALEM ACIK.
- 🔧 **K387 → ISARETCI, TAM METIN `DEVAM-ARSIV.md`'de** (md5 birebir): kok neden MaCiT'te — `hasat_*_mekanik.py::lisans_normalize()` bosluklu desenleri kaciriyor. Cip oturumu 9 Eyl'de arsivlendi, KALEM ACIK.

## 🔧 BU TURDAN ACILAN KALEMLER (hepsi olculdu, hicbiri baslanmadi)
- **K380 (h) BOLUMU MAIN'DE YOK:** geri inecekse build **SONRASI** cagri yeriyle ya da `urun/` yokken `KAPSAM DISI` (OLCULEMEDI DEGIL) inmeli; yoksa iddia olculmemis kalir. Kabul: `deploy.yml`'de build-sonrasi atif ≥1 ∧ kapi rc=0.
- **K381 `d1-sync.py` GERI-OKUMA SOZLESMESI:** arac "yeni: 74 … dogrulandi ✅" bastiktan HEMEN sonra kendi `--durum`'u ayni satirlari EKSIK gosterdi (MaCiT olctu). Replika gecikmesi mi teyit hatasi mi **AYRISTIRILMADI** → `OLCULEMEDI`. Kabul: tek yazimdan hemen sonra + N dk sonra iki `--durum` (arada baska senkron YOK).
- **K383 `satir_soru` YUZEYI ERISILEMEZ:** link `prova=="kapali"` ister, katalogdaki 16/16 konfigur urun canlida `acik`. K89 "3 yuzey" sayimi SISIK, dogrusu **2 olculdu + 1 erisilemez**. Kabul: canli Worker'in non-200 dondugu konfigur satir (OKAN KAPISI).
- **K384 `kisisel-veri-test.py` bir beyani yanlis basiyor** — TAM METIN + kabul olcutu: `DEVAM-ARSIV.md`, baslik `K384 — 8 Eyl 2026` (govde izlenen belgeye YAZILMAZ, E5).

## 🔁 6 EYL KAPI-ENVANTERI ISARETCI — TAM METIN `DEVAM-ARSIV.md`'de. 🔴 **10 EYL DUZELTMESI: "ucu de KURULU, kirmizi SAHTE" hukmu YARIM cikti** (ust blok) — biri sahte, ikisi GERCEK. `R_YOL` bagi + SERIT B kalemi ACIK.

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
