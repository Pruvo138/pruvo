#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K287 — bbox BIRIM/OLCU SAGLIK kabul testi + IKI YONLU mutasyon bataryasi.

    python3 tools/olcu-saglik-test.py              # kabul (rc 0 = hepsi YESIL)
    python3 tools/olcu-saglik-test.py --mutasyon   # mutasyon bataryasi
    python3 tools/olcu-saglik-test.py --iddia-dokumu   # makine okunur satirlar

═══════════════════════════════════════════════════════════════════════════════
NE OLCER
═══════════════════════════════════════════════════════════════════════════════
Hukum tek kaynakta: `tools/olcu_saglik.py`. Bu test onu IKI GERCEK VAKAYLA civiler:

  🔴 pid 4675433 — bbox `1659 x 1659 x 100 mm`. FIZIKSEL IMKANSIZ (gercek fotograf
     ~13 cm gosterdi), eski kapidan GECTI (tek tavan 100 m idi). KIRMIZI YANMALI.
  🟢 pid 7173324 — bbox `1860 x 145 x 104 mm`. MESRU (tam boy Audi A3 marspiyeli,
     gercek fotografla dogrulandi, mm satiri korundu). YESIL GECMELI.

Ikinci vaka bu isin YARISI: "buyukse reddet" kurali onu OLDURUR. Bu yuzden her
mutant ayrica HANGI IDDIAYI oldurdugunu beyan eder ve batarya beyanla OLCUMU
karsilastirir — mutantin kirmizi gelmesi TEK BASINA kanit degildir
([[ad-iki-rolde-mutanti-golgeler]] · [[capa-cokmesi-arkasindaki-capalari-gizler]]).

═══════════════════════════════════════════════════════════════════════════════
TAUTOLOJI KARSITI: FIKSTUR GERCEK BAYTTIR
═══════════════════════════════════════════════════════════════════════════════
A4 kolu `olcu_saglik.hukum()`u DOGRUDAN cagirmaz; iki vakayi GERCEK dosya
baytlarina (binary STL · OBJ · 3MF) cevirir ve URETIM fonksiyonlarini
(`printables-api.stl_bbox/obj_bbox/bbox_3mf`, `cults3d-api._stl_bbox`,
`thing-hazirla.bbox`, `myminifactory-api.parse_dimensions`) kosturur. Fikstur
hukmu DOGRUDAN dondurseydi butun negatif blok tautolojik yesil yanardi
([[sahte-bagimliligin-sekli-negatif-blogu-kutsar]]).

⚠️ `thing-hazirla.py` IMPORT ANINDA sabit koke bakar -> CI fresh-checkout'ta
import PATLAR (ci-kapsam muafiyet gerekcesi, R_YOL sinifi). Bu yuzden onun
`bbox()` govdesi IMPORT EDILMEZ, KAYNAKTAN BIREBIR CIKARILIP izole namespace'te
derlenir — olculen sey yine URETIM METNIDIR, taklidi degil.

⚠️ OLCULEMEDI = YESIL DEGILDIR. Olculemeyen kol rc=1 verir ve sebebini basar.
"""
import hashlib
import importlib.util
import io
import os
import re
import struct
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SAGLIK_YOL = os.path.join(HERE, "olcu_saglik.py")

# ─── GERCEK VAKALAR (mimar defteri K287 / MaCiT Audi kampanyasi, 25 Agu 2026) ───
VAKA_KIRMIZI = (1659.0, 1659.0, 100.0)      # pid 4675433 — birim sapmasi
VAKA_KIRMIZI_SEBEP = "orta-boyut-tavani-asildi"
VAKA_YESIL = (1860.0, 145.0, 104.0)         # pid 7173324 — mesru marspiyel

# URETIM CAGRI YERLERI (menzil olcumu — kapinin menzili CAGRI YERIDIR).
CAGRI_YERLERI = {
    # 🔴 3 -> 4 (2026-09-03, PARCA onarimi): `obj_bbox` artik IKI cagri yeri tasiyor —
    # (a) yuz (`f`) satirlarindan PARCA cozulen normal yol, (b) yuz satiri OLMAYAN salt
    # nokta bulutunda dosya-bbox'ina dusen beyan edilmis geri-dusus. Ikisi de saglik
    # hukmunden GECMEK ZORUNDA; sayi gevsetilmedi, YENIDEN OLCULUP civilendi
    # ([[cagri-yeri-envanterden-duserse-onarildi-sanilir]]).
    "printables-api.py": 4,     # stl_bbox + bbox_3mf + obj_bbox (parca yolu + geri-dusus)
    "thing-hazirla.py": 1,      # bbox
    "cults3d-api.py": 1,        # _stl_bbox
    "myminifactory-api.py": 1,  # parse_dimensions (metin ayristirir, bbox HESAPLAMAZ)
}
CAGRI_TOPLAMI = 7


# ═══════════════════════════════════════════════════════════════════════════
# FIKSTUR URETICILERI — gercek dosya baytlari
# ═══════════════════════════════════════════════════════════════════════════
_KUTU_YUZLERI = ((0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
                 (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7))


def _koseler(dx, dy, dz):
    return [(0.0, 0.0, 0.0), (dx, 0.0, 0.0), (dx, dy, 0.0), (0.0, dy, 0.0),
            (0.0, 0.0, dz), (dx, 0.0, dz), (dx, dy, dz), (0.0, dy, dz)]


def binary_stl(dx, dy, dz):
    """Gecerli binary STL: 80 bayt baslik + uint32 n + n*50 bayt govde."""
    v = _koseler(dx, dy, dz)
    govde = b"PRUVO K287 sentetik kutu".ljust(80, b"\x00")
    govde += struct.pack("<I", len(_KUTU_YUZLERI))
    for a, b, c in _KUTU_YUZLERI:
        govde += struct.pack("<12f", 0.0, 0.0, 1.0,
                             v[a][0], v[a][1], v[a][2],
                             v[b][0], v[b][1], v[b][2],
                             v[c][0], v[c][1], v[c][2])
        govde += b"\x00\x00"
    return govde


def obj_metni(dx, dy, dz):
    """Wavefront OBJ — 'v X Y Z' satirlari + gurultu olarak vt/vn (sayilmamali)."""
    sat = ["# PRUVO K287 sentetik kutu", "vn 0.0 0.0 1.0", "vt 0.0 0.0"]
    for x, y, z in _koseler(dx, dy, dz):
        sat.append("v %s %s %s" % (x, y, z))
    for a, b, c in _KUTU_YUZLERI:
        sat.append("f %d %d %d" % (a + 1, b + 1, c + 1))
    return ("\n".join(sat) + "\n").encode("utf-8")


_3MF_TIPLER = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
               '<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
               'package.relationships+xml"/><Default Extension="model" ContentType='
               '"application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>\n')
_3MF_RELS = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
             'relationships"><Relationship Target="/3D/3dmodel.model" Id="rel-1" '
             'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
             '</Relationships>\n')
_3MF_NS = ('xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
           'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06"')


def uc_mf(dx, dy, dz, birim="millimeter"):
    """Tek-model, transformsuz 3MF paketi (tools/fikstur/3mf-fikstur-uret.py deseni)."""
    vs = "".join('<vertex x="%s" y="%s" z="%s"/>' % k for k in _koseler(dx, dy, dz))
    kok = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<model unit="%s" %s><resources><object id="1" type="model">'
           '<mesh><vertices>%s</vertices><triangles>'
           '<triangle v1="0" v2="1" v3="2"/><triangle v1="1" v2="3" v3="2"/>'
           '</triangles></mesh></object></resources>'
           '<build><item objectid="1"/></build></model>\n') % (birim, _3MF_NS, vs)
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        for ad, govde in (("[Content_Types].xml", _3MF_TIPLER), ("_rels/.rels", _3MF_RELS),
                          ("3D/3dmodel.model", kok)):
            bilgi = zipfile.ZipInfo(ad, date_time=(2026, 8, 25, 0, 0, 0))
            bilgi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(bilgi, govde)
    return tampon.getvalue()


# ═══════════════════════════════════════════════════════════════════════════
# MODUL YUKLEME
# ═══════════════════════════════════════════════════════════════════════════
def _dosyadan(ad, yol):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _saglik():
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    return _dosyadan("olcu_saglik_k287", SAGLIK_YOL)


def _parca():
    """PARCA tek kaynagi (tools/olcu_parca.py) — `_saglik()` ile AYNI kalip."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    return _dosyadan("olcu_parca_k287", os.path.join(HERE, "olcu_parca.py"))


def _thing_bbox():
    """thing-hazirla.py'nin `bbox()` govdesini KAYNAKTAN cikarip izole derler.

    Import EDILMEZ: o dosya import aninda sabit koke bakar ve CI'da patlar. Cikarma
    birebir metindir — degistirilmis bir kopya DEGIL ([[varlik-beyani-silmeyi-ifade-edemez]])."""
    yol = os.path.join(HERE, "thing-hazirla.py")
    with open(yol, encoding="utf-8") as f:
        kaynak = f.read()
    bas = kaynak.find("\ndef bbox(data):")
    if bas < 0:
        return None, "kaynakta `def bbox(data):` capasi YOK (bayat capa)"
    son = kaynak.find("\ndef ", bas + 1)
    if son < 0:
        return None, "bbox() govdesinin sonu bulunamadi"
    govde = kaynak[bas + 1:son]
    if "olcu_saglik" not in govde:
        return None, "cikarilan govde olcu_saglik'a BAGLI DEGIL (menzil kopmus)"
    # 2026-09-03: govde artik PARCA tek kaynagina da baglidir (olcu, en buyuk DOSYA
    # degil en buyuk PARCA uzerinden verilir). Bagimlilik izole ad alanina VERILIR;
    # kopmasi da ayri gerekce ile OLCULEMEDI'ye duser — sessizce dosya-bbox'ina
    # donmez ([[cagri-yeri-envanterden-duserse-onarildi-sanilir]]).
    if "olcu_parca" not in govde:
        return None, "cikarilan govde olcu_parca'ya BAGLI DEGIL (parca menzili kopmus)"
    ns = {"struct": struct, "olcu_saglik": _saglik(), "olcu_parca": _parca()}
    try:
        exec(compile(govde, "thing-hazirla.py::bbox", "exec"), ns)
    except Exception as e:                                   # noqa: BLE001
        return None, "govde derlenemedi: %r" % (e,)
    return ns.get("bbox"), None


# ═══════════════════════════════════════════════════════════════════════════
# IDDIALAR — her biri (hatalar, olculemedi_sebebi) doner
# ═══════════════════════════════════════════════════════════════════════════
def a1_kirmizi_vaka():
    os_ = _saglik()
    h = os_.hukum(list(VAKA_KIRMIZI))
    if h is None:
        return ["pid 4675433 %s -> YESIL (beklenen KIRMIZI)" % (VAKA_KIRMIZI,)], None
    if h != VAKA_KIRMIZI_SEBEP:
        return ["pid 4675433 KIRMIZI ama SEBEP yanlis: %r (beklenen %r) — dogru kol "
                "olcmuyor olabilir" % (h, VAKA_KIRMIZI_SEBEP)], None
    return [], None


def a2_yesil_vaka():
    os_ = _saglik()
    h = os_.hukum(list(VAKA_YESIL))
    if h is not None:
        return ["pid 7173324 %s -> KIRMIZI (%s); MESRU tam boy marspiyel, YESIL olmali"
                % (VAKA_YESIL, h)], None
    return [], None


def a3_eksen_ikizi():
    """Hukum d1'den mi geliyor? Ikizler arasindaki TEK fark orta boyuttur."""
    os_ = _saglik()
    hatalar = []
    for d, kirmizi_bekleniyor, not_ in (
            ((1860.0, 145.0, 104.0), False, "mesru marspiyel"),
            ((1860.0, 1045.0, 104.0), True, "AYNI d0, orta boyut tavanin USTUNDE"),
            ((1860.0, 995.0, 104.0), False, "AYNI d0, orta boyut tavanin ALTINDA"),
            ((1659.0, 1659.0, 100.0), True, "gercek sapma vakasi"),
            ((1659.0, 100.0, 100.0), False, "AYNI d0, uzun-ince -> mesru sinif"),
            ((900.0, 900.0, 900.0), False, "kare ama tavanin altinda -> simetri KANIT DEGIL"),
            ((483.0, 483.0, 277.0), False, "19 inc jant — canli katalogda MESRU, kare"),
            ((452.0, 452.0, 16.0), False, "Sprinter cati fan adaptoru — MESRU, kare")):
        kirmizi = os_.hukum(list(d)) is not None
        if kirmizi != kirmizi_bekleniyor:
            hatalar.append("%s -> %s (beklenen %s) [%s]"
                           % (d, "KIRMIZI" if kirmizi else "YESIL",
                              "KIRMIZI" if kirmizi_bekleniyor else "YESIL", not_))
    return hatalar, None


def a4_uctan_uca():
    """GERCEK uretim fonksiyonlari + GERCEK dosya baytlari (tautoloji karsiti)."""
    hatalar = []
    olculemedi = []
    try:
        pa = _dosyadan("printables_api_k287", os.path.join(HERE, "printables-api.py"))
    except Exception as e:                                   # noqa: BLE001
        return [], "printables-api.py import edilemedi: %r" % (e,)
    try:
        c3 = _dosyadan("cults3d_api_k287", os.path.join(HERE, "cults3d-api.py"))
    except Exception as e:                                   # noqa: BLE001
        c3 = None
        olculemedi.append("cults3d-api.py import edilemedi: %r" % (e,))
    try:
        mmf = _dosyadan("mmf_api_k287", os.path.join(HERE, "myminifactory-api.py"))
    except Exception as e:                                   # noqa: BLE001
        mmf = None
        olculemedi.append("myminifactory-api.py import edilemedi: %r" % (e,))
    th_bbox, th_sebep = _thing_bbox()
    if th_bbox is None:
        olculemedi.append("thing-hazirla.bbox cikarilamadi: %s" % th_sebep)

    gecici = tempfile.mkdtemp(prefix="k287-")
    try:
        for etiket, d, bekle_none in (("SAPMA", VAKA_KIRMIZI, True),
                                      ("MESRU", VAKA_YESIL, False)):
            beklenen = None if bekle_none else [d[0], d[1], d[2]]

            def _kiyas(ad, gelen):
                if bekle_none:
                    if gelen is not None:
                        hatalar.append("%s %s -> %r (beklenen None)" % (ad, etiket, gelen))
                    return
                if gelen is None:
                    hatalar.append("%s %s -> None (beklenen %r) — MESRU kayit oldu"
                                   % (ad, etiket, beklenen))
                elif [round(float(x), 3) for x in gelen] != beklenen:
                    hatalar.append("%s %s -> %r (beklenen %r)" % (ad, etiket, gelen, beklenen))

            p_stl = os.path.join(gecici, "%s.stl" % etiket)
            with open(p_stl, "wb") as f:
                f.write(binary_stl(*d))
            _kiyas("printables.stl_bbox", pa.stl_bbox(p_stl))
            _kiyas("printables.model_bbox(.stl)", pa.model_bbox(p_stl))
            if c3 is not None:
                _kiyas("cults3d._stl_bbox", c3._stl_bbox(p_stl))
            if th_bbox is not None:
                with open(p_stl, "rb") as f:
                    _kiyas("thing-hazirla.bbox", th_bbox(f.read()))

            p_obj = os.path.join(gecici, "%s.obj" % etiket)
            with open(p_obj, "wb") as f:
                f.write(obj_metni(*d))
            _kiyas("printables.obj_bbox", pa.obj_bbox(p_obj))

            p_3mf = os.path.join(gecici, "%s.3mf" % etiket)
            with open(p_3mf, "wb") as f:
                f.write(uc_mf(*d))
            _kiyas("printables.bbox_3mf", pa.bbox_3mf(p_3mf))

            if mmf is not None:
                _kiyas("mmf.parse_dimensions",
                       mmf.parse_dimensions("%g x %g x %g mm" % d))
    finally:
        for ad in os.listdir(gecici):
            os.unlink(os.path.join(gecici, ad))
        os.rmdir(gecici)
    return hatalar, ("; ".join(olculemedi) if olculemedi else None)


def a5_menzil():
    """Kapinin menzili CAGRI YERIDIR: alti uretim yeri de TEK KAYNAGA bagli mi."""
    hatalar = []
    toplam = 0
    for ad, beklenen in sorted(CAGRI_YERLERI.items()):
        yol = os.path.join(HERE, ad)
        if not os.path.exists(yol):
            hatalar.append("%s YOK (bayat capa)" % ad)
            continue
        with open(yol, encoding="utf-8") as f:
            src = f.read()
        if not re.search(r"^import olcu_saglik\b", src, re.M):
            hatalar.append("%s: `import olcu_saglik` YOK" % ad)
        n = len(re.findall(r"olcu_saglik\.(?:suz|hukum|saglikli)\(", src))
        toplam += n
        if n != beklenen:
            hatalar.append("%s: TEK KAYNAK cagrisi %d (beklenen %d)" % (ad, n, beklenen))
        # Yerel esik ARTIGI kalmamali — kopya esik = sinifin ta kendisi.
        for desen, aciklama in ((r"d\[0\]\s*>\s*100000", "yerel 100000 tavani"),
                                (r"max\(d\)\s*<\s*2\.0", "yerel belirsiz-birim esigi"),
                                (r"d\[0\]\s*<\s*2\.0", "yerel belirsiz-birim esigi"),
                                (r"x\s*\*\s*1000\s+for\s+x\s+in\s+d", "metre-sezgisi x1000")):
            if re.search(desen, src):
                hatalar.append("%s: %s HALA VAR -> ikinci hukum sessizce ayrisir" % (ad, aciklama))
    if toplam != CAGRI_TOPLAMI:
        hatalar.append("TEK KAYNAK cagri toplami %d (beklenen %d)" % (toplam, CAGRI_TOPLAMI))
    return hatalar, None


def a6_turetme():
    """Esik SABITLERI ve OLCULEN pay — tavan sessizce kaydirilirsa KIRMIZI."""
    os_ = _saglik()
    hatalar = []
    if os_.ORTA_TAVAN_MM != 1000.0:
        hatalar.append("ORTA_TAVAN_MM=%r (beklenen 1000.0; turetme: canli katalogda "
                       "d1 p99.9=930 mm -> ust tam metre)" % (os_.ORTA_TAVAN_MM,))
    if os_.BELIRSIZ_BIRIM_ALTI_MM != 2.0:
        hatalar.append("BELIRSIZ_BIRIM_ALTI_MM=%r (beklenen 2.0; K287 ONCESI davranis)"
                       % (os_.BELIRSIZ_BIRIM_ALTI_MM,))
    if os_.EN_BUYUK_TAVAN_MM != 100000.0:
        hatalar.append("EN_BUYUK_TAVAN_MM=%r (beklenen 100000.0; K287 ONCESI davranis)"
                       % (os_.EN_BUYUK_TAVAN_MM,))
    pay = os_.ORTA_TAVAN_MM / os_.OLCULEN_UZUN_INCE_D1_TAVANI
    if os_.OLCULEN_UZUN_INCE_D1_TAVANI != 284.1:
        hatalar.append("OLCULEN_UZUN_INCE_D1_TAVANI=%r (beklenen 284.1 — canli katalogta "
                       "d0>600 kumesinin OLCULEN en buyuk d1'i)"
                       % (os_.OLCULEN_UZUN_INCE_D1_TAVANI,))
    if pay < 3.0:
        hatalar.append("MESRU uzun-ince sinifina birakilan pay %.2fx (< 3x) — tavan "
                       "daraltilmis, mesru parca oldurulur" % pay)
    return hatalar, None


def a7_eski_davranis():
    """K287 ONCESI kollar aynen duruyor mu (regresyon)."""
    os_ = _saglik()
    hatalar = []
    for d, kirmizi_bekleniyor, not_ in (
            ((100.0, 100.0, 0.5), False, "ince levha — max=100, belirsiz DEGIL"),
            ((1.5, 1.0, 0.5), True, "belirsiz birim (beyan YOK)"),
            ((1.99, 1.0, 0.5), True, "belirsiz birim siniri"),
            ((2.0, 1.0, 0.5), False, "belirsiz birim siniri — 2.0 dahil DEGIL"),
            ((200000.0, 10.0, 10.0), True, "100 m ustu"),
            ((0.0, 0.0, 0.0), True, "sifir"),
            ((-5.0, 1.0, 1.0), True, "negatif"),
            ((77.0, 30.0, 26.0), False, "tipik canli kayit"),
            ((329.0, 181.0, 123.0), False, "tipik canli kayit"),):
        kirmizi = os_.hukum(list(d)) is not None
        if kirmizi != kirmizi_bekleniyor:
            hatalar.append("%s -> %s (beklenen %s) [%s]"
                           % (d, "KIRMIZI" if kirmizi else "YESIL",
                              "KIRMIZI" if kirmizi_bekleniyor else "YESIL", not_))
    for bozuk in (None, "abc", (1, 2), (1, 2, 3, 4), (float("nan"), 1, 1)):
        if os_.hukum(bozuk) is None:
            hatalar.append("bozuk girdi %r -> YESIL (fail-closed olmali)" % (bozuk,))
    return hatalar, None


def a8_birim_beyani():
    """Birim BEYAN EDEN kaynaklar (3MF unit, MMF dimensions) belirsiz-birim kolundan MUAF."""
    os_ = _saglik()
    hatalar = []
    if os_.hukum([1.5, 1.0, 0.5], birim_beyanli=True) is not None:
        hatalar.append("beyanli 1.5 mm conta -> KIRMIZI; muafiyet kopmus "
                       "(mesru kucuk parca oldurulur)")
    if os_.hukum([1.5, 1.0, 0.5], birim_beyanli=False) is None:
        hatalar.append("beyansiz 1.5 -> YESIL; belirsiz-birim kolu olu")
    if os_.hukum(list(VAKA_KIRMIZI), birim_beyanli=True) is None:
        hatalar.append("beyanli %s -> YESIL; buyuk uc tavani beyanli kaynakta "
                       "UYGULANMIYOR" % (VAKA_KIRMIZI,))
    return hatalar, None


IDDIALAR = (
    ("A1_KIRMIZI_VAKA", a1_kirmizi_vaka),
    ("A2_YESIL_VAKA", a2_yesil_vaka),
    ("A3_EKSEN_IKIZI", a3_eksen_ikizi),
    ("A4_UCTAN_UCA", a4_uctan_uca),
    ("A5_MENZIL", a5_menzil),
    ("A6_TURETME", a6_turetme),
    ("A7_ESKI_DAVRANIS", a7_eski_davranis),
    ("A8_BIRIM_BEYANI", a8_birim_beyani),
)


def kos():
    """[(ad, durum, ayrinti)] — durum: YESIL / KIRMIZI / OLCULEMEDI."""
    cikti = []
    for ad, fn in IDDIALAR:
        try:
            hatalar, olculemedi = fn()
        except Exception as e:                               # noqa: BLE001
            cikti.append((ad, "KIRMIZI", "iddia PATLADI: %r" % (e,)))
            continue
        if olculemedi:
            cikti.append((ad, "OLCULEMEDI", olculemedi))
        elif hatalar:
            cikti.append((ad, "KIRMIZI", " | ".join(hatalar)))
        else:
            cikti.append((ad, "YESIL", ""))
    return cikti


# ═══════════════════════════════════════════════════════════════════════════
# MUTASYON BATARYASI — her mutant HANGI IDDIAYI oldurdugunu BEYAN EDER
# ═══════════════════════════════════════════════════════════════════════════
# (ad, capa, yeni_metin, oldurmesi_beklenen_iddialar, gerekce)
MUTANTLAR = (
    ("M1 orta tavani OLDUR",
     "ORTA_TAVAN_MM = 1000.0",
     "ORTA_TAVAN_MM = 1000000000.0",
     {"A1_KIRMIZI_VAKA", "A3_EKSEN_IKIZI", "A4_UCTAN_UCA", "A6_TURETME",
      "A8_BIRIM_BEYANI"},
     "tavan yoksa 1659x1659 vakasi eski kapidaki gibi GECER (beyanli kaynakta da)"),

    ("M2 orta tavani ASIRI DARALT",
     "ORTA_TAVAN_MM = 1000.0",
     "ORTA_TAVAN_MM = 120.0",
     {"A2_YESIL_VAKA", "A3_EKSEN_IKIZI", "A4_UCTAN_UCA", "A6_TURETME",
      "A7_ESKI_DAVRANIS"},
     "IKINCI YON: dar tavan MESRU marspiyeli (d1=145) ve tipik canli kaydi "
     "(329x181x123) oldurur"),

    ("M3 ekseni d0'a KAYDIR",
     "    if dd[1] > ORTA_TAVAN_MM:",
     "    if dd[0] > ORTA_TAVAN_MM:",
     {"A2_YESIL_VAKA", "A3_EKSEN_IKIZI", "A4_UCTAN_UCA"},
     "EKSEN KANITI: en buyuk boyuta tasinirsa marspiyel (d0=1860) oldurulur"),

    ("M4 ekseni d2'ye KAYDIR",
     "    if dd[1] > ORTA_TAVAN_MM:",
     "    if dd[2] > ORTA_TAVAN_MM:",
     {"A1_KIRMIZI_VAKA", "A3_EKSEN_IKIZI", "A4_UCTAN_UCA", "A8_BIRIM_BEYANI"},
     "en kucuk boyuta tasinirsa 1659x1659x100 (d2=100) KACAR"),

    ("M5 belirsiz-birim kolunu OLDUR",
     "BELIRSIZ_BIRIM_ALTI_MM = 2.0",
     "BELIRSIZ_BIRIM_ALTI_MM = 0.0",
     {"A6_TURETME", "A7_ESKI_DAVRANIS", "A8_BIRIM_BEYANI"},
     "K287 ONCESI kucuk-uc korumasi kaybolursa regresyon kollari yanmali"),

    ("M6 birim-beyani MUAFIYETINI OLDUR",
     "    if not birim_beyanli and dd[0] < BELIRSIZ_BIRIM_ALTI_MM:",
     "    if dd[0] < BELIRSIZ_BIRIM_ALTI_MM:",
     {"A8_BIRIM_BEYANI"},
     "muafiyet dusenken 3MF/MMF'in mesru kucuk parcasi oldurulur"),

    ("M7 en-buyuk tavani OLDUR",
     "EN_BUYUK_TAVAN_MM = 100000.0",
     "EN_BUYUK_TAVAN_MM = 1000000000000.0",
     {"A6_TURETME", "A7_ESKI_DAVRANIS"},
     "eski 100 m tavani sessizce kalkarsa regresyon kolu yanmali"),

    ("M8 OLCULEN pay capasini BOSALT",
     "OLCULEN_UZUN_INCE_D1_TAVANI = 284.1",
     "OLCULEN_UZUN_INCE_D1_TAVANI = 999.0",
     {"A6_TURETME"},
     "pay iddiasi TAUTOLOJI DEGIL: olculen capa kayarsa A6 tek basina yanar"),

    ("M9 KONTROL — anlam degistirmeyen duzenleme",
     "def saglikli(d, birim_beyanli=False):",
     "def saglikli(d, birim_beyanli=False):  # kontrol mutanti",
     set(),
     "KONTROL: hicbir iddia yanmamali; yanarsa batarya gurultu olcuyor"),
)


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _pyc_temizle():
    """🔴 OLCULDU (25 Agu 2026, bu bataryanin ILK kosumunda): `dd[1]` -> `dd[2]` gibi
    AYNI UZUNLUKTAKI bir mutant dosya BOYUTUNU degistirmez; CPython'un .pyc gecerlilik
    olcutu (mtime + boyut) ayni saniye icinde AYNI kalir ve alt surec BIR ONCEKI MUTANTIN
    bytecode'unu yukler. Sonuc: M4 ve M5, M3'un sonuc kumesini birebir tekrarladi ve
    "mutant olmedi" gibi gorundu. Onlem UC KATLI: -B + PYTHONDONTWRITEBYTECODE + elle
    silme; ustune KAYNAK_SHA / DAVRANIS_IZI capalari mutantin GERCEKTEN etki ettigini
    ayrica kanitlar."""
    kok = os.path.join(HERE, "__pycache__")
    if not os.path.isdir(kok):
        return
    for ad in os.listdir(kok):
        if ad.startswith("olcu_saglik") or ad.startswith("olcu-saglik"):
            try:
                os.unlink(os.path.join(kok, ad))
            except OSError:
                pass


def _dokum_kos():
    """Alt surecte iddia dokumunu al -> ({ad: durum}, izler, CompletedProcess)."""
    _pyc_temizle()
    ortam = dict(os.environ)
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run([sys.executable, "-B", os.path.abspath(__file__), "--iddia-dokumu"],
                       capture_output=True, text=True, cwd=HERE, env=ortam)
    durum = {}
    izler = {}
    for satir in (r.stdout or "").splitlines():
        if satir.startswith("IDDIA "):
            ad, _, kalan = satir[6:].partition("=")
            durum[ad.strip()] = kalan.split("::")[0].strip()
        elif satir.startswith("KAYNAK_SHA=") or satir.startswith("DAVRANIS_IZI="):
            ad, _, deger = satir.partition("=")
            izler[ad] = deger.strip()
    return durum, izler, r


# DAVRANIS IZI PROB IZGARASI — hukum() cikti dizisinin ozeti. Mutantin dosyaya
# yazilmasi YETMEZ, DAVRANISA da varmali; iz taban ile ayni kalirsa mutant OLU demektir.
_PROB_IZGARASI = tuple(
    (d, beyanli)
    for beyanli in (False, True)
    for d in ((1659.0, 1659.0, 100.0), (1860.0, 145.0, 104.0), (1860.0, 1045.0, 104.0),
              (1860.0, 995.0, 104.0), (900.0, 900.0, 900.0), (483.0, 483.0, 277.0),
              (100.0, 100.0, 0.5), (1.5, 1.0, 0.5), (2.0, 1.0, 0.5),
              (200000.0, 10.0, 10.0), (0.0, 0.0, 0.0), (77.0, 30.0, 26.0))
)


def _davranis_izi():
    os_ = _saglik()
    parcalar = ["%s|%s|%s" % (d, b, os_.hukum(list(d), birim_beyanli=b))
                for d, b in _PROB_IZGARASI]
    parcalar.append("sabit|%s|%s|%s|%s" % (os_.ORTA_TAVAN_MM, os_.BELIRSIZ_BIRIM_ALTI_MM,
                                           os_.EN_BUYUK_TAVAN_MM,
                                           os_.OLCULEN_UZUN_INCE_D1_TAVANI))
    return hashlib.sha256("\n".join(parcalar).encode("utf-8")).hexdigest()


def mutasyon():
    with open(SAGLIK_YOL, "rb") as f:
        orijinal = f.read()
    taban_sha = hashlib.sha256(orijinal).hexdigest()
    kaynak = orijinal.decode("utf-8")

    print("MUTASYON BATARYASI — hedef: tools/olcu_saglik.py (sha %s)" % taban_sha[:12])
    taban, taban_iz, r0 = _dokum_kos()
    if not taban:
        print("TABAN DOKUMU ALINAMADI (rc=%d)\n%s" % (r0.returncode, r0.stderr[-2000:]))
        return 1
    taban_kirmizi = {a for a, d in taban.items() if d != "YESIL"}
    if taban_kirmizi:
        print("TABAN TEMIZ DEGIL — once kabul testini yesillet: %s"
              % ", ".join(sorted(taban_kirmizi)))
        return 1
    if taban_iz.get("KAYNAK_SHA") != taban_sha:
        print("TABAN KAYNAK_SHA TUTMADI (%s != %s) — alt surec baska dosya okuyor"
              % (taban_iz.get("KAYNAK_SHA"), taban_sha))
        return 1
    print("TABAN: %d iddia, hepsi YESIL · davranis izi %s"
          % (len(taban), (taban_iz.get("DAVRANIS_IZI") or "?")[:12]))

    hata = 0
    olu = 0
    try:
        for ad, capa, yeni, beklenen, gerekce in MUTANTLAR:
            if kaynak.count(capa) != 1:
                print("  %-38s BAYAT CAPA (%d kez gecti) -> %r"
                      % (ad, kaynak.count(capa), capa))
                hata += 1
                continue
            mutant = kaynak.replace(capa, yeni, 1)
            mutant_sha = hashlib.sha256(mutant.encode("utf-8")).hexdigest()
            with open(SAGLIK_YOL, "w", encoding="utf-8") as f:
                f.write(mutant)
            durum, iz, r = _dokum_kos()
            with open(SAGLIK_YOL, "wb") as f:
                f.write(orijinal)
            if not durum:
                print("  %-38s DOKUM ALINAMADI (rc=%d) — mutant SOZDIZIMI bozmus olabilir"
                      % (ad, r.returncode))
                hata += 1
                continue
            # ① Mutant DOSYAYA vardi mi (alt surec gercekten onu mu okudu)?
            if iz.get("KAYNAK_SHA") != mutant_sha:
                print("  %-38s MUTANT ULASMADI  kaynak_sha=%s (beklenen %s) — "
                      "alt surec bayat kopya/bytecode okumus"
                      % (ad, (iz.get("KAYNAK_SHA") or "?")[:12], mutant_sha[:12]))
                hata += 1
                continue
            # ② Mutant DAVRANISA vardi mi? Oldurucu mutantin izi tabandan FARKLI olmali;
            #    kontrol mutantinin izi AYNI kalmali. Bu, "kirmizi geldi ama baska
            #    sebepten" ile "hedef kol gercekten olduruldu"yu ayirir.
            iz_farkli = iz.get("DAVRANIS_IZI") != taban_iz.get("DAVRANIS_IZI")
            if beklenen and not iz_farkli:
                print("  %-38s DAVRANISA VARMADI  iz taban ile AYNI -> mutant OLU "
                      "(dosya degisti, hukum degismedi)" % ad)
                hata += 1
                continue
            if not beklenen and iz_farkli:
                print("  %-38s KONTROL DAVRANISI DEGISTI  iz tabandan farkli -> "
                      "kontrol mutanti anlam tasiyor, kontrol DEGIL" % ad)
                hata += 1
                continue
            olculen = {a for a, d in durum.items() if d != "YESIL"}
            if olculen == beklenen:
                if beklenen:
                    olu += 1
                    print("  %-38s OLDU  hedef=%s" % (ad, ",".join(sorted(beklenen))))
                else:
                    print("  %-38s KONTROL YESIL (beklendigi gibi)" % ad)
            else:
                hata += 1
                print("  %-38s IZ_AYRIMI=YANLIS  beyan=%s  olculen=%s  (%s)"
                      % (ad, ",".join(sorted(beklenen)) or "-",
                         ",".join(sorted(olculen)) or "-", gerekce))
    finally:
        with open(SAGLIK_YOL, "wb") as f:
            f.write(orijinal)
        _pyc_temizle()

    son_sha = _sha(SAGLIK_YOL)
    print("CANLI DOSYA sha256 %s (%s)"
          % (son_sha[:12], "TAM" if son_sha == taban_sha else "BOZUK!"))
    if son_sha != taban_sha:
        hata += 1
    oldurucu = len([m for m in MUTANTLAR if m[3]])
    print("OZET: oldurucu %d/%d · iz ayrimi %s"
          % (olu, oldurucu, "DOGRU" if hata == 0 else "YANLIS"))
    return 1 if hata else 0


def main():
    argv = sys.argv[1:]
    if "--mutasyon" in argv:
        return mutasyon()
    sonuc = kos()
    dokum = "--iddia-dokumu" in argv
    if not dokum:
        print("K287 — bbox birim/olcu saglik kabul testi")
        print("  SAPMA VAKASI (pid 4675433): %s mm  -> KIRMIZI olmali" % (VAKA_KIRMIZI,))
        print("  MESRU VAKA   (pid 7173324): %s mm  -> YESIL olmali" % (VAKA_YESIL,))
        print("")
    kotu = 0
    for ad, durum, ayrinti in sonuc:
        if durum != "YESIL":
            kotu += 1
        if dokum:
            print("IDDIA %s=%s%s" % (ad, durum, (" :: " + ayrinti) if ayrinti else ""))
        else:
            print("  %-18s %s%s" % (ad, durum, ("  ::  " + ayrinti) if ayrinti else ""))
    if dokum:
        # Mutasyon surucusunun CAPALARI: (1) alt surec HANGI kaynagi okudu,
        # (2) o kaynak DAVRANISI degistirdi mi. Bytecode bayatligi bu iki satirla
        # yakalanir — dosya degisip hukum degismezse iz taban ile AYNI kalir.
        print("KAYNAK_SHA=%s" % _sha(SAGLIK_YOL))
        print("DAVRANIS_IZI=%s" % _davranis_izi())
    if not dokum:
        print("")
        print("OZET: %d/%d YESIL" % (len(sonuc) - kotu, len(sonuc)))
        if kotu:
            print("🔴 OLCULEMEDI de YESIL DEGILDIR (fail-closed).")
    return 1 if kotu else 0


if __name__ == "__main__":
    sys.exit(main())
