#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Katalog fiyat tipi normalizasyonu kabul testi; urunler.json'a dokunmaz."""

import copy
import json
import os
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)

import build  # noqa: E402


HATALAR = []


def kontrol(kosul, mesaj):
    if kosul:
        print("  OK: " + mesaj)
    else:
        print("  HATA: " + mesaj)
        HATALAR.append(mesaj)


def urun(pid, fiyat):
    return {
        "id": pid,
        "kategori": "Otomobil",
        "marka": [],
        "baslik": "Fiyat tipi test urunu",
        "aciklama": "Sentetik kabul testi fiksturu.",
        "fiyat": fiyat,
        "gorseller": ["https://media.pruvo3d.com/urunler/fiyat-tipi-test.jpg"],
    }


def yukle(fikstur):
    with tempfile.TemporaryDirectory() as gecici:
        yol = os.path.join(gecici, "fikstur.json")
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(fikstur, f, ensure_ascii=False)
        return build.load_products(yol)


def main():
    sayisal = yukle([urun("fiyat-int-850", 850)])
    xml, adet = build.render_merchant_feed(sayisal)
    kontrol(sayisal[0]["fiyat"] == "850 TL",
            "int fiyat yukleme sinirinda 850 TL olur")
    kontrol(adet == 1 and "<g:price>850 TRY</g:price>" in xml,
            "int fiyat feed'i cokertmez ve 850 olarak girer")

    ham_string = urun("fiyat-string-850", " 850 TL ")
    once, once_adet = build.render_merchant_feed([copy.deepcopy(ham_string)])
    normal = yukle([copy.deepcopy(ham_string)])
    sonra, sonra_adet = build.render_merchant_feed(normal)
    kontrol(normal[0]["fiyat"] == ham_string["fiyat"],
            "string fiyat tek karakter degismeden kalir")
    kontrol(once.encode("utf-8") == sonra.encode("utf-8") and once_adet == sonra_adet,
            "string fiyatli feed normalizasyon oncesi/sonrasi bayt-esittir")

    hatali = urun("fiyat-dict-red", {})
    try:
        yukle([hatali])
    except SystemExit as exc:
        mesaj = str(exc)
        kontrol("fiyat-dict-red" in mesaj and "dict" in mesaj,
                "desteklenmeyen tip id ve tip ile fail-closed duser")
    else:
        kontrol(False, "desteklenmeyen tip sessizce kabul edilmez")

    digerleri = urun("fiyat-alan-koruma", 850)
    beklenen = copy.deepcopy(digerleri)
    beklenen["fiyat"] = "850 TL"
    kontrol(yukle([digerleri])[0] == beklenen,
            "normalizasyon fiyat disindaki alanlara dokunmaz")

    if HATALAR:
        print("KIRMIZI: %d iddia dustu." % len(HATALAR))
        return 1
    print("YESIL: 4 eksen, %d iddia." % 6)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
