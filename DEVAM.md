# DEVAM (KraL) — 8 Agu 2026

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

## 🧾 CTA DENGE TURU KAPANISI — 12 Agu 2026 / 11 Agu 21:xxZ (KraL merge turu, §6+§8)

**Kapsam:** yalnizca kapanis kapilari. Merge/push/temizlik ONCEKI turda inmisti; bu turda kod
DEGISTIRILMEDI, worktree ACILMADI, merge/push YAPILMADI, urun verisine DOKUNULMADI.

**Degisiklik (Okan'in 11 Agu karari):** yardim bandindaki WhatsApp hapinin etiketi artik HER
genislikte kisa — `.wa-uzun{display:none}` kurali `tools/build.py`'de mobil media blogundan
TEMEL CSS'e tasindi. Karsiliginda `.ikon-sepet`'teki `min-width:210px` CTA denge tabani
KALDIRILDI → "Sepete Ekle" masaustunde de gercek `width:fit-content`. Kanal, numaralar ve punto
karari DEGISMEDI; `index.html` DEGISMEDI.

**Muhendis commit'i `547bff87`, main tepesi `389ffdd5`.**

**Olculen sayilar:** masaustu CTA **155,8 × 56 = 8.725 px²** · hap **8.340 px²** · **oran 1,05**.
Mobil oran **1,24** — DEGISMEDI. Kapi rc'leri **6/6 yesil**. D1 **25905** = `urunler.json`
(hash uyusmaz 0 · eksik 0 · fazla 0).

**🟢 CANLI DOGRULAMA (§6) — TAZE.** Kanit kosumu **`31535741568`** (`8a31b85e`,
"Build & deploy to GitHub Pages") **success**; ata ekseni `merge-base --is-ancestor 547bff87
8a31b85e` → **rc=0**. "En son kosum yesildi" DENMEDI: main tepesi `389ffdd5`'in kendi deploy
kosumu (`31538073387`) tur sirasinda **UCUSTA** (queued/in_progress) — yesil YAZILMAZ, ve zaten
karar kosumu o degil. Olcum kanonik adresten, **cache-bust'SIZ**
(`/urun/audi-a6-c4-telefon-tutucu-iphone-13-14-15-pro-max/` → varlik
`/varlik/sayfa-f8805d4f24.css`, 16.367 bayt). Iki eksen AYRI AYRI:
- **EKSEN-1** `min-width:210px` → canli CSS'te **0 vurus** (sayfa ici `<style>` bloklarinda da 0).
  Canli kural artik `.ikon-sepet{flex:none}` — denge tabani YOK.
- **EKSEN-2** `.wa-uzun{display:none}` → **media sorgusu DISINDA**, temel CSS'te (yuvalanma
  olculdu: aktif `@media` YOK).
Katalogun EN YENI urunu (`389ffdd5` partisi) canlida henuz **404** — bu bekleniyor, o partinin
deploy'u ucusta; CTA ekseni acisindan anlamsiz.

**⚠️ GENISLIK TOLERANSI NOTU — bu turun tasinabilir dersi.** Masaustunde elde kalan pay
**~%5 (~7 px)**. (Bu bir YERLESIM toleransidir, ticari bir buyuklukle ilgisi YOKTUR.) Hap etiketi bir
kelime uzarsa **CTA-A1 kirmizi yanar**. Yani etiket METNI artik dengeyi tasiyan bir DEGISKENDIR:
denge sabit bir taban (`min-width`) tarafindan degil, iki kutunun gercek metin genisligi
tarafindan kuruluyor. Bandi daraltan her metin degisikligi (pazarlama dahil) kapi ekseniyle
birlikte dusunulmeli.

**Bu turda:** kod degistirilmedi · deploy elle YAPILMADI · kosum rerun/cancel EDILMEDI · yabanci
degisiklikler (`paket-tazelik-alarmi.yml`, `deploy-aclik-kapisi.py`, `.scratch/`,
`paket-deploy-kritik-yol.md`) BASKA OTURUMUN isi, DOKUNULMADI/commit'lenMEDI.

**Sonraki turun ILK ISI:** (a) `31538073387` ucustaki kosumu JOB birimiyle kapat (`deploy`+`yayin`
success mi) ve `389ffdd5` partisinin urun sayfalari canliya indi mi — 404 kapandi mi;
(b) CTA genislik toleransi notunu kapi tarafina bagla (etiket uzunlugu degisince CTA-A1'i
uyaran eksen).

_Daha eski bloklarin TAM metni DEVAM-ARSIV.md dosyasindadir (kayipsiz tasindi)._
_Acik kalemlerin KAYNAK DOGRUSU: ~/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md_
