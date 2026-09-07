#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Landing / içerik sayfaları için JSON-LD (schema.org Article) TEK ÜRETİCİ.

🔴 NEDEN VAR (6 Eyl 2026 GEO denetimi 5/5 eksik buldu; 7 Eyl'de sayıyla ölçüldü):
`tools/build.py::render_content_page` ile basılan **476** içerik/landing sayfasının
yalnız **44**'ünde JSON-LD vardı, **432**'sinde YOKTU. Var olan 44'ün tamamı
`tools/sayfalar.py` gövde dizelerine ELLE gömülmüş literaldi — üreten bir KOD YOKTU.
Bu yüzden burada "genelleştirilecek mevcut üretici" de yoktu; üretici TEK yere,
bu modüle yazıldı ve `render_content_page`'ten TEK satırla çağrılır.

🔴 İKİZ TANIM YASAĞI — `blok()` fail-closed'dur: gövdede zaten
`application/ld+json` geçiyorsa **BOŞ dize** döner. Böylece elle yazılmış JSON-LD
taşıyan 44 sayfanın çıktısı BAYT-AYNI kalır ve hiçbir sayfada aynı `@type`'tan
iki blok oluşmaz. Ölçen kol: `tools/landing-jsonld-kapisi.py`.

🔴 YERLEŞİM GÖVDEDEDİR, HEAD'DE DEĞİL: elle yazılmış 44 blok da gövdede duruyor
(schema.org bunu kabul eder) ve `render_content_page`'in `<head>`'i ArTisT'in
LCP/hız düzlemidir — oraya dokunulmaz.
"""
import json
import re

# Üretilen ve elle yazılmış blokları AYNI ifadeyle arar; kapı da bunu kullanır
# (tek kaynak — iki ayrı regex körlük üretirdi).
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)

# Bir landing JSON-LD belgesinde BULUNMASI ZORUNLU alanlar — `@type` BAŞINA.
# Kapı bu tabloyu okur; buradan bir alan düşerse kapı da o alanı aramayı bırakır
# (bilerek TEK KAYNAK — iki ayrı liste, üretici ile kapının sessizce ayrışmasına
# yol açardı).
#
# 🔴 TİPE GÖRE AYRIŞIR: `Article` tam künye ister. `FAQPage` ise schema.org'da
# `headline`/`description` TAŞIMAZ — tek zorunlusu `mainEntity`'dir. Tek bir
# Article listesiyle ölçmek, elle yazılmış 7 geçerli FAQPage bloğunu KIRMIZI
# yakardı (7 Eyl'de ölçüldü: 47 sahte ihlal).
ZORUNLU_ALANLAR = {
    "Article": ("@context", "@type", "headline", "description",
                "url", "mainEntityOfPage", "inLanguage", "publisher"),
    "FAQPage": ("@context", "@type", "mainEntity"),
}

BEKLENEN_CONTEXT = "https://schema.org"
BEKLENEN_TIP = "Article"
BEKLENEN_DIL = "tr"
YAYINCI = {"@type": "Organization", "name": "PRUVO", "url": "https://pruvo3d.com/"}

# Google Article rehberi: headline 110 karakteri aşmamalı. Ölçüldü (7 Eyl):
# 476 başlığın en uzunu 57 karakter — bugün hiçbiri sınıra yakın değil. Kural
# yine de zorlanır ki ileride uzun başlıklı sayfa eklenirse kapı KIRMIZI yansın.
HEADLINE_TAVANI = 110


def sayfa_url(site, slug):
    """Landing sayfasının kanonik URL'i — `render_content_page`'teki canonical
    ile BİREBİR aynı biçim (site + '/' + slug + '/')."""
    return site + "/" + slug + "/"


def belge(slug, baslik, meta, site="https://pruvo3d.com"):
    """Tek bir landing sayfası için JSON-LD sözlüğünü üretir.

    `headline`/`description` sayfanın GÖRÜNÜR başlığı ve meta açıklamasıdır —
    uydurulmaz, `CONTENT_PAGES` kaydından birebir alınır.
    """
    url = sayfa_url(site, slug)
    return {
        "@context": BEKLENEN_CONTEXT,
        "@type": BEKLENEN_TIP,
        "headline": baslik,
        "description": meta,
        "url": url,
        "mainEntityOfPage": url,
        "inLanguage": BEKLENEN_DIL,
        "publisher": dict(YAYINCI),
    }


def blok(slug, baslik, meta, govde_html, site="https://pruvo3d.com"):
    """`render_content_page`'in gövdeye ekleyeceği <script> bloğu.

    Gövde zaten JSON-LD taşıyorsa BOŞ dize döner (ikiz tanım yasağı).
    """
    if govde_html and LD_RE.search(govde_html):
        return ""
    ham = json.dumps(belge(slug, baslik, meta, site),
                     ensure_ascii=False, separators=(",", ":"))
    # `</script>` gövdeden kaçırılır: bir başlık/meta içine düşerse blok
    # erkenden kapanır ve sayfanın kalanı script bağlamında kalırdı.
    ham = ham.replace("</", "<\\/")
    return '<script type="application/ld+json">%s</script>' % ham


def dogrula(obj, beklenen_url=None):
    """Bir JSON-LD belgesini şema kurallarına göre denetler.

    Döner: ihlal açıklamalarının listesi (BOŞ liste = geçerli). Kapı bu
    fonksiyonu kullanır — doğrulama mantığı da TEK kaynaktır.
    """
    ihlal = []
    if not isinstance(obj, dict):
        return ["belge bir JSON objesi degil (%s)" % type(obj).__name__]
    tip = obj.get("@type")
    # FAQPage elle yazılmış sayfalarda meşrudur; üretilen belge daima Article.
    if tip not in ZORUNLU_ALANLAR:
        ihlal.append("@type beklenmedik: %r" % (tip,))
    for alan in ZORUNLU_ALANLAR.get(tip, ("@context", "@type")):
        if alan not in obj:
            ihlal.append("zorunlu alan EKSIK: %s" % alan)
        elif obj[alan] in ("", None, {}, []):
            ihlal.append("zorunlu alan BOS: %s" % alan)
    ctx = obj.get("@context")
    if ctx not in (BEKLENEN_CONTEXT, "http://schema.org"):
        ihlal.append("@context beklenmedik: %r" % (ctx,))
    hl = obj.get("headline")
    if isinstance(hl, str) and len(hl) > HEADLINE_TAVANI:
        ihlal.append("headline %d karakter (tavan %d)" % (len(hl), HEADLINE_TAVANI))
    yayinci = obj.get("publisher")
    if isinstance(yayinci, dict) and not yayinci.get("name"):
        ihlal.append("publisher.name BOS")
    if beklenen_url is not None:
        # url YA DA mainEntityOfPage sayfanın kendisini göstermeli. Elle yazılmış
        # bloklarda ikisinden yalnız biri bulunabiliyor; biri doğruysa yeter.
        adaylar = []
        for k in ("url", "mainEntityOfPage"):
            v = obj.get(k)
            if isinstance(v, str):
                adaylar.append(v)
            elif isinstance(v, dict) and isinstance(v.get("@id"), str):
                adaylar.append(v["@id"])
        if adaylar and beklenen_url not in adaylar:
            ihlal.append("url/mainEntityOfPage sayfayi gostermiyor: %r != %r"
                         % (adaylar, beklenen_url))
    return ihlal
