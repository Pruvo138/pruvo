#!/usr/bin/env python3
"""LISANS CAPRAZ OLCUMU — katalogdaki `lisans.tur`, hasat havuzlarindaki OTORITER
lisans degeriyle karsilastirilir (salt okuma; hicbir sey YAZMAZ).

NEDEN VAR (8 Eyl 2026, KraL): hasat mekanik betiklerindeki `lisans_normalize()`
"sharealike"/"noncommercial" desenlerini BITISIK ariyordu; Thingiverse API bosluklu
donuyor ("Creative Commons - Attribution - Share Alike") -> sinif CC-BY'ye dusuyordu.
Ilk kosumda 237 CC-BY-SA + 6 CC-BY-ND kaydi yanlis beyanla yayindaydi (duzeltildi,
merge `fdccc54d`). KAYNAK hata MaCiT'in duzleminde ACIK (defter K387) — yani yeni
dilimler ayni hatayi yeniden uretebilir; bu arac onu SAYIYLA yakalar.

ZINCIR (ucu de ayri duzlem, anahtarlari FARKLI — karistirilirsa olcum SESSIZCE bosalir):
  1. `pruvo-hasat/**/hasat-*-havuz.json` -> `adaylar[].id` (thing id) + `.lisans` (OTORITER ham metin)
  2. `pruvo/.urun-kaynaklari.json`       -> anahtar = urun id, `link` icinde `thing:<id>`
  3. `pruvo/urunler.json`                -> kayit anahtari **`id`** (`slug` DEGIL!), `lisans.tur`
🔴 2. ve 3. adimda anahtar yanlis secilirse kova SIFIR basar ve "risk yok" sanilir
([[eslesme-anahtari-yanlissa-sifir-bulgu-yesil-sanilir]]) — bu yuzden arac KAPSAM
SAYILARINI (esli / canli) bulgudan ONCE basar; canli sayi absurt kucukse bulgu OKUNMAZ.
🔴 Kisa jetonlar (sa/nc/nd/by) ALT-DIZGE olarak aranmaz, JETON olarak aranir: `" sa"`
kolu `"satin-alma"` degerini CC-BY-SA diye siniflandirip 4 sahte vaka uretmisti.

KOVALAR
  A-NC-SATILAMAZ      otoriter NC, bizde degil -> CLAUDE.md "CC ...-NC SATMA" ihlali (EN AGIR)
  A2-ND-BEYAN-YANLIS  otoriter ND, bizde degil -> BY-ND satilabilir ama BEYAN yanlis
  C-SA-KACIRMA        otoriter CC-BY-SA, bizde CC-BY/bos -> ShareAlike sarti beyan EDILMIYOR
  B-ATIF-BORCU        otoriter CC-BY, bizde bos -> atif gorunmuyor ([[lisans-atifi-cc]])
  D-CC0               otoriter CC0 -> CC0 atif ISTEMEZ, risk YOK (bilgi kalemi)
  G-BIZIM-BILINMEYEN  bizim deger CC disi ('kisisel'/'uyelik') -> karsilastirilamaz
  F-OTORITER-CELISKILI ayni tid'e IKI farkli havuz degeri -> hangisi otoriter OLCULEMEDI
  E-DIGER             yukaridakilerin disi

KULLANIM
  python3 tools/lisans-capraz-olcum.py                 # ozet + kovalar (stdout)
  python3 tools/lisans-capraz-olcum.py --detay         # her kovanin ilk 120 kaydi
  python3 tools/lisans-capraz-olcum.py --duzelt-listesi /tam/yol.json
        A + A2 + C kovalarini `duzelt.py --toplu` semasinda YAZAR (tek cikti dosyasi;
        `lisans` objesi KOMPLE yazilir, `lisans.tasarimci` = ATIF aynen korunur).
CIKIS: rc=0 daima (bu bir OLCUM aracidir, kapi DEGIL — kapiya cevrilirse esik/mutant
       ayrica yazilir; simdiki hali "sayiyi bas, hukmu mimar versin").
"""
import argparse
import glob
import json
import os
import re
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HASAT = os.path.join(os.path.dirname(KOK), "pruvo-hasat")

# sinif -> katalogda yazilacak KANONIK metin
KANON = {"CC-BY": "CC BY 4.0", "CC-BY-SA": "CC BY-SA 4.0", "CC-ND": "CC BY-ND 4.0",
         "CC0": "CC0", "CC-NC": "CC BY-NC 4.0", "CC-NC-SA": "CC BY-NC-SA 4.0",
         "CC-NC-ND": "CC BY-NC-ND 4.0", "GPL": "GPL", "BSD": "BSD"}
SATILAMAZ = ("CC-NC", "CC-NC-SA", "CC-NC-ND")


def jetonlar(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split()


def sinif(ham):
    """Ham lisans metnini kanonik sinifa indirger. Kisa jetonlar JETON olarak aranir."""
    j = jetonlar(ham)
    s = " ".join(j)
    if not s:
        return ""
    if "cc0" in j or "public domain" in s or j == ["pd"]:
        return "CC0"
    nc = ("noncommercial" in j) or ("non commercial" in s) or ("nc" in j)
    nd = ("noderivatives" in j) or ("noderiv" in s) or ("no derivatives" in s) or ("nd" in j)
    sa = ("sharealike" in j) or ("share alike" in s) or ("sa" in j)
    if "gpl" in s or "gnu" in j:
        return "GPL"
    if "bsd" in j:
        return "BSD"
    if "all rights reserved" in s:
        return "TELIF"
    if nc and nd:
        return "CC-NC-ND"
    if nc and sa:
        return "CC-NC-SA"
    if nc:
        return "CC-NC"
    if nd:
        return "CC-ND"
    if sa:
        return "CC-BY-SA"
    if "attribution" in j or "by" in j or "cc" in j or "creative" in j:
        return "CC-BY"
    return "BILINMEYEN"


def havuz_lut():
    """thing id -> OTORITER ham lisans degerleri KUMESI (celiski gorunur kalsin diye kume)."""
    lut = {}
    dosya = 0
    for kok in (HASAT, os.path.join(HASAT, ".claude", "worktrees")):
        for d in glob.glob(os.path.join(kok, "**", "hasat-*-havuz.json"), recursive=True):
            try:
                j = json.load(open(d, encoding="utf-8"))
            except (OSError, ValueError):
                continue
            ad = j.get("adaylar") if isinstance(j, dict) else None
            if not isinstance(ad, list):
                continue
            dosya += 1
            for a in ad:
                if isinstance(a, dict) and a.get("id") and a.get("lisans"):
                    lut.setdefault(str(a["id"]).strip(), set()).add(a["lisans"])
    return lut, dosya


def kova_sec(bizim, beklenen):
    if beklenen in SATILAMAZ and bizim not in SATILAMAZ:
        return "A-NC-SATILAMAZ"
    if beklenen == "CC-ND" and bizim != "CC-ND":
        return "A2-ND-BEYAN-YANLIS"
    if beklenen == "CC-BY-SA" and bizim in ("CC-BY", ""):
        return "C-SA-KACIRMA"
    if beklenen == "CC-BY" and bizim == "":
        return "B-ATIF-BORCU"
    if beklenen == "CC0":
        return "D-CC0(risk yok)"
    if bizim == "BILINMEYEN":
        return "G-BIZIM-BILINMEYEN"
    return "E-DIGER"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detay", action="store_true", help="her kovanin ilk 120 kaydini bas")
    ap.add_argument("--duzelt-listesi", metavar="JSON",
                    help="A+A2+C kovalarini duzelt.py --toplu semasinda bu dosyaya yaz")
    a = ap.parse_args()

    lut, havuz_dosya = havuz_lut()
    if not lut:
        print("OLCULEMEDI: hasat havuzu bulunamadi (%s)" % HASAT)
        return 0
    kaynaklar = json.load(open(os.path.join(KOK, ".urun-kaynaklari.json"), encoding="utf-8"))
    urunler = json.load(open(os.path.join(KOK, "urunler.json"), encoding="utf-8"))
    kat = {u["id"]: u for u in urunler if u.get("id")}          # 🔴 anahtar `id`

    kovalar, duzelt = {}, []
    esli = canli = uyusan = 0
    for uid, k in kaynaklar.items():
        m = re.search(r"thing:(\d+)", k.get("link") or "")
        if not m:
            continue
        kume = lut.get(m.group(1))
        if not kume:
            continue
        esli += 1
        u = kat.get(uid)
        if not u:
            continue
        canli += 1
        siniflar = set(sinif(x) for x in kume)
        lis = u.get("lisans")
        bizim_ham = (lis.get("tur") if isinstance(lis, dict) else (lis or "")) or ""
        bizim = sinif(bizim_ham)
        if len(siniflar) > 1:
            kovalar.setdefault("F-OTORITER-CELISKILI", []).append(
                (uid, m.group(1), bizim_ham, bizim, " | ".join(sorted(kume)),
                 "/".join(sorted(siniflar))))
            continue
        beklenen = list(siniflar)[0]
        otoriter_ham = sorted(kume)[0]
        if bizim == beklenen:
            uyusan += 1
            continue
        kv = kova_sec(bizim, beklenen)
        kovalar.setdefault(kv, []).append((uid, m.group(1), bizim_ham, bizim,
                                           otoriter_ham, beklenen))
        if kv in ("A-NC-SATILAMAZ", "A2-ND-BEYAN-YANLIS", "C-SA-KACIRMA") and beklenen in KANON:
            yeni = dict(lis) if isinstance(lis, dict) else ({"tur": lis} if lis else {})
            yeni["tur"] = KANON[beklenen]
            duzelt.append({"id": uid, "alan": "lisans", "deger": yeni,
                           "not": "lisans capraz olcumu: havuz otoriter %r -> %s (%s)"
                                  % (otoriter_ham, beklenen, kv)})

    # 🔴 KAPSAM ONCE: canli sayi absurt kucukse ASAGIDAKI BULGU OKUNMAZ (anahtar hatasi).
    print("KAPSAM  havuz dosyasi=%d · otoriter tid=%d · thing linkli kaynak kaydi=%d "
          "-> CANLI katalogda=%d" % (havuz_dosya, len(lut), esli, canli))
    print("UYUSAN  %d · UYUSMAYAN %d" % (uyusan, canli - uyusan))
    print("KOVALAR:")
    for kv in sorted(kovalar):
        isaret = "   <<< SATILAMAZ" if kv == "A-NC-SATILAMAZ" else ""
        print("  %-24s %5d%s" % (kv, len(kovalar[kv]), isaret))
    if a.detay:
        for kv in sorted(kovalar):
            print("\n=== %s (%d) ===" % (kv, len(kovalar[kv])))
            for r in kovalar[kv][:120]:
                print("  %s | tid=%s | bizim=%r(%s) | otoriter=%r(%s)" % r)
            if len(kovalar[kv]) > 120:
                print("  ... +%d" % (len(kovalar[kv]) - 120))
    if a.duzelt_listesi:
        json.dump(duzelt, open(a.duzelt_listesi, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("DUZELT LISTESI: %s (%d islem — `duzelt.py --toplu` ile uygulanir)"
              % (a.duzelt_listesi, len(duzelt)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
