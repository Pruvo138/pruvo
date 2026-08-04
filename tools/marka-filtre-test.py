#!/usr/bin/env python3
r"""KABUL TESTI — marka TAM-KELIME (\bMARKA\b) arama filtresi.

Sorun (Ford derin pull, 2026-07-18): marka aramasi basligi ALT-DIZE eslesen
alakasiz urunleri getiriyor ("Oxford", "afford", "Food" -> 896/1214 gurultu);
maraba kendi filtresini kurmak zorunda kaldi. Cozum: printables-api.py'de
marka_kelime_gecer(baslik, marka) -> baslikta marka Unicode kelime siniriyla
(\bMARKA\b, Turkce-duyarli, buyuk/kucuk duyarsiz) geciyorsa True.

Bu test:
  1. marka_kelime_gecer'i karisik basliklarla sinar (Ford GECER, Oxford/afford/Food ELENIR).
  2. printables-ara.py VE thing-ara.py'nin ayni fonksiyonu KULLANDIGINI dogrular
     (kaynak-grep: filtre gercekten baglanmis mi — birinde unutulursa yakalanir).

Calistir:  python3 tools/marka-filtre-test.py   (cikis 0 = gecti, 1 = kaldi)
"""
import importlib.util
import os
import re
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
FAILS = []


def _load(fname, modname):
    spec = importlib.util.spec_from_file_location(modname, os.path.join(DIR, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check(ad, kosul):
    if not kosul:
        FAILS.append(ad)
        print("TEST KALDI:", ad, file=sys.stderr)


pr = _load("printables-api.py", "pr_api")
gec = pr.marka_kelime_gecer

# --- 1. Fonksiyon davranisi: karisik baslik listesi ---------------------------
# "Ford" markasi: tam kelime GECER, alt-dize ELENIR.
GECMELI_FORD = [
    "Ford Focus orta konsol duzenleyici",
    "ford fiesta debriyaj pedali",          # kucuk harf
    "FORD Transit kapi tutamaci",           # buyuk harf
    "Kapak (Ford Focus icin)",              # parantez/kelime-ortasi degil
    "Ford-Focus vites korukleme",           # tire ile sinir
    "yeni ford",                            # baslik sonu
]
ELENMELI_FORD = [
    "Oxford pen holder",                    # alt-dize: ...ford...
    "I can afford this bracket",            # alt-dize: af-ford
    "Food container lid",                   # hic ilgisiz
    "Stanford lab mount",                   # alt-dize
    "Bradford bike clip",                   # alt-dize
    "fordable box",                         # kelime-ici (ford + able)
]
for t in GECMELI_FORD:
    check("Ford GECMELI: %r" % t, gec(t, "Ford") is True)
for t in ELENMELI_FORD:
    check("Ford ELENMELI: %r" % t, gec(t, "Ford") is False)

# Turkce-duyarli buyuk/kucuk: "BMW" vs govde; ve Turkce I/İ katmani
check("BMW tam kelime gecer", gec("BMW e46 far braketi", "BMW") is True)
check("BMW alt-dize elenir", gec("ABMWX rastgele", "BMW") is False)

# Cok kelimeli marka: "Alfa Romeo" tam ifade
check("Alfa Romeo gecer", gec("Alfa Romeo Giulia kalorifer", "Alfa Romeo") is True)
check("Alfa (tek) Romeosuz gecmez-degil", gec("Alfa Romeo Giulia", "Alfa") is True)  # "Alfa" tek kelime de var
check("Romeo baska baglamda elenir", gec("Romeo and Juliet statue", "Alfa Romeo") is False)

# Kisa/bos marka -> filtre uygulanmaz (asiri eleme onlenir): True
check("bos marka filtre yok", gec("herhangi baslik", "") is True)
check("tek harf marka filtre yok", gec("X-wing", "X") is True)

# Turkce karakterli marka kelime siniri (ı ç ş): "Şahin" govde icinde degilse elenir
check("Turkce marka tam kelime", gec("Şahin torpido kapagi", "Şahin") is True)
check("Turkce marka alt-dize elenir", gec("Kırşahinler kutu", "Şahin") is False)

# --- 1b. TUMU-BUYUK LATIN MARKA ADI (2026-08-04 kusuru) -----------------------
# KUSUR: tr_lower 'I'->'ı' cevirir (Turkce'de DOGRU); ama TUMU-BUYUK yazilmis LATIN marka
# adinda YANLIS -> 'NISSAN' -> 'nıssan', 'nissan' ile eslesmez. Canlida IKI KEZ goruldu
# (Nissan x MakerWorld, Nissan x Printables). Zarar tesadufen 0 kaldi; alarm YOKTU.
# FIX: marka_katlamalari() — Turkce katlama HER ZAMAN, latin katlama marka adinda 'ı'/'İ'
# YOKSA EK OLARAK denenir. Asagida IKI YON de nobetlenir (tek yon = olu nobetci).
# DIKKAT: yalnizca marka adinda 'I' GECEN markalar kusurluydu ('I'->'ı'). 'SKODA'/'BMW'
# gibi I'siz markalar ESKIDEN DE calisiyordu -> onlar POZITIF degil KONTROL vakasidir
# (asagida ayri). Kusur vakasini I'siz markayla karistirmak mutasyon kanitini korlestirir.
POZITIF_BUYUK = [                                # ONCE KIRMIZI idi (hepsi False donuyordu)
    ("NISSAN GTR arka klips", "nissan"),
    ("MITSUBISHI Lancer torpido klipsi", "mitsubishi"),
    ("FIAT Egea konsol kapagi", "fiat"),
    ("MINI Cooper bardaklik", "mini"),
    ("CITROEN C3 kapi tutamaci", "citroen"),
]
for t, m in POZITIF_BUYUK:
    check("TUMU-BUYUK latin marka GECMELI: %r ~ %r" % (t, m), gec(t, m) is True)

# KONTROL: 'I' TASIMAYAN TUMU-BUYUK marka eskiden de geciyordu, hala gecmeli.
KONTROL_BUYUK = [("SKODA Octavia menteşe", "skoda"), ("FORD Transit kapak", "ford"),
                 ("BMW E46 far braketi", "bmw")]
for t, m in KONTROL_BUYUK:
    check("KONTROL (I'siz) TUMU-BUYUK marka GECMELI: %r ~ %r" % (t, m), gec(t, m) is True)

# Karisik/kucuk yazim REGRESYONU: eskiden de calisiyordu, hala calismali.
check("regr: karisik yazim", gec("Nissan GTR arka klips", "nissan") is True)
check("regr: kucuk yazim", gec("nissan gtr arka klips", "NISSAN") is True)
# Alt-dize gurultusu HALA elenmeli (gevsetme kelime-sinirini DELMEDI).
check("regr: alt-dize NISSAN icinde", gec("UNISSANO parca", "nissan") is False)

# NEGATIF NOBET — Turkce I/ı ayrimi KORUNUYOR mu? (tek yonlu test = olu nobetci)
# 'kısa' (noktasiz ı) ile 'kisa' (noktali i) FARKLI kelimelerdir; eslesmemeli.
# Bu iddia, "aksani soy / ı->i normalize et" seklindeki NAIF fixi KIRMIZI yakar.
check("TR ayrim: 'kısa kollu' ~ 'kisa' ESLESMEMELI",
      gec("kısa kollu kutu", "kisa") is False)
check("TR ayrim: 'kisa devre' ~ 'kısa' ESLESMEMELI",
      gec("kisa devre kapagi", "kısa") is False)
check("TR ayrim: 'ışıklı panel' ~ 'isikli' ESLESMEMELI",
      gec("ışıklı panel", "isikli") is False)
# Turkce katlama HALA calisiyor: TUMU-BUYUK Turkce sozcuk -> Turkce okunusuyla eslesir.
check("TR katlama: 'IŞIK lamba' ~ 'ışık' ESLESMELI", gec("IŞIK lamba", "ışık") is True)
# Marka adinda 'İ' varsa latin katlama DENENMEZ -> Turkce semantik bozulmaz.
check("TR ayrim: 'ISTANBUL plaka' ~ 'İstanbul' ESLESMEMELI",
      gec("ISTANBUL plaka", "İstanbul") is False)

# --- 1c. KIRMIZI-MUTASYON (defect 1) ------------------------------------------
# Mutantlar CANLI dosyaya DOKUNMAZ; burada birebir yeniden yazilir ve KIRMIZI yakmalari
# olculur. Mutasyon kaniti yeniden-uretilebilir olsun diye surucu repoda durur.
def _mut_eski_katlama(baslik, marka):
    """MUTANT 1 = FIX ONCESI hal (yalniz tr_lower). POZITIF_BUYUK vakalarini KACIRMALI."""
    m = pr.tr_lower(marka).strip()
    if len(m) < 2:
        return True
    return re.search(r"\b%s\b" % re.escape(m), pr.tr_lower(baslik), re.UNICODE) is not None


def _mut_aksan_soy(baslik, marka):
    """MUTANT 2 (NAIF ALTERNATIF FIX) = 'ı'yi 'i'ye katla, yani Turkce ayrimi YOK ET.
    POZITIF vakalari GECIRIR ama TR-ayrim vakalarini yanlislikla ESLESTIRIR -> KIRMIZI."""
    def katla(s):
        return (s or "").replace("İ", "i").replace("I", "i").lower().replace("ı", "i")
    m = katla(marka).strip()
    if len(m) < 2:
        return True
    return re.search(r"\b%s\b" % re.escape(m), katla(baslik), re.UNICODE) is not None


def _mut_kontrol(baslik, marka):
    """KONTROL MUTANT = davranissal olarak CANLI kodun AYNISI (latin katlamada 'I'->'i'
    Python varsayilani yerine ACIKCA yazildi). YESIL KALMALI — kalmiyorsa batarya
    davranisi degil kaynak metnini olcuyor demektir."""
    def tr(s):
        return (s or "").replace("İ", "i").replace("I", "ı").lower()

    def lat(s):
        return (s or "").replace("İ", "i").replace("I", "i").lower()
    ham = marka or ""
    ciftler = [(tr(ham).strip(), tr)]
    if "ı" not in ham and "İ" not in ham:
        ciftler.append((lat(ham).strip(), lat))
    if len(ciftler[0][0]) < 2:
        return True
    for m, katla in ciftler:
        if re.search(r"\b%s\b" % re.escape(m), katla(baslik), re.UNICODE):
            return True
    return False


TR_AYRIM = [("kısa kollu kutu", "kisa"), ("kisa devre kapagi", "kısa"),
            ("ışıklı panel", "isikli"), ("ISTANBUL plaka", "İstanbul")]

# MUT-1 KIRMIZI kaniti: eski katlama TUMU-BUYUK vakalarin EN AZ birini kacirmali.
_m1_kacan = [t for t, m in POZITIF_BUYUK if _mut_eski_katlama(t, m) is not True]
check("MUT-1 (eski katlama) TUM pozitif vakalari KACIRMALI", len(_m1_kacan) == len(POZITIF_BUYUK))
check("MUT-1 canli kod YESIL", all(gec(t, m) is True for t, m in POZITIF_BUYUK))
# MUT-1 AYIRT EDICI mi: kontrol vakalarini (I'siz marka) mutant da GECIRMELI. Gecirmiyorsa
# mutant her seyi kiriyordur ve "kusuru yakaladi" kaniti degersizdir.
check("MUT-1 ayirt edici (I'siz kontrol vakalari mutantta da YESIL)",
      all(_mut_eski_katlama(t, m) is True for t, m in KONTROL_BUYUK))

# MUT-2 KIRMIZI kaniti: aksan-soyan naif fix TR-ayrim vakalarini yanlis eslestirmeli.
_m2_yanlis = [t for t, m in TR_AYRIM if _mut_aksan_soy(t, m) is True]
check("MUT-2 (aksan-soy) KIRMIZI yakmali", len(_m2_yanlis) > 0)
check("MUT-2 canli kod TR-ayrimi koruyor", all(gec(t, m) is False for t, m in TR_AYRIM))

# KONTROL MUTANT: TUM iddialarda canli kodla AYNI cevabi vermeli -> YESIL kalir.
_kontrol_sapma = [(t, m) for t, m in (POZITIF_BUYUK + TR_AYRIM)
                  if _mut_kontrol(t, m) != gec(t, m)]
check("KONTROL MUTANT YESIL kalmali (sapma yok)", not _kontrol_sapma)

# --- 1d. KOSULLU MERCH: logosuz 2D siluet serbest, logo/wordmark HALA elenir ---
# KUSUR 3: "wall art"/"wall decoration" kosulsuz eliyordu -> LOGOSUZ gercek siluet de
# eleniyor, elle kurtariliyordu. FIX: COP_MERCH_KOSULLU — yalniz logo/wordmark sinyaliyle eler.
# 🚫 Politika (2026-07-20) DELINMEDI: logo/wordmark tasiyan HALA elenir (asagida nobetlenir).
check("kosullu: logosuz siluet GECER", pr.is_merch("Nissan GTR wall art") is False)
check("kosullu: 'wall decoration' logosuz GECER",
      pr.is_merch("Skyline silhouette wall decoration") is False)
check("kosullu: LOGO + wall art ELENIR", pr.is_merch("Nissan logo wall art") is True)
check("kosullu: EMBLEM + wall decoration ELENIR",
      pr.is_merch("Nissan emblem wall decoration") is True)
check("kosullu: WORDMARK + wall art ELENIR", pr.is_merch("Nissan wordmark wall art") is True)
check("kosullu: LETTERING + wall art ELENIR", pr.is_merch("Nissan lettering wall art") is True)
check("kosullu: logolu wall art populerlik DELMEZ",
      pr.is_nobypass("Nissan logo wall art") is True)
# KONTROL: kosulsuz merch listesi DEGISMEDI (gevsetme sadece duvar-susuna dokundu).
for t in ("BMW keychain", "Audi keyring", "Ford anahtarlik", "VW wall plaque",
          "Opel trophy", "Seat fridge magnet", "Renault sticker"):
    check("kosulsuz merch HALA elenir: %r" % t, pr.is_merch(t) is True)
check("logo tek basina HALA elenir", pr.is_logo("Nissan emblem") is True)


def _mut_kosulsuz_merch(name):
    """MUTANT 3 = FIX ONCESI hal: kosullu terimler kosulsuz listede. Logosuz siluet
    vakasini ELER -> KIRMIZI."""
    n = " " + (name or "").lower() + " "
    return any(c in n for c in (pr.COP_MERCH + pr.COP_MERCH_KOSULLU))


def _mut_merch_kontrol(name):
    """KONTROL MUTANT = canli is_merch ile ayni, sadece kosulsuz listeye fikstyurde HIC
    gecmeyen bir terim eklendi. YESIL kalmali."""
    n = " " + (name or "").lower() + " "
    if any(c in n for c in (pr.COP_MERCH + ("bobblehead",))):
        return True
    if any(c in n for c in pr.COP_MERCH_KOSULLU):
        return pr.is_logo(name) or pr.is_wordmark(name)
    return False


MERCH_TEMIZ = ["Nissan GTR wall art", "Skyline silhouette wall decoration"]
MERCH_KIRLI = ["Nissan logo wall art", "Nissan emblem wall decoration",
               "Nissan wordmark wall art", "BMW keychain", "VW wall plaque"]
check("MUT-3 (kosulsuz merch) KIRMIZI yakmali",
      all(_mut_kosulsuz_merch(t) is True for t in MERCH_TEMIZ))
check("MUT-3 canli kod temizi GECIRIYOR", all(pr.is_merch(t) is False for t in MERCH_TEMIZ))
check("MUT-3 canli kod kirliyi ELIYOR", all(pr.is_merch(t) is True for t in MERCH_KIRLI))
check("KONTROL MUTANT (merch) YESIL kalmali",
      all(_mut_merch_kontrol(t) == pr.is_merch(t) for t in MERCH_TEMIZ + MERCH_KIRLI))

# --- 2. Iki arama araci da fonksiyonu KULLANIYOR mu (kaynak-grep) --------------
for f in ("printables-ara.py", "thing-ara.py"):
    src = open(os.path.join(DIR, f), encoding="utf-8").read()
    check("%s marka_kelime_gecer cagiriyor" % f, "marka_kelime_gecer" in src)
    check("%s --tam-kelime bayragi var" % f, "--tam-kelime" in src)

# --- 2b. CAPA: fix gercekten CANLI kaynakta ve TEK KOPYA mi? -------------------
# Capa TAM BIR KEZ eslesmeli — ikinci kopya = ikiz tanim = sessiz ayrisma riski.
_api_src = open(os.path.join(DIR, "printables-api.py"), encoding="utf-8").read()
for capa in ("def latin_lower(", "def marka_katlamalari(", "COP_MERCH_KOSULLU = (",
             "COP_WORDMARK = (", "def is_wordmark(", "def obj_bbox("):
    check("printables-api.py capa TAM BIR KEZ: %r" % capa, _api_src.count(capa) == 1)
# tr_lower Turkce yuzeyi icin DEGISMEDEN kalmali (denetim-kapisi/yayin-ic-dil ona bagli).
check("tr_lower Turkce kurali korunuyor",
      'replace("İ", "i").replace("I", "ı").lower()' in _api_src)

# makerworld-ara.py kendi katlama KOPYASINI tutmamali (ikiz tanim tuzagi).
_mw_src = open(os.path.join(DIR, "makerworld-ara.py"), encoding="utf-8").read()
check("makerworld-ara.py kendi _tr_lower kopyasini TUTMUYOR", "def _tr_lower" not in _mw_src)
check("makerworld-ara.py ortak katlamayi cagiriyor TAM BIR KEZ",
      _mw_src.count("_pr.marka_katlamalari(") == 1)

# makerworld-ara.marka_geciyor DAVRANIS nobeti (kaynak-grep tek basina yeterli degil).
_mw_spec = importlib.util.spec_from_file_location("mw_ara", os.path.join(DIR, "makerworld-ara.py"))
_mw = importlib.util.module_from_spec(_mw_spec)
_mw_spec.loader.exec_module(_mw)
check("MW: 'NISSAN GTR' ~ 'nissan' GECER", _mw.marka_geciyor("nissan", "NISSAN GTR") is True)
check("MW: karisik yazim regresyonu", _mw.marka_geciyor("nissan", "Nissan GTR") is True)
check("MW: alt-dize HALA elenir", _mw.marka_geciyor("ford", "Oxford box") is False)
check("MW: TR ayrimi korunuyor", _mw.marka_geciyor("kisa", "kısa kollu kutu") is False)
check("MW: bos marka False", _mw.marka_geciyor("", "herhangi") is False)

if FAILS:
    print("\n%d KONTROL KALDI" % len(FAILS), file=sys.stderr)
    sys.exit(1)
print("TEST GECTI")
sys.exit(0)
