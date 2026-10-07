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
import time

# Foundation API (swift yorumlayicisi stdin'den okur; arguman = dosya yolu).
_SWIFT_EVICT = (
    "import Foundation\n"
    "do { try FileManager.default.evictUbiquitousItem("
    "at: URL(fileURLWithPath: CommandLine.arguments[1])) }\n"
    "catch { print(error); exit(1) }\n"
)


# YUKLEME SINYALI (7 Eki 2026 olcumu): `NSURLUbiquitousItemIsUploadedKey` Google Drive
# File Provider'da 744/744 dosyada OKUNDU; 742 icerik dosyasi up=1, 2 `.DS_Store` up=0
# (Drive .DS_Store'u hic yuklemez). SALT OKUMA — dosyaya dokunmaz.
# Cikti: "1" yuklendi · "0" yuklenmedi · "nil" ubiquitous degil/okunamadi.
_SWIFT_YUKLENDI = (
    "import Foundation\n"
    "let u = URL(fileURLWithPath: CommandLine.arguments[1])\n"
    "guard let v = try? u.resourceValues(forKeys: [.isUbiquitousItemKey, "
    ".ubiquitousItemIsUploadedKey]), v.isUbiquitousItem == true, "
    "let up = v.ubiquitousItemIsUploaded else { print(\"nil\"); exit(2) }\n"
    "print(up ? \"1\" : \"0\")\n"
)


def yuklendi_mi(yol):
    """Drive'a yukleme BITTI mi? True | False | None (okunamadi — fail-closed: bitmedi say)."""
    try:
        r = subprocess.run(["swift", "-", yol], input=_SWIFT_YUKLENDI, capture_output=True,
                           text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    cikti = (r.stdout or "").strip()
    if cikti == "1":
        return True
    if cikti == "0":
        return False
    return None


def yukleme_bekle(yol, son_an, aralik, yokla_fn=None, uyku=time.sleep, saat=time.monotonic):
    """`yol` yuklenene kadar `aralik` sn arayla yoklar; `son_an` (monotonic) gecince birakir.
    True = yuklendi (evict guvenli) · False = tavan doldu (evict YOK, yerel SILINMEZ)."""
    yokla = yokla_fn or yuklendi_mi
    while True:
        if yokla(yol) is True:
            return True
        kalan = son_an - saat()
        if kalan <= 0:
            return False
        uyku(min(aralik, kalan))


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
