#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""D1 `siparisler` tablosundan BIR GUNUN siparislerini KAMPANYA SINIFIYLA okur. SALT-OKUNUR.

ArTisT'in gunluk olcum satirina kampanya sutunu verir (BaBa tik 244 D, 27 Eki 2026).
Kampanya sinifi YENI bir alandan degil, siparisin ZATEN tasidigi `atif.ref`'ten turer:
`attribution-ref.js` inis aninda REF:<SRC>-<GRUP>-<RND4> uretir ve grup, inis sayacinin
kampanya sinifiyla ayni haritadan gelir (KAMPANYA_GRUP: figur-arama -> FIG,
yeniden-pazarlama -> YP; utm_campaign bos -> GY = gclid-yalniz; harita disi -> UC).

Kullanim:
    python3 tools/siparis-kampanya-oku.py                    # bugun UTC
    python3 tools/siparis-kampanya-oku.py --gun 2026-10-26   # belirli gun (UTC)
    python3 tools/siparis-kampanya-oku.py --vt /tmp/test.db  # sqlite fiksturu (D1 yerine)

CIKTI (uc satir, sabit sira):
    D1_SIPARIS gun=<g> odenmis=<n>/<TL> bekleyen=<n>/<TL> iptal=<n>/<TL> TOPLAM=<n>
    SIPARIS_KAMPANYA gun=<g> <sinif>=<n>/<TL> ...      # yalniz ODENMIS siparisler
    SIPARIS_BEKLEYEN gun=<g> <sinif>=<n>/<TL> ...      # odenmemis, iptal DEGIL

SINIFLAR (sabit sira): figur-arama · gclid · yeniden-pazarlama · ucretli-diger ·
    ucretli-grup · organik · whatsapp · atif-yok
  - kanal='whatsapp' -> whatsapp (atif tarayicidan gecmez, bostur)
  - ref BOS ya da kalip disi -> atif-yok. 🔴 OLCULEMEDI DEGIL: etiketin yoklugu gecerli bir
    olcumdur ("bu siparis atifsiz geldi"); OLCULEMEDI yalniz D1 okunamazsa basilir.
  - REF:OG-* -> organik · REF:GS-FIG/GY/YP/UC -> figur-arama/gclid/yeniden-pazarlama/
    ucretli-diger · REF:GS-<baska grup> (pg) -> ucretli-grup · baska kaynak -> ucretli-diger

ODENMIS = durum in {odendi, uretimde, kargolandi, tamamlandi} (shop/src/yonet.js
TUM_DURUMLAR'dan). iptal ayri sayilir. Bilinmeyen durum -> OLCULEMEDI (sessiz yanlis
siniflama YOK).

KISISEL VERI: SELECT musteri_ad / musteri_tel / musteri_notu / atif'in ref disindaki
alanlarini HIC SECMEZ; ciktida siparis numarasi bile yoktur.

HATALAR (rc, satir):
    rc=2  SIPARIS=OLCULEMEDI sebep=GUN-BICIMI
    rc=3  SIPARIS=OLCULEMEDI sebep=D1 | D1-SEKIL | BILINMEYEN-DURUM
    rc=0  Siparis yoksa sifirlarla ayni satirlar ("0 siparis" gecerli olcumdur)

D1 erisimi + SQL kacisi `tools/d1-sync.py`den (importlib) — inis-sayac-oku.py ile ayni desen.
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

SINIFLAR = ("figur-arama", "gclid", "yeniden-pazarlama", "ucretli-diger", "ucretli-grup",
            "organik", "whatsapp", "atif-yok")
GS_GRUP = {"FIG": "figur-arama", "GY": "gclid", "YP": "yeniden-pazarlama",
           "UC": "ucretli-diger"}
REF_RE = re.compile(r"^REF:([A-Z]{2})-([A-Z0-9]{2,4})-[A-Z0-9]{4}$")
ODENMIS = frozenset(("odendi", "uretimde", "kargolandi", "tamamlandi"))
BEKLEYEN = frozenset(("bekliyor", "basarisiz", "incele", "havale-bekliyor"))
IPTAL = frozenset(("iptal",))
ALANLAR = ("durum", "kanal", "tutar_kurus", "kargo_kurus", "ref")
# json_valid KORUMASI: atif-oncesi satirlarda atif '' (DEFAULT) — json_extract('') SQLite'ta
# HATA firlatir ve gunun tamami OLCULEMEDI'ye duserdi (fikstur V1 yakaladi).
SQL_GOVDE = ("SELECT durum, kanal, tutar_kurus, kargo_kurus, "
             "CASE WHEN json_valid(atif) THEN json_extract(atif, '$.ref') END AS ref "
             "FROM siparisler WHERE substr(tarih, 1, 10) = ")


class SekilHatasi(ValueError):
    """D1 cevabi beklenen zarf/satir seklinde degil."""


class DurumHatasi(ValueError):
    """Bilinmeyen siparis durumu — siniflanamaz."""


def sinif(kanal, ref):
    """(kanal, ref) -> SINIFLAR'dan biri."""
    if (kanal or "").strip().lower() == "whatsapp":
        return "whatsapp"
    m = REF_RE.match(ref or "")
    if not m:
        return "atif-yok"
    kaynak, grup = m.group(1), m.group(2)
    if kaynak == "OG":
        return "organik"
    if kaynak == "GS":
        return GS_GRUP.get(grup, "ucretli-grup")
    return "ucretli-diger"


def _kurus(v):
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        raise SekilHatasi("tutar tamsayi degil")


def topla(satirlar):
    """satirlar -> (ozet dict, odenmis sinif dict, bekleyen sinif dict). Tutar KURUS."""
    ozet = {"odenmis": [0, 0], "bekleyen": [0, 0], "iptal": [0, 0]}
    od = {s: [0, 0] for s in SINIFLAR}
    bek = {s: [0, 0] for s in SINIFLAR}
    for r in satirlar:
        durum = (r.get("durum") or "").strip().lower()
        tutar = _kurus(r.get("tutar_kurus")) + _kurus(r.get("kargo_kurus"))
        s = sinif(r.get("kanal"), r.get("ref"))
        if durum in ODENMIS:
            kova, sk = ozet["odenmis"], od[s]
        elif durum in BEKLEYEN:
            kova, sk = ozet["bekleyen"], bek[s]
        elif durum in IPTAL:
            kova, sk = ozet["iptal"], None
        else:
            raise DurumHatasi(durum or "<bos>")
        kova[0] += 1
        kova[1] += tutar
        if sk is not None:
            sk[0] += 1
            sk[1] += tutar
    return ozet, od, bek


def tl(kurus):
    return "%d.%02d" % (kurus // 100, kurus % 100)


def satirlar_bas(gun, ozet, od, bek):
    toplam = sum(v[0] for v in ozet.values())
    out = ["D1_SIPARIS gun=%s odenmis=%d/%s bekleyen=%d/%s iptal=%d/%s TOPLAM=%d" % (
        gun, ozet["odenmis"][0], tl(ozet["odenmis"][1]), ozet["bekleyen"][0],
        tl(ozet["bekleyen"][1]), ozet["iptal"][0], tl(ozet["iptal"][1]), toplam)]
    for ad, d in (("SIPARIS_KAMPANYA", od), ("SIPARIS_BEKLEYEN", bek)):
        out.append(ad + " gun=" + gun + " " + " ".join(
            "%s=%d/%s" % (s, d[s][0], tl(d[s][1])) for s in SINIFLAR))
    return out


def _gun_bicimi(g):
    if not g or not re.match(r"^\d{4}-\d{2}-\d{2}$", g):
        return None
    try:
        return _dt.datetime.strptime(g, "%Y-%m-%d").date().isoformat()
    except (TypeError, ValueError):
        return None


def _satirlar_coz(raw):
    """wrangler `d1 execute --json` zarf listesi -> satir listesi (sekil disi -> SekilHatasi)."""
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list) or not raw:
        raise SekilHatasi("D1 cevabi bos ya da liste degil")
    satirlar = []
    for zarf in raw:
        if not isinstance(zarf, dict) or not isinstance(zarf.get("results"), list):
            raise SekilHatasi("D1 zarfi 'results' listesi tasimiyor")
        for s in zarf["results"]:
            if not isinstance(s, dict) or not set(ALANLAR) <= set(s):
                raise SekilHatasi("D1 satiri beklenen alanlari tasimiyor")
            satirlar.append(s)
    return satirlar


def _d1_modulu():
    yol = os.path.join(TOOLS, "d1-sync.py")
    spec = importlib.util.spec_from_file_location("d1_sync_sko", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sorgu_d1(gun):
    d1 = _d1_modulu()
    return _satirlar_coz(d1.sorgu(SQL_GOVDE + d1.q(gun)))


def _sorgu_sqlite(gun, vt_yolu):
    conn = sqlite3.connect(vt_yolu)
    try:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(SQL_GOVDE + "?", (gun,)).fetchall()]
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gun", metavar="YYYY-MM-DD", default=None)
    ap.add_argument("--vt", metavar="YOL", default=None, help="test kolu: yerel sqlite")
    ap.add_argument("--d1-json", metavar="YOL", default=None, dest="d1_json",
                    help="test kolu: wrangler --json cevabi dosyasi")
    args = ap.parse_args()

    gun = args.gun or _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    if not _gun_bicimi(gun):
        print("SIPARIS=OLCULEMEDI sebep=GUN-BICIMI")
        return 2
    try:
        if args.vt:
            satirlar = _sorgu_sqlite(gun, args.vt)
        elif args.d1_json:
            with open(args.d1_json, encoding="utf-8") as f:
                satirlar = _satirlar_coz(json.load(f))
        else:
            satirlar = _sorgu_d1(gun)
        ozet, od, bek = topla(satirlar)
    except SekilHatasi:
        print("SIPARIS=OLCULEMEDI sebep=D1-SEKIL")
        return 3
    except DurumHatasi as e:
        print("SIPARIS=OLCULEMEDI sebep=BILINMEYEN-DURUM durum=%s" % str(e)[:32])
        return 3
    except Exception:
        print("SIPARIS=OLCULEMEDI sebep=D1")
        return 3
    for s in satirlar_bas(gun, ozet, od, bek):
        print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
