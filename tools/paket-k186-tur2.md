# K186 — TUR 2 TALİMATI (işçi): CI KABLOLAMA + MUTASYON + RAPOR

Çalışma ağacın: `/Users/okan/dev/pruvo/.claude/worktrees/zen-lehmann-d54167`
(dal `kral/k186-talep-hatti`). Ana ağaca (`/Users/okan/dev/pruvo`) **TEK BAYT** yazma.

TUR 1'de yazılan dosyalar yerinde: `shop/src/talep.js` · `shop/test/talep.mjs` ·
`tools/talep-hatti-test.py` · `tools/talep-temizlik.py` · `tools/d1-sema.sql` (talepler
bloğu) · `shop/src/index.js` (router satırı). Spec: `tools/paket-k186-talep-hatti.md`.

---

## 0. ÖNCE: EK HÜKÜMLERİ UYGULA (TUR 1 koşarken geldi — spec'te EK HÜKÜM 1–4)

🔴 `tools/paket-k186-talep-hatti.md` dosyasının SONUNDAKİ **EK HÜKÜM 1, 2, 3, 4**
bölümlerini TEKRAR OKU. TUR 1 bunlar yokken koştu; şimdi uygulanacaklar. Özet:

- **EK HÜKÜM 1** — `wa` metni ÜÇ YOLA ayrılır: başarı = yalnız kod · `kod:null` =
  yapılandırılmış özet · RED = ÇIPLAK link (`?text=` YOK). Yeni iddia: **D5, D6, D7**.
  C4 kaynak taraması buna göre DARALTILIR (`kod:null` bilinçli istisna — koda ve teste
  yazılır, sessiz geçilmez).
- **EK HÜKÜM 2** — `yil` TEXT'tir, sayısal karşılaştırmaya GİRMEZ. Yeni iddia: **E3**
  (eksen ayrıştırması, kelime avı değil) + `d1-sema.sql` `talepler` bloğuna kısıt yorumu.
- **EK HÜKÜM 4.1** — `kod:null` özeti HAM YANKI DEĞİL: kategori/marka kanonik jetondan,
  serbest alanlar kontrol karakterlerinden temizlenip kırpılır, `text` 1500'de kesilir.
  Yeni iddia: **D8** (bloklayıcı).
- **EK HÜKÜM 4.2** — `kod:null` SAYILIR: sink **D1 DEĞİL** (ölçmek istediğin arıza tam da
  D1'i düşüren şey), yapılandırılmış `console.error` satırı:
  `talep_kod_uretilemedi sebep=<d1_hata|kod_cakisma> zaman=<ISO>` — başka HİÇBİR alan yok.
  Yeni iddia: **D9, D10, D11** (D11 bloklayıcı).

- **EK HÜKÜM 5.1** — sayaç sink'i GEÇİCİ (KV binding YOK, ölçüldü). Yeni altyapı AÇMA;
  R2'yi sayaç olarak KULLANMA (atomik artırma yok + özel dosya kovası). Sayaç çağrısı
  TEK fonksiyonun arkasında dursun: `talepOlayiSay(env, sebep)`. Rapora `OLCULEMEDI`
  satırını AYNEN geçir.
- **EK HÜKÜM 5.2** — `sebep` kapalı kümesi ÜÇ değerli: `d1_hata` · `kod_cakisma` ·
  `yapilandirma`. Bilinmeyen istisna `yapilandirma`ya düşer, `d1_hata`ya DEĞİL.
  Yeni iddia: **D12**.
- **EK HÜKÜM 5.3** 🔴 — bloklayıcı kola giren HER iddianın (D6·D7·D8·D11) **NEGATİF
  vakası** olacak: "tetikler" + "benzer ama kapsam dışı → TETİKLEMEZ". Spec'te dördü
  için de somut negatif vaka yazılı — onları kullan, uydurma.
  **Negatif vakası olmayan iddia bloklayıcı kola BAĞLANMAZ**, SERIT B'ye iner ve sebebi
  rapora yazılır.

Bu iddialar (D5–D12, E3 + C4 daraltması) TUR 2'nin **birinci** işidir; CI kablolaması
bunlar yazıldıktan SONRA yapılır (yoksa bloklayıcı kola eksik batarya bağlanır).

Bloklayıcı `--sizinti` kolunun NİHAİ kapsamı: **B1–B5 · C1–C5 · D6 · D7 · D8 · D11**
(dördünün de negatif vakası YAZILMIŞ olmak şartıyla).
SERIT B (bayraksız TAM batarya): hepsi + A1–A4 · D1–D5 · D9 · D10 · D12 · E1–E3.

---

## 0.1 TUR 1 ÖLÇÜLDÜ (mimar, ayrı ölçüm turu) — TABAN SAYILAR

TUR 1 işçisi **çıkış kodu 144** ile düştü (kota tavanı), son mesajını yazamadı. Mimar
ayrı bir ölçüm turu koşturdu; **taban bu**, TUR 2 bunun üstüne kurulur:

| Komut | Sonuç | rc |
|---|---|---|
| `node shop/test/talep.mjs` | `GECEN=11 DUSEN=0` | **0** |
| `python3 tools/talep-hatti-test.py` | `IDDIA=20 DUSEN=1 MUTANT=17/20 KONTROL=19/20` | **1** |
| `python3 tools/talep-hatti-test.py --sizinti` | `IDDIA=10 DUSEN=0 MUTANT=8/10 KONTROL=10/10` | **1** |
| `python3 tools/talep-temizlik.py --kendini-test` | `KENDINI_TEST=GECTI 89=KALDI 91=GITTI` | 0 |

**Kapatılacak üç şey:** `DUSEN=1` · sağ kalan 3 mutant (B3, B4 ve bayraksız kolda bir
tanesi daha) · `KONTROL=19/20`.

---

## 0.15 🔴 SAĞ KALAN MUTANTLARIN KÖK NEDENİ (mimar ölçtü — TAHMİN DEĞİL)

### M-B3 🔴 GÖVDE BAYT TAVANI İDDİASI YAPISAL OLARAK ÖLÇÜLEMEZ

Ham kanıt: `MUTANT B3 ... rc=0 ham= ✅ B3` — bayt tavanını öldüren mutant **YAŞADI**.

Sebep: B3 fikstürü `notu: "ş".repeat(2100)`. Ama `notu` alan tavanı **500 karakter**.
Yani bayt tavanı kaldırılsa bile istek `alanlarGecerli`'nin `notu` tavanından **yine**
400 alır. Mutant hedef kolu öldürüyor, test yine yeşil → mutant hiçbir şey kanıtlamıyor.
Deponun bilinen sınıfı: *mutasyon çapası ölü kola nişanlanır* + *mutant yan ekseni de
tetikliyorsa ölçmez*.

🔴 **Daha derin bulgu — bu bir fikstür kusuru DEĞİL, yapısal:** alan tavanlarının toplamı
`40+60+60+20+120+500 = 800` karakter. En kötü hâlde (3 baytlık BMP karakter) ~2400 bayt
+ anahtar yükü ≈ 2500 bayt — **4096 bayt tavanının ALTINDA**. Yani *alan doğrulamasını
geçen hiçbir gövde bayt tavanını AŞAMAZ*. Bayt tavanı bugün, doğrulamayı zaten geçemeyecek
gövdeleri reddediyor; ayırt edici bir davranışı YOK.

**AYIRT EDİCİ FİKSTÜR (bunu kullan):** JSON **jetonlar arası boşluğa** izin verir.
```
{"kanal":"site",<<5000 bosluk>>"parca_adi":"kapak"}
```
Tüm anahtarlar izinli, tüm değerler tavan altında, gövde 4096 baytı AŞIYOR.
Bayt tavanı VARSA → 400. Bayt tavanı KALDIRILIRSA → JSON geçerli, alanlar geçerli →
**200**. İşte mutantı öldüren fark budur.
**Negatif vaka (EK HÜKÜM 5.3, bu iddia bloklayıcı kolda):** aynı gövde 4096 baytın
ALTINDA boşlukla → **200** (kapı boşluğu tek başına suç saymaz).

### M-B4 🔴 ORIGIN GUARD MUTANTI DA YAŞADI — ÖNCE TEŞHİS, SONRA ÇARE

Ham kanıt: `MUTANT B4 ... rc=0 ham= ✅ B4`.
B4 = "Origin/Referer yok → RED". Guard öldürülürse istek geçerli gövdeyle akar ve **200**
dönmeliydi; test yine yeşil kaldı. İki olasılık var, **ölçerek ayır**:
(a) mutasyon çapası tutmadı (metin eşleşmedi → mutant hiç uygulanmadı), ya da
(b) daha erken bir koşul zaten reddediyor.
Mutant uygulandıktan sonraki dosyayı **fiilen oku** ve mutasyonun kaynağa girdiğini
kanıtla; sonra çareyi ona göre yaz. **Uygulanmayan mutant "yakalandı" sayılmaz.**

### M-A 🔴 A EKSENİ MUTANTLARI BİRBİRİNİN ÇAPASINA BASIYOR

Ham çıktılar:
```
A1 -> {"say":1,     "tekrar":true, "yasak":false,"bicim":true}
A2 -> {"say":99996, "tekrar":true, "yasak":true, "bicim":false}
A3 -> {"say":99996, "tekrar":true, "yasak":false,"bicim":false}
A4 -> {"say":1,     "tekrar":true, "yasak":false,"bicim":true}
```
İki kusur:
1. **A1 ile A4 BİREBİR AYNI sonucu veriyor** (`say:1`) → aynı mutasyon iki kez
   uygulanmış, çapalar benzersiz DEĞİL. A4'ün hedefi "`Math.random` kullanılmıyor"
   kaynak iddiasıydı; onu ölçen mutant `crypto.getRandomValues`'i `Math.random`'a
   çevirmeli ve `say ≈ 99996` vermeliydi, `say:1` DEĞİL.
2. **A2 yan eksenleri de yakıyor:** `yasak:true` (hedefi) ama aynı anda `bicim:false`
   ve `tekrar:true`. Hedef kol ÖLÜ olsa bile test kırmızı gelirdi → mutant hedefi
   izole etmiyor. A2 mutantı **yalnız alfabeyi** bozmalı, biçimi ve tekilliği DEĞİL.
Dördünü de yeniden yaz: **her mutant tam olarak BİR iddiayı düşürecek** ve raporda
"düşen iddia listesi = tek eleman" diye gösterilecek.

### M-RAPOR 🔴 TEST HANGİ İDDİANIN DÜŞTÜĞÜNÜ SÖYLEMİYOR

Bayraksız kol `DUSEN=1` basıyor ama **hangi iddia** düştüğü çıktıda YOK — yalnız MUTANT
satırları ve özet var. Hüküm kelimesi var, ham kanıt yok (deponun bilinen dersi).
**Çare:** düşen her iddia için `DUSEN: <ad> — <beklenen> / <gerceklesen>` satırı bas.
Bu olmadan kapı kırmızı yandığında kimse sebebini göremez ve kapı susturulur.

---

## 0.16 KABUL TESTİNİN KENDİ KÖRLÜĞÜ — `shop/test/talep.mjs`

`basliklar()` her fikstürde `kanal`+`kategori`+`parca_adi` gönderiyor; `marka`, `model`,
`yil`, `notu` **hiçbir vakada gönderilmiyor** → hepsi `undefined` olarak D1'e bağlanıyor
ve sahte `KATALOG` bunu sessizce kabul ediyor. **K2 kusuru bu yüzden 11/11 yeşilin
altında saklanıyor.** Sahteyi gerçek D1 gibi katı yap (`undefined` argüman görünce
`throw`) — bu tek değişiklik K2'yi kırmızı yakacaktır, sonra K2'yi düzelt.

---

## 0.2 🔴 MİMARIN KAYNAK OKUMASIYLA BULDUĞU BEŞ KUSUR — `shop/src/talep.js`

Bunlar TUR 1 çıktısı okunarak bulundu, ölçümle değil; **sen ölçerek doğrula**, sonra düzelt.
Her biri için kabul testine vaka koy (aksi hâlde düzeltme çürür).

### K1 🔴 `JSON.parse("null")` → İŞLENMEMİŞ ÇÖKME
```js
govde = JSON.parse(metin);
if (govde.website !== undefined && ...)   // govde === null ise TypeError
```
Gövde tam olarak `null` ise `null.website` **TypeError** atar; bu istisna yakalanmıyor →
uç 500/exception döner. Honeypot kontrolü tip kontrolünden ÖNCE koşuyor.
**Çare:** `alanlarGecerli`'nin nesne kontrolünü honeypot'tan ÖNCE çalıştır (ya da
honeypot'a nesne guard'ı ekle). **Vaka:** gövde `null` → 400, çökme YOK.

### K2 🔴🔴 `undefined` D1'e BAĞLANIYOR — HER EKSİK ALANLI TALEP DÜŞER (ÜRÜN SEVİYESİ)
```js
.bind(kod, tarih, govde.kanal, govde.kategori, ... govde.notu)
```
İsteğe bağlı alanlar (`kategori`, `marka`, `model`, `yil`, `parca_adi`, `notu`)
gönderilmezse `undefined` bağlanır. **D1 `undefined` KABUL ETMEZ** (`D1_TYPE_ERROR`);
yalnız `null`/string/sayı/boolean alır. Yani **eksik alanlı her talep D1'e YAZILAMAZ**,
müşteri `kod:null` alır ve kayıt HİÇ oluşmaz.
🔴 **Sahte `env.KATALOG` bunu ÖRTÜYOR:** `shop/test/talep.mjs`'teki sahte `bind` her şeyi
kabul ediyor, gerçek D1 etmiyor → test YEŞİL, ürün ÖLÜ. Deponun bilinen sınıfı:
*makineyi ölçtük, ürünü ölçmedik*.
**Çare:** her isteğe bağlı alanı `?? null` ile normalize et.
**Vaka:** (a) yalnız `kanal` + `parca_adi` gönderilen talep D1'e YAZILIR ve `kod` döner;
(b) sahte `bind` artık `undefined` görürse **DÜŞER** (sahteyi gerçek D1 gibi katı yap —
`undefined` argüman görünce `throw`). (b) olmadan (a) çürür.

### K3 🔴 `benzersizCakisma` ÇOK GENİŞ — YANLIŞ TEŞHİS (K176 sınıfı)
```js
metin.includes("UNIQUE") || metin.includes("PRIMARY KEY") || metin.includes("CONSTRAINT")
```
`CONSTRAINT` her kısıt hatasını yakalar (`NOT NULL`, `CHECK`, `FOREIGN KEY`). K2 ile
birleşince: gerçek bir `NOT NULL` hatası **kod çakışması** sanılır, 5 kez boşuna denenir,
sonra `sebep=kod_cakisma` etiketlenir. Müdahale yanlış yöne gider — kod evrenini
büyütmeye çalışırsın, oysa şema/bağlama hatası vardır.
**Çare:** yalnız `UNIQUE` ve `PRIMARY KEY` çakışması kod çakışması sayılsın; `CONSTRAINT`
tek başına **yetmez**. Diğer her şey EK HÜKÜM 5.2'ye göre `yapilandirma`.
**Vaka:** `NOT NULL constraint failed` hatası → `sebep=yapilandirma`, `kod_cakisma` DEĞİL,
ve **tekrar denenmez** (1 deneme, 5 değil).

### K4 DÖNGÜDEN SONRAKİ SATIR ÖLÜ KOD
Döngü `deneme 0..4` koşuyor ve her yolda `return` ediyor (`deneme < 4` değilse `else`
kolu döner). Döngüden sonraki `console.error(...)` + `return` **erişilemez**.
🔴 Tehlike: bir mutant ya da kabul testi çapasını bu satıra nişanlarsa **sessiz** geçer
(deponun bilinen tuzağı: *mutasyon çapası ölü kola nişanlanır*). Sil ya da döngüyü
gerçekten düşecek biçime getir. **Vaka:** ölü kol kalmadığını ölç.

### K5 GÖVDE TAVANI OKUMADAN SONRA — TAM TAMPONLAMA
`request.text()` gövdeyi TAMAMEN belleğe alıyor, tavan ondan SONRA bakılıyor. Kimliksiz,
herkese açık bir uçta bu bir yükseltme yüzeyi.
**Çare:** önce `Content-Length` başlığına ucuz ön-eleme (varsa ve tavanı aşıyorsa oku
BİLE deme), sonra yine BAYT ölçümü (başlık yalan söyleyebilir — ön-eleme ölçümün YERİNE
geçmez, ÖNÜNE geçer). **Vaka:** `Content-Length` tavanı aşıyor → `request.text()` HİÇ
çağrılmaz (sahte request'te sayaçla ölç) ve 400 döner.

**Ayrıca (kusur değil, sözleşme notu):** `alanlarGecerli` `kanal`ı ZORUNLU kılıyor
(`KANALLAR.has(govde.kanal)` — `undefined` kümede yok). Bu kabul edilebilir ama
**kapanış sözleşmesinde HocA'ya "kanal ZORUNLU" diye yazılacak**, yoksa Faz-2 alanı
göndermez ve her talebi 400 alır.

---

## 0.5 🔴 MİMARIN TUR 1'DE YAKALADIĞI KUSUR — `talep-temizlik.py` SAYAR ve SİLER FARKLI ÖLÇÜYOR

TUR 1 çıktısını okurken ölçüldü, düzelt:

```python
# SAYMA — ISO'yu GERCEKTEN ayristiriyor, "Z" son ekini +00:00'a cevirip karsilastiriyor:
zaman = datetime.fromisoformat(olusturma.replace("Z", "+00:00"))
if zaman < esik: sayi += 1

# SILME — ayni satirlari DUZ METIN olarak karsilastiriyor:
baglanti.execute("DELETE FROM talepler WHERE olusturma < ?", (esik.isoformat(),))
```

**İki farklı yordam, iki farklı sonuç.** `esik.isoformat()` `+00:00` üretir; kayıt `Z` ile
yazılmışsa metin sıralamasında `"Z"` (0x5A) > `"+"` (0x2B) → zaman olarak ESKİ olan bir
satır metin olarak "eski değil" çıkar. Sonuç: **kuru koşumun bastığı sayı ile `--uygula`nın
gerçekten sildiği satır sayısı AYRIŞIR.** Kuru koşum "3 satır gidecek" der, silme 1 satır
siler (ya da tersi) — ve kimse fark etmez, çünkü iki sayı hiçbir yerde karşılaştırılmaz.

Bu, deponun bilinen sınıfı: **geniş kabul aralığı + dar karşılaştırma aralığı = sessiz
ayrışma**. `yil` TEXT şerhinin (EK HÜKÜM 2) aynı sınıfı, bu sefer `olusturma` ekseninde.

**HÜKÜM:** sayma ve silme **TEK yordam** kullanacak. Tercih edilen çözüm — silinecek
satırları önce ayrıştırarak SEÇ, sonra `kod` listesiyle sil:
```
1. SELECT kod, olusturma FROM talepler
2. Python tarafinda ISO ayristir, esikten eski olanlarin `kod` listesini cikar
3. --uygula ise: DELETE FROM talepler WHERE kod IN (...)   (parcali, tavanli)
```
Böylece "sayılan küme" ile "silinen küme" **aynı kümedir**, ayrışamaz.

**Kabul tablosuna EKLENEN iddialar:**

| # | İddia | Şerit |
|---|---|---|
| F1 | Fikstür: `Z` son ekli ve `+00:00` son ekli, 89 ve 91 günlük **dört** satır. Kuru koşumun bastığı `SILINECEK` sayısı, `--uygula` sonrası **gerçekten silinen** satır sayısına EŞİT | B |
| F2 | `Z` son ekli 91 günlük satır **silinir** (metin karşılaştırması onu kaçırıyordu) | B |
| F3 | `Z` son ekli 89 günlük satır **KALIR** (negatif vaka — fazla silme yok) | B |
| F4 | Ayrıştırılamayan `olusturma` değeri olan satır **SİLİNMEZ** (fail-closed: tanıyamadığını atma) | B |

Ayrıca `--kendini-test` bugün yalnız iki satır (`89`/`91`, ikisi de aynı biçim) ile
koşuyor — **fikstür kusuru bu hatayı KÖR EDİYORDU**. Fikstürü F1–F4'ü kapsayacak
şekilde büyüt.

---

## 1. CI KABLOLAMA (spec §6 — şerit kararı MİMAR HÜKMÜ, değiştirme)

### 1.1 BLOKLAYICI kol → `.github/workflows/deploy.yml`, `serit-a3` job'u
`serit-a3` job'u `deploy: needs:` listesinde GEÇER (deploy.yml:1322) → yayını **bloklar**.
Oraya `continue-on-error`**SUZ** adım ekle:

```yaml
      - name: "Talep hatti sizinti kapisi (PII + allow-list + honeypot + govde tavani, BLOKLAYICI)"
        run: python3 tools/talep-hatti-test.py --sizinti
```

### 1.2 SERIT B kolu → `.github/workflows/nobet.yml`
Kendi adımlarıyla (bu iş yayını BLOKLAMAZ, bilerek):
```yaml
      - name: "Talep hatti TAM batarya + mutasyon (SERIT B)"
        run: python3 tools/talep-hatti-test.py
      - name: "Talep temizlik surucusu: kendini test (iki yonlu, SERIT B)"
        run: python3 tools/talep-temizlik.py --kendini-test
```

🔴 **Beyan ölçüm değildir.** Bir adımın "bloklayıcı" olduğunu YAZMAK yetmez —
`nobet.yml`de duran adım kırmızı yansa bile yayın GEÇER. Raporda bağladığın job adını
**dosya:satır** ile ver ve `deploy: needs:` satırını da alıntıla.

### 1.3 `tools/ci-kapsam-test.py`
Üç yeni dosya (`tools/talep-hatti-test.py`, `tools/talep-temizlik.py`,
`shop/test/talep.mjs`) bu kapının beyan/kapsam envanterine girecek.
**Kapanış kapısı: `python3 tools/ci-kapsam-test.py` → rc=0.** rc≠0 ile iş TESLİM EDİLMEZ.
Muafiyet yazma — üçü de gerçekten CI'da koşuyor, kapsanan olarak görünmeliler.

---

## 2. MUTASYON BATARYASI (spec §5.1 — K182 kuralı)

Her iddia için hedef kolu öldüren bir mutant, ve mutantın **O KOLU** öldürdüğünün AYRI
kanıtı. Bu depoda ölçülmüş üç tuzak — üçünden de kaçındığını raporda göster:

1. **Mutant yan ekseni de tetikliyorsa ölçmez.** Mutant hedef kolu öldürürken iddia
   sayısını / imzayı / başka bir ekseni de kırıyorsa, hedef kol ÖLÜ olsa bile kırmızı
   gelirdi → o mutant hiçbir şey kanıtlamaz. Her mutantın **yalnız** hedef iddiayı
   düşürdüğünü göster (düşen iddia listesi = tek eleman).
2. **Mutasyon çapası ölü kola nişanlanır.** Savunma sırası (spec §3.1) yüzünden bu uçta
   risk YÜKSEK: örneğin gövde-tavanı (B3) mutantını ölçerken istek Origin'i GEÇERLİ
   olmalı, yoksa mutant Origin kolunda ölür ve SESSİZ döner.
3. **Çapalar benzersiz.** İki mutant aynı metne çapalanırsa batarya kırılır.

`rc=1` "mutant yakalandı" DEMEK DEĞİLDİR — testin çöktüğü de `rc=1`'dir. Mutant
raporunda **komut + ham çıktı + çıkış kodu** bulunacak.
Mutasyon diske yazıyorsa `__pycache__` temizle ve mutasyonu `finally` ile GERİ AL.
Bitince `git status` ile ağacın mutasyon artığı taşımadığını **ölç**.

---

## 3. REGRESYON (spec §7 — bozmadığını KANITLA)

- `python3 tools/ci-kapsam-test.py` → **rc=0**
- `shop/test/` mevcut koşum satırı (önce `shop/test/kabul.js` ve `shop/KURULUM.md`'ye
  bak, deponun gerçek koşum komutunu kullan) → **düşen 0**
- `python3 tools/d1-sync.py --kendini-test` → `d1-sema.sql` ile ikiz olan şema fikstürü
  (`IKIZ TANIM UYARISI` yorumu) yeni tablodan etkilendiyse **fikstürü de güncelle**,
  testi SUSTURMA.
- `python3 tools/komut-stili-kapisi.py` ve `python3 tools/kisisel-veri-test.py` varsa koş.

🔴 `python3 tools/d1-sync.py --sema` **KOŞTURMA**. `wrangler deploy` **YAPMA**.
Canlı D1'e hiçbir yazma yok.

---

## 4. RAPOR — worktree kökünde, deponun kanonik mühendis-rapor adıyla (CLAUDE.md'de yazılı; BAŞKA AD YASAK)

Sayılarla, iddia değil ölçüm:

1. **Kabul:** `talep-hatti-test.py` bayraksız ve `--sizinti` kollarının
   `IDDIA / DUSEN / MUTANT / KONTROL` sayıları + çıkış kodları (ham çıktı).
2. **CI kablosu:** bağlanan job adı + `dosya:satır` (deploy.yml ve nobet.yml ayrı ayrı)
   + `deploy: needs:` satırı alıntısı + `ci-kapsam-test.py` rc.
3. **Mutasyon:** her mutant için hedef iddia, komut, ham çıktı, çıkış kodu, ve
   "yalnız bu iddia düştü" kanıtı.
4. **Regresyon:** §3'teki her komutun çıkış kodu.
5. **ŞEMA — UYGULANMADI, ONAY BEKLİYOR:** `talepler` migration SQL'i AYNEN + uygulama
   komutu ve SIRASI (`python3 tools/d1-sync.py --sema`, sonra doğrulama
   `python3 tools/d1-sync.py --durum`). "Uyguladım" YAZMA — uygulamadın.
6. **Saklama süresi kararı:** 90 gün, gerekçesi, `talep-temizlik.py` kullanımı,
   `--uygula`nın KOŞULMADIĞI beyanı.
7. 🔴 **HocA'ya SÖZLEŞME BLOĞU** (Faz-2 bunun üstüne kuracak, eksiksiz olacak):
   - `talep_kodu` regex'i + alfabe + neden bu alfabe
   - `POST /api/shop/talep` gövde şeması: TAM anahtar listesi + her alanın tip/tavanı
     + `kanal` kapalı kümesi + honeypot alan adı
   - Yanıt şekilleri: başarı / RED / D1-hatası (üçü de gövdeleriyle)
   - `talepler` tablosu TAM alan listesi + `durum` kapalı kümesi + `eslesen_urun_id`'nin
     Faz-2'ye bırakıldığı notu
   - `notu` (≠ `not`) ve `yil` TEXT sapmalarının gerekçesi
8. **Ölçemediğin her şey:** `OLCULEMEDI` + sebep. **Sayı uydurma.**

---

## 5. YASAKLAR
- `git commit` ATMA (sandbox `.git` kilidine yazamaz — boşa iş). Commit'i koordinatör atar.
- `git push` / merge **YOK**.
- `urunler.json` ve `index.html`'e **DOKUNMA** (K184 chip'i orada çalışıyor).
- Komut stili: dolar-değişken, dolar-parantez, `for`, `while`, `cd`, çıktı yönlendirme,
  heredoc **YASAK**. Betiği dosyaya yaz, `python3 /tam/yol.py` ile koş.
