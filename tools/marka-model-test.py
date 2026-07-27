#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKA -> MODEL KABUL KAPISI (anasayfa çip-marka evreni: Ford/BMW + Volkswagen/Toyota/Mercedes...).

marka_model_build jeneratörünü İZOLE temp ROOT'a çalıştırır ve üretilen HTML'i spec kabul
kriterleriyle ölçer. Ayrıca anasayfa marka çiplerinin SSR link enjeksiyonunu (build._marka_cip_enjekte)
doğrular. build.py'nin urun/ çıktısına MUHTAÇ DEĞİL (modülü doğrudan çağırır). FAIL-CLOSED.

Ölçülen:
  1. Marka evreni index.html TANINMIS_MARKALAR'dan; folding (Mercedes-Benz->Mercedes, Vauxhall->Opel).
  2. Collision: Ford F-150/F150 tek 'f-150' URL; marka slug + model slug eşsiz.
  3. Eşik: yalnız >=3-ürünlü marka SAYFASI + >=3-ürünlü model sayfası; <3 marka/model AYRI sayfa DEĞİL.
  4. Örnek marka/model URL'leri: SSR H1 + ürün <a> + self-canonical + ItemList/CollectionPage/
     BreadcrumbList JSON-LD + sitemap lastmod + huni prefill + attribution modülü.
  5. Öksüz yok: sayfası olan markanın TÜM (folded) ürünleri linkli.
  6. Marka kuralları: authored copy'de yasaklı token 0; telefon yalnız 905451386526.
  7. Anasayfa çipleri: chip_links her biri <a href="/marka/<slug>/">; SSR enjeksiyon #brandChips'i
     doldurur + window.PRUVO_MARKA_SLUG gömülür; her çip markasının SAYFASI var (sayfasız=0 ya da NOT).

Kullanım: python3 tools/marka-model-test.py
"""
import os
import re
import sys
import json
import html
import tempfile
import shutil
from urllib.parse import unquote

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import build                    # noqa: E402
import marka_model_build as mm  # noqa: E402

HATALAR = []
BILGI = []


def bekle(kosul, mesaj):
    if not kosul:
        HATALAR.append(mesaj)


BANNED = [
    r"3\s*d\s*bask", r"3\s*boyutlu\s*bask", r"3d\s*print", r"\bbask[ıi]l?[ıi]?\b",
    r"\byaz[ıi]c[ıi]", r"\bfilament", r"\bfethiye\b", r"\bg[öo]cek\b",
    r"her\s+renk", r"makerworld", r"openscad", r"jenerat[öo]r",
]
BANNED_RE = [re.compile(p, re.I) for p in BANNED]


def authored(page):
    ms = page.find('<main class="content mm">')
    me = page.find('</main>')
    body = page[ms:me] if (ms >= 0 and me > ms) else page
    return re.sub(r'<ul class="mm-grid">.*?</ul>', " ", body, flags=re.S)


def main():
    tmp = tempfile.mkdtemp(prefix="mm-kabul-")
    try:
        with open(build.JSON_PATH, encoding="utf-8") as f:
            products = json.load(f)
        with open(os.path.join(build.ROOT, "index.html"), encoding="utf-8") as f:
            index_html = f.read()

        ctx = build.marka_model_ctx()
        ctx["ROOT"] = tmp
        # index.html'i temp ROOT'a da koy (uret oradan marka evrenini okur)
        with open(os.path.join(tmp, "index.html"), "w", encoding="utf-8") as f:
            f.write(index_html)

        sonuc = mm.uret(products, ctx)
        bekle(isinstance(sonuc, dict), "uret dict döndürmedi")
        sitemap = sonuc["sitemap"]
        loclar = {loc for loc, _p, _f in sitemap}
        sm_str = build.render_sitemap(products, extra_urls=sitemap)
        bekle(sonuc["dizinler"] == ["marka"], "üst dizin ['marka'] değil")

        evren = mm.MarkaEvreni(index_html)
        veri = mm.gruplandir(products, evren)

        # ===== 1: folding =====
        bekle("Ford" in veri and "BMW" in veri, "Ford/BMW evrende yok")
        bekle("Vauxhall" not in veri, "Vauxhall ayrı marka (Opel'e katlanmadı)")
        bekle("Opel" in veri, "Opel evrende yok")
        vaux = [p for p in products if (p.get("marka") or [""])[0] == "Vauxhall"]
        if vaux:
            opel_ids = {p.get("id") for p in veri["Opel"]["marka_only"]}
            for g in veri["Opel"]["gruplar"].values():
                opel_ids |= {p.get("id") for p in g["urunler"]}
            bekle(all(p.get("id") in opel_ids for p in vaux),
                  "Vauxhall ürünleri Opel'e katlanmadı")

        # ===== 2: collision =====
        ford_gruplar = veri["Ford"]["gruplar"]
        f150 = next((g for g in ford_gruplar.values() if g["slug"] == "f-150"), None)
        bekle(f150 is not None and len(f150["urunler"]) >= 201,
              "F-150 collision birleşmedi (>=201 bekleniyor)")
        bekle(not any(g["slug"] == "f150" for g in ford_gruplar.values()),
              "ayrı 'f150' slug (collision folded değil)")
        bekle(not any(g["slug"] == "f-series" for g in ford_gruplar.values()),
              "F-Series ayrı slug (alias uygulanmadı)")
        marka_sluglar = [mm._slug(m) for m in sonuc["slug_map"]]
        bekle(len(marka_sluglar) == len(set(marka_sluglar)), "marka slug'ları eşsiz değil")

        # ===== 3: eşik + sayfa envanteri =====
        marka_dizinleri = []
        marka_kok = os.path.join(tmp, "marka")
        for ad in os.listdir(marka_kok):
            alt = os.path.join(marka_kok, ad)
            if os.path.isdir(alt) and os.path.exists(os.path.join(alt, "index.html")):
                marka_dizinleri.append(ad)
        bekle(len(marka_dizinleri) == sonuc["marka_sayfasi_sayisi"],
              "marka dizini sayısı raporla uyuşmuyor (%d != %d)"
              % (len(marka_dizinleri), sonuc["marka_sayfasi_sayisi"]))
        for m, slug in sonuc["slug_map"].items():
            tot = sum(len(g["urunler"]) for g in veri[m]["gruplar"].values()) + len(veri[m]["marka_only"])
            bekle(tot >= mm.ESIK, "%s marka sayfası aldı ama <%d ürün" % (m, mm.ESIK))
        ince = None
        for m, d in veri.items():
            tot = sum(len(g["urunler"]) for g in d["gruplar"].values()) + len(d["marka_only"])
            if tot < mm.ESIK:
                ince = m
                break
        if ince:
            bekle(not os.path.exists(os.path.join(tmp, "marka", mm._slug(ince))),
                  "<3 ürünlü marka AYRI sayfa aldı: %s" % ince)
        BILGI.append("marka sayfası: %d · model sayfası: %d · ince marka örneği: %s"
                     % (sonuc["marka_sayfasi_sayisi"], sonuc["model_sayfasi_sayisi"], ince))

        # ===== 4: örnek marka/model URL derin ölçüm =====
        ornek_markalar = ["Ford", "BMW", "Volkswagen", "Toyota", "Mercedes"]
        for marka in ornek_markalar:
            if marka not in veri:
                continue
            marka_slug = mm._slug(marka)
            myol = os.path.join(tmp, "marka", marka_slug, "index.html")
            bekle(os.path.exists(myol), "%s marka sayfası yok" % marka)
            if os.path.exists(myol):
                with open(myol, encoding="utf-8") as f:
                    mp = f.read()
                murl = "https://pruvo3d.com/marka/%s/" % marka_slug
                bekle(('<link rel="canonical" href="%s">' % murl) in mp, "%s marka canonical yok" % marka)
                bekle("{model}" not in mp and "{marka}" not in mp, "%s marka token sızıntı" % marka)
                bekle("wa.me/905451386526" in mp, "%s marka huni yok" % marka)
                for rex in BANNED_RE:
                    mt = rex.search(authored(mp))
                    bekle(mt is None, "%s marka yasaklı token '%s'" % (marka, mt.group(0) if mt else ""))
            buyuk = sorted([g for g in veri[marka]["gruplar"].values() if len(g["urunler"]) >= mm.ESIK],
                           key=lambda g: -len(g["urunler"]))
            if not buyuk:
                continue
            g = buyuk[0]
            yol = os.path.join(tmp, "marka", marka_slug, g["slug"], "index.html")
            bekle(os.path.exists(yol), "%s/%s model sayfası yok" % (marka_slug, g["slug"]))
            if not os.path.exists(yol):
                continue
            with open(yol, encoding="utf-8") as f:
                page = f.read()
            url = "https://pruvo3d.com/marka/%s/%s/" % (marka_slug, g["slug"])
            bekle("<h1>" in page and "Yedek Parça" in page, "%s SSR H1 yok" % g["slug"])
            bekle(len(re.findall(r'href="https://pruvo3d\.com/urun/', page)) >= mm.ESIK,
                  "%s ürün linki < %d" % (g["slug"], mm.ESIK))
            bekle(('<link rel="canonical" href="%s">' % url) in page, "%s self-canonical yok" % g["slug"])
            bekle('<meta name="robots" content="index,follow">' in page, "%s robots yok" % g["slug"])
            for t in ('"ItemList"', '"CollectionPage"', '"BreadcrumbList"'):
                bekle(t in page, "%s %s JSON-LD yok" % (g["slug"], t))
            bekle(("<loc>%s</loc>" % url) in sm_str and url in loclar and "<lastmod>" in sm_str,
                  "%s sitemap lastmod yok" % g["slug"])
            was = re.findall(r'https://wa\.me/905451386526\?text=([^"]+)', page)
            bekle(len(was) >= 1, "%s wa.me CTA yok" % g["slug"])
            if was:
                dec = unquote(was[0])
                bekle((marka + " " + g["display"]) in dec, "%s prefill marka+model yok" % g["slug"])
                bekle("REF:" not in dec, "%s statik prefill REF içeriyor" % g["slug"])
            bekle("PRUVO attribution module: start" in page and "window.pruvoRef" in page,
                  "%s attribution modülü yok" % g["slug"])
            bekle("{model}" not in page and "{marka}" not in page, "%s token sızıntı" % g["slug"])
            for rex in BANNED_RE:
                mt = rex.search(authored(page))
                bekle(mt is None, "%s yasaklı token '%s'" % (g["slug"], mt.group(0) if mt else ""))
            bekle("532" not in authored(page), "%s authored 532" % g["slug"])
            for waurl in re.findall(r'wa\.me/(\d+)', page):
                bekle(waurl == "905451386526", "%s yanlış wa numarası %s" % (g["slug"], waurl))
            for blok in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S):
                try:
                    json.loads(blok)
                except Exception as e:
                    HATALAR.append("%s JSON-LD parse hatası: %s" % (g["slug"], e))

        # ===== 5: öksüz yok (örnek markalarda) =====
        for marka in ornek_markalar:
            if marka not in veri:
                continue
            beklenen = set()
            for p in products:
                mk = p.get("marka") or []
                if mk and evren.taninmis_mi(mk[0]) and evren.katla(mk[0]) == marka and p.get("id"):
                    beklenen.add(p["id"])
            linkli = set()
            for dp, _d, fs in os.walk(os.path.join(tmp, "marka", mm._slug(marka))):
                for fn in fs:
                    if fn == "index.html":
                        with open(os.path.join(dp, fn), encoding="utf-8") as f:
                            pg = f.read()
                        for pid in re.findall(r'href="https://pruvo3d\.com/urun/([^/"]+)/"', pg):
                            linkli.add(html.unescape(pid))
            eksik = beklenen - linkli
            bekle(not eksik, "%s: %d ürün öksüz (linkli değil)" % (marka, len(eksik)))
            BILGI.append("%s: %d ürün, öksüz=%d" % (marka, len(beklenen), len(eksik)))

        # ===== 6: /marka/ index =====
        idx = os.path.join(tmp, "marka", "index.html")
        bekle(os.path.exists(idx), "/marka/ index yok")
        if os.path.exists(idx):
            with open(idx, encoding="utf-8") as f:
                ip = f.read()
            bekle('href="/marka/ford/"' in ip and 'href="/marka/bmw/"' in ip,
                  "/marka/ index marka linkleri eksik")

        # ===== 7: anasayfa çipleri SSR + enjeksiyon =====
        chip_links = sonuc["chip_links"]
        bekle(bool(chip_links), "chip_links boş")
        chip_hrefs = re.findall(r'<a class="brand-btn brand-link[^"]*" href="(/marka/[^"]+/)">', chip_links)
        bekle(len(chip_hrefs) >= 20, "SSR çip linki az (%d)" % len(chip_hrefs))
        for m in sonuc["chip_markalar"]:
            if m in sonuc["slug_map"]:
                bekle(('/marka/%s/' % sonuc["slug_map"][m]) in chip_links, "%s çipi linkli değil" % m)
        bekle(len(sonuc["sayfasiz_cipler"]) == 0, "sayfasız çip var: %s" % sonuc["sayfasiz_cipler"])
        enj = build._marka_cip_enjekte(index_html, chip_links, sonuc["slug_map"])
        bekle('<div class="brand-chips" id="brandChips"><a class="brand-btn brand-link' in enj,
              "SSR enjeksiyon #brandChips'i doldurmadı")
        bekle("window.PRUVO_MARKA_SLUG=" in enj, "PRUVO_MARKA_SLUG gömülmedi")
        bekle('href="/marka/ford/"' in enj and 'href="/marka/bmw/"' in enj,
              "enjekte HTML'de ford/bmw çip linki yok (JS-siz SSR)")
        BILGI.append("SSR çip: %d marka linki (JS-siz), sayfasız çip: %d"
                     % (len(chip_hrefs), len(sonuc["sayfasiz_cipler"])))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n".join("  · " + b for b in BILGI))
    if HATALAR:
        print("\nKIRMIZI — %d ihlal:" % len(HATALAR))
        for h in HATALAR:
            print("  X " + h)
        sys.exit(1)
    print("\nHEPSI GECTI")


if __name__ == "__main__":
    main()
