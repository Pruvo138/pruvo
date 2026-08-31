#!/usr/bin/env python3
"""K352 — `gh` ÇAĞRILARI İÇİN TEK KAYNAK: repo kökü + slug + ÇİVİLİ argv.

🔴 NEDEN VAR (ölçüldü, 29-30 Ağu 2026):
`gh run list` çağrıldığı sürecin **cwd'sinden** repo çözer. `~/.claude/cron/` hattı
`$HOME`'dan koşuyor ve orası git deposu DEĞİL → `failed to determine base repo:
... not a git repository`, rc=1. Sabah spec'i bu yüzden iki gün üst üste
`CI=OLCULEMEDI` doğdu. K333 `gh` İKİLİSİNİN yerini çözmüştü; `gh`'ın REPO'yu
çözmesi açık kalmıştı — bu modül o ekseni kapatır.

SÖZLEŞME:
  * `REPO_KOK`  — tek kaynak repo kökü (mutlak yol).
  * `slug()`    — `Pruvo138/pruvo`; `git remote get-url origin`'den TÜRETİLİR,
                  ELLE YAZILMAZ. Çözülemezse `None` döner (`0`/`""` DEĞİL).
  * `gh_argv()` — verilen `gh` argümanlarını **çivili** argv'ye çevirir.
  * `gh_kwargs()` — `subprocess.run` için `cwd=REPO_KOK` taşıyan kwargs.

Bir çağrı yeri ya `-R <slug>` taşır ya `cwd=REPO_KOK` ile koşar; ikisi de yoksa
`tools/gh-civi-nobetcisi.py` o yeri **ADIYLA** `CIVISIZ` basar.
"""
from __future__ import annotations

import os
import subprocess

# ── TEK KAYNAK ───────────────────────────────────────────────────────────────
REPO_KOK = "/Users/okan/dev/pruvo"

# `gh` ikilisi için aday tam yollar (K333 ekseni — PATH'e SORULMAZ).
GH_ADAY_YOLLARI = (
    "/opt/homebrew/bin/gh",
    "/usr/local/bin/gh",
    "/opt/local/bin/gh",
    "/usr/bin/gh",
)

_slug_onbellek: tuple[bool, str | None] = (False, None)


def gh_yolu() -> str | None:
    """Çalıştırılabilir `gh` tam yolu; bulunamazsa None (boş dizge DEĞİL)."""
    for y in GH_ADAY_YOLLARI:
        if os.path.isfile(y) and os.access(y, os.X_OK):
            return y
    return None


def slug() -> str | None:
    """`owner/repo`; git remote'tan TÜRETİLİR. Çözülemezse None."""
    global _slug_onbellek
    if _slug_onbellek[0]:
        return _slug_onbellek[1]
    deger = None
    try:
        r = subprocess.run(
            ["git", "-C", REPO_KOK, "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode == 0:
            url = r.stdout.strip()
            if url.endswith(".git"):
                url = url[:-4]
            if url.startswith("git@") and ":" in url:
                url = url.split(":", 1)[1]
            elif "://" in url:
                url = url.split("://", 1)[1]
                url = url.split("/", 1)[1] if "/" in url else url
            parcalar = [p for p in url.split("/") if p]
            if len(parcalar) >= 2:
                deger = "/".join(parcalar[-2:])
    except Exception:
        deger = None
    _slug_onbellek = (True, deger)
    return deger


def gh_argv(*args: str, yol: str | None = None) -> list[str] | None:
    """ÇİVİLİ `gh` argv'si. `gh` ikilisi yoksa None döner (çağıran OLCULEMEDI basar).

    Slug çözülürse `-R <slug>` eklenir; çözülemezse argv çivisiz döner ve
    çağıranın `cwd=REPO_KOK` ile koşması ZORUNLUDUR (bkz. `gh_kwargs`).
    """
    ikili = yol or gh_yolu()
    if ikili is None:
        return None
    s = slug()
    argv = [ikili, *args]
    if s and "-R" not in argv and "--repo" not in argv:
        argv += ["-R", s]
    return argv


def gh_kwargs(**ek) -> dict:
    """`subprocess.run` kwargs: her hâlükârda `cwd=REPO_KOK` (ikinci çivi)."""
    kw = {"capture_output": True, "text": True, "timeout": 20, "cwd": REPO_KOK}
    kw.update(ek)
    return kw


if __name__ == "__main__":
    print("REPO_KOK=%s" % REPO_KOK)
    print("GH_YOL=%s" % (gh_yolu() or "OLCULEMEDI"))
    print("SLUG=%s" % (slug() or "OLCULEMEDI"))
    print("ARGV=%s" % (gh_argv("run", "list", "--limit", "1") or "OLCULEMEDI"))
