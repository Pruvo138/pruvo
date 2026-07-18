#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""(b) MUKERRER MARKA BIRLESTIRME — urunler.json marka alanindaki ad varyasyonlarini
kanonik forma indirir (site marka cipleri tekillessin) + parity defterini temizler.

TEK YETKILI YOL duzelt.py (guard mevcut urunu geri almasin). Yeni urun EKLENMEZ.
--kuru: sadece ne degisecegini gosterir (yazma yok).

Kanonik esleme (Okan onayi, 18 Tem): aksan/kisaltma varyasyonlari.
  Citroën->Citroen, Škoda->Skoda, SEAT->Seat, VW->Volkswagen.
  VAG ATLANIR (Volkswagen-Audi GROUP; tek marka degil -> dokunma).
"""
import json
import os
import subprocess
import sys

ROOT = "/Users/okan/dev/pruvo"
URUNLER = os.path.join(ROOT, "urunler.json")
DEFTER = os.path.join(ROOT, ".marka-kapsama.json")
PY = sys.executable or "python3"

ESLEME = {"Citroën": "Citroen", "Škoda": "Skoda", "SEAT": "Seat", "VW": "Volkswagen"}
KURU = "--kuru" in sys.argv


def kanonik(marka):
    """marka dizisini kanoniklestir + sirayi koruyarak dedup."""
    yeni = []
    for m in marka:
        k = ESLEME.get(m, m)
        if k not in yeni:
            yeni.append(k)
    return yeni


def main():
    urunler = json.load(open(URUNLER, encoding="utf-8"))
    degisecek = []
    for p in urunler:
        marka = p.get("marka") or []
        if not any(m in ESLEME for m in marka):
            continue
        yeni = kanonik(marka)
        if yeni != marka:
            degisecek.append((p["id"], marka, yeni))

    print("MARKA BIRLESTIRME | %d urun degisecek%s" % (len(degisecek), "  (KURU)" if KURU else ""))
    for uid, eski, yeni in degisecek[:12]:
        print("  %-42s %s -> %s" % (uid[:42], eski, yeni))
    if len(degisecek) > 12:
        print("  ... +%d daha" % (len(degisecek) - 12))
    if KURU:
        return

    ok = 0
    for uid, eski, yeni in degisecek:
        r = subprocess.run([PY, os.path.join(ROOT, "tools", "duzelt.py"), uid,
                            "--alan", "marka", "--deger", json.dumps(yeni, ensure_ascii=False)],
                           capture_output=True, text=True)
        if r.returncode == 0:
            ok += 1
        else:
            print("  HATA %s: %s" % (uid, (r.stderr or r.stdout)[-160:]))
    print("duzelt: %d/%d basarili" % (ok, len(degisecek)))

    # DEFTER TEMIZLIGI: stale varyant anahtarlarini sil, sonra urunler.json'dan yeniden seed et.
    if os.path.exists(DEFTER):
        d = json.load(open(DEFTER, encoding="utf-8"))
        silinen = [k for k in ESLEME if k in d]
        for k in silinen:
            del d[k]
        with open(DEFTER, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2, sort_keys=True)
        print("defter: %d stale varyant anahtari silindi (%s)" % (len(silinen), ",".join(silinen)))
        subprocess.run([PY, os.path.join(ROOT, "tools", "marka-kapsama.py"), "--backfill"],
                       capture_output=True, text=True)
        print("defter: --backfill ile yeniden seed edildi (kanonik markalar birlesti)")


if __name__ == "__main__":
    main()
