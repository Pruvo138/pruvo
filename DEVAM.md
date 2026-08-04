# DEVAM (KraL) — 4 Agu 2026

## 🔚 OTURUM KAPANISI — 4 Agu · YENI OTURUM ONCE BUNU OKU

**CANLIYA GITTI (bu oturum, hepsi SHA-kanitli + canli olculdu):**
`bd463ee1` marka-model uyeligi `marka[1]` konumundan kurtarildi — canli Zafira **10 -> 21**,
Golf 177 -> 182, model sayfasi 433 -> 485, kaybolan urun 0 ·
`948be793` kusak/varyant katlamasi + model-olmayan sayfalarin kapanmasi + Transporter
birlestirme — Transporter **44 -> 143**, Astra 77 -> 126, Golf +17, Zafira +0 (degismemeli,
degismedi); `ford/focus-st` · `fiesta-st` · `ecoboost` 404 oldu, 14 urunun tamami korundu ·
`9cb1e3ee` cron nabiz korlugu + KADANS KURTARMA (uzlastirma artik push'a bagli, cron ikinci kol) ·
`896f05fa` D1 sapma sinyali yayin sagligi sinyalinden AYRILDI (susturulmadan; yeni
`workflow_run` alarm kanali canli ateslediği dogrulandi) · `117f1420` yayin hatti acildi ·
`4373c02f` + `01bc95f9` DEVAM.md hijyeni.

**KOSUYOR:** dal `model-cip-kanonik` (HEAD `538dc838`, worktree `agent-a6b1653e0fffd19c5`)
**MERGE KAPISINDA** — model cip satiri kanoniklestirildi (`Peugeot 206` -> `206`; cip 479 -> 467,
cip sayisi ile sayfa sayisi ayrismasi 73 -> 0), canlida duran `/marka/peugeot/iphone/` ve
`/marka/mitsubishi/electric/` kapandi, **K19 capraz-marka rozet kapisi** kuruldu
(`ROZET_DISI_CIFT` 6 -> 20; `(Peugeot,Berlingo)`/`(Opel,Berlingo)` mayini ILERIYE DONUK kapatildi).
Kabul: 20/20 + 122/122, mutasyon 28+5 ve 30+5, parite birebir, kaybolan urun 0.

**BEKLIYOR — baskalarinda:**
- **MaCiT** → metin/alan boslugu 1. PARTI (en buyuk 50 model; kaynak liste kararsiz jetonlar
  cikarilmis 6288 kayit / 4513 urun / 817 cift) + EK PARTI (616 urun, **0 yeni sayfa**).
  Parti bitmeden 2. parti acilmiyor. Ayrica hasat aciklama SABLONU kok nedeni.
- **HocA** → `ara*` rota oneki 3 landing'i 403 yapiyor · **YENI:** uc `model` parametresini
  `uyum[].model`'de TAM eslesmeyle suzuyor; 467 cipin 210'unda cip ile ucun teslimi ayrisiyor
  (965 urun-kalemi). Musteriye sayi gosterilmiyor; ucun katlamayi almasi karari onda.
- **KaaN** → `rulman` semasi onarilinca satisa acma karari bende · **ArTisT** → marka-model
  sayfa esigi onerisi.

**OKAN'DA KARAR YOK.** Bugun sorulan uc karar verildi ve uygulandi: asamali git (1. parti 50
model) · Zafira sayfasi 28 hedefi, `Zafira Life` ayri bolumde · yayin hattini KraL acsin.

**🔴 SIRADAKI TUR — bende, oncelik sirasiyla:**
1. `model-cip-kanonik` merge kapisini kapat, canli DELTA ile dogrula (mutlak sayi bekleme).
2. Kararsiz jeton SINIF 1 (152 urun: BMW `GS` · VW `T1`-`T6` · BMW `R/K Serisi`) — 3 yeni sayfa,
   kanonik ad CIPLAK jeton (olculdu: `?ara=T4` 74 vs `Transporter T4` 15).
3. C kovasi (87 urun): olcu satiri sayisal model adiyla cakisiyor — `ara`->`marka` toplu kopya YASAK.
4. Kutudan devralinanlar: gorsel-kutu bosluk kusuru (`build.py` `height` niteligi) · negatif
   onbellek Cache Rule · `hasat_kontrol.py` atif-turu kapisi.

KAPANDI: 4 Agu marka-model uyeligi canli turu — dokum DEVAM-ARSIV.md de (git disi).

KAPANDI: odeme yolu bayatlik seridi — dokum DEVAM-ARSIV.md de (git disi).

### 🟡 ACIK KALEM 1 — kuyruk geri tepmesi OLCULEMEDI (48 saat sonra yeniden olculecek)
ACIK: ayrinti DEVAM-ARSIV.md de (git disi).

### ✅ KAPANDI (4 Agu) — guard, merge'in getirdigi katalogu dalin BAYAT haline geri sariyordu
Onarim main'de: merge SHA `0f8f5c01` (dal 2 commit, 5 dosya, +1276/-141; katalog dosyalari
diff'e GIRMEDI). Guard artik merge halini gorur: iki ebeveynden birinden gelen degisim
mesrudur; provenans cozulemedigi halde veriyi SESSIZCE degistirmek yerine commit'i
gerekceyle REDDEDER ve calisan cikis yollarini basar.
BAGIMSIZ OLCUM (curutucu): kabul testi **26 iddia / 0 kirmizi**, 5 kosumda ayni imza
(determinist); mutasyon bataryasi **16 mutant + kontrol mutanti (bos kume), SAPMA 0**,
TABAN_IDDIA 26, Traceback 0, izlenen 5 canli dosyanin sha256'si once=sonra AYNI.
Kabul testi artik yayini BLOKLAYAN seritte kosuyor (`build` isi, sayfa uretiminden ONCE;
yumusatma yok) — `is-akisi-kapisi.py` rc=0, olculen kapi cagrisi 192, serit tablosuna
giris EKLENMEDI (dosya dala hic dokunmadi); ayni agacta onceki commit rc=1 veriyordu.
Davranissal parite: urun partisi · merge (olay senaryosu) · rebase · amend · cakisma
cozumu — 5 akisin 5'inde onceki commit ile ayni rc + ayni katalog sha; atif/gorsel/
aciklama korundu. Yerel sure 2,6 s. Kapilar 8/8 rc=0. D1 teyidi 17914 = 17914 (uc eksen).

### 🟡 ACIK KALEM — korumanin tasinabilirligi
ACIK: koruma her ortamda ayni sekilde durdurmuyor; ayrinti DEVAM-ARSIV.md de (git disi).
Dal icinden kapatilamaz (ilgili dosya depoya girmiyor) — ayri tur gerekiyor.

### 🟡 ACIK KALEM — kabul testi ortam degiskeni kirliligine kirilgan
Olculdu: ortamda `GIT_DIR`/`GIT_WORK_TREE` tanimliyken kabul testi 26 iddianin 21'inde
KIRMIZI yaniyor (gecici depolar yerine dis depo hedefleniyor). Bugun ulasilamiyor —
ne is akislari ne de yerel kancalar bu degiskenleri kuruyor — ama kapi artik yayini
BLOKLADIGI icin ucuz sertlestirme onerilir: test kendi alt surec ortamindan bu uc
degiskeni (indeks dosyasi dahil) SILSIN.

KAPANDI: nabiz nobetcisi A5 TESLIM ekseni — dokum DEVAM-ARSIV.md de (git disi).

## 🔴 YENI ACIK KALEM — A0 DAMGA alarmi kirmizi: D1 uzlastirici cron'u TESLIM ETMIYOR
ACIK: ayrinti DEVAM-ARSIV.md de (git disi).

KAPANDI: shop bayatlik fail-closed kanitlari — dokum DEVAM-ARSIV.md de (git disi).

## 🔴 YENI ACIK KALEM — katalog geneli metin/alan bosluğu (envanter cikti)
ACIK: ayrinti DEVAM-ARSIV.md de (git disi).

ACIK KALEM: yayin hatti icerik denetimi — dokum DEVAM-ARSIV.md de (git disi).

## 🟡 YENI ACIK KALEM — `CLAUDE.md`/`AGENTS.md` git disi symlink
ACIK KALEM: symlink surumleme ayrintisi — dokum DEVAM-ARSIV.md de (git disi).
