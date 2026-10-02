#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenSCAD derleme ciktisindan KOK NEDEN tanisi — kutuphane (include/use) eksik mi.

Modul olarak: openscad_tani.kutuphane_tanisi(metin) -> "KUTUPHANE-EKSIK: <satir>" | None

🔴 NEDEN VAR (K427, 2 Eki 2026 — OLCULDU, kosum 36929560645): CI'da BOSL2 kurulu
degildi. OpenSCAD eksik include'u HATA degil UYARI sayar ("WARNING: Can't find
include file ...", ardindan "Ignoring unknown module ..."), bos geometriyle devam
eder ve SON satir olarak yalniz "Current top level object is empty." basar. Sonuc:
  * onizleme/test/eslem-olcum.py son satiri tani diye bastigi icin 9 `motor: uretim`
    aile haftalarca "top level object is empty" ile kirmizi yandi, asil neden
    (kutuphane yok) satirlarin ARASINDA gomulu kaldi;
  * jenerator/test/dogrula.py (motor=pruvo) ayni durumu "openscad cokuyor" sanip
    3 kez yeniden denedi ve aileyi `[ATLA]` ile GECTI — `[ATLA]` cikis kodunu
    kirmizi yapmadigi icin bu yol fail-open idi (cerceve/disli/yay).
Bu modul TEK KAYNAKTIR: iki arac da desen listesini buradan okur (ikinci kopya yok).
Yalniz derleme BASARISIZ oldugunda cagrilir; basarili render'daki uyari etiketlenmez.
"""

# OpenSCAD'in eksik kutuphane/tanimsiz modul icin bastigi ifadeler (surumler arasi
# yazim farki: "Can't find" / "Can't open"). Kucuk/buyuk harf duyarsiz aranir.
KUTUPHANE_DESENLERI = (
    "can't find include file",
    "can't open include file",
    "can't open library",
    "ignoring unknown module",
    "ignoring unknown function",
)

TANI_JETONU = "KUTUPHANE-EKSIK"


def kutuphane_tanisi(metin):
    """Derleme ciktisinda (stderr+stdout BIRLIKTE verilmeli: xvfb-run sarmalayicisi
    akislari birlestirebilir) eksik kutuphane izi varsa ILK eslesen satirla
    "KUTUPHANE-EKSIK: <satir>" dondur; yoksa None."""
    if not metin:
        return None
    for satir in metin.splitlines():
        kucuk = satir.lower()
        if any(d in kucuk for d in KUTUPHANE_DESENLERI):
            return "%s: %s" % (TANI_JETONU, satir.strip()[:160])
    return None


def kendini_test_vakalari():
    """(ad, kosul, detay) listesi — dogrula.py ve eslem-olcum.py --kendini-test'i
    bunlari kendi vakalarina EKLER (bu modulun ayri bir CI cagrisi yoktur; menzili
    o iki cagri yeridir). POZITIF ve NEGATIF yon ayri."""
    v = []
    t = kutuphane_tanisi(
        "WARNING: Can't find include file 'BOSL2/std.scad'.\n"
        "WARNING: Ignoring unknown module 'xrot' in file x.scad, line 3\n"
        "Current top level object is empty.\n")
    v.append(("T1 POZITIF: eksik include -> KUTUPHANE-EKSIK (ilk satir)",
              t is not None and t.startswith(TANI_JETONU + ":") and "BOSL2/std.scad" in t,
              repr(t)))
    t = kutuphane_tanisi("WARNING: Ignoring unknown module 'cuboid' in file a.scad\n"
                         "Current top level object is empty.")
    v.append(("T2 POZITIF: yalniz tanimsiz modul -> KUTUPHANE-EKSIK",
              t is not None and "cuboid" in t, repr(t)))
    t = kutuphane_tanisi("WARNING: Can't open library 'BOSL2/gears.scad'.")
    v.append(("T3 POZITIF: use<> kutuphanesi acilamadi -> KUTUPHANE-EKSIK",
              t is not None and "gears.scad" in t, repr(t)))
    t = kutuphane_tanisi("Current top level object is empty.\n")
    v.append(("T4 NEGATIF: yalniz bos geometri -> etiket YOK", t is None, repr(t)))
    t = kutuphane_tanisi("ERROR: Assertion '(w > 0)' failed in file x.scad\n")
    v.append(("T5 NEGATIF: assert (422 sinifi) -> etiket YOK", t is None, repr(t)))
    v.append(("T6 NEGATIF: bos cikti -> etiket YOK", kutuphane_tanisi("") is None, ""))
    return v


def main():
    """`python3 openscad_tani.py --kendini-test` — desen vakalarini tek basina kosar
    (CI: nobet.yml serit-b). Ag/OpenSCAD ISTEMEZ. rc 0 = hepsi yesil, 1 = kirmizi."""
    import sys
    if sys.argv[1:] != ["--kendini-test"]:
        print("kullanim: python3 openscad_tani.py --kendini-test", file=sys.stderr)
        return 2
    vakalar = kendini_test_vakalari()
    kirmizi = [x for x in vakalar if not x[1]]
    print("OPENSCAD KUTUPHANE TANISI — %d/%d YESIL" % (len(vakalar) - len(kirmizi), len(vakalar)))
    for ad, yesil, detay in vakalar:
        print("  %s %-58s %s" % ("+" if yesil else "-", ad, "" if yesil else detay))
    return 1 if kirmizi else 0


if __name__ == "__main__":
    raise SystemExit(main())
