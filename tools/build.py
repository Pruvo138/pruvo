#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRUVO statik sayfa üreticisi.

urunler.json'u okur ve her ürün için Google'da çıkabilen, tam SEO'lu
kendi adresine sahip statik bir sayfa üretir:  /urun/<id>/index.html

Ayrıca sitemap.xml, robots.txt ve .nojekyll dosyalarını üretir.

Ürün ekleme akışı:
  1) urunler.json'un başına yeni ürünü ekle
  2) python3 tools/build.py            (bu betik)
  3) git add -A && commit && push       (urunler.json + urun/ + sitemap.xml)

Harici bağımlılık YOK (saf Python 3 standart kütüphane).
"""

import os
import re
import json
import shutil
import html
import datetime

# ------------------------------------------------------------------ ayarlar
SITE = "https://pruvo3d.com"
WHATSAPP = "905325954005"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT, "urunler.json")
URUN_DIR = os.path.join(ROOT, "urun")
CATEGORIES = ["Marin", "Otomobil", "Motosiklet", "Ev", "Elektronik", "Bahçe"]

TODAY = datetime.date.today().isoformat()
PRICE_VALID = (datetime.date.today().replace(month=12, day=31)
               + datetime.timedelta(days=365)).isoformat()

FAVICON = ("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' "
           "viewBox='0 0 100 100'><rect width='100' height='100' rx='20' "
           "fill='%2312294d'/><text x='50' y='55' font-family='Arial,"
           "Helvetica,sans-serif' font-size='72' font-weight='800' "
           "fill='%23ffffff' text-anchor='middle' dominant-baseline='central'"
           ">P</text></svg>")

WA_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12.04 2C6.58 '
           '2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2 22l5.25-1.38a9.9 '
           '9.9 0 0 0 4.79 1.22h.01c5.46 0 9.9-4.45 9.9-9.91 0-2.65-1.03-5.14-'
           '2.9-7.01A9.82 9.82 0 0 0 12.04 2zm5.8 14.13c-.24.68-1.42 1.31-1.96 '
           '1.35-.5.05-.98.24-3.3-.69-2.77-1.09-4.56-3.9-4.7-4.08-.14-.19-1.12-'
           '1.49-1.12-2.84 0-1.35.71-2.02.96-2.29.24-.27.53-.34.71-.34.18 0 .35 '
           '0 .51.01.16.01.38-.06.6.46.24.56.79 1.94.86 2.08.07.14.12.31.02.5-'
           '.09.19-.14.31-.28.48-.14.17-.29.37-.42.5-.14.14-.28.29-.12.57.16.28'
           '.72 1.18 1.54 1.91 1.06.94 1.95 1.24 2.23 1.38.28.14.44.12.6-.07.16-'
           '.19.69-.8.87-1.08.18-.28.36-.23.6-.14.24.09 1.55.73 1.81.86.27.14.45'
           '.21.51.32.06.11.06.64-.18 1.32z"/></svg>')

# ------------------------------------------------------------------ ortak CSS
PAGE_CSS = """
  :root{
    --navy:#12294d;--navy-2:#1c3a6b;--navy-dark:#0d1e3a;
    --gray-bg:#eef1f5;--gray-card:#fff;--gray-line:#d7dde6;
    --gray-text:#5b6675;--red:#d1332e;--red-dark:#b12723;
    --radius:10px;--shadow:0 2px 10px rgba(18,41,77,.08);
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    background:var(--gray-bg);color:var(--navy);line-height:1.5}
  a{color:inherit}
  header{background:var(--navy);color:#fff;padding:20px;box-shadow:var(--shadow)}
  .header-inner{max-width:1100px;margin:0 auto;display:flex;align-items:center;
    justify-content:space-between;gap:16px;flex-wrap:wrap}
  .brand-link{text-decoration:none;color:#fff;display:block}
  .brand{font-size:34px;font-weight:800;letter-spacing:3px;line-height:1}
  .brand-sub{font-size:12px;letter-spacing:2px;text-transform:uppercase;
    color:#b9c6dc;margin-top:5px}
  .top-back{color:#cdd8ea;text-decoration:none;font-weight:600;font-size:14px;
    white-space:nowrap}
  .top-back:hover{color:#fff}

  main{max-width:1100px;margin:0 auto;padding:28px 20px 50px}
  .crumbs{font-size:13px;color:var(--gray-text);margin-bottom:18px}
  .crumbs a{color:var(--navy-2);text-decoration:none}
  .crumbs a:hover{text-decoration:underline}
  .crumbs span{color:var(--gray-line);margin:0 6px}

  .detail{display:grid;grid-template-columns:1fr 1fr;gap:34px;align-items:start}
  .gallery{position:sticky;top:20px}
  .main-img{width:100%;aspect-ratio:1/1;object-fit:contain;background:var(--gray-card);
    border:1px solid var(--gray-line);border-radius:var(--radius);display:block}
  .thumbs{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
  .thumb{width:74px;height:74px;object-fit:cover;border-radius:8px;
    border:2px solid transparent;cursor:pointer;background:var(--gray-card)}
  .thumb:hover{border-color:var(--gray-line)}
  .thumb.active{border-color:var(--navy)}

  .cat{display:inline-block;background:var(--navy);color:#fff;font-size:11px;
    font-weight:600;letter-spacing:.5px;text-transform:uppercase;padding:4px 11px;
    border-radius:20px}
  h1{font-size:27px;font-weight:800;margin:14px 0 10px;color:var(--navy);line-height:1.25}
  .brands{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:14px}
  .brand-chip{background:var(--gray-card);border:1px solid var(--gray-line);
    border-radius:20px;padding:5px 12px;font-size:12.5px;font-weight:600;
    color:var(--navy);text-decoration:none}
  .brand-chip:hover{border-color:var(--navy-2)}
  .price{font-size:26px;font-weight:800;color:var(--navy);margin:4px 0 20px}
  .price.empty{font-size:15px;font-weight:600;color:var(--gray-text)}
  .desc{font-size:15px;color:#39434f;line-height:1.7;margin-bottom:26px}
  .order-btn{background:var(--red);color:#fff;border:none;border-radius:9px;
    padding:15px 22px;font-size:16px;font-weight:700;cursor:pointer;
    text-decoration:none;display:inline-flex;align-items:center;justify-content:center;
    gap:9px;transition:.15s;max-width:320px;width:100%}
  .order-btn:hover{background:var(--red-dark)}
  .order-btn svg{width:19px;height:19px;fill:#fff}
  .note{font-size:12.5px;color:var(--gray-text);margin-top:12px}

  .related{max-width:1100px;margin:0 auto;padding:0 20px 60px}
  .related h2{font-size:19px;font-weight:700;margin-bottom:16px}
  .rel-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:16px}
  .rel-card{background:var(--gray-card);border:1px solid var(--gray-line);
    border-radius:var(--radius);overflow:hidden;text-decoration:none;color:var(--navy);
    display:flex;flex-direction:column;box-shadow:var(--shadow);transition:transform .15s,box-shadow .15s}
  .rel-card:hover{transform:translateY(-3px);box-shadow:0 8px 22px rgba(18,41,77,.14)}
  .rel-img{width:100%;aspect-ratio:4/3;object-fit:cover;background:#dbe2ec;display:block}
  .rel-body{padding:12px 13px 14px}
  .rel-title{font-size:14px;font-weight:700;line-height:1.35;margin-bottom:6px}
  .rel-price{font-size:14px;font-weight:800;color:var(--navy)}

  footer{background:var(--navy-dark);color:#aeb9cd;text-align:center;padding:22px 20px;
    font-size:13.5px;letter-spacing:.5px}
  .foot-nav{margin-top:8px}
  .foot-nav a{color:#c7d2e4;text-decoration:none;margin:0 8px}
  .foot-nav a:hover{color:#fff;text-decoration:underline}

  @media (max-width:760px){
    .detail{grid-template-columns:1fr;gap:22px}
    .gallery{position:static}
    h1{font-size:22px}.price{font-size:22px}
    .order-btn{max-width:none}
  }
"""


# ------------------------------------------------------------------ yardımcılar
def esc(s):
    return html.escape(s or "", quote=True)


def meta_desc(p):
    """Ürün açıklamasından ~160 karakterlik temiz meta açıklama üret."""
    txt = re.sub(r"\s+", " ", (p.get("aciklama") or "")).strip()
    if len(txt) > 158:
        txt = txt[:158].rsplit(" ", 1)[0] + "…"
    return txt


def price_number(fiyat):
    """'1250 TL' -> '1250' (rakam yoksa None)."""
    if not fiyat:
        return None
    digits = re.sub(r"[^0-9]", "", fiyat)
    return digits or None


def images_of(p):
    imgs = p.get("gorseller") or []
    return [i for i in imgs if i]


def wa_href(p, url):
    msg = u"Merhaba, şu ürünle ilgileniyorum: " + (p.get("baslik") or "") + "\n" + url
    from urllib.parse import quote
    return "https://wa.me/" + WHATSAPP + "?text=" + quote(msg)


def product_url(pid):
    return SITE + "/urun/" + pid + "/"


# ------------------------------------------------------------------ ürün sayfası
def render_product(p, all_products):
    pid = p["id"]
    url = product_url(pid)
    baslik = p.get("baslik") or ""
    kategori = p.get("kategori") or ""
    fiyat = (p.get("fiyat") or "").strip()
    markalar = p.get("marka") or []
    imgs = images_of(p)
    cover = imgs[0] if imgs else (SITE + "/favicon.png")
    desc160 = meta_desc(p)
    pnum = price_number(fiyat)

    aciklama_html = esc(p.get("aciklama") or "").replace("\n", "<br>")

    # --- JSON-LD Product
    offer = {
        "@type": "Offer",
        "url": url,
        "availability": "https://schema.org/InStock",
        "itemCondition": "https://schema.org/NewCondition",
        "priceCurrency": "TRY",
        "seller": {"@type": "Organization", "name": "PRUVO"},
    }
    if pnum:
        offer["price"] = pnum
        offer["priceValidUntil"] = PRICE_VALID

    product_ld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": baslik,
        "image": imgs or [cover],
        "description": re.sub(r"\s+", " ", (p.get("aciklama") or "")).strip(),
        "sku": pid,
        "category": kategori,
        "offers": offer,
    }
    if markalar:
        product_ld["brand"] = [{"@type": "Brand", "name": b} for b in markalar]

    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Ana Sayfa", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": kategori,
             "item": SITE + "/?kategori=" + kategori},
            {"@type": "ListItem", "position": 3, "name": baslik, "item": url},
        ],
    }

    def ld(obj):
        return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

    # --- galeri
    main_img = ('<img class="main-img" id="mainImg" src="%s" alt="%s" '
                'width="800" height="800">') % (esc(cover), esc(baslik))
    thumbs_html = ""
    if len(imgs) > 1:
        parts = []
        for i, src in enumerate(imgs):
            cls = "thumb active" if i == 0 else "thumb"
            parts.append(
                '<img class="%s" src="%s" alt="%s görsel %d" '
                'onclick="pv(this,\'%s\')" loading="lazy">'
                % (cls, esc(src), esc(baslik), i + 1, esc(src)))
        thumbs_html = '<div class="thumbs">' + "".join(parts) + "</div>"

    # --- marka çipleri (ana sayfada o markayı filtreler)
    brand_html = ""
    if markalar:
        chips = "".join(
            '<a class="brand-chip" href="/?marka=%s">%s</a>' % (esc(b), esc(b))
            for b in markalar)
        brand_html = '<div class="brands">' + chips + "</div>"

    # --- fiyat
    if fiyat:
        price_html = '<div class="price">%s</div>' % esc(fiyat)
    else:
        price_html = '<div class="price empty">Fiyat için sipariş verin</div>'

    # --- ilgili ürünler (aynı kategori, kendisi hariç, en fazla 8)
    rel = [x for x in all_products
           if x.get("kategori") == kategori and x["id"] != pid][:8]
    rel_html = ""
    if rel:
        cards = []
        for r in rel:
            rimgs = images_of(r)
            rcov = rimgs[0] if rimgs else cover
            rfiyat = (r.get("fiyat") or "").strip()
            rprice = ('<div class="rel-price">%s</div>' % esc(rfiyat)) if rfiyat else ""
            cards.append(
                '<a class="rel-card" href="%s">'
                '<img class="rel-img" src="%s" alt="%s" loading="lazy" '
                'width="400" height="300">'
                '<div class="rel-body"><div class="rel-title">%s</div>%s</div></a>'
                % (product_url(r["id"]), esc(rcov), esc(r.get("baslik") or ""),
                   esc(r.get("baslik") or ""), rprice))
        rel_html = (
            '<section class="related"><h2>Diğer %s ürünleri</h2>'
            '<div class="rel-grid">%s</div></section>'
            % (esc(kategori), "".join(cards)))

    title_tag = esc(baslik) + " — PRUVO Özel Tasarım Yedek Parça"

    doc = u"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="icon" href="{favicon}">
<meta property="og:type" content="product">
<meta property="og:site_name" content="PRUVO">
<meta property="og:locale" content="tr_TR">
<meta property="og:title" content="{ogtitle}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{ogtitle}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{img}">
<script type="application/ld+json">{product_ld}</script>
<script type="application/ld+json">{breadcrumb_ld}</script>
<style>{css}</style>
</head>
<body>
<header>
  <div class="header-inner">
    <a class="brand-link" href="/">
      <div class="brand">PRUVO</div>
      <div class="brand-sub">Endüstriyel Parça Üretimi</div>
    </a>
    <a class="top-back" href="/">&larr; Tüm Ürünler</a>
  </div>
</header>

<main>
  <nav class="crumbs" aria-label="breadcrumb">
    <a href="/">Ana Sayfa</a><span>&rsaquo;</span>
    <a href="/?kategori={katq}">{kategori}</a><span>&rsaquo;</span>
    {baslik}
  </nav>

  <div class="detail">
    <div class="gallery">
      {main_img}
      {thumbs}
    </div>
    <div class="info">
      <span class="cat">{kategori}</span>
      <h1>{h1}</h1>
      {brands}
      {price}
      <p class="desc">{aciklama}</p>
      <a class="order-btn" href="{wa}" target="_blank" rel="noopener">{icon} Sipariş Ver</a>
      <div class="note">WhatsApp üzerinden sipariş alınır. Ürün talep üzerine özel olarak üretilir.</div>
    </div>
  </div>
</main>

{related}

<footer>
  PRUVO &mdash; Endüstriyel Parça Üretimi | Fethiye
  <div class="foot-nav">
    <a href="/hakkimizda/">Hakkımızda</a> &middot; <a href="/sss/">Sıkça Sorulan Sorular</a> &middot; <a href="/iletisim/">İletişim</a>
  </div>
</footer>

<script>
function pv(el,src){{
  document.getElementById('mainImg').src=src;
  var t=document.querySelectorAll('.thumb');
  for(var i=0;i<t.length;i++){{t[i].className='thumb';}}
  el.className='thumb active';
}}
</script>
</body>
</html>
""".format(
        title=title_tag,
        desc=esc(desc160),
        url=esc(url),
        favicon=FAVICON,
        ogtitle=esc(baslik),
        img=esc(cover),
        product_ld=ld(product_ld),
        breadcrumb_ld=ld(breadcrumb_ld),
        css=PAGE_CSS,
        katq=esc(kategori),
        kategori=esc(kategori),
        baslik=esc(baslik),
        main_img=main_img,
        thumbs=thumbs_html,
        h1=esc(baslik),
        brands=brand_html,
        price=price_html,
        aciklama=aciklama_html,
        wa=esc(wa_href(p, url)),
        icon=WA_ICON,
        related=rel_html,
    )
    return doc


# ------------------------------------------------------------------ sitemap
def render_sitemap(products):
    urls = []
    urls.append((SITE + "/", "1.0", "daily"))
    urls.append((SITE + "/hakkimizda/", "0.5", "monthly"))
    urls.append((SITE + "/sss/", "0.5", "monthly"))
    urls.append((SITE + "/iletisim/", "0.6", "monthly"))
    urls.append((SITE + "/gizlilik/", "0.3", "yearly"))
    for p in products:
        urls.append((product_url(p["id"]), "0.8", "weekly"))
    items = []
    for loc, prio, freq in urls:
        items.append(
            "  <url>\n"
            "    <loc>%s</loc>\n"
            "    <lastmod>%s</lastmod>\n"
            "    <changefreq>%s</changefreq>\n"
            "    <priority>%s</priority>\n"
            "  </url>" % (esc(loc), TODAY, freq, prio))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(items) + "\n</urlset>\n")


# ------------------------------------------------------------------ ana akış
def main():
    with open(JSON_PATH, encoding="utf-8") as f:
        products = json.load(f)

    # eski urun/ klasörünü temizle (silinen ürünler kalmasın)
    if os.path.isdir(URUN_DIR):
        shutil.rmtree(URUN_DIR)
    os.makedirs(URUN_DIR, exist_ok=True)

    for p in products:
        pdir = os.path.join(URUN_DIR, p["id"])
        os.makedirs(pdir, exist_ok=True)
        with open(os.path.join(pdir, "index.html"), "w", encoding="utf-8") as f:
            f.write(render_product(p, products))

    # sitemap.xml
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(render_sitemap(products))

    # robots.txt
    with open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8") as f:
        f.write("User-agent: *\nAllow: /\n\nSitemap: " + SITE + "/sitemap.xml\n")

    # .nojekyll  (GitHub Pages tüm dosyaları olduğu gibi sunsun)
    open(os.path.join(ROOT, ".nojekyll"), "w").close()

    print("OK: %d urun sayfasi + sitemap.xml + robots.txt uretildi." % len(products))


if __name__ == "__main__":
    main()
