#!/usr/bin/env python3
"""ISCI URUN KAPISI (13 Eki 2026, guvenlik-isci-urun-kapisi).

OLCULEN KUSUR: m3 iscisi `uretim-organizer-faz5b1` `BITIS rc=0 hal=SAGLIKLI`
yazdi ama HIC urun uretmedi (galeri dizini bos). isci.sh hukmu yalniz
motorun zarfindan (`isci-hal-cozucu.py`) okuyordu; isin URUNUNE bakmiyordu.

Kaynak: pruvo `tools/isci-urun-kapisi.py`; kurulu kopya
`~/.claude/cron/isci-urun-kapisi.py` (isci.sh cagirir). Kabul:
`tools/isci-urun-kapisi-test.py`.

Spec satir basinda `URUN_YOLU=<glob>` (birden cok olabilir; `~`, mutlak ya da
EV kokune gore goreli). Iki adim:

  basla --spec S --ev E
      -> `ZAMAN=<epoch>` `SAYI=<n|->`  (kosum BASINDA olcum)
  bitis --spec S --ev E --zaman T --baslangic-sayi N --hal H --rc R
      -> `HAL=<son hal>` `RC=<son rc>` `URUN=<n|->` `SATIR=<log satiri>`

Sayilan urun: glob eslesmesi (dizinse icindeki dosyalar), BOS OLMAYAN ve
mtime >= ZAMAN olan dosya. Eski cikti yeni kosumu YESIL yapmaz.

Hukum:
  * spec'te URUN_YOLU yok -> hal/rc AYNEN + `URUN_KAPISI=OLCULEMEDI-URUN`.
  * rc != 0 ya da hal motor/tavan hatasi -> motorun hukmu KORUNUR (BOS ezmez).
  * rc == 0, hal SAGLIKLI|OLCULEMEDI, urun 0 -> `HAL=BOS` + `RC=1`.
  * urun > 0 -> hal/rc AYNEN, `urun=<n>`.
"""
import glob
import os
import sys
import time

ANAHTAR = "URUN_YOLU="
# BOS yalniz motorun "basarili" (ya da hukumsuz) dedigi kosumu ezer.
EZILEBILIR_HALLER = {"SAGLIKLI", "OLCULEMEDI"}


def urun_yollari(spec):
    yollar = []
    with open(spec, encoding="utf-8", errors="replace") as f:
        for satir in f:
            if not satir.startswith(ANAHTAR):
                continue
            deger = satir[len(ANAHTAR):].strip().strip("`'\"").strip()
            if deger:
                yollar.append(deger)
    return yollar


def _mutlak(desen, ev):
    desen = os.path.expanduser(desen)
    if not os.path.isabs(desen):
        desen = os.path.join(ev, desen)
    return desen


def urun_say(yollar, ev, zaman):
    """Bos olmayan ve mtime >= zaman olan dosya sayisi (zaman None: hepsi)."""
    dosyalar = set()
    for desen in yollar:
        for yol in glob.glob(_mutlak(desen, ev), recursive=True):
            if os.path.isdir(yol):
                for kok, _, adlar in os.walk(yol):
                    for ad in adlar:
                        dosyalar.add(os.path.join(kok, ad))
            else:
                dosyalar.add(yol)
    n = 0
    for yol in dosyalar:
        try:
            st = os.stat(yol)
        except OSError:
            continue
        if st.st_size <= 0:
            continue
        if zaman is not None and st.st_mtime < zaman:
            continue
        n += 1
    return n


def _arg(argv, ad, varsayilan=None):
    if ad in argv:
        i = argv.index(ad)
        if i + 1 < len(argv):
            return argv[i + 1]
    return varsayilan


def basla(argv):
    spec, ev = _arg(argv, "--spec"), _arg(argv, "--ev", os.getcwd())
    zaman = time.time()
    yollar = urun_yollari(spec)
    sayi = urun_say(yollar, ev, None) if yollar else "-"
    print("ZAMAN=%.6f" % zaman)
    print("SAYI=%s" % sayi)
    return 0


def bitis(argv):
    spec, ev = _arg(argv, "--spec"), _arg(argv, "--ev", os.getcwd())
    zaman = float(_arg(argv, "--zaman"))
    bas_sayi = _arg(argv, "--baslangic-sayi", "-")
    hal = _arg(argv, "--hal", "OLCULEMEDI")
    rc = int(_arg(argv, "--rc"))
    yollar = urun_yollari(spec)
    if not yollar:
        print("HAL=%s" % hal)
        print("RC=%d" % rc)
        print("URUN=-")
        print("SATIR=URUN_KAPISI=OLCULEMEDI-URUN sebep=spec-urun-yolu-yok")
        return 0
    n = urun_say(yollar, ev, zaman)
    yol_alani = ",".join(y.replace(" ", "%20") for y in yollar)
    if n == 0 and rc == 0 and hal in EZILEBILIR_HALLER:
        print("HAL=BOS")
        print("RC=1")
        print("URUN=0")
        print("SATIR=URUN_KAPISI=BOS sebep=urun-yok onceki_hal=%s urun=0 "
              "urun_baslangic=%s urun_yolu=%s" % (hal, bas_sayi, yol_alani))
        return 0
    karar = "VAR" if n > 0 else "KORUNDU"
    print("HAL=%s" % hal)
    print("RC=%d" % rc)
    print("URUN=%d" % n)
    print("SATIR=URUN_KAPISI=%s urun=%d urun_baslangic=%s urun_yolu=%s"
          % (karar, n, bas_sayi, yol_alani))
    return 0


def main(argv):
    if len(argv) < 2 or argv[1] not in ("basla", "bitis"):
        print("Kullanim: isci-urun-kapisi.py basla|bitis --spec S --ev E ...",
              file=sys.stderr)
        return 2
    try:
        return basla(argv[2:]) if argv[1] == "basla" else bitis(argv[2:])
    except Exception as e:  # cagiran (isci.sh) rc!=0'i OLCULEMEDI-ARAC sayar
        print("URUN_KAPISI_HATA %s: %s" % (type(e).__name__, e), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv))
