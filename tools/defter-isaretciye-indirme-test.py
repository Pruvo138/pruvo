#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K195(a) KABUL TESTI — defter-rotasyon.py `--isaretciye-indir` kolu.

OLCULEN DELIK (19 Agu 2026): defter tavan ustundeyken KAPALI icerik yoksa arac
hicbir sey tasimiyordu (KAYIP / ILERLEME_YOK) ve mimar ELLE rotasyona
zorlaniyordu — bir gunde 4 kez.

🔴 TUM VAKALAR FIKSTUR UZERINDE KOSAR. Gercek DEVAM.md / DEVAM-ARSIV.md'ye
ASLA dokunulmaz; kosum sonunda ikisinin de bayti dogrulanir.

🔴 FIKSTUR AYRIMI (ilk kosumda OLCULDU, [[mutant-yan-ekseni-de-tetikliyorsa-olcmez]]):
Ilk tasarimda tek bir fikstur vardi ve DORT mutantin dordu de YASADI — cunku
fikstur hedef kollari AYIRT ETMIYORDU. Ornek: korumali liste bosaltilinca bile
EN BUYUK blok yine `SON DURUM` oldugu icin `ACIK KALEMLER` kazara kurtuluyordu.
Her vaka artik KENDI fiksturunu kurar ve hedef kolu GERCEKTEN calistirir:
  * V3 -> KORUMALI blok EN BUYUK olacak sekilde kurulur (koruma kalkarsa o iner)
  * V6 -> IKI indirilebilir blok, EN BUYUK olan IKINCI (ilk-aday mutanti yanilir)
  * V5 -> aday VAR ama indirmek bayt KAZANDIRMAZ (ilerleme invaryanti tetiklenir)
  * V1 -> isaretci satirinin KENDISI aranir (isaretci yazilmazsa kirmizi)

VAKALAR
  V1 ilerleme + ISARETCI satiri yazildi
  V2 tasinan blogun TAM METNI arsivde (kayipsiz)
  V3 KORUMALI blok EN BUYUK olsa bile INMEDI
  V4 bayrak YOK -> davranis DEGISMEDI (KAYIP/ILERLEME_YOK) + CARE satiri
  V5 aday var ama ilerleme YOK -> OLCULEMEDI + dosyalar BIREBIR
  V6 IKI aday -> EN BUYUK olan indi (ilk olan degil)
  K1 KONTROL tavan ALTI -> NO_OP, dosyalar BIREBIR

MUTANTLAR (K182 hedef-kol atfi: olen kume == hedef kume)
  M1 korumali baslik listesi bosaltilir   -> V3
  M2 ilerleme invaryanti kaldirilir       -> V5
  M3 "en buyuk" yerine ILK aday secilir   -> V6
  M4 isaretci satiri yazilmaz             -> V1

Kullanim: python3 tools/defter-isaretciye-indirme-test.py
Son satir: VAKA=<n>/<n> MUTANT=<n>/<n> HEDEF_KOL_ATFI=<n>/<n> DUSEN=<n>
"""
import os
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

TOOLS = os.path.dirname(os.path.abspath(__file__))
ARAC = os.path.join(TOOLS, "defter-rotasyon.py")
GERCEK_DEFTER = "/Users/okan/dev/pruvo/DEVAM.md"
GERCEK_ARSIV = "/Users/okan/dev/pruvo/DEVAM-ARSIV.md"

CAPA_M1 = ('KORUMALI_BASLIK_DESENLERI = ("ACIK KALEMLER", "OKAN\'DA", '
           '"OKAN`DA", "ARSIVDE")')
CAPA_M2 = "    if kazanc <= 0:"
CAPA_M3 = '    hedef = max(adaylar, key=lambda b: len(_blok_metni(b).encode("utf-8")))'
# 🔴 M4 NEDEN "ISARETCI SATIRINI HIC YAZMA" DEGIL: o mutant isaretcinin
# BAYTINI da kaldirir, boylece ilerleme aritmetigini degistirip V5'i de
# oldururdu (olculdu: olen={V1,V5}) — yani hedef kolu ISOLE olcemezdi.
# Bunun yerine YALNIZ isaretci METNI bozulur; bayt ~ayni kalir, sadece
# "TAM METIN ARSIVDE" izi kaybolur. Hedef kol boylece TEK basina olculur.
CAPA_M4 = '    isaretci = ("- ↩︎ **TAM METIN ARSIVDE** (%s isaretciye indirme): bu blogun tam "'
YERINE_M4 = '    isaretci = ("- ↩︎ **iz metni bozuldu** (%s isaretciye indirme): bu blogun tam "'

ISARETCI_IZI = "TAM METIN ARSIVDE"


def _bayt(yol):
    with open(yol, "rb") as f:
        return f.read()


def _defter_yaz(kok, bloklar):
    """bloklar: [(baslik, [govde satirlari]), ...] — hicbirinde KAPANIS jetonu yok."""
    parcalar = ["# DEVAM — test fiksturu", ""]
    for baslik, govde in bloklar:
        parcalar.append(baslik)
        parcalar.append("")
        parcalar.extend(govde)
        parcalar.append("")
    defter = os.path.join(kok, "DEVAM.md")
    arsiv = os.path.join(kok, "DEVAM-ARSIV.md")
    with open(defter, "w", encoding="utf-8") as f:
        f.write("\n".join(parcalar) + "\n")
    with open(arsiv, "w", encoding="utf-8") as f:
        f.write("# ARSIV\n\n## eski kayit\n\neski satir\n")
    return defter, arsiv


def _dolgu(etiket, n, genislik=40):
    """NOTR dolgu satiri: ne ACIK ne KAPANIS jetonu tasir.

    🔴 19 AGU DUZELTMESI (K195 §1.2): bu yardimci eskiden `_acik` adiyla
    `- 🔴 ...` satirlari uretiyordu ve V1/V2/V6 tam da YASAK olan seyi
    KABUL EDIYORDU — govdesi ACIK KALEM dolu bir blogun tam metniyle arsive
    inmesini. Yani fikstur, "acik kalem asla arsivlenmez" kuralinin ihlalini
    YESIL sayiyordu. Veto kolu eklenince bu ortaya cikti; dolgu NOTR yapildi.
    ACIK jetonun kendi vetosu AYRI bir kabul testinde olculur:
    tools/defter-rotasyon-cifti-test.py (C2).

    🔴 NEDEN `✅` DEGIL: kapanis jetonu koymak blogu `_tasinir_mi()` yoluna
    sokar ve blok NORMAL rotasyonla tasinir — isaretciye indirme kolu HIC
    kosmaz, yani hedef kol olculemez.
    """
    return ["- %s satir %d %s" % (etiket, i + 1, "x" * genislik)
            for i in range(n)]


def _kos(arac, defter, arsiv, *ek):
    return subprocess.run(
        [sys.executable, arac, defter, arsiv, "--tarih", "2026-08-19"] + list(ek),
        capture_output=True, text=True)


# --- FIKSTURLER ----------------------------------------------------------
def _f_standart(kok):
    """SON DURUM en buyuk indirilebilir blok; korumalilar kucuk."""
    return _defter_yaz(kok, [
        ("## ACIK KALEMLER (korumali)", _dolgu("KORUMALI-ACIK", 2)),
        ("## 🔻 SON DURUM — test blogu", _dolgu("DURUM", 40)),
        ("## OKAN'DA", _dolgu("KORUMALI-OKAN", 2)),
    ])


def _f_korumali_en_buyuk(kok):
    """🔴 KORUMALI blok EN BUYUK. Koruma kalkarsa O iner -> V3 kirmizi yanar.

    🔴 BASLIK NEDEN `ARSIVDE`, `ACIK KALEMLER` DEGIL (19 Agu, olculdu):
    `ACIK KALEMLER` hem KORUMALI_BASLIK_DESENLERI'nde hem ACIK_ISARETCILER'de
    gecer. K195 §1.2 ACIK vetosu eklenince M1 mutanti (koruma listesi bosaltilir)
    OLU kaldi: liste bosalsa bile blok ACIK jeton tasidigi icin yine inmiyordu,
    yani V3 yesil kaliyor ve mutant "YASADI" diyordu — hedef kol OLCULEMIYORDU.
    `ARSIVDE` yalniz KORUMALI listesinde gecer; koruma kalkinca blok GERCEKTEN
    indirilebilir olur ve M1 hedefini vurur.
    """
    return _defter_yaz(kok, [
        ("## ARSIVDE (korumali)", _dolgu("KORUMALI-ARSIVDE", 60)),
        ("## 🔻 SON DURUM — test blogu", _dolgu("DURUM", 10)),
    ])


def _f_iki_aday(kok):
    """IKI indirilebilir blok; EN BUYUK olan IKINCI -> ilk-aday mutanti yanilir."""
    return _defter_yaz(kok, [
        ("## ACIK KALEMLER (korumali)", _dolgu("KORUMALI-ACIK", 2)),
        ("## 🔻 SON DURUM A — kucuk", _dolgu("KUCUK-A", 6)),
        ("## 🔻 SON DURUM B — buyuk", _dolgu("BUYUK-B", 50)),
    ])


def _f_ilerlemesiz(kok):
    """Aday VAR (4 anlamli satir > esik 3) ama govdesi isaretciden KUCUK.

    Indirme bayt KAZANDIRMAZ -> ilerleme invaryanti tetiklenmeli.
    """
    return _defter_yaz(kok, [
        ("## ACIK KALEMLER (korumali)", _dolgu("KORUMALI-ACIK", 2)),
        ("## 🔻 SON DURUM — minik", ["a", "b", "c", "d"]),
    ])


# --- VAKALAR -------------------------------------------------------------
def _v1(arac):
    kok = tempfile.mkdtemp(prefix="k195a-v1-")
    try:
        defter, arsiv = _f_standart(kok)
        d0, a0 = len(_bayt(defter)), len(_bayt(arsiv))
        r = _kos(arac, defter, arsiv, "--tavan-sayi", "20", "--isaretciye-indir")
        d1, a1 = len(_bayt(defter)), len(_bayt(arsiv))
        isaretci = ISARETCI_IZI in _bayt(defter).decode("utf-8")
        iyi = (r.returncode == 0 and "ISARETCIYE_INDIRILDI" in r.stdout
               and d1 < d0 and a1 > a0 and isaretci)
        return iyi, "rc=%d defter %d->%d arsiv %d->%d isaretci=%s" % (
            r.returncode, d0, d1, a0, a1, isaretci)
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def _v2(arac):
    kok = tempfile.mkdtemp(prefix="k195a-v2-")
    try:
        defter, arsiv = _f_standart(kok)
        r = _kos(arac, defter, arsiv, "--tavan-sayi", "20", "--isaretciye-indir")
        arsiv_metin = _bayt(arsiv).decode("utf-8")
        eksik = [s for s in _dolgu("DURUM", 40) if s not in arsiv_metin]
        iyi = r.returncode == 0 and not eksik
        return iyi, "rc=%d arsivde_eksik_satir=%d/40" % (r.returncode, len(eksik))
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def _v3(arac):
    """KORUMALI blok EN BUYUK olsa bile INMEZ."""
    kok = tempfile.mkdtemp(prefix="k195a-v3-")
    try:
        defter, arsiv = _f_korumali_en_buyuk(kok)
        r = _kos(arac, defter, arsiv, "--tavan-sayi", "20", "--isaretciye-indir")
        defter_metin = _bayt(defter).decode("utf-8")
        korumali_satirlar = _dolgu("KORUMALI-ARSIVDE", 60)
        kalan = [s for s in korumali_satirlar if s in defter_metin]
        # 🔴 rc BURADA OLCUT DEGIL: korumali blok tavandan BUYUK oldugu icin
        # arac tavan altina INEMEZ ve rc=4/OLCULEMEDI donmesi DOGRU davranistir.
        # Olculen tek sey: korumali blok ASLA inmemeli.
        iyi = len(kalan) == 60
        return iyi, "rc=%d korumali_satir_defterde=%d/60" % (r.returncode, len(kalan))
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def _v4(arac):
    kok = tempfile.mkdtemp(prefix="k195a-v4-")
    try:
        defter, arsiv = _f_standart(kok)
        onceki = _bayt(defter)
        r = _kos(arac, defter, arsiv, "--tavan-sayi", "20")
        eski = ("KAYIP:" in r.stderr or "ILERLEME_YOK" in r.stderr
                or "TAVAN_FAIL_LOUD" in r.stderr)
        iyi = (r.returncode != 0 and eski and "CARE (K195a)" in r.stderr
               and _bayt(defter) == onceki)
        return iyi, "rc=%d eski_davranis=%s care=%s birebir=%s" % (
            r.returncode, eski, "CARE (K195a)" in r.stderr,
            _bayt(defter) == onceki)
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def _v5(arac):
    """Aday VAR ama ilerleme YOK -> OLCULEMEDI + dosyalar BIREBIR."""
    kok = tempfile.mkdtemp(prefix="k195a-v5-")
    try:
        defter, arsiv = _f_ilerlemesiz(kok)
        d0, a0 = _bayt(defter), _bayt(arsiv)
        r = _kos(arac, defter, arsiv, "--tavan-sayi", "5", "--isaretciye-indir")
        iyi = (r.returncode != 0 and "OLCULEMEDI" in r.stderr
               and _bayt(defter) == d0 and _bayt(arsiv) == a0)
        return iyi, "rc=%d olculemedi=%s defter_birebir=%s arsiv_birebir=%s" % (
            r.returncode, "OLCULEMEDI" in r.stderr,
            _bayt(defter) == d0, _bayt(arsiv) == a0)
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def _v6(arac):
    """IKI aday -> EN BUYUK olan (B) indi, kucuk olan (A) defterde KALDI."""
    kok = tempfile.mkdtemp(prefix="k195a-v6-")
    try:
        defter, arsiv = _f_iki_aday(kok)
        # TAVAN 30: B indirilince tavan altina INILIR, dongu A'ya UZANMAZ.
        # (20 ile iki indirme birden olurdu ve "hangisi secildi" olculemezdi.)
        r = _kos(arac, defter, arsiv, "--tavan-sayi", "30", "--isaretciye-indir")
        defter_metin = _bayt(defter).decode("utf-8")
        buyuk_kalan = [s for s in _dolgu("BUYUK-B", 50) if s in defter_metin]
        kucuk_kalan = [s for s in _dolgu("KUCUK-A", 6) if s in defter_metin]
        # DOGRU davranis: B indi (defterde 0), A durdu (defterde 6)
        iyi = (r.returncode == 0 and len(buyuk_kalan) == 0
               and len(kucuk_kalan) == 6)
        return iyi, "rc=%d buyuk_B_defterde=%d/50 kucuk_A_defterde=%d/6" % (
            r.returncode, len(buyuk_kalan), len(kucuk_kalan))
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def _k1(arac):
    kok = tempfile.mkdtemp(prefix="k195a-k1-")
    try:
        defter, arsiv = _f_standart(kok)
        d0, a0 = _bayt(defter), _bayt(arsiv)
        r = _kos(arac, defter, arsiv, "--tavan-sayi", "100000", "--isaretciye-indir")
        iyi = (r.returncode == 0 and "NO_OP" in r.stdout
               and _bayt(defter) == d0 and _bayt(arsiv) == a0)
        return iyi, "rc=%d no_op=%s birebir=%s" % (
            r.returncode, "NO_OP" in r.stdout,
            _bayt(defter) == d0 and _bayt(arsiv) == a0)
    finally:
        shutil.rmtree(kok, ignore_errors=True)


VAKALAR = [("V1 ilerleme + ISARETCI satiri", _v1),
           ("V2 tasinan metin arsivde", _v2),
           ("V3 korumali EN BUYUK inmedi", _v3),
           ("V4 bayraksiz davranis + CARE", _v4),
           ("V5 ilerleme yok -> OLCULEMEDI", _v5),
           ("V6 EN BUYUK aday indi", _v6),
           ("K1 KONTROL tavan alti NO_OP", _k1)]

MUTANTLAR = [
    ("M1 korumali baslik listesi bosaltilir", CAPA_M1,
     "KORUMALI_BASLIK_DESENLERI = ()", {"V3 korumali EN BUYUK inmedi"}),
    ("M2 ilerleme invaryanti kaldirilir", CAPA_M2, "    if False:",
     {"V5 ilerleme yok -> OLCULEMEDI"}),
    ("M3 'en buyuk' yerine ILK aday", CAPA_M3, "    hedef = adaylar[0]",
     {"V6 EN BUYUK aday indi"}),
    ("M4 isaretci izi bozulur", CAPA_M4, YERINE_M4,
     {"V1 ilerleme + ISARETCI satiri"}),
]


def _mutant(kok, capa, yeni):
    """Mutant kopyayi kur.

    🔴 KARDES MODUL: defter-rotasyon.py acilirken `_TOOLS/defter-kota-taban.py`
    dosyasini KENDI dizininden yukler. Mutant kopyayi ciplak temp dizine koymak
    araci ACILISTA cokertir; o zaman TUM vakalar kirmizi yanar ve mutant "her
    seyi oldurdu" gibi gorunur — hedef-kol atfi OLCULEMEZ (ilk kosumda tam bu
    olculdu: 4 mutantin dordu de 6/6 vaka "oldurdu"). Kardes modul mutantin
    YANINA kopyalanir.
    """
    with open(ARAC, "r", encoding="utf-8") as f:
        kaynak = f.read()
    if kaynak.count(capa) != 1:
        raise AssertionError("capa BENZERSIZ degil (%d): %r" %
                             (kaynak.count(capa), capa[:70]))
    hedef = os.path.join(kok, "defter-rotasyon.py")
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(kaynak.replace(capa, yeni))
    shutil.copy2(os.path.join(TOOLS, "defter-kota-taban.py"),
                 os.path.join(kok, "defter-kota-taban.py"))
    return hedef


def main():
    gercek_d = _bayt(GERCEK_DEFTER) if os.path.exists(GERCEK_DEFTER) else None
    gercek_a = _bayt(GERCEK_ARSIV) if os.path.exists(GERCEK_ARSIV) else None

    print("ARAC = %s" % ARAC)
    print()
    print("--- VAKALAR (gercek arac, FIKSTUR defter) ---")
    vaka = {}
    for ad, fn in VAKALAR:
        iyi, detay = fn(ARAC)
        vaka[ad] = iyi
        print("  %-32s %-8s %s" % (ad, "YESIL" if iyi else "KIRMIZI", detay))
    vaka_gecen = sum(1 for v in vaka.values() if v)

    print()
    print("--- MUTANTLAR (hedef kol atfi: K182) ---")
    olen_say = 0
    atif_say = 0
    for ad, capa, yeni, hedefler in MUTANTLAR:
        kok = tempfile.mkdtemp(prefix="k195a-mut-")
        try:
            mut = _mutant(kok, capa, yeni)
            olenler = {vad for vad, fn in VAKALAR if not fn(mut)[0]}
        finally:
            shutil.rmtree(kok, ignore_errors=True)
        if olenler:
            olen_say += 1
        atif = (olenler == hedefler)
        if atif:
            atif_say += 1
        print("  %-38s %s" % (ad, "OLDU" if olenler else "YASADI"))
        print("      olen  : %s" % (sorted(olenler) or "-"))
        print("      hedef : %s" % sorted(hedefler))
        print("      ATIF  : %s" % ("DOGRU" if atif else "YANLIS"))

    print()
    d_ayni = gercek_d is None or _bayt(GERCEK_DEFTER) == gercek_d
    a_ayni = gercek_a is None or _bayt(GERCEK_ARSIV) == gercek_a
    print("GERCEK DEFTER BIREBIR = %s" % ("EVET" if d_ayni else "HAYIR"))
    print("GERCEK ARSIV  BIREBIR = %s" % ("EVET" if a_ayni else "HAYIR"))

    dusen = ((len(VAKALAR) - vaka_gecen) + (len(MUTANTLAR) - olen_say)
             + (len(MUTANTLAR) - atif_say) + (0 if d_ayni else 1)
             + (0 if a_ayni else 1))
    print()
    print("VAKA=%d/%d MUTANT=%d/%d HEDEF_KOL_ATFI=%d/%d DUSEN=%d" % (
        vaka_gecen, len(VAKALAR), olen_say, len(MUTANTLAR),
        atif_say, len(MUTANTLAR), dusen))
    return 0 if dusen == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
