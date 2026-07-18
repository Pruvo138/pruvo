#!/usr/bin/env python3
"""Sequential parity-backfill wrapper.

Batch-level mutex: `.parity-batch.lock`
Leaf writes are still protected by the existing `.urunler.lock` inside the adders.
This wrapper only guarantees that platform batches run one-by-one and that two
wrappers cannot overlap.

Kullanim:
  python3 tools/parity-sequential-flock.py --dry-run MakerWorld=Ford,Renault Printables=Bosch
  python3 tools/parity-sequential-flock.py MakerWorld=Ford,Renault Printables=Bosch
"""
import argparse
import fcntl
import os
import subprocess
import sys

ROOT = "/Users/okan/dev/pruvo"
TOOLS = os.path.join(ROOT, "tools")
LOCK = os.path.join(ROOT, ".parity-batch.lock")
PY = sys.executable or "python3"


def _parse_spec(raw):
    if "=" in raw:
        plat, rest = raw.split("=", 1)
    elif ":" in raw:
        plat, rest = raw.split(":", 1)
    else:
        raise ValueError("spec format: Platform=marka1,marka2")
    plat = plat.strip()
    brands = [x.strip() for x in rest.split(",") if x.strip()]
    if not plat or not brands:
        raise ValueError("spec format: Platform=marka1,marka2")
    return plat, brands


def _run(platform, brands, per_max, bekle, derin):
    cmd = [PY, os.path.join(TOOLS, "parity-backfill.py"), platform, ",".join(brands), str(per_max), str(bekle)]
    if derin:
        cmd.append("--derin")
    return subprocess.run(cmd, capture_output=False, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--derin", action="store_true")
    ap.add_argument("--per-max", type=int, default=50)
    ap.add_argument("--bekle", type=int, default=8)
    ap.add_argument("specs", nargs="+", help="Platform=marka1,marka2 ...")
    args = ap.parse_args()

    batches = [_parse_spec(s) for s in args.specs]
    with open(LOCK, "w") as lockf:
        fcntl.flock(lockf, fcntl.LOCK_EX)
        try:
            print("PARITY SEQUENTIAL+FLOCK | batch=%d | per_max=%d | bekle=%d | derin=%s"
                  % (len(batches), args.per_max, args.bekle, args.derin))
            for i, (platform, brands) in enumerate(batches, 1):
                print("%d/%d %s -> %s" % (i, len(batches), platform, ",".join(brands)))
                if args.dry_run:
                    continue
                r = _run(platform, brands, args.per_max, args.bekle, args.derin)
                if r.returncode != 0:
                    print("HATA: batch durdu (%s)." % platform, file=sys.stderr)
                    return r.returncode
            print("Bitti: platformlar sirayla isletildi; yazma leaf scriptlerde `.urunler.lock` altinda.")
            return 0
        finally:
            fcntl.flock(lockf, fcntl.LOCK_UN)


if __name__ == "__main__":
    sys.exit(main())
