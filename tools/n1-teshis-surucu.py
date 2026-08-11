#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N1 TESHIS SURUCUSU — RAPOR-MIMARA.md'deki olcumlerin YENIDEN URETICISI.

Bu bir KABUL TESTI DEGILDIR (CI kosmaz, hukum vermez): `fiziksel-urun-kapisi.py` N1
iddiasinin ("…'den başlayan" fiyat `tur`suz 3D sayfada durmali) neden dustugunu
KANITLAYAN teshis kosumudur. Anlatilan olcum kanit degildir; surucu depoda durur.

Uc mod:
  --suclu     kapi SABIT tutularak commit-basi kosum (verilen sha'lar) -> ilk kirmizi
  --celiski   "onarim" fiilen denenir: baslangic_fiyat 1e1f9d9b oncesi bicime dondurulur
              (GECICI AGAC KOPYASINDA; depo agacina YAZMAZ) ve IKI kapi da kosturulur
  --yuzey     `tur`suz 3D sayfada ilan edilen fiyatin bugunku BICIMI dokulur

BULGU (11 Agu): SUCLU=1e1f9d9b, SINIF=B (kasitli). `--celiski` gosterir ki oge geri
konunca `fiziksel-urun-kapisi.py` yesile doner ama `onsecim-parite-kapisi.py`
"SAYFADAKI gorunur tutar = ilan tutari" iddialariyla kirmizi yanar — yani onarim
ticari yuzeyi ONARMAZ, ilan tutarini sepet tutarindan AYIRIR.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

# build.py'de 1e1f9d9b'nin degistirdigi TEK satir (ve oncesi).
YENI_SATIR = "            baslangic_fiyat = esc(taban_fiyat_metni(_ilan_k / 100.0))"
ESKI_SATIR = '            baslangic_fiyat = esc(fiyat) + "&#39;den başlayan"'


def _agac(sha):
    """sha'nin tam agacini gecici dizine acar; yolu dondurur."""
    tmp = tempfile.mkdtemp(prefix="n1-teshis-")
    ar = subprocess.run(["git", "-C", ROOT, "archive", sha], capture_output=True)
    if ar.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        raise SystemExit("git archive basarisiz: %s" % ar.stderr[:300])
    subprocess.run(["tar", "-x", "-C", tmp], input=ar.stdout, capture_output=True)
    return tmp


def _kapi(kok, ad):
    r = subprocess.run([sys.executable, os.path.join(kok, "tools", ad)],
                       capture_output=True, text=True, cwd=kok, timeout=1800)
    return r.returncode, (r.stdout or "")


def mod_suclu(shalar):
    """Kapi SABIT (bugunku kopya), agac degisken -> olculen sey KODUN degisimi."""
    kapi = os.path.join(TOOLS, "fiziksel-urun-kapisi.py")
    for sha in shalar:
        kok = _agac(sha)
        try:
            shutil.copyfile(kapi, os.path.join(kok, "tools", "fiziksel-urun-kapisi.py"))
            rc, cikti = _kapi(kok, "fiziksel-urun-kapisi.py")
            n1 = [l.strip() for l in cikti.splitlines() if l.strip().startswith("N1 ")]
            konu = subprocess.run(["git", "-C", ROOT, "log", "-1", "--format=%s", sha],
                                  capture_output=True, text=True).stdout.strip()[:55]
            print("%s rc=%d | %s | %s" % (sha, rc, n1[0] if n1 else "N1-SATIRI-YOK", konu))
        finally:
            shutil.rmtree(kok, ignore_errors=True)
    return 0


def mod_celiski():
    """CELISKI NOBETI — iki kapi AYNI YONDE mi hukum kuruyor?

    `fiziksel-urun-kapisi.py` ile `onsecim-parite-kapisi.py` ayni yuzeyi (urun sayfasinin
    ilan ettigi tutar) olcer. 11 Agu'da TERS hukum kuruyorlardi: `"…'den başlayan"`
    dizesini geri koymak birini yesile, otekini kirmiziya cekiyordu — hangi kapinin
    susturulacagi bir tercih meselesine donusmustu.

    IDDIA (bu mod rc!=0 ile DUSER):
      (1) degistirilmemis agacta IKISI DE YESIL
      (2) N5 mutantinda (statik tutar liste tutarinda birakilir) IKISI DE KIRMIZI
    Yani "N1'in istedigini yapmak N5'i kirmaz" ve tersi. Bir kapi yesil digeri kirmiziysa
    CELISKI GERI GELMISTIR ve bu mod kirmizi yakar."""
    ADLAR = ["fiziksel-urun-kapisi.py", "onsecim-parite-kapisi.py"]
    olculen = {}
    kok = _agac("HEAD")
    try:
        for etiket in ["asil", "onar"]:
            if etiket == "onar":
                bpy = os.path.join(kok, "tools", "build.py")
                with open(bpy, encoding="utf-8") as f:
                    src = f.read()
                if src.count(YENI_SATIR) != 1:
                    raise SystemExit("CAPA KAYIP/COKLU (%d): build.py degismis, surucu "
                                     "guncellenmeli." % src.count(YENI_SATIR))
                with open(bpy, "w", encoding="utf-8") as f:
                    f.write(src.replace(YENI_SATIR, ESKI_SATIR, 1))
                print("\n=== (2) N5 MUTANTI: statik tutar liste tutarinda birakildi")
            else:
                print("=== (1) DEGISTIRILMEMIS agac")
            for ad in ADLAR:
                rc, cikti = _kapi(kok, ad)
                olculen[(etiket, ad)] = rc
                print("  %-28s rc=%d" % (ad, rc))
                for l in cikti.splitlines():
                    s = l.strip()
                    if s.startswith(("N1F ", "SONUC:")) or "❌" in s:
                        print("      " + s[:150])
    finally:
        shutil.rmtree(kok, ignore_errors=True)

    print("\n=== CELISKI NOBETI")
    hatalar = []
    for ad in ADLAR:
        if olculen[("asil", ad)] != 0:
            hatalar.append("degistirilmemis agacta %s KIRMIZI (rc=%d)"
                           % (ad, olculen[("asil", ad)]))
        if olculen[("onar", ad)] == 0:
            hatalar.append("N5 mutantinda %s YESIL (rc=0) — mutant bu kapida OLU"
                           % ad)
    ayni = len({olculen[("onar", ad)] != 0 for ad in ADLAR}) == 1
    print("  taban  : %s" % {ad: olculen[("asil", ad)] for ad in ADLAR})
    print("  N5 mut.: %s" % {ad: olculen[("onar", ad)] for ad in ADLAR})
    if not ayni:
        hatalar.append("IKI KAPI TERS HUKUM KURUYOR — celiski geri geldi")
    if hatalar:
        print("  KIRMIZI ✘")
        for h in hatalar:
            print("    - " + h)
        return 1
    print("  YESIL ✔ — iki kapi AYNI YONDE: taban ikisi de yesil, N5 mutantinda ikisi de "
          "kirmizi. Celiski YOK.")
    return 0


def mod_yuzey():
    """`tur`suz 3D sayfada ilan edilen fiyat BUGUN hangi bicimde basiliyor?"""
    import importlib.util
    sys.path.insert(0, TOOLS)
    os.chdir(ROOT)
    spec = importlib.util.spec_from_file_location(
        "fkapi", os.path.join(TOOLS, "fiziksel-urun-kapisi.py"))
    fkapi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fkapi)

    mod = fkapi.build_modulu()
    nrm = fkapi._urun("sinama-normal")                      # `tur` alani YOK
    fiz = fkapi._urun("sinama-fiziksel", tur="fiziksel")
    print("ONERI_ONSECIM_ACIK = %s | ilan_kurus(`tur`suz) = %s"
          % (mod.ONERI_ONSECIM_ACIK, mod.ilan_kurus(nrm)))
    for ad, u in [("`tur`suz 3D", nrm), ("fiziksel", fiz)]:
        g = fkapi._govde(mod.render_product(u, [fiz, nrm]))
        blok = re.findall(r'<div class="opsiyon-fiyat"[^>]*>.*?</div>', g, re.S)
        print("  %-12s %s | 'başlayan' govdede: %s"
              % (ad, blok or "FIYAT BLOGU YOK", "başlayan" in g))
    return 0


# --------------------------------------------------------------------------- katki
# Bu daldaki kapi ile GUNCEL origin/main'in kapisi AYNI kod tabaninda (main'in build.py'si)
# yan yana kosturulur; degisen tek sey KAPIDIR. "Dal dogru mu" degil "dal main'e BUGUN ne
# KATIYOR" sorusunun olcumu. Her satir bir EKSEN; ikisi de kirmizi = katki YOK.
KATKI_EKSENLERI = [
    ("build.py", 'fiziksel = (p.get("tur") == "fiziksel")', "fiziksel = False",
     "M1 kosul daima yanlis"),
    ("build.py", 'fiziksel = (p.get("tur") == "fiziksel")', "fiziksel = True",
     "M2 kosul daima dogru"),
    ("build.py",
     """                fiyat_blok=fiyat_satiri(
                    eski_html,
                    '<div class="opsiyon-fiyat" id="opsiyonFiyat">%s</div>' % baslangic_fiyat))""",
     '                fiyat_blok="")',
     "(a) fiyat YUZEYI tumden dusuruldu"),
    ("build.py", "            baslangic_fiyat = esc(taban_fiyat_metni(_ilan_k / 100.0))",
     "            baslangic_fiyat = esc(taban_fiyat_metni(_ilan_k / 100.0 + 1))",
     "(b) tutar 1 TL kaydi — BICIM AYNI"),
    ("build.py", "            baslangic_fiyat = esc(taban_fiyat_metni(_ilan_k / 100.0))",
     '            baslangic_fiyat = esc(fiyat) + "&#39;den başlayan"',
     "(c) statik tutar liste tutarinda (kardes N5)"),
    # Asagidaki IKI eksen MESRU degisikliktir: davranis BOZULMAZ. Dogru kapi YESIL kalmali;
    # kirmizi yanan kapi bicime/deftere bagli demektir (YANLIS POZITIF).
    ("build.py", '    return tam + "," + kusur + " TL"', '    return tam + "." + kusur + " TL"',
     "(d) MESRU: bicimlendirici ondalik ayraci degisti"),
    ("secenekler.js", "  var ONERI_ONSECIM_ACIK = true;", "  var ONERI_ONSECIM_ACIK = false;",
     "(e) MESRU: on-secim bayragi geri kapandi"),
]


def mod_katki():
    """Dal kapisi vs main kapisi — mutant oldurme paritesi + yanlis pozitif ekseni."""
    dal_kapi = os.path.join(TOOLS, "fiziksel-urun-kapisi.py")
    print("=== KATKI OLCUMU (kod tabani: origin/main; degisen YALNIZ kapi)")
    print("%-46s %-9s %-9s %s" % ("eksen", "MAIN", "DAL", "HUKUM"))
    fark = []
    for dosya, eski, yeni, ad in [(None, None, None, None)] + KATKI_EKSENLERI:
        kok = _agac("origin/main")
        try:
            if ad is not None:
                hedef = os.path.join(kok, dosya if dosya != "build.py" else "tools/build.py")
                with open(hedef, encoding="utf-8") as f:
                    src = f.read()
                if src.count(eski) != 1:
                    print("%-46s CAPA YOK/COKLU (%d)" % (ad, src.count(eski)))
                    continue
                with open(hedef, "w", encoding="utf-8") as f:
                    f.write(src.replace(eski, yeni, 1))
            m_rc, _ = _kapi(kok, "fiziksel-urun-kapisi.py")
            shutil.copyfile(dal_kapi, os.path.join(kok, "tools", "dal-kapisi.py"))
            d_rc, _ = _kapi(kok, "dal-kapisi.py")
            etiket = ad or "TABAN (mutantsiz)"
            mesru = etiket.startswith(("(d)", "(e)")) or ad is None
            if mesru:
                hkm = ("ikisi de dogru sessiz ✔" if not m_rc and not d_rc else
                       "DAL YANLIS KIRMIZI ✘" if d_rc and not m_rc else
                       "MAIN YANLIS KIRMIZI ✘" if m_rc and not d_rc else
                       "ikisi de yanlis kirmizi ✘")
            else:
                hkm = ("ikisi de yakaliyor" if m_rc and d_rc else
                       "MAIN KACIRIYOR ← katki" if d_rc and not m_rc else
                       "DAL KACIRIYOR" if m_rc and not d_rc else "IKISI DE KACIRIYOR")
            if ("katki" in hkm) or ("✘" in hkm):
                fark.append("%s: %s" % (etiket, hkm))
            print("%-46s rc=%-6d rc=%-6d %s" % (etiket, m_rc, d_rc, hkm))
        finally:
            shutil.rmtree(kok, ignore_errors=True)
    print("\n=== FARK OZETI")
    if not fark:
        print("  FARK YOK — dal main'e olculebilir bir sey KATMIYOR.")
    else:
        for f in fark:
            print("  - " + f)
    return 0


def main():
    ap = argparse.ArgumentParser(description="N1 ilan fiyati teshis surucusu")
    ap.add_argument("--suclu", nargs="+", metavar="SHA",
                    help="verilen commit'lerde kapiyi SABIT tutup kosturur")
    ap.add_argument("--celiski", action="store_true",
                    help="'onarim'i deneyip iki kapinin celiskisini olcer")
    ap.add_argument("--yuzey", action="store_true",
                    help="bugunku ilan fiyati bicimini doker")
    ap.add_argument("--katki", action="store_true",
                    help="dal kapisi vs origin/main kapisi — mutant oldurme paritesi")
    a = ap.parse_args()
    if a.suclu:
        return mod_suclu(a.suclu)
    if a.celiski:
        return mod_celiski()
    if a.yuzey:
        return mod_yuzey()
    if a.katki:
        return mod_katki()
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
