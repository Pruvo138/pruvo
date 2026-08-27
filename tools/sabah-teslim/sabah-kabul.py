#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KraL SABAH RUTINI — KABUL BATARYASI (A1–A5).

27 Agu 2026, `KraL-SabahTeslim-27Agu`. `kral-sabah.py`nin daha once HIC kabul
bataryasi YOKTU — bu yuzden "yeni dosya acip tabani kacirma" yasagi burada
konusuz: kacirilacak taban DOSYASI yok, ve TABAN SAYILARI her kosumda BASILIR.

  A1  `--kendini-test` rc=0  VE  crontab'in KENDI yorumlayicisiyla kosum
      COKMUYOR — IKISI AYRI BASILIR.
  A2  Gercek kosum BUGUNUN spec'ini URETIYOR (dosya VAR, boyut > 0).
  A3  SONUC KOLU: "dosya uretilmedi" hali ADIYLA raporlanir (rc=0 iken bile).
      Fiksturde spec yazimi engellenince kol KIRMIZI yanar.
  A4  MUTANT: A3 kolu oldurulunce A3 FIKSTURU YESILE DONER (arac sessizce
      basarili gorunur); KONTROL (normal kosum) DEGISMEZ. Hedef-kol atfi ayrica.
  A5  Iki ardisik kosumda A1·A2 BIREBIR ayni.

Fazlar:
  --faz on   : yalniz A1 (yazim YAPMAZ — canli spec'e dokunmaz)
  --faz tam  : A1..A5 (A2 canli spec'i URETIR)
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

CRON = os.path.join(os.path.expanduser("~"), ".claude", "cron")
VARSAYILAN_ARAC = os.path.join(CRON, "kral-sabah.py")
SPEC_DIZINI = os.path.join(CRON, "tamirci-spec")
PY = sys.executable or "python3"

# 🔴 OLCULEN ARAC BAYRAKLA SECILIR (27 Agu 2026, mimar hukmu —
# KraL-KarantinaHukmu-27Agu). ONCE: `ARAC` KURULU KOPYAYA cakiliydi; batarya
# yesil yansa da o yesil DALIN dosyasini degil kurulu kopyayi tarif ediyordu
# — ve o duzleme baska cipler de yazabiliyor. SIMDI `--arac <yol>` hedefi
# degistirir; A4 MUTANTI da o dosyadan turer. Bayraksiz davranis AYNEN eski.
ARAC = VARSAYILAN_ARAC

SONUC = []


def kayit(ad, gecti, ayrinti=""):
    SONUC.append((ad, gecti, ayrinti))
    bayrak = "GECTI" if gecti is True else ("DUSTU" if gecti is False else "OLCULEMEDI")
    print("  [%s] %-42s %s" % (bayrak, ad, ayrinti))
    return gecti


def baslik(m):
    print("\n=== %s ===" % m)


def kos(argv, zaman_asimi=180):
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=zaman_asimi)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "ZAMAN_ASIMI %ds" % zaman_asimi
    except Exception as hata:
        return 125, "%s: %s" % (type(hata).__name__, hata)


def jeton(cikti, onek):
    """Ciktidan `<onek>...` ile baslayan SON satiri dondurur."""
    bulunan = "-"
    for satir in (cikti or "").splitlines():
        if satir.startswith(onek):
            bulunan = satir.strip()
    return bulunan


def bugunun_spec_yolu():
    return os.path.join(SPEC_DIZINI, "KraL-Tamirci-%s.md" % time.strftime("%Y%m%d"))


# --------------------------------------------------------------------- A1

def a1_ortam():
    baslik("A1 — ORTAM: kendini-test + crontab'in KENDI yorumlayicisi (AYRI basilir)")

    rc, cikti = kos([PY, ARAC, "--kendini-test"], 240)
    ortam = jeton(cikti, "ORTAM ")
    capraz = jeton(cikti, "KENDINI_TEST: CAPRAZ_ORTAM=")
    kayit("A1a --kendini-test rc=0", rc == 0,
          "rc=%d | %s | %s" % (rc, ortam, capraz))
    for satir in (cikti or "").splitlines():
        if satir.startswith("CAPRAZ_ORTAM"):
            print("      %s" % satir.strip())

    # A1b — CRONTAB'IN yorumlayicisi. 🔴 Yol ELLE yazilmaz: aracin KENDI
    # `crontab_yorumlayicilari()` fonksiyonundan okunur (tek kaynak).
    yorumlayicilar, sebep = crontab_yorumlayicilari_oku()
    if not yorumlayicilar:
        kayit("A1b crontab yorumlayicisiyla kosum", None,
              "OLCULEMEDI sebep=%s" % sebep)
        return
    hepsi = True
    ayrintilar = []
    for py in yorumlayicilar:
        rc2, cikti2 = kos([py, ARAC, "--ortam-testi"], 120)
        son = jeton(cikti2, "ORTAM ")
        ayrintilar.append("%s rc=%d %s" % (py, rc2, son))
        if rc2 != 0:
            hepsi = False
            ayrintilar.append("  ham=%s" % (cikti2 or "").strip()[-200:])
    kayit("A1b crontab yorumlayicisi COKMUYOR", hepsi, " || ".join(ayrintilar))


def crontab_yorumlayicilari_oku():
    """Aracin kendi fonksiyonunu KULLANIR (ikiz tanim URETILMEZ)."""
    rc, cikti = kos([PY, "-c",
                     "import importlib.util,sys;"
                     "s=importlib.util.spec_from_file_location('ks',%r);"
                     "m=importlib.util.module_from_spec(s);"
                     "s.loader.exec_module(m);"
                     "y,se=m.crontab_yorumlayicilari();"
                     "print('YORUMLAYICILAR=' + ','.join(y));"
                     "print('SEBEP=' + (se or '-'))" % ARAC], 60)
    if rc != 0:
        return [], "arac yuklenemedi rc=%d %s" % (rc, (cikti or "").strip()[-120:])
    ham = jeton(cikti, "YORUMLAYICILAR=").split("=", 1)[-1]
    sebep = jeton(cikti, "SEBEP=").split("=", 1)[-1]
    return ([p for p in ham.split(",") if p], sebep)


# --------------------------------------------------------------------- A2

def a2_gercek_kosum():
    baslik("A2 — GERCEK KOSUM bugunun spec'ini URETIYOR")
    hedef = bugunun_spec_yolu()
    once_var = os.path.isfile(hedef)
    once_boyut = os.path.getsize(hedef) if once_var else -1
    print("  TABAN: dosya_var=%d boyut=%d yol=%s" % (int(once_var), once_boyut, hedef))

    rc, cikti = kos([PY, ARAC], 240)
    ozet = jeton(cikti, "SABAH_SPEC=")
    sonuc = jeton(cikti, "SONUC_KOLU=")
    var = os.path.isfile(hedef)
    boyut = os.path.getsize(hedef) if var else -1
    kayit("A2 bugunun spec'i VAR ve boyut>0",
          rc == 0 and var and boyut > 0 and sonuc.startswith("SONUC_KOLU=SPEC_VAR"),
          "rc=%d dosya_var=%d boyut=%d" % (rc, int(var), boyut))
    print("      %s" % ozet)
    print("      %s" % sonuc)
    return {"rc": rc, "ozet": ozet, "sonuc": sonuc, "boyut": boyut}


# --------------------------------------------------------------------- A3/A4

CAPA = "    if sonuc_kirmizi:\n        rc = max(rc, 1)\n"
YAMA = "    if False:  # MUTANT: SONUC KOLU rc'yi YUKSELTMEZ\n        rc = max(rc, 1)\n"


def _yazilamaz_dizin(td):
    """mkdir'in YAPISAL olarak basarisiz oldugu bir yol: ebeveyn bir DOSYA.

    Izin bitleriyle (`chmod 500`) degil YAPIYLA engelliyoruz — izin bitleri
    root/umask/FS'ye gore degisebilir, `NotADirectoryError` degismez."""
    blok = os.path.join(td, "blok")
    with open(blok, "w", encoding="utf-8") as f:
        f.write("bu bir DOSYA; altina dizin acilamaz\n")
    return os.path.join(blok, "spec-dizini")


def a3_a4_sonuc_kolu():
    baslik("A3/A4 — SONUC KOLU: 'spec uretilmedi' hali ADIYLA raporlanir + MUTANT")
    with tempfile.TemporaryDirectory(prefix="sabah-kabul-") as td:
        yazilamaz = _yazilamaz_dizin(td)

        # --- A3 TABAN: canli arac, yazilamaz spec dizini -> KIRMIZI
        rc3, cikti3 = kos([PY, ARAC, "--spec-dizin", yazilamaz], 240)
        satir3 = jeton(cikti3, "SONUC_KOLU=")
        kayit("A3 spec yazilamayinca kol KIRMIZI yanar",
              rc3 >= 1 and satir3.startswith("SONUC_KOLU=SPEC_URETILMEDI"),
              "rc=%d | %s" % (rc3, satir3[:150]))

        # --- A3-KONTROL: normal kosum (kuru) -> kol SESSIZ, rc temiz
        rcK, ciktiK = kos([PY, ARAC, "--kuru"], 240)
        satirK = jeton(ciktiK, "SONUC_KOLU=")
        kayit("A3-KONTROL kuru kosum rc temiz",
              rcK == 0 and satirK.startswith("SONUC_KOLU=KURU"),
              "rc=%d | %s" % (rcK, satirK[:110]))

        # --- A4 MUTANT
        with open(ARAC, encoding="utf-8") as f:
            kaynak = f.read()
        capa_adedi = kaynak.count(CAPA)
        if capa_adedi != 1:
            kayit("A4a MUTANT capasi TEK", False,
                  "capa_adedi=%d (1 bekleniyor) -> mutant KOSTURULAMADI" % capa_adedi)
            kayit("A4b MUTANT A3 fiksturu YESILE DONER", None, "capa yok")
            kayit("A4c MUTANT KONTROL DEGISMEDI", None, "capa yok")
            return
        kayit("A4a MUTANT capasi TEK", True, "capa_adedi=1")

        mutant = os.path.join(td, "kral-sabah-mutant.py")
        with open(mutant, "w", encoding="utf-8") as f:
            f.write(kaynak.replace(CAPA, YAMA))

        rcM, ciktiM = kos([PY, mutant, "--spec-dizin", yazilamaz], 240)
        satirM = jeton(ciktiM, "SONUC_KOLU=")
        # HEDEF-KOL ATFI: mutantta arac AYNI hatayi yasar (satir DEGISMEZ) ama
        # rc DUSER -> yani olen sey tam olarak "rc'yi yukselten kol"dur.
        kayit("A4b MUTANT A3 fiksturu YESILE DONER (hedef-kol atifli)",
              rc3 >= 1 and rcM == 0
              and satirM.startswith("SONUC_KOLU=SPEC_URETILMEDI"),
              "taban_rc=%d mutant_rc=%d | mutant satiri AYNEN duruyor=%d "
              "(sebep: rc yukseltme kolu)" % (
                  rc3, rcM, int(satirM.startswith("SONUC_KOLU=SPEC_URETILMEDI"))))

        rcMK, ciktiMK = kos([PY, mutant, "--kuru"], 240)
        kayit("A4c MUTANT KONTROL DEGISMEDI",
              rcMK == rcK == 0,
              "kontrol taban_rc=%d mutant_rc=%d" % (rcK, rcMK))


# --------------------------------------------------------------------- A5

def _kararli(cikti):
    """A5 kiyasi icin DETERMINIST satirlar (zaman damgasi tasiyan satir YOK)."""
    tutulan = []
    for satir in (cikti or "").splitlines():
        if satir.startswith(("ORTAM ", "SABAH_SPEC=", "SONUC_KOLU=",
                             "KENDINI_TEST:", "CAPRAZ_ORTAM")):
            tutulan.append(satir.strip())
    return tutulan


def a5_iki_tur():
    baslik("A5 — IKI ARDISIK KOSUMDA A1·A2 BIREBIR AYNI")
    rc1a, c1a = kos([PY, ARAC, "--kendini-test"], 240)
    rc2a, c2a = kos([PY, ARAC], 240)
    rc1b, c1b = kos([PY, ARAC, "--kendini-test"], 240)
    rc2b, c2b = kos([PY, ARAC], 240)

    a1_ayni = (rc1a == rc1b) and (_kararli(c1a) == _kararli(c1b))
    a2_ayni = (rc2a == rc2b) and (_kararli(c2a) == _kararli(c2b))
    kayit("A5a A1 iki turda BIREBIR", a1_ayni,
          "rc %d/%d satir %d/%d" % (rc1a, rc1b, len(_kararli(c1a)), len(_kararli(c1b))))
    kayit("A5b A2 iki turda BIREBIR", a2_ayni,
          "rc %d/%d | T1: %s | T2: %s" % (
              rc2a, rc2b, jeton(c2a, "SABAH_SPEC=")[:90], jeton(c2b, "SABAH_SPEC=")[:90]))
    if not (a1_ayni and a2_ayni):
        print("      T1 A1:\n        " + "\n        ".join(_kararli(c1a)))
        print("      T2 A1:\n        " + "\n        ".join(_kararli(c1b)))
        print("      T1 A2:\n        " + "\n        ".join(_kararli(c2a)))
        print("      T2 A2:\n        " + "\n        ".join(_kararli(c2b)))


def main(argv=None):
    global ARAC
    ap = argparse.ArgumentParser()
    ap.add_argument("--faz", choices=("on", "tam"), default="tam")
    ap.add_argument("--arac", default=None, metavar="YOL",
                    help="olculecek kral-sabah.py (varsayilan: kurulu kopya "
                         "~/.claude/cron/kral-sabah.py). Dalin KENDI dosyasini "
                         "olcmek icin: --arac tools/sabah-teslim/kral-sabah.py")
    args = ap.parse_args(argv)
    if args.arac:
        ARAC = os.path.abspath(os.path.expanduser(args.arac))

    print("KraL SABAH RUTINI KABUL BATARYASI — faz=%s" % args.faz)
    print("damga=%s python=%s" % (
        time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), PY))
    # 🔴 OLCULEN YUZEY ADIYLA BASILIR: iki kosumun farki bu satirdan okunur.
    print("OLCULEN_ARAC=%s (%s)" % (
        ARAC, "BAYRAKLA" if args.arac else "VARSAYILAN/kurulu"))
    print("SPEC_DIZINI=%s" % SPEC_DIZINI)

    if not os.path.isfile(ARAC):
        print("HATA: arac YOK -> %s" % ARAC)
        return 2

    a1_ortam()
    if args.faz == "tam":
        a2_gercek_kosum()
        a3_a4_sonuc_kolu()
        a5_iki_tur()

    baslik("OZET")
    gecen = sum(1 for _, g, _ in SONUC if g is True)
    dusen = [a for a, g, _ in SONUC if g is False]
    olculemeyen = [a for a, g, _ in SONUC if g is None]
    print("VAKA=%d GECTI=%d DUSTU=%d OLCULEMEDI=%d" % (
        len(SONUC), gecen, len(dusen), len(olculemeyen)))
    if dusen:
        print("DUSEN: %s" % ", ".join(dusen))
    if olculemeyen:
        print("OLCULEMEDI: %s" % ", ".join(olculemeyen))
    print("SABAH_KABUL rc=%d" % (1 if (dusen or olculemeyen) else 0))
    return 1 if (dusen or olculemeyen) else 0


if __name__ == "__main__":
    sys.exit(main())
