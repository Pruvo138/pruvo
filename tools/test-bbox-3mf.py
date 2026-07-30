#!/usr/bin/env python3
"""bbox_3mf() kabul testi — cok-.model (Bambu-Studio) 3MF arsivlerinde dogru olcum.

`python3 tools/test-bbox-3mf.py` (argumansiz). Basarisizlikta sifir-olmayan cikis kodu.

Neyi dogruluyor:
  1. ANKRAJ (fikstur): tools/fikstur/3mf/ altindaki UC sentetik arsiv. Her biri ayri bir
     olcum riskini capalar — cok-.model + transform zinciri, tek-.model duz olcum, ve
     birim (inch) donusumu. Beklenen degerler ELLE HESAPLANABILIR (kutu koseleri +
     matris carpimi), dosyalar ~1 KB ve DEPODA.
  2. AYIRT EDICILIK: cok-model fiksturunde ESKI mantik (ilk .model + regex) None donmek,
     YENI mantik dogru olcuyu vermek ZORUNDA. Onarilan hata sinifi tam olarak budur;
     bu iddia olmadan test "iki mantik da ayni" diyen bir totolojiye duserdi.
  3. REGRESYON (kosullu): stl/ altindaki TUM .3mf dosyalari eski ve yeni mantikla olculur.
     Eski fonksiyonun olcebildigi dosyalarda sonuc DEGISMEMELI; eski None donup yeni olcen
     dosyalar "onarilan" sayilir. Eski deger verip yeni None donmek = HARD FAIL.
     stl/ DEPOYA GIRMEZ (gitignore) -> yoksa bolum ACIKCA "ATLANDI" raporlanir (sessiz
     atlama YOK); ankraj bolumu her ortamda kosar.

🔴 30 TEM — NEDEN DEGISTI (olculdu): ankrajlar GERCEK urun dosyalariydi
(stl/pr1173083.3mf, stl/pr912419.3mf) ve `stl/` gitignore'da. Bu makinede de, CI'da da
YOKLAR -> test 0,1 s'de FileNotFoundError ile PATLIYOR, HICBIR iddia kosmuyordu. Ustelik
ci-kapsam izin listesindeki gerekcesi R_YAVAS (">30 s") diyordu; olculen 0,1 s'lik
cokustu, yani muafiyet YALAN bir gerekceyle ayakta duruyordu. Ankraj artik depoda
(uretici: tools/fikstur/3mf-fikstur-uret.py) ve test CI'da BLOKLAYICI kosar.
"""
import importlib.util, os, re, struct, sys, zipfile, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# MUTLAK YOL YOK: eskiden "/Users/okan/dev/pruvo/stl" sabitti -> worktree'de de CI'da da
# yanlis yeri gosteriyordu. Artik betigin KENDI konumundan turetilir.
STL_DIR = os.path.join(ROOT, "stl")
FIKSTUR_DIR = os.path.join(HERE, "fikstur", "3mf")

# --- test edilen modulu yukle (dosya adinda '-' var, normal import olmaz) ---
_spec = importlib.util.spec_from_file_location("printables_api",
                                               os.path.join(HERE, "printables-api.py"))
pa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pa)

# --- ANKRAJ: elle hesaplanmis degerler (buyukten kucuge, mm) ---
# Her giris: dosya -> (beklenen_olcu, eski_mantik_None_mu, aciklama)
ANKRAJ = {
    "cok-model-transform.3mf": (
        [60, 30, 20], True,
        "kok .model montaj (vertex YOK) + 3D/Objects/*.model geometri; "
        "component olcek 2x (X) o item olcek 3x (Y) -> 10x20x30 kutu 20x60x30 olur"),
    "tek-model-duz.3mf": (
        [47, 40, 31], False,
        "tek .model, transform yok -> eski ve yeni mantik AYNI sonucu vermeli"),
    "birim-inch.3mf": (
        [101.6, 50.8, 25.4], False,
        "unit=inch -> 4x2x1 inc kutu mm'ye cevrilmeli (carpan dusserse 25,4 kat sapar)"),
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

    # 1) ANKRAJ — depodaki sentetik fiksturler (her ortamda kosar, FAIL-CLOSED)
    print("=== ANKRAJ (tools/fikstur/3mf — elle hesaplanmis olcu) ===")
    for ad, (beklenen, eski_none_mu, aciklama) in sorted(ANKRAJ.items()):
        path = os.path.join(FIKSTUR_DIR, ad)
        if not os.path.exists(path):
            # FAIL-CLOSED: fikstur yoksa test SESSIZCE atlanmaz, KIRMIZI yanar.
            # (Tam bu sinif hata testi aylarca olu tuttu: ankraj dosyasi yoktu.)
            print("  %s\n    FIKSTUR YOK -> %s" % (ad, path))
            hatalar.append("ANKRAJ FIKSTURU YOK: %s (uret: python3 "
                           "tools/fikstur/3mf-fikstur-uret.py)" % path)
            continue
        olculen = pa.bbox_3mf(path)
        eski = eski_bbox_3mf(path)
        ok = tolere(beklenen, olculen)
        print("  %s  — %s" % (ad, aciklama))
        print("    beklenen: %s" % fmt([float(x) for x in beklenen]))
        print("    YENI    : %s  %s" % (fmt(olculen), "OK" if ok else "FAIL"))
        print("    eski    : %s" % fmt(eski))
        if not ok:
            hatalar.append("ANKRAJ %s: beklenen %s, olculen %s" % (ad, beklenen, fmt(olculen)))
        # AYIRT EDICILIK: eski mantigin bu fiksturde ne yapmasi gerektigi de IDDIADIR.
        # Olmazsa test "iki mantik da ayni" totolojisine duser ve onarilan hata sinifini
        # (cok-.model arsivinde None) hic olcmez.
        if eski_none_mu and eski is not None:
            hatalar.append("AYIRT EDICILIK %s: ESKI mantik None DONMELIYDI, %s dondu -> "
                           "fikstur artik cok-.model sinifini temsil etmiyor" % (ad, fmt(eski)))
        if (not eski_none_mu) and eski is None:
            hatalar.append("AYIRT EDICILIK %s: ESKI mantik olcebilmeliydi, None dondu -> "
                           "fikstur bozulmus" % ad)
        if (not eski_none_mu) and eski is not None and not tolere(beklenen, eski):
            hatalar.append("AYIRT EDICILIK %s: eski mantik %s dedi, beklenen %s "
                           "(bu fiksturde iki mantik AYNI olmali)" % (ad, fmt(eski), beklenen))

    # 2) REGRESYON: tum .3mf'ler — stl/ DEPOYA GIRMEZ (gitignore), yoksa ACIKCA atlanir
    print("\n=== REGRESYON (stl/ altindaki tum .3mf) ===")
    if not os.path.isdir(STL_DIR):
        print("  ⚪ ATLANDI: %s yok (stl/ gitignore'da — CI fresh checkout'ta beklenen hal)."
              % STL_DIR)
        print("     Ankraj bolumu bu ortamda da KOSTU; regresyon taramasi yerel/STL "
              "yedegi olan makinede anlamlidir.")
        dosyalar = []
    else:
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
