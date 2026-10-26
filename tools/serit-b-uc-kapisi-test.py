#!/usr/bin/env python3
"""serit-b-uc-kapisi.py kabul bataryasi — AG YOK.

gh ve git, `PRUVO_SERIT_GH` / `PRUVO_SERIT_GIT` ile gecici dizindeki sahte ikiliye
yonlendirilir; sahteler ciktilarini ENV'den okur. Mutantlar yalniz tempfile altindaki
IZOLE kopyaya uygulanir (canli govde degismez); once mutasyonsuz kopya TABAN olarak
kosulur — taban kirmiziysa her mutant "oldu" gorunurdu.

Vakalar: V1 esit+success -> ESIT rc0 · V2 bayat sha -> RED bayat-sha · V3 surmekte ·
V4 baska dal · V5 gh hatasi -> OLCULEMEDI rc2 · V6 is akisi farkli · V7 basarisiz ·
V8 git hatasi -> OLCULEMEDI · V9 bayat+cancelled (10 Eki vakasi) -> bayat-sha.
Parite satiri (ikinci satir): V10 GECTI · V11 yayin-kuyrugu borcu · V12 jeton yok · V15/V16 fikstur etiketi hukum DEGIL ·
V13 log okunamadi · V14 hijyen-a3 isi yok -> hepsi rc 0, GECTI disi BORC.
Mutantlar: M1 sha karsilastirmasi kalkar -> V2 yesil · M2 OLCULEMEDI rc 0 -> V5 ·
M3 borc GECTI'ye cevrilir -> V11 · M4 okunamayan log GECTI -> V13.
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
if sys.argv[1:2] == ["api"]:
    if "SAHTE_GH_LOG" not in os.environ:
        sys.stderr.write("gh: log yok\\n"); sys.exit(1)
    sys.stdout.write(os.environ["SAHTE_GH_LOG"]); sys.exit(0)
if sys.argv[-1] == "jobs":
    sys.stdout.write(os.environ.get("SAHTE_GH_JOBS",
        '{"jobs":[{"name":"hijyen-a2","databaseId":76},{"name":"hijyen-a3","databaseId":77}]}'))
    sys.exit(0)
sys.stdout.write(os.environ["SAHTE_GH_JSON"])
"""
LOG_GECTI = "2026-10-21T18:41:08Z   ✅ TEST 5 — parite\n2026-10-21T18:41:08Z PARITE_TEST5=GECTI\n"
LOG_KUYRUK = "2026-10-21T18:41:08Z PARITE_TEST5=OLCULEMEDI sebep=yayin-kuyrugu\n"
# Ayni job'daki fikstur adiminin ETIKET satirlari (SERIT B 40245275387'de birebir boyle):
LOG_FIKSTUR = ("2026-10-25T23:59:21Z   ✅ yayin kuyrugu jetonu: PARITE_TEST5=OLCULEMEDI "
               "sebep=yayin-kuyrugu\r\n2026-10-25T23:59:21Z   ✅ kod-senkron jetonu: "
               "PARITE_TEST5=OLCULEMEDI sebep=kod-senkron\r\n")
LOG_KOD_SENKRON = "2026-10-25T23:58:00Z PARITE_TEST5=OLCULEMEDI sebep=kod-senkron\r\n"
BORC = "SERIT_PARITE=OLCULEMEDI sebep=%s kapanis=deploy-nobeti"
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
        # PARITE SATIRI (ikinci satir): GECTI disi her hal borc; rc DEGISMEZ.
        ("V10", {"SAHTE_GH_JSON": kosum(ad), "SAHTE_GH_LOG": LOG_GECTI}, 0,
         f"SERIT_UC=ESIT run={RUN} sha={UC[:12]}", "SERIT_PARITE=GECTI"),
        ("V11", {"SAHTE_GH_JSON": kosum(ad), "SAHTE_GH_LOG": LOG_GECTI + LOG_KUYRUK}, 0,
         f"SERIT_UC=ESIT run={RUN} sha={UC[:12]}", BORC % "yayin-kuyrugu"),
        ("V12", {"SAHTE_GH_JSON": kosum(ad), "SAHTE_GH_LOG": "TEST 5 yok\n"}, 0,
         f"SERIT_UC=ESIT run={RUN} sha={UC[:12]}", BORC % "jeton-yok"),
        ("V13", {"SAHTE_GH_JSON": kosum(ad)}, 0,
         f"SERIT_UC=ESIT run={RUN} sha={UC[:12]}", BORC % "log-okunamadi"),
        ("V14", {"SAHTE_GH_JSON": kosum(ad), "SAHTE_GH_LOG": LOG_GECTI,
                 "SAHTE_GH_JOBS": '{"jobs":[{"name":"hijyen-a2","databaseId":76}]}'}, 0,
         f"SERIT_UC=ESIT run={RUN} sha={UC[:12]}", BORC % "log-okunamadi"),
        # V15/V16 (26 Eki): fikstur ETIKETI hukum DEGILDIR — yalniz kendi satirindaki jeton.
        ("V15", {"SAHTE_GH_JSON": kosum(ad), "SAHTE_GH_LOG": LOG_GECTI + LOG_FIKSTUR}, 0,
         f"SERIT_UC=ESIT run={RUN} sha={UC[:12]}", "SERIT_PARITE=GECTI"),
        ("V16", {"SAHTE_GH_JSON": kosum(ad), "SAHTE_GH_LOG": LOG_KOD_SENKRON + LOG_FIKSTUR}, 0,
         f"SERIT_UC=ESIT run={RUN} sha={UC[:12]}", BORC % "kod-senkron"),
    ]


def calistir(kapi, sahte, env_ek):
    env = {k: v for k, v in os.environ.items() if not k.startswith("SAHTE_")}
    env.update({"PRUVO_SERIT_GH": sahte["gh"], "PRUVO_SERIT_GIT": sahte["git"],
                "SAHTE_GIT_SHA": UC})
    env.update(env_ek)
    p = subprocess.run([sys.executable, kapi, DAL, RUN], capture_output=True, text=True,
                       env=env, timeout=60)
    satirlar = p.stdout.splitlines() + ["", ""]
    return p.returncode, satirlar[0], satirlar[1]


def tutar(vaka, rc, ilk, ikinci):
    """Vaka beklentisi: rc + ilk satir (+ verildiyse ikinci satir) birebir."""
    _, _, b_rc, b_satir, *b_ikinci = vaka
    return rc == b_rc and ilk == b_satir and (not b_ikinci or ikinci == b_ikinci[0])


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
    # On-kosul kapanmadiginda (yayin kuyrugu) GECTI basan surum KIRMIZI yakmali.
    ("M3", "parite borcu GECTI'ye cevrildi",
     ('if all(h == "GECTI" for h, _ in jetonlar):', "if True:"), "V11"),
    ("M4", "okunamayan log GECTI sayildi",
     ('        return borc % "log-okunamadi"', '        return "SERIT_PARITE=GECTI"'), "V13"),
    # Satir sabiti kalkarsa fikstur etiketi GERCEK GECTI'yi borca cevirir (40245275387 vakasi).
    ("M5", "jeton satira sabitli degil",
     ('PARITE_JETON = re.compile(r"^(?:\\S+ )?PARITE_TEST5=', 'PARITE_JETON = re.compile(r"PARITE_TEST5='),
     "V15"),
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

        for vaka in tablo.values():
            rc, ilk, ikinci = calistir(KAPI, sahte, vaka[1])
            ok = tutar(vaka, rc, ilk, ikinci)
            hata += not ok
            print(f"{'YESIL' if ok else 'KIRMIZI'} {vaka[0]} rc={rc} (beklenen {vaka[2]}) | "
                  f"{ilk}{' | ' + ikinci if len(vaka) > 4 else ''}")

        # TABAN: mutasyonsuz izole kopya, mutantlarin hedef vakalarinda yesil olmali
        taban = izole_kopya(os.path.join(gecici, "taban"))
        for _, _, _, hedef in MUTANTLAR:
            rc, ilk, ikinci = calistir(taban, sahte, tablo[hedef][1])
            ok = tutar(tablo[hedef], rc, ilk, ikinci)
            hata += not ok
            print(f"{'YESIL' if ok else 'KIRMIZI'} TABAN-{hedef} rc={rc} | {ilk} | {ikinci}")

        for kimlik, aciklama, mutasyon, hedef in MUTANTLAR:
            kopya = izole_kopya(os.path.join(gecici, kimlik), mutasyon)
            rc, ilk, ikinci = calistir(kopya, sahte, tablo[hedef][1])
            yakalandi = not tutar(tablo[hedef], rc, ilk, ikinci)
            hata += not yakalandi
            print(f"{'YAKALANDI' if yakalandi else 'KACTI'} {kimlik} ({aciklama}) -> "
                  f"{hedef} rc={rc} | {ilk} | {ikinci}")
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    print(f"SONUC: {'YESIL' if hata == 0 else 'KIRMIZI'} hata={hata}")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
