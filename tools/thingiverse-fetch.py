#!/usr/bin/env python3
"""Thingiverse'ten bir modelin ilk STL'ini indirir, stl/<urun_id>.stl olarak saklar
ve sinir kutusu olcusunu (mm) yazdirir.

Token repo kokundeki gitignore'lu .thingiverse-token dosyasindan okunur.

Kullanim:
    python3 tools/thingiverse-fetch.py <thing_id> <urun_id>
Cikti (son satir, ayristirilabilir):
    DIMS <urun_id> <X> <Y> <Z>   (buyukten kucuge, tam sayi mm)
"""
import sys, os, json, urllib.request, struct

ROOT = os.path.join(os.path.dirname(__file__), "..")
TOKEN = open(os.path.join(ROOT, ".thingiverse-token")).read().strip()
STL_DIR = os.path.join(ROOT, "stl")


def api(url):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOKEN,
                                               "User-Agent": "pruvo/1.0"})
    with urllib.request.urlopen(req) as r:
        return r.read()


def bbox(path):
    with open(path, "rb") as f:
        head = f.read(5)
    xs = ys = zs = None
    if head[:5].lower() == b"solid":
        xs, ys, zs = [], [], []
        with open(path, "r", errors="ignore") as f:
            for line in f:
                p = line.split()
                if len(p) == 4 and p[0] == "vertex":
                    try:
                        xs.append(float(p[1])); ys.append(float(p[2])); zs.append(float(p[3]))
                    except ValueError:
                        pass
    if not xs:  # ikili
        xs, ys, zs = [], [], []
        with open(path, "rb") as f:
            f.read(80)
            (n,) = struct.unpack("<I", f.read(4))
            for _ in range(n):
                d = f.read(50)
                if len(d) < 50:
                    break
                v = struct.unpack("<12f", d[:48])
                for i in range(3, 12, 3):
                    xs.append(v[i]); ys.append(v[i + 1]); zs.append(v[i + 2])
    dims = sorted([max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)], reverse=True)
    return dims


def main():
    thing_id, urun_id = sys.argv[1], sys.argv[2]
    files = json.loads(api("https://api.thingiverse.com/things/%s/files" % thing_id))
    stls = [f for f in files if f["name"].lower().endswith(".stl")]
    if not stls:
        print("STL YOK"); return
    stls.sort(key=lambda f: f.get("size", 0), reverse=True)  # en buyuk STL = ana parca
    f = stls[0]
    os.makedirs(STL_DIR, exist_ok=True)
    out = os.path.join(STL_DIR, urun_id + ".stl")
    data = api(f["download_url"])
    with open(out, "wb") as w:
        w.write(data)
    d = bbox(out)
    print("dosya:", f["name"], "->", out, "(%d KB)" % (len(data) // 1024))
    print("DIMS %s %.0f %.0f %.0f" % (urun_id, d[0], d[1], d[2]))


if __name__ == "__main__":
    main()
