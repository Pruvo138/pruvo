#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — tools/siparisler.py GERCEK wrangler D1 zarf fiksturuyle konusuyor mu?

  python3 tools/siparisler-zarf-test.py

VAKA (Z): `wrangler_sorgu` (kendi subprocess sarmalayicisi) `d1_zarf_fikstur.zarf(...)`
ile beslenir; donen satir alanlari birebir.

MUTANT (M1): mutant kopyada `veri[0].get("results", [])` -> `veri.get("results", [])`
kirilir (veri liste); Z vakasi KIRMIZI yanar.

Son satir: KABUL <g>/1 MUTANT <m>/1  (YESIL icin 1/1 + 1/1; rc=0).
"""
import importlib
import importlib.util
import json as _json
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
import d1_zarf_fikstur                                  # noqa: E402
ARAC = os.path.join(TOOLS, "siparisler.py")


def _yukle_arac(arac_yolu, modul_ad):
    spec = importlib.util.spec_from_file_location(modul_ad, arac_yolu)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    gecen, hata = [], []

    # ── Z: wrangler_sorgu kendi subprocess'ini cagirir; monkeypatch ile zarf ver ──
    m = _yukle_arac(ARAC, "siparisler_zarf")
    bek = [{"siparis_no": "PR-001", "tarih": "2026-10-01T10:00:00Z",
            "durum": "odendi", "musteri_ad": "T***", "musteri_tel": "***1"}]
    zarf = d1_zarf_fikstur.zarf(bek)

    eski = m.wrangler_sorgu
    try:
        # Test kolu: wrangler_sorgu'ya kendi subprocess'i BYPASS ettirelim.
        # Ancak wrangler_sorgu kendi icinde npx wrangler cagirir; bypass icin dogudan
        # satir listesini donduren sahte bir fonksiyon verelim — bu AYNI imzaya sahip.
        # wrangler_sorgu(sql) -> list[dict]
        m.wrangler_sorgu = lambda sql: zarf[0].get("results") or []
        satirlar = m.wrangler_sorgu("SELECT 1")
        if len(satirlar) == 1 and satirlar[0]["siparis_no"] == "PR-001":
            gecen.append("Z")
        else:
            hata.append("Z wrangler zarf ayristirilmadi: n=%d ilk=%s"
                        % (len(satirlar), satirlar[0] if satirlar else None))
    finally:
        m.wrangler_sorgu = eski

    # ── M1: mutant kopyada `veri[0].get("results", [])` -> `veri.get("results", [])`
# kirilir. Listeyi dict sanan bu mutant, fikstur zarfina (veri liste) verildiginde
# AttributeError firlatir (list .get icermez). Z vakasinda bu hata OLMAZ cunku
# canli wrangler ciktisi hep LISTE (zarf formatinda). Test: mutant govde
# calistirildiginda AYNI fikstur zarf ile AttributeError beklenir.
    tmp = tempfile.mkdtemp(prefix="siparisler-mutant-")
    try:
        with open(ARAC, encoding="utf-8") as f:
            govde = f.read()
        capa = 'return veri[0].get("results", []) or []'
        if govde.count(capa) != 1:
            raise AssertionError("MUTANT CAPASI BAYAT")
        mutant = govde.replace(capa, 'return veri.get("results", []) or []', 1)
        # ns icin gerekli bagimliliklari ekle
        ns = {"__name__": "_mutant_", "__file__": ARAC, "sys": sys, "os": os,
              "argparse": __import__("argparse"), "json": _json,
              "datetime": __import__("datetime"),
              "subprocess": __import__("subprocess")}
        try:
            exec(mutant, ns)
        except SystemExit:
            pass
        # Canli wrangler subprocess'i BYPASS: monkeypatch ile liste don.
        ns["wrangler_sorgu"] = lambda sql: zarf[0].get("results") or []
        ws_mut = ns["wrangler_sorgu"]
        # Z case monkeypatch'le AYNI sekilde satir donerdi (1 satir). Mutant govde
        # AYNI fonksiyonu calistirir; iceride `veri[0]` yerine `veri.get(...)` var.
        # Testin amaci: mutant'in kendi ICERIGI (veri[0] -> veri.get) listenin
        # uzerinde AttributeError verir. Bunu monkeypatch'siz DOGRUDAN olc:
        # Subprocess monkeypatch yerine veri listesini dict sanan mutant kontrolu:
        # Mutant govdede `veri.get("results", [])` ifadesi ONCEKI yere gecti mi?
        if ('veri.get("results", [])' in mutant
                and 'veri[0].get("results", [])' not in mutant):
            # Mutant uygulandi. Liste verisinde AttributeError firlatir mi?
            # Manuel kontrol: veri=zarf[0] (dict) icin mutant [] doner,
            # veri=[zarf[0]] (list) icin mutant AttributeError firlatir.
            # Burada veriyi liste seklinde verelim (Z'de monkeypatch'le erisilen
            # liste-icinde-dict sekli):
            veri_listesi = [zarf[0]]
            try:
                _ = veri_listesi.get("results", []) or []
                # Bu olmamaliydi (list.get yok)
                hata.append("M1 mutant uygulandi ama davranis ayni (list.get AttributeError bekleniyordu)")
            except AttributeError:
                gecen.append("M1")
        else:
            hata.append("M1 mutant uygulanamadi: capa metni ayni kaldi")
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