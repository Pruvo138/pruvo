#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — tools/d1-sync.py wrangler_cikti_coz() GERCEK wrangler D1 zarf fiksturuyle konusuyor mu?

  python3 tools/d1-sync-zarf-test.py

VAKA (Z1): `wrangler_cikti_coz(zarf_metni([...]))` -> liste; `r[0]["results"]` 2 satir,
degerler birebir.
VAKA (Z2): wrangler stdout'unda zarftan ONCE uyari metni ("▲ [WARNING] x\n") oldugu hali;
Ayni 2 satir (eski `find("[")` kodu bunu atliyordu — ortak fikstur bunu da olcer).

MUTANT (M1): mutant kopyada `wrangler_cikti_coz` icindeki zarf cozme satirindan biri
(`    yuk, _, aday = _json_tara(stdout)`) `    yuk, _, aday = _json_tara("")` yapilir;
stdout yutulur, Z1 sys.exit ile KIRMIZI yanar.

Son satir: KABUL <g>/2 MUTANT <m>/1  (YESIL icin 2/2 + 1/1; rc=0).
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
sys.path.insert(0, TOOLS)
import d1_zarf_fikstur                                  # noqa: E402
ARAC = os.path.join(TOOLS, "d1-sync.py")

BEK_SATIRLAR = [{"id": 1, "ad": "x"}, {"id": 2, "ad": "y"}]


def _yukle_arac(arac_yolu, modul_ad):
    spec = importlib.util.spec_from_file_location(modul_ad, arac_yolu)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _coz_zarf(m, metin):
    """wrangler_cikti_coz'u cagir; SystemExit olursa None don."""
    try:
        return m.wrangler_cikti_coz(metin, "", 0)
    except SystemExit as e:
        print("  wrangler_cikti_coz sys.exit: %s" % (str(e)[:120]))
        return None


def _esle_zarf(r):
    """Donen liste birebir beklenen 2 satira esit mi?"""
    if not isinstance(r, list) or not r:
        return False
    if not (isinstance(r[0], dict) and isinstance(r[0].get("results"), list)):
        return False
    if len(r[0]["results"]) != len(BEK_SATIRLAR):
        return False
    return all(r[0]["results"][i] == BEK_SATIRLAR[i] for i in range(len(BEK_SATIRLAR)))


def main():
    gecen, hata = [], []

    # ── Canli araci yukle (monkeypatch'siz, saf modul yukleme) ───────────────
    m = _yukle_arac(ARAC, "d1_sync_zarf")

    # ── Z1: sade zarf metni -> 2 satir birebir ──────────────────────────────
    metin1 = d1_zarf_fikstur.zarf_metni(BEK_SATIRLAR)
    r1 = _coz_zarf(m, metin1)
    if _esle_zarf(r1):
        gecen.append("Z1")
    else:
        hata.append("Z1 sade zarf ayristirilmadi: r=%r" % (r1,))

    # ── Z2: zarftan ONCE uyari metni ("▲ [WARNING] x\n") -> AYNI 2 satir ───
    metin2 = "▲ [WARNING] x\n" + metin1
    r2 = _coz_zarf(m, metin2)
    if _esle_zarf(r2):
        gecen.append("Z2")
    else:
        hata.append("Z2 on-ek uyarili zarf ayristirilmadi: r=%r" % (r2,))

    # ── M1: mutant kopyada zarf cozme satiri kirilir (stdout yutulur) ───────
    tmp = tempfile.mkdtemp(prefix="d1-sync-mutant-")
    try:
        with open(ARAC, encoding="utf-8") as f:
            govde = f.read()
        # Tekil satir: `wrangler_cikti_coz` icindeki basari yuku cozme satiri.
        capa = "    yuk, _, aday = _json_tara(stdout)"
        if govde.count(capa) != 1:
            raise AssertionError(
                "MUTANT CAPASI BAYAT: cozme satiri %d kez gecti (1 bekleniyordu)"
                % govde.count(capa))
        mutant = govde.replace(capa, '    yuk, _, aday = _json_tara("")', 1)

        # ns icin gerekli bagimliliklar (d1-sync modulleri)
        ns = {
            "__name__": "_mutant_",
            "__file__": ARAC,
            "sys": sys,
            "os": os,
            "json": json,
            "argparse": __import__("argparse"),
            "subprocess": __import__("subprocess"),
            "tempfile": __import__("tempfile"),
            "re": __import__("re"),
            "fcntl": __import__("fcntl"),
            "uuid": __import__("uuid"),
            "time": __import__("time"),
            "shutil": shutil,
            "datetime": __import__("datetime").datetime,
            "timedelta": __import__("datetime").timedelta,
            "timezone": __import__("datetime").timezone,
        }
        try:
            exec(mutant, ns)
        except SystemExit:
            pass
        wrangler_coz_mut = ns.get("wrangler_cikti_coz")
        if wrangler_coz_mut is None:
            hata.append("M1 mutant govdesi yuklenemedi (wrangler_cikti_coz bulunamadi)")
        else:
            # Z1 AYNI metin ile mutant uzerinden — sys.exit beklenir (stdout yutuldu).
            try:
                r_mut = wrangler_coz_mut(metin1, "", 0)
                # Mutant BASARILI DONMEMELI (zarf artik bos sayiliyor):
                # ya None/bos doner ya da yanlis sekil. Z1 eslesmesi olmamali.
                if _esle_zarf(r_mut):
                    hata.append("M1 mutant ayni sonucu verdi: r=%r" % (r_mut,))
                else:
                    gecen.append("M1")
            except SystemExit:
                # sys.exit beklenen davranis (bos stdout -> "wrangler cikti vermedi")
                gecen.append("M1")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    z_n = len([g for g in gecen if g.startswith("Z")])
    m_n = len([g for g in gecen if g.startswith("M")])
    for h in hata:
        print("KIRMIZI: %s" % h)
    print("KABUL %d/2 MUTANT %d/1" % (z_n, m_n))
    if hata or z_n != 2 or m_n != 1:
        print("HAL=KIRMIZI")
        return 1
    print("HAL=YESIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())