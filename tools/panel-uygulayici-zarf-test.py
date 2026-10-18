#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — tools/panel-uygulayici.py GERCEK wrangler D1 zarf fiksturuyle konusuyor mu?

  python3 tools/panel-uygulayici-zarf-test.py

VAKA (Z): `WranglerKuyruk.beklemede_oku` / `sayilar` `d1_zarf_fikstur.zarf(...)` ile
beslenir; satir sayilari birebir beklenenle eslesmeli.

MUTANT (M1): mutant kopyada `blok.get("results")` -> `[]` kirilir; beklemede_oku
bos liste doner.

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
ARAC = os.path.join(TOOLS, "panel-uygulayici.py")


def _yukle_isimle(ad, modul_yol):
    spec = importlib.util.spec_from_file_location(ad, modul_yol)
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


def _yukle_arac(arac_yolu, modul_ad):
    spec = importlib.util.spec_from_file_location(modul_ad, arac_yolu)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    gecen, hata = [], []

    # ── Z: WranglerKuyruk beklemede_oku + sayilar d1_zarf_fikstur ile beslenir ─
    m = _yukle_arac(ARAC, "panel_uygulayici_zarf")
    bek_beklemede = [
        {"id": 1, "hal": "beklemede", "sebep": None, "commit": None},
        {"id": 2, "hal": "beklemede", "sebep": None, "commit": None},
        {"id": 3, "hal": "beklemede", "sebep": None, "commit": None},
    ]
    bek_sayilar = [
        {"hal": "beklemede", "adet": 3},
        {"hal": "uygulandi", "adet": 7},
    ]

    class Faked1:
        def __init__(self):
            self.zarf_beklemede = d1_zarf_fikstur.zarf(bek_beklemede)
            self.zarf_sayilar = d1_zarf_fikstur.zarf(bek_sayilar)

        def sorgu(self, sql):
            return self.zarf_beklemede if "panel_ustyazim WHERE hal='beklemede'" in sql \
                else self.zarf_sayilar

    # WranglerKuyruk, kok olarak ROOT kullanir; testler icin gecici kok verelim.
    yk = m.WranglerKuyruk(ROOT)
    yk.d1 = Faked1()
    bekler = yk.beklemede_oku()
    sayilar = yk.sayilar()
    if (len(bekler) == 3 and sayilar.get("beklemede") == 3
            and sayilar.get("uygulandi") == 7):
        gecen.append("Z")
    else:
        hata.append("Z wrangler zarf ayristirilmadi: bekler=%d sayilar=%r"
                    % (len(bekler), sayilar))

    # ── M1: izole kopyada `blok.get("results")` -> `[]` kirilir ───────────────
    tmp = tempfile.mkdtemp(prefix="panel-mutant-")
    try:
        with open(ARAC, encoding="utf-8") as f:
            govde = f.read()
        # Aracin iki yerde `blok.get("results")` geciriyor olabilir; AYNI mutant YETERLI
        capa = 'satirlar.extend((blok.get("results") or []))'
        if govde.count(capa) != 1:
            raise AssertionError("MUTANT CAPASI BAYAT: %r govdede %d kez"
                                 % (capa, govde.count(capa)))
        mutant = govde.replace(capa, 'satirlar.extend([])', 1)
        ns = {"__name__": "_mutant_", "__file__": ARAC, "sys": sys, "os": os}
        try:
            exec(mutant, ns)
        except SystemExit:
            pass
        WkMut = ns.get("WranglerKuyruk")
        if WkMut is None:
            hata.append("M1 mutant govdesi yuklenemedi (WranglerKuyruk bulunamadi)")
        else:
            yk2 = WkMut(ROOT)
            yk2.d1 = Faked1()
            try:
                bekler2 = yk2.beklemede_oku()
                if len(bekler2) == 0:
                    gecen.append("M1")
                else:
                    hata.append("M1 mutant ayni sonucu verdi: %d" % len(bekler2))
            except Exception as e:
                hata.append("M1 mutant istisna firlatti: %s" % e)
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