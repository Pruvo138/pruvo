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

    Muafiyet ACIK + ADLI + GEREKCELI + BAGLAM-DOGRULAMALI (KURAL_A_MUAF):
    kelime baska bir anlam ekseninde geciyorsa (or. hayvan yemi) sayfa muaf
    olabilir; ama muafiyet SESSIZ olamaz. Gerekcesiz muafiyet girisi kapiyi
    KIRMIZI yapar; muaf sayfada "gida" gecisleri beyan edilen izinli baglamin
    DISINA cikarsa muafiyet duser ve KURAL A normal isler (silent-hole yok).

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

# --- KURAL A muafiyeti (ACIK + ADLI + GEREKCELI) -----------------------------
# Mimar karari (KraL): muafiyet SESSIZ olmayacak. Her kalem icin
#   "gerekce"       -> neden bu sayfada "gida" bir hizmet vaadi DEGIL (zorunlu,
#                      bos/kisa ise kapi KIRMIZI; ci-kapsam IZIN_LISTESI deseni)
#   "izinli_baglam" -> "gida" kelimesinin gecmesine izin verilen tam ifadeler.
#                      Sayfadaki HER "gida" gecisi bu ifadelerden birinin
#                      icinde olmali; biri disari cikarsa muafiyet DUSER,
#                      KURAL A normal isler (yeni bir gida iddiasi sessizce
#                      muafiyetin arkasina saklanamaz).
GEREKCE_MIN = 40

KURAL_A_MUAF = {}

KURAL_A_MUAF_ALANLARI = ("gerekce", "izinli_baglam")

KAPSAM_IFADELERI = ("sertifika", "kapsam dış", "kapsamımız dış")
DUZELTME_IFADELERI = ("revizyon", "yeniden üretim", "düzeltme")
UCRET_IFADELERI = ("yeni bir iş", "ücret")
SAPMA_KOSULU = "sapma bizim aldığımız ölçüden"


def kucult(s):
    """Turkce-duyarli kucultme (I -> ı, İ -> i)."""
    return s.replace("İ", "i").replace("I", "ı").lower()


def etiketsiz(html):
    return re.sub(r"<[^>]+>", " ", html)


def muafiyet_semasi_dogrula():
    """Muafiyet tablosunun kendisini dogrular. Hata listesi doner (bos = temiz)."""
    hatalar = []
    if not isinstance(KURAL_A_MUAF, dict):
        return ["KURAL_A_MUAF bir sozluk olmali (slug -> {gerekce, izinli_baglam})"]
    for slug, kayit in KURAL_A_MUAF.items():
        if not isinstance(kayit, dict):
            hatalar.append("%s -> muafiyet kaydi sozluk degil" % slug)
            continue
        for alan in KURAL_A_MUAF_ALANLARI:
            if alan not in kayit:
                hatalar.append("%s -> muafiyet kaydinda '%s' alani YOK" % (slug, alan))
        gerekce = kayit.get("gerekce")
        if not isinstance(gerekce, str) or not gerekce.strip():
            hatalar.append(
                "%s -> GEREKCESIZ muafiyet kabul edilmiyor (gerekce bos)" % slug
            )
        elif len(gerekce.strip()) < GEREKCE_MIN:
            hatalar.append(
                "%s -> muafiyet gerekcesi cok kisa (%d karakter, en az %d)"
                % (slug, len(gerekce.strip()), GEREKCE_MIN)
            )
        baglam = kayit.get("izinli_baglam")
        if not isinstance(baglam, (tuple, list)) or not baglam:
            hatalar.append("%s -> 'izinli_baglam' bos; sinirsiz muafiyet YASAK" % slug)
        else:
            for ifade in baglam:
                if not isinstance(ifade, str) or "gıda" not in kucult(ifade):
                    hatalar.append(
                        "%s -> izinli baglam ifadesi 'gida' icermiyor: %r" % (slug, ifade)
                    )
    return hatalar


def gecisler_baglamda_mi(govde_kucuk, izinli_baglam):
    """Govdedeki HER 'gida' gecisi izinli ifadelerden birinin icinde mi?

    Doner: (kapsandi_mi, kapsanmayan_ornekler)
    """
    araliklar = []
    for ifade in izinli_baglam:
        i = kucult(ifade)
        basla = 0
        while True:
            k = govde_kucuk.find(i, basla)
            if k < 0:
                break
            araliklar.append((k, k + len(i)))
            basla = k + 1

    disarida = []
    for m in re.finditer("gıda", govde_kucuk):
        if not any(a <= m.start() and m.end() <= b for a, b in araliklar):
            pencere = govde_kucuk[max(0, m.start() - 60):m.end() + 60]
            disarida.append(re.sub(r"\s+", " ", pencere).strip())
    return (not disarida), disarida


def sayfalari_yukle():
    sys.path.insert(0, BURASI)
    import sayfalar  # noqa: E402
    return sayfalar.CONTENT_PAGES


def main():
    sema_hatalari = muafiyet_semasi_dogrula()
    if sema_hatalari:
        print("KIRMIZI: KURAL A muafiyet tablosu gecersiz")
        for h in sema_hatalari:
            print("  KIRMIZI %s" % h)
        return 1

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
    muaf_durum = {}  # slug -> "uygulandi" | "gida-yok" | "baglam-disi"

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
        muaf_kayit = KURAL_A_MUAF.get(slug)
        if "gıda" in g:
            muaf_uygula = False
            if muaf_kayit is not None:
                kapsandi, disarida = gecisler_baglamda_mi(g, muaf_kayit["izinli_baglam"])
                if kapsandi:
                    muaf_uygula = True
                    muaf_durum[slug] = "uygulandi"
                else:
                    muaf_durum[slug] = "baglam-disi"
                    ihlaller.append(
                        "%s -> MUAFIYET DUSTU: 'gida' beyan edilen izinli baglam "
                        "disinda geciyor (%d yerde). Ornek: ...%s..."
                        % (slug, len(disarida), disarida[0])
                    )
            if not muaf_uygula:
                gida_sayfa += 1
                if not any(k in g for k in KAPSAM_IFADELERI):
                    ihlaller.append(
                        "%s -> KURAL A: 'gida' geciyor ama kapsam/sertifika siniri YOK"
                        % slug
                    )
        elif muaf_kayit is not None:
            muaf_durum[slug] = "gida-yok"

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
    for slug in tuple(REVIZYON_ZORUNLU) + tuple(KURAL_A_MUAF):
        if slug not in gorulen_slug:
            print("KIRMIZI: liste bayat, CONTENT_PAGES'te yok -> %s" % slug)
            return 1

    # muafiyet bakimi: gerekcesi kalmayan muafiyet tabloda kalmaz (fail-closed)
    for slug in KURAL_A_MUAF:
        if muaf_durum.get(slug) == "gida-yok":
            print(
                "KIRMIZI: muafiyet BAYAT, sayfada artik 'gida' gecmiyor -> %s "
                "(KURAL_A_MUAF'tan cikar)" % slug
            )
            return 1

    print("taranan landing: %d" % taranan)
    print("KURAL A kapsaminda (gida gecen, muaf olmayan): %d sayfa" % gida_sayfa)
    print("KURAL B kapsaminda (olcu/revizyon): %d sayfa" % revizyon_sayfa)
    print("KURAL A muafiyeti: %d kalem" % len(KURAL_A_MUAF))
    for slug in sorted(KURAL_A_MUAF):
        kayit = KURAL_A_MUAF[slug]
        print("  - %s [%s]" % (slug, muaf_durum.get(slug, "uygulanmadi")))
        print("    izinli baglam: %s" % ", ".join(kayit["izinli_baglam"]))
        print("    gerekce: %s" % " ".join(kayit["gerekce"].split()))

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
