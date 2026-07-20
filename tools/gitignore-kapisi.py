#!/usr/bin/env python3
"""gitignore-kapisi.py — .gitignore'daki "uretilen icerik dizinleri" blogunu dogrular.

NEDEN: tools/sayfalar.py CONTENT_PAGES'e yeni bir SEO/icerik sayfasi eklenince build.py
repo kokunde /<slug>/index.html uretir. .gitignore'da karsiligi yoksa dizin `git status`ta
`??` olarak birikir ve kazayla commit edilirse PUBLIC repoya build ciktisi girer. Liste elle
tutuldugu surece drift kacinilmazdi -> bu kapi blogu CONTENT_PAGES'ten TURETIR ve karsilastirir.

NOT: STATIK_SAYFALAR (hakkimizda/iletisim/sss/gizlilik) elle yazilmis ve repoda IZLENEN
dosyalardir; bloga ASLA girmez (girerse guncellemeleri sessizce kaybolur) — kapi bunu da denetler.

Kullanim:
  python3 tools/gitignore-kapisi.py          # dogrula (drift varsa farki basar, exit 1)
  python3 tools/gitignore-kapisi.py --yaz    # blogu CONTENT_PAGES'ten yeniden uret
"""
import argparse
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GITIGNORE = os.path.join(ROOT, ".gitignore")
SAYFALAR = os.path.join(ROOT, "tools", "sayfalar.py")

BAS = "# >>> uretilen-icerik-dizinleri (otomatik — elle duzenleme; tools/gitignore-kapisi.py dogrular)"
SON = "# <<< uretilen-icerik-dizinleri"


def _sayfalar_modulu():
    """tools/sayfalar.py'yi modul olarak yukler (build.py ile ayni kaynak)."""
    spec = importlib.util.spec_from_file_location("sayfalar", SAYFALAR)
    if spec is None or spec.loader is None:
        sys.exit("HATA: tools/sayfalar.py yuklenemedi: " + SAYFALAR)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["sayfalar"] = mod
    spec.loader.exec_module(mod)
    return mod


def beklenen_satirlar():
    """CONTENT_PAGES'ten turetilmis blok govdesi: her uretilen sayfa icin '/slug/'.

    STATIK_SAYFALAR haric tutulur (repoda izlenen elle yazilmis sayfalar).
    """
    m = _sayfalar_modulu()
    statik = set(m.STATIK_SAYFALAR)
    return ["/%s/" % slug for slug, _b, _meta, _fn in m.CONTENT_PAGES if slug not in statik], statik


def _oku():
    with open(GITIGNORE, encoding="utf-8") as f:
        return f.read().split("\n")


def _blok_sinirlari(satirlar):
    try:
        i = satirlar.index(BAS)
        j = satirlar.index(SON)
    except ValueError:
        return None
    if j < i:
        return None
    return i, j


def dogrula():
    beklenen, statik = beklenen_satirlar()
    satirlar = _oku()
    sinir = _blok_sinirlari(satirlar)
    sorunlar = []

    if sinir is None:
        sorunlar.append("Isaretli blok yok (BAS/SON satirlari bulunamadi). "
                        "Kurmak icin: python3 tools/gitignore-kapisi.py --yaz")
        mevcut = []
    else:
        i, j = sinir
        mevcut = [s for s in satirlar[i + 1:j] if s.strip()]
        eksik = [s for s in beklenen if s not in mevcut]
        fazla = [s for s in mevcut if s not in beklenen]
        if eksik:
            sorunlar.append("blokta EKSIK (uretilir ama ignore edilmiyor): " + ", ".join(eksik))
        if fazla:
            sorunlar.append("blokta FAZLA (CONTENT_PAGES'te yok): " + ", ".join(fazla))
        if not eksik and not fazla and mevcut != beklenen:
            sorunlar.append("blok sirasi CONTENT_PAGES sirasindan farkli (--yaz ile duzelt)")

    # Statik (izlenen) sayfalar .gitignore'un HICBIR yerinde olmamali.
    for slug in sorted(statik):
        for s in satirlar:
            if s.strip().strip("/") == slug:
                sorunlar.append("STATIK sayfa .gitignore'da: %r — izlenen dosya, ignore EDILMEZ" % s.strip())

    # Blok disinda ayni slug'in ikinci kopyasi kalmasin (eski elle yazilmis satirlar).
    if sinir is not None:
        i, j = sinir
        dis = [s.strip() for k, s in enumerate(satirlar) if not (i <= k <= j)]
        cift = sorted(set(b for b in beklenen if b in dis))
        if cift:
            sorunlar.append("blok DISINDA ikinci kopya: " + ", ".join(cift))

    if sorunlar:
        print("GITIGNORE KAPISI: DRIFT (%d bulgu)" % len(sorunlar))
        for s in sorunlar:
            print("  - " + s)
        print("Duzeltme: python3 tools/gitignore-kapisi.py --yaz")
        return 1

    print("GITIGNORE KAPISI: TEMIZ — blok CONTENT_PAGES ile bire bir (%d uretilen dizin), "
          "statik sayfalar (%s) ignore edilmiyor." % (len(beklenen), ", ".join(sorted(statik))))
    return 0


def yaz():
    beklenen, _statik = beklenen_satirlar()
    satirlar = _oku()
    sinir = _blok_sinirlari(satirlar)
    yeni_blok = [BAS] + beklenen + [SON]

    if sinir is None:
        # Blok yoksa build.py ciktilari bolumunun sonuna ekle; bulunamazsa dosya sonuna.
        capa = "/_yayin-icerik-dizinleri.txt"
        yer = satirlar.index(capa) + 1 if capa in satirlar else len(satirlar)
        satirlar = satirlar[:yer] + [""] + yeni_blok + satirlar[yer:]
        print("Blok OLUSTURULDU (%d satir)." % len(beklenen))
    else:
        i, j = sinir
        satirlar = satirlar[:i] + yeni_blok + satirlar[j + 1:]
        print("Blok YENIDEN URETILDI (%d satir)." % len(beklenen))

    # Blok disinda kalan ikinci kopyalari temizle.
    sinir = _blok_sinirlari(satirlar)
    i, j = sinir
    temiz = []
    for k, s in enumerate(satirlar):
        if not (i <= k <= j) and s.strip() in beklenen:
            print("  cift kayit kaldirildi: " + s.strip())
            continue
        temiz.append(s)

    with open(GITIGNORE, "w", encoding="utf-8") as f:
        f.write("\n".join(temiz))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--yaz", action="store_true",
                    help="blogu CONTENT_PAGES'ten yeniden uret (drift'i duzelt)")
    args = ap.parse_args()
    return yaz() if args.yaz else dogrula()


if __name__ == "__main__":
    sys.exit(main())
