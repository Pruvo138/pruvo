#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K253 KABUL TESTI — defter-kota-kapisi.py KUTU (ortak posta kutusu) ekseni.

OLCULEN ARIZA (SINIF, 3. TEKRAR — 20 Agu 2026): ortak posta kutusu
`~/.claude/projects/-Users-okan-dev-pruvo/memory/mimar-posta-kutusu.md` esigi
19 Agu'da ELLE 333 -> 245 satira indirildi, ertesi gun 363'e cikti. Her hafta
ayni el isi. SEBEP: kota kapisi pre-commit'te kosuyor ve YALNIZ DEVAM.md'yi
olcuyordu; kutu repo DISINDA duruyor -> yalniz kutu buyudugunde HICBIR kapi
tetiklenmiyor, tasma ancak insan bakinca goruluyordu.

CARE: tekil budama DEGIL ([[ucuncu-tekrar-sinif-kapisi]]) — AYNI kapi kutuyu da
MUTLAK YOLLA olcer; tavan koda gomulu IKINCI bir sabite YAZILMAZ, mevcut
sahibinden (`tools/kutu-arsivle.py::VARSAYILAN_TAVAN`) TURETILIR.

Bu test GERCEK kapiyi (main()) GERCEK gecici git depolarinda kosar. 🔴 Gercek
kutuya, gercek arsive ve gercek DEVAM.md'ye ASLA dokunulmaz: her vaka kendi
sentetik kutusunu `PRUVO_KUTU_YOLU` ile gosterir, sayaci kendi temp dosyasina
yazar.

VAKALAR (kutu ekseni — BES KOVA + tek kaynak)
  V1 KUTU_ASILDI      tavan USTU kutu   -> rc=1, ciktida dosya adi + satir/bayt
                                           + tavan + CARE komutu BIRLIKTE gecer   [①]
  V2 KUTU_YESIL       tavan ALTI kutu   -> rc=0, yanlis-pozitif YOK               [②]
  V3 KUTU_OLCULEMEDI  hafiza dizini VAR,
                      kutu dosyasi YOK  -> rc=1 (fail-closed), AYRI jeton         [③]
  V4 KUTU_MAKINEDE_YOK hafiza dizini HIC yok -> rc=0 (kosucu; kusur DEGIL)
  V5 KUTU_SAHIPSIZ    <kok>/tools/kutu-arsivle.py YOK -> rc=0 (kardes depo/fikstur)
  V6 TEK_KAYNAK       esik IKINCI bir sabite kopyalanmis -> rc=1                  [⑤]

YAN EKSEN (defter kolu — M1 altinda YASAMALI)
  Y1 defter staged + tavan USTU -> rc=1, "DEFTER KOTASI ASILDI"
  Y2 defter staged + tavan ALTI -> rc=0

MUTANTLAR (K182 hedef-kol atfi: olen kume == hedef kume)
  M1 KUTU KOLU KALDIRILIR      -> V1..V6'dan kutu vakalari olur, Y1+Y2 YASAR      [④]
  M2 TEK KAYNAK NOBETI KALKAR  -> YALNIZ V6 olur
  M3 UCUNCU KOVA YUTULUR       -> YALNIZ V3 olur (OLCULEMEDI, MAKINEDE_YOK'a
                                  dusurulurse fail-closed kaybolur)
  K0 KONTROL: ILGISIZ KOL BOZULUR (bypass sayaci) -> HICBIR vaka olmemeli         [⑥]

MENZIL (⑦ — [[kapinin-menzili-cagri-yeridir]]): `--kendini-test` yesili YETMEZ.
Kapinin GERCEK cagri yeri `tools/kancalar/pre-commit` adim 8'dir; bu test o
dosyayi OKUR ve (a) bayraksiz cagri (b) rc'nin `exit 1` ile YAYILMASI iddialarini
olcer, ayrica iddiayi bir MENZIL MUTANTIYLA sinar (yayilim silinirse KIRMIZI).

Kullanim: python3 tools/kutu-kota-kapisi-test.py
Cikti son satiri:
  VAKA=<n>/<n> MUTANT=<n>/<n> HEDEF_KOL_ATFI=<n>/<n> KONTROL=<n>/<n> MENZIL=<n>/<n> DUSEN=<n>
"""
import importlib.util as ilu
import os
import shutil
import subprocess
import sys
import tempfile

from git_ortami import sentetik_git

sys.dont_write_bytecode = True

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)
KAPI = os.path.join(TOOLS, "defter-kota-kapisi.py")
TABAN = os.path.join(TOOLS, "defter-kota-taban.py")
SAHIP = os.path.join(TOOLS, "kutu-arsivle.py")
PRE_COMMIT = os.path.join(TOOLS, "kancalar", "pre-commit")

# --- mutasyon capalari: kapi kaynagindaki BENZERSIZ dizeler ----------------
CAPA_M1 = "    kutu_rc = kutu_kontrol(kok)"
CAPA_M2 = "    kaynak_rc = tek_kaynak_kontrol(kok)"
CAPA_M3 = ("    if not dizin_var:\n"
           "        return KUTU_MAKINEDE_YOK\n"
           "    if not dosya_var or satir is None or tavan is None:\n"
           "        return KUTU_OLCULEMEDI")
CAPA_K0 = '        _sayaç_yaz(kok, satir, bayt, sinif="BYPASS")'


def _yukle(yol, ad):
    spec = ilu.spec_from_file_location(ad, yol)
    mod = ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_TABAN = _yukle(TABAN, "k253_taban")
_SAHIP = _yukle(SAHIP, "k253_sahip")
TAVAN_SATIR = _TABAN.TAVAN_SATIR
KUTU_TAVAN = _SAHIP.VARSAYILAN_TAVAN


def _git(kok, *args):
    return sentetik_git(kok, *args, kimlik_ad="test", kimlik_eposta="test@pruvo",
                        ayarlar=["-c", "core.hooksPath=/dev/null"],
                        capture_output=True, text=True)


def _kutu_metni(satir):
    """Sentetik kutu — gercek kutu SEKLINDE (frontmatter + `## ` bloklari)."""
    bas = ("---\nname: sentetik-kutu\ndescription: kabul testi fiksturu\n---\n")
    govde = []
    i = 0
    while len(bas.splitlines()) + len(govde) < satir:
        if i % 10 == 0:
            govde.append("## 2026-08-20 — sentetik blok %d\n" % (i // 10))
        else:
            govde.append("satir %d\n" % i)
        i += 1
    return bas + "".join(govde)


def _depo_kur(kok, sahip_ver=True, defter_satir=20, defter_stage_de=False):
    """Sentetik git deposu + <kok>/tools iskeleti."""
    _git(kok, "init", "-q")
    tools = os.path.join(kok, "tools")
    os.makedirs(tools, exist_ok=True)
    shutil.copy2(KAPI, os.path.join(tools, "defter-kota-kapisi.py"))
    shutil.copy2(TABAN, os.path.join(tools, "defter-kota-taban.py"))
    if sahip_ver:
        shutil.copy2(SAHIP, os.path.join(tools, "kutu-arsivle.py"))
    with open(os.path.join(kok, "README.md"), "w", encoding="utf-8") as f:
        f.write("temel dosya\n")
    with open(os.path.join(kok, "DEVAM.md"), "w", encoding="utf-8") as f:
        f.write(("d" * 10 + "\n") * defter_satir)
    _git(kok, "add", "README.md", "DEVAM.md", "tools")
    _git(kok, "commit", "-q", "-m", "temel")
    if defter_stage_de:
        with open(os.path.join(kok, "DEVAM.md"), "a", encoding="utf-8") as f:
            f.write("# stage edilmis degisiklik\n")
        _git(kok, "add", "DEVAM.md")
    return os.path.join(tools, "defter-kota-kapisi.py")


def _kos(kapi_yolu, kok, kutu_yolu, sayac):
    env = os.environ.copy()
    env["PRUVO_DEFTER_KOTA_SAYAC"] = sayac
    if kutu_yolu is None:
        env.pop("PRUVO_KUTU_YOLU", None)
    else:
        env["PRUVO_KUTU_YOLU"] = kutu_yolu
    return subprocess.run([sys.executable, kapi_yolu, kok],
                          capture_output=True, text=True, env=env)


def _vaka(kur, hukum):
    """Ortak iskele: temp kok + temp hafiza dizini kurar, hukmu uygular."""
    def _calistir(kapi_yolu_ustu):
        ust = tempfile.mkdtemp(prefix="k253-")
        try:
            kok = os.path.join(ust, "depo")
            os.makedirs(kok)
            hafiza = os.path.join(ust, "hafiza")
            sayac = os.path.join(ust, "sayac.tsv")
            yerel_kapi = kur(kok, hafiza)
            kapi = kapi_yolu_ustu or yerel_kapi["kapi"]
            r = _kos(kapi, kok, yerel_kapi["kutu"], sayac)
            return hukum(r, yerel_kapi)
        finally:
            shutil.rmtree(ust, ignore_errors=True)
    return _calistir


# --------------------------------------------------------------- V1 KUTU_ASILDI
def _kur_asildi(kok, hafiza):
    kapi = _depo_kur(kok)
    os.makedirs(hafiza, exist_ok=True)
    kutu = os.path.join(hafiza, "mimar-posta-kutusu.md")
    metin = _kutu_metni(KUTU_TAVAN + 40)
    with open(kutu, "w", encoding="utf-8") as f:
        f.write(metin)
    return {"kapi": kapi, "kutu": kutu, "satir": len(metin.splitlines()),
            "bayt": len(metin.encode("utf-8"))}


def _hukum_asildi(r, f):
    """① rc!=0 + dosya adi + olculen satir/bayt + tavan + CARE komutu BIRLIKTE."""
    c = r.stdout + r.stderr
    iyi = (r.returncode != 0
           and "KUTU_ASILDI" in c
           and os.path.basename(f["kutu"]) in c
           and ("%d satir" % f["satir"]) in c
           and ("%d bayt" % f["bayt"]) in c
           and ("tavan satir=%d" % KUTU_TAVAN) in c
           and "CARE:" in c
           and "kutu-arsivle.py" in c)
    return iyi, ("rc=%d jeton=%s dosya=%s satir=%s bayt=%s tavan=%s care=%s"
                 % (r.returncode, "KUTU_ASILDI" in c,
                    os.path.basename(f["kutu"]) in c,
                    ("%d satir" % f["satir"]) in c,
                    ("%d bayt" % f["bayt"]) in c,
                    ("tavan satir=%d" % KUTU_TAVAN) in c, "CARE:" in c))


# ---------------------------------------------------------------- V2 KUTU_YESIL
def _kur_yesil(kok, hafiza):
    kapi = _depo_kur(kok)
    os.makedirs(hafiza, exist_ok=True)
    kutu = os.path.join(hafiza, "mimar-posta-kutusu.md")
    metin = _kutu_metni(max(10, KUTU_TAVAN - 40))
    with open(kutu, "w", encoding="utf-8") as f:
        f.write(metin)
    return {"kapi": kapi, "kutu": kutu}


def _hukum_yesil(r, f):
    """② yanlis-pozitif YOK: tavan altinda kapi YESIL."""
    c = r.stdout + r.stderr
    iyi = (r.returncode == 0 and "KUTU_YESIL" in c and "KUTU_ASILDI" not in c)
    return iyi, "rc=%d yesil=%s asildi=%s" % (r.returncode, "KUTU_YESIL" in c,
                                              "KUTU_ASILDI" in c)


# ----------------------------------------------------------- V3 KUTU_OLCULEMEDI
def _kur_olculemedi(kok, hafiza):
    kapi = _depo_kur(kok)
    os.makedirs(hafiza, exist_ok=True)          # DIZIN VAR
    kutu = os.path.join(hafiza, "mimar-posta-kutusu.md")   # DOSYA YOK
    return {"kapi": kapi, "kutu": kutu}


def _hukum_olculemedi(r, f):
    """③ dosya HIC yoksa YESIL degil OLCULEMEDI + sifir-disi rc (fail-closed)."""
    c = r.stdout + r.stderr
    iyi = (r.returncode != 0 and "KUTU_OLCULEMEDI" in c
           and "KUTU_YESIL" not in c and "KUTU_MAKINEDE_YOK" not in c)
    return iyi, ("rc=%d olculemedi=%s yesil=%s makinede_yok=%s"
                 % (r.returncode, "KUTU_OLCULEMEDI" in c, "KUTU_YESIL" in c,
                    "KUTU_MAKINEDE_YOK" in c))


# ------------------------------------------------------- V4 KUTU_MAKINEDE_YOK
def _kur_makinede_yok(kok, hafiza):
    kapi = _depo_kur(kok)
    # hafiza dizini OLUSTURULMAZ -> kosucu/kardes makine kovasi
    kutu = os.path.join(hafiza, "mimar-posta-kutusu.md")
    return {"kapi": kapi, "kutu": kutu}


def _hukum_makinede_yok(r, f):
    c = r.stdout + r.stderr
    iyi = (r.returncode == 0 and "KUTU_MAKINEDE_YOK" in c
           and "KUTU_OLCULEMEDI" not in c)
    return iyi, "rc=%d makinede_yok=%s olculemedi=%s" % (
        r.returncode, "KUTU_MAKINEDE_YOK" in c, "KUTU_OLCULEMEDI" in c)


# ----------------------------------------------------------- V5 KUTU_SAHIPSIZ
def _kur_sahipsiz(kok, hafiza):
    kapi = _depo_kur(kok, sahip_ver=False)
    os.makedirs(hafiza, exist_ok=True)
    kutu = os.path.join(hafiza, "mimar-posta-kutusu.md")
    with open(kutu, "w", encoding="utf-8") as f:
        f.write(_kutu_metni(KUTU_TAVAN + 40))   # ASAN kutu — ama sahip YOK
    return {"kapi": kapi, "kutu": kutu}


def _hukum_sahipsiz(r, f):
    """Sahiplenmeyen checkout ASAN kutu yuzunden kirmiziya YANMAZ (ambiyans yok)."""
    c = r.stdout + r.stderr
    iyi = (r.returncode == 0 and "KUTU_SAHIPSIZ" in c and "KUTU_ASILDI" not in c)
    return iyi, "rc=%d sahipsiz=%s asildi=%s" % (r.returncode,
                                                 "KUTU_SAHIPSIZ" in c,
                                                 "KUTU_ASILDI" in c)


# ------------------------------------------------------------ V6 TEK_KAYNAK (⑤)
def _kur_tek_kaynak(kok, hafiza):
    kapi = _depo_kur(kok)
    os.makedirs(hafiza, exist_ok=True)
    kutu = os.path.join(hafiza, "mimar-posta-kutusu.md")
    with open(kutu, "w", encoding="utf-8") as f:
        f.write(_kutu_metni(max(10, KUTU_TAVAN - 40)))   # kutu TEMIZ
    # ESIK IKINCI BIR SABITE KOPYALANIR (tek kaynak BOZULUR).
    with open(kapi, "a", encoding="utf-8") as f:
        f.write("\n\nKUTU_TAVAN_KOPYASI = %d\n" % KUTU_TAVAN)
    return {"kapi": kapi, "kutu": kutu}


def _hukum_tek_kaynak(r, f):
    c = r.stdout + r.stderr
    iyi = (r.returncode != 0 and "TEK_KAYNAK_IHLALI" in c
           and "KUTU_TAVAN_KOPYASI" in c)
    return iyi, "rc=%d ihlal=%s ad=%s" % (r.returncode, "TEK_KAYNAK_IHLALI" in c,
                                          "KUTU_TAVAN_KOPYASI" in c)


# ------------------------------------------------- YAN EKSEN (defter kolu) Y1/Y2
def _kur_defter_asan(kok, hafiza):
    kapi = _depo_kur(kok, sahip_ver=False, defter_satir=TAVAN_SATIR + 20,
                     defter_stage_de=True)
    return {"kapi": kapi, "kutu": None}


def _hukum_defter_asan(r, f):
    iyi = (r.returncode == 1 and "DEFTER KOTASI ASILDI" in r.stderr)
    return iyi, "rc=%d defter_asildi=%s" % (r.returncode,
                                            "DEFTER KOTASI ASILDI" in r.stderr)


def _kur_defter_temiz(kok, hafiza):
    kapi = _depo_kur(kok, sahip_ver=False, defter_satir=20, defter_stage_de=True)
    return {"kapi": kapi, "kutu": None}


def _hukum_defter_temiz(r, f):
    c = r.stdout + r.stderr
    iyi = (r.returncode == 0 and "DEFTER KOTASI ASILDI" not in c)
    return iyi, "rc=%d" % r.returncode


VAKALAR = [
    ("V1 KUTU_ASILDI (care+sayi)", _vaka(_kur_asildi, _hukum_asildi)),
    ("V2 KUTU_YESIL (yanlis-pozitif yok)", _vaka(_kur_yesil, _hukum_yesil)),
    ("V3 KUTU_OLCULEMEDI (fail-closed)", _vaka(_kur_olculemedi, _hukum_olculemedi)),
    ("V4 KUTU_MAKINEDE_YOK (kosucu)", _vaka(_kur_makinede_yok, _hukum_makinede_yok)),
    ("V5 KUTU_SAHIPSIZ (kardes depo)", _vaka(_kur_sahipsiz, _hukum_sahipsiz)),
    ("V6 TEK_KAYNAK ihlali yakalanir", _vaka(_kur_tek_kaynak, _hukum_tek_kaynak)),
    ("Y1 YAN defter asimi BLOKLAR", _vaka(_kur_defter_asan, _hukum_defter_asan)),
    ("Y2 YAN defter temiz GECER", _vaka(_kur_defter_temiz, _hukum_defter_temiz)),
]

KUTU_VAKALARI = {"V1 KUTU_ASILDI (care+sayi)", "V2 KUTU_YESIL (yanlis-pozitif yok)",
                 "V3 KUTU_OLCULEMEDI (fail-closed)", "V4 KUTU_MAKINEDE_YOK (kosucu)",
                 "V5 KUTU_SAHIPSIZ (kardes depo)"}

MUTANTLAR = [
    ("M1 KUTU KOLU KALDIRILIR", CAPA_M1, "    kutu_rc = 0", KUTU_VAKALARI),
    ("M2 TEK KAYNAK NOBETI KALKAR", CAPA_M2, "    kaynak_rc = 0",
     {"V6 TEK_KAYNAK ihlali yakalanir"}),
    ("M3 UCUNCU KOVA YUTULUR", CAPA_M3,
     ("    if not dizin_var or not dosya_var or satir is None or tavan is None:\n"
      "        return KUTU_MAKINEDE_YOK"),
     {"V3 KUTU_OLCULEMEDI (fail-closed)"}),
]

KONTROLLER = [
    ("K0 ILGISIZ KOL BOZULUR (bypass sayaci)", CAPA_K0, "        pass"),
]


def _mutant_kapi_uret(dizin, capa, yeni):
    """Kapinin MUTANT kopyasini uretir; capa BENZERSIZ olmali."""
    with open(KAPI, "r", encoding="utf-8") as f:
        kaynak = f.read()
    if kaynak.count(capa) != 1:
        raise AssertionError("mutasyon capasi BENZERSIZ degil (%d kez): %r"
                             % (kaynak.count(capa), capa[:70]))
    yol = os.path.join(dizin, "defter-kota-kapisi.py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kaynak.replace(capa, yeni))
    return yol


def _vakalari_kos(mutant_kaynak=None):
    """Tum vakalari kos; mutant_kaynak verilirse kapi onunla DEGISTIRILIR."""
    olen, yasayan = set(), set()
    for ad, fn in VAKALAR:
        if mutant_kaynak is None:
            iyi, _ = fn(None)
        else:
            iyi, _ = _mutantla_kos(fn, mutant_kaynak)
        (yasayan if iyi else olen).add(ad)
    return olen, yasayan


def _mutantla_kos(fn, mutant_kaynak):
    """Vakayi, <kok>/tools/defter-kota-kapisi.py MUTANT kopya ile kosar."""
    global _MUTANT_KAYNAK
    onceki = _MUTANT_KAYNAK
    _MUTANT_KAYNAK = mutant_kaynak
    try:
        return fn(None)
    finally:
        _MUTANT_KAYNAK = onceki


_MUTANT_KAYNAK = None
_ORIJINAL_DEPO_KUR = _depo_kur


def _depo_kur_mutantli(kok, **kw):
    kapi = _ORIJINAL_DEPO_KUR(kok, **kw)
    if _MUTANT_KAYNAK is not None:
        shutil.copy2(_MUTANT_KAYNAK, kapi)
    return kapi


_depo_kur = _depo_kur_mutantli


# --------------------------------------------------------------- MENZIL (⑦)
def menzil_hukmu(metin):
    """SAF hukum: pre-commit adim 8 kapiyi BAYRAKSIZ cagiriyor VE rc'yi YAYIYOR mu?

    Iddialar (hepsi saglanmali):
      A) `"$pruvo_defter_kota" "$pruvo_kok"` — bayraksiz, kok argumanli cagri.
      B) cagrinin rc'si bir degiskene alinir (`pruvo_defter_kota_rc=$?`).
      C) rc sifir-disi ise `exit 1` -> hukum COMMIT'e YAYILIR.
    """
    iddialar = []
    cagri = 'python3 "$pruvo_defter_kota" "$pruvo_kok"'
    iddialar.append(("A bayraksiz kok-argumanli cagri", cagri in metin))
    iddialar.append(("B rc yakalanir", "pruvo_defter_kota_rc=$?" in metin))
    yayilim = ('if [ "$pruvo_defter_kota_rc" -ne 0 ]; then\n  exit 1\nfi'
               in metin)
    iddialar.append(("C rc sifir-disi -> exit 1 (yayilim)", yayilim))
    return iddialar


def menzil_olc():
    """(iddialar, mutant_gecti, satir_no) — gercek kanca dosyasindan."""
    try:
        with open(PRE_COMMIT, "r", encoding="utf-8") as f:
            metin = f.read()
    except OSError as e:
        return [("pre-commit okunamadi: %s" % e, False)], False, None
    iddialar = menzil_hukmu(metin)
    # MENZIL MUTANTI: rc yayilimi silinirse iddia C KIRMIZI yanmali. Iddia
    # metinden bagimsiz "hep dogru" olsaydi bu mutant sessizce gecerdi.
    mutant_metin = metin.replace(
        'if [ "$pruvo_defter_kota_rc" -ne 0 ]; then\n  exit 1\nfi',
        'if [ "$pruvo_defter_kota_rc" -ne 0 ]; then\n  :\nfi')
    mutant_iddialar = menzil_hukmu(mutant_metin)
    mutant_gecti = any(not ok for _, ok in mutant_iddialar)
    satir_no = None
    i = 1
    for s in metin.splitlines():
        if 'python3 "$pruvo_defter_kota" "$pruvo_kok"' in s:
            satir_no = i
            break
        i += 1
    return iddialar, mutant_gecti, satir_no


def main():
    print("TAVAN_SATIR=%d (defter)  KUTU_TAVAN=%d (sahip: tools/kutu-arsivle.py::"
          "VARSAYILAN_TAVAN)" % (TAVAN_SATIR, KUTU_TAVAN))
    print("KAPI = %s" % KAPI)
    print()

    print("--- VAKALAR (gercek kapi, sentetik depo+kutu) ---")
    vaka_sonuc = {}
    for ad, fn in VAKALAR:
        iyi, detay = fn(None)
        vaka_sonuc[ad] = iyi
        print("  %-38s %-8s %s" % (ad, "YESIL" if iyi else "KIRMIZI", detay))
    vaka_gecen = sum(1 for v in vaka_sonuc.values() if v)

    print()
    print("--- MUTANTLAR (hedef kol atfi: olen == hedef) ---")
    mutant_olen = 0
    atif_dogru = 0
    for ad, capa, yeni, hedefler in MUTANTLAR:
        dizin = tempfile.mkdtemp(prefix="k253-mut-")
        try:
            kaynak = _mutant_kapi_uret(dizin, capa, yeni)
            olenler, yasayanlar = _vakalari_kos(kaynak)
        finally:
            shutil.rmtree(dizin, ignore_errors=True)
        oldu = bool(olenler)
        atif = (olenler == hedefler)
        if oldu:
            mutant_olen += 1
        if atif:
            atif_dogru += 1
        print("  %-32s %s" % (ad, "OLDU" if oldu else "YASADI"))
        print("      olen  : %s" % (sorted(olenler) or "-"))
        print("      hedef : %s" % sorted(hedefler))
        print("      ATIF  : %s" % ("DOGRU" if atif else "YANLIS (olen != hedef)"))

    print()
    print("--- KONTROL (ilgisiz kol bozulur -> HICBIR iddia olmemeli) ---")
    kontrol_gecen = 0
    for ad, capa, yeni in KONTROLLER:
        dizin = tempfile.mkdtemp(prefix="k253-k0-")
        try:
            kaynak = _mutant_kapi_uret(dizin, capa, yeni)
            olenler, _ = _vakalari_kos(kaynak)
        finally:
            shutil.rmtree(dizin, ignore_errors=True)
        gecti = not olenler
        if gecti:
            kontrol_gecen += 1
        print("  %-42s %s  olen=%s" % (ad, "GECTI" if gecti else "DUSTU",
                                       sorted(olenler) or "-"))

    print()
    print("--- MENZIL (gercek cagri yeri: tools/kancalar/pre-commit) ---")
    iddialar, menzil_mutant, satir_no = menzil_olc()
    for iad, ok in iddialar:
        print("  %-40s %s" % (iad, "VAR" if ok else "YOK"))
    print("  %-40s %s" % ("MENZIL MUTANTI (yayilim silinir)",
                          "YAKALANDI" if menzil_mutant else "KACIRILDI"))
    print("  cagri satiri: tools/kancalar/pre-commit:%s" % (satir_no or "-"))
    menzil_toplam = len(iddialar) + 1
    menzil_gecen = sum(1 for _, ok in iddialar if ok) + (1 if menzil_mutant else 0)

    dusen = ((len(VAKALAR) - vaka_gecen)
             + (len(MUTANTLAR) - mutant_olen)
             + (len(MUTANTLAR) - atif_dogru)
             + (len(KONTROLLER) - kontrol_gecen)
             + (menzil_toplam - menzil_gecen))
    print()
    print("VAKA=%d/%d MUTANT=%d/%d HEDEF_KOL_ATFI=%d/%d KONTROL=%d/%d MENZIL=%d/%d "
          "DUSEN=%d" % (vaka_gecen, len(VAKALAR), mutant_olen, len(MUTANTLAR),
                        atif_dogru, len(MUTANTLAR), kontrol_gecen, len(KONTROLLER),
                        menzil_gecen, menzil_toplam, dusen))
    return 0 if dusen == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
