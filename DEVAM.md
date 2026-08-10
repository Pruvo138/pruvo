# DEVAM (KraL) — 8 Agu 2026

## 🕐 CI NOBETI — 10 Agu 2026 23:37Z turu (KraL)

**Supurme (0.4 askisi KALKMIS halde ilk tam tur; sabit kosucu isciye kosturuldu):** rc=0 ·
`GITHUB_BILDIRIM_INBOX=0 · BULUNAN=0 · TASINAN=0 · ATLANAN=0 · CIKAN=0 · KOMSU_KAYIP=0 ·
KUME_DIFF=OLCULDU · KALAN=0 · COP_IZI=1:2026-08-11T01:25:38 · HUKUM=TEMIZ`. Uc fail-closed
alarmin ucu de sessiz. Inbox sayaci 0 iken hukum "OLCULEMEDI" degil **TEMIZ**, cunku pozitif
tanima izi Cop'ten geliyor: aranan dizenin AYNISI Cop'te 1 kayit tutuyor.
**Cop denetimi (salt okuma): 1 kayit, 1 MESRU / YANLIS=0** — ve o tek kayit, bu turun tek
kirmizisinin (`b150d01`) maili. Gorev dosyasi 0.4'teki acik kalem ("sonraki turda YANLIS=1
gorursen sor") boylece **KAPANDI**. Not: 21:37Z turunda 7 olan Cop kayit sayisi 1'e dusmus;
nobet Cop'u BOSALTMAZ, bu dusus nobete atfedilmez.

**CI (bagimsiz `gh` ile olculdu): acik kirmizi YOK, bu turda kod degisikligi YAPILMADI.**
- Son 60 kosumda tek `failure`: `31433971660` (Nöbet şeridi SERIT B, job `serit-b`, headSha
  `b150d013`, 21:27Z). Kok neden logdan alintiyla: `UZAK DAL KAPISI: OLCULEMEDI (fail-closed
  KIRMIZI)` → `Process completed with exit code 2`. Ayni kosumun diger eksenleri (V/A/K/W
  vakalari + mutasyon bataryalari) PASS'ti.
- **Sinifi KAPALI olculdu:** ayni workflow'un sonraki tamamlanan kosumu `31435535409`
  (`7cefc4a1`, 21:48Z) **10 job success** (`serit-b` dahil; `hacim-tam-takim` skipped), ve
  `git merge-base --is-ancestor b150d013 7cefc4a1` rc=0 → kirmizi head, yesil kosumun ATASI.
  Onarim baska oturumca zaten inmis (uzak dal kolu, `f5bb693a`). Gorev dosyasi 2. adim geregi
  duzeltme YAPILMADI.
- SERIT B **yayini BLOKLAMAZ**; yayin kolu ayrica `228f3661` head'inde `Build & deploy` success.
- Ucusta (ariza DEGIL): `cbe7e646` Build & deploy in_progress · `d7aca80e` Build & deploy +
  SERIT B pending. Aradaki `cancelled` SERIT B kayitlari 4.5 kurali geregi kuyruk davranisi.

**Devralinan acik kalemler (21:37Z blogunda yasiyor, HALA ACIK):** worktree tavani
(SAYI=3 TAVAN=2, iki oksuz agac) + `kurtarma/worktree-marka-katla-8c782ed1` capasinin yargisi ·
kayip is capasi `kurtarma/stash-8agu-baska-oturum` (`891feaeb`).

## 🕐 CI NOBETI — 10 Agu 2026 21:37Z turu (KraL)

**Supurme:** ASKIDA (indeks yarisi, Okan kapisi — gorev dosyasi 0.4). Bu turda hicbir mail
tasinmadi/silinmedi. **Cop denetimi** (salt okuma, isciye kosturuldu): **7 kayit, 7 MESRU /
YANLIS=0.** Onceki turun 2 YANLIS kaydi (siparis bildirimi + bir giris maili) artik Cop'te
DEGIL → kurtarma yapilmis; yanlis silme alarmi bu turda SONMUS.

**CI (bagimsiz `gh` ile olculdu): yayin zinciri YESIL, acik kirmizi YOK.**
- Pencerede (son ~70 dk) tek `failure`: `31428696466` (Build & deploy, headSha `dfb172f5`,
  20:22Z). **Sinifi KAPALI olculdu:** ayni workflow'un sonraki tamamlanan kosumu `31430172244`
  (`dd3ce47c`) **success**, ve `git merge-base --is-ancestor dfb172f5 dd3ce47c` rc=0 → kirmizi
  head yesil kosumun atasi. Onarim baska oturumca zaten inmis; bu turda kod degisikligi YOK.
- **Tur ici kabul (beklendi, beyana guvenilmedi):** kosum `31431548413` (headSha `fc22a9ba`)
  **6/6 job success** — `build` · `serit-a2` · `serit-a3` · `serit-a4` · **`deploy`** · **`yayin`**.
- `31433972063` (`b150d013`) **cancelled** — 4.5 kurali: kuyruk davranisi, ariza DEGIL. Icerik
  kaybi yok: `git merge-base --is-ancestor b150d013 b7f7e5b4` rc=0 → ucustaki `31434828201`
  (`b7f7e5b4`) o commit'i ata olarak tasiyor.
- Diger alarm kollari `b7f7e5b4` head'inde yesil (D1 sapma ×2, Odeme yolu bayatlik nabzi, spec
  alarm kolu). Inbox'ta "Run failed" birikmesi supurme askida oldugu icin BEKLENEN.

**🟠 WORKTREE TAVANI ASILDI — push kapisi olctu: SAYI=3 TAVAN=2, ikisi OKSUZ (178,9 dk ve
188,3 dk, ikisi de KIRLI=HAYIR).** `great-feynman-335110` main'de OLMAYAN **1 commit**
tasiyordu (`8c782ed1`, marka katlama ikiz-tanim ayrismasi + drift kapisi + 4 mutant kanit) →
**bu turda capa atildi:** `kurtarma/worktree-marka-katla-8c782ed1`. Worktree'ler SILINMEDI,
dokunulmadi. **SIRADAKI IS:** capadaki isi yargila (main'e mi, cop mu) ve iki oksuz agaci
arsivle-sonra-kaldir yordamiyla dusur — tavan yeniden 2 olsun.

**Devralinan acik kalem (19:37Z blogu defter kotasi 1:1 geregi arsive alindi, kalem BURADA
yasiyor):** kayip is capasi `kurtarma/stash-8agu-baska-oturum` (`891feaeb`) — 5 dosya temiz
uygulanir, 4 dosya yama duzeyinde birlestirme ister, toplu `pop` YAPILMAZ. ⚠️ Baska bir KraL
oturumu ayni pencerede (`b7f7e5b4`) bu isin olcumunu deftere isledi → **mukerrer tur riski**;
devralan TEK oturum olsun.

## 🕐 CI NOBETI — 10 Agu 2026 20:37Z turu (KraL) — **ARŞİVE ALINDI** (defter kotası 1:1; supurme aski karari + indeks sinifi kok nedeni + crontab bayat kopya dersi arsivde)

## 🕐 CI NOBETI — 10 Agu 2026 19:37Z turu (KraL, gec kapandi) — **ARŞİVE ALINDI** (defter kotası 1:1; acik kalem 21:37Z blogunda yasiyor)

## 🔁 DEVIR — 10 Agu 2026 ~19:0xZ, eski hesap → yeni hesap (KraL) — **ARŞİVE ALINDI** (defter kotası 1:1)

## 🔴 UÇUŞTA — ÖTEKİ KraL OTURUMU BU İŞLERE GİRMESİN (10 Ağu ~14:2xZ) — **ARŞİVE ALINDI** (defter kotası 1:1)

## 🕐 CI NOBETI — 10 Agu 2026 14:37Z turu (KraL) — **ARŞİVE ALINDI** (defter kotası 1:1; sure ekseni hukmu: tavani 8 kosumun 7'sinde `serit-a2` koyuyor, 17,9/21,6/24,8 dk)

