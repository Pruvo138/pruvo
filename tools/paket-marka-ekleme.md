# İŞ PAKETİ: Marka tarama + toplu ürün ekleme (MÜHENDİS talimatı)

Sen bu partinin MARABASISIN (varsayılan: Sonnet alt-ajanı — ürün yükleme maraba işidir;
CLAUDE.md KOMUTA ZİNCİRİ). Çağıran sana KAYNAK (Printables/Thingiverse/********) ve MARKA
(ya da doğrudan ID listesi / satıcı URL'si) verdi. Repo: /Users/okan/dev/pruvo.
Uçtan uca sen koşarsın; mimara sadece rapor dönersin.
NOT: Görsel/içerik işini ekleme scriptleri kendi içinde Codex mini'ye devreder — sen ayrıca
Codex ÇAĞIRMA (kota kuralı: Codex kredisi az, sadece scriptlerin kendi çağrısı meşru).
Teknik engel çıkarsa (script hatası, beklenmedik veri) onarmaya ÇALIŞMA — raporla; kod işi
Mühendis katının, zor onarım Usta katınındır (mimar yönlendirir).

## KAYNAK=******** ise (özel mod — satın almadan listeleme)
- `python3 tools/cgt-ekle.py "<satıcı-url>" <list|final>` (çağıran "final/indirimli" dediyse final,
  yoksa list). TL = round(USD × 100); şüphede ürün sayfasındaki İNDİRİMSİZ (üstü çizili) USD esas.
- Ücretli kaynak: `lisans` alanı YOK, atıf YOK. Ölçü satırı beklenmez (STL siparişte alınır).
- Adım 1-2'yi atla; aracın STAGE tablosuyla 4'e geç.

## Adımlar

1. ARA (çağıran doğrudan ID listesi verdiyse bu adımı atla, o ID'lerle 3'e geç):
   - Printables: `python3 tools/printables-ara.py "<MARKA>"`
   - Thingiverse: `python3 tools/thing-ara.py "<MARKA>"`
   Araç NC/OCL (satılamaz) + çöp (anahtarlık/logo/minyatür) + zaten-ekli olanları kendisi eler.

2. ALAKASIZLIK ELEMESİ (aday listesi üzerinde, kural):
   - Ürünün KENDİSİ bu markanın parçası/aksesuarı/ürünü mü? Değilse ELE. Örnek eleme sınıfları:
     başka takımın/markanın aracı (F1: Red Bull/Jordan/Lotus şasisi "Renault motorlu" diye girmez),
     üçüncü taraf IP'si taşıyan (Hogwarts/Disney vb. → telif), marka LOGOSU basılan alakasız eşya
     (yazıcı düğmesi, anahtarlık — ★POPULER-COP işaretliyse İSTİSNA: ekle), başlığı belirsiz olup
     detayı da alakasız çıkan.
   - **YASAK (Okan, 2026-07-16): ölçekli model / maket ARAÇLAR (otomobil-motosiklet-araç maketi,
     "scale model") ve LEGO ile ilişkili HER ürün (uyumlu/benzeri dahil) — lisans uygun olsa bile
     EKLENMEZ, atla+bildir.** (Eski "markanın tarihî ürünü maketi meşru" istisnası KALDIRILDI.)
   - EMİN OLAMADIĞIN her adayı ekleME; rapora "yargı listesi"ne yaz (gerekçeyle) — mimar karar verir.

3. EKLE: kalan ID'leri tek komutta:
   - Printables: `python3 tools/printables-ekle.py <id...>`  (cache `pr<id>`)
   - Thingiverse: `python3 tools/urun-ekle.py <id...>`  (cache `<id>`)
   İLK PARTİ 3-5 ID ile dene; tablo düzgünse kalanını ver. Araç STAGE eder, COMMIT ETMEZ.

4. GÖZDEN GEÇİR ve DÜZELT (yalnız BU partide eklenen ürünlerde; HEAD'dekilere DOKUNMA):
   - Görselleri Read/inceleme yapma; `.thing-cache/<key>/oneri.json` + urunler.json kayıtları yeter.
   - Fiyat kesinleştir: küçük parça ~200-600, set/büyük ~600-1200 TL. Sarı seri değilse fiyat BOŞ olamaz.
   - Kategori: CLAUDE.md kuralı — marka-özel araç parçası ilgili araç kategorisine.
     (Araç maketi zaten YASAK — adım 2'deki kural; buraya gelmemeli.)
   - Marka dizisi konvansiyonu: ["<Marka>", "<Model>"] (model adı sade: "Clio MK1" değil "Clio",
     "Laguna II" değil "Laguna"); aftermarket ürün adları (Tigerexped vb.) marka DEĞİLDİR, çıkar.
   - Açıklamada "3D baskı" GEÇMEZ; "Yaklaşık dış ölçüler: A × B × C mm." satırı OLMALI —
     yoksa STL/3MF'i indirip ölç (tools/printables-api.py: model_bbox; dosya stl/'e `pr<id>.stl`).
     Kaynakta hiç basılabilir dosya yoksa ürünü rapora yaz (yargı listesi).
   - CC lisanslı üründe `lisans` alanı DURMALI (atıf yasal); tasarımcı adı boşsa boş bırak (build halleder).
   - Aynı tasarımcının aynı konsepti iki ilanla girmişse tekini tut, diğerini yargı listesine yaz.
   - Düzeltmeleri scratchpad'e yazacağın tek `.py` ile uygula (sadece bu partinin id'leri).

5. RAPOR (işin bitiş çıktısı, JSON): `.thing-cache/parti-rapor.json` dosyasına yaz:
   `{"marka": "...", "eklenen": ["id", ...], "elenen": [{"id": "...", "neden": "..."}],
     "yargi_listesi": [{"id/aday": "...", "soru": "...", "onerim": "..."}],
     "duzeltilen": ["id: ne düzeltildi", ...]}`
   Son mesajın tek satır özet olsun: "STAGED <N> | yargı <M>".

## YAPMA (mimar/Okan alanı)
- git commit / push YAPMA. `tools/duzelt.py` / guard / HEAD'deki ürünlere DOKUNMA.
- `.urun-kaynaklari.json`ı elle DÜZENLEME (ekleme araçları kendi yazar). Sır dosyalarını okuma.
- Lisans kapısını (satilabilir()) gevşetme; bilinmeyen lisans = yargı listesine.
- Soru sorup bekleme — kararsız kaldığın her şey yargı listesine, işin geri kalanını bitir.
