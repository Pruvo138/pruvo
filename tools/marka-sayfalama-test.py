#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKA HUB SAYFALAMA kabul testi — sentetik veri + bellek-içi mutasyon bataryası.

ÖLÇTÜĞÜ İDDİA (spec dilim-4): /marka/<slug>/ kökü ilk MARKA_KART_N ürünü TAM KART basar,
kalanı /marka/<slug>/<N>/ devam sayfalarına böler. Her ürün en az bir statik hub sayfasında
HAM HTML'de görünür; kök adres DEĞİŞMEZ; her sayfa KENDİ canonical'ını taşır; rel=prev/next
zinciri kurulur; üretilen HER sayfa sitemap'e girer.

TAM katalogla lokalde KOŞMAZ (yasak) — build.marka_model_ctx() + SENTETİK ürünlerle koşar.
Mutant (T8) diske YAZILMAZ, bellekte kurulur.
"""
import ast
import os
import re
import shutil
import sys
import tempfile
import types

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)

import build                                                    # noqa: E402
import marka_model_build as mm                                   # noqa: E402

MM_PATH = os.path.join(TOOLS, "marka_model_build.py")
SITE = build.SITE

KART_RE = re.compile(r'<a class="card-main" href="' + re.escape(SITE) + r'/urun/([^/"]+)/"')
CANON_RE = re.compile(r'<link rel="canonical" href="([^"]+)">')
PREV_RE = re.compile(r'<link rel="prev" href="([^"]+)">')
NEXT_RE = re.compile(r'<link rel="next" href="([^"]+)">')
SAYFA_NAV_RE = re.compile(r'<nav class="mm-sayfa"[^>]*>')

SLUG = "ford"


def urun(no):
    return {"id": "ford-test-%05d" % no, "kategori": "Otomobil", "marka": ["Ford"],
            "baslik": "Ford test parçası %d" % no, "fiyat": "10 TL", "gorseller": []}


def katalog(n):
    return [urun(i) for i in range(n)]


def kos(mm_modul, products):
    """Geçici ROOT'ta mm_modul.uret koşar; (tmp, sonuc) döner. tmp çağıran tarafından silinir."""
    tmp = tempfile.mkdtemp(prefix="mm-sayfalama-")
    ctx = build.marka_model_ctx()
    ctx["ROOT"] = tmp
    with open(os.path.join(build.ROOT, "index.html"), encoding="utf-8") as f:
        index_html = f.read()
    with open(os.path.join(tmp, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    sonuc = mm_modul.uret(products, ctx)
    return tmp, sonuc


def sayfa_yolu(tmp, sayfa):
    """Sayfa 1 = kök /marka/ford/index.html; N>=2 = /marka/ford/<N>/index.html."""
    if sayfa == 1:
        return os.path.join(tmp, "marka", SLUG, "index.html")
    return os.path.join(tmp, "marka", SLUG, str(sayfa), "index.html")


def sayfa_okur(tmp, sayfa):
    with open(sayfa_yolu(tmp, sayfa), encoding="utf-8") as f:
        return f.read()


def kart_ids(html):
    return KART_RE.findall(html)


def kapsama(tmp, toplam):
    """(tam, mukerrer_yok, gorulen_set): kartların sayfalar arası TAM ve TEKİL kapsaması."""
    sayfa_sayisi = mm._marka_sayfa_sayisi(toplam)
    gorulen = []
    for n in range(1, sayfa_sayisi + 1):
        gorulen.extend(kart_ids(sayfa_okur(tmp, n)))
    beklenen = {"ford-test-%05d" % i for i in range(toplam)}
    return set(gorulen) == beklenen, len(gorulen) == len(set(gorulen)), set(gorulen)


def mutant_modul_yukle():
    """Dilimlemeyi ESKİ hale (`[:80]` her sayfaya aynı ilk 80) döndüren bellek-içi mutant."""
    with open(MM_PATH, encoding="utf-8") as f:
        kaynak = f.read()
    agac = ast.parse(kaynak)
    dugum = next(x for x in agac.body
                 if isinstance(x, ast.FunctionDef) and x.name == "_marka_sayfa_dilimi")
    satirlar = kaynak.splitlines(keepends=True)
    mutant = (
        "def _marka_sayfa_dilimi(kalemler, sayfa):\n"
        "    return kalemler[:MARKA_KART_N]\n"
    )
    mutant_kaynak = "".join(satirlar[:dugum.lineno - 1])
    mutant_kaynak += mutant
    mutant_kaynak += "".join(satirlar[dugum.end_lineno:])
    mod = types.ModuleType("pruvo_mm_sayfalama_mutant")
    mod.__file__ = MM_PATH
    mod.__package__ = ""
    sys.modules["pruvo_mm_sayfalama_mutant"] = mod
    exec(compile(mutant_kaynak, MM_PATH, "exec"), mod.__dict__)
    return mod


def main():
    dusen = []
    tmp_listesi = []

    def kaydet(ad, kosul, detay=""):
        if kosul:
            print("  GECTI %s" % ad)
        else:
            dusen.append(ad + ((" — " + detay) if detay else ""))
            print("  DUSEN %s%s" % (ad, (" — " + detay) if detay else ""))

    try:
        # ---- T1: 80 ürünlü marka -> TEK sayfa, gezinme/next YOK
        t1_tmp, _ = kos(mm, katalog(80))
        tmp_listesi.append(t1_tmp)
        t1_html = sayfa_okur(t1_tmp, 1)
        kaydet("T1", (
            not os.path.exists(sayfa_yolu(t1_tmp, 2))
            and NEXT_RE.search(t1_html) is None
            and SAYFA_NAV_RE.search(t1_html) is None
            and len(kart_ids(t1_html)) == 80),
            "tek sayfa/gezinme yok şartı bozuldu")

        # ---- T2: 81 ürünlü marka -> 2 sayfa; sayfa1=80 kart, sayfa2=1 kart
        t2_tmp, _ = kos(mm, katalog(81))
        tmp_listesi.append(t2_tmp)
        t2_p1 = sayfa_okur(t2_tmp, 1)
        t2_p2 = sayfa_okur(t2_tmp, 2)
        kaydet("T2", (
            len(kart_ids(t2_p1)) == 80 and len(kart_ids(t2_p2)) == 1
            and os.path.exists(sayfa_yolu(t2_tmp, 2))),
            "80+1 bölünme yok")

        # ---- T3: 2584 ürünlü marka -> ceil(2584/80)=33 sayfa
        N_BOYUT = 2584
        t3_tmp, t3_sonuc = kos(mm, katalog(N_BOYUT))
        tmp_listesi.append(t3_tmp)
        beklenen_sayfa = mm._marka_sayfa_sayisi(N_BOYUT)
        t3_ok = (beklenen_sayfa == 33
                 and all(os.path.exists(sayfa_yolu(t3_tmp, n))
                         for n in range(1, beklenen_sayfa + 1))
                 and not os.path.exists(sayfa_yolu(t3_tmp, beklenen_sayfa + 1)))
        kaydet("T3", t3_ok, "beklenen sayfa %d" % beklenen_sayfa)

        # ---- T4 KAPSAMA: TÜM ürünler sayfaların ham HTML'inde, TEKİL ve EKSİKSİZ
        tam, mukerrer_yok, _ = kapsama(t3_tmp, N_BOYUT)
        kaydet("T4", tam and mukerrer_yok, "tam=%s mukerrer_yok=%s" % (tam, mukerrer_yok))

        # ---- T5 KANONİK: sayfa1=/marka/ford/, sayfa2=/marka/ford/2/
        t5_c1 = CANON_RE.search(t2_p1)
        t5_c2 = CANON_RE.search(t2_p2)
        kaydet("T5", (
            t5_c1 is not None and t5_c1.group(1) == SITE + "/marka/" + SLUG + "/"
            and t5_c2 is not None and t5_c2.group(1) == SITE + "/marka/" + SLUG + "/2/"),
            "sayfa2 kendini sayfa1 kanoniği yapmamalı")

        # ---- T6 ZİNCİR: sayfa1 next=2 · sayfa2 prev=1,next=3 · son sayfa next YOK
        t6_p1 = sayfa_okur(t3_tmp, 1)
        t6_p2 = sayfa_okur(t3_tmp, 2)
        t6_son = sayfa_okur(t3_tmp, beklenen_sayfa)
        t6_n1 = NEXT_RE.search(t6_p1)
        t6_p2_prev = PREV_RE.search(t6_p2)
        t6_p2_next = NEXT_RE.search(t6_p2)
        kaydet("T6", (
            PREV_RE.search(t6_p1) is None
            and t6_n1 is not None and t6_n1.group(1) == SITE + "/marka/" + SLUG + "/2/"
            and t6_p2_prev is not None and t6_p2_prev.group(1) == SITE + "/marka/" + SLUG + "/"
            and t6_p2_next is not None and t6_p2_next.group(1) == SITE + "/marka/" + SLUG + "/3/"
            and NEXT_RE.search(t6_son) is None),
            "prev/next zinciri bozuk")

        # ---- T7 SITEMAP: üretilen sayfa sayısı kadar kayıt (33 sayfalık markada 33)
        sitemap_sayfalari = t3_sonuc.get("sitemap_sayfalari", [])
        marka_kayit = [url for sinif, url in sitemap_sayfalari
                       if sinif in ("marka", "marka_sayfa")]
        kaydet("T7", len(marka_kayit) == beklenen_sayfa,
               "marka kaydı %d != %d" % (len(marka_kayit), beklenen_sayfa))

        # ---- T8 MUTANT: dilimleme `[:80]`e dönerse T4 (kapsama) DÜŞMELİ
        mutant = mutant_modul_yukle()
        t8_tmp, _ = kos(mutant, katalog(N_BOYUT))
        tmp_listesi.append(t8_tmp)
        m_tam, m_mukerrer, m_gorulen = kapsama(t8_tmp, N_BOYUT)
        kaydet("T8", (not m_tam) and len(m_gorulen) < N_BOYUT,
               "mutant kapsamayı düşürmedi (tam=%s tekilsayı=%d)"
               % (m_tam, len(m_gorulen)))
    finally:
        for t in tmp_listesi:
            shutil.rmtree(t, ignore_errors=True)

    print("VAKA=8 DUSEN=%d" % len(dusen))
    return 1 if dusen else 0


if __name__ == "__main__":
    raise SystemExit(main())
