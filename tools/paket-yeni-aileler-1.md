# PAKET — Yeni sarı aileler, 1. dalga: hortum adaptörü + ölçüye özel kutu + vidalı kavanoz/tapa
## (Okan seçimi, 17 Tem — keşif: GitHub/MakerWorld taraması, karar sohbette)

**Kat:** Claude Mühendis (yüksek efor). Üreteç = pruvo-jenerator deseni (konektör/braket/dişli
v2 nasıl kurulduysa aynen: `~/dev/pruvo-jenerator`, dogrulama setleri + SOZLESME.md düzeni).
**Worktree'de çalış (iki repoda da).** Onay/yargı MİMARA (KraL).

## Aileler ve kaynak hijyeni (İHLAL = RED)
1. **Hortum adaptörü / redüksiyon** (süpürge · marin · atölye): iki uç çapı (iç/dış geçme
   seçimi), boy, konik geçiş, cidar. KAYNAK: SIFIRDAN — standart hortum çapları (süpürge
   32/35/38 mm, marin/bahçe standartları) kamu malı tablolardan; GitHub'daki lisanssız
   repo (Vacuum-Attachments) AÇILMAZ/OKUNMAZ, sadece aile fikridir.
2. **Ölçüye özel kutu (kapaklı · bölmeli)**: iç en/boy/yükseklik, duvar kalınlığı, kapak
   tipi (kapaksız/geçme kapak), bölme sayısı (0-N). KAYNAK: sıfırdan; istersen CC0
   çekirdek (astromikemerri/OpenSCAD-Enclosure) serbestçe kullanılabilir (CC0 = yükümlülük
   yok) ama kalite/bakım standardımıza uyacaksa — karar senin, raporla.
3. **Vidalı kapaklı kavanoz / tapa-kapak**: gövde çapı, yükseklik, diş adımı (kendi vida
   motorumuz/BOSL2 threading), kapak tipi (kavanoz kapağı / kör tapa). KAYNAK: sıfırdan;
   diş standartları kamu malı.

## Her aile için zorunlu zincir (Faz D altyapısı hazır — desen rutin)
a. Üreteç .scad (pruvo-jenerator) + dogrulama seti: derleme + manifold + bbox +
   monotonluk (mevcut kabul deseni, aile başına ≥12 set; uç değerler dahil).
b. Parametre şeması + konfigüratör kaydı (`jenerator/urunler/<id>.json`; tabanFiyatTL
   **null** — fiyat OKAN'dan, sonra girilir; sayfada "Ölçüye özel fiyat" görünür).
c. hacim.js fiyat formülü: dondurulmuş STL fixture'lı kalibrasyon (kalibrasyon-senkron
   deseni, ≤%3). **DİKKAT — hacim.js'te eşzamanlı yazarlar var** (vida paketi + Faz E):
   SADECE yeni aile blokları EKLE, mevcut ailelere DOKUNMA; merge sırasını mimar yönetir.
d. Önizleme: public eşlem (`jenerator/test/esleme/`) + 4d ölçümü ≤%3 geçerse aile
   ONIZLEME_AILELER'e (dalda; merge = yayın kapısı mimar).
e. Sarı ürün kaydı: `urunler.json` BAŞINA 3 yeni obje (parametrik:true, kategori Tamirat,
   fiyat "", "farklı renk seçenekleri" dili, ferah açıklama formatı — CLAUDE.md sarı
   kuralları). Kapak görseli CODEX ile (çoklu-şekil prompt kalıbı) → R2 → gorseller[0].
   NOT: urunler.json'a başka oturum yazmıyorken ekle (sıralı çalışma), guard yeni ürünü
   engellemez.
f. Taban fiyat İÇİN mini pazar bakışı (aile başına 3-5 kaynaklı fiyat + öneri) — rapora;
   fiyatı MİMAR Okan'a taşır, onaysız fiyat GİRİLMEZ.

## Kabul (mimar koşacak)
1. pruvo-jenerator dogrulama: 3 yeni aile tüm setlerde yeşil (+ mevcut aileler regresyon).
2. `node jenerator/test/kalibrasyon-senkron.js` — 3 yeni aile fixture'larıyla genişlemiş,
   yeşil; önce-kırmızı kanıtı (fixture'lar eski hacim.js'te koşulunca kırmızı).
3. `node jenerator/test/fiyat-test.js` (3 aile null-fiyat yolunda) + `node
   onizleme/test/kabul.js` (eklenen aileler kapsamda) + `node shop/test/kabul.js` yeşil.
4. Parite 2'li yeşil; build sonrası 3 yeni sarı sayfa görüntüsü (rozet + "Ölçüye özel
   fiyat" + seçici düzeni) + D1 senkron sayısı doğru.
5. Kapı-1 (deploy sonrası, yeni listeyle) p95 ≤ 10 sn.

## Rapor
Aile × (dogrulama sonuçları, kalibrasyon sapmaları, önizleme ölçümü, taban fiyat önerisi)
+ DEVAM.md güncellemesi (iki repoda da not). Sorular mimara, Okan'a değil.
