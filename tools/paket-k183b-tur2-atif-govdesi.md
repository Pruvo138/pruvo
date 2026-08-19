# PAKET K183b — TUR 2: atıf mekanizması TEK GÖVDE olacak

> MİMAR HÜKMÜ (18 Ağu 2026, KraL). TUR 1 `ade8f7ae` ile commit edildi ve KABUL EDİLDİ;
> bu tur onun ÜSTÜNE gelir. Ev: `/Users/okan/dev/pruvo/.claude/worktrees/k183-dispatch-grubu`.
> Dokunulacak TEK dosya: `tools/is-akisi-kapisi.py`. Commit ATMA, `git` ÇALIŞTIRMA.

## NEDEN (mimar diff'i okudu, ölçtü)

TUR 1'in META-VAKA'sı atıf mantığını **çağırmıyor, KOPYALIYOR**:

```python
for kol in _meta_hedef:
    if not any(h.startswith(kol + " ") for h in meta_bulgu):   # <-- İKİNCİ KOPYA
        _meta_uretti_hedef_hatasi = True
```

Gerçek atıf döngüsü (mutant döngüsünün içindeki `G-HEDEF KOL OLMEDI` bloğu) SİLİNSE
bile bu meta-vaka YEŞİL kalır — çünkü kendi kopyasını ölçüyor. Yani "K182 atıf
mekanizması canlı" iddiası **ölçülmüyor**; ölçülen şey meta-vakanın kendi kopyası.
Bu, defterde kayıtlı sınıftır: kopyalayan test kaynağı ölçmez.

TUR 1'in üç çürütmesinden hiçbiri atıf gövdesini öldürmedi; bu yüzden kusur
çürütmelerden geçti.

## YAPILACAK

### 1) Atıf doğrulaması TEK GÖVDEYE inecek

Modül düzeyinde bir yardımcı:

```python
def _hedef_kol_dogrula(ad, bulgu, hedef_kollar):
    """Beyan edilen her hedef kol icin BULGU'da o kolun satiri var mi?

    Doner: hata metinleri listesi (bos liste = tum hedef kollar yandi).
    TEK GOVDE: hem mutant dongusu hem META-VAKA BURAYI cagirir; ikinci
    kopya YASAK (kopyalayan test kaynagi olcmez).
    """
```

- Mutant döngüsündeki `G-HEDEF KOL OLMEDI` üreten satırlar SİLİNİR, yerine
  `hatalar.extend(_hedef_kol_dogrula(ad, bulgu, hedef_kollar))` gelir.
- Hata metni AYNEN korunur (`G-HEDEF KOL OLMEDI: ...`).

### 2) META-VAKA aynı gövdeyi çağıracak — İKİ YÖNLÜ

M2 mutasyonu uygulanır (`dispatch` kolu `'dispatch'` olur), sonra:

- **YANLIŞ beyan yönü:** `_hedef_kol_dogrula("META", meta_bulgu, ("G1",))`
  BOŞ DÖNERSE → `G-ATIF MEKANIZMASI OLU` hatası (mekanizma ölü).
- **DOĞRU beyan yönü:** `_hedef_kol_dogrula("META", meta_bulgu, ("G10",))`
  BOŞ DÖNMEZSE → `G-ATIF YANLIS POZITIF` hatası (doğru beyan yanlış alarm veriyor).

İki yön de AYRI `iddia` sayılır. Tek yön yeterli DEĞİLDİR: yalnız yanlış-beyan
yönü ölçülürse `return ["hata"]` diye sabit dönen bir gövde de yeşil verirdi.

## KABUL (işçi KOŞAR, ham çıktıyı AYNEN yapıştırır)

1. `python3 .../tools/is-akisi-kapisi.py --kendini-test` → **rc=0**
2. `python3 .../tools/is-akisi-kapisi.py` (gerçek ağaç) → rc RAPORLA
3. **ÇÜRÜTME A (bu turun ASIL kanıtı):** `_hedef_kol_dogrula` gövdesini
   `return []` yap → `--kendini-test` **KIRMIZI** olmalı **ve** çıktıda
   `G-ATIF MEKANIZMASI OLU` GEÇMELİ. (TUR 1'de bu çürütme YEŞİL verirdi —
   farkı raporda YAZ.)
4. **ÇÜRÜTME B:** `_hedef_kol_dogrula` gövdesini
   `return ["G-HEDEF KOL OLMEDI: sabit"]` yap (her zaman hata döner) →
   `--kendini-test` **KIRMIZI** olmalı ve çıktıda `G-ATIF YANLIS POZITIF` GEÇMELİ.
5. Her çürütmeden sonra dosya GERİ ALINIR; son koşum yine `rc=0` olmalı.

Ölçemediğin her şey için ayrı `OLCULEMEDI:` satırı yaz. Yeşil tablo uydurma:
koşmadığın komutun çıktısını yazarsan iş REDDEDİLİR.

Rapor: mühendis raporuna (dalın kökünde, kanonik ad) ham çıktılarla yaz.
