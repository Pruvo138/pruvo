#!/usr/bin/env python3
"""K161-ifsa cumle-duzey PLAN v3 (TUR 3) — YALNIZ CIKAR + SABIT SABLON.

Izinli iki islem:
  (a) ifsa/tavsiye/surec koku tasiyan parcayi METINDEN CIKAR
  (b) cikarilan parca malzeme adi tasiyorsa VE metinde henuz SABIT SABLON
      yoksa 1 SABIT SABLON cumlesi EKLE

KELIME DEGISIKLIGI YAPILMAZ (tur 2'nin temel hatasi buydu). Bu planin butun
ciktisi yapi-denetimi.py ile dogrulanir: yeni metin parcalarinin TAMAMEN
eski parcalarin alt kumesi + en fazla 1 SABIT SABLON olmasi ZORUNLU —
bir parcanin icindeki TEK harf farki bile yakalanir.

Cikti dosyalari:
  /Users/okan/.claude/cron/isci-tur-cikti/k161-ifsa/islemler.json
  /Users/okan/.claude/cron/isci-tur-cikti/k161-ifsa/ELLE.json

ELLE'ye dusen kayitlar (plana GIRMEZ):
  - toplam uzunluk <40 karakter
  - yapi-denetimi bulgusu (CIKAR sonrasi metin testi)
  - ifsa vurusu baslik/urun tanimi parcasinda
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from collections import Counter

ROOT = Path("/Users/okan/dev/pruvo")
EV = Path("/Users/okan/dev/pruvo/.claude/worktrees/k161-ifsa-plan")
DENETIM = EV / "tools" / "denetim-kapisi.py"
ISLEMLER = Path("/Users/okan/.claude/cron/isci-tur-cikti/k161-ifsa/islemler.json")
ELLE_OUT = Path("/Users/okan/.claude/cron/isci-tur-cikti/k161-ifsa/ELLE.json")
URUNLER = ROOT / "urunler.json"
RAPOR = ROOT / ".thing-cache/denetim-kapisi-rapor.json"

# === SABITLER ============================================================
_OLCU_RE = re.compile(r"\nYaklaşık dış ölçüler:[^\n]*", re.UNICODE)
_OLCU_RE_LOOSE = re.compile(r"Yaklaşık dış ölçüler:[^\n]*", re.UNICODE)

# Ayraçlar: ". ", "! ", "? " (2 byte ASCII + 0+ whitespace), "; " (semicolon + space),
# "\n" (satir sonu)
_AYRAC_RE = re.compile(r"[.!?]\s+|;\s+|\n")

# Malzeme listesi (SABLON icin)
# Malzeme BEYANI = uretim vaadi -> yalniz uretim envanterinden TURETILIR (elle liste YASAK:
# tur 3'te elle listedeki "PC" icin "PC malzemeden uretilir" yazildi; PC URETEMIYORUZ,
# memory/malzeme-envanteri-beyan-karari.md). Tek kelimelik ASCII adlar alinir.
_MALZ_LIST = [f["ad"] for f in json.loads((ROOT / "tools" / "filamentler.json").read_text(encoding="utf-8"))["filamentler"]
              if re.fullmatch(r"[A-Z]{2,5}", f.get("ad", ""))]
if not _MALZ_LIST:
    sys.exit("MALZEME_ENVANTERI_BOS: tools/filamentler.json okunamadi -> OLCULEMEDI")
SABLON_TEKIL = "|".join(re.escape(m) for m in _MALZ_LIST)
SABLON_RE = re.compile(
    rf"^(?:{SABLON_TEKIL}) malzemeden üretilir\.$|"
    rf"^(?:{SABLON_TEKIL}) veya (?:{SABLON_TEKIL}) malzemeden üretilir\.$",
    re.UNICODE,
)

# Surec/tavsiye/ifsa kokler (CIKAR tetikleyici) — denetim-kapisi desenlerinin
# TAM listesi DEGIL; sadece cumlenin "canli bilgi tasimiyor, ifsa etrafa
# olculen kalintilardan ibaret" kararini vermeye yetecek kadar.
# ONEMLI: sondaki \b YOK — "seçilmelidir" gibi cekimli haller de yakalanmali.
_IFSA_KOKLERI = [
    # ifsa vuruslari (denetim-kapisi desenlerinin en onemli subset'i)
    r"\b3\s*[db]\s*bask[ıi]", r"\b3\s*boyutlu\s*bask[ıi]", r"\b3d\s*print",
    r"\bbask[ıi]", r"\bbas[ıi]l", r"\bbas[ıi]m", r"\bbas[ıi]ma",
    r"\byazd[ıi]r", r"\bprint",
    r"\bfilaman", r"\bfilament",
    r"\bstl\b", r"\b3mf\b", r"\bgcode\b", r"\bg-code\b", r"\bf3d\b", r"\bstp\b",
    r"\binfill\b", r"\bfdm\b",
    r"\bslicer\b", r"\bdilimleyici",
    r"\bkatman", r"\bdolgu", r"\bdoluluk",
    r"\bspool\b", r"\bhotend\b", r"\bheatsink\b", r"\boctoprint\b",
    r"\bbrim\b", r"\braft\b", r"\bnoz[uü]l", r"\bextrud",
    r"\bsolidworks\b", r"\btinkercad\b", r"\bfreecad\b", r"\bopenscad\b",
    r"\bscad\b", r"\bcura\b",
    # surec kipi
    r"\bsa[ğg]lam\s+bas[ıi]l", r"\bhassas\s+bas[ıi]l",
    r"\bbas[ıi]lmas[ıi]\s+gerek", r"\bbas[ıi]lmas[ıi]\s+(?:[öo]nerilir|tavsiye)",
    # surec tavsiye (malzeme + oneri/tavsiye)
    r"\bpetg\s+[öo]neril", r"\btpu\s+[öo]neril", r"\bpla\s+[öo]neril",
    r"\bpetg\s+tavsiye", r"\btpu\s+tavsiye", r"\bpla\s+tavsiye",
    r"\babs\s+[öo]neril", r"\babs\s+tavsiye",
    # "destek" surec baglami
    r"\bdestek\s+malzeme", r"\bdesteksiz", r"\bdestek\s+gerektir",
    # genel tavsiye (ekleri yutacak kadar esnek)
    r"[öo]nerilir", r"[öo]neril", r"\btavsiye",
    r"se[çc]ilmeli", r"se[çc]ilme", r"\btercih\s+edil",
    r"kullan[ıi]lmas[ıi]", r"kullan[ıi]lmal[ıi]", r"\bgerekir\b", r"\bgerekli\b",
]
RE_IFSA_KOK = re.compile("|".join(_IFSA_KOKLERI), re.UNICODE | re.IGNORECASE)

# Parcanin CANLI (urun/kullanici/montaj) bilgi tasiyip tasimadigini anlamak
# icin CANLI kokleri.
_CANLI_KOKLERI = [
    r"\burun\b", r"\bpar[çc]a\b", r"\borijinal\b", r"\byedek\b",
    r"\bmonte\b", r"\bvid[ae]\b", r"\byap[ıi][şs]t[ıi]r\w*",
    r"\btasar[ıi]m\b", r"\bmodel\b", r"\bmarka\b",
    r"\btutamak\b", r"\btutacak\b", r"\bklips\b", r"\bkapak\b",
    r"\badapt[öo]r\b", r"\binsert\b", r"\bba[ğg]l[ıi]\b", r"\bb[ıi]le[şs]en\b",
    r"\bsap\b", r"\bmandal\b", r"\bfren\b",
    r"\bkablo\b", r"\bsens[öo]r\b", r"\bbardakl[ıi]k\b",
]
RE_CANLI_KOK = re.compile("|".join(_CANLI_KOKLERI), re.IGNORECASE | re.UNICODE)


# === denetim-kapisi ICE AKTAR ============================================
def _dk_yukle():
    tools_dir = str(EV / "tools")
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    spec = importlib.util.spec_from_file_location("denetim_kapisi_k161", str(DENETIM))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# === PARCALAMA ============================================================
def parcala_ayrac_bilgisiyle(metin):
    """Returns list of (part_text, sep_after, start_pos) tuples.
    sep_after: separator bytes AFTER the part (". ", "; ", "\n", or "")
    start_pos: 0-based start index of part_text in original metin.
    """
    parts = []
    cur = ""
    cur_start = 0
    i = 0
    while i < len(metin):
        c = metin[i]
        if c in ".!?":
            # Period/exclamation/question + whitespace
            j = i + 1
            while j < len(metin) and metin[j] in " \t":
                j += 1
            sep = metin[i:j]
            parts.append((cur, sep, cur_start))
            cur = ""
            cur_start = j
            i = j
            continue
        if c == ";":
            j = i + 1
            while j < len(metin) and metin[j] in " \t":
                j += 1
            sep = metin[i:j]
            parts.append((cur, sep, cur_start))
            cur = ""
            cur_start = j
            i = j
            continue
        if c == "\n":
            parts.append((cur, "\n", cur_start))
            cur = ""
            cur_start = i + 1
            i += 1
            continue
        cur += c
        i += 1
    if cur:
        parts.append((cur, "", cur_start))
    return parts


def olcu_ayir(metin):
    """Returns (prefix, olcu_tail)."""
    m = _OLCU_RE.search(metin)
    if m:
        return metin[:m.start()], metin[m.start():]
    m2 = _OLCU_RE_LOOSE.match(metin)
    if m2 and m2.start() == 0:
        return "", metin
    return metin, ""


# === KARAR FONKSIYONLARI ==================================================
def cumlede_ifsa_kok_var_mi(cumle):
    return bool(RE_IFSA_KOK.search(cumle))


def cumlede_canli_bilgi_var_mi(cumle):
    return bool(RE_CANLI_KOK.search(cumle))


def ilk_malzeme_bul(cumle):
    for m in _MALZ_LIST:
        if re.search(rf"\b{re.escape(m)}\b", cumle, re.IGNORECASE):
            return m
    return None


def sablon_var_mi(text):
    """Text'te SABIT SABLON cumlesi var mi?"""
    for c in parcala_ayrac_bilgisiyle(text):
        if c[0] and SABLON_RE.match(c[0].strip()):
            return True
    return False


def cumle_baslikta_mi(uid, cumle, urunler_index):
    rec = urunler_index.get(uid)
    if not isinstance(rec, dict):
        return False
    baslik = str(rec.get("baslik", "") or "")
    if not baslik:
        return False
    baslik_kelimeler = [w for w in re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ]+", baslik.lower()) if len(w) >= 3]
    if not baslik_kelimeler:
        return False
    cumle_lower = cumle.lower()
    eslesen = sum(1 for w in baslik_kelimeler if w in cumle_lower)
    return eslesen / len(baslik_kelimeler) >= 0.5


def cumleden_ifsa_koklari(cumle):
    """Cumlede hangi ifsa koklerinin gectigini bul (raporlama icin)."""
    bulgular = []
    for m in RE_IFSA_KOK.finditer(cumle):
        bulgular.append(m.group(0))
    return bulgular


# === MAIN =================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--islemler-cikti", default=str(ISLEMLER))
    ap.add_argument("--elle-cikti", default=str(ELLE_OUT))
    ap.add_argument("--rapor", action="store_true")
    ap.add_argument("--elle-sayisi-tavan", type=int, default=300)
    args = ap.parse_args()

    if not URUNLER.exists():
        print(f"HATA: {URUNLER} yok", file=sys.stderr)
        return 4
    if not RAPOR.exists():
        print(f"HATA: {RAPOR} yok", file=sys.stderr)
        return 4

    with open(URUNLER, encoding="utf-8") as f:
        urunler = json.load(f)
    with open(RAPOR, encoding="utf-8") as f:
        rapor = json.load(f)

    ifsa_ids = sorted({i["id"] for i in rapor["ihlal"]
                       if i.get("kapi", "").startswith("ifsa/")})
    print(f"ifsa kapsaminda {len(ifsa_ids)} benzersiz id", file=sys.stderr)

    id_index = {u["id"]: u for u in urunler if isinstance(u, dict) and "id" in u}
    _dk_yukle()  # sadece dogrulama/import icin

    islemler_out = []
    elle_out = []
    sayac = Counter()

    for uid in ifsa_ids:
        u = id_index.get(uid)
        if not isinstance(u, dict):
            elle_out.append({"id": uid, "cumle": "(kayit bulunamadi)",
                             "neden": "urunler.json icinde id yok"})
            sayac["ELLE"] += 1
            continue

        aciklama = str(u.get("aciklama", "") or "")
        if not aciklama.strip():
            elle_out.append({"id": uid, "cumle": aciklama,
                             "neden": "aciklama bos"})
            sayac["ELLE"] += 1
            continue

        # OLCU satiri ayir
        ana_metin, olcu = olcu_ayir(aciklama)
        # Parcala
        parts = parcala_ayrac_bilgisiyle(ana_metin)
        if not parts:
            # bos metin
            elle_out.append({"id": uid, "cumle": aciklama,
                             "neden": "ana metin bos"})
            sayac["ELLE"] += 1
            continue

        # Her parcayi karar ver. Bos parcalar (genellikle "\n" ile baslayan
        # cumle oncesi bosluk) muhafaza edilir; bunlar CIKAR listesine
        # GIRMEZ cunku metnin yapisini (satir basi gibi) tasimak zorundadir.
        keep_indices = []
        cikarilan_malzeme = []
        for idx, (part_txt, sep_after, _) in enumerate(parts):
            if not part_txt:
                # Bos parca — muhafaza et (genellikle \n iceren satir basi)
                keep_indices.append(idx)
                continue
            if not cumlede_ifsa_kok_var_mi(part_txt):
                keep_indices.append(idx)
                continue
            # ifsa koku var — karar ver
            if cumle_baslikta_mi(uid, part_txt, id_index):
                elle_out.append({
                    "id": uid, "cumle": part_txt,
                    "neden": "ifsa koku var ama cumle baslik/urun tanimi parcasi",
                })
                sayac["ELLE"] += 1
                continue
            if cumlede_canli_bilgi_var_mi(part_txt):
                elle_out.append({
                    "id": uid, "cumle": part_txt,
                    "neden": ("ifsa koku var ama cumle canli bilgi de tasiyor: "
                              f"{cumleden_ifsa_koklari(part_txt)[:3]}"),
                })
                sayac["ELLE"] += 1
                continue
            # CIKAR
            malz = ilk_malzeme_bul(part_txt)
            if malz:
                cikarilan_malzeme.append(malz)
            sayac["CIKAR"] += 1

        if not keep_indices and not cikarilan_malzeme:
            # hicbir parca yok — ELLE
            elle_out.append({"id": uid, "cumle": aciklama,
                             "neden": "tum parcalar CIKAR oldu, ortada metin yok"})
            sayac["ELLE"] += 1
            continue

        # Yeni metni olustur: keep_indices'deki parts'lari SIRASIYLA birlestir,
        # aralarindaki separatorleri koru. "; " separatorlu parts icin, "; "
        # onceki part korunuyorsa "." ile degistirilebilir (1 byte serbest).
        # Ancak basitlestirme: her keep_index arasinda original separator'u kullan;
        # eger keep_index bir onceki keep_index'ten sonra geliyorsa ve
        # aradaki tum parcalar CIKAR olduysa, o parcanin kendi separator'u
        # kullanilir (separator korunur); ek olarak "; " -> ". " donusumu
        # uygulanir (cikarilan "; " baglantisindan dolayi onceki cumlenin
        # "." ile kapanmasi gerekebilir).
        yeni_parcalar = []
        prev_keep = None
        for idx, (part_txt, sep_after, _) in enumerate(parts):
            if idx in keep_indices:
                yeni_parcalar.append((part_txt, sep_after))
                prev_keep = idx
            else:
                # Bu parca CIKAR oldu. prev_keep varsa ve prev_keep'in sep_after'i
                # "; " ise, onu ". " yap (1 byte). Ancak bu sadece eger CIKAR
                # edilen parca ";" ile ayrilmissa gecerli — sep_after CIKAR
                # edilen part'inki degil.
                if prev_keep is not None:
                    prev_txt, prev_sep = yeni_parcalar[-1]
                    if prev_sep == "; ":
                        # "; " -> ". " (1 byte serbest)
                        yeni_parcalar[-1] = (prev_txt, ". ")
                # Simdi cikarilan part'in kendi sep_after'ini de gormezden gel:
                # sonraki keep varsa o kendi sep_after'ini kullanir.

        # Parcalari birlestir. Her parcanin kendi separator'u eklenir (son
        # parca icin sep_after='' — eklenmez). Bu sayede "uygundur." gibi
        # cumle sonlari korunur.
        yeni_metin = ""
        for txt, sep in yeni_parcalar:
            yeni_metin += txt
            yeni_metin += sep

        # SABIT SABLON ekleme: cikarilan parca malzeme adi tasiyorsa VE
        # metinde henuz SABIT SABLON yoksa 1 tane ekle.
        if cikarilan_malzeme and not sablon_var_mi(yeni_metin):
            malz_set = list(dict.fromkeys(cikarilan_malzeme))  # sirayi koru
            if len(malz_set) == 1:
                sablon_cumle = f"{malz_set[0]} malzemeden üretilir."
            else:
                sablon_cumle = f"{malz_set[0]} veya {malz_set[1]} malzemeden üretilir."
            # Son anlamli karakter "." degilse sona nokta ekle (bosluktan
            # sonra "." kontrolune dikkat — "...uyar. ".endswith('.') False
            # dondurur, bu nedenle rstrip ile kontrol ediyoruz).
            if yeni_metin and not yeni_metin.rstrip().endswith((".", "!", "?")):
                yeni_metin = yeni_metin.rstrip() + "."
            elif yeni_metin != yeni_metin.rstrip():
                yeni_metin = yeni_metin.rstrip()
            yeni_metin = yeni_metin + " " + sablon_cumle
            sayac["BEYAN"] += 1

        # olcu satiri varsa sona ekle. OLCU `\nYaklaşık...` ile baslar;
        # onceki metin sonundaki bosluklari kirp ve direkt birlestir — boylece
        # bayt esitlik (yapi-denetimi) saglanir.
        if olcu:
            yeni_metin = yeni_metin.rstrip() + olcu

        # 40 karakter alti ise ELLE
        if len(yeni_metin) < 40:
            elle_out.append({
                "id": uid, "cumle": aciklama,
                "neden": f"yeni metin cok kisa ({len(yeni_metin)} kar)",
            })
            sayac["ELLE"] += 1
            continue

        if yeni_metin == aciklama:
            elle_out.append({
                "id": uid, "cumle": aciklama,
                "neden": "uygulanan karar sonucu metin degismedi",
            })
            sayac["ELLE"] += 1
            continue

        islemler_out.append({
            "id": uid,
            "alan": "aciklama",
            "deger": yeni_metin,
            "not": "K161 ifsa temizligi (cikarma+sablon, tur 3)",
        })
        sayac["PLAN"] += 1

    if args.rapor:
        print("K161 cumle-plan (tur 3) sayimlari:")
        for k in ("PLAN", "CIKAR", "BEYAN", "ELLE"):
            print(f"  {k}: {sayac[k]}")

    if sayac["ELLE"] > args.elle_sayisi_tavan:
        print(f"UYARI: ELLE sayisi {sayac['ELLE']} > tavan "
              f"{args.elle_sayisi_tavan}", file=sys.stderr)

    Path(args.islemler_cikti).parent.mkdir(parents=True, exist_ok=True)
    Path(args.elle_cikti).parent.mkdir(parents=True, exist_ok=True)
    with open(args.islemler_cikti, "w", encoding="utf-8") as f:
        json.dump({"islemler": islemler_out}, f, ensure_ascii=False, indent=2)
    with open(args.elle_cikti, "w", encoding="utf-8") as f:
        json.dump({"elle": elle_out}, f, ensure_ascii=False, indent=2)

    print(f"islemler.json: {len(islemler_out)} kayit", file=sys.stderr)
    print(f"ELLE.json: {len(elle_out)} kayit", file=sys.stderr)
    return 5 if sayac["ELLE"] > args.elle_sayisi_tavan else 0


if __name__ == "__main__":
    sys.exit(main())
