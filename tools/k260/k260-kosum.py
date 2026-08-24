#!/usr/bin/env python3
"""K260 KOSUM PAKETI — adimlari SIRAYLA kosar, ham ciktiyi ve GERCEK rc'yi yazar.

CHIP: KraL-K260KatSec.

NEDEN BETIK: isci "kostum" der ama ciktiyi uydurabilir
([[ucuz-isci-yesil-tablo-uydurur]] · [[isci-yesil-tablo-ic-olcumu-bosaltir]]).
Bu betik her adimi `subprocess` ile kosar, stdout+stderr'i AYNEN dosyaya yazar ve
rc'yi BORUSUZ olcer ([[boru-rc-isci-olcumunu-yalanlar]]). Isci yalniz bu betigi
kosturur; hukmu mimar HAM DOSYADAN okur.

KOSUM:
    python3 tools/k260/k260-kosum.py --cikti /tam/yol/dizin --faz taban
    python3 tools/k260/k260-kosum.py --cikti /tam/yol/dizin --faz kur
    python3 tools/k260/k260-kosum.py --cikti /tam/yol/dizin --faz kabul
    python3 tools/k260/k260-kosum.py --cikti /tam/yol/dizin --faz tur-kuru
    python3 tools/k260/k260-kosum.py --cikti /tam/yol/dizin --faz tur-canli
"""

import argparse
import os
import subprocess
import sys

CRON = "/Users/okan/.claude/cron"
BU_DIZIN = os.path.dirname(os.path.abspath(__file__))
KUR = os.path.join(BU_DIZIN, "k260-kur.py")
BATARYA = os.path.join(CRON, "nobet-kat-kovasi-test.py")
NOBET_KAPI = os.path.join(CRON, "nobet-kapi.py")

# Regresyon tabani (ONCE=SONRA). Taban kirmizisi K260'in kapsami DEGILDIR ama
# YAZILIR ([[olcut-civilenirken-taban-olculmeli]]).
REGRESYON = (
    ("regresyon-nobet-kabul", [sys.executable,
                               os.path.join(CRON, "nobet-kabul-test.py")]),
    ("regresyon-nobet-kapi-mutasyon",
     [sys.executable, os.path.join(CRON, "nobet-kapi-mutasyon.py")]),
    ("regresyon-sayac-durustluk",
     [sys.executable,
      "/Users/okan/dev/pruvo/tools/nobet-sayac-durustluk-test.py"]),
)

FAZLAR = {
    "taban": REGRESYON + (
        ("taban-kurulum-olcumu", [sys.executable, KUR]),
    ),
    "kur": (
        ("kurulum", [sys.executable, KUR, "--uygula"]),
    ),
    "kabul": (
        ("kabul-batarya", [sys.executable, BATARYA]),
        ("mutasyon", [sys.executable, BATARYA, "--mutasyon"]),
        ("canli-kova-olcumu", [sys.executable, BATARYA, "--canli"]),
    ) + tuple(("sonra-" + ad, komut) for ad, komut in REGRESYON),
    "tur-kuru": (
        ("tur-kuru", [sys.executable, NOBET_KAPI, "--tur-kapat", "--kuru"]),
    ),
    "tur-canli": (
        ("tur-canli", [sys.executable, NOBET_KAPI, "--tur-kapat"]),
    ),
}


def kos(ad, komut, dizin):
    yol = os.path.join(dizin, "%s.txt" % ad)
    try:
        p = subprocess.run(komut, capture_output=True, text=True, timeout=1500)
        govde = p.stdout + p.stderr
        rc = p.returncode
    except subprocess.TimeoutExpired:
        govde, rc = "ZAMAN_ASIMI 1500 sn\n", 124
    except OSError as hata:
        govde, rc = "KOSULAMADI: %s\n" % hata, 127
    with open(yol, "w", encoding="utf-8") as d:
        d.write("KOMUT=%s\n" % " ".join(komut))
        d.write(govde)
        d.write("\nGERCEK_RC=%d\n" % rc)
    print("ADIM=%-34s RC=%d DOSYA=%s" % (ad, rc, yol))
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser(description="K260 kosum paketi")
    ap.add_argument("--cikti", required=True)
    ap.add_argument("--faz", required=True, choices=sorted(FAZLAR))
    args = ap.parse_args(argv)
    os.makedirs(args.cikti, exist_ok=True)
    rcler = []
    for ad, komut in FAZLAR[args.faz]:
        rcler.append((ad, kos(ad, komut, args.cikti)))
    print("FAZ=%s ADIM=%d RC_SIFIR=%d"
          % (args.faz, len(rcler), sum(1 for _, r in rcler if r == 0)))
    for ad, r in rcler:
        print("OZET %s=%d" % (ad, r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
