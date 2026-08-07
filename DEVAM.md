# DEVAM (KraL) — 7 Agu 2026

## 🔚 OTURUM KAPANISI — 7 Agu · YAYIN ZINCIRINDEKI 4 ENGELIN 4'U KALKTI

**MAIN'E GIREN (SHA + olculen sayi):**
1. **Varlik kaldiraci `8bbd760c`** — atif modulu her urun sayfasindan tek same-origin varliga.
   Artefakt **833,6 → 617,1 MiB** (1 GB tavaninda **%81,4 → %60,3**), sayfa basi
   **61.625 → 26.252 bayt**, **kaybolan URL 0** (iki yonde 22.511=22.511).
   🔴 `enjeksiyon-kapisi.py` **2b ekseni DISSIZDI** — uretilen sayfada HTML yorumu ariyordu ama
   uretim yorumlari SOYUYOR → hep bos dize olcuyordu. 4 davranissal eksenle degistirildi (9→12).
   Curutme: oldurucu 5/5 KIRMIZI, kontrol 2/2 YESIL, artefakt deltasi bagimsiz hesapla birebir.
   **Yasal eksen elendi:** tasinan blok CC BY atfi DEGIL; CC BY atfi ayri ve **statik HTML**.
2. **Nobet ayrimi `ffc72a6a`** — 6 bloklamayan job `deploy.yml`'den `nobet.yml`'e.
   `deploy: needs` **4..4** · bloklayici adim **132..132** · tasinan **6/6** · **KAYBOLAN 0**.
   🟢 **CONCURRENCY KILIDI COZULDU:** `pages` grubunda kalan 6/6 job yayin zincirinde.
3. **Denetim kapisi `3b369e34`** — `--evet-sil N` onayi (tavan 50). Onaysiz toplu silme
   **rc=4 / silinen 0 / sha256 DEGISMEDI**; kendini-test 50 iddia. (760 kayitlik silme kaleminin kapisi.)
4. **Kanca koku `3aec9eba`** — worktree'de kanca icinden `GIT_DIR` **mutlak** geldigi icin kok
   `<wt>/tools` cikiyor → rc=2 → **commit BLOK** → isciyi kanca atlamaya itiyordu. Kok artik
   `-C` kesfinden turuyor. Kapali-kalma curutmesinin dokumu ARSIVDE; yuzey **214.553..214.553**.
5. **Ata-lisans kapisi `c3c23d2e`** — turev kaydin atasi kendi verisinde gorunmuyor; ata ancak
   baglantinin **HOST**'undan platform+id cikarilip o platformun API'sine gidilerek cozuluyor.
   Ilk surumde **12 sessiz gecis** vardi (en agiri: turev detayi 404 → "ata yok" → temiz sayiliyordu);
   **12..0**, yanlis-pozitif **0/31**, yanlis-negatif **0/22**, iddia 28→54, oldurucu 20/20.
   🔴 Batarya kendi korlugunu de tasiyordu: ayni uzunluktaki mutasyon ayni saniyede yazilinca
   bytecode onbellegi yuzunden UYGULANMIYOR; mutant kirmizi yaniyor ama dusen **bir oncekinin**
   iddiasi. Onarildi ve bagimsiz yeniden uretildi. → hafiza `[[mutasyon-bytecode-onbellegi]]`
6. **`serit-a3` + is-akisi kapisi `336a16bc`** — mutant tek bir **sabit kodlanmis kurban** uzerinden
   olcuyordu, serit ayrimi o kapinin kolunu tasiyinca fikstur curudu. Altinda gercek delik: bloklayici
   adim silinince tum kapilar rc=0 kaliyordu, `SERIT_B` bunu "bloklayicidir" diye **beyan ediyor ama
   olcmuyordu**. Kurban artik **kanonik** seciliyor.
7. **`serit-a4` ayirt edicilik `07f4bb44`+`1141be85`** — iki mutant dusen iddialarin **KIMLIGINDE**
   ayrismiyordu; M14'un ekledigi vaka zaten kirmizi listenin icinde gizleniyordu. Kolay yol
   (mutant birlestirme) SECILMEDI; gercekten ayri olan davranis icin yeni provenans ekseni eklendi.
   `ayirt-edilemeyen` **1..0**, mutant sayisi **DUSMEDI**.
8. **6 kayit `marka` duzeltmesi `67820319`** — ⚠️ **OKAN'IN ACIK IZNIYLE, TEK SEFERLIK duzlem
   sinir asimi** (urun verisi normalde baska mimarin). `uyum-kapisi` **rc 1→0**
   (`gecen 42 · kalan 0 · iddia 42 · taban 42` — susturma yok), katalog **21376..21376**
   (silme 0), **arama kaybi 0** (dusen 6 jetonun 6/6'si kendi kaydinin basliginda duruyor),
   D1 dort eksen yesil. Kapinin "6 mi 7 mi" celiskisi sahteydi: 7. kayit kapinin kendi
   POZITIF-KONTROL sentetigi.
9. **Defter budama `33e0a27e`+`7eed7d68`** — kayipsiz arsivleme, sinif kapisi 0 ihlal.

**TEMIZLIK:** mukerrer bir CI dali **merge EDILMEDEN silindi** — icerigi main'de VE **gerileme
tasiyordu** (hesap kimligini `secrets.` yerine duz metne ceviriyordu). `git worktree list`
oturum boyunca **6 → 2**; kalanlar baska oturumlarin, DOKUNULMADI.

**KOSUYOR:** yayin nobeti 13. vardiya — kosum **`31154170116`** (headSha `67820319`) izleniyor.
Kabul: `deploy` **JOB**'u success + canli urun sayisi = hedef + yeni urun sayfasi 200.

**BEKLEYEN:**
1. 🔴 **YAYIN HENUZ DOGRULANMADI** — canli **20.849**, hedef **21.376** → **acik 527 urun**,
   yeni urun sayfalari **404**. Zincirdeki dort engel de kalkti (altyapi + 2 kod + veri), yesil
   BEKLENIYOR ama **olculmedi**. Onbellek elendi: `?cb=` olcumu bayt-birebir ayni → **origin bayat**.
   🔴 Hukum **JOB** biriminde verilir: kosum-duzeyi `conclusion` yaniltir (olculdu: kosum `failure`
   iken `deploy` `success` olan bir vaka canliyi besledi).
2. **`uyum-kapisi.py` kirpma korlugu — TEK DOSYADA IKI YAZAR.** Kapi ihlalleri 5'te kesiyor ama
   kestigini/toplami BASMIYOR (`sema ihlali 6` sayarken 5 basti; bu gece bir onarim eksik
   yapilacakti). Kardes oturumun onarimi ana agacta commit'siz duruyor ve **raporlama tasarimi
   daha iyi** — ustune YAZILMADI. Benim dalimdan (`muh/a4-uyum-kesme`, origin'de) alinacak tek
   sey **mutasyon kanit katmani**. Karar: kardes surum taban, kanit katmani asilanir.
3. **Ata-lisans — 5 GIZIL delik + veto genisligi.** Derin ic-ice zarf · ayni duzeyde iki zarf
   anahtari · alan adi buyuk/kucuk harf varyanti → hala `ALAN-YOK` (rc=0). Bugunku tek taranan
   platformda **erisilemez**, ama bir platform olculmeden acilirsa dogar. Ayrica veto ekseni
   genis: 6 sentetik mesru lisansin 4'unu yiyor (yon fail-closed). Cip kostu, **sonucu olculmedi**.
4. **`uyum` semasina varyant alani** (sasi/varyant kodu) — 8. maddedeki duzeltme jetonu DUSURDU;
   dogru uzun vadeli cozum turetmenin onu URETMESI. Sema + kapi + D1 kolonu isi, BENDE.
5. **`serit-a4` bataryasi 42-50 dk** — yayin seridini uzatiyor ve `pages` grubunu tutuyor. BENDE.
6. **`r2_anahtar.py` `ONEKLER`de bir platform eksik** (kardes mimar olctu: 1 kayit yanlis onekle
   canlida) + ayni platformda **iki anahtar gelenegi** olusmus. Tek gelenek karari BENDE.
7. `pages` grubundaki **6/6 job'da `timeout-minutes` YOK** (varsayilan 360 dk) — ikincil
   sertlestirme; workflow degisikligi Okan kapisi.
8. HocA → ADIM 2 (`?model=` uyelik yuklemi). MaCiT → iki worktree merge karari + 2 kayit geri cekme.

**OKAN'DA KARAR (1):** kardes mimarin sordugu **satin-alma fiyatlandirmasi** — ucretli ama ticari
yeniden-satis hakki veren 109 kayitlik kuyruk icin maliyet fiyata nasil yansiyacak
(sabit marj mi, maliyet+X TL mi)? Yanit gelmeden o kuyruk islenmez.

## Onceki turlarin dokumu (saatlik CI nobetleri, A20 capasi, kok turetimi, diriltme kapisi,
## backfill gorsel-gate) — ARSIVDE (DEVAM-ARSIV.md, git disi).
