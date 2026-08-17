#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ozet kart tel sozlesmesi: ana kapinin kapsamadigi uc eksen.

AST alt-kume kapısı BURADA DEĞİL, `tools/ozet-alan-ikiz-test.py`'de; ikiz ölçüm yazma.
Bu dosya yalniz uctan uca tel kayipsizligini, Kol A davranisini ve istemci ikiz
sabitini olcer. `--mutasyon` diske yazmadan iki mutantin da olmesini bekler.
"""
# AST alt-küme kapısı BURADA DEĞİL, `tools/ozet-alan-ikiz-test.py`'de; ikiz ölçüm yazma.
import importlib.util
import os
import re
import sys

sys.dont_write_bytecode = True

EV = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_PY = os.path.join(EV, "tools", "build.py")
INDEX_HTML = os.path.join(EV, "index.html")
TOOLS = os.path.join(EV, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import build  # noqa: E402


def _sentetik_urun():
    """Aradaki kosullu alanlari bilerek tasimayan sentetik urun."""
    return {
        "id": "k165-sentetik-boy",
        "kategori": "Otomobil",
        "marka": ["K165"],
        "baslik": "Sentetik boy secenegi karti",
        "aciklama": "Yalnizca K165 kabul fiksturu; gercek urun degildir.",
        "fiyat": "100 TL",
        "gorseller": ["https://media.pruvo3d.com/urunler/k165-sentetik.jpg"],
        "boy_secenekleri": [
            {"etiket": "Uzun", "fark_tl": 100},
            {"etiket": "Kisa", "fark_tl": 0},
        ],
    }


def _vaka_1_uctan_uca(modul=None):
    """kart_ozeti -> tel -> kart dongusu kayipsiz ve delikleri koruyor mu?"""
    m = modul or build
    kart = m.kart_ozeti(_sentetik_urun())
    tel = m.ozet_karti_sikistir(kart, m.OZET_GORSEL_ONEK)
    geri = m.ozet_karti_ac(tel, m.OZET_KART_ALANLARI, m.OZET_GORSEL_ONEK)

    if len(tel) <= 12:
        raise SystemExit(
            "VAKA 1 DUSTU: tel[12] yok; boy_secenekleri konumu kayboldu."
        )
    if tel[12] != kart["boy_secenekleri"]:
        raise SystemExit(
            "VAKA 1 DUSTU: tel[12]=%r, kart boy_secenekleri=%r; deger birebir degil."
            % (tel[12], kart["boy_secenekleri"])
        )
    delikler = tel[8:12]
    if delikler != [None, None, None, None]:
        raise SystemExit(
            "VAKA 1 DUSTU: aradaki None delikleri korunmadi: %r" % (delikler,)
        )
    if geri != kart:
        raise SystemExit(
            "VAKA 1 DUSTU: geri acilan kart kart_ozeti ciktisina dict-esit degil: %r"
            % (sorted(set(geri.items()) ^ set(kart.items())),)
        )
    print(
        "VAKA 1 GECTI: tel[12] boy_secenekleri birebir, None delikleri korunuyor, "
        "geri kart dict-esit"
    )


def _capa_fiksturu(modul=None):
    """Tum tel konumlari tutarli + tek tel-disi kart anahtari."""
    m = modul or build
    kart = {
        "id": "k165-kol-a",
        "baslik": "Kol A sentetik",
        "kategori": "Otomobil",
        "marka": ["K165"],
        "fiyat": "100 TL",
        "gorsel": "https://media.pruvo3d.com/urunler/kol-a.jpg",
        "parametrik": False,
        "aciklama": "Kol A kabul fiksturu",
        "eski_fiyat": "120 TL",
        "tur": "fiziksel",
        "tavsiyeFilament": "ASA",
        "konfigur": "sabit",
        "boy_secenekleri": [{"etiket": "S", "fark_tl": 0}],
        "__sizinti": "tel-disi",
    }
    tel = [kart.get(alan) for alan in m.OZET_KART_ALANLARI]
    gorsel = m.OZET_KART_ALANLARI.index("gorsel")
    tel[gorsel] = tel[gorsel][len(m.OZET_GORSEL_ONEK):]
    return m, kart, tel


def _capa_mesaji_kaynakta_var():
    """Kol A iddiasini main'deki gercek metne bagla; ezberlenmis KAYIP yok."""
    with open(BUILD_PY, encoding="utf-8") as dosya:
        kaynak = dosya.read()
    if "IKIZ TANIM" not in kaynak:
        raise SystemExit("VAKA 2 DUSTU: build.py Kol A mesajinda `IKIZ TANIM` yok.")
    if "OZET_KART_ALANLARI'nda YOK" not in kaynak:
        raise SystemExit(
            "VAKA 2 DUSTU: build.py Kol A mesajinda alan-sozlugu reddi yok."
        )
    if "deger tele HIC cikmaz (IKIZ " not in kaynak:
        raise SystemExit(
            "VAKA 2 DUSTU: build.py Kol A mesajinin gercek govdesi ayristi."
        )


def _vaka_2_kol_a_capasi(modul=None):
    """Tutarlı teldeki tek fazlalik `__sizinti` icin SystemExit bekle."""
    _capa_mesaji_kaynakta_var()
    m, kart, tel = _capa_fiksturu(modul)
    try:
        m._temsil_konum_capasi(
            [tel], [kart], m.OZET_KART_ALANLARI, m.OZET_GORSEL_ONEK, "k165-kol-a"
        )
    except SystemExit as hata:
        mesaj = str(hata)
        if "__sizinti" not in mesaj or "IKIZ TANIM" not in mesaj:
            raise SystemExit(
                "VAKA 2 DUSTU: Kol A reddetti ama main'in gercek IKIZ TANIM mesajini "
                "tasimiyor: %r" % mesaj
            )
        print("VAKA 2 GECTI: Kol A `__sizinti` fazlasini IKIZ TANIM mesaji ile reddetti.")
        return
    raise SystemExit(
        "VAKA 2 DUSTU: çapa yuttu — Kol A `__sizinti` fazlasini reddetmedi."
    )


def _ozet_ac_govdesi(kaynak):
    eslesme = re.search(r"function\s+ozetAc\s*\([^)]*\)\s*\{", kaynak)
    if not eslesme:
        raise SystemExit("VAKA 3 DUSTU: index.html icinde `function ozetAc(...)` yok.")
    baslangic = eslesme.end() - 1
    derinlik = 0
    son = None
    for konum in range(baslangic, len(kaynak)):
        if kaynak[konum] == "{":
            derinlik += 1
        elif kaynak[konum] == "}":
            derinlik -= 1
            if derinlik == 0:
                son = konum
                break
    if son is None:
        raise SystemExit("VAKA 3 DUSTU: ozetAc govdesi dengeli parantezle kapanmiyor.")
    return kaynak[baslangic:son + 1]


def _vaka_3_ikiz_sabit():
    """Canli istemci ikizi: ozetAc icindeki i < N tek deger olarak 8 olmali."""
    with open(INDEX_HTML, encoding="utf-8") as dosya:
        govde = _ozet_ac_govdesi(dosya.read())
    eslesmeler = re.findall(r"i\s*<\s*(\d+)", govde)
    sabitler = sorted({int(deger) for deger in eslesmeler})
    if sabitler != [8]:
        raise SystemExit(
            "VAKA 3 DUSTU: ozetAc icindeki `i < N` sabitleri %r; beklenen tek deger [8]."
            % sabitler
        )
    print("VAKA 3 GECTI: ozetAc icindeki `i < N` tek deger=8.")


class _BellekMutasyonu:
    """Kaynak metnini bellekte degistirip ayri Python modulu yukler."""

    def __init__(self, yol, ad, degisimler):
        self.yol = yol
        self.ad = ad
        self.degisimler = degisimler

    def yukle(self):
        with open(self.yol, encoding="utf-8") as dosya:
            kaynak = dosya.read()
        mutasyonlu = kaynak
        for eski, yeni in self.degisimler:
            sayi = mutasyonlu.count(eski)
            if sayi != 1:
                return None, None, (
                    "mutasyon uygulanamadi: %d eslesme (beklenen 1): %r"
                    % (sayi, eski[:80])
                )
            mutasyonlu = mutasyonlu.replace(eski, yeni, 1)
        tanim = importlib.util.spec_from_loader(self.ad, loader=None)
        modul = importlib.util.module_from_spec(tanim)
        modul.__dict__["__file__"] = self.yol
        try:
            exec(compile(mutasyonlu, self.yol, "exec"), modul.__dict__)
        except Exception as hata:
            return None, mutasyonlu, "mutant modul yuklenemedi: %r" % (hata,)
        return modul, mutasyonlu, None


def _m1():
    """M1: boy_secenekleri alanini sozlukten dusur."""
    eski = '"tavsiyeFilament", "konfigur", "boy_secenekleri")'
    yeni = '"tavsiyeFilament", "konfigur")'
    modul, _kaynak, hata = _BellekMutasyonu(
        BUILD_PY, "build_k165_m1", [(eski, yeni)]
    ).yukle()
    if hata:
        return False, "KABLO_KOPUK: %s" % hata
    try:
        _vaka_1_uctan_uca(modul)
    except SystemExit as sonuc:
        return True, "VAKA 1 DUSTU: %s" % sonuc
    return False, "M1 hayatta; Vaka 1 boy_secenekleri kaybini yakalayamadi."


def _m2():
    """M2: Kol A fazla anahtar denetimini bellek icinde kaldir."""
    eski = "        fazla = [a for a in kart if a not in alanlar]\n        if fazla:\n"
    yeni = "        if False:  # M2 mutant: fazla anahtar denetimi kaldirildi\n"
    modul, _kaynak, hata = _BellekMutasyonu(
        BUILD_PY, "build_k165_m2", [(eski, yeni)]
    ).yukle()
    if hata:
        return False, "KABLO_KOPUK: %s" % hata
    try:
        _vaka_2_kol_a_capasi(modul)
    except SystemExit as sonuc:
        return True, "çapa yuttu: VAKA 2 DUSTU: %s" % sonuc
    return False, "M2 hayatta; çapa fazlalık anahtarını yuttu."


def _normal():
    vakalar = [_vaka_1_uctan_uca, _vaka_2_kol_a_capasi, _vaka_3_ikiz_sabit]
    dusen = 0
    for vaka in vakalar:
        try:
            vaka()
        except SystemExit as hata:
            dusen += 1
            print(str(hata))
    print("VAKA=3 DUSEN=%d" % dusen)
    return 0 if dusen == 0 else 1


def _mutasyon():
    sonuclar = []
    for etiket, fn in (("M1", _m1), ("M2", _m2)):
        try:
            oldu, sebep = fn()
        except Exception as hata:
            oldu, sebep = False, "KABLO_KOPUK: beklenmeyen istisna: %r" % (hata,)
        if oldu:
            print("%s OLDU vaka=%s sebep=%s" % (etiket, "1" if etiket == "M1" else "2", sebep))
            sonuclar.append(True)
        else:
            print("%s YASADI vaka=%s sebep=%s" % (etiket, "1" if etiket == "M1" else "2", sebep))
            sonuclar.append(False)
    iddia = sum(sonuclar)
    print("MUTANT=%d/2 IDDIA=%d" % (iddia, iddia))
    return 0 if iddia == 2 else 1


def main():
    if "--mutasyon" in sys.argv:
        return _mutasyon()
    return _normal()


if __name__ == "__main__":
    sys.exit(main())
