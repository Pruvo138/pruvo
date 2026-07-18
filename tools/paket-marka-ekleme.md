# İŞ PAKETİ: Marka tarama + toplu ürün ekleme (MÜHENDİS talimatı)

Sen bu partinin MARABASISIN (varsayılan: Sonnet alt-ajanı — ürün yükleme maraba işidir;
CLAUDE.md KOMUTA ZİNCİRİ). Çağıran sana KAYNAK (Printables/Thingiverse/********/MakerWorld/
Cults3D/MyMiniFactory) ve MARKA (ya da doğrudan ID/slug listesi / satıcı URL'si) verdi.
Repo: /Users/okan/dev/pruvo.
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

## KAYNAK=MakerWorld / Cults3D / MyMiniFactory ise (ÖLÇÜSÜZ kaynaklar)
Bu üçü de `makerworld-*.py` desenini izler: `ara` → aday ID/slug listesi, `ekle` → STAGE.
**ÖLÇÜSÜZ eklenir:** indirme login/hesap/OAuth-gated olduğu için ölçü ekleme anında alınamaz →
açıklamada "Yaklaşık dış ölçüler: A × B × C mm" satırı **BEKLENMEZ** (STL siparişte ölçülür).
`denetim-kapisi.py` bu üç kaynağı ölçü kapısından MUAF tutar (kaynak notu `kaynak` alanından/
link domaininden tanınır) — ölçüsüz olmaları auto_sil'e YOL AÇMAZ. Adım 4'te ölçü indirmeye ÇALIŞMA.
- **MakerWorld** (ANAHTAR GEREKMEZ — public API, hazır). Argüman: sayısal `design_id`.
  - Ara:  `python3 tools/makerworld-ara.py "<MARKA>"`   → `design_id` listesi
  - Ekle: `python3 tools/makerworld-ekle.py <design_id...>`  (ön-kontrol: `--kuru <id...>`; cache/R2 `mw<id>`)
- **Cults3D** (API ANAHTARI GEREKİR — env `CULTS_USERNAME` + `CULTS_API_KEY`; alternatif
  dosya `CULTS3D_CREDENTIALS=/yol/creds.json`). Argüman: `slug` (sayısal ID değil).
  Anahtar yoksa `ara` "Cults3D kimligi yok" raporlar → maraba **"anahtar yok" RAPORLAR, zorlamaz**.
  - Ara:  `python3 tools/cults3d-ara.py "<MARKA>"`   → `slug` listesi
  - Ekle: `python3 tools/cults3d-ekle.py <slug...>`  (ön-kontrol: `--kuru <slug...>`; cache/R2 `c3d<slug>`)
- **MyMiniFactory** (API ANAHTARI GEREKİR — env `MMF_KEY`; alternatif dosya `<repo>/.mmf-token`,
  tek satır ham anahtar). Argüman: sayısal `object_id`. Anahtar yoksa `ara` "ANAHTAR YOK" raporlar →
  maraba **"anahtar yok" RAPORLAR, zorlamaz**.
  - Ara:  `python3 tools/myminifactory-ara.py "<MARKA>"`   → `object_id` listesi
  - Ekle: `python3 tools/myminifactory-ekle.py <object_id...>`  (ön-kontrol: `--kuru <id...>`; cache/R2 `mmf<id>`)

Not: Cults3D/MMF ücretsiz+satılabilir modelleri alır (Cults ücretli pazar modelini `ara` eler);
üçünün de `ara` aracı NC/satılamaz + çöp + zaten-ekli olanı kendisi eler (Printables gibi).

## Adımlar

1. ARA (çağıran doğrudan ID/slug listesi verdiyse bu adımı atla, o ID'lerle 3'e geç):
   - Printables: `python3 tools/printables-ara.py "<MARKA>"`
   - Thingiverse: `python3 tools/thing-ara.py "<MARKA>"`
   - MakerWorld: `python3 tools/makerworld-ara.py "<MARKA>"`   (→ design_id; anahtar gerekmez)
   - Cults3D: `python3 tools/cults3d-ara.py "<MARKA>"`   (→ slug; env CULTS_USERNAME+CULTS_API_KEY gerekir)
   - MyMiniFactory: `python3 tools/myminifactory-ara.py "<MARKA>"`   (→ object_id; env MMF_KEY gerekir)
   Araç NC/OCL (satılamaz) + çöp (anahtarlık/logo/minyatür) + zaten-ekli olanları kendisi eler.
   Cults3D/MMF anahtarı yoksa araç net rapor basar → "anahtar yok" raporla, zorlama.

2. ALAKASIZLIK ELEMESİ (aday listesi üzerinde, kural):
   - Ürünün KENDİSİ bu markanın parçası/aksesuarı/ürünü mü? Değilse ELE. Örnek eleme sınıfları:
     başka takımın/markanın aracı (F1: Red Bull/Jordan/Lotus şasisi "Renault motorlu" diye girmez),
     üçüncü taraf IP'si taşıyan (Hogwarts/Disney vb. → telif), marka LOGOSU basılan alakasız eşya
     (yazıcı düğmesi, anahtarlık — ★POPULER-COP işaretliyse İSTİSNA: ekle), başlığı belirsiz olup
     detayı da alakasız çıkan.
   - **YASAK (Okan, 2026-07-16): ölçekli model / maket ARAÇLAR (otomobil-motosiklet-araç maketi,
     "scale model") ve LEGO ile ilişkili HER ürün (uyumlu/benzeri dahil) — lisans uygun olsa bile
     EKLENMEZ, atla+bildir.** (Eski "markanın tarihî ürünü maketi meşru" istisnası KALDIRILDI.)
   - **YASAK (Okan, 2026-07-16): BASKIDA LOGO.** Çıktısı logo/amblem olan ya da logo kabartması
     taşıyan ürün (logo kurabiye kalıbı, amblem, rozet, logolu anahtarlık) EKLENMEZ. Test:
     "logoyu çıkar → satılır ürün kalır mı?" ★POPULER-COP istisnası bu sınıfı DELEMEZ.
   - EMİN OLAMADIĞIN her adayı ekleME; rapora "yargı listesi"ne yaz (gerekçeyle) — mimar karar verir.

3. EKLE: kalan ID/slug'ları tek komutta:
   - Printables: `python3 tools/printables-ekle.py <id...>`  (cache `pr<id>`)
   - Thingiverse: `python3 tools/urun-ekle.py <id...>`  (cache `<id>`)
   - MakerWorld: `python3 tools/makerworld-ekle.py <design_id...>`  (cache `mw<id>`; ölçüsüz)
   - Cults3D: `python3 tools/cults3d-ekle.py <slug...>`  (cache `c3d<slug>`; ölçüsüz; API anahtarı gerekir)
   - MyMiniFactory: `python3 tools/myminifactory-ekle.py <object_id...>`  (cache `mmf<id>`; ölçüsüz; API anahtarı gerekir)
   İLK PARTİ 3-5 ID ile dene; tablo düzgünse kalanını ver. Araç STAGE eder, COMMIT ETMEZ.
   (MakerWorld/Cults3D/MyMiniFactory'de önce `--kuru <id...>` ile canlı ön-kontrol yapabilirsin.)
   - **`urun-ekle.py` / `printables-ekle.py`'yi SENKRON (foreground) koştur, ARKA PLANDA
     BIRAKMA — orphan process + poll/popup'a yol açar (Thingiverse partisinde yaşandı,
     maraba erken öldü).**

3b. OTOMATİK DENETİM (elle dedup/lisans/logo/ölçü yerine): `python3 tools/denetim-kapisi.py`
   (report-only; rapor `.thing-cache/denetim-kapisi-rapor.json`). Kapılar: lisans (fail-closed),
   maket/ölçekli araç (auto_sil), logo/amblem (eskalasyon — "logoyu çıkar" yargısı), ölçüsüz
   (auto_sil), görsel çakışma + dedup (eskalasyon/auto_sil), marka kirliliği (rapor). `eskalasyon`
   + `marka_kirli` = yargı listene; `auto_sil` + `dedup.sil` net → `--uygula` ile `duzelt.py`
   üzerinden kaldırılır (elle silme YOK).

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
     **İSTİSNA — ÖLÇÜSÜZ kaynaklar (********/MakerWorld/Cults3D/MyMiniFactory):** ölçü satırı
     BEKLENMEZ, indirip ölçmeye ÇALIŞMA; denetim-kapisi bu kaynakları ölçü kapısından muaf tutar.
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
