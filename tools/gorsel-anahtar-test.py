#!/usr/bin/env python3
"""KABUL/REGRESYON TESTI — R2 gorsel anahtari ile urun basligini AYIRIR.

Kok neden (2026-07-18, KraL): printables-ekle.py / urun-ekle.py / cgt-ekle.py
process_one()'da R2 gorsel anahtarini Codex'in urettigi BASLIK-SLUG'indan (uid)
hesaplayip merge_safe()'ten ONCE, paralel thread'de yukluyordu. Iki farkli kaynak
urunu ayni Turkce basligi uretirse (or. yedi ayri "Peugeot 206 Vites Topuzu"),
ikisi de AYNI R2 anahtarina (`urunler/<uid>-N.jpg`) yuklenip birbirini eziyor;
JSON id'leri farkli olsa da (X ve X-<pid>) gorseller[] AYNI URL'yi gosteriyordu.
Canlida 126 URL, 143 urun etkilenmisti.

Bu test her uc ekleyicinin process_one'ini I/O sinirlarini stub'layarak surer:
AYNI Codex ciktisi (ayni baslik) + FARKLI kaynak id ile iki urun uretir, uretilen
gorseller[] URL'lerinin ORTAK ELEMANI OLMADIGINI dogrular. Kok neden geri gelirse
(anahtar yine basliktan turerse) test kirmizi yanar.

Calistir:  python3 tools/gorsel-anahtar-test.py   (cikis 0 = gecti, 1 = kaldi)
"""
import importlib.util
import json
import os
import sys
import tempfile

DIR = os.path.dirname(os.path.abspath(__file__))  # bu testin (dolayisiyla ekleyicilerin) dizini
FAILS = []


def _load(fname, modname):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(DIR, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noop_run(*a, **k):
    class _R:
        stdout = ""
        stderr = ""
        returncode = 0
    return _R()


def _write_jpgs(d, names):
    os.makedirs(d, exist_ok=True)
    for n in names:
        with open(os.path.join(d, n), "wb") as f:
            f.write(b"\xff\xd8\xff\xe0JFIFtest" + b"\x00" * 64)  # sahte kucuk jpg


ONERI = {"baslik": "Peugeot 206 Vites Topuzu", "kategori": "Otomobil",
         "marka": ["Peugeot"], "aciklama": "test", "fiyat_oneri": "200 TL",
         "sec_gorseller": ["g1.jpg", "g2.jpg"]}


def _keycap():
    """sips_upload yerine gecer: yuklenen anahtari kaydeder, sahte URL doner."""
    kaydedilen = []

    def cap(local_jpg, key):
        kaydedilen.append(key)
        return "https://media.pruvo3d.com/" + key + ".jpg"
    return cap, kaydedilen


def _urls(res):
    return set((res or {}).get("urun", {}).get("gorseller", []) or [])


def _assert_disjoint(ad, a, b):
    ortak = a & b
    if ortak:
        FAILS.append("%s: iki urun AYNI gorsel URL'yi paylasti -> %s" % (ad, sorted(ortak)))
        print("  ✘ %-12s CAKISMA: %s" % (ad, sorted(ortak)))
    elif not a or not b:
        FAILS.append("%s: gorsel URL uretilemedi (a=%s b=%s)" % (ad, a, b))
        print("  ✘ %-12s gorsel yok (a=%d b=%d)" % (ad, len(a), len(b)))
    else:
        print("  ✔ %-12s ayrik anahtar: %s | %s" % (ad, sorted(a), sorted(b)))


def test_printables():
    m = _load("printables-ekle.py", "pr_ekle_test")
    tmp = tempfile.mkdtemp(prefix="gk_pr_")
    m.CACHE = tmp
    m.subprocess.run = _noop_run
    cap, kaydedilen = _keycap()
    m.sips_upload = cap

    def fake_prep(pid, key):
        d = os.path.join(m.CACHE, key)
        _write_jpgs(d, ["g1.jpg", "g2.jpg"])
        json.dump(ONERI, open(os.path.join(d, "oneri.json"), "w"), ensure_ascii=False)
        meta = {"id": key, "baslik": ONERI["baslik"], "tasarimci": "x", "lisans": "CC BY",
                "olcu_mm": None, "stl_adet": 1, "gorseller": ["g1.jpg", "g2.jpg"],
                "baski": "", "abbr": "", "slug": "s", "pid": pid}
        return meta, "", ""
    m.prep = fake_prep

    a = _urls(m.process_one("2513501"))
    b = _urls(m.process_one("5401065"))
    _assert_disjoint("printables", a, b)


def test_thingiverse():
    m = _load("urun-ekle.py", "th_ekle_test")
    tmp = tempfile.mkdtemp(prefix="gk_th_")
    m.IMGROOT = tmp
    m.subprocess.run = _noop_run
    cap, kaydedilen = _keycap()
    m.sips_upload = cap

    def setup(tid):
        d = os.path.join(m.IMGROOT, tid)
        _write_jpgs(d, ["g1.jpg", "g2.jpg"])
        json.dump(ONERI, open(os.path.join(d, "oneri.json"), "w"), ensure_ascii=False)
        json.dump({"id": tid, "baslik": ONERI["baslik"], "tasarimci": "y",
                   "lisans": "Creative Commons - Attribution", "olcu_mm": None,
                   "stl_adet": 1, "baski": ""},
                  open(os.path.join(d, "meta.json"), "w"), ensure_ascii=False)
    setup("2513501")
    setup("5401065")
    a = _urls(m.process_one("2513501"))
    b = _urls(m.process_one("5401065"))
    _assert_disjoint("thingiverse", a, b)


def test_cgt():
    m = _load("cgt-ekle.py", "cgt_ekle_test")
    tmp = tempfile.mkdtemp(prefix="gk_cgt_")
    m.IMGROOT = tmp
    m.subprocess.run = _noop_run
    cap, kaydedilen = _keycap()
    m.sips_upload = cap

    def fake_urun_verisi(url, author=None):
        itemid = url.rsplit("/", 1)[-1]
        return {"itemid": itemid, "baslik": ONERI["baslik"], "usd": "10", "disc": 0,
                "galeri": ["u1", "u2"], "link": url}
    m.urun_verisi = fake_urun_verisi

    def fake_indir(itemid, galeri, n=6):
        d = os.path.join(m.IMGROOT, "cgt-" + itemid)
        _write_jpgs(d, ["g1.jpg", "g2.jpg"])
        json.dump(ONERI, open(os.path.join(d, "oneri.json"), "w"), ensure_ascii=False)
        return d, [os.path.join(d, "g1.jpg"), os.path.join(d, "g2.jpg")]
    m.indir_gorseller = fake_indir

    a = _urls(m.process_one("https://x/models/7124950", None))
    b = _urls(m.process_one("https://x/models/6267929", None))
    _assert_disjoint("cgtrader", a, b)


def main():
    print("R2 gorsel anahtari <-> baslik AYRIMI regresyon testi")
    print("-" * 60)
    test_printables()
    test_thingiverse()
    test_cgt()
    print("-" * 60)
    if FAILS:
        print("KALDI (%d):" % len(FAILS))
        for f in FAILS:
            print("  -", f)
        return 1
    print("GECTI: 3/3 ekleyici — ayni baslik farkli kaynak -> ayrik gorsel anahtari.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
