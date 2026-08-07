# DEVAM (KraL) — 7 Agu 2026

## ✅ OKAN'IN BILDIRDIGI MARKA SAYFASI KUSURU KAPANDI — merge `d0534fd2`, canlida dogrulandi
Kusur: kapsam sayaci **yanlis birimde** sayiyordu — yalniz `.card` dugumlerini, model kovalarini
DEGIL. `/marka/audi/?kategori=Otomobil` ekranda **201** derken gercek **329**; ayni sayfanin kendi
meta'si zaten 330 diyordu (iki sayi, iki kaynak). Ikinci kusur: `uret()` birlesimi id bazinda
tekillestirilmiyordu → 31 sayfada mukerrer kart.
**Sinif olcumu (marka-ozel onarim DEGIL, Okan'in uyarisi uzerine sertlestirildi):** sapan marka
sayfasi **40→0**, katmanlar ayri: >500 kalem **13→0** · 50-500 **13→0** · 2-49 **14→0** ·
929 model sayfasi zaten 0. Gizlenen kalem **9.378→0** · mukerrer kart **282→0** · kaybolan kart
**0** · kodda marka literali **0/8 yuzey** · iddia **8758/8758** · oldurucu **11/11** (esik ve
"marka-ozel dal" mutantlari dahil) · kontrol **3/3** · ayrisan-olmayan **0** · `urunler.json` 0 satir.
**Canli teyit** (kanonik adres, cache-bust YOK, render edilmis DOM): audi filtreli **201→329**,
filtresiz **330**, mukerrer 202 ham→**199/199**; ford **2582**==2582 · bmw **2310**==2310
(`?kategori=Motosiklet` **628**==628) · kia **341**==341 · subaru **35**==35 · gopro **45**==45.
**Kapi serit karari (davranistan dogrulandi, beyandan DEGIL):** `marka-sayac-kapisi.py` tamamen
yerel/deterministik (ag yok, kardes depo yolu yok) → `serit-a3`, yani `deploy: needs` icinde
**BLOKLAYICI**; `continue-on-error` YOK. D1 dort eksen yesil (21845==21845).
📌 Yol notu: iscinin `gorunenKart + Σ buton` formulu olcumde YANLIS cikti (kart ve kova kumeleri
cakisiyor → 373). Sayi artik SSR'de tek kanonik fonksiyondan tekil birlesim olarak turuyor.

## ⏱ SAATLIK CI NOBETI — 7 Agu 14:37Z turu (ev DOGRU: ~/dev/pruvo)

**Mail supurmesi (kosulsuz):** tasinan **3** · tur sonu inbox'ta "Run failed" **0**.
Cop BOSALTILMADI, baska maile dokunulmadi.

**🔴→🟢 BLOKLAYICI KIRMIZI BULUNDU VE KAPANDI (bu turun ISI):**
`Build & deploy` / `serit-a3` iki ardisik push'ta kirmizi (`31184326063` `b3d7dc95`,
`31187345564` `d0534fd2`) → `deploy` + `yayin` **SKIPPED**, yayin duruyordu.
Dusen adim: `Gramer artigi kapisi (toplu yeniden yazim enkazi + cumle-ici yetim ek)`.
- **KOK NEDEN:** `cift-noktalama` kolunun `\.\s*,` dali Turkce KISALTMA + virgul yazimini
  ("... vb., ...") enkaz sayiyordu. **URUN METNI DOGRUYDU, kusur BETIKTEYDI.**
  5 Agu'da (`f926e0df`) ayni kol sira sayisi varyantiyla ("7., 8. ve 9. nesil") yayini
  durdurmustu; o tur `(?<!\d)` lookbehind'i eklendi ama lookbehind SABIT genislik ister →
  degisken uzunluktaki kisaltma kumesini tasiyamaz. Tekil string yamasi 2 gunde IKINCI kez
  yetmedi. → [[envanter-drift-parti-basina]] sinifi (kapi her katalog partisinde bayatliyor).
- **ONARIM `a0beef7a`:** kol lookbehind yerine TEK yargi noktasiyla daraltildi — nokta oncesi
  jeton RAKAM ya da KANONIK KISALTMA ise muaf, BASKA HER SEY ihlal kalir. `KISALTMALAR` tek
  kaynak sabiti: hem regex muafiyeti hem oz-test fiksturu ondan turer (ikinci elle liste YOK).
  Muafiyet kablosu fail-closed (desen adi tutmazsa import aninda patlar). `search` → `finditer`:
  muaf isabet artik ayni satirdaki GERCEK enkazi maskeleyemez.
- **OLCUM:** kapi `rc=0`, ihlal **0/21.845** · oz-test iddia **60 → 96** · mutasyon **8/8**
  oldurucu (kume bosaltma · genel gevsetme · kol silme · maskeleme · kablo kopmasi ayri ayri
  kirmizi yakiyor). Surucu REPODA durur: `tools/gramer-kisaltma-mutasyon.py`.
  → [[mutasyon-kaniti-yeniden-uretilebilir]]
- **Maruziyet olculdu** (21.845 kayit): nokta ile biten **2.867** ayri jeton; cumle-ici nokta
  tasiyan 25 jeton; `X.,` kalibina fiilen giren **2** vurus (ikisi de mesru).
- **KANIT:** `31191071227` (`a0beef7a`) JOB birimiyle `build`·`serit-a2`·**`serit-a3` success**.
  `deploy.yml` degisikligi YALNIZ yorum (adim silme / `continue-on-error` YOK — diff ile teyit).

**⚠️ IKI DERS (hafizaya yazilacak):**
(a) **Paralel oturum ayni kirmiziyi URUN METNINI degistirerek yesile boyadi** (`fd243cfa`).
    Yesilin kimden geldigi 2x2 matrisle olculdu: eski kapi × eski katalog `rc=1`,
    **yeni kapi × ESKI katalog `rc=0`** (onarim TEK BASINA yeterli), eski kapi × guncel
    katalog `rc=0`. Yesil ODUNC DEGIL. Ayni kisaltma katalogda 69 yerde → metin duzeltmesi
    betik onarimin YERINE GECMEZ. → [[isci-yesili-sahiplenir]]
(b) **Mutasyon bataryasi bir kez SESSIZCE zayifladi:** bir mutantin oldurme ekseni CANLI
    kataloga bagliydi; paralel oturum tuzagi metinden cikarinca mutant sag kaldi (8/8 → 7/8).
    Oldurme girdisi betigin KENDI fiksturune tasindi — kabul kaniti artik baska bir mimarin
    VERI DUZLEMINE bagimli degil. → [[fikstur-degeri-mutasyon-koru]]

**✅ TUR ICINDE KAPANDI — TAM YESIL YAYIN:** `31191071227` (`a0beef7a`) beklendi ve JOB birimiyle
olculdu: `build` · `serit-a2` · `serit-a3` · `serit-a4` · `deploy` · `yayin` **HEPSI success**
(kosum `conclusion=success`). Gramer kapisi onarimi bloklayici zinciri gercekten ACTI:
2 push boyunca SKIPPED kalan `deploy` bu kosumda **success** (31 sn), `yayin` **success** (42 sn).

**Kalan olcumler:**
- 🟢 **`serit-a4` suresi ASILMADI (BEKLEYEN #5 icin taban):** **47 dk 58 sn** olculdu —
  tarihsel 42-50 dk aralig(in)da, katalog 21.845 → 22.037 buyumesine ragmen. Tur ortasindaki
  "~80 dk" tahmini YANLISTI (olculmemis gecen sureyi job suresi sandim); dogru sayi 47m58s.
  `nobet.yml` seridine tasima kosulu (60 dk+) **GERCEKLESMEDI** → tasima YAPILMADI.
  → [[kapi-birikimi-yayin-gecikmesi]]
- 🔴 `r2-onek-nobeti` (SERIT B, `deploy: needs`'te DEGIL → yayini DURDURMAZ): kardes oturumun
  `OLCULEMEDI` ≠ `KIRMIZI` ayrimi main'e **GIRMEDI** (calisma agacinda commit'siz duruyor)
  → **10. kirmizi.** DUR kosulunda, sifirdan teshise BASLANMADI. → [[hukum-yanlis-birimde]]
- 🟡 D1 (`d1-sync.py --durum`): SAYI ekseni D1 **21.988** vs yerel benzersiz **22.037** (49 satir);
  ICERIK ekseni **22.037/22.037 hash birebir** ✅; turetilmis kolonlar `marka_kanon`(49) ·
  `model_kanon`(20) · `marka_arama`(49) BAYAT — hepsi YENI INEN partinin satirlari, deploy
  ucusta. MaCiT duzlemi, DOKUNULMADI. → [[yayin-penceresi-taslak-satir]]
- Calisma agacindaki yabanci 5 dosyaya DOKUNULMADI; `git add` yalniz onarim dosyalarina yapildi.

**DEVIR — sonraki turun ILK isi:**
(1) Ucustaki `31195954169` (`3f3e299a`) zincirini JOB birimiyle olc; success ise canli katalog
    **22.037+**'ye ulasmis olmali (`d1-sync.py --durum` ile teyit; bu tur D1 sayi ekseni 21.988'di).
    **`serit-a3` gramer sinifi KAPANDI** — oradan teshise BASLAMA.
(2) `serit-a4` **60 dk+** surerse `nobet.yml` seridine tasinmasi (precedent `ffc72a6a`,
    "kaybolan 0" olcumuyle) o turun ISI olur. Bu turda **47m58s** olculdu, esik ASILMADI.
(3) `r2-onek-nobeti` icin onceki turun devri aynen gecerli: ayrim main'e girdi mi olc, girdiyse
    yesile/sari `OLCULEMEDI`'ye donmeli.

**Codex NOT:** kredi kotasi **TUKENDI** (yenilenme 8 Agu 10:19) → bu tur tamamen Claude katinda
kosuldu; sonraki tur da Codex'siz planlanmali.

## 🔚 7 Agu OTURUMU — MAIN'E GIREN (tek satir + SHA; TAM DOKUM ARSIVDE)
1. Varlik kaldiraci `8bbd760c` — artefakt **833,6 → 617,1 MiB** (1 GB tavaninda %81,4 → %60,3),
   sayfa basi **61.625 → 26.252 bayt**, kaybolan URL **0**; `enjeksiyon-kapisi.py` ekseni 9→12.
2. Nobet ayrimi `ffc72a6a` — 6 bloklamayan job `nobet.yml`'e; `deploy: needs` **4..4**,
   bloklayici adim **132..132**, **KAYBOLAN 0**; `pages` concurrency kilidi cozuldu.
3. Denetim kapisi `3b369e34` — `--evet-sil N` onayi (tavan 50); onaysiz toplu silme rc=4 /
   silinen 0 / sha256 DEGISMEDI; kendini-test **50 iddia**.
4. Kanca koku `3aec9eba` — kok artik `-C` kesfinden turuyor; yuzey **214.553..214.553**.
5. Ata-lisans kapisi `c3c23d2e` — sessiz gecis **12..0**, yanlis-pozitif 0/31, yanlis-negatif
   0/22, iddia 28→54, oldurucu 20/20. → hafiza [[mutasyon-bytecode-onbellegi]]
6. `serit-a3` + is-akisi kapisi `336a16bc` — kurban artik **kanonik** seciliyor.
7. `serit-a4` ayirt edicilik `07f4bb44`+`1141be85` — `ayirt-edilemeyen` **1..0**, mutant sayisi DUSMEDI.
8. 6 kayit `marka` duzeltmesi `67820319` — Okan'in ACIK IZNIYLE tek seferlik duzlem sinir asimi;
   `uyum-kapisi` **rc 1→0**, katalog **21376..21376**, arama kaybi **0**, D1 dort eksen yesil.
9. Defter budama `33e0a27e`+`7eed7d68`+`c9d9f362` — kayipsiz arsivleme, sinif kapisi **0 ihlal**.
10. `r2_anahtar.py` onek onarimi merge `e3880c89` — deploy `31162365695` success (birebir headSha),
   canli **21376**, ornek urun sayfasi **200**, D1 dort eksen yesil. Parite: `parite-test.js`
   **1199/1199** · `parite-ege.js` **848/848**, rc=0 (onceki OLCULEMEDI bayat dal worktree'sindendi
   → [[parite-testi-olculemedi-basiyor]]). **Ders: nihai agac temiz olmasi YETMEZ, ARA COMMIT'IN
   DIFF'i de public.** Ikinci ders: **iscinin kabul sayisi curutulmeden alinmaz** (8 dusmanca
   mutantin 5'i sag kalmisti; onarim sonrasi iddia 14/14 · oldurucu 18/18 · kontrol 4/4).
11. Gizlilik nobetcisi merge `197fd396` (dal `b3f3e3da` MAIN'DE) — icerik ekseni kanonik kaynaga
   baglandi; iddia **5** · oldurucu **7/7** · kontrol **2/2** · ayrisan-olmayan **0**.
   → hafiza [[nobetci-kanonik-kaynagi-tek-eksende]]
12. ✅ **YAYIN ACILDI — 19 SAATLIK TIKANIKLIK KAPANDI:** kosum `31155302659` (`655ae5e2`) JOB
   birimiyle tamami yesil (`build`·`serit-a2`·`serit-a3`·`serit-a4`·`deploy`·`yayin`).
   Canli katalog **20.849 → 21.376** = yerel → **acik 527 KAPANDI**. "404 anomalisi" COZULDU:
   kusur OLCUMDEYDI — kanonik adres `/urun/<id>/`, katmanli ornek **60/60 → 200**, sitemap
   **21.376 = kayit**, ETKILENEN KAYIT **0**. → hafiza [[kanonik-adres-olcum-yanlisi]]
13. TEMIZLIK: mukerrer bir CI dali **merge EDILMEDEN silindi** (icerigi main'de VE gerileme
   tasiyordu); `git worktree list` **6 → 2**, kalanlar baska oturumlarin, DOKUNULMADI.

**BEKLEYEN (acik kalemler):**
1. 🔴 `tools/yayin-kapisi.py` yalnizca D1'de `yayinda=0` olan TASLAK satirlarin adresine HTTP atar;
   **taslak yoksa hicbir sayfa olcmeden success verir** → `yayin` job'unun yesili "katalog yayinda"
   demek DEGILDIR. [[beyan-edilmis-survivor]] sinifi. BENDE.
2. `uyum-kapisi.py` kirpma korlugu — **TEK DOSYADA IKI YAZAR:** kapi ihlalleri 5'te kesiyor ama
   kestigini/toplami BASMIYOR (`sema ihlali 6` sayarken 5 basti). Kardes oturumun onarimi ana
   agacta commit'siz ve raporlama tasarimi daha iyi → ustune YAZILMADI. Benim dalimdan
   (`muh/a4-uyum-kesme`, origin'de) alinacak tek sey **mutasyon kanit katmani**.
3. Ata-lisans — 5 GIZIL delik + veto genisligi: derin ic-ice zarf · ayni duzeyde iki zarf anahtari ·
   alan adi harf varyanti → hala `ALAN-YOK` (rc=0). Bugunku tek platformda erisilemez, yeni
   platform acilirsa dogar. Veto genis: 6 sentetik mesru lisansin 4'unu yiyor. **Sonucu olculmedi.**
4. `uyum` semasina varyant alani (sasi/varyant kodu) — 8. maddedeki duzeltme jetonu DUSURDU; dogru
   uzun vadeli cozum turetmenin onu URETMESI. Sema + kapi + D1 kolonu isi. BENDE.
5. `serit-a4` bataryasi **42-50 dk** — yayin seridini uzatiyor ve `pages` grubunu tutuyor. BENDE.
6. `pages` grubundaki **6/6 job'da `timeout-minutes` YOK** (varsayilan 360 dk) — Okan kapisi.
7. r2 onek kalani: **CGTrader tek gelenek (tiresiz) uygulamasi** + `x` onekli 1 kaydin anahtari (MaCiT).
8. Gizlilik KALAN SINIR: ad (ozet) ekseni dosya icerigine baglanamadi — PBKDF2 tam tarama
   **3.996.480 aday / 188 sn**. O eksen dosya iceriginde **OLCULEMEDI**, yesil DEGIL.
9. ⏸ GIT GECMISI — **OKAN HUKMU: DOKUNULMAYACAK.** 2610 commit tarandi, **6 commit mesajinda**
   sinif bulgusu var (dokum ARSIVDE). Karar (7 Agu): simdilik temizlenmeyecek, kayit altina alindi.
   Gerekce: yenilenecek sir YOK + temizlik force-push demek (klon/dal/CI SHA bagi kirilir).
   Bundan SONRAKI commit'leri nobetci bloklar. Karar acik, yeniden acilabilir.
10. Homonim markada ikinci kapi (ortak arac, BENDE): `genesis` literalini gecen 9 kaydin
   **6'si (%67)** arac-disiydi. Kanonik `hasat_tara.py` marka-literal kapisindan sonra
   **arac-baglam kapisi YOK**; o hucrede elle konuldu, kalicilastirma bende.
11. HocA → ADIM 2 (`?model=` uyelik yuklemi). MaCiT → iki worktree merge karari + 2 kayit geri cekme.

**OKAN'DA KARAR (1):** kardes mimarin sordugu **satin-alma fiyatlandirmasi** — ucretli ama ticari
yeniden-satis hakki veren 109 kayitlik kuyruk icin maliyet fiyata nasil yansiyacak
(sabit marj mi, maliyet+X TL mi)? Yanit gelmeden o kuyruk islenmez.

## Onceki turlarin VE 7 Agu oturumunun TAM dokumu — ARSIVDE (DEVAM-ARSIV.md, git disi).
