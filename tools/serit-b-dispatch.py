#!/usr/bin/env python3
"""SERIT B DISPATCH KAPISI — dal SERIT B'ye gonderilmeden ONCE bayat taban + eszamanlilik.

Olculen ariza (K438 10 Eki, K434 11 Eki 2026): dal main'in GERISINDEN SERIT B'ye
gonderildi; dalin `urunler.json`'u canli D1'den farkli oldugu icin `hijyen-a3` ->
`filament-test.py` TEST 5 parite KIRMIZI yandi, ~90 dk kosucu bosa gitti. Kural: dal ucu
`origin/main`'i ICERMIYORSA dispatch YAPILMAZ. Ayrica ayni anda ikinci bir dal SERIT B
kosumu kosucu tavanina carpar / yayini iptal ettirir -> o da RED.

Kullanim: python3 tools/serit-b-dispatch.py <dal> [--kuru]

Hukum (tek satir, jetonlar ayrik):
  SERIT_B_DISPATCH=OK run=<id> sha=<12>              rc 0 — dispatch edildi, kosum bulundu
  SERIT_B_DISPATCH=KURU-GECER                        rc 0 — --kuru: kontroller gecti,
                                                            gh workflow run CAGRILMADI
  SERIT_B_DISPATCH=RED sebep=bayat-taban geride=<n>  rc 1 — origin/main dal ucunun atasi degil
  SERIT_B_DISPATCH=RED sebep=eszamanli-dal run=<id> dal=<d>
                                                     rc 1 — ayni is akisinda sirada/surmekte
                                                            bir workflow_dispatch kosumu var
  SERIT_B_DISPATCH=OLCULEMEDI sebep=<...>            rc 2 — gh/git hatasi; ASLA sessiz yesil

RED/OLCULEMEDI yolunda `gh workflow run` CAGRILMAZ. Is akisi adi `serit-b-uc-kapisi.py`
`is_akisi_adi()`'ndan okunur (tek kaynak; kopyalanmaz). Test icin `PRUVO_SERIT_GH` /
`PRUVO_SERIT_GIT` sahte ikiliye yonlendirir (ag YOK).
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UC_KAPISI = os.path.join(KOK, "tools", "serit-b-uc-kapisi.py")
REPO = "Pruvo138/pruvo"
GH = os.environ.get("PRUVO_SERIT_GH", "gh")
GIT = os.environ.get("PRUVO_SERIT_GIT", "git")
AKTIF = ("queued", "in_progress", "pending", "waiting")
ARAMA_TUR = 10
ARAMA_BEKLE = float(os.environ.get("PRUVO_SERIT_BEKLE", "3"))


def olculemedi(sebep):
    print(f"SERIT_B_DISPATCH=OLCULEMEDI sebep={sebep}")
    return 2


def is_akisi_adi():
    try:
        spec = importlib.util.spec_from_file_location("serit_b_uc_kapisi", UC_KAPISI)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.is_akisi_adi()
    except (OSError, ImportError, AttributeError):
        return None


def kos_rc(argv):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=120, cwd=KOK)
    except (OSError, subprocess.TimeoutExpired):
        return None, ""
    return p.returncode, p.stdout


def kos(argv):
    rc, cikti = kos_rc(argv)
    return cikti if rc == 0 else None


def kosum_listesi(argv):
    cikti = kos(argv)
    if cikti is None:
        return None
    try:
        liste = json.loads(cikti)
    except ValueError:
        return None
    if not isinstance(liste, list) or not all(isinstance(k, dict) for k in liste):
        return None
    return liste


def main(argv):
    kuru = "--kuru" in argv[1:]
    konum = [a for a in argv[1:] if a != "--kuru"]
    if len(konum) != 1:
        print("kullanim: serit-b-dispatch.py <dal> [--kuru]", file=sys.stderr)
        return olculemedi("arguman")
    dal = konum[0]
    if not dal or dal.startswith("-") or ".." in dal:
        return olculemedi("arguman")

    beklenen_ad = is_akisi_adi()
    if not beklenen_ad:
        return olculemedi("nobet-yml-adi")

    # (a) taze uclar
    if kos([GIT, "fetch", "--quiet", "origin",
            "+refs/heads/main:refs/remotes/origin/main",
            f"+refs/heads/{dal}:refs/remotes/origin/{dal}"]) is None:
        return olculemedi("git-fetch")
    uc = (kos([GIT, "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{dal}"]) or "").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", uc):
        return olculemedi("git-rev-parse")

    # (b) bayat taban: origin/main dal ucunun atasi mi?
    ata_rc, _ = kos_rc([GIT, "merge-base", "--is-ancestor",
                        "refs/remotes/origin/main", f"refs/remotes/origin/{dal}"])
    if ata_rc not in (0, 1):
        return olculemedi("git-merge-base")
    if ata_rc == 1:
        geride = (kos([GIT, "rev-list", "--count",
                       f"refs/remotes/origin/{dal}..refs/remotes/origin/main"]) or "").strip()
        if not geride.isdigit():
            return olculemedi("git-rev-list")
        print(f"SERIT_B_DISPATCH=RED sebep=bayat-taban geride={geride}")
        print("  dalı `git rebase origin/main` ile yeniden kur; yeniden yazılan dal YENİ adla "
              "itilir (K80)", file=sys.stderr)
        return 1

    # (c) ayni is akisinda sirada/surmekte workflow_dispatch kosumu
    liste = kosum_listesi([GH, "run", "list", "--repo", REPO, "--workflow", "nobet.yml",
                           "--event", "workflow_dispatch", "--limit", "30", "--json",
                           "databaseId,status,event,headBranch,headSha,workflowName"])
    if liste is None:
        return olculemedi("gh-run-list")
    aktif = [k for k in liste
             if k.get("event") == "workflow_dispatch"
             and k.get("workflowName") == beklenen_ad
             and k.get("status") in AKTIF]
    if aktif:
        k = aktif[0]
        print(f"SERIT_B_DISPATCH=RED sebep=eszamanli-dal run={k.get('databaseId')} "
              f"dal={k.get('headBranch')}")
        print("  onceki SERIT B kosumu bitmeden ikinci dal gonderilmez (kosucu tavani / "
              "yayin iptali)", file=sys.stderr)
        return 1

    if kuru:
        print("SERIT_B_DISPATCH=KURU-GECER")
        return 0

    # (d) dispatch + yeni kosumu bul
    onceki = {k.get("databaseId") for k in liste}
    if kos([GH, "workflow", "run", "nobet.yml", "--repo", REPO, "--ref", dal]) is None:
        return olculemedi("gh-workflow-run")
    for tur in range(ARAMA_TUR):
        sonra = kosum_listesi([GH, "run", "list", "--repo", REPO, "--workflow", "nobet.yml",
                               "--event", "workflow_dispatch", "--branch", dal, "--limit", "10",
                               "--json", "databaseId,status,event,headBranch,headSha,workflowName"])
        if sonra is None:
            return olculemedi("gh-run-list")
        for k in sonra:
            if (k.get("event") == "workflow_dispatch" and k.get("headBranch") == dal
                    and k.get("headSha") == uc and k.get("databaseId") not in onceki):
                print(f"SERIT_B_DISPATCH=OK run={k.get('databaseId')} sha={uc[:12]}")
                return 0
        if tur + 1 < ARAMA_TUR:
            time.sleep(ARAMA_BEKLE)
    return olculemedi("dispatch-kosumu-bulunamadi")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
