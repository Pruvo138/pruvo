#!/usr/bin/env python3
"""Yedek sifir/ani-dusus/surum davranisi ve iki oldurucu mutasyonun hermetik kabulu."""
import argparse
import glob
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile


sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.abspath(__file__))
KANONIK = os.path.join(TOOLS, "yedekle.py")


def sha(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(65536), b""):
            h.update(parca)
    return h.hexdigest()


def yaz_json(yol, sayi, dolgu=80):
    veri = {"k%03d" % n: {"olcu": n, "veri": "x" * dolgu} for n in range(sayi)}
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, sort_keys=True)


def modul_yukle(yol):
    ad = "yedekle_koruma_test_%d" % os.getpid()
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def reddedildi_mi(mod, kaynak, yedek):
    try:
        mod._drive_kopyala(kaynak, yedek)
    except mod.YedekKorumaHatasi:
        return True
    return False


def vaka_sifir(mod, kok):
    kaynak = os.path.join(kok, "sifir-kaynak.json")
    yedek = os.path.join(kok, "sifir-yedek.json")
    open(kaynak, "wb").close()
    yaz_json(yedek, 10)
    once = sha(yedek)
    red = reddedildi_mi(mod, kaynak, yedek)
    return red and sha(yedek) == once and os.path.getsize(kaynak) == 0


def vaka_ani(mod, kok):
    kaynak = os.path.join(kok, "ani-kaynak.json")
    yedek = os.path.join(kok, "ani-yedek.json")
    yaz_json(kaynak, 2)
    yaz_json(yedek, 10)
    once = sha(yedek)
    red = reddedildi_mi(mod, kaynak, yedek)
    return red and sha(yedek) == once


def vaka_normal(mod, kok):
    kaynak = os.path.join(kok, "normal-kaynak.json")
    yedek = os.path.join(kok, "normal-yedek.json")
    yaz_json(yedek, 10)
    eski = sha(yedek)
    yaz_json(kaynak, 11)
    yeni = sha(kaynak)
    mod._drive_kopyala(kaynak, yedek)
    ilk_surum = glob.glob(os.path.join(kok, "normal-yedek.[0-9]*.json"))
    if sha(yedek) != yeni or len(ilk_surum) != 1 or sha(ilk_surum[0]) != eski:
        return False
    for sayi in range(12, 36):
        yaz_json(kaynak, sayi)
        mod._drive_kopyala(kaynak, yedek)
    surumler = glob.glob(os.path.join(kok, "normal-yedek.[0-9]*.json"))
    return len(surumler) == mod.SURUM_SAKLA == 20


def tek_vaka(modul_yolu, vaka):
    mod = modul_yukle(modul_yolu)
    with tempfile.TemporaryDirectory(prefix="pruvo-yedek-koruma-") as kok:
        sonuc = {"sifir": vaka_sifir, "ani": vaka_ani, "normal": vaka_normal}[vaka](mod, kok)
    print("VAKA=%s RC=%d" % (vaka, 0 if sonuc else 1))
    return 0 if sonuc else 1


def mutant_yaz(kok, ad, eski, yeni):
    with open(KANONIK, "r", encoding="utf-8") as f:
        kaynak = f.read()
    if kaynak.count(eski) != 1:
        raise RuntimeError("mutasyon ankraji tekil degil: %s" % ad)
    yol = os.path.join(kok, ad + ".py")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(kaynak.replace(eski, yeni, 1))
    return yol


def tam_batarya():
    mod = modul_yukle(KANONIK)
    with tempfile.TemporaryDirectory(prefix="pruvo-yedek-koruma-") as kok:
        davranislar = [vaka_sifir(mod, kok), vaka_ani(mod, kok), vaka_normal(mod, kok)]
        mutant_sifir = mutant_yaz(
            kok, "mutant-sifir",
            "    _yedek_korumasi(kaynak, varis)\n    if os.path.isfile",
            "    pass  # MUTANT: koruma cagrisi olduruldu\n    if os.path.isfile")
        mutant_ani = mutant_yaz(
            kok, "mutant-ani",
            "return eski > 0 and yeni < eski * ANI_DUSUS_ESIGI",
            "return False")
        komut = [sys.executable, os.path.abspath(__file__), "--modul"]
        sifir = subprocess.run(komut + [mutant_sifir, "--vaka", "sifir"],
                               capture_output=True, text=True)
        ani = subprocess.run(komut + [mutant_ani, "--vaka", "ani"],
                             capture_output=True, text=True)
    mutantlar = [sifir.returncode != 0, ani.returncode != 0]
    print("KORUMA_TEST=%d" % sum(1 for sonuc in davranislar if sonuc))
    print("MUTASYON_KIRMIZI=%d" % sum(1 for sonuc in mutantlar if sonuc))
    print("MUTASYON_RC=%d,%d" % (sifir.returncode, ani.returncode))
    print("SURUM_TAVANI=%d" % mod.SURUM_SAKLA)
    return 0 if all(davranislar) and all(mutantlar) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modul")
    ap.add_argument("--vaka", choices=("sifir", "ani", "normal"))
    a = ap.parse_args()
    if a.modul or a.vaka:
        if not a.modul or not a.vaka:
            return 2
        return tek_vaka(a.modul, a.vaka)
    return tam_batarya()


if __name__ == "__main__":
    sys.exit(main())
