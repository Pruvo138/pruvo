# PAKET — Marka dili: ÜRETEÇ hattının kapatılması (KraL → MaCiT)

**Tarih:** 17 Ağu 2026 · **Kaynak:** K161 (kapı KIP ekseni) kapanışı · **Ölçüm:** canlı katalog 29.037

---

## 0. NEDEN — bu bir metin temizliği değil, ÜRETEÇ kusurudur

17 Ağu'da katalogdaki üretim-süreci dili temizlendi: kapı envanteri **297 vuruş / 284 kayıt →
21 / 14**, `malzemeden basılır` **216 → 0**. Ama **temizlik kalıcı değildir**: metni üreten hat
aynı kalıbı basmaya devam ederse her yeni parti sınıfı geri getirir.

🔴 **Kök neden ölçüldü ve şaşırtıcı: talimat da kapı da AYNI hatayı yapıyordu — ihlali
SINIF olarak değil, DİZGE olarak tanımlamışlar.**

`tools/thing-gemini.py:44` ve `tools/thing-icerik.py:125` üreteçlere şunu söylüyor:

> MARKA DILI (ZORUNLU): Sitede **"3D baski" / "3D printed" IFADESI** YASAK.

`tools/URUN-EKLEME-REHBERI.md:60` insan gözden geçirmesine de aynı şeyi söylüyor:

> açıklama **"3D baskı" demiyor mu**

**`"Sert malzemeden basılır."` bu talimatların HİÇBİRİNİ ihlal etmez** — içinde ne "3D baskı"
ne "3D printed" geçer. Üreteç kuralı harfiyen uyguladı, çıktı doktrini ihlal etti, insan
kontrolü de aynı dizgeye baktığı için onayladı. 216 kayıt böyle doğdu.

Aynı kusur kapıda da vardı (kapı `basıl-` fiilini yalnız yanında PLA/PETG gibi bir jeton
varsa görüyordu → 288 satırın 238'i UYARI'da kalıp bloklamıyordu). Kapı 17 Ağu'da kapatıldı;
**bu paket üreteç tarafını kapatır.** Ders: [[kapi-uretici-dili-degisince-korlesir]].

⚠️ **Aciliyet:** kapı artık BLOKLUYOR. Bu paket uygulanmazsa bir sonraki parti
`denetim-kapisi.py --commit-farki` ile **kırmızı yanar ve deploy durur** (17 Ağu'da SEAT
partisinde tam olarak bu oldu, `pruvo` deploy'u saatlerce kırmızı kaldı).

---

## 1. SAHİPLİK — iki yarı, iki ev

| Yüzey | Dosya | Sahip |
|---|---|---|
| AI üreteç prompt'ları | `tools/thing-gemini.py` · `tools/thing-icerik.py` | **KraL** (bu ev) |
| İnsan gözden geçirme talimatı | `tools/URUN-EKLEME-REHBERI.md` | **KraL** (bu ev) |
| Parti içerik yazımı + stage öncesi kontrol | `~/dev/pruvo-hasat/kalibrasyon/SPEC-*.md`, `olcum/*_veri.py` | **MaCiT** |

KraL yarısı bu pakette **ayrı bir kalem** olarak yürür; MaCiT'in beklemesi gerekmez —
§3'teki stage-öncesi kapı tek başına partiyi korur.

---

## 2. KURAL — dizge değil SINIF

**Yasak olan bir kelime değil, bir ANLAM SINIFIDIR: PRUVO'nun üretim SÜRECİNE dair her dil.**
Müşteriye giden metin ürünün NE OLDUĞUNU ve NEYE UYDUĞUNU anlatır; NASIL yapıldığını anlatmaz.

### 2a. Yasak sınıf (örnekler — liste kapalı değil)
- `basıl-` kökünün **her kipi**: basılır · basılan · basılacak · basılması · basılmadan · basım
- `baskı` isminin **süreç çekimleri**: baskı sonrası · baskıda ölçü · test baskısı ·
  baskıyla üretilen · dekoratif baskı modeli · baskı muhafaza/kutu
- dilimleyici/makine dili: dolgu oranı · katman yüksekliği · destek · filament · nozul çapı ·
  duvar/kabuk sayısı · brim/raft · Cura/PrusaSlicer · FDM/SLA/infill
- dosya dili: STL · 3MF · gcode · "dosya dahildir"
- makine parkı: "bazı yazıcılarda" · "baskı yatağına sığar"
- malzeme **TAVSİYESİ**: "PETG önerilir" (malzeme **BEYANI** serbesttir: "PETG malzemededir")

### 2b. Kanonik karşılıklar (Okan onaylı, 17 Ağu — katalogda uygulandı)

| Yerine YAZMA | ŞUNU yaz |
|---|---|
| `Sert malzemeden basılır.` | `Sert malzemeden üretilir.` |
| `Esnek malzemeden basılması önerilir.` | `Esnek malzemeden üretilmesi önerilir.` |
| `İnce ama sağlam basılır.` | `İnce ama sağlam üretilir.` |
| `… basılmadan önce ölçek kalibre edilmelidir.` | `… üretilmeden önce ölçek kalibre edilir.` |
| `dekoratif baskı modeli` | `dekoratif modeli` |
| `baskı sonrası` | `üretim sonrası` |
| `baskıyla üretilen` | `özel üretilen` |
| `baskıda ölçü / ölçek` | `üretimde ölçü / ölçek` |
| `test baskısıyla` | `deneme üretimiyle` |

🔴 **Anlamı koru, cümleyi KISALTMA.** Ev yazımı `üretilir`dir (katalogda canlı: "Orijinal
geometriye sadık üretilir").

### 2c. DOKUNULMAZ — bunlar ihlal DEĞİL
Türkçe çok anlamlıdır; aşağıdakiler meşru ve **düzeltilmemelidir**:
- **BASMA** (press): `düğmeye kazara basılmasını önler` · `ayakla basılan pedal` ·
  `parmakla rahat basılır` · `fitil yerine basılır`
- **BASINÇ** (kuvvet): `baskıyla oturur` · `hafif baskı ile takılır` · `yay baskısı` ·
  `baskı balatası` · `baskı takozu` · `baskı aparatı/aleti` · `su baskını` · `baskılı devre`
- **HEDEF CİHAZ**: ürünün kendisi bir 3D yazıcı parçasıysa cihazın sözlüğü (baskı tablası,
  ekstruder, OctoPrint) MEŞRU UYUM bilgisidir.

Ölçüldü: bu iki sınıfta 11/11 başlık + 10/10 cümle onarımdan **dokunulmadan** geçti.

---

## 3. MaCiT'in İŞİ

### 3.1 🔴 STAGE ÖNCESİ KAPI — parti push'lanmadan ÖNCE koş (EN ÖNEMLİ MADDE)
Kapı zaten var ve parti kapsamında koşabiliyor. Yeni id'ler `urunler.json`'a yazıldıktan
sonra, **push'tan önce**:

```
python3 tools/denetim-kapisi.py --idler <id1> <id2> <id3> ...
```

`IHLAL: 0` görmeden push etme. `IHLAL > 0` ise ihlal satırları hangi cümleyi ve hangi kuralı
tetiklediğini yazar; §2b tablosuyla düzelt, tekrar koş.

Alternatif (çalışma ağacındaki tüm yeni kayıtlar için, id yazmadan):
```
python3 tools/denetim-kapisi.py
```
(bayraksız kol = çalışma ağacı EKSİ HEAD; commit'lenmemiş parti için doğru koldur.)

### 3.2 Parti içerik spec'lerine SINIF kuralını yaz
`~/dev/pruvo-hasat/kalibrasyon/SPEC-*.md` şablonlarında marka dili maddesi bugün
(varsa) "3D baskı deme" biçimindedir. Onu §2a + §2b + §2c ile **değiştir** — dizge yasağı
sınıf yasağına çevrilsin. Yeni parti spec'i yazan her tur bu maddeyi taşısın.

### 3.3 Mevcut içerik dosyalarını tara (yeniden kullanılıyorlar)
`kalibrasyon/hasat-*-icerik*.json` ve `olcum/_*_veri.py` dosyalarında kalıp duruyor; bunlar
sonraki partilere kopyalanırsa sınıf geri gelir. Tara ve §2b ile düzelt:

```
grep -rln "malzemeden bas\|Sert malzemeden\|Darbeye dayanıklı sert" /Users/okan/dev/pruvo-hasat/kalibrasyon /Users/okan/dev/pruvo-hasat/olcum
```

⚠️ Bunlar **fikstür/kaynak** dosyalarıdır, canlı katalog değil — `urunler.json`'a
DOKUNMA (o düzlem 17 Ağu'da zaten temizlendi, `SILINEN_URUN=0`).

### 3.4 🔴 KARMA CÜMLE — toplu metin düzeltirken bunu bilin
Aynı cümlede hem marka dili ihlali hem BAŞKA bir ihlal (ör. `STL`) varsa, yarım düzeltme
ötekinin gerekçe metnini değiştirir; `--commit-farki` onu "bu itmenin GETİRDİĞİ" sanar ve
**tüm ekibin yayınını durdurur.** Ölçüldü: tek kayıt (`cup-holder-100mm-dacia-logan-2009`)
`--commit-farki`yi rc=1 yaptı. Kural: **cümleyi ya tamamen temizle ya hiç dokunma.**

---

## 4. KraL'ın İŞİ (bu evde, ayrı kalem)
1. `tools/thing-gemini.py:44` + `tools/thing-icerik.py:125` — "IFADESI YASAK" dizge kuralı
   §2a/§2b/§2c sınıf kuralıyla değiştirilecek.
2. `tools/URUN-EKLEME-REHBERI.md:60` — `açıklama "3D baskı" demiyor mu` kontrolü
   §3.1'deki **çalıştırılabilir kapı çağrısıyla** değiştirilecek (göz kontrolü dizgeye
   bakıyor, kapı sınıfa bakıyor).
3. Üreteç prompt'una kanonik karşılık tablosu (§2b) gömülecek — üreteç doğru kalıbı
   **ilk seferde** bassın, düzeltmeye kalmasın.

---

## 5. KABUL (çalıştırılabilir — "bakıldı iyi" kabul değil)

```
python3 tools/denetim-kapisi.py --idler <yeni parti id'leri>     # IHLAL: 0
python3 tools/ifsa-kip-test.py                                    # rc=0, KALAN=0
python3 tools/denetim-kapisi.py --tum-katalog --envanter          # vurus ≤21 (bugünkü taban)
```

- **Parti kabulü:** `--idler` kolu `IHLAL: 0` **VE** push sonrası CI `serit-a3` success.
- **Sınıf kabulü:** iki ardışık parti, elle düzeltme YAPILMADAN `IHLAL: 0` versin — üreteç
  doğru kalıbı kendiliğinden basıyor demektir. Tek partilik yeşil sınıfı kapatmaz.
- **Regresyon nöbeti:** `--tum-katalog --envanter` vuruşu **21'i AŞMAMALI**. Aşarsa yeni
  parti sınıfı geri getirmiştir.

---

## 6. NOTLAR
- Bu paket ürün SİLMEZ. `denetim-kapisi.py --uygula --evet-sil N` bu sınıfta **doktrin
  ihlalidir** (Okan: "sitede bulunan tüm ürünler satılabilir, SAKIN siteden bir ürün SİLME").
  Kapı o çareyi reçete etse bile koşulmaz.
- Kalıntı (K161, ayrı parti): kapı kapsamında ama kalıp tablosu dışında **10 kayıt** +
  karma cümle nedeniyle bilerek atlanan **1 kayıt** duruyor. Bunlar MaCiT'in değil ayrı bir
  temizlik kaleminin konusu; `python3 tools/ifsa-metin-onar.py` (report-only) ID'leriyle listeler.
- Onarım aracı `tools/ifsa-metin-onar.py` deterministiktir (AI YOK) ve `tools/duzelt.py`
  üzerinden yazar — flock + guard + ölçü satırı koruması bedava gelir.
