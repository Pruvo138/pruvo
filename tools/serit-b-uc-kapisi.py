#!/usr/bin/env python3
"""SERIT B UCU KAPISI — merge edilen SHA'nin SERIT B kosumu var mi?

Olculen ariza (10 Eki 2026): dal SERIT B kosumu `38029942603` headSha `9d2aa8e8` iken
dal ucu `aec9b6e2` idi (2 dosya fark) — "yesil SERIT B" merge'e yetiyor sanildi, ama
yesil olan SHA merge edilen SHA degildi. Bu kapi o boslugu kapatir.

Kullanim: python3 tools/serit-b-uc-kapisi.py <dal> <run_id>

Hukum (tek satir, jetonlar ayrik):
  SERIT_UC=ESIT run=<id> sha=<12>          rc 0 — headSha == origin/<dal> ucu
                                                  ∧ headBranch == dal ∧ completed ∧ success
                                                  ∧ workflowName == nobet.yml `name:`
  SERIT_UC=RED sebep=<...>                 rc 1 — is-akisi-farkli | dal-farkli | bayat-sha
                                                  | surmekte | basarisiz
  SERIT_UC=OLCULEMEDI sebep=<...>          rc 2 — gh/git hatasi; ASLA sessiz yesil

Kontrol sirasi: is-akisi → dal → sha → durum → sonuc. SHA, durumdan ONCE: bayat bir
kosumun sonucu ne olursa olsun bu dal ucu icin hukum tasimaz.

Test icin `PRUVO_SERIT_GH` / `PRUVO_SERIT_GIT` sahte ikiliye yonlendirir (ag YOK).
"""
import json
import os
import re
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOBET_YML = os.path.join(KOK, ".github", "workflows", "nobet.yml")
REPO = "Pruvo138/pruvo"
GH = os.environ.get("PRUVO_SERIT_GH", "gh")
GIT = os.environ.get("PRUVO_SERIT_GIT", "git")


def olculemedi(sebep):
    print(f"SERIT_UC=OLCULEMEDI sebep={sebep}")
    return 2


def red(sebep, ayrinti):
    print(f"SERIT_UC=RED sebep={sebep}")
    print(f"  {ayrinti}", file=sys.stderr)
    return 1


def is_akisi_adi():
    """nobet.yml'nin ust duzey `name:` degeri (tek kaynak; elle kopyalanmaz)."""
    try:
        with open(NOBET_YML, encoding="utf-8") as f:
            for satir in f:
                m = re.match(r"^name:\s*(.+?)\s*$", satir)
                if m:
                    ad = m.group(1)
                    if len(ad) >= 2 and ad[0] == ad[-1] and ad[0] in "\"'":
                        ad = ad[1:-1]
                    return ad
    except OSError:
        return None
    return None


def kos(argv):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=120, cwd=KOK)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    return p.stdout


def main(argv):
    if len(argv) != 3:
        print("kullanim: serit-b-uc-kapisi.py <dal> <run_id>", file=sys.stderr)
        return olculemedi("arguman")
    dal, run_id = argv[1], argv[2]
    if not run_id.isdigit() or not dal or dal.startswith("-") or ".." in dal:
        return olculemedi("arguman")

    beklenen_ad = is_akisi_adi()
    if not beklenen_ad:
        return olculemedi("nobet-yml-adi")

    cikti = kos([GH, "run", "view", run_id, "--repo", REPO,
                 "--json", "headSha,headBranch,status,conclusion,workflowName"])
    if cikti is None:
        return olculemedi("gh")
    try:
        kosum = json.loads(cikti)
        head_sha = kosum["headSha"]
        head_dal = kosum["headBranch"]
        durum = kosum["status"]
        sonuc = kosum["conclusion"]
        is_akisi = kosum["workflowName"]
    except (ValueError, KeyError, TypeError):
        return olculemedi("gh-json")
    if not isinstance(head_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", head_sha):
        return olculemedi("gh-json")

    if kos([GIT, "fetch", "--quiet", "origin",
            f"+refs/heads/{dal}:refs/remotes/origin/{dal}"]) is None:
        return olculemedi("git-fetch")
    uc = kos([GIT, "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{dal}"])
    uc = (uc or "").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", uc):
        return olculemedi("git-rev-parse")

    if is_akisi != beklenen_ad:
        return red("is-akisi-farkli", f"kosum is akisi={is_akisi!r} beklenen={beklenen_ad!r}")
    if head_dal != dal:
        return red("dal-farkli", f"kosum dali={head_dal} istenen={dal}")
    if head_sha != uc:
        return red("bayat-sha", f"kosum sha={head_sha[:12]} dal ucu={uc[:12]} -> yeni dispatch")
    if durum != "completed":
        return red("surmekte", f"status={durum}")
    if sonuc != "success":
        return red("basarisiz", f"conclusion={sonuc}")

    print(f"SERIT_UC=ESIT run={run_id} sha={uc[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
