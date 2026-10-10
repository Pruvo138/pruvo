#!/usr/bin/env python3
"""FOTO URETEC KOSUCUSU — hermetik kabul testi + mutantlar (tools/foto-uretec-kosucu.py).

HERMETIK: wrangler yerine SAHTE komut (D1 = gecici SQLite, sema tools/d1-sema.sql; R2 = gecici
dizin), uretec yerine SAHTE komut. Gercek D1/R2/ev yolu YOK; her sey tempfile altinda, bitince silinir.

EVREN (K3d, 9 Eki 2026; manifest foto-uretim-veri.js TEK KAYNAK): plaket · figur (motor M, saglayici; bu
kosucunun ISI DEGIL) · bust (D, rolyef_uret) · yapboz (D, yapboz_uret) · anahtarlik (D, isimlik_uret +
anahtarlik:true). Silinen 15 tur (litofan, isimlik, qr, logo, ...) testte TUR olarak YOK; tarayici onizleyicisi YOK.

Vakalar (CEKIRDEK tur = bust; uretec sahte §1 "sozlesme" CLI'ina yonlenir): T1 BOS rc=1 · T2 1 is -> ISLEDI +
hazir + 3 dosya R2'de · T3 rc 2 -> elle · T4 ariza x3 -> elle · T5 sizdirmaz:false -> elle, R2 yazimi 0 ·
T6 CAS kaybi -> yazim yok · T7 D1/R2 erisim yok -> OLCULEMEDI rc=4 + satir DEGISMEDI · T8 kilit -> KILITLI
rc=3 · T9 KURU -> yazim 0 · T10 onizleme kuyrugu -> onizleme-hazir · T11 log tavani · T12 KOPYA KOLU
(onizlemeye bagli siparis, ayni girdi sha -> uretec KOSMAZ) · T12b sha farkli -> uretec yeniden koşar.
Mutantlar (kosucu kopyasi gecici dizinde): M1 sizdirmaz · M2 KURU · M3 CAS · M4 deneme tavani · M5 jeton geri ·
M6/M7 kopya kolu · M0 yorum -> 0 kirmizi.

TEKIN-ORTAK KOPRUSU (yapboz + anahtarlik): T13-<kod> sahte tekin uretecine giden JSON BIREBIR beklenen (form
AYNEN + olcu alani + palet/bolge renkleri RENK_HEX + anahtarlik sabiti) + onizleme-hazir + olcu.json ·
T14 RET "kontrast" -> `uretec-red:kontrast` · T16 tanimsiz renk adi · T18 sema disi parametre · T35 palet sira
boslugu · T36 palet disi bolge -> uretec KOSMAZ · T17 renk_sayisi 3MF'ten OLCULUR · T19 plaka 300 · T20 uzun
kenar geometriden · T21 yapboz araligi · T22/T23 ORNEK kolu.
Manifest tutarliligi (V1-V9, node + kosucu modulu): 2 kopru satiri, metinler AYNEN, renk adlari RENK_HEX'te,
tarayici onizleyicili tur 0, form alanlari uretec semasina eslenir, red metni, parametre dogrulamasi.
`--gercek [--json <yol>]`: CI DISI — 2 GERCEK uretec (yapboz, anahtarlik) x min/orta/maks = 6 koşum (sahte D1/R2).
"""
import fcntl
import hashlib
import json
import os
import plistlib
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
import zipfile
import zlib
import re
from datetime import datetime, timezone

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOSUCU = os.path.join(KOK, "tools", "foto-uretec-kosucu.py")
SEMA = os.path.join(KOK, "tools", "d1-sema.sql")
IS = "0123456789abcdef0123456789abcdef"
IS2 = "fedcba9876543210fedcba9876543210"
SIP = "PR-251007-101500-ABC"
GUNCEL0 = "2026-10-07T00:00:00.000Z"

SAHTE_WRANGLER = r'''
import json, os, shutil, sqlite3, sys
a = sys.argv[1:]
log = open(os.environ["FAKE_LOG"], "a")
log.write(json.dumps(a) + "\n"); log.close()
if a[:2] == ["d1", "execute"]:
    if os.environ.get("FAKE_D1_KAPALI"):
        sys.stderr.write("fetch failed\n"); sys.exit(1)
    sql = a[a.index("--command") + 1]
    c = sqlite3.connect(os.environ["FAKE_DB"]); c.row_factory = sqlite3.Row
    if os.environ.get("FAKE_CAS_KAYBI") and sql.startswith("UPDATE") and "uretec-bekliyor" in sql:
        c.execute("UPDATE foto_uretim SET asama='hazir', guncel='baska-kosucu'"); c.commit()
    cur = c.execute(sql); rows = [dict(r) for r in cur.fetchall()]; c.commit()
    print(json.dumps([{"results": rows, "success": True, "meta": {"changes": cur.rowcount if sql.startswith("UPDATE") else 0}}]))
    sys.exit(0)
if a[:2] == ["r2", "object"]:
    if os.environ.get("FAKE_R2_KAPALI"):
        sys.stderr.write("Authentication error\n"); sys.exit(1)
    anahtar = a[3].split("/", 1)[1]; dosya = a[a.index("--file") + 1]
    yol = os.path.join(os.environ["FAKE_R2"], anahtar)
    if a[2] == "get":
        if not os.path.isfile(yol):
            sys.stderr.write("The specified key does not exist.\n"); sys.exit(1)
        shutil.copyfile(yol, dosya); sys.exit(0)
    os.makedirs(os.path.dirname(yol), exist_ok=True); shutil.copyfile(dosya, yol); sys.exit(0)
sys.exit(9)
'''

# Sahte 3MF onarim koprusu (TeKiN uc_mf_onar.py CLI: `<girdi> <cikti>` · `--olc <girdi> <cikti>`).
# FAKE_KOPRU: ok (varsayilan) | olc-kirmizi (her --olc rc 1 + kusur) | tek-kirmizi (yalniz TEK dosya --olc
# kirmizi; onarim sonrasi cift olcum gecer) | girdi (onarim rc 2) | aynen (onarim cikti = girdi baytlari; TUR-C2d
# figur kolu gercek bicimli Production 3MF fikstürünü koşucunun düzleştirmesine AYNEN ulastirir).
SAHTE_KOPRU = r'''
import json, os, shutil, sys
a = sys.argv[1:]; mod = os.environ.get("FAKE_KOPRU", "ok")
open(os.environ["FAKE_LOG"], "a").write(json.dumps(["kopru"] + a[:1]) + "\n")
if a and a[0] == "--olc":
    k = ["acik_kenar=3"] if mod == "olc-kirmizi" or (mod == "tek-kirmizi" and len(a) == 2) else []
    print(json.dumps({"kabul_kusurlari": k})); sys.exit(1 if k else 0)
if mod == "girdi":
    sys.stderr.write("GIRDI HATASI: sahte\n"); sys.exit(2)
if mod == "aynen":
    shutil.copyfile(a[0], a[1]); sys.exit(0)
shutil.copyfile(a[0], a[1]); open(a[1], "ab").write(b"ONARILDI"); sys.exit(0)
'''
HAM_3MF = b"PK\x03\x04HAM"
# Sahte kopru `kopru_uret.py min-hesapla --kategori <kod> --girdi-mh <yol>` (TeKiN sozlesmesi): FAKE_MIN (vars. 10)
# -> {"min_mm", "neden"}; FAKE_MIN=yok -> rc 2 (yanit yok). Cagriyi FAKE_LOG'a yazar.
SAHTE_MIN = r'''
import json, os, sys
a = sys.argv[1:]
open(os.environ["FAKE_LOG"], "a").write(json.dumps(["min-hesapla", a[a.index("--kategori") + 1]]) + "\n")
m = os.environ.get("FAKE_MIN", "10")
if m == "yok":
    sys.exit(2)
print(json.dumps({"min_mm": float(m), "neden": "sahte"}))
'''

# Sahte tekin-ortak ureteci (G1/G2 CLI: --girdi <uretec json> --cikti <dizin> -> uretec.3mf + onizleme.png
# + ozet.json). Aldigi JSON'u FAKE_TEKIN_LOG'a yazar; extruder sayisi = girdideki renk alani sayisi
# (FAKE_TEKIN_EXTRUDER zorlar). FAKE_TEKIN_RET dolu -> stderr "RET: <metin>" rc 2.
SAHTE_TEKIN = r'''
import json, os, struct, sys, zipfile, zlib
a = sys.argv[1:]; g = json.load(open(a[a.index("--girdi") + 1], encoding="utf-8")); c = a[a.index("--cikti") + 1]
open(os.environ["FAKE_TEKIN_LOG"], "a", encoding="utf-8").write(json.dumps(g, ensure_ascii=False, sort_keys=True) + "\n")
if os.environ.get("FAKE_TEKIN_RET"):
    sys.stderr.write("RET: " + os.environ["FAKE_TEKIN_RET"] + "\n"); sys.exit(2)
L = 0.0
# G4 (kopru-15) olcu alanlari en_mm/dis_cap_mm/cap_mm/yukseklik_mm; onceki G2/S2 anahtarlari
# ONCE denenir (geriye uyumlu). saksi cap_mm.
for k in ("genislik_mm", "plaket_mm", "uzun_kenar_mm", "yuz_mm", "en_mm", "dis_cap_mm",
          "cap_mm", "boru_cap_mm", "u_aralik_mm", "yukseklik_mm"):
    if isinstance(g.get(k), (int, float)):
        L = float(g[k]); break
# Extruder = renk alani sayisi; liste (yapboz `renkler`) her ogesi bir extruder.
n = int(os.environ.get("FAKE_TEKIN_EXTRUDER") or 0) or max(1, sum(len(v) if isinstance(v, list) else 1
                                                                 for k, v in g.items() if k.startswith("renk")))
os.makedirs(c)
ms = "<config>" + "".join('<part id="%d"><metadata key="extruder" value="%d"/></part>' % (i + 1, i + 1) for i in range(n)) + "</config>"
G = L * float(os.environ.get("FAKE_TEKIN_GEO") or 1.0)
vx = "".join('<vertex x="%g" y="%g" z="%g"/>' % (x, y, zz) for x in (0, G) for y in (0, G * 0.5) for zz in (0, 3))
with zipfile.ZipFile(os.path.join(c, "uretec.3mf"), "w") as z:
    z.writestr("3D/3dmodel.model", '<model unit="millimeter"><resources><object id="1" name="govde" type="model">'
               '<mesh><vertices>' + vx + '</vertices></mesh></object></resources><build><item objectid="1"/></build></model>')
    z.writestr("Metadata/model_settings.config", ms)
def ch(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
ham = b"".join(b"\0" + b"\x80" * 1100 for _ in range(4))
open(os.path.join(c, "onizleme.png"), "wb").write(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", 1100, 4, 8, 0, 0, 0, 0)) + ch(b"IDAT", zlib.compress(ham)) + ch(b"IEND", b""))
oz = {"surum": "sahte", "sizdirmaz": True, "olcu_mm": [float(os.environ.get("FAKE_TEKIN_KUTU") or L), round(L * 0.5, 3), 3.0], "ucgen_sayisi": 24,
      "hacim_mm3": {"a": 1000.0, "toplam": 1000.0}}
if "genislik_mm" not in g and "plaket_mm" not in g:
    oz["uzun_kenar_mm"] = L  # NOMINAL; kosucu uzun kenari 3MF geometrisinden olcer (FAKE_TEKIN_GEO)
json.dump(oz, open(os.path.join(c, "ozet.json"), "w"))
'''

# Sahte figur_kulak (dosya girdili; TUR-C2a): --girdi FIGUR DOSYASI (JSON degil); baytlari + argv TEKIN_LOG'a.
SAHTE_FIGUR = SAHTE_TEKIN.replace(
    'g = json.load(open(a[a.index("--girdi") + 1], encoding="utf-8"))',
    'g = {"uzun_kenar_mm": 40.0, "figur_girdi": open(a[a.index("--girdi") + 1], "rb").read().decode("latin-1"),'
    ' "argv": [x if x.startswith("-") or "/" not in x else os.path.basename(x) for x in a]}').replace(
    # TUR-C2d K2: FAKE_FIGUR_RET_TEPE / _SIRT -> yalniz o konumla cagrilinca "RET: <metin>" rc 2; ozet `kulak.konum`.
    'if os.environ.get("FAKE_TEKIN_RET"):',
    'kn = a[a.index("--konum") + 1] if "--konum" in a else "tepe"\n'
    'if os.environ.get("FAKE_FIGUR_RET_" + kn.upper()):\n'
    '    sys.stderr.write("RET: " + os.environ["FAKE_FIGUR_RET_" + kn.upper()] + "\\n"); sys.exit(2)\n'
    'if os.environ.get("FAKE_TEKIN_RET"):').replace(
    '"hacim_mm3": {"a": 1000.0, "toplam": 1000.0}}',
    '"hacim_mm3": {"a": 1000.0, "toplam": 1000.0}, "kulak": {"konum": kn}}')
assert SAHTE_FIGUR.count("FAKE_FIGUR_RET_") == 2 and '"kulak": {"konum": kn}' in SAHTE_FIGUR


def uretim_3mf(govde=1):
    """GERCEK saglayici onarim bicimi (TUR-C2c kok neden): kok model YALNIZ `<component p:path=...>` (Production),
    mesh alt dosyada. 10 mm kup; bilesen donusumu x*2 (20x10x10), build donusumu z etrafinda 90° (-> 10x20x10) +
    oteleme. govde>1 -> ayni bilesene ikinci build ogesi (iki govde). Kucuk (<2 KB), testin icinde uretilir."""
    import io
    import zipfile
    v = [(x, y, z) for x in (0, 10) for y in (0, 10) for z in (0, 10)]
    yuz = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    ucgen = [u for a, b, c, d in yuz for u in ((a, b, c), (a, c, d))]
    ns = 'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"'
    pns = 'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06"'
    alt = ('<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" %s><resources><object id="1" type="model">'
           '<mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object></resources><build/></model>' %
           (ns, "".join('<vertex x="%d" y="%d" z="%d"/>' % p for p in v),
            "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % u for u in ucgen)))
    ogeler = "".join('<item objectid="2" transform="0 1 0 -1 0 0 0 0 1 %d 7 3" p:printable="1"/>' % (100 + 50 * n)
                     for n in range(govde))
    kok = ('<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" %s %s requiredextensions="p"><resources>'
           '<object id="2" type="model"><components><component p:path="/3D/Objects/object_1.model" objectid="1" '
           'transform="2 0 0 0 1 0 0 0 1 5 5 5"/></components></object></resources><build>%s</build></model>' %
           (ns, pns, ogeler))
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')
        z.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships><Relationship Target="/3D/3dmodel.model" '
                   'Id="r0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
        z.writestr("3D/3dmodel.model", kok)
        z.writestr("3D/Objects/object_1.model", alt)
    return b.getvalue()


def stl_ozet(bayt):
    """Ikili STL -> (ucgen sayisi, min kose, kutu) — fikstur beklentisi koşucudan BAGIMSIZ okunur."""
    n = struct.unpack("<I", bayt[80:84])[0] if len(bayt) >= 84 else -1
    if n < 0 or len(bayt) != 84 + 50 * n:
        return None
    p = [struct.unpack("<3f", bayt[84 + 50 * i + 12 + 12 * j:84 + 50 * i + 24 + 12 * j]) for i in range(n) for j in range(3)]
    mn = tuple(round(min(q[c] for q in p), 4) for c in range(3))
    mx = tuple(round(max(q[c] for q in p), 4) for c in range(3))
    return n, mn, tuple(round(mx[c] - mn[c], 4) for c in range(3))

# Manifestin kopru uretecleri -> sahte tekin (esle adi URETEC_CLI'daki gibi; kosucu turun KENDI eslemesini once secer).
TEKIN_ESLE = {"yapboz_uret": "yapboz", "isimlik_uret": "isimlik"}
# CEKIRDEK vakalar (T1-T12, T25, T32-T34) icin D turu: bust (rolyef_uret) sahte §1 "sozlesme" CLI'ina yonlenir.
CEKIRDEK_TUR = "bust"
CEKIRDEK_URETEC = "rolyef_uret"

SAHTE_URETEC = r'''
import json, os, struct, sys, zlib
a = sys.argv[1:]; g = json.load(open(a[a.index("--girdi") + 1])); c = a[a.index("--cikti") + 1]
open(os.environ["FAKE_LOG"], "a").write(json.dumps(["uretec"]) + "\n")
mod = os.environ.get("FAKE_URETEC_MOD", "ok")
if mod == "red":
    sys.stderr.write("RED olcu-aralik: sahte\n"); sys.exit(2)
if mod == "ariza":
    sys.stderr.write("HATA: sahte ariza\n"); sys.exit(1)
os.makedirs(c)
open(os.path.join(c, "model.3mf"), "wb").write(b"PK\x03\x04" + b"\0" * 40)
def png(w, h):
    def ch(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    ham = b"".join(b"\0" + b"\x80" * w for _ in range(h))
    return b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)) + ch(b"IDAT", zlib.compress(ham)) + ch(b"IEND", b"")
open(os.path.join(c, "onizleme.png"), "wb").write(png(1200, 4))
o = {"sozlesme": 1, "kategori": g["kategori"], "uzun_kenar_mm": float(g["olcu_mm"]),
     "kutu_mm": {"x": float(g["olcu_mm"]), "y": 100.0, "z": 3.0}, "renk_sayisi": 2,
     "sizdirmaz": mod != "sizdirmaz", "ucgen": 12, "hacim_cm3": 1.0, "alt_kenar_mm": 3.0,
     "parcalar": [], "girdi_sha256": "", "model_sha256": ""}
json.dump(o, open(os.path.join(c, "olcu.json"), "w"))
'''


def png_gri(w, h):
    def ch(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    ham = b"".join(b"\0" + bytes(((x * 255) // max(1, w - 1) + y) % 256 for x in range(w)) for y in range(h))
    return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)) +
            ch(b"IDAT", zlib.compress(ham)) + ch(b"IEND", b""))


def _foto():
    return png_gri(64, 48)


# Kopru hermetik vakalari: girdi (§2 zarfi) -> uretece giden BEKLENEN JSON (bagimsiz yazilmis).
# yapboz: form AYNEN + surgu olcusu uzun_kenar_mm + palet renk1..N -> renkler listesi (AYNI sira).
# anahtarlik: form AYNEN + surgu olcusu genislik_mm + anahtarlik:true sabiti + plaka/yazi -> renk_plaka/renk_yazi.
G2_VAKA = {
    "yapboz": {"olcu": 150, "renkler": {"renk1": "Ahşap", "renk2": "Lacivert"},
               "parametreler": {"satir": 4, "sutun": 5, "tohum": 7, "kabartma_yon": "koyu_yuksek"},
               "dosyalar": {"foto": ("foto.png", _foto)},
               "beklenen": {"gorsel": "foto.png", "uzun_kenar_mm": 150.0, "satir": 4, "sutun": 5, "tohum": 7,
                            "kabartma_yon": "koyu_yuksek", "renkler": ["#C8B89A", "#12294D"]},
               "renk_sayisi": 2, "parcalar": ["renk1", "renk2"]},
    "anahtarlik": {"olcu": 45, "renkler": {"plaka": "Beyaz", "yazi": "Lacivert"},
                   "parametreler": {"satirlar": ["Ayşe"], "yazi_tipi": "script", "hizalama": "orta",
                                    "anahtarlik_kulak_konum": "sag-ust", "kontur_tasma_mm": 2},
                   "beklenen": {"satirlar": ["Ayşe"], "yazi_tipi": "script", "hizalama": "orta",
                                "anahtarlik_kulak_konum": "sag-ust", "kontur_tasma_mm": 2, "genislik_mm": 45.0,
                                "anahtarlik": True, "renk_plaka": "#F2F2F2", "renk_yazi": "#12294D"},
                   "renk_sayisi": 2, "parcalar": ["plaka", "yazi"]},
}


class Ortam:
    def __init__(self, kosucu=KOSUCU, tablo=True):
        self.d = tempfile.mkdtemp(prefix="foto-kosucu-test-")
        self.kosucu = kosucu
        self.db = os.path.join(self.d, "d1.sqlite")
        self.r2 = os.path.join(self.d, "r2")
        self.log = os.path.join(self.d, "wrangler.log")
        os.makedirs(self.r2)
        open(self.log, "w").close()
        self.tekin_log = os.path.join(self.d, "tekin.log")
        open(self.tekin_log, "w").close()
        for ad, icerik in (("wr.py", SAHTE_WRANGLER), ("uretec.py", SAHTE_URETEC), ("tekin.py", SAHTE_TEKIN)):
            with open(os.path.join(self.d, ad), "w") as f:
                f.write(icerik)
        c = sqlite3.connect(self.db)
        with open(SEMA, encoding="utf-8") as f:
            c.executescript(f.read())
        c.commit()
        c.close()
        self.env = dict(os.environ, FAKE_DB=self.db, FAKE_R2=self.r2, FAKE_LOG=self.log, FAKE_TEKIN_LOG=self.tekin_log,
                        FOTO_KOSUCU_WRANGLER="%s %s" % (sys.executable, os.path.join(self.d, "wr.py")),
                        FOTO_KOSUCU_KILIT=os.path.join(self.d, "kilit"),
                        FOTO_KOSUCU_PYTHON=sys.executable)
        # Her D/R ciktisi onarim kapisindan gecer (8 Eki) -> varsayilan sahte kopru (FAKE_KOPRU=ok).
        self.env["FOTO_KOSUCU_JENERATOR"] = self.jen()
        for k in ("FAKE_D1_KAPALI", "FAKE_R2_KAPALI", "FAKE_CAS_KAYBI", "FAKE_URETEC_MOD", "FOTO_KOSUCU_URETEC_TABLO",
                  "FAKE_TEKIN_RET", "FAKE_TEKIN_EXTRUDER", "FAKE_KOPRU", "FAKE_FIGUR_RET_TEPE", "FAKE_FIGUR_RET_SIRT"):
            self.env.pop(k, None)
        if tablo:
            t = os.path.join(self.d, "tablo.json")
            with open(t, "w") as f:
                tablo_ek = {CEKIRDEK_URETEC: {"bicim": "sozlesme",
                                              "komut": [sys.executable, os.path.join(self.d, "uretec.py")]}}
                for u, esle in TEKIN_ESLE.items():
                    tablo_ek[u] = {"bicim": "tekin-ortak", "betik": os.path.join(self.d, "tekin.py"), "esle": esle}
                json.dump(tablo_ek, f)
            self.env["FOTO_KOSUCU_URETEC_TABLO"] = t

    def sql(self, q, *p):
        c = sqlite3.connect(self.db)
        c.row_factory = sqlite3.Row
        r = [dict(x) for x in c.execute(q, p).fetchall()]
        c.commit()
        c.close()
        return r

    def siparis_is(self, olcu=150, deneme=0):
        kalem = {"foto_is": IS, "foto_tur": CEKIRDEK_TUR, "olcu_mm": olcu, "foto_renkler": ["Beyaz", "Siyah"],
                 "foto_secim": {"govde_malzeme": "PLA"}}
        self.sql("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES (?,?,?,?,?)",
                 SIP, GUNCEL0, "odendi", olcu * 1000, json.dumps([kalem]))
        self.sql("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, deneme, tarih, guncel)"
                 " VALUES (?,0,?,?,?,?,?,?,?)", SIP, IS, CEKIRDEK_TUR, olcu, "uretec-bekliyor", deneme, GUNCEL0, GUNCEL0)
        os.makedirs(os.path.join(self.r2, "foto-onizleme"), exist_ok=True)
        with open(os.path.join(self.r2, "foto-onizleme", IS + ".png"), "wb") as f:
            f.write(png_gri(240, 160))

    def onizleme_is(self):
        self.sql("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, son_kontrol)"
                 " VALUES (?,?,?,?,?,?,?)", IS2, CEKIRDEK_TUR, 120, "ab" * 8, GUNCEL0, "uretec-onizleme", 5)
        d = os.path.join(self.r2, "foto-uretec-onizleme", IS2)
        os.makedirs(d)
        with open(os.path.join(d, "girdi.json"), "w") as f:
            json.dump({"sozlesme": 1, "kategori": CEKIRDEK_TUR, "siparis_no": "", "kalem": 0, "olcu_mm": 120,
                       "renkler": {}, "malzemeler": {}, "parametreler": {}, "dosyalar": {"gri_harita": "gri_harita.png"}}, f)
        with open(os.path.join(d, "gri_harita.png"), "wb") as f:
            f.write(png_gri(200, 140))

    def siparis_onizlemeden(self, secim):
        """Siparis oncesi uretec onizlemesine (IS2) bagli odenmis kalem."""
        kalem = {"foto_is": IS2, "foto_tur": CEKIRDEK_TUR, "olcu_mm": 120, "foto_secim": secim}
        self.sql("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES (?,?,?,?,?)",
                 SIP, GUNCEL0, "odendi", 120000, json.dumps([kalem]))
        self.sql("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, deneme, tarih, guncel)"
                 " VALUES (?,0,?,?,?,?,?,?,?)", SIP, IS2, CEKIRDEK_TUR, 120, "uretec-bekliyor", 0, GUNCEL0, GUNCEL0)

    def uretec_onizleme(self, tur, olcu, renkler, parametreler, dosyalar=None, is_no=IS2):
        """Siparis oncesi uretec onizlemesi (foto_isler 'uretec-onizleme') + R2 girdi dizini."""
        self.sql("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, son_kontrol)"
                 " VALUES (?,?,?,?,?,?,?)", is_no, tur, olcu, "ab" * 8, GUNCEL0, "uretec-onizleme", 5)
        d = os.path.join(self.r2, "foto-uretec-onizleme", is_no)
        os.makedirs(d)
        beyan = {}
        for anahtar, (ad, bayt) in (dosyalar or {}).items():
            beyan[anahtar] = ad
            with open(os.path.join(d, ad), "wb") as f:
                f.write(bayt)
        with open(os.path.join(d, "girdi.json"), "w", encoding="utf-8") as f:
            json.dump({"sozlesme": 1, "kategori": tur, "siparis_no": "", "kalem": 0, "olcu_mm": olcu,
                       "renkler": renkler, "malzemeler": {}, "parametreler": parametreler, "dosyalar": beyan},
                      f, ensure_ascii=False)
        return d

    def tekin_girdileri(self):
        with open(self.tekin_log, encoding="utf-8") as f:
            return [json.loads(s) for s in f if s.strip()]

    def uretec_sayisi(self):
        with open(self.log) as f:
            return sum(1 for s in f if json.loads(s) == ["uretec"])

    def kos(self, *arg, **ek):
        env = dict(self.env, **ek)
        p = subprocess.run([sys.executable, self.kosucu] + list(arg), capture_output=True, text=True, env=env,
                           timeout=600)
        son = (p.stdout.strip().splitlines() or [""])[-1]
        return p.returncode, son, p.stdout + p.stderr

    def yazimlar(self):
        n = 0
        with open(self.log) as f:
            for s in f:
                a = json.loads(s)
                if a[:3] == ["r2", "object", "put"]:
                    n += 1
                elif a[:2] == ["d1", "execute"] and not a[a.index("--command") + 1].startswith("SELECT"):
                    n += 1
        return n

    def r2_put(self):
        with open(self.log) as f:
            return sum(1 for s in f if json.loads(s)[:3] == ["r2", "object", "put"])

    def uretim(self):
        r = self.sql("SELECT asama, sebep, deneme, guncel FROM foto_uretim")
        return r[0] if r else None

    def onarim_is(self, ham=True, tur="figur", olcu=130, girdi=None):
        """Saglayici zinciri bitti: foto_uretim 'onarim-bekliyor' + R2 model.ham.3mf (8 Eki onarim kuyrugu).
        girdi: onizleme girdi.json (TUR-C2a figur cesidi: {cesit, uretec}); None = eski is (dosya YOK).
        ham: True = sahte HAM_3MF baytlari; bayt dizisi = o baytlar (TUR-C2d Production 3MF fiksturu)."""
        self.sql("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, deneme, tarih, guncel)"
                 " VALUES (?,0,?,?,?,?,?,?,?)", SIP, IS, tur, olcu, "onarim-bekliyor", 0, GUNCEL0, GUNCEL0)
        if girdi is not None:
            os.makedirs(os.path.join(self.r2, "foto-uretec-onizleme", IS), exist_ok=True)
            with open(os.path.join(self.r2, "foto-uretec-onizleme", IS, "girdi.json"), "w") as f:
                json.dump(girdi, f)
        if ham:
            os.makedirs(os.path.join(self.r2, "foto", SIP, "0"), exist_ok=True)
            with open(os.path.join(self.r2, "foto", SIP, "0", "model.ham.3mf"), "wb") as f:
                f.write(ham if isinstance(ham, bytes) else HAM_3MF)

    def jen(self, kopru=True):
        """Sahte uretec deposu; kopru=False -> uc_mf_onar.py YOK."""
        d = os.path.join(self.d, "jen" if kopru else "jen-bos")
        os.makedirs(os.path.join(d, "jeneratorler", "foto"), exist_ok=True)
        if kopru:
            with open(os.path.join(d, "jeneratorler", "foto", "uc_mf_onar.py"), "w") as f:
                f.write(SAHTE_KOPRU)
        os.makedirs(os.path.join(d, "jeneratorler", "kopru"), exist_ok=True)
        with open(os.path.join(d, "jeneratorler", "kopru", "kopru_uret.py"), "w") as f:
            f.write(SAHTE_MIN)
        return d

    def model(self):
        y = os.path.join(self.r2, "foto", SIP, "0", "model.3mf")
        return open(y, "rb").read() if os.path.isfile(y) else None

    def kapat(self):
        shutil.rmtree(self.d, ignore_errors=True)


def vakalar(kosucu):
    """Donus {vaka: (gecti, aciklama)}."""
    s = {}

    def vaka(ad, fn):
        o = Ortam(kosucu)
        try:
            gecti, ac = fn(o)
        except Exception as e:  # vaka cokerse KIRMIZI
            gecti, ac = False, "istisna %s: %s" % (type(e).__name__, e)
        finally:
            o.kapat()
        s[ad] = (gecti, ac)

    def t1(o):
        rc, son, _ = o.kos("--uygula")
        return rc == 1 and son == "HAL=BOS rc=1" and o.yazimlar() == 1, "%s yazim=%d" % (son, o.yazimlar())

    def t2(o):
        o.siparis_is()
        rc, son, _ = o.kos("--uygula")
        u = o.uretim()
        dosyalar = sorted(os.listdir(os.path.join(o.r2, "foto", SIP, "0"))) if os.path.isdir(
            os.path.join(o.r2, "foto", SIP, "0")) else []
        return (rc == 0 and son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir"
                and dosyalar == ["model.3mf", "olcu.json", "onizleme.png"]), "%s %s %s" % (son, u, dosyalar)

    def t3(o):
        o.siparis_is()
        rc, son, _ = o.kos("--uygula", FAKE_URETEC_MOD="red")
        u = o.uretim()
        return (rc == 0 and son == "HAL=ISLEDI uretildi=0 red=1 ariza=0 rc=0" and u["asama"] == "elle"
                and u["sebep"] == "uretec-red:olcu-aralik" and o.r2_put() == 0), "%s %s" % (son, u)

    def t4(o):
        o.siparis_is()
        izler = []
        for _ in range(3):
            rc, son, _ = o.kos("--uygula", FAKE_URETEC_MOD="ariza")
            u = o.uretim()
            izler.append((son, u["asama"], u["deneme"]))
        ok = (izler[0][1:] == ("uretec-bekliyor", 1) and izler[1][1:] == ("uretec-bekliyor", 2) and
              izler[2][1] == "elle" and o.uretim()["sebep"] == "uretec-ariza" and
              izler[2][0] == "HAL=ISLEDI uretildi=0 red=0 ariza=1 rc=0" and o.r2_put() == 0)
        return ok, str(izler)

    def t5(o):
        o.siparis_is()
        rc, son, _ = o.kos("--uygula", FAKE_URETEC_MOD="sizdirmaz")
        u = o.uretim()
        return (u["asama"] == "elle" and u["sebep"] == "sizdirmaz-degil" and o.r2_put() == 0
                and son == "HAL=ISLEDI uretildi=0 red=1 ariza=0 rc=0"), "%s %s put=%d" % (son, u, o.r2_put())

    def t6(o):
        o.siparis_is()
        rc, son, _ = o.kos("--uygula", FAKE_CAS_KAYBI="1")
        u = o.uretim()
        return (u["asama"] == "hazir" and u["guncel"] == "baska-kosucu" and o.r2_put() == 0 and
                not os.path.isdir(os.path.join(o.r2, "foto"))), "%s %s put=%d" % (son, u, o.r2_put())

    def t7(o):
        o.siparis_is()
        once = o.uretim()
        rc1, son1, _ = o.kos("--uygula", FAKE_D1_KAPALI="1")
        ara = o.uretim()
        # R2 kapali: kiralama olur, gri harita indirilemez -> jeton geri verilir, satir ayni
        rc2, son2, _ = o.kos("--uygula", FAKE_R2_KAPALI="1")
        sonra = o.uretim()
        return (rc1 == 4 and son1 == "HAL=OLCULEMEDI sebep=d1 rc=4" and ara == once and
                rc2 == 4 and son2 == "HAL=OLCULEMEDI sebep=r2 rc=4" and sonra == once and o.r2_put() == 0), \
            "%s | %s | %s -> %s" % (son1, son2, once, sonra)

    def t8(o):
        o.siparis_is()
        fd = os.open(o.env["FOTO_KOSUCU_KILIT"], os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            rc, son, _ = o.kos("--uygula")
        finally:
            os.close(fd)
        rc2, son2, _ = o.kos("--uygula")  # kilit birakildi (sahibi oldu) -> devralinir
        return (rc == 3 and son == "HAL=KILITLI rc=3" and rc2 == 0 and son2.startswith("HAL=ISLEDI uretildi=1")), \
            "%s | %s" % (son, son2)

    def t9(o):
        o.siparis_is()
        once = o.uretim()
        rc, son, cikti = o.kos()
        return (rc == 0 and son == "HAL=PLAN is=1 rc=0" and o.yazimlar() == 0 and o.uretim() == once and
                "PLAN R2 PUT pruvo-ozel/foto/%s/0/model.3mf" % SIP in cikti), "%s yazim=%d" % (son, o.yazimlar())

    def t10(o):
        o.onizleme_is()
        rc, son, _ = o.kos("--uygula")
        r = o.sql("SELECT asama, hata, hazir_tarih FROM foto_isler WHERE is_no = ?", IS2)[0]
        d = os.path.join(o.r2, "foto-uretec-onizleme", IS2)
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and r["asama"] == "onizleme-hazir" and
                r["hazir_tarih"] != "" and sorted(os.listdir(d)) ==
                ["girdi.json", "gri_harita.png", "model.3mf", "olcu.json", "onizleme.png"]), "%s %s" % (son, r)

    def t12(o):
        # KOPYA KOLU: onizleme -> onizleme-hazir (uretec 1) -> ayni girdili siparis -> uretec KOSMAZ.
        o.onizleme_is()
        o.kos("--uygula")
        o.siparis_onizlemeden({})
        rc, son, cikti = o.kos("--uygula")
        u = o.uretim()
        d = os.path.join(o.r2, "foto", SIP, "0")
        m0 = os.path.join(o.r2, "foto-uretec-onizleme", IS2, "model.3mf")
        ayni = (sorted(os.listdir(d)) == ["model.3mf", "olcu.json", "onizleme.png"] if os.path.isdir(d) else False) and \
            open(os.path.join(d, "model.3mf"), "rb").read() == open(m0, "rb").read()
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
                o.uretec_sayisi() == 1 and "KOPYA" in cikti and ayni), "%s %s uretec=%d ayni=%s" % (
                    son, u, o.uretec_sayisi(), ayni)

    def t12b(o):
        # SHA FARKLI: siparis secimi onizleme girdisinden farkli -> kopya YOK, uretec yeniden koşar.
        o.onizleme_is()
        o.kos("--uygula")
        o.siparis_onizlemeden({"govde_malzeme": "PETG"})  # bust malzeme secimi -> girdi sha farkli
        rc, son, cikti = o.kos("--uygula")
        u = o.uretim()
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
                o.uretec_sayisi() == 2 and "KOPYA" not in cikti), "%s %s uretec=%d" % (son, u, o.uretec_sayisi())

    def t11(o):
        log = os.path.join(o.d, "k.log")
        with open(log, "w") as f:
            f.write("x" * 6 * 1024 * 1024)
        with open(log + ".1", "w") as f:
            f.write("eski")
        rc, son, _ = o.kos("--log", log)
        b1 = os.path.getsize(log)
        b2 = os.path.getsize(log + ".1")
        return (son == "HAL=BOS rc=1" and b1 < 1024 and b2 == 6 * 1024 * 1024 and
                not os.path.exists(log + ".2")), "log=%d log.1=%d" % (b1, b2)

    # ---- tekin-ortak koprusu (yapboz, anahtarlik): uretece giden JSON BIREBIR beklenen.
    def t13(kod):
        def fn(o):
            x = G2_VAKA[kod]
            dosya = {k: (ad, b() if callable(b) else b) for k, (ad, b) in x.get("dosyalar", {}).items()}
            d = o.uretec_onizleme(kod, x["olcu"], x["renkler"], x["parametreler"], dosya)
            rc, son, cikti = o.kos("--uygula")
            r = o.sql("SELECT asama, hata FROM foto_isler WHERE is_no = ?", IS2)[0]
            gelen = o.tekin_girdileri()
            g = dict(gelen[0]) if len(gelen) == 1 else {}
            if "gorsel" in g:
                g["gorsel"] = os.path.basename(g["gorsel"])
            olcu = json.load(open(os.path.join(d, "olcu.json"))) if os.path.isfile(os.path.join(d, "olcu.json")) else {}
            b = struct.unpack(">II", open(os.path.join(d, "onizleme.png"), "rb").read()[16:24]) \
                if os.path.isfile(os.path.join(d, "onizleme.png")) else (0, 0)
            ok = (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and r["asama"] == "onizleme-hazir" and
                  g == x["beklenen"] and olcu.get("renk_sayisi") == x["renk_sayisi"] and
                  olcu.get("uzun_kenar_mm") == float(x["olcu"]) and olcu.get("kategori") == kod and
                  re.match(r"^[0-9a-f]{64}$", olcu.get("girdi_sha256") or "") is not None and max(b) >= 1024 and
                  [p["ad"] for p in olcu.get("parcalar", [])] == x["parcalar"])
            fark = {k: (g.get(k), v) for k, v in x["beklenen"].items() if g.get(k) != v}
            fark.update({k: (g[k], None) for k in g if k not in x["beklenen"]})
            return ok, "%s %s fark=%s renk_sayisi=%s uk=%s" % (son, r, fark, olcu.get("renk_sayisi"),
                                                               olcu.get("uzun_kenar_mm"))
        return fn

    def anahtarlik_onizleme(o, renkler=None, parametreler=None, is_no=IS2):
        x = G2_VAKA["anahtarlik"]
        return o.uretec_onizleme("anahtarlik", x["olcu"], x["renkler"] if renkler is None else renkler,
                                 x["parametreler"] if parametreler is None else parametreler, is_no=is_no)

    def yapboz_onizleme(o, olcu=None, renkler=None, is_no=IS2):
        x = G2_VAKA["yapboz"]
        return o.uretec_onizleme("yapboz", x["olcu"] if olcu is None else olcu,
                                 x["renkler"] if renkler is None else renkler, x["parametreler"],
                                 {"foto": ("foto.png", _foto())}, is_no=is_no)

    def t14(o):
        anahtarlik_onizleme(o, {"plaka": "Beyaz", "yazi": "Gri"})
        rc, son, _ = o.kos("--uygula", FAKE_TEKIN_RET="plaka/yazi renk kontrasti 2.10 < 3.0 (acik/koyu cift sec)")
        r = o.sql("SELECT asama, hata FROM foto_isler WHERE is_no = ?", IS2)[0]
        return (son == "HAL=ISLEDI uretildi=0 red=1 ariza=0 rc=0" and r["asama"] == "basarisiz" and
                r["hata"] == "uretec-red:kontrast"), "%s %s" % (son, r)

    def t_kosmaz(kurucu, beklenen_hata):
        def fn(o):
            kurucu(o)
            rc, son, _ = o.kos("--uygula")
            r = o.sql("SELECT asama, hata FROM foto_isler WHERE is_no = ?", IS2)[0]
            return (son == "HAL=ISLEDI uretildi=0 red=1 ariza=0 rc=0" and r["asama"] == "basarisiz" and
                    r["hata"] == beklenen_hata and o.tekin_girdileri() == []), "%s %s tekin=%d" % (
                        son, r, len(o.tekin_girdileri()))
        return fn

    def t17(o):
        d = anahtarlik_onizleme(o)
        rc, son, _ = o.kos("--uygula", FAKE_TEKIN_EXTRUDER="3")
        olcu = json.load(open(os.path.join(d, "olcu.json"))) if os.path.isfile(os.path.join(d, "olcu.json")) else {}
        return son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and olcu.get("renk_sayisi") == 3, \
            "%s renk_sayisi=%s" % (son, olcu.get("renk_sayisi"))

    # ---- plaka 300 (manifest PLAKA_MM) · uzun kenar geometriden · yapboz araligi (manifest 100-280).
    def t19(o):
        sonuc = {}
        for kutu in (290, 310):
            no = ("%032x" % kutu)
            yapboz_onizleme(o, is_no=no)
            o.kos("--uygula", FAKE_TEKIN_KUTU=str(kutu))
            r = o.sql("SELECT asama, hata FROM foto_isler WHERE is_no = ?", no)[0]
            sonuc[kutu] = (r["asama"], r["hata"])
        return (sonuc[290][0] == "onizleme-hazir" and sonuc[310][0] != "onizleme-hazir" and
                "plaka-disi" in (sonuc[310][1] or "")), "%s" % sonuc

    def t20(o):
        # ozet NOMINAL uzun kenari 150 der, 3MF geometrisi 147 (%2) -> kosucu geometriyi olcer, tolerans RED.
        yapboz_onizleme(o)
        o.kos("--uygula", FAKE_TEKIN_GEO="0.98")
        r = o.sql("SELECT asama, hata FROM foto_isler WHERE is_no = ?", IS2)[0]
        return (r["asama"] != "onizleme-hazir" and "uzun-kenar-tolerans" in (r["hata"] or "")), "%s" % (r,)

    def t21(o):
        sonuc = {}
        for olcu in (280, 290):
            no = ("%032x" % olcu)
            yapboz_onizleme(o, olcu=olcu, is_no=no)
            o.kos("--uygula")
            r = o.sql("SELECT asama, hata FROM foto_isler WHERE is_no = ?", no)[0]
            sonuc[olcu] = (r["asama"], r["hata"])
        return (sonuc[280][0] == "onizleme-hazir" and sonuc[290][0] != "onizleme-hazir" and
                "olcu-aralik-disi" in (sonuc[290][1] or "")), "%s" % sonuc

    for kod in G2_VAKA:
        vaka("T13-" + kod, t13(kod))
    # V5 (TUR-B ⑧): eski yapboz isi `uzun_kenar_mm` (999, olcu DISI) + `iki_renk` tasir -> rc 0, uretece giden JSON
    # yeni isle BIREBIR (uzun_kenar_mm = olcu_mm, iki_renk YOK).
    def v5(o):
        x = G2_VAKA["yapboz"]
        par = dict(x["parametreler"], uzun_kenar_mm=999, iki_renk=True)
        o.uretec_onizleme("yapboz", x["olcu"], x["renkler"], par, {"foto": ("foto.png", _foto())})
        rc, son, _ = o.kos("--uygula")
        gelen = o.tekin_girdileri()
        g = dict(gelen[0]) if len(gelen) == 1 else {}
        if "gorsel" in g:
            g["gorsel"] = os.path.basename(g["gorsel"])
        return rc == 0 and son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and g == x["beklenen"], \
            "rc=%s %s uretec=%s" % (rc, son, g)
    vaka("V5-ESKI", v5)
    vaka("T19", t19)
    vaka("T20", t20)
    vaka("T21", t21)
    vaka("T14", t14)
    vaka("T16", t_kosmaz(lambda o: anahtarlik_onizleme(o, {"plaka": "Pembe", "yazi": "Siyah"}), "uretec-red:renk"))
    vaka("T17", t17)
    vaka("T18", t_kosmaz(lambda o: anahtarlik_onizleme(o, parametreler={"satirlar": ["Ada"], "renk": "x"}),
                         "uretec-red:parametre"))
    # yapboz paleti (K3c): renk2 secili renk1 bos (sira boslugu) / palet disi bolge -> odenen renk sessizce DUSMEZ.
    vaka("T35", t_kosmaz(lambda o: yapboz_onizleme(o, renkler={"renk2": "Lacivert"}), "uretec-red:renk"))
    vaka("T36", t_kosmaz(lambda o: yapboz_onizleme(o, renkler={"renk1": "Ahşap", "renk5": "Siyah"}),
                         "uretec-red:renk"))
    # ---- ORNEK kolu + hedef (8 Eki 2026; tools/foto-ornek-uc-uca.py zinciri).
    ornek_no = "ORNEK-" + IS2[:12]

    def ornek_uretim(o, tur, olcu):
        o.sql("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, deneme, tarih, guncel)"
              " VALUES (?,0,?,?,?,?,?,?,?)", ornek_no, IS2, tur, olcu, "uretec-bekliyor", 0, GUNCEL0, GUNCEL0)

    def t22(o):
        x = G2_VAKA["anahtarlik"]
        anahtarlik_onizleme(o)
        o.sql("UPDATE foto_isler SET ziyaretci = 'ornek' WHERE is_no = ?", IS2)
        o.kos("--uygula")
        ornek_uretim(o, "anahtarlik", x["olcu"])
        rc, son, cikti = o.kos("--uygula")
        u = o.uretim()
        d = os.path.join(o.r2, "foto", ornek_no, "0")
        dosya = sorted(os.listdir(d)) if os.path.isdir(d) else []
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
                dosya == ["model.3mf", "olcu.json", "onizleme.png"] and "KOPYA" in cikti and
                len(o.tekin_girdileri()) == 1), "%s %s dosya=%s tekin=%d" % (son, u, dosya, len(o.tekin_girdileri()))

    def t23(o):
        # Musteri isi (ziyaretci ozeti) ORNEK numarasiyla URETILEMEZ.
        x = G2_VAKA["anahtarlik"]
        anahtarlik_onizleme(o)
        o.kos("--uygula")
        ornek_uretim(o, "anahtarlik", x["olcu"])
        put0 = o.r2_put()
        rc, son, _ = o.kos("--uygula")
        u = o.uretim()
        return (u["asama"] == "elle" and u["sebep"] == "ornek-gecersiz" and o.r2_put() == put0), "%s %s" % (son, u)

    def t24(o):
        o.kos("--hedef", "onizleme")
        o.kos()
        # Bos kuyrukta her kosum 3 SELECT (siparis + onizleme + onarim kuyrugu, 8 Eki).
        adlar = [a[2] for a in (json.loads(s) for s in open(o.log)) if a[:2] == ["d1", "execute"]]
        return (len(adlar) == 6 and set(adlar[:3]) == {"pruvo-katalog-onizleme"} and
                set(adlar[3:]) == {"pruvo-katalog"}), "%s" % adlar

    def t25(o):
        # Uretec onizlemesi OLMAYAN ornek isi (girdi.json yok): 'hazir' + gri harita -> ORNEK siparis uretilir.
        o.sql("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, son_kontrol)"
              " VALUES (?,?,?,?,?,?,?)", IS2, CEKIRDEK_TUR, 140, "ornek", GUNCEL0, "hazir", 0)
        os.makedirs(os.path.join(o.r2, "foto-onizleme"), exist_ok=True)
        with open(os.path.join(o.r2, "foto-onizleme", IS2 + ".png"), "wb") as f:
            f.write(png_gri(200, 140))
        ornek_uretim(o, CEKIRDEK_TUR, 140)
        rc, son, _ = o.kos("--uygula")
        u = o.uretim()
        return son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir", "%s %s" % (son, u)

    vaka("T22", t22)
    vaka("T23", t23)
    # ONARIM KUYRUGU (8 Eki 2026): 'onarim-bekliyor' -> kopru -> --olc -> model.3mf + 'hazir' ya da 'elle'.
    def t27(o):
        o.onarim_is()
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen())
        u = o.uretim()
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
                o.model() == HAM_3MF + b"ONARILDI"), "%s %s" % (son, u)

    def t28(o):
        o.onarim_is()
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen(), FAKE_KOPRU="olc-kirmizi")
        u = o.uretim()
        return (son == "HAL=ISLEDI uretildi=0 red=1 ariza=0 rc=0" and u["asama"] == "elle" and
                u["sebep"] == "onarim-kirmizi" and o.model() is None), "%s %s" % (son, u)

    def t29(o):
        o.onarim_is()
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen(kopru=False))
        u = o.uretim()
        return (son == "HAL=OLCULEMEDI sebep=kopru-yok rc=4" and u["asama"] == "onarim-bekliyor" and
                u["guncel"] == GUNCEL0 and o.model() is None), "%s %s" % (son, u)

    def t30(o):
        o.onarim_is(ham=False)
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen())
        u = o.uretim()
        return (u["asama"] == "elle" and u["sebep"] == "onarim-ham-yok" and o.model() is None), "%s %s" % (son, u)

    def t31(o):
        o.onarim_is()
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen(), FAKE_KOPRU="girdi")
        u = o.uretim()
        return (u["asama"] == "elle" and u["sebep"] == "onarim-girdi-hatasi" and o.model() is None), "%s %s" % (son, u)

    # D/R CIKTISINA AYNI KAPI (8 Eki): tek dosya --olc kirmizi -> kopru -> gecerse onarilmis model + yeni sha.
    def t32(o):
        o.siparis_is()
        rc, son, _ = o.kos("--uygula", FAKE_KOPRU="tek-kirmizi")
        u = o.uretim()
        d = os.path.join(o.r2, "foto", SIP, "0")
        model = open(os.path.join(d, "model.3mf"), "rb").read() if os.path.isfile(os.path.join(d, "model.3mf")) else b""
        olcu = json.load(open(os.path.join(d, "olcu.json"))) if os.path.isfile(os.path.join(d, "olcu.json")) else {}
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
                model.endswith(b"ONARILDI") and olcu.get("model_sha256") == hashlib.sha256(model).hexdigest() and
                sorted(os.listdir(d)) == ["model.3mf", "olcu.json", "onizleme.png"]), "%s %s" % (son, u)

    def t33(o):
        o.siparis_is()
        rc, son, _ = o.kos("--uygula", FAKE_KOPRU="olc-kirmizi")
        u = o.uretim()
        return (u["asama"] == "elle" and u["sebep"] == "onarim-kirmizi" and
                not os.path.isdir(os.path.join(o.r2, "foto", SIP))), "%s %s" % (son, u)

    def t34(o):
        o.siparis_is()
        rc, son, _ = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen(kopru=False))
        u = o.uretim()
        return (son == "HAL=OLCULEMEDI sebep=kopru-yok rc=4" and u["asama"] == "uretec-bekliyor" and
                u["guncel"] == GUNCEL0), "%s %s" % (son, u)

    vaka("T24", t24)
    vaka("T25", t25)
    vaka("T32", t32)
    vaka("T33", t33)
    vaka("T34", t34)
    vaka("T27", t27)
    vaka("T28", t28)
    vaka("T29", t29)
    vaka("T30", t30)
    vaka("T31", t31)

    # FIGUR CESIDI (TUR-C2a): onarim sonrasi girdi.json `uretec` (= manifest foto_kolu.uretec) -> figur_kulak
    # (sahte: onarilmis model --girdi, --konum tepe) -> kulakli model.3mf. Girdi yok (eski is) -> T27 AYNEN (V7).
    # TUR-C2d K1: onarim ciktisi GERCEK bicimli Production 3MF (kok yalniz p:path bileseni) -> koşucu tek govde
    # ikili STL'e duzlestirir (donusumler uygulanmis, min 0) -> figur_kulak --girdi figur.stl.
    def figur_ortami(o, **girdi):
        o.onarim_is(tur="anahtarlik", olcu=45, ham=uretim_3mf(girdi.pop("govde", 1)),
                    girdi=dict({"cesit": "figur", "uretec": "figur_kulak"}, **girdi))
        jen = o.jen()
        with open(os.path.join(jen, "jeneratorler", "foto", "figur_kulak.py"), "w") as f:
            f.write(SAHTE_FIGUR)
        return jen

    def figur_cagrilari(o):
        log = [json.loads(x) for x in open(o.tekin_log, encoding="utf-8") if x.strip()]
        return [x for x in log if "figur_girdi" in x]

    def t60(o):
        jen = figur_ortami(o, sozlesme=1, kategori="anahtarlik", olcu_mm=45, dosyalar={}, parametreler={})
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=jen, FAKE_KOPRU="aynen")
        u = o.uretim()
        fg = figur_cagrilari(o)
        m = o.model() or b""
        oz = stl_ozet(fg[0]["figur_girdi"].encode("latin-1")) if len(fg) == 1 else None
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and len(fg) == 1 and
                oz == (12, (0.0, 0.0, 0.0), (10.0, 20.0, 10.0)) and
                fg[0]["argv"][:2] == ["--konum", "tepe"] and "figur.stl" in fg[0]["argv"] and m.startswith(b"PK") and
                m != uretim_3mf() and "konum=tepe" in c), \
            "%s %s stl=%s fg=%s" % (son, u, oz, [x.get("argv") for x in fg])

    # figur_kulak red (rc 2, >50 mm) -> 'elle' uretec-red:anahtarlik-boyut, model YAZILMAZ.
    # TUR-C2d K2: >50 mm ret sinifinda tepe -> sirt dususu YOK (uretec TEK kez cagrilir).
    def t61(o):
        jen = figur_ortami(o)
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=jen, FAKE_KOPRU="aynen",
                           FAKE_TEKIN_RET="figur uzun kenar 62 mm > 50 mm")
        u = o.uretim()
        fg = figur_cagrilari(o)
        return (u["asama"] == "elle" and u["sebep"] == "uretec-red:anahtarlik-boyut" and o.model() is None and
                [x["argv"][:2] for x in fg] == [["--konum", "tepe"]]), "%s %s fg=%s" % (son, u, [x["argv"][:2] for x in fg])

    # girdi.json'da uretec manifestin foto_kolu.uretec'i DEGIL -> fail-closed 'elle' uretec-uyusmaz.
    def t62(o):
        o.onarim_is(tur="anahtarlik", olcu=45, girdi={"cesit": "figur", "uretec": "isimlik_uret"})
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen())
        u = o.uretim()
        return (u["asama"] == "elle" and u["sebep"] == "uretec-uyusmaz" and o.model() is None), "%s %s" % (son, u)

    # TUR-C2c OLCUM ARACI --kanit-dizin: figur ureteci ozet.json + onizleme.png kopyasi <dizin>/<siparis>/ (bayt AYNI
    # uretecin yazdigi); karar/R2 T60 ile AYNI. Bayraksiz T60 kanit YAZMAZ (launchd yolu degismez).
    def t63(o):
        jen = figur_ortami(o)
        kd = os.path.join(o.d, "kanit")
        rc, son, c = o.kos("--uygula", "--kanit-dizin", kd, FOTO_KOSUCU_JENERATOR=jen, FAKE_KOPRU="aynen")
        u = o.uretim()
        k = os.path.join(kd, SIP)
        dosyalar = sorted(os.listdir(k)) if os.path.isdir(k) else []
        oz = json.load(open(os.path.join(k, "ozet.json"))) if "ozet.json" in dosyalar else {}
        pv = open(os.path.join(k, "onizleme.png"), "rb").read(8) if "onizleme.png" in dosyalar else b""
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
                dosyalar == ["onizleme.png", "ozet.json"] and oz.get("surum") == "sahte" and
                pv == b"\x89PNG\r\n\x1a\n" and (o.model() or b"").startswith(b"PK")), "%s %s kanit=%s" % (son, u, dosyalar)

    # TUR-C2d K2: uretec `kulak yerlesmez (tepe)` -> AYNI iste bir kez sirt -> hazir; kullanilan konum is satirinda
    # (`konum=sirt`) + kanit ozet.json `kulak.konum`.
    def t64(o):
        jen = figur_ortami(o)
        kd = os.path.join(o.d, "kanit")
        rc, son, c = o.kos("--uygula", "--kanit-dizin", kd, FOTO_KOSUCU_JENERATOR=jen, FAKE_KOPRU="aynen",
                           FAKE_FIGUR_RET_TEPE="kulak yerlesmez (tepe): 151 aday tarandi")
        u = o.uretim()
        fg = figur_cagrilari(o)
        oz = os.path.join(kd, SIP, "ozet.json")
        k = (json.load(open(oz)).get("kulak") or {}) if os.path.isfile(oz) else {}
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
                [x["argv"][:2] for x in fg] == [["--konum", "tepe"], ["--konum", "sirt"]] and
                fg[0]["figur_girdi"] == fg[1]["figur_girdi"] and "konum=sirt" in c and k.get("konum") == "sirt" and
                (o.model() or b"").startswith(b"PK")), "%s %s fg=%s kulak=%s" % (son, u, [x["argv"][:2] for x in fg], k)

    # Tepe + sirt ikisi de reddederse mevcut yol AYNEN: 'elle' uretec-red:anahtarlik-boyut, model YAZILMAZ.
    def t65(o):
        jen = figur_ortami(o)
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=jen, FAKE_KOPRU="aynen",
                           FAKE_FIGUR_RET_TEPE="kulak yerlesmez (tepe): 151 aday tarandi",
                           FAKE_FIGUR_RET_SIRT="kulak yerlesmez (sirt): 40 aday tarandi")
        u = o.uretim()
        fg = figur_cagrilari(o)
        return (u["asama"] == "elle" and u["sebep"] == "uretec-red:anahtarlik-boyut" and o.model() is None and
                [x["argv"][:2] for x in fg] == [["--konum", "tepe"], ["--konum", "sirt"]] and "konum=sirt" in c), \
            "%s %s fg=%s" % (son, u, [x["argv"][:2] for x in fg])

    # K1: duzlestirmede birden cok govde -> 'elle' uretec-red:genel (sessiz birlestirme YOK), uretec CAGRILMAZ.
    def t66(o):
        jen = figur_ortami(o, govde=2)
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=jen, FAKE_KOPRU="aynen")
        u = o.uretim()
        return (u["asama"] == "elle" and u["sebep"] == "uretec-red:genel" and o.model() is None and
                figur_cagrilari(o) == [] and "cok govdeli (2 govde)" in c), "%s %s" % (son, u)

    # SAGLIK DAMGASI (10 Eki): K1 --uygula BOS turu foto_ayar.kosucu_son_tik = taze ISO (+ guncel ms) yazar ·
    # K2 KURU kip (bos ve is varken) damga YAZMAZ · K1b OLCULEMEDI turu damga yazmaz (bayat damga = cevrimdisi).
    def damga(o):
        r_ = o.sql("SELECT deger, guncel FROM foto_ayar WHERE anahtar = 'kosucu_son_tik'")
        return r_[0] if r_ else None

    def k1(o):
        once = time.time()
        rc, son, _ = o.kos("--uygula")
        d = damga(o)
        try:
            t = datetime.strptime(d["deger"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc).timestamp()
        except (TypeError, ValueError):
            t = None
        return (son == "HAL=BOS rc=1" and d is not None and t is not None and once - 2 <= t <= time.time() + 2
                and abs(d["guncel"] / 1000.0 - t) < 2), "%s damga=%s" % (son, d)

    def k1b(o):
        rc, son, _ = o.kos("--uygula", FAKE_D1_KAPALI="1")
        return son.startswith("HAL=OLCULEMEDI") and damga(o) is None, "%s damga=%s" % (son, damga(o))

    def k2(o):
        rc, son, _ = o.kos()
        o.siparis_is()
        rc2, son2, _ = o.kos()
        return (son == "HAL=BOS rc=1" and son2 == "HAL=PLAN is=1 rc=0" and damga(o) is None and
                o.yazimlar() == 0), "%s | %s damga=%s" % (son, son2, damga(o))

    vaka("K1", k1)
    vaka("K1b", k1b)
    vaka("K2", k2)
    vaka("T60", t60)
    vaka("T61", t61)
    vaka("T62", t62)
    vaka("T63", t63)
    vaka("T64", t64)
    vaka("T65", t65)
    vaka("T66", t66)
    for ad, fn in (("T1", t1), ("T2", t2), ("T3", t3), ("T4", t4), ("T5", t5), ("T6", t6), ("T7", t7),
                   ("T8", t8), ("T9", t9), ("T10", t10), ("T11", t11), ("T12", t12), ("T12b", t12b)):
        vaka(ad, fn)
    foto_kolu_vakalari(kosucu, s)
    return s


# ANAHTARLIK FOTO KOLU (anahtarlik-foto; 10 Eki figur_kulak, TeKiN kopru kaydi): hermetik — esleme / komut / red kodu /
# yazi kolu ayrimi kosucu fonksiyonlarindan, kopru kaydi agactaki SABIT kopyadan. T44 (V7) GERCEK figur_kulak.py'yi
# 60 mm kup STL ile kosar (uretec deposu ya da trimesh yoksa OLCULEMEDI -> KIRMIZI sayilir, yesil denmez).
ANAHTARLIK_BOYUT_CUMLE = ("Bu fotoğraftan anahtarlık boyutunda bir parça çıkmadı; daha sade bir fotoğraf ya da "
                          "kısa bir yazı deneyin.")


def _kup_stl(yol, kenar):
    """Kenar mm'lik eksen hizali kup (ikili STL, 12 ucgen, watertight, pozitif koordinat)."""
    k = float(kenar)
    v = [(x, y, z) for x in (0, k) for y in (0, k) for z in (0, k)]
    yuz = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    ucgen = [u for a, b, c, d in yuz for u in ((a, b, c), (a, c, d))]
    with open(yol, "wb") as f:
        f.write(b"\0" * 80 + struct.pack("<I", len(ucgen)))
        for u in ucgen:
            f.write(struct.pack("<3f", 0, 0, 0))
            for i in u:
                f.write(struct.pack("<3f", *v[i]))
            f.write(b"\0\0")


def foto_kolu_vakalari(kosucu, s):
    import importlib.util
    import re as _re

    def dene(ad, fn):
        try:
            s[ad] = fn()
        except Exception as e:  # vaka cokerse KIRMIZI
            s[ad] = (False, "istisna %s: %s" % (type(e).__name__, e))
    sp = importlib.util.spec_from_file_location("kosucu_foto_kolu_%d" % id(s), kosucu)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    kok = os.path.dirname(os.path.dirname(os.path.abspath(kosucu)))
    t = m.manifest_oku()["anahtarlik"]
    cli = m.cli_tablosu()
    d = tempfile.mkdtemp(prefix="foto-kolu-vaka-")
    try:
        with open(os.path.join(d, "figur.3mf"), "wb") as f:
            f.write(b"PK\x03\x04")
        with open(os.path.join(d, "figur.stl"), "w", encoding="ascii") as f:
            f.write("solid x\nendsolid x\n")
        zarf = {"dosyalar": {"figur": "figur.3mf"}, "parametreler": {}}

        def t40():
            fn = m.esle_fonksiyonu(t, cli.get("figur_kulak"))
            u, b = fn(zarf, d, {}) if fn else ({}, None)
            us, _ = m.esle_anahtarlik_foto(dict(zarf, dosyalar={"figur": "figur.stl"}), d, {})
            eski = [k for k in cli if "plaket_kulak" in k]
            return (fn is m.esle_anahtarlik_foto and u == {"figur": os.path.join(d, "figur.3mf"), "konum": "tepe"}
                    and b == [] and us["figur"] == os.path.join(d, "figur.stl") and not eski,
                    "fn=%s u=%s us=%s eski=%s" % (getattr(fn, "__name__", fn), u, us, eski))

        def t41():
            g = cli.get("figur_kulak") or {}
            u, _ = m.esle_anahtarlik_foto(dict(zarf, parametreler={"figur_kulak_konum": "sirt"}), d, {})
            k1 = m.dosya_girdili_komut(g, u, "PY", "/JEN", "/HAM")
            k0 = m.dosya_girdili_komut(g, m.esle_anahtarlik_foto(zarf, d, {})[0], "PY", "/JEN", "/HAM")
            b = ["PY", "/JEN/jeneratorler/foto/figur_kulak.py"]
            p = os.path.join(d, "figur.3mf")
            try:  # yazi kolunun konumu (sol-ust) figure GECMEZ
                m.esle_anahtarlik_foto(dict(zarf, parametreler={"figur_kulak_konum": "sol-ust"}), d, {})
                red = None
            except m.KopruRed as e:
                red = str(e)
            return (k1 == b + ["--konum", "sirt", "--girdi", p, "--cikti", "/HAM"] and
                    k0 == b + ["--konum", "tepe", "--girdi", p, "--cikti", "/HAM"] and red == "parametre",
                    "k1=%s k0=%s red=%s" % (k1, k0, red))

        def t42():
            kod = m.ret_kodu("RET: figur uzun kenar 55.00 mm > 50 mm (max 50 mm uzun kenar)")
            kod2 = m.ret_kodu("RET: kulak dahil uzun kenar 61.00 mm > 60 mm (konum=tepe, kulak=(1.00,2.00,3.00))")
            kod3 = m.ret_kodu("RET: kulak yerlesmez (tepe): 12 aday tarandi, hicbiri delik >= 3.5 mm govde disi")
            with open(os.path.join(kok, "foto-uretim-veri.js"), encoding="utf-8") as f:
                veri = f.read()
            metin = _re.findall(r'"anahtarlik-boyut": "([^"]*)"', veri)
            return (kod == kod2 == kod3 == "anahtarlik-boyut" and metin == [ANAHTARLIK_BOYUT_CUMLE],
                    "kod=%s kod2=%s kod3=%s metin=%s" % (kod, kod2, kod3, metin))

        def t44():
            jen = t44_jenerator()
            g = cli.get("figur_kulak") or {}
            if t44_ci_atlar():
                return True, "ATLANDI uretec-deposu-yok (CI: kardes depo checkout YOK; yerelde OLCULUR) %s" % jen
            if not os.path.isfile(os.path.join(jen, g.get("betik") or "-")):
                return False, "OLCULEMEDI uretec-deposu-yok %s" % jen
            _kup_stl(os.path.join(d, "buyuk.stl"), 60)
            u, _ = m.esle_anahtarlik_foto(dict(zarf, dosyalar={"figur": "buyuk.stl"}), d, {})
            ham = os.path.join(d, "ham")
            komut = m.dosya_girdili_komut(g, u, sys.executable, jen, ham)
            p = subprocess.run(komut, capture_output=True, text=True, timeout=300, cwd=jen)
            satir = (p.stderr.strip().splitlines() or [""])[-1]
            kod = m.ret_kodu(satir)
            with open(os.path.join(kok, "foto-uretim-veri.js"), encoding="utf-8") as f:
                metin = _re.findall(r'"anahtarlik-boyut": "([^"]*)"', f.read())
            return (p.returncode == 2 and kod == "anahtarlik-boyut" and metin == [ANAHTARLIK_BOYUT_CUMLE],
                    "rc=%s kod=%s satir=%s" % (p.returncode, kod, satir[:160]))

        def t43():
            fn = m.esle_fonksiyonu(t, cli.get("isimlik_uret"))
            return (fn is m.esle_anahtarlik and not (cli.get("isimlik_uret") or {}).get("dosya_girdisi"),
                    "fn=%s" % getattr(fn, "__name__", fn))
        for ad, fn in (("T40", t40), ("T41", t41), ("T42", t42), ("T43", t43), ("T44", t44)):
            dene(ad, fn)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def t44_jenerator():
    return os.environ.get("FOTO_KOSUCU_JENERATOR") or os.path.expanduser("~/dev/pruvo-jenerator")


def t44_ci_atlar():
    """T44 GERCEK figur_kulak.py'yi (PRIVATE kardes depo) kosar. deploy.yml serit-a3 o depoyu checkout ETMEZ ->
    yalniz CI'da (GITHUB_ACTIONS=true) ve betik yoksa ATLANDI. Yerelde depo yoksa T44 KIRMIZI kalir (OLCULEMEDI);
    nobet.yml bu testi KOSMAZ, yani olcum yerel/pre-push kolundadir (10 Eki: serit-a3 bu yuzden yayini durdurdu)."""
    return (os.environ.get("GITHUB_ACTIONS") == "true"
            and not os.path.isfile(os.path.join(t44_jenerator(), "jeneratorler", "foto", "figur_kulak.py")))


MUTANTLAR = {
    "M1": ('    if o.get("sizdirmaz") is not True:\n        return "sizdirmaz-degil"\n', "", {"T5"}),
    "M2": ("    if not uygula:\n", "    if False:\n", {"T9", "K2"}),
    # SAGLIK DAMGASI: damga yazimi kalkarsa onizleme hazirlayicisi hep "cevrimdisi" gorunur (K1; T1 tek yazim).
    "MK1": ("            damga_yaz(yaz)\n", "            pass\n", {"K1", "T1"}),
    "M3": ('    if n != 1:\n        yaz("CAS %s kiralanamadi', '    if False:\n        yaz("CAS %s kiralanamadi', {"T6"}),
    "M4": ("DENEME_TAVANI = 3\n", "DENEME_TAVANI = 99\n", {"T4"}),
    "M5": ("            d1(geri_ver_sql(i, jeton))\n", "            pass\n", {"T7", "T34"}),
    "M6": ("    if onceki != sha:\n", "    if False:\n", {"T12b"}),
    "M7": ('    if i["kuyruk"] != "siparis" or not i.get("onizleme_kaynakli"):\n        return None\n    os.makedirs',
           '    if True:\n        return None\n    os.makedirs', {"T12", "T22"}),  # T22: ORNEK kolu da kopya koluna baglanir
    # tekin-ortak koprusu (yapboz + anahtarlik)
    "M8": ("    return renk_hex[ad]\n", "    return \"#F2F2F2\"\n", {"T13-yapboz", "T13-anahtarlik", "V5-ESKI"}),
    # (eski M9 qr olcu alani -> anahtarlik sabiti) kopru `cagri.sabit` anahtarlik:true dusurse uretec PLAKA modunda kosar.
    "M9": ('    u["anahtarlik"] = True\n', "    pass\n", {"T13-anahtarlik"}),
    # (eski M10 muhur olcu alani -> yapboz olcu alani) surgu olcusu yanlis alana yazilirsa uretec varsayilani (150) basar.
    "M10": ('    u["uzun_kenar_mm"] = float(g["olcu_mm"])\n', '    u["genislik_mm"] = float(g["olcu_mm"])\n',
            {"T13-yapboz", "V5-ESKI"}),
    "M11": ('    (r"kontrast", "kontrast"),\n', "", {"T14"}),
    "M12": ('"renk_sayisi": uc_mf_extruder_sayisi(os.path.join(cikti, "model.3mf")),',
            '"renk_sayisi": len(bolgeler),', {"T17"}),
    "M13": ('        if any(k not in form for k in (girdi.get("parametreler") or {})):\n            raise KopruRed("parametre")\n',
            "", {"T18"}),
    # plaka 300 tek kaynak · uzun kenar geometriden · yapboz araligi
    # T21: yapboz 280 (aralik ici) kutusu 280 > 250 -> o da KIRMIZI.
    "M14": ("0 < k[e] <= plaka_mm() for e in", "0 < k[e] <= 250 for e in", {"T19", "T21"}),
    "M15": ("0 < k[e] <= plaka_mm() for e in", "0 < k[e] <= 9999 for e in", {"T19"}),
    "M16": ('    uk = uc_mf_uzun_kenar(os.path.join(cikti, "model.3mf"), oz)\n',
            '    uk = oz.get("uzun_kenar_mm") or max(kutu[0], kutu[1])\n', {"T20"}),
    "M17": ('<= i["olcu_mm"] <= a.get("en_cok", 0)):\n        return "olcu-aralik-disi"',
            '<= i["olcu_mm"] <= 99999):\n        return "olcu-aralik-disi"', {"T21"}),
    "M18": ('    if i.get("is_ziyaretci") != ORNEK_ZIYARETCI or ', "    if ", {"T23"}),
    "M19": ('    D1_AD, R2_KOVA, HEDEF = db.group(1), kova.group(1), "onizleme"', '    HEDEF = "onizleme"', {"T24"}),
    # (eski M20 kutu / M31 saksi -> kopru turleri) turun KENDI eslemesi ESLEMELER'den silinirse: anahtarlik
    # uretecin `esle`ine (isimlik, plaka modu) duser; yapboz eslemesiz kalir (uretec-bicimi RED).
    "M20": ('"yapboz": esle_yapboz, "anahtarlik": esle_anahtarlik,\n', '"yapboz": esle_yapboz,\n',
            # esle_isimlik form alanlarini (anahtarlik_kulak_konum, liste satirlar) tanimaz -> T14/T16/T17 de.
            # T43 (9 Eki foto kolu): yazi kolunun eslemesi esle_anahtarlik degil -> o da KIRMIZI (iddia eklendi).
            {"T13-anahtarlik", "T14", "T16", "T17", "T22", "T43"}),
    "M31": ('"sablon": esle_sablon, "yapboz": esle_yapboz, ', '"sablon": esle_sablon, ',
            {"T13-yapboz", "T19", "T20", "T21", "T35", "T36", "V5-ESKI"}),
    # bolge adi manifestten degil sabit `taban`dan okunursa anahtarlik renkleri duser.
    "M25": ('            u["renk_" + b] = h\n', '            u["renk_taban"] = h\n', {"T13-anahtarlik"}),
    # ONARIM KUYRUGU (8 Eki): olcum atlanirsa kirmizi kopru ciktisi 'hazir' olur.
    "M32": ('        rc, hata, cik = kos(["--olc", ham, cikti])\n', '        rc, hata, cik = 0, "", "{}"\n', {"T28", "T33"}),
    # kopru-yok fail-closed silinirse is kuyrukta kalmaz (python dosya bulamaz -> elle).
    "M33": ('        raise Erisilemedi("kopru-yok")\n', "        pass\n", {"T29", "T34"}),
    # erisim yokken kira geri verilmezse satirin jetonu kayar.
    "M34": ("            d1(geri_ver_sql(i, jeton))  # onarim kuyrugu: kira geri (kopru/R2/D1 yok -> is kuyrukta)\n",
            "            pass\n", {"T29"}),
    # ham dosya yoksa kopru yine kosarsa sebep yanlis kovaya duser.
    # TUR-C2a: koşucu girdi.json `uretec` alanini yok sayarsa figur cesidi kulaksiz teslim edilir (T60).
    # TUR-C2c: --kanit-dizin kopyasi yazilmazsa uc-uca olcum araci kulak olcumlerini goremez (T63).
    "M62": ("                kanit_yaz(i, os.path.dirname(cikti))\n", "                pass\n", {"T63", "T64"}),
    # TUR-C2d K1: duzlestirme kapanirsa (onarilmis 3MF AYNEN uretece) Production bileseni okunmaz (T60) ve cok govde
    # sessizce gecer (T66). K2: dusus kapanirsa tepe reddi 'elle' (T64, T65); dusus her ret sinifina yayilirsa
    # >50 mm reddinde de sirt denenir (T61).
    "M63": ('    hata = figur_duzlestir(model, os.path.join(gd, "figur.stl"))\n',
            '    hata = shutil.copyfile(model, os.path.join(gd, "figur.stl")) and None\n', {"T60", "T66"}),
    "M64": ('FIGUR_KONUM_SIRASI = ("tepe", "sirt")\n', 'FIGUR_KONUM_SIRASI = ("tepe",)\n', {"T64", "T65"}),
    "M65": ("        if not (rc == 2 and TEPE_RED.search(ozet)):\n", "        if not rc == 2:\n", {"T61"}),
    "M60": ('    if not isinstance(g, dict) or "uretec" not in g:\n', "    if True:\n",
            {"T60", "T61", "T62", "T63", "T64", "T65", "T66"}),
    # TUR-C2a: girdi.json zorunlu sayilirsa eski is (dosya yok) 'elle'ye duser (T27 = V7).
    "M61": ('    if not r2_al(ONIZLEME_DIZIN % i["is_no"] + "girdi.json", oy):\n        return None\n',
            '    if not r2_al(ONIZLEME_DIZIN % i["is_no"] + "girdi.json", oy):\n        return ""\n', {"T27"}),
    "M35": ('            karar, sebep, ozet = "elle", "onarim-ham-yok", ""\n',
            "            karar, sebep, ozet = onarim_kapisi(ham, cikti)\n", {"T30"}),
    # D/R ciktisina kapi baglanmazsa kirmizi model teslim edilir (T33) ve kopru yokken is ilerler (T34).
    "M36": ("            sebep = cikti_dogrula(i, t, cikti) or d_kapisi(cikti)\n",
            "            sebep = cikti_dogrula(i, t, cikti)\n", {"T32", "T33", "T34"}),
    # onarilmis modelde olcu.json sha tazelenmezse ④ alanlar=0 olur.
    "M37": ('        olcu["model_sha256"] = hashlib.sha256(f.read()).hexdigest()\n', "        pass\n", {"T32"}),
    # yapboz paleti (K3c): sira boslugu kapisi / palet disi bolge kapisi silinirse odenen renk sessizce kayar/duser.
    "M43": ('        if len(secilen) != pb.index(b):\n            raise KopruRed("renk")\n', "", {"T35"}),
    "M44": ('    if any(b not in pb for b in (g.get("renkler") or {})):\n        raise KopruRed("renk")\n', "", {"T36"}),
    # ANAHTARLIK FOTO KOLU: foto dali / parametre_bayraklari / >50 mm cumlesi / yazi kolu ayrimi.
    "M45": ('    if (g or {}).get("kol") == "foto":\n        return ESLEMELER.get(g.get("esle"))\n', "",
            {"T40", "T60", "T61", "T63", "T64", "T65"}),
    "M46": ("        komut += [pb[ad], str(u[ad])]\n", "        pass\n", {"T41", "T60", "T61", "T64", "T65"}),
    "M47": ('    (r"figur uzun kenar|kulak dahil uzun kenar|kulak yerlesmez", "anahtarlik-boyut"),\n',
            "", {"T42", "T44", "T61", "T65"}),
    # 10 Eki figur_kulak: varsayilan konum tepe; STL girdisi de kabul; eski plaket eslemesi geri gelirse KIRMIZI.
    # TUR-C2d: onarim kolu konumu zarfta ACIK verir (FIGUR_KONUM_SIRASI) -> M50 T60'i artik dusurmez; girdi figur.stl
    # oldugu icin M51 tum onarim figur vakalarini dusurur (olculen kumeler).
    "M50": ('KONUM_VARSAYILAN = "tepe"\n', 'KONUM_VARSAYILAN = "sirt"\n', {"T40", "T41"}),
    "M51": ('not ad.endswith((".3mf", ".stl"))', 'not ad.endswith(".3mf")',
            {"T40", "T44", "T60", "T61", "T63", "T64", "T65"}),
    "M52": ('    "figur_kulak": {"bicim": "tekin-ortak", "betik": "jeneratorler/foto/figur_kulak.py",',
            '    "plaket_kulak": {"bicim": "tekin-ortak", "betik": "jeneratorler/foto/plaket_kulak.py",',
            {"T40", "T41", "T44", "T60", "T61", "T63", "T64", "T65"}),
    "M48": ('"anahtarlik-boyut": "Bu fotoğraftan anahtarlık boyutunda bir parça çıkmadı;',
            '"anahtarlik-boyut": "Bu fotoğraftan parça çıkmadı;', {"T42", "T44"}, "foto-uretim-veri.js"),
    # Yazi kolu gerilemesi: foto dali her ureteci yakalar -> anahtarlik yazi isi esle_isimlik'e duser (T13/T14/...).
    "M49": ('    if (g or {}).get("kol") == "foto":\n', '    if True:\n',
            {"T13-anahtarlik", "T14", "T16", "T17", "T22", "T43"}),
    # TUR-B ⑧: eski alan atilmazsa eski yapboz isi `RED parametre` ile duser.
    "M4-ESKI": ("    eski_alanlari_at(t.get(\"kod\"), girdi)\n", "", {"V5-ESKI"}),
    "M0": ("import argparse\n", "import argparse  # kontrol mutanti\n", set()),
}


def mutant_kos(ad):
    eski, yeni, hedef = MUTANTLAR[ad][:3]
    # 4. oge: mutasyonun hedef dosyasi (varsayilan kosucu; "foto-uretim-veri.js" = manifest bellek kopyasi)
    hedef_dosya = MUTANTLAR[ad][3] if len(MUTANTLAR[ad]) > 3 else None
    with open(os.path.join(KOK, hedef_dosya) if hedef_dosya else KOSUCU, encoding="utf-8") as f:
        kaynak = f.read()
    if kaynak.count(eski) != 1:
        return False, "capa %d kez bulundu" % kaynak.count(eski)
    d = tempfile.mkdtemp(prefix="foto-kosucu-mutant-")
    try:
        os.makedirs(os.path.join(d, "tools"))
        os.makedirs(os.path.join(d, "shop"))
        shutil.copyfile(os.path.join(KOK, "foto-uretim-veri.js"), os.path.join(d, "foto-uretim-veri.js"))
        shutil.copyfile(os.path.join(KOK, "shop", "wrangler.onizleme.toml"), os.path.join(d, "shop", "wrangler.onizleme.toml"))
        os.makedirs(os.path.join(d, "jenerator", "kopru"))
        shutil.copyfile(os.path.join(KOK, "jenerator", "kopru", "kopru_kayitlari.json"),
                        os.path.join(d, "jenerator", "kopru", "kopru_kayitlari.json"))
        yol = os.path.join(d, "tools", "foto-uretec-kosucu.py")
        if hedef_dosya:
            shutil.copyfile(KOSUCU, yol)
            with open(os.path.join(d, hedef_dosya), "w", encoding="utf-8") as f:
                f.write(kaynak.replace(eski, yeni))
        else:
            with open(yol, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(eski, yeni))
        s = vakalar(yol)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    kirmizi = {k for k, (g, _) in s.items() if not g}
    if t44_ci_atlar():  # T44 CI'da olculemez (ATLANDI) -> beklenen kumeden duser; yerelde kume AYNEN
        hedef = set(hedef) - {"T44"}
    return kirmizi == hedef, "kirmizi=%s hedef=%s" % (sorted(kirmizi), sorted(hedef))


# ------------------------------------------------------------------ manifest tutarliligi (G2)
def kosucu_modulu():
    import importlib.util
    sp = importlib.util.spec_from_file_location("foto_uretec_kosucu", KOSUCU)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


# EVREN (K3d, 9 Eki 2026) — manifestteki turler ve motorlari AYNEN; silinen 15 tur burada YOK.
EVREN = {"plaket": "M", "figur": "M", "yapboz": "D", "anahtarlik": "D", "bust": "D"}
# Kopru (TeKiN kaydi) satirlari — manifest bunlarla birebir esit olmali (K3c kopru-manifest-uret ciktisi, mimar
# karari; deger bu dosyada BAGIMSIZ yazilidir, manifestten okunmaz).
G2_SATIR = {
    "yapboz": {
        "alan": {"ad": "Fotoğraftan kabartma yapboz", "girdi": ["foto-1"], "motor": "D", "uretec": "yapboz_uret",
                 "olcu_mm": {"en_az": 100, "en_cok": 280},
                 "fiyat": {"formul": "mm_x_10tl", "adim_mm": 10, "taban_tl": 600, "renk_tavani": 4},
                 "ornek_kanit_izni": ["baski", "render"], "renk_secimi": "palet",
                 "palet_bolgeleri": ["renk1", "renk2", "renk3", "renk4"], "olcu_ekseni": "sabit",
                 "malzemeler": {"govde": ["PLA", "PETG"]}},
        "renk_bolgeleri": [],
        "form": {"uzun_kenar_mm": "sayi", "satir": "sayi", "sutun": "sayi", "tohum": "sayi", "kabartma_yon": "secim"},
        "ornek_render": 1,
        "notu": "Üretim dosyasının görüntüsüdür; fotoğrafın açık-koyu tonları kabartma yüksekliğine çevrilir.",
        # TUR-A (10 Eki): ArTisT birebir durustluk cumlesi.
        "durust": ("Her yapboz parçası tek renktir. Siyah, Beyaz ya da Gri seçersen tüm parçalar o renk olur; Renkli "
                   "seçersen parça renkleri fotoğrafından otomatik belirlenir (en çok 4 renk)."),
    },
    "anahtarlik": {
        "alan": {"ad": "Anahtarlık", "girdi": ["metin"], "motor": "D", "uretec": "isimlik_uret",
                 "olcu_mm": {"en_az": 30, "en_cok": 80},
                 "fiyat": {"formul": "mm_x_10tl", "adim_mm": 5, "taban_tl": 600, "renk_tavani": 2},
                 "ornek_kanit_izni": ["render"], "renk_secimi": None, "palet_bolgeleri": None, "olcu_ekseni": "sabit",
                 "malzemeler": {"govde": ["PLA", "PETG"]}},
        "renk_bolgeleri": ["plaka", "yazi"],
        "form": {"satirlar": "metin", "yazi_tipi": "secim", "hizalama": "secim", "genislik_mm": "sayi",
                 "anahtarlik_kulak_konum": "secim", "kontur_tasma_mm": "sayi"},
        "ornek_render": 1,  # 9 Eki: TeKiN ornegi (anahtarlik-kart-9eki) — K3c'de 0 idi
        # 9 Eki (anahtarlik-foto-kolu): dürüstlük cümlesi ②'de 2× basılıyordu -> render notu AYRI cümle.
        "notu": "Üretim dosyasının görüntüsüdür; yazı, renk ve kulak konumu seçimine göre üretilir.",
        "durust": "Metal halka ve zincir dahil değildir; zincir ya da halka takılan kulakçıklı plastik gövde "
                  "(delik Ø 3,5–4 mm).",
    },
}
RENK_HEX_KARAR = {"Beyaz": "#F2F2F2", "Siyah": "#1A1A1A", "Gri": "#818184", "Lacivert": "#12294D",
                  "Kırmızı": "#B3262E", "Sarı": "#E8B923", "Yeşil": "#2E7D4F", "Mavi": "#2E5E8C", "Ahşap": "#C8B89A"}
# Uretec girdi semalarinin alan adlari (pruvo-jenerator yapboz_uret.SEMA; isimlik_uret.SEMA eksi ANAHTARLIK_YASAK);
# `--gercek` kolu GERCEK uretecle dogrular.
URETEC_ALANLARI = {
    "yapboz": {"gorsel", "uzun_kenar_mm", "satir", "sutun", "tohum", "kabartma_yon", "renkler"},
    "anahtarlik": {"satirlar", "yazi_tipi", "hizalama", "genislik_mm", "renk_plaka", "renk_yazi", "anahtarlik",
                   "anahtarlik_kulak_konum", "kontur_tasma_mm", "anahtarlik_kulak_dis_cap_mm",
                   "anahtarlik_delik_cap_mm"},
}
URETEC_OLCU_ALANI = {"yapboz": "uzun_kenar_mm", "anahtarlik": "genislik_mm"}
URETEC_SABIT = {"yapboz": {}, "anahtarlik": {"anahtarlik": True}}

NODE_MANIFEST = r"""
const vm=require('vm'),fs=require('fs');const k={};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),k,{filename:'foto-uretim-veri.js'});
const F=k.PRUVO_FOTO, o={};
o.turler=F.turler; o.renk_hex=F.RENK_HEX; o.red=F.URETEC_RED_METIN;
o.tarayici_var=Object.prototype.hasOwnProperty.call(F,'TARAYICI_ONIZLEYICI'); o.tarayici=F.TARAYICI_ONIZLEYICI||null;
o.onay_surum=F.onay_surum; o.ornek_turler=F.ornekler.map(x=>x.tur); o.plaka=F.PLAKA_MM;
o.ornek_render=F.ornekler.filter(x=>x.kanit==='render').map(x=>[x.tur,x.render,x.onizleme]);
o.onay_anahtar=Object.keys(F.onay).sort(); o.hak_fn=typeof F.hakGerekir+'/'+typeof F.aktarimGerekir;
o.kol={}; for (const t of F.turler) o.kol[t.kod]=F.kolu(t.kod);
o.red_kontrast=F.uretecRedMetni('uretec-red:kontrast'); o.red_bilinmez=F.uretecRedMetni('uretec-red:yok-boyle');
o.red_genel=F.uretecRedMetni('uretec-red');
const P=(kod,p)=>F.parametreDogrula(kod,p), E=(a,b)=>Object.assign({},a,b);
const an={satirlar:['Ayşe'],yazi_tipi:'script',hizalama:'orta',genislik_mm:45,anahtarlik_kulak_konum:'sol-ust',
          kontur_tasma_mm:1.5};
const yb={uzun_kenar_mm:150,satir:4,sutun:5,tohum:7,kabartma_yon:'koyu_yuksek'};
const ok=P('anahtarlik',an);
o.p={
  an_ok:ok.ok, an_deger:ok.deger?ok.deger.satirlar:null,
  an_3satir:P('anahtarlik',E(an,{satirlar:['a','b','c']})).ok,
  an_4satir:P('anahtarlik',E(an,{satirlar:['a','b','c','d']})).ok,
  an_41:P('anahtarlik',E(an,{satirlar:['x'.repeat(41)]})).ok,
  an_bos_satir:P('anahtarlik',E(an,{satirlar:['Ada','','Kat']})).ok,
  an_kontrol:P('anahtarlik',E(an,{satirlar:['A\u0007']})).ok,
  an_dizgi:P('anahtarlik',E(an,{satirlar:'Ayşe'})).ok,
  an_secim:P('anahtarlik',E(an,{yazi_tipi:'Kalın'})).ok,
  an_plaka_alani:P('anahtarlik',E(an,{plaka_sekli:'oval'})).ok,
  yb_ok:P('yapboz',yb).ok,
  yb_satir9:P('yapboz',E(yb,{satir:9})).ok,
  yb_eski_parca:P('yapboz',E(yb,{parca:'30'})).ok,
  yb_yon:P('yapboz',E(yb,{kabartma_yon:'yan'})).ok,
  silinen_tur:P('isimlik',{}).hata
};
process.stdout.write(JSON.stringify(o));
"""


def manifest_vakalari():
    s = {}
    p = subprocess.run(["node", "-e", NODE_MANIFEST, os.path.join(KOK, "foto-uretim-veri.js")], capture_output=True,
                       text=True)
    if p.returncode != 0:
        return {"V0": (False, "node: " + p.stderr[-300:])}
    m = json.loads(p.stdout)
    tur = {t["kod"]: t for t in m["turler"]}
    hata = []
    evren = {t["kod"]: t.get("motor") for t in m["turler"]}
    if evren != EVREN:
        hata.append("evren=%s" % evren)
    for kod, x in G2_SATIR.items():
        t = tur.get(kod) or {}
        for k, v in x["alan"].items():
            if t.get(k) != v:
                hata.append("%s.%s=%r" % (kod, k, t.get(k)))
        if [b.get("kod") for b in t.get("renk_bolgeleri") or []] != x["renk_bolgeleri"]:
            hata.append("%s.renk_bolgeleri" % kod)
        # Renk tavani = boyanabilir bolge sayisi (palet turunde palet_bolgeleri, aksi renk_bolgeleri).
        if (t.get("fiyat") or {}).get("renk_tavani") != len(t.get("palet_bolgeleri") or t.get("renk_bolgeleri") or [0]):
            hata.append("%s.renk_tavani-bolge" % kod)
        if {a: (sema or {}).get("tip") for a, sema in (t.get("form") or {}).items()} != x["form"]:
            hata.append("%s.form-tipleri" % kod)
        if not all(isinstance(a.get("etiket"), str) and a["etiket"] for a in (t.get("form") or {}).values()):
            hata.append("%s.form.etiket" % kod)
    sat = ((tur.get("anahtarlik") or {}).get("form") or {}).get("satirlar") or {}
    if not (sat.get("liste") is True and sat.get("satir_max") == 3 and sat.get("max") == 40 and sat.get("zorunlu") is True):
        hata.append("anahtarlik.satirlar-liste=%r" % sat)
    s["V1"] = (not hata, "satir: %s" % (hata or "evren 5 tur + 2/2 kopru satiri"))
    hata = [k for k, x in G2_SATIR.items() if (tur.get(k) or {}).get("ornek_notu") != x["notu"] or
            (tur.get(k) or {}).get("durustluk") != x["durust"]]
    bos = [t["kod"] for t in m["turler"] if not t.get("ornek_notu") or not t.get("durustluk")]
    s["V2"] = (not hata and not bos, "metin farki=%s bos=%s" % (hata, bos))
    adlar = sorted({r for t in m["turler"] for b in t.get("renk_bolgeleri") or [] for r in b.get("renkler") or []})
    disarida = [a for a in adlar if a not in m["renk_hex"]]
    s["V3"] = (m["renk_hex"] == RENK_HEX_KARAR and not disarida, "RENK_HEX=%s tabloda-yok=%s" % (
        m["renk_hex"] == RENK_HEX_KARAR, disarida))
    # Tarayici onizleyicisi YOK (litofan silindi): onizleyicili tur 0; D turleri deterministik, M turleri saglayici.
    tarayici = m.get("tarayici") or {}
    tarayicili = [t["kod"] for t in m["turler"] if tarayici.get(t.get("uretec"))]
    kol_yanlis = [k for k, mt in EVREN.items() if m["kol"].get(k) != {"D": "deterministik", "M": "saglayici"}[mt]]
    ornek = {}
    for t_, r_, o_ in m["ornek_render"]:
        ornek.setdefault(t_, []).append((r_, o_))
    eksik = [k for k, x in G2_SATIR.items() if ornek.get(k, []) !=
             [("https://media.pruvo3d.com/foto/ornek/%s-1-render.webp" % k,) * 2] * x["ornek_render"]]
    s["V4"] = (not tarayici and not tarayicili and not kol_yanlis and not eksik,
               "tarayici_onizleyici=%s onizleyicili_tur=%d kol_yanlis=%s render-ornegi-eksik/yanlis=%s" % (
                   "var" if m.get("tarayici_var") else "yok", len(tarayicili), kol_yanlis, eksik))
    # Tek onay kutusu (taslak-2, 7 Eki 20:5x): ayri hak/aktarim metni ve kutu kurali YOK; onay = aydinlatma listesi.
    s["V5"] = (m["onay_anahtar"] == ["aydinlatma"] and m["hak_fn"] == "undefined/undefined"
               and m["onay_surum"] == "2026-10-07-taslak-2",
               "onay_anahtar=%s hak_fn=%s onay_surum=%s" % (m["onay_anahtar"], m["hak_fn"], m["onay_surum"]))
    mod = kosucu_modulu()
    eksik = [kod for _, kod in mod.RET_KALIPLARI if kod not in m["red"]]
    kopru_kod = ["kisa-kenar", "qr-uzun"]
    eksik += [k for k in kopru_kod if k not in m["red"]]
    ret_ok = (mod.ret_kodu("RET: plaka/QR renk kontrasti 1.80 < 4.5 (acik/koyu cift sec)") == "kontrast" and
              mod.ret_kodu("RET: parca kisa kenari 18.0 mm < 24 mm: satir/sutun sayisini azaltin") == "parca" and
              mod.ret_kodu("RET: en ince cizgi 0.512 mm < 0.8 mm (yaziyi buyut: plakayi buyut)") == "metin-sigmadi" and
              mod.ret_kodu("RET: SVG: desteklenmeyen eleman <text> (metin/filter/gorsel/maske/stil yok)") == "svg" and
              mod.ret_kodu("RET: bilinmeyen alan: x") == "genel")
    s["V6"] = ("renkler birbirine çok yakın" in m["red_kontrast"] and m["red_bilinmez"] == m["red"][""] and
               m["red_genel"] == m["red"][""] and not eksik and ret_ok,
               "kontrast=%r eksik=%s ret_kodu=%s" % (m["red_kontrast"][:50], eksik, ret_ok))
    pp = m["p"]
    s["V7"] = (pp["an_ok"] and pp["an_deger"] == ["Ayşe"] and pp["an_3satir"] and not pp["an_4satir"] and
               not pp["an_41"] and not pp["an_bos_satir"] and not pp["an_kontrol"] and not pp["an_dizgi"] and
               not pp["an_secim"] and not pp["an_plaka_alani"] and pp["yb_ok"] and not pp["yb_satir9"] and
               not pp["yb_eski_parca"] and not pp["yb_yon"] and pp["silinen_tur"] == "tur-yok",
               "parametreDogrula=%s" % json.dumps(pp, ensure_ascii=False))
    # V8: her form alaninin HER secenegi uretec semasina eslenir (KopruRed yok, alanlar semada, olcu alani dogru,
    # kopru sabiti var). Esleme = URETIM YOLUNUN secimi (esle_fonksiyonu: turun kendi eslemesi once).
    hata = []
    d = tempfile.mkdtemp(prefix="foto-kosucu-v8-")
    try:
        with open(os.path.join(d, "foto.png"), "wb") as f:
            f.write(png_gri(8, 8))
        tablo = mod.cli_tablosu()
        renk_adlari = list(RENK_HEX_KARAR)
        for kod in G2_SATIR:
            t = tur[kod]
            gtab = tablo.get(t["uretec"]) or {}
            fn = mod.esle_fonksiyonu(t, gtab)
            if gtab.get("bicim") != "tekin-ortak" or fn is not mod.ESLEMELER.get(kod):
                hata.append("%s:tablo" % kod)
                continue
            taban = {}
            for a, sema in t["form"].items():
                taban[a] = {"sayi": sema.get("min"), "secim": (sema.get("secenekler") or [None])[0],
                            "metin": ["Ada"] if sema.get("liste") else "Ada", "bool": False}[sema["tip"]]
            denemeler = [dict(taban)]
            for a, sema in t["form"].items():
                for sec in sema.get("secenekler") or []:
                    denemeler.append(dict(taban, **{a: sec}))
            renkler = {b["kod"]: b["renkler"][0] for b in t["renk_bolgeleri"]}
            renkler.update({b: renk_adlari[i] for i, b in enumerate(t.get("palet_bolgeleri") or [])})
            bolge_kume = {b["kod"] for b in t["renk_bolgeleri"]} | set(t.get("palet_bolgeleri") or [])
            for p_ in denemeler:
                girdi = {"sozlesme": 1, "kategori": kod, "olcu_mm": t["olcu_mm"]["en_cok"], "renkler": renkler,
                         "parametreler": p_, "dosyalar": {"foto": "foto.png"}}
                try:
                    u, bolgeler = fn(girdi, d, m["renk_hex"])
                except mod.KopruRed as e:
                    hata.append("%s:%s->%s" % (kod, json.dumps(p_, ensure_ascii=False), e.kod))
                    continue
                if not set(u) <= URETEC_ALANLARI[kod] or u.get(URETEC_OLCU_ALANI[kod]) != float(t["olcu_mm"]["en_cok"]):
                    hata.append("%s:alan %s" % (kod, sorted(set(u) - URETEC_ALANLARI[kod])))
                if any(u.get(k) != v for k, v in URETEC_SABIT[kod].items()):
                    hata.append("%s:sabit" % kod)
                if not bolgeler or not set(bolgeler) <= bolge_kume:
                    hata.append("%s:bolge %s" % (kod, bolgeler))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    s["V8"] = (not hata, "esleme: %s" % (hata or "2/2 tur, her secenek"))
    # V9 (G2b): plaka siniri TEK kaynak manifest PLAKA_MM=300; kosucu ayni degeri okur (ikinci kopya yok).
    try:
        km = kosucu_modulu().plaka_mm()
    except SystemExit as e:
        km = "DUR: %s" % e
    s["V9"] = (m["plaka"] == 300 and km == 300, "manifest=%s kosucu=%s" % (m["plaka"], km))
    return s


# ------------------------------------------------------------------ GERCEK uretec (CI DISI, G2)
def _foto_ton(w, h):
    """Sentetik ton fotografi (gradyan + acik daire): kisi/marka YOK."""
    def ch(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    satirlar = []
    for y in range(h):
        satirlar.append(b"\0" + bytes(230 if (x - w // 2) ** 2 + (y - h // 2) ** 2 < (h // 5) ** 2
                                      else int(40 + 180 * x / w * (1 - y / (2.0 * h))) for x in range(w)))
    return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)) +
            ch(b"IDAT", zlib.compress(b"".join(satirlar))) + ch(b"IEND", b""))


def gercek_vakalar():
    """Kopru turleri x min/orta/maks (manifest araliklari: yapboz 100-280, anahtarlik 30-80)."""
    foto = ("foto.png", _foto_ton(640, 480))
    v = []
    for olcu, renk, sat, sut in ((100, {"renk1": "Ahşap"}, 3, 4),
                                 (190, {"renk1": "Ahşap", "renk2": "Lacivert"}, 4, 5),
                                 (280, {"renk1": "Beyaz", "renk2": "Kırmızı", "renk3": "Mavi", "renk4": "Siyah"}, 5, 6)):
        v.append(("yapboz", olcu, renk, {"satir": sat, "sutun": sut, "tohum": 1, "kabartma_yon": "acik_yuksek"},
                  {"foto": foto}))
    for olcu, satir, yazi_tipi, kulak, tasma in ((30, ["Ali"], "sans-kalin", "sol-ust", 1.5),
                                                  (45, ["Ayşe"], "script", "sag-ust", 2),
                                                  (80, ["Deniz", "Daire 4"], "sans-kalin", "ust-orta", 3)):
        v.append(("anahtarlik", olcu, {"plaka": "Siyah", "yazi": "Beyaz"},
                  {"satirlar": satir, "yazi_tipi": yazi_tipi, "hizalama": "orta", "anahtarlik_kulak_konum": kulak,
                   "kontur_tasma_mm": tasma}, {}))
    return v


def uc_mf_kutular(yol):
    """3MF'ten BAGIMSIZ olcum: {nesne adi: (min xyz, max xyz)} dunya koordinatinda (component + build donusumu)."""
    z = zipfile.ZipFile(yol)
    xml = z.read([n for n in z.namelist() if n.endswith(".model")][0]).decode()
    nesne = {}
    for m in re.finditer(r'<object\b([^>]*)>(.*?)</object>', xml, re.S):
        oid = re.search(r'\bid="(\d+)"', m.group(1)).group(1)
        ad = (re.search(r'\bname="([^"]*)"', m.group(1)) or [None, oid])[1]
        vs = [tuple(float(c) for c in t) for t in re.findall(
            r'<vertex x="([-0-9.e]+)" y="([-0-9.e]+)" z="([-0-9.e]+)"', m.group(2))]
        komp = [(c.group(1), c.group(2)) for c in re.finditer(
            r'<component\b[^>]*objectid="(\d+)"(?:[^>]*transform="([^"]*)")?', m.group(2))]
        nesne[oid] = (ad, vs, komp)

    def donustur(p, t):
        if not t:
            return p
        a = [float(x) for x in t.split()]
        return (p[0] * a[0] + p[1] * a[3] + p[2] * a[6] + a[9], p[0] * a[1] + p[1] * a[4] + p[2] * a[7] + a[10],
                p[0] * a[2] + p[1] * a[5] + p[2] * a[8] + a[11])

    def noktalar(oid, t=None):
        ad, vs, komp = nesne[oid]
        out = [donustur(p, t) for p in vs]
        for cid, ct in komp:
            out += [donustur(p, t) for p in noktalar(cid, ct)]
        return out

    kutu = {}
    for b in re.finditer(r'<item\b[^>]*objectid="(\d+)"(?:[^>]*transform="([^"]*)")?', xml):
        ps = noktalar(b.group(1), b.group(2))
        if ps:
            kutu[nesne[b.group(1)][0]] = (tuple(min(p[i] for p in ps) for i in range(3)),
                                          tuple(max(p[i] for p in ps) for i in range(3)))
    return kutu


def gercek(json_yolu=None):
    import time
    jen = os.environ.get("FOTO_KOSUCU_JENERATOR") or os.path.expanduser("~/dev/pruvo-jenerator")
    py = os.environ.get("FOTO_KOSUCU_PYTHON") or sys.executable
    if not all(os.path.isfile(os.path.join(jen, "jeneratorler", "foto", b)) for b in ("yapboz_uret.py", "isimlik_uret.py")):
        # Gercek uretec deposu yok -> olculemedi (KIRMIZI/YESIL hukmu verilmez; CI bu kolu KOSMAZ).
        print("GERCEK_KOSUM=OLCULEMEDI sebep=jenerator-yok (%s)" % jen)
        return 4
    mod = kosucu_modulu()
    satirlar, gecen = [], 0
    for kod, olcu, renkler, par, dosyalar in gercek_vakalar():
        o = Ortam(tablo=False)
        try:
            o.env["FOTO_KOSUCU_JENERATOR"] = jen
            o.env["FOTO_KOSUCU_PYTHON"] = py
            d = o.uretec_onizleme(kod, olcu, renkler, par, dosyalar)
            t0 = time.time()
            rc, son, cikti = o.kos("--uygula")
            sure = time.time() - t0
            r = o.sql("SELECT asama, hata FROM foto_isler WHERE is_no = ?", IS2)[0]
            olcu_j = json.load(open(os.path.join(d, "olcu.json"))) if os.path.isfile(os.path.join(d, "olcu.json")) else {}
            px = struct.unpack(">II", open(os.path.join(d, "onizleme.png"), "rb").read()[16:24]) \
                if os.path.isfile(os.path.join(d, "onizleme.png")) else (0, 0)
            bag, birim, sha_ayni = None, None, None
            if os.path.isfile(os.path.join(d, "model.3mf")):
                birim = re.search(r'unit="([a-z]+)"', zipfile.ZipFile(os.path.join(d, "model.3mf")).read(
                    "3D/3dmodel.model").decode()).group(1)
                kutular = uc_mf_kutular(os.path.join(d, "model.3mf"))
                if kod == "yapboz":
                    # Parcalar tablada raf duzeninde: birlesik plaket = 3MF konumu - ozet.parcalar[].tasima_mm.
                    # ozet uretec ayni girdiyle YENIDEN kosularak alinir (determinizm: model sha esit olmali).
                    g = json.load(open(os.path.join(d, "girdi.json"), encoding="utf-8"))
                    u, _ = mod.ESLEMELER["yapboz"](g, d, mod.renk_tablosu())
                    td = tempfile.mkdtemp(prefix="foto-kosucu-gercek-")
                    try:
                        with open(os.path.join(td, "u.json"), "w", encoding="utf-8") as f:
                            json.dump(u, f, ensure_ascii=False, sort_keys=True)
                        subprocess.run([py, os.path.join(jen, "jeneratorler/foto/yapboz_uret.py"), "--girdi",
                                        os.path.join(td, "u.json"), "--cikti", os.path.join(td, "c")],
                                       capture_output=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
                        oz = json.load(open(os.path.join(td, "c", "ozet.json")))
                        sha_ayni = open(os.path.join(td, "c", "uretec.3mf"), "rb").read() == \
                            open(os.path.join(d, "model.3mf"), "rb").read()
                    finally:
                        shutil.rmtree(td, ignore_errors=True)
                    tas = {p["ad"]: p["tasima_mm"] for p in oz.get("parcalar", [])}
                    mn = [min(k[0][i] - tas[a][i] for a, k in kutular.items()) for i in (0, 1)]
                    mx = [max(k[1][i] - tas[a][i] for a, k in kutular.items()) for i in (0, 1)]
                    bag = max(mx[0] - mn[0], mx[1] - mn[1])
                else:
                    mn = [min(k[0][i] for k in kutular.values()) for i in (0, 1)]
                    mx = [max(k[1][i] for k in kutular.values()) for i in (0, 1)]
                    bag = max(mx[0] - mn[0], mx[1] - mn[1])
            uk = olcu_j.get("uzun_kenar_mm")
            ok = (r["asama"] == "onizleme-hazir" and olcu_j.get("sizdirmaz") is True and birim == "millimeter" and
                  isinstance(uk, (int, float)) and abs(uk - olcu) <= olcu * 0.01 and
                  bag is not None and abs(bag - olcu) <= olcu * 0.01 and max(px) >= 1024 and
                  1 <= (olcu_j.get("renk_sayisi") or 0) <= 4 and sha_ayni is not False)
            gecen += 1 if ok else 0
            satirlar.append({"kod": kod, "olcu": olcu, "hukum": "GECTI" if ok else "KIRMIZI", "asama": r["asama"],
                             "hata": r["hata"], "sizdirmaz": olcu_j.get("sizdirmaz"), "uzun_kenar_mm": uk,
                             "bagimsiz_uzun_kenar_mm": round(bag, 3) if bag is not None else None,
                             "sapma_yuzde": round(abs(bag - olcu) / olcu * 100, 3) if bag is not None else None,
                             "kutu_mm": olcu_j.get("kutu_mm"), "renk_sayisi": olcu_j.get("renk_sayisi"),
                             "onizleme_px": list(px), "sure_sn": round(sure, 1), "ucgen": olcu_j.get("ucgen"),
                             "parametreler": par, "uretec_rc_ozet": "" if ok else cikti.strip()[-300:]})
            print("%s %-10s %3d asama=%s hata=%s sizdirmaz=%s uk=%s bagimsiz=%s renk=%s px=%s %.1fs" % (
                "✅" if ok else "❌", kod, olcu, r["asama"], r["hata"] or "-", olcu_j.get("sizdirmaz"), uk,
                round(bag, 3) if bag is not None else None, olcu_j.get("renk_sayisi"), px, sure))
        finally:
            o.kapat()
    print("GERCEK_KOSUM=%d/%d" % (gecen, len(satirlar)))
    if json_yolu:
        with open(json_yolu, "w", encoding="utf-8") as f:
            json.dump(satirlar, f, ensure_ascii=False, indent=1)
    return 0 if gecen == len(satirlar) else 1


def kur_vakalari():
    """K3 KUR ARACI (10 Eki): `--hedef onizleme` plist'i ayri etiket + ayri log + `--hedef onizleme`; bayraksiz
    cikti 10 Eki oncesi plist sozlesmesiyle BAYT-ESIT (canli koşucu gerilemesi 0). Yalniz --kuru (diske yazim 0)."""
    arac = os.path.join(KOK, "tools", "foto-kosucu-kur.py")

    def kuru(*arg):
        p = subprocess.run([sys.executable, arac] + list(arg), capture_output=True, text=True, timeout=60)
        return p.returncode, p.stdout

    rc0, c0 = kuru()
    rc1, c1 = kuru("--hedef", "onizleme")
    # Eski (bayraksiz) sozlesme: 10 Eki oncesi plist_uret AYNEN (etiket/log/argumanlar).
    py = shutil.which("python3") or sys.executable
    eski = {"Label": "com.pruvo.foto-kosucu",
            "ProgramArguments": [py, os.path.join(KOK, "tools", "foto-uretec-kosucu.py"), "--uygula", "--log",
                                 os.path.expanduser("~/Library/Logs/pruvo-foto-kosucu.log")],
            "StartInterval": 120, "RunAtLoad": True, "WorkingDirectory": KOK,
            "EnvironmentVariables": {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONDONTWRITEBYTECODE": "1",
                                     "FOTO_KOSUCU_PYTHON": py,
                                     "CLOUDFLARE_ACCOUNT_ID": "<CLOUDFLARE_ACCOUNT_ID --kur aninda ortamdan>"},
            "StandardOutPath": "/dev/null", "StandardErrorPath": "/dev/null", "ProcessType": "Background"}
    beklenen0 = plistlib.dumps(eski).decode() + "KURU: diske yazim 0 (hedef %s)\n" % os.path.expanduser(
        "~/Library/LaunchAgents/com.pruvo.foto-kosucu.plist")
    try:
        p1 = plistlib.loads(c1[:c1.rindex("</plist>") + len("</plist>")].encode())
    except (ValueError, plistlib.InvalidFileException):
        p1 = {}
    log1 = os.path.expanduser("~/Library/Logs/pruvo-foto-kosucu-onizleme.log")
    a1 = p1.get("ProgramArguments") or []
    ok = (rc0 == 0 and c0 == beklenen0 and rc1 == 0 and p1.get("Label") == "com.pruvo.foto-kosucu-onizleme" and
          a1[-2:] == ["--hedef", "onizleme"] and a1[2:5] == ["--uygula", "--log", log1] and
          p1.get("StartInterval") == 120 and
          c1.rstrip().endswith("(hedef %s)" % os.path.expanduser(
              "~/Library/LaunchAgents/com.pruvo.foto-kosucu-onizleme.plist")))
    return {"K3": (ok, "bayraksiz_bayt_esit=%s onizleme=%s %s" % (c0 == beklenen0, p1.get("Label"), a1[2:]))}


def main():
    if "--gercek" in sys.argv:
        a = sys.argv
        return gercek(a[a.index("--json") + 1] if "--json" in a else None)
    kirmizi = 0
    for ad, (g, ac) in manifest_vakalari().items():
        print("%s %s — %s" % ("✅" if g else "❌", ad, ac[:400]))
        kirmizi += 0 if g else 1
    for ad, (g, ac) in kur_vakalari().items():
        print("%s %s — %s" % ("✅" if g else "❌", ad, ac[:400]))
        kirmizi += 0 if g else 1
    for ad, (g, ac) in vakalar(KOSUCU).items():
        print("%s %s — %s" % ("✅" if g else "❌", ad, ac[:300]))
        kirmizi += 0 if g else 1
    survivor = 0
    # SURE (8 Eki 2026: seri 273 sn, pre-push ayna tavani 300 sn): mutantlar PARALEL kosar. Her mutant kendi
    # tempfile agacinda + her vaka kendi Ortam'inda (ayri SQLite/R2/kilit) -> paylasilan durum yok; anlam AYNI.
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 4)) as h:
        sonuclar = list(h.map(mutant_kos, list(MUTANTLAR)))
    for ad, (g, ac) in zip(MUTANTLAR, sonuclar):
        print("%s %s — %s" % ("✅" if g else "❌ SURVIVOR", ad, ac))
        survivor += 0 if g else 1
    print("VAKA_KIRMIZI=%d SURVIVOR=%d" % (kirmizi, survivor))
    return 1 if kirmizi or survivor else 0


if __name__ == "__main__":
    sys.exit(main())
