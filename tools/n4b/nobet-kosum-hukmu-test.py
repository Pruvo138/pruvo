#!/usr/bin/env python3
"""B5 KABUL BATARYASI — DEFTER bacaginin rc'si RUN-ID denemesine yazilmiyor mu?

PAKET: tools/paket-n4b-onarim-hatti-kalanlar.md, blok B5.
KANONIK KAYNAK: pruvo deposu `tools/n4b/nobet-kosum-hukmu-test.py`.

KOSUM:  python3 /Users/okan/.claude/cron/nobet-kosum-hukmu-test.py
KABUL:  son satir `KABUL=GECTI (n/n vaka)` ve rc=0.
CAGRI YERI: `testler.py` PAKETLER listesi.

OLCULEN KABUL MADDELERI
  1) Pozitif: motor rc=0 + CI temiz -> run-id denemesi ARTMAZ (KAPANIR)  -> K3a
  2) Negatif: motor rc!=0 -> run-id denemesi ARTAR, eskalasyon yolu OLMEZ -> K3b/K3c
  3) Mutant: defter rc'si yeniden run-id sayacina baglanirsa KIRMIZI      -> Q1
  4) Gozcunun KENDI rc'si DEGISMEZ — turun kirmiziligi kaybolmaz          -> K3a-rc

🔴 ASIL VAKA (gozcu.log:1365-1371, 19 Agu 22:53Z): motor kostu (rc=0), cikti
"🟢 CI temiz" dedi, tur yine `HUKUM=ONARIMSIZ_TUR rc=1` ile kapandi ve O
RUN-ID'NIN denemesi ARTTI. N4A'nin saydigi 10 eskalasyonun 4'u bu yoldan dogdu.
K3a tam bu turu kurar: SURECIN rc'si 1, KOSUMUN hukmu TEMIZ.
"""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time

CRON_KOKU = "/Users/okan/.claude/cron"
NOBET_KAPI = os.path.join(CRON_KOKU, "nobet-kapi.py")
GOZCU = os.path.join(CRON_KOKU, "gozcu.py")

SIMDI = 1_755_000_000.0
VAKALAR = []


def vaka(vid, beklenen, olculen):
    gecti = (str(beklenen) == str(olculen))
    VAKALAR.append((vid, beklenen, olculen, gecti))
    print("VAKA=%-34s BEKLENEN=%-18s OLCULEN=%-18s SONUC=%s"
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


def _yollar(kok):
    return {"durum": os.path.join(kok, "durum.json"),
            "kalp": os.path.join(kok, "kalp.json"),
            "log": os.path.join(kok, "gozcu.log"),
            "kilit_dizini": os.path.join(kok, "kilit"),
            "eskalasyon": os.path.join(kok, "eskalasyon.md"),
            "artik_dizini": os.path.join(kok, "artik")}


def _kosum(kimlik, conclusion="failure"):
    return {"databaseId": kimlik, "name": "ci", "conclusion": conclusion,
            "status": "completed", "headBranch": "main", "headSha": "abc123"}


class SahteKosucu(object):
    def __init__(self, rc, cikti):
        self.rc = rc
        self.cikti = cikti
        self.cagrilar = []

    def __call__(self, bayraklar):
        self.cagrilar.append(list(bayraklar))
        return (self.rc, self.cikti)


# 🔴 ASIL VAKA: surec rc=1 (DEFTER bacagi ONARIMSIZ_TUR), kosum hukmu TEMIZ.
CIKTI_DEFTER_KIRMIZI_KOSUM_TEMIZ = (
    "MOTOR_DENEME motor=minimax-m3 rc=0 sebep=YESIL\n"
    "🟢 CI temiz\n"
    "KOSUM_HUKMU=TEMIZ MOTOR_RC=0 TUR_HUKMU=TEMIZ\n"
    "USTUSTE_ONARIMSIZ=121\n"
    "HUKUM=ONARIMSIZ_TUR rc=1\n")

CIKTI_MOTOR_DUSTU = (
    "MOTOR_DENEME motor=minimax-m3 rc=1 sebep=HATA\n"
    "TUR_HALI=KOSTU_DUSTU SEBEP=SURE_TAVANI USTUSTE_ONARIMSIZ=122 SAYAC_YAZILDI=1\n"
    "KOSUM_HUKMU=MOTOR_DUSTU MOTOR_RC=- TUR_HUKMU=SURE_TAVANI\n")


# ===========================================================================
# K1 — kosum_hukmu_coz (nobet-kapi, saf)
# ===========================================================================

def bolum_k1(nk, ek=""):
    print("--- BOLUM K1%s: kosum_hukmu_coz (saf) ---" % ek)
    for ad, args, beklenen in (
            ("K1a-temiz", (0, "TEMIZ", 0, 0), "TEMIZ"),
            ("K1b-kapandi", (0, "KAPANDI", 0, 0), "TEMIZ"),
            ("K1c-onarim-ilerliyor", (0, "ONARIM_ILERLIYOR", 0, 0), "ONARIM_DENENDI"),
            ("K1d-onarimsiz-tur", (0, "ONARIMSIZ_TUR", 0, 0), "ONARIM_DENENDI"),
            ("K1e-olcum-var", (0, "", 1, 0), "ONARIM_DENENDI"),
            ("K1f-hukumsuz", (0, "", 0, 0), "OLCULEMEDI"),
            ("K1g-motor-dustu", (1, "TEMIZ", 0, 0), "MOTOR_DUSTU"),
            ("K1h-rc-yok", (None, "TEMIZ", 0, 0), "OLCULEMEDI"),
    ):
        try:
            sonuc = nk.kosum_hukmu_coz(*args)
        except Exception as hata:                       # noqa: BLE001
            sonuc = "HATA:%s" % type(hata).__name__
        vaka("%s%s" % (ad, ek), beklenen, sonuc)


# ===========================================================================
# K2 — kosum_hukmunu_ayikla (gozcu, saf)
# ===========================================================================

KAPI_HUKMU_SIZAN = (
    "MOTOR_DENEME motor=minimax-m3 rc=0 sebep=YESIL\n"
    "N2B HUKUM=GECER KOL=N2B-MUAF EV=KraL ACIK=0 KALEM=-\n"
    "CI kirmizisi bu turda onarildi (duz prose, makine jetonu YOK).\n"
    "MOTOR=minimax-m3\n")


def bolum_k1b(nk, ek=""):
    """K1b — N2B PARTI KAPISININ hukmu TURUN hukmu DEGILDIR.

    🔴 CANLIDA olculdu (gozcu.log, 2026-08-20T14:23:03Z turu):
        KOSUM_HUKMU=ONARIM_DENENDI MOTOR_RC=0 TUR_HUKMU=GECER
    `GECER` kapinin hukmudur; isci makine jetonu basmadigi icin
    `tur_hukmu_ayikla` SONUNCU eslesen olarak KAPININ satirini aldi.
    """
    print("--- BOLUM K1b%s: KAPI HUKMU ELENIR ---" % ek)
    vaka("K1b-kapi-hukmu-elendi%s" % ek, "",
         nk.kosum_tur_hukmu(KAPI_HUKMU_SIZAN))
    vaka("K1b-tur-hukmu-korunur%s" % ek, "TEMIZ",
         nk.kosum_tur_hukmu(KAPI_HUKMU_SIZAN + "HUKUM=TEMIZ rc=0\n"))
    vaka("K1b-jetonsuz-olculemedi%s" % ek, "OLCULEMEDI",
         nk.kosum_hukmu_coz(0, nk.kosum_tur_hukmu(KAPI_HUKMU_SIZAN), 0, 0))
    # Kontrol kolu: eleme YAPILMASAYDI `GECER` okunur ve hukum ONARIM_DENENDI
    # olurdu — yani "olculemedim" yerine "denedim" denirdi (yanlis ozne).
    vaka("K1b-elemesiz-yanlis-ozne%s" % ek, "ONARIM_DENENDI",
         nk.kosum_hukmu_coz(0, nk.tur_hukmu_ayikla(KAPI_HUKMU_SIZAN), 0, 0))


def bolum_k2(gz, ek=""):
    print("--- BOLUM K2%s: kosum_hukmunu_ayikla ---" % ek)
    vaka("K2a-temiz%s" % ek, "TEMIZ",
         gz.kosum_hukmunu_ayikla(CIKTI_DEFTER_KIRMIZI_KOSUM_TEMIZ))
    vaka("K2b-motor-dustu%s" % ek, "MOTOR_DUSTU",
         gz.kosum_hukmunu_ayikla(CIKTI_MOTOR_DUSTU))
    vaka("K2c-sonuncu-kazanir%s" % ek, "MOTOR_DUSTU",
         gz.kosum_hukmunu_ayikla("KOSUM_HUKMU=TEMIZ\nKOSUM_HUKMU=MOTOR_DUSTU\n"))
    # 🔴 FAIL-CLOSED: jeton yoksa "temiz" SANILMAZ.
    vaka("K2d-jetonsuz-fail-closed%s" % ek, "OLCULEMEDI",
         gz.kosum_hukmunu_ayikla("HUKUM=ONARIMSIZ_TUR rc=1\n"))
    vaka("K2e-bos%s" % ek, "OLCULEMEDI", gz.kosum_hukmunu_ayikla(""))


# ===========================================================================
# K3 — UCTAN UCA gozcu.tur (ASIL VAKA)
# ===========================================================================

def _tur_kos(gz, tmp, ad, rc, cikti, tekrar=1, kok=None):
    kok = kok or os.path.join(tmp, "kok-%s" % ad)
    ilk = not os.path.isdir(kok)
    os.makedirs(kok, exist_ok=True)
    yollar = _yollar(kok)
    os.makedirs(yollar["artik_dizini"], exist_ok=True)
    os.makedirs(yollar["kilit_dizini"], exist_ok=True)
    if ilk:
        with open(yollar["durum"], "w", encoding="utf-8") as dosya:
            json.dump({"kosumlar": {}, "taban_alindi": True,
                       "son_gunluk_tur": time.strftime("%Y-%m-%d",
                                                       time.gmtime(SIMDI))},
                      dosya)
    kosucu = SahteKosucu(rc, cikti)
    sonuc = None
    for i in range(tekrar):
        sonuc = gz.tur(simdi=SIMDI + i * 900,
                       kosum_okuyucu=lambda: [_kosum(4242)],
                       defter_okuyucu=lambda: [], tur_kosucu=kosucu,
                       yollar=yollar, pid_canli=lambda p: True)
    with open(yollar["durum"], encoding="utf-8") as dosya:
        durum = json.load(dosya)
    return sonuc, (durum.get("kosumlar") or {}).get("4242") or {}, kok


def bolum_k3(gz, tmp, ek=""):
    print("--- BOLUM K3%s: gozcu.tur (ASIL VAKA) ---" % ek)

    # K3a — DEFTER bacagi KIRMIZI (rc=1) ama KOSUM TEMIZ.
    sonuc, kayit, _ = _tur_kos(gz, tmp, "a%s" % ek, 1,
                               CIKTI_DEFTER_KIRMIZI_KOSUM_TEMIZ)
    vaka("K3a-deneme-KAPANDI%s" % ek, "KAPANDI", kayit.get("durum"))
    vaka("K3a-kalp-kosum-hukmu%s" % ek, "TEMIZ",
         (sonuc["kalp"] or {}).get("kosum_hukmu"))
    # 🔴 KABUL-4: gozcunun KENDI rc'si DEGISMEZ — turun kirmiziligi kaybolmaz.
    vaka("K3a-gozcu-rc-degismedi%s" % ek, 1, sonuc["rc"])
    vaka("K3a-icra-hal%s" % ek, "KOSTU_DUSTU",
         (sonuc["kalp"] or {}).get("icra_hal"))

    # K3b — motor dustu: deneme ARTAR (eskalasyon yolu OLMEZ).
    sonuc, kayit, kok = _tur_kos(gz, tmp, "b%s" % ek, 1, CIKTI_MOTOR_DUSTU)
    vaka("K3b-deneme-DUSTU%s" % ek, "DUSTU", kayit.get("durum"))
    vaka("K3b-deneme-sayisi%s" % ek, 1, kayit.get("deneme"))
    vaka("K3b-gozcu-rc%s" % ek, 1, sonuc["rc"])

    # K3c — ucuncu dususte ESKALASYON ATESLER (kabul-2'nin ASIL sarti).
    _, kayit, _ = _tur_kos(gz, tmp, "b%s" % ek, 1, CIKTI_MOTOR_DUSTU,
                           tekrar=2, kok=kok)
    vaka("K3c-eskalasyon%s" % ek, "ESKALASYON", kayit.get("durum"))
    vaka("K3c-deneme-sayisi%s" % ek, 3, kayit.get("deneme"))


# ===========================================================================
# K4 — MUTANTLAR
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


def bolum_k4(nk, gz, gz_kaynak, tmp):
    print("--- BOLUM K4: MUTANTLAR ---")
    sonuclar = []

    # Q1 — DEFTER rc'si YENIDEN run-id sayacina baglaniyor (arizanin donusu)
    isaret = len(VAKALAR)
    gz_mut = gz_kaynak.replace(
        'deneme_sonraki(kayit, kosum_hukmu == "TEMIZ")',
        'deneme_sonraki(kayit, icra_hal == "KOSTU_BASARILI")', 1)
    mod, yol = _gecici_modul("b5_gozcu_q1", gz_mut, ".b5-gozcu-q1.py")
    try:
        bolum_k2(mod, ek="-Q1")
        bolum_k3(mod, tmp, ek="-Q1")
    finally:
        os.remove(yol)
    sonuclar.append(("Q1-defter-rc-sayaca",) + _atif(
        "Q1-defter-rc-sayaca", isaret,
        ("K3a-deneme-KAPANDI",),
        ("K2", "K3a-kalp-kosum-hukmu", "K3a-gozcu-rc-degismedi", "K3a-icra-hal",
         "K3b", "K3c")))

    # Q2 — AYIKLAYICI fail-open: jeton ne olursa olsun TEMIZ.
    # Hedef: NEGATIF kol (eskalasyon) OLMEMIS olmali — kabul-2'nin bekcisi.
    isaret = len(VAKALAR)
    asil = gz.kosum_hukmunu_ayikla
    gz.kosum_hukmunu_ayikla = lambda cikti: "TEMIZ"
    try:
        bolum_k3(gz, tmp, ek="-Q2")
    finally:
        gz.kosum_hukmunu_ayikla = asil
    sonuclar.append(("Q2-ayiklayici-fail-open",) + _atif(
        "Q2-ayiklayici-fail-open", isaret,
        # K3c-deneme-sayisi de HEDEFTEDIR: kayit KAPANDI olunca `yeni_kirmizilar`
        # onu havuzdan eler, sonraki turlar HIC kosmaz ve sayi 3 yerine 1 kalir.
        ("K3b-deneme-DUSTU", "K3c-eskalasyon", "K3c-deneme-sayisi"),
        ("K3a", "K3b-gozcu-rc", "K3b-deneme-sayisi")))

    # Q3 — kosum cozucusu MOTOR rc'sini YUTUYOR.
    isaret = len(VAKALAR)
    asil_coz = nk.kosum_hukmu_coz
    nk.kosum_hukmu_coz = lambda motor_rc, tur_hukmu, kapanan=0, dagitilan=0: "TEMIZ"
    try:
        bolum_k1(nk, ek="-Q3")
    finally:
        nk.kosum_hukmu_coz = asil_coz
    sonuclar.append(("Q3-motor-rc-yutuluyor",) + _atif(
        "Q3-motor-rc-yutuluyor", isaret,
        ("K1c", "K1d", "K1e", "K1f", "K1g", "K1h"), ("K1a", "K1b-")))

    # Q4 — N2B ELEMESI KALDIRILDI: kapinin hukmu turun hukmu sanilir.
    isaret = len(VAKALAR)
    asil_eleme = nk.kosum_tur_hukmu
    nk.kosum_tur_hukmu = nk.tur_hukmu_ayikla
    try:
        bolum_k1b(nk, ek="-Q4")
    finally:
        nk.kosum_tur_hukmu = asil_eleme
    sonuclar.append(("Q4-N2B-elemesi-yok",) + _atif(
        "Q4-N2B-elemesi-yok", isaret,
        ("K1b-kapi-hukmu-elendi", "K1b-jetonsuz-olculemedi"),
        ("K1b-tur-hukmu-korunur", "K1b-elemesiz-yanlis-ozne")))

    # K0 — KONTROL: kaynak DEGISMEDEN ayni harness'ten gecer
    isaret = len(VAKALAR)
    mod, yol = _gecici_modul("b5_gozcu_k0", gz_kaynak, ".b5-gozcu-k0.py")
    try:
        bolum_k2(mod, ek="-K0")
        bolum_k3(mod, tmp, ek="-K0")
    finally:
        os.remove(yol)
    bolum_k1(nk, ek="-K0")
    bolum_k1b(nk, ek="-K0")
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
    except OSError as hata:
        print("KABUL=KALDI (gozcu.py okunamadi: %s)" % hata)
        return 2
    nk = modul_yukle(NOBET_KAPI, "b5_nobet_kapi")
    gz = modul_yukle(GOZCU, "b5_gozcu")
    eksik = [a for a, m in (("kosum_hukmu_coz", nk),
                            ("kosum_tur_hukmu", nk),
                            ("kosum_hukmunu_ayikla", gz))
             if not hasattr(m, a)]
    if eksik:
        print("KABUL=KALDI (B5 yamasi KURULU DEGIL: %s)" % ",".join(eksik))
        return 2

    tmp = tempfile.mkdtemp(prefix="b5-kosum-")
    try:
        bolum_k1(nk)
        bolum_k1b(nk)
        bolum_k2(gz)
        bolum_k3(gz, tmp)
        mutantlar, k0_yesil, k0_n = bolum_k4(nk, gz, gz_kaynak, tmp)
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
