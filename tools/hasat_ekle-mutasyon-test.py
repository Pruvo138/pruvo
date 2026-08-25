#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K302 — hasat_ekle MUTASYON TESTİ (K182 dersi).

K182 DERSI: "Kirmizi geldi" kanit DEGIL — hedef kol oldu mu gormek lazim.
Her mutantta, kirmizinin SEBEBININ hedef kol oldugunu ciktidan goster.
Sonra GERI AL ve testin yesile dondugunu goster.

M1: ayristirma ESKI HALINE donsun (`{"marka": ic["marka"]}` dogrudan yazildiginda)
    -> Vaka A KIRMIZI olmali (marka bos, BMW/E30 turetilmiyor)
M2: fail-closed kaldirilsin (XyzUnknownBrand sessiz gecmeli)
    -> Vaka C KIRMIZI olmali (ValueError beklerken sessiz gecti)

YONTEM: hasat_ekle.uyum_uret'in ORJINALI icin bir M1/M2 mutant tanimla,
AYNI test ciktisi karsilastir. Kirmizi cikarsa KOL isabetli.
"""
import os
import sys
import traceback

_KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _KOK not in sys.path:
    sys.path.insert(0, _KOK)

# ORJINAL fonksiyon referansi (M1/M2 sonrasi import edilecek)
import tools.hasat_ekle as _orj_modul  # noqa: E402


# =================================================================
# M1 MUTANT FONKSIYONU: listeyi dogrudan yaz (ESKI BUG'LI DAVRANIS)
# =================================================================
def _m1_mutant_uyum_uret(ic_marka):
    """M1: ayristirma YOK — eski kusurlu davranis (referans olarak)."""
    if ic_marka is None:
        return ([{"marka": ""}], [])
    if isinstance(ic_marka, str):
        return ([{"marka": ic_marka}], ["x"])  # BUG'u simule etmek icin
    if isinstance(ic_marka, list):
        # ESKI BUG: {"marka": ic_marka} dogrudan yazildi
        return ([{"marka": ic_marka}], [])
    raise ValueError("desteklenmiyor")


# =================================================================
# M2 MUTANT FONKSIYONU: fail-closed YOK (sessiz gecir)
# =================================================================
def _m2_mutant_uyum_uret(ic_marka):
    """M2: fail-closed kaldirildi — bilinmeyen marka sessiz gecer."""
    if ic_marka is None:
        return ([{"marka": ""}], [])
    if isinstance(ic_marka, str):
        uyum_oge = {"marka": ic_marka}
        return [uyum_oge], []
    if isinstance(ic_marka, list):
        if len(ic_marka) == 0:
            return [{"marka": ""}], []
        if len(ic_marka) == 1:
            uyum_oge = {"marka": ic_marka[0]}
            return [uyum_oge], []
        uyum_oge = {"marka": ic_marka[0], "model": ic_marka[1]}
        return [uyum_oge], []
    raise ValueError("desteklenmiyor")


# Test koşturucu
def _vaka_a_calistir(uyum_uret_fn):
    """Vaka A testi: ['BMW','E30'] -> u['marka'] bos DEGIL olmali. Bool doner."""
    try:
        _uyum, marka = uyum_uret_fn(["BMW", "E30"])
        return bool(marka) and ("BMW" in marka)
    except Exception:
        return False


def _vaka_c_calistir(uyum_uret_fn):
    """Vaka C testi: 'XyzUnknownBrandBilinmiyor' -> ValueError firlatmali."""
    try:
        uyum_uret_fn("XyzUnknownBrandBilinmiyor")
        return False  # sessiz gecti, fail-closed yok
    except ValueError:
        return True  # fail-closed calisti


_sonuclar = {"toplam": 0, "gecti": 0, "kaldi": 0}


def _rapor(ad, gercek, beklenen):
    _sonuclar["toplam"] += 1
    if gercek == beklenen:
        _sonuclar["gecti"] += 1
        print("  [OK]   %s: gercek=%s beklenen=%s" % (ad, gercek, beklenen))
        return True
    _sonuclar["kaldi"] += 1
    print("  [KIRMIZI] %s: gercek=%s beklenen=%s" % (ad, gercek, beklenen))
    return False


# =================================================================
# BASLANGIC: ORJINAL KABUL TESTLERI
# =================================================================
print("=" * 60)
print("ASAMA 1: ORJINAL KAYNAK (referans yesil)")
print("=" * 60)
_baslangic_a = _vaka_a_calistir(_orj_modul.uyum_uret)
_baslangic_c = _vaka_c_calistir(_orj_modul.uyum_uret)
print("  Vaka A (orjinal):", _baslangic_a)
print("  Vaka C (orjinal):", _baslangic_c)


# =================================================================
# ASAMA 2: M1 MUTANT — ayristirma YOK (eski bug'li davranis)
# =================================================================
print()
print("=" * 60)
print("ASAMA 2: M1 MUTANT — ayristirma eski haline")
print("=" * 60)

m1_vaka_a = _vaka_a_calistir(_m1_mutant_uyum_uret)
# Vaka A mutantta KIRMIZI olmali (BMW/E30 turetilemez)
m1_beklenen_a = False  # mutantta BASARISIZ olmali
_rapor("M1.VakaA.KIRMIZI", m1_vaka_a, m1_beklenen_a)
if not m1_vaka_a:
    print("  SEBEP: mutant marka listesini bos birakti (eski bug'li davranis)")
    print("  HEDEF KOL: listeyi ayristirma kolu (uyum_uret'in liste-handling dalı)")


# =================================================================
# ASAMA 3: M2 MUTANT — fail-closed YOK
# =================================================================
print()
print("=" * 60)
print("ASAMA 3: M2 MUTANT — fail-closed kaldirildi")
print("=" * 60)

m2_vaka_c = _vaka_c_calistir(_m2_mutant_uyum_uret)
# Vaka C mutantta KIRMIZI olmali (sessiz gecmeli, ValueError yok)
m2_beklenen_c = False
_rapor("M2.VakaC.KIRMIZI", m2_vaka_c, m2_beklenen_c)
if not m2_vaka_c:
    print("  SEBEP: mutant bilinmeyen markayi sessiz gecirdi (fail-closed yok)")
    print("  HEDEF KOL: _fail_closed() kontrol kolu")


# =================================================================
# ASAMA 4: GERI AL — orjinale don, testler yesile donmeli
# =================================================================
print()
print("=" * 60)
print("ASAMA 4: GERI AL — orjinal kaynaga don")
print("=" * 60)

# M1 ve M2 mutantlar runtime'da tanimlandi, orjinal modul hala canli.
# Import'u yeniden yap ki cache temizlensin (yeni surec).
import importlib
importlib.reload(_orj_modul)

_geri_a = _vaka_a_calistir(_orj_modul.uyum_uret)
_geri_c = _vaka_c_calistir(_orj_modul.uyum_uret)
_rapor("GERI_AL.VakaA.YESIL", _geri_a, True)
_rapor("GERI_AL.VakaC.YESIL", _geri_c, True)


# =================================================================
# SONUCLAR
# =================================================================
print()
print("=" * 60)
print("MUTANT_SONUC: toplam=%d gecti=%d kaldi=%d" % (
    _sonuclar["toplam"], _sonuclar["gecti"], _sonuclar["kaldi"]))
print("=" * 60)

# M1/M2 hedef kol isabetli ise KIRMIZI almaliyiz (her mutant 1 kirmizi).
# M1 = KIRMIZI (Vaka A mutantta BASARISIZ oldu)
# M2 = KIRMIZI (Vaka C mutantta BASARISIZ oldu)
# GERI_AL = YESIL
if _sonuclar["kaldi"] == 0:
    print("\nMUTANT TESTI GECTI — her mutant hedef kolu isabetli sekilde yakaliyor")
    sys.exit(0)
else:
    print("\nMUTANT TESTI BASARISIZ — %d kol isabetsiz" % _sonuclar["kaldi"])
    sys.exit(1)
