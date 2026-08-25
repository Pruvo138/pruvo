#!/usr/bin/env python3
"""marka_kanon haritasini D1 uretim govdesinden uret — K228 tek kaynak.

Cikis stdout'a JSON olarak yazar; hata durumunda stderr + exit 1.
"""
import argparse
import json
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import importlib.util

spec = importlib.util.spec_from_file_location("d1_sync", os.path.join(TOOLS, "d1-sync.py"))
d1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--urunler", default=os.path.join(KOK, "urunler.json"))
    parser.add_argument("--kok", default=KOK)
    args = parser.parse_args()

    with open(args.urunler, encoding="utf-8") as f:
        urunler = json.load(f)

    harita, sebep = d1.marka_kanon_haritasi(urunler)
    if sebep:
        print("HATA: " + sebep, file=sys.stderr)
        sys.exit(1)

    print(json.dumps(harita, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
