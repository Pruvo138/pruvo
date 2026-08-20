# PAKET — VARYASYON PROGRAMI (sağ/sol · tek/çift · uzun/kısa)

> Okan emri (20 Ağu 2026): *"MaCiT birçok ürünü sağ/sol – tek/çift ayırt etmeden torba yapmış;
> her seferinde müşteriyi aramak yerine bunu sayfaya eklemeliyiz. Bu tür varyasyonları daha
> fazla kullanacağız, hazırlığını buna göre yap."*
> Mimar (KraL) ölçümü + faz planı. **Ölçütler faz faz çivilidir; tur içinde büyütülmez.**

## 1. ÖLÇÜLEN DURUM — RAY ZATEN VAR (20 Ağu, KraL, kaynaktan)

`boy_secenekleri` alanı müşteriye giden zincirin **tamamında kablolu**:

| katman | kanıt |
|---|---|
| şema + doğrulayıcı | `tools/arama.py:2585` tip · `:2601 boy_secenekleri_sebebi` (dizi · nesne · bilinmeyen alt alan · `etiket` boşluksuz ≤60 · etiketler BENZERSİZ · `fark_tl` negatif olmayan TAM SAYI) · `:2646` alan→doğrulayıcı dağıtıcısı |
| sayfa üretimi | `tools/build.py:3600 · 3744 · 3786 · 3882 · 4572` (kart + detay) · `:4512` "sepet fiyatını etkileyen alanlar" listesinde |
| seçim + fiyat | `secenekler.js:278-281` — seçilen etiketin `fark_tl`'si fiyata ekleniyor |
| sipariş ucu | `shop/src/index.js:278` D1 kolonu · `:350-355` parse + **yeniden doğrulama** (`Number.isInteger(fark_tl) && >= 0`) · `:430` taşıma |
| D1 | `tools/d1-sync.py` kolon senkronu |

**Katalogdaki fiili kullanım: 2 ürün.**
- `pr634138-volvo-besik-burcu-takma-aleti` — Kovan/Pimli/Pimsiz (3) · `4f855840` (18 Ağu):
  **3 ayrı kayıt TEK ürüne birleştirildi** → var olan ürüne SONRADAN eklenmiş emsal.
- `vw-t5-dugme-yuvasi-kor-kapagi` — Tekli / Uzun **+100 TL** · `fb53b496` (17 Ağu): doğuşta.

⇒ **Eksik olan tek şey yazma yolu**, ray değil.

## 2. ÖLÇÜLEN İHTİYAÇ — ÜST SINIR (kaba, ELENMEMİŞ)

`jq` ile başlık/açıklama jetonu taraması: başlıkta sağ/sol imâsı **1336** · açıklamada
"sağ ve sol / sağ-sol" **290** · tek/çift-kli **243**.
🔴 **Bunlar ÜST SINIRDIR, kalem sayısı DEĞİL** — desen `sağlam`, `solenoid`, `solo` gibi
kelimelere de vurur. Faz 2'nin ilk işi bu sayıyı **elenmiş** hâle getirmektir.

## 3. FAZLAR

### FAZ 0 — yazma yolu (K246, AÇIK, chip'te)
`tools/duzelt.py` `DEGISTIRILEBILIR` kümesine `boy_secenekleri` + **doğrulayıcı kablosu**
(`arama.boy_secenekleri_sebebi`, `uyum`/`altkategori` deseni). Kabul: küme+kablo birlikte · 6
negatif vaka reddedilir · pozitif vaka geçer · doğrulayıcıyı kaldıran mutant KIRMIZI · `--toplu`
yolunda da aynı red. **Bu inmeden diğer fazlar başlamaz.**

### FAZ 1 — canlı zincir teyidi (tek ürün, ölçüm)
Ölçek büyütmeden ÖNCE rayın bugün çalıştığı kanıtlanır. Ürün: `vw-t5-dugme-yuvasi-kor-kapagi`
(Tekli / Uzun +100 TL). Kabul: kanonik adreste seçici GÖRÜNÜR · seçim değişince gösterilen
fiyat **+100 TL** oynar · sepete giden istekte seçilen etiket TAŞINIR · `shop` ucu aynı farkı
**sunucuda** hesaplar (istemciye güvenilmez). Cache-bust YOK. Ölçülemeyen kol `OLCULEMEDI`.

### FAZ 2 — belirsiz ürün envanteri (elenmiş sayı)
Kaba 1336/290/243 üst sınırından **elenmiş** küme çıkarılır: yanlış pozitifler (sağlam/solenoid)
düşer, gerçek adaylar sınıflanır (sağ/sol · tek/çift · uzun/kısa · kovan tipi). Çıktı: id listesi
+ önerilen `boy_secenekleri` + `fark_tl` (fark yoksa 0). **Sahibi ürün düzlemi (MaCiT).**
Kabul: sayı TÜRETİLİR (jeton listesi tek kaynak) · örneklem elle doğrulanır · yanlış pozitif oranı
ölçülür ve YAZILIR.

### FAZ 3 — toplu yazım
`duzelt.py --toplu` ile parti parti. Kabul: her partide flock + tek yazım · `urunler-guard`
geri sarmıyor · D1 beş eksen yeşil · parite testleri taban ile kıyaslanır.

### FAZ 4 — YENİ partilerde tekrar doğmasın (kapı)
Ürün ekleme hattına kapı: başlık/açıklama varyant jetonu taşıyıp `boy_secenekleri` YOKSA
**RED** (ya da gerekçeli muafiyet). Sahibi ürün düzlemi + kapı kodu KraL.
Kabul: kapı + mutant + gerçek partide ölçülmüş red.

### FAZ 5 — Ege (HocA düzlemi)
Bot, seçenekli üründe **seçeneği sorabilmeli** ve seçilen etiketi siparişe taşımalı; aksi hâlde
müşteriyi arama sorunu WhatsApp kanalında sürer. HocA'ya bilgi + kabul: `talimat-kabul.mjs`
vakası.

## 4. SIRA VE BAĞIMLILIK

FAZ 0 → FAZ 1 → (FAZ 2 ∥ FAZ 4) → FAZ 3 → FAZ 5.
FAZ 1 kırmızı çıkarsa **FAZ 2/3 AÇILMAZ** — bozuk rayda ölçek büyütmek zarardır.

## 5. YASAKLAR

- `urunler.json`'a ham JSON yazımı YOK (guard HEAD'e geri sarar) — tek meşru yol `duzelt.py`.
- `fark_tl` **istemciden** hesaplanmaz; sunucu doğrulaması `shop/src/index.js:350-355` korunur.
- Fiyat farkı taşıyan alan doğrulayıcısız yazılamaz (FAZ 0'ın şartı).
- Ölçülmemiş varsayımla ölçek büyütmek YOK.
