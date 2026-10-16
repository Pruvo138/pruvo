#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VARLIK KAPISI — WhatsApp ikonu dar istisnasi kabul bataryasi (Okan 16 Eki 2026).

NEDEN VAR: Okan "whatsapp butonunu burdan kaldır" dedi; kompakt eylem satirindaki
`<a class="ikon-btn ikon-wa" id="orderAlt">` kalkti. `varlik-test.py::cikarim_kaybi` eski
referanstaki ikonun `wa.me?text=…` baglantisini "sorgu parametresi KAYIP" sayiyordu (beyan
edilemez sinif) -> SERIT B `38921106836` kirmizi, merge edilseydi serit-a3 YAYINI kapatirdi.
`_wa_ikonu_ayikla` yalniz YENI sayfada ikon yokken eski sayfadaki ikon <a>'sini kiyastan cikarir.

VAKALAR (hepsi `cikarim_kaybi()` uzerinden, sentetik sayfa):
  W1  eski: ikon + bant linki · yeni: yalniz bant linki (ayni)      -> bulgu 0
  W2  eski: ikon + bant linki · yeni: ikon yok, BANT metni degisti  -> "sorgu parametresi" KIRMIZI
  W3  eski: ikon + bant linki · yeni: ikon yok, BANT linki tumden yok -> "YOLU KAYIP" / "sorgu" KIRMIZI
  W4  eski: ikon + bant · yeni: ikon VAR ama metni degisti           -> KIRMIZI (ikon varken ayiklanmaz)
  W5  KONTROL: eski = yeni (ikonlu)                                  -> bulgu 0
MUTANTLAR (izole kopya):
  M1  ayiklama kapatilir (eski aynen doner)       -> W1 KIRMIZI
  M2  "yenide ikon var mi" kosulu kalkar (her zaman ayikla) -> W4 YESIL (yakalanmali)
  M3  ayiklama deseni tum wa.me <a>'larina genisler -> W2 YESIL (yakalanmali)

KOSUM: python3 tools/varlik-wa-ikon-test.py   (rc=0 => YESIL)
"""
import importlib.util
import os
import sys
import tempfile
import shutil

KOK = os.path.dirname(os.path.abspath(__file__))
KAYNAK = os.path.join(KOK, "varlik-test.py")

NO = "905451386526"
IKON = ('<a class="ikon-btn ikon-wa" id="orderAlt" href="https://wa.me/%s?text=ilgileniyorum%%20urun" '
        'target="_blank" rel="noopener" aria-label="WhatsApp\'tan Sor"><svg></svg></a>' % NO)
BANT = '<a class="help-cta-btn" href="https://wa.me/%s?text=%s">Bize yazin</a>'


def sayfa(ikon=None, bant_metin="yardim%20istiyorum", bant=True):
    govde = '<button class="ikon-btn ikon-sepet" id="cartBtn">Sepete Ekle</button>'
    if ikon:
        govde += ikon
    if bant:
        govde += BANT % (NO, bant_metin)
    return ("<html><head><title>T</title><link rel=\"canonical\" href=\"https://pruvo3d.com/urun/x/\">"
            "</head><body><main>%s</main></body></html>" % govde)


def yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def kos(mod):
    sk = lambda b: [x for x in b if "<a href" in x or "YOLU KAYIP" in x]
    r = {}
    eski = sayfa(IKON)
    r["W1"] = sk(mod.cikarim_kaybi(eski, sayfa()))
    r["W2"] = sk(mod.cikarim_kaybi(eski, sayfa(bant_metin="baska%20metin")))
    r["W3"] = sk(mod.cikarim_kaybi(eski, sayfa(bant=False)))
    r["W4"] = sk(mod.cikarim_kaybi(eski, sayfa(IKON.replace("ilgileniyorum", "degisti"))))
    r["W5"] = sk(mod.cikarim_kaybi(eski, sayfa(IKON)))
    return r


BEKLENEN = {"W1": False, "W2": True, "W3": True, "W4": True, "W5": False}  # True = bulgu VAR
ESKI_GOVDE = ("    if _WA_IKON_RE.search(yeni_html):\n        return eski_html\n"
              "    return _WA_IKON_RE.sub(\"\", eski_html)\n")
MUTANTLAR = (
    ("M1 ayiklama kapali", ESKI_GOVDE, "    return eski_html\n", "W1"),
    ("M2 yenide-ikon kosulu kalkti", ESKI_GOVDE, "    return _WA_IKON_RE.sub(\"\", eski_html)\n", "W4"),
    ("M3 ayiklama tum wa.me <a>'larina genisledi",
     "    return _WA_IKON_RE.sub(\"\", eski_html)\n",
     "    return re.sub(r'<a [^>]*wa\\.me[^>]*>.*?</a>', \"\", eski_html, flags=re.S)\n", "W2"),
)


def main():
    hata = 0
    td = tempfile.mkdtemp(prefix="varlik-wa-ikon-")
    try:
        mod = yukle(KAYNAK, "varlik_wa_asil")
        r = kos(mod)
        for v, bek in BEKLENEN.items():
            ok = bool(r[v]) == bek
            hata += int(not ok)
            print("%s %s bulgu=%d (beklenen %s) %s" % ("✅" if ok else "🔴", v, len(r[v]),
                  "VAR" if bek else "YOK", (r[v][:1] or [""])[0][:90]))
        with open(KAYNAK, encoding="utf-8") as f:
            metin = f.read()
        for ad, capa, yama, hedef in MUTANTLAR:
            if metin.count(capa) != 1:
                print("🔴 %s CAPA_ADEDI=%d" % (ad, metin.count(capa)))
                hata += 1
                continue
            yol = os.path.join(td, "m.py")
            with open(yol, "w", encoding="utf-8") as f:
                f.write(metin.replace(capa, yama))
            rm = kos(yukle(yol, "varlik_wa_mut"))
            oldu = bool(rm[hedef]) != BEKLENEN[hedef]
            hata += int(not oldu)
            print("%s %s -> %s bulgu=%d" % ("✅ OLDU" if oldu else "🔴 YASADI", ad, hedef, len(rm[hedef])))
    finally:
        shutil.rmtree(td, ignore_errors=True)
    print("SONUC: %s" % ("YESIL ✅" if hata == 0 else "KIRMIZI 🔴 hata=%d" % hata))
    return 0 if hata == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
