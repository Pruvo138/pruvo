# MÜHENDİS İŞ PAKETİ — FAZ 3: Site Araması + Katalog Beslemesi Edge'e (20k Hazırlığı)

**Kat:** MÜHENDİS = **Claude Opus yüksek efor** (arama semantiği "hatası sessiz" sınıfı —
Codex'e verilmez; CLAUDE.md İş Bölümü). Kabul testlerini mimar koşturur.
**Karar sahibi:** Okan (16 Tem 2026) — hedef katalog 20k ürün; bugünkü tarayıcı-içi model
~15k'da tıkanıyor (ölçüm: [[katalog-olcek-siniri]]).
**Zamanlama:** Kod ŞİMDİ yazılır, **bayrak arkasında** durur; canlıya alma kararı katalog
~12-15k bandına girince ya da mobil ölçümler bozulunca (mimar+Okan).

## BUGÜNKÜ DURUM (değiştirilecek olan)

- `index.html` TÜM katalogu `fetch("urunler.json")` ile çeker (7.171 üründe ~5 MB), aramayı
  tarayıcıda yapar (yerel 15-27 ms). 20k'da dosya ~14-15 MB = mobil ilk açılış + bellek riski.
- Worker'da `/ara?q=` endpoint'i ZATEN VAR ve site aramasıyla **birebir parite** veriyor
  (Faz 1-2 işi; referans testi `node tools/parite-test.js`, canlı kodu referans alır).
- Ege (`mod=ege`) D1'de arıyor — **bu pakette Ege tarafına DOKUNULMAZ.**

## YAPILACAK

1. **Bayrak:** `index.html`'de tek yerden `EDGE_KATALOG = true/false`. `false` = bugünkü davranış
   AYNEN (geri dönüş yolu). Bayrak kapalıyken hiçbir davranış değişmez — regresyonun kanıtı test.
2. **İlk yük küçülür:** build.py yeni bir `ozet.json` üretir (kategori listesi+sayıları, marka
   çipleri, parametrik ürün id havuzu, en yeni N ürün kartlık özet alanlarıyla; hedef < 150 KB).
   Ana sayfa ilk boyamayı `ozet.json` ile yapar; 5-15 MB'lık `urunler.json` ARTIK İNMEZ (bayrak açıkken).
3. **Sayfalama:** kategori/marka/"Tümü" görünümleri Worker'dan sayfalı çekilir (`/katalog?kategori=
   &marka=&sayfa=` yeni endpoint; D1'den okur, sıralama: en yeni üstte — urunler.json dizisindeki
   sıra D1'de korunuyor olmalı, kontrol et). Sonsuz kaydırma veya "Daha fazla" butonu; saf JS.
4. **Arama:** yazarken debounce (~250 ms) ile `/ara?q=` (site modu). Boş sonuç/ağ hatasında
   kullanıcıya nazik mesaj. Edge gecikmesi ölçülmüştü (80-150 ms) — spinner ile kabul edilebilir.
5. **Parametrik vitrin korunur:** ana sayfada rastgele 4 parametrik ürün en üstte, sarı rozet —
   `ozet.json`'daki havuzdan seçilir; davranış bugünkünün aynısı.
6. **Ürün sayfaları ve SEO değişmez:** `urun/<id>/` statik üretim, sitemap, JSON-LD aynen.
   `urunler.json` üretilmeye ve yayınlanmaya devam eder (yedeklilik + dış tüketiciler).
7. **Önbellek:** `/katalog` ve `/ara` yanıtlarına makul edge cache (örn. 60 sn) + D1 senkronu
   sonrası purge stratejisi belgelenir. DİKKAT: parite/kabul testleri önbelleği DELEREK koşar
   (cache-buster parametre) — [[d1-arama-tuzaklari]] dersi: CDN önbelleği testte YEŞİL YALAN söyletir.

## KAPSAM DIŞI

- Ege araması / `mod=ege` — dokunma. — Arama SEMANTİĞİ (skorlama/eşleşme kuralı) — değişmez;
  bu paket sadece NEREDE koştuğunu taşır. — Yeni framework/kütüphane — yasak (saf JS).
- Kategori seti, tasarım dili, ürün sayfası şablonu — değişmez.

## KABUL TESTLERİ (hepsi çalıştırılabilir; yeşil olmadan iş kapanmaz)

1. **Parite (kanonik):** `node tools/parite-test.js` YEŞİL — bayrak AÇIKKEN sitenin kullandığı
   endpoint ile yerel arama birebir aynı sonucu verir. `node tools/parite-ege.js` de YEŞİL
   (dokunulmadığının kanıtı).
2. **Bayrak-kapalı regresyon:** `EDGE_KATALOG=false` iken sayfanın ağ trafiği ve arama davranışı
   bugünküyle aynı (test: bayrak kapalı build'de urunler.json çekiliyor, /katalog HİÇ çağrılmıyor).
3. **Yük bütçesi:** bayrak açıkken ana sayfa ilk yükünün indirdiği toplam veri < 500 KB
   (görseller hariç); `ozet.json` < 150 KB. Test scripti ölçüp yazdırır.
4. **Gecikme bütçesi:** `/ara` ve `/katalog` p95 < 300 ms (cache-buster'lı 20 ardışık istek,
   edge'de). Sayıları rapora yaz — proje ölçümle yürür.
5. **Sayfalama doğruluğu:** kategori X'in tüm sayfaları birleşince D1'deki kategori X kümesiyle
   birebir aynı id seti (eksik/mükerrer yok); sıralama en-yeni-üstte.
6. **Parametrik vitrin:** bayrak açıkken ana sayfada 4 parametrik kart, rozetli.
7. **Zarif bozulma:** Worker 500/ulaşılamaz iken sayfa çökmez; kullanıcıya mesaj + arama kutusunun
   yerel `ozet.json` içinde en-azından başlık araması yapabildiği yedek yol (fallback) çalışır.

## TESLİM

- Kod: `index.html`, `tools/build.py` (ozet.json), Worker'a `/katalog` endpoint'i (mevcut arama
  worker'ının reposu/dizini neredeyse oraya — Ege dosyalarına dokunmadan; belirsizse yargı listesine).
- **Commit ETME** — değişiklik listesi + 7 testin çıktısı + ölçüm sayıları (yük/gecikme) ile rapor;
  commit/push ve canlıya alma zamanlaması mimarın.
