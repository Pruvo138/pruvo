#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""jenerator/test/aileler/*.js dosyalarini TEK jenerator/hacim.js modulunde birlestirir.

Kurallar:
- Her aile dosyasi SADECE `function <aile>(p) {...}` (+ ayni dosyada `<aile>_...`
  onekli yardimci fonksiyonlar) icerir; global durum/side-effect YASAK.
- Birlestirme alfabetik ve deterministiktir -> ayni girdi = bayt-ozdes cikti
  (kabul testi #4 "tek kaynak" buna dayanir).
- Cikti UMD sarmali: tarayicida window.PRUVO_HACIM, Node/Worker'da module.exports.

Kullanim: python3 birlestir.py   (arguman yok; konumdan bagimsiz calisir)
"""
import io
import os
import re
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
AILE_DIR = os.path.join(TEST_DIR, "aileler")
CIKTI = os.path.join(TEST_DIR, "..", "hacim.js")

BAS = u"""/* PRUVO — parametrik urun hacim fonksiyonlari (mm3).
   TEK KAYNAK: site (client) ve siparis dogrulama ayni dosyayi yukler; kopyalanmaz.
   ELLE DUZENLEME: bu dosya jenerator/test/birlestir.py tarafindan
   jenerator/test/aileler/*.js dosyalarindan uretilir; duzeltme aile dosyasinda yapilir.
   Girdi: p = {parametre_adi: deger, ...} (semadaki `ad` alanlari, sayi/secim degerleri).
   Cikti: yaklasik kati hacim, mm3 (kapali-form; OpenSCAD render dogrulamali, sapma <=%3). */
(function (root, factory) {
  if (typeof module === "object" && module.exports) { module.exports = factory(); }
  else { root.PRUVO_HACIM = factory(); }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

"""

SON = u"""
  return {
%s
  };
});
"""


def main():
    if not os.path.isdir(AILE_DIR):
        sys.exit("aileler/ dizini yok: %s" % AILE_DIR)
    aileler = sorted(f[:-3] for f in os.listdir(AILE_DIR)
                     if f.endswith(".js") and not f.startswith("."))
    if not aileler:
        sys.exit("aileler/ altinda .js dosyasi yok")
    govde = []
    for aile in aileler:
        yol = os.path.join(AILE_DIR, aile + ".js")
        with io.open(yol, "r", encoding="utf-8") as f:
            icerik = f.read().strip()
        if not re.search(r"function\s+%s\s*\(" % re.escape(aile), icerik):
            sys.exit("%s.js icinde `function %s(` yok" % (aile, aile))
        # aile disina tasan isim yok mu (kabaca): tum fonksiyon adlari aile onekli olmali
        for ad in re.findall(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", icerik):
            if ad != aile and not ad.startswith(aile + "_"):
                sys.exit("%s.js: fonksiyon adi '%s' aile onekli degil" % (aile, ad))
        govde.append(u"  // === AILE: %s ===\n%s\n" % (
            aile, u"\n".join(u"  " + s if s.strip() else s
                             for s in icerik.splitlines())))
    disari = u",\n".join(u"    %s: %s" % (a, a) for a in aileler)
    # atomik yaz (gecici dosya + rename): paralel dogrula.py kosulari yarim dosya okumasin
    gecici = CIKTI + ".tmp.%d" % os.getpid()
    with io.open(gecici, "w", encoding="utf-8", newline="\n") as f:
        f.write(BAS + u"\n".join(govde) + SON % disari)
    os.replace(gecici, CIKTI)
    print("hacim.js uretildi: %d aile (%s)" % (len(aileler), ", ".join(aileler)))


if __name__ == "__main__":
    main()
