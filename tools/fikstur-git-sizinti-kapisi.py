#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sentetik git depolarini kanonik ortam yardimcisina zorlayan fail-closed kapi."""
import ast
import os
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
YARDIMCI = os.path.join(TOOLS, "git_ortami.py")


def _ad(n):
    if isinstance(n, ast.Name):
        return n.id
    if isinstance(n, ast.Attribute):
        return _ad(n.value) + "." + n.attr
    return ""


def sinifla(yol):
    try:
        kaynak = open(yol, encoding="utf-8").read()
        agac = ast.parse(kaynak, filename=yol)
    except (OSError, SyntaxError, UnicodeError) as exc:
        return "OLCULEMEDI", "kaynak ayrisamadi: %s" % exc
    # Muafiyet dosya adindan degil, kanonik yardimci taniminin kendisinden TURETILIR.
    tanimlar = {n.name for n in ast.walk(agac) if isinstance(n, (ast.FunctionDef,
                                                                 ast.AsyncFunctionDef))}
    if "sentetik_git" in tanimlar:
        govdeler = {n.name: ast.get_source_segment(kaynak, n) or ""
                    for n in ast.walk(agac) if isinstance(n, ast.FunctionDef)}
        git_ort = govdeler.get("git_ortami", "")
        sentetik = govdeler.get("sentetik_git", "")
        if ("os.environ.copy()" not in git_ort or ".pop(ad, None)" not in git_ort
                or ".pop(ad, None)" not in sentetik or "cwd=calisma_dizini" not in sentetik):
            return "OLCULEMEDI", "kanonik yardimcinin kopya/scrub/cwd garantisi eksik"
        return "MUAF", "kanonik yardimci tanimi"
    kurucu = []
    belirsiz = []
    kullaniyor = False
    for n in ast.walk(agac):
        if isinstance(n, (ast.Name, ast.Attribute)) and _ad(n).endswith("sentetik_git"):
            kullaniyor = True
        if not isinstance(n, ast.Call):
            continue
        sabitler = [x.value for x in ast.walk(n)
                    if isinstance(x, ast.Constant) and isinstance(x.value, str)]
        if "init" in sabitler or "clone" in sabitler:
            cagri = _ad(n.func)
            if cagri.endswith("sentetik_git"):
                kurucu.append((n.lineno, "kanonik"))
            elif cagri in ("subprocess.run", "subprocess.call", "subprocess.check_call",
                           "subprocess.check_output") and "git" in sabitler:
                kurucu.append((n.lineno, "dogrudan"))
            elif cagri.split(".")[-1] in ("g", "_git", "git", "kos", "_kos"):
                belirsiz.append(n.lineno)
    if not kurucu and not belirsiz:
        return "KAPSAM_DISI", "sentetik git depo kurucusu yok"
    if belirsiz and not kullaniyor:
        return "OLCULEMEDI", "dolayli git kurucusunun ortami kanitlanamadi: satir %s" % belirsiz[0]
    if any(tur == "dogrudan" for _satir, tur in kurucu) and not kullaniyor:
        return "SIZDIRIYOR", "dogrudan sentetik git kurucusu kanonik yardimcisiz"
    return "TEMIZ", "sentetik git yalniz kanonik yardimciyla cagriliyor"


def tara(tools=TOOLS):
    sonuc = []
    for ad in sorted(os.listdir(tools)):
        if ad.endswith(".py"):
            sonuc.append((ad, *sinifla(os.path.join(tools, ad))))
    return sonuc


def kendini_test():
    vakalar = {
        "sizdiran.py": ('import subprocess\nsubprocess.run(["git","init","x"])\n', "SIZDIRIYOR"),
        "temiz.py": ('from git_ortami import sentetik_git\nsentetik_git("x","init")\n', "TEMIZ"),
        "kapsam.py": ('print("git yok")\n', "KAPSAM_DISI"),
        "dolayli_temiz.py": ('import git_ortami as g\ndef kur():\n g.sentetik_git("x","init")\n', "TEMIZ"),
        "belirsiz.py": ('def g(*a): pass\ng("init")\n', "OLCULEMEDI"),
        "yardimci.py": ('import os\ndef git_ortami():\n o=os.environ.copy()\n'
                         ' for ad in ("GIT_DIR",): o.pop(ad, None)\n return o\n'
                         'def sentetik_git(calisma_dizini,*a):\n o=git_ortami()\n'
                         ' for ad in ("GIT_DIR",): o.pop(ad, None)\n'
                         ' return run(a, cwd=calisma_dizini)\n', "MUAF"),
    }
    iddia = 0
    with tempfile.TemporaryDirectory(prefix="pruvo-fikstur-kapi-") as d:
        for ad, (govde, beklenen) in vakalar.items():
            yol = os.path.join(d, ad)
            with open(yol, "w", encoding="utf-8") as f:
                f.write(govde)
            olculen, sebep = sinifla(yol)
            iddia += 1
            print("%s %s beklenen=%s olculen=%s (%s)" %
                  ("OK" if olculen == beklenen else "FAIL", ad, beklenen, olculen, sebep))
            if olculen != beklenen:
                return 1
    print("SONUC: YESIL — iddia %d" % iddia)
    return 0


def main():
    if "--kendini-test" in sys.argv[1:]:
        return kendini_test()
    kirmizi = 0
    for ad, durum, sebep in tara():
        if durum in ("SIZDIRIYOR", "OLCULEMEDI"):
            kirmizi += 1
            print("KIRMIZI %s: %s — %s" % (durum, ad, sebep))
    if kirmizi:
        print("SONUC: KIRMIZI — %d dosya" % kirmizi)
        return 1
    print("SONUC: YESIL — sentetik git fiksturleri kanonik")
    return 0


if __name__ == "__main__":
    sys.exit(main())
