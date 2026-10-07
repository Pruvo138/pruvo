#!/usr/bin/env python3
"""FOTO `ORNEK-` UCTAN UCA BETIGI — hermetik kabul testi + mutantlar (tools/foto-ornek-uc-uca.py).

HERMETIK: betik IZOLE bir kopya agacta (tempfile) kosar: sahte sunucu (127.0.0.1, /acik + /onizleme +
/litofan + medya), sahte wrangler (D1 = gecici SQLite, sema tools/d1-sema.sql; R2 = gecici dizin), sahte
kopru (kosucu yerine: kuyruktaki ornek islerine 3MF + olcu.json + onizleme.png yazar), sahte tarayici
sonucu (FOTO_UU_TARAYICI_SAHTE). Gercek D1/R2/onizleme/ev yolu YOK; her sey tempfile, bitince silinir.

Vakalar: U1 isimlik mutlu yol -> HAZIR=1/1 rc=0 (6 olcut HAZIR) · U2 SUNUCU MUTANTI: acik olmayan
kategori 200 -> betik GECERSIZ rc=2 HAZIR=0 · U3 3MF delik (ucgen eksik) -> (4) EKSIK · U4 olcek ekseni
%10 sapma -> (4) EKSIK · U5 sunucu onaysiz istegi kabul (403) -> (5) EKSIK · U6 /acik fiyati mm x 900 ->
(3) EKSIK · U7 tur /acik'ta yok -> (1) EKSIK · U8 375 px tasma 6 -> (6) EKSIK · U9 konsol hatasi 1 ->
(6) EKSIK · U10 tarayici yok -> (3)(5)(6) EKSIK, rc 1 (yesil SAYILMAZ) · U11 litofan (tarayici
onizleyicili) mutlu yol · U12 onizleme toml canliyla ayni -> rc 2, wrangler cagrisi 0 · U13 yazimlar
YALNIZ onizleme D1/kovasina · U14 tur listesi MANIFESTTEN (--hepsi --kol D = manifestteki D sayisi) ·
U15 tarayicida tur secilemiyor (baska tur secili) -> (3)(5)(6) EKSIK · U16 cok parcali TABLA duzeni
(parcalar <= olcu, olcu.json montaj == olcu) -> (4) HAZIR `eksen=montaj` · U17 ayni duzen, olcu.json montaj
%10 sapma -> (4) EKSIK · U18 bir parca urun olcusunu %20 asiyor -> (4) EKSIK.
Mutantlar (betik kopyasinda capa degisir): MB1 mutant kapisi silindi -> U2 KIRMIZI · MB2 sizdirmazlik
olcumu yok -> U3 · MB3 eksen toleransi yok -> U4+U16+U18 · MB4 sunucu onay kontrolu yok -> U5 · MB5 fiyat
carpimi yok -> U6 · MB6 tarayici yokken gecer -> U10 · MB7 canli ayrilik kapisi yok -> U12 ·
MB8 secili tur kontrolu yok -> U15 · MB9 tabla duzeninde parca siniri yok -> U18 · MB0 yorum -> 0 kirmizi.
"""
import json
import os
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import threading
import zipfile
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BETIK = os.path.join(KOK, "tools", "foto-ornek-uc-uca.py")
SEMA = os.path.join(KOK, "tools", "d1-sema.sql")
KOPYA_DOSYALAR = ["foto-uretim-veri.js", "shop/wrangler.toml", "shop/wrangler.onizleme.toml",
                  "tools/foto-onizleme.py"]

SAHTE_WRANGLER = r'''
import json, os, shutil, sqlite3, sys
a = sys.argv[1:]
open(os.environ["FAKE_LOG"], "a").write(json.dumps(a) + "\n")
if a[:2] == ["d1", "execute"]:
    sql = a[a.index("--command") + 1]
    c = sqlite3.connect(os.environ["FAKE_DB"]); c.row_factory = sqlite3.Row
    cur = c.execute(sql); rows = [dict(r) for r in cur.fetchall()]; c.commit()
    print(json.dumps([{"results": rows, "success": True, "meta": {"changes": cur.rowcount}}])); sys.exit(0)
if a[:2] == ["r2", "object"]:
    anahtar = a[3].split("/", 1)[1]; dosya = a[a.index("--file") + 1]
    yol = os.path.join(os.environ["FAKE_R2"], anahtar)
    if a[2] == "get":
        if not os.path.isfile(yol):
            sys.stderr.write("The specified key does not exist.\n"); sys.exit(1)
        shutil.copyfile(yol, dosya); sys.exit(0)
    os.makedirs(os.path.dirname(yol), exist_ok=True); shutil.copyfile(dosya, yol); sys.exit(0)
sys.exit(9)
'''

# Sahte kopru: kuyruktaki isleri isler (gercek kosucunun satir/dosya sozlesmesi). Model: L x L/2 x 3 kutu
# (L = olcu_mm x FAKE_GEO), 12 ucgen, su gecirmez; FAKE_DELIK -> 1 ucgen eksik.
SAHTE_KOPRU = r'''
import json, os, sqlite3, struct, sys, zipfile, zlib, hashlib
db = sqlite3.connect(os.environ["FAKE_DB"]); db.row_factory = sqlite3.Row; R = os.environ["FAKE_R2"]
def png(w, h):
    ch = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)) +
            ch(b"IDAT", zlib.compress(b"".join(b"\x00" + b"\x80" * w for _ in range(h)))) + ch(b"IEND", b""))
def yaz(d, tur, olcu):
    os.makedirs(d, exist_ok=True)
    L = olcu * float(os.environ.get("FAKE_GEO") or 1.0); W = L / 2; H = 3.0
    v = [(x, y, z) for x in (0, L) for y in (0, W) for z in (0, H)]
    t = [(0,2,6),(0,6,4),(1,5,7),(1,7,3),(0,4,5),(0,5,1),(2,3,7),(2,7,6),(0,1,3),(0,3,2),(4,6,7),(4,7,5)]
    if os.environ.get("FAKE_DELIK"): t = t[:-1]
    def nesne(i, v):
        return ('<object id="%d" type="model"><mesh><vertices>' % i +
                "".join('<vertex x="%g" y="%g" z="%g"/>' % p for p in v) + '</vertices><triangles>' +
                "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % q for q in t) + '</triangles></mesh></object>')
    ob, it = nesne(1, v), '<item objectid="1"/>'
    if os.environ.get("FAKE_RAF"):  # tabla duzeni: 2. parca (uzun kenari L x FAKE_RAF) yan tarafta
        B = L * float(os.environ["FAKE_RAF"])
        ob += nesne(2, [(x, y, z) for x in (0, B) for y in (0, 10) for z in (0, H)])
        it += '<item objectid="2" transform="1 0 0 0 1 0 0 0 1 %g 0 0"/>' % (L + 5)
    xml = ('<model unit="millimeter"><resources>' + ob + '</resources><build>' + it + '</build></model>')
    m = os.path.join(d, "model.3mf")
    with zipfile.ZipFile(m, "w") as z: z.writestr("3D/3dmodel.model", xml)
    open(os.path.join(d, "onizleme.png"), "wb").write(png(1024, 512))
    json.dump({"sozlesme": 1, "kategori": tur, "uzun_kenar_mm": L * float(os.environ.get("FAKE_UK") or 1.0),
               "kutu_mm": {"x": L, "y": W, "z": H},
               "renk_sayisi": 2, "sizdirmaz": True, "ucgen": len(t), "hacim_cm3": 1.0,
               "model_sha256": hashlib.sha256(open(m, "rb").read()).hexdigest()}, open(os.path.join(d, "olcu.json"), "w"))
n = 0
for r in db.execute("SELECT * FROM foto_isler WHERE asama = 'uretec-onizleme'").fetchall():
    yaz(os.path.join(R, "foto-uretec-onizleme", r["is_no"]), r["tur"], r["olcu_mm"])
    db.execute("UPDATE foto_isler SET asama='onizleme-hazir' WHERE is_no=?", (r["is_no"],)); n += 1
for r in db.execute("SELECT u.*, i.ziyaretci FROM foto_uretim u LEFT JOIN foto_isler i ON i.is_no=u.is_no"
                    " WHERE u.asama='uretec-bekliyor'").fetchall():
    if r["ziyaretci"] != "ornek" or r["siparis_no"] != "ORNEK-" + r["is_no"][:12]: continue
    yaz(os.path.join(R, "foto", r["siparis_no"], "0"), r["tur"], r["olcu_mm"])
    db.execute("UPDATE foto_uretim SET asama='hazir' WHERE siparis_no=?", (r["siparis_no"],)); n += 1
db.commit()
print("HAL=ISLEDI uretildi=%d red=0 ariza=0 rc=0" % n if n else "HAL=BOS rc=1")
'''


def manifest():
    import importlib.util
    sp = importlib.util.spec_from_file_location("foto_uu", BETIK)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m.manifest_oku()


MAN = manifest()
TUR = {t["kod"]: t for t in MAN["turler"]}


class Sunucu:
    """Sahte onizleme worker'i. ayar: acik (kod listesi), carpan, kapali_kod (mutant: kapali tur kodu),
    onaysiz_kod (mutant: onaysiz istege donen kod)."""

    def __init__(self):
        self.ayar = {"acik": [], "carpan": 1000, "kapali_kod": 400, "onaysiz_kod": 400}
        ayar = self.ayar

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def yanit(self, kod, veri, tip="application/json"):
                b = veri if isinstance(veri, bytes) else json.dumps(veri).encode()
                self.send_response(kod)
                self.send_header("Content-Type", tip)
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def do_GET(self):
                if self.path == "/api/shop/foto/acik":
                    tl = [{"kod": k, "olculer": [{"mm": mm, "fiyat_kurus": mm * ayar["carpan"]}
                                                 for mm in TUR[k]["olcu_secenekleri"]]} for k in ayar["acik"]]
                    return self.yanit(200, {"acik": bool(tl), "turler": tl, "onay_surum": MAN["onay_surum"]})
                if self.path.startswith("/medya/"):
                    return self.yanit(200, b"RIFF0000WEBP", "image/webp")
                self.yanit(404, {"hata": "yok"})

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                g = json.loads(self.rfile.read(n) or b"{}")
                if g.get("tur") not in ayar["acik"]:
                    k = ayar["kapali_kod"]
                    return self.yanit(k, {"hata": "tur-kapali"} if k == 400 else {"is": "x"})
                if g.get("aydinlatma_onay") is not True:
                    k = ayar["onaysiz_kod"]
                    return self.yanit(k, {"hata": "onay-yok" if k == 400 else "bot-dogrulama"})
                self.yanit(403, {"hata": "bot-dogrulama"})

        self.h = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.h.serve_forever, daemon=True).start()
        self.taban = "http://127.0.0.1:%d" % self.h.server_address[1]

    def kapat(self):
        self.h.shutdown()
        self.h.server_close()


def tarayici_iyi(kod):
    t = TUR[kod]
    uc = t["olcu_secenekleri"][-1]
    return {"secildi": True, "secili_tur": kod, "surgu": True,
            "fiyat": "%d mm → %s TL" % (uc, "{:,}".format(uc * 10).replace(",", ".")),
            "onay_kutusu": 1, "onaysiz_dugme_kapali": True, "durustluk": t["durustluk"], "tasma": 0,
            "genislik": 375, "konsol": []}


class Ortam:
    def __init__(self, betik_kaynak):
        self.d = tempfile.mkdtemp(prefix="foto-uu-test-")
        self.agac = os.path.join(self.d, "agac")
        for yol in KOPYA_DOSYALAR:
            os.makedirs(os.path.dirname(os.path.join(self.agac, yol)), exist_ok=True)
            shutil.copyfile(os.path.join(KOK, yol), os.path.join(self.agac, yol))
        with open(os.path.join(self.agac, "tools", "foto-ornek-uc-uca.py"), "w", encoding="utf-8") as f:
            f.write(betik_kaynak)
        self.db = os.path.join(self.d, "d1.sqlite")
        self.r2 = os.path.join(self.d, "r2")
        self.log = os.path.join(self.d, "wrangler.log")
        os.makedirs(self.r2)
        open(self.log, "w").close()
        for ad, ic in (("wr.py", SAHTE_WRANGLER), ("kopru.py", SAHTE_KOPRU)):
            with open(os.path.join(self.d, ad), "w") as f:
                f.write(ic)
        c = sqlite3.connect(self.db)
        with open(SEMA, encoding="utf-8") as f:
            c.executescript(f.read())
        c.commit()
        c.close()
        self.sunucu = Sunucu()
        self.tarayici = {}
        self.env = dict(os.environ, FAKE_DB=self.db, FAKE_R2=self.r2, FAKE_LOG=self.log,
                        FOTO_UU_TABAN=self.sunucu.taban,
                        FOTO_UU_MEDYA_ESLE="https://media.pruvo3d.com=%s/medya" % self.sunucu.taban,
                        FOTO_UU_WRANGLER="%s %s" % (sys.executable, os.path.join(self.d, "wr.py")),
                        FOTO_UU_KOSUCU=os.path.join(self.d, "kopru.py"), FOTO_UU_BEKLE_SN="0",
                        FOTO_UU_TARAYICI_SAHTE=os.path.join(self.d, "tarayici.json"),
                        PYTHONDONTWRITEBYTECODE="1")
        for k in ("FAKE_GEO", "FAKE_DELIK", "FOTO_UU_CHROME"):
            self.env.pop(k, None)

    def kos(self, *arg, **ek):
        with open(self.env["FOTO_UU_TARAYICI_SAHTE"], "w", encoding="utf-8") as f:
            json.dump(self.tarayici, f, ensure_ascii=False)
        env = dict(self.env, **ek)
        if env.get("FOTO_UU_TARAYICI_SAHTE") == "":
            env.pop("FOTO_UU_TARAYICI_SAHTE")
        p = subprocess.run([sys.executable, os.path.join(self.agac, "tools", "foto-ornek-uc-uca.py")] + list(arg),
                           capture_output=True, text=True, env=env, timeout=300)
        son = (p.stdout.strip().splitlines() or [""])[-1]
        return p.returncode, son, p.stdout + p.stderr

    def cagrilar(self):
        with open(self.log) as f:
            return [json.loads(s) for s in f if s.strip()]

    def kapat(self):
        self.sunucu.kapat()
        shutil.rmtree(self.d, ignore_errors=True)


def olcut(cikti, kod, o):
    """Turun (o) olcut satiri: 'HAZIR' | 'EKSIK' | ''."""
    for s in cikti.splitlines():
        if s.startswith("TUR %s " % kod):
            i = s.find("①②③④⑤⑥"[int(o) - 1])
            return s[i + 1:i + 6] if i >= 0 else ""
    return ""


def hazir_ortam(o, kod="isimlik"):
    o.sunucu.ayar["acik"] = [t["kod"] for t in MAN["turler"]]
    o.tarayici = {kod: tarayici_iyi(kod)}


def vakalar(kaynak, sadece=None):
    """sadece: yalniz bu vakalar (mutant kosumu; sure). None = hepsi."""
    s = {}

    def vaka(ad, fn):
        if sadece is not None and ad not in sadece:
            return
        o = Ortam(kaynak)
        try:
            gecti, ac = fn(o)
        except Exception as e:  # cokerse KIRMIZI
            gecti, ac = False, "istisna %s: %s" % (type(e).__name__, e)
        finally:
            o.kapat()
        s[ad] = (gecti, ac)

    def tek(o, kod="isimlik", **ek):
        hazir_ortam(o, kod)
        o.sunucu.ayar["acik"] = [k for k in o.sunucu.ayar["acik"] if k != "plaket"]  # kapali tur = plaket
        return o.kos("--tur", kod, **ek)

    def u1(o):
        rc, son, c = tek(o)
        ok = rc == 0 and son == "HAZIR=1/1 rc=0" and all(olcut(c, "isimlik", x) == "HAZIR" for x in "123456")
        return ok, son if ok else c[-900:]
    vaka("U1", u1)

    def u2(o):
        o.sunucu.ayar["kapali_kod"] = 200
        rc, son, c = tek(o)
        return rc == 2 and son == "HAZIR=0/1 rc=2" and "GECERSIZ" in c, son

    vaka("U2", u2)

    def u3(o):
        rc, son, c = tek(o, FAKE_DELIK="1")
        return rc == 1 and olcut(c, "isimlik", "4") == "EKSIK" and olcut(c, "isimlik", "2") == "HAZIR", son
    vaka("U3", u3)

    def u4(o):
        # Geometri %10 buyuk, olcu.json "dogru" (olcu) der -> YALNIZ bagimsiz eksen olcumu yakalar.
        rc, son, c = tek(o, FAKE_GEO="1.1", FAKE_UK=str(1 / 1.1))
        return rc == 1 and olcut(c, "isimlik", "4") == "EKSIK", son
    vaka("U4", u4)

    def u5(o):
        o.sunucu.ayar["onaysiz_kod"] = 403
        rc, son, c = tek(o)
        return rc == 1 and olcut(c, "isimlik", "5") == "EKSIK" and olcut(c, "isimlik", "4") == "HAZIR", son
    vaka("U5", u5)

    def u6(o):
        o.sunucu.ayar["carpan"] = 900
        rc, son, c = tek(o)
        return rc == 1 and olcut(c, "isimlik", "3") == "EKSIK", son
    vaka("U6", u6)

    def u7(o):
        hazir_ortam(o)
        o.sunucu.ayar["acik"] = ["qr", "logo"]
        rc, son, c = o.kos("--tur", "isimlik")
        return rc == 1 and olcut(c, "isimlik", "1") == "EKSIK", son
    vaka("U7", u7)

    def u8(o):
        hazir_ortam(o)
        o.tarayici["isimlik"]["tasma"] = 6
        o.sunucu.ayar["acik"].remove("plaket")
        rc, son, c = o.kos("--tur", "isimlik")
        return rc == 1 and olcut(c, "isimlik", "6") == "EKSIK", son
    vaka("U8", u8)

    def u9(o):
        hazir_ortam(o)
        o.tarayici["isimlik"]["konsol"] = ["console.error: x"]
        o.sunucu.ayar["acik"].remove("plaket")
        rc, son, c = o.kos("--tur", "isimlik")
        return rc == 1 and olcut(c, "isimlik", "6") == "EKSIK", son
    vaka("U9", u9)

    def u10(o):
        rc, son, c = tek(o, FOTO_UU_TARAYICI_SAHTE="", FOTO_UU_CHROME="0")
        ok = rc == 1 and all(olcut(c, "isimlik", x) == "EKSIK" for x in "356") and olcut(c, "isimlik", "4") == "HAZIR"
        return ok, son
    vaka("U10", u10)

    def u11(o):
        rc, son, c = tek(o, kod="litofan")
        return rc == 0 and son == "HAZIR=1/1 rc=0" and "kol=tarayici" in c, son if rc == 0 else c[-900:]
    vaka("U11", u11)

    def u12(o):
        yol = os.path.join(o.agac, "shop", "wrangler.onizleme.toml")
        with open(yol, encoding="utf-8") as f:
            t = f.read()
        with open(yol, "w", encoding="utf-8") as f:
            f.write(t.replace("pruvo-katalog-onizleme", "pruvo-katalog").replace("pruvo-ozel-onizleme", "pruvo-ozel"))
        rc, son, c = tek(o)
        return rc == 2 and not o.cagrilar(), "%s cagri=%d" % (son, len(o.cagrilar()))
    vaka("U12", u12)

    def u13(o):
        rc, son, c = tek(o)
        hedef = set()
        for a in o.cagrilar():
            hedef.add(a[2] if a[:2] == ["d1", "execute"] else a[3].split("/", 1)[0])
        return rc == 0 and hedef == {"pruvo-katalog-onizleme", "pruvo-ozel-onizleme"}, "hedef=%s" % sorted(hedef)
    vaka("U13", u13)

    def u14(o):
        hazir_ortam(o)
        d = sorted(k for k, t in TUR.items() if t["motor"] == "D")
        o.tarayici = {k: tarayici_iyi(k) for k in d}
        o.sunucu.ayar["acik"].remove("plaket")
        rc, son, c = o.kos("--hepsi", "--kol", "D")
        kosulan = sorted(s.split()[1] for s in c.splitlines() if s.startswith("TUR "))
        return rc == 0 and kosulan == d and son == "HAZIR=%d/%d rc=0" % (len(d), len(d)), "%s %s" % (son, kosulan)
    vaka("U14", u14)

    def u15(o):
        hazir_ortam(o)
        o.tarayici["isimlik"].update(secildi=False, secili_tur="plaket")
        o.sunucu.ayar["acik"].remove("plaket")
        rc, son, c = o.kos("--tur", "isimlik")
        return rc == 1 and all(olcut(c, "isimlik", x) == "EKSIK" for x in "356"), son
    vaka("U15", u15)

    def u16(o):
        rc, son, c = tek(o, FAKE_RAF="1")
        return rc == 0 and olcut(c, "isimlik", "4") == "HAZIR" and "eksen=montaj" in c, son
    vaka("U16", u16)

    def u17(o):
        rc, son, c = tek(o, FAKE_RAF="1", FAKE_UK="1.1")
        return rc == 1 and olcut(c, "isimlik", "4") == "EKSIK", son
    vaka("U17", u17)

    def u18(o):
        rc, son, c = tek(o, FAKE_RAF="1.2")
        return rc == 1 and olcut(c, "isimlik", "4") == "EKSIK" and "eksen=YANLIS" in c, son
    vaka("U18", u18)

    # ---- ORNEK GIRDI (kopru-15 sozluk): saf vakalar — sunucu/D1 YOK; betik kaynagi bellekte yuklenir,
    # uretilen parametre GERCEK VERI.parametreDogrula'dan gecer (node, manifest tek kaynak).
    def saf(ad, fn):
        if sadece is not None and ad not in sadece:
            return
        try:
            ns = {"__name__": "ornek_uc_uca_saf", "__file__": BETIK}
            exec(compile(kaynak, BETIK, "exec"), ns)
            gecti, ac = fn(ns)
        except Exception as e:  # cokerse KIRMIZI
            gecti, ac = False, "istisna %s: %s" % (type(e).__name__, e)
        s[ad] = (gecti, ac)

    def u19(ns):
        # G4a 4 tur (girdi form + bool alan): ornek parametre + dosya hazirlanir, sunucu dogrulamasi ok.
        man = {t["kod"]: t for t in ns["manifest_oku"]()["turler"]}
        p, sebep = {}, []
        for kod in ("kutu", "adaptor", "disli", "kapak"):
            t = man[kod]
            pp, h = ns["ornek_parametre"](t, ns["olcu_sec"](t))
            d, h2 = ns["ornek_dosyalar"](t)
            if pp is None or d is None or not all(t["girdi_acik"]):
                sebep.append("%s:%s%s girdi_acik=%s" % (kod, h, h2, t["girdi_acik"]))
                continue
            p[kod] = pp
        dg = saf_dogrula(p, [])
        bool_ok = p and all(isinstance(p[k][a], bool) for k, a in
                            (("kutu", "kapak"), ("adaptor", "flans"), ("kapak", "topuz")) if k in p)
        ok = not sebep and len(p) == 4 and all(dg[k]["ok"] for k in p) and bool_ok
        return ok, "sebep=%s dogrula=%s" % (sebep, {k: dg[k].get("hata", "ok") for k in dg})
    saf("U19", u19)

    def u20(ns):
        # Bilesen tipler: bool + ses (genlik dizisi, dosya YOK) + konum (sema ornegi) + tarih (saatli/saatsiz).
        t = {"kod": "saf-bilesen", "girdi": ["ses", "konum", "tarih"],
             "form": {"b": {"tip": "bool", "varsayilan": True}, "b2": {"tip": "bool"},
                      "s": {"tip": "ses"}, "k": {"tip": "konum", "ornek": {"enlem": 40.15, "boylam": 29.1}},
                      "d": {"tip": "tarih", "saat": True}, "d2": {"tip": "tarih"}}}
        pp, h = ns["ornek_parametre"](t, 120)
        d, h2 = ns["ornek_dosyalar"](t)
        if pp is None or d is None:
            return False, "desteksiz: %s %s" % (h, h2)
        dg = saf_dogrula({"saf-bilesen": pp}, [t])["saf-bilesen"]
        ok = (dg["ok"] and d == {} and pp["b"] is True and pp["b2"] is False and len(pp["s"]) == 100 and
              pp["k"] == {"enlem": 40.15, "boylam": 29.1} and isinstance(pp["d"], dict) and isinstance(pp["d2"], str))
        return ok, "dogrula=%s dosya=%s" % (dg, d)
    saf("U20", u20)

    def u21(ns):
        # Gercekten bilinmeyen tip/girdi -> sebep adiyla desteksiz (sessiz gecis YOK).
        pp, h = ns["ornek_parametre"]({"form": {"x": {"tip": "renk"}}}, 100)
        d, h2 = ns["ornek_dosyalar"]({"girdi": ["olcu"]})
        return (pp is None and h == "form-tipi-desteksiz:renk" and d is None and h2 == "girdi-desteksiz:olcu",
                "%s | %s" % (h, h2))
    saf("U21", u21)
    return s


SAF_NODE = r"""
const vm=require('vm'),fs=require('fs');const k={};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),k,{filename:'foto-uretim-veri.js'});
const F=k.PRUVO_FOTO, g=JSON.parse(process.argv[2]), ek=JSON.parse(process.argv[3]);
for(const t of ek){F.turler.push(Object.assign({ad:'saf',motor:'D',uretec:'saf',olcu_mm:{en_az:80,en_cok:200},
  fiyat:{formul:'mm_x_10tl',adim_mm:10}},t));}
const r={};for(const kod of Object.keys(g)){r[kod]=F.parametreDogrula(kod,g[kod]);}
process.stdout.write(JSON.stringify(r));
"""


def saf_dogrula(params, ek_turler):
    """GERCEK VERI.parametreDogrula (calisma agacindaki manifest); ek_turler sahte tur satirlari."""
    r = subprocess.run(["node", "-e", SAF_NODE, os.path.join(KOK, "foto-uretim-veri.js"),
                        json.dumps(params), json.dumps(ek_turler)], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError("node: " + r.stderr[:300])
    return json.loads(r.stdout)


MUTANTLAR = {
    "MB1": ("        if not mg:\n            print(\"HAZIR=0/%d rc=2\" % len(kodlar))",
            "        if False:\n            print(\"HAZIR=0/%d rc=2\" % len(kodlar))", {"U2"}),
    "MB2": ('sizd = bool(m) and m["sizdirmaz_nesne"] == m["nesne"]', 'sizd = bool(m)', {"U3"}),
    "MB3": ("eksen = bool(m) and abs(m[\"uzun\"] - tr.olcu) <= tr.olcu * tol + 1e-9", "eksen = bool(m)",
            {"U4", "U16", "U18"}),
    "MB4": ('sunucu_ok = k0 == 400 and j0.get("hata") == "onay-yok" and',
            'sunucu_ok = k0 in (400, 403) and', {"U5"}),
    "MB5": ('all(o.get("fiyat_kurus") == o.get("mm") * 1000 for o in a.get("olculer") or []) and',
            'True and', {"U6"}),
    "MB6": ('        tr.koy("6", False, "tarayici=OLCULEMEDI")\n        return',
            '        tr.koy("6", True, "tarayici=OLCULEMEDI")\n        tr.koy("5", True, "")\n'
            '        tr.koy("3", True, "")\n        return', {"U10"}),
    "MB7": ("    if not d1 or not kova or d1 == cd1 or kova == ckova:", "    if not d1 or not kova:", {"U12"}),
    "MB8": ("    if v is not None and not v.get(\"secildi\"):", "    if False:", {"U15"}),
    "MB9": ('        eksen = (m["parca_en_uzun"] <= tr.olcu * (1 + tol) + 1e-9 and', "        eksen = (True and",
            {"U18"}),
    # kopru-15 sozluk: ornek girdi destegi silinince saf vakalar KIRMIZI.
    "MB10": ('        elif tip == "bool":\n            p[ad] = s.get("varsayilan") is True\n', "", {"U19", "U20"}),
    "MB11": ('elif g in ("form", "metin", "url", "ses", "konum", "tarih"):', 'elif g in ("form", "metin", "url"):',
             {"U20"}),
    "MB12": ('        elif tip == "ses":\n            p[ad] = list(ORNEK_GENLIK)\n', "", {"U20"}),
    "MB13": ('            p[ad] = {"enlem": k["enlem"], "boylam": k["boylam"]}', '            p[ad] = dict(ORNEK_KONUM)',
             {"U20"}),
    "MB14": ('            p[ad] = dict(k) if s.get("saat") is True else k["tarih"]', '            p[ad] = k["tarih"]',
             {"U20"}),
    "MB0": ("# ------------------------------------------------------------------ HTTP",
            "# ------------------------------------------------------------------ HTTP (mutant yorum)", set()),
}


def mutant_kos(ad, kaynak):
    eski, yeni, hedef = MUTANTLAR[ad]
    if kaynak.count(eski) != 1:
        return False, "capa %d kez bulundu" % kaynak.count(eski)
    # SURE (CI adimi <= 300 sn): mutant yalniz hedef vakalari + iki bekci vakada (U1 mutlu yol, U2 mutant
    # kapisi) kosar; hedef disi kirmizi bu kumede aranir. Tam kume her kosumda yukarida (vakalar) olculur.
    s = vakalar(kaynak.replace(eski, yeni), sadece=set(hedef) | {"U1", "U2"})
    kirmizi = {k for k, (g, _) in s.items() if not g}
    return kirmizi == hedef, "kirmizi=%s hedef=%s" % (sorted(kirmizi), sorted(hedef))


def main():
    with open(BETIK, encoding="utf-8") as f:
        kaynak = f.read()
    kirmizi = 0
    for ad, (g, ac) in vakalar(kaynak).items():
        print("%s %s — %s" % ("✅" if g else "❌", ad, ac[:900]))
        kirmizi += 0 if g else 1
    survivor = 0
    if "--mutantsiz" not in sys.argv:
        for ad in MUTANTLAR:
            g, ac = mutant_kos(ad, kaynak)
            print("%s %s — %s" % ("✅" if g else "❌ SURVIVOR", ad, ac))
            survivor += 0 if g else 1
    print("VAKA_KIRMIZI=%d SURVIVOR=%d" % (kirmizi, survivor))
    return 1 if kirmizi or survivor else 0


if __name__ == "__main__":
    sys.exit(main())
