# PAKET K168a — YARIM KALAN İŞİ BİTİR (bütçe tavanında düştü, iş DURUYOR)

Mimar: KraL · 18 Ağu 2026 · hedef kat: İŞÇİ. `tools/paket-k168-recete-yasak-sinifi.md`'nin
devamı; **sıfırdan başlama.**

## 1. DURUM (mimar ölçtü)

Önceki tur `Error: Exceeded USD budget (10)` ile düştü. Paket iki kolu (H1 + H2) tek dilime
sığmadı — **bu benim dilimleme hatam**, işçinin başarısızlığı değil. İş KAYBOLMADI:

```
worktree : /Users/okan/dev/pruvo/.claude/worktrees/k168-recete-yasak
dal      : kral/k168-recete-yasak   (main dışı commit YOK — her şey commit'siz)
 M tools/mimar-icra-kapisi.py        ← H1 YAPILMIŞ (aşağıda teyit edildi)
 ?? tools/recete-kapisi.py           ← H2 gövdesi YAZILMIŞ (24 KB, kendini-test + 3 mutant)
 M tools/marka-invaryant-taban.json  ← 🔴 KAPSAM DIŞI, 1 satır — GERİ ALINACAK
```

**H1 mimarca incelendi ve spec'e UYGUN:** `_py_izinli`'ye üçüncü komut eklenmiş; tam eşitlik,
3 argüman, **hiçbir argüman `-` ile başlayamaz** (bayrak yasağı), iki konum argümanı kanonik
`DEVAM.md` / `DEVAM-ARSIV.md` olmak zorunda. Kapsam bilerek dar. Bu koda DOKUNMA, yalnız
kabulünü koştur.

## 2. ADIM 0 — kapsam dışı değişikliği geri al

```
git -C /Users/okan/dev/pruvo/.claude/worktrees/k168-recete-yasak checkout -- tools/marka-invaryant-taban.json
git -C /Users/okan/dev/pruvo/.claude/worktrees/k168-recete-yasak status --short
```
`marka-invaryant-taban.json` bu paketin kapsamında DEĞİL; büyük olasılıkla bir kapı koşumunun
yan etkisi olarak yeniden yazıldı. Geri alındığı `status` çıktısıyla kanıtlanır.
⚠️ Başka bir kapsam dışı dosya görürsen **geri alma, rapora yaz ve sor.**

## 3. ADIM 1 — kabul (bu dilimin ASIL işi)

Worktree'nin İÇİNDEN, `pwd` çıktısı rapora:

```
python3 tools/recete-kapisi.py --kendini-test
python3 tools/mimar-kilit-test.py
```

Beklenen son satır + rc=0:
```
RECETE=<n> REDDEDILEN=0 EVREN=<n> MUTANT=3/3 KONTROL=2/2
```

* `REDDEDILEN=0` → reçete edilen her çare mimarca koşulabilir durumda.
* `EVREN=0` **YEŞİL DEĞİLDİR** → rc=2 (`OLCULEMEDI`). Gövde bunu zaten yazmış; teyit et.
* Mutantlar: **M1** H1'i geri al → `REDDEDILEN>=1` · **M2** evren boş → rc=2 ·
  **M3** H1'i serbest-biçim argümana genişlet → RED.
* Kontroller: **K1** `durum.py` + `d1-sync.py --durum` AYNEN serbest kalır ·
  **K2** `wc`/`sort`/`head`/serbest `python3` AYNEN yasak kalır. H1 delik AÇMAMALI.

Kırmızıysa: mutantı daralt, **vakayı gevşetme** ([[test-hatali-davranisi-kutsar]]).

## 4. ADIM 2 — CI kablosu (muafiyet YOK)

`tools/recete-kapisi.py` **hijyen şeridine** (`.github/workflows/nobet.yml`, SERİT B) kendi
adımıyla bağlanır: `python3 tools/recete-kapisi.py`. Kırmızısı müşteriye para ödetmez / veri
sızdırmaz / siteyi durdurmaz → bloklayıcı şerit DEĞİL.

Sonra:
```
python3 tools/ci-kapsam-test.py
```
rc=0 **ve** çıktıda `tools/recete-kapisi.py` **muaf listesinde GÖRÜNMEZ** (davranışsal
kontrol; `grep -c` ile jeton adı sayma YOK).

⚠️ `nobet.yml`e başka oturumlar dokunuyor. Düzenlemeden hemen önce:
```
git -C /Users/okan/dev/pruvo log --oneline -3 -- .github/workflows/nobet.yml
```
Beklenmedik yeni dokunuş varsa DUR ve rapora yaz.

🔴 **Kapının taşınabilirliği (③f dersi):** `recete-kapisi.py` hedefini sabit mutlak yoldan
(`/Users/okan/dev/pruvo`) ALMAMALI — CI koşucusunda o yol YOKTUR. `__file__` konumundan
türetsin. Bugün ölçüldü: sabit kök yüzünden aynı dal üç turda üç farklı sayı verdi
([[kapi-sabit-kok-yanlis-agaci-olcer]]). Gövdede sabit kök varsa **düzelt** ve raporda göster.

## 5. ADIM 3 — commit (worktree'de)

Yalnız iki dosya: `tools/mimar-icra-kapisi.py` · `tools/recete-kapisi.py`
(+ `.github/workflows/nobet.yml`). Başka dosya commit'e GİRMEZ.
Merge'ü İZOLE OLMAYAN ayrı bir tur yapacak; **bu turda merge YOK.**

## 6. BÜTÇE DİSİPLİNİ (bu dilimin var olma sebebi)

* Tavan ~30-40 tur. Alt ajan / paralel görev AÇMA. Tarayıcı GEREKMEZ.
* **Mutasyon koşumlarını raporu yazdıktan SONRA yapma — ilerledikçe rapora yaz.** Önceki tur
  bütçeyi mutasyon turlarında yaktı ve rapor yazamadan düştü.
* Bütçenin yarısına gelindiğinde: elindekini commit et, raporu kapat, kalanı sonraki dilime
  bırak. **Yarım ama kayıtlı**, tam ama kayıpsızdan iyidir.

## 7. SINIRLAR

* `defter-rotasyon.py`'nin KENDİ gövdesine DOKUNULMAZ (mutasyonla yeşil, 7/7).
* Defter kota tavanı (130) DEĞİŞTİRİLMEZ.
* `mimar-icra-kapisi.py`'de H1 dışında hiçbir kural değişmez.
* **DOKUNMA:** `urunler.json` · `crontab` · `DEVAM.md` · `~/.claude/cron/` ·
  `k166b-yayin-sinyali` worktree'si.
