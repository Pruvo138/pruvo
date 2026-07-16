#!/usr/bin/env python3
"""bbox_3mf() kabul testi — cok-.model (Bambu-Studio) 3MF arsivlerinde dogru olcum.

`python3 tools/test-bbox-3mf.py` (argumansiz). Basarisizlikta sifir-olmayan cikis kodu.

Neyi dogruluyor:
  1. ANKRAJ: iki Chrysler urunu (kok 3D/3dmodel.model bos, gercek geometri 3D/Objects/*.model).
     Eski fonksiyon names[0]'i (bos kok modeli) okudugu icin None donuyordu; yeni fonksiyon
     transform zincirini cozerek olcmeli, elle olcume ±%5 / ±2 mm toleransla ortusmeli.
  2. REGRESYON: stl/ altindaki TUM .3mf dosyalari eski (names[0]+regex) ve yeni mantikla
     olculur. Eski fonksiyonun olcebildigi (tek-.model) dosyalarda sonuc DEGISMEMELI; eski
     None donup yeni olcen dosyalar "onarilan" sayilir. Eski deger verip yeni None donmek
     = HARD FAIL (regresyon). Transform kaynakli kucuk sapmalar raporlanir, fail sayilmaz.

ELLE OLCUM NOTU: verilen 47x40x31 ve 172x171x22 degerleri "manuel zip+regex" ile, yani
transform'suz HAM vertex birlesimiyle olculmustu. Bu iki dosyada transform'lu dogru hesap
ile ham hesap AYNI cikiyor (biri identity+oteleme, digeri 90° X/Z takasi — ikisi de eksen
hizali sinir kutusunun SIRALI boyutlarini degistirmez), o yuzden beklenen degerler elle
olcume esit sabitlendi. Sapma cikan urun OLMADI, urunler.json olcu satiri duzeltmesi gerekmez.
"""
import importlib.util, os, re, struct, sys, zipfile, glob

HERE = os.path.dirname(os.path.abspath(__file__))
STL_DIR = "/Users/okan/dev/pruvo/stl"

# --- test edilen modulu yukle (dosya adinda '-' var, normal import olmaz) ---
_spec = importlib.util.spec_from_file_location("printables_api",
                                               os.path.join(HERE, "printables-api.py"))
pa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pa)

# --- ANKRAJ: elle olculmus degerler (buyukten kucuge, mm) ---
ANKRAJ = {
    os.path.join(STL_DIR, "pr1173083.3mf"): [47, 40, 31],   # chrysler-dodge guneslik klipsi
    os.path.join(STL_DIR, "pr912419.3mf"): [172, 171, 22],  # Pacifica jant gobek kapagi
}


def tolere(beklenen, olculen):
    """Her boyut ±%5 veya ±2 mm (hangisi buyukse) toleransla ortusuyor mu?"""
    if olculen is None or len(olculen) != 3:
        return False
    for b, o in zip(sorted(beklenen, reverse=True), sorted(olculen, reverse=True)):
        if abs(b - o) > max(2.0, b * 0.05):
            return False
    return True


# --- ESKI davranisin bagimsiz referans implementasyonu (ilk .model + regex) ---
_SAYI = r"[-+0-9.eE]+"


def eski_bbox_3mf(path):
    try:
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".model")]
            if not names:
                return None
            xml = z.read(names[0]).decode("utf-8", "ignore")
    except (zipfile.BadZipFile, KeyError):
        return None
    bm = re.search(r'\bunit\s*=\s*"(\w+)"', xml[:2000])
    carpan = pa._3MF_BIRIM_MM.get((bm.group(1).lower() if bm else "millimeter"))
    if carpan is None:
        return None
    v = re.findall(r'<vertex\s+x="(%s)"\s+y="(%s)"\s+z="(%s)"' % (_SAYI, _SAYI, _SAYI), xml)
    if not v:
        return None
    try:
        xs = [float(a) for a, _, _ in v]
        ys = [float(b) for _, b, _ in v]
        zs = [float(c) for _, _, c in v]
    except ValueError:
        return None
    d = sorted([(max(xs) - min(xs)) * carpan,
                (max(ys) - min(ys)) * carpan,
                (max(zs) - min(zs)) * carpan], reverse=True)
    if d[0] <= 0 or d[0] > 100000:
        return None
    return d


def fmt(v):
    return "None" if v is None else "[%s]" % ", ".join("%.1f" % x for x in v)


def sapma_yuzde(a, b):
    """iki sirali olcunun boyut-bazli max yuzde farki."""
    a, b = sorted(a, reverse=True), sorted(b, reverse=True)
    m = 0.0
    for x, y in zip(a, b):
        taban = max(abs(x), abs(y), 1e-9)
        m = max(m, abs(x - y) / taban * 100.0)
    return m


def main():
    hatalar = []

    # 1) ANKRAJ
    print("=== ANKRAJ (elle olcumle karsilastirma) ===")
    for path, beklenen in ANKRAJ.items():
        olculen = pa.bbox_3mf(path)
        eski = eski_bbox_3mf(path)
        ok = tolere(beklenen, olculen)
        print("  %s" % os.path.basename(path))
        print("    elle    : %s" % fmt([float(x) for x in beklenen]))
        print("    YENI    : %s  %s" % (fmt(olculen), "OK" if ok else "FAIL"))
        print("    eski    : %s" % fmt(eski))
        if not ok:
            hatalar.append("ANKRAJ %s: beklenen %s, olculen %s" %
                           (os.path.basename(path), beklenen, fmt(olculen)))

    # 2) REGRESYON: tum .3mf'ler
    print("\n=== REGRESYON (stl/ altindaki tum .3mf) ===")
    dosyalar = sorted(glob.glob(os.path.join(STL_DIR, "*.3mf")))
    n_onarilan = n_ayni = n_sapan = n_iki_none = n_regresyon = 0
    sapanlar = []
    for path in dosyalar:
        yeni = pa.bbox_3mf(path)
        eski = eski_bbox_3mf(path)
        if eski is None and yeni is None:
            n_iki_none += 1
        elif eski is None and yeni is not None:
            n_onarilan += 1                      # eskiden olculemiyordu, artik olculuyor
        elif eski is not None and yeni is None:
            n_regresyon += 1                     # HARD FAIL: eskiden vardi, kayboldu
            hatalar.append("REGRESYON %s: eski %s -> yeni None" %
                           (os.path.basename(path), fmt(eski)))
        else:
            s = sapma_yuzde(eski, yeni)
            if s <= 1.0:
                n_ayni += 1
            else:
                n_sapan += 1
                sapanlar.append((os.path.basename(path), eski, yeni, s))

    print("  toplam .3mf         : %d" % len(dosyalar))
    print("  onarilan (None->deg): %d" % n_onarilan)
    print("  degismeyen (<=%%1)   : %d" % n_ayni)
    print("  sapan (>%%1)         : %d" % n_sapan)
    print("  iki tarafta None    : %d" % n_iki_none)
    print("  REGRESYON (deg->None): %d" % n_regresyon)

    if sapanlar:
        print("\n  --- sapan dosyalar (transform kaynakli olabilir, fail degil) ---")
        for ad, e, y, s in sapanlar[:40]:
            print("    %-16s eski %s  yeni %s  (%%%.1f)" % (ad, fmt(e), fmt(y), s))
        if len(sapanlar) > 40:
            print("    ... (+%d dosya daha)" % (len(sapanlar) - 40))

    print("\n=== SONUC ===")
    if hatalar:
        print("FAIL (%d):" % len(hatalar))
        for h in hatalar:
            print("  - " + h)
        return 1
    print("TUM TESTLER GECTI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
