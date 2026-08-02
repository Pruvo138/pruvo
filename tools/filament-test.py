#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FILAMENT REHBERI KABUL TESTLERI — tools/paket-filament-rehberi.md'deki 7 test.

Kullanim:
    python3 tools/filament-test.py              # 7 testin hepsi (parite dahil, ag gerekir)
    PARITE=0 python3 tools/filament-test.py     # test 5 (parite, ag) atlanir

Once tools/build.py'yi CALISTIRIR (uretilen sayfalar taze olsun), sonra sirayla:
  1. urunler.json DEGISMEMIS (git diff bos — paket urun verisine dokunmaz)
  2. 20 rastgele urun sayfasi (+ EN AZ BIR parametrik ZORLA dahil): sitede satilan filament
     cipleri (ABS/Karbon HARIC) + tavsiye rozeti + balon metni filamentler.json ile birebir +
     kategori haritasina gore dogru tavsiye (parametrik urunde OZEL KILIF YOK — F kalemi)
  3. hicbir uretilen sayfada "3d bask" / "her renk" yok
  4. /malzeme-rehberi/ uretildi, footer linki var, sitemap'te
  5. node tools/parite-test.js 300 + node tools/parite-ege.js 200 YESIL (aciklama degismedi)
  6. override: tavsiyeFilament alanli sahte urunle render -> harita degil override basiliyor
  7. mobil tooltip: DOM/CSS duzeyinde dogrulama (balon + .acik toggle JS + aria-expanded)
  8. ABS/Karbon Katkili urun sayfasinda CIP OLARAK basilmiyor (site seceneği degil, sadece
     /malzeme-rehberi/ + WhatsApp notu)

KART-SECIM (Okan, 16 Tem — malzeme dropdown -> kart secici):
  9  (a) fonksiyonel sayfada malzeme dropdown YOK; kartlar data-malzeme tasir; tiklama SECER
 10  (b) sayfa acilisinda secili kart YOK + fiyat "…'den baslayan" halinde
 11  (c) secimsiz "Sepete Ekle" -> sepete eklenmez + titreme/kirmizi sinifi eklenir (CSS+JS)
 12  (d) secimle fiyat KATSAYILI guncellenir (JS wiring + secenekler.js kuruş matematigi)
 13  (e) alt paragraf ("Sepete ekleyip…") HICBIR urun sayfasinda yok
 14  (f) "WhatsApp'tan Sor" secim SARTI ARAMAZ (link her zaman calisir)

KART SADELESTIRME (Okan, 16 Tem — liste kartlarindan iki oge kalkti):
 20  ana sayfa kartlarinda "Sepete Ekle" butonu ve "Tavsiye:" cipi YOK (hizli-ekleme yolu
     tamamen kalkti -> hicbir UI yolu malzemesiz/varsayilan-PLA kalem ekleyemez); urun
     sayfasinda cartBtn + malzeme kartlari DURUYOR (regresyon)

EYLEM IKONLARI (Okan madde 7, 16 Tem — buyuk butonlar -> Adet satirinda ikon cifti):
 21  (l) kart-secim sayfasinda sayfa alti buyuk buton YOK; Adet satirinda aria-label+title'li
     2 ikon buton VAR (44px dokunma alani CSS'te); SEMALI PARAMETRIK (sari) sayfa da ayni
     kart-secim duzeninde (F kalemi, 16 Tem gece — commit 68cf6939 ile Okan karari)
 22  (m) ikon sepet butonu ayni cartBtn — secimsiz ekleme kapisi + titreme AYNEN calisiyor
 23  (n) WhatsApp ikonu dogru wa.me hedefine gidiyor (statik href + JS canli mesaj guncelleme)
 24  NOBETCI: buyuk buton yolu (build.py BUYUK_BUTONLAR_HTML) hala CANLI — SENTETIK panelsiz
     (semasiz Jeneratör) urunde buyuk butonlar YERINDE, ikon cifti YOK. Test 21'den parametrik
     iddiasi kalkinca bu kod dalini olcen tek test burasidir (Dekorasyon/Oyun-Hobi 23 Tem
     FONKSIYONEL oldu -> gercek katalogda panelsiz urun kalmadi, nobetci sentetik olcer).
 25  KAPI: urunler.json'da FIILEN kullanilan her kategori ya tavsiye uretir ya da testin
     icindeki BILINCLI-BOS listesinde yer alir (yeni kategori sessizce tavsiyesiz kalamaz).

FIKSTUR NOBETI (1 Agu — bu paketin fiksturu KAYMISTI):
 26  Bu dosyadaki iddialarin TAMAMI OZEL URETIM (baski) urun sayfasi icindir: filament cipi,
     malzeme karti, renk butonu, kart-secim kapisi. `"tur":"fiziksel"` tasiyan kayit HAZIR
     TICARI MALDIR ve build.py o sayfaya bu arayuzu BILEREK basmaz (bkz.
     tools/fiziksel-urun-kapisi.py). Fikstur eskiden `urunler[0]` / "ilk fonksiyonel urun"
     ile secildigi icin katalogun basina fiziksel urunler girince testler ANLAMSIZ bir vaka
     uzerinde kirmizi yaniyordu ("7/25") — kod degil FIKSTUR yanlisti, ama cikti bunu
     SOYLEMIYORDU. Artik fikstur `fikstur_sec()` ile EHLIYET suzgecinden gecerek secilir ve
     TEST 26 kaymayi ACIKCA "YANLIS VAKA" diye kirmizi yakar.
"""
import html
import json
import os
import random
import re
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import filament_ortak

# BUILD SIZINTISI: adim 0'da kosan build.py, asagidaki 4 IZLENEN yasal sayfaya Meta
# piksel enjekte eder ve ana checkout'u KIRLETIR (git status M gizlilik/... vb.). Testler
# uretilmis sayfalara karsi kosulduktan SONRA bu 4 dosyayi HEAD'e geri yukleyip calisma
# agacini temiz birakiyoruz (aksi halde baska bir oturumun genis commit'i uretilmis izleme
# kodunu KAYNAGA sokabilir). Bu liste build.py'nin dokundugu TEK tracked dosya kumesidir
# (urun/, sitemap.xml, robots.txt vb. gitignore'da).
YASAL_SAYFALAR = [
    "gizlilik/index.html", "hakkimizda/index.html",
    "iletisim/index.html", "sss/index.html",
]


def _yasal_sayfalari_geri_yukle():
    """build.py'nin Meta-piksel enjeksiyonuyla kirlettigi 4 yasal sayfayi HEAD'e geri yukle.
    Bu adim KALDIRILIRSA 'git status' KIRLI doner (kirmizi-mutasyon nobeti — kabul testi #5)."""
    subprocess.run(["git", "checkout", "--", *YASAL_SAYFALAR],
                   cwd=ROOT, capture_output=True, text=True)

SONUC = []


# ── FIKSTUR EHLIYETI (SAF — kabul iddialari TEST 26'da) ────────────────────────────────
# 🔴 NEDEN: bu paketin her iddiasi OZEL URETIM (baski) urun sayfasinin arayuzunu olcer.
# `tur == "fiziksel"` kayit HAZIR TICARI MALDIR; build.py o sayfaya filament cipi / malzeme
# karti / renk butonu BILEREK basmaz. Fikstur oraya duserse test "kod kirik" der ama gercekte
# VAKA yanlistir. Bu iki fonksiyon o kaymayi imkansiz kilar (secim) + gorunur yapar (TEST 26).
class FiksturKaymasi(Exception):
    """Fikstur secimi EHIL urun bulamadi. Sessiz/anlamsiz sonuc yerine ACIK duruş."""


def baski_urunu_mu(u):
    """Fikstur EHLIYETI. FAIL-CLOSED: `tur` alani YOK/BOS olan kayit ozel uretim (baski)
    urunudur; tanidigimiz ("fiziksel") ya da TANIMADIGIMIZ her deger fikstur DISIDIR.
    Yarin yeni bir `tur` degeri eklenirse bu paket sessizce kaymak yerine DARALIR."""
    if not isinstance(u, dict):
        return False
    return not (u.get("tur") or "").strip()


def fikstur_sec(urunler, sart, ad):
    """Sarti saglayan ILK EHIL urun (deterministik: katalog sirasi). Yoksa PATLAR —
    fikstursuz kosum "yesil" de "anlamsiz kirmizi" de olmamali."""
    for u in urunler or []:
        if sart(u) and baski_urunu_mu(u):
            return u
    raise FiksturKaymasi(
        "YANLIS VAKA (%s): sarti saglayan EHIL (ozel uretim) urun YOK — bu paketin "
        "iddialari yalniz baski urun sayfasi icin anlamli." % ad)


# ── PARITE CIKIS KODU ESLEMESI (SAF — kabul testi asagida, `--parite-eslem-testi`) ──────
# 🔴 CIKIS KODU SOZLESMESI TEK KAYNAKTADIR: tools/parite-ortak.js dosya basindaki
#    "CIKIS KODU SOZLESMESI" blogu. Burada tablo TEKRARLANMAZ (dort tuketicide dort ayri
#    surum olusmasi tam olarak yasanan hataydi). Bu dosyanin sozlesmedeki YERI:
#        exit 3 -> ATLANDI (GORUNUR sebep, bu testi BLOKLAMAZ)
#    Diger uc tuketici ve gerekceleri o blokta yazilidir; eslesmenin dordu birden
#    tools/parite-sozlesme-test.py ile TEK TEK olculur.
# ⚠️ TUZAK (yasandi): baska bir betigin exit 2'si yanlislikla FAIL sayilmisti. Bu yuzden
# eslesme SAF fonksiyona alindi ve fikstur'le tek tek olculuyor — tahminle degil.
PARITE_GECTI = "GECTI"
PARITE_KIRMIZI = "KIRMIZI"
PARITE_ATLANDI = "ATLANDI"


def parite_sebep_ayikla(cikti):
    """Cikis 3'un GORUNUR sebebi. SAF.

    ⚠️ Sebep metni OLCULEN kanittan turetilir; 'checkout bayat' KESIN HUKUM olarak
    yazilmaz (ayni imza D1'deki yetim satirdan da cikar — parite-ortak.js "TESHIS
    DURUSTLUGU"). Sirasi ONEMLI: fikstur modu ve sert arizalar once."""
    c = cikti or ""
    if "FIKSTUR MODU" in c:
        return ("olculemedi: FIKSTUR MODU (test-only env) — kanonik katalog/uc OLCULMEDI, "
                "parite BELGELENMEDI")
    if "WAF/UA" in c:
        return "olculemedi: WAF/UA duvari (403) — ayrisma SAYILMADI"
    if "HIZ SINIRI" in c:
        return "olculemedi: hiz siniri (429) — yeniden denemeler tukendi"
    if "ZAMAN ASIMI" in c:
        return "olculemedi: zaman asimi — canli uc susuyor"
    if "TAVAN" in c:
        return "olculemedi: supurme tavani asildi — 'yerel ⊆ D1' kaniti uretilemedi"
    m = re.search(r"D1 FAZLALIGI: yerel=(\d+) < canli=(\d+) \| fazla=(\d+)", c)
    if m:
        return ("olculemedi: katalog farki — yerel %s < canli %s (D1'de %s fazla satir); "
                "sebep AYIRT EDILEMEDI: dal bayat ya da D1'de yetim satir"
                % (m.group(1), m.group(2), m.group(3)))
    if "SENKRON GEC" in c:
        return "olculemedi: katalog farki (senkron gecikmesi ya da yetim satir)"
    return "olculemedi (sebep cikti'da bulunamadi)"


def parite_exit_yorumla(exit_kodu, cikti=""):
    """SAF. Doner (ok, etiket, sebep). ok=False ise TEST 5 KIRMIZI yanar."""
    if exit_kodu == 0:
        return (True, PARITE_GECTI, "")
    if exit_kodu == 3:
        return (True, PARITE_ATLANDI, parite_sebep_ayikla(cikti))
    if exit_kodu == 1:
        return (False, PARITE_KIRMIZI, "aciklanamayan ayrisim (yerelde var/D1'de yok ya da SIRA)")
    if exit_kodu == 2:
        return (False, PARITE_KIRMIZI, "test KOSULAMADI (exit 2) — bot kaynagi/fonksiyonu yok")
    return (False, PARITE_KIRMIZI, "beklenmeyen cikis kodu: %s" % exit_kodu)


def parite_eslem_testi():
    """`python3 tools/filament-test.py --parite-eslem-testi` — agsiz, build'siz fikstur."""
    kalan = []

    def ona(kosul, ad):
        print("  %s %s" % ("✅" if kosul else "❌", ad))
        if not kosul:
            kalan.append(ad)

    # VERI CAPASI YOK: asagidaki sayilar SENTETIK fikstur girdisidir, gercek katalog/sorgu
    # sayisi DEGILDIR (atil bir "1199" literali burada capa gorevi goruyordu — kaldirildi).
    ok, et, sb = parite_exit_yorumla(0, "SONUC: BIREBIR PARITE ✅ (N sorgu, site ile ayni)")
    ona(ok and et == PARITE_GECTI and sb == "", "exit 0 -> GECTI")

    ok, et, sb = parite_exit_yorumla(1, "SONUC: PARITE YOK ❌ (7 aciklanamayan / 300 sorgu)")
    ona((not ok) and et == PARITE_KIRMIZI, "exit 1 -> KIRMIZI")

    cikti3 = ("  D1 FAZLALIGI: yerel=1234 < canli=1299 | fazla=65 satir; supurme kaniti: "
              "yerel id'lerin TAMAMI D1'de. SEBEP AYIRT EDILEMEDI -> (a) dal/checkout BAYAT "
              "ya da (b) D1'de YETIM satir.\n"
              "⚪ SENKRON GECİKMESİ / KATALOG FARKI (108 ayrisim) — PARITE KIRIK DEGIL.")
    ok, et, sb = parite_exit_yorumla(3, cikti3)
    ona(ok and et == PARITE_ATLANDI, "exit 3 -> ATLANDI (KIRMIZI DEGIL)")
    ona("1234" in sb and "1299" in sb and "65" in sb,
        "exit 3 sebebi SAYIYLA GORUNUR (olculen kanit)")
    ona("AYIRT EDILEMEDI" in sb and "yetim" in sb.lower(),
        "exit 3 sebebi KESIN HUKUM basmiyor (iki olasilik ADIYLA)")

    ok, et, sb = parite_exit_yorumla(3, "⚪ ÖLÇÜLEMEDİ: WAF/UA — canli uc HTTP 403 dondu")
    ona(ok and et == PARITE_ATLANDI and "WAF/UA" in sb, "exit 3 (WAF/UA) -> ATLANDI + sebep")

    ok, et, sb = parite_exit_yorumla(3, "⚪ ÖLÇÜLEMEDİ: HIZ SINIRI (429) — 3 deneme TUKENDI")
    ona(ok and et == PARITE_ATLANDI and "429" in sb, "exit 3 (429) -> ATLANDI + sebep")

    ok, et, sb = parite_exit_yorumla(3, "⚪ ÖLÇÜLEMEDİ: ZAMAN ASIMI (20000 ms/istek)")
    ona(ok and et == PARITE_ATLANDI and "zaman asimi" in sb.lower(),
        "exit 3 (zaman asimi) -> ATLANDI + sebep")

    ok, et, sb = parite_exit_yorumla(3, "⚪ ÖLÇÜLEMEDİ: TAVAN — supurme TAVANI asildi")
    ona(ok and et == PARITE_ATLANDI and "tavan" in sb.lower(),
        "exit 3 (supurme tavani) -> ATLANDI + sebep")

    # A15 NOBETI: alt-kume/fikstur kosumu ATLANDI'ya dusse bile sebebi tuketiciye ULASMALI.
    ok, et, sb = parite_exit_yorumla(3, "⚠️ FIKSTUR MODU: test-only env verildi (PARITE_URUNLER)")
    ona(ok and et == PARITE_ATLANDI and "FIKSTUR MODU" in sb,
        "exit 3 (PARITE_URUNLER/fikstur modu) -> ATLANDI + GORUNUR uyari (yutulmaz)")

    ok, et, sb = parite_exit_yorumla(2, "index.js'te urunAra() bulunamadi")
    ona((not ok) and et == PARITE_KIRMIZI, "exit 2 -> KIRMIZI (fail-closed, kosulamadi)")

    ok, et, sb = parite_exit_yorumla(None, "zaman asimi")
    ona((not ok) and et == PARITE_KIRMIZI, "exit None -> KIRMIZI")

    print("-" * 70)
    if kalan:
        print("PARITE ESLEM FIKSTURU: %d iddia KALDI ❌" % len(kalan))
        return 1
    print("PARITE ESLEM FIKSTURU: hepsi YESIL ✅")
    return 0


def kayit(no, ad, gecti, detay=""):
    SONUC.append((no, ad, gecti, detay))
    print("  %s TEST %d — %s%s" % ("✅" if gecti else "❌", no, ad,
                                   (" | " + detay) if detay else ""), flush=True)


def sayfa(pid):
    """URETILEN urun sayfasinin YAYIN YUZEYI (sayfa + referans ettigi /varlik/ dosyalari).

    2 Agu 2026: ortak CSS/JS sayfaya gomulu olmaktan cikip icerik-adresli
    /varlik/<ad>-<hash> dosyalarina tasindi. Ham index.html okunursa bu testin aradigi
    kural (44x44 dokunma alani, renk butonu mantigi, canli WhatsApp mesaji ...) hala
    TARAYICIYA INIYOR ama bu metinde bulunmaz -> olcum SESSIZCE korelir, test yalanci
    yesil yanar. TEK KAYNAK sargi: tools/yayin_yuzey.py."""
    import yayin_yuzey
    with open(os.path.join(ROOT, "urun", pid, "index.html"), encoding="utf-8") as f:
        return yayin_yuzey.govde(f.read(), ROOT)


def main():
    print("0) tools/build.py calisiyor (uretim taze olsun)...", flush=True)
    r = subprocess.run([sys.executable, os.path.join(TOOLS, "build.py")],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        print(r.stdout + r.stderr)
        sys.exit("build.py HATA verdi — testler kosulmadi.")
    print("   " + r.stdout.strip())

    with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    ref = filament_ortak.referans()
    site_fil = [f for f in ref["filamentler"] if f.get("site")]
    ozel_fil = [f for f in ref["filamentler"] if not f.get("site")]

    # ── FIKSTUR SECIMI (TEK YER — kayma nobeti TEST 26) ────────────────────────────────
    # TEK KAYNAK: build.FONKSIYONEL_KATEGORILER (elle kopya YOK -> drift olmaz).
    import importlib
    build = importlib.import_module("build")
    # YAYIN YUZEYI SARGISI (2 Agu 2026): sayfanin ORTAK CSS/JS'i artik gomulu degil,
    # icerik-adresli /varlik/<ad>-<hash> dosyalarindan REFERANSLA geliyor. Bu test
    # sayfanin <style>/<script> govdesinde kural (44x44 dokunma alani, renk butonu
    # mantigi ...) ariyor; ham HTML'i okursa aradigi kural TARAYICIYA INMEYE DEVAM
    # ETTIGI HALDE metinde bulunmaz -> olcum SESSIZCE korelir. TEK KAYNAK sargi:
    # tools/yayin_yuzey.py referanslari icerikleriyle yerine koyar.
    if not getattr(build.render_product, "_yayin_yuzeyli", False):
        yayin_yuzey = importlib.import_module("yayin_yuzey")
        _ham = build.render_product

        def _sarili(*a, **k):
            return yayin_yuzey.govde(_ham(*a, **k))
        _sarili._yayin_yuzeyli = True
        build.render_product = _sarili
    FONK = set(build.FONKSIYONEL_KATEGORILER)
    # HAVUZ = TEST 2'nin ornekleme evreni; fiziksel (hazir ticari mal) kayit DISARIDA.
    # Eskiden duz `random.sample(urunler, 20)` idi ve katalogtaki 806 fiziksel urun yuzunden
    # her kosumda ~%63 olasilikla anlamsiz kirmizi yaniyordu (olculdu).
    havuz = [u for u in urunler if baski_urunu_mu(u)]
    try:
        ornek_urun = fikstur_sec(urunler, lambda u: not u.get("parametrik"),
                                 "ornek urun sayfasi")
        fonk_urun = fikstur_sec(
            urunler, lambda u: u.get("kategori") in FONK and not u.get("parametrik"),
            "fonksiyonel kart-secim sayfasi")
        par_u = fikstur_sec(urunler, lambda u: bool(u.get("parametrik")),
                            "parametrik (sari) sayfa")
    except FiksturKaymasi as e:
        # Fikstursuz kosum RAPOR URETMEZ: sessizce anlamsiz kirmizi yakmaktansa DUR.
        print("  ❌ TEST 26 — FIKSTUR NOBETI | %s" % e, flush=True)
        sys.exit(1)
    ornek_sayfa = sayfa(ornek_urun["id"])
    fs = sayfa(fonk_urun["id"])
    ps21 = sayfa(par_u["id"])

    # ---- 1) urunler.json degismemis
    d = subprocess.run(["git", "diff", "--name-only", "--", "urunler.json"],
                       capture_output=True, text=True, cwd=ROOT)
    kayit(1, "urunler.json degismemis (git diff bos)", d.stdout.strip() == "",
          d.stdout.strip() or "temiz")

    # ---- 2) 20 rastgele urun sayfasi (parametrik KAPSAMI garantili): cipler + rozet + balon
    # DETERMINIZM: 7903 urunun yalnizca 21'i parametrik -> duz random.sample parametrigi
    # ~%5 olasilikla yakalar; test o yuzden yazi-tura kirmizi/yesil olurdu. Rastgeleligi
    # koruyoruz (genis kapsam) ama en az BIR parametrik urunu ZORLA orneklemin icine koyuyoruz.
    par_hepsi = [u for u in havuz if u.get("parametrik")]
    ornek = random.sample(havuz, 20)
    if par_hepsi and not any(u.get("parametrik") for u in ornek):
        ornek[random.randrange(len(ornek))] = random.choice(par_hepsi)
    hatalar = []
    for p in ornek:
        s = sayfa(p["id"])
        cip_n = len(re.findall(r'class="fil-cip( tavsiyeli)?"', s))
        if cip_n != len(site_fil):
            hatalar.append("%s: cip sayisi %d != %d" % (p["id"], cip_n, len(site_fil)))
            continue
        for f in site_fil:
            if html.escape(f["uzun"], quote=True) not in s:
                hatalar.append("%s: '%s' balon metni birebir degil" % (p["id"], f["ad"]))
        for f in ozel_fil:
            if html.escape(f["uzun"], quote=True) in s:
                hatalar.append("%s: '%s' (ozel talep) urun sayfasinda cip olarak var" % (p["id"], f["ad"]))
        # OZEL KILIF YOK: F kalemi (Okan, 16 Tem gece) sonrasi parametrik (sari) sayfa normal
        # sayfayla BIREBIR -> rozet beklentisi HER uronde ayni sekilde kategoriden turer.
        # Bugun "Jeneratör" kategoriTavsiye haritasinda olmadigi icin sonuc bos liste cikiyor
        # (ayni bosluk TEST 25 kapisinda BILINCLI olarak kayitli); harita doldurulunca bu
        # test rozeti gormek isteyecek.
        beklenen = [t["ad"] for t in filament_ortak.tavsiyeler(
            p.get("kategori"), p.get("tavsiyeFilament"))]
        rozetli = [m.group(1) for m in re.finditer(
            r'fil-cip tavsiyeli[^>]*>.*?<span class="fil-ad">([^<]+)</span>', s)]
        if sorted(rozetli) != sorted(beklenen):
            hatalar.append("%s (%s): rozet %s != beklenen %s"
                           % (p["id"], p.get("kategori"), rozetli, beklenen))
    kayit(2, "20 rastgele sayfa (+en az 1 parametrik): %d cip (ABS/Karbon HARIC) + rozet + "
          "balon birebir + dogru tavsiye" % len(site_fil), not hatalar, "; ".join(hatalar[:4]))

    # ---- 3) yasak ifadeler: uretilen HICBIR sayfada "3d bask" / "her renk" yok
    yasak = []
    for pat in ["3d bask", "her renk"]:
        g = subprocess.run(["grep", "-rli", pat, "urun", "malzeme-rehberi",
                            "teslimat-iade", "mesafeli-satis", "filament-veri.js",
                            "sitemap.xml", "index.html", "sss", "hakkimizda",
                            "iletisim", "gizlilik"],
                           capture_output=True, text=True, cwd=ROOT)
        if g.stdout.strip():
            yasak.append("%r: %s" % (pat, g.stdout.strip().splitlines()[:3]))
    kayit(3, "'3D bask' ve 'her renk' hicbir uretilen sayfada yok", not yasak,
          "; ".join(yasak))

    # ---- 4) /malzeme-rehberi/ uretildi + footer linki + sitemap
    reh_yol = os.path.join(ROOT, "malzeme-rehberi", "index.html")
    reh_var = os.path.exists(reh_yol)
    reh = open(reh_yol, encoding="utf-8").read() if reh_var else ""
    sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
    kosullar = {
        "sayfa uretildi": reh_var,
        "%d malzemenin hepsi rehberde" % len(ref["filamentler"]):
            reh_var and all((f.get("uzunAd") or f["ad"]) in reh for f in ref["filamentler"]),
        "karsilastirma tablosu": "karsilastirma" in reh and "HDT @ 0.45 MPa" in reh,
        "urun sayfasi footer linki": '/malzeme-rehberi/' in ornek_sayfa,
        "sitemap kaydi": "https://pruvo3d.com/malzeme-rehberi/" in sm,
    }
    kayit(4, "/malzeme-rehberi/ + footer + sitemap", all(kosullar.values()),
          ", ".join(k for k, v in kosullar.items() if not v) or "hepsi tamam")

    # ---- 5) parite testleri (ag gerekir; PARITE=0 ile atlanabilir)
    if os.environ.get("PARITE", "1") == "0":
        kayit(5, "parite testleri", True, "ATLANDI (PARITE=0)")
    else:
        p1 = subprocess.run(["node", os.path.join(TOOLS, "parite-test.js"), "300"],
                            capture_output=True, text=True, cwd=ROOT)
        p2 = subprocess.run(["node", os.path.join(TOOLS, "parite-ege.js"), "200"],
                            capture_output=True, text=True, cwd=ROOT)
        ok1, et1, sb1 = parite_exit_yorumla(p1.returncode, p1.stdout + p1.stderr)
        ok2, et2, sb2 = parite_exit_yorumla(p2.returncode, p2.stdout + p2.stderr)
        ok = ok1 and ok2
        det = "site:%s ege:%s" % (et1, et2)
        # ⚪ ATLANDI'nin SEBEBI DAIMA GORUNUR olsun: yoksa "yesil sanip gecmek" riski dogar.
        if sb1:
            det += " | site: " + sb1
        if sb2:
            det += " | ege: " + sb2
        if not ok:
            det += " | " + (p1.stdout + p1.stderr + p2.stdout + p2.stderr).strip()[-300:]
        kayit(5, "parite (site + ege) — aciklama degismedi kaniti", ok, det)
        # A15 NOBETI: ATLANDI sessizce "yesil" gorunmesin — STDERR'e de dusur.
        if PARITE_ATLANDI in (et1, et2):
            print("⚪ PARITE ATLANDI (parite BELGELENMEDI, cikis 3): %s" % det,
                  file=sys.stderr, flush=True)

    # ---- 6) override: sahte urunle render -> harita degil override basiliyor
    sahte = {"id": "test-override-sahte", "kategori": "Ev", "marka": [],
             "baslik": "Override Test", "aciklama": "test", "fiyat": "100 TL",
             "gorseller": [], "tavsiyeFilament": ["ASA"]}
    h = build.render_product(sahte, [sahte])
    rozetli = [m.group(1) for m in re.finditer(
        r'fil-cip tavsiyeli[^>]*>.*?<span class="fil-ad">([^<]+)</span>', h)]
    kayit(6, "tavsiyeFilament override haritayi eziyor (Ev+override[ASA] -> rozet ASA)",
          rozetli == ["ASA"], "rozetli=%s" % rozetli)

    # ---- 7) mobil tooltip: DOM/CSS duzeyinde dogrulama
    s = ornek_sayfa
    blok = s.split('class="malzeme-blok"', 1)[1].split("</a></div>", 1)[0] \
        if 'class="malzeme-blok"' in s else ""
    kosullar7 = {
        "balon her cipte": s.count('class="fil-balon"') == len(site_fil),
        "CSS: .acik ile balon acilir": ".fil-cip.acik .fil-balon{display:block}" in s,
        "CSS: hover ile balon acilir": ".fil-cip:hover .fil-balon" in s,
        "JS: dokunma toggle": 'classList.toggle("acik")' in s,
        "JS: disari dokununca kapanir": 'document.addEventListener("click"' in s,
        "aria-expanded var": 'aria-expanded="false"' in blok,
        "title= kullanilmamis (mobilde calismaz)": blok != "" and "title=" not in blok,
    }
    kayit(7, "mobil tooltip DOM/CSS dogrulamasi", all(kosullar7.values()),
          ", ".join(k for k, v in kosullar7.items() if not v) or "hepsi tamam")

    # ---- 8) ABS/Karbon Katkili urun sayfasinda SITE SECENEGI OLARAK sunulmuyor
    hatalar8 = []
    for f in ozel_fil:
        if ('value="%s"' % f["ad"]) in ornek_sayfa:
            hatalar8.append("%s: <option> olarak dropdown'da var" % f["ad"])
    if "wa.me/905451386526" not in ornek_sayfa:
        hatalar8.append("WhatsApp muhendislik-malzeme linki yok")
    kayit(8, "ABS/Karbon Katkili SITE SECENEGI olarak sunulmuyor (cip/dropdown yok, WA notu var)",
          not hatalar8, "; ".join(hatalar8) or "temiz")

    # ================= KART-SECIM (malzeme dropdown -> kart secici) =================
    # fonk_urun / fs yukarida (FIKSTUR SECIMI blogu) secildi — EHLIYET suzgecinden gecti.

    # ---- 9 (a) dropdown YOK + kartlar data-malzeme + tiklama SECER
    h9 = []
    if 'id="malzemeSec"' in fs:
        h9.append("malzeme dropdown hala var")
    for f in site_fil:
        if ('data-malzeme="%s"' % html.escape(f["ad"], quote=True)) not in fs:
            h9.append("%s karti data-malzeme tasimıyor" % f["ad"])
    # KART-SECIM BAYRAGI (2 Agu 2026): paylasilan JS govdesi /varlik/urun-<hash>.js'e
    # tasindi; sayfaya-ozel deger artik SAYFADAKI veri blogundan gelir
    # (`var URUN_KART_SECIM = true;`) ve ortak govde onu okur
    # (`var KART_SECIM = URUN_KART_SECIM;`). IKI CAPA da aranir: yalniz birine bakmak,
    # bagin bir ucu koparsa (deger basiliyor ama okunmuyor / okunuyor ama basilmiyor)
    # testi YESIL birakirdi.
    for parca in ["var URUN_KART_SECIM = true;",
                  "var KART_SECIM = URUN_KART_SECIM;",
                  'seciliMalzeme = this.getAttribute("data-malzeme")',
                  'classList.toggle("secili"']:
        if parca not in fs:
            h9.append("secim JS eksik: %s" % parca)
    kayit(9, "(a) malzeme dropdown YOK + kartlar data-malzeme + tiklama secim JS'i",
          not h9, "; ".join(h9[:4]) or "temiz")

    # ---- 10 (b) acilista secili kart YOK + fiyat "baslayan"
    h10 = []
    if 'class="fil-cip secili' in fs or 'class="fil-cip tavsiyeli secili' in fs:
        h10.append("acilista bir kart 'secili' isaretli (onden secim olmamali)")
    m10 = re.search(r'id="opsiyonFiyat">([^<]*)<', fs)
    if not (m10 and "başlayan" in m10.group(1)):
        h10.append("opsiyonFiyat 'baslayan' halinde degil: %r" % (m10.group(1) if m10 else None))
    kayit(10, "(b) acilista secili kart yok + fiyat '…den baslayan'", not h10,
          "; ".join(h10) or "temiz")

    # ---- 11 (c) secimsiz Sepete Ekle -> eklenmez + titreme/kirmizi
    h11 = []
    for parca in ["var eksikM = !seciliMalzeme;",
                  "if(eksikM){ titret(cipler); }",
                  'el.classList.add("titre", kutu ? "hata" : "hata-vurgu")',
                  "@keyframes pruvoTitre",
                  ".titre{animation:pruvoTitre",
                  ".hata-vurgu .fil-cip,.hata-vurgu .renk-btn{border-color:var(--red)"]:
        if parca not in fs:
            h11.append("eksik: %s" % parca)
    kayit(11, "(c) secimsiz Sepete Ekle -> eklenmez + titreme/kirmizi (CSS+JS)",
          not h11, "; ".join(h11[:3]) or "temiz")

    # ---- 12 (d) secimle fiyat KATSAYILI guncellenir (JS wiring + kuruş matematigi)
    h12 = []
    if 'fiyatEl.textContent = ozet.fiyatMetni + "' not in fs and \
       "fiyatEl.textContent = ozet.fiyatMetni +" not in fs:
        h12.append("secimsiz 'baslayan' fiyat JS dali yok")
    if "fiyatEl.textContent = ozet.fiyatMetni;" not in fs:
        h12.append("secili kesin fiyat JS dali yok")
    # secenekler.js kuruş matematigi: PETG (+%30) PLA tabanindan farkli olmali
    r12 = subprocess.run(
        ["node", "-e",
         "require('./secenekler.js');var P=globalThis.PRUVO_SECENEK;"
         "var b=P.hesaplaFiyatKurus(350,'PLA','Siyah',0);"
         "var g=P.hesaplaFiyatKurus(350,'PETG','Siyah',0);"
         "if(b===35000 && g===45500 && g===Math.round(b*1.30)){console.log('OK')}"
         "else{console.error('base',b,'petg',g);process.exit(1)}"],
        capture_output=True, text=True, cwd=ROOT)
    if r12.returncode != 0:
        h12.append("kuruş matematigi: " + (r12.stdout + r12.stderr).strip())
    kayit(12, "(d) secimle fiyat KATSAYILI guncellenir (JS wiring + PETG +%30 kuruş)",
          not h12, "; ".join(h12[:3]) or "temiz")

    # ---- 13 (e) alt paragraf HICBIR urun sayfasinda yok
    g13 = subprocess.run(["grep", "-rl", "Sepete ekleyip birden çok", "urun"],
                         capture_output=True, text=True, cwd=ROOT)
    kayit(13, "(e) alt paragraf ('Sepete ekleyip…') hicbir urun sayfasinda yok",
          g13.stdout.strip() == "", g13.stdout.strip().splitlines()[:3])

    # ---- 14 (f) WhatsApp'tan Sor secim SARTI ARAMAZ
    #   (madde 7 sonrasi: kart-secim sayfasinda link IKON olarak Adet satirinda; hala <a href>)
    h14 = []
    if 'id="orderAlt"' not in fs or '<a class="ikon-btn ikon-wa" id="orderAlt"' not in fs:
        h14.append("orderAlt (WhatsApp'tan Sor) ikon linki yok")
    # titret/gate yalniz cartBtn tiklamasinda; orderAlt bir <a href> ve kilitlenmiyor
    if "orderAlt.disabled" in fs or "orderAlt.classList.add(\"kilitli\")" in fs:
        h14.append("orderAlt secime kilitlenmis")
    kayit(14, "(f) WhatsApp'tan Sor secim sarti aramaz (link her zaman calisir)",
          not h14, "; ".join(h14) or "temiz")

    # ================= RENK BUTONLARI (dropdown -> buton, Okan ek madde) =================
    # Renk listesi TEK KAYNAK secenekler.js (build.py da oradan okur).
    sec_js = open(os.path.join(ROOT, "secenekler.js"), encoding="utf-8").read()
    RENK_SECENEKLERI = json.loads(re.search(r'var RENK_SECENEKLERI = (\[.*?\]);', sec_js).group(1))

    # ---- 15 (g) renk dropdown YOK + 4 buton var + Diger'de gradyan
    h15 = []
    if 'id="renkSec"' in fs:
        h15.append("renk dropdown hala var")
    if fs.count('class="renk-btn"') != len(RENK_SECENEKLERI):
        h15.append("renk-btn sayisi %d != %d" % (fs.count('class="renk-btn"'), len(RENK_SECENEKLERI)))
    for r in RENK_SECENEKLERI:
        if ('data-renk="%s"' % html.escape(r, quote=True)) not in fs:
            h15.append("data-renk=%s butonu yok" % r)
    if "renk-yuvar-gokkusagi" not in fs or "conic-gradient" not in fs:
        h15.append("Diger gokkusagi gradyan yuvarlagi yok")
    kayit(15, "(g) renk dropdown yok + %d buton + Diger gradyan" % len(RENK_SECENEKLERI),
          not h15, "; ".join(h15[:4]) or "temiz")

    # ---- 16 (h) acilista renk seçimsiz
    h16 = []
    if 'class="renk-btn secili' in fs:
        h16.append("acilista bir renk butonu 'secili' (onden secim olmamali)")
    if "var seciliRenk = \"\";" not in fs:
        h16.append("seciliRenk bos baslamiyor")
    # renkOzel kutusu acilista gizli
    m16 = re.search(r'id="renkOzel"[^>]*style="display:none"', fs)
    if not m16:
        h16.append("renkOzel kutusu acilista gizli degil")
    kayit(16, "(h) acilista renk secimsiz + renkOzel gizli", not h16, "; ".join(h16) or "temiz")

    # ---- 17 (i) Diger seçince metin kutusu görünür + boşken sepete eklenmez
    h17 = []
    for parca in ['renkOzel.style.display = (seciliRenk === "Diğer") ? "block" : "none"',
                  'var eksikO = seciliRenk === "Diğer" && renkOzel && !renkOzel.value.trim();',
                  "if(eksikO){ titret(renkOzel); }",
                  ".renk-ozel.hata{border-color:var(--red)"]:
        if parca not in fs:
            h17.append("eksik: %s" % parca)
    kayit(17, "(i) Diger -> metin kutusu gorunur; bosken sepete eklenmez (titrer)",
          not h17, "; ".join(h17[:3]) or "temiz")

    # ---- 18 (j) Diger + metin dolu -> not alaniyla sepete + fiyat +%15
    #   Veri modeli: r="Diğer" kalir, musteri metni renk_ozel'de tasinir; secenekler.js
    #   satirOzeti bunu WhatsApp mesajina koyar ve +%15 uygular. Runtime (node) ile dogrula.
    r18 = subprocess.run(
        ["node", "-e",
         "require('./secenekler.js');var P=globalThis.PRUVO_SECENEK;"
         "var u={id:'x',kategori:'Marin',fiyat:'350 TL'};"
         "var s={id:'x',malzeme:'PLA',renk:'Diğer',renk_ozel:'turuncu',boy_etiket:null,adet:1};"
         "var o=P.satirOzeti(u,s);"
         # +%15: 350*100*100*115/10000 = 40250 kuruş
         "var beklenen=Math.round(350*100*100*115/10000);"
         "if(o.birimKurus===beklenen && o.detay.indexOf('turuncu')>=0){console.log('OK')}"
         "else{console.error('birim',o.birimKurus,'bek',beklenen,'detay',o.detay);process.exit(1)}"],
        capture_output=True, text=True, cwd=ROOT)
    h18 = [] if r18.returncode == 0 else [(r18.stdout + r18.stderr).strip()]
    # JS wiring: renk_ozel'i satira 30 karakterle yaziyor (istemci de sinirliyor)
    if "renkOzel.value.trim().slice(0, 30)" not in fs:
        h18.append("renkOzel istemci tarafi 30 karakter sinir yok")
    kayit(18, "(j) Diger + metin dolu -> renk_ozel not alaniyla sepete + fiyat +%15",
          not h18, "; ".join(h18[:3]) or "temiz")

    # ---- 19 (k) Siyah seçiminde fiyata renk farki BINMEZ (PLA/Siyah = taban)
    r19 = subprocess.run(
        ["node", "-e",
         "require('./secenekler.js');var P=globalThis.PRUVO_SECENEK;"
         "var u={id:'x',kategori:'Marin',fiyat:'350 TL'};"
         "var siyah=P.satirOzeti(u,{id:'x',malzeme:'PLA',renk:'Siyah',renk_ozel:'',boy_etiket:null,adet:1});"
         "var diger=P.satirOzeti(u,{id:'x',malzeme:'PLA',renk:'Diğer',renk_ozel:'mor',boy_etiket:null,adet:1});"
         "if(siyah.birimKurus===35000 && diger.birimKurus===40250){console.log('OK')}"
         "else{console.error('siyah',siyah.birimKurus,'diger',diger.birimKurus);process.exit(1)}"],
        capture_output=True, text=True, cwd=ROOT)
    h19 = [] if r19.returncode == 0 else [(r19.stdout + r19.stderr).strip()]
    kayit(19, "(k) Siyah/Beyaz/Gri renk farki binmez; Diger +%15 (kuruş)",
          not h19, "; ".join(h19[:2]) or "temiz")

    # ---- 20 liste kartlari sade: "Sepete Ekle" butonu + "Tavsiye:" cipi YOK; urun sayfasi regresyonsuz
    ih = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    h20 = []
    # Hizli-ekleme yolunun TUM parcalari kalkti (buton, toggle, sync, cip, veri script'i).
    for yasak in ["setCartBtn", "syncCardButtons", "toggleCart(",
                  '"Tavsiye: "', "card-fil", 'src="/filament-veri.js"']:
        if yasak in ih:
            h20.append("index.html'de hala var: %s" % yasak)
    # bosSatir SADECE goc icin secenekler.js'te kalir; index.html'de dogrudan cagri kalmadi.
    if "bosSatir(" in ih:
        h20.append("index.html hala bosSatir cagiriyor (varsayilan-PLA ekleme yolu)")
    # build.py ilgili-urunler kartlari da temiz (rel-card yalniz gorsel+baslik+fiyat).
    m20 = re.search(r'<section class="related">.*?</section>', fs, re.S)
    rel_html = m20.group(0) if m20 else ""
    if "Sepete Ekle" in rel_html:
        h20.append("ilgili-urunler kartinda Sepete Ekle var")
    if "Tavsiye:" in rel_html:
        h20.append("ilgili-urunler kartinda Tavsiye cipi var")
    # REGRESYON: urun sayfasinda sepete ekleme + malzeme kartlari DURUYOR.
    for gerekli in ['id="cartBtn"', 'id="filCipler"', "data-malzeme="]:
        if gerekli not in fs:
            h20.append("urun sayfasinda kayip: %s" % gerekli)
    kayit(20, "liste kartlarinda Sepete Ekle + Tavsiye yok; urun sayfasi regresyonsuz",
          not h20, "; ".join(h20[:4]) or "temiz")

    # ================= EYLEM IKONLARI (madde 7: buyuk butonlar -> Adet satirina ikon) ==========
    # ---- 21 (l) buyuk butonlar yok + Adet satirinda 2 aria-label'li ikon; PARAMETRIK DE AYNI
    h21 = []
    if 'class="cart-btn"' in fs or 'class="order-wa"' in fs:
        h21.append("kart-secim sayfasinda buyuk buton hala var")
    if not re.search(r'opsiyon-adet-eylem.*?id="adetArti".*?eylem-ikonlar.*?'
                     r'ikon-sepet" id="cartBtn"[^>]*aria-label="Sepete Ekle" title="Sepete Ekle".*?'
                     r'ikon-wa" id="orderAlt"[^>]*aria-label="WhatsApp\'tan Sor"[^>]*title="WhatsApp\'tan Sor"', fs, re.S):
        h21.append("Adet satirinda aria-label+title'li ikon cifti eksik/sirasiz")
    if ".ikon-btn{width:44px;height:44px" not in fs:
        h21.append("44x44 dokunma alani CSS'i yok")
    # SEMALI PARAMETRIK (sari) SAYFA DA KART-SECIM MODUNDA — F kalemi (Okan, 16 Tem gece;
    # commit 68cf6939 "Faz D ek kalemler E+F"): parametrik sayfa duzeni normal sayfayla
    # ESITLENDI. build.py:1197 `kart_secim = bool(sema) or (fonksiyonel and not parametrik)`
    # -> semali parametrikte butonlar Adet satirinda, sayfa altina buyuk buton BASILMAZ.
    # (16 Tem 15:44'te yazilan "parametrik duzene dokunulmadi" iddiasi Okan'in SONRAKI
    #  karariyla gecersiz kaldi; test o gun bayatladi.) Buyuk buton yolunun NOBETCISI -> TEST 24.
    # par_u / ps21 yukarida (FIKSTUR SECIMI blogu) secildi — EHLIYET suzgecinden gecti.
    if "ikon-btn ikon-sepet" not in ps21:
        h21.append("parametrik sayfada ikon sepet yok (kart-secim duzeni bekleniyor)")
    if "ikon-btn ikon-wa" not in ps21:
        h21.append("parametrik sayfada ikon WhatsApp yok (kart-secim duzeni bekleniyor)")
    if 'class="cart-btn" id="cartBtn"' in ps21 or 'class="order-wa" id="orderAlt"' in ps21:
        h21.append("parametrik sayfada eski BUYUK butonlar geri gelmis (F kalemi geri alinmis)")
    kayit(21, "(l) buyuk butonlar kalkti, Adet satirinda 2 ikon (aria+title+44px); "
          "semali parametrik sayfa da AYNI kart-secim duzeninde",
          not h21, "; ".join(h21[:4]) or "temiz")

    # ---- 22 (m) ikon sepet = ayni cartBtn -> secimsiz kapi + titreme AYNEN (id + kapi JS'i)
    h22 = []
    if fs.count('id="cartBtn"') != 1:
        h22.append("cartBtn id'si tek degil (%d)" % fs.count('id="cartBtn"'))
    for parca in ["var eksikM = !seciliMalzeme;",          # kapi ayni kodla duruyor
                  "if(eksikM){ titret(cipler); }",
                  '"Sepette ✓ — çıkarmak için tıklayın"']:  # ikonda durum title/aria ile
        if parca not in fs:
            h22.append("eksik: %s" % parca)
    kayit(22, "(m) ikon sepet butonu = ayni kapi (secimsiz eklemez + titrer) + durum aria/title",
          not h22, "; ".join(h22[:3]) or "temiz")

    # ---- 23 (n) WhatsApp ikonu dogru hedef: statik href + JS canli guncelleme
    h23 = []
    m23 = re.search(r'id="orderAlt" href="([^"]+)"', fs)
    if not (m23 and m23.group(1).startswith("https://wa.me/905451386526?text=")):
        h23.append("statik href wa.me/905451386526 degil: %r" % (m23.group(1)[:60] if m23 else None))
    if 'orderAlt.href = "https://wa.me/905451386526?text=" + encodeURIComponent(mesaj);' not in fs:
        h23.append("JS canli mesaj guncellemesi yok")
    kayit(23, "(n) WhatsApp ikonu dogru wa.me hedefi (statik + JS)", not h23,
          "; ".join(h23[:2]) or "temiz")

    # ---- 24 NOBETCI: BUYUK buton yolu (build.py BUYUK_BUTONLAR_HTML) hala CANLI.
    # TEST 21'den parametrik iddiasi kalkinca bu kod dalini olcen baska iddia kalmiyordu ->
    # dal silinse/bosalsa kimse yakalamazdi. Okan 23 Tem: Dekorasyon + Oyun/Hobi FONKSIYONEL
    # oldu -> gercek katalogda panelsiz urun KALMADI; nobetci artik SENTETIK panelsiz urunle
    # olcer: FONKSIYONEL disi + parametrik olmayan kategori (semasiz Jeneratör) opsiyon paneli
    # basmaz, eylem butonlari sayfa altinda BUYUK halde kalir.
    h24 = []
    pnl_sahte = {"id": "test-panelsiz-nobetci", "kategori": "Jeneratör", "marka": [],
                 "baslik": "Panelsiz Nobetci", "aciklama": "test", "fiyat": "100 TL",
                 "gorseller": []}
    if pnl_sahte["kategori"] in FONK or pnl_sahte.get("parametrik"):
        h24.append("sentetik urun panelsiz dala girmiyor (kategori FONKSIYONEL/parametrik)")
    pnls = build.render_product(pnl_sahte, [pnl_sahte])
    if 'class="cart-btn" id="cartBtn"' not in pnls:
        h24.append("buyuk 'Sepete Ekle' butonu yok (BUYUK_BUTONLAR_HTML dali bosalmis)")
    if 'class="order-wa" id="orderAlt"' not in pnls:
        h24.append("buyuk 'WhatsApp'tan Sor' butonu yok")
    if "ikon-btn ikon-sepet" in pnls:
        h24.append("panelsiz sayfaya ikon cifti tasinmis")
    kayit(24, "NOBETCI: panelsiz (sentetik semasiz-Jeneratör) sayfada BUYUK butonlar yerinde, ikon yok",
          not h24, "; ".join(h24[:3]) or "temiz")

    # ---- 25 KAPI: kategori <-> tavsiye haritasi boslugu FAIL-CLOSED
    # urunler.json'da FIILEN kullanilan her kategori icin ya filament_ortak.tavsiyeler()
    # bir tavsiye uretecek, ya da kategori asagidaki BILINCLI-BOS listesinde olacak.
    # Yarin yeni bir kategori acilip tavsiyesiz kalirsa bu test KIRMIZI yanar (sessiz gecmez).
    BILINCLI_BOS = {
        # Jeneratör = sari/parametrik seri. F kalemi eski "konusarak belirleriz" notunu
        # kaldirdi, yerine kategori-geneli tavsiye HENUZ KARARLASTIRILMADI (OKAN KAPISI).
        # Karar verilince filamentler.json kategoriTavsiye'ye eklenip buradan cikarilacak.
        "Jeneratör",
    }
    h25 = []
    kullanilan_kat = sorted({(u.get("kategori") or "").strip() for u in urunler} - {""})
    for k in kullanilan_kat:
        if filament_ortak.tavsiyeler(k):
            continue
        if k in BILINCLI_BOS:
            continue
        h25.append("%s: tavsiye uretmiyor + BILINCLI_BOS listesinde de degil" % k)
    # ters yon — liste bayatlamasin: haritaya eklendiyse BILINCLI_BOS'tan cikarilmali
    for k in sorted(BILINCLI_BOS):
        if filament_ortak.tavsiyeler(k):
            h25.append("%s: artik tavsiye uretiyor -> BILINCLI_BOS listesinden cikarilmali" % k)
    kayit(25, "KAPI: kullanilan %d kategorinin hepsi ya tavsiye uretir ya BILINCLI_BOS'ta "
          "(bugun bilincli bos: %s)" % (len(kullanilan_kat), ", ".join(sorted(BILINCLI_BOS))),
          not h25, "; ".join(h25[:4]) or "temiz")

    # ---- 26 FIKSTUR NOBETI: kayma "YANLIS VAKA" diye YANAR, sessiz anlamsiz sonuc URETMEZ
    # 🔴 NEDEN VAR (olculdu, 1 Agu): fikstur `urunler[0]` / "ilk fonksiyonel urun" ile
    # seciliyordu. Katalogun basina hazir ticari mal (`"tur":"fiziksel"`) girince fikstur
    # oraya dustu; build.py o sayfaya filament/renk/kart arayuzunu BILEREK basmaz, dolayisiyla
    # 6 test "kod kirik" gibi kirmizi yandi. Kirmizi GERCEKTI ama SEBEBI YANLISTI ve cikti bunu
    # SOYLEMIYORDU. Bu iddia o ayrimi yapar: fikstur EHIL degilse mesaj "YANLIS VAKA" der.
    h26 = []
    # (a) FIILEN kullanilan fiksturler EHIL mi (secim helper'i baypas edilirse burasi yanar)
    for ad, u in [("ornek urun sayfasi", ornek_urun),
                  ("fonksiyonel kart-secim", fonk_urun),
                  ("parametrik (sari)", par_u)]:
        if not baski_urunu_mu(u):
            h26.append("YANLIS VAKA — %s fiksturu '%s' EHIL DEGIL (tur=%r); bu paketin "
                       "iddialari YALNIZ ozel uretim sayfasi icin anlamlidir"
                       % (ad, u.get("id"), u.get("tur")))
    # (b) TEST 2 ornekleme havuzu: ehil olmayan urun SIZMAMALI + ornek alacak kadar buyuk
    havuz_disi = [u for u in havuz if not baski_urunu_mu(u)]
    if havuz_disi:
        h26.append("TEST 2 havuzunda %d EHIL OLMAYAN kayit (ilk: %s)"
                   % (len(havuz_disi), havuz_disi[0].get("id")))
    if len(havuz) < 20:
        h26.append("TEST 2 havuzu 20 ornek icin kucuk (%d)" % len(havuz))
    # (c) URETILEN SAYFA ekseni (veri ile uretim ayrismasi): fikstur sayfasi hazir ticari mal
    #     isaretini TASIMAMALI (build.py yalniz fiziksel uruntte `"tur":"fiziksel"` basar).
    for ad, s in [("ornek", ornek_sayfa), ("fonksiyonel", fs), ("parametrik", ps21)]:
        if '"tur":"fiziksel"' in s:
            h26.append("%s fikstur SAYFASI hazir ticari mal isareti tasiyor "
                       "(urunler.json ile uretim ayrismis olabilir)" % ad)
    # (d) SECICI FAIL-LOUD MU: yalniz ehil-olmayan kayit iceren sentetik katalogda SESSIZCE
    #     bir urun dondurmemeli, FiksturKaymasi ATMALI.
    try:
        kacan = fikstur_sec([{"id": "sentetik-fiziksel", "kategori": "Marin", "tur": "fiziksel"},
                             {"id": "sentetik-bilinmeyen", "kategori": "Marin", "tur": "dijital"}],
                            lambda u: True, "sentetik nobet")
        h26.append("secici EHIL OLMAYAN kaydi SESSIZCE dondurdu: %s" % kacan.get("id"))
    except FiksturKaymasi:
        pass
    # (e) TERS YON — nobetci fazla dar olmasin: ehil kayit VARSA secici onu BULMALI.
    try:
        secilen = fikstur_sec([{"id": "sentetik-fiziksel", "tur": "fiziksel"},
                               {"id": "sentetik-baski"}], lambda u: True, "sentetik ehil")
        if secilen.get("id") != "sentetik-baski":
            h26.append("secici ehil kaydi atladi: %s" % secilen.get("id"))
    except FiksturKaymasi:
        h26.append("secici ehil kayit VARKEN de patliyor (nobetci fazla dar)")
    kayit(26, "FIKSTUR NOBETI: fiksturler ozel uretim urunu (kayma 'YANLIS VAKA' diye yanar); "
          "havuz %d urun, %d fiziksel disarida" % (len(havuz), len(urunler) - len(havuz)),
          not h26, "; ".join(h26[:3]) or "temiz")

    print("-" * 70)
    kaldi = [x for x in SONUC if not x[2]]
    if kaldi:
        print("SONUC: %d/%d test KIRMIZI ❌" % (len(kaldi), len(SONUC)))
        sys.exit(1)
    print("SONUC: %d/%d test YESIL ✅" % (len(SONUC), len(SONUC)))


if __name__ == "__main__":
    # Agsiz + build'siz alt-kapi: parite cikis kodu eslemesi (0/1/2/3). build.py CALISMAZ,
    # checkout kirlenmez -> yasal sayfa geri yukleme de gerekmez.
    if "--parite-eslem-testi" in sys.argv[1:]:
        sys.exit(parite_eslem_testi())
    try:
        main()
    finally:
        # main() sys.exit ile de cikabilir (SystemExit) ya da istisna atabilir; finally her
        # iki durumda da kosar -> kosum SONRASI checkout DAIMA temiz (kabul testi #5).
        _yasal_sayfalari_geri_yukle()
