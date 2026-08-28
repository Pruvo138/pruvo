#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K337 — TUR HALI COZUCUSU (28 Agu 2026, cip KraL-K337Butce-28Agu).

NE ISE YARAR
------------
`claude -p --output-format json` cagrisinin ciktisini stdin'den okur,
INSAN METNINI stdout'a AYNEN gecirir (tee zinciri bozulmaz) ve turun
HALINI ayri bir durum dosyasina yazar.

NEDEN DIZGE DEGIL HAL
---------------------
🔴 K337'nin kok nedeni: butce kesintisi `Exceeded USD budget` INGILIZCE
CUMLESINDEN taninmaya calisiliyordu (isci.sh eski :572-575). Bu, K321'in
birebir sinifidir -- olcut hata MESAJINI okur, HALI degil; saglayici
metni degisince kol KOR kalir.

Kurulu CLI ikilisi (2.1.222) okundu: o cumle bir RENDER'dir, hal degil.
Govdedeki dal birebir sudur:

    case "error_max_budget_usd":
        ya(`Error: Exceeded USD budget (${l.maxBudgetUsd})`)

Yani halin ADI `error_max_budget_usd`; kardesleri `success`,
`error_max_turns`, `error_during_execution`,
`error_max_structured_output_retries`. Bu ad `--output-format json`
zarfinda **`subtype` alaninda makine-okunur** basilir. Bu cozucu
metni DEGIL o alani okur. Ingilizce cumle degisirse hicbir sey olmaz.

FAIL-CLOSED
-----------
Zarf hic bulunamazsa HAL=OLCULEMEDI yazilir -- "sifir"/"saglikli"
UYDURULMAZ ([[varlik-beyani-silmeyi-ifade-edemez]]). Taninmayan bir
`subtype` gelirse HAL=BILINMEYEN_HAL + SUBTYPE=<ad> yazilir; sessizce
saglikli sayilmaz.

Cikis kodu HER ZAMAN 0 -- turun kendi rc'si `pipestatus` ile okunur;
bu cozucu bir SUZGECTIR, hukum mercii degildir.

Kullanim:
    ... | isci-hal-cozucu.py --hal-dosyasi <yol> [--sessiz-hal-satiri]
"""

import argparse
import json
import os
import sys
import tempfile

# --- TEK KAYNAK: CLI subtype -> ev ici HAL adi ------------------------
# Anahtarlar CLI'nin KENDI durum sozlugudur (ikilisinden okundu).
# Deger, bu evin log/karar duzleminde kullandigi addir.
HAL_ADLARI = {
    "success": "SAGLIKLI",
    "error_max_budget_usd": "BUTCE_TAVANI",
    "error_max_turns": "TUR_TAVANI",
    "error_during_execution": "ICRA_HATASI",
    "error_max_structured_output_retries": "YAPISAL_CIKTI_HATASI",
}
# `subtype=success` AMA `is_error=true` hali gercekten olculdu (28 Agu,
# org erisim reddi probu): zarf "success" der, icerik hatadir. Bu HAL
# SAGLIKLI SAYILAMAZ, ama BUTCE_TAVANI da degildir -- kendi adini alir.
HAL_HATALI_SONUC = "HATALI_SONUC"
HAL_OLCULEMEDI = "OLCULEMEDI"
HAL_BILINMEYEN = "BILINMEYEN_HAL"


def zarf_mi(nesne):
    return isinstance(nesne, dict) and nesne.get("type") == "result"


def _json_nesneleri(metin):
    """Metindeki dengeli en ust duzey {...} bloklarini sirayla dondurur.

    stderr satirlari stdout'la ayni boruya aktigi icin zarf bir satirin
    ORTASINDA baslayabilir; satir bazli ayristirma yetmez.
    """
    derinlik = 0
    bas = -1
    dizge = False
    kacis = False
    for i, ch in enumerate(metin):
        if dizge:
            if kacis:
                kacis = False
            elif ch == "\\":
                kacis = True
            elif ch == '"':
                dizge = False
            continue
        if ch == '"':
            dizge = True
        elif ch == "{":
            if derinlik == 0:
                bas = i
            derinlik += 1
        elif ch == "}":
            if derinlik > 0:
                derinlik -= 1
                if derinlik == 0 and bas >= 0:
                    yield bas, i + 1, metin[bas:i + 1]
                    bas = -1


def zarfi_bul(metin):
    """(zarf_dict, bas, son) ya da (None, -1, -1)."""
    son_zarf = None
    for bas, son, parca in _json_nesneleri(metin):
        try:
            nesne = json.loads(parca)
        except ValueError:
            continue
        if zarf_mi(nesne):
            son_zarf = (nesne, bas, son)
    if son_zarf is None:
        return (None, -1, -1)
    return son_zarf


def hal_adi(zarf):
    """Zarftan HAL adini ve subtype'i dondurur."""
    subtype = zarf.get("subtype")
    hatali = bool(zarf.get("is_error"))
    if not isinstance(subtype, str) or not subtype:
        return (HAL_BILINMEYEN, "")
    ad = HAL_ADLARI.get(subtype)
    if ad is None:
        return (HAL_BILINMEYEN, subtype)
    if ad == "SAGLIKLI" and hatali:
        return (HAL_HATALI_SONUC, subtype)
    return (ad, subtype)


def durum_satiri(zarf):
    """Tek makine-okunur satir uretir."""
    if zarf is None:
        return ("HAL=%s SUBTYPE= IS_ERROR= MALIYET_USD= TUR= OTURUM= "
                "SEBEP=zarf-yok" % HAL_OLCULEMEDI)
    ad, subtype = hal_adi(zarf)
    maliyet = zarf.get("total_cost_usd")
    tur = zarf.get("num_turns")
    oturum = zarf.get("session_id")
    return ("HAL=%s SUBTYPE=%s IS_ERROR=%d MALIYET_USD=%s TUR=%s OTURUM=%s "
            "SEBEP=zarf-okundu"
            % (ad, subtype or "yok", 1 if zarf.get("is_error") else 0,
               maliyet if isinstance(maliyet, (int, float)) else "yok",
               tur if isinstance(tur, int) else "yok",
               oturum if isinstance(oturum, str) and oturum else "yok"))


def _atomik_yaz(yol, icerik):
    dizin = os.path.dirname(yol) or "."
    fd, gecici = tempfile.mkstemp(dir=dizin, prefix=".hal.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(icerik)
            f.flush()
            os.fsync(f.fileno())
        os.replace(gecici, yol)
    except BaseException:
        try:
            os.unlink(gecici)
        except FileNotFoundError:
            pass
        raise


def insan_metni(zarf):
    """Metin kipinin BASACAGI seyi uretir (log okunabilirligi korunur)."""
    sonuc = zarf.get("result")
    if isinstance(sonuc, str) and sonuc:
        return sonuc if sonuc.endswith("\n") else sonuc + "\n"
    return ""


def coz(girdi, cikti, hal_yolu, hal_satiri_bas=True):
    zarf, bas, son = zarfi_bul(girdi)
    if zarf is None:
        cikti.write(girdi)
        satir = durum_satiri(None)
    else:
        # Zarfin DISINDA kalan her sey (stderr teshisleri) AYNEN gecer.
        cikti.write(girdi[:bas])
        cikti.write(insan_metni(zarf))
        cikti.write(girdi[son:])
        satir = durum_satiri(zarf)
    if hal_satiri_bas:
        cikti.write(satir + "\n")
    if hal_yolu:
        try:
            _atomik_yaz(hal_yolu, satir + "\n")
        except OSError as e:
            cikti.write("HAL_YAZILAMADI hata=%s\n" % type(e).__name__)
    return satir


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--hal-dosyasi", default="")
    ap.add_argument("--sessiz-hal-satiri", action="store_true",
                    help="HAL satirini stdout'a BASMA (yalniz dosyaya yaz)")
    ns = ap.parse_args(argv)
    girdi = sys.stdin.read()
    coz(girdi, sys.stdout, ns.hal_dosyasi, not ns.sessiz_hal_satiri)
    return 0


if __name__ == "__main__":
    sys.exit(main())
