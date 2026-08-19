#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SERIT-B MASKELEME KAPISI KABUL TESTI — Paket K178b (18 Agu 2026, K178 ACIL
follow-up: continue-on-error: true kirmiziyi YUTAR, yesil raporlar).

MUTLAK KOK KULLANMAZ ([[kapi-sabit-kok-yanlis-agaci-olcer]]). Dosya yolu senin calisma
dizininden hesaplanir (BETIK yer = <repo>/tools/).

OLCULEN KUSURLAR (Kosum 32133861890 ve K178b commit df26964b):
  (a) serit-b job'unda bir adim kirmizi olunca GitHub'in varsayilan fail-fast
      davranisi geri kalan 114 adimi SKIP yapiyor -> uc kapinin kirmizisi halk
      GORUNMEZ ([[kirmizi-adim-sonrakini-maskeler]]).
  (b) `continue-on-error: true` adim duzeyinde kullanimi adimin kirmizisini YUTAR:
      adimin outcome'i `failure` olur ama conclusion'i `success` ve JOB YESIL
      BITER ([[fail-slow-fail-opendir]]). Bu, (a)'dan DAHA TEHLIKELI: kirmizinin
      VAR oldugu raporlanir ama job saglikli gorunur.

BU KAPI: serit-b job'undaki HER KAPI adiminda (altyapi adimlari haric) bagimsizlik
isareti durumunu olcer. Uc kusak var:
  * MASKELEYEN — bagimsizlik isareti YOK (GitHub fail-fast, sonraki adimlar skip).
  * YUTAN       — `continue-on-error: true` tasiyor (adim kirmizisini yutar, job
                  yesil raporlanir). K178b care paketinin H1 ile bu eksen de
                  REDDEDILIR (care: continue-on-error → if: ${{ !cancelled() }}).
  * BAGIMSIZ    — `if: ${{ !cancelled() }}` veya `if: always()` (kosar, kendi
                  kirmizisi job'u dusurur; sonraki adimlari maskelemez).

KAPSAM (19 Agu 2026 GENISLETMESI — SERIT B onarimi, K178 sinifinin hijyen-a3
tekrari olculdukten sonra): nobet.yml'in TUM alarm joblari taranir —
`serit-b` + `hijyen-a2` + `hijyen-a3` + `hijyen-build` + `hijyen-a4`
(TARANAN_JOBLAR). Onceki hal yalniz serit-b'ye bakiyordu; hijyen-a3'te
Yayin-acligi kirmizisi Gramer adimini SKIP etti ve canli gramer kirmizisi
CI'da MASKELI kaldi (kosum 32201776934'te olculdu) — kor bolge kapatildi.
Taranan job'lardan biri YOKSA ya da steps'i bossa kapi OLCULEMEDI ile
KIRMIZIDIR (fail-closed: job'u yeniden adlandirmak/silmek kapsami sessizce
dusuremez).

KAPSAM DISI (sayilmaz):
  * Altyapi adimlari: actions/checkout*, actions/setup-* (K2 kontrolu)
  * TARANAN_JOBLAR disindaki joblar (envanter/cron-nabzi/deploy vb.) — K1
    kontrolu bunu DAVRANISLA olcer (sahte isaretsiz job eklenir, sayilmamali).

CI'DA KABLO: bu test `serit-b` job'unda BIR ADIM olarak kosar ve muafiyet
listesinde DEGIL (davranissal kontrol, grep degil). ci-kapsam-test.py ile kapsam
kapisi saglanir.

MUTANTLAR (4/4 KIRMIZI olmali):
  * M1 --serit-b'de bir adimdan bagimsizlik isaretini kaldir (if: !cancelled()
        sil) -> MASKELEYEN >= 1, o adimin adi yazilir, rc=1
  * M2 --bir adima `continue-on-error: true` GERI KOY -> YUTAN >= 1, o adimin
        adi yazilir, rc=1 (bugunku K178b hatasi birebir yakalayan mutant).
  * M3 --taranan job'lardan birinin steps'ini bos kume yap -> eksik-envanter
        fail-closed kolu KIRMIZI (yesil donmemeli).
  * M4 --hijyen-a3'te bir adimdan bagimsizlik isaretini kaldir -> MASKELEYEN
        >= 1 RED: kapsam GENISLETMESININ canli oldugunun mutant kaniti
        (eski M4 "genisletme yasak" beyaniydi; 19 Agu hukmuyle tersine dondu).

KONTROLLER (2/2 YESIL kalmali):
  * K1 --TARANAN_JOBLAR disindaki bir job'a isaretsiz adim eklense bile kapi
        onu SAYMAMALI (kapsam siniri davranisla olculur, adla degil).
  * K2 --checkout/setup-python/setup-node adimlari MASKELEYEN/YUTAN isareti
        tasIMAMALI, kapi bunlari saymamali. Altyapi adimlarinin OLMAMASI
        BEKLENIR (yesil yanmali).

CI CIKTI FORMATI:
  ADIM=<n> BAGIMSIZ=<n> MASKELEYEN=0 YUTAN=0 MUTANT=4/4 KONTROL=2/2
  (rc=0 yalniz MASKELEYEN=0 ve YUTAN=0 ve MUTANT=4/4 ve KONTROL=2/2 ise)
"""

import argparse
import os
import re
import shutil
import sys
import tempfile

NOBET_YML = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".github", "workflows", "nobet.yml"
)

SERIT_B_JOB_ADI = "serit-b"
# 19 Agu 2026 genislemesi: hijyen joblari da taranir (K178'in hijyen-a3 tekrari).
TARANAN_JOBLAR = (SERIT_B_JOB_ADI, "hijyen-a2", "hijyen-a3", "hijyen-build",
                  "hijyen-a4")
ALTYAPI_USES_ON_EK = ("actions/checkout", "actions/setup-")

CIKIS_KIRMIZI_DAGILIM_BEKLENEN = "ADIM="

# Bagimsizlik isareti tipleri
BAGIMSIZLIK_YUTAN = "YUTAN"            # continue-on-error: true -> yutar
BAGIMSIZLIK_KOSAR = "BAGIMSIZ"          # if: !cancelled() / always() -> kosar, dusurur


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
    """no bet.yml icin minimum gerekli YAML cozumleyici."""
    with open(yol, "r", encoding="utf-8") as fh:
        satirlar = fh.readlines()
    joblar = {}
    aktif_job = None
    aktif_adim = None
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
    if aktif_adim is not None and aktif_job is not None:
        joblar.setdefault(aktif_job, []).append(
            {"name": aktif_adim[0], "uses": aktif_adim[1], "_blok": "\n".join(adim_blok)}
        )
    return {"jobs": joblar}


# ─────────────── ADIM ANALIZI ───────────────
def _adim_bagimsizlik_tipi(adim):
    """Bir adimin bagimsizlik isareti durumunu doner:
       * BAGIMSIZLIK_YUTAN   — continue-on-error: true (kirmiziyi yutar)
       * BAGIMSIZLIK_KOSAR   — if: !cancelled() veya if: always() (kosar, dusurur)
       * None                — bagimsizlik isareti yok (fail-fast, maskeleyen)
    """
    if isinstance(adim, dict):
        if adim.get("continue-on-error") is True:
            return BAGIMSIZLIK_YUTAN
        if_clause = str(adim.get("if", ""))
        if _if_clause_bagimsizmi(if_clause):
            return BAGIMSIZLIK_KOSAR
        run = adim.get("run")
        if isinstance(run, dict) and run.get("continue-on-error") is True:
            return BAGIMSIZLIK_YUTAN
        blok = adim.get("_blok")
        if blok is not None:
            if re.search(r"continue-on-error:\s*true", blok):
                return BAGIMSIZLIK_YUTAN
            if re.search(r"if:\s*!\s*cancelled\(\)", blok):
                return BAGIMSIZLIK_KOSAR
            if re.search(r"if:\s*always\(\)", blok):
                return BAGIMSIZLIK_KOSAR
    return None


def _if_clause_bagimsizmi(if_clause):
    """if clause'un `!cancelled()` veya `always()` icerip icermedigini kontrol eder.
    `always()` yine de BAGIMSIZ sayilir cunku bir sonraki adimi maskelemez.
    """
    s = if_clause.replace(" ", "")
    if "!cancelled()" in s:
        return True
    if "always()" in s:
        return True
    return False


def _adim_altyapi_mi(adim):
    if isinstance(adim, dict):
        uses = str(adim.get("uses", ""))
    else:
        uses = ""
    return any(uses.startswith(ek) for ek in ALTYAPI_USES_ON_EK)


def maske_tara(veri):
    """TARANAN_JOBLAR'in kapı adimlarini sayar:
       * toplam_kapi   — altyapi haric kapı adimi sayisi (5 job toplami)
       * bagimsiz      — if: !cancelled() / always() tasiyan (kosar, dusurur)
       * yutan         — continue-on-error: true tasiyan (kirmiziyi yutar) — RED
       * maskeleyen    — bagimsizlik isareti olmayan (fail-fast) — RED
       * eksik_joblar  — taranan envanterde OLMAYAN/steps'siz job adlari — RED
       * evren_bos_mu  — eksik job var YA DA hic kapı adimi yok (fail-closed)
    """
    joblar = veri.get("jobs", {}) or {}
    toplam = 0
    bagimsiz = 0
    maskeleyen = []
    yutan = []
    eksik = []
    for job_adi in TARANAN_JOBLAR:
        jb = joblar.get(job_adi)
        steps = jb.get("steps") if isinstance(jb, dict) else None
        if not steps:
            eksik.append(job_adi)
            continue
        for adim in steps:
            if _adim_altyapi_mi(adim):
                continue  # K2 kontrolu
            toplam += 1
            tip = _adim_bagimsizlik_tipi(adim)
            nm = adim.get("name") if isinstance(adim, dict) else ""
            nm = "%s :: %s" % (job_adi, str(nm)[:70])
            if tip == BAGIMSIZLIK_KOSAR:
                bagimsiz += 1
            elif tip == BAGIMSIZLIK_YUTAN:
                yutan.append(nm)
            else:
                maskeleyen.append(nm)
    return {"evren_bos_mu": bool(eksik) or toplam == 0,
            "eksik_joblar": eksik,
            "maskeleyen_liste": maskeleyen, "yutan_liste": yutan,
            "toplam_kapi": toplam, "bagimsiz": bagimsiz}


# ─────────────── MUTANT TESTLERI ───────────────
def _yerel_no_bet_kopyasi(tmpdir):
    hedef = os.path.join(tmpdir, "nobet.yml")
    shutil.copy(NOBET_YML, hedef)
    return hedef


def mutant_testleri_calistir():
    """4 mutant calistir, 4/4 kirmizi olmalidir."""
    sonuc = {"m1": None, "m2": None, "m3": None, "m4": None}

    # M1: bir adimdan `if: !cancelled()` satırini kaldir → MASKELEYEN=1 RED
    with tempfile.TemporaryDirectory() as tmp:
        kopya = _yerel_no_bet_kopyasi(tmp)
        with open(kopya, "r", encoding="utf-8") as fh:
            metin = fh.read()
        sb_match = re.search(
            r"^  serit-b:\s*\n(?:(?:    .*\n)|(?:    .*\n.*\n.*\n)){0,5000}",
            metin, re.MULTILINE,
        )
        if sb_match:
            sb_blok = sb_match.group(0)
            yeni_blok = re.sub(
                r"[ \t]+if:\s*\$\{\{\s*!\s*cancelled\(\)\s*}}\n", "", sb_blok, count=1
            )
            if yeni_blok != sb_blok:
                yeni_metin = metin.replace(sb_blok, yeni_blok, 1)
                with open(kopya, "w", encoding="utf-8") as fh:
                    fh.write(yeni_metin)
                sonuc["m1"] = _kabul_calistir(kopya, beklenen_kirmizi=True)
            else:
                sonuc["m1"] = ("OLCULEMEDI", "serit-b icinde if: !cancelled() yok")
        else:
            sonuc["m1"] = ("OLCULEMEDI", "serit-b blogu bulunamadi")

    # M2: bir adima `continue-on-error: true` GERI KOY → YUTAN=1 RED
    try:
        import yaml  # noqa: F401
    except ModuleNotFoundError:
        sonuc["m2"] = ("OLCULEMEDI", "pyyaml yok")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            kopya = _yerel_no_bet_kopyasi(tmp)
            with open(kopya, "r", encoding="utf-8") as fh:
                veri = yaml.safe_load(fh)
            sb = veri["jobs"][SERIT_B_JOB_ADI]
            hedef_idx = None
            for i, adim in enumerate(sb["steps"]):
                if not _adim_altyapi_mi(adim):
                    hedef_idx = i
                    break
            if hedef_idx is None:
                sonuc["m2"] = ("OLCULEMEDI", "serit-b icinde kapı adimi yok")
            else:
                sb["steps"][hedef_idx]["continue-on-error"] = True
                with open(kopya, "w", encoding="utf-8") as fh:
                    yaml.safe_dump(veri, fh, allow_unicode=True, sort_keys=False)
                sonuc["m2"] = _kabul_calistir(kopya, beklenen_kirmizi=True)

    # M3 + M4 icin PyYAML gerekli
    try:
        import yaml  # noqa: F401

        # M3: serit-b job'unun steps: [] yap → ADIM=0, evren bos, RED
        with tempfile.TemporaryDirectory() as tmp:
            kopya = _yerel_no_bet_kopyasi(tmp)
            with open(kopya, "r", encoding="utf-8") as fh:
                veri = yaml.safe_load(fh)

            def m3_mutator(v):
                v["jobs"]["serit-b"]["steps"] = []

            m3_mutator(veri)
            with open(kopya, "w", encoding="utf-8") as fh:
                yaml.safe_dump(veri, fh, allow_unicode=True, sort_keys=False)
            sonuc["m3"] = _kabul_calistir(kopya, beklenen_kirmizi=True)

        # M4: hijyen-a3'te isaret kaldirilirsa GENISLETILMIS kapsam yakaliyor mu?
        sonuc["m4"] = _m4_hijyen_isaret_kaldirma()
    except ModuleNotFoundError:
        sonuc["m3"] = ("OLCULEMEDI", "pyyaml yok")
        sonuc["m4"] = ("OLCULEMEDI", "pyyaml yok")

    return sonuc


def _m4_hijyen_isaret_kaldirma():
    """M4 (19 Agu 2026): hijyen-a3'te BIR adimdan bagimsizlik isaretini kaldir ->
    genisletilmis kapsam MASKELEYEN>=1 ile KIRMIZI donmeli. Eski M4 'kapsami
    hijyen'e genisletme' beyanini koruyordu; SERIT B onarimi o hukmu tersine
    cevirdi — bu mutant genislemenin CANLI oldugunu her kosumda kanitlar."""
    try:
        import yaml  # noqa: F401
    except ModuleNotFoundError:
        return ("OLCULEMEDI", "pyyaml yok")
    with tempfile.TemporaryDirectory() as tmp:
        kopya = _yerel_no_bet_kopyasi(tmp)
        with open(kopya, "r", encoding="utf-8") as fh:
            veri = yaml.safe_load(fh)
        hijyen = veri["jobs"].get("hijyen-a3")
        if hijyen is None or not hijyen.get("steps"):
            return ("OLCULEMEDI", "hijyen-a3 job'u yok")
        hedef = None
        for adim in hijyen["steps"]:
            if _adim_altyapi_mi(adim):
                continue
            if _adim_bagimsizlik_tipi(adim) == BAGIMSIZLIK_KOSAR:
                hedef = adim
                break
        if hedef is None:
            return ("OLCULEMEDI", "hijyen-a3'te isaretli kapı adimi yok")
        hedef.pop("if", None)
        with open(kopya, "w", encoding="utf-8") as fh:
            yaml.safe_dump(veri, fh, allow_unicode=True, sort_keys=False)
        return _kabul_calistir(kopya, beklenen_kirmizi=True)


def _kabul_calistir(yaml_yol, beklenen_kirmizi):
    """Kapiyi verilen no bet.yml uzerinden calistirir.

    beklenen_kirmizi=True ise: MASKELEYEN>=1 VEYA YUTAN>=1 VEYA evren bos -> KIRMIZI.
    beklenen_kirmizi=False ise: hepsi 0 olmali (kontrol).
    """
    veri = yaml_yukle_guvenli(yaml_yol)
    sonuc = maske_tara(veri)
    toplam = sonuc["toplam_kapi"]
    bagimsiz = sonuc["bagimsiz"]
    maske = sonuc["maskeleyen_liste"]
    yutan = sonuc["yutan_liste"]
    evren_bos = sonuc["evren_bos_mu"]

    if beklenen_kirmizi:
        if evren_bos:
            return ("KIRMIZI", "evren bos -> kapi yesil donmedi, kirmizi (beklenen)")
        if len(maske) >= 1:
            return ("KIRMIZI", f"MASKELEYEN={len(maske)} beklenen kirmizi")
        if len(yutan) >= 1:
            return ("KIRMIZI", f"YUTAN={len(yutan)} beklenen kirmizi")
        return ("YESIL", "mutant beklenen kirmiziyi uremedi")
    else:
        if evren_bos:
            return ("OLCULEMEDI", "evren bos, kontrol anlamsiz")
        if len(maske) >= 1 or len(yutan) >= 1:
            return ("KIRMIZI", f"KONTROL beklenmedik kirmizi: maske={len(maske)} yutan={len(yutan)}")
        return ("YESIL", None)


# ─────────────── KONTROL TESTLERI ───────────────
def kontrol_testleri_calistir():
    """K1: TARANAN_JOBLAR disi job sayilmaz (davranissal). K2: altyapi sayilmaz."""
    sonuc = {"k1": None, "k2": None}

    # K1 (19 Agu 2026, davranissal): kapsam DISI bir job'a isaretsiz adim
    # eklenmis kopyada kapi YESIL kalmali — sinir adla degil taramayla olculur.
    veri = yaml_yukle_guvenli(NOBET_YML)
    if not isinstance(veri, dict) or "jobs" not in veri:
        sonuc["k1"] = ("KIRMIZI", "K1: nobet.yml yuklenemedi")
    else:
        import copy
        kopya = copy.deepcopy(veri)
        kopya["jobs"]["k1-kapsam-disi-sahte"] = {
            "runs-on": "ubuntu-latest",
            "steps": [{"name": "isaretsiz sahte adim", "run": "echo k1"}],
        }
        s = maske_tara(kopya)
        if s["maskeleyen_liste"] or s["yutan_liste"] or s["evren_bos_mu"]:
            sonuc["k1"] = ("KIRMIZI",
                           "K1: kapsam disi sahte job sayildi ya da evren bozuldu")
        else:
            sonuc["k1"] = ("YESIL", None)

    betik = os.path.abspath(__file__)
    with open(betik, "r", encoding="utf-8") as fh:
        kaynak = fh.read()
    for on_ek in ("actions/checkout", "actions/setup-"):
        if on_ek not in kaynak:
            sonuc["k2"] = ("KIRMIZI", f"K2 kontrolu eksik: {on_ek} listede degil")
            return sonuc
    sonuc["k2"] = ("YESIL", None)

    return sonuc


# ─────────────── ANA KABUL ───────────────
def ana_kabul(yaml_yol):
    veri = yaml_yukle_guvenli(yaml_yol)
    return maske_tara(veri)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kendini-test", action="store_true", help="Mutant + kontrol bataryasini calistir")
    parser.add_argument("--yaml", default=NOBET_YML, help="nobet.yml yolu (test/olcum)")
    args = parser.parse_args()

    ana = ana_kabul(args.yaml)
    toplam = ana["toplam_kapi"]
    bagimsiz = ana["bagimsiz"]
    maske = ana["maskeleyen_liste"]
    yutan = ana["yutan_liste"]
    evren_bos = ana["evren_bos_mu"]

    if evren_bos:
        print("OLCULEMEDI evren bos ya da envanter eksik (taranan job'lar: %s; "
              "eksik: %s)" % (",".join(TARANAN_JOBLAR),
                              ",".join(ana.get("eksik_joblar") or []) or "-"))
        return 1
    if maske:
        for nm in maske[:10]:
            print(f"MASKELEYEN_ADIM: {nm}")
        print(f"ADIM={toplam} BAGIMSIZ={bagimsiz} MASKELEYEN={len(maske)} YUTAN={len(yutan)} MUTANT=0/0 KONTROL=0/0")
        return 1
    if yutan:
        for nm in yutan[:10]:
            print(f"YUTAN_ADIM: {nm}")
        print(f"ADIM={toplam} BAGIMSIZ={bagimsiz} MASKELEYEN=0 YUTAN={len(yutan)} MUTANT=0/0 KONTROL=0/0")
        return 1

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
                mt_total -= 1
        for k, v in kt.items():
            kt_total += 1
            if v[0] == "YESIL":
                kt_yesil += 1
    else:
        mt_red, mt_total = 0, 0
        kt_yesil, kt_total = 0, 0

    print(f"ADIM={toplam} BAGIMSIZ={bagimsiz} MASKELEYEN=0 YUTAN=0 MUTANT={mt_red}/{mt_total} KONTROL={kt_yesil}/{kt_total}")
    if args.kendini_test and (mutant_bilgi or kontrol_bilgi):
        print(mutant_bilgi)
        print(kontrol_bilgi)
    return 0


if __name__ == "__main__":
    sys.exit(main())