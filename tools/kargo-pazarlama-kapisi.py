#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gorunur pazarlama yuzeyinde kargo ucreti/bedava-esik vaadini engeller.

Yasal muafiyet listesi bu dosyada tutulmaz; sayfalar.YASAL_SAYFALAR tek kaynaktir.
Script/style/comment govdeleri gorunur metin sayilmaz. Ana sayfa, kurumsal statik
sayfalar ve CONTENT_PAGES ortak render yoluyla taranir.
"""

import argparse
import hashlib
import os
import re
import sys
from html.parser import HTMLParser

import build
import sayfalar


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KARGO = r"\bkargo(?:nun|yu|ya|yla|lu|suz)?\b"
VAAT = (
    r"(?:ucretsiz|ücretsiz|bedava|ucret(?:i|li|siz)?|ücret(?:i|li|siz)?|"
    r"esik|eşik|\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})?\s*tl)"
)
VAAT_DESENLERI = (
    re.compile(KARGO + r"[^.!?\n]{0,80}" + VAAT, re.IGNORECASE),
    re.compile(VAAT + r"[^.!?\n]{0,80}" + KARGO, re.IGNORECASE),
)


class GorunurMetin(HTMLParser):
    """HTML'den yalniz kullanicinin gordugu metni cikarir."""

    GIZLI = {"script", "style", "template", "noscript"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.gizli_derinlik = 0
        self.parcalar = []

    def handle_starttag(self, tag, attrs):
        if tag.casefold() in self.GIZLI:
            self.gizli_derinlik += 1
        elif not self.gizli_derinlik and tag.casefold() in {
                "br", "div", "p", "li", "section", "aside", "header", "footer"}:
            self.parcalar.append("\n")

    def handle_endtag(self, tag):
        if tag.casefold() in self.GIZLI:
            if self.gizli_derinlik:
                self.gizli_derinlik -= 1
        elif not self.gizli_derinlik and tag.casefold() in {
                "div", "p", "li", "section", "aside", "header", "footer"}:
            self.parcalar.append("\n")

    def handle_data(self, data):
        if not self.gizli_derinlik:
            self.parcalar.append(data)

    def metin(self):
        return re.sub(r"[ \t\r\f\v]+", " ", "".join(self.parcalar)).casefold()


def gorunur_metin(html):
    ayristirici = GorunurMetin()
    ayristirici.feed(html)
    return ayristirici.metin()


def ihlaller(html):
    metin = gorunur_metin(html)
    bulunan = []
    for desen in VAAT_DESENLERI:
        for eslesme in desen.finditer(metin):
            ifade = re.sub(r"\s+", " ", eslesme.group(0)).strip()
            if ifade not in bulunan:
                bulunan.append(ifade)
    return bulunan


def dosya_oku(yol):
    with open(yol, encoding="utf-8") as dosya:
        return dosya.read()


def yuzeyleri_bul(index_override=None, content_override=None):
    """(ad, html, yasal_mi) uclusu; muafiyet kanonik YASAL_SAYFALAR'dan gelir."""
    yasal = set(sayfalar.YASAL_SAYFALAR)
    yuzeyler = [("index.html", index_override if index_override is not None else
                 dosya_oku(os.path.join(ROOT, "index.html")), False)]

    for slug in sayfalar.STATIK_SAYFALAR:
        tam = os.path.join(ROOT, slug, "index.html")
        yuzeyler.append((slug, dosya_oku(tam), slug in yasal))

    overrides = content_override or {}
    for slug, title, meta, fn in sayfalar.CONTENT_PAGES:
        govde = fn()
        html = build.render_content_page(slug, title, meta, govde)
        if slug in overrides:
            html = overrides[slug]
        yuzeyler.append((slug, html, slug in yasal))
    return yuzeyler


def olc(index_override=None, content_override=None, ayrintili=True):
    yuzeyler = yuzeyleri_bul(index_override, content_override)
    pazarlama = []
    yasal_isabet = []
    for ad, html, yasal_mi in yuzeyler:
        bulunan = ihlaller(html)
        if not bulunan:
            continue
        if yasal_mi:
            yasal_isabet.append((ad, bulunan))
        else:
            pazarlama.append((ad, bulunan))

    if ayrintili:
        print("YASAL_MUAF_KANONIK=%d (%s)" % (
            len(sayfalar.YASAL_SAYFALAR), ",".join(sayfalar.YASAL_SAYFALAR)))
        print("PAZARLAMA_YUZEYI=%d" % sum(not yasal for _ad, _html, yasal in yuzeyler))
        print("KARGO_PAZARLAMA_IHLALI=%d" % len(pazarlama))
        print("KARGO_YASAL_MUAF_ISABET=%d" % len(yasal_isabet))
        for ad, bulunan in pazarlama:
            print("KIRMIZI: %s -> %s" % (ad, " | ".join(bulunan)))
        for ad, _bulunan in yasal_isabet:
            print("YASAL_MUAF: %s" % ad)
    return pazarlama, yasal_isabet


def sha256(yol):
    with open(yol, "rb") as dosya:
        return hashlib.sha256(dosya.read()).hexdigest()


def kendini_test():
    """Kargo geri-mutanti kirmizi; yasal mutant yanlis-pozitif uretmez."""
    izlenen = [os.path.join(ROOT, "index.html"), os.path.join(ROOT, "tools", "sayfalar.py")]
    once = {yol: sha256(yol) for yol in izlenen}
    index_html = dosya_oku(izlenen[0])
    geri_mutant = index_html.replace(
        "</header>",
        '<div class="kargo-mutant">2.500 TL ve üzeri siparişlerde kargo ücretsiz</div>'
        "</header>", 1)
    kirmizi, _yasal = olc(index_override=geri_mutant, ayrintili=False)
    mutant_kargo = bool(kirmizi)

    teslimat = next(
        build.render_content_page(slug, title, meta, fn())
        for slug, title, meta, fn in sayfalar.CONTENT_PAGES
        if slug == "teslimat-iade"
    )
    yasal_mutant = teslimat.replace(
        "</main>",
        "<p>2.500 TL ve üzeri siparişlerde kargo ücretsiz</p></main>", 1)
    kirmizi_yasal, _muaf = olc(
        content_override={"teslimat-iade": yasal_mutant}, ayrintili=False)
    mutant_yasal = not kirmizi_yasal

    sonra = {yol: sha256(yol) for yol in izlenen}
    sha_esit = once == sonra
    print("MUTANT_KARGO_GERI=%s" % (
        "KIRMIZI_YAKTI" if mutant_kargo else "YAKMADI"))
    print("MUTANT_YANLIS_POZITIF_YASAL=%s" % (
        "YAKMADI" if mutant_yasal else "YAKTI"))
    print("SHA256_GERI_ALIM=%s" % ("ESIT" if sha_esit else "FARKLI"))
    if mutant_kargo and mutant_yasal and sha_esit:
        print("SONUC: YESIL — iki mutant yonu olculdu")
        return 0
    print("SONUC: KIRMIZI — mutant kabulunde eksik var")
    return 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kendini-test", action="store_true")
    args = parser.parse_args()
    if args.kendini_test:
        return kendini_test()
    pazarlama, _yasal = olc()
    if pazarlama:
        print("SONUC: KIRMIZI — pazarlama yuzeyinde kargo ucreti/bedava-esik vaadi var")
        return 1
    print("SONUC: YESIL — pazarlama yuzeyinde kargo ucreti/bedava-esik vaadi yok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
