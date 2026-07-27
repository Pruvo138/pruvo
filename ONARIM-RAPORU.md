# ONARIM RAPORU — konfigür nöbetçisi yanlış-pozitifleri kapatıldı

**Yargı: 🟢 MERGE EDİLEBİLİR.** Çürütücünün merge blokeri olarak saydığı **5 yanlış-pozitifin
5'i + 1 miras = 6 tanesi KAPANDI**, **yakalama gücü kaybı 0** (19/19 mutant kırmızı kaldı),
symlink kaçağı **TAM kapatıldı** (aynada symlink 0 · kaynak ağaç **313/313 sha256 aynı** ·
**80/80 koşum** temiz), 25 rutin-düzenleme senaryosu **kalıcı fikstür** oldu.
Harness: **60 PASS / 0 FAIL**, süre 29,1 s. Nöbetçi tek başına: **çıkış 0**.

Dal: `worktree-agent-a7e6d21e35b6f583e`. `origin/worktree-agent-a59ab926853d492c7` (`e90ac33d`)
**çakışmasız merge edildi** (ort, 2 dosya). Diff tabanı **merge-base `7b53c7fd`** (`git merge-base`
ile teyit; ana hat bu arada Renault partisiyle 12 349 → **12 409**'a ilerlemişti). Değişen dosya
merge-base'e göre **yalnız 2**: `tools/konfigur-test.py` (+202/-6) · `tools/konfigur-nobet-mutasyon.py`
(+841, yeni). Benim onarım deltam dal ucuna göre: nöbetçi **+67**, harness **+701/-127**.

---

## 1. ANA ONARIM — mimar kararı birebir uygulandı (2 satır)

`tools/konfigur-test.py` (e) bölümü:

```python
# (a) sınıf/öznitelik/metin ÇİVİSİ çıkarıldı, BÖLGE kaldı:
kontrol('href="/malzeme-rehberi/"' in g,
        "'Malzeme Rehberi' linki ANA GÖVDEDE kalır (footer nav kopyası SAYILMAZ)")
# (b) <p> etiketi + tam sınıf dizgesi yerine SINIF-ADI temelli blok:
wa_blok = blok(g, r'<(p|div)\b[^>]*class="[^"]*malzeme-not[^"]*"[^>]*>.*?</\1>')
```

Kod yorumuna **ÇİVİ YASAĞI** ve ölçülen bölge haritası yazıldı: bir çivinin yakalama katkısı
ölçülmeden eklenmesi yasak; katkı 0 + yanlış-pozitif > 0 olan çivi çıkarılır (emsal
`cta_varlik_kontrol`). `kontrol()` çağrı sayısı DEĞİŞMEDİ → nöbetçinin iddia sayısı aynı (✅ 165).

### ÖNCE / SONRA (kendi ölçümüm, üç nöbetçi sürümü aynı fikstür kümesinde)

| Nöbetçi sürümü | 25 fikstürde KIRMIZI | temiz |
|---|---:|---:|
| merge-base = ana hat (`7b53c7fd`) | **4** | 21 |
| dal ucu, onarım ÖNCESİ (`e90ac33d`) | **11** | 14 |
| **dal, onarım SONRASI (bu iş)** | **5** | **20** |

**KAPANAN yanlış-pozitif: 6** → R02, R04, R05, R18b, R25b (**dalın getirdiği**) + R03 (**miras**).
**Yeni açılan: 0.** Kalan 5 kırmızı = 2 🟠 beyan edilmiş borç (R15, R22) + 3 🔴 miras (R06, R07, R11).

---

## 2. SYMLINK TEHLİKESİ — TAM kapatıldı

`ayna_kur()` artık **hiçbir yerde symlink kurmuyor**: tools/ dosyaları `copy2`, kök dosyaları
`copy2` (symlink hedefi çözülerek; kırık symlink aynaya HİÇ taşınmaz), kök dizinleri
`copytree(symlinks=False)`. Mutasyon anahtarları artık depo-köküne de yazabiliyor
(`urunler.json`, `index.html` gibi) — kopya olduğu için güvenli.

**Kabul ölçümü (harness F bölümü, her koşumda):**

| Ölçüm | Sonuç |
|---|---|
| Aynada symlink sayısı | **0** (kaynağa giden yol fiziksel olarak kapalı) |
| Aynadaki **her** dosyaya append + **her** dizine yeni dosya | **300 dosya + 20 dizin** yazıldı |
| Sonra kaynak ağaç sha256 | **313/313 dosya AYNI** (değişen: yok) |
| Her koşumdan SONRA dokunulmazlık ölçümü | **80/80 koşum temiz**, kirli 0 |
| Nöbetçi doğrudan checkout'ta koşuldu (CI koşulu) | `git status` KİRLENMEDİ |

Ölçüm maliyeti ölçüldü: tam ağaç sha256 (11 MB `urunler.json` dahil) **~0,02 s** → her koşumdan
sonra çalıştırılabiliyor. Bozulursa harness ANINDA kırmızı yanıyor (`dokunulmazlik_olc`).

⚠️ `__pycache__` parmak izinden DIŞLANDI (gitignore'lu türetilmiş artefakt; harness'ın E bölümü
kendi iç-süreç import'uyla onu tazeliyordu → her koşum sahte kırmızı). İddiayı zayıflatmıyor:
"ayna kaynağa yazamaz"ın TAŞIYICISI **aynada symlink = 0** ölçümü; sha256 onun teyidi. Ayrıca E
bölümü artık `sys.dont_write_bytecode` ile hiç `.pyc` yazmıyor (yani dışlama olmasa da temiz).

---

## 3. 25 SENARYO KALICI FİKSTÜR OLDU (harness C bölümü)

Her fikstür **BEYAN EDİLMİŞ beklentiyle** gelir ve **HER İKİ YÖNDE** assert edilir: beklenti
YEŞİL'ken kırmızı yanmak FAIL; beklenti BORÇ/MİRAS'ken **yeşile dönmek de FAIL** (mesaj:
"fikstürü YESIL sınıfına çek + nöbetçideki `ne_olculmedi()` beyanını güncelle"). Sessiz drift
böyle kapanır. Beklenti-KIRMIZI fikstürlerde ayrıca **işaret şartı** var (kırmızı satır doğru
jetonu içermeli) — kaza eseri kırmızı kabul edilmiyor. Eski 6 maddelik `FP-*` listesi bu tabloya
**taşındı** (ikinci kopya bırakılmadı).

Her fikstür **HEM güncel HEM merge-base nöbetçisiyle** koşuyor → "dalın getirdiği" ile "miras"
otomatik ayrışıyor. Ana hatta iki nöbetçi bayt aynı olacağı için BASE kolonu **⚪ olarak düşer**
(referans totolojisi, c4'le aynı sözleşme); kalıcı koruma DAL kolonudur.

| # | sınıf | BASE (main) | DAL-ÖNCE | **DAL-SONRA** | rutin düzenleme |
|---|---|---|---|---|---|
| R01 | ✅ | YEŞİL | YEŞİL | **YEŞİL** | CSS değer değişimi (`.cart-btn:hover` rengi) |
| R02 | ✅ | YEŞİL | KIRMIZI | **YEŞİL** | CSS sınıf ADI değişimi (`malzeme-link`→`malzeme-baglanti`) |
| R03 | ✅ | KIRMIZI | KIRMIZI | **YEŞİL** | gövde notuna ikinci CSS sınıfı (miras da kapandı) |
| R04 | ✅ | YEŞİL | KIRMIZI | **YEŞİL** | gövde linkine ikinci CSS sınıfı |
| R05 | ✅ | YEŞİL | KIRMIZI | **YEŞİL** | HTML öznitelik SIRASI (href önce) |
| R06 | 🔴 | KIRMIZI | KIRMIZI | KIRMIZI | gömülü JS bayrağı config objesine (script-harici refaktör) |
| R07 | 🔴 | KIRMIZI | KIRMIZI | KIRMIZI | JS minify: bayraktaki boşluk kaldırıldı |
| R08 | ✅ | YEŞİL | YEŞİL | **YEŞİL** | HTML minify: `<main>`–`<nav>` arası boşluk |
| R09 | ✅ | YEŞİL | YEŞİL | **YEŞİL** | şablon girintisi (crumbs bloğu) |
| R10 | ✅ | YEŞİL | YEŞİL | **YEŞİL** | footer nav linki + metni değişti |
| R11 | 🔴 | KIRMIZI | KIRMIZI | KIRMIZI | footer nav'a `.cart-btn` sınıflı buton |
| R12 | ✅ | YEŞİL | YEŞİL | **YEŞİL** | katalogda yeni ürün (sentetik `urunler.json` başına) |
| R13 | ✅ | YEŞİL | YEŞİL | **YEŞİL** | katalogda Marin tamamen boşaltıldı |
| R14 | ✅ | YEŞİL | YEŞİL | **YEŞİL** | `CATEGORIES`'e yeni kategori |
| R15 | 🟠 | YEŞİL | KIRMIZI | KIRMIZI | **kategori yeniden adlandırma** (beyan edilmiş borç) |
| R16b | ✅ | YEŞİL | YEŞİL | **YEŞİL** | bölüm sırası: gövde linki WA notunun önüne |
| R17 | ✅ | YEŞİL | YEŞİL | **YEŞİL** | head'e yeni OG/product meta |
| R18b | ✅ | YEŞİL | KIRMIZI | **YEŞİL** | gövde link METNİ yeniden yazıldı |
| R19 | ✅ | YEŞİL | YEŞİL | **YEŞİL** | gövde başlığı yeniden yazıldı |
| R20 | ✅ | YEŞİL | YEŞİL | **YEŞİL** | iyzico ödeme bandı (`sayfalar.py PAY_BAND_HTML`) |
| R21 | ✅ | YEŞİL | YEŞİL | **YEŞİL** | `<main>` etiketine sınıf eklendi |
| R22 | 🟠 | YEŞİL | KIRMIZI | KIRMIZI | **`<main>`→`<div id="main">`** (tasarımca fail-closed) |
| R23 | ✅ | YEŞİL | YEŞİL | **YEŞİL** | yeni harici `<script src>` |
| R24b | ✅ | YEŞİL | YEŞİL | **YEŞİL** | `filamentler.json`'a yeni satışta malzeme |
| R25b | ✅ | YEŞİL | KIRMIZI | **YEŞİL** | gövde WA notu `<p>`→`<div>` |

**20 ✅ temiz · 2 🟠 beyan edilmiş borç · 3 🔴 miras = 25.**

**R12/R13 notu (dürüstlük):** ayna `urunler.json`'u KASITLA taşımaz (D bölümünün katalog-bağımsızlık
İCRA kanıtı buna dayanır). Bu iki fikstür bağışıklığı TERSTEN ölçer: aynaya **sentetik** (3-4 ürünlük)
katalog konur ve mutasyon ona uygulanır. Gerçek 12 409'luk katalog kullanılmaz — hem maliyet hem
veri-çapası yasağı. Yani "12 409 ürünle koştu" DEMİYORUM; "ürün verisi VARSA ve değişirse kapı
kımıldamıyor" diyorum.

### Beyan edilmiş kör noktalar artık nöbetçinin KENDİ çıktısında
`konfigur-test.py` içine `ne_olculmedi()` eklendi (emsal `tools/ege-kabiliyet-kapisi.py`) ve **her
koşumda** basılıyor — yeşilde de: (1) 🟠 kategori yeniden adlandırma = elle liste, artık **5. güncelleme
yeri**; (2) 🟠 `<main>` kaybı = fail-closed, kusur yalnız teşhis metninde; (3) 🔴 bu bölüm ürün
verisini ölçmez; (4) 🔴 c2'nin `KART_SECIM = true` / `class="cart-btn"` dizgeleri hâlâ biçim çivisi —
üç refaktör bu kapıyı yanlış-pozitif kırmızıya düşürür (miras, ayrı iş). Metin bilerek **✅/❌/⚪
işareti içermez** (harness çıktıyı bu işaretlerle sayıyor).

---

## 4. MİRAS YANLIŞ-POZİTİFLER — kapsam BÜYÜTÜLMEDİ + istenen ölçüm

Bedava kapanan alındı (R03). Kalan **3** (R06 script-harici refaktör · R07 JS minify · R11 footer
`.cart-btn`) **DOKUNULMADI** — her biri ayrı çivi-başına yakalama-katkısı ölçümü ister.

**🔴 İSTENEN ÖLÇÜM — evet, bugün main'de rutin bir refaktör yayını DURDURUYOR** (harness G bölümü,
kanıt):

| Kanıt | Ölçüm |
|---|---|
| `deploy.yml` adımı | `Konfigur (dekor konfigurator) kabul testi`, `continue-on-error=False` → **BLOKLAYICI** |
| main nöbetçisi + R06 (bayrak config objesine) | **çıkış 1**, 8 kırmızı satır (`kayıp: ['KART_SECIM = false']`) |
| main nöbetçisi + R07 (JS minify) | **çıkış 1**, 8 kırmızı satır |
| main nöbetçisi + R11 (footer `.cart-btn`) | **çıkış 1**, 5 kırmızı satır (`sızan: ['class="cart-btn"']`) |

Yani `build.py`'de `var KART_SECIM = {kart_secim};` satırını bir config objesine taşıyan ya da
footer'a `.cart-btn` sınıflı bir buton ekleyen **bugünkü main'de TÜM SİTE yayını durur**. Bu bölüm
harness'ta FAIL üretmez, **BULGU** basar (mimar ayrı iş açacak).

---

## KABUL KRİTERLERİ — K1..K8, hepsi sayıyla

| # | Kriter | Ölçüm | Sonuç |
|---|---|---|---|
| **K1** | dalın getirdiği kırmızı = 0 | 25 fikstür: DAL-ÖNCE 11 kırmızı → **DAL-SONRA 5**; BASE-yeşil-DAL-kırmızı fikstür **0**; kapanan **6** (R02·R04·R05·R18b·R25b + miras R03); yeni açılan **0** | 🟢 |
| **K2** | kategori matrisi 14/14, adıyla ≥12/14, nöbetsiz 0 | **14/14 KIRMIZI** (evren = `CATEGORIES`+`NAV_GIZLI`, sabit sayı yok; Jeneratör TERS mutantla) · **adıyla işaret eden 12/14** (Ev/Kamera sayfa-sınıfı adıyla işaret ediyor, miras teşhis eksiği) · **nöbetsiz kategori 0** | 🟢 |
| **K3** | bölge fikstürleri 4/4 KIRMIZI | footer ✔ · çivili footer ✔ · head ✔ · `<main>` içi `<script>` ✔ → **4/4** (+ OLU-WA-NOT ✔) | 🟢 |
| **K4** | 3 ölü-iddia mutantı KIRMIZI, kayıp 0 | OLU-REHBER · OLU-REHBER+çivili footer · OLU-WA-NOT → onarımlı nöbetçide **3/3 KIRMIZI**, merge-base'de 3/3 YEŞİL (ölü). **Yakalama gücü kaybı: 0** — 19 kırmızı mutantın (14 kategori + 5 bölge/ölü) **19'u önce de sonra da KIRMIZI** | 🟢 |
| **K5** | kaynak ağaç N/N sha256 aynı | **313/313** dosya aynı (300 dosya + 20 dizin yazma denemesinden sonra) · aynada symlink **0** · **80/80** koşum temiz | 🟢 |
| **K6** | veri çapası 0 isabet | `konfigur-test.py`'de eklenen **196 satır → 0 isabet** (5 desen). Harness'ta 20 isabet var, **hepsi elle denetlendi**: çıkış kodu karşılaştırması (`rc == 1`, `!= 0`), dizge kırpma (`[:100]`), `subprocess timeout=300`, `len(tekil) == 1` (hermetiklik) → **ürün/kategori sayısı, SHA, tarih, ürün-id çapası 0**. Katalog 12 409'a çıkmışken taban YEŞİL | 🟢 |
| **K7** | determinizm 10/10 · süre · `deploy.yml` 0 hunk | **10/10** tek parmak izi `(çıkış 0, ✅ 165, ❌ 0, ⚪ 3)`. Nöbetçi süre medyanı (5 koşum): main **0,242 s** → onarım öncesi 0,243 → **onarım sonrası 0,249 s** (+7 ms). `deploy.yml` **0 hunk / 0 diff satırı**, `continue-on-error` YOK | 🟢 |
| **K8** | `ci-kapsam-test.py` çıkış 0 | **YEŞİL** — keşfedilen 97 · deploy'da koşulan 27 · muaf 70. Harness (`konfigur-nobet-mutasyon.py`) enumerate EDİLMİYOR (ad deseni uymuyor) → kapsam İDDİA ETMİYOR, CI'ya da alınmadı (mimar kararı) | 🟢 |

Harness toplamı: **60 PASS / 0 FAIL**, çıkış 0, **29,1 s** (80 nöbetçi koşumu; 8,7 s → 29,1 s
artışın sebebi: 25 fikstür × 2 nöbetçi + 4 ek kategori + 2 ek bölge fikstürü + her koşumda tam
ağaç sha256). CI'da koşmadığı için bu bedel yayın süresine YANSIMIYOR.

---

## ÇÜRÜTÜCÜNÜN SAYILARIYLA KARŞILAŞTIRMA

| Çürütücünün ölçtüğü | Benim ölçümüm | Uyum |
|---|---|---|
| Onarım 11/11 senaryo | 19/19 mutant kırmızı + 20/20 temiz-beklenti yeşil (daha geniş küme) | ✅ uyuşuyor |
| 6 yanlış-pozitif kapanır | **6** (R02·R04·R05·R18b·R25b + miras R03) — birebir aynı liste | ✅ uyuşuyor |
| 3 mutant kırmızı kalır | **3/3** kırmızı (OLU-REHBER · çivili footer · OLU-WA) | ✅ uyuşuyor |
| Yakalama gücü kaybı 0 | **0** (19/19) | ✅ uyuşuyor |
| Kategori matrisi 14/14, adıyla 12/14 | **14/14 · 12/14** | ✅ uyuşuyor |
| Bölge fikstürleri 4/4 | **4/4** | ✅ uyuşuyor |
| Süre 0,250 → 0,252 s | 0,242 → **0,249 s** (+7 ms) | ⚠️ mertebe ve yön aynı, mutlak değer makineye/koşuma bağlı; benim ölçümüm ayna kurulumunu HARİÇ tutuyor |
| "15 temiz / 7 kırmızı / 4 miras" (§1 toplam satırı) | **14 temiz / 7 dalın-yenisi / 4 miras = 25** | ⚠️ **AYRIŞIYOR**: çürütücünün toplam satırı 15+7+4=**26** veriyor, oysa tablosunda **25** satır var. Verdict kolonunu tek tek saydım: temiz **14** (R01·R08·R09·R10·R12·R13·R14·R16b·R17·R19·R20·R21·R23·R24b). Yani "temiz" **14**, aritmetik +1 kaymış. Görev metnindeki "24 senaryo" da tabloda **25** satır. Kırmızı sayısı (7 yeni + 4 miras = 11) **birebir doğrulandı** |
| Kök DOSYALAR hâlâ symlink (yarım onarım) | Doğrulandı ve KAPATILDI: artık aynada symlink 0, 313/313 sha256 | ✅ uyuşuyor |
| `deploy.yml` 0 hunk, bloklayıcı | **0 hunk**, `continue-on-error=False` | ✅ uyuşuyor |
| Harness'ın ⚪ parmak izi `⚪ 1` | benim ölçümüm `⚪ 3` | ⚠️ sayma kuralı farkı: TEK ÖLÇÜLEMEDİ kalemi çıktıda 3 kez "⚪" basıyor (`olculemedi()` satırı + özet başlığı + özet maddesi). Kalem sayısı ikisinde de **1** (c4 bayt-eşitliği). ✅ 165 ise işçinin sayısıyla birebir |

---

## SINIR / YASAK BEYANI

D1 · R2 · `urunler.json` · `.urun-kaynaklari.json` **YAZILMADI** (urunler.json yalnız sha256'landı;
mutasyonlar SENTETİK katalogla aynada). Deploy YOK · `wrangler` YOK · secret YOK · CI tetiklenmedi.
Yasak dosyalara (`tools/mimar-*.py`, `tools/yedekle*.py`, `tools/durum-yedek-test.py`,
`tools/parite-*.js`, `tools/filament-test.py`, `.github/workflows/deploy.yml`) **yalnız okuma**
uygulandı — `deploy.yml` 0 hunk ile kanıtlı. Başka ajanların worktree'lerine yazılmadı
(`agent-a393d63542120bffe` yalnız OKUNDU), yabancı dal/untracked'e dokunulmadı,
`worktree remove/prune` çağrılmadı, `main`'e merge edilmedi, `push --force`/`--no-verify` /
`git stash` kullanılmadı. Çalışma ağacı temiz (yalnız bu işin 2 dosyası + bu rapor).
`enjeksiyon-kapisi.py` / `build.py` LOKALDE ÇALIŞTIRILMADI; nöbetçi checkout'ta bir kez koşuldu ve
`git status` KİRLENMEDİ.

---

## KENDİ İDDİAM: **MERGE EDİLEBİLİR** 🟢

Sayılar çürütücünün ölçtükleriyle **uyuşuyor**: 6 yanlış-pozitif kapandı (aynı liste), 3 ölü-iddia
mutantı kırmızı kaldı, yakalama gücü kaybı 0, kategori matrisi 14/14 · 12/14, bölge 4/4,
`deploy.yml` 0 hunk. **İki sayıda ayrışma var, ikisi de sayma/aritmetik kaynaklı, yönü değiştirmiyor:**
(1) çürütücünün "15 temiz" toplamı aritmetik olarak +1 kaymış — tablo satırları **25**, temiz **14**;
(2) ⚪ parmak izi 1 vs 3 = tek kalemin çıktıda 3 kez basılması. Süre farkı (0,252 vs 0,249 s)
makine/kapsam farkı.

**Açık bırakılan (mimarın ayrı iş açması için):** 3 miras yanlış-pozitif (R06 · R07 · R11) — bugün
main'de bu rutin refaktörlerden herhangi biri **TÜM SİTE yayınını durduruyor** (ölçüldü, §4).
Nöbetçi bunu artık kendi yeşil çıktısında **ilan ediyor**.
