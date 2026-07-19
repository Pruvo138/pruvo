#!/usr/bin/env python3
"""Regression gate with teeth.

Runs the release-blocking test set sequentially and stops at first failure.

Default suite:
  - python3 tools/yargi-firearm-test.py
  - python3 tools/lisans-havuz-test.py
  - python3 tools/derin-cap-test.py
  - node tools/parite-test.js
  - node tools/parite-ege.js

Use --demo-fail to inject a deliberate failure at the front of the queue and prove
that the gate blocks.
"""
import argparse
import os
import subprocess
import sys

ROOT = "/Users/okan/dev/pruvo"
PY = sys.executable or "python3"


def _cmds(demo_fail):
    cmds = []
    if demo_fail:
        cmds.append(("demo-fail", [PY, "-c", "import sys; sys.exit(17)"], None))
    cmds.extend([
        ("yargi-firearm", [PY, os.path.join(ROOT, "tools", "yargi-firearm-test.py")], "GECTI"),
        ("lisans-havuz", [PY, os.path.join(ROOT, "tools", "lisans-havuz-test.py")], "3/3 GECTI"),
        ("derin-cap", [PY, os.path.join(ROOT, "tools", "derin-cap-test.py")], "GECTI"),
        ("parite-test", ["node", os.path.join(ROOT, "tools", "parite-test.js")], "BIREBIR PARITE"),
        ("parite-ege", ["node", os.path.join(ROOT, "tools", "parite-ege.js")], None),
    ])
    return cmds


def _run(label, cmd, expect):
    print("==> %s" % label, flush=True)
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
    print(out, end="" if out.endswith("\n") else "\n", flush=True)
    if p.returncode != 0:
        print("BLOKE: %s exit=%d" % (label, p.returncode), file=sys.stderr, flush=True)
        return p.returncode
    if expect and expect not in out:
        print("BLOKE: %s beklenen desen yok: %s" % (label, expect), file=sys.stderr, flush=True)
        return 1
    print("OK: %s" % label, flush=True)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo-fail", action="store_true", help="inject a deliberate blocker")
    args = ap.parse_args()

    for label, cmd, expect in _cmds(args.demo_fail):
        rc = _run(label, cmd, expect)
        if rc != 0:
            return rc
    print("REGRESYON KAPISI YESIL: tum testler gecti.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
