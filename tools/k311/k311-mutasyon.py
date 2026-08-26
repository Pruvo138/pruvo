#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K311 CURUTUCUSU — UC YUZU AYRI AYRI olduren mutantlar + KONTROL.

[[K182]]: "mutant kirmizi geldi" TEK BASINA kanit DEGILDIR. Her mutantin
HANGI VAKAYI oldurdugu CAPALIDIR; ilgisiz bir vakada oluyorsa (tautoloji /
ad golgesi) kol OLCULMEMISTIR.

  MU-A  uretken BEYAZ LISTESI kalkar (OLCULEMEDI de "uretken")  -> K5
  MU-C  tetik 3. basamagi gozcunun hukmunu TASIMAZ (eski hal)   -> K10b
  MU-B  eskalasyon tuketicisi olur (`return 0`)                 -> L1
  MU-E2E GERCEK `ci-nobeti.sh` + mutasyonlu tetik dosyasi -> SAHTE YESIL
        (`BITIS rc=0`) GERI GELIR. Bu, in-memory mutantlarin GORMEDIGI
        kabuk kolunu olcer ([[kapinin-menzili-cagri-yeridir]]).
  MU-K0 KONTROL: ilgisiz degisiklik (yorum) -> YESIL KALMALI.

🔴 CANLI DOSYADA MUTASYON YOK: kaynak bellege okunur, mutant bellekte kurulur;
E2E mutanti GECICI dosyaya yazilir ve is bitince SILINIR (disk kurali).

KOSUM: python3 tools/k311/k311-mutasyon.py
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types

CRON = "/Users/okan/.claude/cron"
GOZCU_YOLU = os.path.join(CRON, "gozcu.py")
TETIK_YOLU = os.path.join(CRON, "nobet-tetik.py")
TEST_YOLU = os.path.join(CRON, "nobet-tetik-test.py")
CI_NOBETI = os.path.join(CRON, "ci-nobeti.sh")


# --- mutant tanimlari: (ad, hedef_dosya, capa, yeni, beklenen_ilk_olen) -----

MU_A = (
    "MU-A uretken BEYAZ LISTESI kalkar",
    "gozcu",
    'URETKEN_KOSUM_HUKUMLERI = ("TEMIZ", "ONARIM_DENENDI")',
    'URETKEN_KOSUM_HUKUMLERI = ("TEMIZ", "ONARIM_DENENDI", "MOTOR_DUSTU", "OLCULEMEDI")',
    "K5",
)

# 🔴 CAPA, KURULU KOPYADAN alinir — kurucunun metninden DEGIL. Ilk kosumda
# tam bu sapti: kurucu metni degisti, capa eskide kaldi, mutant CAPA_TUTMADI
# ile SESSIZCE olculmedi ([[emir-canliligi-kurulu-kopyadan-olculur]]).
# YALNIZ uretkenlik kolu kaldirilir; eskalasyon kolu (MU-B'nin ekseni)
# DOKUNULMADAN kalir ki iki mutant birbirinin golgesinde olmesin.
MU_C = (
    "MU-C tetik 3. basamak hukmu TASIMAZ (eski hal)",
    "tetik",
    '''        uretken, uret_sebep = _uretken_karari(kalp)
        if not uretken:
            return Karar("ACMA", "GOZCU_URETMEDI_%s" % uret_sebep, "", (), True)''',
    '''        uretken, uret_sebep = _uretken_karari(kalp)''',
    "K10b",
)

MU_B = (
    "MU-B eskalasyon TUKETICISI olur",
    "gozcu",
    '''    acik = 0
    for run_id, kayit in kosumlar.items():
        if str(run_id) in canli and (kayit or {}).get("durum") == "ESKALASYON":
            acik += 1
    return acik''',
    '''    acik = 0
    return acik''',
    "L1",
)

MU_K0 = (
    "MU-K0 KONTROL (ilgisiz yorum degisikligi)",
    "gozcu",
    '# --- K311-URETKEN-HUKUM (26 Agu 2026) ---------------------------------'
    '-----',
    '# --- K311-URETKEN-HUKUM (KONTROL MUTANTI, davranis DEGISMEZ) ----------'
    '-----',
    None,
)

MUTANTLAR = [MU_A, MU_C, MU_B, MU_K0]


def oku(yol):
    with open(yol, encoding="utf-8") as dosya:
        return dosya.read()


def _bellekte_kur(kaynak, ad, yol):
    if CRON not in sys.path:
        sys.path.insert(0, CRON)
    modul = types.ModuleType(ad)
    modul.__file__ = yol
    onceki = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        exec(compile(kaynak, yol, "exec"), modul.__dict__)
    finally:
        sys.dont_write_bytecode = onceki
    return modul


def _test_modulu():
    spec = importlib.util.spec_from_file_location("nobet_tetik_test", TEST_YOLU)
    modul = importlib.util.module_from_spec(spec)
    onceki = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(modul)
    finally:
        sys.dont_write_bytecode = onceki
    return modul


def _nt_kur(gozcu_kaynak, tetik_kaynak, sira):
    """Tetik modulunu kurar ve GZ'yi (mutasyonlu olabilen) gozcuyle DEGISTIRIR."""
    gz = _bellekte_kur(gozcu_kaynak, "k311_gozcu_%s" % sira, GOZCU_YOLU)
    nt = _bellekte_kur(tetik_kaynak, "k311_tetik_%s" % sira, TETIK_YOLU)
    nt.GZ = gz
    return nt


def _ilk_hata_vakasi(sonuc):
    if not sonuc.hatalar:
        return "?"
    return sonuc.hatalar[0].split(":", 1)[0].split()[0]


def _pycache_temizle():
    yol = os.path.join(CRON, "__pycache__")
    if os.path.isdir(yol):
        shutil.rmtree(yol, ignore_errors=True)


# ---------------------------------------------------------------------------
# E2E mutanti: GERCEK ci-nobeti.sh + gecici mutasyonlu tetik
# ---------------------------------------------------------------------------

def e2e_kos(tetik_kaynak, kosum_hukmu):
    """GERCEK kabugu kosar; doner: (rc, log_metni). Canli dosyaya DOKUNMAZ.

    🔴 Tetik dosyasi CRON DIZININE yazilir, tempdir'e DEGIL: `nobet-tetik.py`
    `CRON_KOKU`yu `__file__`den turetir ve gozcuyu ORADAN yukler. Tempdir'den
    kosunca `GZ=None` kalir, kapi `GOZCU_YUKLENEMEDI` fail-closed koluna duser
    ve "rc!=0" gorunur — YANLIS SEBEPLE YESIL. Bu tam olarak
    [[sahte-bagimlilik-sekli-negatif-blogu-kutsar]] vakasidir; olculdu ve
    duzeltildi (26 Agu, ilk E2E kosumu). Dosya `finally`de SILINIR.
    """
    import json
    kok = tempfile.mkdtemp(prefix="k311-e2e-")
    tetik = os.path.join(CRON, ".k311-e2e-tetik-%d.py" % os.getpid())
    try:
        with open(tetik, "w", encoding="utf-8") as d:
            d.write(tetik_kaynak)
        kapi = os.path.join(kok, "sahte-kapi.py")
        with open(kapi, "w", encoding="utf-8") as d:
            d.write("import sys\nsys.exit(0)\n")
        kalp_y = os.path.join(kok, "kalp.json")
        kilit_y = os.path.join(kok, "kilit")
        os.makedirs(kilit_y, exist_ok=True)
        log_y = os.path.join(kok, "ci.log")
        simdi = time.time()
        kalp = {
            "damga": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(simdi)),
            "epok": simdi, "tetik": "CI_KIRMIZI", "llm_turu": True,
            "yeni_kirmizi": 1, "kirmizi_toplam": 1, "hedef_run": "E2E-1",
            "dagitilabilir": 0, "kat_mimar": 0, "kat_okan": 0, "kat_isci": 0,
            "gunluk_gerekli": False, "artik_silinen": 0, "taban_alinan": 0,
            "ci_olculdu": True, "ci_sebep": "TAMAM", "defter_olculdu": True,
            "icra_rc": 0, "icra_hal": "KOSTU_BASARILI", "icra_denendi": True,
            "kosum_hukmu": kosum_hukmu, "rc": 0, "kuru": False,
        }
        with open(kalp_y, "w", encoding="utf-8") as d:
            json.dump(kalp, d)
        ortam = dict(os.environ)
        ortam.update({
            "PRUVO_NOBET_KOK": CRON, "PRUVO_NOBET_LOG": log_y,
            "PRUVO_NOBET_EV": kok, "PRUVO_NOBET_KAPI": kapi,
            "PRUVO_NOBET_TETIK": tetik,
            "PRUVO_TETIK_KALP": kalp_y, "PRUVO_TETIK_KILIT": kilit_y,
            "PRUVO_TETIK_GOZCU_LOG": os.path.join(kok, "gozcu-cron.log"),
        })
        sonuc = subprocess.run([CI_NOBETI], env=ortam, cwd=kok,
                               capture_output=True, text=True, timeout=180)
        metin = ""
        if os.path.exists(log_y):
            with open(log_y, encoding="utf-8") as d:
                metin = d.read()
        return sonuc.returncode, metin
    finally:
        shutil.rmtree(kok, ignore_errors=True)
        try:                       # ureten temizler (disk kurali)
            os.unlink(tetik)
        except OSError:
            pass


def main():
    gozcu_asil = oku(GOZCU_YOLU)
    tetik_asil = oku(TETIK_YOLU)
    test = _test_modulu()

    # --- KONTROL: mutasyonsuz hat YESIL mi? ---
    kontrol = test.kos(_nt_kur(gozcu_asil, tetik_asil, "kontrol"))
    if kontrol.gecen != kontrol.toplam:
        for h in kontrol.hatalar:
            print("KONTROL KIRIK " + h)
        print("KONTROL=KIRMIZI GECEN=%d/%d" % (kontrol.gecen, kontrol.toplam))
        _pycache_temizle()
        return 2
    print("KONTROL=YESIL GECEN=%d/%d" % (kontrol.gecen, kontrol.toplam))

    sayac = {"OLDU": 0, "HAYATTA": 0, "ISTISNA": 0, "ATIF_SAPTI": 0,
             "CAPA_TUTMADI": 0, "KONTROL_KIRILDI": 0}
    eslesme = {}

    for sira, (ad, dosya, capa, yeni, beklenen) in enumerate(MUTANTLAR, 1):
        kaynak = gozcu_asil if dosya == "gozcu" else tetik_asil
        adet = kaynak.count(capa)
        if adet != 1:
            print("%-48s CAPA_TUTMADI (kaynakta %d kez)" % (ad, adet))
            sayac["CAPA_TUTMADI"] += 1
            continue
        mut = kaynak.replace(capa, yeni, 1)
        g_kaynak = mut if dosya == "gozcu" else gozcu_asil
        t_kaynak = mut if dosya == "tetik" else tetik_asil
        try:
            sonuc = test.kos(_nt_kur(g_kaynak, t_kaynak, sira))
        except BaseException as hata:
            sayac["ISTISNA"] += 1
            print("%-48s OLDU ISTISNA=%s (KOL OLCULMEDI)" % (ad, type(hata).__name__))
            continue

        if beklenen is None:                       # KONTROL mutanti
            if sonuc.gecen == sonuc.toplam:
                print("%-48s YESIL KALDI GECEN=%d/%d ✓"
                      % (ad, sonuc.gecen, sonuc.toplam))
            else:
                sayac["KONTROL_KIRILDI"] += 1
                print("%-48s 🔴 KONTROL KIRILDI vaka=%s (batarya AMBIYANS olcuyor)"
                      % (ad, _ilk_hata_vakasi(sonuc)))
            continue

        if sonuc.gecen == sonuc.toplam:
            sayac["HAYATTA"] += 1
            print("%-48s 🔴 HAYATTA GECEN=%d/%d (KOL OLCULMUYOR)"
                  % (ad, sonuc.gecen, sonuc.toplam))
            continue
        vaka = _ilk_hata_vakasi(sonuc)
        eslesme[ad.split()[0]] = vaka
        sayac["OLDU"] += 1
        if vaka != beklenen:
            sayac["ATIF_SAPTI"] += 1
            print("%-48s OLDU ama ATIF SAPTI vaka=%s beklenen=%s"
                  % (ad, vaka, beklenen))
        else:
            print("%-48s OLDU vaka=%s (dusen=%d)"
                  % (ad, vaka, sonuc.toplam - sonuc.gecen))

    # --- MU-E2E: kabuk kolu ------------------------------------------------
    print("")
    print("--- MU-E2E: GERCEK ci-nobeti.sh (in-memory mutantlarin GORMEDIGI kol) ---")
    rc_asil, log_asil = e2e_kos(tetik_asil, "OLCULEMEDI")
    rc_yesil, log_yesil = e2e_kos(tetik_asil, "TEMIZ")
    capa_c = MU_C[2]
    e2e_ok = True
    if tetik_asil.count(capa_c) != 1:
        print("MU-E2E CAPA_TUTMADI")
        e2e_ok = False
        rc_mut, log_mut = None, ""
    else:
        rc_mut, log_mut = e2e_kos(tetik_asil.replace(capa_c, MU_C[3], 1), "OLCULEMEDI")

    print("E2E ASIL   uretmeyen  rc=%s  BITIS_rc=0_sayisi=%d"
          % (rc_asil, log_asil.count("BITIS rc=0")))
    print("E2E ASIL   ureten     rc=%s  BITIS_rc=0_sayisi=%d"
          % (rc_yesil, log_yesil.count("BITIS rc=0")))
    print("E2E MUTANT uretmeyen  rc=%s  BITIS_rc=0_sayisi=%d"
          % (rc_mut, log_mut.count("BITIS rc=0")))

    # 🔴 SEBEP DOGRULAMASI: "rc!=0" TEK BASINA kanit degildir. Kapi yanlis
    # sebeple (gozcu yuklenemedi / kalp bayat) da kirmizi yanabilir; o hal
    # K311'i DEGIL fail-closed varsayilanini olcer.
    yanlis_sebep = [ad for ad, m in (("ASIL-uretmeyen", log_asil),
                                     ("ASIL-ureten", log_yesil),
                                     ("MUTANT", log_mut))
                    if ("GOZCU YUKLENEMEDI" in m or "KALP BAYAT" in m)]
    e2e_vakalar = [
        ("E2E0 SEBEP DOGRU (yuklenemedi/bayat kolu ATESLENMEDI)", not yanlis_sebep),
        ("E2E1 asil: uretmeyen hat rc!=0", rc_asil not in (0, None)),
        ("E2E2 asil: uretmeyen hatta BITIS rc=0 YOK", log_asil.count("BITIS rc=0") == 0),
        ("E2E2b asil: sebep GOZCU_URETMEDI", "GOZCU_URETMEDI" in log_asil),
        ("E2E3 asil: URETEN hat rc=0 (negatif kontrol)", rc_yesil == 0),
        ("E2E4 asil: ureten hatta BITIS rc=0 VAR", log_yesil.count("BITIS rc=0") == 1),
        ("E2E5 MUTANT: sahte yesil GERI GELIR (rc=0)", rc_mut == 0),
        ("E2E6 MUTANT: BITIS rc=0 geri gelir", log_mut.count("BITIS rc=0") == 1),
    ]
    if yanlis_sebep:
        print("  🔴 YANLIS SEBEP KOLU ATESLENDI: %s" % ", ".join(yanlis_sebep))
    for ad, ok in e2e_vakalar:
        print("  %-46s %s" % (ad, "GECTI" if ok else "🔴 KALDI"))
        if not ok:
            e2e_ok = False

    _pycache_temizle()
    print("")
    print("OLUM_ESLESMESI: " + (" ".join("%s=%s" % (k, v) for k, v in eslesme.items())
                                or "YOK"))
    hedefli = len([m for m in MUTANTLAR if m[4] is not None])
    print("MUTANT=%d/%d ATIF_SAPTI=%d HAYATTA=%d ISTISNA=%d CAPA_TUTMADI=%d "
          "KONTROL_KIRILDI=%d E2E=%s"
          % (sayac["OLDU"], hedefli, sayac["ATIF_SAPTI"], sayac["HAYATTA"],
             sayac["ISTISNA"], sayac["CAPA_TUTMADI"], sayac["KONTROL_KIRILDI"],
             "YESIL" if e2e_ok else "KIRMIZI"))
    kapi = (sayac["OLDU"] == hedefli and sayac["ATIF_SAPTI"] == 0
            and sayac["HAYATTA"] == 0 and sayac["ISTISNA"] == 0
            and sayac["CAPA_TUTMADI"] == 0 and sayac["KONTROL_KIRILDI"] == 0
            and e2e_ok)
    print("K311_MUTASYON=%s" % ("GECTI" if kapi else "KALDI"))
    return 0 if kapi else 1


if __name__ == "__main__":
    sys.exit(main())
