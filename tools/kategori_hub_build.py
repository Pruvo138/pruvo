#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KATEGORİ HUB jeneratörü — /kategori/<slug>/ statik, sayfalanmış kategori sayfaları.

NEDEN VAR (15 Ağu, iç-link dilim-5): kategori erişimi yalnız ?kategori= JS filtresiydi;
`marka` alanı boş 2.101 ürün (Marin 1284 · Dekorasyon 374 · Ev 155 · Otomobil 111 · Ofis 68)
hiçbir statik girişte görünmüyordu. Bu modül her kategori için CRAWLABLE (SSR, düz <a href>),
sayfalanmış bir hub üretir; ürün sayfası breadcrumb'ı da buraya bağlanır (28.000+ iç link).

ADDITIVE + İZOLE: build.py main()'de ÇAĞIRIR; urunler.json / marka/ akışına DOKUNMAZ.

Kategori evreni + slug + görünür etiket TEK KAYNAKTAN (build.py CATEGORIES + NAV_GIZLI +
GIZLI_SERI_KARARI) ctx ile gelir — burada KOPYA TUTULMAZ (ikiz liste ayrışması yasak).
Kart yüzeyi/CSS marka hub'ıyla AYNI (mm._kart/_shell) — yeni CSS YAZILMAZ. Sayfa başına ürün
sayısı marka hub'ıyla AYNI (mm.MARKA_KART_N) — ikiz sabit YAZILMAZ.
"""
import os
import json

import marka_model_build as mm

# Kategori sayfa sınıfları (marka tablosundan AYRI — marka sayaçlarına karışmaz; marka-kapsam
# "sitemap sınıf evreni birebir" ölçüsü mm.SITEMAP_SAYFA_SINIFLARI üzerinden kalır). Üretici
# her kaydı bu tablodan geçirir -> fail-closed.
SITEMAP_SINIFLARI = {
    "kategori": ("0.7", "weekly"),
    "kategori_sayfa": ("0.6", "weekly"),
}


def _kategori_sayfa_adresi(SITE, slug, sayfa):
    """Kategori hub sayfasının KANONİK adresi. Sayfa 1 = /kategori/<slug>/ (DEĞİŞMEZ),
    N>=2 = /kategori/<slug>/<N>/. TEK KAYNAK: canonical/rel=prev/next/gezinti AYNI fonksiyonu
    çağırır; ikinci bir adres kuralı yazılsaydı kök ile devam sayfaları sessizce ayrışırdı."""
    if sayfa == 1:
        return SITE + "/kategori/" + slug + "/"
    return SITE + "/kategori/" + slug + "/" + str(sayfa) + "/"


def _kategori_sayfa_sayisi(kalem_sayisi):
    """Gerekli statik hub sayfası sayısı = ceil(n / MARKA_KART_N). Marka hub'ıyla AYNI formül
    (mm._marka_sayfa_sayisi) — kopya formül ayrışırdı."""
    return mm._marka_sayfa_sayisi(kalem_sayisi)


def _kategori_sayfa_dilimi(kalemler, sayfa):
    """Kategori hub sayfası <sayfa>'nın basacağı dilim — TEK KAYNAK (T9 mutantı burayı hedefler).
    Sayfa N (N>=1): kalemler[(N-1)*MARKA_KART_N : N*MARKA_KART_N]; son sayfa eksik dolabilir."""
    return mm._marka_sayfa_dilimi(kalemler, sayfa)


def _sayfa_rel_linkleri(esc, SITE, slug, sayfa, toplam_sayfa):
    """<head> için rel=prev/next — kanonikle AYNI MUTLAK adres (crawler zinciri).
    Sayfa 1'de prev YOK, son sayfada next YOK."""
    out = []
    if sayfa > 1:
        out.append('<link rel="prev" href="%s">'
                   % esc(_kategori_sayfa_adresi(SITE, slug, sayfa - 1)))
    if sayfa < toplam_sayfa:
        out.append('<link rel="next" href="%s">'
                   % esc(_kategori_sayfa_adresi(SITE, slug, sayfa + 1)))
    return "".join(x + "\n" for x in out)


def _sayfa_gezinti_html(esc, slug, sayfa, toplam_sayfa):
    """GÖRÜNÜR sayfa gezinmesi (Önceki · 1 2 3 … · Sonraki). Sayfa 1'de Önceki, son sayfada
    Sonraki YOK. Kök adres /kategori/<slug>/ (DEĞİŞMEZ), N>=2 /kategori/<slug>/<N>/. Marka
    hub'ıyla AYNI sınıflar (mm-sayfa) — yeni CSS YOK."""
    if toplam_sayfa <= 1:
        return ""
    parcalar = []
    if sayfa > 1:
        onceki = slug + "/" if sayfa == 2 else slug + "/" + str(sayfa - 1) + "/"
        parcalar.append('<a class="mm-sayfa-onceki" rel="prev" href="/kategori/%s">%s</a>'
                        % (onceki, esc("← Önceki")))
    for n in range(1, toplam_sayfa + 1):
        if n == sayfa:
            parcalar.append('<span class="mm-sayfa-sayi mm-simdi" aria-current="page">%d</span>'
                            % n)
        else:
            hedef = slug + "/" if n == 1 else slug + "/" + str(n) + "/"
            parcalar.append('<a class="mm-sayfa-sayi" href="/kategori/%s">%d</a>' % (hedef, n))
    if sayfa < toplam_sayfa:
        sonraki = slug + "/" + str(sayfa + 1) + "/"
        parcalar.append('<a class="mm-sayfa-sonraki" rel="next" href="/kategori/%s">%s</a>'
                        % (sonraki, esc("Sonraki →")))
    return ('<nav class="mm-sayfa" aria-label="Sayfa gezinmesi">' + "".join(parcalar) + '</nav>')


def _kategori_sayfasi(ctx, kategori, slug, kalemler, sayfa, toplam_sayfa):
    esc = ctx["esc"]
    SITE = ctx["SITE"]
    gorunur = ctx["kategori_gorunur"](kategori)
    url = _kategori_sayfa_adresi(SITE, slug, sayfa)
    basili = _kategori_sayfa_dilimi(kalemler, sayfa)
    n = len(kalemler)

    h1 = gorunur + " Yedek Parça — Ölçüye Özel Üretim"
    title = h1 if sayfa == 1 else h1 + " — Sayfa " + str(sayfa)
    giris = (gorunur + " için kırılan ya da artık bulunamayan plastik parçaları numunenizden "
             "ölçüye özel üretiyoruz. Klipsler, kapak ve tutamaklar, dişliler, braketler ve "
             "bağlantı parçaları gibi küçük ama önemli parçaları elinizdeki numuneden birebir, "
             "parçanın çalışacağı yere göre doğru malzemeyle yeniden üretiyoruz.")
    if sayfa == 1:
        description = (gorunur + " yedek parçaları: " + str(n) + " parça listeleniyor. "
                       "Bulamadığınız parçayı numunenizden ölçüye özel üretelim.")
    else:
        description = (gorunur + " yedek parçaları — sayfa " + str(sayfa) + ": "
                       + str(len(basili)) + " parça listeleniyor. Diğer sayfalara gezinme "
                       "bağlantılarından devam edin.")

    bc = ('<nav class="mm-bc" aria-label="breadcrumb"><a href="/">Ana Sayfa</a> &rsaquo; '
          + esc(gorunur) + '</nav>')

    prefill = ("Merhaba, " + gorunur + " kategorisinde bir parça arıyorum, sitede bulamadım. "
               "Elimdeki numuneyi ölçüp ölçüye özel üretebilir misiniz?")
    huni = mm._huni_blok(
        esc, gorunur + " parçanızı bulamadınız mı?",
        gorunur + " için aradığınız parçayı sitede bulamadıysanız bizimle konuşun. "
        "Elinizdeki kırık veya eski parçayı ölçüp, çalışacağı yere göre doğru malzemeyle "
        "ölçüye özel üretiyoruz. Ölçü sizden, üretim bizden. Parçanızın fotoğrafını "
        "WhatsApp'tan " + mm.WA_TEL_GORUNUR + " numarasına gönderin.",
        prefill, "WhatsApp'tan Yazın")

    # Sayfa sayacı: kök = erişilebilir TÜM kalemler, devam = kendi dilimi. Marka hub'ıyla AYNI
    # sınıf ayrımı (erisim/parca) — marka-sayac-kapisi'nin okuduğu birim ayrışmasın.
    sayfa_kalemleri = kalemler if sayfa == 1 else basili
    oncul = "Bu kategoride" if sayfa == 1 else "Bu sayfada"
    bolum = "erisim" if sayfa == 1 else "parca"

    body = (bc
            + '<h1>' + esc(h1) + '</h1>'
            + '<p class="lead">' + esc(giris) + '</p>'
            + mm._arama_kutusu_html(esc)
            + mm._toplam_bloku(esc, sayfa_kalemleri, oncul)
            + ('<h2 class="mm-sec-h">' + esc(gorunur) + ' parçaları ('
               + mm._bolum_sayaci(esc, sayfa_kalemleri, bolum) + ')</h2>')
            + mm._urun_grid(ctx, basili)
            + _sayfa_gezinti_html(esc, slug, sayfa, toplam_sayfa)
            + huni)

    breadcrumb_ld = mm._ld({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Ana Sayfa", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": gorunur, "item": url},
        ],
    })
    collection_ld = mm._ld({
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": h1, "url": url, "description": description,
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(basili),
                       "itemListElement": mm._itemlist(ctx, basili)},
    })
    head_extra = _sayfa_rel_linkleri(esc, SITE, slug, sayfa, toplam_sayfa)
    html = mm._shell(ctx, title, url, description, breadcrumb_ld, collection_ld, body,
                     head_extra=head_extra)
    return url, html


def uret(products, ctx):
    """TÜM kategoriler (CATEGORIES + NAV_GIZLI — build.py TEK KAYNAK) için /kategori/<slug>/
    hub üretir. Boş kategori atlanır (ince sayfa üretilmez). urunler.json DEĞİŞMEZ.

    Dönüş: {"sitemap":[...], "dizinler":["kategori"], "sitemap_sayfalari":[...],
            "sayim":{kategori: {...}}, "kategori_sayfasi_sayisi":N, "kategori_sayfa_sayisi":N}."""
    ROOT = ctx["ROOT"]
    SITE = ctx["SITE"]
    esc = ctx["esc"]
    kategori_listesi = ctx["kategori_evreni"]

    by_kat = {}
    for p in products:
        kat = (p.get("kategori") or "").strip()
        if kat:
            by_kat.setdefault(kat, []).append(p)

    sitemap = []
    sitemap_sayfalari = []
    sayim = {}
    slug_gorulen = {}

    def yaz(url, html):
        yol = url[len(SITE):].strip("/")          # "kategori/otomobil" ya da "kategori/otomobil/2"
        klasor = os.path.join(ROOT, *yol.split("/"))
        os.makedirs(klasor, exist_ok=True)
        with open(os.path.join(klasor, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)

    def sitemap_ekle(sinif, url):
        if sinif not in SITEMAP_SINIFLARI:
            raise SystemExit("HATA: tanımsız kategori sitemap sınıfı: %r" % (sinif,))
        priority, changefreq = SITEMAP_SINIFLARI[sinif]
        sitemap.append((url, priority, changefreq))
        sitemap_sayfalari.append((sinif, url))

    for kategori in kategori_listesi:
        kalemler = by_kat.get(kategori, [])
        if not kalemler:
            continue                            # boş kategori -> hub YOK (ince sayfa üretilmez)
        slug = ctx["kategori_slug"](kategori)
        if not slug:
            raise SystemExit("HATA: kategori slug'ı BOŞ — %r (folding bozuk)." % (kategori,))
        if slug in slug_gorulen and slug_gorulen[slug] != kategori:
            raise SystemExit("HATA: kategori slug collision — %s hem %r hem %r "
                             "(folding bozuk)." % (slug, slug_gorulen[slug], kategori))
        slug_gorulen[slug] = kategori

        toplam_sayfa = _kategori_sayfa_sayisi(len(kalemler))
        for sayfa_no in range(1, toplam_sayfa + 1):
            url, html = _kategori_sayfasi(ctx, kategori, slug, kalemler, sayfa_no, toplam_sayfa)
            yaz(url, html)
            sitemap_ekle("kategori" if sayfa_no == 1 else "kategori_sayfa", url)
        sayim[kategori] = {"kategori_sayfasi": 1, "kategori_sayfa_sayisi": toplam_sayfa,
                           "toplam_parca": len(kalemler)}

    sinif_sayilari = {sinif: sum(1 for s, _u in sitemap_sayfalari if s == sinif)
                      for sinif in SITEMAP_SINIFLARI}
    return {
        "sitemap": sitemap,
        "sitemap_sayfalari": sitemap_sayfalari,
        "dizinler": ["kategori"],
        "sayim": sayim,
        "kategori_sayfasi_sayisi": sinif_sayilari["kategori"],
        "kategori_sayfa_sayisi": sinif_sayilari["kategori_sayfa"],
    }
