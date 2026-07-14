#!/usr/bin/env python3
"""Kaynak (Thingiverse/Printables) aciklamasindan FILAMENT + BASKI onerisi cumlelerini cikarir.

DAHILI not icindir — `.urun-kaynaklari.json`'daki `baski` alanina yazilir, sitede GORUNMEZ.
Amac: siparis gelince deneme-yanilma yapmadan dogru malzeme/ayarla basmak.

Kullanim (import):  from baski_ipucu import baski_ipucu   (ya da importlib ile)
    baski_ipucu(aciklama_metni) -> kisa Turkce/Ingilizce ozet string (yoksa "").
"""
import re

# Malzeme adlari (tam kelime) — bunlari iceren cumle neredeyse her zaman baski onerisidir.
_MAT = re.compile(r"\b(PETG|PLA\+?|ABS|ASA|TPU|TPE|PCTG|nylon|naylon|polycarbonate|"
                  r"re[cç]ine|carbon\s?fiber|karbon\s?fiber|wood\s?fill|filament)\b", re.I)
# Guclu baski-ayari ifadeleri (malzeme gecmese de baski onerisi sayilir). NET baski-baglami;
# tek basina "support"/"wall"/"mm" gibi gurultuyu TETIKLEMEZ (urun aciklamasi degil, ayar).
_SET = re.compile(r"(layer\s*height|katman\s*y[uü]ksek|infill|dolgu|perimeter|perimetre|"
                  r"wall\s*(line|loop|count)|duvar\s*say|nozzle|nozul|\bbrim\b|\braft\b|"
                  r"heat[-\s]*resist|[ıi]s[ıi]ya?\s*dayan|flexible\s+(material|filament)|"
                  r"esnek\s+(malzeme|filament)|\b\d{2,3}\s?[°º]\s?C\b|"
                  r"\d{1,3}\s?%\s?(infill|dolgu)|\d(\.\d+)?\s?mm\s*(nozzle|layer))", re.I)
# Destek: yalnizca BASKI baglaminda ("no/without/needs support", "support needed/free",
# "destek gerekir/yok"). "drum support" gibi urun-ismini tetiklemez.
_SUP = re.compile(r"((no|without|needs?|require[sd]?|minimal|hardly\s+any|some|with|w/)\s+supports?\b|"
                  r"supports?\s+(needed|required|material|free|are\s+needed|not\s+needed)|"
                  r"destek\s*(gerek\w*|yok|var|olmadan|istemez)|(without|no)\s+destek|"
                  r"print(ed)?\s+without\s+support)", re.I)
# Gurultu: cok kisa ya da alakasiz. Malzeme/ayar eslesse de bunlari atla.
_GURULTU = re.compile(r"(license|thingiverse|printables|remix|please\s+(like|rate)|patreon|"
                      r"follow me|instagram|youtube|appreciate|motivat|thank|donation|"
                      r"buy me|coffee|te[sş]ekk[uü]r|publishing new)", re.I)


def _strip_html(s):
    s = re.sub(r"<br\s*/?>", "\n", s or "", flags=re.I)
    s = re.sub(r"</p>|</li>|</div>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'")
           .replace("&quot;", '"').replace("&gt;", ">").replace("&lt;", "<"))
    return s


def baski_ipucu(text, max_len=400, max_cumle=3):
    """Aciklamadan filament/baski onerisi cumlelerini sec, tek string dondur (dahili not)."""
    if not text:
        return ""
    t = _strip_html(text)
    # Cumle/satir parcalarina ayir
    segs = re.split(r"(?<=[.!?])\s+|\n+", t)
    hits = []
    for s in segs:
        s = " ".join(s.split())          # ic bosluklari sadelestir
        if len(s) < 8 or len(s) > 260:
            continue
        if _GURULTu_var(s):
            continue
        if _MAT.search(s) or _SET.search(s) or _SUP.search(s):
            if s not in hits:
                hits.append(s)
        if len(hits) >= max_cumle:
            break
    out = " ".join(hits).strip()
    return out[:max_len].rsplit(" ", 1)[0] if len(out) > max_len else out


def _GURULTu_var(s):
    return bool(_GURULTU.search(s))


if __name__ == "__main__":
    ornek = ("Small trash bin for your car. PLA is not a suitable material since cars reach "
             "high temperatures; I personally recommend using PETG. Print with 3 perimeters and "
             "20% infill, no supports needed. Please like and rate! Follow me on Instagram.")
    print(repr(baski_ipucu(ornek)))
