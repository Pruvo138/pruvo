#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MARKA -> MODEL PİLOT KABUL KAPISI (Ford + BMW).

marka_model_build jeneratörünü İZOLE bir temp ROOT'a çalıştırır ve üretilen HTML'i spec
kabul kriterleriyle ölçer (seo/marka-model-taksonomi-spec.md §9 + marka-model-huni-bileseni-spec.md).
build.py'nin urun/ çıktısına MUHTAÇ DEĞİL (modülü doğrudan çağırır) -> hızlı, build sırasından
bağımsız. FAIL-CLOSED: herhangi bir iddia kırmızıysa exit 1.

Kabul (ölçülen):
  1. Collision: aynı aracın 2 URL'i YOK (F-150/F150 tek URL 'f-150'; slug seti eşsiz).
  2. Yalnız >=3-ürünlü modeller sayfa aldı; tek-ürünlü model AYRI sayfa DEĞİL.
  3. 5 model URL'i: SSR içerik (H1) + ürün <a> linkleri + self-canonical + ItemList JSON-LD +
     robots index,follow (+ sitemap lastmod: render_sitemap ile).
  4. Her model sayfasında huni CTA: wa.me/905451386526 + prefill decode -> '<Marka> <Model>' +
     attribution-ref.js modülü sayfada.
  5. Huni: ham '{model}'/'{marka}' token sızıntısı YOK; marka sayfasında '{model}' 0; statik
     wa.me href'inde REF YOK (organik temiz — REF'i attribution-ref.js paid'de ekler).
  6. Marka kuralları: yasaklı token (3d/baskı/print/filament/yazıcı/şehir/'her renk') YOK;
     telefon yalnız 905451386526 (532'li 0) — AUTHORED copy'de (ürün başlıkları hariç).
  7. Öksüz yok: her pilot markanın TÜM ürünleri (marka[0]==marka) ya marka ya model sayfasında.
  8. JSON-LD geçerli: her ld+json parse edilir; CollectionPage + ItemList + BreadcrumbList var.

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
import build                    # noqa: E402  (module-level offline; main() __main__ guard'lı)
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


def strip_regions(page):
    """AUTHORED copy = yalnız <main> gövdesi EKSİ ürün-başlığı taşıyan mm-grid link listesi.
    Marka-kuralı taraması yalnız bizim yazdığımıza uygulanır — paylaşılan shell (GA/attribution/
    PAGE_CSS: CSS yorumunda 'filament' geçer, her PRUVO sayfasında var) ve katalog ürün başlıkları
    KAPSAM DIŞI."""
    ms = page.find('<main class="content mm">')
    me = page.find('</main>')
    body = page[ms:me] if (ms >= 0 and me > ms) else page
    return re.sub(r'<ul class="mm-grid">.*?</ul>', " ", body, flags=re.S)


def parse_ldjson(page):
    return re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, flags=re.S)


def main():
    tmp = tempfile.mkdtemp(prefix="mm-kabul-")
    try:
        with open(build.JSON_PATH, encoding="utf-8") as f:
            products = json.load(f)

        ctx = build.marka_model_ctx()
        ctx["ROOT"] = tmp
        sitemap, ust = mm.uret(products, ctx)

        # --- sitemap yapısı
        bekle(ust == ["marka"], "üst dizin ['marka'] değil: %r" % (ust,))
        loclar = {loc for loc, _p, _f in sitemap}
        sm_str = build.render_sitemap(products, extra_urls=sitemap)

        # --- ürün->marka gruplama (referans, öksüz kontrolü + collision)
        veri = mm.gruplandir(products)

        # ===== KRITER 1: collision — slug eşsiz + F-150/F150 tek URL =====
        for marka in mm.PILOT_MARKALAR:
            marka_slug = mm._slug(marka)
            sluglar = [g["slug"] for g in veri[marka]["gruplar"].values()]
            bekle(len(sluglar) == len(set(sluglar)),
                  "%s: model slug'ları eşsiz değil (collision)" % marka)
        # Ford f-150 grubu 198+3 F150 birleşti mi (>=201) ve f150 slug'ı AYRI YOK
        ford_gruplar = veri["Ford"]["gruplar"]
        f150 = None
        for g in ford_gruplar.values():
            if g["slug"] == "f-150":
                f150 = g
        bekle(f150 is not None, "Ford f-150 grubu yok")
        if f150:
            bekle(len(f150["urunler"]) >= 201,
                  "F-150 collision birleşmedi (adet=%d, beklenen>=201)" % len(f150["urunler"]))
            bekle(f150["display"] == "F-150", "F-150 kanonik gösterim yanlış: %r" % f150["display"])
        bekle(not any(g["slug"] == "f150" for g in ford_gruplar.values()),
              "AYRI 'f150' slug'ı var (collision folded değil)")
        # F-Series -> F-Serisi alias
        bekle(not any(g["slug"] == "f-series" for g in ford_gruplar.values()),
              "F-Series ayrı slug (alias uygulanmadı)")

        # ===== KRITER 2: yalnız >=3-ürünlü modeller sayfa aldı =====
        model_dosyalari = []
        for marka in mm.PILOT_MARKALAR:
            marka_slug = mm._slug(marka)
            kok = os.path.join(tmp, "marka", marka_slug)
            for ad in os.listdir(kok):
                alt = os.path.join(kok, ad)
                if os.path.isdir(alt) and os.path.exists(os.path.join(alt, "index.html")):
                    model_dosyalari.append((marka, ad, os.path.join(alt, "index.html")))
        # her model sayfasının grubu >=3
        for marka, slug, yol in model_dosyalari:
            g = next((x for x in veri[marka]["gruplar"].values() if x["slug"] == slug), None)
            bekle(g is not None and len(g["urunler"]) >= mm.ESIK,
                  "%s/%s sayfa aldı ama <%d ürünlü" % (marka, slug, mm.ESIK))
        # tek-ürünlü bir model sayfa ALMADI (örnek bul)
        tekil_ornek = None
        for marka in mm.PILOT_MARKALAR:
            for g in veri[marka]["gruplar"].values():
                if len(g["urunler"]) == 1:
                    tekil_ornek = (mm._slug(marka), g["slug"])
                    break
            if tekil_ornek:
                break
        if tekil_ornek:
            bekle(not os.path.exists(os.path.join(tmp, "marka", tekil_ornek[0], tekil_ornek[1])),
                  "tek-ürünlü model AYRI sayfa aldı: %s/%s" % tekil_ornek)
        BILGI.append("model sayfası: %d (tek-ürünlü örnek katlandı: %s)"
                     % (len(model_dosyalari), tekil_ornek))

        # ===== KRITER 3-6-8: 5 örnek model URL derin ölçüm =====
        ornekler = [("Ford", "focus"), ("Ford", "f-150"), ("Ford", "transit"),
                    ("BMW", "e46"), ("BMW", "r1200gs")]
        for marka, slug in ornekler:
            marka_slug = mm._slug(marka)
            yol = os.path.join(tmp, "marka", marka_slug, slug, "index.html")
            bekle(os.path.exists(yol), "örnek model sayfası yok: %s/%s" % (marka_slug, slug))
            if not os.path.exists(yol):
                continue
            with open(yol, encoding="utf-8") as f:
                page = f.read()
            url = "https://pruvo3d.com/marka/%s/%s/" % (marka_slug, slug)
            # 3a SSR H1
            bekle("<h1>" in page and "Yedek Parça" in page, "%s: H1/SSR içerik yok" % slug)
            # 3b ürün linkleri (SSR)
            urun_link = len(re.findall(r'href="https://pruvo3d\.com/urun/', page))
            bekle(urun_link >= mm.ESIK, "%s: ürün linki < %d (%d)" % (slug, mm.ESIK, urun_link))
            # 3c self-canonical
            bekle(('<link rel="canonical" href="%s">' % url) in page,
                  "%s: self-canonical yanlış/yok" % slug)
            # 3d robots index,follow
            bekle('<meta name="robots" content="index,follow">' in page,
                  "%s: robots index,follow yok" % slug)
            # 3e ItemList JSON-LD
            bekle('"ItemList"' in page, "%s: ItemList JSON-LD yok" % slug)
            bekle('"CollectionPage"' in page, "%s: CollectionPage JSON-LD yok" % slug)
            bekle('"BreadcrumbList"' in page, "%s: BreadcrumbList JSON-LD yok" % slug)
            # 3f sitemap lastmod
            bekle(("<loc>%s</loc>" % url) in sm_str and url in loclar,
                  "%s: sitemap'te yok" % slug)
            bekle("<lastmod>" in sm_str, "sitemap lastmod yok")
            # 4 huni CTA — wa.me + prefill decode -> '<Marka> <Model>'
            was = re.findall(r'https://wa\.me/905451386526\?text=([^"]+)', page)
            bekle(len(was) >= 1, "%s: wa.me CTA yok" % slug)
            if was:
                decoded = unquote(was[0])
                g = next(x for x in veri[marka]["gruplar"].values() if x["slug"] == slug)
                beklenen = marka + " " + g["display"]
                bekle(beklenen in decoded,
                      "%s: prefill '%s' içermiyor (%r)" % (slug, beklenen, decoded[:60]))
                # organik: statik href'te REF YOK
                bekle("REF:" not in decoded, "%s: statik prefill REF içeriyor (organik kirli)" % slug)
            # 4b attribution modülü sayfada
            bekle("PRUVO attribution module: start" in page and "window.pruvoRef" in page,
                  "%s: attribution-ref.js modülü sayfada yok" % slug)
            # 5 token sızıntı
            bekle("{model}" not in page and "{marka}" not in page,
                  "%s: ham token sızıntısı" % slug)
            # 6 marka kuralı (authored bölge)
            authored = strip_regions(page)
            for rex in BANNED_RE:
                m = rex.search(authored)
                bekle(m is None, "%s: yasaklı token '%s'" % (slug, m.group(0) if m else ""))
            bekle("532" not in authored, "%s: authored copy'de 532 (yanlış telefon)" % slug)
            for waurl in re.findall(r'wa\.me/(\d+)', page):
                bekle(waurl == "905451386526", "%s: yanlış wa numarası %s" % (slug, waurl))
            # 8 JSON-LD geçerli parse
            for blok in parse_ldjson(page):
                try:
                    json.loads(blok)
                except Exception as e:
                    HATALAR.append("%s: JSON-LD parse hatası: %s" % (slug, e))

        # ===== marka sayfası: '{model}' 0 + huni B + token =====
        for marka in mm.PILOT_MARKALAR:
            yol = os.path.join(tmp, "marka", mm._slug(marka), "index.html")
            with open(yol, encoding="utf-8") as f:
                page = f.read()
            bekle("{model}" not in page, "%s marka sayfası: ham '{model}' var (token sızıntı)" % marka)
            bekle("{marka}" not in page, "%s marka sayfası: ham '{marka}' var" % marka)
            bekle('<link rel="canonical" href="https://pruvo3d.com/marka/%s/">' % mm._slug(marka) in page,
                  "%s marka sayfası self-canonical yok" % marka)
            bekle("wa.me/905451386526" in page, "%s marka sayfası huni yok" % marka)
            authored = strip_regions(page)
            for rex in BANNED_RE:
                m = rex.search(authored)
                bekle(m is None, "%s marka: yasaklı token '%s'" % (marka, m.group(0) if m else ""))

        # ===== marka index /marka/ =====
        idx = os.path.join(tmp, "marka", "index.html")
        bekle(os.path.exists(idx), "/marka/ index yok")
        if os.path.exists(idx):
            with open(idx, encoding="utf-8") as f:
                ip = f.read()
            bekle('href="/marka/ford/"' in ip and 'href="/marka/bmw/"' in ip,
                  "/marka/ index marka linkleri eksik")

        # ===== KRITER 7: öksüz yok — pilot markanın TÜM ürünleri bir sayfada linkli =====
        for marka in mm.PILOT_MARKALAR:
            beklenen_ids = set()
            for p in products:
                m = p.get("marka") or []
                if m and m[0] == marka and p.get("id"):
                    beklenen_ids.add(p["id"])
            linkli = set()
            marka_kok = os.path.join(tmp, "marka", mm._slug(marka))
            for dirpath, _dirs, files in os.walk(marka_kok):
                for fn in files:
                    if fn != "index.html":
                        continue
                    with open(os.path.join(dirpath, fn), encoding="utf-8") as f:
                        pg = f.read()
                    for pid in re.findall(r'href="https://pruvo3d\.com/urun/([^/"]+)/"', pg):
                        linkli.add(html.unescape(pid))
            eksik = beklenen_ids - linkli
            bekle(not eksik, "%s: %d ürün hiçbir marka/model sayfasında linkli değil (öksüz)"
                  % (marka, len(eksik)))
            BILGI.append("%s: %d ürün, hepsi linkli=%s" % (marka, len(beklenen_ids), not eksik))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n".join("  · " + b for b in BILGI))
    if HATALAR:
        print("\nKIRMIZI — %d ihlal:" % len(HATALAR))
        for h in HATALAR:
            print("  ✗ " + h)
        sys.exit(1)
    print("\nHEPSI GECTI")


if __name__ == "__main__":
    main()
