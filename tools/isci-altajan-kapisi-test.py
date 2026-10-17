#!/usr/bin/env python3
"""Kabul: isci.sh ALT AJAN KAPISI (18 Eki 2026, BaBa 01:2x (B)).

Olculen: tools/isci-altajan-kapisi.py (uygula/kontrol). Kusur: m3 iscisi engel
gorunce isi `Agent` alt ajanina devretti; spec cumlesi deterministik degil.

FIKSTUR: tools/fikstur/isci-altajan/isci-bayrak-satirlari.zsh — kurulu isci.sh'in
4 hedef satiri BIREBIR (KAYNAK satiri dosyada).

VAKALAR (HERMETIK: gecici dizin, gercek HOME/cron'a yazilmaz)
  V1 yamasiz fikstur kontrol            -> rc=1 AJAN_KAPALI=0/3 PROMPT=0
  V2 uygula                             -> rc=0 AJAN_KAPALI=3/3 PROMPT=1
  V3 ikinci uygula (idempotent)         -> degisti=0, bayt-esit, bayrak satir basina 1 kez
  V4 KAPANIS satiri yok                 -> rc=3 OLCULEMEDI, dosya bayt-esit (yazmaz)
  V5 arguman sirasi: `Agent,Task,Workflow`'tan sonraki ilk belirtec '-' ile baslar
     (degiskenli --disallowedTools sonraki argumani YUTMAZ), 3 dizide de
  V6 yamali satirlar zsh'ta dizi olarak acilir, `Agent,Task,Workflow` tek eleman
     (zsh yoksa -- CI kosucusu -- ATLANDI, hukmu ETKILEMEZ)
  V7 GOC: eski `Agent,Task` yamali satir -> yeni liste, bayrak satir basina 1 kez
MUTANTLAR (yardimcinin gecici kopyasi; beklenen KIRMIZI)
  M1 bayrak eklenmez (yamala kimlik)     -> V2 KIRMIZI
  M2 kontrol hep 3/3 sayar               -> V1 KIRMIZI
  M3 eksik hedefte de yazar (fail-open)  -> V4 KIRMIZI
  M4 goc kolu yok (ikinci bayrak eklenir) -> V7 KIRMIZI
YEREL (canli hat yoksa -- CI -- ATLANDI, hukmu ETKILEMEZ)
  (f) kurulu ~/.claude/cron/isci.sh kontrol -> AJAN_KAPALI=3/3 PROMPT=1 basilir
Cikti: `VAKA=<n>/<n> MUTANT_OLDU=4/4`; rc 0 yalniz hepsi yesil ise.
"""
import os
import pwd
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parent
YARDIMCI = KOK / "isci-altajan-kapisi.py"
FIKSTUR = KOK / "fikstur" / "isci-altajan" / "isci-bayrak-satirlari.zsh"
CANLI = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".claude" / "cron" / "isci.sh"
DIZILER = ("CLAUDE_BAYRAKLAR=", "CLAUDE_BAYRAKLAR_2=", "KAPANIS_BAYRAKLAR=")
LISTE = "Agent,Task,Workflow"


def kos(yardimci, kip, yol):
    p = subprocess.run([sys.executable, str(yardimci), kip, str(yol)],
                       capture_output=True, text=True)
    return p.returncode, p.stdout


def vakalar(yardimci, tmp):
    """{ad: bool} — yardimci verilen kopya olabilir (mutant)."""
    sonuc = {}
    hedef = Path(tmp) / "isci.sh"
    shutil.copy(FIKSTUR, hedef)
    rc, out = kos(yardimci, "kontrol", hedef)
    sonuc["V1"] = rc == 1 and "AJAN_KAPALI=0/3 PROMPT=0" in out
    rc, out = kos(yardimci, "uygula", hedef)
    sonuc["V2"] = rc == 0 and "AJAN_KAPALI=3/3 PROMPT=1" in out
    once = hedef.read_bytes()
    rc, out = kos(yardimci, "uygula", hedef)
    metin = hedef.read_text(encoding="utf-8")
    tekil = all(sum(s.count("--disallowedTools") for s in metin.splitlines()
                    if s.lstrip().startswith(d)) == 1 for d in DIZILER)
    sonuc["V3"] = rc == 0 and "degisti=0" in out and hedef.read_bytes() == once and tekil
    sira = []
    for s in metin.splitlines():
        if s.lstrip().startswith(DIZILER):
            b = s.split()
            i = b.index(LISTE) if LISTE in b else -1
            sira.append(i > 0 and b[i - 1] == "--disallowedTools" and i + 1 < len(b)
                        and b[i + 1].startswith(("-", "${BUTCE_BAYRAK[@]+")))
    sonuc["V5"] = len(sira) == 3 and all(sira)
    eksik = Path(tmp) / "eksik.sh"
    eksik.write_text("".join(s for s in FIKSTUR.read_text(encoding="utf-8").splitlines(True)
                             if "KAPANIS_BAYRAKLAR=" not in s), encoding="utf-8")
    once = eksik.read_bytes()
    rc, out = kos(yardimci, "uygula", eksik)
    sonuc["V4"] = rc == 3 and "OLCULEMEDI" in out and eksik.read_bytes() == once
    eski = Path(tmp) / "eski.sh"
    eski.write_text(FIKSTUR.read_text(encoding="utf-8").replace(
        "--permission-mode bypassPermissions",
        "--permission-mode bypassPermissions --disallowedTools Agent,Task"), encoding="utf-8")
    rc, out = kos(yardimci, "uygula", eski)
    sonuc["V7"] = rc == 0 and "AJAN_KAPALI=3/3" in out and all(
        s.count("--disallowedTools") == 1 and (" " + LISTE + " ") in s
        for s in eski.read_text(encoding="utf-8").splitlines()
        if s.lstrip().startswith(DIZILER))
    zsh = shutil.which("zsh")
    if zsh and sonuc["V2"]:
        dizi = "\n".join(s for s in metin.splitlines() if s.lstrip().startswith(DIZILER))
        iyi = True
        for butce in ("BUTCE_BAYRAK=()", "BUTCE_BAYRAK=(--max-budget-usd 5)"):
            betik = (butce + "; KAPANIS_BUTCE_USD=1; OTURUM_ID=x\n" + dizi
                     + "\nfor d in CLAUDE_BAYRAKLAR CLAUDE_BAYRAKLAR_2 KAPANIS_BAYRAKLAR; do "
                     "print -rl -- \"${(@P)d}\"; print -r -- '#SON'; done\n")
            p = subprocess.run([zsh, "-f", "-c", betik], capture_output=True, text=True)
            el = p.stdout.splitlines()
            idx = [i for i, e in enumerate(el) if e == LISTE]
            iyi = iyi and p.returncode == 0 and len(idx) == 3 and all(
                el[i - 1] == "--disallowedTools" and el[i + 1].startswith("-") for i in idx)
        sonuc["V6"] = iyi
    return sonuc


def mutant(tmp, ad, eski, yeni):
    kopya = Path(tmp) / ("mutant-%s.py" % ad)
    kaynak = YARDIMCI.read_text(encoding="utf-8")
    if eski not in kaynak:
        return None
    kopya.write_text(kaynak.replace(eski, yeni, 1), encoding="utf-8")
    d = Path(tmp) / ("m-" + ad)
    d.mkdir()
    return vakalar(kopya, d)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "asil"
        d.mkdir()
        s = vakalar(YARDIMCI, d)
        for ad in sorted(s):
            print("%s %s" % (ad, "YESIL" if s[ad] else "KIRMIZI"))
        if "V6" not in s:
            print("V6 ATLANDI (zsh yok)")
        olen = 0
        for ad, eski, yeni, vaka in (
            ("M1", "s = s.replace(CAPA, CAPA + \" \" + BAYRAK, 1)", "pass", "V2"),
            ("M2", "        if BAYRAK in bulunan[0]:\n            kapali += 1",
             "        kapali += 1", "V1"),
            ("M4", "if \"--disallowedTools \" in s:", "if False:", "V7"),
            ("M3", "    if eksik:\n        print(\"OLCULEMEDI",
             "    if eksik and argv[1] == 'kontrol':\n        print(\"OLCULEMEDI", "V4"),
        ):
            m = mutant(tmp, ad, eski, yeni)
            oldu = m is not None and not m[vaka]
            olen += oldu
            print("%s %s (%s)" % (ad, "OLDU" if oldu else "YASADI", vaka))
    if CANLI.is_file():
        rc, out = kos(YARDIMCI, "kontrol", CANLI)
        print("(f) CANLI %s" % (out.strip() or "rc=%d" % rc))
    else:
        print("(f) ATLANDI (canli isci.sh yok)")
    yesil = sum(s.values())
    print("VAKA=%d/%d MUTANT_OLDU=%d/4" % (yesil, len(s), olen))
    return 0 if yesil == len(s) and olen == 4 else 1


if __name__ == "__main__":
    sys.exit(main())
