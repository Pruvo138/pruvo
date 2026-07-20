# -*- coding: utf-8 -*-
"""PRUVO filament referansi ORTAK yardimcilari — tek kaynak: tools/filamentler.json.

Kullananlar: tools/build.py (urun sayfasi cipleri + /filament-veri.js), tools/sayfalar.py
(/malzeme-rehberi/), ekleme scriptleri (urun-ekle.py / printables-ekle.py: sanitize edilmis
tavsiyeFilament override'i) ve tools/ege-malzeme.py (ege-bilgi.md MALZEME bolumu).

MIMARI ILKE: filament bilgisi URUN VERISINE YAZILMAZ — kural render aninda kategoriden
turetilir. Tek istisna, YENI urunlerde ekleme scriptinin koyabildigi opsiyonel
"tavsiyeFilament" override alani (mevcut urunlerde tek tek tools/duzelt.py).
"""
import json
import os
import re

_YOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "filamentler.json")
_ref = None


def referans():
    """filamentler.json'u okur (surec basina bir kez)."""
    global _ref
    if _ref is None:
        with open(_YOL, encoding="utf-8") as f:
            _ref = json.load(f)
    return _ref


# GECMIS: katalogda 2 urunde kategori "Bahce" (ç'siz) yaziyordu (kaynak: AI icerik adiminin
# ASCII kategori listesi). Veri duzeltildi ve kaynak kapatildi (thing-codex.py normalize eder,
# tools/kategori-kapisi.py dogrular) — burasi yalnizca OKUMA tarafinda geriye donuk toleranstir;
# yeni ASCII kategori beklenmiyor, urun verisine dokunulmaz.
_KATEGORI_ALIAS = {"Bahce": "Bahçe"}


def tavsiyeler(kategori, override=None):
    """Urunun tavsiye listesi: [{"ad": <kanonik ad>, "rozet": <rozet metni>}, ...].

    override (urunler.json'daki opsiyonel "tavsiyeFilament") varsa harita yerine O gecer;
    referans disindaki adlar sessizce atilir. Haritada ilk kayit varsayilan tavsiyedir
    ("Tavsiyemiz"); sonrakiler kosul notuyla ("Güneş gören parçada" vb.) rozetlenir.
    SADECE SITEDE SATILAN ("site": true) malzemeler tavsiye edilir — ABS/Karbon Katkılı
    mühendislik malzemesi olup WhatsApp özel talebiyle satılır, rozetle "Tavsiyemiz"
    diye SUNULMAZ (Okan, 16 Tem).
    """
    ref = referans()
    site_adlar = {f["ad"] for f in ref["filamentler"] if f.get("site")}
    if override:
        return [{"ad": a, "rozet": "Tavsiyemiz"} for a in override if a in site_adlar]
    kategori = _KATEGORI_ALIAS.get(kategori, kategori)
    out = []
    for t in ref["kategoriTavsiye"].get(kategori, []):
        if t["ad"] not in site_adlar:
            continue
        out.append({"ad": t["ad"],
                    "rozet": "Tavsiyemiz" if not out else (t.get("not") or "Tavsiyemiz")})
    return out


# ------------------------------------------------------------- baski -> override sanitize
# Kaynak aciklamasindan gelen `baski` ipucundan SADECE kanonik malzeme adi cikarilir;
# serbest metin, tasarimci adi ya da kaynak izi URUNE TASINMAZ (gizlilik kurali).
_MALZEME_PAT = [
    ("PETG", re.compile(r"\bPETG\b|\bPCTG\b", re.I)),
    ("ASA", re.compile(r"\bASA\b", re.I)),
    ("ABS", re.compile(r"\bABS\b", re.I)),
    ("PLA", re.compile(r"\bPLA\b|\bPLA\+", re.I)),
    ("Karbon Katkılı",
     re.compile(r"(carbon|karbon)[\s-]*(fiber|fibre|fibr|elyaf|katk)|"
                r"\b(PETG|PA|PLA)[\s-]?CF\b", re.I)),
]
# Olumsuz cumlecik: icindeki malzeme anilmalari TAVSIYE DEGILDIR ("PLA is not suitable...").
_OLUMSUZ = re.compile(r"\bnot\b|\bno\b|\bavoid\b|\bnever\b|don'?t|do not|isn'?t|won'?t|"
                      r"instead of|de[gğ]il|[oö]nerilmez|kullanmay|uygun olma|olmaz|yerine",
                      re.I)


def tavsiye_filament(baski_metni):
    """`.urun-kaynaklari.json` `baski` ipucundan sanitize tavsiyeFilament listesi.

    Cumleciklere bolup olumsuz baglamdakileri eler, kalanlarda kanonik malzeme adi arar.
    Ornek: "PLA is not a suitable material; I recommend PETG." -> ["PETG"].
    Kanonik ad bulunamazsa None (override yazilmaz, kategori haritasi gecerli kalir).
    SADECE SITEDE SATILAN malzemeler override olarak yazilir — kaynak metni "ABS" ya da
    "karbon" dese bile (mühendislik malzemesi, WhatsApp özel talebi; site secilebilir
    degil) None doner, kategori haritasi gecerli kalir.
    """
    if not baski_metni:
        return None
    site_adlar = {f["ad"] for f in referans()["filamentler"] if f.get("site")}
    bulunan = []
    for parca in re.split(r"[.;!?\n]+", baski_metni):
        if _OLUMSUZ.search(parca):
            continue
        for ad, pat in _MALZEME_PAT:
            if ad in site_adlar and ad not in bulunan and pat.search(parca):
                bulunan.append(ad)
    return bulunan or None


if __name__ == "__main__":
    ornek = ("PLA is not a suitable material since cars reach high temperatures; "
             "I personally recommend using PETG. Print with 20% infill.")
    print(tavsiye_filament(ornek))                  # ['PETG']
    print(tavsiyeler("Otomobil"))                   # PETG (Tavsiyemiz) + ASA (not)
    print(tavsiyeler("Ev", override=["ASA"]))       # override kazanir
