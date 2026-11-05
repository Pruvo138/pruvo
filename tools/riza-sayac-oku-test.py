#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`tools/riza-sayac-oku.py` bataryasi — ag YOK, D1 YOK, yalniz tempfile.

  V1 sqlite: 3 gun, kabul/ret/kapat toplami + oran           -> rc=0, satir birebir
  V2 pencere siniri: bitis HARIC, baslangic DAHIL              -> sinir disi sayilmaz
  V3 TOPLAM=0                                                  -> KABUL_ORANI=TANIMSIZ, rc=0
  V4 beyaz liste disi karar                                    -> BILINMEYEN_KARAR + rc=4
  V5 d1-json GERCEK zarf (`d1_zarf_fikstur`, canli ayristirici)  -> V1 ile ayni ozet
  V6 d1-json bozuk zarf                                        -> OLCULEMEDI rc=3 (sessiz 0 YOK)
  V7 tarih bicimi / bitis<=baslangic                           -> rc=2
  M1 MUTANT topla() bitisi dahil eder                          -> V5 KIRMIZI
  M2 MUTANT bilinmeyen karar sessiz                            -> V4 KIRMIZI
  M3 MUTANT bos oran %0                                        -> V3 KIRMIZI
  (her mutantta kontrol V1 YESIL kalir)
rc=0 tumu yesil · rc=1 kirmizi var.
"""
import contextlib
import importlib.util
import io
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
ARAC = KOK / "tools" / "riza-sayac-oku.py"
sys.dont_write_bytecode = True
sys.path.insert(0, str(KOK / "tools"))
import d1_zarf_fikstur                                   # noqa: E402  (ortak GERCEK wrangler zarfi)

SATIRLAR = [
    ("2026-10-29", "kabul", 9),     # pencere disi (once)
    ("2026-10-30", "kabul", 2), ("2026-10-30", "ret", 5), ("2026-10-30", "kapat", 1),
    ("2026-11-01", "kabul", 1), ("2026-11-01", "ret", 3),
    ("2026-11-05", "kapat", 2),
    ("2026-11-06", "kabul", 7),     # pencere disi (bitis HARIC)
]
BAS, BIT = "2026-10-30", "2026-11-06"
BEKLENEN_OZET = ("RIZA_SAYAC baslangic=2026-10-30 bitis=2026-11-06 GUN=3 KABUL=3 RET=8 "
                 "KAPAT=3 TOPLAM=14 KABUL_ORANI=%21.4")

MUTANTLAR = {
    # topla() penceresi d1-json kolunun TEK siniridir (SQL siniri sqlite kolunda ayrica durur).
    "M1": ("        if not (bas <= g < bit):\n",
           "        if not (bas <= g <= bit):  # MUTANT\n", "V5"),
    "M2": ("        return 4\n", "        return 0  # MUTANT\n", "V4"),
    "M3": ('if t else "TANIMSIZ"', 'if t else "%0.0"', "V3"),
}


def yukle(kaynak, ad):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / (ad + ".py")
        p.write_text(kaynak, encoding="utf-8")
        s = importlib.util.spec_from_file_location(ad, p)
        m = importlib.util.module_from_spec(s)
        s.loader.exec_module(m)
    return m


def kos(mod, argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = mod.main(argv)
    return rc, buf.getvalue()


def sqlite_vt(td, satirlar):
    yol = str(Path(td) / "riza.sqlite")
    c = sqlite3.connect(yol)
    c.execute("CREATE TABLE riza_sayac(gun TEXT, karar TEXT, n INTEGER, PRIMARY KEY(gun, karar))")
    c.executemany("INSERT INTO riza_sayac VALUES(?,?,?)", satirlar)
    c.commit()
    c.close()
    return yol


def vakalar(mod):
    out = {}
    with tempfile.TemporaryDirectory() as td:
        vt = sqlite_vt(td, SATIRLAR)
        rc, o = kos(mod, ["--baslangic", BAS, "--bitis", BIT, "--vt", vt])
        ilk = o.splitlines()[0] if o else ""
        out["V1"] = (rc == 0 and ilk == BEKLENEN_OZET, "rc=%s ilk=%s" % (rc, ilk))

        rc, o = kos(mod, ["--baslangic", "2026-11-01", "--bitis", "2026-11-05", "--vt", vt])
        ilk = o.splitlines()[0] if o else ""
        out["V2"] = (rc == 0 and "GUN=1 KABUL=1 RET=3 KAPAT=0 TOPLAM=4" in ilk, "ilk=%s" % ilk)

        rc, o = kos(mod, ["--baslangic", "2026-12-01", "--bitis", "2026-12-08", "--vt", vt])
        out["V3"] = (rc == 0 and "TOPLAM=0 KABUL_ORANI=TANIMSIZ" in o, "rc=%s o=%s" % (rc, o.strip()))

        d2 = Path(td) / "b"
        d2.mkdir()
        vt2 = sqlite_vt(d2, SATIRLAR[1:3] + [("2026-10-31", "evet", 4)])
        rc, o = kos(mod, ["--baslangic", BAS, "--bitis", BIT, "--vt", vt2])
        out["V4"] = (rc == 4 and "BILINMEYEN_KARAR=4" in o, "rc=%s o=%s" % (rc, o.strip()[-80:]))

        js = Path(td) / "d1.json"
        js.write_text(d1_zarf_fikstur.zarf_metni(
            [{"gun": g, "karar": k, "n": n} for g, k, n in SATIRLAR]), encoding="utf-8")
        rc, o = kos(mod, ["--baslangic", BAS, "--bitis", BIT, "--d1-json", str(js)])
        ilk = o.splitlines()[0] if o else ""
        out["V5"] = (rc == 0 and ilk == BEKLENEN_OZET, "rc=%s ilk=%s" % (rc, ilk))

        bozuk = Path(td) / "bozuk.json"
        bozuk.write_text(json.dumps([{"sonuc": []}]), encoding="utf-8")
        rc, o = kos(mod, ["--baslangic", BAS, "--bitis", BIT, "--d1-json", str(bozuk)])
        out["V6"] = (rc == 3 and "OLCULEMEDI" in o and "TOPLAM" not in o, "rc=%s o=%s" % (rc, o.strip()))

        r1, _ = kos(mod, ["--baslangic", "2026-13-01", "--bitis", BIT, "--vt", vt])
        r2, _ = kos(mod, ["--baslangic", BIT, "--bitis", BAS, "--vt", vt])
        out["V7"] = (r1 == 2 and r2 == 2, "rc=%s,%s" % (r1, r2))
    return out


def main():
    kaynak = ARAC.read_text(encoding="utf-8")
    kirmizi = 0
    for ad, (ok, d) in vakalar(yukle(kaynak, "riza_oku_taban")).items():
        print("%s %s — %s" % ("YESIL" if ok else "KIRMIZI", ad, d))
        kirmizi += 0 if ok else 1
    for mad, (eski, yeni, hedef) in MUTANTLAR.items():
        if kaynak.count(eski) != 1:
            print("KIRMIZI %s — mutant capasi %d kez (1 olmali)" % (mad, kaynak.count(eski)))
            kirmizi += 1
            continue
        s = vakalar(yukle(kaynak.replace(eski, yeni), "riza_oku_" + mad.lower()))
        oldu, kontrol = (not s[hedef][0]), s["V1"][0]
        print("%s %s — hedef %s %s · kontrol V1 %s" % (
            "YESIL" if (oldu and kontrol) else "KIRMIZI", mad, hedef,
            "KIRMIZI (mutant oldu)" if oldu else "YESIL (mutant KACTI)",
            "YESIL" if kontrol else "KIRMIZI"))
        kirmizi += 0 if (oldu and kontrol) else 1
    print("SONUC: %s (kirmizi=%d)" % ("YESIL" if kirmizi == 0 else "KIRMIZI", kirmizi))
    return 0 if kirmizi == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
