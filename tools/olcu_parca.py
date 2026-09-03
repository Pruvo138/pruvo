# -*- coding: utf-8 -*-
"""olcu_parca.py — OLCU EN BUYUK PARCA UZERINDEN (dosya bbox'i DEGIL). TEK KAYNAK.

🔴 HUKUM (BaBa 2026-09-03 17:1x ② · cip KraL-HasatEkleRedKapisi-3Eyl):
  Bir model dosyasi tabla dizilmis birden cok govde tasiyabilir. Urun aciklamasinda
  yazilan olcu, DOSYANIN sinir kutusu degil EN BUYUK PARCANIN sinir kutusudur.

NEDEN — CANLI ONBELLEKTE OLCULDU (.thing-cache, 198 .stl ornegi, 2026-09-03):
  * cok-parcali dosya 40/198 = **%20,2**
  * cok-parcali dosyalarda dosya-bbox'inin EN BUYUK BOYUTU gercek parcaninkinden
    ORTALAMA **%21,8**, en kotu vakada **%70,6** BUYUK cikiyor
    (th1692616: dosya [106,4 x 62,9 x 6,0] mm -> parca [31,3 x 18,5 x 6,0] mm;
     th12625: 75,6 -> 24,5 mm; th942003: 75,2 -> 25,9 mm)
  * gorulen en yuksek parca sayisi **1199** (pr963888 — tabla dizilmis coklu parca)
  Sapma urun aciklamasindaki "mm" satirina, oradan fiyat + filament tavsiyesine
  SESSIZCE akiyordu: tabla bbox'i "urunun olcusu" diye yaziliyordu.

🔴 NEDEN TEK DOSYA (K287 emsali, AYNEN): saglik hukmu bir zamanlar alti dosyaya
  kopyalanmisti; kopyalar "AYNI karar" diye IDDIA ederken sessizce AYRISMISTI ve
  fizik-disi bbox uretmisti (bkz `olcu_saglik.py` ve `cults3d-api.py:425` notu).
  Parca ayrimi ayni tuzagi tekrar etmesin diye BASTAN tek dosyada tanimlidir:
  ikinci `_parca_kutulari` gövdesi YASAK — nobetcisi
  `tools/olcu-en-buyuk-parca-test.py` (TEK KAYNAK kolu, okuyucu envanteriyle).

OKUYUCULAR (envanter — yeni okuyucu eklenirse bu liste ve nobetci GUNCELLENIR):
  tools/printables-api.py  (stl_bbox · obj_bbox · bbox_3mf)
  tools/cults3d-api.py     (_stl_bbox)
  tools/thing-hazirla.py   (bbox)
  tools/thingiverse-fetch.py (bbox)
  tools/printables-fetch.py  (bbox)
  tools/stl-measure.py     (main — teshis ciktisi)

SOZLESME: girdi `xs/ys/zs` VERTEX-SIRALI duz listelerdir — ucgen t'nin koseleri
3t, 3t+1, 3t+2 indekslerindedir (STL/OBJ ayristiricilarinin hepsi bu siradadir,
alti okuyucuda da ayri ayri DOGRULANDI). Sira bozulursa komsuluk yanlis kurulur;
bu yuzden cagiran, unique-vertex sikistirmasi YAPMADAN ham listeyi verir.
"""
import sys

# Vertex kuantizasyonu: STL vertex'leri float'tir, ayni kose iki ucgende bit-birebir
# ayni gelmeyebilir. Kuantizasyon YALNIZ komsuluk karari icin kullanilir — bbox HAM
# koordinattan hesaplanir, yani olcuye yuvarlama HATASI TASIMAZ.
HASSASIYET = 1e-5

# Ucgen tavani: 80 MB dosya tavani (hasat_stl.BOYUT_TAVAN) binary STL'de ~1,68 M ucgene
# denk -> normal isleyiste tavan ASILMAZ. Asilirsa parca ayrimi YAPILMAZ ve dosya
# bbox'ina dusulur; bu SESSIZ olmaz, stderr'e ILAN yazilir (o kayitta olcu yeniden
# tabla-bbox'i olur ve bunun bilinmesi gerekir).
UCGEN_TAVANI = 2_000_000


def parca_kutulari(xs, ys, zs):
    """Bagli bilesenlerin (PARCA) kutulari: [(dx, dy, dz, ucgen_sayisi)].

    Paylasilan vertex'e gore union-find. Ucgen tavani asilirsa None (cagiran dosya
    bbox'ina duser + ILAN eder); ucgen yoksa bos liste."""
    n_ucgen = len(xs) // 3
    if n_ucgen == 0:
        return []
    if n_ucgen > UCGEN_TAVANI:
        return None
    ebeveyn = []
    anahtar_kok = {}
    h = HASSASIYET

    def bul(x):
        kok = x
        while ebeveyn[kok] != kok:
            kok = ebeveyn[kok]
        while ebeveyn[x] != kok:                     # yol sikistirma
            ebeveyn[x], x = kok, ebeveyn[x]
        return kok

    def dugum(i):
        a = (round(xs[i] / h), round(ys[i] / h), round(zs[i] / h))
        d = anahtar_kok.get(a)
        if d is None:
            d = len(ebeveyn)
            ebeveyn.append(d)
            anahtar_kok[a] = d
        return d

    ucgen_dugum = []
    for t in range(n_ucgen):
        i = 3 * t
        a, b, c = dugum(i), dugum(i + 1), dugum(i + 2)
        ka = bul(a)
        kb = bul(b)
        if kb != ka:
            ebeveyn[kb] = ka
        kc = bul(c)
        ka = bul(a)
        if kc != ka:
            ebeveyn[kc] = ka
        ucgen_dugum.append(a)

    kutular = {}
    for t in range(n_ucgen):
        kok = bul(ucgen_dugum[t])
        i = 3 * t
        k = kutular.get(kok)
        if k is None:
            k = [xs[i], xs[i], ys[i], ys[i], zs[i], zs[i], 0]
            kutular[kok] = k
        for j in (i, i + 1, i + 2):
            x, y, z = xs[j], ys[j], zs[j]
            if x < k[0]: k[0] = x
            if x > k[1]: k[1] = x
            if y < k[2]: k[2] = y
            if y > k[3]: k[3] = y
            if z < k[4]: k[4] = z
            if z > k[5]: k[5] = z
        k[6] += 1
    return [(k[1] - k[0], k[3] - k[2], k[5] - k[4], k[6]) for k in kutular.values()]


def en_buyuk_parca_boyu(xs, ys, zs, kaynak=""):
    """En buyuk PARCA'nin (dx, dy, dz) boyu; parca ayrimi yapilamazsa DOSYA bbox'i.

    "En buyuk" = bbox HACMI; esitlikte ucgen sayisi (deterministik siralama).
    Tek parcali modelde sonuc dosya bbox'i ile BIREBIR AYNIDIR — modellerin ~%80'i
    tek parca oldugu icin bu kol yanlis-pozitif URETMEZ (nobetcisi: kabul vakasi P1)."""
    dosya = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))
    kutular = parca_kutulari(xs, ys, zs)
    if kutular is None:
        sys.stderr.write(
            "PARCA AYRIMI YAPILMADI (ucgen>%d): olcu DOSYA bbox'indan verildi%s\n"
            % (UCGEN_TAVANI, (" | " + str(kaynak)) if kaynak else ""))
        return dosya
    if not kutular:
        return dosya
    en = max(kutular, key=lambda k: (k[0] * k[1] * k[2], k[3]))
    return (en[0], en[1], en[2])


def sirali_parca_boyu(xs, ys, zs, kaynak=""):
    """en_buyuk_parca_boyu -> buyukten kucuge sirali liste (cagiranlarin cogu boyle ister)."""
    return sorted(en_buyuk_parca_boyu(xs, ys, zs, kaynak=kaynak), reverse=True)
