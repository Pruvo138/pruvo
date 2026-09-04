#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`cip-supurme.py` kabul bataryasi — fikstur kutusu/arsivi uzerinde.

🔴 CANLI KUTUYA DOKUNMAZ: modulun KUTU/ARSIV sabitleri fikstur yollarina cevrilir.
🔴 NEGATIF KOLLAR SART: "listeye girdi" kadar "GIRMEDI" de olculur — yalnizca pozitif
   olcen batarya, herkesi terk adayi ilan eden bir supurgeyi YESIL gosterirdi.
"""
import importlib.util
import os
import shutil
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Mutasyon turu icin arac yolu DISARIDAN verilebilir; verilmezse CANLI arac olculur.
ARAC = os.environ.get("CIP_SUPURME_ARAC") or os.path.join(KOK, "tools", "cip-supurme.py")

IDDIA = 0
GECTI = 0
KIRMIZI = []


def iddia(ad, kosul, ayrinti=""):
    global IDDIA, GECTI
    IDDIA += 1
    if kosul:
        GECTI += 1
        print("  [OK]   %s %s" % (ad, ayrinti))
    else:
        KIRMIZI.append(ad)
        print("  [KIRMIZI] %s %s" % (ad, ayrinti))


def yukle():
    spec = importlib.util.spec_from_file_location("cip_supurme", ARAC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ACIK = """## 2026-08-30 — 🚧 MaCiT (çip: `olu-cip-aaa111`) **BAŞLIYORUM: eski is.**
govde
— MaCiT (çip)

---

"""

ACIK_YENI = """## 2026-09-04 — 🚧 KraL (çip: `taze-cip-bbb222`) **BAŞLIYORUM: bugunku is.**
govde
— KraL (çip)

---

"""

KAPALI_KUTUDA = """## 2026-09-01 — 🚧 ArTisT (çip: `kutuda-kapali-ccc333`) **BAŞLIYORUM: is.**
— ArTisT (çip)

---

## 2026-09-01 — ✅ ArTisT (çip: `kutuda-kapali-ccc333`) **SAYILI KAPANIŞ — bitti.**
sayilar
— ArTisT (çip)

---

"""

# K360-A: acilis IKI ada birden cozulur (backtick `ad-ekseni-ddd444` + gevsek
# `KraL-AdEkseni-2Eyl`); kapanis YALNIZ backtick adini tasir.
# 🔴 FIKSTUR AYIRT EDICI OLMALI: sirali kumede adlar[0] = "KraL-AdEkseni-2Eyl"
# (buyuk 'K' < kucuk 'a'), yani kapanista GECMEYEN ad basta. Boylece tek-ad kiyasi
# yapan bir mutant bu blogu ACIK sanir ve V1f DUSER. Ilk fikstur bunu saglamiyordu:
# acilis tek ada cozuluyordu, mutant hedefe ULASAMIYORDU (mutasyon turu yakaladi).
AD_EKSENI_ACIK = """## 2026-09-02 — 🚧 KraL-AdEkseni-2Eyl (çip `ad-ekseni-ddd444`) **BAŞLIYORUM: is.**
— KraL-AdEkseni-2Eyl

---

"""

ARSIVDE_KAPALI = """## 2026-09-01 — ✅ HocA (çip: `arsivde-kapali-eee555`) **SAYILI KAPANIŞ — bitti.**
sayilar
— HocA (çip)

---

## 2026-09-02 — ✅ (çip `ad-ekseni-ddd444`) **SAYILI KAPANIŞ — bitti.**
sayilar
— ad-ekseni-ddd444

---

"""

ARSIVDE_ACIK = """## 2026-09-01 — 🚧 HocA (çip: `arsivde-kapali-eee555`) **BAŞLIYORUM: is.**
— HocA (çip)

---

"""


def kur(gecici, kutu_metin, arsiv_metin):
    k = os.path.join(gecici, "kutu.md")
    a = os.path.join(gecici, "arsiv.md")
    with open(k, "w", encoding="utf-8") as f:
        f.write(kutu_metin)
    with open(a, "w", encoding="utf-8") as f:
        f.write(arsiv_metin)
    return k, a


def adlari(veri):
    kume = set()
    for s in veri["acik"]:
        kume.update(s["adlar"])
    return kume


def main():
    gecici = tempfile.mkdtemp(prefix="cip-supurme-test-")
    try:
        M = yukle()

        print("V1 — kapanissiz acik cip LISTELENIR; kapanisi olan LISTELENMEZ")
        kutu = ACIK + ACIK_YENI + KAPALI_KUTUDA + AD_EKSENI_ACIK + ARSIVDE_ACIK
        M.KUTU, M.ARSIV = kur(gecici, kutu, ARSIVDE_KAPALI)
        veri, hata = M.tara(0)
        iddia("V1a tarama hatasiz", hata is None, "hata=%s" % hata)
        ad = adlari(veri)
        iddia("V1b eski acik cip LISTEDE", "olu-cip-aaa111" in ad)
        iddia("V1c taze acik cip LISTEDE", "taze-cip-bbb222" in ad)
        iddia("V1d KUTUDA kapanisi olan LISTEDE DEGIL", "kutuda-kapali-ccc333" not in ad)
        iddia("V1e ARSIVDE kapanisi olan LISTEDE DEGIL (duzlem)",
              "arsivde-kapali-eee555" not in ad)
        iddia("V1f AD EKSENI: kapanis BASKA adla, yine LISTEDE DEGIL (K360-A)",
              "ad-ekseni-ddd444" not in ad and "KraL-AdEkseni-2Eyl" not in ad)
        iddia("V1g toplam acik = 2", len(veri["acik"]) == 2, "olculen=%d" % len(veri["acik"]))

        print()
        print("V2 — EV atfi imzadan cozulur, cozulemezse BILINMIYOR (ucuncu hal GORUNUR)")
        evler = dict((s["adlar"][0], s["ev"]) for s in veri["acik"])
        iddia("V2a MaCiT atfi", evler.get("olu-cip-aaa111") == "MaCiT", str(evler))
        iddia("V2b KraL atfi", evler.get("taze-cip-bbb222") == "KraL", str(evler))
        M.KUTU, M.ARSIV = kur(gecici,
                              "## 2026-09-01 — 🚧 (çip: `sahipsiz-fff666`) **BAŞLIYORUM: is.**\nx\n\n---\n\n",
                              "")
        v2, _h = M.tara(0)
        iddia("V2c sahipsiz blok BILINMIYOR (sessizce bir eve YAZILMAZ)",
              v2["acik"] and v2["acik"][0]["ev"] == "BILINMIYOR",
              str([s["ev"] for s in v2["acik"]]))

        print()
        print("V3 — YAS ESIGI")
        M.KUTU, M.ARSIV = kur(gecici, kutu, ARSIVDE_KAPALI)
        v3, _h = M.tara(2)
        ad3 = adlari(v3)
        iddia("V3a esik 2 gun: eski cip KALIR", "olu-cip-aaa111" in ad3)
        iddia("V3b esik 2 gun: bugunku cip ELENIR", "taze-cip-bbb222" not in ad3)

        print()
        print("V4 — ARSIV OKUNAMIYOR: bilgi EKSIK oldugu RAPORLANIR (sessizce yesil DEGIL)")
        M.KUTU, M.ARSIV = kur(gecici, ARSIVDE_ACIK, "")
        M.ARSIV = os.path.join(gecici, "YOK-BOYLE-DOSYA.md")
        v4, _h = M.tara(0)
        iddia("V4a arsiv hatasi RAPORLANIR", bool(v4["arsiv_hata"]), str(v4["arsiv_hata"])[:60])
        iddia("V4b arsiv okunamayinca blok LISTEDE KALIR (fail-closed, susulmaz)",
              "arsivde-kapali-eee555" in adlari(v4))

        print()
        print("V5 — --terk NEGATIF KOLLARI")
        M.KUTU, M.ARSIV = kur(gecici, kutu, ARSIVDE_KAPALI)
        with open(M.KUTU, "rb") as f:
            once_bayt = f.read()
        rc = M.terk_yaz("yok-boyle-bir-cip", False)
        with open(M.KUTU, "rb") as f:
            sonra_bayt = f.read()
        iddia("V5a olmayan ad -> rc=2", rc == 2, "rc=%s" % rc)
        iddia("V5b olmayan ad -> kutu BAYT BAYT AYNI", once_bayt == sonra_bayt)

        rc = M.terk_yaz("kutuda-kapali-ccc333", False)
        with open(M.KUTU, "rb") as f:
            sonra2 = f.read()
        iddia("V5c KAPANISI OLAN cipe tutanak YAZILMAZ -> rc=2", rc == 2, "rc=%s" % rc)
        iddia("V5d kapanisi olana -> kutu BAYT BAYT AYNI", once_bayt == sonra2)

        rc = M.terk_yaz("olu-cip-aaa111", True)
        with open(M.KUTU, "rb") as f:
            sonra3 = f.read()
        iddia("V5e --kuru -> rc=0", rc == 0, "rc=%s" % rc)
        iddia("V5f --kuru -> kutu BAYT BAYT AYNI (hicbir sey yazilmaz)",
              once_bayt == sonra3)

        print()
        print("V6 — --terk GERCEK YAZIM: kayipsiz + BASARI kapanisi DEGIL")
        rc = M.terk_yaz("olu-cip-aaa111", False)
        with open(M.KUTU, encoding="utf-8") as f:
            yeni = f.read()
        iddia("V6a rc=0", rc == 0, "rc=%s" % rc)
        iddia("V6b eski icerik BIREBIR duruyor (kayipsiz)",
              once_bayt.decode("utf-8") in yeni)
        iddia("V6c tutanak BASARI kapanisi DEGIL",
              "TERK TUTANAĞI" in yeni and "SONUÇ ÖLÇÜLMEDİ" in yeni)
        iddia("V6d 'neyi olcmek kapatir' YAZILI", "Neyi ölçmek KAPATIR" in yeni)
        iddia("V6e is kaybi uyarisi + arsiv-kapisi sarti YAZILI",
              "arsiv-kapisi.py" in yeni and "rc=0" in yeni)
        iddia("V6f sahibi ev tutanakta ADIYLA", "MaCiT" in yeni.split("TERK TUTANAĞI")[1][:600])

        print()
        print("V7 — ESLESME KURALI IKIZLENMEDI (tek kaynak kutu-arsivle.py)")
        with open(ARAC, encoding="utf-8") as f:
            kaynak = f.read()
        iddia("V7a kapanan_cipler IMPORT edilen moduleden cagriliyor",
              "K.kapanan_cipler(" in kaynak)
        iddia("V7b ikinci bir 'SAYILI KAPANIS' literali TANIMLANMAMIS",
              kaynak.count('"SAYILI KAPANIS"') == 0)

    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    print()
    print("=" * 70)
    print("IDDIA=%d GECTI=%d KIRMIZI=%d" % (IDDIA, GECTI, len(KIRMIZI)))
    if KIRMIZI:
        for k in KIRMIZI:
            print("  DUSEN: %s" % k)
        return 1
    print("SONUC: GECTI ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
