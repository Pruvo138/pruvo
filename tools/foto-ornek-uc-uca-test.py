#!/usr/bin/env python3
"""FOTO `ORNEK-` UCTAN UCA BETIGI — hermetik kabul testi + mutantlar (tools/foto-ornek-uc-uca.py).

HERMETIK: betik IZOLE bir kopya agacta (tempfile) kosar: sahte sunucu (127.0.0.1, /acik + /onizleme +
panel ornek uclari + medya), sahte wrangler (D1 = gecici SQLite, sema tools/d1-sema.sql; R2 = gecici dizin),
sahte kopru (kosucu yerine: kuyruktaki ornek islerine 3MF + olcu.json + onizleme.png yazar; onarim kuyrugu),
sahte tarayici sonucu (FOTO_UU_TARAYICI_SAHTE). Gercek D1/R2/onizleme/ev yolu YOK; her sey tempfile, bitince silinir.

EVREN (sayfa-3adim K3, manifest foto-uretim-veri.js TEK KAYNAK): plaket · figur (motor M, saglayici) · yapboz ·
bust · anahtarlik (motor D, kopru). Sahte /acik GERCEK sunucu gibi yalniz SAYILAN ORNEGI olan turu sunar
(anahtarlik kayitli, ornegi yok -> /acik'te YOK). Sahte /foto/onizleme shop/src/foto.js dallarini taklit eder:
kapali D/R turu -> 503 `kapali` (uretecOnizlemeUcu turHazir once); kapali M / bilinmeyen tur -> 400 `tur-kapali`.
Sahte panel uretim-tik asama kumesi foto.js'ten TURETILIR (tik'in SECMEDIGI asamalar + renk sonrasi asama =
'onarim-bekliyor'; saglayici 3MF'i model.ham.3mf olur, 'hazir'i yalniz yerel kopru yazar).

Vakalar (D kolu varsayilan tur = bust; kapali M tur = plaket): U1 mutlu yol -> HAZIR=1/1 rc=0 · U2 SUNUCU
MUTANTI: kapali tur 200 -> GECERSIZ rc=2 · U2b kapali M tura `gorsel-gecersiz` 400 -> GECERSIZ (bekci `hata`
metnine de bakar) · U2c hicbir M tur kapali degil, yalniz bir D turu kapali (9 Eki'den beri fiksturde kurulur)
-> bekci BILINMEYEN_TUR'a duser, 400 `tur-kapali` -> HAZIR (D kapali tur 503 `kapali` dalina SECILMEZ, 8b0a4a10)
· U3 3MF delik -> (4) EKSIK · U4 olcek ekseni %10 sapma -> (4) EKSIK · U5 sunucu onaysiz istegi kabul (403) ->
(5) EKSIK · U6 /acik fiyati mm x 900 -> (3) EKSIK · U7 tur /acik'ta yok -> (1) EKSIK · U8 375 px tasma 6 ->
(6) EKSIK · U9 konsol hatasi -> (6) EKSIK · U10 tarayici yok -> (3)(5)(6) EKSIK, rc 1 · U12 onizleme toml
canliyla ayni -> rc 2, wrangler cagrisi 0 · U13 yazimlar YALNIZ onizleme D1/kovasina · U14 tur listesi
MANIFESTTEN (--hepsi --kol D = manifestteki 3 D turu; ornegi olmayan anahtarlik (1) EKSIK) · U15 tarayicida
baska tur secili -> (3)(5)(6) EKSIK · U16 cok parcali TABLA duzeni -> (4) HAZIR `eksen=montaj` · U17 ayni duzen
olcu.json %10 sapma -> (4) EKSIK · U18 parca urun olcusunu %20 asiyor -> (4) EKSIK.
SAF: U19 GERCEK manifestin D turleri (yapboz/anahtarlik/bust) ornek parametresi parametreDogrula'dan gecer ·
U20 bilesen tipler (bool/ses/konum/tarih) · U21 desteksiz tip sebep adiyla · U22 kosul + varsayilan ·
U25 kaydin `ornek`i okunur (gercek anahtarlik satirlar + sentetik sayi alani) · P1-P3 3MF p:path.
SAGLAYICI KOLU (--kredi-tavani; tur = plaket, kapali M tur = figur; kredi SUNUCUDA yazilir): S1 tavan 0 ->
②④ OLCULMEZ, panel istegi 0 · S2 tavan 10 -> build oncesi DUR · S3 tavan 100 -> HAZIR=1/1, KREDI_HARCANAN=46/100,
onarim kopru kosusu · S4 tavan 5 -> onizleme istegi 0 · S5 yabanci yarim satir -> DUR, tik 0 · S6 saglayici 3MF
%10 buyuk -> eksen YANLIS · S7 sunucu tahminden pahali -> renk oncesi DUR · S8 makine anahtari yok -> OLCULEMEDI ·
S9 --devam-is 'doku'dan -> ④ HAZIR, 20/30 · S10 --devam-is tavan 0 -> rc 2 · S11 --devam-is bilinmeyen is ·
S12/S13 doku kredisi · S14/S15 onarim kapisi.
Mutantlar (betik kopyasinda capa degisir; capa != 1 kez -> SURVIVOR): MUTANTLAR sozlugu yorumlari.
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
# foto.js: hermetik kopru-15 ONKOSUL bekcisi `shop/src/foto.js` /foto/onizleme icinde TURE RED metnini
# okur; test ortaminda `_red_metni_onizleme()` acabilsin diye KOPYA'ya eklenir.
KOPYA_DOSYALAR = ["foto-uretim-veri.js", "shop/wrangler.toml", "shop/wrangler.onizleme.toml",
                  "shop/src/foto.js", "tools/foto-onizleme.py"]

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
    anahtar = a[3].split("/", 1)[1]
    yol = os.path.join(os.environ["FAKE_R2"], anahtar)
    if a[2] == "get":
        dosya = a[a.index("--file") + 1]
        if not os.path.isfile(yol):
            sys.stderr.write("The specified key does not exist.\n"); sys.exit(1)
        shutil.copyfile(yol, dosya); sys.exit(0)
    if a[2] == "delete":
        if os.path.isfile(yol): os.remove(yol)
        sys.exit(0)
    dosya = a[a.index("--file") + 1]
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
    # TURETILMIS eksen (olcu 0): uretec olcuyu parametreden turetir (sahte: FAKE_TURETIK_MM) -> gercek koşucu
    # gibi OLCULEN uzun kenari (yarim yukari) satira yazar.
    olcu = r["olcu_mm"] or float(os.environ.get("FAKE_TURETIK_MM") or 123.4)
    yaz(os.path.join(R, "foto-uretec-onizleme", r["is_no"]), r["tur"], olcu)
    uk = json.load(open(os.path.join(R, "foto-uretec-onizleme", r["is_no"], "olcu.json")))["uzun_kenar_mm"]
    db.execute("UPDATE foto_isler SET asama='onizleme-hazir', olcu_mm=? WHERE is_no=?",
               (r["olcu_mm"] or int(uk + 0.5), r["is_no"])); n += 1
for r in db.execute("SELECT u.*, i.ziyaretci FROM foto_uretim u LEFT JOIN foto_isler i ON i.is_no=u.is_no"
                    " WHERE u.asama='uretec-bekliyor'").fetchall():
    if r["ziyaretci"] != "ornek" or r["siparis_no"] != "ORNEK-" + r["is_no"][:12]: continue
    yaz(os.path.join(R, "foto", r["siparis_no"], "0"), r["tur"], r["olcu_mm"])
    db.execute("UPDATE foto_uretim SET asama='hazir' WHERE siparis_no=?", (r["siparis_no"],)); n += 1
# ONARIM KUYRUGU (8 Eki): model.ham.3mf -> (kopru) -> model.3mf + 'hazir'. FAKE_ONARIM_YOK: kopru yok, is kuyrukta.
for r in db.execute("SELECT siparis_no, kalem FROM foto_uretim WHERE asama='onarim-bekliyor'").fetchall():
    d = os.path.join(R, "foto", r["siparis_no"], str(r["kalem"]))
    if os.environ.get("FAKE_ONARIM_YOK") or not os.path.isfile(os.path.join(d, "model.ham.3mf")):
        db.commit(); print("HAL=OLCULEMEDI sebep=kopru-yok rc=4"); sys.exit(4)
    os.replace(os.path.join(d, "model.ham.3mf"), os.path.join(d, "model.3mf"))
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
# Sunucu /foto/acik yalniz SAYILAN ORNEGI olan turu sunar (anahtarlik: kayitli, ornegi yok -> /acik'te YOK).
ACIK_EVREN = [t["kod"] for t in MAN["turler"] if t.get("ornekler")]
D_TUR = "bust"      # D kolu (kopru) varsayilan vaka turu — ornegi VAR, /acik'te
KAPALI_M = "plaket"  # tek(): kapatilan saglayici (M) turu -> mutant on kosulu bunu secer


def _sunucu_asamalari():
    """shop/src/foto.js'ten TURETILIR (ikinci sozluk UYDURULMAZ): (1) cron/uretim-tik SELECT'inin SECMEDIGI
    asamalar (`WHERE asama NOT IN (...)`), (2) uretimAdimi 'renk' dalinin satiri tasidigi asama. Bulunamazsa
    test COKER (fail-closed)."""
    import re
    src = open(os.path.join(KOK, "shop", "src", "foto.js"), encoding="utf-8").read()
    m = re.search(r"renk_sayisi FROM foto_uretim WHERE asama NOT IN \(([^)]*)\)", src)
    i = src.find('if (u.asama === "renk") {')
    r = re.search(r'asamaYaz\(env, u, "([a-z-]+)"', src[i:]) if i >= 0 else None
    if not m or not r:
        raise SystemExit("foto.js: uretim-tik asama kumesi / renk sonrasi asama TURETILEMEDI")
    disi = tuple(re.findall(r"'([a-z-]+)'", m.group(1)))
    if r.group(1) not in disi or "hazir" not in disi:
        raise SystemExit("foto.js: renk sonrasi asama %r tik disi kumede DEGIL %r" % (r.group(1), disi))
    return disi, r.group(1)


TIK_DISI, RENK_SONRASI = _sunucu_asamalari()   # bugun: (..., 'onarim-bekliyor'), 'onarim-bekliyor'


def png(w, h):
    ch = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)) +
            ch(b"IDAT", zlib.compress(b"".join(b"\x00" + b"\x80" * w for _ in range(h)))) + ch(b"IEND", b""))


def kutu_3mf(d, L):
    """Saglayici zincirinin olcekli 3MF'i (sahte, PRODUCTION): L x L/2 x 3 su gecirmez kutu.
    Tek bileşen: object_1.model (mesh), root = object id="2" + build <item objectid="2"/> (item transformu yok,
    hedef olcu bu). BambuStudio Production bicimi (gercek akis)."""
    os.makedirs(d, exist_ok=True)
    v = [(x, y, z) for x in (0, L) for y in (0, L / 2) for z in (0, 3.0)]
    t = [(0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3), (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6), (0, 1, 3), (0, 3, 2),
         (4, 6, 7), (4, 7, 5)]
    obj_xml = ('<object id="1" type="model"><mesh><vertices>' +
               "".join('<vertex x="%g" y="%g" z="%g"/>' % p for p in v) + '</vertices><triangles>' +
               "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % q for q in t) +
               '</triangles></mesh></object>')
    kok_xml = ('<model unit="millimeter" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
               'requiredextensions="p"><resources>'
               '<object id="2" type="model"><components>'
               '<component p:path="/3D/Objects/object_1.model" objectid="1"/>'
               '</components></object>'
               '</resources><build><item objectid="2"/></build></model>')
    with zipfile.ZipFile(os.path.join(d, "model.3mf"), "w") as z:
        z.writestr("3D/3dmodel.model", kok_xml)
        z.writestr("3D/Objects/object_1.model", obj_xml)


class Sunucu:
    """Sahte onizleme worker'i. ayar: acik (kod listesi), carpan, kapali_kod (mutant: kapali tur kodu),
    onaysiz_kod (mutant: onaysiz istege donen kod)."""

    def __init__(self):
        self.ayar = {"acik": [], "carpan": 1000, "kapali_kod": 400, "onaysiz_kod": 400, "db": "",
                     "durum_carpan": 1000, "r2": "", "yonet": {}, "gorsel_400_yabanci": False}
        ayar = self.ayar

        def panel(h, yontem, g):
            """Sahte saglayici zinciri (shop/src/foto.js panel ornek uclari + cron uretimAdimi sozlesmesi):
            her ucretli adim foto_kredi'ye SUNUCU yazar. Sayac: ayar['yonet'][uc]."""
            if h.headers.get("X-Onizleme-Makine") != "test-makine" or h.headers.get("X-Yonet-Anahtar"):
                return h.yanit(404, {"hata": "bulunamadi"})
            uc = h.path.split("?", 1)[0][len("/api/shop/yonet"):]
            ayar["yonet"][uc] = ayar["yonet"].get(uc, 0) + 1
            c = sqlite3.connect(ayar["db"])
            simdi = "2026-10-08T00:00:00Z"
            try:
                if uc == "/foto/ornek-onizleme":
                    no = "%032x" % (ayar["yonet"][uc] + 0xabc)
                    c.execute("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, gorev)"
                              " VALUES (?, ?, ?, 'ornek', ?, 'onizleme', ?)", (no, g["tur"], g["olcu_mm"], simdi, "g-" + no))
                    c.execute("INSERT INTO foto_kredi (tarih, adim, is_no, gorev, kredi) VALUES (?, 'onizleme', ?, ?, 6)",
                              (simdi, no, "g-" + no))
                    return h.yanit(200, {"is": no})
                if uc == "/foto/ornek-durum":
                    no = h.path.split("=", 1)[1]
                    # SAGLAYICI-2 devam yolu: bilinmeyen is_no -> 200 asama='yok' (saglayici_2 erken cikar).
                    r = c.execute("SELECT 1 FROM foto_isler WHERE is_no = ?", (no,)).fetchone()
                    if not r:
                        return h.yanit(200, {"is": no, "asama": "yok"})
                    c.execute("UPDATE foto_isler SET asama = 'hazir', hazir_tarih = ? WHERE is_no = ?", (simdi, no))
                    return h.yanit(200, {"is": no, "asama": "hazir"})
                if uc == "/foto/ornek-gorsel":
                    return h.yanit(200, png(1024, 1024), "image/png")
                if uc == "/foto/ornek-uret":
                    r = c.execute("SELECT tur, olcu_mm FROM foto_isler WHERE is_no = ?", (g["is"],)).fetchone()
                    no = "ORNEK-" + g["is"][:12]
                    c.execute("INSERT OR IGNORE INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih,"
                              " guncel) VALUES (?, 0, ?, ?, ?, 'build-baslat', ?, ?)", (no, g["is"], r[0], r[1], simdi, simdi))
                    return h.yanit(200, {"ok": True, "siparis_no": no})
                if uc == "/foto/uretim-tik":
                    # zengin_harita=True: analiz->onarim->doku->renk (kopru-11 SAGLAYICI-2 haritasi).
                    # Default (S1-S8): analiz->renk, bedel build 30 + renk 10 (degismez). renk -> RENK_SONRASI.
                    if ayar.get("zengin_harita"):
                        sonraki = {"build-baslat": "build", "build": "analiz", "analiz": "onarim",
                                   "onarim": "doku", "doku": "renk", "renk": RENK_SONRASI}
                        bedel = {"build": ayar.get("bedel_build", 30), "onarim": 10, "doku": 10, "renk": 10}
                    else:
                        sonraki = {"build-baslat": "build", "build": "analiz", "analiz": "renk", "renk": RENK_SONRASI}
                        bedel = {"build": ayar.get("bedel_build", 30), "renk": 10}
                    # Asama kumesi foto.js'ten (TIK_DISI / RENK_SONRASI): renk -> 'onarim-bekliyor' (ham 3MF
                    # model.ham.3mf + glb); tik o satiri SECMEZ, 'hazir'i yalniz yerel kopru (onarim kuyrugu) yazar.
                    for no, ino, tur, olcu, asama in c.execute(
                            "SELECT siparis_no, is_no, tur, olcu_mm, asama FROM foto_uretim WHERE asama NOT IN"
                            " (%s)" % ", ".join("'%s'" % a for a in TIK_DISI)).fetchall():
                        if asama not in sonraki:
                            return h.yanit(500, {"hata": "sahte-panel-bilinmeyen-asama:" + asama})
                        if asama in bedel:
                            c.execute("INSERT OR IGNORE INTO foto_kredi (tarih, adim, is_no, siparis_no, gorev, kredi)"
                                      " VALUES (?, ?, ?, ?, ?, ?)", (simdi, asama, ino, no, asama + no, bedel[asama]))
                        if sonraki[asama] == RENK_SONRASI:
                            d = os.path.join(ayar["r2"], "foto", no, "0")
                            kutu_3mf(d, olcu * ayar.get("sag_geo", 1.0))
                            os.replace(os.path.join(d, "model.3mf"), os.path.join(d, "model.ham.3mf"))
                            with open(os.path.join(d, "model.glb"), "wb") as f:
                                f.write(b"glTF\x02\x00\x00\x00\x0c\x00\x00\x00")
                        c.execute("UPDATE foto_uretim SET asama = ? WHERE siparis_no = ?", (sonraki[asama], no))
                    return h.yanit(200, {"kuyruga": 0, "ilerleyen": 1})
                return h.yanit(404, {"hata": "bulunamadi"})
            finally:
                c.commit()
                c.close()

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
                if self.path.startswith("/api/shop/yonet/"):
                    return panel(self, "GET", {})
                if self.path == "/api/shop/foto/acik":
                    tl = [{"kod": k, "olculer": [{"mm": mm, "fiyat_kurus": max(mm * ayar["carpan"], TABAN_KURUS)}
                                                 for mm in TUR[k]["olcu_secenekleri"]]} for k in ayar["acik"]]
                    return self.yanit(200, {"acik": bool(tl), "turler": tl, "onay_surum": MAN["onay_surum"]})
                if self.path.startswith("/api/shop/foto/durum?is="):
                    # Sunucu fiyati: satirin KAYITLI olcusu x formul (shop/src/foto.js uretecDurumYaniti).
                    c = sqlite3.connect(ayar["db"])
                    r = c.execute("SELECT tur, olcu_mm, ziyaretci FROM foto_isler WHERE is_no = ?",
                                  (self.path.split("=", 1)[1],)).fetchone()
                    c.close()
                    if not r or r[2] == "ornek":
                        return self.yanit(404, {"hata": "bulunamadi"})
                    return self.yanit(200, {"asama": "hazir", "tur": r[0], "olcu_mm": r[1], "olcu_kaynagi": "turetilmis",
                                            "fiyat_kurus": max(r[1] * ayar["durum_carpan"], TABAN_KURUS)})
                if self.path.startswith("/medya/"):
                    return self.yanit(200, b"RIFF0000WEBP", "image/webp")
                self.yanit(404, {"hata": "yok"})

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                g = json.loads(self.rfile.read(n) or b"{}")
                if self.path.startswith("/api/shop/yonet/"):
                    return panel(self, "POST", g)
                t = TUR.get(g.get("tur")) or {}
                if g.get("tur") not in ayar["acik"] and t.get("motor") in ("D", "R") and \
                        not t.get("tarayici_onizleyici"):
                    # shop/src/foto.js onizlemeUcu: uretec (D/R) turu uretecOnizlemeUcu'na gider, orada
                    # turHazir ONCE -> kapali D/R tur 503 `kapali` (bugun: anahtarlik, ornegi yok).
                    return self.yanit(503, {"hata": "kapali"})
                if g.get("tur") not in ayar["acik"]:
                    # Kopru-15: mutant on-kosulunun "tip kapisi KAPALI" olcumunu test etmek icin:
                    # kapali_kod=400 + gorsel_400_yabanci=True -> 400 `gorsel-gecersiz` (kapidan GECMIS,
                    # gercek figur senaryosu); aksi normal — kapali_kod=400 `tur-kapali`, 200/200 ise gec.
                    k = ayar["kapali_kod"]
                    if k == 400 and ayar.get("gorsel_400_yabanci"):
                        return self.yanit(400, {"hata": "gorsel-gecersiz"})
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


# Sahte sunucu/tarayici gercek formulu taklit eder: max(600 TL, mm × 10 TL) (Okan 8 Eki tabani).
TABAN_KURUS = 60000


def tarayici_iyi(kod, olculen=123):
    t = TUR[kod]
    uc = t["olcu_secenekleri"][-1]
    v = {"secildi": True, "secili_tur": kod, "surgu": True,
         "fiyat": "%d mm → %s TL" % (uc, "{:,}".format(max(uc * 1000, TABAN_KURUS) // 100).replace(",", ".")),
         "onay_kutusu": 1, "onaysiz_dugme_kapali": True, "durustluk": t["durustluk"], "tasma": 0,
         "genislik": 375, "konsol": [], "olculen_not": False}
    if t.get("turetilmis"):
        # Surgu YOK (S1 not var); S3 onizleme olcusu (sahte kopru 123.4 -> 123) ile fiyat yazisi.
        v.update(surgu=False, fiyat="", olculen_not=True, s3_surgu=False,
                 olculen_fiyat="%d mm → %s TL" % (olculen, "{:,}".format(max(olculen * 1000, TABAN_KURUS) // 100).replace(",", ".")))
    return v


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
        self.sunucu.ayar["db"] = self.db
        self.sunucu.ayar["r2"] = self.r2
        self.tarayici = {}
        self.env = dict(os.environ, FAKE_DB=self.db, FAKE_R2=self.r2, FAKE_LOG=self.log,
                        FOTO_UU_TABAN=self.sunucu.taban,
                        FOTO_UU_MEDYA_ESLE="https://media.pruvo3d.com=%s/medya" % self.sunucu.taban,
                        FOTO_UU_WRANGLER="%s %s" % (sys.executable, os.path.join(self.d, "wr.py")),
                        FOTO_UU_KOSUCU=os.path.join(self.d, "kopru.py"), FOTO_UU_BEKLE_SN="0",
                        FOTO_UU_TARAYICI_SAHTE=os.path.join(self.d, "tarayici.json"),
                        ONIZLEME_MAKINE_ANAHTARI="test-makine", FOTO_UU_YOKLA_SN="0", PYTHONDONTWRITEBYTECODE="1")
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


def hazir_ortam(o, kod=D_TUR):
    # sayfa-3adim K3: sahte /acik = ORNEGI OLAN turler (gercek sunucu; anahtarlik kayitli ama ornegi yok).
    # Varsayilan vaka turu D kolu (bust): saglayici (M) kolu kredisiz kosumda OLCULMEZ, S* vakalari olcer.
    o.sunucu.ayar["acik"] = list(ACIK_EVREN)
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

    def tek(o, kod=D_TUR, **ek):
        hazir_ortam(o, kod)
        o.sunucu.ayar["acik"] = [k for k in o.sunucu.ayar["acik"] if k != KAPALI_M]  # kapali M tur = plaket
        return o.kos("--tur", kod, **ek)

    def u1(o):
        rc, son, c = tek(o)
        ok = rc == 0 and son == "HAZIR=1/1 rc=0" and all(olcut(c, D_TUR, x) == "HAZIR" for x in "123456")
        return ok, son if ok else c[-900:]
    vaka("U1", u1)

    def u2(o):
        o.sunucu.ayar["kapali_kod"] = 200
        rc, son, c = tek(o)
        return rc == 2 and son == "HAZIR=0/1 rc=2" and "GECERSIZ" in c, son

    vaka("U2", u2)

    def u2b(o):
        # Kopru-15: kapali M tura (plaket) sahte sunucu "gorsel-gecersiz" 400 -> bekci YANLIS gecmis
        # 400'u MUTLU yol sanmamali (`hata` tur-kapali olmadigi icin GECERSIZ).
        o.sunucu.ayar["gorsel_400_yabanci"] = True
        rc, son, c = tek(o)
        ok = rc == 2 and son == "HAZIR=0/1 rc=2" and "GECERSIZ" in c
        return ok, son if not ok else c[-900:]

    vaka("U2b", u2b)

    def u2c(o):
        # 8b0a4a10 sozlesmesi: hicbir M tur kapali degil; /acik'te olmayan tek tur bir D turu -> sunucuda 503
        # `kapali`. Bekci onu SECMEZ (yalniz motor M), BILINMEYEN_TUR'a duser -> 400 `tur-kapali` -> GECERLI,
        # HAZIR. D turu secerse 503 -> GECERSIZ rc 2 (MB33). 9 Eki: anahtarlik ornegi geldi, manifestte kapali D
        # turu kalmadi -> senaryo FIKSTURDE kurulur (D_TUR disindaki ilk D turu /acik'ten cikarilir).
        hazir_ortam(o)
        if all(k in o.sunucu.ayar["acik"] for k in TUR if TUR[k]["motor"] == "D"):
            o.sunucu.ayar["acik"].remove(sorted(k for k in TUR if TUR[k]["motor"] == "D" and k != D_TUR)[0])
        kapali = [k for k in TUR if k not in o.sunucu.ayar["acik"]]
        if [TUR[k]["motor"] for k in kapali] != ["D"]:
            return False, "on kosul: kapali turler yalniz tek D tur olmali, bulunan %s" % kapali
        rc, son, c = o.kos("--tur", D_TUR)
        ok = rc == 0 and son == "HAZIR=1/1 rc=0" and all(olcut(c, D_TUR, x) == "HAZIR" for x in "123456") and \
            "GECERSIZ" not in c and "yok_tur=uu-yok-tur kod=400 hata=tur-kapali" in c
        return ok, son if ok else c[-900:]

    vaka("U2c", u2c)

    def u3(o):
        rc, son, c = tek(o, FAKE_DELIK="1")
        return rc == 1 and olcut(c, D_TUR, "4") == "EKSIK" and olcut(c, D_TUR, "2") == "HAZIR", son
    vaka("U3", u3)

    def u4(o):
        # Geometri %10 buyuk, olcu.json "dogru" (olcu) der -> YALNIZ bagimsiz eksen olcumu yakalar.
        rc, son, c = tek(o, FAKE_GEO="1.1", FAKE_UK=str(1 / 1.1))
        return rc == 1 and olcut(c, D_TUR, "4") == "EKSIK", son
    vaka("U4", u4)

    def u5(o):
        o.sunucu.ayar["onaysiz_kod"] = 403
        rc, son, c = tek(o)
        return rc == 1 and olcut(c, D_TUR, "5") == "EKSIK" and olcut(c, D_TUR, "4") == "HAZIR", son
    vaka("U5", u5)

    def u6(o):
        o.sunucu.ayar["carpan"] = 900
        rc, son, c = tek(o)
        return rc == 1 and olcut(c, D_TUR, "3") == "EKSIK", son
    vaka("U6", u6)

    # SAGLAYICI KOLU (kopru-15 SAGLAYICI-2): --kredi-tavani. Olculen tur plaket (ACIK); kapali M tur = figur
    # (mutant on kosulu yalniz M kapali turu secer, 8b0a4a10).
    def sag(o, tavan, devam_is="", **ek):
        hazir_ortam(o, "plaket")
        o.sunucu.ayar["acik"] = [k for k in o.sunucu.ayar["acik"] if k != "figur"]
        args = ["--tur", "plaket", "--kredi-tavani", str(tavan)]
        if devam_is:
            args += ["--devam-is", devam_is]
        rc, son, c = o.kos(*args, **ek)
        return rc, son, c, o.sunucu.ayar["yonet"]

    def s1(o):
        rc, son, c, y = sag(o, 0)
        ok = (olcut(c, "plaket", "2") == "EKSIK" and olcut(c, "plaket", "4") == "EKSIK" and "OLCULMEZ" in c and
              sum(y.values()) == 0 and "KREDI_HARCANAN" not in c)
        return ok, "yonet=%s %s" % (y, son)
    vaka("S1", s1)

    def s2(o):
        rc, son, c, y = sag(o, 10)
        ok = (olcut(c, "plaket", "2") == "HAZIR" and olcut(c, "plaket", "4") == "EKSIK" and "kredi-tavani" in c and
              y.get("/foto/uretim-tik", 0) == 0 and "KREDI_HARCANAN=6/10" in c)
        return ok, "yonet=%s %s" % (y, c[-600:])
    vaka("S2", s2)

    def s3(o):
        rc, son, c, y = sag(o, 100)
        # Tam zincir: renk -> 'onarim-bekliyor' (foto.js) -> betik kopruyu BIR kez kosar -> 'hazir' -> ④.
        # Plaket olcu 10..300: ③ /acik fiyatlari 60 mm alti TABANLI (MB32 burada yakalanir).
        ok = (rc == 0 and son == "HAZIR=1/1 rc=0" and all(olcut(c, "plaket", x) == "HAZIR" for x in "123456") and
              "KREDI_HARCANAN=46/100" in c and "KOPRU onarim: HAL=ISLEDI" in c)
        return ok, "yonet=%s %s" % (y, c[-900:])
    vaka("S3", s3)

    def s4(o):
        rc, son, c, y = sag(o, 5)
        ok = (olcut(c, "plaket", "2") == "EKSIK" and "kredi-tavani" in c and y.get("/foto/ornek-onizleme", 0) == 0)
        return ok, "yonet=%s %s" % (y, son)
    vaka("S4", s4)

    def s5(o):
        # Kuyrukta yabanci yarim satir: tik onu da ilerletir -> DUR, tik 0.
        c0 = sqlite3.connect(o.db)
        c0.execute("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel)"
                   " VALUES ('PRV-1', 0, ?, 'plaket', 100, 'build', 't', 't')", ("f" * 32,))
        c0.commit()
        c0.close()
        rc, son, c, y = sag(o, 100)
        ok = olcut(c, "plaket", "4") == "EKSIK" and "yabanci-kuyruk=1" in c and y.get("/foto/uretim-tik", 0) == 0
        return ok, "yonet=%s %s" % (y, c[-600:])
    vaka("S5", s5)

    def s6(o):
        o.sunucu.ayar["sag_geo"] = 1.1   # saglayici 3MF'i %10 buyuk (olcek kapisi kacirdi)
        rc, son, c, y = sag(o, 100)
        return olcut(c, "plaket", "4") == "EKSIK" and "eksen=YANLIS" in c, c[-600:]
    vaka("S6", s6)

    def s7(o):
        # Sunucu build'i tahminden pahali yazar (50): kapi D1 FARKINI da okur -> renk oncesi DUR.
        o.sunucu.ayar["bedel_build"] = 50
        rc, son, c, y = sag(o, 60)
        ok = olcut(c, "plaket", "4") == "EKSIK" and "kredi-tavani 56+10>60" in c
        return ok, "yonet=%s %s" % (y, c[-600:])
    vaka("S7", s7)

    def s8(o):
        # Makine anahtari yok: panel SIFRESINE dusmez (X-Yonet-Anahtar gonderilmez), kosum OLCULEMEDI.
        rc, son, c, y = sag(o, 100, ONIZLEME_MAKINE_ANAHTARI="", YONET_ANAHTAR="test-yonet")
        return rc == 2 and "OLCULEMEDI ONIZLEME_MAKINE_ANAHTARI yok" in c and sum(y.values()) == 0, "yonet=%s %s" % (y, son)
    vaka("S8", s8)

    # kopru-15 SAGLAYICI-2 devam yolu (--devam-is): park etmis saglayici zincirini YENI onizleme acmadan surdur.
    def s9(o):
        # Pre-seed foto_isler (ziyaretci 'ornek', asama 'hazir') + foto_uretim ('doku' satir). zengin harita ile
        # uretim-tik doku->renk->hazir; /foto/ornek-onizleme 0; yalniz yeni adim kredisi (doku 10 + renk 10 = 20).
        # plaket olcu_secenekleri ortanca = 160 (10..300 = 30 olcu, s[len//2], 8 Eki) (betigin tr.olcu'su) — 100 yazarsak eksen YANLIS olur.
        is_no = "f" * 32
        no = "ORNEK-" + is_no[:12]
        c0 = sqlite3.connect(o.db)
        c0.execute("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, hazir_tarih, gorev)"
                   " VALUES (?, 'plaket', 160, 'ornek', 't', 'hazir', 't', 'g')", (is_no,))
        c0.execute("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel)"
                   " VALUES (?, 0, ?, 'plaket', 160, 'doku', 't', 't')", (no, is_no))
        c0.commit()
        c0.close()
        o.sunucu.ayar["zengin_harita"] = True
        rc, son, c, y = sag(o, 30, devam_is=is_no)
        ok = (olcut(c, "plaket", "2") == "HAZIR" and olcut(c, "plaket", "4") == "HAZIR" and
              y.get("/foto/ornek-onizleme", 0) == 0 and y.get("/foto/ornek-uret", 0) == 1 and
              y.get("/foto/uretim-tik", 0) == 2 and "KREDI_HARCANAN=20/30" in c)
        return ok, "yonet=%s %s" % (y, c[-600:])
    vaka("S9", s9)

    def s10(o):
        # --devam-is ile tavan 0: erken HATA + rc 2, panel istegi 0.
        is_no = "f" * 32
        c0 = sqlite3.connect(o.db)
        c0.execute("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, hazir_tarih, gorev)"
                   " VALUES (?, 'plaket', 100, 'ornek', 't', 'hazir', 't', 'g')", (is_no,))
        c0.execute("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel)"
                   " VALUES ('ORNEK-' || substr(?, 1, 12), 0, ?, 'plaket', 100, 'doku', 't', 't')",
                   (is_no, is_no))
        c0.commit()
        c0.close()
        rc, son, c, y = sag(o, 0, devam_is=is_no)
        ok = rc == 2 and "HATA --devam-is" in c and sum(y.values()) == 0
        return ok, "yonet=%s %s" % (y, son)
    vaka("S10", s10)

    def s11(o):
        # --devam-is bilinmeyen is: ornek-onizleme 0, ornek-durum 'yok' erken cikar -> ② EKSIK.
        is_no = "f" * 32  # tohumlanmamis
        rc, son, c, y = sag(o, 100, devam_is=is_no)
        ok = (olcut(c, "plaket", "2") == "EKSIK" and y.get("/foto/ornek-onizleme", 0) == 0 and
              y.get("/foto/ornek-durum", 0) == 1 and olcut(c, "plaket", "4") == "EKSIK")
        return ok, "yonet=%s %s" % (y, c[-600:])
    vaka("S11", s11)

    # kopru-15 KREDI-DOKU: KREDI_TIK["doku"]=0 (doku Tikin BASLAYABILECEK ucretli adim yok; re-analiz
    # ucretsiz — gercek zincir analiz->onarim->doku->analiz->renk). S12: tam zincir analiz'den --devam-is,
    # KREDI_ONIZLEME ayrilmaz, zengin harita uretim-tik analiz->onarim->doku->renk->hazir yapar;
    # BETIK rezervasyon = analiz 10 + onarim 10 = 20, D1 fark = onarim+doku+renk = 30, cikti 30/30.
    # ayrilan=20 ile MB30 (doku=10) ayrilan=30 — S12 KIRMIZI.
    def s12(o):
        is_no = "f" * 32
        no = "ORNEK-" + is_no[:12]
        c0 = sqlite3.connect(o.db)
        c0.execute("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, hazir_tarih, gorev)"
                   " VALUES (?, 'plaket', 160, 'ornek', 't', 'hazir', 't', 'g')", (is_no,))
        c0.execute("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel)"
                   " VALUES (?, 0, ?, 'plaket', 160, 'analiz', 't', 't')", (no, is_no))
        c0.commit()
        c0.close()
        o.sunucu.ayar["zengin_harita"] = True
        rc, son, c, y = sag(o, 30, devam_is=is_no)
        ok = (olcut(c, "plaket", "2") == "HAZIR" and olcut(c, "plaket", "4") == "HAZIR" and
              y.get("/foto/ornek-onizleme", 0) == 0 and y.get("/foto/uretim-tik", 0) == 4 and
              "KREDI_HARCANAN=30/30" in c and "ayrilan=20" in c)
        return ok, "yonet=%s %s" % (y, c[-600:])
    vaka("S12", s12)

    # S13: ayni zincir, tavan 29: BETIK `ayir` (Tik basinda) sonraki adimi gordugu icin onceden yakalayamiyor
    # (max cum = 20 < 29). POST-sonrasi D1 kontrolu yakalar: Iter 4 (renk) POST'unda D1 fark 30 > 29 DUR;
    # hata "kredi-tavani D1 30>29 (POST sonrasi, renk oncesi DUR)" — kabul.
    def s13(o):
        is_no = "f" * 32
        no = "ORNEK-" + is_no[:12]
        c0 = sqlite3.connect(o.db)
        c0.execute("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, hazir_tarih, gorev)"
                   " VALUES (?, 'plaket', 160, 'ornek', 't', 'hazir', 't', 'g')", (is_no,))
        c0.execute("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel)"
                   " VALUES (?, 0, ?, 'plaket', 160, 'analiz', 't', 't')", (no, is_no))
        c0.commit()
        c0.close()
        o.sunucu.ayar["zengin_harita"] = True
        rc, son, c, y = sag(o, 29, devam_is=is_no)
        ok = (olcut(c, "plaket", "4") == "EKSIK" and
              "kredi-tavani D1 30>29 (POST sonrasi, renk oncesi DUR)" in c)
        return ok, "yonet=%s %s" % (y, c[-600:])
    vaka("S13", s13)

    # S14/S15 ONARIM KAPISI (8 Eki): satir 'onarim-bekliyor' (saglayici ham 3MF R2'de) -> betik kosucuyu BIR kez
    # kosar (kredi 0, uretim-tik 0) -> 'hazir' -> ④ olculur. S15: kopru yok -> satir bekler -> ④ EKSIK + sebep.
    def onarim_tohum(o):
        is_no = "e" * 32
        no = "ORNEK-" + is_no[:12]
        c0 = sqlite3.connect(o.db)
        c0.execute("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, hazir_tarih, gorev)"
                   " VALUES (?, 'plaket', 160, 'ornek', 't', 'hazir', 't', 'g')", (is_no,))
        c0.execute("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, tarih, guncel)"
                   " VALUES (?, 0, ?, 'plaket', 160, 'onarim-bekliyor', 't', 't')", (no, is_no))
        c0.commit()
        c0.close()
        d = os.path.join(o.sunucu.ayar["r2"], "foto", no, "0")
        kutu_3mf(d, 160)
        os.replace(os.path.join(d, "model.3mf"), os.path.join(d, "model.ham.3mf"))
        with open(os.path.join(d, "model.glb"), "wb") as f:
            f.write(b"glTF\x02\x00\x00\x00\x0c\x00\x00\x00")
        return is_no

    def s14(o):
        is_no = onarim_tohum(o)
        rc, son, c, y = sag(o, 1, devam_is=is_no)
        ok = (olcut(c, "plaket", "4") == "HAZIR" and y.get("/foto/uretim-tik", 0) == 0 and
              "KOPRU onarim: HAL=ISLEDI" in c and "KREDI_HARCANAN=0/1" in c)
        return ok, "yonet=%s %s" % (y, c[-600:])
    vaka("S14", s14)

    def s15(o):
        is_no = onarim_tohum(o)
        rc, son, c, y = sag(o, 1, devam_is=is_no, FAKE_ONARIM_YOK="1")
        ok = (olcut(c, "plaket", "4") == "EKSIK" and "onarim-bekliyor kosucu sonrasi da" in c and
              y.get("/foto/uretim-tik", 0) == 0)
        return ok, "yonet=%s %s" % (y, c[-600:])
    vaka("S15", s15)

    def u7(o):
        hazir_ortam(o)
        o.sunucu.ayar["acik"] = [k for k in ACIK_EVREN if k != D_TUR]
        rc, son, c = o.kos("--tur", D_TUR)
        return rc == 1 and olcut(c, D_TUR, "1") == "EKSIK" and "acik=0" in c, son
    vaka("U7", u7)

    def u8(o):
        hazir_ortam(o)
        o.tarayici[D_TUR]["tasma"] = 6
        o.sunucu.ayar["acik"].remove(KAPALI_M)
        rc, son, c = o.kos("--tur", D_TUR)
        return rc == 1 and olcut(c, D_TUR, "6") == "EKSIK", son
    vaka("U8", u8)

    def u9(o):
        hazir_ortam(o)
        o.tarayici[D_TUR]["konsol"] = ["console.error: x"]
        o.sunucu.ayar["acik"].remove(KAPALI_M)
        rc, son, c = o.kos("--tur", D_TUR)
        return rc == 1 and olcut(c, D_TUR, "6") == "EKSIK", son
    vaka("U9", u9)

    def u10(o):
        rc, son, c = tek(o, FOTO_UU_TARAYICI_SAHTE="", FOTO_UU_CHROME="0")
        ok = rc == 1 and all(olcut(c, D_TUR, x) == "EKSIK" for x in "356") and olcut(c, D_TUR, "4") == "HAZIR"
        return ok, son
    vaka("U10", u10)

    # K3a (8 Eki 2026): U11 (litofan tarayici onizleyici kolu) SİLİNDİ — litofan artık yok.
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
        # Kosulan kume = manifestteki TUM D turleri (anahtarlik dahil); 9 Eki'den beri ucunun de ornegi VAR ->
        # ornegsiz D turu 0, HAZIR 3/3 rc 0. Ornek kaydi duserse ornksiz bos olmaz -> KIRMIZI. Sayilar manifestten.
        hazir_ortam(o)
        d = sorted(k for k, t in TUR.items() if t["motor"] == "D")
        dz = [k for k in d if TUR[k].get("ornekler")]
        o.tarayici = {k: tarayici_iyi(k) for k in d}
        o.sunucu.ayar["acik"].remove(KAPALI_M)
        rc, son, c = o.kos("--hepsi", "--kol", "D")
        kosulan = sorted(s.split()[1] for s in c.splitlines() if s.startswith("TUR "))
        ornksiz = [k for k in d if k not in dz]
        ok = (kosulan == d and len(d) == 3 and ornksiz == [] and
              rc == 0 and son == "HAZIR=%d/%d rc=0" % (len(d), len(d)) and
              all(olcut(c, k, x) == "HAZIR" for k in d for x in "123456") and "ornek=0 " not in c)
        return ok, "%s %s" % (son, kosulan)
    vaka("U14", u14)

    # K3a (8 Eki 2026): U23/U24 (kutu türetilmiş eksen + esitlik kolu) SİLİNDİ — kutu türetilmiş kalkti;
    # evrendeki 5 türün hiçbiri `turetilmis` değil (sabit eksen), türetilmiş eksen testi anlamsız.
    def u15(o):
        hazir_ortam(o)
        o.tarayici[D_TUR].update(secildi=False, secili_tur="yapboz")
        o.sunucu.ayar["acik"].remove(KAPALI_M)
        rc, son, c = o.kos("--tur", D_TUR)
        return rc == 1 and all(olcut(c, D_TUR, x) == "EKSIK" for x in "356"), son
    vaka("U15", u15)

    def u16(o):
        rc, son, c = tek(o, FAKE_RAF="1")
        return rc == 0 and olcut(c, D_TUR, "4") == "HAZIR" and "eksen=montaj" in c, son
    vaka("U16", u16)

    def u17(o):
        rc, son, c = tek(o, FAKE_RAF="1", FAKE_UK="1.1")
        return rc == 1 and olcut(c, D_TUR, "4") == "EKSIK", son
    vaka("U17", u17)

    def u18(o):
        rc, son, c = tek(o, FAKE_RAF="1.2")
        return rc == 1 and olcut(c, D_TUR, "4") == "EKSIK" and "eksen=YANLIS" in c, son
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
        # GERCEK manifestin D kolu turleri (yapboz/anahtarlik/bust — form + bool alan): ornek parametre + dosya
        # hazirlanir, GERCEK VERI.parametreDogrula ok; bust'in bool alanlari (ters/iki_renk) bool.
        man = {t["kod"]: t for t in ns["manifest_oku"]()["turler"]}
        kodlar = sorted(k for k, t in man.items() if t["motor"] == "D")
        p, sebep = {}, []
        for kod in kodlar:
            t = man[kod]
            pp, h = ns["ornek_parametre"](t, ns["olcu_sec"](t))
            d, h2 = ns["ornek_dosyalar"](t)
            if pp is None or d is None or not all(t["girdi_acik"]):
                sebep.append("%s:%s%s girdi_acik=%s" % (kod, h, h2, t["girdi_acik"]))
                continue
            p[kod] = pp
        dg = saf_dogrula(p, [])
        bool_ok = "bust" in p and all(isinstance(p["bust"][a], bool) for a in ("ters", "iki_renk"))
        ok = (not sebep and kodlar == ["anahtarlik", "bust", "yapboz"] and len(p) == 3 and
              all(dg[k]["ok"] for k in p) and bool_ok)
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
        # Sunucu dogrulamasi YALNIZ manifestin bugun tanidigi form tiplerinde (VERI.FORM_TIPLERI; K3: sayi/secim/
        # metin/bool — ses/konum/tarih silinen turlerle kalkti, sunucu `parametre-yakinda` der). ses/konum/tarih
        # dallari betikte DURDUGU icin uretimleri (MB11-MB14) yine olculur; dogrulama alt kumesi bos OLAMAZ.
        tipler = saf_form_tipleri()
        fd = {ad: sm for ad, sm in t["form"].items() if sm["tip"] in tipler}
        td = {"kod": "saf-bilesen", "girdi": ["form"], "form": fd}
        dg = saf_dogrula({"saf-bilesen": {ad: pp[ad] for ad in fd}}, [td])["saf-bilesen"]
        ok = ("bool" in tipler and set(fd) == {"b", "b2"} and dg["ok"] and d == {} and pp["b"] is True and
              pp["b2"] is False and len(pp["s"]) == 100 and pp["k"] == {"enlem": 40.15, "boylam": 29.1} and
              isinstance(pp["d"], dict) and isinstance(pp["d2"], str))
        return ok, "tipler=%s dogrula=%s dosya=%s" % (sorted(tipler), dg, d)
    saf("U20", u20)

    def u21(ns):
        # Gercekten bilinmeyen tip/girdi -> sebep adiyla desteksiz (sessiz gecis YOK).
        pp, h = ns["ornek_parametre"]({"form": {"x": {"tip": "renk"}}}, 100)
        d, h2 = ns["ornek_dosyalar"]({"girdi": ["olcu"]})
        return (pp is None and h == "form-tipi-desteksiz:renk" and d is None and h2 == "girdi-desteksiz:olcu",
                "%s | %s" % (h, h2))
    saf("U21", u21)

    def u22(ns):
        # kopru-15 DILIM-2: kosulu saglanmayan alan ornege GIRMEZ; gecerli varsayilan (adim 0.01) KULLANILIR,
        # gecersiz varsayilan (izgara disi) eski formule duser; sunucu dogrulamasi (kosul dahil) ok.
        t = {"kod": "saf-kosul", "girdi": ["form"],
             "form": {"mod": {"tip": "secim", "secenekler": ["pul", "burc", "adaptor"], "varsayilan": "burc"},
                      "kademe_mm": {"tip": "sayi", "min": 6, "max": 150, "adim": 0.01, "varsayilan": 14,
                                    "kosul": [{"alan": "mod", "degerler": ["adaptor"]}]},
                      "flans": {"tip": "bool", "varsayilan": False,
                                "kosul": [{"alan": "mod", "degerler": ["burc", "adaptor"]}]},
                      "flans_cap_mm": {"tip": "sayi", "min": 8, "max": 150, "adim": 0.01, "varsayilan": 30,
                                       "kosul": [{"alan": "flans", "degerler": [True]}]},
                      "duvar_mm": {"tip": "sayi", "min": 1.2, "max": 4, "adim": 0.01, "varsayilan": 1.6},
                      "kaba_mm": {"tip": "sayi", "min": 2, "max": 9, "adim": 1, "varsayilan": 2.5}}}
        pp, h = ns["ornek_parametre"](t, 120)
        if pp is None:
            return False, "desteksiz: %s" % h
        dg = saf_dogrula({"saf-kosul": pp}, [t])["saf-kosul"]
        ok = dg["ok"] and pp == {"mod": "burc", "flans": False, "duvar_mm": 1.6, "kaba_mm": 9}
        return ok, "p=%s dogrula=%s" % (pp, dg)
    saf("U22", u22)

    def u25(ns):
        # kopru-15 SON3: kaydin `ornek`i (kopru-manifest-uret tasir) ONCE okunur. Metin: GERCEK anahtarlik
        # `satirlar` ornegi ["Ayşe"] (okunmazsa formul ["PRUVO"]). Sayi: gercek manifestte ornek == varsayilan
        # (ayrim olcmez) -> sentetik alan ornek 7 / varsayilan 5 (okunmazsa 5). Ikisi de parametreDogrula ok.
        man = {t["kod"]: t for t in ns["manifest_oku"]()["turler"]}
        ta = man["anahtarlik"]
        pa, h = ns["ornek_parametre"](ta, ns["olcu_sec"](ta))
        ts = {"kod": "saf-ornek", "girdi": ["form"],
              "form": {"adet": {"tip": "sayi", "min": 1, "max": 9, "adim": 1, "varsayilan": 5, "ornek": 7}}}
        ps, h2 = ns["ornek_parametre"](ts, 120)
        if pa is None or ps is None:
            return False, "desteksiz: %s %s" % (h, h2)
        dg = saf_dogrula({"anahtarlik": pa}, [])
        dg.update(saf_dogrula({"saf-ornek": ps}, [ts]))
        ok = (ta["form"]["satirlar"].get("ornek") == ["Ayşe"] and pa["satirlar"] == ["Ayşe"] and ps == {"adet": 7}
              and all(dg[k]["ok"] for k in dg))
        return ok, "satirlar=%r adet=%r dogrula=%s" % (pa.get("satirlar"), ps.get("adet"),
                                                       {k: dg[k].get("hata", "ok") for k in dg})
    saf("U25", u25)

    # ---- 3MF cok-dosya (p:path, BambuStudio Production): saf vakalar P1/P2/P3. Sentetik 3MF yazici (yalniz
    # test, disk izi YOK): kok = object id="2" + build item <item objectid="2" scale=olcek>, alt =
    # 12-ucgenli kapali kutu alt_L x alt_W x alt_H. P3: alt dosya zip'e yazilmaz (p:path hedefi YOK).
    def saf_3mf_uretim(olcek=0.5, alt_L=200, alt_W=100, alt_H=6, eksik_ucgen=False, alt_var=True):
        v = [(x, y, z) for x in (0, alt_L) for y in (0, alt_W) for z in (0, alt_H)]
        t = [(0, 2, 6), (0, 6, 4), (1, 5, 7), (1, 7, 3), (0, 4, 5), (0, 5, 1), (2, 3, 7), (2, 7, 6), (0, 1, 3),
             (0, 3, 2), (4, 6, 7), (4, 7, 5)]
        if eksik_ucgen:
            t = t[:-1]
        obj_xml = ('<object id="1" type="model"><mesh><vertices>' +
                   "".join('<vertex x="%g" y="%g" z="%g"/>' % p for p in v) + '</vertices><triangles>' +
                   "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % q for q in t) +
                   '</triangles></mesh></object>')
        kok_xml = ('<model unit="millimeter" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
                   'requiredextensions="p"><resources>'
                   '<object id="2" type="model"><components>'
                   '<component p:path="/3D/Objects/object_1.model" objectid="1"/>'
                   '</components></object>'
                   '</resources><build>'
                   '<item objectid="2" transform="%g 0 0 0 %g 0 0 0 %g 0 0 0"/>' % (olcek, olcek, olcek) +
                   '</build></model>')
        d = tempfile.mkdtemp(prefix="p3mf-")
        yol = os.path.join(d, "model.3mf")
        with zipfile.ZipFile(yol, "w") as z:
            z.writestr("3D/3dmodel.model", kok_xml)
            if alt_var:
                z.writestr("3D/Objects/object_1.model", obj_xml)
        return yol, d

    def p1(ns):
        # iki girdili sentetik 3MF: kok = bileşen p:path + item ölçek 0.5, alt = 12 üçgenli kapalı kutu
        # 200×100×6 → nesne 1, sızdırmaz 1, kutu (100, 50, 3).
        yol, d = saf_3mf_uretim()
        try:
            m = ns["uc_mf_olc"](yol)
            ok = (m is not None and m["nesne"] == 1 and m["sizdirmaz_nesne"] == 1 and
                  tuple(round(x, 3) for x in m["kutu"]) == (100.0, 50.0, 3.0))
            return ok, "m=%s" % m
        finally:
            shutil.rmtree(d, ignore_errors=True)
    saf("P1", p1)

    def p2(ns):
        # P1 ile aynı ama alt dosyada 1 üçgen eksik → sızdırmaz 0.
        yol, d = saf_3mf_uretim(eksik_ucgen=True)
        try:
            m = ns["uc_mf_olc"](yol)
            ok = m is not None and m["nesne"] == 1 and m["sizdirmaz_nesne"] == 0
            return ok, "m=%s" % m
        finally:
            shutil.rmtree(d, ignore_errors=True)
    saf("P2", p2)

    def p3(ns):
        # p:path hedefi zip'te YOK → None (fail-closed).
        yol, d = saf_3mf_uretim(alt_var=False)
        try:
            m = ns["uc_mf_olc"](yol)
            return m is None, "m=%s" % m
        finally:
            shutil.rmtree(d, ignore_errors=True)
    saf("P3", p3)

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


def saf_form_tipleri():
    """GERCEK manifestin tanidigi form tipleri (VERI.FORM_TIPLERI, foto-uretim-veri.js)."""
    js = ("const vm=require('vm'),fs=require('fs');const k={};vm.runInNewContext(fs.readFileSync(process.argv[1],"
          "'utf8'),k,{filename:'foto-uretim-veri.js'});const T=k.PRUVO_FOTO.FORM_TIPLERI||{};"
          "process.stdout.write(JSON.stringify(Object.keys(T).filter(x=>T[x]===true)));")
    r = subprocess.run(["node", "-e", js, os.path.join(KOK, "foto-uretim-veri.js")], capture_output=True, text=True,
                       timeout=60)
    if r.returncode != 0:
        raise RuntimeError("node: " + r.stderr[:300])
    return set(json.loads(r.stdout))


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
            {"U4", "U16", "U18", "S6"}),
    "MB4": ('sunucu_ok = k0 == 400 and j0.get("hata") == "onay-yok" and',
            'sunucu_ok = k0 in (400, 403) and', {"U5"}),
    "MB5": ('all(o.get("fiyat_kurus") == beklenen_kurus(o.get("mm")) for o in a.get("olculer") or []) and',
            'True and', {"U6"}),
    "MB6": ('        tr.koy("6", False, "tarayici=OLCULEMEDI")\n        return',
            '        tr.koy("6", True, "tarayici=OLCULEMEDI")\n        tr.koy("5", True, "")\n'
            '        tr.koy("3", True, "")\n        return', {"U10"}),
    "MB7": ("    if not d1 or not kova or d1 == cd1 or kova == ckova:", "    if not d1 or not kova:", {"U12"}),
    "MB8": ("    if v is not None and not v.get(\"secildi\"):", "    if False:", {"U15"}),
    "MB9": ('        eksen = (m["parca_en_uzun"] <= tr.olcu * (1 + tol) + 1e-9 and', "        eksen = (True and",
            {"U18"}),
    # kopru-15 sozluk: ornek girdi destegi silinince saf vakalar KIRMIZI. MB10: bool dali yoksa bust'in (ters/
    # iki_renk bool) ornek parametresi desteksiz -> U19 + U20 + bust mutlu yolu U1 KIRMIZI.
    "MB10": ('        elif tip == "bool":\n            p[ad] = s.get("varsayilan") is True\n', "", {"U1", "U19", "U20"}),
    "MB11": ('elif g in ("form", "metin", "url", "ses", "konum", "tarih"):', 'elif g in ("form", "metin", "url"):',
             {"U20"}),
    "MB12": ('        elif tip == "ses":\n            p[ad] = list(ORNEK_GENLIK)\n', "", {"U20"}),
    "MB13": ('            p[ad] = {"enlem": k["enlem"], "boylam": k["boylam"]}', '            p[ad] = dict(ORNEK_KONUM)',
             {"U20"}),
    "MB14": ('            p[ad] = dict(k) if s.get("saat") is True else k["tarih"]', '            p[ad] = k["tarih"]',
             {"U20"}),
    # kopru-15 DILIM-2: kosul atlamasi silinince kosulsuz alan ornege girer (sunucu sema-disi) -> U22;
    # gecerli varsayilan yerine formul -> U22 (duvar 1.6 yerine 4). U19'un gercek D turlerinde kosullu alan
    # yok ve `ornek` varsayilandan once okunur -> MB15/MB16 U19'a etki etmez.
    "MB15": ("        if not kosul_tamam(s, p):\n            continue\n", "", {"U22"}),
    "MB16": ('        elif tip == "sayi" and sayi_gecerli(s, vs):', '        elif tip == "sayi" and False:', {"U22"}),
    # kopru-15 DILIM-3: ③ TURETILMIS esitlik kolu atlanirsa sapan fiyat HAZIR gecer -> U24 KIRMIZI.
    # K3a: MB17 SİLİNDİ (U24 kalkti).
    # K3a: MB18 SİLİNDİ (U23 kalkti). kopru-15 SON3 (K3 tasindi: sehir/yildiz -> anahtarlik + sentetik sayi):
    # kayit `ornek`i okunmazsa anahtarlik satirlar ["PRUVO"] / sentetik adet 5 (varsayilan) -> U25.
    "MB19": ('        elif tip == "sayi" and sayi_gecerli(s, s.get("ornek")):',
             '        elif tip == "sayi" and False:', {"U25"}),
    "MB20": ('        elif tip == "metin" and metin_gecerli(s, s.get("ornek")):',
             '        elif tip == "metin" and False:', {"U25"}),
    # kopru-15 SAGLAYICI-2: kredi kapisi / yabanci kuyruk / tavan-0 kolu / D1 farki silinince -> KIRMIZI.
    "MB21": ("        if h + n > self.tavan:", "        if False:", {"S2", "S4"}),
    "MB22": ('        if y and y[0]["n"]:', "        if False:", {"S5"}),
    "MB23": ('                if a.kredi_tavani > 0 and tr.t.get("kol") == "saglayici":',
             '                if tr.t.get("kol") == "saglayici":', {"S1"}),
    "MB24": ("        return max(self.toplam() - self.taban, self.ayrilan)", "        return self.ayrilan", {"S7"}),
    # kopru-15 SAGLAYICI-2 devam yolu: --devam-is gecersiz olursa ornek-onizleme yeniden acilir / tavan-0 kolu
    # devre disi kalirsa erken HATA atlanir -> KIRMIZI.
    "MB25": ("    if devam_is_no:\n        tr.is_no = devam_is_no\n    else:",
             "    if False:\n        tr.is_no = devam_is_no\n    else:", {"S9"}),
    "MB26": ("    if a.devam_is and (a.kredi_tavani <= 0 or len(a.tur) != 1 or a.hepsi):",
             "    if a.devam_is and (len(a.tur) != 1 or a.hepsi):", {"S10"}),
    # kopru-15 3MF-PPATH: p:path cozumu kaldirilirsa uretim-dosya 3MF (S3) ve sentetik P1 okunMAZ -> KIRMIZI;
    # item transformu uygulanmazsa P1 kutu (200, 100, 6) kalir, beklenen (100,50,3) sapar -> KIRMIZI.
    "MB27": ("        if not yol_ifade:",
             "        if True:", {"P1", "S3"}),
    "MB28": ("        for p in noktalar(anahtar, b.group(2)):",
             "        for p in noktalar(anahtar, \"\"):", {"P1"}),
    # kopru-15: mutant_on_kosul `hata == hata_bek` kontrolu atlanirsa 400 `gorsel-gecersiz` GEÇERLI
    # sayilir (figur gercek tur 400'a duserse) -> U2b KIRMIZI.
    "MB29": ("    return k == 400 and j.get(\"hata\") == hata_bek, (",
             "    return k == 400, (", {"U2b"}),
    # kopru-15 KREDI-DOKU: KREDI_TIK["doku"]=0 fix MB30'la geri gelirse S12 ayrilan 20->30 KIRMIZI; S13'te
    # BETIK `ayir` ile once yakalandigi icin POST-sonrasi mesaji degil, "kredi-tavani 20+10>29" gelir —
    # S13 KIRMIZI.
    "MB30": ("KREDI_TIK = {\"build-baslat\": 30, \"analiz\": 10, \"onarim\": 10, \"doku\": 0}",
             "KREDI_TIK = {\"build-baslat\": 30, \"analiz\": 10, \"onarim\": 10, \"doku\": 10}",
             {"S12", "S13"}),
    # ONARIM KAPISI (8 Eki): betik 'onarim-bekliyor'da kosucuyu kosmazsa satir uretim-tik'e duser (tik onu
    # SECMEZ, foto.js) -> zaman asimi: S14 ④ EKSIK, S15 dogru sebebi basmaz; tam zincir (renk -> onarim-bekliyor)
    # kosan S3/S6/S9/S12 de 'hazir'a ulasamaz -> KIRMIZI.
    "MB31": ("        if asama == \"onarim-bekliyor\":\n", "        if False:\n",
             {"S3", "S6", "S9", "S12", "S14", "S15"}),
    # Okan 8 Eki tabani: olcum betigi tabani unutursa 60 mm alti olculer (plaket 10..50 mm; D turlerinin
    # /acik'teki olculeri >= 60) ③ EKSIK -> S3 KIRMIZI.
    "MB32": ("    return max(mm * 1000, TABAN_KURUS)\n", "    return mm * 1000\n", {"S3"}),
    # 8b0a4a10: mutant on kosulu YALNIZ M kapali turu secer; filtre kalkarsa ornegi olmayan D anahtarlik
    # secilir, sunucu 503 `kapali` (uretecOnizlemeUcu) -> GECERSIZ rc 2 -> U2c KIRMIZI.
    "MB33": (' if t["kod"] not in acik_kodlar and t.get("motor") == "M"]', ' if t["kod"] not in acik_kodlar]',
             {"U2c"}),
    "MB0": ("# ------------------------------------------------------------------ HTTP",
            "# ------------------------------------------------------------------ HTTP (mutant yorum)", set()),
}


def mutant_kos(ad, kaynak):
    eski, yeni, hedef = MUTANTLAR[ad]
    if kaynak.count(eski) != 1:
        return False, "capa %d kez bulundu" % kaynak.count(eski)
    mutant = kaynak.replace(eski, yeni)
    if mutant == kaynak:
        return False, "mutant UYGULANMADI (kaynak degismedi)"
    # SURE (CI adimi <= 300 sn): mutant yalniz hedef vakalari + iki bekci vakada (U1 mutlu yol, U2 mutant
    # kapisi) kosar; hedef disi kirmizi bu kumede aranir. Tam kume her kosumda yukarida (vakalar) olculur.
    s = vakalar(mutant, sadece=set(hedef) | {"U1", "U2"})
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
