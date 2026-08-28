#!/usr/bin/env python3
"""K340 ON-OLCUM v2 — betik-ici cagri ekseni (2) icin KESIN menzil olcumu.

v1 olctu: "exec arguman metninde HERHANGI repo-disi yol" -> 3 vurus, UCU DE ZARARSIZ
(URL parcasi '/api/shop/fiyat' · kapiya verilen SAHTE prob yolu '/tmp/spec-prob.md' ·
sistem ikilisi '/bin/zsh'). Demek ki menzil YANLIS secilmisti.

v2 KESIN MENZIL — Bash kapisinin KENDI A ve F kollarinin betik-ici karsiligi:
  A'  exec cagrisinin argv[0] LITERALI repo DISINA cozuluyor ve ICRA uzantisi tasiyor
  F'  argv[0] LITERALI bir YORUMLAYICI (python3/node/sh/bash/...) ve ondan sonraki ilk
      tiresiz LITERAL repo DISINA cozuluyor
Baska hicbir sey (arguman icindeki veri yollari, URL'ler, sistem ikilileri) TETIKLEMEZ.

Cikti: kac dosya tetikleniyor + adlari + hangi kol.
"""
import os
import re
import sys

REPO = "/Users/okan/dev/pruvo"
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXEC_RE = re.compile(
    r"(subprocess\.(run|call|check_call|check_output|Popen)|os\.(system|popen|execv|execvp|spawnv)"
    r"|child_process\.(exec|execSync|spawn|spawnSync|execFile|execFileSync))\s*\(")

ICRA_UZANTILARI = (".py", ".sh", ".js", ".mjs", ".cjs", ".rb", ".pl", ".php", ".bash", ".zsh")
YORUMLAYICI_RE = re.compile(r"^(python3?(\.\d+)?|node|sh|bash|zsh|ksh|dash|ruby|perl|php|osascript)$")

# Bir LISTE literalinin ilk ogeleri: ["a", "b", ...] / ['a', 'b', ...]
LISTE_RE = re.compile(r"\[\s*(.*?)\]", re.S)
STR_RE = re.compile(r"""^\s*['"]([^'"\n]*)['"]\s*$""")


def repo_disi(p):
    p = os.path.expanduser(p)
    if not p.startswith("/"):
        return False
    p = os.path.normpath(p)
    return not (p == REPO or p.startswith(REPO + "/"))


def cagri_metni(kaynak, baslangic):
    i = kaynak.index("(", baslangic)
    derinlik, n, j = 0, len(kaynak), i
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


def argv_literalleri(metin):
    """Cagri metnindeki ILK liste literalinin ogelerini dondur.
    Oge STRING literali degilse None konur (= 'okunamadi', OLCULEMEDI sinifi)."""
    m = LISTE_RE.search(metin)
    if not m:
        return None
    ogeler, derinlik, parca = [], 0, ""
    for c in m.group(1):
        if c in "([{":
            derinlik += 1
        elif c in ")]}":
            derinlik -= 1
        if c == "," and derinlik == 0:
            ogeler.append(parca)
            parca = ""
            continue
        parca += c
    if parca.strip():
        ogeler.append(parca)
    out = []
    for o in ogeler:
        sm = STR_RE.match(o)
        out.append(sm.group(1) if sm else None)
    return out


def hukum(argv):
    """(kol, vurus) ya da (None, None)."""
    if not argv or argv[0] is None:
        return None, None
    argv0 = argv[0]
    ad = os.path.basename(argv0)
    # A' — dogrudan repo-disi calistirilabilir
    if ("/" in argv0 or argv0.startswith(".")) and argv0.lower().endswith(ICRA_UZANTILARI):
        if repo_disi(argv0):
            return "A'", argv0
        return None, None
    # F' — yorumlayici + repo-disi betik
    if YORUMLAYICI_RE.match(ad):
        for t in argv[1:]:
            if t is None:
                return None, None          # okunamadi -> OLCULEMEDI, RED URETME
            if t.startswith("-"):
                continue
            if repo_disi(t):
                return "F'", t
            return None, None
    return None, None


def olc(kok):
    vurusanlar = {}
    okunamayan = 0
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
            for m in EXEC_RE.finditer(kaynak):
                metin = cagri_metni(kaynak, m.start())
                argv = argv_literalleri(metin)
                if argv is None:
                    okunamayan += 1
                    continue
                kol, vurus = hukum(argv)
                if kol:
                    vurusanlar.setdefault(os.path.relpath(yol, kok), []).append((kol, vurus))
    return vurusanlar, okunamayan


def main():
    kok = sys.argv[1] if len(sys.argv) > 1 else KOK
    vurusanlar, okunamayan = olc(kok)
    print("KOK=" + kok)
    print("KESIN MENZIL (A' + F') tetikleyen dosya : " + str(len(vurusanlar)))
    print("LITERAL OKUNAMAYAN cagri yeri (OLCULEMEDI sinifi, RED URETMEZ) : " + str(okunamayan))
    for a in sorted(vurusanlar):
        print("  " + a + "  " + repr(vurusanlar[a][:3]))


main()
