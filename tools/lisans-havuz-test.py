#!/usr/bin/env python3
"""KABUL TESTI — aktif arama adaptorleri satilabilir lisanslari AYRI sorgular.

Kullanici arayuzundeki desen: her lisans secenegi ayri arama havuzudur. Tek bir genel
"acik lisans" sorgusunun ilk sayfalari diger lisanslari temsil etmez. Bu test:
  * Thingiverse / Printables / MakerWorld'de her beyaz-liste lisansinin ayri cagrildigini,
  * NC lisansinin hic sorgulanmadigini,
  * lisans havuzlarinda yinelenen ayni model kimliginin tek kez donduruldugunu
ag kullanmadan kanitlar.
"""
import contextlib
import importlib.util
import io
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))


def yukle(dosya, ad):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(HERE, dosya))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def idler(cikti):
    lines = cikti.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("IDLER"):
            return lines[i + 1].split() if i + 1 < len(lines) else []
    return []


def kos(mod):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        mod.main("Toyota", 999, tam_kelime=False) if "tam_kelime" in mod.main.__code__.co_varnames else mod.main("Toyota", 999)
    return idler(buf.getvalue())


def thingiverse():
    mod = yukle("thing-ara.py", "lisans_thing")
    cagrilar = []

    def api(url):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        lic = q["license"][0]
        page = int(q["page"][0])
        cagrilar.append((lic, page))
        if page > 1:
            return {"hits": []}
        sira = mod.SATILABILIR_LISANSLAR.index(lic)
        return {"hits": [
            {"id": 91000000, "name": "Toyota shared bracket", "like_count": 0, "make_count": 0},
            {"id": 91100000 + sira, "name": "Toyota %s bracket" % lic, "like_count": sira, "make_count": 0},
        ]}

    mod.api = api
    mod.mevcut_thing_idleri = lambda: set()
    sonuc = kos(mod)
    ilk = [lic for lic, page in cagrilar if page == 1]
    assert ilk == list(mod.SATILABILIR_LISANSLAR), ilk
    assert not any("nc" in lic for lic in ilk), ilk
    assert len(sonuc) == len(mod.SATILABILIR_LISANSLAR) + 1, sonuc
    assert len(sonuc) == len(set(sonuc)), sonuc


def printables():
    mod = yukle("printables-ara.py", "lisans_printables")
    cagrilar = []

    def search(term, limit=30, offset=0, ordering="popular", licenses=None):
        lic = str(licenses[0])
        cagrilar.append((lic, offset))
        if offset:
            return {"totalCount": 2, "items": []}
        sira = [x[0] for x in mod.SATILABILIR_LISANSLAR].index(lic)
        abbr = mod.SATILABILIR_LISANSLAR[sira][1]
        return {"totalCount": 2, "items": [
            {"id": 92000000, "name": "Toyota shared bracket", "license": {"abbreviation": abbr}},
            {"id": 92100000 + sira, "name": "Toyota bracket %s" % lic,
             "license": {"abbreviation": abbr}, "likesCount": sira, "downloadCount": 0},
        ]}

    mod.pr.search = search
    mod.mevcut_idler = lambda: set()
    sonuc = kos(mod)
    ilk = [lic for lic, offset in cagrilar if offset == 0]
    beklenen = [x[0] for x in mod.SATILABILIR_LISANSLAR]
    assert ilk == beklenen, ilk
    assert not any(x in {"3", "4", "6"} for x in ilk), ilk
    assert len(sonuc) == len(beklenen) + 1, sonuc
    assert len(sonuc) == len(set(sonuc)), sonuc


def makerworld():
    mod = yukle("makerworld-ara.py", "lisans_makerworld")
    cagrilar = []

    def search(term, limit=40, offset=0, licenses=None):
        cagrilar.append((licenses, offset))
        if offset:
            return {"total": 2, "hits": []}
        sira = mod.SATILABILIR_LISANSLAR.index(licenses)
        return {"total": 2, "hits": [
            {"id": 93000000, "title": "Toyota shared bracket", "tags": ["Toyota"],
             "license": licenses},
            {"id": 93100000 + sira, "title": "Toyota bracket %s" % licenses,
             "tags": ["Toyota"], "license": licenses, "likeCount": sira, "downloadCount": 0},
        ]}

    mod.mw.search = search
    mod.mevcut_idler = lambda: set()
    sonuc = kos(mod)
    ilk = [lic for lic, offset in cagrilar if offset == 0]
    assert ilk == list(mod.SATILABILIR_LISANSLAR), ilk
    assert not any("NC" in lic for lic in ilk), ilk
    assert len(sonuc) == len(mod.SATILABILIR_LISANSLAR) + 1, sonuc
    assert len(sonuc) == len(set(sonuc)), sonuc


def main():
    testler = [("Thingiverse", thingiverse), ("Printables", printables), ("MakerWorld", makerworld)]
    for ad, test in testler:
        try:
            test()
            print("  ok  %s: lisanslar ayri, NC yok, kimlikler tekil" % ad)
        except Exception as e:
            print("HATA %s: %s" % (ad, e))
            return 1
    print("3/3 GECTI — aktif platformlar kullanicinin ayri-lisans arama yontemini uyguluyor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
