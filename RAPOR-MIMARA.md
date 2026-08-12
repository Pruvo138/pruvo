# RAPOR — YAYIN DURDU: model evreni ayrışması (`47b6734d`) + aksan ekseni

**Durum: TEŞHİS TAM, ONARIM YAZILMADI (YARIM).** Devir geldiği için tespit commit'lendi.
Ölçümlerin hepsi bu dalda, ana checkout'a dokunulmadı.

Ağaç: `/Users/okan/dev/pruvo/.claude/worktrees/agent-a3251270b98f7b14b`
HEAD = `origin/main` = `dd48c787` (behind 0). `47b6734d` ata: EVET.

---

## 1. İKİ KAPI DA YERELDE KIRMIZI — TEK KOŞUMDA ÖLÇÜLDÜ

| kapı | komut | rc | düşen iddia |
|---|---|---|---|
| KAPI1 | `python3 tools/model-kanon-d1-test.py` | **1** | `B7` (45 geçti / 1 kaldı) |
| KAPI2 | `python3 tools/build.py --sadece-taban` + `--sadece-ozet` + `node tools/faz3-bayrak.js` | **1** | TEST 7 → `yedek sonuclar gercekten sorguyla eslesiyor` (49 geçti / 1 kaldı) |

Ön koşul kolları yeşil: `--sadece-taban` rc=0, `--sadece-ozet` rc=0. Yani KAPI2 rc=1
**iddia düşmesidir**, ÖLÇÜLEMEDİ değil.

---

## 2. 🔴 İKİ KAPININ SAPMASI **AYNI KÜMEDEN GELMİYOR** — İKİ AYRI KÖK

Spec bunu soruyordu. Cevap: **HAYIR, iki ayrı sınıf.**

* KAPI1 = **model evreni ikiz tanımı** (`47b6734d` kaynaklı, REGRESYON).
* KAPI2 = **aksan-normalize kabul vs ham-metin karşılaştırma** (`47b6734d` ile İLGİSİZ —
  o commit `urunler.json`'a/`index.html`'e dokunmuyor; bu kapı **katalog verisine bağlı**
  tetiklendi).

---

## 3. KAPI1 — SAPMA SAYILARI VE SINIFLARI (bağımsız betikle yeniden ölçüldü)

```
URETIM (mmb.yayimlanir_mi) evreni       : 1048 etiket
AYNA   (_yayin_bagimsiz) evreni         : 1011 etiket
SAPMA TOPLAM                            :   39
  FAZLA (üretimde var, aynada yok)      :   38
  EKSIK (aynada var, üretimde yok)      :    1
```

**Sınıflandırma — hepsi açıklandı, `DIGER` sınıfı 0:**

| sınıf | adet | kaynak |
|---|---|---|
| yeni **(d) `jeton_sahibi`** kolu | **38** | `47b6734d` → `baslik_yargisi_var_mi` 4. kol |
| yeni **`yabanci_marka`** kolu | **1** | `47b6734d` → `yayimlanir_mi` 2. kol (`Hyundai\|Genesis`) |
| aksan farkı | **0** | — |
| açıklanamayan | **0** | — |

**FAZLA ilk 20** (hepsi (d) kolu):
`Hyundai|Accent, Alfa Romeo|Alfetta, Nissan|Armada, Kia|Carnival, Honda|Clarity,
Mazda|Demio, Yamaha|Dragstar, Hyundai|Elantra, Suzuki|GSF, Alfa Romeo|GTV,
Alfa Romeo|Giulietta, Hyundai|Kona, Suzuki|Maruti, Nissan|Murano, Alfa Romeo|Nord,
Kia|Picanto, Kia|ProCeed, Fiat|Qubo, Nissan|Rogue, Jaguar|S-Type`

**EKSIK (tamamı):** `Hyundai|Genesis` — `yabanci_marka` kolu.

38 sayısı, merge'ün beyan ettiği çip artışıyla (1022 → 1060) **birebir tutuyor.**
Yani kapsama kazancı gerçek; kırmızı yanan şey **bayat aynadır**, üretim değil.

### Kök: evren BUGÜN ÜÇ YERDE tanımlı (dosya:satır)

| # | yer | rol | 12 Ağu'da güncellendi mi |
|---|---|---|---|
| 1 | `tools/marka_model_build.py:1202` `yayimlanir_mi` | **ÜRETİM / kanonik** | EVET (iki yeni kol) |
| 2 | `tools/model-uyelik-kapisi.py:139` `_bagimsiz_baslik_yargisi` (+`_bagimsiz_sahiplik:103`, `_bagimsiz_sahip:126`, `_b_yargi:839`) | bağımsız ayna #1 | EVET |
| 3 | `tools/model-kanon-d1-test.py:252` `_yayin_bagimsiz` | bağımsız ayna #2 | ❌ **HAYIR — bayat kaldı** |

(4. yüzey `tools/cip-indeks.py:504 `_elendi`` üretimi çağırır, ayrı gövde değil.)

`47b6734d` aynalardan **birini** güncelledi, **ötekini unuttu.** Bu, bu depoda adı konmuş
sınıftır: [[ikiz-tanim-sessiz-ayrisma]] — ama burada **N=2 ayna** olduğu için sınıf
"ikiz" değil "çoğul". Aynayı tek tek yamamak sınıfı KAPATMAZ
([[tekil-yama-sinifi-kapatmaz]]): bir sonraki yargı kolunda 3. yüzey yine bayatlar.

---

## 4. KAPI2 — AKSAN EKSENİ (ayrı kök, `47b6734d` DEĞİL)

`tools/faz3-bayrak.js:445-456`:

```js
const hedef = ozetVeri.yeni[0].baslik.split(/\s+/)[0];      // BUGÜN: "Citroën"
...
kontrol("yedek sonuclar gercekten sorguyla eslesiyor",
  kartlar(kayit).every((c) => c.textContent.toLocaleLowerCase("tr")
                               .indexOf(hedef.toLocaleLowerCase("tr")) !== -1));
```

* **Kabul aralığı (sayfa):** `edgeYedek()` → `aramaPlani()` → `markaAdiKanonu()` →
  `markaNorm()` = `norm()` + **NFD + birleşen-işaret atma** (`index.html:2684`).
  `"Citroën"` → `citroen` → TANINMIŞ MARKA → **marka sorgusu** kolu çalışır ve
  ham metni `Citroen` (aksansız) olan kartlar **doğru şekilde** eşleşir.
* **Karşılaştırma aralığı (test):** ham `indexOf` — aksan katlaması **YOK**.

Sonuç: sayfa DOĞRU davranıyor, **iddia yanlış birimde ölçüyor.** Bu tam olarak
[[kabul-araligi-karsilastirma-araligi]] sınıfı: kabul ve kıyas TEK kanonik fonksiyondan
türemiyor. Ayrıca iddia **veri-bağımlı**: `hedef` katalogun EN YENİ ürününün ilk
kelimesidir — aksanlı/marka-adı olan herhangi bir ürün başa geçtiği an kapı kırmızı yanar.
Yani bu kapı bugün `47b6734d` yüzünden değil, **ürün partisi yüzünden** düştü ve bundan
sonra da rastgele düşmeye devam eder.

**Sapan iddia sayısı: 1.** (`49 geçti / 1 kaldı`.) Sapan eleman: sorgu `"Citroën"`,
kart metni `"Citroen"`.

---

## 5. ÖNERİ: **ONARIM** (REVERT DEĞİL)

`47b6734d` geri alınmamalı:
* sapmanın 39/39'u açıklanmış durumda, `DIGER` sınıfı 0 — belirsizlik yok;
* üretim tarafı **doğru**, kapsama kazancı gerçek (çip 1022 → 1060, %67,33 → %68,56);
* revert, ölçülmüş bir kapsama kazancını ve `Hyundai|Genesis` gürültü düzeltmesini
  geri alır — yani "kapsamayı geri alarak kapıyı susturmak"la aynı yere düşer;
* KAPI2 zaten `47b6734d`'den **bağımsız**; revert onu açmaz, yayın yine kapalı kalır.

### Yazılacak onarım (somut, sıradaki oturumun ilk işi)

**A — KAPI1 (tek kanonik bağımsız yargı):**
`tools/model-uyelik-kapisi.py` içindeki bağımsız gövdeyi (`_bagimsiz_kanon`,
`_bagimsiz_sasi_kodu`, `_bagimsiz_ayri_arac`, `_bagimsiz_ciplak_sayi`,
`_bagimsiz_sahiplik`, `_bagimsiz_sahip`, `_bagimsiz_baslik_yargisi`, çapraz-marka
susturması) **yeni bir `tools/bagimsiz_yayin_yargisi.py` modülüne TAŞI** ve oraya
`yabanci_marka` kolunun bağımsız aynasını da ekle; `model-uyelik-kapisi.py` ile
`model-kanon-d1-test.py:252` **ikisi de bu tek modülü import etsin**, ikinci gövde
KALMASIN. Totoloji riski yok: modül `marka_model_build.yayimlanir_mi`'yi ÇAĞIRMAZ,
yargı tablolarını `arama.py`'den bağımsız okur (bugünkü anti-totoloji özelliği korunur),
ama **bağımsız yargı N kopya değil 1 kopya** olur.

**B — KAPI2 (kabul == kıyas):**
`tools/ozet-ac-ayikla.js` desenini uygula: `index.html`'den `aramaPlani` +
`aramaPlaniEsler` (+ bağımlı `markaNorm`/`norm`/`markaAdiKanonu`) gövdesini
**canlı ayıklayan** bir ortak yardımcı yaz (`tools/arama-plani-ayikla.js`), ve
`faz3-bayrak.js:455`'teki ham `indexOf` iddiasını **o canlı yüklemle** kur. İddia
"kart metni sorguyu ham içeriyor" değil, "çizilen her kart, sayfanın KENDİ arama
yüklemine göre sorguyla eşleşiyor" olsun. Aksan katlaması KALDIRILMAZ (gerçek ihtiyaç:
Citroën/Škoda) — iki taraf **aynı fonksiyondan** türetilir.

**C — kabul (yazıldıktan sonra koşulacak):** KAPI1 rc=0 · KAPI2 rc=0 ·
`marka-sayac-kapisi.py` · `ilan-tutari-kapisi.py` · çip kapısı · `is-akisi-kapisi.py` ·
`ci-kapsam-test.py` · `node tools/parite-test.js` (ANA checkout) · çip 1060 / %68,56
GERİLEMEYECEK · mutasyon: evreni ikiye ayıran mutant KIRMIZI, kontrol mutantı YEŞİL.

### SIRADAKI TEK İŞ (tek cümle)

`tools/model-kanon-d1-test.py:252`'deki `_yayin_bagimsiz` gövdesini sil ve yerine
`tools/model-uyelik-kapisi.py`'den çıkarılacak yeni `tools/bagimsiz_yayin_yargisi.py`
modülünü (içine `yabanci_marka` bağımsız kolu eklenmiş hâliyle) import et — böylece
bağımsız yargı TEK kanonik noktadan türesin.

---

## 6. NE ÖLÇÜLMEDİ (beyan — uydurulmadı)

`marka-sayac-kapisi.py`, `ilan-tutari-kapisi.py`, çip kapısı, `is-akisi-kapisi.py`,
`ci-kapsam-test.py`, `parite-test.js`, mutasyon bataryası ve güncel çip/kapsama sayıları
bu turda **KOŞULMADI** (devir kesti). Çip 1060 / %68,56 rakamı `47b6734d`'nin kendi
beyanıdır, bu turda bağımsız doğrulanmadı.
