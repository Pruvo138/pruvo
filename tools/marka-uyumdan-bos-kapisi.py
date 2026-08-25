#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K302 — marka=uyumdan-bos kapisi: uyum tasirken top-level marka bos ise KIRLI.

KOK NEDEN (MaCiT 26 Agu 2026): hasat_ekle.py ic["marka"] liste bicimindeyken
uyum = [{"marka": ic["marka"]}] ile LISTEYI dogrudan yaziyor,
marka_uyumdan_turet() ise string bekliyor -> u["marka"] = [] SESSIZCE bosaliyor.
61 BMW kaydi boyyle bozuldu, duzelt.py --toplu ile ELLE onarildi; hasat_ekle.py'nin
kok neden duzeltildi (bkz tools/hasat_ekle.py — uyum_uret), ama GECMIS bos kayitlar
DUZELTILMEDEN once bu KAPI ile yakalanir.

ESIK: bir kaydin `uyum` alani non-empty (>=1 oge) VE top-level `marka` alani
EMPTY (yok/null/[]) ise, kayit `marka=uyumdan-bos` sinifina girer -> KIRLI.

UZUN VADEDE: uyum tasima zorunlulugu yok (Tamirat/sinifsiz kayitlar olabilir),
bu yuzden uyum-YOK + marka-bos kombinasyonu KIRLI sayilmaz.

CI'DA: --envanter modunda kirli kayitlarin listesini basar; --ci modunda
kirli varsa rc=1 ile cikar (yayini BLOKLAMAZ — SERIT B).
"""
import argparse
import json
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(KOK, "urunler.json")


def _marka_bos(m):
    """marka alani bos mu? None, [] ya da hic yok."""
    if m is None:
        return True
    if isinstance(m, list) and len(m) == 0:
        return True
    return False


def tara(urunler):
    """KIRLI kayitlari bul: uyum tasir ama top-level marka bos."""
    kirli = []
    for u in urunler:
        uyum = u.get("uyum")
        if not isinstance(uyum, list) or len(uyum) == 0:
            continue  # uyum yok, atla (Tamirat/sinifsiz normal)
        marka = u.get("marka")
        if not _marka_bos(marka):
            continue  # marka dolu, OK
        kirli.append({
            "id": u.get("id"),
            "kategori": u.get("kategori"),
            "uyum_sayisi": len(uyum),
            "sorun": "uyum_tasir_ama_marka_bos",
        })
    return kirli


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--envanter", action="store_true",
                    help="kirli kayitlari bas (varsayilan)")
    ap.add_argument("--ci", action="store_true",
                    help="CI modu: kirli varsa rc=1")
    args = ap.parse_args()

    if not os.path.exists(URUNLER):
        print("URUNLER YOK:", URUNLER, file=sys.stderr)
        sys.exit(2)

    with open(URUNLER, encoding="utf-8") as f:
        urunler = json.load(f)

    kirli = tara(urunler)

    if args.ci:
        # CI: sadece sayi yeterli
        print("K302_MARKA_UYUMDAN_BOS KIRLI=%d / TOPLAM=%d" % (len(kirli), len(urunler)))
        if kirli:
            for k in kirli[:5]:
                print("  ORNEK id=%s kategori=%s uyum=%d" % (
                    k["id"], k["kategori"], k["uyum_sayisi"]))
            sys.exit(1)
        sys.exit(0)

    # --envanter (default)
    print("K302 KAPI — marka=uyumdan-bos")
    print("Toplam kayit          : %d" % len(urunler))
    print("KIRLI (uyum var, marka bos) : %d" % len(kirli))
    if kirli:
        print()
        print("=== KIRLI LISTESI ===")
        for k in kirli[:20]:
            print("  id=%s kategori=%s uyum=%d" % (
                k["id"], k["kategori"], k["uyum_sayisi"]))
        if len(kirli) > 20:
            print("  ... ve %d kirli daha" % (len(kirli) - 20))


if __name__ == "__main__":
    main()
