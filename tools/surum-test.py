#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script onbellek surumleme (cache-buster) KABUL TESTI.

SORUN: /secenekler.js ve /taban-fiyatlar.js canlida cache-control: max-age=14400
(4 SAAT tarayici onbellegi) ile geliyordu; Actions'in Cloudflare purge'u musteri
TARAYICISINI temizlemez -> bayrak/fiyat kurali degisikligi musteriye 4 saate kadar
gec ulasiyordu. Cozum: yayinlanan HTML'lerde script src'lerine ?v=<icerik-hash>.

Neyi dogrular (yayinlanan HTML'ler uzerinde — diskten degil, ureticiden taze):
  1) Site-ici /secenekler.js, /taban-fiyatlar.js ve konfiguratör /jenerator/*.js
     referanslarinin HICBIRI surumsuz (?v= olmadan) KALMAMALI.
       - Ana sayfa  -> build.yayin_index()  (index.html'in surumlenmis yayin kopyasi)
       - Urun sayfa -> build.render_product (bir normal + bir parametrik ornek)
  2) Surum parametresi DOSYA ICERIGININ hash'iyle BIREBIR esit olmali (sabit/yanlis
     degil): ?v=<x> == sha1(dosya)[:10]. Icerik degisirse surum de degisir.

Onceki (surumsuz) kodda KIRMIZI (surumsuz referanslari listeler); duzeltmeyle YESIL.
Calistirma:  python3 tools/surum-test.py   (cikis kodu 0 = gecti)
"""
import os
import re
import sys
import json
import hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build  # noqa: E402

# taban-fiyatlar.js ana sayfada referansli -> hash'i icin once uretilmis olmali.
build.uret_taban_fiyatlar()

# Surumsuz site-ici JS: src="/....js" ardindan HEMEN " (yani ?v= YOK).
SURUMSUZ_RE = re.compile(r'<script\b[^>]*\ssrc="(/[^"?]+\.js)"')
# Surumlu: src="/....js?v=<hash>"
SURUMLU_RE = re.compile(r'<script\b[^>]*\ssrc="(/[^"?]+\.js)\?v=([0-9a-f]+)"')


def beklenen_hash(yol):
    with open(os.path.join(ROOT, yol.lstrip("/")), "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:10]


def main():
    with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)

    normal = next((p for p in urunler if not p.get("parametrik")), None)
    parametrik = None
    for p in urunler:
        if p.get("parametrik") and os.path.isfile(
                os.path.join(build.JEN_URUN_DIR, p["id"] + ".json")):
            parametrik = p
            break

    sayfalar = {"index (yayin)": build.yayin_index()}
    if normal:
        sayfalar["urun/%s (normal)" % normal["id"]] = build.render_product(normal, urunler)
    if parametrik:
        sayfalar["urun/%s (parametrik)" % parametrik["id"]] = \
            build.render_product(parametrik, urunler)

    hatalar = []
    surumlu_toplam = 0
    kritik = set()  # gorulen kritik dosyalar (secenekler + taban)
    for ad, html in sayfalar.items():
        for m in SURUMSUZ_RE.finditer(html):
            hatalar.append("%s: SURUMSUZ script src=\"%s\" (onbellek kirici yok)"
                           % (ad, m.group(1)))
        for m in SURUMLU_RE.finditer(html):
            surumlu_toplam += 1
            yol, ver = m.group(1), m.group(2)
            if yol in ("/secenekler.js", "/taban-fiyatlar.js"):
                kritik.add(yol)
            dosya = os.path.join(ROOT, yol.lstrip("/"))
            if not os.path.isfile(dosya):
                hatalar.append("%s: %s dosyasi yok (hash dogrulanamadi)" % (ad, yol))
                continue
            bek = beklenen_hash(yol)
            if ver != bek:
                hatalar.append("%s: %s surumu '%s' != icerik hash'i '%s'"
                               % (ad, yol, ver, bek))

    # Kapsam yoklamasi: iki kritik dosya da EN AZ bir sayfada surumlu gorulmeli
    # (aksi halde regex/kapsam sessizce bosa dusmustur, test yanlislikla yesil yanar).
    for gerekli in ("/secenekler.js", "/taban-fiyatlar.js"):
        if gerekli not in kritik:
            hatalar.append("KAPSAM: %s hicbir yayin sayfasinda surumlu gorulmedi "
                           "(regex/kapsam bozuk olabilir)." % gerekli)

    if hatalar:
        print("KIRMIZI — surum testi %d hata:" % len(hatalar))
        for h in hatalar:
            print("  - " + h)
        sys.exit(1)
    print("YESIL — surum testi gecti (%d sayfa, %d surumlu referans, hepsi "
          "icerik-hash'iyle esit; kritik: secenekler.js + taban-fiyatlar.js)."
          % (len(sayfalar), surumlu_toplam))


if __name__ == "__main__":
    main()
