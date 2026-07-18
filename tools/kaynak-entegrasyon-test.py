#!/usr/bin/env python3
r"""KABUL TESTI — denetim-kapisi.py OLCU KAPISI kaynak-muafiyeti (KAYNAK ENTEGRASYONU).

NEDEN: MakerWorld/Cults3D/MyMiniFactory adaptorleri urunu EKLEME ANINDA VARSAYILAN OLARAK
OLCUSUZ ekler (indirme login/hesap/OAuth-gated; bkz makerworld-ekle.py / cults3d-ekle.py /
myminifactory-ekle.py). denetim-kapisi.py `kapi_olcu` eskiden yalniz satin-alma/parametrik'i
muaf tutuyordu -> bu 3 kaynagin (olcusuz) urunleri YANLISLIKLA auto_sil ediliyordu = urun kaybi.
Bu test o muafiyeti kilitler; ANCAK Printables/Thingiverse olcusuz urununu HALA auto_sil
saymayi (kapinin KALBI) regresyon olarak korur.

ONCE-KIRMIZI kaniti: bu test DEGISIKLIK ONCESI kodda YENI iddialarda (MakerWorld/Cults3D/
MyMiniFactory olcusuz -> muaf) KIRMIZI yanar; muafiyet eklenince YESIL. REGRESYON iddialari
(Printables/Thingiverse olcusuz -> auto_sil) ONCE DE SONRA DA YESIL kalir.

Kosum:  python3 tools/kaynak-entegrasyon-test.py   (cikis 0 = gecti, 1 = kaldi)
"""
import importlib.util
import os
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
FAILS = []


def _load(fname, modname):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(DIR, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


dk = _load("denetim-kapisi.py", "denetim_kapisi")

OLCUSUZ = "Dayanikli parca, kolay montaj. Farkli renk secenekleri."
OLCULU = "Dayanikli parca. Yaklasik dis olculer: 40 × 25 × 10 mm."


def check(ad, kosul):
    durum = "ok  " if kosul else "KALDI"
    print("  %s %s" % (durum, ad))
    if not kosul:
        FAILS.append(ad)


def urun(uid, baslik="Renault kapi kolu", aciklama=OLCUSUZ, **over):
    u = {"id": uid, "kategori": "Otomobil", "marka": ["Renault"], "baslik": baslik,
         "aciklama": aciklama, "fiyat": "300 TL",
         "gorseller": ["https://media.pruvo3d.com/urunler/%s-1.jpg" % uid]}
    u.update(over)
    return u


def muaf(kayit, aciklama=OLCUSUZ):
    """kapi_olcu -> (None, "") mi? (muaf = auto_sil EDILMEZ)."""
    kapi, _ = dk.kapi_olcu(urun("x", aciklama=aciklama), kayit)
    return kapi is None


def auto_sil(kayit, aciklama=OLCUSUZ):
    """kapi_olcu -> ("olcu", ...) mi? (olcusuz -> auto_sil)."""
    kapi, _ = dk.kapi_olcu(urun("x", aciklama=aciklama), kayit)
    return kapi == "olcu"


# =============================================================================
# YENI IDDIALAR — bu 3 kaynak olcusuz ekleniyor, olcu kapisindan MUAF olmali.
# (DEGISIKLIK ONCESI KIRMIZI yanar; muafiyet eklenince YESIL.)
# =============================================================================
print("--- YENI (degisiklik oncesi KIRMIZI olmali) ---")
# 1 MakerWorld — kaynak alani + tam URL domaini
check("1 MakerWorld olcusuz -> MUAF (kaynak alani)",
      muaf({"kaynak": "MakerWorld", "link": "https://makerworld.com/en/models/123-foo",
            "lisans": "CC BY 4.0", "tur": "ucretsiz-cc"}))
# 2 Cults3D — GERCEK fallback link (cults3d:slug, DOMAIN YOK) -> yalniz KAYNAK ALANI kurtarir
check("2 Cults3D olcusuz -> MUAF (kaynak alani; fallback link domainsiz)",
      muaf({"kaynak": "Cults3D", "link": "cults3d:my-model", "tur": "satin-alma-benzeri"}))
# 3 MyMiniFactory — kaynak alani + tam URL domaini
check("3 MyMiniFactory olcusuz -> MUAF (kaynak alani)",
      muaf({"kaynak": "MyMiniFactory", "link": "https://www.myminifactory.com/object/foo-123",
            "lisans": "CC BY 4.0"}))

# 5 HEM kaynak alani HEM link domaini calisir (her kaynak icin iki varyant)
print("--- 5: kaynak-alani VE link-domaini iki yol da (her kaynak 2 varyant) ---")
check("5a MakerWorld domain-only (kaynak alani YOK) -> MUAF",
      muaf({"link": "https://makerworld.com/en/models/999"}))
check("5b MakerWorld field-only (link BOS) -> MUAF",
      muaf({"kaynak": "MakerWorld", "link": ""}))
check("5c Cults3D domain-only -> MUAF",
      muaf({"link": "https://cults3d.com/en/3d-model/car/renault-clio-kol"}))
check("5d Cults3D field-only (mmf-benzeri i̇c anahtar) -> MUAF",
      muaf({"kaynak": "cults3d", "link": "cults3d:slug-only"}))   # kucuk-harf de eslesir
check("5e MyMiniFactory domain-only -> MUAF",
      muaf({"link": "https://www.myminifactory.com/object/renault-1"}))
check("5f MyMiniFactory field-only (i̇c anahtar link) -> MUAF",
      muaf({"kaynak": "MyMiniFactory", "link": "mmf:12345"}))

# =============================================================================
# REGRESYON — KAPININ KALBI: Printables/Thingiverse olcusuz HALA auto_sil.
# (DEGISIKLIK ONCESI DE SONRA DA YESIL — muafiyet bunlara SIZMAMALI.)
# =============================================================================
print("--- REGRESYON (once de sonra da YESIL — kapinin kalbi) ---")
# Thingiverse'in urun-ekle.py'de yazdigi GERCEK bicim: kaynak="Thingiverse",
# link="https://www.thingiverse.com/thing:<id>" (bkz urun-ekle.py process_one).
check("4a Printables olcusuz -> auto_sil (kaynak alani)",
      auto_sil({"kaynak": "Printables", "link": "https://www.printables.com/model/123",
                "lisans": "CC BY 4.0"}))
check("4b Printables olcusuz -> auto_sil (domain-only)",
      auto_sil({"link": "https://www.printables.com/model/456"}))
check("4c Thingiverse olcusuz -> auto_sil (kaynak alani)",
      auto_sil({"kaynak": "Thingiverse", "link": "https://www.thingiverse.com/thing:12345",
                "lisans": "CC BY 4.0"}))
check("4d Thingiverse olcusuz -> auto_sil (domain-only)",
      auto_sil({"link": "https://www.thingiverse.com/thing:6789"}))
# string kayit (eski bicim) -> ilk token link; printables.com -> auto_sil
check("4e string kayit (printables link) -> auto_sil",
      auto_sil("https://www.printables.com/model/999 CC-BY"))

# =============================================================================
# SAGLIK / ROBUSTLUK — once de sonra da YESIL.
# =============================================================================
print("--- SAGLIK (once de sonra da YESIL) ---")
# 6 olcu satiri OLAN MakerWorld urunu de gecer (trivial — olcu zaten var)
check("6 MakerWorld OLCULU -> MUAF (olcu satiri var)",
      muaf({"kaynak": "MakerWorld", "link": "https://makerworld.com/en/models/1"}, aciklama=OLCULU))
# CGTrader zaten satin-alma ile muaf (KIRMIZI-ONCE DEGIL; robustluk teyidi)
check("CGTrader satin-alma olcusuz -> MUAF (zaten satin-alma)",
      muaf({"kaynak": "CGTrader", "link": "https://www.cgtrader.com/x", "tur": "satin-alma"}))
# alakasiz kaynak olcusuz -> auto_sil (muafiyet gevsemedi)
check("bilinmeyen kaynak olcusuz -> auto_sil (gevseme yok)",
      auto_sil({"kaynak": "SomethingElse", "link": "https://example.com/x"}))

# Yardimci fonksiyonun kendisi (varsa) — dict VE string ikisini de dogru ayirt eder.
# Muafiyet eklenmeden ONCE fonksiyon YOK -> bu blok atlanir (kirmizi run temiz kalir).
if hasattr(dk, "_olcu_muaf_kaynak"):
    print("--- _olcu_muaf_kaynak birim (fonksiyon mevcut) ---")
    check("helper: MakerWorld dict -> True", dk._olcu_muaf_kaynak({"kaynak": "MakerWorld"}) is True)
    check("helper: makerworld string link -> True",
          dk._olcu_muaf_kaynak("https://makerworld.com/en/models/1") is True)
    check("helper: printables dict -> False",
          dk._olcu_muaf_kaynak({"kaynak": "Printables", "link": "https://www.printables.com/x"}) is False)
    check("helper: thingiverse string -> False",
          dk._olcu_muaf_kaynak("https://www.thingiverse.com/thing:1") is False)
    check("helper: None -> False (KeyError/crash yok)", dk._olcu_muaf_kaynak(None) is False)
else:
    print("(_olcu_muaf_kaynak fonksiyonu HENUZ YOK -> birim blok atlandi; muafiyet eklenince kosar)")


# =============================================================================
# ENTEGRASYON — denetle() uctan uca: MakerWorld olcusuz auto_sil'de OLMAMALI,
# Printables olcusuz auto_sil'de OLMALI (kapinin gercek baglantisi).
# =============================================================================
print("--- ENTEGRASYON (denetle uctan uca) ---")
mw_u = urun("mw-olcusuz", baslik="Renault Clio kapi kolu")             # olcusuz, gecerli lisans
pr_u = urun("pr-olcusuz", baslik="Renault Megane bardaklik gozu")     # olcusuz, gecerli lisans
urunler = [mw_u, pr_u]
kaynaklar = {
    "mw-olcusuz": {"kaynak": "MakerWorld", "link": "https://makerworld.com/en/models/555-clio",
                   "lisans": "CC BY 4.0", "tur": "ucretsiz-cc"},
    "pr-olcusuz": {"kaynak": "Printables", "link": "https://www.printables.com/model/777",
                   "lisans": "CC BY 4.0", "tur": "ucretsiz-cc"},
}
r = dk.denetle(urunler, {"mw-olcusuz", "pr-olcusuz"}, set(), kaynaklar)
auto = {(a["id"], a["kapi"]) for a in r["auto_sil"]}
auto_ids = {a["id"] for a in r["auto_sil"]}
check("ENT MakerWorld olcusuz auto_sil'de DEGIL", "mw-olcusuz" not in auto_ids)
check("ENT Printables olcusuz auto_sil(olcu)'da", ("pr-olcusuz", "olcu") in auto)


print()
if FAILS:
    print("BASARISIZ — %d/%d kontrol KALDI:" % (len(FAILS), len(FAILS)), file=sys.stderr)
    for ad in FAILS:
        print("  x %s" % ad, file=sys.stderr)
    sys.exit(1)
print("TUM TESTLER GECTI.")
sys.exit(0)
