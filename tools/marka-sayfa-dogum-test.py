#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKA SAYFASI DOĞUM testi — HEDEFLER'deki her marka için /marka/<slug>/ GERÇEK katalogda DOĞAR.

OLCULEN SESSIZ HATA (23 Eki): Mondial (6 urun, `marka==["Mondial"]`, Motosiklet) ne
index.html TANINMIS_MARKALAR'da ne cip evreninde (cip-indeks ESIK_MARKA=15) vardi ->
`marka_model_build.uret` /marka/mondial/ sayfasini HIC uretmiyordu. Urun katalogda var,
marka sayfasi 404, kimse gormuyordu. ONARIM (dar): "Mondial" TANINMIS_MARKALAR'a girdi;
sayfa evreni `marka_uyelikleri` -> `evren.taninmis_mi` ile zaten bu listeyi okur, ESIK=3
yeter. Diger /marka/** sayfalari bayt-esit kalir (olculdu, RAPOR'da).
AYNI SINIF (25 Eki): /marka/{zontes,keeway,bajaj,sym}/ 404 (MaCiT 24 Eki ekleri) -> ayni
onarim; test tek hedeften HEDEFLER listesine genellestirildi. TVS (1 urun < ESIK 3)
TANINMIS'te ama sayfa dogmaz -> HEDEF DEGIL (urun ESIK'e ulasinca listeye eklenir).
MV Agusta (25 Eki, MaCiT 5 urun ekledi): yayin sonrasi /marka/mv-agusta/ 404 olculdu -> 6. hedef.

NE OLCER (kopya mantik YOK — GERCEK jenerator gecici ROOT'a uretir, urunler.json'a YAZMAZ):
  D1 — her hedef icin uret() slug_map'inde marka -> slug VAR, marka/<slug>/index.html yazildi.
  D2 — her hedef icin /marka/<slug>/** kart kumesi == katalogda marka[] katlamasi o marka
       olan urunlerin kumesi ve >= ESIK.
  MUTANT (her kosumda, HER HEDEFE AYRI) — ayni uretim, index.html'den YALNIZ o marka
       TANINMIS'ten CIKARILMIS izole bir kopyayla tekrarlanir; o hedefin D1'i KIRMIZI
       olmali. Bir mutant YESIL kalirsa test o hedefi olcmuyordur -> rc=1.
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
HEDEFLER = [("Mondial", "mondial"), ("Zontes", "zontes"), ("Keeway", "keeway"),
            ("Bajaj", "bajaj"), ("SYM", "sym"), ("MV Agusta", "mv-agusta"),
            # TANINMIS PARTI 1 (25 Eki)
            ("Olympus", "olympus"), ("Pentax", "pentax"), ("Blackmagic", "blackmagic"),
            ("Leica", "leica"), ("Insta360", "insta360"), ("SsangYong", "ssangyong"),
            ("BYD", "byd"),
            # Indian (25 Eki; MaCiT `009065d8` kanon `Indian`, 14 urun)
            ("Indian", "indian")]
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


def uret_ve_olc(index_html, hedefler):
    """index_html ile GERCEK uret() -> {marka: (hatalar listesi, kart id kumesi)}."""
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
        olcum = {}
        for hedef, slug in hedefler:
            hatalar = []
            if sonuc.get("slug_map", {}).get(hedef) != slug:
                hatalar.append("D1 slug_map[%r] = %r (beklenen %r)"
                               % (hedef, sonuc.get("slug_map", {}).get(hedef), slug))
            kok = os.path.join(tmp, "marka", slug)
            if not os.path.isfile(os.path.join(kok, "index.html")):
                hatalar.append("D1 marka/%s/index.html URETILMEDI" % slug)
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
            olcum[hedef] = (hatalar, ids)
        return olcum
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


evren = mm.MarkaEvreni(INDEX_HTML)
# Sayfa uyeligi = marka[] katlamasi (birincil) ∪ BASLIK uyeligi (ikincil, FAZ 1B — ana sayfa
# filtresiyle ayni yuklem). 25 Eki: "Ducati / MV Agusta Arka Tekerlek Somunu" (marka=["Ducati"])
# /marka/mv-agusta/'da DOGRU olarak duruyordu, yalniz marka[]'ya bakan beklenti onu "fazla"
# sayiyordu. Ikincil kol jeneratorun KENDI fonksiyonlariyla kurulur (kopya mantik YOK).
EK_MARKALAR = mm.cip_evreni_markalari(PRODUCTS, INDEX_HTML)
AD_KANONU, AZAMI_AD = mm.baslik_uyelik_hazirlik(
    sorted(mm.gruplandir(PRODUCTS, evren, EK_MARKALAR)), evren)

hatalar = []
olcum = uret_ve_olc(INDEX_HTML, HEDEFLER)
for hedef, _slug in HEDEFLER:
    h_hatalar, ids = olcum[hedef]
    beklenen = set(p["id"] for p in PRODUCTS if p.get("id") and (
        any(evren.katla((x or "").strip()) == hedef for x in (p.get("marka") or []))
        or hedef in mm.baslik_uyelikleri(p, evren, AD_KANONU, AZAMI_AD, EK_MARKALAR)))
    if not h_hatalar:
        if ids != beklenen:
            h_hatalar.append("D2 kart kumesi sapti: eksik=%s fazla=%s"
                             % (sorted(beklenen - ids), sorted(ids - beklenen)))
        if len(beklenen) < mm.ESIK:
            h_hatalar.append("D2 katalog %s urunu %d < ESIK %d" % (hedef, len(beklenen), mm.ESIK))
    print("D1+D2 %s: katalog=%d sayfa=%d hata=%d" % (hedef, len(beklenen), len(ids), len(h_hatalar)))
    for h in h_hatalar:
        print("  KIRMIZI:", h)
    hatalar.extend(h_hatalar)

# MUTANT (hedef basina): duzeltme geri alinir (TANINMIS'ten YALNIZ o marka cikar) -> o hedefin D1'i KIRMIZI olmali.
blok = re.search(r"var TANINMIS_MARKALAR = \[(.*?)\];", INDEX_HTML, re.S)
for hedef, slug in HEDEFLER:
    if not blok or ('"%s",' % hedef) not in blok.group(1):
        hatalar.append("MUTANT kurulamadi: TANINMIS_MARKALAR'da %r yok" % hedef)
        print("MUTANT (TANINMIS -%s): KURULAMADI" % hedef)
        continue
    mutant_html = (INDEX_HTML[:blok.start(1)] + blok.group(1).replace('"%s",' % hedef, "", 1)
                   + INDEX_HTML[blok.end(1):])
    m_hatalar, _m_ids = uret_ve_olc(mutant_html, [(hedef, slug)])[hedef]
    if m_hatalar:
        print("MUTANT (TANINMIS -%s): KIRMIZI (beklenen) — %s" % (hedef, m_hatalar[0]))
    else:
        hatalar.append("MUTANT YESIL kaldi — test %s duzeltmesini olcmuyor" % hedef)
        print("MUTANT (TANINMIS -%s): YESIL (BEKLENMEYEN)" % hedef)

print("SONUC=%s" % ("GECTI" if not hatalar else "KALDI"))
sys.exit(0 if not hatalar else 1)
