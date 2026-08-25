#!/usr/bin/env python3
"""Sinir kutusu (bbox) BIRIM/OLCU SAGLIK hukmu — TEK KAYNAK (K287).

Bu modul, bir olcum hattinin urettigi `[d0, d1, d2]` (mm, buyukten kucuge) uclusunun
urun aciklamasina YAZILABILIR olup olmadigina karar verir. Tek karar noktasi
`hukum()`; cagiranlar kendi esiklerini TASIMAZ.

═══════════════════════════════════════════════════════════════════════════════
NEDEN TEK DOSYA (sinif, tekil vaka DEGIL)
═══════════════════════════════════════════════════════════════════════════════
25 Agu 2026'ya kadar ayni iki esik ALTI ayri uretim yerinde ELLE kopyalanmisti:
printables-api.stl_bbox / bbox_3mf / obj_bbox · thing-hazirla.bbox ·
cults3d-api._stl_bbox · myminifactory-api.parse_dimensions. Kopyalar ZATEN
ayrismisti — olculdu: `cults3d-api.py` hala "d[0] < 2 ise metre sanip x1000 carp"
tahminini tasiyordu; oysa kardes dosyalarin yorumu bu tahminin FIZIK-DISI bbox
urettigini (0.65 inc parca -> 650 mm) yazip KALDIRMISTI ve "printables-api ile
AYNI karar" diye iddia ediyordu. Iddia metinde dogru, KODDA yanlisti
([[tekil-yama-sinifi-kapatmaz]] · [[ayni-alan-iki-hukum-biri-sessiz]]).

═══════════════════════════════════════════════════════════════════════════════
KUCUK UC — BELIRSIZ BIRIM (eski, degismedi)
═══════════════════════════════════════════════════════════════════════════════
STL/OBJ birim beyani TASIMAZ. En buyuk boyut < 2 birim ise mm/metre/inc ayirt
edilemez -> uydurma yerine None. Esik EN BUYUK boyuttadir, boylece ince levha
(100 x 100 x 0.5) tetiklemez. 3MF ve MMF `dimensions` string'i BIRIMI BEYAN EDER;
onlar `birim_beyanli=True` ile cagirir ve bu koldan MUAFTIR (yoksa mesru 1.5 mm'lik
bir conta reddedilirdi).

═══════════════════════════════════════════════════════════════════════════════
BUYUK UC — ORTA BOYUT TAVANI (K287, 25 Agu 2026'da EKLENDI)
═══════════════════════════════════════════════════════════════════════════════
OLCULEN ARIZA: buyuk ucta tek tavan `d0 > 100000` (100 m) idi. pid 4675433'un
bbox'i **1659 x 1659 x 100 mm** cikti, 100 m'nin ALTINDA oldugu icin kapidan GECTI;
gercek fotograf ~13 cm'lik bir parca gosteriyordu. Fail-closed ELLE uygulandi.

🔴 TERS YON DE GERCEK — "buyukse reddet" MESRU parcayi oldurur: ayni kampanyada
pid 7173324'un bbox'i **1860 x 145 x 104 mm** cikti ve DOGRUYDU (tam boy Audi A3
marspiyeli, gercek fotografla dogrulandi, mm satiri korundu).

─── AYIRT EDICI ARANDI, OLCULEREK BULUNDU (canli katalog, 23.911 olcu satiri) ───

  ✗ KARE/SIMETRI SUPHESI DEGIL. `d0/d1 < 1.02` VE `d0 >= 250 mm` olan 28 kayit var
    ve icinde MESRU parcalar bol: 19 inc jant 483 x 483 x 277 · Sprinter cati fan
    adaptoru 452 x 452 x 16 · VQ35DE emme manifoldu 465 x 464 x 141 · 10 inc
    subwoofer adaptor halkasi 268 x 268 x 22 · cift teker ara pulu 251 x 251 x 4.
    Simetri kanit DEGILDIR; simetriyi olcut yapan kural bunlarin hepsini oldururdu.

  ✗ HACIM DEGIL. 1659 x 1659 x 100 = 0,28 m^3 iken mesru "Insan Tasiyan Katamaran"
    1820 x 250 x 196 = 0,09 m^3 ve mesru Suzuki Samurai taban taramasi
    2445 x 1521 x 744 = 2,77 m^3. Hacim siralamasi iki sinifi AYIRMIYOR.

  ✓ MUTLAK mm — ve EN BUYUK boyutta DEGIL, IKINCI boyutta (`d1`). Sebep: mesru
    "uzun-ince" parcalar (marspiyel, tavan listesi, spoyler, kapi esigi kaplamasi,
    yag cubugu) TEK eksende uzar. Olculdu:
      * 1000 mm tavani `d0`'a konursa 42 kayit reddedilir ve bunlarin 8'i MESRU
        uzun-ince parcadir — **birincisi tam da pid 7173324 marspiyelidir**.
      * Ayni tavan `d1`'e konursa 21 kayit reddedilir ve uzun-ince kanadin
        (d0 > 600 mm) HICBIRI etkilenmez.
    Yani eksen secimi bir tercih degil, ikinci-yon vakasinin ZORUNLU sonucudur.

─── TAVAN NEDEN 1000 mm (uydurma degil, turetildi) ───
  * Canli katalogda `d1`'in p99.9 degeri **930 mm** (23.911 olcu satiri uzerinden);
    tavan bir ust tam metreye yuvarlandi -> 1000 mm.
  * MALIYET: 21 / 23.911 = %0,088 kayit reddedilir (mm satiri YAZILMAZ, urun
    silinmez — fail-closed davranis eskisiyle ayni).
  * PAYI: mesru uzun-ince kanadin (d0 > 600 mm) en buyuk `d1` degeri **284,1 mm**;
    tavan bunun **3,52 katidir**. Yani mesru sinifa 3,5x pay birakilmistir.
  * FIZIK: iki eksende birden 1 m'yi asan bir parca PRUVO'nun uretebilecegi bir
    parca degildir; sayi DOGRU olsa bile o kayit satilabilir bir urun tarif etmez.

⚠️ BU TAVAN "COK BUYUK PARCA" KAPISI DEGIL, BIRIM SAGLIGI KAPISIDIR. Tavanin
ALTINDA kalan supheli kayitlar (or. 600 x 580 x 80 mm cikan bir menfez klipsi)
bu koldan GECER — onlari ayirt eden sey geometri degil PARCA ADI/anlamidir ve
o ayri bir eksendir. Bu dosyaya "ad/anlam" olcutu EKLEME; ayri kalem ac.
"""

# Belirsiz-birim alt siniri: en buyuk boyut bunun altindaysa mm/metre/inc ayirt
# edilemez (yalniz birim beyani OLMAYAN kaynaklar icin — STL, OBJ).
BELIRSIZ_BIRIM_ALTI_MM = 2.0

# Orta (ikinci buyuk) boyut tavani. Turetme + maliyet + payi: ustteki blok.
ORTA_TAVAN_MM = 1000.0

# En buyuk boyut mutlak tavani (eski deger, korundu): 100 m ustu = saglıksiz.
EN_BUYUK_TAVAN_MM = 100000.0

# Mesru uzun-ince kanadin OLCULEN en buyuk `d1` degeri (canli katalog, 25 Agu 2026).
# Kabul testi ORTA_TAVAN_MM'in bunun en az 3 kati oldugunu iddia eder — tavan
# sessizce daraltilirsa mesru sinifa birakilan pay kaybolur ve test KIRMIZI yanar.
OLCULEN_UZUN_INCE_D1_TAVANI = 284.1


def hukum(d, birim_beyanli=False):
    """Bbox saglik hukmu. SAGLIKLI ise None, degilse SEBEP dizgesi doner.

    d              : 3 elemanli sayi dizisi (mm). Sirali gelmesi SART DEGIL —
                     savunma amacli burada da buyukten kucuge siralanir.
    birim_beyanli  : kaynak birimini BEYAN ediyorsa True (3MF `unit`, MMF
                     `dimensions` string'i). O zaman belirsiz-birim kolu ATLANIR.

    Sozlesme: hicbir durumda firlatmaz; anlasilmayan girdi de bir SEBEP dondurur
    (fail-closed — "olcemedim" YESIL DEGILDIR)."""
    if d is None:
        return "olculemedi"
    try:
        dd = sorted([float(x) for x in d], reverse=True)
    except (TypeError, ValueError):
        return "sayisal-degil"
    if len(dd) != 3:
        return "uc-boyut-degil"
    if dd[0] != dd[0] or dd[0] in (float("inf"), float("-inf")):   # NaN / sonsuz
        return "sayisal-degil"
    if dd[0] <= 0:
        return "sifir-ya-da-negatif"
    if dd[0] > EN_BUYUK_TAVAN_MM:
        return "en-buyuk-tavan-asildi"
    if not birim_beyanli and dd[0] < BELIRSIZ_BIRIM_ALTI_MM:
        return "belirsiz-birim"
    if dd[1] > ORTA_TAVAN_MM:
        return "orta-boyut-tavani-asildi"
    return None


def saglikli(d, birim_beyanli=False):
    """hukum() == None kisayolu."""
    return hukum(d, birim_beyanli) is None


def suz(d, birim_beyanli=False):
    """Cagiranlarin ortak kalibi: saglikli ise SIRALI listeyi, degilse None doner."""
    if hukum(d, birim_beyanli) is not None:
        return None
    return sorted([float(x) for x in d], reverse=True)
