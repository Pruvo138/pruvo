# PAKET — Sarı Seri 3D Önizleme FAZ D
## (fiyat kalibrasyon senkronu + 3 yeni aile önizlemeye + kalan 13 ailenin eşlem kalibrasyonu)

**Kat:** Claude Mühendis (güçlü model, yüksek efor). Sebep: fiyat semantiği + gizli eşlem
dosyası = hatası SESSİZ iş sınıfı (yanlış katsayı "doğru görünen" fiyat üretir).
**Çalışma şekli:** worktree dalında; merge = yayın kapısı (aşağıda). `urunler.json`'a DOKUNMA.
**Önce oku:** `DEVAM.md` (Faz C kapanış + "3 EKSIK URETEC HAZIR" bölümleri),
`onizleme/KURULUM.md`, `tools/paket-onizleme-3d.md` (Faz C paketi, desenler orada),
`~/dev/pruvo-jenerator/dogrulama/KAYNAK.md`. Onay/yargı soruları MİMARA (Okan'a değil).

---

## Neden Faz D (bağlam)

- Faz C kapandı: önizleme canlı, bayrak AÇIK, 2 pilot aile
  (`olcuye-ozel-profil-beam`, `olcuye-ozel-oring-conta`). Kapı-1 canlı ölçümü geçti.
- `jenerator/hacim.js` FİYATIN tek kaynağı (shop sunucu-tarafi yeniden hesap da onu okur).
  Konektör + braket formülleri v1; v2 kalibre kaynağı `~/dev/pruvo-jenerator/dogrulama/`
  (test/aileler + urunler; 3 üreteç pruvo-jenerator 6087d14'te hazır, kabul 51 set yeşil).
  Ölçülen sapma: **konektör +%5.2, braket −%17.5.** `PARAMETRIK_ODEME_ACIK` açılmadan
  bu senkron ŞART.
- hacim.js TÜM ailelerde pruvo-jenerator'e kalibre edilmişti; üretim motoru ise (3 yeni
  aile hariç) ölçüye-özel üretim motorudur → kalan 13 ailenin eşlem kalibrasyonu
  4d-benzeri testle ÖLÇÜLMEDEN önizlemeye alınamaz.

## İş kalemleri

### A) Fiyat kalibrasyon senkronu — konektör + braket
Canlı `jenerator/hacim.js` (+ gerekiyorsa `jenerator/urunler/olcuye-ozel-baglanti-konektor.json`
ve `olcuye-ozel-montaj-braketi.json` varsayılan/taban hacimleri) v2 kalibresine senkronlanır.
- Referans: `~/dev/pruvo-jenerator/dogrulama/` setleri. El kopyası yerine **çalıştırılabilir
  senkron testi** yaz (örn. `jenerator/test/kalibrasyon-senkron.js`): canlı hacim.js'i
  dogrulama referans setlerine karşı koşar, sapma ≤%3 ister. Önce MEVCUT kodda KIRMIZI
  yandığını gör ve rapora yaz (test tesiri kanıtı) — sonra senkronla yeşile çek.
- Taban hacim değişirse `tools/taban-fiyat-tablosu.md` satırındaki taban hacmi de güncelle
  (Okan fiyatları henüz doldurmadı; çelişki bırakma).

### B) O-ring pah katsayısı düzeltmesi — **OKAN ONAYINA TABİ, onay gelmeden UYGULAMA**
hacim.js o-ring "pahlı" katsayısı 0.875, eski motora (0.25×CS pah) kalibre; üretim
motorunun pahı 0.18×CS → doğru katsayı ~0.9352, fiyat etkisi ~%6 (fiyat kuralı: değişiklik
SADECE Okan'dan). Mimar onayı iletince: katsayıyı düzelt, `onizleme/test/kabul.js` 4d
[BILGI] satırındaki %6.27 sapmanın ≤%1'e indiğini göster. Onay gelmezse bu kalemi
"BEKLIYOR" olarak raporla, diğer kalemleri bloklamaz.

### C) 3 yeni aile önizlemeye (konektör / braket / dişli v2)
Bunlar BİZİM üreteçlerimiz (pruvo-jenerator, tedarikçi kodu değil) — eşlemleri PUBLIC
`jenerator/test/esleme/` deseniyle gider, gizli eşleme KARIŞTIRILMAZ.
1. .scad'lar önizleme derleme paketine (tar.gz) eklenir; kanonik kopya
   `tools/onizleme-paket-yukle.py` ile R2'ye yeni sürüm olarak yüklenir.
2. `secenekler.js ONIZLEME_AILELER` 2→5 (tek kaynak; worker + build.py aynı listeyi okur).
   **DİKKAT — yayın kapısı:** `ONIZLEME_3D_ACIK=true` canlıda; listeye aile eklemek =
   butonun o ürün sayfalarında MÜŞTERİYE görünmesi. Bu yüzden bu değişiklik worktree
   dalında kalır, main'e merge MİMAR kabulü + Okan görünürlük onayı sonrası.
3. `onizleme/test/kabul.js` kapsamı 5 aileye genişler: 4a şema kapısı, 4b enjeksiyon,
   4c önbellek anahtarı, **4d hacim ≤%3 (gerçek openscad, aile başına N=5 set × 2 tohum)**,
   4d+ üretilemez kombinasyon 422, 4f hız limiti.
4. CI imaj duman testi (`.github/workflows/onizleme-imaj.yml`) 2→5 aileye çıkar
   (tek-aile dumanının yanılttığı Faz C dersi). İmaj güncellenirse wrangler.toml digest
   sabitleme akışına uy (mutable tag TUZAK — KURULUM.md).
5. Deploy sonrası `onizleme/test/kapi1.js` yeni ailelerle koşulur: **p95 ≤ 10 sn.**

### D) Kalan 13 ailenin eşlem kalibrasyonu (ölçüm + hazırlık; yayın AYRI karar)
18 aile − 2 pilot − 3 yeni = 13. Üretim motoru ölçüye-özel üretim motoru → her aile için:
1. **Keşif pakete dahil:** hangi ailenin üretim motorunda karşılığı var/yok — sayıyı ve
   listeyi rapora yaz (karşılığı olmayan aile mimara çıkar, uydurma eşlem YAZILMAZ).
2. Karşılığı olan her aile için gizli eşlem girdisi (`onizleme/derleyici/eslem-ozel.json`,
   gitignore'lu; kanonik R2 paketi) + **4d-benzeri ölçüm**: hacim.js kapalı-form vs gerçek
   openscad STL hacmi, N=5 set × 2 tohum, hedef ≤%3.
3. Sapması >%3 çıkan aile SESSİZCE eklenmez/uydurulmaz → ölçülen sayıyla mimar listesine.
4. **GÜNCELLEME (Okan kararı, 16 Tem gece): hedef TÜM sarı ailelerde önizleme.**
   4d ölçümü ≤%3 geçen HER aile aynı dalda `ONIZLEME_AILELER`'e eklenir (görünürlük
   onayı verildi; yayın yine merge kapısından geçer). Geçemeyen aile eklenmez, ölçülen
   sapmayla rapora — düzeltme turu ayrı iş. Çıktı: aile başına sapma tablosu (rapor +
   DEVAM.md) + nihai aile listesi.

### E) Önizleme model rengi: gri → parlak sarı (Okan kararı, 16 Tem gece)
`jenerator/viewer.js` model rengi sarı seri kimliğine çekilir: parlak sarı (sitedeki sarı
rozet rengiyle uyumlu ton mühendis seçer). Flat shading'de saf sarının yüzey detayını
yutmamasına dikkat (gölgeleme/kontrast okunur kalsın; zemin rengiyle çakışmasın).
Kanıt: en az bir pilot ürün sayfasında ekran görüntüsü (rapora).

### F) Sarı ürün sayfası seçici düzeni normal ürün sayfasıyla eşitlenir (Okan, 16 Tem gece)
Normal ürün sayfaları yeni seçici düzeninde (ekran görüntüsüyle onaylandı); sarı/parametrik
sayfalar eskide kalmış. Sarı sayfada da AYNI düzen olacak:
- Malzeme seçimi dropdown DEĞİL, kart/çip: her kartta ~sıcaklık aralığı + malzeme adı +
  kısa kullanım notu ("Ev içi", "Dış mekân / genel amaçlı", "Güneş + su", "Esnek / titreşim
  emici") + önerilende "TAVSİYEMİZ" rozeti (normal sayfadakinin birebir aynısı).
- Renk seçimi çip: Siyah / Beyaz / Gri / Diğer (+%15).
- Adet: −/+ basamaklı seçici.
- "Sepete Ekle" + WhatsApp butonları ÜSTTE, renk/adet bloğunun yanında (normal sayfa
  hizası) — sayfa altında bırakılmaz.
- Karbon fiber/mühendislik malzemesi WhatsApp notu + "Malzeme Rehberi →" linki aynı yerde.
- Fiyat satırı sarı kuralına uyar: taban fiyat girilmediği sürece "Ölçüye özel fiyat"
  (normal üründeki "X TL'den başlayan" kalıbı ancak taban fiyat varsa).
**İKİNCİ KOPYA YAZMA:** normal sayfanın seçici bileşeni neredeyse (build.py şablonu /
ortak JS) sarı sayfa da ORADAN beslenir — kopyalanıp ayrışan iki seçici bloğu paket reddi
sebebidir. Kanıt: bir sarı ürün sayfası ekran görüntüsü + build iki-durum testi yeşil.

## Sır hijyeni (ihlali paket reddi sebebi)
- `eslem-ozel.json` gitignore'lu kalır; kanonik kopya R2 `pruvo-ozel` özel bucket'ında.
- Üretim motoru tedarikçi/üyelik adı HİÇBİR public dosyada, commit mesajında, test
  çıktısında geçmez ("ölçüye-özel üretim motoru" de).
- `jenerator/test/esleme/` (public) SADECE bizim pruvo-jenerator .scad'larımıza; gizli
  motor eşlemi oraya yazılmaz.
- Commit mesajları isimsiz; R2 anahtarları/token'lar sohbete/rapora yapıştırılmaz.

## Kabul testleri (mimar koşacak — hepsi çalıştırılabilir)
1. `node onizleme/test/kabul.js` → tümü yeşil, kapsam 5 aile; (B onaylıysa) o-ring
   [BILGI] sapması ≤%1.
2. `node jenerator/test/kalibrasyon-senkron.js` (yeni) → konektör+braket+3 yeni aile
   referans setlerine ≤%3; raporda "önce kırmızı" kanıtı.
3. D raporu: 13 aile × ölçülen sapma tablosu + karşılığı olmayanların listesi.
4. `node shop/test/kabul.js` → 9/9 yeşil (hacim.js regresyonu).
5. `node tools/parite-test.js` + `node tools/parite-ege.js` → yeşil (aramaya dokunulmadı
   kanıtı; `_nonce` tuzağına dikkat).
6. `KAPAT_ANAHTAR=... node onizleme/test/kapi1.js` (deploy sonrası, nihai listedeki TÜM
   ailelerle) → p95 ≤ 10 sn.
7. `tools/build.py` iki durum: mevcut main listesiyle yeni ailelerde buton YOK; dal
   listesiyle SADECE nihai listedeki ailelerde VAR.

## Rapor formatı
Ölçülen sayılar (sapma yüzdeleri aile aile, kapı-1 p50/p95, keşif sayıları), verilen/bekleyen
kararlar (B kalemi durumu), DEVAM.md güncellemesi. Öz-rapora güven yok: mimar kabulü
kendisi koşar (Codex pilotu dersi).
