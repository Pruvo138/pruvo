# DEVAM (KraL) — 8 Agu 2026

## ✅ KAPANDI (ARŞİVE ALINDI) — CI kapsam kapısı keşif körlüğü, merge `22c5861a` (9 Ağu 2026)
Tam döküm + açık kalan alt işler → `DEVAM-ARSIV.md` (defter kotası 1:1, bu turda taşındı).

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

## ⏱ Nöbet defteri: 09 Ağu ~14:40–15:20Z turu (KraL)

**Mail süpürmesi:** taşınan 3, tur sonu gelen kutusunda "Run failed" 0. Pozitif tanıma izi: `notifications@github.com` toplam 3 (substring eşleştirme; tam eşitlik kullanılmadı). Taşınanların sınıfı: nöbet şeridi 1, paket/ödeme tazelik alarmı 2 — üçü de yayını bloklamayan alarm kolu.
**CI ölçümü (bağımsız, `gh`):** YAYIN_BLOKLAYAN_KIRMIZI=YOK. Son başarılı deploy koşumu `31312688468` (head `598eb8e3`). Ölçüm anında uçuşta: `31314441507` (head `220cfd6c`, `serit-a4`'te) + `31317963164` kuyrukta. 24 saatlik failure grupları: paket tazelik alarmı 25 · nöbet şeridi (SERIT B) 14 · ana zincir 12 (hepsi eski uç `cef49456`'daki `yayin` job'u, sonraki commit'te yeşile döndü) · ödeme bayatlık nabzı 6 · yayın erişim alarmı 1 · D1 uzlaştırıcı 1.
**✅ KAPANDI — öksüz `pre-push --head` onarımı devralındı ve kapatıldı.** Commit `2b0861f2`, 3 dosya (`tools/kancalar/pre-push` +40/−3 · `.github/workflows/deploy.yml` +13/−0 · yeni `tools/prepush-d1-kaynak-test.py` 331 satır). Kapatılan delik: beş evin paylaştığı checkout'ta herhangi bir oturumun commit'siz ürünleri push anında canlı D1'e yazılabiliyordu; `--head`/`--kaynak` köprüsü artık bağlı. Onarım ölmüş bir oturumun index'inde commit'siz duruyordu (mtime 16:55 / index 17:03; devralındı, "hazır" sayılmadı, yeniden çürütüldü).
**7 eksenli çürütme detayı → DEVAM-ARSIV.md** (sınıf kapısı desenine takıldı, taşındı). Özet: 18 kapı rc=0, 2 kontrol mutantı kırmızı, kablo davranışsal doğrulandı, kabul testi 21/0.
**Maliyet:** yeni adım medyan **8,1 sn**, yayını bloklayan `serit-a2` 22,7 → **~22,9 dk** (tavan 120 sn'nin çok altında). Tetiklenen koşum `31320335635`.
**🔴 YENİ SINIF ÖLÇÜLDÜ — worktree'den push paylaşılan `.git/config`'i BOZUYOR.** Onarım commit'lenirken `mimar-commit-kapisi.py` ana checkout'ta `.py` commit'ini reddetti (kaynak düzlemi worktree ister); geçici worktree yalnız commit aracı olarak kullanıldı. Worktree'den `git push` denenince kanca `GIT_DIR` ihraç etti, bir kapının sentetik fikstürü onu miras aldı ve **ana deponun `.git/config`'ine `core.bare=true` yazdı** → ana checkout'ta `git status` dahil her komut `fatal: this operation must be run in a work tree` verdi, beş evin ortak checkout'u fiilen kilitlendi. `core.bare=false` ile onarıldı, kanca kablolaması + 6 kapı yeniden yeşil doğrulandı. Bilinen sınıfın (kanca kök çözümünü bozar) **daha ağır yüzü: kanca artık PAYLAŞILAN CONFIG'E YAZIYOR.** Commit ana checkout'a fast-forward ile alındı, push ana checkout'tan atıldı, worktree+dal silindi.

**AÇIK KALAN İŞLER — sıradaki turun devralacağı (öncelik sırasıyla):**
1. **(YENİ, EN ÖNCELİKLİ)** Worktree'den push → paylaşılan `.git/config`'e yazma sınıfını kapat. Bugün worktree'den atılan HER push bu riski taşıyor ve tüm evleri kilitleyebiliyor. Kabul: sentetik fikstür ana deponun config'ine yazamasın (fikstür `GIT_DIR`/`GIT_WORK_TREE` mirasını kırsın) + kontrol mutantı kırmızı yaksın.
2. Yayın tavanı yapısal: zincir ~62 dk, `serit-a4` içindeki mutasyon bataryası tek başına ~2725 sn; push aralığı medyanı çok altında. Bataryayı bölme/paralelleştirme — iddia sayısı DÜŞMEDEN. Adım silme / `continue-on-error` YASAK.
3. Model adları için boşluklu↔boşluksuz kanonik tablo YOK (`tools/arama.py`); A4 ikizi yalnız tespit ediliyor, yazma anında engellenmiyor → sıradaki varyant yayını yeniden durdurur. MaCiT ile ortak paket.
4. `serit-b` kırmızı (yayını bloklamaz): `tools/marka-sayfa-mutasyon.py` bataryasında 18 öldürücüden 5'i hayatta (13/18).
5. Canlı ödeme worker'ı bayat (main'den ~5,5 saat geride, eşik 120 dk) → iki alarm şeridi 8 Ağu'dan beri kırmızı. Düzeltme = shop dizininden worker deploy → **OKAN KAPISI**, bu turda Okan'a iletildi.
6. `muh/marka-tek-sayfa` dalı (`73adb519`) hâlâ açık; eksik olan mutasyon bataryası + ilk-yük bayt tablosu → dar çürütme → merge.
7. `stash@{0}` ve izlenmeyen `tools/paket-deploy-kritik-yol.md` başka oturumlara ait, DOKUNULMADI.

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
