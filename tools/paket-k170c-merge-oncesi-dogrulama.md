# PAKET K170-C — merge ÖNCESİ bağımsız kapı koşumu (yalnız ÖLÇÜM, onarım YOK)

**Mimar:** KraL · **Tarih:** 18 Ağu 2026
**Ağaç:** `/Users/okan/dev/pruvo/.claude/worktrees/k170-capraz-yargi` · **Commit:** `e89a4851`

Mimar git ekseninde ölçtü: gerçek merge-base `f5399380`, kapsam **tek dosya**
`tools/arama.py` (+61/-4), çakışma **YOK** (`merge-tree` düz ağaç OID), ff mümkün değil
(merge commit'i gerekecek — normal). Kalan tek soru: **kapılar dalın SON commit'inde
(`e89a4851`) ne diyor.** Bu tur yalnız bunu ölçer.

🔴 **HİÇBİR ŞEYİ ONARMA.** Bu tur tanı turudur: kırmızı görürsen kırmızıyı RAPORLA, düzeltme.
Dosya değiştirme, commit atma, merge etme. Ağaç koşum sonunda `git status --short` ile TEMİZ
kalmalı (kanıtla).

## KOŞULACAKLAR — hepsi DALIN worktree'sinde, çıkış kodu (rc) ile birlikte

```
python3 tools/model-uyelik-kapisi.py
python3 tools/ci-kapsam-test.py
python3 tools/kapi-envanteri.py
python3 tools/kategori-parite-test.py
python3 tools/kategori-kapisi.py
python3 tools/is-akisi-kapisi.py
python3 tools/build.py
```

🔴 `build.py` bu turun EN ÖNEMLİ adımı: K170 yedi kovayı deny'e aldı, yani **build artık 7
sayfa DAHA AZ üretmeli**. Ölçülecek:
- `build.py` rc'si (K164'te tam bu araç exit 1 verip yayını kapatmıştı),
- ürettiği **marka-model sayfa sayısı** — K170 ÖNCESİ (bu worktree'de `git stash` DEĞİL:
  `main` ucunda ayrı ölçüm) ile SONRASI **iki sayı yan yana**,
- `/marka/piaggio/px/` · `/marka/peugeot/c1/` · `/marka/alfa-romeo/916/` dizinlerinin
  üretilen çıktıda **artık DOĞMADIĞI**,
- `/marka/vespa/px/` · `/marka/citroen/c1/` · `/marka/ducati/916/` sayfalarının **DOĞDUĞU**.
- 🔴 `build.py` ağacı kirletiyorsa (üretilen dosyalar) bunu RAPORLA ve koşum sonunda
  `git status --short` çıktısını BİREBİR yapıştır — temizleme kararı mimarındır.

## RAPOR
Aynı dalda, projenin kanonik mühendis raporu adıyla; her komutun **rc'si + ham çıktısının
son 15 satırı**. Kırmızı olan varsa "K170 ÖNCESİ de kırmızıydı" DEME — `main` ucunda AYNI
komutu koşup iki rc'yi yan yana bas ([[anahat-referans-tautolojisi]]). Ölçemediğin ekseni
`OLCULEMEDI` + sebep yaz; **hiçbir satırı ham çıktı olmadan tabloya koyma.**
İş bitince geçici dosya bırakma.
