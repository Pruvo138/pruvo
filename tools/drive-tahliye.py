#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRUVO Drive yerel tahliyesi — TEK supurucu + TAVAN kapisi (sinif onarimi, 7 Eki 2026).

NEDEN: Drive'a yazan ~20 aractan yalniz 5'i yazdigi dosyanin yerel kopyasini geri atiyordu
(evict); digerleri yazip birakiyordu -> `~/Library/CloudStorage` her gun sisiyordu
(Okan: "TEKRARLAYAN KIRMIZI ... 2,5->3,3 GB — kapi yok ya da kablosuz"). Tekil yaziciyi
yamamak 3. tekrardi; bu arac YAZICIDAN BAGIMSIZ calisir: PRUVO kokleri altindaki her
dosyaya bakar, yerelde maddelesmis (blok>0) ve Drive'a yuklenmis olani evict eder.

KURALLAR:
  - Dosya SILINMEZ, TASINMAZ. Yalniz evict (Drive'daki asil dosya yerinde kalir).
  - Yuklenmemis (ya da yukleme durumu OKUNAMAYAN) dosyaya DOKUNULMAZ -> BEKLIYOR.
  - Kokler `drive_yolu`ndan TURETILIR (elle liste YOK): PRUVO Ortak Drive'inin koku
    (`pruvo_dizini()`nin ustu = ".../Ortak Drive'lar/PRUVO"). Drive'im altina yazan PRUVO
    araci YOK (7 Eki olcumu: tools/ altinda CloudStorage yazan 4 dosyanin hepsi Ortak
    Drive'i hedefler) -> Okan'in kisisel Drive'im dizinlerine DOKUNULMAZ.
  - Kok yok / erisilemez -> `OLCULEMEDI` + rc=2 (asla sessiz yesil).

CIKTI (tek satir):
  DRIVE_TAHLIYE yerel_once_mb=<n> yerel_sonra_mb=<n> evict=<n> bekliyor=<n> hata=<n>
                tavan_mb=<T> HUKUM=YESIL|KIRMIZI
  HUKUM=KIRMIZI <=> yerel_sonra > tavan ya da hata>0. rc: YESIL 0 · KIRMIZI 1 · OLCULEMEDI 2.
  `--kuru`: evict YAPILMAZ; `evict` alani "evict edilecek" sayisidir, yerel_sonra=yerel_once.

Test: tools/drive-tahliye-test.py (sahte kok + enjekte yukleme/evict; gercek Drive'a dokunmaz).
"""
import argparse
import os
import sys

TAVAN_MB = 500
EVICT_DENEME = 3
_MB = 1024 * 1024
_ARAC_DIZIN = os.path.dirname(os.path.abspath(__file__))


def _drive_modul(ad):
    """drive_yolu / drive_birak TEMBEL yuklenir: enjekte test kopyasi kardes dosyasiz kosar."""
    if _ARAC_DIZIN not in sys.path:
        sys.path.insert(0, _ARAC_DIZIN)
    return __import__(ad)


def kokleri_turet():
    """PRUVO kokleri: [".../Ortak Drive'lar/PRUVO"] ya da [] (mount yok)."""
    pruvo = _drive_modul("drive_yolu").pruvo_dizini(sessiz=True)   # .../PRUVO/Pruvo
    if not pruvo:
        return []
    return [os.path.dirname(pruvo)]


def tara(kokler):
    """[(yol, yerel_bayt)] — yalniz duzenli dosyalar (symlink izlenmez). Erisim hatasi -> OSError."""
    dosyalar = []
    for kok in kokler:
        for dizin, _, adlar in os.walk(kok):
            for ad in adlar:
                yol = os.path.join(dizin, ad)
                try:
                    st = os.lstat(yol)
                except OSError:
                    continue
                if not os.path.isfile(yol) or os.path.islink(yol):
                    continue
                dosyalar.append((yol, st.st_blocks * 512))
    return dosyalar


def _yerel_toplam(yollar):
    t = 0
    for y in yollar:
        try:
            t += os.lstat(y).st_blocks * 512
        except OSError:
            pass
    return t


def calistir(kokler, tavan_mb=TAVAN_MB, kuru=False, yuklendi_fn=None, evict_fn=None,
             deneme=EVICT_DENEME):
    """Doner: (satir, rc). `yuklendi_fn`/`evict_fn` TOPLU imzalidir: list[yol] -> list[sonuc]."""
    if not kokler or not all(os.path.isdir(k) and os.access(k, os.R_OK | os.X_OK) for k in kokler):
        return ("DRIVE_TAHLIYE OLCULEMEDI kok_yok_ya_da_erisilemez tavan_mb=%d HUKUM=OLCULEMEDI"
                % tavan_mb, 2)
    if yuklendi_fn is None:
        yuklendi_fn = _drive_modul("drive_birak").yuklendi_toplu
    if evict_fn is None:
        evict_fn = _drive_modul("drive_birak").evict_toplu

    dosyalar = tara(kokler)
    once = sum(b for _, b in dosyalar)
    adaylar = [y for y, b in dosyalar if b > 0]
    durum = list(yuklendi_fn(adaylar)) if adaylar else []
    if len(durum) != len(adaylar):
        durum = [None] * len(adaylar)
    yuklu = [y for y, d in zip(adaylar, durum) if d is True]
    bekliyor = len(adaylar) - len(yuklu)

    evict_n = hata = 0
    if kuru:
        evict_n = len(yuklu)
        sonra = once
    else:
        kalan = yuklu
        for _ in range(deneme):
            if not kalan:
                break
            sonuc = list(evict_fn(kalan))
            if len(sonuc) != len(kalan):
                sonuc = [False] * len(kalan)
            evict_n += sum(1 for s in sonuc if s)
            kalan = [y for y, s in zip(kalan, sonuc) if not s]
        hata = len(kalan)
        sonra = _yerel_toplam([y for y, _ in dosyalar])

    kirmizi = sonra > tavan_mb * _MB or hata > 0
    satir = ("DRIVE_TAHLIYE yerel_once_mb=%d yerel_sonra_mb=%d evict=%d bekliyor=%d hata=%d "
             "tavan_mb=%d HUKUM=%s" % (round(once / _MB), round(sonra / _MB), evict_n, bekliyor,
                                       hata, tavan_mb, "KIRMIZI" if kirmizi else "YESIL"))
    return satir, (1 if kirmizi else 0)


def main(argv=None):
    ap = argparse.ArgumentParser(description="PRUVO Drive yerel tahliyesi (yalniz evict, SILME YOK)")
    ap.add_argument("--kuru", action="store_true", help="evict yapmadan say")
    ap.add_argument("--tavan-mb", type=int, default=TAVAN_MB)
    a = ap.parse_args(argv)
    try:
        satir, rc = calistir(kokleri_turet(), tavan_mb=a.tavan_mb, kuru=a.kuru)
    except Exception as e:                                          # noqa: BLE001
        satir, rc = ("DRIVE_TAHLIYE OLCULEMEDI %s:%s tavan_mb=%d HUKUM=OLCULEMEDI"
                     % (type(e).__name__, str(e)[:80].replace(" ", "_"), a.tavan_mb), 2)
    print(satir)
    return rc


if __name__ == "__main__":
    sys.exit(main())
