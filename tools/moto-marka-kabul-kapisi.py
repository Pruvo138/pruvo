#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Moto — kapali marka kumesi 17. tur kabul bataryasi (4 eksen + KONTROL + 2 mutant + kontrol mutant).

Hedef: `tools/arama.py` UYUM_MARKA_IZINLI ve UYUM_MARKA_MIMAR_EKI kumesine 23 Eki 2026
BaBa hukmuyle `Kymco` ve `RKS` eklendi (MaCiT KY1 sikinti). MG/DS bataryalarinin kardesidir;
farki: HEDEF iki jetondur ve KONTROL "degismeyen kume" iddiasini da olcer (Mondial/Kuba).

  A1 — `Kymco` ve `RKS` kanonik KABUL; yazim varyantlari (kymco/KYMCO/`Kymco Motor`/
       `Kym Co`/bosluklu/Kiril homoglif + rks/Rks/`R-K-S`) RED — fail-closed, sessiz
       esleme YOK. Kanonik yazim disi hicbir jeton BILESIK tabloya girmedigi icin
       varyant RED'leri kirilamaz.
  A2 — MaCiT KY1 fiksturu: `{"marka":"Kymco"}` (MODELSiZ) ve `{"marka":"Kymco",
       "model":"Agility"}` uyum_sebebi() GECER, `marka_uyumdan_turet` dogru turer.
  A3 — MARKA/MODEL SINIRI: `Kymco`/`RKS` (ve varyantlari) MODEL alanina yazilamaz
       (`Honda|Kymco`, `Honda|RKS`, `Yamaha|Kymco` RED) — marka modelin icine girmez.
  A4 — KATALOG: urunler.json'da uyum ihlali 0 ve 24 Kymco kaydi `marka:["Kymco"]`
       tasiyor (OLCULDU: marka[] 24, uyum[] 0, kategori `Motosiklet`).
  KONTROL — FARK (izinli − eki) 139 SABIT; iki jeton IKI kumede de var; **degismeyen
            kume** `Mondial`/`Kuba` IZINLI'de ve MIMAR_EKI disinda ayni durumda.

  M1 — `"Kymco", "RKS",` iki kumeden cikarilir        -> beyan {A1, A2, A3, A4}
       (A4 de KIRMIZI OLCULDU: 24 Kymco kaydi `marka["Kymco"]` tasiyor ve jeton kumeden
       cikinca O KAYITLARIN kanonikligi duser — yani A4 jetona bagli, sonuc OLCULECEK
       sekilde beyan edildi: tahmin degil.)
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
HEDEF = ("Kymco", "RKS")
KONUM = "Honda|Kymco"
# Kiril homoglifler: `К` (U+041A) + Latin `ymco` ; `Р` (U+0420) + Latin `KS`
VARYANTLAR = {
    "Kymco": ["kymco", "KYMCO", "Kymco Motor", " Kymco", "Kymco ", "Kym Co", "Kymco-",
              "Кymco"],
    "RKS": ["rks", "Rks", "r k s", "RKS ", " RKS", "R-K-S", "RKS-", "РKS"],
}
KY1_FIKSTUR = [{"marka": "Kymco"}, {"marka": "Kymco", "model": "Agility"}]
SINIR_RED = [("Honda", "Kymco"), ("Honda", "RKS"), ("Yamaha", "Kymco")]
DEGISMEMESI_GEREKEN = ("Mondial", "Kuba")


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
    beklenen = [["Kymco"], ["Kymco", "Agility"]]
    for f, bekl in zip(KY1_FIKSTUR, beklenen):
        u = {"id": "kymco-ky1-fikstur", "kategori": "Motosiklet", "uyum": [f],
             "marka": bekl}
        s = A.uyum_sebebi(u)
        if s is not None:
            red.append((f, s[:80]))
        if A.marka_uyumdan_turet(u) != bekl:
            turetim_bozuk.append((f, A.marka_uyumdan_turet(u)))
    if not sessiz:
        print("A2 KY1 fikstur GECEN %d/%d (modelsiz + model'li) red=%s turetim_bozuk=%s"
              % (len(KY1_FIKSTUR) - len(red), len(KY1_FIKSTUR), red, turetim_bozuk))
    return not red and not turetim_bozuk


def eksen_a3(A, katalog, sessiz=False):
    sizan = [(mk, md) for mk, md in SINIR_RED
             if A.uyum_ogesi_sebebi({"marka": mk, "model": md}) is None]
    if not sessiz:
        print("A3 marka/model siniri (%s) RED %d/%d sizan=%s"
              % (KONUM, len(SINIR_RED) - len(sizan), len(SINIR_RED), sizan))
    return not sizan


def eksen_a4(A, katalog, sessiz=False):
    ihlal = [x.get("id") for x in katalog if A.uyum_sebebi(x)]
    kymco_kayit = [x for x in katalog if x.get("marka") == ["Kymco"]]
    kanonik = all(A.uyum_marka_kanonik(m) == m
                  for x in kymco_kayit for m in (x.get("marka") or []))
    if not sessiz:
        print("A4 katalog %d kayit · uyum ihlali %d (ilk 3 %s) · marka[\"Kymco\"] %d kayit "
              "kanonik=%s"
              % (len(katalog), len(ihlal), ihlal[:3], len(kymco_kayit), kanonik))
    return not ihlal and kanonik and len(kymco_kayit) > 0


EKSENLER = [("A1", eksen_a1), ("A2", eksen_a2), ("A3", eksen_a3), ("A4", eksen_a4)]


def eksen_kontrol(A):
    fark = len(A.UYUM_MARKA_IZINLI) - len(A.UYUM_MARKA_MIMAR_EKI)
    iki_kume = all(j in A.UYUM_MARKA_IZINLI and j in A.UYUM_MARKA_MIMAR_EKI
                    for j in HEDEF)
    sabit = (all(b in A.UYUM_MARKA_IZINLI and b not in A.UYUM_MARKA_MIMAR_EKI
                 for b in DEGISMEMESI_GEREKEN))
    print("KONTROL izinli=%d eki=%d FARK=%d (taban %d) · iki kumede=%s · %s degismedi=%s"
          % (len(A.UYUM_MARKA_IZINLI), len(A.UYUM_MARKA_MIMAR_EKI), fark,
             IZINLI_EKSI_EKI_TABAN, iki_kume, "/".join(DEGISMEMESI_GEREKEN), sabit))
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
    sonuc["M1"] = _mutant("M1 (Kymco+RKS iki kumeden cikti)", metin,
                          '    "Kymco", "RKS",\n', "", {"A1", "A2", "A3", "A4"},
                          katalog, adet=2)
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