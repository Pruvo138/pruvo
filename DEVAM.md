# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.


## 🔁 DEVIR — 19 Agu 2026 22:1xZ, eski hesap → yeni hesap (KraL)
**SIRADAKI TEK IS:** Uc hazir dali merge kapisindan gecirip main'e al — `kral/n1-gozcu-kablolama`
`fd6b6d8d` · `kral/n2-kirleten-onarir` `a87f1809` · `kral/k184-talep-sihirbazi` `f623d712`.
**Nerede kaldim:** 20 Agu ACILIS: main=origin `519fdb2d`, agac TEMIZ, worktree **1**, cakisma
on-testi ucunde de YOK, D1 bes eksen YESIL (29573), `.ci-token` **GECERLI** (01:45 turu rc=0
gercek icra); tazelemeyi BaBa yapti. Spec `tools/paket-uc-dal-merge.md`.
**20 Agu 2. tur (KraL):** main=origin, agac TEMIZ, worktree 1. KAPSAM `merge-base...uc`
ile olculdu, spec tablosuyla BIREBIR (2/+23-3 · 9/+3111-12 · 9/+2359-104); `urunler.json` temasi ve
sizinti YOK → §4 temiz. Cakisma on-testi guncel main'de ucu de TEMIZ (N1'i defter rotasyonum bir ara
catisti, K136 satiri birebir geri konup kapatildi). N1 bataryasi REPO DISI `~/.claude/cron/` (4 arac,
dordu de VAR); repo delta'si DEVAM.md + `pre-push` (20 satir RAPOR-ONLY, `exit` YOK, 0,045 sn — okundu,
temiz). Engel bataryalarin `python3`'u — kapi reddi OLCULDU, kod kilidi kosucu betigi de kesti → odev
**`tools/paket-uc-dal-merge-okan-komutlari.md`**'de dal basina tek `&&` zinciri (OKAN KAPISI). Onceki tur: K190 `4340c0b9` ·
K216 `8634bc49` · K206 `7ce644ae` · K223 `9965c4fb` · K212 `df7425ea` · K224 (isci hatti) ·
shop worker Okan'in deploy'uyla taze (`5606ffbe`, TALEP_SAYAC KV bagli) · D1 bes eksen YESIL.
🟢 **N1 KABLOLAMASI CANLI** (cron repo disi): `crontab` gozcu `8,23,38,53` (15 dk) + `ci-nobeti.sh`
artik once `nobet-tetik.py --karar` kosuyor; kalp `22:08Z` (1 dk taze). Dal merge BEKLIYOR.
**Acik dal:** merge sirasi N1→N2→K184; ayrica `kral/k195-defter-rotasyon` (DEVAM.md cakismasi)
+ `kral/k214-motor-tek-kaynak`. **Baskasinin calisma kopyasinda duran:** YOK.
**Zamanlanmis nobetler:** crontab 5 satir CANLI ve OLCULDU · scheduled-tasks kayitli 3, ucu de
`enabled=false` — KASITLI: `saatlik-github-hata-nobeti` crontab surumuyle MUKERRER olurdu,
`kuyruk-geri-tepmesi-48sa` penceresi gecti, POM izleyicisi bayat. Yeniden kurulan: YOK.
**Okan'da bekleyen karar:** yok (shop deploy bugun yapildi; K200(i) canli `--kuru --d1` duruyor).


## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)
- 🟢 **K214 (19-20 Agu, `KraL-Motor kapisi` chip — DAL OLCULDU, MERGE MIMARDA):** kurucu motor
  listesini GOMUYORDU (`mimar-kapi-kur.py`), 13 Agu kopyasi DONDU → evler emekli deepseek'i kabul,
  canli `kimi`'yi RED; kirmizi ev DORT degil **BES** (BaBa da). Blok+imza artik `mimar_kimlik.py`
  `ISCI_MOTORLARI`'ndan URETILIR (ikinci kopya YOK); nobetci `tools/motor-tek-kaynak-kapisi.py`.
  Sayilar kutuda.
- 🔴 **K212 (`tools/yedekle.py` iki GERCEK kusur, BEKLETMEDE):** tam metin+kabul ARSIVDE; SeritB kapsaminda DEGIL.
- ✅ **19 AGU KAPANANLAR (bloklar ARSIVDE+kutuda):** K186 · K205 · K210 · K211 · K190 · K215/K80 · SeritB · K224 · K209.
- 🔴 **MOTOR KARARI (Okan, 19 Agu aksam — LUNA EMRINI GECERSIZ KILAR):** kapali kume `minimax-m3 kimi claude`; deepseek/codex/luna **RED** (K224'te uygulandi, cron kimi'de kaldi).
- 🔧 **K200 (saklama YURURLUKTE — TAM METIN ARSIVDE):** (i) canli `--kuru --d1` ⚖️ OKAN KAPISI ·
  (ii) periyodik kablolama MIMARDA · (iii) kablolamanin KOSTUGU kanit. Sira: sema→tesisat→trafik.
- 🔴 **K213 (19 Agu, MaCiT olctu → hukum KraL'da, sahibi MaCiT):** CC BY/BY-SA **50 kayitta**
  `lisans.tasarimci` yer tutucu (`?` 49 + `...` 1) → canlida atif KOSULU karsilanmiyor.
  HUKUM KUTUDA (4 madde: urun CEKILMEZ + `lisans` SILINMEZ · ad KAYNAKTAN · kurtarilamayanda
  K27'nin dar kaynak-LINKI kolu · 2. vaka oldugu icin KALICI fail-closed KAPI).
  kabul: kapi + mutant + ihlal sayisi duser + `denetim-kapisi` yesil.
- 🔧 **K199 (19 Agu, KraL):** `is-akisi-kapisi.py` "etkili tasiyici" tanimi LITERALE capali;
  varlik turetilmis mekanizmaya gecince korlesiyor (K193). Care: sonucu olc ya da makine-okunur
  beyani tasiyici say; mutant + negatif vaka sart. · 🔧 **K201 SINIF: KAYIT KENDINI OLCMEZ** — bes vaka;
  her kayit ya TURETILIR ya kendi sayisiyla KABUL EDILIR, "EKLE" yetmez SAYI sart.
- 🔧 **K196 (DEPO GENELI):** CI node 20 / yerel 25.8.1 → yerel JS yesilleri CI surumunde OLCULMEMIS. ARSIVDE.
- 🔧 **K197 (19 Agu):** pre-push maliyet beyani 3,16 sn diyor, olculen medyan **6,11 sn** (5 sn esigi asilmis); sayiyi YORUM soyluyor, dogrulayan yok. ARSIVDE.
- 🔧 **K217 (19 Agu, KraL push ciktisinda OLCTU):** tavan nobetcisi, baska kapinin self-test fiksturlerini
  (temp `pruvo-kapi-test-*`, detached, saniyelik) MIMAR sayip sahte `TAVAN ASILDI SAYI=3` yaziyor (kanit
  hafizada: [[iki-kovali-siniflama-ucuncu-sinifi-yutar]]); yordam "kaldir" dedigi icin GERCEK agac silinebilir. kabul: fikstur duzlemi sayimdan DUSER + mutant hedef-kol atfi + gercek 3. agac YAKALANIR.
- 🔧 **K189** (`ci-kapsam-test.py` hukum ekseni; kabul: aday>0 iken `OLCULEMEDI`+sifir-disi rc +
  ayri jeton + mutant hedef-kol atfi) · 🔧 **K191** (tarama SPEC'i isi ONCULDEN aliyor; sahibi
  MaCiT; kabul: ILK blok KAPSAM ON-OLCUMU + tazelik capasi). **Ikisinin tam metni ARSIVDE.**
- 🟠 **K184 — TEK KALEM:** dal `867cc80e` origin'de, K80 ARTIK BLOKLAMIYOR; kalan kirmizi
  `talep-sihirbazi-test.py` VAKA 36 (batarya kabuk metnini olcuyor, adim araca tasindi).
  Kalan is + delege plani POSTA KUTUSUNDA. Uc daldan CIKTI; HocA E6 dumani bu merge'e bagli.
- 🔧 **K192** (Okan: kalem ac DOKUNMA): `kimi` KURULU kapisinda YOK, dagitim kaniti VARLIK olcuyor. ARSIVDE.
- 🔧 **K202-kendini-test** (M06 cokme + bayat capa) — 🔴 SAHIPSIZ: SeritB chip'i "bende HIC olmadi" diye olctu (onun uyesi K203'tu, YESIL kapandi). kabul: capa govdeden count==1, `beklentiyi tutmayan: 0`.
- 🟠 **K206 (TeKiN→KraL; 3 KARAR VERILDI, icra chip'i sirada):** 8 uretec sari seriye — saklama AYRI
  AILE · gyro `doku=duz` · 8 fiyat ONAY (280/190/170/350=TAVAN/160/240/140/220); kupler render CELISKILI.
  PAKET main'de (`7ce644ae`). kabul (icra): ONIZLEME_AILELER 22→30 · taban-fiyat 21→29 · +8 sari kayit · 8 gorsel R2 200 · parite yesil.
- 🔴 **K222:** `uzlastirici-onarim.py:161` `if rc == 0`, `:178` bayatlik kolundan ONCE; kapi yazmayi
  bloklayip rc=0 donunce surucu "ONARILDI" cikiyor (`32272271453`). kabul: imza varsa TEKRAR
- 🔧 **K220 (KraL):** `marka_yazimlari()`+`taninmis_mi()` TEK listeden besleniyor; liste iki rol tasiyor
  ("baslikta aranan ad" + "MODEL OLAMAZ jetonu"). Range Rover'i markaya yazmak CANLI `/marka/land-rover/range-rover/`
  sayfasini (6 urun) OLDURUYOR — ayrilmadan dokunma. Girdi: K216 raporu EK + `arama.py:2201`. SIRA: D bitti, sirada A.


## KraL ACIK ARTIKLAR (19 Agu anlati blogu ARSIVE TASINDI; kota uyarisi da orada)

- ↩︎ **TAM METIN ARSIVDE** (2026-08-20 isaretciye indirme): bu blogun tam metni `DEVAM-ARSIV.md`'de "2026-08-20 — ISARETCIYE INDIRME: asagidaki blogun TAM METNI defterden BURAYA TASINDI (defterde baslik + tek satirlik isaretci kaldi)" basligi altinda.

## OKAN'DA

- 🔧 Eski yedek klasorunu backup-v2 icine tasima · K89 olcum eylemi silme karari.
  (16 Agu: rotasyon bunu bir kez arsive supurdu, geri konuldu; sinif kusuru K128.)
- 🔧 **TARIFE KARAR KURALI (olculdu, onaya hazir):** $20 KALIR; kota %80'e yaklasirsa ikinci saglayicinin $39 basamagi ($50 tek-saglayici yerine CESITLILIK). TAM GEREKCE ARSIVDE.
- 🔧 **22 Agu:** kimi/codex motor karari (K157) · $100 plan karari (once yanma olcumu).
- Olculen maliyet tabani: $18,72 / 1.081.021.287 token / 8.639 istek = ~$17,3/milyar; $20/ay + ~4,6 milyar/ay = ~$4,3/milyar.
- 🔧 **ODEME WORKER DEPLOY (19 Agu 16:29Z):** pruvo-shop bayatlik nabzi KIRMIZI (134,1 dk / esik 120); yayinlanmamis TEK fark `0f590d11` icindeki `shop/src/talep.js` YORUM satiri, davranis farki YOK. Kapatan eylem `npx wrangler deploy` = OKAN KAPISI. Detay ci-nobeti.log.


## ARSIVDE
14-20 Agu kapananlar `DEVAM-ARSIV.md`'de.