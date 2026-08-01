#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""YAYIN YUZEYI — bir sayfanin TARAYICIDA GECERLI OLAN tam govdesi, TEK METIN.

NEDEN VAR (2 Agu 2026): urun sayfasinin ortak CSS/JS'i sayfaya gomulu olmaktan cikip
icerik-adresli /varlik/<ad>-<hash>.<uz> dosyalarina tasindi. Sayfanin HTML'ini okuyup
`<style>`/`<script>` govdesinde kural arayan kapilar (konfigur-test, eski-fiyat-test,
meta-piksel-test, piksel-katalog-parite-test ...) o an SESSIZCE korelir: aradiklari kod
hala tarayiciya iniyordur ama ARTIK BAKTIKLARI METINDE DEGILDIR. Olcum yuzeyi kucuulur,
kapi yine yesil yanar — bu depoda olculmus "kapi kapsam" hata sinifi.

COZUM TEK KAYNAK: kapi HTML'i okurken bu fonksiyondan gecirir. Fonksiyon /varlik/
referanslarini ICERIKLERIYLE degistirir; sonuc, blok tasinmadan ONCEKI sayfayla ayni
kurallari tasiyan tek bir metindir. Her kapinin kendi "varligi da oku" kopyasini
yazmasi ikiz tanimdir ([[ikiz-tanim-sessiz-ayrisma]]).

FAIL-CLOSED: referans edilen varlik dosyasi diskte YOKSA hata firlatir. Sessizce
"referansi atla" demek, ciplak sayfayi yesil gostermek olurdu.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARLIK_DIR_ADI = "varlik"
VARLIK_URL_ONEK = "/" + VARLIK_DIR_ADI + "/"

_CSS_LINK_RE = re.compile(r'<link rel="stylesheet" href="(' + re.escape(VARLIK_URL_ONEK)
                          + r'[^"]+)">')
_JS_SRC_RE = re.compile(r'<script\b[^>]*\ssrc="(' + re.escape(VARLIK_URL_ONEK)
                        + r'[^"]+)"[^>]*>\s*</script>')


class VarlikYok(RuntimeError):
    pass


def _oku(url, kok):
    yol = os.path.join(kok, url.lstrip("/").split("?")[0])
    if not os.path.isfile(yol):
        raise VarlikYok("referans edilen varlik diskte YOK: %s (%s)" % (url, yol))
    with open(yol, encoding="utf-8") as f:
        return f.read()


def govde(html, kok=None):
    """Sayfayi, /varlik/ referanslari YERINE KONMUS haliyle doner.

    CSS referansi <style>...</style>, JS referansi <script>...</script> olur -> mevcut
    kapilarin `<style>`/`<script>` govdesi arayan olcumleri tasima ONCESI ne olcuyorsa
    AYNISINI olcer."""
    kok = kok or ROOT
    s = _CSS_LINK_RE.sub(lambda m: "<style>" + _oku(m.group(1), kok) + "</style>", html)
    s = _JS_SRC_RE.sub(lambda m: "<script>" + _oku(m.group(1), kok) + "</script>", s)
    return s


def varlik_referanslari(html):
    """Sayfadaki /varlik/ adresleri (olcum kapsaminin BOSA DUSMEDIGINI yoklamak icin)."""
    return _CSS_LINK_RE.findall(html) + _JS_SRC_RE.findall(html)
