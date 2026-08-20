#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K195 KABUL TESTI — rotasyon CIFTI (1:1 LOSSLESS) + ACIK KALEM vetosu + BAYT ekseni.

OLCULEN DELIK (19 Agu 2026, KraL-K195 chip on-olcumu — oncul degil, SAYI):
  1. `defter-kota-kapisi` bir oturumda DORT kez ayni gerekcyle (ASAN_EKSEN=BAYT)
     commit'i reddetti; her seferinde mimar ELLE cumle kisaltti.
  2. Gercek DEVAM.md uzerinde olculdu: korumasiz TEK blok (`🔻 KraL CANLI DURUM`)
     ACIK jeton TASIYOR ve eski kod onu `indirilebilir=True` sayiyordu — yani
     isaretciye indirme kolu ACIK KALEMI arsivleyebiliyordu (yasak).
  3. Gercek DEVAM.md uzerinde olculdu: bayraksiz rotasyon iki KAPANMIS maddeyi
     tasidi, bayt 12288 -> 11831 DUSTU ama SATIR 120 -> 123 CIKTI. Arac blok
     sinirlarina bos satir UYDURUYORDU; tasima "1:1" degildi.

🔴 TUM VAKALAR FIKSTUR UZERINDE KOSAR. Gercek DEVAM.md / DEVAM-ARSIV.md'ye
ASLA dokunulmaz; kosum sonunda ikisinin de bayti dogrulanir.

VAKALAR
  C1 ROTASYON CIFTI 1:1  — kapali maddeler tasindi, LOSSLESS=EVET, uydurulan=0,
                            defterden dusen satir == tasinan icerik satiri,
                            tasinan her satir arsivde
  C2 ACIK KALEM VETOSU   — korumasiz ama ACIK jetonlu blok INMEDI; TASINMADI
                            satiri sebebiyle basildi; acik satirlar arsivde YOK
  C3 BAYT EKSENI         — yalniz --tavan-bayt ile kosuldu, isaretciye indirme
                            calisti, defter bayt tavaninin ALTINA indi
  C4 KOTA KENDI OLCUMU   — arac kotayi kendi olcup basti; sayilar dosyanin
                            bagimsiz olcumuyle BIREBIR ayni
  K1 KONTROL tavan alti  — NO_OP, iki dosya da BIREBIR

MUTANTLAR (K182 hedef-kol atfi: olen kume == hedef kume)
  M1 1:1 kolu bozulur (blok sinirina bos satir uydurulur)  -> C1
  M2 ACIK KALEM vetosu kaldirilir                          -> C2
  M3 BAYT kolu no-op edilir                                -> C3

🔴 M1 NEDEN "KONTROLU SUS" DEGIL "OZELLIGI BOZ": kontrolu no-op etmek (LOSSLESS
hep EVET) DOGRU kod uzerinde hicbir vakayi oldurmez — cunku dogru kodda ihlal
YOKTUR; boyle bir mutant "yasadi" der ve hicbir sey olcmez. Olcmek istedigimiz
sey kontrolun DISI: M1 aracin defterine satir UYDURTUR, C1 de ihlali kontrolun
YAKALADIGINI (LOSSLESS=HAYIR + rc=5 + dosyalarin GERI ALINMASI) arar. Yani C1
kirmizi yandiginda kanit sudur: 1:1 kolu gercekten olcuyor ve durduruyor.

Kullanim: python3 tools/defter-rotasyon-cifti-test.py
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

# --- MUTANT CAPALARI (BENZERSIZ olmali; _mutant sayiyi dogrular) ------------
CAPA_M1 = ("    for blok in kalacak_bloklar:\n"
           "        yeni_defter_satirlar.append(blok[\"baslik\"])\n"
           "        yeni_defter_satirlar.extend(blok[\"govde\"])\n")
YERINE_M1 = ("    for blok in kalacak_bloklar:\n"
             "        yeni_defter_satirlar.append(blok[\"baslik\"])\n"
             "        yeni_defter_satirlar.extend(blok[\"govde\"])\n"
             "        yeni_defter_satirlar.append(\"\")\n")

CAPA_M2 = ("    if _acik_eslesiyor(tum):\n"
           "        return \"ACIK KALEM tasiyor (ACIK jetonu blokta gecti) — K195 §1.2\"\n")
YERINE_M2 = ("    if False:\n"
             "        return \"ACIK KALEM tasiyor (ACIK jetonu blokta gecti) — K195 §1.2\"\n")

CAPA_M3 = ("    if tavan_bayt is not None and bayt > tavan_bayt:\n"
           "        return True\n")
YERINE_M3 = ("    if False and tavan_bayt is not None and bayt > tavan_bayt:\n"
             "        return True\n")


def _bayt(yol):
    with open(yol, "rb") as f:
        return f.read()


def _olc(yol):
    ham = _bayt(yol)
    return len(ham.splitlines()), len(ham)


def _defter_yaz(kok, bloklar, arsiv_govdesi="# ARSIV\n\n## eski kayit\n\neski satir\n"):
    """bloklar: [(baslik, [govde satirlari]), ...]"""
    satirlar = ["# DEVAM — K195 cift testi fiksturu", ""]
    for baslik, govde in bloklar:
        satirlar.append(baslik)
        satirlar.append("")
        satirlar.extend(govde)
        satirlar.append("")
    defter = os.path.join(kok, "DEVAM.md")
    arsiv = os.path.join(kok, "DEVAM-ARSIV.md")
    with open(defter, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar) + "\n")
    with open(arsiv, "w", encoding="utf-8") as f:
        f.write(arsiv_govdesi)
    return defter, arsiv


def _notr(etiket, n, genislik=45):
    """Ne ACIK ne KAPANIS jetonu tasiyan dolgu."""
    return ["- %s satir %d %s" % (etiket, i + 1, "x" * genislik) for i in range(n)]


def _acik(etiket, n, genislik=45):
    return ["- 🔴 **%s-%02d** acik kalem %s" % (etiket, i + 1, "x" * genislik)
            for i in range(n)]


def _kapali(etiket, n, genislik=45):
    """`- ` ilk jetonu KAPANDI olan, gercekten tasinabilir madde."""
    return ["- ✅ **%s%02d KAPANDI** detay %s" % (etiket, i + 1, "x" * genislik)
            for i in range(n)]


def _kos(arac, defter, arsiv, *ek):
    return subprocess.run(
        [sys.executable, arac, defter, arsiv, "--tarih", "2026-08-19"] + list(ek),
        capture_output=True, text=True)


# --- FIKSTURLER ------------------------------------------------------------
def _f_kapali_madde(kok):
    """ACIK jetonlu bir blogun ICINDE kapali maddeler.

    Blok ACIK jeton tasidigi icin BUTUN halinde tasinmaz; MADDE granulunde
    tasima calisir — gercek DEVAM.md'de olculen vakanin ta kendisi.
    """
    return _defter_yaz(kok, [
        ("## ACIK KALEMLER (korumali)", _acik("K900", 2)),
        ("## 🔻 SON DURUM — karisik blok",
         _acik("K901", 1) + _kapali("K91", 4)),
    ])


def _f_acik_blok(kok):
    """Korumasiz ama ACIK jetonlu BUYUK blok — hicbir kapali icerik YOK."""
    return _defter_yaz(kok, [
        ("## ACIK KALEMLER (korumali)", _acik("K902", 2)),
        ("## 🔻 SON DURUM — acik kalem tasiyan blok", _acik("K903", 30)),
    ])


def _f_notr_blok(kok):
    """Korumasiz, NOTR (indirilebilir) buyuk blok — kapali icerik YOK.

    `_tek_gecis_calistir` bu fiksturde HICBIR SEY tasimaz (kapali madde yok),
    yani M1 (1:1 kolu) bu vakalara DOKUNMAZ — hedef kol atfi boyle izole olur.
    """
    return _defter_yaz(kok, [
        ("## ACIK KALEMLER (korumali)", _acik("K904", 2)),
        ("## 🔻 SON DURUM — notr govde", _notr("DURUM", 30)),
    ])


# --- VAKALAR ---------------------------------------------------------------
def _c1(arac):
    """1:1 LOSSLESS — kapali maddeler tasindi, satir uydurulmadi."""
    kok = tempfile.mkdtemp(prefix="k195c-c1-")
    try:
        defter, arsiv = _f_kapali_madde(kok)
        s0, b0 = _olc(defter)
        tasinan = _kapali("K91", 4)
        r = _kos(arac, defter, arsiv)          # tek gecis (tavan bayragi YOK)
        s1, b1 = _olc(defter)
        cikti = r.stdout + r.stderr
        defter_metin = _bayt(defter).decode("utf-8")
        arsiv_metin = _bayt(arsiv).decode("utf-8")
        arsivde = all(s in arsiv_metin for s in tasinan)
        defterde_yok = all(s not in defter_metin for s in tasinan)
        acik_durdu = all(s in defter_metin for s in _acik("K901", 1))
        iyi = (r.returncode == 0
               and "LOSSLESS=EVET" in cikti
               and "uydurulan=0" in cikti
               and (s0 - s1) == len(tasinan)      # 1:1 — satir sayisi tam dustu
               and b1 < b0
               and arsivde and defterde_yok and acik_durdu)
        return iyi, ("rc=%d satir %d->%d (dusen=%d beklenen=%d) bayt %d->%d "
                     "arsivde=%s defterde_yok=%s acik_durdu=%s lossless=%s" % (
                         r.returncode, s0, s1, s0 - s1, len(tasinan), b0, b1,
                         arsivde, defterde_yok, acik_durdu,
                         "EVET" in cikti and "LOSSLESS=EVET" in cikti))
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def _c2(arac):
    """ACIK KALEM VETOSU — korumasiz ama acik blok INMEDI."""
    kok = tempfile.mkdtemp(prefix="k195c-c2-")
    try:
        defter, arsiv = _f_acik_blok(kok)
        acik_satirlar = _acik("K903", 30)
        r = _kos(arac, defter, arsiv, "--tavan-sayi", "10", "--isaretciye-indir")
        defter_metin = _bayt(defter).decode("utf-8")
        arsiv_metin = _bayt(arsiv).decode("utf-8")
        cikti = r.stdout + r.stderr
        kalan = [s for s in acik_satirlar if s in defter_metin]
        sizan = [s for s in acik_satirlar if s in arsiv_metin]
        # 🔴 rc BURADA OLCUT DEGIL (V3 ile ayni gerekce): indirilebilir aday
        # kalmayinca arac OLCULEMEDI ile durur ve bu DOGRU davranistir.
        iyi = (len(kalan) == 30 and not sizan
               and "TASINMADI:" in cikti and "ACIK KALEM tasiyor" in cikti)
        return iyi, "rc=%d acik_defterde=%d/30 arsive_sizan=%d tasinmadi_satiri=%s" % (
            r.returncode, len(kalan), len(sizan), "ACIK KALEM tasiyor" in cikti)
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def _c3(arac):
    """BAYT EKSENI — yalniz --tavan-bayt ile indirme calisti."""
    kok = tempfile.mkdtemp(prefix="k195c-c3-")
    try:
        defter, arsiv = _f_notr_blok(kok)
        s0, b0 = _olc(defter)
        tavan_bayt = 900
        r = _kos(arac, defter, arsiv, "--tavan-bayt", str(tavan_bayt),
                 "--isaretciye-indir")
        s1, b1 = _olc(defter)
        cikti = r.stdout + r.stderr
        iyi = (r.returncode == 0 and "ISARETCIYE_INDIRILDI" in cikti
               and b0 > tavan_bayt and b1 <= tavan_bayt)
        return iyi, "rc=%d bayt %d->%d (tavan=%d) satir %d->%d indirildi=%s" % (
            r.returncode, b0, b1, tavan_bayt, s0, s1,
            "ISARETCIYE_INDIRILDI" in cikti)
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def _c4(arac):
    """KOTA KENDI OLCUMU — aracin bastigi sayilar dosyanin BAGIMSIZ olcumu."""
    kok = tempfile.mkdtemp(prefix="k195c-c4-")
    try:
        defter, arsiv = _f_notr_blok(kok)
        r = _kos(arac, defter, arsiv, "--tavan-sayi", "8", "--isaretciye-indir")
        cikti = r.stdout + r.stderr
        satir = [s for s in cikti.splitlines() if s.startswith("KOTA_KENDI_OLCUMU")]
        if not satir:
            return False, "rc=%d KOTA_KENDI_OLCUMU satiri BASILMADI" % r.returncode
        alan = dict(p.split("=", 1) for p in satir[-1].split() if "=" in p)
        ger_s, ger_b = _olc(defter)
        iyi = (int(alan.get("satir", -1)) == ger_s
               and int(alan.get("bayt", -1)) == ger_b
               and alan.get("KOTA") in ("YESIL", "KIRMIZI"))
        return iyi, "rc=%d basilan(satir=%s bayt=%s KOTA=%s) gercek(%d/%d)" % (
            r.returncode, alan.get("satir"), alan.get("bayt"),
            alan.get("KOTA"), ger_s, ger_b)
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def _k1(arac):
    """KONTROL — tavan altinda NO_OP, iki dosya da BIREBIR."""
    kok = tempfile.mkdtemp(prefix="k195c-k1-")
    try:
        defter, arsiv = _f_notr_blok(kok)
        d0, a0 = _bayt(defter), _bayt(arsiv)
        r = _kos(arac, defter, arsiv, "--tavan-bayt", "100000", "--isaretciye-indir")
        birebir = _bayt(defter) == d0 and _bayt(arsiv) == a0
        iyi = r.returncode == 0 and "NO_OP" in r.stdout and birebir
        return iyi, "rc=%d no_op=%s birebir=%s" % (
            r.returncode, "NO_OP" in r.stdout, birebir)
    finally:
        shutil.rmtree(kok, ignore_errors=True)


VAKALAR = [("C1 rotasyon cifti 1:1", _c1),
           ("C2 acik kalem vetosu", _c2),
           ("C3 bayt ekseni indirme", _c3),
           ("C4 kota kendi olcumu", _c4),
           ("K1 KONTROL tavan alti NO_OP", _k1)]

MUTANTLAR = [
    ("M1 1:1 kolu bozulur (satir uydurulur)", CAPA_M1, YERINE_M1,
     {"C1 rotasyon cifti 1:1"}),
    ("M2 ACIK KALEM vetosu kaldirilir", CAPA_M2, YERINE_M2,
     {"C2 acik kalem vetosu"}),
    ("M3 BAYT kolu no-op edilir", CAPA_M3, YERINE_M3,
     {"C3 bayt ekseni indirme"}),
]


def _mutant(kok, capa, yeni):
    """Mutant kopyayi kur.

    🔴 KARDES MODUL: defter-rotasyon.py acilirken kendi dizinindeki
    `defter-kota-taban.py`'yi yukler. Ciplak temp dizine koyulan mutant
    ACILISTA cokerdi ve TUM vakalar kirmizi yanardi — mutant "her seyi
    oldurdu" gorunur, hedef-kol atfi OLCULEMEZDI. Kardes modul yanina kopyalanir.
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
        print("  %-30s %-8s %s" % (ad, "YESIL" if iyi else "KIRMIZI", detay))
    vaka_gecen = sum(1 for v in vaka.values() if v)

    print()
    print("--- MUTANTLAR (hedef kol atfi: K182) ---")
    olen_say = 0
    atif_say = 0
    for ad, capa, yeni, hedefler in MUTANTLAR:
        kok = tempfile.mkdtemp(prefix="k195c-mut-")
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
        print("  %-40s %s" % (ad, "OLDU" if olenler else "YASADI"))
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
