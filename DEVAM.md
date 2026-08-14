# DEVAM (KraL) — 8 Agu 2026

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

