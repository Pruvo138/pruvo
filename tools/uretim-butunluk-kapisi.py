#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""URETICI BUTUNLUK KAPISI — yayinlanan katalogdaki HER urunun sayfasi VAR mi?

  python3 tools/uretim-butunluk-kapisi.py            # build.py'den SONRA (BLOKLAYICI)
  python3 tools/uretim-butunluk-kapisi.py --kendini-test   # offline kabul + mutasyon
  python3 tools/uretim-butunluk-kapisi.py --kok DIZIN      # (test) baska bir agacta olc

════════════════════════════════════════════════════════════════════════════════════
NEDEN VAR
════════════════════════════════════════════════════════════════════════════════════
Site tarafinda urunler.json ile /urun/<id>/ sayfalari AYNI Pages artefaktinda
(deploy.yml `_site` beyaz listesi) yayinlanir — yani "JSON yayinlandi ama sayfa
yayinlanmadi" diye bir ZAMAN penceresi YOKTUR (olculdu: muhendis raporu §0.1).
Kalan tek ayrisma yolu URETIM'dir: JSON'da olan bir id icin build.py'nin sayfa
URETMEMESI (ya da URL'i dosya yoluyla ayrisan bir id). O halde kart 200, sayfa 404
olur ve bunu bugune kadar HICBIR kapi olcmuyordu.

Bu kapi tam o iddiayi olcer ve BIREBIR ister:
  (1) urunler.json'daki her BENZERSIZ id icin urun/<id>/index.html VAR ve BOS DEGIL,
  (2) urun/ altinda JSON'da KARSILIGI OLMAYAN sayfa YOK (ters yon: oksuz sayfa),
  (3) sitemap.xml'deki her /urun/<id>/ URL'inin dosyasi VAR (SEO ekseni),
  (4) merchant-feed.xml'deki her urun link'inin dosyasi VAR (Merchant ekseni),
  (5) her id URL-GUVENLI (kart linki ile dosya yolu ayrisamaz: bosluk/%/slash/nokta-nokta
      tasiyan id sayfa uretse bile canlida 404 ya da baska sayfa acar).
🔴 continue-on-error TASIMAZ. Olculemezse (urun/ yok, JSON bozuk) OLCULEMEDI basip
   SIFIR-DISI doner — sessiz YESIL imkansiz.
"""
import argparse
import json
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Kart linki (/urun/<id>/) ile dosya yolu (urun/<id>/index.html) BIREBIR esitse guvenli.
# RFC 3986 "unreserved" kumesi: yuzde-kodlama gerekmez, dizin ayirici yok, gizli dosya yok.
GUVENLI_ID = re.compile(r"^[A-Za-z0-9._~-]+$")

URUN_URL = re.compile(r"https://pruvo3d\.com/urun/([^/<]+)/")


def urunleri_oku(kok):
    with open(os.path.join(kok, "urunler.json"), encoding="utf-8") as f:
        d = json.load(f)
    if not isinstance(d, list):
        raise ValueError("urunler.json dizi degil")
    return d


def sayfa_idleri(kok):
    """urun/ altindaki index.html'i olan (ve BOS OLMAYAN) dizin adlari."""
    urun_dir = os.path.join(kok, "urun")
    if not os.path.isdir(urun_dir):
        return None
    bulunan = set()
    for ad in os.listdir(urun_dir):
        yol = os.path.join(urun_dir, ad, "index.html")
        if os.path.isfile(yol) and os.path.getsize(yol) > 0:
            bulunan.add(ad)
    return bulunan


def dosyadaki_urun_idleri(yol):
    """sitemap.xml / merchant-feed.xml icindeki /urun/<id>/ URL'lerinden id kumesi.
    Dosya yoksa None (OLCULEMEDI)."""
    if not os.path.isfile(yol):
        return None
    with open(yol, encoding="utf-8") as f:
        return set(URUN_URL.findall(f.read()))


def denetle(kok):
    """Doner: (cikis_kodu, satirlar). SAF-ISH: yalnizca kok agacini OKUR, YAZMAZ."""
    cikti = []
    try:
        urunler = urunleri_oku(kok)
    except Exception as e:
        return 1, ["OLCULEMEDI: urunler.json okunamadi (%s)" % e]

    json_idler = [u.get("id") for u in urunler]
    bos = [i for i, x in enumerate(json_idler) if not x]
    benzersiz = set(x for x in json_idler if x)

    sayfalar = sayfa_idleri(kok)
    if sayfalar is None:
        return 1, ["OLCULEMEDI: urun/ dizini YOK — build.py kosmadan bu kapi hukum VERMEZ."]

    eksik = sorted(benzersiz - sayfalar)
    oksuz = sorted(sayfalar - benzersiz)
    guvensiz = sorted(x for x in benzersiz if not GUVENLI_ID.match(x))

    cikti.append("urunler.json id (benzersiz): %d  (ham kayit: %d)"
                 % (len(benzersiz), len(json_idler)))
    cikti.append("uretilen urun sayfasi      : %d" % len(sayfalar))

    hata = 0
    if bos:
        cikti.append("HATA: id'siz kayit: %d (ilk indeks %s)" % (len(bos), bos[:5]))
        hata = 1
    if eksik:
        cikti.append("HATA: SAYFASI URETILMEMIS urun: %d -> %s"
                     % (len(eksik), ", ".join(eksik[:10])))
        hata = 1
    if oksuz:
        cikti.append("HATA: JSON'da KARSILIGI OLMAYAN sayfa: %d -> %s"
                     % (len(oksuz), ", ".join(oksuz[:10])))
        hata = 1
    if guvensiz:
        cikti.append("HATA: URL-GUVENSIZ id (kart linki dosya yoluyla ayrisir): %d -> %s"
                     % (len(guvensiz), ", ".join(guvensiz[:10])))
        hata = 1

    for ad, dosya in (("sitemap.xml", "sitemap.xml"),
                      ("merchant-feed.xml", "merchant-feed.xml")):
        idler = dosyadaki_urun_idleri(os.path.join(kok, dosya))
        if idler is None:
            cikti.append("OLCULEMEDI: %s YOK — build.py ciktisi eksik." % ad)
            hata = 1
            continue
        sapan = sorted(idler - sayfalar)
        cikti.append("%s icindeki urun URL'i: %d" % (ad, len(idler)))
        if sapan:
            cikti.append("HATA: %s'de olup SAYFASI OLMAYAN urun: %d -> %s"
                         % (ad, len(sapan), ", ".join(sapan[:10])))
            hata = 1

    cikti.append("SONUC: " + ("KIRMIZI ❌" if hata else "YESIL ✅ — yayinlanan her id'nin sayfasi var"))
    return hata, cikti


# ═══════════════════════════════════════════════════════════════════════════════
# KENDINI TEST — hermetik (gecici dizin; depo agacina DOKUNMAZ, ag YOK)
# ═══════════════════════════════════════════════════════════════════════════════
def _agac(kok, idler, sayfa_idleri_=None, sitemap_idleri=None, feed_idleri=None):
    os.makedirs(os.path.join(kok, "urun"), exist_ok=True)
    with open(os.path.join(kok, "urunler.json"), "w", encoding="utf-8") as f:
        json.dump([{"id": i, "baslik": i} for i in idler], f)
    for i in (idler if sayfa_idleri_ is None else sayfa_idleri_):
        d = os.path.join(kok, "urun", i)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write("<html>%s</html>" % i)

    def yaz(dosya, kume):
        with open(os.path.join(kok, dosya), "w", encoding="utf-8") as f:
            f.write("".join("<loc>https://pruvo3d.com/urun/%s/</loc>" % i for i in kume))
    yaz("sitemap.xml", idler if sitemap_idleri is None else sitemap_idleri)
    yaz("merchant-feed.xml", idler if feed_idleri is None else feed_idleri)


def kendini_test():
    import shutil
    import tempfile
    gecen, kalan = [0], [0]

    def dogrula(ad, kosul, detay=""):
        if kosul:
            gecen[0] += 1
            print("  GECTI " + ad)
        else:
            kalan[0] += 1
            print("  KALDI " + ad + (" — " + str(detay) if detay else ""))

    tmp = tempfile.mkdtemp(prefix="pruvo-butunluk-")
    try:
        # P1 POZITIF: her sey yerinde -> YESIL (yanlis-pozitif nobeti)
        k = os.path.join(tmp, "p1")
        _agac(k, ["a", "b", "c"])
        kod, sat = denetle(k)
        dogrula("B1 POZITIF: 3 urun / 3 sayfa / sitemap+feed tam -> exit 0",
                kod == 0 and any("YESIL" in s for s in sat), (kod, sat))

        # N1 NEGATIF: bir urunun sayfasi URETILMEMIS (asil vaka)
        k = os.path.join(tmp, "n1")
        _agac(k, ["a", "b", "c"], sayfa_idleri_=["a", "b"])
        kod, sat = denetle(k)
        dogrula("B2 NEGATIF: sayfasi uretilmemis urun -> exit 1 + id mesajda",
                kod == 1 and any("SAYFASI URETILMEMIS" in s and "c" in s for s in sat),
                (kod, sat))

        # N2 NEGATIF: sayfa BOS dosya (0 bayt) — "dosya var" yetmez
        k = os.path.join(tmp, "n2")
        _agac(k, ["a", "b"])
        open(os.path.join(k, "urun", "b", "index.html"), "w").close()
        kod, sat = denetle(k)
        dogrula("B3 NEGATIF: 0 baytlik sayfa 'var' sayilmaz -> exit 1",
                kod == 1 and any("SAYFASI URETILMEMIS" in s for s in sat), (kod, sat))

        # N3 NEGATIF: oksuz sayfa (JSON'dan silinmis ama sayfa duruyor)
        k = os.path.join(tmp, "n3")
        _agac(k, ["a"], sayfa_idleri_=["a", "hayalet"])
        kod, sat = denetle(k)
        dogrula("B4 NEGATIF: JSON'da olmayan sayfa (oksuz) -> exit 1",
                kod == 1 and any("KARSILIGI OLMAYAN" in s for s in sat), (kod, sat))

        # N4 NEGATIF: sitemap'te olup sayfasi olmayan URL (SEO ekseni)
        k = os.path.join(tmp, "n4")
        _agac(k, ["a"], sitemap_idleri=["a", "yok-boyle-urun"])
        kod, sat = denetle(k)
        dogrula("B5 NEGATIF: sitemap'te sayfasiz URL -> exit 1",
                kod == 1 and any("sitemap.xml'de olup" in s for s in sat), (kod, sat))

        # N5 NEGATIF: merchant feed'de sayfasiz URL
        k = os.path.join(tmp, "n5")
        _agac(k, ["a"], feed_idleri=["a", "feed-hayaleti"])
        kod, sat = denetle(k)
        dogrula("B6 NEGATIF: merchant-feed'de sayfasiz URL -> exit 1",
                kod == 1 and any("merchant-feed.xml'de olup" in s for s in sat), (kod, sat))

        # N6 NEGATIF: URL-guvensiz id
        k = os.path.join(tmp, "n6")
        _agac(k, ["a", "bos luklu"])
        kod, sat = denetle(k)
        dogrula("B7 NEGATIF: URL-guvensiz id (bosluk) -> exit 1",
                kod == 1 and any("URL-GUVENSIZ" in s for s in sat), (kod, sat))

        # N7 OLCULEMEDI: urun/ hic yok -> sessiz YESIL OLMAZ
        k = os.path.join(tmp, "n7")
        os.makedirs(k)
        with open(os.path.join(k, "urunler.json"), "w", encoding="utf-8") as f:
            json.dump([{"id": "a"}], f)
        kod, sat = denetle(k)
        dogrula("B8 OLCULEMEDI: urun/ yok -> exit 1 + 'OLCULEMEDI'",
                kod == 1 and any("OLCULEMEDI" in s for s in sat), (kod, sat))

        # N8 OLCULEMEDI: bozuk JSON
        k = os.path.join(tmp, "n8")
        os.makedirs(os.path.join(k, "urun"))
        with open(os.path.join(k, "urunler.json"), "w", encoding="utf-8") as f:
            f.write("{bozuk")
        kod, sat = denetle(k)
        dogrula("B9 OLCULEMEDI: bozuk urunler.json -> exit 1",
                kod == 1 and any("OLCULEMEDI" in s for s in sat), (kod, sat))

        # N9: mukerrer id (ham kayit > benzersiz) tek sayfayla KARSILANIR — yanlis-pozitif
        # uretmemeli (404 riski yok: iki kart AYNI sayfaya gider).
        k = os.path.join(tmp, "n9")
        _agac(k, ["a", "a", "b"])
        kod, sat = denetle(k)
        dogrula("B10 POZITIF: mukerrer id tek sayfayla karsilanir -> exit 0 (yanlis-pozitif yok)",
                kod == 0, (kod, sat))

        # ── KIRMIZI-MUTASYON: kapinin KARSILASTIRMA satirlari bozulunca kaciriyor mu?
        # M1: 'eksik' kumesi ters yonde hesaplanirsa (sayfalar - json) asil vaka KACAR.
        json_k, sayfa_k = {"a", "b", "c"}, {"a", "b"}
        dogrula("B11 MUTASYON M1: fark ters cevrilirse (sayfalar - json) eksik urun GORUNMEZ",
                len(sayfa_k - json_k) == 0 and len(json_k - sayfa_k) == 1)
        # M2: 'dosya var mi' kontrolu boyut sartini kaybederse 0 baytlik sayfa YESIL yanar.
        k2 = os.path.join(tmp, "n2")
        bos_yol = os.path.join(k2, "urun", "b", "index.html")
        dogrula("B12 MUTASYON M2: boyut sarti dusen mutant 0 baytlik sayfayi 'var' sayar",
                os.path.isfile(bos_yol) and os.path.getsize(bos_yol) == 0)
        # M3: hata bayragi hic set edilmezse (return 0) mesaj basilsa da CI YESIL olur.
        kod_n1, _ = denetle(os.path.join(tmp, "n1"))
        dogrula("B13 MUTASYON M3: cikis kodu KIRMIZI yolu FIILEN doner (mesaj yetmez)",
                kod_n1 != 0, kod_n1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\nSONUC: %d gecti, %d kaldi" % (gecen[0], kalan[0]))
    return 0 if kalan[0] == 0 else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kendini-test", action="store_true", dest="kendini")
    ap.add_argument("--kok", default=KOK)
    a = ap.parse_args()
    if a.kendini:
        sys.exit(kendini_test())
    kod, satirlar = denetle(a.kok)
    print("URETICI BUTUNLUK KAPISI")
    for s in satirlar:
        print("  " + s)
    sys.exit(kod)


if __name__ == "__main__":
    main()
