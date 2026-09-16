#!/usr/bin/env python3
"""NOBET TETIGI CURUTUCUSU — spec N1 §2'nin UC hedefli mutanti.

K182: bir mutantin OLMESI yetmez; HANGI VAKANIN oldurdugu de olculur. Mutant
hedefiyle ilgisiz bir vakada oluyorsa (tautoloji / ad golgesi) kol OLCULMEMISTIR.
Bu yuzden her mutantin BEKLENEN ilk-olen vakasi capalidir:

  MA kosul kolu kalkar  (yesil de tur acar)     -> A1  (YESIL GUN SIFIR TUR)
  MB kilit kalkar       (ayni run-id 2. tur)    -> B3  (KIRMIZI TEK TUR)
  MC bayatlik kolu kalkar (olu gozcu sessiz)    -> D1  (FAIL-LOUD)

`MUTANT=3/3 IDDIA=3 ISTASYON=0 ATIF_SAPTI=0 YAMA_TUTMADI=0 KONTROL=YESIL` beklenir.
Istisna ile olum KABUL DEGILDIR (ISTASYON) — mutant kolu degil yuklemeyi kirmistir.
"""

import os
import shutil
import sys
import types

KOK = os.path.dirname(os.path.abspath(__file__))
TETIK_YOLU = os.path.join(KOK, "nobet-tetik.py")
TEST_YOLU = os.path.join(KOK, "nobet-tetik-test.py")

# (ad, hedef, yeni, beklenen_ilk_olen_vaka). Capa kaynakta TAM 1 kez gecmeli.
MUTANTLAR = [
    ("MA kosul kolu kalkar: yesil gun de tur acar",
     '    # 7. Yesil: tur ACILMAZ.\n'
     '    return Karar("ACMA", "YESIL", "", (), False)',
     '    # 7. Yesil: tur ACILMAZ.\n'
     '    return Karar("AC", "YESIL", "gunluk:%s" % bugun, ("--tur",), False)',
     "A1"),
    ("MB kilit kalkar: ayni run-id ikinci tur acar",
     "    except FileExistsError:\n        return False\n    except OSError:\n        return False",
     "    except FileExistsError:\n        return True\n    except OSError:\n        return False",
     "B3"),
    ("MC bayatlik kolu kalkar: olu gozcu SESSIZ",
     "    if GZ.kalp_bayat_mi(kalp, simdi, tavan):\n"
     '        return Karar("AC", "KALP_BAYAT", "gunluk:%s" % bugun, ("--tur",), True)',
     "    if False:\n"
     '        return Karar("AC", "KALP_BAYAT", "gunluk:%s" % bugun, ("--tur",), True)',
     "D1"),
]


def _test_modulu():
    import importlib.util
    spec = importlib.util.spec_from_file_location("nobet_tetik_test", TEST_YOLU)
    modul = importlib.util.module_from_spec(spec)
    onceki = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(modul)
    finally:
        sys.dont_write_bytecode = onceki
    return modul


def _bellekte_kur(kaynak, ad, kaynak_yolu):
    modul = types.ModuleType(ad)
    modul.__file__ = kaynak_yolu
    exec(compile(kaynak, kaynak_yolu, "exec"), modul.__dict__)
    return modul


def _pycache_temizle():
    yol = os.path.join(KOK, "__pycache__")
    if os.path.isdir(yol):
        shutil.rmtree(yol, ignore_errors=True)


def _ilk_hata_vakasi(sonuc):
    if not sonuc.hatalar:
        return "?"
    ilk = sonuc.hatalar[0]
    return ilk.split(":", 1)[0].split()[0] if ilk else "?"


def main():
    with open(TETIK_YOLU, encoding="utf-8") as dosya:
        kaynak = dosya.read()
    test = _test_modulu()

    kontrol = test.kos(_bellekte_kur(kaynak, "tetik_kontrol", TETIK_YOLU))
    if kontrol.gecen != kontrol.toplam:
        for hata in kontrol.hatalar:
            print("KONTROL KIRIK " + hata)
        print("KONTROL=KIRMIZI GECEN=%d/%d" % (kontrol.gecen, kontrol.toplam))
        _pycache_temizle()
        return 2
    print("KONTROL=YESIL GECEN=%d/%d" % (kontrol.gecen, kontrol.toplam))

    sayac = {"IDDIA": 0, "ISTASYON": 0, "ATIF_SAPTI": 0, "YAMA_TUTMADI": 0}
    eslesme = {}
    for sira, (ad, hedef, yeni, beklenen) in enumerate(MUTANTLAR, 1):
        adet = kaynak.count(hedef)
        if adet != 1:
            print("%-52s YAMA_TUTMADI (kaynakta %d kez)" % (ad, adet))
            sayac["YAMA_TUTMADI"] += 1
            continue
        mutant_kaynak = kaynak.replace(hedef, yeni)
        try:
            mutant = _bellekte_kur(mutant_kaynak, "tetik_mutant_%d" % sira, TETIK_YOLU)
            sonuc = test.kos(mutant)
        except BaseException as hata:
            sayac["ISTASYON"] += 1
            print("%-52s OLDU ISTISNA=%s (KOL OLCULMEDI)" % (ad, type(hata).__name__))
            continue
        if sonuc.gecen == sonuc.toplam:
            print("%-52s HAYATTA GECEN=%d/%d" % (ad, sonuc.gecen, sonuc.toplam))
            continue
        vaka = _ilk_hata_vakasi(sonuc)
        eslesme[ad.split()[0]] = vaka
        sayac["IDDIA"] += 1
        if vaka != beklenen:
            sayac["ATIF_SAPTI"] += 1
            print("%-52s OLDU ama ATIF SAPTI vaka=%s beklenen=%s" % (ad, vaka, beklenen))
        else:
            print("%-52s OLDU GECEN=%d/%d vaka=%s" % (ad, sonuc.gecen, sonuc.toplam, vaka))

    _pycache_temizle()
    print()
    print("OLUM_ESLESMESI: " + (" ".join("%s=%s" % (k, v) for k, v in eslesme.items())
                                or "YOK"))
    print("MUTANT=%d/%d IDDIA=%d ISTASYON=%d ATIF_SAPTI=%d YAMA_TUTMADI=%d KONTROL=YESIL" % (
        len(MUTANTLAR) - sayac["YAMA_TUTMADI"], len(MUTANTLAR), sayac["IDDIA"],
        sayac["ISTASYON"], sayac["ATIF_SAPTI"], sayac["YAMA_TUTMADI"]))
    kapi = (sayac["IDDIA"] == len(MUTANTLAR) and sayac["ISTASYON"] == 0
            and sayac["ATIF_SAPTI"] == 0 and sayac["YAMA_TUTMADI"] == 0)
    return 0 if kapi else 1


if __name__ == "__main__":
    sys.exit(main())
