#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/e2-birim-ikiz-kanit.py — E2 BOYUT ekseni: UC SUTUNLU ikiz KANITI.

UC SUTUN NE OLCER (ilk turda tek-sutunlu kiyas YANLIS EKSENDE kurulmustu —
[[kabul-araligi-karsilastirma-araligi]] — bu ikinci turun duzeltmesidir):
  * **ESKI (tarihsel)** — HEAD'in GERCEK, degismemis eski kurali (bare "marj",
    `\\w*` YOK). Yalniz TARIHSEL olarak GERCEKTEN kirmizi yanan bir vaka icin
    iddia kurulur (ciplak "MARJ" sozcugu); Turkce ek almis bicimlerin ("marji",
    "marjinda") bu kuralda ZATEN yesil oldugu OLCULDU, o yuzden 3.5'teki 4
    yeni-yesil fiksturun cogu icin ESKI=KIRMIZI iddiasi KURULMAZ.
  * **YENI-BIRIMSIZ (karsit olgu, ablasyon)** — YENI konu ekseni (genisletilmis
    `\\bmarj\\w*\\b` + YENI `E2_SAYI` bagimsiz-jeton kurali) AMA BOYUT/birim
    kanit kolu (E2_BIRIM/E2_PARA) KAPATILMIS: konu+miktar varsa DOGRUDAN
    kirmizi (eski yapinin ta kendisi, sadece konu regexi genisletilmis). Bu
    sutun BOYUT ekseninin GERCEK KATKISINI izole eder: bir satir SADECE bagimsiz
    bir MIKTAR JETONU tasiyorsa burada kirmizidir; BOYUT kanidi (birim/para)
    onu ancak YENI (canli) kuralda yesile cevirir. Bir satirda bagimsiz miktar
    HIC yoksa (or. `CTA-A1` icindeki rakam) bu sutun BOYUT eksenine hic
    ULASMADAN zaten yesildir — o satirin yesilligi BOYUT ekseninden degil
    MIKTAR-tokenizasyon ekseninden gelir; iddia buna GORE ayri kurulur.
  * **YENI** — canli `devam-sinif-kapisi.py` kurali (`e2_bulgusu()`).

Kullanim: python3 tools/e2-birim-ikiz-kanit.py
Cikis kodu: 0 = tum iddialar tuttu · 1 = en az biri tutmadi.
"""
import importlib.util
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
KAPI_YOLU = os.path.join(TOOLS, "devam-sinif-kapisi.py")

# --- ESKI KURAL (11 Agu 2026 oncesi, HEAD'in GERCEK degismemis hali) -------
# Yalniz KIYAS icin yeniden kurulur; devam-sinif-kapisi.py artik bu kurali
# TASIMIYOR (uydurma degil — gercek eski davranisin donuk kopyasidir).
E2_ESKI_KONU = re.compile(
    r"\b(iskonto|(?<!guvenlik )marj|kar payi|karpayi|komisyon|alis fiyati|"
    r"alim fiyati|maliyet fiyati|tedarik fiyati|kur farki|doviz kuru)\b")
E2_ESKI_SAYI = re.compile(r"\d")


def eski_hukum(norm):
    """ESKI (tarihsel) kural: konu kelimesi + HERHANGI BIR RAKAM, ikisi de
    normalize edilmis satirda."""
    return bool(E2_ESKI_KONU.search(norm) and E2_ESKI_SAYI.search(norm))


def _modul_yukle():
    spec = importlib.util.spec_from_file_location("pruvo_e2_ikiz_dsk", KAPI_YOLU)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def yeni_birimsiz_hukum(dsk, ham, norm):
    """YENI-BIRIMSIZ (ablasyon): YENI konu ekseni (genisletilmis \\w* + YENI
    bagimsiz-jeton E2_SAYI) ama BOYUT/birim kanit kolu KAPALI — belirsiz konu
    TICARI konu gibi DOGRUDAN kirmizidir, E2_BIRIM/E2_PARA HIC danisilmaz."""
    if not dsk.E2_SAYI.search(ham):
        return False
    if dsk.E2_TICARI_KONU.search(norm):
        return True
    return bool(dsk.E2_BELIRSIZ_KONU.search(dsk.E2_DONMUS.sub(" ", norm)))


# --- 11 Agu'da FIILEN kirmizi yanan tarihsel vaka (ciplak "MARJ") ----------
TARIHSEL_VAKA = "- MARJ NOTU: masaustunde elde kalan pay ~%5 (~7 px)."

# --- tools/paket-e2-birim-ekseni.md 3.5'te eklenen YENI _YESIL fiksturler --
YENI_YESIL_VAKALAR = [
    "- Masaustunde elde kalan marj ~%5 (~7 px); yerlesim toleransi.",
    "- CTA marji 12 px daraldi; esik 250 ms.",
    "- Ege tavan payi 400 karakter marjinda kaldi.",
    "- Genislik marji CTA-A1 ekseninde izlenecek.",
]

# --- tools/paket-e2-birim-ekseni.md 3.4'te eklenen YENI _KIRMIZI fiksturler -
YENI_KIRMIZI_VAKALAR = [
    "- Aracilik marji islem basina 4500 TL; 12 adet uzerinden hesaplandi.",
    "- Anlasilan marj %18 seviyesinde tutuldu.",
    "- MARJ_ORANI=0.22 sabiti panelden okunuyor.",
    "- Iskonto 7 px kadar kucuk gorunse de uygulandi.",
]


def _b(v):
    return "KIRMIZI" if v else "YESIL"


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

    print("%-58s  %-8s  %-12s  %-8s" % ("SATIR", "ESKI", "YENI-BIRIMSIZ", "YENI"))
    print("-" * 92)

    # --- 1) TARIHSEL vaka: ESKI=KIRMIZI, YENI=YESIL (11 Agu'da GERCEKTEN oldu)
    n = normalize(TARIHSEL_VAKA)
    e = eski_hukum(n)
    y = yeni_hukum(TARIHSEL_VAKA)
    satirlar.append((TARIHSEL_VAKA, e, None, y))
    print("%-58s  %-8s  %-12s  %-8s" % (TARIHSEL_VAKA[:56], _b(e), "-", _b(y)))
    if not (e is True and y is False):
        hatalar.append(
            "TARIHSEL VAKA TUTMADI: %r (ESKI=%s YENI=%s, beklenen ESKI=KIRMIZI "
            "YENI=YESIL)" % (TARIHSEL_VAKA, _b(e), _b(y)))

    # --- 2) yeni-YESIL vakalar: YENI=YESIL (hepsi) + BOYUT-ABLASYON kiyasi ---
    for satir in YENI_YESIL_VAKALAR:
        norm = normalize(satir)
        e = eski_hukum(norm)
        b = yeni_birimsiz_hukum(dsk, satir, norm)
        y = yeni_hukum(satir)
        satirlar.append((satir, e, b, y))
        print("%-58s  %-8s  %-12s  %-8s" % (satir[:56], _b(e), _b(b), _b(y)))
        if y is not False:
            hatalar.append("YENI YESIL DEGIL: %r (YENI=%s, beklenen YESIL)"
                           % (satir, _b(y)))
        bagimsiz_miktar_var = bool(dsk.E2_SAYI.search(satir))
        if bagimsiz_miktar_var:
            # Bu satirda bagimsiz bir MIKTAR JETONU var: BOYUT kaniti (birim)
            # kaldirilinca kirmiziya DONMELI — yesilligin KAYNAGI BOYUT ekseni.
            if b is not True:
                hatalar.append(
                    "BOYUT-ABLASYON TUTMADI (miktar var, boyut kanitiyla yesil "
                    "olmustu): %r YENI-BIRIMSIZ=%s (beklenen KIRMIZI)"
                    % (satir, _b(b)))
        else:
            # Bagimsiz miktar YOK: BOYUT ekseni buraya hic ULASMAZ, bu satir
            # BOYUT ekseninden BAGIMSIZ olarak yesildir (MIKTAR-tokenizasyon
            # ekseni sayesinde) — ablasyonla da YESIL kalmasi BEKLENEN sonuctur.
            if b is not False:
                hatalar.append(
                    "BEKLENMEDIK: bagimsiz miktar YOKKEN YENI-BIRIMSIZ kirmizi "
                    "cikti: %r" % satir)

    # --- 3) yeni-KIRMIZI vakalar: YENI=KIRMIZI (fail-closed korundu) --------
    for satir in YENI_KIRMIZI_VAKALAR:
        norm = normalize(satir)
        e = eski_hukum(norm)
        b = yeni_birimsiz_hukum(dsk, satir, norm)
        y = yeni_hukum(satir)
        satirlar.append((satir, e, b, y))
        print("%-58s  %-8s  %-12s  %-8s" % (satir[:56], _b(e), _b(b), _b(y)))
        if y is not True:
            hatalar.append(
                "FAIL-CLOSED BOZULDU (yeni KIRMIZI vaka): %r YENI=%s (beklenen "
                "KIRMIZI)" % (satir, _b(y)))

    print("-" * 92)
    print("vaka sayisi: %d (1 tarihsel + %d yeni-yesil + %d yeni-kirmizi)"
          % (len(satirlar), len(YENI_YESIL_VAKALAR), len(YENI_KIRMIZI_VAKALAR)))
    for h in hatalar:
        print("  x %s" % h, file=sys.stderr)
    print("e2-birim-ikiz-kanit: %d vaka · %d hata" % (len(satirlar), len(hatalar)))
    return 1 if hatalar else 0


if __name__ == "__main__":
    sys.exit(main())
