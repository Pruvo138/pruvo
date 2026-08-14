# DEVAM (KraL) — 8 Agu 2026

## 14 Agu 2026 — ACIK KALEM SUPURMESI: yayin tikanikligi + dal/oturum temizligi (KraL, interaktif)

**CANLIYA GIDEN (SHA):** `89941482` · `b0203209` · `6ee9ead2` (ucu de push'lu, main FF).
Okan'in "tum acik gorevleri tamamla, isi biten gorev ve oturumlari temizle" emri.

**YAYIN TIKANIKLIGI — TEK KOK, IKI FIKSTUR, UC KAPI.** `ebebb966` pre-push'a **0c** bolumunu
(K80 yeni-CI-adimi hukum kapisi) ekledi. O tek adim gun boyunca UC ayri yerde patladi:
- `89941482` **K98/serit-a3:** `ci-kapsam-test.py --kanca-kablo` D2 fiksturu 0b bolumunu
  ayikliyor ama bitis capasini KOMSU bolumun basligina baglamisti -> araya 0c girince fikstur
  0b sanip 0c'yi de kosturdu, sentetik depoda olmayan araci aradi -> **YANLIS-KIRMIZI**.
  Onarim: 0b artik **KENDI capasiyla** biter (capa silinirse ayiklayici fail-closed durur,
  KOPYA uzerinde mutasyonla kanitlandi) + acilan delik ayni commit'te kapandi: 0c adimi
  `kanca-nobeti::BEKLENEN` + `kanca-kablolama::FAIL_CLOSED` envanterlerine girdi.
- `6ee9ead2` **K85/serit-a2:** ayni adim KARDES fiksturu de kirdi —
  `prepush-d1-kaynak-test.py` sentetik depoya GERCEK kancayi kuruyor ama bagimliliklarini
  **elle tutulan** listeden stub'liyordu; liste bayatlayinca push dustu, kayit yazilmadi,
  `os.unlink` **TRACEBACK** verdi. Onarim: stub kumesi artik **kanca govdesinden TURER** ve
  turetim **kabuk semantigini** izler (`[ ! -f X ] exit 1` -> STUB · `[ -f X ]` -> YOK KALIR ·
  guardsiz cagri -> STUB); iki kume de her kosumda BASILIR. Ayrica kirmizi iddia artik
  tanisiz cokmeye donmuyor (`unlink` idempotent). "Hepsini stub'la" ilk denemede OLCULDU ve
  YANLIS cikti (opsiyonel bloklar kosunca fikstur davranisi degisti) — kural ondan sonra daraldi.
- `b0203209` **K80/silme kolu:** ayni kapi `git push --delete`'i "OLCULEMEDI" sayip rc=2
  veriyordu -> **27 erimis dalin temizligi imkansizdi.** Ayrim yapildi: TUM satirlar silme ise
  KAPSAM DISI (rc=0, gurultulu basilir); girdi BOS ise fail-closed OLCULEMEDI KALIR; karisik
  push'ta guncellemeler yine OLCULUR. Muafiyet nobetsiz kalmasin diye `--kendini-test`e
  **iki yonlu** vaka (S1 silme=kapsam disi · S2 bos=olculemedi) eklendi.

**TEMIZLIK (Okan'in emrinin ikinci yarisi):** 9 artik yerel dal · **27 erimis uzak dal**
(her biri `merge-base --is-ancestor` ile main'de dogrulandi, kayip YOK; kalan 29 dal is
tasiyor, DOKUNULMADI) · 6 isi bitmis oturum arsivlendi (5 mimar evi + bu oturum duruyor) ·
3 merge dali + worktree acildigi turda kapatildi. `worktree list` **tek satir**.
Uzak dal denetiminde 57 dalin agacinda ic-rapor dosya adi tarandi -> isabet **0**.

**KAPANAN ACIK KALEM (kabul komutu kosturularak):** **K59** boy varyanti (`116128af`) ·
**K69** kanca envanteri (`116128af`) · **K71** D1 makineler-arasi lease (`116128af`) ·
**K97** uzak dalda ic rapor (`ic-rapor-adi-kapisi --uzak` rc=0, isabet 0). **K98** kalemi
nobet kapisinin kendi kabul komutuyla kapanacak (`prepush-d1-kaynak-test.py` artik rc=0) —
o satiri cron sahipleniyor, elle EZMEDIM.

**KOSUYOR (sonraki turun ILK isi):** `6ee9ead2` Build & deploy **ucusta**
(`31792235940`). Ucustaki kosum yesil degildir: hukum SHA'yi ICEREN kosumdan alinacak.
Yayin bu turdan once **6 commit / 115 dk** geride ve `deploy` SKIPPED idi.

**🔴 BLOKE — OKAN'DA (2):**
- `tools/yedekle.py` Drive hedefinde **`Operation not permitted`** ile duser (rc=1); yedek
  yarim kalmis, tazelik damgasi YOK ve her push `!! YEDEK alinamadi` basiyor. macOS
  dosya-erisim izni sinifi -> Okan kapisi. **Depo yedeksiz durumda.**
- `media.pruvo3d.com` tekil purge icin Zone.Cache Purge izinli token (onceki turdan devir).

**🔴 GUNUN DERSI:** *kancaya adim eklemek, o kancayi TAKLIT eden her fiksturun bagimliligini
degistirir.* Bugun tek bir yeni adim iki kardes fiksturu ard arda kirdi ve yayini saatlerce
durdurdu; ikisi de "elle tutulan bir liste"ye yaslanmisti. Kural: fikstur, taklit ettigi
seyin bagimlilik kumesini **turetmeli**; ve bir bolum komsusunun basligiyla degil **kendi
capasiyla** bitmeli ([[kardes-fikstur-yeni-kanca-adiminda-kirilir]] ·
[[kapsam-evrenini-cagri-grafindan-turet]] · [[kapi-anchor-coupling-ikilemi]]).
Ikinci ders: fail-closed'in dogru yeri "olcemedim"dir — **"olcecek sey YOK" ile "olcemedim"
ayni sey degildir**; ayrilmazsa kapi kapsamindaki isi degil kapsamindaki HERKESI durdurur.

## 14 Agu 2026 ~10:07Z-t17 — SAATLIK CI NOBETI (KraL, cron, ev=DOGRU)

SUPURME: `mail-supurme-kos.sh` → rc=0 · `GITHUB_BILDIRIM_INBOX=5 BULUNAN=5 TASINAN=5 ATLANAN=0 CIKAN=5 KOMSU_KAYIP=0 KUME_DIFF=OLCULDU KALAN=0 COP_IZI=342:2026-08-14T13:04:42 HUKUM=SUPURULDU`. 5 mail (Build & deploy `8bae6e9`+`116128a` · Odeme bayatlik `8bae6e9`+`116128a` · Nöbet SERIT B `ca146ce`) — hepsi `github+Run failed` yüklemine uyuyor. Önceki turun (t15) `KOMSU_KAYIP=1` alarmı bu turda **0**.
COP_DENETIM: Pruvo hesabı **MESRU=110 / YANLIS=0 / KAPSAM=110 / ATFEDILMEYEN=25** — süpürme temiz, yanlış sınıf 0; sipariş/ödeme kaybı YOK.

GH CI BAĞIMSIZ TEYİT (HEAD `89941482` "fix: K98"): Codex'in K98 düzeltmesi main'e push'lu, CI uçuşta. **Ölçülen: K98 düzeltmesi KISMI** — K80 bacağı KAPANDI (`ci-kapsam-test.py --kanca-kablo` lokal rc=0) ama **K85 bacağı (`prepush-d1-kaynak-test.py`) HÂLÂ KIRIK**: lokal rc=1 (`os.unlink(kayit_a)` FileNotFoundError:233) + `89941482` koşumu `serit-a2` zaten **failure** (`31790776423`; `serit-a3` in_progress, `deploy`+`yayin` yine skipped). **Yayın HÂLÂ BLOKLU.**

§3 DUR: serit-a2 (`prepush-d1-kaynak-test.py` tmp idempotentliği) AYNI kök nedenden 3+ koşumdur kırmızı (`ebebb966` `31781775890` · `8bae6e9c` `31789322432` · `89941482` `31790776423`). K85 sınıf tekrarı; kalan onarım YALNIZ K85 bacağı (spec defterde K98 satırında). Yeni push YOK, mail silme zaten 5/5 yapıldı.
⚠️ TUR İÇİ HAREKET: ölçümümden SONRA aktif oturum (Codex işçisi) `b0203209` "fix: K80 kapisi SILME push'unu bloklamasin — kapsam disi ≠ olculemedi" itti (10:14Z) — K80 onarımı SÜRÜYOR (silme-push kolu ayrı sınıf); serit-a2 (K85 bacağı) hâlâ açık, sonraki tur teyit eder.

TAMIRCI BAKIM: **K95 KAPANDI** (mimar yargısı + ölçüm: `model-uyelik-kapisi.py` lokal `SONUC: 29/29 iddia GECTI`, `YARGISIZ` boş — 3 çift çözülmüş, STALE teşhisi doğrulandı). **K98** defter güncellendi: 89941482 K80 bacağını kapattı, K85 bacağı açık kaldı; dağıtım `nobet-kapi.py`'ye bırakıldı (kabul komutu `prepush-d1-kaynak-test.py` rc≠0 → BEYAN_VAR_KANIT_YOK ile AÇIK kalır, yeniden dağıtılır).
OKAN'A ÇIKIŞ: YOK (§5 — mekanik kod onarımı, Okan kararı gerekmiyor; K80 zaten ESKALASYON=OKAN, K91 OKAN-KAPISI).

## 14 Agu 2026 — BOY VARYANTI + D1 LEASE + 3 BAYAT/KABLOSUZ KAPI (KraL, interaktif)

**CANLIYA GIDEN (SHA):** `116128af` (push'lu, main FF) — 17 dosya, +887/-64.
Ana agacta commit'siz duran 3 kumeyi kabul bataryasindan gecirip kapattim (kaynak commit'i
mimar kod-kilidine takildi → merge dali `fix/boy-lease-kapilar` acildi, commit orada, main
FF ile ilerledi, dal+worktree AYNI TURDA kapatildi; `worktree list` **tek satir**).

- **K59 BOY_SECENEKLERI uctan uca acildi:** sema (arama.py kanonik) → D1 kolonu + urun hash'i
  → edge sepet karti (`build.kart_ozeti`) → odeme Worker'i. Worker artik istemci `boy_etiket`
  degerini D1'deki KANONIK listeye karsi dogruluyor, fark site ile AYNI `secenekler.js boyFarki`
  cekirdeginden geliyor. 4 fail-closed hukum: gecerli boy 200 · bilinmeyen etiket
  `gecersiz-boy` · secim atlanmis `boy-secimi-zorunlu` · kolonsuz D1 `boy-desteklenmiyor`.
  Kapi `tools/boy-secenekleri-kabul.py` deploy.yml'de **BLOKLAYICI** seride baglandi.
  Kardes depo ekseni (pruvo-bot edge Worker'i) yerelde **olculdu ve VAR**; kosucuda
  `EDGE=KAPSAM_DISI` diye BASILIR (sozlesme sahibi HocA deposu).
- **K71 D1 DAGITIK YAZICI LEASE'i:** flock makineler-arasi degil; kosucu×kosucu ve
  kosucu×yerel yarisinda ortak olan tek yer D1. Tek kosullu UPSERT + **sahiplik geri okumasi**
  ("wrangler rc=0" kanit sayilmaz) + uzun yazmada yenileme + cikista yalniz kendi token'ini
  silme. Kabul `tools/d1-dagitik-kilit-test.py` (6/6) deploy.yml'e baglandi.
- **3 KAPI ONARIMI (hepsi "kapi var ama olcmuyor" sinifi):**
  (a) `yayin-erisim-test.py` E7'nin son iddiasi `d4ccdfa1`den beri **BAYAT**ti — elle `SERIT_B`
  defterini sorguluyordu, o defter ayni commit'te bilerek bosaltilmisti (taban 0) → iddia HER
  ZAMAN kirmizi. Iddia AYNI, kaynak degisti: serit uyeligi **workflow'dan TURER** + bu kapi
  ISTISNA tablosunda YOK (elle muafiyet kacisi kapali). M15 mutanti yeni mekanizmayi olduruyor.
  (b) Yeni **E9 ROLLOUT** ekseni: canli sitemap'te henuz olmayan 404 yayin penceresidir, kirmizi
  degil; sitemap okunamazsa fail-closed KAPALI kalir (+M22). M2'nin capraz beyani E9'u tasiyor.
  (c) `kanca-devam-envanter-test.py`: pre-commit'teki `devam-sinif-kapisi` cagrisi iki nobetci
  envanterinde de **kayitsizdi**; kablosuz kapi `ci-kapsam`i kirmizi yakip `fiyat-prova` M3a'nin
  KONTROL on kosulunu dusuruyordu. Envanterler dolduruldu, kabul nobet.yml serit B'ye baglandi.

**OLCULEN (kosulan komut):** kabul bataryasi **10/10 rc=0** · merge kapisi dalin worktree'sinde
**8/8 rc=0** (`ci-kapsam` · `is-akisi-kapisi` · `kapi-envanteri` 7/7 · `yayin-erisim-test` 67/67 ·
`boy-secenekleri-kabul` · `kanca-devam-envanter` 5/5 · `d1-dagitik-kilit` 6/6 ·
`fiyat-prova` 13/13) · cakisma YOK · FF UYGUN · sizinti YOK ·
`d1-sync --durum` 27001=27001, hash UYUSMAZ/EKSIK/FAZLA **0**, turetilmis kolonlar GUNCEL.

**KOSUYOR (sonraki turun ILK isi):** `116128af` icin CI **ucusta** — `31789046024` Build &
deploy + serit B/odeme/spec-alarm kollari. **Ucustaki kosum yesil degildir**: SHA'yi ICEREN kosumun
hukmu alinacak. Push kancasi ayrica `!! YEDEK alinamadi` bastı (`tools/durum.py` ile bak).

**BENDE KALAN:** Q3 sis fari gorseli **vizyonla** teyit · `media.pruvo3d.com` tekil purge
(OKAN'da: Zone.Cache Purge token'i) · arsivden 4 kalem (`build.py` butce kirpmasi ·
`uyum-kapisi` kesme beyani · `arama.py` allow temizligi — `Toyota|86` 71 urun tasiyor, RISKLI).

**🔴 GUNUN DERSI:** *sinif kapisi kurmak, ondan besleneni bayatlatir.* `d4ccdfa1` elle serit
defterini kaldirdi ve TEK KAYNAK'i workflow'a tasidi — dogru karardi; ama o defteri okuyan
E7 iddiasi ve M15 mutanti ayni commit'te tasinmadi, ikisi de sessizce **olu** kaldi.
Mekanizmayi degistiren, o mekanizmayi OKUYAN her yeri ayni commit'te tasimali
([[ikiz-tanim-sessiz-ayrisma]] · [[bayat-kabul-testi]]).

## 14 Agu 2026 — OTURUM KAPANISI (KraL, interaktif; gece boyu)

**CANLIYA GIDEN (SHA):** `6f28a842` D1 seq **kuyruk** kolu bloga oranli adim (`adim=yuksek//(k+1)`)
→ 136 INSERT gecti, **EKSIK=0**, Ege paritesi BIREBIR (893 sorgu) · `2b19c28e` seq normalize
on-kosulu FAZLA eksenine · `4b6f16ac`+`15e89b11` panel: uretici kaynak linki (ayri `urun_kaynak`
tablosu, 26422 satir) + `<details>` acilir kart + `kaynakLinkHtml` regex kacislamasi (sablon
icindeki `\/` TUM client script'ini derlenemez yapiyordu) · **deploy `8081ccdf`** (panel canli;
yonet veri ucu cerezsiz 404, musteri ucu 200) · `a6a16a91` **ABS satisa geri acildi** — katsayi
ASA'dan **TURER** (`FILAMENT_TUREME`), 5 kategoride Worker fail-closed 400 · `37d62efc`
`onarim-commit.py` (kendi kendini tasidi) + `132fb1dd` **stash yarisi SHA ile kapatildi** ·
`0a921f92`+`fbe79882` STL uc-kopya nobetcisi + **158 eksik uretim dosyasi R2'ye** (9 stub imza
dogrulamasinda elendi) · `d4ccdfa1` **serit beyani sinif kapisi: elle defter 111→0** (serit artik
workflow'dan turer; `fiyat-prova` 13/13) · `a28e3262` `serit-a2` **aktif-referans ekseni**
(1697 anahtar kapsam disi, gercek kirik 0, whitelist'e 0 satir) · `74be7cdc` kova **916 + Mazda
B-Serisi ACILDI** (cok-sahipli esik 1/3 + ciplak sayi `marka[]` uyeligi; **KAPANAN_KOVA=0**,
Honda|B Serisi yayinda kaldi) · `47389674` **CDN negatif-onbellek kokeni** (readback CDN'den
S3 sondasina) · `29c3232e` ic-dil KAYNAK kolu · `35192543` yayin-gecikme tavani 75→**128**
(121 kosum olculdu, normal max 86.6 — nobetci **sahte tikanma alarmi** uretiyordu) ·
`1f1c2af5` defter bakimi (DEVAM 556→64 satir, **19/19 blok arsivde**, K20 iddiasi GERI CEKILDI).
**Nobet onarim bacagi kuruldu** (`~/.claude/cron/nobet-kapi.py`): `ACIK>0 & KAPANAN=0 &
DAGITILAN=0` → tur **BASARISIZ**; fan-out 4; kabul **kosulan komuttan** turer (3/3 guvenlik
vakasi: kabuk yok, beyaz liste, `..` kacisi) → **7 gunluk "0 onarim" serisi kirildi**, K49·K53·
K54·K55 kabul komutuyla dogrulanarak kapandi. Sıklık `37` → **`7,37`** (30 dk).

**KOSUYOR:** yok — tum delegasyonlar kapandi, `worktree list` **tek satir**, ana repo push'lu.

**BEKLIYOR / BLOKE:**
- 🔴 **YAYIN KAPALI, top MaCiT'te:** `7ba6287b` partisi iki SERIT A kapisini dusuruyor —
  (1) `c3d-audi-q3-sis-farı-montaj-braketi` id'sinde `ı` (U+0131, URL-guvensiz),
  (2) 14 kaydin `kategori` alani alt-bolum adi (`Dış Aksesuar` vb., CATEGORIES disi) → marka
  sayac **60 dusen**. Ikisi de `urunler.json` = MaCiT tek-yazar. Kutuya araclariyla yazildi.
- ⚖️ **KraL HUKMU (MaCiT'in sordugu guard kisiti):** `urunler-guard` byte-identical rename
  kisiti id-rename + alan duzeltmeyi ayni commit'te reddediyor. **Karar: (a) guard yamasi** —
  rename+duzelt kombinasyonu TEK islem sayilsin. (b) iki ayri commit gecici bozuk goruntu
  birakir, (c) sil-izin muafiyeti kapiyi gevsetir; ikisi de RED. Yamayi bir sonraki KraL turu yazar.
- **HocA:** `/ara` Worker bayat — parite kirmizisi **3 sorguya** indi (`arac`/`Otomobil`/
  `Land Cruiser 90 arac`); `urunler_fts` sayimi birebir, indeks TEMIZ → care Worker deploy'u.
- **Bende (siradaki):** `boy_secenekleri` deploy zinciri (MaCiT `--sema`'yi kosmus) · Q3 sis
  fari gorseli **vizyonla** teyit (ucuz motor gorsel okuyamiyor) · arsivden 4 kalem
  (`build.py` butce kirpmasi 34-commit cakisma riski · `uyum-kapisi` kesme beyani ·
  `arama.py` allow temizligi — `Toyota|86` 71 urun tasidigi icin RISKLI, tek basina uygulanmaz).

**OKAN'DA BEKLEYEN KARAR (1):** `media.pruvo3d.com` icin **Zone.Cache Purge** izinli Cloudflare
token'i. Olculdu: son partide 38 gorselin **19'u 404** (`cf-cache-status: HIT`), 100'luk genis
ornekte **17 404** — TTL 1 YIL, kendiliginden duzelmez. Kok neden kapandi (`47389674`), kalan
404'ler tekil purge ister (`purge_everything` KULLANILMAYACAK).

**🔴 GUNUN DERSI:** *beyan kanit degildir.* Nobet 167 turda 0 onarim yaparken hep `rc=0`
yaziyordu; isci "KAPANDI" derken sha baska depodaydi; MaCiT partisi "uctan uca kapandi" derken
CI kirmiziydi. Panzehir ayni: **kapanisi kosulan bir komuta bagla.** Ikinci ders: stash yigini
depo genelinde ORTAK — argumansiz `apply` komsunun isini alir ([[stash-yigini-ortak-yaris]]).

## 14 Agu 2026 ~11:07Z-t16 — SAATLIK CI NOBETI (KraL, cron, ev=DOGRU)

SUPURME: `mail-supurme-kos.sh` → rc=0 · `GITHUB_BILDIRIM_INBOX=5 BULUNAN=5 TASINAN=5 ATLANAN=0 CIKAN=5 KOMSU_KAYIP=0 KUME_DIFF=OLCULDU KALAN=0 COP_IZI=334:2026-08-14T11:07:45 HUKUM=SUPURULDU`. ebebb96 zincirinden 5 mail (Build & deploy + Odeme yolu bayatlik + Paket tazeligi + D1 uzlastirici + Nöbet şeridi SERIT B) — hepsi `github+Run failed` yüklemine uyuyor.
COP_DENETIM: Pruvo hesabı **MESRU=102 / YANLIS=0 / KAPSAM=102 / ATFEDILMEYEN=14** — süpürme temiz, yanlış sınıf 0; 14 ATFEDILMEYEN K92 sınıfı. Sipariş/ödeme kaybı YOK.
GH CI BAĞIMSIZ TEYİT (HEAD `ebebb966` "K80: yeni CI adimini commit agacinda olc"): **Build & deploy `31781775890` — FAILURE** (6 job: `serit-a2` + `serit-a3` failure, `serit-a4`/`build`/`deploy`/`yayin` ok ama 0 step — concurrency `cancel-in-progress:false` zincirinin beklenen davranışı). Kök neden iki ayrı sınıf:
- **serit-a2 `prepush-d1-kaynak-test.py:233`** `python3: can't open file '/tmp/prepush-d1-kaynak-t4o0lz5q/a/tools/is-akisi-kapisi.py': [Errno 2] No such file or directory` + sonrasında `os.unlink(kayit_a)` `FileNotFoundError: '/tmp/prepush-d1-kaynak-t4o0lz5q/a-kayit.json'` (tmp dizini cleanup sırasında silinmiş, script idempotent değil).
- **serit-a3 `ci-kapsam-test.py --kanca-kablo`** fikstürü düştü: `beklenen=YESIL gelen=KIRMIZI · davranis=['D2 kapi YESIL: kanca rc=1 (DURDU) · kapi rc=0 iken kanca GECIRMELI (yanlis-kirmizi tum ekibin yayinini durdurur)']` — yani kanca `rc=1` döndürüyor ama kapi `rc=0` diyor; kanca YANLIŞ durumda `rc=1` döndü.

Diğer ebebb966 koşumları: `D1 sapma alarmi (kadans kolu)` ✓ (K59 bilinen sınıfın bağımsız ekseni), `K80 yeni CI adimi` 4× (cron tetiklemeli; 2 failure / 1 success / 1 in_progress), `Nöbet şeridi SERIT B` in_progress. K95 kökü DEĞİL — 4518a3d + dd68cd7 build'leri başarılı geçmiş, model-uyelik-kapisi muhtemelen temizlenmiş; K95 stale olabilir (ayrı teyit gerekir).

§3 DUR KOŞULU: aktif fail `31781775890` Build & deploy (K80+K85 ortak sonuç); K80 zaten ESKALASYON (geri-iz `tur=16`, 3 dağıtım, OKAN'a düşmüş) · K85 KAPANDI görünüyordu ama bugün **sınıf tekrarı** — kabul ölçütü (`tools/prepush-d1-kaynak-test.py`) yine kırık. **Yeni push YOK, mail silme YOK** (zaten yapıldı: 5/5).

TAMIRCI BAKIM: **K98 GERÇEKTEN AÇILDI** (acik-kalemler.md satır eklendi: 2026-08-14 · Tamirci→Tamirci · K85 sınıf tekrarı + K80 ortak zincir — Build & deploy BLOKLU · onarım K85 idempotent cleanup + K80 fikstür eşleşmesi · KAT: codex · YASAK: urunler.json/secret/adım-silme/continue-on-error). Defter açık kalem sayısı **19** (önceki 18 + K98). K95 stale teşhis notu K98'in kapanış kanıtına düşüldü (mimar yargısı gerekir). §4.7.1 kapsamında dağıtım `nobet-kapi.py --tur` bir sonraki turda K98'i K95'in yerine distributed olarak işaretleyecek (kapı zaten yapıyor, ikinci kez işçi AÇILMAZ).

ONARIM: YOK (K98 dağıtımı kapıya bırakıldı; K80 zaten ESKALASYON=OKAN; K85 sınıf tekrarı K98 kapsamında).
OKAN'A ÇIKIŞ: YOK (§5 — K98 defterde, K80 zaten OKAN'a düşmüş, K95/K96/K97 §4.7.1 SIRADA, K91 OKAN-KAPISI; mimar kararı gerektiren yeni durum yok).
## 14 Agu 2026 ~07:37Z-t14 — SAATLIK CI NOBETI (KraL, cron, ev=DOGRU)

SUPURME: `mail-supurme-kos.sh` → `GITHUB_BILDIRIM_INBOX=0 BULUNAN=0 TASINAN=0 ATLANAN=0 CIKAN=0 KOMSU_KAYIP=0 KUME_DIFF=OLCULDU KALAN=0 COP_IZI=329:2026-08-14T07:07:53 HUKUM=TEMIZ`. Önceki turlar inbox'ı zaten süpürmüş, bu turda 0/0; COP_IZI=329 önceki süpürmelerin ürünü. §0.4 "0 bulundu pozitif tanıma izi ister" kuralı: COP_IZI ayağı inbox sayacı 0'ı TEMİZ'e çeviren geçerli ayak (aynı gün 07:07Z kayıtları) → hüküm **TEMİZ**.
COP_DENETIM: Pruvo hesabı **MESRU=97 / YANLIS=0 / KAPSAM=97 / ATFEDILMEYEN=14** — süpürme temiz, yanlış sınıf 0; 14 ATFEDILMEYEN K92 sınıfı (süpürme dışı yoldan gelen mailler, K92 kapsamı). Sipariş/ödeme kaybı YOK.
GH CI BAĞIMSIZ TEYİT (HEAD `dd68cd7a` "fix: pre-push D1 senkronu fail-closed (K85)"): son 8 koşumda 6 SUCCESS + 1 FAILURE (`31777286275` Odeme yolu bayatlik, K91/K30 sınıfı bilinen alarm kolu — **yayını DURDURMAZ** §2 + §4.5) + 1 in_progress (`31777286320` build & deploy zinciri 22+ dk, `serit-b` failure + `d1-kadans/uzlastir` failure — K86/K94/K97 + K59 bilinen sınıflar). Daha eski: `31775484640` Paket tazeligi ✗ (K95/K96+K30 sınıfı). **Düzeltme tetikleyen yeni arıza YOK** — tüm kırmızılar defterdeki açık kalemlerle eşleşiyor.
§3 DUR KOŞULU: aktif fail `31777286275` Odeme yolu bayatlik K91 (OKAN-KAPISI, 11 Ağu kararı); K86/K94/K97 §4.7.1 kapsamında `nobet-kapi.py` dağıtımında (t13'te dağıtıldı); K95/K96 §3 DUR'da (MaCiT tek-yazar, YASAK kapsam). Yeni push YOK, mail silme YOK.
TAMIRCI BAKIM: defter değişmedi (bu turda yeni kalem yok, kapanan yok); §4.7.1 kapsamında dağıtım `nobet-kapi.py --tur` t13'ün devamı olarak yürütülüyor. K85 KAPANDI commit dd68cd7a main'de (`merge-base --is-ancestor` önceki tur teyitli).
OKAN'A ÇIKIŞ: YOK (§5 — K97 defterde bekliyor, K95/K96 §3 DUR'da, K86/K94 codex SIRADA, K91 OKAN-KAPISI; mimar kararı gerektiren yeni durum yok).

## 14 Agu 2026 ~09:07Z-t15 — SAATLIK CI NOBETI (KraL, cron, ev=DOGRU) — KIRMIZI

SUPURME: `mail-supurme-kos.sh` → **ALARM rc=1** §0.4: `GITHUB_BILDIRIM_INBOX=3 BULUNAN=3 TASINAN=2 ATLANAN=1 CIKAN=1 KOMSU_KAYIP=1 KUME_DIFF=OLCULDU KALAN=2 COP_IZI=336:2026-08-14T12:07:50 HUKUM=OLCULEMEDI`.
- SILINEN 2 · ATLANAN 1 · 🔴 KOMSU_KAYIP 1 kimlik dokumu **DEVAM-ARSIV.md**'ye tasindi —
  sinif kapisi 3 satirin PUBLIC deftere girmesini DURDURDU (silme YOK, tasima VAR).
  Ozet: hedef DISI bir havayolu sadakat bildirimi Cop'e dustu; §0.4 fail-closed alarmi
  (`KOMSU_KAYIP=1`). ASIL ARIZA: hedef yukleminin URETMEDIGI bir kayit tasindi (indeks kaymasi
  ya da §0.5 indeks-yasaginin devre disi kalmasi). Katalog/kaynak/secret/CNAME sinifina
  DOKUNULMADI. Kurtarma ELLE + OKAN karari, ayrinti arsivde.

§0.4 PROTOKOLÜ UYGULANDI: bu tur **KIRMIZI** (rc≠0). Çıktı olduğu gibi deftere yazıldı. **Teşhis/onarıma GEÇİLMEDİ.** Süpürme tekrar koşulmadı (§0.4 alarm koşulu). Çöp denetimi + CI bağımsız teyit + Codex açılışı YAPILMADI — ALARM koşulunda ölçüm artışı zararı büyütebilir, karar Okan'ın.

**YAPILACAK KURTARMA (ELLE, Okan kararı):** `/Users/okan/.claude/cron/kurtarma-cop-inbox.applescript` (otomatik DEĞİL, §0.4). FAZ 4 doğrulaması: kurtarılan kaydın Gelen Kutusu'na döndüğünün ölçülmesi. Öncesinde Okan'ın kararı bekleniyor (TurkishAirlines mailinin silinmesi PARA KAYBI sınıfı olabilir — uçuş bileti/sipariş kaybı riski).

TAMIRCI BAKIM: bu turda dağıtım yok, kapanan yok. §4.7.1 kapsamında `nobet-kapi.py --tur` bir sonraki turda K98'i dağıtabilir (bu turda ALARM nedeniyle ikinci kez işçi AÇILMADI).

OKAN'A ÇIKIŞ: **VAR — TEK CÜMLE** (§0.4 son cümle: "yanlış silme para kaybı sınıfıdır; §5'in sessiz varsayılan kuralı bu alarmı KAPSAMAZ").
