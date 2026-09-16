#!/usr/bin/env python3
"""K161-ifsa cumle-duzey DIL DENETIMI (deterministik, AI yok).

islemler.json'daki her islem icin eski metin (urunler.json, jq) ile yeni metni
karsilastirir; bulgu turleri:

  BOSLUKSUZ_NOKTA       - [a-zçğıöşü]\\.[A-ZÇĞİÖŞÜ] (nokta ile bitisik buyuk harf)
  KUCUK_HARF_CUMLE_BASI - \\. [a-zçğıöşü] (nokta+space+alt-kucuk harf)
  KOK_TEKRARI           - ayni >=5 harfli kelime 6-kelime penceresinde 2 kez,
                          eski metinde YOKSA (yeni ile gelen tekrar = plansiz)
  CIFT_FIIL             - cumle icinde iki -ilir/-ılır/-ülür/-ulur cekimli fiil
                          noktasiz ARDISIK (veya bir-iki yardimci kelime aralikli)
  SUREC_KALINTISI       - ekstruder/nozul/katman/dolgu/dilimleyici/filament/baski
                          /basil/print kok(ler)i yeni metinde
  DEGISMEYEN            - yeni == eski (degisim yok)

Cikti:
  DIL_BULGU=<n>
  tür kirilimi (ornek: BOSLUKSUZ_NOKTA: 4, KUCUK_HARF_CUMLE_BASI: 51, ...)
  bulgu>0 -> rc=1, degilse rc=0.

Kullanim:
  python3 tools/k161/dil-denetimi.py <islemler.json> [--eski-kok /path/urunler.json]
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

# Sabit Turkce kucuk harfler (ASCII disi)
_TR_KUCUK = "a-zçğıöşü"
_TR_BUYUK = "A-ZÇĞİÖŞÜ"

# 1) BOSLUKSUZ_NOKTA: bir kucuk harfin hemen ardindan nokta ve buyuk harf
RE_BOSLUKSUZ_NOKTA = re.compile(rf"[{_TR_KUCUK}]\.[{_TR_BUYUK}]")

# 2) KUCUK_HARF_CUMLE_BASI: nokta + bosluk + alt kucuk harf (TR disi)
RE_KUCUK_HARF_CUMLE_BASI = re.compile(rf"\. [{_TR_KUCUK}]")

# 3) SUREC_KALINTISI: surec ile ilgili koklerden biri yeni metinde
_RE_SUREC_KOKLERI = (
    r"\bekstruder\w*\b", r"\bekstruzyon\w*\b",
    r"\bnoz[uü]l\w*\b", r"\bkatman\w*\b",
    r"\bdolgu\w*\b", r"\bdoluluk\w*\b",
    r"\bdilimleyici\w*\b", r"\bslicer\w*\b",
    r"\bprusaslicer\w*\b", r"\borcaslicer\w*\b",
    r"\bsuperslicer\w*\b", r"\bideamaker\w*\b",
    r"\bsimplify3d\w*\b", r"\bbambu\s*studio\w*\b",
    r"\bfilaman\w*\b", r"\bfilament\w*\b",
    r"\bspool\w*\b", r"\bhotend\w*\b",
    r"\bheatsink\w*\b", r"\boctoprint\w*\b",
    r"\b3\s*[db]\s*bask[ıi]\w*\b", r"\b3\s*boyutlu\s*bask[ıi]\w*\b",
    r"\b3d\s*print\w*\b", r"\bgcode\w*\b",
    r"\bg-code\w*\b", r"\b3mf\w*\b",
    r"\bstl\b", r"\bf3d\w*\b", r"\bstp\w*\b",
    r"\bfdm\b", r"\binfill\b",
    # 'baski' / 'basil-' buyuk-daraltilmis: kapi_ifsa desenlerinin TAM listesi degil,
    # sadece kok olarak her iki dilde (TR + ASCII) yakalanir.
    r"\bbask[ıi]\w*\b",  # baski/baskisi/baskiya/baskidan/baskinin/baskinin...
    r"\bbas[ıi]l\w*\b",  # basil-/basildi/basilir/basilmasi
    r"\bprint\w*\b",     # print/printed/printing
)
RE_SUREC_KALINTISI = re.compile(
    "|".join(_RE_SUREC_KOKLERI), re.UNICODE)

# 4) CIFT_FIIL: cumle icinde 2 cekimli fiil (ilir|ılır|ülür|ulur) ARDISIK
#    "ardisik" = noktasiz, aralarinda en fazla 2-3 yardimci kelime olabilir
_CIFTFIIL_FIIL_RE = re.compile(
    r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+(?:ilir|ılır|ülür|ulur)")
_CIFTFIIL_ARA_RE = re.compile(
    r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+(?:ilir|ılır|ülür|ulur)"
    r"(?:\s+(?:[a-zA-ZçğıöşüÇĞİÖŞÜ]+)){0,3}"
    r"\s+[a-zA-ZçğıöşüÇĞİÖŞÜ]+(?:ilir|ılır|ülür|ulur)")

# 5) KOK_TEKRARI: ayni >=5 harfli kelime 6-kelime penceresinde 2 kez (case-insensitive)
_KOK_TEKRARI_PENCERE = 6
_KOK_TEKRARI_MIN_LEN = 5
_KELIME_RE = re.compile(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+")

# ONEMLI: dil-denetimi sadece YENI METIN uzerinde degil; ESKI-YENI FARKI uzerinde
# calismali. "kahveyi kahveyi" eski metinde de varsa PLAN BUNU GETIRMEDI = temiz.

ESIK_DIL_BULGU = 1  # 0 farkli tipte bulgu bile -> rc=1

URUNLER = Path("/Users/okan/dev/pruvo/urunler.json")


def cumlelere_bol(metin: str) -> list[str]:
    """_CUMLE_SON_RE benzeri basit bir cumle bolucusu. Olcu satiri
    ('Yaklasik dis olculer:') kendi cumlesinde DOKUNULMAZ yine de ayni sekilde
    dil denetiminden gecirilir (bu aracin isi 'cumle bazli' DEGIL)."""
    return [c.strip() for c in re.split(r"[.!?\n;]", metin) if c.strip()]


def kok_tekrari_varmi(text: str) -> list[tuple[str, int, int]]:
    """Ayni >=5 harfli kelime 6-kelime penceresinde 2 kez; kelime indeksleri."""
    kelimeler = _KELIME_RE.findall(text)
    bulgular = []
    for i in range(len(kelimeler)):
        for j in range(i + 1, min(i + _KOK_TEKRARI_PENCERE, len(kelimeler))):
            w1 = kelimeler[i]
            w2 = kelimeler[j]
            if (len(w1) >= _KOK_TEKRARI_MIN_LEN
                    and w1.lower() == w2.lower()):
                bulgular.append((w1, i, j))
    return bulgular


def yeni_kok_tekrari(eski: str, yeni: str) -> list[tuple[str, int, int]]:
    """Eski metinde OLMAYAN, yeni metinde olan kok tekrarlari."""
    eski_set = {w.lower() for w in _KELIME_RE.findall(eski)
                if len(w) >= _KOK_TEKRARI_MIN_LEN}
    bulgular = []
    for kelime, i, j in kok_tekrari_varmi(yeni):
        if kelime.lower() not in eski_set:
            bulgular.append((kelime, i, j))
    return bulgular


def cift_fiil_var_mi(text: str) -> list[str]:
    """Cumle icinde iki -ilir/-ılır/-ülür/-ulur cekimli fiil noktasiz ardisik."""
    bulgular = []
    for cumle in cumlelere_bol(text):
        if not cumle:
            continue
        for m in _CIFTFIIL_ARA_RE.finditer(cumle):
            bulgular.append(m.group(0))
    return bulgular


def surec_kalintisi(text: str) -> list[str]:
    return [m.group(0) for m in RE_SUREC_KALINTISI.finditer(text)]


def eski_yukle(id_index: dict, uid: str) -> str:
    rec = id_index.get(uid)
    if not isinstance(rec, dict):
        return ""
    return str(rec.get("aciklama", "") or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("islemler", help="islemler.json (duzelt.py --toplu bicimi)")
    ap.add_argument("--eski-kok", default=str(URUNLER),
                    help="eski metni okumak icin urunler.json yolu")
    ap.add_argument("--id-alani", default="id",
                    help="islem kaydindaki id alani adi")
    ap.add_argument("--deger-alani", default="deger",
                    help="islem kaydindaki yeni metin alani adi")
    args = ap.parse_args()

    islemler_path = Path(args.islemler)
    if not islemler_path.exists():
        print(f"HATA: {islemler_path} bulunamadi", file=sys.stderr)
        return 4

    with open(islemler_path, encoding="utf-8") as f:
        islemler_doc = json.load(f)
    islemler = islemler_doc.get("islemler") or []
    if not isinstance(islemler, list):
        print("HATA: islemler.json 'islemler' alani liste degil", file=sys.stderr)
        return 4

    eski_path = Path(args.eski_kok)
    if not eski_path.exists():
        print(f"HATA: eski kok {eski_path} bulunamadi", file=sys.stderr)
        return 4
    with open(eski_path, encoding="utf-8") as f:
        urunler = json.load(f)
    id_index = {u.get("id"): u for u in urunler if isinstance(u, dict)}

    bulgu_sayac = {
        "BOSLUKSUZ_NOKTA": 0,
        "KUCUK_HARF_CUMLE_BASI": 0,
        "KOK_TEKRARI": 0,
        "CIFT_FIIL": 0,
        "SUREC_KALINTISI": 0,
        "DEGISMEYEN": 0,
    }
    ornekler = {k: [] for k in bulgu_sayac}   # her tipten ilk 3 ornek

    for op in islemler:
        if not isinstance(op, dict):
            continue
        uid = op.get(args.id_alani)
        yeni = op.get(args.deger_alani)
        if not isinstance(uid, str) or not isinstance(yeni, str):
            continue
        eski = eski_yukle(id_index, uid)

        if yeni == eski:
            bulgu_sayac["DEGISMEYEN"] += 1
            if len(ornekler["DEGISMEYEN"]) < 3:
                ornekler["DEGISMEYEN"].append((uid, "yeni == eski"))
            continue

        # 1) BOSLUKSUZ_NOKTA
        for m in RE_BOSLUKSUZ_NOKTA.finditer(yeni):
            bulgu_sayac["BOSLUKSUZ_NOKTA"] += 1
            if len(ornekler["BOSLUKSUZ_NOKTA"]) < 3:
                ornekler["BOSLUKSUZ_NOKTA"].append(
                    (uid, m.group(0), m.start()))

        # 2) KUCUK_HARF_CUMLE_BASI
        for m in RE_KUCUK_HARF_CUMLE_BASI.finditer(yeni):
            bulgu_sayac["KUCUK_HARF_CUMLE_BASI"] += 1
            if len(ornekler["KUCUK_HARF_CUMLE_BASI"]) < 3:
                ornekler["KUCUK_HARF_CUMLE_BASI"].append(
                    (uid, m.group(0), m.start()))

        # 3) KOK_TEKRARI (sadece yeni ile gelen)
        for kelime, i, j in yeni_kok_tekrari(eski, yeni):
            bulgu_sayac["KOK_TEKRARI"] += 1
            if len(ornekler["KOK_TEKRARI"]) < 3:
                ornekler["KOK_TEKRARI"].append(
                    (uid, f"{kelime} (idx {i},{j})", None))

        # 4) CIFT_FIIL
        for ardisik in cift_fiil_var_mi(yeni):
            bulgu_sayac["CIFT_FIIL"] += 1
            if len(ornekler["CIFT_FIIL"]) < 3:
                ornekler["CIFT_FIIL"].append((uid, ardisik, None))

        # 5) SUREC_KALINTISI
        for ifade in surec_kalintisi(yeni):
            bulgu_sayac["SUREC_KALINTISI"] += 1
            if len(ornekler["SUREC_KALINTISI"]) < 3:
                ornekler["SUREC_KALINTISI"].append(
                    (uid, ifade, None))

    toplam = sum(bulgu_sayac.values())
    print(f"islemler.json: {len(islemler)} kayit")
    print(f"DIL_BULGU={toplam}")
    for tip, n in bulgu_sayac.items():
        print(f"  {tip}: {n}")
    if toplam > 0:
        print("\nornekler (ilk 3):")
        for tip, lst in ornekler.items():
            for u, *rest in lst:
                print(f"  [{tip}] {u}: {rest}")
    return 1 if toplam >= ESIK_DIL_BULGU else 0


if __name__ == "__main__":
    sys.exit(main())