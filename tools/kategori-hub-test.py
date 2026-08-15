#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KATEGORİ HUB kabul testi — sentetik veri + bellek-içi mutasyon bataryası.

ÖLÇTÜĞÜ İDDİA (spec dilim-5): /kategori/<slug>/ kökü ilk MARKA_KART_N ürünü TAM KART basar,
kalanı /kategori/<slug>/sayfa/<N>/ devam sayfalarına böler. Her ürün — `marka` alanı BOŞ
olanlar DAHİL — statik hub sayfalarının HAM HTML'inde TEKİL ve EKSİKSİZ görünür; her sayfa
kendi canonical'ını taşır; rel=prev/next zinciri kurulur; kategori adı güvenli ASCII slug
üretir (^[a-z0-9-]+$, eğik çizgi yok, çakışma yok); ürün sayfası breadcrumb'ı hub'a
bağlanır; gizli kategoriler (Jeneratör, Skan Art) için de hub üretilir. Sayfa N>=2 `sayfa`
AYRIK isim alanında (mm.SAYFA_AYIRAC) — sayısal model slug'larıyla çakışma ölçüldü
(15 Ağu).

TAM katalogla lokalde KOŞMAZ (yasak) — build.marka_model_ctx() + SENTETİK ürünlerle koşar.
Mutant (T9) diske YAZILMAZ, bellekte kurulur.
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
import kategori_hub_build as kb                                  # noqa: E402
import marka_model_build as mm                                   # noqa: E402

KB_PATH = os.path.join(TOOLS, "kategori_hub_build.py")
SITE = build.SITE

KART_RE = re.compile(r'<a class="card-main" href="' + re.escape(SITE) + r'/urun/([^/"]+)/"')
CANON_RE = re.compile(r'<link rel="canonical" href="([^"]+)">')
PREV_RE = re.compile(r'<link rel="prev" href="([^"]+)">')
NEXT_RE = re.compile(r'<link rel="next" href="([^"]+)">')
SAYFA_NAV_RE = re.compile(r'<nav class="mm-sayfa"[^>]*>')

SLUG = "otomobil"
N_BOYUT = 2584                       # çok sayfalı kapsama fikstürü


def urun(no, kategori="Otomobil", marka=None):
    return {"id": "kat-test-%05d" % no, "kategori": kategori, "marka": list(marka or []),
            "baslik": "Kategori test parçası %d" % no, "fiyat": "10 TL", "gorseller": []}


def katalog(n):
    return [urun(i) for i in range(n)]


def kos(kb_modul, products, kategori_evreni):
    """Geçici ROOT'ta kb_modul.uret koşar; (tmp, sonuc) döner. tmp çağıran tarafından silinir."""
    tmp = tempfile.mkdtemp(prefix="kat-hub-")
    ctx = build.marka_model_ctx()
    ctx["ROOT"] = tmp
    ctx["kategori_evreni"] = kategori_evreni
    sonuc = kb_modul.uret(products, ctx)
    return tmp, sonuc


def sayfa_yolu(tmp, slug, sayfa):
    """Sayfa 1 = kök /kategori/<slug>/index.html; N>=2 = /kategori/<slug>/sayfa/<N>/index.html.
    `sayfa` AYRIK İSİM ALANI (mm.SAYFA_AYIRAC) — marka hub'ıyla AYNI şema (TEK KAYNAK)."""
    if sayfa == 1:
        return os.path.join(tmp, "kategori", slug, "index.html")
    return os.path.join(tmp, "kategori", slug, mm.SAYFA_AYIRAC, str(sayfa), "index.html")


def sayfa_okur(tmp, slug, sayfa):
    with open(sayfa_yolu(tmp, slug, sayfa), encoding="utf-8") as f:
        return f.read()


def kart_ids(html):
    return KART_RE.findall(html)


def kapsama(tmp, slug, toplam):
    """(tam, mukerrer_yok, gorulen_set): kartların sayfalar arası TAM ve TEKİL kapsaması."""
    sayfa_sayisi = kb._kategori_sayfa_sayisi(toplam)
    gorulen = []
    for n in range(1, sayfa_sayisi + 1):
        gorulen.extend(kart_ids(sayfa_okur(tmp, slug, n)))
    beklenen = {"kat-test-%05d" % i for i in range(toplam)}
    return set(gorulen) == beklenen, len(gorulen) == len(set(gorulen)), set(gorulen)


def mutant_modul_yukle():
    """Dilimlemeyi "her sayfaya aynı ilk 80" haline döndüren bellek-içi mutant."""
    with open(KB_PATH, encoding="utf-8") as f:
        kaynak = f.read()
    agac = ast.parse(kaynak)
    dugum = next(x for x in agac.body
                 if isinstance(x, ast.FunctionDef) and x.name == "_kategori_sayfa_dilimi")
    satirlar = kaynak.splitlines(keepends=True)
    mutant = (
        "def _kategori_sayfa_dilimi(kalemler, sayfa):\n"
        "    return kalemler[:mm.MARKA_KART_N]\n"
    )
    mutant_kaynak = "".join(satirlar[:dugum.lineno - 1])
    mutant_kaynak += mutant
    mutant_kaynak += "".join(satirlar[dugum.end_lineno:])
    mod = types.ModuleType("pruvo_kb_sayfalama_mutant")
    mod.__file__ = KB_PATH
    mod.__package__ = ""
    sys.modules["pruvo_kb_sayfalama_mutant"] = mod
    exec(compile(mutant_kaynak, KB_PATH, "exec"), mod.__dict__)
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
        # ---- T1: 80 ürünlü kategori -> TEK sayfa, gezinme/next YOK
        t1_tmp, _ = kos(kb, katalog(80), ["Otomobil"])
        tmp_listesi.append(t1_tmp)
        t1_html = sayfa_okur(t1_tmp, SLUG, 1)
        kaydet("T1", (
            not os.path.exists(sayfa_yolu(t1_tmp, SLUG, 2))
            and NEXT_RE.search(t1_html) is None
            and SAYFA_NAV_RE.search(t1_html) is None
            and len(kart_ids(t1_html)) == 80),
            "tek sayfa/gezinme yok şartı bozuldu")

        # ---- T2: 81 ürünlü kategori -> 2 sayfa; sayfa1=80 kart, sayfa2=1 kart
        t2_tmp, _ = kos(kb, katalog(81), ["Otomobil"])
        tmp_listesi.append(t2_tmp)
        t2_p1 = sayfa_okur(t2_tmp, SLUG, 1)
        t2_p2 = sayfa_okur(t2_tmp, SLUG, 2)
        kaydet("T2", (
            len(kart_ids(t2_p1)) == 80 and len(kart_ids(t2_p2)) == 1
            and os.path.exists(sayfa_yolu(t2_tmp, SLUG, 2))),
            "80+1 bölünme yok")

        # ---- T3 KAPSAMA (asıl iddia): TÜM ürünler sayfalarda TEKİL ve EKSİKSİZ
        t3_tmp, t3_sonuc = kos(kb, katalog(N_BOYUT), ["Otomobil"])
        tmp_listesi.append(t3_tmp)
        beklenen_sayfa = kb._kategori_sayfa_sayisi(N_BOYUT)
        tam, mukerrer_yok, _ = kapsama(t3_tmp, SLUG, N_BOYUT)
        kaydet("T3", (
            beklenen_sayfa == 33
            and all(os.path.exists(sayfa_yolu(t3_tmp, SLUG, n))
                    for n in range(1, beklenen_sayfa + 1))
            and not os.path.exists(sayfa_yolu(t3_tmp, SLUG, beklenen_sayfa + 1))
            and tam and mukerrer_yok),
            "tam=%s mukerrer_yok=%s sayfa=%d" % (tam, mukerrer_yok, beklenen_sayfa))

        # ---- T4 MARKASIZ: marka alanı boş ürünler de hub'da görünür (bu dilimin varlık sebebi)
        t4_urunler = katalog(5)
        t4_urunler.append({"id": "kat-marksiz-1", "kategori": "Otomobil", "marka": [],
                           "baslik": "Markasız test parçası", "fiyat": "10 TL",
                           "gorseller": []})
        t4_tmp, _ = kos(kb, t4_urunler, ["Otomobil"])
        tmp_listesi.append(t4_tmp)
        t4_html = sayfa_okur(t4_tmp, SLUG, 1)
        kaydet("T4", "kat-marksiz-1" in kart_ids(t4_html),
               "marka alanı boş ürün hub kartlarında yok")

        # ---- T5 SLUG: güvenli ASCII, eğik çizgi yok, çakışma yok
        slug_ciftleri = [("Oyun/Hobi", "oyun-hobi"), ("Jeneratör", "olcuye-ozel-uretim"),
                         ("Skan Art", "skan-art"), ("Bahçe", "bahce")]
        guvenli = all(re.fullmatch(r"[a-z0-9-]+", build.kategori_slug(ad)) is not None
                      and "/" not in build.kategori_slug(ad)
                      for ad, _bek in slug_ciftleri)
        dogru = all(build.kategori_slug(ad) == bek for ad, bek in slug_ciftleri)
        tum_kategoriler = build.CATEGORIES + build.NAV_GIZLI
        sluglar = [build.kategori_slug(k) for k in tum_kategoriler]
        cakisma_yok = len(sluglar) == len(set(sluglar)) and all(sluglar)
        kaydet("T5", guvenli and dogru and cakisma_yok,
               "guvenli=%s dogru=%s cakisma_yok=%s" % (guvenli, dogru, cakisma_yok))

        # ---- T6 KANONİK+ZİNCİR: sayfa1=/kategori/<slug>/, sayfa2 kendi adresi; prev/next doğru
        t6_c1 = CANON_RE.search(t2_p1)
        t6_c2 = CANON_RE.search(t2_p2)
        t6_p1 = sayfa_okur(t3_tmp, SLUG, 1)
        t6_p2 = sayfa_okur(t3_tmp, SLUG, 2)
        t6_son = sayfa_okur(t3_tmp, SLUG, beklenen_sayfa)
        t6_n1 = NEXT_RE.search(t6_p1)
        t6_p2_prev = PREV_RE.search(t6_p2)
        t6_p2_next = NEXT_RE.search(t6_p2)
        KS2 = SITE + "/kategori/" + SLUG + "/" + mm.SAYFA_AYIRAC + "/2/"
        KS3 = SITE + "/kategori/" + SLUG + "/" + mm.SAYFA_AYIRAC + "/3/"
        kaydet("T6", (
            t6_c1 is not None and t6_c1.group(1) == SITE + "/kategori/" + SLUG + "/"
            and t6_c2 is not None and t6_c2.group(1) == KS2
            and PREV_RE.search(t6_p1) is None
            and t6_n1 is not None and t6_n1.group(1) == KS2
            and t6_p2_prev is not None and t6_p2_prev.group(1) == SITE + "/kategori/" + SLUG + "/"
            and t6_p2_next is not None and t6_p2_next.group(1) == KS3
            and NEXT_RE.search(t6_son) is None),
            "kanonik/prev-next zinciri bozuk")

        # ---- T7 BREADCRUMB: ürün sayfası breadcrumb'ı hub'a gider, ?kategori= İÇERMEZ
        t7_p = urun(0)
        t7_html = build.render_product(t7_p, [t7_p], None)
        kaydet("T7", (
            "/kategori/" + SLUG + "/" in t7_html and "?kategori=" not in t7_html),
            "breadcrumb hub'a bağlanmadı ya da sorgu adresi kaldı")

        # ---- T8 GİZLİ KATEGORİ: Jeneratör + Skan Art için de hub üretilir
        t8_urunler = [urun(100 + i, "Jeneratör") for i in range(3)]
        t8_urunler += [urun(200 + i, "Skan Art") for i in range(2)]
        t8_tmp, t8_sonuc = kos(kb, t8_urunler, ["Jeneratör", "Skan Art"])
        tmp_listesi.append(t8_tmp)
        kaydet("T8", (
            os.path.exists(sayfa_yolu(t8_tmp, "olcuye-ozel-uretim", 1))
            and os.path.exists(sayfa_yolu(t8_tmp, "skan-art", 1))
            and t8_sonuc["kategori_sayfasi_sayisi"] == 2),
            "gizli kategori hub'ı üretilmedi")

        # ---- T9 MUTANT: dilimleme `[:80]`e dönerse T3 (kapsama) DÜŞMELİ
        mutant = mutant_modul_yukle()
        t9_tmp, _ = kos(mutant, katalog(N_BOYUT), ["Otomobil"])
        tmp_listesi.append(t9_tmp)
        m_tam, m_mukerrer, m_gorulen = kapsama(t9_tmp, SLUG, N_BOYUT)
        kaydet("T9", (not m_tam) and len(m_gorulen) < N_BOYUT,
               "mutant kapsamayı düşürmedi (tam=%s tekilsayı=%d)" % (m_tam, len(m_gorulen)))
    finally:
        for t in tmp_listesi:
            shutil.rmtree(t, ignore_errors=True)

    print("VAKA=9 DUSEN=%d" % len(dusen))
    return 1 if dusen else 0


if __name__ == "__main__":
    raise SystemExit(main())
