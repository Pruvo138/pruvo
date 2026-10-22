#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DS — kapali marka kumesi 16. tur kabul bataryasi (5 eksen + KONTROL + 3 mutant + kontrol mutant).

Hedef: `tools/arama.py` UYUM_MARKA_IZINLI ve UYUM_MARKA_MIMAR_EKI kumesine 22 Eki 2026 BaBa
hukmuyle `DS` (DS Automobiles, 2014'ten beri ayri marque) eklendi. Ayni turda klasik Citroen
DS (1955–75, GERCEK Citroen modeli, CANLI `/marka/citroen/ds/`) KAPALI cift istisnasiyla
(`MARKA_ADLI_MODEL_IZINLI = {("Citroen", "DS")}`) korundu. MG bataryasinin kardesi; fark:
A4 sayfa uretecini (`marka_model_build`) MUTANT arama ile YENIDEN yukleyip olcer.

  A1 — `DS` kanonik KABUL; yazim varyantlari (ds/Ds/`DS Automobiles`/`D.S.`/bosluklu/Kiril) RED.
  A2 — DS model fiksturu (`{"marka": "DS", "model": DS3/DS4/DS7 ...}`) uyum_sebebi() GECER.
  A3 — MARKA/MODEL SINIRI: `Citroen|DS` GECER (istisna); `Peugeot|DS`, `Citroen|ds`,
       `Citroen|D.S.`, `Ford|DS`, `Citroen` motor=`DS` RED (istisna DAR).
  A4 — SAYFA: `/marka/citroen/ds/` kovasi YAYIMLANIR; `Peugeot|DS` kovasi YOK; baglamsiz
       `marka_jetonu_mu("DS")` True, `Citroen` baglaminda False, `Peugeot` baglaminda True.
  A5 — KATALOG: uyum ihlali 0; duzeltilen 2 kayit uyum'unda `{"marka": "DS"}` tasiyor.
  KONTROL — FARK (izinli − eki) 139 SABIT; `DS` iki kumede; istisna tablosu TAM
            `{("Citroen", "DS")}` (sessiz buyume KIRMIZI).

  M1 — `"DS",` iki kumeden cikarilir                    -> beyan {A1, A2, A3, A4, A5}
  M2 — uyum_ogesi_sebebi istisna satiri dusurulur       -> beyan {A3, A5}
  M3 — marka_jetonu_mu istisna satiri dusurulur (uretec) -> beyan {A4}
  KONTROL-MUTANT — UYUM_YIL_EN_ERKEN 1 azalir           -> beyan {} (hepsi YESIL)

Mutasyon yalniz BELLEKTEKI metne uygulanir; canli dosyalarin sha256'si bas/son karsilastirilir.
CIKTI yalniz stdout. rc=0 hepsi gectiyse, rc=1 tek madde dustuyse.
"""
import hashlib
import importlib.util
import json
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "arama.py")
MMB = os.path.join(KOK, "tools", "marka_model_build.py")
URUNLER = os.path.join(KOK, "urunler.json")
INDEX = os.path.join(KOK, "index.html")

IZINLI_EKSI_EKI_TABAN = 139
KANONIK = "DS"
ISTISNA = {("Citroen", "DS")}
# Kiril `Ѕ` (U+0405) + Latin `D`
VARYANTLAR = ["ds", "Ds", "dS", " DS", "DS ", "D S", "DS-", "D.S.", "DS Automobiles",
              "DS Auto", "DЅ"]
DS_MODELLER = ["DS3", "DS 3", "DS4", "DS5", "DS7", "DS 7 Crossback", "DS9"]
SINIR_GECER = [("Citroen", "DS")]
SINIR_RED = [("Peugeot", "DS"), ("Citroen", "ds"), ("Citroen", "D.S."), ("Ford", "DS")]
DUZELTILEN = ["peugeot-citroen-ds-uyumlu-n-cam-vin-numaras-kapat-c",
              "citroen-peugeot-ds-uyumlu-silecek-klipsi"]

M2_ESKI = ('        if ad == "model" and marka_adli_model_mi(ham, oge.get(ad)):\n'
           '            continue\n')
M3_ESKI = ('    if marka is not None and (marka, t) in MARKA_ADLI_MODEL:\n'
           '        return False\n')


def _sha(yol):
    with open(yol, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return f.read()


def _arama_yukle(metin):
    mod = type(sys)("arama")
    mod.__file__ = ARAC
    exec(compile(metin, ARAC, "exec"), mod.__dict__)
    return mod


def _mmb_yukle(arama_mod, mmb_metin):
    """Sayfa uretecini VERILEN arama modulune bagli olarak yukler (import aninda okur)."""
    araclar = os.path.dirname(ARAC)
    if araclar not in sys.path:
        sys.path.insert(0, araclar)
    eski = sys.modules.get("arama")
    sys.modules["arama"] = arama_mod
    try:
        mod = type(sys)("marka_model_build_ds")
        mod.__file__ = MMB
        exec(compile(mmb_metin, MMB, "exec"), mod.__dict__)
    finally:
        if eski is None:
            sys.modules.pop("arama", None)
        else:
            sys.modules["arama"] = eski
    return mod


class Ortam:
    def __init__(self, A, M, katalog, index_html):
        self.A, self.M, self.katalog, self.index_html = A, M, katalog, index_html


def eksen_a1(o, sessiz=False):
    A = o.A
    kabul = A.uyum_marka_kanonik(KANONIK) == KANONIK
    sizan = [v for v in VARYANTLAR if A.uyum_marka_kanonik(v) != ""]
    if not sessiz:
        print("A1 kanonik %r kabul=%s · varyant RED %d/%d sizan=%s"
              % (KANONIK, kabul, len(VARYANTLAR) - len(sizan), len(VARYANTLAR), sizan))
    return kabul and not sizan


def eksen_a2(o, sessiz=False):
    red = []
    for md in DS_MODELLER:
        u = {"id": "ds-fikstur", "kategori": "Otomobil",
             "uyum": [{"marka": "DS", "model": md}], "marka": ["DS", md]}
        s = o.A.uyum_sebebi(u)
        if s is not None:
            red.append((md, s[:80]))
    if not sessiz:
        print("A2 DS fikstur GECEN %d/%d red=%s"
              % (len(DS_MODELLER) - len(red), len(DS_MODELLER), red))
    return not red


def eksen_a3(o, sessiz=False):
    A = o.A
    gecmeyen = [(mk, md) for mk, md in SINIR_GECER
                if A.uyum_ogesi_sebebi({"marka": mk, "model": md}) is not None]
    sizan = [(mk, md) for mk, md in SINIR_RED
             if A.uyum_ogesi_sebebi({"marka": mk, "model": md}) is None]
    motor_sizan = A.uyum_ogesi_sebebi({"marka": "Citroen", "motor": "DS"}) is None
    if not sessiz:
        print("A3 sinir: istisna GECER %d/%d (gecmeyen %s) · RED %d/%d (sizan %s) · "
              "motor=DS RED=%s" % (len(SINIR_GECER) - len(gecmeyen), len(SINIR_GECER),
                                   gecmeyen, len(SINIR_RED) - len(sizan), len(SINIR_RED),
                                   sizan, not motor_sizan))
    return not gecmeyen and not sizan and not motor_sizan


def eksen_a4(o, sessiz=False):
    M = o.M
    ev = M.MarkaEvreni(o.index_html)
    ek = M.cip_evreni_markalari(o.katalog, o.index_html)
    veri = M.gruplandir(o.katalog, ev, ek)
    cit = (veri.get("Citroen") or {}).get("gruplar", {}).get("ds")
    cit_yayin = bool(cit) and M.yayimlanir_mi(cit)
    peu_ds = "ds" in (veri.get("Peugeot") or {}).get("gruplar", {})
    j_bag = M.marka_jetonu_mu("DS", ev)
    j_cit = M.marka_jetonu_mu("DS", ev, "Citroen")
    j_peu = M.marka_jetonu_mu("DS", ev, "Peugeot")
    if not sessiz:
        print("A4 sayfa: /marka/citroen/ds/ yayimlanir=%s (%d urun) · Peugeot|DS kovasi=%s · "
              "marka_jetonu_mu DS baglamsiz=%s Citroen=%s Peugeot=%s"
              % (cit_yayin, len(cit["urunler"]) if cit else 0, peu_ds, j_bag, j_cit, j_peu))
    return cit_yayin and not peu_ds and j_bag and not j_cit and j_peu


def eksen_a5(o, sessiz=False):
    A = o.A
    ihlal = [x.get("id") for x in o.katalog if A.uyum_sebebi(x)]
    duz = {x["id"]: x for x in o.katalog if x.get("id") in DUZELTILEN}
    duzeltildi = (len(duz) == len(DUZELTILEN)
                  and all({"marka": "DS"} in (x.get("uyum") or []) for x in duz.values()))
    if not sessiz:
        print("A5 katalog %d kayit · uyum ihlali %d (ilk 3 %s) · %d kayit DS markasi=%s"
              % (len(o.katalog), len(ihlal), ihlal[:3], len(DUZELTILEN), duzeltildi))
    return not ihlal and duzeltildi


EKSENLER = [("A1", eksen_a1), ("A2", eksen_a2), ("A3", eksen_a3), ("A4", eksen_a4),
            ("A5", eksen_a5)]


def eksen_kontrol(A):
    fark = len(A.UYUM_MARKA_IZINLI) - len(A.UYUM_MARKA_MIMAR_EKI)
    iki_kume = KANONIK in A.UYUM_MARKA_IZINLI and KANONIK in A.UYUM_MARKA_MIMAR_EKI
    tablo = set(A.MARKA_ADLI_MODEL_IZINLI)
    print("KONTROL izinli=%d eki=%d FARK=%d (taban %d) · iki kumede=%s · istisna tablosu=%s"
          % (len(A.UYUM_MARKA_IZINLI), len(A.UYUM_MARKA_MIMAR_EKI), fark,
             IZINLI_EKSI_EKI_TABAN, iki_kume, sorted(tablo)))
    return fark == IZINLI_EKSI_EKI_TABAN and iki_kume and tablo == ISTISNA


def _mutant(ad, metinler, hedef, eski, yeni, beyan, katalog, index_html, adet=1):
    a_metin, m_metin = metinler
    kaynak = a_metin if hedef == "arama" else m_metin
    if kaynak.count(eski) != adet:
        print("%s UYGULANAMADI (desen %d kez, beklenen %d) -> KUSUR"
              % (ad, kaynak.count(eski), adet))
        return False
    yeni_metin = kaynak.replace(eski, yeni)
    if hedef == "arama":
        a_metin = yeni_metin
    else:
        m_metin = yeni_metin
    A = _arama_yukle(a_metin)
    o = Ortam(A, _mmb_yukle(A, m_metin), katalog, index_html)
    kirmizi = {k for k, f in EKSENLER if not f(o, sessiz=True)}
    esit = kirmizi == set(beyan)
    print("%s kirmizi=%s beyan=%s -> %s" % (ad, sorted(kirmizi), sorted(beyan),
                                            "ESIT" if esit else "ESIT DEGIL (KUSUR)"))
    return esit


def main():
    sha_bas = (_sha(ARAC), _sha(MMB))
    katalog = json.loads(_oku(URUNLER))
    index_html = _oku(INDEX)
    metinler = (_oku(ARAC), _oku(MMB))
    A = _arama_yukle(metinler[0])
    o = Ortam(A, _mmb_yukle(A, metinler[1]), katalog, index_html)

    sonuc = {ad: f(o) for ad, f in EKSENLER}
    sonuc["KONTROL"] = eksen_kontrol(A)
    print()
    sonuc["M1"] = _mutant("M1 (DS iki kumeden cikti)", metinler, "arama",
                          '    "DS",\n', "", {"A1", "A2", "A3", "A4", "A5"},
                          katalog, index_html, adet=2)
    sonuc["M2"] = _mutant("M2 (uyum istisnasi dustu)", metinler, "arama",
                          M2_ESKI, "", {"A3", "A5"}, katalog, index_html)
    sonuc["M3"] = _mutant("M3 (uretec istisnasi dustu)", metinler, "mmb",
                          M3_ESKI, "", {"A4"}, katalog, index_html)
    sonuc["KONTROL-MUTANT"] = _mutant("KONTROL-MUTANT (UYUM_YIL_EN_ERKEN -1)", metinler,
                                      "arama", "UYUM_YIL_EN_ERKEN = 1900",
                                      "UYUM_YIL_EN_ERKEN = 1899", set(), katalog, index_html)
    sha_son = (_sha(ARAC), _sha(MMB))
    sonuc["SHA"] = sha_bas == sha_son
    print("SHA arama.py+marka_model_build.py %s" % ("AYNI" if sonuc["SHA"]
                                                    else "DEGISTI (KUSUR)"))
    print()
    gecen = sum(1 for v in sonuc.values() if v)
    print("SONUC: %s — gecen %d · kalan %d · iddia %d"
          % ("YESIL" if gecen == len(sonuc) else "KIRMIZI", gecen, len(sonuc) - gecen,
             len(sonuc)))
    sys.exit(0 if gecen == len(sonuc) else 1)


if __name__ == "__main__":
    main()
