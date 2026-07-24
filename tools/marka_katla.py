#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""markaKatla / markaNorm / taninmisMarkaMi PORTU (Python) — index.html'deki
MARKA KÜRATÖRLÜĞÜ bloğunun BİREBİR karşılığı.

TEK KAYNAK: TANINMIS_MARKALAR listesi index.html'den PARSE edilir (kopya tutulmaz).
Panel/CSV/kapsama raporu satır evrenini ham defter anahtarları yerine bu kanonik
listeden alır; ham defterdeki tüm anahtarların sayımları markaKatla ile kanonik
markaya katlanır (tanınmayan çöp anahtar hiç görünmez).

Site (index.html) ile senkron TUTULMASI gereken tek yer markaNorm gövdesi ve
markaKatla önek kuralıdır — ikisi de aşağıda birebir yansıtıldı. marka-panel-test.py
sabit vaka tablosuyla bu tutarlılığı MUTASYON-KANITLI kilitler.
"""
import os
import re

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
INDEX = os.path.join(ROOT, "index.html")


def _norm(s):
    """index.html norm(): Türkçe-duyarlı küçültme + aksan sadeleştirme."""
    s = (s or "").lower()
    # Türkçe locale lowercase: İ ve I ele; norm() önce toLocaleLowerCase("tr") yapıyor.
    # Python lower() İ -> i̇ (combining) üretebilir; site ile birebir olması için elle eşle.
    s = (s.replace("ı", "i").replace("İ", "i")
          .replace("ç", "c").replace("ğ", "g").replace("ö", "o")
          .replace("ş", "s").replace("ü", "u").replace("â", "a").replace("î", "i"))
    return s


def markaNorm(s):
    """norm() + Latin aksan ("Citroën"->"citroen") + marka ayıraç birleştirme.
    "+", "&", " and " tek biçime indirgenir -> "Black+Decker" == "Black and Decker"."""
    n = _norm(s)
    n = n.replace("é", "e").replace("è", "e").replace("ë", "e").replace("ä", "a")
    # marka ayıraç kanonikleştirme (site markaNorm ile birebir tutulur):
    n = n.replace(" and ", " ").replace("&", " ").replace("+", " ")
    n = re.sub(r"\s+", " ", n).strip()
    return n


def _parse_taninmis(index_path=INDEX):
    """index.html'den TANINMIS_MARKALAR dizisini PARSE et (tek kaynak)."""
    src = open(index_path, encoding="utf-8").read()
    m = re.search(r"var TANINMIS_MARKALAR = \[(.*?)\];", src, re.S)
    if not m:
        raise RuntimeError("TANINMIS_MARKALAR index.html'de bulunamadı")
    body = m.group(1)
    # yorum satırlarını (// ...) at, sonra tırnaklı stringleri topla
    body = re.sub(r"//[^\n]*", "", body)
    return re.findall(r'"([^"]+)"', body)


TANINMIS_MARKALAR = _parse_taninmis()
MARKA_KANONIK = {}
for _m in TANINMIS_MARKALAR:
    MARKA_KANONIK[markaNorm(_m)] = _m
MARKA_NORMLU = [markaNorm(m) for m in TANINMIS_MARKALAR]


def markaKatla(m):
    """Değer tanınmış markanın kendisiyse ya da boşluk/tire ile önekliyse o markanın
    kanonik adına katlanır; değilse OLDUĞU GİBİ döner (site markaKatla birebir)."""
    n = markaNorm(m)
    if n in MARKA_KANONIK:
        return MARKA_KANONIK[n]
    for i, nm in enumerate(MARKA_NORMLU):
        if n.startswith(nm + " ") or n.startswith(nm + "-"):
            return TANINMIS_MARKALAR[i]
    return m


def taninmisMarkaMi(m):
    return markaNorm(m) in MARKA_KANONIK


def kanonik_veya_none(m):
    """markaKatla tanınmış bir markaya katladıysa kanonik adı, katlamadıysa None."""
    k = markaKatla(m)
    return k if taninmisMarkaMi(k) else None


# ---- PANEL/CSV/RAPOR ortak katmanı (satır evreni = TANINMIS_MARKALAR) ----------
PLATFORMLAR = ["Printables", "Thingiverse", "MakerWorld"]
AZ_ORAN = 0.5   # markanın en dolu platformunun bu oranının altı = "az kalmış" (sarı)
AZ_MIN = 10     # en dolu platform bu sayıdan azsa orantıya bakma (küçük markada gürültü)


def kanonik_kapsama(defter):
    """Ham defter (anahtar -> platform -> kayıt) -> kanonik marka -> platform -> BİRLEŞİK kayıt.
    Satır evreni TANINMIS_MARKALAR: defteri olmayan tanınmış marka da BOŞ girer (to-do çıkar).
    markaKatla ile hiçbir tanınmış markaya katlanmayan çöp anahtar HİÇ görünmez.
    Birleştirme: taranan=max, eklenen/elenen/parti=sum, son_tarih=en yeni."""
    agg = {m: {} for m in TANINMIS_MARKALAR}
    for ham, plats in (defter or {}).items():
        kan = kanonik_veya_none(ham)
        if kan is None:
            continue
        agg.setdefault(kan, {})
        if not isinstance(plats, dict):
            continue
        for p, k in plats.items():
            if not isinstance(k, dict):
                continue
            cur = agg[kan].setdefault(p, {"taranan": 0, "eklenen": 0, "elenen": 0,
                                          "parti": 0, "son_tarih": None})
            cur["taranan"] = max(cur["taranan"], int(k.get("taranan", 0) or 0))
            cur["eklenen"] += int(k.get("eklenen", 0) or 0)
            cur["elenen"] += int(k.get("elenen", 0) or 0)
            cur["parti"] += int(k.get("parti", 0) or 0)
            st = k.get("son_tarih")
            if st and (cur["son_tarih"] is None or str(st) > str(cur["son_tarih"])):
                cur["son_tarih"] = st
    return agg


def hucre_deger(kayit):
    """Panel hücre değeri: eklenen>0 -> eklenen | taranan>0 -> 0 (arandı-boş) | yoksa None."""
    if not kayit:
        return None
    if kayit.get("eklenen", 0) > 0:
        return kayit["eklenen"]
    if kayit.get("taranan", 0) > 0:
        return 0
    return None


def durum_hucreler(vals, platlar=None):
    """vals: {platform: int|None}. (kırmızı_platformlar, sarı_platformlar) döner.
    Hiç harvest edilmemiş tanınmış marka (tot==0) TÜM platformlarda kırmızı to-do.
    Coverage'lı markada: eksik platform kırmızı (tot>=3 ise), dengesiz platform sarı."""
    platlar = platlar or list(vals.keys())
    tot = sum(v for v in vals.values() if v)
    en = max([v for v in vals.values() if v] or [0])
    if tot == 0:
        return list(platlar), []
    kirmizi = [p for p in platlar if vals.get(p) is None] if tot >= 3 else []
    sari = ([p for p in platlar if vals.get(p) and vals[p] < en * AZ_ORAN]
            if en >= AZ_MIN else [])
    return kirmizi, sari


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        print("%s -> katla=%s taninmis=%s kanonik=%s"
              % (arg, markaKatla(arg), taninmisMarkaMi(arg), kanonik_veya_none(arg)))
