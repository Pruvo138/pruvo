#!/usr/bin/env python3
"""KABUL TESTI — 3 arama adaptorunde `--derin` pagination/keeper-cap AYRIMI (2026-07-18).

SORUN: parity-backfill adaptorleri `[marka, per_max]` ile cagirinca dongu ~per_max keeper'da
DURUYORDU -> binlerce CC urun HIC gorulmuyordu (sessiz kayip). FIX: `--derin` bayragi maxn'i
dongu-cap'inden AYIRIR; derin modda ham havuz ikincil tavana (offset<3000 / page<=100) ya da
`total` tukenene kadar TAM taranir.

BU TESTIN IZOLE ETTIGI SEY: AYNI kucuk maxn (5) ile,
  - derin=False -> dongu maxn'de DURUR  => tam 5 aday (eski davranis birebir).
  - derin=True  -> maxn YOK SAYILIR     => havuz>>5 (tam havuz), ve DETERMINISTIK (2 kos ayni).
Biri `while` kosulundan `derin or`'u ya da inner-break'ten `not derin and`'i geri alirsa,
derin+maxn=5 yine 5'te durur -> test KIRMIZI yanar.

AG YOK: her adaptorun search kaynagi + `mevcut` dedup fonksiyonu MOCK'lanir (deterministik, offline).
Canli smoke (gercek API'de havuz>50) AYRI kosulur; sayilar RAPOR-MIMARA.md'de.

Kosum:  python3 tools/derin-cap-test.py   -> her adaptor icin satir; son 'N/N GECTI' ya da exit 1.
"""
import contextlib
import importlib.util
import io
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
HAVUZ = 137          # sentetik havuz boyu — eski cap 50'den BELIRGIN buyuk (>2x)
KUCUK = 5            # her iki modda da verilen maxn; derin bunu YOK saymali
MARKA = "zeta"       # tam-kelime marka-alaka filtrelerini gecen sentetik marka


def _yukle(dosya, ad):
    spec = importlib.util.spec_from_file_location(ad, os.path.join(_HERE, dosya))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _idler(cikti):
    """main() ciktisindan 'IDLER ...' satirindan SONRAKI id listesini dondur."""
    lines = cikti.splitlines()
    for i, l in enumerate(lines):
        if l.startswith("IDLER"):
            return lines[i + 1].split() if i + 1 < len(lines) else []
    return []


def _kos(ara, derin):
    """ara.main(MARKA, KUCUK, derin=?) -> uretilen id listesi (stdout'tan)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ara.main(MARKA, KUCUK, derin=derin)
    return _idler(buf.getvalue())


# ---------- sentetik havuzlar (her item TUM deterministik filtreleri gecer) ----------
def _pool_thing():
    return [{"id": 90000000 + i, "name": "Zeta bracket %d" % i,
             "like_count": 0, "make_count": 0, "collect_count": 0} for i in range(HAVUZ)]


def _pool_pr():
    return [{"id": 90000000 + i, "name": "Zeta bracket %d" % i, "slug": "zeta-bracket-%d" % i,
             "downloadCount": 0, "likesCount": 0,
             "license": {"abbreviation": "CC-BY"}} for i in range(HAVUZ)]


def _pool_mw():
    return [{"id": 90000000 + i, "title": "Zeta bracket %d" % i, "slug": "zeta-bracket-%d" % i,
             "tags": ["zeta"], "license": "BY", "downloadCount": 0, "likeCount": 0}
            for i in range(HAVUZ)]


# ---------- mock kurucular: search kaynagini + mevcut-dedup'u degistir ----------
def _mock_thing(ara):
    pool = _pool_thing()

    def api(url):
        m = re.search(r"[?&]page=(\d+)", url)
        page = int(m.group(1)) if m else 1
        return {"hits": pool[(page - 1) * 30: page * 30]}
    ara.api = api
    ara.mevcut_thing_idleri = lambda: set()


def _mock_pr(ara):
    pool = _pool_pr()

    def search(term, limit=30, offset=0, ordering="popular"):
        return {"totalCount": len(pool), "items": pool[offset:offset + limit]}
    ara.pr.search = search
    ara.mevcut_idler = lambda: set()


def _mock_mw(ara):
    pool = _pool_mw()

    def search(term, limit=40, offset=0):
        return {"total": len(pool), "hits": pool[offset:offset + limit]}
    ara.mw.search = search
    ara.mevcut_idler = lambda: set()


ADAPTORLER = [
    ("Thingiverse",   "thing-ara.py",         "thing_ara",   _mock_thing),
    ("Printables",    "printables-ara.py",    "pr_ara",      _mock_pr),
    ("MakerWorld",    "makerworld-ara.py",    "mw_ara",      _mock_mw),
]


def main():
    fails = []
    for platform, dosya, ad, mock in ADAPTORLER:
        try:
            ara = _yukle(dosya, ad)
            mock(ara)
            sig = _kos(ara, derin=False)          # eski davranis: maxn=5'te dur
            d1 = _kos(ara, derin=True)             # derin: maxn yok say -> tam havuz
            d2 = _kos(ara, derin=True)             # ikinci kos -> determinizm
            n_sig, n_d1, n_d2 = len(sig), len(d1), len(d2)
            sorun = []
            if n_sig != KUCUK:
                sorun.append("backward-compat cap %d != %d" % (n_sig, KUCUK))
            if not (n_d1 > 50):
                sorun.append("derin havuz %d, 50'den buyuk DEGIL (cap kalkmadi)" % n_d1)
            if n_d1 != n_d2 or d1 != d2:
                sorun.append("derin DETERMINISTIK degil (%d vs %d)" % (n_d1, n_d2))
            if not (n_d1 > n_sig):
                sorun.append("derin(%d) sig(%d)'ten buyuk degil" % (n_d1, n_sig))
            if sorun:
                fails.append((platform, sorun))
                print("  HATA %-14s cap5=%d derin=%d/%d  -> %s"
                      % (platform, n_sig, n_d1, n_d2, "; ".join(sorun)))
            else:
                print("  ok   %-14s cap5=%d (derin YOK)  derin=%d==%d (>50, deterministik)"
                      % (platform, n_sig, n_d1, n_d2))
        except Exception as e:  # noqa: BLE001
            fails.append((platform, [str(e)]))
            print("  HATA %-14s ISTISNA: %s" % (platform, str(e)[:120]))

    print()
    if fails:
        print("BASARISIZ — %d/%d adaptor kaldi:" % (len(fails), len(ADAPTORLER)))
        for platform, sorun in fails:
            print("  x %s: %s" % (platform, "; ".join(sorun)))
        sys.exit(1)
    print("%d/%d GECTI — 3 adaptor: derin=False cap'te durur, derin=True maxn'i yok sayar "
          "(havuz>50) ve deterministik." % (len(ADAPTORLER), len(ADAPTORLER)))


if __name__ == "__main__":
    main()
