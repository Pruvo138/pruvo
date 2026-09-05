#!/usr/bin/env python3
"""ADI NOBETCISININ KABUL + MUTASYON TESTI.

Nobetci YESIL yaniyor diye ISE YARADIGI SANILMAZ. Bu test, nobetcinin
KIRMIZI YANABILDIGINI — ve DOGRU sebeple yandigini — olcer.

Her mutant IZOLE bir agac kopyasinda yasar; CANLI govde ASLA yamalanmaz
(FILO DERSI ①: test yuku gercek yikici komut olamaz, mutant izole kopyada).

Vakalar:
  V1 TABAN      : dokunulmamis agac  -> GECTI
  V2 YAYILMA    : izinsiz bir .py'ye ad eklenir -> KIRMIZI (IHLAL)
  V3 TAVAN      : izinli dosyada gecis sayisi artar -> KIRMIZI (TAVAN_ASIMI)
  V4 YASAK DUSER: argv0 esleme satiri SILINIR -> KIRMIZI (CAPA_DUSEN)
                  🔴 en kritik vaka: "temizlik" adi kaldirir ama YASAGI da
                  kaldirirsa nobetci bunu YAKALAMALI.
  V5 ANAHTAR    : yeni muafiyet anahtari kaybolursa -> KIRMIZI (CAPA_DUSEN)

Cikis 0 = gecti.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOBETCI = "tools/emekli-motor-adi-nobetcisi.py"


def _agac_kur(hedef):
    """tools/ + .claude/ py yuzeyinin IZOLE kopyasi."""
    os.makedirs(hedef, exist_ok=True)
    shutil.copytree(os.path.join(KOK, "tools"), os.path.join(hedef, "tools"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return hedef


def _kos(agac):
    p = subprocess.run([sys.executable, os.path.join(agac, NOBETCI)],
                       capture_output=True, text=True)
    son = ""
    for satir in (p.stdout or "").splitlines():
        if satir.startswith("ADI_NOBETI"):
            son = satir
    return son, (p.stdout or "") + (p.stderr or "")


def _alan(satir, ad):
    m = re.search(ad + r"=(\S+)", satir)
    return m.group(1) if m else None


VAKALAR = []


def vaka(no, aciklama, mutasyon, bek_hukum, bek_alan=None):
    VAKALAR.append((no, aciklama, mutasyon, bek_hukum, bek_alan))


vaka("V1", "TABAN: dokunulmamis agac", lambda a: None, "GECTI", None)


def _yayilma(agac):
    y = os.path.join(agac, "tools", "durum.py")
    if not os.path.exists(y):
        y = os.path.join(agac, "tools", "build.py")
    with open(y, "a", encoding="utf-8") as f:
        f.write("\n# yeni is codex'e yollanabilir\n")


vaka("V2", "YAYILMA: izinsiz .py'ye ad eklendi", _yayilma, "KIRMIZI", "IHLAL")


def _tavan(agac):
    y = os.path.join(agac, "tools", "mimar_kimlik.py")
    with open(y, "a", encoding="utf-8") as f:
        f.write("\n# codex\n# codex\n# codex\n")


vaka("V3", "TAVAN: izinli dosyada gecis sayisi artti", _tavan, "KIRMIZI", "TAVAN_ASIMI")


def _capa_sil(agac):
    y = os.path.join(agac, "tools", "mimar-icra-kapisi.py")
    s = open(y, encoding="utf-8").read()
    open(y, "w", encoding="utf-8").write(
        s.replace('os.path.basename(argv0) == "codex"',
                  'os.path.basename(argv0) == "EMEKLI"'))


vaka("V4", "YASAK DUSTU: argv0 esleme satiri ad'dan arindirildi",
     _capa_sil, "KIRMIZI", "CAPA_DUSEN")


def _anahtar_sil(agac):
    y = os.path.join(agac, "tools", "mimar-icra-kapisi.py")
    s = open(y, encoding="utf-8").read()
    open(y, "w", encoding="utf-8").write(s.replace("isci-muafiyet:", "her-sey-serbest:"))


vaka("V5", "ANAHTAR DUSTU: yeni muafiyet anahtari yok", _anahtar_sil,
     "KIRMIZI", "CAPA_DUSEN")

gecen = 0
gecici = tempfile.mkdtemp(prefix="adi-nobeti-test-")
try:
    for no, aciklama, mutasyon, bek_hukum, bek_alan in VAKALAR:
        agac = _agac_kur(os.path.join(gecici, no))
        mutasyon(agac)
        satir, ham = _kos(agac)
        if not satir:
            print("%-3s KIRMIZI  nobetci COKTU: %s" % (no, ham.strip()[-160:]))
            continue
        hukum = _alan(satir, "HUKUM")
        ok = (hukum == bek_hukum)
        if ok and bek_alan:
            ok = (_alan(satir, bek_alan) or "0") != "0"
        gecen += 1 if ok else 0
        print("%-3s %-8s beklenen=%-8s gorulen=%-8s %s%s"
              % (no, "GECTI" if ok else "KIRMIZI", bek_hukum, hukum, aciklama,
                 "" if ok else "  || " + satir))
finally:
    shutil.rmtree(gecici, ignore_errors=True)

print("GECEN=%d/%d" % (gecen, len(VAKALAR)))
sys.exit(0 if gecen == len(VAKALAR) else 1)
