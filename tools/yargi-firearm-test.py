#!/usr/bin/env python3
"""KABUL TESTI — parity-backfill yargi: keep-by-default + firearm blok.

Amaç:
  - gercek/ambiguous parçalar model false dese bile TUT
  - clear firearm aksesuarlar model true dese bile ELE
  - airsoft hobi replikasi TUT
  - merch ELENIR

Test, codex modelini sahte bir subprocess ile taklit eder ve parity-backfill.py'nin
post-process politikasını dogrudan dogrular.
"""
import importlib.util
import json
import os
import sys
from types import SimpleNamespace

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load():
    spec = importlib.util.spec_from_file_location("parity_backfill", os.path.join(_HERE, "parity-backfill.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fake_run_factory(results_by_id):
    def fake_run(cmd, capture_output=False, text=False, timeout=None):  # noqa: ARG001
        out_path = None
        for i, arg in enumerate(cmd):
            if arg == "-o" and i + 1 < len(cmd):
                out_path = cmd[i + 1]
                break
        if out_path:
            data = {"results": []}
            for pid, keep in results_by_id.items():
                data["results"].append({"id": pid, "keep": keep, "reason": "stub"})
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    return fake_run


def main():
    mod = _load()
    pairs = [
        ("1", "Toyota bracket"),
        ("2", "spacer"),
        ("3", "gear"),
        ("4", "mount"),
        ("5", "M-LOK rail"),
        ("6", "Magpul MOE grip"),
        ("7", "AR-15 magwell"),
        ("8", "picatinny mount"),
        ("9", "cheek riser"),
        ("10", "pistol brace"),
        ("11", "airsoft bb holder"),
        ("12", "keychain emblem"),
    ]
    expected_keep = {"1", "2", "3", "4", "11"}
    expected_block = {"5", "6", "7", "8", "9", "10", "12"}

    original_run = mod.subprocess.run
    mod.subprocess.run = _fake_run_factory({pid: False for pid, _ in pairs})
    try:
        keep, reason = mod.codex_yargi("Toyota", pairs)
    finally:
        mod.subprocess.run = original_run

    keep = set(keep or set())
    errors = []
    if keep != expected_keep:
        errors.append("keep=%s" % sorted(keep))
    if expected_block & keep:
        errors.append("blocked=%s" % sorted(expected_block & keep))

    print("keep:", " ".join(sorted(keep)))
    for pid, ad in pairs:
        print("  %-2s %-24s -> %s | %s" % (pid, ad, "TUT" if pid in keep else "AT", reason.get(pid, "")[:60]))

    if errors:
        print("BASARISIZ:", "; ".join(errors))
        sys.exit(1)

    print("12/12 GECTI — keep-by-default gerçek parça/airsoft'u tutar, firearm/merch'i ezer.")


if __name__ == "__main__":
    main()
