# PAKET — K184 merge kabulü (chip: `KraL-K184`)

> Mimar (KraL) hükmü. Bu dosya chip'in TEK talimatıdır; kabul ölçütü BURADA çivilidir ve
> tur içinde BÜYÜTÜLMEZ. Bulgu çıkarsa yeni KALEM açılır, ölçüt sabit kalır.

## 1. Kalemin hâli — hüküm ZATEN VERİLDİ

`kral/k184-talep-sihirbazi` **merge EDİLECEK**. `parite-ege.js` kırmızısı bu dalı
**BLOKLAMIYOR**; sahibi ayrı kalemdir (K228). Gerekçe üç eksende ölçüldü:

1. **İçerik:** dalın `index.html` farkı **299 ekleme / 0 SİLME**; `parite-ege.js`'in referans
   çapa bandı **2592–3198** hiç dokunulmadı → testin yerel referansı iki uçta bayt-aynı.
2. **Taban:** K184'süz main'de de kırmızı (`21 açıklanamayan / 895 sorgu`), **aynı yönde**
   (uç ≥ yerel).
3. **Kök:** `marka=` ekseninde iki yüzey farklı yüklem koşuyor (uç `markaUyeMi ∪ baslikMarkalari`,
   yerel yalnız `markaUyeMi`) → yön matematiksel olarak daima uç ≥ yerel. Çürütme ölçütü:
   `uç < yerel` yönünde TEK ayrışma çıkarsa teşhis düşer.

🔴 Dürüst sınır: iki koşumun sorgu evreni aynı değil (1331 ↔ 895); küme karşılaştırması
YAPILAMADI. Hüküm ①'e dayanır, ②/③ destektir.

## 2. Dal + taban

- Dal: `origin/kral/k184-talep-sihirbazi` (mimar ölçtüğünde uç `f623d712`).
- Taban: **güncel `origin/main`** (bu paket yazılırken K214 + P2/P3 + P1 merge'leri indi).
  Tabanı tazele, **yöntemi (rebase mi merge mi) ve `git rev-list --count origin/main..HEAD`
  sayısını YAZ**.
- 🔴 Rebase edersen aynı ada **force-push ATMA** — K80/CI-adım kapısını
  `diff tabani hedefin atasi DEGIL` ile düşürür. Çare bypass değil **YENİ AD**
  (`kral/k184-talep-sihirbazi-r2` gibi); eski ref'i silme, mimar siler.

## 3. Kapsam — bu dal SİTEYİ DEĞİŞTİRİR

9 dosya, +2359/−104. İçinde `index.html` (+299/−0), `tools/build.py`,
`tools/yayin-topla.py`, `tools/talep-sihirbazi-test.py` (+1652, yeni), `talep-alanlari.js`,
`.github/workflows/nobet.yml`, `jenerator/test/kabul.py`, `tools/is-akisi-kapisi.py`,
`tools/vitrin-siralama-test.js` var.

Bu yüzden K214'ten farklı olarak **merge sonrası canlı teyit ŞARTTIR** (aşağıda §5).

## 4. KABUL — merge ÖNCESİ koşulacak ölçümler (hepsi SAYIYLA raporlanır)

| # | ölçüm | kapatan sonuç |
|---|---|---|
| ① | taban tazeleme | yöntem + `rev-list` sayısı + yeni uç SHA |
| ② | `python3 tools/talep-sihirbazi-test.py` | rc=0 · vaka sayısı (VAKA 36 dahil tekil) |
| ③ | `node tools/parite-test.js` | rc + sayı; kırmızıysa **TABANLA** karşılaştır |
| ④ | `python3 tools/yasal-sayfa-drift-*.py` | rc=0 |
| ⑤ | `python3 tools/ci-kapsam-test.py` | rc=0 |
| ⑥ | `python3 tools/kapi-envanteri*.py` | 7/7 · `MUAF_BAGLAM=0` |
| ⑦ | 🔴 `python3 tools/kisisel-veri-test.py` | rc=0 — **merge ÖN-ŞARTI**, gözle diff YASAK |
| ⑧ | `python3 tools/is-akisi-kapisi.py` | rc=0 |

**HARİÇ:** `parite-ege.js`. Kırmızısı TABANIN, sahibi K228; bu turda **tekrar açılmaz**,
onarılmaz, ölçüte eklenmez.

### Kırmızı çıkarsa
ONARMA — **sayıyı getir**. Hüküm mimarda. Tek istisna: kırmızı senin değişikliğindense
onar, onarımı ÖLÇ ve **çürütmesini** (onarımı geri alınca kırmızının döndüğünü) ayrıca yaz.

### Sahiplik ayrımı — varsayım değil ölçüm
Bir kırmızıyı "taban" diye geçmeden önce **K184'süz main koşumunda da kırmızı olduğunu**
göster (job ADI yetmez; düşen **ADIM** düzeyinde karşılaştır).

## 5. Merge SONRASI — mimar yürütür, chip ÖLÇER

Merge'i ve push'u **mimar (KraL ana oturumu) atar**; chip main'e DOKUNMAZ.
Push indikten sonra chip şunları ölçer:

1. Deploy koşumunun `conclusion` değeri + `deploy` job'ının **`skipped` OLMADIĞI**.
2. 🔴 **Cache-bust'SIZ canlı teyit** (kanonik adres, `?cb=`/`?v=` YOK): `last-modified`
   damgası push'tan sonraya İLERLEMELİ. Tabanı **yayın inmeden ÖNCE** ölç, yoksa
   karşılaştırma yapılamaz.
3. `python3 tools/d1-sync.py --durum` beş eksen.
4. Sihirbazın canlı yüzeyi: `/` üzerinde talep sihirbazının açıldığı ve `shop` ucuna giden
   yolun çalıştığı — ölçemiyorsan `OLCULEMEDI` + sebep yaz, **uydurma**.

## 6. YASAKLAR

- `--no-verify` YOK · kapı bypass'ı YOK · `git checkout` ile yabancı değişikliği geri alma YOK.
- `urunler.json` / `.urun-kaynaklari.json` ELLENMEZ.
- Kardeş evlerin (`~/dev/pruvo-*`) dosyalarına DOKUNULMAZ.
- Ana checkout'ta commit YOK; iş kendi worktree'nde, **tek** worktree.
- Okan'a doğrudan bildirim YOK (karar/bloker dışında); rapor mimara.

## 7. Kapanış

Sayılı kapanış `memory/mimar-posta-kutusu.md`'nin EN ÜSTÜNE; son satır birebir
`✅ İŞ BİTTİ — ARŞİVLENEBİLİRİM` (iş gerçekten bittiyse). Bloke kapanıyorsan satırı yaz ama
**neyin ölçülmediğini + neyi ölçmenin kapatacağını** bırak.
