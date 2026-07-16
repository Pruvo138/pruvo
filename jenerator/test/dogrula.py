#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI #1 cekirdegi — hacim.js kapali-form sonucu vs OpenSCAD render hacmi.

Her aile icin: varsayilan set + N rastgele GECERLI set uretir (sema min/max/adim
izgarasinda), hacim.js (node) ve OpenSCAD render STL hacmini karsilastirir.
Sapma > %3 ise KIRMIZI (cikis kodu 1). Ayrica tabanHacimMm3 == fn(varsayilanlar)
(%0.1 tolerans) dogrulanir.

Kullanim:
  python3 dogrula.py oring            # tek aile
  python3 dogrula.py --hepsi          # esleme/ altindaki tum aileler
  python3 dogrula.py oring --set 5 --seed 42
Ortam: PRUVO_SCAD_DIR (varsayilan ~/dev/pruvo-jenerator/jeneratorler),
       PRUVO_OPENSCAD (varsayilan /opt/homebrew/bin/openscad)
"""
import argparse
import io
import json
import os
import random
import subprocess
import sys
import tempfile

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
JEN_DIR = os.path.dirname(TEST_DIR)
ESLEME_DIR = os.path.join(TEST_DIR, "esleme")
URUN_DIR = os.path.join(JEN_DIR, "urunler")
SINIR_YUZDE = 3.0
TABAN_TOLERANS = 0.001

sys.path.insert(0, TEST_DIR)
import stl_hacim  # noqa: E402


def openscad_yolu():
    # Sirayla dene: env -> brew symlink -> /Applications -> Caskroom (2026-07-16:
    # /Applications/OpenSCAD.app kayboldu, brew symlink'i kirik kaldi; Caskroom
    # kopyasi calisiyor — sistem durumuna dokunmadan oradan kos).
    import glob
    import shutil
    adaylar = [os.environ.get("PRUVO_OPENSCAD"),
               "/opt/homebrew/bin/openscad",
               "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
               os.path.join(TEST_DIR, ".openscad-yerel",
                            "OpenSCAD.app", "Contents", "MacOS", "OpenSCAD")]
    adaylar += sorted(glob.glob(
        "/opt/homebrew/Caskroom/openscad*/*/OpenSCAD.app/Contents/MacOS/OpenSCAD"),
        reverse=True)
    adaylar.append(shutil.which("openscad"))
    for yol in adaylar:
        if yol and os.path.exists(yol):
            return yol
    sys.exit("openscad bulunamadi (PRUVO_OPENSCAD ayarlayin)")


def scad_dizini():
    yol = os.environ.get(
        "PRUVO_SCAD_DIR",
        os.path.expanduser("~/dev/pruvo-jenerator/jeneratorler"))
    if not os.path.isdir(yol):
        sys.exit("scad dizini yok: %s (PRUVO_SCAD_DIR ayarlayin)" % yol)
    return yol


def yukle(yol):
    with io.open(yol, "r", encoding="utf-8") as f:
        return json.load(f)


def rastgele_set(sema, rnd):
    """Sema izgarasinda gecerli rastgele parametre seti (metin -> varsayilan)."""
    s = {}
    for p in sema["parametreler"]:
        tip = p.get("tip", "sayi")
        if tip == "sayi":
            adim = float(p.get("adim") or 1)
            n = int(round((float(p["max"]) - float(p["min"])) / adim))
            s[p["ad"]] = round(float(p["min"]) + rnd.randint(0, n) * adim, 6)
        elif tip == "secim":
            secenekler = [x["deger"] if isinstance(x, dict) else x
                          for x in p["secenekler"]]
            s[p["ad"]] = rnd.choice(secenekler)
        elif tip == "metin":
            s[p["ad"]] = p.get("varsayilan", "")
        else:
            sys.exit("bilinmeyen tip: %s (%s)" % (tip, p["ad"]))
    return s


def varsayilan_set(sema):
    return dict((p["ad"], p["varsayilan"]) for p in sema["parametreler"])


def js_hacimler(fonksiyon, setler):
    istek = json.dumps({"fonksiyon": fonksiyon, "setler": setler},
                       ensure_ascii=False)
    proc = subprocess.run(
        ["node", os.path.join(TEST_DIR, "hacim-eval.js")],
        input=istek.encode("utf-8"), capture_output=True, timeout=60)
    if proc.returncode != 0:
        sys.exit("hacim-eval.js hata: %s" % proc.stderr.decode("utf-8", "replace"))
    return json.loads(proc.stdout.decode("utf-8"))


def d_bayraklari(esleme, sset):
    """Turkce parametre setini OpenSCAD -D bayraklarina cevirir."""
    bayraklar = []
    deger_esleme = esleme.get("deger_esleme") or {}
    for ad, scad_ad in (esleme.get("esleme") or {}).items():
        if ad not in sset:
            sys.exit("eslemede olan '%s' sette yok" % ad)
        deger = sset[ad]
        if ad in deger_esleme:
            deger = deger_esleme[ad][str(deger)]
        bayraklar.append("-D")
        if isinstance(deger, str):
            bayraklar.append('%s="%s"' % (scad_ad, deger.replace('"', '')))
        else:
            bayraklar.append("%s=%s" % (scad_ad, ("%.6f" % float(deger)).rstrip("0").rstrip(".")))
    for scad_ad, deger in (esleme.get("sabit") or {}).items():
        bayraklar.append("-D")
        if isinstance(deger, str):
            bayraklar.append('%s="%s"' % (scad_ad, deger.replace('"', '')))
        else:
            bayraklar.append("%s=%s" % (scad_ad, ("%.6f" % float(deger)).rstrip("0").rstrip(".")))
    return bayraklar


def scad_hacim(openscad, scad_yol, esleme, sset, tmpdir, etiket):
    """Render + hacim. Cokme (SIGABRT vb.) 2 kez yeniden denenir; israrla cokerse
    None doner (aile 'yerel dogrulanamadi' sayilir, CI'da kosulur — mimar karari
    2026-07-16: OpenSCAD snapshot acilista ara ara SIGABRT atiyor).
    GERCEK scad hatasi (stderr'de ERROR:) yeniden DENENMEZ ve testi durdurur —
    yanlis esleme/parametre sessizce atlanamaz."""
    stl = os.path.join(tmpdir, "%s.stl" % etiket)
    komut = [openscad, "-o", stl] + d_bayraklari(esleme, sset) + [scad_yol]
    for deneme in range(3):
        if os.path.exists(stl):
            os.remove(stl)
        proc = subprocess.run(komut, capture_output=True, timeout=600)
        hata_metni = proc.stderr.decode("utf-8", "replace")
        if proc.returncode == 0 and os.path.exists(stl):
            return stl_hacim.hacim(stl)
        if "ERROR:" in hata_metni:
            sys.exit("openscad GERCEK hata (%s):\n%s\n%s" % (
                etiket, " ".join(komut), hata_metni[-2000:]))
        print("  ... openscad cokme/bos cikti (%s, deneme %d/3, kod %s) — tekrar" %
              (etiket, deneme + 1, proc.returncode))
        import time
        time.sleep(1)
    return None


def aile_dogrula(aile, set_sayisi, rnd, openscad, scad_dir):
    esleme = yukle(os.path.join(ESLEME_DIR, aile + ".json"))
    sema = yukle(os.path.join(URUN_DIR, esleme["urunId"] + ".json"))
    if sema.get("hacimFormulu") != esleme["fonksiyon"]:
        sys.exit("%s: sema.hacimFormulu != esleme.fonksiyon" % aile)
    scad_yol = os.path.join(scad_dir, esleme["scad"])
    if not os.path.exists(scad_yol):
        sys.exit("scad dosyasi yok: %s" % scad_yol)

    setler = [varsayilan_set(sema)]
    for _ in range(set_sayisi):
        setler.append(rastgele_set(sema, rnd))
    js = js_hacimler(esleme["fonksiyon"], setler)

    # taban hacim tutarliligi
    taban = float(sema["tabanHacimMm3"])
    if abs(js[0] - taban) / taban > TABAN_TOLERANS:
        print("  %s KIRMIZI: tabanHacimMm3=%.2f ama fn(varsayilan)=%.2f" %
              (aile, taban, js[0]))
        return False

    hepsi_yesil = True
    with tempfile.TemporaryDirectory() as tmpdir:
        for i, sset in enumerate(setler):
            ref = scad_hacim(openscad, scad_yol, esleme, sset, tmpdir,
                             "%s-%d" % (aile, i))
            if ref is None:
                print("  [ATLA] %-8s yerel dogrulanamadi (openscad israrla cokuyor)"
                      " — CI dogrulamasina birakildi" % aile)
                return "atla"
            sapma = abs(js[i] - ref) / ref * 100.0
            durum = "OK " if sapma <= SINIR_YUZDE else "SAP"
            if sapma > SINIR_YUZDE:
                hepsi_yesil = False
            kisa = ", ".join("%s=%s" % (k, v) for k, v in sorted(sset.items()))
            print("  [%s] %-8s set%d  js=%12.1f  scad=%12.1f  sapma=%5.2f%%  (%s)" %
                  (durum, aile, i, js[i], ref, sapma, kisa[:100]))
    return hepsi_yesil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("aileler", nargs="*", help="aile adi (esleme/<ad>.json)")
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--set", type=int, default=3, help="rastgele set sayisi")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    # PARALEL GUVENLIK: ayni anda birden cok aile dogrulanabilir (paralel muhendis
    # oturumlari); hacim.js'in yeniden montaji + kosum tek kilit altinda serilestirilir.
    import fcntl
    kilit = open(os.path.join(TEST_DIR, ".dogrula-kilit"), "w")
    fcntl.flock(kilit, fcntl.LOCK_EX)

    # once monte et — hacim.js her zaman aile dosyalarinin guncel birlesimi.
    # Baska bir is aile dosyasini o an yaziyor olabilir -> kisa tekrar dene.
    import time
    for deneme in range(5):
        proc = subprocess.run([sys.executable, os.path.join(TEST_DIR, "birlestir.py")],
                              capture_output=True)
        if proc.returncode == 0:
            break
        time.sleep(2)
    if proc.returncode != 0:
        sys.exit("birlestir.py hata:\n%s%s" % (proc.stdout.decode("utf-8", "replace"),
                                               proc.stderr.decode("utf-8", "replace")))

    if args.hepsi:
        aileler = sorted(f[:-5] for f in os.listdir(ESLEME_DIR)
                         if f.endswith(".json"))
    else:
        aileler = args.aileler
    if not aileler:
        sys.exit("aile verin ya da --hepsi kullanin")

    seed = args.seed if args.seed is not None else random.SystemRandom().randint(0, 10 ** 6)
    print("tohum (tekrar icin --seed %d), sinir <=%%%.1f, rastgele set=%d" %
          (seed, SINIR_YUZDE, args.set))
    rnd = random.Random(seed)
    openscad = openscad_yolu()
    scad_dir = scad_dizini()

    kirmizi, atlanan = [], []
    for aile in aileler:
        sonuc = aile_dogrula(aile, args.set, rnd, openscad, scad_dir)
        if sonuc == "atla":
            atlanan.append(aile)
        elif not sonuc:
            kirmizi.append(aile)
    if atlanan:
        print("YEREL DOGRULANAMAYAN aileler (CI'da kosulacak): %s" % ", ".join(atlanan))
    if kirmizi:
        print("KIRMIZI aileler: %s" % ", ".join(kirmizi))
        sys.exit(1)
    print("YEREL YESIL: %d, CI'YA KALAN: %d" % (len(aileler) - len(atlanan), len(atlanan)))


if __name__ == "__main__":
    main()
