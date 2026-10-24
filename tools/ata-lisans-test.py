#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/ata-lisans-kapisi.py (ATA ZINCIRI lisans kapisi).

DAVRANISSAL + AGSIZ. Butun host/kimlik/lisanslar UYDURMADIR (".example" TLD'si RFC 2606 ile
ayrilmistir; gercek bir kaynak platformu isaret etmez). Fikstur SEKLI gercek cikti seklini
taklit eder: ata referansi {link: <dolu>, license: <BOS>, designId: 0} — dort canli emsalde
olculen desen budur (lisans turevin JSON'unda GORUNMEZ; tek sinyal serbest-metin link).

🔴 D-BOLUMU (D1..D18): bagimsiz curutucunun olctugu SESSIZ GECISLER. Hepsi once rc=0 ile
geciyordu. Her D vakasinin bir OLDURUCU MUTANTI vardir (tools/ata-lisans-mutasyon.py);
mutant uygulaninca ilgili D iddiasi DUSER. Bu, "batarya kendi deligini gormuyor" hukmune
verilen cevaptir — batarya artik kendi korlugunu de olcer.

🔴 IDDIA ETIKETI: her BASARISIZ satiri "[<etiket>] " ile baslar ve etiketler KOSELI PARANTEZ
sayesinde TEKILDIR. Mutasyon surucusu dusen iddiayi bu etiketle kanitlar; etiketsiz (duz
alt-dize) kanit YANILTIR — "D1" capasi "D11b"/"D12" satirlarina da uyuyordu
([[mutasyon-kaniti-yeniden-uretilebilir]]).

KORUNAN EKSENLER (curutucu dogruladi, bozulmamali):
  * yanlis-negatif 0 : NC hicbir yazimda gecmez (NC_YAZIMLARI tablosu).
  * fail-closed      : adaptorsuz · null · 403 · 429 · timeout · bozuk JSON · bos yanit.
  * VERI YAZMAZ      : kosum oncesi/sonrasi veri dosyalarinin sha256'si esit.

Kosum:  python3 tools/ata-lisans-test.py
"""
import contextlib
import hashlib
import importlib.util
import io
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

    # 🔴 ACIKLAMA EKSI fiksturu. Host `thingiverse.com` burada YALNIZCA bir COZUMLEME
    # ANAHTARIDIR: adaptor sentetik-defterden gelir, AG'A CIKILMAZ. Gerekce: aciklamada
    # URL'sIZ yazilan `thing:<N>` kimliginin kanonik site URL'sine cevrilmesi bu kuralin
    # kendisidir; fikstur metinleri canli 4853978/7332849/7332847 aciklamalariyla birebir
    # ayni sekilde yazilmistir.
    {"ad": "tv", "hostlar": ["thingiverse.com"], "kimlik": "thing",
     "ata_destegi": True, "yargi": "insan-adi",        # ND sozlukte SATILABILIR gorunur
     "detaylar": {
         "3543408": {"license": "Creative Commons - Attribution - Non-Commercial - "
                                "No Derivatives"},
         "3628594": {"license": "Creative Commons - Attribution"},
         "9900001": {"license": "Attribution - NoDerivatives"},
     }},
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
    # AYRAC VARYANTI: alt-dize listesinde OLMAYAN kirilmaz tire (U+2011 — web sayfasindan
    # kopyala-yapistirda gercekten gelir). Veto'nun DIGER kollarinin HICBIRI yakalamaz
    # (olculdu: nc-altdize F · tescilli F · 'nc' jetonu F); yalniz JETON BITISIKLIGI yakalar
    # ve kural kalkarsa GENEL sozluk bunu SATILABILIR der = sizinti. Bu vaka olmadan
    # bitisiklik kurali 'beyan edilmis survivor' olurdu ([[beyan-edilmis-survivor]]).
    "Creative Commons Attribution Non‑Commercial 4.0",
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


def _detay_alan(alan_adi, *atalar):
    """Ata alanini VERILEN YAZIMLA yazan detay ('Originals' / 'remixparents' / 'REMIXOF').
    Govde isaretleri (license/title) DURUR: olculen eksen alan ADININ yazimidir."""
    d = {"license": "CC0", "title": "uydurma-turev"}
    d[alan_adi] = list(atalar)
    return d


def _zarfla(govde, kademe):
    """Govdeyi <kademe> adet ic ice zarfa sarar: {"data":{"result":{...}}} ...
    Zarf adlari sirayla kullanilir; her kademede TEK ic sozluk vardir (belirsizlik YOK)."""
    adlar = ["data", "result", "response", "payload", "design", "model"]
    d = govde
    for i in range(kademe):
        d = {adlar[i % len(adlar)]: d}
    return d


A_NC = "https://ata-alfa.example/models/4410-parca"
A_BY = "https://ata-alfa.example/models/7788-parca"

# (etiket, ad, detay, beklenen ilk durum, beklenen rc) — etiket TEKILDIR (bkz. modul basligi)
SENARYOLAR = [
    ("S-POZ-NCSA", "POZITIF: ata NC-SA (canli emsal deseni: license BOS + designId 0)",
     _detay(_ata(A_NC)), K.DURUM_IHLAL, 1),
    ("S-POZ-YENIDEN-LISANS", "POZITIF: turev kendini CC0 ilan etse de ata NC -> ihlal",
     _detay(_ata(A_NC), kendi_lisansi="CC0"), K.DURUM_IHLAL, 1),
    ("S-NEG-BY", "NEGATIF: ata CC-BY -> ihlal YOK", _detay(_ata(A_BY)), K.DURUM_SATILABILIR, 0),
    ("S-NEG-CC0", "NEGATIF: ata CC0 -> ihlal YOK",
     _detay(_ata("https://ata-alfa.example/models/5500-p")), K.DURUM_SATILABILIR, 0),
    ("S-NEG-METIN-URL", "NEGATIF: ata alani YOK, metinde benzer URL var (yanlis-pozitif kapisi)",
     _detay(metin="kaynak: %s adresinden esinlenildi" % A_NC), K.DURUM_ALAN_YOK, 0),
    ("S-AYIRT-HOST", "AYIRT EDICI: AYNI kimlik (7788) FARKLI host (beta) -> NC -> IHLAL",
     _detay(_ata("https://ata-beta.example/models/7788-parca")), K.DURUM_IHLAL, 1),
    ("S-FC-ADAPTORSUZ", "FAIL-CLOSED: adaptorsuz host -> ELLE-BAK",
     _detay(_ata("https://ata-yabanci.example/model/12-p")), K.DURUM_ADAPTORSUZ, 1),
    ("S-FC-NULL", "FAIL-CLOSED: API null -> KALICI",
     _detay(_ata("https://ata-alfa.example/models/9003-p")), K.DURUM_KALICI, 1),
    ("S-FC-403", "FAIL-CLOSED: API 403 -> KALICI",
     _detay(_ata("https://ata-alfa.example/models/9002-p")), K.DURUM_KALICI, 1),
    ("S-AYRIM-429", "AYRIM: API 429 -> GECICI (rc 2), KALICI DEGIL",
     _detay(_ata("https://ata-alfa.example/models/9001-p")), K.DURUM_GECICI, 2),
    ("S-FC-BOS-LISANS", "FAIL-CLOSED: ata lisansi BOS dondu -> KALICI",
     _detay(_ata("https://ata-alfa.example/models/6600-p")), K.DURUM_KALICI, 1),
    ("S-FC-LINKSIZ", "FAIL-CLOSED: ata referansinda link YOK -> KALICI",
     _detay(_ata("")), K.DURUM_KALICI, 1),
    ("S-SIKI-GOMULU-NC", "SIKI YON: gomulu lisans NC ise link satilabilir olsa da IHLAL",
     _detay(_ata(A_BY, license_="Creative Commons - Attribution - Non-Commercial")),
     K.DURUM_IHLAL, 1),
    ("S-NEG-GOMULU-TEMIZ", "NEGATIF: gomulu lisans satilabilir ise hukum VERILMEZ, host yine cozulur",
     _detay(_ata(A_BY, license_="Creative Commons - Attribution")), K.DURUM_SATILABILIR, 0),
    ("S-POZ-GOMULU-TEMIZ-ATA-NC", "POZITIF: gomulu temiz ama ata NC -> host cozumu ihlali yakalar",
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

    # --- IKINCI TUR: "ALAN-YOK" IDDIASI KANITLANIYOR MU (D13..D18) ---
    # Hepsi ONCE rc=0 + durum=ALAN-YOK ile geciyordu ve gerekce metni "detay OLCULDU: ata
    # alani yok" DIYORDU — olculmemis bir seyi olculmus gibi BEYAN eden bir yalan.
    ("D13", "4 KADEMELI zarf ACILIR (eski tavan 3'te ALAN-YOK sayiliyordu)",
     _zarfla(_detay(_ata(A_NC)), 4), 1, K.DURUM_IHLAL),
    ("D13b", "zarf TAVANINI asan detay fail-closed (ALAN-YOK DEGIL)",
     _zarfla(_detay(_ata(A_NC)), K.ZARF_TAVANI + 1), 1, K.DURUM_SEKIL),
    ("D13c", "GOVDE ISARETLI zarf (id/title + data) icindeki ata alani GORULUR",
     {"id": 1, "title": "x", "data": {"license": "CC0", "originals": [_ata(A_NC)]}},
     1, K.DURUM_IHLAL),
    ("D14", "ayni duzeyde IKI zarf anahtari -> BELIRSIZ zarf fail-closed (ALAN-YOK DEGIL)",
     {"data": _detay(_ata(A_NC)), "model": {"license": "CC0"}}, 1, K.DURUM_SEKIL),
    ("D15", "ata alani 'Originals' yazimiyla -> GORULUR (buyuk harf)",
     _detay_alan("Originals", _ata(A_NC)), 1, K.DURUM_IHLAL),
    ("D16", "ata alani 'remixparents' yazimiyla -> GORULUR (kucuk harf)",
     _detay_alan("remixparents", _ata(A_NC)), 1, K.DURUM_IHLAL),
    ("D17", "ata alani 'REMIXOF' yazimiyla -> GORULUR (tumu buyuk)",
     _detay_alan("REMIXOF", _ata(A_NC)), 1, K.DURUM_IHLAL),
    ("D18", "TANINMAYAN sekildeki detay 'ata alani yok' SAYILMAZ (olculmemis platform)",
     {"objectId": 91, "modelName": "uydurma", "attribution": "yok"}, 1, K.DURUM_SEKIL),
]

# V1: TAM METIN lisanslar. Hepsi TICARI SATISA UYGUNDUR; veto YEMEMELIDIR. "non-exclusive"
# ibaresi her standart CC/royalty-free tam metninde gecer — duz alt-dize aramasi bu
# metinleri veto ediyordu (yanlis-pozitif; yon fail-closed ama YAYINI DURDURUR).
TAM_METIN_YAZIMLAR = [
    "Attribution 4.0 International — the Licensor grants You a worldwide, royalty-free, "
    "non-exclusive, irrevocable license to exercise the Licensed Rights.",
    "CC BY-SA 4.0: non-exclusive, worldwide, royalty-free; commercial use permitted with "
    "attribution and share-alike.",
    "Creative Commons Attribution-ShareAlike 4.0 — a non exclusive license to reproduce, "
    "share and adapt the material for any purpose.",
    "MIT License — Permission is hereby granted, free of charge, to any person obtaining a "
    "copy of this software, to use, copy, modify, merge, publish and distribute it.",
]
# Ayni desenin AYIRT EDICI karsi vakalari: bunlar veto'da KALMALI (aksi halde V1 onarimi
# vetoyu delerdi). NC_YAZIMLARI'nda da varlar; burada eksen TEK BASINA olculur.
TESCILLI_EXCLUSIVE = ["MakerWorld Exclusive License", "Exclusive License",
                      "Attribution - Exclusive License"]


# ---- ACIKLAMA EKSI (ucluca; ONCUL canli olcum 23 Eki 2026) ----
# Yapisal ata alani (`ancestors`/`originals`) BOS; atif YALNIZ aciklamada. Onceki kapi
# "ALAN-YOK" diyordu = CC BY-NC-ND turev SATILABILIR GECTI.
A_ND = "https://www.thingiverse.com/thing:3543408"     # ata: CC BY-NC-ND
A_CC = "https://www.thingiverse.com/thing:3628594"     # ata: CC BY
A_NDONLY = "https://www.thingiverse.com/thing:9900001"  # ata: yalniz NoDerivatives


def _ak(metin, **kw):
    """Turev detayi: govde isaretli + aciklama alaninda metin (yapisal ata alani YOK)."""
    return {"id": kw.get("id", 1), "license": "CC0", "title": "uydurma-turev",
            kw.get("alan", "description"): metin}


# (etiket, ad, detay, beklenen durum, beklenen rc)
ACIKLAMA_VAKALARI = [
    ("A1-ACIKLAMA-REMIX", "ACIKLAMA: 'Remix of <URL>' -> ata 3543408 -> IHLAL",
     _ak("Remix of %s" % A_ND), K.DURUM_IHLAL, 1),
    ("A2-ACIKLAMA-THING-KIMLIK",
     "ACIKLAMA: 'based on thing:N' (URL YOK, kimlik deseni) -> IHLAL",
     _ak("based on thing:3543408"), K.DURUM_IHLAL, 1),
    ("A3-ACIKLAMA-ORIGINAL",
     "ACIKLAMA: 'Original design: thing:N' -> IHLAL",
     _ak("Original design: thing:3543408"), K.DURUM_IHLAL, 1),
    ("A4-ACIKLAMA-CC-BY",
     "ACIKLAMA: tetik + CC-BY ata 3628594 -> SATILABILIR (yanlis-ihlal yok)",
     _ak("remixed from %s" % A_CC), K.DURUM_SATILABILIR, 0),
    ("A5-ACIKLAMA-TETIKSIZ",
     "ACIKLAMA: TETIKSIZ metindeki thing URL'si sayilmaz -> ALAN-YOK (yanlis-pozitif kapisi)",
     _ak("kaynak: %s adresinden ilham alindi" % A_ND), K.DURUM_ALAN_YOK, 0),
    ("A6-ACIKLAMA-OKUNAMAZ",
     "ACIKLAMA: alan var ama str DEGIL (int) -> GECICI rc2, ALAN-YOK DEGIL",
     _ak(123), K.DURUM_GECICI, 2),
    ("A7-ACIKLAMA-OZ-ATIF",
     "ACIKLAMA: oz-atif (thing:<kendi id>) -> ref 0, ALAN-YOK",
     _ak("remix of thing:999", id=999), K.DURUM_ALAN_YOK, 0),
    ("A8-ACIKLAMA-USED-THIS-DESIGN",
     "ACIKLAMA: 'I used this design' (canli 4853978 metni) -> IHLAL",
     _ak("For the lowerpart I used this design: %s" % A_ND), K.DURUM_IHLAL, 1),
    ("A9-ATA-ND",
     "ATA LISANSI: yalniz NoDerivatives (hicbir sozluk veto etmez) -> IHLAL",
     _ak("based on %s" % A_NDONLY), K.DURUM_IHLAL, 1),
    # --- B1/B2/B3: "0 VURUS = TEMIZ" YASAGI (23 Eki 2026) ---
    # Once aciklama alanlarinin HICBIRINDE metin yoksa kayit ALAN-YOK rc=0 ile "temiz"
    # sayiliyordu: "olculmedi" sessizce yesile donuyordu.
    ("B1-ACIKLAMA-BOS+SUMMARY",
     "ACIKLAMA: description='' + summary='remix of thing:3543408' -> IHLAL "
     "(bos alan tek basina engel DEGIL)",
     {"id": 1, "license": "CC0", "title": "uydurma-turev", "description": "",
      "summary": "remix of thing:3543408"}, K.DURUM_IHLAL, 1),
    ("B2-ACIKLAMA-YOK",
     "ACIKLAMA: hicbir aciklama alani dolu DEGIL -> GECICI rc2 (0 vurus temiz sayilmaz)",
     {"id": 1, "license": "CC0", "title": "uydurma-turev"}, K.DURUM_GECICI, 2),
    # --- TL1/TL2: Printables `thingiverseLink` YAPISAL ata (BaBa 23 Eki 23:4x) ---
    ("TL1-THINGIVERSELINK",
     "YAPISAL: thingiverseLink -> NC-ND ata, aciklamada tetik YOK -> IHLAL",
     {"id": 1, "license": "CC0", "title": "uydurma-turev", "summary": "duz metin",
      "thingiverseLink": "https://www.thingiverse.com/thing:3543408"}, K.DURUM_IHLAL, 1),
    ("TL2-THINGIVERSELINK-BOS",
     "YAPISAL: thingiverseLink='' -> eski davranis (ALAN-YOK rc0)",
     {"id": 1, "license": "CC0", "title": "uydurma-turev", "summary": "duz metin",
      "thingiverseLink": ""}, K.DURUM_ALAN_YOK, 0),
    ("B3-ACIKLAMA-BOSLUK",
     "ACIKLAMA: description='   ' (yalniz bosluk) -> GECICI rc2 (0 vurus temiz sayilmaz)",
     {"id": 1, "license": "CC0", "title": "uydurma-turev", "description": "   "},
     K.DURUM_GECICI, 2),
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
    for etiket, ad, detay, beklenen_durum, beklenen_rc in SENARYOLAR:
        n += 1
        sonuclar = _kos(detay)
        durum = sonuclar[0]["durum"] if sonuclar else "(sonuc yok)"
        rc = K.cikis_kodu(sonuclar)
        ok = (durum == beklenen_durum and rc == beklenen_rc)
        if rc == 0 and beklenen_rc != 0:
            sessiz_gecis += 1
        if not ok:
            hatalar.append("[%s] %s -> durum=%s (bek %s) rc=%s (bek %s)"
                           % (etiket, ad, durum, beklenen_durum, rc, beklenen_rc))
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
            hatalar.append("[%s] %s -> rc=%s (bek %s) durumlar=%s (icinde bek %s)"
                           % (delik, ad, rc, beklenen_rc, durumlar, beklenen_durum))
        print("  %-4s %-5s %-84s rc=%s" % ("ok" if ok else "HATA", delik, ad[:84], rc))

    # --- 2a) ACIKLAMA EKSI (yapisal alan bos, atif yalniz metinde) ---
    print("  --- ACIKLAMA EKSI (tetik + aciklama; ND kurali) ---")
    for etiket, ad, detay, beklenen_durum, beklenen_rc in ACIKLAMA_VAKALARI:
        n += 1
        sonuclar = _kos(detay)
        durum = sonuclar[0]["durum"] if sonuclar else "(sonuc yok)"
        rc = K.cikis_kodu(sonuclar)
        ok = (durum == beklenen_durum and rc == beklenen_rc)
        if rc == 0 and beklenen_rc != 0:
            sessiz_gecis += 1
        if not ok:
            hatalar.append("[%s] %s -> durum=%s (bek %s) rc=%s (bek %s)"
                           % (etiket, ad, durum, beklenen_durum, rc, beklenen_rc))
        print("  %-4s %-90s durum=%-22s rc=%s" % ("ok" if ok else "HATA", ad[:90], durum, rc))

    # --- 2a-RP) Printables `remixParents` YAPISAL ata (BaBa 24 Eki tik 84) ---
    # Canli olcum 24 Eki: DETAIL_Q `remixParents` sorgulamiyordu, sorgulansa da
    # `{parentPrintId, url, parentPrint{license}}` sekli `_referans_ac`'ta link uretmiyordu
    # -> PR->PR ve "parentPrintId null + url thing:N" atalari gorunmez, PR dilimi sahte temiz.
    # Sekil canli 1495334 (ata pr:1329863 CC-BY) / 1694862 (url thing:3806140) ile ayni.
    print("  --- REMIXPARENTS (PR yapisal ata; parentPrintId · url · gomulu lisans) ---")
    rp_defter = defter + K.sentetik_defter([
        {"ad": "pr", "hostlar": ["printables.com"], "kimlik": "bas-sayi:model",
         "ata_destegi": True, "yargi": "kisaltma",
         "detaylar": {
             # ata aciklamasinda TETIK var ama URL YOK (canli 1329863 sekli): ust kademede
             # metnin kendisi ata linki SAYILMAMALI (yalniz_url).
             "1329863": {"license": "CC-BY", "name": "uydurma-ata",
                         "description": "<p>Including the source file in case you want "
                                        "to remix.</p>"},
             "7700001": {"license": "CC-BY-NC", "name": "uydurma-nc-ata"},
         }}])

    def _rp(*elemanlar):
        return {"id": "1", "license": "CC-BY", "name": "uydurma-turev",
                "summary": "duz metin", "remixParents": list(elemanlar)}

    RP_VAKALARI = [
        ("RP1-PARENTPRINTID", "remixParents parentPrintId -> PR ata CC-BY -> SATILABILIR "
         "(ust kademede aciklama metni link SAYILMAZ)",
         _rp({"parentPrintId": "1329863", "url": None,
              "parentPrint": {"id": "1329863", "license": {"abbreviation": "CC-BY"}}}),
         K.DURUM_SATILABILIR, 0),
        ("RP2-URL-THING", "remixParents parentPrintId null + url thing:N -> TV ata CC BY "
         "-> SATILABILIR",
         _rp({"parentPrintId": None, "url": A_CC, "parentPrint": None}),
         K.DURUM_SATILABILIR, 0),
        ("RP3-GOMULU-NC", "remixParents gomulu ata lisansi CC-BY-NC -> IHLAL",
         _rp({"parentPrintId": "7700001", "url": None,
              "parentPrint": {"id": "7700001", "license": {"abbreviation": "CC-BY-NC"}}}),
         K.DURUM_IHLAL, 1),
        ("RP4-BOS-ELEMAN", "remixParents elemani dolu ama id+url YOK -> KALICI (fail-closed)",
         _rp({"parentPrintId": None, "url": None, "parentPrint": None}),
         K.DURUM_KALICI, 1),
    ]
    for etiket, ad, detay, beklenen_durum, beklenen_rc in RP_VAKALARI:
        n += 1
        sonuclar = K.kayit_yargi("uydurma-urun", detay, rp_defter, K.genel_satilabilir)
        durumlar = [s["durum"] for s in sonuclar]
        rc = K.cikis_kodu(sonuclar)
        # TUM satirlar beklenen durumda olmali: RP1'de ust kademeden sahte ELLE-BAK satiri
        # dogarsa ilk satir SATILABILIR gorunse de kayit ELLE-BAK kuyruguna duser.
        ok = (bool(durumlar) and all(d == beklenen_durum for d in durumlar)
              and rc == beklenen_rc)
        if rc == 0 and beklenen_rc != 0:
            sessiz_gecis += 1
        if not ok:
            hatalar.append("[%s] %s -> durumlar=%s (bek hepsi %s) rc=%s (bek %s)"
                           % (etiket, ad, durumlar, beklenen_durum, rc, beklenen_rc))
        print("  %-4s %-90s durum=%-22s rc=%s" % ("ok" if ok else "HATA", ad[:90],
                                                  ",".join(durumlar), rc))

    # RP-Q: canli sorgu alani. Alan DETAIL_Q'dan cikarsa yukaridaki 4 vaka yine yesil kalir
    # (fikstur alani elle verir) ama canlida tum PR kayitlari ALAN-YOK olur (24 Eki olculdu).
    n += 1
    with open(os.path.join(_HERE, "printables-api.py"), encoding="utf-8") as f:
        _pa = f.read()
    _dq = _pa.split('DETAIL_Q = """', 1)[-1].split('"""', 1)[0]
    ok = ("remixParents { parentPrintId url parentPrint { id license { abbreviation } } }"
          in _dq)
    if not ok:
        hatalar.append("[RP-Q-DETAIL] printables-api DETAIL_Q `remixParents` alt-alanlarini "
                       "SORGULAMIYOR -> canlida PR atasi gorunmez")
    print("  %-4s RP-Q  DETAIL_Q remixParents {parentPrintId url parentPrint{license}} sorgulaniyor"
          % ("ok" if ok else "HATA"))

    # --- 2a-PD) URETIM DEFTERI ata_destegi (BaBa 24 Eki tik 87) ---
    # PR ata alani CANLI olculdu (thingiverseLink + remixParents) -> PR kayitlari KAPSAM_UYGUN;
    # bayrak False kalsaydi toplu taramada PR dilimi OLCULMEDI/ADAPTORLU'ya dusuyordu.
    # TV/c3/mmf sekli OLCULMEDI -> False KALIR (olcumsuz cevirme = sessiz fail-open, D13..D18).
    print("  --- URETIM DEFTERI ata_destegi (PR=True; TV/c3/mmf=False) ---")
    uretim = K.uretim_defteri()
    bayrak = {a.ad: a.ata_destegi for a in uretim}
    n += 1
    ok = (bayrak == {"mw": True, "pr": True, "tv": False, "c3": False, "mmf": False})
    if not ok:
        hatalar.append("[PD1-BAYRAK] uretim defteri ata_destegi beklenen degil: %s" % bayrak)
    print("  %-4s PD1   ata_destegi mw/pr=True · tv/c3/mmf=False -> %s"
          % ("ok" if ok else "HATA", bayrak))

    n += 1
    pd_kayitlar = {
        "pr-turev": {"link": "https://www.printables.com/model/1495334"},
        "pr-kisa-link": {"link": "https://www.printables.com/model/1694862-x"},
        "tv-turev": {"link": "https://www.thingiverse.com/thing:3543408"},
    }
    uygun, olc_adaptorlu, olc_adaptorsuz = K.kapsam_bolumle(pd_kayitlar, uretim)
    uygun_idler = sorted(u[0] for u in uygun)
    pr_olculmedi = [i for i in olc_adaptorlu + olc_adaptorsuz if i.startswith("pr-")]
    ok = (uygun_idler == ["pr-kisa-link", "pr-turev"] and pr_olculmedi == []
          and olc_adaptorlu == ["tv-turev"] and olc_adaptorsuz == [])
    if not ok:
        hatalar.append("[PD2-PR-KAPSAM] toplu taramada PR KAPSAM_UYGUN degil: uygun=%s "
                       "adaptorlu=%s adaptorsuz=%s" % (uygun_idler, olc_adaptorlu,
                                                       olc_adaptorsuz))
    print("  %-4s PD2   toplu kapsam: PR uygun=%d · PR olculmedi=%d · TV adaptorlu=%d"
          % ("ok" if ok else "HATA", len(uygun_idler), len(pr_olculmedi), len(olc_adaptorlu)))

    # PD3/PD4: PR ALAN-YOK bir OLCUM iddiasi olarak KANITLANIR (bayrak True olunca toplu
    # taramada "temiz" sayilacak tek sinif budur): canli DETAIL_Q seklinde govde taninir,
    # ata alani YOK ya da BOS liste -> ALAN-YOK (ATASIZ_OLCULDU) rc 0; sekil taninmazsa DEGIL.
    def _pr_govde(**ek):
        d = {"id": "1495334", "name": "uydurma-turev", "slug": "uydurma-turev",
             "license": {"name": "Creative Commons Attribution", "abbreviation": "CC-BY"},
             "summary": "duz metin", "description": "<p>duz metin</p>"}
        d.update(ek)
        return d
    for etiket, ad, detay, beklenen in [
        ("PD3-PR-ALAN-YOK", "PR detayi: thingiverseLink/remixParents alani YOK -> ALAN-YOK",
         _pr_govde(), K.DURUM_ALAN_YOK),
        ("PD4-PR-BOS-LISTE", "PR detayi: remixParents=[] + thingiverseLink='' -> ALAN-YOK",
         _pr_govde(remixParents=[], thingiverseLink=""), K.DURUM_ALAN_YOK),
        ("PD5-PR-SEKILSIZ", "PR detayi govde TANINMAZ -> ALAN-YOK DENMEZ (fail-closed)",
         {"foo": {"bar": 1}}, None),
    ]:
        n += 1
        sonuclar = K.kayit_yargi("uydurma-urun", detay, uretim, K.genel_satilabilir)
        durumlar = [s["durum"] for s in sonuclar]
        rc = K.cikis_kodu(sonuclar)
        if beklenen is None:
            ok = bool(durumlar) and K.DURUM_ALAN_YOK not in durumlar and rc != 0
        else:
            ok = durumlar == [beklenen] and rc == 0
        if not ok:
            hatalar.append("[%s] %s -> durumlar=%s rc=%s" % (etiket, ad, durumlar, rc))
        print("  %-4s %-90s durum=%-22s rc=%s" % ("ok" if ok else "HATA", ad[:90],
                                                  ",".join(durumlar), rc))

    # --- 2b) ZARF EKSENI TEK BASINA (her eksen AYRI oldurulebilmeli) ---
    # Bu iki iddia olmadan tavan/belirsizlik ekseni D18 (govde izi) tarafindan KAPATILIR ve
    # "savunma derinligi" beyan edilmis survivor'a doner ([[beyan-edilmis-survivor]]).
    print("  --- ZARF EKSENI (tavan · belirsizlik AYRI olculur) ---")
    n += 1
    tavan_hatasi = K._zarf_ac(_zarfla(_detay(_ata(A_NC)), K.ZARF_TAVANI + 1))[1]
    ok = bool(tavan_hatasi)
    if not ok:
        hatalar.append("[D13b-tavan] zarf tavani asildiginda hata DONMEDI (fail-open)")
    print("  %-4s D13b  zarf TAVANI asilinca _zarf_ac hata doner (fail-closed)"
          % ("ok" if ok else "HATA"))

    n += 1
    belirsiz_hatasi = K._zarf_ac({"data": {"a": 1}, "model": {"b": 2}})[1]
    ok = bool(belirsiz_hatasi)
    if not ok:
        hatalar.append("[D14-belirsiz] ayni duzeyde 2 ic sozlukte hata DONMEDI (fail-open)")
    print("  %-4s D14   BELIRSIZ zarfta _zarf_ac hata doner (fail-closed)"
          % ("ok" if ok else "HATA"))

    n += 1
    ok = (K._zarf_ac({"title": "x"})[2] is True and K._zarf_ac({"foo": 1})[2] is False)
    if not ok:
        hatalar.append("[D18-govde-izi] govde izi bayragi TANIMA ile ayrismiyor")
    print("  %-4s D18   govde izi: taninan alan True · taninmayan alan False"
          % ("ok" if ok else "HATA"))

    # --- 3) SOZLUK EKSENI ---
    print("  --- SOZLUK EKSENI (yanlis-negatif / yanlis-pozitif) ---")
    n += 1
    yn = [x for x in NC_YAZIMLARI if K.coklu_sozluk_satilabilir(x, turev_ad)]
    ok = not yn
    if not ok:
        hatalar.append("[yanlis-negatif] NC/tescilli gecti -> %s" % yn)
    print("  %-4s yanlis-negatif %d/%d (NC/tescilli hicbir yazimda gecmiyor)"
          % ("ok" if ok else "HATA", len(yn), len(NC_YAZIMLARI)))

    n += 1
    yp = [x for x in GECERLI_YAZIMLAR if not K.coklu_sozluk_satilabilir(x, turev_ad)]
    ok = not yp
    if not ok:
        hatalar.append("[yanlis-pozitif] gecerli lisans satilamaz sanildi -> %s" % yp)
    print("  %-4s yanlis-pozitif %d/%d (gecerli yazimlarin hepsi satilabilir)"
          % ("ok" if ok else "HATA", len(yp), len(GECERLI_YAZIMLAR)))

    # V1: TAM METIN lisanslar veto YEMEZ; tescilli "Exclusive License" veto'da KALIR.
    n += 1
    veto_yp = [x for x in TAM_METIN_YAZIMLAR if K.lisans_vetosu(x)]
    veto_kacak = [x for x in TESCILLI_EXCLUSIVE if not K.lisans_vetosu(x)]
    ok = not veto_yp and not veto_kacak
    if not ok:
        hatalar.append("[veto-tam-metin] tam metin veto yedi -> %s · tescilli kacti -> %s"
                       % (veto_yp, veto_kacak))
    print("  %-4s V1    tam metin lisans %d/%d veto YEMEZ · tescilli 'Exclusive' %d/%d VETO"
          % ("ok" if ok else "HATA", len(TAM_METIN_YAZIMLAR) - len(veto_yp),
             len(TAM_METIN_YAZIMLAR), len(TESCILLI_EXCLUSIVE) - len(veto_kacak),
             len(TESCILLI_EXCLUSIVE)))

    n += 1
    gomulu_yp = [x for x in GECERLI_YAZIMLAR
                 if K.cikis_kodu(_kos(_detay(_ata(A_BY, license_=x)), turev_ad)) != 0]
    ok = not gomulu_yp
    if not ok:
        hatalar.append("[D6-gomulu-yp] gomulu alan yanlis-pozitif -> %s" % gomulu_yp)
    print("  %-4s D6    gomulu alanda %d gecerli yazimin hicbiri IHLAL damgasi yemiyor"
          % ("ok" if ok else "HATA", len(GECERLI_YAZIMLAR)))

    n += 1
    gomulu_yn = [x for x in NC_YAZIMLARI[:-1]        # son eleman "" (bos) -> ayri eksen
                 if K.cikis_kodu(_kos(_detay(_ata(A_BY, license_=x)), turev_ad)) == 0]
    ok = not gomulu_yn
    if not ok:
        hatalar.append("[D6-gomulu-yn] gomulu alan yanlis-negatif -> %s" % gomulu_yn)
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
        hatalar.append("[D8-kapsam] kapsam ayrimi: uygun=%s adaptorlu=%s adaptorsuz=%s"
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
        hatalar.append("[D8-rc] OLCULMEDI kapsam rc'yi 2'ye cekmiyor")
    print("  %-4s D8    OLCULMEDI kapsam kalinca rc=2 (asla 'temiz' degil)"
          % ("ok" if ok else "HATA"))

    # --- 5) D9: her sonucta urun kimligi (izlenebilirlik) ---
    n += 1
    kimliksiz = []
    for _d, _ad, detay, _rc, _du in DELIKLER:
        kimliksiz.extend(s["durum"] for s in _kos(detay) if not s.get("urun"))
    for _et, _ad, detay, _du, _rc in SENARYOLAR:
        kimliksiz.extend(s["durum"] for s in _kos(detay) if not s.get("urun"))
    ok = not kimliksiz
    if not ok:
        hatalar.append("[D9] urun kimligi set edilmemis sonuc(lar): %s" % sorted(set(kimliksiz)))
    print("  %-4s D9    HER sonucta urun kimligi var (ALAN-YOK dahil)" % ("ok" if ok else "HATA"))

    # --- 6) GECICI/KALICI ayrimi + toplu rc ---
    n += 1
    g = _kos(_detay(_ata("https://ata-alfa.example/models/9001-p")))[0]
    kk = _kos(_detay(_ata("https://ata-alfa.example/models/9002-p")))[0]
    ok = (g["durum"] != kk["durum"] and K.cikis_kodu([g]) == 2 and K.cikis_kodu([kk]) == 1)
    if not ok:
        hatalar.append("[GECICI-KALICI] GECICI/KALICI ayrimi yok")
    print("  %-4s GECICI(rc2) ile KALICI(rc1) AYRI" % ("ok" if ok else "HATA"))

    n += 1
    temiz = _kos(_detay(_ata(A_BY)))
    ok = (K.cikis_kodu(temiz) == 0 and K.cikis_kodu(temiz + [g]) == 2
          and K.cikis_kodu(temiz + [g, kk]) == 1)
    if not ok:
        hatalar.append("[toplu-rc] toplu rc birlesimi yanlis")
    print("  %-4s toplu rc: temiz=0 · +gecici=2 · +kalici=1" % ("ok" if ok else "HATA"))

    # --- 7) UCTAN UCA CLI + VERI YAZMAZ ---
    oncesi = [(p, _sha(p)) for p in _veri_dosyalari()]
    if not oncesi:
        hatalar.append("[YAZMAZ] veri dosyasi bulunamadi -> YAZMAZ iddiasi OLCULEMEDI")
        print("  HATA veri dosyasi yok -> 'yazmaz' iddiasi OLCULEMEDI")
    with tempfile.TemporaryDirectory() as tmp:
        kumeler = [
            ("temiz", {"a": _detay(_ata(A_BY))}, 0),
            ("ihlal", {"a": _detay(_ata(A_NC))}, 1),
            ("gecici", {"a": _detay(_ata("https://ata-alfa.example/models/9001-p"))}, 2),
            ("zincir", {"a": _detay(_ata("https://ata-alfa.example/models/8001-p"))}, 1),
            ("zarf", {"a": {"data": {"license": "CC0", "originals": [_ata(A_NC)]}}}, 1),
            ("derinzarf", {"a": _zarfla(_detay(_ata(A_NC)), 4)}, 1),
            ("sekil", {"a": {"objectId": 91, "modelName": "uydurma"}}, 1),
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
                hatalar.append("[CLI-%s] rc=%d (bek %d)\n%s"
                               % (ad, r.returncode, beklenen, r.stdout))
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
            hatalar.append("[CLI-sozluk] rc=%d (bek 0)" % r.returncode)
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
            hatalar.append("[CLI-elle] adaptorsuz host ELLE-BAK kuyruguna dusmedi (rc=%d)"
                           % r.returncode)
        print("  %-4s adaptorsuz host raporda ELLE-BAK kuyrugunda" % ("ok" if ok else "HATA"))

    n += 1
    sonrasi = [(p, _sha(p)) for p, _ in oncesi]
    ok = (oncesi == sonrasi) and bool(oncesi)
    if not ok and oncesi:
        hatalar.append("[YAZMAZ] KAPI VERI YAZDI — sha256 degisti")
    print("  %-4s kapi VERI YAZMADI (%d dosya, sha256 esit)" % ("ok" if ok else "HATA", len(oncesi)))

    n += 1
    r = subprocess.run([sys.executable, _KAPI_YOL, "--kendini-test"],
                       capture_output=True, text=True)
    ok = (r.returncode == 0)
    if not ok:
        hatalar.append("[kendini-test] --kendini-test rc=%d" % r.returncode)
    print("  %-4s --kendini-test rc=0" % ("ok" if ok else "HATA"))

    # --- 8) --canli COKLU PLATFORM + --tsv (23 Eki 2026) -----------------------------
    # UCTAN-UCA (CLI duzeyinde) ve AGSIZ: `uretim_defteri` CAGRIYISI sahte defterle
    # degistirilir; boylece "hedef cozumleme -> adaptor secimi -> kimlik -> detay ->
    # yargi -> cikti" zincirinin TAMAMI ag olmadan kosulur. Sahte `pr` adaptoru gercek
    # uretim defterindekiyle AYNI kimlik kuralini kullanir (`bas-sayi:model`).
    # ONCUL OLCUM (canli 23 Eki): printables-api.detail(N) detay donuyor + description/
    # summary dolu; MaCiT PR kayitlarinin `link` alani `printables.com/model/<N>`.
    print("  --- CANLI KIPI (PR/Printables) + --tsv (UCTAN-UCA, AGSIZ) ---")
    PR_LINK = "https://www.printables.com/model/1569795-ornek"
    PR_DETAY = {"id": "1569795", "name": "uydurma-turev", "slug": "uydurma-turev",
                "license": "CC-BY", "summary": "uydurma turev",
                "description": "uydurma turev — ata linki yok"}
    PR_ADAPTORLER = [{"ad": "pr", "hostlar": ["printables.com"], "kimlik": "bas-sayi:model",
                      "ata_destegi": False, "yargi": "kisaltma",
                      "detaylar": {"1569795": PR_DETAY}}]

    def _pr_defter():
        return K.sentetik_defter(PR_ADAPTORLER)

    def _canli_cli(argv):
        """CLI'yi IN-PROCESS cagir (uretim_defteri sahte) -> (rc, stdout)."""
        eski = K.uretim_defteri
        K.uretim_defteri = _pr_defter
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = K.main(argv)
        finally:
            K.uretim_defteri = eski
        return rc, buf.getvalue()

    # P1: printables URL -> pr adaptoru secilir, kimlik cikarilir, detay cekilir.
    n += 1
    rc_p1, out_p1 = _canli_cli(["--canli", PR_LINK, "--tsv"])
    satirlar_p1 = [s for s in out_p1.split("\n") if s != ""]
    ok = (rc_p1 == 0 and len(satirlar_p1) == 2
          and satirlar_p1[0].split("\t")[0] == "urun"
          and satirlar_p1[1].split("\t")[1] == K.DURUM_ALAN_YOK)
    if not ok:
        hatalar.append("[P1-PR-HOST] printables URL -> pr adaptoru secilmedi / rc=%d "
                       "satir=%s" % (rc_p1, satirlar_p1))
    print("  %-4s P1    printables URL -> pr adaptoru + kimlik (CLI uctan-uca) rc=%d"
          % ("ok" if ok else "HATA", rc_p1))

    # P2: 'pr:N' -> ayni yol (PR->PR ata baglantisi bu bicimle de girer)
    n += 1
    rc_p2, out_p2 = _canli_cli(["--canli", "pr:1569795", "--tsv"])
    satirlar_p2 = [s for s in out_p2.split("\n") if s != ""]
    ok = (rc_p2 == 0 and len(satirlar_p2) == 2
          and satirlar_p2[1].split("\t")[1] == K.DURUM_ALAN_YOK)
    if not ok:
        hatalar.append("[P2-PR-KISA] 'pr:N' -> pr adaptoru secilmedi / rc=%d satir=%s"
                       % (rc_p2, satirlar_p2))
    print("  %-4s P2    'pr:N' -> pr adaptoru + kimlik (CLI uctan-uca) rc=%d"
          % ("ok" if ok else "HATA", rc_p2))

    # P2b: 'printables:N' (BaBa 21:4x hukmundeki yazim) -> P2 ile AYNI satir
    n += 1
    rc_p2b, out_p2b = _canli_cli(["--canli", "printables:1569795", "--tsv"])
    ok = (rc_p2b == rc_p2 and out_p2b == out_p2)
    if not ok:
        hatalar.append("[P2B-PRINTABLES] 'printables:N' 'pr:N' ile ayni sonucu vermedi / rc=%d"
                       % rc_p2b)
    print("  %-4s P2b   'printables:N' == 'pr:N' (CLI uctan-uca) rc=%d"
          % ("ok" if ok else "HATA", rc_p2b))

    # T1: --tsv basligi 6 sutun + her sonuc icin TEK satir (6 sutun)
    n += 1
    ok = (len(satirlar_p1) == 2
          and satirlar_p1[0].split("\t") == ["urun", "durum", "ata_link", "ata_lisans",
                                             "derinlik", "gerekce"]
          and len(satirlar_p1[1].split("\t")) == 6)
    if not ok:
        hatalar.append("[T1-TSV] --tsv basligi/satiri 6 sutun DEGIL: %s" % (satirlar_p1,))
    print("  %-4s T1    --tsv basligi + satir 6 sutun (rapor yerine makine ciktili)"
          % ("ok" if ok else "HATA"))

    # T1b: --tsv YOKSA insan raporu (rapor kipi) — bayraksiz cikti degismis olmaz
    n += 1
    rc_r, out_r = _canli_cli(["--canli", PR_LINK])
    ok = (rc_r == 0 and "ATA-LISANS KAPISI" in out_r
          and "urun\tdurum\tata_link" not in out_r)
    if not ok:
        hatalar.append("[T1b-TSV-YOK] --tsv bayraksiz cikti rapor kipi DEGIL: %s" % out_r[:300])
    print("  %-4s T1b   --tsv bayraksiz cikti insan raporu (degismedi)"
          % ("ok" if ok else "HATA"))

    # P3: bilinmeyen host -> KaliciHata -> CLI rc=2 (adaptoru olmayan host ELLE-BAK DEGIL)
    n += 1
    rc_p3, out_p3 = _canli_cli(["--canli", "https://bilinmeyen-host.example/model/1"])
    ok = (rc_p3 == 2 and "OLCULEMEDI" in out_p3)
    if not ok:
        hatalar.append("[P3-HOST-YOK] bilinmeyen host -> rc=2 olmadi (rc=%d)" % rc_p3)
    print("  %-4s P3    bilinmeyen host -> KaliciHata -> CLI rc=2" % ("ok" if ok else "HATA"))

    # T1c: --kuru-kosum --tsv -> stdout'TA SADECE TSV. `kuru_kosum`'un kapsam ilerleme
    # satiri (rapor metni) makine ciktisini bozardi. Ucuncu taraf cagrilari sahte
    # verilerek AGSIZ olculur (kuru_kosum -> ag + veri koku gerektirir).
    n += 1
    eski_kk = K.kuru_kosum

    def _sahte_kuru(limit=40, kaynak_filtre=None, yaz=None):
        # 🔴 GERCEK `kuru_kosum` ile AYNI varsayilan: yaz verilmezse STDOUT'a yazar
        # (yutucu lambda degil) — mutant bu varsayilani bozunca ilerleme satiri
        # stdout'a karisir ve T1c duser.
        yaz = yaz or (lambda s: sys.stdout.write(s + "\n"))
        yaz("  uygun (ata alani OLCULMUS): 1 · OLCULMEDI-adaptorlu: 2 "
            "· OLCULMEDI-adaptorsuz: 3 · tavan: 1")
        return ([{"urun": "u1", "durum": K.DURUM_ALAN_YOK, "ata_link": "",
                  "ata_lisans": None, "derinlik": 1,
                  "gerekce": "detay OLCULDU (govde TANINDI): ata alani yok"}],
                1, {"olculmedi_adaptorlu": ["a"], "olculmedi_adaptorsuz": [],
                    "taranmadi": 0, "uygun": 1})

    K.kuru_kosum = _sahte_kuru
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc_kk = K.main(["--kuru-kosum", "--tsv"])
    finally:
        K.kuru_kosum = eski_kk
    sat_kk = [s for s in buf.getvalue().split("\n") if s != ""]
    ok = (rc_kk == 2 and len(sat_kk) == 2
          and sat_kk[0].split("\t")[0] == "urun"
          and all(len(s.split("\t")) == 6 for s in sat_kk))
    if not ok:
        hatalar.append("[T1c-TSV-KURU] --kuru-kosum --tsv stdout'u sadece TSV DEGIL: %s"
                       % (sat_kk,))
    print("  %-4s T1c   --kuru-kosum --tsv stdout'ta SADECE TSV (ilerleme satiri karismaz)"
          % ("ok" if ok else "HATA"))

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
