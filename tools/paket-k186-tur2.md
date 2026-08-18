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

## 0.17 🔴 KABUL TESTİNİN KENDİ KUSURLARI — `tools/talep-hatti-test.py` (mimar tam okudu)

Kaynak okundu, aşağıdakiler **teşhis edilmiş kök nedenlerdir**; tahmin değil.

### H1 🔴🔴 `DUSEN=1`İN KİMLİĞİ: **A1** — ve suç KODDA DEĞİL, SPEC'TE
`kod_ekseni`'nin A1 iddiası `veri["say"] == 100000 and not veri["tekrar"]`.
Doğum-günü sınırı: `30^6 = 729.000.000` evrende `100.000` çekim → beklenen çakışma ≈ **6,9**.
**Sağlam üreteç bile bu iddiayı HER KOŞUMDA düşürür.** Mutant ham çıktıları da bunu
gösteriyor: `{"say":99996,"tekrar":true}` = 4 çakışma, tam beklenen aralıkta.
**Çare:** spec'te **DÜZELTME A1** yazıldı (`tools/paket-k186-talep-hatti.md`) — iddia
"0 çakışma" değil **"farklı kod sayısı ≥ 99.900" (entropi tabanı)** olacak. Çakışma
sayısı İDDİA EDİLMEZ; tekilliği PRIMARY KEY + 5 deneme garanti eder.
Eşiğin ayırt ediciliği: sabit üreteç `say=1`, tek-karakter entropi `say=30`, sağlam
üreteç `~99.993` → üç büyüklük mertebesi fark, yanlış-pozitif riski yok.

### H2 🔴 MUTANT B4 ÖLÜ KOLA NİŞANLANMIŞ (B4'ün sağ kalma sebebi — KESİN)
```js
"B4": js.replace('if (!headers || typeof headers.get !== "function") { return false; }',
                 '... { return true; }')
```
Bu satır YALNIZ `headers` nesnesi YOK/bozuk olduğunda çalışır. Test fikstürü (`istek()`)
**her zaman** çalışan bir `headers.get` veriyor → mutasyona uğrayan kol **HİÇ
ÇALIŞMIYOR** → mutant fiilen no-op → doğal olarak yaşıyor.
B4 iddiası ise "Origin/Referer YOK → RED" — o karar `originIzinli`'nin **sonundaki**
`return false;` satırında veriliyor.
**Çare:** mutant o son `return false;` satırını `return true;` yapacak. (Çapa benzersiz
olmalı: dosyada birden çok `return false;` var → daha geniş, tek geçen bir çapa seç ve
`grep -c` ile 1 olduğunu ÖLÇ.)

### H3 🔴 A2/A3/A4 MUTANTLARI BİRDEN ÇOK İDDİA DÜŞÜRÜYOR
Ölçülen ham çıktılar:
```
A2 -> yasak:true  + bicim:false + tekrar:true   (hedefi A2, ama A3'ü ve A1'i de yakar)
A3 -> bicim:false + tekrar:true                 (hedefi A3, A1'i de yakar)
A4 -> say:1       + tekrar:true                 (hedefi kaynak iddiasi, A1'i de yakar)
```
⚠️ Düzeltme: A1 ve A4 **aynı mutasyon değil** (A1 üreteci sabitler, A4
`crypto.getRandomValues`'i `Math.random` yapar ve `bayt[0]` hiç güncellenmediği için
üreteç yine sabitlenir). Sonuç aynı görünüyor, sebep farklı. Asıl kusur: **üçü de hedef
dışı iddia düşürüyor** — K182 ihlali.
**Çare:** A ekseni iddialarını birbirinden BAĞIMSIZ ölç (her mutant için yalnız KENDİ
iddiasının değerine bak, diğerlerini o koşumda değerlendirme) ve raporda her mutant için
"düşen iddia listesi = tek eleman" göster.

### H4 🔴 C1–C5 MUTANTLARI HAM ÇIKTI BASMIYOR
`mutant_sonuclari` içindeki `print` yalnız `tur in ("kod","talep","node")` için çalışıyor;
`"source"` türü (C ekseni) **hiç satır basmıyor**. Beş bloklayıcı iddianın mutant kanıtı
çıktıda YOK — hüküm var, ham kanıt yok. **Çare:** C mutantları için de
`MUTANT <ad> ... base=<x> mutant=<y>` satırı bas.

### H5 🔴 `main()` B/D/E İDDİALARINI ÖNCE KOŞULSUZ `True` YAPIYOR
```python
for ad in iddialar:
    if ad.startswith(("B","D","E")): sonuclar[ad] = ... if args.sizinti else True
```
Sonra yalnız `dusen` varsa `❌ <ad>` satırları aranıp `False`'a çevriliyor. Yani hüküm
"ölçüldü" değil "aksi kanıtlanmadıkça doğru" temelinde kuruluyor — **fail-open**.
`talep.mjs` bir iddiayı hiç koşmazsa (ör. `--only` süzgeci, isim değişikliği, erken
`process.exit`) o iddia **YEŞİL** sayılır. **Çare:** `talep.mjs` her iddia için `✅/❌`
satırı bassın ve Python tarafı **her iddianın satırını GÖRDÜĞÜNÜ** doğrulasın; satır
yoksa `OLCULEMEDI` → fail-closed (`False`).

### H6 `kod_ekseni`'nde ÖLÜ KOD
İlk `ifade` ataması hemen ikincisiyle eziliyor ve içinde bozuk sözdizimi var
(`say:iym=s.size`). Sil — K4 ile aynı sınıf (ölü kol, mutasyon çapası oraya kayabilir).

### H7 C5 YANLIŞ-POZİTİF YÜZEYİ
`if "4005" in metin` üretim dosyalarının TAMAMINI tarıyor (`shop/src/index.js` dahil).
Bugün temiz, ama o dosyada herhangi bir yerde geçen `4005` alt-dizgesi (ör. bir sayı,
bir ID, bir tarih) **bloklayıcı kapıyı** kırmızı yakar ve yayını durdurur. Taramayı
telefon bağlamına daralt (`tel:` / `wa.me` / `contactPoint` yakınında) ve **negatif vaka**
yaz: bağlamsız bir `4005` alt-dizgesi kapıyı TETİKLEMEZ.

---

## 0.18 🔴 MİMAR ŞERHLERİ — H5 SAYI İNVARYANTI · A1 GEREKÇESİ · H7 TEK KAYNAK

### 0.18.1 H5'in yanına **SAYI İNVARYANTI** (tek ucuz çare)

"İddianın satırını gördüm mü" tek başına YETMEZ: iddia **adı** değişirse ya da bir blok
atlanırsa (erken `return`, `--only` süzgeci, `if` bloğu) test yine sessiz kalır — daha az
iddia koşar, hepsi yeşil görünür.

**Zorunlu:** beklenen iddia sayısı kaynağa **SABİT** yazılır ve her koşumda gerçekleşenle
karşılaştırılır:
```
BEKLENEN_IDDIA        = 20   (bayraksiz kol)
BEKLENEN_IDDIA_SIZINTI = 10   (--sizinti kolu)
```
Gerçekleşen ≠ beklenen → `OLCULEMEDI: <beklenen> iddia bekleniyordu, <gerceklesen> kosdu`
+ **sıfır-dışı çıkış**. Fail-closed. Bu, "sessizce eksilen iddia" sınıfını kapatan tek
ucuz invaryanttır.

| # | İddia | Şerit |
|---|---|---|
| G5 | Bir iddia bloğu devre dışı bırakılırsa (mutant: bir `iddia(...)` çağrısını sil) kapı **OLCULEMEDI** verip sıfır-dışı çıkar — "kalan hepsi yeşil" DEMEZ | 🔴 BLOKLAYICI |

### 0.18.2 A1 eşiğinin GEREKÇESİ KODA yazılacak

`≥ 99.900` eşiği yorumsuz bırakılırsa bir sonraki okuyan onu "0 çakışma olmalı" diye geri
sıkılaştırır ve testi **kalıcı kırmızı** yapar (bugün düşen iddia tam olarak buydu).
Eşiğin yanına iki satır + formül:
```
# Dogum-gunu siniri: evren N = 30^6 = 729.000.000, cekim n = 100.000
# Beklenen cakisma = n^2 / (2N) ~= 6,9 -> "0 cakisma" iddiasi SAGLAM uretecte bile duser.
# Uretecten ENTROPI istenir; TEKILLIGI `kod` PRIMARY KEY + 5 denemelik yeniden uretim
# garanti eder (D4/D10). Esik 99.900: beklenenin ~14 kati tolerans (yanlis-pozitif yok),
# ama entropi kaybinin her gercek bicimini yakalar (sabit uretec say=1, tek-karakter say=30).
```

### 0.18.3 H7 — telefon taraması TEK KAYNAKTAN türeyecek

Ham `"4005" in metin` alt-dizge taraması bloklayıcı kolda **tüm ekibin yayınını**
durduracak bir yanlış-pozitif yüzeyidir. Tarama, deponun kanonik numara kuralından
türesin (`…6526` yalnız WhatsApp bağlamı, `…4005` yalnız arama bağlamı) ve **bağlamla**
ölçsün: numara `wa.me` / `tel:` / `contactPoint` yakınında mı?

| # | İddia | Şerit |
|---|---|---|
| G6 | **NEGATİF:** telefon bağlamı OLMAYAN bir sayı dizisi (ör. bir ID, bir tarih, `4005` alt-dizgesi taşıyan rastgele bir sayı) kapıyı **TETİKLEMEZ** | 🔴 BLOKLAYICI |
| G7 | Gerçek ihlal (`wa.me/…4005` ya da `tel:…6526`) kapıyı **TETİKLER** | 🔴 BLOKLAYICI |

### 0.18.4 C1–C5 mutantları "şu iddia düştü" yazacak

H4'ü kapatırken yalnız "kırmızı geldi" yetmez; her C mutantının ham çıktısı **hangi
iddianın** düştüğünü söylesin (`base=<x> mutant=<y> dusen=<iddia adi>`).

---

## 0.25 🔴 MİMAR ŞERHLERİ — K2, K5 ve A EKSENİ İÇİN BAĞLAYICI EK

Bu üç madde §0.2'deki K2/K5 ve §0.15'teki A ekseni kalemlerini **daraltır**; TUR 2a
bunları kapsamadıysa TUR 2b'de kapanır ve kabulde AYRICA ölçülür.

### 0.25.1 K2 — sahtenin katılığı GERÇEKTEN TÜREMELİ, yoruma yazılmamalı

Sahte `env.KATALOG`'u katılaştırırken **ikiz tanım kurma**: "gerçek D1 `undefined` kabul
etmez" bilgisini bir yoruma yazıp sahteyi elle ayarlama. Katılık **davranıştan** türesin:
`bind(...args)` çağrısında argümanlardan herhangi biri `undefined` ise **FIRLAT**
(gerçek D1'in `D1_TYPE_ERROR`'ıyla aynı sınıf). Böylece sahte, gerçeğin sözleşmesini
taklit eder; iki ayrı "doğru davranış" tanımı doğmaz.

🔴 **ÜRÜN SEVİYESİ VAKA (yalnız sayaç yetmez):**

| # | İddia | Şerit |
|---|---|---|
| G1 | İsteğe bağlı alanların **HİÇBİRİ** gönderilmemiş minimal talep (`kanal` + `parca_adi`) → **`kod` ÜRETİLİR**, `kod:null` DEĞİL, ve D1'e **1 satır** yazılır | 🔴 BLOKLAYICI |

Gerekçe: bugünkü hatada müşterilerin ÇOĞU `kod:null` alacaktı — form isteğe bağlı alanları
boş bırakan herkes. Bu yolu `kod:null` sayacıyla (D9/D10) kapatmak yetmez; sayaç arızayı
*görür*, G1 arızanın *olmamasını* zorlar.

**Kapanış raporuna ders cümlesi (sınıf kalemi):** "Sahte D1 her şeyi kabul ediyordu,
gerçek D1 `undefined` kabul etmez — test 11/11 yeşilken ürün ölüydü."
→ `[[makineyi-olctuk-urunu-olcmedik]]`

### 0.25.2 K5 — tavan "kabul"ü değil **OKUMAYI** da sınırlamalı

Gövde tavanı `request.text()` TAMAMLANDIKTAN sonra bakılıyorsa tavan yalnız kabul
kararını değiştirir, **okumayı engellemez** — kimliksiz, herkese açık bir uçta bu tavanın
koruma amacını boşa çıkarır. İki katman, ikisi de gerekli:
1. `Content-Length` **ön kontrolü**: tavanı aşıyorsa `request.text()` **HİÇ** çağrılmaz.
2. Okuma sırasında **sert kesme**: başlık yalan söyleyebilir → gerçek BAYT ölçümü yine
   yapılır ve tavan aşılırsa reddedilir. (Ön kontrol ölçümün YERİNE değil ÖNÜNE geçer.)

| # | İddia | Şerit |
|---|---|---|
| G2 | `Content-Length` tavanı aşıyor → `request.text()` **çağrılmaz** (sahte request'te sayaçla ölç), 400 döner | 🔴 BLOKLAYICI |
| G3 | **NEGATİF:** meşru, büyük ama tavan ALTINDA gövde → `text()` çağrılır ve istek **REDDEDİLMEZ** | 🔴 BLOKLAYICI |
| G4 | `Content-Length` YALAN söylüyor (küçük beyan, büyük gövde) → gerçek bayt ölçümü yakalar, 400 | B |

### 0.25.3 A ekseni — ÇAPA BENZERSİZLİĞİ ÖLÇÜLECEK, VARSAYILMAYACAK

A1≡A4 ve A2'nin yan eksen yakması **K182'nin ta kendisi**. Üç zorunluluk:
1. Her mutantın çapa metni kaynakta **tam olarak 1 kez** geçmeli — bunu `grep -c` ile
   **ÖLÇ** ve sayıyı rapora yaz. 1 değilse çapayı değiştir, mutantı koşturma.
2. Her mutant **tam olarak BİR** iddiayı düşürsün; raporda "düşen iddia listesi = tek
   eleman" diye göster. A2 mutantı yalnız alfabeyi bozacak — biçimi ve tekilliği DEĞİL.
3. Test **hangi** iddianın düştüğünü bassın. `DUSEN=1` tek başına kanıt değildir.

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

## 0.6 🔴 TUR 2a SONRASI KALINTILAR — `tools/talep-temizlik.py` (mimar okudu)

F1–F4 doğru kuruldu (karışık `Z` / `+00:00` fikstürü + ayrıştırılamayan satır, sayma ve
silme artık **tek yordam**: `silinecek_kodlar`). İki kalıntı var.

### R1 🔴 `calistir` LİSTEYİ İKİ KEZ HESAPLIYOR — kapattığımız sınıf geri geldi
```python
kodlar = silinecek_kodlar(baglanti, esik)   # sayilan kume
sayi = len(kodlar)
if uygula and sayi:
    sil_eski(baglanti, esik)                # <-- listeyi YENIDEN hesapliyor
```
`sil_eski` aynı sorguyu **tekrar** koşuyor. Tek yazıcılı bir dosyada aynı sonucu verir,
ama `talepler` **canlı D1'de eşzamanlı yazılıyor** (site + Faz-2 WhatsApp): iki hesap
arasında satır eklenip silinebilir → **basılan sayı ile gerçekten silinen sayı yine
ayrışır.** F1'in kapattığı sınıfın ta kendisi, yalnız bu sefer sebep biçim değil YARIŞ.
**Çare:** `sil_eski(baglanti, kodlar)` — listeyi ARGÜMAN olarak al, yeniden hesaplama.
**Vaka (F5):** `sil_eski`ye verilen liste ile silinen satır kümesi **birebir aynı**;
fonksiyon kendi başına sorgu KOŞMAZ (mutant: içeride yeniden hesaplarsa iddia düşer).

### R2 🔴🔴 BU ARAÇ CANLI D1'İ TEMİZLEYEMEZ — SAKLAMA SÜRESİ FİİLEN UYGULANMIYOR
Araç `sqlite3.connect(yol)` ile **yerel bir dosyaya** bağlanıyor; `--db` yerel yol alıyor.
Gerçek depo ise Cloudflare **D1**'dir. Yani bugün:
- 90 günlük saklama süresi **hiçbir yerde uygulanmıyor**;
- araç yalnız *mantığı* ve *kendini testi* taşıyor, üretim yolu YOK.

🔴 **Raporda bu AÇIKÇA yazılacak, "temizlik aracı var" diye geçilmeyecek.** Aksi hâlde
biri saklama süresinin yürürlükte olduğunu sanır; oysa tablo sınırsız büyür ve
`pruvo-katalog` D1'i Ege + `d1-sync` + `reklam_ref_gclid` ile PAYLAŞILIR.
Rapora giren satır:
```
OLCULEMEDI/UYGULANMIYOR: 90 gunluk saklama suresi CANLIDA YURURLUKTE DEGIL.
talep-temizlik.py yerel sqlite uzerinde calisir; canli D1 yolu (wrangler d1 execute ya da
worker ucu) ACILMADI — altyapi/deploy karari, MIMAR/OKAN kapisi. ACIK KALEM.
```

---

## 0.7 🔴 MİMAR ŞERHLERİ — ORIGIN POLİTİKASI · İSTEMCİ TAVANLARI

### 0.7.1 `Origin`/`Referer` fail-closed — NEGATİF VAKA ZORUNLU
Kendi sayfamızın gönderemediği bir uç yayınlamak "kapıyı doğru kurup ürünü kırmak"tır.
Uçtan uca teyit K184 (site sihirbazı) chip'iyle yapılacak ve **merge ondan önce YOK**.
Bu pakette bize düşen, politikayı negatif vakasıyla yazmak:

| # | İddia | Şerit |
|---|---|---|
| G8 | **NEGATİF:** meşru aynı-köken isteği (`Origin: https://pruvo3d.com`) **REDDEDİLMEZ** — 200 döner | 🔴 BLOKLAYICI |
| G9 | **NEGATİF:** `Origin` yok ama `Referer: https://pruvo3d.com/...` var → **REDDEDİLMEZ** (tarayıcı bazı akışlarda `Origin` göndermez) | 🔴 BLOKLAYICI |
| G10 | `env.SITE_URL` host'u izinli kümeye GERÇEKTEN ekleniyor (staging/preview kökeni kırılmasın) | B |

### 0.7.2 İstemci tavanları uçla BİREBİR aynı — TEK KAYNAK
RED gerekçe vermiyor (güvenlik açısından doğru), ama o zaman 600 karakter yazan kullanıcı
**sebepsiz hata** görür. Tavanlar tek kaynaktan türeyecek; `ALAN_TAVANLARI` zaten
`shop/src/talep.js`'te `export` — K184 chip'i onu içe aktaracak, kendi kopyasını YAZMAYACAK.

| # | İddia | Şerit |
|---|---|---|
| G11 | `ALAN_TAVANLARI` dışa aktarılmış ve **tek tanım**; repoda ikinci bir tavan tablosu YOK (eksen taraması) | B |

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

### 1.0 🔴 ÖNCE TABAN ÖLÇ — kablolamadan ÖNCE

Kablolamaya dokunmadan **önce** koş ve çıkış kodunu kaydet:
```
python3 /Users/okan/dev/pruvo/.claude/worktrees/zen-lehmann-d54167/tools/ci-kapsam-test.py
```
Sebep: bu kapı bizim dalımızdan bağımsız sebeplerle de kırmızı olabilir. Tabanı
ölçmeden kablolarsak, sonradan gelen kırmızıyı yanlış yere (bizim değişikliğimize)
yazarız — ya da tersi, zaten kırmızı olan bir kapıyı "biz bozmadık" diye susturmaya
çalışırız. **Taban rc rapora yazılır**, kablolama sonrası rc ile YAN YANA.

Taban rc≠0 ise: sebebini oku. Bizim dalımızla ilgisizse rapora `KAPSAM DISI: taban
zaten kirmizi, sebep=<...>` yaz ve kendi kablolamanı yine de tamamla — başkasının
kırmızısını onarmak bu paketin işi DEĞİL, ama onu bizim kırmızımız gibi göstermek de yasak.

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
