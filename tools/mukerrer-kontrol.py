#!/usr/bin/env python3
"""Katalogda mukerrer id, baslik ve kaynak linklerini denetler."""

import argparse
import json
import os
import sys
import tempfile
from collections import defaultdict


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(ROOT, "urunler.json")
KAYNAKLAR = os.path.join(ROOT, ".urun-kaynaklari.json")
ISTISNALAR = os.path.join(ROOT, ".mukerrer-istisna.json")


def _kaynak_linki(kayit):
    """Desteklenen kaynak kaydi biciminden linki cikarir."""
    link = ""
    if isinstance(kayit, str):
        link = kayit.split(None, 1)[0] if kayit.strip() else ""
    elif isinstance(kayit, dict):
        link = kayit.get("link", "")
    elif isinstance(kayit, list) and kayit and isinstance(kayit[0], dict):
        link = kayit[0].get("kaynak") or kayit[0].get("link", "")
    return link.strip() if isinstance(link, str) else ""


def _kaynaklari_oku(path):
    """Kaynak haritasi yoksa veya bozuksa sessizce None dondurur."""
    try:
        with open(path, encoding="utf-8") as f:
            kaynaklar = json.load(f)
    except (OSError, ValueError):
        return None
    return kaynaklar if isinstance(kaynaklar, dict) else None


def _istisnalari_oku(path):
    """Istisna dosyasi yoksa veya bozuksa sessizce bos kume dondurur."""
    try:
        with open(path, encoding="utf-8") as f:
            kayitlar = json.load(f)
    except (OSError, ValueError):
        return set()
    if not isinstance(kayitlar, list):
        return set()
    return {
        kayit.get("kaynak").strip()
        for kayit in kayitlar
        if isinstance(kayit, dict)
        and isinstance(kayit.get("kaynak"), str)
        and kayit.get("kaynak").strip()
    }


def _tara(urunler, kaynaklar=None, istisnalar=None):
    """Bulunan mukerrerleri (tur, deger, idler) olarak dondurur."""
    idler = defaultdict(list)
    basliklar = defaultdict(list)

    for sira, urun in enumerate(urunler):
        if not isinstance(urun, dict):
            continue
        urun_id = urun.get("id")
        gosterim_id = str(urun_id) if urun_id is not None else "#%d" % (sira + 1)
        idler[urun_id].append(gosterim_id)

        baslik = urun.get("baslik")
        if isinstance(baslik, str):
            basliklar[baslik.strip()].append(gosterim_id)

    bulgular = []
    for urun_id, ilgili_idler in idler.items():
        if len(ilgili_idler) > 1:
            bulgular.append(("ID", str(urun_id), ilgili_idler))

    for baslik, ilgili_idler in basliklar.items():
        if len(ilgili_idler) > 1:
            bulgular.append(("BASLIK", baslik, ilgili_idler))

    if kaynaklar is not None:
        linkler = defaultdict(list)
        # Bir id katalogda iki kez geciyorsa kaynak bulgusunu da yapay olarak
        # cogaltma; bu durum zaten mukerrer id bulgusunda raporlanir.
        tekil_idler = dict.fromkeys(
            urun.get("id") for urun in urunler
            if isinstance(urun, dict) and urun.get("id") is not None
        )
        for urun_id in tekil_idler:
            link = _kaynak_linki(kaynaklar.get(urun_id))
            if link and link not in (istisnalar or set()):
                linkler[link].append(str(urun_id))
        for link, ilgili_idler in linkler.items():
            if len(ilgili_idler) > 1:
                bulgular.append(("KAYNAK", link, ilgili_idler))

    return bulgular


def _oz_sinama():
    temiz = [
        {"id": "urun-a", "baslik": "Baslik A"},
        {"id": "urun-b", "baslik": "Baslik B"},
    ]

    kontroller = [
        ("temiz veri", not _tara(temiz, {})),
        ("mukerrer id", any(
            b[0] == "ID" for b in _tara([
                {"id": "ayni", "baslik": "Bir"},
                {"id": "ayni", "baslik": "Iki"},
            ], {})
        )),
        ("mukerrer baslik", any(
            b[0] == "BASLIK" for b in _tara([
                {"id": "bir", "baslik": " Ayni Baslik "},
                {"id": "iki", "baslik": "Ayni Baslik"},
            ], {})
        )),
        ("mukerrer kaynak", any(
            b[0] == "KAYNAK" for b in _tara(temiz, {
                "urun-a": "https://ornek.test/model aciklama",
                "urun-b": [{"kaynak": "https://ornek.test/model"}],
            })
        )),
    ]

    with tempfile.TemporaryDirectory() as gecici:
        olmayan = os.path.join(gecici, "kaynaklar.json")
        try:
            bulgular = _tara(temiz, _kaynaklari_oku(olmayan))
            eksik_dosya_ok = not bulgular
        except Exception:
            eksik_dosya_ok = False
    kontroller.append(("kaynak dosyasi yok", eksik_dosya_ok))

    with tempfile.TemporaryDirectory() as gecici:
        istisna_dosyasi = os.path.join(gecici, "istisnalar.json")
        with open(istisna_dosyasi, "w", encoding="utf-8") as f:
            json.dump([{
                "kaynak": "https://ornek.test/model",
                "neden": "Bilinen ortak kaynak",
            }], f)
        istisnali_bulgular = _tara(temiz, {
            "urun-a": "https://ornek.test/model aciklama",
            "urun-b": [{"kaynak": "https://ornek.test/model"}],
        }, _istisnalari_oku(istisna_dosyasi))
    kontroller.append(("istisnali kaynak", not istisnali_bulgular))

    with tempfile.TemporaryDirectory() as gecici:
        bozuk_istisna = os.path.join(gecici, "istisnalar.json")
        with open(bozuk_istisna, "w", encoding="utf-8") as f:
            f.write("{bozuk json")
        try:
            bozuk_bulgular = _tara(temiz, {
                "urun-a": "https://ornek.test/model aciklama",
                "urun-b": [{"kaynak": "https://ornek.test/model"}],
            }, _istisnalari_oku(bozuk_istisna))
            bozuk_istisna_ok = any(b[0] == "KAYNAK" for b in bozuk_bulgular)
        except Exception:
            bozuk_istisna_ok = False
    kontroller.append(("bozuk istisna dosyasi", bozuk_istisna_ok))

    hatalar = [ad for ad, gecti in kontroller if not gecti]
    if hatalar:
        for ad in hatalar:
            print("TEST KALDI: %s" % ad, file=sys.stderr)
        return 1
    print("TEST GECTI")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--test", action="store_true", help="bellek ici oz-sinamayi calistir")
    args = ap.parse_args()

    if args.test:
        return _oz_sinama()

    with open(URUNLER, encoding="utf-8") as f:
        urunler = json.load(f)
    kaynaklar = _kaynaklari_oku(KAYNAKLAR)
    istisnalar = _istisnalari_oku(ISTISNALAR)
    bulgular = _tara(urunler, kaynaklar, istisnalar)

    if bulgular:
        for tur, deger, ilgili_idler in bulgular:
            print("MUKERRER %s: %s -> %s" % (tur, deger, ", ".join(ilgili_idler)))
        return 1

    print("mukerrer yok: %d urun tarandi" % len(urunler))
    return 0


if __name__ == "__main__":
    sys.exit(main())
