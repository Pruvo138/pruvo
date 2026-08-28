#!/usr/bin/env python3
"""K340 KABUL FIKSTURU — SINIR S1 ('literali okunamayan argv'). ASLA KOSULMAZ.

Cagrilan yol bir DEGISKENDE; kapi bunu OKUYAMAZ. Beklenen davranis: RED URETMEZ,
ALLOW izinde `BETIK-ICI-OLCULEMEDI=<n>` diye ADIYLA basilir. Bu vaka sinirin
SESSIZ olmadigini olcer — "olcemedim" bir kalemdir, muafiyet degil
([[olculemedi-bypass-degil-menzil-daraltmasi]]).
Olculdu: tum tools/ agacinda 65 cagri yeri bu sinifta.
"""
import subprocess
import sys

HEDEF = "/Users/okan/dev/pruvo-hasat/tools/r2-upload.py"


def asla_cagrilmaz():
    subprocess.run([sys.executable, HEDEF], capture_output=True, text=True)
