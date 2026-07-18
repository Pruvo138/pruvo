#!/usr/bin/env python3
"""CATEGORIES + gizli-kategori PARİTE testi (silent-drift guard).

CATEGORIES ve gizli kategoriler İKİ yerde elle tutulur:
  - tools/build.py : CATEGORIES / NAV_GIZLI  (ürün sayfaları + nav)
  - index.html     : CATEGORIES / GIZLI_KATEGORILER  (ana sayfa nav + filtre)
Biri güncellenip diğeri unutulursa ana sayfa ile ürün sayfaları farklı kategori
görür = sessiz bozulma. Bu test ikisinin AYNI (öğe + sıra) olduğunu doğrular.

Çalıştır:  python3 tools/kategori-parite-test.py   (0=geçti, 1=drift)
CATEGORIES ya da gizli listeyi değiştirdiğinde İKİSİNİ birden güncelle, sonra bunu koş.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "tools", "build.py")
INDEX = os.path.join(ROOT, "index.html")


def _liste(metin, desen, etiket, dosya):
    m = re.search(desen, metin, re.M)
    if not m:
        raise SystemExit("KALDI ❌ %s bulunamadı: %s (yapı değişti mi?)" % (etiket, dosya))
    ham = "[" + m.group(1) + "]"
    try:
        return json.loads(ham)
    except json.JSONDecodeError as e:
        raise SystemExit("KALDI ❌ %s ayrıştırılamadı (%s): %s" % (etiket, dosya, e))


with open(BUILD, encoding="utf-8") as f:
    b = f.read()
with open(INDEX, encoding="utf-8") as f:
    i = f.read()

# build.py: CATEGORIES = [ ... ]  /  NAV_GIZLI = [ ... ]
b_cat = _liste(b, r"^CATEGORIES\s*=\s*\[(.*?)\]", "build.py CATEGORIES", BUILD)
b_giz = _liste(b, r"^NAV_GIZLI\s*=\s*\[(.*?)\]", "build.py NAV_GIZLI", BUILD)
# index.html: var CATEGORIES = [ ... ]  /  var GIZLI_KATEGORILER = [ ... ]
i_cat = _liste(i, r"var\s+CATEGORIES\s*=\s*\[(.*?)\]", "index.html CATEGORIES", INDEX)
i_giz = _liste(i, r"var\s+GIZLI_KATEGORILER\s*=\s*\[(.*?)\]", "index.html GIZLI_KATEGORILER", INDEX)


def _wa(metin, desen, etiket, dosya):
    m = re.search(desen, metin, re.M)
    if not m:
        raise SystemExit("KALDI ❌ %s bulunamadı: %s (yapı değişti mi?)" % (etiket, dosya))
    return m.group(1)


# WHATSAPP sipariş numarası da iki yerde elle tutulur; drift = siparişler YANLIŞ numaraya = kayıp satış.
b_wa = _wa(b, r'^WHATSAPP\s*=\s*"(\d+)"', "build.py WHATSAPP", BUILD)
i_wa = _wa(i, r'var\s+WHATSAPP\s*=\s*"(\d+)"', "index.html WHATSAPP", INDEX)

hata = []
if b_cat != i_cat:
    hata.append("CATEGORIES DRİFT:\n  build.py : %s\n  index    : %s" % (b_cat, i_cat))
if b_giz != i_giz:
    hata.append("GİZLİ KATEGORİ DRİFT:\n  build.py NAV_GIZLI      : %s\n  index GIZLI_KATEGORILER: %s" % (b_giz, i_giz))
if b_wa != i_wa:
    hata.append("WHATSAPP DRİFT (sipariş numarası!):\n  build.py : %s\n  index    : %s" % (b_wa, i_wa))

if hata:
    print("\n".join(hata))
    print("SONUC: KALDI ❌ (iki dosyada da AYNI sırada güncelle)")
    sys.exit(1)

print("CATEGORIES (%d): %s" % (len(b_cat), b_cat))
print("gizli: %s   WHATSAPP: %s" % (b_giz, b_wa))
print("SONUC: GECTI ✅ (CATEGORIES + gizli + WHATSAPP build.py<->index.html paritede)")
sys.exit(0)
