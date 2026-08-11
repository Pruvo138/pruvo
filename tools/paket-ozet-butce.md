# PAKET — ozet.json bütçe payı (kayıpsız küçültme)

**Kat: MÜHENDİS / Opus.** Bu ölçüm+kapı kodudur — yanlış ölçüm sessizce yanlış karar üretir.
Codex'e VERİLMEZ (`skill: codex-isci` §4 "Ölçüm/kapı kodu").
**Mimar: KraL.** Tek yazar; `urunler.json` düzlemine DOKUNULMAZ (MaCiT).

---

## 1. NEDEN (ölçülen durum, 11 Ağu 2026)

`ozet.json` sitenin ilk boyama iş paketi: marka/kategori sayaçları, parametrik havuz, blok
havuzları (Marin 100 + Otomobil 100) ve en yeni 48 kart. Tarayıcı ilk ekranı **ağa çıkmadan**
bundan çizer; edge Worker'a ulaşılamazsa yedek arama havuzu da budur.

| Ölçüm | Değer | Kaynak |
|---|---|---|
| Canlı `ozet.json` (sıkıştırılmamış) | **127.401 B** | `curl` + `wc -c`, 11 Ağu 2026 |
| Tavan `OZET_BUTCE` | **153.600 B** (150 KB) | `tools/build.py` |
| Doluluk / pay | **%83,0** / 26.199 B | türetildi |
| Katalog | 25.554 ürün | `tools/durum.py` |

**Kapı bugün neden yayını durdurmuyor:** `build.py`'deki aşım kolu `EDGE_KATALOG` bayrağına
bağlı — bayrak KAPALI iken `UYARI`, AÇIK iken `sys.exit(1)`. `durum.py`'ye göre bayrağın
**"mecburi" eşiği 14.000 üründü ve katalog 25.554'te**: bayrak açıldığı gün bu tavan uyarıdan
**yayın durduran hataya** döner ve elde 26 KB pay kalır.

## 2. YASAK — bu paket tavanı YÜKSELTMEZ

`OZET_BUTCE` satırının üstünde 9 Ağu 2026 mimar kararı yazılı: tavan elle yükseltilerek
"çözülmez", çünkü aynı kırmızı bir sonraki katalog partisinde geri gelir. Ayrıca o satır
**TEK KAYNAK** — `tools/faz3-yuk.js` onu regex ile okur, kendi kopyasını tutmaz.

- `OZET_BUTCE` değeri DEĞİŞMEZ. `ILK_YUK_BUTCE` de değişmez.
- Havuz düğmesi (`VITRIN_BLOKLAR` `havuz`) DÜŞÜRÜLMEZ. 9 Ağu'da 100→88 düşürüldü, aynı gün
  kayıpsız kart temsili gelince 100'e geri alındı; çeşitlilik kaybı kalıcılaştırılmayacak.
- Kart DEĞERİ kaybedilmez. Yalnız **temsil** küçülür; alan silmek/kırpmak bu paketin işi değil.

## 3. ÖNEMLİ DÜZELTME — büyüyen kalem HAVUZ DEĞİL

`index.html` `VITRIN_BLOKLAR` bloğundaki ölçüm kaydı ve `tools/faz3-yuk.js` aynı şeyi söylüyor:
kart SAYISI sabittir (parametrik + 100 + 100 + 48), katalogla büyüyen kalem **`markalar`
haritası**dır (9 Ağu'da 30.136 B ölçülmüştü) ve kart metinleri (açıklama 160 karaktere kadar)
gün içinde oynar. Aynı kayıt kalıcı çözüm için iki kolu ADIYLA gösteriyor:
**(a) kart temsilinin kayıpsız sıkıştırılması**, **(b) `markalar` haritasının eşikle kırpılması.**

🔴 Bu yüzden FAZ 1 zorunludur ve atlanamaz: hangi kolun ne kadar kazandırdığı **bugünkü**
artefakttan ölçülmeden kod yazılmaz. 9 Ağu sayıları bayattır (o gün kayıpsız temsil devreye
girdi, katalog o günden beri ~2.400 ürün büyüdü).

## 4. FAZLAR

### FAZ 1 — BAYT ATIFI (ölçüm, kod değişikliği YOK)
`ozet.json`'un **her üst düzey anahtarı** için bayt payını çıkar: `kartAlanlari`, `kategoriler`,
`markalar`, `parametrik`, `bloklar`, `yeni`, `vitrin`, kalan skalerler. Her kalem için ayrıca
**katalogla büyüyor mu** eksenini ölç (iki farklı katalog boyutunda üret, eğimi bas).

Çıktı: bayt tablosu + büyüme eğimi. **Hangi kolun seçileceğine bu tablo karar verir**, bu belge
değil. Tablo "(a) ve (b) birlikte bile %25 pay bırakmıyor" diyorsa DUR ve mimara dön.

### FAZ 2 — KOLU UYGULA (FAZ 1 tablosunun gösterdiği)
Aday kollar (biri, ötekisi ya da ikisi — tabloya göre):
- **(a) Kart temsili:** bugünkü v2 sabit-sıralı dizi temsilinin ÜSTÜNE kayıpsız bir adım.
  Kısıtlar: `kart_ozeti` ŞEKLİ kardeş depodaki Worker `KART_ALANLARI` ile aynı kalmalı
  (sözleşme `build.py:kart_ozeti` docstring'inde yazılı); temsil değişirse `ozet.surum`
  BUMP edilir ve `index.html` her iki sürümü de açabilmelidir (bayat tarayıcı önbelleği).
- **(b) `markalar` haritası:** eşikle kırpma. 🔴 Kırpma marka çiplerini/sayaçlarını
  SESSİZCE düşürebilir — edge modunda `index.html` sayımları ozet.json'dan okuyor. Kırpılan
  markanın çipi kaybolmamalı ya da kaybı ölçülüp BEYAN edilmeli.

### FAZ 2b — TEMSİL BAYRAĞINI AÇMA YORDAMI (okuyucu önce, yazıcı sonra)

Kol (a) uygulandı ama **iki aşamalı** yayınlanır: `tools/build.py` içindeki TEK KAYNAK
`OZET_TEMSIL_SURUM` varsayılan **2**'dir (artefakt v2, bayrağın öncesiyle BAYT BAYT aynı).
**Yayın N** yalnız v3'ü *açabilen* `index.html`'i çıkarır — yeni istemci eski artefaktı
zaten sorunsuz açtığı için kimse etkilenmez. `index.html`'in tarayıcı önbelleği döndükten
**≥4 saat sonra** ([[tarayici-onbellek-4saat]]) **Yayın N+1**'de sabit `3` yapılır; kazanç
(21.766 B, %17,4) o an devreye girer. Neden bölündü: ölçüldü ki bayat önbellekli ESKİ
`index.html` v3 artefaktı alırsa boş kart çizmez ve fiyat/beyan bozulmaz, ama **223 kartın
kapağı** yer tutucuya düşer; iki aşamalı yayın bu pencereyi bayt kazancından vazgeçmeden
sıfırlar. Doğrulama tek komut — **`node tools/ozet-temsil-test.js`** (iddia 8 bayrağın
KAPALI varsayılanını, iddia 9 gerçek katalogda iki hâli ve bayat istemci penceresini
sayıyla ölçer; `--mutasyon` bayrağı yok sayan mutantı KIRMIZI yakar). Bayrak açıldıktan
sonra `node tools/faz3-yuk.js` + `python3 tools/edge-kart-kapisi.py` yeniden koşulur.

### FAZ 3 — PAY NÖBETÇİSİ (kalıcı kol)
Bugünkü kapı yalnız **tavan aşıldığında** konuşuyor; aşım anında iş zaten geç. Pay eksenini
ölçen bir kol ekle: pay eşiğin altına düştüğünde **bayrak KAPALI iken de** görünür uyarı,
`EDGE_KATALOG` AÇIK iken fail-closed. Eşik ve gerekçe FAZ 1 eğiminden türetilir (kaç partilik
runway bırakıyor), bu belgeden değil.

⚠️ Kapı disiplini: yeni bloklayıcı bir duvar EKLEME — mevcut aşım kolunu pay eksenine genişlet.
`deploy.yml`'de `continue-on-error` yok; yanlış-pozitif TÜM ekibin yayınını durdurur.

## 5. KABUL — çalıştırılabilir, "bakıldı iyi" DEĞİL

1. `python3 tools/build.py` çıktısındaki `ozet.json: <bayt> ... | butce 150 KB` satırı —
   **öncesi/sonrası** bayt farkı raporda SAYIYLA yazılı. (build LOKALDE koşulmaz kuralı bu
   pakette geçerli DEĞİL: mühendis kendi worktree'sinde ölçer, üretilen statik sayfaları
   commit ETMEZ.)
2. `node tools/faz3-yuk.js` → `✅ ozet.json <x> < <butce>` ve pay FAZ 3 eşiğinin üstünde.
3. `python3 tools/edge-kart-kapisi.py` → rc 0 (kart şekli sözleşmesi bozulmadı).
4. `node tools/vitrin-siralama-test.js` → rc 0 (havuz/blok kuralı korundu).
5. `python3 tools/marka-sayac-kapisi.py` → rc 0 (marka sayacı/çipi kaybolmadı — (b) kolu
   seçildiyse ZORUNLU).
6. `node tools/parite-test.js` + `node tools/parite-ege.js` → rc 0, TAM küme (örnekleme YASAK).
7. **Mutasyon kanıtı:** FAZ 3 nöbetçisi için en az 3 mutant, her biri KIRMIZI yanmalı —
   (i) pay eşiği kaldırılırsa, (ii) bayt ölçümü yanlış anahtardan okunursa, (iii) `surum`
   bump'ı düşürülüp eski istemciye yeni temsil verilirse. Sürücü **repoda kalır**
   (anlatılan batarya kanıt değildir).
8. `python3 tools/ci-kapsam-test.py` → yeni nöbetçi CI'da GERÇEKTEN koşuyor mu.

## 6. TESLİM

- Dal: `muh/ozet-butce-payi`. Rapor: dalda, kanonik rapor adıyla (ad CLAUDE.md İLETİŞİM PROTOKOLÜ'nde tanımlı; başka ad YASAK, izlenen bırakılmaz).
- Rapor FAZ 1 tablosunu, seçilen kolu ve GEREKÇESİNİ, kabul maddelerinin çıkış kodlarını
  sayıyla taşır. Ölçülemeyen madde "yeşil" değil **ÖLÇÜLEMEDİ + sebep** yazılır.
- Merge KraL'da, `skill: merge-kapisi` ile.
