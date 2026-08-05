# DEVAM (KraL) — 5 Agu 2026

## 🔴 5 AGU OTURUM ACILISI — HASAR TARAMASI (kota kesintisi sonrasi)
**Kayip is YOK.** Bes deponun (pruvo · hasat · jenerator · pazarlama · bot) calisma agaci TEMIZ;
dort worktree'nin hicbirinde commit'lenmemis degisiklik yok, ana checkout `origin/main` ile senkron.
`d1-sync --durum` uc eksen YESIL: **18.997** urun, sayi/sema/icerik birebir.

**🔴 GERCEK HASAR — ONARILDI, YAYIN ZINCIRI YESIL: canli 18.550 → 18.997 (447 urun).**

🔴 **ONCE MIMARIN KENDI OKUMA HATASI — DERS BUDUR (`[[hukum-yanlis-birimde]]` birebir tekrari):**
"28 ardisik kosum kirmizi" DOGRU ama bundan **"deploy hic kosmadi"** hukmunu cikarmak YANLISTI.
Job duzeyinde olculdu: o 28 kosumun **14'unde `deploy`+`yayin` YESIL kostu**; kosumlari kirmiziya
boyayan sey **bloklamayan** `ifsa-nobeti` alarmiydi. Yayini fiilen durduran **tek** kosum
sonuncusuydu (`ecc01a25`). Yani hasar "11 saat / ~1.500 urun" DEGIL, **tek commit / 447 urun**.
**Kural: kosum duzeyi sonuc, job duzeyi hukmu VERMEZ — `gh api` ile job'a bak.**

**Kok neden: VERI degil KOD da degil — YARGI BOSLUGU.** Bisect: `f35c421f` agaci 21/21 yesil,
`ecc01a25` 1/21; fark **yalniz `urunler.json`** (+8795 satir, 0 kod satiri). `Ford|raptor` zaten
yayindaydi, son parti `Yamaha|raptor`'u 2→6 urune cikarip esigin ustune tasidi, cift **YARGISIZ**
kaldi (K19). Ford Raptor (kamyonet) ≠ Yamaha Raptor (ATV) — ad cakismasi, emsal
`Ford|sierra`/`Suzuki|sierra`. Hukum: `ROZET_CAPRAZ_IZINLI`'ye 2 gerekceli giris
(`SAYISI` 22→24, `IMZA` hesaplandi). Kapi gevsetmesi YOK, `urunler.json`'a dokunulmadi,
MaCiT'e devir 0 kayit.

**Bagimsiz curutme (uc iddia da dogrulandi):** diff 1 dosya +12/−2, deny tablosu imzasi iki agacta
AYNI · batarya 31 oldurucu + 6 kontrol, beklentiyi tutmayan 0 · capraz kume iki kosumda da
43 cift / 20 model, main'in tek KALDI ekseni `YARGISIZ=[Ford|raptor, Yamaha|raptor]`, dalda `-`
→ **bu 2 giris disinda hicbir ciftin yargisi degismiyor** (olculdu, varsayilmadi).

**Merge + ikinci kilit:** merge `a4bcaf60`; ardindan `serit-a2/a3` **daha erken** bir adimda kirmizi
yandi — `devam-sinif-kapisi.py`, bu dosyanin kendi satirlarinda 2 sinif ihlali (kaynak: mimarin
push edilmemis `6d519e84` notu). Kapinin yazdigi cozum uygulandi (silme yok, arsive tasima),
commit `ca01b743`. 📌 Ders: DEVAM.md'ye yazilan hasar notunun KENDISI yayini durdurabiliyor.

**Canli dogrulama (kosum 30983315565, `--is-ancestor` rc=0):** `deploy` **success** · canli
`urunler.json` canonical + cache-bust'siz **18.997**, 25 rastgele yeni urun sayfasi 25/25 HTTP 200 ·
`d1-sync --durum` uc eksen yesil · **tam parite ana checkout'tan:** `parite-test.js` 1199 sorgu
BIREBIR (cikis 0), `parite-ege.js` 848 sorgu BIREBIR (cikis 0) — merge oncesi ikisi de OLCULEMEDI'ydi.
`yayin` job'i once failure verdi: tasarlanmis tavan (447 > `AZAMI_ADAY=300`); `yayin-kapisi.py
--geriye-doldur` ile kapatildi → `yayinda=18997 · taslak=0`, geri-okuma dogrulandi.

**🟡 ACIK KALEMLER (bu turda DOKUNULMADI, mimar karari):**
1. `ifsa-nobeti` kirmizi — bloklamayan alarm, onarimi `ifsa-kaynak-onarim-ve-daraltma` dalinda
   (164 isabet → 0) merge kuyrugunda. Kirmizi kaldigi surece "yayin zinciri kirmizi" sinyali
   gercek yayin arizasindan **ayirt edilemiyor** — bugunku 11 saatlik yanlis okumanin sebebi budur.
2. **`yayin` 300 tavani:** 447'lik parti tekrarlanirsa ayni kirmizi yeniden dogar (MaCiT'e yazildi).
3. `cron-nabzi` kirmizi — `d1-uzlastirici.yml` zamanlanmis teslimi 9,2 saattir yok
   (mevcut "A0 DAMGA" acik kaleminin ayni sinifi, bu merge'le ilgisiz).
4. OLCULEMEDI: `kanca-kablolama-nobeti.py --ci` 18 ekseninin 2'si (16 yesil, 0 kirmizi, cikis 0).
5. Depo hijyeni: 4 worktree → 3 (merge edilen silindi) + 3 push'suz yerel dal, tavan 2.

**OKAN HUKMU (bugun):** (1) hat yesile donene kadar diger mimar oturumlari acilmayacak — **kosul
KARSILANDI, acilabilir**; (2) worktree/dal hijyeni onarimdan SONRA. Ayrica bir hesabin kredisi
07:15'te bitti; oturum acilis sirasi kotaya gore secilecek.

# DEVAM (KraL) — 4 Agu 2026

## 🟠 ACIK KALEM (kanca kablolama dali, agent-aabf841a) — bu turda GENISLETILMEDI
`tools/is-akisi-kapisi.py::SERIT_B` tablosu (is_akisi, job, **betik-yolu**) granulunde
anahtarlaniyor. Yani bir betik SERIT_B'de beyanliysa o betigin GELECEKTEKI TUM bayrakli
cagrilari da sessizce muaf sayilir. Bu dalin getirdigi bir gerileme DEGIL — mevcut tasarim;
`kanca-kablolama-test.py`nin `--mutasyon` kolu da bu yuzden ayrica beyan istemeden gecti.
Gelecek is: SERIT_B'yi (is_akisi, job, betik, **bayrak**) granulune tasimak (bu turda kapsam disi).

## 🔚 OTURUM KAPANISI — 4 Agu · YENI OTURUM ONCE BUNU OKU

### ✅ 5 AGU GECE TURU — CANLIYA GIDENLER
- `f6569d7f` kapi agaci sinifi kapandi — ayrinti DEVAM-ARSIV.md de (git disi).
- `c912548f` yayin kilidi (tek urun) · `d3638a5c` DEVAM budamasi — ikisi de kapandi.

**🔴 SIRADAKI TUR — MERGE KUYRUGU (hepsi dal, hicbiri canlida degil):**
1. **marka aramasi -> uyelik yuklemi** (Okan hukmunun ana kaldiraci): `sayfa != arama`
   **79 marka / 6.507 kalem -> 20 marka / 75 kalem (-%98,8)**, kaybolan urun 0. Merge kapisinda.
   🔴 Capa DINAMIKLESTIRILDI: havuz `srch - sayfa`dan DEGIL **veri iliskisinden** kuruluyor —
   arama kumesinden turese kendini dogrulayan capa olurdu, `srch = set(sayfa)` mutanti havuzu
   da bosaltip kapiyi "olculemedi"ye dusururdu. Bos kume -> rc=2 OLCULEMEDI (M14).
2. **`model_kanon` kolonu** (8.727 urun / 549 deger) — 3 commit: `1) kolon · 2) taban · 3) sozluk`.
   🔴 **MODEL EKSENI MARKADAN FARKLI:** kanon hamin UST KUMESI DEGIL — 1.572 jeton / 5.572 kalem
   kolonda hic gecmiyor, yayimlanan etiketlerde bile "ham eslesiyor kanon eslesmiyor" 16 kova /
   276 kalem. **Uc BIRLESIM kullanmali** (HocA'ya yazildi). Sayfa<->uc farki 96 kova/390 kalem -> 0/0.
   🔴 Commit 3 (sozluk) TEK BASINA MERGE EDILEMEZ: sozluk acilinca 7 kaydin `uyum[].model`'i
   yazim varyanti oluyor -> `uyum-kapisi` A1 KIRMIZI + `urun_hash` bayat -> sonraki senkron o 7
   urunun `uyum`unu D1'de `[]` yapar (Ege uyum bilgisini KAYBEDER). MaCiT'in 7 kayitlik
   duzeltmesiyle AYNI merge'de inecek.
3. **`ege-bilgi.md` tavan payi 27 -> 369** (5 tur curutme). Mayin gercekti: eski pay 27 < en ucuz
   filaman kaleminin 52 birimi, **1 kalem bile tasiriyordu** (KaaN/MaCiT'in isini kirardi).
   🔴 Tur-4 dersi: sikistirma iddia DUSURMEDI ama **iddia EKLEDI** — `cozum DAIMA filament olsun`
   mutlak hukmu, belgenin kendi onayli gomme-somun istisnasiyla (metal) celisiyordu; ikisi de her
   prompta gidiyordu. Denetim tek yonluydu (yalniz kaybolani sayiyordu), cift yonlu yapildi.
4. ACIK KALEM: depo hijyeni ve kapi daraltma — dokum DEVAM-ARSIV.md de (git disi).
5. **Yayin hatti:** bu gece deploy **74 dk durdu** (bir commit inline JS ekleyip `varlik-test.py`i
   kirdi) ve **hicbir alarm atesle­medi** — `deploy-aclik-kapisi` esigi 4 ardisik skipped'e ayarli.
   Ayrica parite esigi bayat: pay 3,0x -> **1,33x**, normal kosulda bile "OLCULEMEDI" uretebilir;
   kritik yol `serit-a3` pencerenin **%93'u**. Ucu birden mühendiste.

**BEKLEYEN KUCUK KALEMLER (bende):** `_isi_yuvasi()` cift-onek korumasi (tek satir) ·
"eklenen jeton gerekce tablosu" **calistirilabilir arac degil**, anlati — bir gun kapiya donerse
ilk fiksturu "hukum ekleyip BICIM diye etiketleme" mutanti olsun · `/marka/bmw/motorrad/` hukmu
(model degil marka KOLU, `PSA`/`VAG` sinifi — kapatilacak) + `Mercedes|A/S/V` (TEK HARF ama
GERCEK model, kapatilmayacak, kanonik gosterime baglanacak) · C kovasi 87 urun · duvar-susu
kapisinin yapisal cozumu (cip evreninden MODEL adi ara).

**CI nobeti:** son tur dokumu DEVAM-ARSIV.md de (git disi).

**BEKLIYOR — baskalarinda:**
- **MaCiT** → metin/alan boslugu 1. PARTI (en buyuk 50 model; kaynak liste kararsiz jetonlar
  cikarilmis 6288 kayit / 4513 urun / 817 cift) + EK PARTI (616 urun, **0 yeni sayfa**).
  Parti bitmeden 2. parti acilmiyor. Ayrica hasat aciklama SABLONU kok nedeni.
- **HocA** → (`ara*` rota kalemi KAPANDI: kutuda kapanis notu, main `c01b70e`, deploy `7830b5f2`;
  kalici kapi `rota-yuzey-nobetci.mjs` kuruldu) · **ACIK:** uc `model` parametresini
  `uyum[].model`'de TAM eslesmeyle suzuyor; 467 cipin 210'unda cip ile ucun teslimi ayrisiyor
  (965 urun-kalemi). Musteriye sayi gosterilmiyor; ucun katlamayi almasi karari onda.
- **KaaN** → `rulman` semasi onarilinca satisa acma karari bende · **ArTisT** → marka-model
  sayfa esigi onerisi.

**OKAN'DA KARAR YOK.** Bugun sorulan uc karar verildi ve uygulandi: asamali git (1. parti 50
model) · Zafira sayfasi 28 hedefi, `Zafira Life` ayri bolumde · yayin hattini KraL acsin.

ACIK KALEM: onceki tur kuyrugu — dokum DEVAM-ARSIV.md de (git disi).

### 🟡 ACIK KALEM 1 — kuyruk geri tepmesi OLCULEMEDI (48 saat sonra yeniden olculecek)
ACIK: ayrinti DEVAM-ARSIV.md de (git disi).

### 🟡 ACIK KALEM — korumanin tasinabilirligi (uc kalem)
(a) Koruma her ortamda ayni sekilde durdurmuyor (durum DEGISMEDI); ayrinti
DEVAM-ARSIV.md de (git disi). Ilgili dosya depoya girmedigi icin dal icinden
kapatilamaz — ayri tur gerekiyor.
(b) Kapi `pre-commit`/`pre-push` icinden cagrildiginda git kendi kancalarini
`GIT_DIR`/`GIT_INDEX_FILE` TANIMLI olarak kosar; yani (a) kapandiginda ortam kirliligi
GERCEK bir yol olur — bu tur tam o yolu kapatti, kayda gecsin.
(c) KAPANDI — ic isci-rapor protokol adina yapilan atiflarin hijyeni: asagidaki
"public depo hijyeni" kalemine bak (merge 20fbff61).

## 🔴 YENI ACIK KALEM — A0 DAMGA alarmi kirmizi: D1 uzlastirici cron'u TESLIM ETMIYOR
ACIK: ayrinti DEVAM-ARSIV.md de (git disi).

## 🔴 YENI ACIK KALEM — katalog geneli metin/alan bosluğu (envanter cikti)
ACIK: ayrinti DEVAM-ARSIV.md de (git disi).

ACIK KALEM: yayin hatti icerik denetimi — dokum DEVAM-ARSIV.md de (git disi).

## 🟡 YENI ACIK KALEM — `CLAUDE.md`/`AGENTS.md` git disi symlink
ACIK KALEM: symlink surumleme ayrintisi — dokum DEVAM-ARSIV.md de (git disi).
