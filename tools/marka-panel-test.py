#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — MARKA DURUM PANELI kanoniklestirmesi (mutasyon-kanitli).

Okan talebi (24 Tem): marka durum paneli satirlari ham defter anahtarlarindan DEGIL
kanonik TANINMIS_MARKALAR listesinden gelsin; defterdeki sayimlar markaKatla ile kanonik
markaya KATLANSIN; taninmayan (cop) anahtarlar GORUNMESIN; bilinen ama harvest edilmemis
markalar (DeWalt vb.) to-do olarak gorunsun.

NE KILITLER (her madde ilgili satir bozulunca KIRMIZI yanar):
  (a) markaKatla PORTU site ile tutarli — sabit vaka tablosu + site markaNorm collapse kuplaji.
  (b) Panel satir evreni == TANINMIS_MARKALAR; cop anahtar (roald98, Toyota cover...) satir DEGIL.
  (c) Toyota Thingiverse sayimi 8 Toyota-X'in TOPLAMI (katlama gerceklesti; en buyuk tekilden buyuk).
  (d) EK markalarin HEPSI TANINMIS_MARKALAR'da + panelde satir; sifir-kapsamli olanlar 🔴 to-do.
  (e) Kanonik + gercek sayimli marka kumesi, ham defterden bagimsiz turetilen kumeyle AYNI
      (katlama kimseyi dusurmedi / cop kimseyi eklemedi).

Saf Python (node gerekmez), OFFLINE, dosya YAZMAZ, urunler.json OKUMAZ. Ham defter salt okunur.
Calistir:  python3 tools/marka-panel-test.py   (0 = gecti, 1 = kaldi)
"""
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
INDEX = os.path.join(ROOT, "index.html")

sys.path.insert(0, TOOLS)
import marka_katla as mk  # noqa: E402

FAILS = []


def kontrol(ad, kosul):
    print(("  PASS  " if kosul else "  FAIL  ") + ad)
    if not kosul:
        FAILS.append(ad)


def bitir():
    if FAILS:
        print("\nSONUC: KIRMIZI ❌  (%d kontrol kaldı)" % len(FAILS))
        sys.exit(1)
    print("\nSONUC: YESIL ✅")
    sys.exit(0)


PLATS = mk.PLATFORMLAR
TANINMIS = set(mk.TANINMIS_MARKALAR)

# Ham defter (.marka-kapsama.json) GITIGNORE — worktree/CI'da YOK. Katlama/aggregation
# mantigini (c/e) SENTETIK, deterministik fikstur ile kilitleriz (konfigur-test deseni):
# test edilen sey kanonik_kapsama fonksiyonunun KENDISI, panel de ayni fonksiyonu cagirir.
# Fikstur gercek defterin desenini yansitir: Toyota-X harvest anahtarlari, buyuk/kucuk
# ikizler, tasarimci-adi copu, tek urunlu Black and Decker.
FIX = {
    "Toyota":         {"Thingiverse": {"eklenen": 29, "taranan": 0, "parti": 1, "son_tarih": "2026-07-01"}},
    "Toyota cover":   {"Thingiverse": {"eklenen": 47, "parti": 1, "son_tarih": "2026-07-10"},
                       "Printables": {"eklenen": 10, "parti": 1}},
    "Toyota mount":   {"Thingiverse": {"eklenen": 46, "parti": 1}},
    "Toyota knob":    {"Thingiverse": {"eklenen": 43, "parti": 1}},
    "Toyota latch":   {"Thingiverse": {"eklenen": 12, "parti": 1}},
    "Mercedes-Benz":  {"Thingiverse": {"eklenen": 100, "parti": 1}},
    "Mercedes":       {"Printables": {"eklenen": 50, "parti": 1}},
    "volkswagen":     {"Thingiverse": {"eklenen": 600, "parti": 1}},
    "Volkswagen":     {"Printables": {"eklenen": 100, "parti": 1}},
    "Volvo Penta":    {"Thingiverse": {"eklenen": 30, "parti": 1}},
    "Volvo":          {"Printables": {"eklenen": 200, "parti": 1}},
    "ABUS":           {"Thingiverse": {"eklenen": 1, "parti": 1}},
    "Black and Decker": {"Thingiverse": {"eklenen": 1, "parti": 1}},
    # cop: sayili ama HICBIR taninmis markaya katlanmaz -> satir OLMAMALI, sayisi kaybolmali
    "roald98":        {"Thingiverse": {"eklenen": 5, "parti": 1}},
    "Speeduino":      {"Printables": {"eklenen": 8, "parti": 1}},
    "Toyota cap":     {"Thingiverse": {"eklenen": 44, "parti": 1}},
    "Toyota adapter": {"Thingiverse": {"eklenen": 45, "parti": 1}},
    "Toyota handle":  {"Thingiverse": {"eklenen": 35, "parti": 1}},
    "Toyota trim":    {"Thingiverse": {"eklenen": 31, "parti": 1}},
}
agg = mk.kanonik_kapsama(FIX)

EK_MARKALAR = ["DeWalt", "Metabo", "Festool", "Hilti", "HiKOKI", "Black+Decker", "Dyson",
               "DeLonghi", "Braun", "Tefal", "Electrolux", "AEG", "Whirlpool", "Arçelik",
               "Vestel", "Grohe", "Hansgrohe"]

# ---- (a) markaKatla portu site ile tutarli -----------------------------------
print("(a) markaKatla portu (sabit vaka + site kuplaji)")
vaka = {
    "Toyota cover": "Toyota", "Mercedes-Benz": "Mercedes", "volkswagen": "Volkswagen",
    "DeWalt": "DeWalt", "Black and Decker": "Black+Decker", "Black & Decker": "Black+Decker",
}
for giris, bek in vaka.items():
    kontrol("markaKatla(%r) == %r" % (giris, bek), mk.markaKatla(giris) == bek)
kontrol("kanonik_veya_none('roald98') is None (cop taninmaz)",
        mk.kanonik_veya_none("roald98") is None)
kontrol("markaNorm collapse: 'Black+Decker' == 'Black and Decker' == 'Black & Decker'",
        mk.markaNorm("Black+Decker") == mk.markaNorm("Black and Decker") == mk.markaNorm("Black & Decker"))
# Site kuplaji: index.html markaNorm ayni collapse'i yapiyor (port ile senkron kanit)
src = open(INDEX, encoding="utf-8").read()
mnorm = re.search(r"function markaNorm\(s\)\{[\s\S]*?\n  \}", src)
kontrol("index.html markaNorm ayıklanabildi", bool(mnorm))
mnorm_src = mnorm.group(0) if mnorm else ""
for parca in (r"/ and /g", r"/&/g", r"/\+/g"):
    kontrol("site markaNorm collapse içeriyor (%s)" % parca, parca in mnorm_src)
kontrol("port TANINMIS_MARKALAR == index.html parse (tek kaynak)",
        list(mk.TANINMIS_MARKALAR) == mk._parse_taninmis(INDEX))

# ---- (b) satir evreni == TANINMIS; cop satir yok -----------------------------
print("(b) panel satir evreni")
kontrol("agg satir evreni == TANINMIS_MARKALAR", set(agg.keys()) == TANINMIS)
cop = ["roald98", "satgod", "Infrastructure_Airsoft_Parts", "WorkHorse", "2scary", "MN82",
       "DS4", "DSM", "WPL", "CTC", "CTR", "Geo", "Speeduino", "Toplife", "RocketStart",
       "Canora", "DiveTalk", "Mojoptix", "Thomas Refault", "Pruveeo", "Silvia", "Coyote",
       "TR8", "Toyota cover", "Toyota mount", "Toyota adapter"]
sizan = [c for c in cop if c in agg]
kontrol("cop anahtar satir DEGIL (sızan: %s)" % (sizan or "-"), not sizan)

# ---- (c) Toyota katlama (Thingiverse toplami) --------------------------------
print("(c) Toyota katlama")
toyota_keys = [k for k in FIX if mk.markaKatla(k) == "Toyota"]
th_vals = [int((FIX[k].get("Thingiverse") or {}).get("eklenen", 0) or 0) for k in toyota_keys]
th_sum = sum(th_vals)
th_max = max(th_vals or [0])
toyota_th = mk.hucre_deger(agg.get("Toyota", {}).get("Thingiverse"))
kontrol("Toyota'ya en az 8 ham anahtar katlanıyor (bulunan %d)" % len(toyota_keys),
        len(toyota_keys) >= 8)
kontrol("Toyota Thingiverse == 8 Toyota-X TOPLAMI (%s == %s)" % (toyota_th, th_sum),
        toyota_th == th_sum and th_sum > 0)
kontrol("katlama gerçek: toplam (%s) tek en-büyükten (%s) büyük" % (th_sum, th_max),
        th_sum > th_max)

# ---- (d) EK markalar --------------------------------------------------------
print("(d) EK markalar to-do")
for b in EK_MARKALAR:
    kontrol("%s TANINMIS_MARKALAR'da + panel satırı" % b, b in TANINMIS and b in agg)
sifir_kapsam = [b for b in EK_MARKALAR
                if not any(mk.hucre_deger(agg[b].get(p)) for p in PLATS)]
for b in sifir_kapsam:
    k, s = mk.durum_hucreler({p: mk.hucre_deger(agg[b].get(p)) for p in PLATS}, PLATS)
    kontrol("%s sıfır-kapsam → 3 platform 🔴 to-do" % b, len(k) == 3 and len(s) == 0)
kontrol("Black+Decker tanınır + 'Black and Decker' ona katlanır",
        mk.taninmisMarkaMi("Black+Decker") and mk.markaKatla("Black and Decker") == "Black+Decker")
kontrol("EK markaların ≥15'i sıfır-kapsam (harvest bekliyor)", len(sifir_kapsam) >= 15)

# ---- (e) gercek sayimli marka kumesi korunuyor -------------------------------
print("(e) gerçek sayımlı marka kümesi korunuyor")


def raw_sayili(k):
    for p, v in (FIX[k] or {}).items():
        if isinstance(v, dict) and (v.get("eklenen", 0) > 0 or v.get("taranan", 0) > 0):
            return True
    return False


# fikstürden BAGIMSIZ turet: sayili + kanonige katlanan (taninmis) ham anahtarlarin kanonikleri
beklenen = {mk.markaKatla(k) for k in FIX
            if raw_sayili(k) and mk.taninmisMarkaMi(mk.markaKatla(k))}
# agg'den turet: gercek sayimli kanonik markalar
gercek = {m for m in agg if any(mk.hucre_deger(agg[m].get(p)) for p in PLATS)}
kontrol("agg gerçek-sayımlı kümesi == ham-defter bağımsız türetimi (%d marka)" % len(gercek),
        gercek == beklenen and len(gercek) > 0)
# spesifik: katlamaya bagimli markalar sayida
for b in ["Mercedes", "Volvo", "Volkswagen", "Toyota"]:
    kontrol("%s gerçek sayımlı (katlama sonrası korundu)" % b, b in gercek)

bitir()
