# PAKET K175 — T1 penceresi ÖLÇMÜYOR: gözcü `gh` kolunu cron ortamında bulamıyor (hipotez), OLCULEMEDI ise SEBEPSİZ (olgu)

Mimar: KraL · 18 Ağu 2026 · hedef kat: İŞÇİ (kod `~/.claude/cron/gozcu.py`'de; mimar eli
sürmez). BaBa'nın T1 hükmünün (48 SAAT paralel pencere) icra arızasıdır.

🔴 **ZAMAN KRİTİK.** Pencere `t1-pencere.json`: `2026-08-18T08:48:05Z` → `2026-08-20T08:48:05Z`.
Gözcü saatte bir (`:23`) ateşleniyor. Her ölçülemeyen saat pencereden GERİ GELMEZ.

---

## 1. ÖLÇÜLEN OLGU (18 Ağu, iki cron turu)

`~/.claude/cron/gozcu-cron.log` (birebir):

```
GOZCU 2026-08-18T09:23:00Z TETIK=OLCULEMEDI LLM_TURU=0 YENI_KIRMIZI=0 DAGITILABILIR=1 KAT_MIMAR=10 KAT_OKAN=1 GUNLUK=1 ARTIK_SILINEN=0 rc=2
GOZCU 2026-08-18T10:23:01Z TETIK=OLCULEMEDI LLM_TURU=0 YENI_KIRMIZI=0 DAGITILABILIR=1 KAT_MIMAR=10 KAT_OKAN=1 GUNLUK=1 ARTIK_SILINEN=0 rc=2
```

`gozcu-kalp.json`: `"ci_olculdu": false` · `"defter_olculdu": true` · `"tetik": "OLCULEMEDI"`
· `"rc": 2` · `"icra_rc": null`.
`gozcu-durum.json`: `{"kosumlar": {}, "son_gunluk_tur": "", "taban_alindi": false}` — **taban
hiç alınamadı.**

Yani: defter kolu ölçüyor, **CI kolu ölçmüyor**; fail-closed doğru çalışıp rc=2 veriyor
(bu bir ARIZA DEĞİL, doğru davranış), ama tur boş geçiyor ve pencere yanıyor.

## 2. HİPOTEZ + KARŞI-KONTROL (ölçülecek, ölçülmeden uygulanmayacak)

`gozcu.py:313-328`:

```
315:    komut = ["gh", "run", "list", "--branch", dal, "--limit", str(limit),
318:        sonuc = subprocess.run(komut, cwd=NK.EV_KOKU, ...)
320:    except (OSError, subprocess.SubprocessError):
321:        return None
322:    if sonuc.returncode != 0:
323:        return None
326:    except ValueError:
327:        return None
```

İkili **çıplak** (`"gh"`) çağrılıyor → PATH'ten çözülüyor. Cron'un varsayılan PATH'i
`/usr/bin:/bin`; `gh` orada DEĞİL.

🔎 **KARŞI-KONTROL — kardeş hat ÇALIŞIYOR ve nedenini gösteriyor.** Aynı crontab'ta `:07`
satırı `ci-nobeti.sh`'i çağırıyor ve o sarmalayıcı işe **PATH'i kendisi kurarak** başlıyor:

```
export PATH="/Users/okan/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
```

T1 satırı ise sarmalayıcısız, doğrudan `/opt/homebrew/bin/python3 gozcu.py --tur` çağırıyor —
**python'un tam yolu verilmiş, `gh`'ınki verilmemiş.** Sınıf hafızada zaten var:
[[codex-tam-yol]] (ikili KURULU ama PATH'te YOK → çıplak çağrı "kurulu değil" yanılgısı verir).

🔴 **İKİNCİ VE AYRI OLGU — bu hipotezden BAĞIMSIZ olarak kusur:** `_gh_kosumlar` ÜÇ ayrı
dünyayı (`ikili yok` · `gh rc!=0` · `bozuk JSON`) tek bir `None`'a eşliyor. Bu yüzden iki
turdur `OLCULEMEDI` yazıyor ve **NEDEN olduğu hiçbir yere yazılmıyor** — teşhis yolu kesik.
Bu, bu depoda kapalı bir eksenin yeniden açılmasıdır ([[kapi-varlik-olcer-yokluk-olcmez]] ·
[[fail-slow-fail-opendir]]): `OLCULEMEDI` doğru jetondur ama **sebepsiz OLCULEMEDI ölçüm
değildir.** Hipotez 3'te çürüse bile bu kol onarılır.

## 3. ADIM 1 — ÖLÇÜM (önce bu; onarım ÖLÇÜMDEN SONRA)

İşçi `~/.claude/cron/k175-prob.py` yazar (tek dosya, salt okuma, hiçbir şeyi değiştirmez) ve
`_gh_kosumlar`'ın **birebir aynı komutunu** iki ortamda koşar:

* **CRON ORTAMI:** çocuk sürece `PATH=/usr/bin:/bin` verilir (cron'un varsayılanı),
  `GH_TOKEN` korunur.
* **TAM ORTAM:** işçinin kendi PATH'i.

Her iki kolda `shutil.which("gh")` sonucu + çağrının düşme biçimi ayrı ayrı kaydedilir.
Tek makine-okunur satır basar:

```
SEBEP_CRON=<IKILI_YOK|RC:<n>|JSON_BOZUK|TAMAM> WHICH_CRON=<yol|YOK> KOSUM_CRON=<n|->
SEBEP_TAM=<...> WHICH_TAM=<yol|YOK> KOSUM_TAM=<n|->
```

🔴 **GİZLİLİK:** `GH_TOKEN` değeri hiçbir çıktıya, log'a, rapora GİRMEZ; `gh` stderr'i
yazdırılacaksa yalnız İLK SATIR ve 120 karakter kırpık yazılır. Kapanışta
`python3 /Users/okan/dev/pruvo/tools/kisisel-veri-test.py` → 0 bulgu.

📌 **MİMARIN YAZILI ÖNGÖRÜSÜ (çürütülebilir olsun diye önden yazıldı):**
`SEBEP_CRON=IKILI_YOK` · `WHICH_CRON=YOK` · `SEBEP_TAM=TAMAM` · `WHICH_TAM=/opt/homebrew/bin/gh`
· `KOSUM_TAM>0`.
**Öngörü tutmazsa ADIM 2'yi UYGULAMA** — ölçülen gerçek sebebi rapora yaz, dur, mimara dön.
Bu depoda tahmin üzerine onarım yasak ([[tahmin-degil-olcum-okan-uyarisi]]).

## 4. ADIM 2 — HÜKÜM (öngörü doğrulanırsa uygulanır)

Onarımdan ÖNCE yedek: `gozcu.py` → `gozcu.py.yedek-K175` (K146: bu dizin versiyon kontrolü
DIŞINDA, yedeksiz düzenleme yasak).

**H1 — ikili çözümü sağlamlaşır.** `_gh_ikili()` yardımcısı: önce `shutil.which("gh")`;
bulamazsa bilinen mutlak adayları sırayla dener (`/opt/homebrew/bin/gh` ·
`/usr/local/bin/gh` · `/Users/okan/.local/bin/gh`) ve **var olan + çalıştırılabilir** olanı
seçer. Hiçbiri yoksa `IKILI_YOK` sebebiyle döner. `komut[0]` artık çıplak `"gh"` DEĞİL,
çözülmüş tam yoldur.

**H2 — hattın kendi PATH'i garanti altına alınır (TEK yerde, girişte).** `--tur` girişinde
`os.environ["PATH"]` yalnızca **genişletilir**: yukarıdaki bilinen dizinlerden diskte VAR
OLAN ve PATH'te henüz OLMAYANLAR başa eklenir. Hiçbir dizin ÇIKARILMAZ.
Gerekçe (kapsam genişletme değil, aynı arızanın bir alt katı): `gh` onarıldığında tetik
ateşlenecek ve gözcü `nobet-kapi.py` → `isci.sh` zincirini çağıracak; o zincir `git`/`gh`/
motor ikililerini yine PATH'ten arar. Tek satırlık onarım pencereyi ikinci kez yakardı.
`ci-nobeti.sh` aynı işi zaten kendi hattı için yapıyor — bu, o davranışın yeni hatta
karşılığıdır.

**H3 — `OLCULEMEDI` artık SEBEP taşır.** `_gh_kosumlar` `(veri, sebep)` döner;
`sebep ∈ {TAMAM, IKILI_YOK, RC:<n>, JSON_BOZUK, ZAMAN_ASIMI}`. Sebep:
`gozcu-kalp.json`'a `"ci_sebep"` alanı olarak **ve** log satırına `CI_SEBEP=<jeton>` olarak
yazılır. **Fail-closed AYNEN KALIR:** `sebep != TAMAM` → `ci_olculdu=False` → `TETIK=OLCULEMEDI`
→ `rc=2`. Bu kol davranışı gevşetmez, yalnız sebebi görünür kılar.

⛔ **KAPSAM DIŞI — crontab'a DOKUNULMAZ.** Ne satır eklenir ne PATH yazılır.
Gerekçe: (a) `crontab <dosya>` tam değiştirmedir, canlı durumu ezme riski taşır
([[canli-durum-defter-kopyasi-bayat]]); (b) onarım koda konursa hattı kim çağırırsa çağırsın
çalışır, crontab'a konursa ikinci bir yüzey doğar ([[ikiz-tanim-sessiz-ayrisma]]).

## 5. KABUL (çalıştırılabilir; "bakıldı iyi" DEĞİL)

🔴 **ÖNCE OKU — bu testin kolay yoldan sahte yeşil verme biçimi:** işçi `gozcu.py --tur`'u
KENDİ kabuğundan koşarsa PATH tam olduğu için onarımsız da GEÇER. Hüküm koşum konumuna
bağlıdır ([[parite-testi-olculemedi-basiyor]]). Bu yüzden **her vaka, çocuk süreci
`PATH=/usr/bin:/bin` ile kurulmuş bir alt süreçte** koşar; elle koşum kabul DEĞİLDİR.

`~/.claude/cron/gozcu-test.py`'ye vaka eklenir, tek komut kapatır:

```
python3 /Users/okan/.claude/cron/gozcu-test.py
```

son satırı ve rc=0:

```
VAKA=<n> DUSEN=0 MUTANT=4/4 KONTROL=2/2
```

### 5.1 Vakalar

| # | Fikstür | Beklenen |
|---|---|---|
| V1 | `PATH=/usr/bin:/bin` ortamında tur | `ci_olculdu=True`, `ci_sebep=TAMAM` (bugün: `False`) |
| V2 | `gh` hiçbir aday yolda YOK | `ci_sebep=IKILI_YOK` · `TETIK=OLCULEMEDI` · `rc=2` |
| V3 | `gh` var ama rc=1 döner | `ci_sebep=RC:1` · `rc=2` |
| V4 | `gh` rc=0 ama bozuk JSON basar | `ci_sebep=JSON_BOZUK` · `rc=2` |
| V5 | `PATH=/usr/bin:/bin` girişte genişletilir | genişletilmiş PATH `/opt/homebrew/bin` İÇERİR, önceki girdiler DURUR |

### 5.2 Mutasyon bataryası (4/4 KIRMIZI olacak)

* **M1** — `komut[0]`'ı çıplak `"gh"`e geri döndür → **V1 DÜŞER**.
* **M2** — `sebep`i at, yine çıplak `None` dön → **V2/V3/V4 DÜŞER** (sebep ayrımı ölür).
* **M3** — `sebep != TAMAM` iken `rc=0` döndür → batarya KIRMIZI (fail-open geri gelmiş olur).
* **M4** — H2'deki PATH genişletmesini kaldır → **V5 DÜŞER**.

⚠️ Her mutant, nişanlandığı vakayı **TEK BAŞINA** düşürmeli. Mutant birden çok ekseni
yakıyorsa hedef kol ölü olsa da kırmızı gelirdi ([[mutant-yan-ekseni-de-tetikliyorsa-olcmez]]);
o mutant kanıt saymaz, daraltılır.

### 5.3 Kontrol mutantları (2/2 YEŞİL kalacak)

* **K1** — Gerçekten ölçülen bir tur (`ci_sebep=TAMAM`) `OLCULEMEDI` diye İŞARETLENMEZ.
* **K2** — `defter_olculdu=False` kolu bugünkü davranışını AYNEN korur (kapsam genişletme yok).

### 5.4 CANLI KABUL — elle koşum SAYILMAZ

Onarımdan sonra **cron'un kendi ateşlediği** ilk `:23` turu beklenir ve
`~/.claude/cron/gozcu-cron.log`'un son satırı rapora **BİREBİR** yapıştırılır. Beklenen:

```
GOZCU <damga> TETIK=<jeton> ... CI_SEBEP=TAMAM ... rc=<n>
```

`ci_olculdu=true` **ve** `gozcu-durum.json`'da `taban_alindi` artık `false` DEĞİL.
Uçuştaki/elle koşum yeşil değildir ([[ucustaki-kosum-yesil-degildir]]).

## 6. PENCERE MUHASEBESİ (bağlayıcı — kıyas tablosunu bu kural yazar)

T1 kıyas tablosu hazırlanırken `ci_olculdu=false` olan turlar **"kırmızı bulunmadı" sayılmaz**;
ayrı satırda `OLCULEMEDI_TUR=<n>` olarak raporlanır ve pencerenin **fiilen ölçülen** başlangıcı
(ilk `CI_SEBEP=TAMAM` turunun damgası) tabloya yazılır. Ölçülemeyen saat yeşil saat değildir.
Bugüne dek kayıp: **2 tur** (09:23Z · 10:23Z).

## 7. SINIRLAR

* Bu paket gözcünün KARAR mantığına (`tetik_karari`, eşikler, dağıtım) DOKUNMAZ; yalnız
  CI ÖLÇÜM kolunu ve sebep kaydını onarır.
* `ci-nobeti` hattı (`:07`) AÇIK KALIR — T1 zaten paralel penceredir; kapatma yetkisi bende değil.
* `crontab` ve `t1-pencere.json` DEĞİŞTİRİLMEZ.
* Bu dizin versiyon kontrolü dışında (K146): yedek `.yedek-K175` zorunlu, geçici prob dosyası
  (`k175-prob.py`) iş bitince SİLİNİR ve silindiği `ls` ile kanıtlanır (13 Ağu disk emri).
* 🔵 KAYIT (bu pakette YAPILMAZ, kalem olarak açılır): bilinen bin dizini listesi artık iki
  yerde — `ci-nobeti.sh` ve `gozcu.py`. İkiz tanım sessizce ayrışır; tek kaynağa çekilmesi
  ayrı bir turun işidir.

## 8. İŞÇİ TALİMATI (tur disiplini — bağlayıcı)

* **Sıra:** ADIM 1 (ölçüm) → öngörü tuttu mu KARAR → ADIM 2 (onarım) → KABUL → CANLI KABUL.
  Öngörü tutmazsa ADIM 2'ye GEÇME, raporu yaz ve DUR.
* **Tavan:** ~30-40 tur, tek dilim. **Alt ajan / paralel görev AÇMA.** Tarayıcı GEREKMEZ.
* **Raporu ÖNCE oluştur, ilerledikçe doldur:** nöbet dizinindeki (`~/.claude/cron/`) kanonik
  mühendis raporu dosyası. 🔴 O dosyada BAŞKA turun raporu VAR — **ÜZERİNE YAZMA**; yeni
  bölümü dosyanın **BAŞINA** tarih damgasıyla EKLE ([[sessiz-uzerine-yazma-yasak]]).
* **Ham kanıt zorunlu:** her "geçti/düştü" hükmünün yanında onu üreten komut ve çıktısının
  ilgili satırı raporun İÇİNDE olacak. Özet tek başına kabul değildir; bu evde işçi özeti
  ham dosyayla desteklenmeden hiçbir tabloya girmez.
* **DOKUNMA:** `~/dev/pruvo/.github/workflows/nobet.yml` (paralel oturum çalışıyor) ·
  `crontab` · `t1-pencere.json` · `urunler.json` · `ci-nobeti.sh`.
* **Temizlik (13 Ağu emri):** `k175-prob.py` ve tüm geçici dosyalar iş bitince SİLİNİR;
  silindiği `ls` çıktısıyla raporda kanıtlanır. Yedek (`gozcu.py.yedek-K175`) KALIR.
