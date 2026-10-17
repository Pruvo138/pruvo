#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/d1-zarf-fikstur-kapisi.py (D1 okuyucusu gercek zarf fiksturune bagli mi).

KABUL SORUSU: "bu satiri silsem hangi vaka kirmizi yanar?" — her vaka/mutant yorumunda.
Fikstur kok TEMPFILE altinda kurulur (kapi + yardimci + zarf kopyalanir, sahte araclar
yazilir); gercek ev agacina YAZILMAZ, silinen yalniz testin kendi gecici dizinidir.

Kosum (borusuz):  python3 tools/d1-zarf-fikstur-kapisi-test.py
Son satir: KABUL <g>/6 MUTANT <m>/3  (YESIL icin 6/6 + 3/3; rc=0).
"""
import os
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
KAPI = "d1-zarf-fikstur-kapisi.py"

OKUYUCU = 'import x\nr = d1.sorgu("SELECT 1")\nsatir = r[0]["results"]\n'
YAZICI = 'import x\nd1.sorgu("DELETE FROM t")\n'              # D1 cagrisi var, sonuc ayristirmaz
BAGLI_TEST = 'import d1_zarf_fikstur as Z\n# okur.py kabul\n'
YARDIMCISIZ_TEST = '# okur.py kabul — elle yazilmis zarf\n'


def kok_kur(tmp, dosyalar, kapi_kaynak=None, zarf_bozuk=False):
    tools = os.path.join(tmp, "tools")
    os.makedirs(os.path.join(tools, "fikstur"))
    shutil.copyfile(kapi_kaynak or os.path.join(TOOLS, KAPI), os.path.join(tools, KAPI))
    shutil.copyfile(os.path.join(TOOLS, "d1_zarf_fikstur.py"), os.path.join(tools, "d1_zarf_fikstur.py"))
    zarf = os.path.join(tools, "fikstur", "wrangler-d1-zarf.json")
    if zarf_bozuk:
        with open(zarf, "w", encoding="utf-8") as f:
            f.write('{"success": true}')
    else:
        shutil.copyfile(os.path.join(TOOLS, "fikstur", "wrangler-d1-zarf.json"), zarf)
    for ad, metin in dosyalar.items():
        with open(os.path.join(tools, ad), "w", encoding="utf-8") as f:
            f.write(metin)
    return tools


def kos(tools):
    p = subprocess.run([sys.executable, os.path.join(tools, KAPI), "--kok", os.path.dirname(tools)],
                       capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout + p.stderr


VAKALAR = {
    # K1: okuyucunun testi yok -> rc1, EKSIK satiri (kapsam kolu silinirse YESIL gecer)
    "K1": ({"okur.py": OKUYUCU}, False, lambda rc, c: rc == 1 and "EKSIK: tools/okur.py" in c),
    # K2: test adi aniyor ama yardimciyi kullanmiyor -> rc1 (YARDIMCI kosulu silinirse YESIL)
    "K2": ({"okur.py": OKUYUCU, "okur-test.py": YARDIMCISIZ_TEST}, False,
           lambda rc, c: rc == 1 and "EKSIK: tools/okur.py" in c),
    # K3: ad + yardimci -> rc0 YESIL
    "K3": ({"okur.py": OKUYUCU, "okur-test.py": BAGLI_TEST}, False,
           lambda rc, c: rc == 0 and "D1_ZARF_KAPSAM=1 BAGLI=1 EKSIK=0 HAL=YESIL" in c),
    # K4: sonuc ayristirmayan yazici kapsam disi (SONUC kosulu silinirse yazici EKSIK olur)
    "K4": ({"okur.py": OKUYUCU, "okur-test.py": BAGLI_TEST, "yazar.py": YAZICI}, False,
           lambda rc, c: rc == 0 and "D1_ZARF_KAPSAM=1 " in c and "yazar.py" not in c),
    # K5: zarf fiksturu bozuk -> rc2 OLCULEMEDI (sekil kontrolu silinirse YESIL gecer)
    "K5": ({"okur.py": OKUYUCU, "okur-test.py": BAGLI_TEST}, True,
           lambda rc, c: rc == 2 and "D1_ZARF=OLCULEMEDI sebep=FIKSTUR" in c),
    # K6: yardimciyi kullanan dosya TEST DEGIL -> baglamaz, rc1
    "K6": ({"okur.py": OKUYUCU, "okur-yardim.py": BAGLI_TEST}, False,
           lambda rc, c: rc == 1 and "EKSIK: tools/okur.py" in c),
}

MUTANTLAR = {
    # M1: yardimci kosulu kalkar -> K2 YESIL olur
    "M1": ("if ad in metin and YARDIMCI in metin:", "if ad in metin:", "K2"),
    # M2: sonuc ayristirma kosulu kalkar -> K4'te yazici kapsama girer
    "M2": ("if D1_CAGRI.search(metin) and SONUC.search(metin):", "if D1_CAGRI.search(metin):", "K4"),
    # M3: fikstur sekli denetlenmez -> K5 rc2 vermez
    "M3": ("    if not fikstur_saglam(tools):\n", "    if False:\n", "K5"),
}


def vaka_kos(ad, kapi_kaynak=None):
    dosyalar, bozuk, bek = VAKALAR[ad]
    tmp = tempfile.mkdtemp(prefix="d1zarf-%s-" % ad.lower())
    try:
        rc, cikti = kos(kok_kur(tmp, dosyalar, kapi_kaynak, bozuk))
        return bek(rc, cikti), rc, cikti
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    gecen, hata = [], []
    for ad in VAKALAR:
        ok, rc, cikti = vaka_kos(ad)
        (gecen if ok else hata).append(ad if ok else "%s rc=%d cikti=%r" % (ad, rc, cikti[:300]))
    with open(os.path.join(TOOLS, KAPI), encoding="utf-8") as f:
        govde = f.read()
    for ad, (eski, yeni, hedef) in MUTANTLAR.items():
        if govde.count(eski) != 1:
            hata.append("%s MUTANT CAPASI BAYAT: %r govdede %d kez" % (ad, eski, govde.count(eski)))
            continue
        tmp = tempfile.mkdtemp(prefix="d1zarf-%s-" % ad.lower())
        try:
            kopya = os.path.join(tmp, KAPI)
            with open(kopya, "w", encoding="utf-8") as f:
                f.write(govde.replace(eski, yeni, 1))
            ok, rc, cikti = vaka_kos(hedef, kapi_kaynak=kopya)
            if not ok:
                gecen.append(ad)
            else:
                hata.append("%s SAG KALDI: %s mutantla da gecti (rc=%d)" % (ad, hedef, rc))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    v = [g for g in gecen if g.startswith("K")]
    m = [g for g in gecen if g.startswith("M")]
    for h in hata:
        print("KIRMIZI: %s" % h)
    print("KABUL %d/%d MUTANT %d/%d" % (len(v), len(VAKALAR), len(m), len(MUTANTLAR)))
    ok = not hata and len(v) == len(VAKALAR) and len(m) == len(MUTANTLAR)
    print("HAL=YESIL" if ok else "HAL=KIRMIZI")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
