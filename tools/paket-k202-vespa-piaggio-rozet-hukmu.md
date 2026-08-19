# PAKET K202 — Vespa/Piaggio çapraz rozet hükmü (YAYIN AÇICI) + sınıf kalemi

> ⚖️ MİMAR HÜKMÜ (KraL, 19 Ağu ~02:1x TRT / 23:1xZ). İcra CHIP'te, worktree'de.
> Mimar eli koda sürmez: aşağıdaki hüküm BAĞLAYICI, satırları işçi yazar, kabul kapıları ölçer.

## 0. NEDEN ŞİMDİ — ÖLÇÜLDÜ, VARSAYILMADI

`deploy.yml` **ardışık 3 push'ta KIRMIZI**; son yeşil yayın `32941dfe` (21:31Z).
Kırmızının kökü tek satır (koşum `32191804434`, iş `serit-a3`, birebir çıktı):

```
KALDI K19 ÇAPRAZ-MARKA ÇİFTİNİN YARGISI VAR (yargısız sayfa doğmaz; 108 çift/50 model)
  — YARGISIZ (sızıntı)=['Piaggio|50', 'Piaggio|50special', 'Piaggio|smallframe',
                        'Vespa|50', 'Vespa|50special', 'Vespa|smallframe']
  · imza=b01f6f590b99ac82 beklenen=b01f6f590b99ac82 sayı=64 beklenen=64
```

Tetikleyen veri: `54d69028` (Piaggio/Vespa × MakerWorld dilim 2, +29 ürün).

**K19 HAKLI, kapı kusurlu DEĞİL.** Reddettiği şey kapının meşru amacına birebir giriyor:
yargısız sayfa doğmasın. [[ucuncu-tekrar-sinif-kapisi]] testini uyguladım:
(a) kapı doğru kümeyi ölçüyor (üretimde doğacak sayfalar), (b) red gerçek bir yargı
boşluğu — yanlış-pozitif DEĞİL. Dolayısıyla burada yasak olan "tekil yama" **hükmü
yazmak değil**, hükmü yazıp sınıfı kapatmamaktır. Sınıf ayrı kalem olarak §4'te açıldı.

## 1. HÜKÜM — EMSAL BİREBİR MEVCUT, YENİ İÇTİHAT YOK

Piaggio **ana marque**, Vespa onun rozetidir. Bu tam olarak K170'te (`largeframe`)
verilmiş hükmün aynısıdır; `arama.py` içinde ZATEN yazılı:

- deny: `("Piaggio","GTS"|"Primavera"|"PX"|"Largeframe")` → "…VESPA rozetidir; gerçek
  sayfa `/marka/vespa/<token>/`. Ürünler Piaggio ağacında durur; ürün KAYBOLMAZ"
- allow: `"Vespa|gts"|"Vespa|primavera"|"Vespa|px"|"Vespa|largeframe"` → `("ROZET", …)`
- `"Vespa|largeframe"` gerekçesi zaten **`("Vespa","Smallframe")` emsaline** atıf yapıyor.
- Jeton tablosunda `("Vespa","Smallframe")` = "gövde AİLE adı" ve `("Vespa","50")` =
  "ikonik tek araç, çıplak sayı ama Vespa altında TEKİL" olarak ZATEN yargılı.

Buradan altı çiftin hükmü **türetilir, icat edilmez**:

| çift | hüküm | gerekçe (emsal) |
|---|---|---|
| `Vespa\|smallframe`  | **ROZET**     | gövde aile adı; emsal birebir `Vespa\|largeframe` |
| `Vespa\|50`          | **ROZET**     | Vespa 50 / V50 gerçek rozet; jeton tablosunda yargılı |
| `Vespa\|50special`   | **ROZET**     | Vespa 50 Special gerçek rozet (50'nin donanım rozeti) |
| `Piaggio\|smallframe`| **ROZET_DIŞI**| Smallframe VESPA gövde ailesi; emsal birebir `Piaggio\|Largeframe` |
| `Piaggio\|50`        | **ROZET_DIŞI**| `Piaggio 50` diye araç satılmadı; emsal `Piaggio\|PX` |
| `Piaggio\|50special` | **ROZET_DIŞI**| aynı eksen; emsal `Piaggio\|PX` |

🔴 **BEKLER sınıfına HİÇBİRİ girmez.** Altısının da emsali birebir mevcut; "mimar hükmü
bekliyor" yazmak burada yargıyı ertelemek olur, yayın da kapalı kalır.

🔴 **Ürün kaybı YASAK.** Piaggio tarafı deny'e girince ürünler **Piaggio ağacında kalır**,
sayfa doğmaz. K11'in `kaybolan ürün=0` ölçütü bunun kapısıdır ve gevşetilemez.

## 2. İCRA — jeton biçimini TÜRET, TAHMİN ETME

Deny tablosu (`ROZET_DISI_CIFT`) gösterim biçimini (`"Largeframe"`), K19 anahtarı
normalize biçimi (`piaggio|largeframe`) tutuyor. `50 Special` ↔ `50special` ayrımı
bu yüzden **koddan türetilecek**: normalize fonksiyonunu oku, biçimi ondan çıkar.
Tahminle yazılmış bir jeton kapıyı sessizce yanıltır.

İki tablo da **imza + sayı** taşıyor; ikisi de elle DEĞİL, kodun kendi hesabıyla
tazelenecek (`rozet_capraz_imzasi()` ve K12'nin karşılığı). Sayıyı elle yazıp imzayı
eski bırakmak [[kayit-kendini-olcmez]] (K201) sınıfına girer.

## 3. KABUL — ÖNCEDEN ÇİVİLENDİ, BULGU ÖLÇÜTÜ BÜYÜTMEZ

Beşi de YEŞİL olmadan merge YOK. Bulunan her yeni kusur **ayrı kalem** olur, bu liste sabit.

1. **K19 boşaldı:** `serit-a3` çıktısında `YARGISIZ (sızıntı)=-` (boş liste), `GECTI K19`.
2. **Sayı/imza türetilmiş:** allow `64 → 67`, deny `46 → 49`; her iki `beklenen=` alanı
   kodun kendi hesabıyla eşleşiyor (elle yazılmış sayı = RED).
3. **Ürün kaybı sıfır:** `GECTI K11 … kaybolan=0`; Piaggio ağacındaki ürün sayısı
   değişimi **0** (öncesi/sonrası SAYIYLA raporlanacak).
4. **MUTANT 6/6 + HEDEF KOL ATFI (K182):** altı satırın **her biri tek tek** silindiğinde
   K19 KIRMIZI yanmalı ve kırmızının sebebi **o çift** olmalı — "kırmızı geldi" yetmez,
   çıktıdaki `YARGISIZ` listesinde tam o anahtar görünmeli. Ayrıca **KONTROL mutantı**:
   `Vespa|smallframe` satırının sınıfını `ROZET`→`BEKLER` kaydıran mutant da kırmızı
   yakmalı (imza yalnız anahtarı imzalıyor; sınıf ekseni ayrı ölçülmeli).
5. **Komşu kapı sessiz kalmalı:** K12 ve K21 imzaları **yalnız beklenen yönde** değişir;
   `deny/allow çelişkisi=-` ve `envanterde var üretimde yok=-` boş kalır.

Merge sonrası: `deploy.yml` koşumu **güncel ucu içeren** koşumda `conclusion=success`
(K144: uçuştaki koşumun `cancelled` olması arıza değil, güncel uç ölçülür).

## 4. SINIF KALEMİ — K202 (bu pakette KAPANMAZ, açılır)

Aynı gerekçe cümlesi ("X bir VESPA rozetidir, Piaggio ana marque'tir") bugün **8. kez**
elle yazılıyor: GTS · Primavera · PX · Largeframe · Smallframe · 50 · 50special (+ana marque).
Her Vespa veri dilimi yeni çiftler doğuruyor ve her biri mimarı bekletiyor — yani yayın
gecikmesi **veri hacmine bağlı ve tekrarlanabilir**.

**Yön (hüküm DEĞİL, araştırma kalemi):** ana-marque ⊃ marque ilişkisi BİR KEZ beyan
edilsin (`Piaggio ⊃ Vespa`), çift hükmü o ilişkiden **TÜRETİLSİN**: marque token'ı →
marque'a ROZET, ana marque'a ROZET_DIŞI. Enumerasyon yerine kural.

🔴 **Türetim gevşetme OLMAMALI:** türetilmiş her çift, bugün elle yazılmış hükümle
**birebir aynı sonucu** vermeli (mevcut 8 çift regresyon fikstürü olur) ve türetimin
GÖREMEDİĞİ çift hâlâ `YARGISIZ` kalmalı — fail-closed. Türetim "her çifti otomatik
onaylayan" bir muafiyet listesine dönüşürse K19'un tüm koruması ölür.

kabul (K202): mevcut 8 çift türetimden **birebir** çıkar **VE** ilişkisi beyan edilmemiş
bir marka çifti hâlâ `YARGISIZ` yakar (negatif vaka) **VE** 3 mutant hedef kolunu öldürür.
