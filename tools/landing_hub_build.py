#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRUVO landing HUB jeneratörü — uzun-kuyruk içerik sayfaları için TEK crawlable dizin.

NEDEN VAR (28 Tem, keşif kök-sorun): tools/sayfalar.py CONTENT_PAGES'teki 166+ uzun-kuyruk
landing sayfası Google'da "keşfedildi — dizine eklenmedi" bandında sıkıştı; çünkü bu sayfalar
inbound linki YALNIZCA birbirlerinden alıyordu (peer landing iç-linki) — anasayfa/güçlü sayfa
onlara link vermiyordu. Bu modül hepsini listeleyen tek bir crawlable HUB (SSR, düz <a href>)
üretir: H1 + kısa giriş + her landing'e crawlable link. Hub anasayfa footer'ından güçlü inbound
alır, hub da her landing'e link vererek keşif zincirini kapatır.

ADDITIVE + İZOLE: build.py bunu main()'de ÇAĞIRIR; kendi urun/ + marka/ + içerik akışına dokunmaz.
sayfalar.py CONTENT_PAGES DEĞİŞMEZ — landing slug/başlıkları oradan yalnız OKUNUR.

Girdi: ctx (build.py'nin verdiği yardımcı/sabit sözlüğü — esc, SITE, TODAY, PAGE_CSS, FOOT_NAV_HTML,
snippet'ler...). Dönüş: {"sitemap":[(loc,prio,freq)], "dizinler":[HUB_SLUG], "sayim":{...}}.
  sitemap  -> build.py render_sitemap'e extra_urls olarak verilir (lastmod'lu girer)
  dizinler -> build.py _yayin-icerik-dizinleri.txt beyaz-listesine eklenir (deploy _site'a kopyalar)

Marka kuralları (CLAUDE.md — ihlal=sessiz hata): "3D baskı/baskı/yazıcı/filament" GEÇMEZ;
ŞEHİR ADI görünür metinde GEÇMEZ (bölgesel landing başlığındaki "| Göcek-Fethiye" kuyruğu hub link
metninden sıyrılır — hedef URL o bölgesel sayfanın gerçek slug'ıdır, URL görünür pazarlama metni
değildir); tedarikçi/üreteç adı GEÇMEZ; telefon yalnız +90 545 138 6526.
"""
import os
import re
import json

# Nötr, marka-uyumlu hub slug'ı (şehir/"3d"/"baskı" YOK). Bu slug bir CONTENT_PAGES slug'ıyla
# ÇAKIŞMAMALI (build sayfayı /<slug>/index.html'e yazar). marka/ + urun/ gibi .gitignore'da elle
# tutulan bir girdisi vardır (tools/gitignore-kapisi.py CONTENT_PAGES bloğunu koruma altına alır).
HUB_SLUG = "ozel-uretim-rehberi"
HUB_H1 = "Ölçüye Özel Üretim ve Yedek Parça Rehberi"

# Şehir adı temizleyicisi (CLAUDE.md Fethiye kuralı — görünür metin). "| Göcek-Fethiye" gibi
# bölgesel kuyruğu link metninden atar; URL'e (href) dokunmaz.
_SEHIR = re.compile(r"\s*[|·•\-–—]?\s*(göcek|fethiye|mu[gğ]la)\b[^|]*", re.I)


def _gorunur_baslik(baslik):
    t = _SEHIR.sub("", baslik or "")
    t = re.sub(r"\s+", " ", t).strip(" |·•-–—")
    return t


def _ld(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


_HUB_CSS = """
  .content.hub{max-width:1000px}
  .hub-bc{font-size:13px;color:#8996ad;margin:0 0 14px}
  .hub-bc a{color:var(--navy-2);text-decoration:none}
  .hub-bc a:hover{text-decoration:underline}
  .content.hub .lead{margin:0 0 18px}
  .hub-list{list-style:none;padding:0;margin:14px 0 8px;
    column-width:280px;column-gap:26px}
  .hub-list li{break-inside:avoid;margin:0 0 9px}
  .hub-list a{display:block;color:var(--navy);text-decoration:none;font-weight:600;
    font-size:14.5px;line-height:1.35;padding:7px 12px;border:1px solid var(--gray-line);
    border-radius:9px;background:var(--gray-card)}
  .hub-list a:hover{border-color:var(--navy-2);background:#fff}
  .hub-more{margin:22px 0 4px;font-size:14px;color:var(--gray-text)}
  .hub-more a{color:var(--navy-2);font-weight:600;text-decoration:none}
  .hub-more a:hover{text-decoration:underline}
"""


def _shell(ctx, title, canonical_url, description, breadcrumb_ld, collection_ld, body_html):
    esc = ctx["esc"]
    # Taban CSS harici varliktan gelir (build.stil_bloklari); _HUB_CSS ayri varlik.
    stil = ctx["stil_bloklari"](_HUB_CSS)
    return ctx["surumle_scriptler"](u"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{ga_head}
{meta_head}
{attribution_head}
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow">
<link rel="icon" href="{favicon}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="PRUVO">
<meta property="og:title" content="{ogtitle}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<script type="application/ld+json">{collection_ld}</script>
<script type="application/ld+json">{breadcrumb_ld}</script>
{stil}
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

<main class="content hub">
{body}
</main>

<footer>
  PRUVO &mdash; Endüstriyel Parça Üretimi
  {foot_nav}
  {pay_band}
</footer>
{pv_js}
{ga_banner}
</body>
</html>
""".format(
        title=esc(title) + " — PRUVO",
        desc=esc(description),
        ogtitle=esc(title),
        url=esc(canonical_url),
        favicon=ctx["FAVICON"],
        stil=stil,
        body=body_html,
        foot_nav=ctx["FOOT_NAV_HTML"],
        pay_band=ctx["PAY_BAND_HTML"],
        pv_js=ctx["PV_SCRIPT_HTML"],
        ga_head=ctx["GA_HEAD_SNIPPET"],
        meta_head=ctx["META_HEAD_SNIPPET"],
        attribution_head=ctx["attribution_head_snippet"](),
        ga_banner=ctx["GA_BANNER_SNIPPET"],
        collection_ld=collection_ld,
        breadcrumb_ld=breadcrumb_ld,
    ))


def _landingler():
    """sayfalar.py CONTENT_PAGES'ten (slug, görünür_başlık) listesi. CONTENT_PAGES tek kaynak;
    bu modül onu OKUR, DEĞİŞTİRMEZ. STATIK_SAYFALAR (hakkimizda/iletisim/sss/gizlilik) zaten
    footer'dan güçlü inbound alıyor + CONTENT_PAGES'te değil — hub yalnız üretilen landing'leri sayar."""
    import sayfalar
    return [(slug, _gorunur_baslik(baslik)) for slug, baslik, _meta, _fn in sayfalar.CONTENT_PAGES]


def uret(ctx):
    ROOT = ctx["ROOT"]
    SITE = ctx["SITE"]
    esc = ctx["esc"]
    url = SITE + "/" + HUB_SLUG + "/"
    landingler = _landingler()

    description = ("Ölçüye özel üretim ve yedek parça konularının tümünü tek sayfada topladık. "
                   "Aradığınız konuya en yakın başlığı seçin; kırılan ya da bulunamayan parçayı "
                   "numunenizden ölçüye özel üretelim. Ölçü sizden, üretim bizden.")

    bc = ('<nav class="hub-bc" aria-label="breadcrumb"><a href="/">Ana Sayfa</a> &rsaquo; '
          + esc(HUB_H1) + '</nav>')

    lis = "".join('<li><a href="/%s/">%s</a></li>' % (esc(slug), esc(baslik))
                  for slug, baslik in landingler)
    liste = '<ul class="hub-list">' + lis + '</ul>'

    body = (bc
            + '<h1>' + esc(HUB_H1) + '</h1>'
            + '<p class="lead">' + esc(description) + '</p>'
            + liste
            + '<p class="hub-more">Aracınızın markasına göre aramak isterseniz '
              '<a href="/marka/">markalar sayfasına</a> göz atın.</p>')

    breadcrumb_ld = _ld({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Ana Sayfa", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": HUB_H1, "item": url},
        ],
    })
    items = [{"@type": "ListItem", "position": i + 1,
              "url": SITE + "/" + slug + "/", "name": baslik}
             for i, (slug, baslik) in enumerate(landingler)]
    collection_ld = _ld({
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": HUB_H1, "url": url, "description": description,
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(items),
                       "itemListElement": items},
    })

    html = _shell(ctx, HUB_H1, url, description, breadcrumb_ld, collection_ld, body)

    klasor = os.path.join(ROOT, HUB_SLUG)
    os.makedirs(klasor, exist_ok=True)
    with open(os.path.join(klasor, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    return {
        "sitemap": [(url, "0.6", "weekly")],
        "dizinler": [HUB_SLUG],
        "sayim": {"landing_sayisi": len(landingler)},
        "hub_slug": HUB_SLUG,
    }
