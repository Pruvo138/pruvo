#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merchant feed gorsel cache-bust kabul testi.

Nobetci: tools/build.py feed uretiminde <g:image_link> ve <g:additional_image_link>
URL'lerinin TAMAMI kararli bir surum damgasi (?v=N) tasimali. Damga her build'de
degisirse (zaman/rastgele) Meta/Google her seferinde tum gorselleri yeniden ceker
-> bu testin (b) maddesi bunu KIRMIZI yakar.

Kontroller (hepsi gecmezse exit 1):
  (a) damgali URL sayisi == toplam gorsel URL sayisi (%100)
  (b) iki ardisik build'in feed'i BYTE-ESIT (damga kararli)
  (c) sorgu iceren URL'de ayrac dogru ('&' kullanilir, '??' olusmaz)
  (d) feed XML gecerli + <item> sayisi bagimsiz hesaplanan beklenen sayiya esit

Bagimlilik: yok (saf Python 3 std lib). Ag/DB erisimi YOK. build.py'yi 2 kez kosar.
Calistir:  python3 tools/feed-cache-bust-test.py
(Dosya adi ci-kapsam kesif desenine uyar: tools/<ad>-test.py -> kapi bu testi GORUR.)
"""

import os
import re
import sys
import json
import runpy
import hashlib
import subprocess
import xml.etree.ElementTree as ET

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
BUILD = os.path.join(TOOLS, "build.py")
FEED = os.path.join(ROOT, "merchant-feed.xml")
G_NS = "http://base.google.com/ns/1.0"

hatalar = []


def olc(ad, kosul, detay=""):
    print(("  GECTI  " if kosul else "  KALDI  ") + ad + (("  -> " + detay) if detay else ""))
    if not kosul:
        hatalar.append(ad)


def build_kos(etiket):
    r = subprocess.run([sys.executable, BUILD], cwd=ROOT,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print("[build %s] exit=%d" % (etiket, r.returncode))
    if r.returncode != 0:
        print(r.stdout.decode("utf-8", "replace")[-2000:])
        sys.exit(2)
    with open(FEED, "rb") as f:
        return f.read()


def beklenen_urun_sayisi(mod):
    """build.py'nin feed filtresini BAGIMSIZ uygula: parametrik degil + sayisal
    fiyat var + en az 1 gorsel."""
    with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    n = 0
    for p in urunler:
        if p.get("parametrik"):
            continue
        if not mod["feed_price"]((p.get("fiyat") or "").strip()):
            continue
        if not mod["images_of"](p):
            continue
        n += 1
    return n


def main():
    print("== feed cache-bust testi ==")
    mod = runpy.run_path(BUILD, run_name="feed_cache_bust_test")   # main() kosmaz
    surum = mod["FEED_IMG_SURUM"]
    feed_img = mod["feed_img"]

    ham1 = build_kos("1")
    ham2 = build_kos("2")

    # (d) gecerli XML + urun sayisi
    kok = ET.fromstring(ham1)
    itemler = kok.findall("./channel/item")
    bekl = beklenen_urun_sayisi(mod)
    olc("(d) XML parse + urun sayisi", len(itemler) == bekl and len(itemler) > 0,
        "feed=%d beklenen=%d" % (len(itemler), bekl))

    # (a) TUM gorsel URL'leri damgali
    urller = []
    for it in itemler:
        for etiket in ("image_link", "additional_image_link"):
            for e in it.findall("{%s}%s" % (G_NS, etiket)):
                urller.append(e.text or "")
    damga = "v=" + str(surum)
    damgali = [u for u in urller if re.search(r"[?&]" + re.escape(damga) + r"(&|$)", u)]
    olc("(a) tum gorsel URL'leri damgali", len(urller) > 0 and len(damgali) == len(urller),
        "damgali=%d toplam=%d (damga %s)" % (len(damgali), len(urller), damga))

    # (b) KARARLILIK: iki build byte-esit
    h1 = hashlib.sha256(ham1).hexdigest()
    h2 = hashlib.sha256(ham2).hexdigest()
    olc("(b) iki ardisik build byte-esit", h1 == h2, "%s vs %s" % (h1[:16], h2[:16]))

    # (c) ayrac dogrulugu: uretilen feed'de '??' yok + sorgulu URL'de '&' kullanilir
    bozuk = [u for u in urller if "??" in u or u.count("?") > 1]
    ornek_sorgulu = feed_img("https://media.pruvo3d.com/urunler/a-1.jpg?w=800")
    ornek_sade = feed_img("https://media.pruvo3d.com/urunler/a-1.jpg")
    ornek_idem = feed_img(ornek_sorgulu)
    olc("(c) ayrac dogru ('&' / tek '?')",
        not bozuk
        and ornek_sorgulu == "https://media.pruvo3d.com/urunler/a-1.jpg?w=800&" + damga
        and ornek_sade == "https://media.pruvo3d.com/urunler/a-1.jpg?" + damga
        and ornek_idem == ornek_sorgulu,
        "bozuk=%d ornek=%s" % (len(bozuk), ornek_sorgulu))

    print("--")
    if hatalar:
        print("KIRMIZI: " + ", ".join(hatalar))
        return 1
    print("YESIL: %d gorsel URL damgali, feed kararli (%d urun)." % (len(urller), len(itemler)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
