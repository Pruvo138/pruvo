#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ISCI ALT AJAN KAPISI — isci.sh iscisini Agent/Task araci KAPALI baslatir (18 Eki 2026).

Hedef `~/.claude/cron/isci.sh` (repoda KOPYASI YOKTUR); yama repoda YASAR,
kurulu kopyaya UYGULANIR, olcum KURULU KOPYADAN yapilir.

OLCULEN VAKA (BaBa 18 Eki 01:2x (B), MaCiT oyuncak derin8 kosumu): m3 iscisi
engel gorunce isi `Agent` alt ajanina devretti. Spec cumlesi ("alt ajan YASAK")
yalniz ricadir; deterministik kol CLI bayragidir: isci.sh'in UC claude cagrisinin
bayrak dizisine (`CLAUDE_BAYRAKLAR`, `CLAUDE_BAYRAKLAR_2`, `KAPANIS_BAYRAKLAR`)
`--disallowedTools Agent,Task` eklenir. Bayrak `--permission-mode bypassPermissions`
cifinin HEMEN ARKASINA girer: arkasindan hep bir secenek (`--max-budget-usd` /
`--output-format`) gelir, degiskenli secenek sonraki argumani YUTMAZ. Talimat
promptuna ek cumle: alt ajan yok, engelde `SEBEP=` satiriyla dur.

Kullanim:
  isci-altajan-kapisi.py uygula <isci.sh>   -> yamalar (idempotent); hedef satir
                                              eksikse rc=3 OLCULEMEDI, dosyaya YAZMAZ
  isci-altajan-kapisi.py kontrol <isci.sh>  -> AJAN_KAPALI=<n>/3 PROMPT=<0|1>;
                                              rc 0 yalniz 3/3 ve PROMPT=1
Kabul: tools/isci-altajan-kapisi-test.py (nobet.yml serit-b).
"""
import os
import re
import sys
import tempfile

BAYRAK = "--disallowedTools Agent,Task"
DIZILER = ("CLAUDE_BAYRAKLAR", "CLAUDE_BAYRAKLAR_2", "KAPANIS_BAYRAKLAR")
CAPA = "--permission-mode bypassPermissions"
PROMPT_DEGISKENI = "ISCI_TALIMAT_PROMPTU"
PROMPT_EKI = (" ALT AJAN YOK: Agent/Task araci kapalidir, isi kimseye devretme;"
              " engel gorursen SEBEP=<tek cumle> satirini yazip dur.")


def _dizi_deseni(ad):
    return re.compile(r"^(\s*)" + re.escape(ad) + r"=\((.*)\)\s*$")


def _prompt_deseni():
    return re.compile(r'^(\s*)' + PROMPT_DEGISKENI + r'="(.*)"\s*$')


def olc(satirlar):
    """(kapali_sayisi, prompt_var, eksik_hedefler) dondurur."""
    kapali, eksik = 0, []
    for ad in DIZILER:
        desen = _dizi_deseni(ad)
        bulunan = [s for s in satirlar if desen.match(s)]
        if len(bulunan) != 1 or CAPA not in bulunan[0]:
            eksik.append(ad)
            continue
        if BAYRAK in bulunan[0]:
            kapali += 1
    pdesen = _prompt_deseni()
    promptlar = [s for s in satirlar if pdesen.match(s)]
    if len(promptlar) != 1:
        eksik.append(PROMPT_DEGISKENI)
    prompt_var = len(promptlar) == 1 and "ALT AJAN YOK" in promptlar[0]
    return kapali, prompt_var, eksik


def yamala(satirlar):
    yeni = []
    pdesen = _prompt_deseni()
    for s in satirlar:
        for ad in DIZILER:
            if _dizi_deseni(ad).match(s) and BAYRAK not in s:
                s = s.replace(CAPA, CAPA + " " + BAYRAK, 1)
        m = pdesen.match(s)
        if m and "ALT AJAN YOK" not in s:
            s = '%s%s="%s%s"\n' % (m.group(1), PROMPT_DEGISKENI, m.group(2), PROMPT_EKI)
        yeni.append(s)
    return yeni


def main(argv):
    if len(argv) != 3 or argv[1] not in ("uygula", "kontrol"):
        print("kullanim: isci-altajan-kapisi.py uygula|kontrol <isci.sh>", file=sys.stderr)
        return 2
    yol = argv[2]
    try:
        with open(yol, encoding="utf-8") as f:
            satirlar = f.readlines()
    except OSError as e:
        print("OLCULEMEDI sebep=okunamadi:%s" % e.__class__.__name__)
        return 3
    _, _, eksik = olc(satirlar)
    if eksik:
        print("OLCULEMEDI sebep=hedef-satir-yok:%s" % ",".join(eksik))
        return 3
    if argv[1] == "uygula":
        yeni = yamala(satirlar)
        degisti = yeni != satirlar
        if degisti:
            kip = os.stat(yol).st_mode & 0o7777
            fd, gecici = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(yol)))
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.writelines(yeni)
            os.chmod(gecici, kip)
            os.replace(gecici, yol)
            satirlar = yeni
        print("UYGULANDI degisti=%d" % int(degisti))
    kapali, prompt_var, _ = olc(satirlar)
    print("AJAN_KAPALI=%d/%d PROMPT=%d" % (kapali, len(DIZILER), int(prompt_var)))
    return 0 if kapali == len(DIZILER) and prompt_var else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
