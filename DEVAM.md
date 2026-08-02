# DEVAM (KraL) — 31 Tem 2026

Onceki ayrintili kayitlar DEVAM-ARSIV.md'de (git disi, lossless).

## MERGE — 2 Agu 2026 · Nobetci gecme olcutu fail-closed (yonet cerez mutasyon surucusu)

- **Merge SHA `1b643886`** (dal ucu `7fa6392c`, merge-base `9d8d0cf8`). Kapsam **2 dosya /
  +179 −29**: `tools/yonet-cerez-mutasyon.py` ve `shop/test/kabul.js` (kabul.js'te +12 satirin
  tamami yorum). `shop/src/yonet.js` diff **BOS** — kaynak davranisi degismedi, sha256 basta =
  sonda. `urunler.json` ve urun kaynak kaydi dokunulmadi. Cakisma yok; sizinti taramasi 0 vurus.
- **Olcut fail-closed:** taninmayan/eksik `olcut` degeri artik varsayilana DUSMEZ (kosum oncesi
  dogrulayici + tuketim yerinde varsayilan dal YOK). Bagimsiz curutucu **12 gecersiz-deger
  denemesinin 12'sini** kirmizi olctu; ayni sapma **eski surucude cikis 0** veriyordu.
  Deneme kumesinin dokumu DEVAM-ARSIV.md'de.
- **Kayit dagilimi (olculdu):** 28 kayit = **22 ESIT** (11 tek_eksen + 11 esit_kume) +
  **3 KAPSAR** (M6/M8/M9, kirmizi kumesi beyandan gercekten genis, gerekcesi kaydinda) +
  **3 kontrol**. Yeni kayit **M24/M25** (`/liste` kolunun iki cagri ordinali), her biri TEK kirmizi.
- **Oynaklik ekseni:** 67 kosumda (beyan sirasi + ters + karisik) oynak kayit **0**;
  IDDIA SAYISI hep **70** — yanlis-kirmizi riski sifir olculdu.
- **Kapilar DALIN worktree'sinde kosuldu, hepsi cikis 0:** `kabul.js --yonet-cerez`
  **70 gecti / 0 kaldi, IDDIA SAYISI 70** (dusmedi) · mutasyon surucusu **28 kayit, TUM MUTANTLAR
  YAKALANDI** · `--sema-paritesi` **2/2** · kisisel veri testi (272 sayfa / 437 izlenen dosya) ·
  CI kapsam kapisi (**161 kesfedilen / 125 kosan / 36 muaf**) · kapi envanteri **7/7**.
- **Parite KOSULMADI — olcerek:** diff'te `worker/`, arama yolu ve `urunler.json` **YOK**.
- **D1 teyidi (merge sonrasi):** urun **16874 = 16874**; sema ekseni temiz; icerik ekseni
  16874 satirda hash uyusmazlik / eksik / fazla **0**.
- **CI:** kendi SHA'sinin deploy kosumu `30746287431` escamanlilikla **cancelled**. SHA-kanitli
  yesil **ardil** kosum `30746642484` (headSha `e6254d30`; `merge-base --is-ancestor 1b643886
  e6254d30` cikis **0**) — kosum **completed/success**, **7 isin 7'si success**
  (envanter · serit-b · cron-nabzi · build · mesaj-nobeti · deploy · yayin); bloklayici
  **"Yonet anahtar/cerez kabul testi (admin giris kapisi — deterministik alt kume)"** adimi
  **success**. Ayrica `1b643886`
  headSha'li iki yardimci is akisi success (`30746394593`, `30746436977`).
- **Temizlik:** worktree kaldirildi; dal **yerel + uzak** silindi.
- **Kuyruk ayri oturumda kapatildi (surec olduruldu, durum kayboldu).** §6/§4/§7 ana checkout'ta
  guncel main (`d05c3662`) uzerinde YENIDEN olculdu: `kabul.js --yonet-cerez` **SONUC 70 gecti /
  0 kaldi, IDDIA SAYISI 70** (rc 0) · `yonet-cerez-mutasyon.py` **28 kayit, TUM MUTANTLAR
  YAKALANDI**, taban iddia 70, `yonet.js` sha256 basta = sonda (rc 0) · `kapi-envanteri.py`
  **7/7** (rc 0) · `ci-kapsam-test.py` **YESIL** (rc 0; bu kosumda **162 kesfedilen / 36 muaf** —
  ustteki 161 dalin worktree'sinde olculmustu, aradaki fark main'in ilerlemesi) · D1 **16874 =
  16874**, sema temiz, icerik ekseni 0/0/0. Zombi **YOK**: `worktree-agent-ad6c23c2a535991b1`
  ne worktree listesinde ne yerel ne uzak dalda var; `merge-base --is-ancestor 7fa6392c
  origin/main` cikis **0** ve M24/M25 kayitlari ana agactaki surucude MEVCUT.

**ACIK MADDELER — bu turda ONARILMADI, merge'i bloklamadi.** Ucu de tabandaki `431f60ec`'te de
vardi (regresyon degil) ve bu surucu `deploy.yml`'de kosmuyor (CI'da kosan sey
`kabul.js --yonet-cerez` alt kumesidir):
1. `MUTANTLAR` listesi **bos** birakilirsa surucu cikis 0 + "TUM MUTANTLAR YAKALANDI" basar —
   vakum yesili.
2. Bir mutant `beklenen=[]` ile "kontrol" diye kaydedilirse yesil gecer; tuketim yerindeki ikinci
   kapi kontrol kayitlarini kapsamiyor.
3. 🔴 **OLCULMEMIS EKSEN:** giris gecikmesi sabiti 250 → 0 (kaba kuvvet yavaslaticisi kalkar)
   alt kumede **SURVIVOR** — o eksenin bugun **hicbir iddiasi yok**.
4. Zamanlama yan-kanali (sabit-zamanli karsilastirmanin gercek sabit-zamanliligi) hala
   **OLCULMEDI** — beyan korundu, yeni eksen acilmadi.

## MERGE — 2 Agu 2026 · CI kapsam kapisi (opt-in alt kume + coklu is akisi tetigi)

- **Merge SHA `8559518f`** (dal `claude/cool-rhodes-92cdf1`, merge-base `ead0bcb6`).
  Kapsam **4 dosya / +2081 −30**: `tools/ci-kapsam-test.py`, `tools/yaml-oku.py`,
  `shop/test/kabul.js`, `.gitignore`. `deploy.yml` 0 satir; `urunler.json` ve
  urun kaynak kaydi dokunulmadi. Cakisma yok, sizinti taramasi 0 vurus.
- **Kapilar dalin worktree'sinde kosuldu (hepsi exit 0):** CI kapsam kapisi
  **161 kabul testi kesfedildi · 4 is akisi (3 otomatik / 1 elle) · 125 otomatikte kosuyor ·
  36 muaf · 2 beyan edilen alt kume (2/2 kapsandi) · 18 muaf alt kume**;
  `--kendini-test` 6 nobetci yesil (48 + 53 sentetik fikstur);
  kapi envanteri **7/7 VAR+BAGLI+NOBETTE**; gitignore kapisi temiz (267 uretilen dizin);
  shop kabul testi **28/28**, ic parite 300 (site) + 845 (Ege) birebir.
- **Bilinen sinir:** iki-kol YAML paritesi bu ortamda **OLCULEMEDI** (tek gercek kol vardi);
  sabit kumede sapma 0 olarak raporlandi, kume disi girdi ayri madde olarak duruyor.
- **D1 teyidi (merge sonrasi):** urun **16874 = 16874** (D1 == urunler.json benzersiz);
  sema ekseni temiz; icerik ekseni 16874 satirda hash uyusmazlik/eksik/fazla **0**.
- **CI:** koşum `30745372063` headSha `8559518f` **failure** — tek kirmizi adim
  "Varlik (ortak CSS/JS harici dosya) kabul testi". **Dalin degil:** ayni adim merge-base
  `ead0bcb6` kosumunda (merge'den ONCE) da kirmiziydi ve dal o kapinin dosyasina hic dokunmadi.
  Dalin kendi iki adimi ("CI kapsam kapisi" + "oz-nobetcileri") ayni kosumda **success**.
  Onarim baska bir oturumda `95d19364` ile main'e alindi; `8559518f` o SHA'nin **atasi**
  (`merge-base --is-ancestor` exit 0) ve ardil kosum `30745500956` **success** — 71 adimin
  hepsi yesil, varlik adimi dahil. SHA-kanitli yesil bu kosumdur.

## TABAN (yeniden olc, ezberleme)
Bu bolume SAYI YAZMA — gun icinde bayatliyor ve bayat sayi yanlis guven veriyor
(bugun olculdu: katalog tek oturumda 16589 -> 16672 hareket etti, elle tutulan agac
listesi de tutmuyordu). Tek dogruluk kaynagi kosulan komut:
- Katalog / D1: `python3 tools/d1-sync.py --durum`
- Calisma alani: `git -C /Users/okan/dev/pruvo worktree list`
- Kapilar: `python3 tools/durum.py`
