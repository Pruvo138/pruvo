#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/defter-kota-taban.py — defter kotası ORTAK tavan değerleri.

🔴 TEK KAYNAK ([[ikiz-tanim-sessiz-ayrisma]]):
    * tools/defter-kota-kapisi.py (kota kapısı)
    * tools/defter-rotasyon.py (rotasyon aracı)
    aynı dosyadan okur; ikinci bir tavan tablosu AÇILMAZ.

Eksen:
    TAVAN_SATIR  — satır sayısı tavanı (mevcut tek-eksen davranışı).
    TAVAN_BAYT   — UTF-8 bayt tavanı (K178 yeni eksen).

Hüküm:
    KIRMIZI  = satir > TAVAN_SATIR  VEYA  bayt > TAVAN_BAYT
    YESIL    = satir <= TAVAN_SATIR VE bayt <= TAVAN_BAYT
    ASAN_EKSEN  = SATIR | BAYT | IKISI | ""  (yesılken boş)

NO-OP: biri None ise o eksen yoksayılır (geriye uyumlu tek-eksen).
"""
TAVAN_SATIR = 130
TAVAN_BAYT = 12288


def tavan_asi_mi(satir, bayt):
    """İki ekseni de yerine getirip aşan ekseni adıyla raporlar.

    Donus: (asi_mi, asan_eksen, satir, bayt).
    asan_eksen: 'SATIR' | 'BAYT' | 'IKISI' | '' (yesılken).
    """
    satir_as = satir > TAVAN_SATIR
    bayt_as = bayt > TAVAN_BAYT
    if satir_as and bayt_as:
        return True, "IKISI", satir, bayt
    if satir_as:
        return True, "SATIR", satir, bayt
    if bayt_as:
        return True, "BAYT", satir, bayt
    return False, "", satir, bayt
