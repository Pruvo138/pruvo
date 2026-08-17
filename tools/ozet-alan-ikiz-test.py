#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OZET KART ALANI — IKIZ TANIM KAPISI (K164, 17 Agu 2026).

NEDEN VAR (olculmus ariza, tekil yama DEGIL sinif kapisi):
`tools/build.py::kart_ozeti` karta alan yazar; `OZET_KART_ALANLARI` ise o kartin TEL
temsilini (ozet.json dizi konumlari) tanimlar. Iki tanim AYRI yerde durur ve birbirini
KONTROL ETMEZ. `boy_secenekleri` 11 Agu'da `kart_ozeti`ye eklendi, sozluge eklenmedi:
alan tele hic cikmadi, konum capasi (yalniz sozlugu gezdigi icin) KOR kaldi ve ariza
**alani tasiyan ilk urun katalogda dogana kadar** (6 gun) uyudu. Dogdugu gun build
`ozet.json temsili KAYIPLI` ile exit 1 verdi, `deploy`+`yayin` skipped oldu ve SITENIN
TUM YAYINI DURDU (run 32064889335).

Calisma ani kolu (`_temsil_konum_capasi` icindeki `fazla` denetimi) ayni sinifi yakalar
AMA yalnizca alani TASIYAN bir urun katalogda VARSA. Bu dosya STATIK olcer: alan
`kart_ozeti`ye eklendigi GUN kirmizi yanar, urun beklemeden.

YON: `kart_ozeti`nin yazabildigi her anahtar `OZET_KART_ALANLARI`nda OLMALIDIR.
Ters yon (sozlukte olup artik yazilmayan alan) HATA DEGILDIR: konum sabitligi bayat
istemcinin sozlesmesidir, alan sozlukten CIKARILMAZ.

Kabul satiri: `ALAN_EVRENI=<n> SOZLUK=<n> EKSIK=<n> KENDINI_TEST=<n>/<n>`
"""
import ast
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(KOK, "tools", "build.py")

# Parser korlesme tabani: `kart_ozeti` govdesindeki sozluk literalinde bugun 8 taban alan
# var. Ayiklayici bundan AZ bulursa desen degismis demektir -> FAIL-CLOSED (sessiz yesil
# yerine kirmizi). [[mimar-kapi-parser-taklidi]]
TABAN_ASGARI = 8


def _sozluk_alanlari(agac):
    """`OZET_KART_ALANLARI = (...)` demetini kaynaktan cozer (import YOK)."""
    for dugum in ast.walk(agac):
        if not isinstance(dugum, ast.Assign):
            continue
        for hedef in dugum.targets:
            if isinstance(hedef, ast.Name) and hedef.id == "OZET_KART_ALANLARI":
                if not isinstance(dugum.value, (ast.Tuple, ast.List)):
                    raise SystemExit("KAPI KORLESTI: OZET_KART_ALANLARI demet/liste degil.")
                adlar = []
                for oge in dugum.value.elts:
                    if not (isinstance(oge, ast.Constant) and isinstance(oge.value, str)):
                        raise SystemExit("KAPI KORLESTI: OZET_KART_ALANLARI'nda dize olmayan "
                                         "oge var (%r)." % (ast.dump(oge)[:80],))
                    adlar.append(oge.value)
                return adlar
    raise SystemExit("KAPI KORLESTI: OZET_KART_ALANLARI atamasi bulunamadi.")


def _kart_alan_evreni(agac, fonksiyon="kart_ozeti", degisken="kart"):
    """`kart_ozeti`nin karta yazabildigi ANAHTAR EVRENINI kaynaktan cikarir.

    Iki desen sayilir:
      * `kart = { "id": ..., ... }`  -> sozluk literalinin anahtarlari
      * `kart["X"] = ...`            -> kosullu alanlar
    Anahtari SABIT DIZE olmayan yazma (ornegin `kart[degisken] = ...`) cozulemez ->
    FAIL-CLOSED: kapi kirmizi yanar, cunku evren artik statik olarak bilinemez.
    """
    for dugum in ast.walk(agac):
        if isinstance(dugum, ast.FunctionDef) and dugum.name == fonksiyon:
            hedef_fn = dugum
            break
    else:
        raise SystemExit("KAPI KORLESTI: `%s` fonksiyonu bulunamadi." % fonksiyon)

    alanlar = []
    for dugum in ast.walk(hedef_fn):
        if not isinstance(dugum, ast.Assign):
            continue
        for hedef in dugum.targets:
            # kart = {...}
            if (isinstance(hedef, ast.Name) and hedef.id == degisken
                    and isinstance(dugum.value, ast.Dict)):
                for anahtar in dugum.value.keys:
                    if not (isinstance(anahtar, ast.Constant)
                            and isinstance(anahtar.value, str)):
                        raise SystemExit("KAPI KORLESTI: `%s` sozluk literalinde SABIT "
                                         "OLMAYAN anahtar var." % degisken)
                    alanlar.append(anahtar.value)
            # kart["X"] = ...
            if (isinstance(hedef, ast.Subscript)
                    and isinstance(hedef.value, ast.Name) and hedef.value.id == degisken):
                dilim = hedef.slice
                if not (isinstance(dilim, ast.Constant) and isinstance(dilim.value, str)):
                    raise SystemExit("KAPI KORLESTI: `%s[...]` yazmasinda anahtar SABIT DIZE "
                                     "degil — alan evreni statik olarak cozulemez." % degisken)
                alanlar.append(dilim.value)
    return alanlar


def olc(kaynak, yol_etiketi="tools/build.py", taban_asgari=TABAN_ASGARI):
    """(evren, sozluk, eksik) dondurur; korlesmede SystemExit atar."""
    agac = ast.parse(kaynak, filename=yol_etiketi)
    sozluk = _sozluk_alanlari(agac)
    evren = _kart_alan_evreni(agac)
    if len(evren) < taban_asgari:
        raise SystemExit("KAPI KORLESTI (%s): `kart_ozeti` evreninde %d alan bulundu, taban "
                         "en az %d — ayiklayici deseni kaybetmis."
                         % (yol_etiketi, len(evren), taban_asgari))
    eksik = [a for a in evren if a not in sozluk]
    return evren, sozluk, eksik


# --------------------------------------------------------------- KENDINI TEST (mutasyon)
# Nobetci CANLI mi: kapiyi kendi mantigini bozarak sinariz. Yesil bir cumle degil, KIRMIZI
# yanan bir mutant kapatir. [[kapi-varlik-olcer-yokluk-olcmez]]
_FIKSTUR_TEMIZ = '''
OZET_KART_ALANLARI = ("id", "baslik", "kategori", "marka", "fiyat", "gorsel",
                      "parametrik", "aciklama", "eski_fiyat", "boy_secenekleri")

def kart_ozeti(p):
    kart = {
        "id": p.get("id"),
        "baslik": p.get("baslik") or "",
        "kategori": p.get("kategori") or "",
        "marka": p.get("marka") or [],
        "fiyat": p.get("fiyat") or "",
        "gorsel": None,
        "parametrik": False,
        "aciklama": "",
    }
    if p.get("eski_fiyat"):
        kart["eski_fiyat"] = p.get("eski_fiyat")
    if p.get("boy_secenekleri"):
        kart["boy_secenekleri"] = p.get("boy_secenekleri")
    return kart
'''

# M1 = bugunku ariza birebir: kosullu alan karta yazilir, sozlukte YOKTUR.
_FIKSTUR_M1 = _FIKSTUR_TEMIZ.replace(', "boy_secenekleri")', ')')
# M2 = taban sozluk literaline sozlukte olmayan alan eklenir (kosullu degil, taban kol).
_FIKSTUR_M2 = _FIKSTUR_TEMIZ.replace('        "aciklama": "",',
                                     '        "aciklama": "",\n        "zzz_yeni": 1,')
# M3 = anahtar sabit dize degil -> evren statik cozulemez, kapi KIRMIZI olmali (fail-closed).
_FIKSTUR_M3 = _FIKSTUR_TEMIZ.replace('kart["boy_secenekleri"] = p.get("boy_secenekleri")',
                                     'kart[ad] = p.get("boy_secenekleri")')
# K1 = KONTROL: sozlukte olup artik yazilmayan alan HATA DEGIL (konum sabitligi korunur).
_FIKSTUR_K1 = _FIKSTUR_TEMIZ.replace('"eski_fiyat", "boy_secenekleri")',
                                     '"eski_fiyat", "boy_secenekleri", "eski_alan")')


def _kirmizi_mi(kaynak):
    """Fikstur uzerinde kapi KIRMIZI yaniyor mu (eksik alan ya da korlesme)."""
    try:
        _evren, _sozluk, eksik = olc(kaynak, "<fikstur>", taban_asgari=8)
    except SystemExit:
        return True
    return bool(eksik)


def kendini_test():
    vakalar = [("M1 kosullu alan sozlukte yok", _FIKSTUR_M1, True),
               ("M2 taban alan sozlukte yok", _FIKSTUR_M2, True),
               ("M3 anahtar sabit dize degil", _FIKSTUR_M3, True),
               ("K1 sozlukte fazladan alan (kontrol)", _FIKSTUR_K1, False),
               ("K0 temiz fikstur (kontrol)", _FIKSTUR_TEMIZ, False)]
    gecen = 0
    for ad, kaynak, beklenen_kirmizi in vakalar:
        gercek = _kirmizi_mi(kaynak)
        if gercek == beklenen_kirmizi:
            gecen += 1
        else:
            print("KENDINI TEST DUSTU: %s — beklenen kirmizi=%s, gercek=%s"
                  % (ad, beklenen_kirmizi, gercek))
    return gecen, len(vakalar)


def main():
    gecen, toplam = kendini_test()
    with open(BUILD, encoding="utf-8") as f:
        kaynak = f.read()
    evren, sozluk, eksik = olc(kaynak)
    if eksik:
        print("🔴 IKIZ TANIM: `kart_ozeti` su alan(lar)i karta yaziyor ama "
              "OZET_KART_ALANLARI'nda YOK: %s" % ", ".join(sorted(set(eksik))))
        print("   Sonuc: alan ozet.json teline HIC cikmaz; kart sepet fiyatini etkiliyorsa "
              "edge modunda SESSIZ fiyat sapmasi olur, build ise `ozet.json temsili KAYIPLI` "
              "ile exit 1 verip TUM YAYINI durdurur.")
        print("   Care: alani OZET_KART_ALANLARI'nin SONUNA ekle (0-11 konumlari artefakt "
              "sozlesmesidir, ortaya EKLEME).")
    print("ALAN_EVRENI=%d SOZLUK=%d EKSIK=%d KENDINI_TEST=%d/%d"
          % (len(set(evren)), len(sozluk), len(set(eksik)), gecen, toplam))
    if eksik or gecen != toplam:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
