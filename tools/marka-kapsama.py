#!/usr/bin/env python3
"""MARKA x PLATFORM kapsama defteri — "hangi markayi hangi sayfada aradik/ekledik".

Amac (Okan, 2026-07-18): marka aramasi TUM platformlarda esitlensin; bir markayi bir
sayfada arayip digerinde unutmayalim. Her ekleme partisi buraya bir kayit dusurur;
rapor hangi (marka,platform) ikilisinin EKSIK oldugunu gosterir.

Kalici defter: /Users/okan/dev/pruvo/.marka-kapsama.json  (gitignore + yedekle --sirlar).

Kullanim:
  python3 tools/marka-kapsama.py                       # matris + eksik (gap) raporu
  python3 tools/marka-kapsama.py --marka Dacia         # tek markanin platform durumu
  python3 tools/marka-kapsama.py kaydet --marka Dacia --platform Printables \
          --taranan 83 --eklenen 57 --elenen 26        # parti sonrasi kayit (ekleme akisi cagirir)
  python3 tools/marka-kapsama.py --backfill            # .urun-kaynaklari.json'dan added-kapsamayi seed et
"""
import argparse
import fcntl
import json
import os
from datetime import datetime, timezone

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFTER = os.path.join(KOK, ".marka-kapsama.json")
KAYNAK = os.path.join(KOK, ".urun-kaynaklari.json")
URUNLER = os.path.join(KOK, "urunler.json")

PLATFORMLAR = ["Printables", "Thingiverse", "MakerWorld", "MyMiniFactory", "********"]
DOMAIN = {
    "thingiverse.com": "Thingiverse", "printables.com": "Printables",
    "makerworld.com": "MakerWorld", "cults3d.com": "Cults3D",
    "myminifactory.com": "MyMiniFactory", "********.com": "********",
}


def _yukle(path, bos):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return bos
    return bos


def _defter_oku():
    return _yukle(DEFTER, {})


def _defter_yaz(d):
    with open(DEFTER, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2, sort_keys=True)


def _platform_link(link):
    l = (link or "").lower()
    for dom, ad in DOMAIN.items():
        if dom in l:
            return ad
    return None


def kaydet(marka, platform, taranan, eklenen, elenen, tarih=None):
    if platform not in PLATFORMLAR:
        # esnek: bilinen adlarla eslesmezse yine kaydet ama uyar
        print("UYARI: bilinmeyen platform '%s' (yine de kaydediliyor)" % platform)
    # FLOCK: paralel backfill'ler ayni anda kaydet cagirinca birbirinin ledger yazimini
    # EZMESIN (read-modify-write atomik olmali; defter flock'suzdu -> kayit kaybi riski).
    with open(DEFTER + ".lock", "w") as _lk:
        fcntl.flock(_lk, fcntl.LOCK_EX)
        d = _defter_oku()
        m = d.setdefault(marka, {})
        kayit = m.get(platform, {"taranan": 0, "eklenen": 0, "elenen": 0, "parti": 0})
        kayit["taranan"] = max(kayit.get("taranan", 0), int(taranan or 0))
        kayit["eklenen"] = kayit.get("eklenen", 0) + int(eklenen or 0)
        kayit["elenen"] = kayit.get("elenen", 0) + int(elenen or 0)
        kayit["parti"] = kayit.get("parti", 0) + 1
        kayit["son_tarih"] = tarih or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        m[platform] = kayit
        _defter_yaz(d)
    print("kaydedildi: %s / %s -> taranan=%s eklenen(+%s) elenen(+%s)" %
          (marka, platform, kayit["taranan"], eklenen, elenen))


def backfill():
    """Eklenen urunlerden (kaynak link -> platform, urunler.json -> marka) added-kapsamayi seed et.
    'taranan' bilinmez (0 kalir); en az bir urun varsa o (marka,platform) ARANMIS demektir."""
    kayn = _yukle(KAYNAK, {})
    urun = {p["id"]: p for p in _yukle(URUNLER, [])}
    # Once TAZE turet (idempotent): tekrar calisinca cift saymasin diye eklenen SET edilir, += degil.
    turetilen = {}  # marka -> plat -> count
    ekle = 0
    for uid, k in kayn.items():
        if isinstance(k, dict):
            link = k.get("link") or k.get("kaynak") or k.get("url") or ""
        elif isinstance(k, str):
            link = k
        else:
            continue
        plat = _platform_link(link)
        p = urun.get(uid)
        if not plat or not p:
            continue
        markalar = p.get("marka") or []
        if not markalar:
            continue
        marka = markalar[0]  # birincil marka
        turetilen.setdefault(marka, {}).setdefault(plat, 0)
        turetilen[marka][plat] += 1
        ekle += 1
    d = _defter_oku()
    for marka, plats in turetilen.items():
        m = d.setdefault(marka, {})
        for plat, cnt in plats.items():
            kayit = m.setdefault(plat, {"taranan": 0, "eklenen": 0, "elenen": 0, "parti": 0})
            kayit["eklenen"] = cnt  # SET (overwrite) -> idempotent; taranan/parti/son_tarih korunur
            kayit.setdefault("son_tarih", "backfill")
    _defter_yaz(d)
    print("backfill: %d urun islendi, defter guncellendi (%d marka)" % (ekle, len(d)))


def rapor(tek_marka=None):
    d = _defter_oku()
    if not d:
        print("defter bos. once: python3 tools/marka-kapsama.py --backfill")
        return
    markalar = [tek_marka] if tek_marka else sorted(d.keys())
    bas = "MARKA".ljust(24) + "".join(p[:4].ljust(7) for p in PLATFORMLAR) + " EKSIK"
    print(bas)
    print("-" * len(bas))
    for marka in markalar:
        m = d.get(marka, {})
        hucre = ""
        eksik = []
        for p in PLATFORMLAR:
            k = m.get(p)
            if k and (k.get("eklenen", 0) > 0 or k.get("taranan", 0) > 0):
                hucre += (str(k.get("eklenen", 0))).ljust(7)
            else:
                hucre += "·".ljust(7)
                eksik.append(p)
        print(marka.ljust(24) + hucre + " " + (",".join(e[:4] for e in eksik) if eksik else "—"))
    print("\n(hucre = eklenen sayisi; · = o platformda aranmamis/urun yok; EKSIK = parity acigi)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="komut")
    k = sub.add_parser("kaydet")
    k.add_argument("--marka", required=True)
    k.add_argument("--platform", required=True)
    k.add_argument("--taranan", type=int, default=0)
    k.add_argument("--eklenen", type=int, default=0)
    k.add_argument("--elenen", type=int, default=0)
    k.add_argument("--tarih", default=None)
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--marka", dest="rapor_marka", default=None)
    a = ap.parse_args()
    if a.komut == "kaydet":
        kaydet(a.marka, a.platform, a.taranan, a.eklenen, a.elenen, a.tarih)
    elif a.backfill:
        backfill()
    else:
        rapor(a.rapor_marka)
