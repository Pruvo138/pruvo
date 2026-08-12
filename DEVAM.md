# DEVAM (KraL) — 8 Agu 2026

## 🔚 KraL — 12 Agu 2026 ~06:xxZ: MARKA SAYAC ESITLEMESI CANLIDA + K51/K52 kapandi

**CANLIYA GITTI — `5ecac404`** (dal `5832204d`). Kosum `31564809178`: `build`+`deploy`+`yayin`
**ucu de success**; ata kaniti `merge-base --is-ancestor` **rc=0**, negatif kontrol **rc=1**.

**Sorun (Okan ekrandan yakaladi, Hyundai yalnizca ORNEKTI):** marka sayfasi beyan ile baslikta
FARKLI sayi gosteriyordu — beyan `toplam`dan, baslik `basili = kalemler[:MARKA_KART_N]`
kapagindan turuyordu. Olculdu: **93 marka sayfasinin 35'i** yanlis rakam basiyordu, en buyuk
sapma **Ford 2582 ↔ 80**. Onarim marka-BAGIMSIZ tek noktada; Okan'in 8 Agu hukmu KORUNDU
(vaat 80'e cekilmedi, `MARKA_KART_N=80` duruyor, kalanina artimli erisim var).

**CANLI OLCUM, cache-bust'SIZ** — kapsamsiz: Hyundai **593/593** · Ford **2582/2582** ·
BMW **2349/2349** · Fiat **475/475** · Renault **831/831** → sapan **0/5**.
`?kategori=` kolu (istemci JS, tarayiciyla): Hyundai **575/575** · Ford **2579/2579** ·
BMW **628/628** · Fiat **475/475** → sapan **0/4**.

**Kapilar:** `marka-sayac-kapisi` rc=0 **21578/21578** · mutasyon **13/13 + kontrol 3/3,
ayrismayan 0** · `is-akisi-kapisi` merge oncesi ve sonrasi **rc=0** · `ci-kapsam` rc=0 ·
`marka-kapsam` 1437/1437 · `marka-model` 29/29 · `marka-artim` 26/26 · `kapi-envanteri` 7/7 ·
agac artigi **0** (SIGTERM'le yarida kesilse bile dosya sha256 birebir) ·
`d1-sync --durum` **5 eksen yesil, katalog 25.964** · kapsam ihlali YOK, sizinti 0.

**UC TUR CURUTME GEREKTI (birinci ve ikinci tur MERGE'U BLOKLADI):**
1. Dal, yayini durduran `is-akisi-kapisi`'ni **rc=1** yakiyordu (main rc=0 olculdu) ve
   `MUTANT=7/7` iddiasi repodaki surucuyle **yeniden uretilemiyordu** (rc=3, uc bayat capa).
2. 🔴 **Kapinin KENDI ozeti yalan soyluyordu:** ayni agacta ayni kosumda hukum
   `rc=1 · DUSEN=2379 · KIRMIZI` iken insana basilan ozet **"sapan marka 0"** diyordu —
   hukum `kapi.dusen`den, ozet AYRI bir kiyastan turuyordu.
3. Kapandi: ozet artik hukmu besleyen kumeden turuyor; merge-base jeneratoruyle
   `SAPAN_MARKA=93` ve `--dokum` marka satirlari **57+16+20 = 93** birebir esit.

**🔴 IKI TASINABILIR DERS:**
- **Beyan ile gosterilen ayri fonksiyondan turerse sessizce ayrisir** — ve bu tur olctu ki ayni
  hata kapinin KENDI icinde de vardi. Bir kapi insana sayi basiyorsa o sayi hukmu besleyen
  kumeden dogmali; yoksa kapi kirmiziyken "sapan 0" yazip isi kapattirir.
- **Mutanti `rc` ile degil, beklenen iddia ailesinin IZIYLE kabul et.** Tautoloji kirici mutant
  da rc=1 verir ama hedeflenen aile jetonunu TASIMAZ.

**K51 KAPANDI — merge `0eb8612b`.** D1 uzlastiricisinin SILME kolu karantinada. Ayirt edici
kanit: ayni fikstur **eski kodla `silinen=37`, yeni kodla `silinen=0`**; bayraksiz yol davranisi
BAYT AYNI, `eksik`/`hash` kollari dokunulmadi, alarm susturulmadi. Ders: silme kolu olan bir
emniyet aginda kabul testinin yesili YETMEZ — ayni fikstur ESKI kodla da kosulmali.

**K52 KAPANDI.** Zombi agac kaldirildi. Arsivleme adimi OLCUMLE gereksiz cikti
(`origin/main..c8b0451e` **0 satir**) — "arsivle-sonra-kaldir" bir ritüel degil KOSULDUR.

**KOSUYOR:** YOK (kendi dalim/worktree'm kalmadi). **Bu turda:** urun verisine DOKUNULMADI ·
deploy elle YAPILMADI · kosum rerun/cancel EDILMEDI · kapi/nobetci GEVSETILMEDI · yabanci
degisikliklere DOKUNULMADI · baskasinin worktree'sine DOKUNULMADI.

**Sonraki turun ISI:** (a) `git worktree list` **6 satir** (tavan 2) — ikisi main'de OLMAYAN
commit tasiyor (`kral/k49-d1-yazici-kilidi` · `kral/k70-index-kolu-pathspec`), ikisi de baska
oturumun CANLI isi, SILINMEZ; (b) K67/K68 karari (ikiz kapisinin 5. ekseni ortak araca tasinsin
mi + ortak isaret listesinin marka-notrlugu); (c) K61 SERIT B hala son tamamlanmis kosumda
`failure`.

## 🕐 CI NOBETI — 12 Agu 2026 08:37 yerel / 05:37Z turu (KraL / Tamirci)

**Ev kontrolu:** `pwd` = `git rev-parse --show-toplevel` = `/Users/okan/dev/pruvo` → DOGRU EV.

**🟢 SUPURME rc=0 — HUKUM=TEMIZ.** Sabit kosucu isciye kosturuldu; betik YAZILMADI/DUZENLENMEDI.
Basilan satirlar: `GITHUB_BILDIRIM_INBOX=0 · BULUNAN=0 · TASINAN=0 · ATLANAN=0 · CIKAN=0 ·
KOMSU_KAYIP=0 · KUME_DIFF=OLCULDU · KALAN=0 · COP_IZI=4:2026-08-12T04:05:51 · HUKUM=TEMIZ`.
Uc fail-closed alarmin ucu de sessiz; sayac 0 iken hukum TEMIZ yazilabildi cunku POZITIF tanima
izi var (aranan dizenin AYNISI Cop'te 4 kayit). **🟠 Cop denetimi: MESRU=4, YANLIS=0** — dordu de
`Run failed` bildirimi, siparis/odeme ekseninde kayit YOK. 11 Agu'nun "9. kayit" acik kalemi bu
turda `YANLIS=0` olctugu icin Okan'a SORULMADI.

**✅ CI TEMIZ — onarim GEREKMEDI.** Pencerede (03:37Z–05:37Z) basarisiz kosum **0**. En yeni
failure `31549865286` (00:20Z), uc tur oncesinden ve sinifi kapali.

**✅ GECEN TURUN ILK ISI (a) KAPANDI.** Ucustaki iki kosum JOB birimiyle olculdu:
`31562307000` → `build·serit-a2·serit-a3·serit-a4·deploy·yayin` **6/6 success**;
`31562307116` → 10 job success + 1 skipped, **failure 0**.

**🟡 UCUSTA — hukum YAZILMADI (ucustaki kosum yesil degildir).** `31564809377` (SERIT B,
`5ecac404`) hala `in_progress`, dusen job 0. Ayrica main tur ortasinda **kardes oturumla
`c906a864`e ilerledi**; `31567340921` (deploy) + `31567341105` (SERIT B) ucusta.

**📏 WORKTREE 6 → 5 satir — iki agac ARSIVLE-sonra-KALDIR yordamiyla dusuruldu.** Kaldirilanlar
K49'un 1. ve 2. dagitiminin OKSUZ agaclari: `agent-a8877112…` (3 dosya, 222 dk hareketsiz) ve
`agent-a8900e2a…` (5 dosya, 156 dk). Kabul sirayla olculdu: 8 dosya `/Users/okan/arsiv-worktree/`
altina sha256'li kopyalandi → **mimar dosyalari bagimsiz olarak ADIYLA gordu** → ancak ondan sonra
`--force` yetkilendirildi. Kayip riski SAYIYLA kapatildi: `d1-sync.py` diff genisligi
A=142 · B=388 satir, **canli K49 dali 431 satir** (ikisini de kapsiyor); `main..cc727e6a` **BOS**
(main disi commit 0 → bundle gerekmedi, K52 dersi uygulandi). KraL'in kendi agaci 1 (K69 iscisi).

**🔴 (b) MADDESI ACIK KALDI: K49 + K70 dallari origin'e HALA ITILMEDI** (`ls-remote --heads
origin` 0 isabet). Yerelde ikisi de commit tasiyor (K49 `7360354a` 3 commit · K70 `2c2e06e0`
1 commit) — kurtarma semasinin ikinci sarti uc turdur eksik.

**🔧 TAMIRCI TURU (§4.7).** Acik 🔧 = **10** (K49·K53·K54·K55·K56·K58·K59·K62·K69·K70); bu turda
kapanan 0, **DAGITILAN 1: K69** (spec `.scratch/spec-k69-devam-kapisi-envanter.md`, MUHENDIS/Opus,
izole agac, dal `kral/k69-devam-kapisi-envanter`). Kabul rc DEGIL IZ ekseninde: cagri satirini
SILEN mutant iki nobetciyi de KIRMIZI yakacak + kontrol kolu + kardes fikstur taramasi + kanca
pathspec biciminde davranissal kanit (K70 dersi). K58 premisi ayrica olculdu: `.scratch/`taki
yabanci taslak dosya HALA yerinde → kalem 🔧 kaliyor.

**Bu turda:** urun verisine DOKUNULMADI · deploy elle YAPILMADI · kosum rerun/cancel EDILMEDI ·
mail betigi YAZILMADI/DUZENLENMEDI · kapi/nobetci GEVSETILMEDI · yabanci ` M`/`??` dosyalara
DOKUNULMADI · baskasinin canli worktree'sine DOKUNULMADI · merge YAPILMADI.
Okan'a CIKILMADI (insan karari gerekmedi; §5).

**Sonraki turun ILK ISI:** (a) `31564809377` + `31567340921` + `31567341105` conclusion'i JOB
birimiyle; (b) K69 dagitimi ARTEFAKT uretti mi (`git worktree list` + agac diff ekseninden, dal
adindan DEGIL) ve dal origin'de mi; (c) K49 + K70 dallarinin itilme sarti (ucuncu tur eksik);
(d) kalan BAYAT agac `k62-dayanak` sahibi olculup yordama alinsin.

_Daha eski bloklarin TAM metni DEVAM-ARSIV.md dosyasindadir (kayipsiz tasindi)._
_Acik kalemlerin KAYNAK DOGRUSU: ~/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md_
