#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/onizleme-deploy-hazirla.py — onizleme worker'inin DEPLOY konfigurasyonunu uretir.

NEDEN VAR (5 Agu 2026): `onizleme/wrangler.toml` icindeki container imaj yolu bir HESAP
KIMLIGI tasiyordu ve depo PUBLIC. Kimlik kaynaktan kaldirildi; izlenen dosyada yerinde
`__HESAP_KIMLIGI__` YER TUTUCUSU duruyor. Deploy anda kimligi ortamdan alir ve yalnizca
GIT-DISI bir kopyaya yazar:

    CLOUDFLARE_ACCOUNT_ID=<kimlik> python3 tools/onizleme-deploy-hazirla.py
    npx wrangler deploy -c onizleme/wrangler.deploy.toml

`CLOUDFLARE_ACCOUNT_ID` zaten wrangler'in KENDI okudugu degiskendir — yeni bir sir turu
ICAT EDILMEDI, yalnizca kaynaktaki DUZ METIN kopya kaldirildi.

🔴 FAIL-CLOSED: degisken yoksa/bicimsizse dosya URETILMEZ (cikis 2). Yer tutucu izlenen
dosyada bulunamazsa da URETILMEZ — sessizce "zaten kimlik yazili" bir toml'u kopyalayip
onu deploy etmek, kapatilan ifsayi geri getirirdi.
🔴 URETILEN DOSYA GIT-DISIDIR (.gitignore). Bu arac ONU GIT'E EKLEMEZ ve izlenen
`onizleme/wrangler.toml`'a ASLA YAZMAZ.

Kullanim:
    python3 tools/onizleme-deploy-hazirla.py                 # uret (CLOUDFLARE_ACCOUNT_ID sart)
    python3 tools/onizleme-deploy-hazirla.py --kendini-test  # offline kabul testi

Cikis kodu: 0 = uretildi/test yesil, 1 = test kirmizi, 2 = OLCULEMEDI (fail-closed).
"""
import argparse
import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True

KAYNAK = "onizleme/wrangler.toml"
HEDEF = "onizleme/wrangler.deploy.toml"
YER_TUTUCU = "__HESAP_KIMLIGI__"
_KIMLIK = re.compile(r"^[0-9a-f]{32}$")

BASLIK = (
    "# URETILMIS DOSYA — ELLE DUZENLEME. Kaynak: %s\n"
    "# Uretici: tools/onizleme-deploy-hazirla.py (hesap kimligi ortamdan gelir).\n"
    "# GIT-DISI: bu dosya commit EDILMEZ (.gitignore).\n" % KAYNAK
)


def _kok():
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return r.stdout.strip()


def uret(govde, kimlik):
    """Saf donusum: yer tutucuyu kimlikle degistirir. Yer tutucu YOKSA None doner."""
    if YER_TUTUCU not in govde:
        return None
    return BASLIK + govde.replace(YER_TUTUCU, kimlik)


def _kendini_test():
    sonuclar = []
    ornek = 'image = "registry.example.com/' + YER_TUTUCU + '/imaj@sha256:abc"\n'
    sahte = "f" * 32

    c = uret(ornek, sahte)
    sonuclar.append(("IDDIA-1 yer tutucu ikame edildi",
                     c is not None and YER_TUTUCU not in c and sahte in c,
                     "cikti=%r" % (c or "")[-60:]))
    sonuclar.append(("IDDIA-2 yer tutucu YOKSA uretim YOK (sessiz kopya kacisi kapali)",
                     uret('image = "registry.example.com/%s/imaj"\n' % sahte, sahte) is None,
                     "yer tutucusuz govde None donmeli"))
    sonuclar.append(("IDDIA-3 bicimsiz kimlik REDDEDILIR",
                     not _KIMLIK.match("KISA") and not _KIMLIK.match("g" * 32)
                     and bool(_KIMLIK.match(sahte)),
                     "regex tam 32 hane onaltilik ister"))
    # Izlenen kaynak GERCEKTEN yer tutuculu mu (kimlik geri sizmis mi)?
    kok = _kok()
    ok = False
    detay = "git kok bulunamadi"
    if kok:
        try:
            with open(os.path.join(kok, KAYNAK), "r", encoding="utf-8") as f:
                govde = f.read()
            ok = YER_TUTUCU in govde and not re.search(
                r"registry\.cloudflare\.com/[0-9a-f]{32}/", govde)
            detay = "yer tutucu var=%s" % (YER_TUTUCU in govde)
        except OSError as e:
            detay = "okunamadi: %s" % e
    sonuclar.append(("IDDIA-4 izlenen %s yer tutuculu (duz metin kimlik YOK)" % KAYNAK, ok, detay))

    basarisiz = [s for s in sonuclar if not s[1]]
    for etiket, gecti, detay in sonuclar:
        print("  [%s] %s — %s" % ("PASS" if gecti else "FAIL", etiket, detay))
    print("  TOPLAM: %d/%d gecti" % (len(sonuclar) - len(basarisiz), len(sonuclar)))
    return 0 if not basarisiz else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kendini-test", action="store_true", help="offline kabul testi")
    args = ap.parse_args()
    if args.kendini_test:
        return _kendini_test()

    kok = _kok()
    if not kok:
        print("OLCULEMEDI: git kok dizini bulunamadi")
        return 2
    kimlik = (os.environ.get("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    if not _KIMLIK.match(kimlik):
        print("OLCULEMEDI: CLOUDFLARE_ACCOUNT_ID tanimli degil ya da bicimsiz "
              "(tam 32 hane onaltilik beklenir). Dosya URETILMEDI.")
        return 2
    try:
        with open(os.path.join(kok, KAYNAK), "r", encoding="utf-8") as f:
            govde = f.read()
    except OSError as e:
        print("OLCULEMEDI: %s okunamadi (%s)" % (KAYNAK, e))
        return 2
    cikti = uret(govde, kimlik)
    if cikti is None:
        print("OLCULEMEDI: %s icinde %s yer tutucusu YOK — uretim yapilmadi."
              % (KAYNAK, YER_TUTUCU))
        return 2
    hedef = os.path.join(kok, HEDEF)
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(cikti)
    print("URETILDI: %s (git-disi)" % HEDEF)
    print("DEPLOY  : npx wrangler deploy -c %s" % HEDEF)
    return 0


if __name__ == "__main__":
    sys.exit(main())
