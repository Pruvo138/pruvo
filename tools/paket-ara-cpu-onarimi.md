# /ara CPU tavani olayi — ONARIM PAKETI (uygulanacak depo: `~/dev/pruvo-bot`)

**Kat:** MÜHENDİS = Claude Opus (arama semantiği "hatası sessiz" sınıfı).
**Durum:** kök neden ÖLÇÜLDÜ, onarım CANLI D1'de (salt-okunur) KANITLANDI, kod DEĞİŞİKLİĞİ
HENÜZ UYGULANMADI — çünkü dosya bu deponun dışında (HocA evi) ve deploy Okan kapısıdır.

---

## 1. OLAY (canlı, müşteri 500 gördü)

Canlı `/ara` ucu `D1_ERROR: D1 DB exceeded its CPU time limit and was reset` dönüyor.

Sıralı prob (30 istek, önbellek kırık, `_nonce`):

| ölçüm | değer |
|---|---|
| istek | 30 |
| başarısız | 5 |
| oran | **%16,7** |
| p50 | 417 ms |
| p95 | 30.230 ms |

Sorgu sınıfına göre ayrıştırma (aynı prob, sınıf başına ayrı koşum):

| sınıf | istek | başarısız | oran | p50 | p95 |
|---|---|---|---|---|---|
| tek-kelime (1 token) | 24 | 0 | %0 | 358 ms | 454 ms |
| çok-kelime (2 token) | 24 | 0 | %0 | 430 ms | 11.472 ms |
| marka+parça (3-4 token) | 24 | 11 | **%45,8** | 12.114 ms | 30.333 ms |
| uzun sorgu (8-10 token) | 12 | 12 | **%100** | 30.158 ms | 30.206 ms |
| türkçe karakter (1 token) | 25 | 1 | %4 | 583 ms | 1.599 ms |

**Ayrım nettir: eksen TÜRKÇE KARAKTER DEĞİL, TOKEN SAYISIDIR.** 1-2 token %0, 3+ token
patlıyor. Türkçe-karakter sınıfındaki tek başarısızlık (`göcek`, 1 token) yan hasardır:
D1 "reset" edildiğinde aynı anda gelen masum sorgu da düşer.

`mod=ege` ucu AYNI probda **0/20 başarısız** — Ege bu olaydan ETKİLENMİYOR (gerekçe §5).

---

## 2. KÖK NEDEN — sessiz bir PLAN ÇEVRİLMESİ (indeks eksikliği DEĞİL)

`araD1()` şu sorguyu kurar:

```sql
SELECT <kart alanlari>
  FROM urunler_fts f JOIN urunler u ON u.rid = f.rowid
 WHERE f.hs LIKE ? AND f.hs LIKE ? AND ... AND u.yayinda = 1
 ORDER BY u.seq DESC LIMIT ?
```

`EXPLAIN QUERY PLAN` (gerçek katalog, 15.955 ürün):

**1-2 token — SAĞLIKLI (FTS sürücü, trigram indeksi çalışıyor):**
```
SCAN f VIRTUAL TABLE INDEX 0:L0L0
SEARCH u USING INTEGER PRIMARY KEY (rowid=?)
```

**3+ token — ÇEVRİLMİŞ (`u` dış döngüye geçti):**
```
SEARCH u USING INDEX urunler_yayin (yayinda=?)
SCAN f VIRTUAL TABLE INDEX 0:=L0L0L0L0
```

Çevrilmiş planda **yayındaki HER ürün için ayrı bir FTS araması** yapılır → tam tarama.

### Canlı D1 ölçümü (salt-okunur, `wrangler d1 execute --remote`)

| sorgu | rows_read | satır sorgusu | sayım sorgusu | **tek batch toplamı** |
|---|---|---|---|---|
| `Volvo S60 far braketi` | 16.121 | 6.810 ms | 6.465 ms | **13.275 ms** |
| `Grandland X havalandırma` | 15.930 | 19.225 ms | 18.358 ms | **37.582 ms** |
| `2016 passat b8 … sağ taraf` | 15.930 | 16.442 ms | 17.017 ms | **33.459 ms** |
| `tekne` (1 token) | 1.840 | 5,4 ms | 3,0 ms | 8,4 ms |
| `kapı kolu` (2 token) | 612 | 3,5 ms | 2,1 ms | 5,6 ms |

Satır ve sayım sorguları `env.KATALOG.batch([...])` ile **aynı çağrıda** koşuyor; yani
maliyet ikiye katlanıp tek bir CPU bütçesine yükleniyor. 13-37 saniye CPU → tavan aşılır.

### ÇEVRİLMEYİ MÜMKÜN KILAN ŞEY NE?

`urunler_yayin(yayinda, seq DESC)` indeksi. İkisi de 31 Tem'de, atomik yayınla geldi:

* `d1-sync.py` → `YAYIN_INDEKS` (bu depo, KraL)
* `araD1()` → `kosul.push("u.yayinda = 1")` (pruvo-bot, commit `4f5a848`, 31 Tem 17:42)

Bu indeks olmadan planlayıcının `u`'yu dış döngüye alacak ucuz bir yolu YOKTU. Yerel ikizde
kanıtlandı — **tek fark indeksin varlığı, sorgu metni aynı:**

| `Grandland X havalandırma` | VDBE adımı | süre |
|---|---|---|
| `urunler_yayin` VAR (bugünkü canlı) | 36.041.000 | 18.090 ms |
| `urunler_yayin` YOK | 2.000 | 8,1 ms |

**İki doğru değişiklik birleşince sessiz bir performans regresyonu doğurdu; ikisi de tek
başına zararsızdı.** Regresyon sorgu METNİNDE değil, PLANDA yaşıyor — bu yüzden hiçbir
mevcut kapı görmedi (parite testleri SONUCU karşılaştırır, PLANI değil).

---

## 3. ONARIM — `JOIN` → `CROSS JOIN` (tek kelime)

SQLite'ta `CROSS JOIN` sonuç kümesini **değiştirmez**; yalnızca planlayıcının birleşim
sırasını yeniden düzenlemesini KAPATIR (soldaki tablo daima dış döngü). Yani `f` sürücü
kalır, trigram indeksi her token için çalışır.

### Uygulanacak diff — `~/dev/pruvo-bot/worker/src/index.js`, `araD1()` (≈ satır 2231)

```diff
   // Token yoksa FTS'e hiç girme — kısıtsız FTS taraması boşuna okuma olur.
+  // 🔴 CROSS JOIN — `JOIN` DEĞİL, ve bu bir yazım tercihi DEĞİL. SQLite'ta CROSS JOIN
+  // sonuç kümesini DEĞİŞTİRMEZ, yalnızca planlayıcının birleşim sırasını yeniden
+  // düzenlemesini kapatır. Düz `JOIN` iken (31 Tem, canlı) 3+ token'li sorgularda plan
+  // çevriliyordu: `SEARCH u USING INDEX urunler_yayin` dış döngü olup yayındaki HER ürün
+  // için ayrı FTS araması yapılıyordu -> tam tarama. Canlı D1'de ölçüldü
+  // ('Volvo S60 far braketi'): rows_read=16.121, satır 6.810 ms + sayım 6.465 ms = 13.275 ms
+  // TEK batch'te -> `D1_ERROR: exceeded its CPU time limit`, müşteriye 500. Sıralı probda
+  // 30 istekten 5'i düşüyordu (%16,7); 10 token'li sorguda %100.
+  // Çevrilmeyi mümkün kılan `urunler_yayin` indeksidir (atomik yayınla geldi) — yani
+  // indeksi kaldırmak DEĞİL, birleşim sırasını SABİTLEMEK doğru onarımdır.
+  // Kapı: `python3 tools/ara-maliyet-kapisi.py` (pruvo deposu) — plan çevrilirse KIRMIZI.
   const kaynak = tokens.length
-    ? "urunler_fts f JOIN urunler u ON u.rid = f.rowid"
+    ? "urunler_fts f CROSS JOIN urunler u ON u.rid = f.rowid"
     : "urunler u";
```

**Şema değişikliği YOK** → `d1-sync.py --sema` sırası gerekmiyor. Yalnız Worker deploy'u.

### Canlı D1'de onarım sonrası (aynı uç, aynı veri, salt-okunur)

| sorgu | ÖNCE (JOIN) | SONRA (CROSS JOIN) | kazanç |
|---|---|---|---|
| `Volvo S60 far braketi` | 13.275 ms / 16.121 satır | **3,6 ms / 9 satır** | 3.688x |
| `Grandland X havalandırma` | 37.582 ms / 15.930 satır | **5,4 ms / 1 satır** | 6.960x |
| `2016 passat b8 … sağ taraf` | 33.459 ms / 15.930 satır | **5,9 ms / 1 satır** | 5.671x |
| `tekne güverte … halat tutucu braket` | (zaman aşımı) | **12,7 ms** | — |
| `tekne` (1 token) | 8,4 ms | 14,7 ms | ~aynı |
| `kapı kolu` (2 token) | 5,6 ms | 6,4 ms | ~aynı |
| `b8 x s6` (hepsi kısa token) | 107,2 ms | 96,6 ms | ~aynı |

**En kötü hal artık 96,6 ms** (tek/kısa token, trigram kullanılamaz, kaçınılmaz tam tarama).
D1 CPU tavanının çok altında.

### SONUÇ AYNI MI? (asıl şart)

`Volvo S60 far braketi` — CROSS JOIN ile dönen satırlar:
```
volvo-s60-v60-far-braketi-31294522
volvo-s60-v60-far-tutucu-braketi-31294521
volvo-s60-v60-far-montaj-braketi-89093257
toplam = 3
```
Bugünkü şeklin döndürdüğü ile **birebir aynı** (aynı 3 satır, aynı `toplam`).

Ayrıca 600 sorguluk korpusta id listesi + `toplam` karşılaştırıldı: **semantik sapma = 0**
(bkz. `tools/ara-maliyet-kapisi.py`).

---

## 4. NEDEN BU SEÇENEK — ölçülen alternatifler

Dört şekil aynı ikizde, aynı 9 sorguda ölçüldü (toplam duvar süresi):

| şekil | toplam süre | not |
|---|---|---|
| A bugünkü (`JOIN`) | **114.304 ms** | olayın kendisi |
| **A' `CROSS JOIN`** | **45,1 ms** | ✅ seçilen — koşullar BYTE olarak aynı |
| B tek FTS sürücüsü + `instr()` süzme | 209,2 ms | daha büyük diff, bazı sorguda daha yavaş |
| B' B + CROSS JOIN | 70,6 ms | gereksiz — A' zaten yeterli |

**A' seçildi, üç gerekçeyle:**

1. **En hızlısı** (45,1 ms; B'nin 4,6 katı iyi). Sebebi: A' TÜM token'ları trigram
   indeksine verir (`INDEX 0:L0L0L0L0`), B yalnızca birini verip kalanını satır satır
   `instr()` ile süzer.
2. **En küçük diff ve en düşük semantik risk.** A' `WHERE` koşullarına HİÇ dokunmaz —
   tek kelime değişir, eşleşme kuralı aynı kalır. B, `f.hs LIKE` kısıtlarını
   `instr(u.hs, ?)` ile değiştirirdi; eşdeğer olduğu gösterilebilir ama bu, "hatası sessiz"
   sınıfında gereksiz bir kanıt yükü demektir.
3. **B ölçülen bir GERİLEME getiriyordu:** `kapı kolu` (2 token, sık sorgu sınıfı) canlı
   D1'de 5,6 ms → 59,4 ms (sayım sorgusu 16.134 satır okuyor, çünkü ikinci LIKE düşünce
   sayım tam taramaya kalıyor). A'da böyle bir gerileme YOK.

Değerlendirilip ELENEN diğer seçenekler:
* **`urunler_yayin` indeksini kaldırmak** — çevrilmeyi durdurur ama atomik yayının
  `katalogD1` OFFSET taramasını indeksten düşürür (şemadaki gerekçeye bakınız). Bir
  regresyonu başkasıyla takas etmek.
* **Sonuç tavanı / uç önbelleği** — semptomu maskeler, tam taramayı durdurmaz; önbellek
  ıskalayan ilk istek yine 500 döner.
* **Ayrı `COUNT(*)` sorgusunu kaldırmak** — maliyeti yarıya indirirdi, 13 s yerine 6,8 s;
  tavan yine aşılırdı. Kök neden bu değil.

---

## 5. EGE ETKİLENMİYOR — `mod=ege` dalına DOKUNULMUYOR

`egeD1Kos()` ön-süzgeci OR zinciri kurar (`f.hs LIKE ... OR f.hs LIKE ...`). Planı:

```
... INDEX 1 / SCAN f VIRTUAL TABLE INDEX 0:L0   (her terim icin ayri trigram taramasi)
SEARCH u USING INTEGER PRIMARY KEY (rowid=?)
```

Çok-indeksli OR birleşimi `f`'yi sürücü tutuyor; 20 terimde bile çevrilme YOK. Canlı ölçüm
de bunu doğruluyor: `mod=ege` probunda 0/20 başarısız. **Ege'nin ağzına da, sorgusuna da
dokunulmuyor.**

---

## 6. KABUL — çalıştırılabilir

```
python3 tools/ara-maliyet-kapisi.py               # 600 sorgu: semantik + plan ekseni
python3 tools/ara-maliyet-kapisi.py --kendini-test # kapi KIRMIZI yanabiliyor mu
node    tools/parite-test.js                       # canli uc paritesi (deploy SONRASI)
node    tools/parite-ege.js                        # Ege paritesi (deploy SONRASI)
```

`tools/ara-maliyet-kapisi.py` bu olay sınıfını kalıcı olarak kapatır: ağsız, deterministik,
CI'da koşabilir; hem semantik sapmayı hem plan çevrilmesini ölçer ve `--kendini-test` ile
mutasyonu (`CROSS JOIN` → `JOIN`) 3/3 yakaladığını KANITLAR.
