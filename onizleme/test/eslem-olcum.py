#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FAZ D — aile eslem kalibrasyon olcumu (4d-benzeri, onizleme kod yoluyla).

Her aile icin: sema izgarasindan N rastgele GECERLI set x M tohum uretir,
-D bayraklarini SERVER.PY'NIN KENDI d_bayraklari fonksiyonuyla (onizleme
derleme yolunun birebir aynisi) kurar, gercek openscad render STL hacmini
jenerator/hacim.js kapali-formuyla karsilastirir. Hedef <= %3.

Bu arac ONIZLEME_AILELER'e alinmamis aileleri OLCMEK icindir (yayin karari
ayri): sapmasi buyuk cikan aile sessizce eklenmez, mimar tablosuna yazilir.

Kullanim:
  python3 onizleme/test/eslem-olcum.py <aile> [<aile>...] [--set 5]
  python3 onizleme/test/eslem-olcum.py --hepsi   # paketteki tum aileler
  (--tohumlar 20260716,20260717 varsayilan; --json <yol> ozet doker)
Gerekli: eslem-ozel.json (gitignore'lu) + uyelik/jenerator .scad kaynaklari.
"""
import argparse
import importlib.util
import io
import json
import os
import random
import subprocess
import sys
import tempfile

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(TEST_DIR))
JEN_TEST = os.path.join(REPO, "jenerator", "test")
SINIR_YUZDE = 3.0

sys.path.insert(0, JEN_TEST)
import stl_hacim  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "onizleme_server", os.path.join(REPO, "onizleme", "derleyici", "server.py"))
server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(server)


def openscad_yolu():
    sys.path.insert(0, JEN_TEST)
    import dogrula
    return dogrula.openscad_yolu()


def paket_topla():
    hedef = tempfile.mkdtemp(prefix="eslem-olcum-paket-")
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO, "tools", "onizleme-paket-yukle.py"),
         "--yerel", hedef], capture_output=True)
    if proc.returncode != 0:
        sys.exit("paket toplanamadi:\n%s%s" %
                 (proc.stdout.decode("utf-8", "replace"),
                  proc.stderr.decode("utf-8", "replace")))
    return hedef


def sema_yukle(aile):
    yol = os.path.join(REPO, "jenerator", "urunler", aile + ".json")
    with io.open(yol, encoding="utf-8") as f:
        return json.load(f)


def rastgele_set(sema, rnd):
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
        else:
            s[p["ad"]] = p.get("varsayilan", "")
    return s


def varsayilan_set(sema):
    return dict((p["ad"], p["varsayilan"]) for p in sema["parametreler"])


def js_hacimler(fonksiyon, setler):
    istek = json.dumps({"fonksiyon": fonksiyon, "setler": setler},
                       ensure_ascii=False)
    proc = subprocess.run(["node", os.path.join(JEN_TEST, "hacim-eval.js")],
                          input=istek.encode("utf-8"), capture_output=True,
                          timeout=60)
    if proc.returncode != 0:
        sys.exit("hacim-eval.js: %s" % proc.stderr.decode("utf-8", "replace"))
    return json.loads(proc.stdout.decode("utf-8"))


def scad_yolu_sec(eslem_aile, sset, paket):
    """Varyant scad override'i destekler (cift-uretecli aileler: vida, yay)."""
    scad = eslem_aile.get("scad")
    secici = eslem_aile.get("secici")
    if secici:
        v = sset.get(secici)
        varyant = (eslem_aile.get("varyantlar") or {}).get(v) or {}
        scad = varyant.get("scad", scad)
    return os.path.join(paket, scad)


def aile_olc(aile, eslem, paket, openscad, set_sayisi, tohumlar):
    sema = sema_yukle(aile)
    eslem_aile = eslem[aile]
    setler = [varsayilan_set(sema)]
    for tohum in tohumlar:
        rnd = random.Random(tohum)
        for _ in range(set_sayisi):
            setler.append(rastgele_set(sema, rnd))
    js = js_hacimler(sema["hacimFormulu"], setler)
    sonuc = {"aile": aile, "set": len(setler), "enKotu": 0.0,
             "kirmizi": 0, "hata": 0, "ret": 0, "satirlar": []}
    with tempfile.TemporaryDirectory() as tmp:
        for i, sset in enumerate(setler):
            bayraklar, sebep = server.d_bayraklari(eslem_aile, sset)
            if bayraklar is None:
                # Eslem BILEREK reddediyor = uretim motorunda karsiligi olmayan
                # sema bolgesi (or. yarim capli vida, ucgen cetvel) -> KISMI.
                sonuc["ret"] += 1
                print("  [RET ] %-10s set%-2d eslem kapsami disi: %s (%s)" %
                      (aile, i, sebep, json.dumps(sset, ensure_ascii=False)[:90]))
                continue
            stl = os.path.join(tmp, "%s-%d.stl" % (aile, i))
            komut = [openscad, "-o", stl, "--export-format", "binstl"] + \
                bayraklar + [scad_yolu_sec(eslem_aile, sset, paket)]
            proc = subprocess.run(komut, capture_output=True, timeout=600)
            if proc.returncode != 0 or not os.path.exists(stl):
                sonuc["hata"] += 1
                print("  [HATA] %-10s set%-2d derleme: %s (%s)" %
                      (aile, i, proc.stderr.decode("utf-8", "replace")
                       .strip().splitlines()[-1][:120] if proc.stderr else "?",
                       json.dumps(sset, ensure_ascii=False)[:90]))
                continue
            ref = stl_hacim.hacim(stl)
            sapma = abs(js[i] - ref) / ref * 100.0
            sonuc["enKotu"] = max(sonuc["enKotu"], sapma)
            if sapma > SINIR_YUZDE:
                sonuc["kirmizi"] += 1
            durum = "OK " if sapma <= SINIR_YUZDE else "SAP"
            kisa = ", ".join("%s=%s" % (k, v) for k, v in sorted(sset.items())
                             if not isinstance(v, str) or len(str(v)) < 20)
            print("  [%s] %-10s set%-2d js=%11.1f stl=%11.1f sapma=%5.2f%%  (%s)"
                  % (durum, aile, i, js[i], ref, sapma, kisa[:110]))
            sonuc["satirlar"].append({"sapma": round(sapma, 2)})
    return sonuc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("aileler", nargs="*")
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--set", type=int, default=5)
    ap.add_argument("--tohumlar", default="20260716,20260717")
    ap.add_argument("--json", help="ozeti bu dosyaya JSON dok")
    args = ap.parse_args()
    tohumlar = [int(x) for x in args.tohumlar.split(",")]

    paket = paket_topla()
    eslem = server.eslem_yukle(paket)
    aileler = sorted(eslem.keys()) if args.hepsi else args.aileler
    if not aileler:
        sys.exit("aile verin ya da --hepsi")
    openscad = openscad_yolu()
    print("olcum: %d aile, %d set x %d tohum + varsayilan, sinir <=%%%.1f" %
          (len(aileler), args.set, len(tohumlar), SINIR_YUZDE))

    ozet = []
    for aile in aileler:
        if aile not in eslem:
            print("  [YOK ] %s eslem paketinde yok" % aile)
            ozet.append({"aile": aile, "durum": "eslem-yok"})
            continue
        s = aile_olc(aile, eslem, paket, openscad, args.set, tohumlar)
        if s["kirmizi"] or s["hata"]:
            s["durum"] = "kirmizi"
        elif s["ret"]:
            s["durum"] = "kismi"  # olculenler yesil ama sema bolgesi eksik
        else:
            s["durum"] = "yesil"
        print("  --> %-10s en kotu %%%.2f, sinir ustu %d/%d, derleme hatasi %d, kapsam disi %d"
              % (aile, s["enKotu"], s["kirmizi"], s["set"], s["hata"], s["ret"]))
        ozet.append(s)
    if args.json:
        with io.open(args.json, "w", encoding="utf-8") as f:
            json.dump(ozet, f, ensure_ascii=False, indent=1)
    kirmizi = [s for s in ozet if s.get("durum") != "yesil"]
    print("\nOZET: %d aile yesil, %d aile sinir disi/eksik" %
          (len(ozet) - len(kirmizi), len(kirmizi)))
    sys.exit(1 if kirmizi else 0)


if __name__ == "__main__":
    main()
