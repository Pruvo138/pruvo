# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔴 K355 (31 Agu) — TERK SUPURMESI CANLIDA INERT, 3. ARDISIK TEYIT · PARA 4.160 TL
`terk-supurme {bakilan=OLCULEMEDI degisen=0 ulasilamadi=OLCULEMEDI}` — `degisen=0` OLCULDU (3 tur);
digerleri D1'den GORULEMEZ (`ulasilamadi` hicbir sey yazmaz -> kostu/kosmadi AYIRT EDILEMEZ).
5 satir **4.160 TL**, en eski `JL5` 9 gunluk. 🔴 **KAPATAN OLCUM:** `odemeHukmu` :936 `det`i LOGLAMIYOR;
retrieve `errorCode`+`errorMessage` (siparis_no ile, kisisel kolon YOK) yazilmadan "token omru YAPISAL"
ile "gecici ARIZA" ayrilamaz. Ucuncu hal ADIYLA yazilir. → [[terk-supurmesi-canlida-inert]]

## 🟠 K356 (31 Agu) — NEDEN LOGU YAZILDI (`KraL-ErrorCodeLog-31Agu`); DEPLOY=OKAN, DAGILIM=OLCULEMEDI
`odemeHukmu` `altyapi-hatasi` kolu artik `errorCode`+`errorMessage`i `siparis_no` ile basiyor.
IKINCI BICIM ACILMADI: mevcut `olcum {...}` satirina 2 alan (olcum.js beyaz listesi -> musteri_*/
fbp/fbc/ga_client_id/token YAPISAL olarak giremez); metin token maskeli+kirpik (iyzico.js tek kaynak).
`det` bosken `YOK` basar. Dal `claude/determined-chaplygin-e8f029`. SAYILAR: taban 23 kol 23 YESIL
`KIRMIZI_SETI=[]` -> is sonrasi AYNI · `terk-supurme.mjs` 60->**98 iddia/0** · mutant **10/10**
(8 hedefli oldu + 2 KONTROL yesil, calisma agaci sha AYNI).
🔴 **LOG OKUMA=OLCULEMEDI, IKI AYRI SEBEP:** (1) kod CANLIDA YOK (merge+deploy Okan kapisi),
(2) `~/.claude/cron/.cf-token` observability sorgusunu **HTTP 403 (code 10000)** ile reddetti ->
deploy sonrasi bile okunamaz; token'a `Workers Observability: Read` GEREKIR. Hukum mimarin.

## ✅ K353 KAPANDI (29 Agu) — esik sinifi + SILINEN kota kapisi (`KraL-EsikVeKota-29Agu`; TAM metin KUTUDA)
Onarim hedefi = ceza esigi -> komut INERT ([[onarim-kolu-zarar-esiginin-arkasinda]]). KUTU tavan 300->**250**,
kutu 253->**196** (dusen 57 == giren 57, kayip=0). DEFTER `SU_SEVIYESI_*` 12.288 vs **9.830** + BEST-EFFORT;
inert DEGIL (fiksturde eski 11.878, yeni 9.172). 🔴 `ca8c3815`in sildigi kota kapisi `3cea0b19`'dan geri
kuruldu + kanca adim 8 + nobet.yml SERIT B; asim rc=1 RED, tavan alti GECER, mutant KIRMIZI yakti, bataryalar
tabanla AYNI. 🔴 **MERGE SONRASI `kanca-kur.py`** (once kosulursa filo felci).

## T1+T2 KAPANDI (29 Agu) — panel "Urunler": ustyazim kuyrugu + gorsel/STL/kaynak-link; TAM HUKUM KUTUDA
T2 canli 2x: kuyruk->main(`dccb46af`,`d2ae7a86`)->canli; katalog SABIT. 🔴 **ACIK: worker deploy=OKAN** + T1a —
kutunun "deploy edildi (`b26cedd8`)" iddiasi CURUTULDU: SHA 5 evin HICBIRINDE yok (`cat-file -t` 5/5 fatal).
## 🔁 28 AGU 18:00 CANLI DURUM — OKAN 17:00 EMRININ BES KALEMI DE KAPANDI (onceden -> sonra)
🔴 **N2B BORU ONEKI SINIFI → HAFIZADA:** [[isci-cagrisinda-echo-stdin-etiketi-yutar]] (K345 ile kapandi).
🔴 **K337:** butce kesintisi sade `rc=1` donuyor, karantina dusus sayiyor (3 ardisik = 6 saat). META=RAF.
🟠 **OKSUZ AGAC (2):** `practical-dirac-a95ed1` -> `44c92f6e` (K258/K168 tek-kaynak modulu `serbest_cagrilar.py`)
ve `sweet-cartwright-b59181` -> `a24550ce` (`kutu-arsivle.py` jeton isleme) — oturumlari OLU, commit'leri
main'de DEGIL, tabanlari bayat (iki-nokta diff `urunler.json`'da 1828 satiri yanlislikla "silinmis" gosteriyor).
Cip `KraL-OksuzAgaclar-28Agu` tasiyor; **katalog geri sarilmayacak** (kabul sarti).
🔵 **WORKTREE 13 -> 11** (`trusting-sutherland-157a62` birlesmisti + oturumu oludu, kaldirildi). Kalan
agaclarin hepsinin oturumu CANLI ya da uzerinde birlesmemis is var -> dusurulmedi.
**BEKLIYOR:** MaCiT dilim'leri (K332 blokeri kalkti).

🟢 **K344 OKSUZ AGACLAR KAPANDI (cip `KraL-OksuzAgaclar-28Agu`, main `a5fc8f22`):** iki dalin isi de main'de.
`44c92f6e` (A) +978/-303 · `a24550ce`+`c665031f` (B) +525/-50, ikisi de TASINDI (SUBSUME degil). 🔴 **Katalog
GERI SARILMADI: `urunler.json` 693.472 -> 693.472 satir BIREBIR**; "1828 satir silme" iki-nokta artefaktiydi.
`serbest-kume-tekkaynak-test` **19 vaka/4 KIRMIZI -> 22 vaka/0 KIRMIZI** · `mimar-kilit-test` 314/307 DEGISMEDI ·
bekci `--teslim-karari` YESIL · `kutu-arsivle --kapanislari-isle --kuru` ana agacta **`CEVRIM=1`** (K341'in civisi).
Worktree 11->10, disk 504M->454M. 🔴 **YENI KALEM K344-A:** A ve main'in K343'u AYNI sinif isi iki kez yapmisti;
K343'un M6/M7/M8 mutantlari bekci tablosunu bozup DEFTER CARE'inin RED olmasini bekledigi icin kirmiziydi (yanlis
eksene civili) — eksen `MX5`'e TASINDI (dar mutant: bekci RED, komsu defter GECER). 🔴 **YENI KALEM K344-B:**
`C3` yalniz kaynak->arac yonunu olcuyor; arac->kaynak yonu (araca eklenen bayrak tabloya yazilmamis) HIC olculmuyor —
`--kapanislari-isle` tam bu bosluktan dustu, elle kapatildi (`a5fc8f22`). Kabul: ters yon kolu + onu olduren mutant.

## 🔁 29 AGU ~05:0x — MIMAR OTURUM KAPANISI (tam metinler KUTUDA; burada yalniz canli durum)
- ✅ K332/K350-B MERGE · K349 sinif esigi · bayat hafiza duzeltmesi · 30 Agu temizlik kaniti →
  **TAM METIN `DEVAM-ARSIV.md`'ye TASINDI** (31 Agu, kural 11; arsiv 22.303 -> buyudu).
- 🔴 **K354 — ONCULUM YANLISTI, DUZELTTIM:** `nice-swanson-706912` agacindaki 47 commit'siz dosyayi
  "kazayla silinen, geri alinacak is" sandim. O oturumun KENDI sayili kapanisi cururttu: `ca8c3815`
  **KASITLI** — *30-gun urun-kaniti testi*, 47 denetim dosyasi bilerek silindi (kapi **112->97**),
  cekirdek yerinde, yayin YESIL (`4c80278f`). Dosyalar STUB DEGIL, tam govde (60/51/46 KB).
  ⚖️ **OKAN HUKMU (30 Agu): supurme SURUYOR; yalniz CLAUDE.md'nin ZORUNLU KILDIGI araclar doner** —
  kural/zorlayan celiskisi kapanir, ~34 supurulmus KALIR. Inecek 3 (+bataryalari): `worktree-tavan-nobeti`
  `mimar-commit-kapisi` `chip-duzeni-kapisi`; `mimar-kod-kilidi`+`mimar-icra-kapisi` main'de VAR.
  Cip kapsami daraltildi. 🔴 **O AGAC, 3'u kalici olana kadar KALDIRILMAZ.**
  *Ders: silme kaza mi karar mi — silinen dosyaya degil SILENIN KAPANISINA bakilir.*

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
