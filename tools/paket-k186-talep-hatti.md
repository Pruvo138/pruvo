# K186 — TALEP HATTI ALTYAPISI (Ege reformu Faz-1 ⇄ Faz-2 ortak omurgası)

Mimar: KraL · Dal: `kral/k186-talep-hatti` · Chip: `KraL-Ege reformu altyapı`

Bu paket **yargı**dır: aşağıdaki kararlar tartışmaya açık değildir, uygulanır. İşçi yalnız
icra eder ve **sayı** getirir. "Bakıldı, iyi görünüyor" kabul DEĞİLDİR.

---

## 0. KAPSAM ÇİTİ (dışına ÇIKMA)

**BU PAKETTE VAR:** `shop/src/talep.js` (yeni, saf modül) · `shop/src/index.js` (yalnız
TEK router satırı) · `tools/d1-sema.sql` (yalnız EKLEME) · `tools/talep-hatti-test.py`
(yeni) · `shop/test/talep.mjs` (yeni) · `tools/talep-temizlik.py` (yeni, kuru-koşum
varsayılan) · `.github/workflows/deploy.yml` + `.github/workflows/nobet.yml` (yalnız
kablolama adımı) · `tools/ci-kapsam-test.py` (yalnız yeni dosyaların beyanı).

**BU PAKETTE YOK — DOKUNMA:**
- 🔴 `urunler.json` ve `index.html` — K184 chip'i aynı anda onlarda çalışıyor. TEK bayt
  değiştirme. Çakışma çıkarırsan iş geri alınır.
- 🔴 `wrangler deploy` **YAPMA**. `python3 tools/d1-sync.py --sema` **KOŞTURMA**. Canlı
  D1'e hiçbir yazma yapma. Bunlar Okan/mimar kapısıdır; sen SQL'i ve komutu hazırlarsın.
- Ege'nin dar-LLM eşleştirmesi (`eslesen_urun_id`'yi kim doldurur) — KAPSAM DIŞI, yalnız
  kolon hazır bırakılır.
- Mevcut D1 tablolarına (`urunler`, `siparisler`, `senkron`, `reklam_ref_gclid`) ALTER YOK.

---

## 1. `talep_kodu` — BİÇİM HÜKMÜ (değiştirme)

```
KOD = "PR-" + 6 karakter
ALFABE = "23456789ABCDEFGHJKMNPQRSTVWXYZ"      (30 karakter)
REGEX  = ^PR-[23456789ABCDEFGHJKMNPQRSTVWXYZ]{6}$
```

**Gerekçe (rapora AYNEN geçir, kendi cümlenle doğrula):**
- Dışlanan karakterler: `0 O` · `1 I L` · `U`. İlk ikisi telefonda okunurken/elle
  yazılırken karışır (kod müşteriden WhatsApp'a ELLE geçebilir — bu yolun tek köprüsü).
  `U` küme dışıdır çünkü kalan harflerle Türkçe'de istenmeyen kısaltmalar üretebiliyor.
- `PR-` öneki: WhatsApp'ta serbest metin içinde kodun **tanınabilir** olması için. Faz-2
  (HocA) gelen mesajda bu öneki arayarak kodu ayıklayacak.
- Evren `30^6 = 729.000.000`. Doğum-günü çakışması 10.000 kayıtta ihmal edilebilir
  (~%0,007). Yine de **çakışma tesadüfe bırakılmaz**: `kod` PRIMARY KEY'dir, INSERT
  çakışırsa yeni kod üretilip **en çok 5 kez** denenir; 5'i de düşerse `kod: null` +
  WhatsApp yedek yolu döner (bkz. §3 hata yolu). **Sessizce başarı dönme.**
- Rastgelelik `crypto.getRandomValues` ile alınır. `Math.random()` **YASAK** (tahmin
  edilebilir kod = başkasının talebini WhatsApp'tan sorgulama yüzeyi).

---

## 2. ŞEMA — `tools/d1-sema.sql` SONUNA EKLENİR (additive)

```sql
CREATE TABLE IF NOT EXISTS talepler (
  kod             TEXT PRIMARY KEY,
  olusturma       TEXT NOT NULL,
  kanal           TEXT NOT NULL,
  kategori        TEXT,
  marka           TEXT,
  model           TEXT,
  yil             TEXT,
  parca_adi       TEXT,
  notu            TEXT,
  durum           TEXT NOT NULL DEFAULT 'yeni',
  eslesen_urun_id TEXT
);
CREATE INDEX IF NOT EXISTS talepler_durum ON talepler(durum, olusturma DESC);
```

**Mimar düzeltmesi — chip önerisinden İKİ sapma, ikisi de gerekçeli:**

1. 🔴 `not` → **`notu`**. `NOT` SQLite'ta ayrılmış sözcüktür (mantıksal değil operatörü);
   `not` adlı kolon her SELECT/INSERT'te tırnaklanmak zorunda kalır ve bir gün biri
   tırnağı unutup sözdizimi hatası alır. Sessiz değil gürültülü bir tuzak ama bedava
   kaçınılır. Faz-2 sözleşmesinde de `notu` geçer.
2. `yil` **TEXT**, INTEGER değil. Müşteri "2015-2018", "2016 sonrası", "bilmiyorum"
   yazar. INTEGER olsa bu girdiler ya kaybolur ya kaydı düşürür. Doğrulama uzunluk
   tavanıdır, sayı zorlaması DEĞİL.

**Alan uzunluk tavanları (Worker'da uygulanır, aşan KIRPILMAZ → RED):**
`kategori` 40 · `marka` 60 · `model` 60 · `yil` 20 · `parca_adi` 120 · `notu` 500.
Kırpma değil red: kırpılmış talep sessizce yanlış bilgi taşır.

**`kanal` kapalı küme:** `'site'` | `'whatsapp'`. Başka değer → RED.
**`durum` kapalı küme:** `'yeni'` | `'goruldu'` | `'kapandi'`. Uç YALNIZ `'yeni'` yazar.

🔴 **PII SÖZLEŞMESİ:** bu tabloda telefon/e-posta/ad/adres kolonu **YOKTUR ve
AÇILMAYACAKTIR**. Kimlik WhatsApp'ta kalır, köprü `kod`'dur. Bu bir tercih değil,
tablonun varlık nedenidir.

---

## 3. UÇ — `POST /api/shop/talep`

Worker route öneki `/api/shop` (bkz. `shop/wrangler.toml`), `index.js:1029` onu soyar.
Yani router içinde yol `/talep`'tir.

**Yeni dosya `shop/src/talep.js` — `shop/src/ref.js` DESENİNİ birebir izle:** saf modül,
`wrangler` importu yok, `index.js`'ten bağımsız birim-test edilebilir. `ref.js`'i oku;
oradaki `birHost` / `izinliHostlar` / `originIzinli` / `kotaAsildi` yapıları bu uç için
**yeniden yazılmaz, aynı desende kurulur** (ikiz tanım riski: ortak olanları `ref.js`'ten
`export` edip `talep.js`'te import etmek TERCİH EDİLİR — hangisini seçtiğini rapora yaz).

`index.js`'e eklenecek TEK satır (1043 civarı, `/ref` satırının yanına):
```js
if (yol === "/talep" && request.method === "POST") return await talepKaydet(request, env);
```

### 3.1 Savunma sırası (bu SIRAYLA — sıra da ölçülür)

1. **Metot**: POST değilse 405.
2. **Origin guard (FAIL-CLOSED)**: `Origin` (yoksa `Referer`) host'u izinli kümede
   olmalı (`pruvo3d.com`, `www.pruvo3d.com`, `env.SITE_URL` host'u). İkisi de yoksa RED.
   Gerekçe: bu uç AUTH'suz D1 YAZAR — `ref.js`'in organik kolundan daha geniş bir yüzey
   değil, aynı sınıf; orada fail-closed seçilmişti, burada da öyle.
3. **Hız sınırı**: `env.TALEP_RATE_LIMIT` native binding, anahtar `CF-Connecting-IP`.
   Binding yoksa (yerel test / henüz deploy edilmemiş) sessizce atlanır = fail-open,
   **ve bu `shop/wrangler.toml` yorumunda AÇIKÇA beyan edilir** (`ref.js` emsali). Cap
   aşılırsa D1'e HİÇ gidilmez.
4. **Gövde tavanı**: gövde `request.text()` ile alınır, **BAYT** ölçülür
   (`new TextEncoder().encode(s).length`), tavan **4096 bayt**. Aşarsa RED.
   🔴 `s.length` **YASAK** — o UTF-16 kod birimi sayar; "şşşşş..." dolu bir gövde
   `.length` tavanının altında kalıp bayt tavanını aşabilir. Bu tuzak bu depoda ölçüldü.
5. **JSON parse**: düşerse RED.
6. **Honeypot**: `website` alanı — yoksa veya `""` ise geç; DOLU ise RED, **D1'e
   gidilmez**. (Ad `website` çünkü otomatik dolduran botlar bu adı hedefler; gerçek
   formda `display:none` + `autocomplete="off"` ile gizlenir — form K184'ün işi, sen
   yalnız sunucu kolunu yaz.)
7. **Allow-list (KATI)**: izinli anahtar kümesi TAM OLARAK
   `{kanal, kategori, marka, model, yil, parca_adi, notu, website}`.
   Kümede olmayan **tek bir anahtar bile** varsa RED. (Beyaz liste dışını sessizce atma:
   atarsak yarın biri `telefon` alanı gönderir, biz onu sessizce yutarız ve kimse
   sözleşmenin bozulduğunu göremez. RED = gürültülü.)
8. **Tip + tavan doğrulaması**: her alan string ya da yok; tavanlar §2'deki gibi.
   `kanal` kapalı kümede.
9. **Kod üret + INSERT** (§1 çakışma yordamı).

### 3.2 Yanıt

Başarı → **200**:
```json
{ "kod": "PR-K7M2QX", "wa": "https://wa.me/905451386526?text=PRUVO%20talep%20kodu%3A%20PR-K7M2QX" }
```
RED → **400**, gövde `{ "hata": "gecersiz", "wa": "https://wa.me/905451386526" }`.
D1 yazma hatası / 5 kod denemesi de düştü → **200**, `{ "kod": null, "wa": "https://wa.me/905451386526" }`
ve `console.error` ile gürültülü log.

**Kural:** her yanıt `wa` taşır — kayıt düşse bile müşteri kaybolmaz (mimar hükmü ④).
**Kural:** RED yanıtları HANGİ kuralın düştüğünü SÖYLEMEZ (tek `"gecersiz"`); saldırgana
savunma haritası verilmez.
🔴 **Kural:** `wa` metni YALNIZ kodu taşır. Marka/model/parça/not **query'ye KONMAZ**
(kişisel veri olmasa da URL'ler loglanır/indekslenir; talep içeriği bizim değil müşterinin
bilgisidir). WhatsApp numarası **yalnız** `wa.me` bağlamında geçer; deponun **arama**
numarası (CLAUDE.md'de yazılı, burada tekrarlanmaz) bu paketin hiçbir dosyasında geçmez.
🔴 **Kural:** `console.log`/`console.error` çağrılarına **alan DEĞERİ** verilmez — yalnız
kod, hata sınıfı ve `e.stack`. Değer loglanırsa müşteri metni Cloudflare loglarına düşer.

---

## 4. SAKLAMA SÜRESİ + TEMİZLİK

**Hüküm: 90 gün, `durum` FARK ETMEKSİZİN.** Gerekçe: tabloda PII yok, yani süre bir
gizlilik zorunluluğu değil **kota ve bayatlık** kararıdır — `pruvo-katalog` D1'i Ege,
`d1-sync` ve `reklam_ref_gclid` ile PAYLAŞILIR, sınırsız büyüyen bir tablo ortak kotayı
yer. 90 günden eski bir talep zaten ticari olarak ölüdür; `kapandi` olanları daha uzun
tutmanın da faydası yok (sipariş kaydı `siparisler` tablosunda, orası ayrı).

`tools/talep-temizlik.py`:
- **Varsayılan KURU KOŞUM** (`--kuru` gerekmez, varsayılan budur): kaç satır silinecek
  SAYAR ve basar, **silmez**.
- `--uygula` bayrağı olmadan HİÇBİR DELETE çalışmaz.
- Kendini test kolu `--kendini-test`: yerel `sqlite3` fikstürüyle "89 günlük satır KALIR /
  91 günlük satır GİDER" iki yönlü ölçülür.
- 🔴 Sen `--uygula` ile **KOŞTURMA**. Canlıya uygulama mimar kapısıdır.

---

## 5. KABUL — `tools/talep-hatti-test.py` (çalıştırılabilir, sayı basar)

Davranış ekseni JS'tedir → `shop/test/talep.mjs` yazılır (node ile koşar, `ref-route.mjs`
desenini izle) ve `talep-hatti-test.py` onu **alt süreç olarak koşturur** + kaynak
taramasını KENDİ yapar. Python testi hem çağrının çıkış kodunu hem iddia sayısını okur.

**Ölçülecek iddialar (her biri AYRI sayılır ve basılır):**

| # | İddia | Şerit |
|---|---|---|
| A1 | Kod üreteci **entropi** ölçümü — bkz. 🔴 DÜZELTME A1 (aşağıda) | B |
| A2 | Kod alfabesinde `0 1 I L O U` **YOK** (üretilen 100.000 kodun hiçbirinde) | B |
| A3 | Üretilen her kod `^PR-[...]{6}$` regex'ini geçer | B |
| A4 | `Math.random` kaynakta **geçmez**, `crypto.getRandomValues` geçer | B |
| B1 | Allow-list dışı alan (`telefon`) → **RED**, D1 çağrısı **0** | 🔴 BLOKLAYICI |
| B2 | Honeypot (`website`) dolu → **RED**, D1 çağrısı **0** | 🔴 BLOKLAYICI |
| B3 | Gövde 4096 baytı aşınca → **RED** (fikstür ÇOK BAYTLI Türkçe karakterle: `.length` tavanın ALTINDA, bayt ÜSTÜNDE — `.length` ile yazılmış bir uygulama bu vakayı GEÇİRİR) | 🔴 BLOKLAYICI |
| B4 | Origin/Referer yok → **RED**, D1 çağrısı **0** | 🔴 BLOKLAYICI |
| B5 | Yabancı Origin → **RED**, D1 çağrısı **0** | 🔴 BLOKLAYICI |
| C1 | KAYNAK TARAMASI: `talepler` CREATE TABLE kolon listesinde PII adı yok | 🔴 BLOKLAYICI |
| C2 | KAYNAK TARAMASI: `talep.js` allow-list sabitinde PII adı yok | 🔴 BLOKLAYICI |
| C3 | KAYNAK TARAMASI: `talep.js` içindeki `console.*` çağrılarının argümanlarında alan DEĞİŞKENİ geçmez | 🔴 BLOKLAYICI |
| C4 | KAYNAK TARAMASI: `wa` URL kurucusunda `kod` DIŞINDA alan interpolasyonu yok | 🔴 BLOKLAYICI |
| C5 | `4005` numarası bu paketin dosyalarında **hiç geçmez**; `905451386526` yalnız `wa.me` bağlamında geçer | 🔴 BLOKLAYICI |
| D1 | Başarı yanıtı `kod` + `wa` taşır | B |
| D2 | RED yanıtı hangi kuralın düştüğünü **söylemez** (tek `"gecersiz"`) | B |
| D3 | D1 yazma hatasında yanıt **200** + `kod:null` + `wa` (müşteri kaybolmaz) | B |
| D4 | Kod çakışmasında en çok 5 deneme, sonra `kod:null` — **sessiz başarı YOK** | B |
| E1 | `kanal` kapalı küme dışı değer → RED | B |
| E2 | Her alanın uzunluk tavanı: tavan+1 → RED, tavan → KABUL (iki yönlü) | B |

🔴 **C1–C5 kaynak taraması KELİME AVI DEĞİLDİR.** Yorumda geçen "telefon" kelimesi testi
kırmamalı. Tarama **eksen** ölçer: (a) CREATE TABLE `talepler` bloğunun kolon adları,
(b) `talep.js`'teki allow-list sabitinin ELEMANLARI, (c) `console.*` çağrılarının
argüman ifadeleri, (d) `wa.me` URL'ini kuran ifade. Ayrıştırma yap, `grep` yapma.
Bu depoda ölçülmüş ders: kaba kelime taraması ya kör olur ya kalıcı kırmızı.

### 5.1 MUTASYON — K182 KURALI

Her iddia için **hedef kolu öldüren** bir mutant yaz ve mutantın **O KOLU** öldürdüğünü
AYRICA kanıtla. Bu depoda ölçülmüş üç tuzak, üçünden de kaçın:

- **Mutant yan ekseni de tetikliyorsa ölçmez**: mutant hedef kolu öldürürken sayı/imza
  gibi başka bir ekseni de kırıyorsa, hedef kol ÖLÜ olsa bile kırmızı gelirdi → o mutant
  hiçbir şey kanıtlamaz. Her mutantın **yalnız** hedef iddiayı düşürdüğünü göster.
- **Mutasyon çapası ölü kola nişanlanır**: daha erken bir koşul zaten hükmü verdiyse
  mutant SESSİZ döner. Savunma sırası (§3.1) yüzünden bu ucda risk YÜKSEK — ör. B3'ü
  ölçmek için önce Origin'i geçerli vermelisin, yoksa mutant Origin kolunda ölür.
- **Çapalar benzersiz**: iki mutant aynı metne çapalanırsa batarya kırılır.
- `rc=1` "mutant yakalandı" DEMEK DEĞİLDİR — testin çöktüğü de rc=1'dir. Mutant
  raporunda **komut + ham çıktı + çıkış kodu** bulunacak.

Test şunları BASAR: `IDDIA=<n> DUSEN=<n> MUTANT=<k>/<k> KONTROL=<n>/<n>`.
Mutasyon diske yazıyorsa bytecode önbelleğini (`__pycache__`) temizle ve mutasyonu
`finally` ile GERİ AL — yarıda kalan mutasyon ağacı kirletir.

---

## 6. CI KABLOLAMA — AYNI SPEC'TE (kablolanmadan iş BİTMEZ)

Şerit kararı (mimar hükmü): **veri sızıntısı riski taşıyan iddialar BLOKLAYICI**, kalanlar
SERIT B. Bu yüzden test **İKİ KOLLU** yazılır:

- `python3 tools/talep-hatti-test.py --sizinti` → yalnız **B1–B5 + C1–C5** (ağsız, hızlı).
  **`.github/workflows/deploy.yml` içindeki `serit-a3` job'una** `continue-on-error`SUZ
  adım olarak bağlanır (`deploy: needs:` listesinde `serit-a3` GEÇER → yayını bloklar).
- `python3 tools/talep-hatti-test.py` (bayraksız, TAM batarya + mutasyon) →
  **`.github/workflows/nobet.yml`** (SERIT B) içine kendi adımıyla.
- `python3 tools/talep-temizlik.py --kendini-test` → nobet.yml SERIT B.

🔴 Bu depoda ölçülmüş ders: bir adımın "bloklayıcı" olduğunu **BEYAN ETMEK** yetmez,
`nobet.yml`de duran adım yayını BLOKLAMAZ. Bağladığın job adını rapora **dosya:satır**
ile yaz.

**Kapanış kapısı:** `python3 tools/ci-kapsam-test.py` **rc=0**. Yeni dosyalar
(`tools/talep-hatti-test.py`, `tools/talep-temizlik.py`, `shop/test/talep.mjs`) o kapının
beyan/kapsam envanterine girmek zorunda. rc≠0 ile iş TESLİM EDİLMEZ.

---

## 7. REGRESYON (bozmadığını KANITLA)

Şu üçü dalın içinde YEŞİL kalacak, çıktısı rapora sayıyla geçecek:
- `python3 tools/ci-kapsam-test.py` → rc=0
- `node --test shop/test/` (ya da deponun mevcut koşum satırı — `shop/test/kabul.js`'e bak)
  → düşen 0
- `python3 tools/d1-sync.py --kendini-test` → şema fikstürü `d1-sema.sql` ile ikizdir
  (dosyada `IKIZ TANIM UYARISI` yorumu var); yeni tablo o fikstürü bozarsa **fikstürü de
  güncelle**, testi susturma.

---

## 8. TESLİM

- Rapor: worktree kökünde, deponun kanonik mühendis-rapor adıyla (CLAUDE.md'de yazılı;
  **başka ad YASAK**). Sayılarla:
  iddia/düşen/mutant/kontrol · CI job adı + dosya:satır · regresyon çıktıları ·
  `--sema` komutu ve SIRASI (uygulanmadı, onay bekliyor) · saklama süresi kararı.
- Rapora ayrıca **HocA'ya sözleşme bloğu**: `talep_kodu` regex'i · `POST /api/shop/talep`
  gövde şeması (tam anahtar listesi + tavanlar) · `talepler` alan listesi · yanıt şekilleri.
- 🔴 `git commit` **ATMA** — sandbox `.git` kilidine yazamaz, denemen boşa iş üretir.
  Koordinatör (KraL) commit'i atacak. Sen yalnız dosyaları bırak.
- push/merge **YOK**.

## 9. KOMUT STİLİ
`$VAR` · `${...}` · `$(...)` · `for` · `while` · `cd` · `>` yönlendirme · heredoc **YASAK**.
Yollar tam ve düz. Betiği dosyaya yaz, sonra `python3 /tam/yol.py` ile koş.

---

# EK HÜKÜM 1 (mimar, TUR 1 koşarken geldi) — `wa` METNİ YOLA GÖRE DEĞİŞİR

§3.2'deki "`wa` metni YALNIZ kodu taşır" kuralı **fazla genişti** ve `kod:null` yolunda
müşteriyi kaybettiriyordu: o yolda D1 yazması DÜŞMÜŞTÜR, yani kayıt YOKTUR — WhatsApp
metni o talebin **tek nüshası**dır. Kural üç yola ayrıldı, üçü de ayrı ölçülür:

| Yol | `wa` metni | Gerekçe |
|---|---|---|
| **Başarı** (`kod` var) | YALNIZ kod: `PRUVO talep kodu: PR-XXXXXX` | Kayıt D1'de duruyor; içeriği URL'e kopyalamanın faydası yok, URL'ler loglanır/indekslenir. |
| **`kod:null`** (D1 düştü / 5 deneme de çakıştı) | **YAPILANDIRILMIŞ ÖZET**: kategori · marka · model · yıl · parça · not | Kayıt YOK. Özet olmazsa müşterinin yazdığı her şey kaybolur. Talep insana ULAŞIR. |
| **RED** (doğrulama düştü) | **BOŞ** — çıplak `https://wa.me/905451386526`, `?text=` YOK | Girdi geçersiz/düşmanca. Saldırganın kontrol ettiği metni geri yankılamak bize ait bir URL'i onun taşıyıcısı yapar. |

Uygulama notu: özet `encodeURIComponent` ile kodlanır; alan tavanları (§2) toplamı ~800
karakter olduğundan URL tavanı sorun değil, ama üretilen `text` yine de **1500 karakterde
kesilir** (kesilirse sonuna `…` konur). Özette boş alanlar satır olarak BASILMAZ.

**Kabul tablosuna (§5) EKLENEN iddialar:**

| # | İddia | Şerit |
|---|---|---|
| D5 | `kod:null` yanıtındaki `wa` metni yapılandırılmış özeti **İÇERİR** (müşteri kaybolmaz) | B |
| D6 | Başarı yanıtındaki `wa` metni kod DIŞINDA alan **taşımaz** | 🔴 BLOKLAYICI |
| D7 | RED yanıtındaki `wa` **`?text=` taşımaz** (girdi yankılanmaz) | 🔴 BLOKLAYICI |

🔴 §5 C4 iddiası buna göre DARALTILIR: "`wa` URL kurucusunda kod dışında alan
interpolasyonu yok" artık **yalnız başarı ve RED yolları** için geçerlidir (D6/D7 ile
ölçülür); `kod:null` yolu bilinçli istisnadır ve C4 onu KAPSAM DIŞI sayar — istisnayı
koda ve teste **yaz**, sessizce geçme.

---

# EK HÜKÜM 2 (mimar) — `yil` TEXT'tir, SAYI GİBİ KARŞILAŞTIRILAMAZ

`yil` TEXT olduğu için `yil > 2010` gibi bir karşılaştırma SQLite'ta sessizce yanlış
sonuç döndürür (metin sıralaması: `"9"` > `"2010"`). Bugün böyle bir sorgu yok; yarın
biri yazarsa hata **sessiz** olur.

**Kabul tablosuna (§5) EKLENEN iddia:**

| # | İddia | Şerit |
|---|---|---|
| E3 | Kaynak taraması: `yil` kolonu üzerinde sayısal/aralık karşılaştırması (`<`, `>`, `BETWEEN`, `CAST(... AS INTEGER)`) **YOK** — repo genelinde `talepler` sorgularında | B |

Bu da eksen ölçümüdür, kelime avı değil: `talepler` tablosuna değen SQL ifadelerini
ayrıştır, `yil` operandının karşılaştırma operatörüne girip girmediğine bak.
Ayrıca `d1-sema.sql`'deki `talepler` bloğuna bu kısıtı **yorum olarak** yaz.

---

# 🔴 DÜZELTME A1 (MİMARIN KENDİ SPEC HATASI — ölçüm yakaladı)

§5'teki **"100.000 üretimde 0 çakışma"** iddiası **matematiksel olarak yanlıştı**; kod
kusuru değil, benim spec kusurum. Doğum-günü sınırı: evren `30^6 = 729.000.000`,
`n = 100.000` çekimde beklenen çakışma `n²/(2N) ≈ 6,9`. Yani **doğru çalışan bir üreteç
bile ~7 çakışma verir** ve iddia HER KOŞUMDA düşer.

Ölçüm bunu doğruladı: taban koşumda `DUSEN=1` — düşen iddia **A1**. Mutant koşumlarının
ham çıktısında da `{"say":99996,"tekrar":true}` görünüyor: 4 çakışma, tam beklenen aralıkta.

🔴 **Kavram hatası neredeydi:** üretecin işi **tekillik** değil **entropi**dir. Tekilliği
`kod` PRIMARY KEY + 5 denemelik yeniden üretim garanti eder (§1) — orası zaten
ölçülüyor (D4/D10). Üreteçten tekillik istemek, veritabanının işini üretece yıkmaktı.

**A1 YENİ TANIMI:**

| # | İddia | Şerit |
|---|---|---|
| A1 | 100.000 üretimde **farklı kod sayısı ≥ 99.900** (entropi tabanı). Bozuk üreteç kesin düşer: sabit üreteç `1`, tek-karakter entropili üreteç `30` verir; sağlam üreteç ~99.993 verir — aradaki uçurum 3 büyüklük mertebesi, eşik istatistiksel gürültüye DEĞMEZ | B |

**Çakışma sayısı iddia edilmez** — beklenen aralıkta olması normaldir ve onu sıfıra
zorlamak yanlış-pozitif üretir. Eşiğin gerekçesi rapora yazılacak: 99.900 eşiği beklenen
~7 çakışmanın 14 katına kadar tolerans tanır (yanlış-pozitif yok), ama entropi kaybının
her gerçek biçimini yakalar (say ≤ 30).

## A1 — KABUL EDİLEN İKİNCİ ÇÖZÜM: DETERMİNİSTİK VEKİL RNG

İşçi eşik yerine **`crypto.getRandomValues`'i sayaç tabanlı bir vekille değiştirip** ölçümü
deterministik yapan bir yol seçti (kod `i`, `i`'nin 30 tabanındaki gösterimi olur → 100.000
çekimde 100.000 farklı kod, çakışma **yapısal olarak** imkânsız).

**Bu çözüm KABUL** — eşik toleransından üstündür: istatistiksel pay gerekmez, iddia
`say == 100000 and not tekrar` biçiminde kesin kalır ve yanlış-pozitif üretmez. İkisinden
biri yeterli; hangisi seçilirse **gerekçesi kodun yanına yazılır** (bir sonraki okuyan
"0 çakışma olmalı" diye geri sıkıştırmasın — bugün düşen iddia tam olarak buydu).

🔴 **AMA BU YOLUN AÇTIĞI KÖR NOKTA KAPATILACAK.** Vekil RNG takılıyken üretecin **gerçek
rastgelelik yolu hiç koşmuyor**; özellikle `talepKoduUret` içindeki **red-örnekleme**
(`do { ... } while (bayt[0] >= kabulSiniri)`) ölçülmemiş kalıyor. Vekil hep `0..29`
döndürdüğü için o `while` koşulu **hiçbir zaman doğru olmuyor** — yani deponun bilinen
tuzağı: *ölü kola nişanlanmış ölçüm*. Red-örnekleme bozulursa (ör. `>=` yerine `>`,
ya da `kabulSiniri` yanlış hesaplanırsa) kodlar **düzgün dağılmaz** ve alfabenin ilk
karakterleri fazla çıkar — hiçbir iddia bunu görmez.

| # | İddia | Şerit |
|---|---|---|
| A5 | Vekil RNG **tavan üstü** değerler de döndürdüğünde (ör. sırayla `250, 7`) üreteç `250`'yi **REDDEDİP** yeniden çeker; üretilen karakter `ALFABE[7]` olur, `ALFABE[250 % 30]` DEĞİL | B |
| A6 | Vekil RNG düzgün dağılımlı `0..255` ürettiğinde, 60.000 karakterde alfabenin **30 harfinin hepsi** görülür ve en sık/en seyrek harf oranı **1,5'i aşmaz** (red-örnekleme modulo sapmasını gerçekten kaldırıyor mu) | B |

A5 mutantı: `bayt[0] >= kabulSiniri` → `bayt[0] >= 256` (red hiç çalışmaz).
A6 mutantı: `kabulSiniri` → `256` (modulo sapması geri gelir).
İkisi de **yalnız kendi iddiasını** düşürmeli.

### 🔴 A6 GİRDİSİ **TAM DEVİR** OLACAK (kırılganlık önlemi — mimar şerhi)

A6'nın vekili `0..255` aralığını **tam devirlerle** süpürecek (`k × 256` çekim, yarım
devir YOK). Gerekçe — koda yorum olarak yazılacak:
```
# Kabul penceresi 0..239 = 240 deger = 30 harf x 8. Supurme 0..255'in TAM kati oldugunda
# her harf birebir 8k kez duser -> en sik / en seyrek orani DETERMINISTIK 1,0 cikar.
# Yarim devirle biten supurme kuyrukta yapay sapma uretir; o zaman 1,5 esigi bir gun
# SEBEPSIZ kirilir ve kimse nedenini bulamaz (kirilgan esik = susturulan kapi).
```
Eşik 1,5 olarak KALIR (mutant marjı), ama sağlam kodda ölçülen değer **tam 1,0** olmalı;
rapora ölçülen oran AYNEN yazılacak. 1,0 değilse süpürme tam devir değildir → önce onu düzelt.

### A7 — GERÇEK RNG YOLU ÖLÇÜM DIŞINDA KALMAYACAK (duman vakası)

Vekil takılıyken üretim yolu hiç koşmuyor. Küçük, **kırılgan olmayan** bir duman vakası:

| # | İddia | Şerit |
|---|---|---|
| A7 | **GERÇEK** `crypto.getRandomValues` ile 1.000 kod üretilir; hepsi `TALEP_KOD_RE`'yi geçer, hepsi 9 karakterdir ve **yalnız** `TALEP_ALFABE` harflerini taşır. **İstatistik YOK** (çakışma/dağılım iddia edilmez) — bu yüzden kırılgan değildir | B |

Böylece "üretim yolu hiç çağrılmadı" sınıfı kapanır; entropi ve tekillik iddiaları
deterministik vekilde kalmaya devam eder. A7 mutantı: `talepKoduUret` gövdesinde
`TALEP_ALFABE` yerine sabit bir dizge — biçim bozulur, A7 düşer.

### 🔴 `BEKLENEN_IDDIA` SABİTLERİ AYNI COMMIT'TE GÜNCELLENECEK

İddia sayısı 20'den arttı (K1–K5, A5–A7, D5–D12, E3, F1–F4, G1–G7 eklendikçe). G5
invaryantı sabitle karşılaştırdığı için **sabit güncellenmezse kendi kapımız kırmızı
yanar** — bu DOĞRU davranıştır (invaryant çalışıyor demektir), ama sabitler iddia
listesiyle **aynı commit'te** güncellenmezse gürültü üretir. Kapanış raporunda nihai
iki sayı (bayraksız kol / `--sizinti` kolu) AYNEN yazılacak.

---

# EK HÜKÜM 4 (mimar şerhleri) — `kod:null` KOLU: NORMALİZE + SAYILIR

EK HÜKÜM 1'in `kod:null` kolu iki delik bıraktı; ikisi de kapatılır.

## 4.1 Özet HAM YANKI DEĞİLDİR (normalize + kırp)

`kod:null` kolu da müşteri metnini **bizim** URL'imize gömüyor — RED kolundan tek farkı
doğrulamadan geçmiş olması, ki doğrulama yalnız **tip + uzunluk** bakar, içeriğe bakmaz.
Özet ham değerden değil, **normalize edilmiş** değerden kurulur:

- `kategori` ve `marka`: kanonik kaynaktan çözülmüş **jeton** ile yazılır; kaynakta
  karşılığı yoksa o satır özete **KONMAZ** (ham değer basılmaz).
- Serbest alanlar (`model`, `yil`, `parca_adi`, `notu`): kontrol karakterleri ve satır
  sonları (`\r`, `\n`, `\t`, U+0000–U+001F, U+007F) **temizlenir**; ardışık boşluk teke
  iner; baş/son boşluk kırpılır; alan bazında §2 tavanının **yarısında** kesilir.
- Üretilen `text` toplamda **1500 karakterde** kesilir (kesilirse sonuna `…`).
- Boş/çözülemeyen alanlar satır olarak **BASILMAZ**.

**Kabul tablosuna EKLENEN iddia:**

| # | İddia | Şerit |
|---|---|---|
| D8 | `kod:null` özeti, gövdedeki ham değerin **birebir kopyası DEĞİL** — fikstür: içinde `\n` + kontrol karakteri + tavan aşırı boşluk taşıyan bir `notu` gönderilir; üretilen `wa` metninde bunların hiçbiri **geçmez** ve alan kırpılmıştır | 🔴 BLOKLAYICI |

## 4.2 `kod:null` SAYILIR (PII'siz)

O yolda D1'de kayıt YOK. Sayaç da yoksa bir D1 kesintisi **"hiç talep gelmedi"** gibi
görünür ve BaBa'nın kabul ölçütü ("yarım bırakılan akış oranı") sessizce yanlış okunur.
Bu, kapıların değil **ürünün** körleşmesidir.

🔴 **Sink KARARI — sayaç D1'e YAZILMAZ.** `kod:null`ın baskın sebebi zaten D1'in
düşmesidir; sayacı D1'e yazmak, ölçmek istediğin arıza tam da onu düşürdüğünde ölçümü
kaybetmek demektir (kendi kendini söndüren alarm). Sink: **yapılandırılmış
`console.error` satırı** (Cloudflare log'una düşer).

Satır biçimi — **YALNIZ** şu üç alan, başka HİÇBİR ŞEY:
```
talep_kod_uretilemedi sebep=<d1_hata|kod_cakisma> zaman=<ISO>
```
`sebep` kapalı küme: `d1_hata` | `kod_cakisma`. Müşteri metni, alan değeri, IP, header —
**hiçbiri** bu satıra girmez. (Bu, §3.2'deki "console'a alan DEĞERİ verilmez" kuralıyla
ÇELİŞMEZ: burada basılan şey sebep kodu ve zamandır, alan değeri değil. C3 iddiası
aynen yürürlükte.)

**Kabul tablosuna EKLENEN iddialar:**

| # | İddia | Şerit |
|---|---|---|
| D9 | D1 hatası → `talep_kod_uretilemedi` satırı **düşer**, `sebep=d1_hata` | B |
| D10 | 5 kod denemesi de çakıştı → satır düşer, `sebep=kod_cakisma` (iki sebep AYIRT EDİLİR) | B |
| D11 | Bu satır **hiçbir alan değeri taşımaz** — fikstür: ayırt edici bir dizge (`ZZQX-SIZINTI-CAPASI`) `notu`ya konur, log çıktısında **geçmez** | 🔴 BLOKLAYICI |

---

# EK HÜKÜM 5 (mimar şerhleri) — KALICILIK SINIRI · ÜÇÜNCÜ SEBEP · NEGATİF VAKA

## 5.1 Sayacın kalıcılık sınırı — ÖLÇÜLDÜ: KV YOK, sink GEÇİCİ

`shop/wrangler.toml` **ölçüldü** (`grep` ile binding listesi): mevcut binding'ler
`[[d1_databases]] KATALOG` · `[[unsafe.bindings]]` (rate limiting, ×2) ·
`[[r2_buckets]] OZEL_DOSYA`. **`kv_namespaces` YOK.**

🔴 **Hüküm: yeni altyapı AÇILMAZ.** R2 (`OZEL_DOSYA`) teknik olarak D1'den bağımsızdır
ama sayaç sink'i **DEĞİLDİR** ve öyle kullanılmayacak: atomik artırma yok (her olay
read-modify-write → eşzamanlı istekte sayaç sessizce geri sayar), üstelik o kova ÖZEL
MÜŞTERİ DOSYASI kovasıdır — ölçüm verisini oraya karıştırmak kapsam ihlalidir.

**Bu yüzden rapora AYNEN şu satır girer, gizlenmez:**
```
OLCULEMEDI: kalici sayac yok — sink GECICI (console.error). Cloudflare'de yalniz canli
tail / Logpush yapilandirilmissa gorunur. BaBa'nin "yarim birakilan akis orani" olcutu
GERIYE DONUK olculemez. Cozum yolu (mimar kapisi): shop/wrangler.toml'a kv_namespaces
binding'i + gunluk anahtarli sayac, ya da Logpush. ACIK KALEM.
```
Kod, ileride binding gelirse kolay bağlanacak şekilde yazılır: sayaç çağrısı **tek bir
fonksiyonun arkasında** durur (`talepOlayiSay(env, sebep)`), bugünkü gövdesi yalnız
`console.error` basar. İkinci bir sink eklemek o fonksiyonu değiştirmek olur, uçları
dolaşmak değil.

## 5.2 `sebep` kapalı kümesi ÜÇ değerlidir

```
sebep ∈ { d1_hata , kod_cakisma , yapilandirma }
```
`yapilandirma` = beklenmeyen istisna · binding yok · şema eksik/kolon bulunamadı.
İki değerli küme beklenmeyen bir arızayı `d1_hata` diye etiketler ve müdahaleyi yanlış
yöne çevirir — K176'nın (yanlış PID basan kilit mesajı) aynı sınıfı. **Bilinmeyen istisna
`yapilandirma`ya düşer**, `d1_hata`ya DEĞİL; `d1_hata` yalnız D1 çağrısının kendisi
patladığında kullanılır.

**Kabul tablosuna EKLENEN iddia:**

| # | İddia | Şerit |
|---|---|---|
| D12 | Beklenmeyen istisna (D1 çağrısı DIŞINDA patlayan bir şey) → `sebep=yapilandirma`, `d1_hata` **DEĞİL** | B |

## 5.3 🔴 BLOKLAYICI KOLA GİREN HER İDDİANIN NEGATİF VAKASI OLACAK

`serit-a3` kırmızısı **tüm ekibin yayınını durdurur**. Tek yönlü iddia, yanlış-pozitifle
yayını kilitler ve kilidi açmak da acil bir yama turu ister. Ayna kapı disiplini:

**D6 · D7 · D8 · D11'in her biri için İKİ vaka yazılacak:**
- **TETİKLER**: iddianın yakalaması gereken girdi → kapı KIRMIZI.
- **TETİKLEMEZ**: iddiaya *benzeyen ama kapsam dışı* girdi → kapı YEŞİL.

Somut "tetiklemez" örnekleri (bunları yaz, uydurma):
- **D6** (başarı yolunda kod dışı alan taşınmaz): `wa` metninde kodun kendisi
  `PR-` öneki taşır ve içinde harf/rakam vardır — bu **alan sızıntısı DEĞİLDİR**, kapı
  bunu kırmızı yakmamalı.
- **D7** (RED yolunda `?text=` yok): başarı ve `kod:null` yollarında `?text=` **VARDIR**
  ve meşrudur — kapı o iki yolu kırmızı yakmamalı.
- **D8** (özet ham yankı değil): temiz, kısa, kontrol karakteri içermeyen bir `parca_adi`
  özette **AYNEN görünebilir** (normalize onu değiştirmez) — kapı bunu "ham yankı" sanıp
  kırmızı yakmamalı. Ayırt edici eksen *normalizasyonun uygulanıp uygulanmadığıdır*,
  "girdiye benzeyen metin var mı" değil.
- **D11** (log satırı alan değeri taşımaz): log satırındaki `zaman=<ISO>` içinde rakamlar,
  `sebep=` içinde harfler vardır — kapı bunları "alan değeri" sanmamalı.

🔴 **Negatif vakası olmayan iddia bloklayıcı kola BAĞLANMAZ.** Bir iddia için negatif
vaka yazamıyorsan, o iddia SERIT B'ye iner ve sebebini rapora yazarsın. Bu bir kaçış
kapısı değil, yanlış-pozitifle ekibin yayınını kilitlememenin bedelidir.

---

# EK HÜKÜM 3 (mimar) — SÖZLEŞMEDE AD BİREBİR

Kapanış sözleşmesinde HocA'ya `notu` adı **birebir** bildirilecek. Faz-2 tarafında `not`
diye yazılırsa ikiz ad doğar ve iki taraf farklı kolona yazar. Raporun §4.7 sözleşme
bloğunda bu ad **kalın** ve gerekçesiyle geçecek.
