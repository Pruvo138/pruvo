#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKA SAYFASI DOĞUM testi — dar: /marka/mondial/ GERÇEK katalogda DOĞAR.

OLCULEN SESSIZ HATA (23 Eki): Mondial (6 urun, `marka==["Mondial"]`, Motosiklet) ne
index.html TANINMIS_MARKALAR'da ne cip evreninde (cip-indeks ESIK_MARKA=15) vardi ->
`marka_model_build.uret` /marka/mondial/ sayfasini HIC uretmiyordu. Urun katalogda var,
marka sayfasi 404, kimse gormuyordu. ONARIM (dar): "Mondial" TANINMIS_MARKALAR'a girdi;
sayfa evreni `marka_uyelikleri` -> `evren.taninmis_mi` ile zaten bu listeyi okur, ESIK=3
yeter. Diger /marka/** sayfalari bayt-esit kalir (olculdu, RAPOR'da).

NE OLCER (kopya mantik YOK — GERCEK jenerator gecici ROOT'a uretir, urunler.json'a YAZMAZ):
  D1 — uret() slug_map'inde "Mondial" -> "mondial" VAR, marka/mondial/index.html yazildi.
  D2 — /marka/mondial/** sayfalarindaki kart kumesi == katalogda marka[] katlamasi Mondial
       olan urunlerin kumesi (olculdu: 6) ve >= ESIK.
  MUTANT (her kosumda) — ayni uretim, index.html'den "Mondial" TANINMIS'ten CIKARILMIS
       izole bir kopyayla tekrarlanir; D1 KIRMIZI olmali. Mutant YESIL kalirsa test
       hicbir sey olcmuyordur -> rc=1.
rc=0 hepsi gecti · rc=1 bir madde dustu · rc=2 OLCULEMEDI (import/uretim coktu).
"""
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(KOK, "tools")
HEDEF = "Mondial"
HEDEF_SLUG = "mondial"
KART_RE = re.compile(r'<div class="card" data-kat="[^"]*"><a class="card-main" href="([^"]+)"')
ID_RE = re.compile(r"/urun/([^/]+)/")


def olculemedi(sebep):
    print("OLCULEMEDI: %s" % sebep)
    sys.exit(2)


sys.path.insert(0, TOOLS)
try:
    import build
    _sp = importlib.util.spec_from_file_location("mm_dogum", os.path.join(TOOLS, "marka_model_build.py"))
    mm = importlib.util.module_from_spec(_sp)
    _sp.loader.exec_module(mm)
    with open(os.path.join(KOK, "urunler.json"), encoding="utf-8") as f:
        PRODUCTS = json.load(f)
    with open(os.path.join(KOK, "index.html"), encoding="utf-8") as f:
        INDEX_HTML = f.read()
except Exception as e:                                        # noqa: BLE001
    olculemedi("kurulum coktu: %r" % (e,))


def uret_ve_olc(index_html):
    """index_html ile GERCEK uret() -> (hatalar listesi, mondial kart id kumesi)."""
    tmp = tempfile.mkdtemp(prefix="marka-dogum-")
    try:
        ctx = build.marka_model_ctx()
        ctx["ROOT"] = tmp
        with open(os.path.join(tmp, "index.html"), "w", encoding="utf-8") as f:
            f.write(index_html)
        try:
            sonuc = mm.uret(PRODUCTS, ctx)
        except Exception as e:                                # noqa: BLE001
            olculemedi("uret() coktu: %r" % (e,))
        hatalar = []
        if sonuc.get("slug_map", {}).get(HEDEF) != HEDEF_SLUG:
            hatalar.append("D1 slug_map[%r] = %r (beklenen %r)"
                           % (HEDEF, sonuc.get("slug_map", {}).get(HEDEF), HEDEF_SLUG))
        kok = os.path.join(tmp, "marka", HEDEF_SLUG)
        if not os.path.isfile(os.path.join(kok, "index.html")):
            hatalar.append("D1 marka/%s/index.html URETILMEDI" % HEDEF_SLUG)
        ids = set()
        for d, _a, dosyalar in os.walk(kok):
            for ad in dosyalar:
                if ad != "index.html":
                    continue
                with open(os.path.join(d, ad), encoding="utf-8") as fh:
                    for href in KART_RE.findall(fh.read()):
                        m = ID_RE.search(href)
                        if m:
                            ids.add(m.group(1))
        return hatalar, ids
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


evren = mm.MarkaEvreni(INDEX_HTML)
BEKLENEN = set(p["id"] for p in PRODUCTS if p.get("id")
               and any(evren.katla((x or "").strip()) == HEDEF for x in (p.get("marka") or [])))

hatalar, ids = uret_ve_olc(INDEX_HTML)
if not hatalar:
    if ids != BEKLENEN:
        hatalar.append("D2 kart kumesi sapti: eksik=%s fazla=%s"
                       % (sorted(BEKLENEN - ids), sorted(ids - BEKLENEN)))
    if len(BEKLENEN) < mm.ESIK:
        hatalar.append("D2 katalog %s urunu %d < ESIK %d" % (HEDEF, len(BEKLENEN), mm.ESIK))
print("D1+D2 %s: katalog=%d sayfa=%d hata=%d" % (HEDEF, len(BEKLENEN), len(ids), len(hatalar)))
for h in hatalar:
    print("  KIRMIZI:", h)

# MUTANT: duzeltme geri alinir (TANINMIS'ten "Mondial" cikar) -> D1 KIRMIZI olmali.
blok = re.search(r"var TANINMIS_MARKALAR = \[(.*?)\];", INDEX_HTML, re.S)
if not blok or ('"%s",' % HEDEF) not in blok.group(1):
    hatalar.append("MUTANT kurulamadi: TANINMIS_MARKALAR'da %r yok" % HEDEF)
else:
    mutant_html = (INDEX_HTML[:blok.start(1)] + blok.group(1).replace('"%s",' % HEDEF, "", 1)
                   + INDEX_HTML[blok.end(1):])
    m_hatalar, _m_ids = uret_ve_olc(mutant_html)
    if m_hatalar:
        print("MUTANT (TANINMIS -%s): KIRMIZI (beklenen) — %s" % (HEDEF, m_hatalar[0]))
    else:
        hatalar.append("MUTANT YESIL kaldi — test duzeltmeyi olcmuyor")
        print("MUTANT (TANINMIS -%s): YESIL (BEKLENMEYEN)" % HEDEF)

print("SONUC=%s" % ("GECTI" if not hatalar else "KALDI"))
sys.exit(0 if not hatalar else 1)
