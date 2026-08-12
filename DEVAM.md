# DEVAM (KraL) — 8 Agu 2026

## 🔁 DEVIR — 12 Agu 2026 ~15:xxZ, eski hesap → yeni hesap (KraL)

**SIRADAKI TEK IS:** `kral/deploy-model-evreni` dalini bitirip main'e al — model evrenini TEK
kanonik kaynaktan turet, `serit-a2` "Model-kanon-D1-kolonu" ve `serit-a3` "FAZ3-bayrak"
kapilarini yesillendir; **yayin bu iki kapi yuzunden KAPALI.**

**Nerede kaldim:** Kosum `31595345905` **failure**; suclu `47b6734d` (marka model cipleri merge'u
— cip 1022→1060, kapsama %67,33→%68,56). Yerelde de kirmizi (`YERELDE=1`), yani CI'ya ozgu degil.
Kok neden: model evreni + aksan-normalize arama **iki yerde ayri tanimli** (ikiz tanim sinifi).
Bugun main'e inen ve **canliya INEMEYEN** isler: `47b6734d` cipler · `9e9635fb` ilan tutari
(kart ↔ yapisal veri 100 kat sapmasi duzeltildi: 30030 → 300) · `e5ecb4fb` vape 4 kayit cikarma.
🔴 **Kapsama GERI ALINARAK kapi susturulMAYACAK** — cip 1060 / %68,56 korunacak.

**Acik worktree/dal:**
- `kral/deploy-model-evreni` (worktree `agent-a3251270b98f7b14b`, **locked**) → yayin onarimi,
  UCUSTA; isciye "yarim da olsa commit'le ve PUSH et" denildi.
- `kral/k35-k36-site-kusurlari` (`f343b398`, origin'de, 8 commit ileri) → malzeme cipi + jenerator
  breadcrumb; **veri on-kosulu MaCiT tarafindan kapatildi** (`28ef3b43`), merge KraL kapisi, HAZIR.
- `kral/k49-d1-yazici-kilidi` · `kral/k78-yayin-erisim-evren-hizalama` → **baska oturumlarin CANLI
  isi**, worktree'leri kirli, DOKUNMA.
- `worktree-agent-a9306261f47df111b` (`c09c4c1c`) = K27, **MERGE EDILMEYECEK**: `shop/` odeme
  duzlemine dokunuyor + urun kaynak linki gizli kayittan turuyor (26.683 dolu kayit) → yalniz
  atif ZORUNLU (CC BY) kayitlarda cozulmeli, ucretli/uyelikli kaynakta ASLA.

**Baskasinin calisma kopyasinda duran:** `tools/d1-sapma-mutasyon.py` + `tools/d1-sapma-mutasyon-dayanak-kaniti.py`
(K62 isi) · `tools/paket-deploy-kritik-yol.md` · `.scratch/` · `urunler.json` + `tools/duzelt.py`
(vape cikarma iscisi UCUSTA, commit `e5ecb4fb` atildi ama is bitmedi).

**Zamanlanmis nobetler (yeni hesapta YENIDEN KURULACAK):** `gunluk-mimar-ihtar` (`0 15 * * *`) ·
`teftis-takip` (`0 17,23 * * *`) · `macit-parti-surucusu` (`0 */2 * * *`) ·
`pazar-mimar-optimizasyon` (`0 12 * * 0`) + crontab `37 * * * *` CI nobeti
(**`~/.claude/cron/.ci-token` OKAN KAPISI — tazelenmezse nobet sessizce olur**).

**Dal emniyeti (devir turu):** **9 dal itildi**, kurtarma etiketi uzakta **6**. Uzaksiz kalan
TEK dal `kurtarma/stash-8agu-baska-oturum` — **bilerek itilmedi**: pre-push sizinti kapisi
fail-closed `OLCULEMEDI` verdi (aday butcesi 1.657.912 > 150.000; itmenin menzili patolojik
genis). Kanca atlama bayragi KULLANILMADI. **Kayip YOK** — K33 yargisinda bu dalin icerigi davranis
ekseninde main'de dogrulanmisti (19/19 urun main'de, 128 girdi scratch artefakti).
⚠️ `main` uzaktan **1 commit ileride**: `d6a148af` (Alfa Romeo × Printables dilim-1, katalog
26065→26068) — MaCiT'in isi, sahibi itecek; diskte duruyor, kayip degil.
⚠️ Worktree tavani asik (**4**): ucunde main'de olmayan commit var (`agent-a3251270b98f7b14b` 1 ·
`agent-a3c810bd32146b6b5` 5 · `agent-a3dd92d91c2416ab6` 2) → **kaldirmadan once BUNDLE gerekir**;
ikisi baska oturumlarin CANLI isi.

**Okan'da bekleyen karar:** Yayin kapali iken beklenecek mi yoksa `47b6734d` revert edilip yayin
hemen acilacak mi — soruldu, cevap "sonra yap, once devir".

**⚠️ D1 SENKRONU DEVIR ANINDA KIRMIZI (`--durum` rc=1, 1/5 eksen).** Sebep bilinen ve BEKLENEN
ara hal: vape 4 kaydi katalogdan cikti (26069 → 26065) → o satirlar D1'de "fazla" gorundu ve
uzlastiricinin silme kolu **KARANTINADA** (ilk gozlemde SILMEZ, `0eb8612b`); ustune esmanli urun
partisi (`d6a148af`) geldi. **Yeni oturumun ISI: bir sonraki turda `d1-sync.py --durum` ile
yeniden olc** — hala 5/5 degilse gercek sapma vardir. YAZAN bayragi kor korune kosma (K49:
yazici kilidi hala YOK).

**Devir aninda hala kosan (yeni oturum bunlari OLU bulacak):** yayin onarimi
(`kral/deploy-model-evreni`, locked worktree) ve vape cikarma iscisi (`urunler.json` +
`tools/duzelt.py` calisma kopyasinda acik). Ikisi de diskte iz birakti; yeni oturum once
`git -C /Users/okan/dev/pruvo status --short` ile bunlari sahiplenmeli.

## 🕐 CI NOBETI — 12 Agu 2026 13:37 yerel / 10:37Z turu (KraL / Tamirci)

**🟠 COP DENETIMI: MESRU=3, YANLIS=8 — SUPURMEYE ATFEDILEMEZ (ucuncu ardisik tur).** Yeni
dusen dort kayit (68194-68197) da GitHub-disi (3× Meta reklam bildirimi 13:11, 1× Cloudflare
tanitim) ve kayit id'leri **bitisik blok** = tek elle-silme hareketinin imzasi. Uc bagimsiz iz:
(a) supurmenin `SILINENLER` listesi iki kaydi ADIYLA basiyor, ikisi de `notifications@github.com`
+ "Run failed"; (b) supurmenin Cop'e dusurdugu kayitlar **68199-68200**, yani dort YANLIS kayit
supurmeden ONCE Cop'teydi; (c) `CIKAN = TASINAN = 2`. Bu turun yeni kayitlarinda **siparis/odeme
maili YOK** → Okan'a **CIKILMADI** (§5 olcutu: yeni insan karari istemiyor; kalem **K77** zaten
defterde acik). Kendiliginden geri ALINMADI.

**✅ D1 SAPMASI KENDI KENDINE KAPANDI — onarim gerekmedi.** `D1 uzlastirici` kosumu
`31584719407` (09:50Z) gercekten kirmiziydi (`ONARILAMADI: sapma KAPANMADI`; ayrica ayni
kosumda `KARANTINA DAMGASI INDIRILEMEDI` → HTTP 401, `KARANTINA_HUKUM=OLCULEMEDI`, fail-closed
dogru davranis). Bagimsiz olcum (`d1-sync.py --durum`) **bes eksende de temiz**: SAYI 25968 ==
25968 · SEQ tam-sayi 0 sapma · SEMA 3 goc indeksi KURULU · TURETILMIS KOLON 5/5 GUNCEL ·
ICERIK `urun_hash` UYUSMAZ=0 EKSIK=0 FAZLA=0. Teyit ikinci eksenden: `D1 sapma alarmi`
kosumu `31588187458` (10:36Z) **success**. → sinif KAPALI, mail hakli olarak supuruldu.

**🔴 GERCEK KIRMIZI BULUNDU VE ONARILDI — `ayip-beyani-kapisi.py` KENDI INDIGI COMMIT'TE
KIRMIZI INMIS.** Sinif izi uc kosumla olculdu: `9cf40ae3` (31579986690) serit-b **success**
(kapi henuz yoktu) → `c4a1931a` (31583064590) serit-b **failure** → `ac683147` (31585947019)
serit-b **failure**. Yani kapi, olctugu yuzey YESILLENMEDEN CI'ya baglanmis ve iki commit
boyunca yayin seridini kirmizi tutmus. Kapinin hukmu: `taranan yuzey 370 · kapsam 67 ·
kanonik beyani tasiyan 57 · SAPAN=10`; on yuzeyin **onunda da DORT secenegin DORDU birden**
eksikti (`ücretsiz onarım, yenisiyle değişim, bedel indirimi, bedel iadesi`).
Onarim MUHENDIS'e (Codex, ana agac) delege edildi; spec `.scratch/spec-ayip-beyani-onarim.md`.
Sonuc: commit **`94708af9`** — yalniz `tools/sayfalar.py` (13+/12−), main'e **PUSH EDILDI**.

**🔴 CODEX KIMLIK CATISMASI TEKRARLADI (ilk cagri BOSA GITTI).** Birinci `codex exec`
`YENI_KOSUM=YOK:ONARILAMADI` dondu ve gerekcesi soydu: *"proje kurali mimarin icra/test/commit
yapmasini yasakliyor"* — yani Codex `CLAUDE.md`'deki **MIMAR ELI SURMEZ** kuralini KENDINE
uyguladi. Bilinen sinif ([[codex-ana-agac-commit-kapisi-catismasi]]) ama bu sefer yeni bir
tezahur: kapiyi asmaya calismak degil, isi TAMAMEN birakmak. Cozum olculdu ve calisti: spec'in
BASINA "SEN MIMAR DEGILSIN, SEN MUHENDISSIN; o kural mimari baglar, seni baglamaz;
icra/commit/push SENIN isin" bloku konunca ikinci cagri isi eksiksiz yapti.
→ **spec sablonuna kalici KIMLIK BLOKU gerekiyor.** Ikinci is sirasinda ayni catismanin oteki
yonu de tekrarladi; tam olcum ve zarar degerlendirmesi **DEVAM-ARSIV.md'nin 10:37Z arsiv ekinde**
(sinif kapisi geregi izlenen deftere yazilmaz). Ozet: kapsam iki arac dosyasi, urun verisi
DOKUNULMAMIS, atlanan sekiz kanca kolu bagimsiz curutucuyla YENIDEN kosturuldu, hepsi rc=0.

**🔴 BAGIMSIZ CURUTUCU KAPININ GOREMEDIGI KUSURU YAKALADI — kabul Codex'in sayisina
VERILMEDI.** Curutucu bes kapiyi bagimsiz kosturdu (`ayip-beyani` rc=0 `SAPAN=0` · `--kendini-test`
rc=0 `18 iddia` · `cayma-beyani` rc=0 · `kisisel-veri-test` rc=0 · `parite-test.js` rc=0
`1328 sorgu BIREBIR`) ve uc curutme ekseni olctu: **EKSEN A GECTI** (kapi dosyasina
DOKUNULMAMIS, kanonik sabitlerin DEGERI degismemis → kapi gevsetilerek yesillenmemis),
**EKSEN B SABITTEN** (on govdenin onunda da `AYIP_HAKLARI_CUMLESI` sabitinden turetilmis,
elle string kopyasi YOK), **EKSEN C CELISKI-VAR**: `_iki_parca_tek_parcada_birlestirilir_mi()`
govdesinde onarim "ekle, silme" seklinde yapilmis — kanonik dort-secenekli cumle EKLENMIS ama
hakki iki secenege daraltan eski kalip (*"ayipli bir urun ucretsiz onarilir ya da degistirilir"*)
yedi satir yukarida **HALA DURUYOR**. Ayni sayfa simdi kendisiyle celisiyor. Kapi bunu goremiyor
cunku yalniz "kanonik cumle VAR MI" diye bakiyor, celiskili kalibin YOKLUGUNU olcmuyor.
Curutucu ayrica kapinin TETIK kor noktasini buldu:
`_yuksek_tork_ve_burulma_tasiyan_plastik_parca_uretimi()` ayni dar kalibin varyantini tasiyor
ama "ayip"/"cayma hakki islemez" gecmedigi icin kapsama HIC girmiyor.
→ **SINIF DERSI: "kapi yesil" ile "metin dogru" ayri hukumlerdir.** Bir kapi VARLIK olcuyorsa
(X sayfada var mi), YOKLUK eksenini (X ile CELISEN Y sayfada duruyor mu) ayrica olcmelidir;
aksi halde "ekle, silmeyi unut" onariminin tamami yesil gecer. → [[kapi-beyanin-dogrulugunu-degil-varligini-olcer]] ailesi.

**✅ CELISKI ONARIMI AYNI TURDA DAGITILDI VE KAPANDI — commit `b01819b2`, PUSH EDILDI.** Spec
`.scratch/spec-ayip-celiski-onarimi.md` (MUHENDIS/Codex, ana agac) iki parca istedi ve ikisi de
indi: (1) dar/sartli kaliplar kaldirildi — `_iki_parca_tek_parcada_birlestirilir_mi()` govdesinden
dar cumle SILINDI, `_yuksek_tork_ve_burulma_tasiyan_plastik_parca_uretimi()` (kapinin KOR
NOKTASI) kanonik cumleye tasindi; (2) kapiya **CELISKI ekseni** eklendi.
Kapsam `tools/ayip-beyani-kapisi.py` (+34/−2) + `tools/sayfalar.py` (+2/−2), baska dosya YOK.
**Kabul isci raporundan DEGIL bagimsiz curutucudan alindi:** `KAPI_rc=0` · `KENDINI_TEST_rc=0`
**IDDIA=21** (taban 18 → +3, yeni fiksturun POZITIF izi) · `MUTASYON=KIRMIZI-YANDI` (eksen
sokulunce `OZ-TEST KIRMIZI: 2/21`, sonra geri alindi → tautoloji DEGIL) · `YENI_EKSEN=GERCEK`
(hem pozitif hem negatif fikstur kolu var) · `GEVSETME=YOK` (esik/kapsam/tetik degismedi, cikis
kodu semantigi 0/1/2 ve fail-closed korundu) · `KALAN_DAR_KALIP=0` · `DILBILGISI=SAGLAM`.

**⚠️ ACIK KALEM — KAPSAM DISI ICERIK KAYBI (curutucu yan bulgusu, sonraki tur yargilasin).**
`_iki_parca_tek_parcada_birlestirilir_mi()` govdesinde dar kalibin BITISIGINDEKI *"Bu kural boyut
uyumundan ayridir — ... duzeltmesi bize aittir."* cumlesi de kaldirilmis. O cumle spec'in hedefi
DEGILDI ve bir taahhut ifadesi tasiyordu → geri konmali mi, yoksa kanonik cumle onu zaten
kapsiyor mu, KraL duzleminde karara baglanacak. Yasal taban risk altinda DEGIL (6502 m.11'in dort
secenegi artik sayfada tam ve sartsiz duruyor).

**⏳ UCUSTA — hukum YAZILMADI.** `94708af9`'in SERIT B kosumu (`31590014957`) daha yeni push
gelince **cancelled** oldu (§4.5: beklenen kuyruk davranisi, icerik kaybolmaz). Tur sonunda
`b01819b2` uzerinde `31591212884` (SERIT B, `serit-b` job'i olculecek) **in_progress**,
`31591212631` (Build & deploy) `pending`. Ucustaki kosum yesil degildir. Kapinin YERELDE yesil
oldugu iki bagimsiz curutucuyla olculdu; **CI teyidi sonraki tura devrediliyor.**

**📏 WORKTREE.** `git worktree list` **7 satir** (ana agac + 6). KraL'in kendi agaclari: K78
(`agent-a3dd92d91c2416ab6`, `b3345e8c`), K49 (`agent-a3c810bd32146b6b5`), K35/K36
(`agent-a5a03b3247066386e`, `f343b398`) → tavan asildi ama hicbirine DOKUNULMADI: bu turun isi
ana agacta gecti ve agac dusurme icin arsivle-sonra-kaldir yordami (K72) tur icinde
kosturulamadi. Sonraki turun kalemi.

**🔧 TAMIRCI TURU.** Acik 🔧 = **14** (K80 yeni acildi); bu turda **KAPANAN 1** (ayip-beyani
kirmizisi: `SAPAN=10` → `SAPAN=0`, iki commit), **DAGITILAN 2** (ana kol + celiski/kor-nokta
kolu, ikisi de ayni turda indi), yeni acilan 2 (**K79** celiski ekseni — UCUSTA, **K80** kapinin
kendi commit'inde kirmizi inmesi — 🔧, onleyici kapi gerekiyor), triyaj edilen 3.
Olculen durumlar:
- **K78 — KANAMA DURDU ama YAPISAL ONARIM INMEDI.** `Yayin erisim alarmi` son kosumu
  `31587748288` (10:30Z) **success** → alarm kendi kendine yesillendi cunku deploy HEAD'i
  yakaladi; dal `kral/k78-yayin-erisim-evren-hizalama` (`b3345e8c`) origin'de duruyor ama
  main'e gore **2 onde / 3 geride**, merge EDILMEDI. Evren-hizalama kusuru duruyor → kalem ACIK.
- **K62 — HALA UCUSTA, KAPANMADI.** Kalemin iddiasi "HEAD'de bayat"; `tools/d1-sapma-mutasyon.py`
  bu turda da ` M` (commit'siz, kardes oturumun elinde) → HEAD henuz o degisikligi ALMADI.
- **K35/K36 — MERGE YAPILMADI.** Dal agaci `f343b398`, origin'deki dal `ba86fd84` ile ayrisik;
  kapi yesili tur icinde olculemedi (agac baska oturumun elinde, dokunulmadi).
- **K56 · K58 · K77** durumu degismedi; bu turda ayrica olculmedi (tur ayip-beyani kirmizisina
  harcandi — CI kirmizisi 🔧 triyajinin ONUNDEDIR).

**Bu turda:** urun verisine DOKUNULMADI · deploy elle YAPILMADI · kosum rerun/cancel EDILMEDI ·
mail betigi YAZILMADI/DUZENLENMEDI · Cop BOSALTILMADI, hicbir mail geri ALINMADI · kapi/nobetci
GEVSETILMEDI (kapi yalnizca GENISLETILMEK uzere dagitildi) · yabanci ` M`/`??` dosyalara
DOKUNULMADI · CANLI agaclara YAZILMADI · **merge YAPILMADI** · dal SILINMEDI.
Okan'a **CIKILMADI** (insan karari gerekmedi; §5).

**Sonraki turun ILK ISI:** (a) `31591212884` `serit-b` job'inin `conclusion`'i + `31591212631`
Build & deploy — kapinin CI teyidi (yerelde yesil, uzakta olculmedi);
(b) yukaridaki kapsam-disi icerik kaybi kalemi: cumle geri konsun mu;
(c) K78 dalinin merge kapisi (alarm yesil ama yapisal kusur duruyor);
(d) worktree tavani: KraL'in 3 agaci icin arsivle-sonra-kaldir;
(e) K80 (yeni acilan onleyici kalem: CI'ya YENI bloklayici adim ekleyen commit, o adimi kendi
agacinda kosup rc=0 almali) — dagitilacak.

_Daha eski bloklarin TAM metni DEVAM-ARSIV.md dosyasindadir (kayipsiz tasindi)._
_Acik kalemlerin KAYNAK DOGRUSU: ~/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md_
