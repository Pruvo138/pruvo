#!/usr/bin/env python3
"""B6 KABUL BATARYASI — `icra_rc` UC HALI UC DEGERE ayiriyor mu?

PAKET: tools/paket-n4b-onarim-hatti-kalanlar.md, blok B6 (K241 IKINCI yuzeyi).
KANONIK KAYNAK: pruvo deposu `tools/n4b/nobet-icra-hali-test.py`.

KOSUM:  python3 /Users/okan/.claude/cron/nobet-icra-hali-test.py
KABUL:  son satir `KABUL=GECTI (n/n vaka)` ve rc=0.
CAGRI YERI: `testler.py` PAKETLER listesi.

OLCULEN KABUL MADDELERI
  1) kilit BOS + tur kosar + rc=0  -> icra_hal=KOSTU_BASARILI, icra_rc=0   -> H1/H2
  2) kilit BOS + tur kosar + rc!=0 -> icra_hal=KOSTU_DUSTU,   icra_rc!=0   -> H1/H2
  3) kilit DOLU -> icra_hal=ATLANDI ve icra_rc `0` OLMAZ                   -> H1c/H2-A
     🔴 Bugunku (yamasiz) davranis bu vakada `0` veriyordu; test o hali KIRMIZI yakar.
  4) Mutant: ATLANDI yeniden `0`'a eslenirse KIRMIZI; hedef kolun oldugu
     AYRICA kanitlanir, pozitif vaka YESIL kalir (K182)                    -> P1
  5) TUKETICI EKSENI: "ardisik yesil tur" sayan HER yer ATLANDI'yi saymiyor -> H3
     · `gozcu.deneme_sonraki` — ATLANDI turunda HIC CAGRILMAZ (H2-A olcer)
     · `nobet-tetik.karar` — "gozcu icra etti mi" sorusu `icra_denendi`den okunur
     · envanter: `icra_rc`'yi gozcu.py DISINDA okuyan dosya sayisi CIVILI=1
"""

import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import time

CRON_KOKU = "/Users/okan/.claude/cron"
GOZCU = os.path.join(CRON_KOKU, "gozcu.py")
TETIK = os.path.join(CRON_KOKU, "nobet-tetik.py")

SIMDI = 1_755_000_000.0
VAKALAR = []


def vaka(vid, beklenen, olculen):
    gecti = (str(beklenen) == str(olculen))
    VAKALAR.append((vid, beklenen, olculen, gecti))
    print("VAKA=%-36s BEKLENEN=%-26s OLCULEN=%-26s SONUC=%s"
          % (vid, beklenen, olculen, "GECTI" if gecti else "KALDI"))
    return gecti


def modul_yukle(yol, ad):
    if CRON_KOKU not in sys.path:
        sys.path.insert(0, CRON_KOKU)
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ad] = mod
    spec.loader.exec_module(mod)
    return mod


# --- fikstur (gozcu-test.py deseninin bagimsiz kopyasi) --------------------

def _yollar(kok):
    return {"durum": os.path.join(kok, "durum.json"),
            "kalp": os.path.join(kok, "kalp.json"),
            "log": os.path.join(kok, "gozcu.log"),
            "kilit_dizini": os.path.join(kok, "kilit"),
            "eskalasyon": os.path.join(kok, "eskalasyon.md"),
            "artik_dizini": os.path.join(kok, "artik")}


def _kosum(kimlik, conclusion, status="completed", dal="main", ad="ci"):
    return {"databaseId": kimlik, "name": ad, "conclusion": conclusion,
            "status": status, "headBranch": dal, "headSha": "abc123"}


class SahteKosucu(object):
    """Gercek nobet-kapi.py YERINE gecer: rc ve ciktiyi test belirler."""

    def __init__(self, rc=0, cikti="SAHTE_TUR"):
        self.rc = rc
        self.cikti = cikti
        self.cagrilar = []

    def __call__(self, bayraklar):
        self.cagrilar.append(list(bayraklar))
        return (self.rc, self.cikti)


ATLAMA_B8 = ("=== 2026-08-20T09:23:02Z NOBET ATLANDI "
             "HUKUM=ONCEKI_TUR_SURUYOR ATLANAN_ARDISIK=1 ===\n"
             "TUR_HALI=ATLANDI SEBEP=KILIT_DOLU USTUSTE_ONARIMSIZ=120 "
             "SAYAC_YAZILDI=0\n")
ATLAMA_ESKI = ("=== 2026-08-20T09:23:02Z NOBET ATLANDI "
               "HUKUM=ONCEKI_TUR_SURUYOR ATLANAN_ARDISIK=1 ===\n")
TEMIZ = "MOTOR=minimax-m3\nHUKUM=TEMIZ rc=0\n"
DUSEN = "TUR_HALI=KOSTU_DUSTU SEBEP=SURE_TAVANI\nHUKUM=SURE_TAVANI rc=1\n"


# ===========================================================================
# H1 — SAF COZUCU
# ===========================================================================

def bolum_h1(gz, ek=""):
    print("--- BOLUM H1%s: icra_halini_coz (saf) ---" % ek)
    for ad, args, beklenen in (
            ("H1a-kostu-basarili", (True, 0, TEMIZ), ("KOSTU_BASARILI", 0)),
            ("H1b-kostu-dustu", (True, 1, DUSEN), ("KOSTU_DUSTU", 1)),
            ("H1c-atlandi-b8", (True, 0, ATLAMA_B8), ("ATLANDI", None)),
            ("H1d-atlandi-eski-log", (True, 0, ATLAMA_ESKI), ("ATLANDI", None)),
            ("H1e-kosulmadi", (False, None, ""), ("KOSULMADI", None)),
            ("H1f-rc-yok", (True, None, TEMIZ), ("KOSULMADI", None)),
    ):
        try:
            sonuc = gz.icra_halini_coz(*args)
        except Exception as hata:                       # noqa: BLE001
            sonuc = ("HATA:%s" % type(hata).__name__, None)
        vaka("%s%s" % (ad, ek), "%s,%s" % beklenen, "%s,%s" % sonuc)

    # 🔴 ASIL VAKA (09:23Z): atlanan turda icra_rc `0` OLMAMALI.
    _, rc_atlanan = gz.icra_halini_coz(True, 0, ATLAMA_B8)
    vaka("H1g-atlanan-rc-sifir-degil%s" % ek, "0 DEGIL",
         "0 DEGIL" if rc_atlanan != 0 else "0")


# ===========================================================================
# H2 — UCTAN UCA gozcu.tur
# ===========================================================================

def _tur_kos(gz, tmp, ad, rc, cikti, kilit_dolu=False):
    kok = os.path.join(tmp, "kok-%s" % ad)
    os.makedirs(kok, exist_ok=True)
    yollar = _yollar(kok)
    os.makedirs(yollar["artik_dizini"], exist_ok=True)
    os.makedirs(yollar["kilit_dizini"], exist_ok=True)
    with open(yollar["durum"], "w", encoding="utf-8") as dosya:
        # 🔴 `taban_alindi` SART: gozcu ILK gordugu kirmiziyi TABAN olarak
        # kaydeder ve tur ACMAZ (gozcu.py:488-496). Bayrak konmazsa H2'nin
        # tamami `icra_hal=KOSULMADI` olcer ve "kol olculemedi" hali GECTI
        # sanilir. Olculdu: b6-kanit/06, K0 kontrol mutanti 0/27 yandi.
        json.dump({"kosumlar": {}, "taban_alindi": True,
                   "son_gunluk_tur": time.strftime("%Y-%m-%d",
                                                   time.gmtime(SIMDI))}, dosya)
    kosucu = SahteKosucu(rc, cikti)
    if kilit_dolu:
        # Gozcu KENDI kilidini alamasin. Bicim TEK KAYNAK: kilit.karar
        # `PID=` ve `EPOK=` satirlarini okur (JSON DEGIL).
        with open(os.path.join(yollar["kilit_dizini"], "4242.kilit"), "w",
                  encoding="utf-8") as dosya:
            dosya.write("PID=%d\nEPOK=%.3f\n" % (os.getpid(), SIMDI))
    # 🔴 N2 SAHIP EKSENINI SOK: fikstur sha'si haritada YOK -> `n2_sahip_coz`
    # "olculemedi" der ve gozcu rc'sini 1'e cikarir. O kirmizi ICRA ekseninin
    # DEGIL, sahip ekseninin kirmizisidir; sokulmezse H2'nin rc vakalari
    # olctugu seyi olcmez ([[prob-kendi-baglamini-olcer]]). Sokum DOGRULANIR:
    # H2a/H2b rc=0 bekler, H2c rc=1 — ayrim yalniz icra ekseninden gelir.
    asil_sahip = gz.n2_sahip_coz
    gz.n2_sahip_coz = lambda sha: ("KraL", "test-fiksturu")
    try:
        sonuc = gz.tur(simdi=SIMDI,
                       kosum_okuyucu=lambda: [_kosum(4242, "failure")],
                       defter_okuyucu=lambda: [], tur_kosucu=kosucu,
                       yollar=yollar, pid_canli=lambda p: True)
    finally:
        gz.n2_sahip_coz = asil_sahip
    with open(yollar["durum"], encoding="utf-8") as dosya:
        durum = json.load(dosya)
    return sonuc, durum, kosucu


def bolum_h2(gz, tmp, ek=""):
    print("--- BOLUM H2%s: gozcu.tur uctan uca ---" % ek)

    sonuc, durum, kosucu = _tur_kos(gz, tmp, "a%s" % ek, 0, ATLAMA_B8)
    kalp = sonuc["kalp"]
    vaka("H2a-atlandi-hal%s" % ek, "ATLANDI", kalp.get("icra_hal"))
    vaka("H2a-atlandi-rc%s" % ek, "None", str(kalp.get("icra_rc")))
    vaka("H2a-atlandi-denendi%s" % ek, "True", str(kalp.get("icra_denendi")))
    vaka("H2a-atlandi-gozcu-rc%s" % ek, 0, sonuc["rc"])
    # 🔴 TUKETICI: atlanan tur DENEME SAYMAZ (deneme_sonraki hic cagrilmaz).
    vaka("H2a-atlandi-deneme-yok%s" % ek, "{}",
         json.dumps(durum.get("kosumlar") or {}))

    sonuc, durum, _ = _tur_kos(gz, tmp, "b%s" % ek, 0, TEMIZ)
    kalp = sonuc["kalp"]
    vaka("H2b-basarili-hal%s" % ek, "KOSTU_BASARILI", kalp.get("icra_hal"))
    vaka("H2b-basarili-rc%s" % ek, "0", str(kalp.get("icra_rc")))
    # SOKUM DOGRULAMASI: sahip ekseni sokuldugu icin YESIL tur rc=0 verir.
    # Bu vaka kirmiziysa sokum tutmamistir ve H2a/H2c rc olcumleri GECERSIZDIR.
    vaka("H2b-basarili-gozcu-rc%s" % ek, 0, sonuc["rc"])
    vaka("H2b-basarili-deneme%s" % ek, "VAR",
         "VAR" if (durum.get("kosumlar") or {}) else "YOK")

    sonuc, durum, _ = _tur_kos(gz, tmp, "c%s" % ek, 1, DUSEN)
    kalp = sonuc["kalp"]
    vaka("H2c-dusen-hal%s" % ek, "KOSTU_DUSTU", kalp.get("icra_hal"))
    vaka("H2c-dusen-rc%s" % ek, "1", str(kalp.get("icra_rc")))
    vaka("H2c-dusen-gozcu-rc%s" % ek, 1, sonuc["rc"])
    vaka("H2c-dusen-deneme%s" % ek, "VAR",
         "VAR" if (durum.get("kosumlar") or {}) else "YOK")

    sonuc, durum, kosucu = _tur_kos(gz, tmp, "d%s" % ek, 0, TEMIZ,
                                    kilit_dolu=True)
    kalp = sonuc["kalp"]
    vaka("H2d-kosulmadi-hal%s" % ek, "KOSULMADI", kalp.get("icra_hal"))
    vaka("H2d-kosulmadi-denendi%s" % ek, "False", str(kalp.get("icra_denendi")))
    vaka("H2d-kosucu-cagrilmadi%s" % ek, 0, len(kosucu.cagrilar))


# ===========================================================================
# H3 — TUKETICI EKSENI (nobet-tetik + envanter)
# ===========================================================================

def _kalp(**ek):
    temel = {"damga": "x", "epok": SIMDI, "tetik": "CI_KIRMIZI",
             "ci_olculdu": True, "defter_olculdu": True, "hedef_run": "4242",
             "gunluk_gerekli": False, "rc": 0}
    temel.update(ek)
    return temel


def bolum_h3(tetik_mod, ek=""):
    print("--- BOLUM H3%s: TUKETICI EKSENI ---" % ek)
    bugun = tetik_mod.bugunun_adi(SIMDI)

    k = tetik_mod.karar(_kalp(icra_denendi=True, icra_rc=None,
                              icra_hal="ATLANDI"), SIMDI, bugun)
    vaka("H3a-atlandi-ikinci-tur-yok%s" % ek, "ACMA/GOZCU_ICRA_ETTI",
         "%s/%s" % (k.hukum, k.sebep))

    k = tetik_mod.karar(_kalp(icra_denendi=True, icra_rc=0,
                              icra_hal="KOSTU_BASARILI"), SIMDI, bugun)
    vaka("H3b-kostu-ikinci-tur-yok%s" % ek, "ACMA/GOZCU_ICRA_ETTI",
         "%s/%s" % (k.hukum, k.sebep))

    k = tetik_mod.karar(_kalp(icra_denendi=False, icra_rc=None,
                              icra_hal="KOSULMADI"), SIMDI, bugun)
    vaka("H3c-kosulmadi-tur-acilir%s" % ek, "AC",
         k.hukum if k.sebep != "GOZCU_ICRA_ETTI" else "ACMA/GOZCU_ICRA_ETTI")

    # Geriye donuk kol: `icra_denendi` TASIMAYAN eski kalp.
    k = tetik_mod.karar(_kalp(icra_rc=0), SIMDI, bugun)
    vaka("H3d-eski-kalp-geriye-donuk%s" % ek, "ACMA/GOZCU_ICRA_ETTI",
         "%s/%s" % (k.hukum, k.sebep))

    # ENVANTER — `icra_rc`'yi gozcu.py DISINDA okuyan dosya sayisi CIVILI.
    # [[tasima-tuketici-envanteri-iddia-duzeyinde]]: "sanirim yorum" YOK, SAYI.
    okuyanlar = []
    for ad in sorted(os.listdir(CRON_KOKU)):
        if not ad.endswith(".py") or ad in ("gozcu.py",):
            continue
        if ad.endswith("-test.py") or ad.startswith("."):
            continue
        try:
            with open(os.path.join(CRON_KOKU, ad), encoding="utf-8",
                      errors="replace") as dosya:
                metin = dosya.read()
        except OSError:
            continue
        if re.search(r'get\(\s*["\']icra_rc["\']', metin):
            okuyanlar.append(ad)
    vaka("H3e-tuketici-envanteri%s" % ek, "['nobet-tetik.py']", str(okuyanlar))


# ===========================================================================
# H4 — MUTANTLAR
# ===========================================================================

def sayim():
    return sum(1 for *_x, g in VAKALAR if g), len(VAKALAR)


def _atif(ad, isaret, hedef_onek, yan_onek):
    yeni = VAKALAR[isaret:]
    del VAKALAR[isaret:]
    hedef = [v for v in yeni if any(v[0].startswith(o) for o in hedef_onek)]
    yan = [v for v in yeni if any(v[0].startswith(o) for o in yan_onek)]
    hedef_oldu = bool(hedef) and all(not v[3] for v in hedef)
    yan_yesil = bool(yan) and all(v[3] for v in yan)
    print("MUTANT=%-30s HEDEF_KOL=%-7s (%d vaka) YAN_EKSEN=%-8s (%d vaka)"
          % (ad, "OLDU" if hedef_oldu else "YASADI", len(hedef),
             "YESIL" if yan_yesil else "KIRMIZI", len(yan)))
    return hedef_oldu, yan_yesil


def _gecici_modul(ad, kaynak, dosya_adi):
    yol = os.path.join(CRON_KOKU, dosya_adi)
    with open(yol, "w", encoding="utf-8") as dosya:
        dosya.write(kaynak)
    try:
        return modul_yukle(yol, ad), yol
    except Exception:                                   # noqa: BLE001
        try:
            os.remove(yol)
        except OSError:
            pass
        raise


def bolum_h4(gz, tetik_mod, gz_kaynak, tt_kaynak, tmp):
    print("--- BOLUM H4: MUTANTLAR ---")
    sonuclar = []

    # P1 — ATLANDI yeniden `0`'a esleniyor (ARIZANIN GERI GELMESI)
    isaret = len(VAKALAR)
    asil = gz.icra_halini_coz

    def bozuk(denendi, ham_rc, cikti):
        if not denendi or ham_rc is None:
            return "KOSULMADI", None
        return ("KOSTU_BASARILI", 0) if ham_rc == 0 else ("KOSTU_DUSTU", ham_rc)
    gz.icra_halini_coz = bozuk
    try:
        bolum_h1(gz, ek="-P1")
        bolum_h2(gz, tmp, ek="-P1")
    finally:
        gz.icra_halini_coz = asil
    sonuclar.append(("P1-atlandi-yesile-esleniyor",) + _atif(
        "P1-atlandi-yesile-esleniyor", isaret,
        ("H1c", "H1d", "H1g", "H2a-atlandi-hal", "H2a-atlandi-rc",
         "H2a-atlandi-deneme-yok"),
        ("H1a", "H1b", "H1e", "H1f", "H2b", "H2c", "H2d")))

    # P2 — TUKETICI eski kola dondu (`icra_rc is not None`)
    isaret = len(VAKALAR)
    tt_mut = tt_kaynak.replace(
        'if kalp.get("icra_denendi", kalp.get("icra_rc") is not None):',
        'if kalp.get("icra_rc") is not None:', 1)
    mod, yol = _gecici_modul("b6_tetik_p2", tt_mut, ".b6-tetik-p2.py")
    try:
        bolum_h3(mod, ek="-P2")
    finally:
        os.remove(yol)
    sonuclar.append(("P2-tuketici-eski-kol",) + _atif(
        "P2-tuketici-eski-kol", isaret, ("H3a",), ("H3b", "H3c", "H3d", "H3e")))

    # P3 — ATLANDI turu yeniden DENEME sayiyor
    isaret = len(VAKALAR)
    gz_mut = gz_kaynak.replace(
        '            if icra_hal in ("KOSTU_BASARILI", "KOSTU_DUSTU"):',
        '            if True:', 1).replace(
        'deneme_sonraki(kayit, icra_hal == "KOSTU_BASARILI")',
        'deneme_sonraki(kayit, True)', 1)
    mod, yol = _gecici_modul("b6_gozcu_p3", gz_mut, ".b6-gozcu-p3.py")
    try:
        bolum_h2(mod, tmp, ek="-P3")
    finally:
        os.remove(yol)
    sonuclar.append(("P3-atlanan-deneme-sayiyor",) + _atif(
        "P3-atlanan-deneme-sayiyor", isaret,
        ("H2a-atlandi-deneme-yok",),
        ("H2a-atlandi-hal", "H2a-atlandi-rc", "H2b", "H2c", "H2d")))

    # K0 — KONTROL: kaynak DEGISMEDEN ayni harness'ten gecer
    isaret = len(VAKALAR)
    mod, yol = _gecici_modul("b6_gozcu_k0", gz_kaynak, ".b6-gozcu-k0.py")
    try:
        bolum_h1(mod, ek="-K0")
        bolum_h2(mod, tmp, ek="-K0")
    finally:
        os.remove(yol)
    bolum_h3(tetik_mod, ek="-K0")
    k0 = VAKALAR[isaret:]
    del VAKALAR[isaret:]
    k0_yesil = all(v[3] for v in k0)
    print("MUTANT=%-30s HEDEF_KOL=%-7s (%d vaka)"
          % ("K0-kontrol", "YESIL" if k0_yesil else "KIRMIZI", len(k0)))
    return sonuclar, k0_yesil, len(k0)


# ===========================================================================

def main():
    try:
        with open(GOZCU, encoding="utf-8") as dosya:
            gz_kaynak = dosya.read()
        with open(TETIK, encoding="utf-8") as dosya:
            tt_kaynak = dosya.read()
    except OSError as hata:
        print("KABUL=KALDI (kaynak okunamadi: %s)" % hata)
        return 2
    gz = modul_yukle(GOZCU, "b6_gozcu")
    if not hasattr(gz, "icra_halini_coz"):
        print("KABUL=KALDI (B6 yamasi KURULU DEGIL: icra_halini_coz yok)")
        return 2
    tetik_mod = modul_yukle(TETIK, "b6_tetik")

    tmp = tempfile.mkdtemp(prefix="b6-icra-")
    try:
        bolum_h1(gz)
        bolum_h2(gz, tmp)
        bolum_h3(tetik_mod)
        mutantlar, k0_yesil, k0_n = bolum_h4(gz, tetik_mod, gz_kaynak,
                                             tt_kaynak, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    gecen, toplam = sayim()
    m_gecen = sum(1 for _, h, y in mutantlar if h and y)
    print("MUTANT=%d/%d  HEDEF_KOL_ATFI=%d/%d  KONTROL=%d/%d"
          % (m_gecen, len(mutantlar),
             sum(1 for _, h, _y in mutantlar if h), len(mutantlar),
             k0_n if k0_yesil else 0, k0_n))
    print("TOPLAM=%d GECTI=%d KALDI=%d" % (toplam, gecen, toplam - gecen))
    if not k0_yesil:
        print("KABUL=OLCULEMEDI (K0 kontrol mutanti kirmizi — batarya kararsiz)")
        return 3
    if gecen == toplam and m_gecen == len(mutantlar):
        print("KABUL=GECTI (%d/%d vaka)" % (gecen, toplam))
        return 0
    print("KABUL=KALDI (%d/%d vaka, %d/%d mutant)"
          % (gecen, toplam, m_gecen, len(mutantlar)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
