#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""URETEC — `index.html` icindeki ALTKATEGORILER veri blogunu arama.py'den TURETIR.

  python3 tools/altkategori-veri.py             # blogu index.html'e YAZ (uret)
  python3 tools/altkategori-veri.py --kontrol   # blok TAZE mi (rc=0 taze, rc=1 bayat)
  python3 tools/altkategori-veri.py --yazdir    # uretilecek blogu ekrana bas (yazmaz)

NEDEN VAR (mimar spec'i "60 deger ELLE gomulmesin" + olculmus dagitim kisiti):
alt kategori cip satirinin evreni TEK KAYNAKTAN gelmeli — o kaynak
tools/arama.py :: ALTKATEGORI_IZINLI'dir (fail-closed izinli kume; duzelt.py, d1-sync,
build.py hepsi ondan turer). Ikinci bir elle-tutulan kopya acilsaydi
[[ikiz-tanim-sessiz-ayrisma]]: kume genisler, cip satiri eski kalir, kimse fark etmez.

NEDEN AYRI BIR .js DOSYASI DEGIL (olculdu 2 Agu): .github/workflows/deploy.yml `_site`'i
ACIK BIR VARLIK LISTESIYLE kurar (`cp _yayin/secenekler.js _yayin/konfigur.js ...`).
Yeni bir kok .js dosyasi o listeye eklenmeden YAYINLANMAZ -> canlida 404 -> cip satiri
SESSIZCE bos kalir. deploy.yml bu is paketinde DOKUNULMAZ kapsamdadir, bu yuzden veri
zaten yayinlanan index.html icine URETILEREK gomulur (depodaki emsal: TANINMIS_MARKALAR
<-> tools/marka_katla.py ikizi). "Elle gommeme" sarti BU BETIKLE saglanir: degerleri
insan yazmaz, uretec yazar; ayrisma tools/altkategori-cip-test.py'de KIRMIZI yanar.

Blok ISARETCILERI (index.html icinde birebir bu iki satir):
  // >>> ALTKATEGORI VERISI ...
  // <<< ALTKATEGORI VERISI
"""
import argparse
import importlib.util
import json
import os
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(DIR)
INDEX = os.path.join(KOK, "index.html")

BAS = "  // >>> ALTKATEGORI VERISI (URETILEN BLOK — python3 tools/altkategori-veri.py)"
SON = "  // <<< ALTKATEGORI VERISI"


def arama_modulu(kok=None):
    yol = os.path.join(kok or KOK, "tools", "arama.py")
    spec = importlib.util.spec_from_file_location("arama_altveri", yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def blok_uret(izinli):
    """ALTKATEGORI_IZINLI -> index.html'e girecek JS blogu (deterministik metin)."""
    satirlar = [
        BAS,
        "  // Alt kategori cip evreni. TEK KAYNAK: tools/arama.py :: ALTKATEGORI_IZINLI",
        "  // (duzelt.py / d1-sync / build.py ayni kumeden turer). ELLE DUZENLEME —",
        "  // kume degisince `python3 tools/altkategori-veri.py` kosulur; ayrisirsa",
        "  // tools/altkategori-cip-test.py (CI'da bloklayici) KIRMIZI yanar.",
        "  var ALTKATEGORILER = {",
    ]
    anahtarlar = list(izinli.keys())
    for i, kat in enumerate(anahtarlar):
        degerler = list(izinli[kat])
        govde = ",".join(json.dumps(d, ensure_ascii=False) for d in degerler)
        virgul = "" if i == len(anahtarlar) - 1 else ","
        satirlar.append("    %s: [%s]%s" % (json.dumps(kat, ensure_ascii=False), govde, virgul))
    satirlar.append("  };")
    satirlar.append(SON)
    return "\n".join(satirlar)


def blok_oku(metin):
    """index.html metnindeki mevcut blok (isaretciler dahil) ya da None."""
    i = metin.find(BAS)
    if i == -1:
        return None
    j = metin.find(SON, i)
    if j == -1:
        return None
    return metin[i:j + len(SON)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kontrol", action="store_true", help="blok taze mi (rc=1 bayat)")
    ap.add_argument("--yazdir", action="store_true", help="blogu bas, dosyaya yazma")
    ap.add_argument("--index", default=INDEX, help="hedef index.html yolu")
    a = ap.parse_args()

    beklenen = blok_uret(arama_modulu().ALTKATEGORI_IZINLI)

    if a.yazdir:
        print(beklenen)
        return 0

    with open(a.index, encoding="utf-8") as f:
        metin = f.read()
    mevcut = blok_oku(metin)

    if a.kontrol:
        if mevcut is None:
            print("BAYAT: index.html'de ALTKATEGORI VERISI blogu YOK.", file=sys.stderr)
            return 1
        if mevcut != beklenen:
            print("BAYAT: index.html blogu arama.ALTKATEGORI_IZINLI ile AYRISMIS.",
                  file=sys.stderr)
            return 1
        print("OK: ALTKATEGORI VERISI blogu taze.")
        return 0

    if mevcut is None:
        print("HATA: index.html'de blok isaretcileri YOK — once elle yerlestir.",
              file=sys.stderr)
        return 2
    if mevcut == beklenen:
        print("OK: blok zaten taze, dosya DEGISMEDI.")
        return 0
    with open(a.index, "w", encoding="utf-8") as f:
        f.write(metin.replace(mevcut, beklenen))
    print("OK: ALTKATEGORI VERISI blogu yenilendi (%d kategori)."
          % len(arama_modulu().ALTKATEGORI_IZINLI))
    return 0


if __name__ == "__main__":
    sys.exit(main())
