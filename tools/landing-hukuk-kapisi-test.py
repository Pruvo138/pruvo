#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL + MUTANT TESTI — tools/landing-hukuk-kapisi.py KURAL A (K389 ④, 13 Eyl 2026).

NEDEN VAR: kapi uzun sure YALNIZ nobet.yml SERIT B'de kostu (yayini BLOKLAMAZ). 8 Eyl'de 1,
12 Eyl'de 4 landing "gida" temasini sinir cumlesi (sertifika / kapsam disi) OLMADAN tasiyip
yayina cikti. Kapi artik deploy.yml `serit-a3`te bloklayicidir; bu test kapinin o sinifi
GERCEKTEN yakaladigini her push'ta yeniden olcer ("kapi bagli" beyani yetmez).

YONTEM (canli kaynaga DOKUNMAZ, diske yalniz gecici dizine yazar):
  * Kapi dosyasi GECICI dizine KOPYALANIR (her kosumda canli kaynaktan -> kopya bayatlamaz).
    Kapi `import sayfalar`i KENDI dizininden yapar; gecici dizine SAHTE bir `sayfalar.py`
    konur. Sahte modul GERCEK tools/sayfalar.py'yi yukler ve CONTENT_PAGES'i kipe gore
    degistirir — yani mutant GERCEK katalogun GERCEK govdesinde yasar, sentetik metinde degil.
  * Hedef sayfa SECILMEZ, TURETILIR: slug sirasiyla, govdesinde "gida" + sinir ifadesi gecen
    VE sinir cumleleri silindikten sonra hala "gida" tasiyan ILK sayfa (deterministik; rastgele
    secim YOK -> ayni SHA ayni hedefi verir).

IDDIALAR:
  K0 KONTROL      — degistirilmemis CONTENT_PAGES: rc=0 · "ihlal: 0" · "YESIL" ·
                    taranan = gercek sayfa sayisi · KURAL A kapsami >= 1.
  M1 SINIR SILINDI— hedef govdeden sinir cumleleri cikarilir: rc!=0 · "ihlal: 1" ·
                    "KIRMIZI <hedef> -> KURAL A" satiri ADIYLA basilir.
  M2 BOS KATALOG  — CONTENT_PAGES bos: rc!=0 (fail-closed, sessiz yesil YOK).
  M3 RENDER HATASI— hedef uretici istisna atar: rc!=0 (fail-closed).
  O  ONCUL        — mutant fiksturu gercekten KURAL A kapsaminda ve sinirsiz (degilse M1
                    anlamsiz yesil verirdi -> test KIRMIZI, OLCULEMEDI basar).

Kosum: python3 tools/landing-hukuk-kapisi-test.py      (offline, stdlib, ag yok, ~1 s)
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARAC = os.path.join(KOK, "tools")
KAPI_ADI = "landing-hukuk-kapisi.py"
BU_DOSYA = os.path.abspath(__file__)

IDDIA = [0]
HATA = []


def bekle(kosul, mesaj):
    IDDIA[0] += 1
    if not kosul:
        HATA.append(mesaj)
        print("  ❌ %s" % mesaj)
    else:
        print("  ✅ %s" % mesaj)
    return bool(kosul)


def _kapi_modulu():
    """Kapinin KENDI sabitlerini (KAPSAM_IFADELERI, kucult, etiketsiz) yukler — ikiz tanim yok."""
    spec = importlib.util.spec_from_file_location("_lhk_kapi", os.path.join(ARAC, KAPI_ADI))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sinir_sil(html):
    """Govdeden sinir ifadesi (KAPSAM_IFADELERI) tasiyan cumleleri cikarir.

    Eslesme kapinin kucultmesi uzerinde yapilir; kucultme uzunluk koruyorsa ayni araliklar
    ozgun metinden silinir. Korumuyorsa None doner (hedef aday DEGIL).
    """
    kapi = _kapi_modulu()
    ifadeler = "|".join(re.escape(k) for k in kapi.KAPSAM_IFADELERI)
    desen = re.compile(r"[^.!?<>]*(?:%s)[^.!?<>]*[.!?]?" % ifadeler)
    metin = html
    for _ in range(50):
        kucuk = kapi.kucult(metin)
        if len(kucuk) != len(metin):
            return None
        araliklar = [(m.start(), m.end()) for m in desen.finditer(kucuk)]
        if not araliklar:
            return metin
        for bas, son in reversed(araliklar):
            metin = metin[:bas] + metin[son:]
    return None


def gercek_sayfalar():
    sys.path.insert(0, ARAC)
    spec = importlib.util.spec_from_file_location("_sayfalar_gercek", os.path.join(ARAC, "sayfalar.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CONTENT_PAGES


SAHTE_SAYFALAR = '''# -*- coding: utf-8 -*-
# GECICI SAHTE sayfalar.py (landing-hukuk-kapisi-test.py uretti) — repoya GIRMEZ.
import importlib.util, os, sys
sys.dont_write_bytecode = True
ARAC = %(arac)r
sys.path.insert(1, ARAC)
_s = importlib.util.spec_from_file_location("_sayfalar_gercek", os.path.join(ARAC, "sayfalar.py"))
_g = importlib.util.module_from_spec(_s); _s.loader.exec_module(_g)
_t = importlib.util.spec_from_file_location("_lhk_test", %(test)r)
_tm = importlib.util.module_from_spec(_t); _t.loader.exec_module(_tm)
KIP = os.environ.get("LHK_KIP", "")
HEDEF = os.environ.get("LHK_HEDEF", "")

def _patla():
    raise RuntimeError("M3 mutant: uretici bilerek patladi")

def _sarmala(kayit):
    slug, baslik, meta, uretici = kayit
    if slug != HEDEF:
        return kayit
    if KIP == "M1":
        return (slug, baslik, meta, lambda u=uretici: _tm.sinir_sil(u()))
    if KIP == "M3":
        return (slug, baslik, meta, _patla)
    return kayit

if KIP == "K0":
    CONTENT_PAGES = list(_g.CONTENT_PAGES)
elif KIP == "M2":
    CONTENT_PAGES = []
elif KIP in ("M1", "M3"):
    CONTENT_PAGES = [_sarmala(k) for k in _g.CONTENT_PAGES]
else:
    raise SystemExit("bilinmeyen kip %%r" %% KIP)
'''


def kos(gecici, kip, hedef):
    ortam = dict(os.environ)
    ortam["LHK_KIP"] = kip
    ortam["LHK_HEDEF"] = hedef
    ortam["PYTHONDONTWRITEBYTECODE"] = "1"
    s = subprocess.run(
        [sys.executable, os.path.join(gecici, KAPI_ADI)],
        cwd=gecici, env=ortam, capture_output=True, text=True, timeout=300,
    )
    return s.returncode, s.stdout + s.stderr


def main():
    kapi = _kapi_modulu()
    sayfalar = gercek_sayfalar()

    print("O — ONCUL: mutant hedefi turetiliyor")
    hedef = None
    aday = 0
    for slug, _b, _m, uretici in sorted(sayfalar, key=lambda k: k[0]):
        govde = uretici()
        g = kapi.kucult(kapi.etiketsiz(govde))
        if "gıda" not in g or not any(k in g for k in kapi.KAPSAM_IFADELERI):
            continue
        mutant = sinir_sil(govde)
        if mutant is None:
            continue
        mg = kapi.kucult(kapi.etiketsiz(mutant))
        if "gıda" in mg and not any(k in mg for k in kapi.KAPSAM_IFADELERI):
            aday += 1
            if hedef is None:
                hedef = slug
    if not bekle(hedef is not None,
                 "O: KURAL A kapsaminda sinir cumlesi silinebilen aday var (aday=%d, hedef=%s)"
                 % (aday, hedef)):
        print("OLCULEMEDI: mutant fiksturu kurulamadi")
        return 2

    with tempfile.TemporaryDirectory(prefix="lhk-test-") as gecici:
        shutil.copyfile(os.path.join(ARAC, KAPI_ADI), os.path.join(gecici, KAPI_ADI))
        with open(os.path.join(gecici, "sayfalar.py"), "w", encoding="utf-8") as f:
            f.write(SAHTE_SAYFALAR % {"arac": ARAC, "test": BU_DOSYA})

        print("K0 — KONTROL (degistirilmemis katalog)")
        rc, cikti = kos(gecici, "K0", hedef)
        m = re.search(r"taranan landing: (\d+)", cikti)
        a = re.search(r"KURAL A kapsaminda \(gida gecen, muaf olmayan\): (\d+)", cikti)
        bekle(rc == 0, "K0: rc=0 (rc=%d)" % rc)
        bekle("ihlal: 0" in cikti and "YESIL" in cikti, "K0: 'ihlal: 0' + 'YESIL' basildi")
        bekle(bool(m) and int(m.group(1)) == len(sayfalar),
              "K0: taranan = gercek sayfa sayisi (%s / %d)" % (m and m.group(1), len(sayfalar)))
        bekle(bool(a) and int(a.group(1)) >= 1,
              "K0: KURAL A kapsami >= 1 (%s)" % (a and a.group(1)))
        if rc != 0:
            print(cikti)

        print("M1 — SINIR CUMLESI SILINDI (%s)" % hedef)
        rc, cikti = kos(gecici, "M1", hedef)
        bekle(rc != 0, "M1: rc!=0 (rc=%d)" % rc)
        bekle("ihlal: 1" in cikti, "M1: 'ihlal: 1' basildi (yalniz hedef dustu)")
        bekle(("KIRMIZI %s -> KURAL A" % hedef) in cikti,
              "M1: ihlal satiri hedefi ADIYLA basiyor")
        if rc == 0:
            print(cikti)

        print("M2 — BOS KATALOG")
        rc, cikti = kos(gecici, "M2", hedef)
        bekle(rc != 0 and "CONTENT_PAGES bos" in cikti, "M2: rc!=0 + 'CONTENT_PAGES bos' (rc=%d)" % rc)

        print("M3 — RENDER HATASI (%s)" % hedef)
        rc, cikti = kos(gecici, "M3", hedef)
        bekle(rc != 0 and "render edilemedi" in cikti, "M3: rc!=0 + 'render edilemedi' (rc=%d)" % rc)

    print("-" * 70)
    print("IDDIA SAYISI: %d · dusen: %d" % (IDDIA[0], len(HATA)))
    if HATA:
        print("SONUC: KIRMIZI ❌")
        return 1
    print("SONUC: YESIL ✅ — KURAL A sinir cumlesi silinen landing'i kapi ADIYLA durduruyor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
