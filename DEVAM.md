# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 16 Agu (~00:xxZ) — UCUZ KAT YENIDEN KURULDU: CODEX + DEEPSEEK EMEKLI, KIMI BIRINCIL (KraL)

**Okan karari, olcumle kapatildi.** Yeni hat: `isci.sh` → **kimi BIRINCIL · minimax-m3 YEDEK**;
DS ve Codex'e yeni is YOLLANMAZ (abonelik iptali Okan kapisi).

**Kanit — `tools/yetkinlik/` bataryasi** (6 sinif, hukum deterministik dogrulayicida; commit
`54e9f4c7`). Iki kosum (1 tekrar + 3 tekrar), cevap verilen turda dogruluk:
**kimi 18/18 · m3 21/22 · codex 14/15 (+1 yalan)**.
- kimi'nin ham skorunu dusuren 6 tur **yetenek degil uc hatasi**: `motor_rc=1`, 2,3-4,3 sn,
  ardisik alti tur; yeniden kosumda ayni tur **6/6**. → `isci.sh`'e **kisa-surede-rc≠0 →
  1 kez otomatik tekrar** korumasi kondu.
- **m3'un olculmus zafiyeti: uzun baglam / cagri grafi** (g5'te UYDURMA satir verdi). O sinif
  kimi'ye ya da capraz dogrulamaya.
- Batarya **kendisi 3 kez yanildi** (`ONERI=` satiri kabul satirini golgeledi · yol oneki ·
  kirilim sirasi) — ucunde de once "motor kaldi" gorundu. Olcer `mutasyon.py` ile kanitlanir
  (12 mutasyon, SURVIVOR=0; `dogrula-test.py` 21 vaka).

**Tarayici tekeli kirildi.** Isci playwright ile **giris yapilmis panele giriyor**
(`PANEL=ACIK`, Cloudflare). Iki mod: etiket `tarayici*` → HEADLESS (pencere yok, izole),
`panel*` → HEADFUL + kalici profil. macOS ekran-disi konumu EZIYOR (pencere `(0,31)`'e
cekiliyor), headless ise panelde bot dogrulamasina takiliyor → panel turunda pencere
kacinilmaz, o yuzden **panel isi ONCE API**: yeni `tools/cf-durum.py` (salt okuma)
D1/R2/Pages'i tarayicisiz veriyor.

**ACIK KALEM (Okan):** cf-durum DNS kapsami icin salt-okuma CF jetonu lazim — ayrinti
DEVAM-ARSIV.md'de (git disi).

## 16 Agu (~01:xxZ) — OTURUM KAPANISI (KraL): IC LINK HATTI CANLIDA, YAYIN IKI KEZ KAPANDI-ACILDI

**CANLIYA GIDEN:** `ca699eec` ID ASCII katlama · `4380e7c8` ic link hatti (rel-card halkasi +
marka/kategori hub sayfalama) · `13108010`+`843cce5a` varlik CIKARIM BEYANI + CI baglantisi ·
`93c420c8` kart ozeti IKIZ TANIMI. Canli katalog **28344 = D1 = urunler.json** (dort eksen yesil).

🔴 **YAYIN BUGUN IKI KEZ KAPANDI, IKISI DE KOK NEDENLE ACILDI:**
1. **Bozuk ID (~6,5 saat):** 51 urun ID'sinde Turkce karakter; ID kanonik adres oldugu icin
   fiyat prova/tahsilat esitligi null donuyordu. ASCII katlama + D1 seq kilidi (normalize'i
   ESKI kaynakla kostur) ile acildi. Ayrinti DEVAM-ARSIV.md.
2. **Ikiz tanim:** bir urun `gorseller: []` ile eklenmisti; `build.py` (Python) bos diziyi
   falsy sayip `gorsel:null`, `vitrin-kabul.js` (JS) truthy sayip `undefined` uretiyordu —
   `JSON.stringify` alani dusuruyor, iki kart ayrisiyor. JS kanonik tarafa (build.py)
   hizalandi + `kart-ikiz-test.js` (7 sinir vakasi, mutantli). Veri tarafini MaCiT kapatti.

**IC LINK (K115 KAPANDI — Okan'in 2. konusu):** olculen kusur, rel-card kategorinin ILK 8'ini
aliyordu ve havuz sirasi urune bagli DEGILDI → tum kategori ayni 8 urune link veriyordu
(canli kanit: 5 Otomobil sayfasi, kesisim 8/8). **Link ALAN benzersiz urun 126 → 27.957,
YETIM 27.954 → 123**, dagilim min1/ortanca8/maks34. Ayrica marka hub sayfalama
(`/marka/<slug>/sayfa/<N>/`, 312 ek sayfa) + statik kategori hub'lari (358 sayfa) +
urun breadcrumb'i artik sorgu adresine degil statik hub'a bagli.
🔴 **Bagimsiz curutme bir CAKISMA yakaladi:** ilk sema `/marka/<slug>/<N>/` idi ve sayisal
model slug'lariyla carpisiyordu — `/marka/mazda/2/` zaten **Mazda 2 modeli** (ayrica 3/5/6,
Renault 5). Sayfalama ayri isim alanina (`/sayfa/<N>/`) tasindi, sayisal modelli marka
fiksturu eklendi, eski sema mutantla KIRMIZI yaniyor.

**CF PURGE (BaBa odevi):** arac hazir (`tools/r2-purge.py`, dal `onarim/r2-purge` `9f7aaf77`),
canli `success:true`. Iki curutme turu iki kusur buldu (hata kollarinda gizlilik olcumu yalniz
mutlu yoldaydi; `--anahtar` kara listesini bos dize atlatip medya KOK adresini hedefliyordu) —
ikisi de kapandi, kara liste BEYAZ listeye cevrildi. Kabul VAKA=34 DUSEN=0.

**VARLIK KAPISI — CIKARIM BEYANI (yeni sinif kapisi):** kasitli sayfa degisikligi kapiyi
kilitliyordu (kirmiziyken tazelenmiyor, tazelenmeden kirmizi gecmiyor). Kapiya zorla-gec kolu
KONMADI; yedek-dusus-beyani deseni kuruldu: kapsam KAPALI kume, blanket beyan RED, tek bulgu kapsam
disiysa RED, gecen her bulgu adiyla BASILIR. **Beyan edilse bile gecmeyen alanlar:** urunun
kendi gorseli · canonical · siparis/WhatsApp baglantisi · baslik · fiyat. Kabul 8/8, 2 mutant.

**SINIF KAPISI (3. tekrar kurali):** bugun UC is "test yesil" deyip push'ta
`CI KAPSAM KAPISI KIRMIZI` ile durdu — kapi dogruydu, eksik olan SPEC'ti. `codex-isci`
skill'ine madde eklendi: yeni nobetci uretten spec, ayni spec'te CI baglamayi ve
`CI_KAPSAM_RC=<n>` kabul satirini ISTER; `IZIN_LISTESI` muafiyeti YASAK. Serit secimi
turnusolu: kirmizisi para/veri/site'yi vurmuyorsa **hijyen** (`nobet.yml` SERIT B).

**NAVLUNGO (Okan, yeni is):** yurt ici kargo API'si `/api/shop/yonet` hattina baglanacak,
siparisler otomatik gonderi bilgisine donusecek. Kargo ucret politikasi **DEGISMIYOR** (Okan),
desi'yi **Okan girer** (kutuyu o seciyor), alici PII'sinin kargo firmasina gitmesi Okan
karariyla SORUN DEGIL. Olculdu: 8 tasiyici · fiyat-oncesi sorgu YOK · webhook VAR (11 olay) ·
token 8 saat · QA+canli ortam ayri. 🔴 **Gercek engel il/ilce:** Navlungo `city`+`district`
ZORUNLU, bizde ikisi de ayri tutulmuyor (form sehri topluyor ama adrese yapistiriyor, ilce hic
yok; 11 kayitta `" / "` ile geri ayristirma 0/11 tuttu). **Dilim-1 HAZIR ama MERGE EDILMEDI:**
dal `il-ilce-dilim1` (`5d57c918`) — il+ilce ayri kolon+form+INSERT, VAKA=8 DUSEN=0, kardes
kapilar (siparisler/maske/odeme/fiyat-parite) ve ci-kapsam rc=0. Kimlik kabi hazir ve Okan'a
acildi: `~/.claude/cron/.navlungo-kimlik.json` (repo DISI, izin 600, degeri Claude okumaz).

## ACIK KALEMLER (kaynak-dogrusu: `acik-kalemler.md`)

- 🔴🔴 **K117 (OKAN EMRI, 16 Agu — SIRADAKI IS, baska ise BASLAMA):** **model filtresi
  calismiyor + model kapsami eksik.** `/marka/toyota/`: 2101 parca, "Modele gore secin (72)"
  ama cip sayilari 2101'e BOLUNMUYOR — cok sayida parca hicbir modele atanmamis, "neredeyse
  tum markalar icin gecerli" (Okan). Ayrica **model linkine basinca filtre CALISMIYOR**.
  Ekran goruntusundeki kanonikleştirme kusuru: ayni arac parcali etiketlerde
  (`MR2`/`MR2 SW20`/`SW20`/`MR2 Spyder` · `Land Cruiser`/`Prado`/`Land Cruiser Prado`/
  `Land Cruiser 200`/`FJ40`/`Land Cruiser FJ40` · `86`/`GT86`/`GR86`/`AE86` ·
  `Avensis`/`T25`/`T27`) ve **model OLMAYAN etiketler** listede (`TRD`, `TRD Pro`, `22RE`,
  `4AGE`, `Scan Gauge`, `107`).
  🔬 **TESHIS KOSULDU (16 Agu, canli tiklamayla) — iki AYRI ariza:**
  **(A) Filtre kodu calisiyor, VERI eksik.** Cip tiklamasi sayaci ve artim kartlari
  guncelliyor, konsol hatasi 0. Ama **ilk 80 SSR karti `data-mm` TASIMIYOR** (olculdu: 0/80
  kart, 0/404 liste ogesi) → `marka_model_build.py:1989` `uyeli = ham ? ... : false` yolu
  tasimayanlari "model disi" sayip **hep gorunur birakiyor**; Corolla secilince baslik
  "(0)" diyor ama UL hala 404 oge tutuyor. Kullaniciya "filtre calismiyor" olarak gorunen
  sey bu. **Onarim: SSR kart ureticisi model uyeligini karta yazmali** (JS tarafi degil).
  **(B) Model kapsami + kanoniklestirme.** Toyota 2109 urun · **modelli 1460 · MODELSIZ 649** ·
  72 cip toplami 1933 → **fark 176**. Kapsama orani marka basina: **honda %81,0 · bmw %82,2 ·
  toyota %91,7 · ford %95,8** — sinif marka-genel, Toyota'ya ozgu DEGIL. Kanoniklestirme
  kusuru olculdu: **4 arac 18 ayri etiket** (MR2 4 etiket/206 parca · Land Cruiser 7/140 ·
  86 ailesi 4/92 · Avensis 3/63). Model OLMAYAN etiketlerin hepsinin sayfasi var
  (`trd` 3 · `trd-pro` 3 · `22re` 6 · `4age` 4 · `scan-gauge` 3 · **`107` 4 — Peugeot
  modeli, Toyota kapsamina siziyor**). Hukum: `model_kanon` kurallari hem alt-kumeleri
  tekillestirmiyor hem marka-disi/model-olmayan jetonlari elemiyor.
  **Yeni oturum bu iki eksenle acilir: (A) kod, (B) kanon kurali.**
- 🟠 **Navlungo dilim-1 MERGE BEKLIYOR:** dal `il-ilce-dilim1` (`5d57c918`). Sonraki dilimler:
  telefon bicimi (`+90 5xx xxx xx xx`), Navlungo istemcisi (8 saat token onbellegi),
  yonetim ekraninda "Kargoya ver" (alanlar dolu, desi Okan'dan), webhook alicisi.
  **Okan kapisi:** `.navlungo-kimlik.json` doldurulmasi.

- 🔴 **K113 (YENI, 16 Agu)** — `Uretici butunluk kapisi` YANLIS SERITTE: `hijyen-build`'de, oysa URL-guvensiz ID kanonik adresi bozar = BLOKLAYICI olmali. Bugun tam bu yuzden bozuk ID'yi yakaladi ama yayini durdurmadi. `deploy.yml`'e yazmayi gerektirir; **peer'in commit'siz isi bekleniyor**.
- 🔴 **K114 (YENI, 16 Agu)** — `onarim/r2-purge` dali (`9f7aaf77`, worktree `/private/tmp/pruvo-purge`) MERGE BEKLIYOR: tek engel `ci-kapsam-test.py` rc=1 (`tools/r2-purge-test.py` CI kapsaminda degil). K113 ile AYNI dosyaya yazilacak, ayni turda kapanmali.
- ✅ **K115 KAPANDI (16 Agu)** — ic link hatti canlida (yukaridaki blok). Sayilar orada.
- 🟠 **K116** — `kimi` isci motoru **KOTA DOLDU** (403). Tarayicili is m3'te. Ayrica MaCiT
  bildirdi: `isci.sh`/kapi kapali kumesi hala `kimi`yi TANIMIYOR (skill "kimi birincil" diyor,
  makine listesi guncellenmemis) — **arac kusuru, bende.**
- 🔴 **K104** — nobet is akisi 200 kosumda 11 success / 77 failure / 110 cancelled; son yesil
  12 Agu. Teshis var, HUKUM MIMARDA. · **K104B** — iki kapi main'de de KIRMIZI (mutasyon
  capalari M06/M31 + 2 kapinin kanca kablosu envanterde yok); tabanda olculdu.
- **K99** bag kolonu spec'i · **K100** defter sinifinda satir-sonu muafiyet kusuru ·
  **K102** nobet yazicisi kok deftere yasakli ic dosya adi uretiyor.
- 🔧 **Iki acik kapi kalemi (gate kodu = Claude kati):** (a) shop bayatlik alarminin TETIK
  ekseni raporladigi bundle evreniyle AYNI DEGIL (25 tur kirmizi, delta 0 dosya);
  (b) `devam-sinif-kapisi.py` is-akisi muafiyeti `norm`/`ham` ekseninde ayrisiyor.
- **Kapanmis kalemlerin tam metni** (K108 curutmesi · yedek dusus beyani · defter sismesi H8 ·
  serit-a2 B3/FAZ3 · 12:11Z nobet turu) **DEVAM-ARSIV.md**'de.
- KAPANDI: K91 · K101 · K103 (kanitlar arsivde).

## VERI OLAYI (kapandi — tam metin arsivde)

Gizli kaynak kaydi 0 bayta dustu, yedekten atomik geri yuklendi. **261 urunun kaynak kaydi KAYIP** (65'i katalogda lisans tasiyor, site atfi SAGLAM). Dort kurtarma yolu kapali; dolgu MaCiT'te, once ticari sinif.

## OKAN'DA

- Motor tarifesi satin alma karari · eski yedek klasorunu backup-v2 icine tasima · K89 olcum eylemi silme karari.
- 🔧 **TARIFE KARAR KURALI (olculdu, onaya hazir):** mevcut $20 plan KALIR. Haftalik kota %80'e yaklasirsa ikinci saglayicinin $39 basamagi TERCIH EDILIR — ayni para bandinda hem kota hem **ikinci saglayici** (429/kesinti/kota duvarinda yedek) verir; mevcut saglayicinin $50 basamagi yalniz kota verir, tek-saglayici riski surer. Ikinci saglayici bekleme listesindeyse tek uygulanabilir yol $50 (0 kod degisikligi). Ust basamagin iki "deneysel" ozelligi bizim hatta GIRMEZ — biz yalnizca Anthropic-uyumlu API ucundan MODEL cagiriyoruz. Kota sayilari iki adayda da yayimlanmiyor, yani secimi fiyat degil CESITLILIK belirliyor. Ekleme bedeli motor basina 6 kod noktasi.
- Olculen maliyet tabani: $18,72 / 1.081.021.287 token / 8.639 istek = yaklasik $17,3/milyar; $20/ay ve yaklasik 4,6 milyar/ay = yaklasik $4,3/milyar.

## KOSUYOR (baska mimarlar)

MaCiT — Ducati d1 sub-slice 2/3 ve 3/3 (taban artik 27420) + 261 kaynak kaydi dolgusu.

## ARSIVDE (tam metinler `DEVAM-ARSIV.md`'de)

14-15 Agu saatlik CI nobeti turlari · 15 Agu gece oturum kapanisi · K101/K103 kapanislari · yayin ve odeme etiketi bloklari · dorduncu motorun hatta baglanmasi · HD/Kawasaki/Ducati ekleme bloklari · sabah oturumunun tam olcum blogu · defterin sikistirma oncesi 196 satirlik tam hali.
