#!/usr/bin/env python3
"""K340 KABUL FIKSTURU — 🔴 KONTROL (kabul ③c). ASLA KOSULMAZ.

MESRU repo-ICI betik-ici cagri. Kapi bu dosyayi SERBEST birakmalidir; birakmazsa
K340 kolu "her cagriya yanan alarm"a donusmus demektir ve is GECERSIZDIR.
Olculdu: ayni bicimdeki cagri tum tools/ agacinda 325 dosyada var.
"""
import subprocess


def asla_cagrilmaz():
    subprocess.run(["python3", "/Users/okan/dev/pruvo/tools/durum.py"],
                   capture_output=True, text=True)
