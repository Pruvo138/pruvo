# EDGE_KATALOG TETİK POLİTİKASI (mimar kararı — 20 Tem 2026)

Bayrak açılışı planlı olay, yangın müdahalesi değil. Ölçüm: usta taslağı 20 Tem
(7.895 ürün; urunler.json 7,53 MB ham / 1,17 MB gzip; sayfa ~66 KB — canlıdan doğrulandı
65.663 B; kararlı büyüme ~245 ürün/gün, toplu-yükleme bandı ~604/gün).

## Eşikler (birincil metrik: ürün sayısı = urunler.json dizi uzunluğu)

| Eşik | Ürün | Anlam |
|---|---|---|
| **B — HAZIRLIK** | **10.000** | Flip DEĞİL: HocA Worker `/katalog` deploy teyidi + faz3 testleri yeşil + flip takvime alınır |
| **A — BİRİNCİL TETİK** | **12.000** | Flip yapılır (aşağıdaki prova sırasıyla) |
| **C — MECBURİ SON TARİH** | **14.000** | Buraya kadar flip olmadıysa başka her iş durur, flip yapılır |

Tavan ~15k (istemci JS belleği; darboğaz hız değil BELLEK). Build süresi ve ozet.json
boyutu tetik DEĞİL (ikincil sağlık göstergesi). Tahmini takvim (20 Tem itibarıyla, TAHMİN):
kararlı hızda 12k ≈ 6 Ağu; toplu-yükleme yeniden başlarsa ≈ 27 Tem.

## Flip provası (sıra ZORUNLU — atlanırsa site boşalır)
1. **[HocA/Okan kapısı]** Worker `/katalog` ucu CANLI (`curl -s ".../katalog?sayfa=1"` anlamlı JSON).
2. `node tools/faz3-sayfalama.js` + `node tools/faz3-gecikme.js` yeşil.
3. `node tools/parite-test.js` + `node tools/parite-ege.js` yeşil (CDN önbellek tuzağı:
   cache-bust/`cache:reload` ile teyit).
4. `python3 tools/d1-sync.py --durum` exit 0 (artık fail-loud).
5. `index.html` `EDGE_KATALOG=false→true` — MÜHENDİS yapar (tek anahtar), commit+push.
6. CDN purge (`tools/faz3-onbellek-purge.md`).
7. Canlı canonical doğrulama: ana sayfa `ozet.json` çekiyor, arama `/ara`ya gidiyor,
   `urunler.json` İNMİYOR.

## Geri alma
`true→false` + push + purge = kanıtlanmış eski davranış; onay beklemez, Okan'a not düşülür.
Flip sonrası ilk 24-48 saat izlenir.

## ⚠️ Bağımsız ikinci kısıt — statik depo (ayrı iş)
Flip ürün SEO sayfalarını AZALTMAZ. `urun/` bugün 514 MB (7.895 × ~66 KB); ~15k'da ≈ 990 MB →
GitHub Pages ~1 GB yumuşak sınırına dayanır, ~20k AŞAR. Sayfa şablonu 5 günde 9,4 KB → 66 KB
şişti (SEO zenginleştirme). Çözüm adayları: sayfa ağırlığını düşürmek ya da depo stratejisi —
aynı ~15k bandında ısırdığı için A eşiği planıyla BİRLİKTE ele alınacak.

## İzleme
Şimdilik: her toplu ekleme partisi sonrası ürün sayısı DEVAM.md'ye yazılır; 10.000 görülünce
B kapısı açılır. (Öneri açık: durum.py'ye eşik-bandı sayacı — mühendis spec'i ayrıca yazılacak.)
