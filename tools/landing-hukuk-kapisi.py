#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Landing hukuk kapisi — kalici nobetci.

Iki hukuki-risk kuralini landing govdeleri uzerinde makine olarak dogrular.
CONTENT_PAGES dogrudan tools/sayfalar.py'den import edilir; build.py KOSTURULMAZ
(uretilen dosyalar kirlenmesin).

KURAL A — gida/tibbi kapsam beyani
    Govdesinde "gida" gecen HER landing'de, ayni sayfada kapsam sinirini soyleyen
    bir ifade de gecmeli: "sertifika" VEYA "kapsam dis" / "kapsamimiz dis".
    Sebep: site genelindeki ilke "gida/tibbi sertifika gerektiren uretimler kapsam
    disidir"; gidayi hizmet edilen bir kosul gibi sunup siniri soylememek celiski
    ve tuketici tarafinda risk yaratir.

KURAL B — revizyon ucret kosulu
    Olcu/revizyon konulu landing'lerde (asagidaki acik liste) sapma kosulu yazili
    olmali: "sapma bizim aldigimiz olcuden" + duzeltme kelimesi (revizyon /
    yeniden uretim / duzeltme) + ucret tarafi ("yeni bir is" veya "ucret").
    Sebep: ozel uretimde cayma hakki yok (bkz. /teslimat-iade); revizyonun kimden
    oldugu yazili degilse bosluk bize doner.

Fail-closed: import, okuma ya da render hatasinda KIRMIZI (exit 1).
"""

import os
import re
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))

# --- KURAL B kapsami: olcu/revizyon konulu landing'ler (acik liste) -----------
REVIZYON_ZORUNLU = (
    "parca-olcusu-nasil-alinir-ve-gonderilir",
    "elektrikli-scooter-plastik-parca-uretimi",
    "elektrikli-supurge-aparati-plastik-parca-uretimi",
    "plastik-pim-yaptirma",
    "kirik-plastik-tirnak-yaptirma",
    "plastik-stoper-durdurucu-yaptirma",
)

# --- KURAL A muafiyeti -------------------------------------------------------
# Tek kalem: "canli-gida" (balik/surungen yemi) baglaminda geciyor, gida-temasi
# hizmeti vaat etmiyor. Bu tur bu paketin kapsami disinda (sayfa gövdesine
# dokunulmadi) -> mimar karari beklemede. Karar verilince bu liste BOSALTILMALI.
KURAL_A_MUAF = ("akvaryum-terraryum-plastik-parca-uretimi",)

KAPSAM_IFADELERI = ("sertifika", "kapsam dış", "kapsamımız dış")
DUZELTME_IFADELERI = ("revizyon", "yeniden üretim", "düzeltme")
UCRET_IFADELERI = ("yeni bir iş", "ücret")
SAPMA_KOSULU = "sapma bizim aldığımız ölçüden"


def kucult(s):
    """Turkce-duyarli kucultme (I -> ı, İ -> i)."""
    return s.replace("İ", "i").replace("I", "ı").lower()


def etiketsiz(html):
    return re.sub(r"<[^>]+>", " ", html)


def sayfalari_yukle():
    sys.path.insert(0, BURASI)
    import sayfalar  # noqa: E402
    return sayfalar.CONTENT_PAGES


def main():
    try:
        sayfalar_listesi = sayfalari_yukle()
    except Exception as hata:  # fail-closed
        print("KIRMIZI: sayfalar.py import edilemedi -> %r" % (hata,))
        return 1

    if not sayfalar_listesi:
        print("KIRMIZI: CONTENT_PAGES bos")
        return 1

    ihlaller = []
    taranan = 0
    gida_sayfa = 0
    revizyon_sayfa = 0
    gorulen_slug = set()

    for kayit in sayfalar_listesi:
        try:
            slug, _baslik, _meta, uretici = kayit
            govde = etiketsiz(uretici())
        except Exception as hata:  # fail-closed
            print("KIRMIZI: sayfa render edilemedi (%r) -> %r" % (kayit, hata))
            return 1
        if not govde.strip():
            print("KIRMIZI: bos govde -> %s" % slug)
            return 1

        taranan += 1
        gorulen_slug.add(slug)
        g = kucult(govde)

        # KURAL A
        if "gıda" in g and slug not in KURAL_A_MUAF:
            gida_sayfa += 1
            if not any(k in g for k in KAPSAM_IFADELERI):
                ihlaller.append(
                    "%s -> KURAL A: 'gida' geciyor ama kapsam/sertifika siniri YOK"
                    % slug
                )

        # KURAL B
        if slug in REVIZYON_ZORUNLU:
            revizyon_sayfa += 1
            eksik = []
            if SAPMA_KOSULU not in g:
                eksik.append("sapma kosulu")
            if not any(k in g for k in DUZELTME_IFADELERI):
                eksik.append("revizyon/duzeltme ifadesi")
            if not any(k in g for k in UCRET_IFADELERI):
                eksik.append("ucret tarafi (yeni bir is / ucret)")
            if eksik:
                ihlaller.append(
                    "%s -> KURAL B: eksik: %s" % (slug, ", ".join(eksik))
                )

    # liste bakimi: kapsam listesindeki slug gercekten var mi (fail-closed)
    for slug in REVIZYON_ZORUNLU + KURAL_A_MUAF:
        if slug not in gorulen_slug:
            print("KIRMIZI: liste bayat, CONTENT_PAGES'te yok -> %s" % slug)
            return 1

    print("taranan landing: %d" % taranan)
    print("KURAL A kapsaminda (gida gecen): %d sayfa" % gida_sayfa)
    print("KURAL B kapsaminda (olcu/revizyon): %d sayfa" % revizyon_sayfa)
    if KURAL_A_MUAF:
        print("KURAL A muafiyeti (mimar karari bekliyor): %s" % ", ".join(KURAL_A_MUAF))

    if ihlaller:
        print("ihlal: %d" % len(ihlaller))
        for i in ihlaller:
            print("  KIRMIZI %s" % i)
        return 1

    print("ihlal: 0")
    print("YESIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
