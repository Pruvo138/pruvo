#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lisans-ifsa-kapisi.py kabul testi — sentetik fikstur (BELLEKTE) + bellek-ici mutantlar.

Diske HIC yazmaz, gercek urunler.json / gizli kaydi OKUMAZ: fikstur metin olarak `kos()`a
verilir. Mutantlar kapinin KAYNAK METNI uzerinde bellekte uretilir (isaretli satir `pass`
olur ya da hedefli degistirme) ve `exec` ile ayri ad uzayinda kosulur.

Vakalar: (a)(b)(c) KIRMIZI · (d) CC BY kontrol YESIL · temiz ozgun YESIL · kaynaksiz kip ·
fail-closed (bozuk JSON / dizi degil / id yok / gizli yok / ayirici sifir) · GERCEK
`build.attribution_html` bagi (c kolu sayfaya basan fonksiyona bagli mi).
Son satir: `VAKA=<n> VAKA_KIRMIZI=<n> MUTANT=<n> SURVIVOR=<n>`; rc 0 yalniz ikisi 0 iken.
"""
import json
import os
import re
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
KAPI = os.path.join(_HERE, "lisans-ifsa-kapisi.py")
TURLER = frozenset({"kendi-tasarim", "ozgun-tasarim"})


def _sahte_atif(p):
    """Kol (c)'yi (a)'dan AYIRMAK icin: lisans'siz `atif` alanindan markup uretir."""
    return '<div class="attribution">%s</div>' % p["atif"] if p.get("atif") else ""


def _u(id_, **kw):
    d = {"id": id_, "baslik": "Kutu", "aciklama": "Organizer kutu.", "fiyat": "500 TL",
         "kategori": "Ev", "marka": [], "gorseller": []}
    d.update(kw)
    return d


KAYNAK = {
    "oz-1": {"tur": "kendi-tasarim", "lisans": "kendi-tasarim"},
    "oz-2": {"tur": "Ozgun-Tasarim "},
    "cc-1": {"tur": "ucretsiz-cc", "lisans": "CC BY 4.0"},
    "uy-1": {"tur": "uyelik"},
}
CC_LIS = {"tasarimci": "Ayse", "tur": "CC BY 4.0"}


def _f(urunler, kaynak=KAYNAK):
    return json.dumps(urunler), (None if kaynak is None else json.dumps(kaynak))


def _temel():
    return [_u("oz-1"), _u("oz-2"), _u("cc-1", lisans=CC_LIS), _u("uy-1")]


def _degis(i, **kw):
    u = _temel()
    u[i].update(kw)
    return u


# (ad, (urunler_metni, kaynak_metni), kwargs, beklenen_rc, beklenen_ihlal_kumesi|None,
#  son satirda olmasi gereken alt dizge)
VAKALAR = [
    ("temiz-ozgun-YESIL", _f(_temel()), {}, 0, set(), "ozgun=2 ihlal=0 rc=0"),
    ("d-ccby-lisansli-YESIL", _f([_u("oz-1"), _u("cc-1", lisans=CC_LIS)]), {}, 0, set(),
     "ozgun=1 ihlal=0 rc=0"),
    ("d-ccby-lisanssiz-ODULSUZ", _f([_u("oz-1"), _u("cc-1")]), {}, 0, set(),
     "ozgun=1 ihlal=0 rc=0"),
    ("a-lisans-anahtari", _f(_degis(0, lisans={})), {}, 1, {("a", "oz-1")}, "ihlal=1 rc=1"),
    ("a-lisans-null", _f(_degis(1, lisans=None)), {}, 1, {("a", "oz-2")}, "ihlal=1 rc=1"),
    ("b-ic-etiket-aciklama", _f(_degis(0, aciklama="Uretim: PRUVO (Kendi uretec)")), {}, 1,
     {("b", "oz-1")}, "ihlal=1 rc=1"),
    ("b-ic-etiket-ozgun-olmayan", _f(_degis(3, notlar=["KENDI-TASARIM"])), {}, 1,
     {("b", "uy-1")}, "ihlal=1 rc=1"),
    ("c-atif-bos-degil", _f(_degis(0, atif="Design by PRUVO")), {}, 1, {("c", "oz-1")},
     "ihlal=1 rc=1"),
    ("c-gercek-build-bagi", _f(_degis(0, lisans=CC_LIS)), {"atif_fn": None}, 1,
     {("a", "oz-1"), ("c", "oz-1")}, "ihlal=2 rc=1"),
    ("vaka-olayi-kendi-tasarim-lisansi",
     _f(_degis(0, lisans={"tasarimci": "PRUVO (kendi uretec)", "tur": "kendi-tasarim"})),
     {"atif_fn": None}, 1, {("a", "oz-1"), ("b", "oz-1"), ("c", "oz-1")}, "ihlal=3 rc=1"),
    ("kaynaksiz-temiz", _f(_temel(), None), {"kaynaksiz": True}, 0, set(),
     "ozgun=OLCULEMEDI ihlal=0 rc=0 kapsam=kaynaksiz"),
    ("kaynaksiz-b-yakalar", _f(_degis(2, lisans={"tur": "kendi-tasarim"}), None),
     {"kaynaksiz": True}, 1, {("b", "cc-1")}, "rc=1 kapsam=kaynaksiz"),
    ("OLCULEMEDI-bozuk-urunler", ("[{", json.dumps(KAYNAK)), {}, 2, None, "OLCULEMEDI"),
    ("OLCULEMEDI-bozuk-kaynak", (json.dumps(_temel()), "{x"), {}, 2, None, "OLCULEMEDI"),
    ("OLCULEMEDI-dizi-degil", (json.dumps({"id": "oz-1"}), json.dumps(KAYNAK)), {}, 2, None,
     "OLCULEMEDI"),
    ("OLCULEMEDI-id-yok", _f([_u("oz-1"), {"baslik": "x"}]), {}, 2, None, "OLCULEMEDI"),
    ("OLCULEMEDI-kaynak-nesne-degil", (json.dumps(_temel()), "[]"), {}, 2, None, "OLCULEMEDI"),
    ("OLCULEMEDI-gizli-yok-beyansiz", _f(_temel(), None), {}, 2, None, "OLCULEMEDI"),
    ("OLCULEMEDI-ayirici-sifir", _f([_u("cc-1", lisans=CC_LIS), _u("uy-1")]), {}, 2, None,
     "OLCULEMEDI"),
]

_IHLAL_RE = re.compile(r"^LISANS_IFSA IHLAL kol=(\w) id=(\S+) ")


def vaka_kos(mod, vaka):
    ad, (um, km), kw, b_rc, b_ihlal, b_son = vaka
    kw = dict(kw)
    kw.setdefault("turler", TURLER)
    if "atif_fn" not in kw:
        kw["atif_fn"] = _sahte_atif
    rc, satirlar = mod.kos(um, km, **kw)
    ihlal = {m.groups() for m in map(_IHLAL_RE.match, satirlar) if m}
    hatalar = []
    if rc != b_rc:
        hatalar.append("rc=%s beklenen=%s" % (rc, b_rc))
    if b_ihlal is not None and ihlal != b_ihlal:
        hatalar.append("ihlal=%s beklenen=%s" % (sorted(ihlal), sorted(b_ihlal)))
    if not satirlar or not satirlar[-1].startswith("LISANS_IFSA ") or b_son not in satirlar[-1]:
        hatalar.append("son satir=%r beklenen alt dizge=%r" % (satirlar[-1:] or "", b_son))
    return hatalar


def _modul(kaynak, ad):
    mod = types.ModuleType(ad)
    mod.__file__ = KAPI
    exec(compile(kaynak, KAPI, "exec"), mod.__dict__)
    return mod


def _sil(isaret):
    """Isaretli satiri girintisini koruyarak `pass` yapar (kolun denetimi silinir)."""
    def f(src):
        satirlar = src.split("\n")
        n = [i for i, s in enumerate(satirlar) if s.rstrip().endswith("# " + isaret)]
        if len(n) != 1:
            raise RuntimeError("isaret %s %d kez bulundu (1 beklenir)" % (isaret, len(n)))
        s = satirlar[n[0]]
        satirlar[n[0]] = s[:len(s) - len(s.lstrip())] + "pass"
        return "\n".join(satirlar)
    return f


def _degistir(eski, yeni):
    def f(src):
        if src.count(eski) != 1:
            raise RuntimeError("mutant capasi %r %d kez bulundu" % (eski, src.count(eski)))
        return src.replace(eski, yeni)
    return f


MUTANTLAR = [
    ("KOL-A-silindi", _sil("KOL-A")),
    ("KOL-B-silindi", _sil("KOL-B")),
    ("KOL-C-silindi", _sil("KOL-C")),
    ("SIFIR-KORUMA-silindi", _sil("SIFIR-KORUMA")),
    ("AYIRICI-tum-katalog", _degistir(
        "if ozgun_mu(kaynaklar.get(p[\"id\"]), turler)]", "]")),
    ("RC-hep-0", _degistir("rc = 1 if ihlaller else 0", "rc = 0")),
    ("ATIF-BAGI-kopuk", _degistir(
        "atif_fn = gercek_atif() if atif_fn is None else atif_fn",
        "atif_fn = (lambda p: \"\") if atif_fn is None else atif_fn")),
    ("OLCULEMEDI-rc-0", _degistir(
        "return 2, [\"LISANS_IFSA OLCULEMEDI", "return 0, [\"LISANS_IFSA OLCULEMEDI")),
    ("IC-ETIKET-buyuk-kucuk-duyarli", _degistir(", re.IGNORECASE)", ")")),
    ("GIZLI-YOK-fail-open", _degistir(
        "raise Olculemedi(\"gizli kaynak kaydi yok (--kaynaksiz verilmedi)\")",
        "kaynaksiz = True")),
]


def main():
    with open(KAPI, encoding="utf-8") as f:
        kaynak = f.read()
    asil = _modul(kaynak, "lisans_ifsa_asil")
    kirmizi = 0
    for v in VAKALAR:
        h = vaka_kos(asil, v)
        print("VAKA %-36s %s" % (v[0], "YESIL" if not h else "KIRMIZI " + "; ".join(h)))
        kirmizi += bool(h)
    survivor = 0
    for ad, mut in MUTANTLAR:
        try:
            mod = _modul(mut(kaynak), "lisans_ifsa_mutant")
            olduren = [v[0] for v in VAKALAR if vaka_kos(mod, v)]
        except RuntimeError as e:
            print("MUTANT %-30s KURULAMADI (%s) -> SURVIVOR sayilir" % (ad, e))
            survivor += 1
            continue
        if olduren:
            print("MUTANT %-30s OLDURULDU (%s)" % (ad, ", ".join(olduren[:3])))
        else:
            print("MUTANT %-30s SURVIVOR" % ad)
            survivor += 1
    print("VAKA=%d VAKA_KIRMIZI=%d MUTANT=%d SURVIVOR=%d"
          % (len(VAKALAR), kirmizi, len(MUTANTLAR), survivor))
    return 0 if kirmizi == 0 and survivor == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
