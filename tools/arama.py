# -*- coding: utf-8 -*-
"""Arama metni uretimi — index.html'deki norm() + haystack()'in BIREBIR karsiligi.

Neden ayri dosya: ayni mantik uc yerde lazim (d1-sync.py yazarken, parite testi
dogrularken, Worker /ara sorgularken). Tek kaynak olmazsa uc kopya sessizce
birbirinden ayrilir ve arama sonuclari site ile D1 arasinda ayrisir.

DIKKAT — Turkce buyuk/kucuk harf tuzagi:
  JS  "İ".toLocaleLowerCase("tr") -> "i"
  PY  "İ".lower()                 -> "i" + U+0307 (birlesik nokta) — FARKLI!
  JS  "I".toLocaleLowerCase("tr") -> "ı" (sonra norm onu "i" yapar)
  PY  "I".lower()                 -> "i"
Bu yuzden lower()'dan ONCE I/İ elle cevrilir. Dogrulugu varsayima birakilmadi:
tools/parite-test.js (referansi index.html'in GERCEK kodu olan test) bu ciktiyla
uretilmis D1 indeksini sitenin sonucuyla karsilastirir — burada bir harf kaysa
test kirmizi yanar.
"""

import hashlib
import json

_HARF = str.maketrans({
    "ı": "i", "ç": "c", "ğ": "g", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i",
})


def norm(s):
    """index.html norm() ile birebir ayni ciktiyi verir."""
    if not s:
        return ""
    # toLocaleLowerCase("tr") taklidi: I -> ı, İ -> i (lower()'dan ONCE)
    s = s.replace("İ", "i").replace("I", "ı")
    return s.lower().translate(_HARF)


def haystack(u):
    """Urunun aranabilir metni — index.html haystack() ile birebir ayni."""
    return norm(" ".join([
        u.get("baslik") or "",
        u.get("aciklama") or "",
        " ".join(u.get("marka") or []),
        u.get("kategori") or "",
        (u.get("id") or "").replace("-", " "),
    ]))


def tokenlar(q):
    """Sorguyu index.html ile ayni sekilde parcalara ayirir (bosluga gore)."""
    return [t for t in norm(q).split() if t]


def esles(hs, tokens):
    """filtered() ile ayni: HER token, arama metninin ALT-DIZESI olmali."""
    return all(t in hs for t in tokens)


# D1'e yazilan alanlar — biri degisirse satir yeniden yazilir, degismezse yazilmaz.
# (D1 gunluk 100.000 yazma limiti: tam rebuild yerine sadece degiseni yazmak sart.)
def urun_hash(u):
    ozet = json.dumps([
        u.get("id") or "",
        u.get("baslik") or "",
        u.get("kategori") or "",
        u.get("marka") or [],
        u.get("fiyat") or "",
        (u.get("gorseller") or [None])[0],
        bool(u.get("parametrik")),
        haystack(u),
    ], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(ozet.encode("utf-8")).hexdigest()[:16]
