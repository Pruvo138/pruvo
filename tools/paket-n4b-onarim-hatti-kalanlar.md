# PAKET — N4B: onarım hattının KALAN iki yapısal arızası (`~/.claude/cron` düzlemi)

> N4A'nın ölçtüğü dört blokerden **ikisi** N4A içinde onarıldı (B1 etiket sözleşmesi,
> sayaç dürüstlüğü bataryası). Kalan ikisi `~/.claude/cron/*.py` içinde ve
> `tools/mimar-kod-kilidi.py` mimarın oraya yazmasını **konumdan bağımsız** yasaklıyor
> (çalıştırılabilir uzantı kuralı). Bu paket o ikisini kapatır.
>
> 🔴 Bu paket açılmadan **N4A ①/② kabul maddeleri kapanamaz**: B1 düzeltmesi main'e inse
> bile B4 duruyorsa `dagitilacak` yine boş kalır ve `ustuste_onarimsiz` yine düşmez.

## ÖNCÜL — N4A'da ölçüldü (20 Ağu 2026, `KraL-N4A`)

| olgu | ölçüm | kaynak |
|---|---|---|
| `ustuste_onarimsiz` | 104 → **105** (artıyor) | `~/.claude/cron/nobet-onarimsiz-sayac.json` |
| açık 🔧 kalem | **12** | `ACIK_KALEM=12`, `gozcu.log:1983` |
| → MIMAR katı | **10** (K49,K53,K70,K77,K80,K84,K86,K96,K105,K108) | `gozcu.log:1969-1978` |
| → OKAN katı | **1** (K98) | `gozcu.log:1979` |
| → işçi katı | **1** (K55) — ama `durum=ESKALASYON motor=deepseek-pro` | `nobet-geri-iz.json` |
| dağıtılan | **0** (105 turdur) | `DAGITILAN=0` |

## B4 — TEK işçi-katı kalem, EMEKLİ bir motora eskale edilmiş halde DONMUŞ

`nobet-geri-iz.json` içinde `K55 durum=ESKALASYON motor=deepseek-pro`.
`deepseek-pro` **15 Ağu 2026'da emekli** ([[deepseek-emekli-karari]]); K55 ona atanmış,
rapor üretmemiş, 3 denemede eskale olmuş ve `eskale_kalemler()`
(`nobet-kapi.py:307-314`) onu **bir daha ASLA** aday havuzuna sokmuyor:

> *"Eskale kalem tekrar aday havuzuna girseydi dagitim sayaci her turda sifirlanir ve
> eskalasyon bir daha ASLA ates almazdi: sessiz sonsuz dongu."*

O gerekçe DOĞRU — ama bir yan etkisi ölçülmedi: **eskalasyonu üreten motor artık yoksa,
kalem insan kapısında değil HİÇBİR kapıda beklemektedir.** Aynı sınıf `nobet-kapi.py:68-73`
yorumunda zaten bir kez ölçülmüştü ("bir kati emekli etmek o kata ATANMIS isleri TASIMIYOR").
Bu **ikinci** vaka → tekil yama YASAK, sınıf çözümü gerekli ([[ucuncu-tekrar-sinif-kapisi]]).

**İstenen (tekil "K55'i elle çöz" DEĞİL):** geri izdeki bir kaydın `motor` alanı
`mimar_kimlik.CANLI_ISCI_MOTORLARI` kümesinde DEĞİLSE, o eskalasyon **BAYAT** sayılır ve
kalem — sayacı sıfırlamadan, eskalasyon kanıtını silmeden — **canlı kata GÖÇ ETTİRİLİR**
(`canli_kata_goc` zaten var, `nobet-kapi.py:82`). Göç bir kez olur ve loga `ESKALASYON_BAYAT
kalem=<id> eski_motor=<x> yeni_kat=<y>` satırı düşer.

### Kabul (çalıştırılabilir, hepsi sayıyla)
1. **Pozitif:** sentetik geri izde `motor=deepseek-pro` + `durum=ESKALASYON` bir kalem →
   tur sonunda `DAGITILAN>=1` ve logda `ESKALASYON_BAYAT` satırı.
2. **Negatif:** `motor=minimax-m3` (CANLI) + `durum=ESKALASYON` bir kalem → **dağıtılmaz**
   (orijinal invaryant korunur; sonsuz döngü açılmaz).
3. **Mutant A (kapsam):** canlı motor kümesi boş dönerse **hiçbir şey göç etmez** ve hüküm
   `OLCULEMEDI` olur — "hepsi bayat" diye topluca göç ETTİRMEZ (fail-closed).
4. **Mutant B (sayaç dürüstlüğü):** göç yolu `ustuste_onarimsiz`'i doğrudan sıfırlarsa
   `tools/nobet-sayac-durustluk-test.py` **kırmızı** yanar. Sayaç yalnız `onarim>0` ile düşer.
5. Her mutantın **hedef kolu öldürdüğü** ayrıca kanıtlanır; yan eksen YEŞİL (K182).
6. `gozcu-eskalasyon.md` **SİLİNMEZ/TEMİZLENMEZ** — kanıttır.

## B5 — hüküm ekseni karışması: defter bacağının rc'si CI-run denemesine yazılıyor

`tur_kos()` (`nobet-kapi.py:1503-1506`) CI kırmızısı için açılan turun sonucunu
**defter bacağının** H1 hükmünden alıyor; `gozcu.py:500` bunu
`deneme_sonraki(kayit, icra_rc == 0)` ile **run-id'nin** deneme sayacına yazıyor.

Ölçülmüş kanıt (`gozcu.log:1365-1371`, 19 Ağu 22:53Z): motor koştu (`rc=0`), çıktı
`🟢 CI temiz` dedi, tur yine `HUKUM=ONARIMSIZ_TUR rc=1` ile kapandı → o run-id'nin denemesi
arttı. N4A'nın saydığı 10 eskalasyonun **4'ü** bu yoldan doğdu.

**İstenen:** iki özne ayrılır. CI-run denemesinin sonucu **yalnız** o run'a dair kollardan
türetilir (motor koştu mu · onarım commit'i düştü mü · sonraki koşum yeşil mi); defter
bacağının `ONARIMSIZ_TUR` hükmü **gözcünün kendi rc'sinde** kalır ama **run-id deneme
sayacına yazılmaz**.

### Kabul
1. **Pozitif:** motor rc=0 + CI temiz → run-id denemesi **artmaz** (sıfırlanır/kapanır).
2. **Negatif:** motor rc!=0 → run-id denemesi **artar** (eskalasyon yolu ÖLMEZ — bu şart,
   ayrımın "her şeyi yeşile boyayan" bir gevşetmeye dönüşmesini engeller).
3. **Mutant:** defter rc'si yeniden run-id sayacına bağlanırsa test **kırmızı** yanar.
4. Gözcünün kendi `rc`'si (`gozcu.py:512-513`) **değişmez** — turun kırmızılığı kaybolmaz;
   yalnız **kime yazıldığı** düzelir.

## B6 — 🔴 `icra_rc=0` ÜÇ HÂLİ İKİ DEĞERE SIKIŞTIRIYOR ("koştu" ile "hiç koşmadı" aynı)

**20 Ağu 2026, N4A merge'inden sonra CANLIDA ölçüldü.** `gozcu-kalp.json` 09:23:00Z:
`icra_rc: 0`, `rc: 0` — yani yeşil. Ama aynı turun log satırı (`gozcu.log:1999`):

```
=== 2026-08-20T09:23:02Z NOBET ATLANDI HUKUM=ONCEKI_TUR_SURUYOR ATLANAN_ARDISIK=1 ===
```

Tur **hiç koşmadı**: bir önceki tur (09:08:02Z, `nobet-tur.kilit` `PID=91760`) hâlâ uçuştaydı.

Kod yolu:

| dosya:satır | ne yapıyor |
|---|---|
| `nobet-kapi.py:1463-1467` | `alindi, hukum = kilit_al()` · kilit yoksa `atlanan_ardisik_guncelle(True)`, atlama satırı basılır ve **`return 0`** |
| `gozcu.py:496` | `icra_rc, icra_cikti = tur_kosucu(["--tur"])` → o `0` doğrudan `icra_rc` olur |
| `gozcu.py:512-513` | `icra_rc == 0` olduğu için gözcü `rc`'si de yükseltilmez |

**Neden tehlikeli:** `icra_rc` tek skaler ile **üç ayrı hâli** taşıyor —
`KOSTU_BASARILI` · `KOSTU_DUSTU` · `ATLANDI`. Üçüncüsü birinciyle aynı değere (`0`) eşleniyor.

🔴 **Bu, N4A'nın ④ kabul maddesini SAHTE olarak sağlanabilir yapıyordu:** *"icra_rc yeşile döndü
ve iki ARDIŞIK turda görüldü"* şartı, **arka arkaya atlanan iki turla** karşılanabilirdi — hem de
tam olarak onarım turu uzun sürdüğü için, yani sistem "çalışıyor" görünürken hiçbir tur
koşmamışken. Ölçüt, ölçtüğü şey doğru olmadan sağlanabiliyorsa kusurludur.

**Mimar ölçütü SIKILAŞTIRDI (20 Ağu, N4A kapanışına işlendi):**
> ④ = *"`icra_rc` yeşile döndü ve yeşilliği iki ARDIŞIK **gerçekten KOŞMUŞ** turda görüldü;
> `HUKUM=ONCEKI_TUR_SURUYOR` / `NOBET ATLANDI` turları **SAYILMAZ**."*

**İstenen (B6):** `icra_rc` üç hâli ayırsın. Öneri: kalbe ayrı bir `icra_hal` alanı
(`KOSTU_BASARILI` / `KOSTU_DUSTU` / `ATLANDI`) ve `icra_rc` yalnız gerçekten koşmuş turlarda
anlamlı sayılsın (atlananda `null`).

### Kabul (çalıştırılabilir, hepsi sayıyla)
1. **Pozitif:** kilit BOŞ + tur koşar + rc=0 → `icra_hal=KOSTU_BASARILI`, `icra_rc=0`.
2. **Negatif-1:** kilit BOŞ + tur koşar + rc!=0 → `icra_hal=KOSTU_DUSTU`, `icra_rc!=0`.
3. **Negatif-2 (asıl vaka):** kilit DOLU → `icra_hal=ATLANDI` ve `icra_rc` **`0` OLMAZ**
   (null ya da ayrı bir jeton). 🔴 Bugünkü davranış bu vakada `0` veriyor; test o hâli
   KIRMIZI yakmalı.
4. **Mutant:** `ATLANDI`'yı yeniden `0`'a eşleyen yol enjekte edilince test kırmızı yanar;
   **hedef kolun öldüğü ayrıca kanıtlanır** (pozitif vaka YEŞİL kalır, K182).
5. **Tüketici ekseni:** "iki ardışık yeşil tur" sayan HER yer (kabul metinleri, panolar)
   `ATLANDI` turlarını saymadığını göstermeli — kapının menzili çağrı yeridir
   ([[kapinin-menzili-cagri-yeridir]]).

### Sınıf notu — tekil yama YASAK
Bu, **K241'in ikinci yüzeyidir**: *tek skaler, üç anlam.*
- Yüzey 1 (K241): `ONARIM=0` — "dağıtılacak İŞ YOK" ile "DENEDİ ve başaramadı" aynı kovada.
- Yüzey 2 (B6): `icra_rc=0` — "koştu ve başardı" ile "hiç koşmadı" aynı değerde.
Aynı sınıfın ikinci ölçülmüş vakası olduğu için çözüm **sınıf düzeyinde** olmalı
([[ucuncu-tekrar-sinif-kapisi]]): bir hüküm skaleri, ayırt etmesi gereken hâl sayısından
az değer taşıyorsa nöbetçi UYARMALI.

---

## B7 — tur artık BAŞLIYOR ama 1500 sn tavanını doldurup ÖLDÜRÜLÜYOR

**20 Ağu 2026, N4A merge'inden sonra CANLIDA ölçüldü.** `gozcu.log:1993-1999`, 09:08 turu:

```
=== 2026-08-20T09:08:02Z BASLANGIC (nobet-kapi) ===
KOTAKARANTINA motorlar=kimi omur=6h
MOTOR_DENEME motor=minimax-m3 rc=1 sebep=HATA
N2B HUKUM=GECER KOL=N2B-MUAF EV=KraL ACIK=0 KALEM=-      <- B1 ONARILDI, kapi GECIRIYOR
SURE_TAVANI_ASILDI=1 TAVAN_SN=1500
HUKUM=SURE_TAVANI rc=1
```

B1 kapandıktan sonra arıza sınıfı **değişti**: *"kapı kendi onarım turunu reddediyor"* →
*"tur koşuyor ama süresi doluyor"*. m3 **1500 sn (25 dk) koştu ve onarım üretmedi**.
Kısa tavanın uygulanmış olması ayrıca şunu söylüyor: `_sureli_isci_bekle`
(`nobet-kapi.py:1218-1234`) `onarim_ilerliyor_mu(cikti)` çağrısından **pozitif sinyal
görmedi** — görseydi `TUR_ONARIM_ZAMAN_ASIMI_SN`'ye (3000 sn) uzardı.

🔴 **"HAT BOZUK" mu "KAT YOK" mu — OLCULEMEDI.** Bu ayrım bu paketin en kritik sorusudur ve
şu an cevaplanamıyor: `isci.log` o pencerede **iç içe geçmiş**. `ci-nobeti` turunun
`BASLANGIC` satırı `isci.log:4274`, ama ardından gelen satırlar eşzamanlı koşan
`kabul-k184-kuyruk` ve `citroen-d5-3-ekle` turlarına ait (`kral-k184` worktree yolları
görünüyor). Turun 25 dakika boyunca **ne yaptığı** log ekseninden okunamıyor.

**Neyi ölçmek kapatır:** `ci-nobeti` turunun çıktısını izole eden bir kayıt — tur başına ayrı
dosya, ya da her satıra etiket öneki. O olmadan "m3 beceremedi" (kat yok) ile "tur bir yerde
asıldı" (hat bozuk) ayrımı yapılamaz ve **tarife kararı yanlış veriye dayanır**.

### Kabul
1. Bir `ci-nobeti` turunun TÜM çıktısı, başka turların satırları KARIŞMADAN okunabiliyor
   (sentetik iki eşzamanlı turla ölçülür: her iki turun satır kümesi ayrıştırılabilmeli).
2. Tavan aşımında turun **son 50 satırı** hükme eklenir — "neden asıldı" sorusu logsuz kalmaz.
3. `onarim_ilerliyor_mu`'nun pozitif/negatif kolları ayrı ayrı ölçülür (bugün yalnız negatif
   kol gözlendi; pozitif kolun ÖLÜ olmadığı kanıtlanmalı).
4. **Mutant:** izolasyon kaldırılınca (satırlar yine karışınca) test KIRMIZI yanar.

---

## B8 — SAYAÇ EKSİK SAYIYOR: koşan ve düşen tur sayılmıyor (K241'in ÜÇÜNCÜ yüzeyi)

Aynı 09:08 turunda ölçüldü: tur **koştu**, **başarısız oldu** (`SURE_TAVANI rc=1`), ve
`ustuste_onarimsiz` **105 → 105**, yani **artmadı**.

Sebep: `tur_kos()` (`nobet-kapi.py:1495-1496`) `SURE_TAVANI_ASILDI=1` görünce **erken
dönüyor**; `tur_kapat()` hiç çağrılmıyor, dolayısıyla `ustuste_onarimsiz_guncelle()`
(`:1362`) de çalışmıyor.

Sonuç: "üst üste onarımsız tur" sayacı **gerçekten denenip başarısız olan turları saymıyor**.
Yalnız defter bacağına ulaşabilen turları sayıyor.

🔴 **K241'in ÜÇÜNCÜ yüzeyi.** Sayaç artık hem **fazla** hem **eksik** sayabiliyor:

| yüzey | kusur |
|---|---|
| K241 / yüzey 1 | `ONARIM=0`: "dağıtılacak İŞ YOK" ile "DENEDİ ve başaramadı" aynı kovada (FAZLA sayar) |
| B6 / yüzey 2 | `icra_rc=0`: "koştu ve başardı" ile "HİÇ KOŞMADI" aynı değerde |
| **B8 / yüzey 3** | **koşan ve DÜŞEN tur hiç sayılmıyor (EKSİK sayar)** |

Üçüncü ölçülmüş vaka → **tekil yama KESİNLİKLE YASAK** ([[ucuncu-tekrar-sinif-kapisi]]).
Sınıf çözümü: bir turun hükmü **tek bir yerde** ve **tüm çıkış yollarını kapsayacak** biçimde
kaydedilmeli; erken `return` eden her kol da sayaca uğramalı (ya da sayaç `finally`'ye alınmalı).

### Kabul
1. **Pozitif:** tur koşar + onarım üretir → sayaç 0'a düşer.
2. **Negatif-1:** tur koşar + düşer (`SURE_TAVANI` dahil) → sayaç **+1** (bugün artmıyor).
3. **Negatif-2:** tur ATLANDI (kilit dolu) → sayaç **DEĞİŞMEZ** (atlanan tur onarımsız tur
   değildir — B6 ile tutarlı).
4. **Mutant:** erken `return` kolu sayacı yeniden atlarsa test KIRMIZI yanar; hedef kolun
   öldüğü ayrıca kanıtlanır.
5. Üç kolun **hepsi** aynı sayaç yolundan geçtiği, çıkış yollarının envanteriyle gösterilir
   (`return` sayısı = ölçülen kol sayısı; sayı çivili).

---

## B2/B3 — 🔴 BU PAKETTE DEĞİL: "HAT BOZUK" DEĞİL "KAT YOK" → OKAN KAPISI

10 kalemin hepsi `kat_sec` (`nobet-kapi.py:287-299`) tarafından `EMEKLI_MOTOR_JETONLARI`
(`:131-135`) üzerinden MİMAR'a düşüyor. Jetonlar: `kapi/kapı · nobetci · guvenlik · secret ·
sema · lisans · odeme · fiyat · mutasyon · fail-open · fail-closed · kilit · flock · kanca ·
hook · kabul testi`.

Kalem kalem gerekçe (hangi jeton, neden inemez):

| kalem | eşleşen jeton | inebilir mi |
|---|---|---|
| K49 | `kilit`, `flock` | ❌ D1 yazıcı kilidi = veri kaybı sınıfı, sessiz hata |
| K53 | `kapi` | ❌ hasat kapısının üreticisi = kapı kodu |
| K70 | `kapi`, `kanca`, `fail-open` | ❌ commit kancası fail-open |
| K77 | `kapi` (sınıf atfında) | ❌ nöbet hükmü + alarm yüzeyi |
| K80 | `kapi` | ❌ CI'ya bağlı bloklayıcı kapı |
| K84 | `fail-open` | ❌ denetim körlüğü, sessiz hata |
| K86 | `mutasyon` | ❌ üç mutasyon bataryası kapsam deliği |
| K96 | `kapi` (`uretim-butunluk-kapisi`) | ❌ yayını bloklayan üretim kapısı |
| K105 | `mutasyon` | ❌ mutasyon çapası tekil değil |
| K108 | `kapi` (`model uyeligi kapisi`) | ❌ CI zinciri + kapı |
| K98 | `kime=Okan` / merge hükmü | ❌ OKAN katı |

**Bu sınıflandırma DOĞRUDUR ve CLAUDE.md ile birebir örtüşür:** *"CLAUDE'da kalan: kapı/ölçüm
kodu · ödeme-fiyat · güvenlik/secret · gizlilik · şema · lisans/satılabilirlik · merge/deploy
hükmü"* ve *"Claude işçisi KraL+MaCiT'te KOŞULSUZ RED"*.

⇒ Yani bu 10 kalem için **makinede iş yapabilecek bir kat YOKTUR**. Sayaç yalan söylemiyor;
doğruyu söylüyor: *hiçbir şey onarılmıyor, çünkü onaracak kat yok.*

🔴 **Sayacı bu yüzden GEVŞETME.** "Dağıtılabilir kalem yoksa sayaç artmasın" demek,
`nobet-kapi.py:72`'de kayıtlı sessiz-yeşil arızasını geri getirmektir. Sayaç bir ALARM'dır ve
alarm doğru çalışıyor.

**Okan kapısına çıkan karar (tarife/doktrin, mimar veremez):**
1. MİMAR sınıfı kalemler için ücretli bir kat açılacak mı (`PRUVO_CLAUDE_ISCI_IZNI=OKAN`),
   yoksa
2. bu 10 kalem mimarın kendi turlarında mı kapatılacak (o hâlde sayaç 105+ olarak KALIR ve
   bu **kabul edilmiş** bir durumdur, arıza değildir)?

Karar verilene kadar `ustuste_onarimsiz`'in düşmesi **B4 çözülse bile** yalnız K55 üzerinden
mümkündür (12 kalemin 1'i).
