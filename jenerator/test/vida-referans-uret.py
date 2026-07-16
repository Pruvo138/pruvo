#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VIDA kalibrasyon fixture'ini uretir -> kalibrasyon-referans.json "vida" ailesi.

Vida ailesinin fiyat referansi URETIM MOTORUDUR (onizleme paketindeki uretec;
eslem onizleme/derleyici/eslem-ozel.json'dan gelir — gizli dosya, degisken
adlari bu koda YAZILMAZ). pruvo-jenerator'deki vida.scad (BOSL2) referans
DEGILDIR: altigen kafa tablosu M5 altini ve tablo disi ara olculeri kapsamiyor,
uretim de o motorla yapilmiyor. Eski jenerator/test/esleme/vida.json bu yuzden
kaldirildi (olcu=M5'e cakiliydi — capa duyarsiz fiyat hatasinin kaynagi).

Dondurulmus set (deterministik, rastgele yok):
  - civata: M5..M20 standart olculer x boy {10, 20*, 55, 100} (*yalniz M5;
    varsayilan set). M3/M4 civata URETIM MOTORUNDA BOS GEOMETRI (altigen kafa
    tablosu M5'ten basliyor) -> fixture yok, uretilemezlik raporda/mimarda.
  - mil: M3..M20 x boy {10, 100} + dogrusallik ara noktasi boy=55 (M3/M12/M20).
  - somun: M3..M20 (boy/tolerans hacmi etkilemez).
  - pul: M3..M20 + tolerans duyarsizlik kontrolu (M3 tol=0, M20 tol=1 —
    uretim motoru pul olcusunu ISO tablosundan alir, tolerans hacme etkimez).
Standart olcu listesi uretim esleminin Spec tablosuyla ayni (11 olcu);
ara (yarim) olculeri uretim motoru REDDEDER -> fixture uretilmez, fiyat
formulu ara olcuyu komsu olculerden enterpolasyonla fiyatlar.

Konektor/braket/disli fixture'larina DOKUNMAZ (onlar kalibrasyon-referans-uret.py).
Kullanim: python3 jenerator/test/vida-referans-uret.py
Gerekli: eslem-ozel.json + uretim .scad kaynaklari (mimar makinesi) + openscad.
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(TEST_DIR))
AILE_ID = "olcuye-ozel-vida-civata-somun-pul"
sys.path.insert(0, TEST_DIR)
import dogrula     # noqa: E402
import stl_hacim   # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "onizleme_server", os.path.join(REPO, "onizleme", "derleyici", "server.py"))
server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(server)

CAPLAR = [3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20]


def setler():
    s = [{"urun_tipi": "civata", "cap": 5, "boy": 20, "tolerans": 0.2}]  # varsayilan
    for cap in CAPLAR:
        if cap >= 5:
            for boy in (10, 55, 100):
                s.append({"urun_tipi": "civata", "cap": cap, "boy": boy,
                          "tolerans": 0.2})
        for boy in (10, 100):
            s.append({"urun_tipi": "mil", "cap": cap, "boy": boy, "tolerans": 0.2})
        s.append({"urun_tipi": "somun", "cap": cap, "boy": 20, "tolerans": 0.2})
        s.append({"urun_tipi": "pul", "cap": cap, "boy": 20, "tolerans": 0.2})
    for cap in (3, 12, 20):
        s.append({"urun_tipi": "mil", "cap": cap, "boy": 55, "tolerans": 0.2})
    s.append({"urun_tipi": "pul", "cap": 3, "boy": 20, "tolerans": 0.0})
    s.append({"urun_tipi": "pul", "cap": 20, "boy": 20, "tolerans": 1.0})
    return s


def paket_topla():
    hedef = tempfile.mkdtemp(prefix="vida-referans-paket-")
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO, "tools", "onizleme-paket-yukle.py"),
         "--yerel", hedef], capture_output=True)
    if proc.returncode != 0:
        sys.exit("paket toplanamadi:\n%s%s" %
                 (proc.stdout.decode("utf-8", "replace"),
                  proc.stderr.decode("utf-8", "replace")))
    return hedef


def scad_yolu_sec(eslem_aile, sset, paket):
    scad = eslem_aile.get("scad")
    secici = eslem_aile.get("secici")
    if secici:
        varyant = (eslem_aile.get("varyantlar") or {}).get(sset.get(secici)) or {}
        scad = varyant.get("scad", scad)
    return os.path.join(paket, scad)


def main():
    openscad = dogrula.openscad_yolu()
    paket = paket_topla()
    eslem = server.eslem_yukle(paket)
    if AILE_ID not in eslem:
        sys.exit("eslem paketinde vida yok")
    aile = eslem[AILE_ID]

    kayitlar = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, sset in enumerate(setler()):
            bayraklar, sebep = server.d_bayraklari(aile, sset)
            if bayraklar is None:
                sys.exit("dondurulmus set eslem disi kaldi (%s): %s" %
                         (sebep, json.dumps(sset)))
            stl = os.path.join(tmp, "vida-%d.stl" % i)
            komut = [openscad, "-o", stl, "--export-format", "binstl"] + \
                bayraklar + [scad_yolu_sec(aile, sset, paket)]
            ref = None
            for _ in range(3):  # ara ara SIGABRT (dogrula.py notu) -> tekrar
                proc = subprocess.run(komut, capture_output=True, timeout=600)
                if proc.returncode == 0 and os.path.exists(stl):
                    ref = stl_hacim.hacim(stl)
                    break
            if ref is None:
                sys.exit("vida set%d israrla uretilemedi: %s\n%s" % (
                    i, json.dumps(sset),
                    proc.stderr.decode("utf-8", "replace")[-500:]))
            kayitlar.append({"parametreler": sset, "referansMm3": ref})
            print("  vida set%-3d %-6s M%-4g boy=%-4g referans=%.2f mm3" %
                  (i, sset["urun_tipi"], sset["cap"], sset["boy"], ref))

    yol = os.path.join(TEST_DIR, "kalibrasyon-referans.json")
    with io.open(yol, encoding="utf-8") as f:
        veri = json.load(f)
    veri["aileler"]["vida"] = {
        "_not": ("Referans URETIM MOTORU render'i (vida-referans-uret.py, "
                 "dondurulmus deterministik set). Civata M3/M4 uretim motorunda "
                 "uretilemiyor (bos geometri) -> fixture yok; ara/yarim olculeri "
                 "eslem reddediyor. Pul tolerans'a duyarsiz (son iki set kontrol)."),
        "fonksiyon": "vida",
        "urunId": AILE_ID,
        "setler": kayitlar,
    }
    with io.open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)
    print("yazildi: %s (vida %d set)" % (yol, len(kayitlar)))


if __name__ == "__main__":
    main()
