#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Drive STL klasorune yaz -> sha256 dogrula -> yerel Drive kopyasini GERI AT (evict).

NEDEN (STL-SIFIR, 6 Eki 2026): `thing-hazirla.py` her STL'yi Drive STL klasorune de yaziyordu;
Google Drive (FileProvider) yazilan dosyayi diskte "indirilmis" birakir -> Drive klasoru
makinede kalici yer kaplar (Okan kurali: makinede iz birakma). Ana dosya Drive'da kalir,
yalniz yerel onbellek kopyasi `FileManager.default.evictUbiquitousItem` ile atilir
(mimar 6 Eki olctu: 23.436 KB -> 0, boyut ayni).

SIRA ZORUNLU: evict YALNIZ geri okunan sha256 yazilan veriyle ESIT ise yapilir — yazim
bozuksa yerel kopya kanit olarak kalir (UYUSMAZ). Evict basarisizsa dosya Drive'da yine
vardir; yalniz disk yeri geri alinmamistir (BIRAKILAMADI) — veri kaybi yolu yok.
Bu modul hicbir seyi SILMEZ.
"""

import hashlib
import subprocess

# Foundation API (swift yorumlayicisi stdin'den okur; arguman = dosya yolu).
_SWIFT_EVICT = (
    "import Foundation\n"
    "do { try FileManager.default.evictUbiquitousItem("
    "at: URL(fileURLWithPath: CommandLine.arguments[1])) }\n"
    "catch { print(error); exit(1) }\n"
)


def evict(yol):
    """Drive/iCloud yerel kopyasini geri atar. True = basarili."""
    try:
        r = subprocess.run(["swift", "-", yol], input=_SWIFT_EVICT, capture_output=True,
                           text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def sha256_dosya(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for p in iter(lambda: f.read(1 << 20), b""):
            h.update(p)
    return h.hexdigest()


def yaz_dogrula_birak(yol, data, birak_fn=None):
    """`data`yi `yol`a yazar, geri okuyup sha256 dogrular, esitse evict eder.
    Doner: "BIRAKILDI" | "BIRAKILAMADI" (evict basarisiz) | "UYUSMAZ" (yazim bozuk, evict YOK)."""
    birak = birak_fn or evict
    with open(yol, "wb") as f:
        f.write(data)
    if sha256_dosya(yol) != hashlib.sha256(data).hexdigest():
        return "UYUSMAZ"
    return "BIRAKILDI" if birak(yol) else "BIRAKILAMADI"
