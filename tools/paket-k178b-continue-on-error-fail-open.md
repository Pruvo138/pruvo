# PAKET K178b — 🔴 ACİL: K178'in çaresi FAIL-OPEN oldu; SERİT B artık kırmızıyı YEŞİL raporluyor

Mimar: KraL · 18 Ağu 2026 · hedef kat: İŞÇİ · kabul MİMARDA.
**Hata BENİM spec'imde.** K178 §3'te "adım düzeyinde `continue-on-error: true` (job sonucu
yine de kırmızı raporlar)" yazmıştım — **parantez içindeki iddia YANLIŞ.**

## 1. ÖLÇÜLEN OLGU (mimar, main `ce6d91f7`)

```
grep -c "continue-on-error: true" .github/workflows/nobet.yml → 124
grep -c "if: always()"            .github/workflows/nobet.yml →   1
```

GitHub Actions'ta adım düzeyinde `continue-on-error: true`, adımın kırmızısının **job'u
düşürmesini engeller**: adımın `outcome`'ı `failure`, `conclusion`'ı `success` olur ve
**job YEŞİL biter.**

**Sonuç — durum K178 ÖNCESİNDEN daha kötü:**

| | önce (K178'siz) | şimdi (K178 ile) | olması gereken |
|---|---|---|---|
| kaç kapı koşuyor | 12/126 | **126/126** ✅ | 126/126 |
| kırmızı kapı görünüyor mu | hayır (skipped) | **hayır (yeşil raporlanıyor)** | EVET |
| job hükmü | failure (doğru) | **success (YANLIŞ)** | failure |

Yani 114 sessiz kırmızı, 122 **yeşil beyanlı** kırmızıya dönüştü. Görünmeyen kırmızı kötüdür;
**sağlıklı olduğunu İDDİA EDEN kırmızı daha kötüdür** ([[fail-slow-fail-opendir]] ·
[[duzeltme-fail-loudu-fail-opena-cevirebilir]]).

## 2. HÜKÜM

**H1 — `continue-on-error: true` → `if: ${{ !cancelled() }}`.** İstenen davranış "önceki adım
kırmızıysa da koş" idi; bunu sağlayan şey `if` koşuludur, `continue-on-error` DEĞİL.
`if: ${{ !cancelled() }}` ile adım önceki kırmızıya rağmen koşar **ve kendi kırmızısı job'u
düşürür**. `always()` DEĞİL: bu şerit kuyrukta sık `cancelled` oluyor
([[cancelled-yigini-yayin-tavani]]); `always()` iptalden sonra da koşup runner yakar.

**H2 — Kapsam AYNEN K178'inki.** Yalnız `serit-b` job'unun kapı adımları. Bloklayıcı
şeritlerde (`serit-a2`/`a3`, `deploy` zinciri) **hiçbir şey değişmez**; oradaki
`continue-on-error` varsa DOKUNULMAZ (ölçüp ayır: 124 isabetin kaçı `serit-b` dışında?).

**H3 — Nöbetçi bu ekseni de ölçer.** `tools/serit-b-maskeleme-test.py` bugün yalnız
"bağımsız koşuyor mu" ölçüyor. **İkinci eksen eklenir:** bir kapı adımı
`continue-on-error: true` taşıyorsa **RED** (`YUTAN=<n>`), çünkü o adım kırmızısını yutar.
Tek eksen ölçen nöbetçi bu hatayı kaçırdı — bataryanın kendisi eksikti.

## 3. KABUL (çalıştırılabilir)

```
python3 tools/serit-b-maskeleme-test.py
```
son satır + rc=0:
```
ADIM=<n> BAGIMSIZ=<n> MASKELEYEN=0 YUTAN=0 MUTANT=4/4 KONTROL=2/2
```

### Mutantlar (4/4 KIRMIZI)
* **M1** — bir adımdan `if` koşulunu kaldır → `MASKELEYEN=1`, adım adıyla RED.
* **M2** — bir adıma `continue-on-error: true` geri koy → **`YUTAN=1`** RED. *(Bugünkü
  hatayı birebir yakalayan mutant budur; K178'in bataryasında YOKTU.)*
* **M3** — evreni boş kümeye indir → rc≠0 `OLCULEMEDI`, YEŞİL DÖNMEZ.
* **M4** — nöbetçiyi bloklayıcı şeride de uygula → RED (kapsam genişletme).

### Kontroller (2/2 YEŞİL)
* **K1** — `serit-a2`/`a3` adımları DEĞİŞMEMİŞ sayılır.
* **K2** — altyapı adımları (`checkout`, `setup-python`, `Post Run …`) ne MASKELEYEN ne
  YUTAN sayılır (yanlış-pozitif nöbetçisi).

### 🔴 ASIL KABUL — canlı koşum
Merge sonrası ilk SERİT B koşumunda:
```
gh -R Pruvo138/pruvo run view <run_id> --json jobs --jq '[.jobs[]|select(.name=="serit-b")|.steps[]|.conclusion] | group_by(.) | map({durum:.[0], sayi:length})'
gh -R Pruvo138/pruvo run view <run_id> --json jobs --jq '.jobs[]|select(.name=="serit-b")|.conclusion'
```
İkisi birden istenir:
1. `skipped` sayısı **114'ten belirgin DÜŞMÜŞ** (kapılar koşuyor),
2. job `conclusion` = **failure** (kırmızı kapılar VAR ve GÖRÜNÜYOR).

⚠️ Job `success` çıkarsa bu paket BAŞARISIZDIR — kırmızılar hâlâ yutuluyor demektir.
Kuyrukta `cancelled` olursa `OLCULEMEDI` yaz, push'suz bir pencerede tekrar ölç.

## 4. SINIRLAR

* Hiçbir kapının KENDİ mantığına dokunulmaz; kırmızılar **susturulmaz**, görünür kılınır.
* Kırmızı sayısının artması BEKLENEN sonuçtur.
* Reçete kapısının kırmızısı (K179) bu pakette çözülmez.
* **DOKUNMA:** `urunler.json` · `crontab` · `DEVAM.md` · `~/.claude/cron/` · bloklayıcı şeritler.

## 5. İŞÇİ TALİMATI

* Tavan ~30-40 tur, tek dilim. Alt ajan / paralel görev AÇMA.
* Bütçenin yarısında elindekini commit et, raporu kapat.
* Kaynak kod commit'i **worktree'de**; iş bitince worktree kaldırılır ve `git worktree list`
  ile kanıtlanır.
