#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D1 `inis_sayac` tablosundan BIR GUNUN reklam-inis olcumunu okur.

ArTisT'in gunluk olcum satiri icin UTM_FB / UTM_IG / UTM_G toplamlarini uretir.

Kullanim:
    python3 tools/inis-sayac-oku.py                       # bugun UTC
    python3 tools/inis-sayac-oku.py --gun 2026-10-17      # belirli gun
    python3 tools/inis-sayac-oku.py --kampanya             # kampanya kirilimi (n azalan)
    python3 tools/inis-sayac-oku.py --vt /tmp/test.db      # sqlite fiksturu (D1 yerine)

CIKTI (TEK SATIR, sonradan dusunulebilir analiz kolay):
    T   INIS gun=<YYYY-MM-DD> UTM_FB=<n> UTM_IG=<n> UTM_G=<n> UTM_GEO=<n> UTM_DIGER=<n> TOPLAM=<n>

`--kampanya` verilirse ALTINDA her (kaynak, kampanya) icin:
    T     <kaynak> <kampanya> <n>

HATALAR (rc, satır):
    rc=2  INIS=OLCULEMEDI sebep=GUN-BICIMI   --gun YYYY-MM-DD degil
    rc=3  INIS=OLCULEMEDI sebep=D1           canli D1 erisilemedi (sessiz 0 YOK)
    rc=3  INIS=OLCULEMEDI sebep=D1-SEKIL     D1 cevabi zarf/satir seklinde degil (sessiz 0 YOK)
    rc=0  Kayit yoksa sifirlarla ayni satir ("0 inis" gecerli olcumdur)

DESEN: tools/reklam-oci-yukleyici.py:302-380 (K443 ile silindi; `git show 3ce4b0852:tools/reklam-oci-yukleyici.py`) — `_d1_modulu` importlib ile
tools/d1-sync.py; SQL kacisi `d1-sync.py::q` ile birebir ayni. Kendi kopyamiz
YOK ([[ikiz-tanim-sessiz-ayrisma]]); kapi uctan uca olculur.
"""
import argparse
import datetime as _dt
import importlib.util
import json
import os
import sqlite3
import sys

sys.dont_write_bytecode = True                            # hedef repoya __pycache__ yazma

TOOLS = os.path.dirname(os.path.abspath(__file__))


# ===========================================================================
# KAYNAK SINIFLARI — sabit ve kapali liste (fail-closed). Beyaz liste
# `tools/d1-sema.sql` ile BIREBIR AYNI; yeni kaynak eklemek iki yerde de olur.
# ===========================================================================
FB = ("facebook", "fb", "meta")                            # ucunu sinifla
IG = ("instagram", "ig")
G  = ("google",)
GEO = ("chatgpt.com", "perplexity", "copilot", "bing")
# DIGER = beyaz listede OLMAYAN kaynaklar (whatsapp, tiktok, email vb.) — ayrica sayilir.


def _sinif_topla(satirlar):
    """[(kaynak, kampanya, n), ...] -> (FB, IG, G, GEO, DIGER, TOPLAM) tamsayilar."""
    fb = ig = g = geo = diger = 0
    for kaynak, _kampanya, n in satirlar:
        k = (kaynak or "").lower()
        try:
            n = int(n)
        except (TypeError, ValueError):
            n = 0
        if k in FB:
            fb += n
        elif k in IG:
            ig += n
        elif k in G:
            g += n
        elif k in GEO:
            geo += n
        else:
            diger += n
    return fb, ig, g, geo, diger, fb + ig + g + geo + diger


def _gun_bicimi(g):
    """YYYY-MM-DD biciminde mi? Gecerli ise YYYY-MM-DD; degilse None.

    🔴 strptime `%m`/`%d` tek haneli degerleri sessizce kabul eder (2026-1-7 gecerli
    sayilirdi) — bu spec'in V4 iddiasini KIRAR (bicim disi -> rc=2). O yuzden ilk
    once TAM BIÇIM dogrulanir (4-2-2 tire araligi), sonra strptime ile takvim dogrulamasi.
    """
    import re as _re
    if not g or not _re.match(r"^\d{4}-\d{2}-\d{2}$", g):
        return None
    try:
        return _dt.datetime.strptime(g, "%Y-%m-%d").date().isoformat()
    except (TypeError, ValueError):
        return None


def _bugun_utc():
    return _dt.datetime.now(_dt.timezone.utc).date().isoformat()


# ══════════════════════════════════════════════════════════════════════════════
# D1 ERISIMI — `tools/d1-sync.py`nin importlib sarmalayicisi
# ══════════════════════════════════════════════════════════════════════════════
def _d1_modulu():
    """`tools/d1-sync.py`yi importlib ile yukle (ad tire tasir, duz import calismaz).

    SQL metin kacisi (`q`) ORADAN alinir: ikinci bir kacis kopyasi tutulsaydi biri
    guncellenir digeri kalirdi ve ayrisma SESSIZ olurdu.
    """
    yol = os.path.join(TOOLS, "d1-sync.py")
    spec = importlib.util.spec_from_file_location("d1_sync_ocu", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SekilHatasi(ValueError):
    """D1 cevabi beklenen zarf/satir seklinde degil — sayilamaz, sessiz 0 YASAK."""


def _satirlar_coz(raw):
    """wrangler `d1 execute --json` cevabi -> satir listesi.

    Cevap ZARF LISTESIDIR: [{"results": [{kaynak, kampanya, n}, ...], "success": ..}].
    17 Eki olculdu: eski kod yalniz dict bekliyordu; liste geldiginde zarfin kendisini
    satir sanip `n=0` basti -> canli D1'de 25 inis varken TOPLAM=0 (sessiz 0).
    Beklenmeyen her sekil SekilHatasi -> rc=3 OLCULEMEDI.
    """
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or not raw:
        raise SekilHatasi("D1 cevabi bos ya da liste degil")
    satirlar = []
    for zarf in raw:
        if not isinstance(zarf, dict) or not isinstance(zarf.get("results"), list):
            raise SekilHatasi("D1 zarfi 'results' listesi tasimiyor")
        for s in zarf["results"]:
            if not isinstance(s, dict) or not {"kaynak", "kampanya", "n"} <= set(s):
                raise SekilHatasi("D1 satiri kaynak/kampanya/n tasimiyor")
            satirlar.append(s)
    return satirlar


def _sorgu_d1(gun):
    """Canli D1: SELECT kaynak, kampanya, n FROM inis_sayac WHERE gun=?"""
    d1 = _d1_modulu()
    q = d1.q
    sql = "SELECT kaynak, kampanya, n FROM inis_sayac WHERE gun=" + q(gun)
    return _satirlar_coz(d1.sorgu(sql))


def _sorgu_d1_json(yol):
    """Test kolu: wrangler cevabini dosyadan oku, canli yolla AYNI ayristiriciya ver."""
    with open(yol, encoding="utf-8") as f:
        return _satirlar_coz(json.load(f))


def _sorgu_sqlite(gun, vt_yolu):
    """Yerel sqlite: D1 ile ayni SQL metni, gercek sqlite motoru."""
    conn = sqlite3.connect(vt_yolu)
    try:
        conn.row_factory = sqlite3.Row
        sql = "SELECT kaynak, kampanya, n FROM inis_sayac WHERE gun=?"
        cur = conn.execute(sql, (gun,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# ARGUE
# ══════════════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gun", metavar="YYYY-MM-DD", default=None,
                    help="olculecek gun (varsayilan: bugun UTC). Bicim disi -> rc=2")
    ap.add_argument("--vt", metavar="YOL", default=None,
                    help="test kolu: yerel sqlite dosyasi (canli D1 yerine)")
    ap.add_argument("--kampanya", action="store_true",
                    help="her (kaynak, kampanya) icin n azalan alt satirlar bas")
    ap.add_argument("--d1-json", metavar="YOL", default=None, dest="d1_json",
                    help="test kolu: wrangler --json cevabi dosyasi (canli D1 ayristiricisi)")
    args = ap.parse_args()

    gun = _bugun_utc() if not args.gun else args.gun
    if not _gun_bicimi(gun):
        sys.stdout.write("INIS=OLCULEMEDI sebep=GUN-BICIMI\n")
        return 2

    # ── VT secimi: --vt verildiyse sqlite; yoksa canli D1 ─────────────────
    try:
        if args.vt:
            satirlar = _sorgu_sqlite(gun, args.vt)
        elif args.d1_json:
            satirlar = _sorgu_d1_json(args.d1_json)
        else:
            satirlar = _sorgu_d1(gun)
    except SekilHatasi:
        sys.stdout.write("INIS=OLCULEMEDI sebep=D1-SEKIL\n")
        return 3
    except Exception as e:
        # Canli D1 erisilemez (token, ag, DNS) — sessiz 0 YASAK.
        sys.stdout.write("INIS=OLCULEMEDI sebep=D1\n")
        return 3

    # satir = (kaynak, kampanya, n)
    normal = [(s.get("kaynak", ""), s.get("kampanya", ""), s.get("n", 0))
              for s in satirlar]

    fb, ig, g, geo, diger, toplam = _sinif_topla(normal)
    sys.stdout.write(
        "INIS gun=%s UTM_FB=%d UTM_IG=%d UTM_G=%d UTM_GEO=%d UTM_DIGER=%d TOPLAM=%d\n"
        % (gun, fb, ig, g, geo, diger, toplam)
    )

    if args.kampanya:
        # n azalan; esitlikte kaynak sonra kampanya alfabetik (sabit).
        sirali = sorted(normal, key=lambda r: (-(int(r[2]) if str(r[2]).isdigit() else 0),
                                                (r[0] or "").lower(),
                                                (r[1] or "").lower()))
        for kaynak, kampanya, n in sirali:
            sys.stdout.write("  %s %s %s\n" % (kaynak, kampanya, n))

    return 0


if __name__ == "__main__":
    sys.exit(main())