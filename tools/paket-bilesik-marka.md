# PAKET — Bileşik marka adı kanonikleştirmesi (`Mercedes-Benz` → `Mercedes`)

**Mimar:** KraL · **Kat:** Opus (sessiz-hata: arama metni + kapalı küme + ikiz tanım)
**Okan hükmü:** "Mercedes-Benz bu kategori değil marka" + tam eşleme **`Mercedes-Benz` → `Mercedes`**.
**Kaynak ölçüm (MaCiT, tekrar ölçme):** 736 "marka-başı-kanonik-değil" kaydın kova ayrımı —
Kova1 (üretici) 500 · Kova2 (kanonikleştirme) 4 · Kova3 (belirsiz) 232. `Mercedes-Benz` **20 kayıt**,
bugün Kova3'te.

## 0. KARAR — NEDEN MEVCUT FONKSİYON GENİŞLETİLMİYOR

`arama.marka_varyanti_sebebi()`'nin kapsadığı küme **ölçülmüş bir YAZIM VARYANTI listesidir**
(BaoFeng/Citroën/Ikea/KIA/MINI/SMART/Ssangyong — TAM 7). `Mercedes-Benz` bir yazım varyantı
DEĞİL: kanonik markayı **İÇEREN bileşik ad**. Farklı kural sınıfı → **ayrı fonksiyon, ayrı
kapalı tablo, ayrı iddia.** İki sınıfı tek çapada eritmek 7'li çapayı anlamsız kılar.

🔴 **GENEL NORMALİZASYON YASAK.** "Tire/boşluk kırp, içeriyorsa eşle" türü bir kural
YAZILMAYACAK — `F-150`, `Rolls-Royce`, `D2-55`, `206+`, `K5` gibi meşru jetonları yer.
Tablo **kapalı ve elle yazılmış** olacak; bilinmeyen bileşik ad **sessizce eşlenmez**, olduğu
gibi kalır (fail-closed = eşleme yok, uydurma eşleme yok).

## 1. YAPILACAK (`tools/arama.py` — tek kaynak)

1. `BILESIK_MARKA_KANONIK` — kapalı, elle yazılmış eşleme tablosu. **Tek tohum:**
   `"Mercedes-Benz": "Mercedes"`. Başka giriş EKLEME (Okan yalnız bunu verdi).
2. `bilesik_marka_kanonik(deger)` + `bilesik_marka_sebebi(deger)` — `marka_varyanti_*` ile
   AYNI imza deseni, ama BAĞIMSIZ kod yolu. Birinin diğerinin bayrağını tekrar okuması YASAK
   ([[beyan-edilmis-survivor]]: aynı kod yolunu iki kez ölçmek iki iddia değildir).
3. **7'li çapa KORUNUR:** `marka_varyanti_sebebi()`'nin kümesi TAM 7 kalacak. Sayı değişirse
   kapı **fail-closed KIRMIZI** yansın — MaCiT'in kova ayrımı bu çapaya dayanıyor.

## 2. 🔴 ASIL RİSK — ARAMA JETONU KAYBI (bu paketin varlık sebebi)

`marka` = arama metni. `Mercedes-Benz` → `Mercedes` yazılırsa **"Mercedes-Benz" araması
o 20 ürünü bulamayabilir.** Bu tam olarak `marka = tekillestir(uyum[].marka + uyum[].model)`
kararını doğuran sessiz kayıp sınıfıdır.

**Şart:** kanonikleştirme sonrası `Mercedes-Benz` sorgusu aynı 20 ürünü **BULMAYA DEVAM
EDECEK**. Mekanizma (ham yazımın haystack'te kalması mı, sorgu tarafında normalizasyon mı)
mühendisin kararı — ama **ÖLÇÜLECEK**, varsayılmayacak. Ölçülemiyorsa "yeşil" DENMEZ.

## 3. KABUL TESTİ (iddialar `tools/uyum-kapisi.py`'ye eklenir)

Yeni workflow adımı AÇMA — `uyum-kapisi.py` zaten CI'da bloklayıcı koşuyor. İddialar oraya
eklenecek (bugünkü 29 iddiadan DÜŞMEYECEK):

| # | İddia |
|---|---|
| B1 | `bilesik_marka_kanonik("Mercedes-Benz") == "Mercedes"` (Okan'ın tam eşlemesi) |
| B2 | Tabloda OLMAYAN bileşik ad DEĞİŞMEDEN döner — uydurma eşleme yok |
| B3 | Meşru tireli jetonlar DOKUNULMADAN geçer: `F-150`, `Rolls-Royce`, `D2-55`, `206+`, `K5` |
| B4 | `marka_varyanti_sebebi()` kümesi TAM 7 — sayı kayarsa KIRMIZI (çapa nöbeti) |
| B5 | İki fonksiyon BAĞIMSIZ kod yolu: `bilesik_*` bozulunca `marka_varyanti_*` iddiası YEŞİL kalır ve tersi |
| B6 | **ARAMA PARİTESİ:** kanonikleştirilmiş kayıtta `Mercedes-Benz` sorgusu ürünü BULUYOR (jeton kaybı yok) |
| B7 | Katalog taraması: bugün `Mercedes-Benz` yazımını taşıyan kayıt sayısı ÖLÇÜLÜR ve rapora yazılır (beklenen 20; sapma varsa DUR, yazma) |

**Mutasyon:** `tools/uyum-mutasyon.py` (ya da kapının kendi `mutasyon()` kolu) genişletilir —
B1/B3/B4/B5/B6 için **TEK-KIRMIZI** mutant, `olcut` alanı **ESIT**, en az 2 kontrol mutantı,
kaynak sha256 başta/sonda aynı. Mevcut 13/13 mutant sayısı DÜŞMEYECEK.

**Fikstür disiplini:** `Mercedes` ile `Mercedes-Benz` dışında, tabloda olmayan ama benzeyen bir
bileşik ad (uydurma) fikstüre konacak — "tablo hiç okunmadı, hep içerdiği markayı döndürdü"
mutantını yeşil geçirmesin ([[fikstur-degeri-mutasyon-koru]]).

## 4. VERİ YAZIMI — BU DALDA YOK

`urunler.json`'a **HİÇBİR ŞEY YAZILMAYACAK**. Bu dal mekanizmayı ve kapıyı açar. 20 kaydın
yazımı MaCiT'in düzlemi ve AYRI tur; yazımdan önce arama paritesi ÖNCE/SONRA ölçülecek.
Raporda **etkilenecek kayıt sayısı** (ölçülmüş) bulunacak — yazım kararı bende.

## 5. ÇAKIŞMA UYARISI

Paralel bir dal `tools/duzelt.py` + `tools/duzelt-uyum-*.py` + `.github/workflows/deploy.yml`
üzerinde çalışıyor. **Bu dalda o dosyalara DOKUNMA.** `deploy.yml`'ye adım eklemek gerekirse
DUR ve raporla — yeni adım yerine mevcut `uyum-kapisi.py` iddiası tercih edilir.

## 6. TESLİM

Dalda `RAPOR-MIMARA.md` (bu ad ZORUNLU): iddia sayısı önce/sonra, mutant tablosu
(mutant → yakan iddia), koşulan her komutun ÇIKIŞ KODU, `node tools/parite-test.js` ve
`node tools/parite-ege.js` sonuçları, `Mercedes-Benz` taşıyan ölçülen kayıt sayısı, sha256
başta/sonda. Kırmızı varsa **commit atmadan** dur. Merge YAPMA — kapı mimarda.
