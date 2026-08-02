# SPEC — CI kapsam kapisi: ALT KUME ekseni (opt-in beyan) + uyari katmani + coklu-workflow onarimi

MIMAR: KraL · MUHENDIS: Opus (sessiz-hata sinifi: olcum + kapi + CI yayin yolu)
HEDEF DOSYALAR: `tools/ci-kapsam-test.py` (KATMAN 1), `tools/yaml-oku.py` (KATMAN 0),
`shop/test/kabul.js` (yalniz beyan satiri). deploy.yml'e YENI ADIM GEREKMEZ (gerekce D bolumunde).

---

## 0. NEDEN (olculmus baglam — bunu tekrar olcme, uzerine kur)

Kapi bugun DOSYA duzeyinde kapsam olcuyor: bir kabul-testi dosyasi deploy.yml'de kosuluyorsa
"kapsanmis" sayilir. Olculmus delik: `shop/test/kabul.js` CI'da YALNIZ `--sema-paritesi` ile
kosuyordu; `--yonet-cerez` (63 iddialik admin giris guvenlik alt kumesi) HIC kosmuyordu ve kapi
YESIL kaliyordu. O tekil delik kapatildi (deploy.yml + node 20->22).

**BAYRAK duzeyine GENEL GECIS YAPMA — olculdu ve CURUDU.** 159 dosya kesfediliyor, 123'u
kosuluyor, 116 (dosya,bayrak) cifti hic kosmuyor: 89'u MODIFIKATOR (`--kok`/`--dosya`/`--yaz`/
`--json`/esik — ayri iddia kumesi DEGIL), 21'i ayri main kolu, 6'si baska workflow'da (cron)
kosuyor. 21'in triyaji: 11 `--mutasyon` meta oz-dogrulama (yardim metni "elle" diyor),
`--sandbox` gercek iyzico sirri istiyor, 6 `eslem-olcum.py` bayragi gitignore'lu R2 veri paketi
istiyor, `--canli` canli D1'e vuruyor, 2 `yayin-kapisi.py` bayragi operasyonel alt komut.
GERCEKTEN CI'ya baglanabilir sessiz alt kume sayisi **1** idi ve o kapatildi.

Duz bayrak kapsami sinyal/gurultu **1:115** olur ve her yeni `--kok` tarzi bayrak tum ekibin
yayinini kirmiziya cevirir → [[kapi-kapsam-eksen-secimi]] · [[kapi-kapsam-genisletme-tuzagi]].

Bu yuzden eksen **OPT-IN BEYAN**: yazarin ACIK niyeti. Beyan EDILMEYEN bayrak hicbir sey
talep etmez → yanlis-kirmizi yuzeyi ~sifir.

---

## A. BOLUM A — COKLU WORKFLOW ONARIMI (bagimsiz dogruluk kusuru, ONCE BUNU YAP)

### A1. Kusur
`DEPLOY_VARSAYILAN` tek dosya: kapi SADECE `.github/workflows/deploy.yml` okuyor. Repoda 4
workflow var:

| dosya | tetik | sinif |
|---|---|---|
| `deploy.yml` | `push` | OTOMATIK |
| `d1-uzlastirici.yml` | `schedule: "7,22,37,52 * * * *"` + `workflow_dispatch` | OTOMATIK |
| `paket-tazelik-alarmi.yml` | `schedule: "11,26,41,56 * * * *"` + `workflow_dispatch` | OTOMATIK |
| `onizleme-imaj.yml` | yalniz `workflow_dispatch` | **ELLE** |

Sonuc: cron'da GERCEKTEN kosan 6 bayrak "hic kosmuyor" gorunuyor.

### A2. Kural
* Kapi TUM izlenen workflow'lari okur (`git ls-files` → `.github/workflows/*.yml|*.yaml`;
  `os.walk` DEGIL — `kesfet()` ile ayni disiplin, gitignore'lu/uretilmis dosya sapma yaratmasin).
* Her workflow'un tetik sinifi **GERCEK YAML ayristiricisiyla** belirlenir.
* **ELLE tetiklenen (yalniz `workflow_dispatch`/`repository_dispatch`) bir workflow'da kosmak
  "CI'da kosuyor" SAYILMAZ.** OTOMATIK (push/pull_request/schedule/release/...) sayilir.
* Rapor bunlari AYRI basar: hangi dosya hangi workflow'da, ve o workflow'un sinifi ne.

### A3. `tools/yaml-oku.py`'ye eklenecek (KATMAN 0, TEK KAYNAK — ikinci kopya CIKARMA)

```
def tetikleyiciler(metin) -> (set[str] | None, hata: str | None)
```
* PyYAML → ruby/psych kol sirasi AYNEN korunur; `run_dugumleri()` ile ayni onbellek/kol
  disiplini. Ayri bir ayristirici ic kopyasi ACMA.
* 🔴 **YAML 1.1 TUZAGI (bunu atlarsan sessizce yanlis siniflarsin):** ciplak `on:` anahtari
  hem PyYAML hem Psych tarafindan **boolean `True`** olarak cozulur. Anahtar esleme
  `"on"` VEYA `True` olabilir; ikisini de kabul et. Tirnakli `"on":` de olabilir.
* Uc yazim da desteklenmeli: `on: push` (skalar) · `on: [push, workflow_dispatch]` (dizi) ·
  `on:\n  push:\n    branches: ...` (esleme).
* `_YAML_OKU_SOZLESME` tuple'ina `"tetikleyiciler"` EKLE (fail-closed sozlesme kontrolu).

### A4. `ci-kapsam-test.py` tarafi

```
IS_AKISI_DIZINI = os.path.join(ROOT, ".github", "workflows")
ELLE_TETIKLER = frozenset(("workflow_dispatch", "repository_dispatch"))

def is_akislari() -> [(repo_rel_yol, metin, sinif)]   # sinif: "OTOMATIK" | "ELLE" | "BELIRSIZ"
```
* `sinif` = "OTOMATIK" ⟺ tetik kumesi `ELLE_TETIKLER` DISINDA en az bir eleman iceriyor.
* Tetik cozulemezse (ayristirma hatasi / `on:` yok) → **"BELIRSIZ"**, ve **kapsam acisindan
  ELLE gibi davranilir** (yani o workflow'da kosmak kapsam SAYILMAZ). Gerekce: ters yon
  (BELIRSIZ→OTOMATIK) kapiyi SESSIZCE GEVSETIR (sahte-YESIL). BELIRSIZ workflow raporda
  **UYARI satiri** olarak basilir, **exit kodunu ETKILEMEZ** (tek sahte-kirmizi tum ekibin
  yayinini durdurur).

### A5. Kapsam semantigi — mevcut nobetcileri KIRMA
`kosulan(deploy_metin, kesif)` imzasi ve semantigi **AYNEN KALIR** (bulgu1/muaf/bayraksiz/
kendini-test nobetcileri onu tek metinle cagiriyor). Uzerine EKLE:

```
def kosulan_coklu(akislar, kesif) -> (kos_otomatik: dict[yol -> set[workflow]],
                                      kos_elle:     dict[yol -> set[workflow]])
```
`denetle()` yeni bir **opsiyonel** parametre alir (or. `akislar=None`); `None` iken BUGUNKU
davranis (yalniz verilen deploy metni) korunur → ozyinelemeli nobetciler degismeden gecer.
`main()` gercek envanteri gecirir.

🔴 **OLC, VARSAYMA:** A bolumu bittiginde `IZIN_LISTESI`'nde artik "kosuluyor" hale gelen
giris var mi ONCE/SONRA sayisiyla olc. Varsa → "BAYAT izin (ARTIK KOSULUYOR)" kirmizisi
dogrudur, o girisi listeden CIKAR ve raporda sayiyla bildir.
`onizleme/*` dortlusu (`kabul.js`, `kapi1.js`, `duman_kabul.py`, `tools/onizleme-kapisi.py`)
yalniz `onizleme-imaj.yml`'de (ELLE) kosuyor → **muaf KALMALI**; A4 kurali bunu saglar.
Bu, A bolumunun canlilik kontrolu: bu dortlu kirmiziya donuyorsa ELLE/OTOMATIK ayrimini
yanlis kurmussun.

---

## B. BOLUM B — OPT-IN BEYAN (BLOKLAYICI CEKIRDEK)

### B1. Beyan bicimi
Test dosyasi CI'ya baglanabilir **deterministik** alt kumesini KENDI ICINDE beyan eder:

* `.py` → `# CI-ALT-KUME: --bayrak`
* `.js` / `.mjs` / `.cjs` → `// CI-ALT-KUME: --bayrak`

Ayristirma: satir basi (bosluk serbest), yorum isareti, `CI-ALT-KUME:`, sonra **`--` ile
baslayan tek jeton**. Satirin kalani serbest aciklama olabilir. Bir dosyada birden cok beyan
satiri olabilir.

🔴 **KENDI DOSYASINDA SIZINTI TUZAGI** ([[nobetci-kendi-dosyasinda-sizinti]]): bu bicimi
ANLATAN her docstring/yorum satiri gercek bir beyan gibi ayristirilir — `ci-kapsam-test.py`
kesif predikatina ZATEN giriyor (`-test.py`). ZORUNLU: prose'da **daima `<bayrak>` yer
tutucusu** kullan (`# CI-ALT-KUME: <bayrak>`), asla gercek `--` ornegi yazma. Buna bir
FIKSTUR koy: doc bicimi (`<bayrak>`) beyan olarak AYRISTIRILMAMALI.

### B2. Bloklayici kural
Kesfedilen her dosyanin BEYAN EDILEN her alt kumesi icin:
1. **OTOMATIK** bir workflow'da o dosyayi FIILEN kosan bir komut var VE o komutun etkili
   argumanlari arasinda bayrak geciyor → **KAPSANMIS**.
2. Degilse `ALT_KUME_IZIN_LISTESI[(yol, bayrak)]` dolu GEREKCE ile var → **MUAF**.
3. Ucuncu hal YOK → `BEYAN EDILEN ALT KUME KOSMUYOR: <yol> <bayrak>` → **exit 1**.

Bayrak tespiti: `SUZGEC.anlamli_cagri(komut, yol)` `EVET` dondugunde 3. donen deger
`argumanlar` listesidir — bayragi ORADA ara. Ham metinde `in` ARAMA (echo/yorum/`--help`
sinifi sessiz kacislar orada yasar; suzgec zaten sertlestirilmis TEK KAYNAK).
`OLCULEMEDI` hukmu → **kapsanmis say** (fail-OPEN, bilincli: bu kapi `continue-on-error`SUZ
kosar, `kosulan()`'in bugunku belirsizlik politikasiyla AYNI yon).

### B3. `ALT_KUME_IZIN_LISTESI` curume kurallari (dosya duzeyindeki 2/3/4'un aynasi)
* Bos/boslukli gerekce → exit 1.
* Anahtardaki `yol` artik KESFEDILMIYOR → exit 1 (BAYAT).
* `bayrak` jetonu artik o dosyanin METNINDE hic gecmiyor → exit 1 (BAYAT; ucuz ve saglam
  capa — bayrak yeniden adlandirilirsa giris curur).
* Giris VAR ama alt kume OTOMATIK bir workflow'da FIILEN kosuyor → exit 1 (BAYAT, listeden cikar).

### B4. BILINEN SINIR — kod icinde ACIKCA yaz
Modul docstring'ine ve `ALT_KUME_IZIN_LISTESI`'nin basina, kacamaksiz:

> BEYAN EDILMEYEN yeni bir alt kume bu kapiya GORUNMEZ. Bu bir **disiplin cihazidir, kafes
> degil** ([[kapi-disiplin-ilkesi]]). Duz bayrak kapsami olculdu ve curudu (sinyal/gurultu
> 1:115, bkz. bolum 0). Yeni A-sinifi adaylar BOLUM C uyari katmaniyla her kosumda yuzeye
> cikar; bloklama bedeli sifirdir.

---

## C. BOLUM C — UYARI KATMANI (EXIT KODUNA ASLA DOKUNMAZ)

Kesfedilen her dosyada su bayraklari CI logunda GORUNUR bas:
(a) ayri bir `main` kolu tetikleyen, (b) hicbir workflow'da kosmayan, (c) beyan edilmemis ve
muaf olmayan.

* **Tumu `try/except Exception` ile sarili**; istisna → tek satir "UYARI KATMANI OLCULEMEDI:
  <sinif>: <mesaj>", exit kodu DEGISMEZ. Bu, [[duzeltme-fail-open-cevirebilir]] dersinin
  tersi degil: bu katman ZATEN bloklamiyor, tek riski bloklayan koda istisna sizdirmasi.
* "Ayri main kolu" tespiti **HEURISTIK** ve raporda ACIKCA oyle etiketlenir:
  * `.py`: `ast` ile `add_argument("--x", action="store_true")` bayraklari + o bayragin
    `dest`'i bir `if` testinde geciyor VE o `if` govdesinde `return` / `sys.exit(...)` var.
  * `.js`/`.mjs`/`.cjs`: **olculmuyor** → "N dosya olculemedi (js)" diye SAYIYLA bas.
* 🔴 **SESSIZ KIRPMA YOK** ([[hukum-yanlis-birimde]]): liste kirpilirsa (or. ilk 20) kac
  kalem dusuruldugu YAZILIR. "basarili / olculemedi" ayri sayilir, tek toplamda gizlenmez.
* Manuel-only workflow'da kosan bayraklar AYRI bir satirda ("ELLE tetiklenen workflow'da
  kosuyor — CI kapsami SAYILMAZ") listelenir.

---

## D. BOLUM D — BACKFILL

1. `shop/test/kabul.js`: `// CI-ALT-KUME: --yonet-cerez` ve `// CI-ALT-KUME: --sema-paritesi`
   (dosya basina, kisa gerekce cumlesiyle). Ikisi de deploy.yml'de zaten bloklayici kosuyor →
   kural 1 ile KAPSANMIS olmali. Bu, B bolumunun POZITIF canlilik kontrolu.
2. `ALT_KUME_IZIN_LISTESI`'ne 20 A-sinifi bayrak **OLCULMUS** gerekceyle. Triyaji ONCE
   DOGRULA (yol+bayrak ciftlerini fiilen olc, benim listemi kopyalama), sonra sinifla:
   * `--mutasyon` meta oz-dogrulama (11 adet) — yardim metni "elle" diyor.
   * `--sandbox` — gercek iyzico sirri gerekiyor.
   * `eslem-olcum.py` 6 bayragi — gitignore'lu R2 veri paketi; taze checkout'ta YAPISAL
     olarak kosamaz.
   * `--canli` — canli D1 non-determinizmi.
   * `yayin-kapisi.py` 2 bayragi — operasyonel alt komut, kabul testi degil.
   Gerekce METNI somut ve olculebilir olsun (mevcut `R_*` sabitleri uslubu; sayi/rc/sure yaz).
   Sayi 20'den saparsa **sapmayi raporla** — benim sayimi degil, OLCUMU esas al.
3. deploy.yml'e yeni adim EKLENMEZ: kapi zaten iki kolla (bayraksiz + `--kendini-test`)
   `continue-on-error`SUZ kosuyor; yeni kurallar o kollara biner. Bunu FIILEN dogrula
   (`kendini_test_adimi_kontrol` / `bayraksiz_adim_kontrol` yesil kalmali).

---

## E. KABUL — CALISTIRILABILIR, "BAKILDI IYI" DEGIL

### E1. Yesil sart
* `python3 tools/ci-kapsam-test.py` → exit 0
* `python3 tools/ci-kapsam-test.py --kendini-test` → exit 0
* Mevcut 6 oz-nobetci (bulgu1 · muaf sayaci · kendini-test adimi · bayraksiz adim · suzgec
  fikstur · suzgec kablo) YESIL kalir. Bunlarin ciktisini ONCE/SONRA kaydet.

### E2. MUTASYON KANITI — her yeni kural icin ONCE KIRMIZI SONRA YESIL
Sentetik fikstur olarak (`KATLAMA_FIKSTURLERI` uslubu; GERCEK deploy.yml'e DOKUNMA):

| # | mutant | beklenen |
|---|---|---|
| a | beyan edilmis bir alt kumenin deploy.yml'deki cagrisi SILINIR | **KIRMIZI** |
| b | beyan satiri VAR, bayrak hicbir yerde kosmuyor | **KIRMIZI** |
| c | beyan EDILMEYEN yeni bir modifikator bayrak eklenir | **YESIL** (yanlis-kirmizi yok) |
| d | uyari katmani bulgu basar | **exit 0 KALIR** |
| e | alt kume yalniz ELLE tetiklenen workflow'da kosuyor | **KIRMIZI** |
| f | alt kume cron (OTOMATIK) workflow'da kosuyor | **YESIL** |
| g | beyan doc bicimi (`# CI-ALT-KUME: <bayrak>`) | beyan SAYILMAZ (YESIL) |
| h | `ALT_KUME_IZIN_LISTESI` girisi bos gerekce | **KIRMIZI** |
| i | izin girisinin bayragi dosya metninden kaldirilir | **KIRMIZI** (BAYAT) |
| j | izin girisindeki alt kume aslinda kosuyor | **KIRMIZI** (BAYAT) |
| k | **konuyla ilgisiz rutin duzenleme** (or. deploy.yml'e alakasiz `- name:` adimi, test dosyasina alakasiz yorum) | **YESIL** |

🔴 **(c) ve (k) VAKALARINI SILME.** Bu kapi `continue-on-error`SUZ kosar: tek yanlis-kirmizi
tum ekibin yayinini durdurur. (k) sinifi fikstur kumesinde DAIMA bulunmali
([[fikstur-degeri-mutasyon-koru]]: kontrol mutanti olmadan olcum korelir).

### E3. Yapisal sartlar
* Mevcut 4 workflow'un hepsi **gercek YAML ayristiricisiyla** okunur — metin taklidi DEGIL.
  Dosya zaten `tools/yaml-oku.py` kullaniyor; **ONU KULLAN, ikinci kopya CIKARMA**
  ([[ayna-kapi-kesif-ekseni]] · [[ikiz-tanim-sessiz-ayrisma]]).
* Yeni fikstur kumeleri icin `*_FIKSTUR_ASGARI` sabiti + `_fikstur_sayisi_kontrol()` kablosu
  (fikstur sessizce silinmesin).
* Yeni nobetciler **AST kablo kontrolune** (`NOBETCI_KABLOLARI` / `suzgec_kablosu_kontrol`)
  eklenir → nobetci `denetle()`/`main()` govdesinden fiilen CAGRILIYOR olmali; cagri satiri
  silinince KIRMIZI ([[nobetci-cagri-satiri-nobetsiz]]).
* Yeni nobetciler `denetle(kontroller=True)` kolunda VE `--kendini-test` kolunda raporlanir
  (mevcut desen).
* `--kendini-test` toplam suresi CI'da makul kalsin; psych kolunda `YAML_OKU.onbellegi_isit()`
  ile TOPLU ayristir (her fikstur icin ayri ruby sureci acma). SURE olc ve raporla.

---

## F. RAPOR (dalda `RAPOR-MIMARA.md`, BASKA AD YASAK)

Sayiyla kapat, cumleyle degil:
1. ONCE/SONRA: kesfedilen dosya · OTOMATIK kosulan · ELLE-only kosulan · muaf (dosya) ·
   beyan edilen alt kume · muaf alt kume · uyari katmani bulgu sayisi.
2. E2 tablosunun 11 satiri icin FIILEN olculen exit kodu (beklenen/olculen).
3. A5 olcumu: coklu-workflow onarimi hangi `IZIN_LISTESI` girislerini degistirdi (0 ise "0" yaz).
4. D2 olcumu: izin listesine giren (yol,bayrak) cifti sayisi + 20'den sapma varsa gerekcesi.
5. `--kendini-test` suresi (once/sonra) ve YAML ayristirici kolu.
6. Bilerek YAPILMAYAN sey + gerekcesi (varsa).

## G. SINIRLAR — YAPMA
* Duz/genel bayrak kapsamina GECME (bolum 0).
* deploy.yml'e yeni bloklayici adim ekleme (D3).
* `tools/icra-suzgeci.py` ve `tools/yaml-oku.py` mantigini KOPYALAMA — ithal et.
* `git push`/merge YAPMA — dalda birak, mimar bagimsiz curutucu kosturup merge edecek.
* `urunler.json`, R2, D1, deploy sirlarina DOKUNMA.
