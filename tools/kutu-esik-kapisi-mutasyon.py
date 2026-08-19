#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KUTU ESİK KAPISI MUTASYON BATARYASI — hedef kolları oldurur.

Mutantlar yalniz gecici dizindeki kaynak kopyalarina uygulanir. Asil kapı ve
arsiv araci degismez; bytecode da yazilmaz. Her mutant hedef vakayi kirmali ve
yan vakalari yesil birakmalidir.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True


TOOLS = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(TOOLS, "kutu-esik-kapisi.py")
ARSIV = os.path.join(TOOLS, "kutu-arsivle.py")


def komut(kapi):
    return subprocess.run([sys.executable, kapi, "--kendini-test"],
                          capture_output=True, text=True)


def vaka_durumu(cikti, vaka):
    eslesen = re.findall(r"^V%d (YESIL|KIRMIZI)\b" % vaka, cikti, re.MULTILINE)
    return eslesen[0] if eslesen else "OLCULEMEDI"


def kaynak_satiri(kaynak, aranan):
    konum = kaynak.find(aranan)
    if konum >= 0:
        numara = kaynak.count("\n", 0, konum) + 1
        satir = kaynak.splitlines()[numara - 1]
        return numara, satir
    return 0, ""


def mutant_kos(kok, ad, aranan, yerine, hedefler, yanlar, kaynak):
    mutant = os.path.join(kok, "mutant-%s-kapi.py" % ad)
    arsiv_kopya = os.path.join(kok, "kutu-arsivle.py")
    shutil.copyfile(KAPI, mutant)
    shutil.copyfile(ARSIV, arsiv_kopya)
    with open(mutant, "r", encoding="utf-8") as dosya:
        metin = dosya.read()
    bulundu = metin.count(aranan)
    kaynakta_bulundu = kaynak.count(aranan)
    if bulundu == 1 and kaynakta_bulundu == 1:
        metin = metin.replace(aranan, yerine, 1)
        with open(mutant, "w", encoding="utf-8", newline="") as dosya:
            dosya.write(metin)
    sonuc = komut(mutant) if bulundu == 1 else None
    cikti = "" if sonuc is None else sonuc.stdout + sonuc.stderr
    olcum = bulundu == 1 and kaynakta_bulundu == 1
    hedef_kirmizi = olcum and all(vaka_durumu(cikti, v) == "KIRMIZI"
                                          for v in hedefler)
    yan_yesil = olcum and all(vaka_durumu(cikti, v) == "YESIL"
                                     for v in yanlar)
    satir_no, satir_metni = kaynak_satiri(kaynak, aranan)
    hukum = "OLDURDU" if hedef_kirmizi and yan_yesil else "OLDURMEDI"
    print("%s %s: hedef=%s hedef_kirmizi=%s yan_yesil=%s dizge_satir=%d "
          "HUKUM=%s" %
          (ad, {"M1": "ESIK OKUNMUYOR", "M2": "ROTASYON TETIKLENMIYOR",
                "M3": "FAIL-CLOSED KOLU OLU", "M4": "ROTASYON ISTISNA KOLU OLU",
                "M5": "ROTASYON SONRASI OLCUM KOLU OLU",
                "M6": "ESIK KAYNAGI FAIL-CLOSED KOLU OLU",
                "M7": "HEDEF KUTU OLCUMU FAIL-CLOSED KOLU OLU"}[ad],
           ",".join("V%d" % v for v in hedefler),
           "EVET" if hedef_kirmizi else "HAYIR",
           "EVET" if yan_yesil else "HAYIR", satir_no, hukum))
    if satir_no:
        print("%s dizge=%s" % (ad, satir_metni.strip()))
    else:
        print("%s dizge=OLCULEMEDI (kaynakta bulunamadi)" % ad)
    return hukum == "OLDURDU"


def m8_ci_tespiti(kok, kaynak):
    """M8 — CI-TESPIT AYRIMI CANLI MI (KUTU_KAPSAM_DISI kolunun iki yonu).

    GERCEK_KUTU ekseni V1..V11 vaka cercevesinde degil, kendini-test'in
    sonundadir; bu yuzden vaka-bazli mutant_kos'a girmez. Olcum sahte-HOME
    (gercek kutu YOK) ortaminda uc koldan yapilir:
      KONTROL-A: mutantsiz kapi, CI degiskenleri temiz -> rc=1 + OLCULEMEDI
                 (yerel fail-closed CANLI; kol yerelde acilmiyor)
      KONTROL-B: mutantsiz kapi, GITHUB_ACTIONS=true -> rc=0 + KUTU_KAPSAM_DISI
                 (CI kolu CANLI; runner'da eksen kapsam disi)
      M8 mutant: ci_ortaminda() govdesi `return True` yapilinca temiz ortamda
                 rc=0'a kayar -> karari GERCEKTEN tespit satiri veriyor.
    Capa nobeti (count==1) tespit satirinin kaynaktan sokulmesini ayrica yakalar.
    """
    aranan = '    return os.environ.get("GITHUB_ACTIONS") == "true"'
    yerine = "    return True"
    sahte_home = os.path.join(kok, "m8-sahte-home")
    os.makedirs(sahte_home, exist_ok=True)
    temiz = dict(os.environ)
    temiz["HOME"] = sahte_home
    temiz.pop("GITHUB_ACTIONS", None)
    temiz.pop("CI", None)
    ci_ortam = dict(temiz)
    ci_ortam["GITHUB_ACTIONS"] = "true"

    def kos(kapi, ortam):
        return subprocess.run([sys.executable, kapi, "--kendini-test"],
                              capture_output=True, text=True, env=ortam)

    kontrol_a = kos(KAPI, temiz)
    a_iyi = (kontrol_a.returncode == 1 and
             "GERCEK_KUTU_BAYT: OLCULEMEDI" in kontrol_a.stdout)
    kontrol_b = kos(KAPI, ci_ortam)
    b_iyi = (kontrol_b.returncode == 0 and
             "KUTU_KAPSAM_DISI" in kontrol_b.stdout)

    mutant = os.path.join(kok, "mutant-M8-kapi.py")
    shutil.copyfile(KAPI, mutant)
    shutil.copyfile(ARSIV, os.path.join(kok, "kutu-arsivle.py"))
    with open(mutant, "r", encoding="utf-8") as dosya:
        metin = dosya.read()
    bulundu = metin.count(aranan)
    kaynakta_bulundu = kaynak.count(aranan)
    olcum = bulundu == 1 and kaynakta_bulundu == 1
    m_rc = None
    m_kapsam = False
    if olcum:
        metin = metin.replace(aranan, yerine, 1)
        with open(mutant, "w", encoding="utf-8", newline="") as dosya:
            dosya.write(metin)
        m_sonuc = kos(mutant, temiz)
        m_rc = m_sonuc.returncode
        m_kapsam = "KUTU_KAPSAM_DISI" in m_sonuc.stdout
    satir_no, satir_metni = kaynak_satiri(kaynak, aranan)
    iyi = olcum and a_iyi and b_iyi and m_rc == 0 and m_kapsam
    hukum = "OLDURDU" if iyi else "OLDURMEDI"
    print("M8 CI-TESPIT AYRIMI: kontrolA_failclosed=%s kontrolB_ci_kapsamdisi=%s "
          "mutant_rc=%s mutant_kapsamdisi=%s dizge_satir=%d HUKUM=%s" %
          ("EVET" if a_iyi else "HAYIR", "EVET" if b_iyi else "HAYIR",
           m_rc, "EVET" if m_kapsam else "HAYIR", satir_no, hukum))
    if satir_no:
        print("M8 dizge=%s" % satir_metni.strip())
    else:
        print("M8 dizge=OLCULEMEDI (kaynakta bulunamadi)")
    return iyi


def main():
    with open(KAPI, "r", encoding="utf-8") as dosya:
        kaynak = dosya.read()
    taban = komut(KAPI)
    taban_cikti = taban.stdout + taban.stderr
    taban_11_yesil = (taban.returncode == 0 and
                      "KENDINI-TEST: 11/11" in taban.stdout and
                      all(vaka_durumu(taban_cikti, v) == "YESIL"
                          for v in range(1, 12)))
    print("TABAN MUTASYONSUZ rc=%d KENDINI-TEST: %s" %
          (taban.returncode, "11/11 YESIL" if taban_11_yesil else "OLCULEMEDI/KIRMIZI"))
    if not taban_11_yesil:
        print("MUTASYON: 0/7 OLDURDU")
        return 1

    mutantler = [
        ("M1", "    tavan = arsiv_mod.VARSAYILAN_TAVAN",
         "    tavan = 10**9", [4], [1, 2, 3]),
        ("M2", r'''        sonuc = subprocess.run(
            [sys.executable, arsiv_araci, "--kutu", kutu_yolu],
            capture_output=True, text=True, timeout=zaman_asimi_saniyesi())''',
         "        sonuc = _SahteSonuc()", [4], [1, 2, 3]),
        ("M3", r'''    sys.stderr.write(
        "KUTU ESIK KAPISI (fail-closed): kutu %d satir, tavan %d. "
        "Rotasyon rc=%s ile tavani indiremedi -> yazma REDDEDILDI.\n" %
        (sonra, tavan, sonuc.returncode))
    rotasyon_ciktisini_yaz(sonuc)
    return 2''',
         r'''    sys.stderr.write(
        "KUTU ESIK KAPISI (fail-closed): kutu %d satir, tavan %d. "
        "Rotasyon rc=%s ile tavani indiremedi -> yazma REDDEDILDI.\n" %
        (sonra, tavan, sonuc.returncode))
    rotasyon_ciktisini_yaz(sonuc)
    return 0''',
         [5, 6], [1, 2, 3, 4]),
        ("M4", r'''        sys.stderr.write(
            "KUTU ESIK KAPISI (fail-closed): rotasyon istisna ile basarisiz "
            "(%s) -> yazma REDDEDILDI.\n" % hata)
        return 2''',
         r'''        sys.stderr.write(
            "KUTU ESIK KAPISI (fail-closed): rotasyon istisna ile basarisiz "
            "(%s) -> yazma REDDEDILDI.\n" % hata)
        return 0''',
         [7], [1, 2, 3, 4, 5, 6, 8, 9, 10]),
        ("M5", r'''        sys.stderr.write(
            "KUTU ESIK KAPISI (fail-closed): rotasyon sonrasi kutu olculemedi "
            "(%s) -> yazma REDDEDILDI.\n" % hata)
        rotasyon_ciktisini_yaz(sonuc)
        return 2''',
         r'''        sys.stderr.write(
            "KUTU ESIK KAPISI (fail-closed): rotasyon sonrasi kutu olculemedi "
            "(%s) -> yazma REDDEDILDI.\n" % hata)
        rotasyon_ciktisini_yaz(sonuc)
        return 0''',
         [8], [1, 2, 3, 4, 5, 6, 7, 9, 10]),
        ("M6", r'''        sys.stderr.write(
            "KUTU ESIK KAPISI (fail-closed): esik kaynagi (%s) "
            "yuklenemedi (%s) -> esik OLCULEMEDI, yazma REDDEDILDI.\n" %
            (arsiv_araci, hata))
        return 2''',
         r'''        sys.stderr.write(
            "KUTU ESIK KAPISI (fail-closed): esik kaynagi (%s) "
            "yuklenemedi (%s) -> esik OLCULEMEDI, yazma REDDEDILDI.\n" %
            (arsiv_araci, hata))
        return 0''',
         [9], [1, 2, 3, 4, 5, 6, 7, 8, 10]),
        ("M7", r'''    try:
        once = kutu_satir_sayisi(kutu_yolu)
    except (OSError, UnicodeDecodeError) as hata:
        sys.stderr.write(
            "KUTU ESIK KAPISI (fail-closed): hedef kutu olculemedi (%s) "
            "-> yazma REDDEDILDI.\n" % hata)
        return 2''',
         r'''    try:
        once = kutu_satir_sayisi(kutu_yolu)
    except (OSError, UnicodeDecodeError) as hata:
        sys.stderr.write(
            "KUTU ESIK KAPISI (fail-closed): hedef kutu olculemedi (%s) "
            "-> yazma REDDEDILDI.\n" % hata)
        return 0''',
         [11], list(range(1, 11))),
    ]
    kok = tempfile.mkdtemp(prefix="kutu-esik-mutasyon-")
    try:
        olduren = 0
        for ad, aranan, yerine, hedefler, yanlar in mutantler:
            if mutant_kos(kok, ad, aranan, yerine, hedefler, yanlar, kaynak):
                olduren += 1
        if m8_ci_tespiti(kok, kaynak):
            olduren += 1
    finally:
        shutil.rmtree(kok)
    print("MUTASYON: %d/8 %s" %
          (olduren, "OLDURDU" if olduren == 8 else "OLDURMEDI"))
    return 0 if olduren == 8 else 1


if __name__ == "__main__":
    sys.exit(main())
