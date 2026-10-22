#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MG — kapali marka kumesi 15. tur kabul bataryasi (4 eksen + KONTROL + 2 mutant + kontrol mutant).

Hedef: `tools/arama.py` UYUM_MARKA_IZINLI ve UYUM_MARKA_MIMAR_EKI kumesine 22 Eki 2026
BaBa hukmuyle `MG` (otomobil marque'i: MGB/Midget/MGF/ZS/MG4 ...) eklendi. MaCiT MG dilim
M1 (thingiverse 25) bunu bekliyordu. Batarya K302 emsalidir, farki: her mutant AYNI dort
ekseni kosar ve kirmizi eksen kumesi BEYANA TAM ESIT olmali (fazladan kirmizi da KUSUR).

  A1 — `MG` kanonik KABUL; yazim varyantlari (mg/Mg/mG/bosluklu/`MG Motor`/`M.G.`/`MG-`/
       Kiril homoglif) RED — fail-closed, takma ad SESSIZCE eslenmez.
  A2 — MaCiT M1'in 11 model fiksturu (`{"marka": "MG", "model": ...}`) uyum_sebebi() GECER
       ve marka uyumdan dogru turer.
  A3 — MARKA/MODEL SINIRI: `MG` (ve varyanti) MODEL alanina yazilamaz (`Rover|MG`,
       `MG|Mg`, `Ford|mg` RED) — eski `Rover|MG` verisinin duzeltilme sebebi.
  A4 — KATALOG: urunler.json'da uyum ihlali 0 ve duzeltilen kayit (`opel-c20ne-rover-mg-...`)
       uyum'unda `{"marka": "MG"}` tasiyor.
  KONTROL — FARK (izinli − eki) 139 SABIT; `MG` iki kumede de var; ELENEN/URETICI'de YOK.

  M1 — `"MG",` iki kumeden cikarilir          -> beyan {A1, A2, A3, A4}
  M2 — model alaninin varyant kontrolu susar  -> beyan {A3}
  KONTROL-MUTANT — UYUM_YIL_EN_ERKEN 1 azalir -> beyan {} (hepsi YESIL)

Mutasyon yalniz BELLEKTEKI metne uygulanir (exec ile ayri modul); canli arama.py'nin sha256'si
bas/son karsilastirilir. CIKTI yalniz stdout. rc=0 hepsi gectiyse, rc=1 tek madde dustuyse.
"""
import hashlib
import json
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "arama.py")
URUNLER = os.path.join(KOK, "urunler.json")

IZINLI_EKSI_EKI_TABAN = 139
KANONIK = "MG"
# Kiril `М` (U+041C) + Latin `G`
VARYANTLAR = ["mg", "Mg", "mG", " MG", "MG ", "M G", "MG-", "M.G.", "MG Motor",
              "MG Rover", "МG"]
M1_MODELLER = ["MGB", "MG4", "Midget", "HS", "ZS", "ZS EV", "ZR", "ZT", "TF", "Metro",
               "MGF/TF"]
SINIR_RED = [("Rover", "MG"), ("MG", "Mg"), ("Ford", "mg")]
DUZELTILEN_ID = "opel-c20ne-rover-mg-gaz-kelebe-i-adapt-r-55mm"


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
    kabul = A.uyum_marka_kanonik(KANONIK) == KANONIK
    sizan = [v for v in VARYANTLAR if A.uyum_marka_kanonik(v) != ""]
    if not sessiz:
        print("A1 kanonik %r kabul=%s · varyant RED %d/%d sizan=%s"
              % (KANONIK, kabul, len(VARYANTLAR) - len(sizan), len(VARYANTLAR), sizan))
    return kabul and not sizan


def eksen_a2(A, katalog, sessiz=False):
    red = []
    turetim_bozuk = []
    for md in M1_MODELLER:
        u = {"id": "mg-fikstur", "kategori": "Otomobil",
             "uyum": [{"marka": "MG", "model": md}], "marka": ["MG", md]}
        s = A.uyum_sebebi(u)
        if s is not None:
            red.append((md, s[:80]))
        if A.marka_uyumdan_turet(u) != ["MG", md]:
            turetim_bozuk.append(md)
    if not sessiz:
        print("A2 M1 fikstur GECEN %d/%d red=%s turetim_bozuk=%s"
              % (len(M1_MODELLER) - len(red), len(M1_MODELLER), red, turetim_bozuk))
    return not red and not turetim_bozuk


def eksen_a3(A, katalog, sessiz=False):
    sizan = [(mk, md) for mk, md in SINIR_RED
             if A.uyum_ogesi_sebebi({"marka": mk, "model": md}) is None]
    if not sessiz:
        print("A3 marka/model siniri RED %d/%d sizan=%s"
              % (len(SINIR_RED) - len(sizan), len(SINIR_RED), sizan))
    return not sizan


def eksen_a4(A, katalog, sessiz=False):
    ihlal = [x.get("id") for x in katalog if A.uyum_sebebi(x)]
    kayit = [x for x in katalog if x.get("id") == DUZELTILEN_ID]
    duzeltildi = (len(kayit) == 1
                  and {"marka": "MG"} in (kayit[0].get("uyum") or [])
                  and not any(o.get("model") == "MG" for o in kayit[0].get("uyum") or []))
    if not sessiz:
        print("A4 katalog %d kayit · uyum ihlali %d (ilk 3 %s) · %s duzeltildi=%s"
              % (len(katalog), len(ihlal), ihlal[:3], DUZELTILEN_ID, duzeltildi))
    return not ihlal and duzeltildi


EKSENLER = [("A1", eksen_a1), ("A2", eksen_a2), ("A3", eksen_a3), ("A4", eksen_a4)]


def eksen_kontrol(A):
    fark = len(A.UYUM_MARKA_IZINLI) - len(A.UYUM_MARKA_MIMAR_EKI)
    iki_kume = KANONIK in A.UYUM_MARKA_IZINLI and KANONIK in A.UYUM_MARKA_MIMAR_EKI
    disarida = (KANONIK not in A.UYUM_MARKA_ELENEN and KANONIK not in A.URETICI_MARKA)
    print("KONTROL izinli=%d eki=%d FARK=%d (taban %d) · iki kumede=%s · ELENEN/URETICI disi=%s"
          % (len(A.UYUM_MARKA_IZINLI), len(A.UYUM_MARKA_MIMAR_EKI), fark,
             IZINLI_EKSI_EKI_TABAN, iki_kume, disarida))
    return fark == IZINLI_EKSI_EKI_TABAN and iki_kume and disarida


def _kirmizi_kume(A, katalog):
    return {ad for ad, f in EKSENLER if not f(A, katalog, sessiz=True)}


def _mutant(ad, metin, eski, yeni, beyan, katalog, adet=1):
    m = metin.replace(eski, yeni)
    uygulandi = metin.count(eski) == adet and m != metin
    if not uygulandi:
        print("%s UYGULANAMADI (desen %d kez, beklenen %d) -> KUSUR" % (ad, metin.count(eski), adet))
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
    sonuc["M1"] = _mutant("M1 (MG iki kumeden cikti)", metin,
                          '    "MG",\n', "", {"A1", "A2", "A3", "A4"}, katalog, adet=2)
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
