#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — tools/reklam-oci-yukleyici.py GERCEK wrangler D1 zarf fiksturuyle konusuyor mu?

  python3 tools/reklam-oci-yukleyici-zarf-test.py

VAKA (Z): `Oci` sinifinin `sorgu` yolu `d1_zarf_fikstur.zarf(...)` ile beslenir;
donen satir alanlari birebir.

MUTANT (M1): mutant kopyada `(r[0].get("results") or [])` -> `[]` kirilir; sorgu
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
ARAC = os.path.join(TOOLS, "reklam-oci-yukleyici.py")


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

    # ── Z: D1Vt.sorgu `d1_zarf_fikstur` ile calisir ───────────────────────────
    m = _yukle_arac(ARAC, "reklam_oci_yukleyici_zarf")
    bek = [{"id": 1, "name": "CART_TIPI", "ok": 1},
           {"id": 2, "name": "VIEW_CONTENT", "ok": 0}]
    zarf = d1_zarf_fikstur.zarf(bek)

    # D1Vt'yi monkeypatch'le: d1_modulu() -> Faked1
    class Faked1:
        def sorgu(self, sql):
            return zarf
    eski_d1m = m._d1_modulu
    try:
        m._d1_modulu = lambda: Faked1()
        vt = m.D1Vt()
        satirlar = vt.sorgu("SELECT 1")
        if len(satirlar) == 2 and satirlar[0]["name"] == "CART_TIPI":
            gecen.append("Z")
        else:
            hata.append("Z wrangler zarf ayristirilmadi: n=%d ilk=%s"
                        % (len(satirlar), satirlar[0] if satirlar else None))
    finally:
        m._d1_modulu = eski_d1m

    # ── M1: izole kopyada `(r[0].get("results") or [])` -> `[]` kirilir ────────
    tmp = tempfile.mkdtemp(prefix="reklam-oci-mutant-")
    try:
        with open(ARAC, encoding="utf-8") as f:
            govde = f.read()
        capa = 'return (r[0].get("results") or []) if r else []'
        if govde.count(capa) != 1:
            raise AssertionError("MUTANT CAPASI BAYAT")
        mutant = govde.replace(capa, 'return []', 1)
        ns = {"__name__": "_mutant_", "__file__": ARAC, "sys": sys, "os": os}
        try:
            exec(mutant, ns)
        except SystemExit:
            pass
        # Mutant uygulandiginda satir donduren fonksiyon [] donmeli — eski halde 2 donerdi.
        D1VtMut = ns.get("D1Vt")
        if D1VtMut is None:
            hata.append("M1 mutant govdesi yuklenemedi (D1Vt bulunamadi)")
        else:
            try:
                vt2 = D1VtMut()
                sat2 = vt2.sorgu("SELECT 1")
                if len(sat2) == 0:
                    gecen.append("M1")
                else:
                    hata.append("M1 mutant ayni sonucu verdi: %d" % len(sat2))
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