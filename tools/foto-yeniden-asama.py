#!/usr/bin/env python3
"""FOTO YENIDEN ASAMA — 'elle analiz-kirmizi' satirini 'onarim-bekliyor'a deterministik gecis (8 Eki 2026, BaBa).

NEDEN: onarim kapisindan (shop/src/foto.js ONARIM_HAM_BICIM + tools/foto-uretec-kosucu.py onarim kuyrugu)
ONCE sağlayıcı zinciri kirmizi analizde 'elle analiz-kirmizi'ye dusuyordu; o satirlarin saglayici renk 3MF'i
R2'de DURUYOR (ornek: ORNEK-9ba97f662e3f). Yeni zincir (kredi) ACMADAN ayni ciktiyi yerel kopruye vermek icin
tek gecis: ham cikti `model.ham.3mf`e tasinir, `model.3mf` SILINIR (ham dosya asla sunulmaz), satir CAS ile
'onarim-bekliyor'a gecer; gerisini koşucunun onarim kuyrugu yapar. Saglayici cagrisi 0, kredi 0.

KAPI (fail-closed, RED rc 1, hicbir yazim yok): satir yok · asama 'elle' + sebep 'analiz-kirmizi' degil ·
R2'de saglayici ham ciktisi (model.ham.3mf ya da model.3mf) yok · dosya 3MF (zip) degil · CAS tutmadi.
Varsayilan KURU (plan basar). `--uygula` yazar. Yalniz ONIZLEME (canli gecis ayri hukum).

Kullanim: python3 tools/foto-yeniden-asama.py --siparis ORNEK-9ba97f662e3f [--kalem 0] [--uygula]
Son satir: `YENIDEN_ASAMA siparis=<s> kalem=<k> kaynak=<anahtar|-> HAL=<PLAN|TAMAM|RED> sebep=<..> rc=<0|1|2>`
"""
import argparse
import importlib.util
import os
import sys
import tempfile
import shutil

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAM, MODEL = "model.ham.3mf", "model.3mf"


def kosucu():
    sys.dont_write_bytecode = True
    s = importlib.util.spec_from_file_location("foto_kosucu", os.path.join(KOK, "tools", "foto-uretec-kosucu.py"))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--siparis", required=True)
    ap.add_argument("--kalem", type=int, default=0)
    ap.add_argument("--uygula", action="store_true")
    a = ap.parse_args(argv)
    k = kosucu()

    def bitir(hal, sebep, rc, kaynak="-"):
        print("YENIDEN_ASAMA siparis=%s kalem=%d kaynak=%s HAL=%s sebep=%s rc=%d"
              % (a.siparis, a.kalem, kaynak, hal, sebep or "-", rc))
        return rc

    if not k.SIPARIS_KALIBI.match(a.siparis):
        return bitir("RED", "siparis-kalibi", 2)
    k.hedef_kur("onizleme")
    try:
        sat, _ = k.d1("SELECT asama, sebep, guncel FROM foto_uretim WHERE siparis_no = %s AND kalem = %d"
                      % (k.sql_metin(a.siparis), a.kalem))
    except k.Erisilemedi as e:
        return bitir("RED", "olculemedi-%s" % e, 2)
    if not sat:
        return bitir("RED", "satir-yok", 1)
    r = sat[0]
    if r.get("asama") != "elle" or r.get("sebep") != "analiz-kirmizi":
        return bitir("RED", "asama-uygun-degil:%s/%s" % (r.get("asama"), r.get("sebep")), 1)
    d = "foto/%s/%d/" % (a.siparis, a.kalem)
    gecici = tempfile.mkdtemp(prefix="foto-yeniden-asama-")
    try:
        yol = os.path.join(gecici, "ham.3mf")
        kaynak = None
        for ad in (HAM, MODEL):
            if k.r2_al(d + ad, yol):
                kaynak = ad
                break
        if not kaynak:
            return bitir("RED", "ham-cikti-yok", 1)
        with open(yol, "rb") as f:
            if f.read(4) != b"PK\x03\x04":
                return bitir("RED", "ham-3mf-degil", 1, kaynak)
        if not a.uygula:
            print("PLAN R2 %s%s -> %s%s ; R2 SIL %s%s ; D1 asama elle -> onarim-bekliyor (CAS guncel=%s)"
                  % (d, kaynak, d, HAM, d, MODEL, r.get("guncel")))
            return bitir("PLAN", "", 0, kaynak)
        if kaynak == MODEL:
            k.r2_koy(d + HAM, yol, "model/3mf")
        k.wr(["r2", "object", "delete", k.R2_KOVA + "/" + d + MODEL, "--remote"])
        if k.r2_al(d + MODEL, os.path.join(gecici, "kontrol.3mf")):
            return bitir("RED", "model-silinemedi", 1, kaynak)
        _, n = k.d1("UPDATE foto_uretim SET asama = 'onarim-bekliyor', sebep = '', deneme = 0, guncel = %s"
                    " WHERE siparis_no = %s AND kalem = %d AND asama = 'elle' AND guncel = %s"
                    % (k.sql_metin(k.simdi_iso()), k.sql_metin(a.siparis), a.kalem, k.sql_metin(r.get("guncel"))))
        if n != 1:
            return bitir("RED", "cas", 1, kaynak)
        return bitir("TAMAM", "", 0, kaynak)
    except k.Erisilemedi as e:
        return bitir("RED", "olculemedi-%s" % e, 2)
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
