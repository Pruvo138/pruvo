# DEVAM (KraL) — 8 Agu 2026

## 🕐 CI NOBETI — 12 Agu 2026 01:37 yerel / 22:37Z turu (KraL / Tamirci)

**Ev kontrolu:** `pwd` = `git rev-parse --show-toplevel` = `/Users/okan/dev/pruvo` → DOGRU EV.

**🟢 SUPURME rc=0 — HUKUM=SUPURULDU.** Sabit kosucu isciye kosturuldu; betik
YAZILMADI/DUZENLENMEDI. Betigin bastigi satirlar:
`GITHUB_BILDIRIM_INBOX=3 · BULUNAN=3 · TASINAN=3 · ATLANAN=0 · CIKAN=3 · KOMSU_KAYIP=0 ·
KUME_DIFF=OLCULDU · KALAN=0 · COP_IZI=53:2026-08-12T01:24:44 · HUKUM=SUPURULDU`. Uc fail-closed
alarmin ucu de sessiz. Silinen 3 kimlik: `Build & deploy (2ebbd47)` · `Nobet seridi (0c4b279)` ·
`Build & deploy (389ffdd)` — ucu de `…/check-suites/…@github.com` bicimindeydi.

**🟠 Cop denetimi (salt okuma): 57 kayit — MESRU=53, YANLIS=4.** Bilinen 3 kaleme (16:54
reklam-platformu bildirimi, id `68047/68048/68049`) **DORDUNCUSU eklendi**: id `68158`, 15:55,
bir DMARC toplu raporu. Bu turun supurmesine **ATFEDILMEZ** — uc bagimsiz iz: (a) `68158` bu turun
kayitlarindan (`68162/68163/68164`) KUCUK, (b) turun muhasebesi `CIKAN = TASINAN = 3`, (c)
`KOMSU_KAYIP=0` (hedef kumesi disinda kimlik dusmedi). **Siparis/odeme ekseninde Cop'te kayit YOK**
→ para kaybi sinifi DEGIL. Soru zaten sorulmus, cevap gelmedi → tekrar SORULMADI, kendiliginden
geri alma YAPILMADI (§0.4).

**✅ DEVREDILEN (a) KAPANDI — YAYIN BLOKU ACILDI, JOB BIRIMIYLE YESIL.** Onceki turun devrettigi
iki kosum (`31540904335` + `31540904515`, `06c69180`) **`cancelled`** cikti = kuyruk davranisi,
ariza DEGIL (§4.5) → SHA'yi ata olarak tasiyan ardillari beklendi. Karar kosumu
**`31542119298`** (`9c56de08`) **TAM YESIL**: `build` · `serit-a2` · `serit-a3` · `serit-a4` ·
**`deploy`** · **`yayin`** ALTISI DA `success`; dusen adim YOK, `skipped` YOK.
**Yayin tabani artik main tepesinin kendisi** — inmemis commit kalmadi, aclik KAPANDI.

**✅ DEVREDILEN (c) KAPANDI — CANLI DOGRULAMA, CACHE-BUST'SIZ.** Ata ekseni: son basarili
deploy head'i `9c56de08` → `merge-base --is-ancestor <sha> origin/main` **rc=0**, **negatif
kontrol rc=1** (tautoloji degil). Katalog ekseni: **canli 25935 = yerel 25935 → ESIT** (MaCiT'in
Fiat×MakerWorld partisi canlida). ⚠️ Varlik ekseni **OLCULEMEDI** — spec ana sayfayi isaret etti,
oysa `/varlik/sayfa-<hash>.css` taşıyıcısı URUN sayfasi; yesil YAZILMADI, sonraki tura kaldi.

**🔴 YENI KIRMIZI — SERIT B `serit-b` job FAILURE (`31542119603`, `9c56de08`); yayini BLOKLAMAZ.**
Dusen adim bir mutasyon bataryasi; batarya **iki mutant sapmasi** raporladi. Teshis ve kabul
olcutu **acik kalem K61**'de durur (defter: `memory/acik-kalemler.md`, git DISI) — ayrinti
izlenen deftere YAZILMAZ. Codex'in hukmu **bagimsiz dogrulandi** (kendi `gh run view` olcumu:
`serit-b` = failure). Kok neden ONCEKI turun kapattigi oksuz-commit sinifi DEGIL → DUR kosulu
(3 kosum ayni kok neden) **tetiklenMEDI**. Onarim MUHENDIS'e (Opus, izole worktree) dagitildi;
gevsetme / mutant cikarma / beklenti degistirme YASAK olarak spec'e yazildi.

**🔧 TAMIRCI TURU (§4.7).** Defterde **8 acik 🔧** (K49·K53·K54·K55·K56·K58·K59 + bu turda acilan
**K61**); en eskisi K49 (11 Agu). Bu turda:
- **K51 DAGITILDI** (iki turdur devrediliyordu, sinif ikinci kez geldi → kalici kapi zorunlu):
  `tools/paket-d1-uzlastirici-karantina.md` spec'i MUHENDIS'e (Opus) verildi. Durum `UCUSTA`.
- **K56 TESHIS KAPANDI, onarim acik.** Kirmizi **bayat referans DEGIL, TAUTOLOJI**: c4 referansi
  `merge-base HEAD..origin/main` blobundan turuyor; ana agac main ucundayken referans == calisan
  dosya (ikisi de `9c56de08`, blob `d034eff4…`, **267.672 bayt ozdes**) → ayrisan bayt YOK → iddia
  olculemiyor → fail-closed rc=2. Sinif [[anahat-referans-tautolojisi]] (IKINCI vaka).
  🟢 **Kanama CI'da YOK:** `deploy.yml:1555` yalnizca `--anahat` kolunu kosuyor (rc=0), kancalarda
  cagri 0 → yayin riski YOK, oncelik dustu.
- **K61 ACILDI** (yukaridaki SERIT B deligi), onarimi ayni turda dagitildi.

**🧾 Defter kotasi 1:1 uygulandi.** `DEVAM.md` **171 → 64 satir / 4.502 bayt** (hedef 130/12.288'in
ALTINDA). Iki en eski blok (`00:37 turu` + `CTA DENGE KAPANISI`) `DEVAM-ARSIV.md`'ye **BAYT
BIREBIR** tasindi — kanit SHA-256 esitligi: `CI_BAYT=4473/1394eee7…`, `CTA_BAYT=3048/33f7fd44…`
kaynakta ve arsivde AYNI. Ozet YOK. `devam-sinif-kapisi.py` **rc=0** (113 satir tarandi).

**⏸️ PUSH BILEREK YAPILMADI — K49 sinifi CANLI olcuyle onlendi (commit `8d256c96` main'de bekliyor).**
Tur ortasinda `git status`'ta **`M urunler.json` BELIRDI** (90 satir / 5 urun) → kardes mimarin
partisi CANLI ([[canli-oturum-kaniti-git-status-farki]]). `d1-sync.py --durum` bunu dogruladi:
icerik ekseni **25940/25940 birebir** (hash uyusmaz 0 · eksik 0 · fazla 0) ama sayi ekseni
**D1=25935 degil 25940** ve **uc turetilmis kolon BAYAT** (`marka_kanon` 5 · `model_kanon` 2 ·
`marka_arama` 5) → parti **yazmanin ORTASINDA**. Push, pre-push kancasi araciligiyla **ikinci bir
D1 yazicisi** baslatirdi; K49 hala acik (yazici kilidi YOK). Bu turda bizi tesaduf degil **olcum**
korudu. Commit kaybolmaz; push sonraki turun ILK isidir (once `--durum` yeniden olculur).

**Bu turda:** urun verisine DOKUNULMADI · deploy elle YAPILMADI · kosum rerun/cancel EDILMEDI ·
mail betigi YAZILMADI/DUZENLENMEDI · kapi/nobetci GEVSETILMEDI · merge YAPILMADI · yabanci
`.scratch/` ve `tools/paket-deploy-kritik-yol.md` dosyalarina DOKUNULMADI · baskasinin
worktree'sine DOKUNULMADI. Codex'e 4 cagri (K56 teshisi · kosum bekleme · canli dogrulama · defter
kotasi), MUHENDIS'e 2 dal (K51 · K61). Okan'a CIKILMADI (rutin onarim + zaten sorulmus soru; §5).

**Sonraki turun ILK ISI:** (a) **`8d256c96`'yi PUSH ET** — once `d1-sync.py --durum` yeniden
olculur, kardes parti inmis/tamamlanmis olmali (sayi ekseni ve turetilmis kolonlar tazelenmis);
(b) iki MUHENDIS dalini **skill: merge-kapisi** ile tart (K51 karantina · K61 kapsam ayrimi) —
merge KraL'da, isci yalnizca dal push etti; (c) `31542119603`'un ardil kosumunda `serit-b`
yesillendi mi; (d) varlik eksenini URUN sayfasindan cache-bust'SIZ olc (bu turda OLCULEMEDI
kaldi); (e) K52 worktree tavani — `git worktree list` **4 satir**, ucu bu oturumun DEGIL,
ARSIVLE-sonra-kaldir.

## 🕐 CI NOBETI — 12 Agu 2026 01:0x yerel / 11 Agu 21:37Z turu — IKINCI OTURUM (KraL)

⚠️ **MUKERRER TUR:** asagidaki blok da "21:37Z turu" basligini tasiyor; ayni pencereyi iki
oturum bagimsiz kosmus. Bu blok GEC kosan oturumundur, olcumleri FARKLIDIR (o tur
`COP_IZI=48:23:34`, bu tur `COP_IZI=50:00:15`), ustune yazilmadi.

**Ev kontrolu:** `pwd` = `/Users/okan/dev/pruvo` → DOGRU EV.

**🟢 SUPURME rc=0 — HUKUM=SUPURULDU.** Sabit kosucu isciye kosturuldu; betik
YAZILMADI/DUZENLENMEDI. Betigin bastigi satirlar:
`GITHUB_BILDIRIM_INBOX=2 · BULUNAN=2 · TASINAN=2 · ATLANAN=0 · CIKAN=2 · KOMSU_KAYIP=0 ·
KUME_DIFF=OLCULDU · KALAN=0 · COP_IZI=50:2026-08-12T00:15:20 · HUKUM=SUPURULDU`. Uc fail-closed
alarmin ucu de sessiz. Silinen 2 kimlik: `Nöbet şeridi (9569da5)` + `Paket tazeligi (078e814)`.

**🟠 Cop denetimi (salt okuma, rc=0): 51 kayit — MESRU=48, YANLIS=3.** Ucu de bilinen AYNI kalem
(16:54, reklam-platformu bildirimi; id `68047/68048/68049`); sayi ARTMADI, bu turun kayitlarindan
(`68156/68157`) KUCUK → bu turun supurmesine ATFEDILMEZ. Siparis/odeme ekseninde Cop'te kayit YOK.
Soru zaten sorulmus, cevap gelmedi → tekrar SORULMADI, kendiliginden geri alma YAPILMADI.

**✅ ONARIM 1 — SERIT B'nin KOK NEDENI KAPANDI (oksuz commit sinifi).** `d82c8874` mutasyon
bataryasini CI'a bagladi (`nobet.yml` serit-b: `python3 tools/deploy-aclik-gh-mutasyon.py`) ama
bataryanin OLCTUGU uygulama (`GH_DENEME_TAVANI` / `_gecici_ag_hatasi` / `_gh_yeniden_deneme_testi`)
commit EDILMEMISTI — calisma agacinda oksuz duruyordu. Oldurulecek mutant olmayinca SERIT B
20:01Z'den beri kirmizi kaldi (son tamamlanan hukum `31532757456` failure). Onceki tur bu dosyalari
"baska oturumun yarim isi" diye BIRAKMISTI; oturum defterini kapatip gitmisti → [[oksuz-commitsiz-onarim-curur]].
Olcum ONCE yapildi: batarya **5 mutant + 1 kontrol, dusen=0, rc=0**; `--kendini-test` **42 iddia,
rc=0** (CI'da 20:05'te 30 iddia idi, +12). Dal `kral/serit-b-aclik-tamamla` (`0f4b5fdc`), ff-only
merge, push. Ana agactaki oksuz icerik dalin commit'iyle **BAYT-BAYT AYNI** oldugu dogrulandi
(59265 / 19450 bayt) → hicbir yabanci bayt degistirilmedi, stash/checkout/reset KULLANILMADI.
Esik GEVSETILMEDI: tukenince hukum hala fail-closed rc=2. **D1 teyidi: 25905, bes eksen de ✅.**
Worktree + dal ayni turda kapatildi.

**✅ ONARIM 2 — YAYIN BLOKU ACILDI (`Ic rapor adi kapisi`).** `31538073387` (`389ffdd5`) serit-a3
FAILURE, dusen adim "Ic rapor adi kapisi" → **`deploy` + `yayin` SKIPPED = yayin BLOKLU.** Kok neden
logdan alinti: `tools/paket-d1-uzlastirici-karantina.md:118` ic rapor dosya adini METINDE tasiyordu.
O spec'i onceki nobet turu yazmisti (`5c65142d`) → nobetcinin kendi belgesi yayini durdurdu
(ders hafizada kayitli). Onarim EN KUCUK olani: spec satiri anlamini koruyarak yeniden
yazildi (`06c69180`). **Kapi GEVSETILMEDI** — muafiyet listesine ekleme YOK, kapi betigine dokunulmadi,
adim silinmedi, `continue-on-error` eklenmedi.

**⏳ ACIK — IKI HUKUM UCUSTA, YESIL YAZILMADI ([[ucustaki-kosum-yesil-degildir]]).** Tur suresi
doldu; kosumlar bitmeden hukum verilmedi:
- `deploy.yml` **`31540904335`** (`06c69180`) — kabul: `build` + **`deploy`** + **`yayin`** ucu de
  `success`; `skipped` YESIL DEGILDIR.
- SERIT B **`31540904515`** (`06c69180`) — kabul: `serit-b` job `success`.
`cancelled` cikarsa ariza DEGIL (kuyruk davranisi, §4.5) → SHA'yi ata olarak tasiyan SONRAKI kosum
beklenir.

**Yayin tabani:** son YESIL deploy `31535741568` (`8a31b85e`, 20:59:56Z; build+deploy+yayin altisi
success). Ondan sonraki commit'ler yayina INMEDI — `06c69180` yesillenmezse aclik buyur.

**Bu turda:** urun verisine DOKUNULMADI · deploy elle YAPILMADI · kosum rerun/cancel EDILMEDI ·
mail betigi YAZILMADI/DUZENLENMEDI · kapi/nobetci GEVSETILMEDI · yabanci `.scratch/` ve
`tools/paket-deploy-kritik-yol.md` dosyalarina DOKUNULMADI · baskasinin worktree'sine DOKUNULMADI.
Okan'a CIKILMADI (rutin onarim + zaten sorulmus soru; §5).

**Sonraki turun ILK ISI:** (a) yukaridaki iki ucustaki kosumun `conclusion`'ini olc — `deploy`+`yayin`
`success` mi; degilse kok nedeni logdan alintila; (b) `tools/paket-d1-uzlastirici-karantina.md`
spec'i hala MUHENDIS'e (Opus) verilmedi, dalda kapatilmali; (c) canliyi cache-bust'SIZ dogrula.

_Daha eski bloklarin TAM metni DEVAM-ARSIV.md dosyasindadir (kayipsiz tasindi)._
_Acik kalemlerin KAYNAK DOGRUSU: ~/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md_
