#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OLCU = EN BUYUK PARCA (dosya DEGIL) — kabul + mutasyon bataryasi.

HUKUM (BaBa 2026-09-03 17:1x ② · cip KraL-HasatEkleRedKapisi-3Eyl):
  Bir model dosyasi tabla dizilmis birden cok govde tasiyabilir. Olcu, DOSYANIN
  sinir kutusundan degil EN BUYUK PARCANIN sinir kutusundan verilir.

NEDEN — CANLI ONBELLEKTE OLCULDU (198 .stl ornegi, .thing-cache):
  * cok-parcali dosya 40/198 = %20,2
  * cok-parcali dosyalarda dosya-bbox'inin EN BUYUK BOYUTU gercek parcaninkinden
    ORTALAMA %21,8, en kotu vakada %70,6 BUYUK
    (th1692616: dosya 106,4 mm -> parca 31,3 mm)
  * gorulen en yuksek parca sayisi 1199 (pr963888)
  Sapma urun aciklamasindaki "mm" satirina, oradan fiyat/filament tavsiyesine akiyordu.

VAKALAR
  P1 tek parca kup                  -> dosya-bbox ile BIREBIR AYNI (yanlis-pozitif nobetcisi;
                                       modellerin ~%80'i tek parca, sonuc DEGISMEMELI)
  P2 tabla: 20mm kup + 8mm alt-bolunmus levha, 100mm ayrik -> 20mm kup (110mm ACIKLIK DEGIL)
     (levhanin UCGEN SAYISI kuptenden COK: "en buyuk"un HACIM oldugunu kanitlar)
  P3 14 parcali tabla                -> en buyuk govde
  P4 OBJ iki ayrik kutu              -> buyuk olan
  P5 3MF iki build item              -> buyuk olan
  P6 OBJ yuz satiri YOK (nokta bulutu) -> dosya-bbox'ina duser (beyan edilen sinir)
  P7 KOSE PAYLASAN iki govde         -> TEK parca (asiri bolme yok)

MUTANTLAR — her biri OLDURDUGU HEDEF KOLU adiyla gosterir.
  N1 parca ayrimi devre disi (_parca_kutulari daima None)   KOL: parca-ayrimi
  N2 "en buyuk" olcutu HACIM yerine UCGEN SAYISI            KOL: en-buyuk-olcut-hacim
  N3 3MF item-basi kutu toplama kaldirildi                  KOL: 3mf-item-parcasi
  N4 OBJ 'f' yuz cozumu kaldirildi                          KOL: obj-yuz-cozumu
  NK KONTROL: yalniz bir yorum/mesaj dizesi degisir         KOL: YOK (hicbir vaka degismez)
"""
import importlib.util
import os
import shutil
import struct
import sys
import tempfile
import zipfile

KOK = os.path.dirname(os.path.abspath(__file__))
API = os.path.join(KOK, "printables-api.py")


def _yukle(yol, ad="pr_api"):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ad] = mod
    spec.loader.exec_module(mod)
    return mod


# --- geometri uretecleri ------------------------------------------------------
def kutu_ucgenleri(sx, sy, sz, ox=0.0, oy=0.0, oz=0.0):
    """Eksen-hizali kutunun 12 ucgeni (kose noktalari mutlak koordinatta)."""
    x0, y0, z0 = ox, oy, oz
    x1, y1, z1 = ox + sx, oy + sy, oz + sz
    k = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    yuz = [(0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6), (0, 4, 5), (0, 5, 1),
           (1, 5, 6), (1, 6, 2), (2, 6, 7), (2, 7, 3), (3, 7, 4), (3, 4, 0)]
    return [(k[a], k[b], k[c]) for a, b, c in yuz]


def levha_ucgenleri(sx, sy, sz, ox, oy, oz, bolme):
    """Ust yuzu `bolme x bolme` alt-ucgenlere bolunmus ince levha (UCGEN SAYISI YUKSEK,
    HACIM DUSUK) — "en buyuk" olcutunun hacim mi ucgen sayisi mi oldugunu ayirt eder."""
    ucg = kutu_ucgenleri(sx, sy, sz, ox, oy, oz)[2:]     # ust yuzu cikar, yerine bolunmus
    ax, ay = sx / bolme, sy / bolme
    for i in range(bolme):
        for j in range(bolme):
            x0, y0 = ox + i * ax, oy + j * ay
            x1, y1 = x0 + ax, y0 + ay
            z = oz + sz
            ucg.append(((x0, y0, z), (x1, y0, z), (x1, y1, z)))
            ucg.append(((x0, y0, z), (x1, y1, z), (x0, y1, z)))
    return ucg


def binary_stl(ucgenler):
    blob = b"\0" * 80 + struct.pack("<I", len(ucgenler))
    for t in ucgenler:
        blob += struct.pack("<3f", 0.0, 0.0, 0.0)
        for v in t:
            blob += struct.pack("<3f", *v)
        blob += b"\0\0"
    return blob


def obj_metni(ucgenler):
    satir, koseler, indeks = [], [], {}
    for t in ucgenler:
        for v in t:
            if v not in indeks:
                indeks[v] = len(koseler) + 1
                koseler.append(v)
    for v in koseler:
        satir.append("v %.6f %.6f %.6f" % v)
    for t in ucgenler:
        satir.append("f %d %d %d" % tuple(indeks[v] for v in t))
    return ("\n".join(satir) + "\n").encode()


def obj_nokta_bulutu(ucgenler):
    """Yalniz 'v' satirlari — 'f' YOK (parca ayrimi yapilamaz, dosya-bbox'ina duser)."""
    gorulen, satir = set(), []
    for t in ucgenler:
        for v in t:
            if v not in gorulen:
                gorulen.add(v)
                satir.append("v %.6f %.6f %.6f" % v)
    return ("\n".join(satir) + "\n").encode()


def _model_xml(objeler, itemlar, unit="millimeter"):
    p = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<model unit="%s" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
         % unit, "<resources>"]
    for oid, ucgenler in objeler:
        koseler, indeks = [], {}
        for t in ucgenler:
            for v in t:
                if v not in indeks:
                    indeks[v] = len(koseler)
                    koseler.append(v)
        p.append('<object id="%s" type="model"><mesh><vertices>' % oid)
        for v in koseler:
            p.append('<vertex x="%.6f" y="%.6f" z="%.6f"/>' % v)
        p.append("</vertices><triangles>")
        for t in ucgenler:
            p.append('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(indeks[v] for v in t))
        p.append("</triangles></mesh></object>")
    p.append("</resources><build>")
    for oid in itemlar:
        p.append('<item objectid="%s"/>' % oid)
    p.append("</build></model>")
    return "\n".join(p).encode()


def tmf_yaz(yol, objeler, itemlar):
    with zipfile.ZipFile(yol, "w") as z:
        z.writestr("3D/3dmodel.model", _model_xml(objeler, itemlar))


# --- vakalar ------------------------------------------------------------------
KUCUK = kutu_ucgenleri(8, 8, 1, 0, 0, 0)
BUYUK = kutu_ucgenleri(20, 20, 20, 100, 0, 0)
LEVHA_COK_UCGEN = levha_ucgenleri(8, 8, 1, 0, 0, 0, 12)          # 288+ ucgen, hacim 64
ONBES = []
for _i in range(14):
    ONBES += kutu_ucgenleri(5 + _i, 5, 5, _i * 60, 0, 0)          # en buyuk: 18x5x5
KOSE_PAYLASAN = kutu_ucgenleri(10, 10, 10, 0, 0, 0) + kutu_ucgenleri(10, 10, 10, 10, 0, 0)


def vakalar(mod, calisma):
    """[(ad, olculen, beklenen)] — beklenen = en buyuk boyut (mm)."""
    sonuc = []

    def stl(ad, ucgenler):
        y = os.path.join(calisma, ad + ".stl")
        with open(y, "wb") as f:
            f.write(binary_stl(ucgenler))
        return mod.stl_bbox(y)

    def obj(ad, blob):
        y = os.path.join(calisma, ad + ".obj")
        with open(y, "wb") as f:
            f.write(blob)
        return mod.obj_bbox(y)

    sonuc.append(("P1 tek parca kup 20mm", stl("p1", BUYUK), [20.0, 20.0, 20.0]))
    sonuc.append(("P2 tabla: 20mm kup + cok-ucgenli levha",
                  stl("p2", BUYUK + LEVHA_COK_UCGEN), [20.0, 20.0, 20.0]))
    sonuc.append(("P3 14 parcali tabla", stl("p3", ONBES), [18.0, 5.0, 5.0]))
    sonuc.append(("P4 OBJ iki ayrik kutu",
                  obj("p4", obj_metni(KUCUK + BUYUK)), [20.0, 20.0, 20.0]))
    y5 = os.path.join(calisma, "p5.3mf")
    tmf_yaz(y5, [("1", KUCUK), ("2", BUYUK)], ["1", "2"])
    sonuc.append(("P5 3MF iki build item", mod.bbox_3mf(y5), [20.0, 20.0, 20.0]))
    sonuc.append(("P6 OBJ nokta bulutu (f yok)",
                  obj("p6", obj_nokta_bulutu(KUCUK + BUYUK)), [120.0, 20.0, 20.0]))
    sonuc.append(("P7 kose paylasan iki govde -> TEK parca",
                  stl("p7", KOSE_PAYLASAN), [20.0, 10.0, 10.0]))
    return sonuc


PARCA = "olcu_parca.py"          # TEK KAYNAK (parca ayrimi + "en buyuk" olcutu)
PRAPI = "printables-api.py"      # bicim-ozgu kollar (3MF item · OBJ yuz cozumu)

MUTANTLAR = [
    ("N1 parca ayrimi devre disi", "parca-ayrimi", PARCA,
     "    n_ucgen = len(xs) // 3\n    if n_ucgen == 0:",
     "    n_ucgen = len(xs) // 3\n    if True:  # MUTANT\n        return []\n    if n_ucgen == 0:",
     # P3 tabla acikligi: son kutu 13*60 = 780 ofsette, genislik 5+13 = 18 -> 798 mm
     {"P2": [120.0, 20.0, 20.0], "P3": [798.0, 5.0, 5.0], "P4": [120.0, 20.0, 20.0],
      "P1": [20.0, 20.0, 20.0]}),
    ("N2 'en buyuk' olcutu = ucgen sayisi", "en-buyuk-olcut-hacim", PARCA,
     "    en = max(kutular, key=lambda k: (k[0] * k[1] * k[2], k[3]))",
     "    en = max(kutular, key=lambda k: (k[3], k[0]))  # MUTANT: ucgen sayisi",
     {"P2": [8.0, 8.0, 1.0], "P1": [20.0, 20.0, 20.0]}),
    ("N3 3MF item-basi kutu toplama kaldirildi", "3mf-item-parcasi", PRAPI,
     "                if len(xs) > onceki:                      # bu item'in KENDI bbox'i",
     "                if False:  # MUTANT",
     {"P5": [120.0, 20.0, 20.0]}),
    ("N4 OBJ 'f' yuz cozumu kaldirildi", "obj-yuz-cozumu", PRAPI,
     '        elif p[0] == "f" and len(p) >= 4:',
     '        elif False:  # MUTANT',
     {"P4": [120.0, 20.0, 20.0], "P2": [20.0, 20.0, 20.0]}),
    ("NK KONTROL (yalniz ilan metni)", "YOK", PARCA,
     "PARCA AYRIMI YAPILMADI (ucgen>%d)",
     "PARCA AYRIMI YAPILMADI [kontrol] (ucgen>%d)",
     {}),
]

# TEK KAYNAK nobetcisi: parca ayrimi govdesi YALNIZ olcu_parca.py'de olmali; bbox
# HESAPLAYAN uretim dosyalarinin HEPSI oraya delege etmeli (K287 dersi: kopyalar
# "AYNI karar" diye iddia ederken sessizce ayrisir). Envanter olculerek civilendi.
OKUYUCULAR = ("printables-api.py", "cults3d-api.py", "thing-hazirla.py",
              "thingiverse-fetch.py", "printables-fetch.py", "stl-measure.py")


def _yakin(a, b, tol=0.05):
    if a is None or b is None:
        return a is b
    if len(a) != len(b):
        return False
    return all(abs(x - y) <= max(tol, abs(y) * 0.01) for x, y in zip(a, b))


def main():
    calisma = tempfile.mkdtemp(prefix="parca-kabul-")
    hatalar = []
    iddia = gecti = 0
    try:
        mod = _yukle(API, "pr_api_temiz")
        taban = {}
        print("--- TABAN (teslim edilen arac) ---")
        for ad, olculen, beklenen in vakalar(mod, calisma):
            iyi = _yakin(olculen, beklenen)
            iddia += 1
            gecti += 1 if iyi else 0
            taban[ad.split()[0]] = olculen
            print("[%s] %-42s -> %s (beklenen %s)"
                  % ("OK" if iyi else "HATA", ad, olculen, beklenen))
            if not iyi:
                hatalar.append("%s: %s != %s" % (ad, olculen, beklenen))

        for m_ad, kol, hedef_dosya, ara, koy, beklentiler in MUTANTLAR:
            print("")
            iddia += 1
            kaynak = open(os.path.join(KOK, hedef_dosya), encoding="utf-8").read()
            if ara not in kaynak:
                print("[HATA] %s KURULAMADI: capa %s icinde yok" % (m_ad, hedef_dosya))
                hatalar.append("%s: mutant capasi %s icinde yok" % (m_ad, hedef_dosya))
                continue
            gecti += 1
            mdizin = os.path.join(calisma, "mut-" + m_ad.split()[0])
            os.makedirs(mdizin, exist_ok=True)
            # 🔴 MUTANT IZOLASYONU: mutantlanan dosya DAHIL tum bagimlilik kopyalanir,
            # boylece mutant CANLI gövdeye degil kopyaya uygulanir ve olcum kendi
            # baglamini olcer ([[mutant-canli-govdede-yasamaz]]).
            for yardimci in ("olcu_saglik.py", "olcu_parca.py", "printables-api.py"):
                shutil.copy(os.path.join(KOK, yardimci), os.path.join(mdizin, yardimci))
            with open(os.path.join(mdizin, hedef_dosya), "w", encoding="utf-8") as f:
                f.write(kaynak.replace(ara, koy))
            myol = os.path.join(mdizin, "printables-api.py")
            # 🔴 `import olcu_parca` sys.modules'te ONBELLEKLENIR: temiz kosum onu KOK'ten
            # yuklemis olur ve mutant kopya HIC OKUNMAZ (mutant "ulasmaz", batarya sahte
            # yesil verir -> [[mutantli-kosum-tabanla-ayniysa-mutant-ulasmadi]]).
            # Bu yuzden yardimci modulleri onbellekten DUSURUP mutant dizininden yukletiyoruz.
            saklanan = {ad: sys.modules.pop(ad)
                        for ad in ("olcu_parca", "olcu_saglik") if ad in sys.modules}
            sys.path.insert(0, mdizin)
            try:
                mmod = _yukle(myol, "pr_api_mut_" + m_ad.split()[0])
            finally:
                sys.path.pop(0)
                for ad in ("olcu_parca", "olcu_saglik"):
                    sys.modules.pop(ad, None)
                sys.modules.update(saklanan)
            print("--- %s | HEDEF KOL: %s" % (m_ad, kol))
            m_sonuc = {a.split()[0]: o for a, o, _b in vakalar(mmod, mdizin)}
            hedefler = beklentiler or {k: v for k, v in taban.items()}
            for vaka, bekle in sorted(hedefler.items()):
                olculen = m_sonuc.get(vaka)
                iyi = _yakin(olculen, bekle)
                iddia += 1
                gecti += 1 if iyi else 0
                not_ = "AYNI" if _yakin(bekle, taban.get(vaka)) else "DEGISTI"
                print("    [%s] %s -> %s (beklenen %s, %s)"
                      % ("OK" if iyi else "HATA", vaka, olculen, bekle, not_))
                if not iyi:
                    hatalar.append("%s/%s: %s != %s" % (m_ad, vaka, olculen, bekle))

        print("")
        mod2 = _yukle(API, "pr_api_geri")
        for ad, olculen, beklenen in vakalar(mod2, calisma):
            iyi = _yakin(olculen, beklenen)
            iddia += 1
            gecti += 1 if iyi else 0
            if not iyi:
                hatalar.append("geri alma sonrasi %s degisti" % ad)
        print("[%s] MUTANT GERI ALINDI: 7 vaka temiz kaynakta AYNEN"
              % ("OK" if not [h for h in hatalar if "geri alma" in h] else "HATA"))

        # --- TEK KAYNAK + OKUYUCU ENVANTERI ------------------------------------
        print("")
        ikinci = []
        for f in sorted(os.listdir(KOK)):
            if not f.endswith(".py") or f == "olcu_parca.py":
                continue
            if "-test.py" in f or f.startswith("test-"):
                continue
            g = open(os.path.join(KOK, f), encoding="utf-8", errors="replace").read()
            if "def parca_kutulari" in g:
                ikinci.append(f)
        iyi = not ikinci
        iddia += 1
        gecti += 1 if iyi else 0
        print("[%s] TEK KAYNAK: `parca_kutulari` govdesi yalniz olcu_parca.py'de "
              "(ikinci govde: %s)" % ("OK" if iyi else "HATA", ikinci or "yok"))
        if not iyi:
            hatalar.append("parca ayrimi ikinci kez tanimli: %s" % ikinci)

        # Her okuyucu TEK KAYNAGA delege ediyor mu? (arizanin YER DEGISTIRMESI kolu)
        delege_yok = []
        for f in OKUYUCULAR:
            g = open(os.path.join(KOK, f), encoding="utf-8", errors="replace").read()
            if "olcu_parca" not in g:
                delege_yok.append(f)
        iyi = not delege_yok
        iddia += 1
        gecti += 1 if iyi else 0
        print("[%s] OKUYUCU ENVANTERI: %d/%d uretim dosyasi olcu_parca'ya delege ediyor "
              "(delege etmeyen: %s)"
              % ("OK" if iyi else "HATA", len(OKUYUCULAR) - len(delege_yok),
                 len(OKUYUCULAR), delege_yok or "yok"))
        if not iyi:
            hatalar.append("bbox hesaplayan dosya olcu_parca'ya delege etmiyor: %s"
                           % delege_yok)
    finally:
        shutil.rmtree(calisma, ignore_errors=True)

    print("")
    print("VAKA=7 IDDIA=%d GECTI=%d KIRMIZI=%d" % (iddia, gecti, len(hatalar)))
    if hatalar:
        print("KABUL KIRMIZI: %d hata" % len(hatalar))
        for h in hatalar:
            print("  - " + h)
        return 1
    print("KABUL YESIL: 7 vaka + 4 mutant (hedef kol atifli) + 1 kontrol gecti")
    return 0


if __name__ == "__main__":
    sys.exit(main())
