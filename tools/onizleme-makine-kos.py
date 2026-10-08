#!/usr/bin/env python3
"""ONIZLEME MAKINE ANAHTARI ile tek koşum — anahtar DISKE YAZILMAZ, EKRANA BASILMAZ (8 Eki 2026, KraL).

NEDEN: `foto-ornek-uc-uca.py` saglayici kolu onizlemede `X-Onizleme-Makine` ister (shop/src/yonet.js
makineAnahtariGecerli). Anahtarin degeri yalniz o oturumun belleginde yasardi; her halef scratchpad'e yazip
elle `secret put` ediyordu (dosya artigi + icra kapisi repo-disi yolu keser). Bu arac: anahtari bellekte
uretir -> onizleme surumune `versions secret put` (stdin) -> `foto-onizleme.py yukle` -> takma ad yayilimini
bekler -> verilen komutu env `ONIZLEME_MAKINE_ANAHTARI` ile kosar. Anahtar surec bitince kaybolur; sonraki
koşum yenisini basar (eskisi gecersizlesir — onizleme disinda kullanan yok).

Kullanim: python3 tools/onizleme-makine-kos.py [--yukleme-yok] [--bekle 75] -- python3 tools/foto-ornek-uc-uca.py --tur figur ...
Cikis: alt komutun rc'si; hazirlik hatasi rc 2 (`MAKINE_KOS HATA <adim>`).
"""
import argparse
import os
import secrets
import shlex
import subprocess
import sys
import time

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOP = os.path.join(KOK, "shop")
TOML = os.path.join(SHOP, "wrangler.onizleme.toml")
HESAP = "dbbe2a8620c3c3a57c586b8a98142fb9"  # tools/foto-onizleme.py ile ayni
AD = "ONIZLEME_MAKINE_ANAHTARI"


def wrangler():
    k = os.environ.get("ONIZLEME_KOS_WRANGLER", "")
    return shlex.split(k) if k else ["npx", "--prefix", SHOP, "wrangler"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--yukleme-yok", action="store_true", help="foto-onizleme.py yukle ADIMINI atla (kod ayni)")
    ap.add_argument("--bekle", type=int, default=75, help="takma ad yayilimi icin bekleme (sn)")
    ap.add_argument("komut", nargs=argparse.REMAINDER, help="-- <alt komut>")
    a = ap.parse_args(argv)
    komut = a.komut[1:] if a.komut[:1] == ["--"] else a.komut
    if not komut:
        print("MAKINE_KOS HATA komut-yok")
        return 2
    anahtar = secrets.token_hex(24)
    env = dict(os.environ, CLOUDFLARE_ACCOUNT_ID=HESAP)
    p = subprocess.run(wrangler() + ["versions", "secret", "put", AD, "-c", TOML], input=anahtar + "\n",
                       capture_output=True, text=True, cwd=SHOP, env=env, timeout=300)
    if p.returncode != 0:
        print("MAKINE_KOS HATA secret-put %s" % (p.stderr or p.stdout).strip()[-200:].replace(anahtar, "***"))
        return 2
    print("MAKINE_KOS secret-put rc=0")
    if not a.yukleme_yok:
        y = subprocess.run([sys.executable, os.path.join(KOK, "tools", "foto-onizleme.py"), "yukle"],
                           capture_output=True, text=True, cwd=KOK, timeout=900)
        print("MAKINE_KOS yukle rc=%d %s" % (y.returncode, ((y.stdout or "").strip().splitlines() or [""])[-1][:160]))
        if y.returncode != 0:
            return 2
    time.sleep(max(0, a.bekle))
    alt = subprocess.run(komut, env=dict(os.environ, **{AD: anahtar}), cwd=KOK)
    return alt.returncode


if __name__ == "__main__":
    sys.exit(main())
