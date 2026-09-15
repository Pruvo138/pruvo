#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL + MUTANT — tools/sayfalar.py _seo_md_to_html() satir ici **bold** -> <strong> (canli kusur).

NEDEN VAR: dalga 53/54 sayfalarinda canlida literal `**` gorunuyordu (ornek:
`pos-terminali-ve-satis-noktasi-plastik-oem-parca-uretimi`). Donusturucu `#`/`##`/`- ` blogu
duzgun isletti ama satir ici `**x**` -> <strong>x</strong> YOKTU; 67 cagri yerinde hep ayni
fonksiyon kullanildigi icin dalga bazli tek tek yakalamak YERINE katalog ekseninde olculuyor.

YONTEM (offline, stdlib, ag yok, ~2-3 s):
  * V1-V6 fikstur: _seo_md_to_html(md) dogrudan cagirilir; beklenen HTML esit mi kontrol edilir.
  * KATALOG EKSENI: `import sayfalar`; tum CONTENT_PAGES icin fn() cagirip BELLEKTE HTML uret
    (dosya YAZMAZ); `**` tasiyan sayfa ve toplam `**` sayisini bas. Kabul = 0.
  * MUTANT: tools/sayfalar.py GECICI dizine kopyalanir; `_satir_ici` govdesi no-op haline
    getirilir ve import edilir. Canli dosyaya YAZMAZ; oncesi/sonrasi `shasum -a 256` esit olmali.
    Beklenti: V1-V4 KIRMIZI (literal `**` kaliyor), V5/V6 YEŞIL kaliyor.

IDDIALAR (toplam 6 fikstur):
  V1 paragraf "a **b** c"          -> "<p>a <strong>b</strong> c</p>"
  V2 liste    "- **X:** y"         -> <li><strong>X:</strong> y</li>
  V3 ayni satirda iki bold         -> <p><strong>a</strong> ve <strong>b</strong></p>
  V4 baslik   "## **Baslik**"      -> <h2><strong>Baslik</strong></h2>
  V5 kapanmamis "**a kapatmamis"   -> degismez (uydurma kapama yok)
  V6 bold'suz metin BIREBIR        -> onceki davranis korunur (regresyon)

Kabul: SONUC: VAKA=<g>/<n> MUTANT=<oldu>/<n> LITERAL_BOLD_SAYFA=<n> HUKUM=YESIL|KIRMIZI
Kosum: python3 tools/seo-md-donusum-test.py
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools")
HEDEF_DOSYA = os.path.join(ARAC, "sayfalar.py")

HATA = []
BILGI = []


def _shasum(dosya):
    s = subprocess.run(["shasum", "-a", "256", dosya], capture_output=True, text=True, timeout=30)
    if s.returncode != 0 or not s.stdout.strip():
        raise RuntimeError("shasum basarisiz: rc=%d" % s.returncode)
    return s.stdout.split()[0]


def _yukle(dosya):
    spec = importlib.util.spec_from_file_location("_smt_sayfalar", dosya)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def vakalari_kos(mod):
    """V1-V6 fiksturu calistirir; (gecen, toplam) doner."""
    fn = mod._seo_md_to_html
    gecen = 0
    toplam = 0

    # V1: paragraf
    toplam += 1
    out = fn("a **b** c").strip()
    beklenen = "<p>a <strong>b</strong> c</p>"
    if out == beklenen:
        gecen += 1
        print("  ✅ [V1] paragraf         : %s" % out)
    else:
        HATA.append("V1 yanlis: '%s' (beklenen '%s')" % (out, beklenen))
        print("  ❌ [V1] paragraf         : %s   (beklenen %s)" % (out, beklenen))

    # V2: liste
    toplam += 1
    out = fn("- **X:** y")
    beklenen = "<ul>\n<li><strong>X:</strong> y</li>\n</ul>"
    if out.strip() == beklenen:
        gecen += 1
        print("  ✅ [V2] liste            : %s" % out.replace("\n", "|"))
    else:
        HATA.append("V2 yanlis: %r" % out)
        print("  ❌ [V2] liste            : %r   (beklenen %r)" % (out, beklenen))

    # V3: ayni satirda iki bold
    toplam += 1
    out = fn("**a** ve **b**").strip()
    beklenen = "<p><strong>a</strong> ve <strong>b</strong></p>"
    if out == beklenen:
        gecen += 1
        print("  ✅ [V3] iki bold         : %s" % out)
    else:
        HATA.append("V3 yanlis: '%s' (beklenen '%s')" % (out, beklenen))
        print("  ❌ [V3] iki bold         : %s   (beklenen %s)" % (out, beklenen))

    # V4: ## baslik
    toplam += 1
    out = fn("## **Baslik**").strip()
    beklenen = "<h2><strong>Baslik</strong></h2>"
    if out == beklenen:
        gecen += 1
        print("  ✅ [V4] h2 kalin         : %s" % out)
    else:
        HATA.append("V4 yanlis: '%s' (beklenen '%s')" % (out, beklenen))
        print("  ❌ [V4] h2 kalin         : %s   (beklenen %s)" % (out, beklenen))

    # V5: kapanmamis **a degismez (uydurma kapama yok)
    toplam += 1
    out = fn("**a kapatmamis").strip()
    if "**" in out and "<strong>" not in out:
        gecen += 1
        print("  ✅ [V5] kapanmamis       : %s   (degmedi, dogru)" % out)
    else:
        HATA.append("V5 kapanmamis degisti: '%s'" % out)
        print("  ❌ [V5] kapanmamis       : %s   (degmemeliydi)" % out)

    # V6: bold'suz metin birebir (regresyon)
    toplam += 1
    md = "# Baslik\n\nBu bir paragraf.\n\n- Liste ogesi\n\n## Alt baslik"
    out = fn(md)
    beklenen_satirlar = [
        "<h1>Baslik</h1>",
        "<p>Bu bir paragraf.</p>",
        "<ul>",
        "<li>Liste ogesi</li>",
        "</ul>",
        "<h2>Alt baslik</h2>",
    ]
    satirlar = [s.strip() for s in out.strip().splitlines()]
    if satirlar == beklenen_satirlar:
        gecen += 1
        print("  ✅ [V6] regresyon        : birebir esit (6 satir)")
    else:
        HATA.append("V6 regresyon bozuk: %s" % satirlar)
        print("  ❌ [V6] regresyon        : bozuk (beklenen=%s alinan=%s)"
              % (beklenen_satirlar, satirlar))

    return gecen, toplam


def katalog_ekseni(mod):
    """CONTENT_PAGES'in tumunu render eder; literal `**` tasiyan sayfa sayisini olcer.

    TUM CONTENT_PAGES olculur — hard-HTML sayfalarin literal `**` kusuru da BU eksen
    kapsamindadir. Onceki "_seo_md_to_html kullananlar" suzgeci spec'i sessizce
    daraltip 14 sayfayi gizliyordu. Dosya YAZMAZ; sadece fn() cagirir.

    Returns: (literal_sayfa, literal_toplam, ornekler, katalog_sayfa, render_hatasi)
    """
    sayfalar = mod.CONTENT_PAGES
    literal_sayfa = 0
    literal_toplam = 0
    ornekler = []
    render_hatasi = 0
    for slug, _baslik, _meta, uretici in sayfalar:
        try:
            html = uretici()
        except Exception:
            render_hatasi += 1
            continue
        n = html.count("**")
        if n:
            literal_sayfa += 1
            literal_toplam += n
            if len(ornekler) < 5:
                ornekler.append((slug, n))
    return literal_sayfa, literal_toplam, ornekler, len(sayfalar), render_hatasi


def mutant_ekseni():
    """sayfalar.py GECICI dizine kopyalanir; _satir_ici varsa no-op haline getirilir.

    Canli dosyanin SHA'si oncesi/sonrasi esit olmali. Beklenen: V1-V4 KIRMIZI (literal `**` kaliyor),
    V5/V6 YEŞIL kaliyor.
    """
    sha_oncesi = _shasum(HEDEF_DOSYA)
    gecici = tempfile.mkdtemp(prefix="seo-md-test-")
    try:
        kopya = os.path.join(gecici, "sayfalar.py")
        shutil.copyfile(HEDEF_DOSYA, kopya)
        with open(kopya, encoding="utf-8") as f:
            kaynak = f.read()

        # _satir_ici tanimini no-op haline getir (def satirinin TAMAMINI no-op ile degistir)
        yeni = re.sub(
            r"^(\s*)def _satir_ici\b[^\n]*$",
            r"\1def _satir_ici(t):  # seo-md-test mutant: no-op\n\1    return t",
            kaynak,
            flags=re.MULTILINE,
            count=1,
        )
        mutasyon_yapildi = (yeni != kaynak)
        if mutasyon_yapildi:
            with open(kopya, "w", encoding="utf-8") as f:
                f.write(yeni)

        sha_sonra = _shasum(HEDEF_DOSYA)
        if sha_oncesi != sha_sonra:
            return False, "canli SHA degisti! (%s != %s)" % (sha_oncesi, sha_sonra), mutasyon_yapildi

        mod = _yukle(kopya)
        fn = mod._seo_md_to_html

        beklenen_kirmizi = 0  # V1-V4: mutant durumda literal `**` kalmali
        beklenen_yesil = 0    # V5/V6: mutant durumda da dogru davranmali

        # V1
        out = fn("a **b** c").strip()
        if "**b**" in out and "<strong>b</strong>" not in out:
            beklenen_kirmizi += 1
            print("  ✅ [M-V1] mutant: V1 KIRMIZI  : %s" % out)
        else:
            print("  ❌ [M-V1] mutant: V1 donusmus  : %s" % out)

        # V2
        out = fn("- **X:** y")
        if "**X:**" in out and "<strong>X:</strong>" not in out:
            beklenen_kirmizi += 1
            print("  ✅ [M-V2] mutant: V2 KIRMIZI  : %s" % out.replace("\n", "|"))
        else:
            print("  ❌ [M-V2] mutant: V2 donusmus  : %s" % out.replace("\n", "|"))

        # V3
        out = fn("**a** ve **b**").strip()
        if "**a**" in out and "**b**" in out and "<strong>" not in out:
            beklenen_kirmizi += 1
            print("  ✅ [M-V3] mutant: V3 KIRMIZI  : %s" % out)
        else:
            print("  ❌ [M-V3] mutant: V3 donusmus  : %s" % out)

        # V4
        out = fn("## **Baslik**").strip()
        if "**Baslik**" in out and "<strong>Baslik</strong>" not in out:
            beklenen_kirmizi += 1
            print("  ✅ [M-V4] mutant: V4 KIRMIZI  : %s" % out)
        else:
            print("  ❌ [M-V4] mutant: V4 donusmus  : %s" % out)

        # V5 — mutant durumda da kapanmamis degismemeli
        out = fn("**a kapatmamis").strip()
        if "**" in out and "<strong>" not in out:
            beklenen_yesil += 1
            print("  ✅ [M-V5] mutant: V5 YEŞIL    : kapanmamis bozulmadi")
        else:
            print("  ❌ [M-V5] mutant: V5 bozuldu   : %s" % out)

        # V6 — mutant durumda da bold'suz metin birebir
        md = "# Baslik\n\nBu bir paragraf.\n\n- Liste ogesi\n\n## Alt baslik"
        out = fn(md)
        beklenen_satirlar = [
            "<h1>Baslik</h1>",
            "<p>Bu bir paragraf.</p>",
            "<ul>",
            "<li>Liste ogesi</li>",
            "</ul>",
            "<h2>Alt baslik</h2>",
        ]
        satirlar = [s.strip() for s in out.strip().splitlines()]
        if satirlar == beklenen_satirlar:
            beklenen_yesil += 1
            print("  ✅ [M-V6] mutant: V6 YEŞIL    : regresyon korundu")
        else:
            print("  ❌ [M-V6] mutant: V6 bozuldu  : %s" % satirlar)

        # V1-V4 tamamen kirmizi (4/4), V5/V6 tamamen yesil (2/2)
        mutant_ok = (beklenen_kirmizi == 4 and beklenen_yesil == 2)
        return mutant_ok, "V1-V4=%d/4 V5/V6=%d/2 mutasyon=%s" % (
            beklenen_kirmizi, beklenen_yesil, "yapildi" if mutasyon_yapildi else "yapilmadi(_satir_ici yok)"
        ), mutasyon_yapildi
    finally:
        shutil.rmtree(gecici, ignore_errors=True)


def main():
    print("=" * 70)
    print("SEO md donusumu — satir ici **bold** kabul testi")
    print("=" * 70)

    print()
    print("=== VAKA: fikstur (V1-V6) ===")
    mod = _yukle(HEDEF_DOSYA)
    vg, vt = vakalari_kos(mod)

    print()
    print("=== KATALOG EKSENI: tum CONTENT_PAGES (hard-HTML dahil) ===")
    l_sayfa, l_toplam, ornekler, katalog_sayfa, render_hatasi = katalog_ekseni(mod)
    print("  KATALOG_SAYFA                : %d" % katalog_sayfa)
    print("  render hatasi sayfa         : %d" % render_hatasi)
    print("  literal '**' tasiyan        : %d sayfa, toplam %d adet" % (l_sayfa, l_toplam))
    for slug, n in ornekler:
        print("    · %s : %d adet '**'" % (slug, n))

    print()
    print("=== MUTANT: _satir_ici no-op kopya ===")
    mutant_ok, mutant_bilgi, _mut_yapildi = mutant_ekseni()
    print("  sonuc               : %s" % ("OLU" if mutant_ok else "OLMADI"))
    print("  detay               : %s" % mutant_bilgi)

    print()
    print("-" * 70)
    # fail-closed: render_hatasi>0 ise kirmizi
    hukum = "YESIL" if (vg == vt and l_sayfa == 0 and render_hatasi == 0 and mutant_ok) else "KIRMIZI"
    print("SONUC: VAKA=%d/%d MUTANT=%s/4 KATALOG_SAYFA=%d LITERAL_BOLD_SAYFA=%d RENDER_HATASI=%d HUKUM=%s"
          % (vg, vt, ("oldu" if mutant_ok else "olmadı"), katalog_sayfa, l_sayfa, render_hatasi, hukum))
    return 0 if hukum == "YESIL" else 1


if __name__ == "__main__":
    sys.exit(main())
