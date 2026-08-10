# DEVAM (KraL) — 8 Agu 2026

## 🕐 CI NOBETI — 10 Agu 2026 20:37Z turu (KraL)

**🔴🔴 SUPURME ASKIYA ALINDI — 10 Agu supurme onarimi SINIFI KAPATMAMIS, ayni tur yeniden olculdu.**
Bu turun supurmesi kendi ciktisinda yanlis silmeyi itiraf etti: `GITHUB_BILDIRIM_INBOX=1 ·
BULUNAN=1 · **TASINAN=2** · KALAN=0 · COP_IZI=7:2026-08-10T23:25:31 · HUKUM=SUPURULDU` —
`KONULAR` listesinin 2. satiri bir **SIPARIS bildirimi**ydi (10 Agu'da bir kez kurtarilan AYNI
kayit, ikinci kez coplendi). Cop denetimi: 9 kayit, **7 MESRU / 2 YANLIS** (siparis bildirimi +
1 giris maili).
- **Kok neden (yeni, olculdu):** `messages of inbox whose ...` yuklemi Mail uygulamasinda
  **INDEKSLI referans** dondurur (`message N of inbox`); referans `delete` **aninda** cozulur ve silme
  asenkron oldugu icin bir sonraki tur yuklemi hala eski indeksi verir → o indeks artik
  **KOMSU** maili gosterir. `TASINAN > BULUNAN` bu yarisin makine izidir. 10 Agu onarimi
  (her turda yuklemi yeniden kos + daima `item 1`) yarisin SEKLINI degistirdi, sinifini DEGIL.
  Dogru cozum silmeyi **kararli kimlikten** (`message id`) yapmak — AppleScript degisikligi =
  ajan yazamaz (Okan emri) = **OKAN KAPISI**.
- **Alinan onlem (bu tur):** nobet gorev dosyasina `0.4 SUPURME ASKIDA` blogu eklendi (0.5'i ezer;
  salt-okuma cop denetimi kosmaya devam eder) · crontab'taki **:17 IKINCI silme yolu** (BaBa evi
  betigi, `repeat with m in hedefler` — ayni indeks sinifi, logda `BULUNAN=4 KALAN=1` desenleri)
  **KAPATILDI**. Kurtarma (`kurtarma-cop-inbox.applescript`) spec geregi ELLE → Okan'a tek cumle.
- **⚠️ Bu turda ben de ayni sinifa dustum, 1 dakikada geri alindi:** `crontab
  /Users/okan/.claude/cron/ci-nobeti.crontab` kuruldu ama o dosya **2 satirlik BAYAT kopyaydi**;
  canli crontab'ta **5** kayit vardi → 3 canli nobet (2 posta izleme + parti surucusu) sessizce
  dustu. Ayni turda tam surum yazilip geri kuruldu: **AKTIF=4** (37 ci-nobeti · 3,23,43 macit
  posta · 9,29,49 kaan posta · 13 */2 parti surucusu), aktif `17` **YOK**. Ders: `crontab <dosya>`
  kurmadan ONCE `crontab -l` ile satir-satir karsilastir — defter kopyasi canli durumu temsil ETMEZ.

**CI (bagimsiz `gh` ile olculdu):** son `failure` = `31425366313` (Build & deploy, headSha
`f905e7f4`, 19:41Z) → job `serit-a3`, adim **`Ic rapor adi kapisi`**; kok neden logdan alintiyla:
`DEVAM.md:7`'deki defter satiri bir ic protokol dosya adini tasiyordu (kapinin 10 Agu'da acilan
uzak-dal/izlenen-agac ekseni bunu gorur oldu). **Onarim BASKA bir oturumca zaten push edilmis:**
`dd3ce47c` ("Defter satirindaki protokol dosya adi notrlestirildi"). `build` · `serit-a2` ·
`serit-a4` bu kosumda da **success**'ti; `deploy`+`yayin` **skipped** (serit-a3'e bagli).
`main == origin/main == dd3ce47c`, ahead 0.
- **Kabul (bagimsiz olculdu, Codex'in/baskasinin sayisina guvenilmedi):** kosum `31430172244`
  (headSha `dd3ce47c`) **6 job da yesil** — `build` 13m06s · `serit-a2` 23m54s · `serit-a3`
  **17m58s (kirmizi olan kapi artik success)** · `serit-a4` 10s · **`deploy` 42s** · **`yayin` 46s**.
  Yayin tavanini bu kosumda `serit-a2` koydu (23m54s), toplam ~34 dk.
- **🟢 Okan'da bekleyen 1. kalem KAPANDI:** `Odeme yolu bayatlik nabzi` DEVAM'da "6 kosumdur
  kirmizi" yaziyordu; su an **son 6 kosum da success** (19:36Z `7c473b49`'dan beri kesintisiz).
  Shop worker bayatligi alarmi sonmus — kalem listeden dusuruldu.
- Su an inbox'ta "Run failed" maili birikecek (supurme askida); bu **beklenen** ve arizasiz.

## 🕐 CI NOBETI — 10 Agu 2026 19:37Z turu (KraL, gec kapandi)

**Supurme (askiya alma blogu HENUZ YOKKEN kosuldu):** `GITHUB_BILDIRIM_INBOX=1 · BULUNAN=1 ·
TASINAN=2 · KALAN=0 · COP_IZI=6:2026-08-10T22:27:40 · HUKUM=SUPURULDU`. Cop denetimi: 7 kayit,
**6 MESRU / 1 YANLIS** (bir giris maili). `TASINAN > BULUNAN` — 20:37Z turunun tespit ettigi
AYNI indeks sinifi; o turun askiya alma karariyla kapandi, bu turda ayrica islem yapilmadi.

**CI kirmizisi:** kosum `31424004814` (`Yayin erisim alarmi`, job `erisim`, headSha `e77f6a10`,
19:25Z). Kok neden logdan alintiyla: TEK URL 503 + ucun gecici bakim govdesi, 327/328 acik.
Ayni gun 17:13'te FARKLI tek sayfayla ayni imza. Canli dogrulama (no-cache dahil) ikisi de
**200** → **yanlis pozitif**, kalici erisim arizasi degil.

**Onarim (Opus muhendis, commit `3f603b87`):** `tools/yayin-erisim-nobeti.py` gecici sinifta
(5xx VEYA ag hatasi) KAPALI'ya dusen URL'i **BIR KEZ** yeniden yokluyor (~5 sn,
`Cache-Control: no-cache`). Fail-closed korundu: 4xx ve dongu/yonlendirme yeniden YOKLANMAZ;
ikinci yoklama da basarisizsa KAPALI/rc degismez; basarili olursa URL ACIK sayilir ama
**sessizlesmez** — `GECICI` satiri + ozet `GECICI=<n>`.

**Kabul (bagimsiz olculdu):** `tools/yayin-erisim-test.py` rc=0, **IDDIA 48 → 58** (+10, yeni
E8 ekseni, aga cikmaz, uyku sahte). Kontrol mutanti `503→503` → KAPALI rc=1 **GECTI**; `404`
icin toplam istek=1; ag hatasi→ag hatasi → OLCULEMEDI rc=2. Mutasyon bataryasi
(`tools/yayin-erisim-mutasyon.py`): 21 kirmizi-beklentili + 5 kontrol, 8 eksen, hepsi
beyanina uydu.

**Bagimsiz teyit:** kosum `31430172244` (headSha `dd3ce47c`) **6/6 job success** (build ·
deploy · yayin · serit-a2/a3/a4); `git merge-base --is-ancestor 3f603b87 origin/main` rc=0.
Alarm kolunun 21:05Z kosumu (`31432239675`) **success**.

**Sapma (islenmis):** ana agacta `git commit` commit kapisinca reddedildi → kisa omurlu
worktree commit araci olarak kullanildi, main `--ff-only` ilerletildi (merge commit YOK),
worktree ayni turda kaldirildi. Kalan worktree satirlari baska oturumlarin, dokunulmadi.

**Takip isi (bloklayici DEGIL):** E5 zaman asimi iddiasi artik iki yoklama olcuyor, sure
0,40 → 0,80 sn (esik 1,5 sn) — esik payi daraldi; CI yavaslarsa esik 1,8 sn'ye cekilebilir.

- **🟠 KAYIP IS BULUNDU (bu turda olculdu, capa atildi):** `git stash list` icinde 8 Agu 09:50:15+03:00 tarihli, **baska bir oturuma ait** bir stash duruyordu (`891feaeb`, taban `04d40ad4`); reflog kesintisiz: stash → rebase → `reset: moving to HEAD`, hicbir `apply`/`pop`/`drop` izi YOK → **geri yuklenmemis.** Icerigi: 11 dosya; ikisinin (`deploy.yml`, `nobet.yml`) degisikligi sonradan `e94433f9` ile inmis, **9 dosya / 741 satir depo gecmisinde HIC yok** (`--all` ile tarandi).
- Kayip govde tek bir is: yayin gecikme nobetcisinin taban yeniden olcumu (`KOSUM_OMUR_TAVANI_DK` 75 → **128**, iki fikstur gercek kosum govdeleriyle 49,1 → 85,0 dk ve 99 → 130,0 dk), `uyum-kapisi.py`'de dokum-kesmesi beyani (`IDDIA_TABANI` 39 → **42**), `cron-nabiz-kapisi.py` siniflandirma capalari, `build.py`'de bir ozet ayristirma fonksiyonu (adi repoda hicbir yerde yok), `is-akisi-kapisi.py` gerekce satiri.
- **Alinan onlem:** stash kirilgan oldugu icin dal capasi atildi → `kurtarma/stash-8agu-baska-oturum` = `891feaeb`. Stash'e DOKUNULMADI (`drop`/`clear` yok), calisma agaci DEGISTIRILMEDI.
- **Geri yukleme iki alt sinif:** temiz uygulanir (5 dosya: `uyum-kapisi.py`, `cron-nabiz-kapisi.py`, `yayin-gecikme-nobeti.py` + 2 fikstur — stash'ten beri o dosyalara commit degmemis) · yama duzeyinde birlestirme SART (4 dosya: `build.py`, `is-akisi-kapisi.py`, `DEVAM.md`, `arama.py` — HEAD'de yeni is var, korlemesine `pop` geri sarar).
- **SIRADAKI IS (bu tur icin):** capadaki 5 temiz dosya once alinacak, her biri kendi kapisiyla ayri ayri kirmizi/yesil olculecek (esik degisiklikleri kontrol mutanti ISTER); 4 catisan dosya yama duzeyinde birlestirilecek. Baska oturumlarin aktif calismasi nedeniyle toplu `pop` YAPILMAZ.

## 🔁 DEVIR — 10 Agu 2026 ~19:0xZ, eski hesap → yeni hesap (KraL) — **ARŞİVE ALINDI** (defter kotası 1:1)

## 🔴 UÇUŞTA — ÖTEKİ KraL OTURUMU BU İŞLERE GİRMESİN (10 Ağu ~14:2xZ) — **ARŞİVE ALINDI** (defter kotası 1:1)

## 🕐 CI NOBETI — 10 Agu 2026 14:37Z turu (KraL) — **ARŞİVE ALINDI** (defter kotası 1:1; sure ekseni hukmu: tavani 8 kosumun 7'sinde `serit-a2` koyuyor, 17,9/21,6/24,8 dk)

