#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — K63: cok kelimeli marka korlugu + kesif kova taksonomisi.

OLCULEN KUSUR (12 Agu 2026): `makerworld-ara.marka_geciyor()` marka terimini TEK PARCA
olarak derliyordu. Marka adi iki kelimeliyse platformdaki yaygin yazimlar (AlfaRomeo,
Alfa-Romeo, alfa_romeo; Mercedes-Benz <-> Mercedes Benz) TAM KELIME sayilmayip
`elenen_marka` kovasina dusuyordu. Etkilenen markalar: Land Rover · Aston Martin ·
Mercedes-Benz · Alfa Romeo.

IKI EKSEN AYRI AYRI OLCULUR (genisletme gurultu getirebilir — tek eksen yeterli DEGIL):
  POZITIF : eskiden SESSIZCE elenen, marka adini ayrac farkiyla tasiyan kayitlar GECMELI.
  NEGATIF : genisletmenin ACMAMASI gereken kapilar KAPALI kalmali (alt-dize gurultusu,
            tek marka kelimesi, Turkce I/ı ayrimi, tek kelimeli markada davranis SABIT).
Ucuncu eksen KOVA: `elenen_marka` "gorulen" SAYILMAZ (birinci kusurun telafi yolu).

Kirmizi iddialar AILE IZI ile basilir (mutasyon kabulu `rc` ile DEGIL izle yapilir):
POZITIF · NEGATIF · KOVA · SABIT.

Kosum: python3 tools/marka-cok-kelime-test.py
Cikis: 0 = tum eksenler yesil · 1 = en az bir eksen kirmizi.
"""
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "makerworld_ara", os.path.join(_HERE, "makerworld-ara.py"))
ara = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ara)

# --- POZITIF: kusur onarilmadan HEPSI kirmiziydi (marka ayrac farkiyla yaziliyor) ----
# (marka, metinler, aciklama)
POZITIF = [
    ("alfa romeo", ("AlfaRomeo Giulia badge holder",), "bitisik yazim"),
    ("alfa romeo", ("Alfa-Romeo 156 vent clip",), "tireli yazim"),
    ("alfa romeo", ("alfa_romeo 147 hub cap",), "alt cizgili yazim"),
    ("alfa romeo", ("AFGiuliaFull", "alfaromeo giulia", "afgiuliafull"),
     "baslik kisaltma; ETIKET bitisik marka tasiyor (canli olcumde kurtarildi)"),
    ("land rover", ("Landrover Defender D90 light bracket",), "bitisik yazim"),
    ("land rover", ("LAND-ROVER roof rail cap",), "buyuk harf + tire"),
    ("aston martin", ("AstonMartin DB9 grille clip",), "bitisik yazim"),
    ("mercedes-benz", ("Mercedes Benz W124 hood clip",), "marka TIRELI, metin BOSLUKLU"),
    ("mercedes benz", ("MercedesBenz Sprinter cup holder",), "marka BOSLUKLU, metin BITISIK"),
    ("mercedes benz", ("kapak", "mercedes-benz w203", "some-slug"), "etikette tireli"),
]

# --- NEGATIF: genisletme bu kapilari ACMAMALI ---------------------------------------
NEGATIF = [
    ("ford", ("Oxford pencil holder",), "alt-dize (Ox+ford)"),
    ("ford", ("Things you can afford to print",), "alt-dize (af+ford)"),
    ("mini", ("aluminium bracket",), "alt-dize (alu+mini+um)"),
    ("audi", ("audiophile speaker stand",), "alt-dize (audi+ophile)"),
    ("alfa romeo", ("Romeo and Juliet bust",), "markanin TEK kelimesi yetmez"),
    ("alfa romeo", ("Alfa Laval plate cover",), "ilk kelime baska markanin parcasi"),
    ("land rover", ("Land Cruiser 70 series snorkel",), "Land + baska model (Toyota)"),
    ("aston martin", ("Martin guitar neck rest",), "yalniz ikinci kelime (baska alan)"),
    ("alfa romeo", ("alfaromeoo giulia",), "kelime siniri: sondaki fazla harf"),
    ("alfa romeo", ("xalfaromeo giulia",), "kelime siniri: bastaki fazla harf"),
    ("alfa romeo", ("Alfa 156 ve ayri yerde Romeo yazisi",), "kelimeler BITISIK degil"),
    ("kisa", ("kısa kollu kutu",), "Turkce I/ı ayrimi korunuyor"),
    ("", ("herhangi bir metin",), "bos marka -> daima False"),
    # 🔴 KAPANMAYAN SINIR, BILEREK NEGATIF: yalniz MODEL adi tasiyan baslikta marka
    # dizesi metinde HIC YOKTUR; hicbir metin kurali yakalayamaz. Canli olcum: "alfa
    # romeo" sorgusunun 143 sonucunun 118'i hicbir marka kelimesi tasimiyor (Citroën,
    # Skoda, Bugatti...) -> filtreyi buraya kadar acmak %82,5 gurultu demek. Telafi
    # yolu MODEL TERIMLI yeniden taramadir; kapisi asagidaki KOVA eksenidir.
    ("alfa romeo", ("Giulia grill keychain",), "model-adi-yalniz: metin kuraliyla KURTARILAMAZ"),
]

# --- SABIT: tek kelimeli markada davranis DEGISMEDI (regresyon nobeti) --------------
# 🔴 SON UC FIKSTUR: tek kelimeli markada ayrac gevsemesi HARF ARASINA sizmamali.
# Olculdu (mutasyon K63-M7): desen govdesi harf harf bolunurse "f.o.r.d" tek kelimeli
# "ford" markasiyla eslesir; ustteki dort satir bu mutanti YAKALAMIYORDU.
SABIT = [
    ("ford", ("Ford Mustang wheel cap",), True),
    ("ford", ("grille for FORD Focus MK2",), True),
    ("nissan", ("NISSAN GTR spoiler",), True),
    ("opel", ("Please open the box lid",), False),
    ("ford", ("Bradford city keychain",), False),
    ("mini", ("Mini Cooper badge holder",), True),
    ("ford", ("f.o.r.d printing guide",), False),
    ("mini", ("m-i-n-i cooper decal",), False),
    ("audi", ("a u d i letters",), False),
]


def _iz(aile, mesaj):
    print("  🔴 IZ=%s %s" % (aile, mesaj))


def main():
    iddia, kirmizi = 0, 0
    poz_gecen, neg_gecen = 0, 0

    print("-- POZITIF ekseni (ayrac farkli yazim GECMELI)")
    for marka, metinler, aciklama in POZITIF:
        iddia += 1
        got = ara.marka_geciyor(marka, *metinler)
        if got:
            poz_gecen += 1
            print("  ok   %-14s %-42s # %s" % (marka, str(metinler)[:40], aciklama))
        else:
            kirmizi += 1
            _iz("POZITIF", "%s ~ %r elendi (gecmeliydi) # %s"
                % (marka, metinler[0][:44], aciklama))

    print("-- NEGATIF ekseni (genisletme bu kapilari ACMAMALI)")
    for marka, metinler, aciklama in NEGATIF:
        iddia += 1
        got = ara.marka_geciyor(marka, *metinler)
        if not got:
            neg_gecen += 1
            print("  ok   %-14s %-42s # %s" % (marka, str(metinler)[:40], aciklama))
        else:
            kirmizi += 1
            _iz("NEGATIF", "%s ~ %r GECTI (elenmeliydi) # %s"
                % (marka, metinler[0][:44], aciklama))

    print("-- SABIT ekseni (tek kelimeli markada davranis degismedi)")
    for marka, metinler, bekle in SABIT:
        iddia += 1
        got = ara.marka_geciyor(marka, *metinler)
        if got != bekle:
            kirmizi += 1
            _iz("SABIT", "%s ~ %r -> %s (beklenen %s)" % (marka, metinler[0][:44], got, bekle))

    print("-- KOVA ekseni (elenen_marka 'gorulen' SAYILMAZ)")
    havuz = {"adaylar": [("1", "a")], "elenen_cop": [("2", "b")],
             "elenen_nc": [("3", "x", "c")], "elenen_marka": [("4", "d"), ("5", "e")],
             "zaten_ekli": ["6"]}

    iddia += 1
    try:
        gorulen = ara.gorulen_idler(havuz)
    except Exception as hata:
        gorulen = None
        kirmizi += 1
        _iz("KOVA", "gorulen_idler cagrilamadi -> %r" % (hata,))
    if gorulen is not None:
        if gorulen != {"1", "2", "3", "6"}:
            kirmizi += 1
            _iz("KOVA", "gorulen kume yanlis: %r" % (sorted(gorulen),))

    iddia += 1
    if gorulen is not None and ({"4", "5"} & gorulen):
        kirmizi += 1
        _iz("KOVA", "elenen_marka ID'leri 'gorulen' sayildi -> model-terimli telafi KOR")

    iddia += 1
    try:
        if ara.kararsiz_idler(havuz) != {"4", "5"}:
            kirmizi += 1
            _iz("KOVA", "kararsiz kume yanlis: %r" % (sorted(ara.kararsiz_idler(havuz)),))
    except Exception as hata:
        kirmizi += 1
        _iz("KOVA", "kararsiz_idler cagrilamadi -> %r" % (hata,))

    iddia += 1
    if set(ara.HUKUMLU_KOVALAR) & set(ara.KARARSIZ_KOVALAR):
        kirmizi += 1
        _iz("KOVA", "kova siniflari AYRIK degil (bir kova iki sinifta)")

    iddia += 1
    try:
        ara.gorulen_idler(dict(havuz, yeni_kova=[("9", "z")]))
        kirmizi += 1
        _iz("KOVA", "taniinmayan kova SESSIZCE yutuldu (fail-open)")
    except ara.BilinmeyenKova:
        pass
    except Exception as hata:
        kirmizi += 1
        _iz("KOVA", "taniinmayan kovada yanlis istisna -> %r" % (hata,))

    print()
    print("K63_POZITIF=%d/%d K63_NEGATIF=%d/%d"
          % (poz_gecen, len(POZITIF), neg_gecen, len(NEGATIF)))
    if kirmizi:
        print("BASARISIZ: %d/%d iddia kirmizi" % (kirmizi, iddia))
        return 1
    print("TUM TESTLER GECTI (%d iddia)." % iddia)
    return 0


if __name__ == "__main__":
    sys.exit(main())
