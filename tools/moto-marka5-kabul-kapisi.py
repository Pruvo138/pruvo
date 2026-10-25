#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Moto — kapali marka kumesi 18. tur kabul bataryasi (4 eksen + KONTROL + 2 mutant + kontrol mutant).

Hedef: `tools/arama.py` UYUM_MARKA_IZINLI ve UYUM_MARKA_MIMAR_EKI kumesine 25 Eki 2026
BaBa hukmuyle (tik 126/129) `Voge`, `Keeway`, `Benelli`, `TVS` eklendi
(MaCiT 24 Eki 22:04: Voge ekle K302 "top-level marka BOS"). 17. tur bataryasinin
(`moto-marka-kabul-kapisi.py`, Kymco/RKS) kardesidir; o bataryaya DOKUNULMADI.
19. tur (ayni gun): `MV Agusta` index.html `BILESIK_MARKA` aynasiyla AYNI dalda girdi;
ayna = otorite esitligini model-uyelik-kapisi K8 olcer, burada A1 varyantlari + A3 siniri + M3.

  A1 — dort jeton kanonik KABUL; yazim varyantlari (kucuk/buyuk harf, bosluklu, tireli,
       Kiril homoglif) RED — fail-closed, sessiz esleme YOK.
  A2 — MaCiT Voge fiksturu: `{"marka":"Voge"}` (MODELSIZ) ve `{"marka":"Benelli",
       "model":"TRK 502"}` uyum_sebebi() GECER, `marka_uyumdan_turet` dogru turer.
  A3 — MARKA/MODEL SINIRI: jetonlar MODEL alanina yazilamaz (`Honda|Voge`,
       `Yamaha|Benelli`, `Suzuki|TVS` RED).
  A4 — KATALOG: urunler.json'da uyum ihlali 0 ve `marka[]`'si `Benelli` iceren kayitlar
       (OLCULDU 25 Eki: 13, uyum NULL) kanonik.
  KONTROL — FARK (izinli − eki) 139 SABIT; dort jeton IKI kumede de var; 17. tur
            jetonlari (`Kymco`/`RKS`) ve degismeyen `Mondial`/`Kuba` ayni durumda.

  M1 — dort jeton iki kumeden cikarilir                -> beyan {A1, A2, A3, A4}
  M2 — model alaninin varyant kontrolu susar           -> beyan {A3}
  M3 — 19. tur `MV Agusta` iki kumeden cikarilir       -> beyan {A1, A3} (+A4 katalogda MV kaydi varsa)
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
HEDEF = ("Voge", "Keeway", "Benelli", "TVS")
HEDEF_SATIRI = '    "Voge", "Keeway", "Benelli", "TVS",\n'
# 19. tur (25 Eki): index.html BILESIK_MARKA aynasiyla AYNI dalda giren cok kelimeli jeton.
HEDEF_19 = ("MV Agusta",)
HEDEF_19_SATIRI = '    "MV Agusta",\n'
KONUM = "Honda|Voge"
# Kiril homoglifler: `В` (U+0412) · `К` (U+041A) · `Т` (U+0422)
VARYANTLAR = {
    "Voge": ["voge", "VOGE", " Voge", "Voge ", "Vo ge", "Voge-", "Вoge"],
    "Keeway": ["keeway", "KEEWAY", "Kee Way", "Keeway ", "Keeway-", "Кeeway"],
    "Benelli": ["benelli", "BENELLI", "Bene lli", "Benelli ", "Benelli-", "Вenelli"],
    "TVS": ["tvs", "Tvs", "T V S", "TVS ", "T-V-S", "Тvs"],
    "MV Agusta": ["mv agusta", "MV AGUSTA", "MVAgusta", "MV-Agusta", " MV Agusta",
                  "MV Agusta ", "Мv Agusta"],
}
FIKSTUR = [({"marka": "Voge"}, ["Voge"]),
           ({"marka": "Benelli", "model": "TRK 502"}, ["Benelli", "TRK 502"])]
SINIR_RED = [("Honda", "Voge"), ("Yamaha", "Benelli"), ("Suzuki", "TVS"), ("Suzuki", "MV Agusta")]
DEGISMEMESI_GEREKEN = ("Mondial", "Kuba")
ONCEKI_TUR = ("Kymco", "RKS")


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
        u = {"id": "moto5-fikstur", "kategori": "Motosiklet", "uyum": [f], "marka": bekl}
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
        print("A3 marka/model siniri (%s) RED %d/%d sizan=%s"
              % (KONUM, len(SINIR_RED) - len(sizan), len(SINIR_RED), sizan))
    return not sizan


def eksen_a4(A, katalog, sessiz=False):
    ihlal = [x.get("id") for x in katalog if A.uyum_sebebi(x)]
    benelli = [x for x in katalog if "Benelli" in (x.get("marka") or [])]
    kanonik = all(A.uyum_marka_kanonik(x["marka"][0]) == x["marka"][0] for x in benelli)
    if not sessiz:
        print("A4 katalog %d kayit · uyum ihlali %d (ilk 3 %s) · marka[] Benelli %d kayit "
              "kanonik=%s" % (len(katalog), len(ihlal), ihlal[:3], len(benelli), kanonik))
    return not ihlal and kanonik and len(benelli) > 0


EKSENLER = [("A1", eksen_a1), ("A2", eksen_a2), ("A3", eksen_a3), ("A4", eksen_a4)]


def eksen_kontrol(A):
    fark = len(A.UYUM_MARKA_IZINLI) - len(A.UYUM_MARKA_MIMAR_EKI)
    iki_kume = all(j in A.UYUM_MARKA_IZINLI and j in A.UYUM_MARKA_MIMAR_EKI
                   for j in HEDEF + HEDEF_19 + ONCEKI_TUR)
    sabit = all(b in A.UYUM_MARKA_IZINLI and b not in A.UYUM_MARKA_MIMAR_EKI
                for b in DEGISMEMESI_GEREKEN)
    print("KONTROL izinli=%d eki=%d FARK=%d (taban %d) · iki kumede (18.+17. tur)=%s · "
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
    sonuc["M1"] = _mutant("M1 (dort jeton iki kumeden cikti)", metin, HEDEF_SATIRI, "",
                          {"A1", "A2", "A3", "A4"}, katalog, adet=2)
    sonuc["M2"] = _mutant("M2 (model varyant kontrolu sustu)", metin,
                          "        sebep = marka_varyanti_sebebi(ad, oge.get(ad))\n",
                          "        sebep = None if ad == \"model\" else "
                          "marka_varyanti_sebebi(ad, oge.get(ad))\n",
                          {"A3"}, katalog)
    # 🔴 M3 BEYANI KATALOGDAN TURETILIR (25 Eki 2026): beyan 07:42'de MV Agusta 0 urunken
    # {A1, A3} diye civilendi; MaCiT 09:17'de 5 MV urunu ekleyince ayni mutant A4'u de
    # (katalog uyum ihlali) DOGRU olarak kirmiziya cevirdi -> beyan bayat, Pages 2deeb7f8
    # serit-a2 KIRMIZI, yayin SKIPPED. Kural: katalogda HEDEF_19 markali kayit varsa A4 beyana girer.
    m3_beyan = {"A1", "A3"}
    if any(j in (x.get("marka") or []) for x in katalog for j in HEDEF_19):
        m3_beyan.add("A4")
    sonuc["M3"] = _mutant("M3 (19. tur MV Agusta iki kumeden cikti)", metin, HEDEF_19_SATIRI,
                          "", m3_beyan, katalog, adet=2)
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
