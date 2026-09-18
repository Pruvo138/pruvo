#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NOBET ONARIM KABUL BATARYASI — W2 dilim 1 (16 Eyl 2026).

OLCTUGU KALEMLER: K316 (V1 + V2). K334 · K325 · K326 · K311 bu dilimde
ONARILMADI; batarya onlari SESSIZCE YESIL SAYMAZ — her biri icin ADIYLA
`OLCULEMEDI` satiri basar ve rc'yi YUKSELTMEZ (iddia edilmeyen eksen kirmizi
da yakmaz, ama GORUNMEZ de kalmaz).

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
)

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


VAKALAR = (
    ("K316/V1 capa bayatligi", vaka_k316_v1_capa_bayatligi_kapandi),
    ("K316/V2 motor aritesi", vaka_k316_v2_motor_aritesi_tek_kaynaktan_turer),
    ("K316/V2 MUTANT arite", mutant_k316_v2_arite_kolu),
    ("K316/V2 el kitabi uretici", vaka_k316_v2_el_kitabi_ureticisi_kapatir),
    ("KONTROL canli yazma", kontrol_canli_dosyaya_yazilmadi),
    ("KONTROL sandbox temiz", kontrol_sandbox_temizlendi),
)

# 🔴 BU DILIMDE ONARILMAYAN KALEMLER — SESSIZ YESIL SAYILMAZ, ADIYLA BASILIR.
# Batarya bunlar icin IDDIA URETMEZ; rc'yi de yukseltmez (olculmemis eksen
# kirmizi yakmaz, ama GORUNMEZ de kalmaz). Kapatan olcum her satirda yazili.
OLCULEMEYENLER = (
    ("K334", "tur acan iki kol (CI_KIRMIZI · GUNLUK_DEFTER) merdivenin 3. "
             "basamaginin ALTINDA; onarim bu dilimde YAPILMADI. Kapatir: "
             "gozcu kalbine `icra_anahtar` yazilir + `nobet-tetik.karar()` "
             "cift atesleme yasagini ANAHTAR EKSENINDE uygular + canli turda "
             "kol govdesi kostugu olculur."),
    ("K325", "`ustuste_onarimsiz` esik ustunde SATURE OLMUYOR "
             "(`ustuste_onarimsiz_sonraki` sinirsiz +1). Kapatir: esikte "
             "saturasyon + sayiya gore davranis degistiren tuketici mutanti."),
    ("K326", "`kirmizi_toplam` hala 40-kosumluk PENCEREDEN turuyor "
             "(`gozcu.py` `_gh_kosumlar(limit=40)` + `len(kirmizilar)`). "
             "Kapatir: `ardilsiz` kirmizi (is akisi adi basina EN YENI kosum) "
             "ekseni + F2/F3 AYRI cikti + ters yon (duran kirmizi gorunur) vakasi."),
    ("K311", "seviye kolu (`seviye_karari`) KURULU; kalan dar kalem defter "
             "durum sozlugu (`ACIK_KALEM=0`) ve K334 ile AYNI merdivende. "
             "K334 kapanmadan bu kalemin ① ayagi olculemez."),
)


def main():
    print("=== NOBET ONARIM KABUL (W2 dilim 1) ===")
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
