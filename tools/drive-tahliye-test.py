#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""drive-tahliye.py hermetik kabul testi (7 Eki 2026).

Sahte kok (tempfile) + enjekte TOPLU `yuklendi_fn`/`evict_fn`. Gercek HOME'a / gercek
Drive'a YAZMAZ, `swift` CAGIRMAZ. "Yerelde maddelesmis" = st_blocks>0: dolu dosya blok
tasir; sahte evict dosyayi truncate edip AYNI boyuta sparse uzatir (blok 0, boyut ayni —
FileProvider evict'inin diskteki izi).

Vakalar:
  Y1 yuklenmis dosya evict edilir (YESIL rc=0)
  Y2 yuklenmemis dosya BEKLIYOR, evict'e GITMEZ (dokunulmaz)
  Y3 tavan asimi -> KIRMIZI rc=1
  Y4 kok yok -> OLCULEMEDI rc=2
  Y5 evict hatasi (3 deneme) -> KIRMIZI, hata>0
  Y6 hicbir dosya silinmez (os.remove/unlink/rmdir/rmtree cagrisi 0; dosyalar yerinde)
Mutantlar (izole kopyada, kaynak DEGISMEZ): M1 tavan karsilastirmasi ters -> Y3 KIRMIZI ·
  M2 yuklendi kontrolu atlanir -> Y2 KIRMIZI. Mutant oldurulemezse test rc=1.
"""
import importlib.util
import os
import shutil
import sys
import tempfile

ARAC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drive-tahliye.py")
MB = 1024 * 1024

MUTANTLAR = [
    ("M1-tavan-ters", "Y3", "kirmizi = sonra > tavan_mb * _MB", "kirmizi = sonra < tavan_mb * _MB"),
    ("M2-yuklendi-atla", "Y2", "if d is True]", "if True]"),
]


def yukle(yol, ad):
    spec = importlib.util.spec_from_file_location(ad, yol)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def dolu_yaz(yol, bayt):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, "wb") as f:
        f.write(b"\x5a" * bayt)


def bloklu(yol):
    return os.lstat(yol).st_blocks > 0


class SahteDrive:
    """yuklu kumesi + evict davranisi. `cagri` her evict'e giden yolu kaydeder."""

    def __init__(self, yuklu, bozuk=()):
        self.yuklu = set(yuklu)
        self.bozuk = set(bozuk)
        self.cagri = []

    def yuklendi(self, yollar):
        return [y in self.yuklu for y in yollar]

    def evict(self, yollar):
        sonuc = []
        for y in yollar:
            self.cagri.append(y)
            if y in self.bozuk:
                sonuc.append(False)
                continue
            boyut = os.path.getsize(y)
            with open(y, "r+b") as f:
                f.truncate(0)
                f.truncate(boyut)
            sonuc.append(True)
        return sonuc


def vakalar(mod):
    """{vaka: (gecti, ayrinti)}"""
    s = {}
    kok_ust = tempfile.mkdtemp(prefix="drive-tahliye-test-")
    try:
        # ---- Y1 + Y2 + Y6: bir yuklu, bir yuklenmemis dosya, tavan genis ----
        kok = os.path.join(kok_ust, "y1", "PRUVO")
        a = os.path.join(kok, "Pruvo", "STL", "a.stl")
        b = os.path.join(kok, "Pruvo", "backup-v2", "b.json")
        dolu_yaz(a, 64 * 1024)
        dolu_yaz(b, 64 * 1024)
        sd = SahteDrive(yuklu=[a])
        silme = {"n": 0}
        asil = {}

        def say(ad):
            def f(*x, **k):
                silme["n"] += 1
                return asil[ad](*x, **k)
            return f
        for ad, sahip in (("remove", os), ("unlink", os), ("rmdir", os), ("rmtree", shutil)):
            asil[ad] = getattr(sahip, ad)
            setattr(sahip, ad, say(ad))
        try:
            satir, rc = mod.calistir([kok], tavan_mb=500, yuklendi_fn=sd.yuklendi, evict_fn=sd.evict)
        finally:
            for ad, sahip in (("remove", os), ("unlink", os), ("rmdir", os), ("rmtree", shutil)):
                setattr(sahip, ad, asil[ad])
        s["Y1"] = (rc == 0 and "HUKUM=YESIL" in satir and " evict=1 " in satir and not bloklu(a)
                   and a in sd.cagri, satir)
        s["Y2"] = (b not in sd.cagri and bloklu(b) and " bekliyor=1 " in satir, satir)
        s["Y6"] = (silme["n"] == 0 and os.path.exists(a) and os.path.exists(b)
                   and os.path.getsize(a) == 64 * 1024, "silme_cagrisi=%d" % silme["n"])

        # ---- Y3: yuklenmemis 2 MB, tavan 1 MB -> KIRMIZI rc=1 ----
        kok3 = os.path.join(kok_ust, "y3", "PRUVO")
        c = os.path.join(kok3, "Pruvo", "c.bin")
        dolu_yaz(c, 2 * MB)
        satir, rc = mod.calistir([kok3], tavan_mb=1, yuklendi_fn=SahteDrive([]).yuklendi,
                                 evict_fn=SahteDrive([]).evict)
        s["Y3"] = (rc == 1 and "HUKUM=KIRMIZI" in satir and "yerel_sonra_mb=2" in satir, satir)

        # ---- Y4: kok yok -> OLCULEMEDI rc=2 (bos kok listesi de) ----
        satir, rc = mod.calistir([os.path.join(kok_ust, "yok")], yuklendi_fn=sd.yuklendi,
                                 evict_fn=sd.evict)
        satir2, rc2 = mod.calistir([], yuklendi_fn=sd.yuklendi, evict_fn=sd.evict)
        s["Y4"] = (rc == 2 and rc2 == 2 and "OLCULEMEDI" in satir and "YESIL" not in satir
                   and "YESIL" not in satir2, satir)

        # ---- Y5: yuklu ama evict hep basarisiz -> 3 deneme, hata=1, KIRMIZI ----
        kok5 = os.path.join(kok_ust, "y5", "PRUVO")
        e = os.path.join(kok5, "Pruvo", "e.stl")
        dolu_yaz(e, 64 * 1024)
        sd5 = SahteDrive(yuklu=[e], bozuk=[e])
        satir, rc = mod.calistir([kok5], tavan_mb=500, yuklendi_fn=sd5.yuklendi, evict_fn=sd5.evict)
        s["Y5"] = (rc == 1 and "HUKUM=KIRMIZI" in satir and " hata=1 " in satir
                   and sd5.cagri.count(e) == 3 and os.path.exists(e), satir)

        # ---- kuru: evict YAPILMAZ, sayilir ----
        kok7 = os.path.join(kok_ust, "y7", "PRUVO")
        g = os.path.join(kok7, "Pruvo", "g.stl")
        dolu_yaz(g, 64 * 1024)
        sd7 = SahteDrive(yuklu=[g])
        satir, rc = mod.calistir([kok7], kuru=True, yuklendi_fn=sd7.yuklendi, evict_fn=sd7.evict)
        s["Y7-kuru"] = (not sd7.cagri and bloklu(g) and " evict=1 " in satir
                        and satir.count("\n") == 0, satir)
    finally:
        shutil.rmtree(kok_ust, ignore_errors=True)
    return s


def main():
    kaynak = open(ARAC, encoding="utf-8").read()
    toplam_rc = 0
    sonuc = vakalar(yukle(ARAC, "drive_tahliye_asil"))
    for v, (ok, ayr) in sorted(sonuc.items()):
        print("%s %s  %s" % ("GECTI " if ok else "KALDI ", v, ayr))
        if not ok:
            toplam_rc = 1

    gecici = tempfile.mkdtemp(prefix="drive-tahliye-mutant-")
    try:
        for ad, hedef, capa, yama in MUTANTLAR:
            if kaynak.count(capa) != 1:
                print("MUTANT %s CAPA_YOK (sayi=%d) — kaynak degisti, mutant bayat" % (ad, kaynak.count(capa)))
                toplam_rc = 1
                continue
            yol = os.path.join(gecici, ad + ".py")
            with open(yol, "w", encoding="utf-8") as f:
                f.write(kaynak.replace(capa, yama))
            ms = vakalar(yukle(yol, "drive_tahliye_" + ad.replace("-", "_")))
            olduruldu = not ms[hedef][0]
            print("MUTANT %s -> %s %s" % (ad, hedef, "KIRMIZI (olduruldu)" if olduruldu else "YESIL (SAG KALDI)"))
            if not olduruldu:
                toplam_rc = 1
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    print("DRIVE_TAHLIYE_TEST vaka=%d gecti=%d mutant=%d HUKUM=%s" % (
        len(sonuc), sum(1 for ok, _ in sonuc.values() if ok), len(MUTANTLAR),
        "YESIL" if toplam_rc == 0 else "KIRMIZI"))
    return toplam_rc


if __name__ == "__main__":
    sys.exit(main())
