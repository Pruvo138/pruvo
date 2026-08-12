# DEVAM (KraL) — 8 Agu 2026

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

## 🕐 CI NOBETI — 12 Agu 2026 09:37 yerel / 06:37Z turu (KraL / Tamirci)

**Ev kontrolu:** calisma dizini `/Users/okan/dev/pruvo` → DOGRU EV.

**🟢 SUPURME rc=0 — HUKUM=TEMIZ.** Sabit kosucu isciye kosturuldu; betik YAZILMADI/DUZENLENMEDI.
Basilan satirlar: `GITHUB_BILDIRIM_INBOX=0 · BULUNAN=0 · TASINAN=0 · ATLANAN=0 · CIKAN=0 ·
KOMSU_KAYIP=0 · KUME_DIFF=OLCULDU · KALAN=0 · COP_IZI=4:2026-08-12T04:05:51 · HUKUM=TEMIZ`.
Uc fail-closed alarmin ucu de sessiz; sayac 0 iken hukum TEMIZ yazilabildi cunku POZITIF tanima
izi var (aranan dizenin AYNISI Cop'te 4 kayit, en yenisi 04:05).

**🟠 COP DENETIMI: MESRU=4, YANLIS=2 — SUPURMEYE ATFEDILMEZ (uc bagimsiz iz).** Iki kayit ayni
bulten mailinin kopyasi (09:01 yerel, siparis/odeme mailleri DEGIL; siparis ekseninde Cop'te kayit
YOK). (a) Bu turun supurmesi `CIKAN=0` — gelen kutusundan hicbir kayit ayrilmadi; (b) tek silme
yolunun yuklemi `notifications@github.com` + `Run failed`; bulten ikisini de saglamiyor, dolayisiyla
o yolun uretebilecegi bir kayit degil; (c) kayit id'leri en yeni mesru kayittan BUYUK ve zamani
onceki turun `YANLIS=0` olcumunden SONRA. Kendiliginden geri ALINMADI — Okan'a TEK cumle cikildi.

**✅ CI TEMIZ — onarim GEREKMEDI.** Son ~25 kosumda `conclusion=failure` **0**. Gecen turdan
devreden uc kosum JOB birimiyle kapandi: `31564809377` 12 job (11 success + 1 skipped) ·
`31567340921` `build·serit-a2·serit-a3·serit-a4·deploy·yayin` **6/6 success** · `31567341105`
**cancelled, jobs:[]** — 4.5 maddesindeki kuyruk davranisi, ARIZA DEGIL: ayni head `c906a864`
kardes kosumda tam yesil ve main tepesinin atasi, icerik kaybolmadi.

**📏 WORKTREE 5 → 2 SATIR — TAVAN SAGLANDI.** Dort agac arsivle-sonra-kaldir yordamiyla dusuruldu,
hicbiri once silinmedi. Sira ZORUNLU tutuldu: (1) origin'de olmayan commit sayisi 0 olarak olculdu,
(2) calisma agaci yamasi + izlenmeyen dosyalar `/Users/okan/arsiv-worktree/` altina kopyalandi,
(3) her yama temiz HEAD blobu uzerinde yeniden uretilip **sha256 birebir** gosterildi, ANCAK
ONDAN SONRA kaldirma yetkilendirildi. Toplam arsiv: 4 yama (1714 + 25.379 + 12.085 bayt + bos) +
1 izlenmeyen dosya. Ana agactaki YABANCI degisiklikler tur basi ve tur sonu BIREBIR ayni.
⚠️ Isci ilk denemede `apply --check`i KIRLI agaca kosup sahte kirmizi aldi (agac zaten yamanin
SONRA-goruntusunu tasiyor); yontemi temiz HEAD blobuna cevirip kaniti oyle uretti.

**🔴 GECEN TURUN (b) MADDESI KAPANDI: K49 + K70 dallari origin'e ITILDI** (uc turdur eksikti).
Kanca ikisinde de `temiz: 0 bulgu` verdi, kanca ATLANMADI. Teyit `ls-remote --heads` ile bagimsiz:
`7360354a` ve `2c2e06e0` — yereldeki HEAD'lerle ayni.

**🔧 TAMIRCI TURU.** Acik 🔧 = **11** (K49·K53·K54·K55·K56·K58·K59·K62·K69·K70 + yeni **K71**);
bu turda kapanan 0, **DAGITILAN 1** (K49 iade onarimi). Olculen durumlar:
- **K49 — isci BITIRDI, bagimsiz CURUTUCU kostu, hukum `CURUTME=KALDI`.** Beyan edilen 8 sayinin
  8'i de yeniden uretildi (sapma yok) **ama raporun kabul bolumu BOS birakilmisti** — sayilar
  dogruydu, kaniti yoktu. Kapsam deligi kapandi=EVET, GERCEK kanca biciminde olculdu. **5 iade
  maddesi, 2'si bloklayici:** dal `is-akisi-kapisi.py`'yi **rc=1** yakiyor (main rc=0) ve raporun
  "iki BLOKLAYICI adim" iddiasi olcumle curudu (`serit-b`'nin `needs:`'i yok → yayini durdurmaz;
  olculen sure 137 sn, beyan "≈4 dk"). Onarim AYNI TURDA dagitildi; mimar karari: adimlar
  `serit-b`'de KALIR ve beyan tablosuna kaydedilir — koruma kilidin KENDISI, bu adimlar onun TESTI.
- **K71 ACILDI (yeni).** Curutucu `gh run view` ile olctu: kayitli zarar olaylarinin ikisi
  GitHub KOSUCUSUNDA `event=schedule` ile kostu; kilit TEK MAKINE kapsamli → kosucu×kosucu ve
  kosucu×yerel yarisi ACIK. **K49 bu dal alinsa bile KAPANMAZ.** Ders: bir emniyet aginin kapsam
  BIRIMI, zararin olculdugu birimle ayni mi diye sorulmali; "kapi yesil" ile "olculen zarar
  kapandi" AYRI iddialardir.
- **K70 — isci OLDU (138 dk hareketsiz, rapor uretmedi).** Tek WIP commit'i itildi, commit'siz
  yamasi arsivlendi; sonraki tur sifirdan degil bu WIP'ten devralacak.
- **K62 — bayat agac kapandi:** main disi commit **0** ve kirli iki dosyanin ANA AGACTA sha256
  BIREBIR AYNISI var → is ana agacta suruyor, agac mukerrerdi. Arsivlendi ve kaldirildi.
- **K69 — CANLI** (agac 45 dk once dokunulmus, dal origin'de); dokunulmadi.

**Bu turda:** urun verisine DOKUNULMADI · deploy elle YAPILMADI · kosum rerun/cancel EDILMEDI ·
mail betigi YAZILMADI/DUZENLENMEDI · kapi/nobetci GEVSETILMEDI · yabanci ` M`/`??` dosyalara
DOKUNULMADI · K69'un canli agacina DOKUNULMADI · **merge YAPILMADI** · dal SILINMEDI.

**Sonraki turun ILK ISI:** (a) K49 iade onariminin artefakti (`git worktree list` + agac diff
ekseninden, dal adindan DEGIL) ve `is-akisi-kapisi` dal rc'sinin main ile ESITLENDIGI; (b) K49
dali temizse merge kapisi ile ayri tur — **K49 satiri yine de KAPANMAZ, K71 acik kalir**;
(c) K69 dagitiminin sonucu; (d) K70'in WIP'inden devir.
_Daha eski bloklarin TAM metni DEVAM-ARSIV.md dosyasindadir (kayipsiz tasindi)._
_Acik kalemlerin KAYNAK DOGRUSU: ~/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md_
