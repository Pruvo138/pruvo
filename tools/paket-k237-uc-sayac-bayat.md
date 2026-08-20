# PAKET — K237: uç 29 ürünü döndürmüyor, `senkron.urun_sayisi` bayat (chip: `KraL-K237`)

> Mimar (KraL) hükmü. **Müşteri etkisi VAR** — sessiz satış kaybı sınıfı (K85).
> Kabul ölçütü burada çivilidir, tur içinde BÜYÜTÜLMEZ.

## 1. ÖLÇÜLEN OLGULAR (varsayım değil — kim ölçtü, ne çıktı)

| kim | ölçüm | sonuç |
|---|---|---|
| KraL (mimar) | `python3 tools/d1-sync.py --durum` | `D1 urun sayisi: 29602` · alt satır **`urun_sayisi = 29573`** |
| KraL | aynı koşum, beş eksen | SAYI ✅ · SEQ ✅ · ŞEMA ✅ · TÜRETİLMİŞ (5 kolon) ✅ · İÇERİK (29602 hash, uyuşmaz 0, eksik 0, fazla 0) ✅ |
| P2/P3 chip | `node tools/parite-test.js` | `YERELDE VAR / D1'DE YOK: 29 urun · yerel=29602 canli=29573` + **`YAYINDA AMA GORUNMUYOR: 29 id, D1'de yayinda=1 olduğu HALDE /katalog?ids= dondurmedi`** |
| aracın kendi hükmü | — | *"yayin gecikmesiyle ACIKLANAMAZ — uc/indeks gerilemesi"* |
| MaCiT (veri sahibi) | kendi partisi (`d55ed35d`, Seat d2-2, +29) | ürün verisi DOĞRU; devralmadı, **mekanizma KraL düzlemi** (kod kilidi) |

🔴 **İki ayrı belirti var, TEK sebep VARSAYILMAYACAK:**
- **(a)** `senkron.urun_sayisi` = 29573 (bayat sayaç).
- **(b)** `/katalog?ids=` 29 id'i DÖNDÜRMÜYOR (müşteri etkisi burada).

**(a) ⇒ (b) bağı HENÜZ KANITLANMADI.** İlk iş bu bağı kurmak ya da çürütmek.

## 2. HİPOTEZ (kanıt DEĞİL — çürütülecek)

`tools/d1-sync.py:4576` `INSERT INTO senkron (anahtar,deger) VALUES ('urun_sayisi', …)`
yalnız YAZMA kolunda çalışıyor; hash'ler eşit olunca senkron `degisiklik yok — D1'e yazilmadi ✅`
koluna düşüyor ve sayaç güncellenmiyor. Uç okuma yolu bu sayacı (veya ondan türeyen bir
yayın/sürüm işaretini) sınır olarak kullanıyorsa, 29 satır D1'de dururken uçta görünmez kalır.

**Çürütme ölçütü:** uç okuma yolunun SQL'i `senkron.urun_sayisi`'ye (ya da ondan türeyen bir
değere) hiç bakmıyorsa hipotez DÜŞER ve sebep başka yerdedir — o hâlde (b) bağımsız ölçülür.
Sınıf uyarısı: [[aracin-teshis-cumlesi-olcum-degil]] — kolonun müşteri etkisi onu OKUYAN SQL'in
TAMAMINDAN türetilir; `OR` yan kolu varsa kolon bayatken bile yüzey "çalışıyor" görünebilir.

## 3. SIRA (bozma)

1. **(b)'nin sebebini ÖLÇ** — uç `/katalog` okuma yolunun tamamını çıkar: hangi kolon/işaret
   satırı görünür kılıyor, 29 id neden eleniyor. Kolon adı değil **SQL'in tamamı**.
2. **(a) ile bağını kur ya da ÇÜRÜT.**
3. Ancak ondan sonra onar. Önce onarıp sonra açıklama yazma.

## 4. KABUL — dördü de SAYIYLA

| # | kapatan ölçüm |
|---|---|
| ① | 29 id `/katalog?ids=` ile **DÖNER** (id listesiyle, tek tek) |
| ② | `--durum`'un iki satırı **eşitlenir** ya da eşitsizlik **fail-closed RED** verir (sessiz geçmez) |
| ③ | sayaç **TÜRETİLİR** ya da senkron sonunda **zorunlu** tazelenir — "yazma olduysa" koluna bağlı KALMAZ |
| ④ | **mutant:** sayaç elle bayatlatılır, kapı YAKALAR; mutantın **hedef kolu öldürdüğü ayrıca** kanıtlanır (K182) |

Ek: `tools/d1-sync-durum-test.py` zaten `urun_sayisi`'yi fikstürlüyor — yeni vaka oraya eklenir,
ikinci bir test gövdesi DOĞMAZ.

## 5. YASAKLAR

- D1'e **elle UPDATE/INSERT YOK** (sayacı elle 29602 yazmak onarım değil, ölçümü siler).
- `urunler.json` / `.urun-kaynaklari.json` ELLENMEZ — veri MaCiT'in, DOĞRU olduğu ölçüldü.
- `--no-verify` YOK · kapı bypass YOK · `wrangler deploy` **OKAN KAPISI**.
- Ana checkout'ta commit YOK; iş kendi worktree'nde. Merge+push **MİMARDA**.

## 6. Kapanış

Sayılı kapanış `memory/mimar-posta-kutusu.md`'nin EN ÜSTÜNE; MaCiT'e haber (bağımsız
`/katalog?ids=` doğrulamasını o yapacak). Son satır birebir `✅ İŞ BİTTİ — ARŞİVLENEBİLİRİM`.
Ölçemediğin kalırsa `OLCULEMEDI` + sebep + "neyi ölçmek kapatır" — uydurma.
