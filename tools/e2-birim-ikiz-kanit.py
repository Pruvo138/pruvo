#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/e2-birim-ikiz-kanit.py — E2 BOYUT ekseni: ONCE-KIRMIZI/SONRA-YESIL
(ve tersi) ikiz KANITI.

tools/devam-sinif-kapisi.py MODUL olarak yuklenir (importlib, gercek YENI
E2 kuralini tasir: `e2_bulgusu()`). ESKI kural (11 Agu 2026 oncesi — "konu
kelimesi + HERHANGI BIR RAKAM") burada YALNIZ KIYAS icin yerel olarak
YENIDEN KURULUR — devam-sinif-kapisi.py artik bu kurali TASIMIYOR, ikinci
bir CANLI kopyasi olsaydi [[ikiz-tanim-sessiz-ayrisma]] sinifi olurdu; burada
bilerek DONUK (donmus) bir TARIHSEL kiyas sabiti olarak durur.

tools/paket-e2-birim-ekseni.md 3.4/3.5'te eklenen HER yeni fikstur icin
(ESKI hukum, YENI hukum) ciftini basar ve iki iddiayi yargilar:
  * yeni YESIL vakalarin HEPSI  : ESKI=KIRMIZI, YENI=YESIL (yanlis-pozitif kapandi)
  * yeni KIRMIZI vakalarin HEPSI: YENI=KIRMIZI             (fail-closed korundu)

Kullanim: python3 tools/e2-birim-ikiz-kanit.py
Cikis kodu: 0 = tum iddialar tuttu · 1 = en az biri tutmadi.
"""
import importlib.util
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
KAPI_YOLU = os.path.join(TOOLS, "devam-sinif-kapisi.py")

# --- ESKI KURAL (11 Agu 2026 oncesi) — YALNIZ KIYAS icin yeniden kurulur ---
# Birebir devam-sinif-kapisi.py'nin ESKI (bu paketten ONCEKI) E2_KONU/E2_SAYI
# ciftidir. Uydurma degil: gercek eski davranisin donuk kopyasidir.
E2_ESKI_KONU = re.compile(
    r"\b(iskonto|(?<!guvenlik )marj|kar payi|karpayi|komisyon|alis fiyati|"
    r"alim fiyati|maliyet fiyati|tedarik fiyati|kur farki|doviz kuru)\b")
E2_ESKI_SAYI = re.compile(r"\d")


def eski_hukum(norm):
    """ESKI kural: konu kelimesi + HERHANGI BIR RAKAM, IKISI DE normalize
    edilmis satirda."""
    return bool(E2_ESKI_KONU.search(norm) and E2_ESKI_SAYI.search(norm))


def _modul_yukle():
    spec = importlib.util.spec_from_file_location("pruvo_e2_ikiz_dsk", KAPI_YOLU)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- tools/paket-e2-birim-ekseni.md 3.5'te eklenen YENI _YESIL fiksturler ---
# Beklenen: ESKI=KIRMIZI (yanlis-pozitif ONCE vardi), YENI=YESIL (sonra kapandi).
YENI_YESIL_VAKALAR = [
    "- Masaustunde elde kalan marj ~%5 (~7 px); yerlesim toleransi.",
    "- CTA marji 12 px daraldi; esik 250 ms.",
    "- Ege tavan payi 400 karakter marjinda kaldi.",
    "- Genislik marji CTA-A1 ekseninde izlenecek.",
]

# --- tools/paket-e2-birim-ekseni.md 3.4'te eklenen YENI _KIRMIZI fiksturler ---
# Beklenen: YENI=KIRMIZI (fail-closed korundu). ESKI degeri BILGI icin basilir
# ama iddia ONA BAGLI DEGILDIR (bkz. asagidaki RAPOR notu — bazilari ESKI
# kuralda da zaten kirmiziydi, biri ESKI kuralin KENDI kor noktasini gosterir).
YENI_KIRMIZI_VAKALAR = [
    "- Aracilik marji islem basina 4500 TL; 12 adet uzerinden hesaplandi.",
    "- Anlasilan marj %18 seviyesinde tutuldu.",
    "- MARJ_ORANI=0.22 sabiti panelden okunuyor.",
    "- Iskonto 7 px kadar kucuk gorunse de uygulandi.",
]


def main():
    dsk = _modul_yukle()
    ozet, hata = dsk.ozet_modulu()
    if ozet is None:
        print("OLCULEMEDI: ozet modulu yuklenemedi: %s" % hata, file=sys.stderr)
        return 1
    normalize = ozet.normalize

    def yeni_hukum(ham):
        return dsk.e2_bulgusu(ham, normalize(ham)) is not None

    hatalar = []
    satirlar = []

    print("%-68s  %-8s  %-8s" % ("SATIR", "ESKI", "YENI"))
    print("-" * 90)

    for satir in YENI_YESIL_VAKALAR:
        e = eski_hukum(normalize(satir))
        y = yeni_hukum(satir)
        satirlar.append((satir, e, y))
        print("%-68s  %-8s  %-8s" % (satir[:66], "KIRMIZI" if e else "YESIL",
                                     "KIRMIZI" if y else "YESIL"))
        if not (e is True and y is False):
            hatalar.append(
                "YANLIS-POZITIF KAPANMADI (yeni YESIL vaka): %r (ESKI=%s YENI=%s, "
                "beklenen ESKI=KIRMIZI YENI=YESIL)"
                % (satir, "KIRMIZI" if e else "YESIL", "KIRMIZI" if y else "YESIL"))

    for satir in YENI_KIRMIZI_VAKALAR:
        e = eski_hukum(normalize(satir))
        y = yeni_hukum(satir)
        satirlar.append((satir, e, y))
        print("%-68s  %-8s  %-8s" % (satir[:66], "KIRMIZI" if e else "YESIL",
                                     "KIRMIZI" if y else "YESIL"))
        if y is not True:
            hatalar.append(
                "FAIL-CLOSED BOZULDU (yeni KIRMIZI vaka): %r YENI=YESIL oldu "
                "(beklenen KIRMIZI)" % satir)

    print("-" * 90)
    print("vaka sayisi: %d (yeni-yesil-iddia %d + yeni-kirmizi-iddia %d)"
          % (len(satirlar), len(YENI_YESIL_VAKALAR), len(YENI_KIRMIZI_VAKALAR)))
    for h in hatalar:
        print("  x %s" % h, file=sys.stderr)
    print("e2-birim-ikiz-kanit: %d vaka · %d hata" % (len(satirlar), len(hatalar)))
    return 1 if hatalar else 0


if __name__ == "__main__":
    sys.exit(main())
