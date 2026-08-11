#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KONFIGUR SIYAH KAPAK KAPISI — onden secili renk Siyah KALIYOR mu? (FAIL-CLOSED)

NE KORUR (Okan emri, 11 Agu 2026)
---------------------------------
Konfigur/dekor urunlerinde KAPAK GORSELI siyah olacak ve URUN SAYFASINDA ONDEN
SECILI RENK Siyah olacak. Bu iki sey AYNI seydir: onden secili renk AYRI bir alanda
DURMAZ, `tools/build.py::_konfigur_varsayilan_renk` onu KAPAK GORSELINDEN turetir
(renkGorselIndeks'i 0 olan renk; yoksa listenin ilki). Yani kapagi griye geri almak
on-secimi de griye cevirir — sessizce, tek bir alan adi bile degismeden.

🔴 KURAL VERIDEN DEGIL URETIM KODUNDAN TURETILIR
------------------------------------------------
Bu kapi on-secim rengini YENIDEN YAZMAZ; sayfayi basan fonksiyonun TA KENDISINI
(`build._konfigur_varsayilan_renk`) cagirir. Kopya bir yuklem yazmak, iki tanimin
sessizce ayrismasi demektir ([[ikiz-tanim-sessiz-ayrisma]]): kapi yesil yanarken
sayfa baska renk basabilirdi. Fonksiyon bulunamazsa kapi "gecti" DEMEZ, OLCULEMEDI
basar ve KIRMIZI biter.

IKI EKSEN (biri digerini KARSILAMAZ)
------------------------------------
  (A) TURETIM SONUCU : uretim fonksiyonunun dondurdugu renk "Siyah" mi.
  (B) KAPAK CAPASI   : turetim GERCEKTEN kapak gorselinden mi geliyor —
                       renkGorselIndeks["Siyah"] == 0 mi.
(B) olmadan (A) tek basina KANDIRILABILIR: renkGorselIndeks BOSALTILIRSA uretim
fonksiyonu "listenin ilki" koluna duser ve renkler[0] "Siyah" oldugu icin yine
"Siyah" dondurur — kapak gri olsa bile. O halde on-secim SABIT bir renge baglanmis,
kapak gorselinden KOPMUS olur. (B) tam olarak bu deligi kapatir ve bu kapinin
mutasyon bataryasinda AYRI bir kol olarak olculur.

FAIL YONU
---------
  * ihlal        -> KIRMIZI (cikis 1)
  * cozulemedi   -> OLCULEMEDI + KIRMIZI (cikis 1). "Cozemedim" ASLA yesil DEGILDIR.
  * konfigur alani olmayan urunler KAPSAM DISI (dokunulmaz, sayilir).

Calistir:  python3 tools/konfigur-siyah-kapak-kapisi.py   (0 = gecti, 1 = kaldi)
"""
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URUNLER = os.path.join(ROOT, "urunler.json")
BUILD = os.path.join(ROOT, "tools", "build.py")

BEKLENEN_RENK = "Siyah"

# 🔴 JETONLAR AYRIK: hicbiri digerinin ALT DIZESI DEGILDIR ([[maskeleme-kismi-kapatma]]).
# "ihlal YOK" gibi bir govde kullanmak pozitif kolu negatif kolun icine gomer ve
# pozitif kolu olduren mutant o ortak govdeden gecerdi.
JETON_TAM = "KONFIGUR_KAPAK_TAM"
JETON_IHLAL = "KONFIGUR_KAPAK_IHLAL"
JETON_OLCULEMEDI = "OLCULEMEDI"


def uretim_turetimi():
    """(fn, sebep) — sayfayi basan GERCEK fonksiyon. Cozulemezse (None, sebep)."""
    if not os.path.isfile(BUILD):
        return None, "tools/build.py bulunamadi (%s)" % BUILD
    try:
        spec = importlib.util.spec_from_file_location("build_konfigur_kapak", BUILD)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:                                       # noqa: BLE001
        return None, "tools/build.py yuklenemedi (%s: %s)" % (type(e).__name__, e)
    fn = getattr(mod, "_konfigur_varsayilan_renk", None)
    if not callable(fn):
        return None, ("build.py'de _konfigur_varsayilan_renk YOK — on-secim turetimi "
                      "tasinmis/yeniden adlandirilmis olabilir")
    return fn, None


def urun_hukmu(u, turet):
    """-> (durum, sebep); durum: TAM | IHLAL | OLCULEMEDI."""
    k = u.get("konfigur")
    renkler = k.get("renkler")
    rgi = k.get("renkGorselIndeks")
    g = u.get("gorseller")

    if not isinstance(renkler, list) or not renkler:
        return "OLCULEMEDI", "konfigur.renkler yok / liste degil"
    if not isinstance(rgi, dict):
        return "OLCULEMEDI", "konfigur.renkGorselIndeks yok / obje degil"
    if not isinstance(g, list) or not g:
        return "OLCULEMEDI", "gorseller yok / bos"

    try:
        renk = turet(k)
    except Exception as e:                                       # noqa: BLE001
        return "OLCULEMEDI", "uretim fonksiyonu patladi (%s: %s)" % (type(e).__name__, e)
    if renk is None:
        return "OLCULEMEDI", "uretim fonksiyonu renk TURETEMEDI (None)"

    # EKSEN A — turetim sonucu
    if renk != BEKLENEN_RENK:
        return "IHLAL", ("onden secili renk '%s' (beklenen '%s') — kapak gorseli "
                         "'%s' rengine ait" % (renk, BEKLENEN_RENK, renk))

    # EKSEN B — turetim GERCEKTEN kapak gorselinden mi geliyor
    ix = rgi.get(BEKLENEN_RENK)
    if ix != 0:
        return "IHLAL", ("'%s' turedi ama KAPAK CAPASI YOK: renkGorselIndeks['%s']=%r "
                         "(0 olmali). On-secim kapak gorselinden KOPMUS, sabit renge "
                         "baglanmis." % (BEKLENEN_RENK, BEKLENEN_RENK, ix))
    return "TAM", "renkGorselIndeks['%s']=0 -> kapak gorseli gerceken siyah" % BEKLENEN_RENK


def denetle(urunler, turet):
    """-> (ozet_satir, ihlaller, olculemeyenler, tam_sayisi)."""
    tam, ihlal, olculemedi = [], [], []
    for u in urunler:
        if not isinstance(u, dict) or not isinstance(u.get("konfigur"), dict):
            continue                                   # KAPSAM DISI
        durum, sebep = urun_hukmu(u, turet)
        kayit = (u.get("id"), sebep)
        if durum == "TAM":
            tam.append(kayit)
        elif durum == "IHLAL":
            ihlal.append(kayit)
        else:
            olculemedi.append(kayit)

    kapsam = len(tam) + len(ihlal) + len(olculemedi)
    if olculemedi:
        satir = ("konfigur on-secim %s: %d/%d urun COZULEMEDI — hukum VERILMEDI "
                 "('cozemedim = gecti' sessiz gecisi YASAK)"
                 % (JETON_OLCULEMEDI, len(olculemedi), kapsam))
    elif ihlal:
        satir = ("konfigur on-secim %s: %d/%d urunde onden secili renk '%s' DEGIL"
                 % (JETON_IHLAL, len(ihlal), kapsam, BEKLENEN_RENK))
    else:
        satir = ("konfigur on-secim %s: %d/%d urunde onden secili renk '%s' ve kapak "
                 "capasi yerinde" % (JETON_TAM, len(tam), kapsam, BEKLENEN_RENK))
    return satir, ihlal, olculemedi, len(tam)


def main():
    turet, sebep = uretim_turetimi()
    if turet is None:
        print("KONFIGUR SIYAH KAPAK KAPISI")
        print("  %s: uretim turetimi cozulemedi — %s" % (JETON_OLCULEMEDI, sebep))
        print("SONUC: KIRMIZI ❌ (hukum VERILMEDI; 'gecti' DENMEZ)")
        return 1
    try:
        with open(URUNLER, encoding="utf-8") as f:
            urunler = json.load(f)
    except (OSError, ValueError) as e:
        print("KONFIGUR SIYAH KAPAK KAPISI")
        print("  %s: urunler.json okunamadi/ayristirilamadi (%s)" % (JETON_OLCULEMEDI, e))
        print("SONUC: KIRMIZI ❌ (hukum VERILMEDI)")
        return 1

    satir, ihlal, olculemedi, tam = denetle(urunler, turet)
    print("KONFIGUR SIYAH KAPAK KAPISI")
    print("  katalog          : %s (%d kayit)" % (URUNLER, len(urunler)))
    print("  turetim kaynagi  : tools/build.py::_konfigur_varsayilan_renk (URETIM KODU)")
    print("  kapsamdaki urun  : %d (konfigur alani tasiyan)" % (tam + len(ihlal) + len(olculemedi)))
    print("  on-secim '%s'  : %d" % (BEKLENEN_RENK, tam))
    print("  " + satir)
    for pid, s in olculemedi:
        print("    OLCULEMEDI %s :: %s" % (pid, s))
    for pid, s in ihlal:
        print("    IHLAL      %s :: %s" % (pid, s))
    print("-" * 70)
    if ihlal or olculemedi:
        print("SONUC: KIRMIZI ❌  (ihlal %d · olculemedi %d)" % (len(ihlal), len(olculemedi)))
        return 1
    print("SONUC: YESIL ✅ — konfigur urunlerinin TAMAMINDA onden secili renk '%s' ve "
          "turetim kapak gorseline capali." % BEKLENEN_RENK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
