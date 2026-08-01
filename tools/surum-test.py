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
  2) Surum parametresi, MUSTERININ GERCEKTEN ALDIGI baytlarin hash'iyle BIREBIR esit
     olmali (sabit/yanlis degil): ?v=<x> == sha1(YAYINLANAN dosya)[:10].

CAPA: YAYINLANAN BAYT (31 Tem — eskiden KAYNAK baytiydi).
  Bu kapinin isi "onbellek kirici, kullanicinin indirdigi icerikle senkron mu" sorusudur.
  Referansi KAYNAK dosyaya baglamak, kaynak ile yayinlanan kopyanin ayristigi her
  senaryoda (yayin oncesi bir donusum adimi — ornegin yorum soyma/minify) kapiyi
  SAHTE-KIRMIZI yakar; oysa ?v= dogru, sadece kapinin baktigi yer yanlistir. Cozum
  gevsetme DEGIL GUCLENDIRME: hash artik /<rel> adresinden GERCEKTEN inen baytlardan
  hesaplanir.
  YAYINLANAN YOL KURALI (bu dosyada BAGIMSIZ tanimlanir, build'den ODUNC ALINMAZ):
    _yayin/<rel> dosyasi VARSA yayinlanan kopya odur, yoksa kaynak <rel>.
  Bu kural deploy'un kopyalama sirasiyla ayni. Kural bir gun ayrisirsa (or. dizin adi
  degisirse) kapi KAYNAGA duser ve hash TUTMAZ -> KIRMIZI. Yani ayrisma FAIL-CLOSED'dir,
  sessizce yesil kalmaz. Cozumleyicinin kendisi de her kosumda birim olarak sinanir
  (bkz. "cozumleyici oz-testi") -> main gibi _yayin'siz agaclarda kod olu kalmaz.

Onceki (surumsuz) kodda KIRMIZI (surumsuz referanslari listeler); duzeltmeyle YESIL.
Calistirma:  python3 tools/surum-test.py   (cikis kodu 0 = gecti)
"""
import os
import re
import sys
import json
import shutil
import hashlib
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import build  # noqa: E402

# taban-fiyatlar.js ana sayfada referansli -> hash'i icin once uretilmis olmali.
build.uret_taban_fiyatlar()

# Surumsuz site-ici JS: src="/....js" ardindan HEMEN " (yani ?v= YOK).
SURUMSUZ_RE = re.compile(r'<script\b[^>]*\ssrc="(/[^"?]+\.js)"')
# Surumlu: src="/....js?v=<hash>"
SURUMLU_RE = re.compile(r'<script\b[^>]*\ssrc="(/[^"?]+\.js)\?v=([0-9a-f]+)"')

# Yayin kopyalarinin dizini (deploy _site'a BURADAN kopyalar). Yoksa kaynak yayinlanir.
YAYIN_DIR = "_yayin"


def yayin_yolu(kok, rel):
    """/<rel> adresinden tarayiciya GERCEKTEN inen baytlarin diskteki yolu."""
    parca = rel.lstrip("/").split("/")
    y = os.path.join(kok, YAYIN_DIR, *parca)
    return y if os.path.isfile(y) else os.path.join(kok, *parca)


def beklenen_hash(yol):
    with open(yayin_yolu(ROOT, yol), "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:10]


def cozumleyici_oz_testi():
    """Yayinlanan-yol cozumleyicisinin birim testi (agactan bagimsiz, HER kosumda koşar).
    Boylece _yayin'siz agaclarda (or. main) bu kol OLU KOD olarak curumez."""
    hatalar = []
    kok = tempfile.mkdtemp(prefix="surum-coz-")
    try:
        os.makedirs(os.path.join(kok, "jenerator"))
        with open(os.path.join(kok, "x.js"), "w", encoding="utf-8") as f:
            f.write("KAYNAK")
        with open(os.path.join(kok, "jenerator", "y.js"), "w", encoding="utf-8") as f:
            f.write("KAYNAK-ALT")
        if yayin_yolu(kok, "/x.js") != os.path.join(kok, "x.js"):
            hatalar.append("COZUMLEYICI: yayin kopyasi YOKKEN kaynaga dusmedi")
        if yayin_yolu(kok, "/jenerator/y.js") != os.path.join(kok, "jenerator", "y.js"):
            hatalar.append("COZUMLEYICI: alt dizinde kaynaga dusmedi")
        os.makedirs(os.path.join(kok, YAYIN_DIR, "jenerator"))
        with open(os.path.join(kok, YAYIN_DIR, "x.js"), "w", encoding="utf-8") as f:
            f.write("YAYIN")
        with open(os.path.join(kok, YAYIN_DIR, "jenerator", "y.js"), "w", encoding="utf-8") as f:
            f.write("YAYIN-ALT")
        if yayin_yolu(kok, "/x.js") != os.path.join(kok, YAYIN_DIR, "x.js"):
            hatalar.append("COZUMLEYICI: yayin kopyasi VARKEN kaynak kazandi "
                           "(?v= musterinin almadigi bayttan turerdi)")
        if yayin_yolu(kok, "/jenerator/y.js") != os.path.join(kok, YAYIN_DIR, "jenerator", "y.js"):
            hatalar.append("COZUMLEYICI: alt dizinde yayin kopyasi kazanmadi")
        with open(yayin_yolu(kok, "/x.js"), "rb") as f:
            if f.read() != b"YAYIN":
                hatalar.append("COZUMLEYICI: yayin kopyasi okunmadi")
    finally:
        shutil.rmtree(kok, ignore_errors=True)
    return hatalar


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

    hatalar = cozumleyici_oz_testi()
    surumlu_toplam = 0
    yayin_kopyali = 0     # ?v='si YAYIN kopyasindan turetilen referans sayisi
    kritik = set()  # gorulen kritik dosyalar (secenekler + taban)
    varlik_gorulen = 0
    for ad, html in sayfalar.items():
        for m in SURUMSUZ_RE.finditer(html):
            yol = m.group(1)
            if yol.startswith(build.VARLIK_URL_ONEK):
                # ICERIK-ADRESLI VARLIK: onbellek kirici ADIN KENDISIDIR (sha256 ilk 10),
                # ustune ?v= yazmak ayni bayta ikinci bir surum ekseni verirdi. MUAFIYET
                # DEGIL, BASKA BICIMDE OLCUM: ad dosyanin BAYTLARINDAN yeniden turetilir;
                # tutmuyorsa bayat/yanlis dosya servis edilirdi -> KIRMIZI.
                dosya = os.path.join(ROOT, yol.lstrip("/"))
                if not os.path.isfile(dosya):
                    hatalar.append("%s: varlik dosyasi YOK -> sayfa ciplak kalir (%s)" % (ad, yol))
                    continue
                with open(dosya, encoding="utf-8") as f:
                    govde = f.read()
                temel, uz = os.path.splitext(os.path.basename(yol))
                bek = "%s-%s%s" % (temel.rsplit("-", 1)[0], build.varlik_hash(govde), uz)
                if bek != os.path.basename(yol):
                    hatalar.append("%s: varlik adi kendi BAYTLARINDAN turemiyor (%s != %s)"
                                   % (ad, os.path.basename(yol), bek))
                else:
                    varlik_gorulen += 1
                continue
            hatalar.append("%s: SURUMSUZ script src=\"%s\" (onbellek kirici yok)" % (ad, yol))
        for m in SURUMLU_RE.finditer(html):
            surumlu_toplam += 1
            yol, ver = m.group(1), m.group(2)
            if yol in ("/secenekler.js", "/taban-fiyatlar.js"):
                kritik.add(yol)
            dosya = yayin_yolu(ROOT, yol)          # MUSTERIYE INEN baytlar
            if not os.path.isfile(dosya):
                hatalar.append("%s: %s dosyasi yok (hash dogrulanamadi)" % (ad, yol))
                continue
            if os.path.normpath(dosya).startswith(
                    os.path.normpath(os.path.join(ROOT, YAYIN_DIR)) + os.sep):
                yayin_kopyali += 1
            bek = beklenen_hash(yol)
            if ver != bek:
                hatalar.append("%s: %s surumu '%s' != YAYINLANAN icerik hash'i '%s' "
                               "(olculen bayt: %s)" % (ad, yol, ver, bek,
                                                       os.path.relpath(dosya, ROOT)))

    # Kapsam yoklamasi (varlik kolu): urun sayfalari icerik-adresli JS varligi REFERANS
    # ETMELI. Sifir gorulme = ya taşıma geri alinmis ya regex bosa dusmus; iki halde de
    # yukaridaki ad-dogrulamasi HIC kosmamis olur -> yalancı yesil.
    if varlik_gorulen == 0:
        hatalar.append("varlik kolu HIC olculmedi: hicbir sayfada %s*.js referansi yok "
                       "(regex/kapsam bosa dustu mu?)" % build.VARLIK_URL_ONEK)

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
    print("YESIL — surum testi gecti (%d sayfa, %d surumlu referans, hepsi YAYINLANAN "
          "icerigin hash'iyle esit; %d referans _yayin/ kopyasindan olculdu, %d kaynaktan; "
          "kritik: secenekler.js + taban-fiyatlar.js; cozumleyici oz-testi 6/6)."
          % (len(sayfalar), surumlu_toplam, yayin_kopyali, surumlu_toplam - yayin_kopyali))


if __name__ == "__main__":
    main()
