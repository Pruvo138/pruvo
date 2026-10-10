#!/usr/bin/env python3
"""serit-b-uc-kapisi.py kabul bataryasi — AG YOK.

gh ve git, `PRUVO_SERIT_GH` / `PRUVO_SERIT_GIT` ile gecici dizindeki sahte ikiliye
yonlendirilir; sahteler ciktilarini ENV'den okur. Mutantlar yalniz tempfile altindaki
IZOLE kopyaya uygulanir (canli govde degismez); once mutasyonsuz kopya TABAN olarak
kosulur — taban kirmiziysa her mutant "oldu" gorunurdu.

Vakalar: V1 esit+success -> ESIT rc0 · V2 bayat sha -> RED bayat-sha · V3 surmekte ·
V4 baska dal · V5 gh hatasi -> OLCULEMEDI rc2 · V6 is akisi farkli · V7 basarisiz ·
V8 git hatasi -> OLCULEMEDI · V9 bayat+cancelled (10 Eki vakasi) -> bayat-sha.
Mutantlar: M1 sha karsilastirmasi kalkar -> V2 yesil · M2 OLCULEMEDI rc 0 -> V5.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAPI = os.path.join(KOK, "tools", "serit-b-uc-kapisi.py")
NOBET_YML = os.path.join(KOK, ".github", "workflows", "nobet.yml")
DAL = "kral/ornek-dal"
UC = "a" * 40
BAYAT = "b" * 40
RUN = "123456"

SAHTE_GH = """import os, sys
if os.environ.get("SAHTE_GH_RC", "0") != "0":
    sys.stderr.write("gh: sahte hata\\n"); sys.exit(int(os.environ["SAHTE_GH_RC"]))
sys.stdout.write(os.environ["SAHTE_GH_JSON"])
"""
SAHTE_GIT = """import os, sys
if os.environ.get("SAHTE_GIT_RC", "0") != "0":
    sys.exit(int(os.environ["SAHTE_GIT_RC"]))
if "rev-parse" in sys.argv:
    sys.stdout.write(os.environ["SAHTE_GIT_SHA"] + "\\n")
"""


def is_akisi_adi():
    import importlib.util
    spec = importlib.util.spec_from_file_location("serit_kapi", KAPI)
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


def kosum(ad, sha=UC, dal=DAL, status="completed", conclusion="success", is_akisi=None):
    return json.dumps({"headSha": sha, "headBranch": dal, "status": status,
                       "conclusion": conclusion, "workflowName": is_akisi or ad})


def vakalar(ad):
    # (kimlik, env, beklenen rc, beklenen ilk satir)
    return [
        ("V1", {"SAHTE_GH_JSON": kosum(ad)}, 0, f"SERIT_UC=ESIT run={RUN} sha={UC[:12]}"),
        ("V2", {"SAHTE_GH_JSON": kosum(ad, sha=BAYAT)}, 1, "SERIT_UC=RED sebep=bayat-sha"),
        ("V3", {"SAHTE_GH_JSON": kosum(ad, status="in_progress", conclusion="")}, 1,
         "SERIT_UC=RED sebep=surmekte"),
        ("V4", {"SAHTE_GH_JSON": kosum(ad, dal="kral/baska-dal")}, 1,
         "SERIT_UC=RED sebep=dal-farkli"),
        ("V5", {"SAHTE_GH_JSON": kosum(ad), "SAHTE_GH_RC": "1"}, 2,
         "SERIT_UC=OLCULEMEDI sebep=gh"),
        ("V6", {"SAHTE_GH_JSON": kosum(ad, is_akisi="Yayin")}, 1,
         "SERIT_UC=RED sebep=is-akisi-farkli"),
        ("V7", {"SAHTE_GH_JSON": kosum(ad, conclusion="failure")}, 1,
         "SERIT_UC=RED sebep=basarisiz"),
        ("V8", {"SAHTE_GH_JSON": kosum(ad), "SAHTE_GIT_RC": "128"}, 2,
         "SERIT_UC=OLCULEMEDI sebep=git-fetch"),
        ("V9", {"SAHTE_GH_JSON": kosum(ad, sha=BAYAT, conclusion="cancelled")}, 1,
         "SERIT_UC=RED sebep=bayat-sha"),
    ]


def calistir(kapi, sahte, env_ek):
    env = {k: v for k, v in os.environ.items() if not k.startswith("SAHTE_")}
    env.update({"PRUVO_SERIT_GH": sahte["gh"], "PRUVO_SERIT_GIT": sahte["git"],
                "SAHTE_GIT_SHA": UC})
    env.update(env_ek)
    p = subprocess.run([sys.executable, kapi, DAL, RUN], capture_output=True, text=True,
                       env=env, timeout=60)
    ilk = (p.stdout.splitlines() or [""])[0]
    return p.returncode, ilk


def izole_kopya(kok, mutasyon=None):
    """kok altina tools/serit-b-uc-kapisi.py + .github/workflows/nobet.yml kopyasi."""
    os.makedirs(os.path.join(kok, "tools"))
    os.makedirs(os.path.join(kok, ".github", "workflows"))
    shutil.copy(NOBET_YML, os.path.join(kok, ".github", "workflows", "nobet.yml"))
    with open(KAPI, encoding="utf-8") as f:
        govde = f.read()
    if mutasyon:
        eski, yeni = mutasyon
        if govde.count(eski) != 1:
            raise SystemExit(f"MUTANT CAPASI TUTMADI ({govde.count(eski)} eslesme): {eski!r}")
        govde = govde.replace(eski, yeni)
    hedef = os.path.join(kok, "tools", "serit-b-uc-kapisi.py")
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(govde)
    return hedef


MUTANTLAR = [
    ("M1", "sha karsilastirmasi kaldirildi", ("if head_sha != uc:", "if False:"), "V2"),
    ("M2", "OLCULEMEDI rc 0'a cevrildi",
     ('print(f"SERIT_UC=OLCULEMEDI sebep={sebep}")\n    return 2',
      'print(f"SERIT_UC=OLCULEMEDI sebep={sebep}")\n    return 0'), "V5"),
]


def main():
    ad = is_akisi_adi()
    if not ad:
        print("KIRMIZI: nobet.yml `name:` okunamadi")
        return 1
    hata = 0
    gecici = tempfile.mkdtemp(prefix="serit-b-uc-test-")
    try:
        sahte = sahte_kur(gecici)
        tablo = {v[0]: v for v in vakalar(ad)}

        for kimlik, env_ek, b_rc, b_satir in tablo.values():
            rc, ilk = calistir(KAPI, sahte, env_ek)
            ok = rc == b_rc and ilk == b_satir
            hata += not ok
            print(f"{'YESIL' if ok else 'KIRMIZI'} {kimlik} rc={rc} (beklenen {b_rc}) | {ilk}")

        # TABAN: mutasyonsuz izole kopya, mutantlarin hedef vakalarinda yesil olmali
        taban = izole_kopya(os.path.join(gecici, "taban"))
        for _, _, _, hedef in MUTANTLAR:
            _, env_ek, b_rc, b_satir = tablo[hedef]
            rc, ilk = calistir(taban, sahte, env_ek)
            ok = rc == b_rc and ilk == b_satir
            hata += not ok
            print(f"{'YESIL' if ok else 'KIRMIZI'} TABAN-{hedef} rc={rc} | {ilk}")

        for kimlik, aciklama, mutasyon, hedef in MUTANTLAR:
            kopya = izole_kopya(os.path.join(gecici, kimlik), mutasyon)
            _, env_ek, b_rc, b_satir = tablo[hedef]
            rc, ilk = calistir(kopya, sahte, env_ek)
            yakalandi = not (rc == b_rc and ilk == b_satir)
            hata += not yakalandi
            print(f"{'YAKALANDI' if yakalandi else 'KACTI'} {kimlik} ({aciklama}) -> "
                  f"{hedef} rc={rc} | {ilk}")
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    print(f"SONUC: {'YESIL' if hata == 0 else 'KIRMIZI'} hata={hata}")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
