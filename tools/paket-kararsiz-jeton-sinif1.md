# PAKET — Kararsız jeton SINIF 1: donanım/nesil/seri kodlarının model düzlemine yargısı

Mimar: KraL · Düzlem: `tools/arama.py` tabloları + `index.html` kanonik eşleme + çip/sayfa
üreticisi. **`urunler.json` ve `.urun-kaynaklari.json` KAPSAM DIŞI** (MaCiT'in düzlemi; bu
pakette VERİYE yazılmaz, yalnız YÜKLEM/TABLO değişir).

Taban: `d91ea881` (model çipi kanonikleşti, çip 467 / model sayfası 534, K19 çapraz-marka
kapısı canlı). Bu paket K19'un **altında** çalışır: yeni çapraz çift doğarsa K19 kırmızı yakar.

---

## 1. SORUN (ölçülmüş)

Katalog geneli envanterde **387 ürün** "KARARSIZ" kovasında: jeton gerçek ama **model değil**
(donanım / nesil / seri kodu). Bunların **SINIF 1 = 152 ürün**, üç aile:

| aile | örnek jeton | ürün | not |
|---|---|---|---|
| BMW motosiklet serisi | `GS` | ~54 | 🔴 **Citroën GS ile AYNI AD, FARKLI ARAÇ** (D kovası) |
| VW Transporter kuşakları | `T1`…`T6` (`T4` 34, `T5` 33) | ~68 | kuşak kodu; `Transporter` sayfası CANLI ve 143 ürün |
| BMW motosiklet serileri | `R Serisi`, `K Serisi` | ~30 | 🔴 çıplak `R`/`K` **TEK HARF** |

**Kanonik ad kararı (BENİM HÜKMÜM, ölçüme dayalı):** kullanıcı **ÇIPLAK jetonla** arıyor —
ölçüldü: `?ara=T4` **74** sonuç vs `Transporter T4` **15**. Bu yüzden kanonik gösterim
`T4`'tür, `Transporter T4` değil.

🔴 **İSTİSNA — TEK HARF ÇIPLAK KULLANILMAZ.** `R` / `K` çıplak jeton olarak model adı
OLMAZ (bu depoda kısa jeton gürültüsü ölçülmüş bir sınıftır: `benzin`→`benz` çarpışması
550→1428 şişme yapmıştı). Bu ailenin kanonik adı `R Serisi` / `K Serisi` **tam yazımıdır**.

---

## 2. YAPILACAK

`GS` · `T1`–`T6` · `R Serisi` · `K Serisi` jetonları **MODEL sayılacak** ve model çipi +
model SEO sayfası düzlemine kanonik adlarıyla girecek. Uygulama **tek kaynaktan**: mevcut
kapalı/gerekçeli tablolar (`arama.py`) + `index.html` KANONİK MODEL EŞLEMESİ bloğu.
**İkinci tablo AÇMA, yeni liste UYDURMA** — `d91ea881`'in kurduğu düzen bozulmayacak.

### 🔴 ZORUNLU ÖN ÖLÇÜM — hüküm vermeden ÖNCE bas
1. `GS`: BMW tarafı ile **Citroën GS** tarafı ayrı ayrı kaç üründe? Her ikisi de sayfa eşiğini
   (`ESIK`) geçiyor mu? K19 bu çifti nasıl sınıflıyor (deny / allow / KIRMIZI)?
2. `T1`–`T6`: her kuşak ayrı ayrı kaç ürün? Hangileri eşiği geçiyor? VW dışında bir markada
   (ör. başka üreticinin `T5`'i) eşiği geçen var mı?
3. `R Serisi` / `K Serisi`: kaç ürün, eşik geçiyor mu, çıplak `R`/`K` yazımıyla kaç ürün
   yanlış eşleşiyor (gürültü ölçümü — bu sayı kanonik ad kararının kanıtıdır).
4. Bu üç aile **`Transporter` (143 ürün) ve `Boxer`/`GS` gibi mevcut kovalarla ÇAKIŞIYOR mu**:
   `T4` çipi doğarsa `Transporter` çipinden ürün DÜŞER Mİ? (Kuşak katlaması `d91ea881`'de
   zaten var — jeton düzeyinde değil KOVA düzeyinde elenmeli, aksi halde ana kova zayıflar.)

### HÜKÜM KURALI (çakışmada bana sorma, bunu uygula)
- Aynı fiziksel araç iki marque'ta farklı adla satılıyorsa → **ikizin adıyla sayfa AÇILMAZ**
  (K19 deny). `GS` bu sınıf DEĞİL: BMW GS ile Citroën GS **farklı araçlar, ikisi de gerçek
  rozet** → doğru hüküm **ALLOW** (`ROZET_CAPRAZ_IZINLI`), her ikisi kendi markasında sayfa
  açar. Ama bunu **ölçümle doğrula**: ikisi de eşiği geçmiyorsa allow girişi ÖLÜ olur, yazma.
- Bir kuşak kodu ana modelin ürünlerini ana kovadan DÜŞÜRÜYORSA → kuşak sayfası açılmaz,
  katlama ana modele yapılır (`Transporter` ana kova KORUNUR).

---

## 3. KABUL — sayıyla dön, "bakıldı iyi" kabul DEĞİL

1. **Kaybolan ürün = 0.** Marka sayfasında görünen toplam ürün sayısı önce/sonra AYNI olmalı;
   her elenen/doğan kovada `kaybolan 0` ayrı ayrı basılacak. Düşen ürün varsa **DUR**.
2. **`Transporter` kovası ölç:** 143 ürünün kaçı kaldı? Düştüyse kuşak katlaması jeton
   düzeyine kaymış demektir → KIRMIZI, düzelt.
3. **Çip/sayfa ekseni:** çip 467 → ? · model sayfası 534 → ? · **öksüz çip 0 kalmalı**
   (`d91ea881`'in kazanımı geri gitmeyecek).
4. **K19 yeşil** (`model-uyelik-kapisi.py`) — yeni çapraz çift yargısız kalmayacak.
5. **Arama şişmesi (yanlış-pozitif) ölç:** özellikle `R`/`K` ve `T1`–`T6` için önce/sonra
   toplam eşleşme. Şişme varsa **DUR**.
6. **Kabul testi + MUTASYON kanıtı zorunlu** (mevcut harness'lere vaka ekle, yeni harness açma):
   `tools/model-uyelik-kapisi.py` (+`--kendini-test`) ve `tools/cip-indeks-test.py`.
   Her yeni iddia için **önce KIRMIZI, sonra YEŞİL** göster; çapa TAM BİR KEZ eşleşmeli.
   🔴 En az bir **kontrol mutantı** koy (yeşil kalmalı) ve en az bir mutant `GS` çapraz-marka
   eksenini **tek başına** kırmızı yakabilmeli — yakamıyorsa o eksen ayrı iddia SAYILMAZ,
   gerekçesini yaz ([[beyan-edilmis-survivor]]).
7. `node tools/parite-test.js` + `node tools/parite-ege.js` → **açıklanamayan 0**.
   ⚠️ Parite kararı GÜNCEL main'deki ANA CHECKOUT'tan; dal worktree'sinden koşulan parite
   bayat taban yüzünden SAHTE SAPMA üretir.
8. `tools/ci-kapsam-test.py` rc=0 — eklediğin her iddia CI'da gerçekten koşacak.

## 4. TESLİM
- Dalını `git push -u origin <dal>` ile it, `RAPOR-MIMARA.md`'yi **dalda** bırak (izlenen
  yere KOYMA, başka ad YASAK).
- Raporda: ön ölçümün 4 sorusunun cevabı · uygulanan hüküm + gerekçe · yukarıdaki 8 kabul
  ekseninin sayısı · **ÖLÇÜLEMEDİ kalan her şey dürüstçe** (yeşil sayma).
- Merge'ü SEN yapma — merge kapısı bende.
