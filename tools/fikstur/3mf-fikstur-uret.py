#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/test-bbox-3mf.py'nin ANKRAJ fiksturlerini URETIR (deterministik, agsiz).

NEDEN VAR (30 Tem): test-bbox-3mf.py'nin ankrajlari GERCEK urun dosyalariydi
(`stl/pr1173083.3mf`, `stl/pr912419.3mf`) ve `stl/` depoya GIRMEZ (gitignore, yerel/R2).
Sonuc: test her ortamda 0,1 s'de FileNotFoundError ile patliyordu -> HICBIR iddia
kosmuyordu, ustelik ci-kapsam izin listesindeki gerekcesi R_YAVAS (">30 s") diyordu,
yani muafiyet de YANLIS bir gerekceyle duruyordu. Artik ankraj DEPODA: kucuk (~1 KB),
sentetik, elle hesaplanabilir 3MF arsivleri.

BU BETIK CI'DA KOSMAZ (kosarsa fiksturu EZER) — `tools/fikstur/` alt dizinindedir,
ci-kapsam kesif predikati yalniz `tools/` DOGRUDAN altina bakar. Fikstur degistirmek
gerekirse elle kosulur ve URETILEN dosyalar commit edilir.

    python3 tools/fikstur/3mf-fikstur-uret.py            # uretir/uzerine yazar
    python3 tools/fikstur/3mf-fikstur-uret.py --dogrula  # uretilenle depodakini KIYASLAR

FIKSTUR SINIFLARI (her biri ayri bir OLCUM RISKINI ankrajlar):
  cok-model-transform.3mf : Bambu-Studio sinifi. Kok `3D/3dmodel.model` YALNIZ montaj
      tutar (vertex YOK) ve arsivde ILK sirada gelir; gercek geometri
      `3D/Objects/object_1.model`tedir, `p:path` + `transform` ile baglanir.
      ESKI mantik (ilk .model + regex) burada None doner — onarilan sinifin ta kendisi.
      Kutu 10x20x30 mm; component transform X'te 2x olcek, item transform Y'de 3x olcek
      -> (20, 60, 30), SIRALI [60, 30, 20] mm. Olcekler BILEREK secildi: iki transform
      katmani da AYIRT EDICI olsun diye. Dort hal dort FARKLI sonuc verir — zincir
      cozulmezse (ham vertex geri-dususu) [30, 20, 10], yalniz component uygulanirsa
      [30, 20, 20], yalniz item uygulanirsa [60, 30, 10]. Donme matrisi kullanilsaydi
      olcu SIRALI oldugu icin fark GORUNMEZDI (sessiz-yesil).
  tek-model-duz.3mf : tek `.model`, transform yok, unit=millimeter. Eski ve yeni mantik
      AYNI sonucu vermek ZORUNDA (regresyon ankraji). Kutu -> [47, 40, 31] mm.
  birim-inch.3mf : tek `.model`, unit="inch". Birim carpani dusserse olcu 25,4 kat
      kucuk cikar (sessiz hata sinifi). Kutu 4x2x1 inc -> [101.6, 50.8, 25.4] mm.
"""
import os
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
CIKTI = os.path.join(HERE, "3mf")

# Zip icindeki tarih SABIT tutulur -> ayni girdi ayni BAYTLARI uretir (--dogrula anlamli).
SABIT_TARIH = (2026, 7, 30, 0, 0, 0)

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
    'relationships+xml"/>'
    '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-'
    '3dmodel+xml"/></Types>\n')

RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.'
    'com/3dmanufacturing/2013/01/3dmodel"/></Relationships>\n')

NS = ('xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
      'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06"')


def _kutu_vertexleri(dx, dy, dz):
    """Eksen hizali kutunun 8 kosesi — 3MF <vertex> satirlari (oznitelik sirasi x,y,z)."""
    kose = []
    for x in (0.0, dx):
        for y in (0.0, dy):
            for z in (0.0, dz):
                kose.append('<vertex x="%s" y="%s" z="%s"/>' % (x, y, z))
    return "".join(kose)


# 8 kose -> 12 ucgen yerine 2 ucgen yeter (bbox yalniz vertex'lere bakar); yine de
# gecerli bir <triangles> blogu birakilir ki dosya sema-makul gorunsun.
UCGENLER = '<triangle v1="0" v2="1" v3="2"/><triangle v1="1" v2="3" v3="2"/>'


def _mesh(dx, dy, dz):
    return ('<mesh><vertices>%s</vertices><triangles>%s</triangles></mesh>'
            % (_kutu_vertexleri(dx, dy, dz), UCGENLER))


def cok_model_transform():
    """(uyeler) — kok montaj ILK, geometri AYRI .model dosyasinda (Bambu sinifi)."""
    kok = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<model unit="millimeter" %s>'
           '<resources><object id="1" type="model"><components>'
           # component transform: X'te 2x olcek + oteleme (satir-major 12 sayi)
           '<component objectid="10" p:path="/3D/Objects/object_1.model" '
           'transform="2 0 0 0 1 0 0 0 1 5 0 0"/>'
           '</components></object></resources>'
           # item transform: Y'de 3x olcek + oteleme
           '<build><item objectid="1" transform="1 0 0 0 3 0 0 0 1 0 7 0"/></build>'
           '</model>\n') % NS
    parca = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" %s>'
             '<resources><object id="10" type="model">%s</object></resources>'
             '<build/></model>\n') % (NS, _mesh(10.0, 20.0, 30.0))
    # SIRA ONEMLI: kok (vertex'siz) ILK yazilir -> eski "names[0]" mantigi None doner.
    return [("3D/3dmodel.model", kok), ("3D/Objects/object_1.model", parca)]


def tek_model_duz():
    kok = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<model unit="millimeter" %s>'
           '<resources><object id="1" type="model">%s</object></resources>'
           '<build><item objectid="1"/></build></model>\n') % (NS, _mesh(47.0, 40.0, 31.0))
    return [("3D/3dmodel.model", kok)]


def birim_inch():
    kok = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<model unit="inch" %s>'
           '<resources><object id="1" type="model">%s</object></resources>'
           '<build><item objectid="1"/></build></model>\n') % (NS, _mesh(4.0, 2.0, 1.0))
    return [("3D/3dmodel.model", kok)]


FIKSTURLER = {
    "cok-model-transform.3mf": cok_model_transform,
    "tek-model-duz.3mf": tek_model_duz,
    "birim-inch.3mf": birim_inch,
}


def paket_baytlari(uyeler):
    import io
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        for ad, govde in ([("[Content_Types].xml", CONTENT_TYPES),
                           ("_rels/.rels", RELS)] + list(uyeler)):
            bilgi = zipfile.ZipInfo(ad, date_time=SABIT_TARIH)
            bilgi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(bilgi, govde)
    return tampon.getvalue()


def main():
    dogrula = "--dogrula" in sys.argv[1:]
    if not dogrula:
        os.makedirs(CIKTI, exist_ok=True)
    fark = []
    for ad, uret in sorted(FIKSTURLER.items()):
        veri = paket_baytlari(uret())
        yol = os.path.join(CIKTI, ad)
        if dogrula:
            mevcut = None
            if os.path.exists(yol):
                with open(yol, "rb") as f:
                    mevcut = f.read()
            durum = "AYNI" if mevcut == veri else ("YOK" if mevcut is None else "FARKLI")
            print("  %-26s %s  (%d bayt)" % (ad, durum, len(veri)))
            if durum != "AYNI":
                fark.append(ad)
            continue
        with open(yol, "wb") as f:
            f.write(veri)
        print("  yazildi: %s  (%d bayt)" % (yol, len(veri)))
    if dogrula and fark:
        print("FARK VAR: %s -> bayraksiz kosup commit et" % ", ".join(fark))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
