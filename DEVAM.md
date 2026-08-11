# DEVAM (KraL) — 8 Agu 2026

## 🕐 CI NOBETI — 11 Agu 2026 22:38 yerel / 19:38Z turu (KraL)

**Ev kontrolu:** `pwd` = `/Users/okan/dev/pruvo` → DOGRU EV.

**🟢 SUPURME rc=0 — HUKUM=SUPURULDU (askidan sonraki 2. temiz tur).** Sabit kosucu isciye
kosturuldu; betik YAZILMADI/DUZENLENMEDI. Betigin bastigi satirlar oldugu gibi:
`GITHUB_BILDIRIM_INBOX=5 · BULUNAN=5 · TASINAN=5 · ATLANAN=0 · CIKAN=5 · KOMSU_KAYIP=0 ·
KUME_DIFF=OLCULDU · KALAN=0 · COP_IZI=43:2026-08-11T22:31:53 · HUKUM=SUPURULDU`. Uc fail-closed
alarmin ucu de sessiz; tur sonu kutuda `Run failed` **0**.

**🟠 Cop denetimi (salt okuma, rc=0): 45 kayit — MESRU=42, YANLIS=3.** Ucu de onceki UC turdan
bilinen AYNI kalem (16:54, reklam-platformu bildirimi; id `68047/68048/68049`), sayi ARTMADI ve
bu turun kayitlarindan (`68134…68137`) KUCUK. **Siparis/odeme ekseninde Cop'te kayit YOK.**
Sinif karari Okan'da, cevap gelmedi → tekrar SORULMADI, kendiliginden geri alma YAPILMADI.

**✅ SUPURME DEFTERI TAMAMI TARANDI — "yanlis silme" iddiasi makineyle CURUTULDU.**
`mail-supurme.log` (6 Agu 18:17 → 11 Agu 19:38Z, **22 kosum**): `SILINEN_GITHUB_DISI=0` ·
`META_IZI=0` → betigin sildigi HICBIR kayit github+`Run failed` disinda degil, ve Cop'teki 3
yabanci kaydin defterde **hic izi yok**. `KOMSU_KAYIP` alarmi bugun 2 kez tuttu (16:39Z, 18:38Z);
her ikisinde de "hedef disi" kimlik **yine bir github check-suite kimligi** — yani alarm mesru
sinif icinde tuttu, yanlis sinif zarari **0**.

**🔴 CI: `deploy` KIRMIZI OLCULDU → ONARIM DELEGE EDILDI → ONARIM MAIN'DE.** `31527715768`
(`f4caf59f`) **FAILURE**, dusen adim `serit-a3 / Varlik ... kabul testi + mutasyon nobeti`
(`build` ve `serit-a4` success). Kok neden: N1 mutantinin capasi `min-width:210px` dizesine
kilitliydi, ayni commit o dizeyi kaldirinca capa 0 kez eslesti → mutant NO-OP → fail-closed
kirmizi. Onarim `c8b0451e` (**2 satir**, `tools/varlik-mutasyon.py`): capa yeni CSS'e tasindi,
mutasyon SINIFI korundu (`height:56px→57px`) — kapi gevsetilmedi, esik degismedi, adim silinmedi.
Yerelde varlik testi 10 eksen + mutasyon **8/8** rc=0. Karar kosumu **`31531089183`** (`c8b0451e`)
tur sonunda hala **UCUSTA** — yesil YAZILMAZ.

**✅ "Paket tazeligi alarmi" sinifi KENDILIGINDEN KAPANDI:** `31529488161` (19:45Z) **success**;
onceki kirmizisi (`31523722642`) "taranan 8 kosumda basarili `deploy` YOK" diyordu.

**✅ "Yayin erisim alarmi" kirmizisi (`31528157635`) GECICI CIKTI — canli KAYIP YOK.** Alarm 11
URL'i 404 olctu, ama uc bagimsiz ayak tersini gosterdi: (a) 404 gorulen sluglar `363a7e36`
(SEO wave-34) ile geldi ve o commit, **TAM YESIL** biten `31525687626`'nin (`c8460b17`) atasidir;
(b) uretim yolu ayrisMIYOR — `build.py` `CONTENT_PAGES` dongusu `/<slug>/index.html` uretiyor,
`deploy.yml` ayni dizini `_site`'a kopyaliyor, wave-33 karsi ornegi ayni yoldan 200; (c) **canli
yeniden yoklandi: `/slug/` 200 · `/slug.html` 404 · sitemap eslesmesi 1.** Alarm 19:30:01Z'de
kosmus, ilgili deploy 19:34:53–19:35:24Z'de tamamlanmis → alarm **yayin inmeden ~4 dk once eski
surumu** olctu. → `[[alarm-onarim-ucus-suresi]]` sinifinin yeni ornegi.
🔧 **ONERI (uygulanmadi, KraL kuyrugunda):** erisim alarmi, uygulanabilir deploy tamamlanmadan
hukum vermesin — o pencerede `KAPALI` degil **OLCULEMEDI** bassin.

**Bu turda:** urun verisine dokunulmadi · worktree ACILMADI · deploy elle YAPILMADI · yabanci
degisikliklere DOKUNULMADI (`d82c8874` sahibi tarafindan CI'a baglandi, kapsam kapisi blokaji
boylece kalkti). Codex'e 5 cagri (supurme+Cop · defter olcumu · alarm kimlik olcumu · 404 teshisi
· serit-a3 onarimi). Okan'a cikilmadi (rutin sonuc + zaten sorulmus soru).

**Sonraki turun ILK ISI:** (a) **`31531089183`'u JOB birimiyle kapat** (`build` VE `deploy`/`yayin`
success mi) — ucustaki kosum yesil DEGILDIR; (b) canliyi cache-bust'siz dogrula (11 SEO sayfasi +
katalog sayisi); (c) erisim-alarmi OLCULEMEDI onerisini spec'e cevir; (d) DEVREDILEN 1 (E10
kardes-depo kolu) serit karari KraL'da.

## 🕐 CI NOBETI — 12 Agu 2026 00:37 yerel / 11 Agu 21:37Z turu (KraL)

**Ev kontrolu:** `pwd` = `/Users/okan/dev/pruvo` → DOGRU EV.

**🟢 SUPURME rc=0 — HUKUM=SUPURULDU (askidan sonraki 3. temiz tur).** Sabit kosucu isciye
kosturuldu; betik YAZILMADI/DUZENLENMEDI. Betigin bastigi satirlar oldugu gibi:
`GITHUB_BILDIRIM_INBOX=5 · BULUNAN=5 · TASINAN=5 · ATLANAN=0 · CIKAN=5 · KOMSU_KAYIP=0 ·
KUME_DIFF=OLCULDU · KALAN=0 · COP_IZI=48:2026-08-11T23:34:00 · HUKUM=SUPURULDU`. Uc fail-closed
alarmin ucu de sessiz; tur sonu kutuda `Run failed` **0**. Silinen 5 kimligin 5'i de
`Pruvo138/pruvo/check-suites/…@github.com` bicimindeydi.

**🟠 Cop denetimi (salt okuma, rc=0): 51 kayit — MESRU=48, YANLIS=3.** Ucu de onceki DORT turdan
bilinen AYNI kalem (16:54, reklam-platformu bildirimi; id `68047/68048/68049`), sayi ARTMADI ve
bu turun kayitlarindan (`68147…68151`) KUCUK → bu turun supurmesine ATFEDILMEZ.
**Siparis/odeme ekseninde Cop'te kayit YOK.** Sinif karari Okan'da, cevap gelmedi → tekrar
SORULMADI, kendiliginden geri alma YAPILMADI.

**✅ DEVREDILEN (a) KAPANDI — serit-a3 sinifi JOB BIRIMIYLE YESIL.** Onceki tur `31531089183`'u
devretmisti; o kosum `cancelled` cikti (kuyruk davranisi, `cancel-in-progress: false` — ariza
DEGIL, §4.5). Karar kosumu **`31532757154`** (`9569da50`, c8b0451e'nin torunu) TAM YESIL:
`build` · `serit-a2` · `serit-a3` · `serit-a4` · **`deploy`** · **`yayin`** altisi da `success`;
dusen adim YOK. Yani N1 mutasyon capasi onarimi (`c8b0451e`) fiilen dogrulandi.

**🔴 YAYIN ACLIGI OLCULDU VE KAPANDI — alarm SAHTE DEGIL, DOGRUYDU.** `Paket tazeligi alarmi`
`31534175609` (`078e814a`) FAILURE; dusen job `yayin-nabzi`, adim "Olcum — yayin gecikmesi /
tikanma / aclik". Kok neden logdan: **en eski bekleyen commit 66 dk (esik 65 dk)**. Bagimsiz
teyit: son yesil deploy `31525687626` (`c8460b17`, 19:36:15Z) idi ve o gunden beri **9 commit**
yayina inmemisti. Aclik zincirin serit-a3'te durmasindan doguyordu; zincir 21:03:56Z'de
`31532757154` ile inince **kalan inmeyen commit 9 → 3**. Alarmin kendi olcumu bayat DEGILDI.
`tazelik` job'i ayni kosumda success — kirmizi yalniz nabiz kolundaydi.
⚠️ `paket-tazelik-alarmi.yml` + `deploy-aclik-kapisi.py` calisma agacinda BASKA bir oturumun
yarim isi; DOKUNULMADI, kapsam DEVRALINMADI.

**🔴 YENI SINIF — D1 UZLASTIRICI MESRU SATIR SILDI (onarim BU TURDA YAPILMADI, spec yazildi).**
`31532464176` (`c8b0451e`) FAILURE; dusen adimlar "Teyit — onarimdan sonra sapma SIFIR mi" +
"ONARILAMADI". Logdan alinti: `hash UYUSMAZ: 0 | D1'de EKSIK: 0 | D1'de FAZLA: 37` · `silinen: 37`
· `GERI-OKUMA DOGRULANDI` · `D1 urun sayisi: 25827` · `icerik ekseni (urun_hash): 25864 D1 satiri`.
Uzlastirici agaci uzak main ucuna tazeledi (25827) ama **D1 git'ten ILERIDEYDI** (25864) —
esZAMANLI bir urun partisinin D1'e yazip git push'u henuz inmemis 37 satirini "FAZLA" sayip
SILDI. `--bayatlik` kapisi dogru calisti ama YANLIS SORUYU sorar: agacin GIT'e gore bayatligini
olcer, D1'in agactan ILERI olmasini olcmez. Yeni desen degil (`31502177931`: `FAZLA: 41`, uc
tazelenince 0). Sapma su an KAPALI (salt-okuma 25864 = 25864) ve `D1 sapma alarmi` yesil.
📄 **Spec: `tools/paket-d1-uzlastirici-karantina.md`** — silme kolu KARANTINAYA alinir (ilk
gozlemde SILME YOK, ikinci gozlem FARKLI `origin/main` SHA'sinda ise silinir, damga okunamazsa
fail-closed `OLCULEMEDI`); `EKSIK`/`hash` kollari DEGISMEZ. **KAT: MUHENDIS (Opus)** — olcum +
veri silme = sessiz-hata sinifi, Codex'e VERILMEZ. Kabul: `uzlastirici-karantina-test.py` (K1-K7,
K7 = 11 Agu vakasinin birebir oynatimi, beklenen `silinen: 0`) + mutasyon bataryasi + kontrol
mutantlari + `cron-nabiz-kapisi.py --kendini-test`.

**Bu turda:** urun verisine dokunulmadi · deploy elle YAPILMADI · worktree ACILMADI · kod
degistirilmedi (yalniz `.md` spec'i) · yabanci degisikliklere DOKUNULMADI · kosum rerun/cancel
EDILMEDI · mail betigi YAZILMADI/DUZENLENMEDI. Codex'e 4 cagri (supurme+Cop · D1 teshisi ·
yayin nabzi teshisi · deploy zinciri bekleme). Okan'a cikilmadi (rutin sonuc + zaten sorulmus soru).

**Sonraki turun ILK ISI:** (a) `tools/paket-d1-uzlastirici-karantina.md` spec'ini MUHENDIS'e
(Opus) ver, dalda kapat; (b) `Paket tazeligi alarmi`nin bir sonraki kosumu yesil mi — aclik
gercekten kapandi mi (esik 65 dk, taban yayin ani); (c) canliyi cache-bust'siz dogrula
(`9569da50` icerigi indi mi); (d) DEVREDILEN 1 (E10 kardes-depo kolu) serit karari KraL'da.

_Daha eski bloklarin TAM metni DEVAM-ARSIV.md dosyasindadir (kayipsiz tasindi)._
_Acik kalemlerin KAYNAK DOGRUSU: ~/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md_
