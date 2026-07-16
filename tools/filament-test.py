#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FILAMENT REHBERI KABUL TESTLERI — tools/paket-filament-rehberi.md'deki 7 test.

Kullanim:
    python3 tools/filament-test.py              # 7 testin hepsi (parite dahil, ag gerekir)
    PARITE=0 python3 tools/filament-test.py     # test 5 (parite, ag) atlanir

Once tools/build.py'yi CALISTIRIR (uretilen sayfalar taze olsun), sonra sirayla:
  1. urunler.json DEGISMEMIS (git diff bos — paket urun verisine dokunmaz)
  2. rastgele 20 urun sayfasi: sitede satilan filament cipleri (ABS/Karbon HARIC) + tavsiye
     rozeti + balon metni filamentler.json ile birebir + kategori haritasina gore dogru tavsiye
  3. hicbir uretilen sayfada "3d bask" / "her renk" yok
  4. /malzeme-rehberi/ uretildi, footer linki var, sitemap'te
  5. node tools/parite-test.js 300 + node tools/parite-ege.js 200 YESIL (aciklama degismedi)
  6. override: tavsiyeFilament alanli sahte urunle render -> harita degil override basiliyor
  7. mobil tooltip: DOM/CSS duzeyinde dogrulama (balon + .acik toggle JS + aria-expanded)
  8. ABS/Karbon Katkili urun sayfasinda CIP OLARAK basilmiyor (site seceneği degil, sadece
     /malzeme-rehberi/ + WhatsApp notu)
"""
import html
import json
import os
import random
import re
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import filament_ortak

SONUC = []


def kayit(no, ad, gecti, detay=""):
    SONUC.append((no, ad, gecti, detay))
    print("  %s TEST %d — %s%s" % ("✅" if gecti else "❌", no, ad,
                                   (" | " + detay) if detay else ""), flush=True)


def sayfa(pid):
    with open(os.path.join(ROOT, "urun", pid, "index.html"), encoding="utf-8") as f:
        return f.read()


def main():
    print("0) tools/build.py calisiyor (uretim taze olsun)...", flush=True)
    r = subprocess.run([sys.executable, os.path.join(TOOLS, "build.py")],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        print(r.stdout + r.stderr)
        sys.exit("build.py HATA verdi — testler kosulmadi.")
    print("   " + r.stdout.strip())

    with open(os.path.join(ROOT, "urunler.json"), encoding="utf-8") as f:
        urunler = json.load(f)
    ref = filament_ortak.referans()
    site_fil = [f for f in ref["filamentler"] if f.get("site")]
    ozel_fil = [f for f in ref["filamentler"] if not f.get("site")]

    # ---- 1) urunler.json degismemis
    d = subprocess.run(["git", "diff", "--name-only", "--", "urunler.json"],
                       capture_output=True, text=True, cwd=ROOT)
    kayit(1, "urunler.json degismemis (git diff bos)", d.stdout.strip() == "",
          d.stdout.strip() or "temiz")

    # ---- 2) rastgele 20 urun sayfasi: cipler + rozet + balon metni + dogru tavsiye
    hatalar = []
    for p in random.sample(urunler, 20):
        s = sayfa(p["id"])
        cip_n = len(re.findall(r'class="fil-cip( tavsiyeli)?"', s))
        if cip_n != len(site_fil):
            hatalar.append("%s: cip sayisi %d != %d" % (p["id"], cip_n, len(site_fil)))
            continue
        for f in site_fil:
            if html.escape(f["uzun"], quote=True) not in s:
                hatalar.append("%s: '%s' balon metni birebir degil" % (p["id"], f["ad"]))
        for f in ozel_fil:
            if html.escape(f["uzun"], quote=True) in s:
                hatalar.append("%s: '%s' (ozel talep) urun sayfasinda cip olarak var" % (p["id"], f["ad"]))
        beklenen = ([] if p.get("parametrik") else
                    [t["ad"] for t in filament_ortak.tavsiyeler(
                        p.get("kategori"), p.get("tavsiyeFilament"))])
        rozetli = [m.group(1) for m in re.finditer(
            r'fil-cip tavsiyeli[^>]*>.*?<span class="fil-ad">([^<]+)</span>', s)]
        if sorted(rozetli) != sorted(beklenen):
            hatalar.append("%s (%s): rozet %s != beklenen %s"
                           % (p["id"], p.get("kategori"), rozetli, beklenen))
        if p.get("parametrik") and html.escape(ref["parametrikNot"], quote=True) not in s:
            hatalar.append("%s: parametrik not yok" % p["id"])
    kayit(2, "20 rastgele sayfa: %d cip (ABS/Karbon HARIC) + rozet + balon birebir + dogru tavsiye"
          % len(site_fil), not hatalar, "; ".join(hatalar[:4]))

    # ---- 3) yasak ifadeler: uretilen HICBIR sayfada "3d bask" / "her renk" yok
    yasak = []
    for pat in ["3d bask", "her renk"]:
        g = subprocess.run(["grep", "-rli", pat, "urun", "malzeme-rehberi",
                            "teslimat-iade", "mesafeli-satis", "filament-veri.js",
                            "sitemap.xml", "index.html", "sss", "hakkimizda",
                            "iletisim", "gizlilik"],
                           capture_output=True, text=True, cwd=ROOT)
        if g.stdout.strip():
            yasak.append("%r: %s" % (pat, g.stdout.strip().splitlines()[:3]))
    kayit(3, "'3D bask' ve 'her renk' hicbir uretilen sayfada yok", not yasak,
          "; ".join(yasak))

    # ---- 4) /malzeme-rehberi/ uretildi + footer linki + sitemap
    reh_yol = os.path.join(ROOT, "malzeme-rehberi", "index.html")
    reh_var = os.path.exists(reh_yol)
    reh = open(reh_yol, encoding="utf-8").read() if reh_var else ""
    sm = open(os.path.join(ROOT, "sitemap.xml"), encoding="utf-8").read()
    ornek_sayfa = sayfa(urunler[0]["id"])
    kosullar = {
        "sayfa uretildi": reh_var,
        "%d malzemenin hepsi rehberde" % len(ref["filamentler"]):
            reh_var and all((f.get("uzunAd") or f["ad"]) in reh for f in ref["filamentler"]),
        "karsilastirma tablosu": "karsilastirma" in reh and "HDT @ 0.45 MPa" in reh,
        "urun sayfasi footer linki": '/malzeme-rehberi/' in ornek_sayfa,
        "sitemap kaydi": "https://pruvo3d.com/malzeme-rehberi/" in sm,
    }
    kayit(4, "/malzeme-rehberi/ + footer + sitemap", all(kosullar.values()),
          ", ".join(k for k, v in kosullar.items() if not v) or "hepsi tamam")

    # ---- 5) parite testleri (ag gerekir; PARITE=0 ile atlanabilir)
    if os.environ.get("PARITE", "1") == "0":
        kayit(5, "parite testleri", True, "ATLANDI (PARITE=0)")
    else:
        p1 = subprocess.run(["node", os.path.join(TOOLS, "parite-test.js"), "300"],
                            capture_output=True, text=True, cwd=ROOT)
        p2 = subprocess.run(["node", os.path.join(TOOLS, "parite-ege.js"), "200"],
                            capture_output=True, text=True, cwd=ROOT)
        ok = p1.returncode == 0 and p2.returncode == 0
        det = "site:%s ege:%s" % ("YESIL" if p1.returncode == 0 else "KIRMIZI",
                                  "YESIL" if p2.returncode == 0 else "KIRMIZI")
        if not ok:
            det += " | " + (p1.stdout + p1.stderr + p2.stdout + p2.stderr).strip()[-300:]
        kayit(5, "parite (site + ege) — aciklama degismedi kaniti", ok, det)

    # ---- 6) override: sahte urunle render -> harita degil override basiliyor
    import importlib
    build = importlib.import_module("build")
    sahte = {"id": "test-override-sahte", "kategori": "Ev", "marka": [],
             "baslik": "Override Test", "aciklama": "test", "fiyat": "100 TL",
             "gorseller": [], "tavsiyeFilament": ["ASA"]}
    h = build.render_product(sahte, [sahte])
    rozetli = [m.group(1) for m in re.finditer(
        r'fil-cip tavsiyeli[^>]*>.*?<span class="fil-ad">([^<]+)</span>', h)]
    kayit(6, "tavsiyeFilament override haritayi eziyor (Ev+override[ASA] -> rozet ASA)",
          rozetli == ["ASA"], "rozetli=%s" % rozetli)

    # ---- 7) mobil tooltip: DOM/CSS duzeyinde dogrulama
    s = ornek_sayfa
    blok = s.split('class="malzeme-blok"', 1)[1].split("</a></div>", 1)[0] \
        if 'class="malzeme-blok"' in s else ""
    kosullar7 = {
        "balon her cipte": s.count('class="fil-balon"') == len(site_fil),
        "CSS: .acik ile balon acilir": ".fil-cip.acik .fil-balon{display:block}" in s,
        "CSS: hover ile balon acilir": ".fil-cip:hover .fil-balon" in s,
        "JS: dokunma toggle": 'classList.toggle("acik")' in s,
        "JS: disari dokununca kapanir": 'document.addEventListener("click"' in s,
        "aria-expanded var": 'aria-expanded="false"' in blok,
        "title= kullanilmamis (mobilde calismaz)": blok != "" and "title=" not in blok,
    }
    kayit(7, "mobil tooltip DOM/CSS dogrulamasi", all(kosullar7.values()),
          ", ".join(k for k, v in kosullar7.items() if not v) or "hepsi tamam")

    # ---- 8) ABS/Karbon Katkili urun sayfasinda SITE SECENEGI OLARAK sunulmuyor
    hatalar8 = []
    for f in ozel_fil:
        if ('value="%s"' % f["ad"]) in ornek_sayfa:
            hatalar8.append("%s: <option> olarak dropdown'da var" % f["ad"])
    if "wa.me/905451386526" not in ornek_sayfa:
        hatalar8.append("WhatsApp muhendislik-malzeme linki yok")
    kayit(8, "ABS/Karbon Katkili SITE SECENEGI olarak sunulmuyor (cip/dropdown yok, WA notu var)",
          not hatalar8, "; ".join(hatalar8) or "temiz")

    print("-" * 70)
    kaldi = [x for x in SONUC if not x[2]]
    if kaldi:
        print("SONUC: %d/%d test KIRMIZI ❌" % (len(kaldi), len(SONUC)))
        sys.exit(1)
    print("SONUC: %d/%d test YESIL ✅" % (len(SONUC), len(SONUC)))


if __name__ == "__main__":
    main()
