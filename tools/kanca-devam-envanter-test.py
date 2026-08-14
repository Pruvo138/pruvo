#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-commit DEVAM sinif kapisinin iki nobetci envanterindeki kabul testi."""
import importlib.util
import os
import sys


TOOLS = os.path.dirname(os.path.abspath(__file__))
HEDEF = "tools/devam-sinif-kapisi.py"
CIFT = ("pre-commit", HEDEF)
KANCA = os.path.join(TOOLS, "kancalar", "pre-commit")


def yukle(ad, dosya):
    yol = os.path.join(TOOLS, dosya)
    spec = importlib.util.spec_from_file_location(ad, yol)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[ad] = modul
    spec.loader.exec_module(modul)
    return modul


def sonuc(ad, gecti, ayrinti):
    print("%s %s — %s" % ("OK" if gecti else "HATA", ad, ayrinti))
    return gecti


def main():
    try:
        nobet = yukle("k69_kanca_nobeti", "kanca-nobeti.py")
        kablo = yukle("k69_kanca_kablolama", "kanca-kablolama-nobeti.py")
        suzgec = nobet.suzgec_yukle()
        with open(KANCA, encoding="utf-8", errors="replace") as f:
            govde = f.read()
    except Exception as e:
        print("HATA kurulum — %s: %s" % (type(e).__name__, e))
        return 1

    beklenen = {
        (kanca, arac)
        for kanca, araclar in nobet.BEKLENEN
        for arac, _gerekce in araclar
    }
    politika = set(kablo.FAIL_CLOSED) | set(kablo.FAIL_OPEN)
    kontroller = []
    kontroller.append(sonuc(
        "BEKLENEN",
        CIFT in beklenen,
        "%s %s" % (CIFT, "VAR" if CIFT in beklenen else "YOK")))
    kontroller.append(sonuc(
        "FAIL_CLOSED",
        CIFT in kablo.FAIL_CLOSED and CIFT not in kablo.FAIL_OPEN,
        "%s closed=%s open=%s" %
        (CIFT, CIFT in kablo.FAIL_CLOSED, CIFT in kablo.FAIL_OPEN)))
    kontroller.append(sonuc(
        "ENVANTER_PARITESI",
        CIFT in beklenen and CIFT in politika,
        "iki envanterde birlikte kayitli olmali"))

    h_nobet, _tani = nobet.cagri_hukmu(govde, HEDEF, suzgec)
    indeks, satir, ham, etkili = kablo._cagri_satiri(nobet, suzgec, govde, HEDEF)
    saglikli_kablo = False
    if indeks is not None:
        yutuyor, _ = kablo.yutma_hukmu(satir)
        bloklu, _ = kablo.bloklama_hukmu(etkili, indeks, ham)
        saglikli_kablo = not yutuyor and bloklu
    kontroller.append(sonuc(
        "SAGLIKLI_GOVDE",
        h_nobet == nobet.YESIL and saglikli_kablo,
        "nobet=%s kablolama=%s" % (h_nobet, "YESIL" if saglikli_kablo else "KIRMIZI")))

    mutant_satir = 'python3 "$pruvo_devam" --index'
    eslesme = govde.count(mutant_satir)
    mutant = govde.replace(mutant_satir, "", 1)
    h_mutant, _tani = nobet.cagri_hukmu(mutant, HEDEF, suzgec)
    mutant_indeks, _s, _h, _e = kablo._cagri_satiri(nobet, suzgec, mutant, HEDEF)
    kontroller.append(sonuc(
        "CAGRI_SILME_MUTANTI",
        eslesme == 1 and h_mutant == nobet.KIRMIZI and mutant_indeks is None,
        "eslesme=%d nobet=%s kablolama=%s" %
        (eslesme, h_mutant, "KIRMIZI" if mutant_indeks is None else "YESIL")))

    print("SONUC: %s (%d/%d)" %
          ("YESIL" if all(kontroller) else "KIRMIZI", sum(kontroller), len(kontroller)))
    return 0 if all(kontroller) else 1


if __name__ == "__main__":
    raise SystemExit(main())
