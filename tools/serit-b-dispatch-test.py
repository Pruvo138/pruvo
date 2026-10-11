#!/usr/bin/env python3
"""serit-b-dispatch.py kabul bataryasi — AG YOK.

gh ve git, `PRUVO_SERIT_GH` / `PRUVO_SERIT_GIT` ile gecici dizindeki sahte ikiliye
yonlendirilir; sahteler ciktilarini ENV'den okur, gh her cagriyi SAHTE_GH_LOG'a yazar
(`gh workflow run` CAGRILDI MI olcumu buradan). Mutantlar yalniz tempfile altindaki IZOLE
kopyaya uygulanir; once mutasyonsuz kopya TABAN olarak TUM vakalarda kosulur — taban
kirmiziysa her mutant "oldu" gorunurdu. Her mutant TUM vakalara karsi kosulur ve kirmizi
kume TAM OLARAK hedef kumeye esit olmalidir (fazlasi da eksigi de KIRMIZI).

Vakalar: atasi -> OK (dispatch) · bayat -> RED bayat-taban geride=7 (dispatch YOK) ·
eszamanli -> RED eszamanli-dal · push-kosumu (event=push surmekte) -> ENGELLEMEZ, OK ·
git-hatasi -> OLCULEMEDI rc2 · gh-hatasi -> OLCULEMEDI rc2 · kuru -> KURU-GECER (dispatch YOK).
Mutantlar: MA ancestor kontrolu kalkar -> {bayat} · ME eszamanlilik kontrolu kalkar -> {eszamanli}.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools", "serit-b-dispatch.py")
UC_KAPISI = os.path.join(KOK, "tools", "serit-b-uc-kapisi.py")
NOBET_YML = os.path.join(KOK, ".github", "workflows", "nobet.yml")
DAL = "kral/ornek-dal"
UC = "a" * 40

SAHTE_GH = """import json, os, sys
with open(os.environ["SAHTE_GH_LOG"], "a", encoding="utf-8") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
if os.environ.get("SAHTE_GH_RC", "0") != "0":
    sys.stderr.write("gh: sahte hata\\n"); sys.exit(int(os.environ["SAHTE_GH_RC"]))
if sys.argv[1:3] == ["workflow", "run"]:
    sys.exit(0)
if sys.argv[1:3] == ["run", "list"]:
    anahtar = "SAHTE_GH_SONRA" if "--branch" in sys.argv else "SAHTE_GH_LIST"
    sys.stdout.write(os.environ.get(anahtar, "[]"))
"""
SAHTE_GIT = """import os, sys
if os.environ.get("SAHTE_GIT_RC", "0") != "0":
    sys.exit(int(os.environ["SAHTE_GIT_RC"]))
if "merge-base" in sys.argv:
    sys.exit(int(os.environ.get("SAHTE_GIT_ATA", "0")))
if "rev-list" in sys.argv:
    sys.stdout.write(os.environ.get("SAHTE_GIT_GERIDE", "0") + "\\n")
if "rev-parse" in sys.argv:
    sys.stdout.write(os.environ["SAHTE_GIT_SHA"] + "\\n")
"""


def is_akisi_adi():
    import importlib.util
    spec = importlib.util.spec_from_file_location("serit_kapi", UC_KAPISI)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.is_akisi_adi()


def sahte_kur(dizin):
    yollar = {}
    for ad, govde in (("gh", SAHTE_GH), ("git", SAHTE_GIT)):
        yol = os.path.join(dizin, ad)
        with open(yol, "w", encoding="utf-8") as f:
            f.write(f"#!{sys.executable}\n" + govde)
        os.chmod(yol, 0o755)
        yollar[ad] = yol
    return yollar


def kosum(ad, run_id, status="completed", event="workflow_dispatch", dal=DAL, sha=UC):
    return {"databaseId": run_id, "status": status, "event": event, "headBranch": dal,
            "headSha": sha, "workflowName": ad}


def vakalar(ad):
    eski = kosum(ad, 555)  # ayni dalin onceki (bitmis) dispatch kosumu
    yeni = kosum(ad, 777, status="queued")
    sonra = json.dumps([yeni, eski])
    # (kimlik, env, ek arguman, beklenen rc, beklenen ilk satir, dispatch cagrildi mi)
    return [
        ("atasi", {"SAHTE_GH_LIST": json.dumps([eski]), "SAHTE_GH_SONRA": sonra}, [], 0,
         f"SERIT_B_DISPATCH=OK run=777 sha={UC[:12]}", True),
        ("bayat", {"SAHTE_GIT_ATA": "1", "SAHTE_GIT_GERIDE": "7",
                   "SAHTE_GH_LIST": json.dumps([eski]), "SAHTE_GH_SONRA": sonra}, [], 1,
         "SERIT_B_DISPATCH=RED sebep=bayat-taban geride=7", False),
        ("eszamanli", {"SAHTE_GH_LIST": json.dumps(
            [kosum(ad, 999, status="in_progress", dal="kral/baska-dal", sha="c" * 40), eski]),
            "SAHTE_GH_SONRA": sonra}, [], 1,
         "SERIT_B_DISPATCH=RED sebep=eszamanli-dal run=999 dal=kral/baska-dal", False),
        ("push-kosumu", {"SAHTE_GH_LIST": json.dumps(
            [kosum(ad, 888, status="in_progress", event="push", dal="main", sha="d" * 40)]),
            "SAHTE_GH_SONRA": sonra}, [], 0,
         f"SERIT_B_DISPATCH=OK run=777 sha={UC[:12]}", True),
        ("git-hatasi", {"SAHTE_GIT_RC": "128", "SAHTE_GH_SONRA": sonra}, [], 2,
         "SERIT_B_DISPATCH=OLCULEMEDI sebep=git-fetch", False),
        ("gh-hatasi", {"SAHTE_GH_RC": "1", "SAHTE_GH_SONRA": sonra}, [], 2,
         "SERIT_B_DISPATCH=OLCULEMEDI sebep=gh-run-list", False),
        ("kuru", {"SAHTE_GH_LIST": json.dumps([eski]), "SAHTE_GH_SONRA": sonra}, ["--kuru"], 0,
         "SERIT_B_DISPATCH=KURU-GECER", False),
    ]


def calistir(arac, sahte, env_ek, ek_arg, log):
    if os.path.exists(log):
        os.remove(log)
    env = {k: v for k, v in os.environ.items() if not k.startswith("SAHTE_")}
    env.update({"PRUVO_SERIT_GH": sahte["gh"], "PRUVO_SERIT_GIT": sahte["git"],
                "PRUVO_SERIT_BEKLE": "0", "SAHTE_GIT_SHA": UC, "SAHTE_GH_LOG": log})
    env.update(env_ek)
    p = subprocess.run([sys.executable, arac, DAL] + ek_arg, capture_output=True, text=True,
                       env=env, timeout=60)
    ilk = (p.stdout.splitlines() or [""])[0]
    cagrildi = False
    if os.path.exists(log):
        with open(log, encoding="utf-8") as f:
            cagrildi = any(json.loads(s)[:2] == ["workflow", "run"] for s in f if s.strip())
    return p.returncode, ilk, cagrildi


def vaka_kos(arac, sahte, vaka, log):
    kimlik, env_ek, ek_arg, b_rc, b_satir, b_cagri = vaka
    rc, ilk, cagrildi = calistir(arac, sahte, env_ek, ek_arg, log)
    ok = rc == b_rc and ilk == b_satir and cagrildi == b_cagri
    return ok, f"{kimlik} rc={rc} (beklenen {b_rc}) dispatch={cagrildi} | {ilk}"


def izole_kopya(kok, mutasyon=None):
    """kok altina arac + uc-kapisi (is_akisi_adi kaynagi) + nobet.yml kopyasi."""
    os.makedirs(os.path.join(kok, "tools"))
    os.makedirs(os.path.join(kok, ".github", "workflows"))
    shutil.copy(NOBET_YML, os.path.join(kok, ".github", "workflows", "nobet.yml"))
    shutil.copy(UC_KAPISI, os.path.join(kok, "tools", "serit-b-uc-kapisi.py"))
    with open(ARAC, encoding="utf-8") as f:
        govde = f.read()
    if mutasyon:
        eski, yeni = mutasyon
        if govde.count(eski) != 1:
            raise SystemExit(f"MUTANT CAPASI TUTMADI ({govde.count(eski)} eslesme): {eski!r}")
        govde = govde.replace(eski, yeni)
    hedef = os.path.join(kok, "tools", "serit-b-dispatch.py")
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(govde)
    return hedef


MUTANTLAR = [
    ("MA", "ancestor kontrolu kaldirildi", ("if ata_rc == 1:", "if False:"), {"bayat"}),
    ("ME", "eszamanlilik kontrolu kaldirildi", ("if aktif:", "if False:"), {"eszamanli"}),
]


def main():
    ad = is_akisi_adi()
    if not ad:
        print("KIRMIZI: nobet.yml `name:` okunamadi")
        return 1
    hata = 0
    gecici = tempfile.mkdtemp(prefix="serit-b-dispatch-test-")
    try:
        sahte = sahte_kur(gecici)
        log = os.path.join(gecici, "gh.log")
        liste = vakalar(ad)

        for vaka in liste:
            ok, satir = vaka_kos(ARAC, sahte, vaka, log)
            hata += not ok
            print(f"{'YESIL' if ok else 'KIRMIZI'} {satir}")

        taban = izole_kopya(os.path.join(gecici, "taban"))
        for vaka in liste:
            ok, satir = vaka_kos(taban, sahte, vaka, log)
            hata += not ok
            print(f"{'YESIL' if ok else 'KIRMIZI'} TABAN-{satir}")

        for kimlik, aciklama, mutasyon, hedef in MUTANTLAR:
            kopya = izole_kopya(os.path.join(gecici, kimlik), mutasyon)
            kirmizi = set()
            for vaka in liste:
                ok, _ = vaka_kos(kopya, sahte, vaka, log)
                if not ok:
                    kirmizi.add(vaka[0])
            tam = kirmizi == hedef
            hata += not tam
            print(f"{'YAKALANDI' if tam else 'KACTI'} {kimlik} ({aciklama}) kirmizi="
                  f"{sorted(kirmizi)} beklenen={sorted(hedef)}")
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    print(f"SONUC: {'YESIL' if hata == 0 else 'KIRMIZI'} hata={hata}")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
