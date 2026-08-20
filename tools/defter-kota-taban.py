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

🔴 KUTU (ORTAK POSTA KUTUSU) EKSENI — K253, 20 Agu 2026:
Kutunun tavani BU DOSYAYA YAZILMAZ. Kutunun MEVCUT tavan sahibi
`tools/kutu-arsivle.py::VARSAYILAN_TAVAN`dir (LOSSLESS rotasyon araci onu
kullanir). Kapi ile arac AYNI sayidan beslenmezse kapi "asildi" derken arac
"tavan altinda, is yok" der -> SESSIZ AYRISMA. Bu yuzden kutu tavani
SAHIPTEN TURETILIR (`kutu_sahibi()`), koda gomulu IKINCI bir sabit ACILMAZ.
"""
import os

TAVAN_SATIR = 130
TAVAN_BAYT = 12288

# Kutu tavaninin/yolunun MEVCUT sahibi. Ad burada yazilir, SAYI YAZILMAZ.
KUTU_SAHIBI_ADI = "kutu-arsivle.py"


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


# ---------------------------------------------------------------------------
# KUTU TAVANI — SAHIPTEN TURETME (K253)
# ---------------------------------------------------------------------------
def kutu_sahip_yolu(kok):
    """Yargilanan DEPO KOKUNE gore sahip dosyasinin yolu.

    🔴 EKSEN `kok`TUR, kapinin KENDI konumu DEGIL: kutu, KraL checkout'una ait
    bir varliktir. Sahip dosyasini kapinin yanindan cozseydik, sentetik fikstur
    depolarini (kabul testleri) yargilarken de GERCEK makinenin kutusunu olcer,
    komsu testleri ambiyans yuzunden kirmiziya yakardik
    ([[kapi-ambiyansi-olcerse-komsu-kirmiziya-yakar]]).
    """
    return os.path.join(kok, "tools", KUTU_SAHIBI_ADI)


def kutu_sahibi(kok):
    """(modul, sahip_yolu, hata) — <kok>/tools/kutu-arsivle.py'yi yukler.

    modul None + hata None  -> sahip BU DEPODA YOK (kutuyu bu checkout sahiplenmiyor).
    modul None + hata dolu   -> sahip VAR ama yuklenemedi (OLCULEMEDI sinifi).
    """
    yol = kutu_sahip_yolu(kok)
    if not os.path.isfile(yol):
        return None, yol, None
    import importlib.util as _ilu
    try:
        spec = _ilu.spec_from_file_location("pruvo_kutu_arsivle_sahip", yol)
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:                                   # noqa: BLE001
        return None, yol, "sahip modul yuklenemedi: %s" % e
    return mod, yol, None


def kutu_tavan_satir(mod):
    """Sahip modulunden kutu SATIR tavani. Sayi burada YAZILMAZ, OKUNUR."""
    return getattr(mod, "VARSAYILAN_TAVAN", None)


def kutu_dosya_yolu(mod):
    """Sahip modulunden kutu dosyasinin MUTLAK yolu (yine sahipten TURETILIR)."""
    yol = getattr(mod, "KUTU_VARSAYILAN", None)
    if not yol:
        return None
    return os.path.abspath(os.path.expanduser(yol))


def kutu_arsiv_yolu(mod):
    """Sahip modulunden arsiv dosyasinin MUTLAK yolu (care satirinda gecer)."""
    yol = getattr(mod, "ARSIV_VARSAYILAN", None)
    if not yol:
        return None
    return os.path.abspath(os.path.expanduser(yol))
