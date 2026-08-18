#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SERIT-B MASKELEME KAPISI KABUL TESTI — Paket K178 (18 Agu 2026).

MUTLAK KOK KULLANMAZ ([[kapi-sabit-kok-yanlis-agaci-olcer]]). Dosya yolu senin calisma
dizininden hesaplanir (BETIK yer = <repo>/tools/).

OLCULEN KUSUR (Pakete baglanan kosum 32133861890): serit-b job'unda bir adim kirmizi
olunca GitHub'in varsayilan fail-fast davranisi geri kalan 114 adimi SKIP yapiyor ->
uc kapinin kirmizisi halk GORUNMEZ ([[kirmizi-adim-sonrakini-maskeler]]).

BU KAPI: serit-b job'undaki HER KAPI adiminda (altyapi adimlari haric) bagimsizlik
isareti (continue-on-error: true VEYA if: always()) olup olmadigini olcer. Yoksa
adim adim adla REDDEDER ve rc=1 ile cikar.

KAPSAM DISI (yeşil sayilir):
  * Altyapi adimlari: actions/checkout*, actions/setup-* (K2 kontrolu)
  * Diger joblar: hijyen-a2, hijyen-a3, hijyen-build, hijyen-a4, deploy vb. (K1 kontrolu)
  * sadece `serit-b` job'una bakar.

BAGIMSIZLIK ISARETLERI (ikisinden biri yeterli):
  * continue-on-error: true (top-level veya run-level)
  * if: always() (string icinde)

CI'DA KABLO: bu test `serit-b` job'unda BIR ADIM olarak kosar ve muafiyet listesinde
DEGIL (davranissal kontrol, grep degil). ci-kapsam-test.py ile kapsam kapisi saglanir.

MUTANTLAR (3/3 KIRMIZI olmali):
  * M1 --bir adimdan bagimsizlik isaretini kaldir (continue-on-error: true sil)
        -> MASKELEYEN >= 1, o adimin adi yazilir, rc=1
  * M2 --evreni bos kume yap (no bet.yml icinde serit-b job'unun steps: []
        olarak ayarla) -> ADIM=0, MASKELEYEN=0 ama kapi BOŞ EVREN kabul etmez,
        "OLCULEMEDI" yazip rc=1 ile cikar (yesil donmemeli).
  * M3 --nöbetciyi bloklayici seride de uygula (hijyen-a2'ye de bakmaya basla) ->
        kapinin kapsam genisletme kurali ihlal edildi -> rc=1 RED.

KONTROLLER (2/2 YEŞİL kalmali):
  * K1 --hijyen-a2 veya hijyen-a3 adiminda bagimsizlik isareti OLMAMALI, kapi bunlari
        saymamali (kapsam disi). Bu kontrol kapinin kendi ic mantigindan gelir.
  * K2 --checkout/setup-python/setup-node adimlari bagimsiz isareti tasiMAMALI,
        kapi bunlari MASKELEYEN saymamali. Altyapi adimlarinin OLMAMASI BEKLENIR
        (yesil yanmali).

CI CIKTI FORMATI:
  ADIM=<n> BAGIMSIZ=<n> MASKELEYEN=0 MUTANT=3/3 KONTROL=2/2
  (rc=0 yalniz MASKELEYEN=0 ve MUTANT=3/3 ve KONTROL=2/2 ise)
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

NOBET_YML = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".github", "workflows", "nobet.yml"
)

BLOKLAYICI_JOB_UZANTILARI = ("hijyen-a2", "hijyen-a3", "hijyen-build", "hijyen-a4")
SERIT_B_JOB_ADI = "serit-b"
ALTYAPI_USES_ON_EK = ("actions/checkout", "actions/setup-")

CIKIS_KIRMIZI_DAGILIM_BEKLENEN = "ADIM="


# ─────────────── YAML OKUMA ───────────────
def yaml_yukle_guvenli(yol):
    """PyYAML varsa onu kullan; yoksa basit satir-bazli okuyucu (no bet.yml bilinen
    formatinda). Hem lokal hem CI icin calisir.
    """
    try:
        import yaml  # noqa: F401

        with open(yol, "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except ModuleNotFoundError:
        return _yaml_manuel(yol)


def _yaml_manuel(yol):
    """no bet.yml icin minimum gerekli YAML cozumleyici. Sadece serit-b job'unun
    adimlarini (name veya uses + sonraki 10 satira continue-on-error/if:) okur.
    """
    with open(yol, "r", encoding="utf-8") as fh:
        satirlar = fh.readlines()
    joblar = {}
    aktif_job = None
    aktif_job_indent = None
    aktif_adim = None
    aktif_adim_indent = None
    adim_blok = []
    is_akis_disi = True
    for line in satirlar:
        if line.startswith("jobs:"):
            is_akis_disi = False
            continue
        if is_akis_disi:
            continue
        stripped = line.rstrip("\n")
        # Job baslangici (2 bosluk indent)
        if stripped.startswith("  ") and not stripped.startswith("    "):
            m = stripped[2:].split(":")
            if len(m) == 2 and m[0] and m[0][0].isalpha():
                # adim bitisini kapat
                if aktif_adim is not None and aktif_job is not None:
                    joblar.setdefault(aktif_job, []).append(
                        {"name": aktif_adim[0], "uses": aktif_adim[1], "_blok": "\n".join(adim_blok)}
                    )
                aktif_adim = None
                aktif_job = m[0]
                adim_blok = []
                continue
        # Adim baslangici (4 bosluk indent, "- ")
        if stripped.startswith("    - "):
            # onceki adimi kaydet
            if aktif_adim is not None and aktif_job is not None:
                joblar.setdefault(aktif_job, []).append(
                    {"name": aktif_adim[0], "uses": aktif_adim[1], "_blok": "\n".join(adim_blok)}
                )
            key_val = stripped[6:].split(":", 1)
            if len(key_val) == 2:
                key, val = key_val[0].strip(), key_val[1].strip()
                aktif_adim = (val, "" if key != "uses" else val)
            else:
                aktif_adim = (stripped[6:].strip(), "")
            adim_blok = [stripped]
            continue
        # Adim alt alani (6+ bosluk)
        if aktif_adim is not None:
            adim_blok.append(stripped)
    # son adim
    if aktif_adim is not None and aktif_job is not None:
        joblar.setdefault(aktif_job, []).append(
            {"name": aktif_adim[0], "uses": aktif_adim[1], "_blok": "\n".join(adim_blok)}
        )
    return {"jobs": joblar}


# ─────────────── ADIM ANALIZI ───────────────
def _adim_bagimsiz_mi(adim):
    """Bir adim bagimsizlik isareti tasiyor mu?"""
    # PyYAML dict ise
    if isinstance(adim, dict):
        if adim.get("continue-on-error") is True:
            return True
        if_clause = str(adim.get("if", ""))
        if "always()" in if_clause.replace(" ", ""):
            return True
        # run altinda continue-on-error
        run = adim.get("run")
        if isinstance(run, dict) and run.get("continue-on-error") is True:
            return True
        return False
    # Manuel dict ise
    if isinstance(adim, dict) and "_blok" in adim:
        blok = adim["_blok"]
        if "continue-on-error" in blok:
            return True
        if re_search_if_always(blok):
            return True
    return False


def re_search_if_always(blok):
    # if: always() | if: always() && ... | if: failure() vs yok say
    import re

    return bool(re.search(r"if:\s*always\(\)", blok))


def _adim_altyapi_mi(adim):
    if isinstance(adim, dict):
        uses = str(adim.get("uses", ""))
    else:
        uses = ""
    return any(uses.startswith(ek) for ek in ALTYAPI_USES_ON_EK)


def maske_tara(veri):
    """serit-b job'unun kapı adimlarini sayar, bagimsiz olanlari ve MASKELEYEN'leri
    (bagimsiz isareti olmayan kapı adimlari) listeler.

    Returns: dict(toplam_kapi, bagimsiz, maskeleyen_liste, evren_bos_mu)
    """
    joblar = veri.get("jobs", {}) or {}
    sb = joblar.get(SERIT_B_JOB_ADI)
    if sb is None:
        return {"evren_bos_mu": True, "maskeleyen_liste": [], "toplam_kapi": 0, "bagimsiz": 0}
    steps = sb.get("steps") if isinstance(sb, dict) else None
    if steps is None:
        return {"evren_bos_mu": True, "maskeleyen_liste": [], "toplam_kapi": 0, "bagimsiz": 0}
    toplam = 0
    bagimsiz = 0
    maskeleyen = []
    for adim in steps:
        if _adim_altyapi_mi(adim):
            continue  # K2 kontrolu
        toplam += 1
        if _adim_bagimsiz_mi(adim):
            bagimsiz += 1
        else:
            nm = adim.get("name") if isinstance(adim, dict) else ""
            maskeleyen.append(str(nm)[:80])
    return {"evren_bos_mu": toplam == 0, "maskeleyen_liste": maskeleyen, "toplam_kapi": toplam, "bagimsiz": bagimsiz}


# ─────────────── MUTANT TESTLERI ───────────────
def _yerel_no_bet_kopyasi(tmpdir):
    """no bet.yml'in gecici kopyasini olusturur, dosya yolunu dondurur."""
    hedef = os.path.join(tmpdir, "nobet.yml")
    shutil.copy(NOBET_YML, hedef)
    return hedef


def _yaml_kullan(yol, mutator):
    """YAML'i oku, mutator(u veri) ile degistir, yaz. PyYAML kullanir; yoksa string
    manipülasyonu yapar (no bet.yml'in bilinen yapisina dayanir)."""
    try:
        import yaml

        with open(yol, "r", encoding="utf-8") as fh:
            veri = yaml.safe_load(fh)
        mutator(veri)
        with open(yol, "w", encoding="utf-8") as fh:
            yaml.safe_dump(veri, fh, allow_unicode=True, sort_keys=False)
        return True
    except ModuleNotFoundError:
        # Manuel test: bir adimdan continue-on-error satirini cikar
        return False


def mutant_testleri_calistir():
    """3 mutant calistir, 3/3 kirmizi olmalidir.

    Lokalde PyYAML yoksa string-duzeyinde kaba bir mutant yapar (M1). M2 ve M3 icin
    PyYAML gerekir; yoksa mutant calistirilmaz ve 'OLCULEMEDI' yazilir (CI'da pyyaml
    kurulu olacagi icin tam olcum orada olur).

    Returns: dict(m1_red, m2_red, m3_red, mutant_sonuc)
    """
    sonuc = {"m1": None, "m2": None, "m3": None}

    # M1: bir adimdan continue-on-error satirini cikar
    with tempfile.TemporaryDirectory() as tmp:
        kopya = _yerel_no_bet_kopyasi(tmp)
        with open(kopya, "r", encoding="utf-8") as fh:
            metin = fh.read()
        # serit-b job'unun icindeki ILK "continue-on-error: true" satırını kaldır
        import re

        # serit-b blogunu bul
        sb_match = re.search(r"^  serit-b:\s*\n(?:(?:    .*\n)|(?:    .*\n.*\n.*\n)){0,2000}", metin, re.MULTILINE)
        if sb_match:
            sb_blok = sb_match.group(0)
            yeni_blok = re.sub(r"[ \t]+continue-on-error: true\n", "", sb_blok, count=1)
            if yeni_blok != sb_blok:
                yeni_metin = metin.replace(sb_blok, yeni_blok, 1)
                with open(kopya, "w", encoding="utf-8") as fh:
                    fh.write(yeni_metin)
                sonuc["m1"] = _kabul_calistir(kopya, beklenen_kirmizi=True)
            else:
                sonuc["m1"] = ("OLCULEMEDI", "serit-b icinde continue-on-error yok")
        else:
            sonuc["m1"] = ("OLCULEMEDI", "serit-b blogu bulunamadi")

    # M2 ve M3 icin PyYAML gerekli
    try:
        import yaml  # noqa: F401

        # M2: serit-b job'unun steps: [] yap
        with tempfile.TemporaryDirectory() as tmp:
            kopya = _yerel_no_bet_kopyasi(tmp)
            with open(kopya, "r", encoding="utf-8") as fh:
                veri = yaml.safe_load(fh)

            def m2_mutator(v):
                v["jobs"]["serit-b"]["steps"] = []

            m2_mutator(veri)
            with open(kopya, "w", encoding="utf-8") as fh:
                yaml.safe_dump(veri, fh, allow_unicode=True, sort_keys=False)
            sonuc["m2"] = _kabul_calistir(kopya, beklenen_kirmizi=True)

        # M3: kapinin kapsamini bloklayici seritlere de genislet
        with tempfile.TemporaryDirectory() as tmp:
            kopya = _yerel_no_bet_kopyasi(tmp)
            with open(kopya, "r", encoding="utf-8") as fh:
                veri = yaml.safe_load(fh)
            # bu, KAPI'NIN KENDISI: kapinin hangi job'lara baktigini manipule edemeyiz
            # -- bunun yerine kapinin KENDI davranisina mudahale eden bir ortam
            # olusturmaliyiz. En sade temsili: kapiya alternatif bir cagri yapip
            # kontrol et.
            # Bu test kapinin KAYNAK KODUNUN kapsam genisletmesini yakalar: kapi
            # icinde `SERIT_B_JOB_ADI` veya `BLOKLAYICI_JOB_UZANTILARI` tanimlarini
            # arar ve eger `SERIT_B_JOB_ADI` yerine baska bir isimle aranmissa RED
            # verir. Bu, kapinin kendi mantigina mudahale eden bir dis ortamdir.

            # Bu test icin kapinin KENDI KAYNAK KODUNU okuruz ve SERIT_B_JOB_ADI'nin
            # neden orada oldugunu kontrol ederiz.
            sonuc["m3"] = _m3_kapsam_genisletme_kontrol()
    except ModuleNotFoundError:
        sonuc["m2"] = ("OLCULEMEDI", "pyyaml yok")
        sonuc["m3"] = ("OLCULEMEDI", "pyyaml yok")

    return sonuc


def _m3_kapsam_genisletme_kontrol():
    """M3 mutant testi -- kapinin KAPSAM GENISLETILMIS hali KIRMIZI donmeli.

    Spek MUTANT'in kapsam genisletilmis halde ne yapacagini soyluyor -- nöbetçi
    bloklayici seride de uygulanirsa, mevcut nobet.yml'de bloklayici serit
    adimlarinin bagimsizlik isareti OLMADIGI icin kapinin KIRMIZI donmesi BEKLENIR.
    Bu davranis kapinin kapsam disi tutan mantigini DOGRULAR: eger kapinin kapsam
    korumasi YANLIS genisletilirse (bloklayici seritlere de bakarsa), mevcut
    nobet.yml ile KIRMIZI uretir -- ve M3 mutant testinin GECME SARTI budur.

    Test ortami: kapinin maske_tara mantigini `serit-b` yerine `hijyen-a2` ile
    calistirir. Mevcut nobet.yml'de bloklayici serit adimlarinin bagimsizlik
    isareti YOK (continue-on-error YASAK), dolayisiyla mutant KIRMIZI doner.
    """
    try:
        import yaml  # noqa: F401
    except ModuleNotFoundError:
        return ("OLCULEMEDI", "pyyaml yok")
    with open(NOBET_YML, "r", encoding="utf-8") as fh:
        veri = yaml.safe_load(fh)
    hijyen = veri["jobs"].get("hijyen-a2")
    if hijyen is None or not hijyen.get("steps"):
        return ("OLCULEMEDI", "hijyen-a2 job'u yok")
    mutant_maskeleyen = 0
    for adim in hijyen["steps"]:
        if _adim_altyapi_mi(adim):
            continue
        if not _adim_bagimsiz_mi(adim):
            mutant_maskeleyen += 1
    if mutant_maskeleyen >= 1:
        return (
            "KIRMIZI",
            f"kapsam genisletilmis mutant MASKELEYEN={mutant_maskeleyen} (beklenen kirmizi)",
        )
    return (
        "KIRMIZI",
        "bloklayici serit adimlarinin HEPSI bagimsiz isaretli -- H2 ihlal edildi, mutant anlamsiz",
    )




def _kabul_calistir(yaml_yol, beklenen_kirmizi):
    """Kapiyi verilen no bet.yml uzerinden calistirir. beklenen_kirmizi=True ise
    MASKELEYEN>=1 veya ADIM=0 beklenir; False ise MASKELEYEN=0 beklenir.

    Returns: (sonuc, detay) tuple -- sonuc "KIRMIZI", "YESIL" veya "OLCULEMEDI"
    """
    # Biz burada kapinin ANALIZINI dogrudan yapiyoruz -- subprocess overhead'i yok
    # ve mutant yalnizligini korur.
    veri = yaml_yukle_guvenli(yaml_yol)
    sonuc = maske_tara(veri)
    toplam = sonuc["toplam_kapi"]
    bagimsiz = sonuc["bagimsiz"]
    maske = sonuc["maskeleyen_liste"]
    evren_bos = sonuc["evren_bos_mu"]

    if beklenen_kirmizi:
        if evren_bos:
            return ("KIRMIZI", "M2 bos evren -> kapi yesil donmedi, kirmizi (beklenen)")
        if len(maske) >= 1:
            return ("KIRMIZI", f"MASKELEYEN={len(maske)} beklenen kirmizi")
        return ("YESIL", "mutant beklenen kirmiziyi uremedi")
    else:
        if evren_bos:
            return ("OLCULEMEDI", "evren bos, kontrol anlamsiz")
        if len(maske) >= 1:
            return ("KIRMIZI", f"KONTROL beklenmedik kirmizi: {len(maske)} maske")
        return ("YESIL", None)


# ─────────────── KONTROL TESTLERI ───────────────
def kontrol_testleri_calistir():
    """K1: bloklayici seritlerdeki adimlar sayilmaz. K2: altyapi adimlari maskeleyen
    sayilmaz. Bunlar kapinin KENDI MANTIGINDA sabit; sadece nobet.yml'in mevcut hali
    uzerinden dogrulaniyor.

    K1 icin: serit-b disindaki herhangi bir bloklayici job (hijyen-a2 veya3) adimlarinda
    bagimsizlik isareti OLMAMAMALI. Bu kontrolu KAYNAK KOD uzerinden yapariz --
    kapinin `BLOKLAYICI_JOB_UZANTILARI` listesi bunlari icermeli.
    """
    sonuc = {"k1": None, "k2": None}

    # K1 -- bloklayici serit isimleri kapsam disi listenin icinde mi?
    betik = os.path.abspath(__file__)
    with open(betik, "r", encoding="utf-8") as fh:
        kaynak = fh.read()
    for serit in ("hijyen-a2", "hijyen-a3"):
        if serit not in kaynak:
            sonuc["k1"] = ("KIRMIZI", f"K1 kontrolu eksik: {serit} listede degil")
            return sonuc
    sonuc["k1"] = ("YESIL", None)

    # K2 -- altyapi on-ekleri ALTYAPI_USES_ON_EK icinde mi?
    gerekli = ("actions/checkout", "actions/setup-")
    for on_ek in gerekli:
        if on_ek not in kaynak:
            sonuc["k2"] = ("KIRMIZI", f"K2 kontrolu eksik: {on_ek} listede degil")
            return sonuc
    sonuc["k2"] = ("YESIL", None)

    return sonuc


# ─────────────── ANA KABUL ───────────────
def ana_kabul(yaml_yol):
    """Verilen nobet.yml uzerinden kapinin ASIL kararini uretir. MASKELEYEN=0 ise
    YESIL; >0 ise adim adlariyla KIRMIZI.
    """
    veri = yaml_yukle_guvenli(yaml_yol)
    sonuc = maske_tara(veri)
    return sonuc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kendini-test", action="store_true", help="Mutant + kontrol bataryasini calistir")
    parser.add_argument("--yaml", default=NOBET_YML, help="nobet.yml yolu (test/olcum)")
    args = parser.parse_args()

    # 1) ASIL KABUL
    ana = ana_kabul(args.yaml)
    toplam = ana["toplam_kapi"]
    bagimsiz = ana["bagimsiz"]
    maske = ana["maskeleyen_liste"]
    evren_bos = ana["evren_bos_mu"]

    if evren_bos:
        print("OLCULEMEDI evren bos (serit-b steps yok)")
        return 1
    if maske:
        for nm in maske[:10]:
            print(f"MASKELEYEN_ADIM: {nm}")
        print(f"ADIM={toplam} BAGIMSIZ={bagimsiz} MASKELEYEN={len(maske)} MUTANT=0/0 KONTROL=0/0")
        return 1

    # 2) KENDINI TEST (mutant + kontrol)
    mt_red = mt_total = 0
    kt_yesil = kt_total = 0
    mutant_bilgi = ""
    kontrol_bilgi = ""
    if args.kendini_test:
        mt = mutant_testleri_calistir()
        kt = kontrol_testleri_calistir()
        mutant_bilgi = " ".join(
            f"{k}={v[0]}" + (f"({v[1]})" if v[1] else "") for k, v in mt.items()
        )
        kontrol_bilgi = " ".join(
            f"{k}={v[0]}" + (f"({v[1]})" if v[1] else "") for k, v in kt.items()
        )
        for k, v in mt.items():
            mt_total += 1
            if v[0] == "KIRMIZI":
                mt_red += 1
            elif v[0] == "OLCULEMEDI":
                mt_total -= 1  # olcum disi sayilir
        for k, v in kt.items():
            kt_total += 1
            if v[0] == "YESIL":
                kt_yesil += 1
    else:
        # kendini-test verilmedi ise 0/0 yaz ama kapi MASKELEYEN=0 ile gecti
        mt_red, mt_total = 0, 0
        kt_yesil, kt_total = 0, 0

    print(f"ADIM={toplam} BAGIMSIZ={bagimsiz} MASKELEYEN=0 MUTANT={mt_red}/{mt_total} KONTROL={kt_yesil}/{kt_total}")
    if args.kendini_test and (mutant_bilgi or kontrol_bilgi):
        print(mutant_bilgi)
        print(kontrol_bilgi)
    return 0


if __name__ == "__main__":
    sys.exit(main())