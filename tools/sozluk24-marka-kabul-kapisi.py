#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kapali marka kumesi 24. tur kabul bataryasi (3 urun markasi) — 4 eksen + KONTROL
+ 2 mutant + kontrol mutant.

Hedef: `tools/arama.py` UYUM_MARKA_IZINLI ve UYUM_MARKA_MIMAR_EKI kumesine 29 Eki 2026
MaCiT ES20 blokaji icin 3 jeton eklendi (Keurig, Moccamaster, Roland; gerekce arama.py
24. tur basliginda). 23. tur bataryasinin (`sozluk23-marka-kabul-kapisi.py`) kardesidir;
ona DOKUNULMADI.

  A1 — 3 jeton kanonik KABUL; yazim varyantlari (kucuk/buyuk harf, bas/son bosluk, tire,
       Kiril homoglif) RED — fail-closed, sessiz esleme YOK. Varyantlar jetondan TURETILIR.
  A2 — HASAT fiksturu: `{"marka":"Keurig"}` (MODELSIZ) ve `{"marka":"Moccamaster",
       "model":"KBG"}` uyum_sebebi() GECER, `marka_uyumdan_turet` dogru turer.
  A3 — MARKA/MODEL SINIRI: jetonlar MODEL alanina yazilamaz (`Philips|Keurig`,
       `Bosch|Moccamaster`, `Yamaha|Roland` RED).
  A4 — KATALOG: urunler.json'da uyum ihlali 0; 3 jetonun HER BIRI icin `marka[]`'si onu
       iceren kayit VAR ve kanonik.
  KONTROL — FARK (izinli − eki) 139 SABIT; 3 jeton IKI kumede de var; 23. tur jetonlari
            (Gaggia, Polaris) ve degismeyen `Mondial`/`Kuba` ayni durumda; 23. turda
            DISARIDA birakilan 22 jetonun HICBIRI kumede DEGIL (yargi geri sizmaz).

  M1 — 3 jeton iki kumeden cikarilir                   -> beyan {A1, A2, A3, A4}
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
HEDEF = ("Keurig", "Moccamaster", "Roland")
HEDEF_SATIRI = '    "Keurig", "Moccamaster", "Roland",\n'
DISARIDA = ("La Scala", "Mr. Coffee", "Peak Design", "Proctor Silex", "MINI", "Alpine", "TRD", "Denso", "Nordlinger", "Acura", "Avanza", "Corsair",
            "Pontiac", "Brodit", "Givi", "Gurtner", "Haibike", "Mennekes", "OOONO",
            "Trail Tech", "SMEG", "Quad Lock")
KONUM = "Philips|Keurig"
# Kiril homoglifler (Latin -> Kiril): a e o c p x A E O C P T K M H B
HOMOGLIF = {"a": "а", "e": "е", "o": "о", "c": "с", "p": "р", "x": "х", "A": "А",
            "E": "Е", "O": "О", "C": "С", "P": "Р", "T": "Т", "K": "К", "M": "М",
            "H": "Н", "B": "В"}
FIKSTUR = [({"marka": "Keurig"}, ["Keurig"]),
           ({"marka": "Moccamaster", "model": "KBG"}, ["Moccamaster", "KBG"])]
SINIR_RED = [("Philips", "Keurig"), ("Bosch", "Moccamaster"), ("Yamaha", "Roland")]
DEGISMEMESI_GEREKEN = ("Mondial", "Kuba")
ONCEKI_TUR = ("Gaggia", "Polaris")
VERI_SARTLI = HEDEF


def varyantlar(t):
    """Jetondan TURETILEN yazim varyantlari; jetonun kendisine esit olan elenir."""
    aday = [t.lower(), t.upper(), " " + t, t + " ", t + "-"]
    for i, ch in enumerate(t):
        if ch in HOMOGLIF:
            aday.append(t[:i] + HOMOGLIF[ch] + t[i + 1:])
            break
    goruldu, out = set(), []
    for v in aday:
        if v != t and v not in goruldu:
            goruldu.add(v)
            out.append(v)
    return out


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
    kabul_yok, sizan, toplam = [], [], 0
    for t in HEDEF:
        if A.uyum_marka_kanonik(t) != t:
            kabul_yok.append(t)
        for v in varyantlar(t):
            toplam += 1
            if A.uyum_marka_kanonik(v) != "":
                sizan.append(v)
    if not sessiz:
        print("A1 kanonik kabul %d/%d (kabul edilmeyen=%s) · varyant RED %d/%d sizan=%s"
              % (len(HEDEF) - len(kabul_yok), len(HEDEF), kabul_yok, toplam - len(sizan),
                 toplam, sizan))
    return not kabul_yok and not sizan and toplam > 0


def eksen_a2(A, katalog, sessiz=False):
    red = []
    turetim_bozuk = []
    for f, bekl in FIKSTUR:
        u = {"id": "s24-fikstur", "kategori": "Elektronik", "uyum": [f], "marka": bekl}
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
    eksik = [j for j in VERI_SARTLI if sayi[j] == 0]
    kanonik = all(A.uyum_marka_kanonik(j) == j for j in HEDEF)
    if not sessiz:
        print("A4 katalog %d kayit · uyum ihlali %d (ilk 3 %s) · marka[] kaydi olmayan jeton %d %s"
              " · kanonik=%s" % (len(katalog), len(ihlal), ihlal[:3], len(eksik), eksik,
                                 kanonik))
    return not ihlal and kanonik and not eksik


EKSENLER = [("A1", eksen_a1), ("A2", eksen_a2), ("A3", eksen_a3), ("A4", eksen_a4)]


def eksen_kontrol(A):
    fark = len(A.UYUM_MARKA_IZINLI) - len(A.UYUM_MARKA_MIMAR_EKI)
    iki_kume = all(j in A.UYUM_MARKA_IZINLI and j in A.UYUM_MARKA_MIMAR_EKI
                   for j in HEDEF + ONCEKI_TUR)
    sabit = all(b in A.UYUM_MARKA_IZINLI and b not in A.UYUM_MARKA_MIMAR_EKI
                for b in DEGISMEMESI_GEREKEN)
    sizan = [d for d in DISARIDA if d in A.UYUM_MARKA_IZINLI or d in A.UYUM_MARKA_MIMAR_EKI]
    print("KONTROL izinli=%d eki=%d FARK=%d (taban %d) · iki kumede (24.+23. tur)=%s · "
          "%s degismedi=%s · disarida birakilan kumeye sizan=%s"
          % (len(A.UYUM_MARKA_IZINLI), len(A.UYUM_MARKA_MIMAR_EKI), fark,
             IZINLI_EKSI_EKI_TABAN, iki_kume, "/".join(DEGISMEMESI_GEREKEN), sabit, sizan))
    return fark == IZINLI_EKSI_EKI_TABAN and iki_kume and sabit and not sizan


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
    sonuc["M1"] = _mutant("M1 (3 jeton iki kumeden cikti)", metin, HEDEF_SATIRI, "",
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
