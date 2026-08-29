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

# 🔴 SU SEVIYESI — ONARIM HEDEFI, CEZA ESIGINDEN AYRIDIR (K353, 29 Agu 2026).
# OLCULEN ARIZA: `defter-rotasyon.py --tavan-kaynaktan`in dongu cikis kosulu
# `not _tavan_asildi_mi(...)` idi — yani rotasyon TAVANA DEGER DEGMEZ duruyordu.
# 29 Agu olcumu: hedef 11.500 iken rotasyon 12.266'da durdu, tavanin (12.288)
# ALTINDA yalnizca 22 BAYT pay birakti. Deftere yazilan bir sonraki satir kotayi
# ANINDA yeniden asar; kapi yeniden kirmizi yanar, yordamin emrettigi komut ise
# `TAVAN=DOLU_NO_OP rc=0` ile INERT doner ([[onarim-kolu-zarar-esiginin-arkasinda]]).
# Bu, kota kapisinin 29 Agu supurmesinde SILINMESININ de gerekcesiydi (kanca
# adim 8: "kapi evin TUM commit'ini kilitliyordu") — yani sinif onarilmadan kapi
# geri kurulursa kilit de geri gelir.
# CARE: CEZA esigi (TAVAN_*) ile ONARIM hedefi (SU_SEVIYESI_*) AYRI sayilardir.
# Kapi TAVANDA kirmizi yakar; rotasyon SU SEVIYESINE iner ve arada BAS PAYI kalir.
# Oran kutu tarafiyla ayni desendir (`kutu-arsivle.py::SU_SEVIYESI_ORANI`).
# 🔴 BEST-EFFORT: su seviyesine INILEMEZSE ama defter tavanin ALTINA indiyse bu
# BASARIDIR (kota saglandi) — pay kisaligi ADIYLA BASILIR, kilit URETILMEZ.
# Aksi halde onarim kolu yeni bir yerde yeniden zarar esiginin arkasina duserdi.
SU_SEVIYESI_ORANI = 0.8


def su_seviyesi(tavan):
    """Tavandan ONARIM hedefini turetir. None ise o eksen yok sayilir.

    DAIMA tavanin ALTINDA kalir (en az 1 birim); tavanla ESITLENEMEZ — esitlik
    tam da onarilan arizanin kendisidir.
    """
    if tavan is None:
        return None
    hedef = int(tavan * SU_SEVIYESI_ORANI)
    if hedef >= tavan:
        hedef = tavan - 1
    if hedef < 1:
        hedef = 1
    return hedef


SU_SEVIYESI_SATIR = su_seviyesi(TAVAN_SATIR)
SU_SEVIYESI_BAYT = su_seviyesi(TAVAN_BAYT)

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
