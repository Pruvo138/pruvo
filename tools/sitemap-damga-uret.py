#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sitemap damga ONBELLEGINI sifirdan kurar + dagilimi bastirir (yerel/teshis).

⚠️ `sitemap-damgalari.json` GIT'E GIRMEZ (gitignore) ve KANIT DEGILDIR: tarihlerin
tek kaynagi git gecmisidir. CI'da onbellek `actions/cache` ile tasinir; dusse bile
build SOGUK BASLAR ve ayni tarihleri yeniden turetir.

🔴 IKINCI BIR TURETIM YAZILMAZ ([[ikiz-tanim-sessiz-ayrisma]]). Bu arac tarihleri
KENDI algoritmasiyla hesaplamaz; build.py ile AYNI `sitemap_damga.sitemap_tarihleri`
cagrisini yapar. (Olculdu 11 Agu 2026: ayri yazilmis "eskiden yeniye" bir uretec,
silinip geri eklenen 1 urunde build'in cozumunden 1 gun sapiyordu — 22'ye karsi 23
benzersiz tarih. Ayri uretec KALDIRILDI.)

KOSUM:
    python3 tools/sitemap-damga-uret.py            # onbellegi kur + dagilim
    python3 tools/sitemap-damga-uret.py --dagilim  # var olan onbellegi bozmadan bak
"""

import collections
import json
import os
import subprocess
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "tools"))
import sitemap_damga as sd                                     # noqa: E402


def main():
    yalniz_bak = "--dagilim" in sys.argv
    r = subprocess.run(("git", "rev-parse", "--is-shallow-repository"),
                       cwd=KOK, capture_output=True, text=True)
    if r.stdout.strip() != "false":
        print("UYARI: shallow klon — gecmis eksik, cozulemeyen urun lastmod'suz kalir.")

    with open(os.path.join(KOK, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    yol = sd.defter_yolu(KOK)
    if not yalniz_bak and os.path.exists(yol):
        os.remove(yol)                       # SOGUK baslat (tam yurume)

    t0 = time.time()
    url_tarih, tani = sd.sitemap_tarihleri(
        urunler, lambda pid: "/urun/" + pid + "/", yol, KOK)
    sure = time.time() - t0

    sayac = collections.Counter(url_tarih.values())
    print("urun            : %d" % len(urunler))
    print("tarihli URL     : %d  (onbellekten %d · git'ten %d)"
          % (len(url_tarih), tani["defterden"], tani["gitten"]))
    print("cozulemedi      : %d  (bu URL'lerde <lastmod> BASILMAZ)" % tani["cozulemedi"])
    print("yurunen commit  : %d · sure %.0f sn · tavan asildi: %s · sure asildi: %s"
          % (tani["yurunen_commit"], sure, tani["tavan_asildi"], tani["sure_asildi"]))
    print("benzersiz tarih : %d" % len(sayac))
    for t in sorted(sayac):
        print("   ", t, "->", sayac[t])
    print("onbellek        : %s (%d bayt)"
          % (yol, os.path.getsize(yol) if os.path.exists(yol) else 0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
