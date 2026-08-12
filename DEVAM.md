# DEVAM (KraL) — 8 Agu 2026

## 🕐 CI NOBETI — 12 Agu 2026 12:37 yerel / 09:37Z turu (KraL / Tamirci)

**Ev kontrolu:** `pwd` = `git rev-parse --show-toplevel` = `/Users/okan/dev/pruvo` → DOGRU EV.

**🟢 SUPURME rc=0 — HUKUM=SUPURULDU (bu tur GERCEK kosum, no-op degil).** Sabit kosucu isciye
kosturuldu; betik YAZILMADI/DUZENLENMEDI. Basilan satirlar: `GITHUB_BILDIRIM_INBOX=1 · BULUNAN=1 ·
TASINAN=1 · ATLANAN=0 · CIKAN=1 · KOMSU_KAYIP=0 · KUME_DIFF=OLCULDU · KALAN=0 ·
COP_IZI=1:2026-08-12T11:45:04 · HUKUM=SUPURULDU`. Uc fail-closed alarmin ucu de sessiz; muhasebe
kapali (`CIKAN = TASINAN = 1`). Tasinan tek kayit kimlikle secildi ve **bir CI arizasini haber
veriyordu** — asagidaki alarm oradan cikti.

**🟠 COP DENETIMI: MESRU=1, YANLIS=4 — SUPURMEYE ATFEDILEMEZ (ikinci ardisik tur).** Dort kayit da
GitHub-disi (iyzico toplu odeme · Info Yatirim · Claude Team · Skool), kayit id'leri **bitisik
blok** (68184-68187) = tek elle-silme hareketinin imzasi; bu turun supurmesi yalnizca 1 kayit
tasidi ve o kaydin kimligi dordunden hicbiriyle eslesmiyor. Okan'a **TEKRAR CIKILMADI**: ayni sinif
ayni gun bir kez bildirildi, Okan'dan yeni bir karar istemiyor (§5 olcutu) ve kalem zaten **K77**
olarak defterde acik. Kendiliginden geri ALINMADI.

**🔴 CI KIRMIZISI GERCEKTI — `Yayin erisim alarmi`, 11 URL canlida 404.** Kosum `31579567151`
(08:42Z) dusen adim *"Olcum — yayinlanmis sayfalar canlida ACIK mi"*: `HUKUM: KAPALI — 11 URL
kapali/dongu, 0 olcum arizasi, 361 acik · GECICI=0`. Bagimsiz canli teyit (09:41Z, cache-bust'SIZ):
**11/11 URL 200**, anasayfa/sitemap/urunler.json 200 → kapanma GERCEKTI ama GECICIYDI. Kok eksen
olculdu: alarm evreni HEAD'den turuyor, olctugu canli yuzey son basarili deploy'un SHA'sinda —
bu turda **4 commit geride** (`31579986390` @ `9cf40ae3` ↔ o anki `origin/main` `c4a1931a`).
Is `deploy.yml` `needs:` zincirinde DEGIL (ayri concurrency, yalniz `cron "26 * * * *"`) → **yayini
DURDURMAZ.** Diger eksende CI temiz: son 30 kosumda baska `failure` **0**, `cron-nabzi` success.
**K78 ACILDI ve AYNI TURDA DAGITILDI** (MUHENDIS/Opus, izole agac, dal `kral/k78-yayin-erisim-evren-
hizalama`); dagitim ARTEFAKTLI ve CANLI — **K72 kurtarma semasinin IKI sarti da TUTTU**: WIP commit
alindi (`e7ecec0e`) ve dal tur icinde origin'e **ITILDI** (`b3345e8c`, `ls-remote` ile bagimsiz
teyit) → objeler tek nushada DEGIL, is kaybi riski **0**. Isci tur sonunda hala CALISIYOR; tur ici
bekleme suresi (~25 dk) doldugu icin hukum YAZILMADI (§3.5) — devralma sonraki turun ILK isi.

**📏 WORKTREE — K63/K64 AGACI ARSIVLEME GEREKTIRMEDEN DUSURULDU.** Uc eksen once olculdu:
`merge-base --is-ancestor d5141b20 origin/main` **rc=0** · `origin/main..dal` **0 commit** ·
agacta `status --porcelain` **0 satir** · `ls-remote` ile dalin uzakta durdugu bagimsiz teyitli →
arsivlenecek commit'siz is YOKTU, kaldirma yetkilendirildi. **Dal SILINMEDI** (yerelde+origin'de).

**🟡 K35/K36 MERGE ON-KOSULU ACILDI AMA KAPANMADI — MERGE YAPILMADI.** MaCiT'in veri onarimi indi
(`28ef3b43`, 3 Volvo Penta kaydindan `tur` kalkti) — sana yazdigim "once veri, sonra merge" sirasinin
ilk adimi kapandi. Dal agacinda `git merge origin/main` **TEMIZ** (cakisma YOK, `f343b398`); dal
main'e gore 6 dosya / +830 / −40 ve `urunler.json`/`worker/`/`shop/` diff'te **YOK** (kapsam KraL
duzlemi). ANCAK `malzeme-yuzey-kapisi.py` **rc=3 = OLCULEMEDI** ("1 urunun sayfasi yok") cunku
dal agacindaki `build.py` kosumu tur icinde bitmedi; kardes kapilar da OLCULEMEDI. **Kapi yesil
olculmeden merge YOK** — bu ayni zamanda dogru fail-closed davranis, arıza degil. Dal itilmedi.

**🔧 TAMIRCI TURU.** Acik 🔧 = **13**; kapanan 0, **DAGITILAN 1 (K78, yeni)**, triyaj edilen 3.
Defter kusuru da onarildi: mail kalemi **K75 id'siyle acilmisti ve Okan'in marka-model-cipleri
kalemiyle CAKISIYORDU** → icerik degismeden **K77**'ye tasindi ("id yeniden kullanilmaz" kurali).
Olculen durumlar: **K56** HALA ACIK (bayraksiz kol rc=2, `--anahat` rc=0, ayni tautoloji iddiasi;
kanama CI'da YOK) · **K58** HALA ACIK (rc=1, `IDDIA=115 KIRMIZI=1`, ayni envanter drift ekseni) ·
**K62** UCUSTA ve KAPANMADI — kardes oturumun `tools/d1-sapma-mutasyon.py` degisikligi HALA
commit'siz (129 ekleme / 20 silme), kalemin iddiasi "HEAD'de bayat" ve HEAD henuz o dosyayi almadi ·
**K49** CANLI (agac 31 dk, 5 commit onde, `serit-b-beyan-mutasyon.py` uretiliyor) — dokunulmadi.

**Bu turda:** urun verisine DOKUNULMADI · deploy elle YAPILMADI · kosum rerun/cancel EDILMEDI ·
mail betigi YAZILMADI/DUZENLENMEDI · Cop BOSALTILMADI, hicbir mail geri ALINMADI · kapi/nobetci
GEVSETILMEDI · yabanci ` M`/`??` dosyalara DOKUNULMADI · CANLI agaclara YAZILMADI · **merge
YAPILMADI** · dal SILINMEDI. Okan'a CIKILMADI (insan karari gerekmedi; §5).

**Sonraki turun ILK ISI:** (a) K78 muhendisinin ciktisi — dustuyse bagimsiz curutucu, dusmediyse
mtime ile olum karari (K72 yordami); (b) K35/K36 dal agacinda `build.py` bitti mi, kapi rc=0 mi —
yesilse **merge-kapisi ile ayri tur**; (c) ucustaki dort kosumun conclusion'i JOB birimiyle;
(d) K62'nin commit'i indi mi (indiyse kalem KAPANIR).

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

**📏 WORKTREE — K72 ESIGI TUR ORTASINDA ASILDI, KARAR AYNI TURDA ALINDI.** Kabul olcutu (b) ilk kez
fiilen hukum verdi: tur basi mtime **85,0 dk** (CANLI, sinirda) → push kancasi **95,7 dk** → yeniden
olcum **97,4 dk** = **OLU**. Arsivle-sonra-kaldir sirasi zorunlu tutuldu ve 2. adim kritik cikti:
dal origin'de `7360354a` iken yerel `5a9f9353`'tu → **4 commit TEK NUSHADAYDI**; itilmeseydi
kaldirma kalici kayip olurdu (kanca temiz, `--force` KULLANILMADI, `ls-remote` ile bagimsiz teyit).
Commit'siz 22.674 baytlik yama arsivlendi, kabul **TEMIZ klon** uzerinde uretildi (`apply --check`
**rc=0**, sha256 birebir), ANCAK ONDAN SONRA agac kaldirildi. Dal SILINMEDI. KraL'in kendi agaci
artik **0**; listedeki dort agac baska oturumlarin CANLI iscisi (locked) → DOKUNULMADI.

**🔴 K70 DORDUNCU kez CANLI URETILDI — artik deterministik.** Bu turun defter commit'i `3c13caf1`
(mandat edilen pathspec bicimi) ayni ciktida: kardes kapi **"satir: 118"** okurken hedef kapi
**"stage'de 0 metin dosyasi tarandi"** dedi. Dort ardisik turun dordunde de ayni ikili → kenar
durum DEGIL, her pathspec commit'inde tekrarliyor; kabul bataryasi bunu fikstur almali.

**🔧 TAMIRCI TURU.** Acik 🔧 = **12**; kapanan 0, **DAGITILAN 1 (K49, 2. tur)**, triyaj edilen 3,
yeni acilan 1 (**K75**). K49 iade onarimi ayni turda yeniden dagitildi (spec
`.scratch/spec-k49-iade-onarimi-tur2.md`, MUHENDIS/Opus, izole agac; uc madde spec'te — ozet
GEREKCESI arsivdedir). "Ilk 15 dk'da WIP commit +
push" kurali spec'e BAGLAYICI yazildi — onceki **bes** iscinin hepsi tam bu adimi atlayip oldu.
Olculen durumlar:
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
  (12 Agu 09:37Z defter onarimi: bu kalem **K77**'ye tasindi, id cakismasi giderildi.)

**Bu turda:** urun verisine DOKUNULMADI · deploy elle YAPILMADI · kosum rerun/cancel EDILMEDI ·
mail betigi YAZILMADI/DUZENLENMEDI · Cop BOSALTILMADI, hicbir mail geri ALINMADI · kapi/nobetci
GEVSETILMEDI · yabanci ` M`/`??` dosyalara DOKUNULMADI · dort CANLI agacin hicbirine YAZILMADI ·
**merge YAPILMADI** · dal SILINMEDI. Okan'a **CIKILDI** (tek cumle, odeme ekseni — §0.5 geregi).

_Daha eski bloklarin TAM metni DEVAM-ARSIV.md dosyasindadir (kayipsiz tasindi)._
_Acik kalemlerin KAYNAK DOGRUSU: ~/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md_
