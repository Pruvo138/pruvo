# K186 — TUR 2d: `IZOLE=19/50` AÇIĞINI KAPAT + `kabul.js` EKSENİNİ ÖLÇ

TUR 2c commit'li: `3d79c31f`. Ölçülen durum:
```
IDDIA=50 DUSEN=0 MUTANT=50/50 KONTROL=50/50 IZOLE=19/50   rc=0
--sizinti  IDDIA=17 DUSEN=0 MUTANT=17/17 KONTROL=17/17 IZOLE=15/17  rc=0
ci-kapsam-test.py YESIL rc=0 · kisisel-veri-test.py YESIL rc=0
```
İki kalem kaldı. Merge ÖNCESİ ikisi de kapanacak.

---

## 1. 🔴🔴 `IZOLE=19/50` — 31 "BEYANLI İSTİSNA" KOVASI BOŞALTILACAK

**Mimar hükmü:** *"Beyan ölçüm değildir."* 31 mutant bugün "izole edilemedi, gerekçesi
şu" kovasında duruyor. Bu, deponun bilinen sınıfı: **beyan edilmiş survivor** — sessizce
istisna kovasında duran mutant **yeşil tabloyu şişirir**.

Her istisna **ikiden birine** dönüşecek, üçüncü seçenek YOK:

**(A) GERÇEK İZOLASYON KANITI.** Mutant hedef kolu öldürüyor **ve** yan vakalar yeşil
kalıyor. Yani `dusen_kume == {hedef}`. Bunun için mutantı yeniden yaz:
- Yan ekseni tetikliyorsa mutasyonu **daralt** (ör. A ekseninde: alfabeyi bozan mutant
  biçimi ve tekilliği bozmasın — vekil RNG'yi mutantın hedefine göre ayarla).
- Hedef kol zaten başka bir koşul tarafından ölçülüyorsa (ör. C2'nin B1'i de düşürmesi)
  **iddiaları ayrıştır**: ikisi aynı şeyi ölçüyorsa biri gereksizdir, sil; farklı şey
  ölçüyorsa fikstürleri ayrıştır ki mutasyon yalnız birine değsin.

**(B) `OLCULEMEDI` + SEBEP.** İzolasyon **yapısal olarak** imkânsızsa (iki iddia aynı kod
satırına bağlıysa ve ayrıştırmak yapay olurdu), o mutant **`IZOLE=OLCULEMEDI`** olarak
işaretlenir, sebebi tek cümleyle yazılır, ve **özet satırında AYRI sayılır**:
```
IZOLE=<n>/<toplam> OLCULEMEDI=<m>
```
🔴 `OLCULEMEDI` sayısı sıfırdan büyükse çıkış kodu **sıfır KALIR** (bu bir hata değil,
bir sınır beyanıdır) **ama** rapora her biri adıyla ve sebebiyle yazılır. "İstisna"
kelimesi kaynakta ve çıktıda **KULLANILMAYACAK** — ya `EVET` ya `OLCULEMEDI`.

**Hedef:** `IZOLE + OLCULEMEDI == 50`, ve `OLCULEMEDI` listesi rapora tek tek dökülmüş.
Bugünkü 31'in **çoğunun (A)'ya dönmesi bekleniyor** — özellikle A ekseni (A1–A7): vekil
RNG kontrolümüzde olduğu için oradaki mutantlar izole edilebilir olmalı.

**Sıra:** önce `--sizinti` kolunun 2 açığını kapat (bloklayıcı kol, önceliklidir), sonra
50'lik kolun 31'i.

---

## 1.5 🔴 BAĞIMSIZ DENETİM SONUCU — ÜÇ SOMUT KUSUR (tahmin değil, ölçüldü)

Bağımsız doğrulama 31 beyanı tek tek tarttı: **28 SAĞLAM, 3 ZAYIF.** Zayıf olan üçü:

### 1.5.1 🔴 `K1` MUTANTI YANLIŞ SATIRA NİŞANLANMIŞ — en ciddi
Ölçülen düşen küme: `B1, D2, D7, E1, E2, K1`. Denetim hükmü:
> "K1 mutasyonu kaynakta **null gövdeyi değil, alan doğrulama koşulunu** değiştiriyor."

Yani mutant, K1'in ölçtüğünü iddia ettiği kolu (gövde `null` iken işlenmemiş TypeError)
**mutasyona uğratmıyor**; başka bir koşulu bozuyor ve yan etkiyle 6 iddia düşüyor.
**K1'in "mutantla kanıtlandı" iddiasının dayanağı YOK.** Bu, `B4`'te kapattığımız sınıfın
aynısı (*mutasyon çapası ölü/yanlış kola nişanlanır*), bu kez ters yönde: mutant çalışıyor
ama **hedef kolu değil**.
**Çare:** K1 mutantını, `talepKaydet` içindeki **nesne guard'ına** (`if (!govde || typeof
govde !== "object" || Array.isArray(govde)) { return gecersiz(); }`) nişanla; çapa
benzersiz olsun, `dusen_kume == {K1}` olsun. Olmuyorsa `IZOLE=OLCULEMEDI` + sebep.

### 1.5.2 `C4` ve `G8` GEREKÇELERİ ÖLÇÜLEN KÜMEYİ AÇIKLAMIYOR
- **C4**: küme `C4, D1, D6, G1, K2`. Gerekçe yalnız `D6`'yı açıklıyor; `D1/G1/K2`
  düşüşleri **açıklanmamış**.
- **G8**: küme 19 elemanlı. Gerekçe "başarı koşullarının ortak ön koşulu" diyor, ama
  kümede **hata/negatif fikstürler de** var — gerekçe kümeyle uyuşmuyor.

**Kural:** gerekçe, ölçülen kümenin **HER elemanını** açıklamalı. Açıklamıyorsa gerekçe
değil, kılıftır. İkisini ya (A) gerçek izolasyona çevir, ya (B) `IZOLE=OLCULEMEDI` yap ve
**kümenin tamamını kapsayan** dürüst bir sebep yaz.

### 1.5.3 🔴 SIZINTI NÖBETÇİSİNİ **BÖLÜNMÜŞ DİZGE** İLE ATLATMA — sessiz kaçış
Ölçüldü: kanonik WhatsApp numarası kaynakta **parçalanmış** duruyor
(`"90545" + "1386526"` biçiminde), böylece `kisisel-veri-test.py` onu **göremiyor**.

Bu ne muafiyettir ne de temizliktir — **üçüncü bir yol: gizleme.** Muafiyetten daha
kötüdür, çünkü muafiyet listede **görünür**, bölünmüş dizge **görünmez**. Bugün masum bir
amaçla yapıldı (test kanonik numaraya atıf yapmak zorunda), ama kalıcı hâli bir kaçış
tekniğini repoya **öğretmek** olur; yarın başka biri aynı numarayı başka bir yerde bölerek
yazar ve nöbetçi kör kalır.

**Çare (sırayla dene):**
1. Test kanonik numaraya **hiç atıf yapmasın** — pozitif vakayı tamamen sentetik bir
   numarayla kur (nöbetçinin kalıbına uyan ama gerçek olmayan).
2. Atıf zorunluysa numarayı **tek kanonik kaynaktan çalıştırma anında oku** (kaynakta
   literal olarak durmasın) — gizleme değil, türetme olur.
3. Hiçbiri olmuyorsa **bölünmüş dizgeyi bırakma**; nöbetçiye gerekçeli muafiyet ekle
   (görünür olsun) ve rapora yaz.
🔴 Seçtiğin yolu ve **neden** seçtiğini rapora yaz. Sessiz bırakma.

---

## 1.6 🔴 MİMAR HÜKMÜ 2.2 **UYGULANMAMIŞ** — `G5` hâlâ `--sizinti` içinde

Ölçüldü:
- `tools/talep-hatti-test.py` argüman ayrıştırıcısında **`--capa` bayrağı YOK**
  (yalnız `--sizinti` ve `--phone-probe` var).
- `deploy.yml`'de talep ile ilgili **tek adım** var (`--sizinti`, satır 820-821,
  `serit-a3` içinde). G5 için ayrı adım **yok**.
- `G5` mutant haritasında `tur="test"` olarak `--sizinti` kolunda koşuyor.

Mimar hükmü açıktı: *"G5 → BLOKLAYICI, ama `--sizinti` İÇİNE DEĞİL, KENDİ ADIMI olarak.
G5 bir sızıntı iddiası değil, bloklayıcı kümenin ÜSTÜNDE meta-invaryant; sızıntı
bayrağının içine tıkarsan **eksenin adı yalan olur** ve `--sizinti` sayısı iki farklı şeyi
sayar."*

**Yapılacak:**
1. `--capa` bayrağı ekle; yalnız G5'i (ve çapa invaryantını) koşsun.
2. `G5`'i `SIZINTI_IDDIALAR`'dan **ÇIKAR** → `BEKLENEN_IDDIA_SIZINTI` **17 → 16**.
3. `deploy.yml` `serit-a3`'e **ikinci adım**:
```yaml
      - name: "Talep hatti iddia-capa invaryanti (BLOKLAYICI)"
        run: python3 tools/talep-hatti-test.py --capa
```
4. Çapa sayısı **tek kaynaktan** gelmeye devam etsin (`BEKLENEN_IDDIA` /
   `BEKLENEN_IDDIA_SIZINTI`); ikiz tanım yasak.
5. G5 mutantı, kırmızının **sebebinin** silinen iddia olduğunu göstersin: çıktı
   `OLCULEMEDI: <beklenen> bekleniyordu, <gerceklesen> kosdu` satırını **taşısın**.

---

## 2. `shop/test/kabul.js` EKSENİ — ÖLÇÜLDÜ: **YEREL Node 25, CI Node 20**

**ÖLÇÜLDÜ (bağımsız doğrulama, dosya:satır kanıtlı):**
- `deploy.yml`'deki **4** `setup-node` adımının hepsi `node-version: "20"`
  (61-63, 372-374, 813-815, 1380-1382).
- `nobet.yml`'deki **11** adımın hepsi `node-version: "20"` (362-364, 1946-1948, 3708-3710 …).
- **Yerel: `v25.8.1`.** → **AYNI DEĞİL: CI 20, yerel 25.**
- `shop/test/kabul.js` yerelde `rc=1`, sebep **ağ yokluğu** (paket kayıt sunucusuna
  erişilemiyor, wrangler kurulumu) — Node sürümü DEĞİL.

🔴 **BUNUN ANLAMI, RAPORA AYNEN GİRECEK:** bu turda alınan **bütün yerel `rc=0`'lar Node
25'te ölçüldü; CI Node 20'de koşuyor.** Yani `talep.mjs`'in 50 iddiası ve mutasyon
bataryası **CI'nın koştuğu sürümde HİÇ ölçülmedi**. Bu bir varsayım değil, ölçülmüş bir
boşluktur.

**YAPILACAK:**
1. Bataryayı **Node 20 ile de koştur** (varsa `nvm`/`fnm`/`volta`; yoksa
   `npx --yes node@20` gibi bir yol dene). Sonucu ham çıktı + rc ile rapora yaz.
   Başarırsan yerel/CI boşluğu kapanır.
2. Node 20 yerelde **elde edilemiyorsa** (ağ yok) rapora **aynen** şunu yaz:
   `OLCULEMEDI: batarya CI surumunde (Node 20) hic kosturulmadi; yerel olcumler Node 25.8.1.
   Ilk gercek Node-20 olcumu CI'nin ilk kosumunda olacak.` — ve deftere kalem açılması notu düş.
3. `python3 tools/ci-kapsam-test.py` çıktısında `shop/test/kabul.js`'in
   **`OTOMATIK'te kosulan`** listesinde geçip geçmediğini **ölç** (tahmin etme) ve yaz.
   Geçmiyorsa bu eksen **hiçbir yerde ölçülmemiş** demektir; o cümleyi aynen kullan.
🔴 "Risk düşük" **deme**.

---

## 3. KAYIT — SÖZLEŞMEYE GİREN `zorunlu` HÜKMÜ (icra K184 merge'inden SONRA)

Mimar hükmü, **bugün uygulanmayacak** (paylaşılan tablo dosyası bu dalda YOK), ama
**rapora ve HocA sözleşmesine bugünden girecek**:

- **`zorunlu` alanının kanonik sahibi UÇTUR.** Uç, "geçerli talep nedir"in tek
  otoritesidir; güvenlik ve veri sınırı orada.
- **İstemci yalnız DAHA KATI olabilir, asla daha gevşek.** Ek katılık ayrı ve **beyan
  edilmiş** bir alanla yazılır (`site_zorunlu`).
- 🔴 **İNVARYANT: `site_zorunlu ⊇ zorunlu`** — ucun zorunlu tuttuğu her alan istemcide de
  zorunludur. Kapı bunu ölçer; ihlal **KIRMIZI**.
- `kanal` tek kaynağa **girer**: uçta zorunlu, sitede otomatik doldurulur — tabloda
  öyle işaretlenir.
- Bu, **G1 çelişkisini çözer**: G1 (yalnız `kanal`+`parca_adi` taşıyan minimal talep
  `kod` ÜRETİR) uçta DOĞRU kalır; istemcinin marka/model ısrarı artık çelişki değil,
  **beyan edilmiş üst-küme**. İş kararı olarak da doğru: WhatsApp kolundan marka/model'siz
  talep gelmesi meşrudur (Ege sonradan sorar), site formu sorabildiği için katı kalır.
- İthalat biçimi **(a)**: yan etkiyle yükle, `globalThis`'ten oku. Gerekçe: (b) kardeş
  chip'in yükleme yüzeyini değiştirir ve `index.html`in yüklenme biçimi bu depoda
  canlı-kırılma yüzeyidir; estetik canlı riskin üstüne konmaz. (b)/(c) kalıcı biçim
  olarak **deftere kalem**, bugün değil.
- 🔴 Bu dalda **aynı adlı ikinci dosya YARATILMAYACAK** (mimar onayı verilmedi).

---

## 4. 🔴 MİMAR HÜKÜMLERİ (TUR 2d koşarken geldi — hepsi BAĞLAYICI)

### 4.1 İKİ SAYI AYRI BASILACAK
Kapanışta `--sizinti IDDIA=16` ve `--capa IDDIA=1` **ayrı ayrı** basılacak.
**Tek sayı iki ekseni saymayacak** — ekseni birleştirmek `--sizinti`'nin adını yalan yapar.

### 4.2 K1'İN YENİ MUTANTI YAN İDDİALARIN YEŞİL KALDIĞINI DA GÖSTERECEK
Mimar hükmü: *"Kanıt DAYANAKSIZ, çekilecek."* Yeni mutant nesne guard'ına nişanlanacak
**ve** `dusen_kume == {K1}` olduğu gösterilecek.
🔴 Gerekçe: 6 iddianın yan etkiyle düşmesi, mutantın **nişan aldığı yeri değil menzilini**
gösterir. Menzil dar olmalı.

### 4.3 🔴 BÖLÜNMÜŞ DİZGE **YASAK** — kalıcı kural, iki yol var, üçüncüsü YOK
- **VARSAYILAN: tamamen sentetik pozitif vaka.** Testin kanonik numaraya atıf yapması
  gerekmiyor; desene uyan sentetik numara nöbetçiyi **aynı şekilde** tetikler.
- **Kanonik numaraya gerçekten ihtiyaç varsa: çalıştırma anında TEK KAYNAKTAN türet**
  (literal kaynakta **hiç** yazılmaz).
- 🔴 **GÖRÜNÜR MUAFİYET YOLU REDDEDİLDİ** — muafiyetle geçen test kapıyı **fail-open**
  yapar. (Aynı kural bu pakette zaten var; mimar tekrar çiviledi.)
- 🔴 **EK İŞ — kaçışın YAYILMASINI engelle:** `kisisel-veri-test.py`'ye (ya da ilgili
  nöbetçiye), kaynakta **yan yana duran rakam literallerinin birleştirilmesi** hâlini
  yakalayan bir vaka ekle (ör. `"90545" + "1386526"` deseni). Mükemmel gizlemeyi
  yakalayamaz — amaç o değil; amaç bu tekniğin repoda **öğrenilmesini** engellemek.
- Seçtiğin yolu **gerekçesiyle** rapora yaz.

### 4.4 🔴 NODE 20 — MERGE ŞARTI DEĞİŞTİ
Ölçüm net: CI'daki **15** `setup-node` adımının hepsi `20`, yerel `25.8.1`. Yani
`talep.mjs`'in 50 iddiası ve mutasyon bataryası **CI'nın koştuğu sürümde hiç ölçülmedi**.
**Yerel yeşil, ölçülmemiş yeşildir.**

**Dal main'e ancak şu ikisinden BİRİ varsa alınır:**
- **(a)** aynı bataryanın **Node 20** ile yerelde koşmuş **ham çıktısı**, ya da
- **(b)** dalın **CI koşumunun, SHA'yı İÇEREN** yeşili.

"Yerelde 50/50" **tek başına YETMEZ**. Bu bulgu K186'yı aşıyor; mimar ayrı kalem açtı
(**K196**) — aynı sapma bu depodaki **her JS ölçümü** için geçerli.

### 4.5 İZOLASYON SAYISI **ÜÇ KOVAYLA** BASILACAK
Tek `IZOLE=n` yerine:
```
IZOLE: SAGLAM=<n> · ZAYIF=<n> · ACIKLANMAMIS=<n>
```
Bugünkü denetim: **28 sağlam / 3 zayıf / 0 açıklanmamış**. Hedef: `ZAYIF=0` ve
`ACIKLANMAMIS=0`; kalanlar ya `SAGLAM` ya `OLCULEMEDI` + sebep.

**Genelleşen kural (kapanış notuna AYNEN girecek, ders defterine yazılıyor):**
> *Gerekçe, ölçülen kümenin HER elemanını açıklamalı; açıklamıyorsa gerekçe değil kılıftır.*

---

## YASAKLAR
`git commit` · `git push` · `wrangler deploy` · `d1-sync.py --sema` · `urunler.json` ve
`index.html`'e dokunmak · paylaşılan tablo dosyasını bu dalda yaratmak · `shop/wrangler.toml`
değiştirmek (K187/K190 ayrı turlarda).
Komut stili: dolar-değişken, dolar-parantez, `for`, `while`, `cd`, çıktı yönlendirme,
heredoc YASAK. **Sayı uydurma.**

## TESLİM
Raporu (worktree kökündeki mevcut mühendis raporu dosyası) GÜNCELLE. İçinde:
`IZOLE=<n>/50 OLCULEMEDI=<m>` + `OLCULEMEDI` listesinin adlı/sebepli dökümü ·
`--sizinti` kolunun `IZOLE` sayısı · Node sürüm karşılaştırması (yerel vs CI, dosya:satır) ·
`kabul.js` CI'da koşuyor mu ölçümü · §3'teki `zorunlu` hükmünün sözleşme bloğuna eklenmiş hâli.
