#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Üretilen bütün CONTENT_PAGES sayfalarında doğru, ön-dolu WhatsApp CTA'sı."""

import sys
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

import build


WA_NUMARA = "905451386526"


class BaglantiAyristirici(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefler = []

    def handle_starttag(self, tag, attrs):
        if tag.casefold() != "a":
            return
        ozellikler = dict(attrs)
        if ozellikler.get("href"):
            self.hrefler.append(ozellikler["href"])


def wa_baglantilari(html):
    ayristirici = BaglantiAyristirici()
    ayristirici.feed(html)
    return [href for href in ayristirici.hrefler if "wa.me" in href.casefold()]


def main():
    if not build.CONTENT_PAGES:
        print("KIRMIZI: CONTENT_PAGES bos; landing yuzeyi olculemedi")
        return 1

    eksik = []
    yanlis_numara = []
    toplam = 0
    dogru = 0

    for slug, title, meta, fn in build.CONTENT_PAGES:
        try:
            html = build.render_content_page(slug, title, meta, fn())
        except Exception as hata:
            print("KIRMIZI: %s render edilemedi -> %r" % (slug, hata))
            return 1
        toplam += 1
        hrefler = wa_baglantilari(html)
        sayfa_dogru = False
        for href in hrefler:
            adres = urlparse(href)
            numara = adres.path.strip("/")
            if numara != WA_NUMARA:
                yanlis_numara.append("%s:%s" % (slug, numara or "BOS"))
                continue
            mesaj = parse_qs(adres.query, keep_blank_values=True).get("text", [""])[0].strip()
            if not mesaj:
                continue
            sayfa_dogru = True
        if sayfa_dogru:
            dogru += 1
        else:
            eksik.append(slug)

    print("LANDING_TOPLAM=%d" % toplam)
    print("WA_LINKI_OLAN=%d" % dogru)
    print("WA_LINKI_OLMAYAN=%d" % len(eksik))
    print("YASAK_4005_WA_ICINDE=%d" % sum("4005" in x for x in yanlis_numara))
    if eksik:
        print("KIRMIZI: dogru ve on-dolu WhatsApp CTA'si olmayan: %s" % ", ".join(eksik))
    if yanlis_numara:
        print("KIRMIZI: wa.me icinde yanlis numara: %s" % ", ".join(yanlis_numara))
    if eksik or yanlis_numara:
        return 1
    print("SONUC: YESIL — tum landing sayfalari dogru numarali, on-dolu WhatsApp CTA'si tasiyor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
