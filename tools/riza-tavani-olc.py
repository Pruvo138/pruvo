#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RIZA TAVANI — Ads'e OCI ile yuklenebilecek satin almanin UST SINIRINI sayiyla basar.

NEDEN VAR (21 Eyl 2026, cip `KraL-RizaOrani-21Eyl`):
  `attribution-ref.js:279` hasConsent() = localStorage[CONSENT_KEY] === "kabul" -> OPT-IN,
  varsayilan riza YOK. `:355` persistPaidOnLoad() ilk satiri `if (!hasConsent()) return;`.
  Yani tiklama kimligi (gclid/gbraid/wbraid) rizasiz oturumda HIC saklanmiyor. Sonuc:
  OCI yukleme hatti kurulsa BILE Ads'e yansiyacak satin almanin ust siniri RIZA ORANIDIR.
  Bu bir kod kusuru DEGIL, bir TAVAN'dir -> [[oci-tavani-riza-kapisidir]].

🔴 OLCUM EKSENI: SIPARIS, ziyaret DEGIL. Sebep — obur uc eksen KAPALI ya da DONGUSEL:
  * GA4 rizasiz oturumu GORMEZ -> GA4'ten oran cikarmak DONGUSELDIR.
  * CF RUM rizadan bagimsizdir ama SORGU DIZESI BOYUT DEGILDIR
    (rumPageloadEventsAdaptiveGroups boyutlari: bot/countryName/date/deliveryType/deviceType/
    navigationType/refererHost/refererPath/refererScheme/requestHost/requestPath/requestScheme/
    siteTag/userAgentBrowser/userAgentOS) -> gclid tasiyan INISI AYIRT EDEMEZ, paid inis
    sayisi oradan CIKMAZ.
  * Ads tik sayisi (N) Google Ads API kimligi ister; o kimlik SIFRE sinifi = OKAN KAPISI,
    ayrica tarayici KraL evinde SERT BLOKLU -> bu evden ERISILEMEZ.
  KALAN ve DOGRUDAN olcum: siparisin KENDISI. `siparisler.atif.$.ref` alani RIZA
  KAPISININ DISINDA yazilir (index.html::PRUVO_ATIF.topla — "RIZA KAPISININ DISINDA —
  bilerek"; REF click-id tasimaz, src+grup+4 rastgele karakterdir), buna karsilik
  `reklam_ref_gclid` satiri YALNIZ riza varken duser. Dolayisiyla:
      PAYDA (rizadan BAGIMSIZ) = ref'i 'REF:GS-' ile baslayan siparisler (paid tik kokenli)
      PAY   (riza kapili)      = o ref'in `reklam_ref_gclid`de TIK KIMLIKLI karsiligi
  Oran = Ads'e yuklenebilecek satin almanin UST SINIRI. Vekil DEGIL, tavanin KENDISI.

FAIL-CLOSED: girdi ucu erisilemez / payda 0 / pay > payda / alan eksik -> rc != 0 ve
`HAL=<ariza>` satiri. SESSIZ "%0" YOKTUR: "pay 0" ile "payda 0" AYRI hukumlerdir.

KULLANIM (borusuz):
  python3 tools/riza-tavani-olc.py
  python3 tools/riza-tavani-olc.py --baslangic 2026-08-27 --bitis 2026-09-22
  python3 tools/riza-tavani-olc.py --fikstur <satirlar.json>      # D1'e DOKUNMAZ (test kolu)
"""
import argparse
import datetime
import importlib.util
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")

# REF halkasi (K99) 25 Agu 2026'da indi; ILK ref tasiyan siparis 27 Agu'dur. Daha erken bir
# baslangic paydayi SAHTE DARALTIR degil, sahte GENISLETIR: o donemde paid siparis de ref
# TASIMIYORDU, dolayisiyla paya giremez ama paydaya da girmez — yine de pencereyi halkanin
# indigi tarihe capalamak, "tavan dusuk" hukmunun olcum baslangicindan DEGIL gercekten
# rizadan geldigini garanti eder.
VARSAYILAN_BASLANGIC = "2026-08-27"

# `atif` kolonu NOT NULL DEFAULT '' — bos dizgede json_extract SQLITE_ERROR (7500) verir ve
# TUM sorgu duser. Kapi: yalnizca '{' ile baslayan degerde json_extract cagir.
_ATIF_JSON = "s.atif LIKE '{' || '%'"
_REF = "CASE WHEN " + _ATIF_JSON + " THEN json_extract(s.atif,'$.ref') END"
_GAID = "CASE WHEN " + _ATIF_JSON + " THEN json_extract(s.atif,'$.ga_client_id') END"

SQL = """
SELECT
  substr({ref},5,2)                                       AS src,
  s.durum                                                 AS durum,
  CASE WHEN {gaid} IS NOT NULL THEN 1 ELSE 0 END          AS rizali,
  CASE WHEN g.gclid IS NOT NULL OR g.gbraid IS NOT NULL
            OR g.wbraid IS NOT NULL THEN 1 ELSE 0 END     AS tik_kimlikli
FROM siparisler s
LEFT JOIN reklam_ref_gclid g ON g.ref = {ref}
WHERE {ref} IS NOT NULL
  AND s.tarih >= '{bas}' AND s.tarih < '{bit}'
""".strip()

PAID_SRC = "GS"
ORGANIK_SRC = "OG"
ZORUNLU_ALANLAR = ("src", "durum", "rizali", "tik_kimlikli")


class Ariza(Exception):
    """HAL=<jeton> + rc ile DURAN ariza. Sessiz varsayilana ASLA dusulmez."""

    def __init__(self, jeton, rc, aciklama):
        super().__init__(aciklama)
        self.jeton = jeton
        self.rc = rc
        self.aciklama = aciklama


def wilson(pay, payda, z=1.96):
    """95% Wilson araligi. n kucukken normal yaklasim yaniltir; tavan bir BUTCE KARARI
    girdisi oldugu icin belirsizlik SAYIYLA basilir, gizlenmez."""
    if payda <= 0:
        raise Ariza("PAYDA-SIFIR", 3, "Wilson: payda 0")
    p = pay / payda
    d = 1 + z * z / payda
    merkez = (p + z * z / (2 * payda)) / d
    yari = z * math.sqrt(p * (1 - p) / payda + z * z / (4 * payda * payda)) / d
    return max(0.0, merkez - yari), min(1.0, merkez + yari)


def olc(satirlar):
    """SAF cekirdek: satir listesi -> olcum sozlugu. D1/dosya BILMEZ; testin surdugu yuzey."""
    if not isinstance(satirlar, list):
        raise Ariza("GIRDI-BICIMI", 5, "satirlar bir liste degil: %r" % type(satirlar))
    for i, r in enumerate(satirlar):
        if not isinstance(r, dict):
            raise Ariza("GIRDI-BICIMI", 5, "satir %d sozluk degil" % i)
        eksik = [a for a in ZORUNLU_ALANLAR if a not in r]
        if eksik:
            raise Ariza("ALAN-EKSIK", 5, "satir %d alan eksik: %s" % (i, ",".join(eksik)))

    paid = [r for r in satirlar if r["src"] == PAID_SRC]
    organik = [r for r in satirlar if r["src"] == ORGANIK_SRC]
    payda = len(paid)
    if payda == 0:
        # 🔴 SESSIZ %0 YASAGI: "hic paid siparis yok" ile "tavan %0" AYRI hukumlerdir.
        raise Ariza("PAYDA-SIFIR", 3,
                    "pencerede ref'i 'REF:GS-' ile baslayan SIPARIS YOK — tavan TANIMSIZ "
                    "(oran hesaplanmaz). Pencereyi genislet ya da paid trafigin siteye "
                    "indigini once dogrula.")

    pay = sum(1 for r in paid if int(r["tik_kimlikli"]) == 1)
    rizali = sum(1 for r in paid if int(r["rizali"]) == 1)
    if pay > payda:
        raise Ariza("PAY-PAYDADAN-BUYUK", 4,
                    "tik kimlikli paid siparis (%d) paid siparis sayisini (%d) asti — "
                    "JOIN cogalmasi ya da bozuk pay kaynagi" % (pay, payda))
    if rizali > payda:
        raise Ariza("PAY-PAYDADAN-BUYUK", 4,
                    "rizali paid siparis (%d) > paid siparis (%d)" % (rizali, payda))

    tam = [r for r in paid if r["durum"] == "tamamlandi"]
    tam_pay = sum(1 for r in tam if int(r["tik_kimlikli"]) == 1)
    org_rizali = sum(1 for r in organik if int(r["rizali"]) == 1)
    alt, ust = wilson(pay, payda)
    return {
        "paid_siparis": payda,
        "tik_kimlikli": pay,
        "rizali_paid": rizali,
        "tavan_simdi": pay / payda,
        "tavan_oci2": rizali / payda,
        "guven_alt": alt,
        "guven_ust": ust,
        "paid_tamamlandi": len(tam),
        "tamamlandi_tik_kimlikli": tam_pay,
        "tavan_tamamlandi": (tam_pay / len(tam)) if tam else None,
        "organik_siparis": len(organik),
        "organik_rizali": org_rizali,
        "organik_riza_orani": (org_rizali / len(organik)) if organik else None,
    }


def d1_satirlari(bas_t, bit_t):
    """Canli D1 (SALT OKUMA). Erisilemezse HAL=D1-ERISILEMEDI ile DURUR — sessiz bos liste YOK."""
    yol = os.path.join(TOOLS, "d1-sync.py")
    if not os.path.exists(yol):
        raise Ariza("D1-ERISILEMEDI", 2, "tools/d1-sync.py yok: %s" % yol)
    if TOOLS not in sys.path:
        sys.path.insert(0, TOOLS)
    try:
        spec = importlib.util.spec_from_file_location("d1sync_riza", yol)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except BaseException as e:                     # SystemExit DAHIL — sessizce olme yok
        raise Ariza("D1-ERISILEMEDI", 2, "d1-sync yuklenemedi: %s" % str(e)[:400])
    sql = SQL.format(ref=_REF, gaid=_GAID, bas=bas_t, bit=bit_t)
    try:
        ham = mod.sorgu(sql)
    except BaseException as e:
        raise Ariza("D1-ERISILEMEDI", 2, "D1 sorgusu basarisiz: %s" % str(e)[:400])
    if not ham or not isinstance(ham, list) or not ham[0].get("success"):
        raise Ariza("D1-ERISILEMEDI", 2,
                    "D1 yaniti basarili degil: %s" % json.dumps(ham, ensure_ascii=False)[:400])
    return ham[0].get("results") or []


def fikstur_satirlari(yol):
    if not os.path.exists(yol):
        raise Ariza("FIKSTUR-YOK", 2, "fikstur dosyasi yok: %s" % yol)
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise Ariza("FIKSTUR-BOZUK", 2, "fikstur okunamadi: %s" % e)


def _yuzde(x):
    return "OLCULEMEDI" if x is None else ("%.1f%%" % (100.0 * x))


def yaz(o, bas_t, bit_t, kaynak):
    print("PENCERE=%s..%s  KAYNAK=%s" % (bas_t, bit_t, kaynak))
    print("PAYDA_PAID_SIPARIS=%d   (rizadan BAGIMSIZ: siparisler.atif.$.ref 'REF:GS-')"
          % o["paid_siparis"])
    print("PAY_TIK_KIMLIKLI=%d     (riza kapili: reklam_ref_gclid gclid/gbraid/wbraid)"
          % o["tik_kimlikli"])
    print("TAVAN_SIMDI=%s          (bugun Ads'e YUKLENEBILIR satin alma orani)"
          % _yuzde(o["tavan_simdi"]))
    print("GUVEN_ARALIGI_95=%s..%s (Wilson, n=%d)"
          % (_yuzde(o["guven_alt"]), _yuzde(o["guven_ust"]), o["paid_siparis"]))
    print("RIZALI_PAID=%d          TAVAN_OCI2=%s  (OCI#2 sonrasi ulasilabilir tavan)"
          % (o["rizali_paid"], _yuzde(o["tavan_oci2"])))
    print("PAID_TAMAMLANDI=%d      TAMAMLANDI_TIK_KIMLIKLI=%d  TAVAN_TAMAMLANDI=%s"
          % (o["paid_tamamlandi"], o["tamamlandi_tik_kimlikli"], _yuzde(o["tavan_tamamlandi"])))
    print("ORGANIK_SIPARIS=%d      ORGANIK_RIZALI=%d  ORGANIK_RIZA_ORANI=%s  (karsilastirma ekseni)"
          % (o["organik_siparis"], o["organik_rizali"], _yuzde(o["organik_riza_orani"])))
    print("HAL=TAMAM")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--baslangic", default=VARSAYILAN_BASLANGIC, help="YYYY-MM-DD (dahil)")
    ap.add_argument("--bitis", default=None, help="YYYY-MM-DD (haric); varsayilan yarin")
    ap.add_argument("--fikstur", default=None, help="D1 yerine JSON satir listesi (test kolu)")
    ap.add_argument("--json", action="store_true", help="olcumu JSON olarak da bas")
    a = ap.parse_args(argv)

    bit_t = a.bitis or (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    try:
        b0 = datetime.date.fromisoformat(a.baslangic)
        b1 = datetime.date.fromisoformat(bit_t)
    except ValueError as e:
        print("HAL=PENCERE-BICIMI  %s" % e, file=sys.stderr)
        print("HAL=PENCERE-BICIMI")
        return 6
    if b1 <= b0:
        print("HAL=PENCERE-TERS  bitis <= baslangic (%s..%s)" % (a.baslangic, bit_t),
              file=sys.stderr)
        print("HAL=PENCERE-TERS")
        return 6

    try:
        if a.fikstur:
            satirlar, kaynak = fikstur_satirlari(a.fikstur), "fikstur"
        else:
            satirlar, kaynak = d1_satirlari(a.baslangic, bit_t), "D1(canli,salt-okuma)"
        o = olc(satirlar)
    except Ariza as x:
        print("HAL=%s  %s" % (x.jeton, x.aciklama), file=sys.stderr)
        print("HAL=%s" % x.jeton)
        return x.rc
    yaz(o, a.baslangic, bit_t, kaynak)
    if a.json:
        print(json.dumps(o, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
