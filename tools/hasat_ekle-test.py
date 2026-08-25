#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K302 — hasat_ekle KABUL TESTİ (üç vaka).

K302 (MaCiT BMW/Ford x TV olayi, 26 Agu 2026): ic["marka"] liste bicimindeyken
uyum = [{"marka": ic["marka"]}] satiri LISTEYİ dogrudan yaziyor,
marka_uyumdan_turet() ise string bekliyordu — u["marka"] = [] SESSIZCE bos kaliyordu.

KABUL: uyum_uret() URETIM yolunu cagirir. Fikstur kopyasi DEGIL.
"""
import os
import sys

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

from tools.hasat_ekle import uyum_uret  # noqa: E402


def _baslik(s):
    print("\n=== %s ===" % s)


_sonuclar = {"gecti": 0, "kaldi": 0, "toplam": 0}


def _kontrol(ad, kosul, sebep=""):
    _sonuclar["toplam"] += 1
    if kosul:
        _sonuclar["gecti"] += 1
        print("  [OK]   %s" % ad)
    else:
        _sonuclar["kaldi"] += 1
        print("  [FAIL] %s  %s" % (ad, sebep))


# =================================================================
# VAKA A: 2 elemanli liste — eskiden SESSIZ bosalirdi, simdi dogru turetilmeli
# =================================================================
_baslik("VAKA A: ['BMW','E30'] (2 elemanli liste)")

uyum_a, marka_a = uyum_uret(["BMW", "E30"])
_kontrol(
    "uyum[0] tam {'marka':'BMW','model':'E30'}",
    uyum_a == [{"marka": "BMW", "model": "E30"}],
    "uyum=%r" % uyum_a,
)
_kontrol(
    "u['marka'] bos DEGIL",
    isinstance(marka_a, list) and len(marka_a) > 0,
    "marka=%r" % marka_a,
)
_kontrol(
    "u['marka'] icinde 'BMW' var",
    "BMW" in marka_a,
    "marka=%r" % marka_a,
)
_kontrol(
    "u['marka'] icinde 'E30' var",
    "E30" in marka_a,
    "marka=%r" % marka_a,
)


# =================================================================
# VAKA B: 1 elemanli liste — REGRESYON YASAGI (Audi davranisi bozulmamali)
# =================================================================
_baslik("VAKA B (regresyon): ['Audi'] (1 elemanli liste)")

uyum_b, marka_b = uyum_uret(["Audi"])
_kontrol(
    "uyum[0] {'marka':'Audi'} (model yok)",
    uyum_b == [{"marka": "Audi"}],
    "uyum=%r" % uyum_b,
)
_kontrol(
    "u['marka'] == ['Audi']",
    marka_b == ["Audi"],
    "marka=%r" % marka_b,
)


# =================================================================
# VAKA B-2: string giris — eski davranis korunur (regresyon)
# =================================================================
_baslik("VAKA B-2 (regresyon): 'Renault' (string)")

uyum_b2, marka_b2 = uyum_uret("Renault")
_kontrol(
    "uyum[0] {'marka':'Renault'}",
    uyum_b2 == [{"marka": "Renault"}],
    "uyum=%r" % uyum_b2,
)
_kontrol(
    "u['marka'] == ['Renault']",
    marka_b2 == ["Renault"],
    "marka=%r" % marka_b2,
)


# =================================================================
# VAKA C: FAIL-CLOSED — marka turetilemeyen girdi sessiz gecmemeli
# =================================================================
_baslik("VAKA C: FAIL-CLOSED — bilinmeyen marka (string)")

try:
    _uyum_c, _marka_c = uyum_uret("XyzUnknownBrandBilinmiyor")
    _kontrol("ValueError firlatilmali", False, "sessiz gecti: %r" % (_marka_c,))
except ValueError as e:
    _kontrol("ValueError firlatildi (fail-closed)", True)
    _kontrol(
        "hata mesaji anlamli (marka turetilemedi gecti)",
        "marka turetilemedi" in str(e),
        "msg=%r" % str(e),
    )


# =================================================================
# VAKA D: bos liste — TAMBO MARKALI KAYIT, fail-closed TETIKLENMEMELI
# =================================================================
_baslik("VAKA D (sınır): [] (bos liste) — fail-closed tetiklenmemeli")

try:
    uyum_d, marka_d = uyum_uret([])
    _kontrol(
        "bos liste sessiz gecti (kayit markasiz)",
        uyum_d == [{"marka": ""}] and marka_d == [],
        "uyum=%r marka=%r" % (uyum_d, marka_d),
    )
except ValueError as e:
    _kontrol("bos liste sessiz gecmeli (ValueError olmamali)", False, str(e))


# =================================================================
# VAKA E: None — TAMBO MARKALI KAYIT, fail-closed TETIKLENMEMELI
# =================================================================
_baslik("VAKA E (sınır): None — fail-closed tetiklenmemeli")

try:
    uyum_e, marka_e = uyum_uret(None)
    _kontrol(
        "None sessiz gecti",
        uyum_e == [{"marka": ""}] and marka_e == [],
        "uyum=%r marka=%r" % (uyum_e, marka_e),
    )
except ValueError as e:
    _kontrol("None sessiz gecmeli (ValueError olmamali)", False, str(e))


# =================================================================
# VAKA F: 3+ elemanli liste — bilincli sekilde ilk ikisi alinir
# =================================================================
_baslik("VAKA F (sınır): ['Ford','Focus','Mk3'] (3 eleman)")

uyum_f, marka_f = uyum_uret(["Ford", "Focus", "Mk3"])
_kontrol(
    "uyum[0] ilk iki: {'marka':'Ford','model':'Focus'}",
    uyum_f == [{"marka": "Ford", "model": "Focus"}],
    "uyum=%r" % uyum_f,
)
_kontrol(
    "u['marka'] icinde 'Ford' var",
    "Ford" in marka_f,
    "marka=%r" % marka_f,
)


# =================================================================
# VAKA G: gecersiz tip — ValueError (tur kontrolu)
# =================================================================
_baslik("VAKA G (sınır): 42 (int) — ValueError")

try:
    _uyum_g, _marka_g = uyum_uret(42)
    _kontrol("int icin ValueError beklenir", False, "sessiz gecti")
except ValueError as e:
    _kontrol("int icin ValueError firlatildi", True)


# =================================================================
# SONUCLAR
# =================================================================
print()
print("=" * 60)
print("VAKA=%d/%d  (gecti/toplam)" % (_sonuclar["gecti"], _sonuclar["toplam"]))
print("=" * 60)

if _sonuclar["kaldi"] > 0:
    print("\n%d KABUL BASARISIZ" % _sonuclar["kaldi"])
    sys.exit(1)
print("\nTUM KABUL GECTI")
sys.exit(0)
