#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKA HUB SAYFALAMA kabul testi — sentetik veri + bellek-içi mutasyon bataryası.

ÖLÇTÜĞÜ İDDİA (spec dilim-4): /marka/<slug>/ kökü ilk MARKA_KART_N ürünü TAM KART basar,
kalanı /marka/<slug>/sayfa/<N>/ devam sayfalarına böler. Her ürün en az bir statik hub
sayfasında HAM HTML'de görünür; kök adres DEĞİŞMEZ; her sayfa KENDİ canonical'ını taşır;
rel=prev/next zinciri kurulur; üretilen HER sayfa sitemap'e girer; sayısal model slug'larıyla
(/marka/mazda/2/) çakışmaz (sayfa N>=2 `sayfa` AYRIK isim alanında yaşar — T9 mutantı).

TAM katalogla lokalde KOŞMAZ (yasak) — build.marka_model_ctx() + SENTETİK ürünlerle koşar.
Mutant (T8 dilim, T9 çakışma) diske YAZILMAZ, bellekte kurulur.
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
    """Sayfa 1 = kök /marka/ford/index.html; N>=2 = /marka/ford/sayfa/<N>/index.html.
    `sayfa` AYRIK İSİM ALANI (mm.SAYFA_AYIRAC) — sayısal model slug'larıyla çakışma
    ölçüldü (15 Ağu); sayfa 1 = kök DEĞİŞMEZ, /sayfa/1/ ÜRETİLMEZ."""
    if sayfa == 1:
        return os.path.join(tmp, "marka", SLUG, "index.html")
    return os.path.join(tmp, "marka", SLUG, mm.SAYFA_AYIRAC, str(sayfa), "index.html")


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


def mutant_eski_sema_modul_yukle():
    """Adres şemasını ESKİ `/<N>/`'e döndüren bellek-içi mutant. T9 ÇAKIŞMA FİKSTÜRÜ'nün
    ESKİ şemada KIRMIZI olduğunu kanıtlar. `marka_model_build`'in iki yerini birden çevirir:
      · `_marka_sayfa_adresi`  → `/<N>/` (SAYFA_AYIRAC'sız)
      · `_sayfa_gezinti_html`  → göreli bağlar kökten sonra `<N>/` kullanır
    Model sayfası kanonik (`/marka/<slug>/<model_slug>/`) OLDUĞU GİBİ kalır — model slug'ı
    `2` ile sayfalama N=2 ÇAKIŞIR; mutant bunu yeniden doğurur (kırmızı kanıt)."""
    with open(MM_PATH, encoding="utf-8") as f:
        kaynak = f.read()
    # 1) _marka_sayfa_adresi: kök/sayfa2'yi eski `/<N>/` şemasına çevir
    eski_adres = (
        "def _marka_sayfa_adresi(SITE, marka_slug, sayfa):\n"
        "    if sayfa == 1:\n"
        "        return SITE + \"/marka/\" + marka_slug + \"/\"\n"
        "    return SITE + \"/marka/\" + marka_slug + \"/\" + str(sayfa) + \"/\"\n"
    )
    kaynak = re.sub(
        r"def _marka_sayfa_adresi\(SITE, marka_slug, sayfa\):.*?(?=\ndef |\nclass |\Z)",
        eski_adres + "\n\n", kaynak, count=1, flags=re.S)
    # 2) _sayfa_gezinti_html: göreli bağlarda SAYFA_AYIRAC'i kaldır
    kaynak = kaynak.replace(
        'marka_slug + "/" + SAYFA_AYIRAC + "/" + str(',
        'marka_slug + "/" + str(')
    mod = types.ModuleType("pruvo_mm_sayfalama_mutant_eski")
    mod.__file__ = MM_PATH
    mod.__package__ = ""
    sys.modules["pruvo_mm_saypalama_mutant_eski"] = mod
    exec(compile(kaynak, MM_PATH, "exec"), mod.__dict__)
    return mod


def cakisma_katalog():
    """Çakışma fikstürü — modelleri `2`,`3`,`5`,`6` olan, 100 ürünlü Mazda.
    T9'un ASIL İDDİASI: yeni şemada TÜM üretilen URL'ler BENZERSİZ; hiçbir sayfalama adresi
    `/marka/mazda/2/`, `/3/`, `/5/`, `/6/` model adresini EZMEZ. ESKİ şemada mutant bunu kırar
    (4 mükerrer URL). marka[]'deki 2/3/5/6 jetonları kanonik model anahtarı olur
    (model_anahtari='Mazda','2'='2')."""
    out = []
    for n in ["2", "3", "5", "6"]:
        for i in range(25):
            out.append({"id": "mazda-%s-%05d" % (n, i), "kategori": "Otomobil",
                        "marka": ["Mazda", n], "baslik": "Mazda %s parça %d" % (n, i),
                        "fiyat": "10 TL", "gorseller": []})
    return out


def sayfa_slug_katalog():
    """Sayfa slug fikstürü — modeli 'Sayfa' olan marka. T10 İDDİASI: üretici SystemExit ile
    fail-closed durur (`/marka/<marka>/sayfa/<N>/` ile çakışan slug). Model token 'Sayfa'
    kanonik anahtar `sayfa` üretir; üretici slug == SAYFA_AYIRAC ise YAPIMDAN ÇIKAR.
    marka[]'deki 'Mazda' TANINMIS listesinde olmalı (aksi halde üyelik açılmaz, model de
    doğmaz, fail-closed tetiklenmez — bu yüzden sentetik marka yerine gerçek marka)."""
    out = []
    for i in range(4):
        out.append({"id": "ss-%05d" % i, "kategori": "Otomobil",
                    "marka": ["Mazda", "Sayfa"], "baslik": "Mazda Sayfa parça %d" % i,
                    "fiyat": "10 TL", "gorseller": []})
    return out


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

        # ---- T5 KANONİK: sayfa1=/marka/ford/, sayfa2=/marka/ford/sayfa/2/
        t5_c1 = CANON_RE.search(t2_p1)
        t5_c2 = CANON_RE.search(t2_p2)
        kaydet("T5", (
            t5_c1 is not None and t5_c1.group(1) == SITE + "/marka/" + SLUG + "/"
            and t5_c2 is not None and t5_c2.group(1) == SITE + "/marka/" + SLUG + "/"
            + mm.SAYFA_AYIRAC + "/2/"),
            "sayfa2 kendini sayfa1 kanoniği yapmamalı")

        # ---- T6 ZİNCİR: sayfa1 next=sayfa/2 · sayfa2 prev=/,next=sayfa/3 · son sayfa next YOK
        t6_p1 = sayfa_okur(t3_tmp, 1)
        t6_p2 = sayfa_okur(t3_tmp, 2)
        t6_son = sayfa_okur(t3_tmp, beklenen_sayfa)
        t6_n1 = NEXT_RE.search(t6_p1)
        t6_p2_prev = PREV_RE.search(t6_p2)
        t6_p2_next = NEXT_RE.search(t6_p2)
        SAYFA2 = SITE + "/marka/" + SLUG + "/" + mm.SAYFA_AYIRAC + "/2/"
        SAYFA3 = SITE + "/marka/" + SLUG + "/" + mm.SAYFA_AYIRAC + "/3/"
        kaydet("T6", (
            PREV_RE.search(t6_p1) is None
            and t6_n1 is not None and t6_n1.group(1) == SAYFA2
            and t6_p2_prev is not None and t6_p2_prev.group(1) == SITE + "/marka/" + SLUG + "/"
            and t6_p2_next is not None and t6_p2_next.group(1) == SAYFA3
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

        # ---- T9 ÇAKIŞMA FİKSTÜRÜ (asıl iddia): modeller 2/3/5/6, 100 ürün.
        # Üretilen TÜM URL'ler benzersiz (`len(set(urls)) == len(urls)`) ve hiçbir sayfalama
        # adresi (`/marka/mazda/sayfa/2/`) model adresini (`/marka/mazda/2/`) EZMEZ. ESKİ
        # şemada (mutant `/<N>/`e döner) kırmızı yanmalı — T9a. Yeni şemada yeşil — T9b.
        t9b_tmp, t9b_sonuc = kos(mm, cakisma_katalog())
        tmp_listesi.append(t9b_tmp)
        t9b_url_listesi = [url for _sinif, url in t9b_sonuc.get("sitemap_sayfalari", [])]
        t9b_url_set = set(t9b_url_listesi)
        t9b_benzersiz = len(t9b_url_set) == len(t9b_url_listesi)
        t9b_model_adresleri = {SITE + "/marka/mazda/" + s + "/" for s in ("2", "3", "5", "6")}
        t9b_sayfa_adresleri = {u for u in t9b_url_set if "/sayfa/" in u}
        t9b_ezme_yok = t9b_sayfa_adresleri.isdisjoint(t9b_model_adresleri)
        kaydet("T9b", t9b_benzersiz and t9b_ezme_yok,
               "benzersiz=%s (set=%d liste=%d) ezme_yok=%s (sayfa=%s model=%s)"
               % (t9b_benzersiz, len(t9b_url_set), len(t9b_url_listesi), t9b_ezme_yok,
                  sorted(t9b_sayfa_adresleri)[:3], sorted(t9b_model_adresleri)))

        # ---- T9a MUTANT (ESKİ şema kanıtı): /<N>/ mutant'ı aynı fikstürde mükerrer URL
        # ÜRETİR — yani eski şema ÇAKIŞMA üretirdi. T9b'nin gerçekten yeni şemayı ölçtüğünü
        # doğrular. Mutant bellek-içi; diske YAZILMAZ.
        eski_mutant = mutant_eski_sema_modul_yukle()
        t9a_tmp, t9a_sonuc = kos(eski_mutant, cakisma_katalog())
        tmp_listesi.append(t9a_tmp)
        t9a_url_listesi = [url for _sinif, url in t9a_sonuc.get("sitemap_sayfalari", [])]
        t9a_mukerrer = len(set(t9a_url_listesi)) < len(t9a_url_listesi)
        kaydet("T9a", t9a_mukerrer,
               "ESKİ şema mutant'ı mükerrer URL ÜRETMEDİ (%d benzersiz / %d toplam) — T9b'nin "
               "yeni şemayı ölçtüğü kanıtlanmıyor" % (len(set(t9a_url_listesi)),
                                                       len(t9a_url_listesi)))

        # ---- T10 SAYFA SLUG FİKSTÜRÜ: model slug'ı SAYFA_AYIRAC ile çakışan markada
        # üretici fail-closed (SystemExit) davranır — sessizce ezip geçmez.
        try:
            t10_tmp, _ = kos(mm, sayfa_slug_katalog())
            tmp_listesi.append(t10_tmp)
            kaydet("T10", False,
                   "model slug'ı '%s' olan üretici SystemExit ETMEDİ (sessizce üretti)" %
                   mm.SAYFA_AYIRAC)
        except SystemExit as e:
            mesaj = str(e) if e else ""
            t10_kaldi = False
            t10_mesaj = mm.SAYFA_AYIRAC in mesaj or "sayfa" in mesaj.lower()
            kaydet("T10", t10_mesaj,
                   "fail-closed mesajı SAYFA_AYIRAC'i anmıyor: %s" % mesaj[:120])
    finally:
        for t in tmp_listesi:
            shutil.rmtree(t, ignore_errors=True)

    print("VAKA=10 DUSEN=%d" % len(dusen))
    return 1 if dusen else 0


if __name__ == "__main__":
    raise SystemExit(main())
