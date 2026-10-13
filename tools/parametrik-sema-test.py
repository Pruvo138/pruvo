#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""parametrik-sema-test.py — K441: `parametrik:true` kayit ⇒ `jenerator/urunler/<id>.json` ZORUNLU.

Olculen kural TEK KAYNAKTA: tools/parametrik_sema.py. Iki tuketici: denetim-kapisi.py KAPI 12
(bu dosya: birim + denetle()/_urun_ihlalleri() baglantisi) ve urun-kuyruk-birlestir.py
(tools/urun-kuyruk-test.py V19-V22 + M-SEMA).

Vakalar: V1 semali -> tamam · V2 semasiz -> gerekce (id + yol) · V3 parametrik DEGIL -> tamam ·
V4 guvensiz id (yol kacisi) -> fail-closed (sema_var HER SEYE evet dese bile) ·
V5 sema_var istisna -> fail-closed · V6 semasizlar() filtre+sira · V7 denetle() KAPI 12
ihlal uretir · V8 _urun_ihlalleri() ayni ihlali tasir (denetle ile ikiz-kural YOK) · V9 SEMA_DIZIN
== build.py::JEN_URUN_DIR · V10 GERCEK KATALOG artmama (semasiz parametrik kumesi GECMIS_BORC'un
alt kumesi).
Mutantlar (izole kopya, once TABAN): sema_var yutulur -> V2 · parametrik filtresi kalkar -> V3 ·
guvensiz id korumasi kalkar -> V4 · istisna 'tamam' sayilir -> V5.
"""
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True  # agaca __pycache__ birakma
MODUL_YOLU = os.path.join(KOK, "tools", "parametrik_sema.py")

# GECMIS BORC (13 Eki 2026, K441): sema'si main'de OLMAYAN tek parametrik kayit. Bu kume
# YALNIZ daralir — yeni bir semasiz parametrik kayit main'e girerse V10 KIRMIZI yanar.
# (Sema gelince id'nin burada kalmasi zararsiz; liste buyutulmez.)
GECMIS_BORC = frozenset({"olcuye-ozel-saksi-vazo"})


def yukle(yol, ad="parametrik_sema_test_modulu"):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def vakalar(mod):
    """(kimlik, hata|None) listesi — `mod` taban YA DA mutant kopya olabilir."""
    cikti = []

    def vaka(kimlik, govde):
        try:
            hata = govde()
        except Exception as e:                                       # noqa: BLE001
            hata = "istisna: %s: %s" % (type(e).__name__, e)
        cikti.append((kimlik, hata))

    def hep(_yol):
        return True

    def hic(_yol):
        return False

    def v1():
        if mod.semasiz_gerekce({"id": "olcuye-ozel-x", "parametrik": True}, hep) is not None:
            return "semali parametrik kayit ihlal verdi"

    def v2():
        g = mod.semasiz_gerekce({"id": "olcuye-ozel-x", "parametrik": True}, hic)
        if not g or "olcuye-ozel-x" not in g or "jenerator/urunler/olcuye-ozel-x.json" not in g:
            return "semasiz parametrik kayit gerekce vermedi/eksik: %r" % (g,)

    def v3():
        for u in ({"id": "duz-urun"}, {"id": "duz-urun", "parametrik": False},
                  {"id": "duz-urun", "parametrik": None}, "metin", None, 7):
            if mod.semasiz_gerekce(u, hic) is not None:
                return "parametrik OLMAYAN kayit ihlal verdi: %r" % (u,)

    def v4():
        # sema_var HER SEYE 'evet' dese bile guvensiz id sema yoluna CEVRILMEZ (yol kacisi).
        for uid in ("../etc/passwd", "a/b", "A-Buyuk", "", None, 5, "a..b", "-bas", "son-",
                    "bosluk var"):
            g = mod.semasiz_gerekce({"id": uid, "parametrik": True}, hep)
            if not g or "GUVENLE" not in g:
                return "guvensiz id %r fail-closed DEGIL: %r" % (uid, g)

    def v5():
        def patla(_yol):
            raise OSError("disk okunamadi")
        g = mod.semasiz_gerekce({"id": "olcuye-ozel-x", "parametrik": True}, patla)
        if not g or "OLCULEMEDI" not in g:
            return "sema_var istisnasi fail-closed DEGIL: %r" % (g,)

    def v6():
        liste = [{"id": "z-param", "parametrik": True}, {"id": "duz"},
                 {"id": "a-param", "parametrik": True}, {"id": "m-param", "parametrik": True}]
        var = {"jenerator/urunler/m-param.json"}
        sonuc = mod.semasizlar(liste, lambda y: y in var)
        if [i for i, _ in sonuc] != ["a-param", "z-param"]:
            return "semasizlar sira/icerik: %r" % ([i for i, _ in sonuc],)
        yalniz = mod.semasizlar(liste, lambda y: y in var, sadece_idler={"z-param"})
        if [i for i, _ in yalniz] != ["z-param"]:
            return "sadece_idler filtresi: %r" % ([i for i, _ in yalniz],)

    for kimlik, govde in (("V1-semali-tamam", v1), ("V2-semasiz-gerekce", v2),
                          ("V3-parametrik-degil-tamam", v3), ("V4-guvensiz-id-failclosed", v4),
                          ("V5-istisna-failclosed", v5), ("V6-semasizlar-filtre-sira", v6)):
        vaka(kimlik, govde)
    return cikti


def denetim_vakalari():
    """V7/V8: denetim-kapisi.py baglantisi (modulu dosya yolundan yukler)."""
    cikti = []
    dk = yukle(os.path.join(KOK, "tools", "denetim-kapisi.py"), "denetim_kapisi_ps_test")
    semasiz = {"id": "olcuye-ozel-test-semasiz", "parametrik": True, "baslik": "x",
               "kategori": "Jeneratör", "fiyat": "", "gorseller": ["https://m/x.jpg"]}
    semali = dict(semasiz, id="olcuye-ozel-cerceve")      # sema dosyasi GERCEK depoda var
    duz = {"id": "duz-urun", "baslik": "x", "gorseller": ["https://m/x.jpg"]}

    def ihlaller(u):
        r = dk.denetle([u], {u["id"]}, set(), {})
        return [i for i in r["ihlal"] if i["kapi"] == "parametrik-sema"]

    def v7():
        if len(ihlaller(semasiz)) != 1:
            return "denetle(): semasiz parametrik icin KAPI 12 ihlali != 1: %r" % ihlaller(semasiz)
        if ihlaller(semali):
            return "denetle(): semali kayit KAPI 12 ihlali verdi: %r" % ihlaller(semali)
        if ihlaller(duz):
            return "denetle(): parametrik OLMAYAN kayit KAPI 12 ihlali verdi"

    def v8():
        # --commit-farki 'onceden var' suzgeci _urun_ihlalleri() ile karsilastirir; ikiz-kural olmamali.
        kume = {k for k, _ in dk._urun_ihlalleri(semasiz) if k == "parametrik-sema"}
        if kume != {"parametrik-sema"}:
            return "_urun_ihlalleri(): KAPI 12 yok (ikiz-kural ayristi): %r" % kume
        if any(k == "parametrik-sema" for k, _ in dk._urun_ihlalleri(semali)):
            return "_urun_ihlalleri(): semali kayit ihlalli"
        denetle_g = ihlaller(semasiz)[0]["gerekce"]
        if ("parametrik-sema", denetle_g) not in dk._urun_ihlalleri(semasiz):
            return "denetle() ve _urun_ihlalleri() AYNI gerekceyi uretmiyor"

    for kimlik, govde in (("V7-denetle-KAPI12", v7), ("V8-urun-ihlalleri-ikiz-yok", v8)):
        try:
            hata = govde()
        except Exception as e:                                       # noqa: BLE001
            hata = "istisna: %s: %s" % (type(e).__name__, e)
        cikti.append((kimlik, hata))
    return cikti


def v9():
    mod = yukle(MODUL_YOLU)
    with open(os.path.join(KOK, "tools", "build.py"), encoding="utf-8") as f:
        m = re.search(r'^JEN_URUN_DIR\s*=\s*os\.path\.join\(ROOT,\s*"([^"]+)",\s*"([^"]+)"\)',
                      f.read(), re.M)
    if not m:
        return "build.py::JEN_URUN_DIR bulunamadi (tanim degisti, kapi bayatladi)"
    if "/".join(m.groups()) != mod.SEMA_DIZIN:
        return "SEMA_DIZIN %r != build.py::JEN_URUN_DIR %r" % (mod.SEMA_DIZIN, "/".join(m.groups()))


def v10():
    """GERCEK KATALOG non-growth: semasiz parametrik kayitlar GECMIS_BORC'un alt kumesi olmali."""
    mod = yukle(MODUL_YOLU)
    with open(os.path.join(KOK, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    sema = lambda yol: os.path.isfile(os.path.join(KOK, *yol.split("/")))  # noqa: E731
    bulunan = {i for i, _ in mod.semasizlar(urunler, sema)}
    yeni = sorted(bulunan - GECMIS_BORC, key=str)
    if yeni:
        return ("YENI semasiz parametrik kayit(lar) main'de: %s — once jenerator/urunler/<id>.json "
                "main'e, sonra kayit (K441)" % ", ".join(map(str, yeni)))
    print("      gercek katalog: semasiz parametrik=%d (gecmis borc=%d) — artis YOK"
          % (len(bulunan), len(GECMIS_BORC & bulunan)))


MUTANTLAR = (
    ("M1", "sema_var cevabi yutulur (her kayit 'sema var' sayilir)",
     ("    if var:\n        return None\n", "    if True:\n        return None\n"),
     "V2-semasiz-gerekce"),
    ("M2", "parametrik filtresi kalkar (her kayit sema ister)",
     ("    if not parametrik_mi(urun):\n        return None\n",
      "    if False:\n        return None\n"), "V3-parametrik-degil-tamam"),
    ("M3", "guvensiz id korumasi kalkar",
     ("    if yol is None:\n        return (\"parametrik kayit: id",
      "    if False:\n        return (\"parametrik kayit: id"), "V4-guvensiz-id-failclosed"),
    ("M4", "sema_var istisnasi 'tamam' sayilir (fail-open)",
     ("    except Exception as e:                                           # noqa: BLE001\n"
      "        return (\"parametrik kayit %s: sema varligi OLCULEMEDI (%s: %s) — fail-closed\"\n"
      "                % (uid, type(e).__name__, e))\n",
      "    except Exception as e:                                           # noqa: BLE001\n"
      "        return None\n"), "V5-istisna-failclosed"),
)


def main():
    hata_sayisi = 0
    taban = vakalar(yukle(MODUL_YOLU))
    for kimlik, hata in taban + denetim_vakalari():
        hata_sayisi += bool(hata)
        print("%s %s%s" % ("KIRMIZI" if hata else "YESIL", kimlik, " | SORUN: %s" % hata if hata else ""))
    for kimlik, fonk in (("V9-SEMA_DIZIN-build-ikiz", v9), ("V10-gercek-katalog-artmama", v10)):
        hata = fonk()
        hata_sayisi += bool(hata)
        print("%s %s%s" % ("KIRMIZI" if hata else "YESIL", kimlik, " | SORUN: %s" % hata if hata else ""))

    gecici = tempfile.mkdtemp(prefix="parametrik-sema-test-")
    try:
        with open(MODUL_YOLU, encoding="utf-8") as f:
            govde = f.read()
        for kimlik, aciklama, (eski, yeni), hedef in MUTANTLAR:
            if govde.count(eski) != 1:
                print("KIRMIZI %s MUTANT CAPASI TUTMADI (%d eslesme)" % (kimlik, govde.count(eski)))
                hata_sayisi += 1
                continue
            yol = os.path.join(gecici, kimlik + ".py")
            with open(yol, "w", encoding="utf-8") as f:
                f.write(govde.replace(eski, yeni))
            dusenler = [k for k, h in vakalar(yukle(yol, "mutant_" + kimlik)) if h]
            yakalandi = hedef in dusenler
            hata_sayisi += not yakalandi
            print("%s %s (%s) -> hedef %s dusenler=%s" % (
                "YAKALANDI" if yakalandi else "KACTI", kimlik, aciklama, hedef, dusenler))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    print("SONUC: %s vaka=%d mutant=%d hata=%d" % (
        "YESIL" if hata_sayisi == 0 else "KIRMIZI", len(taban) + 4, len(MUTANTLAR), hata_sayisi))
    return 1 if hata_sayisi else 0


if __name__ == "__main__":
    sys.exit(main())
