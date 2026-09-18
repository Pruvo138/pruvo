#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NOBET ONARIM KABUL BATARYASI — W2 dilim 1 (16 Eyl) + dilim 2 (18 Eyl 2026).

OLCTUGU KALEMLER: K316 (V1 + V2 + vaka 6) · K334 · K326 (+ K311 YUZ B
eskalasyon ardili) · K325 · K311 (b). Her kalem vaka + HEDEF-KOL ATIFLI
mutant + KONTROL ile olculur. K334 zinciri GERCEK giris noktalarindan
kosar: gozcu `tur()` (kuru DEGIL, LLM kosucusu sahte) -> kalp -> GERCEK
`ci-nobeti.sh` -> GERCEK `nobet-tetik.py --karar` (damga diske yazilir).

🔴 CANLI DOSYADA MUTASYON YOK. Batarya `tools/nobet-onarim/cron/` altindaki
KOPYALARI gecici bir sandbox'a alir, olcumu ORADAN yapar; mutantlar yalniz
sandbox'ta yasar. Sandbox is bitince SILINIR (Okan disk kurali; try/finally +
atexit). `~/.claude/cron` altina TEK BAYT yazilmaz — `PRUVO_CRON_KOKU` ve
`PRUVO_EV_KOKU` env'leri sandbox'a/ depoya bakar.

CI: `.github/workflows/nobet.yml` serit-b. CI'da `~/.claude/cron` YOKTUR;
batarya o yolu HIC kullanmaz, dolayisiyla CI'da da ayni olcumu yapar. Kopyasi
olmayan bagimli modul (`cip_dogum_bekcisi.py` vb.) eksikse bu ADIYLA basilir.

KOSUM: python3 tools/nobet-onarim/nobet-onarim-kabul.py   (rc=0 => YESIL)
"""

import atexit
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.abspath(__file__))
EV_KOKU = os.path.dirname(os.path.dirname(KOK))
KOPYA_DIZINI = os.path.join(KOK, "cron")

# Sandbox'a TASINACAK kopyalar. Liste TAM: eksik bir bagimlilik "sessiz yesil"
# degil, ADIYLA bir kurulum hatasidir.
KOPYALAR = (
    "gozcu.py", "gozcu-mutasyon.py", "gozcu-test.py", "kilit.py",
    "nobet-tetik.py", "nobet-kapi.py", "nobet-kabul-test.py",
    "nobet_merdiven.py", "cip_dogum_bekcisi.py",
    # W2-2: K334 zinciri GERCEK giris noktasindan kosar (ci-nobeti.sh ->
    # nobet-tetik --karar); tetik bataryasi + curutucusu da kumda olculur.
    "ci-nobeti.sh", "nobet-tetik-test.py", "nobet-tetik-mutasyon.py",
)
# `motor_ayakta()` motor anahtar DOSYASININ boyutuna bakar. Kumda SAHTE, bos
# olmayan bir dosya konur — SIR DEGILDIR, canli anahtar OKUNMAZ/KOPYALANMAZ.
# Olculdu (18 Eyl): dosya yokken vaka 35 (`minimax-m3 karantinada degil`) ve
# goc vakalari motor-dusmus sanip KIRMIZI yaniyordu — ortam artifakti.
SAHTE_ANAHTAR_ADI = ".minimax-anahtar"

# 🔴 EL KITABI KOPYA DEGIL, FIKSTUR (17 Eyl 2026, KraL-Tamirci-17Eyl).
# OLCULEN KILITLENME: `111ffdef` izlenen `cron/onarim-el-kitabi.md` kopyasini
# depodan cikardi (ad `onarim*.md` = ic rapor sizinti nobetcisi, seritA3 ->
# yayin SKIPPED). Batarya ise o kopyayi KOPYALAR'da sart kosuyordu -> 6/6 vaka
# `KOPYA EKSIK` ile dustu (SERIT B 16-17 Eyl kosumlari). Iki kapi AYNI dosyayi
# zit yonde istedi; kopyayi geri koymak sizinti kapisini, kopyasiz birakmak
# bataryayi kirmizi yakar. SINIF COZUMU: el kitabi IZLENEN bir belge olarak
# degil, sandbox icinde URETILEN bir fikstur olarak yasar (diskte yalniz
# sandbox omru kadar; depoda `.md` YOK). `kat` sutunu motor adi TASIMAZ: hepsi
# `SAHTE-KAT` yazilir, dogru deger `nobet-kapi.py --el-kitabi-uret` ile
# `kat_sec`ten TURER. Boylece (a) V2 uretici vakasinin "once KIRMIZI" tabani
# motor kararindan bagimsiz tutar, (b) emekli motor adi nobetcisi bu dosyada
# ad bulmaz, (c) fikstur canli el kitabindan SESSIZCE ayrisamaz — ayrismanin
# tek ekseni olan `kat` zaten uretilir.
EL_KITABI_ADI = "onarim-el-kitabi.md"
FIKSTUR_KAT = "SAHTE-KAT"
_EL_KITABI_SATIRLARI = (
    ("D1 senkron / sapma / drift",
     "d1-sync, d1 senkron, d1 sapma, d1 drift, uzlastirici, katalog senkron",
     "tools/d1-sync.py",
     "python3 /Users/okan/dev/pruvo/tools/d1-sync.py --durum"),
    ("Arama paritesi (site/Ege)",
     "parite, arama paritesi, esanlam, ege arama",
     "tools/parite-ege.js · tools/parite-test.js",
     "node /Users/okan/dev/pruvo/tools/parite-ege.js"),
    ("Katalog alan / tip sapmasi",
     "katalog alan, alan tipi, tip sapmasi, sema gocu",
     "tools/katalog-alan-kapisi.py",
     "python3 /Users/okan/dev/pruvo/tools/katalog-alan-kapisi.py"),
    ("Kisisel veri / gizlilik sizintisi",
     "kisisel veri, gizlilik, sizinti, tedarikci adi",
     "tools/kisisel-veri-test.py",
     "python3 /Users/okan/dev/pruvo/tools/kisisel-veri-test.py"),
    ("Shop / panel / odeme yuzeyi",
     "shop, odeme, sepet, panel yuzeyi, konfigur",
     "shop/test/kabul.js",
     "node /Users/okan/dev/pruvo/shop/test/kabul.js --paritesiz"),
    ("Yeni test CI'da kosmuyor",
     "ci kapsam, ci'da kosmuyor, kancada yok, kabul testi cagrilmiyor, adim envanteri",
     "tools/ci-kapsam-test.py",
     "python3 /Users/okan/dev/pruvo/tools/ci-kapsam-test.py"),
    ("CI adimi yanlis seritte / beyansiz kapi",
     "serit, is akisi, beyansiz kapi, kapi kirmizi, workflow adimi",
     "tools/is-akisi-kapisi.py",
     "python3 /Users/okan/dev/pruvo/tools/is-akisi-kapisi.py"),
    ("STL R2/Drive kopya sapmasi",
     "stl kopya, stl r2, stl drive, uc kopya, sadece drive, uretim dosyasi eksik",
     "tools/stl-uc-kopya-nobet.py",
     "python3 /Users/okan/dev/pruvo/tools/stl-uc-kopya-nobet.py"),
    ("Kardes depo testi",
     "kardes depo, kardes depo testi, kardes depodaki test, kardes repo testi",
     "pruvo-hasat/test/hasat_denetim_kabul.py",
     "python3 /Users/okan/dev/pruvo-hasat/test/hasat_denetim_kabul.py"),
)


def el_kitabi_fiksturu():
    """Sandbox el kitabi metni (tablo bicimi `nobet-kapi.py::el_kitabi_oku`)."""
    satirlar = ["# el kitabi fiksturu (nobet-onarim-kabul sandbox)", "",
                "| sinif | jetonlar | arac | kabul komutu | kat |",
                "|---|---|---|---|---|"]
    for sinif, jetonlar, arac, komut in _EL_KITABI_SATIRLARI:
        satirlar.append("| %s | %s | %s | `%s` | %s |"
                        % (sinif, jetonlar, arac, komut, FIKSTUR_KAT))
    return "\n".join(satirlar) + "\n"

# --- W2-2 kum probu ------------------------------------------------------
# Gozcu turunu GERCEK `tur()` ile (kuru DEGIL) kumda kosar. Yan etkili iki
# kol DEGISTIRILIR ve bu ADIYLA yazilir: `_bekci_kolu` (cip_dogum_bekcisi
# CRON_KOKU'yu mutlak yol olarak tutar -> kumdan bildirim/yazma riski) ve
# `n2_devir_kararlari` (iz dosyasi). LLM turu kosucusu sahtedir; cagri
# SAYILIR. Prob `gozcu.CRON_KOKU` kum DEGILSE FAIL-CLOSED durur.
PROB_ADI = "_w2_prob.py"
PROB_KAYNAGI = r'''"""W2-2 kum probu — YALNIZ kum icinde kosar; canli yola dokunmaz."""
import importlib.util
import json
import os
import sys
import time

KUM = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, KUM)
sys.dont_write_bytecode = True


def yukle(ad, yol):
    spec = importlib.util.spec_from_file_location(ad, yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def gozcu_turu(senaryo_yolu):
    with open(senaryo_yolu, encoding="utf-8") as dosya:
        s = json.load(dosya)
    gz = yukle("gozcu_prob", os.path.join(KUM, "gozcu.py"))
    if os.path.realpath(gz.CRON_KOKU) != os.path.realpath(KUM):
        print("PROB_RED gozcu.CRON_KOKU kum DEGIL: %s" % gz.CRON_KOKU)
        return 3
    gz._bekci_kolu = lambda simdi, kuru: {
        "hukum": "TEMIZ", "sebep": "KUM", "kirmizi": False,
        "bildirim": {}, "teslim": {}}
    gz.n2_devir_kararlari = lambda kalemler, simdi, modul=None: {
        "DEVREDILDI": 0, "SLA_ICINDE": 0, "KAPALI": 0, "ZATEN": 0,
        "ihlal_eklenen": 0, "hata": False}
    yollar = {
        "durum": os.path.join(KUM, "gozcu-durum.json"),
        "kalp": os.path.join(KUM, "gozcu-kalp.json"),
        "log": os.path.join(KUM, "gozcu.log"),
        "kilit_dizini": os.path.join(KUM, "gozcu-kilit-gozcu"),
        "eskalasyon": os.path.join(KUM, "gozcu-eskalasyon.md"),
        "artik_dizini": KUM,
    }
    os.makedirs(yollar["kilit_dizini"], exist_ok=True)
    simdi = time.time()
    durum = s.get("durum") or {}
    if s.get("gunluk_yapildi"):
        durum["son_gunluk_tur"] = time.strftime("%Y-%m-%d", time.gmtime(simdi))
    with open(yollar["durum"], "w", encoding="utf-8") as dosya:
        json.dump(durum, dosya)
    kalemler = gz.NK.defter_ayristir(s.get("defter") or "")
    cagrilar = []

    def kosucu(bayraklar):
        cagrilar.append(list(bayraklar))
        return 0, "KOSUM_HUKMU=TEMIZ\n"

    sonuc = gz.tur(kuru=False, simdi=simdi,
                   kosum_okuyucu=lambda: (s.get("kosumlar") or [], "TAMAM"),
                   defter_okuyucu=lambda: kalemler, tur_kosucu=kosucu,
                   yollar=yollar, pid_canli=lambda pid: False)
    kalp = sonuc["kalp"]
    alanlar = ("tetik", "icra_denendi", "icra_anahtar", "gunluk_gerekli",
               "kirmizi_toplam", "kirmizi_ardilsiz", "eskalasyon_acik", "rc",
               "uretken", "icra_hal", "kosum_hukmu", "dagitilabilir")
    print("PROB_KALP " + json.dumps({a: kalp.get(a, "<YOK>") for a in alanlar},
                                    sort_keys=True))
    print("PROB_KOSUCU " + json.dumps(cagrilar))
    return 0


def sozluk(defter_yolu):
    nk = yukle("nk_prob", os.path.join(KUM, "nobet-kapi.py"))
    ev = os.environ.get("PRUVO_EV_KOKU") or ""
    pb = yukle("pb_prob", os.path.join(ev, "tools", "parti-borc-kapisi.py"))
    with open(defter_yolu, encoding="utf-8") as dosya:
        kalemler = nk.defter_ayristir(dosya.read())
    nk_acik = sorted(k["id"] for k in nk.onarim_kalemleri(kalemler)
                     + nk.sahipli_kalemler(kalemler))
    gecersiz = []
    acik, okundu, _hata = pb.acik_kalem_listesi(defter_yolu, gecersiz_sink=gecersiz)
    pb_acik = sorted(k["kimlik"] for k in acik)
    print("PROB_SOZLUK " + json.dumps({
        "kaynak": nk.SOZLUK_KAYNAGI, "nk": nk_acik, "pb": pb_acik,
        "pb_okundu": okundu, "pb_gecersiz": len(gecersiz),
        "bilinmeyen": len(nk.bilinmeyen_durumlu_kalemler(kalemler))}, sort_keys=True))
    return 0


if __name__ == "__main__":
    if sys.argv[1] == "gozcu":
        sys.exit(gozcu_turu(sys.argv[2]))
    if sys.argv[1] == "sozluk":
        sys.exit(sozluk(sys.argv[2]))
    sys.exit(2)
'''

_SANDBOXLAR = []


def _sandbox_kur():
    """Kopyalari izole bir dizine acar. Hata olsa da atexit SILER."""
    kok = tempfile.mkdtemp(prefix="nobet-onarim-kabul-")
    _SANDBOXLAR.append(kok)
    for ad in KOPYALAR:
        kaynak = os.path.join(KOPYA_DIZINI, ad)
        if not os.path.exists(kaynak):
            raise AssertionError("KOPYA EKSIK: %s (sandbox kurulamaz)" % ad)
        shutil.copy2(kaynak, os.path.join(kok, ad))
    with open(os.path.join(kok, EL_KITABI_ADI), "w", encoding="utf-8") as dosya:
        dosya.write(el_kitabi_fiksturu())
    with open(os.path.join(kok, SAHTE_ANAHTAR_ADI), "w", encoding="utf-8") as dosya:
        dosya.write("SAHTE-KUM-ANAHTARI")
    with open(os.path.join(kok, PROB_ADI), "w", encoding="utf-8") as dosya:
        dosya.write(PROB_KAYNAGI)
    return kok


def _sandbox_sil(kok):
    shutil.rmtree(kok, ignore_errors=True)
    if kok in _SANDBOXLAR:
        _SANDBOXLAR.remove(kok)


@atexit.register
def _artik_temizle():
    for kok in list(_SANDBOXLAR):
        _sandbox_sil(kok)


def _kos(sandbox, betik, *bayraklar):
    """Sandbox icindeki betigi KOSAR. Doner: (rc, cikti)."""
    ortam = dict(os.environ)
    ortam["PRUVO_CRON_KOKU"] = sandbox
    ortam["PRUVO_EV_KOKU"] = EV_KOKU
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"
    sonuc = subprocess.run(
        [sys.executable, os.path.join(sandbox, betik)] + list(bayraklar),
        cwd=sandbox, env=ortam, capture_output=True, text=True, timeout=900)
    return sonuc.returncode, (sonuc.stdout or "") + (sonuc.stderr or "")


def _sayi(cikti, alan):
    """`ALAN=<n>` degerini ciktidan okur; yoksa None (tahmin URETILMEZ)."""
    esles = re.search(r"\b%s=(\d+)" % re.escape(alan), cikti)
    return int(esles.group(1)) if esles else None


def _vaka_hukmu(cikti, ad_parcasi):
    """Bir V2 vakasinin YESIL/KIRMIZI hukmunu satir basindan okur."""
    for satir in cikti.splitlines():
        if ad_parcasi in satir:
            if satir.startswith("YESIL"):
                return "YESIL"
            if satir.startswith("KIRMIZI"):
                return "KIRMIZI"
    return "BULUNAMADI"


def _mutant_uygula(sandbox, dosya, eski, yeni):
    """Sandbox kopyasinda TEK satir mutasyonu. Etkisiz kalirsa FAIL-LOUD."""
    yol = os.path.join(sandbox, dosya)
    with open(yol, encoding="utf-8") as dosya_nesnesi:
        metin = dosya_nesnesi.read()
    if metin.count(eski) != 1:
        raise AssertionError("MUTANT CAPASI TEKIL DEGIL (%d kez): %s"
                             % (metin.count(eski), eski))
    with open(yol, "w", encoding="utf-8") as dosya_nesnesi:
        dosya_nesnesi.write(metin.replace(eski, yeni))


# --- vakalar ---------------------------------------------------------------

def vaka_k316_v1_capa_bayatligi_kapandi():
    """K316/V1: gozcu-mutasyon.py rc=0 · MUTANT=16/16 · YAMA_TUTMADI=0.

    Kalem 27 Agu'da `YAMA_TUTMADI=1` olctu (bir mutantin capasi kaynakta
    BULUNMUYORDU) ve payda `len(MUTANTLAR) - YAMA_TUTMADI` ile SESSIZCE
    daraliyordu. Bugunku olcum: kapsam tabandan DUSMUYOR.
    """
    sandbox = _sandbox_kur()
    try:
        rc, cikti = _kos(sandbox, "gozcu-mutasyon.py")
        olen = re.search(r"\bMUTANT=(\d+)/(\d+)", cikti)
        assert olen, "MUTANT=<n>/<n> satiri BASILMADI:\n%s" % cikti[-1500:]
        pay, payda = int(olen.group(1)), int(olen.group(2))
        yama = _sayi(cikti, "YAMA_TUTMADI")
        assert rc == 0, "V1 rc=%d (beklenen 0)\n%s" % (rc, cikti[-1500:])
        assert yama == 0, "YAMA_TUTMADI=%s (beklenen 0)" % yama
        assert payda == 16, "payda %d (16 bekleniyordu — kapsam DUSTU)" % payda
        assert pay == payda, "MUTANT=%d/%d — olmeyen eksen var" % (pay, payda)
        assert "CAPA_BAYAT_EKSENLER: YOK" in cikti, "capa bayat ekseni VAR"
        return "V1 rc=0 MUTANT=%d/%d YAMA_TUTMADI=0 CAPA_BAYAT=YOK" % (pay, payda)
    finally:
        _sandbox_sil(sandbox)


def vaka_k316_v2_motor_aritesi_tek_kaynaktan_turer():
    """K316/V2 vaka 8: KAT_MEKANIK beklentisi ARITE KURALIYLA turer.

    6 Eyl motor kararindan sonra canli kume TEKE indi; batarya `motorlar[1]`
    indeksini SABIT tuttugu icin `IndexError` ile COKUYORDU (olculdu 16 Eyl:
    VAKA=51 DUSEN=4, dusen biri buydu). Kaynak (nobet-kapi.py) bu hali ZATEN
    dogru ele aliyor; ayrisan taraf OLCEN taraftir.
    """
    sandbox = _sandbox_kur()
    try:
        rc, cikti = _kos(sandbox, "nobet-kabul-test.py")
        hukum = _vaka_hukmu(cikti, "8 sessiz-hata sinifi")
        assert hukum == "YESIL", "vaka 8 hukmu=%s\n%s" % (hukum, cikti[-1200:])
        assert "MOTOR_SAYISI=" in cikti, "motor sayisi ADIYLA basilmadi"
        assert "KAT_AYRIMI=" in cikti, "kat ayrimi ADIYLA basilmadi"
        return "vaka 8 YESIL · motor sayisi + kat ayrimi ADIYLA basiliyor (rc=%d)" % rc
    finally:
        _sandbox_sil(sandbox)


def mutant_k316_v2_arite_kolu():
    """MUTANT (hedef kol: nobet-kapi.py `KAT_MEKANIK` ARITE GERI DUSUSU).

    Tek motorlu kumede `KAT_MEKANIK = KAT_TARAMA` geri dususu OLDURULUNCE
    vaka 8 KIRMIZI yanmalidir. Oldurmeyen bir vaka o kolu OLCMUYOR demektir.
    """
    sandbox = _sandbox_kur()
    try:
        _mutant_uygula(
            sandbox, "nobet-kapi.py",
            "KAT_MEKANIK = CANLI_ISCI_MOTORLARI[1] if len(CANLI_ISCI_MOTORLARI) > 1 else KAT_TARAMA",
            "KAT_MEKANIK = CANLI_ISCI_MOTORLARI[1] if len(CANLI_ISCI_MOTORLARI) > 1 else None")
        _, cikti = _kos(sandbox, "nobet-kabul-test.py")
        hukum = _vaka_hukmu(cikti, "8 sessiz-hata sinifi")
        assert hukum == "KIRMIZI", (
            "MUTANT OLMEDI: arite geri dususu oldurulunce vaka 8 hukmu=%s" % hukum)
        return "M-ARITE oldu: KAT_MEKANIK geri dususu olunce vaka 8 KIRMIZI"
    finally:
        _sandbox_sil(sandbox)


def vaka_k316_v2_el_kitabi_ureticisi_kapatir():
    """K316/V2 vaka 19+41: el kitabi kat sutunu URETICIYLE kapanir.

    Duz metin degistirmek YASAK (kalem: tekil yama). Sinif onarimi ZATEN
    kurulu: `nobet-kapi.py --el-kitabi-uret`. Bu vaka onu SANDBOX kopyasinda
    kosar ve iki vakanin KIRMIZI -> YESIL gectigini olcer; canli dosyaya
    DOKUNULMAZ. KONTROL: uretici IDEMPOTENT (ikinci kosumda DEGISEN=0).
    """
    sandbox = _sandbox_kur()
    try:
        _, once = _kos(sandbox, "nobet-kabul-test.py")
        once_19 = _vaka_hukmu(once, "19 el kitabi")
        once_41 = _vaka_hukmu(once, "41 el kitabi kat sutunu URETILIR")
        assert once_19 == "KIRMIZI" and once_41 == "KIRMIZI", (
            "TABAN BEKLENTISI TUTMADI: 19=%s 41=%s (uretici zaten kosulmus olabilir)"
            % (once_19, once_41))

        rc_uret, uret = _kos(sandbox, "nobet-kapi.py", "--el-kitabi-uret")
        assert rc_uret == 0, "uretici rc=%d\n%s" % (rc_uret, uret[-800:])
        degisen = _sayi(uret, "DEGISEN")
        assert degisen and degisen > 0, "uretici hicbir hucreyi ONARMADI: %s" % uret

        rc_iki, tekrar_uret = _kos(sandbox, "nobet-kapi.py", "--el-kitabi-uret")
        assert rc_iki == 0 and _sayi(tekrar_uret, "DEGISEN") == 0, (
            "uretici IDEMPOTENT degil: %s" % tekrar_uret)

        _, sonra = _kos(sandbox, "nobet-kabul-test.py")
        sonra_19 = _vaka_hukmu(sonra, "19 el kitabi")
        sonra_41 = _vaka_hukmu(sonra, "41 el kitabi kat sutunu URETILIR")
        assert sonra_19 == "YESIL" and sonra_41 == "YESIL", (
            "uretici kostu ama vakalar kapanmadi: 19=%s 41=%s" % (sonra_19, sonra_41))
        dusen_once, dusen_sonra = _sayi(once, "DUSEN"), _sayi(sonra, "DUSEN")
        return ("uretici: DEGISEN=%d · vaka 19+41 KIRMIZI->YESIL · DUSEN %s->%s "
                "· idempotent" % (degisen, dusen_once, dusen_sonra))
    finally:
        _sandbox_sil(sandbox)


def kontrol_canli_dosyaya_yazilmadi():
    """KONTROL: batarya `~/.claude/cron` altina TEK BAYT yazmaz.

    Canli dizin YOKSA (CI) bu eksen ADIYLA OLCULEMEDI basar — sessiz yesil YOK.
    """
    canli = os.path.expanduser("~/.claude/cron")
    if not os.path.isdir(canli):
        return "OLCULEMEDI: canli cron dizini YOK (CI) — bu evde yazma riski de YOK"
    hedef = os.path.join(canli, "onarim-el-kitabi.md")
    if not os.path.exists(hedef):
        return "OLCULEMEDI: canli el kitabi YOK"
    once = os.path.getmtime(hedef)
    sandbox = _sandbox_kur()
    try:
        _kos(sandbox, "nobet-kapi.py", "--el-kitabi-uret")
    finally:
        _sandbox_sil(sandbox)
    assert os.path.getmtime(hedef) == once, (
        "🔴 SANDBOX KOSUMU CANLI EL KITABINA YAZDI (mtime degisti)")
    return "canli el kitabi mtime DEGISMEDI (sandbox izolasyonu tuttu)"


def kontrol_sandbox_temizlendi():
    """KONTROL: ureten temizler — sandbox is bitince diskte KALMAZ."""
    sandbox = _sandbox_kur()
    yol = sandbox
    _sandbox_sil(sandbox)
    assert not os.path.exists(yol), "sandbox diskte KALDI: %s" % yol
    assert not _SANDBOXLAR, "izlenen sandbox listesi bos degil: %s" % _SANDBOXLAR
    return "sandbox silindi · izlenen liste bos"


# --- W2-2 yardimcilari -----------------------------------------------------

def _gozcu_senaryo(sandbox, senaryo):
    """Kumda GERCEK bir gozcu turu kosar (kuru DEGIL); kalbin alanlarini doner."""
    yol = os.path.join(sandbox, "senaryo.json")
    with open(yol, "w", encoding="utf-8") as dosya:
        json.dump(senaryo, dosya, ensure_ascii=False)
    rc, cikti = _kos(sandbox, PROB_ADI, "gozcu", yol)
    esles = re.search(r"^PROB_KALP (.+)$", cikti, re.MULTILINE)
    assert rc == 0 and esles, "gozcu probu dustu rc=%d\n%s" % (rc, cikti[-1500:])
    kalp = json.loads(esles.group(1))
    kosucu = json.loads(re.search(r"^PROB_KOSUCU (.+)$", cikti, re.MULTILINE).group(1))
    return kalp, kosucu


def _kabuk():
    """ci-nobeti.sh zsh betigidir; CI kosucusunda zsh yoksa bash (soz dizimi uyumlu)."""
    return shutil.which("zsh") or shutil.which("bash")


def _ci_nobeti(sandbox):
    """GERCEK ci-nobeti.sh -> GERCEK `nobet-tetik.py --karar`. Doner (rc, log)."""
    log = os.path.join(sandbox, "ci-nobeti.log")
    ortam = dict(os.environ)
    ortam.update({
        "PRUVO_CRON_KOKU": sandbox, "PRUVO_EV_KOKU": EV_KOKU,
        "PRUVO_NOBET_KOK": sandbox, "PRUVO_NOBET_LOG": log,
        "PRUVO_NOBET_EV": sandbox,
        "PRUVO_NOBET_TETIK": os.path.join(sandbox, "nobet-tetik.py"),
        "PRUVO_NOBET_KAPI": os.path.join(sandbox, "nobet-kapi.py"),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    once = ""
    if os.path.exists(log):
        with open(log, encoding="utf-8") as dosya:
            once = dosya.read()
    sonuc = subprocess.run([_kabuk(), os.path.join(sandbox, "ci-nobeti.sh")],
                           cwd=sandbox, env=ortam, capture_output=True, text=True,
                           timeout=300)
    with open(log, encoding="utf-8") as dosya:
        yeni = dosya.read()[len(once):]
    return sonuc.returncode, yeni + (sonuc.stderr or "")


def _damga_var(sandbox, onek):
    dizin = os.path.join(sandbox, "gozcu-kilit")
    try:
        return sorted(a for a in os.listdir(dizin) if a.startswith(onek)
                      and a.endswith(".tuketildi"))
    except OSError:
        return []


def _kosum(kimlik, ad, sonuc):
    return {"databaseId": kimlik, "name": ad, "conclusion": sonuc,
            "status": "completed", "headBranch": "main",
            "headSha": "", "createdAt": ""}


# Gunluk tur borcu VAR + dagitilabilir TEK kalem -> gozcu DEFTER_DAGITIM kosar.
_DAGITIM_DEFTERI = "\n".join([
    "| id | tarih | kimden→kime | iş (tek cümle) | durum | kapanış kanıtı |",
    "|---|---|---|---|---|---|",
    "| K01 | 2026-09-18 | KraL→Tamirci | 🔧 tarama kök neden bulunacak | 🔧 | — |",
])


def _k334_dagitim_senaryosu():
    return {"defter": _DAGITIM_DEFTERI, "kosumlar": [],
            "durum": {"taban_alindi": True}}


def _k334_zinciri(sandbox):
    """Gozcu DEFTER_DAGITIM turu + gunluk borc -> ci-nobeti. Doner (kalp, rc, log)."""
    kalp, kosucu = _gozcu_senaryo(sandbox, _k334_dagitim_senaryosu())
    assert kalp["tetik"] == "DEFTER_DAGITIM" and kalp["gunluk_gerekli"], (
        "FIKSTUR ISIRMADI: gozcu DEFTER_DAGITIM+gunluk uretmedi: %s" % kalp)
    assert kosucu == [["--tur-kapat"]], "gozcu turu kosulmadi: %s" % kosucu
    rc, log = _ci_nobeti(sandbox)
    return kalp, rc, log


# --- K334 ---------------------------------------------------------------------

def vaka_k334_gunluk_kolu_fiilen_kosar():
    """K334 ①: gozcu BASKA bir tur (DEFTER_DAGITIM) actiginda 5. kol GUNLUK_DEFTER
    GERCEK ci-nobeti.sh -> nobet-tetik --karar zincirinde FIILEN ateslenir.

    TABAN (onarimdan ONCE, 27 Agu olcumu): 3. basamak BLANKET idi; bu kalpte
    `sebep=GOZCU_ICRA_ETTI` + `tetik_karari=ACMA` -> kol ULASILAMAZ.
    Kuru kosum DEGIL: damga (`gunluk_<gun>.tuketildi`) GERCEKTEN yazilir.
    """
    sandbox = _sandbox_kur()
    try:
        kalp, rc, log = _k334_zinciri(sandbox)
        assert kalp["icra_anahtar"].startswith("dagitim:"), kalp
        assert "TUR ACILIYOR sebep=GUNLUK_DEFTER" in log, (
            "5. kol ATESLENMEDI:\n%s" % log[-800:])
        assert re.search(r"TETIK_HUKMU tetik_rc=0 .*tetik_karari=AC\b", log), log[-800:]
        assert re.search(r"BITIS rc=0 ===", log), log[-800:]
        damga = _damga_var(sandbox, "gunluk_")
        assert len(damga) == 1, "gunluk damgasi yazilmadi: %s" % damga
        assert rc == 0, "ci-nobeti rc=%d" % rc
        return ("gozcu=%s -> TUR ACILIYOR sebep=GUNLUK_DEFTER · tetik_rc=0 · "
                "BITIS rc=0 · damga=%s" % (kalp["icra_anahtar"], damga[0]))
    finally:
        _sandbox_sil(sandbox)


def kontrol_k334_ayni_anahtar_iki_kez_acilmaz():
    """K334 ③ KONTROL: cift atesleme yasagi GOREVINI yapiyor.

    (a) gozcu GUNLUK_DEFTER turunu KENDI acti -> tetik AYNI anahtar icin ACMA
        (`GOZCU_ICRA_ETTI`, damga YOK).
    (b) K334 zincirinden sonra ikinci ci-nobeti turu -> `_TUKETILDI`, yeni tur YOK.
    (c) eski kalp (`icra_anahtar` alani YOK) -> BLANKET kol korunur.
    """
    sandbox = _sandbox_kur()
    try:
        kalp, kosucu = _gozcu_senaryo(sandbox, {"defter": "", "kosumlar": [],
                                                "durum": {"taban_alindi": True}})
        assert kalp["tetik"] == "GUNLUK_DEFTER" and kosucu == [["--tur"]], kalp
        assert kalp["icra_anahtar"].startswith("gunluk:"), kalp
        rc_a, log_a = _ci_nobeti(sandbox)
        assert "TUR ACILMADI sebep=GOZCU_ICRA_ETTI" in log_a, log_a[-800:]
        assert _damga_var(sandbox, "gunluk_") == [], "ayni anahtar IKINCI kez tuketildi"
        assert rc_a == 0, rc_a
    finally:
        _sandbox_sil(sandbox)
    sandbox = _sandbox_kur()
    try:
        _k334_zinciri(sandbox)
        _rc, log_b = _ci_nobeti(sandbox)
        assert "TUR ACILMADI sebep=GUNLUK_DEFTER_TUKETILDI" in log_b, log_b[-800:]
        assert len(_damga_var(sandbox, "gunluk_")) == 1
        # (c) eski kalp: alan cikarilir, ayni kalp -> BLANKET ACMA
        yol = os.path.join(sandbox, "gozcu-kalp.json")
        with open(yol, encoding="utf-8") as dosya:
            kalp_c = json.load(dosya)
        kalp_c.pop("icra_anahtar", None)
        with open(yol, "w", encoding="utf-8") as dosya:
            json.dump(kalp_c, dosya)
        shutil.rmtree(os.path.join(sandbox, "gozcu-kilit"), ignore_errors=True)
        _rc, log_c = _ci_nobeti(sandbox)
        assert "TUR ACILMADI sebep=GOZCU_ICRA_ETTI" in log_c, log_c[-800:]
    finally:
        _sandbox_sil(sandbox)
    return ("(a) gozcu gunluk:<gun> acti -> ACMA GOZCU_ICRA_ETTI, damga 0 · "
            "(b) 2. tur _TUKETILDI · (c) alansiz eski kalp BLANKET")


def mutant_k334_merdiven_eski_sira():
    """K334 ② MUTANT (hedef kol: `nobet-tetik.karar()` 3. basamak anahtar ekseni).

    `ayni_tur_mu` kosulu `True`ya cevrilir (= eski BLANKET merdiven). Vaka
    ayni zincirde KIRMIZI yanmali ve kirmizinin SEBEBI blanket kol olmali
    (`sebep=GOZCU_ICRA_ETTI`) — baska bir kolun dusmesi atif SAYILMAZ.
    """
    sandbox = _sandbox_kur()
    try:
        _mutant_uygula(sandbox, "nobet-tetik.py",
                       "        if ayni_tur_mu(kalp, bugun):",
                       "        if True:")
        _kalp, _rc, log = _k334_zinciri(sandbox)
        assert "TUR ACILIYOR sebep=GUNLUK_DEFTER" not in log, "MUTANT OLMEDI"
        assert "TUR ACILMADI sebep=GOZCU_ICRA_ETTI" in log, (
            "ATIF SAPTI: kol baska sebeple sustu:\n%s" % log[-600:])
        return "M-K334-SIRA oldu: blanket merdivende 5. kol ULASILAMAZ (sebep=GOZCU_ICRA_ETTI)"
    finally:
        _sandbox_sil(sandbox)


def mutant_k334_gozcu_anahtar_yazmaz():
    """K334 MUTANT (hedef kol: gozcu kalbine `icra_anahtar` YAZIMI).

    Alan yazilmazsa tetik eski kalp sanir ve BLANKET'e duser -> zincir KIRMIZI.
    Kablonun iki ucu (yazan gozcu, okuyan tetik) AYRI olculur.
    """
    sandbox = _sandbox_kur()
    try:
        _mutant_uygula(sandbox, "gozcu.py",
                       '        "icra_anahtar": icra_anahtari(',
                       '        "icra_anahtar_KOPUK": icra_anahtari(')
        kalp, kosucu = _gozcu_senaryo(sandbox, _k334_dagitim_senaryosu())
        assert kalp["icra_anahtar"] == "<YOK>", kalp
        _rc, log = _ci_nobeti(sandbox)
        assert "TUR ACILIYOR sebep=GUNLUK_DEFTER" not in log, "MUTANT OLMEDI"
        assert "sebep=GOZCU_ICRA_ETTI" in log, "ATIF SAPTI:\n%s" % log[-600:]
        return "M-K334-KABLO oldu: gozcu anahtar yazmayinca tetik BLANKET'e dustu"
    finally:
        _sandbox_sil(sandbox)


# --- K326 + K311 YUZ B ------------------------------------------------------

_ESKALE_100 = {"taban_alindi": True,
               "kosumlar": {"100": {"durum": "ESKALASYON", "deneme": 3, "ad": "A"}}}


def _k326_senaryolari():
    return {
        # eskale kirmizi 100'un ARDILI 101 success -> cozulmus
        "ARDIL": {"kosumlar": [_kosum(101, "A", "success"), _kosum(100, "A", "failure")],
                  "durum": _ESKALE_100, "gunluk_yapildi": True},
        # ters yon: success 99'dan SONRA failure 100 -> DURAN kirmizi
        "DURAN": {"kosumlar": [_kosum(100, "A", "failure"), _kosum(99, "A", "success")],
                  "durum": _ESKALE_100, "gunluk_yapildi": True},
        # iptal ARDIL DEGIL
        "IPTAL": {"kosumlar": [_kosum(101, "A", "cancelled"), _kosum(100, "A", "failure")],
                  "durum": _ESKALE_100, "gunluk_yapildi": True},
    }


def _k326_kos(sandbox, ad):
    kalp, _ = _gozcu_senaryo(sandbox, _k326_senaryolari()[ad])
    rc, log = _ci_nobeti(sandbox)
    return kalp, rc, log


def vaka_k326_ardilli_kirmizi_duran_sayilmaz():
    """K326 + K311 YUZ B: ardili SUCCESS olan kirmizi seviye/eskalasyon URETMEZ.

    CANLI TABAN (18 Eyl): run 35323115483 ESKALASYON, ardili 35328100912
    success; `eskalasyon_acik` yine de 1 kaldi ve ci-nobeti 163 tur
    `HUKUM=ESKALASYON_ACIK rc=1` basti — kosum pencereden dusene kadar.
    Pencere sayaci SILINMEDI: `kirmizi_toplam=1` yan yana basilir.
    """
    sandbox = _sandbox_kur()
    try:
        kalp, rc, log = _k326_kos(sandbox, "ARDIL")
        assert kalp["kirmizi_toplam"] == 1, "PENCERE ekseni silinmis: %s" % kalp
        assert kalp["kirmizi_ardilsiz"] == 0, kalp
        assert kalp["eskalasyon_acik"] == 0, "K311 YUZ B: ardilli eskalasyon ACIK: %s" % kalp
        assert "TUR ACILMADI sebep=YESIL" in log, log[-600:]
        assert rc == 0 and "HUKUM=TEMIZ" in log, "rc=%d\n%s" % (rc, log[-600:])
        return ("ardil success -> pencere=1 ardilsiz=0 eskalasyon_acik=0 · "
                "ci-nobeti HUKUM=TEMIZ rc=0")
    finally:
        _sandbox_sil(sandbox)


def vaka_k326_duran_kirmizi_gorunur():
    """K326 ters yon (kenar-tetikli korluk GERI GELMEZ): ardili OLMAYAN kirmizi
    seviye KIRMIZISI uretir; iptal edilen kosum ardil SAYILMAZ."""
    sandbox = _sandbox_kur()
    try:
        kalp, rc, log = _k326_kos(sandbox, "DURAN")
        assert kalp["kirmizi_ardilsiz"] == 1 and kalp["eskalasyon_acik"] == 1, kalp
        assert "sebep=SEVIYE_KIRMIZI_1" in log and rc == 1, "rc=%d\n%s" % (rc, log[-600:])
    finally:
        _sandbox_sil(sandbox)
    sandbox = _sandbox_kur()
    try:
        kalp_i, rc_i, _log = _k326_kos(sandbox, "IPTAL")
        assert kalp_i["kirmizi_ardilsiz"] == 1, "iptal ARDIL sayildi: %s" % kalp_i
        assert rc_i == 1, rc_i
    finally:
        _sandbox_sil(sandbox)
    return "duran kirmizi -> ardilsiz=1 eskalasyon=1 SEVIYE_KIRMIZI_1 rc=1 · iptal ardil DEGIL"


def vaka_k326_f2_f3_ayri():
    """K326: F2 (11 duran kirmizi) ile F3 (0 kirmizi) AYRI cikti; F4 DEGISMEZ."""
    sandbox = _sandbox_kur()
    try:
        kosumlar = [_kosum(200 + i, "IS-%02d" % i, "failure") for i in range(11)]
        kalp, _ = _gozcu_senaryo(sandbox, {"kosumlar": kosumlar, "gunluk_yapildi": True,
                                           "durum": {"taban_alindi": True, "kosumlar": {
                                               str(200 + i): {"durum": "TABAN", "deneme": 0}
                                               for i in range(11)}}})
        rc_f2, log_f2 = _ci_nobeti(sandbox)
        assert kalp["kirmizi_ardilsiz"] == 11, kalp
        assert "sebep=SEVIYE_KIRMIZI_11" in log_f2 and rc_f2 == 1, log_f2[-600:]
    finally:
        _sandbox_sil(sandbox)
    sandbox = _sandbox_kur()
    try:
        _gozcu_senaryo(sandbox, {"kosumlar": [], "gunluk_yapildi": True,
                                 "durum": {"taban_alindi": True}})
        rc_f3, log_f3 = _ci_nobeti(sandbox)
        assert "sebep=YESIL" in log_f3 and rc_f3 == 0, log_f3[-600:]
        # F4 DEGISMEZ: nobet-tetik-test S5 ("gercek YENI kirmizi -> TUR
        # ACILIR") bu bataryanin icinde; rc=0 ise S5 dahil hepsi yesil.
        rc_t, cikti_t = _kos(sandbox, "nobet-tetik-test.py")
        assert rc_t == 0, cikti_t[-800:]
    finally:
        _sandbox_sil(sandbox)
    return "F2 rc=1 SEVIYE_KIRMIZI_11 · F3 rc=0 YESIL · F4 (nobet-tetik-test S5) YESIL"


def mutant_k326_pencereye_geri():
    """K326 MUTANT (hedef kol: gozcu `ardilsiz_kirmizilar` ekseni -> pencere).

    Ardilsiz kume pencere kumesine esitlenince ARDIL vakasi KIRMIZI yanar ve
    atif alanlarda gorunur: `kirmizi_ardilsiz=1` + `eskalasyon_acik=1`.
    """
    sandbox = _sandbox_kur()
    try:
        _mutant_uygula(sandbox, "gozcu.py",
                       "    ardilsiz = ardilsiz_kirmizilar(ham_kosumlar or [])",
                       "    ardilsiz = kirmizilar")
        kalp, rc, _log = _k326_kos(sandbox, "ARDIL")
        assert kalp["kirmizi_ardilsiz"] == 1 and kalp["eskalasyon_acik"] == 1, (
            "MUTANT OLMEDI: %s" % kalp)
        assert rc == 1, rc
        return "M-K326-PENCERE oldu: ardilli kirmizi yine sayildi (eskalasyon_acik=1, rc=1)"
    finally:
        _sandbox_sil(sandbox)


def mutant_k326_kor_goz():
    """K326 MUTANT (ters yon, hedef kol: ardilsiz kume BOS) — duran kirmizi
    gorunmez olursa DURAN vakasi KIRMIZI yanmali (daraltma tek basina YASAK)."""
    sandbox = _sandbox_kur()
    try:
        _mutant_uygula(sandbox, "gozcu.py",
                       "    ardilsiz = ardilsiz_kirmizilar(ham_kosumlar or [])",
                       "    ardilsiz = []")
        kalp, rc, log = _k326_kos(sandbox, "DURAN")
        assert "sebep=SEVIYE_KIRMIZI_1" not in log, "MUTANT OLMEDI"
        assert kalp["kirmizi_ardilsiz"] == 0 and rc == 0, (kalp, rc)
        return "M-K326-KOR oldu: duran kirmizi YESIL gorundu (ters yon korlugu yakalandi)"
    finally:
        _sandbox_sil(sandbox)


def mutant_k326_tetik_pencere_okur():
    """K326 MUTANT (hedef kol: tetik `seviye_kirmizisi` alan secimi)."""
    sandbox = _sandbox_kur()
    try:
        _mutant_uygula(
            sandbox, "nobet-tetik.py",
            '    alan = "kirmizi_ardilsiz" if "kirmizi_ardilsiz" in kalp else "kirmizi_toplam"',
            '    alan = "kirmizi_toplam"')
        _kalp, rc, log = _k326_kos(sandbox, "ARDIL")
        assert "sebep=SEVIYE_KIRMIZI_1" in log and rc == 1, "MUTANT OLMEDI:\n%s" % log[-500:]
        return "M-K326-TETIK oldu: tetik pencereyi okuyunca ardilli kirmizi SEVIYE_KIRMIZI_1"
    finally:
        _sandbox_sil(sandbox)


# --- K325 ---------------------------------------------------------------------

def vaka_k325_sature_ve_tuketici():
    """K325: nobet-kabul-test vaka 43 (esikte saturasyon + tuketici davranisi)."""
    sandbox = _sandbox_kur()
    try:
        _, cikti = _kos(sandbox, "nobet-kabul-test.py")
        hukum = _vaka_hukmu(cikti, "43 ustuste sayac SATURE")
        assert hukum == "YESIL", "vaka 43 hukmu=%s\n%s" % (hukum, cikti[-900:])
        return "vaka 43 YESIL (esik alti satirsiz · esikte SATURE=1 · +3 tur sabit)"
    finally:
        _sandbox_sil(sandbox)


def _k325_mutant(eski, yeni, beklenen_parca):
    sandbox = _sandbox_kur()
    try:
        _mutant_uygula(sandbox, "nobet-kapi.py", eski, yeni)
        _, cikti = _kos(sandbox, "nobet-kabul-test.py")
        satir = [s for s in cikti.splitlines() if "43 ustuste sayac SATURE" in s]
        assert satir and satir[0].startswith("KIRMIZI"), "MUTANT OLMEDI: %s" % satir
        assert beklenen_parca in satir[0], "ATIF SAPTI: %s" % satir[0][:200]
        return satir[0][:120]
    finally:
        _sandbox_sil(sandbox)


def mutant_k325_tuketici():
    """K325 MUTANT (hedef kol: tuketicinin esik karari) -> (a) KIRMIZI."""
    _k325_mutant("    if ustuste_onarimsiz >= USTUSTE_ONARIMSIZ_ESIGI:",
                 "    if False:", "(a) esikte tuketici SUSTU")
    return "M-K325-TUKETICI oldu: esikte satir basilmayinca vaka 43 (a) KIRMIZI"


def mutant_k325_saturasyon():
    """K325 MUTANT (hedef kol: saturasyon) -> sinirsiz +1 -> (b) KIRMIZI."""
    _k325_mutant("    return max(onceki, min(onceki + 1, USTUSTE_ONARIMSIZ_ESIGI))",
                 "    return onceki + 1", "(b) sayac esikte SATURE OLMADI")
    return "M-K325-SATURE oldu: sinirsiz +1'de vaka 43 (b) KIRMIZI"


# --- K311 (b) -----------------------------------------------------------------

_SOZLUK_DEFTERI = "\n".join([
    "| id | tarih | kimden→kime | iş (tek cümle) | durum | kapanış kanıtı |",
    "|---|---|---|---|---|---|",
    "| K01 | 2026-09-18 | KraL→Tamirci | a | ACIK | — |",
    "| K02 | 2026-09-18 | KraL→Tamirci | b | 🔧 | — |",
    "| K03 | 2026-09-18 | KraL→Tamirci | c | UCUSTA | — |",
    "| K04 | 2026-09-18 | KraL→Okan | d | OKAN-KAPISI | — |",
    "| K05 | 2026-09-18 | KraL→Tamirci | e | KAPANDI | — |",
])


def vaka_k311b_iki_okuyucu_ayni_tur():
    """K311 (b): durum sozlugu TEK KAYNAKTAN; IKINCI okuyucu AYNI turda olculur.

    Canli taban (18 Eyl, ayni tur): nobet-kapi 13 onarilacak + 3 sahipli =
    parti-borc 16 acik, AYRISMA=0 — 26 Agu `ACIK_KALEM=0` arizasi KAPANMIS.
    Bu vaka fiksturde BES kanonik degerin her biriyle iki okuyucunun ayni
    kumeyi sectigini VE sozlugun parti-borc'tan olculdugunu dogrular.
    """
    sandbox = _sandbox_kur()
    try:
        yol = os.path.join(sandbox, "defter.md")
        with open(yol, "w", encoding="utf-8") as dosya:
            dosya.write(_SOZLUK_DEFTERI + "\n")
        rc, cikti = _kos(sandbox, PROB_ADI, "sozluk", yol)
        esles = re.search(r"^PROB_SOZLUK (.+)$", cikti, re.MULTILINE)
        assert rc == 0 and esles, "sozluk probu dustu rc=%d\n%s" % (rc, cikti[-1200:])
        s = json.loads(esles.group(1))
        assert s["kaynak"] == "parti-borc-kapisi.KANONIK_DURUMLAR", s
        assert s["pb_okundu"] and s["pb_gecersiz"] == 0 and s["bilinmeyen"] == 0, s
        assert s["nk"] == s["pb"] == ["K01", "K02", "K03", "K04"], s
        return "kaynak=parti-borc · iki okuyucu ayni 4 acik (K01-K04), KAPANDI disarida"
    finally:
        _sandbox_sil(sandbox)


def _sahte_ev(parti_borc_degistir=None):
    """Gecici EV: tools/{parti-borc-kapisi,mimar_kimlik}.py kopyasi (mutant icin)."""
    ev = tempfile.mkdtemp(prefix="nobet-onarim-kabul-ev-")
    _SANDBOXLAR.append(ev)
    os.makedirs(os.path.join(ev, "tools"))
    for ad in ("parti-borc-kapisi.py", "mimar_kimlik.py"):
        shutil.copy2(os.path.join(EV_KOKU, "tools", ad), os.path.join(ev, "tools", ad))
    if parti_borc_degistir:
        eski, yeni = parti_borc_degistir
        yol = os.path.join(ev, "tools", "parti-borc-kapisi.py")
        with open(yol, encoding="utf-8") as dosya:
            metin = dosya.read()
        assert metin.count(eski) == 1, "MUTANT CAPASI TEKIL DEGIL: %s" % eski
        with open(yol, "w", encoding="utf-8") as dosya:
            dosya.write(metin.replace(eski, yeni))
    return ev


def _nobet_kapi_yukle_ev(sandbox, ev):
    ortam = dict(os.environ, PRUVO_CRON_KOKU=sandbox, PRUVO_EV_KOKU=ev,
                 PYTHONDONTWRITEBYTECODE="1")
    kod = ("import sys; sys.path.insert(0, %r); import importlib.util as u; "
           "s = u.spec_from_file_location('nk', %r); m = u.module_from_spec(s); "
           "s.loader.exec_module(m); print('KAYNAK=' + m.SOZLUK_KAYNAGI)"
           % (sandbox, os.path.join(sandbox, "nobet-kapi.py")))
    sonuc = subprocess.run([sys.executable, "-c", kod], cwd=sandbox, env=ortam,
                           capture_output=True, text=True, timeout=120)
    return sonuc.returncode, (sonuc.stdout or "") + (sonuc.stderr or "")


def mutant_k311b_yeni_durum_sessiz_kalmaz():
    """K311 (b) MUTANT: tek kaynaga YENI bir durum degeri eklenir -> nobet-kapi
    YUKLEMEDE KORGOZ_K311_SOZLUK ile patlar (sessizce BILINMIYOR saymaz).
    KONTROL: degistirilmemis kopya EV'de ayni yukleme YESIL (kaynak=parti-borc)
    — yani olum mutasyona atfedilir, kopya EV'in eksikligine DEGIL."""
    sandbox = _sandbox_kur()
    try:
        ev_k = _sahte_ev()
        rc_k, cikti_k = _nobet_kapi_yukle_ev(sandbox, ev_k)
        assert rc_k == 0 and "KAYNAK=parti-borc-kapisi.KANONIK_DURUMLAR" in cikti_k, (
            "KONTROL KIRMIZI (kopya EV yuklenmedi):\n%s" % cikti_k[-800:])
        _sandbox_sil(ev_k)
        ev_m = _sahte_ev(("KANONIK_DURUMLAR = ACIK_DURUMLAR | frozenset({KAPALI_DURUM})",
                          "KANONIK_DURUMLAR = ACIK_DURUMLAR | frozenset({KAPALI_DURUM, 'ASKIDA'})"))
        rc_m, cikti_m = _nobet_kapi_yukle_ev(sandbox, ev_m)
        _sandbox_sil(ev_m)
        assert rc_m != 0 and "KORGOZ_K311_SOZLUK" in cikti_m and "ASKIDA" in cikti_m, (
            "MUTANT OLMEDI rc=%d\n%s" % (rc_m, cikti_m[-800:]))
        return "M-K311b oldu: tek kaynaga 'ASKIDA' eklenince yukleme RED (KONTROL YESIL)"
    finally:
        _sandbox_sil(sandbox)


# --- K316 vaka 6 + batarya butunu -------------------------------------------

def _kabul_tam(sandbox):
    rc_u, _ = _kos(sandbox, "nobet-kapi.py", "--el-kitabi-uret")
    assert rc_u == 0, "uretici rc=%d" % rc_u
    return _kos(sandbox, "nobet-kabul-test.py")


def vaka_k316_kabul_bataryasi_tam_yesil():
    """K316 ②+⑤: nobet-kabul-test rc=0 · DUSEN=0 · VAKA>=46 · vaka 6 YESIL ·
    K316 mutanti 1/1 — ve IKI ARDISIK kosumda ozet satiri BIREBIR.

    TABAN (18 Eyl, onarimdan ONCE, canliyla birebir kopya): `VAKA=51 DUSEN=2
    ... K316_MUTANT_KIRMIZI=0/1 RC=1` (vaka 6 + mutant capasi `EV_KOKU`
    env'e gecince 0 kez; vaka 35 sahte anahtarsiz kum artifakti).
    """
    sandbox = _sandbox_kur()
    try:
        rc1, c1 = _kabul_tam(sandbox)
        _, c2 = _kos(sandbox, "nobet-kabul-test.py")
        ozet1 = [s for s in c1.splitlines() if s.startswith("VAKA=")]
        ozet2 = [s for s in c2.splitlines() if s.startswith("VAKA=")]
        assert rc1 == 0, "rc=%d\n%s" % (rc1, "\n".join(
            s for s in c1.splitlines() if s.startswith(("KIRMIZI", "MUTASYON")))[:1500])
        assert _sayi(c1, "DUSEN") == 0 and (_sayi(c1, "VAKA") or 0) >= 46, ozet1
        assert _vaka_hukmu(c1, "6 3. turda ESKALASYON=OKAN") == "YESIL"
        assert "K316_MUTANT_KIRMIZI=1/1" in c1, ozet1
        assert ozet1 and ozet1 == ozet2, "iki kosum AYRISTI: %s != %s" % (ozet1, ozet2)
        return ozet1[0]
    finally:
        _sandbox_sil(sandbox)


def mutant_k316_vaka6_goce_geri():
    """K316 vaka 6 MUTANT (hedef: vaka 6 fiksturunun kati): emekli ada geri
    donunce vaka 6 KIRMIZI yanmali ve metni `yine dagitildi` tasimali."""
    sandbox = _sandbox_kur()
    try:
        _mutant_uygula(sandbox, "nobet-kabul-test.py",
                       '"tur": 1, "kat": FIKSTUR_KAT,',
                       '"tur": 1, "kat": GOC_OZNESI_KAT,')
        _, cikti = _kabul_tam(sandbox)
        satir = [s for s in cikti.splitlines() if "6 3. turda ESKALASYON=OKAN" in s]
        assert satir and satir[0].startswith("KIRMIZI"), "MUTANT OLMEDI: %s" % satir
        assert "yine dagitildi" in satir[0], "ATIF SAPTI: %s" % satir[0][:160]
        return "M-K316-V6 oldu: emekli kat -> goc -> 'eskale kalem yine dagitildi'"
    finally:
        _sandbox_sil(sandbox)


def vaka_tetik_bataryalari_yesil():
    """Mevcut nobet-tetik-test + curutucu KUMDA yesil (W2-2 onlari bozmadi).

    Curutucu tabani (18 Eyl): `MUTANT=2/3 YAMA_TUTMADI=1` — MA capasi yorum
    satiri tasiyordu; capa yalniz KOD'a baglandi -> 3/3.
    """
    sandbox = _sandbox_kur()
    try:
        rc_t, c_t = _kos(sandbox, "nobet-tetik-test.py")
        rc_m, c_m = _kos(sandbox, "nobet-tetik-mutasyon.py")
        assert rc_t == 0 and _sayi(c_t, "DUSEN") == 0, c_t[-800:]
        assert rc_m == 0 and "MUTANT=3/3" in c_m and "YAMA_TUTMADI=0" in c_m, c_m[-800:]
        return "nobet-tetik-test VAKA=%s DUSEN=0 · curutucu MUTANT=3/3 YAMA_TUTMADI=0" % (
            _sayi(c_t, "VAKA"))
    finally:
        _sandbox_sil(sandbox)


VAKALAR = (
    ("K316/V1 capa bayatligi", vaka_k316_v1_capa_bayatligi_kapandi),
    ("K316/V2 motor aritesi", vaka_k316_v2_motor_aritesi_tek_kaynaktan_turer),
    ("K316/V2 MUTANT arite", mutant_k316_v2_arite_kolu),
    ("K316/V2 el kitabi uretici", vaka_k316_v2_el_kitabi_ureticisi_kapatir),
    ("K316 batarya tam+2 kosum", vaka_k316_kabul_bataryasi_tam_yesil),
    ("K316 MUTANT vaka6 goce", mutant_k316_vaka6_goce_geri),
    ("K334 gunluk kolu FIILEN", vaka_k334_gunluk_kolu_fiilen_kosar),
    ("K334 KONTROL cift atesleme", kontrol_k334_ayni_anahtar_iki_kez_acilmaz),
    ("K334 MUTANT eski merdiven", mutant_k334_merdiven_eski_sira),
    ("K334 MUTANT kablo kopuk", mutant_k334_gozcu_anahtar_yazmaz),
    ("K326+K311B ardilli kirmizi", vaka_k326_ardilli_kirmizi_duran_sayilmaz),
    ("K326 duran kirmizi gorunur", vaka_k326_duran_kirmizi_gorunur),
    ("K326 F2/F3 ayri F4 sabit", vaka_k326_f2_f3_ayri),
    ("K326 MUTANT pencere", mutant_k326_pencereye_geri),
    ("K326 MUTANT kor goz", mutant_k326_kor_goz),
    ("K326 MUTANT tetik alan", mutant_k326_tetik_pencere_okur),
    ("K325 sature+tuketici", vaka_k325_sature_ve_tuketici),
    ("K325 MUTANT tuketici", mutant_k325_tuketici),
    ("K325 MUTANT saturasyon", mutant_k325_saturasyon),
    ("K311b iki okuyucu", vaka_k311b_iki_okuyucu_ayni_tur),
    ("K311b MUTANT yeni durum", mutant_k311b_yeni_durum_sessiz_kalmaz),
    ("tetik bataryalari", vaka_tetik_bataryalari_yesil),
    ("KONTROL canli yazma", kontrol_canli_dosyaya_yazilmadi),
    ("KONTROL sandbox temiz", kontrol_sandbox_temizlendi),
)

# W2-2 (18 Eyl 2026): dilim 1'in dort OLCULEMEDI satiri (K334 · K325 · K326 ·
# K311) yukaridaki vaka+mutant+KONTROL ucluleriyle KALKTI. Liste BOS tutulur;
# yeni bir olculmeyen eksen dogarsa BURAYA adiyla yazilir (sessiz yesil YOK).
OLCULEMEYENLER = ()


def main():
    print("=== NOBET ONARIM KABUL (W2 dilim 1+2) ===")
    print("kopya dizini: %s" % os.path.relpath(KOPYA_DIZINI, EV_KOKU))
    dusen = 0
    for ad, islev in VAKALAR:
        try:
            not_metni = islev()
            print("YESIL   %-28s %s" % (ad, not_metni))
        except BaseException as hata:
            dusen += 1
            print("KIRMIZI %-28s %s: %s" % (ad, type(hata).__name__, hata))
    for kalem, sebep in OLCULEMEYENLER:
        print("OLCULEMEDI %s — %s" % (kalem, sebep))
    rc = 1 if dusen else 0
    print("VAKA=%d DUSEN=%d OLCULEMEDI=%d RC=%d"
          % (len(VAKALAR), dusen, len(OLCULEMEYENLER), rc))
    return rc


if __name__ == "__main__":
    sys.exit(main())
