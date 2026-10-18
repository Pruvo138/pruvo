#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — tools/kanal-kirilim-raporu.py GERCEK wrangler D1 zarf fiksturuyle konusuyor mu?

  python3 tools/kanal-kirilim-raporu-zarf-test.py

VAKA (Z): `d1_satirlari(d1, ...)` yardimcisi `d1_zarf_fikstur.zarf(...)` ile beslenir;
satir sayisi + alan degerleri birebir beklenenle eslesmeli.

MUTANT (M1): izole kopyada ayristirma satiri `r[0].get("results")` -> `r["results"]`
kirilir; Z vakasi KIRMIZI yanar (TypeError ya da bos liste).

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
ARAC = os.path.join(TOOLS, "kanal-kirilim-raporu.py")


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

    # ── Z: d1_satirlari(faked1, ...) -> beklenen sayida satir doner ──────────
    m = _yukle_arac(ARAC, "kanal_kirilim_raporu_zarf")
    bek = [{"tarih": "2026-10-01T00:00:00Z", "durum": "odendi",
            "tutar_kurus": 10000, "kargo_kurus": 0,
            "kanal": "site", "atif": ""},
           {"tarih": "2026-10-02T00:00:00Z", "durum": "tamamlandi",
            "tutar_kurus": 20000, "kargo_kurus": 2500,
            "kanal": "site", "atif": '{"utm_source":"google"}'}]

    def sahte_sorgu(sql):
        return d1_zarf_fikstur.zarf(bek)

    class Faked1:
        sorgu = staticmethod(sahte_sorgu)
        def kolon_var_mi(self, *a, **kw):
            return True

    satirlar, kanal_var = m.d1_satirlari(Faked1(), "", "")
    if (kanal_var is True and len(satirlar) == 2
            and satirlar[0]["tarih"] == "2026-10-01T00:00:00Z"
            and satirlar[1]["tutar_kurus"] == 20000):
        gecen.append("Z")
    else:
        hata.append("Z wrangler zarf ayristirilmadi: kanal_var=%s n=%d ilk=%s"
                    % (kanal_var, len(satirlar), satirlar[0] if satirlar else None))

    # ── M1: mutant kopyada r[0].get("results") -> r["results"] kirilir ───────
    tmp = tempfile.mkdtemp(prefix="kanal-kirilim-mutant-")
    try:
        # Bu aracin modulu ek olarak node koprusunu (kanal-sinif-cli.mjs) kullanir.
        # Bu testin asil OLCUSU D1 zarf ayristirma; node koprusu testlere KONU DEGIL.
        with open(ARAC, encoding="utf-8") as f:
            govde = f.read()
        capa = 'return ((r[0].get("results") or []) if r else []), True'
        if govde.count(capa) != 1:
            raise AssertionError("MUTANT CAPASI BAYAT")
        mutant = govde.replace(capa, 'return ((r["results"] or []) if r else []), True', 1)
        ns = {"__name__": "_mutant_", "__file__": ARAC, "sys": sys, "os": os}
        try:
            exec(mutant, ns)
        except SystemExit:
            pass
        d1_satirlari_mut = ns.get("d1_satirlari")
        if d1_satirlari_mut is None:
            hata.append("M1 mutant govdesi yuklenemedi (d1_satirlari bulunamadi)")
        else:
            try:
                satirlar2, _ = d1_satirlari_mut(Faked1(), "", "")
                if len(satirlar2) == 0:
                    gecen.append("M1")
                else:
                    hata.append("M1 mutant kirildi ama satir doner: %d" % len(satirlar2))
            except TypeError:
                # r["results"] TypeError verir (r liste) — mutantin YAKALANDIGININ kaniti
                gecen.append("M1")
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