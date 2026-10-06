#!/usr/bin/env python3
"""FOTO KOSUCU KURULUM ARACI — launchd plist'i (2 dk aralik) URETIR; varsayilan --kuru yalniz basar.

  python3 tools/foto-kosucu-kur.py            # --kuru: plist'i ekrana basar, diske HICBIR sey yazmaz
  python3 tools/foto-kosucu-kur.py --kur      # YALNIZ MIMAR: plist'i yazar + launchctl bootstrap
  python3 tools/foto-kosucu-kur.py --kaldir   # launchctl bootout + plist + log dosyalari SILINIR

Kosucu `--uygula --log <log>` ile calisir; log tavani kosucuda (tek log <= 5 MB, asilinca eskisi
silinir — en cok iki dosya). launchd'nin kendi stdout/stderr'i /dev/null (sinirsiz buyuyen dosya YOK).
Hesap secimi: `--kur` aninda ortamdaki CLOUDFLARE_ACCOUNT_ID plist'e girer (repoya YAZILMAZ); yoksa --kur durur.
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


def plist_uret(hesap):
    py = shutil.which("python3") or sys.executable
    ortam = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONDONTWRITEBYTECODE": "1",
             "FOTO_KOSUCU_PYTHON": py}
    if hesap:
        ortam["CLOUDFLARE_ACCOUNT_ID"] = hesap
    return {
        "Label": ETIKET,
        "ProgramArguments": [py, os.path.join(KOK, "tools", "foto-uretec-kosucu.py"), "--uygula", "--log", LOG],
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
    a = ap.parse_args(argv)
    hedef = "gui/%d" % os.getuid()
    if a.kaldir:
        subprocess.run(["launchctl", "bootout", hedef + "/" + ETIKET], capture_output=True)
        silinen = [y for y in (PLIST, LOG, LOG + ".1") if os.path.exists(y)]
        for y in silinen:
            os.remove(y)
        print("KALDIRILDI silinen=%d" % len(silinen))
        return 0
    if a.kur:
        hesap = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
        if not hesap:
            print("DUR: CLOUDFLARE_ACCOUNT_ID ortamda yok (wrangler hesap secimi)", file=sys.stderr)
            return 2
        os.makedirs(os.path.dirname(PLIST), exist_ok=True)
        with open(PLIST, "wb") as f:
            plistlib.dump(plist_uret(hesap), f)
        subprocess.run(["launchctl", "bootout", hedef + "/" + ETIKET], capture_output=True)
        p = subprocess.run(["launchctl", "bootstrap", hedef, PLIST], capture_output=True, text=True)
        print("KURULDU rc=%d plist=%s log=%s" % (p.returncode, PLIST, LOG))
        return p.returncode
    sys.stdout.write(plistlib.dumps(plist_uret("<CLOUDFLARE_ACCOUNT_ID --kur aninda ortamdan>")).decode())
    print("KURU: diske yazim 0 (hedef %s)" % PLIST)
    return 0


if __name__ == "__main__":
    sys.exit(main())
