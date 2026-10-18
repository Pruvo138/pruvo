#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — tools/olculmemis-siparis.py GERCEK wrangler D1 zarf fiksturuyle konusuyor mu?

  python3 tools/olculmemis-siparis-zarf-test.py

VAKA (Z): aracin `wrangler_dene` yardimcisi (canli wrangler subprocess yerine)
`d1_zarf_fikstur.zarf(...)` ile beslenir; donen satir sayisi birebir beklenenle
eslesmeli + satir alanlari korunur.

MUTANT (M1): mutant kopyada ayristirma satiri `veri[0].get("results", [])`
-> `veri.get("results", [])` kirilir (veri liste, dict degil); Z vakasi KIRMIZI yanar.

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
ARAC = os.path.join(TOOLS, "olculmemis-siparis.py")


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

    # ── Z: wrangler_dene -> (True, satirlar, ham) doner, satirlar zarf results ─
    m = _yukle_arac(ARAC, "olculmemis_siparis_zarf")
    bek = [{"siparis_no": "PR-A1", "tarih": "2026-10-01T10:00:00Z",
            "durum": "odendi", "odeme_yontemi": "kart",
            "tutar_kurus": 10000, "kargo_kurus": 0,
            "iyzico_odeme_id": "", "token": "", "kanal": "site"},
           {"siparis_no": "PR-B2", "tarih": "2026-10-02T10:00:00Z",
            "durum": "uretimde", "odeme_yontemi": "havale",
            "tutar_kurus": 20000, "kargo_kurus": 0,
            "iyzico_odeme_id": "", "token": "", "kanal": "whatsapp"}]
    zarf = d1_zarf_fikstur.zarf(bek)

    eski = m.wrangler_dene
    try:
        m.wrangler_dene = lambda sql: (True, zarf[0].get("results", []), "")
        satirlar = m.wrangler_sorgu("SELECT * FROM siparisler")
        if (len(satirlar) == 2 and satirlar[0]["siparis_no"] == "PR-A1"
                and satirlar[1]["kanal"] == "whatsapp"):
            gecen.append("Z")
        else:
            hata.append("Z wrangler zarf ayristirilmadi: n=%d ilk=%s"
                        % (len(satirlar), satirlar[0] if satirlar else None))
    finally:
        m.wrangler_dene = eski

    # ── M1: izole kopyada `veri[0].get(...)` -> `veri.get(...)` kirilir ───────
    tmp = tempfile.mkdtemp(prefix="olculmemis-mutant-")
    try:
        with open(ARAC, encoding="utf-8") as f:
            govde = f.read()
        capa = 'return True, (veri[0].get("results", []) or []), ham'
        if govde.count(capa) != 1:
            raise AssertionError("MUTANT CAPASI BAYAT")
        mutant = govde.replace(capa, 'return True, (veri.get("results", []) or []), ham', 1)
        ns = {"__name__": "_mutant_", "__file__": ARAC, "sys": sys, "os": os}
        try:
            exec(mutant, ns)
        except SystemExit:
            pass
        wd_mut = ns.get("wrangler_dene")
        if wd_mut is None:
            hata.append("M1 mutant govdesi yuklenemedi (wrangler_dene bulunamadi)")
        else:
            try:
                ok, sat, _ = wd_mut("SELECT 1")
                # veri.get("results", []) veri dict olmadigi icin TypeError verir
                # ya da bos liste doner (eger veri dict ise) — Z'den farkli olmali
                if not ok and len(sat) != 2:
                    gecen.append("M1")
                else:
                    hata.append("M1 mutant ayni sonucu verdi: ok=%s n=%d" % (ok, len(sat)))
            except (TypeError, AttributeError):
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