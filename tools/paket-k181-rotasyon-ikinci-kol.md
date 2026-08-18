# PAKET K181 — SINIF KAPISI: rotasyonun tek kolu var, kota bu yüzden 7 kez ELLE döndü

**Mimar:** KraL · **Tarih:** 18 Ağu 2026 · **Sınıf kalemi** ([[ucuncu-tekrar-sinif-kapisi]])

## OLGU (Okan ölçtü, 18 Ağu)
`DEVAM.md` commit'li **130/130** (satır marjı SIFIR), çalışma ağacı **133** → kanca commit'te
kesecek. Bu, kalemin **ikinci geri açılışı** ve rotasyon bugün **7. kez ELLE** döndü.
Üçüncü tekrar kuralı gereği **tekil yama ARTIK YASAK** — kalem sınıf olarak kapanacak.

## KÖK NEDEN (mimar teşhisi, ölçülebilir)
`defter-rotasyon.py`nin **TEK KOLU** var: **kapanmış** maddeyi arşive taşır. Bugün ölçüldü —
iki kapanış maddesini taşıdı ve sonra `TASINAN=0 TASINAN_MADDE=0 DEFTER_SATIR=135` dedi:
**yapacak işi kalmamıştı, defter hâlâ tavanın üstündeydi.** Oysa defter dört mimarın ortak
yazdığı append-ağırlıklı bir dosya ve büyümesi AÇIK kalemlerden geliyor. Bu yüzden her
mimar aynı el hareketini tekrarlıyor: açık bir kalemin gövdesini arşive taşıyıp yerine tek
satır işaretçi bırakmak. **7 kez elle yapılan şey, aracın ikinci kolu olmalıdır.**

🔴 Yanlış çareler (bilerek dışarıda): tavanı büyütmek (Okan ölçülü koydu, bugün bayt ekseni
de bağlandı) · satırları birleştirip tavanı kandırmak (bayt eksenini gizler, K178 bunun için
vardı) · madde silmek (Okan kuralı 11: **hiçbir şey silinmez, TAŞINIR**).

## MİMAR HÜKMÜ — İKİNCİ KOL: "gövdeyi arşive, yerine işaretçi"

1. **Tetik DAR:** ikinci kol yalnızca (a) herhangi bir eksen tavanı aşıyorsa **VE**
   (b) birinci kolun taşıyacağı kapanmış madde KALMADIYSA çalışır. Tavan altındayken
   ASLA çalışmaz — defteri kendiliğinden budamaz.
2. **Seçim kuralı:** en ESKİ tarihli açık maddeden başla (satırdaki `(<gg> Agu` damgası).
   Eşitlikte dosyadaki sıra. Her turda **BİR** madde indir, iki ekseni de yeniden ölç,
   ikisi de tavan altına inince **DUR** — fazla budama YASAK.
3. **Lossless (Okan kuralı 11):** maddenin TAM GÖVDESİ arşive yazılır (arşivde zaten varsa
   MÜKERRER YAZMA, işaretçiyi mevcut kayda bağla). Defterde kalan işaretçi şunları TAŞIR:
   kalem kimliği (`K###`/ad) · durum işareti (🔴/🟠/🔧/🔵) · **tek cümle** iş özeti ·
   "Tam metin ARSIVDE". Kimlik ya da durum kaybolursa kalem kuyruktan DÜŞER — bu bir
   veri kaybıdır, `KAYIP` yaz ve DUR.
4. **SAHİPLİK KÖRLÜĞÜ BİLEREK:** defter dört mimarın ortak dosyası; ikinci kol kimin
   kalemi olduğuna BAKMAZ. Güvenli olmasının sebebi işaretçinin kimlik + durum + arşiv
   yolunu taşıması: sahibi kalemini kaybetmez, yalnız gövdesi bir tık uzağa gider.
5. **Kapanmış maddeye dokunmaz** (o birinci kolun işi), **başlık/bölüm satırlarına dokunmaz**.

## 🔴 İKİNCİ DENEME — BİRİNCİSİ NEDEN DÜŞTÜ (18 Ağu, ölçüldü)
İlk tur `Error: Exceeded USD budget (10)` ile düştü ve **worktree BOŞTU**; buna karşılık ANA
ağaçta `tools/defter-rotasyon.py` 11 satırlık, **uygulanmamış özelliği anlatan** bir docstring
almıştı. İki ders, ikisi de bu turda BAĞLAYICI:

**A) AĞAÇ DİSİPLİNİ.** Sana verilen ağaçta çalış. **Mutlak yol
(`/Users/okan/dev/pruvo/tools/...`) KULLANMA** — göreli yol kullan. **Ana ağaca YAZMA**
(orada başka oturumların işçileri koşuyor). Tur sonunda kendi ağacının
`git status --short` çıktısını rapora yapıştır.

**B) SIRA: ÖNCE KOD, SONRA BELGE.** Docstring/rapor'u ÖNDEN yazma. Uygulanmamış bir özelliği
anlatan docstring hiç yoktan kötüdür ve tur düşerse geriye o yalan kalır.

**C) BU DİLİM DARALTILDI.** Bu turda YALNIZ şunlar var: ikinci kol + aşağıdaki BELİRLEYİCİ
FİKSTÜR + M1 mutantı. **M2/M3/M4 ve kontrol vakaları BU TURDA YOK** — ayrı dilimde istenecek.
Kapsamı kendiliğinden genişletme; bütçe bu yüzden yandı.

## KABUL (hepsi ZORUNLU, sayıyla)
```
python3 tools/defter-rotasyon.py --kendini-test   → DUSEN=0
python3 tools/defter-kota-kapisi.py --kendini-test → DUSEN=0   (K178 ekseni bozulmadi)
```
**FİKSTÜR (yeni, ZORUNLU): "kapanmış madde YOK ama tavan aşılıyor"** — 135 satırlık,
içinde HİÇ kapanmış madde olmayan sentetik defter. Beklenen: ikinci kol devreye girer,
defter ≤130 satır **ve** ≤12288 bayta iner, arşiv AYNI miktarda büyür, hiçbir kalem kimliği
kaybolmaz. 🔴 **Bu fikstür bu paketin varlık sebebidir**; yoksa iş bitmemiştir.

**MUTASYON (4, hepsi KIRMIZI yakmalı):**
- M1 ikinci kolu tamamen kaldır → yukarıdaki fikstür tavanın ÜSTÜNDE kalır.
- M2 tetiği gevşet (tavan altındayken de çalışsın) → "tavan altında dokunma" vakası kırmızı.
- M3 işaretçiden kalem kimliğini düşür → `KAYIP` kırmızı.
- M4 gövdeyi arşive yazmadan defterden çıkar → lossless bayt eşitliği kırmızı.
🔴 Mutant birden çok ekseni tetikliyorsa YALIT ([[mutant-yan-ekseni-de-tetikliyorsa-olcmez]]);
yalıtılamazsa `YALITILAMADI` yaz, "geçti" YAZMA.
**KONTROL (2, YEŞİL kalmalı):** tavan altındaki defter → hiç değişmez (bayt birebir) ·
kapanmış maddesi olan defter → yalnız BİRİNCİ kol çalışır.

## SINIR
- `DEVAM.md`nin BUGÜNKÜ içeriğini bu turda BUDAMA — araç onarılıyor, defter değil.
  (Aracı indirdikten sonra defteri mimar aracın KENDİSİYLE döndürecek; el hareketi BİTİYOR.)
- `urunler.json` / gizli kaynak düzlemi DOKUNULMAZ. Main'e push ETME, merge ETME.
- 🔴 **DALDA COMMIT ET** ve commit SHA'sını rapora yaz (bugün dört turda commit atlandı).

## RAPOR
Dalda, projenin kanonik mühendis raporu adıyla; her komutun rc'si + ham çıktı + yeni
fikstürün ÖNCE/SONRA satır-bayt tablosu + lossless bayt eşitliği. Geçici dosyayı SEN sil.
