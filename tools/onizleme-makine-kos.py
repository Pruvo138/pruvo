#!/usr/bin/env python3
"""ONIZLEME MAKINE ANAHTARI ile tek koşum — anahtar DISKE YAZILMAZ, EKRANA BASILMAZ (8 Eki 2026, KraL).

NEDEN: `foto-ornek-uc-uca.py` saglayici kolu onizlemede `X-Onizleme-Makine` ister (shop/src/yonet.js
makineAnahtariGecerli). Anahtarin degeri yalniz o oturumun belleginde yasardi; her halef scratchpad'e yazip
elle `secret put` ediyordu (dosya artigi + icra kapisi repo-disi yolu keser). Bu arac: anahtari bellekte
uretir -> onizleme surumune `versions secret put` (stdin) -> `foto-onizleme.py yukle` -> takma ad yayilimini
bekler -> verilen komutu env `ONIZLEME_MAKINE_ANAHTARI` ile kosar. Anahtar surec bitince kaybolur; sonraki
koşum yenisini basar (eskisi gecersizlesir — onizleme disinda kullanan yok).

Kullanim: python3 tools/onizleme-makine-kos.py [--yukleme-yok] [--bekle 75] [--beklenen-sha <sha>] -- python3 tools/foto-ornek-uc-uca.py --tur figur ...
Cikis: alt komutun rc'si; hazirlik hatasi rc 2 (`MAKINE_KOS HATA <adim>`).

SHA DAMGASI DOGRULAMASI (BaBa 17:0x, 9 Eki 2026):
- Yukleme + bekleme sonrasi worker'dan `https://foto-onizleme-pruvo-shop.gmlmz.workers.dev/onizleme-surum.json`
  okunur (onbellek atlatici `?v=<sha>`); sha'yuken HEAD ile ayni olmalidir.
- Uymazsa 3 deneme (30 sn arayla); sonra rc 2 `MAKINE_KOS HATA damga-uyusmaz beklenen=<sha8> okunan=<sha8>`.
- `--yukleme-yok` kipinde de damga OKUNUR ve basilir; `--beklenen-sha` verilmisse okunamaz sirayla
  karsilastirilir, verilmemisse yalniz basila.
- Test kancasi: `ONIZLEME_KOS_HTTP_READER` env'i ile gercek aga gidilmeden sahte okuyucu kullanilabilir
  (url -> str; testin hermetik kalmasini saglar).
- Okuyucu acik User-Agent gonderir: CF, urllib'in varsayilan `Python-urllib/x` imzasini 403 + `error code: 1010`
  ile reddediyordu (9 Eki olcum; tarayici 200). Okuma hatasi satiri kok nedeni basar
  (`hata=HTTPError=<kod> <govde>` / `hata=URLError=<reason>`), yalniz istisna tipini DEGIL.
"""
import argparse
import json
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
DAMGA_URL = "https://foto-onizleme-pruvo-shop.gmlmz.workers.dev/onizleme-surum.json"
DAMGA_DENEME = 3
DAMGA_BEKLEME = 30  # sn
UA = "pruvo-onizleme-damga/1 (+https://pruvo3d.com)"  # varsayilan Python-urllib imzasi CF 1010 ile reddedilir


class OkumaHatasi(RuntimeError):
    """_http_oku hatasi; metni kok nedeni tasir."""


def wrangler():
    k = os.environ.get("ONIZLEME_KOS_WRANGLER", "")
    return shlex.split(k) if k else ["npx", "--prefix", SHOP, "wrangler"]


def _http_oku(url):
    """Test kancasi ONIZLEME_KOS_HTTP_READER varsa onu kullanir; yoksa urllib ile gercek okuma."""
    kanca = os.environ.get("ONIZLEME_KOS_HTTP_READER", "")
    if kanca:
        return shlex.split(kanca)[0]  # sahte okuyucu: komut olarak cagrilamaz, asagidaki fallback
    import urllib.request
    istek = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(istek, timeout=20) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        raise OkumaHatasi("http-okuma-hatasi " + _hata_metni(e)) from e


def _hata_metni(e):
    """Istisnadan kok neden: HTTPError kodu+govde / URLError reason / tip=metin (tek satir, <=200)."""
    import urllib.error
    if isinstance(e, urllib.error.HTTPError):
        try:
            govde = e.read(120).decode("utf-8", "replace")
        except Exception:
            govde = ""
        m = "HTTPError=%d %s" % (e.code, govde)
    elif isinstance(e, urllib.error.URLError):
        m = "URLError=%r" % (e.reason,)
    elif isinstance(e, OkumaHatasi):
        m = str(e)
    else:
        m = "%s=%s" % (type(e).__name__, e)
    return " ".join(m.split())[:200]


def head_sha_al():
    p = subprocess.run(("git", "rev-parse", "HEAD"), cwd=KOK, capture_output=True, text=True)
    return (p.stdout or "").strip()


def damga_dogrula(beklenen_sha):
    """Worker'dan damga oku; beklenen_sha ile karsilastir. Uymazsa 3 deneme (30 sn arayla).

    Dondurur: (okunan_sha veya "", sonuc_rc). beklenen_sha None ise yalniz okur ve basar.
    """
    if not beklenen_sha:
        beklenen_sha = head_sha_al()
    if not beklenen_sha:
        print("MAKINE_KOS HATA head-sha-bos")
        return ("", 2)
    beklenen8 = beklenen_sha[:8]
    okunan = ""
    for deneme in range(1, DAMGA_DENEME + 1):
        try:
            ham = _http_oku(DAMGA_URL + "?v=" + beklenen_sha)
            veri = json.loads(ham)
            okunan = (veri.get("sha") or "").strip()
            if okunan == beklenen_sha:
                print("MAKINE_KOS damga=" + okunan[:8] + " rc=0")
                return (okunan, 0)
            print("MAKINE_KOS damga-deneme=%d beklenen=%s okunan=%s" % (deneme, beklenen8, okunan[:8]))
        except Exception as e:
            print("MAKINE_KOS damga-deneme=%d hata=%s" % (deneme, _hata_metni(e)))
        if deneme < DAMGA_DENEME:
            time.sleep(DAMGA_BEKLEME)
    print("MAKINE_KOS HATA damga-uyusmaz beklenen=%s okunan=%s" % (beklenen8, okunan[:8]))
    return (okunan, 2)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--yukleme-yok", action="store_true", help="foto-onizleme.py yukle ADIMINI atla (kod ayni)")
    ap.add_argument("--bekle", type=int, default=75, help="takma ad yayilimi icin bekleme (sn)")
    ap.add_argument("--beklenen-sha", default="", help="damga dogrulamasi icin beklenen sha (yoksa HEAD)")
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
    beklenen = a.beklenen_sha or head_sha_al()
    if not a.yukleme_yok:
        y = subprocess.run([sys.executable, os.path.join(KOK, "tools", "foto-onizleme.py"), "yukle"],
                           capture_output=True, text=True, cwd=KOK, timeout=900)
        print("MAKINE_KOS yukle rc=%d %s" % (y.returncode, ((y.stdout or "").strip().splitlines() or [""])[-1][:160]))
        if y.returncode != 0:
            return 2
    time.sleep(max(0, a.bekle))
    okunan, drc = damga_dogrula(beklenen)
    if drc != 0 and a.beklenen_sha:
        return drc
    alt = subprocess.run(komut, env=dict(os.environ, **{AD: anahtar}), cwd=KOK)
    return alt.returncode


if __name__ == "__main__":
    sys.exit(main())
