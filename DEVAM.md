# DEVAM (KraL) — 8 Agu 2026

## 🕐 CI NOBETI — 12 Agu 2026 11:37 yerel / 08:37Z turu (KraL / Tamirci)

**Ev kontrolu:** `pwd` = `git rev-parse --show-toplevel` = `/Users/okan/dev/pruvo` → DOGRU EV.

**🟠 SUPURME rc=0 ama HUKUM=OLCULEMEDI (betigin KENDI hukmu, dogru fail-closed).** Sabit kosucu
isciye kosturuldu; betik YAZILMADI/DUZENLENMEDI. Basilan satirlar: `GITHUB_BILDIRIM_INBOX=0 ·
BULUNAN=0 · TASINAN=0 · ATLANAN=0 · CIKAN=0 · KOMSU_KAYIP=0 · KUME_DIFF=OLCULDU · KALAN=0 ·
COP_IZI=0:YOK · HUKUM=OLCULEMEDI`. Uc fail-closed alarmin ucu de sessiz. Sayac 0 iken hukum
TEMIZ **yazilamadi** cunku POZITIF tanima izi kayboldu: onceki iki tur `COP_IZI=4` olcerken bu tur
Cop'te aranan dizeden **0** kayit var.

**🔴 COP DENETIMI: MESRU=0, YANLIS=4 — SUPURMEYE ATFEDILEMEZ (dort bagimsiz iz).** Dort kayit da
GitHub-disi (biri bir odeme bildirimi). (a) Bu turun supurmesi `TASINAN=0 · CIKAN=0` — gelen
kutusundan hicbir kayit ayrilmadi; (b) log ekseninde olculdu: 12 Agu'da TASINAN>0 olan **tek** blok
01:39Z (`TASINAN=2 CIKAN=2 KOMSU_KAYIP=0`), sonraki 7 turun hepsi `TASINAN=0` — oysa dort kaydin
biri 08:10Z'de, yani son sifir-olmayan supurmeden ~6,5 saat SONRA alindi; (c) tek silme yolunun
yuklemi iki kosulu birden ister ve dordu de saglamiyor; silme artik konumdan degil kararli
KIMLIKTEN yapiliyor (aktif betikte indeks deseni **0**, silme tek satirda `whose message id is`);
(d) kayit id'leri BITISIK (dortlu blok) — tek bir elle-silme hareketinin imzasi. 48 saat log
ekseninde iki `KOMSU_KAYIP=1` izi var (11 Agu 16:39Z · 18:38Z) ama ikisinin kimligi de bir GitHub
check-suite kaydi, bu dort kayitla ESLESMIYOR. Kendiliginden geri ALINMADI (yordam geregi) —
Okan'a TEK cumle cikildi.

**✅ CI TEMIZ — onarim GEREKMEDI.** Son 25 kosumda `conclusion=failure` **0**. Alti kosum ucusta
(iki `Build & deploy` dahil); ucustaki kosum yesil degildir → hukum YAZILMADI, sonraki turun ILK
isi. Gecen turun devrettigi `31573022087` **success** ile kapandi. Yayin zinciri HEAD'i henuz
yakalamadi ama arizali degil: en son basarili deploy `31575954625`, aradaki iki commit'in kosumu
kuyrukta/ucusta.

**📏 WORKTREE 5 SATIR — TAVAN ASIK AMA OLU AGAC YOK.** K72'nin kabul olcutu (b) bu turdan itibaren
kosuyor: dort agacin da mtime'i olculdu → **4 CANLI, 0 OLU, 0 BITMIS.** Uc agac baska oturumlarin
canli iscisi (0,3 · 0,7 · 2,2 dk once dokunulmus, `locked`) — tavan sahiplik bazlidir, KraL'in
kendi agaci degil, DOKUNULMADI. K49 agaci 85 dk hareketsiz (esik 90) → **CANLI ama sinirda**,
dal origin'de, main'e gore 4 commit → tek-nusha riski YOK. Sonraki tur yeniden olculecek.

**🔧 TAMIRCI TURU.** Acik 🔧 = **12**; bu turda kapanan 0, dagitilan 0, **triyaj edilen 3**,
**yeni acilan 1 (K75)**. Olculen durumlar:
- **K56 — HALA ACIK, iddia bugun birebir dogrulandi.** Bayraksiz kol **rc=2**, `--anahat` kolu
  **rc=0**; tek sebep ayni `c4 bayt-esitlik: referans build` ÖLÇÜLEMEDİ iddiasi. Kanama CI'da YOK.
- **K58 — HALA ACIK ve buyudu.** `onizleme-kisit-kosul-test.py` **rc=1**, `IDDIA=115 KIRMIZI=1`;
  envanter beyani ile gercek **iki** dosyada ayrisiyor (11 Agu'da bir taneydi). Kok eksen: tuketici
  envanteri ELLE tutuluyor, `.scratch/` icerigi her turda degisiyor → her yeni gecici dosya kapiyi
  kirmizi yakiyor. Bugun `.scratch/` altinda **432** oge var.
- **K62 — KAPANMADI, UCUSTA.** Batarya bugun **rc=0**, `HARNESS BAYAT` satiri **yok**, `kosan=15 /
  toplam=15` (12 oldurucu + 3 kontrol). AMA bu yesil, kardes bir oturumun ana agacta COMMIT
  ETMEDIGI degisiklikten geliyor (`diff --stat` = 129 ekleme / 20 silme). Kalemin iddiasi
  "HEAD'de bayat" idi ve HEAD henuz degismedi → durum 🔧 degil **UCUSTA**; commit inince kapanir.
- **K75 ACILDI (yeni 🔧).** Cop denetimi ile supurmenin pozitif tanima izi AYNI paylasilan yuzeye
  (Cop kutusu) bagli ve o yuzeyi nobet KONTROL ETMIYOR: Okan elle mail silince denetim `YANLIS>0`
  yaniyor, Okan Cop'u temizleyince `COP_IZI` kayboluyor ve hukum kalici `OLCULEMEDI`ye dusuyor.
  Iki kol da bu turda AYNI ANDA ateslendi. Sinif: pencere-goreli alarm kendini sonduruyor.

**Bu turda:** urun verisine DOKUNULMADI · deploy elle YAPILMADI · kosum rerun/cancel EDILMEDI ·
mail betigi YAZILMADI/DUZENLENMEDI · Cop BOSALTILMADI, hicbir mail geri ALINMADI · kapi/nobetci
GEVSETILMEDI · yabanci ` M`/`??` dosyalara DOKUNULMADI · dort CANLI agacin hicbirine YAZILMADI ·
**merge YAPILMADI** · dal SILINMEDI. Okan'a **CIKILDI** (tek cumle, odeme ekseni — §0.5 geregi).

**Sonraki turun ILK ISI:** (a) ucustaki alti kosumun conclusion'i JOB birimiyle; (b) K49 agacinin
mtime'i (85 dk → esige 5 dk kalmisti) ve kalan 4 iade maddesi; (c) K62'nin commit'i indi mi
(indiyse kalem KAPANIR); (d) K49 agaci kapaninca K69 + K70 WIP'lerinden yeniden dagitim.

## 🕐 CI NOBETI — 12 Agu 2026 10:37 yerel / 07:37Z turu (KraL / Tamirci)

**Ev kontrolu:** `pwd` = `git rev-parse --show-toplevel` = `/Users/okan/dev/pruvo` → DOGRU EV.

**🟢 SUPURME rc=0 — HUKUM=TEMIZ.** Sabit kosucu isciye kosturuldu; betik YAZILMADI/DUZENLENMEDI.
Basilan satirlar: `GITHUB_BILDIRIM_INBOX=0 · BULUNAN=0 · TASINAN=0 · ATLANAN=0 · CIKAN=0 ·
KOMSU_KAYIP=0 · KUME_DIFF=OLCULDU · KALAN=0 · COP_IZI=4:2026-08-12T04:05:51 · HUKUM=TEMIZ`.
Uc fail-closed alarmin ucu de sessiz; sayac 0 iken hukum TEMIZ cunku POZITIF tanima izi var.
**🟠 Cop denetimi: MESRU=4, YANLIS=2** — gecen turun ta kendisi olan IKI bulten kopyasi (09:01),
yeni kayit YOK; supurmeye atfedilmez (`CIKAN=0`, yuklem bulteni kapsamiyor). Okan'a bir kez
cikilmisti, TEKRAR EDILMEDI. Siparis/odeme ekseninde Cop'te kayit YOK.

**✅ CI TEMIZ — onarim GEREKMEDI.** Son 30 kosumda `conclusion=failure` **0**. Gecen turun defter
push'unun YAYIN zinciri JOB birimiyle kapandi: `31573021777` → `serit-a2·serit-a3·serit-a4·build·
deploy·yayin` **6/6 success**. Kardes SERIT B kosumu `31573022087` hala `in_progress` (10 job
success + 1 skipped + 2 uzun batarya ucusta, **dusen 0**) — yayini BLOKLAMAZ, hukum YAZILMADI
(ucustaki kosum yesil degildir); sonraki turun ILK isi.

**📏 WORKTREE 3 → 2 SATIR — TAVAN SAGLANDI.** Kaldirilan tek agac K69'un OLU iscisiydi
(`agent-a0432ed5…`, 1s45dk hareketsiz, cikti uretmedi). Sira ZORUNLU tutuldu: origin'de olmayan
commit **0** olarak olculdu (`ls-remote` ile bagimsiz teyit, WIP `31053890` zaten uzakta) →
commit'siz yama 17.993 bayt + 3 izlenmeyen kesif betigi arsivlendi → kabul TEMIZ klon uzerinde
uretildi (`apply --check` **rc=0** + uc dosyanin sha256'si orijinalle BIREBIR) → ANCAK ONDAN SONRA
kaldirma yetkilendirildi. Dal yerelde ve origin'de KALDI, spec duruyor.

**🟢 K49 IADE ONARIMI — BLOKLAYICI MADDE OLCULEREK KAPANDI, ISCI CANLI.** Gecen turun 1. iade
maddesi (dal `is-akisi-kapisi.py`'yi rc=1 yakiyor) artik gecerli DEGIL: dal **rc=0**, ana agac
**rc=0** — parite SAGLANDI; sayac farki (kapi cagrisi 292/290 · SERIT B beyani 109/107 · bloklayici
110/108) dalin kendi diff'inden turuyor, yani mimar karari geregi iki adim `serit-b`'de KALMIS ve
**beyan tablosuna KAYDEDILMIS.** Isci canli (agac 18 dk once dokunulmus) ama commit'siz 5 dosya
tasiyor → K72 riskine karsi SALT-OKUMA sigorta anlik goruntusu alindi (22.674 bayt, temiz klon
uzerinde `apply --check` **rc=0**; hedef agaca YAZILMADI, commit/stash ATILMADI).
Dal main'e gore 5 dosya / +1048 / −3. **Merge YAPILMADI** — kalan 4 iade maddesi henuz kapanmadi.

**🔧 TAMIRCI TURU.** Acik 🔧 = **12** (K49·K53·K54·K55·K56·K58·K59·K62·K69·K70·K71 + yeni **K72**);
bu turda kapanan 0, dagitilan 0 (worktree tavani: K49 agaci canli oldugu icin K69 yeniden dagitimi
sonraki tura birakildi — is DURMADI, WIP korunuyor). **K72 ACILDI:** izole agacta kosan muhendis
iscisi rapor uretmeden oluyor — **12 saatte DORT olculen vaka** (222 · 156 · 138 · 105 dk
hareketsizlik). Kurtarma semasi ("ilk 15 dk'da WIP commit + push") dordunde de tuttu → **is kaybi
0**; kalan zarar KAYIP degil ~1 saatlik KUYRUK GECIKMESI. Ders: bir isciyi dagitmak onu
CALISTIRMAZ; dagitimin kabulu artefakttir ve artefaktin TAZELIGI de olculmelidir (mtime olcumu bu
turdan itibaren her tur kosuyor). **K73 ACILDI** (MaCiT gozlemi, ACIK): hasat terim havuzu dilim
sonrasi yeniden yazilmadigi icin sonraki dilim ayni adaylari tekrar isliyor.

**Bu turda:** urun verisine DOKUNULMADI · deploy elle YAPILMADI · kosum rerun/cancel EDILMEDI ·
mail betigi YAZILMADI/DUZENLENMEDI · kapi/nobetci GEVSETILMEDI · yabanci ` M`/`??` dosyalara
DOKUNULMADI · CANLI K49 agacina YAZILMADI · **merge YAPILMADI** · dal SILINMEDI.
Okan'a CIKILMADI (insan karari gerekmedi; §5).

**Sonraki turun ILK ISI:** (a) `31573022087` conclusion'i JOB birimiyle; (b) K49 iscisinin kalan 4
iade maddesi — cikti dustuyse bagimsiz curutucu, dusmediyse mtime ile olum karari (K72 yordami);
(c) K49 agaci kapaninca K69'un WIP'inden yeniden dagitim; (d) K70 WIP'inden devir.

_Daha eski bloklarin TAM metni DEVAM-ARSIV.md dosyasindadir (kayipsiz tasindi)._
_Acik kalemlerin KAYNAK DOGRUSU: ~/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md_
