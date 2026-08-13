#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""arama.py araç eş anlamlılarının lazy ve fail-closed yükleme kabul testi."""

import importlib.util
import json
import os
import shutil
import sys
import tempfile


TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
SONUCLAR = []


def modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def kontrol(kod, kosul, mesaj):
    SONUCLAR.append(bool(kosul))
    print(("  OK   " if kosul else "  HATA ") + "%s %s" % (kod, mesaj))


def arac_kopyasi(kok):
    os.makedirs(os.path.join(kok, "tools"))
    shutil.copy(os.path.join(TOOLS, "arama.py"), os.path.join(kok, "tools", "arama.py"))
    return os.path.join(kok, "tools", "arama.py")


def kanonik_index_yaz(kok):
    with open(os.path.join(kok, "index.html"), "w", encoding="utf-8") as f:
        f.write('var ARAC_ES_ANLAMLI = ["oto", "otomobil", "araba", "arac"];\n')
        f.write('var ARAC_ES_ANLAMLI_SINIR = "[^a-z0-9]";\n')


def a1():
    kok = tempfile.mkdtemp(prefix="arama-lazy-a1-")
    try:
        arama_yolu = arac_kopyasi(kok)
        shutil.copy(os.path.join(TOOLS, "duzelt.py"), os.path.join(kok, "tools", "duzelt.py"))
        shutil.copy(os.path.join(TOOLS, "gorsel_koken.py"),
                    os.path.join(kok, "tools", "gorsel_koken.py"))
        arama = modul_yukle(arama_yolu, "arama_lazy_a1")
        duzelt = modul_yukle(os.path.join(kok, "tools", "duzelt.py"), "duzelt_lazy_a1")
        kontrol("A1", arama is not None and duzelt is not None,
                "index.html olmadan arama.py ve duzelt.py import edildi")
    except Exception as hata:
        kontrol("A1", False, "import coktu: %s" % hata)
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def a2():
    try:
        arama = modul_yukle(os.path.join(TOOLS, "arama.py"), "arama_lazy_a2")
        with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
            urunler = json.load(f)
        token = arama.tokenlar("audi araba")
        adet = sum(1 for urun in urunler if arama.esles(arama.haystack(urun), token))
        kontrol("A2", arama._ARAC_ES_ANLAMLI_YUKLENDI is True and adet > 0,
                "kanonik genisleme calisti; audi araba sonucu=%d" % adet)
    except Exception as hata:
        kontrol("A2", False, "kanonik genisleme coktu: %s" % hata)


def a3():
    kok = tempfile.mkdtemp(prefix="arama-lazy-a3-")
    try:
        arama = modul_yukle(arac_kopyasi(kok), "arama_lazy_a3")
        import_sonrasi = arama._ARAC_ES_ANLAMLI_YUKLENDI
        kanonik_index_yaz(kok)
        token = arama.tokenlar("araba")
        kontrol("A3", import_sonrasi is None and arama._ARAC_ES_ANLAMLI_YUKLENDI is True
                and any(isinstance(t, tuple) for t in token),
                "import dosya okumadi; ilk kullanim sonradan olusan index'i yukledi")
    except Exception as hata:
        kontrol("A3", False, "lazy davranis coktu: %s" % hata)
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def a4():
    eksik = tempfile.mkdtemp(prefix="arama-lazy-a4-eksik-")
    bozuk = tempfile.mkdtemp(prefix="arama-lazy-a4-bozuk-")
    try:
        arama_eksik = modul_yukle(arac_kopyasi(eksik), "arama_lazy_a4_eksik")
        eksik_token = arama_eksik.tokenlar("araba")
        arac_kopyasi(bozuk)
        with open(os.path.join(bozuk, "index.html"), "w", encoding="utf-8") as f:
            f.write('var ARAC_ES_ANLAMLI = [bozuk];\n')
            f.write('var ARAC_ES_ANLAMLI_SINIR = "[^a-z0-9]";\n')
        arama_bozuk = modul_yukle(os.path.join(bozuk, "tools", "arama.py"),
                                  "arama_lazy_a4_bozuk")
        bozuk_token = arama_bozuk.tokenlar("araba")
        durum = (arama_eksik._ARAC_ES_ANLAMLI_YUKLENDI is False
                 and arama_bozuk._ARAC_ES_ANLAMLI_YUKLENDI is False
                 and not any(isinstance(t, tuple) for t in eksik_token + bozuk_token))
        kontrol("A4", durum,
                "eksik/bozuk veride surec ayakta, genisleme kapali ve durum gorunur")
    except Exception as hata:
        kontrol("A4", False, "fail-closed yolu coktu: %s" % hata)
    finally:
        shutil.rmtree(eksik, ignore_errors=True)
        shutil.rmtree(bozuk, ignore_errors=True)


def main():
    a1()
    a2()
    a3()
    a4()
    gecen = sum(SONUCLAR)
    print("SONUC: %d/%d iddia GECTI" % (gecen, len(SONUCLAR)))
    return 0 if gecen == len(SONUCLAR) else 1


if __name__ == "__main__":
    sys.exit(main())
