#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K357 — `tools/sabah-teslim/kur.py` TAM KOPYA KOLU FAIL-CLOSED bataryasi.

Yuzey: `tam_kopya_kolu()` + `kur()`'un ilk bacagi. HER vaka tempfile icinde
SAHTE kaynak/hedef dizininde kosar; gercek ev yolu YOK, silme komutu YOK
(TemporaryDirectory kendi kendini temizler).

  V1 hedef AYRISIK + bayraksiz -> hedef bayt-ayni ∧ rc=4 ∧ yedek YOK ∧
     fark ADIYLA (sha + yalniz-hedef def adi) ∧ kur() rc=4
  V2 hedef AYNI               -> ZATEN ∧ rc=0 ∧ yazim YOK
  V3 AYRISIK + --tam-kopya-ez -> hedef == kaynak ∧ yedek dogar (eski bayt) ∧ rc=0
  V4 HEPSI-YA-HIC             -> biri AYRISIK, digeri hedefte YOK -> ikisi de yazilmaz
  V5 --kuru + AYRISIK         -> yazim YOK ∧ rc=4
  V6 hedef YOK (ilk kurulum)  -> ikisi de yazilir ∧ rc=0 (sabah-kabul A7 fiksturu buna dayanir)
  M1 MUTANT: `engel = var and not ez` -> `engel = False` (eski `kuru or ayni` kolu)
     -> V1 KIRMIZI olmali; kontrol: V2 mutantta da YESIL (hedef-kol atfi)

Kosum: python3 tools/sabah-kur-tam-kopya-test.py   (rc=0 = hepsi beklenen)
"""

import importlib.util
import io
import os
import sys
import tempfile
from contextlib import redirect_stdout

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KUR = os.path.join(KOK, "tools", "sabah-teslim", "kur.py")

MUT_CAPA = "        engel = var and not ez\n"
MUT_YAMA = "        engel = False  # MUTANT: eski kosulsuz kol\n"

KAYNAK_SABAH = "def ana():\n    return 1\n"
KAYNAK_KABUL = "def a7_kurucu_idempotens():\n    return 0\n"
CANLI_KABUL = ("def a7_kurucu_idempotens():\n    return 0\n\n"
               "def a9_tavan_freni():\n    return 0\n")


def modul_yukle(yol, ad):
    s = importlib.util.spec_from_file_location(ad, yol)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def yaz_dosya(yol, metin):
    with open(yol, "w", encoding="utf-8") as f:
        f.write(metin)


def oku(yol):
    with open(yol, "rb") as f:
        return f.read()


def duzen(td, hedef_kabul=None, hedef_sabah=None):
    kd = os.path.join(td, "kaynak")
    hd = os.path.join(td, "cron")
    os.makedirs(kd)
    os.makedirs(hd)
    yaz_dosya(os.path.join(kd, "kral-sabah.py"), KAYNAK_SABAH)
    yaz_dosya(os.path.join(kd, "sabah-kabul.py"), KAYNAK_KABUL)
    if hedef_sabah is not None:
        yaz_dosya(os.path.join(hd, "kral-sabah.py"), hedef_sabah)
    if hedef_kabul is not None:
        yaz_dosya(os.path.join(hd, "sabah-kabul.py"), hedef_kabul)
    return kd, hd


def kos_kol(m, kd, hd, **kw):
    satirlar = []
    s = m.tam_kopya_kolu(kd, hd, yaz=satirlar.append, yedek_soneki=".yedek-test", **kw)
    return s, "\n".join(satirlar)


def yedekler(hd):
    return sorted(a for a in os.listdir(hd) if ".yedek-" in a)


def v1(m):
    with tempfile.TemporaryDirectory(prefix="k357-v1-") as td:
        kd, hd = duzen(td, hedef_kabul=CANLI_KABUL, hedef_sabah=KAYNAK_SABAH)
        once = oku(os.path.join(hd, "sabah-kabul.py"))
        s, cikti = kos_kol(m, kd, hd)
        sonra = oku(os.path.join(hd, "sabah-kabul.py"))
        # kur() bacagi: ayni duzenle, gercek giris noktasi uzerinden rc
        m.WT, m.CRON = kd, hd
        m.CIKTI_DIZINI = os.path.join(td, "log")
        m.HAM = os.path.join(m.CIKTI_DIZINI, "kurulum.log")
        # Mutantta kol yazip YAMA bacagina iner ve fiksturde yama hedefi YOK ->
        # cokus. Cokus sessiz yesil DEGIL: rc ADIYLA `COKTU:<tip>` olur (≠4).
        try:
            with redirect_stdout(io.StringIO()):
                rc_kur = m.kur(kuru=False)
        except Exception as e:
            rc_kur = "COKTU:%s" % type(e).__name__
        sonra2 = oku(os.path.join(hd, "sabah-kabul.py"))
        gecti = (s["rc"] == 4 and once == sonra == sonra2 and not yedekler(hd)
                 and s["ayrisik"] == ["sabah-kabul.py"] and rc_kur == 4
                 and "KOPYA_AYRISIK sabah-kabul.py kaynak_sha=" in cikti
                 and "hedefte_olup_kaynakta_olmayan_def=1 a9_tavan_freni" in cikti)
        return gecti, "rc=%s kur_rc=%s bayt_ayni=%d yedek=%d" % (
            s["rc"], rc_kur, int(once == sonra == sonra2), len(yedekler(hd)))


def v2(m):
    with tempfile.TemporaryDirectory(prefix="k357-v2-") as td:
        kd, hd = duzen(td, hedef_kabul=KAYNAK_KABUL, hedef_sabah=KAYNAK_SABAH)
        mt = os.stat(os.path.join(hd, "sabah-kabul.py")).st_mtime_ns
        s, cikti = kos_kol(m, kd, hd)
        gecti = (s["rc"] == 0 and s["zaten"] == ["kral-sabah.py", "sabah-kabul.py"]
                 and not s["yazilan"] and not yedekler(hd) and "ZATEN" in cikti
                 and os.stat(os.path.join(hd, "sabah-kabul.py")).st_mtime_ns == mt)
        return gecti, "rc=%s zaten=%d yazilan=%d" % (
            s["rc"], len(s["zaten"]), len(s["yazilan"]))


def v3(m):
    with tempfile.TemporaryDirectory(prefix="k357-v3-") as td:
        kd, hd = duzen(td, hedef_kabul=CANLI_KABUL, hedef_sabah=KAYNAK_SABAH)
        s, _ = kos_kol(m, kd, hd, ez=True)
        h = os.path.join(hd, "sabah-kabul.py")
        yd = h + ".yedek-test"
        gecti = (s["rc"] == 0 and s["yazilan"] == ["sabah-kabul.py"]
                 and oku(h) == KAYNAK_KABUL.encode("utf-8")
                 and os.path.isfile(yd) and oku(yd) == CANLI_KABUL.encode("utf-8"))
        return gecti, "rc=%s yazilan=%s yedek=%d" % (
            s["rc"], ",".join(s["yazilan"]), int(os.path.isfile(yd)))


def v4(m):
    with tempfile.TemporaryDirectory(prefix="k357-v4-") as td:
        kd, hd = duzen(td, hedef_kabul=CANLI_KABUL, hedef_sabah=None)
        s, _ = kos_kol(m, kd, hd)
        gecti = (s["rc"] == 4 and not s["yazilan"]
                 and not os.path.exists(os.path.join(hd, "kral-sabah.py")))
        return gecti, "rc=%s kral-sabah_yazildi=%d" % (
            s["rc"], int(os.path.exists(os.path.join(hd, "kral-sabah.py"))))


def v5(m):
    with tempfile.TemporaryDirectory(prefix="k357-v5-") as td:
        kd, hd = duzen(td, hedef_kabul=CANLI_KABUL, hedef_sabah=None)
        once = oku(os.path.join(hd, "sabah-kabul.py"))
        s, _ = kos_kol(m, kd, hd, kuru=True)
        gecti = (s["rc"] == 4 and not s["yazilan"]
                 and oku(os.path.join(hd, "sabah-kabul.py")) == once
                 and not os.path.exists(os.path.join(hd, "kral-sabah.py")))
        return gecti, "rc=%s yazilan=%d" % (s["rc"], len(s["yazilan"]))


def v6(m):
    # `sabah-kabul.py::a7_kurucu_idempotens` fiksturu tam-kopya hedefi OLMAYAN bir
    # sahte cron kurar; ilk kurulum yazmaya DEVAM etmeli (fail-closed onu kirmamali).
    with tempfile.TemporaryDirectory(prefix="k357-v6-") as td:
        kd, hd = duzen(td)
        s, _ = kos_kol(m, kd, hd)
        gecti = (s["rc"] == 0 and s["yazilan"] == ["kral-sabah.py", "sabah-kabul.py"]
                 and not yedekler(hd)
                 and oku(os.path.join(hd, "sabah-kabul.py")) == KAYNAK_KABUL.encode("utf-8"))
        return gecti, "rc=%s yazilan=%d yedek=%d" % (
            s["rc"], len(s["yazilan"]), len(yedekler(hd)))


def main():
    sonuc = []

    def kayit(ad, gecti, ayrinti):
        sonuc.append((ad, gecti))
        print("%s %s — %s" % ("✅" if gecti else "❌", ad, ayrinti))

    if not os.path.isfile(KUR):
        print("❌ kur.py YOK: %s" % KUR)
        return 1
    m = modul_yukle(KUR, "kur_k357")
    for ad, fn in (("V1 AYRISIK+bayraksiz -> yazmaz, rc=4", v1),
                   ("V2 AYNI -> ZATEN, rc=0", v2),
                   ("V3 --tam-kopya-ez -> yazar + yedek", v3),
                   ("V4 hepsi-ya-hic", v4),
                   ("V5 --kuru + AYRISIK -> yazmaz, rc=4", v5),
                   ("V6 hedef YOK (ilk kurulum / A7 fiksturu) -> yazar, rc=0", v6)):
        g, a = fn(m)
        kayit(ad, g, a)

    with open(KUR, encoding="utf-8") as f:
        kaynak = f.read()
    adet = kaynak.count(MUT_CAPA)
    kayit("M0 mutant capasi TEK", adet == 1, "capa_adedi=%d" % adet)
    if adet == 1:
        with tempfile.TemporaryDirectory(prefix="k357-mut-") as td:
            mut = os.path.join(td, "kur.py")
            yaz_dosya(mut, kaynak.replace(MUT_CAPA, MUT_YAMA, 1))
            mm = modul_yukle(mut, "kur_k357_mutant")
            g1, a1 = v1(mm)
            kayit("M1 MUTANT V1'i KIRMIZIYA dusurur", not g1, "mutant V1: %s" % a1)
            g2, a2 = v2(mm)
            kayit("M2 MUTANT KONTROL: V2 yesil kalir", g2, "mutant V2: %s" % a2)

    dusen = [a for a, g in sonuc if not g]
    print("IDDIA SAYISI=%d GECTI=%d DUSTU=%d" % (len(sonuc), len(sonuc) - len(dusen), len(dusen)))
    return 1 if dusen else 0


if __name__ == "__main__":
    sys.exit(main())
