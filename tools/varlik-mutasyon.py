#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VARLIK KAPISI MUTASYON NOBETI — tools/varlik-test.py OLU NOBETCI mi?

NEDEN VAR: bir kabul testinin "yesil" olmasi tek basina hicbir sey kanitlamaz; asil soru
BOZULDUGUNDA KIRMIZI YANIYOR MU. Bu betik tools/build.py'nin GECICI bir kopyasina spec'in
5. bolumundeki alti mutanti tek tek uygular ve varlik-test'in her birinde beklenen rengi
verdigini olcer. GERCEK DEPO DOSYASINA DOKUNULMAZ: mutasyon, tools/ agacinin gecici bir
kopyasinda yapilir (kok girdileri ve .git gercek depoya symlink; .git gerekli cunku
varlik-test kiyas ureticisini git gecmisinden alir).

KONTROL MUTANTI ZORUNLU (M6): davranisi degistirmeyen bir yeniden adlandirma YESIL
kalmali. Aksi halde "her degisiklikte kirmizi yanan" bir kapi da bu testten gecerdi ve
kirmizilarin hicbir bilgi degeri olmazdi ([[fikstur-degeri-mutasyon-koru]]).

Kullanim: python3 tools/varlik-mutasyon.py
Cikis: 0 = alti mutantin altisi da beklenen rengi verdi · 1 = en az biri sapti.
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
# Symlink DEGIL, gercek (bos) dizin olmasi gerekenler: uretim ciktilari.
YEREL_DIZINLER = ("varlik", "urun", "_yayin")

# (kod, aciklama, eski, yeni, beklenen_rc)
MUTANTLAR = [
    ("M1", "hash sabitlendi (icerik degisse de ad degismez)",
     'return hashlib.sha256(icerik.encode("utf-8")).hexdigest()[:VARLIK_HASH_UZUNLUK]',
     'return "0000000000"', 1),
    ("M2", "sayfadaki referans YANLIS ada baglandi",
     '    _VARLIK_ONBELLEK[ad] = url\n    return url',
     '    _VARLIK_ONBELLEK[ad] = url\n    return url.replace("-", "-0", 1)', 1),
    ("M3", "harici dosyaya CSS'in bir kismi yazilmadi (kirpma)",
     '        govde = yorum_soy.css_soy(icerik)',
     '        govde = yorum_soy.css_soy(icerik)[:-50]', 1),
    ("M4", "sayfa govdesinden bir meta alani dusuruldu",
     '<meta name="twitter:card" content="summary_large_image">\n', '', 1),
    ("M5", "satir-ici cekirdek kaynaktan koparildi (IKIZ uretildi)",
     '    parcalar = ["<style>" + cekirdek + "</style>",',
     '    parcalar = ["<style>:root{--navy:#12294d}*{box-sizing:border-box}</style>",', 1),
    ("M6", "KONTROL: davranisi degistirmeyen yeniden adlandirma",
     'def varlik_adres(onek, uzanti, icerik):', 'def varlik_adres(on_ek, uzanti, icerik):', 0),
]
# M6 yeniden adlandirmasinin govdedeki devami (tek mutant, uc nokta).
M6_EK = [
    ('                           % (onek, uzanti))', '                           % (on_ek, uzanti))'),
    ('    ad = "%s-%s.%s" % (onek, varlik_hash(govde), uzanti)',
     '    ad = "%s-%s.%s" % (on_ek, varlik_hash(govde), uzanti)'),
]


def gecici_kok():
    tmp = tempfile.mkdtemp(prefix="varlik-mutasyon-")
    shutil.copytree(TOOLS, os.path.join(tmp, "tools"), symlinks=True)
    os.symlink(os.path.join(ROOT, ".git"), os.path.join(tmp, ".git"))
    for ad in os.listdir(ROOT):
        if ad in ("tools", ".git") or ad in YEREL_DIZINLER:
            continue
        os.symlink(os.path.join(ROOT, ad), os.path.join(tmp, ad))
    for ad in YEREL_DIZINLER:
        os.makedirs(os.path.join(tmp, ad), exist_ok=True)
    return tmp


def uygula(yol, ciftler):
    s = io.open(yol, encoding="utf-8").read()
    for eski, yeni in ciftler:
        n = s.count(eski)
        if n != 1:
            return None, "capa %d kez gecti (1 bekleniyordu): %r" % (n, eski[:60])
        s = s.replace(eski, yeni, 1)
    io.open(yol, "w", encoding="utf-8").write(s)
    return True, ""


def kos(tmp):
    p = subprocess.run([sys.executable, os.path.join(tmp, "tools", "varlik-test.py"),
                        "--ornek", "6"], capture_output=True, text=True, timeout=3600)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    # 0) MUTASYONSUZ TABAN: kopya agac oldugu gibi YESIL olmali (yoksa mutant
    #    kirmizilarinin hicbiri mutasyondan geliyor sayilamaz).
    tmp = gecici_kok()
    try:
        rc, cikti = kos(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if rc != 0:
        print("TABAN KIRMIZI (rc=%d) -> mutasyon olcumu ANLAMSIZ.\n%s" % (rc, cikti[-1500:]))
        return 1
    print("  taban (mutasyonsuz): rc=0 YESIL")

    sapan = []
    print("\n%-4s %-58s %-8s %-8s %s" % ("KOD", "MUTANT", "BEKLENEN", "OLCULEN", "SONUC"))
    for kod, aciklama, eski, yeni, beklenen in MUTANTLAR:
        ciftler = [(eski, yeni)] + (M6_EK if kod == "M6" else [])
        tmp = gecici_kok()
        try:
            ok, hata = uygula(os.path.join(tmp, "tools", "build.py"), ciftler)
            if not ok:
                sapan.append("%s: capa uygulanamadi (%s)" % (kod, hata))
                print("%-4s %-58s %-8s %-8s CAPA YOK" % (kod, aciklama[:58], beklenen, "-"))
                continue
            rc, cikti = kos(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        renk = "KIRMIZI" if rc == 1 else ("YESIL" if rc == 0 else "rc=%d" % rc)
        tamam = (rc == beklenen)
        if not tamam:
            sapan.append("%s: beklenen rc=%d, olculen rc=%d" % (kod, beklenen, rc))
        print("%-4s %-58s %-8s %-8s %s"
              % (kod, aciklama[:58], "KIRMIZI" if beklenen else "YESIL", renk,
                 "OK" if tamam else "SAPTI"))

    if sapan:
        print("\nSAPMA (%d):" % len(sapan))
        for s in sapan:
            print("  - " + s)
        return 1
    print("\nOK: alti mutantin altisi da beklenen rengi verdi (M6 kontrol mutanti YESIL).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
