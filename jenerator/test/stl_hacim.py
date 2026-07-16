#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Binary/ASCII STL dosyasinin KATI HACMINI (mm3) hesaplar (diverjans teoremi).

Kullanim: python3 stl_hacim.py <dosya.stl>   -> stdout'a tek sayi (mm3)
Modul olarak: stl_hacim.hacim(path) -> float

OpenSCAD render ciktisi su/gecirmez (watertight) oldugu icin sonuc kesindir;
isaretli tetrahedron toplami kullanilir, yuzey normal yonunden bagimsizdir (abs).
"""
import struct
import sys


def _ascii_mi(path):
    with open(path, "rb") as f:
        bas = f.read(512)
    if not bas.startswith(b"solid"):
        return False
    return b"facet" in bas


def _ucgenler_ascii(path):
    v = []
    with open(path, "r", errors="ignore") as f:
        for satir in f:
            s = satir.strip()
            if s.startswith("vertex"):
                p = s.split()
                v.append((float(p[1]), float(p[2]), float(p[3])))
                if len(v) == 3:
                    yield v
                    v = []


def _ucgenler_binary(path):
    with open(path, "rb") as f:
        f.seek(80)
        (n,) = struct.unpack("<I", f.read(4))
        for _ in range(n):
            kayit = f.read(50)
            d = struct.unpack("<12fH", kayit)
            yield [(d[3], d[4], d[5]), (d[6], d[7], d[8]), (d[9], d[10], d[11])]


def hacim(path):
    ucgenler = _ucgenler_ascii(path) if _ascii_mi(path) else _ucgenler_binary(path)
    toplam = 0.0
    for (a, b, c) in ucgenler:
        # isaretli hacim: dot(a, cross(b, c)) / 6
        cx = b[1] * c[2] - b[2] * c[1]
        cy = b[2] * c[0] - b[0] * c[2]
        cz = b[0] * c[1] - b[1] * c[0]
        toplam += a[0] * cx + a[1] * cy + a[2] * cz
    return abs(toplam) / 6.0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("kullanim: stl_hacim.py <dosya.stl>")
    print("%.6f" % hacim(sys.argv[1]))
