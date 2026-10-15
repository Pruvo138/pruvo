#!/usr/bin/env python3
"""FOTO URETEC KOSUCUSU — hermetik kabul testi + mutantlar (tools/foto-uretec-kosucu.py).

HERMETIK: wrangler yerine SAHTE komut (D1 = gecici SQLite, sema tools/d1-sema.sql; R2 = gecici
dizin), uretec yerine SAHTE komut. Gercek D1/R2/ev yolu YOK; her sey tempfile altinda, bitince silinir.

EVREN (K3d, 9 Eki 2026; manifest foto-uretim-veri.js TEK KAYNAK): plaket · figur (motor M, saglayici; bu
kosucunun ISI DEGIL) · bust (D, rolyef_uret) · yapboz (D, yapboz_uret). Silinen 15 tur (litofan, isimlik, qr, logo, ...) testte TUR olarak YOK; tarayici onizleyicisi YOK.

Vakalar (CEKIRDEK tur = bust; uretec sahte §1 "sozlesme" CLI'ina yonlenir): T1 BOS rc=1 · T2 1 is -> ISLEDI +
hazir + 3 dosya R2'de · T3 rc 2 -> elle · T4 ariza x3 -> elle · T5 sizdirmaz:false -> elle, R2 yazimi 0 ·
T6 CAS kaybi -> yazim yok · T7 D1/R2 erisim yok -> OLCULEMEDI rc=4 + satir DEGISMEDI · T8 kilit -> KILITLI
rc=3 · T9 KURU -> yazim 0 · T10 onizleme kuyrugu -> onizleme-hazir · T11 log tavani · T12 KOPYA KOLU
(onizlemeye bagli siparis, ayni girdi sha -> uretec KOSMAZ) · T12b sha farkli -> uretec yeniden koşar.
Mutantlar (kosucu kopyasi gecici dizinde): M1 sizdirmaz · M2 KURU · M3 CAS · M4 deneme tavani · M5 jeton geri ·
M6/M7 kopya kolu · M0 yorum -> 0 kirmizi.
RENK SUTUNU (10 Eki): 'hazir'da foto_uretim.renk_sayisi = uretilen model.3mf extruder sayisi (giris tavani 2 ezilir):
RO3 onarim kolu 3 boya -> 3 · RO4 4 boya -> 4 · RS1 uretec kolu (ORNEK kopya) 3 extruder -> 3;
M-RS-ONARIM / M-RS-SIPARIS / M-RS-SQL.
④ RENDER KOLU (11 Eki, Okan "bu 4 renkli bir figur degil"): RN1 figur hazir -> sahte render araci -> R2
foto-onizleme/<is>-render.webp, bolge renkleri ODENEN renklere esli · RN2 render rc 1 -> karar AYNEN hazir +
RENDER=YOK · RN3 plaket render kolu DEGIL · RN4 `--render` CLI (KURU yazmaz, tanimsiz renk rc 2, --uygula yazar);
M-RN-HOOK / M-RN-PALET / M-RN-KOL / M-RN-KURU.

TEKIN-ORTAK KOPRUSU (yapboz): T13-<kod> sahte tekin uretecine giden JSON BIREBIR beklenen (form
AYNEN + olcu alani + palet/bolge renkleri RENK_HEX) + onizleme-hazir + olcu.json ·
T14 RET "kontrast" -> `uretec-red:kontrast` · T16 tanimsiz renk adi · T18 sema disi parametre · T35 palet sira
boslugu · T36 palet disi bolge -> uretec KOSMAZ · T17 renk_sayisi 3MF'ten OLCULUR · T19 plaka 300 · T20 uzun
kenar geometriden · T21 yapboz araligi · T22/T23 ORNEK kolu.
Manifest tutarliligi (V1-V9, node + kosucu modulu): 1 kopru satiri, metinler AYNEN, renk adlari RENK_HEX'te,
tarayici onizleyicili tur 0, form alanlari uretec semasina eslenir, red metni, parametre dogrulamasi.
`--gercek [--json <yol>]`: CI DISI — 1 GERCEK uretec (yapboz) x min/orta/maks = 3 koşum (sahte D1/R2).
"""
import fcntl
import hashlib
import json
import math
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
# FIGUR ZINCIRI (BaBa 22:3x) sahteleri: TEST'in kendi 3MF dunya-uzun-kenar okuyucusu (koşucudan BAGIMSIZ; Production
# p:path bileseni + donusumler) hem sahte denge'de hem vakalarda kullanilir.
SAHTE_OLC_KOD = r'''
import re, zipfile
def sahte_modeller(yol):
    with zipfile.ZipFile(yol) as z:
        return {n: z.read(n).decode("utf-8") for n in z.namelist() if n.endswith(".model")}
def sahte_uzun(md):
    ns = {}
    for ad, x in md.items():
        for m in re.finditer(r'<object\b[^>]*?\bid="(\d+)"[^>]*>(.*?)</object>', x, re.S):
            vs = [tuple(float(c) for c in v) for v in re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', m.group(2))]
            ks = [(re.search(r'p:path="/?([^"]*)"', k).group(1) if "p:path" in k else ad,
                   re.search(r'objectid="(\d+)"', k).group(1), (re.search(r'transform="([^"]*)"', k) or [0, ""])[1])
                  for k in re.findall(r'<component\b[^>]*>', m.group(2))]
            ns[(ad, m.group(1))] = (vs, ks)
    def tr(ps, t):
        if not t:
            return ps
        a = [float(v) for v in t.split()]
        return [(p[0]*a[0]+p[1]*a[3]+p[2]*a[6]+a[9], p[0]*a[1]+p[1]*a[4]+p[2]*a[7]+a[10], p[0]*a[2]+p[1]*a[5]+p[2]*a[8]+a[11]) for p in ps]
    def pt(k):
        vs, ks = ns.get(k, ([], []))
        out = list(vs)
        for kad, cid, t in ks:
            out += tr(pt((kad, cid)), t)
        return out
    P = []
    for ad, x in md.items():
        for it in re.findall(r'<item\b[^>]*>', x):
            P += tr(pt((ad, re.search(r'objectid="(\d+)"', it).group(1))), (re.search(r'transform="([^"]*)"', it) or [0, ""])[1])
    return max(max(p[e] for p in P) - min(p[e] for p in P) for e in range(3)) if P else None
'''
# Sahte figur_duzelt (TeKiN CLI `--girdi <3mf> --cikti <dizin>` -> duzelt.3mf + tek satir DUZELT=...): FAKE_DUZELT
# ok (vars.; kabuk birlestir = build'de yalniz ILK item, kaide = koklerin x1.1 buyumesi + <!--kaide--> isareti) |
# denge (ayni geometri, rc 2 sebep=denge_kopma: saglayici olcusunde kopma, olcek meselesi) | rc1 | geo (rc 2 kabuk_uzak).
SAHTE_DUZELT = r'''
import json, os, re, sys, zipfile
a = sys.argv[1:]; g = a[a.index("--girdi") + 1]; c = a[a.index("--cikti") + 1]; mod = os.environ.get("FAKE_DUZELT", "ok")
open(os.environ["FAKE_LOG"], "a").write(json.dumps(["duzelt", mod]) + "\n")
if mod == "rc1":
    print("DUZELT=RED sebep=beklenmeyen kaide=- birlestir=-"); sys.exit(1)
if mod == "geo":
    print("DUZELT=RED sebep=kabuk_uzak kaide=yok birlestir=-"); sys.exit(2)
os.makedirs(c, exist_ok=True)
with zipfile.ZipFile(g) as z:
    og = [(zi, z.read(zi.filename)) for zi in z.infolist()]
ilk = [True]
def item(m):
    if ilk[0]:
        ilk[0] = False
        return m.group(0)
    return ""
def buyut(m):
    return 'x="%g" y="%g" z="%g"' % tuple(float(v) * 1.1 for v in m.groups())
with zipfile.ZipFile(os.path.join(c, "duzelt.3mf"), "w") as z:
    for zi, b in og:
        if zi.filename.endswith(".model"):
            x = re.sub(r'<item\b[^>]*/>', item, b.decode("utf-8"))
            if "<vertex" in x:
                x = re.sub(r'x="([^"]+)" y="([^"]+)" z="([^"]+)"', buyut, x).replace("<mesh>", "<!--kaide--><mesh>", 1)
            b = x.encode("utf-8")
        z.writestr(zi, b)
rc = 2 if mod == "denge" else 0
print("DUZELT=%s sebep=%s kaide=ekle birlestir=1" % ("RED" if rc else "OK", "denge_kopma" if rc else "-")); sys.exit(rc)
'''
# Sahte figur_denge (`--girdi <3mf>` -> tek satir DENGE=...): kabuk = build item sayisi (>1 cok_kabuk) ·
# FAKE_DENGE_KAIDE=zorunlu ve <!--kaide--> yok -> devrilme · uzun kenar > FAKE_DENGE_MAX_MM (vars. 1000) -> kopma ·
# FAKE_DENGE=rc1 -> beklenmeyen rc 1. Olculen uzun kenari FAKE_LOG'a yazar.
SAHTE_DENGE = SAHTE_OLC_KOD + r'''
import json, os, sys
a = sys.argv[1:]; g = a[a.index("--girdi") + 1]; md = sahte_modeller(g); L = sahte_uzun(md)
open(os.environ["FAKE_LOG"], "a").write(json.dumps(["denge", round(L, 2)]) + "\n")
if os.environ.get("FAKE_DENGE") == "rc1":
    print("DENGE=RED sebep=beklenmeyen"); sys.exit(1)
x = "".join(md.values()); kabuk = len(re.findall(r"<item\b", x)); mx = float(os.environ.get("FAKE_DENGE_MAX_MM") or 1000)
sebep = ("cok_kabuk" if kabuk > 1 else "devrilme" if os.environ.get("FAKE_DENGE_KAIDE") == "zorunlu" and
         "<!--kaide-->" not in x else "kopma" if L > mx else "-")
print("DENGE=%s sebep=%s pay_mm=9.00 egim_derece=9.0 min_kesit_mm2=99.0 kabuk=%d n=20.0 sigma_varsayim=10 "
      "max_guvenli_mm=%.1f" % ("RED" if sebep != "-" else "OK", sebep, kabuk, mx)); sys.exit(2 if sebep != "-" else 0)
'''
exec(SAHTE_OLC_KOD)
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
# Sahte TeKiN render araci (`hepsi --is IS.json --out DIZIN --emsal PNG --samples N`; tools/foto_kart_render.py):
# is.json'daki 3MF'in filament_colour'unu <out>/<kod>-1-render.webp'e JSON yazar (palet eslemesi testten OLCULUR),
# cagriyi FAKE_LOG'a ["render", samples] yazar. FAKE_RENDER=rc1 -> rc 1, dosya YOK.
SAHTE_RENDER = r'''
import json, os, sys, zipfile
a = sys.argv[1:]
open(os.environ["FAKE_LOG"], "a").write(json.dumps(["render", a[a.index("--samples") + 1]]) + "\n")
if os.environ.get("FAKE_RENDER") == "rc1":
    sys.exit(1)
i = json.load(open(a[a.index("--is") + 1]))[0]; out = a[a.index("--out") + 1]
if a[0] != "hepsi" or not os.path.isfile(a[a.index("--emsal") + 1]) or not os.path.isfile(i["onizleme"]):
    sys.exit(3)
with zipfile.ZipFile(i["3mf"]) as z:
    try:
        fc = json.loads(z.read("Metadata/project_settings.config")).get("filament_colour")
    except KeyError:
        fc = None
os.makedirs(out, exist_ok=True)
open(os.path.join(out, i["kod"] + "-1-render.webp"), "w").write(json.dumps({"filament_colour": fc}))
# gercek arac png kopyasini da yazar (tools/foto_kart_render.py hepsi: <kod>-1-render.png + .webp)
open(os.path.join(out, i["kod"] + "-1-render.png"), "wb").write(b"\x89PNG\r\n\x1a\n" + json.dumps({"filament_colour": fc}).encode())
'''

# ④ ORTAK RENDER SOZLESMESI (TeKiN, 14 Eki): sahte arac — `--model M --renk HEX [--renk2 HEX --bolge2 ad] --arkaplan
# studyo --cikti PNG`; cagriyi FAKE_LOG'a ["render-yeni", renk, renk2, bolge2, model uzantisi, arkaplan] yazar.
SAHTE_RENDER_YENI = r'''
import json, os, sys
a = sys.argv[1:]
g = lambda k: a[a.index(k) + 1] if k in a else ""
open(os.environ["FAKE_LOG"], "a").write(json.dumps(["render-yeni", g("--renk"), g("--renk2"), g("--bolge2"),
    os.path.splitext(g("--model"))[1], g("--arkaplan")]) + "\n")
open(g("--cikti"), "wb").write(b"\x89PNG\r\n\x1a\n" + g("--renk").encode())
'''

# ④ TEK RENK (Okan 14 Eki): sahte Blender — tools/foto-renk-render.py'nin cagirdigi `Blender -b ... -- blender-ic --glb
# --renk HEX --cikti PNG` arayuzu. Cagriyi FAKE_LOG'a ["blender", hex] yazar, --cikti'ya PNG imzali bayt + hex yazar.
# FAKE_BLENDER=rc1 -> rc 1, dosya YOK.
SAHTE_BLENDER = r'''
import json, os, sys
a = sys.argv[1:]
b = a[a.index("--") + 1:] if "--" in a else a
renk = b[b.index("--renk") + 1]; cikti = b[b.index("--cikti") + 1]; glb = b[b.index("--glb") + 1]
open(os.environ["FAKE_LOG"], "a").write(json.dumps(["blender", renk, os.path.isfile(glb)]) + "\n")
if os.environ.get("FAKE_BLENDER") == "rc1":
    sys.exit(1)
open(cikti, "wb").write(b"\x89PNG\r\n\x1a\n" + renk.encode())
print("RENK-IC=OK yassi=0")
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



def uretim_3mf(govde=1, boya=None):
    """GERCEK saglayici onarim bicimi (TUR-C2c kok neden): kok model YALNIZ `<component p:path=...>` (Production),
    mesh alt dosyada. 10 mm kup; bilesen donusumu x*2 (20x10x10), build donusumu z etrafinda 90° (-> 10x20x10) +
    oteleme. govde>1 -> ayni bilesene ikinci build ogesi (iki govde). Kucuk (<2 KB), testin icinde uretilir.
    boya: paint_color dizgeleri listesi -> ucgen n'ye boya[n % len] (BambuStudio boyali figur; None = boyasiz AYNEN)."""
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
            "".join(('<triangle v1="%d" v2="%d" v3="%d" paint_color="%s"/>' % (u + (boya[n % len(boya)],))) if boya
                    else ('<triangle v1="%d" v2="%d" v3="%d"/>' % u) for n, u in enumerate(ucgen))))
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


# Fikstur boya dizgeleri -> yaprak durumlari (TABLO; koşucunun TriangleSelector cozucusunden BAGIMSIZ). "841" = bir
# kenari bolunmus ucgen (durum 1 + durum 2; TeKiN test_figur_kulak.BOYA_TABLO ile ayni dizge).
BOYA_DURUM = {"4": {1}, "8": {2}, "0C": {3}, "1C": {4}, "841": {1, 2}}


def extruder_say(bayt):
    """3MF baytlari -> FARKLI extruder sayisi (koşucudan BAGIMSIZ okuma): model_settings govde extruder'lari; ucgen
    boyasi varsa durum d>=1 -> extruder d (BOYA_DURUM tablosu; tabloda olmayan dizge -> -1). Okunamazsa 0."""
    import io
    import zipfile
    try:
        with zipfile.ZipFile(io.BytesIO(bayt)) as z:
            govde = set(re.findall(r'key="extruder"\s+value="(\d+)"', z.read("Metadata/model_settings.config").decode()))
            boya = [p for n in z.namelist() if n.endswith(".model")
                    for p in re.findall(r'paint_color="([^"]*)"', z.read(n).decode())]
    except (KeyError, zipfile.BadZipFile, UnicodeDecodeError):
        return 0
    if any(p not in BOYA_DURUM for p in boya):
        return -1
    return len({str(d) for p in boya for d in BOYA_DURUM[p]}) if boya else len(govde)


# Manifestin kopru uretecleri -> sahte tekin (esle adi URETEC_CLI'daki gibi; kosucu turun KENDI eslemesini once secer).
TEKIN_ESLE = {"yapboz_uret": "yapboz"}
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
G2_VAKA = {
    "yapboz": {"olcu": 150, "renkler": {"renk1": "Ahşap", "renk2": "Lacivert"},
               "parametreler": {"satir": 4, "sutun": 5, "tohum": 7, "kabartma_yon": "koyu_yuksek"},
               "dosyalar": {"foto": ("foto.png", _foto)},
               "beklenen": {"gorsel": "foto.png", "uzun_kenar_mm": 150.0, "satir": 4, "sutun": 5, "tohum": 7,
                            "kabartma_yon": "koyu_yuksek", "renkler": ["#C8B89A", "#12294D"]},
               "renk_sayisi": 2, "parcalar": ["renk1", "renk2"]},
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
                  "FAKE_TEKIN_RET", "FAKE_TEKIN_EXTRUDER", "FAKE_KOPRU", "FOTO_KOSUCU_URETEC_SURE_SN"):
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
        r = self.sql("SELECT asama, sebep, deneme, guncel, renk_sayisi FROM foto_uretim")
        return r[0] if r else None

    def onarim_is(self, ham=True, tur="figur", olcu=130, girdi=None):
        """Saglayici zinciri bitti: foto_uretim 'onarim-bekliyor' + R2 model.ham.3mf (8 Eki onarim kuyrugu).
        girdi: onizleme girdi.json (R2 foto-uretec-onizleme/<is>/); None = dosya YOK.
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

    def jen(self, kopru=True, zincir=True, render=False):
        """Sahte uretec deposu; kopru=False -> uc_mf_onar.py YOK; zincir=False -> figur_duzelt/figur_denge YOK;
        render=True -> tools/foto_kart_render.py (sahte; ④ render kolu)."""
        d = os.path.join(self.d, ("jen" if kopru else "jen-bos") + ("" if zincir else "-zincirsiz") +
                         ("-render" if render is True else ("-render-" + render if render else "")))
        os.makedirs(os.path.join(d, "jeneratorler", "foto"), exist_ok=True)
        if render:
            os.makedirs(os.path.join(d, "tools"), exist_ok=True)
            with open(os.path.join(d, "tools", "foto_kart_render.py"), "w") as f:
                # render="yeni": TeKiN ORTAK render sozlesmesi (--model --renk [--renk2 --bolge2] --arkaplan --cikti)
                f.write(SAHTE_RENDER_YENI if render == "yeni" else SAHTE_RENDER)
        if kopru:
            with open(os.path.join(d, "jeneratorler", "foto", "uc_mf_onar.py"), "w") as f:
                f.write(SAHTE_KOPRU)
        if zincir:
            for ad, kod in (("figur_duzelt.py", SAHTE_DUZELT), ("figur_denge.py", SAHTE_DENGE)):
                with open(os.path.join(d, "jeneratorler", "foto", ad), "w") as f:
                    f.write(kod)
        os.makedirs(os.path.join(d, "jeneratorler", "kopru"), exist_ok=True)
        with open(os.path.join(d, "jeneratorler", "kopru", "kopru_uret.py"), "w") as f:
            f.write(SAHTE_MIN)
        return d

    def model(self):
        y = os.path.join(self.r2, "foto", SIP, "0", "model.3mf")
        return open(y, "rb").read() if os.path.isfile(y) else None

    def renk_is(self, renk="Gri", glb=True, hata="", is_no=IS):
        """④ TEK RENK: Worker build'i bitirdi -> foto_renk_onizleme 'render-bekliyor' + R2 GLB (glb=False: GLB YOK)."""
        self.sql("INSERT INTO foto_renk_onizleme (is_no, renk, asama, build_gorev, build_olcu, tarih, son_kontrol, hata,"
                 " guncel) VALUES (?,?,?,?,?,?,?,?,?)", is_no, renk, "render-bekliyor", "gorev-renk", 100, GUNCEL0, 5,
                 hata, 5)
        if glb:
            os.makedirs(os.path.join(self.r2, "foto-onizleme"), exist_ok=True)
            with open(os.path.join(self.r2, "foto-onizleme", is_no + "-model.glb"), "wb") as f:
                f.write(b"glTF-sahte-onizleme-modeli")

    def renk_env(self, **ek):
        """Sahte Blender (tools/foto-renk-render.py FOTO_RENK_BLENDER kancasi) + Blender kapisi atlanir (hermetik)."""
        b = os.path.join(self.d, "blender.py")
        with open(b, "w") as f:
            f.write(SAHTE_BLENDER)
        return dict({"FOTO_RENK_BLENDER": "%s %s" % (sys.executable, b), "FOTO_RENK_KAPI_YOK": "1"}, **ek)

    def renk_satiri(self, is_no=IS):
        r = self.sql("SELECT renk, asama, hata FROM foto_renk_onizleme WHERE is_no = ?", is_no)
        return r[0] if r else None

    def blender_cagri(self):
        return [json.loads(x) for x in open(self.log) if json.loads(x)[0] == "blender"]

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

    # ---- tekin-ortak koprusu (yapboz): uretece giden JSON BIREBIR beklenen.
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

    def yapboz_onizleme(o, olcu=None, renkler=None, is_no=IS2, parametreler=None):
        x = G2_VAKA["yapboz"]
        return o.uretec_onizleme("yapboz", x["olcu"] if olcu is None else olcu,
                                 x["renkler"] if renkler is None else renkler,
                                 x["parametreler"] if parametreler is None else parametreler,
                                 {"foto": ("foto.png", _foto())}, is_no=is_no)

    def t14(o):
        yapboz_onizleme(o)
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
        d = yapboz_onizleme(o)
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

    vaka("T16", t_kosmaz(lambda o: yapboz_onizleme(o, renkler={"renk1": "Pembe"}), "uretec-red:renk"))
    vaka("T17", t17)
    vaka("T18", t_kosmaz(lambda o: yapboz_onizleme(o, parametreler=dict(G2_VAKA["yapboz"]["parametreler"], renk="x")),
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
        x = G2_VAKA["yapboz"]
        yapboz_onizleme(o)
        o.sql("UPDATE foto_isler SET ziyaretci = 'ornek' WHERE is_no = ?", IS2)
        o.kos("--uygula")
        ornek_uretim(o, "yapboz", x["olcu"])
        rc, son, cikti = o.kos("--uygula")
        u = o.uretim()
        d = os.path.join(o.r2, "foto", ornek_no, "0")
        dosya = sorted(os.listdir(d)) if os.path.isdir(d) else []
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
                dosya == ["model.3mf", "olcu.json", "onizleme.png"] and "KOPYA" in cikti and
                len(o.tekin_girdileri()) == 1), "%s %s dosya=%s tekin=%d" % (son, u, dosya, len(o.tekin_girdileri()))

    def t23(o):
        # Musteri isi (ziyaretci ozeti) ORNEK numarasiyla URETILEMEZ.
        x = G2_VAKA["yapboz"]
        yapboz_onizleme(o)
        o.kos("--uygula")
        ornek_uretim(o, "yapboz", x["olcu"])
        put0 = o.r2_put()
        rc, son, _ = o.kos("--uygula")
        u = o.uretim()
        return (u["asama"] == "elle" and u["sebep"] == "ornek-gecersiz" and o.r2_put() == put0), "%s %s" % (son, u)

    def t24(o):
        o.kos("--hedef", "onizleme")
        o.kos()
        # Bos kuyrukta her kosum 4 SELECT (siparis + onizleme + onarim kuyrugu, 8 Eki; + ④ tek renk kuyrugu, 14 Eki).
        adlar = [a[2] for a in (json.loads(s) for s in open(o.log)) if a[:2] == ["d1", "execute"]]
        return (len(adlar) == 8 and set(adlar[:4]) == {"pruvo-katalog-onizleme"} and
                set(adlar[4:]) == {"pruvo-katalog"}), "%s" % adlar

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
    # FIGUR ZINCIRI (22:3x) sonrasi onarilmis model AYNEN teslim = plaket kolu (figur turu artik zincire girer):
    # plaket zinciri DEGISMEZ -> duzelt/denge CAGRILMAZ, model bayt-ayni onarim ciktisi.
    def zincir_cagrilari(o):
        return [json.loads(x)[0] for x in open(o.log) if json.loads(x)[0] in ("duzelt", "denge")]

    def t27(o):
        o.onarim_is(tur="plaket")
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen())
        u = o.uretim()
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
                o.model() == HAM_3MF + b"ONARILDI" and zincir_cagrilari(o) == []), \
            "%s %s zincir=%s" % (son, u, zincir_cagrilari(o))

    # FIGUR ZINCIRI (insan · pet · model; BaBa 22:3x): onarim -> figur_duzelt -> olcek (KAIDE DAHIL uzun kenar =
    # siparis olcusu) -> figur_denge. Beklenen uzun kenar testin KENDI okuyucusuyla (sahte_uzun) olculur.
    def zincir_kos(o, olcu, ham=None, **env):
        o.onarim_is(olcu=olcu, ham=ham or uretim_3mf())
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen(), FAKE_KOPRU="aynen", **env)
        m = o.model()
        L = None
        if m:
            y = os.path.join(o.d, "teslim.3mf")
            with open(y, "wb") as f:
                f.write(m)
            L = sahte_uzun(sahte_modeller(y))
            md = sahte_modeller(y)
        else:
            md = {}
        return son, o.uretim(), m, L, "".join(md.values()), zincir_cagrilari(o), c

    def olcu_tutar(L, olcu):
        return L is not None and abs(L - olcu) <= olcu * 0.01

    # FZ1 pet kaidesiz (denge: kaide yoksa devrilme) -> duzelt kaide ekler -> 136 mm OK (pet tavanı 136,5 — TeKiN 792ac60).
    def fz1(o):
        son, u, m, L, x, z, c = zincir_kos(o, 136, FAKE_DENGE_KAIDE="zorunlu", FAKE_DENGE_MAX_MM="136.5")
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
                "<!--kaide-->" in x and olcu_tutar(L, 136) and z == ["duzelt", "denge"] and
                u["renk_sayisi"] == extruder_say(m)), "%s %s L=%s z=%s" % (son, u, L, z)

    # FZ2 arac 5 kabuk -> duzelt birlestirir -> teslim modeli 1 kabuk, 130 mm OK.
    def fz2(o):
        son, u, m, L, x, z, c = zincir_kos(o, 130, ham=uretim_3mf(5), FAKE_DENGE_MAX_MM="300")
        return (u["asama"] == "hazir" and len(re.findall(r"<item\b", x)) == 1 and olcu_tutar(L, 130) and
                "kabuk=1" in c), "%s %s L=%s items=%d" % (son, u, L, len(re.findall(r"<item\b", x)))

    # FZ3 insan 130 mm (tavan 105,4 ustu) -> denge RED kopma -> 'elle' uretec-red:denge-kopma, model YAZILMAZ.
    def fz3(o):
        son, u, m, L, x, z, c = zincir_kos(o, 130, FAKE_DUZELT="denge", FAKE_DENGE_MAX_MM="105.4")
        return (son == "HAL=ISLEDI uretildi=0 red=1 ariza=0 rc=0" and u["asama"] == "elle" and
                u["sebep"] == "uretec-red:denge-kopma" and m is None and z == ["duzelt", "denge"]), \
            "%s %s z=%s" % (son, u, z)

    # FZ4 insan 105 mm (duzelt saglayici olcusunde denge_kopma rc 2 verir; olcekli denge OK) -> 'hazir'.
    def fz4(o):
        son, u, m, L, x, z, c = zincir_kos(o, 105, FAKE_DUZELT="denge", FAKE_DENGE_MAX_MM="105.4")
        return (u["asama"] == "hazir" and olcu_tutar(L, 105) and z == ["duzelt", "denge"]), \
            "%s %s L=%s z=%s" % (son, u, L, z)

    # FZ5 duzelt rc 1 / FZ5b rc 2 geometri reddi -> ariza (deneme+1, satir kuyrukta), denge KOSMAZ, model YOK.
    def fz5(o, mod="rc1"):
        son, u, m, L, x, z, c = zincir_kos(o, 120, FAKE_DUZELT=mod)
        return (son == "HAL=ISLEDI uretildi=0 red=0 ariza=1 rc=0" and u["asama"] == "onarim-bekliyor" and
                u["deneme"] == 1 and m is None and z == ["duzelt"]), "%s %s z=%s" % (son, u, z)

    # FZ6 olcek KAIDE DAHIL: duzelt uzun kenari x1.1 buyutur; teslim uzun kenari = siparis (±%1) ve kaide isareti var.
    def fz6(o):
        son, u, m, L, x, z, c = zincir_kos(o, 120)
        return (u["asama"] == "hazir" and olcu_tutar(L, 120) and "<!--kaide-->" in x), "%s %s L=%s" % (son, u, L)

    # FZ7 denge rc 1 -> ariza (hazir DEGIL). FZ8 figur_duzelt betigi yok -> OLCULEMEDI, is KUYRUKTA.
    def fz7(o):
        son, u, m, L, x, z, c = zincir_kos(o, 120, FAKE_DENGE="rc1")
        return (son == "HAL=ISLEDI uretildi=0 red=0 ariza=1 rc=0" and u["asama"] == "onarim-bekliyor" and
                m is None), "%s %s" % (son, u)

    def fz8(o):
        o.onarim_is(ham=uretim_3mf())
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen(zincir=False), FAKE_KOPRU="aynen")
        u = o.uretim()
        return (son == "HAL=OLCULEMEDI sebep=figur-duzelt-yok rc=4" and u["asama"] == "onarim-bekliyor" and
                u["guncel"] == GUNCEL0 and o.model() is None), "%s %s" % (son, u)

    vaka("FZ1", fz1)
    vaka("FZ2", fz2)
    vaka("FZ3", fz3)
    vaka("FZ4", fz4)
    vaka("FZ5", fz5)
    vaka("FZ5b", lambda o: fz5(o, "geo"))
    vaka("FZ6", fz6)
    vaka("FZ7", fz7)
    vaka("FZ8", fz8)

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

    # RENK SUTUNU (10 Eki, is 05255ed0): 'hazir'da foto_uretim.renk_sayisi = URETILEN model.3mf'in extruder sayisi
    # (extruder_say, koşucudan BAGIMSIZ); satira giriste yazilan tavan (RENK_GIRIS) ezilir. Onarim kolu (plaket,
    # kopru aynen): TEK govde + ucgen boyasi (paint_color) -> boya durumlari sayilir (bolunmus ucgen "841" iki durum).
    BOYA3 = ["4", "841", "0C"]  # durumlar {1}, {1,2} (bolunmus), {3} -> 3 extruder
    BOYA4 = ["4", "841", "0C", "1C"]  # + {4} (durum 3 + sonraki basamak 1) -> 4 extruder
    RENK_GIRIS = 2

    def boyali_3mf(boya):
        # uretim_3mf (Production, boyali alt mesh) + Metadata/model_settings.config (tek govde, extruder 1).
        import io
        import zipfile
        g, c = io.BytesIO(uretim_3mf(1, boya)), io.BytesIO()
        with zipfile.ZipFile(g) as zg, zipfile.ZipFile(c, "w") as zc:
            for n in zg.namelist():
                zc.writestr(n, zg.read(n))
            zc.writestr("Metadata/model_settings.config",
                        '<config><object id="2"><metadata key="extruder" value="1"/></object></config>')
        return c.getvalue()

    def renk_onarim(boya, beklenen):
        def fn(o):
            o.onarim_is(tur="plaket", olcu=60, ham=boyali_3mf(boya))
            o.sql("UPDATE foto_uretim SET renk_sayisi = ?", RENK_GIRIS)
            rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen(), FAKE_KOPRU="aynen")
            u = o.uretim()
            n = extruder_say(o.model() or b"")
            return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
                    n == beklenen and u["renk_sayisi"] == n), "%s %s renk=%s" % (son, u, n)
        return fn

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
    vaka("RO3", renk_onarim(BOYA3, 3))   # boya durumlari {1}, {1,2}, {3} -> 3 renk
    vaka("RO4", renk_onarim(BOYA4, 4))   # + {4} -> 4 renk

    def rs1(o):
        # Uretec kolu (uretim satiri uretec-bekliyor -> hazir; T22 ORNEK kopya kolu, 3 extruder'li 3MF): satira girista
        # yazilan tavan (RENK_GIRIS) -> uretilen model.3mf'in extruder sayisi (3; koşucudan BAGIMSIZ extruder_say).
        x = G2_VAKA["yapboz"]
        yapboz_onizleme(o)
        o.sql("UPDATE foto_isler SET ziyaretci = 'ornek' WHERE is_no = ?", IS2)
        o.kos("--uygula", FAKE_TEKIN_EXTRUDER="3")
        ornek_uretim(o, "yapboz", x["olcu"])
        o.sql("UPDATE foto_uretim SET renk_sayisi = ?", RENK_GIRIS)
        rc, son, _ = o.kos("--uygula", FAKE_TEKIN_EXTRUDER="3")
        u = o.uretim()
        y = os.path.join(o.r2, "foto", ornek_no, "0", "model.3mf")
        n = extruder_say(open(y, "rb").read()) if os.path.isfile(y) else None
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and n == 3 and
                u["renk_sayisi"] == n), "%s %s extruder=%s" % (son, u, n)

    vaka("RS1", rs1)

    # ④ RENDER KOLU (Okan 11 Eki "bu 4 renkli bir figur degil"): figur teslim modeli hazir -> TeKiN render araci
    # (sahte) -> R2 foto-onizleme/<is>-render.webp; 3MF bolge renkleri kalemin ODENEN renklerine eslenir (en yakin).
    # Render basarisizligi karari DEGISTIRMEZ; plaket render kolu DEGIL; KURU CLI R2'ye yazmaz.
    RENDER_ANAHTAR = os.path.join("foto-onizleme", IS + "-render.webp")
    SAG_RENKLER = ["#562F18", "#F4DACC", "#18243B", "#597FAB"]   # 11 Eki prova insan 3MF'i (saglayici bolge renkleri)

    def renkli_3mf():
        import io
        out = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(uretim_3mf())) as z, zipfile.ZipFile(out, "w") as w:
            for n in z.namelist():
                w.writestr(n, z.read(n))
            w.writestr("Metadata/project_settings.config", json.dumps({"filament_colour": SAG_RENKLER}))
        return out.getvalue()

    def render_kur(o, tur="figur", renkler=("Siyah", "Beyaz")):
        o.onarim_is(tur=tur, olcu=120, ham=renkli_3mf())
        o.sql("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES (?,?,?,?,?)",
              SIP, GUNCEL0, "odendi", 120000, json.dumps([{"foto_is": IS, "foto_tur": tur, "olcu_mm": 120,
                                                            "foto_renkler": list(renkler)}]))
        os.makedirs(os.path.join(o.r2, "foto-onizleme"), exist_ok=True)
        with open(os.path.join(o.r2, "foto-onizleme", IS + ".png"), "wb") as f:
            f.write(png_gri(64, 64))

    def render_cagri(o):
        return [json.loads(x) for x in open(o.log) if json.loads(x)[0] == "render"]

    def rn1(o):
        render_kur(o)
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen(render=True), FAKE_KOPRU="aynen")
        y = os.path.join(o.r2, RENDER_ANAHTAR)
        fc = json.load(open(y)).get("filament_colour") if os.path.isfile(y) else None
        siyah, beyaz = RENK_HEX_KARAR["Siyah"], RENK_HEX_KARAR["Beyaz"]
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and o.uretim()["asama"] == "hazir" and
                fc == [siyah, beyaz, siyah, siyah] and "RENDER=OK" in c and render_cagri(o) == [["render", "64"]]), \
            "%s fc=%s cagri=%s" % (son, fc, render_cagri(o))

    def rn2(o):
        render_kur(o)
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen(render=True), FAKE_KOPRU="aynen", FAKE_RENDER="rc1")
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and o.uretim()["asama"] == "hazir" and
                not os.path.isfile(os.path.join(o.r2, RENDER_ANAHTAR)) and "RENDER=YOK" in c and
                "sebep=render-rc-1" in c), "%s %s" % (son, o.uretim())

    def rn3(o):
        render_kur(o, tur="plaket")
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen(render=True), FAKE_KOPRU="aynen")
        return (o.uretim()["asama"] == "hazir" and render_cagri(o) == [] and
                not os.path.isfile(os.path.join(o.r2, RENDER_ANAHTAR)) and "RENDER=" not in c), \
            "%s cagri=%s" % (son, render_cagri(o))

    def rn4(o):
        m = os.path.join(o.d, "m.3mf")
        with open(m, "wb") as f:
            f.write(renkli_3mf())
        on = os.path.join(o.d, "on.png")
        with open(on, "wb") as f:
            f.write(png_gri(64, 64))
        jen = o.jen(render=True)
        rc0, son0, _ = o.kos("--render", IS, "--3mf", m, "--onizleme", on, FOTO_KOSUCU_JENERATOR=jen)
        put0 = o.r2_put()
        rc2, son2, _ = o.kos("--render", IS, "--3mf", m, "--onizleme", on, "--renkler", "Mor",
                             FOTO_KOSUCU_JENERATOR=jen)
        rc1, son1, _ = o.kos("--render", IS, "--3mf", m, "--onizleme", on, "--renkler", "Kırmızı", "--uygula",
                             FOTO_KOSUCU_JENERATOR=jen)
        y = os.path.join(o.r2, RENDER_ANAHTAR)
        fc = json.load(open(y)).get("filament_colour") if os.path.isfile(y) else None
        return (rc0 == 0 and son0.startswith("HAL=RENDER-KURU") and put0 == 0 and
                rc2 == 2 and son2 == "HAL=RED sebep=renk rc=2" and
                rc1 == 0 and son1.startswith("HAL=RENDER-OK") and fc == [RENK_HEX_KARAR["Kırmızı"]] * 4), \
            "%s/%s/%s put0=%d fc=%s" % (son0, son2, son1, put0, fc)

    vaka("RN1", rn1)
    vaka("RN2", rn2)
    vaka("RN3", rn3)
    vaka("RN4", rn4)

    # ④ TEK RENK ONIZLEMESI (Okan 14 Eki 03:0x): Worker build'i bitirdi (render-bekliyor + R2 GLB) -> koşucu SECILEN
    # renkte (manifest RENK_HEX) sahte Blender'la cizer -> R2 foto-onizleme/<is>-<renk>.png -> 'hazir'.
    RENK_PNG = lambda renk: os.path.join("foto-onizleme", IS + "-" + renk + ".png")  # noqa: E731

    def rr1(o):
        o.renk_is("Gri")
        rc, son, c = o.kos("--uygula", **o.renk_env())
        y = os.path.join(o.r2, RENK_PNG("Gri"))
        icerik = open(y, "rb").read() if os.path.isfile(y) else b""
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and o.renk_satiri()["asama"] == "hazir" and
                icerik == b"\x89PNG\r\n\x1a\n" + RENK_HEX_KARAR["Gri"].lstrip("#").encode() and
                o.blender_cagri() == [["blender", RENK_HEX_KARAR["Gri"].lstrip("#"), True]] and
                not os.path.isfile(os.path.join(o.r2, RENK_PNG("Beyaz")))), \
            "%s satir=%s cagri=%s png=%r" % (son, o.renk_satiri(), o.blender_cagri(), icerik[:20])

    def rr2(o):
        o.renk_is("Beyaz", glb=False)
        rc, son, c = o.kos("--uygula", **o.renk_env())
        s = o.renk_satiri()
        return (s["asama"] == "basarisiz" and s["hata"] == "model-yok" and o.blender_cagri() == [] and
                not os.path.isfile(os.path.join(o.r2, RENK_PNG("Beyaz")))), "%s satir=%s" % (son, s)

    def rr3(o):
        o.renk_is("Siyah")
        sonlar = []
        for _ in range(3):
            o.sql("UPDATE foto_renk_onizleme SET son_kontrol = 5")
            rc, son, c = o.kos("--uygula", **o.renk_env(FAKE_BLENDER="rc1"))
            sonlar.append((son, dict(o.renk_satiri())))
        return (sonlar[0][1] == {"renk": "Siyah", "asama": "render-bekliyor", "hata": "render-ariza-1"} and
                sonlar[1][1]["hata"] == "render-ariza-2" and
                sonlar[2][1] == {"renk": "Siyah", "asama": "basarisiz", "hata": "render-basarisiz"} and
                not os.path.isfile(os.path.join(o.r2, RENK_PNG("Siyah")))), "%s" % sonlar

    def rr4(o):
        # Goc oncesi hedef: tablo YOK -> renk kuyrugu BOS (OLCULEMEDI DEGIL), diger kuyruklar aynen.
        o.sql("DROP TABLE foto_renk_onizleme")
        rc, son, c = o.kos("--uygula", **o.renk_env())
        o.onizleme_is()
        rc2, son2, c2 = o.kos("--uygula", **o.renk_env())
        return (rc == 1 and son == "HAL=BOS rc=1" and rc2 == 0 and son2.startswith("HAL=ISLEDI uretildi=1")), \
            "%s / %s" % (son, son2)

    def rr5(o):
        # --kuyruk renk: yalniz ④ cizimi; bekleyen uretec onizlemesi DOKUNULMAZ (kanit kosumu canli kuyrugu yemez).
        o.renk_is("Beyaz")
        o.onizleme_is()
        rc, son, c = o.kos("--uygula", "--kuyruk", "renk", **o.renk_env())
        u = o.sql("SELECT asama FROM foto_isler WHERE is_no = ?", IS2)
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and o.renk_satiri()["asama"] == "hazir" and
                u and u[0]["asama"] == "uretec-onizleme" and o.uretec_sayisi() == 0), "%s %s" % (son, u)

    # ④ URETEC TURU (Okan 14 Eki 03:5x "tum 6 modulde"): onizleme modeli girdinin SECILEN renk(ler)iyle ortak studyo
    # sablonunda cizilir -> R2 foto-uretec-onizleme/<is>/renk.png, D1 'onizleme-hazir'dan ONCE. TeKiN ortak araci
    # (sozlesme --arkaplan) varsa o; 3+ renk (Renkli palet) cizilmez; arac yoksa onizleme yine hazir (cizim YOK).
    RENK_URETEC = os.path.join("foto-uretec-onizleme", IS2, "renk.png")

    def rr_uretec(o, renkler):
        o.uretec_onizleme(CEKIRDEK_TUR, 120, renkler, {}, {"gri_harita": ("gri_harita.png", png_gri(200, 140))})
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen(render="yeni"))
        cagri = [json.loads(x) for x in open(o.log) if json.loads(x)[0] == "render-yeni"]
        r = o.sql("SELECT asama FROM foto_isler WHERE is_no = ?", IS2)[0]
        return son, c, cagri, r["asama"], os.path.isfile(os.path.join(o.r2, RENK_URETEC))

    def rr6(o):
        son, c, cagri, asama, var = rr_uretec(o, {"govde": "Gri"})
        return (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and asama == "onizleme-hazir" and var and
                cagri == [["render-yeni", RENK_HEX_KARAR["Gri"].lstrip("#"), "", "", ".3mf", "studyo"]] and
                "RENK-CIZIM=OK" in c), "%s %s %s" % (son, cagri, var)

    def rr7(o):
        son, c, cagri, asama, var = rr_uretec(o, {"plaka": "Siyah", "yazi": "Beyaz"})
        return (asama == "onizleme-hazir" and var and
                cagri == [["render-yeni", RENK_HEX_KARAR["Siyah"].lstrip("#"), RENK_HEX_KARAR["Beyaz"].lstrip("#"),
                           "yazi", ".3mf", "studyo"]]), "%s %s" % (son, cagri)

    def rr8(o):
        son, c, cagri, asama, var = rr_uretec(o, {"renk1": "Siyah", "renk2": "Beyaz", "renk3": "Gri"})
        return (asama == "onizleme-hazir" and not var and cagri == [] and "sebep=renkli" in c), "%s %s" % (son, cagri)

    vaka("RR1", rr1)
    vaka("RR2", rr2)
    vaka("RR3", rr3)
    vaka("RR4", rr4)
    vaka("RR5", rr5)
    def rr9(o):
        # Ortak arac YOK + iki renk (iki renkli uretec ciktisi): eski 3MF araci part renklerini okumaz (14 Eki olcumu: Siyah+Beyaz
        # model TUMDEN Siyah cizildi) -> cizim YOK (uretec gorseli AYNEN); tek renkte eski arac cizer.
        o.uretec_onizleme(CEKIRDEK_TUR, 120, {"plaka": "Siyah", "yazi": "Beyaz"}, {},
                          {"gri_harita": ("gri_harita.png", png_gri(200, 140))})
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen(render=True))
        iki = (os.path.isfile(os.path.join(o.r2, RENK_URETEC)), "sebep=iki-renk-ortak-arac-yok" in c)
        return (son.startswith("HAL=ISLEDI uretildi=1") and iki == (False, True)), "%s %s" % (son, iki)

    def rr10(o):
        # Cizim istisnasi (sahte uretecin 3MF'i zip degil -> eski arac yolunda BadZipFile) onizlemeyi DUSURMEZ.
        o.uretec_onizleme(CEKIRDEK_TUR, 120, {"govde": "Gri"}, {}, {"gri_harita": ("gri_harita.png", png_gri(200, 140))})
        rc, son, c = o.kos("--uygula", FOTO_KOSUCU_JENERATOR=o.jen(render=True))
        r = o.sql("SELECT asama FROM foto_isler WHERE is_no = ?", IS2)[0]
        return (son.startswith("HAL=ISLEDI uretildi=1") and r["asama"] == "onizleme-hazir" and
                "RENK-CIZIM=YOK" in c and "sebep=istisna" in c), "%s %s" % (son, r)

    vaka("RR6", rr6)
    vaka("RR7", rr7)
    vaka("RR8", rr8)
    vaka("RR9", rr9)
    vaka("RR10", rr10)
    for ad, fn in (("T1", t1), ("T2", t2), ("T3", t3), ("T4", t4), ("T5", t5), ("T6", t6), ("T7", t7),
                   ("T8", t8), ("T9", t9), ("T10", t10), ("T11", t11), ("T12", t12), ("T12b", t12b)):
        vaka(ad, fn)
    return s


MUTANTLAR = {
    "M1": ('    if o.get("sizdirmaz") is not True:\n        return "sizdirmaz-degil"\n', "", {"T5"}),
    "M2": ("    if not uygula:\n", "    if False:\n", {"T9", "K2"}),
    # SAGLIK DAMGASI: damga yazimi kalkarsa onizleme hazirlayicisi hep "cevrimdisi" gorunur (K1; T1 tek yazim).
    "MK1": ("            damga_yaz(yaz)\n", "            pass\n", {"K1", "T1"}),
    "M3": ('    if n != 1:\n        yaz("CAS %s kiralanamadi', '    if False:\n        yaz("CAS %s kiralanamadi', {"T6"}),
    "M4": ("DENEME_TAVANI = 3\n", "DENEME_TAVANI = 99\n", {"T4", "RR3"}),
    "M5": ("            d1(geri_ver_sql(i, jeton))\n", "            pass\n", {"T7", "T34"}),
    "M6": ("    if onceki != sha:\n", "    if False:\n", {"T12b"}),
    "M7": ('    if i["kuyruk"] != "siparis" or not i.get("onizleme_kaynakli"):\n        return None\n    os.makedirs',
           '    if True:\n        return None\n    os.makedirs', {"T12", "T22"}),  # T22: ORNEK kolu da kopya koluna baglanir
    # tekin-ortak koprusu (yapboz)
    "M8": ("    return renk_hex[ad]\n", "    return \"#F2F2F2\"\n", {"T13-yapboz", "V5-ESKI"}),
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
    # yapboz eslemesi silinirse uretec-bicimi RED: tum yapboz vakalari (14 Eki: T14/T16/T17/T18/T22/RS1 yapboza tasindi).
    "M31": ('"sablon": esle_sablon, "yapboz": esle_yapboz,\n', '"sablon": esle_sablon,\n',
            {"T13-yapboz", "T14", "T16", "T17", "T18", "T19", "T20", "T21", "T22", "T35", "T36", "RS1", "V5-ESKI"}),
    # ONARIM KUYRUGU (8 Eki): olcum atlanirsa kirmizi kopru ciktisi 'hazir' olur.
    "M32": ('        rc, hata, cik = kos(["--olc", ham, cikti])\n', '        rc, hata, cik = 0, "", "{}"\n', {"T28", "T33"}),
    # kopru-yok fail-closed silinirse is kuyrukta kalmaz (python dosya bulamaz -> elle).
    "M33": ('        raise Erisilemedi("kopru-yok")\n', "        pass\n", {"T29", "T34"}),
    # erisim yokken kira geri verilmezse satirin jetonu kayar.
    "M34": ("            d1(geri_ver_sql(i, jeton))  # onarim kuyrugu: kira geri (kopru/R2/D1 yok -> is kuyrukta)\n",
            "            pass\n", {"T29", "FZ8"}),
    # palet ciktisi TEK govde + ucgen boyasi: koşucu boyayi saymazsa renk=1 (gercek prova 10 Eki: 4 boyali figur -> 1).
    "M-RB-BOYA": ("    if not boya:\n        return len(govde)\n", "    if True:\n        return len(govde)\n", {"RO3", "RO4"}),
    # bolunmus ucgende yalniz ilk yaprak sayilirsa ("841" -> {1}) durum 2 kaybolur -> renk=2 (RO3).
    "M-RB-BOLUNMUS": ("            bekleyen += (kod & 3) + 1\n", "            bekleyen += 1\n", {"RO3", "RO4"}),
    # RENK SUTUNU: 'hazir' yazimi olculen extruder sayisini tasimazsa satir giris tavaninda (2/4) kalir ->
    # onarim kolu RO3/RO4, uretec (siparis) kolu RS1; SQL kolu ikisini birden.
    "M-RS-ONARIM": ("            renk = uc_mf_extruder_sayisi(cikti)\n", "            renk = None\n",
                    {"RO3", "RO4"}),
    "M-RS-SIPARIS": ('                    renk = uc_mf_extruder_sayisi(os.path.join(cikti, "model.3mf"))\n',
                     "                    renk = None\n", {"RS1"}),
    "M-RS-SQL": ('                st += ", renk_sayisi = %d" % int(renk)\n', "                pass\n",
                 {"RO3", "RO4", "RS1"}),
    # kalem okunmazsa render paleti de duser (odenen renkler yerine filament tablosu) -> RN1.
    "M-RB-SELECT": (' u.guncel, s.urunler"\n', ' u.guncel"\n', {"RN1"}),
    # ④ RENDER KOLU (Okan 11 Eki): kanca kalkarsa render YOK · palet kalemi yok sayilirsa bolgeler odenmemis renge ·
    # kol sarti kalkarsa plaket de render'lanir · KURU kol R2'ye yazarsa.
    "M-RN-HOOK": ("            onizleme_render_koy(i, cikti, gecici, yaz)\n", "            pass\n", {"RN1", "RN2"}),
    "M-RN-PALET": ("for a in (adlar or sorted(tablo))", "for a in (sorted(tablo))", {"RN1", "RN4"}),
    "M-RN-KOL": ('        if karar == "hazir" and zincir:\n', '        if karar == "hazir":\n', {"RN3"}),
    "M-RN-KURU": ("        if uygula:\n            try:\n", "        if True:\n            try:\n",
                  {"RN4"}),
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
    # TUR-B ⑧: eski alan atilmazsa eski yapboz isi `RED parametre` ile duser.
    "M4-ESKI": ("    eski_alanlari_at(t.get(\"kod\"), girdi)\n", "", {"V5-ESKI"}),
    # FIGUR ZINCIRI (22:3x): duzelt atlanirsa kaidesiz pet devrilir, 5 kabuk kalir, cagri sirasi bozulur; olcek
    # duzeltten ONCE yapilirsa kaide uzun kenari olcunun ustune tasir (koşucu ariza / teslim olcusu tutmaz); denge
    # RED'i hazir sayilirsa tavan ustu insan teslim edilir.
    "M-FZ-ATLA": ('    rc, dsatir = _jen_kos(FIGUR_DUZELT_BETIK, ["--girdi", model, "--cikti", dz])\n    duz = os.path.join(dz, "duzelt.3mf")\n',
                  '    rc, dsatir = 0, "DUZELT=atlandi"\n    duz = model\n',
                  {"FZ1", "FZ2", "FZ3", "FZ4", "FZ5", "FZ5b", "FZ6", "FZ8"}),
    "M-FZ-SIRA": ('    L = uc_mf_olcekle(duz, olcekli, olcu) if isinstance(olcu, int) and olcu > 0 else None\n',
                  '    uc_mf_olcekle(model, olcekli + ".on.3mf", olcu)\n'
                  '    _jen_kos(FIGUR_DUZELT_BETIK, ["--girdi", olcekli + ".on.3mf", "--cikti", dz + "-on"])\n'
                  '    shutil.copyfile(os.path.join(dz + "-on", "duzelt.3mf"), olcekli)\n    L = olcu\n',
                  {"FZ1", "FZ2", "FZ3", "FZ4", "FZ6"}),
    "M-FZ-RED-HAZIR": ('    if rc == 0 and satir.startswith("DENGE=OK "):\n', '    if rc in (0, 2):\n', {"FZ3"}),
    # ④ TEK RENK (Okan 14 Eki): cizim yanlis renkte (secilen yerine Beyaz hex'i) -> RR1 · R2 anahtari renkten bagimsiz
    # (hep -Beyaz.png) -> RR1 · tablo yokken kuyruk OLCULEMEDI'ye dusurur (diger kuyruklar da durur) -> RR4.
    "M-RR-HEX": ('    hx = renk_tablosu().get(i["renk"]) if RENK_ADI_KALIBI', '    hx = renk_tablosu().get("Beyaz") if RENK_ADI_KALIBI',
                 {"RR1"}),
    "M-RR-ANAHTAR": ('    return "foto-onizleme/%s-%s.png" % (is_no, renk)', '    return "foto-onizleme/%s-Beyaz.png" % is_no',
                     {"RR1"}),
    "M-RR-TABLO": ("    except TabloYok:\n        return []\n", "    except KeyError:\n        return []\n", {"RR4"}),
    # ④ uretec cizimi: kanca kalkarsa cizim YOK -> RR6/RR7 · ikinci renk dusurulurse iki renkli model tek renk -> RR7.
    "M-RR-URETEC-KANCA": ('                if i["kuyruk"] == "onizleme":\n                    try:\n',
                          '                if False:\n                    try:\n', {"RR6", "RR7", "RR8", "RR9", "RR10"}),
    "M-RR-IKINCI-RENK": ("    if len(farkli) == 2:\n        bolge2", "    if False:\n        bolge2", {"RR7"}),
    # eski 3MF araci iki renkte de kullanilirsa (part renkleri okunmaz) yanlis renkli cizim yazilir -> RR9.
    "M-RR-ESKI-IKI-RENK": ("        if len(farkli) != 1:\n            yaz(", "        if False:\n            yaz(", {"RR9"}),
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
        # ④ TEK RENK: koşucu cizim aracini KENDI kokunden cagirir (tools/foto-renk-render.py) -> kopyada da olmali.
        shutil.copyfile(os.path.join(KOK, "tools", "foto-renk-render.py"), os.path.join(d, "tools", "foto-renk-render.py"))
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
    return kirmizi == hedef, "kirmizi=%s hedef=%s" % (sorted(kirmizi), sorted(hedef))


# ------------------------------------------------------------------ manifest tutarliligi (G2)
def kosucu_modulu():
    import importlib.util
    sp = importlib.util.spec_from_file_location("foto_uretec_kosucu", KOSUCU)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


# EVREN (K3d, 9 Eki 2026) — manifestteki turler ve motorlari AYNEN; silinen 15 tur burada YOK.
EVREN = {"plaket": "M", "figur": "M", "yapboz": "D", "bust": "D"}
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

}
RENK_HEX_KARAR = {"Beyaz": "#F2F2F2", "Siyah": "#1A1A1A", "Gri": "#818184", "Lacivert": "#12294D",
                  "Kırmızı": "#B3262E", "Sarı": "#E8B923", "Yeşil": "#2E7D4F", "Mavi": "#2E5E8C", "Ahşap": "#C8B89A"}
# Uretec girdi semalarinin alan adlari (pruvo-jenerator yapboz_uret.SEMA);
# `--gercek` kolu GERCEK uretecle dogrular.
URETEC_ALANLARI = {
    "yapboz": {"gorsel", "uzun_kenar_mm", "satir", "sutun", "tohum", "kabartma_yon", "renkler"},

}
URETEC_OLCU_ALANI = {"yapboz": "uzun_kenar_mm"}
URETEC_SABIT = {"yapboz": {}}

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
const yb={uzun_kenar_mm:150,satir:4,sutun:5,tohum:7,kabartma_yon:'koyu_yuksek'};
o.p={
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
    s["V1"] = (not hata, "satir: %s" % (hata or "evren 4 tur + 1/1 kopru satiri"))
    hata = [k for k, x in G2_SATIR.items() if (tur.get(k) or {}).get("ornek_notu") != x["notu"] or
            (tur.get(k) or {}).get("durustluk") != x["durust"]]
    # C2 (10 Eki): ornek_notu "" = ② TEK cumle (figur + plaket; durustluk kapsar) -> ALAN zorunlu, metni bos olabilir.
    bos = [t["kod"] for t in m["turler"] if not isinstance(t.get("ornek_notu"), str) or not t.get("durustluk")]
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
             [("https://media.pruvo3d.com/foto/ornek/%s-1-render.webp" % k,) * 2] * x["ornek_render"] + x.get("ornek_ek", [])]
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
              mod.ret_kodu("RET: ince cizgi (< 0.60 mm) var; ince_cizgi=reddet") == "ince-cizgi" and
              mod.ret_kodu("RET: SVG: desteklenmeyen eleman <text> (metin/filter/gorsel/maske/stil yok)") == "svg" and
              mod.ret_kodu("RET: bilinmeyen alan: x") == "genel")
    # ArTisT 19. okuma (13 Eki): "Yazı ve taban rengi birbirine çok yakın; yazı okunmaz. Farklı bir renk seç."
    s["V6"] = ("rengi birbirine çok yakın" in m["red_kontrast"] and m["red_bilinmez"] == m["red"][""] and
               m["red_genel"] == m["red"][""] and not eksik and ret_ok,
               "kontrast=%r eksik=%s ret_kodu=%s" % (m["red_kontrast"][:50], eksik, ret_ok))
    pp = m["p"]
    s["V7"] = (pp["yb_ok"] and not pp["yb_satir9"] and
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
    s["V8"] = (not hata, "esleme: %s" % (hata or "1/1 tur, her secenek"))
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
    """Kopru turleri x min/orta/maks (manifest araligi: yapboz 100-280)."""
    foto = ("foto.png", _foto_ton(640, 480))
    v = []
    for olcu, renk, sat, sut in ((100, {"renk1": "Ahşap"}, 3, 4),
                                 (190, {"renk1": "Ahşap", "renk2": "Lacivert"}, 4, 5),
                                 (280, {"renk1": "Beyaz", "renk2": "Kırmızı", "renk3": "Mavi", "renk4": "Siyah"}, 5, 6)):
        v.append(("yapboz", olcu, renk, {"satir": sat, "sutun": sut, "tohum": 1, "kabartma_yon": "acik_yuksek"},
                  {"foto": foto}))
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
    if not all(os.path.isfile(os.path.join(jen, "jeneratorler", "foto", b)) for b in ("yapboz_uret.py",)):
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
    # FOTO_KOSUCU_TEST_ISCI: es zamanli mutant tavani (agir-is kapisi altinda <=3); yoksa eski deger AYNEN.
    isci = int(os.environ.get("FOTO_KOSUCU_TEST_ISCI") or min(8, os.cpu_count() or 4))
    with ThreadPoolExecutor(max_workers=max(1, isci)) as h:
        sonuclar = list(h.map(mutant_kos, list(MUTANTLAR)))
    for ad, (g, ac) in zip(MUTANTLAR, sonuclar):
        print("%s %s — %s" % ("✅" if g else "❌ SURVIVOR", ad, ac))
        survivor += 0 if g else 1
    print("VAKA_KIRMIZI=%d SURVIVOR=%d" % (kirmizi, survivor))
    return 1 if kirmizi or survivor else 0


if __name__ == "__main__":
    sys.exit(main())
