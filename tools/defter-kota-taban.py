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

# ---------------------------------------------------------------------------
# ONLEM ESIGI (K351, 29 Agu 2026) — TAVANIN ALTINDA KALAN IKINCI EKSEN
# ---------------------------------------------------------------------------
# 🔴 OLCULEN ARIZA (29 Agu, cip `KraL-Tamirci-29Agu`; iddia degil, iki kosum):
# defter 12.284 B iken (tavana 4 BAYT) yordamin emrettigi
# `defter-rotasyon.py --tavan-kaynaktan` **`TASINAN=0 ... TAVAN=DOLU_NO_OP`**
# dondu ve dosya BIREBIR ayni kaldi. Sebep yapisal: rotasyon aracinin tavan
# dongusu daha ilk adimda `if not _tavan_asildi_mi(...): return 0` ile cikiyor,
# ve ONARIM MEKANIZMASININ TAMAMI (cok-gecisli tasima + `--isaretciye-indir`)
# o dongunun ICINDE yasiyor. Yani arac ancak tavan ASILDIKTAN sonra is yapabilir
# — ama tavan asildigi anda `defter-kota-kapisi.py` EVIN TUM COMMIT'INI zaten
# kilitlemis olur. Koruma, korudugu isi ancak zarar olustuktan sonra yapabiliyor
# ([[koruma-kurali-korudugunu-durdurur]]).
#
# COZUM EKSENI: tavan TEK basina yetmez; tavanin ALTINDA, arac icin ERISILEBILIR
# ikinci bir esik gerekir. Bu esik BURADA, tavanin sahibi olan TEK KAYNAKTA
# durur ve tavandan TURETILIR — yordama ya da komut satirina elle yazilan her
# sayi ikinci bir kopyadir ve sessizce ayrisir
# ([[kapi-red-metni-ikinci-kopyadir]]).
#
# 🔴 KAPSAM — ONLEM ESIGI KAPININ HUKMUNU DEGISTIRMEZ: `tavan_asi_mi()` ve
# dolayisiyla `defter-kota-kapisi.py` KIRMIZI/YESIL hukmu YALNIZ tavandan
# turer. Onlem esigi ayri bir eksendir ve yalniz ROTASYON ARACINA hedef verir.
# Onlemi kapinin hukmune baglamak, kilidi 130/12288'den 117/11059'a CEKMEK
# olurdu — yani arizayi onarmak yerine ONE ALMAK. Kapi mutantiyla civilenmistir.
ONLEM_ORANI = 0.90


def onlem_esikleri():
    """(onlem_satir, onlem_bayt) — TAVANDAN TURETILIR, ayrica YAZILMAZ.

    Ikinci bir sabit tablo ACILMAZ: oran degisirse iki esik de birlikte kayar.
    """
    return int(TAVAN_SATIR * ONLEM_ORANI), int(TAVAN_BAYT * ONLEM_ORANI)


def onlem_asi_mi(satir, bayt):
    """Onlem esigi ekseni. Donus `tavan_asi_mi` ile AYNI bicimde.

    🔴 Bu fonksiyon KAPI HUKMU URETMEZ — yalniz rotasyon aracinin "daha
    tasiyacak isim var mi" sorusunu cevaplar.
    """
    o_satir, o_bayt = onlem_esikleri()
    satir_as = satir > o_satir
    bayt_as = bayt > o_bayt
    if satir_as and bayt_as:
        return True, "IKISI", satir, bayt
    if satir_as:
        return True, "SATIR", satir, bayt
    if bayt_as:
        return True, "BAYT", satir, bayt
    return False, "", satir, bayt

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
