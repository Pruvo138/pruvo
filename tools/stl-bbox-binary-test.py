#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stl_bbox() BINARY-ONCE tespit kabul testi (printables-api.py).

KUSUR (MaCiT teshisi): binary STL header'inda duz metin "solid ..." (Fusion360/
SolidWorks export deseni) varsa eski kod dosyayi ASCII saniyor, binary copten
data.decode(...) ile tesadufi "vertex ..." desenleri toplayip SESSIZCE yanlis bbox
uretiyordu. FIX: format karari BINARY-ONCE aritmetikle verilir (n>0 VE
len==84+n*50 -> binary parse), "solid" basligina GUVENILMEZ; aksi halde ASCII;
hicbiri gecmezse fail-closed (None).

Deterministik sentetik fikstur: 10mm kenarli kup (8 kose, 12 ucgen) 3 STL biciminde
INSA edilir; beklenen bbox = [10, 10, 10]. Gercek STL dosyasi GEREKMEZ.

Vakalar (BINARY-ONCE tespit):
  1. TUZAK      : header'i "solid Fusion..." ile baslayan + icinde aldatici "vertex"
                  metni tasiyan GECERLI binary kup -> binary yol, 10x10x10 (asil fix).
  2. REGR-ASCII : gercek ASCII kup -> 10x10x10 (ASCII yolu bozulmadi).
  3. REGR-BINARY: "solid" ile BASLAMAYAN gecerli binary kup -> 10x10x10.
  4. FAIL-CLOSED: len<84 / 0-ucgen / bozuk-kesik / html -> cokme YOK, None (uydurma YOK).

Vakalar (BELIRSIZ-BIRIM fail-closed — MaCiT teshisi, metre-sezgisi kaldirildi):
  5. BELIRSIZ   : ham 0.65-birim parca (aslinda ~16.5mm inc) -> None (650mm DEGIL). Eski kod
                  "<2 birim => metre" sanip x1000 ile FIZIK-DISI 650mm uretiyordu; artik None.
  6. NORMAL-MM  : 50mm parca -> ~50mm (esik ustu, oldugu gibi doner).
  7. INCE-LEVHA : 100 x 100 x 0.5 -> DONER (max=100 >= 2; SADECE en buyuk boyut <2 belirsizdir).
KIRMIZI-MUTASYON (CIFT-YON):
  A) tespit sirasini ESKIYE al (ASCII-once) -> TUZAK (1) KIRMIZI (900/800/700).
  B) metre-sezgisi (too-LAX, eski x1000) -> vaka 5 (0.65 parca) 650mm verir = KIRMIZI.
  C) min-boyut esigi (too-STRICT, min(d)<2 -> None) -> vaka 7 (ince levha) None verir = KIRMIZI.
  (mutasyonlar IZOLE kopyada uygulanir; canli printables-api.py'ye DOKUNULMAZ.)

Kullanim: python3 tools/stl-bbox-binary-test.py  (argumansiz; basarisizlikta exit!=0)
"""
import importlib.util
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

# Test edilen modulu yukle (dosya adinda '-' var -> normal import olmaz).
# printables-api.py alt kismindaki smoke-test `if __name__ == "__main__"` guard'i
# ile korunur, exec_module ag'a vurmaz.
_spec = importlib.util.spec_from_file_location(
    "printables_api", os.path.join(HERE, "printables-api.py"))
pa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pa)

# --- 10mm kup geometrisi: 8 kose + 12 ucgen (bbox her eksende 0..10) ---
_V = [(0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0),
      (0, 0, 10), (10, 0, 10), (10, 10, 10), (0, 10, 10)]
_TRIS_IDX = [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
             (3, 2, 6), (3, 6, 7), (0, 3, 7), (0, 7, 4), (1, 2, 6), (1, 6, 5)]
CUBE = [(_V[a], _V[b], _V[c]) for (a, b, c) in _TRIS_IDX]


def pad80(b):
    """Header icerigini TAM 80 bayta getir (kesme YOK; 80'i asarsa hata)."""
    assert len(b) <= 80, "header icerigi 80 bayti asti: %d" % len(b)
    return b + b" " * (80 - len(b))


def binary_stl(header80, tris):
    """80-bayt header + uint32 ucgen sayisi + her ucgen 50 bayt (normal + 3 vertex +
    2-bayt oznitelik). Gecerli binary STL bayt dizisi doner."""
    assert len(header80) == 80, "header 80 bayt olmali, %d" % len(header80)
    out = bytearray(header80)
    out += struct.pack("<I", len(tris))
    for (v0, v1, v2) in tris:
        out += struct.pack("<3f", 0.0, 0.0, 0.0)          # normal (bbox'ta okunmaz)
        for (x, y, z) in (v0, v1, v2):
            out += struct.pack("<3f", float(x), float(y), float(z))
        out += struct.pack("<H", 0)                        # attribute byte count
    return bytes(out)


def ascii_stl(tris, ad="cube"):
    """Gercek ASCII STL metni (solid/facet/outer loop/vertex/endloop/endfacet)."""
    satir = ["solid %s" % ad]
    for (v0, v1, v2) in tris:
        satir.append("  facet normal 0 0 0")
        satir.append("    outer loop")
        for (x, y, z) in (v0, v1, v2):
            satir.append("      vertex %g %g %g" % (x, y, z))
        satir.append("    endloop")
        satir.append("  endfacet")
    satir.append("endsolid %s" % ad)
    return ("\n".join(satir) + "\n").encode("utf-8")


def yaz(blob):
    """Baytlari gecici bir .stl dosyasina yazip yolu doner (temizlik sonda)."""
    fd, yol = tempfile.mkstemp(suffix=".stl")
    with os.fdopen(fd, "wb") as w:
        w.write(blob)
    return yol


# --- TUZAK fikstur: "solid" ile baslar (eski kod ASCII sanar) + header'da ALDATICI
#     vertex satirlari. Eski (ASCII-once) kod bunlari okur -> YANLIS bbox [900,800,700];
#     dogru geometri binary govdede -> yeni (binary-once) kod [10,10,10] verir. ---
_TUZAK_ICERIK = b"solid Fusion\nvertex 0 0 0\nvertex 900 800 700\n"
TUZAK_HEADER = pad80(_TUZAK_ICERIK)


# --- MUTASYON: fix ONCESI (ASCII-once) davranisin BIREBIR kopyasi. Canli dosyada
#     DEGIL; yalniz bu testte. TUZAK vakasini KIRMIZI yakmasi beklenir. ---
def _ascii_first_bbox(path):
    with open(path, "rb") as f:
        data = f.read()
    head = data[:512].lstrip().lower()
    if head.startswith(b"<") or b"<html" in head or b"just a moment" in head:
        return None
    xs, ys, zs = [], [], []
    if b"vertex" in data[:2000] or data[:5].lower() == b"solid":
        for line in data.decode("utf-8", "ignore").splitlines():
            p = line.strip().split()
            if len(p) == 4 and p[0] == "vertex":
                try:
                    xs.append(float(p[1])); ys.append(float(p[2])); zs.append(float(p[3]))
                except ValueError:
                    pass
    if not xs and len(data) >= 84:
        n = struct.unpack("<I", data[80:84])[0]
        if 84 + n * 50 != len(data):
            return None
        off = 84
        for _ in range(n):
            if off + 48 > len(data):
                break
            v = struct.unpack("<12f", data[off:off + 48]); off += 50
            for j in range(3, 12, 3):
                xs.append(v[j]); ys.append(v[j + 1]); zs.append(v[j + 2])
    if not xs:
        return None
    d = sorted([max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)], reverse=True)
    if d[0] < 2.0:
        d = [x * 1000 for x in d]
    if d[0] <= 0 or d[0] > 100000:
        return None
    return d


def kup_mu(d, tol=0.01):
    """d == [10, 10, 10] (± tol) mi?"""
    if not isinstance(d, list) or len(d) != 3:
        return False
    return all(abs(x - 10.0) <= tol for x in d)


# --- FIX A (BELIRSIZ-BIRIM) yardimcilari -------------------------------------
def box_tris(sx, sy, sz):
    """Kenar olculeri (sx,sy,sz) olan eksen-hizali kutu -> 12 ucgen (her eksende 0..s)."""
    v = [(0, 0, 0), (sx, 0, 0), (sx, sy, 0), (0, sy, 0),
         (0, 0, sz), (sx, 0, sz), (sx, sy, sz), (0, sy, sz)]
    return [(v[a], v[b], v[c]) for (a, b, c) in _TRIS_IDX]


def yaklasik(d, exp, tol=0.05):
    """d, exp listesine (± tol) esit mi? (float32 yuvarlama toleransli)."""
    if not isinstance(d, list) or len(d) != len(exp):
        return False
    return all(abs(a - b) <= tol for a, b in zip(sorted(d, reverse=True), sorted(exp, reverse=True)))


def _raw_dims(path):
    """path'ten HAM (esiksiz) sorted-desc boyutlar — mutant tail mantigi bunun uzerine
    uygulanir. Binary STL parse (bu testin fikstyurleri binary). Bulunamazsa None."""
    with open(path, "rb") as f:
        data = f.read()
    xs, ys, zs = [], [], []
    if len(data) >= 84:
        n = struct.unpack("<I", data[80:84])[0]
        if n > 0 and 84 + n * 50 == len(data):
            off = 84
            for _ in range(n):
                v = struct.unpack("<12f", data[off:off + 48]); off += 50
                for j in range(3, 12, 3):
                    xs.append(v[j]); ys.append(v[j + 1]); zs.append(v[j + 2])
    if not xs:
        return None
    return sorted([max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)], reverse=True)


def _mut_metre(path):
    """MUTANT B (too-LAX) = FIX ONCESI metre-sezgisi: en buyuk boyut <2 -> x1000. Canli dosyada
    DEGIL; 0.65 parcayi 650mm yapip vaka 5'i KIRMIZI yakmasi beklenir."""
    d = _raw_dims(path)
    if d is None:
        return None
    if d[0] < 2.0:
        d = [x * 1000 for x in d]
    if d[0] <= 0 or d[0] > 100000:
        return None
    return d


def _mut_anydim(path):
    """MUTANT C (too-STRICT) = HERHANGI boyut <2 -> None (naif asiri-kati alternatif fix). Canli
    dosyada DEGIL; ince levhayi (0.5) yanlislikla eleyip vaka 7'yi KIRMIZI yakmasi beklenir."""
    d = _raw_dims(path)
    if d is None:
        return None
    if min(d) < 2.0:
        return None
    if d[0] <= 0 or d[0] > 100000:
        return None
    return d


def main():
    tmp = []
    hata = []
    try:
        p_tuzak = yaz(binary_stl(TUZAK_HEADER, CUBE)); tmp.append(p_tuzak)
        p_ascii = yaz(ascii_stl(CUBE)); tmp.append(p_ascii)
        p_bin = yaz(binary_stl(pad80(b"PRUVO test cube (binary)"), CUBE)); tmp.append(p_bin)
        p_kisa = yaz(b"solidshort"); tmp.append(p_kisa)                       # len<84
        p_sifir = yaz(pad80(b"PRUVO empty") + struct.pack("<I", 0)); tmp.append(p_sifir)  # 0 ucgen
        p_kesik = yaz(pad80(b"PRUVO trunc") + struct.pack("<I", 12) + b"\x00" * 20)
        tmp.append(p_kesik)                                                   # bozuk: 12 iddia, govde eksik
        p_html = yaz(b"<html><body>Just a moment...</body></html>"); tmp.append(p_html)
        # FIX A fikstyurleri (BELIRSIZ-BIRIM): 0.65-birim / 50mm / ince levha (binary)
        p_kucuk = yaz(binary_stl(pad80(b"PRUVO small 0.65"), box_tris(0.65, 0.65, 0.65))); tmp.append(p_kucuk)
        p_50 = yaz(binary_stl(pad80(b"PRUVO 50mm"), box_tris(50.0, 50.0, 50.0))); tmp.append(p_50)
        p_levha = yaz(binary_stl(pad80(b"PRUVO thin plate"), box_tris(100.0, 100.0, 0.5))); tmp.append(p_levha)

        print("stl_bbox() BINARY-ONCE tespit kabul testi")
        print("-" * 64)

        # 1) TUZAK (asil fix): "solid" basligli GECERLI binary kup -> 10x10x10
        d = pa.stl_bbox(p_tuzak)
        ok = kup_mu(d)
        print("  1 TUZAK       binary-'solid'-header kup -> %-18s %s" % (d, "OK" if ok else "FAIL"))
        if not ok:
            hata.append("TUZAK: beklenen [10,10,10], gelen %r" % (d,))

        # 2) REGRESYON-ASCII: gercek ASCII kup -> 10x10x10
        d = pa.stl_bbox(p_ascii)
        ok = kup_mu(d)
        print("  2 REGR-ASCII  gercek ASCII kup         -> %-18s %s" % (d, "OK" if ok else "FAIL"))
        if not ok:
            hata.append("REGR-ASCII: beklenen [10,10,10], gelen %r" % (d,))

        # 3) REGRESYON-BINARY: "solid" ile baslamayan binary kup -> 10x10x10
        d = pa.stl_bbox(p_bin)
        ok = kup_mu(d)
        print("  3 REGR-BINARY non-'solid'-header kup   -> %-18s %s" % (d, "OK" if ok else "FAIL"))
        if not ok:
            hata.append("REGR-BINARY: beklenen [10,10,10], gelen %r" % (d,))

        # 4) FAIL-CLOSED: bozuk/kisa/0-ucgen/html -> cokme YOK, None (uydurma olcu YOK)
        for etiket, yol in (("len<84", p_kisa), ("0-ucgen", p_sifir),
                            ("kesik-binary", p_kesik), ("html", p_html)):
            try:
                d = pa.stl_bbox(yol)
            except Exception as e:  # noqa: BLE001 - fail-closed: hicbir girdide firlatmamali
                d = "<EXC:%s>" % e
                hata.append("FAIL-CLOSED %s: fonksiyon FIRLATTI (%s)" % (etiket, e))
            ok = (d is None)
            print("  4 FAIL-CLOSED %-13s              -> %-18s %s" % (etiket, d, "OK" if ok else "FAIL"))
            if not ok and not str(d).startswith("<EXC"):
                hata.append("FAIL-CLOSED %s: None bekleniyordu, gelen %r" % (etiket, d))

        # KIRMIZI-MUTASYON: tespit sirasi ESKIYE (ASCII-once) alininca TUZAK KIRMIZI olmali.
        print("-" * 64)
        canli = pa.stl_bbox(p_tuzak)
        mutant = _ascii_first_bbox(p_tuzak)
        canli_ok = kup_mu(canli)
        mutant_kirmizi = not kup_mu(mutant)     # mutant TUZAK'ta 10x10x10 VERMEMELI
        print("  MUTASYON  canli (binary-once)  TUZAK -> %-18s %s" % (canli, "GREEN" if canli_ok else "RED"))
        print("  MUTASYON  mutant (ASCII-once)  TUZAK -> %-18s %s" % (mutant, "RED(beklenen)" if mutant_kirmizi else "GREEN(!)"))
        if not canli_ok:
            hata.append("MUTASYON: canli fonksiyon TUZAK'i 10x10x10 vermedi (%r)" % (canli,))
        if not mutant_kirmizi:
            hata.append("MUTASYON ETKISIZ: ASCII-once mutant da TUZAK'i 10x10x10 verdi (%r) "
                        "-> test kusuru yakalamiyor" % (mutant,))

        # ================= FIX A: BELIRSIZ-BIRIM (metre-sezgisi kaldirildi) =================
        print("-" * 64)
        # 5) BELIRSIZ: 0.65-birim parca -> None (650mm DEGIL) — asil fix
        d5 = pa.stl_bbox(p_kucuk)
        ok5 = d5 is None
        print("  5 BELIRSIZ    0.65-birim parca        -> %-18s %s" % (d5, "OK" if ok5 else "FAIL"))
        if not ok5:
            hata.append("BELIRSIZ: 0.65-birim parca None donmeli (650mm DEGIL), gelen %r" % (d5,))
        # 6) NORMAL-MM: 50mm -> ~50 (esik ustu, oldugu gibi doner)
        d6 = pa.stl_bbox(p_50)
        ok6 = yaklasik(d6, [50, 50, 50])
        print("  6 NORMAL-MM   50mm parca              -> %-18s %s" % (d6, "OK" if ok6 else "FAIL"))
        if not ok6:
            hata.append("NORMAL-MM: ~50mm bekleniyordu, gelen %r" % (d6,))
        # 7) INCE-LEVHA: 100 x 100 x 0.5 -> DONER (max=100>=2, None DEGIL)
        d7 = pa.stl_bbox(p_levha)
        ok7 = yaklasik(d7, [100, 100, 0.5])
        print("  7 INCE-LEVHA  100 x 100 x 0.5         -> %-18s %s" % (d7, "OK" if ok7 else "FAIL"))
        if not ok7:
            hata.append("INCE-LEVHA: [100,100,0.5] bekleniyordu (None DEGIL), gelen %r" % (d7,))

        # KIRMIZI-MUTASYON B (too-LAX metre-sezgisi): 0.65 parca 650mm = KIRMIZI, canli None = dogru
        print("-" * 64)
        mB = _mut_metre(p_kucuk)
        canli5 = pa.stl_bbox(p_kucuk)
        mB_kirmizi = mB is not None            # mutant None VERMEMELI (yanlis ~650 verir)
        print("  MUT-B  metre-sezgisi 0.65 parca -> %-18s %s" % (mB, "RED(beklenen)" if mB_kirmizi else "GREEN(!)"))
        print("  MUT-B  canli        0.65 parca  -> %-18s %s" % (canli5, "GREEN" if canli5 is None else "RED(!)"))
        if not mB_kirmizi:
            hata.append("MUT-B ETKISIZ: metre-sezgisi mutant 0.65 parcada da None verdi -> test kusuru yakalamiyor")
        elif not (isinstance(mB, list) and mB[0] > 600):
            hata.append("MUT-B beklenen ~650mm (fizik-disi), gelen %r" % (mB,))
        if canli5 is not None:
            hata.append("MUT-B canli: 0.65 parca None donmedi (%r)" % (canli5,))

        # KIRMIZI-MUTASYON C (too-STRICT min-boyut): ince levha None = KIRMIZI, canli doner = dogru
        mC = _mut_anydim(p_levha)
        canli7 = pa.stl_bbox(p_levha)
        mC_kirmizi = mC is None                # mutant ince levhayi yanlislikla eler
        print("  MUT-C  min-esik ince levha      -> %-18s %s" % (mC, "RED(beklenen)" if mC_kirmizi else "GREEN(!)"))
        print("  MUT-C  canli    ince levha      -> %-18s %s" % (canli7, "GREEN" if canli7 is not None else "RED(!)"))
        if not mC_kirmizi:
            hata.append("MUT-C ETKISIZ: min-esik mutant ince levhayi elemedi -> test kusuru yakalamiyor")
        if canli7 is None:
            hata.append("MUT-C canli: ince levha None dondu (elenmemeliydi)")

        print("-" * 64)
        if hata:
            for h in hata:
                print("  X " + h)
            print("SONUC: KIRMIZI  (%d sorun)" % len(hata))
            return 1
        print("SONUC: YESIL  — 7 vaka + 3 kirmizi-mutasyon (A ASCII-once, B metre-lax, C min-strict) gecti.")
        return 0
    finally:
        for y in tmp:
            try:
                os.unlink(y)
            except OSError:
                pass


if __name__ == "__main__":
    sys.exit(main())
