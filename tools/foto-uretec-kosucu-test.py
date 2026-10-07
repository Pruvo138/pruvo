#!/usr/bin/env python3
"""FOTO URETEC KOSUCUSU — hermetik kabul testi + mutantlar (tools/foto-uretec-kosucu.py).

HERMETIK: wrangler yerine SAHTE komut (D1 = gecici SQLite, sema tools/d1-sema.sql; R2 = gecici
dizin), uretec yerine SAHTE komut. Gercek D1/R2/ev yolu YOK; her sey tempfile altinda, bitince silinir.

Vakalar: T1 BOS rc=1 · T2 1 is -> ISLEDI + hazir + 3 dosya R2'de · T3 rc 2 -> elle · T4 ariza x3 -> elle ·
T5 sizdirmaz:false -> elle, R2 yazimi 0 · T6 CAS kaybi -> yazim yok · T7 D1/R2 erisim yok ->
OLCULEMEDI rc=4 + satir DEGISMEDI · T8 kilit -> KILITLI rc=3 · T9 KURU -> yazim 0 · T10 onizleme kuyrugu
-> onizleme-hazir · T11 log tavani · T12 KOPYA KOLU (onizlemeye bagli siparis, ayni girdi sha -> uretec
KOSMAZ, model onizlemeninki) · T12b sha farkli -> uretec yeniden koşar.
Mutantlar (kosucu kopyasi gecici dizinde): M1 sizdirmaz dogrulamasi silindi -> T5 KIRMIZI ·
M2 KURU kapisi silindi -> T9 · M3 CAS kira kontrolu silindi -> T6 · M4 deneme tavani yok -> T4 ·
M5 erisim hatasinda jeton geri verilmez -> T7 · M0 yorum -> 0 kirmizi.

`--uctan-uca`: CI DISI yerel prova — ayni sahte D1/R2 ile GERCEK litofan_uret.py (pruvo-jenerator,
salt okunur) kosulur; 3MF sizdirmaz + uzun kenar ±%1 + asama 'hazir' olculur.
"""
import fcntl
import json
import os
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib
import re

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


class Ortam:
    def __init__(self, kosucu=KOSUCU, tablo=True):
        self.d = tempfile.mkdtemp(prefix="foto-kosucu-test-")
        self.kosucu = kosucu
        self.db = os.path.join(self.d, "d1.sqlite")
        self.r2 = os.path.join(self.d, "r2")
        self.log = os.path.join(self.d, "wrangler.log")
        os.makedirs(self.r2)
        open(self.log, "w").close()
        for ad, icerik in (("wr.py", SAHTE_WRANGLER), ("uretec.py", SAHTE_URETEC)):
            with open(os.path.join(self.d, ad), "w") as f:
                f.write(icerik)
        c = sqlite3.connect(self.db)
        with open(SEMA, encoding="utf-8") as f:
            c.executescript(f.read())
        c.commit()
        c.close()
        self.env = dict(os.environ, FAKE_DB=self.db, FAKE_R2=self.r2, FAKE_LOG=self.log,
                        FOTO_KOSUCU_WRANGLER="%s %s" % (sys.executable, os.path.join(self.d, "wr.py")),
                        FOTO_KOSUCU_KILIT=os.path.join(self.d, "kilit"),
                        FOTO_KOSUCU_PYTHON=sys.executable)
        for k in ("FAKE_D1_KAPALI", "FAKE_R2_KAPALI", "FAKE_CAS_KAYBI", "FAKE_URETEC_MOD", "FOTO_KOSUCU_URETEC_TABLO"):
            self.env.pop(k, None)
        if tablo:
            t = os.path.join(self.d, "tablo.json")
            with open(t, "w") as f:
                json.dump({"litofan_uret": {"bicim": "sozlesme",
                                            "komut": [sys.executable, os.path.join(self.d, "uretec.py")]}}, f)
            self.env["FOTO_KOSUCU_URETEC_TABLO"] = t

    def sql(self, q, *p):
        c = sqlite3.connect(self.db)
        c.row_factory = sqlite3.Row
        r = [dict(x) for x in c.execute(q, p).fetchall()]
        c.commit()
        c.close()
        return r

    def siparis_is(self, olcu=150, deneme=0):
        kalem = {"foto_is": IS, "foto_tur": "litofan", "olcu_mm": olcu,
                 "foto_secim": {"panel_renk": "Beyaz", "ayak_renk": "Siyah", "panel_malzeme": "PLA",
                                "ayak_malzeme": "PETG"}}
        self.sql("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES (?,?,?,?,?)",
                 SIP, GUNCEL0, "odendi", olcu * 1000, json.dumps([kalem]))
        self.sql("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, deneme, tarih, guncel)"
                 " VALUES (?,0,?,?,?,?,?,?,?)", SIP, IS, "litofan", olcu, "uretec-bekliyor", deneme, GUNCEL0, GUNCEL0)
        os.makedirs(os.path.join(self.r2, "foto-onizleme"), exist_ok=True)
        with open(os.path.join(self.r2, "foto-onizleme", IS + ".png"), "wb") as f:
            f.write(png_gri(240, 160))

    def onizleme_is(self):
        self.sql("INSERT INTO foto_isler (is_no, tur, olcu_mm, ziyaretci, tarih, asama, son_kontrol)"
                 " VALUES (?,?,?,?,?,?,?)", IS2, "litofan", 120, "ab" * 8, GUNCEL0, "uretec-onizleme", 5)
        d = os.path.join(self.r2, "foto-uretec-onizleme", IS2)
        os.makedirs(d)
        with open(os.path.join(d, "girdi.json"), "w") as f:
            json.dump({"sozlesme": 1, "kategori": "litofan", "siparis_no": "", "kalem": 0, "olcu_mm": 120,
                       "renkler": {}, "malzemeler": {}, "parametreler": {}, "dosyalar": {"gri_harita": "gri_harita.png"}}, f)
        with open(os.path.join(d, "gri_harita.png"), "wb") as f:
            f.write(png_gri(200, 140))

    def siparis_onizlemeden(self, secim):
        """Siparis oncesi uretec onizlemesine (IS2) bagli odenmis kalem."""
        kalem = {"foto_is": IS2, "foto_tur": "litofan", "olcu_mm": 120, "foto_secim": secim}
        self.sql("INSERT INTO siparisler (siparis_no, tarih, durum, tutar_kurus, urunler) VALUES (?,?,?,?,?)",
                 SIP, GUNCEL0, "odendi", 120000, json.dumps([kalem]))
        self.sql("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, deneme, tarih, guncel)"
                 " VALUES (?,0,?,?,?,?,?,?,?)", SIP, IS2, "litofan", 120, "uretec-bekliyor", 0, GUNCEL0, GUNCEL0)

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
        return rc == 1 and son == "HAL=BOS rc=1" and o.yazimlar() == 0, son

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
        o.siparis_onizlemeden({"ayak_renk": "Siyah"})
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

    for ad, fn in (("T1", t1), ("T2", t2), ("T3", t3), ("T4", t4), ("T5", t5), ("T6", t6), ("T7", t7),
                   ("T8", t8), ("T9", t9), ("T10", t10), ("T11", t11), ("T12", t12), ("T12b", t12b)):
        vaka(ad, fn)
    return s


MUTANTLAR = {
    "M1": ('    if o.get("sizdirmaz") is not True:\n        return "sizdirmaz-degil"\n', "", {"T5"}),
    "M2": ("        if not uygula:\n", "        if False:\n", {"T9"}),
    "M3": ('    if n != 1:\n        yaz("CAS %s kiralanamadi', '    if False:\n        yaz("CAS %s kiralanamadi', {"T6"}),
    "M4": ("DENEME_TAVANI = 3\n", "DENEME_TAVANI = 99\n", {"T4"}),
    "M5": ("            d1(geri_ver_sql(i, jeton))\n", "            pass\n", {"T7"}),
    "M6": ("    if onceki != sha:\n", "    if False:\n", {"T12b"}),
    "M7": ('    if i["kuyruk"] != "siparis" or not i.get("onizleme_kaynakli"):\n        return None\n    os.makedirs',
           '    if True:\n        return None\n    os.makedirs', {"T12"}),
    "M0": ("import argparse\n", "import argparse  # kontrol mutanti\n", set()),
}


def mutant_kos(ad):
    eski, yeni, hedef = MUTANTLAR[ad]
    with open(KOSUCU, encoding="utf-8") as f:
        kaynak = f.read()
    if kaynak.count(eski) != 1:
        return False, "capa %d kez bulundu" % kaynak.count(eski)
    d = tempfile.mkdtemp(prefix="foto-kosucu-mutant-")
    try:
        os.makedirs(os.path.join(d, "tools"))
        os.makedirs(os.path.join(d, "shop"))
        shutil.copyfile(os.path.join(KOK, "foto-uretim-veri.js"), os.path.join(d, "foto-uretim-veri.js"))
        yol = os.path.join(d, "tools", "foto-uretec-kosucu.py")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(kaynak.replace(eski, yeni))
        s = vakalar(yol)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    kirmizi = {k for k, (g, _) in s.items() if not g}
    return kirmizi == hedef, "kirmizi=%s hedef=%s" % (sorted(kirmizi), sorted(hedef))


def uctan_uca():
    jen = os.environ.get("FOTO_KOSUCU_JENERATOR") or os.path.expanduser("~/dev/pruvo-jenerator")
    o = Ortam(tablo=False)
    try:
        o.env["FOTO_KOSUCU_JENERATOR"] = jen
        o.siparis_is(olcu=150)
        rc, son, cikti = o.kos("--uygula")
        u = o.uretim()
        d = os.path.join(o.r2, "foto", SIP, "0")
        olcu = json.load(open(os.path.join(d, "olcu.json"))) if os.path.isfile(os.path.join(d, "olcu.json")) else {}
        z = zipfile.ZipFile(os.path.join(d, "model.3mf"))
        xml = z.read([n for n in z.namelist() if n.endswith(".model")][0]).decode()
        birim = re.search(r'unit="([a-z]+)"', xml).group(1)
        nesneler = re.findall(r"<object\b.*?</object>", xml, re.S)
        kutular = []
        for n in nesneler:
            xs = [float(v) for v in re.findall(r'<vertex x="([-0-9.e]+)"', n)]
            ys = [float(v) for v in re.findall(r'<vertex x="[-0-9.e]+" y="([-0-9.e]+)"', n)]
            kutular.append((round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3)))
        panel_uzun = max(kutular[0]) if kutular else 0
        w, h = struct.unpack(">II", open(os.path.join(d, "onizleme.png"), "rb").read()[16:24])
        print("UCTAN_UCA son=%s" % son)
        print("asama=%s sebep=%r deneme=%s" % (u["asama"], u["sebep"], u["deneme"]))
        print("r2=%s" % sorted(os.listdir(d)))
        print("olcu.json sizdirmaz=%s uzun_kenar_mm=%s kutu=%s renk=%s ucgen=%s" % (
            olcu.get("sizdirmaz"), olcu.get("uzun_kenar_mm"), olcu.get("kutu_mm"), olcu.get("renk_sayisi"),
            olcu.get("ucgen")))
        print("3mf unit=%s nesne=%d panel_kutu_xy=%s bagimsiz_uzun_kenar=%s sapma=%.4f%%" % (
            birim, len(nesneler), kutular[0] if kutular else None, panel_uzun, abs(panel_uzun - 150) / 1.5))
        print("onizleme.png %dx%d" % (w, h))
        ok = (son == "HAL=ISLEDI uretildi=1 red=0 ariza=0 rc=0" and u["asama"] == "hazir" and
              olcu.get("sizdirmaz") is True and abs(panel_uzun - 150) <= 1.5 and birim == "millimeter")
        print("UCTAN_UCA_HUKUM=%s" % ("GECTI" if ok else "KIRMIZI"))
        if not ok:
            print(cikti)
        return 0 if ok else 1
    finally:
        o.kapat()


def main():
    if "--uctan-uca" in sys.argv:
        return uctan_uca()
    kirmizi = 0
    for ad, (g, ac) in vakalar(KOSUCU).items():
        print("%s %s — %s" % ("✅" if g else "❌", ad, ac[:300]))
        kirmizi += 0 if g else 1
    survivor = 0
    for ad in MUTANTLAR:
        g, ac = mutant_kos(ad)
        print("%s %s — %s" % ("✅" if g else "❌ SURVIVOR", ad, ac))
        survivor += 0 if g else 1
    print("VAKA_KIRMIZI=%d SURVIVOR=%d" % (kirmizi, survivor))
    return 1 if kirmizi or survivor else 0


if __name__ == "__main__":
    sys.exit(main())
