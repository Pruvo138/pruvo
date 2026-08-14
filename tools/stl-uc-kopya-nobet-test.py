#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/stl-uc-kopya-nobet.py (SAF FIKSTUR, AG YOK, R2'ye HIC gidilmez).

Yedi vaka (spec: SPEC-stl-r2-eksik.md · H2):
  1. Dort kova dogru sayilir (bilinen 4+2+3+1 dagilimi, gercek dosyalar uzerinde)
  2. HICBIRINDE>0 -> KIRMIZI (rc!=0), esik YOK
  3. SADECE_DRIVE > ESIK -> KIRMIZI
  4. SADECE_DRIVE <= ESIK -> GECER (mesru hasat penceresi kirmizi yakmaz)
  5. SADECE_R2>0 TEK BASINA kirmizi DEGIL (SARI/uyari)
  6. Stub dosya (113 bayt, STL imzasi YOK) gercek STL sayilmaz — hicbir kovaya girmez
  7. R2 listeleme reddedilirse HUKUM=OLCULEMEDI + rc!=0 (sahte YESIL yok)

Fikstur dosyalari GECICI dizinde uretilir ve her vakadan sonra SILINIR (disk emri:
"ureten temizler"). Ag cagrisi YOKTUR: R2 listesi sahte istemciyle beslenir.

    python3 tools/stl-uc-kopya-nobet-test.py             # kabul testi (0 = gecti)
    python3 tools/stl-uc-kopya-nobet-test.py --mutasyon  # oldurucu mutant bataryasi

Ikisi de DETERMINISTIK ve ag-siz; ikisi de `.github/workflows/nobet.yml` (SERIT B, push
tetikli) icinde FIILEN kosar. Mutasyon kolu ci-kapsam-test.py'ye acikca beyan edilir ki
CI cagrisi silinirse kapi KIRMIZI yansin (beyan edilmeyen alt kume kapiya GORUNMEZ):
# CI-ALT-KUME: --mutasyon
"""

import importlib.util
import os
import shutil
import struct
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
HEDEF_AD = "stl-uc-kopya-nobet.py"


def _yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


nobet = _yukle(os.path.join(TOOLS, HEDEF_AD), "nobet_sut")
_gercek_yukleyici = _yukle(os.path.join(TOOLS, "stl-r2-yukle.py"), "syu_test")

STUB_ICERIK = (b"You can only send 300 requests per 5 minutes. Please check "
               b"https://www.thingiverse.com/developers/getting-started")
assert len(STUB_ICERIK) == 113, "stub fiksturu 113 bayt olmali (canlida olculen boyut)"


class SahteYukleyici:
    """`stl-r2-yukle.py`'nin fikstur kilifi: anahtar turetme GERCEK fonksiyondan gelir
    (ikiz tanim YOK), yalniz 6/10 MB'lik canli JSON okumalari fikstur degerleriyle
    degistirilir — test AG'a da 26.781'lik katalogа da bagli kalmaz."""

    KAYNAKLAR = "/gecersiz/yol/olmayan-kaynak-kaydi.json"

    def __init__(self, idler):
        self._idler = idler

    def urun_idleri(self):
        return self._idler

    def kaynak_esleme_yukle(self, yol):
        return {}, set()

    def siniflandir(self, *a, **k):
        return _gercek_yukleyici.siniflandir(*a, **k)


def binary_stl(ucgen=2):
    """Gecerli binary STL baytlari: 80 bayt baslik + ucgen sayisi + 50 bayt/ucgen."""
    return b"P" * 80 + struct.pack("<I", ucgen) + b"\x00" * (50 * ucgen)


def fikstur_kur(dosyalar):
    """dosyalar: {ad: bayt}. Gecici dizin doner (cagiran SILER)."""
    dizin = tempfile.mkdtemp(prefix="stl-uc-kopya-fix-")
    for ad, icerik in dosyalar.items():
        with open(os.path.join(dizin, ad), "wb") as f:
            f.write(icerik)
    return dizin


VAKALAR = []


def vaka(ad):
    def sar(fn):
        VAKALAR.append((ad, fn))
        return fn
    return sar


# ------------------------------------------------------------------ 1) dort kova

@vaka("1) dort kova dogru sayilir (4+2+3+1) — stub sayima GIRMEZ")
def _v1():
    idler = {"u%d" % i for i in range(1, 12)}
    dosyalar = {"u%d--a.stl" % i: binary_stl() for i in range(1, 11)}
    dosyalar["u11--stub.stl"] = STUB_ICERIK          # Drive'da var ama STL DEGIL
    dizin = fikstur_kur(dosyalar)
    try:
        # u1..u4 = her ikisinde · u5,u6 = sadece R2 · u7,u8,u9 = sadece Drive · u10 = hicbirinde
        r2 = {"stl/u%d/a.stl" % i for i in range(1, 7)}
        drive = {"u%d--a.stl" % i for i in (1, 2, 3, 4, 7, 8, 9)} | {"u11--stub.stl"}
        kayitlar = nobet.yerel_tara(dizin, yukleyici=SahteYukleyici(idler))
        sonuc = nobet.kovala(kayitlar, r2, drive)
        s = sonuc["sayim"]
        beklenen = {"HER_IKISINDE": 4, "SADECE_R2": 2, "SADECE_DRIVE": 3, "HICBIRINDE": 1}
        if s != beklenen:
            return "kovalar beklenenden farkli: %s (beklenen %s)" % (s, beklenen)
        if len(sonuc["stub"]) != 1:
            return "STUB=%d (1 olmali; 113 baytlik rate-limit metni)" % len(sonuc["stub"])
        if "u11--stub.stl" in sum(sonuc["listeler"].values(), []):
            return "stub dosya bir KOVAYA girdi (gercek STL sayildi)"
        return None
    finally:
        shutil.rmtree(dizin, ignore_errors=True)


# ------------------------------------------------------------------ 2) HICBIRINDE kirmizi

@vaka("2) HICBIRINDE>0 -> KIRMIZI (rc!=0), esik YOK")
def _v2():
    sayim = {"HER_IKISINDE": 900, "SADECE_R2": 0, "SADECE_DRIVE": 0, "HICBIRINDE": 1}
    durum, sebepler, rc = nobet.hukum(sayim, esik=20)
    if durum != "KIRMIZI" or rc == 0:
        return "tek dosyalik tek-kopya kaybi kirmizi YAKMADI: durum=%s rc=%d" % (durum, rc)
    if not any("HICBIRINDE" in s for s in sebepler):
        return "kirmizi sebebi HICBIRINDE'yi anmiyor: %s" % sebepler
    return None


# ------------------------------------------------------------------ 3) esik ustu kirmizi

@vaka("3) SADECE_DRIVE > ESIK -> KIRMIZI")
def _v3():
    sayim = {"HER_IKISINDE": 572, "SADECE_R2": 0, "SADECE_DRIVE": 183, "HICBIRINDE": 0}
    durum, sebepler, rc = nobet.hukum(sayim, esik=20)
    if durum != "KIRMIZI" or rc == 0:
        return ("canli ariza dagilimi (SADECE_DRIVE=183, esik=20) kirmizi YAKMADI: "
                "durum=%s rc=%d" % (durum, rc))
    if not any("SADECE_DRIVE" in s for s in sebepler):
        return "kirmizi sebebi SADECE_DRIVE'i anmiyor: %s" % sebepler
    return None


# ------------------------------------------------------------------ 4) esik alti gecer

@vaka("4) SADECE_DRIVE <= ESIK -> GECER (mesru hasat penceresi)")
def _v4():
    for n in (0, 19, 20):
        sayim = {"HER_IKISINDE": 572, "SADECE_R2": 0, "SADECE_DRIVE": n, "HICBIRINDE": 0}
        durum, _sebepler, rc = nobet.hukum(sayim, esik=20)
        if rc != 0 or durum == "KIRMIZI":
            return ("SADECE_DRIVE=%d (esik=20) mesru pencere olmasina ragmen kirmizi: "
                    "durum=%s rc=%d" % (n, durum, rc))
    return None


# ------------------------------------------------------------------ 5) SADECE_R2 sari

@vaka("5) SADECE_R2>0 TEK BASINA kirmizi DEGIL (SARI/uyari)")
def _v5():
    sayim = {"HER_IKISINDE": 572, "SADECE_R2": 7, "SADECE_DRIVE": 0, "HICBIRINDE": 0}
    durum, sebepler, rc = nobet.hukum(sayim, esik=20)
    if rc != 0:
        return "SADECE_R2 tek basina rc bozdu (rc=%d) — musteri etkilenmiyor" % rc
    if durum != "SARI":
        return "SADECE_R2>0 SARI degil '%s' verdi (uyari kaybolur)" % durum
    if not sebepler:
        return "SARI hali sebepsiz basildi (uyari gorunmez olur)"
    return None


# ------------------------------------------------------------------ 6) stub imzasi

@vaka("6) stub (113 bayt, imzasiz) gercek STL SAYILMAZ; gecerli STL/3MF sayilir")
def _v6():
    dosyalar = {
        "stub.stl": STUB_ICERIK,
        "binary.stl": binary_stl(3),
        "ascii.stl": b"solid test\nfacet normal 0 0 0\nendsolid test\n",
        "paket.3mf": b"PK\x03\x04" + b"\x00" * 200,
        "sahte.3mf": b"BU BIR ZIP DEGIL" + b"\x00" * 200,
        "bos.stl": b"",
    }
    dizin = fikstur_kur(dosyalar)
    try:
        beklenen = {"stub.stl": False, "binary.stl": True, "ascii.stl": True,
                    "paket.3mf": True, "sahte.3mf": False, "bos.stl": False}
        for ad, bekle in beklenen.items():
            varan = nobet.stl_gecerli(os.path.join(dizin, ad))
            if varan != bekle:
                return "stl_gecerli(%s)=%s (beklenen %s)" % (ad, varan, bekle)
        # sayima girmedigini de dogrula: stub tek basina, Drive'da var, R2'de yok
        idler = {"u1"}
        dizin2 = fikstur_kur({"u1--stub.stl": STUB_ICERIK})
        try:
            kayitlar = nobet.yerel_tara(dizin2, yukleyici=SahteYukleyici(idler))
            sonuc = nobet.kovala(kayitlar, set(), {"u1--stub.stl"})
            if sonuc["sayim"]["SADECE_DRIVE"] != 0:
                return "stub dosya SADECE_DRIVE olarak sayildi (gercek STL sayilmis)"
            if len(sonuc["stub"]) != 1:
                return "stub ayri raporlanmadi"
        finally:
            shutil.rmtree(dizin2, ignore_errors=True)
        return None
    finally:
        shutil.rmtree(dizin, ignore_errors=True)


# ------------------------------------------------------------------ 7) fail-closed

@vaka("7) R2 listeleme REDDEDILIRSE HUKUM=OLCULEMEDI + rc!=0 (sahte YESIL yok)")
def _v7():
    class SahteRed(Exception):
        pass

    def patlayan_istemci():
        raise SahteRed("An error occurred (AccessDenied) when calling the ListObjectsV2 "
                       "operation: Access Denied")

    idler = {"u1", "u2"}
    # FAIL-OPEN mutanti YAKALANSIN diye fikstur bilerek "her sey yolunda" gorunumlu:
    # R2 bos donseydi SADECE_DRIVE=2 (<esik) + HICBIRINDE=0 -> hukum YESIL, rc=0 olurdu.
    dizin = fikstur_kur({"u1--a.stl": binary_stl(), "u2--a.stl": binary_stl()})
    drive = fikstur_kur({"u1--a.stl": binary_stl(), "u2--a.stl": binary_stl()})
    satirlar = []
    try:
        rc = nobet.kos(dizin, drive, esik=20, istemci_fn=patlayan_istemci,
                       yaz=satirlar.append, yukleyici=SahteYukleyici(idler))
    finally:
        shutil.rmtree(dizin, ignore_errors=True)
        shutil.rmtree(drive, ignore_errors=True)
    cikti = "\n".join(satirlar)
    if rc == 0:
        return "R2 reddi rc=0 ile gecti (FAIL-OPEN — sahte yesil): %s" % cikti
    if "OLCULEMEDI" not in cikti:
        return "R2 reddinde OLCULEMEDI basilmadi: %s" % cikti
    for kova in ("HER_IKISINDE", "SADECE_DRIVE"):
        if kova + "=" in cikti:
            return "olculemeyen kosumda kova SAYISI basildi (%s) — sahte sayi" % kova
    # `--durum` modu da olculemeyeni yesil GOSTERMEMELI
    dizin = fikstur_kur({"u1--a.stl": binary_stl()})
    drive = fikstur_kur({"u1--a.stl": binary_stl()})
    try:
        rc2 = nobet.kos(dizin, drive, esik=20, istemci_fn=patlayan_istemci,
                        durum_modu=True, yaz=lambda *_a: None,
                        yukleyici=SahteYukleyici(idler))
    finally:
        shutil.rmtree(dizin, ignore_errors=True)
        shutil.rmtree(drive, ignore_errors=True)
    if rc2 == 0:
        return "--durum modu olculemeyen kosumu rc=0 ile yesil gosterdi"
    return None


# ------------------------------------------------------------------ kabul kosumu

def kabul_kos():
    hatalar = []
    for ad, fn in VAKALAR:
        try:
            hata = fn()
        except Exception as e:                                        # noqa: BLE001
            hata = "COKTU: %s: %s" % (type(e).__name__, e)
        if hata:
            hatalar.append((ad, hata))
            print("  FAIL  %s\n        %s" % (ad, hata))
        else:
            print("  PASS  %s" % ad)
    print("\nVAKA=%d/%d" % (len(VAKALAR) - len(hatalar), len(VAKALAR)))
    if hatalar:
        print("SONUC: BASARISIZ ❌ (%d vaka)" % len(hatalar))
        return 1
    print("SONUC: TUM VAKALAR GECTI ✅")
    return 0


# ------------------------------------------------------------------ mutasyon bataryasi

YESIL_IZ = "SONUC: TUM VAKALAR GECTI"
KIRMIZI_IZ = "SONUC: BASARISIZ"

# (ad, aranan, yerine, KIRMIZI_beklenir_mi)
MUTANTLAR = [
    ("N1) HICBIRINDE kolu KALKTI (tek-kopya kaybi kirmizi yakmiyor)",
     '    if sayim["HICBIRINDE"] > 0:',
     "    if False:",
     True),
    ("N2) esik SONSUZA cekildi (SADECE_DRIVE hic kirmizi yakmaz)",
     '    if sayim["SADECE_DRIVE"] > esik:',
     '    if sayim["SADECE_DRIVE"] > float("inf"):',
     True),
    ("N3) stub dosya GERCEK STL sayildi (imza kapisi dustu)",
     '        if not kayit["gecerli"]:',
     "        if False:",
     True),
    ("N4) R2 reddinde 0 basildi (FAIL-OPEN — sahte yesil)",
     '        raise OlcumHatasi("R2 listeleme basarisiz/reddedildi (%s: %s)"\n'
     '                          % (type(e).__name__, str(e)[:200])) from e',
     "        return set()",
     True),
    ("N5) KONTROL MUTANTI (davranis DEGISMEZ) — YESIL kalmali",
     "    stub = []",
     "    stub = list()",
     False),
]


def ayna_kur():
    """tools/ symlink aynasi -> gecici kok. Canli agaca YAZILMAZ."""
    kok = tempfile.mkdtemp(prefix="stl-uc-kopya-mut-")
    os.makedirs(os.path.join(kok, "tools"))
    for ad in os.listdir(TOOLS):
        kaynak = os.path.join(TOOLS, ad)
        if os.path.isfile(kaynak):
            os.symlink(kaynak, os.path.join(kok, "tools", ad))
    return kok


def mutasyon_uygula(kok, eski, yeni):
    hedef = os.path.join(kok, "tools", HEDEF_AD)
    with open(os.path.join(TOOLS, HEDEF_AD), encoding="utf-8") as f:
        src = f.read()
    if src.count(eski) != 1:
        return "hedef metin kaynakta %d kez geciyor (1 olmali)" % src.count(eski)
    mut = src.replace(eski, yeni, 1)
    if mut == src:
        return "mutasyon metni DEGISTIRMEDI"
    os.unlink(hedef)
    with open(hedef, "w", encoding="utf-8") as f:
        f.write(mut)
    with open(hedef, encoding="utf-8") as f:
        diskte = f.read()
    if diskte != mut or eski in diskte:
        return "mutasyon diske UYGULANMADI"
    return None


def kabul_altkosum(kok):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, os.path.join(kok, "tools",
                                                        os.path.basename(__file__))],
                          capture_output=True, text=True, env=env, timeout=600)


def mutasyon_kos():
    import hashlib
    with open(os.path.join(TOOLS, HEDEF_AD), "rb") as f:
        ozet = hashlib.sha256(f.read()).hexdigest()
    print("KANONIK_KAYNAK=%s sha256=%s" % (HEDEF_AD, ozet))

    fails = []
    print("\n=== KONTROL KOSUMU (mutasyonsuz ayna) — YESIL olmali ===")
    kok = ayna_kur()
    r = kabul_altkosum(kok)
    temiz = r.returncode == 0 and YESIL_IZ in r.stdout
    print("  %s  mutasyonsuz ayna (rc=%d)" % ("PASS" if temiz else "FAIL", r.returncode))
    if not temiz:
        fails.append("mutasyonsuz ayna yesil degil")
        print(r.stdout[-2000:])
        print(r.stderr[-1000:])
    shutil.rmtree(kok, ignore_errors=True)

    print("\n=== MUTANTLAR ===")
    kirmizi_yanan = 0
    beklenen = sum(1 for m in MUTANTLAR if m[3])
    kontrol = None
    for ad, eski, yeni, kirmizi_bekle in MUTANTLAR:
        kok = ayna_kur()
        hata = mutasyon_uygula(kok, eski, yeni)
        if hata:
            print("  FAIL  %s -> UYGULANAMADI: %s" % (ad, hata))
            fails.append(ad)
            shutil.rmtree(kok, ignore_errors=True)
            continue
        r = kabul_altkosum(kok)
        yesil, kirmizi = YESIL_IZ in r.stdout, KIRMIZI_IZ in r.stdout
        if kirmizi_bekle:
            ok = kirmizi and r.returncode != 0
            if ok:
                kirmizi_yanan += 1
            etiket = ("KIRMIZI ✅" if ok else
                      ("COKTU (kirmiziyla karismaz)" if not yesil and not kirmizi
                       else "YESIL ❌ MUTANT SAG KALDI"))
            print("  %s  %s -> %s" % ("PASS" if ok else "FAIL", ad, etiket))
            if not ok:
                fails.append(ad)
                print("        rc=%d stderr: %s" % (r.returncode, (r.stderr or "")[-300:]))
        else:
            kontrol = "YESIL" if (yesil and r.returncode == 0) else "KIRMIZI"
            ok = kontrol == "YESIL"
            print("  %s  %s -> %s" % ("PASS" if ok else "FAIL", ad, kontrol))
            if not ok:
                fails.append(ad + " (kontrol mutanti kirmizi: batarya olcmuyor)")
                print(r.stdout[-1500:])
        shutil.rmtree(kok, ignore_errors=True)

    print("\nMUTANT_KIRMIZI=%d/%d  KONTROL_MUTANT=%s"
          % (kirmizi_yanan, beklenen, kontrol or "KOSULMADI"))
    if fails:
        print("SONUC: MUTASYON KIRMIZI ❌ (%d)" % len(fails))
        return 1
    print("SONUC: MUTASYON YESIL ✅")
    return 0


if __name__ == "__main__":
    if "--mutasyon" in sys.argv:
        sys.exit(mutasyon_kos())
    sys.exit(kabul_kos())
