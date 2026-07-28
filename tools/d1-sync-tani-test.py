#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""d1-sync.py Wrangler hata tanisi regresyon testi; D1'e/ag'a dokunmaz."""
import importlib.util
import os

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = importlib.util.spec_from_file_location(
    "d1_sync_tani", os.path.join(KOK, "tools", "d1-sync.py"))
D1 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D1)


class Sonuc:
    def __init__(self, kod, stdout="", stderr=""):
        self.returncode = kod
        self.stdout = stdout
        self.stderr = stderr


def senaryo(sonuclar):
    """subprocess.run icin sirali sahte sonuclar; (cagri, sonuc/exit-mesaji) dondur."""
    cagri = [0]

    def sahte_run(*args, **kwargs):
        i = min(cagri[0], len(sonuclar) - 1)
        cagri[0] += 1
        return sonuclar[i]

    eski_run, eski_sleep = D1.subprocess.run, D1.time.sleep
    D1.subprocess.run, D1.time.sleep = sahte_run, lambda saniye: None
    try:
        try:
            sonuc = D1.wrangler(["--command", "SELECT 1"])
            return cagri[0], sonuc
        except SystemExit as e:
            return cagri[0], str(e.code)
    finally:
        D1.subprocess.run, D1.time.sleep = eski_run, eski_sleep


def main():
    gecen = 0
    toplam = 3

    cagri, mesaj = senaryo([
        Sonuc(1, stderr="getaddrinfo ENOTFOUND registry.npmjs.org")
    ])
    gecici_tani_dogru = cagri == 3 and "GECICI HATA, yeniden dene" in mesaj
    cagri_auth, sonuc_auth = senaryo([
        Sonuc(1, stderr="Authentication error [code: 10000]"),
        Sonuc(0, stdout='[{"results": [], "success": true}]'),
    ])
    gecici_10000_kurtuldu = (
        cagri_auth == 2 and sonuc_auth == [{"results": [], "success": True}])
    if gecici_tani_dogru and gecici_10000_kurtuldu:
        gecen += 1
        print("GECTI gecici hata -> dogru tani; gecici 10000 -> retry ile basari")
    else:
        print("KALDI gecici hata:", cagri, mesaj, cagri_auth, sonuc_auth)

    cagri, mesaj = senaryo([
        Sonuc(1, stderr="Authentication error [code: 10000]")
    ])
    if cagri == 3 and "GERCEK 10000 - auth" in mesaj:
        gecen += 1
        print("GECTI gercek auth -> 2 retry + GERCEK 10000")
    else:
        print("KALDI gercek auth:", cagri, mesaj)

    cagri, sonuc = senaryo([
        Sonuc(0, stdout='[{"results": [], "success": true}]')
    ])
    if cagri == 1 and sonuc == [{"results": [], "success": True}]:
        gecen += 1
        print("GECTI basarili JSON -> eski davranis")
    else:
        print("KALDI basarili JSON:", cagri, sonuc)

    print("SONUC: %d/%d" % (gecen, toplam))
    raise SystemExit(0 if gecen == toplam else 1)


if __name__ == "__main__":
    main()
