#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ILK EKRAN KAPISI — urun detay sablonunda fiyat/CTA erisimi + guven seridi (P2/P3).

NEDEN VAR (ArTisT olcumu, 20 Agu)
---------------------------------
  P2  375x812'de ust bantlar ekranin ~%70'ini yiyordu ve PARAMETRIK (sari seri)
      sayfalarda fiyat + "Sepete Ekle" HICBIR kaydirma noktasinda ilk ekranda
      degildi. Cozum: (a) urun sayfasindan `.info-strip` blogu KALKTI, (b) dar
      ekranda `position:fixed` bir SATIN ALMA SERIDI fiyat+CTA'yi ilk 812 px
      icinde TUTAR.
  P3  11 urun sayfasinin hicbirinde CTA'nin yaninda guven ibaresi yoktu
      (iyzico/Visa/Mastercard yalniz footer'daydi). Cozum: CTA'nin hemen altina,
      sayfanin %100'une basilan GUVEN SERIDI.

BU KAPININ IDDIASI
------------------
  A1  Her render yolunda SATIN ALMA SERIDI TAM 1 adet ve fiyat+CTA TASIYOR.
  A2  Her render yolunda GUVEN SERIDI TAM 1 adet (P3: sablonun %100'u).
  A3  `.info-strip` urun sayfasindan KALKTI (P2a) — hicbir yolda yok.
  A4  🔴 GUVEN SERIDI HUKUKI VAAT TASIMAZ: iade/cayma HAKKI iddiasi YOK,
      teslim SURESI jetonu YOK, kargo UCRETI/bedava esigi YOK.
  A5  Yasal link TEK KAYNAKTAN: href slug'i + gorunur etiket
      `sayfalar.CONTENT_PAGES`ten TURER (uydurma ad drift kirmizisidir).
  A6  ID TEKLIGI: serit ikinci bir #cartBtn / #opsiyonFiyat / #sinifBeyan DOGURMAZ.
  A7  DELEGASYON: serit butonu #cartBtn'e delege eder (ikinci sepet mantigi yok) ve
      fiyati sunucudan BOS gelir (istemcide aynalanir; uydurma tutar basilmaz).

A4 NEDEN BURADA (ve `cayma-beyani-kapisi.py`da DEGIL)
----------------------------------------------------
O kapinin `CAYMA_RE` deseni "cayma" kokunden turer ve "iade" kelimesini YAKALAMAZ;
yani "degisim/iade hakki" ibaresi 23.968 ozel uretim sayfasina SESSIZCE girebilirdi.
Olcuye ozel uretim Mesafeli Sozlesmeler Yonetmeligi m.15 kapsaminda cayma hakki
DISINDADIR — o ibare VAR OLMAYAN bir hak vaat eder. Desenin dar olmasi ayri bir
kalemdir (mimar aldi); BU kapi kendi yuzeyini (guven seridi) kendi olcer.
"""

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import build                                                   # noqa: E402
import sayfalar                                                # noqa: E402


# ------------------------------------------------------------------ fikstur
# GERCEK `urunler.json` OKUNMAZ: kapi katalog buyudukce bayatlamasin ve tek bir
# urun kaydinin duzeltilmesi kapiyi yesile cevirmesin diye sentetik kayit kullanilir
# (cayma-beyani-kapisi.py ile AYNI fikstur ekseni; alanlar render_product'in FIILEN
# okudugu asgari kume).
SENTETIK_KONFIGUR = {
    "renkler": ["Siyah", "Beyaz"],
    "renkGorselIndeks": {"Siyah": 0, "Beyaz": 0},
    "boyutMm": {"min": 60, "max": 300, "adim": 10, "varsayilan": 150,
                "etiket": "Yükseklik"},
    "hacim": {"refYukseklikMm": 150, "refHacimCm3": 300.0},
    "fiyatCapalari": [[60, 500], [300, 2500]],
}


def _urun(uid, tur=Ellipsis, kategori="Marin", ek=None):
    u = {
        "id": uid,
        "baslik": "Sinama Urunu",
        "kategori": kategori,
        "marka": ["Sinama"],
        "fiyat": "1000 TL",
        "aciklama": "Sinama aciklamasi.\nIkinci satir.",
        "gorseller": ["https://media.example/%s-1.jpg" % uid],
    }
    if tur is not Ellipsis:
        u["tur"] = tur
    if ek:
        u.update(ek)
    return u


def render_yollari(mod=build):
    """(ad, html) — sablonun BES render yolu. Yol eklenirse BURAYA eklenir."""
    fiz = _urun("sinama-fiziksel", tur="fiziksel")
    nrm = _urun("sinama-normal")
    tum = [fiz, nrm]
    return [
        ("kart-secim", mod.render_product(nrm, tum)),
        ("hazir/stok", mod.render_product(fiz, tum)),
        ("konfigur", mod.render_product(
            _urun("sinama-konfigur", kategori="Dekorasyon",
                  ek={"konfigur": SENTETIK_KONFIGUR, "fiyat": "500 TL"}), tum)),
        ("semasiz-parametrik", mod.render_product(
            _urun("sinama-parametrik-semasiz", ek={"parametrik": True}), tum)),
        ("panelsiz", mod.render_product(
            _urun("sinama-panelsiz", kategori="Jeneratör"), tum)),
    ]


# ------------------------------------------------------------------ desenler
# 🔴 `\s*$` KOYMA: serit sayfanin SONU degildir (ardindan </main>, ilgili urunler ve
# footer gelir). Ilk turda oyle yazilmisti ve A1 "etiket yok" diye SAHTE KIRMIZI yakti —
# serit sayfada duruyordu (A6/A7 ayni kosumda YESILDI). Kapinin kendi deseni de
# olculmelidir: mutant tablosundaki "serit SILINDI" bu kolu ayrica kanitlar.
SATIN_SERIT_RE = re.compile(r'<div class="satin-serit"[^>]*>(.*?)</div>', re.S)
SATIN_SERIT_SAY_RE = re.compile(r'class="satin-serit"')
GUVEN_SERIT_RE = re.compile(r'<div class="guven-serit">(.*?)</div>\s*(?=<|$)', re.S)
GUVEN_SERIT_SAY_RE = re.compile(r'class="guven-serit"')
INFO_STRIP_RE = re.compile(r'class="info-strip')
GUVEN_LINK_RE = re.compile(r'<a class="guven-oge guven-link" href="([^"]+)">([^<]*)</a>')

# A4 — YASAK SINIFLAR. Kume DAR ve GEREKCELI: her biri olculmus bir hukuki/marka
# kuralina baglidir. Desen guven seridinin GORUNUR metnine uygulanir.
IADE_HAK_RE = re.compile(r"\b(cayma\w*|iade|değişim|geri\s+iade|iade\s+hakk)", re.I)
KARGO_VAAT_RE = re.compile(
    r"kargo[^.!?\n]{0,80}(ücretsiz|ucretsiz|bedava|ücret|ucret|eşik|esik|\d[\d.\s]*\s*tl)"
    r"|(ücretsiz|bedava|\d[\d.\s]*\s*tl)[^.!?\n]{0,80}kargo", re.I)
# Teslim suresi jetonu: `cayma-beyani-kapisi._sureler` ile AYNI YON — sayi + "is gunu"
# ya da teslim baglaminda gun/saat/hafta. Ikinci bir kural yazmamak icin desen ORADAN
# ithal edilir; ithal edilemezse kapi OLCULEMEDI der (sessiz gecmez).
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "cayma_kapisi", os.path.join(ROOT, "tools", "cayma-beyani-kapisi.py"))
    _cayma = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_cayma)
    _sureler = _cayma._sureler
    SURE_KAYNAGI = "cayma-beyani-kapisi._sureler"
except Exception as _e:                                        # pragma: no cover
    _sureler = None
    SURE_KAYNAGI = "ITHAL EDILEMEDI: %s" % _e


def etiketsiz(html_parca):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html_parca)).strip()


# ------------------------------------------------------------------ olcum
def olc(mod=build, ayrintili=True):
    """(hatalar, satirlar). hatalar bos = YESIL."""
    hatalar, rapor = [], []

    def ol(kod, iddia, gecti, ek=""):
        rapor.append("%-4s %-58s %s%s"
                     % (kod, iddia, "✅" if gecti else "❌",
                        ("  %s" % ek) if ek else ""))
        if not gecti:
            hatalar.append("%s: %s%s" % (kod, iddia, ("  -> %s" % ek) if ek else ""))

    yollar = render_yollari(mod)
    rapor.append("RENDER YOLU=%d" % len(yollar))

    # --- A1
    a1 = []
    for ad, h in yollar:
        adet = len(SATIN_SERIT_SAY_RE.findall(h))
        if adet != 1:
            a1.append("%s: serit adedi=%d" % (ad, adet))
            continue
        if 'id="seritFiyat"' not in h:
            a1.append("%s: #seritFiyat yok" % ad)
        if 'id="seritSepet"' not in h:
            a1.append("%s: #seritSepet yok" % ad)
        if "Sepete Ekle" not in (SATIN_SERIT_RE.search(h).group(1)
                                 if SATIN_SERIT_RE.search(h) else ""):
            a1.append("%s: seritte 'Sepete Ekle' etiketi yok" % ad)
    ol("A1", "SATIN ALMA SERIDI tam 1 adet + fiyat/CTA dugumleri var", not a1, "; ".join(a1))

    # --- A2
    a2 = ["%s: adet=%d" % (ad, len(GUVEN_SERIT_SAY_RE.findall(h)))
          for ad, h in yollar if len(GUVEN_SERIT_SAY_RE.findall(h)) != 1]
    ol("A2", "GUVEN SERIDI sablonun %100'unde ve tam 1 adet", not a2, "; ".join(a2))

    # --- A3
    a3 = [ad for ad, h in yollar if INFO_STRIP_RE.search(h)]
    ol("A3", "`.info-strip` urun sayfasindan KALKTI (P2a)", not a3, "; ".join(a3))

    # --- A4  (hukuki vaat tasimaz)
    a4 = []
    if _sureler is None:
        a4.append("sure olcucusu ithal edilemedi (%s)" % SURE_KAYNAGI)
    for ad, h in yollar:
        m = GUVEN_SERIT_RE.search(h)
        if not m:
            a4.append("%s: guven seridi bulunamadi" % ad)
            continue
        # 🔴 YASAL LINKIN KENDI ETIKETI A4'TEN DISLANIR — ve bu fail-open DEGILDIR:
        # etiket A5'te `sayfalar.CONTENT_PAGES` basligina BAYT-ESIT olmak zorundadir,
        # yani oraya serbest metin (ornegin "Kolay İade Garantisi") saklanamaz. Disarida
        # birakilmasaydi kanonik sayfa ADI ("Teslimat ve İade") kapiyi SAHTE KIRMIZI
        # yakardi — sayfanin adi bir hak IDDIASI degildir. Iki iddia birbirini tutar:
        # A5 etiketi CIVILER, A4 geri kalan her seyi TARAR.
        govde = GUVEN_LINK_RE.sub("", m.group(1))
        metin = etiketsiz(govde)
        if IADE_HAK_RE.search(metin):
            a4.append("%s: IADE/CAYMA HAKKI iddiasi: %r" % (ad, metin))
        if KARGO_VAAT_RE.search(metin):
            a4.append("%s: KARGO UCRETI/esik vaadi: %r" % (ad, metin))
        if _sureler is not None and _sureler(metin):
            a4.append("%s: TESLIM SURESI jetonu seride: %s" % (ad, sorted(_sureler(metin))))
    ol("A4", "guven seridi iade-hakki / kargo-ucreti / teslim-suresi TASIMAZ",
       not a4, "; ".join(a4))

    # --- A5  (tek kaynak: CONTENT_PAGES)
    kanonik = next((b for s, b, _m, _f in sayfalar.CONTENT_PAGES
                    if s == mod.GUVEN_TESLIMAT_SLUG), None)
    a5 = []
    if not kanonik:
        a5.append("CONTENT_PAGES'te slug yok: %s" % mod.GUVEN_TESLIMAT_SLUG)
    else:
        for ad, h in yollar:
            m = GUVEN_LINK_RE.search(h)
            if not m:
                a5.append("%s: yasal link yok" % ad)
                continue
            href, etiket = m.group(1), m.group(2)
            if href != "/%s/" % mod.GUVEN_TESLIMAT_SLUG:
                a5.append("%s: href kanonik degil: %s" % (ad, href))
            if etiket != kanonik:
                a5.append("%s: etiket CONTENT_PAGES basligindan turemiyor "
                          "(%r != %r)" % (ad, etiket, kanonik))
    ol("A5", "yasal link href+etiket CONTENT_PAGES'ten TURER", not a5,
       "; ".join(a5) if a5 else "etiket=%r" % kanonik)

    # --- A6  (id tekligi)
    a6 = []
    for ad, h in yollar:
        for tekil in ("cartBtn", "opsiyonFiyat", "sinifBeyan", "seritSepet", "seritFiyat"):
            adet = len(re.findall(r'id="%s"' % tekil, h))
            if adet > 1:
                a6.append("%s: #%s x%d" % (ad, tekil, adet))
    ol("A6", "serit ikinci bir tekil id DOGURMADI", not a6, "; ".join(a6))

    # --- A7  (delegasyon + sunucu tarafinda BOS fiyat)
    js = mod.URUN_JS_SABLONU
    a7 = []
    if "btn.click()" not in js:
        a7.append("serit butonu #cartBtn'e DELEGE etmiyor (btn.click() yok)")
    if "fiyatKaynak" not in js:
        a7.append("serit fiyati aynalanmiyor (fiyatKaynak yok)")
    for ad, h in yollar:
        m = re.search(r'<span class="serit-fiyat" id="seritFiyat">(.*?)</span>', h, re.S)
        if m is None:
            a7.append("%s: serit fiyat dugumu yok" % ad)
        elif m.group(1).strip():
            a7.append("%s: sunucu seride tutar BASMIS: %r" % (ad, m.group(1)))
    ol("A7", "serit CTA delege eder + fiyati sunucudan BOS gelir", not a7, "; ".join(a7))

    if ayrintili:
        for satir in rapor:
            print(satir)
        print("SURE_OLCUCU_KAYNAGI=%s" % SURE_KAYNAGI)
    return hatalar, rapor


# ------------------------------------------------------------------ mutasyon
# 🔴 Her mutant TEK bir ekseni oldurmeli: "hepsini birden dusuren" mutant, o eksenin
# gercekten olculdugunu KANITLAMAZ ([[ad-iki-rolde-mutanti-golgeler]]).
MUTANTLAR = [
    ("serit SILINDI", "SATIN_SERIT_HTML", lambda _v: "", {"A1", "A7"}),
    ("serit IKIZLENDI", "SATIN_SERIT_HTML", lambda v: v + v, {"A1", "A6"}),
    ("guven seridi SILINDI", "GUVEN_SERIT_HTML", lambda _v: "", {"A2", "A5"}),
    ("guven seridine IADE HAKKI eklendi", "GUVEN_SERIT_HTML",
     lambda v: v.replace("</div>", '<span class="guven-oge">değişim/iade hakkı</span></div>'),
     {"A4"}),
    ("guven seridine TESLIM SURESI eklendi", "GUVEN_SERIT_HTML",
     lambda v: v.replace("</div>",
                         '<span class="guven-oge">3-5 iş günü içinde kargoya verilir</span></div>'),
     {"A4"}),
    ("guven seridine KARGO BEDAVA esigi eklendi", "GUVEN_SERIT_HTML",
     lambda v: v.replace("</div>",
                         '<span class="guven-oge">2.500 TL üzeri kargo bedava</span></div>'),
     {"A4"}),
    ("yasal link etiketi UYDURULDU", "GUVEN_SERIT_HTML",
     lambda v: re.sub(r'(guven-link" href="[^"]+">)[^<]*', r"\1Kolay İade Garantisi", v),
     {"A5"}),
]


def mutasyon_kosumu():
    print("=== TABAN ===")
    taban_hata, _ = olc()
    print("TABAN=%s" % ("YESIL" if not taban_hata else "KIRMIZI: %s" % taban_hata))
    if taban_hata:
        print("SONUC: KIRMIZI — taban zaten kirmizi, mutasyon olcumu ANLAMSIZ")
        return 1

    oldu, sagkalan = 0, []
    for ad, sabit, donustur, beklenen in MUTANTLAR:
        asil = getattr(build, sabit)
        yeni = donustur(asil)
        if yeni == asil:
            sagkalan.append("%s (CAPA TUTMADI — mutant uygulanamadi)" % ad)
            continue
        setattr(build, sabit, yeni)
        try:
            hatalar, _ = olc(ayrintili=False)
        finally:
            setattr(build, sabit, asil)
        dusen = {h.split(":", 1)[0] for h in hatalar}
        if not hatalar:
            sagkalan.append("%s (HIC kirmizi yanmadi)" % ad)
        elif not (dusen & beklenen):
            sagkalan.append("%s (yanlis eksen dustu: %s, beklenen %s)"
                            % (ad, sorted(dusen), sorted(beklenen)))
        else:
            oldu += 1
            print("MUTANT ÖLDÜ  %-42s -> %s" % (ad, sorted(dusen)))

    print("MUTANT=%d/%d" % (oldu, len(MUTANTLAR)))
    for s in sagkalan:
        print("SAGKALAN: %s" % s)
    # Taban geri alindi mi — kapi kendi olctugu modulu KIRLETMEZ.
    geri, _ = olc(ayrintili=False)
    print("GERI_ALIM=%s" % ("TEMIZ" if not geri else "KIRLI: %s" % geri))
    if oldu == len(MUTANTLAR) and not geri:
        print("SONUC: YESIL — %d mutantin hepsi HEDEF eksenden oldu" % oldu)
        return 0
    print("SONUC: KIRMIZI — mutasyon kabulunde eksik var")
    return 1


# ------------------------------------------------------------------ onizleme
# PIKSEL OLCUMU ICIN KENDI KENDINE YETEN SAYFA. `build.py` LOKALDE KOSTURULMAZ
# (CI'da kosar) — burada yalnizca `render_product` CAGRILIR, `main()` DEGIL: `_yayin/`
# uretilmez, site kurulmaz. Uretilen HTML `file://` uzerinden acilabilsin diye:
#   * `/varlik/<ad>` -> render sirasinda ZATEN yazilmis olan yerel dosya,
#   * `/secenekler.js` · `/konfigur.js` · `/jenerator/*.js` -> depo kokundeki dosya,
#   * uzak gorseller -> gri data: URI (ag istegi YOK).
# 🔴 Gorsel degistirmek OLCUMU BOZMAZ: `.main-img` yuksekligi `aspect-ratio:1/1`,
# `.thumb` ise sabit 74x74 ile CSS'ten gelir — bayt degil KUTU olculur.
# 🔴 DISK KURALI: cikti dizinini CAGIRAN SILER; bu arac depo agacina hicbir kalici
# dosya birakmaz (`varlik/` dizinini render zaten uretir, o da temizlenmelidir).
BOS_GORSEL = ("data:image/svg+xml;charset=utf-8,"
              "%3Csvg xmlns='http://www.w3.org/2000/svg' width='800' height='800'%3E"
              "%3Crect width='800' height='800' fill='%23dbe2ec'/%3E%3C/svg%3E")


def onizleme_yaz(hedef_dizin):
    """Bes render yolunu `hedef_dizin`e kendi kendine yeten HTML olarak yazar."""
    if not os.path.isdir(hedef_dizin):
        os.makedirs(hedef_dizin)
    yazilan = []
    for ad, html_metni in render_yollari():
        h = html_metni
        h = re.sub(r'(?<=["\'(])%s([A-Za-z0-9_.-]+)' % re.escape(build.VARLIK_URL_ONEK),
                   lambda m: "file://" + os.path.join(build.VARLIK_DIR, m.group(1)), h)
        for rel in ("secenekler.js", "konfigur.js", "attribution-ref.js",
                    "jenerator/hacim.js", "jenerator/konfigurator.js", "jenerator/viewer.js"):
            h = h.replace('src="/%s"' % rel,
                          'src="file://%s"' % os.path.join(build.ROOT, rel))
        h = re.sub(r'src="https?://[^"]+"', 'src="%s"' % BOS_GORSEL, h)
        yol = os.path.join(hedef_dizin, "%s.html" % ad.replace("/", "-"))
        with open(yol, "w", encoding="utf-8") as f:
            f.write(h)
        yazilan.append((ad, yol))
        print("ONIZLEME %-20s %s" % (ad, yol))
    print("ONIZLEME_SAYISI=%d" % len(yazilan))
    print("🔴 TEMIZLIK: bu dizini ve depo kokundeki `varlik/` dizinini SIL.")
    return yazilan


def main():
    ayrist = argparse.ArgumentParser()
    ayrist.add_argument("--kendini-test", action="store_true",
                        help="mutasyon kosumu (kapinin kendisi olculur)")
    ayrist.add_argument("--onizleme", metavar="DIZIN",
                        help="bes render yolunu kendi kendine yeten HTML olarak yaz "
                             "(piksel olcumu icin; dizini CAGIRAN siler)")
    args = ayrist.parse_args()
    if args.onizleme:
        onizleme_yaz(args.onizleme)
        return 0
    if args.kendini_test:
        return mutasyon_kosumu()
    hatalar, _ = olc()
    if hatalar:
        print("SONUC: KIRMIZI — %d iddia dustu" % len(hatalar))
        return 1
    print("SONUC: YESIL — ilk ekran + guven seridi iddialari tuttu")
    return 0


if __name__ == "__main__":
    sys.exit(main())
