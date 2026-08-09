# DEVAM (KraL) — 8 Agu 2026

## 2026-08-09 11:37Z — CI nöbeti (KraL)
- Süpürme (koşulsuz): GitHub "Run failed" 3 mail Çöp'e taşındı; tur sonu gelen kutusunda Run-failed 0. Pozitif tanıma izi VAR (GitHub gönderenli toplam sıfır değildi) → hüküm TEMİZ, OLÇÜLEMEDİ değil.
- Deploy blokajı kök nedeni: `serit-a2` / "Uyum kapisi" (`tools/uyum-kapisi.py`) A4 model ikizi iddiası — Toyota Town Ace/TownAce · Lite Ace/LiteAce yazım ikizi. Kapıda elle tutulan allowlist YOK; iddia canlı katalog verisinden türüyor.
- Kök neden KAPANDI: veri tarafı `110b46bf` ile düzeltilmiş. `110b46bf`'yi ata olarak taşıyan koşum `31311137432`'de `serit-a2` = success (11:40→12:02, ~22 dk).
- Koşum `31311137432` durumu: build success · serit-a2 success · serit-a3 success · serit-a4 20+ dk hâlâ koşuyor · deploy ve yayin henüz başlamadı. Zincir hükmü = ÖLÇÜLEMEDİ (yeşil DEĞİL). Tavanı `serit-a4` koyuyor.
- Son başarılı deploy `31286873618` (`3e7f1b24`, 00:45Z) `110b46bf`'yi taşımıyor → düzeltme canlıda DEĞİL.
- Ayrı alarm kolları `deploy`/`yayin` zincirini BLOKLAMIYOR (kaynaktan `needs:` bağı ölçüldü): `odeme-bayatlik-push` ve `paket-tazelik-alarmi`. İkisinin kökü AYNI: canlı shop worker kodu main'den 157,5 dk geride (eşik 120 dk). Düzeltme = shop worker deploy → OKAN KAPISI, bu turda YAPILMADI.
- Ölçüm tuzağı (bu turda yaşandı): bayat koşumlardan okunan "serit-a2/serit-a3 kırmızı" iddiası, güncel koşumda ölçülünce ÇÜRÜDÜ. Kapı hükmü koşum başına ve `merge-base --is-ancestor` ile hangi commit'i taşıdığı ölçülerek verilmeli.
- SONRAKİ TURUN İLK İŞİ: `31311137432` koşumunun `serit-a4`/`deploy`/`yayin` conclusion'ını ölç; kırmızıysa sıfırdan teşhise başlama, bu notu devral.

## ⏱ SAATLIK CI NOBETI — 9 Agu 08:37Z turu (ev DOGRU: ~/dev/pruvo)

**Supurme (kosulsuz, §0.5):** kutu 7537 · `notifications@github.com` toplam **0** · "Run failed" **0** → Cop'e **0** · tur sonu kalan **0**. Pozitif tanima izi ALINDI: `sender contains "github"` → **1** gercek isabet (baska bir GitHub adresi), liste uzunluk paritesi 7537=7537, buyuk/kucuk harf duyarli ve duyarsiz tarama tutarli → hukum **TEMIZ**, OLCULEMEDI degil.

**🟢 KraL duzlemindeki BLOKAJLARIN HEPSI KAPANDI ve ADIYLA OLCULDU:**
- `build` **success** (kosum `31303970771`) → onceki turun `ozet.json` butce onarimi (`55ae7851`, vitrin havuzu 100→88) **KANITLANDI**. Butce sabiti gevsetilmedi, adim silinmedi.
- Olu kosum `31301608015` iptal edildi: `build`+`serit-a2`+`serit-a3` zaten kirmiziydi → `deploy` garanti `skipped`, ama `serit-a4` ucusta `pages` grubunu tutuyordu. Iptal sonrasi `31303970771` basladi. (Ayni kaldirac 00:46 turunda da dogru cikmisti.)
- **YENI kirmizi sinif — konfigur artefakt sapmasi (ONARILDI, push `822a8591`):** `serit-a3` / "Konfigur bundle kapisi". Sebep: `a046296a` katalogdan 53 urun kaldirinca `shop/src/konfigurlar.js` aynasi bayatladi. Kaldirilanlarin konfigurlu olani **tek**ti. Olcum jeneratorun KENDI `_sayi_normalize`'iyla yapildi (elle diff sahte sapma uretir): **0 ekleme / 48 silme**, kalan **16** id'in hicbirinde konfigur/fiyat degeri DEGISMEDI → canli fiyat degismedi, Okan kapisi gerekmedi. Kapilar: bundle rc=0 · `--kendini-test` rc=0 · `konfigur-fail-closed` **5/5**. Yeni kosum `31304782641`.

**🔴 TEK KALAN BLOKAJ — `serit-a2` / A4 model ikizi: SINIF = VERI (MaCiT duzlemi), kapi yanlis-pozitifi DEGIL.**
Curutuldu: A4'un elle tutulan muafiyet/allow kumesi **YOK** (kardeslerinin aksine `marka-invaryant-taban.json` benzeri bir taban dosyasi yok), normalizasyon ciplak regex → "elle tutulan liste parti basina bayatliyor" sinifi burada **yapisal olarak gecersiz**.
Nedensellik tekrar oynatildi: `3ab04a9d^` → **0** ikiz grubu · `3ab04a9d` → **2** · HEAD → **2**.
`git log -S` ile yazim yaslari: bosluklu `"Town Ace"` YALNIZ `3ab04a9d`'de (9 Agu partisi) · bosluksuz `"TownAce"` `1dee7bea`'dan beri (15 Tem, 3 hafta yesil).
→ **Yerlesik yazim BOSLUKSUZ.** Onceki IKI posta (04:2xZ ve 08:41Z) onarim yonunu **TERS** yazmisti (3 haftadir canli olan kaydi degistirtiyordu); 09:1xZ postasiyla **DUZELTILDI**: degisecek tek urun `toyota-town-ace-lite-ace-2008-geri-gorus-ayna-braketi`, uc alan (`uyum[0].model` · `uyum[1].model` · `marka`) — `marka` zorunlu, yoksa A4 yesillenirken A2/K5 kirmizi yanar. KraL urun verisine DOKUNMAZ.

**⚠️ LATENT RISK (KraL isi, sonraki muhendislik karari):** A4 sifir esikli SERT blok; on iki satir asagidaki kardes eksen A5 ayni parti-basi sapma sinifini "tek bir kacak jeton BES EVIN yayinini birden durdururdu" gerekcesiyle **bilerek** bloklamayan seviyeye cekmis. A4'un ayni maruziyeti var, ratchet YOK. Olculen latent yuzey: ayni katlama `marka` dizilerine uygulaninca bugun **78** ikiz grubu (F-150/F150 198-3 · Citroen/Citroën 410-4 · Kia/KIA 353-1 …) — hicbiri bugun A4 yuzeyinde degil, ama o kayda `uyum` blogu geldigi gun **aninda deploy durdurucu**. Ratchet yapilirsa kabul sarti: sentetik YENI ikiz kirmizi yakmali, tabanda kayitli ikiz yesil kalmali — kontrol mutanti olmadan taban civilemek ekseni sessizce **no-op**'a cevirir.

**OLCULEMEDI (uydurulmadi):** `serit-a4` hukmu — tur sonunda hala `in_progress`. `31304782641` tur sonunda kuyrukta. Yayin acligi olcum aninda ~8,5 saat / 24 commit; son basarili deploy hala `3e7f1b24` (00:45:56Z).

**Ana checkout'taki commit'siz `tools/build.py` + `tools/faz3-yuk.js` (aday A) artik ISLEVSIZ:** build o dosyalar olmadan **yesil** olculdu (`55ae7851` ayri koldan kapatti). Sahibi dusursun; KraL dokunmadi, ezmedi.

**SONRAKI TURUN ILK ISI:** (a) MaCiT A4'u kapatti mi (`uyum-kapisi.py` rc=0 mi); (b) `31304782641`'de `serit-a3` ADIYLA success mi — konfigur onariminin kaniti; (c) `serit-a4` hukmu ADIYLA; (d) A4 ratchet karari (yukaridaki kabul sartiyla) muhendise verilsin mi.


## ⏱ SAATLIK CI NOBETI — 9 Agu 06:37Z turu (ev DOGRU: ~/dev/pruvo)

**Supurme (kosulsuz, §0.5):** kutu 7538 · GitHub toplam 1 · "Run failed" 1 → Cop'e **1** · tur sonu kalan **0**. Pozitif tanima izi ALINDI (kontrol eksenleri `google.com` **1801** · `pruvo3d.com` **12** — eslestirici calisiyor) → hukum SUPURULDU, OLCULEMEDI degil.

**🔴 ASIL IS — yayin blokajinin TEK sebebi olculdu ve KAPATILDI.**
Onceki iki tur "iki blokaj" demisti. Bu turda CI kuyruguna kosum EKLEMEDEN, PRISTINE worktree'de (`origin/main` = `bacb7e1e`) IS DUZEYINDE olculdu:
- `build` **KIRMIZI** — `Statik sayfalari uret` (`tools/build.py`): ozet.json **154530 B > 153600 B** (`OZET_BUTCE = 150*1024`); `EDGE_KATALOG=true` oldugu icin uyari degil `sys.exit(1)`. Katalog 23105.
- `serit-a2` **rc=0 YESIL** (22 iddia) · `serit-a3` **rc=0 YESIL**. Yani onceki turlarin "ikiz de blokaj" hukmu BU head'de gecerli DEGILDI — tek blokaj `build`.
- ⚠️ `tools/faz3-yuk.js` HICBIR workflow adiminda CAGRILMIYOR (grep 0 isabet): oradaki butce kolu CI'da tetiklenmeyen OLU kapi. Kirmiziyi yalniz build.py'nin gomulu kapisi yakiyor.

**Iki rakip onarim DEVRALINDI, olculdu, IKISI DE REDDEDILDI** (ikisi de ~2 saat sessiz: yerel diff mtime 05:09:50Z **iki turdur degismedi**, dal worktree son yazma 05:08:02Z, push YOK, muhendis raporu YOK):
- **A** (ana checkout'ta commit'siz `tools/build.py` +140/-41 · `tools/faz3-yuk.js` +27/-5; bayt-geribeslemeli havuz kirpma): ozet **153593 B** — butceyi 7 B ile geciyor — ama `tools/eski-fiyat-test.py` **rc=1**: enjeksiyon ~22 B buyutunce dongu BIR KART FAZLA kirpiyor (Marin 100→98 vs 100→99), yani ozet ICERIGI katalogun degil BAYT BOYUTUNUN fonksiyonu oluyor. Bloklayici kapida kirmizi.
- **B** (dal `onarim/ozet-butce` `854202d5`, push EDILMEMIS; kayipsiz dizi-sikistirma): ozet **134564 B**, en iyi ham sayi, butce GEVSETILMEMIS — ama `serit-a3`teki UC tuketiciyi guncellememis (`tools/edge-kart-kapisi.py` · `shop/test/sepet-panel.js` · `jenerator/test/vitrin-kabul.js`); `vitrin-kabul.js` **7/9**'a dusuyor (kart objesi bekleyen kod dizi aliyor, `kart.id` undefined). B'nin bayt fikri KALICI cozumdur; eksigi cozucunun yazilmamasi.
- Ikisi de DOKUNULMADI/EZILMEDI: A hala ana checkout'ta commit'siz, B hala dalda.

**INEN ONARIM (KENDI kolu, en kucuk patlama yaricapi) — `55ae7851`:** `index.html` `VITRIN_BLOKLAR` havuz **100 → 88** (Marin, Otomobil). **Butce SABIT 153600** — gevsetme YOK, adim silme YOK, `continue-on-error` YOK. Olculen: ozet **154530 → 143232 B**, `build.py` **rc=0**.
Zorunlu yan onarim: `tools/vitrin-siralama-test.js` `fiksturB` havuz=100'e civiliydi ve yalniz 8 kalemlik payi vardi → HERHANGI bir yuk azaltmasi iddia 12a'yi `yetersiz=false` ile dusuruyordu; pay tek ustsuz terimden verildi (parametrik 4→40) ve **iki kontrol mutantiyla** 12a/12b'nin hala atesledigi dogrulandi.
Havuz 88 secimi OLCUMLE: yuk 1 Agu'dan beri **137676 → 154530 B** ve **gunluk ±7 KB oynaklik** var (yeni urun aciklama metni + `markalar` haritasi 30136 B) → 6533 B paylik havuz=92 secenegi TEK GUNLUK gurultunun icinde kaldigi icin REDDEDILDI.

**🔴 YAYIN HALA ACILMADI — sebep DEGISTI: iki YENI kirmizi tur ORTASINDA indi (`a046296a`, kardes oturum):**
1. `serit-a2` → `tools/uyum-kapisi.py` A4: katalog model ikizi (bosluklu vs bosluksuz iki ham yazim, iki model) **4 kayit**. **MaCiT duzlemi — KraL urun verisine DOKUNMAZ.** Posta kutusuna yazildi.
2. `serit-a3` → ic rapor adi kapisi: `DEVAM.md:7` ic rapor dosya adini tasiyordu. Kardes oturumun commit'siz kopyasinda ZATEN duzeltilmisti; bu turun defter commit'iyle iniyor. → [[nobet-kendi-defteri-yayini-durdurur]] (tekrar eden sinif, ikinci kez)

**OLCULEMEDI (uydurulmadi):** `55ae7851`in kosumu **`31302602408` KUYRUKTA, hic BASLAMADI** — onceki commit'in kosumu (`31301608015`) hala in_progress ve `cancel-in-progress: false`. ~22 dk beklendi. `build`/`serit-a2`/`serit-a3`/`serit-a4`/`deploy`/`yayin` hukmu tur sonunda OLCULEMEDI. Yayin acligi olcum aninda **19 commit / ~340 dk**; son basarili deploy hala `3e7f1b24` (00:45:56Z, kosum `31286873618`).

**Kapanan AYRI sinif:** `yayin-erisim-alarmi` 04:40Z'de 1/328 sayfa **503** diyordu; 06:03Z kosumu **328/328 = 200** (HUKUM ACIK) ve canli `curl` de **200** (kontrol ekseni anasayfa 200). Kendiliginden duzeldi, yayindan BAGIMSIZ dogrulandi — varsayilmadi.

**TUR KAPANISINDA OLCULEN (08:45Z):** defter + ic-ad kapisi commit'i **`68852391`** push'landi (kapilar rc=0: ic rapor adi · defter sinif · kisisel veri; arsiv kayipsiz eklendi; yabanci diff STAGE EDILMEDI). `55ae7851`in kosumu `31302602408` **cancelled** (yeni push kuyruktakini dusurdu — beklenen, icerik KAYBOLMADI: `68852391` onun ardili). Yeni kosum **`31303970771`** (head `68852391`) UCUSTA: `build`/`serit-a2`/`serit-a3`/`serit-a4` dordu de **in_progress** → hukum tur sonunda **OLCULEMEDI**, yesil SAYILMADI. `Paket tazeligi alarmi` hala failure (aclik semptomu, ayri kol).
**MaCiT postasi UCUNCU kez yazildi (08:41Z)** ve ikiz LOKALDE yeniden uretildi: `uyum-kapisi.py` rc=1 — `{'townace': ['Town Ace','TownAce'], 'liteace': ['Lite Ace','LiteAce']}`, gecen 38 · kalan 1. Olculmus maliyet 08:41Z: `3e7f1b24..HEAD` **23 commit / ~476 dk**.

**SONRAKI TURUN ILK ISI:** (a) `31303970771`in `build` hukmunu ADIYLA olc — yesilse ozet onarimi kanitlanir; (b) MaCiT 4 kayitlik ikizi duzeltti mi (`serit-a2`); (c) ikisi de yesilse `deploy`/`yayin` indi mi — canli `last-modified` ile teyit; (d) B dalinin dizi-sikistirmasi + 3 tuketici cozucusu KALICI is olarak muhendise verilsin mi karari (havuz 88 yalnizca gecici pay satin aldi; egilim ±7 KB/gun).

## 2026-08-09 05:37Z — CI nöbeti (KraL)
- Süpürme: GitHub toplam 1 · "Run failed" 1 → Çöp'e 1 · tur sonu kalan 0. Pozitif tanıma izi VAR (substring eşleşme, toplam > 0), hüküm TEMİZ.
- CI HÜKÜM: KIRIK — bir önceki tura göre DEĞİŞMEDİ. Canlıdaki son başarılı deploy hâlâ `3e7f1b24` (00:45:56Z, koşum `31286873618`); main `bacb7e1e`, arada 20 commit yayınlanmamış, yayın açlığı ~5 saat.
- İki blokaj AYNEN duruyor, ikisi de bu turda ELLENMEDİ:
  1. `build`: ozet.json bayt bütçesi aşımı. Onarım İKİ AYRI biçimde uçuşta — (a) ana checkout'ta commit'siz `tools/build.py` + `tools/faz3-yuk.js` (mtime 05:09:50Z, ölçüm anında ~33 dk taze = CANLI iş, öksüz DEĞİL); (b) dal `onarim/ozet-butce` uç `854202d5`, main'in 1 commit önünde, main'den geride 0, uzağa push EDİLMEMİŞ, worktree ~43 dk hareketsiz, mühendis raporu YOK. Sıra posta kutusunda 05:1xZ'de kararlaştırılmış: (a) önce insin, (b) üstüne rebase olsun. HÜKÜM: bu turda MERGE YOK — (b)'yi almak (a)'nın commit'lenmemiş dosyalarını ezerdi.
  2. `serit-a2`: A4 model ikizi (aynı normalize değere düşen iki ham yazım), tam 1 kayıt. MaCiT düzlemi; posta 04:2xZ'de yazıldı, ~80 dk sonra katalog commit'i DEĞİŞMEDİ (son dokunan `3ab04a9d`) ve ikiz lokalde hâlâ ölçülüyor. Posta TEKRAR yazılmadı (gürültü).
- `yayin-erisim-alarmi` kırmızı — AYRI SINIF, açlığın semptomu DEĞİL: 1 yayınlanmış sayfa canlıda HTTP 503, 327 sayfa açık, 0 ölçüm arızası. Yayın inince kendiliğinden yeşile döneceği VARSAYILMAYACAK, ayrıca ölçülecek.
- `paket-tazelik-alarmi` kırmızı = açlık semptomu (çıkış 4; taranan 8 koşumda `deploy` işini başarıyla koşan koşum yok). `serit-b` mutasyon kırmızısı (18 öldürücüden 5 hayatta) yayını BLOKLAMAZ — ayrı kuyruk.
- BU TURUN İCRASI ve DERSİ: `pages` grubu BOŞ ölçüldü (uçuşta koşum yok) → `workflow_dispatch` ile `31297165688` tetiklendi. Sonra defterin son nöbet notu okununca AYNI head üzerinde `build` + `serit-a2`'nin ölçülmüş kırmızı olduğu görüldü → `deploy` bunlara `needs` ile bağlı olduğu için yeşil bitemezdi, buna karşılık `pages` grubunu ~48 dk tutup (tavan `serit-a4`) onarım push'unun deploy'unu kuyruğa itecekti → koşum İPTAL edildi. DERS: dispatch'ten ÖNCE defterin son nöbet notu okunur; "grup boş" ile "yayın yapılabilir" AYNI ŞEY DEĞİLDİR.
- SONRAKI TURUN İLK İŞİ: (a) ana checkout'taki commit'siz `build.py`/`faz3-yuk.js` indi mi — inmediyse mtime ilerledi mi (~2 saat sessizlikte öksüz sayılıp devralınacak); (b) MaCiT ikizi düzeltti mi; (c) ikisi de indiyse yeni push'un `build`/`serit-a2`/`deploy`/`yayin` hükmünü ölç; (d) 503 veren sayfayı yayından BAĞIMSIZ ölç.

## ⏱ SAATLIK CI NOBETI — 9 Agu 04:37Z turu — dokum ARSIVDE (supurme 1→Cop temiz; build ozet.json 154530>153600 + serit-a2 ikizi iki BASKA duzlemde, ellenmedi; olu kosum `31293979280` iptal edildi, `pages` grubu acildi; yayin-nabzi acligi ardisik 3 kosum)

## 🔁 KraL DEVIR (clear oncesi yazildi) — SIRADAKI TEK IS: `muh/marka-tek-sayfa` dalini KAPAT
**Okan emri (bu gece):** dali baslat; MaCiT mesgul oldugu icin 215 urunluk VERI onarimi BEKLIYOR.
Dal: `muh/marka-tek-sayfa` **`73adb519`** (push'lu, worktree bugun KALDIRILDI → yeniden `worktree add` gerek).
Hukum (Okan): marka sayfasi markanin TUM parcalarini kart listeler, cipler **sayfa ici filtre**.
Olculen: gorunur kart **11731 → 21628** (audi 200→331 · ford 488→2583 · bmw 1010→2347), azalan marka **0**,
kimlik sapan sayfa **32 → 0**, tavani asan sayfa **11 → 0**. Iddia 10871, davranis testi 20/20.
Onceki curutme 1. turda MERGE_EDILEMEZ demis, UC kirmizi kapatilmis (teslim yolu tautolojisi ·
agirlik regresyonu → edge `/katalog?ids=` · ci-kapsam kablolama).
⏭ **EKSIK OLAN:** mutasyon bataryasi + ilk-yuk bayt tablosu → **dar curutme (yeni yuzey)** → merge + canli dogrulama.
⚠️ Merge oncesi ZORUNLU (bugun iki kez yayin durdu): `is-akisi-kapisi.py` rc=0 + yeni adim `serit-b`'ye
DUZ TEK KOMUTLA kablolu + `SERIT_B` beyani AYNI commit'te; ayrica `varlik-test.py` rc=0.
Bu dal ayrica sayfanin kendi ic sayac celiskisini kapatir (baslik 330 ↔ cip toplami+diger 370).
🔴 **KAPANMADI, ayri is (VERI duzlemi/MaCiT):** basliginda marka gecen ama `marka[]` uyesi olmayan
**215 urun** (Mini 42 · Grom 29 · K100 19 · Datsun 18…). `arama.py` gecis kolu **ONCE KAPATILMAYACAK**
(arama daralir, satis yolu). Ayrica acik: H1/H3 kurali **16 model-olmayan** degeri model sayiyor.

## ✅ BANNER LCP ONARIMI CANLIYA INDI + ONCE/SONRA OLCULDU — 9 Agu 00:46 (kosum `31284643156`, head `062f8cb2`)
`e907eac7` 8 Agu 22:16'dan beri main'deydi ama **hicbir kosum onu yayinlamamisti**; kendi kosumu
(`31281327794`) cancelled, ardil kosumlarda `serit-a2`+`serit-a3` defter sinif kapisindan kirmizi.
Kalan tikanikligin sebebi bu kirmizilar DEGILDI (onarim `e56705a2`'de; iki kapi da main tepesinde
rc=0 olculdu): kuyruk `bdddaee0` kosumunda (`31282011345`) kilitliydi — `serit-a4` ucusta, ama
`serit-a2`/`serit-a3` ZATEN kirmizi oldugu icin o kosumun `deploy`'u garanti `skipped`'ti; `pages`
grubunu tutan bu OLU kosum iptal edilince kuyruk acildi ve `31284643156` **deploy + yayin success**
verdi (artefakt `last-modified 00:45:42Z`, `cf-cache-status=HIT`, `age=0`).
**Canli kabul (canonical adres, cache-bust YOK) — 6 eksen:** `<picture>` **6** · `rel=preload`+
`as=image` **1** · `preconnect` **1** · `-v2-*.webp` benzersiz anahtar **18** · v2'siz banner webp
**0** · eski uc anahtarin toplam gecisi **0**. `fetchpriority="high"` **2** cikti; beklenti 1 idi ve
**beklenti yanlisti**: head preload + govde LCP `<img>` ikisi birden tasimak ZORUNDA (ayrisirsa
gorsel iki kez iner) — kaynakta 23. ve 1036. satir, yani 2 DOGRU sayidir.
**PSI mobil (Lighthouse 13.4.1, emule Moto G Power / yavas 4G) — ONCE (8 Agu, TEK kosum) → SONRA
(9 Agu 00:56-01:02Z, UC kosum):** performans **74 → 88 · 92 · 98** · LCP **10,7 → 2,1-3,4 sn** ·
SI **2,4 → 1,1 sn** · FCP **1,1 → 1,1 sn** · TBT **100 → 10-170 ms** · CLS **0 → 0**.
Regresyon kontrolu: erisilebilirlik **100** · en-iyi-uygulamalar **100** · SEO **100** — ucu de
UC kosumun UCUNDE de degismedi.
🔴 **Tek kosum yaziLMADI, ARALIK yazildi:** ilk kosum 98/2,1 sn okundu, bagimsiz ikinci tur 92/3,4 sn
ve onbellekten okunan ucuncu bir rapor 88 verdi. Performans ±5, TBT 10-170 ms salindi; yani tek
PSI kosumunu "sonuc" diye civilemek bu sayfada **yaniltici**. Salinimin ALTINDA kalan hukum yine de
tartisilmaz: LCP **10,7 sn → en kotu 3,4 sn**, yani en kotumser okumada bile ~3x iyilesme, ve TBT
ekseni gurultunun icinde (100 ms tabani araligin ORTASINDA) — TBT'de regresyon IDDIA EDILEMEZ.
🔴 **Atif siniri:** olculen sayfa `062f8cb2` ve bu commit `b7cdc015`'i ICERMEZ (`--is-ancestor`
rc=1) → yukaridaki kazanc **WebP kolunun TEK BASINA** kazancidir; AVIF kolunun EK katkisi HENUZ
olculmedi. Kardes turun bekledigi kosum `31286873618` (head `3e7f1b24`, `b7cdc015` ICERIR) ucusta.
ℹ️ Anahtarsiz PSI REST ucu **8 denemede de HTTP 429** verdi; sayilar PSI'nin web arayuzunden
gorsel-sinif isciye okutuldu, uydurulmadi.
**EK TUR — 9 Agu 06:42Z, AVIF kolu CANLI (`last-modified 01:47:30Z`):** taze PSI mobil kosumu
performans **99** · LCP **2,0 sn** · FCP 1,1 · TBT 90 ms · CLS **0** · SI 1,1; erisilebilirlik/
en-iyi-uygulamalar/SEO **100/100/100**. Canli HTML: `<picture>` 6 · preload 1 · preconnect 1 ·
`fetchpriority=high` 2 · banner **webp 18 + avif 15** benzersiz · `type="image/avif"` **6** ·
eski anahtar **0**; preload edilen gorsel **HTTP 200, `image/avif`, 40007 B** (servis ediliyor).
Boylece kardes turun bekledigi AVIF canli teyidi KAPANDI — beklenen `type="image/avif"` 5 idi,
olculen **6**; fark kusur degil, o beklenti preload satirini saymiyordu.
🔴 **"Performans hala 74" bildirimi CANLI GERILEME DEGILDI (olculdu):** 74, 8 Agu tabaniyla
BIREBIR ayni sayidir ve PSI web arayuzu ayni adres icin **onbellekten kayitli rapor** sunar
(bu turda da bir kosumda 88'lik bayat rapor onbellekten geldi, zorla yeniden analizle 92'ye dondu).
Ders: PSI hukmu **rapor zaman damgasi** teyit edilmeden alinmaz; skor degil, damga karsilastirilir.
Alan (CrUX) verisi ayrica **YOK** ("yeterli gercek dunya hiz verisi yok") — yani saha egrisi bu
sayfada henuz hicbir hukum tasimiyor.
⏭ AYRI IS (banner disi, bu onarimin kapsaminda DEGIL): taze raporun en buyuk gorsel firsati
**229 KiB** ve kaynagi urun **kart kucuk resimleri** (`/urunler/*-thumb.jpg` gorunenden buyuk
sunuluyor); banner gorselleri o tabloda yalniz 4-13 KB'lik artiklarla goruluyor.

## ✅ R2 AVIF WHITELIST'I + BANNER AVIF KOLU main'e ALINDI — 9 Agu 00:47 (merge `b7cdc015`) — dokum ARSIVDE
R1 sihirli-bayt whitelist'i AVIF'e acildi (`tools/r2-upload.py`, kabul testi 91/91) + banner 15 yeni R2 anahtari (canli teyit 15/15 200) + `lcp-onculuk-kapisi.py` format-agnostik yapildi (A8/A9 eksenleri). Canli dogrulama TAMAM: kosum `31286873618` success, `<source type="image/avif">` 5 · `<picture>` 6 · benzersiz `banner/*-v2-*.avif` 15. Mobil kume 201,0→170,9 KiB (-%15,0). Tam dokum: DEVAM-ARSIV.md.

## ✅ KATALOG ALAN KAPISI main'e ALINDI — 8 Agu 22:35 (merge `bdddaee0`) — dokum ARSIVDE
Dal `claude/suspicious-ishizaka-414f35` merge commit'iyle alindi (ff IMKANSIZ, cakisma 0, kapsam 9 dosya +1054/-1). Merge sonrasi kapilar rc=0, D1 dort eksen YESIL. Yan etkisi (kardes fikstur ikizi) ve daha eski defter-sinifi kirmizisi KAPANDI. Tam dokum: DEVAM-ARSIV.md.
## 🔚 OTURUM KAPANISI — 8 Agu (yayin blokaji + marka sayfasi turu) — dokum ARSIVDE
CANLIYA GITTI 5 SHA (`d3fbc1e5`/`b36c208b`/`36d57ce6`/`d81349b6`/`e94433f9`, sabit-yol-kapisi+yayin-kor-yesili+BASLIK_DOGAN turetme+oksuz CI kablosu onarimlari) + yayin acildi (22376==22376). KOSUYOR: `muh/marka-tek-sayfa` (Okan hukmu: marka sayfasi TUM parcalari listeler) — dal simdi `73adb519`'a ilerledi, guncel durum ustteki KraL DEVIR blogunda. BEKLIYOR 7 kalem + OKAN'DA BEKLEYEN 5 karar (timeout-minutes, GPL/LGPL/BSD, Drive yedek vb.) — tam dokum: DEVAM-ARSIV.md.

## ✅ NOBET NOBETCILERI SERTLESTI — dal main'e ALINDI (8 Agu 22:20, dokum ARSIVDE)
Merge --ff-only d9485a0d, kapsam 3 dosya +589/-61, sizinti 0. Olu koruma 48 birim kapatildi (tablo 18/18, pay 0). Merge sonrasi kapilar: D1 dort eksen rc=0 (22685) · CI kapsam rc=0 (246 kesif) · is-akisi rc=0 + kendini-test rc=0 (204 iddia) · nobetci mutasyon 7/7 + kontrol YESIL. Ders: ff uygunlugu YEREL main ile olculur. Temizlik bilerek yapilmadi. Tam dokum: DEVAM-ARSIV.md.
## ⏱ SAATLIK CI NOBETI — 9 Agu 02:37Z turu — dokum ARSIVDE (supurme 0 esleme → Cop 0, pozitif tanima izi alindi; D1 uzlastirici kapandi — dort eksen 23034==23034; ASIL BULGU: aclik kuyruk degil `deploy: needs` kirmizisiydi, olu kosum `31288785522` iptal edildi, icerik kaybi 0; serit-a2/a3 kardes oturumun `5d576510`'uyla ADIYLA success; serit-a4/build/deploy/yayin OLCULEMEDI; tavan isi worktree'si 47 dk sessiz)

## ⏱ SAATLIK CI NOBETI — 9 Agu 01:37Z turu — dokum ARSIVDE (supurme temiz 1->Cop; serit-b + D1 uzlastirici kapandi; yayin acligi (Paket tazeligi/yayin-nabzi ardisik 2 kirmizi) muhendise devredildi, tavan dusurme dalda; `6b15062b` deploy/yayin OLCULEMEDI)

## ⏱ SAATLIK CI NOBETI — 8 Agu 23:37Z turu — dokum ARSIVDE (supurme hukmu OLCULEMEDI; serit-b + serit-a2/a3 kapandi, `31284643156` 6/6 success)

## Onceki turlarin VE 7 Agu oturumunun TAM dokumu — ARSIVDE (DEVAM-ARSIV.md, git disi).
