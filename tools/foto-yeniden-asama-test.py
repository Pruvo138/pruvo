#!/usr/bin/env python3
"""foto-yeniden-asama.py kabul testi (hermetik: sahte wrangler = sqlite D1 + dizin R2; ag YOK).

V1 elle/analiz-kirmizi + R2 model.3mf -> --uygula: model.ham.3mf AYNI bayt, model.3mf SILINDI, asama onarim-bekliyor
V2 ham cikti yok -> RED ham-cikti-yok, D1 degismez
V3 asama hazir -> RED asama-uygun-degil, R2/D1 degismez
V4 KURU (--uygula yok) -> PLAN, yazim 0
V5 dosya 3MF degil -> RED ham-3mf-degil
V6 model.ham.3mf zaten var -> kaynak model.ham.3mf, model.3mf yine silinir
Mutantlar (izole kopya): K1 ham kapisi silindi -> V2 · K2 asama kapisi silindi -> V3 · K3 model.3mf silinmedi -> V1,V6 ·
K4 kuru kapisi silindi -> V4 · K0 kontrol.
Son satir: VAKA_KIRMIZI=<n> SURVIVOR=<m>
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "foto-yeniden-asama.py")
SEMA = os.path.join(KOK, "tools", "d1-sema.sql")
NO = "ORNEK-9ba97f662e3f"
G0 = "2026-10-08T00:00:00.000Z"
UCMF = b"PK\x03\x04saglayici-ham"

SAHTE_WRANGLER = r'''
import json, os, shutil, sqlite3, sys
a = sys.argv[1:]
open(os.environ["FAKE_LOG"], "a").write(json.dumps(a[:3]) + "\n")
if a[:2] == ["d1", "execute"]:
    sql = a[a.index("--command") + 1]
    c = sqlite3.connect(os.environ["FAKE_DB"]); c.row_factory = sqlite3.Row
    cur = c.execute(sql); rows = [dict(r) for r in cur.fetchall()] if cur.description else []
    n = c.total_changes; c.commit(); c.close()
    print(json.dumps([{"results": rows, "success": True, "meta": {"changes": n}}])); sys.exit(0)
if a[:2] == ["r2", "object"]:
    yol = os.path.join(os.environ["FAKE_R2"], a[3].split("/", 1)[1])
    if a[2] == "delete":
        if os.path.isfile(yol): os.remove(yol)
        sys.exit(0)
    dosya = a[a.index("--file") + 1]
    if a[2] == "get":
        if not os.path.isfile(yol):
            sys.stderr.write("The specified key does not exist.\n"); sys.exit(1)
        shutil.copyfile(yol, dosya); sys.exit(0)
    os.makedirs(os.path.dirname(yol), exist_ok=True); shutil.copyfile(dosya, yol); sys.exit(0)
sys.exit(9)
'''


class Ortam:
    def __init__(self, arac=ARAC):
        self.d = tempfile.mkdtemp(prefix="foto-yeniden-asama-test-")
        self.arac, self.db, self.r2 = arac, os.path.join(self.d, "d1.sqlite"), os.path.join(self.d, "r2")
        self.log = os.path.join(self.d, "log")
        os.makedirs(self.r2)
        open(self.log, "w").close()
        with open(os.path.join(self.d, "wr.py"), "w") as f:
            f.write(SAHTE_WRANGLER)
        c = sqlite3.connect(self.db)
        with open(SEMA, encoding="utf-8") as f:
            c.executescript(f.read())
        c.commit()
        c.close()
        self.env = dict(os.environ, FAKE_DB=self.db, FAKE_R2=self.r2, FAKE_LOG=self.log,
                        FOTO_KOSUCU_WRANGLER="%s %s" % (sys.executable, os.path.join(self.d, "wr.py")))

    def satir(self, asama="elle", sebep="analiz-kirmizi"):
        c = sqlite3.connect(self.db)
        c.execute("INSERT INTO foto_uretim (siparis_no, kalem, is_no, tur, olcu_mm, asama, sebep, deneme, tarih, guncel)"
                  " VALUES (?,0,?,?,?,?,?,0,?,?)", (NO, "9ba97f662e3f" + "0" * 20, "figur", 130, asama, sebep, G0, G0))
        c.commit()
        c.close()

    def koy(self, ad, bayt=UCMF):
        d = os.path.join(self.r2, "foto", NO, "0")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, ad), "wb") as f:
            f.write(bayt)

    def oku(self, ad):
        y = os.path.join(self.r2, "foto", NO, "0", ad)
        return open(y, "rb").read() if os.path.isfile(y) else None

    def asama(self):
        c = sqlite3.connect(self.db)
        r = c.execute("SELECT asama, sebep, guncel FROM foto_uretim").fetchone()
        c.close()
        return r

    def yazim(self):
        return sum(1 for s in open(self.log) if json.loads(s)[:3] in (["r2", "object", "put"], ["r2", "object", "delete"])
                   or ("UPDATE" in s))

    def kos(self, *arg):
        p = subprocess.run([sys.executable, self.arac, "--siparis", NO] + list(arg), capture_output=True, text=True,
                           env=self.env, timeout=120)
        return p.returncode, (p.stdout.strip().splitlines() or [""])[-1]

    def kapat(self):
        shutil.rmtree(self.d, ignore_errors=True)


def vakalar(arac=ARAC):
    s = {}

    def vaka(ad, fn):
        o = Ortam(arac)
        try:
            s[ad] = fn(o)
        except Exception as e:
            s[ad] = (False, "istisna %s: %s" % (type(e).__name__, e))
        finally:
            o.kapat()

    def v1(o):
        o.satir(); o.koy("model.3mf")
        rc, son = o.kos("--uygula")
        a = o.asama()
        return (rc == 0 and "HAL=TAMAM" in son and "kaynak=model.3mf" in son and o.oku("model.ham.3mf") == UCMF and
                o.oku("model.3mf") is None and a[0] == "onarim-bekliyor" and a[1] == "" and a[2] != G0), son

    def v2(o):
        o.satir()
        rc, son = o.kos("--uygula")
        return rc == 1 and "sebep=ham-cikti-yok" in son and o.asama()[0] == "elle", son

    def v3(o):
        o.satir(asama="hazir", sebep=""); o.koy("model.3mf")
        rc, son = o.kos("--uygula")
        return (rc == 1 and "sebep=asama-uygun-degil" in son and o.asama()[0] == "hazir" and
                o.oku("model.3mf") == UCMF and o.oku("model.ham.3mf") is None), son

    def v4(o):
        o.satir(); o.koy("model.3mf")
        rc, son = o.kos()
        return (rc == 0 and "HAL=PLAN" in son and o.yazim() == 0 and o.asama()[0] == "elle" and
                o.oku("model.3mf") == UCMF), son

    def v5(o):
        o.satir(); o.koy("model.3mf", b"<html>degil</html>")
        rc, son = o.kos("--uygula")
        return rc == 1 and "sebep=ham-3mf-degil" in son and o.asama()[0] == "elle", son

    def v6(o):
        o.satir(); o.koy("model.ham.3mf"); o.koy("model.3mf", b"PK\x03\x04baska")
        rc, son = o.kos("--uygula")
        return (rc == 0 and "kaynak=model.ham.3mf" in son and o.oku("model.ham.3mf") == UCMF and
                o.oku("model.3mf") is None and o.asama()[0] == "onarim-bekliyor"), son

    for ad, fn in (("V1", v1), ("V2", v2), ("V3", v3), ("V4", v4), ("V5", v5), ("V6", v6)):
        vaka(ad, fn)
    return s


MUTANTLAR = {
    "K1": ("        if not kaynak:\n            return bitir(\"RED\", \"ham-cikti-yok\", 1)\n", "", {"V2"}),
    "K2": ("    if r.get(\"asama\") != \"elle\" or r.get(\"sebep\") != \"analiz-kirmizi\":\n",
           "    if False:\n", {"V3"}),
    "K3": ("        k.wr([\"r2\", \"object\", \"delete\", k.R2_KOVA + \"/\" + d + MODEL, \"--remote\"])\n", "", {"V1", "V6"}),
    "K4": ("        if not a.uygula:\n", "        if False:\n", {"V4"}),
    "K0": ("import argparse\n", "import argparse  # kontrol\n", set()),
}


def mutant(ad):
    eski, yeni, hedef = MUTANTLAR[ad]
    kaynak = open(ARAC, encoding="utf-8").read()
    if kaynak.count(eski) != 1:
        return False, "capa %d kez" % kaynak.count(eski)
    d = tempfile.mkdtemp(prefix="foto-yeniden-asama-mutant-")
    try:
        os.makedirs(os.path.join(d, "tools"))
        os.makedirs(os.path.join(d, "shop"))
        shutil.copyfile(os.path.join(KOK, "tools", "foto-uretec-kosucu.py"), os.path.join(d, "tools", "foto-uretec-kosucu.py"))
        shutil.copyfile(os.path.join(KOK, "shop", "wrangler.onizleme.toml"), os.path.join(d, "shop", "wrangler.onizleme.toml"))
        yol = os.path.join(d, "tools", "foto-yeniden-asama.py")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(kaynak.replace(eski, yeni))
        s = vakalar(yol)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    kirmizi = {k for k, (g, _) in s.items() if not g}
    return kirmizi == hedef, "kirmizi=%s hedef=%s" % (sorted(kirmizi), sorted(hedef))


def main():
    s = vakalar()
    for ad, (g, ac) in s.items():
        print("%s %s — %s" % ("✅" if g else "❌", ad, ac))
    surv = 0
    for ad in MUTANTLAR:
        g, ac = mutant(ad)
        surv += 0 if g else 1
        print("%s %s — %s" % ("✅" if g else "❌ SURVIVOR", ad, ac))
    vk = sum(1 for g, _ in s.values() if not g)
    print("VAKA_KIRMIZI=%d SURVIVOR=%d" % (vk, surv))
    return 0 if vk == surv == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
