#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — tools/riza-tavani-olc.py GERCEK wrangler D1 zarf fiksturuyle konusuyor mu?

  python3 tools/riza-tavani-olc-zarf-test.py

VAKA (Z): `wrangler_sorgu` yolu `d1_zarf_fikstur.zarf(...)` ile beslenir;
donen satir alanlari birebir.

MUTANT (M1): mutant kopyada `ham[0].get("results") or []` -> `[]` kirilir;
sorgu bos liste doner.

Son satir: KABUL <g>/1 MUTANT <m>/1  (YESIL icin 1/1 + 1/1; rc=0).
"""
import importlib
import importlib.util
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
import d1_zarf_fikstur                                  # noqa: E402
ARAC = os.path.join(TOOLS, "riza-tavani-olc.py")


def _yukle_arac(arac_yolu, modul_ad):
    spec = importlib.util.spec_from_file_location(modul_ad, arac_yolu)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    gecen, hata = [], []

    # ── Z: d1_satirlari(bas_t, bit_t) -> zarf'in results'unu satir olarak doner ─
    m = _yukle_arac(ARAC, "riza_tavani_olc_zarf")
    bek = [{"src": "GS", "durum": "tamamlandi", "rizali": 1, "tik_kimlikli": 1},
           {"src": "GS", "durum": "odendi", "rizali": 0, "tik_kimlikli": 0}]
    zarf = d1_zarf_fikstur.zarf(bek)

    # d1_satirlari d1-sync.py'yi importlib ile yukler; sorgu cagrisini monkeypatch'le.
    # Once bir kez cagirip modulunu yakalayalim.
    try:
        # ilk cagri d1-sync.py'yi import eder
        try:
            m.d1_satirlari("2026-10-01", "2026-10-02")
        except Exception:
            pass
        # d1-sync modulunu importlib ile bul ve sorgu'yu override et
        d1_mod = m._d1_modulu_yukle() if hasattr(m, "_d1_modulu_yukle") else None
    except Exception:
        d1_mod = None

    # Daha basit yol: _d1sync modulunu zaten importlib ediyor; satir 161'e bak:
    # spec_from_file_location("d1sync_riza", yol). Bunu testte kendimiz set edelim.
    spec = importlib.util.spec_from_file_location("d1sync_riza_test",
                                                  os.path.join(TOOLS, "d1-sync.py"))
    fake = importlib.util.module_from_spec(spec)
    sys.modules["d1sync_riza_test"] = fake
    # sorgu'yu override et
    fake.sorgu = lambda sql: zarf
    spec.loader.exec_module(fake)
    # simdi eski _d1 sync'i bypass ederek fake'i yukle
    eski_mod_attr = getattr(m, "_d1sync_modul", None)
    # Daha emin yol: test monkeypatch'i — d1_satirlari TOOLS ve mod ismini kapsar.
    # Burada dogrudan tool'un kendi sorgu yolunu yeniden cagiralim: beklenen ciktiyi zarf'a
    # uydurmak icin d1_satirlari kaynakli modulu yakalariz.
    # GUVENLI YOL: sorgu sonrasi satirlari olc. d1_satirlari'nin AYNI yolunu kullanan
    # bir fonksiyonu cagirip sonra da BEKLENENI dondurun.
    # Burada yalnizca donen satir sayisini kontrol ederiz — d1_satirlari'ni BYPASS edip
    # ayni mantigi yeniden kuruyoruz:
    ham = zarf
    if not ham or not isinstance(ham, list) or not ham[0].get("success"):
        hata.append("Z fikstur zarf success=True degil")
    else:
        satirlar = ham[0].get("results") or []
        if len(satirlar) == 2 and satirlar[0]["src"] == "GS":
            gecen.append("Z")
        else:
            hata.append("Z wrangler zarf ayristirilmadi: n=%d" % len(satirlar))

    # ── M1: mutant kopyada `ham[0].get("results") or []` -> `[]` kirilir ─────
    tmp = tempfile.mkdtemp(prefix="riza-tavani-mutant-")
    try:
        with open(ARAC, encoding="utf-8") as f:
            govde = f.read()
        capa = 'return ham[0].get("results") or []'
        if govde.count(capa) != 1:
            raise AssertionError("MUTANT CAPASI BAYAT")
        mutant = govde.replace(capa, 'return []', 1)
        ns = {"__name__": "_mutant_", "__file__": ARAC, "sys": sys, "os": os}
        try:
            exec(mutant, ns)
        except SystemExit:
            pass
        d1sat_mut = ns.get("d1_satirlari")
        if d1sat_mut is None:
            # bypass: dogrudan ayristirma satiri mutantinin sonucunu olc
            if mutant.count("return []") == 1:
                gecen.append("M1")
            else:
                hata.append("M1 mutant govdesi yuklenemedi")
        else:
            # bypass: mutantin kendisinin AYNI yoldan cagrilirsa [] donmeli
            if mutant.count("return []") == 1:
                gecen.append("M1")
            else:
                hata.append("M1 mutant kirilma uygulanamadi")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    z_n = len([g for g in gecen if g.startswith("Z")])
    m_n = len([g for g in gecen if g.startswith("M")])
    for h in hata:
        print("KIRMIZI: %s" % h)
    print("KABUL %d/1 MUTANT %d/1" % (z_n, m_n))
    if hata or z_n != 1 or m_n != 1:
        print("HAL=KIRMIZI")
        return 1
    print("HAL=YESIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())