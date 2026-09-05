# PAKET K172 — `mk1` MARKA-KÖR jetona taşınır (üç satır değil, TEK satır)

**Mimar:** KraL · **Tarih:** 18 Ağu 2026 · **Motor:** emekli motor `gpt-5.6-luna` (20 Ağu istisnası)

## MİMAR HÜKMÜ (bağlayıcı — işçi bu hükmü TARTIŞMAZ, UYGULAR)

`Mk1` bir **NESİL İŞARETİDİR**, rozet değil. Hiçbir üretici "Mk1" adıyla rozetlenmiş bir araç
SATMADI; her zaman `<Model> Mk1` biçiminde geçer (Escort Mk1, Golf Mk1, Mini Mk1, Amazon Mk1).
Bugün üç markada birden yargısız/BEKLER duruyor: `Ford|mk1` · `Volkswagen|mk1` · `Volvo|mk1`.

🔴 **Üç ayrı deny satırı YAZILMAYACAK.** Öyle yapmak dördüncü marka geldiğinde aynı işi
tekrar açtırır — bu depoda ölçülmüş bir yürüyen bant. Doğru yer **marka-KÖR** kümedir:

- `MODEL_OLMAYAN_JETON` = jeton **hiçbir marka için** model değil (bugünkü üyeler: `PSA`,
  `VAG` grup kısaltmaları · `Carling`/`AEM`/`Sprint Booster`/`Roland` parça üreticileri ·
  `Geo` kardeş marque). **`mk1` tam olarak bu sınıftır.**
- `MODEL_OLMAYAN_CIFT` = jeton BAŞKA markada gerçek model, bu markada değil (ör. `Ford|ST`).
  `mk1` buraya UYMAZ, çünkü hiçbir markada model değil.

Dosyadaki `GS` notu (satır 1339) niye marka-kör kümeye yazılmadığını anlatıyor: `GS` BMW'de
ve Lexus'ta GERÇEK rozet. `mk1`'de o durum YOK — karşı örnek arandı, bulunamadı.

## İCRA (tam olarak bunlar, fazlası değil)

1. `tools/arama.py` → `MODEL_OLMAYAN_JETON` sözlüğüne **TEK** giriş ekle:
   `"Mk1"` → gerekçe: nesil işareti, rozet değil; `<Model> Mk1` biçiminde geçer; hiçbir
   markada tekil rozet olarak satılmadı (K172, 18 Ağu, KraL hükmü).
   Yazımı mevcut satırların biçimine UYDUR (anahtarın büyük/küçük harf hâli için komşu
   girdilere bak; kanon fonksiyonu ne bekliyorsa ONU kullan — TAHMİN ETME, ÖLÇ).
2. `MODEL_OLMAYAN_SAYISI` 7 → 8; `MODEL_OLMAYAN_IMZA` **fonksiyonu ÇAĞIRARAK** yeniden hesapla.
   🔴 İmzayı kapının hata metninden KOPYALAMA.
3. `ROZET_CAPRAZ_IZINLI`den **üç BEKLER girdisini SİL**: `Ford|mk1`, `Volkswagen|mk1`,
   `Volvo|mk1` (artık marka-kör kural kapsıyor; allow'da kalmaları `capraz_bayat` üretir).
   `ROZET_CAPRAZ_IZINLI_SAYISI` 67 → 64; `ROZET_CAPRAZ_IZINLI_IMZA` yeniden HESAPLA.
4. Başka hiçbir tabloya, hiçbir satıra DOKUNMA.

## KABUL — her satır çalıştırılacak, çıktı ham olarak rapora

```
python3 tools/model-uyelik-kapisi.py     -> rc=0; YARGISIZ=0 CELISKI=0 BAYAT=0
python3 tools/model-baslik-kolu-test.py  -> rc=0
python3 tools/kategori-parite-test.py    -> rc=0
python3 tools/build.py                   -> rc=0
python3 tools/ci-kapsam-test.py          -> rc=0     (CI_KAPSAM_RC=0 satirini rapora yaz)
```
🔴 **K11 KAYBOLAN EKSENİ:** kapının K11 ölçümünde `kaybolan=0`. `mk1` kovalarının bugün
sayfası VAR MIYDI — varsa hangileri kapandı, ürün sayılarıyla TEK TEK yaz.
🔴 **BUILD SAYFA FARKI:** `build.py` ÖNCE ve SONRA ürettiği model sayfası sayısını yaz
(iki sayı yan yana). Beklenen: kapanan `mk1` sayfası kadar AZALMA, başka fark YOK.

**MUTASYON (3, hepsi KIRMIZI yakmalı):**
- M1 `Mk1` girdisini sil → kapı `YARGISIZ` verir.
- M2 `MODEL_OLMAYAN_IMZA`yı eski değerde bırak → imza ekseni kırmızı.
- M3 üç BEKLER girdisinden birini allow'a geri koy → `BAYAT` (envanterde var, çapraz değil).
🔴 Mutant birden çok ekseni birden tetikliyorsa YALIT: sayaç/imzayı mutasyona uydur ki
yalnız hedef kol yanabilsin. Yalıtılamazsa `YALITILAMADI` yaz, "geçti" YAZMA.

## SINIR VE ÇALIŞMA BİÇİMİ (kota disiplini)
- Raporu ÖNCE oluştur, **~30-40 turda** dilimleyip kapat. **Alt ajan / paralel görev AÇMA.**
  Tarayıcı KULLANMA. Toplu ürün işlemi YOK.
- `urunler.json` ve gizli kaynak düzlemi **DOKUNULMAZ**.
- 🔴 **DALDA COMMIT ET**, commit SHA'sını rapora yaz. Main'e push ETME, merge ETME.
- Geçici dosya bırakma.

## RAPOR
Dalın worktree'sinde, projenin kanonik mühendis raporu adıyla (gitignore'lu).
Son satır tek makine-okunur özet:
`K172 KAPI_RC=<n> BASLIK_RC=<n> BUILD_RC=<n> CI_KAPSAM_RC=<n> SAYFA_ONCE=<n> SAYFA_SONRA=<n> KAYBOLAN=<n> MUTANT=<n>/3`
