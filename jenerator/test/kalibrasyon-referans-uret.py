#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""kalibrasyon-senkron.js referans fixture'ini uretir (mimar/muhendis araci).

Konektor + braket + disli (olcuye gore uretec v2 aileleri) + adaptor + kutu +
kavanoz (yeni sari aileler 1. dalga, 2026-07-17) icin sema-gecerli
deterministik parametre setlerini GERCEK openscad render'iyla olcer ve
kalibrasyon-referans.json'a yazar. Referanslar dondurulur: test (node
kalibrasyon-senkron.js) openscad'siz her yerde kosar.

Kullanim: python3 jenerator/test/kalibrasyon-referans-uret.py
Ortam: PRUVO_SCAD_DIR (vars. ~/dev/pruvo-jenerator/jeneratorler), PRUVO_OPENSCAD
"""
import io
import json
import os
import random
import sys
import tempfile

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TEST_DIR)
import dogrula     # noqa: E402
import stl_hacim   # noqa: E402

AILELER = ["konektor", "braket", "disli", "adaptor", "kutu", "kavanoz"]
TOHUM = 42
RASTGELE_SET = 6


def yukle(yol):
    with io.open(yol, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    openscad = dogrula.openscad_yolu()
    scad_dir = dogrula.scad_dizini()
    cikti = {"_not": ("Referans hacimler gercek OpenSCAD STL olcumu; "
                      "uretim: kalibrasyon-referans-uret.py, tohum=%d" % TOHUM),
             "aileler": {}}
    for aile in AILELER:
        esleme = yukle(os.path.join(TEST_DIR, "esleme", aile + ".json"))
        sema = yukle(os.path.join(TEST_DIR, "..", "urunler",
                                  esleme["urunId"] + ".json"))
        rnd = random.Random(TOHUM)
        setler = [dogrula.varsayilan_set(sema)]
        # secim parametrelerinin HER degeri en az bir sette gecsin
        # (disli tipleri gibi dallanan geometriler tek rastgeleye kalmasin)
        for p in sema["parametreler"]:
            if p.get("tip") == "secim":
                for secenek in p["secenekler"]:
                    deger = secenek["deger"] if isinstance(secenek, dict) \
                        else secenek
                    s = dogrula.rastgele_set(sema, rnd)
                    s[p["ad"]] = deger
                    setler.append(s)
        for _ in range(RASTGELE_SET):
            setler.append(dogrula.rastgele_set(sema, rnd))
        kayitlar = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for i, sset in enumerate(setler):
                ref = dogrula.scad_hacim(
                    openscad, os.path.join(scad_dir, esleme["scad"]),
                    esleme, sset, tmpdir, "%s-%d" % (aile, i))
                if ref is None:
                    sys.exit("%s set%d: openscad israrla cokuyor" % (aile, i))
                kayitlar.append({"parametreler": sset, "referansMm3": ref})
                print("  %s set%-2d referans=%.1f mm3" % (aile, i, ref))
        cikti["aileler"][aile] = {
            "fonksiyon": esleme["fonksiyon"],
            "urunId": esleme["urunId"],
            "setler": kayitlar,
        }
    yol = os.path.join(TEST_DIR, "kalibrasyon-referans.json")
    with io.open(yol, "w", encoding="utf-8") as f:
        json.dump(cikti, f, ensure_ascii=False, indent=1)
    print("yazildi: %s" % yol)


if __name__ == "__main__":
    main()
