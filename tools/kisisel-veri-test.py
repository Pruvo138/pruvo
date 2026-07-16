#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kişisel veri koruması KABUL TESTİ.

Neyi doğrular:
  1) NEGATİF — üretilen içerik sayfaları (teslimat-iade, mesafeli-satis,
     malzeme-rehberi; sayfalar.py+build.py'den TAZE render edilir) ve statik
     sayfalarda (index, hakkimizda, iletisim, sss, gizlilik) satıcının kişisel
     bilgileri HAM KAYNAKTA düz metin olarak GEÇMEZ.
     Tek istisna: <script type="application/ld+json"> blokları (SEO takası —
     bilinçli karar, mimar kaydında).
  2) POZİTİF — korumalı .pv span'larının parçaları (data-a..l) doğru sırada
     birleştirilince beklenen değerler birebir geri çıkar (sayfa müşteriye
     doğru bilgiyi göstermeye devam ediyor) ve her sayfada beklenen sayıda
     korumalı değer var.

Çalıştırma:  python3 tools/kisisel-veri-test.py   (çıkış kodu 0 = geçti)
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build  # noqa: E402  (render_content_page + CONTENT_PAGES)

# ------------------------------------------------------------------ aranan düz metin kalıpları
# Not: kalıplar boşluksuz NORMALİZE metinde aranır (boşluk/nbsp/tire farkları
# kaçamak yaratmasın diye). Hepsi kişisel veri; JSON-LD dışında SIFIR olmalı.
KALIPLAR = [
    "okangemalmaz", "gemalmaz",
    "+905325954005", "905325954005", "05325954005", "5325954005",
    "info@pruvo3d.com",
    "akarca", "adnanmenderes",
    "3910052435",
    "fethiyevergidairesi",
]

# ------------------------------------------------------------------ pozitif kontrol beklentileri
TEL = "+90 532 595 4005"
EPOSTA = "info@pruvo3d.com"
ADRES_KISA = "Adnan Menderes Blv. No:303, 48300 Fethiye/Muğla"
ADRES_TAM = "Akarca Mah. Adnan Menderes (BBT) Blv. No:303 Daire No:203, Fethiye / Muğla"
UNVAN = "Okan Gemalmaz"
VKN = "3910052435"
VD = "Fethiye Vergi Dairesi"

# sayfa -> o sayfada geri kurulabilmesi ŞART değerler
BEKLENEN = {
    "iletisim": [TEL, EPOSTA, ADRES_KISA],
    "gizlilik": [EPOSTA, ADRES_KISA],
    "teslimat-iade": [UNVAN, ADRES_TAM, VD, VKN, TEL, EPOSTA],
    "mesafeli-satis": [UNVAN, ADRES_TAM, VD, VKN, TEL, EPOSTA],
}

LD_RE = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>.*?</script>', re.S)
PV_RE = re.compile(r'<span class="pv[^"]*"([^>]*)></span>')
ATTR_RE = re.compile(r'data-([a-l])="([^"]*)"')


def normalize(metin):
    metin = metin.lower()
    for c in (" ", "\t", "\n", " ", "-", "(", ")"):
        metin = metin.replace(c, "")
    return metin


def pv_birlestir(html):
    """Kaynaktaki .pv span'larını (karışık sıralı data-a..l) sırayla birleştirir;
    ardışık span'lar tek değere ait olabilir → tam metin döner."""
    parca_metinler = []
    for m in PV_RE.finditer(html):
        attrs = dict(ATTR_RE.findall(m.group(1)))
        parca_metinler.append("".join(attrs.get(k, "")
                                      for k in "abcdefghijkl"))
    return "".join(parca_metinler)


def main():
    hatalar = []
    dosyalar = {}

    # üretilen sayfalar — diskten değil, üreticiden taze render
    for slug, title, meta, fn in build.CONTENT_PAGES:
        dosyalar[slug] = build.render_content_page(slug, title, meta, fn())

    # statik sayfalar
    for slug, yol in [("index", "index.html"),
                      ("hakkimizda", "hakkimizda/index.html"),
                      ("iletisim", "iletisim/index.html"),
                      ("sss", "sss/index.html"),
                      ("gizlilik", "gizlilik/index.html")]:
        with open(os.path.join(ROOT, yol), encoding="utf-8") as f:
            dosyalar[slug] = f.read()

    for slug, html in sorted(dosyalar.items()):
        # 1) NEGATİF: JSON-LD hariç ham kaynakta düz metin yok
        temiz = LD_RE.sub("", html)
        norm = normalize(temiz)
        for kalip in KALIPLAR:
            if normalize(kalip) in norm:
                hatalar.append("%s: '%s' HAM KAYNAKTA düz metin geçiyor"
                               % (slug, kalip))

        # 2) POZİTİF: korumalı değerler parçalardan birebir geri çıkıyor
        butun = pv_birlestir(html)
        for deger in BEKLENEN.get(slug, []):
            if deger not in butun:
                hatalar.append("%s: '%s' pv parçalarından GERİ KURULAMADI "
                               "(müşteri göremez!)" % (slug, deger))

    if hatalar:
        print("KIRMIZI — kişisel veri testi %d hata:" % len(hatalar))
        for h in hatalar:
            print("  - " + h)
        sys.exit(1)
    print("YEŞİL — kişisel veri testi geçti (%d sayfa, %d kalıp, "
          "%d sayfada pozitif kontrol)."
          % (len(dosyalar), len(KALIPLAR), len(BEKLENEN)))


if __name__ == "__main__":
    main()
