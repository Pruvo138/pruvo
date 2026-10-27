#!/usr/bin/env python3
"""DAL DEPLOY PROVASI — deploy.yml'de BLOKLAYAN ama SERIT B'de kosmayan adimlari DAL UCUNDA kosar.

OLCULEN VAKA (14 Eki 2026): PUSH-2 dali SERIT B'de yesildi, main'e alindi; Pages `38505301885`
serit-a3 adim 47 (`python3 tools/foto-uretec-kosucu-test.py` -> `SURVIVOR M4/M5`) KIRMIZI ->
deploy+yayin SKIPPED. Adim YALNIZ deploy.yml'de kosuyordu; "beklenen kirmizi -> gerekceli merge"
kurali SERIT B'yi okuyor, deploy.yml'de bloklayan ayni adimi okumuyordu.

Bu arac `<agac>/.github/workflows/deploy.yml`'in `serit-a3` job'indan
"Fotograftan ozel uretim kabul testi" adimi (DAHIL) ile "Serit derinlik olcumu" adimi (HARIC)
ARASINDAKI adimlarin `run:` govdelerini AYNI AGACTA (cwd=<agac>) satir satir kosar.
Adim/komut listesi ELLE YAZILMAZ — her kosumda deploy.yml'den TURETILIR.

Kullanim:
  python3 tools/dal-deploy-prova.py <agac> [--haric <adim-adi-alt-dizgesi>]...
  python3 tools/dal-deploy-prova.py <agac> --liste [--tum] [--ayristirici yaml|satir]

Hal sozlugu (adim basina): YESIL · KIRMIZI · OLCULEMEDI (env'de secret/ifade, uses, shell) ·
KOSULMADI (--haric ya da `if: failure()`). OLCULEMEDI ve KOSULMADI ozet satirinda AYRI sayilir,
YESIL sayilmaz. Ilk kirmizida DURULMAZ (always() gibi hepsi kosar).

Ozet (jetonlar ayrik):
  DAL_PROVA=YESIL kosulan=<n> kirmizi=0 olculemedi=<n> kosulmadi=<n>   rc 0
  DAL_PROVA=KIRMIZI kirmizi=<n> ilk=<adim>                             rc 1
  DAL_PROVA=OLCULEMEDI sebep=<...>                                     rc 2
Agac kosum oncesi kirliyse kosulmaz (OLCULEMEDI sebep=agac-kirli). Kosum sonrasi
`git status --porcelain` oncekinden farkliysa `AGAC_KIRLETILDI=<yollar>` + rc 1.

Kabul bataryasi: python3 tools/dal-deploy-prova-test.py [--agir]
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys
import time

JOB = "serit-a3"
CAPA_BAS = "Fotograftan ozel uretim kabul testi"
CAPA_SON = "Serit derinlik olcumu"
IS_AKISI = os.path.join(".github", "workflows", "deploy.yml")
KOMUT_ZAMAN_ASIMI = 1800
KIRMIZI_KUYRUK = 15
# SERIT B EK KAPILARI (BaBa tik 251 A, 27 Eki 2026): deploy.yml araliginda OLMAYAN ama dalin
# ekledigi dosya sinifina bakan SERIT B kapisi. Olculen vaka: siparis-kampanya dali DAL_PROVA
# 9/0/0 iken SERIT B 40465465588 `d1-zarf-fikstur-kapisi` EKSIK=1 ile dustu (~70 dk kosucu).
# (ad, komut, agacta bulunmasi gereken dosya) — dosya yoksa (fikstur depo) KOSULMAZ, SAYILMAZ.
EK_KAPILAR = (
    ("SERIT B ek: D1 zarf fikstur kapisi", "python3 tools/d1-zarf-fikstur-kapisi.py",
     os.path.join("tools", "d1-zarf-fikstur-kapisi.py")),
)

# Govdede bu yapilardan biri varsa satir satir bolunemez -> govde TEK komut olarak kosar.
BILESIK = re.compile(r"(\\\s*$|<<|^\s*(if|then|else|elif|fi|for|while|until|do|done|case|esac|function)\b|^\s*[{}()]\s*$)")


def _cik(satir, rc):
    print(satir, flush=True)
    sys.exit(rc)


# ----------------------------------------------------------------------------- ayristirma
def _norm_deger(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return "" if v is None else str(v)


def _adim_kur(ham):
    """Iki ayristiricinin ortak adim bicimi."""
    run = ham.get("run")
    return {
        "name": _norm_deger(ham.get("name")),
        "run": None if run is None else "\n".join(s.rstrip() for s in str(run).rstrip("\n").split("\n")),
        "env": {str(k): _norm_deger(v) for k, v in (ham.get("env") or {}).items()},
        "if": _norm_deger(ham.get("if")),
        "uses": _norm_deger(ham.get("uses")),
        "shell": _norm_deger(ham.get("shell")),
        "working-directory": _norm_deger(ham.get("working-directory")),
    }


def yaml_ayristir(metin):
    import yaml
    veri = yaml.safe_load(metin) or {}
    job = (veri.get("jobs") or {}).get(JOB)
    if not isinstance(job, dict):
        return None
    return [_adim_kur(a) for a in (job.get("steps") or [])]


def _girinti(s):
    return len(s) - len(s.lstrip(" "))


def _skaler(ham):
    ham = ham.strip()
    if ham.startswith('"'):
        cikti, i = [], 1
        while i < len(ham) and ham[i] != '"':
            if ham[i] == "\\" and i + 1 < len(ham):
                i += 1
                cikti.append({"n": "\n", "t": "\t"}.get(ham[i], ham[i]))
            else:
                cikti.append(ham[i])
            i += 1
        return "".join(cikti)
    if ham.startswith("'"):
        cikti, i = [], 1
        while i < len(ham):
            if ham[i] == "'":
                if ham[i + 1:i + 2] == "'":
                    cikti.append("'")
                    i += 2
                    continue
                break
            cikti.append(ham[i])
            i += 1
        return "".join(cikti)
    return re.sub(r"\s+#.*$", "", ham).strip()


def satir_ayristir(metin):
    """PyYAML'siz yedek: yalniz `jobs.<JOB>.steps` icin, GitHub is akisi bicimine yetecek kadar."""
    satirlar = metin.split("\n")
    bas = next((i for i, s in enumerate(satirlar) if re.match(r"^  %s:\s*(#.*)?$" % re.escape(JOB), s)), None)
    if bas is None:
        return None
    son = next((i for i in range(bas + 1, len(satirlar)) if re.match(r"^ {0,2}[^\s#]", satirlar[i])), len(satirlar))
    adim_bas = next((i for i in range(bas + 1, son) if re.match(r"^    steps:\s*$", satirlar[i])), None)
    if adim_bas is None:
        return []
    adimlar, ham, i = [], None, adim_bas + 1
    while i < son:
        s = satirlar[i]
        if not s.strip() or s.lstrip().startswith("#"):
            i += 1
            continue
        if _girinti(s) < 6:
            break
        if s.startswith("      - "):
            ham = {}
            adimlar.append(ham)
            s = " " * 8 + s[8:]
        m = re.match(r"^        ([A-Za-z_][\w-]*):(.*)$", s)
        if ham is None or not m:
            i += 1
            continue
        anahtar, deger = m.group(1), m.group(2).strip()
        i += 1
        if deger[:1] in ("|", ">"):
            govde, ic = [], None
            while i < son:
                t = satirlar[i]
                if t.strip():
                    if ic is None:
                        ic = _girinti(t)
                        if ic <= 8:
                            break
                    elif _girinti(t) < ic:
                        break
                govde.append(t[ic:] if ic is not None and t.strip() else "")
                i += 1
            while govde and not govde[-1]:
                govde.pop()
            if deger.startswith(">"):
                ham[anahtar] = re.sub(r"(?<!\n)\n(?!\n)", " ", "\n".join(govde))
            else:
                ham[anahtar] = "\n".join(govde)
        elif deger == "" or deger.startswith("#"):
            harita = {}
            while i < son:
                t = satirlar[i]
                if t.strip() and not t.lstrip().startswith("#") and _girinti(t) <= 8:
                    break
                mm = re.match(r"^\s+([^\s:#][^:]*):\s*(.*)$", t)
                if mm:
                    harita[mm.group(1).strip()] = _skaler(mm.group(2))
                i += 1
            ham[anahtar] = harita
        elif deger.startswith("{"):
            ham[anahtar] = {k.strip(): _skaler(v) for k, v in
                            (p.split(":", 1) for p in deger.strip("{} ").split(",") if ":" in p)}
        else:
            ham[anahtar] = _skaler(deger)
    return [_adim_kur(a) for a in adimlar]


def adimlari_oku(agac, ayristirici="oto"):
    yol = os.path.join(agac, IS_AKISI)
    try:
        with open(yol, encoding="utf-8") as f:
            metin = f.read()
    except OSError:
        return None, "is-akisi-yok"
    if ayristirici == "oto":
        try:
            import yaml  # noqa: F401
            ayristirici = "yaml"
        except ImportError:
            ayristirici = "satir"
    adimlar = yaml_ayristir(metin) if ayristirici == "yaml" else satir_ayristir(metin)
    if adimlar is None:
        return None, "job-yok"
    return adimlar, None


def araligi_turet(adimlar):
    """Ilk capa DAHIL, son capa HARIC. Donus: (adimlar, sebep)."""
    bas = [i for i, a in enumerate(adimlar) if a["name"].startswith(CAPA_BAS)]
    son = [i for i, a in enumerate(adimlar) if a["name"].startswith(CAPA_SON)]
    if not bas or not son:
        return None, "capa-yok"
    if len(bas) > 1 or len(son) > 1:
        return None, "capa-cift"
    if bas[0] >= son[0]:
        return None, "capa-sira"
    aralik = adimlar[bas[0]:son[0]]
    return aralik, None


def ozet_imza(a):
    return hashlib.sha1(repr(sorted(a.items())).encode("utf-8")).hexdigest()[:12]


# ----------------------------------------------------------------------------- kosum
def secret_mi(adim):
    return any("secrets." in v or "${{" in v for v in adim["env"].values())


def kosulamaz_sebep(adim):
    if secret_mi(adim):
        return "secret"
    if adim["run"] is None:
        return "uses" if adim["uses"] else "run-yok"
    if "${{" in adim["run"]:
        return "ifade"
    if adim["shell"] and adim["shell"] != "bash":
        return "shell"
    return None


def komutlar(govde):
    if any(BILESIK.search(s) for s in govde.split("\n")):
        return [govde]
    return [s.strip() for s in govde.split("\n") if s.strip() and not s.strip().startswith("#")]


def temiz_ortam():
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def porcelain(agac):
    r = subprocess.run(["git", "-C", agac, "status", "--porcelain", "--untracked-files=all"],
                       capture_output=True, text=True, env=temiz_ortam())
    return r.stdout if r.returncode == 0 else None


def komut_kos(komut, cwd):
    t0 = time.time()
    try:
        r = subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", komut], cwd=cwd,
                           env=temiz_ortam(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True, errors="replace", timeout=KOMUT_ZAMAN_ASIMI)
        rc, cikti = r.returncode, r.stdout
    except subprocess.TimeoutExpired as e:
        ham = e.stdout or ""
        rc, cikti = 124, ham.decode("utf-8", "replace") if isinstance(ham, bytes) else ham
    return rc, round(time.time() - t0, 1), cikti


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("agac")
    p.add_argument("--haric", action="append", default=[])
    p.add_argument("--liste", action="store_true", help="yalniz turetilen adim listesini bas, kosma")
    p.add_argument("--tum", action="store_true", help="--liste ile: job'in TUM adimlari")
    p.add_argument("--ayristirici", choices=("oto", "yaml", "satir"), default="oto")
    a = p.parse_args()
    agac = os.path.abspath(a.agac)

    adimlar, sebep = adimlari_oku(agac, a.ayristirici)
    if adimlar is None:
        _cik("DAL_PROVA=OLCULEMEDI sebep=%s" % sebep, 2)
    if a.liste and a.tum:
        for x in adimlar:
            print("ADIM_IMZA %s\t%s" % (ozet_imza(x), x["name"]))
        _cik("ADIM_LISTE=%d" % len(adimlar), 0)
    aralik, sebep = araligi_turet(adimlar)
    if not aralik:
        _cik("DAL_PROVA=OLCULEMEDI sebep=%s" % (sebep or "bos-aralik"), 2)
    if a.liste:
        for x in aralik:
            print("ADIM_IMZA %s\t%s" % (ozet_imza(x), x["name"]))
        _cik("ADIM_LISTE=%d" % len(aralik), 0)

    once = porcelain(agac)
    if once is None:
        _cik("DAL_PROVA=OLCULEMEDI sebep=git-yok", 2)
    if once.strip():
        print("AGAC_KIRLI=%s" % ",".join(s[3:] for s in once.splitlines()[:10]))
        _cik("DAL_PROVA=OLCULEMEDI sebep=agac-kirli", 2)

    kosulan, kirmizi, olculemedi, kosulmadi = 0, [], 0, 0
    print("DAL_PROVA_ARALIK adim=%d job=%s agac=%s" % (len(aralik), JOB, agac), flush=True)
    for no, adim in enumerate(aralik, 1):
        ad = adim["name"]
        if any(h in ad for h in a.haric):
            kosulmadi += 1
            print("ADIM=%s HAL=KOSULMADI sebep=haric" % ad, flush=True)
            continue
        if "failure()" in adim["if"]:
            kosulmadi += 1
            print("ADIM=%s HAL=KOSULMADI sebep=if-failure" % ad, flush=True)
            continue
        neden = kosulamaz_sebep(adim)
        if neden:
            olculemedi += 1
            print("ADIM=%s HAL=OLCULEMEDI sebep=%s" % (ad, neden), flush=True)
            continue
        cwd = os.path.join(agac, adim["working-directory"]) if adim["working-directory"] else agac
        t0, kirmizi_mi = time.time(), False
        for komut in komutlar(adim["run"]):
            rc, sure, cikti = komut_kos(komut, cwd)
            print("  KOMUT adim=%d rc=%d sure=%ss :: %s" % (no, rc, sure, komut.split("\n")[0]), flush=True)
            if rc != 0:
                kirmizi_mi = True
                for s in cikti.rstrip("\n").split("\n")[-KIRMIZI_KUYRUK:]:
                    print("    | " + s, flush=True)
        kosulan += 1
        if kirmizi_mi: kirmizi.append(ad)
        print("ADIM=%s HAL=%s sure=%.1fs" % (ad, "KIRMIZI" if kirmizi_mi else "YESIL", time.time() - t0), flush=True)

    for ad, komut, dosya in EK_KAPILAR:
        if not os.path.isfile(os.path.join(agac, dosya)):
            print("EK_KAPI=%s HAL=YOK sebep=dosya-yok" % ad, flush=True)
            continue
        t0 = time.time()
        rc, sure, cikti = komut_kos(komut, agac)
        print("  KOMUT ek rc=%d sure=%ss :: %s" % (rc, sure, komut), flush=True)
        if rc != 0:
            kirmizi.append(ad)
            for s in cikti.rstrip("\n").split("\n")[-KIRMIZI_KUYRUK:]:
                print("    | " + s, flush=True)
        kosulan += 1
        print("ADIM=%s HAL=%s sure=%.1fs" % (ad, "KIRMIZI" if rc else "YESIL", time.time() - t0), flush=True)

    sonra = porcelain(agac)
    kirletilen = None
    if sonra != once:
        kirletilen = sorted(set((sonra or "").splitlines()) - set(once.splitlines())) or ["<porcelain-degisti>"]
        print("AGAC_KIRLETILDI=%s" % ",".join(s[3:] if len(s) > 3 else s for s in kirletilen), flush=True)
    if kirmizi:
        _cik("DAL_PROVA=KIRMIZI kirmizi=%d ilk=%s" % (len(kirmizi), kirmizi[0]), 1)
    if kirletilen:
        _cik("DAL_PROVA=KIRMIZI kirmizi=0 ilk=AGAC_KIRLETILDI", 1)
    _cik("DAL_PROVA=YESIL kosulan=%d kirmizi=0 olculemedi=%d kosulmadi=%d" % (kosulan, olculemedi, kosulmadi), 0)


if __name__ == "__main__":
    main()
