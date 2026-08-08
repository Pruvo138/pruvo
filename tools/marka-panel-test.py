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
  (f) markaKatla ONEK kurali: ALT-DIZE yanlis-pozitifi yasak.
  (g) TEK KANONIK PLATFORM TANIMI (marka_katla.PLATFORM_TANIMI): panel/CSV/defter yazicisi
      platform listesini ELLE tutmaz, hepsi TURETIR; tanim degisince panel PESINDEN GELIR.
  (h) Yeni kolonlar (Cults3D + CGTrader) panelde VAR, SONDA ve gercekten sayim tasiyor.
  (i) null != 0 ayrimi: hasat yapilmamis hucre None (🔴 to-do), arandi-bos hucre 0 (⚪).
  (j) KIMLIK KORUNUMU: yeni platform verisi mevcut 3 kolonun hucre degerini DEGISTIRMEZ.
  (k) Esik mantigi (AZ_ORAN / AZ_MIN).
  (l) OTOMATIK TAZELEME davranis testi -> tools/panel-tazeleme-test.js (node ISTER,
      node yoksa FAIL-CLOSED; sessiz "olculemedi" YESIL sayilmaz).

OFFLINE, urunler.json OKUMAZ, ham defter salt okunur. (l) ekseni gecici dizine bir
panel.html yazar ve siler; repo dosyasi DEGISMEZ.
Kabul testinin KENDISI olculur:  python3 tools/panel-mutasyon-test.py  (7 mutant + 1 kontrol)
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


def kontrol_c(ad, fn):
    """Çağrılabilir iddia — İSTİSNA da FAIL sayılır.
    Gerekçe: bozuk konfigürasyon testi ÇÖKERTİRSE çıktıda "SONUC:" satırı hiç basılmaz;
    mutasyon bataryası bunu "kırmızı yandı" ile karıştıramamalı, kabul testi her hâlükârda
    kendi hükmünü basmalı ([[mutasyon-kaniti-yeniden-uretilebilir]])."""
    try:
        ok = bool(fn())
    except Exception as e:
        print("  FAIL  %s  [istisna: %s: %s]" % (ad, type(e).__name__, e))
        FAILS.append(ad)
        return
    kontrol(ad, ok)


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
    "Toyota cover": "Toyota", "Toyota 86": "Toyota", "Mercedes-Benz": "Mercedes",
    "volkswagen": "Volkswagen", "DeWalt": "DeWalt",
    "Black and Decker": "Black+Decker", "Black & Decker": "Black+Decker",
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
    # beklenen kirmizi sayisi PLATS uzunlugundan TURETILIR (elle "3" yazilirsa yeni
    # platform eklendiginde test sahte kirmizi yakar -> [[ikiz-tanim-sessiz-ayrisma]])
    kontrol("%s sıfır-kapsam → %d platformun HEPSİ 🔴 to-do" % (b, len(PLATS)),
            len(k) == len(PLATS) and len(s) == 0)
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

# ---- (f) markaKatla ONEK kurali: ALT-DIZE yanlis-pozitifi YASAK --------------
# markaKatla onek kurali: n.startswith(nm+" ") or n.startswith(nm+"-"). Yani taninmis
# marka YALNIZ boSluk/tire ile onekliyse katlanir; ALT-DIZE (icinde gecmesi) DEGIL.
# Bu bolum o farki kilitler: onek kurali 'nm in n' alt-dize'ye ya da ayiraci ('/'-')
# kaldiran startswith(nm)'ye MUTE edilirse asagidaki cop degerler taninmis markaya
# sizar -> KIRMIZI. Deger -> markaNorm sonrasi ALT-DIZE olarak icerdigi taninmis marka:
print("(f) alt-dize yanlis-pozitif yasak (önek mutasyon kilidi)")
ALTDIZE_COP = {
    "Fortoyota":  "Toyota",   # 'toyota' ORTADA -> ne onek ne ayiracli; 'nm in n' sizdirir
    "xToyota":    "Toyota",   # 'toyota' sonda; 'nm in n' sizdirir
    "seatbelt":   "Seat",     # 'seat' BASTA ayiracsiz; startswith(nm) mutasyonu da sizdirir
    "Audiophile": "Audi",     # 'audi' basta ayiracsiz
    "Fordable":   "Ford",     # 'ford' basta ayiracsiz
    "Minimalist": "Mini",     # 'mini' basta ayiracsiz
    "Bmwx":       "BMW",      # 'bmw' basta ayiracsiz
}
# on-kosul: sizabilecekleri taban markalar GERCEKTEN taninmis (yoksa mutasyon kanit degil)
for ic_marka in sorted(set(ALTDIZE_COP.values())):
    kontrol("ön-koşul: %s taninmis marka (sızma hedefi gerçek)" % ic_marka,
            mk.taninmisMarkaMi(ic_marka))
# 1) hicbir cop deger taninmis markaya katlanmaz (kendisi olarak doner)
for cop_ad, ic_marka in ALTDIZE_COP.items():
    kontrol("markaKatla(%r) katlanmaz (kendisi, %r DEĞİL)" % (cop_ad, ic_marka),
            mk.markaKatla(cop_ad) == cop_ad)
    kontrol("kanonik_veya_none(%r) is None (alt-dize tanınmaz)" % cop_ad,
            mk.kanonik_veya_none(cop_ad) is None)
# 2) copFIX ile agg: cop anahtar satir DEGIL + icerdikleri marka sifir-kapsam (sayim SIZMADI)
copFIX = {ad: {"Thingiverse": {"eklenen": 99, "parti": 1}} for ad in ALTDIZE_COP}
cop_agg = mk.kanonik_kapsama(copFIX)
sizan_satir = [ad for ad in ALTDIZE_COP if ad in cop_agg]
kontrol("alt-dize çöp anahtar satır DEĞİL (sızan: %s)" % (sizan_satir or "-"),
        not sizan_satir)
hedef = sorted(set(ALTDIZE_COP.values()))
sizan_sayim = [b for b in hedef if any(mk.hucre_deger(cop_agg[b].get(p)) for p in PLATS)]
kontrol("alt-dize sızıntı YOK: %s hâlâ sıfır-kapsam (sızan: %s)"
        % (hedef, sizan_sayim or "-"), not sizan_sayim)
# 3) POZITIF karsi-kanit: gercek onek (boSluk/tire) HALA katlanir (mutasyon asiri-daralmasin)
for giris, bek in {"Toyota 86": "Toyota", "Seat-Leon": "Seat", "Ford Focus": "Ford"}.items():
    kontrol("pozitif önek korunur: markaKatla(%r) == %r" % (giris, bek),
            mk.markaKatla(giris) == bek)

# ---- (g) TEK KANONIK PLATFORM TANIMI — ikiz liste YASAK ----------------------
# Panel (PLATS/KISA), CSV ve defter yazicisi platform listelerini ELLE tutarsa sessizce
# ayrisirlar ([[ikiz-tanim-sessiz-ayrisma]]): kolon basligi ile kolon degeri, ya da
# yazicinin kabul ettigi kume ile panelin gosterdigi kume birbirini tutmaz. Burada
# (1) turevlerin tanimdan geldigi, (2) tuketicilerin ELLE liste YAZMADIGI ve
# (3) tanim degisince tuketicinin GERCEKTEN pesinden geldigi kilitlenir.
print("(g) tek kanonik platform tanımı (ikiz türetme)")
kontrol("PLATFORM_TANIMI mevcut ve >=3 platform", len(mk.PLATFORM_TANIMI) >= 3)
kontrol("PLATFORMLAR tanımdan türemiş",
        mk.PLATFORMLAR == [a for a, _k, _d in mk.PLATFORM_TANIMI])
kontrol("PLATFORM_KISA tanımdan türemiş",
        mk.PLATFORM_KISA == [k for _a, k, _d in mk.PLATFORM_TANIMI])
kontrol("PLATFORM_DOMAIN tanımdan türemiş",
        mk.PLATFORM_DOMAIN == {d: a for a, _k, d in mk.PLATFORM_TANIMI})
kontrol("türev uzunlukları eşit",
        len(mk.PLATFORMLAR) == len(mk.PLATFORM_KISA) == len(mk.PLATFORM_TANIMI))
# fail-closed dogrulayici GERCEKTEN patliyor mu (nobetci olu olmasin)
_yedek = list(mk.PLATFORMLAR)
try:
    mk.PLATFORMLAR = _yedek[:-1]
    try:
        mk._platform_tanimi_dogrula()
        _patladi = False
    except RuntimeError:
        _patladi = True
finally:
    mk.PLATFORMLAR = _yedek
kontrol("_platform_tanimi_dogrula() ayrışmada RuntimeError atıyor (fail-closed)", _patladi)

TUKETICILER = ["parity-panel.py", "parity-csv.py", "marka-kapsama.py"]
ELLE_LISTE = re.compile(r"^\s*(PLATS|KISA|PLATFORMLAR|PLATFORM_KISA|DOMAIN)\s*=\s*[\[\{]", re.M)
for f in TUKETICILER:
    yol = os.path.join(TOOLS, f)
    kaynak = open(yol, encoding="utf-8").read()
    kontrol("%s ELLE platform listesi YAZMIYOR" % f, not ELLE_LISTE.search(kaynak))
    kontrol("%s listesini mk.'den TÜRETİYOR" % f, "mk.PLATFORM" in kaynak)


def _panel_yukle():
    """parity-panel.py'yi TAZE exec et (mk sys.modules'ten paylasilir -> turetme olculur)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("pp_test", os.path.join(TOOLS, "parity-panel.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    pp, _pp_hata = _panel_yukle(), None
except Exception as _e:            # ikiz ayrismasi import aninda fail-closed patlayabilir
    pp, _pp_hata = None, "%s: %s" % (type(_e).__name__, _e)
kontrol("parity-panel.py YÜKLENEBİLDİ (%s)" % (_pp_hata or "ok"), pp is not None)
kontrol_c("panel PLATS == mk.PLATFORMLAR", lambda: list(pp.PLATS) == list(mk.PLATFORMLAR))
kontrol_c("panel KISA == mk.PLATFORM_KISA", lambda: list(pp.KISA) == list(mk.PLATFORM_KISA))
kontrol_c("panel AZ_ORAN/AZ_MIN == mk (sunucu durumu ile istemci rengi ayrışmasın)",
          lambda: pp.AZ_ORAN == mk.AZ_ORAN and pp.AZ_MIN == mk.AZ_MIN)
# TURETME EKSENI: kanonik tanim degisince panel PESINDEN GELMELI (elle liste olsaydi GELMEZDI)
_yp, _yk = list(mk.PLATFORMLAR), list(mk.PLATFORM_KISA)
_izledi = _izledi_veri = False
try:
    mk.PLATFORMLAR = _yp + ["ZZTest"]
    mk.PLATFORM_KISA = _yk + ["ZZTest"]
    try:
        pp2 = _panel_yukle()
        _izledi = list(pp2.PLATS) == _yp + ["ZZTest"] and list(pp2.KISA) == _yk + ["ZZTest"]
        _veri = pp2.panel_data()
        _izledi_veri = _veri["plats"] == _yk + ["ZZTest"] and \
            all(len(r["cells"]) == len(_yp) + 1 for r in _veri["rows"])
    except Exception as _e:
        print("        [türetme ekseni istisnası: %s: %s]" % (type(_e).__name__, _e))
finally:
    mk.PLATFORMLAR, mk.PLATFORM_KISA = _yp, _yk
kontrol("TÜRETME: kanonik tanım değişince panel PLATS/KISA peşinden geldi", _izledi)
kontrol("TÜRETME: panel_data() plats + hücre SAYISI da peşinden geldi", _izledi_veri)
try:
    pp = _panel_yukle()             # gercek tanimla geri yukle
except Exception:
    pp = None

# ---- (h) YENI KOLONLAR: Cults3D + CGTrader ----------------------------------
print("(h) yeni kolonlar (Cults3D + CGTrader)")
YENI_KOLON = ["Cults3D", "CGTrader"]
for p in YENI_KOLON:
    kontrol("%s kanonik platform listesinde" % p, p in mk.PLATFORMLAR)
    kontrol_c("%s panel kolonu (KISA)" % p, lambda p=p: p in pp.KISA)
kontrol("mevcut 3 kolon AYNI SIRADA ve BASTA (kimlik korunumu)",
        mk.PLATFORMLAR[:3] == ["Printables", "Thingiverse", "MakerWorld"])
kontrol("yeni kolonlar SONA eklendi", mk.PLATFORMLAR[3:] == YENI_KOLON)
kontrol("her platformun link domaini tanımlı",
        all(any(d for d, a in mk.PLATFORM_DOMAIN.items() if a == p) for p in mk.PLATFORMLAR))

# yeni kolonlar GERCEKTEN sayim tasiyabiliyor mu (kolonlar dekoratif olmasin)
YENI_FIX = {
    "Toyota": {"Cults3D": {"eklenen": 12, "parti": 1}, "CGTrader": {"eklenen": 21, "parti": 1}},
    "Toyota cover": {"Cults3D": {"eklenen": 8, "parti": 1}},
    "Subaru": {"CGTrader": {"eklenen": 3, "parti": 1}},
}
yagg = mk.kanonik_kapsama(YENI_FIX)
kontrol("Cults3D katlama: Toyota == 12+8 == 20",
        mk.hucre_deger(yagg["Toyota"].get("Cults3D")) == 20)
kontrol("CGTrader: Toyota == 21", mk.hucre_deger(yagg["Toyota"].get("CGTrader")) == 21)
kontrol("CGTrader: Subaru == 3", mk.hucre_deger(yagg["Subaru"].get("CGTrader")) == 3)
_ycells = [mk.hucre_deger(yagg["Toyota"].get(p)) for p in mk.PLATFORMLAR]
kontrol_c("panel hücre vektörü yeni kolonları TAŞIYOR (%d hücre)" % len(_ycells),
          lambda: _ycells[mk.PLATFORMLAR.index("Cults3D")] == 20
          and _ycells[mk.PLATFORMLAR.index("CGTrader")] == 21)

# ---- (i) null != 0 AYRIMI (B2) — panelin TEK isi olan to-do sinyali ---------
# Hasat YAPILMAMIS hucre null (🔴 yapilacak), hasat yapilip urun cikmamis hucre 0 (⚪).
# Turetme/backfill "eslesme bulamadim"i otomatik 0 yazarsa tum 🔴 evreni sessizce
# yalanci ⚪ olur ve panel yapilacak sinyalini KAYBEDER.
print("(i) null ≠ 0 ayrımı (to-do sinyali)")
kontrol("hucre_deger(None) is None (kayıt yok -> hiç aranmadı)", mk.hucre_deger(None) is None)
kontrol("hucre_deger({}) is None", mk.hucre_deger({}) is None)
kontrol("hucre_deger(taranan=0,eklenen=0) is None (0 DEĞİL)",
        mk.hucre_deger({"taranan": 0, "eklenen": 0}) is None)
kontrol("hucre_deger(taranan=9,eklenen=0) == 0 (arandı-boş; None DEĞİL)",
        mk.hucre_deger({"taranan": 9, "eklenen": 0}) == 0)
kontrol("hucre_deger(taranan=9,eklenen=4) == 4", mk.hucre_deger({"taranan": 9, "eklenen": 4}) == 4)
NULL_FIX = {
    "Toyota": {"Cults3D": {"taranan": 40, "eklenen": 0, "parti": 1},   # arandi-BOS -> 0 (⚪)
               "CGTrader": {"eklenen": 5, "parti": 1}},                # dolu
    # Subaru'nun Cults3D kaydi HIC YOK -> None (🔴 yapilacak)
    "Subaru": {"CGTrader": {"eklenen": 5, "parti": 1}},
}
nagg = mk.kanonik_kapsama(NULL_FIX)
t_c3d = mk.hucre_deger(nagg["Toyota"].get("Cults3D"))
s_c3d = mk.hucre_deger(nagg["Subaru"].get("Cults3D"))
kontrol("arandı-boş hücre 0 (⚪), None DEĞİL", t_c3d == 0 and t_c3d is not None)
kontrol("hiç aranmamış hücre None (🔴), 0 DEĞİL", s_c3d is None)
kontrol("iki hücre AYIRT EDİLEBİLİR (0 is not None)", t_c3d is not s_c3d)
_k_t, _s_t = mk.durum_hucreler({p: mk.hucre_deger(nagg["Toyota"].get(p))
                                for p in mk.PLATFORMLAR}, mk.PLATFORMLAR)
_k_s, _s_s = mk.durum_hucreler({p: mk.hucre_deger(nagg["Subaru"].get(p))
                                for p in mk.PLATFORMLAR}, mk.PLATFORMLAR)
kontrol("arandı-boş (0) hücre 🔴 to-do SAYILMAZ", "Cults3D" not in _k_t)
kontrol("hiç aranmamış (None) hücre 🔴 to-do SAYILIR", "Cults3D" in _k_s)

# ---- (j) KIMLIK KORUNUMU: ilk 3 kolon 3-platform hesabiyla BIT BIT ayni ------
print("(j) kimlik korunumu (mevcut 3 kolon)")
# Yeni kolonlarin EKLENMESI mevcut 3 kolonun HUCRE DEGERINI degistirmemeli. Ayni fikstur
# once yeni-platform verisi OLMADAN, sonra VARKEN katlanir; ilk 3 kolon bit bit ayni olmali.
# (Durumun/renklerin degismesi BEKLENIR — kolon eklemenin AMACI o; kilitlenen sey DEGER.)
ESKI_PLATS = ["Printables", "Thingiverse", "MakerWorld"]
KIM_FIX = {m: dict(v) for m, v in FIX.items()}
KIM_FIX["Toyota"]["Cults3D"] = {"eklenen": 77, "parti": 1}
KIM_FIX["Toyota"]["CGTrader"] = {"eklenen": 88, "parti": 1}
KIM_FIX["Subaru"] = {"CGTrader": {"eklenen": 66, "parti": 1}}
KIM_FIX["Volvo Penta"] = dict(KIM_FIX["Volvo Penta"])
KIM_FIX["Volvo Penta"]["Cults3D"] = {"eklenen": 9, "parti": 1}
oncesi = mk.kanonik_kapsama(FIX)
sonrasi = mk.kanonik_kapsama(KIM_FIX)
kontrol("satır evreni değişmedi", set(oncesi) == set(sonrasi))
sapan = [(m, p) for m in oncesi for p in ESKI_PLATS
         if mk.hucre_deger(oncesi[m].get(p)) != mk.hucre_deger(sonrasi[m].get(p))]
kontrol("mevcut 3 kolonda SAPAN HÜCRE = 0 (sapan: %s)" % (sapan[:3] or "-"), not sapan)
kontrol("karşılaştırma BOŞ değil (%d hücre ölçüldü)" % (len(oncesi) * 3),
        len(oncesi) * 3 > 300)
# kontrol-mutanti: olcum gercekten duyarli mi (3 kolondan birini bozarsak YAKALAR mi)
_boz = {m: dict(v) for m, v in KIM_FIX.items()}
_boz["Toyota"]["Thingiverse"] = {"eklenen": 1, "parti": 1}
_bagg = mk.kanonik_kapsama(_boz)
_yakalanan = [(m, p) for m in oncesi for p in ESKI_PLATS
              if mk.hucre_deger(oncesi[m].get(p)) != mk.hucre_deger(_bagg[m].get(p))]
kontrol("kimlik ölçümü DUYARLI: kasıtlı bozma YAKALANIYOR", bool(_yakalanan))

# ---- (k) ESIK MANTIGI (AZ_ORAN / AZ_MIN) ------------------------------------
print("(k) eşik mantığı (AZ_ORAN / AZ_MIN)")
kontrol("AZ_ORAN == 0.5", mk.AZ_ORAN == 0.5)
kontrol("AZ_MIN == 10", mk.AZ_MIN == 10)
# Indisler PLATFORMLAR uzunlugundan TURETILIR; sabit PL5[3]/PL5[4] yazilirsa platform
# listesi daralinca test COKER ve cokme "kirmizi yandi" ile karisir.
PL5 = mk.PLATFORMLAR
kontrol("eşik ekseni ölçülebilir (>=3 platform)", len(PL5) >= 3)
_v = {p: None for p in PL5}
_v[PL5[0]], _v[PL5[1]], _v[PL5[2]] = 100, 40, 60   # 40 < 100*0.5 -> SARI, 60 -> degil
_k, _s = mk.durum_hucreler(dict(_v), PL5)
kontrol("lider 100: 40 SARI (az kalmış)", PL5[1] in _s)
kontrol("lider 100: 60 SARI DEĞİL", PL5[2] not in _s)
_bos = PL5[3:]
kontrol("değersiz platformların HEPSİ 🔴 (%d adet, tot>=3)" % len(_bos),
        all(p in _k for p in _bos) and len(_k) == len(_bos))
_v2 = {p: None for p in PL5}
_v2[PL5[0]], _v2[PL5[1]] = 9, 1                    # lider 9 < AZ_MIN -> orantiya BAKMA
_k2, _s2 = mk.durum_hucreler(dict(_v2), PL5)
kontrol("lider AZ_MIN altında (9): sarı ÜRETİLMEZ (küçük markada gürültü)", _s2 == [])

# ---- (l) OTOMATIK TAZELEME davranis testi (D7) -------------------------------
# node ISTER; node yoksa FAIL-CLOSED (sessiz "olculemedi" YESIL sayilmaz).
print("(l) otomatik tazeleme arama/filtre/sıralamayı bozmuyor (node DOM testi)")
import shutil          # noqa: E402
import subprocess      # noqa: E402
import tempfile        # noqa: E402

_node = shutil.which("node")
kontrol("node bulundu (tazeleme testi ÖLÇÜLEBİLİR)", bool(_node))
if _node:
    _tmpd = tempfile.mkdtemp(prefix="panel-tazeleme-")
    _hp = os.path.join(_tmpd, "panel.html")
    _r = None
    try:
        with open(_hp, "w", encoding="utf-8") as _f:
            _f.write(pp.render_html())
        _r = subprocess.run([_node, os.path.join(TOOLS, "panel-tazeleme-test.js"), _hp],
                            capture_output=True, text=True)
    except Exception as _e:
        print("        [HTML üretilemedi: %s: %s]" % (type(_e).__name__, _e))
    if _r is not None and _r.returncode != 0:
        print(_r.stdout[-3000:])
        print(_r.stderr[-2000:])
    kontrol("panel HTML üretildi + panel-tazeleme-test.js rc=0",
            _r is not None and _r.returncode == 0)
    kontrol("tazeleme testi GERÇEKTEN koştu (PASS satırı var)",
            _r is not None and "PASS" in _r.stdout)
    shutil.rmtree(_tmpd, ignore_errors=True)

bitir()
