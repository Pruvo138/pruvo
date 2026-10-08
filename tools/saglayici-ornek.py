#!/usr/bin/env python3
"""SAGLAYICI TURU ORNEK GORSELI (kopru-15, 8 Eki 2026) — saglayici kolundaki turun (figur) ① ornegini GERCEK
saglayici onizlemesinden uretir. Yalniz ② adimi (onizleme) kosar: build/renk YOK -> bedel KREDI_ONIZLEME.
    python3 tools/saglayici-ornek.py --tur figur --girdi-yaz <yol.png>          # agsiz: girdi cizimini yazar
    python3 tools/saglayici-ornek.py --tur figur --kredi-tavani 10              # onizleme -> webp -> R2 -> 200
Girdi SENTETIK cizimdir (kisi/marka/telifli gorsel YOK): oyuncak kedi silueti, 4 renk, desenli zemin.
Akis: kredi kapisi (foto-ornek-uc-uca.Kredi, D1 farki) -> /yonet/foto/ornek-onizleme -> ornek-durum yoklamasi ->
ornek-gorsel -> cwebp -q 90 -> pruvo-media/foto/ornek/<kod>-1-render.webp (--remote) -> medya URL 200 image/webp.
Son satir: `ORNEK tur=<kod> is=<is> px=<wxh> R2=<kod> KREDI_HARCANAN=<n>/<N> rc=<0|1>`. Manifest satirini
(ornekler) BU ARAC YAZMAZ — kaydi mimar elle ekler (kanit "render").
"""
import argparse
import importlib.util
import os
import struct
import subprocess
import sys
import tempfile
import zlib

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UU = os.path.join(KOK, "tools", "foto-ornek-uc-uca.py")
CWEBP = "/opt/homebrew/bin/cwebp"
R2_ONEK = "pruvo-media/foto/ornek/"
MEDYA_URL = "https://media.pruvo3d.com/foto/ornek/"


def uu():
    s = importlib.util.spec_from_file_location("foto_uu", UU)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def rgb_png(w, h, piksel):
    satir = b"".join(b"\x00" + b"".join(bytes(piksel(x, y)) for x in range(w)) for y in range(h))

    def ch(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) +
            ch(b"IDAT", zlib.compress(satir, 9)) + ch(b"IEND", b""))


def kedi_cizimi(n=640):
    """Oyuncak kedi: turuncu govde+bas, krem karin+agiz, koyu goz/burun, ucgen kulak. Zemin acik desenli."""
    turuncu, krem, koyu = (232, 128, 46), (250, 232, 200), (40, 34, 30)
    s = n / 640.0

    def elips(x, y, cx, cy, rx, ry):
        return ((x - cx * s) / (rx * s)) ** 2 + ((y - cy * s) / (ry * s)) ** 2 <= 1

    def ucgen(x, y, a, b, c):
        def k(p, q, r):
            return (p[0] - r[0]) * (q[1] - r[1]) - (q[0] - r[0]) * (p[1] - r[1])
        p = (x / s, y / s)
        d1, d2, d3 = k(p, a, b), k(p, b, c), k(p, c, a)
        return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))

    def piksel(x, y):
        for cx in (290, 350):                                   # gozler
            if elips(x, y, cx, 230, 14, 20):
                return koyu
        if elips(x, y, 320, 270, 12, 9):                        # burun
            return koyu
        if elips(x, y, 320, 288, 34, 22):                       # agiz bolgesi
            return krem
        if elips(x, y, 320, 245, 100, 88):                      # bas
            return turuncu
        if ucgen(x, y, (232, 210), (262, 120), (300, 170)) or ucgen(x, y, (408, 210), (378, 120), (340, 170)):
            return turuncu                                      # kulaklar
        if elips(x, y, 320, 430, 80, 95):                       # karin
            return krem
        if elips(x, y, 320, 420, 120, 130):                     # govde
            return turuncu
        for cx in (265, 375):                                   # patiler
            if elips(x, y, cx, 545, 40, 22):
                return krem
        if elips(x, y, 455, 470, 22, 70):                       # kuyruk
            return turuncu
        g = 236 + (x * 7919 + y * 104729) % 11                  # desenli zemin (GORSEL_EN_AZ_BAYT ustu)
        return (g, g, g)
    return rgb_png(n, n, piksel)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Saglayici turu ornek gorseli (yalniz onizleme adimi)")
    ap.add_argument("--tur", required=True)
    ap.add_argument("--kredi-tavani", type=int, default=0)
    ap.add_argument("--girdi-yaz", help="yalniz girdi cizimini bu yola yaz (ag YOK)")
    a = ap.parse_args(argv)
    girdi = kedi_cizimi()
    if a.girdi_yaz:
        with open(a.girdi_yaz, "wb") as f:
            f.write(girdi)
        print("GIRDI=%s bayt=%d" % (a.girdi_yaz, len(girdi)))
        return 0
    m = uu()
    m.MAN.update(m.manifest_oku())
    t = {x["kod"]: x for x in m.MAN["turler"]}.get(a.tur)
    if not t or t.get("kol") != "saglayici":
        print("HATA tur saglayici kolunda degil: %s\nORNEK tur=%s rc=1" % (a.tur, a.tur))
        return 1
    if a.kredi_tavani <= 0:
        print("HATA --kredi-tavani > 0 gerekli (0 = saglayiciya istek YOK)\nORNEK tur=%s rc=1" % a.tur)
        return 1
    bulut = m.Bulut(*m.hedef_adlari())
    kredi = m.Kredi(bulut, a.kredi_tavani)
    tr = m.Tur(a.tur, t)
    tr.olcu = m.olcu_sec(t)
    tr.dosyalar = {"foto": ("figur-girdi.png", girdi, "image/png")}
    m.saglayici_2(tr, kredi)
    print("② %s %s" % ("HAZIR" if tr.s["2"][0] else "EKSIK", tr.s["2"][1]))
    son = "ORNEK tur=%s is=%s" % (a.tur, tr.is_no or "-")
    if not tr.s["2"][0]:
        print("%s KREDI_HARCANAN=%d/%d rc=1" % (son, kredi.harcanan(), kredi.tavan))
        return 1
    k, tip, b = m.yonet("GET", "/foto/ornek-gorsel?is=" + tr.is_no)
    px = m.gorsel_boyut(b)
    d = tempfile.mkdtemp(prefix="saglayici-ornek-")
    try:
        ham, webp = os.path.join(d, "ham"), os.path.join(d, "ornek.webp")
        with open(ham, "wb") as f:
            f.write(b)
        p = subprocess.run([CWEBP, "-quiet", "-q", "90", ham, "-o", webp], capture_output=True, text=True)
        if p.returncode != 0:
            print("%s px=%s cwebp=%s KREDI_HARCANAN=%d/%d rc=1" % (son, px, p.stderr.strip()[-200:], kredi.harcanan(),
                                                                   kredi.tavan))
            return 1
        ad = "%s-1-render.webp" % a.tur
        p = bulut.wr(["r2", "object", "put", R2_ONEK + ad, "--remote", "--file", webp, "--content-type", "image/webp"])
        k, tip, _ = m.http("GET", MEDYA_URL + ad)
        ok = p.returncode == 0 and k == 200 and tip.startswith("image/webp")
        print("%s px=%s R2=%s url=%s KREDI_HARCANAN=%d/%d rc=%d" % (
            son, "%dx%d" % px if px else "yok", k, MEDYA_URL + ad, kredi.harcanan(), kredi.tavan, 0 if ok else 1))
        return 0 if ok else 1
    finally:
        for ad in os.listdir(d):
            os.remove(os.path.join(d, ad))
        os.rmdir(d)


if __name__ == "__main__":
    sys.exit(main())
