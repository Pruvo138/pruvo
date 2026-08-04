#!/usr/bin/env python3
"""urunler-guard-hook.py — Claude Code PreToolUse(Bash) hook koprusudur.

stdin'den hook JSON'unu okur, tool_input.command icinde bir `git commit` ya da
`git push` var mi bakar; varsa urunler-guard.py'yi ilgili --tetik ile calistirir.
`--no-verify` bunu ATLATAMAZ, cunku bu harness hook'u git'in kendi hook'u DEGILDIR.

🔴 FAIL-LOUD KOPRUSU (4 Agu 2026): eskiden bu kopru guard'in CIKIS KODUNU ve
CIKTISINI YUTUYOR, daima 0 donuyordu. Guard sessizce veri mutasyonu yaptiginda
(merge getirisini bayat hale geri sardiginda) hicbir kapi calmadi. Artik:
  * guard 0 disi donerse -> kopru 2 doner (PreToolUse'da 2 = tool cagrisini BLOKLA)
    ve guard'in gerekcesini stderr'e AYNEN aktarir. `git commit` KOSMAZ.
  * guard cokerse/zaman asimina ugrarsa -> koruma KOSMAMISTIR, yine BLOKLANIR.
  * PRUVO_GUARD_ZORLA=1 -> blok GURULTULU UYARIYA duser (guard'in kendi kacis
    bayragiyla ayni ad; guard yine de hicbir veriyi degistirmez).

🔴 NEDEN BU DOSYA (IZLENEN) ONEMLI: `.claude/settings.json` ve `.git/hooks/`
gitignore'dadir (bu makineye ozel). `tools/` altindaki bu kopru IZLENIR ->
buradaki fail-loud davranisi TUM oturumlara ulasir. `.git/hooks/pre-commit`
tarafindaki ayni duzeltme YALNIZ bu makinede gecerlidir.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD = os.path.join(ROOT, "tools", "urunler-guard.py")
ZORLA_ENV = "PRUVO_GUARD_ZORLA"
BLOKLA = 2   # PreToolUse sozlesmesi: 2 = tool cagrisini engelle, stderr'i modele ver

# Bir kabuk segmentinde `git ... commit|push` tespiti (araya -C yol / bayrak girebilir).
_GIT_SUB = re.compile(r"\bgit\b[^\n]*?\b(commit|push)\b")


def _tetik(command):
    """Komut string'i commit mi push mu tetikliyor? Yoksa None."""
    tetik = None
    for seg in re.split(r"&&|\|\||;|\||\n", command):
        m = _GIT_SUB.search(seg)
        if not m:
            continue
        sub = m.group(1)
        if sub == "commit":
            return "commit"  # commit oncelikli
        if sub == "push":
            tetik = "push"
    return tetik


def _yaz(metin):
    if not metin:
        return
    try:
        sys.stderr.write(metin if metin.endswith("\n") else metin + "\n")
    except Exception:
        pass


def _blokla(basi, ayrinti):
    """Guard KOSMADI ya da REDDETTI -> git komutunu engelle (ya da zorla gecir)."""
    _yaz(basi)
    _yaz(ayrinti)
    if os.environ.get(ZORLA_ENV) == "1":
        _yaz("   %s=1 verildi -> blok UYARIYA cevrildi, komut DEVAM EDIYOR." % ZORLA_ENV)
        return 0
    _yaz("   Komut BLOKLANDI. Acil atlama (kayitli): %s=1" % ZORLA_ENV)
    return BLOKLA


def main():
    try:
        data = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    command = (data.get("tool_input") or {}).get("command") or ""
    tetik = _tetik(command)
    if not tetik:
        return 0
    if not os.path.exists(GUARD):
        return 0  # guard henuz bu agacta yoksa sessizce gec
    try:
        p = subprocess.run([sys.executable or "python3", GUARD, "--tetik", tetik],
                           capture_output=True, text=True, timeout=90)
    except Exception as e:
        return _blokla("!! urunler-guard KOSTURULAMADI (%r) — koruma calismadi." % (e,),
                       "   urunler.json korunmadan commit/push edilemez.")
    _yaz(p.stdout)
    if p.returncode != 0:
        return _blokla("!! urunler-guard REDDETTI (rc=%d) — %s bloklandi."
                       % (p.returncode, tetik), p.stderr)
    _yaz(p.stderr)   # geri sarma/uyari satirlari GORUNUR kalir (rc=0 olsa bile)
    return 0


if __name__ == "__main__":
    sys.exit(main())
