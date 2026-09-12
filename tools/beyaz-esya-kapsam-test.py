# -*- coding: utf-8 -*-
"""BEYAZ ESYA KAPSAM KAPISI — Okan emri 29 Tem 2026: "beyaz esya ile hicbir iliskimiz yok".

NE OLCER
--------
Yayina cikan PRUVO metin yuzeylerinde beyaz esya kancasi kalmis mi:
  * YUZEY ekseni  : tools/sayfalar.py :: CONTENT_PAGES -> (slug, baslik, meta, govde)
                    Bu eksende MUAFIYET YOKTUR. Bir sayfa buraya girerse yakalanir.
  * HAM ekseni    : tools/sayfalar.py + index.html dosya metni (yorumlar dahil).
                    Politika yorumu yazmak icin TEK kacis: satirda `KAPSAM-DISI-NOT`
                    isareti. Kacis NON-GROWTH'tur: muaf satir sayisi MUAF_TAVAN'i
                    asarsa kapi KIRMIZI yanar (kacis deliginin buyumesi olculur).
Iki eksen BAGIMSIZDIR: ham eksendeki kacis, yuzey eksenini gevsetmez.

DESEN NEREDEN GELIR
-------------------
TEK KAYNAK kardes ev: ~/dev/pruvo-pazarlama/seo/dalga-guard.py :: YASAKLI
(aciklama alani "beyaz-esya-kapsam" olan kayitlar). O ev CI'da checkout EDILMEZ,
bu yuzden burada bir YEREL AYNA durur ve kardes ev ERISILEBILIRSE ayna ona karsi
dogrulanir (SAPMA=YOK / SAPMA=VAR -> KIRMIZI). Erisilmezse SAPMA=OLCULEMEDI diye
BASILIR — sessizce "yesil" sayilmaz ([[kopya-turetilemiyorsa-bayatlik-olculemez]]).

KOSUM
-----
  python3 tools/beyaz-esya-kapsam-test.py              # canli tarama (rc=0/1)
  python3 tools/beyaz-esya-kapsam-test.py --envanter   # A/B/C kovalari + sayilar
  python3 tools/beyaz-esya-kapsam-test.py --mutasyon   # IZOLE fikstur mutantlari
Beyan: nobet.yml :: serit-b (yayini BLOKLAMAZ; `deploy` bu job'a needs: ile bagli degil).
"""
import argparse
import importlib.util
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KARDES_GUARD = os.path.expanduser("~/dev/pruvo-pazarlama/seo/dalga-guard.py")

# --------------------------------------------------------------- yerel ayna (TEK KAYNAK: kardes guard)
# Bu liste ELLE BAKIMLI DEGILDIR: kardes ev erisilebildiginde asagidaki `desenleri_al`
# onu kaynaktan okuyup BIREBIR karsilastirir. Sapma = KIRMIZI.
AYNA_DESENLER = [
    r"\bbeyaz[\s\-]esya",
    r"\bbuzdolab",
    r"\bcamasir[\s\-]makin",
    r"\bbulasik[\s\-]makin",
    r"\belektrikli[\s\-]supurge",
]
AYNA_ETIKET = "beyaz-esya-kapsam"

# normalize() aynasi — kardes guard ile ayni 1:1 harf esleme (uzunluk KORUNUR).
_TR_HARF = {"ı": "i", "İ": "I", "ş": "s", "Ş": "S", "ğ": "g", "Ğ": "G",
            "ü": "u", "Ü": "U", "ö": "o", "Ö": "O", "ç": "c", "Ç": "C"}

MUAF_ISARET = "KAPSAM-DISI-NOT"
# Ham eksendeki politika-yorumu kacisi NON-GROWTH: bugun olculen sayi + 0 pay.
# Yeni bir muaf satir eklemek kapiyi KIRMIZI yakar; sayiyi yukseltmek MIMAR karari
# olur ve gerekcesi bu satira yazilir.
MUAF_TAVAN = 6

HAM_DOSYALAR = ["tools/sayfalar.py", "index.html"]

# C kovasi — guard deseninin YAKALAMADIGI, kapsam ICI kalan sinirda slug'lar.
# Burada liste tutmak bir MUAFIYET DEGILDIR (kapi zaten yakalamiyor); envanter
# ciktisinda "olculdu ve dokunulmadi" diye gorunmesi icin adlari yazilidir.
SINIRDA_SLUGLAR = (
    "robot-supurge-plastik-parca-yaptirma",
    "firin-ocak-dugmesi-ve-kulpu-yaptirma",
    "davlumbaz-ve-aspirator-plastik-parca-yaptirma",
    "mikrodalga-doner-tabla-gobegi-yaptirma",
    "utu-ve-buhar-kazani-plastik-parcasi-yaptirma",
)


def normalize(s):
    """Kardes guard'in normalize()'i ile ayni: TR harf sadelestirme + kucuk harf.

    Cikti uzunlugu girdiyle BIREBIR ayni kalir (alinti ofseti kaymasin).
    """
    s = "".join(_TR_HARF.get(ch, ch) for ch in s)
    return s.lower()


def desenleri_al():
    """(desenler, kaynak_etiketi, sapma_durumu) dondurur.

    kardes ev varsa oradan OKUR ve aynayi dogrular; yoksa aynayi kullanir ve
    sapmayi OLCULEMEDI diye isaretler.
    """
    if not os.path.exists(KARDES_GUARD):
        return [re.compile(p) for p in AYNA_DESENLER], "AYNA", "OLCULEMEDI"
    spec = importlib.util.spec_from_file_location("_dalga_guard_ro", KARDES_GUARD)
    g = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(g)
    except Exception as e:                                   # pragma: no cover
        print("UYARI: kardes guard okunamadi (%s) — ayna kullanilacak" % e)
        return [re.compile(p) for p in AYNA_DESENLER], "AYNA", "OLCULEMEDI"
    kaynak = [p for p, aciklama in g.YASAKLI if aciklama == AYNA_ETIKET]
    sapma = "YOK" if kaynak == AYNA_DESENLER else "VAR"
    # normalize davranis sapmasi da olculur: ayni girdi ayni ciktiyi vermeli.
    prob = "Beyaz EŞYA · Buzdolabı ÇAMAŞIR Bulaşık SÜPÜRGE ığşüöç"
    if hasattr(g, "normalize") and g.normalize(prob) != normalize(prob):
        sapma = "VAR"
    return [re.compile(p) for p in kaynak], "KARDES", sapma


def isabetler(metin, desenler):
    """[(desen, alinti)] — metindeki her kapsam-disi isabet."""
    n = normalize(metin)
    out = []
    for p in desenler:
        for m in p.finditer(n):
            alinti = metin[max(0, m.start() - 35):m.end() + 35].replace("\n", " ")
            out.append((p.pattern, alinti))
    return out


# --------------------------------------------------------------- yuzey ekseni
def _sayfalar_modulu():
    sys.path.insert(0, os.path.join(KOK, "tools"))
    import sayfalar
    return sayfalar


def sayfa_yuzeyleri():
    """CONTENT_PAGES'ten (slug, baslik, kimlik_metni, govde_metni) uretir."""
    sayfalar = _sayfalar_modulu()
    for slug, baslik, meta, fn in sayfalar.CONTENT_PAGES:
        govde = fn() if callable(fn) else str(fn)
        yield slug, baslik, slug + " " + baslik, (meta or "") + " " + govde


def yuzey_tara(desenler, yuzeyler=None):
    """(A, B) kovalari. A = slug/baslik isabetli, B = yalniz govde/meta isabetli."""
    A, B = [], []
    for slug, baslik, kimlik, govde in (yuzeyler if yuzeyler is not None else sayfa_yuzeyleri()):
        kimlik_h = isabetler(kimlik, desenler)
        govde_h = isabetler(govde, desenler)
        if kimlik_h:
            A.append((slug, baslik, kimlik_h, govde_h))
        elif govde_h:
            B.append((slug, baslik, [], govde_h))
    return A, B


# --------------------------------------------------------------- ham eksen
def ham_tara(desenler, dosyalar=None, icerikler=None):
    """(isabetler, muaf_satir_sayisi). icerikler verilirse dosya OKUNMAZ (fikstur)."""
    bulgu, muaf = [], 0
    kaynaklar = icerikler if icerikler is not None else {
        yol: open(os.path.join(KOK, yol), encoding="utf-8").read()
        for yol in (dosyalar if dosyalar is not None else HAM_DOSYALAR)
    }
    for yol, metin in kaynaklar.items():
        for no, satir in enumerate(metin.splitlines(), 1):
            if MUAF_ISARET in satir:
                muaf += 1
                continue
            for desen, alinti in isabetler(satir, desenler):
                bulgu.append((yol, no, desen, alinti))
    return bulgu, muaf


# --------------------------------------------------------------- yonlendirme ekseni (404 YASAK)
def yonlendirme_tara(desenler):
    """(hatalar, kayit_sayisi) — uretimden cikan her slug 404 DEGIL, hedefi kapsam ICI.

    Bu eksen yuzey/ham eksenlerinden BAGIMSIZDIR: bir sayfayi silmek kapiyi yesile
    cevirir ama URL'yi 404 yapar; o durum burada KIRMIZI yanar.
    """
    sys.path.insert(0, os.path.join(KOK, "tools"))
    try:
        import yonlendirmeler
    except ImportError:
        return ["tools/yonlendirmeler.py YOK — uretimden cikan slug'lar 404 riski altinda"], 0
    sayfalar = _sayfalar_modulu()
    hatalar, sayi = yonlendirmeler.dogrula(sayfalar.CONTENT_PAGES)
    basliklar = {s: b for s, b, _m, _f in sayfalar.CONTENT_PAGES}
    for eski, hedef, _g in yonlendirmeler.YONLENDIRMELER:
        # hedefin KENDISI kapsam disi olamaz (yonlendirme kapsami geri getirmez)
        if hedef in basliklar and isabetler(hedef + " " + basliklar[hedef], desenler):
            hatalar.append("hedef KAPSAM DISI: %s -> %s" % (eski, hedef))
        # stub sayfanin GORUNUR metninde kapsam disi ibare gecemez
        if hedef in basliklar:
            stub = yonlendirmeler.stub_html(eski, sayfalar.CONTENT_PAGES, "https://pruvo3d.com",
                                            ga_head="")
            govde = stub.split("<body>", 1)[-1]
            if isabetler(govde, desenler):
                hatalar.append("stub GORUNUR metninde kapsam disi ibare: %s" % eski)
            # yonlendirme sinyalinin UCU DE bulunmali: canonical + refresh + gorunur link.
            hedef_url = "https://pruvo3d.com/" + hedef + "/"
            for imza, ad in (('rel="canonical" href="%s"' % hedef_url, "canonical"),
                             ('http-equiv="refresh" content="0; url=%s"' % hedef_url, "refresh"),
                             ('<a href="%s"' % hedef_url, "gorunur link")):
                if imza not in stub:
                    hatalar.append("stub'ta %s YOK: %s" % (ad, eski))
    return hatalar, sayi


# --------------------------------------------------------------- mutantlar (IZOLE fikstur)
def _mutasyon():
    """Kapi gercekten oluyor mu: her mutant IZOLE fikstur uzerinde KIRMIZI yakmali.

    Mutantlar CANLI govdeye DOKUNMAZ ([[mutant-canli-govdede-yasamaz]]);
    tarama fonksiyonlari fikstur alacak sekilde yazildi.
    """
    desenler, _kaynak, _sapma = desenleri_al()
    temiz_yuzey = [("olcuye-ozel-mentese-uretimi", "Ölçüye Özel Menteşe Üretimi",
                    "olcuye-ozel-mentese-uretimi Ölçüye Özel Menteşe Üretimi",
                    "Dolap kapağının menteşesini ölçüye özel üretiyoruz.")]
    temiz_ham = {"fikstur.py": "# temiz satir\nMETIN = 'dolap kapagi menteşesi'\n"}

    vakalar = [
        ("M1 govde cumlesi geri kondu",
         lambda: yuzey_tara(desenler, [(temiz_yuzey[0][0], temiz_yuzey[0][1], temiz_yuzey[0][2],
                                        "Menteşe bir çamaşır makinesinin kapağını taşıyorsa.")])[1]),
        ("M2 govde ic-linki geri kondu",
         lambda: yuzey_tara(desenler, [(temiz_yuzey[0][0], temiz_yuzey[0][1], temiz_yuzey[0][2],
                                        'Ayrinti: <a href="/beyaz-esya-plastik-parca-uretimi/">bak</a>.')])[1]),
        ("M3 slug geri kondu",
         lambda: yuzey_tara(desenler, [("buzdolabi-raf-sebzelik-plastik-parca-yaptirma",
                                        "Raf Parçası", "buzdolabi-raf-sebzelik-plastik-parca-yaptirma Raf Parçası",
                                        "temiz govde")])[0]),
        ("M4 baslik geri kondu",
         lambda: yuzey_tara(desenler, [("raf-parcasi", "Buzdolabı Raf ve Sebzelik Parçası",
                                        "raf-parcasi Buzdolabı Raf ve Sebzelik Parçası",
                                        "temiz govde")])[0]),
        ("M5 ham dosyaya yorum olarak geri kondu",
         lambda: ham_tara(desenler, icerikler={"f.py": "# ev / mutfak / beyaz eşya / tesisat\n"})[0]),
        ("M6 elektrikli supurge kancasi geri kondu",
         lambda: yuzey_tara(desenler, [(temiz_yuzey[0][0], temiz_yuzey[0][1], temiz_yuzey[0][2],
                                        "Elektrikli süpürge hortumu için de üretiriz.")])[1]),
        ("M7 bulasik makinesi kancasi geri kondu",
         lambda: yuzey_tara(desenler, [(temiz_yuzey[0][0], temiz_yuzey[0][1], temiz_yuzey[0][2],
                                        "Parça bulaşık makinesine giriyor mu?")])[1]),
    ]
    # YONLENDIRME ekseni mutantlari — CANLI tabloya DOKUNMADAN, fikstur CONTENT_PAGES ile.
    sys.path.insert(0, os.path.join(KOK, "tools"))
    import yonlendirmeler as _y
    gercek = {slug for slug, _h, _g in _y.YONLENDIRMELER}
    hedefler = {h for _e, h, _g in _y.YONLENDIRMELER}
    tam = [(h, "Baslik", "meta", lambda: "govde") for h in hedefler]
    vakalar += [
        ("M8 yonlendirme hedefi uretimden kalkti (404 olurdu)",
         lambda: _y.dogrula([p for p in tam if p[0] != sorted(hedefler)[0]])[0]),
        ("M9 eski slug hem uretiliyor hem yonlendiriliyor",
         lambda: _y.dogrula(tam + [(sorted(gercek)[0], "B", "m", lambda: "g")])[0]),
    ]

    kontroller = [
        ("K4 tam hedef kumesi YESIL kalmali", lambda: _y.dogrula(tam)[0]),
        ("K1 temiz yuzey YESIL kalmali",
         lambda: (yuzey_tara(desenler, temiz_yuzey)[0] + yuzey_tara(desenler, temiz_yuzey)[1])),
        ("K2 temiz ham dosya YESIL kalmali", lambda: ham_tara(desenler, icerikler=temiz_ham)[0]),
        ("K3 muaf isaretli satir sayilmamali",
         lambda: ham_tara(desenler, icerikler={"f.py": "# KAPSAM-DISI-NOT: beyaz eşya kapsam disi\n"})[0]),
    ]

    hata = 0
    for ad, fn in vakalar:
        bulgu = fn()
        if bulgu:
            print("  ✅ MUTANT YAKALANDI — %s (isabet=%d)" % (ad, len(bulgu)))
        else:
            print("  ❌ MUTANT KACTI — %s" % ad)
            hata += 1
    for ad, fn in kontroller:
        bulgu = fn()
        if not bulgu:
            print("  ✅ KONTROL TEMIZ — %s" % ad)
        else:
            print("  ❌ YANLIS-POZITIF — %s (isabet=%d)" % (ad, len(bulgu)))
            hata += 1
    print("MUTASYON: %d mutant / %d kontrol · DUSEN=%d" % (len(vakalar), len(kontroller), hata))
    return 1 if hata else 0


# --------------------------------------------------------------- ana
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--envanter", action="store_true", help="A/B/C kovalarini ADIYLA bas")
    ap.add_argument("--mutasyon", action="store_true", help="izole fikstur mutantlarini kosur")
    ap.add_argument("--stub", metavar="ESKI_SLUG", help="bir yonlendirme stub'inin HTML'ini bas")
    a = ap.parse_args()

    desenler, kaynak, sapma = desenleri_al()
    print("DESEN_SAYISI=%d KAYNAK=%s SAPMA=%s" % (len(desenler), kaynak, sapma))
    if sapma == "VAR":
        print("❌ KIRMIZI: yerel ayna kardes guard'dan SAPTI — AYNA_DESENLER guncellenmeli.")
        return 1

    if a.mutasyon:
        return _mutasyon()

    if a.stub:
        sys.path.insert(0, os.path.join(KOK, "tools"))
        import yonlendirmeler
        print(yonlendirmeler.stub_html(a.stub, _sayfalar_modulu().CONTENT_PAGES,
                                       "https://pruvo3d.com", ga_head=""))
        return 0

    A, B = yuzey_tara(desenler)
    ham, muaf = ham_tara(desenler)
    yuzey_isabet = sum(len(k) + len(g) for _s, _b, k, g in A) + sum(len(g) for _s, _b, _k, g in B)

    if a.envanter:
        print("\n=== A — SLUG/BASLIK kapsam disi (%d) ===" % len(A))
        for slug, baslik, k, g in A:
            print("A | %s | %s | kimlik=%d govde=%d" % (slug, baslik, len(k), len(g)))
        print("\n=== B — yalniz GOVDE/META (%d) ===" % len(B))
        for slug, _baslik, _k, g in B:
            print("B | %s | isabet=%d" % (slug, len(g)))
            for desen, alinti in g[:3]:
                print("      [%s] ...%s..." % (desen, alinti))
        print("\n=== C — sinirda, guard YAKALAMIYOR (dokunulmaz) ===")
        for slug in SINIRDA_SLUGLAR:
            print("C | %s | guard_isabet=%d" % (slug, len(isabetler(slug, desenler))))

    yon_hatalar, yon_sayi = yonlendirme_tara(desenler)

    print("\nYUZEY: A=%d B=%d isabet=%d" % (len(A), len(B), yuzey_isabet))
    print("HAM:   isabet=%d muaf_satir=%d (tavan=%d)" % (len(ham), muaf, MUAF_TAVAN))
    print("YONLENDIRME: kayit=%d hata=%d" % (yon_sayi, len(yon_hatalar)))
    for h in yon_hatalar:
        print("  ! %s" % h)
    for yol, no, desen, alinti in ham[:20]:
        print("  %s:%d [%s] ...%s..." % (yol, no, desen, alinti))

    hata = 0
    if yuzey_isabet:
        print("❌ KIRMIZI: yayina cikan sayfa yuzeyinde %d beyaz esya isabeti (A=%d B=%d)."
              % (yuzey_isabet, len(A), len(B)))
        hata = 1
    if ham:
        print("❌ KIRMIZI: ham dosya metninde %d beyaz esya isabeti." % len(ham))
        hata = 1
    if muaf > MUAF_TAVAN:
        print("❌ KIRMIZI: muaf satir %d > tavan %d — kacis deligi BUYUYOR (NON-GROWTH ihlali)."
              % (muaf, MUAF_TAVAN))
        hata = 1
    if yon_hatalar:
        print("❌ KIRMIZI: yonlendirme tablosu %d hata — uretimden cikan URL 404 olur."
              % len(yon_hatalar))
        hata = 1
    if not hata:
        print("✅ YESIL: beyaz esya kapsami TEMIZ (yuzey 0 · ham 0 · muaf %d<=%d · "
              "yonlendirme %d kayit hatasiz)." % (muaf, MUAF_TAVAN, yon_sayi))
    return hata


if __name__ == "__main__":
    sys.exit(main())
