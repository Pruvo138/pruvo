#!/usr/bin/env python3
"""K340 ON-OLCUM — betik-ici cagri ekseni (2) icin YANLIS-POZITIF yuzeyini olcer.

Iki tarama sekli kiyaslanir:
  KABA   : dosyada exec primitifi VAR ve dosyanin HERHANGI bir yerinde repo-disi
           mutlak yol literali VAR  -> tetikler
  SINIRLI: exec primitifinin ARGUMAN METNI (parantez eslemesiyle sinirlanmis)
           icinde repo-disi mutlak yol literali VAR -> tetikler

Cikti: her iki sekil icin tetiklenen dosya sayisi + SINIRLI'nin adlari.
Karar bu sayidan verilir; tahmin YOK.
"""
import os
import re
import sys

REPO = "/Users/okan/dev/pruvo"
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXEC_RE = re.compile(
    r"(subprocess\.(run|call|check_call|check_output|Popen)|os\.(system|popen|execv|execvp|spawnv)"
    r"|child_process\.(exec|execSync|spawn|spawnSync|execFile|execFileSync))\s*\(")

# Repo DISI mutlak yol literali: tirnak icinde '/' ile baslayan ya da '~/' ile baslayan
LITERAL_RE = re.compile(r"""['"](~?/[^'"\n]{2,})['"]""")


def repo_disi(p):
    p = os.path.expanduser(p)
    if not p.startswith("/"):
        return False
    p = os.path.normpath(p)
    return not (p == REPO or p.startswith(REPO + "/"))


def cagri_metni(kaynak, baslangic):
    """EXEC primitifinin acilis parantezinden kapanisina kadar olan metni dondur."""
    i = kaynak.index("(", baslangic)
    derinlik = 0
    n = len(kaynak)
    j = i
    while j < n and j - i < 4000:
        c = kaynak[j]
        if c == "(":
            derinlik += 1
        elif c == ")":
            derinlik -= 1
            if derinlik == 0:
                return kaynak[i:j + 1]
        j += 1
    return kaynak[i:i + 4000]


def olc(kok):
    kaba, sinirli, sinirli_adlar, sinirli_ornek = 0, 0, [], {}
    for dizin, _alt, dosyalar in os.walk(kok):
        if "/.git" in dizin:
            continue
        for d in dosyalar:
            if not d.endswith((".py", ".js")):
                continue
            yol = os.path.join(dizin, d)
            try:
                with open(yol, "r", encoding="utf-8", errors="replace") as f:
                    kaynak = f.read()
            except Exception:
                continue
            if not EXEC_RE.search(kaynak):
                continue
            # KABA
            dosya_disi = [m.group(1) for m in LITERAL_RE.finditer(kaynak)
                          if repo_disi(m.group(1))]
            if dosya_disi:
                kaba += 1
            # SINIRLI
            vurus = []
            for m in EXEC_RE.finditer(kaynak):
                metin = cagri_metni(kaynak, m.start())
                for lm in LITERAL_RE.finditer(metin):
                    if repo_disi(lm.group(1)):
                        vurus.append(lm.group(1))
            if vurus:
                sinirli += 1
                sinirli_adlar.append(os.path.relpath(yol, kok))
                sinirli_ornek[os.path.relpath(yol, kok)] = vurus[:3]
    return kaba, sinirli, sinirli_adlar, sinirli_ornek


def main():
    kok = sys.argv[1] if len(sys.argv) > 1 else KOK
    kaba, sinirli, adlar, ornek = olc(kok)
    print("KOK=" + kok)
    print("KABA (dosyada exec + herhangi yerde repo-disi literal) : " + str(kaba))
    print("SINIRLI (exec ARGUMAN METNINDE repo-disi literal)      : " + str(sinirli))
    print("--- SINIRLI tetikleyen dosyalar ---")
    for a in sorted(adlar):
        print("  " + a + "   ornek=" + repr(ornek[a]))


main()
