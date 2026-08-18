#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K185 nöbetçisi için vaka, mutasyon ve kontrol kabul testi."""
import os
import re
import shutil
import subprocess
import sys
import tempfile


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAPI = os.path.join(ROOT, "tools", "chip-duzeni-kapisi.py")
SAHIPLIK = os.path.join(ROOT, "tools", "sahiplik-kapisi.py")


def _defter(*kalemler):
    return "## ACIK KALEMLER\n" + "\n".join(kalemler) + "\n## SONRA\n"


VAKALAR = (
    ("V1 POZITIF", _defter(
        "- 🟠 **K185 CHIP `KraL-birinci`:** açık",
        "- 🟠 **K186 CHIP `HocA-ikinci`:** açık"),
     "KraL-birinci BASLIYORUM\nHocA-ikinci BASLIYORUM\n", 0,
     ("YESIL", "KALEM=2", "CHIP=2")),
    ("V2 NEGATIF onek yok", _defter(
        "- 🟠 **K185 CHIP `Chip duzeni genelleme`:** açık"),
     "Chip duzeni genelleme BASLIYORUM\n", 1,
     ("KIRMIZI", "ONEK_KIRMIZI=1")),
    ("V3 NEGATIF bilinmeyen ev", _defter(
        "- 🟠 **K185 CHIP `ZzZ-bir is`:** açık"),
     "ZzZ-bir is BASLIYORUM\n", 1,
     ("KIRMIZI", "ONEK_KIRMIZI=1")),
    ("V4 NEGATIF bos is", _defter(
        "- 🟠 **K185 CHIP `KraL-`:** açık"),
     "KraL- BASLIYORUM\n", 1,
     ("KIRMIZI", "ONEK_KIRMIZI=1")),
    ("V5 NEGATIF kutu izi yok", _defter(
        "- 🟠 **K185 CHIP `KraL-izsiz`:** açık"),
     "başka iş BASLIYORUM\n", 1,
     ("KIRMIZI", "IZ_KIRMIZI=1")),
    ("V6a KAPSAM DISI temiz", _defter(
        "- 🟠 **K185 CHIP `KraL-kutusuz`:** açık"),
     None, 0,
     ("KUTU_KAPSAM_DISI",)),
    ("V6b KAPSAM DISI ve bozuk onek", _defter(
        "- 🟠 **K185 CHIP `ZzZ-kutusuz`:** açık"),
     None, 1,
     ("KUTU_KAPSAM_DISI", "ONEK_KIRMIZI=1")),
    ("V7 OLCULEMEDI defter yok", None,
     "KraL-var BASLIYORUM\n", 2,
     ("OLCULEMEDI",)),
    ("V8 OLCULEMEDI bos bolge", "## ACIK KALEMLER\n## SONRA\n",
     "KraL-var BASLIYORUM\n", 2,
     ("OLCULEMEDI",)),
    ("V9 POZITIF chip yok", _defter("- normal açık kalem"),
     "", 0,
     ("YESIL", "KALEM=1", "CHIP=0")),
    ("V10 POZITIF kimlik izi", _defter(
        "- 🟠 **K185 CHIP `KraL-adi kutuda yok`:** açık"),
     "K185 BASLIYORUM\n", 0,
     ("YESIL", "IZ_KIRMIZI=0")),
)


def _dosyaya_yaz(yol, icerik):
    with open(yol, "w", encoding="utf-8") as dosya:
        dosya.write(icerik)


def _kos(source, owner, base_dir, defter, kutu, extra=()):
    run_dir = tempfile.mkdtemp(prefix="kosum-", dir=base_dir)
    try:
        tools_dir = os.path.join(run_dir, "tools")
        os.makedirs(tools_dir)
        source_path = os.path.join(tools_dir, "chip-duzeni-kapisi.py")
        owner_path = os.path.join(tools_dir, "sahiplik-kapisi.py")
        _dosyaya_yaz(source_path, source)
        shutil.copyfile(owner, owner_path)
        defter_path = os.path.join(run_dir, "DEVAM.md")
        kutu_path = os.path.join(run_dir, "kutu.md")
        if defter is not None:
            _dosyaya_yaz(defter_path, defter)
        if kutu is not None:
            _dosyaya_yaz(kutu_path, kutu)
        komut = [sys.executable, source_path, "--defter", defter_path,
                 "--kutu", kutu_path]
        komut.extend(extra)
        tamam = subprocess.run(komut, capture_output=True, text=True, timeout=2)
        return tamam.returncode, tamam.stdout + tamam.stderr
    finally:
        shutil.rmtree(run_dir)


def _vaka_kontrol(source, owner, base_dir, vaka):
    ad, defter, kutu, beklenen_rc, jetonlar = vaka
    rc, cikti = _kos(source, owner, base_dir, defter, kutu)
    son = cikti.strip().splitlines()[-1] if cikti.strip() else ""
    tamam = rc == beklenen_rc and all(jeton in cikti for jeton in jetonlar)
    return tamam, (ad, rc, son)


def _mutasyon_uygula(source, degisimler):
    sonuc = source
    for capa, yeni in degisimler:
        if sonuc.count(capa) != 1:
            return None, "CAPA BOZUK: %r sayi=%d" % (capa, sonuc.count(capa))
        sonuc = sonuc.replace(capa, yeni, 1)
    return sonuc, None


def _mutasyon_kontrol(source, owner, base_dir, tanim):
    ad, degisimler, vaka_indeksi, beklenen, aranan = tanim
    mutant, hata = _mutasyon_uygula(source, degisimler)
    if mutant is None:
        return False, "%s %s" % (ad, hata)
    vaka = VAKALAR[vaka_indeksi]
    rc, cikti = _kos(mutant, owner, base_dir, vaka[1], vaka[2])
    rc_taban, cikti_taban = _kos(source, owner, base_dir, vaka[1], vaka[2])
    fark = (rc, cikti) != (rc_taban, cikti_taban)
    if aranan.startswith("ABSENT:"):
        jeton = aranan.split(":", 1)[1]
        jeton_kosulu = jeton not in cikti and jeton in cikti_taban
    else:
        jeton_kosulu = aranan in cikti and aranan not in cikti_taban
    canary_kosulu = True
    if ad.startswith("M5"):
        canaryli, canary_hata = _mutasyon_uygula(source, (degisimler[1],))
        if canaryli is None:
            return False, "%s %s" % (ad, canary_hata)
        canary_rc, canary_cikti = _kos(canaryli, owner, base_dir, vaka[1], vaka[2])
        canary_kosulu = canary_rc == 2 and "OLCULEMEDI" in canary_cikti
    sonuc = (rc == beklenen[0] and jeton_kosulu and canary_kosulu and
             rc_taban == beklenen[1] and fark)
    return sonuc, "%s taban_rc=%d mutant_rc=%d" % (ad, rc_taban, rc)


def _kontrol_mutanti(source, owner, base_dir, tanim):
    ad, capa, yeni = tanim
    mutant, hata = _mutasyon_uygula(source, ((capa, yeni),))
    if mutant is None:
        return False, "%s %s" % (ad, hata)
    taban = []
    mutasyon = []
    for vaka in VAKALAR:
        taban.append(_kos(source, owner, base_dir, vaka[1], vaka[2])[0])
        mutasyon.append(_kos(mutant, owner, base_dir, vaka[1], vaka[2])[0])
    return taban == mutasyon, "%s rc dizisi=%s" % (ad, taban)


def main():
    base_dir = tempfile.mkdtemp(prefix="chip-k185-test-")
    try:
        with open(KAPI, encoding="utf-8") as dosya:
            source = dosya.read()
        vaka_sonuclari = [_vaka_kontrol(source, SAHIPLIK, base_dir, vaka)
                          for vaka in VAKALAR]
        vaka_gecen = sum(1 for tamam, _detay in vaka_sonuclari if tamam)

        mutantlar = (
            ("M1 eksen 1 ev oneki",
             (("return _ev_onek_gecerli(chip_adi, evler)  # CHIP_MUTANT_M1_PREFIX",
               "return True  # CHIP_MUTANT_M1_PREFIX"),),
             1, (0, 1), "ONEK_KIRMIZI=0"),
            ("M2 eksen 2 kutu izi",
             (("return iz_var  # CHIP_MUTANT_M2_TRACE",
               "return True  # CHIP_MUTANT_M2_TRACE"),),
             4, (0, 1), "IZ_KIRMIZI=0"),
            ("M3 KAPSAM DISI jetonu",
             (("kapsam = \" KUTU_KAPSAM_DISI\" if sonuc[\"kutu_kapsam_dis\"] else \"\"  # CHIP_MUTANT_M3_SCOPE_OUTPUT",
               "kapsam = \"\"  # CHIP_MUTANT_M3_SCOPE_OUTPUT"),),
             5, (0, 0), "ABSENT:KUTU_KAPSAM_DISI"),
            ("M4 fail-open",
             (("return _olculemedi_sonucu(\"defter dosyası okunamadı\")  # CHIP_MUTANT_M4_FAIL_CLOSED",
               "return {\"hal\": YESIL, \"rc\": 0, \"kalem\": 0, \"chip\": 0, \"onek_kirmizi\": 0, \"iz_kirmizi\": 0, \"items\": [], \"kutu_kapsam_dis\": False, \"gerekce\": \"mutant\"}  # CHIP_MUTANT_M4_FAIL_CLOSED"),),
             7, (0, 2), "CHIP DUZENI: YESIL"),
            ("M5 canary + kesif",
             (("if not _canary():  # CHIP_MUTANT_M5_CANARY",
               "if False:  # CHIP_MUTANT_M5_CANARY"),
              ("CHIP_TOKEN_RE = re.compile(r\"\\bCHIP\\b\")  # CHIP_MUTANT_M5_DISCOVERY",
               "CHIP_TOKEN_RE = re.compile(r\"\\bBROKEN_CHIP\\b\")  # CHIP_MUTANT_M5_DISCOVERY")),
             0, (0, 0), "CHIP=0"),
            ("M6 KAPSAM DISI/OLCULEMEDI ayrimi",
             (("if kutu_kapsam_dis:\n        # CHIP_MUTANT_M6_SCOPE\n        kutu_kapsam_dis = True",
               "if kutu_kapsam_dis:\n        # CHIP_MUTANT_M6_SCOPE\n        return _olculemedi_sonucu(\"kutu okunamadı\")"),),
             5, (2, 0), "OLCULEMEDI"),
        )
        mutant_sonuclari = [_mutasyon_kontrol(source, SAHIPLIK, base_dir, mutant)
                            for mutant in mutantlar]
        mutant_gecen = sum(1 for tamam, _detay in mutant_sonuclari if tamam)

        kontroller = (
            ("K1 yorum/docstring",
             "Bu kapı oturum panelini değil",
             "Bu kapı oturum panelini değilmiş"),
            ("K2 açıklama kelimesi",
             "ev öneki %s",
             "ev etiketi %s"),
        )
        kontrol_sonuclari = [_kontrol_mutanti(source, SAHIPLIK, base_dir, kontrol)
                             for kontrol in kontroller]
        kontrol_gecen = sum(1 for tamam, _detay in kontrol_sonuclari if tamam)

        if vaka_gecen != len(VAKALAR):
            for _tamam, detay in vaka_sonuclari:
                if not _tamam:
                    print("VAKA KIRMIZI: %s" % (detay,))
        if mutant_gecen != len(mutantlar):
            for _tamam, detay in mutant_sonuclari:
                if not _tamam:
                    print("MUTANT KIRMIZI: %s" % (detay,))
        if kontrol_gecen != len(kontroller):
            for _tamam, detay in kontrol_sonuclari:
                if not _tamam:
                    print("KONTROL KIRMIZI: %s" % (detay,))
        rc = 0 if (vaka_gecen == len(VAKALAR) and
                   mutant_gecen == len(mutantlar) and
                   kontrol_gecen == len(kontroller)) else 1
        print("CHIP DUZENI TEST: VAKA=%d/%d MUTANT=%d/%d KONTROL=%d/%d RC=%d" %
              (vaka_gecen, len(VAKALAR), mutant_gecen, len(mutantlar),
               kontrol_gecen, len(kontroller), rc))
        return rc
    finally:
        shutil.rmtree(base_dir)


if __name__ == "__main__":
    sys.exit(main())
