#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — tools/yayin-kapisi.py GERCEK wrangler D1 zarf fiksturuyle konusuyor mu?

  python3 tools/yayin-kapisi-zarf-test.py

VAKA (Z): `taslak_idler(m)`, `yayinda_idler(m)`, `d1_sayilar(m)` yardimcilari
`d1_zarf_fikstur.zarf(...)` ile beslenir; donen sayilar birebir beklenenle
eslesmeli.

MUTANT (M1): mutant kopyada `r[0].get("results")` -> `[]` kirilir; donen
sayilar/listeler BOS olur.

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
ARAC = os.path.join(TOOLS, "yayin-kapisi.py")


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

    # ── Z: taslak_idler/yayinda_idler/d1_sayilar d1_zarf_fikstur ile calisir ──
    m = _yukle_arac(ARAC, "yayin_kapisi_zarf")
    zarf_taslak = d1_zarf_fikstur.zarf([{"id": "a"}, {"id": "b"}, {"id": "c"}])
    zarf_yayinda = d1_zarf_fikstur.zarf([{"id": "x"}, {"id": "y"}])
    zarf_sayilar = d1_zarf_fikstur.zarf([{"toplam": 5, "yayinda": 2, "taslak": 3}])

    def sahte_sorgu(sql):
        if "COUNT(*)" in sql or "SUM(CASE" in sql:
            return zarf_sayilar
        if "yayinda=0" in sql:
            return zarf_taslak
        if "yayinda=1" in sql:
            return zarf_yayinda
        return d1_zarf_fikstur.zarf([])

    class Faked1:
        sorgu = staticmethod(sahte_sorgu)

    taslaklar = m.taslak_idler(Faked1())
    yayindalar = m.yayinda_idler(Faked1())
    sayilar = m.d1_sayilar(Faked1())
    if (len(taslaklar) == 3 and set(taslaklar) == {"a", "b", "c"}
            and len(yayindalar) == 2 and set(yayindalar) == {"x", "y"}
            and sayilar == (5, 2, 3)):
        gecen.append("Z")
    else:
        hata.append("Z wrangler zarf ayristirilmadi: taslak=%r yayinda=%r sayilar=%r"
                    % (taslaklar, yayindalar, sayilar))

    # ── M1: mutant kopyada `r[0].get("results")` -> `[]` kirilir ───────────────
    # `taslak_idler` ve `yayinda_idler` ayni return satirini paylasiyor; SQL satirini
    # capa'ya dahil edip `taslak_idler` fonksiyonunu HEDEFLEYEREK tekilestiriyoruz
    # (grep birebir: "SELECT id FROM urunler WHERE yayinda=0" + return satiri).
    tmp = tempfile.mkdtemp(prefix="yayin-kapisi-mutant-")
    try:
        with open(ARAC, encoding="utf-8") as f:
            govde = f.read()
        capa = ('    r = m.sorgu("SELECT id FROM urunler WHERE yayinda=0")\n'
                '    return [s["id"] for s in (r[0].get("results") or [])]')
        if govde.count(capa) != 1:
            raise AssertionError(
                "MUTANT CAPASI BAYAT: taslak_idler satiri %d kez gecti (1 bekleniyordu)"
                % govde.count(capa))
        mutant = govde.replace(
            capa,
            '    r = m.sorgu("SELECT id FROM urunler WHERE yayinda=0")\n    return []', 1)
        ns = {"__name__": "_mutant_", "__file__": ARAC, "sys": sys, "os": os}
        try:
            exec(mutant, ns)
        except SystemExit:
            pass
        taslak_idler_mut = ns.get("taslak_idler")
        if taslak_idler_mut is None:
            hata.append("M1 mutant govdesi yuklenemedi (taslak_idler bulunamadi)")
        else:
            try:
                taslaklar2 = taslak_idler_mut(Faked1())
                if len(taslaklar2) == 0:
                    gecen.append("M1")
                else:
                    hata.append("M1 mutant ayni sonucu verdi: %r" % taslaklar2)
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