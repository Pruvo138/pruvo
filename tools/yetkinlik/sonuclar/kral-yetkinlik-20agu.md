# KraL-Yetkinlik — motor × görev matrisi + kota/maliyet ölçümü (20 Ağu 2026)

> Bu dosya **ölçüm kaydıdır**, karar değildir. Abonelik hükmü Okan'ındır.
> Sayılar ham çıktıdan okundu; işçi prozası kanıt sayılmadı.

## 0) KAPSAM ÖN-ÖLÇÜMÜ — yeni koşum GEREKMEDİ

`sonuclar/` altındaki 8 dosya okundu. **12 hücrenin (2 motor × 6 görev) hepsi zaten
ölçülmüş**, çoğu 3-5 tekrarla. Eksik hücre YOK → batarya yeniden koşulmadı.
Bunun yerine iki şey yapıldı: (a) yanlış sınıflanmış hücrelerin **yeniden sınıflaması**,
(b) kararın asıl dayanağı olan **kota/maliyet** eksenlerinin ölçümü.

## 1) 🔴 DÜZELTME — kimi'nin 6 "başarısızlığı" KOTA'dır, yeteneksizlik DEĞİL

`batarya-3a`'daki 6 kimi hücresi `KALDI` yazıyor. Deponun **kendi commit'lenmiş
sınıflandırıcısı** bunu çürütüyor — `dogrula.py:_uc_hatasi_mi()`:

```
rc != 0  AND  kabul is None  AND  sure_sn < 15   →   DOGRULANAMADI (uç/kota hatası)
```

`batarya-3a` kimi bloğunun altı satırının **hepsi** bu koşulu sağlıyor:
rc=1, kabul=null, süre **4,259 / 3,237 / 2,629 / 3,652 / 2,664 / 2,300 sn**
(normal tur 28–75 sn). Bu blok, düzeltmeyi getiren `ce834098` commit'inden **ÖNCE**
koşmuştu; commit başlığı zaten birebir: *"uç hatasını yetenekten ayır"*.
Aynı motor bir sonraki bataryada (`batarya-3a2`) **6/6 GEÇTİ**.

→ O 6 hücre **KOTA sütununa** taşınır. Başarısızlık sütununda bırakmak kararı yanlış yöne çeker.

## 2) MOTOR × GÖREV MATRİSİ (düzeltilmiş sınıflandırıcıyla, son 3 tam batarya)

m3 = `batarya-3a/3b/3c` · kimi = `batarya-3a2/3b/3c` · süreler saniye

| Görev | minimax-m3 | süre (m3) | kimi | süre (kimi) |
|---|---|---|---|---|
| 1 tarayıcı/panel | **3/3** | 31,0 · 28,4 · 35,1 | **3/3** | 57,8 · 75,5 · 75,4 |
| 2 ölçüm/teşhis | **3/3** | 26,1 · 30,6 · 26,2 | **3/3** | 71,3 · 61,3 · 50,5 |
| 3 toplu dönüşüm | **3/3** | 42,6 · 25,5 · 35,3 | **3/3** | 60,0 · 54,0 · 61,2 |
| 4 kırmızıyı onarma | **3/3** | 34,4 · 35,9 · 67,7 | **3/3** | 48,3 · 58,7 · 46,5 |
| 5 uzun bağlam tarama | **2/3** | 100,5 ✓ · 77,3 ✗ · 33,2 ✓ | **3/3** | 49,0 · 56,0 · 52,6 |
| 6 talimat disiplini | **2/3** | 14,0 ✓ · 15,2 ✓ · 23,9 ✗ | **3/3** | 32,5 · 28,2 · 30,9 |
| **TOPLAM** | **16/18** | 682,9 sn (ort. 37,9) | **18/18** | 969,7 sn (ort. 53,9) |

- **KOTA sütunu:** kimi +6 hücre `DOGRULANAMADI` (batarya-3a, uç hatası). m3: **0**.
- **YALAN (uydurma):** her iki motorda da post-fix **0**. (Pre-fix m3 g5'te 1, codex'te 2.)
- **Tamamlanma:** post-fix hiçbir tur 1500 sn tavanına takılmadı; `raporsuz` yalnız düşen turlarda.
- m3 ortalama **1,42× daha hızlı**; kimi doğrulukta **2 hücre önde** (g5, g6).

### 🔴 "m3 panel süremez" notu ÇÜRÜK — ölçüldü
m3 görev 1'i **5 bataryada 5/5** geçti, her birinde `iz_dosyasi_sayisi=1`
(gerçek `mcp__playwright*` izi). Bugünkü canlı kanıt da var:
`baglam-olcum.tsv`'de önek kuralına uyan **tek** tur `tarayici-kabul-k236` —
motor **minimax-m3**, 20 Ağu 14:09Z, 4.531.779 girdi, 181 sn, **rc=0**.

## 3) E3 — KOTA SAYACININ SAHİBİ (çelişki çözüldü)

`kota-gecmis.tsv` kolonları `kota-olcum.py::append_history()`'den birebir:

```
utc \t seven_total \t ana \t agent \t opus_share \t NA
```

- Kaynak: `~/.claude/projects/**/*.jsonl` → **CLAUDE'un kendi transcript'leri**.
  `model_group()` yalnız opus/sonnet/haiku/diğer kovalarını tanır.
  **MiniMax da kimi de bu sayaçta YOK.**
- Pencere: **kayan 7 GÜN** (aylık değil).
- Bugünkü satır doğru okunuşu: toplam **19.652.883.980** = ANA **15.331.909.813**
  + ALT_AJAN **4.320.974.167** (tam toplanıyor ✓), son alan **%56,19 opus payı**.
- Posta kutusundaki "toplam/kullanılan/kalan/%" okuması hatalı; "+2,65B/gün" farkı
  **2. kolondan** (ANA) türetilmiş: 15.331.909.813 − 12.679.670.834 = 2.652.238.979.
  Gerçek toplam farkı **+919.231.156**.

→ **Bu sayaç m3'ün 5,1B/ay tavanıyla kıyaslanamaz.** Farklı sağlayıcı, farklı pencere.

## 4) E1 — MOTOR BAŞINA TÜKETİM (`baglam-olcum.tsv`, 20 Ağu ~14:15Z anlık görüntü)

🔴 Dosyanın **%56'sı test fikstürü** (`ev=^ev[0-9]*$` veya `etiket=vaka-*`):
5000 satırın **2786'sı fikstür**, **2214'ü gerçek**. Ham dosya üzerinden alınan
her toplam yarıdan fazlası gürültüdür. Aşağısı **GERCEK** kovasıdır.
(Dosya CANLI: iki koşum arasında 2213→2214 büyüdü.)

| | minimax-m3 | kimi |
|---|---:|---:|
| tur sayısı | 1.188 | 1.025 |
| `toplam_girdi` (tüm kayıt = son 7 gün) | **4.190.259.305** | **523.307.488** |
| bugün (20 Ağu) | 353.390.395 | 125.825.795 |
| tur başına ORTALAMA | 3.527.154 | 510.543 |
| tur başına MEDYAN | 262.503 | 500 |
| rc=0 / rc≠0 | 1.159 / 29 | 998 / 27 |
| **düşen turlarda boşa yanan girdi** | **554.702.700** | **157.753.684** |
| `butce_vuruldu` tur sayısı | 19 | 1 |

**En çok yakan etiketler (GERCEK):** ① m3 `ci-nobeti` 129 tur / **380.319.979**
② m3 `skodatv-dilim3` 1 tur / 173.621.246 ③ m3 `dilim1` 11 tur / 133.586.761
④ m3 `seat-d2-2-ekle-m3` 1 tur / 103.861.015 ⑤ **kimi** `seat-d2-2-ekle` 2 tur /
67.725.190 (rc≠0 ×2) ⑪ **kimi** `citroen-d5-1-ekle` 1 tur / 43.240.416 (rc≠0).
→ kimi'nin kotasını yiyen sınıf **toplu ürün ekleme dilimleri**, nöbet değil.

### 🔴 ÇELİŞKİ — çözülmedi, adıyla yazılıyor
m3 yerel kayıtta **7 günde 4,19B girdi** gösteriyor; Max tavanı **5,1B/AY**.
Yani yerel sayım aylık tavanı ~3,5× aşmalıydı — ama m3 **hiç 403 almadı, hiç
karantinaya girmedi**. Dolayısıyla `toplam_girdi` (her turda yeniden gönderilen
bağlam + cache okuma dahil ham sayım) MiniMax'ın **faturaladığı metrik DEĞİLDİR**.
Gerçek tüketim yalnız **MiniMax panelinden** okunabilir → E1 bu kaynaktan **ÖLÇÜLEMEDİ**.

## 5) KOTA / 403 SÜTUNU — bugünkü canlı hal

| | minimax-m3 | kimi |
|---|---:|---:|
| bugün karantina (`KOTA_KARANTINA`, ömür 6s) | **0** | **11** |
| `KARANTINA_KARAR ... yazildi=evet` | 0 | 11/11 |
| `isci.log` 403 "usage limit for this billing cycle" | 0 | **21** |
| bugünkü tur sayısı (`isci.log`, 113 turun) | 71 | 42 |

- `.motor-karantina` içeriği **`kimi 1787231383`** = 20 Ağu **13:09:43Z**, ömür 6s
  → **kimi şu anda karantinada.**
- 403 metni birebir: *"You've reached your usage limit for this billing cycle."*
  Bu **kota tükenmesidir**, yetenek kusuru değil.
- `kimi-nabiz.log` 17→20 Ağu **her satırda SAGLIK=KIRMIZI**, iki ayrı kip:
  17–18 Ağu `http=403 permission_error`; 18 Ağu 18:10'dan bugüne **`http=200` ama
  `icerik=bos`** (out_tok 29–36). Yani kimi ucu **200 dönüp boş içerik üretiyor** —
  naif bir nabız bunu YEŞİL sayardı.
- `isci-motor-uc.zsh` kayıtlı ölçüm: kimi `k3` kolu ile *"günlük 25-29M girdi, aylık
  kredi 2 günde bitti"* → varsayılan ucuz kola (`kimi-for-coding`) düşürülmüş.
  **Tarayıcılı turlarda kimi hâlâ `k3`** (pahalı kol) kullanıyor; m3'te böyle bir ayrım yok.

## 6) E2 — EŞZAMANLILIK TEPE DEĞERİ

Süpürme (sweep) yöntemi, `utc` + `sure` aralıklarından; `sure` yok/0 olan 1.298 tur atlandı.

| pencere | tüm motorlar | kimi | minimax-m3 |
|---|---:|---:|---:|
| bugün (20 Ağu) — **organik** | **6** | **6** | **5** |
| tüm kayıt, GERCEK kovası | 9 ⚠️ | 9 ⚠️ | 6 |

- Bugünkü tepe **6**, damga 00:46:43Z, etiketler gerçek iş:
  `kabul-p1-ilk-ekran · onarim-k214-regresyon · kabul-p1-tarayici · seat-d2-2-ekle ·
  kabul-fantom-purchase · onarim-sizinti-olcum`.
- ⚠️ "9" değeri **fikstür bulaşıklı** (`sisme-vaka-D-buyuk/E-kucuk`): fikstür filtresi
  `vaka-` önekini arıyor, bu etiketler `sisme-vaka-…` olduğu için kaçtı. Organik tepe **6**.
- `HEPSI` kovasındaki 113 değeri tamamen sentetik (`etiket=isci` yük testi), iş yükü değil.

→ Bugünkü gerçek tepe **6**, Max'ın 4–5 eşzamanlılık bandının **ÜSTÜNDE**,
Ultra'nın 6–7 bandının içinde.

## 7) PANEL HİPOTEZİ — frekans ekseninde çürük, üstelik etiketler kolu hiç açmamış

`isci.sh` tarayıcı MCP'sini **yalnız `panel*`/`tarayici*` ile BAŞLAYAN** etikete verir.
Tüm `baglam-olcum.tsv`'de bu önek kuralına uyan **tek satır** var: `tarayici-kabul-k236`.
`kabul-p1-tarayici` / `kabul-p1-tarayici-m3` etiketleri `kabul` ile başlıyor →
**bu turlar tarayıcıyı HİÇ almadı**; 12,2M girdileri panel sürmenin maliyeti değildir.

## 8) ÖLÇÜLEMEDİ (sebebiyle)

1. **m3'ün gerçek faturalanan aylık tüketimi (E1).** `isci.log`'da token alanı **yok**
   (`butce=` bir tavan, tüketim değil); `baglam-olcum.tsv`'deki `toplam_girdi` ham
   bağlam sayımı, faturalanan metrik değil (§4 çelişkisi). Kaynak: **MiniMax paneli**.
2. **kimi'nin bugünkü yetkinliği.** Motor 13:09:43Z'den beri karantinada + nabız
   17 Ağu'dan beri KIRMIZI → bugün koşulacak her kimi turu kota koluna düşerdi.
   Yetkinlik verisi 15 Ağu'da motor sağlıklıyken alınmıştır.
3. **`isci.log`'dan gerçek eşzamanlılık.** `BITIS` satırı motor/etiket taşımıyor;
   `collect_worker_runs()` örtüşen turda `pending`'i eziyor → örtüşen turlar sessizce
   DÜŞÜYOR. E2 bu yüzden `isci.log`'dan değil `baglam-olcum.tsv`'den türetildi.

## 9) TEK CÜMLELİK HAM BULGU

Altı görev sınıfının hiçbirinde iki motor arasında **yetenek uçurumu yok** (m3 16/18,
kimi 18/18; m3 ~1,4× hızlı, kimi g5/g6'da 2 hücre daha isabetli) — ayrışma yetenekte
değil **süreklilikte**: kimi bugün 11 kez karantinaya girdi, 21 kez 403 aldı ve şu an
karantinada, m3 ise 0 kez; buna karşılık m3 aynı 7 günde kimi'nin **8 katı** ham girdi
işledi (4,19B ↔ 0,52B) ve bugünkü eşzamanlılık tepesi **6**, Max'ın 4–5 bandının üstünde.

---
İmza: **KraL-Yetkinlik** · ölçüm anı 20 Ağu 2026 ~14:15Z · merge YAPILMADI
