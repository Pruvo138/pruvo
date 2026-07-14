#!/usr/bin/env python3
"""Printables'ten bir modelin en buyuk STL'ini indirir, stl/<urun_id>.stl olarak saklar,
Drive'a yedekler ve sinir kutusu olcusunu (mm) yazdirir. thingiverse-fetch.py'nin esdegeri.

TOKEN GEREKMEZ — Printables getDownloadLink mutation'i login olmadan calisir (24s imzali link).

Kullanim:
    python3 tools/printables-fetch.py <print_id> <urun_id>
Cikti (son satir, ayristirilabilir):
    DIMS <urun_id> <X> <Y> <Z>   (buyukten kucuge, tam sayi mm)
"""
import importlib.util, os, struct, sys

ROOT = "/Users/okan/dev/pruvo"
STL_DIR = os.path.join(ROOT, "stl")

_spec = importlib.util.spec_from_file_location("pr_api", os.path.join(ROOT, "tools", "printables-api.py"))
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)


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
    if not xs:  # ikili STL
        xs, ys, zs = [], [], []
        with open(path, "rb") as f:
            f.read(80)
            (n,) = struct.unpack("<I", f.read(4))
            for _ in range(n):
                dd = f.read(50)
                if len(dd) < 50:
                    break
                v = struct.unpack("<12f", dd[:48])
                for i in range(3, 12, 3):
                    xs.append(v[i]); ys.append(v[i + 1]); zs.append(v[i + 2])
    dims = sorted([max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)], reverse=True)
    return dims


def main():
    print_id, urun_id = sys.argv[1], sys.argv[2]
    os.makedirs(STL_DIR, exist_ok=True)
    out_noext = os.path.join(STL_DIR, urun_id)
    name, out, nbytes = pr.download_stl(print_id, out_noext)
    # Drive yedegi (varsa) — repo disi tek kopya
    backup_cfg = os.path.join(ROOT, ".stl-backup-dir")
    if os.path.exists(backup_cfg):
        bdir = open(backup_cfg).read().strip()
        if bdir and os.path.isdir(bdir):
            ext = os.path.splitext(out)[1]
            with open(out, "rb") as rf, open(os.path.join(bdir, urun_id + ext), "wb") as wf:
                wf.write(rf.read())
            print("yedek:", bdir)
    d = bbox(out) if out.lower().endswith(".stl") else pr.bbox_3mf(out)
    print("dosya:", name, "->", out, "(%d KB)" % (nbytes // 1024))
    print("DIMS %s %.0f %.0f %.0f" % (urun_id, d[0], d[1], d[2]))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Kullanim: python3 tools/printables-fetch.py <print_id> <urun_id>")
    main()
