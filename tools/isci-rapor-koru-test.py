#!/usr/bin/env python3
"""Kabul: isci.sh K337 KAPANIS RAPOR KORUMASI (20 Eki 2026, BaBa 08:1x (3)).

Olculen: tools/isci-rapor-koru.py (once/sonra/yama/kontrol). Kusur: kapanis LLM
cagrisi devraldigi dizindeki ortak isci raporunu EZDI (EyLuL 19 Eki 23:29:
355.997 B -> 18.930 B). Kabul: ekleme-disi yazim RED + .bak'tan geri + yazilan
icerik tarihli ayracla SONA (kayip 0); normal ekleme GECER.

FIKSTUR: tools/fikstur/isci-rapor-koru/isci-kapanis-kolu.zsh — kurulu isci.sh'in
kapanis cagrisi satirlari BIREBIR (KAYNAK satiri dosyada).

VAKALAR (HERMETIK: yalniz gecici dizin; gercek ev/cron yolu KULLANILMAZ)
  V1  normal ekleme                     -> rc=0 GECTI, icerik eski+ek, .bak kalmaz
  V2  kucultucu yazim (kucuk dosya)     -> rc=1 RED, dosya eski ile baslar, yazilan
                                           icerik SONDA, tek ayrac, .bak kalmaz
  V3  ortadan degistirip BUYUTEN yazim  -> rc=1 RED (boy karsilastirmasi YETMEZ)
  V4  dosya silindi                     -> rc=1 RED, dosya .bak ile BAYT-ESIT
  V5  once yoktu, sonra olustu / hic yok -> rc=0 hal=YENI / hal=YOK
  V6  coklu kok + tekillesme            -> ayni dizin (symlink) tek .bak; ezilen kok
                                           RED, ekleyen kok GECTI, rc=1
  V7  bayat .bak EZILMEZ                -> `.eski-*` kenarda, icerigi bayat ile esit
  V8  yama idempotent                   -> 1. degisti=1 + kontrol 2/2 ESIT rc=0;
                                           2. degisti=0 bayt-esit; once blogu cagridan
                                           ONCE, sonra blogu KAPANIS_RC=$? ARDINDA
  V9  capasiz isci.sh                   -> rc=3 OLCULEMEDI, bayt-esit, kopya YAZILMAZ
  V10 uctan uca: yamali fikstur, sahte motor PWD'deki raporu EZER -> geri alindi,
                                           cron raporu dokunulmadi, kapanis_rc=7 KORUNDU
  V11 uctan uca: sahte motor EKLER      -> GECTI, ayrac 0
  (V10/V11 zsh yoksa bash ile kosar; ikisi de yoksa ATLANDI)
MUTANTLAR (aracin gecici kopyasi; beklenen KIRMIZI)
  M1 onek yerine boy karsilastirmasi    -> V3 KIRMIZI
  M2 RED'de geri yazmaz                 -> V2 KIRMIZI
  M3 yazilan icerik SONA eklenmez (kayip) -> V2 KIRMIZI
  M4 capa yoksa da yazar (fail-open)    -> V9 KIRMIZI
  M5 sonra blogu her yamada yeniden girer -> V8 KIRMIZI
Cikti: `VAKA=<n>/<n> MUTANT_OLDU=<m>/5`; rc 0 yalniz hepsi yesil ise.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parent
ARAC = KOK / "isci-rapor-koru.py"
FIKSTUR = KOK / "fikstur" / "isci-rapor-koru" / "isci-kapanis-kolu.zsh"


def _arac_ad():
    spec = importlib.util.spec_from_file_location("isci_rapor_koru", ARAC)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul.AD


AD =_arac_ad()  # rapor dosya adi TEK KAYNAK: aracin AD sabiti
ESKI = ("## 2026-10-19 — eski rapor 1\n" + "satir\n" * 200
        + "## 2026-10-19 — eski rapor 2\nson satir\n").encode("utf-8")
AYRAC = "isci-rapor-koru: EKLEME-DISI YAZIM GERI ALINDI".encode("utf-8")
AYRINTI = {}


def kos(arac, *arg):
    p = subprocess.run([sys.executable, str(arac)] + [str(a) for a in arg],
                       capture_output=True, text=True)
    return p.returncode, p.stdout


def dizin(tmp, ad, rapor=ESKI):
    d = Path(tmp) / ad
    d.mkdir()
    if rapor is not None:
        (d / AD).write_bytes(rapor)
    return d


def baklar(d):
    return sorted(p.name for p in d.iterdir() if p.name.endswith(".bak"))


def tur(arac, d, yazim, kokler=None):
    """once -> yazim(dosya) -> sonra; (sonra rc, once+sonra cikti) dondurur."""
    kokler = kokler or [d]
    arg = []
    for k in kokler:
        arg += ["--kok", k]
    _, out1 = kos(arac, "once", *arg, "--kimlik", "t")
    yazim(d / AD)
    rc, out2 = kos(arac, "sonra", *arg, "--kimlik", "t")
    return rc, out1 + out2


def kabuk():
    # RAPOR_KORU_TEST_KABUK=bash: CI kosucusunu (zsh yok) yerelde taklit eder.
    z = None if os.environ.get("RAPOR_KORU_TEST_KABUK") == "bash" else shutil.which("zsh")
    if z:
        return [z, "-f"]
    b = shutil.which("bash")
    return [b, "--noprofile", "--norc"] if b else None


def uctan_uca(arac, tmp, ad, motor_govdesi):
    t = Path(tmp) / ad
    t.mkdir()
    cron, ev = dizin(t, "cron"), dizin(t, "ev")
    isci = cron / "isci.sh"
    shutil.copy(FIKSTUR, isci)
    rc, _ = kos(arac, "yama", isci)
    if rc != 0:
        return None
    motor = t / "sahte-motor.sh"
    motor.write_text("#!/bin/sh\n" + motor_govdesi + "\nexit 7\n", encoding="utf-8")
    motor.chmod(0o755)
    log = t / "isci.log"
    betik = t / "kos.sh"
    betik.write_text(
        "CLAUDE_ENV=()\nKAPANIS_HALI=TUR_TAVANI\nKAPANIS_BUTCE_USD=1\nOTURUM_ID=oturum\n"
        "KAPANIS_PROMPTU=durma-noktasi-yaz\nCLAUDE_BIN='%s'\nLOG='%s'\n"
        "CRON_KOKU='%s'\nEV_KOKU='%s'\nsource '%s'\n" % (motor, log, cron, ev, isci),
        encoding="utf-8")
    p = subprocess.run(kabuk() + [str(betik)], cwd=str(ev), capture_output=True, text=True)
    gunluk = log.read_text(encoding="utf-8") if log.exists() else ""
    AYRINTI[ad] = "rc=%d\n%s%s%s" % (p.returncode, p.stdout, p.stderr, gunluk)
    return p.returncode, ev, cron, gunluk


def vakalar(arac, tmp):
    s = {}
    # V1 normal ekleme
    d = dizin(tmp, "v1")
    rc, out = tur(arac, d, lambda f: f.open("ab").write(b"## yeni durma noktasi\n"))
    s["V1"] = (rc == 0 and "hal=GECTI" in out and (d / AD).read_bytes() == ESKI
               + b"## yeni durma noktasi\n" and baklar(d) == [])
    # V2 kucultucu yazim
    d = dizin(tmp, "v2")
    kucuk = "## DURMA NOKTASI — otel v3.2\nezen rapor\n".encode("utf-8")
    rc, out = tur(arac, d, lambda f: f.write_bytes(kucuk))
    son = (d / AD).read_bytes()
    s["V2"] = (rc == 1 and "hal=RED" in out and son.startswith(ESKI) and son.endswith(kucuk)
               and son.count(AYRAC) == 1 and baklar(d) == [])
    # V3 ortadan degistirip buyuten yazim
    d = dizin(tmp, "v3")
    buyuk = ESKI.replace(b"eski rapor 1", b"DEGISTI!!!!!") + b"x" * 500
    rc, out = tur(arac, d, lambda f: f.write_bytes(buyuk))
    son = (d / AD).read_bytes()
    s["V3"] = rc == 1 and "hal=RED" in out and son.startswith(ESKI) and son.endswith(buyuk)
    # V4 dosya silindi
    d = dizin(tmp, "v4")
    rc, out = tur(arac, d, lambda f: f.unlink())
    s["V4"] = (rc == 1 and "hal=RED" in out and (d / AD).read_bytes() == ESKI
               and baklar(d) == [])
    # V5 once yok -> sonra var / hic yok
    d, bos = dizin(tmp, "v5", rapor=None), dizin(tmp, "v5b", rapor=None)
    rc, out = tur(arac, d, lambda f: f.write_bytes(b"ilk rapor\n"), kokler=[d, bos])
    s["V5"] = (rc == 0 and "kok=%s hal=YENI" % os.path.realpath(d) in out
               and "kok=%s hal=YOK" % os.path.realpath(bos) in out
               and (d / AD).read_bytes() == b"ilk rapor\n")
    # V6 coklu kok + tekillesme
    a, c = dizin(tmp, "v6a"), dizin(tmp, "v6c")
    bag = Path(tmp) / "v6-bag"
    bag.symlink_to(a)
    kos(arac, "once", "--kok", a, "--kok", bag, "--kok", c, "--kimlik", "t")
    tek = baklar(a) == [AD + ".koru-t.bak"] and baklar(c) == [AD + ".koru-t.bak"]
    (a / AD).write_bytes(b"ezildi\n")
    (c / AD).open("ab").write(b"ek\n")
    rc, out = kos(arac, "sonra", "--kok", a, "--kok", bag, "--kok", c, "--kimlik", "t")
    s["V6"] = (tek and rc == 1 and out.count("hal=RED") == 1 and out.count("hal=GECTI") == 1
               and (a / AD).read_bytes().startswith(ESKI)
               and (c / AD).read_bytes() == ESKI + b"ek\n")
    # V7 bayat .bak ezilmez
    d = dizin(tmp, "v7")
    (d / (AD + ".koru-t.bak")).write_bytes(b"bayat yedek\n")
    rc, out = tur(arac, d, lambda f: f.open("ab").write(b"ek\n"))
    eskiler = [p for p in d.iterdir() if ".bak.eski-" in p.name]
    s["V7"] = (rc == 0 and "BAYAT_YEDEK_KENARA" in out and len(eskiler) == 1
               and eskiler[0].read_bytes() == b"bayat yedek\n")
    # V8 yama idempotent + konum
    d = Path(tmp) / "v8"
    d.mkdir()
    isci = d / "isci.sh"
    shutil.copy(FIKSTUR, isci)
    rc1, out1 = kos(arac, "yama", isci)
    rck, outk = kos(arac, "kontrol", isci)
    bir = isci.read_bytes()
    rc2, out2 = kos(arac, "yama", isci)
    satir = isci.read_text(encoding="utf-8").splitlines()
    i_once = [i for i, x in enumerate(satir) if " once " in x and "isci-rapor-koru.py" in x]
    i_cagri = [i for i, x in enumerate(satir) if '"$KAPANIS_PROMPTU"' in x]
    i_rc = [i for i, x in enumerate(satir) if x.strip() == "KAPANIS_RC=$?"]
    i_sonra = [i for i, x in enumerate(satir) if " sonra " in x and "isci-rapor-koru.py" in x]
    s["V8"] = (rc1 == 0 and "degisti=1" in out1 and rck == 0 and "KORU_KANCASI=2/2 KOPYA=ESIT"
               in outk and rc2 == 0 and "degisti=0" in out2 and isci.read_bytes() == bir
               and len(i_once) == len(i_cagri) == len(i_rc) == len(i_sonra) == 1
               and i_once[0] < i_cagri[0] < i_rc[0] < i_sonra[0]
               and i_sonra[0] == i_rc[0] + 2 and (d / "isci-rapor-koru.py").is_file())
    # V9 capasiz
    d = Path(tmp) / "v9"
    d.mkdir()
    isci = d / "isci.sh"
    isci.write_text("".join(x for x in FIKSTUR.read_text(encoding="utf-8").splitlines(True)
                            if "KAPANIS_RC=$?" not in x), encoding="utf-8")
    once = isci.read_bytes()
    rc, out = kos(arac, "yama", isci)
    s["V9"] = (rc == 3 and "OLCULEMEDI" in out and isci.read_bytes() == once
               and not (d / "isci-rapor-koru.py").exists())
    # V10/V11 uctan uca
    if kabuk():
        r = uctan_uca(arac, tmp, "v10", "printf 'EZEN RAPOR\\n' > %s" % AD)
        if r is None:
            s["V10"] = False
        else:
            rc, ev, cron, log = r
            son = (ev / AD).read_bytes()
            s["V10"] = (rc == 0 and son.startswith(ESKI) and son.endswith(b"EZEN RAPOR\n")
                        and son.count(AYRAC) == 1 and (cron / AD).read_bytes() == ESKI
                        and "kapanis_rc=7" in log and "RAPOR_KORU rc=1" in log
                        and baklar(ev) == [] and baklar(cron) == [])
        r = uctan_uca(arac, tmp, "v11", "printf 'EK\\n' >> %s" % AD)
        if r is None:
            s["V11"] = False
        else:
            rc, ev, cron, log = r
            s["V11"] = (rc == 0 and (ev / AD).read_bytes() == ESKI + b"EK\n"
                        and "RAPOR_KORU rc=0" in log and "kapanis_rc=7" in log)
    return s


MUTANTLAR = (
    ("M1", "        if yeni.startswith(eski):", "        if len(yeni) >= len(eski):", "V3"),
    ("M2", "            _atomik_yaz(dosya, geri, os.stat(bak).st_mode & 0o7777)\n",
     "            pass\n", "V2"),
    ("M3", "+ ayrac(len(eski), len(yeni), kok) + yeni", "+ ayrac(len(eski), len(yeni), kok)", "V2"),
    ("M4", "    if _capalar(satirlar) is None:\n        print(\"OLCULEMEDI sebep=capa",
     "    if False:\n        print(\"OLCULEMEDI sebep=capa", "V9"),
    ("M5", "    if not (r + 1 < len(yeni) and yeni[r + 1].strip().startswith(SONRA_BAS)):",
     "    if True:", "V8"),
)


def mutant(tmp, ad, eski, yeni):
    d = Path(tmp) / ("m-" + ad)
    d.mkdir()
    kopya = d / "isci-rapor-koru.py"
    kaynak = ARAC.read_text(encoding="utf-8")
    if eski not in kaynak:
        return None
    kopya.write_text(kaynak.replace(eski, yeni, 1), encoding="utf-8")
    return vakalar(kopya, d)


def main():
    with tempfile.TemporaryDirectory(prefix="isci-rapor-koru-") as tmp:
        d = Path(tmp) / "asil"
        d.mkdir()
        s = vakalar(ARAC, d)
        for ad in sorted(s, key=lambda x: int(x[1:])):
            print("%s %s" % (ad, "YESIL" if s[ad] else "KIRMIZI"))
            if not s[ad] and ad.lower() in AYRINTI:
                print("  " + AYRINTI[ad.lower()].replace("\n", "\n  ").rstrip())
        if "V10" not in s:
            print("V10/V11 ATLANDI (zsh/bash yok)")
        olen = 0
        for ad, eski, yeni, vaka in MUTANTLAR:
            m = mutant(tmp, ad, eski, yeni)
            oldu = m is not None and not m.get(vaka, True)
            olen += oldu
            print("%s %s (%s)" % (ad, "OLDU" if oldu else "YASADI", vaka))
    yesil = sum(s.values())
    print("VAKA=%d/%d MUTANT_OLDU=%d/%d" % (yesil, len(s), olen, len(MUTANTLAR)))
    return 0 if yesil == len(s) and olen == len(MUTANTLAR) else 1


if __name__ == "__main__":
    sys.exit(main())
