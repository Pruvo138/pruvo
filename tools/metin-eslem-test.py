#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""METIN ESLEM KAPISI — musteri metni derleyiciye ULASIYOR MU (aile aile).

NE KANITLAR (dar, dogru etiket):
  Semasinda `tip: "metin"` parametresi olan HER aile icin, YALNIZ o metin degisirken
  (geometri parametreleri SABIT) onizleme/uretim derleyicisine giden -D BAYRAK KUMESI
  IKI FARKLI METINDE FARKLI OLUR.
  Olcum GERCEK kodla yapilir: eslem uretimi tools/onizleme-paket-yukle.py
  (acik_eslem_uret) + bayrak uretimi onizleme/derleyici/server.py (d_bayraklari).
  Kopya mantik yazilmaz.

NE KANITLAMAZ (iddia edilmez):
  * Metnin DOGRU yere, dogru boyutta, okunur bicimde basildigini KANITLAMAZ
    (bunun icin gercek OpenSCAD render'i gerekir -> .github/workflows/onizleme-imaj.yml
    "metin farklilasma" duman adimi iki farkli metinle GERCEK STL uretip cmp'ler).
  * Ciktinin GEOMETRIK olarak gecerli oldugunu kanitlamaz.
  * Uzunluk tavani (server METIN_SERT_TAVAN=24) asildiginda musteriye ne soylendigini
    kanitlamaz (metin sessizce KIRPILIR; sema maksUzunluk degerleriyle celiskisi
    RAPOR-MIMARA.md'de tarif edildi, davranis bu turda DEGISTIRILMEDI).

NEDEN VAR (olculmus sessiz hata, 29 Tem 2026):
  Canli onizleme ucundan (POST /api/onizleme/olustur, tarayici UA, cache-bust yok)
  ayni geometriyle uc metin denendi:
    olcuye-ozel-cerceve      '' / 'OKAN' / 'ZZZZZZZZ' -> UCU DE 65284 bayt, 1304 ucgen, AYNI SHA-256
    olcuye-ozel-cetvel       '' / 'OKAN' / 'ZZZZZZZZ' -> UCU DE 422184 bayt, 8442 ucgen, AYNI SHA-256
    olcuye-ozel-damga-kase   'PRUVO'/'OKAN'/'ZZZZZZZZ' -> UCU DE 228484 bayt, 4568 ucgen, AYNI SHA-256
    kisiye-ozel-jeton-cip-madalyon (KONTROL) -> 3 metin, 3 FARKLI SHA (calisiyor)
  Yani musteri ne yazarsa yazsin ayni STL uretiliyordu; hicbir test bagirmiyordu.
  Kok neden iki katliydi: (1) eslem ureteci `metin` tipini hic bilmiyordu
  (yapisal engel), (2) metin `sabit` blokuna kacirilmisti ve `sabit` en son
  uygulandigi icin musteri degerini SESSIZCE eziyordu.

KESIF (elle liste YOK — yeni aile sessizce kapsam disi kalmasin):
  jenerator/urunler/*.json DIZIN TARAMASI -> `tip: "metin"` parametresi olan aileler.

ESLEM KAYNAGI (aile basina):
  * ACIK aile (tools/onizleme-paket-yukle.py ACIK_AILELER) -> eslem PUBLIC
    jenerator/test/esleme/<ad>.json'dan TURETILIR; CI fresh checkout'ta da olculur.
  * Gizli-eslem ailesi -> onizleme/derleyici/eslem-ozel.json (gitignore) ya da
    --paket <dizin>/eslem-ozel.json. Dosya YOKSA (GitHub Pages CI) o aile
    ⚪ OLCULEMEDI sayilir; SESSIZ degildir: rapora yazilir ve sayilir.
    TAM kapsam icin gizli paketin CEKILDIGI is akisinda kosun:
      python3 tools/metin-eslem-test.py --paket onizleme/derleyici/paket-ozel

IZIN LISTESI: bir aile ancak GEREKCE ile muaf tutulabilir. Muaf aile GECERSE kapi
KIRMIZI yanar (bayat muafiyet), gerekcesi bossa KIRMIZI yanar, kesifte yoksa
KIRMIZI yanar -> muafiyet curuyemez.

KIRMIZI-MUTASYON (kanit turleri, RAPOR-MIMARA.md'de ham cikti):
  (a) acik_eslem_uret'ten `metin` dali kaldirilir      -> KIRMIZI
  (b) bir ailenin metni `sabit`e geri konur            -> KIRMIZI
  (c) bu dosyanin govdesi no-op yapilir                -> --kendini-test KIRMIZI
      (oz-nobetciler HER kosumda bloklayici olarak isler; govde inert olamaz)
  (d) deploy.yml'deki cagri satiri silinir             -> tools/ci-kapsam-test.py KIRMIZI

Kullanim:
  python3 tools/metin-eslem-test.py
  python3 tools/metin-eslem-test.py --paket onizleme/derleyici/paket-ozel
  python3 tools/metin-eslem-test.py --kendini-test
"""
import argparse
import glob
import importlib.util
import json
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
SEMA_DIZIN = os.path.join(ROOT, "jenerator", "urunler")
GIZLI_ESLEM = os.path.join(ROOT, "onizleme", "derleyici", "eslem-ozel.json")

# Iki SOMUT metin: ikisi de sunucunun BEYAZ LISTESINDE, ikisi de 24 karakter sert
# tavanin ALTINDA ve birbirinden farkli -> "fark" iddiasi kirpma/temizleme
# davranisina degil, GERCEK baglantiya dayanir.
METIN_A = "OKAN"
METIN_B = "ZZZZZZZZ"


def _modul(ad, yol):
    spec = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SERVER = _modul("pruvo_onizleme_server",
                os.path.join(ROOT, "onizleme", "derleyici", "server.py"))
PAKET = _modul("pruvo_onizleme_paket",
               os.path.join(TOOLS, "onizleme-paket-yukle.py"))


# ---- IZIN LISTESI (aile -> GEREKCE). Bos gerekce = KIRMIZI. -----------------
IZIN_LISTESI = {
    "olcuye-ozel-cetvel": (
        "KABILIYET BOSLUGU (eslem hatasi DEGIL, 29 Tem olcumu): bu ailenin onizleme/uretim "
        "eslemi gizli uyelik uretecine baglidir ve O URETECTE SERBEST METIN DEGISKENI YOKTUR "
        "(ustdüzey degiskenleri okundu: yalniz olcu/taksimat/font/hizalama + bir SVG 'Graphic' "
        "bayragi; musteri yazisi icin bir Text/Caption degiskeni yok). Yani sema `yazi` "
        "parametresini vaat ediyor ama bagli motor onu FIZIKSEL OLARAK basamiyor; hicbir eslem "
        "duzeltmesi bunu cozmez. KARAR MIMARDA (iki yol RAPOR-MIMARA.md'de): (A) aileyi bizim "
        "kendi uretecimize tasi (public test eslemi ZATEN yazi->yazi_logo esliyor; gizli "
        "eslemden aile blogu silinmeli — ACIK_AILELER cakisma kapisi bunu zorunlu kilar), "
        "(B) semadan `yazi` parametresini kaldir (musteriye teslim edilemeyen alan sorulmasin). "
        "Karar uygulanip aile GECER hale gelince bu giris SILINMELIDIR: gecen bir aile izin "
        "listesinde kalirsa kapi 'bayat muafiyet' diye KIRMIZI yanar."),
}


def semalari_tara():
    """jenerator/urunler/*.json -> {urunId: sema} (yalniz `metin` parametresi olanlar)."""
    bulunan = {}
    for yol in sorted(glob.glob(os.path.join(SEMA_DIZIN, "*.json"))):
        with open(yol, encoding="utf-8") as f:
            sema = json.load(f)
        metinler = [p["ad"] for p in sema.get("parametreler", [])
                    if p.get("tip") == "metin"]
        if metinler:
            bulunan[sema["id"]] = (sema, metinler)
    return bulunan


def _varsayilan_parametreler(sema):
    """Semadaki varsayilanlardan tam parametre sozlugu (metin alanlari haric)."""
    p = {}
    for tanim in sema.get("parametreler", []):
        if tanim.get("tip") == "metin":
            continue
        p[tanim["ad"]] = tanim.get("varsayilan")
    return p


def _secimleri_eslemle_uyumla(eslem, parametreler):
    """Eslemdeki `secim` tablolarinda KARSILIGI OLMAYAN varsayilanlari tablodan bir
    degerle degistirir. Neden: onizleme eslemi bazi ailelerde semadan DAR tablo tasir
    (or. onizleme kisitlari) -> sema varsayilani tabloda olmayabilir ve olcum
    'secim-tanimsiz' ile YANLIS-KIRMIZI yanardi. Metin iddiasini ETKILEMEZ: iki
    kosumda da AYNI geometri/secim degerleri kullanilir."""
    bloklar = [eslem.get("ortak") or {}]
    for v in (eslem.get("varyantlar") or {}).values():
        bloklar.append(v or {})
    for blok in bloklar:
        for kural in (blok.get("secim") or {}).values():
            param, tablo = kural["param"], kural["tablo"]
            v = parametreler.get(param)
            if SERVER.sayi_mi(v):
                v = SERVER.sayi_metni(v)
            if isinstance(v, str) and v in tablo:
                continue
            anahtar = sorted(tablo.keys())[0]
            try:
                parametreler[param] = float(anahtar) if anahtar.replace(
                    ".", "", 1).replace("-", "", 1).isdigit() else anahtar
            except (AttributeError, ValueError):
                parametreler[param] = anahtar
    return parametreler


def aile_olc(eslem, sema, metin_adlari):
    """(durum, tani) — durum: 'gecti' | 'kaldi'. Metin degisince -D kumesi degisiyor mu?"""
    sorunlar = []
    for metin_ad in metin_adlari:
        temel = _varsayilan_parametreler(sema)
        temel = _secimleri_eslemle_uyumla(eslem, temel)
        pa, pb = dict(temel), dict(temel)
        pa[metin_ad], pb[metin_ad] = METIN_A, METIN_B
        ba, sebep_a = SERVER.d_bayraklari(eslem, pa)
        bb, sebep_b = SERVER.d_bayraklari(eslem, pb)
        if ba is None or bb is None:
            sorunlar.append("%r: eslem bayrak uretemedi (a=%s b=%s)"
                            % (metin_ad, sebep_a, sebep_b))
            continue
        if ba == bb:
            sorunlar.append(
                "%r: iki FARKLI metin (%r vs %r) AYNI -D kumesini uretti -> musteri "
                "metni derleyiciye ULASMIYOR (esleme yok ya da `sabit` eziyor)"
                % (metin_ad, METIN_A, METIN_B))
    return ("kaldi" if sorunlar else "gecti"), sorunlar


def eslem_coz(aile, acik_ad, gizli_eslem):
    """(eslem_blogu | None, kaynak_etiketi, hata)"""
    if acik_ad is not None:
        try:
            urun_id, blok, _scad = PAKET.acik_eslem_uret(acik_ad)
        except SystemExit as e:  # acik_eslem_uret hata halinde sys.exit eder
            return None, "acik", "eslem uretimi DURDU: %s" % (e,)
        if urun_id != aile:
            return None, "acik", "ACIK_AILELER tutarsiz: %s != %s" % (urun_id, aile)
        return blok, "acik(jenerator/test/esleme/%s.json)" % acik_ad, None
    if gizli_eslem is None:
        return None, "gizli", None  # olculemedi (dosya yok)
    blok = gizli_eslem.get(aile)
    if blok is None:
        return None, "gizli", "gizli eslemde aile YOK: %s" % aile
    return blok, "gizli(eslem-ozel.json)", None


def denetle(paket_dizin=None, izin=None, yaz=True):
    """(cikis_kodu, rapor_satirlari)"""
    izin = IZIN_LISTESI if izin is None else izin
    satirlar = []

    def yz(s):
        satirlar.append(s)
        if yaz:
            print(s)

    aileler = semalari_tara()
    yz("Metin parametresi olan aile (dizin taramasi): %d" % len(aileler))

    gizli_yol = (os.path.join(paket_dizin, "eslem-ozel.json")
                 if paket_dizin else GIZLI_ESLEM)
    gizli = None
    if os.path.exists(gizli_yol):
        with open(gizli_yol, encoding="utf-8") as f:
            gizli = json.load(f)["aileler"]
        yz("Gizli eslem: VAR (%s) -> gizli-eslem aileleri de olculuyor"
           % os.path.relpath(gizli_yol, ROOT))
    else:
        yz("Gizli eslem: YOK -> gizli-eslem aileleri ⚪ OLCULEMEDI "
           "(tam kapsam: --paket <gizli paket dizini>)")

    gecen, kalan, olculemeyen, muaf_gecti = [], [], [], []
    for aile in sorted(aileler):
        sema, metin_adlari = aileler[aile]
        acik_ad = PAKET.ACIK_AILELER.get(aile)
        eslem, kaynak, hata = eslem_coz(aile, acik_ad, gizli)
        etiket = "%s [%s]" % (aile, kaynak)
        if eslem is None and hata is None:
            olculemeyen.append(aile)
            yz("  ⚪ %s — gizli eslem yok, OLCULEMEDI" % etiket)
            continue
        if eslem is None:
            durum, sorunlar = "kaldi", [hata]
        else:
            durum, sorunlar = aile_olc(eslem, sema, metin_adlari)
        if durum == "gecti":
            if aile in izin:
                muaf_gecti.append(aile)
                yz("  ❌ %s — BAYAT MUAFIYET: aile artik GECIYOR, izin listesinden CIKAR"
                   % etiket)
            else:
                gecen.append(aile)
                yz("  ✅ %s — metin degisince -D kumesi DEGISIYOR (%s)"
                   % (etiket, ", ".join(metin_adlari)))
        elif aile in izin:
            yz("  🟡 %s — MUAF (gerekceli): %s" % (etiket, sorunlar[0]))
        else:
            kalan.append(aile)
            for s in sorunlar:
                yz("  ❌ %s — %s" % (etiket, s))

    hatalar = []
    for aile, gerekce in sorted(izin.items()):
        if not (gerekce or "").strip():
            hatalar.append("izin listesinde GEREKCESIZ giris: %s" % aile)
        if aile not in aileler:
            hatalar.append("izin listesinde olup KESFEDILMEYEN aile (bayat giris): %s"
                           % aile)
    for aile in muaf_gecti:
        hatalar.append("BAYAT MUAFIYET: %s artik geciyor -> izin listesinden cikarilmali"
                       % aile)
    for aile in kalan:
        hatalar.append("METIN DUSUYOR: %s" % aile)

    yz("")
    yz("Gecen: %d | Kalan: %d | Muaf (izin listesi): %d | Olculemedi: %d"
       % (len(gecen), len(kalan), len(izin), len(olculemeyen)))
    if hatalar:
        yz("SONUC: KIRMIZI (%d sorun)" % len(hatalar))
        for h in hatalar:
            yz("  ❌ %s" % h)
        return 1, satirlar
    yz("SONUC: YESIL")
    return 0, satirlar


# ---- OZ-NOBETCILER (govde no-op olamasin) ----------------------------------
_SENTETIK_SEMA = {
    "id": "zzz-sentetik-metin-ailesi",
    "parametreler": [
        {"ad": "boy", "tip": "sayi", "varsayilan": 20},
        {"ad": "yazi", "tip": "metin", "varsayilan": ""},
    ],
}


def oz_nobetci():
    """GOVDE-INERTLIK NOBETCISI (mutasyon (c)).

    aile_olc()'un GERCEKTEN olctugunu uc sentetik eslemle kanitlar. Govde no-op
    yapilirsa (or. hep 'gecti' donerse ya da iddia silinirse) 1. ve 3. iddia
    KIRMIZI yanar; hep 'kaldi' donerse 2. iddia KIRMIZI yanar. Yani nobetci
    her iki yonde de sabitlenmis bir govdeyi yakalar.
    (ok, hata_listesi) doner."""
    sema = _SENTETIK_SEMA
    hata = []

    # 1) SABIT'e kacirilmis metin -> musteri degeri ezilir -> KALDI olmali
    kotu = {"scad": "x.scad", "secici": None, "varyantlar": None,
            "ortak": {"sayisal": {"B": {"terimler": {"boy": 1}}},
                      "sabit": {"Yazi": ""}}}
    d, _ = aile_olc(kotu, sema, ["yazi"])
    if d != "kaldi":
        hata.append("(1) SABIT'e kacirilmis metin 'gecti' sayildi -> govde inert "
                    "(beklenen 'kaldi', gelen %r)" % d)

    # 2) DOGRU `metin` blogu -> GECTI olmali
    iyi = {"scad": "x.scad", "secici": None, "varyantlar": None,
           "ortak": {"sayisal": {"B": {"terimler": {"boy": 1}}},
                     "metin": {"Yazi": {"param": "yazi"}}}}
    d, sorun = aile_olc(iyi, sema, ["yazi"])
    if d != "gecti":
        hata.append("(2) DOGRU metin eslemesi 'kaldi' sayildi -> yanlis-pozitif "
                    "(sorunlar: %s)" % sorun)

    # 3) metin BAGLI ama `sabit` AYNI degiskeni eziyor -> KALDI olmali
    #    (server.py'de `sabit` en son uygulanir; cerceve'de olculen tam bu hal)
    ezen = {"scad": "x.scad", "secici": None, "varyantlar": None,
            "ortak": {"sayisal": {"B": {"terimler": {"boy": 1}}},
                      "metin": {"Yazi": {"param": "yazi"}},
                      "sabit": {"Yazi": ""}}}
    d, _ = aile_olc(ezen, sema, ["yazi"])
    if d != "kaldi":
        hata.append("(3) `sabit` ezmesi 'gecti' sayildi -> govde SIRA/EZME halini "
                    "olcmuyor (beklenen 'kaldi', gelen %r)" % d)

    # 4) KESIF canlı mi: dizin taramasi en az bir aile bulmali (sema dizini
    #    tasinir/predikat bozulursa kapi sessizce BOS kume uzerinde yesil yanardi)
    if not semalari_tara():
        hata.append("(4) KESIF BOS: jenerator/urunler taramasi `tip:metin` olan hicbir "
                    "aile bulmadi -> predikat/dizin bozulmus, kapi anlamsiz yesil yanardi")
    return (not hata), hata


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paket", metavar="DIZIN",
                    help="gizli paket dizini (eslem-ozel.json burada) — TAM kapsam")
    ap.add_argument("--kendini-test", action="store_true",
                    help="yalniz oz-nobetcileri kosar ve raporlar")
    args = ap.parse_args()

    ok, hata = oz_nobetci()
    print("OZ-NOBETCI: %s" % ("YESIL" if ok else "KIRMIZI"))
    for h in hata:
        print("  ❌ %s" % h)
    if args.kendini_test:
        sys.exit(0 if ok else 1)

    kod, _ = denetle(args.paket)
    sys.exit(0 if (kod == 0 and ok) else 1)


if __name__ == "__main__":
    main()
