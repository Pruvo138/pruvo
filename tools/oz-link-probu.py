# -*- coding: utf-8 -*-
"""OZ-LINK PROBU — bir icerik sayfasi KENDI URL'ine link veriyor mu.

Kapsam temizliginde olculdu: bir ic-link kaldirilip yerine kapsam ICI hedef konurken
hedef yanlislikla SAYFANIN KENDISI secilebiliyor ("o parcalari <a href='/bu-sayfa/'>bu
sayfada</a> topladik"). Okur icin olu dongudur, arama motoru icin degersiz sinyaldir.
  python3 tools/oz-link-probu.py           # rc=1 ise oz-link VAR, adiyla basar
"""
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "tools"))


def tara(sayfalar_listesi):
    """[(slug, oz_link_sayisi)] — kendi URL'ine link veren sayfalar."""
    bulgu = []
    for slug, _baslik, _meta, fn in sayfalar_listesi:
        govde = fn() if callable(fn) else str(fn)
        n = len(re.findall(r'href="/%s/"' % re.escape(slug), govde))
        if n:
            bulgu.append((slug, n))
    return bulgu


def _kendini_test():
    """IZOLE fikstur: mutant KIRMIZI yakmali, kontrol YESIL kalmali."""
    kirli = [("a-sayfasi", "A", "m", lambda: '<a href="/a-sayfasi/">buraya</a>')]
    temiz = [("a-sayfasi", "A", "m", lambda: '<a href="/b-sayfasi/">buraya</a>')]
    # benzer ONEKLI slug oz-link SAYILMAZ (yanlis-pozitif kolu)
    onek = [("a-sayfasi", "A", "m", lambda: '<a href="/a-sayfasi-uzun/">buraya</a>')]
    hata = 0
    for ad, fikstur, beklenen in (("M1 sayfa kendine link verdi", kirli, True),
                                  ("K1 baska sayfaya link", temiz, False),
                                  ("K2 onek-benzeri slug oz-link DEGIL", onek, False)):
        var = bool(tara(fikstur))
        if var == beklenen:
            print("  ✅ %s" % ad)
        else:
            print("  ❌ DUSTU — %s (beklenen=%s, olculen=%s)" % (ad, beklenen, var))
            hata += 1
    print("KENDINI-TEST: 1 mutant / 2 kontrol · DUSEN=%d" % hata)
    return 1 if hata else 0


if "--kendini-test" in sys.argv:
    sys.exit(_kendini_test())

import sayfalar

bulgu = tara(sayfalar.CONTENT_PAGES)
print("TARANAN=%d OZ_LINKLI_SAYFA=%d TOPLAM_OZ_LINK=%d"
      % (len(sayfalar.CONTENT_PAGES), len(bulgu), sum(n for _s, n in bulgu)))
for slug, n in bulgu:
    print("  ! %s -> kendine %d link" % (slug, n))
if bulgu:
    print("❌ KIRMIZI: sayfa kendi URL'ine link veriyor.")
    sys.exit(1)
print("✅ YESIL: oz-link yok.")
