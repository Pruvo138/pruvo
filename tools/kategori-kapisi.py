#!/usr/bin/env python3
"""kategori-kapisi.py — urunler.json'daki KATEGORI degerlerinin gecerliligini dogrular.

NEDEN: index.html kategori cipini `p.kategori === activeCat` ile BIREBIR esler ve
`?kategori=<ad>` parametresini CATEGORIES beyaz listesine karsi suzer. Listede olmayan
bir kategori (or. ASCII "Bahce" vs "Bahçe") urunu katalogda BIRAKIR ama kategoriden
GORUNMEZ yapar; build.py tarafinda da FONKSIYONEL_KATEGORILER disinda kaldigi icin
malzeme/renk secicisi ve Google urun taksonomisi duser. Hata SESSIZDIR -> kapi sart.

TEK KAYNAK: gecerli kategori listesi BU DOSYADA TUTULMAZ. index.html (CATEGORIES +
GIZLI_KATEGORILER) ve tools/build.py (CATEGORIES + NAV_GIZLI) PROGRAMATIK okunur; ikisi
birbirinden farkliysa bu da HATA sayilir (iki yer birlikte guncellenmeli kurali).

Kullanim:
  python3 tools/kategori-kapisi.py                # urunler.json'u dogrula (ihlal varsa exit 1)
  python3 tools/kategori-kapisi.py --liste        # gecerli kategorileri bas (exit 0)
  python3 tools/kategori-kapisi.py --kendini-test # kapinin KENDI kabul bataryasi (CI: nobet.yml::serit-b)

DIKKAT: bu kapi build.py'ye BAGLANMAZ (tek kotu kategori tum yayini kirmasin); bagimsiz
calistirilabilir bir kabul testidir. build.py en fazla UYARI basar.
"""
import argparse
import ast
import json
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "index.html")
BUILD = os.path.join(ROOT, "tools", "build.py")
URUNLER = os.path.join(ROOT, "urunler.json")


def _js_dizi(metin, ad, kaynak):
    """index.html icindeki `var <ad> = ["a","b"];` dizisini okur (JSON olarak ayristirilir)."""
    m = re.search(r"var\s+" + re.escape(ad) + r"\s*=\s*(\[[^\]]*\])\s*;", metin)
    if not m:
        raise SystemExit("HATA: %s icinde `var %s = [...]` bulunamadi." % (kaynak, ad))
    try:
        dizi = json.loads(m.group(1))
    except ValueError as e:
        raise SystemExit("HATA: %s icindeki %s dizisi ayristirilamadi: %s" % (kaynak, ad, e))
    if not isinstance(dizi, list) or not all(isinstance(x, str) for x in dizi):
        raise SystemExit("HATA: %s icindeki %s bir metin dizisi degil." % (kaynak, ad))
    return dizi


def _py_dizi(agac, ad, kaynak):
    """build.py icindeki modul duzeyi `<ad> = [...]` atamasini okur (ast, exec YOK)."""
    for dugum in agac.body:
        if isinstance(dugum, ast.Assign):
            for hedef in dugum.targets:
                if isinstance(hedef, ast.Name) and hedef.id == ad:
                    try:
                        deger = ast.literal_eval(dugum.value)
                    except ValueError as e:
                        raise SystemExit("HATA: %s icindeki %s sabit degil: %s" % (kaynak, ad, e))
                    if not isinstance(deger, list) or not all(isinstance(x, str) for x in deger):
                        raise SystemExit("HATA: %s icindeki %s bir metin dizisi degil." % (kaynak, ad))
                    return deger
    raise SystemExit("HATA: %s icinde modul duzeyinde `%s = [...]` bulunamadi." % (kaynak, ad))


def kaynak_listeler():
    """(index_nav, index_gizli, build_nav, build_gizli) dondurur — dosyalardan OKUNUR."""
    with open(INDEX, encoding="utf-8") as f:
        html = f.read()
    with open(BUILD, encoding="utf-8") as f:
        agac = ast.parse(f.read(), filename=BUILD)
    return (_js_dizi(html, "CATEGORIES", "index.html"),
            _js_dizi(html, "GIZLI_KATEGORILER", "index.html"),
            _py_dizi(agac, "CATEGORIES", "tools/build.py"),
            _py_dizi(agac, "NAV_GIZLI", "tools/build.py"))


def gecerli_kategoriler():
    """Iki kaynagi karsilastirir; uyusuyorsa gecerli kategori listesini dondurur.

    Uyusmuyorsa SystemExit(1) ile duser — CLAUDE.md "index.html VE tools/build.py, ayni
    sirada guncelle" kurali makine olarak burada dogrulanir.
    """
    i_nav, i_gizli, b_nav, b_gizli = kaynak_listeler()
    hatalar = []
    if i_nav != b_nav:
        hatalar.append("CATEGORIES ayristi:\n  index.html   : %s\n  tools/build.py: %s"
                       % (i_nav, b_nav))
    if i_gizli != b_gizli:
        hatalar.append("GIZLI kategoriler ayristi:\n  index.html GIZLI_KATEGORILER: %s\n"
                       "  tools/build.py NAV_GIZLI    : %s" % (i_gizli, b_gizli))
    if hatalar:
        print("KATEGORI KAPISI: KAYNAK AYRISMASI")
        for h in hatalar:
            print("  - " + h)
        raise SystemExit(1)
    return i_nav + i_gizli


def ihlalleri_bul(urunler, gecerli):
    """Kayit listesindeki gecersiz-kategori ihlallerini dondurur: [(id, kategori), ...].

    TEK KAYNAK: hem main() hem --kendini-test BU fonksiyonu cagirir. Ikinci kopya
    tutulmaz -> batarya kapinin GERCEK govdesini olcer, benzerini degil.
    """
    ihlaller = []
    for u in urunler:
        if not isinstance(u, dict):
            ihlaller.append(("<obje-degil>", repr(u)[:60]))
            continue
        kat = u.get("kategori")
        if kat not in gecerli:
            ihlaller.append((u.get("id", "<id-yok>"), kat))
    return ihlaller


def _rc_hesapla(dusen):
    """Bataryanin IKI YONLU cikis kodu civisi: DUSEN bos ise 0, degilse 1.

    Vaka SAYISI ekseni cikis kodu eksenini OLCMEZ -> rc bu fonksiyondan okunur ve
    KONTROL-B iki yonu de ayri ayri dogrular (bos->0 VE dolu->1).
    """
    return 1 if dusen else 0


def _fikstur(dizin, ad, kayitlar):
    """Gecici bir urun JSON fiksturu yazar ve yolunu dondurur (yalniz temp dizininde)."""
    yol = os.path.join(dizin, ad)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(kayitlar, f, ensure_ascii=False)
    return yol


def kendini_test():
    """Kapinin calistirilabilir kabul bataryasi: 10 iddia + 2 kontrol.

    Her dusen iddia `DUSEN:` satiri basar; sonda DUSEN KUMESI vaka ADLARIYLA yazilir
    (mutant hangi vakalari oldurdugunu adiyla gostersin diye). rc _rc_hesapla()'dan gelir.
    """
    dusen = []
    kosan = []  # iddia SAYISI elle tutulmaz — bayatlamasin diye kosarken sayilir

    def iddia(ad, beklenen, gercek):
        kosan.append(ad)
        if beklenen == gercek:
            print("  ok   %s" % ad)
        else:
            print("  DUSEN: %s — beklenen=%r gercek=%r" % (ad, beklenen, gercek))
            dusen.append(ad)

    # --- KONTROL-A: gecerli kume IKI kaynaktan turetiliyor ve ayrismamis --------
    try:
        i_nav, i_gizli, b_nav, b_gizli = kaynak_listeler()
        kaynak_hatasi = None
    except SystemExit as e:
        i_nav = i_gizli = b_nav = b_gizli = None
        kaynak_hatasi = str(e)
    iddia("KONTROL-A/kaynak-paritesi-index-build", (True, True, None),
          (i_nav == b_nav, i_gizli == b_gizli, kaynak_hatasi))
    iddia("KONTROL-A/nav-12-gizli-2", (12, 2),
          (len(i_nav or []), len(i_gizli or [])))

    # --- KONTROL-B: rc civisi IKI YONLU ----------------------------------------
    iddia("KONTROL-B/rc-civisi-bos-kume-sifir", 0, _rc_hesapla([]))
    iddia("KONTROL-B/rc-civisi-dolu-kume-birden-buyuk", 1, _rc_hesapla(["ornek-vaka"]))

    gecerli = gecerli_kategoriler()

    # --- VAKA 01-09: ihlalleri_bul() ekseni -------------------------------------
    iddia("VAKA-01/gecerli-nav-kategori-YANMAZ",
          [], ihlalleri_bul([{"id": "t1", "kategori": "Ev"}], gecerli))
    iddia("VAKA-02/gecersiz-kategori-EvYasam-YANAR",
          [("t2-einhell-fikstur", "Ev & Yaşam")],
          ihlalleri_bul([{"id": "t2-einhell-fikstur", "kategori": "Ev & Yaşam"}], gecerli))
    iddia("VAKA-03/gizli-Jenerator-YANMAZ",
          [], ihlalleri_bul([{"id": "t3", "kategori": "Jeneratör"}], gecerli))
    iddia("VAKA-04/gizli-SkanArt-YANMAZ",
          [], ihlalleri_bul([{"id": "t4", "kategori": "Skan Art"}], gecerli))
    iddia("VAKA-05/bos-kategori-YANAR",
          [("t5", "")], ihlalleri_bul([{"id": "t5", "kategori": ""}], gecerli))
    iddia("VAKA-06/eksik-alan-YANAR",
          [("t6", None)], ihlalleri_bul([{"id": "t6"}], gecerli))
    iddia("VAKA-07/ascii-Bahce-YANAR",  # 'Bahce' != 'Bahçe' — kapinin NEDEN'indeki tuzak
          [("t7", "Bahce")], ihlalleri_bul([{"id": "t7", "kategori": "Bahce"}], gecerli))
    iddia("VAKA-08/obje-degil-YANAR",
          1, len(ihlalleri_bul(["duz-dizgi"], gecerli)))
    iddia("VAKA-09/karisik-kayitta-YALNIZ-bozuk-sayilir",
          [("t9-bozuk", "Ev & Yaşam")],
          ihlalleri_bul([{"id": "t9a", "kategori": "Marin"},
                         {"id": "t9-bozuk", "kategori": "Ev & Yaşam"},
                         {"id": "t9b", "kategori": "Skan Art"}], gecerli))

    # --- VAKA-10: UCTAN UCA main() yolu (argparse + dosya okuma + rc) -----------
    with tempfile.TemporaryDirectory() as gecici:
        temiz = _fikstur(gecici, "temiz.json", [{"id": "t10a", "kategori": "Ofis"}])
        kirli = _fikstur(gecici, "kirli.json", [{"id": "t10-einhell", "kategori": "Ev & Yaşam"}])
        iddia("VAKA-10/uctan-uca-main-temiz-rc0", 0, main(["--json", temiz]))
        iddia("VAKA-10/uctan-uca-main-kirli-rc1", 1, main(["--json", kirli]))

    # TABAN CIVISI: batarya cevresi degisince sessizce OLMESIN diye en az bu kadar
    # iddia KOSMUS olmali (4 kontrol + 10 vaka = 14). Vaka silinirse burasi yanar.
    TABAN_IDDIA = 15
    toplam = len(kosan)
    if toplam < TABAN_IDDIA:
        print("  DUSEN: TABAN/iddia-sayisi-dustu — beklenen>=%d gercek=%d" % (TABAN_IDDIA, toplam))
        dusen.append("TABAN/iddia-sayisi-dustu")
        toplam += 1
    # 🔴 FAIL-CLOSED CIVI: cikis kodu TEK BASINA _rc_hesapla()'ya emanet EDILEMEZ.
    # O fonksiyon bozulursa (mutant M4) batarya metinde "KIRMIZI" derken rc=0 verir
    # ve CI'da SESSIZCE yesil gorunur — vaka SAYISI ekseni cikis kodu eksenini OLCMEZ
    # ([[vaka-sayisi-ekseni-cikis-kodu-eksenini-olcmez]]). Basilan DUSEN kumesi ile rc
    # ayrisirsa ayrisma KENDISI bir DUSEN kalemidir ve kapi KIRMIZI'ya duser.
    ham_rc = _rc_hesapla(dusen)
    if bool(dusen) != bool(ham_rc):
        print("  DUSEN: TUTARLILIK/rc-civisi-bozuk — DUSEN=%d iken _rc_hesapla=%r"
              % (len(dusen), ham_rc))
        dusen.append("TUTARLILIK/rc-civisi-bozuk")
        toplam += 1

    gecen = toplam - len(dusen)
    if dusen:
        print("DUSEN KUMESI: %s" % ", ".join(dusen))
    else:
        print("DUSEN KUMESI: <bos>")
    print("TOPLAM: %d/%d" % (gecen, toplam))
    print("SONUC: %s" % ("KIRMIZI" if dusen else "YESIL"))
    # DUSEN doluysa rc MUTLAKA sifir-disi: _rc_hesapla bozulmus olsa bile bu dal tutar.
    # (Yazim BILEREK _rc_hesapla'nin govdesinden FARKLI: ozdes olsaydi mutant capasi
    # iki yere birden eslesir ve M4 "COKLU CAPA" ile olculemez hale gelirdi.)
    if dusen:
        return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--liste", action="store_true",
                    help="gecerli kategorileri bas ve cik (dogrulama yapma)")
    ap.add_argument("--kendini-test", dest="kendini_test", action="store_true",
                    help="kapinin kendi kabul bataryasini kos (CI: nobet.yml::serit-b)")
    ap.add_argument("--json", dest="json_yolu", default=URUNLER,
                    help="dogrulanacak urun JSON yolu (varsayilan: repo koku urunler.json)")
    args = ap.parse_args(argv)

    if args.kendini_test:
        return kendini_test()

    gecerli = gecerli_kategoriler()
    if args.liste:
        for k in gecerli:
            print(k)
        return 0

    with open(args.json_yolu, encoding="utf-8") as f:
        urunler = json.load(f)

    ihlaller = ihlalleri_bul(urunler, gecerli)

    if ihlaller:
        print("KATEGORI KAPISI: %d IHLAL (gecerli: %s)" % (len(ihlaller), ", ".join(gecerli)))
        for uid, kat in ihlaller:
            print("  - %s -> kategori=%r" % (uid, kat))
        print("Duzeltme YOLU: python3 tools/duzelt.py <id> --alan kategori --deger \"<Gecerli>\"")
        return 1

    print("KATEGORI KAPISI: TEMIZ — %d urun, %d gecerli kategori (%s)"
          % (len(urunler), len(gecerli), ", ".join(gecerli)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
