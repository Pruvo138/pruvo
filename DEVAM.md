# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 16 Agu (~15:00Z) — K123 KAPANDI: YAYIN-YASI NOBETCISI CANLIDA + MUKERRER ISTISNASI WORKTREE'DE (KraL)

**Merge `cadf9acb`** (origin/main'de; dal `kral/k123-yayin-yasi` + worktree SILINDI).
D1 teyidi **5/5 eksen YESIL** (28682 = 28682).

**(A) YAYIN-YASI NOBETCISI** (`tools/yayin-yasi-nobetcisi.py` + `.github/workflows/yayin-yasi-alarmi.yml`).
15 Agu 14:02 - 16 Agu ~12:00 arasi yayin ~21 saat kapaliydi; o pencerede yayin YASI hicbir
yerde OLCULMUYORDU (mekanik ayrinti DEVAM-ARSIV.md'de).
- Olculen buyukluk **"son dagitimin yasi" DEGIL, "yayina girmemis EN ESKI commit'in yasi"**
  (tavan **3 sa**): sakin gecede main ilerlemedigi icin alarm otmez; main ilerleyip canli
  kalinca saat isler. Commit SAYISI hukum vermez (Pages ara kosumlari iptal eder), raporlanir.
- Hukum kosum `conclusion`'ina DEGIL `github-pages` ortamina dusen **gercek dagitim kaydina**
  bakar. Fail-closed: jeton/kayit yok · dagitilan SHA main gecmisinde degil · tarih okunamadi
  · negatif yas hepsi **rc 2** (sessiz yesil YOK).
- 🔴 **Mevcut nobetciler bu sinifi YAPISAL olarak gormuyordu:** `yayin-erisim` kumeyi main
  agacindan turetip canli sitemap'te olmayan 404'leri ROLLOUT sayiyor — yani yayin tamamen
  durunca **tam olarak sessizlesiyor**; `yayin-gecikme` ise D1 taslak yigini olcuyor.
- AYRI SERIT: `push`/`pull_request`/`workflow_call` tetigi yok, `deploy.yml`'e `needs` ile
  bagli degil, `concurrency` ayri → yayin yoluna maliyeti 0 sn. Cron **41** (yogun dakika
  degil; 26 · 9,24,39,54 · 13,28,43,58 fazlarina carpmaz).
- Olcum: **KABUL 23/23 · MUTASYON 9/9 OLDU · SURVIVOR=0 · UYGULANMADI=0** · CI_KAPSAM_RC=0
  (taban 0) · canli `workflow_dispatch` kosumu **rc=0**: *"12 commit yayin sirasinda; en
  eskisi 1 sa 57 dk bekliyor — tavan 3.0 sa · son basarili dagitim 2 sa 04 dk once."*

**(B) 🔴 SINIF ONARIMI — mukerrer istisnasi worktree'de de gorulur.** `.mukerrer-istisna.json`
`.gitignore`da ve `git worktree add` **izlenmeyen dosyayi tasimiyor** → AYNI HEAD icin ana
agacta `rc=0`, worktree'de `rc=1` olcuuldu; **urun verisine hic dokunmayan** commit'ler bile
"MUKERRER KAYNAK" ile bloklandi. Bedeli kayitli: iki kanca atlamasi + `k119e` worktree'sinin
temizlenememesi. Ucuncu tekrar oldugu icin tekil yama YAPILMADI: `istisna_yolu()` yereli
bulamazsa `git rev-parse --git-common-dir` ile **paylasilan ana agactan** okur ve hangi yolu
kullandigini basar. **Kapi gevsetilmedi** — dosya hicbir agacta yoksa davranis eskisinin
aynisi; paylasilan dosyanin VARLIGI degil ICERIGI hukum verir.
Kabul `tools/mukerrer-kapsam-test.py` 5 → **8 iddia** (A6 worktree istisnayi gorur · A7 istisna
hicbir agacta yoksa KIRMIZI · A8 varlik degil icerik). **ESKI kapiyla A6 KALDI** (regresyon
kanitli), taban 5/5 yesil.

**Olcuulen yan bulgular:**
- `cron-nabiz-kapisi.py` **A2 ekseninin "henuz main'de olmayan yeni is akisi" kolu YOK**
  (`A2_MUAFIYET=YOK`, `tools/cron-nabiz-kapisi.py:1233`): yeni cron dosyasi dalda KIRMIZI
  yakar, main'e girip GitHub kaydettikten sonra kendiliginden yesile doner. SERIT B, yayini
  BLOKLAMAZ — kalem ACILMADI, sonraki cron ekleyen icin not.
- Push aninda **K85 D1 yazici lease'i** (baska evin ucusu) bir kez durdurdu; sira, ariza degil.
  Ikinci denemede D1 senkron gecti, push `refs/heads/main +4`.

## 16 Agu — OTURUM KAPANISI (KraL) — CANLIYA GIDEN · KOSUYOR · BEKLIYOR · OKAN'DA

**CANLIYA GIDEN (main push'lu, ana repo temiz):**
- `7a695700` K117 merge — kapsam × model filtresi tek yuklem + kanon deny/kusak + eksik
  modeller (dal `kral/k117b-model-kanon` merge edildi, **worktree+dal SILINDI**).
- `62386a64` gizli kayitta notrlenmemis alanlar temizlendi · `96e89833` varlik cikarim
  beyani (6 urun) · `d17e7ebd` beyan tamamlandi (30 urun) → **deploy=success**, yayin ACILDI.
- `935f6695` + `4e7f3602` defter.
- D1: `model_kanon` bayat 44→0 ve 25→0; taslak yigini **496→55**, yayin gecikmesi **441→0**
  (`--geriye-doldur`, 5/5 eksen YESIL, degismez ihlali 0).
- Canli dogrulama (onbellek kirma YOK): Corolla cipi **184/184, TRD cipi 0**;
  `trd`/`22re`/`107` **404**, `mr2`/`lexus/gs` **200**.
- Repo DISI: mail supurucusu v2 (kimlik tabanli) — kabul 8/8, SURVIVOR=0, elle kosum
  43 silindi **komsu kaybi 0**, crontab `21,51` ACILDI (5→6 aktif satir, kayip satir 0).

**KOSUYOR:** KraL tarafinda kosan is YOK; delege turlarinin hepsi kabul satiriyla kapandi.
(MaCiT parti-surucusu kendi cron'unda devam ediyor — ayri ev.)

**BEKLIYOR (kim/neyle bloke):**
- 8 Vespa + 7 model sayfasi **404** → bir sonraki `deploy` kosumunu bekliyor
  (`BEKLIYOR=deploy`); urunler son yayina giren derlemede yoktu. Kod tarafi HAZIR.
- `.claude/worktrees/k119e` (dal `fix/k119e`) **TEMIZLENEMEDI**: icinde staged
  `varlik-cikarim-beyani.json` taslagi var, commit mukerrer kancasinda takiliyor —
  worktree gitignore'lu istisna dosyasini TASIMIYOR (bilinen sinif). Atlama anahtari
  KULLANILMADI. Icerik ayrica `stash@{0}`'da. Sahibi/onarim turu cozecek.
- `kurtarma/k122-yabanci-is` dali **DURUYOR** — peer'in dusurulen commit'siz isi
  (deploy.yml K113 · marka-uyelik-test.py K109 · kalibrasyon 4 dosya). Sahibi uygulayacak;
  **`git gc` kosturulmayacak.**
- Ana agacta yabanci ` M tools/marka-uyelik-test.py` — DOKUNULMADI.

**OKAN'DA BEKLEYEN KARARLAR:**
- **K120** gizli kaynak kaydinin git'ten cikarilmasi — karar VERILDI, uygulama bekliyor;
  kapilarin yokluk kolu olculmeden kapanmaz (sessiz delik riski).
- Navlungo kimlik dosyasinin doldurulmasi + dilim-1 merge (`il-ilce-dilim1`).
- Motor tarifesi satin alma karari (tarife kural blogu asagida).

## 16 Agu (~13:xxZ) — K117 KAPANDI + YAYIN 21 SAAT SONRA ACILDI + TASLAK YIGINI COZULDU (KraL)

**K117 (Okan emri) CANLIDA DOGRULANDI.** Okan'in ekran goruntusundeki vaka:
`/marka/toyota/?kategori=Otomobil` + Corolla cipi → **gorunur kart 184 · sayac 184 ·
TRD cipi 0** (onbellek kirma sorgusu YOK). Kanon: `trd`/`22re`/`107` **404**,
`mr2`/`lexus/gs` **200**.
- **(A)** Kok neden: kapsam modulu (`?kategori=`) model filtresini eziyordu — `uygula()`
  her karta `style.display`'i YALNIZ kapsama gore yaziyor, `data-mm`'den habersizdi;
  filtre bitince `sayilariTazele()` onu cagirdigi icin ~1 sn sonra tum katalog geri
  geliyordu. Kapsam yokken erken cikis oldugu icin parametresiz olcumler TEMIZ cikiyordu
  (bu yuzden ilk uc olcum turu kusuru GORMEDI). Cozum: gorunurluk + sayac TEK kanonik
  yuklemden (kapsam ∧ model); sayac sahipligi tekillesti. Kabul **6/6**, **SURVIVOR=0**.
- **(B)** 6 model-olmayan jeton deny + 10 kusak eslemesi (MR2/Land Cruiser/Avensis) +
  AE86 kusak-disi. KAPANAN_SAYFA=6, **KAYBOLAN_URUN=0**.
- **(C)** 17 gercek model listeye alindi (15'i sayfa aciyor; Hyundai Genesis yabanci-marka
  damgasi, Peugeot 203 esik alti). 250 elenen kovanin 225'i DOGRU eleniyor (167'si baska
  markanin ADI). **ESIK=3 KALDI (Okan karari).**
- Merge `7a695700` (4 dosya, +343/−23), parite 1328+893 BIREBIR, D1 `model_kanon` 44→0.

🔴 **YAYIN 15 AGU 14:02'DEN BERI KAPALIYMIS** (son basarili deploy `268da994`, uzerine
22 commit). Kimse fark etmemis: `deploy` job'i `needs`'ten dusunce **SKIPPED** oluyor,
bu sessiz bir sonuc. Uc engel sirayla kaldirildi (`62386a64` → `96e89833` → D1 sirasi →
`d17e7ebd`), **deploy=success**.
🔴 **TASLAK YIGINI:** `yayin` job'i (deploy SONRASI, yayini durdurmaz) `441 > 300` tavani
yuzunden kirmiziydi. Aracin kendi `--geriye-doldur` kolu ile **496 → 55**, yayin gecikmesi
**441 → 0**, degismez ihlali 0, d1-sync 5/5 eksen YESIL, gerileme YOK. Kalan 55 canli
JSON'da olmayan satirlar (aracin kendi suzgeci). 8 Vespa + 7 model sayfasi bir sonraki
deploy kosumunu bekliyor (`BEKLIYOR=deploy`).

🔬 **BU OTURUMUN DERSLERI (uc kez ayni sinif):**
1. **Isci oz-raporu kanit degil — UC KEZ curudu.** (a) K117-C "14 kovada kova YOK,
   YENI_SAYFA=1" dedi, bagimsiz olcum 17/17 kova + 15 sayfa buldu. (b) K121 "SURVIVOR=16"
   bastu, gercek survivor 0'di (etiket yanlisti). (c) K119-E spec'imi "uygulanamaz" diye
   reddetti ve **hakliydi** — benim talimatim yanlisti, reddetmeseydi 6 saglam urun
   silinecekti. **Ders: hem yesili hem kirmiziyi bagimsiz olc.**
2. **Yazili yasak yetmiyor.** Iki tur spec'teki ACIK yasagi cignedi (biri kancayi atladi,
   biri `stash` kullanip baska oturumun commit'siz isini DUSURDU). Kurtarildi:
   dal `kurtarma/k122-yabanci-is` (646 unreachable commit tarandi). Yasak kancaya
   baglanmali — kalem.
3. **Tekrar eden kapi = sinif kusuru.** `varlik-test` her urun partisinde kirmizi yaniyor
   (olculdu: yesil → iki parti → yine kirmizi, 6/6 yeni urunden). Kalici cozum
   `--referans-tazele` (kosul SAGLANIYOR: kapi yesilken tazelenir, sonra 4380e7c8 beyani
   GEREKSIZ olur) — yapilmadi, kalem.

## 16 Agu (~09:xxZ) — UCUZ KAT KOTA YANMASI OLCULDU: MODEL KATMANI + BAGLAM BUTCESI (KraL)

**Soru (Okan): "kimi kotasi cok cabuk doluyor, code modunda kullandigimiz icin mi?"**
Olculdu — hayir, uc secimi degil. Iki sebep:
1. **Model:** kimi hatti amiral gemisi `k3` ile kosuyordu (824/830 tur). Red metni
   `403 usage limit for this billing cycle` → aylik kredi ~2 gunde bitti.
2. **Baglam:** her tur tum konusmayi yeniden faturalar. kimi 830 turda **54,6M** girdi
   token; ozgun icerik (tum arac ciktilari) ~290k token → **~180x tekrar**. m3 evinde ayni
   desen: 174 oturum / **1,26 milyar** girdi token.

**Tur sayisi maliyetin KARESI:** m3 evinde >60 turluk 111 oturum toplam yanmanin **%88,7**'si;
<=40 turluk 33 oturum yalnizca %3,2. En pahali tek oturum 355 tur / 57,8M — 40'lik dilimlere
bolunseydi ~16M (**%72 tasarruf**; taban tekrar odenir, rampa 9 kat kuculur).

**YAPILAN (ikisi de kabul testiyle kapandi, 8/8):**
- `isci.sh` kimi motoru **katmanlandi**: varsayilan `kimi-for-coding` (K2.7), `k3` yalniz
  `tarayici*`/`panel*` turlarinda, `PRUVO_KIMI_MODEL` ile acik ezme (kapali kume, bilinmeyen
  deger `exit 2`). Test: `~/.claude/cron/isci-kimi-model-test.py`.
- `BASLANGIC` log satiri artik `model=` tasiyor; tur sonunda `OLCUM ... TUR= TOPLAM_GIRDI=
  TEPE= CIKTI=` satiri + `~/.claude/cron/baglam-olcum.tsv` trend dosyasi (olcum turun
  cikis kodunu DEGISTIRMEZ; ayrinti hafizada).
- Isci ORTAK baglamina **baglam butcesi kurali**: tur butcesi ~40 (dolunca DILIM birak,
  idempotent) · bagimsiz komutlari tek turda birlestir · ciktiyi kaynakta darat.

**KUSUR BULUNDU VE KAPANDI:** ilk canli olcum kendi kusurunu gosterdi — 6 turluk kosum
`TUR=46 TOPLAM_GIRDI=2.185.553` yazildi (isci profilleri (motor, ev) basina PAYLASILIR;
es zamanli komsu oturum mtime penceresine girdi). Onarim: her `claude` cagrisi artik
`--session-id <uuid>` ile kosuyor, olcum YALNIZ o UUID dosyasini okuyor (mtime mantigi
kalkti; kisa-tur TEKRAR akisi ikinci UUID alir, degerler toplanir). Kabul **12/12**.
Canli teyit 09:19Z: `TUR=6 TOPLAM_GIRDI=204.542 TEPE=35.189` — bagimsiz `jq` ile ayni
oturum dosyasindan birebir dogrulandi. ⚠️ TSV'de **09:18Z oncesi satirlar onarim oncesidir,
kanit sayilmaz**; yanlis 09:04Z satiri silindi.
→ hafiza: `kimi-kota-amiral-gemisi-yakar` · `paylasilan-profilde-eszamanli-oturum-olcumu-kirletir`

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

- ✅ **K117 KAPANDI (16 Agu) — main `7a695700`, CI SUCCESS, D1 tazelendi.** Uc eksen de
  canliya gitti; ayrinti asagidaki teshis blogunda. Kapanis sayilari:
  merge 4 dosya (+343/−23) · parite 1328 + 893 BIREBIR · D1 `model_kanon` BAYAT 44 → **0**
  (5 turetilmis kolon yesil, 47/47) · turnusol `Toyota+TRD` KAPALI, `Vespa+PX` ACIK ·
  worktree+dal silindi. **(A)** kapsam × model tek yuklem, kabul 6/6 + **SURVIVOR=0** ·
  **(B)** 6 deny + 10 kusak eslemesi, KAPANAN_SAYFA=6 KAYBOLAN_URUN=0 · **(C)** 17 allow
  girdisi, bagimsiz olcum **17/17 kova var, 17/17 eslesti, 15 sayfa aciliyor** (Hyundai
  Genesis yabanci-marka damgasi, Peugeot 203 esik alti). **ESIK=3 KALDI (Okan karari).**
  🔴 **ISCI RAPORU CURUTULDU:** K117-C iscisi "14 kovada kova YOK, YENI_SAYFA=1" dedi;
  bagimsiz olcum yanlisladi (15 sayfa). Oz-rapor kanit degildir — ders tekrar dogrulandi.
- 🔴🔴 **K117 TESHIS ARSIVI (kapali):** **model filtresi
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
  🔬 **16 Agu OTURUMU — UC EKSEN OLCULDU, ONARIM DALI `kral/k117b-model-kanon`:**
  **(A) KOK NEDEN BULUNDU — kapsam modulu model filtresini EZIYOR.** `?kategori=` ACIKKEN
  cipe basilinca filtre uygulaniyor, ~1 sn sonra tum katalog geri geliyor (canli:
  Toyota/Corolla secili, ekran "2101 parca"). `marka_model_build.py:1855` filtre bitince
  `sayilariTazele()` → `PRUVO_KAPSAM.uygula()`; `:1539` her `.card[data-kat]` icin
  `style.display`'i YALNIZ kapsama gore yeniden yaziyor, `data-mm`'den habersiz.
  Kapsam yokken `uygula()` erken cikiyor → kusur yalniz `?kategori=` kolunda gorunur
  (bu yuzden parametresiz olcumler temiz cikti). **Marka-genel, tek kod yolu, 358 sayfa.**
  Hukum: gorunurluk + sayaclar TEK kanonik yuklemden (kapsam ∧ model) turer; sayac sahipligi
  tekillesir. SPEC yazildi, isci kosuyor.
  **(B) KAPANDI — commit `1a567143` (dalda, push YOK).** `MODEL_OLMAYAN_CIFT` 29→35
  (TRD · TRD Pro · 22RE · 4AGE · Scan Gauge · 107=Peugeot modeli) · `KUSAK_ESLEME` 9→19
  (SW20/MR2 SW20/MR2 Spyder→MR2 · Prado/LC Prado/LC 200/FJ40/LC FJ40→Land Cruiser ·
  T25/T27→Avensis) · `KUSAK_DISI_JETON` 1→2 (AE86 farkli arac) · `BASLIK_DOGAN_ALLOW`
  141→140. 5 kapi rc=0, **KAPANAN_SAYFA=6, KAYBOLAN_URUN=0.** 86/GT86/GR86 birlestirmesi
  AYRI hukme birakildi.
  **(C) YENI EKSEN (Okan, "Aristo listede yok") — 275 KOVA / 63 MARKA / 636 URUN listeye
  hic girmiyor.** 🔴 Aristo'nun sebebi yargi kolu DEGIL (`SAHIP=E`), **ESIK**: Toyota'nin
  Aristo kovasi 2 urun (esik 3); basliktaki 4 urunun 2'si Lexus uyesi sayiliyor.
  Elenen kume KARISIK — gercek model (Vespa PX 20 · Ciao 23 · Smallframe 10 · VW/Seat
  Citigo · Opel Rifter/Partner · Peugeot Combo/Jumpy · Chevrolet Ampera · Seat Sharan) ile
  cop (Vespa|Piaggio 258 marka adi · `Sierra` tedarikci 4 markada 104 urun · iPhone/MagSafe
  aksesuar · Peugeot|Stellantis grup adi · Toyota|Berlingo, Seat|Golf baska marka modeli)
  IC ICE. Tek kural acmak copu yayina sokar → 275 kova kanitla siniflandiriliyor,
  hukum mimarda. Ters bulgu: H1 sekil kurali **848 kova/1849 urun** aciyor (motor/sasi
  kodlari dahil) ama harf-only gercek model adlari kolsuz kaliyor.
- 🔴🔴 **K119 (16 Agu, EN YUKSEK ONCELIK) — YAYIN 15 AGU 14:02'DEN BERI KAPALIYDI.**
  Son basarili deploy SHA `268da994` (2026-08-15T14:02Z); uzerine **22 commit** birikti
  (K117 · Ducati×PR 46 urun · Kia×C3D 9 urun · ic link isleri). Kimse fark etmemis —
  `deploy` job'i `needs: [build, serit-a2, serit-a3, serit-a4]` ile fail-closed SKIPPED
  oluyordu, kirmizi CI listesinde tek satirdi.
  **Engeller sirayla kaldirildi:**
  1. `serit-a3` KIRMIZI — gizli kayitta notrlestirilmemis 4 alan (iki urun partisinden).
     Temizlendi → `62386a64`; 4 hata → **0**, `denetim-kapisi` IHLAL=0, 31 kayit notrlendi.
     Ayrinti DEVAM-ARSIV.md (git disi).
  2. `serit-a3` yine KIRMIZI — **`CIKARIM KAYBI`**, `tools/varlik-test.py`, 6 urun.
     Olculdu: urunlerin KENDI gorselleri saglam (HTTP 200); dusen sey **rel-card
     referanslariydi** (yeni ic-link algoritmasi eski hedefleri birakti). 6 id
     `varlik-cikarim-beyani.json` kapsamina alindi → `96e89833`, **serit-a3 SUCCESS**.
  3. Kalan engel `build` job'i: **D1 yazici lease'i (MAKINELER-ARASI)** — ariza DEGIL
     SIRA. Bekle→rerun→canli turnusol isi kosuyor.
  🔴 **DERS (sinif):** yayin kapaliligi hicbir yerde ALARM URETMIYOR. `deploy` SKIPPED
  sessizdir; 14 saat boyunca bes ev calisti ve hicbiri canliya cikmadi. Kalici cozum
  yayin-yasi nobetcisi olmali (son basarili deploy X saatten eskiyse KIRMIZI).
  🔴 **IKI KANCA ATLAMASI OLDU (isci karari, kayit):** mukerrer kancasi iki kez asildi;
  sebep `onarim-commit.py`'nin worktree kurarken izlenmeyen istisna dosyasini TASIMAMASI.
  Ayri kalem, sinif kapisi gerekiyor. Ayrinti DEVAM-ARSIV.md (git disi).
- 🔐 **K120 (OKAN KARARI, 16 Agu — UYGULANMADI, yayin acilinca yapilacak):** gizli kaynak
  kaydi **git'ten CIKACAK** (izlenmeyecek), yalniz diskte yasayacak; notrlenen alanlar geri
  yazilacak. Gerekce: doktrin dosyayi "gizli" sayiyor ama dosya IZLENEN ve repo PUBLIC —
  celiskiyi Okan dosyayi izlemeden cikararak cozdu.
  🔴 **UYARI (uygulayacak tura):** dosya CI checkout'unda ARTIK OLMAYACAK; onu okuyan
  kapilar yoklukta sessizce yesil SAYMAMALI — her kapinin yokluk kolu olculmeden bu is
  kapanmaz. Ad GECMISTE zaten public oldu; izlemeden cikarma geriye donuk temizlik DEGILDIR.
  Ayrinti DEVAM-ARSIV.md (git disi).
- 🔧 **K118 (YENI, 16 Agu — MaCiT bildirdi, HUKUM BENDE):** pre-push sizinti kapisi
  (`tools/gecmis-geri-donus-kapisi.py`) her BICIM-KAYDIRAN urun partisinde rc=2 verecek →
  isciler kapiyi atlamaya suruklendi (bir kez OLDU: `d8c48ad9`).
  🔬 **IKI TESHIS DE OLCUMLE CURUDU:** MaCiT "hook `main..HEAD` kullaniyor" dedi, ben
  "tum gecmisi tariyor" dedim — **ikisi de YANLIS.** `eklenen_commitler` (satir 260-280)
  `rev-list <local> --not <remote_sha>`, yedegi `--not --remotes=origin`; uc vaka
  (normal · sifir remote · bilinmeyen remote) **ucu de 0 commit / 0 aday / rc=0**.
  **Gercek:** `d8c48ad9` menzili **1 commit**, o tek commit **1.298.794 aday** uretiyor
  (butce 150.000 → %8659). Sinif bilinen: `urunler.json` girintisi kayinca diff tum
  dosyayi "eklenen satir" sayiyor ([[urunler-json-bicim-diffi-icerigi-gizler]]). Butce
  KOD commit'ine gore kalibre ("en pahali tek commit 57.339 aday"), tam-dosya veri
  commit'i onu YAPISAL olarak asiyor. Tam gecmis 3288 commit.
  **Yonum (uygulanmadi, olculecek):** butceyi buyutmek DEGIL (katalogla buyur, yine
  kirilir) — icerik ekseninde `urunler.json`'u ayri ele al; o dosyanin sizinti riski
  zaten `denetim-kapisi` + `kisisel-veri-test` mulku. Kapsam DARALTMA oldugu icin
  olcumsuz yapilmaz. `kabul:` alani BOS — kapanmadan once doldurulacak.
- 🟠 **Navlungo dilim-1 MERGE BEKLIYOR:** dal `il-ilce-dilim1` (`5d57c918`). Sonraki dilimler:
  telefon bicimi (`+90 5xx xxx xx xx`), Navlungo istemcisi (8 saat token onbellegi),
  yonetim ekraninda "Kargoya ver" (alanlar dolu, desi Okan'dan), webhook alicisi.
  **Okan kapisi:** `.navlungo-kimlik.json` doldurulmasi.

- 🔴 **K113 (YENI, 16 Agu)** — `Uretici butunluk kapisi` YANLIS SERITTE: `hijyen-build`'de, oysa URL-guvensiz ID kanonik adresi bozar = BLOKLAYICI olmali. Bugun tam bu yuzden bozuk ID'yi yakaladi ama yayini durdurmadi. `deploy.yml`'e yazmayi gerektirir; **peer'in commit'siz isi bekleniyor**.
- 🔴 **K114 (YENI, 16 Agu)** — `onarim/r2-purge` dali (`9f7aaf77`, worktree `/private/tmp/pruvo-purge`) MERGE BEKLIYOR: tek engel `ci-kapsam-test.py` rc=1 (`tools/r2-purge-test.py` CI kapsaminda degil). K113 ile AYNI dosyaya yazilacak, ayni turda kapanmali.
- ✅ **K115 KAPANDI (16 Agu)** — ic link hatti canlida (yukaridaki blok). Sayilar orada.
- 🟠 **K116 — ARAC KUSURU YOK, DUZELTME (16 Agu, olculdu):** iki kapali kume de `kimi`yi
  TANIYOR (`tools/mimar_kimlik.py` `ISCI_MOTORLARI` + `isci.sh` `GECERLI_MOTORLAR`). MaCiT'in
  gordugu RED **kota karantinasiydi** (`~/.claude/cron/.motor-karantina`: `kimi 1786826660`,
  6h omur — bugun DOLDU). Karantina bitti ama motor hala 403: *"usage limit for this billing
  cycle … refreshed in the next cycle"* — yani **fatura donemi** kotasi, saatlik degil.
  **Hat bugun: m3 BIRINCIL, kimi donem yenilenene kadar KAPALI.** Kod degisikligi GEREKMIYOR.
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
