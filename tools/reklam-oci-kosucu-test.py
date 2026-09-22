#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL — `tools/reklam-oci-kosucu.py` ZARAR ESIGI kararini GERCEKTEN kosar.

══════════════════════════════════════════════════════════════════════════════
🔴 NEDEN BU TEST YAML METNI OKUMAZ
══════════════════════════════════════════════════════════════════════════════
Zarar esigi `.github/workflows/reklam-oci.yml` kabugunda yasasaydi, bu dosya ancak
YAML metninde bir dizge ARAYABILIRDI. Dizge arayan bir kabul, kararin KENDISINI hic
kosmaz: govde tersine cevrilse bile dizge yerinde durdugu icin YESIL kalirdi — alet
KOR olur ([[kabul-teslim-edilmeyen-iskeleyle-saglanirsa-alet-kor-kalir]]). Bu yuzden
karar `tools/reklam-oci-kosucu.py::karar` icine TASINDI ve burada CAGRILIYOR.

BATARYA (dort zorunlu vaka + uc ek eksen):
  1. bekleyen=0, kimlik YOK   -> rc 0 · EYLEM=BEKLE · birebir `HAL=KIMLIK-BEKLIYOR BEKLEYEN=0`
  2. bekleyen=3, kimlik YOK   -> rc 1 · EYLEM=ZARAR · yukleme CAGRILMAZ
  3. bekleyen=3, kimlik VAR   -> yukleme DENENIR (kol tam 1 kez cagrilir)
  4. durum OLCULEMEDI (None)  -> rc 3 · EYLEM=OLCULEMEDI · yukleme CAGRILMAZ
  5. durum kolu PATLAR        -> rc 3 (istisna yesile dusmez)
  6. kimlik VAR + yukleme rc=1-> rc 1 (yukleme kirmizisi YUTULMAZ)
  7. bayrak AYRISMASI         -> rc 3 (ikiz tanim sessiz kalamaz)

MUTANT (izole kopyada; CANLI govde DEGISMEZ — [[mutant-canli-govdede-yasamaz]]):
  her mutant EN AZ BIR vakayi KIRMIZI yakmalidir. `SURVIVOR=0` basilmazsa kabul DUSER.
  🔴 Hangi vakanin oldurdugu CIVILENMEZ — beklenen-kirmizi kumesi taban degisince
  ikinci kat bayatlar ([[mutant-beklenen-kirmizi-kumesi-taban-degisince-ikinci-kat-bayatlar]]).

Kullanim:
  python3 tools/reklam-oci-kosucu-test.py              # batarya + mutant (CI kolu)
  python3 tools/reklam-oci-kosucu-test.py --mutant     # yalniz mutant kolu
"""

import argparse
import importlib.util
import os
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOSUCU = os.path.join(TOOLS, "reklam-oci-kosucu.py")
AKIS = os.path.join(os.path.dirname(TOOLS), ".github", "workflows", "reklam-oci.yml")

DORT_ALAN = ["GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CLIENT_ID",
             "GOOGLE_ADS_CLIENT_SECRET", "GOOGLE_ADS_REFRESH_TOKEN"]


def modul_yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ══════════════════════════════════════════════════════════════════════════════
# KOL SAHTELERI — ag YOK, D1 YOK, secret YOK.
# ══════════════════════════════════════════════════════════════════════════════
def durum_sabit(deger):
    def _kol():
        return deger
    return _kol


def durum_patlar():
    def _kol():
        raise RuntimeError("D1 acilamadi (kasitli — OLCULEMEDI ekseni)")
    return _kol


def kimlik_sabit(tam):
    def _kol():
        return (True, []) if tam else (False, list(DORT_ALAN))
    return _kol


def yukle_sayaci(rc=0, metin="YUKLEME: gonderilen=3 basarili=3 basarisiz=0 istek=1"):
    """Cagrilma SAYISINI tutar — 'denendi mi' sorusu rc ile ayirt EDILEMEZ."""
    kayit = {"n": 0}

    def _kol():
        kayit["n"] += 1
        return rc, metin
    return _kol, kayit


# ══════════════════════════════════════════════════════════════════════════════
# BATARYA — her vaka (ad, gecti_mi, mesaj) doner. M = olculen modul (gercek|mutant)
# ══════════════════════════════════════════════════════════════════════════════
def batarya(M):
    sonuc = []

    def ekle(ad, kosul, mesaj):
        sonuc.append((ad, bool(kosul), mesaj))

    # ── 1. bekleyen=0, kimlik YOK -> YESIL + birebir satir ──────────────────
    yk, say = yukle_sayaci()
    rc, satir, eylem = M.kos(durum_sabit(0), kimlik_sabit(False), yk)
    metin = "\n".join(satir)
    ekle("1a rc", rc == 0, "bekleyen=0+kimlik yok -> rc=%d (beklenen 0)" % rc)
    ekle("1b eylem", eylem == M.EYLEM_BEKLE,
         "eylem=%s (beklenen BEKLE)" % eylem)
    ekle("1c birebir satir", "HAL=KIMLIK-BEKLIYOR BEKLEYEN=0" in metin,
         "ozet `HAL=KIMLIK-BEKLIYOR BEKLEYEN=0` satirini BASMIYOR")
    ekle("1d yukleme denenmedi", say["n"] == 0,
         "kimlik yokken yukleme %d kez cagrildi (beklenen 0)" % say["n"])

    # ── 2. bekleyen=3, kimlik YOK -> ZARAR ESIGI, KIRMIZI ───────────────────
    yk, say = yukle_sayaci()
    rc, satir, eylem = M.kos(durum_sabit(3), kimlik_sabit(False), yk)
    metin = "\n".join(satir)
    ekle("2a rc", rc == 1, "bekleyen=3+kimlik yok -> rc=%d (beklenen 1)" % rc)
    ekle("2b eylem", eylem == M.EYLEM_ZARAR, "eylem=%s (beklenen ZARAR)" % eylem)
    ekle("2c sayi basildi", "BEKLEYEN=3" in metin,
         "zarar metni BEKLEYEN sayisini BASMIYOR")
    ekle("2d yukleme denenmedi", say["n"] == 0,
         "kimlik yokken yukleme %d kez cagrildi (beklenen 0)" % say["n"])

    # ── 3. bekleyen=3, kimlik VAR -> yukleme DENENIR ────────────────────────
    yk, say = yukle_sayaci(rc=0)
    rc, satir, eylem = M.kos(durum_sabit(3), kimlik_sabit(True), yk)
    ekle("3a yukleme denendi", say["n"] == 1,
         "kimlik varken yukleme %d kez cagrildi (beklenen 1)" % say["n"])
    ekle("3b eylem", eylem == M.EYLEM_YUKLE, "eylem=%s (beklenen YUKLE)" % eylem)
    ekle("3c rc", rc == 0, "basarili yuklemede rc=%d (beklenen 0)" % rc)

    # ── 4. durum OLCULEMEDI (None) -> rc 3, YESIL DEGIL ─────────────────────
    yk, say = yukle_sayaci()
    rc, satir, eylem = M.kos(durum_sabit(None), kimlik_sabit(False), yk)
    ekle("4a rc", rc == 3, "durum None -> rc=%d (beklenen 3)" % rc)
    ekle("4b eylem", eylem == M.EYLEM_OLCULEMEDI,
         "eylem=%s (beklenen OLCULEMEDI)" % eylem)
    ekle("4c yukleme denenmedi", say["n"] == 0,
         "olculemedi kolunda yukleme %d kez cagrildi (beklenen 0)" % say["n"])

    # ── 5. durum kolu PATLAR -> istisna YESILE dusmez ───────────────────────
    yk, say = yukle_sayaci()
    rc, satir, eylem = M.kos(durum_patlar(), kimlik_sabit(False), yk)
    ekle("5a rc", rc == 3, "durum kolu patladi -> rc=%d (beklenen 3)" % rc)

    # ── 6. kimlik VAR ama yukleme KIRMIZI -> rc YUTULMAZ ────────────────────
    yk, say = yukle_sayaci(rc=1, metin="YUKLEME: basarisiz=2")
    rc, satir, eylem = M.kos(durum_sabit(2), kimlik_sabit(True), yk)
    ekle("6a rc", rc == 1, "yukleme rc=1 iken kosucu rc=%d (beklenen 1)" % rc)

    # ── 7. BAYRAK AYRISMASI -> ikiz tanim sessiz kalamaz ────────────────────
    yk, say = yukle_sayaci()
    rc, satir, eylem = M.kos(durum_sabit(0), kimlik_sabit(False), yk, bayrak="VAR")
    ekle("7a rc", rc == 3, "bayrak VAR / olcum YOK -> rc=%d (beklenen 3)" % rc)
    ekle("7b yukleme denenmedi", say["n"] == 0,
         "ayrisma kolunda yukleme %d kez cagrildi (beklenen 0)" % say["n"])
    # ayni yonde: bayrak dogruysa karar DEGISMEZ
    yk, say = yukle_sayaci()
    rc, satir, eylem = M.kos(durum_sabit(0), kimlik_sabit(False), yk, bayrak="YOK")
    ekle("7c dogru bayrak karari bozmaz", rc == 0 and eylem == M.EYLEM_BEKLE,
         "bayrak YOK iken rc=%d eylem=%s (beklenen 0/BEKLE)" % (rc, eylem))

    return sonuc


# ══════════════════════════════════════════════════════════════════════════════
# MUTANTLAR — izole kopyada. Her biri EN AZ BIR vakayi oldurmeli.
# ══════════════════════════════════════════════════════════════════════════════
MUTANTLAR = [
    ("M1 zarar esigi gevsetildi (> -> >=)",
     "    if bekleyen > 0:",
     "    if bekleyen >= 0:"),
    ("M2 zarar kolu yesile cevrildi",
     "        return EYLEM_ZARAR, RC_KIRMIZI",
     "        return EYLEM_BEKLE, RC_YESIL"),
    ("M3 zarar esigi komple KALDIRILDI",
     "    if bekleyen > 0:\n        # 🔴 ZARAR ESIGI",
     "    if False:\n        # 🔴 ZARAR ESIGI"),
    ("M4 kimlik kolu ters cevrildi",
     "    if kimlik_tam:\n        return EYLEM_YUKLE, RC_YESIL",
     "    if not kimlik_tam:\n        return EYLEM_YUKLE, RC_YESIL"),
    ("M5 OLCULEMEDI yesile dusuruldu",
     "    if bekleyen is None:\n        return EYLEM_OLCULEMEDI, RC_OLCULEMEDI",
     "    if bekleyen is None:\n        return EYLEM_BEKLE, RC_YESIL"),
    ("M6 bayrak capraz kolu susturuldu",
     "    if b != beklenen:",
     "    if False and b != beklenen:"),
    ("M7 yukleme rc'si yutuldu",
     "        rc, yukleme_metni = yukle_kolu()",
     "        _rc_atildi, yukleme_metni = yukle_kolu()"),
]


def mutant_kolu(govde, dizin):
    """Mutantlari IZOLE dizinde kos. CANLI dosyaya HICBIR yazma YOK."""
    olen, sagkalan = 0, []
    for i, (ad, eski, yeni) in enumerate(MUTANTLAR):
        if eski not in govde:
            sagkalan.append("%s — CAPA TUTMADI (kaynak degisti, mutant hedefini "
                            "bulamadi)" % ad)
            continue
        yol = os.path.join(dizin, "mutant_%02d.py" % i)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(govde.replace(eski, yeni, 1))
        try:
            M = modul_yukle(yol, "reklam_oci_kosucu_mutant_%02d" % i)
        except Exception as e:                    # noqa: BLE001
            # Cokme de OLUM sayilir: bozulmus govde kabul bataryasini GECEMEZ.
            print("  ☠️  %-44s (mutant yuklenemedi: %s)" % (ad, e))
            olen += 1
            continue
        try:
            dusen = [v for v in batarya(M) if not v[1]]
        except Exception as e:                    # noqa: BLE001
            print("  ☠️  %-44s (batarya istisna atti: %s)" % (ad, e))
            olen += 1
            continue
        if dusen:
            print("  ☠️  %-44s (olduren vaka: %s)" % (ad, dusen[0][0]))
            olen += 1
        else:
            sagkalan.append("%s — HICBIR VAKA KIRMIZI YANMADI" % ad)
    return olen, sagkalan


# ══════════════════════════════════════════════════════════════════════════════
def akis_kablolamasi():
    """Is akisi FIILEN bu aracı cagiriyor mu. Kablolanmamis karar OLU karardir."""
    if not os.path.exists(AKIS):
        return False, "is akisi YOK: %s" % AKIS
    m = open(AKIS, encoding="utf-8").read()
    eksik = [j for j in ("tools/reklam-oci-yukleyici.py --kuyrukla",
                         "tools/reklam-oci-kosucu.py",
                         "tools/reklam-oci-kosucu-test.py",
                         "schedule:", "workflow_dispatch:") if j not in m]
    if eksik:
        return False, "is akisinda eksik: %s" % ", ".join(eksik)
    return True, "is akisi uc adimi da cagiriyor (kuyrukla + kosucu + kabul)"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mutant", action="store_true", help="yalniz mutant kolunu kos")
    a = ap.parse_args(argv)

    govde = open(KOSUCU, encoding="utf-8").read()
    rc = 0

    if not a.mutant:
        print("REKLAM OCI KOSUCU — KABUL BATARYASI")
        M = modul_yukle(KOSUCU, "reklam_oci_kosucu_gercek")
        vakalar = batarya(M)
        dusen = [v for v in vakalar if not v[1]]
        for ad, gecti, mesaj in vakalar:
            if not gecti:
                print("  ❌ %-28s %s" % (ad, mesaj))
        print("  VAKA=%d GECEN=%d DUSEN=%d"
              % (len(vakalar), len(vakalar) - len(dusen), len(dusen)))
        if dusen:
            rc = 1

        tamam, mesaj = akis_kablolamasi()
        print("  KABLOLAMA: %s — %s" % ("✅" if tamam else "❌", mesaj))
        if not tamam:
            rc = 1

    print("MUTANT KOLU (izole kopya — canli govde DEGISMEZ)")
    with tempfile.TemporaryDirectory(prefix="oci-kosucu-mutant-") as d:
        olen, sagkalan = mutant_kolu(govde, d)
    for s in sagkalan:
        print("  🔴 SAGKALAN: %s" % s)
    print("  MUTANT=%d OLEN=%d SURVIVOR=%d" % (len(MUTANTLAR), olen, len(sagkalan)))
    if sagkalan:
        rc = 1

    print("-" * 70)
    print("SONUC: %s" % ("YESIL ✅" if rc == 0 else "KIRMIZI 🔴"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
