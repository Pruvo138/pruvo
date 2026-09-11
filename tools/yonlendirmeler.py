# -*- coding: utf-8 -*-
"""KALICI YONLENDIRME TABLOSU — uretimden cikan icerik slug'lari icin 301 esdegeri.

NEDEN VAR
---------
Okan emri (29 Tem 2026) ile beyaz esya kapsam DISI ilan edildi ve konuya ait 5 icerik
sayfasi uretimden cikarildi. Duz silme (404) bilerek YAPILMADI: bu URL'ler aylardir
indekste ve baglanti degeri tasiyor. Silinen her slug, EN YAKIN kapsam ICI sayfaya
yonlendirilir; boylece arama motoru eski URL'yi indeksten dusurur ve sinyali hedefe
tasir — URL yayin yuzeyinden KAYBOLUR ama deger kaybolmaz.

MEKANIZMA — NEDEN META-REFRESH, NEDEN GERCEK 301 DEGIL
------------------------------------------------------
Yayin origin'i GitHub Pages'tir (`.github/workflows/deploy.yml`); GitHub Pages statik
dosya sunar, `_redirects` DESTEKLEMEZ ve sunucu tarafi 301 uretemez. Onunde Cloudflare
zone'u var; gercek 301 oradaki Redirect Rules ile kurulur ama bu PANEL/TOKEN yetkisi
ister = OKAN KAPISI. Repodan bugun kurulabilen en az mudahaleli, izin gerektirmeyen
mekanizma: eski yolda kalan MINIMUM bir sayfa +
  <link rel="canonical" href="<hedef>">        (sinyal konsolidasyonu)
  <meta http-equiv="refresh" content="0; url=<hedef>">  (arama motoru bunu yonlendirme
                                                         sayar, kullaniciyi da tasir)
  gorunur tek link                              (JS/refresh kapaliysa cikis yolu)
🔴 `noindex` BILEREK YOK: yonlendirme sayfasina noindex koymak sinyal konsolidasyonunu
ENGELLER — arama motoru sayfayi taramayi birakirsa canonical'i da isleyemez ve eski
URL'nin degeri hedefe GECMEZ, sadece kaybolur. Eski URL'nin SERP'ten dusmesini saglayan
sey noindex degil, canonical + refresh ciftidir.
Bu tablo AYNI ZAMANDA gercek 301 kuralinin girdisidir: CF tarafi acilirsa kural listesi
elle yazilmaz, buradan URETILIR (tek kaynak).

SAYFA YUZEYI DEGIL, YONLENDIRME HARITASIDIR
-------------------------------------------
Buradaki slug metinleri pazarlama metni degildir; stub sayfalarda kapsam disi hicbir
ibare GORUNMEZ (basliklar ve gorunur metin hedeften turetilir). `tools/sayfalar.py`
ve `index.html` kapsam taramasi (tools/beyaz-esya-kapsam-test.py) bu dosyayi metin
ekseninde taramaz; bunun yerine YONLENDIRME eksenini olcer: her kayit gecerli, her
hedef kapsam ICI ve CONTENT_PAGES'te MEVCUT olmak zorundadir (404 uretmek YASAK).
"""

# (eski_slug, hedef_slug, gerekce) — hedef, eski sayfanin isini devralan EN YAKIN
# kapsam ICI sayfadir. Sirasi onemsiz; hedefler CONTENT_PAGES'te var olmak ZORUNDA.
YONLENDIRMELER = [
    ("beyaz-esya-plastik-parca-uretimi",
     "kirik-plastik-parca-yaptirma",
     "genel kirik plastik parca uretimi — eski sayfanin en genis kapsam ICI karsiligi"),
    ("elektrikli-supurge-aparati-plastik-parca-uretimi",
     "robot-supurge-plastik-parca-yaptirma",
     "supurge aparati/hortum baglantisi ayni cihaz ailesinde kapsam ICI karsilik"),
    ("bulasik-makinesi-sepet-tekerlegi-yaptirma",
     "olcuye-ozel-tekerlek-makara-uretimi",
     "sepet tekerlegi = tekerlek/makara sinifi; parca tipi ayni, kapsam ICI"),
    ("buzdolabi-raf-sebzelik-plastik-parca-yaptirma",
     "olcuye-ozel-raf-pimi-tutucu-uretimi",
     "raf tasiyici/pim sinifi; parca tipi ayni, kapsam ICI"),
    ("camasir-makinesi-kapak-parcasi-yaptirma",
     "olcuye-ozel-mentese-uretimi",
     "kapak mentesesi/mandali sinifi; parca tipi ayni, kapsam ICI"),
]

# Stub sayfa iskeleti. Gorunur metinde kapsam disi HICBIR ibare gecmez: baslik ve link
# etiketi HEDEF sayfadan gelir, eski slug yalnizca URL olarak (dizin adi) yasar.
STUB_SABLON = u"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(hedef_baslik)s — PRUVO</title>
<link rel="canonical" href="%(hedef_url)s">
<meta http-equiv="refresh" content="0; url=%(hedef_url)s">
<style>body{font-family:system-ui,-apple-system,'Segoe UI',Arial,sans-serif;margin:0;
padding:3rem 1.25rem;background:#f5f6f8;color:#12294d;line-height:1.6}
main{max-width:34rem;margin:0 auto;background:#fff;border-radius:.75rem;padding:2rem;
box-shadow:0 1px 3px rgba(18,41,77,.12)}h1{font-size:1.25rem;margin:0 0 .75rem}
a{color:#12294d;font-weight:600}</style>
</head>
<body>
<main>
<h1>Bu sayfa taşındı</h1>
<p>Aradığınız içerik şu sayfada devam ediyor:
<a href="%(hedef_url)s">%(hedef_baslik)s</a>.</p>
</main>
</body>
</html>
"""


def hedef_haritasi():
    """{eski_slug: hedef_slug} — CF Redirect Rules uretimi de bunu kullanir."""
    return {eski: hedef for eski, hedef, _g in YONLENDIRMELER}


def dogrula(content_pages):
    """(hata_listesi, kayit_sayisi) — her hedef CONTENT_PAGES'te MEVCUT mu.

    Hedefi olmayan bir kayit stub'i 404'e yonlendirir; fail-closed sayilir.
    """
    mevcut = {slug for slug, _b, _m, _f in content_pages}
    hatalar = []
    for eski, hedef, _g in YONLENDIRMELER:
        if hedef not in mevcut:
            hatalar.append("hedef CONTENT_PAGES'te YOK: %s -> %s" % (eski, hedef))
        if eski in mevcut:
            hatalar.append("eski slug HALA uretiliyor (yonlendirme ile cakisiyor): %s" % eski)
        if eski == hedef:
            hatalar.append("kendine yonlendirme: %s" % eski)
    return hatalar, len(YONLENDIRMELER)


def stub_html(eski_slug, content_pages, site):
    """Eski slug icin yonlendirme sayfasinin HTML'i."""
    basliklar = {slug: baslik for slug, baslik, _m, _f in content_pages}
    hedef = hedef_haritasi()[eski_slug]
    return STUB_SABLON % {
        "hedef_url": site + "/" + hedef + "/",
        "hedef_baslik": basliklar[hedef],
    }


def dizinler():
    """Yayin manifestine (`_yayin-icerik-dizinleri.txt`) girecek dizin adlari.

    sitemap'e GIRMEZ: yonlendirme sayfasi indekslenecek icerik degildir.
    """
    return [eski for eski, _h, _g in YONLENDIRMELER]
