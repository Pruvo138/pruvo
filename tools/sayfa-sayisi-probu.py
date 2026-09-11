# -*- coding: utf-8 -*-
"""CONTENT_PAGES sayaci — beyaz esya kapsam temizliginin 'kaç sayfa dustu' eksenini olcer.

Tek is: sayfalar.py import edilebiliyor mu ve kac icerik sayfasi var. Silme isleminin
YAN ETKISINI (baska sayfalarin da dusmesi) sayiyla yakalar.
  python3 tools/sayfa-sayisi-probu.py
"""
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "tools"))

import sayfalar

n = len(sayfalar.CONTENT_PAGES)
sluglar = [s for s, _b, _m, _f in sayfalar.CONTENT_PAGES]
tekil = len(set(sluglar))
print("CONTENT_PAGES=%d" % n)
print("TEKIL_SLUG=%d" % tekil)
print("SITEMAP_SLUGS=%d" % len(sayfalar.SITEMAP_SLUGS))
if tekil != n:
    print("❌ KIRMIZI: tekrarli slug var (%d tekrar)." % (n - tekil))
    sys.exit(1)
# her govde cagrilabilir ve bos olmamali (silme sirasinda kirik referans kalmasin)
kirik = [s for s, _b, _m, f in sayfalar.CONTENT_PAGES
         if not (f() if callable(f) else str(f)).strip()]
if kirik:
    print("❌ KIRMIZI: bos govde: %s" % ", ".join(kirik))
    sys.exit(1)
print("✅ YESIL: %d sayfa, hepsi tekil ve dolu." % n)
