#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/ata-lisans-kapisi.py (ATA ZINCIRI lisans kapisi).

DAVRANISSAL + AGSIZ. Butun host/kimlik/lisanslar UYDURMADIR (".example" TLD'si RFC 2606 ile
ayrilmistir; gercek bir kaynak platformu isaret etmez). Fikstur SEKLI gercek cikti seklini
taklit eder: ata referansi {link: <dolu>, license: <BOS>, designId: 0} — dort canli emsalde
olculen desen budur (lisans turevin JSON'unda GORUNMEZ; tek sinyal serbest-metin link).

🔴 D-BOLUMU (D1..D12): bagimsiz curutucunun olctugu SESSIZ GECISLER. Hepsi once rc=0 ile
geciyordu. Her D vakasinin bir OLDURUCU MUTANTI vardir (tools/ata-lisans-mutasyon.py);
mutant uygulaninca ilgili D iddiasi DUSER. Bu, "batarya kendi deligini gormuyor" hukmune
verilen cevaptir — batarya artik kendi korlugunu de olcer.

KORUNAN EKSENLER (curutucu dogruladi, bozulmamali):
  * yanlis-negatif 0 : NC hicbir yazimda gecmez (NC_YAZIMLARI tablosu).
  * fail-closed      : adaptorsuz · null · 403 · 429 · timeout · bozuk JSON · bos yanit.
  * VERI YAZMAZ      : kosum oncesi/sonrasi veri dosyalarinin sha256'si esit.

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
# turev: ata referansini BASAN platform (CC'yi CIPLAK yazan sozluk).
ADAPTORLER = [
    {"ad": "turev", "hostlar": ["turev-platform.example"], "kimlik": "bas-sayi:models",
     "yargi": "ciplak-cc", "ata_destegi": True, "detaylar": {}},

    {"ad": "alfa", "hostlar": ["ata-alfa.example"], "kimlik": "bas-sayi:models",
     "ata_destegi": True, "yargi": "genel",
     "detaylar": {
         "7788": {"license": "Creative Commons - Attribution"},
         "5500": {"license": "Creative Commons - Public Domain Dedication"},
         "4410": {"license": "Creative Commons - Attribution - Non-Commercial - Share Alike"},
         "6600": {"license": ""},
         "6601": {},                              # BOS detay -> fail-closed
         "6602": {"license": "Creative Commons - Attribution", "originals": 12345},
         "9001": "__GECICI__",
         "9002": "__KALICI__",
         "9003": None,
         "9004": "__TIMEOUT__",
         "9005": "__BOZUK__",
         # --- ZARF: ata alani ust duzeyde DEGIL, zarfin icinde ---
         "7001": {"data": {"license": "Creative Commons - Attribution",
                           "originals": [{"link": "https://ata-alfa.example/models/4410-x",
                                          "license": "", "designId": 0}]}},
         # --- IKI KADEME: BY ata, NC BUYUK ata ---
         "8001": {"license": "Creative Commons - Attribution",
                  "remixParents": [{"link": "https://ata-alfa.example/models/4410-x",
                                    "license": "", "designId": 0}]},
         # --- DERINLIK TAVANI ---
         "8100": {"license": "Creative Commons - Attribution",
                  "ancestors": [{"link": "https://ata-alfa.example/models/8101-x"}]},
         "8101": {"license": "Creative Commons - Attribution",
                  "ancestors": [{"link": "https://ata-alfa.example/models/8102-x"}]},
         "8102": {"license": "Creative Commons - Attribution",
                  "ancestors": [{"link": "https://ata-alfa.example/models/8103-x"}]},
         "8103": {"license": "Creative Commons - Attribution"},
         # --- DONGU ---
         "8200": {"license": "Creative Commons - Attribution",
                  "derivedFrom": [{"link": "https://ata-alfa.example/models/8200-x"}]},
     }},

    {"ad": "beta", "hostlar": ["ata-beta.example"], "kimlik": "bas-sayi:models",
     "ata_destegi": True, "yargi": "genel",
     "detaylar": {"7788": {"license": "Creative Commons - Attribution - Non-Commercial"}}},
]

# NC/tescilli hicbir yazimda gecmemeli (yanlis-negatif ekseni — KORU).
NC_YAZIMLARI = [
    "BY-NC", "BY-NC-SA", "BY-NC-ND", "CC-BY-NC", "CC BY-NC 4.0", "cc_by_nc",
    "Creative Commons - Attribution - Non-Commercial",
    "Attribution-NonCommercial 4.0 International",
    "Attribution - Non Commercial - Share Alike",
    "Creative Commons Noncommercial", "NonCommercial-NoDerivs",
    "Standard Digital File License", "Standard Digital File License - Community Use",
    "MakerWorld Exclusive License", "All Rights Reserved", "Personal Use Only",
    "Private Use", "OCL v1", "Official Content License", "Premium License",
    # --- VETO'nun AYIRT EDICI vakalari: alt sozluklerin HICBIRI bunlari yakalamaz
    #     ("attribution" jetonu yuzunden satilabilir derler); ticari kullanimi kapatan
    #     serbest-metin ibaresini YALNIZ veto gorur. Veto kalkarsa bunlar SIZAR.
    "Attribution 4.0 - not for commercial use",
    "Attribution - No Commercial Use",
    "Attribution - Premium License",
    "Attribution 4.0 - Official Content License",
    "",
]
# Gecerli lisanslar HER sozlukte satilabilir olmali (yanlis-pozitif ekseni).
GECERLI_YAZIMLAR = [
    "BY", "BY-SA", "BY-ND", "CC0", "CC-BY", "CC-BY-SA", "GPL 3.0", "LGPL", "BSD",
    "Creative Commons - Attribution", "Creative Commons Attribution 4.0",
    "Creative Commons - Attribution - Share Alike", "Attribution 4.0 International",
    "Creative Commons - Public Domain Dedication",
    "Attribution-ShareAlike 4.0 International",
]


def _ata(link, license_="", design_id=0):
    """Gercek cikti sekli: license BOS, designId 0, link DOLU."""
    return {"link": link, "license": license_, "designId": design_id}


def _detay(*atalar, **kw):
    d = {"license": kw.get("kendi_lisansi", "CC0"), "title": "uydurma-turev"}
    alan = kw.get("alan", "originals")
    if atalar:
        d[alan] = list(atalar)
    if kw.get("metin"):
        d["description"] = kw["metin"]
    return d


A_NC = "https://ata-alfa.example/models/4410-parca"
A_BY = "https://ata-alfa.example/models/7788-parca"

# (ad, detay, beklenen ilk durum, beklenen rc)
SENARYOLAR = [
    ("POZITIF: ata NC-SA (canli emsal deseni: license BOS + designId 0)",
     _detay(_ata(A_NC)), K.DURUM_IHLAL, 1),
    ("POZITIF: turev kendini CC0 ilan etse de ata NC -> ihlal",
     _detay(_ata(A_NC), kendi_lisansi="CC0"), K.DURUM_IHLAL, 1),
    ("NEGATIF: ata CC-BY -> ihlal YOK", _detay(_ata(A_BY)), K.DURUM_SATILABILIR, 0),
    ("NEGATIF: ata CC0 -> ihlal YOK",
     _detay(_ata("https://ata-alfa.example/models/5500-p")), K.DURUM_SATILABILIR, 0),
    ("NEGATIF: ata alani YOK, metinde benzer URL var (yanlis-pozitif kapisi)",
     _detay(metin="kaynak: %s adresinden esinlenildi" % A_NC), K.DURUM_ALAN_YOK, 0),
    ("AYIRT EDICI: AYNI kimlik (7788) FARKLI host (beta) -> NC -> IHLAL",
     _detay(_ata("https://ata-beta.example/models/7788-parca")), K.DURUM_IHLAL, 1),
    ("FAIL-CLOSED: adaptorsuz host -> ELLE-BAK",
     _detay(_ata("https://ata-yabanci.example/model/12-p")), K.DURUM_ADAPTORSUZ, 1),
    ("FAIL-CLOSED: API null -> KALICI",
     _detay(_ata("https://ata-alfa.example/models/9003-p")), K.DURUM_KALICI, 1),
    ("FAIL-CLOSED: API 403 -> KALICI",
     _detay(_ata("https://ata-alfa.example/models/9002-p")), K.DURUM_KALICI, 1),
    ("AYRIM: API 429 -> GECICI (rc 2), KALICI DEGIL",
     _detay(_ata("https://ata-alfa.example/models/9001-p")), K.DURUM_GECICI, 2),
    ("FAIL-CLOSED: ata lisansi BOS dondu -> KALICI",
     _detay(_ata("https://ata-alfa.example/models/6600-p")), K.DURUM_KALICI, 1),
    ("FAIL-CLOSED: ata referansinda link YOK -> KALICI", _detay(_ata("")), K.DURUM_KALICI, 1),
    ("SIKI YON: gomulu lisans NC ise link satilabilir olsa da IHLAL",
     _detay(_ata(A_BY, license_="Creative Commons - Attribution - Non-Commercial")),
     K.DURUM_IHLAL, 1),
    ("NEGATIF: gomulu lisans satilabilir ise hukum VERILMEZ, host yine cozulur",
     _detay(_ata(A_BY, license_="Creative Commons - Attribution")), K.DURUM_SATILABILIR, 0),
    ("POZITIF: gomulu temiz ama ata NC -> host cozumu ihlali yakalar",
     _detay(_ata(A_NC, license_="Creative Commons - Attribution")), K.DURUM_IHLAL, 1),
]

# ---- D-BOLUMU: curutucunun olctugu SESSIZ GECISLER (hepsi rc=0 ile geciyordu) ----
# (delik, ad, detay, beklenen rc, sonuclarda BULUNMASI gereken durum)
DELIKLER = [
    ("D1", "turev detayi None (404/silinmis/gizli) -> ata yok SAYILMAZ",
     None, 1, K.DURUM_KALICI),
    ("D2a", "ata alani 'remixParents' adiyla -> taranir",
     _detay(_ata(A_NC), alan="remixParents"), 1, K.DURUM_IHLAL),
    ("D2b", "ata alani 'derivedFrom' adiyla -> taranir",
     _detay(_ata(A_NC), alan="derivedFrom"), 1, K.DURUM_IHLAL),
    ("D2c", "ata alani 'ancestors' adiyla -> taranir",
     _detay(_ata(A_NC), alan="ancestors"), 1, K.DURUM_IHLAL),
    ("D2d", "ata alani 'originalDesigns' adiyla -> taranir",
     _detay(_ata(A_NC), alan="originalDesigns"), 1, K.DURUM_IHLAL),
    ("D2e", "ata alani 'remixOf' adiyla -> taranir",
     _detay(_ata(A_NC), alan="remixOf"), 1, K.DURUM_IHLAL),
    ("D3a", "ata alani LISTE degil DICT -> atlanmaz",
     {"license": "CC0", "originals": _ata(A_NC)}, 1, K.DURUM_IHLAL),
    ("D3b", "ata alani LISTE degil STRING -> atlanmaz",
     {"license": "CC0", "originals": A_NC}, 1, K.DURUM_IHLAL),
    ("D3c", "ata alani TANINMAYAN sekilde (sayi) -> fail-closed",
     {"license": "CC0", "originals": 12345}, 1, K.DURUM_KALICI),
    ("D3d", "turev detayi ZARFLI ({'data':{...}}) -> ata alani GORULUR",
     {"data": {"license": "CC0", "originals": [_ata(A_NC)]}}, 1, K.DURUM_IHLAL),
    ("D3e", "turev detayi BOS {} -> 'ata yok' SAYILMAZ", {}, 1, K.DURUM_KALICI),
    ("D4", "tek serbest-metin alanda IKI ata URL'si -> IKISI de cozulur",
     _detay(_ata("bkz %s ve %s" % (A_BY, A_NC))), 1, K.DURUM_IHLAL),
    ("D5a", "IKI KADEMELI zincir: ata BY, atanin atasi NC -> IHLAL",
     _detay(_ata("https://ata-alfa.example/models/8001-p")), 1, K.DURUM_IHLAL),
    ("D5b", "zincir DERINLIK TAVANI asilirsa fail-closed (sessiz gecis yok)",
     _detay(_ata("https://ata-alfa.example/models/8100-p")), 1, K.DURUM_KALICI),
    ("D5c", "zincir DONGUSU sonsuza girmez ve hukum uretir",
     _detay(_ata("https://ata-alfa.example/models/8200-p")), 0, K.DURUM_SATILABILIR),
    ("D5d", "ZARF ICINDEKI ata zinciri de yukari yurur (NC buyuk ata)",
     _detay(_ata("https://ata-alfa.example/models/7001-p")), 1, K.DURUM_IHLAL),
    ("D7", "okuma TIMEOUT -> GECICI (KALICI degil)",
     _detay(_ata("https://ata-alfa.example/models/9004-p")), 2, K.DURUM_GECICI),
    ("D11a", "ata detayi zarf sonrasi BOS -> KALICI",
     _detay(_ata("https://ata-alfa.example/models/6601-p")), 1, K.DURUM_KALICI),
    ("D11b", "ata detayindaki UST ata alani taninmayan sekilde -> KALICI",
     _detay(_ata("https://ata-alfa.example/models/6602-p")), 1, K.DURUM_KALICI),
    ("D12", "bozuk JSON -> KALICI (gecici DEGIL)",
     _detay(_ata("https://ata-alfa.example/models/9005-p")), 1, K.DURUM_KALICI),
]


def _fikstur_yaz(dizin, ad, detaylar, kayitlar=None):
    yol = os.path.join(dizin, ad)
    with open(yol, "w", encoding="utf-8") as f:
        json.dump({"adaptorler": ADAPTORLER,
                   "kayitlar": kayitlar or {k: {} for k in detaylar},
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
    kok = K._veri_kok()
    adaylar = [os.path.join(kok, "urunler.json"), os.path.join(kok, ".urun-kaynaklari.json")]
    return [p for p in adaylar if os.path.exists(p)]


def main():
    defter = K.sentetik_defter(ADAPTORLER)
    turev_ad = K.adaptor_bul("turev-platform.example", defter)
    hatalar = []
    n = 0
    sessiz_gecis = 0

    def _kos(detay, kaynak=None):
        return K.kayit_yargi("uydurma-urun", detay, defter, K.genel_satilabilir, kaynak)

    # --- 1) temel senaryolar ---
    for ad, detay, beklenen_durum, beklenen_rc in SENARYOLAR:
        n += 1
        sonuclar = _kos(detay)
        durum = sonuclar[0]["durum"] if sonuclar else "(sonuc yok)"
        rc = K.cikis_kodu(sonuclar)
        ok = (durum == beklenen_durum and rc == beklenen_rc)
        if rc == 0 and beklenen_rc != 0:
            sessiz_gecis += 1
        if not ok:
            hatalar.append("%s -> durum=%s (bek %s) rc=%s (bek %s)"
                           % (ad, durum, beklenen_durum, rc, beklenen_rc))
        print("  %-4s %-90s durum=%-22s rc=%s" % ("ok" if ok else "HATA", ad[:90], durum, rc))

    # --- 2) D-BOLUMU: sessiz gecis delikleri ---
    print("  --- D-BOLUMU (curutucunun olctugu sessiz gecisler) ---")
    for delik, ad, detay, beklenen_rc, beklenen_durum in DELIKLER:
        n += 1
        sonuclar = _kos(detay)
        rc = K.cikis_kodu(sonuclar)
        durumlar = [s["durum"] for s in sonuclar]
        ok = (rc == beklenen_rc and beklenen_durum in durumlar)
        if rc == 0 and beklenen_rc != 0:
            sessiz_gecis += 1
        if not ok:
            hatalar.append("%s %s -> rc=%s (bek %s) durumlar=%s (icinde bek %s)"
                           % (delik, ad, rc, beklenen_rc, durumlar, beklenen_durum))
        print("  %-4s %-5s %-84s rc=%s" % ("ok" if ok else "HATA", delik, ad[:84], rc))

    # --- 3) SOZLUK EKSENI ---
    print("  --- SOZLUK EKSENI (yanlis-negatif / yanlis-pozitif) ---")
    n += 1
    yn = [x for x in NC_YAZIMLARI if K.coklu_sozluk_satilabilir(x, turev_ad)]
    ok = not yn
    if not ok:
        hatalar.append("YANLIS-NEGATIF: NC/tescilli gecti -> %s" % yn)
    print("  %-4s yanlis-negatif %d/%d (NC/tescilli hicbir yazimda gecmiyor)"
          % ("ok" if ok else "HATA", len(yn), len(NC_YAZIMLARI)))

    n += 1
    yp = [x for x in GECERLI_YAZIMLAR if not K.coklu_sozluk_satilabilir(x, turev_ad)]
    ok = not yp
    if not ok:
        hatalar.append("YANLIS-POZITIF: gecerli lisans satilamaz sanildi -> %s" % yp)
    print("  %-4s yanlis-pozitif %d/%d (gecerli yazimlarin hepsi satilabilir)"
          % ("ok" if ok else "HATA", len(yp), len(GECERLI_YAZIMLAR)))

    n += 1
    gomulu_yp = [x for x in GECERLI_YAZIMLAR
                 if K.cikis_kodu(_kos(_detay(_ata(A_BY, license_=x)), turev_ad)) != 0]
    ok = not gomulu_yp
    if not ok:
        hatalar.append("D6 gomulu alan yanlis-pozitif -> %s" % gomulu_yp)
    print("  %-4s D6    gomulu alanda %d gecerli yazimin hicbiri IHLAL damgasi yemiyor"
          % ("ok" if ok else "HATA", len(GECERLI_YAZIMLAR)))

    n += 1
    gomulu_yn = [x for x in NC_YAZIMLARI[:-1]        # son eleman "" (bos) -> ayri eksen
                 if K.cikis_kodu(_kos(_detay(_ata(A_BY, license_=x)), turev_ad)) == 0]
    ok = not gomulu_yn
    if not ok:
        hatalar.append("D6 gomulu alan yanlis-negatif -> %s" % gomulu_yn)
    print("  %-4s D6    gomulu alanda %d NC/tescilli yazimin hepsi IHLAL"
          % ("ok" if ok else "HATA", len(NC_YAZIMLARI) - 1))

    # --- 4) D8: KAPSAM iki kovaya AYRILIYOR mu (agsiz) ---
    print("  --- D8 KAPSAM AYRIMI ---")
    n += 1
    sahte_kayitlar = {
        "k-uygun": {"link": "https://turev-platform.example/models/1-x"},
        "k-adaptorlu-olculmedi": {"link": "https://ata-gamma.example/models/2-x"},
        "k-adaptorsuz": {"link": "https://ata-yabanci.example/x/3"},
        "k-linksiz": {"link": ""},
    }
    kapsam_defter = defter + K.sentetik_defter(
        [{"ad": "gamma", "hostlar": ["ata-gamma.example"], "kimlik": "bas-sayi:models",
          "ata_destegi": False, "detaylar": {}}])
    uygun, olc_adaptorlu, olc_adaptorsuz = K.kapsam_bolumle(sahte_kayitlar, kapsam_defter)
    ok = (len(uygun) == 1 and olc_adaptorlu == ["k-adaptorlu-olculmedi"]
          and sorted(olc_adaptorsuz) == ["k-adaptorsuz", "k-linksiz"])
    if not ok:
        hatalar.append("D8 kapsam ayrimi: uygun=%s adaptorlu=%s adaptorsuz=%s"
                       % (len(uygun), olc_adaptorlu, olc_adaptorsuz))
    print("  %-4s D8    ALAN-YOK(olculdu) ile OLCULMEDI(bakilmadi) AYRI kovada "
          "(uygun=%d · adaptorlu=%d · adaptorsuz=%d)"
          % ("ok" if ok else "HATA", len(uygun), len(olc_adaptorlu), len(olc_adaptorsuz)))

    n += 1
    ok = (K.cikis_kodu([{"durum": K.DURUM_SATILABILIR}], {"olculmedi_adaptorlu": ["a"]}) == 2
          and K.cikis_kodu([{"durum": K.DURUM_SATILABILIR}], {"olculmedi_adaptorsuz": ["a"]}) == 2
          and K.cikis_kodu([{"durum": K.DURUM_SATILABILIR}], {"taranmadi": 3}) == 2
          and K.cikis_kodu([{"durum": K.DURUM_SATILABILIR}], {}) == 0)
    if not ok:
        hatalar.append("D8 OLCULMEDI kapsam rc'yi 2'ye cekmiyor")
    print("  %-4s D8    OLCULMEDI kapsam kalinca rc=2 (asla 'temiz' degil)"
          % ("ok" if ok else "HATA"))

    # --- 5) D9: her sonucta urun kimligi (izlenebilirlik) ---
    n += 1
    kimliksiz = []
    for _d, _ad, detay, _rc, _du in DELIKLER:
        kimliksiz.extend(s["durum"] for s in _kos(detay) if not s.get("urun"))
    for _ad, detay, _du, _rc in SENARYOLAR:
        kimliksiz.extend(s["durum"] for s in _kos(detay) if not s.get("urun"))
    ok = not kimliksiz
    if not ok:
        hatalar.append("D9 urun kimligi set edilmemis sonuc(lar): %s" % sorted(set(kimliksiz)))
    print("  %-4s D9    HER sonucta urun kimligi var (ALAN-YOK dahil)" % ("ok" if ok else "HATA"))

    # --- 6) GECICI/KALICI ayrimi + toplu rc ---
    n += 1
    g = _kos(_detay(_ata("https://ata-alfa.example/models/9001-p")))[0]
    kk = _kos(_detay(_ata("https://ata-alfa.example/models/9002-p")))[0]
    ok = (g["durum"] != kk["durum"] and K.cikis_kodu([g]) == 2 and K.cikis_kodu([kk]) == 1)
    if not ok:
        hatalar.append("GECICI/KALICI ayrimi yok")
    print("  %-4s GECICI(rc2) ile KALICI(rc1) AYRI" % ("ok" if ok else "HATA"))

    n += 1
    temiz = _kos(_detay(_ata(A_BY)))
    ok = (K.cikis_kodu(temiz) == 0 and K.cikis_kodu(temiz + [g]) == 2
          and K.cikis_kodu(temiz + [g, kk]) == 1)
    if not ok:
        hatalar.append("toplu rc birlesimi yanlis")
    print("  %-4s toplu rc: temiz=0 · +gecici=2 · +kalici=1" % ("ok" if ok else "HATA"))

    # --- 7) UCTAN UCA CLI + VERI YAZMAZ ---
    oncesi = [(p, _sha(p)) for p in _veri_dosyalari()]
    if not oncesi:
        hatalar.append("veri dosyasi bulunamadi -> YAZMAZ iddiasi OLCULEMEDI")
        print("  HATA veri dosyasi yok -> 'yazmaz' iddiasi OLCULEMEDI")
    with tempfile.TemporaryDirectory() as tmp:
        kumeler = [
            ("temiz", {"a": _detay(_ata(A_BY))}, 0),
            ("ihlal", {"a": _detay(_ata(A_NC))}, 1),
            ("gecici", {"a": _detay(_ata("https://ata-alfa.example/models/9001-p"))}, 2),
            ("zincir", {"a": _detay(_ata("https://ata-alfa.example/models/8001-p"))}, 1),
            ("zarf", {"a": {"data": {"license": "CC0", "originals": [_ata(A_NC)]}}}, 1),
            ("null", {"a": None}, 1),
        ]
        for ad, detaylar, beklenen in kumeler:
            n += 1
            yol = _fikstur_yaz(tmp, "fx-%s.json" % ad, detaylar)
            r = subprocess.run([sys.executable, _KAPI_YOL, "--fikstur", yol],
                               capture_output=True, text=True)
            ok = (r.returncode == beklenen)
            if r.returncode == 0 and beklenen != 0:
                sessiz_gecis += 1
            if not ok:
                hatalar.append("CLI %s: rc=%d (bek %d)\n%s" % (ad, r.returncode, beklenen, r.stdout))
            print("  %-4s CLI --fikstur %-7s -> rc=%d (bek %d)"
                  % ("ok" if ok else "HATA", ad, r.returncode, beklenen))

        n += 1
        yol = _fikstur_yaz(
            tmp, "fx-sozluk.json", {"a": _detay(_ata(A_BY, license_="BY-SA"))},
            kayitlar={"a": {"link": "https://turev-platform.example/models/1-x"}})
        r = subprocess.run([sys.executable, _KAPI_YOL, "--fikstur", yol],
                           capture_output=True, text=True)
        ok = (r.returncode == 0)
        if not ok:
            hatalar.append("CLI sozluk ekseni: rc=%d (bek 0)" % r.returncode)
        print("  %-4s CLI: turev link'i kaynak sozlugunu seciyor -> rc=%d (bek 0)"
              % ("ok" if ok else "HATA", r.returncode))

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
    print("  %-4s kapi VERI YAZMADI (%d dosya, sha256 esit)" % ("ok" if ok else "HATA", len(oncesi)))

    n += 1
    r = subprocess.run([sys.executable, _KAPI_YOL, "--kendini-test"],
                       capture_output=True, text=True)
    ok = (r.returncode == 0)
    if not ok:
        hatalar.append("--kendini-test rc=%d" % r.returncode)
    print("  %-4s --kendini-test rc=0" % ("ok" if ok else "HATA"))

    print("")
    print("SESSIZ_GECIS=%d" % sessiz_gecis)
    if hatalar:
        print("BASARISIZ — %d iddia yanlis:" % len(hatalar))
        for h in hatalar:
            print("  x %s" % h)
        return 1
    print("TUM TESTLER GECTI (%d iddia)." % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
