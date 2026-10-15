#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KABUL TESTI — tools/r2-canli-dogrula.py (kova-genel canli R2 dogrulama).

AG YOK: PATH'in basina SAHTE `npx` konur (wrangler'in 15 Eki 2026'da CANLI OLCULEN
davranisini taklit eder: var -> rc0 "Download complete."; yok -> rc1 "The specified key
does not exist." + 0 baytlik --file; olmayan KOVA -> object get AYNI not-found metni,
bucket info rc1; kimlik hatasi -> rc1 "Authentication failed"). Her vaka kendi gecici
kokunde: sahte urunler.json + stl/ + manifest + sahte R2 deposu (PRUVO_VERI_KOK ile).

VAKALAR
  stl: S1 esit->ESIT · S2 ayni boyut farkli icerik->FARKLI · S3 R2'de yok->YOK ·
       S4 rc!=0 (govde+"Download complete." olsa bile)->asla ESIT · S5 hatali ad->HATALI_AD,
       get CAGRILMAZ · S6 --sil yalniz ESIT'i siler · S7 --sil yokken silme 0 ·
       S8 manifest "esit" dese de R2'de yoksa YOK · S9 olmayan kova->OLCULEMEDI, get yok ·
       S10 --rapor sinif listesi · S11 gecici dizin kosum sonunda silinir
  yok: Y1 gercek not-found->SILINDI_KANITLI · Y2 nesne var->HALA_VAR ·
       Y3 kimlik/ag hatasi->OLCULEMEDI (SILINDI_KANITLI DEGIL) · Y4 kip dosya yazmaz/silmez ·
       Y5 olmayan kova->OLCULEMEDI (SILINDI_KANITLI DEGIL)
MUTANTLAR (her biri >=1 vakayi KIRMIZI yapmali; SURVIVOR=0):
  M1 sha'yi boyuta indir · M2 wrangler rc'yi yok say · M3 --sil sinif kontrolunu kaldir ·
  M4 manifest esitse ESIT say · M5 her get hatasini not-found say · M6 kova on-kapisini kaldir

    python3 tools/r2-canli-dogrula-test.py      # exit 0 = YESIL
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ARAC = os.path.join(TOOLS, "r2-canli-dogrula.py")
KARDESLER = ("stl-r2-yukle.py", "veri_kok.py")
KOVA = "pruvo-ozel"

SAHTE_NPX = r'''#!%s
import os, shutil, sys
a = sys.argv[1:]
r2 = os.environ["FAKE_R2"]
mod = os.environ.get("FAKE_MOD", "normal")
with open(os.environ["FAKE_CAGRI"], "a") as f:
    f.write(" ".join(a) + "\n")
if a[:4] == ["wrangler", "r2", "bucket", "info"]:
    kova = a[4]
    if os.path.isdir(os.path.join(r2, kova)):
        print("Getting info for '%%s'...\nname:                   %%s\nobject_count: 1" %% (kova, kova))
        sys.exit(0)
    print("\x1b[31m✘ [ERROR] A request to the Cloudflare API failed.\x1b[0m\n"
          "  The specified bucket does not exist. [code: 10006]")
    sys.exit(1)
if a[:4] == ["wrangler", "r2", "object", "get"]:
    kova, anahtar = a[4].split("/", 1)
    hedef = a[a.index("--file") + 1]
    kaynak = os.path.join(r2, kova, anahtar)
    if mod == "auth":
        open(hedef, "wb").close()
        print("\x1b[31m✘ [ERROR] A request to the Cloudflare API failed.\x1b[0m\n"
              "  Authentication failed (status: 400) [code: 9106]")
        sys.exit(1)
    if os.path.isfile(kaynak):
        shutil.copyfile(kaynak, hedef)
        print("Downloading ...\nDownload complete.")
        sys.exit(1 if mod == "rc_yalan" else 0)
    open(hedef, "wb").close()   # gercek wrangler: not-found'da da 0 baytlik --file olusturur
    print("Downloading ...\n\x1b[31m✘ [ERROR]\x1b[0m \x1b[1mThe specified key does not exist.\x1b[0m")
    sys.exit(1)
print("sahte npx: bilinmeyen cagri", a)
sys.exit(3)
''' % sys.executable


def sha1(b):
    return hashlib.sha1(b).hexdigest()


class Kok:
    """Bir vakanin gecici evreni: veri koku + stl/ + sahte R2 + sahte npx."""

    def __init__(self, ust, idler=("a1", "b1", "c1"), kova_var=True):
        self.yol = tempfile.mkdtemp(prefix="vaka-", dir=ust)
        self.stl = os.path.join(self.yol, "stl")
        self.r2 = os.path.join(self.yol, "r2")
        self.bin = os.path.join(self.yol, "bin")
        self.tmp = os.path.join(self.yol, "tmp")
        for d in (self.stl, self.bin, self.tmp):
            os.makedirs(d)
        if kova_var:
            os.makedirs(os.path.join(self.r2, KOVA))
        else:
            os.makedirs(self.r2)
        self.cagri = os.path.join(self.yol, "cagri.log")
        open(self.cagri, "w").close()
        npx = os.path.join(self.bin, "npx")
        with open(npx, "w", encoding="utf-8") as f:
            f.write(SAHTE_NPX)
        os.chmod(npx, 0o755)
        self._json("urunler.json", [{"id": i} for i in idler])
        self._json(".urun-kaynaklari.json", {})
        self._json(".stl-r2-manifest.json", {})

    def _json(self, ad, veri):
        with open(os.path.join(self.yol, ad), "w", encoding="utf-8") as f:
            json.dump(veri, f)

    def yerel(self, ad, govde):
        with open(os.path.join(self.stl, ad), "wb") as f:
            f.write(govde)

    def uzak(self, anahtar, govde):
        yol = os.path.join(self.r2, KOVA, anahtar)
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, "wb") as f:
            f.write(govde)

    def manifest(self, veri):
        self._json(".stl-r2-manifest.json", veri)

    def kos(self, arac, argv, mod="normal"):
        ortam = dict(os.environ)
        ortam.update(PATH=self.bin + os.pathsep + ortam.get("PATH", ""),
                     FAKE_R2=self.r2, FAKE_MOD=mod, FAKE_CAGRI=self.cagri,
                     PRUVO_VERI_KOK=self.yol, TMPDIR=self.tmp)
        p = subprocess.run([sys.executable, arac] + argv, cwd=self.yol, env=ortam,
                           capture_output=True, text=True, timeout=120)
        return p.returncode, p.stdout + p.stderr

    def get_sayisi(self):
        with open(self.cagri) as f:
            return sum(1 for s in f if " object get " in " " + s)

    def agac(self):
        """(goreli yol -> sha1) — cagri.log ve tmp/ haric tum kok."""
        d = {}
        for kok, _dz, dosyalar in os.walk(self.yol):
            for ad in dosyalar:
                tam = os.path.join(kok, ad)
                if tam == self.cagri:
                    continue
                with open(tam, "rb") as f:
                    d[os.path.relpath(tam, self.yol)] = sha1(f.read())
        return d


def satir(cikti, onek):
    for s in cikti.splitlines():
        if s.startswith(onek):
            return dict(p.split("=", 1) for p in s.split()[2:] if "=" in p)
    return {}


def stl_satir(cikti):
    return satir(cikti, "R2_DOGRULA KIP=stl")


def yok_satir(cikti):
    return satir(cikti, "R2_DOGRULA KIP=yok")


X = b"solid x\n" + b"A" * 300
Y = b"solid x\n" + b"B" * 300          # X ile AYNI boyut, farkli icerik


def vakalar(ust, arac):
    """[(ad, ok, ayrinti)] — her vaka bagimsiz gecici kokte."""
    s = []

    def stl_kos(k, *ek, mod="normal"):
        return k.kos(arac, ["stl", "--dizin", k.stl, "--paralel", "3"] + list(ek), mod=mod)

    # S1
    k = Kok(ust); k.yerel("a1.stl", X); k.uzak("stl/a1/a1.stl", X)
    rc, c = stl_kos(k); r = stl_satir(c)
    s.append(("S1 esit->ESIT rc0", rc == 0 and r.get("ESIT") == "1" and r.get("TOPLAM") == "1", c))
    # S2
    k = Kok(ust); k.yerel("a1.stl", X); k.uzak("stl/a1/a1.stl", Y)
    rc, c = stl_kos(k); r = stl_satir(c)
    s.append(("S2 ayni boyut farkli icerik->FARKLI rc1",
              rc == 1 and r.get("FARKLI") == "1" and r.get("ESIT") == "0", c))
    # S3
    k = Kok(ust); k.yerel("a1.stl", X)
    rc, c = stl_kos(k); r = stl_satir(c)
    s.append(("S3 R2'de yok->YOK rc1", rc == 1 and r.get("YOK") == "1", c))
    # S4
    k = Kok(ust); k.yerel("a1.stl", X); k.uzak("stl/a1/a1.stl", X)
    rc, c = stl_kos(k, mod="rc_yalan"); r = stl_satir(c)
    s.append(("S4 wrangler rc!=0 -> asla ESIT (OLCULEMEDI rc2)",
              rc == 2 and r.get("ESIT") == "0" and r.get("OLCULEMEDI") == "1", c))
    # S5
    k = Kok(ust); k.yerel("zzz--parca.stl", X); k.uzak("stl/zzz/parca.stl", X)
    rc, c = stl_kos(k); r = stl_satir(c)
    s.append(("S5 hatali ad->HATALI_AD, get cagrilmaz",
              rc == 1 and r.get("HATALI_AD") == "1" and r.get("ESIT") == "0"
              and k.get_sayisi() == 0, c + " GET=%d" % k.get_sayisi()))
    # S6
    k = Kok(ust)
    k.yerel("a1.stl", X); k.uzak("stl/a1/a1.stl", X)        # ESIT
    k.yerel("b1.stl", X); k.uzak("stl/b1/b1.stl", Y)        # FARKLI
    k.yerel("c1.stl", X)                                     # YOK
    rc, c = stl_kos(k, "--sil"); kalan = sorted(os.listdir(k.stl))
    s.append(("S6 --sil yalniz ESIT'i siler",
              kalan == ["b1.stl", "c1.stl"] and "SILINDI=1 " in c and "KALAN=2" in c,
              c + " kalan=%s" % kalan))
    # S7
    k = Kok(ust); k.yerel("a1.stl", X); k.uzak("stl/a1/a1.stl", X)
    rc, c = stl_kos(k)
    s.append(("S7 --sil yokken silme 0",
              os.listdir(k.stl) == ["a1.stl"] and "SILINDI=" not in c, c))
    # S8
    k = Kok(ust); k.yerel("a1.stl", X)
    k.manifest({"stl/a1/a1.stl": {"sha1": sha1(X), "boyut": len(X)}})
    rc, c = stl_kos(k); r = stl_satir(c)
    s.append(("S8 manifest esit dese de R2'de yok->YOK",
              rc == 1 and r.get("YOK") == "1" and r.get("ESIT") == "0"
              and r.get("MANIFEST") == "1", c))
    # S9
    k = Kok(ust, kova_var=False); k.yerel("a1.stl", X)
    rc, c = stl_kos(k); r = stl_satir(c)
    s.append(("S9 olmayan kova->OLCULEMEDI, get yok",
              rc == 2 and r.get("OLCULEMEDI") == "1" and r.get("YOK") == "0"
              and k.get_sayisi() == 0 and "KOVA_KAPISI=KAPALI" in c, c))
    # S10
    k = Kok(ust); k.yerel("a1.stl", X); k.uzak("stl/a1/a1.stl", X); k.yerel("b1.stl", X)
    rapor = os.path.join(k.yol, "rapor.txt")
    rc, c = stl_kos(k, "--rapor", rapor)
    metin = open(rapor, encoding="utf-8").read() if os.path.isfile(rapor) else ""
    s.append(("S10 --rapor sinif listesi",
              "## ESIT (1)\na1.stl\tstl/a1/a1.stl" in metin and "## YOK (1)\nb1.stl" in metin,
              metin))
    # S11
    s.append(("S11 gecici dizin kosum sonunda silinir", os.listdir(k.tmp) == [],
              str(os.listdir(k.tmp))))

    anahtar_yok, anahtar_var = "stl/silinen/silinen.stl", "stl/a1/a1.stl"

    def yok_kos(k, anahtarlar, mod="normal"):
        dosya = os.path.join(k.yol, "anahtarlar.txt")
        with open(dosya, "w", encoding="utf-8") as f:
            f.write("# yorum\n\n" + "\n".join(anahtarlar) + "\n")
        return k.kos(arac, ["yok", "--anahtar-dosyasi", dosya, "--paralel", "2"], mod=mod)

    # Y1
    k = Kok(ust)
    rc, c = yok_kos(k, [anahtar_yok]); r = yok_satir(c)
    s.append(("Y1 gercek not-found->SILINDI_KANITLI rc0",
              rc == 0 and r.get("SILINDI_KANITLI") == "1" and r.get("OLCULEMEDI") == "0", c))
    # Y2
    k = Kok(ust); k.uzak(anahtar_var, X)
    rc, c = yok_kos(k, [anahtar_var, anahtar_yok]); r = yok_satir(c)
    s.append(("Y2 nesne var->HALA_VAR rc1",
              rc == 1 and r.get("HALA_VAR") == "1" and r.get("SILINDI_KANITLI") == "1", c))
    # Y3
    k = Kok(ust)
    rc, c = yok_kos(k, [anahtar_yok], mod="auth"); r = yok_satir(c)
    s.append(("Y3 kimlik/ag hatasi->OLCULEMEDI (SILINDI_KANITLI degil) rc2",
              rc == 2 and r.get("OLCULEMEDI") == "1" and r.get("SILINDI_KANITLI") == "0", c))
    # Y4
    k = Kok(ust); k.uzak(anahtar_var, X); k.yerel("a1.stl", X)
    dosya = os.path.join(k.yol, "anahtarlar.txt")
    with open(dosya, "w", encoding="utf-8") as f:
        f.write(anahtar_var + "\n" + anahtar_yok + "\n")
    once = k.agac()
    rc, c = k.kos(arac, ["yok", "--anahtar-dosyasi", dosya])
    sonra = k.agac()
    s.append(("Y4 yok kipi dosya yazmaz/silmez", once == sonra and os.listdir(k.tmp) == [],
              "fark=%s" % (set(once.items()) ^ set(sonra.items()))))
    # Y5
    k = Kok(ust, kova_var=False)
    rc, c = yok_kos(k, [anahtar_yok]); r = yok_satir(c)
    s.append(("Y5 olmayan kova->OLCULEMEDI (SILINDI_KANITLI degil)",
              rc == 2 and r.get("SILINDI_KANITLI") == "0" and r.get("OLCULEMEDI") == "1"
              and k.get_sayisi() == 0, c))
    return s


MUTANTLAR = [
    ("M1 sha'yi boyuta indir",
     "esit = (r_sha == y_sha and r_boyut == y_boyut)", "esit = (r_boyut == y_boyut)", 1),
    ("M2 wrangler rc'yi yok say",
     "if rc == 0 and INDIRME_TAMAM in metin", "if INDIRME_TAMAM in metin", 1),
    ("M3 --sil sinif kontrolunu kaldir",
     "            if k[0] != ESIT:\n                continue\n",
     "            if False:\n                continue\n", 1),
    ("M4 manifest esitse ESIT say",
     "        durum, r_sha, r_boyut = w.sonda(anahtar)\n",
     "        _m = yuk.manifest_oku(a.manifest or os.path.join(veri, '.stl-r2-manifest.json'))\n"
     "        if (_m.get(anahtar) or {}).get('sha1') == y_sha:\n"
     "            return (ESIT, ad, anahtar, y_sha, 'manifest')\n"
     "        durum, r_sha, r_boyut = w.sonda(anahtar)\n", 1),
    ("M5 her get hatasini not-found say",
     "if rc == 1 and NOT_FOUND_METNI in metin and not dolu:", "if rc != 0:", 1),
    ("M6 kova on-kapisini kaldir",
     "kova_acik, sebep = w.kova_acik_mi()", "kova_acik, sebep = True, ''", 2),
]


def main():
    ust = tempfile.mkdtemp(prefix="r2-canli-dogrula-test-")
    try:
        sonuc = vakalar(ust, ARAC)
        gecen = 0
        for ad, ok, ayrinti in sonuc:
            print(("  ✅ " if ok else "  ❌ ") + ad)
            if not ok:
                print("     " + ayrinti.replace("\n", "\n     ")[:1500])
            gecen += bool(ok)
        kaynak = open(ARAC, encoding="utf-8").read()
        survivor = 0
        for ad, eski, yeni, adet in MUTANTLAR:
            if kaynak.count(eski) != adet:
                print("  ❌ %s: mutasyon capasi %d kez bulundu (beklenen %d) — test bayat"
                      % (ad, kaynak.count(eski), adet))
                survivor += 1
                continue
            mdizin = tempfile.mkdtemp(prefix="mutant-", dir=ust)
            for kardes in KARDESLER:
                shutil.copy(os.path.join(TOOLS, kardes), mdizin)
            marac = os.path.join(mdizin, "r2-canli-dogrula.py")
            with open(marac, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(eski, yeni))
            kirmizi = [v[0] for v in vakalar(ust, marac) if not v[1]]
            if kirmizi:
                print("  🔪 %s OLDURULDU (%d vaka kirmizi: %s)"
                      % (ad, len(kirmizi), ", ".join(x.split()[0] for x in kirmizi)))
            else:
                print("  ❌ %s HAYATTA KALDI" % ad)
                survivor += 1
        print("VAKA=%d/%d SURVIVOR=%d MUTANT=%d" % (gecen, len(sonuc), survivor, len(MUTANTLAR)))
        return 0 if gecen == len(sonuc) and survivor == 0 else 1
    finally:
        shutil.rmtree(ust, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
