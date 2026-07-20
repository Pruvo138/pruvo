#!/usr/bin/env python3
"""kategori-kapisi.py — urunler.json'daki KATEGORI degerlerinin gecerliligini dogrular.

NEDEN: index.html kategori cipini `p.kategori === activeCat` ile BIREBIR esler ve
`?kategori=<ad>` parametresini CATEGORIES beyaz listesine karsi suzer. Listede olmayan
bir kategori (or. ASCII "Bahce" vs "Bahçe") urunu katalogda BIRAKIR ama kategoriden
GORUNMEZ yapar; build.py tarafinda da FONKSIYONEL_KATEGORILER disinda kaldigi icin
malzeme/renk secicisi ve Google urun taksonomisi duser. Hata SESSIZDIR -> kapi sart.

TEK KAYNAK: gecerli kategori listesi BU DOSYADA TUTULMAZ. index.html (CATEGORIES +
GIZLI_KATEGORILER) ve tools/build.py (CATEGORIES + NAV_GIZLI) PROGRAMATIK okunur; ikisi
birbirinden farkliysa bu da HATA sayilir (iki yer birlikte guncellenmeli kurali).

Kullanim:
  python3 tools/kategori-kapisi.py            # urunler.json'u dogrula (ihlal varsa exit 1)
  python3 tools/kategori-kapisi.py --liste    # gecerli kategorileri bas (exit 0)

DIKKAT: bu kapi build.py'ye BAGLANMAZ (tek kotu kategori tum yayini kirmasin); bagimsiz
calistirilabilir bir kabul testidir. build.py en fazla UYARI basar.
"""
import argparse
import ast
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "index.html")
BUILD = os.path.join(ROOT, "tools", "build.py")
URUNLER = os.path.join(ROOT, "urunler.json")


def _js_dizi(metin, ad, kaynak):
    """index.html icindeki `var <ad> = ["a","b"];` dizisini okur (JSON olarak ayristirilir)."""
    m = re.search(r"var\s+" + re.escape(ad) + r"\s*=\s*(\[[^\]]*\])\s*;", metin)
    if not m:
        raise SystemExit("HATA: %s icinde `var %s = [...]` bulunamadi." % (kaynak, ad))
    try:
        dizi = json.loads(m.group(1))
    except ValueError as e:
        raise SystemExit("HATA: %s icindeki %s dizisi ayristirilamadi: %s" % (kaynak, ad, e))
    if not isinstance(dizi, list) or not all(isinstance(x, str) for x in dizi):
        raise SystemExit("HATA: %s icindeki %s bir metin dizisi degil." % (kaynak, ad))
    return dizi


def _py_dizi(agac, ad, kaynak):
    """build.py icindeki modul duzeyi `<ad> = [...]` atamasini okur (ast, exec YOK)."""
    for dugum in agac.body:
        if isinstance(dugum, ast.Assign):
            for hedef in dugum.targets:
                if isinstance(hedef, ast.Name) and hedef.id == ad:
                    try:
                        deger = ast.literal_eval(dugum.value)
                    except ValueError as e:
                        raise SystemExit("HATA: %s icindeki %s sabit degil: %s" % (kaynak, ad, e))
                    if not isinstance(deger, list) or not all(isinstance(x, str) for x in deger):
                        raise SystemExit("HATA: %s icindeki %s bir metin dizisi degil." % (kaynak, ad))
                    return deger
    raise SystemExit("HATA: %s icinde modul duzeyinde `%s = [...]` bulunamadi." % (kaynak, ad))


def kaynak_listeler():
    """(index_nav, index_gizli, build_nav, build_gizli) dondurur — dosyalardan OKUNUR."""
    with open(INDEX, encoding="utf-8") as f:
        html = f.read()
    with open(BUILD, encoding="utf-8") as f:
        agac = ast.parse(f.read(), filename=BUILD)
    return (_js_dizi(html, "CATEGORIES", "index.html"),
            _js_dizi(html, "GIZLI_KATEGORILER", "index.html"),
            _py_dizi(agac, "CATEGORIES", "tools/build.py"),
            _py_dizi(agac, "NAV_GIZLI", "tools/build.py"))


def gecerli_kategoriler():
    """Iki kaynagi karsilastirir; uyusuyorsa gecerli kategori listesini dondurur.

    Uyusmuyorsa SystemExit(1) ile duser — CLAUDE.md "index.html VE tools/build.py, ayni
    sirada guncelle" kurali makine olarak burada dogrulanir.
    """
    i_nav, i_gizli, b_nav, b_gizli = kaynak_listeler()
    hatalar = []
    if i_nav != b_nav:
        hatalar.append("CATEGORIES ayristi:\n  index.html   : %s\n  tools/build.py: %s"
                       % (i_nav, b_nav))
    if i_gizli != b_gizli:
        hatalar.append("GIZLI kategoriler ayristi:\n  index.html GIZLI_KATEGORILER: %s\n"
                       "  tools/build.py NAV_GIZLI    : %s" % (i_gizli, b_gizli))
    if hatalar:
        print("KATEGORI KAPISI: KAYNAK AYRISMASI")
        for h in hatalar:
            print("  - " + h)
        raise SystemExit(1)
    return i_nav + i_gizli


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--liste", action="store_true",
                    help="gecerli kategorileri bas ve cik (dogrulama yapma)")
    ap.add_argument("--json", dest="json_yolu", default=URUNLER,
                    help="dogrulanacak urun JSON yolu (varsayilan: repo koku urunler.json)")
    args = ap.parse_args()

    gecerli = gecerli_kategoriler()
    if args.liste:
        for k in gecerli:
            print(k)
        return 0

    with open(args.json_yolu, encoding="utf-8") as f:
        urunler = json.load(f)

    ihlaller = []
    for u in urunler:
        if not isinstance(u, dict):
            ihlaller.append(("<obje-degil>", repr(u)[:60]))
            continue
        kat = u.get("kategori")
        if kat not in gecerli:
            ihlaller.append((u.get("id", "<id-yok>"), kat))

    if ihlaller:
        print("KATEGORI KAPISI: %d IHLAL (gecerli: %s)" % (len(ihlaller), ", ".join(gecerli)))
        for uid, kat in ihlaller:
            print("  - %s -> kategori=%r" % (uid, kat))
        print("Duzeltme YOLU: python3 tools/duzelt.py <id> --alan kategori --deger \"<Gecerli>\"")
        return 1

    print("KATEGORI KAPISI: TEMIZ — %d urun, %d gecerli kategori (%s)"
          % (len(urunler), len(gecerli), ", ".join(gecerli)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
