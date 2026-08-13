# PRUVO — ÜRÜN EKLEME REHBERİ (yeni oturum önce BUNU oku)

> Bu dosya, "resim tek ekleniyor / STL'den ölçü alınmıyor / dosyalar doğru yere kaydedilmiyor"
> gibi tekrar eden hataları önlemek için var. Ürün eklemeye BAŞLAMADAN önce baştan sona oku.
> Mekanik işi tek komut yapar: **`python3 tools/thing-hazirla.py <id> [<id> ...]`** (görselleri
> indirir + STL'leri `stl/`+Drive'a kaydeder + ölçü verir). Onu kullan, sıfırdan script yazma.
>
> 🔴 **12 Ağu 2026:** yayını durduran 6 alan kuralı ve "ekledikten sonra koş" listesi
> **[bölüm 9](#9-yayini-durduran-alan-kurallari-12-ağu-2026-ölçüldü)**'da. Bunlar 8 Ağu'dan sonra
> eklendi ve rehberde geçiş sayısı **0** idi (ölçüldü) — ürüne dokunmadan önce oku.

---

## 0) ALTIN KURALLAR (ihlal = hata)
1. **ONAY/SORU YOK.** Okan link + fiyat verir; sen yaparsın. `AskUserQuestion` KULLANMA. Belirsizse
   en makul varsayımla DEVAM et. Sonda tek satır: **"N ürün eklendi. ✅"** (uzun özet yazma).
   Tek istisna: tüm ürünleri silme gibi yıkıcı/geri alınamaz işlem net değilse kısa teyit.
2. **KOMUT STİLİ (değişkensiz).** Bash'te ASLA `$VAR`, `for ...; do ... $x ...; done`, `$(...)`,
   `cd`, `>` yönlendirmesi, `<<EOF` heredoc, `cat >`/`printf >` KULLANMA — hepsi `bypassPermissions`
   ile bile geçilemeyen onay penceresi açar. Döngü gerekiyorsa **Python `.py` içinde** yap, dosyayı
   **`Write` tool'u** ile yaz, düz `python3 /tam/yol.py` ile çalıştır. Çoklu id alan araçlar zaten var
   (`thing-meta.py`, `thing-hazirla.py` birden çok id alır) → for-döngüsüne gerek yok.
3. **HER ÜRÜNE 3-4 GÖRSEL.** Tek görselle asla bırakma (galeride gerçekten 1 varsa istisna).
4. **STL'DEN ÖLÇÜ AL** ve açıklamaya yaz.
5. **DOSYALARI DOĞRU YERE KAYDET** (aşağıdaki tablo). `thing-hazirla.py` STL'i otomatik doğru yere koyar.

---

## 1) ADIM ADIM

**a. Lisans + metadata:** `python3 tools/thing-meta.py <id> [<id> ...]`
   - Lisans **satılabilir mi?** SAT: CC BY, CC BY-SA, CC0/Public Domain, BSD, GNU GPL,
     CC BY-ND (fiziksel çoğaltma serbest — açıklamada "aynen üretilir", türetme yok).
   - **SATMA (atla + kısa bildir):** CC BY-NC, CC BY-NC-SA, CC BY-NC-ND, ve tasarımcı metninde
     "non-commercial" diyen CC BY-ND. Ticari kullanım yasak = satamayız.
   - CC lisanslıysa objeye `"lisans": {"tasarimci":"<ad>","tur":"CC BY 4.0"}` ZORUNLU (atıf yasal).
     CGTrader royalty-free'de `lisans` konmaz. CC0'da `lisans` konmaz (nota "CC0" yaz).
   - **YASAK ÜRÜN TÜRLERİ (Okan, 2026-07-16 — lisans uygun olsa bile EKLEME, atla+bildir):**
     (1) **Ölçekli model / maket araçlar** (otomobil-motosiklet maketi, "scale model", display
     model). Muadil/yedek PARÇA işimizdir, aracın MAKETİ değil. (2) **LEGO ile ilişkili her
     ürün** (lego uyumlu, lego benzeri, minifigür vb. — marka/lisans riski). 16 Tem'de bu iki
     gruptaki mevcut ürünler siteden toplu silindi; geri eklenmez.
     (3) **BASKIDA MARKA LOGOSU olan hiçbir ürün** (Okan: "hiçbir logoyu baskı yapmıyoruz").
     Çıktının kendisi logo/amblem olan ya da üzerinde logo kabartması taşıyan her şey: logo
     kurabiye kalıbı (Toyota vb.), amblem/rozet, logolu anahtarlık... Test: "logoyu çıkar →
     satılır ürün kalır mı?" Kalmıyorsa YASAK; kalıyorsa logosuz halini anlat/ekle. Popülerlik
     istisnası (★POPULER-COP) bu sınıfı DELEMEZ.

**b. Hazırlık (tek komut):** `python3 tools/thing-hazirla.py <id> [<id> ...]`
   - Çıktı: her id için TASARIMCI, LİSANS, indirilen görsellerin **yerel yolları**, her STL'in ölçüsü
     ve en büyük parçanın ölçüsü. STL'ler `stl/` + Drive'a otomatik kaydedilir.
   - Ayrıca her id için `.thing-cache/<id>/meta.json` yazar (Gemini yardımcısı bunu okur).

**b2. GEMINI YARDIMCISI (token diyeti — TERCİH EDİLEN yol):**
   `python3 tools/thing-gemini.py <id> [<id> ...]` (önce b çalışmış olmalı).
   - Görsel-seçme + Türkçe içerik yazmayı **Gemini'ye devreder** → bu iş Claude bağlamına girmez, token yakmaz.
   - Döner (küçük JSON, `.thing-cache/<id>/oneri.json`): `sec_gorseller` (seçili 3-4 görsel, en iyi ilk),
     `elenen`, `baslik`, `aciklama` (ölçü satırı dahil), `kategori`, `marka`, `not`.
   - Bu JSON'u OKU (görselleri `Read` ETME). Öneriyi hızlıca gözden geçir: kategori/marka mantıklı mı,
     açıklama "3D baskı" demiyor mu, uydurma özellik var mı. Küçük düzeltmeyi sen yap.
   - `sec_gorseller` yollarını doğrudan (f) adımında R2'ye yükle.
   - `.gemini-key` yoksa / Gemini hata verirse → aşağıdaki (c) manuel yola düş.

**c. (FALLBACK) Görselleri GÖZLE İNCELE:** çıktıdaki `Read: .thing-cache/<id>/gN.jpg` yollarını **`Read` tool'u**
   ile aç, bak. **3-4 iyi görsel seç:**
   - Gerçek/araca takılı/elde tutulan **fotoğrafları tercih et** (güven verir).
   - Sadece render varsa temiz render kullan; ama gerçek foto varken salt-render'la yetinme.
   - **Ele:** tasarımcı logosu/filigranı, üzerinde yazı/CAD arayüzü (Gemini ✦ parıltısı vb.),
     "Access Denied"/çok küçük/bozuk, birebir duplike, alakasız görseller.
   - Filigran köşedeyse `Pillow`/`sips` ile kırpabilirsin (scratchpad'e küçük `.py` yaz).

**d. Ölçüyü açıklamaya yaz:** `Yaklaşık dış ölçüler: A × B × C mm.` (helper'ın verdiği en büyük parça).
   Çok parçalıysa mantıklı olanı seç (ör. plaka setinde plaka ölçüsü). STL yoksa ölçü satırını yazma.

**e. Türkçe içerik:** başlık + açıklama (ferah, maddeler `\n`'li) + kategori + marka (dizi).
   Kategori kuralları CLAUDE.md'de — araç-marka özel parça ilgili araç kategorisine (Tamirat'a değil).

**f. Seçilen görselleri R2'ye yükle** (küçült + yükle):
   `python3 tools/r2-upload.py <yerel.jpg> urunler/<id>-1.jpg` (her görsel için ayrı, `-1`,`-2`,`-3`).
   Yüklemeden önce `sips -Z 1000 -s formatOptions 80 <girdi> --out <cikti>` ile küçült.
   **ÖNBELLEK KURALI:** bir ürünün görselini DEĞİŞTİRİRKEN aynı R2 anahtarının ÜZERİNE YAZMA —
   Cloudflare eski sürümü sunar; her zaman YENİ dosya adı (`-v2`, `-kapak`).
   🔴 **8 Ağu 2026'dan beri KURAL KODDA (fail-closed):** anahtar R2'de zaten VARSA yükleyici
   **yazmaz**, anahtarı basar ve `4` ile çıkar (`https://…` satırı BASILMAZ → parti aracı
   o görseli "yüklenemedi" sayar). Doğru çözüm YENİ dosya adı + `gorseller` URL'sini
   güncellemektir. Bilerek ezmek `--ezmeye-izin-ver` ister; `--kuru-prova` hiçbir şey yazmaz.

**g. Ürünü ekle:** obje `urunler.json`'un **BAŞINA** (en yeni en üstte). `.urun-kaynaklari.json`'a
   (gitignore) kaynak: `{kaynak, link, tasarimci, lisans, tur, not, baski}`. `baski` = filament/baskı
   önerisi (kaynaktaki öneri; TPU gereken conta/burç vb. belirt).
   **Ekleme betiğini `Write` ile scratchpad'e `.py` yaz, `python3` ile çalıştır** (heredoc yok).

**h. Doğrula:** `python3 tools/mukerrer-kontrol.py` (mükerrer **id** + **başlık** + `.urun-kaynaklari.json`
   varsa **kaynak linki** tarar). Temizse `mukerrer yok: N urun tarandi` basar, çıkış 0; mükerrer
   varsa `MUKERRER <TÜR>: <değer> -> <id...>` satırları basar, çıkış 1 — o ürünü ele/düzelt.
   ⚠️ **İnline `python3 -c "..."` KULLANMA** — `komut-stili-kapisi.py` bunu makine olarak REDDEDER,
   rehberi izleyen işçi kapıya takılır (buradaki eski örnek buydu, 20 Tem düzeltildi).

**i. Yedek:** `python3 tools/yedekle.py --sirlar`

**j. Commit + push:** `git -C /Users/okan/dev/pruvo pull --quiet` → `git -C /Users/okan/dev/pruvo add urunler.json`
   → `git -C /Users/okan/dev/pruvo commit -m "<başlık>" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"`
   → `git -C /Users/okan/dev/pruvo push`. Statik sayfalar (`urun/`, sitemap) CI'da üretilir — commit ETME.

**k. D1 teyidi:** `python3 tools/d1-sync.py --durum` — push sonrası `.git/hooks/pre-push` D1'i
   otomatik senkronlar; bu komut D1'deki satır sayısını `urunler.json`'daki **benzersiz id** sayısıyla
   kıyaslar. Uyuşmazlıkta **fail-loud exit 1** döner (Ege/WhatsApp botu D1'den okur — senkron aksarsa
   site gösterir ama Ege GÖREMEZ, sessiz satış kaybı).

---

## 1b) ÇOK PLATFORM (Thingiverse dışında) — gerçekte var olan araçlar

Yukarıdaki a-k akışı **tek ürün, elle, Thingiverse** ekleme içindir. Üç kaynak aktif; her biri aynı
adaptör deseniyle bir **ara** + bir **ekle** aracına sahip (Thingiverse şablon, diğerleri eşdeğeri):

| Platform | Ara (aday id listesi verir) | Ekle (paralel, STAGE eder — **COMMIT ETMEZ**) | Token |
|---|---|---|---|
| Thingiverse | `tools/thing-ara.py "<marka>"` | `tools/urun-ekle.py <id...>` | gerekmez |
| Printables | `tools/printables-ara.py "<marka>"` | `tools/printables-ekle.py <id...>` | gerekmez (public GraphQL) |
| MakerWorld | `tools/makerworld-ara.py "<marka>"` | `tools/makerworld-ekle.py <id...>` | gerekmez (STL indirme login ister → ölçü genelde **YOK**, kaynak notuna yazılır) |

`urun-ekle.py` / `printables-ekle.py` / `makerworld-ekle.py`: id'leri **paralel** işler (hazırlık →
lisans/NC kapısı → `thing-codex.py` ile görsel seçimi + Türkçe içerik + fiyat önerisi → seçili
görseller R2'ye → `.urunler.lock` **flock** altında `urunler.json`'u o an yeniden okuyup STAGE eder).
Yukarıdaki **b2** adımındaki `thing-gemini.py` farklı bir yardımcıdır (tek-ürün elle akışı için);
bu toplu/çok-platform orkestratörler içerik üretimini `thing-codex.py` üzerinden yapar.

**Marka bazlı toplu ekleme artık genelde slash komutlarıyla MARABAYA (Sonnet) devrediliyor**
(`.claude/commands/tverse.md`, `printables.md`, `makerworld.md`, `urun.md`): `/tverse <marka>`,
`/printables <marka>`, `/makerworld <marka>`, `/urun <thingiverse id...>`. Bu komutlar mimarın işi
devretmesi içindir; maraba `tools/paket-marka-ekleme.md` spesifikasyonunu uygular: ara → ekle
(STAGE) → `tools/denetim-kapisi.py` (otomatik lisans/logo/ölçü/dedup/görsel/marka denetimi) →
**kabul testi** `tools/parti-kontrol.py` (yeni partideki her ürün için id/başlık/kategori/marka/
görsel/ölçü/fiyat/lisans yapısal kontrolü + mevcut ürün alan-değişikliği denetimi) **+**
`tools/mukerrer-kontrol.py` → `yedekle.py --sirlar` → pull/commit/push → `tools/marka-kapsama.py
kaydet` (hangi marka/platform çifti tarandı deftere düşer — bir markayı bir sayfada arayıp
diğerinde unutmayalım).

Bu bölümdeki araçlar aşağıdaki **5) TOPLU YÜKLEME**'deki fiyatlandırma/filtre/dedup kurallarının
YERİNE geçmez — onlar hâlâ geçerli, sadece "hangi komutla" kısmı burada güncel.

---

## 2) KAYIT YERLERİ (kritik — hepsi olmalı)

| Ne | Nereye | Not |
|----|--------|-----|
| Görseller | Cloudflare **R2** (`media.pruvo3d.com/urunler/<id>-N.jpg`) | git'e GİRMEZ; `r2-upload.py` |
| STL | `/Users/okan/dev/pruvo/stl/` **+** Drive STL (`.stl-backup-dir`'deki yol) | `thing-hazirla.py` otomatik yapar |
| Ürün verisi | `urunler.json` (dizinin BAŞINA) | tek kaynak; CI sayfaları üretir |
| Kaynak/lisans | `.urun-kaynaklari.json` (gitignore) | sipariş gelince STL indirmek + atıf için |
| Yedek | `yedekle.py --sirlar` → Drive backup | hafıza + kaynak + STL |
| Görsel önizleme | `.thing-cache/<id>/` (gitignore) | sadece incelemek için |

---

## 3) ZORUNLU KONTROL LİSTESİ (her ürün için hepsi ✔ olmalı)
- [ ] Lisans satılabilir (NC/ND-nonkomersiyal değil); CC ise `lisans` alanı eklendi
- [ ] **3-4 görsel** seçildi (mümkünse gerçek/montaj fotoğrafı dahil), R2'ye yüklendi
- [ ] Görseller GÖZLE incelendi (logo/filigran/duplike/render-only ayıklandı)
- [ ] **STL ölçüsü** açıklamada ("Yaklaşık dış ölçüler: A × B × C mm")
- [ ] STL `stl/` + Drive'a kaydedildi
- [ ] Doğru kategori + marka (dizi) — araç-özel parça ilgili araç kategorisinde
- [ ] Obje `urunler.json` BAŞINDA; kaynak `.urun-kaynaklari.json`'da (`baski` dahil)
- [ ] `altkategori` / `uyum` alanı ELLE `urunler.json`'a yazılmadı; `tools/duzelt.py` ile yazıldı (bkz. **8**)
- [ ] Mükerrer id kontrolü yapıldı (`tools/mukerrer-kontrol.py`)
- [ ] Toplu/çok-ürünlük partiyse `tools/parti-kontrol.py` yeşil (bkz. 1b)
- [ ] `yedekle.py --sirlar` çalıştırıldı
- [ ] commit + push (statik sayfalar CI'da; `urun/` commit edilmedi)
- [ ] `tools/d1-sync.py --durum` ile D1 teyidi yapıldı

---

## 4) SIK YAPILAN HATALAR (bunları YAPMA)
- Tek görsel eklemek (galeri çok görselliyken). → 3-4 seç.
- STL ölçüsünü atlamak / uydurmak. → `thing-hazirla.py`'nin ölçüsünü kullan.
- STL'i `stl/` veya Drive'a kaydetmemek. → helper otomatik yapar; başka yolla indirdiysen ikisine de koy.
- Gerçek foto varken salt-render kullanmak; logo/filigranlı görsel koymak.
- Yanlış kategori (araç-marka özel parçayı Tamirat'a atmak).
- Onay/soru sormak; uzun özet yazmak.
- `for`/`$VAR`/`$()`/`>`/heredoc kullanıp onay penceresi açtırmak.
- Aynı R2 anahtarının üzerine yazıp eski (önbellekli) görselin kalması.
- Sarı rengi normal üründe kullanmak (sarı yalnız parametrik seri).

---

## 5) TOPLU YÜKLEME (arama / kategori — **fiyatları OKAN VERMEZ, SEN belirlersin**)

> **GÜNCEL NOT (20 Tem):** marka bazlı toplu ekleme artık genelde bu bölümü elle takip etmek yerine
> `/tverse`, `/printables`, `/makerworld`, `/urun` slash komutlarıyla yapılıyor → bkz. **1b) ÇOK
> PLATFORM**. Aşağıdaki fiyatlandırma/filtre/dedup kuralları hâlâ geçerli (o akış da onlara uyar);
> yalnız "hangi araçla" kısmı 1b'de güncel — bu bölümü onun YERİNE değil, EK olarak oku.

Okan tek tek link+fiyat yerine bir **arama linki / kategori / tasarımcı** verebilir ("buradaki araba
parçalarını ekle" gibi). O zaman:

**a. Sadece GERÇEK ARAÇ PARÇALARI ekle.** Şunları ELE (aksesuar/dekor/model):
anahtarlık, telefon/tablet tutucu, cupholder, kumbara, tepsi/organizer, gözlük/şemsiye/sünger tutucu,
MagSafe/şarj/dashcam/GoPro montajı, anahtar rafı, logo/amblem/badge/silüet, cookie cutter, saksı,
tam araç & ölçekli modeller, RC/Hot Wheels, süs.

**b. Lisans filtresi (bkz. 1a).** CC …-NC… (Non-Commercial) ve tasarımcı "non-commercial" diyen
ND'leri ATLA. Kaç tanesini hangi sebeple atladığını sonda kısaca bildir.

**c. Kopya (dedup).** Katalogda zaten olan tür/parçanın tekrarını ekleme (fazla göbek kapağı, hoparlör
adaptörü, gösterge podu, vites topuzu, dash blank vb. birer temsilci yeter). Yeni uid katalogda var mı
kontrol et.

**d. Toplu araçlar (for/heredoc YOK):**
   - Lisans: `python3 tools/thing-meta.py <id> <id> <id> ...` (çoklu id alır).
   - Hazırlık: `python3 tools/thing-hazirla.py <id> <id> ...` (çoklu id; görsel+STL+ölçü).
   - Görsel seçimi + R2 yükleme + `urunler.json`'a ekleme için scratchpad'e **`.py` ekleme betiği yaz**
     (döngü Python içinde), `python3` ile çalıştır. ~40'ar ürünlük partiler halinde: her partiyi ayrı
     commit + push et; parti başına `yedekle.py --sirlar`.
   - **Not:** id listesini bile `Write` tool'u ile bir dosyaya yaz; `printf > ` / `echo > ` KULLANMA.

**e. FİYATLANDIRMA (Okan vermez — parça türüne göre sen ver). Yaklaşık aralıklar:**

| Parça türü | Fiyat |
|---|---|
| Küçük klips / pim / tapa / kör kapak / grommet / vida kapağı / conta | 250 TL |
| Orta kapak / çerçeve / trim / dişli tek parça | 300–400 TL |
| Düğme / buton / bezel / knob | 300 TL |
| Kol (kapı/kaput/vites) / kolçak / mandal / handle | 400–500 TL |
| Far / sis far kapağı, büyük panel/braket/tampon parçası | 400–500 TL |
| Gösterge yuvası / vent pod (52mm) | 500 TL |
| Atölye aleti (sökme/merkezleme/hizalama/ölçüm/test) | 500–650 TL |
| Büyük/çok parçalı set (ör. alt gövde plaka seti) | 650–1500 TL (boyuta göre) |

Emin değilsen benzer mevcut ürünlere bak, mantıklı bir değer seç; Okan'a fiyat SORMA. Sonda:
"N ürün eklendi. ✅" + atlananları (NC/aksesuar/kopya) tek satır özetle.

## 6) SARI SERİ GÖRSEL (parametrik ürün kapağı) — CLAUDE.md'den taşındı 19 Tem

- **GERÇEKÇİ RENDER** (Okan kararı; SVG/vektör REDDEDİLDİ "gerçekçi değil"). **Sarıyı YALNIZ bu seride kullan.**
- **NOT (2026-07-14): Gemini ile OTOMATİK resim üretimi (`tools/gemini-render.py`, `gemini-2.5-flash-image`)
  KALDIRILDI** — $300 trial kredisi Gemini API'ye uygulanamıyor (Mart 2026 kuralı). Mevcut 18 sarı seri
  render'ı (`-ai*.jpg`) R2'de KALIR. Yeni parametrik ürün kapağı için **CODEX yalnız Okan'ın o ürün için
  açık kredi onayıyla** (eski "ürün başına bedava" varsayımı 19 Tem ölçümüyle geçersiz).
- **Yol:** varsayılan manuel render/fotoğraf → yedek manuel AI (Grok / Gemini web / Meshy=gerçek 3B / Canva)
  → Downloads → `sips` ile kırp → `r2-upload` **YENİ dosya adıyla** → `gorseller[0]` güncelle
  (`.urunler.lock` **flock** altında). Nihai hedef: sarı filamentle basıp stüdyoda fotoğrafla.
- **Çoklu-şekil prompt kalıbı** (manuel AI aracına; ailenin birden çok şekli bir arada):
  *"Photorealistic 3D product render of a group of several different matte YELLOW FDM 3D-printed [PARÇALAR],
  visible fine layer lines, arranged together on a clean warm off-white studio background, soft top-left light,
  gentle contact shadow, centered, product photography, no text"*.
  [PARÇALAR] örn: profil→"I-beam, T-slot, square tube, U-channel"; O-ring→"O-rings/seal rings, different
  diameters & cross-sections"; dişli→"spur, helical, bevel, ring gears".
- **LOGO/YAZI YOK** (AI aracının parıltısı/logosu olmasın; varsa `scratchpad/logo_temizle.py` ile köşeyi
  zeminle uzatıp temizle).

---

## 7) MaCiT'e AÇIK (20 Tem rehber düzeltmesi sırasında ölçüldü, karara bağlanmadı)

- **`.urun-kaynaklari.json` gerçekten TEK şema değil, ama net "iki şema" da değil — heterojen.**
  Ölçüm (main checkout, 8250 kayıt): baskın biçim 7 alanlı `{kaynak,link,tasarimci,lisans,tur,not,baski}`
  (7034 kayıt) ve `uyelik` alanı eksik 6-alanlı hali (1002 kayıt) dahil **en az 9 farklı dict anahtar
  kombinasyonu**, artı **12 eski düz-string kayıt**, artı birkaç minimal iskelet kayıt (`{link,uyelik}`,
  `{uyelik,varyantlar}` — muhtemelen sarı/parametrik seri üyelik-only kayıtları). `uyelik` alanı başlı
  başına ayrı bir "ikinci şema" değil, mevcut şemaya eklenen **opsiyonel** bir alan (bkz. `tools/uyelik-cek.py`);
  asıl heterojenlik düz-string + iskelet eski kayıtlarda. **Normalize eden bir migrasyon script'i
  ARANDI, YOK.** `tools/mukerrer-kontrol.py`nin `_kaynak_linki()` fonksiyonu bu yüzden üç biçimi
  (str / dict / list[dict]) ayrı ayrı defansif olarak ele alıyor.
  **Soru:** bu eski biçimleri tek şemaya normalize eden bir tek-seferlik betik yazılsın mı, yoksa
  okuyucular (mukerrer-kontrol.py gibi) hep defansif mi kalsın? Rehbere migrasyon adımı EKLENMEDİ
  (uydurmamak için) — MaCiT karar verirse buraya yazılabilir.

- **ÖLÇÜLMEDİ:** bu 9 anahtar-kombinasyonunun hangi tarih aralığında/hangi araçla yazıldığı
  (git geçmişi kazılmadı — dosya gitignore olduğu için commit geçmişi yok, sadece güncel an-kesiti
  ölçüldü). Kayıtların kaç tanesinin hâlâ `urunler.json`'da karşılığı olan ürünlere ait olduğu da
  ölçülmedi (yetim kaynak kaydı olabilir).

---

## 8) `altkategori` ve `uyum` ALANLARI — ELLE YAZILMAZ (8 Ağu 2026 eklendi)

Bu iki alan opsiyoneldir; yazılırlarsa **kapalı kümelere** uymak zorundadırlar ve tek yetkili
yazma yolu **`tools/duzelt.py`**'dir.

**`altkategori`** = kategori İÇİNDEKİ daraltma etiketi (ör. `Otomobil > Aydınlatma`).
- İzinli değerlerin **TEK kaynağı**: `arama.ALTKATEGORI_IZINLI` (`tools/arama.py`). Küme
  `urunler.json`'dan yeniden hesaplanmaz — hesaplansaydı her yeni değer kendini izinli yapardı.
- Değer, kaydın `kategori`si için izinli kümede olmalı; ayrıca **tedarikçi imza nöbetinden**
  geçmeli (marka/firma adı, vitrin adı, SKU öneki taşıyamaz — depo PUBLIC).
- Boş bırakmak GEÇERLİDİR. Alanı boşaltmak: `--alan-sil altkategori` (`" "` yazmak DEĞİL).
- Kümeyi genişletmek **MİMAR kararıdır** (`arama.py` elle güncellenir).

**`uyum`** = ürünün NEYE UYDUĞU (`kategori` "ürün NE" der, `uyum` "neye takılır" der).
- Şema: dizi; her öğe `{"marka": <ZORUNLU, kapalı kümeden>, "model"/"motor"/"oem": opsiyonel
  metin, "yil": [baş, son] ya da []}`.
- Marka kümesinin **TEK kaynağı**: `arama.UYUM_MARKA_IZINLI`. Üretici markaları (buji, tutya,
  yapıştırıcı üreticisi vb.) bu kümede DEĞİLDİR — ayrım: "bu ürün <X>'e takılır" anlamlıysa uyum,
  ürünün KENDİSİ o markanın malıysa üretici.
- 🔴 **`marka` ELLE YAZILMAZ.** `uyum` doluyken `marka`, `arama.marka_uyumdan_turet` ile
  TÜRETİLİR (= tekilleştir(uyum[].marka + uyum[].model)) ve `duzelt.py` onu AYNI işlemde kendisi
  yazar. Aynı çağrıda hem `uyum` hem `marka` vermek REDDEDİLİR (iki kaynak yarışamaz).
- `uyum` boş/yok olan eski kayıtlarda `marka` serbesttir (regresyon yok).

**Neden doğrudan `urunler.json`'a yazmak YASAK (ölçüldü, 8 Ağu 2026):** toplu ekleme yolu dosyaya
doğrudan yazıp `duzelt.py`'nin iki fail-closed kapısını birden atladı; bir partide 5 kayıt bozuk
`main`'e girdi (1 izinsiz `altkategori`, 5 elle yazılmış `marka` ikizi). Arıza **saatler sonra**
CI'da göründü, deploy atlandı, yayın 3,5+ saat kapandı. Artık **commit anında**
`tools/katalog-alan-kapisi.py` (pre-commit adım 5) INDEX'te DEĞİŞEN kayıtları aynı kanonik
fonksiyonlarla ölçer ve ihlalde commit'i durdurur.

**Doğru kullanım:**
```
python3 tools/duzelt.py <id> --alan altkategori --deger "Aydınlatma"
python3 tools/duzelt.py <id> --alan-sil altkategori
python3 tools/duzelt.py <id> --alan uyum --deger '[{"marka":"Ford","model":"Focus"}]'
```
Commit `katalog alan kapisi rc=1` ile durursa: gerekçe ekranda, id + alan + kanonik sebep ile
basılır. Gevşetme bayrağı/muafiyet listesi YOKTUR.

---

## 9) YAYINI DURDURAN ALAN KURALLARI (12 Ağu 2026 — ölçüldü)

> **Neden bu bölüm var:** rehber 8 Ağu'da kalmıştı. `tavsiyeFilament`, `konfigur`,
> `boy_secenekleri`, feed politika jetonları, görsel köken ve Skan Art — hepsinin bu dosyadaki
> **geçiş sayısı 0** ölçüldü, oysa altısı da bugün ürün eklemeyi ya da yayını durdurabiliyor.

### 9.1 `tavsiyeFilament` **DİZİ** olmak zorunda — dize yazmak 6 kapıyı kırmızı yakar
Doğru: `"tavsiyeFilament": ["PETG"]` · Yanlış: `"tavsiyeFilament": "PETG"`.
Alan liste değilse `filament_ortak.tavsiyeler` fail-closed boş liste döner (`filament_ortak.py:57`);
istemci (`secenekler.js onSecimMalzeme`) ise dizeyi **karakter karakter** gezer — iki dil sessizce
ayrışır, ürün rozetsiz kalır ve ön-seçili malzeme güvenli varsayılana düşer.
**Geçerli adlar YALNIZ `PLA · PETG · ASA · TPU`** (`filament-veri.js` içinde `"site": true` olanlar).
`"ABS"`, `"Karbon Katkılı"` ve `"TPU (esnek)"` gibi serbest metin **satılan malzeme değildir**:
alan dolu olduğu halde hiçbir ad ayakta kalmaz, tanı `taninmayan` olur ve kapı bunu sayar.
👉 **Yap:** alanı her zaman dizi yaz ve içine yalnız o dört addan seç; emin değilsen alanı hiç yazma
(kategori haritası doğru tavsiyeyi zaten türetir).

### 9.2 Dekor/`konfigur` ürününde kapak görseli **SİYAH** + `renkGorselIndeks["Siyah"] = 0`
Ön-seçili renk ayrı bir alanda durmaz; `build.py::_konfigur_varsayilan_renk` onu **kapak
görselinden** türetir. Kapağı griye almak ön-seçimi de sessizce griye çevirir.
`tools/konfigur-siyah-kapak-kapisi.py` iki ekseni ayrı ölçer: (A) türetilen renk "Siyah" mı,
(B) türetim gerçekten kapaktan mı geliyor (`renkGorselIndeks["Siyah"] == 0`). (B) olmadan (A)
kandırılabilir — `renkGorselIndeks` boşaltılırsa fonksiyon "listenin ilki" koluna düşer.
👉 **Yap:** `gorseller[0]`'ı siyah render yap ve `renkGorselIndeks`'te `"Siyah": 0` yaz.

### 9.3 Dekor ürünü ekledikten sonra bundle üret + Worker'ı yeniden yayınla
Worker konfigür fiyatını `shop/src/konfigurlar.js` **artefaktından** okur (tüm `urunler.json`
bundle'a girmez). Artefakt tazelenmezse o üründe kart ödemesi **400** verir ve müşteri
WhatsApp'a düşer — 29 Tem'de bu iki kez iş kaybettirdi.
👉 **Yap:** `python3 tools/konfigur-bundle-kapisi.py --yaz` **+** `npx wrangler deploy --config
shop/wrangler.toml`. İkisi de yapılmadan dekor ürünü "eklendi" sayılmaz.

### 9.4 `boy_secenekleri` **KULLANILMAZ** (bugün taşıyan ürün sayısı: 0)
Alan üç yerde birden yarım: ürün sayfası boy seçtirir, edge kartı boy farkını **0** sayar, ödeme
sunucusu kalemi baştan reddeder (`boy-desteklenmiyor` → `index.html:2336`). Yani müşteriye
seçtirilen boy ne fiyata yansır ne de ödenebilir.
👉 **Yap:** alanı yazma. Gerekiyorsa önce **D1 kolonu + `kart_ozeti` + Worker `KART_ALANLARI`**
üçü birden açılmalı — bu bir MİMAR kalemidir, ürün ekleyenin işi değildir.

### 9.5 Feed politika jetonları başlığa/açıklamaya GİRMEZ
Yasak kelimeler: **elektronik sigara · e-sigara · vape**. `tools/feed-politika-kapisi.py`
bloklayıcıdır; giren **tek kelime** feed'i ve dolayısıyla **tüm ekibin yayınını** durdurur.
👉 **Yap:** ürün gerçekten bu sınıftaysa **ekleme**; benzer bir aparatsa (ör. kutu/tutucu) metni
jetonsuz yaz ("taşınabilir cihaz tutucusu" gibi).

### 9.6 Skan Art ürününde **köken manifesti ŞART**
Kategori `Skan Art` + görselli her ürün için `<koken-dizini>/<urun-id>.json` olmalı ve içindeki
`kaynak_stl` + `taban_render` dosyaları **diskte gerçekten** bulunmalı. Zorlama CI'da değil
**yazım anında**dır (`urun-ekle.py merge_safe` → `gk.zorla` → `KokenIhlali` → hiçbir şey yazılmaz).
Köken dizinleri artık **BİRLEŞTİRİLİYOR** (12 Ağu onarımı): `pruvo/urun-gorsel-koken` **ve**
`pruvo-jenerator/urun-gorsel-koken` birlikte taranır. Önceden yalnız ilki okunuyordu ve TeKiN'ın
12 manifestlik deposu görünmüyordu: **YEŞİL 0/16 → onarımdan sonra 5/16**. Kalan 11'in **10'u
gerçekten manifestsiz**, **1'i** (`capa-…`) manifestli ama `kaynak_stl` diskten silinmiş —
bu iki sınıf `gorsel_koken.py --denetim` çıktısında ayrı ayrı basılır.
👉 **Yap:** eklemeden önce `python3 tools/gorsel_koken.py --denetim` koş; ürünün adı YEŞİL
değilse manifesti (ya da eksik STL/render dosyasını) **TeKiN'dan** iste — manifest TeKiN'ın
düzlemidir, `pruvo-jenerator`'a sen yazmazsın.
> ⚠️ Aynı id iki dizinde **farklı** içerikle varsa kapı fail-closed kırmızı yakar (hangisinin
> gerçek köken olduğu aracın kararı değildir). Fazlalığı sil ya da içerikleri eşitle.

### 9.7 EKLEDİKTEN SONRA KOŞ (sırayla)
| # | Komut | Ne zaman |
|---|-------|----------|
| 1 | `python3 tools/mukerrer-kontrol.py` | her zaman |
| 2 | `python3 tools/parti-kontrol.py` | toplu/çok ürünlük parti |
| 3 | `python3 tools/gorsel_koken.py --denetim` | Skan Art ürünü varsa |
| 4 | `python3 tools/konfigur-siyah-kapak-kapisi.py` | `konfigur` alanı olan ürün varsa |
| 5 | `python3 tools/konfigur-bundle-kapisi.py --yaz` | `konfigur` alanı olan ürün varsa |
| 6 | `npx wrangler deploy --config shop/wrangler.toml` | 5. adım artefaktı değiştirdiyse |
| 7 | `python3 tools/yedekle.py --sirlar` | her zaman |
| 8 | commit + push (`urun/` COMMIT EDİLMEZ) | her zaman |
| 9 | `python3 tools/d1-sync.py --durum` | push'tan sonra, her zaman |

3-6 arası adımlar **ürün tipine bağlıdır**; 1, 2, 7, 8, 9 atlanmaz. Kırmızı bir adımı geçip
sonrakine gitme — kapıların hepsi fail-closed'dır ve gevşetme bayrağı yoktur.

---

## 10) KANONİK KAPILARIN TAZELİK LİSTESİ (12 Ağu 2026 — araçlardan türetildi)

Ayırma ölçütü: `kapi-envanteri.py` ile `ci-kapsam-test.py` keşif kümelerindeki araçlardan ilk
belge satırı ürün verisi/katalog/görsel/R2/D1/mükerrer/denetim/feed/marka-sayacı eksenine değenler
ve ürün commit'inin izlenen pre-commit zincirindeki araçlar alınır; elle ikinci kapı listesi tutulmaz.

| Kapı | Ne zaman koşulur · tam komut · kırmızı ne demek |
|---|---|
| `ara-maliyet-kapisi.py` | Katalog/D1 arama yolunu değiştirdikten sonra: `python3 tools/ara-maliyet-kapisi.py`; kırmızı, sorgunun maliyetli tam taramaya düştüğünü gösterir. |
| `canli-saglik-kapisi.py` | Push ve D1 teyidinden sonra: `python3 tools/canli-saglik-kapisi.py`; kırmızı, depo/D1 ile müşterinin gördüğü canlı yüzeyin ayrıştığını gösterir. |
| `cron-nabiz-kapisi.py` | D1 uzlaştırma nöbetini etkileyen partiden sonra: `python3 tools/cron-nabiz-kapisi.py`; kırmızı, katalog sapmasının zamanında denetlenmediğini gösterir. |
| `cta-denge-kapisi.py` | Ürün kartı/sayfası çıktısını etkileyen değişiklikten sonra: `python3 tools/cta-denge-kapisi.py`; kırmızı, temel çağrıların görsel dengesinin bozulduğunu gösterir. |
| `d1-fiyat-parite-kapisi.py` | Fiyat veya seçim alanı taşıyan ürün ekledikten sonra: `python3 tools/d1-fiyat-parite-kapisi.py`; kırmızı, vitrin ile D1 fiyat kapsamının ayrıştığını gösterir. |
| `d1-sapma-kapisi.py` | D1 senkronu/uzlaştırması sonrasında: `python3 tools/d1-sapma-kapisi.py`; kırmızı, katalog ile D1 arasında açıklanamayan sapma bulunduğunu gösterir. |
| `devam-sinif-kapisi.py` | Commit öncesi izlenen notlar değiştiyse: `python3 tools/devam-sinif-kapisi.py --index`; kırmızı, izlenen dosyaya gizli sınıf veri girdiğini gösterir. |
| `diriltme-kapisi.py` | Ürün verisi değişen her committe: `python3 tools/diriltme-kapisi.py --index`; kırmızı, daha önce kaldırılmış bir ürünün geri geldiğini gösterir. |
| `gorselsiz-render-kapisi.py` | Görselsiz kayıt eklenmiş veya render yolu değişmişse: `python3 tools/gorselsiz-render-kapisi.py`; kırmızı, görselli/görselsiz ürün yüzeylerinden birinin bozulduğunu gösterir. |
| `gramer-artigi-kapisi.py` | Başlık/açıklama toplu yazılmışsa: `python3 tools/gramer-artigi-kapisi.py`; kırmızı, katalog metninde toplu dönüşüm artığı bulunduğunu gösterir. |
| `ic-rapor-index-kolu.py` | Her ürün commitinden hemen önce: `python3 tools/ic-rapor-index-kolu.py`; kırmızı, izlenen indekste yayımlanmaması gereken iç süreç izi bulunduğunu gösterir. |
| `kanca-kur.py` | Kanca kablolaması yoksa veya pre-commit bunu bildirirse: `python3 tools/kanca-kur.py`; kırmızı, zorunlu commit/push kancalarının kurulamadığını gösterir. |
| `kategori-kapisi.py` | Her ürün partisi tamamlandığında: `python3 tools/kategori-kapisi.py`; kırmızı, katalogda izin verilmeyen kategori değeri bulunduğunu gösterir. |
| `konfigur-canli-kapisi.py` | Konfigür alanı olan ürünün Worker yayını sonrasında: `python3 tools/konfigur-canli-kapisi.py`; kırmızı, canlı tahsilat ile ürün verisinin ayrıştığını gösterir. |
| `lcp-onculuk-kapisi.py` | Kapak/banner görsel hattı değiştiğinde: `python3 tools/lcp-onculuk-kapisi.py`; kırmızı, öncelikli görsel yükleme sözleşmesinin bozulduğunu gösterir. |
| `marka-sayac-kapisi.py` | Marka/model üyeliği etkileyen her partiden sonra: `python3 tools/marka-sayac-kapisi.py`; kırmızı, beyan edilen parça sayısı ile erişilebilir kart kümesinin ayrıştığını gösterir. |
| `mimar-commit-kapisi.py` | Ürün commitinde pre-commit zinciri içinde: `python3 tools/mimar-commit-kapisi.py --stdin`; kırmızı, ürün verisine yetkisiz katın dokunduğunu gösterir. |
| `paket-tazelik-kapisi.py` | R2 derleme paketi/eslem değiştiğinde: `python3 tools/paket-tazelik-kapisi.py`; kırmızı, R2 paketi ile main eşleminin bayat olduğunu gösterir. |
| `r2-onek-gelenek-kapisi.py` | Yeni kaynak türü veya R2 anahtar öneki kullanıldığında: `python3 tools/r2-onek-gelenek-kapisi.py`; kırmızı, anahtar öneki geleneğinin veya tek-kaynak türetimin bozulduğunu gösterir. |
| `stok-d1-kapisi.py` | Ticari hal/stok alanı taşıyan ürün eklenince: `python3 tools/stok-d1-kapisi.py`; kırmızı, D1 hattının müşteriye yanlış ticari hal vaat edebildiğini gösterir. |
| `ticari-hal-kapisi.py` | `tur` veya `gorselsiz` alanı eklenip düzeltilince: `python3 tools/ticari-hal-kapisi.py`; kırmızı, meşru düzeltme sınırlarının aşıldığını gösterir. |
| `uretim-butunluk-kapisi.py` | Push sonrası katalog sayfaları üretildiğinde: `python3 tools/uretim-butunluk-kapisi.py`; kırmızı, yayımlanan bir ürünün üretim/sayfa zincirinin eksik olduğunu gösterir. |
| `urunler-guard.py` | Ürün verisi değişen her committe pre-commit tarafından: `python3 tools/urunler-guard.py`; kırmızı, yetki/provenans korumasının ürünü reddettiğini gösterir. |

Rehberin kendisini her değişiklikten sonra `python3 tools/urun-ekleme-rehberi-tazeligi.py` ile ölç;
kırmızı, yukarıdaki kanonik keşif kümesinden en az bir aracın rehberde hiç anılmadığını gösterir.
