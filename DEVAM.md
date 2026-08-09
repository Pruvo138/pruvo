# DEVAM (KraL) — 8 Agu 2026

## ✅ KAPANDI — CI kapsam kapısı keşif körlüğü (9 Ağu 2026, merge `22c5861a`)
Dal `claude/nice-wu-1c2bc9` → main (`2d653f9f..22c5861a`), 10 dosya +3002/−35.
**Kök kusur:** `tools/ci-kapsam-test.py` keşfi yalnız `git ls-files` üzerindeydi → yeni bir
`*-kapisi.py` yazan mimar `git add`'den ÖNCE kapıyı koşarsa rc=0 "YEŞİL" alıyordu; kırmızı ancak
push sonrası bloklamayan nöbet şeridinde konuşuyordu.
**Kabul (ana checkout + dal worktree'sinde aynı kanıt):** `git add` edilmemiş yeni `*-kapisi.py` →
kapı **rc=1** + `HENUZ IZLENMIYOR (kapsamsiz)` etiketi; dosya silinince **rc=0**.
**Seçim ölçümle:** izlenmeyen keşif kovası ZORUNLUYDU — pre-push tek başına körlüğü kapatmıyor
(commit anında dosya zaten `git ls-files`'ta, ölçüldü). İkisi de yapıldı: pre-push'a fail-closed
kapsam kolu eklendi (P95 4,3 sn ≤ 5 sn eşiği).
**10 tur çürütme, kapatılan sınıflar:** kablo iddiası (özellik duruyor, kablosu yok) · pre-push
hükmü kabuk taklidinden **gerçek `sh` / gerçek `git push`**'a · ortam sadakati (git kanca ortamı) ·
hüküm ezme sözdiziminden **davranışa** (nöbetçi zorla False → kolun rc'si) · fail-slow → fail-fast
(guard `return` + 30 sn tavan) · evren ad deseninden **çağrı grafına** (yanlış-poz 6→0, yanlış-neg 6→0).
**Sayılar:** mutasyon sürücüsü **9 → 63 iddia** · bloklayıcı yüzey bayraksız 15 + kanca-kablo kolu 3,
birleşim 18 (taban 18, eşitlik) · kalıcı fuzz 48 varyant, sapma 0 · üç kanonik sayı **253 keşif ·
56 muaf · 213 .py + 40** (dalın etkisi 0; artış merge'in getirdiği dosyalardan) · kapı envanteri 7/7 ·
kanca kablolama 62 iddia.
**Maliyet:** pre-push medyan 3,9 / P95 4,3 sn (eşik 5) · kanca-kablo kolu 12,5–13,4 sn (tavan 60, CI).
**Merge sonrası doğrulama:** kanca kurulumu sonrası kanca nöbeti **rc=0 (15/15)** · ana checkout'ta
5 kapı rc=0, `MUTANT=63/63` · D1 dört eksen yeşil (23275==23275, `urun_hash` uyuşmaz 0) · koşum
`31311137432`: `build`/`serit-a2`/`serit-a3`/`serit-a4`/`deploy` **hepsi success** · 🔴 `serit-a3`
adım #13 (45 gerçek `git push`) main'de **İLK KEZ KOŞTU**: success, 2 sn · canlı
`https://pruvo3d.com/` **200, TAZE** (last-modified deploy sonrası).

**AÇIK KALAN / AYRI İŞLER (dalın kusuru DEĞİL, ölçüldü):**
1. `yayin` job'u kırmızı: `ADAY SAYISI TAVANI ASTI: 531 > 300` göç yığını (D1'de yerel karşılığı
   olmayan taslak satır). Hükmün kendisi yeşil, çıkış kodu tavandan; `needs: deploy` olduğu için
   **yayını bloklamadı** (site taze). Katalog/D1 düzlemi — MaCiT. Kapı çözümü kendi basıyor:
   `tools/yayin-kapisi.py --geriye-doldur`.
2. Parite `parite-test.js` / `parite-ege.js` **rc=3 = ÖLÇÜLEMEDİ** (KIRMIZI DEĞİL): ayrışım 0
   (site 1199, Ege 850, açıklanamayan 0); sebep taslak yığını sayfa probu tavanı. Pristine main'de
   birebir aynı ölçüldü → dalın etkisi 0. Yayın penceresi açılınca yeniden ölç.
3. İki alarm şeridi kırmızı, ikisi de **yayını bloklamıyor** ve kökü aynı: canlı shop worker kodu
   main'den geride (eşik aşımı). Düzeltme = worker deploy → **OKAN KAPISI**. Biri 8 Ağu'dan beri
   kesintisiz kırmızı, diğeri saf saat aşımı (önceki 11 koşum success).
4. Worktree `.claude/worktrees/nice-wu-1c2bc9` **KALDIRILMADI** — turu koşan oturum hâlâ içindeydi.
   Dal main'de (içerik doğrulandı, 10 dosya). Sıradaki tur: `git worktree remove` + `git branch -D`.
5. Ana checkout'ta başka oturumların izlenmeyenleri duruyor — DOKUNULMADI.
6. Kanca-kablo kolu süresi dört turda 8,5 → 13,4 sn arttı (tavan 60); trend izlenmeli.

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
