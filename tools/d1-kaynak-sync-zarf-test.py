#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — tools/d1-kaynak-sync.py GERCEK wrangler D1 zarf fiksturuyle konusuyor mu?

  python3 tools/d1-kaynak-sync-zarf-test.py

VAKA (Z): aracin D1 okuma yolu (`d1_linkler` + `tablo_var_mi`) `d1_zarf_fikstur.zarf(...)`
ile beslenir; satir sayisi + en az bir alan degeri birebir beklenenle eslesmeli.

MUTANT (M1): mutant kopyada ayristirma satiri `blok.get("results")` -> `[]` kirilir;
Z vakasi KIRMIZI yanar (0 satir sayar).

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
import d1_zarf_fikstur                                  # noqa: E402  (ortak gercek zarf)
ARAC = os.path.join(TOOLS, "d1-kaynak-sync.py")


def _yukle_isimle(ad, modul_yol):
    """Tireli adi importlib ile yukle ve sys.modules'a koy."""
    spec = importlib.util.spec_from_file_location(ad, modul_yol)
    m = importlib.util.module_from_spec(spec)
    sys.modules[ad] = m
    spec.loader.exec_module(m)
    return m


def _yukle_arac(arac_yolu, modul_ad):
    """Aracin govdesini importlib ile yukle (tireli adlar dahil)."""
    spec = importlib.util.spec_from_file_location(modul_ad, arac_yolu)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def mutasyonla(yol, eski, yeni):
    with open(yol, encoding="utf-8") as f:
        govde = f.read()
    if govde.count(eski) != 1:
        raise AssertionError("MUTANT CAPASI BAYAT: %r govdede %d kez" % (eski, govde.count(eski)))
    with open(yol, "w", encoding="utf-8") as f:
        f.write(govde.replace(eski, yeni))


def main():
    gecen, hata = [], []

    # ── Z: gercek zarf fiksturu uzerinden d1_linkler + tablo_var_mi ────────────
    m = _yukle_arac(ARAC, "d1_kaynak_sync_zarf")
    bek = [{"id": "u-001", "link": "https://example.com/a"},
           {"id": "u-002", "link": "https://example.com/b"},
           {"id": "u-003", "link": ""}]
    zarf = d1_zarf_fikstur.zarf(bek)
    # tablo_var_mi: sqlite_master sorgusu tablo adini iceren bir satir donmeli.
    # Icerigi onemsiz; "results bos degil" == tablo var sayimi yeterli.
    zarf_tab = d1_zarf_fikstur.zarf([{"name": "urun_kaynak"}])
    cagri = {"n": 0}

    def sahte_sorgu(sql):
        cagri["n"] += 1
        return zarf if "FROM urun_kaynak" in sql else zarf_tab

    eski_ds = m.ds
    try:
        m.ds = type("DS", (), {"sorgu": staticmethod(sahte_sorgu)})
        var = m.tablo_var_mi()
        linkler = m.d1_linkler()
        if (var is True and len(linkler) == 3
                and linkler["u-001"] == "https://example.com/a"
                and linkler["u-002"] == "https://example.com/b"
                and linkler["u-003"] == ""
                and cagri["n"] >= 2):
            gecen.append("Z")
        else:
            hata.append("Z wrangler zarf ayristirilmadi: var=%s n=%d linkler=%r"
                        % (var, cagri["n"], list(linkler.items())[:3]))
    finally:
        m.ds = eski_ds

    # ── M1: mutant kopyada ayristirma [] olursa d1_linkler bos doner ───────────
    # d1-sync'i ONCE sys.modules'a gercek haliyle koy ki mutant govde onu bulabilsin.
    tmp = tempfile.mkdtemp(prefix="d1-kaynak-sync-mutant-")
    try:
        _yukle_isimle("d1_sync_mutant", os.path.join(TOOLS, "d1-sync.py"))

        with open(ARAC, encoding="utf-8") as f:
            govde = f.read()
        if govde.count('for satir in (blok.get("results") or []):') != 1:
            raise AssertionError("MUTANT CAPASI BAYAT: ana satir bulunamadi")
        mutant = govde.replace('for satir in (blok.get("results") or []):',
                               'for satir in []:', 1)
        # d1-sync modulunu gercekten karsilasacak sekilde loader'i bypass et.
        mutant = mutant.replace(
            '_ds_spec = importlib.util.spec_from_file_location("d1_sync", _DS_YOL)\nds = importlib.util.module_from_spec(_ds_spec)\n_ds_spec.loader.exec_module(ds)',
            'sys.modules["d1_sync"] = sys.modules["d1_sync_mutant"]\n'
            'ds = sys.modules["d1_sync_mutant"]',
            1)
        # KAYNAKLAR'i bos gecici dosyaya yonlendir (yoksa sys.exit).
        sahte_kaynak = os.path.join(tmp, ".urun-kaynaklari.json")
        with open(sahte_kaynak, "w", encoding="utf-8") as f:
            _json.dump({}, f)
        mutant = mutant.replace(
            'KAYNAKLAR = os.path.join(KOK, ".urun-kaynaklari.json")',
            'KAYNAKLAR = %r' % sahte_kaynak, 1)
        mutant = mutant.replace(
            'sys.path.insert(0, os.path.join(KOK, "tools"))',
            'sys.path.insert(0, %r)' % TOOLS, 1)
        ns = {"__name__": "_mutant_", "__file__": ARAC, "sys": sys, "os": os, "json": _json,
              "re": __import__("re"), "importlib": importlib,
              "argparse": __import__("argparse")}
        try:
            exec(mutant, ns)
        except SystemExit:
            pass
        # govde d1-kaynak-sync modulunu adla kaydetmedi; `d1_linkler` ns uzerinden erisilir.
        # Esle: ns icindeki d1_linkler fonksiyonunun __module__'u "_mutant_" olmali.
        if ns.get("d1_linkler") is not None:
            # dummy wrapper: d1_linkler'i bir shim modulune bagla ki m2.ds atayalim.
            shim = type("M", (object,), {
                "d1_linkler": staticmethod(ns["d1_linkler"]),
                "tablo_var_mi": staticmethod(ns["tablo_var_mi"]),
                "ds": None})()
            m2 = shim
        else:
            m2 = ns.get("d1_kaynak_sync") or ns.get("ds")
        if m2 is None:
            hata.append("M1 mutant govdesi yuklenemedi (modul bulunamadi)")
        else:
            zarf2 = d1_zarf_fikstur.zarf(bek)
            zarf2_tab = d1_zarf_fikstur.zarf([{"name": "urun_kaynak"}])
            m2.ds = type("DS", (), {"sorgu": staticmethod(
                lambda sql: zarf2 if "FROM urun_kaynak" in sql else zarf2_tab)})
            try:
                linkler2 = m2.d1_linkler()
                if len(linkler2) == 0:
                    gecen.append("M1")
                else:
                    hata.append("M1 ayristirma [] ile kirildi ama linkler bos degil: %r"
                                % list(linkler2.items())[:3])
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