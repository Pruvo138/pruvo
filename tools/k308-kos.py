#!/usr/bin/env python3
"""K308 tek-komutluk KOSUCU — kabul bataryasi + regresyonlar, HAM cikti dosyaya.

🔴 CIKTI YOLU GIT-DISINA CIVILI ([[K314]] / [[diskte-iz-birakma-yasagi]]): ic
kosum raporu IZLENEN agaca YAZILMAZ — yazilirsa `kisisel-veri-test.py` KURAL A
yayini durdurur. Varsayilan hedef `--cikti` ile verilir; verilmezse sistem gecici
dizini kullanilir ve yol EN SON satirda basilir.

Isci prozasina guvenilmez: her adimin rc'si ve ham ciktisi dosyaya doner, hukum
dosyadan `grep`/`cat` ile OKUNUR ([[ucuz-isci-yesil-tablo-uydurur]])."""
import os
import subprocess
import sys
import tempfile

BURASI = os.path.dirname(os.path.abspath(__file__))

ADIMLAR = [
    ("py_compile-yedekle", [sys.executable, "-m", "py_compile",
                            os.path.join(BURASI, "yedekle.py")]),
    ("py_compile-kabul", [sys.executable, "-m", "py_compile",
                          os.path.join(BURASI, "yedek-dusus-kabul.py")]),
    ("kanca-sozdizimi", ["sh", "-n", os.path.join(BURASI, "kancalar", "pre-push")]),
    ("K308-KABUL", [sys.executable, os.path.join(BURASI, "yedek-dusus-kabul.py")]),
    ("REGRESYON-yedek-koruma", [sys.executable,
                                os.path.join(BURASI, "yedek-koruma-test.py")]),
    ("REGRESYON-yedekle-test", [sys.executable,
                                os.path.join(BURASI, "yedekle-test.py")]),
]


def main():
    hedef = None
    argv = sys.argv[1:]
    if "--cikti" in argv:
        hedef = argv[argv.index("--cikti") + 1]
    if not hedef:
        hedef = os.path.join(tempfile.gettempdir(), "k308-kosum.txt")
    if os.path.abspath(hedef).startswith(os.path.abspath(os.path.join(BURASI, ".."))):
        print("RED: cikti yolu REPO ICINDE (%s) — git-disi bir yol ver." % hedef)
        return 2

    satirlar = []
    ozet = []
    for ad, komut in ADIMLAR:
        p = subprocess.run(komut, capture_output=True, text=True)
        satirlar.append("===== %s   rc=%d =====" % (ad, p.returncode))
        satirlar.append(p.stdout)
        if p.stderr.strip():
            satirlar.append("--- stderr ---")
            satirlar.append(p.stderr)
        ozet.append("%s=%d" % (ad, p.returncode))
    ozet_satiri = "OZET " + " ".join(ozet)
    satirlar.append(ozet_satiri)
    with open(hedef, "w", encoding="utf-8") as f:
        f.write("\n".join(satirlar) + "\n")
    print(ozet_satiri)
    print("CIKTI=%s" % hedef)
    return 0


if __name__ == "__main__":
    sys.exit(main())
