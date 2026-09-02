#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gorunur pazarlama yuzeyinde kargo ucreti/bedava-esik vaadini engeller.

Yasal muafiyet listesi bu dosyada tutulmaz; sayfalar.YASAL_SAYFALAR tek kaynaktir.
Style/comment govdeleri gorunur metin sayilmaz. Sepet gibi JavaScript'in kullaniciya
yazdigi metin dizgeleri de taranir. Ana sayfa, kurumsal statik sayfalar ve CONTENT_PAGES
ortak render yoluyla taranir.

🔴 TEK DAR MUAFIYET — ANA SAYFA HEADER KARGO ROZETI (2 Eyl 2026, Okan pencereden onayladi,
BaBa hukmu; 9 Agu `6f8e0fe8` "kargo pazarlama rozetini kaldir" karari YALNIZ BU SATIR icin
gecersizdir, kural baska her yuzeyde AYNEN yururluktedir):
  Header guven blogu V5'te "2.500 TL uzeri ucretsiz kargo" metni KALIR; ama kapi GEVSETILMEZ,
  muafiyet DARALIR ve id + KAYNAK ekseniyle olculur (`kargo_rozet_muafiyeti`):
    M1 index.html'de `getElementById("hgKargoMetinYazi")` cagiran script blogu TAM 1 adet
    M2 o blok esigi `PRUVO_SECENEK` . `KARGO_BEDAVA_ESIK_KURUS`'tan OKUR (tek kaynak:
       secenekler.js — Worker'in tahsil ettigi sabit; elle sayi YOK)
    M3 blokta 4+ haneli sayi literali YOK (`|| 250000` gibi elle yedek de yasak)
    M4 blogun HICBIR dizgesinde rakam yok (metin "<eşik> TL uzeri ucretsiz kargo" seklinde
       CALISMA ANINDA birlesir; "2.500" kaynakta YAZILMAZ)
    M5 `<span id="hgKargoMetinYazi">` kaynakta BOS ve TAM 1 kez (gorunur metin ekseni
       zaten dolu span'i yakalar; ikinci kopya da burada duser)
  Bes kosuldan biri tutmazsa muafiyet YOKTUR ve blok herkes gibi taranir (fail-closed).
  Muaf olan YALNIZ o bloktaki dizgelerdir: ayni dizge baska bir blokta/sepette gecerse
  KIRMIZI. `--kendini-test` dort mutantla (elle rakam / baska id / ikinci kopya / kaynak
  kopuk) muafiyetin daralmadigini her push'ta yeniden olcer; onceki uc mutant da durur.
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


_SCRIPT_GOVDE_RE = re.compile(r"<script(?:\s[^>]*)?>(.*?)</script\s*>",
                              re.IGNORECASE | re.DOTALL)


def script_govdeleri(html):
    """Sayfadaki <script> govdeleri, kaynak sirasiyla (blok indeksi muafiyet anahtaridir)."""
    return _SCRIPT_GOVDE_RE.findall(html)


def dizgeleri_ayir(kaynak):
    """TEK script govdesindeki JS dizgelerini yorumlardan ayirarak dondurur (casefold)."""
    bulunan = []
    i = 0
    while i < len(kaynak):
        if kaynak.startswith("//", i):
            son = kaynak.find("\n", i + 2)
            i = len(kaynak) if son < 0 else son + 1
            continue
        if kaynak.startswith("/*", i):
            son = kaynak.find("*/", i + 2)
            i = len(kaynak) if son < 0 else son + 2
            continue
        tirnak = kaynak[i]
        if tirnak not in "\"'`":
            i += 1
            continue
        i += 1
        parcalar = []
        while i < len(kaynak):
            karakter = kaynak[i]
            if karakter == "\\" and i + 1 < len(kaynak):
                parcalar.append(" " if kaynak[i + 1] in "nrt" else kaynak[i + 1])
                i += 2
                continue
            if karakter == tirnak:
                i += 1
                break
            parcalar.append(karakter)
            i += 1
        bulunan.append("".join(parcalar).casefold())
    return bulunan


def javascript_dizgeleri(html):
    """Script govdelerindeki JS dizgelerini yorumlardan ayirarak dondurur (tum bloklar)."""
    bulunan = []
    for kaynak in script_govdeleri(html):
        bulunan.extend(dizgeleri_ayir(kaynak))
    return bulunan


# --- Header kargo rozeti DAR muafiyeti (2 Eyl 2026 hukmu; gerekce dosya basliginda) ---
KARGO_ROZET_ID = "hgKargoMetinYazi"
KARGO_ESIK_SABITI = "KARGO_BEDAVA_ESIK_KURUS"
KARGO_ESIK_KAYNAGI = "PRUVO_SECENEK"
_ROZET_ID_CAGRISI = re.compile(r'getElementById\(\s*["\']' + KARGO_ROZET_ID + r'["\']\s*\)')
_ROZET_BOS_SPAN = re.compile(r'<span\s+id="' + KARGO_ROZET_ID + r'"\s*>\s*</span>')
_ROZET_ID_GECIS = re.compile(r'id="' + KARGO_ROZET_ID + r'"')
_UZUN_SAYI = re.compile(r"\d{4,}")
_RAKAM = re.compile(r"\d")


def kargo_rozet_muafiyeti(html):
    """(muaf_blok_indeksi | None, gerekce). M1-M5 kosullari (dosya basligi); biri tutmazsa
    None doner ve HICBIR blok muaf sayilmaz — yon fail-closed."""
    govdeler = script_govdeleri(html)
    adaylar = [i for i, g in enumerate(govdeler) if _ROZET_ID_CAGRISI.search(g)]
    if len(adaylar) != 1:
        return None, "M1 rozet script blogu sayisi %d (tam 1 olmali)" % len(adaylar)
    i = adaylar[0]
    g = govdeler[i]
    if KARGO_ESIK_SABITI not in g or KARGO_ESIK_KAYNAGI not in g:
        return None, "M2 blok esigi %s.%s'tan okumuyor" % (KARGO_ESIK_KAYNAGI, KARGO_ESIK_SABITI)
    if _UZUN_SAYI.search(g):
        return None, "M3 blokta 4+ haneli sayi literali var (elle esik/yedek)"
    for dizge in dizgeleri_ayir(g):
        if _RAKAM.search(dizge):
            return None, "M4 blok dizgesinde rakam var: %r" % dizge
    if len(_ROZET_BOS_SPAN.findall(html)) != 1 or len(_ROZET_ID_GECIS.findall(html)) != 1:
        return None, "M5 <span id=%s> kaynakta BOS ve tam 1 kez olmali" % KARGO_ROZET_ID
    return i, "muaf: yalniz script blogu #%d" % i


def ihlaller(html):
    bulunan = []
    muaf_blok, _gerekce = kargo_rozet_muafiyeti(html)
    metinler = [gorunur_metin(html)]
    for i, govde in enumerate(script_govdeleri(html)):
        if i == muaf_blok:
            continue
        metinler.extend(dizgeleri_ayir(govde))
    for metin in metinler:
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
        muaf_blok, gerekce = kargo_rozet_muafiyeti(yuzeyler[0][1])
        print("KARGO_ROZET_MUAFIYET=%s (%s)" % (
            "YOK" if muaf_blok is None else "BLOK_%d" % muaf_blok, gerekce))
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
    """Sepet geri-mutanti kirmizi; yasal/tahsilat metni yanlis-pozitif uretmez."""
    izlenen = [os.path.join(ROOT, "index.html"), os.path.join(ROOT, "tools", "sayfalar.py")]
    once = {yol: sha256(yol) for yol in izlenen}
    index_html = dosya_oku(izlenen[0])
    capa = 'lines.push("Ara toplam: " + PRUVO_SECENEK.kurusMetni(toplam));'
    geri_mutant = index_html.replace(
        capa, capa + '\n      lines.push("2.500 TL üzeri kargo bedava");', 1)
    mutant_capa = geri_mutant != index_html
    kirmizi, _yasal = olc(index_override=geri_mutant, ayrintili=False)
    mutant_kargo = mutant_capa and bool(kirmizi)

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
    mutant_tahsilat = not ihlaller(
        '<div><span>Gönderim</span><span>250,00 TL</span></div>'
        '<script>lines.push("Gönderim: " + kurusMetni(kargo));</script>')

    # --- Header kargo rozeti DAR muafiyeti (2 Eyl): kontrol YESIL, dort mutant KIRMIZI ---
    # Kontrol: dokunulmamis kaynak muafiyetle YESIL olmali; yoksa mutantlarin kirmizisi
    # "her sey kirmizi" totolojisidir ([[fikstur-degeri-mutasyon-koru]]).
    kontrol_kirmizi, _k = olc(index_override=index_html, ayrintili=False)
    rozet_kontrol = (kargo_rozet_muafiyeti(index_html)[0] is not None
                     and not kontrol_kirmizi)
    rozet_capa = '" TL üzeri ücretsiz kargo"'
    rozet_id_capa = 'getElementById("%s")' % KARGO_ROZET_ID
    rozet_blok = next(("<script>%s</script>" % g for g in script_govdeleri(index_html)
                       if _ROZET_ID_CAGRISI.search(g)), None)
    capalar_var = (rozet_capa in index_html and rozet_id_capa in index_html
                   and rozet_blok is not None and rozet_blok in index_html
                   and "S." + KARGO_ESIK_SABITI in index_html)

    def _mutant_kirmizi(metin):
        kirmizi_m, _y = olc(index_override=metin, ayrintili=False)
        return metin != index_html and bool(kirmizi_m)

    m_rakam = _mutant_kirmizi(index_html.replace(
        rozet_capa, '"2.500 TL üzeri ücretsiz kargo"', 1)) if capalar_var else False
    m_id = _mutant_kirmizi(index_html.replace(
        rozet_id_capa, 'getElementById("%sX")' % KARGO_ROZET_ID, 1)) if capalar_var else False
    m_kopya = _mutant_kirmizi(index_html.replace(
        rozet_blok, rozet_blok + "\n" + rozet_blok, 1)) if capalar_var else False
    m_kaynak = _mutant_kirmizi(index_html.replace(
        "S." + KARGO_ESIK_SABITI, "250000")) if capalar_var else False

    sonra = {yol: sha256(yol) for yol in izlenen}
    sha_esit = once == sonra
    print("MUTANT_KARGO_GERI=%s" % (
        "KIRMIZI_YAKTI" if mutant_kargo else "YAKMADI"))
    print("MUTANT_YANLIS_POZITIF_YASAL=%s" % (
        "YAKMADI" if mutant_yasal else "YAKTI"))
    print("MUTANT_YANLIS_POZITIF_TAHSILAT=%s" % (
        "YAKMADI" if mutant_tahsilat else "YAKTI"))
    print("ROZET_CAPALAR=%s" % ("VAR" if capalar_var else "YOK"))
    print("ROZET_KONTROL_YESIL=%s" % ("EVET" if rozet_kontrol else "HAYIR"))
    print("MUTANT_ROZET_ELLE_RAKAM=%s" % ("KIRMIZI_YAKTI" if m_rakam else "YAKMADI"))
    print("MUTANT_ROZET_BASKA_ID=%s" % ("KIRMIZI_YAKTI" if m_id else "YAKMADI"))
    print("MUTANT_ROZET_IKINCI_KOPYA=%s" % ("KIRMIZI_YAKTI" if m_kopya else "YAKMADI"))
    print("MUTANT_ROZET_KAYNAK_KOPUK=%s" % ("KIRMIZI_YAKTI" if m_kaynak else "YAKMADI"))
    print("SHA256_GERI_ALIM=%s" % ("ESIT" if sha_esit else "FARKLI"))
    if (mutant_kargo and mutant_yasal and mutant_tahsilat and sha_esit
            and capalar_var and rozet_kontrol and m_rakam and m_id and m_kopya and m_kaynak):
        print("SONUC: YESIL — uc eski + dort rozet mutanti ve kontrol olculdu")
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
