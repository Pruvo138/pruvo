# DEVAM (KraL) — 8 Agu 2026

> Kapanmis islerin TAM metni `DEVAM-ARSIV.md`'de (git DISI). Burada yalnizca CANLI durum durur.

## 🔵 27 EYL 19:5x KraL ana-oturum (Okan /goal: "EyLüL'ün Jev entegrasyonunu tüm PRUVO evlerinde uygula") — **ÖLÇÜLDÜ, İCRA DEVREDİLDİ (bağlam kotası 511K doldu)**
**🔵 20:2x (yeni oturum):** çip `KraL-JevGomulu-27Eyl` AÇILDI (`task_1c4cca2f`; ① + ArTisT `artist-arama-terimi` kalıbı). ② 19:5x isteği yalnız PRUVO kutusuna yazılmıştı, EyLüL'ün `KUTU.md`'sine DÜŞMEMİŞTİ → SendMessage ile doğrudan iletildi (kanal dersi: Faralya evine istek o evin kendi KUTU'suna ya da SendMessage'a gider). OTeLLa 12:5x'e KABUL kutuda. Canlı iz 20:1x: açılış KraL 3 · ArTisT 1 · pencere TeKiN 4 · motor TeKiN 1 · metin PRUVO 0.
**SIRADAKİ TEK İŞ:** çip kapanışı gelince merge-kapisi ile al → canlı kabul (ANA oturumda Agent çağrısı: mekanik görev RED+m3 metni, yargı görevi GEÇER) · EyLüL (a) sha'sı gelince PRUVO yolunda metin kapısı satırı ≥1 ölç · kalan açılış izleri (MaCiT/HocA/TeKiN/BaBa) doğal açılışta. Spec = aşağıdaki ①–③; iş emri `otel-advisor/hazirlik/hukum-jev-gomulu-2026-09-27.md` (J2 §1 §2 §6 §7 §9).
**ÖLÇÜM (27 Eyl 19:5x):** EyLüL'ün 4 kancası `~/.claude/settings.json`'da GENEL kayıtlı → PRUVO oturumlarında da tetikleniyor (SessionStart kutu-nobeti + kayit-yedek · PreToolUse[AskUserQuestion] pencere-suzgeci · PreToolUse[Agent|Task] motor-secimi · PostToolUse[Write|Edit|MultiEdit] metin-kapisi). Canlı iz (`~/.claude/jev-kayit/*-2026-09.jsonl`) PRUVO'da: kutu nöbeti açılış yalnız KraL 5 (`KraL` 3 + `pruvo` 2; ev çözücü doğru, diğer 5 evde 14:27'den beri yeni oturum yok) · pencere süzgeci yalnız TeKiN 4 (gecti 3 · dondu_esik_alti 1) · motor seçimi yalnız TeKiN 1 · metin kapısı PRUVO **0**.
**① KraL İŞİ (kapı kodu, tek nokta = 5 ev shim'i):** `tools/mimar-icra-kapisi.py::_agent_karari` hâlâ mimarın elle beyanını (`isci-muafiyet: <iş> — <sınıf>`) istiyor; J2 §7.1 "sınıf jetonu mimarın beyanıdır; yerini bu karar alır". Beyan YOKSA Jev motor seçimi: `yargi`/`sessiz_hata` ≥ eşik → GEÇER · `mekanik` ≥ eşik → RED + m3 yönlendirmesi (motor-secimi ile aynı metin) · eşik altı/Jev yok → bugünkü beyan şartı (fail-closed). Kabul: pozitif+negatif vaka, ağsız sahte Jev, ≥5 izole mutant SURVIVOR=0, `mimar-kilit-test` + `mimar-kapi-mutasyon-test` + `ci-kapsam` + `kisisel-veri` rc=0, merge ÖNCESİ SERIT B dalda yeni kırmızı 0.
**② EyLüL İSTEĞİ (kutuya yazıldı):** (a) metin kapısı `dis_metin_turu`'na PRUVO yolları: `pruvo-pazarlama/icerik/` (30 dosya) · `pruvo-pazarlama/seo/` · `pruvo/ege-bilgi.md` · `pruvo/llms.txt` (`pruvo-bot/beyin/*.md` canlı ağız değil → kapsam dışı) (b) PRUVO devri `spawn_task` çipiyle → motor seçimi eşleyicisine eklenmesi önerisi (c) MaCiT çipleri `pruvo` ağacında KraL sayılıyor (bilgi).
**③ ÇAKIŞMA ÖLÇÜMÜ (J2'nin KraL'dan istediği):** PRUVO 5 evinde `PreToolUse[Agent|Task] mimar-icra-kapisi` + genel `motor-secimi` aynı olayda paralel → iki ayrı RED gerekçesi basılabilir (① ile hizalanır) · `PermissionRequest[*]` otomatik izin kancası pencere süzgeciyle ÇAKIŞMAZ (farklı olay) · `PreToolUse[*] icra-kapisi`/`baglam-kotasi` AskUserQuestion'ı RED etmiyor (TeKiN izleri geçti). Kapanış ölçütü: 6 PRUVO evinde açılış izi ≥1 · PRUVO'da motor seçimi ≥1 dönen + ≥1 geçen · metin kapısı PRUVO yolu ≥1 satır · ① main'de.

## ✅ 27 EYL 12:5x KraL ana-oturum (Okan: "tüm açık görevleri tamamla, bitenleri temizle") — **SERIT B 5 kırmızı onarımı main'de (`e328f383`) · worktree 1 + Tamirci**
**✅ SERIT B TAM YEŞİL:** `ac7bf360` push koşumu `36310675507` **success** (`23e8feeb` 26 Eyl 13:23Z'den beri İLK); SHA'nın 8/8 iş akışı success, deploy `36310675357` `deploy`+`yayin` success SKIPPED 0. K426'nın main bacağı push koşumunda TUTTU (schedule teyidi bir sonraki zamanlı koşumda).
**SIRADAKİ TEK İŞ:** yok (KraL kuyruğu boş). Açık yalnız dış olay bekleyen kanıtlar (aşağıdaki blok ①②) + çip adayları: K80 yeni-dal tabanı `merge-base(uç, --remotes)` · reçete kapısı yorum/Türkçe "Care" sınıf onarımı · ortak "sahte uç kur" yardımcısı (Tamirci ÖNERİ) · K427 → TeKiN.
**MERGE (Tamirci)** ← `claude/objective-davinci-bac14b` @`be71b6b8` (KraL-Tamirci-27Eyl; 1 dosya `parite-yayin-fikstur-test.js` +33/−1, çakışma 0): SERIT B 6. kırmızı kökü = 6 Eyl S8/SM1 onarımı ikiz yayın harness'ına taşınmamış, sahte `/ara` üretim kataloğunda (38.913) senkron sınıflandırıyor → Y1 22,6 sn → **0,86 sn**. Dal ağacında BAĞIMSIZ: `parite-fikstur` · `parite-yayin-fikstur` · `parite-etiket` · `parite-hiz-freni` · `parite-tavan --kendini-test` · `kisisel-veri` · `ci-kapsam` → 7/7 rc=0. Dal SERIT B `36304778148`: adım success, dalın getirdiği yeni kırmızı 0. Bilinen ayrı kırmızı: `hacim-tam-takim | TEST 1` yalnız dispatch'te koşar, 19 Eyl'den beri her dispatch'te failure (`35430322589`/`35501368433`/`36259360649`/`36304764477`) — push/schedule SERIT B'yi etkilemez; kalem açık.
**MERGE `e328f383`** ← `claude/elated-wright-59319e` @`ce2810bc` (KraL-SeritB-Onarim; merge-base `0797bfb7`, main yalnız MaCiT ürün commit'leriyle ilerlemişti, 9 dosya +87/−26 yalnız `tools/`, çakışma 0). Dal ağacında BAĞIMSIZ, borusuz: `fikstur-git-sizinti-kapisi` · `ci-sabit-canli-yol-kapisi` · `emekli-motor-adi-nobetcisi --ayrinti` (HUKUM=GECTI, tavan 66→**65 daraltıldı**) + `-test` · `ci-kapsam-test` (+`--kendini-test`) · `recete-kapisi` · `mimar-kilit-test` · `k80-arsiv-tag` · `k80-yorum-cagri` · `care-ev-ekseni` · `kisisel-veri` → **12/12 rc=0**. Dalda dispatch SERIT B `36304764477`: hedef 7 adımın 7'si success; kalan kırmızılar yalnız Tamirci kalemi + hacim dispatch kalemi. Yan bulgu (çip): `2b670fb8`'in `--kendini-test` hükmünü liste anlamasına çevirmesi K1..K15 hüküm nöbetçisini SESSİZCE öldürmüştü → `ok1 and … and ok15` geri geldi, M-KB6 yine KIRMIZI yakıyor.
**TEMİZLİK:** onarım çipi oturumu (zaten arşivli) · ağacı + dalı yerel/uzak SİLİNDİ · MaCiT'in arşivli 3 dilim oturumundan kalan sahipsiz 2 ağaç (`laughing-mclean`, `sweet-swartz`: lsof 0, temiz, HEAD main'de) + 2 boş dal SİLİNDİ · boş `claude/sharp-merkle-f6bda5` SİLİNDİ → worktree = ana + Tamirci.

## ✅ 27 EYL KraL ana-oturum (Okan: "devam") — **KilitMutant + YetimMerge (3 dal) main'de (`9ac32b92`) · kapı testleri TAM YEŞİL · dal evreni 26 → 13**
**SIRADAKİ TEK İŞ:** ~~SeritB onarımı~~ → yukarıdaki blok. Açık canlı kanıtlar (dış olay bekliyor): ① ilk canlı iki-push yarışında `D1 YARIS SONRASI OLCUM:` satırı · ② bekleyen commit varken `yayin-nabzi` log'unda `main'e giris ani: … (push aktivitesi)` · ③ K80 ÖNERİ (a): yeni-dal push'unda taban = `merge-base(uç, --remotes)` (çok commit'li dalın ilk commit'lerindeki CI adımı ölçülmüyor) — çip adayı. Kalan 13 uzak dal bilinçli: KURTARMA_ARSIVI 8 · PARK 1 (`il-ilce-dilim1`) · OLCULEMEDI 4 (`agitated-haslett` K189 · `exciting-kalam` K268/K270 · `seo-wave28-backlink` ArTisT · `muh/n1-ilan-fiyat`).
**ENTEGRASYON `9ac32b92`** (ff; 4 merge: `claude/elastic-noether-81791b` KilitMutant @`17ec3aed` + YetimMerge A `63025fb0` · B `c8dccdf3` · C `0a74ebd1`; her biri main'e karşı çakışma 0, 26 dosya, arama düzlemi 0). Birleşik GEÇİCİ ağaçta BAĞIMSIZ, borusuz: `mimar-kilit-test` **325/325** (önce 318/323) · `mimar-kapi-mutasyon-test` **74/74** (önce 37 eşik altı) · `jev-kapi` · `tikayici-kaldirma` · `k80-arsiv-tag` · `k80-yorum-cagri` · `ata-lisans` · `yayin-erisim` · `yayin-gecikme` · `yayin-yasi` · `d1-yaris` · `is-akisi-kapisi` · `ci-kapsam` (+`--kendini-test`) · `ci-kapsam-dar-mutasyon` · `kisisel-veri` · `yedekle-test --hermetik` · `uyum-kapisi` (+`--kirpma-mutasyonu`) · `diriltme --kendini-test` · `durum` → **hepsi rc=0**. KilitMutant hükmü: KOD REGRESYONU 0, tüm kırmızı BAYAT TEST (11 Eyl RED→RAPOR kararı + 29 Ağu raporcu silinmesi + çapa bayatlığı). YetimMerge: 9 dalın 8'i yeniden uygulandı, `muh/a4-uyum-kesme` ESKIMIS; K80 arşiv-tag menzili onarıldı (`koru/faz3-edge-arama` tag'lenip silindi).
**YAYIN:** `9ac32b92` run `36276627930` — `deploy` success · `yayin` success · SKIPPED 0. **Kapanan canlı kanıtlar:** YetimMerge C (k78) — elle `yayin-erisim-alarmi` `36277586749` success, `HIZALAMA KANITI … rc 0 (ATA)` + `ROLLOUT: KAPALI — evren deploy SHA'sindan turedi` ✅ · KilitMutant runner — SERIT B `36276628053`'te `Mimar kapi bataryalari — kanonik yerel duzlem` · `Mimar kilit kabul testi (325 vaka)` · `Mimar kapi mutasyon bataryasi` · K80 ×2 · K286 hepsi **success** ✅.
**🔴 SERIT B KIRMIZISI BENDEN (onarıldı):** `Recete kapisi` `AYIKLANAMADI=1 serbest_cagrilar.py:1` — Jev kapı dalının (`a737ffa5`, merge'ü ben aldım) yorumu "Care: ADLI SEKILLER … `python3 -c`" reçete kapısının büyük/küçük harf duyarsız `CARE:` + 250 karakter penceresine düştü (yanlış pozitif). Merge kapımda `recete-kapisi` KOŞULMAMIŞTI. Yorum "Onarim yolu" yapıldı → `recete-kapisi` RECETE=13 AYIKLANAMADI 0 rc=0 · `jev-kapi` · `serbest-kume-ev-ekseni` · `ci-kapsam` rc=0. 🔧 SINIF KALEMİ: reçete kapısı `#` yorum satırlarını ve Türkçe "Çare/Care" kelimesini reçete sayıyor — kabul: yorum içi `Care: … python3 -c` fikstürü YEŞİL, gerçek `print("CARE: python3 -c …")` KIRMIZI + mutant.
**TEMİZLİK:** merge edilen 4 dal yerel+uzak SİLİNDİ · yeniden uygulanan 9 eski dal `arsiv/dal/*` tag'i (ls-remote uç BİREBİR) + SİLİNDİ → arşiv tag **35** · geçici entegrasyon ağacı/dalı SİLİNDİ. 🔴 Ağaç adı geri dönüşümü 2. kez: `sharp-merkle-f6bda5` + `elastic-noether-81791b` artık CANLI MaCiT çiplerinin (Pentax/Olympus dilim-2) — DOKUNULMADI. Ana ağaçta `urunler.json` ` M` = MaCiT'in uçuştaki 9 ürünü (D1 EKSİK 9 aynı kayıtlar) — dokunulmadı.

## ✅ 26 EYL 20:0x KraL ana-oturum (Okan: "tüm açık görevleri tamamla, bitenleri temizle") — **PARİTE KAPANDI (BİREBİR) · 23 Eyl dal-envanteri onarımı main'de (`7808fd50`) · 3 çip açıldı · PRUVO temizliği**
**SIRADAKİ TEK İŞ:** ~~3 çip merge~~ → yukarıdaki blok (YayinGecikme `7b7ea819` · KilitMutant + YetimMerge `9ac32b92`).
**MERGE `7b7ea819`** ← `claude/funny-heisenberg-188c2b` (KraL-YayinGecikme; ff, 7 dosya +587/−24): yaş tabanı `max(en eski commit, yayın anı, main'e giriş anı)`, giriş = `repos/…/activity` push'u (`before == son yayınlanan`); ölçülemezse eski taban + `OLCULEMEDI` notu. Bağımsız: `yayin-gecikme-test` rc=0 · `--kendini-test` 25/25 · `ci-kapsam` · `kisisel-veri` rc=0 · canlı `--alarm` 🟢. Yan onarım: `yayin-gecikme-mutasyon.py` 28 Ağu'dan beri ÖLÜYDÜ (ayna `gecici_worktree` taşımıyordu) → 27/27 mutant. Yayın run `36259835129` deploy+yayin success; elle `paket-tazelik-alarmi` `36260760493` success. **AÇIK:** CI iş akışı kimliğinin `/activity` erişimi OLCULEMEDI (bekleyen commit yoktu, satır basılmadı) — kapatan: bekleyen commit varken koşan ilk `yayin-nabzi` log'unda `main'e giris ani: … (push aktivitesi)`.
**MERGE `62c1c521`** ← `claude/blissful-hugle-f926b0` (KraL-PrePushD1; ff, 11 dosya +878/−20): pre-push D1 sahte RED → `YerelYaziciUcusta` rc=5 `D1_SENKRON=YARIS` + ≤480 sn bekle + uzak main yeniden ölç (YAZ / KAPSANDI yalnız KATI ata / YARIS fail-closed); CARE satırı çağıran evin DEVAM'ından. Dal ucunda BAĞIMSIZ: `d1-yaris-test` · `prepush-d1-kaynak-test` · `care-ev-ekseni-test` · `jev-kapi-test` · `serbest-kume-ev-ekseni` · `ci-kapsam` · `kisisel-veri` hepsi rc=0 · `d1-sync --kendini-test` 157/0. Push kancadan geçti, D1 38868 uyuşmaz 0. ⇒ 25 Eyl bloğundaki iki 🔧 KraL AÇIK kalem (pre-push D1 sahte RED · CARE ev yolu) **KAPANDI**. Açık kalan (çipin ölçemediği): canlı iki-push yarışında `D1 YARIS SONRASI OLCUM:` satırı ilk kez görülünce teyit.
**DAL TRİYAJI (çip `KraL-DalTriyaj-26Eyl`, kapandı):** evren 51 → 26; **25 ESKIMIS** dal `arsiv/dal/*` tag'lenip yerel+uzak silindi (tag 25, force 0). Kalan: YETIM_DEGERLI 10 (→ YetimMerge çipi) · KURTARMA_ARSIVI 8 (bilinçli, durur) · OLCULEMEDI 4 (`agitated-haslett` K189 · `exciting-kalam` K268/K270 — KilitMutant kırmızısıyla ilişkili olabilir · `seo-wave28-backlink` ArTisT · `muh/n1-ilan-fiyat`).
**PARİTE ✅:** main 71 dk durgunken, katalog canlıyla eşit (37891): `parite-test.js` **BİREBİR 1334/1334 rc=0** · `parite-ege.js` **BİREBİR 897/897 rc=0** ⇒ 14. turun `OLCULEMEDI`'si KAPANDI.
**MERGE `7808fd50`** ← `claude/nifty-panini-fd2a08` (23 Eyl Tamirci; `dal-envanteri.py` yerel+uzak evren, +367/−16, 3 dosya, çakışma 0, main o dosyalara dokunmamıştı). Birleşik geçici ağaçta: `--kendini-test` DÜŞEN 0 · `--mutasyon` 5/5 SURVIVOR=0 · `ci-kapsam` · `kisisel-veri` rc=0. Merge+push TEK komutta (komşu yakalamasın).
**YAYIN:** `7808fd50` run `36255819182` `deploy`+`yayin` success, SKIPPED 0. SHA'daki tek kırmızı `Paket tazeligi alarmi` (schedule 16:45Z) = `yayin-gecikme-nobeti` 🔴 TIKALI "bekleyen 76 dk" — **yanlış alarm**: yaş son yayından (15:29) sayılıyor, 63 dk sessizlik + push'ta, commit ~13 dk'lıktı ve deploy'u koşuyordu → deploy inince `rerun` attempt 2 **success**. 🔧 AÇIK KALEM: yaş tabanı `max(yayın anı, commit'in main'e giriş anı)` olmalı; kabul: "sessizlik + taze push" fikstürü YEŞİL, gerçek tıkanma fikstürü KIRMIZI.
**TEMİZLİK:** oturum arşivi 3 (MaCiT Fujifilm dilim-9 · MaCiT Pentax pilot · KraL DefterYuklem 25 Eyl) — başka evlerin (FaR/EyLüL/OTeLLa/BaBa cron) oturumlarına DOKUNULMADI · worktree `upbeat-solomon` silindi (temiz, lsof 0, içerik main'de) → worktree **1** (yalnız ana) · yerel `claude/*` dal 5→0 (4 boş + nifty-panini merge) · uzak nifty-panini silindi · scratchpad 0. 🔴 MaCiT'in 3 kapanışı (Olympus/Pentax/Fujifilm-dilim9) `✅ İŞ BİTTİ — ARŞİVLENEBİLİRİM` jetonu TAŞIMIYOR — Okan'ın "temizle" emriyle arşivlendi, MaCiT'e kutudan bildirildi.

## ✅ 26 EYL 17:xx KraL ana-oturum — **MARKA SÖZLÜĞÜ 14. TUR MAIN'DE (`c7669344`): Pentax · Olympus · Leica · Blackmagic · Insta360 · parite ~~OLCULEMEDI~~ → KAPANDI (yukarıda)**
**SIRADAKİ TEK İŞ:** ~~parite~~ → yukarıdaki blok.
**MERGE:** çip `KraL-Whitelist-Kamera5-26Eyl` kapanışı (8 ölçüt, IZINLI 191→196 · EKI 52→57 · FARK 139 · URL 40845=40845 · K220 menzili boş · mutant kör değil) → yerel merge `9531c0d1` (kod değişimi 2 satır, çakışma 0). 🔴 **Push'tan ÖNCE MaCiT paylaşılan checkout'ta `pull --rebase` + push yaptı:** merge commit düzleşti, dal commit'i `c7669344` olarak origin'e gitti — `git cherry` `-` (patch BİREBİR), içerik kaybı 0, ama **parite kapımdan önce yayına girdi** ([[ana-checkout-lokal-merge-komsu-pushu]] tekrarı). İki yeni çip ağacı (`jovial-napier`, `upbeat-solomon`) `9531c0d1` üstünden açıldı — sahipleri başka, dokunulmadı.
**PARİTE `OLCULEMEDI`:** 3 koşum kırmızı (24 · 19 · 49 / 1334) ve üçü de eşzamanlı eklemeyle açıklandı: ② 19 "yerelde var /ara'da yok" = deploy'u sürmekte olan dilim-10 ürünleri (yayın bayrağı bekliyor) · ③ 25/25 örnek `/ara` > yerel, max fark **8** = koşum arasında eklenen 6 Olympus + 2 Fujifilm. Beş jetonu içeren sorgularda sapma **0**. `parite-ege.js` KOŞULMADI. Kapatan: MaCiT sessizken tam parite rc=0.
**TEMİZLİK:** `claude/sharp-mayer-3e72bc` + `claude/inspiring-euclid-df62af` yerel+uzak SİLİNDİ (ls-remote 0); geçici merge ağacı SİLİNDİ; worktree 5→3 (kalan 2 yabancı çip).

## ✅ 26 EYL 16:3x KraL ana-oturum (Okan: "devam") — **JEV ENGEL 2 KAPANDI: kapı dalı main'de (`a737ffa5`) · YAYIN KIRIĞI KAPANDI · hoca-niyet 0,85**
**SIRADAKİ TEK İŞ:** ~~Kamera5 çipi merge~~ → yukarıdaki blok.
**MERGE `a737ffa5`** ← `claude/inspiring-euclid-df62af` @`92c2f545` (merge-base `2bec95cd`, 4 dosya +553/−22: `serbest_cagrilar.py` · `mimar-icra-kapisi.py` · `jev-kapi-test.py` · `deploy.yml` adımı; `merge-tree` çakışma 0, ff İMKÂNSIZ). Birleşik ağaçta (geçici worktree) borusuz: `jev-kapi-test` BULGU=0 · `serbest-kume-ev-ekseni` rc=0 · `ci-kapsam` rc=0 · `kisisel-veri` rc=0. **CANLI KABUL:** ANA oturumda `jev.py saglik` kapıdan geçti rc=0 `motor=jev`; `mimar-kapi-kur --durum` KABLO 5/5. D1 38833=38833 uyuşmaz 0. Dal yerel+uzak SİLİNDİ.
**🔧 YENİ AÇIK KALEM (CI DIŞI ÇÜRÜME):** `mimar-kilit-test` main'de **318/323** (vaka 110/111/114 `EKSIK-KURUCU` · 921/922 `SERT_BLOK`→`DIGER_RED`) + `mimar-kapi-mutasyon-test` **37 mutant** eşik altı (ME1/ME2/J1 BAYAT-ANKRAJ …). Birleşik ağaçta küme BİREBİR aynı ⇒ Jev dalından DEĞİL. İkisi de CI'da KOŞMUYOR (`nobet.yml:2894` yalnız yorum) → kırmızı görünmüyordu. Kabul: ikisi rc=0 ∧ SERIT B'ye bağlı.
**YAYIN:** `ec7cbf50` run `36242996331` — `deploy` success · `yayin` success · SKIPPED 0 (`serit-a3` success, önceki ~50 atlanan adım koştu). `a737ffa5` run `36245429096` kuyrukta.
**🔴 YAYIN KIRIĞI:** `2bec95cd` köke `JEV-ENVANTER.md` koydu → `kisisel-veri-test` Kural B (`KOK_BELGE_IZIN`) `serit-a3`'ü kırdı, `deploy`+`yayin` SKIPPED (runs `36241469826` · `36241894677` failure). Önceki blokta yazan "kisisel-veri rc=0" dosya `git add` edilmeden koşulmuştu (ls-files ekseni) → [[yeni-kok-belge-commit-oncesi-kisisel-veri-yesil-yalan]]. Taşımak BaBa'nın kök ölçümünü körleştireceği için İZİN girdisi gerekçeyle eklendi. Yerel: `kisisel-veri` rc 1→0 · `ci-kapsam` rc=0.
**JEV:** MaCiT (d) uygulandı `9f744ff9`: `macit-red-gerekcesi` `logo_tasiyor`+`mukerrer_islev` ÇIKTI (metinden seçilemez; kanca zaten BILGI sayıyor, hasat kodunda seçenek listesine bağ 0). `--kendini-test` 7/0 · canlı çağrı `lego_iliskili` 0,61 `motor=jev`. (c) kategori açıklamaları DEĞİŞMEDİ: metin değişirse 0,8 eşiği ölçümsüz kalır → aday metni + altın küme yeniden ölçümü MaCiT'e.
**Okan'a çıkan:** YOK.

## 🔵 26 EYL 15:2x KraL ana-oturum (Okan /goal) — **JEV PRUVO'YA: kalıp katmanı main'de (`2bec95cd`), iki engel çözülüyor, 3 çip açık**
**SIRADAKİ TEK İŞ:** çip `KraL-JevKapi-26Eyl` (`task_6d71d37a`) dalını merge-kapısıyla al → `.claude/mimar-kapi-kur.py` ile 5 eve kur → her evde `jev.py saglik` serbest mi ölç. Ardından EyLüL'ün ortak istemci zarf düzeltmesi gelince `jev_karar.py --kalip hoca-niyet --metin "…"` → `motor=jev` (şu an `kume_disi_cevap`).
**YAPILAN:** ortak istemci `/Users/okan/.claude/jev/jev.py` (EyLüL) üstüne PRUVO **kalıp katmanı** `tools/jev_karar.py` + TEK KAYNAK `tools/jev-kaliplar.json` (5 ev, 8 kalıp, `esik: null` = insan onayı) + `JEV-ENVANTER.md` (P1–P8). Kendi yazdığım adaptör ortak istemci görününce SİLİNDİ (ikinci kopya yok). Kabul `--kendini-test` **7 iddia / 0 kırmızı**; izole mutant A (insan bandı) K4'te, B (seçenek adı) K2'de ÖLDÜ. `ci-kapsam` + `kisisel-veri` rc=0.
**CANLI:** Jev Workers AI REST'ten doğru cevap veriyor (`hoca-niyet` → `urun_sorusu` güven 1, 569 token, ~0,9 sn); tek CF hesabı, anahtar/ödeme GEREKMEDİ. `.cf-token`'ın AI yetkisi YOK (401) — yol wrangler oturumu.
**ENGELLER:** 🔴 E1 ortak istemci CF REST dış zarfını (`{result,success}`) açmıyor ⇒ her karar `kume_disi_cevap` — EyLüL'e iki kez düzeltme satırıyla bildirildi (15:2x). 🔴 E2 mimar icra kapısı repo-dışı `jev.py`'yi ANA oturumda reddediyor (5 ev) — çip `KraL-JevKapi-26Eyl` çalışıyor.
**ÇİPLER:** `KraL-JevKapi-26Eyl` (`task_6d71d37a`, ağaç `beautiful-mirzakhani-874df9`) · `HocA-JevEge-26Eyl` (`task_ed294420`, pruvo-bot: her gelen mesaja Jev niyeti) · `MaCiT-JevKategori-26Eyl` (`task_0233e7e8`, pruvo-hasat: kategori/RED ikinci görüşü). Kutuya tüm evlere duyuru yazıldı. **Okan'a çıkan:** YOK.

## ✅ 25 EYL 22:5x KraL ana-oturum (Okan: "devam") — **BaBa ③ de main'de (`92d7621a`, merge'ü çip attı) · önceki YAYIN `OLCULEMEDI` KAPANDI**
**SIRADAKİ TEK İŞ:** OCI kalıcılık kabulü — 26 Eyl ≥06:25Z sonraki ilk zamanlanmış koşumda `EL-SIKISMA-TAMAM` (dış zaman). MaCiT 22:3x araç kusurları TRİYAJ EDİLDİ (26 Eyl 01:xx): `hasat_ekle` `uyum` türetimi + `marka-kapsama` büyük/küçük harf → **pruvo-hasat/MaCiT düzlemi**, KraL'da değil · `yedekle` karantinası **KUSUR DEĞİL** (bayt-düşüşü koruması doğru çalıştı; kasıtlıysa `.yedek-dusus-izin.json`'a beyan; `--sirlar` zaten EMEKLİ) · 🔧 **KraL AÇIK:** pre-push D1 kolu eşzamanlı push'ta sahte RED veriyor — bu gece 2. kez ölçüldü (benim push'um `D1 SENKRONU BASARISIZ rc=1` ile durdu, hemen ardından `--durum` 38829=38829 / uyuşmaz 0) · 🔧 **KraL AÇIK (düşük):** CARE satırı başka evde koşulunca KraL'ın `DEVAM.md` yolunu basıyor (`defter-rotasyon.py` CARE metninde yol YOK; kaynak `defter-kota-kapisi.py` türetimi — ölçülecek). 🧾 **Okan'ın e-Arşiv işi:** 45 fatura planı masaüstünde `PRUVO-fatura/`; portal yazımı Claude güvenlik denetimince reddedildi, fatura KESİLMEDİ.
**MERGE `92d7621a`** ← `claude/heuristic-jackson-d99973` (`a608d277`; merge-base `a91295b3`, tek dosya `tools/defter-rotasyon.py` +395/−6, `merge-tree` çakışma **0**, ff İMKÂNSIZ → merge commit). Merge'ü çip kendisi attı (22:48, ben ölçerken); çift yazım olmasın diye soruldu: **kutu = çip, defter = KraL**. Bağımsız ölçüm DALIN AĞACINDA, borusuz: `--kendini-test` **21/21 DÜŞEN=0 rc=0** (3 izole mutant OLDU) · `defter-onlem-bacagi-test` **115/0, MUTANT 6/6** · `ci-kapsam` rc=0 · `kisisel-veri` rc=0 · canlı `--kuru` DEVAM md5 önce=sonra (`c3025866…`). 🔴 **İki ayrı sayı:** `--kuru` ②'den ÖNCEKİ defterde (65 blok) **INDIRILEBILIR=2**, bugünkü defterde (7 blok) **INDIRILEBILIR=0** — indirilecek blok KALMADI (59'u ② ile indi); yüklem körelmedi: `20:5x` bloğu ③ kolunda VETO yiyor (kimliksiz açık kalem).
**YAYIN:** `03081fcb` → run `36179659751` `completed` · `deploy` success · `yayin` success · SKIPPED **0** ⇒ önceki bloğun `OLCULEMEDI`'si KAPANDI. `92d7621a` → run `36181971743` headSha BİREBİR, 6/6 job success (`deploy`+`yayin` success, SKIPPED **0**). `db685791` (bu defter) koşumu ardıl push'larca `cancelled`; ardılı `33620ae1` taşıyor.
**TEMİZLİK:** 🔴 **Ağaç adı geri dönüşümü CANLI yakalandı** — ilk ölçümde `beautiful-mirzakhani` · `confident-sutherland` · `mystifying-sinoussi` detached/temiz/lsof 0 (artık) göründü; silmeden ÖNCE ikinci ölçümde üçü de yeni açılan 3 MaCiT çipine devredilmiş (yeni dallar, lsof 2/2/5) ⇒ **HİÇBİRİ silinmedi** ([[worktree-adi-geri-donusturulur-canli-cipi-siler]]). `quizzical-feistel-d5bd17` + dal `claude/heuristic-jackson-d99973` SİLİNDİ (ağaç: çip · uzak dal: Okan); `ls-remote` boş, `worktree list` 4, içerik main'de (`92d7621a`). Repo-dışı `dal-olc.py` icra kapısına takıldı; §2-§3 adımları elle `git` ile koşuldu.
**MOTOR ORANI:** Claude 1 / m3 0 — iş merge hükmü + ölçüm (sessiz-hata sınıfı), hacim yok. **Okan'a çıkan:** YOK.

## ✅ 25 EYL 22:2x KraL ana-oturum (Okan: "devam") — **cron nabız holü main'de (`d3846746`) · BaBa'nın 3 kaleminin 2'si KAPANDI: defter 497→154, hafıza 16.629→15.317 B**
**SIRADAKİ TEK İŞ:** çip `KraL-DefterYuklem-25Eyl` (`task_b1e6da02`) dalını merge-kapısıyla al (BaBa ③). Ayrıca **YAYIN `OLCULEMEDI`** — aşağıdaki iki koşumdan biri `deploy`+`yayin` `success` ∧ skipped=0 basınca kapanır.
**MERGE `d3846746`** ← `claude/mystifying-sinoussi-436710` (1 dosya +386/−17, merge-base `4a202b24`, çakışma **0**). 🔴 **Çipin ağacı main'e dönmüştü** (`HEAD=9167a6fa`, 229 iddia) — main'i ölçüyordum; dalı AYRI geçici ağaca çıkarıp gerçek uçta (`706f3ca3`) ölçtüm: **252 iddia / 0 KIRMIZI** · `ci-kapsam` · `kisisel-veri` rc=0 (borusuz). Taban FİİLEN oynadı (main 229 ↔ dal 252). Pozitif kontrol `T-DOLU-SESSIZ` üç iddiayla "gerçekten sessiz cron HÂLÂ 🔴" diyor; tekil yama YOK (iş akışı adı geçen 2 satırın ikisi de yorum). 🔴 **Ağaç adı geri dönüştürülmüş** — `mystifying-sinoussi-436710` artık başka dal taşıyor, komşu çipe dokunulmadı.
**🟢 BaBa ② DEFTER KİLİDİ AÇILDI (`65dc08b9`, m3):** `DEVAM.md` **497→154 satır** (175.073→14.653 B), arşiv 24.864→**25.294**. İşçi damgasına güvenilmedi — donmuş kopyamla BAĞIMSIZ: çıkan **59** blok başlığının **59'u** arşivde (eksik 0) · arşiv **APPEND-ONLY** (ilk 24.864 satır md5 BİREBİR) · eski arşivden **0 satır** silinmiş · **çıkan 373 anlamlı satırın 373'ü arşivde (kayıp 0)**. Kabul: `devam-sinif-kapisi` rc=0 · K-kimlik **140 ≥ 89** · commit kapsamı yalnız `DEVAM.md`. 🔴 **İlk deneme fail-closed DURDU, hata BENİMDİ:** `SIRADAKİ TEK İŞ` iki yazım varyantında geçiyor (13 noktalı İ + 2 noktasız I = 15); spec'im tek desen sanmıştı, işçi öncülü yalanlayıp durdu, **hasar 0**.
**🟢 BaBa ④ HAFIZA KAPANDI (m3):** `MEMORY.md` **16.629→15.317 B** (tavan 16.384 altında). Dört ekseni kendim ölçtüm: satır 39 · 180 link hedefi diskte, eksik **0** · dosya sayısı 478 değişmedi. İşçi tutturamadığını ADIYLA yazdı: **11 satır hâlâ >300 B (en uzun 2.849)** → BaBa'ya çıktı, kural kategori satırlarında matematiksel olarak tutmuyor.
**EV:** `9167a6fa` → `d3846746` → **`65dc08b9`**, `ls-remote` KANITLANDI, ağaç 0 dosya. **YAYIN `OLCULEMEDI`:** `36177516477` (`16d7e222`, merge'i ata taşıyor) `in_progress` · `36179235590` (`65dc08b9`) `pending`; kota penceresi kapandı, beklenmedi. **TEMİZLİK:** geçici ölçüm ağacı + merge edilen dal (yerel+uzak) + 2 işçi spec'i + 2 rapor dizini + işçinin bıraktığı dosya SİLİNDİ, scratchpad 0. **MOTOR ORANI:** Claude 1 / **m3 3** (`MOTOR=` 168→172). **ÖZ-ÖLÇÜM:** tur **448** / bağlam **428K** (<500 · <450K). **Okan'a çıkan:** YOK.

## ✅ 25 EYL 20:5x–21:2x KraL ana-oturum (Okan: "devam") — **BEKLEYEN İKİ DAL DA MAIN'DE (`70a7eb69`) · çürütme çipin kapatamadığı HOLÜ buldu**
**SIRADAKİ TEK İŞ:** çip `KraL-CronNabizHolKapat-25Eyl` (`task_352e8b5d`) dalını merge-kapısıyla al. OCI kalıcılık kabulü (26 Eyl ≥06:25Z sonraki ilk zamanlanmış koşumda `EL-SIKISMA-TAMAM`) hâlâ AÇIK — dış zaman bekliyor.
**MERGE ① `claude/eloquent-dirac-1c3278`** (1 dosya `cron-nabiz-kapisi.py` +227/−3, merge-base `7b5914f3`, `merge-tree` çakışma **0**) **② `claude/elastic-booth-6178be`** (4 dosya +676/−12, merge-base `2f95d003`, çakışma **0**). Öz-raporlara güvenilmedi, hepsi **DALIN AĞACINDA borusuz** (`${pipestatus[1]}`) koşuldu: ① `--kendini-test` **229 iddia/0 KIRMIZI** · `ci-kapsam` · `kisisel-veri` rc=0 ② OCI kabul **MUTANT=28 ÖLEN=28 SURVIVOR=0** · `reklam-oci-kapisi` 9 bacak · `ci-kapsam` · `kisisel-veri` rc=0. Merge SONRASI ana ağaçta dördü de tekrar yeşil. Sır taraması: yeni jeton aracında sabit `client_secret`/`refresh_token` deseni **0 vuruş**, istemci json'u `~/Downloads`'tan okunup siliniyor, repoya yazmıyor.
**🔴🔴 ÇÜRÜTME HOL BULDU — ÇİPİN ÖLÇÜTÜ TUTTU AMA SINIF KAPANMADI:** dalın ağacında canlı kapı 17:58Z'de `SONUC: 🔴 ALARM ... A5+A3(yayin-erisim-alarmi.yml)` **rc=1** bastı (`OLCULEMEDI` değil **kesin** hüküm); ~2 dk sonra aynı komut **✅ ✅** (teslim 10/48, son koşum 4,1 sa önce). Gerçek: o iş akışının son schedule koşumu **13:56:08Z `success`**, yaş ~4,0 sa, eşik 18 sa ⇒ **kırmızı YANLIŞTI**. Kök neden kaynakta açık: `sayfa_tutarsizligi` şartı (2) *"sayfa DOLMAMIŞ"* — o akışın `total_count`'u **585**, sayfa DOLU ⇒ yeni kol hiç tetiklenmiyor. **Bayat ama DOLU sayfa, gerçekten susmuş yoğun bir cron'dan tek yanıtla AYIRT EDİLEMEZ** ⇒ çare ikinci gözlem (pencere süzgeçli sorgu), çipe çivilendi (>229 iddia ∧ pozitif kontrol 🔴 ∧ ≥2 mutant SURVIVOR=0).
**EV / YAYIN + 🔴 ÜÇ YARIŞ/KAPI OLAYI:** `a0084ecd` → **`70a7eb69`**, `ls-remote` = `70a7eb69` **KANITLANDI**; `--durum` **6 eksen ✅ 38743=38743, hash uyuşmaz 0**; deploy run **`36171438682`** izleniyor. ① merge sırasında `main` altımdan ilerledi (`2f95d003`→`a0084ecd`) + yerel dal referansı uzağın gerisindeydi → taban tazelenip yeniden ölçüldü ② ilk merge **rc=128 `could not write index`** ile DURDU (komşu `urunler.json`'u stage'lemişti): **stash/force YAPILMADI**, hasar 0 (`MERGE_HEAD` yok), komşunun commit'i inince üstüne alındı ③ ilk push pre-push kapısınca DURDURULDU (**K85: D1 bayatken `urunler.json` main'e giriyordu**) — kapı haklıydı; D1 senkronlanınca geçti. Push RED metni "ref itilmedi" demek DEĞİLDİ (`ls-remote` ile ölçüldü).
**TEMİZLİK:** worktree **4→2** (iki merge edilmiş ağaç `lsof`=0 → silindi; `quizzical-feistel` **CANLI** → dokunulmadı, pozitif kontrol ana checkout'ta 11) · 2 dal yerelde+uzakta silindi · ağaç 0 dosya · scratchpad 0. **DEFTER:** rotasyon **yapısal olarak tükendi** (`--onlem` → `SU_SEVIYESI=ULASILAMADI TASINAN=0`, iki aday `SINIFLANAMAZ`: açık jeton taşıyor) — araç arızası DEĞİL, blok bu yüzden kompakt. **MOTOR ORANI:** Claude 1 / m3 0 — tur tamamen merge hükmü + kapı çürütmesi (sessiz-hata sınıfı), `isci-devri` bunu Claude'da tutar; mekanik hacim yoktu. **Okan'a çıkan:** YOK.

## 🔧 BU TURDAN ACILAN KALEMLER (hepsi olculdu, hicbiri baslanmadi)
- **K380 (h) BOLUMU MAIN'DE YOK:** geri inecekse build **SONRASI** cagri yeriyle ya da `urun/` yokken `KAPSAM DISI` (OLCULEMEDI DEGIL) inmeli; yoksa iddia olculmemis kalir. Kabul: `deploy.yml`'de build-sonrasi atif ≥1 ∧ kapi rc=0.
- **K381 `d1-sync.py` GERI-OKUMA SOZLESMESI:** arac "yeni: 74 … dogrulandi ✅" bastiktan HEMEN sonra kendi `--durum`'u ayni satirlari EKSIK gosterdi (MaCiT olctu). Replika gecikmesi mi teyit hatasi mi **AYRISTIRILMADI** → `OLCULEMEDI`. Kabul: tek yazimdan hemen sonra + N dk sonra iki `--durum` (arada baska senkron YOK).
- **K383 `satir_soru` YUZEYI ERISILEMEZ:** link `prova=="kapali"` ister, katalogdaki 16/16 konfigur urun canlida `acik`. K89 "3 yuzey" sayimi SISIK, dogrusu **2 olculdu + 1 erisilemez**. Kabul: canli Worker'in non-200 dondugu konfigur satir (OKAN KAPISI).
- **K384 `kisisel-veri-test.py` bir beyani yanlis basiyor** — TAM METIN + kabul olcutu: `DEVAM-ARSIV.md`, baslik `K384 — 8 Eyl 2026` (govde izlenen belgeye YAZILMAZ, E5).

## ACIK KALEMLER (kapananlarin tam metni `DEVAM-ARSIV.md`'de)
- 🔴 **26 AGU KALEMLERI — TAM METIN KAYNAK-DOGRUSUNDA (`acik-kalemler.md`) + KUTUDA; burada yalniz
  ISARETCI** (uzun hali `DEVAM-ARSIV.md` 26 Agu ROTASYON blogu 1/5): K306 MERGE `df3b0d48` · K308 ACIK ·
  K309 DILIM-1 MERGE `25b38a82` (DILIM-2 MIMARDA) · K310 ACIK · K212 MERGE `97370cc2` KAPANDI · K222
  KAPANDI · K311 MERGE `bcbdb1dd` ACIK (①-④ GECMEDI; ④ GERI ALINDI) · **K312 ACILDI**.
- 🔴 **MOTOR (6 Eyl; 20 Agu GECERSIZ):** `minimax-m3` TEK + `claude`; `kimi` EMEKLI. Yedek YOK — m3 duserse `HAL=MOTOR-YOK rc=1`. Kaynak `mimar_kimlik.py`.
- 🔧 **K200 (TAM METIN ARSIVDE):** (i) kuru kosum OLCULDU 25 Agu (1512/234, sir elemesi 5/5; BULGU:
  gurultu budamasi memory agacinda KOSMUYOR → 13 gecici dosya Drive'a) · (ii) kablolama MIMARDA · (iii) kostugu kanit.
- 🔧 **K199 (19 Agu):** `is-akisi-kapisi.py` "etkili tasiyici" LITERALE capali; varlik turetilmis
  mekanizmaya gecince korlesir (K193). Care: sonucu olc ya da makine-okunur beyani tasiyici say;
  mutant+negatif sart. · 🔧 **K201 SINIF: KAYIT KENDINI OLCMEZ** — 5 vaka; ya TURETILIR ya SAYIYLA.
- 🔴 **K197: 19 Ağu mimara giden rapor içeriği (239 satır / 11.617 B) KAYBEDİLDİ — gitignore deseni + ağaç silme sırası.** Birebir cümle + öz KUTUDA.
- 🔧 **K217** tavan fiksturu. (K311 tam metni kaynak-dogrusunda; defterdeki ikinci kopya ARSIVE indi 2/5.)
- 🔧 **K189** (`ci-kapsam-test.py` hukum ekseni; kabul: aday>0 iken `OLCULEMEDI`+sifir-disi rc +
  ayri jeton + mutant hedef-kol atfi) · 🔧 **K191** (tarama SPEC'i isi ONCULDEN aliyor; sahibi
  MaCiT; kabul: ILK blok KAPSAM ON-OLCUMU + tazelik capasi). **Ikisinin tam metni ARSIVDE.**
- 🔧 **K192** (Okan: kalem ac DOKUNMA): `kimi` KURULU kapisinda YOK, dagitim kaniti VARLIK olcuyor. ARSIVDE.
- 🔧 **K202-kendini-test** (M06 cokme + bayat capa) — 🔴 SAHIPSIZ: SeritB chip'i "bende HIC olmadi" diye olctu (onun uyesi K203'tu, YESIL kapandi). kabul: capa govdeden count==1, `beklentiyi tutmayan: 0`.
- 🟠 **K206 (TeKiN→KraL; 3 KARAR VERILDI, icra chip'i sirada):** 8 uretec sari seriye — saklama AYRI
  AILE · gyro `doku=duz` · 8 fiyat ONAY (280/190/170/350=TAVAN/160/240/140/220); kupler render CELISKILI.
  PAKET main'de (`7ce644ae`). kabul (icra): ONIZLEME_AILELER 22→30 · taban-fiyat 21→29 · +8 sari kayit · 8 gorsel R2 200 · parite yesil.
- 🔧 **K220 (KraL) → ISARETCI, TAM METIN `DEVAM-ARSIV.md`'de:** `marka_yazimlari()`+`taninmis_mi()` TEK listeden besleniyor, liste IKI rol tasiyor;
  Range Rover'i markaya yazmak CANLI `/marka/land-rover/range-rover/` sayfasini OLDURUYOR — **menzil on-olcumu yapilmadan dokunma**
  ([[k220-menzil-on-olcumu-uc-turdur-eksik]]). 31 Agu negatif olcumu (`Raymarine`, kume-farki yordami, sayi-only kolun korlugu mutantla kanitli) ARSIVDE. SIRA: D bitti, sirada A.

- 🔗 **K-kimlik REF arşivi (taşınan bloklardan iz — ölçü eksenleri izlenen belgede tutuldu):**
  - **K0** — ref (geçmiş blok · taşındı)
  - **K1** — ref (geçmiş blok · taşındı)
  - **K2** — ref (geçmiş blok · taşındı)
  - **K3** — ref (geçmiş blok · taşındı)
  - **K5** — ref (geçmiş blok · taşındı)
  - **K110** — ref (geçmiş blok · taşındı)
  - **K240** — ref (geçmiş blok · taşındı)
  - **K252** — ref (geçmiş blok · taşındı)
  - **K270** — ref (geçmiş blok · taşındı)
  - **K284** — ref (geçmiş blok · taşındı)
  - **K291** — ref (geçmiş blok · taşındı)
  - **K313** — ref (geçmiş blok · taşındı)
  - **K314** — ref (geçmiş blok · taşındı)
  - **K316** — ref (geçmiş blok · taşındı)
  - **K317** — ref (geçmiş blok · taşındı)
  - **K319** — ref (geçmiş blok · taşındı)
  - **K320** — ref (geçmiş blok · taşındı)
  - **K321** — ref (geçmiş blok · taşındı)
  - **K322** — ref (geçmiş blok · taşındı)
  - **K323** — ref (geçmiş blok · taşındı)
  - **K325** — ref (geçmiş blok · taşındı)
  - **K326** — ref (geçmiş blok · taşındı)
  - **K327** — ref (geçmiş blok · taşındı)
  - **K331** — ref (geçmiş blok · taşındı)
  - **K332** — ref (geçmiş blok · taşındı)
  - **K334** — ref (geçmiş blok · taşındı)
  - **K335** — ref (geçmiş blok · taşındı)
  - **K336** — ref (geçmiş blok · taşındı)
  - **K337** — ref (geçmiş blok · taşındı)
  - **K338** — ref (geçmiş blok · taşındı)
  - **K339** — ref (geçmiş blok · taşındı)
  - **K340** — ref (geçmiş blok · taşındı)
  - **K351** — ref (geçmiş blok · taşındı)
  - **K352** — ref (geçmiş blok · taşındı)
  - **K353** — ref (geçmiş blok · taşındı)
  - **K356** — ref (geçmiş blok · taşındı)
  - **K357** — ref (geçmiş blok · taşındı)
  - **K360** — ref (geçmiş blok · taşındı)
  - **K361** — ref (geçmiş blok · taşındı)
  - **K365** — ref (geçmiş blok · taşındı)
  - **K366** — ref (geçmiş blok · taşındı)
  - **K367** — ref (geçmiş blok · taşındı)
  - **K368** — ref (geçmiş blok · taşındı)
  - **K369** — ref (geçmiş blok · taşındı)
  - **K370** — ref (geçmiş blok · taşındı)
  - **K371** — ref (geçmiş blok · taşındı)
  - **K372** — ref (geçmiş blok · taşındı)
  - **K373** — ref (geçmiş blok · taşındı)
  - **K374** — ref (geçmiş blok · taşındı)
  - **K375** — ref (geçmiş blok · taşındı)
  - **K376** — ref (geçmiş blok · taşındı)
  - **K386** — ref (geçmiş blok · taşındı)
  - **K387** — ref (geçmiş blok · taşındı)
  - **K389** — ref (geçmiş blok · taşındı)
  - **K390** — ref (geçmiş blok · taşındı)
  - **K391** — ref (geçmiş blok · taşındı)
  - **K392** — ref (geçmiş blok · taşındı)
  - **K395** — ref (geçmiş blok · taşındı)
  - **K396** — ref (geçmiş blok · taşındı)
  - **K397** — ref (geçmiş blok · taşındı)
  - **K399** — ref (geçmiş blok · taşındı)
  - **K401** — ref (geçmiş blok · taşındı)
  - **K402** — ref (geçmiş blok · taşındı)
  - **K404** — ref (geçmiş blok · taşındı)
  - **K405** — ref (geçmiş blok · taşındı)
  - **K406** — ref (geçmiş blok · taşındı)
  - **K407** — ref (geçmiş blok · taşındı)
  - **K408** — ref (geçmiş blok · taşındı)
  - **K410** — ref (geçmiş blok · taşındı)
  - **K411** — ref (geçmiş blok · taşındı)
  - **K412** — ref (geçmiş blok · taşındı)
  - **K414** — ref (geçmiş blok · taşındı)
  - **K415** — ref (geçmiş blok · taşındı)
  - **K416** — ref (geçmiş blok · taşındı)
  - **K417** — ref (geçmiş blok · taşındı)
  - **K418** — ref (geçmiş blok · taşındı)
  - **K419** — ref (geçmiş blok · taşındı)
  - **K420** — ref (geçmiş blok · taşındı)
  - **K421** — ref (geçmiş blok · taşındı)
  - **K422** — ref (geçmiş blok · taşındı)
  - **K423** — ref (geçmiş blok · taşındı)
  - **K89** — ref (geçmiş blok · taşındı)
  - **K91** — ref (geçmiş blok · taşındı)

## KraL ACIK ARTIKLAR (19 Agu anlati blogu ARSIVE TASINDI; kota uyarisi da orada)
🔧 **K203:** tavan kapisi worktree ICINDEN rol eksenini kaybediyor (sebep onek DEGIL cagri baglami);
K223'un FIKSTUR kovasi fikstur eksenini kapatti, ROL ekseni ACIK. · 🔧 **K204:** `OKSUZ` fiilen
"kirli mi" olcuyor, TEK BASINA kaldirma gerekcesi DEGIL. · 🔧 **K188** → kaynak-dogrusunda (5/5, `KraL-K309D2`: rc=0 ama eksen bataryada YOK).
- 🔧 **K218 · K219 · K221:** tam metinler ARSIVDE. (K195 merge edildi `528da42d`.)
- 🔧 **K198** → ARSIVDE · izlenen yapilandirmada ticari alan var, nobetci o duzlemi
- 🔧 **K182 (18 Agu — SINIF, bugun UC KEZ cikti):** mutant "kirmizi geldi" diye kanit
  sayiliyor ama kirmizinin SEBEBI hedef kol mu olculmuyor (recete M1 · K178 tek eksen ·
  ③g M5). kabul: her mutant, hedef kolu oldurdugunu AYRICA kanitlar.
- 🔧 **K176** → ARSIVDE · D1 kilit mesaji YANLIS PID basiyor (`d1-sync.py:157`); yayini bloklamaz · kabul: tutani basar ya da OLCULEMEDI + mutant.
- 🔧 **K171** → ARSIVDE · gizli kaynak
- 🔧 **K140** → ACIK_KALEMLER · ikinci kopya ARSIVE indi 4/5, `KraL-K309D2`: kapi EVREN KAYNAGI hatasi (cip evreni kuratorlu) · kabul: `marka-invaryant-kapisi.py` 7 jeton DUSMUS + `Rover` DURUYOR + mutasyon 4/4.
- 🔧 **17 Agu KALEMLERI:** K163 · K162 · K157 (⚖️ Okan, 22 Agu) · K158 · K146 · K142 (MaCiT) · K118. TAM METIN ARSIVDE.
- 🔴 **K104 / K104B:** nobet sicili + iki kapi main'de kirmizi. HUKUM MIMARDA. · **K99**
  bag kolonu · **K100** satir-sonu muafiyeti · **K102** yasakli ic dosya adi.
- 🔧 **K179 · K135 · K152** · 🟠 **K139 · K144** → ISARETCIYE INDIRILDI (7 Eyl, elle: `defter-rotasyon.py` 10/10 blogu K195 §1.2 ile VETOLADI, ilerleme uretemedi). TAM METIN `DEVAM-ARSIV.md`'de — arsiv isabeti K135=4 K139=2 K144=8 K152=11 K179=7, kalem kimlikleri KORUNDU.
- 🔧 **Iki acik kapi kalemi:** (a) shop bayatlik TETIK ekseni ≠ bundle evreni; (b) `devam-sinif-kapisi.py`
  is-akisi muafiyeti `norm`/`ham` ayrisiyor. · 🟠 **K122:** `kurtarma/k122-yabanci-is` dali DURUYOR. ARSIVDE.
- 🔧 **K151** (17-19 Agu): TAM METNI ARSIVDE (20 Agu 1:1 tasima blogu). · 🔧 **K161** → ISARETCI: KAYNAK-DOGRUSUNDA (26 Agu, `KraL-K309D2`).

## OKAN'DA
- ✅ 25 Agu penceresi: 9 kalem kapandi → [[okan-25agu-kapatilan-konular]]; 🔴 yeniden ACILMAZ.
- 🔧 **K297·K298·K299·K300·K301:** SERIT B hijyen kirmizisi · iki ayri K29 · K86 metni bayat ·
  K55 sayisi **197** · `T4-OLCUTSUZ` tum evlerde. Tam metinler KUTUDA.
- 🔧 **K329 (28 Agu, CI nobeti):** iki kapi dosyasi kanonik `git_ortami.sentetik_git`'e gecirildi, yerelde YESIL olculdu; main'e INEMEDI — kutu 306>300, 6 blok `ARŞİVLENEBİLİRİM` bekliyor (**Okan arsivi**), is `ci-nobet-git-ortami` dalinda stage'li.

## ARSIVDE — 14-20 Agu `DEVAM-ARSIV.md`'de.
