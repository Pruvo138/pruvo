#!/usr/bin/env python3
"""FOTO KOSUCU KURULUM ARACI — launchd plist'i (2 dk aralik) URETIR; varsayilan --kuru yalniz basar.

  python3 tools/foto-kosucu-kur.py            # --kuru: plist'i ekrana basar, diske HICBIR sey yazmaz
  python3 tools/foto-kosucu-kur.py --kur      # YALNIZ MIMAR: plist'i yazar + launchctl bootstrap
  python3 tools/foto-kosucu-kur.py --kaldir   # launchctl bootout + plist + log dosyalari SILINIR
  ... --hedef onizleme                        # ONIZLEME D1 kosucusu: ayri etiket/plist/log, kosucuya --hedef onizleme

Kosucu `--uygula --log <log>` ile calisir; log tavani kosucuda (tek log <= 5 MB, asilinca eskisi
silinir — en cok iki dosya). launchd'nin kendi stdout/stderr'i /dev/null (sinirsiz buyuyen dosya YOK).
Hesap secimi: `--kur` aninda ortamdaki CLOUDFLARE_ACCOUNT_ID plist'e girer (repoya YAZILMAZ); yoksa --kur durur.
HEDEF (10 Eki 2026): varsayilan canli = bugunku plist BAYT-ESIT; `--kur`/`--kaldir` hedef basina (biri digerine dokunmaz).
"""
import argparse
import os
import plistlib
import shutil
import subprocess
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ETIKET = "com.pruvo.foto-kosucu"
ARALIK_SN = 120
PLIST = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % ETIKET)
LOG = os.path.expanduser("~/Library/Logs/pruvo-foto-kosucu.log")


def hedef_yollari(hedef):
    """(etiket, plist, log) — canli: bugunku sabitler AYNEN; onizleme: `-onizleme` ekli ayri set."""
    if hedef == "canli":
        return ETIKET, PLIST, LOG
    etiket = ETIKET + "-" + hedef
    return (etiket, os.path.expanduser("~/Library/LaunchAgents/%s.plist" % etiket),
            os.path.expanduser("~/Library/Logs/pruvo-foto-kosucu-%s.log" % hedef))


def plist_uret(hesap, hedef="canli"):
    etiket, _, log = hedef_yollari(hedef)
    py = shutil.which("python3") or sys.executable
    ortam = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONDONTWRITEBYTECODE": "1",
             "FOTO_KOSUCU_PYTHON": py}
    if hesap:
        ortam["CLOUDFLARE_ACCOUNT_ID"] = hesap
    arg = [py, os.path.join(KOK, "tools", "foto-uretec-kosucu.py"), "--uygula", "--log", log]
    if hedef != "canli":
        arg += ["--hedef", hedef]
    return {
        "Label": etiket,
        "ProgramArguments": arg,
        "StartInterval": ARALIK_SN,
        "RunAtLoad": True,
        "WorkingDirectory": KOK,
        "EnvironmentVariables": ortam,
        "StandardOutPath": "/dev/null",
        "StandardErrorPath": "/dev/null",
        "ProcessType": "Background",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--kuru", action="store_true", help="varsayilan: plist'i bas, yazma")
    g.add_argument("--kur", action="store_true", help="YALNIZ MIMAR: yaz + yukle")
    g.add_argument("--kaldir", action="store_true", help="bosalt + plist ve loglari sil")
    ap.add_argument("--hedef", choices=["canli", "onizleme"], default="canli",
                    help="kosucunun D1/R2 hedefi (onizleme: ayri etiket/plist/log; varsayilan canli)")
    a = ap.parse_args(argv)
    etiket, plist, log = hedef_yollari(a.hedef)
    hedef = "gui/%d" % os.getuid()
    if a.kaldir:
        subprocess.run(["launchctl", "bootout", hedef + "/" + etiket], capture_output=True)
        silinen = [y for y in (plist, log, log + ".1") if os.path.exists(y)]
        for y in silinen:
            os.remove(y)
        print("KALDIRILDI silinen=%d" % len(silinen))
        return 0
    if a.kur:
        hesap = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
        if not hesap:
            print("DUR: CLOUDFLARE_ACCOUNT_ID ortamda yok (wrangler hesap secimi)", file=sys.stderr)
            return 2
        os.makedirs(os.path.dirname(plist), exist_ok=True)
        with open(plist, "wb") as f:
            plistlib.dump(plist_uret(hesap, a.hedef), f)
        subprocess.run(["launchctl", "bootout", hedef + "/" + etiket], capture_output=True)
        p = subprocess.run(["launchctl", "bootstrap", hedef, plist], capture_output=True, text=True)
        print("KURULDU rc=%d plist=%s log=%s" % (p.returncode, plist, log))
        return p.returncode
    sys.stdout.write(plistlib.dumps(plist_uret("<CLOUDFLARE_ACCOUNT_ID --kur aninda ortamdan>", a.hedef)).decode())
    print("KURU: diske yazim 0 (hedef %s)" % plist)
    return 0


if __name__ == "__main__":
    sys.exit(main())
