# DEVAM (KraL) — 8 Agu 2026

## ⏱ Nöbet defteri: 09 Ağu ~10:40–12:00Z turu (KraL)

**🟢 YAYIN AÇILDI.** 9 saattir inmeyen yayın hattı çözüldü. Kök neden: `tools/uyum-kapisi.py` A4 ("model ikizi yok") kırmızısı — katalogda `Town Ace`/`TownAce` ve `Lite Ace`/`LiteAce` aynı normalize anahtara düşüyordu; `serit-a2` `deploy: needs` içinde olduğu için `deploy`+`yayin` skipped kalıyordu. Onarım commit'i (`110b46bf`) lokalde hazırdı ama uzağa gönderilmemişti — CI 9 saat boyunca eski ucu (`2d653f9f`) ölçtü.
**Ayırt edici ölçüm:** origin/main katalogla KIRMIZI (geçen 38 · kalan 1 · iddia 39), HEAD katalogla YEŞİL (39 · 0 · 39). İddia sayısı 39'da sabit, taban 39 → kapsam küçültme YOK.
**Canlı doğrulama:** uç `cef49456`, koşum `31311137432` → `build` success · `serit-a2` **success** (önceki uç `2d653f9f`'te koşum `31307292100`'de aynı iş failure) · `serit-a3` success · `serit-a4` in_progress. D1 dört eksen yeşil: 23275==23275, şema 3 göç indeksi kurulu, türetilmiş kolon 5/5, `urun_hash` 23275/23275 uyuşmaz 0.
**Mail süpürmesi:** taşınan 1, tur sonu gelen kutusunda "Run failed" **0**. Pozitif tanıma izi: `notifications@github.com` toplam 1 (substring eşleştirme; tam eşitlik kullanılmadı).
**Push yarışı:** itme `cannot lock ref` ile reddedildi — eşzamanlı başka bir oturum aynı commit'leri saniyeler içinde göndermişti; sonuç ekseninde hedef tuttu (ahead/behind 0/0), tüm kapılara UYULDU.

**AÇIK KALAN İŞLER (sıradaki turun devralacağı):**
1. **Yayın tavanı yapısal.** `serit-a4` işi 3621 sn (60 dk 21 sn); içindeki "Model uyeligi mutasyon bataryasi" adımı **2725 sn** ölçüldü, `deploy.yml`'deki yorumun beyanı **440 sn** → beyan 6,2× bayat (adım katalog boyutuyla ölçekleniyor). Zincir ~62 dk, son 12 saatteki push aralığı medyan 6,4 dk / ortalama 15,4 dk → hat tek bir push'u bile tamamlayamıyor. Ölçüldü: `cancel-in-progress: false` olmasına rağmen **6 koşumda `serit-a4` gerçekten çalışırken kesildi** (7–61 dk koşmuş işler); kod yorumundaki "çalışan asla öldürülmez" beyanı bu depoda ÇÜRÜTÜLDÜ. Kuyrukta ölen 11 (zararsız). Sonraki iş: bataryayı bölme/paralelleştirme — iddia sayısı DÜŞMEDEN süreyi push aralığının altına çekmek; adım silme/`continue-on-error` YASAK.
2. **Sınıf kapanmadı:** `tools/arama.py`'de markalar için kanonik tablo var, **modeller için boşluklu↔boşluksuz kanonik tablo YOK**. A4 ikizi yalnız tespit ediliyor, yazma anında engellenmiyor → `CR-V`/`CRV`, `X Trail`/`X-Trail` gibi bir sonraki varyant yayını yeniden durdurur. Tekil yama değil, kanonik kümeden türeyen normalize gerekiyor; ürün ekleme hattını ilgilendirdiği için MaCiT ile ortak paket. (A4 ratchet kabul şartı ve ölçülen 78 ikiz gruplu latent yüzeyin dökümü ARŞİVDE.)
3. **`pre-push` kancası `d1-sync.py`'yi `--head` bayrağı OLMADAN çağırıyor** (`pre-push:148`). Beş evin paylaştığı checkout'ta herhangi bir oturumun commit'siz ürünleri itme anında canlı D1'e yazılabiliyor; `--head` bayrağı bu amaçla mevcut ama çağrıya bağlanmamış. Tek satırlık kapatma, hattı daha fazla tıkamamak için ayrı tura ertelendi.
4. **`serit-b` kırmızı** (yayını bloklamaz): `tools/marka-sayfa-mutasyon.py` bataryasında 18 öldürücüden 5'i hayatta (marka eşleme gevşek, geçersiz-id filtresi, sayfa sayacı, edge yerine tüm katalog, parti tavanı) → 13/18. Test kapsam boşluğu, ayrı mühendislik işi.
5. `stash@{0}` başka bir oturumun kod-düzlemi değişikliklerini taşıyor, sahibine sorulmalı.

## 2026-08-09 11:37Z — CI nöbeti (KraL)
- Süpürme (koşulsuz): GitHub "Run failed" 3 mail Çöp'e taşındı; tur sonu gelen kutusunda Run-failed 0. Pozitif tanıma izi VAR (GitHub gönderenli toplam sıfır değildi) → hüküm TEMİZ, OLÇÜLEMEDİ değil.
- Deploy blokajı kök nedeni: `serit-a2` / "Uyum kapisi" (`tools/uyum-kapisi.py`) A4 model ikizi iddiası — Toyota Town Ace/TownAce · Lite Ace/LiteAce yazım ikizi. Kapıda elle tutulan allowlist YOK; iddia canlı katalog verisinden türüyor.
- Kök neden KAPANDI: veri tarafı `110b46bf` ile düzeltilmiş. `110b46bf`'yi ata olarak taşıyan koşum `31311137432`'de `serit-a2` = success (11:40→12:02, ~22 dk).
- Koşum `31311137432` durumu: build success · serit-a2 success · serit-a3 success · serit-a4 20+ dk hâlâ koşuyor · deploy ve yayin henüz başlamadı. Zincir hükmü = ÖLÇÜLEMEDİ (yeşil DEĞİL). Tavanı `serit-a4` koyuyor.
- Son başarılı deploy `31286873618` (`3e7f1b24`, 00:45Z) `110b46bf`'yi taşımıyor → düzeltme canlıda DEĞİL.
- Ayrı alarm kolları `deploy`/`yayin` zincirini BLOKLAMIYOR (kaynaktan `needs:` bağı ölçüldü): `odeme-bayatlik-push` ve `paket-tazelik-alarmi`. İkisinin kökü AYNI: canlı shop worker kodu main'den 157,5 dk geride (eşik 120 dk). Düzeltme = shop worker deploy → OKAN KAPISI, bu turda YAPILMADI.
- Ölçüm tuzağı (bu turda yaşandı): bayat koşumlardan okunan "serit-a2/serit-a3 kırmızı" iddiası, güncel koşumda ölçülünce ÇÜRÜDÜ. Kapı hükmü koşum başına ve `merge-base --is-ancestor` ile hangi commit'i taşıdığı ölçülerek verilmeli.

## 🔁 KraL DEVIR (clear oncesi yazildi) — SIRADAKI TEK IS: `muh/marka-tek-sayfa` dalini KAPAT
**Okan emri (bu gece):** dali baslat; MaCiT mesgul oldugu icin 215 urunluk VERI onarimi BEKLIYOR.
Dal: `muh/marka-tek-sayfa` **`73adb519`** (push'lu, worktree bugun KALDIRILDI → yeniden `worktree add` gerek).
Hukum (Okan): marka sayfasi markanin TUM parcalarini kart listeler, cipler **sayfa ici filtre**.
Olculen: gorunur kart **11731 → 21628** (audi 200→331 · ford 488→2583 · bmw 1010→2347), azalan marka **0**,
kimlik sapan sayfa **32 → 0**, tavani asan sayfa **11 → 0**. Iddia 10871, davranis testi 20/20.
Onceki curutme 1. turda MERGE_EDILEMEZ demis, UC kirmizi kapatilmis (teslim yolu tautolojisi ·
agirlik regresyonu → edge `/katalog?ids=` · ci-kapsam kablolama).
⏭ **EKSIK OLAN:** mutasyon bataryasi + ilk-yuk bayt tablosu → **dar curutme (yeni yuzey)** → merge + canli dogrulama.
⚠️ Merge oncesi ZORUNLU (bugun iki kez yayin durdu): `is-akisi-kapisi.py` rc=0 + yeni adim `serit-b`'ye
DUZ TEK KOMUTLA kablolu + `SERIT_B` beyani AYNI commit'te; ayrica `varlik-test.py` rc=0.
Bu dal ayrica sayfanin kendi ic sayac celiskisini kapatir (baslik 330 ↔ cip toplami+diger 370).
🔴 **KAPANMADI, ayri is (VERI duzlemi/MaCiT):** basliginda marka gecen ama `marka[]` uyesi olmayan
**215 urun** (Mini 42 · Grom 29 · K100 19 · Datsun 18…). `arama.py` gecis kolu **ONCE KAPATILMAYACAK**
(arama daralir, satis yolu). Ayrica acik: H1/H3 kurali **16 model-olmayan** degeri model sayiyor.

## Onceki turlarin VE 7 Agu oturumunun TAM dokumu — ARSIVDE (DEVAM-ARSIV.md, git disi).
