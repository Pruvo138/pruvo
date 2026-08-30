#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K195(b) KABUL TESTI — defter-kota-kapisi.py "stage disi" kolu.

OLCULEN DELIK (19 Agu 2026): DEVAM.md stage'de degilken kapi HIC OLCMEDEN
`return 0` donuyordu. Yesil "olctum, temiz" degil "BAKMADIM" demekti.

Bu test GERCEK kapiyi (main()) GERCEK bir gecici git deposunda kosar —
fikstur ne defteri ne de bu deponun DEVAM.md'sini kullanir. 🔴 Gercek
/Users/okan/dev/pruvo/DEVAM.md'ye ASLA dokunulmaz.

VAKALAR
  V1 stage DISI + tavan ALTI      -> rc=0, stdout `KAPSAM_DISI_OLCULDU ASIM=YOK`
  V2 stage DISI + tavan USTU      -> rc=0, stderr `KAPSAM_DISI_ASIM`, SAYAC yazildi
  V3 defter IZLENMIYOR (blob yok) -> rc=0, stderr `KAPSAM_DISI_OLCULEMEDI` + SEBEP
  K1 stage ICI  + tavan USTU      -> rc=1 (BLOKLAMA SEMANTIGI DEGISMEDI)
  K2 stage ICI  + tavan ALTI      -> rc=0, `KAPSAM_DISI` cikmaz

MUTANTLAR (her biri KENDI hedef kolunu oldurur — K182 hedef-kol atfi)
  M1 kol tamamen eski haline doner (ciplak return 0)  -> V1+V2+V3 olur, K1+K2 YASAR
  M2 sayac yazimi kaldirilir                          -> YALNIZ V2 olur
  M3 asim kolu BLOKLAR (return 1)                     -> YALNIZ V2 olur
  M4 OLCULEMEDI kolu sessizlesir                      -> YALNIZ V3 olur

Kullanim: python3 tools/defter-kota-kapsam-disi-test.py
Cikti son satiri: VAKA=<n>/<n> MUTANT=<n>/<n> HEDEF_KOL_ATFI=<n>/<n> DUSEN=<n>
"""
import os
import shutil
import subprocess
import sys
import tempfile

from git_ortami import sentetik_git

sys.dont_write_bytecode = True

TOOLS = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(TOOLS, "defter-kota-kapisi.py")
TABAN = os.path.join(TOOLS, "defter-kota-taban.py")
SERBEST = os.path.join(TOOLS, "serbest_cagrilar.py")

# --- mutasyon capalari: kapi kaynagindaki BENZERSIZ dizeler --------------
CAPA_M1 = "        return _kapsam_disi_olc(kok)"
CAPA_M2 = '        _sayaç_yaz(kok, satir, bayt, sinif="KAPSAM_DISI_ASIM")'
CAPA_M3 = ('              % (satir, bayt, TAVAN_SATIR, TAVAN_BAYT, eksen, SAYAC_YOLU),\n'
           '              file=sys.stderr)\n'
           '        return 0')
CAPA_M4 = ('        print("!! KAPSAM_DISI_OLCULEMEDI — DEVAM.md stage\'de yok VE INDEX blob\'u "\n'
           '              "okunamadi. SEBEP: `git cat-file blob :DEVAM.md` sifir-disi dondu "\n'
           '              "(defter izlenmiyor ya da depo kokü yanlis: %s). Kota OLCULMEDI."\n'
           '              % kok, file=sys.stderr)')


def _git(kok, *args):
    # Sentetik depo git'i KANONIK yardimciyla kosar (fikstur-git-sizinti-kapisi
    # sozlesmesi): miras GIT_* kesif baglami scrub'lanir, cwd acikca sabitlenir.
    return sentetik_git(kok, *args, kimlik_ad="test",
                        kimlik_eposta="test@pruvo",
                        ayarlar=["-c", "core.hooksPath=/dev/null"],
                        capture_output=True, text=True)


def _tavanlar():
    import importlib.util as ilu
    spec = ilu.spec_from_file_location("defter_kota_taban_test", TABAN)
    mod = ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.TAVAN_SATIR, mod.TAVAN_BAYT


TAVAN_SATIR, TAVAN_BAYT = _tavanlar()


def _defter_metni(asan):
    """Tavani ASAN ya da ALTINDA kalan sentetik defter uret."""
    if asan:
        return ("x" * 60 + "\n") * (TAVAN_SATIR + 20)
    return ("y" * 10 + "\n") * 20


def _depo_kur(kok, defter_asan=None, defter_stage_de=False):
    """Gecici git deposu kur.

    defter_asan None ise DEVAM.md HIC olusturulmaz (V3: blob yok).
    defter_stage_de True ise defter DEGISTIRILIP `git add` edilir (K1/K2).
    """
    _git(kok, "init", "-q")
    with open(os.path.join(kok, "README.md"), "w", encoding="utf-8") as f:
        f.write("temel dosya\n")
    _git(kok, "add", "README.md")
    if defter_asan is not None:
        yol = os.path.join(kok, "DEVAM.md")
        with open(yol, "w", encoding="utf-8") as f:
            f.write(_defter_metni(defter_asan))
        _git(kok, "add", "DEVAM.md")
    _git(kok, "commit", "-q", "-m", "temel")
    if defter_asan is not None and defter_stage_de:
        # commit SONRASI degistir + stage'le -> diff --cached'de gorunur
        yol = os.path.join(kok, "DEVAM.md")
        with open(yol, "a", encoding="utf-8") as f:
            f.write("# stage edilmis degisiklik\n")
        _git(kok, "add", "DEVAM.md")


def _kapi_kos(kapi_yolu, kok, sayac_yolu):
    env = os.environ.copy()
    env["PRUVO_DEFTER_KOTA_SAYAC"] = sayac_yolu
    return subprocess.run([sys.executable, kapi_yolu, kok],
                          capture_output=True, text=True, env=env)


def _mutant_kapi(kok_dizin, capa, yeni):
    """Kapinin MUTANT kopyasini (taban ile birlikte) gecici dizine ser."""
    with open(KAPI, "r", encoding="utf-8") as f:
        kaynak = f.read()
    if kaynak.count(capa) != 1:
        raise AssertionError("mutasyon capasi BENZERSIZ degil (%d kez): %r"
                             % (kaynak.count(capa), capa[:60]))
    hedef = os.path.join(kok_dizin, "defter-kota-kapisi.py")
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(kaynak.replace(capa, yeni))
    # 28 AGU: kapinin TEK KAYNAKLARI yaninda olmali. `serbest_cagrilar.py` CARE
    # satirlarini besliyor; kopyalanmazsa mutant import'ta COKER ve cokme "hedefini
    # vurdu" diye okunur — olculdu: HEDEF_KOL_ATFI 4/4 -> 0/4
    # ([[capa-cokmesi-arkasindaki-capalari-gizler]]).
    for _yan in (TABAN, SERBEST):
        shutil.copy2(_yan, os.path.join(kok_dizin, os.path.basename(_yan)))
    return hedef


# --- VAKALAR: her biri (ad, kurulum, hukum) ------------------------------
def _v1(kapi_yolu):
    kok = tempfile.mkdtemp(prefix="k195b-v1-")
    sayac = os.path.join(kok, "sayac.tsv")
    try:
        _depo_kur(kok, defter_asan=False)
        r = _kapi_kos(kapi_yolu, kok, sayac)
        iyi = (r.returncode == 0 and "KAPSAM_DISI_OLCULDU" in r.stdout
               and "ASIM=YOK" in r.stdout)
        return iyi, "rc=%d stdout=%r" % (r.returncode, r.stdout.strip()[:100])
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def _v2(kapi_yolu):
    kok = tempfile.mkdtemp(prefix="k195b-v2-")
    sayac = os.path.join(kok, "sayac.tsv")
    try:
        _depo_kur(kok, defter_asan=True)
        r = _kapi_kos(kapi_yolu, kok, sayac)
        sayac_var = os.path.exists(sayac)
        sayac_icerik = ""
        if sayac_var:
            with open(sayac, "r", encoding="utf-8") as f:
                sayac_icerik = f.read()
        iyi = (r.returncode == 0 and "KAPSAM_DISI_ASIM" in r.stderr
               and "KAPSAM_DISI_ASIM" in sayac_icerik)
        return iyi, ("rc=%d stderr_asim=%s sayac_asim=%s"
                     % (r.returncode, "KAPSAM_DISI_ASIM" in r.stderr,
                        "KAPSAM_DISI_ASIM" in sayac_icerik))
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def _v3(kapi_yolu):
    kok = tempfile.mkdtemp(prefix="k195b-v3-")
    sayac = os.path.join(kok, "sayac.tsv")
    try:
        _depo_kur(kok, defter_asan=None)  # DEVAM.md HIC yok
        r = _kapi_kos(kapi_yolu, kok, sayac)
        iyi = (r.returncode == 0 and "KAPSAM_DISI_OLCULEMEDI" in r.stderr
               and "SEBEP" in r.stderr)
        return iyi, "rc=%d stderr=%r" % (r.returncode, r.stderr.strip()[:100])
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def _k1(kapi_yolu):
    """KONTROL: stage ICI + asim -> BLOKLAR (semantik degismedi)."""
    kok = tempfile.mkdtemp(prefix="k195b-k1-")
    sayac = os.path.join(kok, "sayac.tsv")
    try:
        _depo_kur(kok, defter_asan=True, defter_stage_de=True)
        r = _kapi_kos(kapi_yolu, kok, sayac)
        iyi = (r.returncode == 1 and "DEFTER KOTASI ASILDI" in r.stderr
               and "KAPSAM_DISI" not in r.stderr and "KAPSAM_DISI" not in r.stdout)
        return iyi, "rc=%d asildi=%s" % (r.returncode,
                                          "DEFTER KOTASI ASILDI" in r.stderr)
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def _k2(kapi_yolu):
    """KONTROL: stage ICI + tavan alti -> sessiz yesil, KAPSAM_DISI cikmaz."""
    kok = tempfile.mkdtemp(prefix="k195b-k2-")
    sayac = os.path.join(kok, "sayac.tsv")
    try:
        _depo_kur(kok, defter_asan=False, defter_stage_de=True)
        r = _kapi_kos(kapi_yolu, kok, sayac)
        iyi = (r.returncode == 0 and "KAPSAM_DISI" not in r.stdout
               and "KAPSAM_DISI" not in r.stderr)
        return iyi, "rc=%d kapsam_disi_cikti=%s" % (
            r.returncode, "KAPSAM_DISI" in (r.stdout + r.stderr))
    finally:
        shutil.rmtree(kok, ignore_errors=True)


VAKALAR = [("V1 stage-disi tavan-alti", _v1),
           ("V2 stage-disi tavan-ustu", _v2),
           ("V3 defter izlenmiyor", _v3),
           ("K1 KONTROL stage-ici asim BLOKLAR", _k1),
           ("K2 KONTROL stage-ici temiz", _k2)]

# (ad, capa, yeni, HEDEF vaka adlari) — mutant YALNIZ hedeflerini oldurmeli
MUTANTLAR = [
    ("M1 kol eski haline doner (ciplak return 0)", CAPA_M1, "        return 0",
     {"V1 stage-disi tavan-alti", "V2 stage-disi tavan-ustu", "V3 defter izlenmiyor"}),
    ("M2 sayac yazimi kaldirilir", CAPA_M2, "        pass",
     {"V2 stage-disi tavan-ustu"}),
    ("M3 asim kolu BLOKLAR", CAPA_M3,
     ('              % (satir, bayt, TAVAN_SATIR, TAVAN_BAYT, eksen, SAYAC_YOLU),\n'
      '              file=sys.stderr)\n'
      '        return 1'),
     {"V2 stage-disi tavan-ustu"}),
    ("M4 OLCULEMEDI kolu sessizlesir", CAPA_M4, "        pass",
     {"V3 defter izlenmiyor"}),
]


def main():
    print("TAVAN_SATIR=%d TAVAN_BAYT=%d" % (TAVAN_SATIR, TAVAN_BAYT))
    print("KAPI = %s" % KAPI)
    print()
    print("--- VAKALAR (gercek kapi) ---")
    vaka_sonuc = {}
    for ad, fn in VAKALAR:
        iyi, detay = fn(KAPI)
        vaka_sonuc[ad] = iyi
        print("  %-38s %-8s %s" % (ad, "YESIL" if iyi else "KIRMIZI", detay))
    vaka_gecen = sum(1 for v in vaka_sonuc.values() if v)

    print()
    print("--- MUTANTLAR (hedef kol atfi: K182) ---")
    mutant_olen = 0
    atif_dogru = 0
    for ad, capa, yeni, hedefler in MUTANTLAR:
        kok = tempfile.mkdtemp(prefix="k195b-mut-")
        try:
            mutant = _mutant_kapi(kok, capa, yeni)
            olenler = set()
            yasayanlar = set()
            for vad, fn in VAKALAR:
                iyi, _ = fn(mutant)
                (yasayanlar if iyi else olenler).add(vad)
        finally:
            shutil.rmtree(kok, ignore_errors=True)
        oldu = bool(olenler)
        # HEDEF KOL ATFI: olen kume, hedef kumeyle BIREBIR ayni olmali.
        atif = (olenler == hedefler)
        if oldu:
            mutant_olen += 1
        if atif:
            atif_dogru += 1
        print("  %-44s %s" % (ad, "OLDU" if oldu else "YASADI"))
        print("      olen  : %s" % (sorted(olenler) or "-"))
        print("      hedef : %s" % sorted(hedefler))
        print("      ATIF  : %s" % ("DOGRU (olen == hedef)" if atif
                                     else "YANLIS (olen != hedef)"))

    dusen = ((len(VAKALAR) - vaka_gecen) + (len(MUTANTLAR) - mutant_olen)
             + (len(MUTANTLAR) - atif_dogru))
    print()
    print("VAKA=%d/%d MUTANT=%d/%d HEDEF_KOL_ATFI=%d/%d DUSEN=%d" % (
        vaka_gecen, len(VAKALAR), mutant_olen, len(MUTANTLAR),
        atif_dogru, len(MUTANTLAR), dusen))
    return 0 if dusen == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
