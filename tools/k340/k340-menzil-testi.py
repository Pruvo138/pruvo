#!/usr/bin/env python3
"""K340 MENZIL TESTI — betik-ici cagri kolunun (②) menzilini SUREKLI olcer.

🔴 NEDEN KALICI BIR TEST (tek seferlik olcum degil):
K340'in ② kolu, repo ICINDEKI bir betigin GOVDESINI okuyup icinde repo DISI bir
programi calistiran LITERAL cagri arar. Menzil 28 Agu'da OLCULEREK secildi:

    KABA   (dosyada exec primitifi + herhangi yerde repo-disi literal) : 125 dosya
    ORTA   (exec cagrisinin ARGUMAN METNINDE repo-disi yol)            :   3 dosya
           (ucu de ZARARSIZ: '/api/shop/fiyat' URL parcasi · '/tmp/spec-prob.md'
            kapiya verilen SAHTE prob yolu · '/bin/zsh' sistem ikilisi)
    KESIN  (A' + F' = CALISTIRILAN PROGRAMIN konumu)                   :   0 dosya

KESIN menzil secildi cunku mesru HICBIR araci yakmiyordu. Ama bu bir ANLIK sayidir:
yarin biri `tools/` altina repo-disi bir araci LITERAL olarak calistiran bir cagri
yazarsa, kapi o araci REDDETMEYE baslar ve bunu kimse fark etmez — hat sessizce durur.
Bu test o sayiyi CIVILER: KESIN menzil 0'dan buyukse rc=1 ve dosyalar ADIYLA basilir.

🔴 IKINCI KOPYA DEGIL: bu test kapinin yuklemini TAKLIT eder, ondan TURETMEZ
([[kabul-fiksturu-yasagi-kutsar]]). Kapinin kendi davranisi mimar-kilit-test.py
850-853 vakalariyla ve mimar-kapi-mutasyon-test.py M_K340_2 mutantiyla olculur;
burada olculen sey KAPI DEGIL, AGACIN kapiya sundugu YUZEYDIR.

Kullanim: python3 tools/k340/k340-menzil-testi.py [<taranacak-kok>]
rc=0 temiz · rc=1 KESIN menzilde dosya var (kapi onlari REDDEDECEK)
"""
import os
import re
import sys

REPO = "/Users/okan/dev/pruvo"
KOK_VARSAYILAN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXEC_RE = re.compile(
    r"(subprocess\.(run|call|check_call|check_output|Popen)"
    r"|os\.(system|popen|execv|execvp|execve|spawnv)"
    r"|child_process\.(exec|execSync|spawn|spawnSync|execFile|execFileSync))\s*\(")
LITERAL_RE = re.compile(r"""['"](~?/[^'"\n]{2,})['"]""")
STR_RE = re.compile(r"""^\s*['"]([^'"\n]*)['"]\s*$""")
ICRA_UZANTILARI = (".py", ".pyw", ".js", ".mjs", ".cjs", ".ts", ".tsx",
                   ".sh", ".bash", ".zsh", ".command", ".rb", ".pl")
YORUMLAYICI_RE = re.compile(
    r"^(python|python2|python3(\.\d+)?|pypy3?|node|nodejs|deno|bun|ts-node|tsx|"
    r"sh|bash|zsh|ksh|dash|ruby|perl|php|osascript)$")

# 🔴 FIKSTUR MUAFIYETI, ADIYLA: tools/k340/fikstur/ altindaki dosyalar KASITLI olarak
# repo-disi cagri TASIR — kapinin ② kolunun kabul vakalari onlar. Menzil sayimindan
# ADIYLA dislanir; baska hicbir dizin muaf DEGILDIR.
MUAF_DIZIN = os.path.join("k340", "fikstur")


def repo_disi(p):
    p = os.path.expanduser(p)
    if not p.startswith("/"):
        return False
    p = os.path.normpath(p)
    return not (p == REPO or p.startswith(REPO + "/"))


def cagri_metni(kaynak, baslangic):
    try:
        i = kaynak.index("(", baslangic)
    except ValueError:
        return ""
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
    m = re.search(r"\[(.*?)\]", metin, re.S)
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
    return [(STR_RE.match(o).group(1) if STR_RE.match(o) else None) for o in ogeler]


def kesin_hukum(argv):
    """(kol, vurus) ya da (None, None). Kapinin A ve F kollarinin betik-ici karsiligi."""
    if not argv or argv[0] is None:
        return None, None
    argv0 = argv[0]
    if ("/" in argv0 or argv0.startswith(".")) and argv0.lower().endswith(ICRA_UZANTILARI):
        return ("A'", argv0) if repo_disi(argv0) else (None, None)
    if YORUMLAYICI_RE.match(os.path.basename(argv0)):
        for t in argv[1:]:
            if t is None:
                return None, None
            if t.startswith("-"):
                continue
            return ("F'", t) if repo_disi(t) else (None, None)
    return None, None


def olc(kok):
    kaba, orta, kesin, olculemedi = 0, 0, {}, 0
    for dizin, _alt, dosyalar in os.walk(kok):
        if "/.git" in dizin:
            continue
        muaf = MUAF_DIZIN in dizin
        for d in dosyalar:
            if not d.endswith((".py", ".js", ".mjs", ".cjs")):
                continue
            yol = os.path.join(dizin, d)
            try:
                with open(yol, "r", encoding="utf-8", errors="replace") as f:
                    kaynak = f.read()
            except Exception:
                continue
            if not EXEC_RE.search(kaynak):
                continue
            if any(repo_disi(m.group(1)) for m in LITERAL_RE.finditer(kaynak)):
                kaba += 1
            orta_vurus = False
            for m in EXEC_RE.finditer(kaynak):
                metin = cagri_metni(kaynak, m.start())
                if any(repo_disi(lm.group(1)) for lm in LITERAL_RE.finditer(metin)):
                    orta_vurus = True
                argv = argv_literalleri(metin)
                if argv is None or argv[0] is None:
                    olculemedi += 1
                    continue
                kol, vurus = kesin_hukum(argv)
                if kol and not muaf:
                    kesin.setdefault(os.path.relpath(yol, kok), []).append((kol, vurus))
            if orta_vurus:
                orta += 1
    return kaba, orta, kesin, olculemedi


def main():
    kok = sys.argv[1] if len(sys.argv) > 1 else KOK_VARSAYILAN
    kaba, orta, kesin, olculemedi = olc(kok)
    print("K340 MENZIL TESTI · kok=" + kok)
    print("  KABA  (exec + herhangi yerde repo-disi literal) : " + str(kaba) + " dosya  [RAPOR]")
    print("  ORTA  (exec ARGUMAN METNINDE repo-disi yol)     : " + str(orta) + " dosya  [RAPOR]")
    print("  KESIN (A'+F' = calistirilan PROGRAMIN konumu)   : " + str(len(kesin)) + " dosya  [KAPI]")
    print("  OLCULEMEDI (literali okunamayan cagri yeri, S1) : " + str(olculemedi) + " cagri  [RAPOR]")
    print("  (fikstur muafiyeti ADIYLA: " + MUAF_DIZIN + ")")
    if kesin:
        print("🔴 KIRMIZI — kapi bu dosyalari REDDEDECEK:")
        for a in sorted(kesin):
            print("   " + a + "  " + repr(kesin[a][:3]))
        return 1
    print("SONUC: GECTI ✅ (kesin menzilde mesru arac YOK)")
    return 0


sys.exit(main())
