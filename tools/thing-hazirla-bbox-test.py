#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""thing-hazirla.py bbox() BELIRSIZ-BIRIM kabul testi (metre-sezgisi 2. kopyasi).

thing-hazirla.bbox() printables-api.stl_bbox()'in AYRI bir kopyasidir (bytes alir, path degil) ve
ayni metre-sezgisi kusurunu tasiyordu: `if d[0] < 2.0: d = [x*1000 ...]`. FIX: `max(d) < 2.0 ->
None` (fail-closed) — binary STL birim beyani tasimaz, en buyuk boyut < 2 birim ise mm/metre/inc
ayirt edilemez; uydurma yerine olcemeyip None don. Bu ayri fonksiyonu stl-bbox-binary-test.py
KAPSAMAZ -> ayri smoke/birim testi.

Vakalar (sentetik binary STL, deterministik):
  1. BELIRSIZ  : 0.65-birim kup -> None (650mm DEGIL) — asil fix.
  2. NORMAL    : 50mm kup       -> ~50mm.
  3. INCE-LEVHA: 100 × 100 × 0.5 -> DONER (max=100 >= 2; None DEGIL).
KIRMIZI-MUTASYON: eski metre-sezgisi (x1000) -> vaka 1'de 0.65 parca ~650mm verir = KIRMIZI;
  canli bbox None. (mutant IZOLE; canli thing-hazirla.py'ye DOKUNULMAZ.)

⚠️ YEREL-ONLY: thing-hazirla.py import aninda ROOT=/Users/okan/dev/pruvo altindan .thingiverse-token
okur (hardcoded yol) -> CI fresh-checkout'ta import PATLAR. Bu yuzden deploy.yml'e EKLENMEZ,
ci-kapsam-test IZIN_LISTESI'nde gerekceyle muaftir (test-bbox-3mf emsali; yerelde kosulur).

Kullanim: python3 tools/thing-hazirla-bbox-test.py  (argumansiz; basarisizlikta exit!=0)
"""
import importlib.util
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

_spec = importlib.util.spec_from_file_location("thing_hazirla", os.path.join(HERE, "thing-hazirla.py"))
th = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(th)   # NOT: ROOT hardcoded -> yerelde token okur, CI'da patlar (muaf)

_TRIS_IDX = [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
             (3, 2, 6), (3, 6, 7), (0, 3, 7), (0, 7, 4), (1, 2, 6), (1, 6, 5)]


def box_tris(sx, sy, sz):
    v = [(0, 0, 0), (sx, 0, 0), (sx, sy, 0), (0, sy, 0),
         (0, 0, sz), (sx, 0, sz), (sx, sy, sz), (0, sy, sz)]
    return [(v[a], v[b], v[c]) for (a, b, c) in _TRIS_IDX]


def binary_stl(header_text, tris):
    """80-bayt header ('solid' ile BASLAMAZ, 'vertex' icermez) + uint32 n + n*50 govde."""
    h = header_text.encode("ascii")
    assert len(h) <= 80
    out = bytearray(h + b" " * (80 - len(h)))
    out += struct.pack("<I", len(tris))
    for (v0, v1, v2) in tris:
        out += struct.pack("<3f", 0.0, 0.0, 0.0)
        for (x, y, z) in (v0, v1, v2):
            out += struct.pack("<3f", float(x), float(y), float(z))
        out += struct.pack("<H", 0)
    return bytes(out)


def _raw_dims(data):
    """bbox()'in esiksiz HAM boyutlari (binary yol) — mutant tail bunun uzerine."""
    xs, ys, zs = [], [], []
    if len(data) >= 84:
        n = struct.unpack("<I", data[80:84])[0]
        if 84 + n * 50 == len(data):
            off = 84
            for _ in range(n):
                v = struct.unpack("<12f", data[off:off + 48]); off += 50
                for j in range(3, 12, 3):
                    xs.append(v[j]); ys.append(v[j + 1]); zs.append(v[j + 2])
    if not xs:
        return None
    return sorted([max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)], reverse=True)


def _mut_metre(data):
    """MUTANT (too-LAX) = FIX ONCESI metre-sezgisi: en buyuk boyut <2 -> x1000. 0.65->650."""
    d = _raw_dims(data)
    if d is None:
        return None
    if d[0] < 2.0:
        d = [x * 1000 for x in d]
    if d[0] <= 0 or d[0] > 100000:
        return None
    return d


def yaklasik(d, exp, tol=0.05):
    if not isinstance(d, list) or len(d) != len(exp):
        return False
    return all(abs(a - b) <= tol for a, b in zip(sorted(d, reverse=True), sorted(exp, reverse=True)))


def main():
    hata = []
    b_kucuk = binary_stl("PRUVO small 0.65", box_tris(0.65, 0.65, 0.65))
    b_50 = binary_stl("PRUVO 50mm cube", box_tris(50.0, 50.0, 50.0))
    b_levha = binary_stl("PRUVO thin plate", box_tris(100.0, 100.0, 0.5))

    print("thing-hazirla.bbox() BELIRSIZ-BIRIM kabul testi")
    print("-" * 64)

    d1 = th.bbox(b_kucuk)
    ok1 = d1 is None
    print("  1 BELIRSIZ    0.65-birim kup          -> %-18s %s" % (d1, "OK" if ok1 else "FAIL"))
    if not ok1:
        hata.append("BELIRSIZ: 0.65 kup None donmeli (650mm DEGIL), gelen %r" % (d1,))

    d2 = th.bbox(b_50)
    ok2 = yaklasik(d2, [50, 50, 50])
    print("  2 NORMAL      50mm kup                -> %-18s %s" % (d2, "OK" if ok2 else "FAIL"))
    if not ok2:
        hata.append("NORMAL: ~50mm bekleniyordu, gelen %r" % (d2,))

    d3 = th.bbox(b_levha)
    ok3 = yaklasik(d3, [100, 100, 0.5])
    print("  3 INCE-LEVHA  100 × 100 × 0.5         -> %-18s %s" % (d3, "OK" if ok3 else "FAIL"))
    if not ok3:
        hata.append("INCE-LEVHA: [100,100,0.5] bekleniyordu (None DEGIL), gelen %r" % (d3,))

    print("-" * 64)
    mB = _mut_metre(b_kucuk)
    canli = th.bbox(b_kucuk)
    mB_kirmizi = mB is not None
    print("  MUT  metre-sezgisi 0.65 kup -> %-30s %s" % (mB, "RED(beklenen)" if mB_kirmizi else "GREEN(!)"))
    print("  MUT  canli        0.65 kup  -> %-30s %s" % (canli, "GREEN" if canli is None else "RED(!)"))
    if not mB_kirmizi:
        hata.append("MUT ETKISIZ: metre-sezgisi mutant 0.65 kupte de None verdi")
    elif not (isinstance(mB, list) and mB[0] > 600):
        hata.append("MUT beklenen ~650mm (fizik-disi), gelen %r" % (mB,))
    if canli is not None:
        hata.append("MUT canli: 0.65 kup None donmedi (%r)" % (canli,))

    print("-" * 64)
    if hata:
        for h in hata:
            print("  X " + h)
        print("SONUC: KIRMIZI  (%d sorun)" % len(hata))
        return 1
    print("SONUC: YESIL  — 3 vaka + kirmizi-mutasyon gecti.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
