#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RIZA SAYACI OKUYUCU — `riza_sayac(gun, karar, n)` tablosunu tarih penceresinde sayar.

NEDEN VAR (5 Kas 2026, BaBa 23:2x hukmu ⑤): riza bandi metin denemesi A/B olcumu
ister — A = yayin oncesi son 7 gun, B = sonraki 7 gun, eksen bant kararlari
(kabul / ret / kapat). Tablo 22 Eki'den beri yaziliyor (`shop/src/riza-sayac.js`)
ama OKUYUCU YOKTU; ham `npx wrangler` makinede iz birakiyordu. Bu arac D1'e
`tools/d1-sync.py::sorgu` uzerinden gider (ozel npm onbellegi + log kapali).

CIKTI (tek makine-okunur satir + gun satirlari):
  RIZA_SAYAC baslangic=YYYY-MM-DD bitis=YYYY-MM-DD GUN=<n> KABUL=<n> RET=<n> KAPAT=<n> TOPLAM=<n> KABUL_ORANI=<%x.x|TANIMSIZ>
    <gun> kabul=<n> ret=<n> kapat=<n>
FAIL-CLOSED:
  * D1 erisilemez / cevap sekli bozuk -> `RIZA_SAYAC=OLCULEMEDI sebep=...` rc=3
  * tarih bicimi bozuk / bitis<=baslangic -> rc=2
  * beyaz liste disi karar -> sayilmaz AMA `BILINMEYEN_KARAR=<n>` basilir ve rc=4
  * TOPLAM=0 -> oran `TANIMSIZ` (sessiz %0 YOK), rc=0
KULLANIM (borusuz):
  python3 tools/riza-sayac-oku.py --baslangic 2026-10-30 --bitis 2026-11-06
  python3 tools/riza-sayac-oku.py --baslangic .. --bitis .. --vt <sqlite>      # test kolu
  python3 tools/riza-sayac-oku.py --baslangic .. --bitis .. --d1-json <dosya>  # test kolu
Bitis HARIC. Gun ekseni sunucu UTC gunudur (yazici oyle yazar).
"""
import argparse
import datetime as _dt
import importlib.util
import json
import os
import re
import sqlite3
import sys

sys.dont_write_bytecode = True

TOOLS = os.path.dirname(os.path.abspath(__file__))
KARARLAR = ("kabul", "ret", "kapat")       # shop/src/riza-sayac.js beyaz listesi
_GUN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SekilHatasi(ValueError):
    """D1 cevabi beklenen zarf/satir seklinde degil — sayilamaz, sessiz 0 YASAK."""


def gun_gecerli(g):
    if not g or not _GUN.match(g):
        return False
    try:
        _dt.date.fromisoformat(g)
        return True
    except ValueError:
        return False


def _d1_modulu():
    yol = os.path.join(TOOLS, "d1-sync.py")
    spec = importlib.util.spec_from_file_location("d1_sync_riza_oku", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def satirlar_coz(raw):
    """wrangler `d1 execute --json` cevabi (zarf listesi) -> satir listesi."""
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or not raw:
        raise SekilHatasi("D1 cevabi bos ya da liste degil")
    satirlar = []
    for zarf in raw:
        if not isinstance(zarf, dict) or not isinstance(zarf.get("results"), list):
            raise SekilHatasi("D1 zarfi 'results' listesi tasimiyor")
        for s in zarf["results"]:
            if not isinstance(s, dict) or not {"gun", "karar", "n"} <= set(s):
                raise SekilHatasi("D1 satiri gun/karar/n tasimiyor")
            satirlar.append(s)
    return satirlar


SQL_SABLON = "SELECT gun, karar, n FROM riza_sayac WHERE gun >= %s AND gun < %s"


def sorgu_d1(bas, bit):
    d1 = _d1_modulu()
    return satirlar_coz(d1.sorgu(SQL_SABLON % (d1.q(bas), d1.q(bit))))


def sorgu_d1_json(yol):
    with open(yol, encoding="utf-8") as f:
        return satirlar_coz(json.load(f))


def sorgu_sqlite(bas, bit, vt):
    conn = sqlite3.connect(vt)
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(SQL_SABLON % ("?", "?"), (bas, bit))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def topla(satirlar, bas, bit):
    """Doner: (gunler{gun:{karar:n}}, toplam{karar:n}, bilinmeyen_n).

    Pencere disi satir (test kolunda olabilir) sayilmaz — sorgu ile ayni sinir.
    """
    gunler, toplam, bilinmeyen = {}, {k: 0 for k in KARARLAR}, 0
    for s in satirlar:
        g = str(s.get("gun", ""))
        if not (bas <= g < bit):
            continue
        try:
            n = int(s.get("n"))
        except (TypeError, ValueError):
            raise SekilHatasi("n tamsayi degil: %r" % (s.get("n"),))
        k = str(s.get("karar", ""))
        if k not in KARARLAR:
            bilinmeyen += n
            continue
        gunler.setdefault(g, {kk: 0 for kk in KARARLAR})[k] += n
        toplam[k] += n
    return gunler, toplam, bilinmeyen


def ozet_satiri(bas, bit, gunler, toplam):
    t = sum(toplam.values())
    oran = "%%%.1f" % (100.0 * toplam["kabul"] / t) if t else "TANIMSIZ"
    return ("RIZA_SAYAC baslangic=%s bitis=%s GUN=%d KABUL=%d RET=%d KAPAT=%d TOPLAM=%d "
            "KABUL_ORANI=%s" % (bas, bit, len(gunler), toplam["kabul"], toplam["ret"],
                                toplam["kapat"], t, oran))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--baslangic", required=True, metavar="YYYY-MM-DD", help="dahil")
    ap.add_argument("--bitis", required=True, metavar="YYYY-MM-DD", help="haric")
    ap.add_argument("--vt", default=None, help="test kolu: yerel sqlite")
    ap.add_argument("--d1-json", default=None, dest="d1_json", help="test kolu: wrangler --json cevabi")
    a = ap.parse_args(argv)

    if not (gun_gecerli(a.baslangic) and gun_gecerli(a.bitis)) or a.bitis <= a.baslangic:
        sys.stdout.write("RIZA_SAYAC=OLCULEMEDI sebep=TARIH\n")
        return 2
    try:
        if a.vt:
            satirlar = sorgu_sqlite(a.baslangic, a.bitis, a.vt)
        elif a.d1_json:
            satirlar = sorgu_d1_json(a.d1_json)
        else:
            satirlar = sorgu_d1(a.baslangic, a.bitis)
        gunler, toplam, bilinmeyen = topla(satirlar, a.baslangic, a.bitis)
    except SekilHatasi as e:
        sys.stdout.write("RIZA_SAYAC=OLCULEMEDI sebep=D1-SEKIL (%s)\n" % e)
        return 3
    except Exception as e:                                       # noqa: BLE001
        sys.stdout.write("RIZA_SAYAC=OLCULEMEDI sebep=D1 (%s)\n" % type(e).__name__)
        return 3

    sys.stdout.write(ozet_satiri(a.baslangic, a.bitis, gunler, toplam) + "\n")
    for g in sorted(gunler):
        d = gunler[g]
        sys.stdout.write("  %s kabul=%d ret=%d kapat=%d\n" % (g, d["kabul"], d["ret"], d["kapat"]))
    if bilinmeyen:
        sys.stdout.write("BILINMEYEN_KARAR=%d (beyaz liste disi; sayilmadi)\n" % bilinmeyen)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
