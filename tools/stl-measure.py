#!/usr/bin/env python3
"""STL sinir kutusu (bounding box) olcumu. Ikili + ASCII STL destekler.
Kullanim: python3 stl-measure.py <dosya.stl>
Cikti: X Y Z (mm) + hacim tahmini.
"""
import sys
import struct


def read_ascii(path):
    xs, ys, zs = [], [], []
    with open(path, "r", errors="ignore") as f:
        for line in f:
            p = line.split()
            if len(p) == 4 and p[0] == "vertex":
                try:
                    xs.append(float(p[1]))
                    ys.append(float(p[2]))
                    zs.append(float(p[3]))
                except ValueError:
                    pass
    return xs, ys, zs


def read_binary(path):
    xs, ys, zs = [], [], []
    with open(path, "rb") as f:
        f.read(80)
        (n,) = struct.unpack("<I", f.read(4))
        for _ in range(n):
            data = f.read(50)
            if len(data) < 50:
                break
            # 12 floats: normal(3) + 3 vertices(3 each); skip normal
            vals = struct.unpack("<12f", data[:48])
            for i in range(3, 12, 3):
                xs.append(vals[i])
                ys.append(vals[i + 1])
                zs.append(vals[i + 2])
    return xs, ys, zs


def is_ascii_stl(path):
    with open(path, "rb") as f:
        head = f.read(5)
    return head[:5].lower() == b"solid"


def main():
    path = sys.argv[1]
    if is_ascii_stl(path):
        xs, ys, zs = read_ascii(path)
        if not xs:  # bazi ikili dosyalar 'solid' ile baslar; ASCII bos ciktiysa ikili dene
            xs, ys, zs = read_binary(path)
    else:
        xs, ys, zs = read_binary(path)
    if not xs:
        print("OLCUM YOK")
        return
    dx = max(xs) - min(xs)
    dy = max(ys) - min(ys)
    dz = max(zs) - min(zs)
    dims = sorted([dx, dy, dz], reverse=True)
    print("RAW %.2f x %.2f x %.2f mm" % (dx, dy, dz))
    print("SORTED %.0f x %.0f x %.0f mm" % (dims[0], dims[1], dims[2]))


if __name__ == "__main__":
    main()
