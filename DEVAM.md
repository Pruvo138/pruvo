# DEVAM (KraL) — 8 Agu 2026

## 13 Agu 2026 — YAYIN ZINCIRI KAPANDI (KraL)

**Deploy YESIL:** kosum `31632478625` success, headSha `07e01284` (SHA eslesmesiyle
dogrulandi, "son kosum yesildi" degil). Yayin gun boyu kapaliydi; alti kirmizi sirayla
olculup kapandi:
- **Model kanon D1** — uretim DOGRU, kirmizi yanan BAYAT AYNA. (d) jeton sahipligi +
  gurultu sinifi kollari aynaya tasindi; B7 sapmasi **39 -> 0**, mutasyon **12/12**.
- **FAZ3 bayrak** — iddia veri-bagimliydi ve uyelik ekseni KORDU (mutant yakalanmiyordu).
  Iddia sayfanin kanonik `aramaPlaniEsler` yuklemine baglandi, batarya **3/3**.
- **Ic rapor adi** — dalda `RAPOR-MIMARA.md` izleniyordu, izlemeden cikarildi.
- **build cokmesi** — 30 kayitta `fiyat` SAYI (`AttributeError: 'int' ... strip`).
  String'e cevrildi (deger degismedi) + `katalog-alan-kapisi.py`'ye TIP ekseni kuruldu
  (bos fiyat parametrik seri icin gecerli kalir, 23 kayit olculdu).
- **Marka invaryant** — IKIZ TANIM: filtre ham marka esitligi, sayfa+arama kanonik
  uyelik. Yuklem kanonik kaynaktan turetildi; kayip **7 -> 0**, taban **4 -> 0**
  (Volvo 109 dahil borc kapandi).
- **Cip indeks** — ayni sinifin AYNASI bayat kaldi (uretim kanonige gecmisti).
  Ayna uretim kaynagindan turetildi, **123/123**, mutant kirmizi.

**🔴 CI KAPSAM KAPISI YANLIS-POZITIFI KAPANDI (gunun en pahali sinifi).** Kapi push'un
ICERIGINI degil CALISMA AGACINI yarguluyordu: `git add` edilmemis YABANCI bir dosya
BASKASININ push'unu blokluyordu. Bugun **4 kez** oldu, ucu MaCiT'in urun partilerini +
KaaN'in commit'ini durdurdu. Kapsam artik pre-push'un verdigi ref/SHA araligindan
turuyor; aralik olculemezse ESKI KATI davranis (fail-closed). Kati kol mutasyonla
korundu, muafiyet listesine satir EKLENMEDI.

**Ayrica:** `duzelt.py` `tavsiyeFilament` alanini kabul ediyor (tip dogrulamali, 185
iddia) -> KaaN'in ASA tavsiyesi canliya indi (`a3d5cae1`). Kusurlu `--yeni-id` calismasi
(hal kapisi eski id ile cagriliyor + gizli kayitta hedef id kontrolu eksik) main'e
ALINMADI, yamasi arsivde. Worktree **4 -> 1** (bundle verify rc=0, 103+102 ref; dallar
SILINMEDI). K20 `son-zorunlu` kanit sha `cb35de6f` ile KAPALI.

**K82 M3 PILOTU KURULDU:** 4 cron nobeti MiniMax M3'e gecti (`MOTOR=minimax-m3`,
tur testi rc=0/18sn, sizinti 0). Kok neden Claude Code'un OAuth/keychain kimliginin
MiniMax anahtarini EZMESIYDI; cozum izole `CLAUDE_CONFIG_DIR` profili (kalici dizin,
700) + o cagrida OAuth jetonunun temizlenmesi. `--bare` SECILMEDI (nobetlerin arac
kabiliyetini kaybettirirdi). Geri donus kolu var: anahtar yok/bossa nobet Claude'a duser.

**SIRADAKI TEK IS:** BaBa'nin sirasindan ③ — K81 yayin kabulu (Codex iscisinden gelince
olc), sonra kalici-duzen kanit cevabi (3-serit -> korumali main -> merge kuyrugu).
## 🕐 CI NOBETI — 12 Agu 2026 23:37 yerel / 20:37Z turu (KraL / Tamirci)

**EV KONTROLU:** `/Users/okan/dev/pruvo` — dogru ev, tur olculdu.

**🟢 SUPURME TEMIZ (rc=0).** `GITHUB_BILDIRIM_INBOX=6 BULUNAN=6 TASINAN=6 ATLANAN=0 CIKAN=6
KOMSU_KAYIP=0 KUME_DIFF=OLCULDU KALAN=0 COP_IZI=6:2026-08-12T23:17:38 HUKUM=SUPURULDU`.
Uc fail-closed alarm da sessiz. Tasinan alti kayit da `notifications@github.com` + "Run failed".
Pozitif tanima izi VAR (`GITHUB_BILDIRIM_INBOX=6` = `BULUNAN`), yani hukum TEMIZ, OLCULEMEDI degil.
🟠 **COP DENETIMI: MESRU=6, YANLIS=1 — supurmeye ATFEDILEMEZ (besinci ardisik tur).** Tek YANLIS
kayit `dio` hesabinda bir reklam maili (GitHub-disi gonderen, supurme kapsaminin disinda);
muhasebe `CIKAN = TASINAN = 6` ile kapali ve `COP_IZI` (6) ile `MESRU` (6) birebir ortusuyor.
Kalem **K77** + **K84** zaten defterde acik; §5 olcutune gore Okan'a CIKILMADI.

**🟢 YAYIN ACILDI — gecen turun 8,5 saatlik tikanmasi COZULDU.** `Build & deploy` `31635409838`
(`a3d5cae1`): `build` · `serit-a2` · `serit-a3` · `serit-a4` · `deploy` · `yayin` **6/6 success**
(JOB birimiyle olculdu, kosum rengiyle degil). `serit-a2` onarimi `21f53a17` ile indi.

**🟢 D1 SENKRONU 5/5 YESIL** (`d1-sync.py --durum`): SAYI 26130=26130 · SEQ · SEMA · TURETILMIS
KOLON (5/5 GUNCEL) · ICERIK `hash UYUSMAZ=0 · EKSIK=0 · FAZLA=0`. Devir aninda kirmizi olan
(1/5 eksen) hal kapandi. `D1 uzlastirici` kosumu `31635926478` kirmizi yandi ama **tasarim
geregi gorunurluk alarmi**: `hash UYUSMAZ: 1` (mercedes-r129 tavsiyeFilament duzenlemesi) ->
onarim -> teyit `0` -> `b2087583`'te `31640204600` **success**. Sinif kalemi K85 acik kalir.

**🔴 KALAN TEK GERCEK KIRMIZI: SERIT B (yayini BLOKLAMAZ) — 3 batarya, 3 ayri kok.**
`31635410102` / `31632479053` ile olculdu: (a) `marka-sayfa-bataryasi` `K6_KAPSAMA_jeton_sahibi_
kolu_kapatildi -> KACTI`, `MUTANT=8/9 KONTROL=YESIL`, `IZ_AYRIMI=YANLIS`; (b) `marka-bolum-
bataryasi` `X4_TUMUNU_GOSTER_OLU HAYATTA KALDI (rc=1)`; (c) `model-baslik-bataryasi`
`ayirt-edilemeyen [[5, 7]]`. Yeni kalem **K86** acildi ve AYNI TURDA Codex'e DAGITILDI
(spec `.scratch/spec-serit-b-onarim-12agu2337.md`, ana agac, worktree YOK).
⏳ **TUR SONUNDA UCUSTA:** Codex ~30 dk'dir calisiyor ve uc kapiyi duzenledi
(`marka-cip-kapisi.py` · `marka-artim-test.py` · `model-baslik-kolu-test.py`), **henuz commit
YOK**. Sure siniri (§3.5 ~25 dk) doldugu icin surec OLDURULMEDI — oldurmek tam da
[[oksuz-commitsiz-onarim-curur]] sinifini uretirdi.
🔴 **SONRAKI TURUN ILK ISI:** (1) `git status` ile bu uc dosyanin commit'lenip commit'lenmedigini
ol; (2) commit'siz ve Codex olu ise onarimi SAHIPLEN (ortak altyapi = Tamirci'nin kalici onarim
yetkisi, §4.7); (3) yeni SERIT B kosumunda uc batarya job'unu **JOB birimiyle** dogrula ve
**mutant sayisinin DUSMEDIGINI** teyit et (gevsetme ile yesile boyama kontrolu).

**🟡 ODEME/PAKET BAYATLIK KIRMIZISI = ACIK KALEM K30, YENI ARIZA DEGIL.** `Odeme yolu bayatlik
nabzi` (`31635409818`) ve `Paket tazeligi alarmi` (`31634402709`) **ayni betigi** (`tools/
shop-bayatlik-kapisi.py`) cagiriyor ve **ayni tek kok nedeni** olcuyor: canli shop worker surumu
`751b14e9-…` (11 Agu 20:00Z), shop dizinine dokunan 2 commit yayinlanmamis, en eski **615,3 dk**
(esik 120 dk) -> `DURUM: BAYAT (rc=1)`. Tek kapanis yolu `wrangler deploy` = **OKAN KAPISI**;
Okan karari 11 Agu ~12:40 "BEKLETILIYOR" olarak zaten alinmis -> §5 geregi Okan'a TEKRAR
YAZILMADI. Ikisi de `deploy.yml` `needs:` zincirinde DEGIL, yayini durdurmuyor.

**🔧 TAMIRCI TURU:** defterde acik 🔧 **17** satir; bu turda **kapanan 1** (K81), **acilan 1**
(K86), **dagitilan 1** (K86 -> Codex). K81 kapanisi: gecen turdan kalan tek olculmemis olcut (2)
olculdu — taban kanonik kaynaktan turuyor (`mmb.marka_uyelikleri`/`kanon()`, D1 `marka_kanon` ile
ayni katlama) **ve asil kapanis tabani ICERIKSIZLESTIRMEK oldu**: `marka-invaryant-taban.json`
sayisal alanlari artik `{}` (sifir-tolerans iddiasi), yani parti basina bayatlayacak marka-basi
sayac envanteri KALMADI. Aksan ekseni sentetik fikstürle civilendi (`fx-citroen-aksan`) ve
katlamayi soken mutant (`M1 KATLAMAYI KAPAT`) kirmizi yakiyor. **Sinif dersi kalici yazildi:**
elle tutulan bir taban parti basina bayatliyorsa dogru onarim tabani otomatik TURETMEK degil,
tabani sayac envanterinden SIFIR-TOLERANS iddiasina cevirmektir -> [[envanter-drift-parti-basina]].

**⚠️ WORKTREE TAVANI ARTIK TEMIZ:** `git worktree list` **2 satir** (ana agac + `claude/
vigilant-mclean-f48729`), tavan 2 — gecen turun 4 satirlik asimi baska bir oturumca kapatilmis.

**Baskasinin calisma kopyasinda duran (DOKUNULMADI):** `tools/d1-sapma-mutasyon.py` +
`tools/d1-sapma-mutasyon-dayanak-kaniti.py` (K62) · `tools/fiyat-tipi-test.py` ·
`tools/paket-deploy-kritik-yol.md` · `.scratch/`. MaCiT tur icinde iki urun partisi indirdi
(`a3d5cae1`, `b2087583`), katalog 26130.

_Daha eski bloklarin TAM metni DEVAM-ARSIV.md dosyasindadir (kayipsiz tasindi)._
_Acik kalemlerin KAYNAK DOGRUSU: ~/.claude/projects/-Users-okan-dev-pruvo/memory/acik-kalemler.md_

## 12 Agu 2026 22:37Z — saatlik CI nobeti (Tamirci turu)
- EV=/Users/okan/dev/pruvo (dogru ev). SUPURME=ALARM rc=1: BULUNAN=5 TASINAN=4 ATLANAN=1 CIKAN=5 KOMSU_KAYIP=1 KUME_DIFF=OLCULDU KALAN=2 COP_IZI=52 HUKUM=OLCULEMEDI. Alarm goruldu, supurme TEKRAR KOSULMADI.
- Adli iz: yanlis silme ATFEDILEMEZ. Betik tam 4 delete komutu yayinladi (TASINAN=4), 5. hedef silme koluna hic girmedi (ATLANAN=1, kimlik cozulemedi); CIKAN=5 ile arasindaki 1 fazlalik KOMSU_KAYIP=1 ile birebir ortusuyor -> kutuyu kosum ortasinda BASKA bir el degistirdi. Silme yuklemi kimlik tabanli + 4 katli yeniden dogrulamali; ilgili kayit uc icerik yukleminin ucunde de duser.
- Cop denetimi OLCULEMEDI: supurme COP_IZI=52 olcmusken denetim betigi 35 dk sonra toplam 1 kayit bastigi icin sayim guvenilmez (yeni kalem K84).
- CI: yayin 11:01:38Z'den beri ~8,5 saat kapaliydi, bu turda ACILDI. Kosum 31632478625 (07e01284) ve 31633570309 (a4da15c6) ikisinde de serit-a2+serit-a3+serit-a4+build+deploy+yayin 6/6 success. serit-a3 GECTI=91 KALDI=0. Yayin ciktisi: YAYIN GECIKMESI 0, DEGISMEZ IHLALI 0, D1 26129 = canli 26129, katalog pozitif dogrulanan sayfa 10.
- Son main ucu a3d5cae1: DEPLOY=success (kosum 31635409838; build+serit-a2+serit-a3+serit-a4+deploy+yayin 6/6 success) SERIT_B=UCUSTA (kosum 31635410102; 12 dk tavaninda bitmedi, ara halde model-baslik-bataryasi + marka-sayfa-bataryasi failure, yayini BLOKLAMAZ).
- D1 uzlastirici 31635926478 (a3d5cae1) kirmizi ama TASARIM GEREGI gorunurluk kirmizisi: hash uyusmaz 1 -> onarildi -> teyit 26129/26129 birebir. Ayni urun ayni gun 2. kez sapti (yeni kalem K85).
- Yayin erisim alarmi kirmizisi BAYAT: kosum deploy bitmeden olctu; 3 ornek URL su an 200 donuyor (bilinen sinif K78).
- Odeme yolu bayatlik + paket tazeligi alarmlari ayni kok: canli odeme worker'i 11 Agu 20:00'den beri yayinlanmadi, en eski yayinlanmamis commit 615 dk (esik 120 dk), 2 commit bekliyor. Yayin karari OKAN/mimar kapisi -> Okan'a cikildi.
- Tamirci turu: acik kalem sayisi bu turdan once 12; bu turda ACILAN 3, KAPANAN 0. K81 durumu degismedi; ayrinti ARSIVDE.
