# PAKET K171 — `duzelt.py` gizli kaynak kayıt düzlemini de temizlesin

**Mimar:** KraL · **Tarih:** 18 Ağu 2026 · **Kalem:** K171 (MaCiT → KraL devri)
**Sorun (MaCiT ölçtü):** ürün silindiğinde kanonik düzeltme aracı yalnız `urunler.json`'u
yazıyor; gizli kaynak kayıt düzlemi (`KAYNAKLAR` sabiti) **dokunulmadan kalıyor**. FAZ C'nin
ardından o düzlemde **15 artık kayıt** var. İşçi bağlamı kendi yazıcısını kurmayı YASAKLIYOR
ve araçta bayrak YOK → iş DURDU, doğru davrandı.

> 🔴 **GİZLİLİK (KraL kapısı, bu paketin en sert kuralı):** bu düzlem üyelik/tedarikçi
> bilgisi taşır. Ne log'a, ne manifest'e, ne commit mesajına, ne rapora **kayıt İÇERİĞİ
> yazılmaz** — yalnız `id` ve SAYI. `uyelik` alanının değeri hiçbir çıktıya BASILMAZ.
> Kabul satırında bunun ölçümü ZORUNLU.

---

## MİMAR HÜKMÜ

1. **Yeni ayrı betik YAZILMAZ.** Emsal aynı dosyada zaten var: `_id_yeniden_adlandir`
   (`_kaynak_rename_hazirla` ile) bu düzlemi **AYNI flock + AYNI atomik yazım turunda**
   ele alıyor. `--sil` ve `--toplu` kolları o desenin AYNISINI kullanacak. İkinci kilit,
   ikinci tur, ikinci yazıcı YASAK ([[kilitsiz-tek-yol-disiplini-bozar]]).
2. **Bayrak bu dilimde OPT-IN**, adı `--kaynak-temizle`. Varsayılanı açmak bu turda
   YAPILMAZ: MaCiT'in şu an KOŞAN partileri var, paylaşılan aracın davranışını uçuş
   sırasında değiştirmek ayrı bir risk. Varsayılana çevirme kararı **ölçümden sonra**
   (aşağıdaki `--kaynak-durum` sayısı elde olunca) ayrı dilimde verilir.
3. **Sessiz sıfır YASAK** (K163 sınıfı). Düzlem dosyası yoksa / ayrıştırılamıyorsa /
   okunamıyorsa sonuç `OLCULEMEDI`'dir; **hiçbir şey yazılmaz, çıkış kodu ≠ 0**. `0` yalnız
   ÖLÇÜLEN sıfır için kullanılır ([[kapi-varlik-olcer-yokluk-olcmez]]).
4. **Kısmi yazım YASAK.** İki düzlemden biri yazılıp diğeri yazılamazsa tur **tümüyle**
   düşer (atomik yazımlar aynı flock içinde, ikisi de başarılı olmadan commit edilmez).
   Yarım tur, artığı çoğaltmaktan daha kötüdür.
5. **İdempotent.** Silinecek id o düzlemde yoksa hata DEĞİL: `ZATEN_YOK=<n>` diye raporlanır.

## İCRA (işçi)

### Adım 1 — ölçüm kolu (ÖNCE bu, çünkü sayı olmadan hüküm verilemez)
`--kaynak-durum` (salt okuma, yazma YOK) ekle. Bastığı satır tam olarak:
```
KAYNAK_KAYIT=<n> URUN=<n> ARTIK=<n> ARTIK_ORNEK=<en fazla 5 id>
```
`ARTIK` = kaynak düzleminde olup `urunler.json`'da OLMAYAN id sayısı. **İçerik BASILMAZ**,
yalnız id. Dosya okunamazsa `OLCULEMEDI` + rc≠0.

### Adım 2 — `--kaynak-temizle` bayrağı
- `--sil` ve `--toplu` ile birlikte kullanılabilir; tek başına kullanılırsa hata.
- Etki: o turda silinen id kümesi, **aynı flock içinde** kaynak düzleminden de düşürülür;
  `_atomic_write` ikinci düzlem için de çağrılır (emsal: `_id_yeniden_adlandir`).
- Turun sonunda basılan satır: `KAYNAK_SILINEN=<n> ZATEN_YOK=<n> KAYNAK_KALAN=<n>`.
- Manifest'e yalnız id listesi + sayı yazılır; **kayıt gövdesi YAZILMAZ**.

### Adım 3 — mevcut 15 artığın temizliği (ayrı tur, bayrak indikten SONRA)
`--kaynak-durum` ile ÖNCE ölç → temizle → SONRA tekrar ölç. İki ölçüm de rapora BİREBİR
yapıştırılır. "15 temizlendi" iddiası **diskten** doğrulanmadan yazılmaz
([[silme-sayaci-diskten-dogrulanmali]]).

## KABUL (hepsi ZORUNLU, ham çıktılar rapora yapıştırılır)

```
python3 tools/duzelt-test.py            → rc=0   (yoksa: tools/testler.py rc=0)
python3 tools/duzelt.py --kaynak-durum  → rc=0, ARTIK=15 (temizlik ONCESI)
<temizlik turu>
python3 tools/duzelt.py --kaynak-durum  → rc=0, ARTIK=0  (temizlik SONRASI)
python3 tools/d1-kaynak-sync.py --durum → ONCESI/SONRASI iki ölçüm, ikisi de rapora
```

**GİZLİLİK ÖLÇÜMÜ (ZORUNLU, bu paket bununla kapanır):** temizlik turunun TÜM çıktısı
(stdout + stderr + yazılan manifest + commit mesajı) `tools/kisisel-veri-test.py` ile
taranır → **0 bulgu**. Ayrıca `uyelik` kelimesinin geçtiği hiçbir DEĞER çıktıda olmamalı.

**MUTASYON BATARYASI (4 mutant, hepsi KIRMIZI yakmalı):**
- M1: kaynak düzlemi yazımını kaldır → `KAYNAK_KALAN` düşmez, kabul kırmızı.
- M2: dosya okunamazken `ARTIK=0` döndür (sessiz sıfır) → `OLCULEMEDI` beklenirken 0 → kırmızı.
- M3: ikinci `_atomic_write`i flock DIŞINA taşı → eşzamanlılık vakası kırmızı yakmalı.
- M4: raporlayıcıya kayıt gövdesini bastır → gizlilik taraması bulgu vermeli.
Uygulanamayan mutant `UYGULANAMADI` yazılır, 0 SAYILMAZ.

## SINIR
`urunler.json`'un içeriğine bu paket DOKUNMAZ (ürün silme kararı bu paketin konusu değil;
o karar Okan'da ve zaten verilmiş olan turlar kapandı). Bu paket yalnız **artık kaydı**
temizler ve aracın eksik kolunu kapatır.
