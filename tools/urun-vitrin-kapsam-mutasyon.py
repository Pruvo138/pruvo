#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUTASYON BATARYASI — urun sayfasi / kart ayrimini koruyan kapi CANLI mi?

    python3 tools/urun-vitrin-kapsam-mutasyon.py      (0 = gecti, 1 = kaldi)

NE KORUNUYOR (isletme karari, 11 Agu — Okan)
════════════════════════════════════════════════════════════════════════════════
  * URUN SAYFASI : onerilen malzeme onden secili; vurgulanan tutar ONDAN turer.
  * KART/BESLEME/MARKUP : BASLANGIC tabaninda KALIR (Okan bunu acikca secti; kartin
    yukselmesi REDDEDILEN davranistir).
  * Bu iki kol ayni cekirdegi cagirir ama AYRI anahtarlara baglidir.

Bu batarya, tools/d1-fiyat-parite-kapisi.py'nin bu ayrimi GERCEKTEN olctugunu kanitlar:
kaynaklar BELLEKTE bozulur, kapi yeniden kosar ve rengi olculur. Kapi olmusse bozulmus
kaynak YESIL yanar ve batarya bunu KIRMIZI raporlar.

🔴 DISKE HICBIR MUTASYON YAZILMAZ ([[mutasyon-bytecode-onbellegi]]): Python hedefleri
`exec(compile(src, ...), types.ModuleType(...).__dict__)` ile bellekte kosar — .py dosyasi
olusmadigi icin CPython ne __pycache__ yazar ne okur. JS/HTML hedefleri kapinin kendi
STDIN'li kosucusuna METIN olarak gecer. Kosum sonunda canli dosyalarin sha256'si
bas = son karsilastirilir.

🔴 JETONLAR/CAPALAR AYRIK ([[maskeleme-kismi-kapatma]]): her mutant KENDI satirini hedefler
ve uygulanma UCU DE olculur — capa TAM 1 kez geciyor mu · eski metin gitti mi · yeni metin
geldi mi. Capa tutmazsa mutant "CAPA YOK" ile SAPMA sayilir (sessizce atlanmaz).

🔴 IKI KONTROL VARDIR ([[beyan-edilmis-survivor]]):
  M0  davranisi degistirmeyen yeniden adlandirma -> YESIL kalmali. Kalmazsa kapi "her
      degisiklikte kirmizi" demektir ve hicbir sey olcmuyordur.
  M9  FAIL-OPEN ISPATI: girdi ZEHIRLI iken kapinin hukum fonksiyonu yutucuya cevrilir ->
      YESIL bekleniyor. Bu bir "kapi saglam" iddiasi DEGIL, o hukum satirlarinin YUK
      TASIDIGININ kanitidir (M3 ayni zehirle KIRMIZI yaniyor; ikisi bir CIFTTIR).
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import types

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

KAPI_YOL = os.path.join(TOOLS, "d1-fiyat-parite-kapisi.py")
HEDEF_DOSYALAR = {
    "secenekler": os.path.join(ROOT, "secenekler.js"),
    "index": os.path.join(ROOT, "index.html"),
    "d1sync": os.path.join(TOOLS, "d1-sync.py"),
    "build": os.path.join(TOOLS, "build.py"),
    "filament": os.path.join(TOOLS, "filament_ortak.py"),
    "kapi": KAPI_YOL,
}


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ═══════════════════════════════════════════════════════════ ZEHIRLER (girdi bozma)
# Zehir = kapinin GORMESI GEREKEN gercek dunya arizasi. Mutasyondan farki: kaynak
# kodun mantigini degil, kapinin OLCTUGU DURUMU bozar.
ZEHIRLER = {
    "vitrin": ("secenekler",
               "var ONERI_VITRIN_ACIK = false;",
               "var ONERI_VITRIN_ACIK = true;"),
    "kenar": ("d1sync",
              'q(u.get("fiyat") or "")',
              'q(_turetilmis_fiyat(u))'),
}

# ═══════════════════════════════════════════════════════════ MUTANTLAR
# (kod, aciklama, zehir, [(hedef, eski, yeni)], beklenen_rc)
MUTANTLAR = [
    ("M0", "KONTROL: davranisi degistirmeyen yeniden adlandirma", None,
     [("build",
       'def fiziksel_mi(p):\n    return bool(p) and p.get("tur") == TUR_FIZIKSEL',
       'def fiziksel_mi(kayit):\n    return bool(kayit) and kayit.get("tur") == TUR_FIZIKSEL')],
     0),

    ("M1", "bayrak ACIKKEN on-secim tabana sabitlendi (cip hep PLA)", None,
     [("build",
       "    return on_secim_tani(p)[1]",
       "    return VARSAYILAN_MALZEME")],
     1),

    ("M2", "ilan tutari CIPTEN AYRI turedi (sessiz zam/indirim)", None,
     [("build",
       "    return _birim_kurus(p, on_secim_malzeme(p))",
       "    return _birim_kurus(p, VARSAYILAN_MALZEME)")],
     1),

    ("M3", "KART DA YUKSELDI — kapsam sizintisi (Okan'in REDDETTIGI davranis)",
     "vitrin", [], 1),

    ("M4", "kart yuzeyi URUN SAYFASI turetmesini cagiriyor", None,
     [("index",
       "    if(!PRUVO_SECENEK.ONERI_VITRIN_ACIK || !PRUVO_SECENEK.vitrinBirimKurus)"
       "{ return p.fiyat; }",
       "    if(!PRUVO_SECENEK.ONERI_ONSECIM_ACIK || !PRUVO_SECENEK.ilanBirimKurus)"
       "{ return p.fiyat; }")],
     1),

    ("M5", "markup URUN SAYFASI koluna baglandi (dis listeleme sessizce zamlandi)", None,
     [("build",
       "    if ONERI_VITRIN_ACIK and pnum:",
       "    if ONERI_ONSECIM_ACIK and pnum:")],
     1),

    ("M6", "TANINMAYAN malzeme sessizce 'varsayilan'a cokuyor", None,
     [("filament",
       "    return ((TANI_TANINMAYAN if onerili else TANI_VARSAYILAN), guvenli)",
       "    return (TANI_VARSAYILAN, guvenli)")],
     1),

    ("M7", "kenar kolonu HAM alani birakti (kiyas tabani sessizce kaydi)",
     "kenar", [], 1),

    ("M8", "AZALTICI SOKULDU: taban secenegin tutari sayfadan kalkti", None,
     [("build",
       '    if p.get("parametrik") or p.get("konfigur"):\n        return None\n'
       "    return _birim_kurus(p, malzeme)",
       "    return None")],
     1),

    ("M10", "BILINCLI SECIM NOTU SOKULDU (sapan secim sessizce gecer)", None,
     [("build",
       "    if tani == filament_ortak.TANI_ONERI:",
       "    if False:")],
     1),

    ("M11", "NOT HER SECIMDE GORUNUYOR (yanlis-pozitif gurultu)", None,
     [("build",
       "oneriNot.hidden = !(_o && seciliMalzeme && seciliMalzeme !== _o);",
       "oneriNot.hidden = false;")],
     1),

    ("M9", "FAIL-OPEN ISPATI: zehirli girdi + hukum fonksiyonu yutucu (CIFT: M3)",
     "vitrin",
     [("kapi",
       'def kontrol(kosul, mesaj):\n    print(("  ✅ " if kosul else "  ❌ ") + mesaj)\n'
       "    if not kosul:\n        HATALAR.append(mesaj)\n    return bool(kosul)",
       'def kontrol(kosul, mesaj):\n    print(("  ✅ " if kosul else "  ❌ ") + mesaj)\n'
       "    return bool(kosul)")],
     0),
]


# ═══════════════════════════════════════════════════════════ kosum altyapisi
def _uygula(kaynaklar, hedef, eski, yeni):
    """(ok, mesaj) — capa TAM 1 kez gecmeli; eski gitmeli, yeni gelmeli."""
    src = kaynaklar[hedef]
    n = src.count(eski)
    if n != 1:
        return (False, "capa %d kez gecti (1 olmali): %r" % (n, eski[:70]))
    yeni_src = src.replace(eski, yeni, 1)
    if eski in yeni_src and eski != yeni:
        return (False, "eski metin hala duruyor")
    if yeni not in yeni_src:
        return (False, "yeni metin yerlesmedi")
    kaynaklar[hedef] = yeni_src
    return (True, "ok")


def _modul(ad, src, yol):
    m = types.ModuleType(ad)
    m.__file__ = yol
    sys.modules[ad] = m
    exec(compile(src, yol, "exec"), m.__dict__)
    return m


def _kos(kaynaklar, fikstur):
    """Kapiyi verilen KAYNAK METINLERIYLE kosar; rc doner. Diske yazmaz."""
    onceki = {ad: sys.modules.get(ad)
              for ad in ("filament_ortak", "build", "_kapi_mut")}
    try:
        _modul("filament_ortak", kaynaklar["filament"], HEDEF_DOSYALAR["filament"])
        build_mod = _modul("build", kaynaklar["build"], HEDEF_DOSYALAR["build"])
        kapi = _modul("_kapi_mut", kaynaklar["kapi"], KAPI_YOL)
        yut = io.StringIO()
        with contextlib.redirect_stdout(yut):
            rc, _ozet = kapi.olc(kaynaklar["secenekler"], kaynaklar["index"],
                                 kaynaklar["d1sync"], kaynaklar["build"],
                                 fikstur["urunler"], fikstur["ref"], fikstur["urun"],
                                 fikstur["kosucu"], build_mod)
        return (rc, None)
    except Exception as e:                              # noqa: BLE001
        return (None, "%s: %s" % (type(e).__name__, e))
    finally:
        for ad, mod in onceki.items():
            if mod is None:
                sys.modules.pop(ad, None)
            else:
                sys.modules[ad] = mod


def main():
    bas_sha = {ad: _sha(y) for ad, y in HEDEF_DOSYALAR.items()}
    temiz = {ad: _oku(y) for ad, y in HEDEF_DOSYALAR.items()}

    with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    # Referans dosyasi mutasyon hedefi DEGIL: gercek referanstan okunur.
    fo = _modul("_fo_temiz", temiz["filament"], HEDEF_DOSYALAR["filament"])
    gecici = tempfile.mkdtemp(prefix="kapsam-mut-")
    sapan = []
    try:
        fikstur = {"urunler": urunler,
                   "ref": os.path.join(gecici, "ref.json"),
                   "urun": os.path.join(gecici, "urunler.json"),
                   "kosucu": os.path.join(gecici, "kosucu.js")}
        with open(fikstur["ref"], "w", encoding="utf-8") as f:
            json.dump(fo.referans(), f, ensure_ascii=False)
        with open(fikstur["urun"], "w", encoding="utf-8") as f:
            json.dump(urunler, f, ensure_ascii=False)
        kapi_temiz = _modul("_kapi_temiz", temiz["kapi"], KAPI_YOL)
        with open(fikstur["kosucu"], "w", encoding="utf-8") as f:
            f.write(kapi_temiz.JS_KOSUCU)

        print("MUTASYON BATARYASI — urun sayfasi / kart ayrimi kapisi")
        print("hedefler: " + " · ".join(sorted(HEDEF_DOSYALAR)))

        # ---- TABAN: bozulmamis kaynakla kapi YESIL mi? (yoksa hicbir olcum anlamli degil)
        rc0, hata0 = _kos(dict(temiz), fikstur)
        print("\nTABAN KOSUM (bozulmamis kaynak): rc=%s %s"
              % (rc0, "" if rc0 == 0 else ("HATA: %s" % hata0)))
        if rc0 != 0:
            print("TABAN KIRMIZI — mutasyon olcumu anlamsiz olurdu, DURDURULDU.")
            return 1

        print("\n%-4s %-62s %-9s %-9s %s"
              % ("KOD", "MUTANT", "BEKLENEN", "OLCULEN", "SONUC"))
        for kod, aciklama, zehir, mutasyonlar, beklenen in MUTANTLAR:
            kaynaklar = dict(temiz)
            capa_hata = None
            if zehir:
                h, e, y = ZEHIRLER[zehir]
                ok, mesaj = _uygula(kaynaklar, h, e, y)
                if not ok:
                    capa_hata = "zehir(%s) %s" % (zehir, mesaj)
            for hedef, eski, yeni in mutasyonlar:
                if capa_hata:
                    break
                ok, mesaj = _uygula(kaynaklar, hedef, eski, yeni)
                if not ok:
                    capa_hata = "%s: %s" % (hedef, mesaj)
            if capa_hata:
                sapan.append("%s: CAPA YOK — %s" % (kod, capa_hata))
                print("%-4s %-62s %-9s %-9s CAPA YOK"
                      % (kod, aciklama[:62], beklenen, "-"))
                continue
            rc, hata = _kos(kaynaklar, fikstur)
            if rc is None:
                sapan.append("%s: kosum dustu — %s" % (kod, hata))
                renk = "DUSTU"
            else:
                renk = {0: "YESIL", 1: "KIRMIZI", 2: "OLCULEMEDI"}.get(rc, "rc=%d" % rc)
            tamam = (rc == beklenen)
            if not tamam and rc is not None:
                sapan.append("%s: beklenen rc=%d, olculen rc=%s" % (kod, beklenen, rc))
            print("%-4s %-62s %-9s %-9s %s"
                  % (kod, aciklama[:62], {0: "YESIL", 1: "KIRMIZI"}.get(beklenen, beklenen),
                     renk, "OK" if tamam else "SAPTI"))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    son_sha = {ad: _sha(y) for ad, y in HEDEF_DOSYALAR.items()}
    degisen = [ad for ad in bas_sha if bas_sha[ad] != son_sha[ad]]
    if degisen:
        sapan.append("CANLI DOSYA DEGISTI (mutasyon diske sizdi): %s" % ", ".join(degisen))
    else:
        print("\nDISK TEMIZ: %d hedef dosyanin sha256'si bas = son (mutasyon diske YAZILMADI)"
              % len(bas_sha))

    kirmizi_beklenen = sum(1 for m in MUTANTLAR if m[4] == 1)
    if sapan:
        print("\nSAPMA (%d):" % len(sapan))
        for s in sapan:
            print("  - " + s)
        return 1
    print("\nOK: %d mutantin hepsi beklenen rengi verdi "
          "(%d KIRMIZI + M0 kontrol YESIL + M9 fail-open ispati YESIL)."
          % (len(MUTANTLAR), kirmizi_beklenen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
