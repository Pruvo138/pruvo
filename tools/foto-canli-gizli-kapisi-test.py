#!/usr/bin/env python3
"""Kabul: tools/foto-canli-gizli-kapisi.py (program kapaliyken foto bolumu canlida GORUNMEZ).

Agsiz, deterministik (fikstur + node). Vakalar:
  V1 kapali + HTML hidden + gercek JS            -> YESIL rc 0
  V2 kapali + HTML hidden YOK                    -> KIRMIZI rc 1 (sebep html-hidden-yok)
  V3 kapali + HTML hidden + JS /acik'i beklemeden acar (mutant JS) -> KIRMIZI rc 1 (sebep js-aciyor)
  V4 acik program (1 tur)                        -> UYGULANMAZ rc 0
  V5 ag hatasi (erisilemez kok)                  -> OLCULEMEDI rc 2
  V6 /acik HTTP hatasi (ok=0) + hidden           -> YESIL (bolum kodu hata yanitinda acmaz)
  V7 kor kosucu (JS hic acamaz) -> pozitif kontrol OLCULEMEDI rc 2 (sessiz YESIL yok)
MUTANT (kapinin kopyasinda): M-A (a) kontrolu silinir -> V2 YESIL'e doner = V2 bunu yakalar;
                             M-B (b) kontrolu silinir -> V3 YESIL'e doner = V3 bunu yakalar.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEPO = Path(__file__).resolve().parent.parent
KAPI = DEPO / "tools" / "foto-canli-gizli-kapisi.py"
KARAR = DEPO / "tools" / "foto-canli-gizli-karar.mjs"
JS = DEPO / "foto-uretim.js"
VERI = DEPO / "foto-uretim-veri.js"

HTML_GIZLI = '<html><body><section id="fotoUretim" class="foto-uretim" hidden aria-label="x"></section></body></html>'
HTML_ACIK = '<html><body><section id="fotoUretim" class="foto-uretim" aria-label="x"></section></body></html>'
ACIK_KAPALI = '{"acik":false,"turler":[]}'
ACIK_TEK = '{"acik":true,"turler":[{"kod":"plaket","ad":"Kabartma plaket"}]}'

# V3 mutanti = KG-M1 (shop/test/foto-uretim.mjs) ile ayni: bolum /acik beklemeden acilir (eski davranis).
JS_CAPA = "    cizYukleniyor();\n    acikYukle();"
JS_MUTANT = "    bolum.removeAttribute(\"hidden\");\n    cizYukleniyor();\n    acikYukle();"
# V7: bolum kodu hic acamaz (removeAttribute silinir) -> pozitif kontrol kor kosucuyu yakalamali.
JS_KOR_CAPA = 'if (anaBolum) anaBolum.removeAttribute("hidden");'

HATA = []


def ol(ad, kosul, ayrinti=""):
    print("%s %s%s" % ("OK  " if kosul else "FAIL", ad, ("  | " + ayrinti) if not kosul else ""))
    if not kosul:
        HATA.append(ad)


def kos(kapi, d, html, acik, js=None, ek=()):
    (d / "s.html").write_text(html, encoding="utf-8")
    (d / "a.json").write_text(acik, encoding="utf-8")
    komut = [sys.executable, str(kapi), "--fikstur-html", str(d / "s.html"), "--fikstur-acik", str(d / "a.json"),
             "--fikstur-js", str(js or JS), "--fikstur-veri", str(VERI), "--deneme", "1", "--bekle", "0", *ek]
    r = subprocess.run(komut, capture_output=True, text=True, timeout=120)
    satir = next((s for s in r.stdout.splitlines() if s.startswith("FOTO_CANLI_GIZLI=")), "")
    return r.returncode, satir, r.stdout + r.stderr


def mutant_kapi(d, ad, capa_isareti):
    kaynak = KAPI.read_text(encoding="utf-8")
    satirlar = kaynak.splitlines(keepends=True)
    hedef = [i for i, s in enumerate(satirlar) if capa_isareti in s]
    if len(hedef) != 1:
        return None
    girinti = satirlar[hedef[0]][: len(satirlar[hedef[0]]) - len(satirlar[hedef[0]].lstrip())]
    satirlar[hedef[0]] = girinti + "if False:  # " + capa_isareti + " (mutant)\n"
    md = d / ad
    md.mkdir()
    (md / "foto-canli-gizli-kapisi.py").write_text("".join(satirlar), encoding="utf-8")
    shutil.copy(KARAR, md / "foto-canli-gizli-karar.mjs")
    return md / "foto-canli-gizli-kapisi.py"


def main():
    with tempfile.TemporaryDirectory(prefix="foto-canli-gizli-test-") as g:
        d = Path(g)
        js_kaynak = JS.read_text(encoding="utf-8")
        js_mut = d / "foto-uretim-mutant.js"
        js_mut.write_text(js_kaynak.replace(JS_CAPA, JS_MUTANT, 1), encoding="utf-8")
        ol("V3 on-kosul: JS mutant capasi kaynakta 1 kez", js_kaynak.count(JS_CAPA) == 1)
        js_kor = d / "foto-uretim-kor.js"
        js_kor.write_text(js_kaynak.replace(JS_KOR_CAPA, "", 1), encoding="utf-8")
        ol("V7 on-kosul: kor capa kaynakta 1 kez", js_kaynak.count(JS_KOR_CAPA) == 1)

        rc, s, t = kos(KAPI, d, HTML_GIZLI, ACIK_KAPALI)
        ol("V1 kapali + hidden -> YESIL rc 0", rc == 0 and s.startswith("FOTO_CANLI_GIZLI=YESIL acik_tur=0"), t)
        print("    " + s)
        rc, s, t = kos(KAPI, d, HTML_ACIK, ACIK_KAPALI)
        ol("V2 kapali + hidden YOK -> KIRMIZI rc 1 + geri alma komutu",
           rc == 1 and s.startswith("FOTO_CANLI_GIZLI=KIRMIZI sebep=html-hidden-yok") and "gh run rerun" in t, t)
        print("    " + s)
        rc, s, t = kos(KAPI, d, HTML_GIZLI, ACIK_KAPALI, js=js_mut)
        ol("V3 kapali + hidden + JS aciyor -> KIRMIZI rc 1", rc == 1 and s.startswith("FOTO_CANLI_GIZLI=KIRMIZI sebep=js-aciyor"), t)
        print("    " + s)
        rc, s, t = kos(KAPI, d, HTML_ACIK, ACIK_TEK)
        ol("V4 acik program -> UYGULANMAZ acik_tur=1 rc 0", rc == 0 and s == "FOTO_CANLI_GIZLI=UYGULANMAZ acik_tur=1", t)
        print("    " + s)
        r = subprocess.run([sys.executable, str(KAPI), "--kok", "http://127.0.0.1:9/", "--deneme", "2", "--bekle", "0"],
                           capture_output=True, text=True, timeout=120)
        s = next((x for x in r.stdout.splitlines() if x.startswith("FOTO_CANLI_GIZLI=")), "")
        ol("V5 ag hatasi -> OLCULEMEDI rc 2 (2 deneme, YESIL DEGIL)",
           r.returncode == 2 and s.startswith("FOTO_CANLI_GIZLI=OLCULEMEDI") and r.stderr.count("OLCULEMEDI") == 2,
           r.stdout + r.stderr)
        print("    " + s)
        rc, s, t = kos(KAPI, d, HTML_GIZLI, '{"hata":"x"}', ek=("--fikstur-acik-ok", "0"))
        ol("V6 /acik HTTP hatasi + hidden -> YESIL", rc == 0 and s.startswith("FOTO_CANLI_GIZLI=YESIL"), t)
        rc, s, t = kos(KAPI, d, HTML_GIZLI, ACIK_KAPALI, js=js_kor)
        ol("V7 kor kosucu -> pozitif kontrol OLCULEMEDI rc 2", rc == 2 and "pozitif-kontrol" in s, t)

        ma = mutant_kapi(d, "ma", "MUTANT-CAPA-A")
        ol("M-A capa kapida 1 kez", ma is not None)
        if ma:
            rc, s, t = kos(ma, d, HTML_ACIK, ACIK_KAPALI)
            ol("M-A (a) kontrolu silinince V2 YESIL'e doner -> V2 mutanti YAKALAR", rc == 0 and "=YESIL" in s, t)
            print("    M-A V2: " + s)
        mb = mutant_kapi(d, "mb", "MUTANT-CAPA-B")
        ol("M-B capa kapida 1 kez", mb is not None)
        if mb:
            rc, s, t = kos(mb, d, HTML_GIZLI, ACIK_KAPALI, js=js_mut)
            ol("M-B (b) kontrolu silinince V3 YESIL'e doner -> V3 mutanti YAKALAR", rc == 0 and "=YESIL" in s, t)
            print("    M-B V3: " + s)

    print("FOTO_CANLI_GIZLI_TEST=%s hata=%d" % ("YESIL" if not HATA else "KIRMIZI", len(HATA)))
    return 1 if HATA else 0


if __name__ == "__main__":
    sys.exit(main())
