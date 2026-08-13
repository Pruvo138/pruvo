#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Katalog alan-tip semasi kabul testi (offline, tek basina kosar).

Mutant kaniti: `python3 tools/katalog-tip-sinifi-test.py M1` (M1..M4). Mutant
kosumunun rc=1 olmasi, ilgili kabul iddiasinin bozulmayi oldurdugunu gosterir.
"""
import copy
import json
import os
import sys
import warnings

sys.dont_write_bytecode = True

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import arama  # noqa: E402
import filament_ortak  # noqa: E402


def temel(uid="x"):
    return {"id": uid, "kategori": "Ev", "baslik": "Deneme", "aciklama": "Aciklama",
            "fiyat": "430 TL", "gorseller": [], "marka": []}


def alan_ihlali(kayit, alan):
    return [i for i in arama.katalog_tip_ihlalleri([kayit]) if i[1] == alan]


def mutant_uygula(ad):
    if ad == "M1":
        arama.KATALOG_ALAN_TIPLERI = {"fiyat": str}
    elif ad == "M2":
        arama.katalog_alan_tip_sebebi = lambda alan, deger: None
    elif ad == "M3":
        asil = arama.katalog_alan_tip_sebebi

        def boslari_reddet(alan, deger):
            sebep = asil(alan, deger)
            if sebep is None and deger in ("", []):
                return "%s bos deger olamaz" % alan
            return sebep

        arama.katalog_alan_tip_sebebi = boslari_reddet
    elif ad == "M4":
        asil = arama.katalog_alan_tip_sebebi

        def bilinmeyeni_gecir(alan, deger):
            if alan not in arama.KATALOG_ALAN_TIPLERI:
                return None
            return asil(alan, deger)

        arama.katalog_alan_tip_sebebi = bilinmeyeni_gecir
    elif ad:
        raise ValueError("bilinmeyen mutant: %s" % ad)


def main():
    mutant = sys.argv[1] if len(sys.argv) == 2 else ""
    if len(sys.argv) > 2:
        print("KULLANIM: katalog-tip-sinifi-test.py [M1|M2|M3|M4]")
        print("SONUC: 0/9 iddia GECTI")
        return 1
    mutant_uygula(mutant)
    sonuclar = []

    a1 = temel("a1")
    a1["tavsiyeFilament"] = "TPU (esnek filament) önerilir"
    a1_i = alan_ihlali(a1, "tavsiyeFilament")
    with warnings.catch_warnings(record=True) as uyari:
        warnings.simplefilter("always")
        render = filament_ortak.tavsiyeler(a1["kategori"], a1["tavsiyeFilament"])
    sonuclar.append(("A1", len(a1_i) == 1 and "TIP TANIMI YOK" not in a1_i[0][3]
                     and render == [] and len(uyari) == 1
                     and "KATALOG TIP UYARISI" in str(uyari[0].message)))

    a2 = temel("a2")
    a2["fiyat"] = 430
    a2_i = alan_ihlali(a2, "fiyat")
    sonuclar.append(("A2", len(a2_i) == 1 and "TIP TANIMI YOK" not in a2_i[0][3]))

    a3 = temel("a3")
    a3["fiyat"] = ""
    sonuclar.append(("A3", not arama.katalog_tip_ihlalleri([a3])))

    a4_bos = temel("a4-bos")
    a4_bos["marka"] = []
    a4_yok = temel("modular-duvar-boya-sise-organizeri")
    del a4_yok["marka"]
    sonuclar.append(("A4", not arama.katalog_tip_ihlalleri([a4_bos, a4_yok])))

    a5 = temel("a5")
    a5["parametrik"] = False
    sonuclar.append(("A5", not arama.katalog_tip_ihlalleri([a5])))

    a6 = temel("a6")
    a6["parametrik"] = True
    sonuclar.append(("A6", "lisans" not in a6 and not arama.katalog_tip_ihlalleri([a6])))

    a7 = temel("a7")
    a7["gelecektekiAlan"] = "deger"
    a7_i = alan_ihlali(a7, "gelecektekiAlan")
    sonuclar.append(("A7", len(a7_i) == 1 and
                     a7_i[0][3] == "TIP TANIMI YOK: gelecektekiAlan"))

    a8_vakalar = []
    for alan, deger in (("baslik", []), ("gorseller", "url"), ("parametrik", 1)):
        kayit = temel("a8-" + alan)
        kayit[alan] = deger
        ihlal = alan_ihlali(kayit, alan)
        a8_vakalar.append(len(ihlal) == 1 and "TIP TANIMI YOK" not in ihlal[0][3])
    sonuclar.append(("A8", all(a8_vakalar)))

    with open(os.path.join(KOK, "urunler.json"), encoding="utf-8") as f:
        katalog = json.load(f)
    mesru = []
    for kayit in katalog:
        if not arama.katalog_tip_ihlalleri([kayit]):
            mesru.append(copy.deepcopy(kayit))
        if len(mesru) == 200:
            break
    sonuclar.append(("A9", len(mesru) == 200 and
                     not arama.katalog_tip_ihlalleri(mesru)))

    for ad, gecti in sonuclar:
        print("%s: %s" % (ad, "GECTI" if gecti else "KIRMIZI"))
    gecen = sum(1 for ad, gecti in sonuclar if gecti)
    print("SONUC: %d/%d iddia GECTI" % (gecen, len(sonuclar)))
    return 0 if gecen == len(sonuclar) else 1


if __name__ == "__main__":
    sys.exit(main())
