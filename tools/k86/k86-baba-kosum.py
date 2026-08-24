#!/usr/bin/env python3
"""K86 BaBa eskalasyonu — CANLI turda KALICILASIYOR mu? ONCE/SONRA olcumu.

CHIP: KraL-K260KatSec (K86 eskalasyon kalicilastirma turu).

ARIZA/TABAN (olculdu, tekrar teshis EDILMEYECEK):
  Kuru tur su satiri basti:
    MERDIVEN kalem=K86 HAL=YETENEK YON=YUKARI SAYILIR=1 SAYAC=5
             BASAMAK=KRAL->BABA DURUM=ESKALASYON SEBEP=YETENEK
  AMA `nobet-geri-iz.json` icinde K86 hala `durum=DAGITILDI merdiven.basamak=KRAL`.
  Sebep: gecisi KURU tur uretti, kuru tur YAZMAZ (`if not kuru and yaz:`).

🔴 HUKUM LOG SATIRINDAN DEGIL GERI-IZ DOSYASINDAN OKUNUR
([[aracin-teshis-cumlesi-olcum-degil]]): `ESKALASYON=BABA` satirinin BASILMASI,
basamagin KALICILASTIGI anlamina GELMEZ.

KOSUM:
    python3 tools/k86/k86-baba-kosum.py --cikti /tam/yol/dizin
"""

import argparse
import json
import os
import subprocess
import sys

CRON = "/Users/okan/.claude/cron"
GERI_IZ = os.path.join(CRON, "nobet-geri-iz.json")
NOBET_KAPI = os.path.join(CRON, "nobet-kapi.py")
KALEM = "K86"

# Tur ciktisindan AYNEN tasinacak ozet satirlari (regresyon).
OZET_ONEKLERI = ("ACIK_KALEM=", "DAGITILAN=", "ONARIM=", "USTUSTE_ONARIMSIZ=",
                 "K260_KOVA", "HUKUM=", "MERDIVEN kalem=K86", "ESKALASYON=")


def _kayit():
    """K86'nin geri-iz kaydi. Okunamazsa None (fail-closed: hukum OLCULEMEDI)."""
    try:
        with open(GERI_IZ, encoding="utf-8") as d:
            return (json.load(d).get("kalemler") or {}).get(KALEM)
    except (OSError, ValueError) as hata:
        print("GERI_IZ=OKUNAMADI sebep=%s" % hata)
        return None


def _basamak(kayit):
    if kayit is None:
        return "OLCULEMEDI"
    return (kayit.get("merdiven") or {}).get("basamak") or "YOK"


def _durum(kayit):
    return "OLCULEMEDI" if kayit is None else (kayit.get("durum") or "YOK")


def main(argv=None):
    ap = argparse.ArgumentParser(description="K86 BaBa kalicilastirma olcumu")
    ap.add_argument("--cikti", required=True)
    args = ap.parse_args(argv)
    os.makedirs(args.cikti, exist_ok=True)

    # --- ONCE ---
    once = _kayit()
    taban = _basamak(once)
    print("ONCE kalem=%s basamak=%s durum=%s dagitim=%s"
          % (KALEM, taban, _durum(once),
             (once or {}).get("dagitim_sayisi", "-")))

    # --- CANLI TUR (--kuru DEGIL) ---
    yol = os.path.join(args.cikti, "tur-canli.txt")
    try:
        p = subprocess.run([sys.executable, NOBET_KAPI, "--tur-kapat"],
                           capture_output=True, text=True, timeout=1500)
        govde, rc = p.stdout + p.stderr, p.returncode
    except subprocess.TimeoutExpired:
        govde, rc = "ZAMAN_ASIMI 1500 sn\n", 124
    except OSError as hata:
        govde, rc = "KOSULAMADI: %s\n" % hata, 127
    with open(yol, "w", encoding="utf-8") as d:
        d.write(govde + "\nGERCEK_RC=%d\n" % rc)
    print("TUR_RC=%d DOSYA=%s" % (rc, yol))

    tur_no = "-"
    for satir in govde.splitlines():
        duz = satir.strip()
        if duz.startswith("=== ") and "tur=" in duz:
            for parca in duz.split():
                if parca.startswith("tur="):
                    tur_no = parca[len("tur="):]
        if any(duz.startswith(o) for o in OZET_ONEKLERI):
            print("TUR| %s" % duz[:200])

    # --- SONRA ---
    sonra_kayit = _kayit()
    sonra = _basamak(sonra_kayit)
    print("SONRA kalem=%s basamak=%s durum=%s dagitim=%s"
          % (KALEM, sonra, _durum(sonra_kayit),
             (sonra_kayit or {}).get("dagitim_sayisi", "-")))

    if sonra == "OLCULEMEDI" or taban == "OLCULEMEDI":
        hukum = "OLCULEMEDI"
        sebep = "geri-iz okunamadi"
    elif sonra == "BABA":
        hukum = "GECTI"
        sebep = "-"
    else:
        hukum = "DUSTU"
        sebep = "basamak BABA degil: %s (durum=%s)" % (sonra,
                                                      _durum(sonra_kayit))
    print("SEBEP=%s" % sebep)
    print("K86BABA= TABAN=%s SONRA=%s HUKUM=%s TUR=%s rc=%d"
          % (taban, sonra, hukum, tur_no, rc))
    return 0 if hukum == "GECTI" else 1


if __name__ == "__main__":
    sys.exit(main())
