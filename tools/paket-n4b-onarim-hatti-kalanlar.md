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

## B2/B3 — 🔴 BU PAKETTE DEĞİL: "HAT BOZUK" DEĞİL "KAT YOK" → OKAN KAPISI

10 kalemin hepsi `kat_sec` (`nobet-kapi.py:287-299`) tarafından `CODEX_JETONLARI`
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
