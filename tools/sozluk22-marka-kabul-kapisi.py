#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kapali marka kumesi 22. tur kabul bataryasi (Geo, Ducabike, Ronal, Tekonsha, Bayliner,
CTEK, Cuisinart, OutIn) — 4 eksen + KONTROL + 2 mutant + kontrol mutant.

Hedef: `tools/arama.py` UYUM_MARKA_IZINLI ve UYUM_MARKA_MIMAR_EKI kumesine 27 Eki 2026
BaBa hukmuyle (tik 258 C) sekiz jeton eklendi (MaCiT esik-alti dalgalari: Geo 3 urun
hazir, `hasat_ekle` uyum fail-closed takildi = K302 sozluk boslugu). Gerekce + olculen
katalog agirligi arama.py 22. tur basliginda. 21. tur bataryasinin
(`sozluk21-marka-kabul-kapisi.py`) kardesidir; ona DOKUNULMADI.

  A1 — sekiz jeton kanonik KABUL; yazim varyantlari (kucuk/buyuk harf, bosluklu, tireli,
       Kiril homoglif) RED — fail-closed, sessiz esleme YOK.
  A2 — HASAT fiksturu: `{"marka":"Ducabike"}` (MODELSIZ) ve `{"marka":"Geo",
       "model":"Tracker"}` uyum_sebebi() GECER, `marka_uyumdan_turet` dogru turer.
  A3 — MARKA/MODEL SINIRI: jetonlar MODEL alanina yazilamaz (`Suzuki|Geo`,
       `Ducati|Ducabike`, `Renault|Ronal`, `Nespresso|OutIn` RED).
  A4 — KATALOG: urunler.json'da uyum ihlali 0; sekiz jetonun HER BIRI icin `marka[]`'si
       onu iceren kayit VAR (OLCULDU 27 Eki main 40.937: Geo 5 · digerleri 2) ve kanonik.
  KONTROL — FARK (izinli − eki) 139 SABIT; sekiz jeton IKI kumede de var; 21. tur
            jetonlari (Lada, NIU) ve degismeyen `Mondial`/`Kuba` ayni durumda.

  M1 — sekiz jeton iki kumeden cikarilir               -> beyan {A1, A2, A3, A4}
  M2 — model alaninin varyant kontrolu susar           -> beyan {A3}
  KONTROL-MUTANT — UYUM_YIL_EN_ERKEN 1 azalir          -> beyan {} (hepsi YESIL)

Mutasyon yalniz BELLEKTEKI metne uygulanir (exec ile ayri modul); canli arama.py'nin
sha256'si bas/son karsilastirilir. CIKTI yalniz stdout. rc=0 hepsi gectiyse, rc=1 tek
madde dustuyse.
"""
import hashlib
import json
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "arama.py")
URUNLER = os.path.join(KOK, "urunler.json")

IZINLI_EKSI_EKI_TABAN = 139
HEDEF = ("Geo", "Ducabike", "Ronal", "Tekonsha", "Bayliner", "CTEK", "Cuisinart", "OutIn")
HEDEF_SATIRI = ('    "Geo", "Ducabike", "Ronal", "Tekonsha", "Bayliner", "CTEK", '
                '"Cuisinart", "OutIn",\n')
KONUM = "Suzuki|Geo"
# Kiril homoglifler: `е` (U+0435) · `о` (U+043E) · `а` (U+0430) · `С` (U+0421) ·
# `Т` (U+0422) · `К` (U+041A) · `і` (U+0456)
VARYANTLAR = {
    "Geo": ["geo", "GEO", "G eo", " Geo", "Geo ", "Geo-", "Gеo"],
    "Ducabike": ["ducabike", "DUCABIKE", "Duca bike", " Ducabike", "Ducabike ", "Duca-bike",
                 "Ducаbike"],
    "Ronal": ["ronal", "RONAL", "Ro nal", " Ronal", "Ronal ", "Ronal-", "Rоnal"],
    "Tekonsha": ["tekonsha", "TEKONSHA", "Tek onsha", " Tekonsha", "Tekonsha ", "Tekonsha-",
                 "Tеkonsha"],
    "Bayliner": ["bayliner", "BAYLINER", "Bay liner", " Bayliner", "Bayliner ", "Bay-liner",
                 "Bаyliner"],
    "CTEK": ["ctek", "Ctek", "C TEK", " CTEK", "CTEK ", "C-TEK", "СТЕК"],
    "Cuisinart": ["cuisinart", "CUISINART", "Cuisin art", " Cuisinart", "Cuisinart ",
                  "Cuisinart-", "Cuіsinart"],
    "OutIn": ["outin", "Outin", "OUTIN", "Out In", " OutIn", "OutIn ", "Out-In", "OutІn"],
}
FIKSTUR = [({"marka": "Ducabike"}, ["Ducabike"]),
           ({"marka": "Geo", "model": "Tracker"}, ["Geo", "Tracker"])]
SINIR_RED = [("Suzuki", "Geo"), ("Ducati", "Ducabike"), ("Renault", "Ronal"),
             ("Nespresso", "OutIn")]
DEGISMEMESI_GEREKEN = ("Mondial", "Kuba")
ONCEKI_TUR = ("Lada", "NIU")
VERI_SARTLI = HEDEF              # sekizinin de katalogda kaydi VAR (olculdu, main 40.937)


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _yukle_arama():
    sys.path.insert(0, os.path.dirname(ARAC))
    import arama                                                    # noqa: PLC0415
    return arama


def _mutant_yukle(metin):
    mod = type(sys)("arama_mutant")
    mod.__file__ = ARAC
    exec(compile(metin, ARAC, "exec"), mod.__dict__)
    return mod


def eksen_a1(A, katalog, sessiz=False):
    red = {}
    for kanonik, varyantlar in VARYANTLAR.items():
        kabul = A.uyum_marka_kanonik(kanonik) == kanonik
        sizan = [v for v in varyantlar if A.uyum_marka_kanonik(v) != ""]
        red[kanonik] = (kabul, sizan)
        if not sessiz:
            print("A1 kanonik %r kabul=%s · varyant RED %d/%d sizan=%s"
                  % (kanonik, kabul, len(varyantlar) - len(sizan), len(varyantlar), sizan))
    return all(k and not s for k, s in red.values())


def eksen_a2(A, katalog, sessiz=False):
    red = []
    turetim_bozuk = []
    for f, bekl in FIKSTUR:
        u = {"id": "s22-fikstur", "kategori": "Otomobil", "uyum": [f], "marka": bekl}
        s = A.uyum_sebebi(u)
        if s is not None:
            red.append((f, s[:80]))
        if A.marka_uyumdan_turet(u) != bekl:
            turetim_bozuk.append((f, A.marka_uyumdan_turet(u)))
    if not sessiz:
        print("A2 fikstur GECEN %d/%d (modelsiz + model'li) red=%s turetim_bozuk=%s"
              % (len(FIKSTUR) - len(red), len(FIKSTUR), red, turetim_bozuk))
    return not red and not turetim_bozuk


def eksen_a3(A, katalog, sessiz=False):
    sizan = [(mk, md) for mk, md in SINIR_RED
             if A.uyum_ogesi_sebebi({"marka": mk, "model": md}) is None]
    if not sessiz:
        print("A3 marka/model siniri (%s ...) RED %d/%d sizan=%s"
              % (KONUM, len(SINIR_RED) - len(sizan), len(SINIR_RED), sizan))
    return not sizan


def eksen_a4(A, katalog, sessiz=False):
    ihlal = [x.get("id") for x in katalog if A.uyum_sebebi(x)]
    sayi = {j: sum(1 for x in katalog if j in (x.get("marka") or [])) for j in HEDEF}
    kanonik = all(A.uyum_marka_kanonik(j) == j for j in HEDEF)
    if not sessiz:
        print("A4 katalog %d kayit · uyum ihlali %d (ilk 3 %s) · marka[] %s (sart: hepsi > 0) · "
              "kanonik=%s" % (len(katalog), len(ihlal), ihlal[:3], sayi, kanonik))
    return not ihlal and kanonik and all(sayi[j] > 0 for j in VERI_SARTLI)


EKSENLER = [("A1", eksen_a1), ("A2", eksen_a2), ("A3", eksen_a3), ("A4", eksen_a4)]


def eksen_kontrol(A):
    fark = len(A.UYUM_MARKA_IZINLI) - len(A.UYUM_MARKA_MIMAR_EKI)
    iki_kume = all(j in A.UYUM_MARKA_IZINLI and j in A.UYUM_MARKA_MIMAR_EKI
                   for j in HEDEF + ONCEKI_TUR)
    sabit = all(b in A.UYUM_MARKA_IZINLI and b not in A.UYUM_MARKA_MIMAR_EKI
                for b in DEGISMEMESI_GEREKEN)
    print("KONTROL izinli=%d eki=%d FARK=%d (taban %d) · iki kumede (22.+21. tur)=%s · "
          "%s degismedi=%s" % (len(A.UYUM_MARKA_IZINLI), len(A.UYUM_MARKA_MIMAR_EKI), fark,
                               IZINLI_EKSI_EKI_TABAN, iki_kume,
                               "/".join(DEGISMEMESI_GEREKEN), sabit))
    return fark == IZINLI_EKSI_EKI_TABAN and iki_kume and sabit


def _kirmizi_kume(A, katalog):
    return {ad for ad, f in EKSENLER if not f(A, katalog, sessiz=True)}


def _mutant(ad, metin, eski, yeni, beyan, katalog, adet=1):
    m = metin.replace(eski, yeni)
    uygulandi = metin.count(eski) == adet and m != metin
    if not uygulandi:
        print("%s UYGULANAMADI (desen %d kez, beklenen %d) -> KUSUR"
              % (ad, metin.count(eski), adet))
        return False
    kirmizi = _kirmizi_kume(_mutant_yukle(m), katalog)
    esit = kirmizi == set(beyan)
    print("%s kirmizi=%s beyan=%s -> %s" % (ad, sorted(kirmizi), sorted(beyan),
                                            "ESIT" if esit else "ESIT DEGIL (KUSUR)"))
    return esit


def main():
    sha_bas = _sha(ARAC)
    A = _yukle_arama()
    with open(URUNLER, encoding="utf-8") as f:
        katalog = json.load(f)
    with open(ARAC, encoding="utf-8") as f:
        metin = f.read()

    sonuc = {ad: f(A, katalog) for ad, f in EKSENLER}
    sonuc["KONTROL"] = eksen_kontrol(A)
    print()
    sonuc["M1"] = _mutant("M1 (sekiz jeton iki kumeden cikti)", metin, HEDEF_SATIRI, "",
                          {"A1", "A2", "A3", "A4"}, katalog, adet=2)
    sonuc["M2"] = _mutant("M2 (model varyant kontrolu sustu)", metin,
                          "        sebep = marka_varyanti_sebebi(ad, oge.get(ad))\n",
                          "        sebep = None if ad == \"model\" else "
                          "marka_varyanti_sebebi(ad, oge.get(ad))\n",
                          {"A3"}, katalog)
    sonuc["KONTROL-MUTANT"] = _mutant("KONTROL-MUTANT (UYUM_YIL_EN_ERKEN -1)", metin,
                                      "UYUM_YIL_EN_ERKEN = 1900", "UYUM_YIL_EN_ERKEN = 1899",
                                      set(), katalog)
    sha_son = _sha(ARAC)
    sonuc["SHA"] = sha_bas == sha_son
    print("SHA arama.py bas=%s son=%s %s" % (sha_bas[:12], sha_son[:12],
                                             "AYNI" if sonuc["SHA"] else "DEGISTI (KUSUR)"))
    print()
    gecen = sum(1 for v in sonuc.values() if v)
    print("SONUC: %s — gecen %d · kalan %d · iddia %d"
          % ("YESIL" if gecen == len(sonuc) else "KIRMIZI", gecen, len(sonuc) - gecen,
             len(sonuc)))
    sys.exit(0 if gecen == len(sonuc) else 1)


if __name__ == "__main__":
    main()
