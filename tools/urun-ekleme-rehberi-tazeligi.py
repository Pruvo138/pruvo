#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Urun ekleme rehberi tazeligi — kanonik urun kapilari rehberde aniliyor mu?

Kapi envanteri burada yeniden yazilmaz. Aday evreni, iki kanonik aracin kendi
kesfinden alinir; urun-ekleme ayrimi araclarin ilk belge paragrafindaki katalog,
urun verisi, gorsel, R2, D1, mukerrer, denetim, feed ve marka-sayaci eksenleriyle
yapilir. Pre-commit/pre-push zincirindeki kapilar da urun commit'inin zorunlu
yolunda olduklari icin araclarin izlenen kanca kaynaklarindan turetilir.

Cikis 0 = hukmu besleyen kume rehberde en az birer kez aniliyor.
Cikis 1 = eksik ad var. Cikis 2 = olcum kurulamadigi icin fail-closed.
"""
import importlib.util
import os
import re
import subprocess
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
REHBER = os.path.join(TOOLS, "URUN-EKLEME-REHBERI.md")

# Bu bir kapi listesi degil, B1'de istenen urun-ekleme AYIRMA OLCUTUDUR.
# Yalniz ilk belge paragrafi okunur: test govdesindeki tesadufi jetonlar kapsami
# sisiremez. Yeni bir kanonik arac bu eksenlerden birini beyan ederse ratchet'e
# kendiliginden girer.
URUN_EKSENI = re.compile(
    r"(?:urun(?:ler)?(?:\s+eklem|\s+veri|\.json)|katalog|gorsel|\br2\b|\bd1\b|"
    r"mukerrer|denetim|feed|marka.{0,20}saya[cç])", re.I | re.S)
KOMUT_RE = re.compile(r"python3\s+(?:\"?[^\s\"]*/)?(tools/[A-Za-z0-9_.-]+\.py)")
ATAMA_RE = re.compile(
    r'^[A-Za-z_][A-Za-z0-9_]*="[^"\n]*/(tools/[A-Za-z0-9_.-]+\.py)"', re.M)


def _yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    if spec is None or spec.loader is None:
        raise RuntimeError("modul tanimi kurulamadi: %s" % yol)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[ad] = modul
    spec.loader.exec_module(modul)
    return modul


def _ilk_belge(yol):
    with open(os.path.join(ROOT, yol), encoding="utf-8") as f:
        metin = f.read(6000)
    konumlar = [(metin.find('"""'), '"""'), (metin.find("'''"), "'''")]
    konumlar = [(i, tirnak) for i, tirnak in konumlar if i >= 0]
    if not konumlar:
        return metin[:2000]
    bas, tirnak = min(konumlar)
    son = metin.find(tirnak, bas + 3)
    belge = metin[bas + 3:son] if son >= 0 else metin[bas + 3:]
    return next((satir.strip() for satir in belge.splitlines() if satir.strip()), "")


def _izlenen_kanca_komutlari():
    p = subprocess.run(
        ["git", "-C", ROOT, "ls-files", "tools/kancalar/pre-commit"],
        capture_output=True, text=True, timeout=30)
    if p.returncode != 0:
        raise RuntimeError("kanca kesfi icin git ls-files rc=%d" % p.returncode)
    bulunan = set()
    for yol in p.stdout.splitlines():
        with open(os.path.join(ROOT, yol), encoding="utf-8") as f:
            icerik = f.read()
        etkin = "\n".join(satir for satir in icerik.splitlines()
                           if not satir.lstrip().startswith("#"))
        bulunan.update(KOMUT_RE.findall(etkin))
        # Gercek kanca betikleri yollarini kabuk degiskenine atar. Yalniz etkin
        # atama satirlarini al; yorumdaki ornek/olcum yollarini kapi sanma.
        bulunan.update(ATAMA_RE.findall(etkin))
    return bulunan


def kanonik_urun_kapilari():
    ci = _yukle(os.path.join(TOOLS, "ci-kapsam-test.py"), "_rehber_ci_kapsam")
    env = _yukle(os.path.join(TOOLS, "kapi-envanteri.py"), "_rehber_kapi_envanteri")

    ci_kumesi = set(ci.kesfet())
    env_kumesi = {g["script"] for g in env.GATES}
    env_kumesi.update(g["script"] for g in env.BILGI_KANCALARI)
    kanca = _izlenen_kanca_komutlari()
    adaylar = ci_kumesi | env_kumesi | kanca

    secilen = set()
    for yol in adaylar:
        if not os.path.isfile(os.path.join(ROOT, yol)):
            raise RuntimeError("kanonik arac dosyasi yok: %s" % yol)
        operasyonel = (yol in env_kumesi or yol in kanca or
                       os.path.basename(yol).endswith("-kapisi.py"))
        if operasyonel and (yol in kanca or URUN_EKSENI.search(_ilk_belge(yol))):
            secilen.add(yol)
    return sorted(secilen)


def main():
    try:
        kapilar = kanonik_urun_kapilari()
        with open(REHBER, encoding="utf-8") as f:
            rehber = f.read()
    except (OSError, RuntimeError, subprocess.SubprocessError) as e:
        print("URUN EKLEME REHBERI TAZELIGI: OLCULEMEDI (fail-closed)")
        print(str(e))
        return 2

    eksik = [yol for yol in kapilar if os.path.basename(yol) not in rehber]
    print("URUN EKLEME REHBERI TAZELIGI: kanonik=%d eksik=%d" %
          (len(kapilar), len(eksik)))
    if eksik:
        print("EKSIK KANONIK KAPILAR:")
        for yol in eksik:
            print("  " + yol)
        return 1
    print("SONUC: YESIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
