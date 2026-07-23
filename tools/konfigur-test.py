#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KONFIGUR KABUL TESTI — konfigüre edilebilir DEKOR ürünü altyapısı (renk + boy kaydırıcı).

Kapsam (tools/build.py "konfigur" alanı + /konfigur.js + secenekler.js konfigur bayrağı):
  (a) ŞEMA: konfigur_dogrula geçerli şemayı kabul eder; bozuk mutantların HER BİRİNİ
      (min>=varsayilan, boş renkler, 'Diğer', bilinmeyen renk, hacim ref <=0, kötü görsel
      indeksi, fiyatsız ürün, parametrik:true birlikteliği...) reddeder. render_product
      geçersiz konfigur'da SystemExit ile DÜŞER (fail-closed — yanlış fiyat sessizce yayınlanamaz).
  (b) FİYAT: node ile GERÇEK /konfigur.js + /secenekler.js koşulur (kopya/taklit yok):
      boy artarken fiyat AZALMAZ, en küçük boyda fiyat TAM taban (zemin), hiçbir boyda
      tabanın altına inilmez, standart renkler (Siyah/Beyaz/Gri) fiyatı DEĞİŞTİRMEZ ve
      build.py'deki Python aynası (JS öncesi fiyat metni) node sonuçlarıyla kuruşu kuruşuna
      aynıdır (drift nöbeti). 6/10/15/20/25/30 cm fiyat tablosu rapor için basılır.
  (c) GERİ UYUMLULUK: konfigur'suz ürün sayfaları (panelsiz Dekorasyon, kart-seçim
      fonksiyonel, boy_secenekli, lisanslı, parametrik sarı) merge-base'deki ESKİ build.py
      çıktısıyla BAYT-EŞİT üretilir ve hiçbirinde konfigur izi yoktur. Eski build.py
      alınamazsa (sığ klon) bayt-eşitlik GÜRÜLTÜLÜ atlanır, iz nöbeti yine koşar.
      NOT (bayat-taban): merge sonrası merge-base HEAD'e eşitlenir -> karşılaştırma
      kendiliğinden yeşilleşir; kalıcı CI nöbeti İZ YOKLUĞU + (a)/(b)/(d) değişmezleridir.
  (d) KONFIGUR SAYFASI: JSON-LD Offer.price = taban (EN KÜÇÜK boyun) fiyatı, Merchant
      feed aynı fiyatla basılır; sayfada URUN_KONFIGUR + /konfigur.js?v= + renk butonları
      (data-gorsel) + kaydırıcı + kancalar vardır; 'Diğer'/renkOzel ve büyük butonlar YOKTUR;
      JS öncesi fiyat metni varsayılan boyun kuruşlu fiyatıdır.

Offline (ağ yok), gerçek urunler.json OKUNMAZ (sentetik fikstürler), repo dosyasına YAZMAZ.
node ZORUNLU (deploy.yml setup-node kurar); yoksa FAIL-CLOSED kırmızı.

Kullanım:  python3 tools/konfigur-test.py
"""
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import build  # noqa: E402

HATALAR = []


def kontrol(kosul, mesaj):
    if kosul:
        print("  ✅ " + mesaj)
    else:
        print("  ❌ " + mesaj)
        HATALAR.append(mesaj)


# ------------------------------------------------------------------ fikstürler
GORSELLER = [
    "https://media.pruvo3d.com/urunler/test-kurt-siyah-1.jpg",
    "https://media.pruvo3d.com/urunler/test-kurt-beyaz-1.jpg",
    "https://media.pruvo3d.com/urunler/test-kurt-gri-1.jpg",
]

KURT_KONFIGUR = {
    "renkler": ["Siyah", "Beyaz", "Gri"],
    "renkGorselIndeks": {"Siyah": 0, "Beyaz": 1, "Gri": 2},
    "boyutMm": {"min": 60, "max": 300, "adim": 10, "varsayilan": 150, "etiket": "Yükseklik"},
    "hacim": {"refYukseklikMm": 1899.739, "refHacimCm3": 239222.8},
}
TABAN_TL = 150


def urun(konfigur=None, **ek):
    p = {
        "id": "test-dekor-kurt-figuru",
        "kategori": "Dekorasyon",
        "marka": [],
        "baslik": "Dekoratif Kurt Figürü",
        "aciklama": "Özel tasarım dekoratif figür. Farklı renk seçenekleriyle üretilir.\n"
                    "Yaklaşık dış ölçüler: 60 × 40 × 150 mm",
        "fiyat": "150 TL",
        "gorseller": list(GORSELLER),
    }
    if konfigur is not None:
        p["konfigur"] = copy.deepcopy(konfigur)
    p.update(ek)
    return p


# ------------------------------------------------------------------ (a) şema doğrulaması
def test_sema():
    print("\n(a) KONFIGUR ŞEMA DOĞRULAMASI")
    kontrol(build.konfigur_dogrula(urun(KURT_KONFIGUR)) == [],
            "geçerli konfigur şeması hatasız kabul edilir")

    def mutant(ad, degistir, urun_degistir=None):
        p = urun(KURT_KONFIGUR)
        if urun_degistir:
            urun_degistir(p)
        degistir(p["konfigur"])
        hatalar = build.konfigur_dogrula(p)
        kontrol(bool(hatalar), "mutant reddedilir: %s (%s)"
                % (ad, hatalar[0] if hatalar else "HATA YOK — sessiz kabul!"))

    mutant("min >= varsayilan", lambda k: k["boyutMm"].update({"min": 150}))
    mutant("varsayilan > max", lambda k: k["boyutMm"].update({"varsayilan": 400}))
    mutant("adim 0", lambda k: k["boyutMm"].update({"adim": 0}))
    mutant("max adıma oturmuyor", lambda k: k["boyutMm"].update({"max": 305}))
    mutant("etiket boş", lambda k: k["boyutMm"].update({"etiket": " "}))
    mutant("renkler boş", lambda k: k.update({"renkler": []}))
    mutant("renkler 'Diğer' içeriyor", lambda k: k.update(
        {"renkler": ["Siyah", "Diğer"], "renkGorselIndeks": {"Siyah": 0, "Diğer": 1}}))
    mutant("bilinmeyen renk", lambda k: k.update(
        {"renkler": ["Mor"], "renkGorselIndeks": {"Mor": 0}}))
    mutant("hacim ref yüksekliği 0", lambda k: k["hacim"].update({"refYukseklikMm": 0}))
    mutant("hacim ref hacmi negatif", lambda k: k["hacim"].update({"refHacimCm3": -1}))
    mutant("renkGorselIndeks eksik anahtar", lambda k: k["renkGorselIndeks"].pop("Gri"))
    mutant("görsel indeksi aralık dışı", lambda k: k["renkGorselIndeks"].update({"Gri": 9}))
    mutant("fiyat alanı boş (taban yok)", lambda k: None,
           urun_degistir=lambda p: p.update({"fiyat": ""}))
    mutant("parametrik:true birlikteliği", lambda k: None,
           urun_degistir=lambda p: p.update({"parametrik": True}))

    # render_product fail-closed: geçersiz konfigur build'i DÜŞÜRÜR
    bozuk = urun(KURT_KONFIGUR)
    bozuk["konfigur"]["boyutMm"]["min"] = 500
    try:
        build.render_product(bozuk, [bozuk])
        kontrol(False, "render_product geçersiz konfigur'da SystemExit vermeli (sessiz üretti!)")
    except SystemExit:
        kontrol(True, "render_product geçersiz konfigur'da SystemExit ile düşer (fail-closed)")


# ------------------------------------------------------------------ (b) fiyat (gerçek JS, node)
NODE_RUNNER = r"""
"use strict";
var sec = process.argv[2], konf = process.argv[3];
require(sec);                                   // globalThis.PRUVO_SECENEK'i kurar
var KONFIGUR = require(konf);                   // /konfigur.js modülü
var SECENEK = globalThis.PRUVO_SECENEK;
var veri = JSON.parse(process.argv[4]);         // {konfigur:{...}, tabanTL:N}
var k = veri.konfigur; k.tabanFiyatTL = veri.tabanTL;
var b = k.boyutMm, seri = [], renkEsit = true;
for (var boy = b.min; boy <= b.max + 1e-9; boy += b.adim) {
  var kurus = KONFIGUR.fiyatKurus(k, boy, "Siyah", SECENEK);
  var beyaz = KONFIGUR.fiyatKurus(k, boy, "Beyaz", SECENEK);
  var gri = KONFIGUR.fiyatKurus(k, boy, "Gri", SECENEK);
  var secimsiz = KONFIGUR.fiyatKurus(k, boy, "", SECENEK);
  if (kurus !== beyaz || kurus !== gri || kurus !== secimsiz) { renkEsit = false; }
  seri.push({ boy: boy, kurus: kurus });
}
process.stdout.write(JSON.stringify({ seri: seri, renkEsit: renkEsit }));
"""


def test_fiyat():
    print("\n(b) FİYAT MONOTONLUĞU + TABAN ZEMİN (node ile gerçek /konfigur.js)")
    node = shutil.which("node")
    kontrol(bool(node), "node bulunur (FAIL-CLOSED ön koşul — deploy.yml setup-node kurar)")
    if not node:
        return None

    tmp = tempfile.mkdtemp(prefix="konfigur-test-")
    runner = os.path.join(tmp, "runner.js")
    with open(runner, "w", encoding="utf-8") as f:
        f.write(NODE_RUNNER)
    try:
        r = subprocess.run(
            [node, runner, os.path.join(ROOT, "secenekler.js"),
             os.path.join(ROOT, "konfigur.js"),
             json.dumps({"konfigur": KURT_KONFIGUR, "tabanTL": TABAN_TL})],
            capture_output=True, text=True, timeout=60)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    kontrol(r.returncode == 0, "node koşumu başarılı (stderr: %s)" % (r.stderr.strip() or "-"))
    if r.returncode != 0:
        return None
    sonuc = json.loads(r.stdout)
    seri = sonuc["seri"]

    bm = KURT_KONFIGUR["boyutMm"]
    beklenen_adet = int(round((bm["max"] - bm["min"]) / bm["adim"])) + 1
    kontrol(len(seri) == beklenen_adet,
            "tüm kaydırıcı adımları hesaplandı (%d/%d)" % (len(seri), beklenen_adet))
    kontrol(all(x["kurus"] is not None and x["kurus"] > 0 for x in seri),
            "her boyda pozitif kuruşlu fiyat üretilir")
    kontrol(seri[0]["kurus"] == TABAN_TL * 100,
            "en küçük boyda fiyat TAM taban fiyattır (zemin: %s)"
            % build.taban_fiyat_metni(TABAN_TL))
    kontrol(all(seri[i]["kurus"] >= seri[i - 1]["kurus"] for i in range(1, len(seri))),
            "boy artarken fiyat AZALMAZ (monotonluk)")
    kontrol(all(x["kurus"] >= TABAN_TL * 100 for x in seri),
            "hiçbir boyda taban fiyatın altına inilmez")
    kontrol(sonuc["renkEsit"],
            "standart renkler (Siyah/Beyaz/Gri, seçimsiz dahil) fiyatı değiştirmez")

    # Python aynası (build.py JS-öncesi fiyat metni) node ile kuruşu kuruşuna aynı mı (drift)?
    sapmalar = [x["boy"] for x in seri
                if build.konfigur_fiyat_kurus(KURT_KONFIGUR, TABAN_TL, x["boy"]) != x["kurus"]]
    kontrol(not sapmalar,
            "build.py Python aynası node/JS ile kuruşu kuruşuna aynı (sapan boy: %s)"
            % (sapmalar or "-"))

    print("  --- FİYAT TABLOSU (taban %d TL, PLA, standart renk) ---" % TABAN_TL)
    for x in seri:
        if x["boy"] in (60, 100, 150, 200, 250, 300):
            print("    %5.1f cm  ->  %s" % (x["boy"] / 10.0,
                                            build.taban_fiyat_metni(x["kurus"] / 100.0)))
    return seri


# ------------------------------------------------------------------ (c) geri uyumluluk
KONFIGUR_IZLERI = ["URUN_KONFIGUR", "konfigur.js", "konfigurBoy", "konfigurKaydirici",
                   "PRUVO_KONFIGUR", "data-gorsel"]


def eski_build_modulu():
    """merge-base'deki (dal ayrım noktası) tools/build.py'yi ayrı modül olarak yükler.
    (None, sebep) dönerse bayt-eşitlik karşılaştırması atlanır (İZ nöbeti yine koşar)."""
    for ref in ("origin/main", "main", "HEAD"):
        mb = subprocess.run(["git", "-C", ROOT, "merge-base", "HEAD", ref],
                            capture_output=True, text=True)
        if mb.returncode != 0:
            continue
        commit = mb.stdout.strip()
        kaynak = subprocess.run(["git", "-C", ROOT, "show", commit + ":tools/build.py"],
                                capture_output=True, text=True)
        if kaynak.returncode != 0:
            continue
        g = {"__file__": os.path.join(TOOLS, "build.py"), "__name__": "build_eski"}
        exec(compile(kaynak.stdout, "build_eski<%s>" % commit[:12], "exec"), g)
        return g, "%s (merge-base HEAD..%s)" % (commit[:12], ref)
    return None, "merge-base/git show alınamadı (sığ klon?)"


def test_geri_uyumluluk():
    print("\n(c) GERİ UYUMLULUK (konfigur'suz sayfalar)")
    fikstuler = [
        ("panelsiz Dekorasyon", urun(None)),
        ("kart-seçim fonksiyonel (Otomobil)", urun(
            None, id="test-oto-parca", kategori="Otomobil", marka=["Audi"],
            baslik="Test Oto Parçası", fiyat="850 TL")),
        ("boy_secenekli fonksiyonel", urun(
            None, id="test-boylu", kategori="Ev", baslik="Test Boylu Ürün", fiyat="300 TL",
            boy_secenekleri=[{"etiket": "20 cm"}, {"etiket": "30 cm", "fark_tl": 100}])),
        ("lisanslı (CC BY)", urun(
            None, id="test-lisansli", kategori="Kamera", baslik="Test Lisanslı",
            fiyat="450 TL", lisans={"tasarimci": "testci", "tur": "CC BY 4.0"})),
        ("parametrik sarı (gerçek şema: huni)", urun(
            None, id="olcuye-ozel-huni", kategori="Jeneratör",
            baslik="Ölçüye Özel Huni", fiyat="", parametrik=True)),
    ]
    tumu = [p for _, p in fikstuler]
    yeni_ciktilar = {}
    for ad, p in fikstuler:
        html = build.render_product(p, tumu)
        yeni_ciktilar[p["id"]] = html
        izler = [iz for iz in KONFIGUR_IZLERI if iz in html]
        kontrol(not izler, "konfigur izi yok: %s (sızan: %s)" % (ad, izler or "-"))

    eski, sebep = eski_build_modulu()
    if eski is None:
        print("  UYARI: eski build.py yüklenemedi -> bayt-eşitlik ATLANDI (%s). "
              "İz nöbeti + (a)/(b)/(d) koştu." % sebep)
        return
    print("  eski build.py tabanı: %s" % sebep)
    for ad, p in fikstuler:
        eski_html = eski["render_product"](p, tumu)
        esit = eski_html == yeni_ciktilar[p["id"]]
        kontrol(esit, "BAYT-EŞİT: %s" % ad)
        if not esit:
            # ilk ayrışan bölgeyi raporla (tanılama)
            y = yeni_ciktilar[p["id"]]
            i = next((j for j in range(min(len(y), len(eski_html)))
                      if y[j] != eski_html[j]), min(len(y), len(eski_html)))
            print("     ilk fark ofset %d: eski=%r yeni=%r"
                  % (i, eski_html[max(0, i - 40):i + 40], y[max(0, i - 40):i + 40]))


# ------------------------------------------------------------------ (d) konfigur sayfası
def test_konfigur_sayfasi(seri):
    print("\n(d) KONFIGUR'LU ÜRÜN SAYFASI + JSON-LD/FEED")
    p = urun(KURT_KONFIGUR)
    html = build.render_product(p, [p])

    ld_bloklar = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    kontrol(len(ld_bloklar) >= 2, "JSON-LD blokları basılır")
    product_ld = json.loads(ld_bloklar[0])
    offers = product_ld.get("offers") or {}
    kontrol(offers.get("price") == str(TABAN_TL),
            "JSON-LD Offer.price = taban (EN KÜÇÜK boy) fiyatı: %r" % offers.get("price"))
    kontrol(offers.get("priceCurrency") == "TRY", "JSON-LD priceCurrency TRY")

    feed_xml, feed_n = build.render_merchant_feed([p])
    kontrol(feed_n == 1 and ("<g:price>%d TRY</g:price>" % TABAN_TL) in feed_xml,
            "Merchant feed'e taban fiyatla girer (%d TRY)" % TABAN_TL)

    kontrol('var URUN_KONFIGUR = {"boyutMm"' in html, "inline URUN_KONFIGUR verisi basılır")
    kontrol('"tabanFiyatTL":%d' % TABAN_TL in html, "URUN_KONFIGUR.tabanFiyatTL = fiyat alanındaki taban")
    kontrol('<script src="/konfigur.js?v=' in html, "/konfigur.js sürümlü (?v=hash) yüklenir")
    kontrol('id="konfigurKaydirici"' in html and 'type="range"' in html,
            "boy kaydırma çubuğu basılır")
    kontrol('id="konfigurBoy"' in html, "boy sayı kutusu basılır")
    kontrol(html.count("data-gorsel=") == len(KURT_KONFIGUR["renkler"]),
            "her renk butonu data-gorsel taşır (görsel değişimi)")
    for r, i in KURT_KONFIGUR["renkGorselIndeks"].items():
        kontrol(('data-renk="%s" data-gorsel="%s"' % (r, GORSELLER[i])) in html,
                "renk -> görsel eşlemesi doğru: %s" % r)
    kontrol('id="renkOzel"' not in html, "'Diğer'/serbest renk kutusu YOK (standart 3 renk)")
    kontrol("Diğer" not in html.split('id="renkButonlar"')[1].split("</div>")[0],
            "renk butonlarında 'Diğer' yok")
    kontrol('<button class="cart-btn"' not in html,
            "sayfa altı büyük butonlar yerine ikon düzeni kullanılır")
    kontrol('id="cartBtn"' in html and "ikon-sepet" in html, "Sepete Ekle ikonu vardır")
    kontrol("PRUVO_KONFIGUR.kur(URUN_KONFIGUR, URUN, render)" in html,
            "kur kancası bağlı (kaydırıcı/renk değişimi render'ı tetikler)")
    kontrol("PRUVO_KONFIGUR.satiraYaz(s)" in html,
            "sepet satırı kancası bağlı (seçimler siparişe taşınır)")
    kontrol("PRUVO_KONFIGUR.tazele()" in html, "fiyat tazeleme kancası bağlı")
    kontrol("PRUVO_KONFIGUR.eksikVurgula()" in html,
            "renk seçilmeden sepete ekleme kilidi bağlı")
    kontrol(" && !URUN_KONFIGUR" in html,
            "varsayılan fiyat yazıcısı konfigur sayfasında devre dışı (çakışma yok)")
    kontrol("KART_SECIM = false" in html,
            "KART_SECIM kapalı (malzeme-kartı kilidi konfigur'da tetiklenmez)")

    if seri:
        varsayilan = KURT_KONFIGUR["boyutMm"]["varsayilan"]
        beklenen_kurus = next(x["kurus"] for x in seri if x["boy"] == varsayilan)
        beklenen_metin = build.taban_fiyat_metni(beklenen_kurus / 100.0)
        kontrol(('id="opsiyonFiyat">%s<' % beklenen_metin) in html,
                "JS öncesi fiyat metni = varsayılan boyun kuruşlu fiyatı (%s)" % beklenen_metin)


# ------------------------------------------------------------------ ana akış
def main():
    print("KONFIGUR KABUL TESTİ (dekor konfigüratörü altyapısı)")
    test_sema()
    seri = test_fiyat()
    test_geri_uyumluluk()
    test_konfigur_sayfasi(seri)
    print("-" * 70)
    if HATALAR:
        print("SONUC: KIRMIZI ❌  (%d sorun)" % len(HATALAR))
        return 1
    print("SONUC: YESIL ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
