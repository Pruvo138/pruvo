#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/ata-lisans-kapisi.py (ATA ZINCIRI lisans kapisi).

DAVRANISSAL + AGSIZ. Butun host/kimlik/lisanslar UYDURMADIR (".example" TLD'si RFC 2606 ile
ayrilmistir; gercek bir kaynak platformu isaret etmez). Fikstur SEKLI gercek cikti seklini
taklit eder: ata referansi {link: <dolu>, license: <BOS>, designId: 0} — dort canli emsalde
olculen desen budur (lisans turevin JSON'unda GORUNMEZ; tek sinyal serbest-metin link).

OLCULEN IDDIALAR:
  POZITIF      : ata NC -> ihlal YAKALANIR (rc 1).
  NEGATIF      : ata CC-BY / CC0 -> ihlal YOK (rc 0); ata alani OLMAYAN kayit (metinde
                 benzer URL gecse bile) TETIKLEMEZ — yanlis-pozitif tum ekibin yayinini durdurur.
  FAIL-CLOSED  : adaptorsuz host · API null · API 403 -> ucu de rc != 0 (ASLA yesil).
  GECICI/KALICI: API 429 GECICI (rc 2, yeniden denenebilir) ve KALICI'dan AYRI raporlanir.
  AYIRT EDICI  : AYNI ata kimligi, FARKLI host -> hukum DEGISIR. Host okunmazsa YESIL,
                 okunursa KIRMIZI. Kapinin gercekten YENI eksen olctugunun kaniti.
  SIKI YON     : ata referansindaki gomulu lisans DOLU ve NC ise ag'a cikmadan ihlal;
                 turevin kendini "CC0" diye yeniden lisanslamasi hukmu DEGISTIRMEZ.
  VERI YAZMAZ  : kapi kosumundan once/sonra veri dosyalarinin sha256'si ESIT.

MUTASYON SURUCUSU (kanit repoda durur, anlatilmaz):  python3 tools/ata-lisans-mutasyon.py

Kosum:  python3 tools/ata-lisans-test.py
"""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_KAPI_YOL = os.path.join(_HERE, "ata-lisans-kapisi.py")
_spec = importlib.util.spec_from_file_location("ata_lisans_kapisi", _KAPI_YOL)
K = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(K)

# --------------------------------------------------------------- UYDURMA defter
# alfa ve beta AYNI kimligi (7788) TASIR ama lisanslari ZITTIR -> host ekseni load-bearing.
ADAPTORLER = [
    {"ad": "alfa", "hostlar": ["ata-alfa.example"], "kimlik": "bas-sayi:models",
     "ata_destegi": True,
     "detaylar": {
         "7788": {"license": "Creative Commons - Attribution"},
         "4410": {"license": "Creative Commons - Attribution - Non-Commercial - Share Alike"},
         "5500": {"license": "Creative Commons - Public Domain Dedication"},
         "6600": {"license": ""},
         "9001": "__GECICI__",
         "9002": "__KALICI__",
         "9003": None,
     }},
    {"ad": "beta", "hostlar": ["ata-beta.example"], "kimlik": "bas-sayi:models",
     "ata_destegi": True,
     "detaylar": {
         "7788": {"license": "Creative Commons - Attribution - Non-Commercial"},
     }},
]


def _ata(link, license_="", design_id=0):
    """Gercek cikti sekli: license BOS, designId 0, link DOLU."""
    return {"link": link, "license": license_, "designId": design_id}


def _detay(*atalar, **kw):
    d = {"license": kw.get("kendi_lisansi", "CC0"), "title": "uydurma-turev"}
    if atalar:
        d["originals"] = list(atalar)
    if kw.get("metin"):
        d["description"] = kw["metin"]
    return d


# (ad, detay JSON, beklenen durum, beklenen tekil rc)
SENARYOLAR = [
    ("POZITIF: ata NC-SA (canli emsal deseni: license BOS + designId 0)",
     _detay(_ata("https://ata-alfa.example/models/4410-parca")),
     K.DURUM_IHLAL, 1),

    ("POZITIF: turev kendini CC0 ilan etse de ata NC -> ihlal",
     _detay(_ata("https://ata-alfa.example/models/4410-parca"), kendi_lisansi="CC0"),
     K.DURUM_IHLAL, 1),

    ("NEGATIF: ata CC-BY -> ihlal YOK",
     _detay(_ata("https://ata-alfa.example/models/7788-parca")),
     K.DURUM_SATILABILIR, 0),

    ("NEGATIF: ata CC0 (public domain) -> ihlal YOK",
     _detay(_ata("https://ata-alfa.example/models/5500-parca")),
     K.DURUM_SATILABILIR, 0),

    ("NEGATIF: ata alani YOK — metinde benzer URL gecse bile TETIKLEMEZ (yanlis-pozitif kapisi)",
     _detay(metin="kaynak: https://ata-alfa.example/models/4410-parca adresinden esinlenildi"),
     K.DURUM_ATA_YOK, 0),

    ("AYIRT EDICI: AYNI kimlik (7788) FARKLI host (beta) -> NC -> IHLAL",
     _detay(_ata("https://ata-beta.example/models/7788-parca")),
     K.DURUM_IHLAL, 1),

    ("FAIL-CLOSED: adaptorsuz host -> ELLE-BAK, ASLA yesil",
     _detay(_ata("https://ata-yabanci.example/model/12-parca")),
     K.DURUM_ADAPTORSUZ, 1),

    ("FAIL-CLOSED: API null -> KALICI (eskalasyon)",
     _detay(_ata("https://ata-alfa.example/models/9003-parca")),
     K.DURUM_KALICI, 1),

    ("FAIL-CLOSED: API 403 -> KALICI (eskalasyon)",
     _detay(_ata("https://ata-alfa.example/models/9002-parca")),
     K.DURUM_KALICI, 1),

    ("AYRIM: API 429 -> GECICI (yeniden denenebilir), KALICI DEGIL",
     _detay(_ata("https://ata-alfa.example/models/9001-parca")),
     K.DURUM_GECICI, 2),

    ("FAIL-CLOSED: ata lisansi BOS dondu -> KALICI",
     _detay(_ata("https://ata-alfa.example/models/6600-parca")),
     K.DURUM_KALICI, 1),

    ("FAIL-CLOSED: ata referansinda link YOK -> host okunamaz -> KALICI",
     _detay(_ata("")),
     K.DURUM_KALICI, 1),

    ("SIKI YON: gomulu lisans NC ise link satilabilir olsa da IHLAL",
     _detay(_ata("https://ata-alfa.example/models/7788-parca",
                 license_="Creative Commons - Attribution - Non-Commercial")),
     K.DURUM_IHLAL, 1),

    ("NEGATIF: gomulu lisans satilabilir ise hukum VERILMEZ, host yine cozulur (ata CC-BY)",
     _detay(_ata("https://ata-alfa.example/models/7788-parca",
                 license_="Creative Commons - Attribution")),
     K.DURUM_SATILABILIR, 0),

    ("FAIL-CLOSED: gomulu lisans temiz ama ata NC -> host cozumu ihlali yakalar",
     _detay(_ata("https://ata-alfa.example/models/4410-parca",
                 license_="Creative Commons - Attribution")),
     K.DURUM_IHLAL, 1),
]


def _fikstur_yaz(dizin, ad, detaylar):
    yol = os.path.join(dizin, ad)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump({"adaptorler": ADAPTORLER,
                   "kayitlar": {k: {} for k in detaylar},
                   "detaylar": detaylar}, f)
    return yol


def _sha(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        blok = f.read(1 << 20)
        while blok:
            h.update(blok)
            blok = f.read(1 << 20)
    return h.hexdigest()


def _veri_dosyalari():
    """Kapinin ASLA yazmamasi gereken veri dosyalari (var olanlar)."""
    kok = K._veri_kok()
    adaylar = [os.path.join(kok, "urunler.json"),
               os.path.join(kok, ".urun-kaynaklari.json")]
    return [p for p in adaylar if os.path.exists(p)]


def main():
    defter = K.sentetik_defter(ADAPTORLER)
    hatalar = []
    n = 0

    # --- 1) senaryo bazli davranis ---
    for ad, detay, beklenen_durum, beklenen_rc in SENARYOLAR:
        n += 1
        sonuclar = K.kayit_yargi("uydurma-urun-%d" % n, detay, defter, K.genel_satilabilir)
        durum = sonuclar[0]["durum"] if sonuclar else "(sonuc yok)"
        rc = K.cikis_kodu(sonuclar)
        ok = (durum == beklenen_durum and rc == beklenen_rc)
        if not ok:
            hatalar.append("%s -> durum=%s (bek %s) rc=%s (bek %s)"
                           % (ad, durum, beklenen_durum, rc, beklenen_rc))
        print("  %-4s %-96s durum=%-22s rc=%s"
              % ("ok" if ok else "HATA", ad[:96], durum, rc))

    # --- 2) GECICI ile KALICI AYRI (ayni kova degil) ---
    n += 1
    g = K.kayit_yargi("u-g", _detay(_ata("https://ata-alfa.example/models/9001-parca")),
                      defter, K.genel_satilabilir)[0]
    k = K.kayit_yargi("u-k", _detay(_ata("https://ata-alfa.example/models/9002-parca")),
                      defter, K.genel_satilabilir)[0]
    ok = (g["durum"] != k["durum"] and K.cikis_kodu([g]) == 2 and K.cikis_kodu([k]) == 1)
    if not ok:
        hatalar.append("GECICI/KALICI ayrimi yok: %s vs %s" % (g["durum"], k["durum"]))
    print("  %-4s GECICI(rc2) ile KALICI(rc1) AYRI raporlaniyor" % ("ok" if ok else "HATA"))

    # --- 3) toplu rc: ihlal, gecici'yi bastirir; temiz kume 0 ---
    n += 1
    temiz = [K.kayit_yargi("t%d" % i, _detay(_ata("https://ata-alfa.example/models/7788-p")),
                           defter, K.genel_satilabilir)[0] for i in range(3)]
    ok = (K.cikis_kodu(temiz) == 0
          and K.cikis_kodu(temiz + [g]) == 2
          and K.cikis_kodu(temiz + [g, k]) == 1)
    if not ok:
        hatalar.append("toplu rc birlesimi yanlis")
    print("  %-4s toplu rc: temiz=0 · +gecici=2 · +kalici=1" % ("ok" if ok else "HATA"))

    # --- 4) UCTAN UCA CLI: rc 0 / 1 / 2 ve VERI YAZMAZ ---
    oncesi = [(p, _sha(p)) for p in _veri_dosyalari()]
    if not oncesi:
        hatalar.append("veri dosyasi bulunamadi -> YAZMAZ iddiasi OLCULEMEDI")
        print("  HATA veri dosyasi yok -> 'yazmaz' iddiasi OLCULEMEDI")
    with tempfile.TemporaryDirectory() as tmp:
        kumeler = [
            ("temiz", {"a": _detay(_ata("https://ata-alfa.example/models/7788-p"))}, 0),
            ("ihlal", {"a": _detay(_ata("https://ata-alfa.example/models/4410-p"))}, 1),
            ("gecici", {"a": _detay(_ata("https://ata-alfa.example/models/9001-p"))}, 2),
        ]
        for ad, detaylar, beklenen in kumeler:
            n += 1
            yol = _fikstur_yaz(tmp, "fx-%s.json" % ad, detaylar)
            r = subprocess.run([sys.executable, _KAPI_YOL, "--fikstur", yol],
                               capture_output=True, text=True)
            ok = (r.returncode == beklenen)
            if not ok:
                hatalar.append("CLI %s: rc=%d (bek %d)\n%s" % (ad, r.returncode, beklenen, r.stdout))
            print("  %-4s CLI --fikstur %-7s -> rc=%d (bek %d)"
                  % ("ok" if ok else "HATA", ad, r.returncode, beklenen))

        # ELLE-BAK kuyrugu raporda GORUNUYOR mu (sessizce gecirmeme kanidi)
        n += 1
        yol = _fikstur_yaz(tmp, "fx-elle.json",
                           {"a": _detay(_ata("https://ata-yabanci.example/model/12-p"))})
        r = subprocess.run([sys.executable, _KAPI_YOL, "--fikstur", yol],
                           capture_output=True, text=True)
        ok = (r.returncode == 1 and "ELLE-BAK KUYRUGU" in r.stdout
              and "ata-yabanci.example" in r.stdout)
        if not ok:
            hatalar.append("adaptorsuz host ELLE-BAK kuyruguna dusmedi (rc=%d)" % r.returncode)
        print("  %-4s adaptorsuz host raporda ELLE-BAK kuyrugunda" % ("ok" if ok else "HATA"))

    n += 1
    sonrasi = [(p, _sha(p)) for p, _ in oncesi]
    ok = (oncesi == sonrasi) and bool(oncesi)
    if not ok and oncesi:
        hatalar.append("KAPI VERI YAZDI — sha256 degisti")
    print("  %-4s kapi VERI YAZMADI (%d dosya, sha256 esit)"
          % ("ok" if ok else "HATA", len(oncesi)))

    # --- 5) oz-denetim kolu da yesil mi ---
    n += 1
    r = subprocess.run([sys.executable, _KAPI_YOL, "--kendini-test"],
                       capture_output=True, text=True)
    ok = (r.returncode == 0)
    if not ok:
        hatalar.append("--kendini-test rc=%d" % r.returncode)
    print("  %-4s --kendini-test rc=0" % ("ok" if ok else "HATA"))

    print("")
    if hatalar:
        print("BASARISIZ — %d iddia yanlis:" % len(hatalar))
        for h in hatalar:
            print("  x %s" % h)
        return 1
    print("TUM TESTLER GECTI (%d iddia)." % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
